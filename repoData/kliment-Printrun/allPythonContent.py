__FILENAME__ = calibrateextruder
#!/usr/bin/env python
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

# Interactive RepRap e axis calibration program
# (C) Nathan Zadoks 2011

s = 300  # Extrusion speed (mm/min)
n = 100  # Default length to extrude
m = 0  # User-entered measured extrusion length
k = 300  # Default amount of steps per mm
port = '/dev/ttyUSB0'  # Default serial port to connect to printer
temp = 210  # Default extrusion temperature

tempmax = 250  # Maximum extrusion temperature

t = int(n * 60) / s  # Time to wait for extrusion

try:
    from printdummy import printcore
except ImportError:
    from printcore import printcore

import time
import getopt
import sys
import os

def float_input(prompt=''):
    f = None
    while f is None:
        s = raw_input(prompt)
        try:
            f = float(s)
        except ValueError:
            sys.stderr.write("Not a valid floating-point number.\n")
            sys.stderr.flush()
    return f
def wait(t, m=''):
    sys.stdout.write(m + '[' + (' ' * t) + ']\r' + m + '[')
    sys.stdout.flush()
    for i in range(t):
        for s in ['|\b', '/\b', '-\b', '\\\b', '|']:
            sys.stdout.write(s)
            sys.stdout.flush()
            time.sleep(1.0 / 5)
    print
def w(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def heatup(p, temp, s = 0):
    curtemp = gettemp(p)
    p.send_now('M109 S%03d' % temp)
    p.temp = 0
    if not s: w("Heating extruder up..")
    f = False
    while curtemp <= (temp - 1):
        p.send_now('M105')
        time.sleep(0.5)
        if not f:
            time.sleep(1.5)
            f = True
        curtemp = gettemp(p)
        if curtemp: w(u"\rHeating extruder up.. %3d \xb0C" % curtemp)
    if s: print
    else: print "\nReady."

def gettemp(p):
    try: p.logl
    except: setattr(p, 'logl', 0)
    try: p.temp
    except: setattr(p, 'temp', 0)
    for n in range(p.logl, len(p.log)):
        line = p.log[n]
        if 'T:' in line:
            try:
                setattr(p, 'temp', int(line.split('T:')[1].split()[0]))
            except: print line
    p.logl = len(p.log)
    return p.temp
if not os.path.exists(port):
    port = 0

# Parse options
help = u"""
%s [ -l DISTANCE ] [ -s STEPS ] [ -t TEMP ] [ -p PORT ]
        -l      --length        Length of filament to extrude for each calibration step (default: %d mm)
        -s      --steps         Initial amount of steps to use (default: %d steps)
        -t      --temp          Extrusion temperature in degrees Celsius (default: %d \xb0C, max %d \xb0C)
        -p      --port          Serial port the printer is connected to (default: %s)
        -h      --help          This cruft.
"""[1:-1].encode('utf-8') % (sys.argv[0], n, k, temp, tempmax, port if port else 'auto')
try:
    opts, args = getopt.getopt(sys.argv[1:], "hl:s:t:p:", ["help", "length=", "steps=", "temp=", "port="])
except getopt.GetoptError, err:
    print str(err)
    print help
    sys.exit(2)
for o, a in opts:
    if o in ('-h', '--help'):
        print help
        sys.exit()
    elif o in ('-l', '--length'):
        n = float(a)
    elif o in ('-s', '--steps'):
        k = int(a)
    elif o in ('-t', '--temp'):
        temp = int(a)
        if temp >= tempmax:
            print (u'%d \xb0C? Are you insane?'.encode('utf-8') % temp) + (" That's over nine thousand!" if temp > 9000 else '')
            sys.exit(255)
    elif o in ('-p', '--port'):
        port = a

# Show initial parameters
print "Initial parameters"
print "Steps per mm:    %3d steps" % k
print "Length extruded: %3d mm" % n
print
print "Serial port:     %s" % (port if port else 'auto')

p = None
try:
    # Connect to printer
    w("Connecting to printer..")
    try:
        p = printcore(port, 115200)
    except:
        print 'Error.'
        raise
    while not p.online:
        time.sleep(1)
        w('.')
    print " connected."

    heatup(p, temp)

    # Calibration loop
    while n != m:
        heatup(p, temp, True)
        p.send_now("G92 E0")  # Reset e axis
        p.send_now("G1 E%d F%d" % (n, s))  # Extrude length of filament
        wait(t, 'Extruding.. ')
        m = float_input("How many millimeters of filament were extruded? ")
        if m == 0: continue
        if n != m:
            k = (n / m) * k
            p.send_now("M92 E%d" % int(round(k)))  # Set new step count
            print "Steps per mm:    %3d steps" % k  # Tell user
    print 'Calibration completed.'  # Yay!
except KeyboardInterrupt:
    pass
finally:
    if p: p.disconnect()

########NEW FILE########
__FILENAME__ = plater
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import wx

from printrun.stlplater import StlPlater

if __name__ == '__main__':
    app = wx.App(False)
    main = StlPlater(sys.argv[1:])
    main.Show()
    app.MainLoop()

########NEW FILE########
__FILENAME__ = printcore
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import time
import getopt
import sys

from printrun.printcore import printcore
from printrun import gcoder

if __name__ == '__main__':
    baud = 115200
    loud = False
    statusreport = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h,b:,v,s",
                                   ["help", "baud", "verbose", "statusreport"])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)
    for o, a in opts:
        if o in ('-h', '--help'):
            # FIXME: Fix help
            print ("Opts are: --help, -b --baud = baudrate, -v --verbose, "
                   "-s --statusreport")
            sys.exit(1)
        if o in ('-b', '--baud'):
            baud = int(a)
        if o in ('-v', '--verbose'):
            loud = True
        elif o in ('-s', '--statusreport'):
            statusreport = True

    if len(args) > 1:
        port = args[-2]
        filename = args[-1]
        print "Printing: %s on %s with baudrate %d" % (filename, port, baud)
    else:
        print "Usage: python [-h|-b|-v|-s] printcore.py /dev/tty[USB|ACM]x filename.gcode"
        sys.exit(2)
    p = printcore(port, baud)
    p.loud = loud
    time.sleep(2)
    gcode = [i.strip() for i in open(filename)]
    gcode = gcoder.LightGCode(gcode)
    p.startprint(gcode)

    try:
        if statusreport:
            p.loud = False
            sys.stdout.write("Progress: 00.0%\r")
            sys.stdout.flush()
        while p.printing:
            time.sleep(1)
            if statusreport:
                progress = 100 * float(p.queueindex) / len(p.mainqueue)
                sys.stdout.write("Progress: %02.1f%%\r" % progress)
                sys.stdout.flush()
        p.disconnect()
        sys.exit(0)
    except:
        p.disconnect()

########NEW FILE########
__FILENAME__ = excluder
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
from printrun import gviz

from .utils import imagefile, install_locale
install_locale('pronterface')

class ExcluderWindow(gviz.GvizWindow):

    def __init__(self, excluder, *args, **kwargs):
        super(ExcluderWindow, self).__init__(*args, **kwargs)
        self.SetTitle(_("Part excluder: draw rectangles where print instructions should be ignored"))
        self.toolbar.AddLabelTool(128, " " + _("Reset selection"),
                                  wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(),
                                  shortHelp = _("Reset selection"),
                                  longHelp = "")
        self.Bind(wx.EVT_TOOL, self.reset_selection, id = 128)
        self.parent = excluder
        self.p.paint_overlay = self.paint_selection
        self.p.layerup()

    def real_to_gcode(self, x, y):
        return (x + self.p.build_dimensions[3],
                self.p.build_dimensions[4] + self.p.build_dimensions[1] - y)

    def gcode_to_real(self, x, y):
        return (x - self.p.build_dimensions[3],
                self.p.build_dimensions[1] - (y - self.p.build_dimensions[4]))

    def mouse(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT) \
           or event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            self.initpos = None
        elif event.Dragging() and event.RightIsDown():
            e = event.GetPositionTuple()
            if not self.initpos or not hasattr(self, "basetrans"):
                self.initpos = e
                self.basetrans = self.p.translate
            self.p.translate = [self.basetrans[0] + (e[0] - self.initpos[0]),
                                self.basetrans[1] + (e[1] - self.initpos[1])]
            self.p.dirty = 1
            wx.CallAfter(self.p.Refresh)
        elif event.Dragging() and event.LeftIsDown():
            x, y = event.GetPositionTuple()
            if not hasattr(self, "basetrans"):
                self.basetrans = self.p.translate
            x = (x - self.basetrans[0]) / self.p.scale[0]
            y = (y - self.basetrans[1]) / self.p.scale[1]
            x, y = self.real_to_gcode(x, y)
            if not self.initpos:
                self.initpos = (x, y)
                self.basetrans = self.p.translate
                self.parent.rectangles.append((0, 0, 0, 0))
            else:
                pos = (x, y)
                x0 = min(self.initpos[0], pos[0])
                y0 = min(self.initpos[1], pos[1])
                x1 = max(self.initpos[0], pos[0])
                y1 = max(self.initpos[1], pos[1])
                self.parent.rectangles[-1] = (x0, y0, x1, y1)
            wx.CallAfter(self.p.Refresh)
        else:
            event.Skip()

    def _line_scaler(self, orig):
        x0, y0 = self.gcode_to_real(orig[0], orig[1])
        x0 = self.p.scale[0] * x0 + self.p.translate[0]
        y0 = self.p.scale[1] * y0 + self.p.translate[1]
        x1, y1 = self.gcode_to_real(orig[2], orig[3])
        x1 = self.p.scale[0] * x1 + self.p.translate[0]
        y1 = self.p.scale[1] * y1 + self.p.translate[1]
        width = max(x0, x1) - min(x0, x1) + 1
        height = max(y0, y1) - min(y0, y1) + 1
        return (min(x0, x1), min(y0, y1), width, height,)

    def paint_selection(self, dc):
        dc = wx.GCDC(dc)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleList([self._line_scaler(rect)
                              for rect in self.parent.rectangles],
                             None, wx.Brush((200, 200, 200, 150)))

    def reset_selection(self, event):
        self.parent.rectangles = []
        wx.CallAfter(self.p.Refresh)

class Excluder(object):

    def __init__(self):
        self.rectangles = []
        self.window = None

    def pop_window(self, gcode, *args, **kwargs):
        if not self.window:
            self.window = ExcluderWindow(self, *args, **kwargs)
            self.window.p.addfile(gcode, True)
            self.window.Bind(wx.EVT_CLOSE, self.close_window)
            self.window.Show()
        else:
            self.window.Show()
            self.window.Raise()

    def close_window(self, event = None):
        if self.window:
            self.window.Destroy()
            self.window = None

if __name__ == '__main__':
    import sys
    import gcoder
    gcode = gcoder.GCode(open(sys.argv[1]))
    app = wx.App(False)
    ex = Excluder()
    ex.pop_window(gcode)
    app.MainLoop()

########NEW FILE########
__FILENAME__ = gcodeplater
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from .utils import install_locale, get_home_pos
install_locale('pronterface')

import wx
import sys
import types
import re
import math

from printrun import gcview
from printrun import gcoder
from printrun.objectplater import Plater
from printrun.gl.libtatlin import actors

def extrusion_only(gline):
    return gline.e is not None \
        and (gline.x, gline.y, gline.z) == (None, None, None)

# Custom method for gcoder.GCode to analyze & output gcode in a single call
def gcoder_write(self, f, line, store = False):
    f.write(line)
    self.append(line, store = store)

rewrite_exp = re.compile("(%s)" % "|".join(["X([-+]?[0-9]*\.?[0-9]*)",
                                            "Y([-+]?[0-9]*\.?[0-9]*)"]))

def rewrite_gline(centeroffset, gline, cosr, sinr):
    if gline.is_move and (gline.x is not None or gline.y is not None):
        if gline.relative:
            xc = yc = 0
            cox = coy = 0
            if gline.x is not None:
                xc = gline.x
            if gline.y is not None:
                yc = gline.y
        else:
            xc = gline.current_x + centeroffset[0]
            yc = gline.current_y + centeroffset[1]
            cox = centeroffset[0]
            coy = centeroffset[1]
        new_x = "X%.04f" % (xc * cosr - yc * sinr - cox)
        new_y = "Y%.04f" % (xc * sinr + yc * cosr - coy)
        new = {"X": new_x, "Y": new_y}
        new_line = rewrite_exp.sub(lambda ax: new[ax.group()[0]], gline.raw)
        new_line = new_line.split(";")[0]
        if gline.x is None: new_line += " " + new_x
        if gline.y is None: new_line += " " + new_y
        return new_line
    else:
        return gline.raw

class GcodePlater(Plater):

    load_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)") + "|*.gcode;*.gco;*.g"
    save_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)") + "|*.gcode;*.gco;*.g"

    def __init__(self, filenames = [], size = (800, 580), callback = None, parent = None, build_dimensions = None, circular_platform = False, antialias_samples = 0):
        super(GcodePlater, self).__init__(filenames, size, callback, parent, build_dimensions)
        viewer = gcview.GcodeViewPanel(self, build_dimensions = self.build_dimensions,
                                       antialias_samples = antialias_samples)
        self.set_viewer(viewer)
        self.platform = actors.Platform(self.build_dimensions,
                                        circular = circular_platform)
        self.platform_object = gcview.GCObject(self.platform)

    def get_objects(self):
        return [self.platform_object] + self.models.values()
    objects = property(get_objects)

    def load_file(self, filename):
        gcode = gcoder.GCode(open(filename, "rU"),
                             get_home_pos(self.build_dimensions))
        model = actors.GcodeModel()
        if gcode.filament_length > 0:
            model.display_travels = False
        generator = model.load_data(gcode)
        generator_output = generator.next()
        while generator_output is not None:
            generator_output = generator.next()
        obj = gcview.GCObject(model)
        obj.gcode = gcode
        obj.dims = [gcode.xmin, gcode.xmax,
                    gcode.ymin, gcode.ymax,
                    gcode.zmin, gcode.zmax]
        obj.centeroffset = [-(obj.dims[1] + obj.dims[0]) / 2,
                            -(obj.dims[3] + obj.dims[2]) / 2,
                            0]
        self.add_model(filename, obj)
        wx.CallAfter(self.Refresh)

    # What's hard in there ?
    # 1) [x] finding the order in which the objects are printed
    # 2) [x] handling layers correctly
    # 3) [x] handling E correctly
    # 4) [x] handling position shifts: should we either reset absolute 0 using
    #        G92 or should we rewrite all positions ? => we use G92s
    # 5) [ ] handling the start & end gcode properly ?
    # 6) [x] handling of current tool
    # 7) [x] handling of Z moves for sequential printing (don't lower Z before
    #        reaching the next object print area)
    # 8) [x] handling of absolute/relative status
    # Initial implementation should just print the objects sequentially,
    # but the end goal is to have a clean per-layer merge
    def export_to(self, name):
        return self.export_combined(name)
        return self.export_sequential(name)

    def export_combined(self, name):
        models = self.models.values()
        last_real_position = None
        # Sort models by Z max to print smaller objects first
        models.sort(key = lambda x: x.dims[-1])
        alllayers = []
        for (model_i, model) in enumerate(models):
            def add_offset(layer):
                return layer.z + model.offsets[2] if layer.z is not None else layer.z
            alllayers += [(add_offset(layer), model_i, layer_i)
                          for (layer_i, layer) in enumerate(model.gcode.all_layers) if layer]
        alllayers.sort()
        laste = [0] * len(models)
        lasttool = [0] * len(models)
        lastrelative = [False] * len(models)
        with open(name, "w") as f:
            analyzer = gcoder.GCode(None, get_home_pos(self.build_dimensions))
            analyzer.write = types.MethodType(lambda self, line: gcoder_write(self, f, line), analyzer)
            for (layer_z, model_i, layer_i) in alllayers:
                model = models[model_i]
                layer = model.gcode.all_layers[layer_i]
                r = math.radians(model.rot)
                o = model.offsets
                co = model.centeroffset
                offset_pos = last_real_position if last_real_position is not None else (0, 0, 0)
                analyzer.write("; %f %f %f\n" % offset_pos)
                trans = (- (o[0] + co[0]),
                         - (o[1] + co[1]),
                         - (o[2] + co[2]))
                trans_wpos = (offset_pos[0] + trans[0],
                              offset_pos[1] + trans[1],
                              offset_pos[2] + trans[2])
                analyzer.write("; GCodePlater: Model %d Layer %d at Z = %s\n" % (model_i, layer_i, layer_z))
                if lastrelative[model_i]:
                    analyzer.write("G91\n")
                else:
                    analyzer.write("G90\n")
                if analyzer.current_tool != lasttool[model_i]:
                    analyzer.write("T%d\n" % lasttool[model_i])
                analyzer.write("G92 X%.5f Y%.5f Z%.5f\n" % trans_wpos)
                analyzer.write("G92 E%.5f\n" % laste[model_i])
                for l in layer:
                    if l.command != "G28" and (l.command != "G92" or extrusion_only(l)):
                        if r == 0:
                            analyzer.write(l.raw + "\n")
                        else:
                            analyzer.write(rewrite_gline(co, l, math.cos(r), math.sin(r)) + "\n")
                # Find the current real position & E
                last_real_position = analyzer.current_pos
                laste[model_i] = analyzer.current_e
                lastrelative[model_i] = analyzer.relative
                lasttool[model_i] = analyzer.current_tool
        print _("Exported merged G-Codes to %s") % name

    def export_sequential(self, name):
        models = self.models.values()
        last_real_position = None
        # Sort models by Z max to print smaller objects first
        models.sort(key = lambda x: x.dims[-1])
        with open(name, "w") as f:
            for model_i, model in enumerate(models):
                r = math.radians(model.rot)
                o = model.offsets
                co = model.centeroffset
                offset_pos = last_real_position if last_real_position is not None else (0, 0, 0)
                trans = (- (o[0] + co[0]),
                         - (o[1] + co[1]),
                         - (o[2] + co[2]))
                trans_wpos = (offset_pos[0] + trans[0],
                              offset_pos[1] + trans[1],
                              offset_pos[2] + trans[2])
                f.write("; GCodePlater: Model %d\n" % model_i)
                f.write("G90\n")
                f.write("G92 X%.5f Y%.5f Z%.5f E0\n" % trans_wpos)
                f.write("G1 X%.5f Y%.5f" % (-co[0], -co[1]))
                for l in model.gcode:
                    if l.command != "G28" and (l.command != "G92" or extrusion_only(l)):
                        if r == 0:
                            f.write(l.raw + "\n")
                        else:
                            f.write(rewrite_gline(co, l, math.cos(r), math.sin(r)) + "\n")
                # Find the current real position
                for i in xrange(len(model.gcode) - 1, -1, -1):
                    gline = model.gcode.lines[i]
                    if gline.is_move:
                        last_real_position = (- trans[0] + gline.current_x,
                                              - trans[1] + gline.current_y,
                                              - trans[2] + gline.current_z)
                        break
        print _("Exported merged G-Codes to %s") % name

if __name__ == '__main__':
    app = wx.App(False)
    main = GcodePlater(sys.argv[1:])
    for fn in main.filenames:
        main.load_file(fn)
    main.filenames = None
    main.autoplate()
    main.export_to("gcodeplate___test.gcode")
    raise SystemExit
    main.Show()
    app.MainLoop()

########NEW FILE########
__FILENAME__ = gcoder
#!/usr/bin/env python
# This file is copied from GCoder.
#
# GCoder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GCoder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import math
import datetime
import logging
from array import array

gcode_parsed_args = ["x", "y", "e", "f", "z", "i", "j"]
gcode_parsed_nonargs = ["g", "t", "m", "n"]
to_parse = "".join(gcode_parsed_args + gcode_parsed_nonargs)
gcode_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n|([%s])([-+]?[0-9]*\.?[0-9]*)" % to_parse)
gcode_strip_comment_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n")
m114_exp = re.compile("\([^\(\)]*\)|[/\*].*\n|([XYZ]):?([-+]?[0-9]*\.?[0-9]*)")
specific_exp = "(?:\([^\(\)]*\))|(?:;.*)|(?:[/\*].*\n)|(%s[-+]?[0-9]*\.?[0-9]*)"
move_gcodes = ["G0", "G1", "G2", "G3"]

class PyLine(object):

    __slots__ = ('x', 'y', 'z', 'e', 'f', 'i', 'j',
                 'raw', 'command', 'is_move',
                 'relative', 'relative_e',
                 'current_x', 'current_y', 'current_z', 'extruding',
                 'current_tool',
                 'gcview_end_vertex')

    def __init__(self, l):
        self.raw = l

    def __getattr__(self, name):
        return None

class PyLightLine(object):

    __slots__ = ('raw', 'command')

    def __init__(self, l):
        self.raw = l

    def __getattr__(self, name):
        return None

try:
    import gcoder_line
    Line = gcoder_line.GLine
    LightLine = gcoder_line.GLightLine
except Exception, e:
    logging.warning("Memory-efficient GCoder implementation unavailable: %s" % e)
    Line = PyLine
    LightLine = PyLightLine

def find_specific_code(line, code):
    exp = specific_exp % code
    bits = [bit for bit in re.findall(exp, line.raw) if bit]
    if not bits: return None
    else: return float(bits[0][1:])

def S(line):
    return find_specific_code(line, "S")

def P(line):
    return find_specific_code(line, "P")

def split(line):
    split_raw = gcode_exp.findall(line.raw.lower())
    if split_raw and split_raw[0][0] == "n":
        del split_raw[0]
    if not split_raw:
        line.command = line.raw
        line.is_move = False
        logging.warning("raw G-Code line \"%s\" could not be parsed" % line.raw)
        return [line.raw]
    command = split_raw[0]
    line.command = command[0].upper() + command[1]
    line.is_move = line.command in move_gcodes
    return split_raw

def parse_coordinates(line, split_raw, imperial = False, force = False):
    # Not a G-line, we don't want to parse its arguments
    if not force and line.command[0] != "G":
        return
    unit_factor = 25.4 if imperial else 1
    for bit in split_raw:
        code = bit[0]
        if code not in gcode_parsed_nonargs and bit[1]:
            setattr(line, code, unit_factor * float(bit[1]))

class Layer(list):

    __slots__ = ("duration", "z")

    def __init__(self, lines, z = None):
        super(Layer, self).__init__(lines)
        self.z = z

class GCode(object):

    line_class = Line

    lines = None
    layers = None
    all_layers = None
    layer_idxs = None
    line_idxs = None
    append_layer = None
    append_layer_id = None

    imperial = False
    relative = False
    relative_e = False
    current_tool = 0
    # Home position: current absolute position counted from machine origin
    home_x = 0
    home_y = 0
    home_z = 0
    # Current position: current absolute position counted from machine origin
    current_x = 0
    current_y = 0
    current_z = 0
    # For E this is the absolute position from machine start
    current_e = 0
    total_e = 0
    max_e = 0
    # Current feedrate
    current_f = 0
    # Offset: current offset between the machine origin and the machine current
    # absolute coordinate system (as shifted by G92s)
    offset_x = 0
    offset_y = 0
    offset_z = 0
    offset_e = 0
    # Expected behavior:
    # - G28 X => X axis is homed, offset_x <- 0, current_x <- home_x
    # - G92 Xk => X axis does not move, so current_x does not change
    #             and offset_x <- current_x - k,
    # - absolute G1 Xk => X axis moves, current_x <- offset_x + k
    # How to get...
    # current abs X from machine origin: current_x
    # current abs X in machine current coordinate system: current_x - offset_x

    filament_length = None
    duration = None
    xmin = None
    xmax = None
    ymin = None
    ymax = None
    zmin = None
    zmax = None
    width = None
    depth = None
    height = None

    est_layer_height = None

    # abs_x is the current absolute X in machine current coordinate system
    # (after the various G92 transformations) and can be used to store the
    # absolute position of the head at a given time
    def _get_abs_x(self):
        return self.current_x - self.offset_x
    abs_x = property(_get_abs_x)

    def _get_abs_y(self):
        return self.current_y - self.offset_y
    abs_y = property(_get_abs_y)

    def _get_abs_z(self):
        return self.current_z - self.offset_z
    abs_z = property(_get_abs_z)

    def _get_abs_e(self):
        return self.current_e - self.offset_e
    abs_e = property(_get_abs_e)

    def _get_abs_pos(self):
        return (self.abs_x, self.abs_y, self.abs_z)
    abs_pos = property(_get_abs_pos)

    def _get_current_pos(self):
        return (self.current_x, self.current_y, self.current_z)
    current_pos = property(_get_current_pos)

    def _get_home_pos(self):
        return (self.home_x, self.home_y, self.home_z)

    def _set_home_pos(self, home_pos):
        if home_pos:
            self.home_x, self.home_y, self.home_z = home_pos
    home_pos = property(_get_home_pos, _set_home_pos)

    def _get_layers_count(self):
        return len(self.all_zs)
    layers_count = property(_get_layers_count)

    def __init__(self, data = None, home_pos = None,
                 layer_callback = None, deferred = False):
        if not deferred:
            self.prepare(data, home_pos, layer_callback)

    def prepare(self, data = None, home_pos = None, layer_callback = None):
        self.home_pos = home_pos
        if data:
            line_class = self.line_class
            self.lines = [line_class(l2) for l2 in
                          (l.strip() for l in data)
                          if l2]
            self._preprocess(build_layers = True,
                             layer_callback = layer_callback)
        else:
            self.lines = []
            self.append_layer_id = 0
            self.append_layer = Layer([])
            self.all_layers = [self.append_layer]
            self.all_zs = set()
            self.layers = {}
            self.layer_idxs = array('I', [])
            self.line_idxs = array('I', [])

    def __len__(self):
        return len(self.line_idxs)

    def __iter__(self):
        return self.lines.__iter__()

    def prepend_to_layer(self, commands, layer_idx):
        # Prepend commands in reverse order
        commands = [c.strip() for c in commands[::-1] if c.strip()]
        layer = self.all_layers[layer_idx]
        # Find start index to append lines
        # and end index to append new indices
        start_index = self.layer_idxs.index(layer_idx)
        for i in range(start_index, len(self.layer_idxs)):
            if self.layer_idxs[i] != layer_idx:
                end_index = i
                break
        else:
            end_index = i + 1
        end_line = self.line_idxs[end_index - 1]
        for i, command in enumerate(commands):
            gline = Line(command)
            # Split to get command
            split(gline)
            # Force is_move to False
            gline.is_move = False
            # Insert gline at beginning of layer
            layer.insert(0, gline)
            # Insert gline at beginning of list
            self.lines.insert(start_index, gline)
            # Update indices arrays & global gcodes list
            self.layer_idxs.insert(end_index + i, layer_idx)
            self.line_idxs.insert(end_index + i, end_line + i + 1)
        return commands[::-1]

    def rewrite_layer(self, commands, layer_idx):
        # Prepend commands in reverse order
        commands = [c.strip() for c in commands[::-1] if c.strip()]
        layer = self.all_layers[layer_idx]
        # Find start index to append lines
        # and end index to append new indices
        start_index = self.layer_idxs.index(layer_idx)
        for i in range(start_index, len(self.layer_idxs)):
            if self.layer_idxs[i] != layer_idx:
                end_index = i
                break
        else:
            end_index = i + 1
        self.layer_idxs = self.layer_idxs[:start_index] + array('I', len(commands) * [layer_idx]) + self.layer_idxs[end_index:]
        self.line_idxs = self.line_idxs[:start_index] + array('I', range(len(commands))) + self.line_idxs[end_index:]
        del self.lines[start_index:end_index]
        del layer[:]
        for i, command in enumerate(commands):
            gline = Line(command)
            # Split to get command
            split(gline)
            # Force is_move to False
            gline.is_move = False
            # Insert gline at beginning of layer
            layer.insert(0, gline)
            # Insert gline at beginning of list
            self.lines.insert(start_index, gline)
        return commands[::-1]

    def append(self, command, store = True):
        command = command.strip()
        if not command:
            return
        gline = Line(command)
        self._preprocess([gline])
        if store:
            self.lines.append(gline)
            self.append_layer.append(gline)
            self.layer_idxs.append(self.append_layer_id)
            self.line_idxs.append(len(self.append_layer))
        return gline

    def _preprocess(self, lines = None, build_layers = False,
                    layer_callback = None):
        """Checks for imperial/relativeness settings and tool changes"""
        if not lines:
            lines = self.lines
        imperial = self.imperial
        relative = self.relative
        relative_e = self.relative_e
        current_tool = self.current_tool
        current_x = self.current_x
        current_y = self.current_y
        current_z = self.current_z
        offset_x = self.offset_x
        offset_y = self.offset_y
        offset_z = self.offset_z

        # Extrusion computation
        current_e = self.current_e
        offset_e = self.offset_e
        total_e = self.total_e
        max_e = self.max_e

        # Store this one out of the build_layers scope for efficiency
        cur_layer_has_extrusion = False

        # Initialize layers and other global computations
        if build_layers:
            # Bounding box computation
            xmin = float("inf")
            ymin = float("inf")
            zmin = 0
            xmax = float("-inf")
            ymax = float("-inf")
            zmax = float("-inf")
            # Also compute extrusion-only values
            xmin_e = float("inf")
            ymin_e = float("inf")
            xmax_e = float("-inf")
            ymax_e = float("-inf")

            # Duration estimation
            # TODO:
            # get device caps from firmware: max speed, acceleration/axis
            # (including extruder)
            # calculate the maximum move duration accounting for above ;)
            lastx = lasty = lastz = laste = lastf = 0.0
            lastdx = 0
            lastdy = 0
            x = y = e = f = 0.0
            currenttravel = 0.0
            moveduration = 0.0
            totalduration = 0.0
            acceleration = 2000.0  # mm/s^2
            layerbeginduration = 0.0

            # Initialize layers
            all_layers = self.all_layers = []
            all_zs = self.all_zs = set()
            layer_idxs = self.layer_idxs = []
            line_idxs = self.line_idxs = []

            layer_id = 0
            layer_line = 0

            last_layer_z = None
            prev_z = None
            prev_base_z = (None, None)
            cur_z = None
            cur_lines = []

        if self.line_class != Line:
            get_line = lambda l: Line(l.raw)
        else:
            get_line = lambda l: l
        for true_line in lines:
            # # Parse line
            # Use a heavy copy of the light line to preprocess
            line = get_line(true_line)
            split_raw = split(line)
            if line.command:
                # Update properties
                if line.is_move:
                    line.relative = relative
                    line.relative_e = relative_e
                    line.current_tool = current_tool
                elif line.command == "G20":
                    imperial = True
                elif line.command == "G21":
                    imperial = False
                elif line.command == "G90":
                    relative = False
                    relative_e = False
                elif line.command == "G91":
                    relative = True
                    relative_e = True
                elif line.command == "M82":
                    relative_e = False
                elif line.command == "M83":
                    relative_e = True
                elif line.command[0] == "T":
                    current_tool = int(line.command[1:])

                if line.command[0] == "G":
                    parse_coordinates(line, split_raw, imperial)

                # Compute current position
                if line.is_move:
                    x = line.x
                    y = line.y
                    z = line.z

                    if line.f is not None:
                        self.current_f = line.f

                    if line.relative:
                        x = current_x + (x or 0)
                        y = current_y + (y or 0)
                        z = current_z + (z or 0)
                    else:
                        if x is not None: x = x + offset_x
                        if y is not None: y = y + offset_y
                        if z is not None: z = z + offset_z

                    if x is not None: current_x = x
                    if y is not None: current_y = y
                    if z is not None: current_z = z

                elif line.command == "G28":
                    home_all = not any([line.x, line.y, line.z])
                    if home_all or line.x is not None:
                        offset_x = 0
                        current_x = self.home_x
                    if home_all or line.y is not None:
                        offset_y = 0
                        current_y = self.home_y
                    if home_all or line.z is not None:
                        offset_z = 0
                        current_z = self.home_z

                elif line.command == "G92":
                    if line.x is not None: offset_x = current_x - line.x
                    if line.y is not None: offset_y = current_y - line.y
                    if line.z is not None: offset_z = current_z - line.z

                line.current_x = current_x
                line.current_y = current_y
                line.current_z = current_z

                # # Process extrusion
                if line.e is not None:
                    if line.is_move:
                        if line.relative_e:
                            line.extruding = line.e > 0
                            total_e += line.e
                            current_e += line.e
                        else:
                            new_e = line.e + offset_e
                            line.extruding = new_e > current_e
                            total_e += new_e - current_e
                            current_e = new_e
                        max_e = max(max_e, total_e)
                        cur_layer_has_extrusion |= line.extruding
                    elif line.command == "G92":
                        offset_e = current_e - line.e

                # # Create layers and perform global computations
                if build_layers:
                    # Update bounding box
                    if line.is_move:
                        if line.extruding:
                            if line.current_x is not None:
                                xmin_e = min(xmin_e, line.current_x)
                                xmax_e = max(xmax_e, line.current_x)
                            if line.current_y is not None:
                                ymin_e = min(ymin_e, line.current_y)
                                ymax_e = max(ymax_e, line.current_y)
                        if max_e <= 0:
                            if line.current_x is not None:
                                xmin = min(xmin, line.current_x)
                                xmax = max(xmax, line.current_x)
                            if line.current_y is not None:
                                ymin = min(ymin, line.current_y)
                                ymax = max(ymax, line.current_y)

                    # Compute duration
                    if line.command in ["G1", "G0", "G4"]:
                        if line.command == "G4":
                            moveduration = P(line)
                            if moveduration:
                                moveduration /= 1000.0
                                totalduration += moveduration
                        else:
                            x = line.x if line.x is not None else lastx
                            y = line.y if line.y is not None else lasty
                            z = line.z if line.z is not None else lastz
                            e = line.e if line.e is not None else laste
                            # mm/s vs mm/m => divide by 60
                            f = line.f / 60.0 if line.f is not None else lastf

                            # given last feedrate and current feedrate calculate the
                            # distance needed to achieve current feedrate.
                            # if travel is longer than req'd distance, then subtract
                            # distance to achieve full speed, and add the time it took
                            # to get there.
                            # then calculate the time taken to complete the remaining
                            # distance

                            # FIXME: this code has been proven to be super wrong when 2
                            # subsquent moves are in opposite directions, as requested
                            # speed is constant but printer has to fully decellerate
                            # and reaccelerate
                            # The following code tries to fix it by forcing a full
                            # reacceleration if this move is in the opposite direction
                            # of the previous one
                            dx = x - lastx
                            dy = y - lasty
                            if dx * lastdx + dy * lastdy <= 0:
                                lastf = 0

                            currenttravel = math.hypot(dx, dy)
                            if currenttravel == 0:
                                if line.z is not None:
                                    currenttravel = abs(line.z) if line.relative else abs(line.z - lastz)
                                elif line.e is not None:
                                    currenttravel = abs(line.e) if line.relative_e else abs(line.e - laste)
                            # Feedrate hasn't changed, no acceleration/decceleration planned
                            if f == lastf:
                                moveduration = currenttravel / f if f != 0 else 0.
                            else:
                                # FIXME: review this better
                                # this looks wrong : there's little chance that the feedrate we'll decelerate to is the previous feedrate
                                # shouldn't we instead look at three consecutive moves ?
                                distance = 2 * abs(((lastf + f) * (f - lastf) * 0.5) / acceleration)  # multiply by 2 because we have to accelerate and decelerate
                                if distance <= currenttravel and lastf + f != 0 and f != 0:
                                    moveduration = 2 * distance / (lastf + f)  # This is distance / mean(lastf, f)
                                    moveduration += (currenttravel - distance) / f
                                else:
                                    moveduration = 2 * currenttravel / (lastf + f)  # This is currenttravel / mean(lastf, f)
                                    # FIXME: probably a little bit optimistic, but probably a much better estimate than the previous one:
                                    # moveduration = math.sqrt(2 * distance / acceleration) # probably buggy : not taking actual travel into account

                            lastdx = dx
                            lastdy = dy

                            totalduration += moveduration

                            lastx = x
                            lasty = y
                            lastz = z
                            laste = e
                            lastf = f

                    # FIXME : looks like this needs to be tested with "lift Z on move"
                    if line.z is not None:
                        if line.command == "G92":
                            cur_z = line.z
                        elif line.is_move:
                            if line.relative and cur_z is not None:
                                cur_z += line.z
                            else:
                                cur_z = line.z

                    # FIXME: the logic behind this code seems to work, but it might be
                    # broken
                    if cur_z != prev_z:
                        if prev_z is not None and last_layer_z is not None:
                            offset = self.est_layer_height if self.est_layer_height else 0.01
                            if abs(prev_z - last_layer_z) < offset:
                                if self.est_layer_height is None:
                                    zs = sorted([l.z for l in all_layers if l.z is not None])
                                    heights = [round(zs[i + 1] - zs[i], 3) for i in range(len(zs) - 1)]
                                    heights = [height for height in heights if height]
                                    if len(heights) >= 2: self.est_layer_height = heights[1]
                                    elif heights: self.est_layer_height = heights[0]
                                    else: self.est_layer_height = 0.1
                                base_z = round(prev_z - (prev_z % self.est_layer_height), 2)
                            else:
                                base_z = round(prev_z, 2)
                        else:
                            base_z = prev_z

                        if base_z != prev_base_z:
                            new_layer = Layer(cur_lines, base_z)
                            new_layer.duration = totalduration - layerbeginduration
                            layerbeginduration = totalduration
                            all_layers.append(new_layer)
                            if cur_layer_has_extrusion and prev_z not in all_zs:
                                all_zs.add(prev_z)
                            cur_lines = []
                            cur_layer_has_extrusion = False
                            layer_id += 1
                            layer_line = 0
                            last_layer_z = base_z
                            if layer_callback is not None:
                                layer_callback(self, len(all_layers) - 1)

                        prev_base_z = base_z

            if build_layers:
                cur_lines.append(true_line)
                layer_idxs.append(layer_id)
                line_idxs.append(layer_line)
                layer_line += 1
                prev_z = cur_z
            # ## Loop done

        # Store current status
        self.imperial = imperial
        self.relative = relative
        self.relative_e = relative_e
        self.current_tool = current_tool
        self.current_x = current_x
        self.current_y = current_y
        self.current_z = current_z
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.offset_z = offset_z

        self.current_e = current_e
        self.offset_e = offset_e
        self.max_e = max_e
        self.total_e = total_e

        # Finalize layers
        if build_layers:
            if cur_lines:
                new_layer = Layer(cur_lines, prev_z)
                new_layer.duration = totalduration - layerbeginduration
                layerbeginduration = totalduration
                all_layers.append(new_layer)
                if cur_layer_has_extrusion and prev_z not in all_zs:
                    all_zs.add(prev_z)

            self.append_layer_id = len(all_layers)
            self.append_layer = Layer([])
            self.append_layer.duration = 0
            all_layers.append(self.append_layer)
            self.layer_idxs = array('I', layer_idxs)
            self.line_idxs = array('I', line_idxs)

            # Compute bounding box
            all_zs = self.all_zs.union(set([zmin])).difference(set([None]))
            zmin = min(all_zs)
            zmax = max(all_zs)

            self.filament_length = self.max_e

            if self.filament_length > 0:
                self.xmin = xmin_e if not math.isinf(xmin_e) else 0
                self.xmax = xmax_e if not math.isinf(xmax_e) else 0
                self.ymin = ymin_e if not math.isinf(ymin_e) else 0
                self.ymax = ymax_e if not math.isinf(ymax_e) else 0
            else:
                self.xmin = xmin if not math.isinf(xmin) else 0
                self.xmax = xmax if not math.isinf(xmax) else 0
                self.ymin = ymin if not math.isinf(ymin) else 0
                self.ymax = ymax if not math.isinf(ymax) else 0
            self.zmin = zmin if not math.isinf(zmin) else 0
            self.zmax = zmax if not math.isinf(zmax) else 0
            self.width = self.xmax - self.xmin
            self.depth = self.ymax - self.ymin
            self.height = self.zmax - self.zmin

            # Finalize duration
            totaltime = datetime.timedelta(seconds = int(totalduration))
            self.duration = totaltime

    def idxs(self, i):
        return self.layer_idxs[i], self.line_idxs[i]

    def estimate_duration(self):
        return self.layers_count, self.duration

class LightGCode(GCode):
    line_class = LightLine

def main():
    if len(sys.argv) < 2:
        print "usage: %s filename.gcode" % sys.argv[0]
        return

    print "Line object size:", sys.getsizeof(Line("G0 X0"))
    print "Light line object size:", sys.getsizeof(LightLine("G0 X0"))
    gcode = GCode(open(sys.argv[1], "rU"))

    print "Dimensions:"
    xdims = (gcode.xmin, gcode.xmax, gcode.width)
    print "\tX: %0.02f - %0.02f (%0.02f)" % xdims
    ydims = (gcode.ymin, gcode.ymax, gcode.depth)
    print "\tY: %0.02f - %0.02f (%0.02f)" % ydims
    zdims = (gcode.zmin, gcode.zmax, gcode.height)
    print "\tZ: %0.02f - %0.02f (%0.02f)" % zdims
    print "Filament used: %0.02fmm" % gcode.filament_length
    print "Number of layers: %d" % gcode.layers_count
    print "Estimated duration: %s" % gcode.estimate_duration()[1]

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gcview
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

from . import gcoder
from .gl.panel import wxGLPanel
from .gl.trackball import build_rotmatrix
from .gl.libtatlin import actors
from .injectgcode import injector, injector_edit

from pyglet.gl import glPushMatrix, glPopMatrix, \
    glTranslatef, glRotatef, glScalef, glMultMatrixd, \
    glGetDoublev, GL_MODELVIEW_MATRIX, GLdouble

from .gviz import GvizBaseFrame

from .utils import imagefile, install_locale, get_home_pos
install_locale('pronterface')

def create_model(light):
    if light:
        return actors.GcodeModelLight()
    else:
        return actors.GcodeModel()

def gcode_dims(g):
    return ((g.xmin, g.xmax, g.width),
            (g.ymin, g.ymax, g.depth),
            (g.zmin, g.zmax, g.height))

def set_model_colors(model, root):
    for field in dir(model):
        if field.startswith("color_"):
            root_fieldname = "gcview_" + field
            if hasattr(root, root_fieldname):
                setattr(model, field, getattr(root, root_fieldname))

def recreate_platform(self, build_dimensions, circular):
    self.platform = actors.Platform(build_dimensions, circular = circular)
    self.objects[0].model = self.platform
    wx.CallAfter(self.Refresh)

def set_gcview_params(self, path_width, path_height):
    self.path_halfwidth = path_width / 2
    self.path_halfheight = path_height / 2
    has_changed = False
    for obj in self.objects[1:]:
        if isinstance(obj.model, actors.GcodeModel):
            obj.model.set_path_size(self.path_halfwidth, self.path_halfheight)
            has_changed = True
    return has_changed

class GcodeViewPanel(wxGLPanel):

    def __init__(self, parent, id = wx.ID_ANY,
                 build_dimensions = None, realparent = None,
                 antialias_samples = 0):
        super(GcodeViewPanel, self).__init__(parent, id, wx.DefaultPosition,
                                             wx.DefaultSize, 0,
                                             antialias_samples = antialias_samples)
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.canvas.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.initialized = 0
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = realparent if realparent else parent
        self.initpos = None
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        self.basequat = [0, 0, 0, 1]
        self.mousepos = [0, 0]

    def inject(self):
        l = self.parent.model.num_layers_to_draw
        filtered = [k for k, v in self.parent.model.layer_idxs_map.iteritems() if v == l]
        if filtered:
            injector(self.parent.model.gcode, l, filtered[0])
        else:
            print _("Invalid layer for injection")

    def editlayer(self):
        l = self.parent.model.num_layers_to_draw
        filtered = [k for k, v in self.parent.model.layer_idxs_map.iteritems() if v == l]
        if filtered:
            injector_edit(self.parent.model.gcode, l, filtered[0])
        else:
            print _("Invalid layer for edition")

    def setlayercb(self, layer):
        pass

    def OnInitGL(self, *args, **kwargs):
        super(GcodeViewPanel, self).OnInitGL(*args, **kwargs)
        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        for obj in self.parent.objects:
            if obj.model and obj.model.loaded and not obj.model.initialized:
                obj.model.init()

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        self.create_objects()

        glPushMatrix()
        # Rotate according to trackball
        glMultMatrixd(build_rotmatrix(self.basequat))
        # Move origin to bottom left of platform
        platformx0 = -self.build_dimensions[3] - self.parent.platform.width / 2
        platformy0 = -self.build_dimensions[4] - self.parent.platform.depth / 2
        glTranslatef(platformx0, platformy0, 0)

        for obj in self.parent.objects:
            if not obj.model \
               or not obj.model.loaded \
               or not obj.model.initialized:
                continue
            glPushMatrix()
            glTranslatef(*(obj.offsets))
            glRotatef(obj.rot, 0.0, 0.0, 1.0)
            glTranslatef(*(obj.centeroffset))
            glScalef(*obj.scale)

            obj.model.display()
            glPopMatrix()
        glPopMatrix()

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_modelview_mat(self, local_transform):
        mvmat = (GLdouble * 16)()
        if local_transform:
            glPushMatrix()
            # Rotate according to trackball
            glMultMatrixd(build_rotmatrix(self.basequat))
            # Move origin to bottom left of platform
            platformx0 = -self.build_dimensions[3] - self.parent.platform.width / 2
            platformy0 = -self.build_dimensions[4] - self.parent.platform.depth / 2
            glTranslatef(platformx0, platformy0, 0)
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    def double(self, event):
        if hasattr(self.parent, "clickcb") and self.parent.clickcb:
            self.parent.clickcb(event)

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: rotate viewport
        RMB: move viewport
        """
        if event.Entering():
            self.canvas.SetFocus()
            event.Skip()
            return
        if event.Dragging() and event.LeftIsDown():
            self.handle_rotation(event)
        elif event.Dragging() and event.RightIsDown():
            self.handle_translation(event)
        elif event.LeftUp():
            self.initpos = None
        elif event.RightUp():
            self.initpos = None
        else:
            event.Skip()
            return
        event.Skip()
        wx.CallAfter(self.Refresh)

    def layerup(self):
        if not self.parent.model:
            return
        max_layers = self.parent.model.max_layers
        current_layer = self.parent.model.num_layers_to_draw
        # accept going up to max_layers + 1
        # max_layers means visualizing the last layer differently,
        # max_layers + 1 means visualizing all layers with the same color
        new_layer = min(max_layers + 1, current_layer + 1)
        self.parent.model.num_layers_to_draw = new_layer
        self.parent.setlayercb(new_layer)
        wx.CallAfter(self.Refresh)

    def layerdown(self):
        if not self.parent.model:
            return
        current_layer = self.parent.model.num_layers_to_draw
        new_layer = max(1, current_layer - 1)
        self.parent.model.num_layers_to_draw = new_layer
        self.parent.setlayercb(new_layer)
        wx.CallAfter(self.Refresh)

    def handle_wheel(self, event):
        delta = event.GetWheelRotation()
        factor = 1.05
        if hasattr(self.parent, "model") and event.ShiftDown():
            if not self.parent.model:
                return
            count = 1 if not event.ControlDown() else 10
            for i in range(count):
                if delta > 0: self.layerup()
                else: self.layerdown()
            return
        x, y = event.GetPositionTuple()
        x, y, _ = self.mouse_to_3d(x, y)
        if delta > 0:
            self.zoom(factor, (x, y))
        else:
            self.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """react to mouse wheel actions:
            without shift: set max layer
            with shift: zoom viewport
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def fit(self):
        if not self.parent.model or not self.parent.model.loaded:
            return
        self.canvas.SetCurrent(self.context)
        dims = gcode_dims(self.parent.model.gcode)
        self.reset_mview(1.0)
        center_x = (dims[0][0] + dims[0][1]) / 2
        center_y = (dims[1][0] + dims[1][1]) / 2
        center_x = self.build_dimensions[0] / 2 - center_x
        center_y = self.build_dimensions[1] / 2 - center_y
        if self.orthographic:
            ratio = float(self.dist) / max(dims[0][2], dims[1][2])
            glScalef(ratio, ratio, 1)
        glTranslatef(center_x, center_y, 0)
        wx.CallAfter(self.Refresh)

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        step = 1.1
        if event.ControlDown():
            step = 1.05
        kup = [85, 315]               # Up keys
        kdo = [68, 317]               # Down Keys
        kzi = [wx.WXK_PAGEDOWN, 388, 316, 61]        # Zoom In Keys
        kzo = [wx.WXK_PAGEUP, 390, 314, 45]       # Zoom Out Keys
        kfit = [70]       # Fit to print keys
        kshowcurrent = [67]       # Show only current layer keys
        kreset = [82]       # Reset keys
        key = event.GetKeyCode()
        if key in kup:
            self.layerup()
        if key in kdo:
            self.layerdown()
        x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        if key in kzi:
            self.zoom_to_center(step)
        if key in kzo:
            self.zoom_to_center(1 / step)
        if key in kfit:
            self.fit()
        if key in kshowcurrent:
            if not self.parent.model or not self.parent.model.loaded:
                return
            self.parent.model.only_current = not self.parent.model.only_current
            wx.CallAfter(self.Refresh)
        if key in kreset:
            self.resetview()
        event.Skip()

    def resetview(self):
        self.canvas.SetCurrent(self.context)
        self.reset_mview(0.9)
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.Refresh)

class GCObject(object):

    def __init__(self, model):
        self.offsets = [0, 0, 0]
        self.centeroffset = [0, 0, 0]
        self.rot = 0
        self.curlayer = 0.0
        self.scale = [1.0, 1.0, 1.0]
        self.model = model

class GcodeViewLoader(object):

    path_halfwidth = 0.2
    path_halfheight = 0.15

    def addfile_perlayer(self, gcode = None, showall = False):
        self.model = create_model(self.root.settings.light3d
                                  if self.root else False)
        if isinstance(self.model, actors.GcodeModel):
            self.model.set_path_size(self.path_halfwidth, self.path_halfheight)
        self.objects[-1].model = self.model
        if self.root:
            set_model_colors(self.model, self.root)
        if gcode is not None:
            generator = self.model.load_data(gcode)
            generator_output = generator.next()
            while generator_output is not None:
                yield generator_output
                generator_output = generator.next()
        wx.CallAfter(self.Refresh)
        yield None

    def addfile(self, gcode = None, showall = False):
        generator = self.addfile_perlayer(gcode, showall)
        while generator.next() is not None:
            continue

    def set_gcview_params(self, path_width, path_height):
        return set_gcview_params(self, path_width, path_height)

class GcodeViewMainWrapper(GcodeViewLoader):

    def __init__(self, parent, build_dimensions, root, circular, antialias_samples):
        self.root = root
        self.glpanel = GcodeViewPanel(parent, realparent = self,
                                      build_dimensions = build_dimensions,
                                      antialias_samples = antialias_samples)
        self.glpanel.SetMinSize((150, 150))
        if self.root and hasattr(self.root, "gcview_color_background"):
            self.glpanel.color_background = self.root.gcview_color_background
        self.clickcb = None
        self.widget = self.glpanel
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.platform = actors.Platform(build_dimensions, circular = circular)
        self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

    def __getattr__(self, name):
        return getattr(self.glpanel, name)

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def recreate_platform(self, build_dimensions, circular):
        return recreate_platform(self, build_dimensions, circular)

    def addgcodehighlight(self, *a):
        pass

    def setlayer(self, layer):
        if layer in self.model.layer_idxs_map:
            viz_layer = self.model.layer_idxs_map[layer]
            self.parent.model.num_layers_to_draw = viz_layer
            wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

class GcodeViewFrame(GvizBaseFrame, GcodeViewLoader):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, build_dimensions, objects = None,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.DEFAULT_FRAME_STYLE, root = None, circular = False,
                 antialias_samples = 0):
        GvizBaseFrame.__init__(self, parent, ID, title,
                               pos, size, style)
        self.root = root

        panel, vbox = self.create_base_ui()

        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.clonefrom = objects
        self.platform = actors.Platform(build_dimensions, circular = circular)
        if objects:
            self.model = objects[1].model
        else:
            self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

        fit_image = wx.Image(imagefile('fit.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.toolbar.InsertLabelTool(6, 8, " " + _("Fit to plate"), fit_image,
                                     shortHelp = _("Fit to plate [F]"),
                                     longHelp = '')
        self.toolbar.Realize()
        self.glpanel = GcodeViewPanel(panel,
                                      build_dimensions = build_dimensions,
                                      realparent = self,
                                      antialias_samples = antialias_samples)
        vbox.Add(self.glpanel, 1, flag = wx.EXPAND)

        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.resetview(), id = 5)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.fit(), id = 8)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.inject(), id = 6)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.editlayer(), id = 7)

    def setlayercb(self, layer):
        self.layerslider.SetValue(layer)
        self.update_status("")

    def update_status(self, extra):
        layer = self.model.num_layers_to_draw
        filtered = [k for k, v in self.model.layer_idxs_map.iteritems() if v == layer]
        if filtered:
            z = filtered[0]
            message = _("Layer %d -%s Z = %.03f mm") % (layer + 1, extra, z)
        else:
            message = _("Entire object")
        wx.CallAfter(self.SetStatusText, message, 0)

    def process_slider(self, event):
        new_layer = self.layerslider.GetValue()
        new_layer = min(self.model.max_layers + 1, new_layer)
        new_layer = max(1, new_layer)
        self.model.num_layers_to_draw = new_layer
        self.update_status("")
        wx.CallAfter(self.Refresh)

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def recreate_platform(self, build_dimensions, circular):
        return recreate_platform(self, build_dimensions, circular)

    def addfile(self, gcode = None):
        if self.clonefrom:
            self.model = self.clonefrom[-1].model.copy()
            self.objects[-1].model = self.model
        else:
            GcodeViewLoader.addfile(self, gcode)
        self.layerslider.SetRange(1, self.model.max_layers + 1)
        self.layerslider.SetValue(self.model.max_layers + 1)
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

if __name__ == "__main__":
    import sys
    app = wx.App(redirect = False)
    build_dimensions = [200, 200, 100, 0, 0, 0]
    title = 'Gcode view, shift to move view, mousewheel to set layer'
    frame = GcodeViewFrame(None, wx.ID_ANY, title, size = (400, 400),
                           build_dimensions = build_dimensions)
    gcode = gcoder.GCode(open(sys.argv[1]), get_home_pos(build_dimensions))
    frame.addfile(gcode)

    first_move = None
    for i in range(len(gcode.lines)):
        if gcode.lines[i].is_move:
            first_move = gcode.lines[i]
            break
    last_move = None
    for i in range(len(gcode.lines) - 1, -1, -1):
        if gcode.lines[i].is_move:
            last_move = gcode.lines[i]
            break
    nsteps = 20
    steptime = 500
    lines = [first_move] + [gcode.lines[int(float(i) * (len(gcode.lines) - 1) / nsteps)] for i in range(1, nsteps)] + [last_move]
    current_line = 0

    def setLine():
        global current_line
        frame.set_current_gline(lines[current_line])
        current_line = (current_line + 1) % len(lines)
        timer.Start()
    timer = wx.CallLater(steptime, setLine)
    timer.Start()

    frame.Show(True)
    app.MainLoop()
    app.Destroy()

########NEW FILE########
__FILENAME__ = actors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Guillaume Seguin
# Copyright (C) 2011 Denis Kobozev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import time
import numpy
import math
import logging
import threading

from ctypes import sizeof

from pyglet.gl import glPushMatrix, glPopMatrix, glTranslatef, \
    glGenLists, glNewList, GL_COMPILE, glEndList, glCallList, \
    GL_ELEMENT_ARRAY_BUFFER, GL_UNSIGNED_INT, GL_TRIANGLES, GL_LINE_LOOP, \
    GL_ARRAY_BUFFER, GL_STATIC_DRAW, glColor4f, glVertex3f, \
    glBegin, glEnd, GL_LINES, glEnable, glDisable, glGetFloatv, \
    GL_LINE_SMOOTH, glLineWidth, GL_LINE_WIDTH, GLfloat, GL_FLOAT, GLuint, \
    glVertexPointer, glColorPointer, glDrawArrays, glDrawRangeElements, \
    glEnableClientState, glDisableClientState, GL_VERTEX_ARRAY, GL_COLOR_ARRAY, \
    GL_FRONT_AND_BACK, GL_FRONT, glMaterialfv, GL_SPECULAR, GL_EMISSION, \
    glColorMaterial, GL_AMBIENT_AND_DIFFUSE, glMaterialf, GL_SHININESS, \
    GL_NORMAL_ARRAY, glNormalPointer, GL_LIGHTING, glColor3f
from pyglet.graphics.vertexbuffer import create_buffer, VertexBufferObject

from printrun.utils import install_locale
install_locale('pronterface')

def vec(*args):
    return (GLfloat * len(args))(*args)

def compile_display_list(func, *options):
    display_list = glGenLists(1)
    glNewList(display_list, GL_COMPILE)
    func(*options)
    glEndList()
    return display_list

def numpy2vbo(nparray, target = GL_ARRAY_BUFFER, usage = GL_STATIC_DRAW, use_vbos = True):
    vbo = create_buffer(nparray.nbytes, target = target, usage = usage, vbo = use_vbos)
    vbo.bind()
    vbo.set_data(nparray.ctypes.data)
    return vbo

def triangulate_rectangle(i1, i2, i3, i4):
    return [i1, i4, i3, i3, i2, i1]

def triangulate_box(i1, i2, i3, i4,
                    j1, j2, j3, j4):
    return [i1, i2, j2, j2, j1, i1, i2, i3, j3, j3, j2, i2,
            i3, i4, j4, j4, j3, i3, i4, i1, j1, j1, j4, i4]

class BoundingBox(object):
    """
    A rectangular box (cuboid) enclosing a 3D model, defined by lower and upper corners.
    """
    def __init__(self, upper_corner, lower_corner):
        self.upper_corner = upper_corner
        self.lower_corner = lower_corner

    @property
    def width(self):
        width = abs(self.upper_corner[0] - self.lower_corner[0])
        return round(width, 2)

    @property
    def depth(self):
        depth = abs(self.upper_corner[1] - self.lower_corner[1])
        return round(depth, 2)

    @property
    def height(self):
        height = abs(self.upper_corner[2] - self.lower_corner[2])
        return round(height, 2)


class Platform(object):
    """
    Platform on which models are placed.
    """
    graduations_major = 10

    def __init__(self, build_dimensions, light = False, circular = False):
        self.light = light
        self.circular = circular
        self.width = build_dimensions[0]
        self.depth = build_dimensions[1]
        self.height = build_dimensions[2]
        self.xoffset = build_dimensions[3]
        self.yoffset = build_dimensions[4]
        self.zoffset = build_dimensions[5]

        self.color_grads_minor = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.1)
        self.color_grads_interm = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.2)
        self.color_grads_major = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.33)

        self.initialized = False
        self.loaded = True

    def init(self):
        self.display_list = compile_display_list(self.draw)
        self.initialized = True

    def draw(self):
        glPushMatrix()

        glTranslatef(self.xoffset, self.yoffset, self.zoffset)

        def color(i):
            if i % self.graduations_major == 0:
                glColor4f(*self.color_grads_major)
            elif i % (self.graduations_major / 2) == 0:
                glColor4f(*self.color_grads_interm)
            else:
                if self.light: return False
                glColor4f(*self.color_grads_minor)
            return True

        # draw the grid
        glBegin(GL_LINES)
        if self.circular:  # Draw a circular grid
            for i in range(0, int(math.ceil(self.width + 1))):
                angle = math.asin(2 * float(i) / self.width - 1)
                x = (math.cos(angle) + 1) * self.depth / 2
                if color(i):
                    glVertex3f(float(i), self.depth - x, 0.0)
                    glVertex3f(float(i), x, 0.0)

            for i in range(0, int(math.ceil(self.depth + 1))):
                angle = math.acos(2 * float(i) / self.depth - 1)
                x = (math.sin(angle) + 1) * self.width / 2
                if color(i):
                    glVertex3f(self.width - x, float(i), 0.0)
                    glVertex3f(x, float(i), 0.0)
        else:  # Draw a rectangular grid
            for i in range(0, int(math.ceil(self.width + 1))):
                if color(i):
                    glVertex3f(float(i), 0.0, 0.0)
                    glVertex3f(float(i), self.depth, 0.0)

            for i in range(0, int(math.ceil(self.depth + 1))):
                if color(i):
                    glVertex3f(0, float(i), 0.0)
                    glVertex3f(self.width, float(i), 0.0)
        glEnd()

        if self.circular:
            glBegin(GL_LINE_LOOP)
            for i in range(0, 360):
                angle = math.radians(i)
                glVertex3f((math.cos(angle) + 1) * self.width / 2,
                           (math.sin(angle) + 1) * self.depth / 2, 0.0)
            glEnd()

        glPopMatrix()

    def display(self, mode_2d=False):
        # FIXME: using the list sometimes results in graphical corruptions
        # glCallList(self.display_list)
        self.draw()

class PrintHead(object):
    def __init__(self):
        self.color = (43. / 255, 0., 175. / 255, 1.0)
        self.scale = 5
        self.height = 5

        self.initialized = False
        self.loaded = True

    def init(self):
        self.display_list = compile_display_list(self.draw)
        self.initialized = True

    def draw(self):
        glPushMatrix()

        glBegin(GL_LINES)
        glColor4f(*self.color)
        for di in [-1, 1]:
            for dj in [-1, 1]:
                glVertex3f(0, 0, 0)
                glVertex3f(self.scale * di, self.scale * dj, self.height)
        glEnd()

        glPopMatrix()

    def display(self, mode_2d=False):
        glEnable(GL_LINE_SMOOTH)
        orig_linewidth = (GLfloat)()
        glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
        glLineWidth(3.0)
        glCallList(self.display_list)
        glLineWidth(orig_linewidth)
        glDisable(GL_LINE_SMOOTH)

class Model(object):
    """
    Parent class for models that provides common functionality.
    """
    AXIS_X = (1, 0, 0)
    AXIS_Y = (0, 1, 0)
    AXIS_Z = (0, 0, 1)

    letter_axis_map = {
        'x': AXIS_X,
        'y': AXIS_Y,
        'z': AXIS_Z,
    }

    axis_letter_map = dict([(v, k) for k, v in letter_axis_map.items()])

    lock = None

    def __init__(self, offset_x=0, offset_y=0):
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.lock = threading.Lock()

        self.init_model_attributes()

    def init_model_attributes(self):
        """
        Set/reset saved properties.
        """
        self.invalidate_bounding_box()
        self.modified = False

    def invalidate_bounding_box(self):
        self._bounding_box = None

    @property
    def bounding_box(self):
        """
        Get a bounding box for the model.
        """
        if self._bounding_box is None:
            self._bounding_box = self._calculate_bounding_box()
        return self._bounding_box

    def _calculate_bounding_box(self):
        """
        Calculate an axis-aligned box enclosing the model.
        """
        # swap rows and columns in our vertex arrays so that we can do max and
        # min on axis 1
        xyz_rows = self.vertices.reshape(-1, order='F').reshape(3, -1)
        lower_corner = xyz_rows.min(1)
        upper_corner = xyz_rows.max(1)
        box = BoundingBox(upper_corner, lower_corner)
        return box

    @property
    def width(self):
        return self.bounding_box.width

    @property
    def depth(self):
        return self.bounding_box.depth

    @property
    def height(self):
        return self.bounding_box.height

    def movement_color(self, move):
        """
        Return the color to use for particular type of movement.
        """
        if move.extruding:
            if move.current_tool == 0:
                return self.color_tool0
            elif move.current_tool == 1:
                return self.color_tool1
            elif move.current_tool == 2:
                return self.color_tool2
            elif move.current_tool == 3:
                return self.color_tool3
            else:
                return self.color_tool4

        return self.color_travel

def movement_angle(src, dst, precision=0):
    x = dst[0] - src[0]
    y = dst[1] - src[1]
    angle = math.degrees(math.atan2(y, -x))  # negate x for clockwise rotation angle
    return round(angle, precision)

def get_next_move(gcode, layer_idx, gline_idx):
    gline_idx += 1
    while layer_idx < len(gcode.all_layers):
        layer = gcode.all_layers[layer_idx]
        while gline_idx < len(layer):
            gline = layer[gline_idx]
            if gline.is_move:
                return gline
            gline_idx += 1
        layer_idx += 1
        gline_idx = 0
    return None

class GcodeModel(Model):
    """
    Model for displaying Gcode data.
    """

    color_travel = (0.6, 0.6, 0.6, 0.6)
    color_tool0 = (1.0, 0.0, 0.0, 1.0)
    color_tool1 = (0.67, 0.05, 0.9, 1.0)
    color_tool2 = (1.0, 0.8, 0., 1.0)
    color_tool3 = (1.0, 0., 0.62, 1.0)
    color_tool4 = (0., 1.0, 0.58, 1.0)
    color_printed = (0.2, 0.75, 0, 1.0)
    color_current = (0, 0.9, 1.0, 1.0)
    color_current_printed = (0.1, 0.4, 0, 1.0)

    display_travels = True

    buffers_created = False
    use_vbos = True
    loaded = False

    gcode = None

    path_halfwidth = 0.2
    path_halfheight = 0.2

    def set_path_size(self, path_halfwidth, path_halfheight):
        with self.lock:
            self.path_halfwidth = path_halfwidth
            self.path_halfheight = path_halfheight

    def load_data(self, model_data, callback=None):
        t_start = time.time()
        self.gcode = model_data

        self.count_travel_indices = count_travel_indices = [0]
        self.count_print_indices = count_print_indices = [0]
        self.count_print_vertices = count_print_vertices = [0]

        # Some trivial computations, but that's mostly for documentation :)
        # Not like 10 multiplications are going to cost much time vs what's
        # about to happen :)

        # Max number of values which can be generated per gline
        # to store coordinates/colors/normals.
        # Nicely enough we have 3 per kind of thing for all kinds.
        coordspervertex = 3
        verticesperline = 8
        coordsperline = coordspervertex * verticesperline
        coords_count = lambda nlines: nlines * coordsperline

        travelverticesperline = 2
        travelcoordsperline = coordspervertex * travelverticesperline
        travel_coords_count = lambda nlines: nlines * travelcoordsperline

        trianglesperface = 2
        facesperbox = 4
        trianglesperbox = trianglesperface * facesperbox
        verticespertriangle = 3
        indicesperbox = verticespertriangle * trianglesperbox
        boxperline = 2
        indicesperline = indicesperbox * boxperline
        indices_count = lambda nlines: nlines * indicesperline

        nlines = len(model_data)
        ntravelcoords = travel_coords_count(nlines)
        ncoords = coords_count(nlines)
        nindices = indices_count(nlines)
        travel_vertices = self.travels = numpy.zeros(ntravelcoords, dtype = GLfloat)
        travel_vertex_k = 0
        vertices = self.vertices = numpy.zeros(ncoords, dtype = GLfloat)
        vertex_k = 0
        colors = self.colors = numpy.zeros(ncoords, dtype = GLfloat)
        color_k = 0
        normals = self.normals = numpy.zeros(ncoords, dtype = GLfloat)
        normal_k = 0
        indices = self.indices = numpy.zeros(nindices, dtype = GLuint)
        index_k = 0
        self.layer_idxs_map = {}
        self.layer_stops = [0]

        prev_is_extruding = False
        prev_move_normal_x = None
        prev_move_normal_y = None
        prev_move_angle = None

        prev_pos = (0, 0, 0)
        layer_idx = 0

        self.printed_until = 0
        self.only_current = False

        twopi = 2 * math.pi

        processed_lines = 0

        while layer_idx < len(model_data.all_layers):
            with self.lock:
                nlines = len(model_data)
                remaining_lines = nlines - processed_lines
                # Only reallocate memory which might be needed, not memory
                # for everything
                ntravelcoords = coords_count(remaining_lines) + travel_vertex_k
                ncoords = coords_count(remaining_lines) + vertex_k
                nindices = indices_count(remaining_lines) + index_k
                if ncoords > vertices.size:
                    self.travels.resize(ntravelcoords, refcheck = False)
                    self.vertices.resize(ncoords, refcheck = False)
                    self.colors.resize(ncoords, refcheck = False)
                    self.normals.resize(ncoords, refcheck = False)
                    self.indices.resize(nindices, refcheck = False)
                layer = model_data.all_layers[layer_idx]
                has_movement = False
                for gline_idx, gline in enumerate(layer):
                    if not gline.is_move:
                        continue
                    if gline.x is None and gline.y is None and gline.z is None:
                        continue
                    has_movement = True
                    current_pos = (gline.current_x, gline.current_y, gline.current_z)
                    if not gline.extruding:
                        travel_vertices[travel_vertex_k] = prev_pos[0]
                        travel_vertices[travel_vertex_k + 1] = prev_pos[1]
                        travel_vertices[travel_vertex_k + 2] = prev_pos[2]
                        travel_vertices[travel_vertex_k + 3] = current_pos[0]
                        travel_vertices[travel_vertex_k + 4] = current_pos[1]
                        travel_vertices[travel_vertex_k + 5] = current_pos[2]
                        travel_vertex_k += 6
                        prev_is_extruding = False
                    else:
                        gline_color = self.movement_color(gline)

                        next_move = get_next_move(model_data, layer_idx, gline_idx)
                        next_is_extruding = (next_move.extruding
                                             if next_move is not None else False)

                        delta_x = current_pos[0] - prev_pos[0]
                        delta_y = current_pos[1] - prev_pos[1]
                        norm = delta_x * delta_x + delta_y * delta_y
                        if norm == 0:  # Don't draw anything if this move is Z+E only
                            continue
                        norm = math.sqrt(norm)
                        move_normal_x = - delta_y / norm
                        move_normal_y = delta_x / norm
                        move_angle = math.atan2(delta_y, delta_x)

                        # FIXME: compute these dynamically
                        path_halfwidth = self.path_halfwidth * 1.2
                        path_halfheight = self.path_halfheight * 1.2

                        new_indices = []
                        new_vertices = []
                        new_normals = []
                        if prev_is_extruding:
                            # Store previous vertices indices
                            prev_id = vertex_k / 3 - 4
                            avg_move_normal_x = (prev_move_normal_x + move_normal_x) / 2
                            avg_move_normal_y = (prev_move_normal_y + move_normal_y) / 2
                            norm = avg_move_normal_x * avg_move_normal_x + avg_move_normal_y * avg_move_normal_y
                            if norm == 0:
                                avg_move_normal_x = move_normal_x
                                avg_move_normal_y = move_normal_y
                            else:
                                norm = math.sqrt(norm)
                                avg_move_normal_x /= norm
                                avg_move_normal_y /= norm
                            delta_angle = move_angle - prev_move_angle
                            delta_angle = (delta_angle + twopi) % twopi
                            fact = abs(math.cos(delta_angle / 2))
                            # If move is turning too much, avoid creating a big peak
                            # by adding an intermediate box
                            if fact < 0.5:
                                # FIXME: It looks like there's some heavy code duplication here...
                                hw = path_halfwidth
                                p1x = prev_pos[0] - hw * prev_move_normal_x
                                p2x = prev_pos[0] + hw * prev_move_normal_x
                                p1y = prev_pos[1] - hw * prev_move_normal_y
                                p2y = prev_pos[1] + hw * prev_move_normal_y
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] + path_halfheight))
                                new_vertices.extend((p1x, p1y, prev_pos[2]))
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] - path_halfheight))
                                new_vertices.extend((p2x, p2y, prev_pos[2]))
                                new_normals.extend((0, 0, 1))
                                new_normals.extend((-prev_move_normal_x, -prev_move_normal_y, 0))
                                new_normals.extend((0, 0, -1))
                                new_normals.extend((prev_move_normal_x, prev_move_normal_y, 0))
                                first = vertex_k / 3
                                # Link to previous
                                new_indices += triangulate_box(prev_id, prev_id + 1,
                                                               prev_id + 2, prev_id + 3,
                                                               first, first + 1,
                                                               first + 2, first + 3)
                                p1x = prev_pos[0] - hw * move_normal_x
                                p2x = prev_pos[0] + hw * move_normal_x
                                p1y = prev_pos[1] - hw * move_normal_y
                                p2y = prev_pos[1] + hw * move_normal_y
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] + path_halfheight))
                                new_vertices.extend((p1x, p1y, prev_pos[2]))
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] - path_halfheight))
                                new_vertices.extend((p2x, p2y, prev_pos[2]))
                                new_normals.extend((0, 0, 1))
                                new_normals.extend((-move_normal_x, -move_normal_y, 0))
                                new_normals.extend((0, 0, -1))
                                new_normals.extend((move_normal_x, move_normal_y, 0))
                                prev_id += 4
                                first += 4
                                # Link to previous
                                new_indices += triangulate_box(prev_id, prev_id + 1,
                                                               prev_id + 2, prev_id + 3,
                                                               first, first + 1,
                                                               first + 2, first + 3)
                            else:
                                hw = path_halfwidth / fact
                                # Compute vertices
                                p1x = prev_pos[0] - hw * avg_move_normal_x
                                p2x = prev_pos[0] + hw * avg_move_normal_x
                                p1y = prev_pos[1] - hw * avg_move_normal_y
                                p2y = prev_pos[1] + hw * avg_move_normal_y
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] + path_halfheight))
                                new_vertices.extend((p1x, p1y, prev_pos[2]))
                                new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] - path_halfheight))
                                new_vertices.extend((p2x, p2y, prev_pos[2]))
                                new_normals.extend((0, 0, 1))
                                new_normals.extend((-avg_move_normal_x, -avg_move_normal_y, 0))
                                new_normals.extend((0, 0, -1))
                                new_normals.extend((avg_move_normal_x, avg_move_normal_y, 0))
                                first = vertex_k / 3
                                # Link to previous
                                new_indices += triangulate_box(prev_id, prev_id + 1,
                                                               prev_id + 2, prev_id + 3,
                                                               first, first + 1,
                                                               first + 2, first + 3)
                        else:
                            # Compute vertices normal to the current move and cap it
                            p1x = prev_pos[0] - path_halfwidth * move_normal_x
                            p2x = prev_pos[0] + path_halfwidth * move_normal_x
                            p1y = prev_pos[1] - path_halfwidth * move_normal_y
                            p2y = prev_pos[1] + path_halfwidth * move_normal_y
                            new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] + path_halfheight))
                            new_vertices.extend((p1x, p1y, prev_pos[2]))
                            new_vertices.extend((prev_pos[0], prev_pos[1], prev_pos[2] - path_halfheight))
                            new_vertices.extend((p2x, p2y, prev_pos[2]))
                            new_normals.extend((0, 0, 1))
                            new_normals.extend((-move_normal_x, -move_normal_y, 0))
                            new_normals.extend((0, 0, -1))
                            new_normals.extend((move_normal_x, move_normal_y, 0))
                            first = vertex_k / 3
                            new_indices = triangulate_rectangle(first, first + 1,
                                                                first + 2, first + 3)

                        if not next_is_extruding:
                            # Compute caps and link everything
                            p1x = current_pos[0] - path_halfwidth * move_normal_x
                            p2x = current_pos[0] + path_halfwidth * move_normal_x
                            p1y = current_pos[1] - path_halfwidth * move_normal_y
                            p2y = current_pos[1] + path_halfwidth * move_normal_y
                            new_vertices.extend((current_pos[0], current_pos[1], current_pos[2] + path_halfheight))
                            new_vertices.extend((p1x, p1y, current_pos[2]))
                            new_vertices.extend((current_pos[0], current_pos[1], current_pos[2] - path_halfheight))
                            new_vertices.extend((p2x, p2y, current_pos[2]))
                            new_normals.extend((0, 0, 1))
                            new_normals.extend((-move_normal_x, -move_normal_y, 0))
                            new_normals.extend((0, 0, -1))
                            new_normals.extend((move_normal_x, move_normal_y, 0))
                            end_first = vertex_k / 3 + len(new_vertices) / 3 - 4
                            new_indices += triangulate_rectangle(end_first + 3, end_first + 2,
                                                                 end_first + 1, end_first)
                            new_indices += triangulate_box(first, first + 1,
                                                           first + 2, first + 3,
                                                           end_first, end_first + 1,
                                                           end_first + 2, end_first + 3)

                        for new_i, item in enumerate(new_indices):
                            indices[index_k + new_i] = item
                        index_k += len(new_indices)
                        for new_i, item in enumerate(new_vertices):
                            vertices[vertex_k + new_i] = item
                        vertex_k += len(new_vertices)
                        for new_i, item in enumerate(new_normals):
                            normals[normal_k + new_i] = item
                        normal_k += len(new_normals)
                        new_colors = list(gline_color)[:-1] * (len(new_vertices) / 3)
                        for new_i, item in enumerate(new_colors):
                            colors[color_k + new_i] = item
                        color_k += len(new_colors)

                        prev_is_extruding = True
                        prev_move_normal_x = move_normal_x
                        prev_move_normal_y = move_normal_y
                        prev_move_angle = move_angle

                    prev_pos = current_pos
                    count_travel_indices.append(travel_vertex_k / 3)
                    count_print_indices.append(index_k)
                    count_print_vertices.append(vertex_k / 3)
                    gline.gcview_end_vertex = len(count_print_indices) - 1

                if has_movement:
                    self.layer_stops.append(len(count_print_indices) - 1)
                    self.layer_idxs_map[layer_idx] = len(self.layer_stops) - 1
                    self.max_layers = len(self.layer_stops) - 1
                    self.num_layers_to_draw = self.max_layers + 1
                    self.initialized = False
                    self.loaded = True

            processed_lines += len(layer)

            if callback:
                callback(layer_idx + 1)

            yield layer_idx
            layer_idx += 1

        with self.lock:
            self.dims = ((model_data.xmin, model_data.xmax, model_data.width),
                         (model_data.ymin, model_data.ymax, model_data.depth),
                         (model_data.zmin, model_data.zmax, model_data.height))

            self.travels.resize(travel_vertex_k, refcheck = False)
            self.vertices.resize(vertex_k, refcheck = False)
            self.colors.resize(color_k, refcheck = False)
            self.normals.resize(normal_k, refcheck = False)
            self.indices.resize(index_k, refcheck = False)

            self.max_layers = len(self.layer_stops) - 1
            self.num_layers_to_draw = self.max_layers + 1
            self.loaded = True
            self.initialized = False

        t_end = time.time()

        logging.debug(_('Initialized 3D visualization in %.2f seconds') % (t_end - t_start))
        logging.debug(_('Vertex count: %d') % ((len(self.vertices) + len(self.travels)) / 3))
        yield None

    def copy(self):
        copy = GcodeModel()
        for var in ["vertices", "colors", "travels", "indices", "normals",
                    "max_layers", "num_layers_to_draw", "printed_until",
                    "layer_stops", "dims", "only_current",
                    "layer_idxs_map", "count_travel_indices",
                    "count_print_indices", "count_print_vertices",
                    "path_halfwidth", "path_halfheight",
                    "gcode"]:
            setattr(copy, var, getattr(self, var))
        copy.loaded = True
        copy.initialized = False
        return copy

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        with self.lock:
            self.layers_loaded = self.max_layers
            self.initialized = True
            if self.buffers_created:
                self.travel_buffer.delete()
                self.index_buffer.delete()
                self.vertex_buffer.delete()
                self.vertex_color_buffer.delete()
                self.vertex_normal_buffer.delete()
            self.travel_buffer = numpy2vbo(self.travels, use_vbos = self.use_vbos)
            self.index_buffer = numpy2vbo(self.indices, use_vbos = self.use_vbos,
                                          target = GL_ELEMENT_ARRAY_BUFFER)
            self.vertex_buffer = numpy2vbo(self.vertices, use_vbos = self.use_vbos)
            self.vertex_color_buffer = numpy2vbo(self.colors, use_vbos = self.use_vbos)
            self.vertex_normal_buffer = numpy2vbo(self.normals, use_vbos = self.use_vbos)
            self.buffers_created = True

    def display(self, mode_2d=False):
        with self.lock:
            glPushMatrix()
            glTranslatef(self.offset_x, self.offset_y, 0)
            glEnableClientState(GL_VERTEX_ARRAY)

            has_vbo = isinstance(self.vertex_buffer, VertexBufferObject)
            if self.display_travels:
                self._display_travels(has_vbo)

            glEnable(GL_LIGHTING)
            glEnableClientState(GL_NORMAL_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)
            glMaterialfv(GL_FRONT, GL_SPECULAR, vec(1, 1, 1, 1))
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0, 0, 0, 0))
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)

            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
            self._display_movements(has_vbo)

            glDisable(GL_LIGHTING)

            glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)

            glPopMatrix()

    def _display_travels(self, has_vbo):
        self.travel_buffer.bind()
        glVertexPointer(3, GL_FLOAT, 0, self.travel_buffer.ptr)

        # Prevent race condition by using the number of currently loaded layers
        max_layers = self.layers_loaded
        # TODO: show current layer travels in a different color
        end = self.layer_stops[min(self.num_layers_to_draw, max_layers)]
        end_index = self.count_travel_indices[end]
        glColor4f(*self.color_travel)
        if self.only_current:
            if self.num_layers_to_draw < max_layers:
                end_prev_layer = self.layer_stops[self.num_layers_to_draw - 1]
                start_index = self.count_travel_indices[end_prev_layer + 1]
                glDrawArrays(GL_LINES, start_index, end_index - start_index + 1)
        else:
            glDrawArrays(GL_LINES, 0, end_index)

        self.travel_buffer.unbind()

    def _draw_elements(self, start, end, draw_type = GL_TRIANGLES):
        # Don't attempt printing empty layer
        if self.count_print_indices[end] == self.count_print_indices[start - 1]:
            return
        glDrawRangeElements(draw_type,
                            self.count_print_vertices[start - 1],
                            self.count_print_vertices[end] - 1,
                            self.count_print_indices[end] - self.count_print_indices[start - 1],
                            GL_UNSIGNED_INT,
                            sizeof(GLuint) * self.count_print_indices[start - 1])

    def _display_movements(self, has_vbo):
        self.vertex_buffer.bind()
        glVertexPointer(3, GL_FLOAT, 0, self.vertex_buffer.ptr)

        self.vertex_color_buffer.bind()
        glColorPointer(3, GL_FLOAT, 0, self.vertex_color_buffer.ptr)

        self.vertex_normal_buffer.bind()
        glNormalPointer(GL_FLOAT, 0, self.vertex_normal_buffer.ptr)

        self.index_buffer.bind()

        # Prevent race condition by using the number of currently loaded layers
        max_layers = self.layers_loaded

        start = 1
        layer_selected = self.num_layers_to_draw <= max_layers
        if layer_selected:
            end_prev_layer = self.layer_stops[self.num_layers_to_draw - 1]
        else:
            end_prev_layer = 0
        end = self.layer_stops[min(self.num_layers_to_draw, max_layers)]

        glDisableClientState(GL_COLOR_ARRAY)

        glColor3f(*self.color_printed[:-1])

        # Draw printed stuff until end or end_prev_layer
        cur_end = min(self.printed_until, end)
        if not self.only_current:
            if 1 <= end_prev_layer <= cur_end:
                self._draw_elements(1, end_prev_layer)
            elif cur_end >= 1:
                self._draw_elements(1, cur_end)

        glEnableClientState(GL_COLOR_ARRAY)

        # Draw nonprinted stuff until end_prev_layer
        start = max(cur_end, 1)
        if end_prev_layer >= start:
            if not self.only_current:
                self._draw_elements(start, end_prev_layer)
            cur_end = end_prev_layer

        # Draw current layer
        if layer_selected:
            glDisableClientState(GL_COLOR_ARRAY)

            glColor3f(*self.color_current_printed[:-1])

            if cur_end > end_prev_layer:
                self._draw_elements(end_prev_layer + 1, cur_end)

            glColor3f(*self.color_current[:-1])

            if end > cur_end:
                self._draw_elements(cur_end + 1, end)

            glEnableClientState(GL_COLOR_ARRAY)

        # Draw non printed stuff until end (if not ending at a given layer)
        start = max(self.printed_until, 1)
        if not layer_selected and end >= start:
            self._draw_elements(start, end)

        self.vertex_buffer.unbind()
        self.vertex_color_buffer.unbind()
        self.vertex_normal_buffer.unbind()

class GcodeModelLight(Model):
    """
    Model for displaying Gcode data.
    """

    color_travel = (0.6, 0.6, 0.6, 0.6)
    color_tool0 = (1.0, 0.0, 0.0, 0.6)
    color_tool1 = (0.67, 0.05, 0.9, 0.6)
    color_tool2 = (1.0, 0.8, 0., 0.6)
    color_tool3 = (1.0, 0., 0.62, 0.6)
    color_tool4 = (0., 1.0, 0.58, 0.6)
    color_printed = (0.2, 0.75, 0, 0.6)
    color_current = (0, 0.9, 1.0, 0.8)
    color_current_printed = (0.1, 0.4, 0, 0.8)

    buffers_created = False
    use_vbos = True
    loaded = False

    gcode = None

    def load_data(self, model_data, callback=None):
        t_start = time.time()
        self.gcode = model_data

        self.layer_idxs_map = {}
        self.layer_stops = [0]

        prev_pos = (0, 0, 0)
        layer_idx = 0
        nlines = len(model_data)
        vertices = self.vertices = numpy.zeros(nlines * 6, dtype = GLfloat)
        vertex_k = 0
        colors = self.colors = numpy.zeros(nlines * 8, dtype = GLfloat)
        color_k = 0
        self.printed_until = -1
        self.only_current = False
        while layer_idx < len(model_data.all_layers):
            with self.lock:
                nlines = len(model_data)
                if nlines * 6 != vertices.size:
                    self.vertices.resize(nlines * 6, refcheck = False)
                    self.colors.resize(nlines * 8, refcheck = False)
                layer = model_data.all_layers[layer_idx]
                has_movement = False
                for gline in layer:
                    if not gline.is_move:
                        continue
                    if gline.x is None and gline.y is None and gline.z is None:
                        continue
                    has_movement = True
                    vertices[vertex_k] = prev_pos[0]
                    vertices[vertex_k + 1] = prev_pos[1]
                    vertices[vertex_k + 2] = prev_pos[2]
                    current_pos = (gline.current_x, gline.current_y, gline.current_z)
                    vertices[vertex_k + 3] = current_pos[0]
                    vertices[vertex_k + 4] = current_pos[1]
                    vertices[vertex_k + 5] = current_pos[2]
                    vertex_k += 6

                    vertex_color = self.movement_color(gline)
                    colors[color_k] = vertex_color[0]
                    colors[color_k + 1] = vertex_color[1]
                    colors[color_k + 2] = vertex_color[2]
                    colors[color_k + 3] = vertex_color[3]
                    colors[color_k + 4] = vertex_color[0]
                    colors[color_k + 5] = vertex_color[1]
                    colors[color_k + 6] = vertex_color[2]
                    colors[color_k + 7] = vertex_color[3]
                    color_k += 8

                    prev_pos = current_pos
                    gline.gcview_end_vertex = vertex_k / 3

                if has_movement:
                    self.layer_stops.append(vertex_k / 3)
                    self.layer_idxs_map[layer_idx] = len(self.layer_stops) - 1
                    self.max_layers = len(self.layer_stops) - 1
                    self.num_layers_to_draw = self.max_layers + 1
                    self.initialized = False
                    self.loaded = True

            if callback:
                callback(layer_idx + 1)

            yield layer_idx
            layer_idx += 1

        with self.lock:
            self.dims = ((model_data.xmin, model_data.xmax, model_data.width),
                         (model_data.ymin, model_data.ymax, model_data.depth),
                         (model_data.zmin, model_data.zmax, model_data.height))

            self.vertices.resize(vertex_k, refcheck = False)
            self.colors.resize(color_k, refcheck = False)
            self.max_layers = len(self.layer_stops) - 1
            self.num_layers_to_draw = self.max_layers + 1
            self.initialized = False
            self.loaded = True

        t_end = time.time()

        logging.debug(_('Initialized 3D visualization in %.2f seconds') % (t_end - t_start))
        logging.debug(_('Vertex count: %d') % (len(self.vertices) / 3))
        yield None

    def copy(self):
        copy = GcodeModelLight()
        for var in ["vertices", "colors", "max_layers",
                    "num_layers_to_draw", "printed_until",
                    "layer_stops", "dims", "only_current",
                    "layer_idxs_map", "gcode"]:
            setattr(copy, var, getattr(self, var))
        copy.loaded = True
        copy.initialized = False
        return copy

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        with self.lock:
            self.layers_loaded = self.max_layers
            self.initialized = True
            if self.buffers_created:
                self.vertex_buffer.delete()
                self.vertex_color_buffer.delete()
            self.vertex_buffer = numpy2vbo(self.vertices, use_vbos = self.use_vbos)
            self.vertex_color_buffer = numpy2vbo(self.colors, use_vbos = self.use_vbos)  # each pair of vertices shares the color
            self.buffers_created = True

    def display(self, mode_2d=False):
        with self.lock:
            glPushMatrix()
            glTranslatef(self.offset_x, self.offset_y, 0)
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)

            self._display_movements(mode_2d)

            glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)
            glPopMatrix()

    def _display_movements(self, mode_2d=False):
        self.vertex_buffer.bind()
        has_vbo = isinstance(self.vertex_buffer, VertexBufferObject)
        if has_vbo:
            glVertexPointer(3, GL_FLOAT, 0, None)
        else:
            glVertexPointer(3, GL_FLOAT, 0, self.vertex_buffer.ptr)

        self.vertex_color_buffer.bind()
        if has_vbo:
            glColorPointer(4, GL_FLOAT, 0, None)
        else:
            glColorPointer(4, GL_FLOAT, 0, self.vertex_color_buffer.ptr)

        # Prevent race condition by using the number of currently loaded layers
        max_layers = self.layers_loaded

        start = 0
        if self.num_layers_to_draw <= max_layers:
            end_prev_layer = self.layer_stops[self.num_layers_to_draw - 1]
        else:
            end_prev_layer = -1
        end = self.layer_stops[min(self.num_layers_to_draw, max_layers)]

        glDisableClientState(GL_COLOR_ARRAY)

        glColor4f(*self.color_printed)

        # Draw printed stuff until end or end_prev_layer
        cur_end = min(self.printed_until, end)
        if not self.only_current:
            if 0 <= end_prev_layer <= cur_end:
                glDrawArrays(GL_LINES, start, end_prev_layer)
            elif cur_end >= 0:
                glDrawArrays(GL_LINES, start, cur_end)

        glEnableClientState(GL_COLOR_ARRAY)

        # Draw nonprinted stuff until end_prev_layer
        start = max(cur_end, 0)
        if end_prev_layer >= start:
            if not self.only_current:
                glDrawArrays(GL_LINES, start, end_prev_layer - start)
            cur_end = end_prev_layer

        # Draw current layer
        if end_prev_layer >= 0:
            glDisableClientState(GL_COLOR_ARRAY)

            # Backup & increase line width
            orig_linewidth = (GLfloat)()
            glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
            glLineWidth(2.0)

            glColor4f(*self.color_current_printed)

            if cur_end > end_prev_layer:
                glDrawArrays(GL_LINES, end_prev_layer, cur_end - end_prev_layer)

            glColor4f(*self.color_current)

            if end > cur_end:
                glDrawArrays(GL_LINES, cur_end, end - cur_end)

            # Restore line width
            glLineWidth(orig_linewidth)

            glEnableClientState(GL_COLOR_ARRAY)

        # Draw non printed stuff until end (if not ending at a given layer)
        start = max(self.printed_until, 0)
        end = end - start
        if end_prev_layer < 0 and end > 0 and not self.only_current:
            glDrawArrays(GL_LINES, start, end)

        self.vertex_buffer.unbind()
        self.vertex_color_buffer.unbind()

########NEW FILE########
__FILENAME__ = panel
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from threading import Lock
import logging
import sys
import traceback
import numpy
import numpy.linalg

import wx
from wx import glcanvas

import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import glEnable, glDisable, GL_LIGHTING, glLightfv, \
    GL_LIGHT0, GL_LIGHT1, GL_LIGHT2, GL_POSITION, GL_DIFFUSE, \
    GL_AMBIENT, GL_SPECULAR, GL_COLOR_MATERIAL, \
    glShadeModel, GL_SMOOTH, GL_NORMALIZE, \
    GL_BLEND, glBlendFunc, glClear, glClearColor, \
    glClearDepth, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, \
    GL_DEPTH_BUFFER_BIT, glDepthFunc, GL_DEPTH_TEST, \
    GLdouble, glGetDoublev, glGetIntegerv, GLint, \
    GL_LEQUAL, glLoadIdentity, glMatrixMode, GL_MODELVIEW, \
    GL_MODELVIEW_MATRIX, GL_ONE_MINUS_SRC_ALPHA, glOrtho, \
    GL_PROJECTION, GL_PROJECTION_MATRIX, glScalef, \
    GL_SRC_ALPHA, glTranslatef, gluPerspective, gluUnProject, \
    glViewport, GL_VIEWPORT
from pyglet import gl
from .trackball import trackball, mulquat
from .libtatlin.actors import vec

class wxGLPanel(wx.Panel):
    '''A simple class for using OpenGL with wxPython.'''

    orthographic = True
    color_background = (0.98, 0.98, 0.78, 1)
    do_lights = True

    def __init__(self, parent, id, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0,
                 antialias_samples = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(wxGLPanel, self).__init__(parent, id, pos, size, style)

        self.GLinitialized = False
        self.mview_initialized = False
        attribList = (glcanvas.WX_GL_RGBA,  # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER,  # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24)  # 24 bit

        if antialias_samples > 0 and hasattr(glcanvas, "WX_GL_SAMPLE_BUFFERS"):
            attribList += (glcanvas.WX_GL_SAMPLE_BUFFERS, 1,
                           glcanvas.WX_GL_SAMPLES, antialias_samples)

        self.width = None
        self.height = None

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList = attribList)
        self.context = glcanvas.GLContext(self.canvas)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizerAndFit(self.sizer)

        self.rot_lock = Lock()
        self.basequat = [0, 0, 0, 1]
        self.zoom_factor = 1.0

        self.gl_broken = False

        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        if self.IsFrozen():
            event.Skip()
            return
        if (wx.VERSION > (2, 9) and self.canvas.IsShownOnScreen()) or self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            self.canvas.SetCurrent(self.context)
            self.OnReshape()
            self.Refresh(False)
            timer = wx.CallLater(100, self.Refresh)
            timer.Start()
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent(self.context)

        if not self.gl_broken:
            try:
                self.OnInitGL()
                self.OnDraw()
            except pyglet.gl.lib.GLException:
                self.gl_broken = True
                logging.error(_("OpenGL failed, disabling it:"))
                traceback.print_exc(file = sys.stdout)
        event.Skip()

    def Destroy(self):
        # clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        # call the super method
        super(wxGLPanel, self).Destroy()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, call_reshape = True):
        '''Initialize OpenGL for use in the window.'''
        if self.GLinitialized:
            return
        self.GLinitialized = True
        # create a pyglet context for this panel
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
        # normal gl init
        glClearColor(*self.color_background)
        glClearDepth(1.0)                # set depth value to 1
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if call_reshape:
            self.OnReshape()

    def OnReshape(self):
        """Reshape the OpenGL viewport based on the size of the window"""
        size = self.GetClientSize()
        oldwidth, oldheight = self.width, self.height
        width, height = size.width, size.height
        if width < 1 or height < 1:
            return
        self.width = max(float(width), 1.0)
        self.height = max(float(height), 1.0)
        self.OnInitGL(call_reshape = False)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.orthographic:
            glOrtho(-width / 2, width / 2, -height / 2, height / 2,
                    -5 * self.dist, 5 * self.dist)
        else:
            gluPerspective(60., float(width) / height, 10.0, 3 * self.dist)
            glTranslatef(0, 0, -self.dist)  # Move back
        glMatrixMode(GL_MODELVIEW)

        if not self.mview_initialized:
            self.reset_mview(0.9)
            self.mview_initialized = True
        elif oldwidth is not None and oldheight is not None:
            wratio = self.width / oldwidth
            hratio = self.height / oldheight

            factor = min(wratio * self.zoomed_width, hratio * self.zoomed_height)
            x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
            self.zoom(factor, (x, y))
            self.zoomed_width *= wratio / factor
            self.zoomed_height *= hratio / factor

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def setup_lights(self):
        if not self.do_lights:
            return
        glEnable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, vec(0.4, 0.4, 0.4, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(0, 0, 0, 0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(0, 0, 0, 0))
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0, 0, 0, 1.0))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT2, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 2, 3, 0))
        glEnable(GL_LIGHT2)
        glLightfv(GL_LIGHT2, GL_AMBIENT, vec(0, 0, 0, 1.0))
        glLightfv(GL_LIGHT2, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT2, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1))
        glLightfv(GL_LIGHT2, GL_POSITION, vec(-1, -1, 3, 0))
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)

    def reset_mview(self, factor):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.setup_lights()
        if self.orthographic:
            wratio = self.width / self.dist
            hratio = self.height / self.dist
            minratio = float(min(wratio, hratio))
            self.zoom_factor = 1.0
            self.zoomed_width = wratio / minratio
            self.zoomed_height = hratio / minratio
            glScalef(factor * minratio, factor * minratio, 1)

    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        self.pygletcontext.set_current()
        glClearColor(*self.color_background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()
        self.canvas.SwapBuffers()

    # ==========================================================================
    # To be implemented by a sub class
    # ==========================================================================
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        pass

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_modelview_mat(self, local_transform):
        mvmat = (GLdouble * 16)()
        glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    def mouse_to_3d(self, x, y, z = 1.0, local_transform = False):
        x = float(x)
        y = self.height - float(y)
        # The following could work if we were not initially scaling to zoom on
        # the bed
        # if self.orthographic:
        #    return (x - self.width / 2, y - self.height / 2, 0)
        pmat = (GLdouble * 16)()
        mvmat = self.get_modelview_mat(local_transform)
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)
        glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        gluUnProject(x, y, z, mvmat, pmat, viewport, px, py, pz)
        return (px.value, py.value, pz.value)

    def mouse_to_ray(self, x, y, local_transform = False):
        x = float(x)
        y = self.height - float(y)
        pmat = (GLdouble * 16)()
        mvmat = (GLdouble * 16)()
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)
        mvmat = self.get_modelview_mat(local_transform)
        gluUnProject(x, y, 1, mvmat, pmat, viewport, px, py, pz)
        ray_far = (px.value, py.value, pz.value)
        gluUnProject(x, y, 0., mvmat, pmat, viewport, px, py, pz)
        ray_near = (px.value, py.value, pz.value)
        return ray_near, ray_far

    def mouse_to_plane(self, x, y, plane_normal, plane_offset, local_transform = False):
        # Ray/plane intersection
        ray_near, ray_far = self.mouse_to_ray(x, y, local_transform)
        ray_near = numpy.array(ray_near)
        ray_far = numpy.array(ray_far)
        ray_dir = ray_far - ray_near
        ray_dir = ray_dir / numpy.linalg.norm(ray_dir)
        plane_normal = numpy.array(plane_normal)
        q = ray_dir.dot(plane_normal)
        if q == 0:
            return None
        t = - (ray_near.dot(plane_normal) + plane_offset) / q
        if t < 0:
            return None
        return ray_near + t * ray_dir

    def zoom(self, factor, to = None):
        glMatrixMode(GL_MODELVIEW)
        if to:
            delta_x = to[0]
            delta_y = to[1]
            glTranslatef(delta_x, delta_y, 0)
        glScalef(factor, factor, 1)
        self.zoom_factor *= factor
        if to:
            glTranslatef(-delta_x, -delta_y, 0)
        wx.CallAfter(self.Refresh)

    def zoom_to_center(self, factor):
        self.canvas.SetCurrent(self.context)
        x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        self.zoom(factor, (x, y))

    def handle_rotation(self, event):
        if self.initpos is None:
            self.initpos = event.GetPositionTuple()
        else:
            p1 = self.initpos
            p2 = event.GetPositionTuple()
            sz = self.GetClientSize()
            p1x = float(p1[0]) / (sz[0] / 2) - 1
            p1y = 1 - float(p1[1]) / (sz[1] / 2)
            p2x = float(p2[0]) / (sz[0] / 2) - 1
            p2y = 1 - float(p2[1]) / (sz[1] / 2)
            quat = trackball(p1x, p1y, p2x, p2y, self.dist / 250.0)
            with self.rot_lock:
                self.basequat = mulquat(self.basequat, quat)
            self.initpos = p2

    def handle_translation(self, event):
        if self.initpos is None:
            self.initpos = event.GetPositionTuple()
        else:
            p1 = self.initpos
            p2 = event.GetPositionTuple()
            if self.orthographic:
                x1, y1, _ = self.mouse_to_3d(p1[0], p1[1])
                x2, y2, _ = self.mouse_to_3d(p2[0], p2[1])
                glTranslatef(x2 - x1, y2 - y1, 0)
            else:
                glTranslatef(p2[0] - p1[0], -(p2[1] - p1[1]), 0)
            self.initpos = p2

########NEW FILE########
__FILENAME__ = trackball
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import math

from pyglet.gl import GLdouble

def cross(v1, v2):
    return [v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0]]

def trackball(p1x, p1y, p2x, p2y, r):
    TRACKBALLSIZE = r

    if p1x == p2x and p1y == p2y:
        return [0.0, 0.0, 0.0, 1.0]

    p1 = [p1x, p1y, project_to_sphere(TRACKBALLSIZE, p1x, p1y)]
    p2 = [p2x, p2y, project_to_sphere(TRACKBALLSIZE, p2x, p2y)]
    a = cross(p2, p1)

    d = map(lambda x, y: x - y, p1, p2)
    t = math.sqrt(sum(map(lambda x: x * x, d))) / (2.0 * TRACKBALLSIZE)

    if t > 1.0:
        t = 1.0
    if t < -1.0:
        t = -1.0
    phi = 2.0 * math.asin(t)

    return axis_to_quat(a, phi)

def axis_to_quat(a, phi):
    lena = math.sqrt(sum(map(lambda x: x * x, a)))
    q = map(lambda x: x * (1 / lena), a)
    q = map(lambda x: x * math.sin(phi / 2.0), q)
    q.append(math.cos(phi / 2.0))
    return q

def build_rotmatrix(q):
    m = (GLdouble * 16)()
    m[0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[1] = 2.0 * (q[0] * q[1] - q[2] * q[3])
    m[2] = 2.0 * (q[2] * q[0] + q[1] * q[3])
    m[3] = 0.0

    m[4] = 2.0 * (q[0] * q[1] + q[2] * q[3])
    m[5] = 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0])
    m[6] = 2.0 * (q[1] * q[2] - q[0] * q[3])
    m[7] = 0.0

    m[8] = 2.0 * (q[2] * q[0] - q[1] * q[3])
    m[9] = 2.0 * (q[1] * q[2] + q[0] * q[3])
    m[10] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    m[11] = 0.0

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0
    return m


def project_to_sphere(r, x, y):
    d = math.sqrt(x * x + y * y)
    if (d < r * 0.70710678118654752440):
        return math.sqrt(r * r - d * d)
    else:
        t = r / 1.41421356237309504880
        return t * t / d


def mulquat(q1, rq):
    return [q1[3] * rq[0] + q1[0] * rq[3] + q1[1] * rq[2] - q1[2] * rq[1],
            q1[3] * rq[1] + q1[1] * rq[3] + q1[2] * rq[0] - q1[0] * rq[2],
            q1[3] * rq[2] + q1[2] * rq[3] + q1[0] * rq[1] - q1[1] * rq[0],
            q1[3] * rq[3] - q1[0] * rq[0] - q1[1] * rq[1] - q1[2] * rq[2]]

########NEW FILE########
__FILENAME__ = bufferedcanvas
"""
BufferedCanvas -- flicker-free canvas widget
Copyright (C) 2005, 2006 Daniel Keep, 2011 Duane Johnson

To use this widget, just override or replace the draw method.
This will be called whenever the widget size changes, or when
the update method is explicitly called.

Please submit any improvements/bugfixes/ideas to the following
url:

  http://wiki.wxpython.org/index.cgi/BufferedCanvas

2006-04-29: Added bugfix for a crash on Mac provided by Marc Jans.
"""

# Hint: try removing '.sp4msux0rz'
__author__ = 'Daniel Keep <daniel.keep.sp4msux0rz@gmail.com>'

__license__ = """
This file is part of the Printrun suite.

Printrun is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Printrun is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Printrun.  If not, see <http://www.gnu.org/licenses/>.
"""

__all__ = ['BufferedCanvas']

import wx

class BufferedCanvas(wx.Panel):
    """
    Implements a flicker-free canvas widget.

    Standard usage is to subclass this class, and override the
    draw method.  The draw method is passed a device context, which
    should be used to do your drawing.

    If you want to force a redraw (for whatever reason), you should
    call the update method.  This is because the draw method is never
    called as a result of an EVT_PAINT event.
    """

    # These are our two buffers.  Just be aware that when the buffers
    # are flipped, the REFERENCES are swapped.  So I wouldn't want to
    # try holding onto explicit references to one or the other ;)
    buffer = None
    backbuffer = None

    def __init__(self,
                 parent,
                 ID=-1,
                 pos = wx.DefaultPosition,
                 size = wx.DefaultSize,
                 style = wx.NO_FULL_REPAINT_ON_RESIZE | wx.WANTS_CHARS):
        wx.Panel.__init__(self, parent, ID, pos, size, style)

        # Bind events
        self.Bind(wx.EVT_PAINT, self.onPaint)

        # Disable background erasing (flicker-licious)
        def disable_event(*pargs, **kwargs):
            pass  # the sauce, please
        self.Bind(wx.EVT_ERASE_BACKGROUND, disable_event)

    #
    # General methods
    #

    def draw(self, dc, w, h):
        """
        Stub: called when the canvas needs to be re-drawn.
        """
        pass

    def update(self):
        """
        Causes the canvas to be updated.
        """
        self.Refresh()

    def getWidthHeight(self):
        width, height = self.GetClientSizeTuple()
        if width == 0:
            width = 1
        if height == 0:
            height = 1
        return (width, height)

    #
    # Event handlers
    #

    def onPaint(self, event):
        # Blit the front buffer to the screen
        w, h = self.GetClientSizeTuple()
        if not w or not h:
            return
        else:
            dc = wx.BufferedPaintDC(self)
            self.draw(dc, w, h)

########NEW FILE########
__FILENAME__ = controls
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

from .xybuttons import XYButtons, XYButtonsMini
from .zbuttons import ZButtons, ZButtonsMini
from .graph import Graph
from .widgets import TempGauge
from wx.lib.agw.floatspin import FloatSpin

from .utils import make_button, make_custom_button

class XYZControlsSizer(wx.GridBagSizer):

    def __init__(self, root, parentpanel = None):
        super(XYZControlsSizer, self).__init__()
        if not parentpanel: parentpanel = root.panel
        root.xyb = XYButtons(parentpanel, root.moveXY, root.homeButtonClicked, root.spacebarAction, root.bgcolor, zcallback=root.moveZ)
        self.Add(root.xyb, pos = (0, 1), flag = wx.ALIGN_CENTER)
        root.zb = ZButtons(parentpanel, root.moveZ, root.bgcolor)
        self.Add(root.zb, pos = (0, 2), flag = wx.ALIGN_CENTER)
        wx.CallAfter(root.xyb.SetFocus)

def add_extra_controls(self, root, parentpanel, extra_buttons = None, mini_mode = False):
    standalone_mode = extra_buttons is not None
    base_line = 1 if standalone_mode else 2

    if standalone_mode:
        gauges_base_line = base_line + 10
    elif mini_mode and root.display_graph:
        gauges_base_line = base_line + 6
    else:
        gauges_base_line = base_line + 5
    tempdisp_line = gauges_base_line + (2 if root.display_gauges else 0)
    if mini_mode and root.display_graph:
        e_base_line = base_line + 3
    else:
        e_base_line = base_line + 2

    pos_mapping = {
        "htemp_label": (base_line + 0, 0),
        "htemp_off": (base_line + 0, 2),
        "htemp_val": (base_line + 0, 3),
        "htemp_set": (base_line + 0, 4),
        "btemp_label": (base_line + 1, 0),
        "btemp_off": (base_line + 1, 2),
        "btemp_val": (base_line + 1, 3),
        "btemp_set": (base_line + 1, 4),
        "ebuttons": (e_base_line + 0, 0),
        "esettings": (e_base_line + 1, 0),
        "speedcontrol": (e_base_line + 2, 0),
        "htemp_gauge": (gauges_base_line + 0, 0),
        "btemp_gauge": (gauges_base_line + 1, 0),
        "tempdisp": (tempdisp_line, 0),
        "extrude": (3, 0),
        "reverse": (3, 2),
    }

    span_mapping = {
        "htemp_label": (1, 2),
        "htemp_off": (1, 1),
        "htemp_val": (1, 1),
        "htemp_set": (1, 1 if root.display_graph else 2),
        "btemp_label": (1, 2),
        "btemp_off": (1, 1),
        "btemp_val": (1, 1),
        "btemp_set": (1, 1 if root.display_graph else 2),
        "ebuttons": (1, 5 if root.display_graph else 6),
        "esettings": (1, 5 if root.display_graph else 6),
        "speedcontrol": (1, 5 if root.display_graph else 6),
        "htemp_gauge": (1, 5 if mini_mode else 6),
        "btemp_gauge": (1, 5 if mini_mode else 6),
        "tempdisp": (1, 5 if mini_mode else 6),
        "extrude": (1, 2),
        "reverse": (1, 3),
    }

    if standalone_mode:
        pos_mapping["tempgraph"] = (base_line + 5, 0)
        span_mapping["tempgraph"] = (5, 6)
    elif mini_mode:
        pos_mapping["tempgraph"] = (base_line + 2, 0)
        span_mapping["tempgraph"] = (1, 5)
    else:
        pos_mapping["tempgraph"] = (base_line + 0, 5)
        span_mapping["tempgraph"] = (5, 1)

    if mini_mode:
        pos_mapping["etool_label"] = (0, 0)
        pos_mapping["etool_val"] = (0, 1)
        pos_mapping["edist_label"] = (0, 2)
        pos_mapping["edist_val"] = (0, 3)
        pos_mapping["edist_unit"] = (0, 4)
    else:
        pos_mapping["edist_label"] = (0, 0)
        pos_mapping["edist_val"] = (1, 0)
        pos_mapping["edist_unit"] = (1, 1)
        pos_mapping["efeed_label"] = (0, 2)
        pos_mapping["efeed_val"] = (1, 2)
        pos_mapping["efeed_unit"] = (1, 3)

    def add(name, widget, *args, **kwargs):
        kwargs["pos"] = pos_mapping[name]
        if name in span_mapping:
            kwargs["span"] = span_mapping[name]
        if "container" in kwargs:
            container = kwargs["container"]
            del kwargs["container"]
        else:
            container = self
        container.Add(widget, *args, **kwargs)

    # Hotend & bed temperatures #

    # Hotend temp
    add("htemp_label", wx.StaticText(parentpanel, -1, _("Heat:")), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
    htemp_choices = [root.temps[i] + " (" + i + ")" for i in sorted(root.temps.keys(), key = lambda x:root.temps[x])]

    root.settoff = make_button(parentpanel, _("Off"), lambda e: root.do_settemp("off"), _("Switch Hotend Off"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.settoff)
    add("htemp_off", root.settoff)

    if root.settings.last_temperature not in map(float, root.temps.values()):
        htemp_choices = [str(root.settings.last_temperature)] + htemp_choices
    root.htemp = wx.ComboBox(parentpanel, -1, choices = htemp_choices,
                             style = wx.CB_DROPDOWN, size = (80, -1))
    root.htemp.SetToolTip(wx.ToolTip(_("Select Temperature for Hotend")))
    root.htemp.Bind(wx.EVT_COMBOBOX, root.htemp_change)

    add("htemp_val", root.htemp)
    root.settbtn = make_button(parentpanel, _("Set"), root.do_settemp, _("Switch Hotend On"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.settbtn)
    add("htemp_set", root.settbtn, flag = wx.EXPAND)

    # Bed temp
    add("btemp_label", wx.StaticText(parentpanel, -1, _("Bed:")), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
    btemp_choices = [root.bedtemps[i] + " (" + i + ")" for i in sorted(root.bedtemps.keys(), key = lambda x:root.temps[x])]

    root.setboff = make_button(parentpanel, _("Off"), lambda e: root.do_bedtemp("off"), _("Switch Heated Bed Off"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.setboff)
    add("btemp_off", root.setboff)

    if root.settings.last_bed_temperature not in map(float, root.bedtemps.values()):
        btemp_choices = [str(root.settings.last_bed_temperature)] + btemp_choices
    root.btemp = wx.ComboBox(parentpanel, -1, choices = btemp_choices,
                             style = wx.CB_DROPDOWN, size = (80, -1))
    root.btemp.SetToolTip(wx.ToolTip(_("Select Temperature for Heated Bed")))
    root.btemp.Bind(wx.EVT_COMBOBOX, root.btemp_change)
    add("btemp_val", root.btemp)

    root.setbbtn = make_button(parentpanel, _("Set"), root.do_bedtemp, _("Switch Heated Bed On"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.setbbtn)
    add("btemp_set", root.setbbtn, flag = wx.EXPAND)

    root.btemp.SetValue(str(root.settings.last_bed_temperature))
    root.htemp.SetValue(str(root.settings.last_temperature))

    # added for an error where only the bed would get (pla) or (abs).
    # This ensures, if last temp is a default pla or abs, it will be marked so.
    # if it is not, then a (user) remark is added. This denotes a manual entry

    for i in btemp_choices:
        if i.split()[0] == str(root.settings.last_bed_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_bed_temperature):
            root.btemp.SetValue(i)
    for i in htemp_choices:
        if i.split()[0] == str(root.settings.last_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_temperature):
            root.htemp.SetValue(i)

    if '(' not in root.btemp.Value:
        root.btemp.SetValue(root.btemp.Value + ' (user)')
    if '(' not in root.htemp.Value:
        root.htemp.SetValue(root.htemp.Value + ' (user)')

    # Speed control #
    speedpanel = root.newPanel(parentpanel)
    speedsizer = wx.BoxSizer(wx.HORIZONTAL)
    speedsizer.Add(wx.StaticText(speedpanel, -1, _("Print speed:")), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

    root.speed_slider = wx.Slider(speedpanel, -1, 100, 1, 300)
    speedsizer.Add(root.speed_slider, 1, flag = wx.EXPAND)

    root.speed_spin = FloatSpin(speedpanel, -1, value = 100, min_val = 1, max_val = 300, digits = 0, style = wx.ALIGN_LEFT, size = (60, -1))
    speedsizer.Add(root.speed_spin, 0, flag = wx.ALIGN_CENTER_VERTICAL)
    root.speed_label = wx.StaticText(speedpanel, -1, _("%"))
    speedsizer.Add(root.speed_label, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

    def speedslider_set(event):
        root.do_setspeed()
        root.speed_setbtn.SetBackgroundColour(wx.NullColour)
    root.speed_setbtn = make_button(speedpanel, _("Set"), speedslider_set, _("Set print speed factor"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.speed_setbtn)
    speedsizer.Add(root.speed_setbtn, flag = wx.ALIGN_CENTER)
    speedpanel.SetSizer(speedsizer)
    add("speedcontrol", speedpanel, flag = wx.EXPAND)

    def speedslider_spin(event):
        value = root.speed_spin.GetValue()
        root.speed_setbtn.SetBackgroundColour("red")
        root.speed_slider.SetValue(value)
    root.speed_spin.Bind(wx.EVT_SPINCTRL, speedslider_spin)

    def speedslider_scroll(event):
        value = root.speed_slider.GetValue()
        root.speed_setbtn.SetBackgroundColour("red")
        root.speed_spin.SetValue(value)
    root.speed_slider.Bind(wx.EVT_SCROLL, speedslider_scroll)

    # Temperature gauges #

    if root.display_gauges:
        root.hottgauge = TempGauge(parentpanel, size = (-1, 24), title = _("Heater:"), maxval = 300, bgcolor = root.bgcolor)
        add("htemp_gauge", root.hottgauge, flag = wx.EXPAND)
        root.bedtgauge = TempGauge(parentpanel, size = (-1, 24), title = _("Bed:"), maxval = 150, bgcolor = root.bgcolor)
        add("btemp_gauge", root.bedtgauge, flag = wx.EXPAND)

        def hotendgauge_scroll_setpoint(e):
            rot = e.GetWheelRotation()
            if rot > 0:
                root.do_settemp(str(root.hsetpoint + 1))
            elif rot < 0:
                root.do_settemp(str(max(0, root.hsetpoint - 1)))

        def bedgauge_scroll_setpoint(e):
            rot = e.GetWheelRotation()
            if rot > 0:
                root.do_settemp(str(root.bsetpoint + 1))
            elif rot < 0:
                root.do_settemp(str(max(0, root.bsetpoint - 1)))
        root.hottgauge.Bind(wx.EVT_MOUSEWHEEL, hotendgauge_scroll_setpoint)
        root.bedtgauge.Bind(wx.EVT_MOUSEWHEEL, bedgauge_scroll_setpoint)

    # Temperature (M105) feedback display #
    root.tempdisp = wx.StaticText(parentpanel, -1, "", style = wx.ST_NO_AUTORESIZE)

    def on_tempdisp_size(evt):
        root.tempdisp.Wrap(root.tempdisp.GetSize().width)
    root.tempdisp.Bind(wx.EVT_SIZE, on_tempdisp_size)

    def tempdisp_setlabel(label):
        wx.StaticText.SetLabel(root.tempdisp, label)
        root.tempdisp.Wrap(root.tempdisp.GetSize().width)
        root.tempdisp.SetSize((-1, root.tempdisp.GetBestSize().height))
    root.tempdisp.SetLabel = tempdisp_setlabel
    add("tempdisp", root.tempdisp, flag = wx.EXPAND)

    # Temperature graph #

    if root.display_graph:
        root.graph = Graph(parentpanel, wx.ID_ANY, root)
        add("tempgraph", root.graph, flag = wx.EXPAND | wx.ALL, border = 5)
        root.graph.Bind(wx.EVT_LEFT_DOWN, root.graph.show_graph_window)

    # Extrusion controls #

    # Extrusion settings
    esettingspanel = root.newPanel(parentpanel)
    esettingssizer = wx.GridBagSizer()
    esettingssizer.SetEmptyCellSize((0, 0))
    root.edist = FloatSpin(esettingspanel, -1, value = root.settings.last_extrusion, min_val = 0, max_val = 1000, size = (70, -1), digits = 1)
    root.edist.SetBackgroundColour((225, 200, 200))
    root.edist.SetForegroundColour("black")
    root.edist.Bind(wx.EVT_SPINCTRL, root.setfeeds)
    root.edist.Bind(wx.EVT_TEXT, root.setfeeds)
    add("edist_label", wx.StaticText(esettingspanel, -1, _("Length:")), container = esettingssizer, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.LEFT, border = 5)
    add("edist_val", root.edist, container = esettingssizer, flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
    unit_label = _("mm") if mini_mode else _("mm @")
    add("edist_unit", wx.StaticText(esettingspanel, -1, unit_label), container = esettingssizer, flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
    root.edist.SetToolTip(wx.ToolTip(_("Amount to Extrude or Retract (mm)")))
    if not mini_mode:
        root.efeedc = FloatSpin(esettingspanel, -1, value = root.settings.e_feedrate, min_val = 0, max_val = 50000, size = (70, -1), digits = 1)
        root.efeedc.SetToolTip(wx.ToolTip(_("Extrude / Retract speed (mm/min)")))
        root.efeedc.SetBackgroundColour((225, 200, 200))
        root.efeedc.SetForegroundColour("black")
        root.efeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.efeedc.Bind(wx.EVT_TEXT, root.setfeeds)
        add("efeed_val", root.efeedc, container = esettingssizer, flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
        add("efeed_label", wx.StaticText(esettingspanel, -1, _("Speed:")), container = esettingssizer, flag = wx.ALIGN_LEFT)
        add("efeed_unit", wx.StaticText(esettingspanel, -1, _("mm/\nmin")), container = esettingssizer, flag = wx.ALIGN_CENTER)
    else:
        root.efeedc = None
    esettingspanel.SetSizer(esettingssizer)
    add("esettings", esettingspanel, flag = wx.ALIGN_LEFT)

    if not standalone_mode:
        ebuttonspanel = root.newPanel(parentpanel)
        ebuttonssizer = wx.BoxSizer(wx.HORIZONTAL)
        if root.settings.extruders > 1:
            etool_sel_panel = esettingspanel if mini_mode else ebuttonspanel
            etool_label = wx.StaticText(etool_sel_panel, -1, _("Tool:"))
            if root.settings.extruders == 2:
                root.extrudersel = wx.Button(etool_sel_panel, -1, "0", style = wx.BU_EXACTFIT)
                root.extrudersel.SetToolTip(wx.ToolTip(_("Click to switch current extruder")))

                def extrudersel_cb(event):
                    if root.extrudersel.GetLabel() == "1":
                        new = "0"
                    else:
                        new = "1"
                    root.extrudersel.SetLabel(new)
                    root.tool_change(event)
                root.extrudersel.Bind(wx.EVT_BUTTON, extrudersel_cb)
                root.extrudersel.GetValue = root.extrudersel.GetLabel
                root.extrudersel.SetValue = root.extrudersel.SetLabel
            else:
                choices = [str(i) for i in range(0, root.settings.extruders)]
                root.extrudersel = wx.ComboBox(etool_sel_panel, -1, choices = choices,
                                               style = wx.CB_DROPDOWN | wx.CB_READONLY,
                                               size = (50, -1))
                root.extrudersel.SetToolTip(wx.ToolTip(_("Select current extruder")))
                root.extrudersel.SetValue(choices[0])
                root.extrudersel.Bind(wx.EVT_COMBOBOX, root.tool_change)
            root.printerControls.append(root.extrudersel)
            if mini_mode:
                add("etool_label", etool_label, container = esettingssizer, flag = wx.ALIGN_CENTER)
                add("etool_val", root.extrudersel, container = esettingssizer)
            else:
                ebuttonssizer.Add(etool_label, flag = wx.ALIGN_CENTER)
                ebuttonssizer.Add(root.extrudersel)

        for key in ["extrude", "reverse"]:
            desc = root.cpbuttons[key]
            btn = make_custom_button(root, ebuttonspanel, desc,
                                     style = wx.BU_EXACTFIT)
            ebuttonssizer.Add(btn, 1, flag = wx.EXPAND)

        ebuttonspanel.SetSizer(ebuttonssizer)
        add("ebuttons", ebuttonspanel, flag = wx.EXPAND)
    else:
        for key, btn in extra_buttons.items():
            add(key, btn, flag = wx.EXPAND)

class ControlsSizer(wx.GridBagSizer):

    def __init__(self, root, parentpanel = None, standalone_mode = False, mini_mode = False):
        super(ControlsSizer, self).__init__()
        if not parentpanel: parentpanel = root.panel
        if mini_mode: self.make_mini(root, parentpanel)
        else: self.make_standard(root, parentpanel, standalone_mode)

    def make_standard(self, root, parentpanel, standalone_mode):
        lltspanel = root.newPanel(parentpanel)
        llts = wx.BoxSizer(wx.HORIZONTAL)
        lltspanel.SetSizer(llts)
        self.Add(lltspanel, pos = (0, 0), span = (1, 6))
        xyzpanel = root.newPanel(parentpanel)
        self.xyzsizer = XYZControlsSizer(root, xyzpanel)
        xyzpanel.SetSizer(self.xyzsizer)
        self.Add(xyzpanel, pos = (1, 0), span = (1, 6), flag = wx.ALIGN_CENTER)

        self.extra_buttons = {}
        pos_mapping = {"extrude": (4, 0),
                       "reverse": (4, 2),
                       }
        span_mapping = {"extrude": (1, 2),
                        "reverse": (1, 3),
                        }
        for key, desc in root.cpbuttons.items():
            if not standalone_mode and key in ["extrude", "reverse"]:
                continue
            panel = lltspanel if key == "motorsoff" else parentpanel
            btn = make_custom_button(root, panel, desc)
            if key == "motorsoff":
                llts.Add(btn)
            elif not standalone_mode:
                self.Add(btn, pos = pos_mapping[key], span = span_mapping[key], flag = wx.EXPAND)
            else:
                self.extra_buttons[key] = btn

        root.xyfeedc = wx.SpinCtrl(lltspanel, -1, str(root.settings.xy_feedrate), min = 0, max = 50000, size = (70, -1))
        root.xyfeedc.SetToolTip(wx.ToolTip(_("Set Maximum Speed for X & Y axes (mm/min)")))
        llts.Add(wx.StaticText(lltspanel, -1, _("XY:")), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        llts.Add(root.xyfeedc)
        llts.Add(wx.StaticText(lltspanel, -1, _("mm/min Z:")), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        root.zfeedc = wx.SpinCtrl(lltspanel, -1, str(root.settings.z_feedrate), min = 0, max = 50000, size = (70, -1))
        root.zfeedc.SetToolTip(wx.ToolTip(_("Set Maximum Speed for Z axis (mm/min)")))
        llts.Add(root.zfeedc,)

        root.xyfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.zfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.xyfeedc.Bind(wx.EVT_TEXT, root.setfeeds)
        root.zfeedc.Bind(wx.EVT_TEXT, root.setfeeds)
        root.zfeedc.SetBackgroundColour((180, 255, 180))
        root.zfeedc.SetForegroundColour("black")

        if not standalone_mode:
            add_extra_controls(self, root, parentpanel, None)

    def make_mini(self, root, parentpanel):
        root.xyb = XYButtonsMini(parentpanel, root.moveXY, root.homeButtonClicked,
                                 root.spacebarAction, root.bgcolor,
                                 zcallback = root.moveZ)
        self.Add(root.xyb, pos = (1, 0), span = (1, 4), flag = wx.ALIGN_CENTER)
        root.zb = ZButtonsMini(parentpanel, root.moveZ, root.bgcolor)
        self.Add(root.zb, pos = (0, 4), span = (2, 1), flag = wx.ALIGN_CENTER)
        wx.CallAfter(root.xyb.SetFocus)

        pos_mapping = {"motorsoff": (0, 0),
                       }
        span_mapping = {"motorsoff": (1, 4),
                        }
        btn = make_custom_button(root, parentpanel, root.cpbuttons["motorsoff"])
        self.Add(btn, pos = pos_mapping["motorsoff"], span = span_mapping["motorsoff"], flag = wx.EXPAND)

        add_extra_controls(self, root, parentpanel, None, True)

########NEW FILE########
__FILENAME__ = graph
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
from math import log10, floor, ceil

from printrun.utils import install_locale
install_locale('pronterface')

from .bufferedcanvas import BufferedCanvas

class GraphWindow(wx.Frame):
    def __init__(self, root, parent_graph = None, size = (600, 600)):
        super(GraphWindow, self).__init__(None, title = _("Temperature graph"),
                                          size = size)
        panel = wx.Panel(self, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.graph = Graph(panel, wx.ID_ANY, root, parent_graph = parent_graph)
        vbox.Add(self.graph, 1, wx.EXPAND)
        panel.SetSizer(vbox)

class Graph(BufferedCanvas):
    '''A class to show a Graph with Pronterface.'''

    def __init__(self, parent, id, root, pos = wx.DefaultPosition,
                 size = wx.Size(150, 80), style = 0, parent_graph = None):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(Graph, self).__init__(parent, id, pos, size, style)
        self.root = root

        if parent_graph is not None:
            self.extruder0temps = parent_graph.extruder0temps
            self.extruder0targettemps = parent_graph.extruder0targettemps
            self.extruder1temps = parent_graph.extruder1temps
            self.extruder1targettemps = parent_graph.extruder1targettemps
            self.bedtemps = parent_graph.bedtemps
            self.bedtargettemps = parent_graph.bedtargettemps
        else:
            self.extruder0temps = [0]
            self.extruder0targettemps = [0]
            self.extruder1temps = [0]
            self.extruder1targettemps = [0]
            self.bedtemps = [0]
            self.bedtargettemps = [0]

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.updateTemperatures, self.timer)

        self.minyvalue = 0
        self.maxyvalue = 250
        self.rescaley = True  # should the Y axis be rescaled dynamically?
        if self.rescaley:
            self._ybounds = Graph._YBounds(self)

        # If rescaley is set then ybars gives merely an estimate
        # Note that "bars" actually indicate the number of internal+external gridlines.
        self.ybars = 5
        self.xbars = 7  # One bar per 10 second
        self.xsteps = 60  # Covering 1 minute in the graph

        self.window = None

    def show_graph_window(self, event = None):
        if not self.window:
            self.window = GraphWindow(self.root, self)
            self.window.Show()
            if self.timer.IsRunning():
                self.window.graph.StartPlotting(self.timer.Interval)
        else:
            self.window.Raise()

    def __del__(self):
        if self.window: self.window.Close()

    def updateTemperatures(self, event):
        self.AddBedTemperature(self.bedtemps[-1])
        self.AddBedTargetTemperature(self.bedtargettemps[-1])
        self.AddExtruder0Temperature(self.extruder0temps[-1])
        self.AddExtruder0TargetTemperature(self.extruder0targettemps[-1])
        self.AddExtruder1Temperature(self.extruder1temps[-1])
        self.AddExtruder1TargetTemperature(self.extruder1targettemps[-1])
        if self.rescaley:
            self._ybounds.update()
        self.Refresh()

    def drawgrid(self, dc, gc):
        # cold, medium, hot = wx.Colour(0, 167, 223),\
        #                     wx.Colour(239, 233, 119),\
        #                     wx.Colour(210, 50.100)
        # col1 = wx.Colour(255, 0, 0, 255)
        # col2 = wx.Colour(255, 255, 255, 128)

        # b = gc.CreateLinearGradientBrush(0, 0, w, h, col1, col2)

        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))

        # gc.SetBrush(wx.Brush(wx.Colour(245, 245, 255, 52)))

        # gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0, 255))))
        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 255), 1))

        # gc.DrawLines(wx.Point(0, 0), wx.Point(50, 10))

        font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.Colour(23, 44, 44))

        # draw vertical bars
        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        for x in range(self.xbars + 1):
            dc.DrawLine(x * (float(self.width - 1) / (self.xbars - 1)),
                        0,
                        x * (float(self.width - 1) / (self.xbars - 1)),
                        self.height)

        # draw horizontal bars
        spacing = self._calculate_spacing()  # spacing between bars, in degrees
        yspan = self.maxyvalue - self.minyvalue
        ybars = int(yspan / spacing)  # Should be close to self.ybars
        firstbar = int(ceil(self.minyvalue / spacing))  # in degrees
        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        for y in range(firstbar, firstbar + ybars + 1):
            # y_pos = y*(float(self.height)/self.ybars)
            degrees = y * spacing
            y_pos = self._y_pos(degrees)
            dc.DrawLine(0, y_pos, self.width, y_pos)
            gc.DrawText(unicode(y * spacing),
                        1, y_pos - (font.GetPointSize() / 2))

        if self.timer.IsRunning() is False:
            font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(3, 4, 4))
            gc.DrawText("Graph offline",
                        self.width / 2 - (font.GetPointSize() * 3),
                        self.height / 2 - (font.GetPointSize() * 1))

        # dc.DrawCircle(50, 50, 1)

        # gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))
        # gc.DrawLines([[20, 30], [10, 53]])
        # dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))

    def _y_pos(self, temperature):
        """Converts a temperature, in degrees, to a pixel position"""
        # fraction of the screen from the bottom
        frac = (float(temperature - self.minyvalue)
                / (self.maxyvalue - self.minyvalue))
        return int((1.0 - frac) * (self.height - 1))

    def _calculate_spacing(self):
        # Allow grids of spacings 1,2.5,5,10,25,50,100,etc

        yspan = float(self.maxyvalue - self.minyvalue)
        log_yspan = log10(yspan / self.ybars)
        exponent = int(floor(log_yspan))

        # calculate boundary points between allowed spacings
        log1_25 = log10(2) + log10(1) + log10(2.5) - log10(1 + 2.5)
        log25_5 = log10(2) + log10(2.5) + log10(5) - log10(2.5 + 5)
        log5_10 = log10(2) + log10(5) + log10(10) - log10(5 + 10)

        if log_yspan - exponent < log1_25:
            return 10 ** exponent
        elif log1_25 <= log_yspan - exponent < log25_5:
            return 25 * 10 ** (exponent - 1)
        elif log25_5 <= log_yspan - exponent < log5_10:
            return 5 * 10 ** exponent
        else:
            return 10 ** (exponent + 1)

    def drawtemperature(self, dc, gc, temperature_list,
                        text, text_xoffset, r, g, b, a):
        if self.timer.IsRunning() is False:
            dc.SetPen(wx.Pen(wx.Colour(128, 128, 128, 128), 1))
        else:
            dc.SetPen(wx.Pen(wx.Colour(r, g, b, a), 1))

        x_add = float(self.width) / self.xsteps
        x_pos = 0.0
        lastxvalue = 0.0
        lastyvalue = temperature_list[-1]

        for temperature in (temperature_list):
            y_pos = self._y_pos(temperature)
            if (x_pos > 0.0):  # One need 2 points to draw a line.
                dc.DrawLine(lastxvalue, lastyvalue, x_pos, y_pos)

            lastxvalue = x_pos
            x_pos = float(x_pos) + x_add
            lastyvalue = y_pos

        if len(text) > 0:
            font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            # font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            if self.timer.IsRunning() is False:
                gc.SetFont(font, wx.Colour(128, 128, 128))
            else:
                gc.SetFont(font, wx.Colour(r, g, b))

            text_size = len(text) * text_xoffset + 1
            gc.DrawText(text,
                        x_pos - x_add - (font.GetPointSize() * text_size),
                        lastyvalue - (font.GetPointSize() / 2))

    def drawbedtemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtemps,
                             "Bed", 2, 255, 0, 0, 128)

    def drawbedtargettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtargettemps,
                             "Bed Target", 2, 255, 120, 0, 128)

    def drawextruder0temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0temps,
                             "Ex0", 1, 0, 155, 255, 128)

    def drawextruder0targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0targettemps,
                             "Ex0 Target", 2, 0, 5, 255, 128)

    def drawextruder1temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1temps,
                             "Ex1", 3, 55, 55, 0, 128)

    def drawextruder1targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1targettemps,
                             "Ex1 Target", 2, 55, 55, 0, 128)

    def SetBedTemperature(self, value):
        self.bedtemps.pop()
        self.bedtemps.append(value)

    def AddBedTemperature(self, value):
        self.bedtemps.append(value)
        if float(len(self.bedtemps) - 1) / self.xsteps > 1:
            self.bedtemps.pop(0)

    def SetBedTargetTemperature(self, value):
        self.bedtargettemps.pop()
        self.bedtargettemps.append(value)

    def AddBedTargetTemperature(self, value):
        self.bedtargettemps.append(value)
        if float(len(self.bedtargettemps) - 1) / self.xsteps > 1:
            self.bedtargettemps.pop(0)

    def SetExtruder0Temperature(self, value):
        self.extruder0temps.pop()
        self.extruder0temps.append(value)

    def AddExtruder0Temperature(self, value):
        self.extruder0temps.append(value)
        if float(len(self.extruder0temps) - 1) / self.xsteps > 1:
            self.extruder0temps.pop(0)

    def SetExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.pop()
        self.extruder0targettemps.append(value)

    def AddExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.append(value)
        if float(len(self.extruder0targettemps) - 1) / self.xsteps > 1:
            self.extruder0targettemps.pop(0)

    def SetExtruder1Temperature(self, value):
        self.extruder1temps.pop()
        self.extruder1temps.append(value)

    def AddExtruder1Temperature(self, value):
        self.extruder1temps.append(value)
        if float(len(self.extruder1temps) - 1) / self.xsteps > 1:
            self.extruder1temps.pop(0)

    def SetExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.pop()
        self.extruder1targettemps.append(value)

    def AddExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.append(value)
        if float(len(self.extruder1targettemps) - 1) / self.xsteps > 1:
            self.extruder1targettemps.pop(0)

    def StartPlotting(self, time):
        self.Refresh()
        self.timer.Start(time)
        if self.window: self.window.graph.StartPlotting(time)

    def StopPlotting(self):
        self.timer.Stop()
        self.Refresh()
        if self.window: self.window.graph.StopPlotting()

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.root.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        self.width = w
        self.height = h
        self.drawgrid(dc, gc)
        self.drawbedtargettemp(dc, gc)
        self.drawbedtemp(dc, gc)
        self.drawextruder0targettemp(dc, gc)
        self.drawextruder0temp(dc, gc)
        self.drawextruder1targettemp(dc, gc)
        self.drawextruder1temp(dc, gc)

    class _YBounds(object):
        """Small helper class to claculate y bounds dynamically"""

        def __init__(self, graph, minimum_scale=5.0, buffer=0.10):
            """_YBounds(Graph,float,float)

            graph           parent object to calculate scales for
            minimum_scale   minimum range to show on the graph
            buffer          amount of padding to add above & below the
                            displayed temperatures. Given as a fraction of the
                            total range. (Eg .05 to use 90% of the range for
                            temperatures)
            """
            self.graph = graph
            self.min_scale = minimum_scale
            self.buffer = buffer

            # Frequency to rescale the graph
            self.update_freq = 10
            # number of updates since last full refresh
            self._last_update = self.update_freq

        def update(self, forceUpdate=False):
            """Updates graph.minyvalue and graph.maxyvalue based on current
            temperatures """
            self._last_update += 1
            # TODO Smart update. Only do full calculation every 10s. Otherwise,
            # just look at current graph & expand if necessary
            if forceUpdate or self._last_update >= self.update_freq:
                self.graph.minyvalue, self.graph.maxyvalue = self.getBounds()
                self._last_update = 0
            else:
                bounds = self.getBoundsQuick()
                self.graph.minyvalue, self.graph.maxyvalue = bounds

        def getBounds(self):
            """
            Calculates the bounds based on the current temperatures

            Rules:
             * Include the full extruder0 history
             * Include the current target temp (but not necessarily old
               settings)
             * Include the extruder1 and/or bed temp if
                1) The target temp is >0
                2) The history has ever been above 5
             * Include at least min_scale
             * Include at least buffer above & below the extreme temps
            """
            extruder0_min = min(self.graph.extruder0temps)
            extruder0_max = max(self.graph.extruder0temps)
            extruder0_target = self.graph.extruder0targettemps[-1]
            extruder1_min = min(self.graph.extruder1temps)
            extruder1_max = max(self.graph.extruder1temps)
            extruder1_target = self.graph.extruder1targettemps[-1]
            bed_min = min(self.graph.bedtemps)
            bed_max = max(self.graph.bedtemps)
            bed_target = self.graph.bedtargettemps[-1]

            miny = min(extruder0_min, extruder0_target)
            maxy = max(extruder0_max, extruder0_target)
            if extruder1_target > 0 or extruder1_max > 5:  # use extruder1
                miny = min(miny, extruder1_min, extruder1_target)
                maxy = max(maxy, extruder1_max, extruder1_target)
            if bed_target > 0 or bed_max > 5:  # use HBP
                miny = min(miny, bed_min, bed_target)
                maxy = max(maxy, bed_max, bed_target)

            padding = (maxy - miny) * self.buffer / (1.0 - 2 * self.buffer)
            miny -= padding
            maxy += padding

            if maxy - miny < self.min_scale:
                extrapadding = (self.min_scale - maxy + miny) / 2.0
                miny -= extrapadding
                maxy += extrapadding

            return (miny, maxy)

        def getBoundsQuick(self):
            # Only look at current temps
            extruder0_min = self.graph.extruder0temps[-1]
            extruder0_max = self.graph.extruder0temps[-1]
            extruder0_target = self.graph.extruder0targettemps[-1]
            extruder1_min = self.graph.extruder1temps[-1]
            extruder1_max = self.graph.extruder1temps[-1]
            extruder1_target = self.graph.extruder1targettemps[-1]
            bed_min = self.graph.bedtemps[-1]
            bed_max = self.graph.bedtemps[-1]
            bed_target = self.graph.bedtargettemps[-1]

            miny = min(extruder0_min, extruder0_target)
            maxy = max(extruder0_max, extruder0_target)
            if extruder1_target > 0 or extruder1_max > 5:  # use extruder1
                miny = min(miny, extruder1_min, extruder1_target)
                maxy = max(maxy, extruder1_max, extruder1_target)
            if bed_target > 0 or bed_max > 5:  # use HBP
                miny = min(miny, bed_min, bed_target)
                maxy = max(maxy, bed_max, bed_target)

            # We have to rescale, so add padding
            bufratio = self.buffer / (1.0 - self.buffer)
            if miny < self.graph.minyvalue:
                padding = (self.graph.maxyvalue - miny) * bufratio
                miny -= padding
            if maxy > self.graph.maxyvalue:
                padding = (maxy - self.graph.minyvalue) * bufratio
                maxy += padding

            return (min(miny, self.graph.minyvalue),
                    max(maxy, self.graph.maxyvalue))

########NEW FILE########
__FILENAME__ = log
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

from .utils import make_button

class LogPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(LogPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        root.logbox = wx.TextCtrl(parentpanel, style = wx.TE_MULTILINE, size = (350, -1))
        root.logbox.SetMinSize((100, -1))
        root.logbox.SetEditable(0)
        self.Add(root.logbox, 1, wx.EXPAND)
        bottom_panel = root.newPanel(parentpanel)
        lbrs = wx.BoxSizer(wx.HORIZONTAL)
        root.commandbox = wx.TextCtrl(bottom_panel, style = wx.TE_PROCESS_ENTER)
        root.commandbox.SetToolTip(wx.ToolTip(_("Send commands to printer\n(Type 'help' for simple\nhelp function)")))
        root.commandbox.Bind(wx.EVT_TEXT_ENTER, root.sendline)
        root.commandbox.Bind(wx.EVT_CHAR, root.cbkey)
        root.commandbox.history = [u""]
        root.commandbox.histindex = 1
        lbrs.Add(root.commandbox, 1)
        root.sendbtn = make_button(bottom_panel, _("Send"), root.sendline, _("Send Command to Printer"), style = wx.BU_EXACTFIT, container = lbrs)
        bottom_panel.SetSizer(lbrs)
        self.Add(bottom_panel, 0, wx.EXPAND)

########NEW FILE########
__FILENAME__ = toolbar
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

from .utils import make_autosize_button

def MainToolbar(root, parentpanel = None, use_wrapsizer = False):
    if not parentpanel: parentpanel = root.panel
    if root.settings.lockbox:
        root.locker = wx.CheckBox(parentpanel, label = _("Lock") + "  ")
        root.locker.Bind(wx.EVT_CHECKBOX, root.lock)
        root.locker.SetToolTip(wx.ToolTip(_("Lock graphical interface")))
        glob = wx.BoxSizer(wx.HORIZONTAL)
        parentpanel = root.newPanel(parentpanel)
        glob.Add(parentpanel, 1, flag = wx.EXPAND)
        glob.Add(root.locker, 0, flag = wx.ALIGN_CENTER)
    ToolbarSizer = wx.WrapSizer if use_wrapsizer and wx.VERSION > (2, 9) else wx.BoxSizer
    self = ToolbarSizer(wx.HORIZONTAL)
    root.rescanbtn = make_autosize_button(parentpanel, _("Port"), root.rescanports, _("Communication Settings\nClick to rescan ports"))
    self.Add(root.rescanbtn, 0, wx.TOP | wx.LEFT, 0)

    root.serialport = wx.ComboBox(parentpanel, -1, choices = root.scanserial(),
                                  style = wx.CB_DROPDOWN)
    root.serialport.SetToolTip(wx.ToolTip(_("Select Port Printer is connected to")))
    root.rescanports()
    self.Add(root.serialport)

    self.Add(wx.StaticText(parentpanel, -1, "@"), 0, wx.RIGHT | wx.ALIGN_CENTER, 0)
    root.baud = wx.ComboBox(parentpanel, -1,
                            choices = ["2400", "9600", "19200", "38400",
                                       "57600", "115200", "250000"],
                            style = wx.CB_DROPDOWN, size = (100, -1))
    root.baud.SetToolTip(wx.ToolTip(_("Select Baud rate for printer communication")))
    try:
        root.baud.SetValue("115200")
        root.baud.SetValue(str(root.settings.baudrate))
    except:
        pass
    self.Add(root.baud)

    if not hasattr(root, "connectbtn"):
        root.connectbtn = make_autosize_button(parentpanel, _("Connect"), root.connect, _("Connect to the printer"))
        root.statefulControls.append(root.connectbtn)
    else:
        root.connectbtn.Reparent(parentpanel)
    self.Add(root.connectbtn)
    if not hasattr(root, "resetbtn"):
        root.resetbtn = make_autosize_button(parentpanel, _("Reset"), root.reset, _("Reset the printer"))
        root.statefulControls.append(root.resetbtn)
    else:
        root.resetbtn.Reparent(parentpanel)
    self.Add(root.resetbtn)

    self.AddStretchSpacer(prop = 1)

    root.loadbtn = make_autosize_button(parentpanel, _("Load file"), root.loadfile, _("Load a 3D model file"), self)
    root.sdbtn = make_autosize_button(parentpanel, _("SD"), root.sdmenu, _("SD Card Printing"), self)
    root.sdbtn.Reparent(parentpanel)
    root.printerControls.append(root.sdbtn)
    if not hasattr(root, "printbtn"):
        root.printbtn = make_autosize_button(parentpanel, _("Print"), root.printfile, _("Start Printing Loaded File"))
        root.statefulControls.append(root.printbtn)
    else:
        root.printbtn.Reparent(parentpanel)
    self.Add(root.printbtn)
    if not hasattr(root, "pausebtn"):
        root.pausebtn = make_autosize_button(parentpanel, _("Pause"), root.pause, _("Pause Current Print"))
        root.statefulControls.append(root.pausebtn)
    else:
        root.pausebtn.Reparent(parentpanel)
    self.Add(root.pausebtn)
    root.offbtn = make_autosize_button(parentpanel, _("Off"), root.off, _("Turn printer off"), self)
    root.printerControls.append(root.offbtn)

    self.AddStretchSpacer(prop = 4)

    if root.settings.lockbox:
        parentpanel.SetSizer(self)
        return glob
    else:
        return self

########NEW FILE########
__FILENAME__ = utils
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

def make_button(parent, label, callback, tooltip, container = None, size = wx.DefaultSize, style = 0):
    button = wx.Button(parent, -1, label, style = style, size = size)
    button.Bind(wx.EVT_BUTTON, callback)
    button.SetToolTip(wx.ToolTip(tooltip))
    if container:
        container.Add(button)
    return button

def make_autosize_button(*args):
    return make_button(*args, size = (-1, -1), style = wx.BU_EXACTFIT)

def make_custom_button(root, parentpanel, i, style = 0):
    btn = make_button(parentpanel, i.label, root.process_button,
                      i.tooltip, style = style)
    btn.SetBackgroundColour(i.background)
    btn.SetForegroundColour("black")
    btn.properties = i
    root.btndict[i.command] = btn
    root.printerControls.append(btn)
    return btn

########NEW FILE########
__FILENAME__ = viz
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import traceback

import wx

from printrun import gviz

class NoViz(object):

    showall = False

    def clear(self, *a):
        pass

    def addfile(self, *a, **kw):
        pass

    def addgcode(self, *a, **kw):
        pass

    def Refresh(self, *a):
        pass

    def setlayer(self, *a):
        pass

class VizPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(VizPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        if root.settings.mainviz == "None":
            root.gviz = NoViz()
        use2dview = root.settings.mainviz == "2D"
        if root.settings.mainviz == "3D":
            try:
                import printrun.gcview
                root.gviz = printrun.gcview.GcodeViewMainWrapper(parentpanel, root.build_dimensions_list, root = root, circular = root.settings.circular_bed, antialias_samples = int(root.settings.antialias3dsamples))
                root.gviz.clickcb = root.show_viz_window
            except:
                use2dview = True
                print "3D view mode requested, but we failed to initialize it."
                print "Falling back to 2D view, and here is the backtrace:"
                traceback.print_exc()
        if use2dview:
            root.gviz = gviz.Gviz(parentpanel, (300, 300),
                                  build_dimensions = root.build_dimensions_list,
                                  grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                  extrusion_width = root.settings.preview_extrusion_width,
                                  bgcolor = root.bgcolor)
            root.gviz.SetToolTip(wx.ToolTip(_("Click to examine / edit\n  layers of loaded file")))
            root.gviz.showall = 1
            root.gviz.Bind(wx.EVT_LEFT_DOWN, root.show_viz_window)
        use3dview = root.settings.viz3d
        if use3dview:
            try:
                import printrun.gcview
                objects = None
                if isinstance(root.gviz, printrun.gcview.GcodeViewMainWrapper):
                    objects = root.gviz.objects
                root.gwindow = printrun.gcview.GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (600, 600), build_dimensions = root.build_dimensions_list, objects = objects, root = root, circular = root.settings.circular_bed, antialias_samples = int(root.settings.antialias3dsamples))
            except:
                use3dview = False
                print "3D view mode requested, but we failed to initialize it."
                print "Falling back to 2D view, and here is the backtrace:"
                traceback.print_exc()
        if not use3dview:
            root.gwindow = gviz.GvizWindow(build_dimensions = root.build_dimensions_list,
                                           grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                           extrusion_width = root.settings.preview_extrusion_width,
                                           bgcolor = root.bgcolor)
        root.gwindow.Bind(wx.EVT_CLOSE, lambda x: root.gwindow.Hide())
        if not isinstance(root.gviz, NoViz):
            self.Add(root.gviz.widget, 1, flag = wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL)

########NEW FILE########
__FILENAME__ = widgets
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
import re

class MacroEditor(wx.Dialog):
    """Really simple editor to edit macro definitions"""

    def __init__(self, macro_name, definition, callback, gcode = False):
        self.indent_chars = "  "
        title = "  macro %s"
        if gcode:
            title = "  %s"
        self.gcode = gcode
        wx.Dialog.__init__(self, None, title = title % macro_name,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.callback = callback
        self.panel = wx.Panel(self, -1)
        titlesizer = wx.BoxSizer(wx.HORIZONTAL)
        self.titletext = wx.StaticText(self.panel, -1, "              _")  # title%macro_name)
        titlesizer.Add(self.titletext, 1)
        self.findb = wx.Button(self.panel, -1, _("Find"), style = wx.BU_EXACTFIT)  # New button for "Find" (Jezmy)
        self.findb.Bind(wx.EVT_BUTTON, self.find)
        self.okb = wx.Button(self.panel, -1, _("Save"), style = wx.BU_EXACTFIT)
        self.okb.Bind(wx.EVT_BUTTON, self.save)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.findb)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel, -1, _("Cancel"), style = wx.BU_EXACTFIT)
        self.cancelb.Bind(wx.EVT_BUTTON, self.close)
        titlesizer.Add(self.cancelb)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer, 0, wx.EXPAND)
        self.e = wx.TextCtrl(self.panel, style = wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2, size = (400, 400))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        topsizer.Add(self.e, 1, wx.ALL | wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
        self.e.SetFocus()

    def find(self, ev):
        # Ask user what to look for, find it and point at it ...  (Jezmy)
        S = self.e.GetStringSelection()
        if not S:
            S = "Z"
        FindValue = wx.GetTextFromUser('Please enter a search string:', caption = "Search", default_value = S, parent = None)
        somecode = self.e.GetValue()
        position = somecode.find(FindValue, self.e.GetInsertionPoint())
        if position == -1:
            self.titletext.SetLabel(_("Not Found!"))
        else:
            self.titletext.SetLabel(str(position))

            # ananswer = wx.MessageBox(str(numLines)+" Lines detected in file\n"+str(position), "OK")
            self.e.SetFocus()
            self.e.SetInsertionPoint(position)
            self.e.SetSelection(position, position + len(FindValue))
            self.e.ShowPosition(position)

    def ShowMessage(self, ev, message):
        dlg = wx.MessageDialog(self, message,
                               "Info!", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def save(self, ev):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.e.GetValue()))
        else:
            self.callback(self.e.GetValue().split("\n"))

    def close(self, ev):
        self.Destroy()

    def unindent(self, text):
        self.indent_chars = text[:len(text) - len(text.lstrip())]
        if len(self.indent_chars) == 0:
            self.indent_chars = "  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented

    def reindent(self, text):
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            if line.strip() != "":
                reindented += self.indent_chars + line + "\n"
        return reindented

SETTINGS_GROUPS = {"Printer": _("Printer settings"),
                   "UI": _("User interface"),
                   "Viewer": _("Viewer"),
                   "Colors": _("Colors"),
                   "External": _("External commands")}

class PronterOptionsDialog(wx.Dialog):
    """Options editor"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, parent = None, title = _("Edit settings"),
                           size = (400, 500), style = wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        header = wx.StaticBox(panel, label = _("Settings"))
        sbox = wx.StaticBoxSizer(header, wx.VERTICAL)
        notebook = wx.Notebook(panel)
        all_settings = pronterface.settings._all_settings()
        group_list = []
        groups = {}
        for group in ["Printer", "UI", "Viewer", "Colors", "External"]:
            group_list.append(group)
            groups[group] = []
        for setting in all_settings:
            if setting.group not in group_list:
                group_list.append(setting.group)
                groups[setting.group] = []
            groups[setting.group].append(setting)
        for group in group_list:
            grouppanel = wx.Panel(notebook, -1)
            notebook.AddPage(grouppanel, SETTINGS_GROUPS[group])
            settings = groups[group]
            grid = wx.GridBagSizer(hgap = 8, vgap = 2)
            current_row = 0
            for setting in settings:
                if setting.name.startswith("separator_"):
                    sep = wx.StaticLine(grouppanel, size = (-1, 5), style = wx.LI_HORIZONTAL)
                    grid.Add(sep, pos = (current_row, 0), span = (1, 2),
                             border = 3, flag = wx.ALIGN_CENTER | wx.ALL | wx.EXPAND)
                    current_row += 1
                label, widget = setting.get_label(grouppanel), setting.get_widget(grouppanel)
                if setting.name.startswith("separator_"):
                    font = label.GetFont()
                    font.SetWeight(wx.BOLD)
                    label.SetFont(font)
                grid.Add(label, pos = (current_row, 0),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
                grid.Add(widget, pos = (current_row, 1),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
                if hasattr(label, "set_default"):
                    label.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                    if hasattr(widget, "Bind"):
                        widget.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                current_row += 1
            grid.AddGrowableCol(1)
            grouppanel.SetSizer(grid)
        sbox.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sbox)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(panel, 1, wx.ALL | wx.EXPAND)
        topsizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT)
        self.SetSizerAndFit(topsizer)
        self.SetMinSize(self.GetSize())

def PronterOptions(pronterface):
    dialog = PronterOptionsDialog(pronterface)
    if dialog.ShowModal() == wx.ID_OK:
        for setting in pronterface.settings._all_settings():
            old_value = setting.value
            setting.update()
            if setting.value != old_value:
                pronterface.set(setting.name, setting.value)
    dialog.Destroy()

class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, None, title = _("Custom button"),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pronterface = pronterface
        topsizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = 4, vgap = 2)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, -1, _("Button title")), 0, wx.BOTTOM | wx.RIGHT)
        self.name = wx.TextCtrl(self, -1, "")
        grid.Add(self.name, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Command")), 0, wx.BOTTOM | wx.RIGHT)
        self.command = wx.TextCtrl(self, -1, "")
        xbox = wx.BoxSizer(wx.HORIZONTAL)
        xbox.Add(self.command, 1, wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT, self.macrob_enabler)
        self.macrob = wx.Button(self, -1, "..", style = wx.BU_EXACTFIT)
        self.macrob.Bind(wx.EVT_BUTTON, self.macrob_handler)
        xbox.Add(self.macrob, 0)
        grid.Add(xbox, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Color")), 0, wx.BOTTOM | wx.RIGHT)
        self.color = wx.TextCtrl(self, -1, "")
        grid.Add(self.color, 1, wx.EXPAND)
        topsizer.Add(grid, 0, wx.EXPAND)
        topsizer.Add((0, 0), 1)
        topsizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_CENTER)
        self.SetSizer(topsizer)

    def macrob_enabler(self, e):
        macro = self.command.GetValue()
        valid = False
        try:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif hasattr(self.pronterface.__class__, u"do_" + macro):
                valid = False
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        except:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        self.macrob.Enable(valid)

    def macrob_handler(self, e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue() == "":
            self.name.SetValue(macro)

class TempGauge(wx.Panel):

    def __init__(self, parent, size = (200, 22), title = "",
                 maxval = 240, gaugeColour = None, bgcolor = "#FFFFFF"):
        wx.Panel.__init__(self, parent, -1, size = size)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.width, self.height = size
        self.title = title
        self.max = maxval
        self.gaugeColour = gaugeColour
        self.value = 0
        self.setpoint = 0
        self.recalc()

    def recalc(self):
        mmax = max(int(self.setpoint * 1.05), self.max)
        self.scale = float(self.width - 2) / float(mmax)
        self.ypt = max(16, int(self.scale * max(self.setpoint, self.max / 6)))

    def SetValue(self, value):
        self.value = value
        wx.CallAfter(self.Refresh)

    def SetTarget(self, value):
        self.setpoint = value
        wx.CallAfter(self.Refresh)

    def interpolatedColour(self, val, vmin, vmid, vmax, cmin, cmid, cmax):
        if val < vmin: return cmin
        if val > vmax: return cmax
        if val <= vmid:
            lo, hi, val, valhi = cmin, cmid, val - vmin, vmid - vmin
        else:
            lo, hi, val, valhi = cmid, cmax, val - vmid, vmax - vmid
        vv = float(val) / valhi
        rgb = lo.Red() + (hi.Red() - lo.Red()) * vv, lo.Green() + (hi.Green() - lo.Green()) * vv, lo.Blue() + (hi.Blue() - lo.Blue()) * vv
        rgb = map(lambda x: x * 0.8, rgb)
        return wx.Colour(*map(int, rgb))

    def paint(self, ev):
        self.width, self.height = self.GetClientSizeTuple()
        self.recalc()
        x0, y0, x1, y1, xE, yE = 1, 1, self.ypt + 1, 1, self.width + 1 - 2, 20
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        cold, medium, hot = wx.Colour(0, 167, 223), wx.Colour(239, 233, 119), wx.Colour(210, 50.100)
        # gauge1, gauge2 = wx.Colour(255, 255, 210), (self.gaugeColour or wx.Colour(234, 82, 0))
        gauge1 = wx.Colour(255, 255, 210)
        shadow1, shadow2 = wx.Colour(110, 110, 110), self.bgcolor
        gc = wx.GraphicsContext.Create(dc)
        # draw shadow first
        # corners
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 9, xE - 7, 9, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 1, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 17, xE - 7, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 17, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(x0 + 6, 17, x0 + 6, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(0, 17, x0 + 6, 8)
        # edges
        gc.SetBrush(gc.CreateLinearGradientBrush(xE - 6, 0, xE + 1, 0, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 9, 8, 8)
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, yE - 2, x0, yE + 5, shadow1, shadow2))
        gc.DrawRectangle(x0 + 6, yE - 2, xE - 12, 7)
        # draw gauge background
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0, x1 + 1, y1, cold, medium))
        gc.DrawRoundedRectangle(x0, y0, x1 + 4, yE, 6)
        gc.SetBrush(gc.CreateLinearGradientBrush(x1 - 2, y1, xE, y1, medium, hot))
        gc.DrawRoundedRectangle(x1 - 2, y1, xE - x1, yE, 6)
        # draw gauge
        width = 12
        w1 = y0 + 9 - width / 2
        w2 = w1 + width
        value = x0 + max(10, min(self.width + 1 - 2, int(self.value * self.scale)))
        # gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, gauge2))
        # gc.SetBrush(gc.CreateLinearGradientBrush(0, 3, 0, 15, wx.Colour(255, 255, 255), wx.Colour(255, 90, 32)))
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, self.interpolatedColour(value, x0, x1, xE, cold, medium, hot)))
        val_path = gc.CreatePath()
        val_path.MoveToPoint(x0, w1)
        val_path.AddLineToPoint(value, w1)
        val_path.AddLineToPoint(value + 2, w1 + width / 4)
        val_path.AddLineToPoint(value + 2, w2 - width / 4)
        val_path.AddLineToPoint(value, w2)
        # val_path.AddLineToPoint(value-4, 10)
        val_path.AddLineToPoint(x0, w2)
        gc.DrawPath(val_path)
        # draw setpoint markers
        setpoint = x0 + max(10, int(self.setpoint * self.scale))
        gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0))))
        setp_path = gc.CreatePath()
        setp_path.MoveToPoint(setpoint - 4, y0)
        setp_path.AddLineToPoint(setpoint + 4, y0)
        setp_path.AddLineToPoint(setpoint, y0 + 5)
        setp_path.MoveToPoint(setpoint - 4, yE)
        setp_path.AddLineToPoint(setpoint + 4, yE)
        setp_path.AddLineToPoint(setpoint, yE - 5)
        gc.DrawPath(setp_path)
        # draw readout
        text = u"T\u00B0 %u/%u" % (self.value, self.setpoint)
        # gc.SetFont(gc.CreateFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        # gc.DrawText(text, 29,-2)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        gc.DrawText(self.title, x0 + 19, y0 + 4)
        gc.DrawText(text, x0 + 119, y0 + 4)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)))
        gc.DrawText(self.title, x0 + 18, y0 + 3)
        gc.DrawText(text, x0 + 118, y0 + 3)

class SpecialButton(object):

    label = None
    command = None
    background = None
    tooltip = None
    custom = None

    def __init__(self, label, command, background = None,
                 tooltip = None, custom = False):
        self.label = label
        self.command = command
        self.background = background
        self.tooltip = tooltip
        self.custom = custom

########NEW FILE########
__FILENAME__ = xybuttons
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
import math
from .bufferedcanvas import BufferedCanvas
from printrun.utils import imagefile

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (106, 100),
        1: (86, 83),
        2: (68, 65),
        3: (53, 50)
    }
    corner_size = (49, 49)
    corner_inset = (7, 13)
    label_overlay_positions = {
        1: (145, 98.5, 9),
        2: (160.5, 83.5, 10.6),
        3: (178, 66, 13),
        4: (197.3, 46.3, 13.3)
    }
    concentric_circle_radii = [0, 17, 45, 69, 94, 115]
    concentric_inset = 11
    center = (124, 121)
    spacer = 7
    imagename = "control_xy.png"
    corner_to_axis = {
        -1: "xy",
        0: "x",
        1: "z",
        2: "y",
        3: "all",
    }

    def __init__(self, parent, moveCallback = None, cornerCallback = None, spacebarCallback = None, bgcolor = "#FFFFFF", ID=-1, zcallback=None):
        self.bg_bmp = wx.Image(imagefile(self.imagename), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = -1
        self.quadrant = None
        self.concentric = None
        self.corner = None
        self.moveCallback = moveCallback
        self.cornerCallback = cornerCallback
        self.spacebarCallback = spacebarCallback
        self.zCallback = zcallback
        self.enabled = False
        # Remember the last clicked buttons, so we can repeat when spacebar pressed
        self.lastMove = None
        self.lastCorner = None

        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.bgcolormask = wx.Colour(self.bgcolor.Red(), self.bgcolor.Green(), self.bgcolor.Blue(), 128)

        BufferedCanvas.__init__(self, parent, ID, size=self.bg_bmp.GetSize())

        self.bind_events()

    def bind_events(self):
        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_KEY_UP, self.OnKey)
        wx.GetTopLevelParent(self).Bind(wx.EVT_CHAR_HOOK, self.OnTopLevelKey)

    def disable(self):
        self.enabled = False
        self.update()

    def enable(self):
        self.enabled = True
        self.update()

    def repeatLast(self):
        if self.lastMove:
            self.moveCallback(*self.lastMove)
        if self.lastCorner:
            self.cornerCallback(self.corner_to_axis[self.lastCorner])

    def clearRepeat(self):
        self.lastMove = None
        self.lastCorner = None

    def distanceToLine(self, pos, x1, y1, x2, y2):
        xlen = x2 - x1
        ylen = y2 - y1
        pxlen = x1 - pos.x
        pylen = y1 - pos.y
        return abs(xlen * pylen - ylen * pxlen) / math.sqrt(xlen ** 2 + ylen ** 2)

    def distanceToPoint(self, x1, y1, x2, y2):
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def cycleKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx

    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()

    def getMovement(self):
        xdir = [1, 0, -1, 0, 0, 0][self.quadrant]
        ydir = [0, 1, 0, -1, 0, 0][self.quadrant]
        zdir = [0, 0, 0, 0, 1, -1][self.quadrant]
        magnitude = math.pow(10, self.concentric - 2)
        if not zdir == 0:
            magnitude = min(magnitude, 10)
        return (magnitude * xdir, magnitude * ydir, magnitude * zdir)

    def lookupConcentric(self, radius):
        idx = 0
        for r in self.concentric_circle_radii[1:]:
            if radius < r:
                return idx
            idx += 1
        return len(self.concentric_circle_radii)

    def getQuadrantConcentricFromPosition(self, pos):
        rel_x = pos[0] - self.center[0]
        rel_y = pos[1] - self.center[1]
        radius = math.sqrt(rel_x ** 2 + rel_y ** 2)
        if rel_x > rel_y and rel_x > -rel_y:
            quadrant = 0  # Right
        elif rel_x <= rel_y and rel_x > -rel_y:
            quadrant = 3  # Down
        elif rel_x > rel_y and rel_x < -rel_y:
            quadrant = 1  # Up
        else:
            quadrant = 2  # Left

        idx = self.lookupConcentric(radius)
        return (quadrant, idx)

    def mouseOverKeypad(self, mpos):
        for idx, kpos in self.keypad_positions.items():
            radius = self.distanceToPoint(mpos[0], mpos[1], kpos[0], kpos[1])
            if radius < 9:
                return idx
        return None

    def drawPartialPie(self, gc, center, r1, r2, angle1, angle2):
        p1 = wx.Point(center.x + r1 * math.cos(angle1), center.y + r1 * math.sin(angle1))

        path = gc.CreatePath()
        path.MoveToPoint(p1.x, p1.y)
        path.AddArc(center.x, center.y, r1, angle1, angle2, True)
        path.AddArc(center.x, center.y, r2, angle2, angle1, False)
        path.AddLineToPoint(p1.x, p1.y)
        gc.DrawPath(path)

    def highlightQuadrant(self, gc, quadrant, concentric):
        assert(quadrant >= 0 and quadrant <= 3)
        assert(concentric >= 0 and concentric <= 4)

        inner_ring_radius = self.concentric_inset
        # fudge = math.pi*0.002
        fudge = -0.02
        center = wx.Point(self.center[0], self.center[1])
        if quadrant == 0:
            a1, a2 = (-math.pi * 0.25, math.pi * 0.25)
            center.x += inner_ring_radius
        elif quadrant == 1:
            a1, a2 = (math.pi * 1.25, math.pi * 1.75)
            center.y -= inner_ring_radius
        elif quadrant == 2:
            a1, a2 = (math.pi * 0.75, math.pi * 1.25)
            center.x -= inner_ring_radius
        elif quadrant == 3:
            a1, a2 = (math.pi * 0.25, math.pi * 0.75)
            center.y += inner_ring_radius

        r1 = self.concentric_circle_radii[concentric]
        r2 = self.concentric_circle_radii[concentric + 1]

        self.drawPartialPie(gc, center, r1 - inner_ring_radius, r2 - inner_ring_radius, a1 + fudge, a2 - fudge)

    def drawCorner(self, gc, x, y, angle = 0.0):
        w, h = self.corner_size

        gc.PushState()
        gc.Translate(x, y)
        gc.Rotate(angle)
        path = gc.CreatePath()
        path.MoveToPoint(-w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2 + h / 4)
        path.AddLineToPoint(w / 12, h / 12)
        path.AddLineToPoint(-w / 2 + w / 4, h / 2)
        path.AddLineToPoint(-w / 2, h / 2)
        path.AddLineToPoint(-w / 2, -h / 2)
        gc.DrawPath(path)
        gc.PopState()

    def highlightCorner(self, gc, corner = 0):
        w, h = self.corner_size
        xinset, yinset = self.corner_inset
        cx, cy = self.center
        ww, wh = self.GetSizeTuple()

        if corner == 0:
            x, y = (cx - ww / 2 + xinset + 1, cy - wh / 2 + yinset)
            self.drawCorner(gc, x + w / 2, y + h / 2, 0)
        elif corner == 1:
            x, y = (cx + ww / 2 - xinset, cy - wh / 2 + yinset)
            self.drawCorner(gc, x - w / 2, y + h / 2, math.pi / 2)
        elif corner == 2:
            x, y = (cx + ww / 2 - xinset, cy + wh / 2 - yinset - 1)
            self.drawCorner(gc, x - w / 2, y - h / 2, math.pi)
        elif corner == 3:
            x, y = (cx - ww / 2 + xinset + 1, cy + wh / 2 - yinset - 1)
            self.drawCorner(gc, x + w / 2, y - h / 2, math.pi * 3 / 2)

    def drawCenteredDisc(self, gc, radius):
        cx, cy = self.center
        gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Brush and pen for grey overlay when mouse hovers over
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))

            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    if self.concentric == 0:
                        self.drawCenteredDisc(gc, self.concentric_circle_radii[1])
                    elif self.quadrant is not None:
                        self.highlightQuadrant(gc, self.quadrant, self.concentric)
                elif self.corner is not None:
                    self.highlightCorner(gc, self.corner)

            if self.keypad_idx >= 0:
                padw, padh = (self.keypad_bmp.GetWidth(), self.keypad_bmp.GetHeight())
                pos = self.keypad_positions[self.keypad_idx]
                pos = (pos[0] - padw / 2 - 3, pos[1] - padh / 2 - 3)
                gc.DrawBitmap(self.keypad_bmp, pos[0], pos[1], padw, padh)

            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 128), 1))
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 128 + 64)))
            for idx, kpos in self.label_overlay_positions.items():
                if idx != self.concentric:
                    r = kpos[2]
                    gc.DrawEllipse(kpos[0] - r, kpos[1] - r, r * 2, r * 2)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)
        # Used to check exact position of keypad dots, should we ever resize the bg image
        # for idx, kpos in self.label_overlay_positions.items():
        #    dc.DrawCircle(kpos[0], kpos[1], kpos[2])

    # ------ #
    # Events #
    # ------ #
    def OnTopLevelKey(self, evt):
        # Let user press escape on any control, and return focus here
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.SetFocus()
        evt.Skip()

    def OnKey(self, evt):
        if not self.enabled:
            return
        if self.keypad_idx >= 0:
            if evt.GetKeyCode() == wx.WXK_TAB:
                self.setKeypadIndex(self.cycleKeypadIndex())
            elif evt.GetKeyCode() == wx.WXK_UP:
                self.quadrant = 1
            elif evt.GetKeyCode() == wx.WXK_DOWN:
                self.quadrant = 3
            elif evt.GetKeyCode() == wx.WXK_LEFT:
                self.quadrant = 2
            elif evt.GetKeyCode() == wx.WXK_RIGHT:
                self.quadrant = 0
            elif evt.GetKeyCode() == wx.WXK_PAGEUP:
                self.quadrant = 4
            elif evt.GetKeyCode() == wx.WXK_PAGEDOWN:
                self.quadrant = 5
            else:
                evt.Skip()
                return

            self.concentric = self.keypad_idx
            x, y, z = self.getMovement()

            if x != 0 or y != 0 and self.moveCallback:
                self.moveCallback(x, y)
            if z != 0 and self.zCallback:
                self.zCallback(z)
        elif evt.GetKeyCode() == wx.WXK_SPACE:
            self.spacebarCallback()

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldcorner = self.corner
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        self.quadrant = None
        self.concentric = None
        if idx is None:
            center = wx.Point(self.center[0], self.center[1])
            riseDist = self.distanceToLine(mpos, center.x - 1, center.y - 1, center.x + 1, center.y + 1)
            fallDist = self.distanceToLine(mpos, center.x - 1, center.y + 1, center.x + 1, center.y - 1)
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)

            # If mouse hovers in space between quadrants, don't commit to a quadrant
            if riseDist <= self.spacer or fallDist <= self.spacer:
                self.quadrant = None

        cx, cy = self.center
        if mpos.x < cx and mpos.y < cy:
            self.corner = 0
        if mpos.x >= cx and mpos.y < cy:
            self.corner = 1
        if mpos.x >= cx and mpos.y >= cy:
            self.corner = 2
        if mpos.x < cx and mpos.y >= cy:
            self.corner = 3

        if oldq != self.quadrant or oldc != self.concentric or oldcorner != self.corner:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        # Take focus when clicked so that arrow keys can control movement
        self.SetFocus()

        mpos = event.GetPosition()

        idx = self.mouseOverKeypad(mpos)
        if idx is None:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    if self.concentric == 0:
                        self.lastCorner = -1
                        self.lastMove = None
                        self.cornerCallback(self.corner_to_axis[-1])
                    elif self.quadrant is not None:
                        x, y, z = self.getMovement()
                        if self.moveCallback:
                            self.lastMove = (x, y)
                            self.lastCorner = None
                            self.moveCallback(x, y)
                elif self.corner is not None:
                    if self.cornerCallback:
                        self.lastCorner = self.corner
                        self.lastMove = None
                        self.cornerCallback(self.corner_to_axis[self.corner])
        else:
            if self.keypad_idx == idx:
                self.setKeypadIndex(-1)
            else:
                self.setKeypadIndex(idx)

    def OnLeaveWindow(self, evt):
        self.quadrant = None
        self.concentric = None
        self.update()

class XYButtonsMini(XYButtons):
    imagename = "control_mini.png"
    center = (57, 56.5)
    concentric_circle_radii = [0, 30.3]
    corner_inset = (5, 5)
    corner_size = (50, 50)
    outer_radius = 31
    corner_to_axis = {
        0: "x",
        1: "z",
        2: "y",
        3: "xy",
    }

    def bind_events(self):
        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldcorner = self.corner
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()

        self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)

        cx, cy = XYButtonsMini.center
        if mpos.x < cx and mpos.y < cy:
            self.corner = 0
        if mpos.x >= cx and mpos.y < cy:
            self.corner = 1
        if mpos.x >= cx and mpos.y >= cy:
            self.corner = 2
        if mpos.x < cx and mpos.y >= cy:
            self.corner = 3

        if oldq != self.quadrant or oldc != self.concentric or oldcorner != self.corner:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        # Take focus when clicked so that arrow keys can control movement
        self.SetFocus()

        mpos = event.GetPosition()

        self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
        if self.concentric is not None:
            if self.concentric < len(self.concentric_circle_radii):
                self.cornerCallback("all")
            elif self.corner is not None:
                if self.cornerCallback:
                    self.lastCorner = self.corner
                    self.lastMove = None
                    self.cornerCallback(self.corner_to_axis[self.corner])

    def drawCorner(self, gc, x, y, angle = 0.0):
        w, h = self.corner_size

        gc.PushState()
        gc.Translate(x, y)
        gc.Rotate(angle)
        path = gc.CreatePath()
        path.MoveToPoint(-w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2 + h / 4)
        path.AddArc(w / 2, h / 2, self.outer_radius, 3 * math.pi / 2, math.pi, False)
        path.AddLineToPoint(-w / 2, h / 2)
        path.AddLineToPoint(-w / 2, -h / 2)
        gc.DrawPath(path)
        gc.PopState()

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Brush and pen for grey overlay when mouse hovers over
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))

            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    self.drawCenteredDisc(gc, self.concentric_circle_radii[-1])
                elif self.corner is not None:
                    self.highlightCorner(gc, self.corner)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)

########NEW FILE########
__FILENAME__ = zbuttons
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
from .bufferedcanvas import BufferedCanvas
from printrun.utils import imagefile

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class ZButtons(BufferedCanvas):
    button_ydistances = [7, 30, 55, 83]  # ,112
    move_values = [0.1, 1, 10]
    center = (30, 118)
    label_overlay_positions = {
        0: (1.1, 18, 9),
        1: (1.1, 41.5, 10.6),
        2: (1.1, 68, 13),
    }
    imagename = "control_z.png"

    def __init__(self, parent, moveCallback = None, bgcolor = "#FFFFFF", ID=-1):
        self.bg_bmp = wx.Image(imagefile(self.imagename), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.range = None
        self.direction = None
        self.orderOfMagnitudeIdx = 0  # 0 means '1', 1 means '10', 2 means '100', etc.
        self.moveCallback = moveCallback
        self.enabled = False
        # Remember the last clicked value, so we can repeat when spacebar pressed
        self.lastValue = None

        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.bgcolormask = wx.Colour(self.bgcolor.Red(), self.bgcolor.Green(), self.bgcolor.Blue(), 128)

        BufferedCanvas.__init__(self, parent, ID, size=self.bg_bmp.GetSize())

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

    def disable(self):
        self.enabled = False
        self.update()

    def enable(self):
        self.enabled = True
        self.update()

    def repeatLast(self):
        if self.lastValue:
            self.moveCallback(self.lastValue)

    def clearRepeat(self):
        self.lastValue = None

    def lookupRange(self, ydist):
        idx = -1
        for d in self.button_ydistances:
            if ydist < d:
                return idx
            idx += 1
        return None

    def highlight(self, gc, rng, dir):
        assert(rng >= -1 and rng <= 3)
        assert(dir >= -1 and dir <= 1)

        fudge = 11
        x = 0 + fudge
        w = 59 - fudge * 2
        if rng >= 0:
            k = 1 if dir > 0 else 0
            y = self.center[1] - (dir * self.button_ydistances[rng + k])
            h = self.button_ydistances[rng + 1] - self.button_ydistances[rng]
            gc.DrawRoundedRectangle(x, y, w, h, 4)
            # gc.DrawRectangle(x, y, w, h)
        # self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)

    def getRangeDir(self, pos):
        ydelta = self.center[1] - pos[1]
        return (self.lookupRange(abs(ydelta)), sign(ydelta))

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 128), 1))
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 128 + 64)))
            for idx, kpos in self.label_overlay_positions.items():
                if idx != self.range:
                    r = kpos[2]
                    gc.DrawEllipse(self.center[0] - kpos[0] - r, self.center[1] - kpos[1] - r, r * 2, r * 2)

            # Top 'layer' is the mouse-over highlights
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))
            if self.range is not None and self.direction is not None:
                self.highlight(gc, self.range, self.direction)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)

    # ------ #
    # Events #
    # ------ #

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldr, oldd = self.range, self.direction

        mpos = event.GetPosition()
        self.range, self.direction = self.getRangeDir(mpos)

        if oldr != self.range or oldd != self.direction:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        mpos = event.GetPosition()
        r, d = self.getRangeDir(mpos)
        if r >= 0:
            value = d * self.move_values[r]
            if self.moveCallback:
                self.lastValue = value
                self.moveCallback(value)

    def OnLeaveWindow(self, evt):
        self.range = None
        self.direction = None
        self.update()

class ZButtonsMini(ZButtons):
    button_ydistances = [7, 30, 55]
    center = (30, 84)
    label_overlay_positions = {
        0: (1, 18, 9),
        1: (1, 42.8, 12.9),
    }
    imagename = "control_z_mini.png"
    move_values = [0.1, 10]

########NEW FILE########
__FILENAME__ = gviz
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from Queue import Queue
from collections import deque
import wx
import time
from . import gcoder
from .injectgcode import injector, injector_edit

from .utils import imagefile, install_locale, get_home_pos
install_locale('pronterface')

class GvizBaseFrame(wx.Frame):

    def create_base_ui(self):
        self.CreateStatusBar(1)
        self.SetStatusText(_("Layer number and Z position show here when you scroll"))

        hpanel = wx.Panel(self, -1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        panel = wx.Panel(hpanel, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(panel, -1, style = wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_HORZ_TEXT)
        self.toolbar.AddSimpleTool(1, wx.Image(imagefile('zoom_in.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom In [+]"), '')
        self.toolbar.AddSimpleTool(2, wx.Image(imagefile('zoom_out.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom Out [-]"), '')
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(3, wx.Image(imagefile('arrow_up.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Up a Layer [U]"), '')
        self.toolbar.AddSimpleTool(4, wx.Image(imagefile('arrow_down.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Down a Layer [D]"), '')
        self.toolbar.AddLabelTool(5, " " + _("Reset view"), wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), shortHelp = _("Reset view"), longHelp = '')
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(6, wx.Image(imagefile('inject.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), shortHelpString = _("Inject G-Code"), longHelpString = _("Insert code at the beginning of this layer"))
        self.toolbar.AddSimpleTool(7, wx.Image(imagefile('edit.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), shortHelpString = _("Edit layer"), longHelpString = _("Edit the G-Code of this layer"))

        vbox.Add(self.toolbar, 0, border = 5)

        panel.SetSizer(vbox)

        hbox.Add(panel, 1, flag = wx.EXPAND)
        self.layerslider = wx.Slider(hpanel, style = wx.SL_VERTICAL | wx.SL_AUTOTICKS | wx.SL_LEFT | wx.SL_INVERSE)
        self.layerslider.Bind(wx.EVT_SCROLL, self.process_slider)
        hbox.Add(self.layerslider, 0, border = 5, flag = wx.LEFT | wx.EXPAND)
        hpanel.SetSizer(hbox)

        return panel, vbox

    def setlayercb(self, layer):
        self.layerslider.SetValue(layer)

    def process_slider(self, event):
        raise NotImplementedError

ID_ABOUT = 101
ID_EXIT = 110
class GvizWindow(GvizBaseFrame):
    def __init__(self, f = None, size = (600, 600), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5, bgcolor = "#000000"):
        super(GvizWindow, self).__init__(None, title = _("Gcode view, shift to move view, mousewheel to set layer"), size = size)

        panel, vbox = self.create_base_ui()

        self.p = Gviz(panel, size = size, build_dimensions = build_dimensions, grid = grid, extrusion_width = extrusion_width, bgcolor = bgcolor, realparent = self)

        self.toolbar.Realize()
        vbox.Add(self.p, 1, wx.EXPAND)

        self.SetMinSize(self.ClientToWindowSize(vbox.GetMinSize()))
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, self.resetview, id = 5)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.inject(), id = 6)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.editlayer(), id = 7)

        self.initpos = None
        self.p.Bind(wx.EVT_KEY_DOWN, self.key)
        self.Bind(wx.EVT_KEY_DOWN, self.key)
        self.p.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.p.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)

        if f:
            gcode = gcoder.GCode(f, get_home_pos(self.p.build_dimensions))
            self.p.addfile(gcode)

    def set_current_gline(self, gline):
        return

    def process_slider(self, event):
        self.p.layerindex = self.layerslider.GetValue()
        z = self.p.get_currentz()
        wx.CallAfter(self.SetStatusText, _("Layer %d - Z = %.03f mm") % (self.p.layerindex + 1, z), 0)
        self.p.dirty = True
        wx.CallAfter(self.p.Refresh)

    def resetview(self, event):
        self.p.translate = [0.0, 0.0]
        self.p.scale = self.p.basescale
        self.p.zoom(0, 0, 1.0)

    def mouse(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT) or event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None
        elif event.Dragging():
            e = event.GetPositionTuple()
            if self.initpos is None:
                self.initpos = e
                self.basetrans = self.p.translate
            self.p.translate = [self.basetrans[0] + (e[0] - self.initpos[0]),
                                self.basetrans[1] + (e[1] - self.initpos[1])]
            self.p.dirty = True
            wx.CallAfter(self.p.Refresh)
        else:
            event.Skip()

    def key(self, event):
        #  Keycode definitions
        kup = [85, 315]               # Up keys
        kdo = [68, 317]               # Down Keys
        kzi = [388, 316, 61]        # Zoom In Keys
        kzo = [390, 314, 45]       # Zoom Out Keys
        x = event.GetKeyCode()
        cx, cy = self.p.translate
        if x in kup:
            self.p.layerup()
        if x in kdo:
            self.p.layerdown()
        if x in kzi:
            self.p.zoom(cx, cy, 1.2)
        if x in kzo:
            self.p.zoom(cx, cy, 1 / 1.2)

    def zoom(self, event):
        z = event.GetWheelRotation()
        if event.ShiftDown():
            if z > 0: self.p.layerdown()
            elif z < 0: self.p.layerup()
        else:
            if z > 0: self.p.zoom(event.GetX(), event.GetY(), 1.2)
            elif z < 0: self.p.zoom(event.GetX(), event.GetY(), 1 / 1.2)

class Gviz(wx.Panel):

    # Mark canvas as dirty when setting showall
    _showall = 0

    def _get_showall(self):
        return self._showall

    def _set_showall(self, showall):
        if showall != self._showall:
            self.dirty = True
            self._showall = showall
    showall = property(_get_showall, _set_showall)

    def __init__(self, parent, size = (200, 200), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5, bgcolor = "#000000", realparent = None):
        wx.Panel.__init__(self, parent, -1)
        self.widget = self
        size = [max(1.0, x) for x in size]
        ratio = size[0] / size[1]
        self.SetMinSize((150, 150 / ratio))
        self.parent = realparent if realparent else parent
        self.size = size
        self.build_dimensions = build_dimensions
        self.grid = grid
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)
        self.hilight = deque()
        self.hilightarcs = deque()
        self.hilightqueue = Queue(0)
        self.hilightarcsqueue = Queue(0)
        self.clear()
        self.filament_width = extrusion_width  # set it to 0 to disable scaling lines with zoom
        self.update_basescale()
        self.scale = self.basescale
        penwidth = max(1.0, self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0))
        self.translate = [0.0, 0.0]
        self.mainpen = wx.Pen(wx.Colour(0, 0, 0), penwidth)
        self.arcpen = wx.Pen(wx.Colour(255, 0, 0), penwidth)
        self.travelpen = wx.Pen(wx.Colour(10, 80, 80), penwidth)
        self.hlpen = wx.Pen(wx.Colour(200, 50, 50), penwidth)
        self.fades = [wx.Pen(wx.Colour(250 - 0.6 ** i * 100, 250 - 0.6 ** i * 100, 200 - 0.4 ** i * 50), penwidth) for i in xrange(6)]
        self.penslist = [self.mainpen, self.travelpen, self.hlpen] + self.fades
        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.blitmap = wx.EmptyBitmap(self.GetClientSize()[0], self.GetClientSize()[1], -1)
        self.paint_overlay = None

    def inject(self):
        layer = self.layers.index(self.layerindex)
        injector(self.gcode, self.layerindex, layer)

    def editlayer(self):
        layer = self.layers.index(self.layerindex)
        injector_edit(self.gcode, self.layerindex, layer)

    def clearhilights(self):
        self.hilight.clear()
        self.hilightarcs.clear()
        while not self.hilightqueue.empty():
            self.hilightqueue.get_nowait()
        while not self.hilightarcsqueue.empty():
            self.hilightarcsqueue.get_nowait()

    def clear(self):
        self.gcode = None
        self.lastpos = [0, 0, 0, 0, 0, 0, 0]
        self.hilightpos = self.lastpos[:]
        self.gcoder = gcoder.GCode([], get_home_pos(self.build_dimensions))
        self.lines = {}
        self.pens = {}
        self.arcs = {}
        self.arcpens = {}
        self.layers = {}
        self.layersz = []
        self.clearhilights()
        self.layerindex = 0
        self.showall = 0
        self.dirty = True
        self.partial = False
        self.painted_layers = set()
        wx.CallAfter(self.Refresh)

    def get_currentz(self):
        z = self.layersz[self.layerindex]
        z = 0. if z is None else z
        return z

    def layerup(self):
        if self.layerindex + 1 < len(self.layers):
            self.layerindex += 1
            z = self.get_currentz()
            wx.CallAfter(self.parent.SetStatusText, _("Layer %d - Going Up - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = True
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def layerdown(self):
        if self.layerindex > 0:
            self.layerindex -= 1
            z = self.get_currentz()
            wx.CallAfter(self.parent.SetStatusText, _("Layer %d - Going Down - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = True
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def setlayer(self, layer):
        if layer in self.layers:
            self.clearhilights()
            self.layerindex = self.layers[layer]
            self.dirty = True
            self.showall = 0
            wx.CallAfter(self.Refresh)

    def update_basescale(self):
        self.basescale = 2 * [min(float(self.size[0] - 1) / self.build_dimensions[0],
                                  float(self.size[1] - 1) / self.build_dimensions[1])]

    def resize(self, event):
        old_basescale = self.basescale
        width, height = self.GetClientSizeTuple()
        if width < 1 or height < 1:
            return
        self.size = (width, height)
        self.update_basescale()
        zoomratio = float(self.basescale[0]) / old_basescale[0]
        wx.CallLater(200, self.zoom, 0, 0, zoomratio)

    def zoom(self, x, y, factor):
        if x == -1 and y == -1:
            side = min(self.size)
            x = y = side / 2
        self.scale = [s * factor for s in self.scale]

        self.translate = [x - (x - self.translate[0]) * factor,
                          y - (y - self.translate[1]) * factor]
        penwidth = max(1.0, self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0))
        for pen in self.penslist:
            pen.SetWidth(penwidth)
        self.dirty = True
        wx.CallAfter(self.Refresh)

    def _line_scaler(self, x):
        return (self.scale[0] * x[0],
                self.scale[1] * x[1],
                self.scale[0] * x[2],
                self.scale[1] * x[3],)

    def _arc_scaler(self, x):
        return (self.scale[0] * x[0],
                self.scale[1] * x[1],
                self.scale[0] * x[2],
                self.scale[1] * x[3],
                self.scale[0] * x[4],
                self.scale[1] * x[5],)

    def _drawlines(self, dc, lines, pens):
        scaled_lines = map(self._line_scaler, lines)
        dc.DrawLineList(scaled_lines, pens)

    def _drawarcs(self, dc, arcs, pens):
        scaled_arcs = map(self._arc_scaler, arcs)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        for i in range(len(scaled_arcs)):
            dc.SetPen(pens[i] if type(pens) == list else pens)
            dc.DrawArc(*scaled_arcs[i])

    def repaint_everything(self):
        width = self.scale[0] * self.build_dimensions[0]
        height = self.scale[1] * self.build_dimensions[1]
        self.blitmap = wx.EmptyBitmap(width + 1, height + 1, -1)
        dc = wx.MemoryDC()
        dc.SelectObject(self.blitmap)
        dc.SetBackground(wx.Brush((250, 250, 200)))
        dc.Clear()
        dc.SetPen(wx.Pen(wx.Colour(180, 180, 150)))
        for grid_unit in self.grid:
            if grid_unit > 0:
                for x in xrange(int(self.build_dimensions[0] / grid_unit) + 1):
                    draw_x = self.scale[0] * x * grid_unit
                    dc.DrawLine(draw_x, 0, draw_x, height)
                for y in xrange(int(self.build_dimensions[1] / grid_unit) + 1):
                    draw_y = self.scale[1] * (self.build_dimensions[1] - y * grid_unit)
                    dc.DrawLine(0, draw_y, width, draw_y)
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))

        if not self.showall:
            # Draw layer gauge
            dc.SetBrush(wx.Brush((43, 144, 255)))
            dc.DrawRectangle(width - 15, 0, 15, height)
            dc.SetBrush(wx.Brush((0, 255, 0)))
            if self.layers:
                dc.DrawRectangle(width - 14, (1.0 - (1.0 * (self.layerindex + 1)) / len(self.layers)) * height, 13, height - 1)

        if self.showall:
            for i in range(len(self.layersz)):
                self.painted_layers.add(i)
                self._drawlines(dc, self.lines[i], self.pens[i])
                self._drawarcs(dc, self.arcs[i], self.arcpens[i])
            dc.SelectObject(wx.NullBitmap)
            return

        if self.layerindex < len(self.layers) and self.layerindex in self.lines:
            for layer_i in range(max(0, self.layerindex - 6), self.layerindex):
                self._drawlines(dc, self.lines[layer_i], self.fades[self.layerindex - layer_i - 1])
                self._drawarcs(dc, self.arcs[layer_i], self.fades[self.layerindex - layer_i - 1])
            self._drawlines(dc, self.lines[self.layerindex], self.pens[self.layerindex])
            self._drawarcs(dc, self.arcs[self.layerindex], self.arcpens[self.layerindex])

        self._drawlines(dc, self.hilight, self.hlpen)
        self._drawarcs(dc, self.hilightarcs, self.hlpen)

        self.paint_hilights(dc)

        dc.SelectObject(wx.NullBitmap)

    def repaint_partial(self):
        if self.showall:
            dc = wx.MemoryDC()
            dc.SelectObject(self.blitmap)
            for i in set(range(len(self.layersz))).difference(self.painted_layers):
                self.painted_layers.add(i)
                self._drawlines(dc, self.lines[i], self.pens[i])
                self._drawarcs(dc, self.arcs[i], self.arcpens[i])
            dc.SelectObject(wx.NullBitmap)

    def paint_hilights(self, dc = None):
        if self.hilightqueue.empty() and self.hilightarcsqueue.empty():
            return
        hl = []
        if not dc:
            dc = wx.MemoryDC()
            dc.SelectObject(self.blitmap)
        while not self.hilightqueue.empty():
            hl.append(self.hilightqueue.get_nowait())
        self._drawlines(dc, hl, self.hlpen)
        hlarcs = []
        while not self.hilightarcsqueue.empty():
            hlarcs.append(self.hilightarcsqueue.get_nowait())
        self._drawarcs(dc, hlarcs, self.hlpen)
        dc.SelectObject(wx.NullBitmap)

    def paint(self, event):
        if self.dirty:
            self.dirty = False
            self.partial = False
            self.repaint_everything()
        elif self.partial:
            self.partial = False
            self.repaint_partial()
        self.paint_hilights()
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        dc.DrawBitmap(self.blitmap, self.translate[0], self.translate[1])
        if self.paint_overlay:
            self.paint_overlay(dc)

    def addfile_perlayer(self, gcode, showall = False):
        self.clear()
        self.gcode = gcode
        self.showall = showall
        generator = self.add_parsed_gcodes(gcode)
        generator_output = generator.next()
        while generator_output is not None:
            yield generator_output
            generator_output = generator.next()
        max_layers = len(self.layers)
        if hasattr(self.parent, "layerslider"):
            self.parent.layerslider.SetRange(0, max_layers - 1)
            self.parent.layerslider.SetValue(0)
        yield None

    def addfile(self, gcode = None, showall = False):
        generator = self.addfile_perlayer(gcode, showall)
        while generator.next() is not None:
            continue

    def _get_movement(self, start_pos, gline):
        """Takes a start position and a gcode, and returns a 3-uple containing
        (final position, line, arc), with line and arc being None if not
        used"""
        target = start_pos[:]
        target[5] = 0.0
        target[6] = 0.0
        if gline.current_x is not None: target[0] = gline.current_x
        if gline.current_y is not None: target[1] = gline.current_y
        if gline.current_z is not None: target[2] = gline.current_z
        if gline.e is not None:
            if gline.relative_e:
                target[3] += gline.e
            else:
                target[3] = gline.e
        if gline.f is not None: target[4] = gline.f
        if gline.i is not None: target[5] = gline.i
        if gline.j is not None: target[6] = gline.j

        if gline.command in ["G0", "G1"]:
            line = [self._x(start_pos[0]),
                    self._y(start_pos[1]),
                    self._x(target[0]),
                    self._y(target[1])]
            return target, line, None
        elif gline.command in ["G2", "G3"]:
            # startpos, endpos, arc center
            arc = [self._x(start_pos[0]), self._y(start_pos[1]),
                   self._x(target[0]), self._y(target[1]),
                   self._x(start_pos[0] + target[5]), self._y(start_pos[1] + target[6])]
            if gline.command == "G2":  # clockwise, reverse endpoints
                arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]
            return target, None, arc

    def _y(self, y):
        return self.build_dimensions[1] - (y - self.build_dimensions[4])

    def _x(self, x):
        return x - self.build_dimensions[3]

    def add_parsed_gcodes(self, gcode):
        start_time = time.time()

        layer_idx = 0
        while layer_idx < len(gcode.all_layers):
            layer = gcode.all_layers[layer_idx]
            has_move = False
            for gline in layer:
                if gline.is_move:
                    has_move = True
                    break
            if not has_move:
                yield layer_idx
                layer_idx += 1
                continue
            viz_layer = len(self.layers)
            self.lines[viz_layer] = []
            self.pens[viz_layer] = []
            self.arcs[viz_layer] = []
            self.arcpens[viz_layer] = []
            for gline in layer:
                if not gline.is_move:
                    continue

                target, line, arc = self._get_movement(self.lastpos[:], gline)

                if line is not None:
                    self.lines[viz_layer].append(line)
                    self.pens[viz_layer].append(self.mainpen if target[3] != self.lastpos[3] else self.travelpen)
                elif arc is not None:
                    self.arcs[viz_layer].append(arc)
                    self.arcpens[viz_layer].append(self.arcpen)

                self.lastpos = target
            # Only add layer to self.layers now to prevent the display of an
            # unfinished layer
            self.layers[layer_idx] = viz_layer
            self.layersz.append(layer.z)

            # Refresh display if more than 0.2s have passed
            if time.time() - start_time > 0.2:
                start_time = time.time()
                self.partial = True
                wx.CallAfter(self.Refresh)

            yield layer_idx
            layer_idx += 1

        self.dirty = True
        wx.CallAfter(self.Refresh)
        yield None

    def addgcodehighlight(self, gcode = "M105"):
        gcode = gcode.split("*")[0]
        gcode = gcode.split(";")[0]
        gcode = gcode.lower().strip()
        if not gcode:
            return
        gline = self.gcoder.append(gcode, store = False)

        if gline.command not in ["G0", "G1", "G2", "G3"]:
            return

        target, line, arc = self._get_movement(self.hilightpos[:], gline)

        if line is not None:
            self.hilight.append(line)
            self.hilightqueue.put_nowait(line)
        elif arc is not None:
            self.hilightarcs.append(arc)
            self.hilightarcsqueue.put_nowait(arc)

        self.hilightpos = target
        wx.CallAfter(self.Refresh)

if __name__ == '__main__':
    import sys
    app = wx.App(False)
    main = GvizWindow(open(sys.argv[1], "rU"))
    main.Show()
    app.MainLoop()

########NEW FILE########
__FILENAME__ = injectgcode
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from .gui.widgets import MacroEditor

from .utils import install_locale
install_locale('pronterface')

def injector(gcode, viz_layer, layer_idx):
    cb = lambda toadd: inject(gcode, viz_layer, layer_idx, toadd)
    z = gcode.all_layers[layer_idx].z
    z = z if z is not None else 0
    MacroEditor(_("Inject G-Code at layer %d (Z = %.03f)") % (viz_layer, z), "", cb, True)

def injector_edit(gcode, viz_layer, layer_idx):
    cb = lambda toadd: rewritelayer(gcode, viz_layer, layer_idx, toadd)
    layer = gcode.all_layers[layer_idx]
    z = layer.z
    z = z if z is not None else 0
    lines = [line.raw for line in layer]
    MacroEditor(_("Edit G-Code of layer %d (Z = %.03f)") % (viz_layer, z), lines, cb, True)

def inject(gcode, viz_layer, layer_idx, toadd):
    # TODO: save modified gcode after injection ?
    nlines = len(gcode.prepend_to_layer(toadd, layer_idx))
    print _("Successfully injected %d lines at beginning of layer %d") % (nlines, viz_layer)

def rewritelayer(gcode, viz_layer, layer_idx, toadd):
    # TODO: save modified gcode after edit ?
    nlines = len(gcode.rewrite_layer(toadd, layer_idx))
    print _("Successfully edited layer %d (which now contains %d lines)") % (viz_layer, nlines)

########NEW FILE########
__FILENAME__ = objectplater
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from .utils import install_locale, iconfile
install_locale('plater')

import os
import types
import wx

def patch_method(obj, method, replacement):
    orig_handler = getattr(obj, method)

    def wrapped(*a, **kwargs):
        kwargs['orig_handler'] = orig_handler
        return replacement(*a, **kwargs)
    setattr(obj, method, types.MethodType(wrapped, obj))

class Plater(wx.Frame):
    def __init__(self, filenames = [], size = (800, 580), callback = None, parent = None, build_dimensions = None):
        super(Plater, self).__init__(parent, title = _("Plate building tool"), size = size)
        self.filenames = filenames
        self.SetIcon(wx.Icon(iconfile("plater.png"), wx.BITMAP_TYPE_PNG))
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        panel = self.menupanel = wx.Panel(self, -1)
        sizer = self.menusizer = wx.GridBagSizer()
        self.l = wx.ListBox(panel)
        sizer.Add(self.l, pos = (1, 0), span = (1, 2), flag = wx.EXPAND)
        sizer.AddGrowableRow(1, 1)
        # Clear button
        clearbutton = wx.Button(panel, label = _("Clear"))
        clearbutton.Bind(wx.EVT_BUTTON, self.clear)
        sizer.Add(clearbutton, pos = (2, 0), span = (1, 2), flag = wx.EXPAND)
        # Load button
        loadbutton = wx.Button(panel, label = _("Load"))
        loadbutton.Bind(wx.EVT_BUTTON, self.load)
        sizer.Add(loadbutton, pos = (0, 0), span = (1, 1), flag = wx.EXPAND)
        # Snap to Z = 0 button
        snapbutton = wx.Button(panel, label = _("Snap to Z = 0"))
        snapbutton.Bind(wx.EVT_BUTTON, self.snap)
        sizer.Add(snapbutton, pos = (3, 0), span = (1, 1), flag = wx.EXPAND)
        # Put at center button
        centerbutton = wx.Button(panel, label = _("Put at center"))
        centerbutton.Bind(wx.EVT_BUTTON, self.center)
        sizer.Add(centerbutton, pos = (3, 1), span = (1, 1), flag = wx.EXPAND)
        # Delete button
        deletebutton = wx.Button(panel, label = _("Delete"))
        deletebutton.Bind(wx.EVT_BUTTON, self.delete)
        sizer.Add(deletebutton, pos = (4, 0), span = (1, 1), flag = wx.EXPAND)
        # Auto arrange button
        autobutton = wx.Button(panel, label = _("Auto arrange"))
        autobutton.Bind(wx.EVT_BUTTON, self.autoplate)
        sizer.Add(autobutton, pos = (5, 0), span = (1, 2), flag = wx.EXPAND)
        # Export button
        exportbutton = wx.Button(panel, label = _("Export"))
        exportbutton.Bind(wx.EVT_BUTTON, self.export)
        sizer.Add(exportbutton, pos = (0, 1), span = (1, 1), flag = wx.EXPAND)
        if callback is not None:
            donebutton = wx.Button(panel, label = _("Done"))
            donebutton.Bind(wx.EVT_BUTTON, lambda e: self.done(e, callback))
            sizer.Add(donebutton, pos = (6, 0), span = (1, 1), flag = wx.EXPAND)
            cancelbutton = wx.Button(panel, label = _("Cancel"))
            cancelbutton.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
            sizer.Add(cancelbutton, pos = (6, 1), span = (1, 1), flag = wx.EXPAND)
        self.basedir = "."
        self.models = {}
        panel.SetSizerAndFit(sizer)
        self.mainsizer.Add(panel, flag = wx.EXPAND)
        self.SetSizer(self.mainsizer)
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]

    def set_viewer(self, viewer):
        # Patch handle_rotation on the fly
        if hasattr(viewer, "handle_rotation"):
            def handle_rotation(self, event, orig_handler):
                if self.initpos is None:
                    self.initpos = event.GetPositionTuple()
                else:
                    if not event.ShiftDown():
                        p1 = self.initpos
                        p2 = event.GetPositionTuple()
                        x1, y1, _ = self.mouse_to_3d(p1[0], p1[1])
                        x2, y2, _ = self.mouse_to_3d(p2[0], p2[1])
                        self.parent.move_shape((x2 - x1, y2 - y1))
                        self.initpos = p2
                    else:
                        orig_handler(event)
            patch_method(viewer, "handle_rotation", handle_rotation)
        # Patch handle_wheel on the fly
        if hasattr(viewer, "handle_wheel"):
            def handle_wheel(self, event, orig_handler):
                if not event.ShiftDown():
                    delta = event.GetWheelRotation()
                    angle = 10
                    if delta > 0:
                        self.parent.rotate_shape(angle / 2)
                    else:
                        self.parent.rotate_shape(-angle / 2)
                else:
                    orig_handler(event)
            patch_method(viewer, "handle_wheel", handle_wheel)
        self.s = viewer
        self.mainsizer.Add(self.s, 1, wx.EXPAND)

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False

        name = self.l.GetString(name)

        model = self.models[name]
        model.offsets = [model.offsets[0] + delta[0],
                         model.offsets[1] + delta[1],
                         model.offsets[2]
                         ]
        return True

    def rotate_shape(self, angle):
        """rotates acive shape
        positive angle is clockwise
        """
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.l.GetString(name)
        model = self.models[name]
        model.rot += angle

    def autoplate(self, event = None):
        print _("Autoplating")
        separation = 2
        try:
            from printrun import packer
            p = packer.Packer()
            for i in self.models:
                width = abs(self.models[i].dims[0] - self.models[i].dims[1])
                height = abs(self.models[i].dims[2] - self.models[i].dims[3])
                p.add_rect(width, height, data = i)
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            rects = p.pack(padding = separation,
                           center = packer.Vector2(centerx, centery))
            for rect in rects:
                i = rect.data
                position = rect.center()
                self.models[i].offsets[0] = position.x
                self.models[i].offsets[1] = position.y
        except ImportError:
            bedsize = self.build_dimensions[0:3]
            cursor = [0, 0, 0]
            newrow = 0
            max = [0, 0]
            for i in self.models:
                self.models[i].offsets[2] = -1.0 * self.models[i].dims[4]
                x = abs(self.models[i].dims[0] - self.models[i].dims[1])
                y = abs(self.models[i].dims[2] - self.models[i].dims[3])
                centre = [x / 2, y / 2]
                centreoffset = [self.models[i].dims[0] + centre[0],
                                self.models[i].dims[2] + centre[1]]
                if (cursor[0] + x + separation) >= bedsize[0]:
                    cursor[0] = 0
                    cursor[1] += newrow + separation
                    newrow = 0
                if (newrow == 0) or (newrow < y):
                    newrow = y
                # To the person who works out why the offsets are applied
                # differently here:
                #    Good job, it confused the hell out of me.
                self.models[i].offsets[0] = cursor[0] + centre[0] - centreoffset[0]
                self.models[i].offsets[1] = cursor[1] + centre[1] - centreoffset[1]
                if (max[0] == 0) or (max[0] < (cursor[0] + x)):
                    max[0] = cursor[0] + x
                if (max[1] == 0) or (max[1] < (cursor[1] + x)):
                    max[1] = cursor[1] + x
                cursor[0] += x + separation
                if (cursor[1] + y) >= bedsize[1]:
                    print _("Bed full, sorry sir :(")
                    self.Refresh()
                    return
            centreoffset = [(bedsize[0] - max[0]) / 2, (bedsize[1] - max[1]) / 2]
            for i in self.models:
                self.models[i].offsets[0] += centreoffset[0]
                self.models[i].offsets[1] += centreoffset[1]
        self.Refresh()

    def clear(self, event):
        result = wx.MessageBox(_('Are you sure you want to clear the grid? All unsaved changes will be lost.'),
                               _('Clear the grid?'),
                               wx.YES_NO | wx.ICON_QUESTION)
        if result == 2:
            self.models = {}
            self.l.Clear()
            self.Refresh()

    def center(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            m.offsets = [centerx, centery, m.offsets[2]]
            self.Refresh()

    def snap(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            m.offsets[2] = -m.dims[4]
            self.Refresh()

    def delete(self, event):
        i = self.l.GetSelection()
        if i != -1:
            del self.models[self.l.GetString(i)]
            self.l.Delete(i)
            self.l.Select(self.l.GetCount() - 1)
            self.Refresh()

    def add_model(self, name, model):
        newname = os.path.split(name.lower())[1]
        if not isinstance(newname, unicode):
            newname = unicode(newname, "utf-8")
        c = 1
        while newname in self.models:
            newname = os.path.split(name.lower())[1]
            newname = newname + "(%d)" % c
            c += 1
        self.models[newname] = model

        self.l.Append(newname)
        i = self.l.GetSelection()
        if i == wx.NOT_FOUND:
            self.l.Select(0)

        self.l.Select(self.l.GetCount() - 1)

    def load(self, event):
        dlg = wx.FileDialog(self, _("Pick file to load"), self.basedir, style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(self.load_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.load_file(name)
        dlg.Destroy()

    def load_file(self, filename):
        raise NotImplementedError

    def export(self, event):
        dlg = wx.FileDialog(self, _("Pick file to save to"), self.basedir, style = wx.FD_SAVE)
        dlg.SetWildcard(self.save_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.export_to(name)
        dlg.Destroy()

    def export_to(self, name):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = packer
# Imported from python-rectangle-packer commit 32fce1aaba
# https://github.com/maxretter/python-rectangle-packer
#
# Python Rectangle Packer - Packs rectangles around a central point
# Copyright (C) 2013 Max Retter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import math

import Polygon
import Polygon.Utils


class Vector2(object):
    """Simple 2d vector / point class."""

    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def add(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def sub(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def scale(self, factor):
        return Vector2(self.x * factor, self.y * factor)

    def magnitude(self):
        return math.sqrt(self.dot_product(self))

    def unit(self):
        """Build unit vector."""
        return self.scale(1 / self.magnitude())

    def dot_product(self, other):
        return self.x * other.x + self.y * other.y

    def distance(self, other):
        """Distance forumla for other point."""
        return math.sqrt(
            (other.x - self.x) ** 2 +
            (other.y - self.y) ** 2
        )


class Rect(object):
    """Simple rectangle object."""
    def __init__(self, width, height, data={}):
        self.width = width
        self.height = height
        self.data = data

        # upper left
        self.position = Vector2()

    def half(self):
        """Half width and height."""
        return Vector2(
            self.width / 2,
            self.height / 2
        )

    def expand(self, width, height):
        """Builds a new rectangle based on this one with given offsets."""
        expanded = Rect(self.width + width, self.height + height)
        expanded.set_center(self.center())

        return expanded

    def point_list(self):
        top = self.position.y
        right = self.position.x + self.width
        bottom = self.position.y + self.height
        left = self.position.x

        return PointList([
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom),
        ])

    def center(self):
        """Center of rect calculated from position and dimensions."""
        return self.position.add(self.half())

    def set_center(self, center):
        """Set the position based on a new center point."""
        self.position = center.sub(self.half())

    def area(self):
        """Area: length * width."""
        return self.width * self.height


class PointList(object):
    """Methods for transforming a list of points."""
    def __init__(self, points=[]):
        self.points = points
        self._polygon = None

    def polygon(self):
        """Builds a polygon from the set of points."""
        if not self._polygon:
            self._polygon = Polygon.Polygon(self.points)

        return self._polygon

    def segments(self):
        """Returns a list of LineSegment objects."""
        segs = []
        for i, point in enumerate(self.points[1:]):
            index = i + 1

            segs.append(LineSegment(
                Vector2(self.points[index - 1][0], self.points[index - 1][1]),
                Vector2(self.points[index][0], self.points[index][1])
            ))

        segs.append(LineSegment(
            Vector2(self.points[-1][0], self.points[-1][1]),
            Vector2(self.points[0][0], self.points[0][1]),
        ))

        return segs


class LineSegment(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def length(self):
        """Length of segment vector."""
        return self.end.sub(self.start).magnitude()

    def closest_point_to_point(self, point):
        """Point along segment that is closest to given point."""
        segment_vector = self.end.sub(self.start)
        point_vector = point.sub(self.start)

        seg_mag = segment_vector.magnitude()

        # project point_vector on segment_vector
        projection = segment_vector.dot_product(point_vector)

        # scalar value used to interpolate new point along segment_vector
        scalar = projection / seg_mag ** 2

        # clamp on [0,1]
        scalar = 1.0 if scalar > 1.0 else scalar
        scalar = 0.0 if scalar < 0.0 else scalar

        # interpolate scalar along segment and add start point back in
        return self.start.add(segment_vector.unit().scale(scalar * seg_mag))

    def closest_distance_to_point(self, point):
        """Helper method too automatically return distance."""
        closest_point = self.closest_point_to_point(point)
        return closest_point.distance(point)


class Packer(object):
    def __init__(self):
        self._rects = []

    def add_rect(self, width, height, data={}):
        self._rects.append(Rect(width, height, data))

    def pack(self, padding=0, center=Vector2()):
        # init everything
        placed_rects = []
        sorted_rects = sorted(self._rects, key=lambda rect: -rect.area())
        # double padding due to halfing later on
        padding *= 2

        for rect in sorted_rects:

            if not placed_rects:
                # first rect, right on target.
                rect.set_center(center)

            else:
                # Expand each rectangle based on new rect size and padding
                # get a list of points
                # build a polygon
                point_lists = [
                    pr.expand(rect.width + padding, rect.height + padding).point_list().polygon()
                    for pr in placed_rects
                ]

                # take the union of all the polygons (relies on + operator override)
                # the [0] at the end returns the first "contour", which is the only one we need
                bounding_points = PointList(sum(
                    point_lists[1:],
                    point_lists[0]
                )[0])

                # find the closest segment
                closest_segments = sorted(
                    bounding_points.segments(),
                    key=lambda segment: segment.closest_distance_to_point(center)
                )

                # get the closest point
                place_point = closest_segments[0].closest_point_to_point(center)

                # set the rect position
                rect.set_center(place_point)

            placed_rects.append(rect)

        return placed_rects

########NEW FILE########
__FILENAME__ = osx
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.
#
# Imported from http://www.benden.us/journal/2014/OS-X-Power-Management-No-Sleep-Howto/
# Copyright (c) Joseph Benden 2014

import ctypes
import CoreFoundation
import objc

def SetUpIOFramework():
    # load the IOKit library
    framework = ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/IOKit.framework/IOKit')

    # declare parameters as described in IOPMLib.h
    framework.IOPMAssertionCreateWithName.argtypes = [
        ctypes.c_void_p,  # CFStringRef
        ctypes.c_uint32,  # IOPMAssertionLevel
        ctypes.c_void_p,  # CFStringRef
        ctypes.POINTER(ctypes.c_uint32)]  # IOPMAssertionID
    framework.IOPMAssertionRelease.argtypes = [
        ctypes.c_uint32]  # IOPMAssertionID
    return framework

def StringToCFString(string):
    # we'll need to convert our strings before use
    encoding = CoreFoundation.kCFStringEncodingASCII
    cfstring = CoreFoundation.CFStringCreateWithCString(None, string, encoding)
    return objc.pyobjc_id(cfstring.nsstring())

def AssertionCreateWithName(framework, a_type,
                            a_level, a_reason):
    # this method will create an assertion using the IOKit library
    # several parameters
    a_id = ctypes.c_uint32(0)
    a_type = StringToCFString(a_type)
    a_reason = StringToCFString(a_reason)
    a_error = framework.IOPMAssertionCreateWithName(
        a_type, a_level, a_reason, ctypes.byref(a_id))

    # we get back a 0 or stderr, along with a unique c_uint
    # representing the assertion ID so we can release it later
    return a_error, a_id

def AssertionRelease(framework, assertion_id):
    # releasing the assertion is easy, and also returns a 0 on
    # success, or stderr otherwise
    return framework.IOPMAssertionRelease(assertion_id)

def inhibit_sleep_osx(reason):
    no_idle = "NoIdleSleepAssertion"

    # Initialize IOKit framework
    if inhibit_sleep_osx.framework is None:
        inhibit_sleep_osx.framework = SetUpIOFramework()
    framework = inhibit_sleep_osx.framework

    # Start inhibition
    ret, a_id = AssertionCreateWithName(framework, no_idle, 255, reason)
    inhibit_sleep_osx.assertion_id = a_id
    return ret
inhibit_sleep_osx.framework = None

def deinhibit_sleep_osx():
    return AssertionRelease(inhibit_sleep_osx.framework,
                            inhibit_sleep_osx.assertion_id)

########NEW FILE########
__FILENAME__ = printcore
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "2014.04.06"

from serial import Serial, SerialException
from select import error as SelectError
from threading import Thread, Lock
from Queue import Queue, Empty as QueueEmpty
import time
import platform
import os
import sys
reload(sys).setdefaultencoding('utf8')
import logging
import traceback
import errno
import socket
import re
from functools import wraps
from collections import deque
from printrun import gcoder
from .utils import install_locale, decode_utf8, setup_logging
install_locale('pronterface')

setup_logging(sys.stderr)

def locked(f):
    @wraps(f)
    def inner(*args, **kw):
        with inner.lock:
            return f(*args, **kw)
    inner.lock = Lock()
    return inner

def control_ttyhup(port, disable_hup):
    """Controls the HUPCL"""
    if platform.system() == "Linux":
        if disable_hup:
            os.system("stty -F %s -hup" % port)
        else:
            os.system("stty -F %s hup" % port)

def enable_hup(port):
    control_ttyhup(port, False)

def disable_hup(port):
    control_ttyhup(port, True)

class printcore():
    def __init__(self, port = None, baud = None):
        """Initializes a printcore instance. Pass the port and baud rate to
           connect immediately"""
        self.baud = None
        self.port = None
        self.analyzer = gcoder.GCode()
        # Serial instance connected to the printer, should be None when
        # disconnected
        self.printer = None
        # clear to send, enabled after responses
        # FIXME: should probably be changed to a sliding window approach
        self.clear = 0
        # The printer has responded to the initial command and is active
        self.online = False
        # is a print currently running, true if printing, false if paused
        self.printing = False
        self.mainqueue = None
        self.priqueue = Queue(0)
        self.queueindex = 0
        self.lineno = 0
        self.resendfrom = -1
        self.paused = False
        self.sentlines = {}
        self.log = deque(maxlen = 10000)
        self.sent = []
        self.writefailures = 0
        self.tempcb = None  # impl (wholeline)
        self.recvcb = None  # impl (wholeline)
        self.sendcb = None  # impl (wholeline)
        self.preprintsendcb = None  # impl (wholeline)
        self.printsendcb = None  # impl (wholeline)
        self.layerchangecb = None  # impl (wholeline)
        self.errorcb = None  # impl (wholeline)
        self.startcb = None  # impl ()
        self.endcb = None  # impl ()
        self.onlinecb = None  # impl ()
        self.loud = False  # emit sent and received lines to terminal
        self.tcp_streaming_mode = False
        self.greetings = ['start', 'Grbl ']
        self.wait = 0  # default wait period for send(), send_now()
        self.read_thread = None
        self.stop_read_thread = False
        self.send_thread = None
        self.stop_send_thread = False
        self.print_thread = None
        if port is not None and baud is not None:
            self.connect(port, baud)
        self.xy_feedrate = None
        self.z_feedrate = None

    def logError(self, error):
        if self.errorcb:
            try: self.errorcb(error)
            except: traceback.print_exc()
        else:
            logging.error(error)

    @locked
    def disconnect(self):
        """Disconnects from printer and pauses the print
        """
        if self.printer:
            if self.read_thread:
                self.stop_read_thread = True
                self.read_thread.join()
                self.read_thread = None
            if self.print_thread:
                self.printing = False
                self.print_thread.join()
            self._stop_sender()
            try:
                self.printer.close()
            except socket.error:
                pass
            except OSError:
                pass
        self.printer = None
        self.online = False
        self.printing = False

    @locked
    def connect(self, port = None, baud = None):
        """Set port and baudrate if given, then connect to printer
        """
        if self.printer:
            self.disconnect()
        if port is not None:
            self.port = port
        if baud is not None:
            self.baud = baud
        if self.port is not None and self.baud is not None:
            # Connect to socket if "port" is an IP, device if not
            host_regexp = re.compile("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$|^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")
            is_serial = True
            if ":" in port:
                bits = port.split(":")
                if len(bits) == 2:
                    hostname = bits[0]
                    try:
                        port = int(bits[1])
                        if host_regexp.match(hostname) and 1 <= port <= 65535:
                            is_serial = False
                    except:
                        pass
            self.writefailures = 0
            if not is_serial:
                self.printer_tcp = socket.socket(socket.AF_INET,
                                                 socket.SOCK_STREAM)
                self.timeout = 0.25
                self.printer_tcp.settimeout(1.0)
                try:
                    self.printer_tcp.connect((hostname, port))
                    self.printer_tcp.settimeout(self.timeout)
                    self.printer = self.printer_tcp.makefile()
                except socket.error as e:
                    self.logError(_("Could not connect to %s:%s:") % (hostname, port) +
                                  "\n" + _("Socket error %s:") % e.errno +
                                  "\n" + e.strerror)
                    self.printer = None
                    self.printer_tcp = None
                    return
            else:
                disable_hup(self.port)
                self.printer_tcp = None
                try:
                    self.printer = Serial(port = self.port,
                                          baudrate = self.baud,
                                          timeout = 0.25)
                except SerialException as e:
                    self.logError(_("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                                  "\n" + _("Serial error: %s") % e)
                    self.printer = None
                    return
                except IOError as e:
                    self.logError(_("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                                  "\n" + _("IO error: %s") % e)
                    self.printer = None
                    return
            self.stop_read_thread = False
            self.read_thread = Thread(target = self._listen)
            self.read_thread.start()
            self._start_sender()

    def reset(self):
        """Reset the printer
        """
        if self.printer and not self.printer_tcp:
            self.printer.setDTR(1)
            time.sleep(0.2)
            self.printer.setDTR(0)

    def _readline(self):
        try:
            try:
                line = self.printer.readline()
                if self.printer_tcp and not line:
                    raise OSError(-1, "Read EOF from socket")
            except socket.timeout:
                return ""

            if len(line) > 1:
                self.log.append(line)
                if self.recvcb:
                    try: self.recvcb(line)
                    except: traceback.print_exc()
                if self.loud: logging.info("RECV: %s" % line.rstrip())
            return line
        except SelectError as e:
            if 'Bad file descriptor' in e.args[1]:
                self.logError(_(u"Can't read from printer (disconnected?) (SelectError {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                return None
            else:
                self.logError(_(u"SelectError ({0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                raise
        except SerialException as e:
            self.logError(_(u"Can't read from printer (disconnected?) (SerialException): {0}").format(decode_utf8(str(e))))
            return None
        except socket.error as e:
            self.logError(_(u"Can't read from printer (disconnected?) (Socket error {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
            return None
        except OSError as e:
            if e.errno == errno.EAGAIN:  # Not a real error, no data was available
                return ""
            self.logError(_(u"Can't read from printer (disconnected?) (OS Error {0}): {1}").format(e.errno, e.strerror))
            return None

    def _listen_can_continue(self):
        if self.printer_tcp:
            return not self.stop_read_thread and self.printer
        return (not self.stop_read_thread
                and self.printer
                and self.printer.isOpen())

    def _listen_until_online(self):
        while not self.online and self._listen_can_continue():
            self._send("M105")
            if self.writefailures >= 4:
                print _("Aborting connection attempt after 4 failed writes.")
                return
            empty_lines = 0
            while self._listen_can_continue():
                line = self._readline()
                if line is None: break  # connection problem
                # workaround cases where M105 was sent before printer Serial
                # was online an empty line means read timeout was reached,
                # meaning no data was received thus we count those empty lines,
                # and once we have seen 15 in a row, we just break and send a
                # new M105
                # 15 was chosen based on the fact that it gives enough time for
                # Gen7 bootloader to time out, and that the non received M105
                # issues should be quite rare so we can wait for a long time
                # before resending
                if not line:
                    empty_lines += 1
                    if empty_lines == 15: break
                else: empty_lines = 0
                if line.startswith(tuple(self.greetings)) \
                   or line.startswith('ok') or "T:" in line:
                    self.online = True
                    if self.onlinecb:
                        try: self.onlinecb()
                        except: traceback.print_exc()
                    return

    def _listen(self):
        """This function acts on messages from the firmware
        """
        self.clear = True
        if not self.printing:
            self._listen_until_online()
        while self._listen_can_continue():
            line = self._readline()
            if line is None:
                break
            if line.startswith('DEBUG_'):
                continue
            if line.startswith(tuple(self.greetings)) or line.startswith('ok'):
                self.clear = True
            if line.startswith('ok') and "T:" in line and self.tempcb:
                # callback for temp, status, whatever
                try: self.tempcb(line)
                except: traceback.print_exc()
            elif line.startswith('Error'):
                self.logError(line)
            # Teststrings for resend parsing       # Firmware     exp. result
            # line="rs N2 Expected checksum 67"    # Teacup       2
            if line.lower().startswith("resend") or line.startswith("rs"):
                for haystack in ["N:", "N", ":"]:
                    line = line.replace(haystack, " ")
                linewords = line.split()
                while len(linewords) != 0:
                    try:
                        toresend = int(linewords.pop(0))
                        self.resendfrom = toresend
                        break
                    except:
                        pass
                self.clear = True
        self.clear = True

    def _start_sender(self):
        self.stop_send_thread = False
        self.send_thread = Thread(target = self._sender)
        self.send_thread.start()

    def _stop_sender(self):
        if self.send_thread:
            self.stop_send_thread = True
            self.send_thread.join()
            self.send_thread = None

    def _sender(self):
        while not self.stop_send_thread:
            try:
                command = self.priqueue.get(True, 0.1)
            except QueueEmpty:
                continue
            while self.printer and self.printing and not self.clear:
                time.sleep(0.001)
            self._send(command)
            while self.printer and self.printing and not self.clear:
                time.sleep(0.001)

    def _checksum(self, command):
        return reduce(lambda x, y: x ^ y, map(ord, command))

    def startprint(self, gcode, startindex = 0):
        """Start a print, gcode is an array of gcode commands.
        returns True on success, False if already printing.
        The print queue will be replaced with the contents of the data array,
        the next line will be set to 0 and the firmware notified. Printing
        will then start in a parallel thread.
        """
        if self.printing or not self.online or not self.printer:
            return False
        self.queueindex = startindex
        self.mainqueue = gcode
        self.printing = True
        self.lineno = 0
        self.resendfrom = -1
        self._send("M110", -1, True)
        if not gcode or not gcode.lines:
            return True
        self.clear = False
        resuming = (startindex != 0)
        self.print_thread = Thread(target = self._print,
                                   kwargs = {"resuming": resuming})
        self.print_thread.start()
        return True

    def cancelprint(self):
        self.pause()
        self.paused = False
        self.mainqueue = None
        self.clear = True

    # run a simple script if it exists, no multithreading
    def runSmallScript(self, filename):
        if filename is None: return
        f = None
        try:
            with open(filename) as f:
                for i in f:
                    l = i.replace("\n", "")
                    l = l[:l.find(";")]  # remove comments
                    self.send_now(l)
        except:
            pass

    def pause(self):
        """Pauses the print, saving the current position.
        """
        if not self.printing: return False
        self.paused = True
        self.printing = False

        # try joining the print thread: enclose it in try/except because we
        # might be calling it from the thread itself
        try:
            self.print_thread.join()
        except RuntimeError, e:
            if e.message == "cannot join current thread":
                pass
            else:
                traceback.print_exc()
        except:
            traceback.print_exc()

        self.print_thread = None

        # saves the status
        self.pauseX = self.analyzer.abs_x
        self.pauseY = self.analyzer.abs_y
        self.pauseZ = self.analyzer.abs_z
        self.pauseE = self.analyzer.abs_e
        self.pauseF = self.analyzer.current_f
        self.pauseRelative = self.analyzer.relative

    def resume(self):
        """Resumes a paused print.
        """
        if not self.paused: return False
        if self.paused:
            # restores the status
            self.send_now("G90")  # go to absolute coordinates

            xyFeedString = ""
            zFeedString = ""
            if self.xy_feedrate is not None:
                xyFeedString = " F" + str(self.xy_feedrate)
            if self.z_feedrate is not None:
                zFeedString = " F" + str(self.z_feedrate)

            self.send_now("G1 X%s Y%s%s" % (self.pauseX, self.pauseY,
                                            xyFeedString))
            self.send_now("G1 Z" + str(self.pauseZ) + zFeedString)
            self.send_now("G92 E" + str(self.pauseE))

            # go back to relative if needed
            if self.pauseRelative: self.send_now("G91")
            # reset old feed rate
            self.send_now("G1 F" + str(self.pauseF))

        self.paused = False
        self.printing = True
        self.print_thread = Thread(target = self._print,
                                   kwargs = {"resuming": True})
        self.print_thread.start()

    def send(self, command, wait = 0):
        """Adds a command to the checksummed main command queue if printing, or
        sends the command immediately if not printing"""

        if self.online:
            if self.printing:
                self.mainqueue.append(command)
            else:
                self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def send_now(self, command, wait = 0):
        """Sends a command to the printer ahead of the command queue, without a
        checksum"""
        if self.online:
            self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def _print(self, resuming = False):
        self._stop_sender()
        try:
            if self.startcb:
                # callback for printing started
                try: self.startcb(resuming)
                except:
                    self.logError(_("Print start callback failed with:") +
                                  "\n" + traceback.format_exc())
            while self.printing and self.printer and self.online:
                self._sendnext()
            self.sentlines = {}
            self.log.clear()
            self.sent = []
            if self.endcb:
                # callback for printing done
                try: self.endcb()
                except:
                    self.logError(_("Print end callback failed with:") +
                                  "\n" + traceback.format_exc())
        except:
            self.logError(_("Print thread died due to the following error:") +
                          "\n" + traceback.format_exc())
        finally:
            self.print_thread = None
            self._start_sender()

    def process_host_command(self, command):
        """only ;@pause command is implemented as a host command in printcore, but hosts are free to reimplement this method"""
        command = command.lstrip()
        if command.startswith(";@pause"):
            self.pause()

    def _sendnext(self):
        if not self.printer:
            return
        while self.printer and self.printing and not self.clear:
            time.sleep(0.001)
        # Only wait for oks when using serial connections or when not using tcp
        # in streaming mode
        if not self.printer_tcp or not self.tcp_streaming_mode:
            self.clear = False
        if not (self.printing and self.printer and self.online):
            self.clear = True
            return
        if self.resendfrom < self.lineno and self.resendfrom > -1:
            self._send(self.sentlines[self.resendfrom], self.resendfrom, False)
            self.resendfrom += 1
            return
        self.resendfrom = -1
        if not self.priqueue.empty():
            self._send(self.priqueue.get_nowait())
            self.priqueue.task_done()
            return
        if self.printing and self.queueindex < len(self.mainqueue):
            (layer, line) = self.mainqueue.idxs(self.queueindex)
            gline = self.mainqueue.all_layers[layer][line]
            if self.layerchangecb and self.queueindex > 0:
                (prev_layer, prev_line) = self.mainqueue.idxs(self.queueindex - 1)
                if prev_layer != layer:
                    try: self.layerchangecb(layer)
                    except: traceback.print_exc()
            if self.preprintsendcb:
                if self.queueindex + 1 < len(self.mainqueue):
                    (next_layer, next_line) = self.mainqueue.idxs(self.queueindex + 1)
                    next_gline = self.mainqueue.all_layers[next_layer][next_line]
                else:
                    next_gline = None
                gline = self.preprintsendcb(gline, next_gline)
            if gline is None:
                self.queueindex += 1
                self.clear = True
                return
            tline = gline.raw
            if tline.lstrip().startswith(";@"):  # check for host command
                self.process_host_command(tline)
                self.queueindex += 1
                self.clear = True
                return

            # Strip comments
            tline = gcoder.gcode_strip_comment_exp.sub("", tline).strip()
            if tline:
                self._send(tline, self.lineno, True)
                self.lineno += 1
                if self.printsendcb:
                    try: self.printsendcb(gline)
                    except: traceback.print_exc()
            else:
                self.clear = True
            self.queueindex += 1
        else:
            self.printing = False
            self.clear = True
            if not self.paused:
                self.queueindex = 0
                self.lineno = 0
                self._send("M110", -1, True)

    def _send(self, command, lineno = 0, calcchecksum = False):
        # Only add checksums if over serial (tcp does the flow control itself)
        if calcchecksum and not self.printer_tcp:
            prefix = "N" + str(lineno) + " " + command
            command = prefix + "*" + str(self._checksum(prefix))
            if "M110" not in command:
                self.sentlines[lineno] = command
        if self.printer:
            self.sent.append(command)
            # run the command through the analyzer
            gline = None
            try:
                gline = self.analyzer.append(command, store = False)
            except:
                logging.warning(_("Could not analyze command %s:") % command +
                                "\n" + traceback.format_exc())
            if self.loud:
                logging.info("SENT: %s" % command)
            if self.sendcb:
                try: self.sendcb(command, gline)
                except: traceback.print_exc()
            try:
                self.printer.write(str(command + "\n"))
                if self.printer_tcp:
                    try:
                        self.printer.flush()
                    except socket.timeout:
                        pass
                self.writefailures = 0
            except socket.error as e:
                if e.errno is None:
                    self.logError(_(u"Can't write to printer (disconnected ?):") +
                                  "\n" + traceback.format_exc())
                else:
                    self.logError(_(u"Can't write to printer (disconnected?) (Socket error {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                self.writefailures += 1
            except SerialException as e:
                self.logError(_(u"Can't write to printer (disconnected?) (SerialException): {0}").format(decode_utf8(str(e))))
                self.writefailures += 1
            except RuntimeError as e:
                self.logError(_(u"Socket connection broken, disconnected. ({0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                self.writefailures += 1

########NEW FILE########
__FILENAME__ = projectlayer
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import xml.etree.ElementTree
import wx
import wx.lib.agw.floatspin as floatspin
import os
import time
import zipfile
import tempfile
import shutil
from cairosvg.surface import PNGSurface
import cStringIO
import imghdr
import copy
import re
from collections import OrderedDict
import itertools
import math

class DisplayFrame(wx.Frame):
    def __init__(self, parent, title, res = (1024, 768), printer = None, scale = 1.0, offset = (0, 0)):
        wx.Frame.__init__(self, parent = parent, title = title, size = res)
        self.printer = printer
        self.control_frame = parent
        self.pic = wx.StaticBitmap(self)
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        self.slicer = 'bitmap'
        self.dpi = 96
        dc = wx.MemoryDC()
        dc.SelectObject(self.bbitmap)
        dc.SetBackground(wx.Brush("black"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

        self.SetBackgroundColour("black")
        self.pic.Hide()
        self.SetDoubleBuffered(True)
        self.SetPosition((self.control_frame.GetSize().x, 0))
        self.Show()

        self.scale = scale
        self.index = 0
        self.size = res
        self.offset = offset
        self.running = False
        self.layer_red = False

    def clear_layer(self):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()
        except:
            raise
            pass

    def resize(self, res = (1024, 768)):
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        dc = wx.MemoryDC()
        dc.SelectObject(self.bbitmap)
        dc.SetBackground(wx.Brush("black"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

    def draw_layer(self, image):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()

            if self.slicer == 'Slic3r' or self.slicer == 'Skeinforge':

                if self.scale != 1.0:
                    layercopy = copy.deepcopy(image)
                    height = float(layercopy.get('height').replace('m', ''))
                    width = float(layercopy.get('width').replace('m', ''))

                    layercopy.set('height', str(height * self.scale) + 'mm')
                    layercopy.set('width', str(width * self.scale) + 'mm')
                    layercopy.set('viewBox', '0 0 ' + str(width * self.scale) + ' ' + str(height * self.scale))

                    g = layercopy.find("{http://www.w3.org/2000/svg}g")
                    g.set('transform', 'scale(' + str(self.scale) + ')')
                    stream = cStringIO.StringIO(PNGSurface.convert(dpi = self.dpi, bytestring = xml.etree.ElementTree.tostring(layercopy)))
                else:
                    stream = cStringIO.StringIO(PNGSurface.convert(dpi = self.dpi, bytestring = xml.etree.ElementTree.tostring(image)))

                pngImage = wx.ImageFromStream(stream)

                # print "w:", pngImage.Width, ", dpi:", self.dpi, ", w (mm): ",(pngImage.Width / self.dpi) * 25.4

                if self.layer_red:
                    pngImage = pngImage.AdjustChannels(1, 0, 0, 1)

                dc.DrawBitmap(wx.BitmapFromImage(pngImage), self.offset[0], self.offset[1], True)

            elif self.slicer == 'bitmap':
                if isinstance(image, str):
                    image = wx.Image(image)
                if self.layer_red:
                    image = image.AdjustChannels(1, 0, 0, 1)
                dc.DrawBitmap(wx.BitmapFromImage(image.Scale(image.Width * self.scale, image.Height * self.scale)), self.offset[0], -self.offset[1], True)
            else:
                raise Exception(self.slicer + " is an unknown method.")

            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()

        except:
            raise
            pass

    def show_img_delay(self, image):
        print "Showing", str(time.clock())
        self.control_frame.set_current_layer(self.index)
        self.draw_layer(image)
        wx.FutureCall(1000 * self.interval, self.hide_pic_and_rise)

    def rise(self):
        if (self.direction == "Top Down"):
            print "Lowering", str(time.clock())
        else:
            print "Rising", str(time.clock())

        if self.printer is not None and self.printer.online:
            self.printer.send_now("G91")

            if (self.prelift_gcode):
                for line in self.prelift_gcode.split('\n'):
                    if line:
                        self.printer.send_now(line)

            if (self.direction == "Top Down"):
                self.printer.send_now("G1 Z-%f F%g" % (self.overshoot, self.z_axis_rate,))
                self.printer.send_now("G1 Z%f F%g" % (self.overshoot - self.thickness, self.z_axis_rate,))
            else:  # self.direction == "Bottom Up"
                self.printer.send_now("G1 Z%f F%g" % (self.overshoot, self.z_axis_rate,))
                self.printer.send_now("G1 Z-%f F%g" % (self.overshoot - self.thickness, self.z_axis_rate,))

            if (self.postlift_gcode):
                for line in self.postlift_gcode.split('\n'):
                    if line:
                        self.printer.send_now(line)

            self.printer.send_now("G90")
        else:
            time.sleep(self.pause)

        wx.FutureCall(1000 * self.pause, self.next_img)

    def hide_pic(self):
        print "Hiding", str(time.clock())
        self.pic.Hide()

    def hide_pic_and_rise(self):
        wx.CallAfter(self.hide_pic)
        wx.FutureCall(500, self.rise)

    def next_img(self):
        if not self.running:
            return
        if self.index < len(self.layers):
            print self.index
            wx.CallAfter(self.show_img_delay, self.layers[self.index])
            self.index += 1
        else:
            print "end"
            wx.CallAfter(self.pic.Hide)
            wx.CallAfter(self.Refresh)

    def present(self,
                layers,
                interval = 0.5,
                pause = 0.2,
                overshoot = 0.0,
                z_axis_rate = 200,
                prelift_gcode = "",
                postlift_gcode = "",
                direction = "Top Down",
                thickness = 0.4,
                scale = 1,
                size = (1024, 768),
                offset = (0, 0),
                layer_red = False):
        wx.CallAfter(self.pic.Hide)
        wx.CallAfter(self.Refresh)
        self.layers = layers
        self.scale = scale
        self.thickness = thickness
        self.size = size
        self.interval = interval
        self.pause = pause
        self.overshoot = overshoot
        self.z_axis_rate = z_axis_rate
        self.prelift_gcode = prelift_gcode
        self.postlift_gcode = postlift_gcode
        self.direction = direction
        self.layer_red = layer_red
        self.offset = offset
        self.index = 0
        self.running = True

        self.next_img()

class SettingsFrame(wx.Frame):

    def _set_setting(self, name, value):
        if self.pronterface:
            self.pronterface.set(name, value)

    def _get_setting(self, name, val):
        if self.pronterface:
            try:
                return getattr(self.pronterface.settings, name)
            except AttributeError:
                return val
        else:
            return val

    def __init__(self, parent, printer = None):
        wx.Frame.__init__(self, parent, title = "ProjectLayer Control", style = (wx.DEFAULT_FRAME_STYLE | wx.WS_EX_CONTEXTHELP))
        self.SetExtraStyle(wx.FRAME_EX_CONTEXTHELP)
        self.pronterface = parent
        self.display_frame = DisplayFrame(self, title = "ProjectLayer Display", printer = printer)

        self.panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        buttonbox = wx.StaticBoxSizer(wx.StaticBox(self.panel, label = "Controls"), wx.HORIZONTAL)

        load_button = wx.Button(self.panel, -1, "Load")
        load_button.Bind(wx.EVT_BUTTON, self.load_file)
        load_button.SetHelpText("Choose an SVG file created from Slic3r or Skeinforge, or a zip file of bitmap images (with extension: .3dlp.zip).")
        buttonbox.Add(load_button, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 5)

        present_button = wx.Button(self.panel, -1, "Present")
        present_button.Bind(wx.EVT_BUTTON, self.start_present)
        present_button.SetHelpText("Starts the presentation of the slices.")
        buttonbox.Add(present_button, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 5)

        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.pause_button.Bind(wx.EVT_BUTTON, self.pause_present)
        self.pause_button.SetHelpText("Pauses the presentation. Can be resumed afterwards by clicking this button, or restarted by clicking present again.")
        buttonbox.Add(self.pause_button, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 5)

        stop_button = wx.Button(self.panel, -1, "Stop")
        stop_button.Bind(wx.EVT_BUTTON, self.stop_present)
        stop_button.SetHelpText("Stops presenting the slices.")
        buttonbox.Add(stop_button, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 5)

        self.help_button = wx.ContextHelpButton(self.panel)
        buttonbox.Add(self.help_button, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 5)

        fieldboxsizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, label = "Settings"), wx.VERTICAL)
        fieldsizer = wx.GridBagSizer(10, 10)

        # Left Column

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Layer (mm):"), pos = (0, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.thickness = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_layer", "0.1")), size = (80, -1))
        self.thickness.Bind(wx.EVT_TEXT, self.update_thickness)
        self.thickness.SetHelpText("The thickness of each slice. Should match the value used to slice the model.  SVG files update this value automatically, 3dlp.zip files have to be manually entered.")
        fieldsizer.Add(self.thickness, pos = (0, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Exposure (s):"), pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.interval = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_interval", "0.5")), size = (80, -1))
        self.interval.Bind(wx.EVT_TEXT, self.update_interval)
        self.interval.SetHelpText("How long each slice should be displayed.")
        fieldsizer.Add(self.interval, pos = (1, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Blank (s):"), pos = (2, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.pause = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_pause", "0.5")), size = (80, -1))
        self.pause.Bind(wx.EVT_TEXT, self.update_pause)
        self.pause.SetHelpText("The pause length between slices. This should take into account any movement of the Z axis, plus time to prepare the resin surface (sliding, tilting, sweeping, etc).")
        fieldsizer.Add(self.pause, pos = (2, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Scale:"), pos = (3, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.scale = floatspin.FloatSpin(self.panel, -1, value = self._get_setting('project_scale', 1.0), increment = 0.1, digits = 3, size = (80, -1))
        self.scale.Bind(floatspin.EVT_FLOATSPIN, self.update_scale)
        self.scale.SetHelpText("The additional scaling of each slice.")
        fieldsizer.Add(self.scale, pos = (3, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Direction:"), pos = (4, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.direction = wx.ComboBox(self.panel, -1, choices = ["Top Down", "Bottom Up"], value = self._get_setting('project_direction', "Top Down"), size = (80, -1))
        self.direction.Bind(wx.EVT_COMBOBOX, self.update_direction)
        self.direction.SetHelpText("The direction the Z axis should move. Top Down is where the projector is above the model, Bottom up is where the projector is below the model.")
        fieldsizer.Add(self.direction, pos = (4, 1), flag = wx.ALIGN_CENTER_VERTICAL)

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Overshoot (mm):"), pos = (5, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.overshoot = floatspin.FloatSpin(self.panel, -1, value = self._get_setting('project_overshoot', 3.0), increment = 0.1, digits = 1, min_val = 0, size = (80, -1))
        self.overshoot.Bind(floatspin.EVT_FLOATSPIN, self.update_overshoot)
        self.overshoot.SetHelpText("How far the axis should move beyond the next slice position for each slice. For Top Down printers this would dunk the model under the resi and then return. For Bottom Up printers this would raise the base away from the vat and then return.")
        fieldsizer.Add(self.overshoot, pos = (5, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Pre-lift Gcode:"), pos = (6, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.prelift_gcode = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_prelift_gcode", "").replace("\\n", '\n')), size = (-1, 35), style = wx.TE_MULTILINE)
        self.prelift_gcode.SetHelpText("Additional gcode to run before raising the Z axis. Be sure to take into account any additional time needed in the pause value, and be careful what gcode is added!")
        self.prelift_gcode.Bind(wx.EVT_TEXT, self.update_prelift_gcode)
        fieldsizer.Add(self.prelift_gcode, pos = (6, 1), span = (2, 1))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Post-lift Gcode:"), pos = (6, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.postlift_gcode = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_postlift_gcode", "").replace("\\n", '\n')), size = (-1, 35), style = wx.TE_MULTILINE)
        self.postlift_gcode.SetHelpText("Additional gcode to run after raising the Z axis. Be sure to take into account any additional time needed in the pause value, and be careful what gcode is added!")
        self.postlift_gcode.Bind(wx.EVT_TEXT, self.update_postlift_gcode)
        fieldsizer.Add(self.postlift_gcode, pos = (6, 3), span = (2, 1))

        # Right Column

        fieldsizer.Add(wx.StaticText(self.panel, -1, "X (px):"), pos = (0, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        projectX = int(math.floor(float(self._get_setting("project_x", 1920))))
        self.X = wx.SpinCtrl(self.panel, -1, str(projectX), max = 999999, size = (80, -1))
        self.X.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        self.X.SetHelpText("The projector resolution in the X axis.")
        fieldsizer.Add(self.X, pos = (0, 3))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Y (px):"), pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        projectY = int(math.floor(float(self._get_setting("project_y", 1200))))
        self.Y = wx.SpinCtrl(self.panel, -1, str(projectY), max = 999999, size = (80, -1))
        self.Y.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        self.Y.SetHelpText("The projector resolution in the Y axis.")
        fieldsizer.Add(self.Y, pos = (1, 3))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "OffsetX (mm):"), pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.offset_X = floatspin.FloatSpin(self.panel, -1, value = self._get_setting("project_offset_x", 0.0), increment = 1, digits = 1, size = (80, -1))
        self.offset_X.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)
        self.offset_X.SetHelpText("How far the slice should be offset from the edge in the X axis.")
        fieldsizer.Add(self.offset_X, pos = (2, 3))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "OffsetY (mm):"), pos = (3, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.offset_Y = floatspin.FloatSpin(self.panel, -1, value = self._get_setting("project_offset_y", 0.0), increment = 1, digits = 1, size = (80, -1))
        self.offset_Y.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)
        self.offset_Y.SetHelpText("How far the slice should be offset from the edge in the Y axis.")
        fieldsizer.Add(self.offset_Y, pos = (3, 3))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "ProjectedX (mm):"), pos = (4, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.projected_X_mm = floatspin.FloatSpin(self.panel, -1, value = self._get_setting("project_projected_x", 505.0), increment = 1, digits = 1, size = (80, -1))
        self.projected_X_mm.Bind(floatspin.EVT_FLOATSPIN, self.update_projected_Xmm)
        self.projected_X_mm.SetHelpText("The actual width of the entire projected image. Use the Calibrate grid to show the full size of the projected image, and measure the width at the same level where the slice will be projected onto the resin.")
        fieldsizer.Add(self.projected_X_mm, pos = (4, 3))

        fieldsizer.Add(wx.StaticText(self.panel, -1, "Z Axis Speed (mm/min):"), pos = (5, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.z_axis_rate = wx.SpinCtrl(self.panel, -1, str(self._get_setting("project_z_axis_rate", 200)), max = 9999, size = (80, -1))
        self.z_axis_rate.Bind(wx.EVT_SPINCTRL, self.update_z_axis_rate)
        self.z_axis_rate.SetHelpText("Speed of the Z axis in mm/minute. Take into account that slower rates may require a longer pause value.")
        fieldsizer.Add(self.z_axis_rate, pos = (5, 3))

        fieldboxsizer.Add(fieldsizer)

        # Display

        displayboxsizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, label = "Display"), wx.VERTICAL)
        displaysizer = wx.GridBagSizer(10, 10)

        displaysizer.Add(wx.StaticText(self.panel, -1, "Fullscreen:"), pos = (0, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        self.fullscreen = wx.CheckBox(self.panel, -1)
        self.fullscreen.Bind(wx.EVT_CHECKBOX, self.update_fullscreen)
        self.fullscreen.SetHelpText("Toggles the project screen to full size.")
        displaysizer.Add(self.fullscreen, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL)

        displaysizer.Add(wx.StaticText(self.panel, -1, "Calibrate:"), pos = (0, 2), flag = wx.ALIGN_CENTER_VERTICAL)
        self.calibrate = wx.CheckBox(self.panel, -1)
        self.calibrate.Bind(wx.EVT_CHECKBOX, self.show_calibrate)
        self.calibrate.SetHelpText("Toggles the calibration grid. Each grid should be 10mmx10mm in size. Use the grid to ensure the projected size is correct. See also the help for the ProjectedX field.")
        displaysizer.Add(self.calibrate, pos = (0, 3), flag = wx.ALIGN_CENTER_VERTICAL)

        displaysizer.Add(wx.StaticText(self.panel, -1, "1st Layer:"), pos = (0, 4), flag = wx.ALIGN_CENTER_VERTICAL)

        first_layer_boxer = wx.BoxSizer(wx.HORIZONTAL)
        self.first_layer = wx.CheckBox(self.panel, -1)
        self.first_layer.Bind(wx.EVT_CHECKBOX, self.show_first_layer)
        self.first_layer.SetHelpText("Displays the first layer of the model. Use this to project the first layer for longer so it holds to the base. Note: this value does not affect the first layer when the \"Present\" run is started, it should be used manually.")

        first_layer_boxer.Add(self.first_layer, flag = wx.ALIGN_CENTER_VERTICAL)

        first_layer_boxer.Add(wx.StaticText(self.panel, -1, " (s):"), flag = wx.ALIGN_CENTER_VERTICAL)
        self.show_first_layer_timer = floatspin.FloatSpin(self.panel, -1, value=-1, increment = 1, digits = 1, size = (55, -1))
        self.show_first_layer_timer.SetHelpText("How long to display the first layer for. -1 = unlimited.")
        first_layer_boxer.Add(self.show_first_layer_timer, flag = wx.ALIGN_CENTER_VERTICAL)
        displaysizer.Add(first_layer_boxer, pos = (0, 6), flag = wx.ALIGN_CENTER_VERTICAL)

        displaysizer.Add(wx.StaticText(self.panel, -1, "Red:"), pos = (0, 7), flag = wx.ALIGN_CENTER_VERTICAL)
        self.layer_red = wx.CheckBox(self.panel, -1)
        self.layer_red.Bind(wx.EVT_CHECKBOX, self.show_layer_red)
        self.layer_red.SetHelpText("Toggles whether the image should be red. Useful for positioning whilst resin is in the printer as it should not cause a reaction.")
        displaysizer.Add(self.layer_red, pos = (0, 8), flag = wx.ALIGN_CENTER_VERTICAL)

        displayboxsizer.Add(displaysizer)

        # Info
        infosizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, label = "Info"), wx.VERTICAL)

        infofieldsizer = wx.GridBagSizer(10, 10)

        filelabel = wx.StaticText(self.panel, -1, "File:")
        filelabel.SetHelpText("The name of the model currently loaded.")
        infofieldsizer.Add(filelabel, pos = (0, 0))
        self.filename = wx.StaticText(self.panel, -1, "")

        infofieldsizer.Add(self.filename, pos = (0, 1))

        totallayerslabel = wx.StaticText(self.panel, -1, "Total Layers:")
        totallayerslabel.SetHelpText("The total number of layers found in the model.")
        infofieldsizer.Add(totallayerslabel, pos = (1, 0))
        self.total_layers = wx.StaticText(self.panel, -1)

        infofieldsizer.Add(self.total_layers, pos = (1, 1))

        currentlayerlabel = wx.StaticText(self.panel, -1, "Current Layer:")
        currentlayerlabel.SetHelpText("The current layer being displayed.")
        infofieldsizer.Add(currentlayerlabel, pos = (2, 0))
        self.current_layer = wx.StaticText(self.panel, -1, "0")
        infofieldsizer.Add(self.current_layer, pos = (2, 1))

        estimatedtimelabel = wx.StaticText(self.panel, -1, "Estimated Time:")
        estimatedtimelabel.SetHelpText("An estimate of the remaining time until print completion.")
        infofieldsizer.Add(estimatedtimelabel, pos = (3, 0))
        self.estimated_time = wx.StaticText(self.panel, -1, "")
        infofieldsizer.Add(self.estimated_time, pos = (3, 1))

        infosizer.Add(infofieldsizer)

        #

        vbox.Add(buttonbox, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, border = 10)
        vbox.Add(fieldboxsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 10)
        vbox.Add(displayboxsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 10)
        vbox.Add(infosizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = 10)

        self.panel.SetSizer(vbox)
        self.panel.Fit()
        self.Fit()
        self.SetPosition((0, 0))
        self.Show()

    def __del__(self):
        if hasattr(self, 'image_dir') and self.image_dir != '':
            shutil.rmtree(self.image_dir)
        if self.display_frame:
            self.display_frame.Destroy()

    def set_total_layers(self, total):
        self.total_layers.SetLabel(str(total))
        self.set_estimated_time()

    def set_current_layer(self, index):
        self.current_layer.SetLabel(str(index))
        self.set_estimated_time()

    def display_filename(self, name):
        self.filename.SetLabel(name)

    def set_estimated_time(self):
        if not hasattr(self, 'layers'):
            return

        current_layer = int(self.current_layer.GetLabel())
        remaining_layers = len(self.layers[0]) - current_layer
        # 0.5 for delay between hide and rise
        estimated_time = remaining_layers * (float(self.interval.GetValue()) + float(self.pause.GetValue()) + 0.5)
        self.estimated_time.SetLabel(time.strftime("%H:%M:%S", time.gmtime(estimated_time)))

    def parse_svg(self, name):
        et = xml.etree.ElementTree.ElementTree(file = name)
        # xml.etree.ElementTree.dump(et)

        slicer = 'Slic3r' if et.getroot().find('{http://www.w3.org/2000/svg}metadata') is None else 'Skeinforge'
        zlast = 0
        zdiff = 0
        ol = []
        if (slicer == 'Slic3r'):
            height = et.getroot().get('height').replace('m', '')
            width = et.getroot().get('width').replace('m', '')

            for i in et.findall("{http://www.w3.org/2000/svg}g"):
                z = float(i.get('{http://slic3r.org/namespaces/slic3r}z'))
                zdiff = z - zlast
                zlast = z

                svgSnippet = xml.etree.ElementTree.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')

                svgSnippet.set('viewBox', '0 0 ' + width + ' ' + height)
                svgSnippet.set('style', 'background-color:black;fill:white;')
                svgSnippet.append(i)

                ol += [svgSnippet]
        else:

            slice_layers = et.findall("{http://www.w3.org/2000/svg}metadata")[0].findall("{http://www.reprap.org/slice}layers")[0]
            minX = slice_layers.get('minX')
            maxX = slice_layers.get('maxX')
            minY = slice_layers.get('minY')
            maxY = slice_layers.get('maxY')

            height = str(abs(float(minY)) + abs(float(maxY)))
            width = str(abs(float(minX)) + abs(float(maxX)))

            for g in et.findall("{http://www.w3.org/2000/svg}g")[0].findall("{http://www.w3.org/2000/svg}g"):

                g.set('transform', '')

                text_element = g.findall("{http://www.w3.org/2000/svg}text")[0]
                g.remove(text_element)

                path_elements = g.findall("{http://www.w3.org/2000/svg}path")
                for p in path_elements:
                    p.set('transform', 'translate(' + maxX + ',' + maxY + ')')
                    p.set('fill', 'white')

                z = float(g.get('id').split("z:")[-1])
                zdiff = z - zlast
                zlast = z

                svgSnippet = xml.etree.ElementTree.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')

                svgSnippet.set('viewBox', '0 0 ' + width + ' ' + height)
                svgSnippet.set('style', 'background-color:black;fill:white;')
                svgSnippet.append(g)

                ol += [svgSnippet]
        return ol, zdiff, slicer

    def parse_3DLP_zip(self, name):
        if not zipfile.is_zipfile(name):
            raise Exception(name + " is not a zip file!")
        accepted_image_types = ['gif', 'tiff', 'jpg', 'jpeg', 'bmp', 'png']
        zipFile = zipfile.ZipFile(name, 'r')
        self.image_dir = tempfile.mkdtemp()
        zipFile.extractall(self.image_dir)
        ol = []

        # Note: the following funky code extracts any numbers from the filenames, matches
        # them with the original then sorts them. It allows for filenames of the
        # format: abc_1.png, which would be followed by abc_10.png alphabetically.
        os.chdir(self.image_dir)
        vals = filter(os.path.isfile, os.listdir('.'))
        keys = map(lambda p: int(re.search('\d+', p).group()), vals)
        imagefilesDict = dict(itertools.izip(keys, vals))
        imagefilesOrderedDict = OrderedDict(sorted(imagefilesDict.items(), key = lambda t: t[0]))

        for f in imagefilesOrderedDict.values():
            path = os.path.join(self.image_dir, f)
            if os.path.isfile(path) and imghdr.what(path) in accepted_image_types:
                ol.append(path)

        return ol, -1, "bitmap"

    def load_file(self, event):
        dlg = wx.FileDialog(self, ("Open file to print"), style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(("Slic3r or Skeinforge svg files (;*.svg;*.SVG;);3DLP Zip (;*.3dlp.zip;)"))
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(("File not found!"))
                return
            if name.endswith(".3dlp.zip"):
                layers = self.parse_3DLP_zip(name)
                layerHeight = float(self.thickness.GetValue())
            else:
                layers = self.parse_svg(name)
                layerHeight = layers[1]
                self.thickness.SetValue(str(layers[1]))
                print "Layer thickness detected:", layerHeight, "mm"
            print len(layers[0]), "layers found, total height", layerHeight * len(layers[0]), "mm"
            self.layers = layers
            self.set_total_layers(len(layers[0]))
            self.set_current_layer(0)
            self.current_filename = os.path.basename(name)
            self.display_filename(self.current_filename)
            self.slicer = layers[2]
            self.display_frame.slicer = self.slicer
        dlg.Destroy()

    def show_calibrate(self, event):
        if self.calibrate.IsChecked():
            self.present_calibrate(event)
        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2]
            self.display_frame.scale = float(self.scale.GetValue())
            self.display_frame.clear_layer()

    def show_first_layer(self, event):
        if self.first_layer.IsChecked():
            self.present_first_layer(event)
        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2]
            self.display_frame.scale = float(self.scale.GetValue())
            self.display_frame.clear_layer()

    def show_layer_red(self, event):
        self.display_frame.layer_red = self.layer_red.IsChecked()

    def present_calibrate(self, event):
        if self.calibrate.IsChecked():
            self.display_frame.Raise()
            self.display_frame.offset = (float(self.offset_X.GetValue()), -float(self.offset_Y.GetValue()))
            self.display_frame.scale = 1.0
            resolution_x_pixels = int(self.X.GetValue())
            resolution_y_pixels = int(self.Y.GetValue())

            gridBitmap = wx.EmptyBitmap(resolution_x_pixels, resolution_y_pixels)
            dc = wx.MemoryDC()
            dc.SelectObject(gridBitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()

            dc.SetPen(wx.Pen("red", 7))
            dc.DrawLine(0, 0, resolution_x_pixels, 0)
            dc.DrawLine(0, 0, 0, resolution_y_pixels)
            dc.DrawLine(resolution_x_pixels, 0, resolution_x_pixels, resolution_y_pixels)
            dc.DrawLine(0, resolution_y_pixels, resolution_x_pixels, resolution_y_pixels)

            dc.SetPen(wx.Pen("red", 2))
            aspectRatio = float(resolution_x_pixels) / float(resolution_y_pixels)

            projectedXmm = float(self.projected_X_mm.GetValue())
            projectedYmm = round(projectedXmm / aspectRatio)

            pixelsXPerMM = resolution_x_pixels / projectedXmm
            pixelsYPerMM = resolution_y_pixels / projectedYmm

            gridCountX = int(projectedXmm / 10)
            gridCountY = int(projectedYmm / 10)

            for y in xrange(0, gridCountY + 1):
                for x in xrange(0, gridCountX + 1):
                    dc.DrawLine(0, y * (pixelsYPerMM * 10), resolution_x_pixels, y * (pixelsYPerMM * 10))
                    dc.DrawLine(x * (pixelsXPerMM * 10), 0, x * (pixelsXPerMM * 10), resolution_y_pixels)

            self.first_layer.SetValue(False)
            self.display_frame.slicer = 'bitmap'
            self.display_frame.draw_layer(gridBitmap.ConvertToImage())

    def present_first_layer(self, event):
        if (self.first_layer.GetValue()):
            if not hasattr(self, "layers"):
                print "No model loaded!"
                self.first_layer.SetValue(False)
                return
            self.display_frame.offset = (float(self.offset_X.GetValue()), float(self.offset_Y.GetValue()))
            self.display_frame.scale = float(self.scale.GetValue())

            self.display_frame.slicer = self.layers[2]
            self.display_frame.dpi = self.get_dpi()
            self.display_frame.draw_layer(copy.deepcopy(self.layers[0][0]))
            self.calibrate.SetValue(False)
            if self.show_first_layer_timer != -1.0:
                def unpresent_first_layer():
                    self.display_frame.clear_layer()
                    self.first_layer.SetValue(False)
                wx.CallLater(self.show_first_layer_timer.GetValue() * 1000, unpresent_first_layer)

    def update_offset(self, event):

        offset_x = float(self.offset_X.GetValue())
        offset_y = float(self.offset_Y.GetValue())
        self.display_frame.offset = (offset_x, offset_y)

        self._set_setting('project_offset_x', offset_x)
        self._set_setting('project_offset_y', offset_y)

        self.refresh_display(event)

    def refresh_display(self, event):
        self.present_calibrate(event)
        self.present_first_layer(event)

    def update_thickness(self, event):
        self._set_setting('project_layer', self.thickness.GetValue())
        self.refresh_display(event)

    def update_projected_Xmm(self, event):
        self._set_setting('project_projected_x', self.projected_X_mm.GetValue())
        self.refresh_display(event)

    def update_scale(self, event):
        scale = float(self.scale.GetValue())
        self.display_frame.scale = scale
        self._set_setting('project_scale', scale)
        self.refresh_display(event)

    def update_interval(self, event):
        interval = float(self.interval.GetValue())
        self.display_frame.interval = interval
        self._set_setting('project_interval', interval)
        self.set_estimated_time()
        self.refresh_display(event)

    def update_pause(self, event):
        pause = float(self.pause.GetValue())
        self.display_frame.pause = pause
        self._set_setting('project_pause', pause)
        self.set_estimated_time()
        self.refresh_display(event)

    def update_overshoot(self, event):
        overshoot = float(self.overshoot.GetValue())
        self.display_frame.pause = overshoot
        self._set_setting('project_overshoot', overshoot)

    def update_prelift_gcode(self, event):
        prelift_gcode = self.prelift_gcode.GetValue().replace('\n', "\\n")
        self.display_frame.prelift_gcode = prelift_gcode
        self._set_setting('project_prelift_gcode', prelift_gcode)

    def update_postlift_gcode(self, event):
        postlift_gcode = self.postlift_gcode.GetValue().replace('\n', "\\n")
        self.display_frame.postlift_gcode = postlift_gcode
        self._set_setting('project_postlift_gcode', postlift_gcode)

    def update_z_axis_rate(self, event):
        z_axis_rate = int(self.z_axis_rate.GetValue())
        self.display_frame.z_axis_rate = z_axis_rate
        self._set_setting('project_z_axis_rate', z_axis_rate)

    def update_direction(self, event):
        direction = self.direction.GetValue()
        self.display_frame.direction = direction
        self._set_setting('project_direction', direction)

    def update_fullscreen(self, event):
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        else:
            self.display_frame.ShowFullScreen(0)
        self.refresh_display(event)

    def update_resolution(self, event):
        x = int(self.X.GetValue())
        y = int(self.Y.GetValue())
        self.display_frame.resize((x, y))
        self._set_setting('project_x', x)
        self._set_setting('project_y', y)
        self.refresh_display(event)

    def get_dpi(self):
        resolution_x_pixels = int(self.X.GetValue())
        projected_x_mm = float(self.projected_X_mm.GetValue())
        projected_x_inches = projected_x_mm / 25.4

        return resolution_x_pixels / projected_x_inches

    def start_present(self, event):
        if not hasattr(self, "layers"):
            print "No model loaded!"
            return

        self.pause_button.SetLabel("Pause")
        self.set_current_layer(0)
        self.display_frame.Raise()
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        self.display_frame.slicer = self.layers[2]
        self.display_frame.dpi = self.get_dpi()
        self.display_frame.present(self.layers[0][:],
                                   thickness = float(self.thickness.GetValue()),
                                   interval = float(self.interval.GetValue()),
                                   scale = float(self.scale.GetValue()),
                                   pause = float(self.pause.GetValue()),
                                   overshoot = float(self.overshoot.GetValue()),
                                   z_axis_rate = int(self.z_axis_rate.GetValue()),
                                   prelift_gcode = self.prelift_gcode.GetValue(),
                                   postlift_gcode = self.postlift_gcode.GetValue(),
                                   direction = self.direction.GetValue(),
                                   size = (float(self.X.GetValue()), float(self.Y.GetValue())),
                                   offset = (float(self.offset_X.GetValue()), float(self.offset_Y.GetValue())),
                                   layer_red = self.layer_red.IsChecked())

    def stop_present(self, event):
        print "Stop"
        self.pause_button.SetLabel("Pause")
        self.set_current_layer(0)
        self.display_frame.running = False

    def pause_present(self, event):
        if self.pause_button.GetLabel() == 'Pause':
            print "Pause"
            self.pause_button.SetLabel("Continue")
            self.display_frame.running = False
        else:
            print "Continue"
            self.pause_button.SetLabel("Pause")
            self.display_frame.running = True
            self.display_frame.next_img()

if __name__ == "__main__":
    provider = wx.SimpleHelpProvider()
    wx.HelpProvider_Set(provider)
    a = wx.App()
    SettingsFrame(None).Show()
    a.MainLoop()

########NEW FILE########
__FILENAME__ = pronsole
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import cmd
import glob
import os
import time
import sys
import shutil
import subprocess
import codecs
import argparse
import locale
import logging
import traceback
import re

from serial import SerialException

from . import printcore
from .utils import install_locale, run_command, get_command_output, \
    format_time, format_duration, RemainingTimeEstimator, \
    get_home_pos, parse_build_dimensions, parse_temperature_report
install_locale('pronterface')
from printrun.power import powerset_print_start, powerset_print_stop
from printrun import gcoder

from functools import wraps

if os.name == "nt":
    try:
        import _winreg
    except:
        pass
READLINE = True
try:
    import readline
    try:
        readline.rl.mode.show_all_if_ambiguous = "on"  # config pyreadline on windows
    except:
        pass
except:
    READLINE = False  # neither readline module is available

tempreading_exp = re.compile("(^T:| T:)")

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8] + ".g"

def setting_add_tooltip(func):
    @wraps(func)
    def decorator(self, *args, **kwargs):
        widget = func(self, *args, **kwargs)
        helptxt = self.help or ""
        sep, deftxt = "", ""
        if len(helptxt):
            sep = "\n"
            if helptxt.find("\n") >= 0:
                sep = "\n\n"
        if self.default is not "":
            deftxt = _("Default: ")
            resethelp = _("(Control-doubleclick to reset to default value)")
            if len(repr(self.default)) > 10:
                deftxt += "\n    " + repr(self.default).strip("'") + "\n" + resethelp
            else:
                deftxt += repr(self.default) + "  " + resethelp
        helptxt += sep + deftxt
        if len(helptxt):
            widget.SetToolTipString(helptxt)
        return widget
    return decorator

class Setting(object):

    DEFAULT_GROUP = "Printer"

    hidden = False

    def __init__(self, name, default, label = None, help = None, group = None):
        self.name = name
        self.default = default
        self._value = default
        self.label = label
        self.help = help
        self.group = group if group else Setting.DEFAULT_GROUP

    def _get_value(self):
        return self._value

    def _set_value(self, value):
        raise NotImplementedError
    value = property(_get_value, _set_value)

    def set_default(self, e):
        import wx
        if e.CmdDown() and e.ButtonDClick() and self.default is not "":
            confirmation = wx.MessageDialog(None, _("Are you sure you want to reset the setting to the default value: {0!r} ?").format(self.default), _("Confirm set default"), wx.ICON_EXCLAMATION | wx.YES_NO | wx.NO_DEFAULT)
            if confirmation.ShowModal() == wx.ID_YES:
                self._set_value(self.default)
        else:
            e.Skip()

    @setting_add_tooltip
    def get_label(self, parent):
        import wx
        widget = wx.StaticText(parent, -1, self.label or self.name)
        widget.set_default = self.set_default
        return widget

    @setting_add_tooltip
    def get_widget(self, parent):
        return self.get_specific_widget(parent)

    def get_specific_widget(self, parent):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class HiddenSetting(Setting):

    hidden = True

    def _set_value(self, value):
        self._value = value
    value = property(Setting._get_value, _set_value)

class wxSetting(Setting):

    widget = None

    def _set_value(self, value):
        self._value = value
        if self.widget:
            self.widget.SetValue(value)
    value = property(Setting._get_value, _set_value)

    def update(self):
        self.value = self.widget.GetValue()

class StringSetting(wxSetting):

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.TextCtrl(parent, -1, str(self.value))
        return self.widget

class ComboSetting(wxSetting):

    def __init__(self, name, default, choices, label = None, help = None, group = None):
        super(ComboSetting, self).__init__(name, default, label, help, group)
        self.choices = choices

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.ComboBox(parent, -1, str(self.value), choices = self.choices, style = wx.CB_DROPDOWN)
        return self.widget

class SpinSetting(wxSetting):

    def __init__(self, name, default, min, max, label = None, help = None, group = None, increment = 0.1):
        super(SpinSetting, self).__init__(name, default, label, help, group)
        self.min = min
        self.max = max
        self.increment = increment

    def get_specific_widget(self, parent):
        from wx.lib.agw.floatspin import FloatSpin
        self.widget = FloatSpin(parent, -1, min_val = self.min, max_val = self.max, digits = 0)
        self.widget.SetValue(self.value)
        return self.widget

class FloatSpinSetting(SpinSetting):

    def get_specific_widget(self, parent):
        from wx.lib.agw.floatspin import FloatSpin
        self.widget = FloatSpin(parent, -1, value = self.value, min_val = self.min, max_val = self.max, increment = self.increment, digits = 2)
        return self.widget

class BooleanSetting(wxSetting):

    def _get_value(self):
        return bool(self._value)

    def _set_value(self, value):
        self._value = value
        if self.widget:
            self.widget.SetValue(bool(value))

    value = property(_get_value, _set_value)

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.CheckBox(parent, -1)
        self.widget.SetValue(bool(self.value))
        return self.widget

class StaticTextSetting(wxSetting):

    def __init__(self, name, label = " ", text = "", help = None, group = None):
        super(StaticTextSetting, self).__init__(name, "", label, help, group)
        self.text = text

    def update(self):
        pass

    def _get_value(self):
        return ""

    def _set_value(self, value):
        pass

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.StaticText(parent, -1, self.text)
        return self.widget

class BuildDimensionsSetting(wxSetting):

    widgets = None

    def _set_value(self, value):
        self._value = value
        if self.widgets:
            self._set_widgets_values(value)
    value = property(wxSetting._get_value, _set_value)

    def _set_widgets_values(self, value):
        build_dimensions_list = parse_build_dimensions(value)
        for i in range(len(self.widgets)):
            self.widgets[i].SetValue(build_dimensions_list[i])

    def get_widget(self, parent):
        from wx.lib.agw.floatspin import FloatSpin
        import wx
        build_dimensions = parse_build_dimensions(self.value)
        self.widgets = []
        w = lambda val, m, M: self.widgets.append(FloatSpin(parent, -1, value = val, min_val = m, max_val = M, digits = 2))
        addlabel = lambda name, pos: self.widget.Add(wx.StaticText(parent, -1, name), pos = pos, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = 5)
        addwidget = lambda *pos: self.widget.Add(self.widgets[-1], pos = pos, flag = wx.RIGHT, border = 5)
        self.widget = wx.GridBagSizer()
        addlabel(_("Width"), (0, 0))
        w(build_dimensions[0], 0, 2000)
        addwidget(0, 1)
        addlabel(_("Depth"), (0, 2))
        w(build_dimensions[1], 0, 2000)
        addwidget(0, 3)
        addlabel(_("Height"), (0, 4))
        w(build_dimensions[2], 0, 2000)
        addwidget(0, 5)
        addlabel(_("X offset"), (1, 0))
        w(build_dimensions[3], -2000, 2000)
        addwidget(1, 1)
        addlabel(_("Y offset"), (1, 2))
        w(build_dimensions[4], -2000, 2000)
        addwidget(1, 3)
        addlabel(_("Z offset"), (1, 4))
        w(build_dimensions[5], -2000, 2000)
        addwidget(1, 5)
        addlabel(_("X home pos."), (2, 0))
        w(build_dimensions[6], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 1))
        addlabel(_("Y home pos."), (2, 2))
        w(build_dimensions[7], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 3))
        addlabel(_("Z home pos."), (2, 4))
        w(build_dimensions[8], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 5))
        return self.widget

    def update(self):
        values = [float(w.GetValue()) for w in self.widgets]
        self.value = "%.02fx%.02fx%.02f%+.02f%+.02f%+.02f%+.02f%+.02f%+.02f" % tuple(values)

class Settings(object):
    def __baudrate_list(self): return ["2400", "9600", "19200", "38400", "57600", "115200", "250000"]

    def __init__(self, root):
        # defaults here.
        # the initial value determines the type
        self._add(StringSetting("port", "", _("Serial port"), _("Port used to communicate with printer")))
        self._add(ComboSetting("baudrate", 115200, self.__baudrate_list(), _("Baud rate"), _("Communications Speed")))
        self._add(BooleanSetting("tcp_streaming_mode", False, _("TCP streaming mode"), _("When using a TCP connection to the printer, the streaming mode will not wait for acks from the printer to send new commands. This will break things such as ETA prediction, but can result in smoother prints.")), root.update_tcp_streaming_mode)
        self._add(SpinSetting("bedtemp_abs", 110, 0, 400, _("Bed temperature for ABS"), _("Heated Build Platform temp for ABS (deg C)"), "Printer"))
        self._add(SpinSetting("bedtemp_pla", 60, 0, 400, _("Bed temperature for PLA"), _("Heated Build Platform temp for PLA (deg C)"), "Printer"))
        self._add(SpinSetting("temperature_abs", 230, 0, 400, _("Extruder temperature for ABS"), _("Extruder temp for ABS (deg C)"), "Printer"))
        self._add(SpinSetting("temperature_pla", 185, 0, 400, _("Extruder temperature for PLA"), _("Extruder temp for PLA (deg C)"), "Printer"))
        self._add(SpinSetting("xy_feedrate", 3000, 0, 50000, _("X && Y manual feedrate"), _("Feedrate for Control Panel Moves in X and Y (mm/min)"), "Printer"))
        self._add(SpinSetting("z_feedrate", 200, 0, 50000, _("Z manual feedrate"), _("Feedrate for Control Panel Moves in Z (mm/min)"), "Printer"))
        self._add(SpinSetting("e_feedrate", 100, 0, 1000, _("E manual feedrate"), _("Feedrate for Control Panel Moves in Extrusions (mm/min)"), "Printer"))
        self._add(StringSetting("slicecommand", "python skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s", _("Slice command"), _("Slice command"), "External"))
        self._add(StringSetting("sliceoptscommand", "python skeinforge/skeinforge_application/skeinforge.py", _("Slicer options command"), _("Slice settings command"), "External"))
        self._add(StringSetting("final_command", "", _("Final command"), _("Executable to run when the print is finished"), "External"))
        self._add(StringSetting("error_command", "", _("Error command"), _("Executable to run when an error occurs"), "External"))

        self._add(HiddenSetting("project_offset_x", 0.0))
        self._add(HiddenSetting("project_offset_y", 0.0))
        self._add(HiddenSetting("project_interval", 2.0))
        self._add(HiddenSetting("project_pause", 2.5))
        self._add(HiddenSetting("project_scale", 1.0))
        self._add(HiddenSetting("project_x", 1024))
        self._add(HiddenSetting("project_y", 768))
        self._add(HiddenSetting("project_projected_x", 150.0))
        self._add(HiddenSetting("project_direction", "Top Down"))
        self._add(HiddenSetting("project_overshoot", 3.0))
        self._add(HiddenSetting("project_z_axis_rate", 200))
        self._add(HiddenSetting("project_layer", 0.1))
        self._add(HiddenSetting("project_prelift_gcode", ""))
        self._add(HiddenSetting("project_postlift_gcode", ""))
        self._add(HiddenSetting("pause_between_prints", True))
        self._add(HiddenSetting("default_extrusion", 5.0))
        self._add(HiddenSetting("last_extrusion", 5.0))
        self._add(HiddenSetting("total_filament_used", 0.0))

    _settings = []

    def __setattr__(self, name, value):
        if name.startswith("_"):
            return object.__setattr__(self, name, value)
        if isinstance(value, Setting):
            if not value.hidden:
                self._settings.append(value)
            object.__setattr__(self, "_" + name, value)
        elif hasattr(self, "_" + name):
            getattr(self, "_" + name).value = value
        else:
            setattr(self, name, StringSetting(name = name, default = value))

    def __getattr__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return getattr(self, "_" + name).value

    def _add(self, setting, callback = None, validate = None,
             alias = None, autocomplete_list = None):
        setattr(self, setting.name, setting)
        if callback:
            setattr(self, "__" + setting.name + "_cb", callback)
        if validate:
            setattr(self, "__" + setting.name + "_validate", validate)
        if alias:
            setattr(self, "__" + setting.name + "_alias", alias)
        if autocomplete_list:
            setattr(self, "__" + setting.name + "_list", autocomplete_list)

    def _set(self, key, value):
        try:
            value = getattr(self, "__%s_alias" % key)()[value]
        except KeyError:
            pass
        except AttributeError:
            pass
        try:
            getattr(self, "__%s_validate" % key)(value)
        except AttributeError:
            pass
        t = type(getattr(self, key))
        if t == bool and value == "False": setattr(self, key, False)
        else: setattr(self, key, t(value))
        try:
            cb = None
            try:
                cb = getattr(self, "__%s_cb" % key)
            except AttributeError:
                pass
            if cb is not None: cb(key, value)
        except:
            logging.warning((_("Failed to run callback after setting \"%s\":") % key) +
                            "\n" + traceback.format_exc())
        return value

    def _tabcomplete(self, key):
        try:
            return getattr(self, "__%s_list" % key)()
        except AttributeError:
            pass
        try:
            return getattr(self, "__%s_alias" % key)().keys()
        except AttributeError:
            pass
        return []

    def _all_settings(self):
        return self._settings

class Status:

    def __init__(self):
        self.extruder_temp = 0
        self.extruder_temp_target = 0
        self.bed_temp = 0
        self.bed_temp_target = 0
        self.print_job = None
        self.print_job_progress = 1.0

    def update_tempreading(self, tempstr):
        temps = parse_temperature_report(tempstr)
        if "T0" in temps and temps["T0"][0]: hotend_temp = float(temps["T0"][0])
        elif "T" in temps and temps["T"][0]: hotend_temp = float(temps["T"][0])
        else: hotend_temp = None
        if "T0" in temps and temps["T0"][1]: hotend_setpoint = float(temps["T0"][1])
        elif "T" in temps and temps["T"][1]: hotend_setpoint = float(temps["T"][1])
        else: hotend_setpoint = None
        if hotend_temp is not None:
            self.extruder_temp = hotend_temp
            if hotend_setpoint is not None:
                self.extruder_temp_target = hotend_setpoint
        bed_temp = float(temps["B"][0]) if "B" in temps and temps["B"][0] else None
        if bed_temp is not None:
            self.bed_temp = bed_temp
            setpoint = temps["B"][1]
            if setpoint:
                self.bed_temp_target = float(setpoint)

    @property
    def bed_enabled(self):
        return self.bed_temp != 0

    @property
    def extruder_enabled(self):
        return self.extruder_temp != 0


class pronsole(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        if not READLINE:
            self.completekey = None
        self.status = Status()
        self.dynamic_temp = False
        self.compute_eta = None
        self.p = printcore.printcore()
        self.p.recvcb = self.recvcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
        self.p.layerchangecb = self.layer_change_cb
        self.p.process_host_command = self.process_host_command
        self.recvlisteners = []
        self.in_macro = False
        self.p.onlinecb = self.online
        self.p.errorcb = self.logError
        self.fgcode = None
        self.listing = 0
        self.sdfiles = []
        self.paused = False
        self.sdprinting = 0
        self.uploading = 0  # Unused, just for pronterface generalization
        self.temps = {"pla": "185", "abs": "230", "off": "0"}
        self.bedtemps = {"pla": "60", "abs": "110", "off": "0"}
        self.percentdone = 0
        self.tempreadings = ""
        self.macros = {}
        self.history_file = "~/.pronsole-history"
        self.rc_loaded = False
        self.processing_rc = False
        self.processing_args = False
        self.settings = Settings(self)
        self.settings._add(BuildDimensionsSetting("build_dimensions", "200x200x100+0+0+0+0+0+0", _("Build dimensions"), _("Dimensions of Build Platform\n & optional offset of origin\n & optional switch position\n\nExamples:\n   XXXxYYY\n   XXX,YYY,ZZZ\n   XXXxYYYxZZZ+OffX+OffY+OffZ\nXXXxYYYxZZZ+OffX+OffY+OffZ+HomeX+HomeY+HomeZ"), "Printer"), self.update_build_dimensions)
        self.settings._port_list = self.scanserial
        self.settings._temperature_abs_cb = self.set_temp_preset
        self.settings._temperature_pla_cb = self.set_temp_preset
        self.settings._bedtemp_abs_cb = self.set_temp_preset
        self.settings._bedtemp_pla_cb = self.set_temp_preset
        self.update_build_dimensions(None, self.settings.build_dimensions)
        self.monitoring = 0
        self.starttime = 0
        self.extra_print_time = 0
        self.silent = False
        self.commandprefixes = 'MGT$'
        self.promptstrs = {"offline": "%(bold)soffline>%(normal)s ",
                           "fallback": "%(bold)sPC>%(normal)s ",
                           "macro": "%(bold)s..>%(normal)s ",
                           "online": "%(bold)sT:%(extruder_temp_fancy)s%(progress_fancy)s>%(normal)s "}

    #  --------------------------------------------------------------
    #  General console handling
    #  --------------------------------------------------------------

    def postloop(self):
        self.p.disconnect()
        cmd.Cmd.postloop(self)

    def preloop(self):
        self.log(_("Welcome to the printer console! Type \"help\" for a list of available commands."))
        self.prompt = self.promptf()
        cmd.Cmd.preloop(self)

    # We replace this function, defined in cmd.py .
    # It's default behavior with regards to Ctr-C
    # and Ctr-D doesn't make much sense...
    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """

        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey + ": complete")
                history = os.path.expanduser(self.history_file)
                if os.path.exists(history):
                    readline.read_history_file(history)
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro) + "\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    if self.use_rawinput:
                        try:
                            line = raw_input(self.prompt)
                        except EOFError:
                            print ""
                            self.do_exit("")
                        except KeyboardInterrupt:
                            print ""
                            line = ""
                    else:
                        self.stdout.write(self.prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            line = ""
                        else:
                            line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                    readline.write_history_file(history)
                except ImportError:
                    pass

    def confirm(self):
        y_or_n = raw_input("y/n: ")
        if y_or_n == "y":
            return True
        elif y_or_n != "n":
            return self.confirm()
        return False

    def log(self, *msg):
        print u"".join(unicode(i) for i in msg)

    def logError(self, *msg):
        msg = u"".join(unicode(i) for i in msg)
        logging.error(msg)
        if not self.settings.error_command:
            return
        output = get_command_output(self.settings.error_command, {"$m": msg})
        if output:
            self.log("Error command output:")
            self.log(output.rstrip())

    def promptf(self):
        """A function to generate prompts so that we can do dynamic prompts. """
        if self.in_macro:
            promptstr = self.promptstrs["macro"]
        elif not self.p.online:
            promptstr = self.promptstrs["offline"]
        elif self.status.extruder_enabled:
            promptstr = self.promptstrs["online"]
        else:
            promptstr = self.promptstrs["fallback"]
        if "%" not in promptstr:
            return promptstr
        else:
            specials = {}
            specials["extruder_temp"] = str(int(self.status.extruder_temp))
            specials["extruder_temp_target"] = str(int(self.status.extruder_temp_target))
            if self.status.extruder_temp_target == 0:
                specials["extruder_temp_fancy"] = str(int(self.status.extruder_temp))
            else:
                specials["extruder_temp_fancy"] = "%s/%s" % (str(int(self.status.extruder_temp)), str(int(self.status.extruder_temp_target)))
            if self.p.printing:
                progress = int(1000 * float(self.p.queueindex) / len(self.p.mainqueue)) / 10
            elif self.sdprinting:
                progress = self.percentdone
            else:
                progress = 0.0
            specials["progress"] = str(progress)
            if self.p.printing or self.sdprinting:
                specials["progress_fancy"] = " " + str(progress) + "%"
            else:
                specials["progress_fancy"] = ""
            specials["bold"] = "\033[01m"
            specials["normal"] = "\033[00m"
            return promptstr % specials

    def postcmd(self, stop, line):
        """ A hook we override to generate prompts after
            each command is executed, for the next prompt.
            We also use it to send M105 commands so that
            temp info gets updated for the prompt."""
        if self.p.online and self.dynamic_temp:
            self.p.send_now("M105")
        self.prompt = self.promptf()
        return stop

    def write_prompt(self):
        sys.stdout.write(self.promptf())
        sys.stdout.flush()

    def help_help(self, l = ""):
        self.do_help("")

    def do_gcodes(self, l = ""):
        self.help_gcodes()

    def help_gcodes(self):
        self.log("Gcodes are passed through to the printer as they are")

    def parseusercmd(self, line):
        pass

    def help_shell(self):
        self.log("Executes a python command. Example:")
        self.log("! os.listdir('.')")

    def do_shell(self, l):
        exec(l)

    def emptyline(self):
        """Called when an empty line is entered - do not remove"""
        pass

    def default(self, l):
        if l[0].upper() in self.commandprefixes.upper():
            if self.p and self.p.online:
                if not self.p.loud:
                    self.log("SENDING:" + l.upper())
                self.p.send_now(l.upper())
            else:
                self.logError(_("Printer is not online."))
            return
        elif l[0] == "@":
            if self.p and self.p.online:
                if not self.p.loud:
                    self.log("SENDING:" + l[1:])
                self.p.send_now(l[1:])
            else:
                self.logError(_("Printer is not online."))
            return
        else:
            cmd.Cmd.default(self, l)

    def do_exit(self, l):
        if self.status.extruder_temp_target != 0:
            print "Setting extruder temp to 0"
        self.p.send_now("M104 S0.0")
        if self.status.bed_enabled:
            if self.status.bed_temp_target != 0:
                print "Setting bed temp to 0"
            self.p.send_now("M140 S0.0")
        self.log("Disconnecting from printer...")
        if self.p.printing:
            print "Are you sure you want to exit while printing?"
            print "(this will terminate the print)."
            if not self.confirm():
                return
        self.log(_("Exiting program. Goodbye!"))
        self.p.disconnect()
        sys.exit()

    def help_exit(self):
        self.log(_("Disconnects from the printer and exits the program."))

    # --------------------------------------------------------------
    # Macro handling
    # --------------------------------------------------------------

    def complete_macro(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.macros.keys() if i.startswith(text)]
        elif len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " "):
            return [i for i in ["/D", "/S"] + self.completenames(text) if i.startswith(text)]
        else:
            return []

    def hook_macro(self, l):
        l = l.rstrip()
        ls = l.lstrip()
        ws = l[:len(l) - len(ls)]  # just leading whitespace
        if len(ws) == 0:
            self.end_macro()
            # pass the unprocessed line to regular command processor to not require empty line in .pronsolerc
            return self.onecmd(l)
        self.cur_macro_def += l + "\n"

    def end_macro(self):
        if "onecmd" in self.__dict__: del self.onecmd  # remove override
        self.in_macro = False
        self.prompt = self.promptf()
        if self.cur_macro_def != "":
            self.macros[self.cur_macro_name] = self.cur_macro_def
            macro = self.compile_macro(self.cur_macro_name, self.cur_macro_def)
            setattr(self.__class__, "do_" + self.cur_macro_name, lambda self, largs, macro = macro: macro(self, *largs.split()))
            setattr(self.__class__, "help_" + self.cur_macro_name, lambda self, macro_name = self.cur_macro_name: self.subhelp_macro(macro_name))
            if not self.processing_rc:
                self.log("Macro '" + self.cur_macro_name + "' defined")
                # save it
                if not self.processing_args:
                    macro_key = "macro " + self.cur_macro_name
                    macro_def = macro_key
                    if "\n" in self.cur_macro_def:
                        macro_def += "\n"
                    else:
                        macro_def += " "
                    macro_def += self.cur_macro_def
                    self.save_in_rc(macro_key, macro_def)
        else:
            self.logError("Empty macro - cancelled")
        del self.cur_macro_name, self.cur_macro_def

    def compile_macro_line(self, line):
        line = line.rstrip()
        ls = line.lstrip()
        ws = line[:len(line) - len(ls)]  # just leading whitespace
        if ls == "" or ls.startswith('#'): return ""  # no code
        if ls.startswith('!'):
            return ws + ls[1:] + "\n"  # python mode
        else:
            ls = ls.replace('"', '\\"')  # need to escape double quotes
            ret = ws + 'self.parseusercmd("' + ls + '".format(*arg))\n'  # parametric command mode
            return ret + ws + 'self.onecmd("' + ls + '".format(*arg))\n'

    def compile_macro(self, macro_name, macro_def):
        if macro_def.strip() == "":
            self.logError("Empty macro - cancelled")
            return
        macro = None
        pycode = "def macro(self,*arg):\n"
        if "\n" not in macro_def.strip():
            pycode += self.compile_macro_line("  " + macro_def.strip())
        else:
            lines = macro_def.split("\n")
            for l in lines:
                pycode += self.compile_macro_line(l)
        exec pycode
        return macro

    def start_macro(self, macro_name, prev_definition = "", suppress_instructions = False):
        if not self.processing_rc and not suppress_instructions:
            self.logError("Enter macro using indented lines, end with empty line")
        self.cur_macro_name = macro_name
        self.cur_macro_def = ""
        self.onecmd = self.hook_macro  # override onecmd temporarily
        self.in_macro = False
        self.prompt = self.promptf()

    def delete_macro(self, macro_name):
        if macro_name in self.macros.keys():
            delattr(self.__class__, "do_" + macro_name)
            del self.macros[macro_name]
            self.log("Macro '" + macro_name + "' removed")
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("macro " + macro_name, "")
        else:
            self.logError("Macro '" + macro_name + "' is not defined")

    def do_macro(self, args):
        if args.strip() == "":
            self.print_topics("User-defined macros", map(str, self.macros.keys()), 15, 80)
            return
        arglist = args.split(None, 1)
        macro_name = arglist[0]
        if macro_name not in self.macros and hasattr(self.__class__, "do_" + macro_name):
            self.logError("Name '" + macro_name + "' is being used by built-in command")
            return
        if len(arglist) == 2:
            macro_def = arglist[1]
            if macro_def.lower() == "/d":
                self.delete_macro(macro_name)
                return
            if macro_def.lower() == "/s":
                self.subhelp_macro(macro_name)
                return
            self.cur_macro_def = macro_def
            self.cur_macro_name = macro_name
            self.end_macro()
            return
        if macro_name in self.macros:
            self.start_macro(macro_name, self.macros[macro_name])
        else:
            self.start_macro(macro_name)

    def help_macro(self):
        self.log("Define single-line macro: macro <name> <definition>")
        self.log("Define multi-line macro:  macro <name>")
        self.log("Enter macro definition in indented lines. Use {0} .. {N} to substitute macro arguments")
        self.log("Enter python code, prefixed with !  Use arg[0] .. arg[N] to substitute macro arguments")
        self.log("Delete macro:             macro <name> /d")
        self.log("Show macro definition:    macro <name> /s")
        self.log("'macro' without arguments displays list of defined macros")

    def subhelp_macro(self, macro_name):
        if macro_name in self.macros.keys():
            macro_def = self.macros[macro_name]
            if "\n" in macro_def:
                self.log("Macro '" + macro_name + "' defined as:")
                self.log(self.macros[macro_name] + "----------------")
            else:
                self.log("Macro '" + macro_name + "' defined as: '" + macro_def + "'")
        else:
            self.logError("Macro '" + macro_name + "' is not defined")

    # --------------------------------------------------------------
    # Configuration handling
    # --------------------------------------------------------------

    def set(self, var, str):
        try:
            t = type(getattr(self.settings, var))
            value = self.settings._set(var, str)
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("set " + var, "set %s %s" % (var, value))
        except AttributeError:
            logging.debug(_("Unknown variable '%s'") % var)
        except ValueError, ve:
            if hasattr(ve, "from_validator"):
                self.logError(_("Bad value %s for variable '%s': %s") % (str, var, ve.args[0]))
            else:
                self.logError(_("Bad value for variable '%s', expecting %s (%s)") % (var, repr(t)[1:-1], ve.args[0]))

    def do_set(self, argl):
        args = argl.split(None, 1)
        if len(args) < 1:
            for k in [kk for kk in dir(self.settings) if not kk.startswith("_")]:
                self.log("%s = %s" % (k, str(getattr(self.settings, k))))
            return
        if len(args) < 2:
            try:
                self.log("%s = %s" % (args[0], getattr(self.settings, args[0])))
            except AttributeError:
                logging.warning("Unknown variable '%s'" % args[0])
            return
        self.set(args[0], args[1])

    def help_set(self):
        self.log("Set variable:   set <variable> <value>")
        self.log("Show variable:  set <variable>")
        self.log("'set' without arguments displays all variables")

    def complete_set(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in dir(self.settings) if not i.startswith("_") and i.startswith(text)]
        elif len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " "):
            return [i for i in self.settings._tabcomplete(line.split()[1]) if i.startswith(text)]
        else:
            return []

    def load_rc(self, rc_filename):
        self.processing_rc = True
        try:
            rc = codecs.open(rc_filename, "r", "utf-8")
            self.rc_filename = os.path.abspath(rc_filename)
            for rc_cmd in rc:
                if not rc_cmd.lstrip().startswith("#"):
                    self.onecmd(rc_cmd)
            rc.close()
            if hasattr(self, "cur_macro_def"):
                self.end_macro()
            self.rc_loaded = True
        finally:
            self.processing_rc = False

    def load_default_rc(self, rc_filename = ".pronsolerc"):
        if rc_filename == ".pronsolerc" and hasattr(sys, "frozen") and sys.frozen in ["windows_exe", "console_exe"]:
            rc_filename = "printrunconf.ini"
        try:
            try:
                self.load_rc(os.path.join(os.path.expanduser("~"), rc_filename))
            except IOError:
                self.load_rc(rc_filename)
        except IOError:
            # make sure the filename is initialized
            self.rc_filename = os.path.abspath(os.path.join(os.path.expanduser("~"), rc_filename))

    def save_in_rc(self, key, definition):
        """
        Saves or updates macro or other definitions in .pronsolerc
        key is prefix that determines what is being defined/updated (e.g. 'macro foo')
        definition is the full definition (that is written to file). (e.g. 'macro foo move x 10')
        Set key as empty string to just add (and not overwrite)
        Set definition as empty string to remove it from .pronsolerc
        To delete line from .pronsolerc, set key as the line contents, and definition as empty string
        Only first definition with given key is overwritten.
        Updates are made in the same file position.
        Additions are made to the end of the file.
        """
        rci, rco = None, None
        if definition != "" and not definition.endswith("\n"):
            definition += "\n"
        try:
            written = False
            if os.path.exists(self.rc_filename):
                shutil.copy(self.rc_filename, self.rc_filename + "~bak")
                rci = codecs.open(self.rc_filename + "~bak", "r", "utf-8")
            rco = codecs.open(self.rc_filename + "~new", "w", "utf-8")
            if rci is not None:
                overwriting = False
                for rc_cmd in rci:
                    l = rc_cmd.rstrip()
                    ls = l.lstrip()
                    ws = l[:len(l) - len(ls)]  # just leading whitespace
                    if overwriting and len(ws) == 0:
                        overwriting = False
                    if not written and key != "" and rc_cmd.startswith(key) and (rc_cmd + "\n")[len(key)].isspace():
                        overwriting = True
                        written = True
                        rco.write(definition)
                    if not overwriting:
                        rco.write(rc_cmd)
                        if not rc_cmd.endswith("\n"): rco.write("\n")
            if not written:
                rco.write(definition)
            if rci is not None:
                rci.close()
            rco.close()
            shutil.move(self.rc_filename + "~new", self.rc_filename)
            # if definition != "":
            #    self.log("Saved '"+key+"' to '"+self.rc_filename+"'")
            # else:
            #    self.log("Removed '"+key+"' from '"+self.rc_filename+"'")
        except Exception, e:
            self.logError("Saving failed for ", key + ":", str(e))
        finally:
            del rci, rco

    #  --------------------------------------------------------------
    #  Configuration update callbacks
    #  --------------------------------------------------------------

    def update_build_dimensions(self, param, value):
        self.build_dimensions_list = parse_build_dimensions(value)
        self.p.analyzer.home_pos = get_home_pos(self.build_dimensions_list)

    def update_tcp_streaming_mode(self, param, value):
        self.p.tcp_streaming_mode = self.settings.tcp_streaming_mode

    #  --------------------------------------------------------------
    #  Command line options handling
    #  --------------------------------------------------------------

    def add_cmdline_arguments(self, parser):
        parser.add_argument('-v', '--verbose', help = _("increase verbosity"), action = "store_true")
        parser.add_argument('-c', '--conf', '--config', help = _("load this file on startup instead of .pronsolerc ; you may chain config files, if so settings auto-save will use the last specified file"), action = "append", default = [])
        parser.add_argument('-e', '--execute', help = _("executes command after configuration/.pronsolerc is loaded ; macros/settings from these commands are not autosaved"), action = "append", default = [])
        parser.add_argument('filename', nargs='?', help = _("file to load"))

    def process_cmdline_arguments(self, args):
        if args.verbose:
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
        for config in args.conf:
            self.load_rc(config)
        if not self.rc_loaded:
            self.load_default_rc()
        self.processing_args = True
        for command in args.execute:
            self.onecmd(command)
        self.processing_args = False
        if args.filename:
            filename = args.filename.decode(locale.getpreferredencoding())
            self.cmdline_filename_callback(filename)

    def cmdline_filename_callback(self, filename):
        self.do_load(filename)

    def parse_cmdline(self, args):
        parser = argparse.ArgumentParser(description = 'Printrun 3D printer interface')
        self.add_cmdline_arguments(parser)
        args = [arg for arg in args if not arg.startswith("-psn")]
        args = parser.parse_args(args = args)
        self.process_cmdline_arguments(args)

    #  --------------------------------------------------------------
    #  Printer connection handling
    #  --------------------------------------------------------------

    def connect_to_printer(self, port, baud):
        try:
            self.p.connect(port, baud)
            return True
        except SerialException as e:
            # Currently, there is no errno, but it should be there in the future
            if e.errno == 2:
                self.logError(_("Error: You are trying to connect to a non-existing port."))
            elif e.errno == 8:
                self.logError(_("Error: You don't have permission to open %s.") % port)
                self.logError(_("You might need to add yourself to the dialout group."))
            else:
                self.logError(traceback.format_exc())
            # Kill the scope anyway
            return False
        except OSError as e:
            if e.errno == 2:
                self.logError(_("Error: You are trying to connect to a non-existing port."))
            else:
                self.logError(traceback.format_exc())
            return False

    def do_connect(self, l):
        a = l.split()
        p = self.scanserial()
        port = self.settings.port
        if (port == "" or port not in p) and len(p) > 0:
            port = p[0]
        baud = self.settings.baudrate or 115200
        if len(a) > 0:
            port = a[0]
        if len(a) > 1:
            try:
                baud = int(a[1])
            except:
                self.log("Bad baud value '" + a[1] + "' ignored")
        if len(p) == 0 and not port:
            self.log("No serial ports detected - please specify a port")
            return
        if len(a) == 0:
            self.log("No port specified - connecting to %s at %dbps" % (port, baud))
        if port != self.settings.port:
            self.settings.port = port
            self.save_in_rc("set port", "set port %s" % port)
        if baud != self.settings.baudrate:
            self.settings.baudrate = baud
            self.save_in_rc("set baudrate", "set baudrate %d" % baud)
        self.connect_to_printer(port, baud)

    def help_connect(self):
        self.log("Connect to printer")
        self.log("connect <port> <baudrate>")
        self.log("If port and baudrate are not specified, connects to first detected port at 115200bps")
        ports = self.scanserial()
        if ports:
            self.log("Available ports: ", " ".join(ports))
        else:
            self.log("No serial ports were automatically found.")

    def complete_connect(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.scanserial() if i.startswith(text)]
        elif len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " "):
            return [i for i in ["2400", "9600", "19200", "38400", "57600", "115200"] if i.startswith(text)]
        else:
            return []

    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist = []
        if os.name == "nt":
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i = 0
                while(1):
                    baselist += [_winreg.EnumValue(key, i)[1]]
                    i += 1
            except:
                pass

        for g in ['/dev/ttyUSB*', '/dev/ttyACM*', "/dev/tty.*", "/dev/cu.*", "/dev/rfcomm*"]:
            baselist += glob.glob(g)
        return filter(self._bluetoothSerialFilter, baselist)

    def _bluetoothSerialFilter(self, serial):
        return not ("Bluetooth" in serial or "FireFly" in serial)

    def online(self):
        self.log("\rPrinter is now online")
        self.write_prompt()

    def do_disconnect(self, l):
        self.p.disconnect()

    def help_disconnect(self):
        self.log("Disconnects from the printer")

    def do_block_until_online(self, l):
        while not self.p.online:
            time.sleep(0.1)

    def help_block_until_online(self, l):
        self.log("Blocks until printer is online")
        self.log("Warning: if something goes wrong, this can block pronsole forever")

    #  --------------------------------------------------------------
    #  File loading handling
    #  --------------------------------------------------------------

    def do_load(self, filename):
        self._do_load(filename)

    def _do_load(self, filename):
        if not filename:
            self.logError("No file name given.")
            return
        self.log("Loading file: " + filename)
        if not os.path.exists(filename):
            self.logError("File not found!")
            return
        self.load_gcode(filename)
        self.log(_("Loaded %s, %d lines.") % (filename, len(self.fgcode)))
        self.log(_("Estimated duration: %d layers, %s") % self.fgcode.estimate_duration())

    def load_gcode(self, filename, layer_callback = None, gcode = None):
        if gcode is None:
            self.fgcode = gcoder.LightGCode(deferred = True)
        else:
            self.fgcode = gcode
        self.fgcode.prepare(open(filename, "rU"),
                            get_home_pos(self.build_dimensions_list),
                            layer_callback = layer_callback)
        self.fgcode.estimate_duration()
        self.filename = filename

    def complete_load(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.g*")]
            else:
                return glob.glob("*/") + glob.glob("*.g*")

    def help_load(self):
        self.log("Loads a gcode file (with tab-completion)")

    def do_slice(self, l):
        l = l.split()
        if len(l) == 0:
            self.logError(_("No file name given."))
            return
        settings = 0
        if l[0] == "set":
            settings = 1
        else:
            self.log(_("Slicing file: %s") % l[0])
            if not(os.path.exists(l[0])):
                self.logError(_("File not found!"))
                return
        try:
            if settings:
                command = self.settings.sliceoptscommand
                self.log(_("Entering slicer settings: %s") % command)
                run_command(command, blocking = True)
            else:
                command = self.settings.slicecommand
                stl_name = l[0]
                gcode_name = stl_name.replace(".stl", "_export.gcode").replace(".STL", "_export.gcode")
                run_command(command,
                            {"$s": stl_name,
                             "$o": gcode_name},
                            blocking = True)
                self.log(_("Loading sliced file."))
                self.do_load(l[0].replace(".stl", "_export.gcode"))
        except Exception, e:
            self.logError(_("Slicing failed: %s") % e)

    def complete_slice(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.stl")]
            else:
                return glob.glob("*/") + glob.glob("*.stl")

    def help_slice(self):
        self.log(_("Creates a gcode file from an stl model using the slicer (with tab-completion)"))
        self.log(_("slice filename.stl - create gcode file"))
        self.log(_("slice filename.stl view - create gcode file and view using skeiniso (if using skeinforge)"))
        self.log(_("slice set - adjust slicer settings"))

    #  --------------------------------------------------------------
    #  Print/upload handling
    #  --------------------------------------------------------------

    def do_upload(self, l):
        names = l.split()
        if len(names) == 2:
            filename = names[0]
            targetname = names[1]
        else:
            self.logError(_("Please enter target name in 8.3 format."))
            return
        if not self.p.online:
            self.logError(_("Not connected to printer."))
            return
        self._do_load(filename)
        self.log(_("Uploading as %s") % targetname)
        self.log(_("Uploading %s") % self.filename)
        self.p.send_now("M28 " + targetname)
        self.log(_("Press Ctrl-C to interrupt upload."))
        self.p.startprint(self.fgcode)
        try:
            sys.stdout.write(_("Progress: ") + "00.0%")
            sys.stdout.flush()
            while self.p.printing:
                time.sleep(0.5)
                sys.stdout.write("\b\b\b\b\b%04.1f%%" % (100 * float(self.p.queueindex) / len(self.p.mainqueue),))
                sys.stdout.flush()
            self.p.send_now("M29 " + targetname)
            time.sleep(0.2)
            self.p.clear = True
            self._do_ls(False)
            self.log("\b\b\b\b\b100%.")
            self.log(_("Upload completed. %s should now be on the card.") % targetname)
            return
        except (KeyboardInterrupt, Exception) as e:
            if isinstance(e, KeyboardInterrupt):
                self.logError(_("...interrupted!"))
            else:
                self.logError(_("Something wrong happened while uploading:"))
                traceback.print_exc(file = sys.stdout)
            self.p.pause()
            self.p.send_now("M29 " + targetname)
            time.sleep(0.2)
            self.p.cancelprint()
            self.logError(_("A partial file named %s may have been written to the sd card.") % targetname)

    def complete_upload(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.g*")]
            else:
                return glob.glob("*/") + glob.glob("*.g*")

    def help_upload(self):
        self.log("Uploads a gcode file to the sd card")

    def help_print(self):
        if not self.fgcode:
            self.log(_("Send a loaded gcode file to the printer. Load a file with the load command first."))
        else:
            self.log(_("Send a loaded gcode file to the printer. You have %s loaded right now.") % self.filename)

    def do_print(self, l):
        if not self.fgcode:
            self.logError(_("No file loaded. Please use load first."))
            return
        if not self.p.online:
            self.logError(_("Not connected to printer."))
            return
        self.log(_("Printing %s") % self.filename)
        self.log(_("You can monitor the print with the monitor command."))
        self.p.startprint(self.fgcode)

    def do_pause(self, l):
        if self.sdprinting:
            self.p.send_now("M25")
        else:
            if not self.p.printing:
                self.logError(_("Not printing, cannot pause."))
                return
            self.p.pause()
        self.paused = True

    def help_pause(self):
        self.log(_("Pauses a running print"))

    def pause(self, event):
        return self.do_pause(None)

    def do_resume(self, l):
        if not self.paused:
            self.logError(_("Not paused, unable to resume. Start a print first."))
            return
        self.paused = False
        if self.sdprinting:
            self.p.send_now("M24")
            return
        else:
            self.p.resume()

    def help_resume(self):
        self.log(_("Resumes a paused print."))

    def listfiles(self, line, echo = False):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
            if echo:
                self.log(_("Files on SD card:"))
                self.log("\n".join(self.sdfiles))
        elif self.listing:
            self.sdfiles.append(line.strip().lower())

    def _do_ls(self, echo):
        # FIXME: this was 2, but I think it should rather be 0 as in do_upload
        self.listing = 0
        self.sdfiles = []
        self.recvlisteners.append(lambda l: self.listfiles(l, echo))
        self.p.send_now("M20")

    def do_ls(self, l):
        if not self.p.online:
            self.logError(_("Printer is not online. Please connect to it first."))
            return
        self._do_ls(True)

    def help_ls(self):
        self.log(_("Lists files on the SD card"))

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            self.logError(_("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            self.log(l)
        if "File selected" in l:
            self.log(_("Starting print"))
            self.p.send_now("M24")
            self.sdprinting = 1
            # self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "Done printing file" in l:
            self.log(l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "SD printing byte" in l:
            # M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0 * int(vals[0]) / int(vals[1])
            except:
                pass

    def do_reset(self, l):
        self.p.reset()

    def help_reset(self):
        self.log(_("Resets the printer."))

    def do_sdprint(self, l):
        if not self.p.online:
            self.log(_("Printer is not online. Please connect to it first."))
            return
        self._do_ls(False)
        while self.listfiles in self.recvlisteners:
            time.sleep(0.1)
        if l.lower() not in self.sdfiles:
            self.log(_("File is not present on card. Please upload it first."))
            return
        self.recvlisteners.append(self.waitforsdresponse)
        self.p.send_now("M23 " + l.lower())
        self.log(_("Printing file: %s from SD card.") % l.lower())
        self.log(_("Requesting SD print..."))
        time.sleep(1)

    def help_sdprint(self):
        self.log(_("Print a file from the SD card. Tab completes with available file names."))
        self.log(_("sdprint filename.g"))

    def complete_sdprint(self, text, line, begidx, endidx):
        if not self.sdfiles and self.p.online:
            self._do_ls(False)
            while self.listfiles in self.recvlisteners:
                time.sleep(0.1)
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.sdfiles if i.startswith(text)]

    #  --------------------------------------------------------------
    #  Printcore callbacks
    #  --------------------------------------------------------------

    def startcb(self, resuming = False):
        self.starttime = time.time()
        if resuming:
            print _("Print resumed at: %s") % format_time(self.starttime)
        else:
            print _("Print started at: %s") % format_time(self.starttime)
            if not self.sdprinting:
                self.compute_eta = RemainingTimeEstimator(self.fgcode)
            else:
                self.compute_eta = None
        try:
            powerset_print_start(reason = "Preventing sleep during print")
        except:
            logging.error(_("Failed to set power settings:"))
            traceback.print_exc(file = sys.stdout)

    def endcb(self):
        try:
            powerset_print_stop()
        except:
            logging.error(_("Failed to set power settings:"))
            traceback.print_exc(file = sys.stdout)
        if self.p.queueindex == 0:
            print_duration = int(time.time() - self.starttime + self.extra_print_time)
            self.log(_("Print ended at: %(end_time)s and took %(duration)s") % {"end_time": format_time(time.time()),
                                                                                "duration": format_duration(print_duration)})

            # Update total filament length used
            new_total = self.settings.total_filament_used + self.fgcode.filament_length
            self.set("total_filament_used", new_total)

            if not self.settings.final_command:
                return
            output = get_command_output(self.settings.final_command,
                                        {"$s": str(self.filename),
                                         "$t": format_duration(print_duration)})
            if output:
                self.log("Final command output:")
                self.log(output.rstrip())

    def recvcb(self, l):
        if tempreading_exp.findall(l):
            self.tempreadings = l
            self.status.update_tempreading(l)
        tstring = l.rstrip()
        if tstring != "ok" and not self.listing and not self.monitoring:
            if tstring[:5] == "echo:":
                tstring = tstring[5:].lstrip()
            if self.silent is False: print "\r" + tstring.ljust(15)
            sys.stdout.write(self.promptf())
            sys.stdout.flush()
        for listener in self.recvlisteners:
            listener(l)

    def layer_change_cb(self, newlayer):
        if self.compute_eta:
            secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
            self.compute_eta.update_layer(newlayer, secondselapsed)

    def get_eta(self):
        if self.sdprinting or self.uploading:
            if self.uploading:
                fractioncomplete = float(self.p.queueindex) / len(self.p.mainqueue)
            else:
                fractioncomplete = float(self.percentdone / 100.0)
            secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
            # Prevent division by zero
            secondsestimate = secondselapsed / max(fractioncomplete, 0.000001)
            secondsremain = secondsestimate - secondselapsed
            progress = fractioncomplete
        else:
            secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
            secondsremain, secondsestimate = self.compute_eta(self.p.queueindex, secondselapsed)
            progress = self.p.queueindex
        return secondsremain, secondsestimate, progress

    def do_eta(self, l):
        if not self.p.printing:
            self.logError(_("Printer is not currently printing. No ETA available."))
        else:
            secondsremain, secondsestimate, progress = self.get_eta()
            eta = _("Est: %s of %s remaining") % (format_duration(secondsremain),
                                                  format_duration(secondsestimate))
            self.log(eta.strip())

    def help_eta(self):
        self.log(_("Displays estimated remaining print time."))

    #  --------------------------------------------------------------
    #  Temperature handling
    #  --------------------------------------------------------------

    def set_temp_preset(self, key, value):
        if not key.startswith("bed"):
            self.temps["pla"] = str(self.settings.temperature_pla)
            self.temps["abs"] = str(self.settings.temperature_abs)
            self.log("Hotend temperature presets updated, pla:%s, abs:%s" % (self.temps["pla"], self.temps["abs"]))
        else:
            self.bedtemps["pla"] = str(self.settings.bedtemp_pla)
            self.bedtemps["abs"] = str(self.settings.bedtemp_abs)
            self.log("Bed temperature presets updated, pla:%s, abs:%s" % (self.bedtemps["pla"], self.bedtemps["abs"]))

    def tempcb(self, l):
        if "T:" in l:
            self.log(l.strip().replace("T", "Hotend").replace("B", "Bed").replace("ok ", ""))

    def do_gettemp(self, l):
        if "dynamic" in l:
            self.dynamic_temp = True
        if self.p.online:
            self.p.send_now("M105")
            time.sleep(0.75)
            if not self.status.bed_enabled:
                print "Hotend: %s/%s" % (self.status.extruder_temp, self.status.extruder_temp_target)
            else:
                print "Hotend: %s/%s" % (self.status.extruder_temp, self.status.extruder_temp_target)
                print "Bed:    %s/%s" % (self.status.bed_temp, self.status.bed_temp_target)

    def help_gettemp(self):
        self.log(_("Read the extruder and bed temperature."))

    def do_settemp(self, l):
        l = l.lower().replace(", ", ".")
        for i in self.temps.keys():
            l = l.replace(i, self.temps[i])
        try:
            f = float(l)
        except:
            self.logError(_("You must enter a temperature."))
            return

        if f >= 0:
            if f > 250:
                print _("%s is a high temperature to set your extruder to. Are you sure you want to do that?") % f
                if not self.confirm():
                    return
            if self.p.online:
                self.p.send_now("M104 S" + l)
                self.log(_("Setting hotend temperature to %s degrees Celsius.") % f)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."))

    def help_settemp(self):
        self.log(_("Sets the hotend temperature to the value entered."))
        self.log(_("Enter either a temperature in celsius or one of the following keywords"))
        self.log(", ".join([i + "(" + self.temps[i] + ")" for i in self.temps.keys()]))

    def complete_settemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.temps.keys() if i.startswith(text)]

    def do_bedtemp(self, l):
        f = None
        try:
            l = l.lower().replace(", ", ".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
        except:
            self.logError(_("You must enter a temperature."))
        if f is not None and f >= 0:
            if self.p.online:
                self.p.send_now("M140 S" + l)
                self.log(_("Setting bed temperature to %s degrees Celsius.") % f)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."))

    def help_bedtemp(self):
        self.log(_("Sets the bed temperature to the value entered."))
        self.log(_("Enter either a temperature in celsius or one of the following keywords"))
        self.log(", ".join([i + "(" + self.bedtemps[i] + ")" for i in self.bedtemps.keys()]))

    def complete_bedtemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.bedtemps.keys() if i.startswith(text)]

    def do_monitor(self, l):
        interval = 5
        if not self.p.online:
            self.logError(_("Printer is not online. Please connect to it first."))
            return
        if not (self.p.printing or self.sdprinting):
            self.logError(_("Printer is not printing. Please print something before monitoring."))
            return
        self.log(_("Monitoring printer, use ^C to interrupt."))
        if len(l):
            try:
                interval = float(l)
            except:
                self.logError(_("Invalid period given."))
        self.log(_("Updating values every %f seconds.") % (interval,))
        self.monitoring = 1
        prev_msg_len = 0
        try:
            while True:
                self.p.send_now("M105")
                if self.sdprinting:
                    self.p.send_now("M27")
                time.sleep(interval)
                if self.p.printing:
                    preface = _("Print progress: ")
                    progress = 100 * float(self.p.queueindex) / len(self.p.mainqueue)
                elif self.sdprinting:
                    preface = _("Print progress: ")
                    progress = self.percentdone
                prev_msg = preface + "%.1f%%" % progress
                if self.silent is False:
                    sys.stdout.write("\r" + prev_msg.ljust(prev_msg_len))
                    sys.stdout.flush()
                prev_msg_len = len(prev_msg)
        except KeyboardInterrupt:
            if self.silent is False: print _("Done monitoring.")
        self.monitoring = 0

    def help_monitor(self):
        self.log(_("Monitor a machine's temperatures and an SD print's status."))
        self.log(_("monitor - Reports temperature and SD print status (if SD printing) every 5 seconds"))
        self.log(_("monitor 2 - Reports temperature and SD print status (if SD printing) every 2 seconds"))

    #  --------------------------------------------------------------
    #  Manual printer controls
    #  --------------------------------------------------------------

    def do_tool(self, l):
        tool = None
        try:
            tool = int(l.lower().strip())
        except:
            self.logError(_("You must specify the tool index as an integer."))
        if tool is not None and tool >= 0:
            if self.p.online:
                self.p.send_now("T%d" % tool)
                self.log(_("Using tool %d.") % tool)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative tool numbers."))

    def help_tool(self):
        self.log(_("Switches to the specified tool (e.g. doing tool 1 will emit a T1 G-Code)."))

    def do_move(self, l):
        if len(l.split()) < 2:
            self.logError(_("No move specified."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to move."))
            return
        l = l.split()
        if l[0].lower() == "x":
            feed = self.settings.xy_feedrate
            axis = "X"
        elif l[0].lower() == "y":
            feed = self.settings.xy_feedrate
            axis = "Y"
        elif l[0].lower() == "z":
            feed = self.settings.z_feedrate
            axis = "Z"
        elif l[0].lower() == "e":
            feed = self.settings.e_feedrate
            axis = "E"
        else:
            self.logError(_("Unknown axis."))
            return
        try:
            float(l[1])  # check if distance can be a float
        except:
            self.logError(_("Invalid distance"))
            return
        try:
            feed = int(l[2])
        except:
            pass
        self.p.send_now("G91")
        self.p.send_now("G1 " + axis + str(l[1]) + " F" + str(feed))
        self.p.send_now("G90")

    def help_move(self):
        self.log(_("Move an axis. Specify the name of the axis and the amount. "))
        self.log(_("move X 10 will move the X axis forward by 10mm at %s mm/min (default XY speed)") % self.settings.xy_feedrate)
        self.log(_("move Y 10 5000 will move the Y axis forward by 10mm at 5000mm/min"))
        self.log(_("move Z -1 will move the Z axis down by 1mm at %s mm/min (default Z speed)") % self.settings.z_feedrate)
        self.log(_("Common amounts are in the tabcomplete list."))

    def complete_move(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in ["X ", "Y ", "Z ", "E "] if i.lower().startswith(text)]
        elif len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " "):
            base = line.split()[-1]
            rlen = 0
            if base.startswith("-"):
                rlen = 1
            if line[-1] == " ":
                base = ""
            return [i[rlen:] for i in ["-100", "-10", "-1", "-0.1", "100", "10", "1", "0.1", "-50", "-5", "-0.5", "50", "5", "0.5", "-200", "-20", "-2", "-0.2", "200", "20", "2", "0.2"] if i.startswith(base)]
        else:
            return []

    def do_extrude(self, l, override = None, overridefeed = 300):
        length = self.settings.default_extrusion  # default extrusion length
        feed = self.settings.e_feedrate  # default speed
        if not self.p.online:
            self.logError("Printer is not online. Unable to extrude.")
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.logError(_("Invalid length given."))
        if len(ls) > 1:
            try:
                feed = int(ls[1])
            except:
                self.logError(_("Invalid speed given."))
        if override is not None:
            length = override
            feed = overridefeed
        self.do_extrude_final(length, feed)

    def do_extrude_final(self, length, feed):
        if length > 0:
            self.log(_("Extruding %fmm of filament.") % (length,))
        elif length < 0:
            self.log(_("Reversing %fmm of filament.") % (-length,))
        else:
            self.log(_("Length is 0, not doing anything."))
        self.p.send_now("G91")
        self.p.send_now("G1 E" + str(length) + " F" + str(feed))
        self.p.send_now("G90")

    def help_extrude(self):
        self.log(_("Extrudes a length of filament, 5mm by default, or the number of mm given as a parameter"))
        self.log(_("extrude - extrudes 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude 20 - extrudes 20mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude -5 - REVERSES 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)"))

    def do_reverse(self, l):
        length = self.settings.default_extrusion  # default extrusion length
        feed = self.settings.e_feedrate  # default speed
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to reverse."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.logError(_("Invalid length given."))
        if len(ls) > 1:
            try:
                feed = int(ls[1])
            except:
                self.logError(_("Invalid speed given."))
        self.do_extrude("", -length, feed)

    def help_reverse(self):
        self.log(_("Reverses the extruder, 5mm by default, or the number of mm given as a parameter"))
        self.log(_("reverse - reverses 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("reverse 20 - reverses 20mm of filament at 300mm/min (5mm/s)"))
        self.log(_("reverse 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)"))
        self.log(_("reverse -5 - EXTRUDES 5mm of filament at 300mm/min (5mm/s)"))

    def do_home(self, l):
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to move."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        if "x" in l.lower():
            self.p.send_now("G28 X0")
        if "y" in l.lower():
            self.p.send_now("G28 Y0")
        if "z" in l.lower():
            self.p.send_now("G28 Z0")
        if "e" in l.lower():
            self.p.send_now("G92 E0")
        if not len(l):
            self.p.send_now("G28")
            self.p.send_now("G92 E0")

    def help_home(self):
        self.log(_("Homes the printer"))
        self.log(_("home - homes all axes and zeroes the extruder(Using G28 and G92)"))
        self.log(_("home xy - homes x and y axes (Using G28)"))
        self.log(_("home z - homes z axis only (Using G28)"))
        self.log(_("home e - set extruder position to zero (Using G92)"))
        self.log(_("home xyze - homes all axes and zeroes the extruder (Using G28 and G92)"))

    def do_off(self, l):
        self.off()

    def off(self, ignore = None):
        if self.p.online:
            if self.p.printing: self.pause(None)
            self.log(_("; Motors off"))
            self.onecmd("M84")
            self.log(_("; Extruder off"))
            self.onecmd("M104 S0")
            self.log(_("; Heatbed off"))
            self.onecmd("M140 S0")
            self.log(_("; Fan off"))
            self.onecmd("M107")
            self.log(_("; Power supply off"))
            self.onecmd("M81")
        else:
            self.logError(_("Printer is not online. Unable to turn it off."))

    def help_off(self):
        self.log(_("Turns off everything on the printer"))

    #  --------------------------------------------------------------
    #  Host commands handling
    #  --------------------------------------------------------------

    def process_host_command(self, command):
        """Override host command handling"""
        command = command.lstrip()
        if command.startswith(";@"):
            command = command[2:]
            self.log(_("G-Code calling host command \"%s\"") % command)
            self.onecmd(command)

    def do_run_script(self, l):
        p = run_command(l, {"$s": str(self.filename)}, stdout = subprocess.PIPE)
        for line in p.stdout.readlines():
            self.log("<< " + line.strip())

    def help_run_script(self):
        self.log(_("Runs a custom script. Current gcode filename can be given using $s token."))

    def do_run_gcode_script(self, l):
        p = run_command(l, {"$s": str(self.filename)}, stdout = subprocess.PIPE)
        for line in p.stdout.readlines():
            self.onecmd(line.strip())

    def help_run_gcode_script(self):
        self.log(_("Runs a custom script which output gcode which will in turn be executed. Current gcode filename can be given using $s token."))

########NEW FILE########
__FILENAME__ = pronterface
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import os
import Queue
import re
import sys
import time
import threading
import traceback
import cStringIO as StringIO
import subprocess
import glob
import logging

try: import simplejson as json
except ImportError: import json

from . import pronsole
from . import printcore

from .utils import install_locale, setup_logging, \
    iconfile, configfile, format_time, format_duration, \
    hexcolor_to_float, parse_temperature_report, \
    prepare_command, check_rgb_color, check_rgba_color
install_locale('pronterface')

try:
    import wx
except:
    logging.error(_("WX is not installed. This program requires WX to run."))
    raise

from printrun.gui.widgets import SpecialButton, MacroEditor, \
    PronterOptions, ButtonEdit

winsize = (800, 500)
layerindex = 0
if os.name == "nt":
    winsize = (800, 530)

pronterface_quitting = False

class PronterfaceQuitException(Exception):
    pass

from printrun.gui import MainWindow
from printrun.excluder import Excluder
from pronsole import dosify, wxSetting, HiddenSetting, StringSetting, SpinSetting, FloatSpinSetting, BooleanSetting, StaticTextSetting
from printrun import gcoder

tempreading_exp = re.compile("(^T:| T:)")

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
        setup_logging(sys.stdout)
        self.target = target

    def __del__(self):
        sys.stdout = self.stdout

    def write(self, data):
        try:
            self.target(data)
        except:
            pass
        try:
            data = data.encode("utf-8")
        except:
            pass
        self.stdout.write(data)

    def flush(self):
        self.stdout.flush()

class ComboSetting(wxSetting):

    def __init__(self, name, default, choices, label = None, help = None, group = None):
        super(ComboSetting, self).__init__(name, default, label, help, group)
        self.choices = choices

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.ComboBox(parent, -1, str(self.value), choices = self.choices, style = wx.CB_DROPDOWN)
        return self.widget

class PronterWindow(MainWindow, pronsole.pronsole):

    _fgcode = None

    def _get_fgcode(self):
        return self._fgcode

    def _set_fgcode(self, value):
        self._fgcode = value
        self.excluder = None
        self.excluder_e = None
        self.excluder_z_abs = None
        self.excluder_z_rel = None
    fgcode = property(_get_fgcode, _set_fgcode)

    def _get_display_graph(self):
        return self.settings.tempgraph
    display_graph = property(_get_display_graph)

    def _get_display_gauges(self):
        return self.settings.tempgauges
    display_gauges = property(_get_display_gauges)

    def __init__(self, app, filename = None, size = winsize):
        pronsole.pronsole.__init__(self)
        self.app = app
        self.window_ready = False
        self.ui_ready = False
        self._add_settings(size)

        for field in dir(self.settings):
            if field.startswith("_gcview_color_"):
                cleanname = field[1:]
                color = hexcolor_to_float(getattr(self.settings, cleanname), 4)
                setattr(self, cleanname, list(color))

        self.pauseScript = "pause.gcode"
        self.endScript = "end.gcode"

        self.filename = filename

        self.statuscheck = False
        self.status_thread = None
        self.capture_skip = {}
        self.capture_skip_newline = False
        self.tempreport = ""
        self.userm114 = 0
        self.userm105 = 0
        self.m105_waitcycles = 0
        self.fgcode = None
        self.excluder = None
        self.slicep = None
        self.monitor_interval = 3
        self.current_pos = [0, 0, 0]
        self.paused = False
        self.uploading = False
        self.sentlines = Queue.Queue(0)
        self.cpbuttons = {
            "motorsoff": SpecialButton(_("Motors off"), ("M84"), (250, 250, 250), _("Switch all motors off")),
            "extrude": SpecialButton(_("Extrude"), ("pront_extrude"), (225, 200, 200), _("Advance extruder by set length")),
            "reverse": SpecialButton(_("Reverse"), ("pront_reverse"), (225, 200, 200), _("Reverse extruder by set length")),
        }
        self.custombuttons = []
        self.btndict = {}
        self.filehistory = None
        self.autoconnect = False
        self.parse_cmdline(sys.argv[1:])

        # FIXME: We need to initialize the main window after loading the
        # configs to restore the size, but this might have some unforeseen
        # consequences.
        # -- Okai, it seems it breaks things like update_gviz_params ><
        os.putenv("UBUNTU_MENUPROXY", "0")
        size = (self.settings.last_window_width, self.settings.last_window_height)
        MainWindow.__init__(self, None, title = _("Pronterface"), size = size)
        if self.settings.last_window_maximized:
            self.Maximize()
        self.SetIcon(wx.Icon(iconfile("pronterface.png"), wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MAXIMIZE, self.on_maximize)
        self.window_ready = True

        # set feedrates in printcore for pause/resume
        self.p.xy_feedrate = self.settings.xy_feedrate
        self.p.z_feedrate = self.settings.z_feedrate

        self.panel.SetBackgroundColour(self.bgcolor)
        customdict = {}
        try:
            execfile(configfile("custombtn.txt"), customdict)
            if len(customdict["btns"]):
                if not len(self.custombuttons):
                    try:
                        self.custombuttons = customdict["btns"]
                        for n in xrange(len(self.custombuttons)):
                            self.cbutton_save(n, self.custombuttons[n])
                        os.rename("custombtn.txt", "custombtn.old")
                        rco = open("custombtn.txt", "w")
                        rco.write(_("# I moved all your custom buttons into .pronsolerc.\n# Please don't add them here any more.\n# Backup of your old buttons is in custombtn.old\n"))
                        rco.close()
                    except IOError, x:
                        logging.error(str(x))
                else:
                    logging.warning(_("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc"))
                    logging.warning(_("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt"))

        except:
            pass
        self.create_menu()
        self.update_recent_files("recentfiles", self.settings.recentfiles)

        self.reload_ui()
        # disable all printer controls until we connect to a printer
        self.gui_set_disconnected()
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText(_("Not connected to printer."))

        self.t = Tee(self.catchprint)
        self.stdout = sys.stdout
        self.slicing = False
        self.loading_gcode = False
        self.loading_gcode_message = ""
        self.mini = False
        self.p.sendcb = self.sentcb
        self.p.preprintsendcb = self.preprintsendcb
        self.p.printsendcb = self.printsentcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
        self.curlayer = 0
        self.cur_button = None
        self.predisconnect_mainqueue = None
        self.predisconnect_queueindex = None
        self.predisconnect_layer = None
        self.hsetpoint = 0.0
        self.bsetpoint = 0.0
        if self.autoconnect:
            self.connect()
        if self.filename is not None:
            self.do_load(self.filename)
        if self.settings.monitor:
            self.update_monitor()

    #  --------------------------------------------------------------
    #  Main interface handling
    #  --------------------------------------------------------------

    def reset_ui(self):
        MainWindow.reset_ui(self)
        self.custombuttons_widgets = []

    def reload_ui(self, *args):
        if not self.window_ready: return
        self.Freeze()

        # If UI is being recreated, delete current one
        if self.ui_ready:
            # Store log console content
            logcontent = self.logbox.GetValue()
            # Create a temporary panel to reparent widgets with state we want
            # to retain across UI changes
            temppanel = wx.Panel(self)
            # TODO: add viz widgets to statefulControls
            for control in self.statefulControls:
                control.GetContainingSizer().Detach(control)
                control.Reparent(temppanel)
            self.panel.DestroyChildren()
            self.gwindow.Destroy()
            self.reset_ui()

        # Create UI
        if self.settings.uimode == "Tabbed":
            self.createTabbedGui()
        else:
            self.createGui(self.settings.uimode == "Compact",
                           self.settings.controlsmode == "Mini")

        if hasattr(self, "splitterwindow"):
            self.splitterwindow.SetSashPosition(self.settings.last_sash_position)

            def splitter_resize(event):
                self.splitterwindow.UpdateSize()
            self.splitterwindow.Bind(wx.EVT_SIZE, splitter_resize)

            def sash_position_changed(event):
                self.set("last_sash_position", self.splitterwindow.GetSashPosition())
            self.splitterwindow.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, sash_position_changed)

        # Set gcview parameters here as they don't get set when viewers are
        # created
        self.update_gcview_params()

        # Finalize
        if self.online:
            self.gui_set_connected()
        if self.ui_ready:
            self.logbox.SetValue(logcontent)
            temppanel.Destroy()
            self.panel.Layout()
            if self.fgcode:
                self.start_viz_thread()
        self.ui_ready = True
        self.Thaw()

    def on_resize(self, event):
        wx.CallAfter(self.on_resize_real)
        event.Skip()

    def on_resize_real(self):
        maximized = self.IsMaximized()
        self.set("last_window_maximized", maximized)
        if not maximized and not self.IsIconized():
            size = self.GetSize()
            self.set("last_window_width", size[0])
            self.set("last_window_height", size[1])

    def on_maximize(self, event):
        self.set("last_window_maximized", self.IsMaximized())
        event.Skip()

    def on_exit(self, event):
        self.Close()

    def kill(self, e):
        global pronterface_quitting
        pronterface_quitting = True
        self.statuscheck = False
        if self.status_thread:
            self.status_thread.join()
            self.status_thread = None
        self.p.recvcb = None
        self.p.disconnect()
        if hasattr(self, "feedrates_changed"):
            self.save_in_rc("set xy_feedrate", "set xy_feedrate %d" % self.settings.xy_feedrate)
            self.save_in_rc("set z_feedrate", "set z_feedrate %d" % self.settings.z_feedrate)
            self.save_in_rc("set e_feedrate", "set e_feedrate %d" % self.settings.e_feedrate)
        if self.settings.last_extrusion != self.settings.default_extrusion:
            self.save_in_rc("set last_extrusion", "set last_extrusion %d" % self.settings.last_extrusion)
        if self.excluder:
            self.excluder.close_window()
        wx.CallAfter(self.gwindow.Destroy)
        wx.CallAfter(self.Destroy)

    def _get_bgcolor(self):
        if self.settings.bgcolor != "auto":
            return self.settings.bgcolor
        else:
            return wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWFRAME)
    bgcolor = property(_get_bgcolor)

    #  --------------------------------------------------------------
    #  Main interface actions
    #  --------------------------------------------------------------

    def do_monitor(self, l = ""):
        if l.strip() == "":
            self.set("monitor", not self.settings.monitor)
        elif l.strip() == "off":
            self.set("monitor", False)
        else:
            try:
                self.monitor_interval = float(l)
                self.set("monitor", self.monitor_interval > 0)
            except:
                self.log(_("Invalid period given."))
        if self.settings.monitor:
            self.log(_("Monitoring printer."))
        else:
            self.log(_("Done monitoring."))

    def do_pront_extrude(self, l = ""):
        feed = self.settings.e_feedrate
        self.do_extrude_final(self.edist.GetValue(), feed)

    def do_pront_reverse(self, l = ""):
        feed = self.settings.e_feedrate
        self.do_extrude_final(- self.edist.GetValue(), feed)

    def do_settemp(self, l = ""):
        try:
            if l.__class__ not in (str, unicode) or not len(l):
                l = str(self.htemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.temps.keys():
                l = l.replace(i, self.temps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M104 S" + l)
                    self.log(_("Setting hotend temperature to %f degrees Celsius.") % f)
                    self.sethotendgui(f)
                else:
                    self.logError(_("Printer is not online."))
            else:
                self.logError(_("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."))
        except Exception, x:
            self.logError(_("You must enter a temperature. (%s)") % (repr(x),))

    def do_bedtemp(self, l = ""):
        try:
            if l.__class__ not in (str, unicode) or not len(l):
                l = str(self.btemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M140 S" + l)
                    self.log(_("Setting bed temperature to %f degrees Celsius.") % f)
                    self.setbedgui(f)
                else:
                    self.logError(_("Printer is not online."))
            else:
                self.logError(_("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."))
        except Exception, x:
            self.logError(_("You must enter a temperature. (%s)") % (repr(x),))

    def do_setspeed(self, l = ""):
        try:
            if l.__class__ not in (str, unicode) or not len(l):
                l = str(self.speed_slider.GetValue())
            else:
                l = l.lower()
            speed = int(l)
            if self.p.online:
                self.p.send_now("M220 S" + l)
                self.log(_("Setting print speed factor to %d%%.") % speed)
            else:
                self.logError(_("Printer is not online."))
        except Exception, x:
            self.logError(_("You must enter a speed. (%s)") % (repr(x),))

    def setbedgui(self, f):
        self.bsetpoint = f
        if self.display_gauges: self.bedtgauge.SetTarget(int(f))
        if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, int(f))
        if f > 0:
            wx.CallAfter(self.btemp.SetValue, str(f))
            self.set("last_bed_temperature", str(f))
            wx.CallAfter(self.setboff.SetBackgroundColour, None)
            wx.CallAfter(self.setboff.SetForegroundColour, None)
            wx.CallAfter(self.setbbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.setbbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.btemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.setboff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.setboff.SetForegroundColour, "white")
            wx.CallAfter(self.setbbtn.SetBackgroundColour, None)
            wx.CallAfter(self.setbbtn.SetForegroundColour, None)
            wx.CallAfter(self.btemp.SetBackgroundColour, "white")
            wx.CallAfter(self.btemp.Refresh)

    def sethotendgui(self, f):
        self.hsetpoint = f
        if self.display_gauges: self.hottgauge.SetTarget(int(f))
        if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, int(f))
        if f > 0:
            wx.CallAfter(self.htemp.SetValue, str(f))
            self.set("last_temperature", str(f))
            wx.CallAfter(self.settoff.SetBackgroundColour, None)
            wx.CallAfter(self.settoff.SetForegroundColour, None)
            wx.CallAfter(self.settbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.settbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.htemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.settoff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.settoff.SetForegroundColour, "white")
            wx.CallAfter(self.settbtn.SetBackgroundColour, None)
            wx.CallAfter(self.settbtn.SetForegroundColour, None)
            wx.CallAfter(self.htemp.SetBackgroundColour, "white")
            wx.CallAfter(self.htemp.Refresh)

    def rescanports(self, event = None):
        scanned = self.scanserial()
        portslist = list(scanned)
        if self.settings.port != "" and self.settings.port not in portslist:
            portslist.append(self.settings.port)
            self.serialport.Clear()
            self.serialport.AppendItems(portslist)
        if os.path.exists(self.settings.port) or self.settings.port in scanned:
            self.serialport.SetValue(self.settings.port)
        elif portslist:
            self.serialport.SetValue(portslist[0])

    def cbkey(self, e):
        if e.GetKeyCode() == wx.WXK_UP:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history.append(self.commandbox.GetValue())  # save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex - 1) % len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        elif e.GetKeyCode() == wx.WXK_DOWN:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history.append(self.commandbox.GetValue())  # save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex + 1) % len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        else:
            e.Skip()

    def plate(self, e):
        from . import stlplater as plater
        self.log(_("Plate function activated"))
        plater.StlPlater(size = (800, 580), callback = self.platecb,
                         parent = self,
                         build_dimensions = self.build_dimensions_list,
                         circular_platform = self.settings.circular_bed,
                         simarrange_path = self.settings.simarrange_path,
                         antialias_samples = int(self.settings.antialias3dsamples)).Show()

    def plate_gcode(self, e):
        from . import gcodeplater as plater
        self.log(_("G-Code plate function activated"))
        plater.GcodePlater(size = (800, 580), callback = self.platecb,
                           parent = self,
                           build_dimensions = self.build_dimensions_list,
                           circular_platform = self.settings.circular_bed,
                           antialias_samples = int(self.settings.antialias3dsamples)).Show()

    def platecb(self, name):
        self.log(_("Plated %s") % name)
        self.loadfile(None, name)

    def do_editgcode(self, e = None):
        if self.filename is not None:
            MacroEditor(self.filename, [line.raw for line in self.fgcode], self.doneediting, True)

    def doneediting(self, gcode):
        open(self.filename, "w").write("\n".join(gcode))
        wx.CallAfter(self.loadfile, None, self.filename)

    def sdmenu(self, e):
        obj = e.GetEventObject()
        popupmenu = wx.Menu()
        item = popupmenu.Append(-1, _("SD Upload"))
        if not self.fgcode:
            item.Enable(False)
        self.Bind(wx.EVT_MENU, self.upload, id = item.GetId())
        item = popupmenu.Append(-1, _("SD Print"))
        self.Bind(wx.EVT_MENU, self.sdprintfile, id = item.GetId())
        self.panel.PopupMenu(popupmenu, obj.GetPosition())

    def htemp_change(self, event):
        if self.hsetpoint > 0:
            self.do_settemp("")
        wx.CallAfter(self.htemp.SetInsertionPoint, 0)

    def btemp_change(self, event):
        if self.bsetpoint > 0:
            self.do_bedtemp("")
        wx.CallAfter(self.btemp.SetInsertionPoint, 0)

    def tool_change(self, event):
        self.do_tool(self.extrudersel.GetValue())

    def show_viz_window(self, event):
        if self.fgcode:
            self.gwindow.Show(True)
            self.gwindow.SetToolTip(wx.ToolTip("Mousewheel zooms the display\nShift / Mousewheel scrolls layers"))
            self.gwindow.Raise()

    def setfeeds(self, e):
        self.feedrates_changed = True
        try:
            if self.efeedc is not None:
                self.settings._set("e_feedrate", self.efeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("z_feedrate", self.zfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("xy_feedrate", self.xyfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("last_extrusion", self.edist.GetValue())
        except:
            pass

    def homeButtonClicked(self, axis):
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()
        if axis == "x":
            self.onecmd('home X')
        elif axis == "y":  # upper-right
            self.onecmd('home Y')
        elif axis == "z":
            self.onecmd('home Z')
        elif axis == "xy":
            self.onecmd('home XY')
        elif axis == "all":
            self.onecmd('home')
        else:
            return
        self.p.send_now('M114')

    def clamped_move_message(self):
        self.log(_("Manual move outside of the build volume prevented (see the \"Clamp manual moves\" option)."))

    def moveXY(self, x, y):
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()
        if x != 0:
            if self.settings.clamp_jogging:
                new_x = self.current_pos[0] + x
                if new_x < self.build_dimensions_list[3] or new_x > self.build_dimensions_list[0] + self.build_dimensions_list[3]:
                    self.clamped_move_message()
                    return
            self.onecmd('move X %s' % x)
        elif y != 0:
            if self.settings.clamp_jogging:
                new_y = self.current_pos[1] + y
                if new_y < self.build_dimensions_list[4] or new_y > self.build_dimensions_list[1] + self.build_dimensions_list[4]:
                    self.clamped_move_message()
                    return
            self.onecmd('move Y %s' % y)
        else:
            return
        self.p.send_now('M114')

    def moveZ(self, z):
        if z != 0:
            if self.settings.clamp_jogging:
                new_z = self.current_pos[2] + z
                if new_z < self.build_dimensions_list[5] or new_z > self.build_dimensions_list[2] + self.build_dimensions_list[5]:
                    self.clamped_move_message()
                    return
            self.onecmd('move Z %s' % z)
            self.p.send_now('M114')
        # When user clicks on the Z control, the XY control no longer gets spacebar/repeat signals
        self.xyb.clearRepeat()

    def spacebarAction(self):
        self.zb.repeatLast()
        self.xyb.repeatLast()

    #  --------------------------------------------------------------
    #  Console handling
    #  --------------------------------------------------------------

    def catchprint(self, l):
        """Called by the Tee operator to write to the log box"""
        if not self.IsFrozen():
            wx.CallAfter(self.addtexttolog, l)

    def addtexttolog(self, text):
        try:
            self.logbox.AppendText(text)
            max_length = 20000
            current_length = self.logbox.GetLastPosition()
            if current_length > max_length:
                self.logbox.Remove(0, current_length / 10)
        except:
            self.log(_("Attempted to write invalid text to console, which could be due to an invalid baudrate"))

    def clear_log(self, e):
        self.logbox.Clear()

    def set_verbose_communications(self, e):
        self.p.loud = e.IsChecked()

    def parseusercmd(self, line):
        if line.upper().startswith("M114"):
            self.userm114 += 1
        elif line.upper().startswith("M105"):
            self.userm105 += 1

    def sendline(self, e):
        command = self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.addtexttolog, ">>> " + command + "\n")
        self.parseusercmd(str(command))
        self.onecmd(str(command))
        self.commandbox.SetSelection(0, len(command))
        self.commandbox.history.append(command)
        self.commandbox.histindex = len(self.commandbox.history)

    #  --------------------------------------------------------------
    #  Main menu handling & actions
    #  --------------------------------------------------------------

    def create_menu(self):
        """Create main menu"""
        self.menustrip = wx.MenuBar()
        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile, m.Append(-1, _("&Open..."), _(" Open file")))
        self.savebtn = m.Append(-1, _("&Save..."), _(" Save file"))
        self.savebtn.Enable(False)
        self.Bind(wx.EVT_MENU, self.savefile, self.savebtn)

        self.filehistory = wx.FileHistory(maxFiles = 8, idBase = wx.ID_FILE1)
        recent = wx.Menu()
        self.filehistory.UseMenu(recent)
        self.Bind(wx.EVT_MENU_RANGE, self.load_recent_file,
                  id = wx.ID_FILE1, id2 = wx.ID_FILE9)
        m.AppendMenu(wx.ID_ANY, _("&Recent Files"), recent)
        self.Bind(wx.EVT_MENU, self.clear_log, m.Append(-1, _("Clear console"), _(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.on_exit, m.Append(wx.ID_EXIT, _("E&xit"), _(" Closes the Window")))
        self.menustrip.Append(m, _("&File"))

        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1, _("&Edit..."), _(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.plate, m.Append(-1, _("Plater"), _(" Compose 3D models into a single plate")))
        self.Bind(wx.EVT_MENU, self.plate_gcode, m.Append(-1, _("G-Code Plater"), _(" Compose G-Codes into a single plate")))
        self.Bind(wx.EVT_MENU, self.exclude, m.Append(-1, _("Excluder"), _(" Exclude parts of the bed from being printed")))
        self.Bind(wx.EVT_MENU, self.project, m.Append(-1, _("Projector"), _(" Project slices")))
        self.menustrip.Append(m, _("&Tools"))

        m = wx.Menu()
        self.recoverbtn = m.Append(-1, _("Recover"), _(" Recover previous print after a disconnect (homes X, Y, restores Z and E status)"))
        self.recoverbtn.Disable = lambda *a: self.recoverbtn.Enable(False)
        self.Bind(wx.EVT_MENU, self.recover, self.recoverbtn)
        self.menustrip.Append(m, _("&Advanced"))

        if self.settings.slic3rintegration:
            m = wx.Menu()
            print_menu = wx.Menu()
            filament_menu = wx.Menu()
            printer_menu = wx.Menu()
            m.AppendSubMenu(print_menu, _("Print &settings"))
            m.AppendSubMenu(filament_menu, _("&Filament"))
            m.AppendSubMenu(printer_menu, _("&Printer"))
            menus = {"print": print_menu,
                     "filament": filament_menu,
                     "printer": printer_menu}
            try:
                self.load_slic3r_configs(menus)
                self.menustrip.Append(m, _("&Slic3r"))
            except IOError:
                self.logError(_("Failed to load Slic3r configuration:") +
                              "\n" + traceback.format_exc())

        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        m.AppendSubMenu(self.macros_menu, _("&Macros"))
        self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e: PronterOptions(self), m.Append(-1, _("&Options"), _(" Options dialog")))

        self.Bind(wx.EVT_MENU, lambda x: threading.Thread(target = lambda: self.do_slice("set")).start(), m.Append(-1, _("Slicing settings"), _(" Adjust slicing settings")))

        mItem = m.AppendCheckItem(-1, _("Debug communications"),
                                  _("Print all G-code sent to and received from the printer."))
        m.Check(mItem.GetId(), self.p.loud)
        self.Bind(wx.EVT_MENU, self.set_verbose_communications, mItem)

        self.menustrip.Append(m, _("&Settings"))
        self.update_macros_menu()
        self.SetMenuBar(self.menustrip)

        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.about,
                  m.Append(-1, _("&About Printrun"), _("Show about dialog")))
        self.menustrip.Append(m, _("&Help"))

    def project(self, event):
        """Start Projector tool"""
        from printrun import projectlayer
        projectlayer.SettingsFrame(self, self.p).Show()

    def exclude(self, event):
        """Start part excluder tool"""
        if not self.fgcode:
            wx.CallAfter(self.statusbar.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.excluder:
            self.excluder = Excluder()
        self.excluder.pop_window(self.fgcode, bgcolor = self.bgcolor,
                                 build_dimensions = self.build_dimensions_list)

    def about(self, event):
        """Show about dialog"""

        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon(iconfile("pronterface.png"), wx.BITMAP_TYPE_PNG))
        info.SetName('Printrun')
        info.SetVersion(printcore.__version__)

        description = _("Printrun is a pure Python 3D printing"
                        " (and other types of CNC) host software.")

        description += "\n\n" + \
                       _("%.02fmm of filament have been extruded during prints") \
                       % self.settings.total_filament_used

        info.SetDescription(description)
        info.SetCopyright('(C) 2011 - 2014')
        info.SetWebSite('https://github.com/kliment/Printrun')

        licence = """\
Printrun is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Printrun is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
Printrun. If not, see <http://www.gnu.org/licenses/>."""

        info.SetLicence(licence)
        info.AddDeveloper('Kliment Yanev')
        info.AddDeveloper('Guillaume Seguin')

        wx.AboutBox(info)

    #  --------------------------------------------------------------
    #  Settings & command line handling (including update callbacks)
    #  --------------------------------------------------------------

    def _add_settings(self, size):
        self.settings._add(BooleanSetting("monitor", True, _("Monitor printer status"), _("Regularly monitor printer temperatures (required to have functional temperature graph or gauges)"), "Printer"), self.update_monitor)
        self.settings._add(StringSetting("simarrange_path", "", _("Simarrange command"), _("Path to the simarrange binary to use in the STL plater"), "External"))
        self.settings._add(BooleanSetting("circular_bed", False, _("Circular build platform"), _("Draw a circular (or oval) build platform instead of a rectangular one"), "Printer"), self.update_bed_viz)
        self.settings._add(SpinSetting("extruders", 0, 1, 5, _("Extruders count"), _("Number of extruders"), "Printer"))
        self.settings._add(BooleanSetting("clamp_jogging", False, _("Clamp manual moves"), _("Prevent manual moves from leaving the specified build dimensions"), "Printer"))
        self.settings._add(ComboSetting("uimode", "Standard", ["Standard", "Compact", "Tabbed"], _("Interface mode"), _("Standard interface is a one-page, three columns layout with controls/visualization/log\nCompact mode is a one-page, two columns layout with controls + log/visualization\nTabbed mode is a two-pages mode, where the first page shows controls and the second one shows visualization and log."), "UI"), self.reload_ui)
        self.settings._add(ComboSetting("controlsmode", "Standard", ["Standard", "Mini"], _("Controls mode"), _("Standard controls include all controls needed for printer setup and calibration, while Mini controls are limited to the ones needed for daily printing"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("slic3rintegration", False, _("Enable Slic3r integration"), _("Add a menu to select Slic3r profiles directly from Pronterface"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("slic3rupdate", False, _("Update Slic3r default presets"), _("When selecting a profile in Slic3r integration menu, also save it as the default Slic3r preset"), "UI"))
        self.settings._add(ComboSetting("mainviz", "3D", ["2D", "3D", "None"], _("Main visualization"), _("Select visualization for main window."), "Viewer"), self.reload_ui)
        self.settings._add(BooleanSetting("viz3d", False, _("Use 3D in GCode viewer window"), _("Use 3D mode instead of 2D layered mode in the visualization window"), "Viewer"), self.reload_ui)
        self.settings._add(StaticTextSetting("separator_3d_viewer", _("3D viewer options"), "", group = "Viewer"))
        self.settings._add(BooleanSetting("light3d", False, _("Use a lighter 3D visualization"), _("Use a lighter visualization with simple lines instead of extruded paths for 3D viewer"), "Viewer"), self.reload_ui)
        self.settings._add(ComboSetting("antialias3dsamples", "0", ["0", "2", "4", "8"], _("Number of anti-aliasing samples"), _("Amount of anti-aliasing samples used in the 3D viewer"), "Viewer"), self.reload_ui)
        self.settings._add(BooleanSetting("trackcurrentlayer3d", False, _("Track current layer in main 3D view"), _("Track the currently printing layer in the main 3D visualization"), "Viewer"))
        self.settings._add(FloatSpinSetting("gcview_path_width", 0.4, 0.01, 2, _("Extrusion width for 3D viewer"), _("Width of printed path in 3D viewer"), "Viewer", increment = 0.05), self.update_gcview_params)
        self.settings._add(FloatSpinSetting("gcview_path_height", 0.3, 0.01, 2, _("Layer height for 3D viewer"), _("Height of printed path in 3D viewer"), "Viewer", increment = 0.05), self.update_gcview_params)
        self.settings._add(BooleanSetting("tempgraph", True, _("Display temperature graph"), _("Display time-lapse temperature graph"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("tempgauges", False, _("Display temperature gauges"), _("Display graphical gauges for temperatures visualization"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("lockbox", False, _("Display interface lock checkbox"), _("Display a checkbox that, when check, locks most of Pronterface"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("lockonstart", False, _("Lock interface upon print start"), _("If lock checkbox is enabled, lock the interface when starting a print"), "UI"))
        self.settings._add(BooleanSetting("refreshwhenloading", True, _("Update UI during G-Code load"), _("Regularly update visualization during the load of a G-Code file"), "UI"))
        self.settings._add(HiddenSetting("last_window_width", size[0]))
        self.settings._add(HiddenSetting("last_window_height", size[1]))
        self.settings._add(HiddenSetting("last_window_maximized", False))
        self.settings._add(HiddenSetting("last_sash_position", -1))
        self.settings._add(HiddenSetting("last_bed_temperature", 0.0))
        self.settings._add(HiddenSetting("last_file_path", u""))
        self.settings._add(HiddenSetting("last_temperature", 0.0))
        self.settings._add(StaticTextSetting("separator_2d_viewer", _("2D viewer options"), "", group = "Viewer"))
        self.settings._add(FloatSpinSetting("preview_extrusion_width", 0.5, 0, 10, _("Preview extrusion width"), _("Width of Extrusion in Preview"), "Viewer", increment = 0.1), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step1", 10., 0, 200, _("Fine grid spacing"), _("Fine Grid Spacing"), "Viewer"), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step2", 50., 0, 200, _("Coarse grid spacing"), _("Coarse Grid Spacing"), "Viewer"), self.update_gviz_params)
        self.settings._add(StringSetting("bgcolor", "#FFFFFF", _("Background color"), _("Pronterface background color"), "Colors"), self.reload_ui, validate = check_rgb_color)
        self.settings._add(StringSetting("gcview_color_background", "#FAFAC7FF", _("3D view background color"), _("Color of the 3D view background"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_travel", "#99999999", _("3D view travel moves color"), _("Color of travel moves in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_tool0", "#FF000099", _("3D view print moves color"), _("Color of print moves with tool 0 in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_tool1", "#AC0DFF99", _("3D view tool 1 moves color"), _("Color of print moves with tool 1 in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_tool2", "#FFCE0099", _("3D view tool 2 moves color"), _("Color of print moves with tool 2 in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_tool3", "#FF009F99", _("3D view tool 3 moves color"), _("Color of print moves with tool 3 in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_tool4", "#00FF8F99", _("3D view tool 4 moves color"), _("Color of print moves with tool 4 in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_printed", "#33BF0099", _("3D view printed moves color"), _("Color of printed moves in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_current", "#00E5FFCC", _("3D view current layer moves color"), _("Color of moves in current layer in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StringSetting("gcview_color_current_printed", "#196600CC", _("3D view printed current layer moves color"), _("Color of already printed moves from current layer in 3D view"), "Colors"), self.update_gcview_colors, validate = check_rgba_color)
        self.settings._add(StaticTextSetting("note1", _("Note:"), _("Changing some of these settings might require a restart to get effect"), group = "UI"))
        recentfilessetting = StringSetting("recentfiles", "[]")
        recentfilessetting.hidden = True
        self.settings._add(recentfilessetting, self.update_recent_files)

    def add_cmdline_arguments(self, parser):
        pronsole.pronsole.add_cmdline_arguments(self, parser)
        parser.add_argument('-a', '--autoconnect', help = _("automatically try to connect to printer on startup"), action = "store_true")

    def process_cmdline_arguments(self, args):
        pronsole.pronsole.process_cmdline_arguments(self, args)
        self.autoconnect = args.autoconnect

    def update_recent_files(self, param, value):
        if self.filehistory is None:
            return
        recent_files = []
        try:
            recent_files = json.loads(value)
        except:
            self.logError(_("Failed to load recent files list:") +
                          "\n" + traceback.format_exc())
        # Clear history
        while self.filehistory.GetCount():
            self.filehistory.RemoveFileFromHistory(0)
        recent_files.reverse()
        for f in recent_files:
            self.filehistory.AddFileToHistory(f)

    def update_gviz_params(self, param, value):
        params_map = {"preview_extrusion_width": "extrusion_width",
                      "preview_grid_step1": "grid",
                      "preview_grid_step2": "grid"}
        if param not in params_map:
            return
        if not hasattr(self, "gviz"):
            # GUI hasn't been loaded yet, ignore this setting
            return
        trueparam = params_map[param]
        if hasattr(self.gviz, trueparam):
            gviz = self.gviz
        elif hasattr(self.gwindow, "p") and hasattr(self.gwindow.p, trueparam):
            gviz = self.gwindow.p
        else:
            return
        if trueparam == "grid":
            try:
                item = int(param[-1])  # extract list item position
                grid = list(gviz.grid)
                grid[item - 1] = value
                value = tuple(grid)
            except:
                traceback.print_exc()
        if hasattr(self.gviz, trueparam):
            self.apply_gviz_params(self.gviz, trueparam, value)
        if hasattr(self.gwindow, "p") and hasattr(self.gwindow.p, trueparam):
            self.apply_gviz_params(self.gwindow.p, trueparam, value)

    def apply_gviz_params(self, widget, param, value):
        setattr(widget, param, value)
        widget.dirty = 1
        wx.CallAfter(widget.Refresh)

    def update_gcview_colors(self, param, value):
        color = hexcolor_to_float(value, 4)
        # This is sort of a hack: we copy the color values into the preexisting
        # color tuple so that we don't need to update the tuple used by gcview
        target_color = getattr(self, param)
        for i, v in enumerate(color):
            target_color[i] = v
        wx.CallAfter(self.Refresh)

    def update_build_dimensions(self, param, value):
        pronsole.pronsole.update_build_dimensions(self, param, value)
        self.update_bed_viz()

    def update_bed_viz(self, *args):
        """Update bed visualization when size/type changed"""
        if hasattr(self, "gviz") and hasattr(self.gviz, "recreate_platform"):
            self.gviz.recreate_platform(self.build_dimensions_list, self.settings.circular_bed)
        if hasattr(self, "gwindow") and hasattr(self.gwindow, "recreate_platform"):
            self.gwindow.recreate_platform(self.build_dimensions_list, self.settings.circular_bed)

    def update_gcview_params(self, *args):
        need_reload = False
        if hasattr(self, "gviz") and hasattr(self.gviz, "set_gcview_params"):
            need_reload |= self.gviz.set_gcview_params(self.settings.gcview_path_width, self.settings.gcview_path_height)
        if hasattr(self, "gwindow") and hasattr(self.gwindow, "set_gcview_params"):
            need_reload |= self.gwindow.set_gcview_params(self.settings.gcview_path_width, self.settings.gcview_path_height)
        if need_reload:
            self.start_viz_thread()

    def update_monitor(self, *args):
        if hasattr(self, "graph") and self.display_graph:
            if self.settings.monitor:
                wx.CallAfter(self.graph.StartPlotting, 1000)
            else:
                wx.CallAfter(self.graph.StopPlotting)

    #  --------------------------------------------------------------
    #  Statusbar handling
    #  --------------------------------------------------------------

    def statuschecker(self):
        while self.statuscheck:
            string = ""
            if self.sdprinting or self.uploading or self.p.printing:
                secondsremain, secondsestimate, progress = self.get_eta()
                if self.sdprinting or self.uploading:
                    if self.uploading:
                        string += _("SD upload: %04.2f%% |") % (100 * progress,)
                        string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
                    else:
                        string += _("SD printing: %04.2f%% |") % (self.percentdone,)
                elif self.p.printing:
                    string += _("Printing: %04.2f%% |") % (100 * float(self.p.queueindex) / len(self.p.mainqueue),)
                    string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
                if progress > 0:
                    string += _(" Est: %s of %s remaining | ") % (format_duration(secondsremain),
                                                                  format_duration(secondsestimate))
                    string += _(" Z: %.3f mm") % self.curlayer
            elif self.loading_gcode:
                string = self.loading_gcode_message
            wx.CallAfter(self.statusbar.SetStatusText, string)
            wx.CallAfter(self.gviz.Refresh)
            if self.p.online:
                if self.p.writefailures >= 4:
                    self.logError(_("Disconnecting after 4 failed writes."))
                    self.status_thread = None
                    self.disconnect()
                    return
            if self.settings.monitor and self.p.online:
                if self.sdprinting:
                    self.p.send_now("M27")
                if self.m105_waitcycles % 10 == 0:
                    self.p.send_now("M105")
                self.m105_waitcycles += 1
            cur_time = time.time()
            wait_time = 0
            while time.time() < cur_time + self.monitor_interval - 0.25:
                if not self.statuscheck:
                    break
                time.sleep(0.25)
                # Safeguard: if system time changes and goes back in the past,
                # we could get stuck almost forever
                wait_time += 0.25
                if wait_time > self.monitor_interval - 0.25:
                    break
            # Always sleep at least a bit, if something goes wrong with the
            # system time we'll avoid freezing the whole app this way
            time.sleep(0.25)
            try:
                while not self.sentlines.empty():
                    gc = self.sentlines.get_nowait()
                    wx.CallAfter(self.gviz.addgcodehighlight, gc)
                    self.sentlines.task_done()
            except Queue.Empty:
                pass
        wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))

    #  --------------------------------------------------------------
    #  Interface lock handling
    #  --------------------------------------------------------------

    def lock(self, event = None, force = None):
        if force is not None:
            self.locker.SetValue(force)
        if self.locker.GetValue():
            self.log(_("Locking interface."))
            for panel in self.panels:
                panel.Disable()
        else:
            self.log(_("Unlocking interface."))
            for panel in self.panels:
                panel.Enable()

    #  --------------------------------------------------------------
    #  Printer connection handling
    #  --------------------------------------------------------------

    def connect(self, event = None):
        self.log(_("Connecting..."))
        port = None
        if self.serialport.GetValue():
            port = str(self.serialport.GetValue())
        else:
            scanned = self.scanserial()
            if scanned:
                port = scanned[0]
        baud = 115200
        try:
            baud = int(self.baud.GetValue())
        except:
            self.logError(_("Could not parse baud rate: "))
            traceback.print_exc(file = sys.stdout)
        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            wx.CallAfter(self.toolbarsizer.Layout)
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        if not self.connect_to_printer(port, baud):
            return
        self.statuscheck = True
        if port != self.settings.port:
            self.set("port", port)
        if baud != self.settings.baudrate:
            self.set("baudrate", str(baud))
        self.status_thread = threading.Thread(target = self.statuschecker)
        self.status_thread.start()
        if self.predisconnect_mainqueue:
            self.recoverbtn.Enable()

    def store_predisconnect_state(self):
        self.predisconnect_mainqueue = self.p.mainqueue
        self.predisconnect_queueindex = self.p.queueindex
        self.predisconnect_layer = self.curlayer

    def disconnect(self, event = None):
        self.log(_("Disconnected."))
        if self.p.printing or self.p.paused or self.paused:
            self.store_predisconnect_state()
        self.p.disconnect()
        self.statuscheck = False
        if self.status_thread:
            self.status_thread.join()
            self.status_thread = None

        wx.CallAfter(self.connectbtn.SetLabel, _("Connect"))
        wx.CallAfter(self.connectbtn.SetToolTip, wx.ToolTip(_("Connect to the printer")))
        wx.CallAfter(self.connectbtn.Bind, wx.EVT_BUTTON, self.connect)

        wx.CallAfter(self.gui_set_disconnected)

        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")

        # Relayout the toolbar to handle new buttons size
        wx.CallAfter(self.toolbarsizer.Layout)

    def reset(self, event):
        self.log(_("Reset."))
        dlg = wx.MessageDialog(self, _("Are you sure you want to reset the printer?"), _("Reset?"), wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.p.reset()
            self.sethotendgui(0)
            self.setbedgui(0)
            self.p.printing = 0
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            if self.paused:
                self.p.paused = 0
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                self.paused = 0
            wx.CallAfter(self.toolbarsizer.Layout)
        dlg.Destroy()

    #  --------------------------------------------------------------
    #  Print/upload handling
    #  --------------------------------------------------------------

    def on_startprint(self):
        wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
        wx.CallAfter(self.pausebtn.Enable)
        wx.CallAfter(self.printbtn.SetLabel, _("Restart"))
        wx.CallAfter(self.toolbarsizer.Layout)

    def printfile(self, event):
        self.extra_print_time = 0
        if self.paused:
            self.p.paused = 0
            self.paused = 0
            if self.sdprinting:
                self.on_startprint()
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return

        if not self.fgcode:
            wx.CallAfter(self.statusbar.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.p.online:
            wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))
            return
        self.on_startprint()
        self.p.startprint(self.fgcode)

    def sdprintfile(self, event):
        self.extra_print_time = 0
        self.on_startprint()
        threading.Thread(target = self.getfiles).start()

    def upload(self, event):
        if not self.fgcode:
            return
        if not self.p.online:
            return
        dlg = wx.TextEntryDialog(self, ("Enter a target filename in 8.3 format:"), _("Pick SD filename"), dosify(self.filename))
        if dlg.ShowModal() == wx.ID_OK:
            self.p.send_now("M21")
            self.p.send_now("M28 " + str(dlg.GetValue()))
            self.recvlisteners.append(self.uploadtrigger)
        dlg.Destroy()

    def uploadtrigger(self, l):
        if "Writing to file" in l:
            self.uploading = True
            self.p.startprint(self.fgcode)
            self.p.endcb = self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)

    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.statusbar.SetStatusText, _("File upload complete"))
        time.sleep(0.5)
        self.p.clear = True
        self.uploading = False

    def pause(self, event):
        if not self.paused:
            self.log(_("Print paused at: %s") % format_time(time.time()))
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if not self.p.printing:
                    return
                self.p.pause()
                self.p.runSmallScript(self.pauseScript)
            self.paused = True
            # self.p.runSmallScript(self.pauseScript)
            self.extra_print_time += int(time.time() - self.starttime)
            wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
            wx.CallAfter(self.toolbarsizer.Layout)
        else:
            self.log(_("Resuming."))
            self.paused = False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.toolbarsizer.Layout)

    def recover(self, event):
        self.extra_print_time = 0
        if not self.p.online:
            wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))
            return
        # Reset Z
        self.p.send_now("G92 Z%f" % self.predisconnect_layer)
        # Home X and Y
        self.p.send_now("G28 X Y")
        self.on_startprint()
        self.p.startprint(self.predisconnect_mainqueue, self.p.queueindex)

    #  --------------------------------------------------------------
    #  File loading handling
    #  --------------------------------------------------------------

    def filesloaded(self):
        dlg = wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
        if dlg.ShowModal() == wx.ID_OK:
            target = dlg.GetStringSelection()
            if len(target):
                self.recvlisteners.append(self.waitforsdresponse)
                self.p.send_now("M23 " + target.lower())
        dlg.Destroy()
        # print self.sdfiles

    def getfiles(self):
        if not self.p.online:
            self.sdfiles = []
            return
        self.listing = 0
        self.sdfiles = []
        self.recvlisteners.append(self.listfiles)
        self.p.send_now("M21")
        self.p.send_now("M20")

    def model_to_gcode_filename(self, filename):
        suffix = "_export.gcode"
        for ext in [".stl", ".obj"]:
            filename = filename.replace(ext, suffix)
            filename = filename.replace(ext.upper(), suffix)
        return filename

    def slice_func(self):
        try:
            output_filename = self.model_to_gcode_filename(self.filename)
            pararray = prepare_command(self.settings.slicecommand,
                                       {"$s": self.filename, "$o": output_filename})
            if self.settings.slic3rintegration:
                for cat, config in self.slic3r_configs.items():
                    if config:
                        fpath = os.path.join(self.slic3r_configpath, cat, config)
                        pararray += ["--load", fpath]
            self.log(_("Running ") + " ".join(pararray))
            self.slicep = subprocess.Popen(pararray, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
            while True:
                o = self.slicep.stdout.read(1)
                if o == '' and self.slicep.poll() is not None: break
                sys.stdout.write(o)
            self.slicep.wait()
            self.stopsf = 1
        except:
            logging.error(_("Failed to execute slicing software: "))
            self.stopsf = 1
            traceback.print_exc(file = sys.stdout)

    def slice_monitor(self):
        while not self.stopsf:
            try:
                wx.CallAfter(self.statusbar.SetStatusText, _("Slicing..."))  # +self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn = self.filename
        try:
            self.load_gcode_async(self.model_to_gcode_filename(self.filename))
        except:
            self.filename = fn
        self.slicing = False
        self.slicep = None

    def slice(self, filename):
        wx.CallAfter(self.loadbtn.SetLabel, _("Cancel"))
        wx.CallAfter(self.toolbarsizer.Layout)
        self.log(_("Slicing ") + filename)
        self.cout = StringIO.StringIO()
        self.filename = filename
        self.stopsf = 0
        self.slicing = True
        threading.Thread(target = self.slice_func).start()
        threading.Thread(target = self.slice_monitor).start()

    def cmdline_filename_callback(self, filename):
        # Do nothing when processing a filename from command line, as we'll
        # handle it when everything has been prepared
        self.filename = filename

    def do_load(self, l):
        if hasattr(self, 'slicing'):
            self.loadfile(None, l)
        else:
            self._do_load(l)

    def load_recent_file(self, event):
        fileid = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileid)
        self.loadfile(None, filename = path)

    def loadfile(self, event, filename = None):
        if self.slicing and self.slicep is not None:
            self.slicep.terminate()
            return
        basedir = self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir = os.path.split(self.filename)[0]
            except:
                pass
        dlg = None
        if filename is None:
            dlg = wx.FileDialog(self, _("Open file to print"), basedir, style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
        if filename or dlg.ShowModal() == wx.ID_OK:
            if filename:
                name = filename
            else:
                name = dlg.GetPath()
                dlg.Destroy()
            if not os.path.exists(name):
                self.statusbar.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path", path)
            try:
                abspath = os.path.abspath(name)
                recent_files = []
                try:
                    recent_files = json.loads(self.settings.recentfiles)
                except:
                    self.logError(_("Failed to load recent files list:") +
                                  "\n" + traceback.format_exc())
                if abspath in recent_files:
                    recent_files.remove(abspath)
                recent_files.insert(0, abspath)
                if len(recent_files) > 5:
                    recent_files = recent_files[:5]
                self.set("recentfiles", json.dumps(recent_files))
            except:
                self.logError(_("Could not update recent files list:") +
                              "\n" + traceback.format_exc())
            if name.lower().endswith(".stl") or name.lower().endswith(".obj"):
                self.slice(name)
            else:
                self.load_gcode_async(name)
        else:
            dlg.Destroy()

    def load_gcode_async(self, filename):
        self.filename = filename
        gcode = self.pre_gcode_load()
        threading.Thread(target = self.load_gcode_async_thread, args = (gcode,)).start()

    def load_gcode_async_thread(self, gcode):
        try:
            self.load_gcode(self.filename,
                            layer_callback = self.layer_ready_cb,
                            gcode = gcode)
        except PronterfaceQuitException:
            return
        wx.CallAfter(self.post_gcode_load)

    def layer_ready_cb(self, gcode, layer):
        global pronterface_quitting
        if pronterface_quitting:
            raise PronterfaceQuitException
        if not self.settings.refreshwhenloading:
            return
        self.viz_last_layer = layer
        if time.time() - self.viz_last_yield > 1.0:
            time.sleep(0.2)
            self.loading_gcode_message = _("Loading %s: %d layers loaded (%d lines)") % (self.filename, layer + 1, len(gcode))
            self.viz_last_yield = time.time()
            wx.CallAfter(self.statusbar.SetStatusText, self.loading_gcode_message)

    def start_viz_thread(self, gcode = None):
        threading.Thread(target = self.loadviz, args = (gcode,)).start()

    def pre_gcode_load(self):
        self.loading_gcode = True
        self.loading_gcode_message = _("Loading %s") % self.filename
        gcode = gcoder.GCode(deferred = True)
        self.viz_last_yield = 0
        self.viz_last_layer = -1
        self.start_viz_thread(gcode)
        return gcode

    def post_gcode_load(self, print_stats = True):
        # Must be called in wx.CallAfter for safety
        self.loading_gcode = False
        message = _("Loaded %s, %d lines") % (self.filename, len(self.fgcode),)
        self.log(message)
        self.statusbar.SetStatusText(message)
        self.savebtn.Enable(True)
        self.loadbtn.SetLabel(_("Load File"))
        self.printbtn.SetLabel(_("Print"))
        self.pausebtn.SetLabel(_("Pause"))
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        if self.p.online:
            self.printbtn.Enable()
        self.toolbarsizer.Layout()
        self.viz_last_layer = None
        if print_stats:
            self.output_gcode_stats()

    def output_gcode_stats(self):
        gcode = self.fgcode
        self.log(_("%.2fmm of filament used in this print") % gcode.filament_length)
        self.log(_("The print goes:"))
        self.log(_("- from %.2f mm to %.2f mm in X and is %.2f mm wide") % (gcode.xmin, gcode.xmax, gcode.width))
        self.log(_("- from %.2f mm to %.2f mm in Y and is %.2f mm deep") % (gcode.ymin, gcode.ymax, gcode.depth))
        self.log(_("- from %.2f mm to %.2f mm in Z and is %.2f mm high") % (gcode.zmin, gcode.zmax, gcode.height))
        self.log(_("Estimated duration: %d layers, %s") % gcode.estimate_duration())

    def loadviz(self, gcode = None):
        self.gviz.clear()
        self.gwindow.p.clear()
        if gcode is not None:
            generator = self.gviz.addfile_perlayer(gcode, True)
            next_layer = 0
            # Progressive loading of visualization
            # We load layers up to the last one which has been processed in GCoder
            # (self.viz_last_layer)
            # Once the GCode has been entirely loaded, this variable becomes None,
            # indicating that we can do the last generator call to finish the
            # loading of the visualization, which will itself return None.
            # During preloading we verify that the layer we added is the one we
            # expected through the assert call.
            while True:
                global pronterface_quitting
                if pronterface_quitting:
                    return
                max_layer = self.viz_last_layer
                if max_layer is None:
                    break
                while next_layer <= max_layer:
                    assert(generator.next() == next_layer)
                    next_layer += 1
                time.sleep(0.1)
            generator_output = generator.next()
            while generator_output is not None:
                assert(generator_output in (None, next_layer))
                next_layer += 1
                generator_output = generator.next()
        else:
            # If GCode is not being loaded asynchroneously, it is already
            # loaded, so let's make visualization sequentially
            gcode = self.fgcode
            self.gviz.addfile(gcode)
        wx.CallAfter(self.gviz.Refresh)
        # Load external window sequentially now that everything is ready.
        # We can't really do any better as the 3D viewer might clone the
        # finalized model from the main visualization
        self.gwindow.p.addfile(gcode)

    #  --------------------------------------------------------------
    #  File saving handling
    #  --------------------------------------------------------------

    def savefile(self, event):
        basedir = self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir = os.path.split(self.filename)[0]
            except:
                pass
        dlg = wx.FileDialog(self, _("Save as"), basedir, style = wx.FD_SAVE)
        dlg.SetWildcard(_("GCODE files (*.gcode;*.gco;*.g)|*.gcode;*.gco;*.g|All Files (*.*)|*.*"))
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            open(name, "w").write("\n".join((line.raw for line in self.fgcode)))
            self.log(_("G-Code succesfully saved to %s") % name)
        dlg.Destroy()

    #  --------------------------------------------------------------
    #  Printcore callbacks
    #  --------------------------------------------------------------

    def process_host_command(self, command):
        """Override host command handling"""
        command = command.lstrip()
        if command.startswith(";@pause"):
            self.pause(None)
        else:
            pronsole.pronsole.process_host_command(self, command)

    def startcb(self, resuming = False):
        """Callback on print start"""
        pronsole.pronsole.startcb(self, resuming)
        if self.settings.lockbox and self.settings.lockonstart:
            wx.CallAfter(self.lock, force = True)

    def endcb(self):
        """Callback on print end/pause"""
        pronsole.pronsole.endcb(self)
        if self.p.queueindex == 0:
            self.p.runSmallScript(self.endScript)
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            wx.CallAfter(self.toolbarsizer.Layout)

    def online(self):
        """Callback when printer goes online"""
        self.log(_("Printer is now online."))
        wx.CallAfter(self.online_gui)

    def online_gui(self):
        """Callback when printer goes online (graphical bits)"""
        self.connectbtn.SetLabel(_("Disconnect"))
        self.connectbtn.SetToolTip(wx.ToolTip("Disconnect from the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON, self.disconnect)

        if hasattr(self, "extrudersel"):
            self.do_tool(self.extrudersel.GetValue())

        self.gui_set_connected()

        if self.filename:
            self.printbtn.Enable()

        wx.CallAfter(self.toolbarsizer.Layout)

    def sentcb(self, line, gline):
        """Callback when a printer gcode has been sent"""
        if not gline:
            pass
        elif gline.command in ["M104", "M109"]:
            gline_s = gcoder.S(gline)
            if gline_s is not None:
                temp = gline_s
                if self.display_gauges: wx.CallAfter(self.hottgauge.SetTarget, temp)
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, temp)
        elif gline.command in ["M140", "M190"]:
            gline_s = gcoder.S(gline)
            if gline_s is not None:
                temp = gline_s
                if self.display_gauges: wx.CallAfter(self.bedtgauge.SetTarget, temp)
                if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, temp)
        elif gline.command.startswith("T"):
            tool = gline.command[1:]
            if hasattr(self, "extrudersel"): wx.CallAfter(self.extrudersel.SetValue, tool)
        self.sentlines.put_nowait(line)

    def is_excluded_move(self, gline):
        """Check whether the given moves ends at a position specified as
        excluded in the part excluder"""
        if not gline.is_move or not self.excluder or not self.excluder.rectangles:
            return False
        for (x0, y0, x1, y1) in self.excluder.rectangles:
            if x0 <= gline.current_x <= x1 and y0 <= gline.current_y <= y1:
                return True
        return False

    def preprintsendcb(self, gline, next_gline):
        """Callback when a printer gcode is about to be sent. We use it to
        exclude moves defined by the part excluder tool"""
        if not self.is_excluded_move(gline):
            return gline
        else:
            if gline.z is not None:
                if gline.relative:
                    if self.excluder_z_abs is not None:
                        self.excluder_z_abs += gline.z
                    elif self.excluder_z_rel is not None:
                        self.excluder_z_rel += gline.z
                    else:
                        self.excluder_z_rel = gline.z
                else:
                    self.excluder_z_rel = None
                    self.excluder_z_abs = gline.z
            if gline.e is not None and not gline.relative_e:
                self.excluder_e = gline.e
            # If next move won't be excluded, push the changes we have to do
            if next_gline is not None and not self.is_excluded_move(next_gline):
                if self.excluder_e is not None:
                    self.p.send_now("G92 E%.5f" % self.excluder_e)
                    self.excluder_e = None
                if self.excluder_z_abs is not None:
                    if gline.relative:
                        self.p.send_now("G90")
                    self.p.send_now("G1 Z%.5f" % self.excluder_z_abs)
                    self.excluder_z_abs = None
                    if gline.relative:
                        self.p.send_now("G91")
                if self.excluder_z_rel is not None:
                    if not gline.relative:
                        self.p.send_now("G91")
                    self.p.send_now("G1 Z%.5f" % self.excluder_z_rel)
                    self.excluder_z_rel = None
                    if not gline.relative:
                        self.p.send_now("G90")
                return None

    def printsentcb(self, gline):
        """Callback when a print gcode has been sent"""
        if gline.is_move:
            if hasattr(self.gwindow, "set_current_gline"):
                wx.CallAfter(self.gwindow.set_current_gline, gline)
            if hasattr(self.gviz, "set_current_gline"):
                wx.CallAfter(self.gviz.set_current_gline, gline)

    def layer_change_cb(self, newlayer):
        """Callback when the printed layer changed"""
        pronsole.pronsole.layer_change_cb(self, newlayer)
        layerz = self.fgcode.all_layers[newlayer].z
        if layerz is not None:
            self.curlayer = layerz
        if self.settings.mainviz != "3D" or self.settings.trackcurrentlayer3d:
            wx.CallAfter(self.gviz.setlayer, newlayer)

    def update_tempdisplay(self):
        try:
            temps = parse_temperature_report(self.tempreport)
            if "T0" in temps and temps["T0"][0]:
                hotend_temp = float(temps["T0"][0])
            elif "T" in temps and temps["T"][0]:
                hotend_temp = float(temps["T"][0])
            else:
                hotend_temp = None
            if hotend_temp is not None:
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder0Temperature, hotend_temp)
                if self.display_gauges: wx.CallAfter(self.hottgauge.SetValue, hotend_temp)
                setpoint = None
                if "T0" in temps and temps["T0"][1]: setpoint = float(temps["T0"][1])
                elif temps["T"][1]: setpoint = float(temps["T"][1])
                if setpoint is not None:
                    if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, setpoint)
                    if self.display_gauges: wx.CallAfter(self.hottgauge.SetTarget, setpoint)
            if "T1" in temps:
                hotend_temp = float(temps["T1"][0])
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder1Temperature, hotend_temp)
                setpoint = temps["T1"][1]
                if setpoint and self.display_graph:
                    wx.CallAfter(self.graph.SetExtruder1TargetTemperature, float(setpoint))
            bed_temp = float(temps["B"][0]) if "B" in temps and temps["B"][0] else None
            if bed_temp is not None:
                if self.display_graph: wx.CallAfter(self.graph.SetBedTemperature, bed_temp)
                if self.display_gauges: wx.CallAfter(self.bedtgauge.SetValue, bed_temp)
                setpoint = temps["B"][1]
                if setpoint:
                    setpoint = float(setpoint)
                    if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, setpoint)
                    if self.display_gauges: wx.CallAfter(self.bedtgauge.SetTarget, setpoint)
        except:
            traceback.print_exc()

    def update_pos(self, l):
        bits = gcoder.m114_exp.findall(l)
        x = None
        y = None
        z = None
        for bit in bits:
            if not bit[0]: continue
            if x is None and bit[0] == "X":
                x = float(bit[1])
            elif y is None and bit[0] == "Y":
                y = float(bit[1])
            elif z is None and bit[0] == "Z":
                z = float(bit[1])
        if x is not None: self.current_pos[0] = x
        if y is not None: self.current_pos[1] = y
        if z is not None: self.current_pos[2] = z

    def recvcb(self, l):
        isreport = False
        if "ok C:" in l or "Count" in l \
           or ("X:" in l and len(gcoder.m114_exp.findall(l)) == 6):
            self.posreport = l
            self.update_pos(l)
            if self.userm114 > 0:
                self.userm114 -= 1
            else:
                isreport = True
        if "ok T:" in l or tempreading_exp.findall(l):
            self.tempreport = l
            wx.CallAfter(self.tempdisp.SetLabel, self.tempreport.strip().replace("ok ", ""))
            self.update_tempdisplay()
            if self.userm105 > 0:
                self.userm105 -= 1
            else:
                self.m105_waitcycles = 0
                isreport = True
        tstring = l.rstrip()
        if not self.p.loud and (tstring not in ["ok", "wait"] and not isreport):
            wx.CallAfter(self.addtexttolog, tstring + "\n")
        for listener in self.recvlisteners:
            listener(l)

    def listfiles(self, line, ignored = False):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles.append(line.strip().lower())

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
        if "File selected" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Starting print"))
            self.sdprinting = 1
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
            return
        if "SD printing byte" in l:
            # M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0 * int(vals[0]) / int(vals[1])
            except:
                pass

    #  --------------------------------------------------------------
    #  Custom buttons handling
    #  --------------------------------------------------------------

    def cbuttons_reload(self):
        allcbs = getattr(self, "custombuttons_widgets", [])
        for button in allcbs:
            self.cbuttonssizer.Detach(button)
            button.Destroy()
        self.custombuttons_widgets = []
        custombuttons = self.custombuttons[:] + [None]
        for i, btndef in enumerate(custombuttons):
            if btndef is None:
                if i == len(custombuttons) - 1:
                    self.newbuttonbutton = b = wx.Button(self.centerpanel, -1, "+", size = (19, 18), style = wx.BU_EXACTFIT)
                    # b.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    b.SetForegroundColour("#4444ff")
                    b.SetToolTip(wx.ToolTip(_("click to add new custom button")))
                    b.Bind(wx.EVT_BUTTON, self.cbutton_edit)
                else:
                    b = wx.StaticText(self.panel, -1, "")
            else:
                b = wx.Button(self.centerpanel, -1, btndef.label, style = wx.BU_EXACTFIT)
                b.SetToolTip(wx.ToolTip(_("Execute command: ") + btndef.command))
                if btndef.background:
                    b.SetBackgroundColour(btndef.background)
                    rr, gg, bb = b.GetBackgroundColour().Get()
                    if 0.3 * rr + 0.59 * gg + 0.11 * bb < 60:
                        b.SetForegroundColour("#ffffff")
                b.custombutton = i
                b.properties = btndef
            if btndef is not None:
                b.Bind(wx.EVT_BUTTON, self.process_button)
                b.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
            self.custombuttons_widgets.append(b)
            if type(self.cbuttonssizer) == wx.GridBagSizer:
                self.cbuttonssizer.Add(b, pos = (i // 4, i % 4), flag = wx.EXPAND)
            else:
                self.cbuttonssizer.Add(b, flag = wx.EXPAND)
        self.centerpanel.Layout()
        self.centerpanel.GetContainingSizer().Layout()

    def help_button(self):
        self.log(_('Defines custom button. Usage: button <num> "title" [/c "colour"] command'))

    def do_button(self, argstr):
        def nextarg(rest):
            rest = rest.lstrip()
            if rest.startswith('"'):
                return rest[1:].split('"', 1)
            else:
                return rest.split(None, 1)
        # try:
        num, argstr = nextarg(argstr)
        num = int(num)
        title, argstr = nextarg(argstr)
        colour = None
        try:
            c1, c2 = nextarg(argstr)
            if c1 == "/c":
                colour, argstr = nextarg(c2)
        except:
            pass
        command = argstr.strip()
        if num < 0 or num >= 64:
            self.log(_("Custom button number should be between 0 and 63"))
            return
        while num >= len(self.custombuttons):
            self.custombuttons.append(None)
        self.custombuttons[num] = SpecialButton(title, command)
        if colour is not None:
            self.custombuttons[num].background = colour
        if not self.processing_rc:
            self.cbuttons_reload()
        # except Exception, x:
        #    print "Bad syntax for button definition, see 'help button'"
        #    print x

    def cbutton_save(self, n, bdef, new_n = None):
        if new_n is None: new_n = n
        if bdef is None or bdef == "":
            self.save_in_rc(("button %d" % n), '')
        elif bdef.background:
            colour = bdef.background
            if type(colour) not in (str, unicode):
                # print type(colour), map(type, colour)
                if type(colour) == tuple and tuple(map(type, colour)) == (int, int, int):
                    colour = map(lambda x: x % 256, colour)
                    colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                else:
                    colour = wx.Colour(colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
            self.save_in_rc(("button %d" % n), 'button %d "%s" /c "%s" %s' % (new_n, bdef.label, colour, bdef.command))
        else:
            self.save_in_rc(("button %d" % n), 'button %d "%s" %s' % (new_n, bdef.label, bdef.command))

    def cbutton_edit(self, e, button = None):
        bedit = ButtonEdit(self)
        if button is not None:
            n = button.custombutton
            bedit.name.SetValue(button.properties.label)
            bedit.command.SetValue(button.properties.command)
            if button.properties.background:
                colour = button.properties.background
                if type(colour) not in (str, unicode):
                    # print type(colour)
                    if type(colour) == tuple and tuple(map(type, colour)) == (int, int, int):
                        colour = map(lambda x: x % 256, colour)
                        colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                    else:
                        colour = wx.Colour(colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                bedit.color.SetValue(colour)
        else:
            n = len(self.custombuttons)
            while n > 0 and self.custombuttons[n - 1] is None:
                n -= 1
        if bedit.ShowModal() == wx.ID_OK:
            if n == len(self.custombuttons):
                self.custombuttons.append(None)
            self.custombuttons[n] = SpecialButton(bedit.name.GetValue().strip(), bedit.command.GetValue().strip(), custom = True)
            if bedit.color.GetValue().strip() != "":
                self.custombuttons[n].background = bedit.color.GetValue()
            self.cbutton_save(n, self.custombuttons[n])
        wx.CallAfter(bedit.Destroy)
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_remove(self, e, button):
        n = button.custombutton
        self.cbutton_save(n, None)
        del self.custombuttons[n]
        for i in range(n, len(self.custombuttons)):
            self.cbutton_save(i, self.custombuttons[i])
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_order(self, e, button, dir):
        n = button.custombutton
        if dir < 0:
            n = n - 1
        if n + 1 >= len(self.custombuttons):
            self.custombuttons.append(None)  # pad
        # swap
        self.custombuttons[n], self.custombuttons[n + 1] = self.custombuttons[n + 1], self.custombuttons[n]
        self.cbutton_save(n, self.custombuttons[n])
        self.cbutton_save(n + 1, self.custombuttons[n + 1])
        # if self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        wx.CallAfter(self.cbuttons_reload)

    def editbutton(self, e):
        if e.IsCommandEvent() or e.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if e.IsCommandEvent():
                pos = (0, 0)
            else:
                pos = e.GetPosition()
            popupmenu = wx.Menu()
            obj = e.GetEventObject()
            if hasattr(obj, "custombutton"):
                item = popupmenu.Append(-1, _("Edit custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_edit(e, button), item)
                item = popupmenu.Append(-1, _("Move left <<"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_order(e, button, -1), item)
                if obj.custombutton == 0: item.Enable(False)
                item = popupmenu.Append(-1, _("Move right >>"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_order(e, button, 1), item)
                if obj.custombutton == 63: item.Enable(False)
                pos = self.panel.ScreenToClient(e.GetEventObject().ClientToScreen(pos))
                item = popupmenu.Append(-1, _("Remove custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_remove(e, button), item)
            else:
                item = popupmenu.Append(-1, _("Add custom button"))
                self.Bind(wx.EVT_MENU, self.cbutton_edit, item)
            self.panel.PopupMenu(popupmenu, pos)
        elif e.Dragging() and e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            if not hasattr(self, "dragpos"):
                self.dragpos = scrpos
                e.Skip()
                return
            else:
                dx, dy = self.dragpos[0] - scrpos[0], self.dragpos[1] - scrpos[1]
                if dx * dx + dy * dy < 5 * 5:  # threshold to detect dragging for jittery mice
                    e.Skip()
                    return
            if not hasattr(self, "dragging"):
                # init dragging of the custom button
                if hasattr(obj, "custombutton") and obj.properties is not None:
                    # self.newbuttonbutton.SetLabel("")
                    # self.newbuttonbutton.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                    # self.newbuttonbutton.SetForegroundColour("black")
                    # self.newbuttonbutton.SetSize(obj.GetSize())
                    # if self.toolbarsizer.GetItem(self.newbuttonbutton) is not None:
                    #    self.toolbarsizer.SetItemMinSize(self.newbuttonbutton, obj.GetSize())
                    #    self.mainsizer.Layout()
                    for b in self.custombuttons_widgets:
                        # if b.IsFrozen(): b.Thaw()
                        if b.properties is None:
                            b.Enable()
                            b.SetLabel("")
                            b.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            b.SetForegroundColour("black")
                            b.SetSize(obj.GetSize())
                            if self.toolbarsizer.GetItem(b) is not None:
                                self.toolbarsizer.SetItemMinSize(b, obj.GetSize())
                                self.mainsizer.Layout()
                        #    b.SetStyle(wx.ALIGN_CENTRE+wx.ST_NO_AUTORESIZE+wx.SIMPLE_BORDER)
                    self.dragging = wx.Button(self.panel, -1, obj.GetLabel(), style = wx.BU_EXACTFIT)
                    self.dragging.SetBackgroundColour(obj.GetBackgroundColour())
                    self.dragging.SetForegroundColour(obj.GetForegroundColour())
                    self.dragging.sourcebutton = obj
                    self.dragging.Raise()
                    self.dragging.Disable()
                    self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                    self.last_drag_dest = obj
                    self.dragging.label = obj.s_label = obj.GetLabel()
                    self.dragging.bgc = obj.s_bgc = obj.GetBackgroundColour()
                    self.dragging.fgc = obj.s_fgc = obj.GetForegroundColour()
            else:
                # dragging in progress
                self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                wx.CallAfter(self.dragging.Refresh)
                dst = None
                src = self.dragging.sourcebutton
                drg = self.dragging
                for b in self.custombuttons_widgets:
                    if b.GetScreenRect().Contains(scrpos):
                        dst = b
                        break
                # if dst is None and self.panel.GetScreenRect().Contains(scrpos):
                #    # try to check if it is after buttons at the end
                #    tspos = self.panel.ClientToScreen(self.toolbarsizer.GetPosition())
                #    bspos = self.panel.ClientToScreen(self.cbuttonssizer.GetPosition())
                #    tsrect = wx.Rect(*(tspos.Get()+self.toolbarsizer.GetSize().Get()))
                #    bsrect = wx.Rect(*(bspos.Get()+self.cbuttonssizer.GetSize().Get()))
                #    lbrect = btns[-1].GetScreenRect()
                #    p = scrpos.Get()
                #    if len(btns)<4 and tsrect.Contains(scrpos):
                #        if lbrect.GetRight() < p[0]:
                #            print "Right of last button on upper cb sizer"
                #    if bsrect.Contains(scrpos):
                #        if lbrect.GetBottom() < p[1]:
                #            print "Below last button on lower cb sizer"
                #        if lbrect.GetRight() < p[0] and lbrect.GetTop() <= p[1] and lbrect.GetBottom() >= p[1]:
                #            print "Right to last button on lower cb sizer"
                if dst is not self.last_drag_dest:
                    if self.last_drag_dest is not None:
                        self.last_drag_dest.SetBackgroundColour(self.last_drag_dest.s_bgc)
                        self.last_drag_dest.SetForegroundColour(self.last_drag_dest.s_fgc)
                        self.last_drag_dest.SetLabel(self.last_drag_dest.s_label)
                    if dst is not None and dst is not src:
                        dst.s_bgc = dst.GetBackgroundColour()
                        dst.s_fgc = dst.GetForegroundColour()
                        dst.s_label = dst.GetLabel()
                        src.SetBackgroundColour(dst.GetBackgroundColour())
                        src.SetForegroundColour(dst.GetForegroundColour())
                        src.SetLabel(dst.GetLabel())
                        dst.SetBackgroundColour(drg.bgc)
                        dst.SetForegroundColour(drg.fgc)
                        dst.SetLabel(drg.label)
                    else:
                        src.SetBackgroundColour(drg.bgc)
                        src.SetForegroundColour(drg.fgc)
                        src.SetLabel(drg.label)
                    self.last_drag_dest = dst
        elif hasattr(self, "dragging") and not e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            # dragging finished
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            dst = None
            src = self.dragging.sourcebutton
            drg = self.dragging
            for b in self.custombuttons_widgets:
                if b.GetScreenRect().Contains(scrpos):
                    dst = b
                    break
            if dst is not None:
                src_i = src.custombutton
                dst_i = dst.custombutton
                self.custombuttons[src_i], self.custombuttons[dst_i] = self.custombuttons[dst_i], self.custombuttons[src_i]
                self.cbutton_save(src_i, self.custombuttons[src_i])
                self.cbutton_save(dst_i, self.custombuttons[dst_i])
                while self.custombuttons[-1] is None:
                    del self.custombuttons[-1]
            wx.CallAfter(self.dragging.Destroy)
            del self.dragging
            wx.CallAfter(self.cbuttons_reload)
            del self.last_drag_dest
            del self.dragpos
        else:
            e.Skip()

    def process_button(self, e):
        try:
            if hasattr(e.GetEventObject(), "custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button = e.GetEventObject().custombutton
            command = e.GetEventObject().properties.command
            self.parseusercmd(command)
            self.onecmd(command)
            self.cur_button = None
        except:
            self.log(_("Failed to handle button"))
            self.cur_button = None
            raise

    #  --------------------------------------------------------------
    #  Macros handling
    #  --------------------------------------------------------------

    def start_macro(self, macro_name, old_macro_definition = ""):
        if not self.processing_rc:
            def cb(definition):
                if len(definition.strip()) == 0:
                    if old_macro_definition != "":
                        dialog = wx.MessageDialog(self, _("Do you want to erase the macro?"), style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                        if dialog.ShowModal() == wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    self.log(_("Cancelled."))
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            MacroEditor(macro_name, old_macro_definition, cb)
        else:
            pronsole.pronsole.start_macro(self, macro_name, old_macro_definition)

    def end_macro(self):
        pronsole.pronsole.end_macro(self)
        self.update_macros_menu()

    def delete_macro(self, macro_name):
        pronsole.pronsole.delete_macro(self, macro_name)
        self.update_macros_menu()

    def new_macro(self, e = None):
        dialog = wx.Dialog(self, -1, _("Enter macro name"), size = (260, 85))
        panel = wx.Panel(dialog, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        wx.StaticText(panel, -1, _("Macro name:"), (8, 14))
        dialog.namectrl = wx.TextCtrl(panel, -1, '', (110, 8), size = (130, 24), style = wx.TE_PROCESS_ENTER)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(dialog, wx.ID_OK, _("Ok"), size = (60, 24))
        dialog.Bind(wx.EVT_TEXT_ENTER, lambda e: dialog.EndModal(wx.ID_OK), dialog.namectrl)
        # dialog.Bind(wx.EVT_BUTTON, lambda e:self.new_macro_named(dialog, e), okb)
        hbox.Add(okb)
        hbox.Add(wx.Button(dialog, wx.ID_CANCEL, _("Cancel"), size = (60, 24)))
        vbox.Add(panel)
        vbox.Add(hbox, 1, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        dialog.SetSizer(vbox)
        dialog.Centre()
        macro = ""
        if dialog.ShowModal() == wx.ID_OK:
            macro = dialog.namectrl.GetValue()
            if macro != "":
                wx.CallAfter(self.edit_macro, macro)
        dialog.Destroy()
        return macro

    def edit_macro(self, macro):
        if macro == "": return self.new_macro()
        if macro in self.macros:
            old_def = self.macros[macro]
        elif len([c for c in macro.encode("ascii", "replace") if not c.isalnum() and c != "_"]):
            self.log(_("Macro name may contain only ASCII alphanumeric symbols and underscores"))
            return
        elif hasattr(self.__class__, "do_" + macro):
            self.log(_("Name '%s' is being used by built-in command") % macro)
            return
        else:
            old_def = ""
        self.start_macro(macro, old_def)
        return macro

    def update_macros_menu(self):
        if not hasattr(self, "macros_menu"):
            return  # too early, menu not yet built
        try:
            while True:
                item = self.macros_menu.FindItemByPosition(1)
                if item is None: break
                self.macros_menu.DeleteItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x, m = macro: self.start_macro(m, self.macros[m]), self.macros_menu.Append(-1, macro))

    #  --------------------------------------------------------------
    #  Slic3r integration
    #  --------------------------------------------------------------

    def load_slic3r_configs(self, menus):
        """List Slic3r configurations and create menu"""
        # Hack to get correct path for Slic3r config
        orig_appname = self.app.GetAppName()
        self.app.SetAppName("Slic3r")
        configpath = wx.StandardPaths.Get().GetUserDataDir()
        self.app.SetAppName(orig_appname)
        self.slic3r_configpath = configpath
        configfile = os.path.join(configpath, "slic3r.ini")
        config = self.read_slic3r_config(configfile)
        self.slic3r_configs = {}
        for cat in menus:
            menu = menus[cat]
            pattern = os.path.join(configpath, cat, "*.ini")
            files = sorted(glob.glob(pattern))
            try:
                preset = config.get("presets", cat)
                self.slic3r_configs[cat] = preset
            except:
                preset = None
                self.slic3r_configs[cat] = None
            for f in files:
                name = os.path.splitext(os.path.basename(f))[0]
                item = menu.Append(-1, name, f, wx.ITEM_RADIO)
                item.Check(os.path.basename(f) == preset)
                self.Bind(wx.EVT_MENU,
                          lambda event, cat = cat, f = f:
                          self.set_slic3r_config(configfile, cat, f), item)

    def read_slic3r_config(self, configfile, parser = None):
        """Helper to read a Slic3r configuration file"""
        import ConfigParser
        parser = ConfigParser.RawConfigParser()

        class add_header(object):
            def __init__(self, f):
                self.f = f
                self.header = '[dummy]'

            def readline(self):
                if self.header:
                    try: return self.header
                    finally: self.header = None
                else:
                    return self.f.readline()
        parser.readfp(add_header(open(configfile)), configfile)
        return parser

    def set_slic3r_config(self, configfile, cat, file):
        """Set new preset for a given category"""
        self.slic3r_configs[cat] = file
        if self.settings.slic3rupdate:
            config = self.read_slic3r_config(configfile)
            config.set("presets", cat, os.path.basename(file))
            f = StringIO.StringIO()
            config.write(f)
            data = f.getvalue()
            f.close()
            data = data.replace("[dummy]\n", "")
            with open(configfile, "w") as f:
                f.write(data)

class PronterApp(wx.App):

    mainwindow = None

    def __init__(self, *args, **kwargs):
        super(PronterApp, self).__init__(*args, **kwargs)
        self.SetAppName("Pronterface")
        self.mainwindow = PronterWindow(self)
        self.mainwindow.Show()

########NEW FILE########
__FILENAME__ = stlplater
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import os

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from .utils import install_locale
install_locale('pronterface')

import wx
import time
import threading
import math
import sys
import re
import traceback
import subprocess
from copy import copy

from printrun import stltool
from printrun.objectplater import Plater

glview = False
if "-nogl" not in sys.argv:
    try:
        from printrun import stlview
        glview = True
    except:
        print "Could not load 3D viewer for plater:"
        traceback.print_exc()


def evalme(s):
    return eval(s[s.find("(") + 1:s.find(")")])

def transformation_matrix(model):
    matrix = stltool.I
    if any(model.centeroffset):
        matrix = model.translation_matrix(model.centeroffset).dot(matrix)
    if model.rot:
        matrix = model.rotation_matrix([0, 0, model.rot]).dot(matrix)
    if any(model.offsets):
        matrix = model.translation_matrix(model.offsets).dot(matrix)
    return matrix

class showstl(wx.Window):
    def __init__(self, parent, size, pos):
        wx.Window.__init__(self, parent, size = size, pos = pos)
        self.i = 0
        self.parent = parent
        self.previ = 0
        self.Bind(wx.EVT_MOUSEWHEEL, self.rot)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.Bind(wx.EVT_PAINT, self.repaint)
        self.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.triggered = 0
        self.initpos = None
        self.prevsel = -1

    def prepare_model(self, m, scale):
        m.bitmap = wx.EmptyBitmap(800, 800, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(m.bitmap)
        dc.SetBackground(wx.Brush((0, 0, 0, 0)))
        dc.SetBrush(wx.Brush((0, 0, 0, 255)))
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        for i in m.facets:
            dc.DrawPolygon([wx.Point(400 + scale * p[0], (400 - scale * p[1])) for p in i[1]])
        dc.SelectObject(wx.NullBitmap)
        m.bitmap.SetMask(wx.Mask(m.bitmap, wx.Colour(0, 0, 0, 255)))

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.parent.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.parent.l.GetString(name)
        model = self.parent.models[name]
        model.offsets = [model.offsets[0] + delta[0],
                         model.offsets[1] + delta[1],
                         model.offsets[2]
                         ]
        self.Refresh()
        return True

    def move(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                currentpos = event.GetPositionTuple()
                delta = (0.5 * (currentpos[0] - self.initpos[0]),
                         -0.5 * (currentpos[1] - self.initpos[1])
                         )
                self.move_shape(delta)
                self.Refresh()
                self.initpos = None
        elif event.ButtonDown(wx.MOUSE_BTN_RIGHT):
            self.parent.right(event)
        elif event.Dragging():
            if self.initpos is None:
                self.initpos = event.GetPositionTuple()
            self.Refresh()
            dc = wx.ClientDC(self)
            p = event.GetPositionTuple()
            dc.DrawLine(self.initpos[0], self.initpos[1], p[0], p[1])
            del dc
        else:
            event.Skip()

    def rotate_shape(self, angle):
        """rotates acive shape
        positive angle is clockwise
        """
        self.i += angle
        if not self.triggered:
            self.triggered = 1
            threading.Thread(target = self.cr).start()

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        # print keycode
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        # h
        if keycode == 72:
            self.move_shape((-step, 0))
        # l
        if keycode == 76:
            self.move_shape((step, 0))
        # j
        if keycode == 75:
            self.move_shape((0, step))
        # k
        if keycode == 74:
            self.move_shape((0, -step))
        # [
        if keycode == 91:
            self.rotate_shape(-angle)
        # ]
        if keycode == 93:
            self.rotate_shape(angle)
        event.Skip()

    def rotateafter(self):
        if self.i != self.previ:
            i = self.parent.l.GetSelection()
            if i != wx.NOT_FOUND:
                self.parent.models[self.parent.l.GetString(i)].rot -= 5 * (self.i - self.previ)
            self.previ = self.i
            self.Refresh()

    def cr(self):
        time.sleep(0.01)
        wx.CallAfter(self.rotateafter)
        self.triggered = 0

    def rot(self, event):
        z = event.GetWheelRotation()
        s = self.parent.l.GetSelection()
        if self.prevsel != s:
            self.i = 0
            self.prevsel = s
        if z < 0:
            self.rotate_shape(-1)
        else:
            self.rotate_shape(1)

    def repaint(self, event):
        dc = wx.PaintDC(self)
        self.paint(dc = dc)

    def paint(self, coord1 = "x", coord2 = "y", dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        scale = 2
        dc.SetPen(wx.Pen(wx.Colour(100, 100, 100)))
        for i in xrange(20):
            dc.DrawLine(0, i * scale * 10, 400, i * scale * 10)
            dc.DrawLine(i * scale * 10, 0, i * scale * 10, 400)
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
        for i in xrange(4):
            dc.DrawLine(0, i * scale * 50, 400, i * scale * 50)
            dc.DrawLine(i * scale * 50, 0, i * scale * 50, 400)
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        dcs = wx.MemoryDC()
        for m in self.parent.models.values():
            b = m.bitmap
            im = b.ConvertToImage()
            imgc = wx.Point(im.GetWidth() / 2, im.GetHeight() / 2)
            im = im.Rotate(math.radians(m.rot), imgc, 0)
            bm = wx.BitmapFromImage(im)
            dcs.SelectObject(bm)
            bsz = bm.GetSize()
            dc.Blit(scale * m.offsets[0] - bsz[0] / 2, 400 - (scale * m.offsets[1] + bsz[1] / 2), bsz[0], bsz[1], dcs, 0, 0, useMask = 1)
        del dc

class StlPlater(Plater):

    load_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL|OpenSCAD files (*.scad)|*.scad")
    save_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL")

    def __init__(self, filenames = [], size = (800, 580), callback = None,
                 parent = None, build_dimensions = None, circular_platform = False,
                 simarrange_path = None, antialias_samples = 0):
        super(StlPlater, self).__init__(filenames, size, callback, parent, build_dimensions)
        self.cutting = False
        self.cutting_axis = None
        self.cutting_dist = None
        if glview:
            viewer = stlview.StlViewPanel(self, (580, 580),
                                          build_dimensions = self.build_dimensions,
                                          circular = circular_platform,
                                          antialias_samples = antialias_samples)
            # Cutting tool
            nrows = self.menusizer.GetRows()
            self.menusizer.Add(wx.StaticText(self.menupanel, -1, _("Cut along:")),
                               pos = (nrows, 0), span = (1, 1), flag = wx.ALIGN_CENTER)
            cutconfirmbutton = wx.Button(self.menupanel, label = _("Confirm cut"))
            cutconfirmbutton.Bind(wx.EVT_BUTTON, self.cut_confirm)
            cutconfirmbutton.Disable()
            self.cutconfirmbutton = cutconfirmbutton
            self.menusizer.Add(cutconfirmbutton, pos = (nrows, 1), span = (1, 1), flag = wx.EXPAND)
            cutpanel = wx.Panel(self.menupanel, -1)
            cutsizer = self.cutsizer = wx.BoxSizer(wx.HORIZONTAL)
            cutpanel.SetSizer(cutsizer)
            cutxplusbutton = wx.ToggleButton(cutpanel, label = _(">X"), style = wx.BU_EXACTFIT)
            cutxplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", 1))
            cutsizer.Add(cutxplusbutton, 1, flag = wx.EXPAND)
            cutzplusbutton = wx.ToggleButton(cutpanel, label = _(">Y"), style = wx.BU_EXACTFIT)
            cutzplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", 1))
            cutsizer.Add(cutzplusbutton, 1, flag = wx.EXPAND)
            cutzplusbutton = wx.ToggleButton(cutpanel, label = _(">Z"), style = wx.BU_EXACTFIT)
            cutzplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", 1))
            cutsizer.Add(cutzplusbutton, 1, flag = wx.EXPAND)
            cutxminusbutton = wx.ToggleButton(cutpanel, label = _("<X"), style = wx.BU_EXACTFIT)
            cutxminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", -1))
            cutsizer.Add(cutxminusbutton, 1, flag = wx.EXPAND)
            cutzminusbutton = wx.ToggleButton(cutpanel, label = _("<Y"), style = wx.BU_EXACTFIT)
            cutzminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", -1))
            cutsizer.Add(cutzminusbutton, 1, flag = wx.EXPAND)
            cutzminusbutton = wx.ToggleButton(cutpanel, label = _("<Z"), style = wx.BU_EXACTFIT)
            cutzminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", -1))
            cutsizer.Add(cutzminusbutton, 1, flag = wx.EXPAND)
            self.menusizer.Add(cutpanel, pos = (nrows + 1, 0), span = (1, 2), flag = wx.EXPAND)
        else:
            viewer = showstl(self, (580, 580), (0, 0))
        self.simarrange_path = simarrange_path if simarrange_path else "./simarrange/sa"
        self.set_viewer(viewer)

    def start_cutting_tool(self, event, axis, direction):
        toggle = event.GetEventObject()
        if toggle.GetValue():
            # Disable the other toggles
            for child in self.cutsizer.GetChildren():
                child = child.GetWindow()
                if child != toggle:
                    child.SetValue(False)
            self.cutting = True
            self.cutting_axis = axis
            self.cutting_dist = None
            self.cutting_direction = direction
        else:
            self.cutting = False
            self.cutting_axis = None
            self.cutting_dist = None
            self.cutting_direction = None

    def cut_confirm(self, event):
        name = self.l.GetSelection()
        name = self.l.GetString(name)
        model = self.models[name]
        transformation = transformation_matrix(model)
        transformed = model.transform(transformation)
        print _("Cutting %s alongside %s axis") % (name, self.cutting_axis)
        axes = ["x", "y", "z"]
        cut = transformed.cut(axes.index(self.cutting_axis),
                              self.cutting_direction,
                              self.cutting_dist)
        cut.offsets = [0, 0, 0]
        cut.rot = 0
        cut.scale = model.scale
        cut.filename = model.filename
        cut.centeroffset = [0, 0, 0]
        self.s.prepare_model(cut, 2)
        self.models[name] = cut
        self.cutconfirmbutton.Disable()
        self.cutting = False
        self.cutting_axis = None
        self.cutting_dist = None
        self.cutting_direction = None
        for child in self.cutsizer.GetChildren():
            child = child.GetWindow()
            child.SetValue(False)

    def clickcb(self, event, single = False):
        if not isinstance(self.s, stlview.StlViewPanel):
            return
        if self.cutting:
            self.clickcb_cut(event)
        else:
            self.clickcb_rebase(event)

    def clickcb_cut(self, event):
        axis = self.cutting_axis
        self.cutting_dist, _, _ = self.s.get_cutting_plane(axis, None,
                                                           local_transform = True)
        if self.cutting_dist is not None:
            self.cutconfirmbutton.Enable()

    def clickcb_rebase(self, event):
        x, y = event.GetPosition()
        ray_near, ray_far = self.s.mouse_to_ray(x, y, local_transform = True)
        best_match = None
        best_facet = None
        best_dist = float("inf")
        for key, model in self.models.iteritems():
            transformation = transformation_matrix(model)
            transformed = model.transform(transformation)
            if not transformed.intersect_box(ray_near, ray_far):
                print "Skipping %s for rebase search" % key
                continue
            facet, facet_dist = transformed.intersect(ray_near, ray_far)
            if facet is not None and facet_dist < best_dist:
                best_match = key
                best_facet = facet
                best_dist = facet_dist
        if best_match is not None:
            print "Rebasing %s" % best_match
            model = self.models[best_match]
            newmodel = model.rebase(best_facet)
            newmodel.offsets = model.offsets
            newmodel.rot = 0
            newmodel.scale = model.scale
            newmodel.filename = model.filename
            newmodel.centeroffset = [-(newmodel.dims[1] + newmodel.dims[0]) / 2,
                                     -(newmodel.dims[3] + newmodel.dims[2]) / 2,
                                     0]
            self.s.prepare_model(newmodel, 2)
            self.models[best_match] = newmodel
            wx.CallAfter(self.Refresh)

    def done(self, event, cb):
        try:
            os.mkdir("tempstl")
        except:
            pass
        name = "tempstl/" + str(int(time.time()) % 10000) + ".stl"
        self.export_to(name)
        if cb is not None:
            cb(name)
        self.Destroy()

    def load_file(self, filename):
        if filename.lower().endswith(".stl"):
            try:
                self.load_stl(filename)
            except:
                dlg = wx.MessageDialog(self, _("Loading STL file failed"), _("Error"), wx.OK)
                dlg.ShowModal()
                traceback.print_exc(file = sys.stdout)
        elif filename.lower().endswith(".scad"):
            try:
                self.load_scad(filename)
            except:
                dlg = wx.MessageDialog(self, _("Loading OpenSCAD file failed"), _("Error"), wx.OK)
                dlg.ShowModal()
                traceback.print_exc(file = sys.stdout)

    def load_scad(self, name):
        lf = open(name)
        s = [i.replace("\n", "").replace("\r", "").replace(";", "") for i in lf if "stl" in i]
        lf.close()

        for i in s:
            parts = i.split()
            for part in parts:
                if 'translate' in part:
                    translate_list = evalme(part)
            for part in parts:
                if 'rotate' in part:
                    rotate_list = evalme(part)
            for part in parts:
                if 'import' in part:
                    stl_file = evalme(part)

            newname = os.path.split(stl_file.lower())[1]
            c = 1
            while newname in self.models:
                newname = os.path.split(stl_file.lower())[1]
                newname = newname + "(%d)" % c
                c += 1
            stl_path = os.path.join(os.path.split(name)[0:len(os.path.split(stl_file)) - 1])
            stl_full_path = os.path.join(stl_path[0], str(stl_file))
            self.load_stl_into_model(stl_full_path, stl_file, translate_list, rotate_list[2])

    def load_stl(self, name):
        if not os.path.exists(name):
            print _("Couldn't load non-existing file %s") % name
            return
        path = os.path.split(name)[0]
        self.basedir = path
        if name.lower().endswith(".stl"):
            for model in self.models.values():
                if model.filename == name:
                    newmodel = copy(model)
                    newmodel.offsets = list(model.offsets)
                    newmodel.rot = model.rot
                    newmodel.scale = list(model.scale)
                    self.add_model(name, newmodel)
                    self.s.prepare_model(newmodel, 2)
                    break
            else:
                # Filter out the path, just show the STL filename.
                self.load_stl_into_model(name, name)
        wx.CallAfter(self.Refresh)

    def load_stl_into_model(self, path, name, offset = [0, 0, 0], rotation = 0, scale = [1.0, 1.0, 1.0]):
        model = stltool.stl(path)
        model.offsets = list(offset)
        model.rot = rotation
        model.scale = list(scale)
        model.filename = name
        self.add_model(name, model)
        model.centeroffset = [-(model.dims[1] + model.dims[0]) / 2,
                              -(model.dims[3] + model.dims[2]) / 2,
                              0]
        self.s.prepare_model(model, 2)

    def export_to(self, name):
        with open(name.replace(".", "_") + ".scad", "w") as sf:
            facets = []
            for model in self.models.values():
                r = model.rot
                o = model.offsets
                co = model.centeroffset
                sf.write("translate([%s, %s, %s])"
                         "rotate([0, 0, %s])"
                         "translate([%s, %s, %s])"
                         "import(\"%s\");\n" % (o[0], o[1], o[2],
                                                r,
                                                co[0], co[1], co[2],
                                                model.filename))
                model = model.transform(transformation_matrix(model))
                facets += model.facets
            stltool.emitstl(name, facets, "plater_export")
            print _("Wrote plate to %s") % name

    def autoplate(self, event = None):
        try:
            self.autoplate_simarrange()
        except:
            traceback.print_exc(file = sys.stdout)
            print _("Failed to use simarrange for plating, "
                    "falling back to the standard method")
            super(StlPlater, self).autoplate()

    def autoplate_simarrange(self):
        print _("Autoplating using simarrange")
        models = dict(self.models)
        files = [model.filename for model in models.values()]
        command = [self.simarrange_path, "--dryrun",
                   "-m",  # Pack around center
                   "-x", str(int(self.build_dimensions[0])),
                   "-y", str(int(self.build_dimensions[1]))] + files
        p = subprocess.Popen(command, stdout = subprocess.PIPE)

        pos_regexp = re.compile("File: (.*) minx: ([0-9]+), miny: ([0-9]+), minrot: ([0-9]+)")
        for line in p.stdout:
            line = line.rstrip()
            if "Generating plate" in line:
                plateid = int(line.split()[-1])
                if plateid > 0:
                    print _("Plate full, please remove some objects")
                    break
            if "File:" in line:
                bits = pos_regexp.match(line).groups()
                filename = bits[0]
                x = float(bits[1])
                y = float(bits[2])
                rot = -float(bits[3])
                for name, model in models.items():
                    # FIXME: not sure this is going to work superwell with utf8
                    if model.filename == filename:
                        model.offsets[0] = x
                        model.offsets[1] = y
                        model.rot = rot
                        del models[name]
                        break
        if p.wait() != 0:
            raise RuntimeError(_("simarrange failed"))

########NEW FILE########
__FILENAME__ = stltool
# coding: utf-8

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import struct
import math

import numpy
import numpy.linalg

def normalize(v):
    return v / numpy.linalg.norm(v)

def genfacet(v):
    veca = v[1] - v[0]
    vecb = v[2] - v[1]
    vecx = numpy.cross(veca, vecb)
    vlen = numpy.linalg.norm(vecx)
    if vlen == 0:
        vlen = 1
    normal = vecx / vlen
    return (normal, v)

I = numpy.identity(4)

def homogeneous(v, w = 1):
    return numpy.append(v, w)

def applymatrix(facet, matrix = I):
    return genfacet(map(lambda x: matrix.dot(homogeneous(x))[:3], facet[1]))

def ray_triangle_intersection(ray_near, ray_dir, (v1, v2, v3)):
    """
    Möller–Trumbore intersection algorithm in pure python
    Based on http://en.wikipedia.org/wiki/M%C3%B6ller%E2%80%93Trumbore_intersection_algorithm
    """
    eps = 0.000001
    edge1 = v2 - v1
    edge2 = v3 - v1
    pvec = numpy.cross(ray_dir, edge2)
    det = edge1.dot(pvec)
    if abs(det) < eps:
        return False, None
    inv_det = 1. / det
    tvec = ray_near - v1
    u = tvec.dot(pvec) * inv_det
    if u < 0. or u > 1.:
        return False, None
    qvec = numpy.cross(tvec, edge1)
    v = ray_dir.dot(qvec) * inv_det
    if v < 0. or u + v > 1.:
        return False, None

    t = edge2.dot(qvec) * inv_det
    if t < eps:
        return False, None

    return True, t

def ray_rectangle_intersection(ray_near, ray_dir, p0, p1, p2, p3):
    match1, _ = ray_triangle_intersection(ray_near, ray_dir, (p0, p1, p2))
    match2, _ = ray_triangle_intersection(ray_near, ray_dir, (p0, p2, p3))
    return match1 or match2

def ray_box_intersection(ray_near, ray_dir, p0, p1):
    x0, y0, z0 = p0[:]
    x1, y1, z1 = p1[:]
    rectangles = [((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)),
                  ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
                  ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
                  ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),
                  ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)),
                  ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)),
                  ]
    rectangles = [(numpy.array(p) for p in rect)
                  for rect in rectangles]
    for rect in rectangles:
        if ray_rectangle_intersection(ray_near, ray_dir, *rect):
            return True
    return False

def emitstl(filename, facets = [], objname = "stltool_export", binary = True):
    if filename is None:
        return
    if binary:
        with open(filename, "wb") as f:
            buf = "".join(["\0"] * 80)
            buf += struct.pack("<I", len(facets))
            facetformat = struct.Struct("<ffffffffffffH")
            for facet in facets:
                l = list(facet[0][:])
                for vertex in facet[1]:
                    l += list(vertex[:])
                l.append(0)
                buf += facetformat.pack(*l)
            f.write(buf)
    else:
        with open(filename, "w") as f:
            f.write("solid " + objname + "\n")
            for i in facets:
                f.write("  facet normal " + " ".join(map(str, i[0])) + "\n   outer loop\n")
                for j in i[1]:
                    f.write("    vertex " + " ".join(map(str, j)) + "\n")
                f.write("   endloop" + "\n")
                f.write("  endfacet" + "\n")
            f.write("endsolid " + objname + "\n")

class stl(object):

    _dims = None

    def _get_dims(self):
        if self._dims is None:
            minx = float("inf")
            miny = float("inf")
            minz = float("inf")
            maxx = float("-inf")
            maxy = float("-inf")
            maxz = float("-inf")
            for normal, facet in self.facets:
                for vert in facet:
                    if vert[0] < minx:
                        minx = vert[0]
                    if vert[1] < miny:
                        miny = vert[1]
                    if vert[2] < minz:
                        minz = vert[2]
                    if vert[0] > maxx:
                        maxx = vert[0]
                    if vert[1] > maxy:
                        maxy = vert[1]
                    if vert[2] > maxz:
                        maxz = vert[2]
            self._dims = [minx, maxx, miny, maxy, minz, maxz]
        return self._dims
    dims = property(_get_dims)

    def __init__(self, filename = None):
        self.facet = (numpy.zeros(3), (numpy.zeros(3), numpy.zeros(3), numpy.zeros(3)))
        self.facets = []
        self.facetsminz = []
        self.facetsmaxz = []

        self.name = ""
        self.insolid = 0
        self.infacet = 0
        self.inloop = 0
        self.facetloc = 0
        if filename is None:
            return
        with open(filename) as f:
            data = f.read()
        if "facet normal" in data[1:300] and "outer loop" in data[1:300]:
            lines = data.split("\n")
            for line in lines:
                if not self.parseline(line):
                    return
        else:
            print "Not an ascii stl solid - attempting to parse as binary"
            f = open(filename, "rb")
            buf = f.read(84)
            while len(buf) < 84:
                newdata = f.read(84 - len(buf))
                if not len(newdata):
                    break
                buf += newdata
            facetcount = struct.unpack_from("<I", buf, 80)
            facetformat = struct.Struct("<ffffffffffffH")
            for i in xrange(facetcount[0]):
                buf = f.read(50)
                while len(buf) < 50:
                    newdata = f.read(50 - len(buf))
                    if not len(newdata):
                        break
                    buf += newdata
                fd = list(facetformat.unpack(buf))
                self.name = "binary soloid"
                facet = [fd[:3], [fd[3:6], fd[6:9], fd[9:12]]]
                self.facets.append(facet)
                self.facetsminz.append((min(map(lambda x: x[2], facet[1])), facet))
                self.facetsmaxz.append((max(map(lambda x: x[2], facet[1])), facet))
            f.close()
            return

    def intersect_box(self, ray_near, ray_far):
        ray_near = numpy.array(ray_near)
        ray_far = numpy.array(ray_far)
        ray_dir = normalize(ray_far - ray_near)
        x0, x1, y0, y1, z0, z1 = self.dims
        p0 = numpy.array([x0, y0, z0])
        p1 = numpy.array([x1, y1, z1])
        return ray_box_intersection(ray_near, ray_dir, p0, p1)

    def intersect(self, ray_near, ray_far):
        ray_near = numpy.array(ray_near)
        ray_far = numpy.array(ray_far)
        ray_dir = normalize(ray_far - ray_near)
        best_facet = None
        best_dist = float("inf")
        for facet_i, (normal, facet) in enumerate(self.facets):
            match, dist = ray_triangle_intersection(ray_near, ray_dir, facet)
            if match and dist < best_dist:
                best_facet = facet_i
                best_dist = dist
        return best_facet, best_dist

    def rebase(self, facet_i):
        normal, facet = self.facets[facet_i]
        u1 = facet[1] - facet[0]
        v2 = facet[2] - facet[0]
        n1 = u1.dot(u1)
        e1 = u1 / math.sqrt(n1)
        u2 = v2 - u1 * v2.dot(u1) / n1
        e2 = u2 / numpy.linalg.norm(u2)
        e3 = numpy.cross(e1, e2)
        # Ensure Z direction if opposed to the normal
        if normal.dot(e3) > 0:
            e2 = - e2
            e3 = - e3
        matrix = [[e1[0], e2[0], e3[0], 0],
                  [e1[1], e2[1], e3[1], 0],
                  [e1[2], e2[2], e3[2], 0],
                  [0, 0, 0, 1]]
        matrix = numpy.array(matrix)
        # Inverse change of basis matrix
        matrix = numpy.linalg.inv(matrix)
        # Set first vertex of facet as origin
        neworig = matrix.dot(homogeneous(facet[0]))
        matrix[:3, 3] = -neworig[:3]
        newmodel = self.transform(matrix)
        return newmodel

    def cut(self, axis, direction, dist):
        s = stl()
        s.facets = []
        f = min if direction == 1 else max
        for _, facet in self.facets:
            minval = f([vertex[axis] for vertex in facet])
            if direction * minval > direction * dist:
                continue
            vertices = []
            for vertex in facet:
                vertex = numpy.copy(vertex)
                if direction * (vertex[axis] - dist) > 0:
                    vertex[axis] = dist
                vertices.append(vertex)
            s.facets.append(genfacet(vertices))
        s.insolid = 0
        s.infacet = 0
        s.inloop = 0
        s.facetloc = 0
        s.name = self.name
        for facet in s.facets:
            s.facetsminz += [(min(map(lambda x:x[2], facet[1])), facet)]
            s.facetsmaxz += [(max(map(lambda x:x[2], facet[1])), facet)]
        return s

    def translation_matrix(self, v):
        matrix = [[1, 0, 0, v[0]],
                  [0, 1, 0, v[1]],
                  [0, 0, 1, v[2]],
                  [0, 0, 0, 1]
                  ]
        return numpy.array(matrix)

    def translate(self, v = [0, 0, 0]):
        return self.transform(self.translation_matrix(v))

    def rotation_matrix(self, v):
        z = v[2]
        matrix1 = [[math.cos(math.radians(z)), -math.sin(math.radians(z)), 0, 0],
                   [math.sin(math.radians(z)), math.cos(math.radians(z)), 0, 0],
                   [0, 0, 1, 0],
                   [0, 0, 0, 1]
                   ]
        matrix1 = numpy.array(matrix1)
        y = v[0]
        matrix2 = [[1, 0, 0, 0],
                   [0, math.cos(math.radians(y)), -math.sin(math.radians(y)), 0],
                   [0, math.sin(math.radians(y)), math.cos(math.radians(y)), 0],
                   [0, 0, 0, 1]
                   ]
        matrix2 = numpy.array(matrix2)
        x = v[1]
        matrix3 = [[math.cos(math.radians(x)), 0, -math.sin(math.radians(x)), 0],
                   [0, 1, 0, 0],
                   [math.sin(math.radians(x)), 0, math.cos(math.radians(x)), 0],
                   [0, 0, 0, 1]
                   ]
        matrix3 = numpy.array(matrix3)
        return matrix3.dot(matrix2.dot(matrix1))

    def rotate(self, v = [0, 0, 0]):
        return self.transform(self.rotation_matrix(v))

    def scale_matrix(self, v):
        matrix = [[v[0], 0, 0, 0],
                  [0, v[1], 0, 0],
                  [0, 0, v[2], 0],
                  [0, 0, 0, 1]
                  ]
        return numpy.array(matrix)

    def scale(self, v = [0, 0, 0]):
        return self.transform(self.scale_matrix(v))

    def transform(self, m = I):
        s = stl()
        s.facets = [applymatrix(i, m) for i in self.facets]
        s.insolid = 0
        s.infacet = 0
        s.inloop = 0
        s.facetloc = 0
        s.name = self.name
        for facet in s.facets:
            s.facetsminz += [(min(map(lambda x:x[2], facet[1])), facet)]
            s.facetsmaxz += [(max(map(lambda x:x[2], facet[1])), facet)]
        return s

    def export(self, f = sys.stdout):
        f.write("solid " + self.name + "\n")
        for i in self.facets:
            f.write("  facet normal " + " ".join(map(str, i[0])) + "\n")
            f.write("   outer loop" + "\n")
            for j in i[1]:
                f.write("    vertex " + " ".join(map(str, j)) + "\n")
            f.write("   endloop" + "\n")
            f.write("  endfacet" + "\n")
        f.write("endsolid " + self.name + "\n")
        f.flush()

    def parseline(self, l):
        l = l.strip()
        if l.startswith("solid"):
            self.insolid = 1
            self.name = l[6:]
            # print self.name

        elif l.startswith("endsolid"):
            self.insolid = 0
            return 0
        elif l.startswith("facet normal"):
            l = l.replace(", ", ".")
            self.infacet = 1
            self.facetloc = 0
            normal = numpy.array(map(float, l.split()[2:]))
            self.facet = (normal, (numpy.zeros(3), numpy.zeros(3), numpy.zeros(3)))
        elif l.startswith("endfacet"):
            self.infacet = 0
            self.facets.append(self.facet)
            facet = self.facet
            self.facetsminz += [(min(map(lambda x:x[2], facet[1])), facet)]
            self.facetsmaxz += [(max(map(lambda x:x[2], facet[1])), facet)]
        elif l.startswith("vertex"):
            l = l.replace(", ", ".")
            self.facet[1][self.facetloc][:] = numpy.array(map(float, l.split()[1:]))
            self.facetloc += 1
        return 1

if __name__ == "__main__":
    s = stl("../../Downloads/frame-vertex-neo-foot-x4.stl")
    for i in xrange(11, 11):
        working = s.facets[:]
        for j in reversed(sorted(s.facetsminz)):
            if j[0] > i:
                working.remove(j[1])
            else:
                break
        for j in (sorted(s.facetsmaxz)):
            if j[0] < i:
                working.remove(j[1])
            else:
                break

        print i, len(working)
    emitstl("../../Downloads/frame-vertex-neo-foot-x4-a.stl", s.facets, "emitted_object")
# stl("../prusamendel/stl/mendelplate.stl")

########NEW FILE########
__FILENAME__ = stlview
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
import time

import numpy
import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import GL_AMBIENT_AND_DIFFUSE, glBegin, glClearColor, \
    glColor3f, GL_CULL_FACE, GL_DEPTH_TEST, GL_DIFFUSE, GL_EMISSION, \
    glEnable, glEnd, GL_FILL, GLfloat, GL_FRONT_AND_BACK, GL_LIGHT0, \
    GL_LIGHT1, glLightfv, GL_LIGHTING, GL_LINE, glMaterialf, glMaterialfv, \
    glMultMatrixd, glNormal3f, glPolygonMode, glPopMatrix, GL_POSITION, \
    glPushMatrix, glRotatef, glScalef, glShadeModel, GL_SHININESS, \
    GL_SMOOTH, GL_SPECULAR, glTranslatef, GL_TRIANGLES, glVertex3f, \
    glGetDoublev, GL_MODELVIEW_MATRIX, GLdouble, glClearDepth, glDepthFunc, \
    GL_LEQUAL, GL_BLEND, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, \
    GL_LINE_LOOP, glGetFloatv, GL_LINE_WIDTH, glLineWidth, glDisable, \
    GL_LINE_SMOOTH
from pyglet import gl

from .gl.panel import wxGLPanel
from .gl.trackball import build_rotmatrix
from .gl.libtatlin import actors

def vec(*args):
    return (GLfloat * len(args))(*args)

class stlview(object):
    def __init__(self, facets, batch):
        # Create the vertex and normal arrays.
        vertices = []
        normals = []

        for i in facets:
            for j in i[1]:
                vertices.extend(j)
                normals.extend(i[0])

        # Create a list of triangle indices.
        indices = range(3 * len(facets))  # [[3*i, 3*i+1, 3*i+2] for i in xrange(len(facets))]
        # print indices[:10]
        self.vertex_list = batch.add_indexed(len(vertices) // 3,
                                             GL_TRIANGLES,
                                             None,  # group,
                                             indices,
                                             ('v3f/static', vertices),
                                             ('n3f/static', normals))

    def delete(self):
        self.vertex_list.delete()

class StlViewPanel(wxGLPanel):

    do_lights = False

    def __init__(self, parent, size, id = wx.ID_ANY,
                 build_dimensions = None, circular = False,
                 antialias_samples = 0):
        super(StlViewPanel, self).__init__(parent, id, wx.DefaultPosition, size, 0,
                                           antialias_samples = antialias_samples)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double_click)
        self.initialized = True
        self.parent = parent
        self.initpos = None
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]
        self.platform = actors.Platform(self.build_dimensions,
                                        circular = circular)
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.forceresize)
        self.mousepos = (0, 0)

    def OnReshape(self):
        self.mview_initialized = False
        super(StlViewPanel, self).OnReshape()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, call_reshape = True):
        '''Initialize OpenGL for use in the window.'''
        if self.GLinitialized:
            return
        self.GLinitialized = True
        # create a pyglet context for this panel
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
        # normal gl init
        glClearColor(0, 0, 0, 1)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glClearDepth(1.0)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Uncomment this line for a wireframe view
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Simple light setup.  On Windows GL_LIGHT0 is enabled by default,
        # but this is not the case on Linux or Mac, so remember to always
        # include it.
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)

        glLightfv(GL_LIGHT0, GL_POSITION, vec(.5, .5, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(1, 1, 1, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 0, .5, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(.5, .5, .5, 1))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(1, 1, 1, 1))
        glShadeModel(GL_SMOOTH)

        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0, 0.3, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, vec(1, 1, 1, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0, 0.1, 0, 0.9))
        if call_reshape:
            self.OnReshape()
        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def double_click(self, event):
        if hasattr(self.parent, "clickcb") and self.parent.clickcb:
            self.parent.clickcb(event)

    def forceresize(self):
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 1))
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] - 1))
        self.initialized = False

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: move active object,
            with shift rotate viewport
        RMB: nothing
            with shift move viewport
        """
        self.mousepos = event.GetPositionTuple()
        if event.Dragging() and event.LeftIsDown():
            self.handle_rotation(event)
        elif event.Dragging() and event.RightIsDown():
            self.handle_translation(event)
        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                self.initpos = None
        elif event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None
        else:
            event.Skip()
            return
        event.Skip()
        wx.CallAfter(self.Refresh)

    def handle_wheel(self, event):
        delta = event.GetWheelRotation()
        factor = 1.05
        x, y = event.GetPositionTuple()
        x, y, _ = self.mouse_to_3d(x, y, local_transform = True)
        if delta > 0:
            self.zoom(factor, (x, y))
        else:
            self.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """react to mouse wheel actions:
        rotate object
            with shift zoom viewport
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        print keycode
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        # h
        if keycode == 72:
            self.parent.move_shape((-step, 0))
        # l
        if keycode == 76:
            self.parent.move_shape((step, 0))
        # j
        if keycode == 75:
            self.parent.move_shape((0, step))
        # k
        if keycode == 74:
            self.parent.move_shape((0, -step))
        # [
        if keycode == 91:
            self.parent.rotate_shape(-angle)
        # ]
        if keycode == 93:
            self.parent.rotate_shape(angle)
        event.Skip()
        wx.CallAfter(self.Refresh)

    def anim(self, obj):
        g = 50 * 9.8
        v = 20
        dt = 0.05
        basepos = obj.offsets[2]
        obj.offsets[2] += obj.animoffset
        while obj.offsets[2] > -1:
            time.sleep(dt)
            obj.offsets[2] -= v * dt
            v += g * dt
            if obj.offsets[2] < 0:
                obj.scale[2] *= 1 - 3 * dt
        # return
        v = v / 4
        while obj.offsets[2] < basepos:
            time.sleep(dt)
            obj.offsets[2] += v * dt
            v -= g * dt
            obj.scale[2] *= 1 + 5 * dt
        obj.scale[2] = 1.0

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        if not self.platform.initialized:
            self.platform.init()
        self.initialized = 1
        wx.CallAfter(self.Refresh)

    def prepare_model(self, m, scale):
        batch = pyglet.graphics.Batch()
        stlview(m.facets, batch = batch)
        m.batch = batch
        # m.animoffset = 300
        # threading.Thread(target = self.anim, args = (m, )).start()
        wx.CallAfter(self.Refresh)

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        self.create_objects()

        glPushMatrix()
        glTranslatef(0, 0, -self.dist)
        glMultMatrixd(build_rotmatrix(self.basequat))  # Rotate according to trackball
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
        glTranslatef(- self.build_dimensions[3] - self.platform.width / 2,
                     - self.build_dimensions[4] - self.platform.depth / 2, 0)  # Move origin to bottom left of platform
        # Draw platform
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glDisable(GL_LIGHTING)
        self.platform.draw()
        glEnable(GL_LIGHTING)
        # Draw mouse
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = (0, 0, 1), plane_offset = 0,
                                    local_transform = False)
        if inter is not None:
            glPushMatrix()
            glTranslatef(inter[0], inter[1], inter[2])
            glBegin(GL_TRIANGLES)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(1, 0, 0, 1))
            glNormal3f(0, 0, 1)
            glVertex3f(2, 2, 0)
            glVertex3f(-2, 2, 0)
            glVertex3f(-2, -2, 0)
            glVertex3f(2, -2, 0)
            glVertex3f(2, 2, 0)
            glVertex3f(-2, -2, 0)
            glEnd()
            glPopMatrix()

        # Draw objects
        glDisable(GL_CULL_FACE)
        glPushMatrix()
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.3, 0.7, 0.5, 1))
        for i in self.parent.models:
            model = self.parent.models[i]
            glPushMatrix()
            glTranslatef(*(model.offsets))
            glRotatef(model.rot, 0.0, 0.0, 1.0)
            glTranslatef(*(model.centeroffset))
            glScalef(*model.scale)
            model.batch.draw()
            glPopMatrix()
        glPopMatrix()
        glEnable(GL_CULL_FACE)

        # Draw cutting plane
        if self.parent.cutting:
            # FIXME: make this a proper Actor
            axis = self.parent.cutting_axis
            fixed_dist = self.parent.cutting_dist
            dist, plane_width, plane_height = self.get_cutting_plane(axis, fixed_dist)
            if dist is not None:
                glPushMatrix()
                if axis == "x":
                    glRotatef(90, 0, 1, 0)
                    glRotatef(90, 0, 0, 1)
                    glTranslatef(0, 0, dist)
                elif axis == "y":
                    glRotatef(90, 1, 0, 0)
                    glTranslatef(0, 0, -dist)
                elif axis == "z":
                    glTranslatef(0, 0, dist)
                glDisable(GL_CULL_FACE)
                glBegin(GL_TRIANGLES)
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0, 0.9, 0.15, 0.3))
                glNormal3f(0, 0, self.parent.cutting_direction)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(0, plane_height, 0)
                glVertex3f(0, 0, 0)
                glVertex3f(plane_width, 0, 0)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(0, 0, 0)
                glEnd()
                glEnable(GL_CULL_FACE)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glEnable(GL_LINE_SMOOTH)
                orig_linewidth = (GLfloat)()
                glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
                glLineWidth(4.0)
                glBegin(GL_LINE_LOOP)
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0, 0.8, 0.15, 1))
                glVertex3f(0, 0, 0)
                glVertex3f(0, plane_height, 0)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(plane_width, 0, 0)
                glEnd()
                glLineWidth(orig_linewidth)
                glDisable(GL_LINE_SMOOTH)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glPopMatrix()

        glPopMatrix()

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_modelview_mat(self, local_transform):
        mvmat = (GLdouble * 16)()
        if local_transform:
            glPushMatrix()
            # Rotate according to trackball
            glTranslatef(0, 0, -self.dist)
            glMultMatrixd(build_rotmatrix(self.basequat))  # Rotate according to trackball
            glTranslatef(- self.build_dimensions[3] - self.platform.width / 2,
                         - self.build_dimensions[4] - self.platform.depth / 2, 0)  # Move origin to bottom left of platform
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    def get_cutting_plane(self, cutting_axis, fixed_dist, local_transform = False):
        cutting_plane_sizes = {"x": (self.platform.depth, self.platform.height),
                               "y": (self.platform.width, self.platform.height),
                               "z": (self.platform.width, self.platform.depth)}
        plane_width, plane_height = cutting_plane_sizes[cutting_axis]
        if fixed_dist is not None:
            return fixed_dist, plane_width, plane_height
        ref_sizes = {"x": self.platform.width,
                     "y": self.platform.depth,
                     "z": self.platform.height,
                     }
        ref_planes = {"x": (0, 0, 1),
                      "y": (0, 0, 1),
                      "z": (0, 1, 0)
                      }
        ref_offsets = {"x": 0,
                       "y": 0,
                       "z": - self.platform.depth / 2
                       }
        translate_axis = {"x": 0,
                          "y": 1,
                          "z": 2
                          }
        fallback_ref_planes = {"x": (0, 1, 0),
                               "y": (1, 0, 0),
                               "z": (1, 0, 0)
                               }
        fallback_ref_offsets = {"x": - self.platform.height / 2,
                                "y": - self.platform.width / 2,
                                "z": - self.platform.width / 2,
                                }
        ref_size = ref_sizes[cutting_axis]
        ref_plane = ref_planes[cutting_axis]
        ref_offset = ref_offsets[cutting_axis]
        inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = ref_plane,
                                    plane_offset = ref_offset,
                                    local_transform = local_transform)
        max_size = max((self.platform.width,
                        self.platform.depth,
                        self.platform.height))
        dist = None
        if inter is not None and numpy.fabs(inter).max() + max_size / 2 < 2 * max_size:
            dist = inter[translate_axis[cutting_axis]]
        if dist is None or dist < -0.5 * ref_size or dist > 1.5 * ref_size:
            ref_plane = fallback_ref_planes[cutting_axis]
            ref_offset = fallback_ref_offsets[cutting_axis]
            inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                        plane_normal = ref_plane,
                                        plane_offset = ref_offset,
                                        local_transform = False)
            if inter is not None and numpy.fabs(inter).max() + max_size / 2 < 2 * max_size:
                dist = inter[translate_axis[cutting_axis]]
        if dist is not None:
            dist = min(1.5 * ref_size, max(-0.5 * ref_size, dist))
        return dist, plane_width, plane_height

def main():
    app = wx.App(redirect = False)
    frame = wx.Frame(None, -1, "GL Window", size = (400, 400))
    StlViewPanel(frame)
    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = utils
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import re
import gettext
import datetime
import subprocess
import shlex
import logging

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not
# found (windows)
def install_locale(domain):
    if os.path.exists('/usr/share/pronterface/locale'):
        gettext.install(domain, '/usr/share/pronterface/locale', unicode = 1)
    elif os.path.exists('/usr/local/share/pronterface/locale'):
        gettext.install(domain, '/usr/local/share/pronterface/locale',
                        unicode = 1)
    else:
        gettext.install(domain, './locale', unicode = 1)

def setup_logging(out):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logging_handler = logging.StreamHandler(out)
    logging_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(logging_handler)

def iconfile(filename):
    if hasattr(sys, "frozen") and sys.frozen == "windows_exe":
        return sys.executable
    else:
        return pixmapfile(filename)

def imagefile(filename):
    for prefix in ['/usr/local/share/pronterface/images',
                   '/usr/share/pronterface/images']:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]),
                                   "images", filename)
    if os.path.exists(local_candidate):
        return local_candidate
    else:
        return os.path.join("images", filename)

def lookup_file(filename, prefixes):
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]), filename)
    if os.path.exists(local_candidate):
        return local_candidate
    for prefix in prefixes:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    return filename

def pixmapfile(filename):
    return lookup_file(filename, ['/usr/local/share/pixmaps',
                                  '/usr/share/pixmaps'])

def sharedfile(filename):
    return lookup_file(filename, ['/usr/local/share/pronterface',
                                  '/usr/share/pronterface'])

def configfile(filename):
    return lookup_file(filename, [os.path.expanduser("~/.printrun/"), ])

def decode_utf8(s):
    try:
        s = s.decode("utf-8")
    except:
        pass
    return s

def format_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

def format_duration(delta):
    return str(datetime.timedelta(seconds = int(delta)))

def prepare_command(command, replaces = None):
    command = shlex.split(command.replace("\\", "\\\\").encode())
    if replaces:
        replaces["$python"] = sys.executable
        for pattern, rep in replaces.items():
            command = [bit.replace(pattern, rep) for bit in command]
    command = [bit.encode() for bit in command]
    return command

def run_command(command, replaces = None, stdout = subprocess.STDOUT, stderr = subprocess.STDOUT, blocking = False):
    command = prepare_command(command, replaces)
    if blocking:
        return subprocess.call(command)
    else:
        return subprocess.Popen(command, stderr = stderr, stdout = stdout)

def get_command_output(command, replaces):
    p = run_command(command, replaces,
                    stdout = subprocess.PIPE, stderr = subprocess.STDOUT,
                    blocking = False)
    return p.stdout.read()

class RemainingTimeEstimator(object):

    drift = None
    gcode = None

    def __init__(self, gcode):
        self.drift = 1
        self.previous_layers_estimate = 0
        self.current_layer_estimate = 0
        self.current_layer_lines = 0
        self.gcode = gcode
        self.remaining_layers_estimate = sum(layer.duration for layer in gcode.all_layers)
        if len(gcode) > 0:
            self.update_layer(0, 0)

    def update_layer(self, layer, printtime):
        self.previous_layers_estimate += self.current_layer_estimate
        if self.previous_layers_estimate > 0 and printtime > 0:
            self.drift = printtime / self.previous_layers_estimate
        self.current_layer_estimate = self.gcode.all_layers[layer].duration
        self.current_layer_lines = len(self.gcode.all_layers[layer])
        self.remaining_layers_estimate -= self.current_layer_estimate
        self.last_idx = -1
        self.last_estimate = None

    def __call__(self, idx, printtime):
        if not self.current_layer_lines:
            return (0, 0)
        if idx == self.last_idx:
            return self.last_estimate
        layer, line = self.gcode.idxs(idx)
        layer_progress = (1 - (float(line + 1) / self.current_layer_lines))
        remaining = layer_progress * self.current_layer_estimate + self.remaining_layers_estimate
        estimate = self.drift * remaining
        total = estimate + printtime
        self.last_idx = idx
        self.last_estimate = (estimate, total)
        return self.last_estimate

def parse_build_dimensions(bdim):
    # a string containing up to six numbers delimited by almost anything
    # first 0-3 numbers specify the build volume, no sign, always positive
    # remaining 0-3 numbers specify the coordinates of the "southwest" corner of the build platform
    # "XXX,YYY"
    # "XXXxYYY+xxx-yyy"
    # "XXX,YYY,ZZZ+xxx+yyy-zzz"
    # etc
    bdl = re.findall("([-+]?[0-9]*\.?[0-9]*)", bdim)
    defaults = [200, 200, 100, 0, 0, 0, 0, 0, 0]
    bdl = filter(None, bdl)
    bdl_float = [float(value) if value else defaults[i] for i, value in enumerate(bdl)]
    if len(bdl_float) < len(defaults):
        bdl_float += [defaults[i] for i in range(len(bdl_float), len(defaults))]
    for i in range(3):  # Check for nonpositive dimensions for build volume
        if bdl_float[i] <= 0: bdl_float[i] = 1
    return bdl_float

def get_home_pos(build_dimensions):
    return build_dimensions[6:9] if len(build_dimensions) >= 9 else None

def hexcolor_to_float(color, components):
    color = color[1:]
    numel = len(color)
    ndigits = numel / components
    div = 16 ** ndigits - 1
    return tuple(round(float(int(color[i:i + ndigits], 16)) / div, 2)
                 for i in range(0, numel, ndigits))

def check_rgb_color(color):
    if len(color[1:]) % 3 != 0:
        ex = ValueError(_("Color must be specified as #RGB"))
        ex.from_validator = True
        raise ex

def check_rgba_color(color):
    if len(color[1:]) % 4 != 0:
        ex = ValueError(_("Color must be specified as #RGBA"))
        ex.from_validator = True
        raise ex

tempreport_exp = re.compile("([TB]\d*):([-+]?\d*\.?\d*)(?: ?\/)?([-+]?\d*\.?\d*)")
def parse_temperature_report(report):
    matches = tempreport_exp.findall(report)
    return dict((m[0], (m[1], m[2])) for m in matches)

########NEW FILE########
__FILENAME__ = zscaper
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx
from stltool import stl, genfacet, emitstl
a = wx.App()

def genscape(data = [[0, 1, 0, 0], [1, 0, 2, 0], [1, 0, 0, 0], [0, 1, 0, 1]],
             pscale = 1.0, bheight = 1.0, zscale = 1.0):
    o = stl(None)
    datal = len(data)
    datah = len(data[0])
    # create bottom:
    bmidpoint = (pscale * (datal - 1) / 2.0, pscale * (datah - 1) / 2.0)
    # print range(datal), bmidpoint
    for i in zip(range(datal + 1)[:-1], range(datal + 1)[1:])[:-1]:
        # print (pscale*i[0], pscale*i[1])
        o.facets += [[[0, 0, -1], [[0.0, pscale * i[0], 0.0], [0.0, pscale * i[1], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [[[0, 0, -1], [[2.0 * bmidpoint[1], pscale * i[1], 0.0], [2.0 * bmidpoint[1], pscale * i[0], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [genfacet([[0.0, pscale * i[0], data[i[0]][0] * zscale + bheight], [0.0, pscale * i[1], data[i[1]][0] * zscale + bheight], [0.0, pscale * i[1], 0.0]])]
        o.facets += [genfacet([[2.0 * bmidpoint[1], pscale * i[1], data[i[1]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[0], data[i[0]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[1], 0.0]])]
        o.facets += [genfacet([[0.0, pscale * i[0], data[i[0]][0] * zscale + bheight], [0.0, pscale * i[1], 0.0], [0.0, pscale * i[0], 0.0]])]
        o.facets += [genfacet([[2.0 * bmidpoint[1], pscale * i[1], 0.0], [2.0 * bmidpoint[1], pscale * i[0], data[i[0]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[0], 0.0]])]
    for i in zip(range(datah + 1)[: - 1], range(datah + 1)[1:])[: - 1]:
        # print (pscale * i[0], pscale * i[1])
        o.facets += [[[0, 0, -1], [[pscale * i[1], 0.0, 0.0], [pscale * i[0], 0.0, 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [[[0, 0, -1], [[pscale * i[0], 2.0 * bmidpoint[0], 0.0], [pscale * i[1], 2.0 * bmidpoint[0], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [genfacet([[pscale * i[1], 0.0, data[0][i[1]] * zscale + bheight], [pscale * i[0], 0.0, data[0][i[0]] * zscale + bheight], [pscale * i[1], 0.0, 0.0]])]
        o.facets += [genfacet([[pscale * i[0], 2.0 * bmidpoint[0], data[datal - 1][i[0]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], data[datal - 1][i[1]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], 0.0]])]
        o.facets += [genfacet([[pscale * i[1], 0.0, 0.0], [pscale * i[0], 0.0, data[0][i[0]] * zscale + bheight], [pscale * i[0], 0.0, 0.0]])]
        o.facets += [genfacet([[pscale * i[0], 2.0 * bmidpoint[0], data[datal - 1][i[0]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], 0.0], [pscale * i[0], 2.0 * bmidpoint[0], 0.0]])]
    for i in xrange(datah - 1):
        for j in xrange(datal - 1):
            o.facets += [genfacet([[pscale * i, pscale * j, data[j][i] * zscale + bheight], [pscale * (i + 1), pscale * (j), data[j][i + 1] * zscale + bheight], [pscale * (i + 1), pscale * (j + 1), data[j + 1][i + 1] * zscale + bheight]])]
            o.facets += [genfacet([[pscale * (i), pscale * (j + 1), data[j + 1][i] * zscale + bheight], [pscale * i, pscale * j, data[j][i] * zscale + bheight], [pscale * (i + 1), pscale * (j + 1), data[j + 1][i + 1] * zscale + bheight]])]
            # print o.facets[-1]
    return o
def zimage(name, out):
    i = wx.Image(name)
    s = i.GetSize()
    print len(map(ord, i.GetData()[::3]))
    b = map(ord, i.GetData()[::3])
    data = []
    for i in xrange(s[0]):
        data += [b[i * s[1]:(i + 1) * s[1]]]
    # data = [i[::5] for i in data[::5]]
    emitstl(out, genscape(data, zscale = 0.1).facets, name)

"""
class scapewin(wx.Frame):
    def __init__(self, size = (400, 530)):
        wx.Frame.__init__(self, None,
                          title = "Right-click to load an image", size = size)
        self.SetIcon(wx.Icon("plater.png", wx.BITMAP_TYPE_PNG))
        self.SetClientSize(size)
        self.panel = wx.Panel(self, size = size)


"""
if __name__ == '__main__':
    """
    app = wx.App(False)
    main = scapewin()
    main.Show()
    app.MainLoop()
"""
    zimage("catposthtmap2.jpg", "testobj.stl")
del a

########NEW FILE########
__FILENAME__ = pronsole
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import traceback
from printrun.pronsole import pronsole

if __name__ == "__main__":

    interp = pronsole()
    interp.parse_cmdline(sys.argv[1:])
    try:
        interp.cmdloop()
    except SystemExit:
        interp.p.disconnect()
    except:
        print _("Caught an exception, exiting:")
        traceback.print_exc()
        interp.p.disconnect()

########NEW FILE########
__FILENAME__ = pronterface
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys

try:
    import wx  # NOQA
except:
    print("wxPython is not installed. This program requires wxPython to run.")
    if sys.version_info.major >= 3:
        print("""\
As you are currently running python3, this is most likely because wxPython is
not yet available for python3. You should try running with python2 instead.""")
        sys.exit(-1)
    else:
        raise

from printrun.pronterface import PronterApp

if __name__ == '__main__':
    app = PronterApp(False)
    try:
        app.MainLoop()
    except KeyboardInterrupt:
        pass
    del app

########NEW FILE########
__FILENAME__ = gcodeviewer
#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import logging
logging.basicConfig(level=logging.INFO)

import wx

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from printrun.gcview import GcodeViewFrame
from printrun import gcoder

app = wx.App(redirect = False)
build_dimensions = [200, 200, 100, -100, -100, 0]
build_dimensions = [200, 200, 100, 0, 0, 0]
frame = GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (800, 800), build_dimensions = build_dimensions)
gcode = gcoder.GCode(open(sys.argv[1]))
print "Gcode loaded"
frame.addfile(gcode)

first_move = None
for i in range(len(gcode.lines)):
    if gcode.lines[i].is_move:
        first_move = gcode.lines[i]
        break
last_move = None
for i in range(len(gcode.lines) - 1, -1, -1):
    if gcode.lines[i].is_move:
        last_move = gcode.lines[i]
        break
nsteps = 20
steptime = 50
lines = [first_move] \
    + [gcode.lines[int(float(i) * (len(gcode.lines) - 1) / nsteps)]
       for i in range(1, nsteps)] + [last_move]
current_line = 0
def setLine():
    global current_line
    frame.set_current_gline(lines[current_line])
    current_line = (current_line + 1) % len(lines)
    timer.Start()

timer = wx.CallLater(steptime, setLine)
timer.Start()

frame.Show(True)
app.MainLoop()
app.Destroy()

########NEW FILE########
