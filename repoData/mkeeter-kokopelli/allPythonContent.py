__FILENAME__ = about
from koko import NAME, VERSION, HASH

import wx

def show_about_box(event=None):
    '''Displays an About box with information about this program.'''

    info = wx.AboutDialogInfo()
    info.SetName(NAME)
    info.SetVersion(VERSION)

    if HASH is None:
        info.SetDescription('An interactive design tool for .cad files.')
    else:
        info.SetDescription(
            'An interactive design tool for .cad files.\ngit commit: ' +
            HASH
        )

    info.SetWebSite('https://github.com/mkeeter/kokopelli')
    info.SetCopyright(
'''(C) 2012-13 MIT Center for Bits and Atoms
(C) 2013 Matt Keeter''')

    wx.AboutBox(info)

########NEW FILE########
__FILENAME__ = app
import os
import Queue
import sys
import weakref

import wx

# Edit the system path to find things in the lib folder
sys.path.append(os.path.join(sys.path[0], 'koko'))

################################################################################

import koko
from   koko             import NAME

print '\r'+' '*80+'\r[||||||----]    importing koko.dialogs',
sys.stdout.flush()
import koko.dialogs     as dialogs

print '\r'+' '*80+'\r[||||||----]    importing koko.frame',
sys.stdout.flush()
from   koko.frame       import MainFrame

print '\r'+' '*80+'\r[||||||||--]    importing koko.template',
sys.stdout.flush()
from   koko.template    import TEMPLATE

print '\r'+' '*80+'\r[||||||||--]    importing koko.struct',
sys.stdout.flush()
from koko.struct        import Struct

print '\r'+' '*80+'\r[||||||||--]    importing koko.taskbot',
sys.stdout.flush()
from   koko.taskbot     import TaskBot

print '\r'+' '*80+'\r[||||||||--]    importing koko.prims.core',
sys.stdout.flush()
from   koko.prims.core  import PrimSet

print '\r'+' '*80+'\r[||||||||--]    importing koko.fab',
sys.stdout.flush()
from    koko.fab.image  import Image
from    koko.fab.mesh   import Mesh
from    koko.fab.asdf   import ASDF

print '\r'+' '*80+'\r[|||||||||-]    reticulating splines',
sys.stdout.flush()

# Dummy imports so that py2app includes these files
import koko.lib.shapes
import koko.lib.shapes2d
import koko.lib.shapes3d
import koko.lib.text

################################################################################

class App(wx.App):
    def OnInit(self):

        koko.APP = weakref.proxy(self)
        koko.TASKS = TaskBot()

        self._mode = 'cad'

        # Open a file from the command line
        if len(sys.argv) > 1:
            d, self.filename = os.path.split(sys.argv[1])
            self.directory = os.path.abspath(d)
        else:
            self.filename = ''
            self.directory = os.getcwd()

        # Create frame
        koko.FRAME = MainFrame(self)

        # Create a set of GUI primitives
        koko.PRIMS = PrimSet()

        # This is a brand new file
        self.saved = False
        self.reeval_required = True
        self.render_required = True

        # Snap the view to cad file bounds
        self.first_render = True

        # Show the application!
        koko.FRAME.Show()
        koko.CANVAS.SetFocus()

        # Start with the OpenGL window open to force OpenGL to
        # initialize itself, then switch back to the heightmap
        self.render_mode('3D')
        koko.GLCANVAS.init_GL()
        self.render_mode('2D')

        if self.filename:   wx.CallAfter(self.load)

        return True

    @property
    def directory(self):
        return self._directory
    @directory.setter
    def directory(self, value):
        try:
            sys.path.remove(self._directory)
        except (AttributeError, ValueError):
            pass
        self._directory = value
        if self.directory != '':
            os.chdir(self.directory)
            sys.path.append(self.directory)

    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, value):
        """ @brief Switches between CAD/CAM and CAM modes
            @param value New mode ('cad,'asdf', or 'stl')
        """
        self._mode = value

        koko.FRAME.get_menu('File','Reload').Enable(True)
        koko.FRAME.get_menu('File','Save').Enable(True)
        koko.FRAME.get_menu('File','Save As').Enable(True)
        koko.FRAME.get_menu('View','Show script').Enable(True)
        koko.FRAME.get_menu('View','Show output').Enable(True)
        koko.FRAME.get_menu('View','Re-render').Enable(True)
        for e in ['.png','.svg','.stl', '.dot','.asdf']:
            koko.FRAME.get_menu('Export', e).Enable(True)

        if value in ['stl','asdf','png','vol']:
            koko.FRAME.get_menu('File','Reload').Enable(False)
            koko.FRAME.get_menu('File','Save').Enable(False)
            koko.FRAME.get_menu('File','Save As').Enable(False)
            koko.FRAME.get_menu('View','Show script').Enable(False)
            koko.FRAME.get_menu('View','Show script').Check(False)
            koko.FRAME.show_script(False)
            koko.FRAME.get_menu('View','Show output').Enable(False)
            koko.FRAME.get_menu('View','Show output').Check(False)
            koko.FRAME.show_output(False)
            koko.FRAME.get_menu('View','Re-render').Enable(False)

            # Disable all exports for these values
            if value in ['stl','png','vol']:
                for e in ['.png','.svg','.stl', '.dot','.asdf']:
                    koko.FRAME.get_menu('Export', e).Enable(False)

            # Disable some exports for these other values
            elif value == 'asdf':
                for e in ['.svg','.dot']:
                    koko.FRAME.get_menu('Export', e).Enable(False)

            koko.FRAME.get_menu('Export','Show CAM panel').Check(value == 'vol')
            koko.FRAME.show_import(value == 'vol')
            koko.FRAME.show_cam(value != 'vol')

################################################################################

    def savepoint(self, event):
        """ @brief Callback when a save point is reached in the editor.
            @param event Either a boolean value or a StyledTextEvent
            from the callback.
        """
        if type(event) is wx.stc.StyledTextEvent:
            value = (event.EventType == wx.stc.wxEVT_STC_SAVEPOINTREACHED)
        else:
            value = event

        if value == self.saved: return

        # Modify the window titlebar.
        self.saved = value
        s = '%s:  ' % NAME
        if self.filename:
            s += self.filename
        else:
            s += '[Untitled]'

        if not self.saved:
            s += '*'

        koko.FRAME.SetTitle(s)


################################################################################

    def new(self, event=None):
        """ @brief Creates a new file from the default template. """
        if self.saved or dialogs.warn_changes():

            self.filename = ''
            self.mode = 'cad'
            self.clear()

            koko.EDITOR.text = TEMPLATE

            self.first_render = True

################################################################################

    def save(self, event=None):
        """ @brief Save callback from main menu.
        """

        # If we don't have a filename, perform Save As instead
        if self.filename == '':
            self.save_as()
        else:
            # Write out the file
            path = os.path.join(self.directory, self.filename)

            if koko.PRIMS.shapes != []:
                text = ('''##    Geometry header    ##
%s
##    End of geometry header    ##
''' % koko.PRIMS.to_script()) + koko.EDITOR.text
            else:
                text = koko.EDITOR.text

            with open(path, 'w') as f:
                f.write(text)

            # Tell the editor that we've saved
            # (this invokes the callback to change title text)
            koko.EDITOR.SetSavePoint()

            # Update the status box.
            koko.FRAME.status = 'Saved file %s' % self.filename

################################################################################

    def save_as(self, event=None):
        """ @brief Save As callback from main menu.
        """

        # Open a file dialog to get target
        df = dialogs.save_as(self.directory, extension='.ko')

        if df[1] != '':
            self.directory, self.filename = df
            self.save()

################################################################################

    def reload(self, event=None):
        """ @brief Reloads the current file, warning of changes if necessary.
        """
        if self.filename != ''  and (self.saved or dialogs.warn_changes()):
            self.load()
            self.first_render = False

################################################################################

    def clear(self):
        """ @brief Clears all data from previous file.
        """
        koko.TASKS.reset()
        koko.PRIMS.clear()
        koko.CANVAS.clear()
        koko.GLCANVAS.clear()
        koko.IMPORT.clear()

    def load(self):
        """ @brief Loads the current design file
            @details The file is defined by self.directory and self.filename
        """
        self.clear()

        path = os.path.join(self.directory, self.filename)

        if path[-3:] == '.ko' or path[-4:] == '.cad':
            with open(path, 'r') as f:
                text = f.read()
                if text.split('\n')[0] == '##    Geometry header    ##':
                    koko.PRIMS.reconstruct(eval(text.split('\n')[1]))
                    koko.PRIMS.undo_stack = [koko.PRIMS.reconstructor()]
                    text = '\n'.join(text.split('\n')[3:])
            koko.EDITOR.text = text
            koko.FRAME.status = 'Loaded design file'

            if path[-4:] == '.cad':
                dialogs.warning("""
This file has a '.cad' extension, which was superceded by '.ko'.  It may use deprecated features or syntax.

If it is an example file, the 'kokopelli/examples' folder may include an updated version with a '.ko' extension""")

            self.mode = 'cad'
            self.first_render = True
            self.savepoint(True)

        elif path[-4:] == '.png':
            self.mode = 'png'
            img = Image.load(path)
            koko.CANVAS.load_image(img)
            koko.GLCANVAS.load_image(img)
            koko.FAB.set_input(img)
            wx.CallAfter(self.snap_bounds)

        elif path[-4:] == '.stl':
            self.mode = 'stl'
            mesh = Mesh.load(path)

            koko.FRAME.get_menu('View', '3D').Check(True)
            self.render_mode('3D')

            koko.GLCANVAS.load_mesh(mesh)
            wx.CallAfter(self.snap_bounds)

        elif path[-5:] == '.asdf':
            self.mode = 'asdf'

            koko.FRAME.status = 'Loading ASDF'
            wx.Yield()

            asdf = ASDF.load(path)
            koko.FRAME.status = 'Triangulating'
            wx.Yield()

            mesh = asdf.triangulate()
            mesh.source = Struct(type=ASDF, file=path, depth=0)
            koko.FRAME.status = ''

            koko.FRAME.get_menu('View', '3D').Check(True)
            self.render_mode('3D')

            koko.GLCANVAS.load_mesh(mesh)
            koko.FAB.set_input(asdf)

        elif path[-4:] == '.vol':
            self.mode = 'vol'
            koko.IMPORT.set_target(self.directory, self.filename)

################################################################################

    def open(self, event=None):
        """ @brief Open a file dialog to get a target, then load it.
        """
        # Open a file dialog to get target
        if self.saved or dialogs.warn_changes():
            df = dialogs.open_file(self.directory)
            if df[1] != '':
                self.directory, self.filename = df
                self.load()

################################################################################

    def exit(self, event=None):
        """ @brief Warns of unsaved changes then exits.
        """
        if self.saved or dialogs.warn_changes():
            koko.FRAME.Destroy()

            # Delete these objects to avoid errors due to deletion order
            # during Python's cleanup stage
            del koko.FRAME
            del koko.EDITOR
            del koko.CANVAS
            del koko.GLCANVAS

################################################################################

    def snap_bounds(self, event=None):
        if koko.CANVAS.IsShown():
            koko.CANVAS.snap_bounds()
        if koko.GLCANVAS.IsShown():
            koko.GLCANVAS.snap_bounds()

    def snap_axis(self, event=None):
        axis = koko.FRAME.GetMenuBar().FindItemById(event.GetId()).GetLabel()
        if koko.CANVAS.IsShown():
            koko.CANVAS.snap_axis(axis)
        if koko.GLCANVAS.IsShown():
            koko.GLCANVAS.snap_axis(axis)

################################################################################

    def mark_changed_design(self, event=None):
        ''' Mark that the design needs to be re-evaluated and re-rendered.'''
        self.reeval_required = True

    def mark_changed_view(self, event=None):
        ''' Mark that the design needs to be re-rendered
            (usually because of a view change) '''

        self.render_required = True


################################################################################

    def idle(self, event=None):

        # Check the threads and clear out any that are dead
        koko.TASKS.join_threads()

        # Snap the bounds to the math file if this was the first render.
        if koko.TASKS.cached_cad and self.first_render:
            koko.CANVAS.snap_bounds()
            koko.GLCANVAS.snap_bounds()
            self.first_render = False
            self.render_required = True

        # We can't render until we have a valid math file
        if self.render_required and not koko.TASKS.cached_cad:
            self.render_required = False
            self.reeval_required = True

        # Recalculate math file then render
        if self.reeval_required:
            if self.mode == 'cad':  self.reeval()
            self.reeval_required = False
            self.render_required = False

        # Render given valid math file
        if self.render_required:
            if self.mode == 'cad':  self.render()
            self.render_required = False

        koko.TASKS.refine()


################################################################################

    def render(self):
        ''' Render the image, given the existing math file.'''
        koko.TASKS.render(koko.CANVAS.view)

    def reeval(self):
        ''' Render the image, calculating a new math file.'''
        koko.TASKS.render(koko.CANVAS.view,
                          script=koko.EDITOR.text)


    def render_mode(self, event):
        if type(event) is str:
            t = event
        else:
            t = koko.FRAME.GetMenuBar().FindItemById(event.GetId()).GetLabel()

        shading = koko.FRAME.get_menu('View', 'Shading mode')

        if '3D' in t:
            for s in shading:   s.Enable(True)
            koko.CANVAS.Hide()
            if not koko.GLCANVAS.IsShown():
                koko.GLCANVAS.snap = True
                self.reeval_required = True
            koko.GLCANVAS.Show()
        elif '2D' in t:
            for s in shading:   s.Enable(False)
            koko.GLCANVAS.Hide()
            koko.CANVAS.snap = not koko.CANVAS.IsShown()
            koko.CANVAS.Show()
        elif 'Both' in t:
            for s in shading:   s.Enable(True)
            koko.CANVAS.snap   = not koko.CANVAS.IsShown()
            koko.GLCANVAS.snap = not koko.GLCANVAS.IsShown()
            koko.CANVAS.Show()
            koko.GLCANVAS.Show()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

        self.mark_changed_view()

################################################################################

    def export(self, event):
        ''' General-purpose export callback.  Decides which export
            command to call based on the menu item text.'''

        item = koko.FRAME.GetMenuBar().FindItemById(event.GetId())
        filetype = item.GetLabel()

        if   self.mode == 'cad':    self.export_from_cad(filetype)
        elif self.mode == 'asdf':   self.export_from_asdf(filetype)

    def export_from_asdf(self, filetype):
        asdf = koko.FAB.panels[0].input

        if filetype == '.stl':
            kwargs = {}
        elif filetype == '.png':
            dlg = dialogs.RenderDialog('.png export', asdf)
            if dlg.ShowModal() == wx.ID_OK:
                kwargs = dlg.results
            else:
                kwargs = None
            dlg.Destroy()
        elif filetype == '.asdf':
            kwargs = {}

        if kwargs is None:  return

        # Open up a save as dialog to get the export target
        df = dialogs.save_as(self.directory, extension=filetype)
        if df[1] == '':     return
        path = os.path.join(*df)

        koko.TASKS.export(asdf, path, **kwargs)


    def export_from_cad(self, filetype):
        cad = koko.TASKS.cached_cad

        if 'failed' in koko.FRAME.status:
            dialogs.warning('Design has errors!  Export failed.')
            return
        elif cad is None:
            dialogs.warning('Design needs to be rendered before exporting!  Export failed')
            return
        elif koko.TASKS.export_task:
            dialogs.warning('Export already in progress.')
            return
        elif filetype in ['.png','.svg'] and any(
                getattr(cad,b) is None
                for b in ['xmin','xmax','ymin','ymax']):
            dialogs.warning('Design needs to be bounded along X and Y axes ' +
                            'to export %s' % filetype)
            return
        elif filetype in ['.stl','.asdf'] and any(
                getattr(cad,b) is None
                for b in ['xmin','xmax','ymin','ymax','zmin','zmax']):
            dialogs.warning('Design needs to be bounded on all axes '+
                            'to export %s' % filetype)
            return
        elif filetype == '.svg' and cad.zmin is not None:
            dialogs.warning('Design must be flat (without z bounds)'+
                            ' to export .svg')
            return


        # Open up a dialog box to get the export resolution or settings
        if filetype == '.asdf':
            dlg = dialogs.ResolutionDialog(10, '.asdf export', cad)
            key = None
        elif filetype == '.stl':
            dlg = dialogs.ResolutionDialog(10, '.stl export',
                                   cad, 'Watertight')
            key = 'use_cms'
        elif filetype == '.png':
            dlg = dialogs.ResolutionDialog(
                10, '.stl export', cad, 'Heightmap'
            )
            key = 'make_heightmap'
        elif filetype in '.svg':
            dlg = dialogs.ResolutionDialog(
                10, '.svg export', cad
            )
            key = None
        elif filetype == '.dot':
            dlg = dialogs.CheckDialog('.dot export', 'Packed arrays')
            key = 'dot_arrays'
        else:
            dlg = None

        if dlg:
            if dlg.ShowModal() == wx.ID_OK:
                kwargs = {}
                if isinstance(dlg, dialogs.ResolutionDialog):
                    kwargs.update({'resolution': float(dlg.result)})
                if key:
                    kwargs.update({key: dlg.checked})
            else:
                kwargs = None
            dlg.Destroy()
        else:
                kwargs = {}

        # If we didn't get a valid resolution, then abort
        if kwargs is None:  return

        # Open up a save as dialog to get the export target
        df = dialogs.save_as(self.directory, extension=filetype)
        if df[1] == '':     return
        path = os.path.join(*df)

        koko.TASKS.export(cad, path, **kwargs)

################################################################################

    def show_library(self, event):

        item = koko.FRAME.GetMenuBar().FindItemById(event.GetId())
        name = item.GetLabel()

        if koko.BUNDLED:
            path = koko.BASE_DIR + name.split('.')[-1] + '.py'
        else:
            v = {}
            exec('import %s as module' % name.replace('koko.',''), v)
            path = v['module'].__file__.replace('.pyc','.py')

        dialogs.TextFrame(name, path)

########NEW FILE########
__FILENAME__ = asdf
import ctypes

from koko.c.interval import Interval

class ASDF(ctypes.Structure):
    """ @class ASDF
        @brief C data structure describing an ASDF.
    """
    pass
ASDF._fields_ = [('state', ctypes.c_int),
                 ('X', Interval), ('Y', Interval), ('Z', Interval),
                 ('branches', ctypes.POINTER(ASDF)*8),
                 ('d', ctypes.c_float*8),
                 ('data', ctypes.c_void_p)]

########NEW FILE########
__FILENAME__ = interval
import ctypes

class Interval(ctypes.Structure):
    """ @class Interval
        @brief Interval containing upper and lower bounds with overloaded arithmetic operators
    """
    _fields_ = [('lower', ctypes.c_float),
                ('upper', ctypes.c_float)]

    def __init__(self, lower=0, upper=None):
        """ @brief Constructor for Interval
            @param lower Lower bound
            @param upper Upper bound (if None, lower is used)
        """
        if upper is None:   upper = lower
        if isinstance(lower, Interval):
            lower, upper = lower.lower, lower.upper
        ctypes.Structure.__init__(self, lower, upper)

    def __str__(self):
        return "[%g, %g]" % (self.lower, self.upper)
    def __repr__(self):
        return "Interval(%g, %g)" % (self.lower, self.upper)
    def __add__(self, rhs):     return libfab.add_i(self, Interval(rhs))
    def __radd__(self, lhs):    return libfab.add_i(Interval(lhs), self)
    def __sub__(self, rhs):     return libfab.sub_i(self, Interval(rhs))
    def __rsub__(self, lhs):    return libfab.sub_i(Interval(lhs), self)
    def __mul__(self, rhs):     return libfab.mul_i(self, Interval(rhs))
    def __rmul__(self, lhs):    return libfab.mul_i(Interval(lhs), self)
    def __div__(self, rhs):     return libfab.div_i(self, Interval(rhs))
    def __rdiv__(self, lhs):    return libfab.div_i(Interval(lhs), self)
    def __neg__(self):          return libfab.neg_i(self)

    @staticmethod
    def sqrt(i):    return libfab.sqrt_i(i)
    @staticmethod
    def pow(i, e):  return libfab.pow_i(i, e)
    @staticmethod
    def sin(i):     return libfab.sin_i(i)
    @staticmethod
    def cos(i):     return libfab.cos_i(i)
    @staticmethod
    def tan(i):     return libfab.tan_i(i)

    def copy(self):
        return Interval(self.lower, self.upper)

from koko.c.libfab import libfab

########NEW FILE########
__FILENAME__ = libfab
""" Module to import the libfab shared C library. """

import ctypes
import os
import sys

# Here are a few likely filenames
base = os.path.abspath(sys.argv[0])
if sys.argv[0]: base = os.path.dirname(base)

libname = 'libfab' + ('.dylib' if 'Darwin' in os.uname() else '.so')
filenames =[
    os.path.join(base, 'libfab/', libname),
    os.path.join(base, '../lib/', libname),
    os.path.join(base, '../Frameworks/', libname),
    libname
]

for filename in filenames:
    try:
        libfab = ctypes.CDLL(filename)
    except OSError:
        continue
    else:
        break
else:
    print 'Error: libfab not found'
    sys.exit(1)


# Helper functions for pointer and pointer to pointer
def p(t):   return ctypes.POINTER(t)
def pp(t):  return p(p(t))

################################################################################

# util/region.h
from region import Region

libfab.split.argtypes = [Region, p(Region), ctypes.c_int]
libfab.split.restype  = ctypes.c_int

libfab.split_xy.argtypes = [Region, p(Region), ctypes.c_int]
libfab.split_xy.restype  = ctypes.c_int

libfab.octsect.argtypes = [Region, Region*8]
libfab.octsect.restype  = ctypes.c_uint8

libfab.octsect_overlap.argtypes = [Region, Region*8]
libfab.octsect_overlap.restype  = ctypes.c_uint8

libfab.build_arrays.argtypes = [p(Region)] + [ctypes.c_float]*6
libfab.free_arrays.argtypes  = [p(Region)]

# util/vec3f.h
from vec3f import Vec3f
libfab.deproject.argtypes = [Vec3f, ctypes.c_float*4]
libfab.deproject.restype  =  Vec3f

libfab.project.argtypes = [Vec3f, ctypes.c_float*4]
libfab.project.restype  =  Vec3f

################################################################################

class MathTreeP(ctypes.c_void_p):   pass
class PackedTreeP(ctypes.c_void_p): pass

# tree/solver.h
libfab.render8.argtypes  = [
    PackedTreeP, Region, pp(ctypes.c_uint8), p(ctypes.c_int)
]
libfab.render16.argtypes = [
    PackedTreeP, Region, pp(ctypes.c_uint16), p(ctypes.c_int)
]

# tree/tree.h

libfab.free_tree.argtypes = [MathTreeP]

libfab.print_tree.argtypes = [MathTreeP]
libfab.fdprint_tree.argtypes = [MathTreeP, ctypes.c_int]
libfab.fdprint_tree_verbose.argtypes = [MathTreeP, ctypes.c_int]

libfab.clone_tree.argtypes = [MathTreeP]
libfab.clone_tree.restype  =  MathTreeP

libfab.count_nodes.argtypes = [MathTreeP]
libfab.count_nodes.restype  = ctypes.c_uint

libfab.dot_arrays.argtypes = [MathTreeP, p(ctypes.c_char)]
libfab.dot_tree.argtypes = [MathTreeP, p(ctypes.c_char)]

# tree/packed.h
libfab.make_packed.argtypes = [MathTreeP]
libfab.make_packed.restype  =  PackedTreeP

libfab.free_packed.argtypes = [PackedTreeP]

# tree/eval.h
from interval import Interval

libfab.eval_i.argtypes = [PackedTreeP, Interval, Interval, Interval]
libfab.eval_i.restype  =  Interval

# tree/parser.h
libfab.parse.argtypes = [p(ctypes.c_char)]
libfab.parse.restype  =  MathTreeP

################################################################################

# asdf/asdf.h
from koko.c.asdf import ASDF

libfab.build_asdf.argtypes = [
    PackedTreeP, Region, ctypes.c_bool, p(ctypes.c_int)
]
libfab.build_asdf.restype  =  p(ASDF)

libfab.free_asdf.argtypes = [p(ASDF)]

libfab.asdf_root.argtypes = [PackedTreeP, Region]
libfab.asdf_root.restype  =  p(ASDF)

libfab.count_leafs.argtypes = [p(ASDF)]
libfab.count_leafs.restype  = ctypes.c_int

libfab.count_cells.argtypes = [p(ASDF)]
libfab.count_cells.restype = ctypes.c_int

libfab.asdf_scale.argtypes = [p(ASDF), ctypes.c_float]

libfab.asdf_slice.argtypes = [p(ASDF), ctypes.c_float]
libfab.asdf_slice.restype  =  p(ASDF)

libfab.find_dimensions.argtypes = [p(ASDF)] + [p(ctypes.c_int)]*3
libfab.get_d_from_children.argtypes = [p(ASDF)]

libfab.interpolate.argtypes = [p(ctypes.c_float)] + [ctypes.c_float]*9
libfab.interpolate.restype  = ctypes.c_float

libfab.get_depth.argtypes = [p(ASDF)]
libfab.get_depth.restype  = ctypes.c_int

libfab.asdf_get_max.argtypes = [p(ASDF)]
libfab.asdf_get_max.restype  = ctypes.c_float

libfab.asdf_get_min.argtypes = [p(ASDF)]
libfab.asdf_get_min.restype  = ctypes.c_float

libfab.asdf_histogram.argtypes = [
    p(ASDF), p(ctypes.c_int*4), ctypes.c_int
]

libfab.simplify.argtypes = [p(ASDF), ctypes.c_bool]


# asdf/import.h
libfab.import_vol_region.argtypes = (
    [p(ctypes.c_char)] + [ctypes.c_int]*3 +
    [Region, ctypes.c_int, ctypes.c_float,
     ctypes.c_bool, ctypes.c_bool]
)
libfab.import_vol_region.restype  = p(ASDF)

libfab.import_vol.argtypes = [
    p(ctypes.c_char), ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_float, ctypes.c_float, ctypes.c_bool, ctypes.c_bool
]
libfab.import_vol.restype  = p(ASDF)

libfab.import_lattice.argtypes = [
    pp(ctypes.c_float), ctypes.c_int, ctypes.c_int,
    ctypes.c_float, ctypes.c_float, ctypes.c_bool
]
libfab.import_lattice.restype = p(ASDF)


# asdf/render.h
libfab.render_asdf.argtypes = [
    p(ASDF), Region, ctypes.c_float*4, pp(ctypes.c_uint16)
]
libfab.render_asdf_shaded.argtypes = [
    p(ASDF), Region, ctypes.c_float*4,
    pp(ctypes.c_uint16), pp(ctypes.c_uint16), pp(ctypes.c_uint8*3)
]
libfab.draw_asdf_cells.argtypes = [p(ASDF), Region, pp(ctypes.c_uint8*3)]

libfab.draw_asdf_distance.argtypes = [
    p(ASDF), Region, ctypes.c_float, ctypes.c_float, pp(ctypes.c_uint16)
]


# asdf/file_io.h
libfab.asdf_write.argtypes = [p(ASDF), p(ctypes.c_char)]

libfab.asdf_read.argtypes = [p(ctypes.c_char)]
libfab.asdf_read.restype  =  p(ASDF)


# asdf/triangulate.h
from koko.c.mesh import Mesh
libfab.triangulate.argtypes = [
    p(ASDF), p(ctypes.c_int)
]
libfab.triangulate.restype = p(Mesh)

# asdf/cms.c
libfab.triangulate_cms.argtypes = [p(ASDF)]
libfab.triangulate_cms.restype = p(Mesh)

# asdf/contour.h
from koko.c.path import Path

libfab.contour.argtypes = [
    p(ASDF), p(pp(Path)), p(ctypes.c_int)
]
libfab.contour.restype  = ctypes.c_int


# asdf/distance.c
libfab.asdf_offset.argtypes = [
    p(ASDF), ctypes.c_float, ctypes.c_float
]
libfab.asdf_offset.restype  =  p(ASDF)

################################################################################

# cam/slices.h
libfab.find_support.argtypes = [
    ctypes.c_int, ctypes.c_int, pp(ctypes.c_uint8), pp(ctypes.c_uint8)
]
libfab.colorize_slice.argtypes = [
    ctypes.c_int, ctypes.c_int, pp(ctypes.c_uint8), pp(ctypes.c_uint8*3)
]
libfab.next_slice.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float,
    pp(ctypes.c_uint8), pp(ctypes.c_uint8)
]


# cam/distance.h
libfab.distance_transform1.argtypes = (
    [ctypes.c_int]*4 +
    [pp(ctypes.c_uint8), pp(ctypes.c_uint32)]
)

libfab.distance_transform2.argtypes = (
    [ctypes.c_int]*3 +
    [ctypes.c_float, pp(ctypes.c_uint32), pp(ctypes.c_float)]
)

libfab.distance_transform.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float,
    pp(ctypes.c_uint8), pp(ctypes.c_float)
]

# formats/png.c
libfab.save_png16L.argtypes = [p(ctypes.c_char), ctypes.c_int,
                                ctypes.c_int, ctypes.c_float*6,
                                pp(ctypes.c_uint16)]

libfab.count_by_color.argtypes = [p(ctypes.c_char), ctypes.c_int,
                                   ctypes.c_int, ctypes.c_uint32,
                                   p(ctypes.c_uint32)]

libfab.depth_blit.argtypes = (
    [pp(ctypes.c_uint8), pp(ctypes.c_uint8), pp(ctypes.c_uint8*3)] +
    [ctypes.c_int]*4 + [ctypes.c_float]*3
)


libfab.load_png_stats.argtypes = (
    [p(ctypes.c_char)] + [p(ctypes.c_int)]*2 + [p(ctypes.c_float)]*3
)

libfab.load_png.argtypes = [p(ctypes.c_char), pp(ctypes.c_uint16)]

# formats/mesh.h
libfab.free_mesh.argtypes = [p(Mesh)]

libfab.increase_indices.argtypes = [p(Mesh), ctypes.c_uint32]

libfab.save_mesh.argtypes = [p(ctypes.c_char), p(Mesh)]

libfab.load_mesh.argtypes = [p(ctypes.c_char)]
libfab.load_mesh.restype = p(Mesh)

libfab.merge_meshes.argtypes = [ctypes.c_uint32, pp(Mesh)]
libfab.merge_meshes.restype = p(Mesh)

# formats/stl.c
libfab.save_stl.argtypes = [p(Mesh), p(ctypes.c_char)]

libfab.load_stl.argtypes = [p(ctypes.c_char)]
libfab.load_stl.restype = p(Mesh)


# cam/toolpath.c
from koko.c.path import Path

libfab.find_paths.argtypes = [
    ctypes.c_int, ctypes.c_int, pp(ctypes.c_float),
    ctypes.c_float, ctypes.c_int, p(ctypes.c_float), p(pp(Path))
]
libfab.find_paths.restype = ctypes.c_int

libfab.free_paths.argtypes = [pp(Path), ctypes.c_int]

libfab.sort_paths.argtypes = [pp(Path), ctypes.c_int, p(ctypes.c_int)]

libfab.finish_cut.argtypes = (
    [ctypes.c_int]*2+[pp(ctypes.c_uint16)]+[ctypes.c_float]*4+
    [ctypes.c_int, p(pp(Path))]
)

del p, pp

########NEW FILE########
__FILENAME__ = mesh
import ctypes

from koko.c.interval import Interval

class Mesh(ctypes.Structure):
    """ @class Mesh
        @brief C data structure describing a Mesh
    """
    _fields_ = [
        ('vdata', ctypes.POINTER(ctypes.c_float)),
        ('vcount', ctypes.c_uint32),
        ('valloc', ctypes.c_uint32),
        ('tdata', ctypes.POINTER(ctypes.c_uint32)),
        ('tcount', ctypes.c_uint32),
        ('talloc', ctypes.c_uint32),
        ('X', Interval), ('Y', Interval), ('Z', Interval)
    ]


########NEW FILE########
__FILENAME__ = multithread
import threading
from thread import LockType

def __monitor(interrupt, halt):
    """ @brief Waits for interrupt, then sets halt to 1
        @param interrupt threading.Event on which we wait
        @param halt ctypes.c_int used as a flag elsewhere
    """
    interrupt.wait()
    halt.value = 1


def multithread(target, args, interrupt=None, halt=None):
    """ @brief Runs a process on multiple threads.
        @details Must be called with both interrupt and halt or neither.  Interrupt is cleared before returning.
        @param target Callable function
        @param args List of argument tuples (one tuple per thread)
        @param interrupt threading.Event to halt thread or None
        @param halt ctypes.c_int used as an interrupt flag by target
    """

    if (halt is None) ^ (interrupt is None):
        raise ValueError('multithread must be invoked with both halt and interrupt (or neither)')

    threads = [threading.Thread(target=target, args=a) for a in args]

    if interrupt:
        m = threading.Thread(target=__monitor, args=(interrupt, halt))
        m.daemon = True
        m.start()

    for t in threads:   t.daemon = True
    for t in threads:   t.start()
    for t in threads:   t.join()

    if interrupt:
        interrupt.set()
        m.join()
        interrupt.clear()


def monothread(target, args, interrupt=None, halt=None):
    """ @brief Runs a process on a single thread
        @details Must be called with both interrupt and halt or neither.  Interrupt is cleared before returning.
        @param target Callable function
        @param args Argument tuples
        @param interrupt threading.Event to halt thread or None
        @param halt ctypes.c_int used as an interrupt flag by target
    """
    if (halt is None) ^ (interrupt is None):
        raise ValueError('monothread must be invoked with both halt and interrupt (or neither)')

    if interrupt:
        m = threading.Thread(target=__monitor, args=(interrupt, halt))
        m.daemon = True
        m.start()

    result = target(*args)

    if interrupt:
        interrupt.set()
        m.join()
        interrupt.clear()

    return result

def threadsafe(f):
    ''' A decorator that locks the arguments to a function,
        invokes the function, then unlocks the arguments and
        returns.'''
    def wrapped(*args, **kwargs):
        for a in set(list(args) + kwargs.values()):
            if hasattr(a, 'lock') and LockType and isinstance(a.lock, LockType):
                a.lock.acquire()
        result = f(*args, **kwargs)
        for a in set(list(args) + kwargs.values()):
            if hasattr(a, 'lock') and LockType and isinstance(a.lock, LockType):
                a.lock.release()
        return result
    return wrapped

########NEW FILE########
__FILENAME__ = path
import ctypes

class Path(ctypes.Structure):
    """ @class Path
        @brief C data structure containing a doubly linked list.
    """
    def __repr__(self):
        return 'pt(%g, %g) at %s' % \
            (self.x, self.y, hex(ctypes.addressof(self)))
    def __eq__(self, other):
        if other is None:   return False
        return ctypes.addressof(self) == ctypes.addressof(other)
    def __ne__(self, other):
        if other is None:   return False
        return not (self == other)

def p(t):   return ctypes.POINTER(t)
def pp(t):  return p(p(t))

Path._fields_ = [
    ('prev', p(Path)), ('next', p(Path)),
    ('x', ctypes.c_float), ('y', ctypes.c_float), ('z', ctypes.c_float),
    ('ptr', pp(Path*2))
]

del p, pp

########NEW FILE########
__FILENAME__ = region
import ctypes

class Region(ctypes.Structure):
    ''' @class Region
        @brief Class containing lattice bounds and ticks.
        @details Replicates C Region class.
    '''
    _fields_ = [('imin', ctypes.c_uint32),
                ('jmin', ctypes.c_uint32),
                ('kmin', ctypes.c_uint32),
                ('ni', ctypes.c_uint32),
                ('nj', ctypes.c_uint32),
                ('nk', ctypes.c_uint32),
                ('voxels', ctypes.c_uint64),
                ('X', ctypes.POINTER(ctypes.c_float)),
                ('Y', ctypes.POINTER(ctypes.c_float)),
                ('Z', ctypes.POINTER(ctypes.c_float)),
                ('L', ctypes.POINTER(ctypes.c_uint16))]

    def __init__(self, (xmin, ymin, zmin)=(0.,0.,0.),
                       (xmax, ymax, zmax)=(0.,0.,0.),
                       scale=100., dummy=False, depth=None):
        """ @brief Creates an array.
        """

        dx = float(xmax - xmin)
        dy = float(ymax - ymin)
        dz = float(zmax - zmin)

        if depth is not None:
            scale = 3*(2**6)* 2**(depth/3.) / (dx+dy+dz)

        ni = max(int(round(dx*scale)), 1)
        nj = max(int(round(dy*scale)), 1)
        nk = max(int(round(dz*scale)), 1)

        # Dummy assignments so that Doxygen recognizes these instance variables
        self.ni = self.nj = self.nk = 0
        self.imin = self.jmin = self.kmin = 0
        self.voxels = 0
        self.X = self.Y = self.Z = self.L = None

        ## @var ni
        # Number of ticks along x axis
        ## @var nj
        #Number of points along y axis
        ## @var nk
        # Number of points along z axis

        ## @var imin
        # Minimum i coordinate in global lattice space
        ## @var jmin
        # Minimum j coordinate in global lattice space
        ## @var kmin
        # Minimum k coordinate in global lattice space

        ## @var voxels
        # Voxel count in this section of the lattice

        ## @var X
        # Array of ni+1 X coordinates as floating-point values
        ## @var Y
        # Array of nj+1 Y coordinates as floating-point values
        ## @var Z
        # Array of nk+1 Z coordinates as floating-point values
        ## @var L
        # Array of nk+1 luminosity values as 16-bit integers

        ## @var free_arrays
        # Boolean indicating whether this region dynamically allocated
        # the X, Y, Z, and L arrays.
        #
        # Determines whether these arrays are
        # freed when the structure is deleted.

        ctypes.Structure.__init__(self,
                                  0, 0, 0,
                                  ni, nj, nk,
                                  ni*nj*nk,
                                  None, None, None, None)

        if dummy is False:
            libfab.build_arrays(ctypes.byref(self),
                                 xmin, ymin, zmin,
                                 xmax, ymax, zmax)
            self.free_arrays = True
        else:
            self.free_arrays = False

    def __del__(self):
        """ @brief Destructor for Region
            @details Frees allocated arrays if free_arrays is True
        """
        if hasattr(self, 'free_arrays') and self.free_arrays and libfab is not None:
            libfab.free_arrays(self)

    def __repr__(self):
        return ('[(%g, %g), (%g, %g), (%g, %g)]' %
            (self.imin, self.imin + self.ni,
             self.jmin, self.jmin + self.nj,
             self.kmin, self.kmin + self.nk))

    def split(self, count=2):
        """ @brief Repeatedly splits the region along its longest axis
            @param count Number of subregions to generate
            @returns List of regions (could be fewer than requested if the region is indivisible)
        """
        L = (Region*count)()
        count = libfab.split(self, L, count)

        return L[:count]

    def split_xy(self, count=2):
        """ @brief Repeatedly splits the region on the X and Y axes
            @param count Number of subregions to generate
            @returns List of regions (could be fewer than requested if the region is indivisible)
        """
        L = (Region*count)()
        count = libfab.split_xy(self, L, count)

        return L[:count]

    def octsect(self, all=False, overlap=False):
        """ @brief Splits the region into eight subregions
            @param all If true, returns an 8-item array with None in the place of missing subregions.  Otherwise, the output array is culled to only include valid subregions.
            @returns An array of containing regions (and Nones if all is True and the region was indivisible along some axis)
        """
        L = (Region*8)()
        if overlap:
            bits = libfab.octsect_overlap(self, L)
        else:
            bits = libfab.octsect(self, L)

        if all:
            return [L[i] if (bits & (1 << i)) else None for i in range(8)]
        else:
            return [L[i] for i in range(8) if (bits & (1 << i))]


from koko.c.libfab import libfab
from koko.c.vec3f import Vec3f

########NEW FILE########
__FILENAME__ = vec3f
import ctypes
from math import sin, cos, radians, sqrt

class Vec3f(ctypes.Structure):
    """ @class Vec3f
        @brief Three-element vector with overloaded arithmetic operators.
    """
    _fields_ = [('x', ctypes.c_float),
                ('y', ctypes.c_float),
                ('z', ctypes.c_float)]
    def __init__(self, x=0., y=0., z=0.):
        try:                x = list(x)
        except TypeError:   ctypes.Structure.__init__(self, x, y, z)
        else:               ctypes.Structure.__init__(self, x[0], x[1], x[2])

    def __str__(self):
        return "(%g, %g, %g)" % (self.x, self.y, self.z)
    def __repr__(self):
        return "Vec3f(%g, %g, %g)" % (self.x, self.y, self.z)
    def __add__(self, rhs):
        return Vec3f(self.x + rhs.x, self.y + rhs.y, self.z + rhs.z)
    def __sub__(self, rhs):
        return Vec3f(self.x - rhs.x, self.y - rhs.y, self.z - rhs.z)
    def __div__(self, rhs):
        return Vec3f(self.x/rhs, self.y/rhs, self.z/rhs)
    def __neg__(self):
        return Vec3f(-self.x, -self.y, -self.z)
    def length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)
    def copy(self):
        return Vec3f(self.x, self.y, self.z)

    @staticmethod
    def M(alpha, beta):
        """ @brief Generates M matrix for libfab's project and deproject functions.
            @param alpha Rotation about z axis
            @param beta Rotation about x axis.
            @returns (cos(a), sin(a), cos(b), sin(b)) as float array
        """
        return (ctypes.c_float*4)(
            cos(radians(alpha)), sin(radians(alpha)),
            cos(radians(beta)),  sin(radians(beta))
        )

    def project(self, alpha, beta):
        """ @brief Transforms from cell frame to view frame.
            @param alpha Rotation about z axis
            @param beta Rotation about x axis.
            @returns Projected Vec3f object
        """
        return libfab.project(self, self.M(alpha, beta))

    def deproject(self, alpha, beta):
        """ @brief Transforms from view frame to cell frame.
            @param alpha Rotation about z axis
            @param beta Rotation about x axis.
            @returns Deprojected Vec3f object
        """
        return libfab.deproject(self, self.M(alpha, beta))

    def __iter__(self):
        """ @brief Iterates over (x, y, z) list
        """
        return [self.x, self.y, self.z].__iter__()

from koko.c.libfab import libfab

########NEW FILE########
__FILENAME__ = asdf
import  wx
import  wx.lib.stattext

import  os

import  koko
from    koko.struct     import Struct
from    koko.cam.panel  import FabPanel
from    koko.dialogs    import RescaleDialog

from    koko.fab.image import Image

class ASDFInputPanel(FabPanel):
    """ @class ASDFInputPanel   UI Panel for ASDF loaded from a file
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Input',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        text = wx.GridSizer(2, 2)

        self.file   = wx.StaticText(self, label='.asdf file')
        self.pix    = wx.StaticText(self)
        self.mms    = wx.StaticText(self)
        self.ins    = wx.StaticText(self)

        text.Add(self.file)
        text.Add(self.mms, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.pix, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.ins, flag=wx.ALIGN_LEFT|wx.EXPAND)

        sizer.Add(text, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        resize = wx.Button(self, label='Rescale')
        sizer.Add(resize, flag=wx.CENTER|wx.ALL, border=5)
        resize.Bind(wx.EVT_BUTTON, self.resize)

        self.SetSizerAndFit(sizer)


    @property
    def input(self):
        """ @brief Property returning self.asdf """
        return self.asdf


    def resize(self, event=None):
        """ @brief Allows user to resize asdf
            @details Opens a RescaleDialog and rescales the stored asdf, then updates the UI, retriangulates the displayed mesh.
        """
        dlg = RescaleDialog('Rescale ASDF', self.asdf)
        if dlg.ShowModal() == wx.ID_OK:
            self.asdf.rescale(float(dlg.result))

            mesh = self.asdf.triangulate()
            mesh.source = Struct(type=ASDF, file=self.asdf.filename, depth=0)
            koko.GLCANVAS.load_mesh(mesh)

            self.parent.invalidate()
            self.parent.update()
        dlg.Destroy()


    def update(self, input):
        """ @brief Updates this panel
            @param input Input ASDF
            @returns Dictionary with dx, dy, and dz values
        """

        ## @var asdf
        #   ASDF data structure
        self.asdf = input

        if self.asdf.filename:   file = os.path.split(self.asdf.filename)[1]
        else:                    file = 'Unknown .asdf file'
        self.file.SetLabel(file)

        self.pix.SetLabel('%i x %i x %i voxels' % self.asdf.dimensions)

        self.mms.SetLabel(
            '%.1f x %.1f x %.1f mm' %
            (self.asdf.dx, self.asdf.dy, self.asdf.dz)
        )

        self.ins.SetLabel(
            '%.2f x %.2f x %.2f"' %
            (self.asdf.dx/25.4, self.asdf.dy/25.4, self.asdf.dz/25.4)
        )
        return {'dx': self.asdf.dx, 'dy': self.asdf.dy, 'dz': self.asdf.dz}


    def run(self):
        """ @brief Returns a dictionary with the stored asdf
        """
        return {'asdf': self.asdf}

################################################################################

class ASDFImagePanel(FabPanel):
    ''' @class ASDFImagePanel Panel to convert an ASDF data structure into a png.
    '''
    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('Lattice', [
            ('Resolution (pixels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.img = Image(0,0)

    def update(self, dx, dy, dz):
        """ @brief Updates UI panel with dimensions
            @param dx   x dimension (mm)
            @param dy   y dimension (mm)
            @param dz   z dimension (mm)
        """
        try:
            scale = float(self.res.GetValue())
        except ValueError:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel(
                'Resolution (pixels/mm)\n%i x %i x %i' %
                (max(1, dx*scale),
                 max(1, dy*scale),
                 max(1, dz*scale))
            )
        return {'threeD': True}

    def run(self, asdf):
        """ @brief Renders an ASDF to an image
            @details Image is saved to self.img and appended to dictionary
            @param args Dictionary with key 'asdf'
            @returns Dictionary updated with key 'img'
        """
        koko.FRAME.status = 'Generating image'

        values = self.get_values()
        if not values:  return False

        # Render the asdf into an image
        self.img = asdf.render(resolution=values['res'])
        koko.FRAME.status = ''

        return {'img': self.img}

################################################################################

from koko.fab.asdf          import ASDF
from koko.cam.path_panels   import PathPanel, ContourPanel, MultiPathPanel

TYPE = ASDF
WORKFLOWS = {
    None:           (ASDFInputPanel,),
    PathPanel:      (ASDFInputPanel, ASDFImagePanel,),
    MultiPathPanel: (ASDFInputPanel,),
}

################################################################################

########NEW FILE########
__FILENAME__ = cad
import wx
import wx.lib.stattext

import  koko

from    koko.struct     import Struct
from    koko.dialogs    import error
from    koko.fab.image  import Image
from    koko.c.region   import Region

from    koko.cam.panel  import FabPanel

################################################################################

class CadInputPanel(FabPanel):
    """ @class CadInputPanel  Input FabPanel for script-based workflow
    """

    def __init__(self, parent):
        """ @brief Initializes the panel
            @param Parent UI panel
        """
        FabPanel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Input',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
        self.label = wx.StaticText(self, label='.cad file')
        sizer.Add(self.label,
                  flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        self.SetSizerAndFit(sizer)

    @property
    def input(self):
        """ @brief Property returning self.cad """
        return self.cad

    def update(self, input):
        """ @brief Updates the current cad structure
            @param input Input cad structure
            @returns Dictionary with 'cad' populated
        """

        ## @var cad
        # FabVars data structure
        self.cad = input

        if self.cad.dx: x = '%g' % (self.cad.dx*self.cad.mm_per_unit)
        else:           x = '?'
        if self.cad.dy: y = '%g' % (self.cad.dy*self.cad.mm_per_unit)
        else:           y = '?'
        if self.cad.dz: z = '%g' % (self.cad.dz*self.cad.mm_per_unit)
        else:           z = 0

        self.label.SetLabel('.cad file     (%s x %s x %s mm)' %  (x, y, z))
        return {'cad': self.cad}

    def run(self):
        """ @brief Returns a dictionary with the stored cad structure
        """
        koko.FRAME.status = 'Checking cad expression'
        if not bool(self.cad.shape.ptr):
            wx.CallAfter(self.label.SetBackgroundColour, '#853535')
            wx.CallAfter(self.label.SetForegroundColour, '#ffffff')
            koko.FRAME.status = 'Error: Failed to parse math expression!'
            return False
        if self.cad.dx is None or self.cad.dy is None:
            wx.CallAfter(self.label.SetBackgroundColour, '#853535')
            wx.CallAfter(self.label.SetForegroundColour, '#ffffff')
            koko.FRAME.status = 'Error: invalid XY bounds on expression'
            return False
        return {'cad': self.cad}

################################################################################

class CadImgPanel(FabPanel):
    """ @class CadImgPanel  Panel to convert cad structure to image
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('Lattice', [
            ('Resolution (pixels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.img = Image(0,0)


    def update(self, cad):
        """ @brief Updates displayed dimensions
            @param cad cad data structure
            @returns Dictionary with 'threeD' defined
        """
        try:
            scale = float(self.res.GetValue()) * cad.mm_per_unit
        except ValueError:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n%i x %i x %i' %
                                (max(1, cad.dx*scale if cad.dx else 1),
                                 max(1, cad.dy*scale if cad.dy else 1),
                                 max(1, cad.dz*scale if cad.dz else 1)))
        return {'threeD': cad.dz}


    def run(self, cad):
        """ @brief Generates image
            @param cad Input cad data structure
            @returns Dictionary with 'img' defined
        """
        koko.FRAME.status = 'Generating image'

        values = self.get_values()
        if not values:  return False

        # Render the expression into an image
        expr = cad.shape

        zmin = expr.zmin if expr.zmin else 0
        zmax = expr.zmax if expr.zmax else 0
        dz   = zmax - zmin

        border = cad.border
        region = Region( (expr.xmin-border*expr.dx,
                          expr.ymin-border*expr.dy,
                          zmin-border*dz),
                         (expr.xmax+border*expr.dx,
                          expr.ymax+border*expr.dy,
                          zmax+border*dz),
                          values['res']*cad.mm_per_unit)

        self.img = expr.render(region=region,
                               mm_per_unit=cad.mm_per_unit)
        koko.FRAME.status = ''

        return {'img': self.img}


class CadASDFPanel(FabPanel):
    """ @class CadASDFPanel  Panel to convert cad structure to ASDF
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)
        self.construct('ASDF', [
            ('Resolution (voxels/mm)\n', 'res', float, lambda f: f > 0)])

        self.res.Bind(wx.EVT_TEXT, self.parent.update)


    def update(self, cad):
        """ @brief Updates size labels
            @param cad Input cad structure
            @returns Dictionary with dx, dy, dz values
        """
        try:
            scale = float(self.res.GetValue()) * cad.mm_per_unit
        except ValueError:
            self.labels[0].SetLabel('Resolution (voxels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel('Resolution (voxels/mm)\n%i x %i x %i' %
                                (max(1, cad.dx*scale if cad.dx else 1),
                                 max(1, cad.dy*scale if cad.dy else 1),
                                 max(1, cad.dz*scale if cad.dz else 1)))

        # Return ASDF structure with correct dimensions
        return {
            'dx': cad.dx*cad.mm_per_unit,
            'dy': cad.dy*cad.mm_per_unit,
            'dz': cad.dz*cad.mm_per_unit,
        }


    def run(self, cad):
        """ @brief Generates ASDF from cad structure
            @param cad Input cad data structure
            @returns Dictionary with 'asdf' defined
        """
        koko.FRAME.status = 'Generating ASDF'

        values = self.get_values()
        if not values:  return False

        # Render the expression into an image
        expr = cad.shape

        zmin = expr.zmin if expr.zmin else 0
        zmax = expr.zmax if expr.zmax else 0
        dz   = zmax - zmin

        border = cad.border
        region = Region( (expr.xmin-border*expr.dx,
                          expr.ymin-border*expr.dy,
                          zmin-border*dz),
                         (expr.xmax+border*expr.dx,
                          expr.ymax+border*expr.dy,
                          zmax+border*dz),
                          values['res']*cad.mm_per_unit)

        self.asdf = expr.asdf(
            region=region, mm_per_unit=cad.mm_per_unit
        )

        koko.FRAME.status = ''

        return {'asdf': self.asdf}

################################################################################

from koko.fab.fabvars       import FabVars
from koko.cam.path_panels   import PathPanel, ContourPanel, MultiPathPanel

TYPE = FabVars
WORKFLOWS = {
    None:           (CadInputPanel,),
    PathPanel:      (CadInputPanel, CadImgPanel),
    ContourPanel:   (CadInputPanel, CadImgPanel),
    MultiPathPanel: (CadInputPanel, CadASDFPanel),
}

################################################################################

########NEW FILE########
__FILENAME__ = image
import wx
import wx.lib.stattext

import os

import  koko
from    koko.cam.panel import FabPanel

class ImageInputPanel(FabPanel):
    """ @class ImageInputPanel  Input FabPanel for Image-based workflow
    """

    def __init__(self, parent):
        """ @brief Initializes the panel
            @param Parent UI panel
        """

        FabPanel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Input',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        text = wx.GridSizer(2, 2)

        ## @var file
        # UI label with filename
        self.file   = wx.StaticText(self, label='.png file')

        ## @var pix
        # UI label with size in pixels
        self.pix    = wx.StaticText(self)

        ## @var file
        # UI label with size in mms
        self.mms    = wx.StaticText(self)

        ## @var file
        # UI label with size in inches
        self.ins    = wx.StaticText(self)

        text.Add(self.file)
        text.Add(self.mms, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.pix, flag=wx.ALIGN_LEFT|wx.EXPAND)
        text.Add(self.ins, flag=wx.ALIGN_LEFT|wx.EXPAND)

        sizer.Add(text, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        self.SetSizerAndFit(sizer)

    @property
    def input(self):
        """ @brief Property returning self.img
        """
        return self.img

    def update(self, input):
        """ @brief Updates the current image
            @details Reloads size values
            @param input Input image
            @returns Dictionary with 'threeD' value populated
        """

        ## @var img
        #   Image data structure
        self.img = input

        if self.img.filename:   file = os.path.split(self.img.filename)[1]
        else:                   file = 'Unknown .png file'
        self.file.SetLabel(file)

        self.pix.SetLabel('%i x %i pixels' % (self.img.width, self.img.height))

        if self.img.zmin is not None and self.img.zmax is not None:
            self.mms.SetLabel('%.2g x %.2g x %.2g mm' %
                (self.img.dx, self.img.dy, self.img.dz)
            )
            self.ins.SetLabel('%.2g x %.2g x %.2g"' %
                (self.img.dx/25.4,
                 self.img.dy/25.4,
                 self.img.dz/25.4)
            )
            threeD = bool(self.img.dz)
        else:
            self.mms.SetLabel('%.2g x %.2g mm' %
                (self.img.dx, self.img.dy)
            )
            self.ins.SetLabel('%.2g x %.2g"' %
                (self.img.dx/25.4,self.img.dy/25.4)
            )
            threeD = False

        return {'threeD': threeD}

    def run(self):
        """ @brief Returns a dictionary with the stored Image
        """
        return {'img': self.img}

################################################################################

from koko.fab.image         import Image
from koko.cam.path_panels   import PathPanel, ContourPanel

TYPE = Image

WORKFLOWS = {
    None:           (ImageInputPanel,),
    PathPanel:      (ImageInputPanel,),
    ContourPanel:   (ImageInputPanel,),
}

################################################################################

########NEW FILE########
__FILENAME__ = epilog
"""
@namespace epilog
@brief Output details and UI panel for an Epilog laser cutter.
"""


NAME = 'Epilog'

import  tempfile
import  subprocess

import  koko
from    koko.cam.panel import OutputPanel

class EpilogOutput(OutputPanel):
    """ @class EpilogOutput UI Panel for Epilog laser
    """

    """ @var extension File extension for Epilog laser file
    """
    extension = '.epi'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        self.construct('Epilog laser cutter', [
            ('2D power (%)', 'power', int, lambda f: 0 <= f <= 100),
            ('Speed (%)', 'speed', int, lambda f: 0 <= f <= 100),
            ('Rate','rate', int, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f >= 0),
            ('ymin (mm)', 'ymin', float, lambda f: f >= 0),
            ('autofocus', 'autofocus', bool)
        ], start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into an epilog
            laser file (with .epi suffix).
        '''
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Converting to .epi file'

        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        job_name = koko.APP.filename if koko.APP.filename else 'untitled'

        self.file.write("%%-12345X@PJL JOB NAME=%s\r\nE@PJL ENTER LANGUAGE=PCL\r\n&y%iA&l0U&l0Z&u600D*p0X*p0Y*t600R*r0F&y50P&z50S*r6600T*r5100S*r1A*rC%%1BIN;XR%d;YP%d;ZS%d;\n" %
            (job_name, 1 if values['autofocus'] else 0,
             values['rate'], values['power'], values['speed']))

        scale = 600/25.4 # The laser's tick is 600 DPI
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale
        xy = lambda x,y: (xoffset + scale*x, yoffset + scale*y)

        for path in paths:
            self.file.write("PU%d,%d;" % xy(*path.points[0][0:2]))
            for pt in path.points[1:]:
                self.file.write("PD%d,%d;" % xy(*pt[0:2]))
            self.file.write("\n")

        self.file.write("%%0B%%1BPUtE%%-12345X@PJL EOJ \r\n")
        self.file.flush()

        koko.FRAME.status = ''

        return True


    def send(self):
        subprocess.call('printer=laser; lpr -P$printer "%s"'
                        % self.file.name, shell=True)

################################################################################

from koko.cam.path_panels   import ContourPanel

INPUT = ContourPanel
PANEL = EpilogOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
    ('<None>', {}),

    ('Cardboard',
        {CadImgPanel:  [('res',5)],
         ContourPanel: [('diameter', 0.25)],
         EpilogOutput: [('power', 25), ('speed', 75),
                        ('rate', 500), ('xmin', 0), ('ymin', 0)]
        }
    )
]

########NEW FILE########
__FILENAME__ = gcode
NAME = 'G-code'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.fab.path   import Path

from    koko.cam.panel  import FabPanel, OutputPanel

class GCodeOutput(OutputPanel):

    extension = '.g'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'G-Code', [
            ('Cut speed (mm/s)', 'feed',  float, lambda f: f > 0),
            ('Plunge rate (mm/s)', 'plunge',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Cut type', 'type', ['Conventional', 'Climb']),
            ('Tool number', 'tool', int, lambda f: f > 0),
            ('Coolant', 'coolant', bool)
        ])

        self.construct()


    def run(self, paths):
        ''' Convert the path from the previous panel into a g-code file
        '''

        koko.FRAME.status = 'Converting to .g file'

        values = self.get_values()
        if not values:  return False

        # Reverse direction for climb cutting
        if values['type']:
            paths = Path.sort([p.reverse() for p in paths])


        # Check to see if all of the z values are the same.  If so,
        # we can use 2D cutting commands; if not, we'll need
        # to do full three-axis motion control
        zmin = paths[0].points[0][2]
        flat = True
        for p in paths:
            if not all(pt[2] == zmin for pt in p.points):
                flat = False

        # Create a temporary file to store the .sbp instructions
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        self.file.write("%%\n")     # tape start
        self.file.write("G17\n")    # XY plane
        self.file.write("G20\n")    # Inch mode
        self.file.write("G40\n")    # Cancel tool diameter compensation
        self.file.write("G49\n")    # Cancel tool length offset
        self.file.write("G54\n")    # Coordinate system 1
        self.file.write("G80\n")    # Cancel motion
        self.file.write("G90\n")    # Absolute programming
        self.file.write("G94\n")    # Feedrate is per minute

        scale = 1/25.4 # inch units

        self.file.write("T%dM06\n" % values['tool']) # Tool selection + change
        self.file.write("F%0.4f\n" % (60*scale*values['feed']))  # Feed rate
        self.file.write("S%0.4f\n" % values['spindle']) # spindle speed
        if values['coolant']:   self.file.write("M08\n") # coolant on

        # Move up before starting spindle
        self.file.write("G00Z%0.4f\n" % (scale*values['jog']))
        self.file.write("M03\n") # spindle on (clockwise)
        self.file.write("G04 P1\n") # pause one second to spin up spindle

        xy  = lambda x,y:   (scale*x, scale*y)
        xyz = lambda x,y,z: (scale*x, scale*y, scale*z)


        for p in paths:

            # Move to the start of this path at the jog height
            self.file.write("G00X%0.4fY%0.4fZ%0.4f\n" %
                            xyz(p.points[0][0], p.points[0][1], values['jog']))

            # Plunge to the desired depth
            self.file.write("G01Z%0.4f F%0.4f\n" %
                            (p.points[0][2]*scale, 60*scale*values['plunge']))

            # Restore XY feed rate
            self.file.write("F%0.4f\n" % (60*scale*values['feed']))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("X%0.4fY%0.4f\n" % xy(*pt[0:2]))
                else:       self.file.write("X%0.4fY%0.4fZ%0.4f\n" % xyz(*pt))

            # Lift the bit up to the jog height at the end of the segment
            self.file.write("Z%0.4f\n" % (scale*values['jog']))

        self.file.write("M05\n") # spindle stop
        if values['coolant']:   self.file.write("M09\n") # coolant off
        self.file.write("M30\n") # program end and reset
        self.file.write("%%\n")  # tape end
        self.file.flush()

        koko.FRAME.status = ''
        return True


################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = GCodeOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),

('Flat cutout (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     1),
        ('overlap',     ''),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        1),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
),

('Wax rough cut (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     -1),
        ('overlap',     0.25),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        0.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
),

('Wax finish cut (1/8")', {
    PathPanel:
        [('diameter',    3.175),
         ('offsets',     -1),
         ('overlap',     0.5),
         ('threeD',      True),
         ('type',        'XZ + YZ'),
         ('step',        0.5),
         ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    GCodeOutput:
        [('feed', 20),
         ('plunge', 2.5),
         ('spindle', 10000),
         ('jog', 5),
         ('tool', 1),
         ('coolant', False)]
    }
)
]

########NEW FILE########
__FILENAME__ = modela
NAME = 'Roland Modela'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.cam.panel import FabPanel, OutputPanel

class ModelaOutput(OutputPanel):

    extension = '.rml'


    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Modela', [
            ('Speed (mm/s)', 'speed', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f > 0),
            ('ymin (mm)', 'ymin', float, lambda f: f > 0)
            ])

        sizer = self.GetSizer()

        move_button = wx.Button(self, wx.ID_ANY, label='Move to xmin, ymin')
        move_button.Bind(wx.EVT_BUTTON, self.move)
        sizer.Add(move_button, flag=wx.CENTER|wx.TOP, border=5)

        # Add generate + save buttons
        self.construct(start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into a roland
            modela file (with .rml suffix)
        '''

        koko.FRAME.status = 'Converting to .rml file'

        values = self.get_values()
        if not values:  return False

        # Check to see if all of the z values are the same.  If so,
        # we can use pen up / pen down commands; if not, we'll need
        # to do full three-axis motion control
        zmin = paths[0].points[0][2]
        flat = True
        for p in paths:
            if not all(pt[2] == zmin for pt in p.points):
                flat = False


        scale = 40.
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale

        xy  = lambda x,y:   (xoffset + scale*x, yoffset + scale*y)
        xyz = lambda x,y,z: (xoffset + scale*x, yoffset + scale*y, scale*z)

        # Create a temporary file to store the .rml stuff
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        self.file.write("PA;PA;")   # plot absolute

        # Set speeds
        self.file.write("VS%.1f;!VZ%.1f" % (values['speed'], values['speed']))

        # Set z1 to the cut depth (only relevant for a 2D cut)
        # and z2 to the jog height (used in both 2D and 3D)
        self.file.write("!PZ%d,%d;" % (zmin*scale, values['jog']*scale))

        self.file.write("!MC1;\n")  # turn the motor on

        for p in paths:
            # Move to the start of this path with the pen up
            self.file.write("PU%d,%d;" % xy(*p.points[0][0:2]))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("PD%d,%d;"   % (xy(*pt[0:2])))
                else:       self.file.write("Z%d,%d,%d;" % (xyz(*pt)))

            # Lift then pen up at the end of the segment
            self.file.write("PU%d,%d;" % xy(*p.points[-1][0:2]))

        self.file.write("!MC0;"*1000) # Modela buffering bug workaround
        self.file.write("\nH;\n")
        self.file.flush()

        koko.FRAME.status = ''
        return True


    def send(self, file=None):
        if file is None:    file = self.file.name
        subprocess.call('port = /dev/ttyUSB0;' +
                        'stty -F $port raw -echo crtscts;' +
                        'cat "%s" > $port' % self.file.name,
                        shell=True)


    def move(self, event=None):
        values = self.get_values(('xmin','ymin'))
        if not values:  return False

        x, y = values['xmin'], values['ymin']
        with open('rml_move.rml') as f:
            f.write("PA;PA;!VZ10;!PZ0,100;PU %d %d;PD %d %d;!MC0;" %
                    (x,y,x,y))
        self.send('rml_move.rml')
        os.remove('rml_move.rml')

################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = ModelaOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),

('Wax rough cut (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     -1),
        ('overlap',     0.25),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        0.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ModelaOutput:
        [('speed', 29),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }
),

('Wax finish cut (1/8")', {
    PathPanel:
        [('diameter',    3.175),
         ('offsets',     -1),
         ('overlap',     0.5),
         ('threeD',      True),
         ('type',        'XZ + YZ'),
         ('step',        0.5),
         ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ModelaOutput:
        [('speed', 20),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }
),

('Mill traces (1/64")', {
    PathPanel:
        [('diameter',    0.4),
         ('offsets',     4),
         ('overlap',     0.75),
         ('depth',      -0.1),
         ('threeD',      False),
         ('top',         ''),
         ('bottom',      ''),
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 4),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }),

('Mill traces (0.010")', {
    PathPanel:
       [('diameter',    0.254),
        ('offsets',     4),
        ('overlap',     0.75),
        ('depth',      -0.1),
        ('threeD',      False),
        ('top',         ''),
        ('bottom',      '')
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 2),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }),

('Cut out board (1/32")',
    {PathPanel:
       [('diameter',    0.79),
        ('offsets',     1),
        ('overlap',     ''),
        ('threeD',      True),
        ('top',         -0.5),
        ('bottom',      -1.7),
        ('step',        0.5),
        ('type',        'XY')
         ],
    CadImgPanel:
        [('res', 15)],
    ModelaOutput:
        [('speed', 4),
         ('jog', 1.0),
         ('xmin', 20),
         ('ymin', 20)]
    }
)
]

########NEW FILE########
__FILENAME__ = null
# Empty machine description file

NAME = "<None>"
INPUT = None
PANEL = None
DEFAULTS = {}

########NEW FILE########
__FILENAME__ = shopbot
NAME = 'Shopbot'

import  os
import  subprocess
import  tempfile

import  wx

import  koko
from    koko.fab.path   import Path
from    koko.cam.panel  import FabPanel, OutputPanel

class ShopbotOutput(OutputPanel):
    """ @class ShopbotOutput
        @brief Panel for a three-axis Shopbot machine.
    """
    extension = '.sbp'

    def __init__(self, parent):
        """ @brief Panel constructor
            @param parent Parent UI panel
        """
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Shopbot', [
            ('Cut speed (mm/s)', 'cut_speed',  float, lambda f: f > 0),
            ('Jog speed (mm/s)', 'jog_speed',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Cut type', 'type', ['Conventional', 'Climb']),
            ('File units', 'units', ['inches', 'mm'])
        ])

        self.construct()


    def run(self, paths):
        """ @brief Convert the path from the previous panel into a shopbot file.
            @param paths List of Paths
        """

        koko.FRAME.status = 'Converting to .sbp file'

        values = self.get_values()
        if not values:  return False

        # Reverse direction for climb cutting
        if values['type']:
            paths = Path.sort([p.reverse() for p in paths])

        # Check to see if all of the z values are the same.  If so,
        # we can use 2D cutting commands; if not, we'll need
        # to do full three-axis motion control
        zmin = paths[0].points[0][2]
        flat = True
        for p in paths:
            if not all(pt[2] == zmin for pt in p.points):
                flat = False

        ## @var file
        # tempfile.NamedTemporaryFile to store OpenSBP commands
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        self.file.write("SA\r\n")   # plot absolute
        self.file.write("TR,%s,1,\r\n" % values['spindle']) # spindle speed
        self.file.write("SO,1,1\r\n") # set output number 1 to on
        self.file.write("pause,2,\r\n") # pause for spindle to spin up

        scale = 1 if values['units'] else 1/25.4 # mm vs inch units

        # Cut and jog speeds
        self.file.write("MS,%f,%f\r\n" %
            (values['cut_speed']*scale, values['cut_speed']*scale))
        self.file.write("JS,%f,%f\r\n" %
            (values['jog_speed']*scale, values['jog_speed']*scale))

        self.file.write("JZ,%f\r\n" % (values['jog']*scale)) # Move up

        xy  = lambda x,y:   (scale*x, scale*y)
        xyz = lambda x,y,z: (scale*x, scale*y, scale*z)


        for p in paths:

            # Move to the start of this path with the pen up
            self.file.write("J2,%f,%f\r\n" % xy(*p.points[0][0:2]))

            if flat:    self.file.write("MZ,%f\r\n" % (zmin*scale))
            else:       self.file.write("M3,%f,%f,%f\r\n" % xyz(*p.points[0]))

            # Cut each point in the segment
            for pt in p.points:
                if flat:    self.file.write("M2,%f,%f\r\n" % xy(*pt[0:2]))
                else:       self.file.write("M3,%f,%f,%f\r\n" % xyz(*pt))

            # Lift then pen up at the end of the segment
            self.file.write("MZ,%f\r\n" % (values['jog']*scale))

        self.file.flush()

        koko.FRAME.status = ''
        return True


################################################################################

from koko.cam.path_panels   import PathPanel

INPUT = PathPanel
PANEL = ShopbotOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),

('Flat cutout (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     1),
        ('overlap',     ''),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        1.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
),

('Wax rough cut (1/8")', {
    PathPanel: [
        ('diameter',    3.175),
        ('offsets',     -1),
        ('overlap',     0.25),
        ('threeD',      True),
        ('type',        'XY'),
        ('step',        1.5),
        ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
),

('Wax finish cut (1/8")', {
    PathPanel:
        [('diameter',    3.175),
         ('offsets',     -1),
         ('overlap',     0.5),
         ('threeD',      True),
         ('type',        'XZ + YZ'),
         ('step',        1.5),
         ('depth',       ''),
        ],
    CadImgPanel:
        [('res', 5)],
    ShopbotOutput:
        [('cut_speed', 20),
         ('jog_speed', 5.0),
         ('spindle', 10000),
         ('jog', 5)]
    }
)
]

########NEW FILE########
__FILENAME__ = shopbot5
NAME = '5-Axis Shopbot'

import  os
import  subprocess
import  tempfile
from    math import atan2, sqrt, degrees, pi

import numpy as np
import  wx

import  koko
from    koko.fab.path   import Path
from    koko.cam.panel  import FabPanel, OutputPanel

class Shopbot5Output(OutputPanel):
    """ @class Shopbot5Output
        @brief Output panel for a five-axis shopbot
    """

    ## @var extension
    # File extension for OpenSBP files
    extension = '.sbp'

    def __init__(self, parent):
        """ @brief Initializes the UI panel
            @param parent Parent panel
        """
        OutputPanel.__init__(self, parent)

        FabPanel.construct(self, 'Five-axis Shopbot', [
            ('Cut/jog speed (mm/s)', 'cut_speed',  float, lambda f: f > 0),
            ('Spindle speed (RPM)', 'spindle', float, lambda f: f > 0),
            ('Jog height (mm)', 'jog', float, lambda f: f > 0),
            ('Bit length (mm)', 'bit', float, lambda f: f > 0),
            ('Gauge length (mm)', 'gauge', float, lambda f: f > 0),
        ])

        self.construct()
        self.gauge.SetValue(str(6.787*25.4))



    def run(self, planes, axis_names):
        """ @brief Converts paths from the previous panel into a shopbot file
            @details Compensates for angles and adds safe traverses between paths
            @param planes List of list of paths.  Each interior list should be of paths on a single plane.
            @param axis_names List of names for each axis.
        """

        koko.FRAME.status = 'Converting to .sbp file'

        values = self.get_values()
        if not values:  return False
        offset = values['gauge'] + values['bit']
        jog = values['jog']
        scale = 1/25.4 # inch units

        ## @var file
        # NamedTemporaryFile containing the OpenSBP part file
        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)

        def M3(x, y, z, scale=scale, offset=offset):
            self.file.write(
                "M3,%f,%f,%f\r\n" %
                (x*scale, y*scale, (z-offset)*scale)
            )


        self.file.write(
            "'This is a 5-axis Shopbot file created by kokopelli.\r\n"
        )
        self.file.write(
            "'The bit should be zeroed so that when pointing down,\r\n"
        )
        self.file.write(
            "'it touches the material at xmin, ymin, zmax.\r\n"
        )

        self.file.write("SA\r\n")   # plot absolute
        self.file.write("TR,%s,1,\r\n" % values['spindle']) # spindle speed
        self.file.write("SO,1,1\r\n") # set output number 1 to on
        self.file.write("pause,2,\r\n") # pause for spindle to spin up

        # Cut and jog speeds
        self.file.write("MS,%f,%f\r\n" %
            (values['cut_speed']*scale, values['cut_speed']*scale))

        # Make sure the head is neutrally positioned
        self.file.write("M5,,,,0,0\r\n")


        # Move up.
        M3(0, 0, jog+offset)

        for plane, axis_name in zip(planes, axis_names):

            self.file.write(
                "'Beginning of %s plane\r\n" % axis_name
            )

            v = plane[0][0][3:6]

            cut_offset = offset * plane[0][0][3:6]
            jog_offset = (offset+jog) * plane[0][0][3:6]

            # Take the first point of the path and subtract the endmill
            # length plus the jog distance.
            origin = plane[0][0][0:3] - jog_offset

            # Travel to the correct xy coordinates
            M3(origin[0], origin[1], jog+offset)

            # We can rotate the B axis in two possible directions,
            # which gives two different possible A rotations
            aM = atan2( v[1],  v[0])
            aP = atan2(-v[1], -v[0])

            # Pick whichever A rotation is smaller
            b = atan2(sqrt(v[0]**2 + v[1]**2), -v[2])
            if (abs(aM) < abs(aP)):
                a = aM
                b = -b
            else:
                a = aP

            self.file.write("M5,,,,%f,%f\r\n" % (degrees(a), degrees(b)))

            for path in plane:
                # Move to this path's start coordinates
                pos = path[0][0:3]
                start = pos - v*np.dot(pos - origin, v)
                M3(*start)

                for pt in path.points:
                    pos = pt[0:3] - cut_offset

                    depth = np.dot(pos - origin, v)
                    if depth > values['bit']:
                        pos -= v*(depth - values['bit'])

                    M3(*pos)

                # Back off to the safe cut plane
                stop = pos - v*np.dot(pos - origin, v)
                M3(*stop)

            # Pull up to above the top of the model
            M3(stop[0], stop[1], jog+offset)

            # Rotate the head back to neutral
            self.file.write("M5,,,,0,0\r\n")

        self.file.flush()

        koko.FRAME.status = ''
        return {'file': self.file}


################################################################################

from koko.cam.path_panels   import MultiPathPanel

INPUT = MultiPathPanel
PANEL = Shopbot5Output

################################################################################

from koko.cam.inputs.cad import CadASDFPanel

DEFAULTS = [
('<None>', {}),

('1/4" endmill, foam', {
    CadASDFPanel: [
        ('res', 10),
    ],
    MultiPathPanel: [
        ('res',         10),
        ('diameter',    6.35),
        ('stepover_r',  0.8),
        ('stepover_f',  0.5),
        ('step',        6),
        ('tool', 'Ball')
    ],
    Shopbot5Output: [
        ('cut_speed', 50),
        ('spindle', 10000),
        ('jog', 5),
        ('bit', 127)
    ]
}),

]

########NEW FILE########
__FILENAME__ = universal
NAME = 'Universal laser cutter'

import  tempfile
import  subprocess

import  koko
from    koko.cam.panel import OutputPanel

class UniversalOutput(OutputPanel):

    extension = '.uni'

    def __init__(self, parent):
        OutputPanel.__init__(self, parent)

        self.construct('Universal laser cutter', [
            ('2D power (%)', 'power', int, lambda f: 0 <= f <= 100),
            ('Speed (%)', 'speed', int, lambda f: 0 <= f <= 100),
            ('Rate','rate', int, lambda f: f > 0),
            ('xmin (mm)', 'xmin', float, lambda f: f >= 0),
            ('ymin (mm)', 'ymin', float, lambda f: f >= 0)
        ], start=True)


    def run(self, paths):
        ''' Convert the path from the previous panel into an epilog
            laser file (with .epi suffix).
        '''
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Converting to .uni file'

        self.file = tempfile.NamedTemporaryFile(suffix=self.extension)
        job_name = koko.APP.filename if koko.APP.filename else 'untitled'

        self.file.write("Z") # initialize
        self.file.write("t%s~;" % job_name) # job name
        self.file.write("IN;DF;PS0;DT~") # initialize
        self.file.write("s%c" % (values['rate']/10)) # ppi

        speed_hi = chr((648*values['speed']) / 256)
        speed_lo = chr((648*values['speed']) % 256)
        self.file.write("v%c%c" % (speed_hi, speed_lo))

        power_hi = chr((320*values['power']) / 256)
        power_lo = chr((320*values['power']) % 256)
        self.file.write("p%c%c" % (power_hi, power_lo))

        self.file.write("a%c" % 2) # air assist on high

        scale = 1000/25.4 # The laser's tick is 1000 DPI
        xoffset = values['xmin']*scale
        yoffset = values['ymin']*scale
        xy = lambda x,y: (xoffset + scale*x, yoffset + scale*y)

        for path in paths:
            self.file.write("PU;PA%d,%d;PD;" % xy(*path.points[0][0:2]))
            for pt in path.points[1:]:
                self.file.write("PA%d,%d;" % xy(*pt[0:2]))
            self.file.write("\n")

        self.file.write("e") # end of file
        self.file.flush()

        koko.FRAME.status = ''

        return True


    def send(self):
        subprocess.call('printer=laser; lpr -P$printer "%s"'
                        % self.file.name, shell=True)

################################################################################

from koko.cam.path_panels import ContourPanel

INPUT = ContourPanel
PANEL = UniversalOutput

################################################################################

from koko.cam.inputs.cad import CadImgPanel

DEFAULTS = [
('<None>', {}),
('Cardboard',
    {CadImgPanel:  [('res',5)],
     ContourPanel: [('diameter', 0.25)],
     UniversalOutput: [('power', 25), ('speed', 75),
                       ('rate', 500), ('xmin', 0), ('ymin', 0)]
    }
)
]

########NEW FILE########
__FILENAME__ = panel
"""@package panel Parent classes for CAM UI panels.
"""

import os
import shutil

import wx
import wx.lib.stattext

import koko
import koko.dialogs as dialogs

class FabPanel(wx.Panel):
    """ @class FabPanel
        @brief Parent class for a CAM workflow panel.
    """

    def __init__(self, parent):
        """ @brief Initializes a FabPanel.
            @param parent   parent panel
        """
        wx.Panel.__init__(self, parent)

        ## @var parent
        # Parent UI panel
        self.parent = parent

        ## @var names
        # List of variable names
        self.names  = []

        ## @var labels
        # List of GenStaticText labels (UI elements)
        self.labels = []

        ## @var params
        # List of UI parameter widgets (textbox, choice, or check box)
        self.params = []

        ## @var types
        # List of desired parameter types
        self.types  = []

        ## @var checks
        # List of lambda functions to check parameter validity
        self.checks = []


    def construct(self, title, parameters):
        """ @brief Populates the panel with UI elements.
            @param title    Panel title
            @param parameters   List of (label, name, type, checker) tuples
        """

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label=title,
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND)

        gs = wx.FlexGridSizer(len(parameters), 2, 5, 5)
        gs.SetFlexibleDirection(wx.VERTICAL)
        gs.AddGrowableCol(0, 1)
        gs.AddGrowableCol(1, 1)
        for i in range(len(parameters)):    gs.AddGrowableRow(i)

        for P in parameters:
            if len(P) == 3:
                label, name, cls = P
                check = lambda f: True
            elif len(P) == 4:
                label, name, cls, check = P

            label = wx.StaticText(self, label=label)

            gs.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)

            if cls in [int, float]:
                p = wx.TextCtrl(self, wx.ID_ANY, style=wx.NO_BORDER)
                gs.Add(p, flag=wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHAR, self.parent.invalidate)
            elif cls is bool:
                p = wx.CheckBox(self)
                gs.Add(p, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHECKBOX, self.parent.invalidate)
            elif type(cls) in [list, tuple]:
                p = wx.Choice(self, wx.ID_ANY, choices=cls)
                gs.Add(p, flag=wx.CENTER|wx.ALIGN_CENTER_VERTICAL)
                p.Bind(wx.EVT_CHOICE, self.parent.invalidate)
            else:
                raise ValueError('Invalid parameter description '+str(p))

            self.names.append(name)
            self.labels.append(label)
            self.params.append(p)
            self.types.append(cls)
            self.checks.append(check)


            setattr(self, name, p)

        sizer.Add(gs, proportion=1, flag=wx.EXPAND|wx.TOP, border=5)
        self.SetSizerAndFit(sizer)


    def update(self, **kwargs):        return kwargs
    def run(self, **kwargs):           return kwargs


    def apply_defaults(self, defaults):
        """ @brief Applies a defaults dictionary to this panel.
            @param defaults Dictionary mapping parameter names to default values
        """
        if not type(self) in defaults:  return

        for p, v in defaults[type(self)]:
            if type(getattr(self, p)) is wx.TextCtrl:
                getattr(self, p).SetValue(str(v))
            elif type(getattr(self, p)) is wx.CheckBox:
                getattr(self, p).SetValue(bool(v))
            elif type(getattr(self, p)) is wx.Choice:
                i = getattr(self, p).GetStrings().index(v)
                getattr(self, p).SetSelection(i)


    def store_values(self):
        """ @brief Copies parameter values to self.values.

            @details
            This saves parameter values so that we don't have to call wx functions in a separate thread.
        """
        self.values = {}
        for name in self.names:
            i = self.names.index(name)

            # TextCtrl
            if self.types[i] in [int, float]:
                self.values[name] = self.params[i].GetValue()
            # Check box
            elif self.types[i] is bool:
                self.values[name] = self.params[i].IsChecked()
            # Choice
            elif type(self.types[i]) in [list, tuple]:
                self.values[name] = self.params[i].GetSelection()


    def get_values(self, names=None):
        """ @brief Returns a dictionary of panel values.  If a parameter cannot be acquired or a validator fails, marks the error and returns False.

            @param names Names of parameters to return (default of None gives all parameters)
        """

        if names is None:   names = self.names

        values = {}
        for name in names:
            i = self.names.index(name)
            success = True

            # TextCtrl
            if self.types[i] in [int, float]:
                try:   values[name] = self.types[i](self.values[name])
                except ValueError:  success = False
            # Check box
            elif self.types[i] is bool:
                values[name] = self.values[name]
            # Choice
            elif type(self.types[i]) in [list, tuple]:
                values[name] = self.values[name]

            # Validator function
            if success and not self.checks[i](values[name]):
                success = False

            if not success:
                wx.CallAfter(self.labels[i].SetBackgroundColour, '#853535')
                wx.CallAfter(self.labels[i].SetForegroundColour, '#ffffff')
                koko.FRAME.status = 'Invalid value for %s' % name
                return False

        return values


################################################################################

class OutputPanel(FabPanel):
    """ @class OutputPanel
        @brief Subclass of FabPanel with Generate and Save buttons
    """

    def __init__(self, parent):
        """ Initializes an OutputPanel.
            @param parent   Parent panel
        """
        FabPanel.__init__(self, parent)

    def construct(self, title=None, parameters=[], start=False):
        """ Constructs UI elements for an OutputPanel
            @param title Panel title
            @param parameters List of (label, name, type, checker) tuples
            @param start Boolean indicating if the panel should show a Start button
        """

        if title is not None:
            FabPanel.construct(self, title, parameters)

        hs = wx.BoxSizer(wx.HORIZONTAL)

        ## @var gen_button
        # wx.Button to generate toolpath
        self.gen_button = wx.Button(self, id=wx.ID_ANY, label='Generate')
        self.gen_button.Bind(wx.EVT_BUTTON, self.parent.start)

        ## @var save_button
        # wx.Button to save toolpath
        self.save_button = wx.Button(self, id=wx.ID_ANY, label='Save')
        self.save_button.Enable(False)
        self.save_button.Bind(wx.EVT_BUTTON, self.save)
        hs.Add(self.gen_button,   flag=wx.ALL, border=5)
        hs.Add(self.save_button,  flag=wx.ALL, border=5)

        ## @var start_button
        # wx.Button to start machine running (optional)
        if start:
            self.start_button = wx.Button(self, id=wx.ID_ANY, label='Start')
            self.start_button.Enable(False)
            self.start_button.Bind(wx.EVT_BUTTON, self.start)
            hs.Add(self.start_button, flag=wx.ALL, border=5)
        else:
            self.start_button = None

        sizer = self.GetSizer()
        sizer.Add(hs, flag=wx.TOP|wx.CENTER, border=5)
        self.SetSizerAndFit(sizer)

    def save(self, event=None):
        """@ brief Saves a generated toolpath file with the appropriate extension.
        """
        dir, file = dialogs.save_as(koko.APP.directory,
                                    extension=self.extension)
        if file == '':  return
        path = os.path.join(dir, file)
        shutil.copy(self.file.name, path)


    def start(self, event=None):
        """@brief Sends a file to a machine (overloaded in children)
        """
        raise NotImplementedError(
            'start needs to be overloaded in machine class'
        )

    def enable(self):
        """@brief Enables Generate, Save, and Start buttons (if present)
        """
        wx.CallAfter(self.gen_button.Enable, True)
        wx.CallAfter(self.save_button.Enable, True)
        if self.start_button:
            wx.CallAfter(self.start_button.Enable, True)

    def invalidate(self):
        """@brief  Enables Generate button and disables Save and Start buttons.
        """
        self.gen_button.Enable(True)
        self.save_button.Enable(False)
        if self.start_button:
            self.start_button.Enable(False)

########NEW FILE########
__FILENAME__ = path_panels
import operator

import wx

import  koko
from    koko.dialogs    import error
from    koko.cam.panel  import FabPanel
from    koko.fab.path   import Path

from    koko.c.vec3f    import Vec3f
import  numpy as np

################################################################################

class ContourPanel(FabPanel):
    """ @class ContourPanel
        @brief Panel to generate a single offset contour
    """
    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        self.construct('2D Path', [
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ])

    def run(self, img):
        """ @brief Generates a single offset contour
            @param img Image to contour
            @returns Dictionary with 'paths' defined
        """
        values = self.get_values()
        if not values:  return False

        koko.FRAME.status = 'Finding distance transform'
        distance = img.distance()

        ## var @paths
        #   List of Paths representing contour cut
        self.paths = distance.contour(values['diameter']/2, 1, 0)
        koko.CANVAS.load_paths(self.paths, img.xmin, img.ymin)

        return {'paths': self.paths}

################################################################################

class PathPanel(FabPanel):
    """ @class PathPanel
        @brief General-purpose 2D/3D path planning panel.
    """
    def __init__(self, parent):

        FabPanel.__init__(self, parent)

        self.construct('Path', [
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ('Offsets (-1 to fill)', 'offsets', int,
                lambda f: f == -1 or f > 0),
            ('Overlap (0 - 1)', 'overlap', float, lambda f: 0 < f < 1),
            ('3D cut', 'threeD', bool),
            ('Z depth (mm)','depth', float, lambda f: f < 0),
            ('Top height (mm)','top', float),
            ('Bottom height (mm)','bottom', float),
            ('Step height (mm)','step', float, lambda f: f > 0),
            ('Path type', 'type', ['XY','XZ + YZ']),
            ('Tool type', 'tool', ['Flat','Ball']),
            ])

        # This panel is a bit special, because modifying the checkbox
        # can actually change the panel's layout (different labels are
        # shown or hidden depending on the path type)
        self.threeD.Bind(
            wx.EVT_CHECKBOX,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )
        self.type.Bind(
            wx.EVT_CHOICE,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )

    def update(self, threeD):
        """ @brief Modifies visible controls based on the situation
            @param threeD Boolean defining if the previous image has z information
        """

        def hide(index):
            self.labels[index].Hide()
            self.params[index].Hide()

        def show(index):
            self.labels[index].Show()
            self.params[index].Show()

        for i in range(len(self.params)):   show(i)

        if self.threeD.IsChecked() or threeD:
            hide(4)

            # 3D models can't be evaluated as 2D toolpaths,
            # and they've got their own opinions on z bounds
            if threeD:
                hide(3)
                hide(5)
                hide(6)

            # Number of offsets only matters for xy cuts;
            # mill bit selection only matters for finish cuts
            if self.type.GetSelection() == 1:   hide(1)
            else:                               hide(9)

        else:
            for i in range(5, 10):   hide(i)

        self.parent.Layout()
        return {}


    def run(self, img):
        """ @brief Generates paths
            @param img Input image
            @returns Dictionary with 'paths' defined
        """
        if self.threeD.IsChecked():
            if self.type.GetSelection() == 0:
                return self.run_rough(img)
            else:
                return self.run_finish(img)
            return False
        else:
            return self.run_2d(img)


    def run_rough(self, img):
        """ @brief Calculates a rough cut toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """

        # Save image's original z values (which may have been None)
        old_zvals = img.zmin, img.zmax

        if img.zmin is not None and img.zmax is not None and img.dz:
            values = self.get_values(['diameter','offsets','step'])
            if not values:  return False
            values['top']    = img.zmax
            values['bottom'] = img.zmin
        else:
            values = self.get_values(['diameter','offsets',
                                      'top','bottom','step'])
            if not values:  return False
            img.zmin = values['bottom']
            img.zmax = values['top']

        # We only need an overlap value if we're cutting more than one offsets
        if values['offsets'] != 1:
            v = self.get_values(['overlap'])
            if not v:   return False
            values.update(v)
        else:
            values['overlap'] = 1

        # Figure out the set of z values at which to cut
        heights = [values['top']]
        while heights[-1] > values['bottom']:
            heights.append(heights[-1]-values['step'])
        heights[-1] = values['bottom']

        # Loop over z values, accumulating samples
        i = 0

        self.paths = []
        last_image = None
        last_paths = []
        for z in heights:
            i += 1
            koko.FRAME.status = 'Calculating level %i/%i' % (i, len(heights))

            L = img.threshold(z)
            L.array *= 100

            if last_image is not None and L == last_image:
                paths = [p.copy() for p in last_paths]
            else:
                distance = L.distance()
                paths = distance.contour(
                    values['diameter'], values['offsets'], values['overlap']
                )

            for p in paths:    p.set_z(z-values['top'])

            last_paths = paths
            last_image = L
            self.paths += paths

        # Path offsets (to match image / mesh position)
        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = values['top']

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        # Restore z values on image
        img.zmin, img.zmax = old_zvals

        return {'paths': self.paths}


    def run_finish(self, img):
        """ @brief Calculates a finish cut toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """


        koko.FRAME.status = 'Making finish cut'

        # Save image's original z values (which may have been None)
        old_zvals = img.zmin, img.zmax

        if img.zmin is not None and img.zmax is not None and img.dz:
            values = self.get_values(['diameter','overlap','tool'])
            if not values:  return False
        else:
            values = self.get_values(['diameter','overlap',
                                      'top','bottom','tool'])
            if not values:  return False
            img.zmin = values['bottom']
            img.zmax = values['top']

        self.paths = img.finish_cut(
            values['diameter'], values['overlap'], values['tool']
        )
        for p in self.paths:
            p.offset_z(img.zmin-img.zmax)

        # Path offsets (to match image / mesh position)
        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = img.zmax

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        # Restore z values on image
        img.zmin, img.zmax = old_zvals

        return {'paths': self.paths}


    def run_2d(self, img):
        """ @brief Calculates a 2D contour toolpath
            @param img Input image
            @returns Dictionary with 'paths' defined
        """

        values = self.get_values(['diameter','offsets','depth'])
        if not values:  return False

        # We only need an overlap value if we're cutting more than one offsets
        if values['offsets'] != 1:
            v = self.get_values(['overlap'])
            if not v:   return False
            values.update(v)
        else:
            values['overlap'] = 0

        koko.FRAME.status = 'Finding distance transform'
        distance = img.distance()

        koko.FRAME.status = 'Finding contours'
        self.paths = distance.contour(values['diameter'],
                                      values['offsets'],
                                      values['overlap'])
        for p in self.paths:    p.set_z(values['depth'])


        self.xmin = img.xmin
        self.ymin = img.ymin
        self.zmin = values['depth']

        koko.GLCANVAS.load_paths(self.paths, self.xmin, self.ymin, self.zmin)
        koko.CANVAS.load_paths(self.paths, self.xmin, self.ymin)
        koko.FRAME.status = ''

        return {'paths': self.paths}

################################################################################

class MultiPathPanel(FabPanel):
    """ @class MultiPathPanel
        @brief Path planning panel for multiple face cuts.
        @details The resulting paths are normalized so that xmin = 0, ymin = 0, and zmax = 0 (so cutting z values are negative, going into the material).
    """

    def __init__(self, parent):
        FabPanel.__init__(self, parent)

        self.construct('Custom plane path', [
            ('Resolution (pixels/mm)\n? x ? x ?',
                'res', float, lambda f: f>0),
            ('Diameter (mm)', 'diameter', float, lambda f: f >= 0),
            ('Rough stepover (0-1)', 'stepover_r', float, lambda f: 0 < f < 1),
            ('Finish stepover (0-1)', 'stepover_f', float, lambda f: 0 < f < 1),
            ('Step height (mm)','step', float, lambda f: f > 0),
            ('Tool type', 'tool', ['Flat','Ball']),
            ('Cut type', 'cut', ['Rough','Finish','Both']),
            ('Mode', 'mode', ['Faces', 'From view', '3x2']),
            ('Cuts per 180 degrees', 'cuts_per', int, lambda f: f > 1),
            ('Alpha', 'alpha', float),
            ('Beta', 'beta', float, lambda f: f >= 0 and f <= 90),
            ])

        sizer = self.GetSizer()

        hs = wx.BoxSizer(wx.HORIZONTAL)
        get_button = wx.Button(
            self, wx.ID_ANY, label='Get rotation')
        set_button = wx.Button(
            self, wx.ID_ANY, label='Set rotation')
        get_button.Bind(wx.EVT_BUTTON, self.get_spin)
        set_button.Bind(wx.EVT_BUTTON, self.set_spin)
        hs.Add(get_button, flag=wx.LEFT|wx.TOP, border=5)
        hs.Add(set_button, flag=wx.LEFT|wx.TOP, border=5)
        sizer.Add(hs, flag=wx.CENTER|wx.BOTTOM, border=5)
        self._buttons = set_button, get_button

        self.SetSizerAndFit(sizer)

        self.res.Bind(wx.EVT_TEXT, self.parent.update)
        self.mode.Bind(
            wx.EVT_CHOICE,
            lambda e: (self.parent.update(), self.parent.invalidate())
        )


    def get_spin(self, event=None):
        """ @brief Copies alpha and beta values from GLCanvas
        """
        self.alpha.SetValue(str(koko.GLCANVAS.alpha))
        self.beta.SetValue(str(min(90,koko.GLCANVAS.beta)))
        self.parent.invalidate()

    def set_spin(self, event=None):
        """ @brief Copies alpha and beta values to GLCanvas
        """
        self.store_values()
        values = self.get_values(['alpha', 'beta'])
        if not values:  return
        koko.GLCANVAS.alpha = values['alpha']
        koko.GLCANVAS.beta = values['beta']
        koko.GLCANVAS.Refresh()


    def update(self, dx, dy, dz):
        """ @brief Modifies UI panel based on the situation
            @param dx x size of input ASDF (mm)
            @param dy y size of input ASDF (mm)
            @param dz z size of input ASDF (mm)
            @details Updates image size text and shows/hides parts of the UI based on selections.
        """

        def hide(index):
            self.labels[index].Hide()
            self.params[index].Hide()

        def show(index):
            self.labels[index].Show()
            self.params[index].Show()

        if self.mode.GetSelection() == 0:
            hide(8)
            hide(9)
            hide(10)
            [b.Show(False) for b in self._buttons]
        elif self.mode.GetSelection() == 1:
            hide(8)
            show(9)
            show(10)
            [b.Show(True) for b in self._buttons]
        else:
            show(8)
            hide(9)
            hide(10)
            [b.Show(False) for b in self._buttons]

        self.parent.Layout()

        try:
            scale = float(self.res.GetValue())
        except ValueError:
            self.labels[0].SetLabel('Resolution (pixels/mm)\n? x ? x ?')
        else:
            self.labels[0].SetLabel(
                'Resolution (pixels/mm)\n%i x %i x %i' %
                (max(1, dx*scale),
                 max(1, dy*scale),
                 max(1, dz*scale))
            )
        return {}


    def run(self, asdf):
        """ @brief Generates one or more toolpaths
            @param asdf Input ASDF data structure
            @returns Dictionary with 'planes' (list of list of paths) and 'axis_names' (list of strings) items
        """
        # Parameters used by all operators
        values = self.get_values(
            ['mode','res','diameter','stepover_r',
             'tool','step','stepover_f','cut']
        )
        if not values:  return False

        # Get more parameters based on mode
        if values['mode'] == 1:
            v = self.get_values(['alpha','beta'])
            if not v:   return False
            values.update(v)
        elif values['mode'] == 2:
            v = self.get_values(['cuts_per'])
            if not v:   return False
            values.update(v)

        ## @var planes
        # List of lists of paths.  Each list of paths represent a set of cuts on a given plane.
        self.planes = []

        ## @var axis_names
        # List of strings representing axis names.
        self.axis_names = []

        if values['mode'] == 0:
            target_planes = [
                (0, 0, '+Z'), (180, 90, '+Y'), (0, 90, '-Y'),
                (90, 90, '-X'), (270, 90,'+X')
            ]
        elif values['mode'] == 1:
            target_planes = [
                (values['alpha'], values['beta'], 'view')
            ]
        elif values['mode'] == 2:
            cuts = values['cuts_per']
            alphas = [-90 + 180*v/float(cuts-1) for v in range(cuts)]
            betas = [360*v/float(cuts*2-2) for v in range(2*cuts-2)]
            target_planes = []
            for a in alphas:
                for b in betas:
                    target_planes.append( (a, b, '%g, %g' % (a, b)) )

        for a, b, axis in target_planes:
            koko.FRAME.status = 'Rendering ASDF on %s axis' % axis

            # Find endmill pointing vector
            v = -Vec3f(0,0,1).deproject(a, b)

            # Render the ASDF to a bitmap at the appropriate resolution
            img = asdf.render_multi(
                resolution=values['res'], alpha=a, beta=b
            )[0]

            # Find transformed ADSF bounds
            bounds = asdf.bounds(a, b)


            paths = []
            if values['cut'] in [0, 2]:
                paths += self.rough_cut(
                    img, values['diameter'], values['stepover_r'],
                    values['step'], bounds, axis
                )


            if values['cut'] in [1,2]:
                paths += self.finish_cut(
                    img, values['diameter'], values['stepover_f'],
                    values['tool'], bounds, axis
                )



            # Helper function to decide whether a path is inside the
            # ASDF's bounding box
            def inside(pt, asdf=asdf):
                d = values['diameter']
                return (
                    pt[0] >= -2*d and
                    pt[0] <= asdf.X.upper - asdf.X.lower + 2*d and
                    pt[1] >= -2*d and
                    pt[1] <= asdf.Y.upper - asdf.Y.lower + 2*d and
                    pt[2] <= 2*d and
                    pt[2] >= -(asdf.Z.upper - asdf.Z.lower)
                )


            culled = []
            for p in paths:
                for i in range(len(p.points)):
                    p.points[i,:] = list(Vec3f(p.points[i,:]).deproject(a, b))
                    p.points[i,:] -= [asdf.xmin, asdf.ymin, asdf.zmax]
                p.points = np.hstack(
                    (p.points, np.array([list(v)]*p.points.shape[0]))
                )
                current_path = []
                for pt in p.points:
                    if inside(pt):
                        current_path.append(pt)
                    elif current_path:
                        culled.append(Path(np.vstack(current_path)))
                        current_path = []
                if current_path:
                    culled.append(Path(np.vstack(current_path)))

            self.planes.append(culled)
            self.axis_names.append(axis)

        paths = reduce(operator.add, self.planes)
        koko.GLCANVAS.load_paths(
            paths, asdf.xmin, asdf.ymin, asdf.zmax
        )

        return {'planes': self.planes, 'axis_names': self.axis_names}



    def rough_cut(self, img, diameter, stepover, step, bounds, axis=''):
        """ @brief Calculates a rough cut
            @param img Image to cut
            @param diameter Endmill diameter
            @param stepover Stepover between passes
            @param step Z step amount
            @param bounds Image bounds
            @param axis Name of target axis
            @returns A list of cut paths
        """

        heights = [img.zmax]
        while heights[-1] > img.zmin:
            heights.append(heights[-1]-step)
        heights[-1] = img.zmin

        # Loop over z values, accumulating samples
        i = 0
        total = []
        for z in heights:
            i += 1
            if axis:
                koko.FRAME.status = (
                    'Calculating level %i/%i on %s axis'
                    % (i, len(heights), axis)
                )
            else:
                koko.FRAME.status = (
                    'Calculating level %i/%i on %s axis'
                    % (i, len(heights))
                )

            L = img.threshold(z)
            distance = L.distance()
            paths = distance.contour(diameter, -1, stepover)

            for p in paths:
                p.points[:,0] += bounds.xmin
                p.points[:,1] += bounds.ymin
                p.points[:,2]  = z

            total += paths
        return total


    def finish_cut(self, img, diameter, stepover, tool, bounds, axis=''):
        """ @brief Calculates a finish cut on a single image.
            @param img Image to cut
            @param diameter Endmill diameter
            @param stepover Stepover between passes
            @param tool Tool type (0 for flat-end, 1 for ball-end)
            @param bounds Image bounds
            @param axis Name of target axis
            @returns A list of cut paths
        """
        koko.FRAME.status = 'Making finish cut on %s axis' % axis
        finish = img.finish_cut(diameter, stepover, tool)

        # Special case to make sure that the safe plane
        # for the finish cut is good.
        finish[0].points = np.vstack(
            [finish[0].points[0,:], finish[0].points]
        )
        finish[0].points[0,2] = img.zmax - img.zmin

        for p in finish:
            for i in range(len(p.points)):
                p.points[i,0:3] += [bounds.xmin, bounds.ymin, bounds.zmin]
        return finish

########NEW FILE########
__FILENAME__ = workflow
""" @module CAM workflow module
"""
import sys

import wx
import wx.lib.stattext

import koko

from koko.cam.inputs    import INPUTS
from koko.cam.machines  import MACHINES

from koko.cam.panel     import OutputPanel

from koko.themes       import APP_THEME

################################################################################

class OutputSelector(wx.Panel):
    """ @class OutputSelector
        @brief  Contains a wx.Choice panel to select between machines.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY, label='Output',
                                              style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        self.machines = MACHINES

        menu = wx.Choice(self, wx.ID_ANY,
                         choices=[m.NAME for m in self.machines])
        self.Bind(wx.EVT_CHOICE, self.choice)
        sizer.Add(menu, flag=wx.CENTER|wx.TOP, border=5)

        self.SetSizerAndFit(sizer)

    def choice(self, event):
        """ Regenerates CAM workflow UI based on the selected machine
            @param event wx.Event for choice selection
        """
        self.parent.set_output(self.machines[event.GetSelection()])

################################################################################

class DefaultSelector(wx.Panel):
    """ @class DefaultSelector
        @brief  Contains a wx.Choice panel to select between defaults.
    """

    def __init__(self, parent, defaults):
        """ @brief Creates a DefaultSelector panel
            @param parent Parent UI panel
            @param defaults List of defaults
        """
        wx.Panel.__init__(self, parent)

        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.lib.stattext.GenStaticText(self, wx.ID_ANY,
            label='Defaults', style=wx.ALIGN_CENTRE)
        title.header = True
        sizer.Add(title, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        menu = wx.Choice(self, wx.ID_ANY, choices=[d[0] for d in defaults])
        self.defaults = [d[1] for d in defaults]

        self.Bind(wx.EVT_CHOICE, self.choice)
        sizer.Add(menu, flag=wx.CENTER|wx.TOP, border=5)

        self.SetSizerAndFit(sizer)

    def choice(self, evt):
        """ @brief Applies the selected defaults
            @param evt  wx.Event from the wx.Choice selection
        """
        self.parent.apply_defaults(self.defaults[evt.GetSelection()])

################################################################################

class FabWorkflowPanel(wx.Panel):
    """ @brief CAM UI Workflow panel
    """

    def __init__(self, parent):
        """ @brief Creates a FabWorkflowPanel
            @param parent Parent wx.Frame object
        """
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(OutputSelector(self),
                       flag=wx.EXPAND|wx.TOP,  border=10)

        self.SetSizerAndFit(self.sizer)

        """
        @var input  Input module (initially None)
        @var output Output module (initially null)
        @var panels List of FabPanels in workflow
        @var defaults   DefaultSelector panel
        """
        self.input      = None
        self.output     = MACHINES[0]
        self.panels     = []
        self.defaults   = None

    def regenerate(self, input, output):
        """ @brief Regenerates the workflow UI
            @param input    Input data structure
            @param output   Output module
        """

        self.input = [i for i in INPUTS if i.TYPE == type(input)][0]

        # Make sure we can find a path from the start panel to
        # the desired path panel.
        if output.INPUT in self.input.WORKFLOWS:
            self.output = output

        # If that fails, then load the None machine as our output
        else:
            self.output = MACHINES[0]

        for p in self.panels:   p.Destroy()
        if self.defaults:       self.defaults.Destroy()
        self.panels = []
        self.defaults = None

        if self.output.DEFAULTS:
            self.defaults = DefaultSelector(self, output.DEFAULTS)
            self.sizer.Add(self.defaults, flag=wx.EXPAND|wx.TOP, border=10)

        workflow = (
            self.input.WORKFLOWS[self.output.INPUT] +
            (self.output.INPUT, self.output.PANEL)
        )

        for p in workflow:
            if p is None:   continue

            panel = p(self)

            self.panels.append(panel)
            self.sizer.Add(panel, flag=wx.EXPAND|wx.TOP, border=10)

        APP_THEME.apply(self)
        self.Layout()


    def set_input(self, input):
        """ @brief Loads an input data structure, regenerating the workflow if necessary
            @param input Input data structure
        """
        if input is None:
            return
        elif self.input is None or self.input.TYPE != type(input):
            self.regenerate(input, self.output)
        elif self.panels:
            self.invalidate()
        self.update(input)


    def update(self, input=None):
        """ @brief Updates each panel based on input data structure
            @details If input is None or a wx.Event structure, uses most recent input (extracted from first panel in workflow).
            @param input Input data structure
        """
        if input is None or isinstance(input, wx.Event):
            input = self.panels[0].input

        i = {'input': input}
        for p in self.panels:
            i = p.update(**i)


    def set_output(self, machine):
        """ @brief Sets the output machine, regenerating the workflow if necessary
            @param machine Module describing output
        """
        input = self.panels[0].input
        if self.output != machine:
            if self.panels: self.invalidate()
            self.regenerate(self.panels[0].input, machine)
        self.update(input)

    def apply_defaults(self, defaults):
        """ @brief Applies a set of defaults to UI panels
            @param defaults Default settings
        """
        self.invalidate()
        for p in self.panels:
            p.apply_defaults(defaults)
        self.update()


    def start(self, event=None):
        """ @brief Runs the CAM workflow in a separate thread
        """
        self.panels[-1].gen_button.SetLabel('Running...')
        self.panels[-1].gen_button.Enable(False)

        # Save the wx widget values to local dictionaries
        # (since wx functions don't like being called by
        #  threads other than the main thread)
        for p in self.panels:   p.store_values()

        # Start the CAM workflow generation running in a
        # separate thread.
        koko.TASKS.start_cam()


    def run(self):
        """ @brief Generates a toolpath
            @detail This function should be called in a separate thread to avoid stalling the UI
        """
        success = True
        result = {}
        for p in self.panels:
            result = p.run(**result)
            if result is False: break
        else:
            self.panels[-1].enable()

        wx.CallAfter(self.panels[-1].gen_button.SetLabel, 'Generate')
        wx.CallAfter(self.panels[-1].gen_button.Enable, True)


    def invalidate(self, event=None):
        """ @brief Invalidates final panel in workflow
            @details Disables Save and Start buttons, and deletes paths from canvases to indicate that a generated path is no longer valid.
        """
        APP_THEME.apply(self)
        if isinstance(self.panels[-1], OutputPanel):
            self.panels[-1].invalidate()
        koko.CANVAS.clear_path()
        koko.GLCANVAS.clear_path()
        if event:   event.Skip()

########NEW FILE########
__FILENAME__ = canvas
from    math import sin, cos, pi, floor, ceil

import  wx
import  numpy as np

import  koko
from    koko.prims.menu import show_menu
from    koko.struct     import Struct

class Canvas(wx.Panel):
    """ @class Canvas
        @brief Canvas based on a wx.Panel that draws images and primitives
    """

    def __init__(self, parent, app, *args, **kwargs):
        """ @brief Creates the canvas
            @param parent Parent wx.Frame
            @param app wx.App to which we'll bind callbacks
        """
        wx.Panel.__init__(self, parent, *args, **kwargs)

        ## @var mark_changed_view
        # Callback to trigger a rerender
        self.mark_changed_view = app.mark_changed_view

        # Bind ALL THE THINGS!
        self.bind_callbacks()

        ## @var click
        # Previous click position (in pixel coordinates)
        ## @var mouse
        # Current mouse position (in pixel coordinates)
        self.click = self.mouse = wx.Point()

        ## @var center
        # View center (in cad units)
        self.center = [0.0, 0.0]

        ## @var alpha
        # Rotation about z axis (non-functional)
        ## @var beta
        # Rotation about x axis (non-functional)
        self.alpha = self.beta = 0

        ## @var scale
        # View scale (in pixels/unit)
        self.scale = 20.0

        ## @var mm_per_unit
        # Real-world scale (in mm/unit)
        self.mm_per_unit = 25 # scale factor

        ## @var image
        # Merged image to draw, or None
        self.image = None

        ## @var drag_target
        # Target for left-click and drag operations
        self.drag_target = None

        ## @var dc
        # DrawCanvas variable
        self.dc     = None

        ## @var paths
        # Set of paths to draw, stored as a list of ?x2 NumPy array
        self.paths  = []

        ## @var traverses
        # Set of traverses to draw, stored as an ?x4 NumPy array
        self.traverses = None

        ## @var snap
        # When true, snap to bounds as soon as possible
        self.snap   = True

        ## @var dragged
        # Used when dragging to check if this was a click+drag or a single click

        ## @var images
        # List of images that were merged to make self.image; used in drawing bounds.

################################################################################

    def bind_callbacks(self):
        """ @brief Binds a set of Canvas callbacks.
        """
        self.Bind(wx.EVT_PAINT,         self.paint)
        self.Bind(wx.EVT_MOTION,        self.mouse_move)
        self.Bind(wx.EVT_LEFT_DOWN,     self.mouse_lclick)
        self.Bind(wx.EVT_LEFT_DCLICK,   self.mouse_dclick)
        self.Bind(wx.EVT_LEFT_UP,       self.mouse_lrelease)
        self.Bind(wx.EVT_RIGHT_DOWN,    self.mouse_rclick)
        self.Bind(wx.EVT_MOUSEWHEEL,    self.mouse_scroll)
        self.Bind(wx.EVT_SIZE,          self.mark_changed_view)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_CHAR,          self.char)

    @property
    def border(self):
        """ @brief Border property
        """
        return getattr(self, '_border', None)
    @border.setter
    def border(self, value):
        """ @brief Sets border property and calls Refresh
        """
        self._border = value
        wx.CallAfter(self.Refresh)

################################################################################

    def mouse_move(self, event):
        """ @brief  Handles a mouse move across the canvas.
            @details Drags self.drag_target if it exists
        """
        self.mouse = wx.Point(event.GetX(), event.GetY())

        x, y = self.pixel_to_pos(*self.mouse)
        if koko.PRIMS.mouse_pos(x, y):  self.Refresh()

        # Drag the current drag target around
        if self.drag_target is not None:
            self.dragged = True
            delta = self.mouse - self.click
            self.click = self.mouse
            self.drag_target.drag(delta.x/self.scale, -delta.y/self.scale)
            self.Refresh()

########################################

    def mouse_lclick(self, event):
        """ @brief Records click position and gets a drag target
            @details The drag target is stored in self.drag_target.  It may be a primitive or the canvas itself.
        """
        self.mouse = wx.Point(event.GetX(), event.GetY())
        self.click = self.mouse

        # If we were already dragging something, then dragged remains
        # true (otherwise it is false, because we're starting a new
        # drag)
        self.dragged = bool(self.drag_target)

        x, y = self.pixel_to_pos(*self.mouse)
        t = koko.PRIMS.get_target(x, y)
        if t:
            self.drag_target = t
        else:
            self.drag_target = self

########################################

    def mouse_lrelease(self, event):
        """ @brief Release the current drag target.
        """
        if self.drag_target:
            if self.dragged and self.drag_target != self:
                koko.PRIMS.push_stack()
            elif not self.dragged:
                koko.PRIMS.close_panels()
            self.drag_target = None

########################################

    def mouse_rclick(self, event):
        ''' Pop up a menu to create primitives. '''
        menu = show_menu()

        menu.AppendSeparator()

        snap = menu.Append(wx.ID_ANY, text='Snap to bounds')
        self.Bind(wx.EVT_MENU, lambda e: self.snap_bounds(), snap)

        # Get the a target primitive to delete
        self.mouse = wx.Point(event.GetX(), event.GetY())
        x, y = self.pixel_to_pos(*self.mouse)
        t = koko.PRIMS.get_target(x, y)
        delete = menu.Append(wx.ID_ANY, text='Delete')
        if t is not None:
            self.Bind(wx.EVT_MENU, lambda e: koko.PRIMS.delete(t), delete)
        else:
            delete.Enable(False)

        undo = menu.Append(wx.ID_ANY, text='Undo')
        if koko.PRIMS.can_undo:
            self.Bind(wx.EVT_MENU, koko.PRIMS.undo, undo)
        else:
            undo.Enable(False)

        self.PopupMenu(menu)

########################################

    def char(self, event):
        """ @brief Keyboard callback
            @details Recognizes Ctrl+Z as Undo and Delete to delete primitive
        """
        if event.CmdDown() and event.GetKeyCode() == ord('Z'):
            if koko.PRIMS.can_undo: koko.PRIMS.undo()
        elif event.GetKeyCode() == 127:

            x, y = self.pixel_to_pos(*self.mouse)

            t = koko.PRIMS.get_target(x, y)
            koko.PRIMS.delete(t)
        else:
            event.Skip()

########################################

    def mouse_dclick(self, event):
        '''Double-click to open up the point editing box.'''
        self.mouse = wx.Point(event.GetX(), event.GetY())
        x, y = self.pixel_to_pos(*self.mouse)
        target = koko.PRIMS.get_target(x, y)
        if target is not None:
            target.open_panel()

########################################

    def mouse_scroll(self, event):
        '''Handles mouse scrolling by adjusting window scale.'''
        width, height = self.Size

        origin = ((width/2 - self.mouse[0]) / self.scale - self.center[0],
                  (self.mouse[1] - height/2) / self.scale - self.center[1])

        dScale = 1.0025
        if event.GetWheelRotation() < 0:
            dScale = 1 / dScale
        for i in range(abs(event.GetWheelRotation())):
            self.scale *= dScale
        if self.scale > (1 << 32):
            self.scale = 1 << 32

        # Reposition the center so that the point under the mouse cursor remains
        # under the mouse cursor post-zoom.
        self.center = ((width/2 - self.mouse[0]) / self.scale - origin[0],
                       (self.mouse[1] - height/2) / self.scale - origin[1])

        self.mark_changed_view()
        self.Refresh()

################################################################################

    def drag(self, dx, dy):
        ''' Drag the canvas around. '''
        self.center = (self.center[0] - dx, self.center[1] - dy)
        self.mark_changed_view()
        self.Refresh()

################################################################################

    def mm_to_pixel(self, x, y=None):
        """ @brief Converts an x, y position in mm into an i,j coordinate
            @details Uses self.mm_per_unit to synchronize scales
            @returns A 2-item tuple representing i,j position
        """
        width, height = self.Size
        xcenter, ycenter = self.center
        xcenter *= self.mm_per_unit
        ycenter *= self.mm_per_unit
        scale = self.scale / self.mm_per_unit

        if y is None:
            return int(x*scale)
        else:
            return map(int,
                [(x - xcenter) * scale + (width / 2.),
                 height/2. - (y - ycenter) * scale]
            )


    def pos_to_pixel(self, x, y=None):
        """ @brief Converts an x, y position in arbitrary units into an i,j coordinate
            @returns A 2-item tuple representing i,j position
        """

        width, height = self.Size
        xcenter, ycenter = self.center

        if y is None:
            return int(x*self.scale)
        else:
            return map(int,
                [(x - xcenter) * self.scale + (width / 2.),
                 height/2. - (y - ycenter) * self.scale]
            )

########################################

    def pixel_to_pos(self, i, j):
        """ @brief Converts an i,j pixel position into an x,y coordinate in arbitrary units.
            @returns A 2-item tuple representing x,y position
        """
        width, height = self.Size
        xcenter, ycenter = self.center

        return ((i - width/2) / self.scale + xcenter,
               (height/2 - j) / self.scale + ycenter)

################################################################################

    def get_crop(self):
        ''' Calculates a cropping rectangle to discard portions of the image
            that do not fit into the current view. '''

        if self.image.xmin < self.xmin*self.mm_per_unit:
            x0 = floor(
                self.image.pixels_per_mm *
                (self.xmin*self.mm_per_unit - self.image.xmin)
            )
        else:
            x0 = 0

        if self.image.xmax > self.xmax*self.mm_per_unit:
            x1 = ceil(
                self.image.width - (self.image.pixels_per_mm *
                (self.image.xmax - self.xmax*self.mm_per_unit))
            )
        else:
            x1 = self.image.width

        if self.image.ymin < self.ymin*self.mm_per_unit:
            y1 = ceil(
                self.image.height - (self.image.pixels_per_mm *
                (self.ymin*self.mm_per_unit - self.image.ymin))
            )
        else:
            y1 = self.image.height

        if self.image.ymax > self.ymax*self.mm_per_unit:
            y0 = floor(
                self.image.pixels_per_mm *
                (self.image.ymax - self.ymax*self.mm_per_unit)
            )
        else:
            y0 = 0

        return wx.Rect(x0, y0, x1-x0, y1 - y0)

################################################################################

    def paint(self, event=None):
        '''Redraws the window.'''

        self.dc = wx.PaintDC(self)
        self.dc.SetBackground(wx.Brush((20,20,20)))
        self.dc.Clear()

        # Draw the active iamge
        self.draw_image()

        # Draw bounds only if 'Show bounds' is checked
        if koko.FRAME.get_menu('View','Show bounds').IsChecked():
            self.draw_bounds()

        # Draw x and y axes
        if koko.FRAME.get_menu('View','Show axes').IsChecked():
            self.draw_axes()

        self.draw_paths()

        # Draw border
        self.draw_border()

        koko.PRIMS.draw(self)

        self.dc = None

################################################################################

    def draw_image(self):
        ''' Draws the current image in the dc. '''

        if not self.image:  return


        width, height = self.Size
        xcenter, ycenter = self.center[0], self.center[1]

        if self.scale / self.mm_per_unit == self.image.pixels_per_mm:

            # If the image is at the correct scale, then we're fine
            # to simply render it at its set position
            bitmap = wx.BitmapFromImage(self.image.wximg)
            xmin = self.image.xmin
            ymax = self.image.ymax
        else:

            # Otherwise, we have to rescale the image
            # (and we'll pre-emptively crop it to avoid
            #  blowing it up to a huge size)
            crop = self.get_crop()

            if crop.Width <= 0 or crop.Height <= 0:  return

            scale = self.scale / (self.mm_per_unit * self.image.pixels_per_mm)

            img = self.image.wximg.Copy().GetSubImage(crop)
            if int(img.Width*scale) == 0 or int(img.Height*scale) == 0:
                return

            img.Rescale(img.Width  * scale,
                        img.Height * scale)
            bitmap = wx.BitmapFromImage(img)

            xmin = (
                self.image.xmin +
                crop.Left*self.image.mm_per_pixel
            )
            ymax = (
                self.image.ymax -
                crop.Top*self.image.mm_per_pixel
            )

        # Draw image
        imgX, imgY = self.mm_to_pixel(xmin, ymax)

        self.dc.SetBrush(wx.Brush((0,0,0)))
        self.dc.SetPen(wx.TRANSPARENT_PEN)
        self.dc.DrawRectangle(imgX, imgY, bitmap.Width, bitmap.Height)
        self.dc.DrawBitmap(bitmap, imgX, imgY)


    def load_paths(self, paths, xmin, ymin):
        """ @brief Loads a set of toolpaths
            @details Can be called from a separate thread; uses self._load_paths to actually store data.
            @param paths List of Path objects
            @param xmin Left X coordinate (in mm) for alignment
            @param ymin Bottom Y coordinate (in mm) for alignment
        """
        cuts = []
        for p in paths:
            if p.closed:
                cuts.append(
                    np.append(p.points[:,0:2], [p.points[0,0:2]], axis=0)
                )
            else:
                cuts.append(np.copy(p.points[:,0:2]))
            cuts[-1][:,0] += xmin
            cuts[-1][:,1] += ymin

        traverses = np.empty((0, 6))
        for i in range(len(paths)-1):
            p = paths[i]
            start = p.points[0,:] if p.closed else p.points[-1,:]
            end = paths[i+1].points[0,:]
            traverses = np.append(traverses,
                [np.append(start, end)], axis=0)

        traverses[:,0] += xmin
        traverses[:,1] += ymin
        traverses[:,3] += xmin
        traverses[:,4] += ymin
        wx.CallAfter(self._load_paths, cuts, traverses)


    def _load_paths(self, paths, traverses):
        """ @brief Stores paths and traverses then refreshes canvas
            @details Should only be called from main thread
        """
        self.paths = paths
        self.traverses = traverses
        self.Refresh()


    def clear(self):
        """ @brief Clears stored images and paths; redraws canvas.
        """
        self.images = []
        self.image  = None
        self.paths = None
        self.Refresh()


    def clear_path(self):
        """ @brief Clears stored paths; redraws canvas.
        """
        self.paths = None
        self.Refresh()
        return


    def draw_paths(self):
        """ @brief Draws stored paths (and possibly traverses)
        """
        if self.paths is None:  return

        self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        self.dc.SetPen(wx.Pen((100,255,150), 1))

        scale = self.scale / self.mm_per_unit
        center = (
            self.center[0] * self.mm_per_unit,
            self.center[1] * self.mm_per_unit
        )

        for i in range(len(self.paths)):

            d = i/float(len(self.paths))
            self.dc.SetPen(wx.Pen((100*d,200*d+50,255*(1-d)), 1))

            p = self.paths[i]
            i = (p[:,0] - center[0]) * scale + self.Size[0]/2.
            j = self.Size[1]/2. - (p[:,1] - center[1])*scale

            self.dc.DrawLines(zip(i,j))

        if koko.FRAME.get_menu('View','Show traverses').IsChecked():
            self.dc.SetPen(wx.Pen((255,100,100), 1))
            t = self.traverses
            if t is None or t.size == 0:   return

            i0 = (t[:,0] - center[0]) * scale + self.Size[0]/2.
            j0 = self.Size[1]/2. - (t[:,1] - center[1])*scale
            i1 = (t[:,3] - center[0]) * scale + self.Size[0]/2.
            j1 = self.Size[1]/2. - (t[:,4] - center[1])*scale

            self.dc.DrawLineList(zip(i0, j0, i1, j1))


################################################################################

    def draw_axes(self):
        """ @brief Draws x, y, z axes in red, green, and blue.
        """
        def spin(x, y, z, alpha, beta):
            ca, sa = cos(alpha), sin(alpha)
            x, y, z = (ca*x - sa*y, sa*x + ca*y, z)

            cb, sb = cos(beta), sin(beta)
            x, y, z = (x, cb*y + sb*z, -sb*y + cb*z)

            return x, y, z

        center = self.pos_to_pixel(0, 0)
        self.dc.SetPen(wx.Pen((255, 0, 0), 2))
        x, y, z = spin(50, 0, 0, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

        self.dc.SetPen(wx.Pen((0, 255, 0), 2))
        x, y, z = spin(0, 50, 0, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

        self.dc.SetPen(wx.Pen((0, 0, 255), 2))
        x, y, z = spin(0, 0, 50, -self.alpha, -self.beta)
        self.dc.DrawLine(center[0], center[1], center[0] + x, center[1] - y)

################################################################################

    def draw_border(self):
        """ @brief If self.border is set, draw a rectangular border around canvas.
        """
        if self.border:
            self.dc.SetPen(wx.TRANSPARENT_PEN)
            self.dc.SetBrush(wx.Brush(self.border))

            border_width = 3
            self.dc.DrawRectangle(0, 0, self.Size[0], border_width)
            self.dc.DrawRectangle(0, self.Size[1]-border_width,
                                  self.Size[0], border_width)
            self.dc.DrawRectangle(0, 0, border_width, self.Size[1])
            self.dc.DrawRectangle(self.Size[0]-border_width, 0,
                                  border_width, self.Size[1])

################################################################################

    def draw_bounds(self):
        """ @brief Draws rectangular border around individual images.
        """
        for i in self.images:
            scale = self.scale / self.mm_per_unit
            xmin, ymin = self.pos_to_pixel(
                i.xmin / self.mm_per_unit, i.ymin / self.mm_per_unit
            )
            xmax, ymax = self.pos_to_pixel(
                i.xmax / self.mm_per_unit, i.ymax / self.mm_per_unit
            )

            self.dc.SetPen(wx.Pen((128, 128, 128)))
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
            self.dc.DrawRectangle(xmin, ymin, xmax-xmin, ymax-ymin)


################################################################################

    @property
    def xmin(self):
        """ @brief Position of left edge (in arbitrary units) """
        return self.center[0] - self.Size[0]/2./self.scale
    @property
    def xmax(self):
        """ @brief Position of right edge (in arbitrary units) """
        return self.center[0] + self.Size[0]/2./self.scale
    @property
    def ymin(self):
        """ @brief Position of bottom edge (in arbitrary units) """
        return self.center[1] - self.Size[1]/2./self.scale
    @property
    def ymax(self):
        """ @brief Position of top edge (in arbitrary units) """
        return self.center[1] + self.Size[1]/2./self.scale

    @property
    def view(self):
        """ @brief Gets global view description
            @returns Struct with xmin, ymin, xmax, ymax, and pixels_per_unit variables."""
        return Struct(xmin=self.xmin, xmax=self.xmax,
                      ymin=self.ymin, ymax=self.ymax,
                      alpha=self.alpha, beta=self.beta,
                      pixels_per_unit=self.scale)

################################################################################

    def load_image(self, img, mm_per_unit=1):
        """ @brief Loads a single image and sets canvas real-space scale
        """
        self.load_images([img], mm_per_unit)

    def load_images(self, imgs, mm_per_unit=1):
        """ @brief Loads a list of images and sets canvas real-space scale
            @details Thread-safe, using self._load_images to store data
        """
        merged = imgs[0].merge(imgs)
        wx.CallAfter(self._load_images, imgs, merged, mm_per_unit)

    def _load_images(self, imgs, merged, mm_per_unit=1):
        """ @brief Stores a new set of images, merged image, and scale factor.
            @details Should only be called from main thread
        """
        self.images = imgs
        self.image = merged

        if self.snap:
            self.snap_bounds()
            self.snap = False

        self.mm_per_unit = mm_per_unit
        self.Refresh()

################################################################################

    def snap_bounds(self):
        """ @brief Snaps to view centered on the current image.
        """

        if not self.image:  return

        width, height = self.Size

        try:
            self.center = [
                (self.image.xmin + self.image.dx/2.) / self.mm_per_unit,
                (self.image.ymin + self.image.dy/2.) / self.mm_per_unit
            ]

            self.scale = float(
                min(width/(self.image.dx/self.mm_per_unit),
                    height/(self.image.dy/self.mm_per_unit))
            )
            self.alpha = self.beta = 0
        except TypeError:
            pass
        else:
            self.mark_changed_view()

        self.Refresh()


    def snap_axis(self, axis):
        """ @brief Snaps to view along a particular axis.
        """

        if axis == '+x':
            self.alpha, self.beta = pi/2, -pi/2
        elif axis == '+y':
            self.alpha, self.beta = 0, pi/2
        elif axis == '+z':
            self.alpha, self.beta = 0, 0
        elif axis == '-x':
            self.alpha, self.beta = -pi/2, -pi/2
        elif axis == '-y':
            self.alpha, self.beta = 0, -pi/2
        elif axis == '-z':
            self.alpha, self.beta = 0, pi
        self.mark_changed_view()

        self.Refresh()

########NEW FILE########
__FILENAME__ = dialogs
""" Module containing various wxPython dialogs. """
import  wx

import  koko
import  koko.editor
from    koko.themes import APP_THEME

def warn_changes():
    '''Check to see if the user is ok with abandoning unsaved changes.
       Returns True if we should proceed.'''
    dlg = wx.MessageDialog(None, "All unsaved changes will be lost.",
                           "Warning:",
                           wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_OK

################################################################################

def warning(text):
    '''General-purpose warning box.'''
    message(text, "Warning:", wx.ICON_WARNING)

def error(text):
    '''General-purpose warning box.'''
    message(text, "Error:", wx.ICON_ERROR)

def message(text, title, icon = 0):
    dlg = wx.MessageDialog(None, text, title, wx.OK | icon)
    dlg.ShowModal()
    dlg.Destroy()

################################################################################

def save_as(directory, filename='', extension='.*'):
    '''Prompts a Save As dialog, returning directory, filename.'''

    dlg = wx.FileDialog(None, "Choose a file",
                        directory, '', '*%s' % extension,
                        wx.FD_SAVE)

    if dlg.ShowModal() == wx.ID_OK:
        directory, filename = dlg.GetDirectory(), dlg.GetFilename()

    # Fix for Ubuntu dialog box, which doesn't append extension
    if extension != '.*' and filename[-len(extension):] != extension:
        filename += extension

    dlg.Destroy()
    return directory, filename

################################################################################

def open_file(directory, filename=''):
    '''Prompts an Open dialog, returning directory, filename.'''
    dlg = wx.FileDialog(None, "Choose a file", directory, style=wx.FD_OPEN)

    if dlg.ShowModal() == wx.ID_OK:
        directory, filename = dlg.GetDirectory(), dlg.GetFilename()

    dlg.Destroy()
    return directory, filename

################################################################################

class ResolutionDialog(wx.Dialog):
    ''' Dialog box that allows users to set resolution

        Also includes an extra checked box with caller-defined
        label. '''
    def __init__(self, res, title, cad, checkbox=''):
        wx.Dialog.__init__(self, parent=None, title=title)

        if cad is not None:
            self.dx = cad.dx if cad.dx else 0
            self.dy = cad.dy if cad.dy else 0
            self.dz = cad.dz if cad.dz else 0
            self.mm_per_unit = cad.mm_per_unit

        self.value = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)

        self.value.Bind(wx.EVT_CHAR, self.limit_to_numbers)
        self.value.Bind(wx.EVT_TEXT, self.update_dimensions)
        self.value.Bind(wx.EVT_TEXT_ENTER, self.done)

        self.value.ChangeValue(str(res))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.value, flag=wx.ALL, border=10)
        okButton = wx.Button(self, label='OK')
        okButton.Bind(wx.EVT_BUTTON, self.done)
        hbox.Add(okButton, flag=wx.ALL, border=10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(wx.StaticText(self, wx.ID_ANY, 'Resolution (pixels/mm):'),
                               flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox)


        self.dimensions = wx.StaticText(self, wx.ID_ANY, '')
        vbox.Add(self.dimensions, flag=wx.LEFT | wx.BOTTOM, border=10)

        if checkbox:
            self.check = wx.CheckBox(self, wx.ID_ANY, checkbox)
            self.check.SetValue(True)
            vbox.Add(self.check, flag=wx.LEFT | wx.BOTTOM, border=10)
        else:
            self.check = None

        self.update_dimensions()
        self.SetSizerAndFit(vbox)

    def limit_to_numbers(self, event=None):
        valid = '0123456789'
        if not '.' in self.value.GetValue():
            valid += '.'

        keycode = event.GetKeyCode()
        if keycode < 32 or keycode >= 127 or chr(keycode) in valid:
            event.Skip()

    def update_dimensions(self, event=None):
        if self.mm_per_unit:
            try:
                scale = float(self.value.GetValue()) * self.mm_per_unit
            except ValueError:
                label = '0 x 0 x 0'
            else:
                label = '%i x %i x %i' % (max(1, self.dx*scale),
                                          max(1, self.dy*scale),
                                          max(1, self.dz*scale))
            self.dimensions.SetLabel(label)

    def done(self, event):
        # Get results from UI elements
        self.result = self.value.GetValue()

        if self.check is not None:  self.checked = self.check.IsChecked()
        else:                       self.checked = None

        # Make sure that the result is a valid float
        try:                float(self.result)
        except ValueError:  self.EndModal(wx.ID_CANCEL)
        else:               self.EndModal(wx.ID_OK)

################################################################################

class RenderDialog(wx.Dialog):
    ''' Dialog box that allows users to set resolution and rotation
    '''
    def __init__(self, title, asdf):
        wx.Dialog.__init__(self, parent=None, title=title)

        if asdf is not None:
            self.asdf = asdf

        self.res = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self.alpha = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self.beta = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)

        self.res.Bind(wx.EVT_CHAR, lambda e: self.limit_to_numbers(e, self.res))
        self.alpha.Bind(wx.EVT_CHAR, lambda e: self.limit_to_numbers(e, self.alpha))
        self.beta.Bind(wx.EVT_CHAR, lambda e: self.limit_to_numbers(e, self.beta))

        for d in [self.res, self.alpha, self.beta]:
            d.Bind(wx.EVT_TEXT, self.update_dimensions)
            d.Bind(wx.EVT_TEXT_ENTER, self.done)

        self.res.ChangeValue('10')
        self.alpha.ChangeValue('0')
        self.beta.ChangeValue('0')

        gs = wx.GridSizer(3, 2)
        gs.Add(wx.StaticText(self, wx.ID_ANY, 'Resolution (pixels/mm)'),
                flag=wx.LEFT|wx.TOP, border=10)
        gs.Add(self.res, flag=wx.RIGHT|wx.TOP, border=10)
        gs.Add(wx.StaticText(self, wx.ID_ANY, 'Z rotation (degrees)'),
                flag=wx.LEFT|wx.TOP, border=10)
        gs.Add(self.alpha, flag=wx.RIGHT|wx.TOP, border=10)
        gs.Add(wx.StaticText(self, wx.ID_ANY, 'X\' rotation (degrees)'),
                flag=wx.LEFT|wx.TOP, border=10)
        gs.Add(self.beta, flag=wx.RIGHT|wx.TOP, border=10)

        hbox = wx.BoxSizer(wx.VERTICAL)
        hbox.Add(gs)
        self.dimensions = wx.StaticText(self, wx.ID_ANY, '')
        hbox.Add(self.dimensions, flag=wx.ALL, border=10)
        okButton = wx.Button(self, label='OK')
        okButton.Bind(wx.EVT_BUTTON, self.done)
        hbox.Add(okButton, flag=wx.ALL, border=10)

        self.update_dimensions()
        self.SetSizerAndFit(hbox)

    def limit_to_numbers(self, event, box):
        valid = '0123456789'
        if not '.' in box.GetValue():
            valid += '.'

        keycode = event.GetKeyCode()
        if keycode < 32 or keycode >= 127 or chr(keycode) in valid:
            event.Skip()

    def update_dimensions(self, event=None):
        try:
            res = float(self.res.GetValue())
            alpha = float(self.alpha.GetValue())
            beta = float(self.beta.GetValue())
        except ValueError:
            label = 'Image size: 0 x 0 (x 0)'
        else:
            r = self.asdf.bounding_region(res, alpha, beta)
            label = 'Image size: %i x %i (x %i)' % (r.ni, r.nj, r.nk)
        self.dimensions.SetLabel(label)

    def done(self, event):
        ''' Save results from UI elements in self.results
        '''
        self.results = {
            'resolution':   self.res.GetValue(),
            'alpha':        self.alpha.GetValue(),
            'beta':         self.beta.GetValue()
        }

        for k in self.results:
            try: self.results[k] = float(self.results[k])
            except ValueError:  self.EndModal(wx.ID_CANCEL)
        self.EndModal(wx.ID_OK)

################################################################################

class RescaleDialog(wx.Dialog):
    ''' Dialog box that allows users to rescale an image or asdf '''
    def __init__(self, title, source):
        wx.Dialog.__init__(self, parent=None, title=title)

        for a in ('dx','dy','dz'):
            setattr(self, a, getattr(source, a))

        self.value = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)

        self.value.Bind(wx.EVT_CHAR, self.limit_to_numbers)
        self.value.Bind(wx.EVT_TEXT, self.update_dimensions)
        self.value.Bind(wx.EVT_TEXT_ENTER, self.done)

        self.value.ChangeValue('1')

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.value, flag=wx.ALL, border=10)
        okButton = wx.Button(self, label='OK')
        okButton.Bind(wx.EVT_BUTTON, self.done)
        hbox.Add(okButton, flag=wx.ALL, border=10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(wx.StaticText(self, wx.ID_ANY, 'Scale factor:'),
                               flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox)

        self.dimensions = wx.StaticText(self, wx.ID_ANY, '\n')
        vbox.Add(self.dimensions, flag=wx.LEFT | wx.BOTTOM, border=10)

        self.update_dimensions()
        self.SetSizerAndFit(vbox)

    def limit_to_numbers(self, event=None):
        valid = '0123456789'
        if not '.' in self.value.GetValue():
            valid += '.'

        keycode = event.GetKeyCode()
        if keycode < 32 or keycode >= 127 or chr(keycode) in valid:
            event.Skip()

    def update_dimensions(self, event=None):
        try:
            scale = float(self.value.GetValue())
        except ValueError:
            label = '? x ? x ?'
        else:
            label = '%.1f x %.1f x %.1f mm\n%.1f x %.1f x %.1f"' % (
                self.dx*scale, self.dy*scale, self.dz*scale,
                self.dx*scale/25.4, self.dy*scale/25.4, self.dz*scale/25.4,
            )
        self.dimensions.SetLabel(label)

    def done(self, event):
        # Get results from UI elements
        self.result = self.value.GetValue()

        # Make sure that the result is a valid float
        try:                float(self.result)
        except ValueError:  self.EndModal(wx.ID_CANCEL)
        else:               self.EndModal(wx.ID_OK)

################################################################################

class CheckDialog(wx.Dialog):
    ''' Dialog box with a single check box. '''
    def __init__(self, title, label):
        wx.Dialog.__init__(self, parent=None, title=title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.check = wx.CheckBox(self, wx.ID_ANY, label)
        hbox.Add(self.check, flag=wx.ALL, border=10)
        okButton = wx.Button(self, label='OK')
        okButton.Bind(wx.EVT_BUTTON, self.done)
        hbox.Add(okButton, flag=wx.ALL, border=10)

        self.SetSizerAndFit(hbox)

    def done(self, event):
        self.checked = self.check.IsChecked()
        self.EndModal(wx.ID_OK)

################################################################################

class TextFrame(wx.Frame):
    '''A simple text frame to display the contents of a file
       or software-defined text.'''
    def __init__(self, title, filename=None):
        wx.Frame.__init__(self, koko.FRAME, title=title)

        # Create text pane.
        self.txt = koko.editor.Editor(self, style=wx.NO_BORDER, size=(600, 400))
        self.txt.SetCaretLineVisible(0)
        self.txt.SetReadOnly(True)

        if filename is not None:
            with open(filename, 'r') as f:
                self.txt.text = f.read()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND | wx.ALL, border=5)
        self.SetSizerAndFit(sizer)

        APP_THEME.apply(self)
        self.Show()

    @property
    def text(self):
        return self.txt.text
    @text.setter
    def text(self, value):
        self.txt.text = value

########NEW FILE########
__FILENAME__ = editor
import wx
import wx.py

import re
import inspect
import types

import  koko
from    koko.template import TEMPLATE

import subprocess
import platform

class Editor(wx.py.editwindow.EditWindow):
    '''Derived class for editing design scripts.'''

    def __init__(self, parent, margins=True, **kwargs):

        wx.py.editwindow.EditWindow.__init__(
            self, parent, **kwargs)

        # I don't like the look of the scroll bars on Mac OS 10.6, s
        # let's just disable them here.
        if ('Darwin' in platform.platform() and
            '10.6' in subprocess.check_output('sw_vers')):
                self.SetUseVerticalScrollBar(False)


        self.SetMarginWidth(1, 16)
        self.SetMarginWidth(2, 16)
        self.SetMarginWidth(3, 4)

        if margins:
            # Margin for numbers

            self.SetMarginType(2,wx.stc.STC_MARGIN_NUMBER)

            # Margin for error marks
            self.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
            self.MarkerDefine(0, wx.stc.STC_MARK_SHORTARROW, 'black','red')


        # Line ending mode
        self.SetEOLMode(wx.stc.STC_EOL_LF)

        # Disable text editor callback on line marker changes,
        # to prevent infinite recursion
        self.SetModEventMask(wx.stc.STC_MODEVENTMASKALL &
                            ~wx.stc.STC_MOD_CHANGEMARKER &
                            ~wx.stc.STC_MOD_CHANGESTYLE)

        # Make cmd+left and cmd+right home and end
        self.CmdKeyAssign(wx.stc.STC_KEY_LEFT,
                          wx.stc.STC_SCMOD_CTRL,
                          wx.stc.STC_CMD_VCHOME)
        self.CmdKeyAssign(wx.stc.STC_KEY_RIGHT,
                          wx.stc.STC_SCMOD_CTRL,
                          wx.stc.STC_CMD_LINEEND)
        self.CmdKeyAssign(wx.stc.STC_KEY_UP,
                          wx.stc.STC_SCMOD_CTRL,
                          wx.stc.STC_CMD_DOCUMENTSTART)
        self.CmdKeyAssign(wx.stc.STC_KEY_DOWN,
                          wx.stc.STC_SCMOD_CTRL,
                          wx.stc.STC_CMD_DOCUMENTEND)

        self.CmdKeyAssign(wx.stc.STC_KEY_LEFT,
                          wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT,
                          wx.stc.STC_CMD_VCHOMEEXTEND)
        self.CmdKeyAssign(wx.stc.STC_KEY_RIGHT,
                          wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT,
                          wx.stc.STC_CMD_LINEENDEXTEND)
        self.CmdKeyAssign(wx.stc.STC_KEY_UP,
                          wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT,
                          wx.stc.STC_CMD_DOCUMENTSTARTEXTEND)
        self.CmdKeyAssign(wx.stc.STC_KEY_DOWN,
                          wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT,
                          wx.stc.STC_CMD_DOCUMENTENDEXTEND)


        # Apply a dark theme to the editor
        self.SetCaretForeground('#888888')

        # Add a faint highlight to the selected line
        self.SetCaretLineVisible(True)
        self.SetCaretLineBack('#303030')

        # Don't show horizontal scroll bar
        self.SetUseHorizontalScrollBar(False)

        hideScrollbar = False
        if hideScrollbar:
            self.SetUseHorizontalScrollBar(False)
            dummyScroll = wx.ScrollBar(self)
            dummyScroll.Hide()
            self.SetVScrollBar(dummyScroll)

################################################################################

    def bind_callbacks(self, app):
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self.SetFocus())
        self.Bind(wx.stc.EVT_STC_SAVEPOINTLEFT,     app.savepoint)
        self.Bind(wx.stc.EVT_STC_SAVEPOINTREACHED,  app.savepoint)
        self.Bind(wx.stc.EVT_STC_CHANGE,
                  lambda e: (koko.FRAME.set_hint(self.syntax_hint()),
                             app.mark_changed_design()))


################################################################################

    def load_template(self):
        self.text = TEMPLATE

################################################################################

    def syntax_hint(self):
        line, pos = self.GetCurLine()
        line = line[:pos]

        # Find all "import" statements in the text and run them
        imports = filter(lambda L: 'import' in L, self.text.split('\n'))
        imported = {}
        for i in imports:
            try:    exec(i, imported)
            except (SyntaxError, ImportError):  continue

        for k in imported.keys():
            if (isinstance(imported[k], object) and
                    not isinstance(imported[k], types.FunctionType)):
                imported[k] = imported[k].__init__

        # Filter the functions to only include those that are callable
        # and can be analyzed with inspect.
        for k in imported.keys():
            if not callable(imported[k]):
                del imported[k]
            else:
                try:                inspect.getargspec(imported[k])
                except TypeError:   del imported[k]

        # Remove closed functions (since we're not inside them)
        parens  = re.findall('[a-zA-Z_][0-9a-zA-Z_]*\([^\(]*\)', line)
        while parens:
            for p in parens:    line = line.replace(p, '')
            parens  = re.findall('[a-zA-Z_][0-9a-zA-Z_]*\([^\(]*\)', line)

        # Pick out valid symbols in the line of code
        symbols = re.findall('[a-zA-Z_][0-9a-zA-Z_]*', line)

        # Sort through defined functions for matches
        matches = []
        for sym in symbols[::-1]:
            for k in imported.keys():
                if k.startswith(sym):
                    score = float(len(sym)) / float(len(k))
                    matches += [(score, k)]
            if matches:
                break

        # If we found no valid matches, then stop searching.
        if matches == []:
            return ''

        # Find the match with the highest score.
        match = reduce(lambda x,y: x if x[0] >= y[0] else y, matches)

        # Get the function
        f = imported[match[1]]

        # Get its arguments and defaults
        args = inspect.getargspec(f)

        # Format them nicely
        args = inspect.formatargspec(args.args, args.varargs,
                                     args.keywords, args.defaults)

        # Modify the formatting for a class constructor
        # (or anything starting with the argument 'self')
        if args.startswith('(self, '):
            args = args.replace('(self, ','(') + '    [class]'

        # And return them to the hint
        return match[1] + args

################################################################################

    @property
    def text(self):
        return self.GetText()
    @text.setter
    def text(self, t):
        '''Loads a body of text into the editor, locking and
           unlocking if necessary.'''

        read_only = self.GetReadOnly()
        wx.CallAfter(self.SetReadOnly, False)
        wx.CallAfter(self.SetText, t)
        wx.CallAfter(self.EmptyUndoBuffer)
        wx.CallAfter(self.SetSavePoint)
        wx.CallAfter(self.SetReadOnly, read_only)

################################################################################

    @property
    def error_marker(self):
        return None
    @error_marker.setter
    def error_marker(self, line):
        wx.CallAfter(self.MarkerDeleteAll, 0)
        if line is not None:
            wx.CallAfter(self.MarkerAdd, line, 0)

########NEW FILE########
__FILENAME__ = export
import ctypes
import Queue
import shutil
import subprocess
import tempfile
import threading
import time
import os

import wx

import  koko
import  koko.dialogs as dialogs
from    koko.c.region     import Region

from    koko.fab.asdf     import ASDF
from    koko.fab.path     import Path
from    koko.fab.image    import Image
from    koko.fab.mesh     import Mesh

class ExportProgress(wx.Frame):
    ''' Frame with a progress bar and a cancel button.
        When the cancel button is pressed, events are set.
    '''
    def __init__(self, title, event1, event2):
        self.events = event1, event2

        wx.Frame.__init__(self, parent=koko.FRAME, title=title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.gauge = wx.Gauge(self, wx.ID_ANY, size=(200, 20))
        hbox.Add(self.gauge, flag=wx.ALL, border=10)

        cancel = wx.Button(self, label='Cancel')
        self.Bind(wx.EVT_BUTTON, self.cancel)
        hbox.Add(cancel, flag=wx.ALL, border=10)

        self.SetSizerAndFit(hbox)
        self.Show()

    @property
    def progress(self): return self.gauge.GetValue()
    @progress.setter
    def progress(self, v):  wx.CallAfter(self.gauge.SetValue, v)

    def cancel(self, event):
        for e in self.events:   e.set()

################################################################################

class ExportTaskCad(object):
    ''' A class representing a FabVars export task.

        Requires a filename and cad structure,
        plus optional supporting arguments.
    '''

    def __init__(self, filename, cad, **kwargs):

        self.filename   = filename
        self.extension  = self.filename.split('.')[-1]
        self.cad        = cad
        for k in kwargs:    setattr(self, k, kwargs[k])

        self.event   = threading.Event()
        self.c_event = threading.Event()

        self.window = ExportProgress(
            'Exporting to %s' % self.extension, self.event, self.c_event
        )

        # Create a new thread to run the export in the background
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()


    def export_png(self):
        ''' Exports a png using libtree.
        '''

        if self.make_heightmap:
            out = self.make_image(self.cad.shape)
        else:
            i = 0
            imgs = []
            for e in self.cad.shapes:
                if self.event.is_set(): return
                img = self.make_image(e)
                if img is not None: imgs.append(img)
                i += 1
                self.window.progress = i*90/len(self.cad.shapes)
            out = Image.merge(imgs)

        if self.event.is_set(): return

        self.window.progress = 90
        out.save(self.filename)
        self.window.progress = 100



    def make_image(self, expr):
        ''' Renders a single expression, returning the image
        '''
        zmin = self.cad.zmin if self.cad.zmin else 0
        zmax = self.cad.zmax if self.cad.zmax else 0

        region = Region(
            (self.cad.xmin, self.cad.ymin, zmin),
            (self.cad.xmax, self.cad.ymax, zmax),
            self.resolution*self.cad.mm_per_unit
        )

        img = expr.render(
            region, mm_per_unit=self.cad.mm_per_unit, interrupt=self.c_event
        )

        img.color = expr.color
        return img


    def export_asdf(self):
        ''' Exports an ASDF file.
        '''
        asdf = self.make_asdf(self.cad.shape)
        self.window.progress = 50
        if self.event.is_set(): return
        asdf.save(self.filename)
        self.window.progress = 100


    def export_svg(self):
        ''' Exports an svg file at 90 DPI with per-object colors.
        '''
        xmin = self.cad.xmin*self.cad.mm_per_unit
        dx = (self.cad.xmax - self.cad.xmin)*self.cad.mm_per_unit
        ymax = self.cad.ymax*self.cad.mm_per_unit
        dy = (self.cad.ymax - self.cad.ymin)*self.cad.mm_per_unit
        stroke = max(dx, dy)/100.


        Path.write_svg_header(self.filename, dx, dy)

        i = 0
        for expr in self.cad.shapes:
            # Generate an ASDF
            if self.event.is_set(): return
            asdf = self.make_asdf(expr, flat=True)
            i += 1
            self.window.progress = i*33/len(self.cad.shapes)

            # Find the contours of the ASDF
            if self.event.is_set(): return
            contours = self.make_contour(asdf)
            i += 2
            self.window.progress = i*33/len(self.cad.shapes)

            # Write them out to the SVG file
            for c in contours:
                c.write_svg_contour(
                    self.filename, xmin, ymax, stroke=stroke,
                    color=expr.color if expr.color else (0,0,0)
                )

        Path.write_svg_footer(self.filename)


    def export_stl(self):
        ''' Exports an stl, using an asdf as intermediary.
        '''
        i = 0
        meshes = []
        for expr in self.cad.shapes:

            if self.event.is_set(): return
            asdf = self.make_asdf(expr)
            i += 1
            self.window.progress = i*33/len(self.cad.shapes)

            if self.event.is_set(): return
            mesh = self.make_mesh(asdf)
            i += 2
            self.window.progress = i*33/len(self.cad.shapes)

            if mesh is not None:    meshes.append(mesh)

        if self.event.is_set(): return
        total = Mesh.merge(meshes)
        total.save_stl(self.filename)

    def make_asdf(self, expr, flat=False):
        ''' Renders an expression to an ASDF '''
        if flat:
            region = Region(
                (expr.xmin - self.cad.border*expr.dx,
                 expr.ymin - self.cad.border*expr.dy,
                 0),
                (expr.xmax + self.cad.border*expr.dx,
                 expr.ymax + self.cad.border*expr.dy,
                 0),
                 self.resolution * self.cad.mm_per_unit
            )
        else:
            region = Region(
                (expr.xmin - self.cad.border*expr.dx,
                 expr.ymin - self.cad.border*expr.dy,
                 expr.zmin - self.cad.border*expr.dz),
                (expr.xmax + self.cad.border*expr.dx,
                 expr.ymax + self.cad.border*expr.dy,
                 expr.zmax + self.cad.border*expr.dz),
                 self.resolution * self.cad.mm_per_unit
            )
        asdf = expr.asdf(
            region=region, mm_per_unit=self.cad.mm_per_unit,
            interrupt=self.c_event
        )
        return asdf


    def make_contour(self, asdf):
        contour = asdf.contour(interrupt=self.c_event)
        return contour


    def make_mesh(self, asdf):
        ''' Renders an ASDF to a mesh '''
        if self.use_cms:
            return asdf.triangulate_cms()
        else:
            return asdf.triangulate(interrupt=self.c_event)


    def export_dot(self):
        ''' Saves a math tree as a .dot file. '''

        # Make the cad function and C data structure
        expr = self.cad.shape
        expr.ptr
        self.window.progress = 25

        # Save as a dot file
        expr.save_dot(self.filename, self.dot_arrays)
        self.window.progress = 100


    def run(self):
        getattr(self, 'export_%s' % self.extension)()
        wx.CallAfter(self.window.Destroy)

################################################################################

class ExportTaskASDF(object):
    ''' A class representing an ASDF export task.
    '''

    def __init__(self, filename, asdf, **kwargs):
        self.filename = filename
        self.extension = self.filename.split('.')[-1]
        self.asdf = asdf

        for k in kwargs:    setattr(self, k, kwargs[k])

        self.event = threading.Event()
        self.c_event = threading.Event()

        self.progress = ExportProgress(
            'Exporting to %s' % self.extension, self.event, self.c_event
        )

        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def export_png(self):
        img = self.asdf.render(
            alpha=self.alpha, beta=self.beta, resolution=self.resolution
        )
        self.progress.progress = 90
        img.save(self.filename)
        self.progress.progress = 100

    def export_stl(self):
        mesh = self.asdf.triangulate_cms()
        self.progress.progress = 60
        mesh.save_stl(self.filename)
        self.progress.progress = 100

    def export_asdf(self):
        self.asdf.save(self.filename)
        koko.APP.savepoint(True)
        self.progress.progress = 100

    def run(self):
        getattr(self, 'export_%s' % self.extension)()
        wx.CallAfter(self.progress.Destroy)

########NEW FILE########
__FILENAME__ = asdf
""" Module defining a distance field class. """

import ctypes
from datetime       import datetime
import threading
from math           import sin, cos, radians, log, ceil
import os
import Queue

from koko.c.multithread    import multithread, monothread, threadsafe

from koko.struct    import Struct
from koko.c.libfab  import libfab
from koko.c.asdf    import ASDF as _ASDF
from koko.c.path    import Path as _Path
from koko.c.region  import Region
from koko.c.vec3f   import Vec3f

################################################################################

class ASDF(object):
    ''' Wrapper class that contains an ASDF pointer and
        automatically frees it upon destruction.'''

    def __init__(self, ptr, free=True, color=None):
        """ @brief Creates an ASDF wrapping the given pointer
            @param ptr Target pointer
            @param free Boolean determining if the ASDF is freed upon destruction
            @param color ASDF's color (or None)
        """

        ## @var ptr
        # Pointer to a C ASDF structure
        self.ptr        = ptr

        ## @var free
        # Boolean determining whether the pointer is freed
        self.free       = free

        ## @var color
        # Tuple representing RGB color (or None)
        self.color      = color

        ## @var filename
        # Filename if ASDF was loaded from a file
        self.filename   = None

        ## @var _lock
        # Lock for safe multithreaded operations
        self.lock = threading.Lock()

    @threadsafe
    def __del__(self):
        """ @brief ASDF destructor which frees ASDF is necessary
        """
        if self.free and libfab is not None:
            libfab.free_asdf(self.ptr)

    def lock(self):
        """ @brief Locks the ASDF to prevent interference from other threads
        """
        self._lock.acquire()

    def unlock(self):
        """ @brief Unlocks the ASDF
        """
        self._lock.release()

    def interpolate(self, x, y, z):
        """ @brief Interpolates based on ASDF corners
        """
        return libfab.interpolate(
            self.ptr.contents.d, x, y, z,
            self.X.lower, self.Y.lower, self.Z.lower,
            self.X.upper - self.X.lower,
            self.Y.lower - self.Y.upper,
            self.Z.lower - self.Z.upper
        )

    @property
    def branches(self):
        """ @returns 8-item list, where each item is a branch or None
        """
        b = []
        for i in range(8):
            try:
                self.ptr.contents.branches[i].contents.X
            except ValueError:
                b += [None]
            else:
                b += [ASDF(self.ptr.contents.branches[i], free=False)]
        return b

    @property
    def state(self):
        """ @returns A string describing ASDF state """
        return ['FILLED','EMPTY','BRANCH','LEAF'][self.ptr.contents.state]
    @property
    def d(self):
        """ @returns Array of eight distance samples """
        return [self.ptr.contents.d[i] for i in range(8)]
    @property
    def X(self):
        """ @returns X bounds as an Interval """
        return self.ptr.contents.X
    @property
    def Y(self):
        """ @returns Y bounds as an Interval """
        return self.ptr.contents.Y
    @property
    def Z(self):
        """ @returns Z bounds as Interval """
        return self.ptr.contents.Z

    @property
    def xmin(self):
        """ @returns Minimum x bound (in mm) """
        return self.ptr.contents.X.lower
    @property
    def xmax(self):
        """ @returns Maximum x bound (in mm) """
        return self.ptr.contents.X.upper
    @property
    def dx(self):
        """ @returns X size (in mm) """
        return self.xmax - self.xmin

    @property
    def ymin(self):
        """ @returns Minimum y bound (in mm) """
        return self.ptr.contents.Y.lower
    @property
    def ymax(self):
        """ @returns Maximum y bound (in mm) """
        return self.ptr.contents.Y.upper
    @property
    def dy(self):
        """ @returns Y size (in mm) """
        return self.ymax - self.ymin

    @property
    def zmin(self):
        """ @returns Minimum z bound (in mm) """
        return self.ptr.contents.Z.lower
    @property
    def zmax(self):
        """ @returns Maximum y bound (in mm) """
        return self.ptr.contents.Z.upper
    @property
    def dz(self):
        """ @returns Z size (in mm) """
        return self.zmax - self.zmin
    @property
    def mm_per_unit(self):  return 1


    def rescale(self, mult):
        """ @brief Rescales the ASDF by the given scale factor
            @param mult Scale factor (1 is no change)
            @returns None
        """
        libfab.asdf_scale(self.ptr, mult)

    @property
    def depth(self):
        """ @returns The depth of this ASDF
        """
        return libfab.get_depth(self.ptr)

    @property
    def dimensions(self):
        """ @returns ni, nj, nk tuple of lattice dimensions
        """
        ni = ctypes.c_int()
        nj = ctypes.c_int()
        nk = ctypes.c_int()

        libfab.find_dimensions(self.ptr, ni, nj, nk)
        return ni.value, nj.value, nk.value

    @property
    def cell_count(self):
        """ @returns Number of cells in this ASDF
        """
        return libfab.count_cells(self.ptr)

    @property
    def ram(self):
        """ @returns Number of bytes in RAM this ASDF occupies
        """
        return self.cell_count * ctypes.sizeof(_ASDF)


    def save(self, filename):
        """ @brief Saves the ASDF to file
        """
        libfab.asdf_write(self.ptr, filename)


    @classmethod
    def load(cls, filename):
        """ @brief Loads an ASDF file from disk
            @param cls Class (automatic argument)
            @param filename Filename (string)
            @returns An ASDF loaded from the file
        """
        asdf = cls(libfab.asdf_read(filename))
        asdf.filename = filename
        return asdf


    @classmethod
    def from_vol(cls, filename, ni, nj, nk, offset, mm_per_voxel,
                 merge_leafs=True):
        """ @brief Imports a .vol file
            @param cls Class (automatic argument)
            @param filename Name of .vol file
            @param ni Number of samples in x direction
            @param nj Number of samples in y direction
            @param nk Number of samples in z direction
            @param offset Isosurface density
            @param mm_per_voxel Scaling factor (mm/voxel)
            @param merge_leafs Boolean determining whether leaf cells are merged
            @returns An ASDF representing an isosurface of the .vol data
        """
        asdf = cls(
            libfab.import_vol(
                filename, ni, nj, nk,
                offset, mm_per_voxel, merge_leafs
            )
        )
        return asdf

    @classmethod
    def from_pixels(cls, img, offset, merge_leafs=False):
        """ @brief Imports an Image
            @param cls Class (automatic argument)
            @param img Image object
            @param offset Isosurface level
            @param merge_leafs Boolean determining whether leaf cells are merged
            @returns An ASDF representing the original image
        """
        asdf = cls(libfab.import_lattice(img.pixels, img.width, img.height,
                                          offset, 1/img.pixels_per_mm,
                                          merge_leafs))
        return asdf


    def slice(self, z):
        """ @brief Finds a 2D ASDF at a given z height
            @param z Z height at which to slice the ASDF
            @returns 2D slice of original ASDF
        """
        return ASDF(libfab.asdf_slice(self.ptr, z), color=self.color)


    def bounds(self, alpha=0, beta=0):
        ''' Find the minimum possible bounding box for this ASDF
            rotated with angles alpha and beta. '''

        # Create an array of the eight cube corners
        corners = [Vec3f(self.X.upper if (i & 4) else self.X.lower,
                         self.Y.upper if (i & 2) else self.Y.lower,
                         self.Z.upper if (i & 1) else self.Z.lower)
                   for i in range(8)]

        # Project the corners around
        M = (ctypes.c_float*4)(cos(radians(alpha)), sin(radians(alpha)),
                               cos(radians(beta)),  sin(radians(beta)))
        corners = [libfab.project(c, M) for c in corners]

        # Find and return the bounds
        return Struct(
            xmin=min(c.x for c in corners),
            xmax=max(c.x for c in corners),
            ymin=min(c.y for c in corners),
            ymax=max(c.y for c in corners),
            zmin=min(c.z for c in corners),
            zmax=max(c.z for c in corners)
        )


    def bounding_region(self, resolution, alpha=0, beta=0):
        """ @brief Finds a bounding region with the given rotation
            @param resolution Region resolution (voxels/unit)
            @param alpha Rotation about Z axis
            @param beta Rotation about X axis
        """
        b = self.bounds(alpha, beta)
        return Region(
            (b.xmin, b.ymin, b.zmin),
            (b.xmax, b.ymax, b.zmax),
            resolution
        )


    #
    #   Render to image
    #
    def render(self, region=None, threads=8, alpha=0, beta=0, resolution=10):
        """ @brief Renders to an image
            @param region Render region (default bounding box)
            @param threads Threads to use (default 8)
            @param alpha Rotation about Z axis (default 0)
            @param beta Rotation about X axis (default 0)
            @param resolution Resolution in voxels per mm
            @returns A height-map Image
        """
        return self.render_multi(region, threads, alpha, beta, resolution)[0]


    def render_multi(self, region=None, threads=8,
                     alpha=0, beta=0, resolution=10):
        """ @brief Renders to an image
            @param region Render region (default bounding box)
            @param threads Threads to use (default 8)
            @param alpha Rotation about Z axis (default 0)
            @param beta Rotation about X axis (default 0)
            @resolution Resolution in voxels per mm
            @returns A tuple with a height-map, shaded image, and image with colored normals
        """
        if region is None:
            region = self.bounding_region(resolution, alpha, beta)

        depth   = Image(
            region.ni, region.nj, channels=1, depth=16,
        )
        shaded  = Image(
            region.ni, region.nj, channels=1, depth=16,
        )
        normals = Image(
            region.ni, region.nj, channels=3, depth=8,
        )

        subregions = region.split_xy(threads)

        M = (ctypes.c_float*4)(cos(radians(alpha)), sin(radians(alpha)),
                               cos(radians(beta)), sin(radians(beta)))
        args = [
            (self.ptr, s, M, depth.pixels, shaded.pixels, normals.pixels)
            for s in subregions
        ]
        multithread(libfab.render_asdf_shaded, args)

        for image in [depth, shaded, normals]:
            image.xmin = region.X[0]
            image.xmax = region.X[region.ni]
            image.ymin = region.Y[0]
            image.ymax = region.Y[region.nj]
            image.zmin = region.Z[0]
            image.zmax = region.Z[region.nk]
        return depth, shaded, normals


    def render_distance(self, resolution=10):
        """ @brief Draws the ASDF as a distance field (used for debugging)
            @param resolution Image resolution
            @returns An 16-bit, 1-channel Image showing the distance field
        """
        region = self.bounding_region(resolution)
        image = Image(region.ni, region.nj, channels=1, depth=16)
        image.xmin = region.X[0]
        image.xmax = region.X[region.ni]
        image.ymin = region.Y[0]
        image.ymax = region.Y[region.nj]
        image.zmin = region.Z[0]
        image.zmax = region.Z[region.nk]

        minimum = libfab.asdf_get_min(self.ptr)
        maximum = libfab.asdf_get_max(self.ptr)

        libfab.draw_asdf_distance(
            self.ptr, region, minimum, maximum, image.pixels
        )
        return image


    #
    #   Triangulation functions
    #
    @threadsafe
    def triangulate(self, threads=True, interrupt=None):
        """ @brief Triangulates an ASDF, returning a mesh
            @param threads Boolean determining multithreading
            @param interrupt threading.Event used to abort
            @returns A Mesh containing the triangulated ASDF
        """
        # Create an event to interrupt the evaluation
        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        # Create a set of arguments
        if threads:
            q = Queue.Queue()
            args = []
            for b in self.branches:
                if b is None:   continue
                args.append( (b, halt, q) )

            # Run the triangulation operation in parallel
            multithread(ASDF._triangulate, args, interrupt, halt)

            results = []
            while True:
                try:                results.append(q.get_nowait())
                except Queue.Empty: break
        else:
            results = [self._triangulate(halt)]
        m = Mesh.merge(results)
        m.color = self.color
        return m


    def _triangulate(self, halt, queue=None):
        ''' Triangulates a mesh, storing data in the vdata and idata
            arrays.  Pushes results to the queue.'''

        mesh = Mesh(libfab.triangulate(self.ptr, halt))
        if queue:   queue.put(mesh)
        else:       return mesh


    @threadsafe
    def triangulate_cms(self):
        return Mesh(libfab.triangulate_cms(self.ptr))


    @threadsafe
    def contour(self, interrupt=None):
        """ @brief Contours an ASDF
            @returns A set of Path objects
            @param interrupt threading.Event used to abort run
        """
        # Create an event to interrupt the evaluation
        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        ptr = ctypes.POINTER(ctypes.POINTER(_Path))()
        path_count = monothread(
            libfab.contour, (self.ptr, ptr, halt), interrupt, halt
        )

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return paths


    def histogram(self):
        """ @brief Generates a histogram of cell distribution
            @returns A list of lists of cell counts
        """
        bins = ((ctypes.c_int*4)*self.depth)()

        libfab.asdf_histogram(self.ptr, bins, 0)

        return zip(*map(list, bins))


    def offset(self, o, resolution=10):
        """ @brief Offsets an ASDF
            @details Uses a variation on the Meijster distance transform
            @param o Offset distance (in mm)
            @param resolution Offset render resolution
        """
        return ASDF(libfab.asdf_offset(self.ptr, o, resolution))

################################################################################

from koko.fab.image import Image
from koko.fab.mesh  import Mesh
from koko.fab.path  import Path

########NEW FILE########
__FILENAME__ = fabvars
""" Module defining a container class for CAD state and settings """

import operator

from koko.lib.shapes2d  import color
from koko.fab.tree      import MathTree

class FabVars(object):
    ''' Container class to hold CAD state and settings.'''
    def __init__(self):
        self._shapes     = []
        self._shape      = None
        self.render_mode = None
        self.mm_per_unit = 25.4
        self.border      = 0.05

    @property
    def shapes(self):   return self._shapes
    @shapes.setter
    def shapes(self, value):
        if type(value) not in (list, tuple):
            raise TypeError('cad.shapes must be a list or tuple of MathTree objects')
        value = map(MathTree.wrap, value)
        self._shapes = list(value)
        self._shape = reduce(operator.add,
            [color(s, None) for s in self.shapes]
        )

    @property
    def shape(self):    return self._shape
    @shape.setter
    def shape(self, value): self.shapes = [MathTree.wrap(value)]
    @property
    def function(self): return self.shape
    @function.setter
    def function(self, value):  self.shape = value

    @property
    def render_mode(self):
        return self._render_mode
    @render_mode.setter
    def render_mode(self, value):
        if value not in ['2D','3D',None]:
            raise TypeError("render_mode must be '2D' or '3D'")
        self._render_mode = value

    @property
    def mm_per_unit(self):
        return self._mm_per_unit
    @mm_per_unit.setter
    def mm_per_unit(self, value):
        try:
            self._mm_per_unit = float(value)
        except TypeError:
            raise TypeError("mm_per_unit should be a number.")



    @property
    def xmin(self):
        try:
            dx = (max(s.xmax for s in self.shapes) -
                  min(s.xmin for s in self.shapes))
            return min(s.xmin for s in self.shapes) - dx*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def xmax(self):
        try:
            dx = (max(s.xmax for s in self.shapes) -
                  min(s.xmin for s in self.shapes))
            return max(s.xmax for s in self.shapes) + dx*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dx(self):
        try:    return self.xmax - self.xmin
        except TypeError:   return None

    @property
    def ymin(self):
        try:
            dy = (max(s.ymax for s in self.shapes) -
                  min(s.ymin for s in self.shapes))
            return min(s.ymin for s in self.shapes) - dy*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def ymax(self):
        try:
            dy = (max(s.ymax for s in self.shapes) -
                  min(s.ymin for s in self.shapes))
            return max(s.ymax for s in self.shapes) + dy*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dy(self):
        try:    return self.ymax - self.ymin
        except TypeError:   return None

    @property
    def zmin(self):
        try:
            dz = (max(s.zmax for s in self.shapes) -
                  min(s.zmin for s in self.shapes))
            return min(s.zmin for s in self.shapes) - dz*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def zmax(self):
        try:
            dz = (max(s.zmax for s in self.shapes) -
                  min(s.zmin for s in self.shapes))
            return max(s.zmax for s in self.shapes) + dz*self.border/2.
        except (TypeError, ValueError, AttributeError):   return None
    @property
    def dz(self):
        try:    return self.zmax - self.zmin
        except TypeError:   return None

    @property
    def bounded(self):
        return all(getattr(self, b) is not None for b in
                    ['xmin','xmax','ymin','ymax','zmin','zmax'])


########NEW FILE########
__FILENAME__ = image
""" Module defining a simple image based on a NumPy array. """

import  ctypes
import  math
import  threading

import  wx
import  numpy as np

from    koko.c.libfab       import libfab
from    koko.c.multithread  import multithread
from    koko.c.path         import Path as Path_

from    koko.fab.path       import Path


class Image(object):
    ''' @class Image
        @brief Wraps a numpy array (indexed by row, column) and various parameters
    '''

    def __init__(self, w, h, channels=1, depth=8):
        """ @brief Image constructor
            @param w Image width in pixels
            @param h Image height in pixels
            @param channels Number of channels (1 or 3)
            @param depth Image depth (8, 16, 32, or 'f' for floating-point)
        """

        if depth == 8:      dtype = np.uint8
        elif depth == 16:   dtype = np.uint16
        elif depth == 32:   dtype = np.uint32
        elif depth == 'f':  dtype = np.float32
        else:   raise ValueError("Invalid bit depth (must be 8, 16, or 'f')")

        ## @var array
        # NumPy array storing image pixels
        if channels == 1 or channels == 3:
            self.array = np.zeros( (h, w, channels), dtype=dtype )
        else:
            raise ValueError('Invalid number of channels (must be 1 or 3)')

        ## @var color
        # Base image color (used when merging black-and-white images)
        self.color      = None

        for b in ['xmin','ymin','zmin','xmax','ymax','zmax']:
            setattr(self, b, None)

        ## @var _wx
        # wx.Image representation of this image
        self._wx = None

        ## @var filename
        # String representing filename or None
        self.filename = None

    def __eq__(self, other):
        eq = self.array == other.array
        if eq is False: return False
        else:           return eq.all()

    @property
    def width(self):    return self.array.shape[1]
    @property
    def height(self):   return self.array.shape[0]


    def copy(self, channels=None, depth=None):
        """ @brief Copies an image, optionally changing depth and channel count.
            @returns A copied Image
            @param channels Channel count
            @param depth Depth count
        """

        out = self.__class__(
            self.width, self.height,
            self.channels, self.depth
        )
        out.array = self.array.copy()
        for a in ['xmin','ymin','zmin',
                  'xmax','ymax','zmax']:
            setattr(out, a, getattr(self, a))
        out.color = [c for c in self.color] if self.color else None
        if channels is not None:    out.channels = channels
        if depth is not None:       out.depth = depth
        return out


    def colorize(self, r, g, b):
        """ @brief Creates a colorized image from a black-and-white image.
            @param r Red level (0-1)
            @param b Blue level (0-1)
            @param g Green level (0-1)
            @returns A three-channel 8-bit colorized Image
        """

        if self.channels != 1:
            raise ValueError('Invalid image type for colorizing cut ' +
                '(requires 1-channel image)')

        out = self.__class__(
            self.width, self.height, channels=3, depth=8,
        )

        out.array = np.dstack(
            np.ones((self.width, self.height), dtype=np.uint8)*r,
            np.ones((self.width, self.height), dtype=np.uint8)*g,
            np.ones((self.width, self.height), dtype=np.uint8)*b
        ) * self.copy(channels=3, depth=8).array

        return out


    def __getitem__(self, index):
        """ @brief Overloads image indexing to get pixels
        """
        return self.array[index]


    @property
    def wximg(self):
        """ @brief Returns (after constructing, if necessary) a wx.Image representation of this Image.
        """
        if self._wx is None:
            img = self.copy(channels=3, depth=8)
            self._wx = wx.ImageFromBuffer(img.width, img.height, img.array)
        return self._wx


    @property
    def channels(self): return self.array.shape[2]
    @channels.setter
    def channels(self, c):
        """ @brief Sets the number of channels, convering as needed.
        """
        if c == self.channels: return
        elif c == 1 and self.channels == 3:
            self.array = np.array(np.sum(self.array, axis=2)/3,
                                  dtype=self.array.dtype)
        elif c == 3 and self.channels == 1:
            self.array = np.dstack((self.array,self.array,self.array))
        else:
            raise ValueError('Invalid channel count (must be 1 or 3)')

    @property
    def depth(self):
        if   self.array.dtype == np.uint8:      return 8
        elif self.array.dtype == np.uint16:     return 16
        elif self.array.dtype == np.uint32:     return 32
        elif self.array.dtype == np.float32:    return 'f'
        else:   return None
    @depth.setter
    def depth(self, d):
        """ @brief Sets the image depth, convering as needed.
        """
        if d == self.depth:    return
        elif d == 8:
            if self.depth == 16:
                self.array = np.array(self.array >> 8, dtype=np.uint8)
            elif self.depth == 32:
                self.array = np.array(self.array >> 24, dtype=np.uint8)
            elif self.depth == 'f':
                self.array = np.array(self.array*255, dtype=np.uint8)
        elif d == 16:
            if self.depth == 8:
                self.array = np.array(self.array << 8, dtype=np.uint16)
            elif self.depth == 32:
                self.array = np.array(self.array >> 16, dtype=np.uint16)
            elif self.depth == 'f':
                self.array = np.array(self.array*65535, dtype=np.uint16)
        elif d == 32:
            if self.depth == 8:
                self.array = np.array(self.array << 24, dtype=np.uint32)
            elif self.depth == 16:
                self.array = np.array(self.array << 16, dtype=np.uint32)
            elif self.depth == 'f':
                self.array = np.array(self.array*4294967295., dtype=np.uint32)
        elif d == 'f':
            if self.depth == 8:
                self.array = np.array(self.array/255., dtype=np.float32)
            elif self.depth == 16:
                self.array = np.array(self.array/65535., dtype=np.float32)
            elif self.depth == 32:
                self.array = np.array(self.array/4294967295., dtype=np.float32)
        else:
            raise ValueError("Invalid depth (must be 8, 16, 32, or 'f')")


    @property
    def dx(self):
        try:                return self.xmax - self.xmin
        except TypeError:   return None
    @property
    def dy(self):
        try:                return self.ymax - self.ymin
        except TypeError:   return None
    @property
    def dz(self):
        try:                return self.zmax - self.zmin
        except TypeError:   return None


    @property
    def pixels_per_mm(self):
        """ @brief Parameter to get image pixels/mm
        """
        if self.width > self.height and self.dx is not None:
            return self.width/self.dx
        elif self.dy is not None:
            return self.height/self.dy
        else:       return None
    @property
    def mm_per_pixel(self):
        """ @brief Parameter to get image mm/pixel
        """
        if self.width > self.height and self.dx is not None:
            return self.dx/self.width
        elif self.dy is not None:
            return self.dy/self.height
        else:       return None

    @property
    def bits_per_mm(self):
        if self.dz is None or self.depth is 'f': return None
        elif self.depth == 8:   return 255. / self.dz
        elif self.depth == 16:  return 65535. / self.dz
        elif self.depth == 32:  return 4294967295. / self.dz
    @property
    def mm_per_bit(self):
        if self.dz is None or self.depth is 'f': return None
        elif self.depth == 8:   return self.dz / 255.
        elif self.depth == 16:  return self.dz / 65535.
        elif self.depth == 32:  return self.dz / 4294967295.

    @property
    def dtype(self):
        """ @returns Pixel data type (from ctypes)
        """
        if self.array.dtype == np.uint8:        return ctypes.c_uint8
        elif self.array.dtype == np.uint16:     return ctypes.c_uint16
        elif self.array.dtype == np.uint32:     return ctypes.c_uint32
        elif self.array.dtype == np.float32:    return ctypes.c_float

    @property
    def row_ptype(self):
        """ @returns Row pointer type
        """
        if self.channels == 3:  return ctypes.POINTER(self.dtype*3)
        else:                   return ctypes.POINTER(self.dtype)

    @property
    def pixels(self):
        """ @brief Creates a ctypes pixel array that looks into the NumPy array.
            @returns Pointer of type **dtype if channels is 1, **dtype[3] if channels is 3
        """

        # Make sure that the array is contiguous in memory
        if not self.array.flags['C_CONTIGUOUS']:
            self.array = np.ascontiguousarray(self.array)

        pixels = (self.row_ptype*self.height)()

        start = self.array.ctypes.data
        stride = self.array.ctypes.strides[0]

        for j in range(self.height):
            pixels[self.height-j-1] = ctypes.cast(
                start + j*stride, self.row_ptype
            )

        return pixels


    @property
    def flipped_pixels(self):
        """ @brief Identical to self.pixels, but flipped on the y axis.
        """
        return (self.row_ptype*self.height)(*self.pixels[::-1])



    @classmethod
    def merge(cls, images):
        """ @brief Merges a set of greyscale images into an RGB image.
            @details The input images need to have the same z bounds and scale,
            otherwise the merge will produce something nonsensical.
            @param images List of Images
            @returns 8-bit 3-channel combined Image
        """

        if not images or not all(isinstance(i, Image) for i in images):
            raise TypeError('Invalid argument to merge')

        xmin = min(i.xmin for i in images)
        xmax = max(i.xmax for i in images)
        ymin = min(i.ymin for i in images)
        ymax = max(i.ymax for i in images)

        # Find the target resolution based on the largest image side
        # (to avoid discretization error if we have small and large images)
        largest = 0
        resolution = 0
        for i in images:
            if i.width > largest:
                resolution = i.width / i.dx
                largest = i.width
            elif i.height > largest:
                resolution = i.height / i.dy
                largest = i.height

        out = cls(
            int((xmax-xmin)*resolution),
            int((ymax-ymin)*resolution),
            channels=3, depth=8,
        )
        out.xmin, out.xmax = xmin, xmax
        out.ymin, out.ymax = ymin, ymax
        out.zmin, out.zmax = images[0].zmin, images[0].zmax

        depth = cls(out.width, out.height)

        for img in images:
            img = img.copy(depth=8)

            x  = max(0, int((img.xmin - out.xmin)*resolution))
            ni = min(out.width - x, img.width)
            y  = max(0, int((img.ymin - out.ymin)*resolution))
            nj = min(out.height - y, img.height)

            R, G, B = [c/255. for c in img.color] if img.color else [1, 1, 1]

            libfab.depth_blit(
                img.pixels, depth.pixels, out.pixels,
                x, y, ni, nj,
                R, G, B
            )

        return out


    @classmethod
    def load(cls, filename):
        """ @brief Loads a png from a file as a 16-bit heightmap.
            @param filename Name of target .png image
            @returns A 16-bit, 1-channel image.
        """

        # Get various png parameters so that we can allocate the
        # correct amount of storage space for the new image
        dx, dy, dz = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
        ni, nj = ctypes.c_int(), ctypes.c_int()
        libfab.load_png_stats(filename, ni, nj, dx, dy, dz)

        # Create a python image data structure
        img = cls(ni.value, nj.value, channels=1, depth=16)

        # Add bounds to the image
        if math.isnan(dx.value):
            print 'Assuming 72 dpi for x resolution.'
            img.xmin, img.xmax = 0, 72*img.width/25.4
        else:   img.xmin, img.xmax = 0, dx.value

        if math.isnan(dy.value):
            print 'Assuming 72 dpi for y resolution.'
            img.ymin, img.ymax = 0, 72*img.height/25.4
        else:   img.ymin, img.ymax = 0, dy.value

        if not math.isnan(dz.value):    img.zmin, img.zmax = 0, dz.value

        # Load the image data from the file
        libfab.load_png(filename, img.pixels)
        img.filename = filename

        return img


    def save(self, filename):
        """ @brief Saves an image as a png
            @detail 3-channel images are saved as RGB images without metadata; 1-channel images are saved as 16-bit greyscale images with correct bounds and 'zmax', 'zmin' fields as text chunks.
        """
        if filename[-4:].lower() != '.png':
            raise ValueError('Image must be saved with .png extension')

        if self.channels == 3:
            self.wximg.SaveFile(filename, wx.BITMAP_TYPE_PNG)
        else:
            img = self.copy(channels=1, depth=16)
            bounds = (ctypes.c_float*6)(
                self.xmin, self.ymin, self.zmin if self.zmin else float('nan'),
                self.xmax, self.ymax, self.zmax if self.zmax else float('nan')
            )
            libfab.save_png16L(filename, self.width, self.height,
                                bounds, img.flipped_pixels)


    def threshold(self, z):
        """ @brief Thresholds a heightmap at a given depth.
            @brief Can only be called on an 8, 16, or 32-bit image.
            @param z Z depth (in image units)
            @returns Thresholded image (8-bit, single-channel)
        """

        out = self.__class__(self.width, self.height, channels=1, depth=8)
        for b in ['xmin','xmax','ymin','ymax']:
            setattr(out, b, getattr(self, b))
        out.zmin = out.zmax = z

        if self.depth == 8:     k = int(255*(z-self.zmin) / self.dz)
        elif self.depth == 16:  k = int(65535*(z-self.zmin) / self.dz)
        elif self.depth == 32:  k = int(4294967295*(z-self.zmin) / self.dz)
        elif self.depth == 'f':
            raise ValueError('Cannot take threshold of floating-point image')

        out.array = np.array(self.array >= k, dtype=np.uint8)

        return out


    def finish_cut(self, bit_diameter, overlap, bit_type):
        ''' Calculates xy and yz finish cuts on a 16-bit heightmap
        '''

        if self.depth != 16 or self.channels != 1:
            raise ValueError('Invalid image type for finish cut '+
                '(requires 16-bit, 1-channel image)')

        ptr = ctypes.POINTER(ctypes.POINTER(Path_))()
        path_count = libfab.finish_cut(
            self.width, self.height, self.pixels,
            self.mm_per_pixel, self.mm_per_bit,
            bit_diameter, overlap, bit_type, ptr)

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return paths


    def contour(self, bit_diameter, count=1, overlap=0.5):
        """ @brief Finds a set of isolines on a distance field image.
            @param bit_diameter Tool diameter (in mm)
            @param count Number of offsets
            @param overlap Overlap between offsets
            @returns A list of Paths
        """
        if self.depth != 'f' or self.channels != 1:
            raise ValueError('Invalid image type for contour cut '+
                '(requires floating-point, 1-channel image)')

        max_distance = max(self.array.flatten())
        levels = [bit_diameter/2]
        step = bit_diameter * overlap
        if count == -1:
            while levels[-1] < max_distance:
                levels.append(levels[-1] + step)
            levels[-1] = max_distance
        else:
            for i in range(count-1):
                levels.append(levels[-1] + step)
        levels = (ctypes.c_float*len(levels))(*levels)

        ptr = ctypes.POINTER(ctypes.POINTER(Path_))()
        path_count = libfab.find_paths(
            self.width, self.height, self.pixels,
            1./self.pixels_per_mm, len(levels),
            levels, ptr)

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return Path.sort(paths)


    def distance(self, threads=2):
        """ @brief Finds the distance transform of an input image.
            @param threads Number of threads to use
            @returns A one-channel floating-point image
        """
        input = self.copy(depth=8)

        # Temporary storage for G lattice
        g = self.__class__(
            self.width, self.height,
            channels=1, depth=32
        )
        ibounds = [int(t/float(threads)*self.width) for t in range(threads)]
        ibounds = zip(ibounds, ibounds[1:] + [self.width])

        args1 = [(i[0], i[1], self.width, self.height, input.pixels, g.pixels)
                 for i in ibounds]

        multithread(libfab.distance_transform1, args1)

        del input

        output = self.copy(depth='f')

        jbounds = [int(t/float(threads)*self.height) for t in range(threads)]
        jbounds = zip(jbounds, jbounds[1:] + [self.height])

        args2 = [(j[0], j[1], self.width, self.pixels_per_mm,
                 g.pixels, output.pixels) for j in jbounds]

        multithread(libfab.distance_transform2, args2)

        output.zmin = output.zmax = None

        return output



########NEW FILE########
__FILENAME__ = mesh
""" Module defining Mesh class to store indexed geometry. """

import  ctypes
import  operator
import  os
import  tempfile

from    koko.struct     import Struct

class Mesh(object):
    ''' Mesh objects represent a chunk of indexed geometry.'''

    def __init__(self, ptr, color=None):
        """ @brief Initializes a mesh object from vertex and index array(s).
            @param ptr Pointer to C mesh structure
            @param color Draw color (or None)
        """

        ## @var ptr
        # Pointer to a C Mesh structure
        self.ptr = ptr

        ## @var color
        # Color for mesh drawing operations
        self.color = color

        ## @var source
        # Structure describing source of this mesh (or none)
        # Used in re-rendering operations
        self.source = None

        ## @var cached
        # Temporary file containing this mesh
        self.cached = None

        ## @var children
        # Array of mesh children (for multi-scale meshes)
        self.children = []

    def __del__(self):
        """ @brief Mesh destructor
        """
        if libfab and self.ptr:
            libfab.free_mesh(self.ptr)

    @property
    def X(self):
        if self.ptr:    return self.ptr.contents.X
        else:
            return Interval(
                min(c.X.lower for c in self.children),
                max(c.X.upper for c in self.children)
            )

    @property
    def Y(self):
        if self.ptr:    return self.ptr.contents.Y
        else:
            return Interval(
                min(c.Y.lower for c in self.children),
                max(c.Y.upper for c in self.children)
            )

    @property
    def Z(self):
        if self.ptr:    return self.ptr.contents.Z
        else:
            return Interval(
                min(c.Z.lower for c in self.children),
                max(c.Z.upper for c in self.children)
            )

    @property
    def tcount(self):   return self.ptr.contents.tcount if self.ptr else None
    @property
    def vcount(self):   return self.ptr.contents.vcount if self.ptr else None

    @property
    def vdata(self):    return self.ptr.contents.vdata
    @property
    def tdata(self):    return self.ptr.contents.tdata

    def save_stl(self, filename):
        libfab.save_stl(self.ptr, filename)

    def save(self, filename):
        """ @brief Saves the mesh as an binary stl file or as a binary mesh file
            @param filename Target filename; if it ends in '.stl' an stl will be saved
        """
        if filename[-4:] == '.stl':
            self.save_stl(filename)
        else:
            libfab.save_mesh(filename, self.ptr)

################################################################################

    def refine(self):
        """ @brief Attempts to refine the mesh object, saving this mesh
            in a temporary file.
        """
        if self.cached is None:
            self.cached = tempfile.NamedTemporaryFile()
            self.save(self.cached.name)

        if self.source.type is MathTree:
            self.refine_math()
        elif self.source.type is ASDF:
            self.refine_asdf()


    def refine_math(self):
        """ @brief Refines a mesh based on a math tree
            @details Splits the mesh's bounding box then renders both subregions
            at a higher detail level, saving them in self.children
        """
        region = Region(
            (self.X.lower / self.source.scale,
             self.Y.lower / self.source.scale,
             self.Z.lower / self.source.scale),
            (self.X.upper / self.source.scale,
             self.Y.upper / self.source.scale,
             self.Z.upper / self.source.scale),
             depth=self.source.depth+1
        )

        subregions = region.split()
        meshes = []
        for s in subregions:
            asdf = self.source.expr.asdf(
                region=s, mm_per_unit=self.source.scale
            )
            mesh = asdf.triangulate()

            mesh.source = Struct(
                type=MathTree,
                expr=self.source.expr.clone(),
                depth=self.source.depth+1,
                scale=self.source.scale
            )
            meshes.append(mesh)

        self.children = meshes
        libfab.free_mesh(self.ptr)
        self.ptr = None


    def refine_asdf(self):
        """ @brief Refines a mesh from an .asdf file
            @details Attempts to load .asdf files at a higher recursion level
            and assigns them to self.children
        """
        meshes = []
        for i in range(8):
            filename = self.source.file.replace('.asdf', '%i.asdf' % i)
            asdf = ASDF.load(filename)
            mesh = asdf.triangulate()
            mesh.source = Struct(
                type=ASDF, file=filename, depth=self.source.depth+1
            )
            meshes.append(mesh)

        self.children = meshes
        libfab.free_mesh(self.ptr)
        self.ptr = None


    def expandable(self):
        """ @brief Returns True if this mesh can be refined.
        """
        if self.source is None:
            return False
        elif self.source.type is MathTree:
            return True
        elif self.source.type is ASDF:
            return all(
                os.path.exists(
                    self.source.file.replace('.asdf', '%i.asdf' % i)
                ) for i in range(8)
            )
        return False


    def collapse(self):
        """ @brief Collapses the mesh, deleting children and re-rendering at
        the mesh's resolution.
        """
        if self.cached:
            mesh = Mesh.load(self.cached.name)
        elif self.source.type is MathTree:
            mesh = self.collapse_tree()
        elif self.source.type is ASDF:
            mesh = self.collapse_asdf()

        # Steal the mesh object by moving pointers around
        self.ptr = mesh.ptr
        mesh.ptr = None
        self.children = []


    def collapse_tree(self):
        """ @brief Re-renders from the source math tree
        """
        region = Region(
            (self.X.lower / self.source.scale,
             self.Y.lower / self.source.scale,
             self.Z.lower / self.source.scale),
            (self.X.upper / self.source.scale,
             self.Y.upper / self.source.scale,
             self.Z.upper / self.source.scale),
             depth=self.source.depth
        )

        asdf = self.source.expr.asdf(
            region=region, mm_per_unit=self.source.scale
        )
        return asdf.triangulate()


    def collapse_asdf(self):
        """ @brief Reloads from the source .asdf file
        """
        asdf = ASDF.load(self.source.file)
        return asdf.triangulate()


    def leafs(self):
        """ @brief Returns a flat list of leaf cells
            (i.e. cells without children)
        """
        if self.children:
            return reduce(operator.add, [c.leafs() for c in self.children])
        else:
            return [self]


    def get_fills(self, d):
        """ @brief Finds and saves fill percentages of cells with children.
            @param d Dictionary mapping leaf cells to fill percentages.
        """
        if not self.children:   return {}

        out = {}
        score = 0
        for c in self.children:
            out.update(c.get_fills(d))
            if c in out:    score += out[c]
            elif c in d:    score += d[c]
        out[self] = score

        return out


    @classmethod
    def load(cls, filename):
        if filename[-4:] == '.stl':
            return cls.load_stl(filename)
        return cls(libfab.load_mesh(filename))


    @classmethod
    def load_stl(cls, filename):
        return cls(libfab.load_stl(filename))


    @classmethod
    def merge(cls, meshes):
        """ @brief Efficiently combines a set of independent meshes.
            (does not perform vertex deduplication).
        """
        ptrs = (ctypes.POINTER(_Mesh) * len(meshes))(
                *[m.ptr for m in meshes]
        )
        m = cls(libfab.merge_meshes(len(meshes), ptrs))
        return m


from    koko.c.libfab   import libfab
from    koko.c.region   import Region
from    koko.c.mesh     import Mesh as _Mesh
from    koko.c.interval import Interval

from    koko.fab.tree   import MathTree
from    koko.fab.asdf   import ASDF

########NEW FILE########
__FILENAME__ = path
""" Module defining Path class for toolpaths and contours. """

import numpy as np

class Path(object):
    def __init__(self, points, closed=False):
        self.points = points
        self.closed = closed

    def set_z(self, z):
        self.points[:,2] = z

    def offset_z(self, dz):
        self.points[:,2] += dz

    def reverse(self):
        return Path(self.points[::-1], self.closed)

    def __getitem__(self, i):
        return self.points[i]

    def copy(self):
        return Path(self.points.copy(), self.closed)

    @classmethod
    def from_ptr(cls, ptr):
        ''' Imports a path from a path linked list structure.
        '''
        xyz = lambda p: [[p.contents.x, p.contents.y, p.contents.z]]

        start = ptr
        points = np.array(xyz(ptr))

        ptr = ptr.contents.next

        while ptr.contents != start.contents:
            points = np.vstack( (points, xyz(ptr)) )

            # Advance through the linked list
            if bool(ptr.contents.next): ptr = ptr.contents.next
            else:                       break

        closed = (ptr.contents == start.contents)

        return cls(points, closed)


    @property
    def xmin(self): return float(min(self.points[:,0]))
    @property
    def xmax(self): return float(max(self.points[:,0]))
    @property
    def dx(self):   return self.xmax - self.xmin

    @property
    def ymin(self): return float(min(self.points[:,1]))
    @property
    def ymax(self): return float(max(self.points[:,1]))
    @property
    def dy(self):   return self.ymax - self.ymin


    @staticmethod
    def sort(paths):
        ''' Sorts an array of paths such that contained paths
            are before the paths than contain then, and each
            stage greedily picks the nearest valid path to come next.
        '''
        # Create an array such that if before[i,j] is True, path i
        # needs to be cut before path j (because the bounds of path i
        # are contained within the bounds of path j).
        before = np.ones((len(paths), len(paths)), dtype=np.bool)
        xmin = np.array([[p.xmin for p in paths]]*len(paths))
        before &= xmin < xmin.transpose()
        xmax = np.array([[p.xmax for p in paths]]*len(paths))
        before &= xmax > xmax.transpose()
        ymin = np.array([[p.ymin for p in paths]]*len(paths))
        before &= ymin < ymin.transpose()
        ymax = np.array([[p.ymax for p in paths]]*len(paths))
        before &= ymax > ymax.transpose()

        sorted = []

        done = [False]*len(paths)
        pos = np.array([[0, 0]])

        for i in range(len(paths)):
            # Calculate the distances from our current path to the
            # startpoints of other paths (don't have anything before
            # them and aren't already done)
            distances = [
                float('inf') if (any(before[:,i]) or done[i])
                else sum(pow(pos - paths[i].points[0][0:2], 2).flatten())
                for i in range(len(paths))
            ]
            index = distances.index(min(distances))
            done[index] = True
            before[index,:] = False
            sorted.append(paths[index])

            # New position is the end of the path
            if sorted[-1].closed:   pos = sorted[-1].points[0][0:2]
            else:                   pos = sorted[-1].points[-1][0:2]

        return sorted

    @classmethod
    def save_merged_svg(cls, filename, paths, border=0):
        xmin = min(p.xmin for p in paths)
        xmax = max(p.xmax for p in paths)
        ymin = min(p.ymin for p in paths)
        ymax = max(p.ymax for p in paths)

        if border:
            dx = xmax - xmin
            xmin -= dx * border
            xmax += dx * border
            dy = ymax - ymin
            ymin -= dy * border
            ymax += dy * border

        cls.write_svg_header(filename, xmax-xmin, ymax-ymin)
        for p in paths:
            p.write_svg_contour(filename, xmin, ymax)
        cls.write_svg_footer(filename)

    def save_svg(self, filename):
        self.write_svg_header(filename, self.dx, self.dy)
        self.write_svg_contour(filename, self.xmin, self.ymin)
        self.write_svg_footer(filename)

    @classmethod
    def write_svg_header(cls, filename, dx, dy):
        ''' Writes the header to an SVG file.
            dx and dy should be in mm.
        '''
        with open(filename, 'wb') as f:
            f.write(
"""<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>
<!-- Created with kokopelli (kokompe.cba.mit.edu) -->
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg
    xmlns   = "http://www.w3.org/2000/svg"
    width   = "{dx:g}mm"
    height  = "{dy:g}mm"
    units   = "mm"
>""".format(dx=dx, dy=dy))


    @classmethod
    def write_svg_footer(cls, filename):
        ''' Writes the footer to an SVG file.
        '''
        with open(filename, 'a') as f:  f.write('</svg>')


    def write_svg_contour(self, filename, xmin, ymax,
                          stroke=0.1, color=(0,0,0)):
        ''' Saves a single SVG contour at 90 DPI.
        '''
        scale = 90/25.4

        xy = lambda p: (scale*(p[0]-xmin), scale*(ymax-p[1]))

        with open(filename, 'a') as f:

            # Write the opening statement for this path
            f.write(
'  <path style="stroke:rgb(%i,%i,%i); stroke-width:%g; fill:none"'
                % (color[0], color[1], color[2], stroke)
            )

            # Write the first point of the path
            f.write(
'        d="M%g %g' % xy(self.points[0])
            )

            # Write the rest of the points
            for pt in self.points[1:]:  f.write(' L%g %g' % xy(pt))

            if self.closed: f.write(' Z')
            f.write('"/>\n')

########NEW FILE########
__FILENAME__ = tree
""" Module defining MathTree class and helper decorators. """

import  ctypes
import  os, sys
import  threading
import  math
import  Queue

from    koko.c.libfab       import libfab
from    koko.c.interval     import Interval
from    koko.c.region       import Region
from    koko.c.multithread  import multithread, threadsafe

################################################################################

def forcetree(f):
    ''' A decorator that forces function arguments to be
        of MathTree type using MathTree.wrap

        Takes a class method (with cls as its first argument)'''
    def wrapped(*args, **kwargs):
        return f(args[0], *[MathTree.wrap(a) for a in args[1:]],
                 **{a:MathTree.wrap(kwargs[a]) for a in kwargs})
    return wrapped

def matching(f):
    ''' A decorator that ensures that MathTree properties
        (e.g. color) match across all shape inputs, raising an
        exception otherwise. '''
    def wrapped(*args):
        colors = set(a.color for a in args if isinstance(a, MathTree)
                                           and a.shape                                        and a.color is not None)
        if len(colors) > 1:
            raise ValueError(
                'Error:  Cannot combine objects with different colors.')
        out = f(*args)
        if colors:  out.color = colors.pop()
        return out
    return wrapped

################################################################################

class MathTree(object):
    """ @class MathTree
        @brief Represents a distance metric math expression.

        @details
        Arithmetic operators are overloaded to extend the tree with
        either distance metric arithmetic or shape logical expressions,
        depending on the value of the instance variable 'shape'
    """

    def __init__(self, math, shape=False, color=None):
        """ @brief MathTree constructor
            @param math Math string (in prefix notation)
            @param shape Boolean modifying arithmetic operators
            @param color Color tuple or None
        """

        ## @var math
        # Math string (in sparse prefix syntax)
        if type(math) in [int, float]:
            self.math = 'f' + str(math)
        else:
            self.math   = math

        ## @var shape
        # Boolean modify the behavior of arithmetic operators
        self.shape  = shape

        ## @var color
        # Assigned color, or None
        self.color  = color

        self._str   = None
        self._ptr    = None

        ## @var bounds
        # X, Y, Z bounds (or None)
        self.bounds  = [None]*6

        self.lock  = threading.Lock()

    @threadsafe
    def __del__(self):
        """ @brief MathTree destructor """
        if self._ptr is not None and libfab is not None:
            libfab.free_tree(self.ptr)

    @property
    def ptr(self):
        """ @brief Parses self.math and returns a pointer to a MathTree structure
        """
        if self._ptr is None:
            self._ptr = libfab.parse(self.math)
        return self._ptr

    ############################################################################

    @property
    def dx(self):
        try:                return self.xmax - self.xmin
        except TypeError:   return None
    @property
    def dy(self):
        try:                return self.ymax - self.ymin
        except TypeError:   return None
    @property
    def dz(self):
        try:                return self.zmax - self.zmin
        except TypeError:   return None

    @property
    def bounds(self):
        return [self.xmin, self.xmax,
                self.ymin, self.ymax,
                self.zmin, self.zmax]
    @bounds.setter
    def bounds(self, value):
        for b in ['xmin','xmax','ymin','ymax','zmin','zmax']:
            setattr(self, b, value.pop(0))

    @property
    def xmin(self): return self._xmin
    @xmin.setter
    def xmin(self, value):
        if value is None:   self._xmin = None
        else:
            try:    self._xmin = float(value)
            except: raise ValueError('xmin must be a float')
    @property
    def xmax(self): return self._xmax
    @xmax.setter
    def xmax(self, value):
        if value is None:   self._xmax = None
        else:
            try:    self._xmax = float(value)
            except: raise ValueError('xmax must be a float')

    @property
    def ymin(self): return self._ymin
    @ymin.setter
    def ymin(self, value):
        if value is None:   self._ymin = None
        else:
            try:    self._ymin = float(value)
            except: raise ValueError('ymin must be a float')
    @property
    def ymax(self): return self._ymax
    @ymax.setter
    def ymax(self, value):
        if value is None:   self._ymax = None
        else:
            try:    self._ymax = float(value)
            except: raise ValueError('ymax must be a float')

    @property
    def zmin(self): return self._zmin
    @zmin.setter
    def zmin(self, value):
        if value is None:   self._zmin = None
        else:
            try:    self._zmin = float(value)
            except: raise ValueError('zmin must be a float')
    @property
    def zmax(self): return self._zmax
    @zmax.setter
    def zmax(self, value):
        if value is None:   self._zmax = None
        else:
            try:    self._zmax = float(value)
            except: raise ValueError('zmax must be a float')

    @property
    def bounded(self):
        return all(d is not None for d in [self.dx, self.dy, self.dz])

    ############################################################################

    @property
    def color(self):    return self._color
    @color.setter
    def color(self, rgb):
        named = {'red':     (255, 0,   0  ),
                 'blue':    (0,   0,   255),
                 'green':   (0,   255, 0  ),
                 'white':   (255, 255, 255),
                 'grey':    (128, 128, 128),
                 'black':   (0,   0,   0  ),
                 'yellow':  (255, 255, 0  ),
                 'cyan':    (0,   255, 255),
                 'magenta': (255, 0,   255),
                 'teal':    (0, 255, 255),
                 'pink':    (255, 0, 255),
                 'brown':   (145, 82, 45),
                 'tan':     (125, 90, 60),
                 'navy':    (0, 0, 128)}
        if type(rgb) is str and rgb in named:
                self._color = named[rgb]
        elif type(rgb) in [tuple, list] and len(rgb) == 3:
            self._color = tuple(rgb)
        elif rgb is None:
            self._color = rgb
        else:
            raise ValueError('Invalid color (must be integer 3-value tuple or keyword)')

    ############################################################################

    @staticmethod
    def wrap(value):
        ''' Converts a value to a MathTree.

            None values are left alone,
            Strings are assumed to be valid math strings and wrapped
            Floats / ints are converted'''
        if isinstance(value, MathTree):
            return value
        elif value is None:
            return value
        elif type(value) is str:
            return MathTree(value)
        elif type(value) is not float:
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise TypeError('Wrong type for MathTree arithmetic (%s)' %
                                type(value))
        return MathTree.Constant(value)


    @classmethod
    @forcetree
    def min(cls, A, B): return cls('i'+A.math+B.math)

    @classmethod
    @forcetree
    def max(cls, A, B): return cls('a'+A.math+B.math)

    @classmethod
    @forcetree
    def pow(cls, A, B): return cls('p'+A.math+B.math)

    @classmethod
    @forcetree
    def sqrt(cls, A):   return cls('r'+A.math)

    @classmethod
    @forcetree
    def abs(cls, A):    return cls('b'+A.math)

    @classmethod
    @forcetree
    def square(cls, A): return cls('q'+A.math)

    @classmethod
    @forcetree
    def sin(cls, A):    return cls('s'+A.math)

    @classmethod
    @forcetree
    def cos(cls, A):    return cls('c'+A.math)

    @classmethod
    @forcetree
    def tan(cls, A):    return cls('t'+A.math)

    @classmethod
    @forcetree
    def asin(cls, A):   return cls('S'+A.math)

    @classmethod
    @forcetree
    def acos(cls, A):   return cls('C'+A.math)

    @classmethod
    @forcetree
    def atan(cls, A):   return cls('T'+A.math)

    #########################
    #  MathTree Arithmetic  #
    #########################

    # If shape is set, then + and - perform logical combination;
    # otherwise, they perform arithmeic.
    @matching
    @forcetree
    def __add__(self, rhs):
        if self.shape or (rhs and rhs.shape):

            if rhs is None: return self.clone()

            t = MathTree('i'+self.math+rhs.math, True)

            if self.dx is not None and rhs.dx is not None:
                t.xmin = min(self.xmin, rhs.xmin)
                t.xmax = max(self.xmax, rhs.xmax)
            if self.dx is not None and rhs.dy is not None:
                t.ymin = min(self.ymin, rhs.ymin)
                t.ymax = max(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = min(self.zmin, rhs.zmin)
                t.zmax = max(self.zmax, rhs.zmax)

            return t
        else:
            return MathTree('+' + self.math + rhs.math)
    @matching
    @forcetree
    def __radd__(self, lhs):
        if lhs is None:     return self.clone()

        if self.shape or (lhs and lhs.shape):

            t = MathTree('i'+lhs.math+self.math)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = min(self.xmin, lhs.xmin)
                t.xmax = max(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = min(self.ymin, lhs.ymin)
                t.ymax = max(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = min(self.zmin, lhs.zmin)
                t.zmax = max(self.zmax, lhs.zmax)
            return t
        else:
            return MathTree('+' + lhs.math + self.math)

    @matching
    @forcetree
    def __sub__(self, rhs):
        if self.shape or (rhs and rhs.shape):

            if rhs is None: return self.clone()

            t = MathTree('a'+self.math+'n'+rhs.math, True)
            for i in ['xmin','xmax','ymin','ymax','zmin','zmax']:
                setattr(t, i, getattr(self, i))
            return t
        else:
            return MathTree('-'+self.math+rhs.math)

    @matching
    @forcetree
    def __rsub__(self, lhs):
        if self.shape or (lhs and lhs.shape):

            if lhs is None: return MathTree('n' + self.math)

            t = MathTree('a'+lhs.math+'n'+self.math, True)
            for i in ['xmin','xmax','ymin','ymax','zmin','zmax']:
                setattr(t, i, getattr(lhs, i))
            return t
        else:
            return MathTree('-'+lhs.math+self.math)

    @matching
    @forcetree
    def __and__(self, rhs):
        if self.shape or rhs.shape:
            t = MathTree('a' + self.math + rhs.math, True)
            if self.dx is not None and rhs.dx is not None:
                t.xmin = max(self.xmin, rhs.xmin)
                t.xmax = min(self.xmax, rhs.xmax)
            if self.dy is not None and rhs.dy is not None:
                t.ymin = max(self.ymin, rhs.ymin)
                t.ymax = min(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = max(self.zmin, rhs.zmin)
                t.zmax = min(self.zmax, rhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '& operator is undefined for non-shape math expressions.')

    @matching
    @forcetree
    def __rand__(self, lhs):
        if self.shape or lhs.shape:
            t = MathTree('a' + lhs.math + self.math, True)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = max(self.xmin, lhs.xmin)
                t.xmax = min(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = max(self.ymin, lhs.ymin)
                t.ymax = min(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = max(self.zmin, lhs.zmin)
                t.zmax = min(self.zmax, lhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '& operator is undefined for non-shape math expressions.')


    @matching
    @forcetree
    def __or__(self, rhs):
        if self.shape or rhs.shape:
            t = MathTree('i' + self.math + rhs.math, True)
            if self.dx is not None and rhs.dx is not None:
                t.xmin = min(self.xmin, rhs.xmin)
                t.xmax = max(self.xmax, rhs.xmax)
            if self.dy is not None and rhs.dy is not None:
                t.ymin = min(self.ymin, rhs.ymin)
                t.ymax = max(self.ymax, rhs.ymax)
            if self.dz is not None and rhs.dz is not None:
                t.zmin = min(self.zmin, rhs.zmin)
                t.zmax = max(self.zmax, rhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '| operator is undefined for non-shape math expressions.')


    @matching
    @forcetree
    def __ror__(self, lhs):
        if self.shape or lhs.shape:
            t = MathTree('i' + lhs.math + self.math, True)
            if self.dx is not None and lhs.dx is not None:
                t.xmin = min(self.xmin, lhs.xmin)
                t.xmax = max(self.xmax, lhs.xmax)
            if self.dy is not None and lhs.dy is not None:
                t.ymin = min(self.ymin, lhs.ymin)
                t.ymax = max(self.ymax, lhs.ymax)
            if self.dz is not None and lhs.dz is not None:
                t.zmin = min(self.zmin, lhs.zmin)
                t.zmax = max(self.zmax, lhs.zmax)
            return t
        else:
            raise NotImplementedError(
                '| operator is undefined for non-shape math expressions.')

    @forcetree
    def __mul__(self, rhs):
        return MathTree('*' + self.math + rhs.math)

    @forcetree
    def __rmul__(self, lhs):
        return MathTree('*' + lhs.math + self.math)

    @forcetree
    def __div__(self, rhs):
        return MathTree('/' + self.math + rhs.math)

    @forcetree
    def __rdiv__(self, lhs):
        return MathTree('/' + lhs.math + self.math)

    @forcetree
    def __neg__(self):
        return MathTree('n' + self.math, shape=self.shape)


    ###############################
    ## String and representation ##
    ###############################

    def __str__(self):
        if self._str is None:
            self._str = self.make_str()
        return self._str

    def make_str(self, verbose=False):
        """ @brief Converts the object into an infix-notation string

            @details
            Creates a OS pipe, instructs the object to print itself into the pipe, and reads the output in chunks of maximum size 1024.
        """

        # Create a pipe to get the printout
        read, write = os.pipe()

        # Start the print function running in a separate thread
        # (so that we can eat the output and avoid filling the pipe)
        if verbose: printer = libfab.fdprint_tree_verbose
        else:       printer = libfab.fdprint_tree
        t = threading.Thread(target=printer, args=(self.ptr, write))
        t.daemon = True
        t.start()

        s = r = os.read(read, 1024)
        while r:
            r = os.read(read, 1024)
            s += r
        t.join()

        os.close(read)

        return s

    def __repr__(self):
        return "'%s' (tree at %s)" % (self, hex(self.ptr.value))

    def verbose(self):
        return self.make_str(verbose=True)

    def save_dot(self, filename, arrays=False):
        """ @brief Converts math expression to .dot graph description
        """
        if arrays:
            libfab.dot_arrays(self.ptr, filename)
        else:
            libfab.dot_tree(self.ptr, filename)

    @property
    def node_count(self):
        return libfab.count_nodes(self.ptr)

    #################################
    ## Tree manipulation functions ##
    #################################
    @forcetree
    def map(self, X=None, Y=None, Z=None):
        """ @brief Applies a map operator to a tree
            @param X New X function or None
            @param Y New Y function or None
            @param Z New Z function or None
        """
        return MathTree('m'+
                           (X.math if X else ' ')+
                           (Y.math if Y else ' ')+
                           (Z.math if Z else ' ')+
                           self.math,
                      shape=self.shape, color=self.color)

    @forcetree
    def map_bounds(self, X=None, Y=None, Z=None):
        """ @brief Calculates remapped bounds
            @returns Array of remapped bounds
            @param X New X function or None
            @param Y New Y function or None
            @param Z New Z function or None
            @details Note that X, Y, and Z should be the inverse
            of a coordinate mapping to properly transform bounds.
        """
        if self.dx is not None: x = Interval(self.xmin, self.xmax)
        else:                   x = Interval(float('nan'))
        if self.dy is not None: y = Interval(self.ymin, self.ymax)
        else:                   y = Interval(float('nan'))
        if self.dz is not None: z = Interval(self.zmin, self.zmax)
        else:                   z = Interval(float('nan'))

        if self.dx is not None: a = Interval(self.xmin, self.xmax)
        else:                   a = Interval(float('nan'))
        if self.dy is not None: b = Interval(self.ymin, self.ymax)
        else:                   b = Interval(float('nan'))
        if self.dz is not None: c = Interval(self.zmin, self.zmax)
        else:                   c = Interval(float('nan'))

        if X:
            X_p = libfab.make_packed(X.ptr)
            a = libfab.eval_i(X_p, x, y, z)
            libfab.free_packed(X_p)

        if Y:
            Y_p = libfab.make_packed(Y.ptr)
            b = libfab.eval_i(Y_p, x, y, z)
            libfab.free_packed(Y_p)

        if Z:
            Z_p = libfab.make_packed(Z.ptr)
            c = libfab.eval_i(Z_p, x, y, z)
            libfab.free_packed(Z_p)

        bounds = []
        for i in [a,b,c]:
            if math.isnan(i.lower) or math.isnan(i.upper):
                bounds += [None, None]
            else:
                bounds += [i.lower, i.upper]

        return bounds

    @threadsafe
    def clone(self):
        m = MathTree(self.math, shape=self.shape, color=self.color)
        m.bounds = [b for b in self.bounds]
        if self._ptr is not None:
            m._ptr = libfab.clone_tree(self._ptr)
        return m

    #################################
    #    Rendering functions        #
    #################################

    def render(self, region=None, resolution=None, mm_per_unit=None,
               threads=8, interrupt=None):
        """ @brief Renders a math tree into an Image
            @param region Evaluation region (if None, taken from expression bounds)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param threads Number of threads to use
            @param interrupt threading.Event that aborts rendering if set
            @returns Image data structure
        """

        if region is None:
            if self.dx is None or self.dy is None:
                raise Exception('Unknown render region!')
            elif resolution is None:
                raise Exception('Region or resolution must be provided!')
            region = Region(
                (self.xmin, self.ymin, self.zmin if self.zmin else 0),
                (self.xmax, self.ymax, self.zmax if self.zmax else 0),
                resolution
            )

        try:
            float(mm_per_unit)
        except ValueError, TypeError:
            raise ValueError('mm_per_unit must be a number')

        if interrupt is None:   interrupt = threading.Event()
        halt = ctypes.c_int(0)  # flag to abort render
        image = Image(
            region.ni, region.nj, channels=1, depth=16,
        )

        # Divide the task to share among multiple threads
        clones = [self.clone() for i in range(threads)]
        packed = [libfab.make_packed(c.ptr) for c in clones]

        subregions = region.split_xy(threads)

        # Solve each region in a separate thread
        args = zip(packed, subregions, [image.pixels]*threads, [halt]*threads)

        multithread(libfab.render16, args, interrupt, halt)

        for p in packed:    libfab.free_packed(p)

        image.xmin = region.X[0]*mm_per_unit
        image.xmax = region.X[region.ni]*mm_per_unit
        image.ymin = region.Y[0]*mm_per_unit
        image.ymax = region.Y[region.nj]*mm_per_unit
        image.zmin = region.Z[0]*mm_per_unit
        image.zmax = region.Z[region.nk]*mm_per_unit

        return image


    def asdf(self, region=None, resolution=None, mm_per_unit=None,
             merge_leafs=True, interrupt=None):
        """ @brief Constructs an ASDF from a math tree.
            @details Runs in up to eight threads.
            @param region Evaluation region (if None, taken from expression bounds)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param merge_leafs Boolean determining whether leaf cells are combined
            @param interrupt threading.Event that aborts rendering if set
            @returns ASDF data structure
        """

        if region is None:
            if not self.bounded:
                raise Exception('Unknown render region!')
            elif resolution is None:
                raise Exception('Region or resolution must be provided!')
            region = Region(
                (self.xmin, self.ymin, self.zmin if self.zmin else 0),
                (self.xmax, self.ymax, self.zmax if self.zmax else 0),
                resolution
            )

        if interrupt is None:   interrupt = threading.Event()

        # Shared flag to interrupt rendering
        halt = ctypes.c_int(0)

        # Split the region into up to 8 sections
        split = region.octsect(all=True)
        subregions = [split[i] for i in range(8) if split[i] is not None]
        ids = [i for i in range(8) if split[i] is not None]

        threads = len(subregions)
        clones  = [self.clone() for i in range(threads)]
        packed  = [libfab.make_packed(c.ptr) for c in clones]

        # Generate a root for the tree
        asdf = ASDF(libfab.asdf_root(packed[0], region), color=self.color)
        asdf.lock.acquire()

        # Multithread the solver process
        q = Queue.Queue()
        args = zip(packed, ids, subregions, [q]*threads)

        # Helper function to construct a single branch
        def construct_branch(ptree, id, region, queue):
            asdf = libfab.build_asdf(ptree, region, merge_leafs, halt)
            queue.put((id, asdf))

        # Run the constructor in parallel to make the branches
        multithread(construct_branch, args, interrupt, halt)
        for p in packed:    libfab.free_packed(p)

        # Attach the branches to the root
        for s in subregions:
            try:                id, branch = q.get_nowait()
            except Queue.Empty: break
            else:
                # Make sure we didn't get a NULL pointer back
                # (which could occur if the halt flag was raised)
                try: branch.contents
                except ValueError:
                    asdf.lock.release()
                    return None
                asdf.ptr.contents.branches[id] = branch
        libfab.get_d_from_children(asdf.ptr)
        libfab.simplify(asdf.ptr, merge_leafs)
        asdf.lock.release()

        # Set a scale on the ASDF if one was provided
        if mm_per_unit is not None:     asdf.rescale(mm_per_unit)

        return asdf


    def triangulate(self, region=None, resolution=None,
                    mm_per_unit=None, merge_leafs=True, interrupt=None):
        """ @brief Triangulates a math tree (via ASDF)
            @details Runs in up to eight threads
            @param region Evaluation region (if not, taken from expression)
            @param resolution Render resolution in voxels/unit
            @param mm_per_unit Real-world scale
            @param merge_leafs Boolean determining whether leaf cells are combined
            @param interrupt threading.Event that aborts rendering if set
            @returns Mesh data structure
        """
        asdf = self.asdf(region, resolution, mm_per_unit, merge_leafs, interrupt)
        return asdf.triangulate()


    @staticmethod
    def Constant(f):   return MathTree('f%g' % f)

    @staticmethod
    def X():    return MathTree('X')

    @staticmethod
    def Y():    return MathTree('Y')

    @staticmethod
    def Z():    return MathTree('Z')

if libfab:
    X = MathTree.X()
    Y = MathTree.Y()
    Z = MathTree.Z()


from    koko.fab.image      import Image
from    koko.fab.asdf       import ASDF

########NEW FILE########
__FILENAME__ = frame
import os
import sys

import wx
import wx.lib.stattext

import  koko
from    koko.about     import show_about_box

print '\r'+' '*80+'\r[||||||----]    importing koko.canvas',
sys.stdout.flush()
from    koko.canvas    import Canvas

print '\r'+' '*80+'\r[|||||||---]    importing koko.glcanvas',
sys.stdout.flush()
from    koko.glcanvas  import GLCanvas

print '\r'+' '*80+'\r[||||||||--]    importing koko.editor',
sys.stdout.flush()
from    koko.editor    import Editor

from    koko.vol    import ImportPanel

from    koko.themes    import APP_THEME
from    koko.cam.workflow import FabWorkflowPanel

import subprocess

################################################################################

class MainFrame(wx.Frame):

    def __init__(self, app):

        wx.Frame.__init__(self, parent=None)

        # Build menus and bind callback
        self.build_menus(app)

        # Bind idle callback
        self.Bind(wx.EVT_IDLE, app.idle)

        # The main sizer for the application
        sizer = wx.BoxSizer(wx.VERTICAL)
        version = '%s %s' % (koko.NAME, koko.VERSION)
        sizer.Add(wx.StaticText(self, label=version),
                                flag=wx.ALIGN_RIGHT|wx.ALL, border=5)

        # Horizontal sizer that contains script, output, and canvases
        core = wx.BoxSizer(wx.HORIZONTAL)

        koko.IMPORT = ImportPanel(app, self)

        editor_panel = wx.Panel(self)
        editor_sizer = wx.BoxSizer(wx.VERTICAL)

        # Vertical sizer that contains the editor and the output panel
        koko.EDITOR = Editor(editor_panel, style=wx.NO_BORDER, size=(300, 400))
        koko.EDITOR.load_template()
        koko.EDITOR.bind_callbacks(app)

        editor_sizer.Add(koko.EDITOR, proportion=2, flag=wx.EXPAND)
        self.show_editor = lambda b: editor_sizer.ShowItems(b)

        self._output = Editor(editor_panel, margins=False,
                              style=wx.NO_BORDER, size=(300, 100))
        self._output.SetWrapStartIndent(4)
        self._output.SetReadOnly(True)
        self._output.SetCaretLineVisible(False)
        self._output.SetWrapMode(wx.stc.STC_WRAP_WORD)
        editor_sizer.Add(self._output, proportion=1, border=10,
                         flag=wx.EXPAND|wx.TOP)
        editor_panel.SetSizerAndFit(editor_sizer)

        self.show_editor = lambda b: editor_panel.Show(b)

        # Vertical / Horizontal sizer that contains the two canvases
        canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        self.set_canvas_orientation = lambda o: canvas_sizer.SetOrientation(o)

        koko.CANVAS = Canvas(self, app, size=(300, 300))
        canvas_sizer.Add(koko.CANVAS, proportion=1, flag=wx.EXPAND)

        # wx.glcanvas is terrible on wx-gtk.  The command to check whether
        # various attributes are supported doesn't actually work, so we'll do
        # it experimentally: try to construct a GLCanvas with various
        # depth buffer sizes, stopping when one of them works.
        for d in [32, 24, 16, 8]:
            try:    koko.GLCANVAS = GLCanvas(self, size=(300, 300), depth=d)
            except: continue
            else:   break

        canvas_sizer.Add(koko.GLCANVAS, proportion=1, flag=wx.EXPAND)
        koko.GLCANVAS.Hide()

        core.Add(koko.IMPORT,
                flag=wx.EXPAND|wx.RIGHT, border=20)
        koko.IMPORT.Hide()
        core.Add(editor_panel, proportion=4,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        core.Add(canvas_sizer, proportion=6,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        koko.FAB = FabWorkflowPanel(self)
        core.Add(koko.FAB, proportion=3,
                 flag=wx.EXPAND|wx.RIGHT, border=10)
        koko.FAB.Hide()

        sizer.Add(core, proportion=1, flag=wx.EXPAND)

        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._hint = wx.lib.stattext.GenStaticText(self)
        bottom_sizer.Add(self._hint, proportion=1)

        self._status = wx.lib.stattext.GenStaticText(
            self, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE
        )
        bottom_sizer.Add(self._status, proportion=1)

        sizer.Add(bottom_sizer, flag=wx.EXPAND|wx.ALL, border=10)

        self.SetSizerAndFit(sizer)
        APP_THEME.apply(self)

        self._status.SetForegroundColour(wx.Colour(100, 100, 100))

        # By default, hide the output panel
        self._output.Hide()
        self.Layout()

        """
        # Settings for screen recording
        self.SetClientSize((1280, 720))
        self.SetPosition((0,wx.DisplaySize()[1] - self.GetSize()[1]))
        """

        self.Maximize()


################################################################################

    def build_menus(self, app):
        '''Build a set of menus and attach associated callbacks.'''

        def attach(menu, command, callback, shortcut='', help='',
                   wxID=wx.ID_ANY, attach_function = None):
            '''Helper function to add an item to a menu and bind the
               associated callback.'''

            if shortcut:    menu_text = '%s\t%s' % (command, shortcut)
            else:           menu_text = command

            if attach_function is None:
                attach_function = menu.Append

            item = attach_function(wxID, menu_text, help)
            self.Bind(wx.EVT_MENU, callback, item)

            return item

        menu_bar = wx.MenuBar()

        file = wx.Menu()
        attach(file, 'New', app.new, 'Ctrl+N', 'Start a new design', wx.ID_NEW)
        file.AppendSeparator()

        attach(file, 'Open', app.open, 'Ctrl+O', 'Open a design file', wx.ID_OPEN)
        attach(file, 'Reload', app.reload, 'Ctrl+R', 'Reload the current file')

        file.AppendSeparator()

        attach(file, 'Save', app.save, 'Ctrl+S',
               'Save the current file', wx.ID_SAVE)
        attach(file, 'Save As', app.save_as, 'Ctrl+Shift+S',
               'Save the current file', wx.ID_SAVEAS)

        if not 'Darwin' in os.uname():
            file.AppendSeparator()

        attach(file, 'About', show_about_box, '',
               'Display an About box', wx.ID_ABOUT)
        attach(file, 'Exit', app.exit, 'Ctrl+Q',
               'Terminate the program', wx.ID_EXIT)

        menu_bar.Append(file, 'File')

        view = wx.Menu()
        output = attach(view, 'Show output', self.show_output, 'Ctrl+D',
                        'Display errors in a separate pane',
                         attach_function=view.AppendCheckItem)
        script = attach(view, 'Show script', self.show_script, 'Ctrl+T',
                        'Display Python script',
                         attach_function=view.AppendCheckItem)
        script.Toggle()

        view.AppendSeparator()
        attach(view, '2D', app.render_mode,
               attach_function=view.AppendRadioItem)
        attach(view, '3D', app.render_mode,
               attach_function=view.AppendRadioItem)
        attach(view, 'Both', app.render_mode,
               attach_function=view.AppendRadioItem)

        view.AppendSeparator()

        shaders = wx.Menu()
        for s in [
            'Shaded', 'Wireframe',
            'Normals', 'Subdivision'
        ]:
            m = shaders.AppendRadioItem(wx.ID_ANY, s)
            m.Enable(False)
            if s == 'Show shaded':    m.Check(True)
            self.Bind(wx.EVT_MENU, lambda e: self.Refresh(), m)

        view.AppendSubMenu(shaders, 'Shading mode')

        view.AppendSeparator()

        attach(view, 'Show axes', lambda e: self.Refresh(),
               'Display X, Y, and Z axes on frame',
               attach_function=view.AppendCheckItem)
        attach(view, 'Show bounds', lambda e: self.Refresh(),
               'Display object bounds',
               attach_function=view.AppendCheckItem)
        attach(view, 'Show traverses', lambda e: self.Refresh(),
               'Display toolpath traverses',
               attach_function=view.AppendCheckItem)

        view.AppendSeparator()

        attach(view, 'Re-render', app.mark_changed_design, 'Ctrl+Enter',
              'Re-render the output image')


        menu_bar.Append(view, 'View')

        export = wx.Menu()
        attach(export, '.png',  app.export, help='Export to image file')
        attach(export, '.svg',  app.export, help='Export to svg file')
        attach(export, '.stl',  app.export, help='Export to stl file')
        attach(export, '.dot',  app.export, help='Export to dot / Graphviz file')
        export.AppendSeparator()
        attach(export, '.asdf', app.export, help='Export to .asdf file')
        export.AppendSeparator()
        attach(export, 'Show CAM panel', self.show_cam, 'Ctrl+M', '',
               attach_function=export.AppendCheckItem)

        menu_bar.Append(export, 'Export')

        libraries = wx.Menu()

        attach(libraries, 'koko.lib.shapes2d', app.show_library,
               help='2D Shapes library')
        attach(libraries, 'koko.lib.shapes3d', app.show_library,
               help='3D Shapes library')
        attach(libraries, 'koko.lib.text', app.show_library,
               help='Text library')


        menu_bar.Append(libraries, 'Libraries')

        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU_HIGHLIGHT, self.OnMenuHighlight)
        self.Bind(wx.EVT_MENU_CLOSE, self.OnMenuClose)

################################################################################

    @property
    def status(self):
        return self._status.GetLabel()
    @status.setter
    def status(self, value):
        wx.CallAfter(self._status.SetLabel, value)
    def set_status(self, value):
        self.status = value

################################################################################

    @property
    def hint(self):
        return self._hint.GetLabel()
    @hint.setter
    def hint(self, value):
        wx.CallAfter(self._hint.SetLabel, value)
    def set_hint(self, value):
        self.hint = value

################################################################################

    @property
    def output(self):
        return self._output.text
    @output.setter
    def output(self, value):
        self._output.text = value
    def set_output(self, value):
        self.output = value

################################################################################

    def OnMenuHighlight(self, event):
        '''Sets an appropriate hint based on the highlighted menu item.'''
        id = event.GetMenuId()
        item = self.GetMenuBar().FindItemById(id)
        if not item or not item.GetHelp():
            self.hint = ''
        else:
            self.hint = item.GetHelp()

    def OnMenuClose(self, event):
        '''Clears the menu item hint.'''
        self.hint = ''

    def show_output(self, evt):
        ''' Shows or hides the output panel. '''
        if type(evt) is not bool:   evt = evt.Checked()

        if evt:
            if koko.EDITOR.IsShown():
                self._output.Show()
        else:               self._output.Hide()
        self.Layout()

    def show_script(self, evt):
        ''' Shows or hides the script panel. '''
        if type(evt) is not bool:   evt = evt.Checked()

        if evt:
            self.show_editor(True)
            self.set_canvas_orientation(wx.VERTICAL)
        else:
            self.show_editor(False)
            self.set_canvas_orientation(wx.HORIZONTAL)
        self.Layout()

    def show_cam(self, evt):
        if type(evt) is not bool:   evt = evt.Checked()
        koko.FAB.Show(evt)
        self.Layout()

    def show_import(self, evt):
        if type(evt) is not bool:   evt = evt.Checked()
        koko.IMPORT.Show(evt)
        self.Layout()

    def get_menu(self, *args):
        m = [m[0] for m in self.GetMenuBar().Menus
                  if m[1] == args[0]][0]

        m = [m for m in m.GetMenuItems() if m.GetLabel() == args[1]][0]

        sub = m.GetSubMenu()
        if sub is None: return m
        else:           return sub.GetMenuItems()




########NEW FILE########
__FILENAME__ = glcanvas
import  sys
import  os
from    math import pi, degrees
import  operator

import  numpy as np
import  wx
from    wx import glcanvas

import  koko
from    koko.c.vec3f    import Vec3f
from    koko.c.interval import Interval
from    koko.c.libfab   import libfab
from    koko.fab.mesh   import Mesh

try:
    import OpenGL
    from OpenGL.GL      import *
    from OpenGL.arrays  import vbo
    from OpenGL.GL      import shaders
except ImportError:
    print 'kokopelli error: PyOpenGL import failed!'
    sys.exit(1)


class DragHandler(object):
    def deproject(self, dx, dy):
        return Vec3f(
            0.01 / koko.GLCANVAS.scale*dx,
            -0.01 / koko.GLCANVAS.scale*dy
        ).deproject(koko.GLCANVAS.alpha, koko.GLCANVAS.beta)


################################################################################

class GLCanvas(glcanvas.GLCanvas):
    def __init__(self, parent, size=(500, 300), depth=32):
        if 'Linux' in os.uname():
            glcanvas.GLCanvas.__init__(
                self, parent, wx.ID_ANY, size=size,
                attribList=[glcanvas.WX_GL_DOUBLEBUFFER,
                            glcanvas.WX_GL_RGBA,
                            glcanvas.WX_GL_DEPTH_SIZE, depth]
	    )
        elif 'Darwin' in os.uname():
            glcanvas.GLCanvas.__init__(
                self, parent, wx.ID_ANY, size=size,
                style=glcanvas.WX_GL_DOUBLEBUFFER
            )
        else:
            raise Exception('kokopelli does not know how to initialize GLCanvas on this operating system')

        self.context = glcanvas.GLContext(self)
        self.init = False

        self.Bind(wx.EVT_SIZE,       self.evt_size)
        self.Bind(wx.EVT_PAINT,      self.evt_paint)

        self.Bind(wx.EVT_LEFT_DOWN,  self.evt_mouse_left_down)
        self.Bind(wx.EVT_RIGHT_DOWN, self.mouse_rclick)
        self.Bind(wx.EVT_LEFT_UP,    self.evt_mouse_left_up)
        self.Bind(wx.EVT_MOTION,     self.evt_mouse_move)
        self.Bind(wx.EVT_MOUSEWHEEL, self.evt_mouse_scroll)

        self.drag_target = None
        self.hover_target = None
        self.alpha = 0
        self.beta  = 0

        self.scale   = 1
        self._scale  = 1
        self.center  = Vec3f()
        self._center = Vec3f()

        self.meshes     = []
        self.mesh_vbos  = []
        self.leafs      = []

        self.path_vbo   = None

        self.image      = None

        self.loaded     = False
        self.snap       = True

        self.LOD_complete = False

################################################################################

    def clear(self):
        wx.CallAfter(self._clear)

    def _clear(self):
        self.meshes     = []
        self.mesh_vbos  = []
        self.path_vbo   = None
        self.image      = None
        self.Refresh()

    def clear_path(self):
        wx.CallAfter(self._clear_path)

    def _clear_path(self):
        self.path_vbo   = None
        self.Refresh()

    @property
    def texture(self):  return getattr(self, '_texture', None)
    @texture.setter
    def texture(self, value):
        if self.texture is not None:
            glDeleteTextures(self.texture)
        self._texture = value
        return self.texture
################################################################################

    @property
    def border(self):
        try:
            return self._border
        except AttributeError:
            self._border = None
            return self._border
    @border.setter
    def border(self, value):
        self._border = value
        wx.CallAfter(self.Refresh)


    def get_pixels(self):
        width, height = self.GetClientSize()
        glReadBuffer(GL_FRONT)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        return width, height, glReadPixels(2, 2, width,height,
                                           GL_RGB, GL_UNSIGNED_BYTE)

################################################################################

    def evt_size(self, evt=None):
        if not self.init:
            self.init_GL()
        else:
            self.update_viewport()

################################################################################

    def evt_paint(self, evt=None, shader=None):
        if not self.init:
            self.init_GL()
        self.draw(shader)

################################################################################

    def evt_mouse_left_down(self, evt):
        cursor = wx.StockCursor(wx.CURSOR_BLANK)
        self.SetCursor(cursor)
        self.mouse = wx.Point(evt.GetX(), evt.GetY())
        self.drag_target = self.query(evt.GetX(), evt.GetY())
        self.Refresh()

################################################################################

    def evt_mouse_left_up(self, evt):
        cursor = wx.StockCursor(wx.CURSOR_ARROW)
        self.SetCursor(cursor)
        self.drag_target = None
        self.Refresh()

################################################################################

    def spin_handler(self):
        class SpinHandler(DragHandler):
            def drag(self, dx, dy):
                koko.GLCANVAS.alpha = (koko.GLCANVAS.alpha + dx) % 360
                koko.GLCANVAS.beta -= dy
                if   koko.GLCANVAS.beta < 0:   koko.GLCANVAS.beta = 0
                elif koko.GLCANVAS.beta > 180: koko.GLCANVAS.beta = 180
                koko.GLCANVAS.LOD_complete = False
        return SpinHandler()

    def pan_handler(self):
        class PanHandler(DragHandler):
            def drag(self, dx, dy):
                proj = self.deproject(dx, dy)
                koko.GLCANVAS.center.x -= proj.x
                koko.GLCANVAS.center.y -= proj.y
                koko.GLCANVAS.center.z -= proj.z
                koko.GLCANVAS.LOD_complete = False
        return PanHandler()

    def evt_mouse_move(self, evt):
        pos = wx.Point(evt.GetX(), evt.GetY())
        if self.drag_target:
            delta = pos - self.mouse
            self.drag_target.drag(delta.x, delta.y)
        else:
            self.hover_target = self.query(evt.GetX(), evt.GetY())
        self.Refresh()
        self.mouse = pos

################################################################################

    def evt_mouse_scroll(self, evt):
        if wx.GetKeyState(wx.WXK_SHIFT):
            delta = Vec3f(0, 0, 0.01*evt.GetWheelRotation()/self.scale)
            proj = delta.deproject(self.alpha, self.beta)
            self.center.x -= proj.x
            self.center.y -= proj.y
            self.center.z -= proj.z
        else:
            dScale = 1 / 1.0025 if evt.GetWheelRotation() < 0 else 1.0025
            for i in range(abs(evt.GetWheelRotation())):
                self.scale *= dScale
        self.LOD_complete = False
        self.Refresh()

################################################################################

    def update_viewport(self):
        self.SetCurrent(self.context)
        w, h = self.Size
        glViewport(0, 0, w, h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity();

        aspect = w/float(h)

        if aspect > 1:  glFrustum(-aspect, aspect, -1, 1, 1, 9)
        else:           glFrustum(-1, 1, -1/aspect, 1/aspect, 1, 9)

        glMatrixMode(GL_MODELVIEW)

################################################################################

    def compile_shaders(self):

        mesh_vs = """
            #version 120
            attribute vec3 vertex_position;
            attribute vec3 vertex_normal;

            varying vec3 normal;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);

                normal = normalize(gl_NormalMatrix*vertex_normal);
            }
        """
        shaded_fs = """
            #version 120

            varying vec3 normal;
            uniform vec4 color;

            void main() {
                gl_FragColor = vec4(0.1 + 0.9*normal[2]*color[0],
                                    0.1 + 0.9*normal[2]*color[1],
                                    0.1 + 0.9*normal[2]*color[2],
                                    color[3]);
            }
        """

        wire_fs = """
            #version 120

            varying vec3 normal;
            uniform vec4 color;

            void main() {
                float B = normal[2] < 0.0 ? 0.2 : normal[2]*0.8+0.2;
                gl_FragColor = vec4(B*color[0], B*color[1], B*color[2], color[3]);
            }
        """
        norm_fs = """
            #version 120

            varying vec3 normal;

            void main() {
                gl_FragColor = vec4(normal[0]/2 + 0.5,
                                    normal[1]/2 + 0.5,
                                    normal[2]/2 + 0.5, 1.0);
            }
        """


        self.plain_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(shaded_fs,    GL_FRAGMENT_SHADER))
        self.wire_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(wire_fs,      GL_FRAGMENT_SHADER))
        self.norm_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(norm_fs,      GL_FRAGMENT_SHADER))

        flat_vs = """
            #version 120
            attribute vec3 vertex_position;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
            }
        """
        flat_fs = """
            #version 120

            uniform vec4 color;

            void main() {
                gl_FragColor = color;
            }
        """


        self.flat_shader = shaders.compileProgram(
            shaders.compileShader(flat_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(flat_fs,      GL_FRAGMENT_SHADER))

        path_vs = """
            #version 120
            attribute vec3  vertex_position;
            attribute float vertex_color;

            varying float color;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
                color = vertex_color;
            }
        """

        path_fs = """
            #version 120

            varying float color;
            uniform int show_traverses;

            void main() {
                if (color == 0.0)
                    gl_FragColor = vec4(0.9, 0.2, 0.2,
                                        show_traverses > 0.0 ? 0.5 : 0.0);
                else
                    gl_FragColor = vec4(0.3*color + 0.2,
                                        0.8*color + 0.2,
                                        1.0 - color,
                                        0.9);
            }
        """
        self.path_shader = shaders.compileProgram(
            shaders.compileShader(path_vs, GL_VERTEX_SHADER),
            shaders.compileShader(path_fs, GL_FRAGMENT_SHADER))

        tex_vs = """
            #version 120

            attribute vec3 vertex_position;
            attribute vec2 vertex_texcoord;

            varying vec2 texcoord;

            void main()
            {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
                texcoord = vertex_texcoord;
            }
        """
        tex_fs = """
            #version 120

            uniform sampler2D texture;
            varying vec2 texcoord;

            void main()
            {
                vec4 color = texture2D(texture, texcoord);
                if (color[0] != 0.0 || color[1] != 0.0 || color[2] != 0.0)
                    gl_FragColor = color;
                else
                    gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
            }
        """
        self.image_shader = shaders.compileProgram(
            shaders.compileShader(tex_vs, GL_VERTEX_SHADER),
            shaders.compileShader(tex_fs, GL_FRAGMENT_SHADER)
        )

################################################################################

    def init_GL(self):
        self.SetCurrent(self.context)
        self.compile_shaders()

        glEnable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.update_viewport()

        self.init = True

################################################################################

    def load_mesh(self, mesh):
        self.load_meshes([mesh])

    def load_meshes(self, meshes):
        ''' Loads a ctypes array of floats into a vertex buffer object. '''

        # Find useful parameters about the mesh.
        min_corner = Vec3f(min(m.X.lower for m in meshes),
                           min(m.Y.lower for m in meshes),
                           min(m.Z.lower for m in meshes))
        max_corner = Vec3f(max(m.X.upper for m in meshes),
                           max(m.Y.upper for m in meshes),
                           max(m.Z.upper for m in meshes))
        center = (min_corner + max_corner) / 2

        L = (min_corner - center).length()
        scale = 4/L

        self.reload_vbos(meshes)

        wx.CallAfter(self._load_meshes, meshes, scale, center)

    def _load_meshes(self, meshes, scale, center):
        self.meshes = meshes
        self._scale = scale
        self._center = center

        if self.snap:
            self.snap_bounds()
            self.snap = False

        self.reload_vbos()


################################################################################

    def reload_vbos(self, meshes=None):
        mesh_vbos = []

        # Each mesh gets its own VBO.
        # Each leaf gets its own unique color within the mesh VBO

        all_leafs = []
        if meshes is None:  meshes = self.meshes

        for m in meshes:
            leafs = m.leafs()
            all_leafs += leafs
            merged = Mesh.merge(leafs)

            tcounts = [L.tcount for L in leafs]

            mesh_vbos.append(
                (vbo.VBO(merged.vdata, size=merged.vcount*4*6),
                 vbo.VBO(merged.tdata, target=GL_ELEMENT_ARRAY_BUFFER,
                     size=merged.tcount*4*3),
                 tcounts,
                 m, merged)
            )


        wx.CallAfter(self._reload_vbos, mesh_vbos, all_leafs)


    def _reload_vbos(self, mesh_vbos, leafs):
        self.mesh_vbos  = mesh_vbos
        self.leafs      = leafs
        self.Refresh()


################################################################################

    def load_paths(self, paths, xmin, ymin, zmin):
        count = sum(map(lambda p: len(p.points)+p.closed+2, paths))
        vdata = (ctypes.c_float*(count*4))()

        xyz = lambda pt: [pt[0]+xmin, pt[1]+ymin, pt[2]+zmin]

        vindex = 0
        for p in paths:
            vdata[vindex:vindex+4] = xyz(p.points[0]) + [0]
            vindex += 4

            for pt in p.points:
                vdata[vindex:vindex+4] = \
                    xyz(pt) + [0.1+0.9*vindex/float(len(vdata))]
                vindex += 4

            # Close the path
            if p.closed:
                vdata[vindex:vindex+4] = \
                    xyz(p.points[0]) + [0.1+0.9*vindex/float(len(vdata))]
                vindex += 4

            vdata[vindex:vindex+4] = xyz(p.points[-1]) + [0]
            vindex += 4

        path_vbo = vbo.VBO(vdata)
        wx.CallAfter(self._load_paths, path_vbo)

    def _load_paths(self, path_vbo):
        self.path_vbo = path_vbo
        self.Refresh()

################################################################################

    def load_images(self, images):
        wx.CallAfter(self._load_image, images[0].__class__.merge(images))

    def load_image(self, image):
        wx.CallAfter(self._load_image, image)

    def _load_image(self, image):

        image = image.copy(depth=8, channels=3)
        data = np.flipud(image.array)

        self.tex_vbo = vbo.VBO((ctypes.c_float*30)(
            image.xmin, image.ymin, 0, 0, 0,
            image.xmax, image.ymin, 0, 1, 0,
            image.xmax, image.ymax, 0, 1, 1,

            image.xmin, image.ymin, 0, 0, 0,
            image.xmax, image.ymax, 0, 1, 1,
            image.xmin, image.ymax, 0, 0, 1
        ))

        self.texture = glGenTextures(1)
        self.image = image

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, data.flatten())

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        corner = Vec3f(image.xmin, image.ymin, 0)
        self._center = corner + Vec3f(image.dx, image.dy, 0)/2
        self._scale = 4/(Vec3f(image.dx, image.dy, 0)/2).length()

################################################################################

    def draw(self, shader=None):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        shading = koko.FRAME.get_menu('View', 'Shading mode')
        shader = [c.GetLabel() for c in shading if c.IsChecked()][0]

        if shader == 'Show subdivision':
            self.draw_flat(50)
        else:
            self.draw_mesh(shader)

        # Draw set of toolpaths
        if self.path_vbo is not None:
            self.draw_paths()

        # Draw textured rectangle for 2D image
        if self.image is not None:
            self.draw_image()

        # Draw border around window
        if self.border is not None:
            self.draw_border()

        self.SwapBuffers()

################################################################################

    def draw_mesh(self, shader):

        if shader == 'Wireframe':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()
        self.orient()

        current_shader = {'Wireframe': self.wire_shader,
                          'Normals':   self.norm_shader,
                          'Shaded':    self.plain_shader}[shader]

        shaders.glUseProgram(current_shader)

        # Find the positions of shader attributes
        attributes = {}
        for a in ['vertex_position', 'vertex_normal']:
            attributes[a] = glGetAttribLocation(current_shader, a)
            glEnableVertexAttribArray(attributes[a])

        color_loc = glGetUniformLocation(current_shader, 'color')

        # Loop over meshes
        for vertex_vbo, index_vbo, tcounts, multires, mesh in self.mesh_vbos:
            vertex_vbo.bind()
            index_vbo.bind()

            (r,g,b) = multires.color if multires.color else (255, 255, 255)

            if color_loc != -1:
                glUniform4f(color_loc, r/255., g/255., b/255., 1)

            glVertexAttribPointer(
                attributes['vertex_position'], # attribute index
                3,                     # number of components per attribute
                GL_FLOAT,              # data type of each component
                False,                 # Do not normalize components
                6*4,                   # stride length (in bytes)
                vertex_vbo)            # Vertex buffer object

            glVertexAttribPointer(
                attributes['vertex_normal'], 3,
                GL_FLOAT, False, 6*4, vertex_vbo + 12)

            # Draw the triangles stored in the vbo
            glDrawElements(GL_TRIANGLES, sum(tcounts)*3,
                           GL_UNSIGNED_INT, index_vbo)


            index_vbo.unbind()
            vertex_vbo.unbind()

        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        shaders.glUseProgram(0)

        # Draw bounds and axes if the appropriate menu items are checked
        if koko.FRAME.get_menu('View', 'Show bounds').IsChecked():
            self.draw_bounds()
        if koko.FRAME.get_menu('View', 'Show axes').IsChecked():
            self.draw_axes()
        if koko.IMPORT.IsShown():
            self.draw_import_bounds()

        glPopMatrix()

################################################################################

    def sample(self):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.draw_flat()

        width, height = self.GetClientSize()
        glReadBuffer(GL_BACK)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        pixels = glReadPixels(
            2, 2, width,height, GL_RGB, GL_UNSIGNED_BYTE
        )

        count = (ctypes.c_uint32*len(self.leafs))()
        libfab.count_by_color(
            ctypes.c_char_p(pixels), width, height, len(self.leafs), count
        )

        out = {}
        for c, m in zip(count, self.leafs):
            out[m] = c/float(width*height)
        return out


    def draw_flat(self, scale=1):

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()
        self.orient()

        shaders.glUseProgram(self.flat_shader)

        # Find the positions of shader attributes
        attributes = {}
        vertex_loc = glGetAttribLocation(self.flat_shader, 'vertex_position')
        glEnableVertexAttribArray(vertex_loc)
        color_loc = glGetUniformLocation(self.flat_shader, 'color')

        # Loop over meshes
        index = 1
        for vertex_vbo, index_vbo, tcounts, _, mesh in self.mesh_vbos:

            vertex_vbo.bind()
            index_vbo.bind()

            glVertexAttribPointer(
                vertex_loc,            # attribute index
                3,                     # number of components per attribute
                GL_FLOAT,              # data type of each component
                False,                 # Do not normalize components
                6*4,                   # stride length (in bytes)
                vertex_vbo)            # Vertex buffer object


            # Draw leafs from the VBO, with each leaf getting
            # its own unique color.
            offset = 0
            for tcount in tcounts:
                i = index
                b = (i % (256/scale))
                i /= 256/scale
                g = (i % (256/scale))
                i /= 256/scale
                r = (i % (256/scale))
                index += 1

                glUniform4f(
                    color_loc, r/(256./scale), g/(256./scale),
                    b/(256./scale), 1
                )

                glDrawElements(
                    GL_TRIANGLES, tcount*3,
                    GL_UNSIGNED_INT, index_vbo + offset
                )
                offset += tcount*4*3


            index_vbo.unbind()
            vertex_vbo.unbind()

        glDisableVertexAttribArray(vertex_loc)

        shaders.glUseProgram(0)

        glPopMatrix()

    def query(self, px, py):
        bc = koko.IMPORT.bounding_cube()

        # Render an invisible layer with spheres on the minimum
        # and maximum corner of the import bounding box.
        if bc is not None:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

            glPushMatrix()
            self.orient()

            glPushMatrix()
            glTranslate(bc[0], bc[2], bc[4])
            glColor3f(1, 0, 0)
            self.draw_cube(
                Interval(-0.1/self.scale, 0.1/self.scale),
                Interval(-0.1/self.scale, 0.1/self.scale),
                Interval(-0.1/self.scale, 0.1/self.scale)
            )
            glPopMatrix()

            glPushMatrix()
            glTranslate(bc[1], bc[3], bc[5])
            glColor3f(0, 1, 0)
            self.draw_cube(
                Interval(-0.1/self.scale, 0.1/self.scale),
                Interval(-0.1/self.scale, 0.1/self.scale),
                Interval(-0.1/self.scale, 0.1/self.scale)
            )
            glPopMatrix()

            glPopMatrix()

            width, height = self.GetClientSize()
            pixels = glReadPixels(
                px, height-py, 1, 1, GL_RGB, GL_UNSIGNED_BYTE
            )

            if ord(pixels[0]):
                return koko.IMPORT.bottom_drag()
            elif ord(pixels[1]):
                return koko.IMPORT.top_drag()


        if wx.GetKeyState(wx.WXK_SHIFT):
            return self.pan_handler()
        else:
            return self.spin_handler()

################################################################################

    def draw_axes(self):
        glDisable(GL_DEPTH_TEST)
        glScalef(0.5/self.scale, 0.5/self.scale, 0.5/self.scale)
        glLineWidth(2)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        glColor3f(0.2, 0.2, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        glEnd()
        glLineWidth(1)
        glEnable(GL_DEPTH_TEST)

################################################################################

    def draw_cube(self, X, Y, Z):
        glBegin(GL_QUADS)
        for z in (Z.upper, Z.lower):
            glVertex(X.lower, Y.lower, z)
            glVertex(X.lower, Y.upper, z)
            glVertex(X.upper, Y.upper, z)
            glVertex(X.upper, Y.lower, z)
        for y in (Y.upper, Y.lower):
            glVertex(X.lower, y, Z.lower)
            glVertex(X.lower, y, Z.upper)
            glVertex(X.upper, y, Z.upper)
            glVertex(X.upper, y, Z.lower)
        for x in (X.lower, X.upper):
            glVertex(x, Y.lower, Z.lower)
            glVertex(x, Y.lower, Z.upper)
            glVertex(x, Y.upper, Z.upper)
            glVertex(x, Y.upper, Z.lower)
        glEnd()

    def draw_rect(self, X, Y):
        glBegin(GL_QUADS)
        glVertex(X[0], Y[0], 0)
        glVertex(X[1], Y[0], 0)
        glVertex(X[1], Y[1], 0)
        glVertex(X[0], Y[1], 0)
        glEnd()

    def draw_bounds(self):
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glColor3f(0.5, 0.5, 0.5)
        for m in self.meshes:
            self.draw_cube(m.X, m.Y, m.Z)
        if self.image:
            self.draw_rect(
                (self.image.xmin, self.image.xmax),
                (self.image.ymin, self.image.ymax)
            )


    def draw_import_bounds(self):
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Terrible hack to detect if we're dragging one of the
        # import region corners.
        if self.drag_target and hasattr(self.drag_target, 'corner'):
            corner = self.drag_target.corner
            color  = (203/255., 75/255., 22/255.)
        elif self.hover_target and hasattr(self.hover_target, 'corner'):
            corner = self.hover_target.corner
            color  = (70/255., 170/255., 240/255.)
        else:
            corner = None

        glLineWidth(2)
        bc = koko.IMPORT.bounding_cube()
        if bc is None:  return
        glColor3f(38/255., 139/255., 210/255.)

        self.draw_cube(
            Interval(bc[0], bc[1]),
            Interval(bc[2], bc[3]),
            Interval(bc[4], bc[5])
        )
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_DEPTH_TEST)

        if corner == 'min': glColor3f(*color)
        else:               glColor3f(38/255., 139/255., 210/255.)
        glPushMatrix()
        glTranslate(bc[0], bc[2], bc[4])
        self.draw_cube(
            Interval(-0.1/self.scale, 0.1/self.scale),
            Interval(-0.1/self.scale, 0.1/self.scale),
            Interval(-0.1/self.scale, 0.1/self.scale)
        )
        glPopMatrix()

        if corner == 'max': glColor3f(*color)
        else:               glColor3f(38/255., 139/255., 210/255.)
        glPushMatrix()
        glTranslate(bc[1], bc[3], bc[5])
        self.draw_cube(
            Interval(-0.1/self.scale, 0.1/self.scale),
            Interval(-0.1/self.scale, 0.1/self.scale),
            Interval(-0.1/self.scale, 0.1/self.scale)
        )
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)


################################################################################

    def draw_border(self):
        ''' Draws a colored border around the edge of the screen. '''
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        w, h = self.Size
        glViewport(0, 0, w, h)

        aspect = w/float(h)

        if aspect > 1:
            xmin, xmax = -aspect, aspect
            ymin, ymax = -1, 1
        else:
            xmin, xmax = -1, 1
            ymin, ymax = -1/aspect, 1/aspect

        glBegin(GL_QUADS)
        glColor3f(self.border[0]/255.,
                  self.border[1]/255.,
                  self.border[2]/255.)

        glVertex(xmin, ymin, -1)
        glVertex(xmin, ymax, -1)
        glVertex(xmin+0.01, ymax, -1)
        glVertex(xmin+0.01, ymin, -1)

        glVertex(xmin, ymax, -1)
        glVertex(xmax, ymax, -1)
        glVertex(xmax, ymax-0.01, -1)
        glVertex(xmin, ymax-0.01, -1)

        glVertex(xmax-0.01, ymin, -1)
        glVertex(xmax-0.01, ymax, -1)
        glVertex(xmax, ymax, -1)
        glVertex(xmax, ymin, -1)

        glVertex(xmin, ymin+0.01, -1)
        glVertex(xmax, ymin+0.01, -1)
        glVertex(xmax, ymin, -1)
        glVertex(xmin, ymin, -1)

        glEnd()

################################################################################

    def draw_image(self):

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()

        self.orient()

        # Set up various parameters
        shaders.glUseProgram(self.image_shader)
        attributes = {}
        for a in ['vertex_position', 'vertex_texcoord']:
            attributes[a] = glGetAttribLocation(self.image_shader, a)
            glEnableVertexAttribArray(attributes[a])

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glUniform1i(
            glGetUniformLocation(self.image_shader, 'texture'), 0
        )

        self.tex_vbo.bind()
        glVertexAttribPointer(
            attributes['vertex_position'],
            3, GL_FLOAT, False, 5*4, self.tex_vbo
        )
        glVertexAttribPointer(
            attributes['vertex_texcoord'],
            2, GL_FLOAT, False, 5*4, self.tex_vbo+3*4
        )


        glDrawArrays(GL_TRIANGLES,  0, 6)

        # And disable all of those parameter
        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        self.tex_vbo.unbind()
        shaders.glUseProgram(0)

        glPopMatrix()

################################################################################

    def draw_paths(self):
        glLineWidth(2)

        glPushMatrix()

        self.orient()

        current_shader = self.path_shader
        shaders.glUseProgram(current_shader)

        self.path_vbo.bind()

        # Find the positions of shader attributes
        attributes = {}
        for a in ['vertex_position', 'vertex_color']:
            attributes[a] = glGetAttribLocation(current_shader, a)
            glEnableVertexAttribArray(attributes[a])

        # Set vertex attribute pointers
        glVertexAttribPointer(
            attributes['vertex_position'], 3,
            GL_FLOAT, False, 4*4, self.path_vbo)

        glVertexAttribPointer(
            attributes['vertex_color'], 1,
            GL_FLOAT, False, 4*4, self.path_vbo + 12)

        # Show or hide traverses
        t = koko.FRAME.get_menu('View','Show traverses').IsChecked()
        glUniform1i(
            glGetUniformLocation(current_shader, 'show_traverses'),
            1 if t else 0
        )

        # Draw the triangles stored in the vbo
        glDrawArrays(GL_LINE_STRIP, 0, len(self.path_vbo)/4)

        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        self.path_vbo.unbind()

        shaders.glUseProgram(0)

        glPopMatrix()
        glLineWidth(1)

################################################################################

    def orient(self):
        glTranslatef(0, 0, -5)
        glScalef(self.scale, self.scale, self.scale)
        glRotatef(-self.beta,  1, 0, 0)
        glRotatef(self.alpha, 0, 0, 1)
        glTranslatef(-self.center.x, -self.center.y, -self.center.z)

    def snap_bounds(self):
        ''' Snap to saved center and model scale. '''
        self.center = self._center.copy()
        self.scale  = self._scale
        self.Refresh()

    def snap_axis(self, axis):
        ''' Snaps to view along a particular axis. '''

        if axis == '-x':
            self.alpha, self.beta = 90, 90
        elif axis == '-y':
            self.alpha, self.beta = 0, 90
        elif axis == '+z':
            self.alpha, self.beta = 0, 0
        elif axis == '+x':
            self.alpha, self.beta = 270, 90
        elif axis == '+y':
            self.alpha, self.beta = 180, 90
        elif axis == '-z':
            self.alpha, self.beta = 0, 180
        self.Refresh()

    def mouse_rclick(self, event):
        menu = wx.Menu()
        snap = menu.Append(wx.ID_ANY, text='Snap to bounds')
        self.Bind(wx.EVT_MENU, lambda e: self.snap_bounds(), snap)

        axes = wx.Menu()
        for a in ['+x','-x','+y','-y','+z','-z']:
            self.Bind(wx.EVT_MENU, lambda e,x=a: self.snap_axis(x),
                      axes.Append(wx.ID_ANY, a))
        menu.AppendMenu(wx.ID_ANY, 'View axis', axes)
        self.PopupMenu(menu)


########NEW FILE########
__FILENAME__ = pcb
import operator
from math import cos, sin, atan2, radians, degrees, sqrt

import koko.lib.shapes2d as s2d
from koko.lib.text import text

class PCB(object):
    def __init__(self, x0, y0, width, height):
        self.x0 = x0
        self.y0 = y0
        self.width = width
        self.height = height

        self.components  = []
        self.connections = []

        self._cutout = None

    @property
    def traces(self):
        L = [c.pads for c in self.components] + [c.traces for c in self.connections]
        shape = reduce(operator.add, L) if L else None
        shape.bounds = self.cutout.bounds
        return shape

    @property
    def part_labels(self):
        L = [c.label for c in self.components if c.label is not None]
        shape = reduce(operator.add, L) if L else None
        shape.bounds = self.cutout.bounds
        return shape

    @property
    def pin_labels(self):
        L = [c.pin_labels for c in self.components if c.pin_labels is not None]
        shape = reduce(operator.add, L) if L else None
        shape.bounds = self.cutout.bounds
        return shape

    @property
    def layout(self):
        T = []
        if self.part_labels:
            T.append(s2d.color(self.part_labels, (125, 200, 60)))
        if self.pin_labels:
            T.append(s2d.color(self.pin_labels, (255, 90, 60)))
        if self.traces:
            T.append(s2d.color(self.traces, (125, 90, 60)))
        return T

    @property
    def cutout(self):
        if self._cutout is not None:    return self._cutout
        return s2d.rectangle(self.x0, self.x0 + self.width,
                             self.y0, self.y0 + self.height)

    def __iadd__(self, rhs):
        if isinstance(rhs, Component):
            self.components.append(rhs)
        elif isinstance(rhs, Connection):
            self.connections.append(rhs)
        else:
            raise TypeError("Invalid type for PCB addition (%s)" % type(rhs))
        return self

    def connectH(self, *args, **kwargs):
        ''' Connects a set of pins or points, traveling first
            horizontally then vertically
        '''
        width = kwargs['width'] if 'width' in kwargs else 0.016
        points = []
        for A, B in zip(args[:-1], args[1:]):
            if not isinstance(A, BoundPin):     A = Point(*A)
            if not isinstance(B, BoundPin):     B = Point(*B)
            points.append(A)
            if (A.x != B.x):
                points.append(Point(B.x, A.y))
        if A.y != B.y:  points.append(B)
        self.connections.append(Connection(width, *points))

    def connectV(self, *args, **kwargs):
        ''' Connects a set of pins or points, travelling first
            vertically then horizontally.
        '''
        width = kwargs['width'] if 'width' in kwargs else 0.016
        points = []
        for A, B in zip(args[:-1], args[1:]):
            if not isinstance(A, BoundPin):     A = Point(*A)
            if not isinstance(B, BoundPin):     B = Point(*B)
            points.append(A)
            if (A.y != B.y):
                points.append(Point(A.x, B.y))
        if A.x != B.x:  points.append(B)
        self.connections.append(Connection(width, *points))

################################################################################

class Component(object):
    ''' Generic PCB component.
    '''
    def __init__(self, x, y, rot=0, name=''):
        ''' Constructs a Component object
                x           X position
                y           Y position
                rotation    angle (degrees)
                name        String
        '''
        self.x = x
        self.y = y
        self.rot   = rot

        self.name = name

    def __getitem__(self, i):
        if isinstance(i, str):
            try:
                pin = [p for p in self.pins if p.name == i][0]
            except IndexError:
                raise IndexError("No pin with name %s" % i)
        elif isinstance(i, int):
            try:
                pin = self.pins[i-1]
            except IndexError:
                raise IndexError("Pin %i is not in array" %i)
        return BoundPin(pin, self)

    @property
    def pads(self):
        pads = reduce(operator.add, [p.pad for p in self.pins])
        return s2d.move(s2d.rotate(pads, self.rot), self.x, self.y)

    @property
    def pin_labels(self):
        L = []
        for p in self.pins:
            p = BoundPin(p, self)
            if p.pin.name:
                L.append(text(p.pin.name, p.x, p.y, 0.03))
        return reduce(operator.add, L) if L else None

    @property
    def label(self):
        return text(self.name, self.x, self.y, 0.03)

################################################################################

class Pin(object):
    ''' PCB pin, with name, shape, and position
    '''
    def __init__(self, x, y, shape, name=''):
        self.x      = x
        self.y      = y
        self.shape  = shape
        self.name   = name

    @property
    def pad(self):
        return s2d.move(self.shape, self.x, self.y)

################################################################################

class BoundPin(object):
    ''' PCB pin localized to a specific component
        (so that it has correct x and y positions)
    '''
    def __init__(self, pin, component):
        self.pin = pin
        self.component = component

    @property
    def x(self):
        return (cos(radians(self.component.rot)) * self.pin.x -
                sin(radians(self.component.rot)) * self.pin.y +
                self.component.x)

    @property
    def y(self):
        return (sin(radians(self.component.rot)) * self.pin.x +
                cos(radians(self.component.rot)) * self.pin.y +
                self.component.y)

################################################################################

class Point(object):
    ''' Object with x and y member variables
    '''
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __iter__(self):
        return iter([self.x, self.y])

################################################################################

class Connection(object):
    ''' Connects two pins via a series of intermediate points
    '''
    def __init__(self, width, *args):
        self.width = width
        self.points = [
            a if isinstance(a, BoundPin) else Point(*a) for a in args
        ]

    @property
    def traces(self):
        t = []
        for p1, p2 in zip(self.points[:-1], self.points[1:]):
            d = sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
            if p2 != self.points[-1]:
                d += self.width/2
            a = atan2(p2.y - p1.y, p2.x - p1.x)
            r = s2d.rectangle(0, d, -self.width/2, self.width/2)
            t.append(s2d.move(s2d.rotate(r, degrees(a)), p1.x, p1.y))
        return reduce(operator.add, t)


################################################################################
# Discrete passive components
################################################################################

_pad_1206 = s2d.rectangle(-0.032, 0.032, -0.034, 0.034)

class R_1206(Component):
    ''' 1206 Resistor
    '''
    pins = [Pin(-0.06, 0, _pad_1206), Pin(0.06, 0, _pad_1206)]
    prefix = 'R'

class C_1206(Component):
    ''' 1206 Capacitor
    '''
    pins = [Pin(-0.06, 0, _pad_1206), Pin(0.06, 0, _pad_1206)]
    prefix = 'C'

_pad_SJ = s2d.rectangle(-0.02, 0.02, -0.03, 0.03)
class SJ(Component):
    ''' Solder jumper
    '''
    pins = [Pin(-0.029, 0, _pad_SJ), Pin(0.029, 0, _pad_SJ)]
    prefix = 'SJ'

_pad_SOD_123 = s2d.rectangle(-0.02, 0.02, -0.024, 0.024)
class D_SOD_123(Component):
    ''' Diode
    '''
    pins = [Pin(-0.07, 0, _pad_SOD_123, 'A'),
            Pin(0.07, 0, _pad_SOD_123, 'C')]
    prefix = 'D'


################################################################################
# Connectors
################################################################################

_pad_USB_trace = s2d.rectangle(-0.0075, 0.0075, -0.04, 0.04)
_pad_USB_foot  = s2d.rectangle(-0.049, 0.049, -0.043, 0.043)
class USB_mini_B(Component):
    ''' USB mini B connector
        Hirose UX60-MB-5ST
    '''
    pins = [
        Pin(0.063,   0.24, _pad_USB_trace, 'G'),
        Pin(0.0315,  0.24, _pad_USB_trace),
        Pin(0,       0.24, _pad_USB_trace, '+'),
        Pin(-0.0315, 0.24, _pad_USB_trace, '-'),
        Pin(-0.063,  0.24, _pad_USB_trace, 'V'),

        Pin( 0.165, 0.21, _pad_USB_foot),
        Pin(-0.165, 0.21, _pad_USB_foot),
        Pin( 0.165, 0.0, _pad_USB_foot),
        Pin(-0.165, 0.0, _pad_USB_foot)
    ]
    prefix = 'J'

_pad_header  = s2d.rectangle(-0.06, 0.06, -0.025, 0.025)
class Header_4(Component):
    ''' 4-pin header
        fci 95278-101a04lf bergstik 2x2x0.1
    '''
    pins = [
        Pin(-0.107,  0.05, _pad_header),
        Pin(-0.107, -0.05, _pad_header),
        Pin( 0.107, -0.05, _pad_header),
        Pin( 0.107,  0.05, _pad_header)
    ]
    prefix = 'J'

class Header_ISP(Component):
    ''' ISP programming header
        FCI 95278-101A06LF Bergstik 2x3x0.1
    '''
    pins = [
        Pin(-0.107, 0.1,  _pad_header, 'GND'),
        Pin(-0.107, 0,    _pad_header, 'MOSI'),
        Pin(-0.107, -0.1, _pad_header, 'V'),
        Pin( 0.107, -0.1, _pad_header, 'MISO'),
        Pin( 0.107, 0,    _pad_header, 'SCK'),
        Pin( 0.107, 0.1,  _pad_header, 'RST')
    ]
    prefix = 'J'

class Header_FTDI(Component):
    ''' FTDI cable header
    '''
    pins = [
        Pin(0,  0.25, _pad_header, 'GND'),
        Pin(0,  0.15, _pad_header, 'CTS'),
        Pin(0,  0.05, _pad_header, 'VCC'),
        Pin(0, -0.05, _pad_header, 'TX'),
        Pin(0, -0.15, _pad_header, 'RX'),
        Pin(0, -0.25, _pad_header, 'RTS')
    ]
    prefix = 'J'


################################################################################
# SOT-23 components
################################################################################

_pad_SOT23 = s2d.rectangle(-.02,.02,-.012,.012)
class NMOS_SOT23(Component):
    ''' NMOS transistor in SOT23 package
        Fairchild NDS355AN
    '''
    pins = [
        Pin(0.045, -0.0375, _pad_SOT23, 'G'),
        Pin(0.045,  0.0375, _pad_SOT23, 'S'),
        Pin(-0.045, 0, _pad_SOT23, 'D')
    ]
    prefix = 'Q'

class PMOS_SOT23(Component):
    ''' PMOS transistor in SOT23 package
        Fairchild NDS356AP
    '''
    pins = [
        Pin(-0.045, -0.0375, _pad_SOT23, 'G'),
        Pin(-0.045,  0.0375, _pad_SOT23, 'S'),
        Pin(0.045, 0, _pad_SOT23, 'D')
    ]
    prefix = 'Q'

class Regulator_SOT23(Component):
    '''  SOT23 voltage regulator
    '''
    pins = [
        Pin(-0.045, -0.0375, _pad_SOT23, 'Out'),
        Pin(-0.045,  0.0375, _pad_SOT23, 'In'),
        Pin(0.045, 0, _pad_SOT23, 'GND')
    ]
    prefix = 'U'

################################################################################
#   Clock crystals
################################################################################
_pad_XTAL_NX5032GA = s2d.rectangle(-.039,.039,-.047,.047)

class XTAL_NX5032GA(Component):
    pins = [Pin(-0.079, 0, _pad_XTAL_NX5032GA),
            Pin(0.079, 0, _pad_XTAL_NX5032GA)]
    prefix = 'X'

################################################################################
# Atmel microcontrollers
################################################################################

_pad_SOIC = s2d.rectangle(-0.041, 0.041, -0.015, 0.015)
class ATtiny45_SOIC(Component):
    pins = []
    y = 0.075
    for t in ['RST', 'PB3', 'PB4', 'GND']:
        pins.append(Pin(-0.14, y, _pad_SOIC, t))
        y -= 0.05
    for p in ['PB0', 'PB1', 'PB2', 'VCC']:
        y += 0.05
        pins.append(Pin(0.14, y, _pad_SOIC, t))
    del y
    prefix = 'U'

class ATtiny44_SOIC(Component):
    pins = []
    y = 0.15
    for t in ['VCC', 'PB0', 'PB1', 'PB3', 'PB2', 'PA7', 'PA6']:
        pad = _pad_SOIC + s2d.circle(-0.041, 0, 0.015) if t == 'VCC' else _pad_SOIC
        pins.append(Pin(-0.12, y, pad, t))
        y -= 0.05
    for t in ['PA5', 'PA4', 'PA3', 'PA2', 'PA1', 'PA0', 'GND']:
        y += 0.05
        pins.append(Pin(0.12, y, _pad_SOIC, t))
    prefix = 'U'

_pad_TQFP_h = s2d.rectangle(-0.025, 0.025, -0.008, 0.008)
_pad_TQFP_v = s2d.rectangle(-0.008, 0.008, -0.025, 0.025)

class ATmega88_TQFP(Component):
    pins = []
    y = 0.1085
    for t in ['PD3', 'PD4', 'GND', 'VCC', 'GND', 'VCC', 'PB6', 'PB7']:
        pins.append(Pin(-0.18, y, _pad_TQFP_h, t))
        y -= 0.031
    x = -0.1085
    for t in ['PD5', 'PD6', 'PD7', 'PB0', 'PB1', 'PB2', 'PB3', 'PB4']:
        pins.append(Pin(x, -0.18, _pad_TQFP_v, t))
        x += 0.031
    y = -0.1085
    for t in ['PB5', 'AVCC', 'ADC6', 'AREF', 'GND', 'ADC7', 'PC0', 'PC1']:
        pins.append(Pin(0.18, y, _pad_TQFP_h, t))
        y += 0.031
    x = 0.1085
    for t in ['PC2', 'PC3', 'PC4', 'PC5', 'PC6', 'PD0', 'PD1', 'PD2']:
        pins.append(Pin(x, 0.18, _pad_TQFP_v, t))
        x -= 0.031
    del x, y
    prefix = 'U'


################################################################################
#   CBA logo
################################################################################
_pin_circle_CBA = s2d.circle(0, 0, 0.02)
_pin_square_CBA = s2d.rectangle(-0.02, 0.02, -0.02, 0.02)
class CBA(Component):
    pins = []
    for i in range(3):
        for j in range(3):
            pin = _pin_circle_CBA if i == 2-j and j >= 1 else _pin_square_CBA
            pins.append(Pin(0.06*(i-1), 0.06*(j-1), pin))

########NEW FILE########
__FILENAME__ = shapes
from koko.lib.shapes2d import *
from koko.lib.shapes3d import *

########NEW FILE########
__FILENAME__ = shapes2d
import math

from koko.c.interval    import Interval
from koko.fab.tree      import MathTree, X, Y, Z, matching

################################################################################

def circle(x0, y0, r):

    # sqrt((X-x0)**2 + (Y-y0)**2) - r
    r = abs(r)
    s = MathTree('-r+q%sq%sf%g' % (('-Xf%g' % x0) if x0 else 'X',
                                   ('-Yf%g' % y0) if y0 else 'Y', r))

    s.xmin, s.xmax = x0-r, x0+r
    s.ymin, s.ymax = y0-r, y0+r

    s.shape = True
    return s

################################################################################

def triangle(x0, y0, x1, y1, x2, y2):
    # Find the angles of the points about the center
    xm = (x0 + x1 + x2) / 3.
    ym = (y0 + y1 + y2) / 3.
    angles = [math.atan2(y - ym, x - xm) for x, y in [(x0,y0), (x1,y1), (x2,y2)]]

    # Sort the angles so that the smallest one is first
    if angles[1] < angles[0] and angles[1] < angles[2]:
        angles = [angles[1], angles[2], angles[0]]
    elif angles[2] < angles[0] and angles[2] < angles[1]:
        angles = [angles[2], angles[0], angles[1]]

    # Enforce that points must be in clockwise order by swapping if necessary
    if angles[2] > angles[1]:
        x0, y0, x1, y1 = x1, y1, x0, y0

    def edge(x, y, dx, dy):
        # dy*(X-x)-dx*(Y-y)
        return '-*f%(dy)g-Xf%(x)g*f%(dx)g-Yf%(y)g' % locals()

    e0 = edge(x0, y0, x1-x0, y1-y0)
    e1 = edge(x1, y1, x2-x1, y2-y1)
    e2 = edge(x2, y2, x0-x2, y0-y2)

    # -min(e0, min(e1, e2))
    s = MathTree('ni%(e0)si%(e1)s%(e2)s' % locals())

    s.xmin, s.xmax = min(x0, x1, x2), max(x0, x1, x2)
    s.ymin, s.ymax = min(y0, y1, y2), max(y0, y1, y2)

    s.shape = True
    return s

def right_triangle(x0, y0, h):
    corner = MathTree.max(MathTree('-f%fX' % x0),MathTree('-f%fY' % y0))
    corner.shape = True
    shape = corner & MathTree('-X-f%f-Yf%f' % (x0+h, y0))
    shape.xmin = x0
    shape.xmax = x0 + h
    shape.ymin = y0
    shape.ymax = y0 + h
    return shape

################################################################################

def rectangle(x0, x1, y0, y1):
    # max(max(x0 - X, X - x1), max(y0 - Y, Y - y1)
    s = MathTree('aa-f%(x0)gX-Xf%(x1)ga-f%(y0)gY-Yf%(y1)g' % locals())

    s.xmin, s.xmax = x0, x1
    s.ymin, s.ymax = y0, y1

    s.shape = True
    return s

def rounded_rectangle(x0, x1, y0, y1, r):
    r *= min(x1 - x0, y1 - y0)/2
    return (
        rectangle(x0, x1, y0+r, y1-r) +
        rectangle(x0+r, x1-r, y0, y1) +
        circle(x0+r, y0+r, r) +
        circle(x0+r, y1-r, r) +
        circle(x1-r, y0+r, r) +
        circle(x1-r, y1-r, r)
    )

################################################################################

def tab(x, y, width, height, angle=0, chamfer=0.2):
    tab = rectangle(-width/2, width/2, 0, height)
    cutout = triangle(width/2 - chamfer*height, height,
                      width/2, height,
                      width/2, height - chamfer*height)
    tab -= cutout + reflect_x(cutout)

    return move(rotate(tab, angle), x, y)

################################################################################

def slot(x, y, width, height, angle=0, chamfer=0.2):
    slot = rectangle(-width/2, width/2, -height, 0)
    inset = triangle(width/2, 0,
                     width/2 + height * chamfer, 0,
                     width/2, -chamfer*height)
    slot += inset + reflect_x(inset)

    return move(rotate(slot, angle), x, y)

################################################################################

def move(part, dx, dy, dz=0):
    p = part.map('-Xf%g' % dx if dx else None,
                 '-Yf%g' % dy if dy else None,
                 '-Zf%g' % dz if dz else None)
    if part.dx: p.xmin, p.xmax = part.xmin + dx, part.xmax + dx
    if part.dy: p.ymin, p.ymax = part.ymin + dy, part.ymax + dy
    if part.dz: p.zmin, p.zmax = part.zmin + dz, part.zmax + dz

    return p

translate = move

################################################################################

add      = lambda x, y: x + y
subtract = lambda x, y: x - y

################################################################################

def rotate(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(X='+*f%(ca)gX*f%(sa)gY'  % locals(),
                 Y='+*f%(nsa)gX*f%(ca)gY' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa
    p.bounds = part.map_bounds(X='+*f%(ca)gX*f%(sa)gY'  % locals(),
                               Y='+*f%(nsa)gX*f%(ca)gY' % locals())

    return p

################################################################################

def reflect_x(part, x0=0):

    # X' = 2*x0-X
    p = part.map(X='-*f2f%gX' % x0 if x0 else 'nX')

    # X  = 2*x0-X'
    p.bounds = part.map_bounds(X='-*f2f%gX' % x0 if x0 else 'nX')
    return p

def reflect_y(part, y0=0):

    # Y' = 2*y0-Y
    p = part.map(Y='-*f2f%gY' % y0 if y0 else 'nY')

    # Y  = 2*y0-Y'
    p.bounds = part.map_bounds(Y='-*f2f%gY' % y0 if y0 else 'nY')
    return p

def reflect_xy(part):
    p = part.map(X='Y', Y='X')
    p.bounds = part.map_bounds(X='Y', Y='X')
    return p

################################################################################

def scale_x(part, x0, sx):

    # X' = x0 + (X-x0)/sx
    p = part.map(X='+f%(x0)g/-Xf%(x0)gf%(sx)g' % locals()
                    if x0 else '/Xf%g' % sx)

    # X  = (X'-x0)*sx + x0
    p.bounds = part.map_bounds(X='+f%(x0)g*f%(sx)g-Xf%(x0)g' % locals()
                               if x0 else '*Xf%g' % sx)
    return p

def scale_y(part, y0, sy):

    # Y' = y0 + (Y-y0)/sy
    p = part.map(Y='+f%(y0)g/-Yf%(y0)gf%(sy)g' % locals()
                    if y0 else '/Yf%g' % sy)

    # Y  = (Y'-y0)*sy + y0
    p.bounds = part.map_bounds(Y='+f%(y0)g*f%(sy)g-Yf%(y0)g' % locals()
                               if y0 else '*Yf%g' % sy)

    return p

def scale_xy(part, x0, y0, sxy):

    # X' = x0 + (X-x0)/sx
    # Y' = y0 + (Y-y0)/sy
    p = part.map(X='+f%(x0)g/-Xf%(x0)gf%(sxy)g' % locals()
                    if x0 else '/Xf%g' % sxy,
                 Y='+f%(y0)g/-Yf%(y0)gf%(sxy)g' % locals()
                    if y0 else '/Yf%g' % sxy)

    # X  = (X'-x0)*sx + x0
    # Y  = (Y'-y0)*sy + y0
    p.bounds = part.map_bounds(X='+f%(x0)g*f%(sxy)g-Xf%(x0)g' % locals()
                               if x0 else '*Xf%g' % sxy,
                               Y='+f%(y0)g*f%(sxy)g-Yf%(y0)g' % locals()
                               if y0 else '*Yf%g' % sxy)
    return p

################################################################################

def shear_x_y(part, y0, y1, dx0, dx1):

    dx = dx1 - dx0
    dy = y1 - y0

    # X' = X-dx0-dx*(Y-y0)/dy
    p = part.map(X='--Xf%(dx0)g/*f%(dx)g-Yf%(y0)gf%(dy)g' % locals())

    # X  = X'+dx0+(dx)*(Y-y0)/dy
    p.bounds = part.map_bounds(X='++Xf%(dx0)g/*f%(dx)g-Yf%(y0)gf%(dy)g'
                                  % locals())
    return p

################################################################################

def taper_x_y(part, x0, y0, y1, s0, s1):

    dy = y1 - y0
    ds = s1 - s0
    s0y1 = s0 * y1
    s1y0 = s1 * y0

    #   X'=x0+(X-x0)*(y1-y0)/(Y*(s1-s0)+s0*y1-s1*y0))
    X = '+f%(x0)g/*-Xf%(x0)gf%(dy)g-+*Yf%(ds)gf%(s0y1)gf%(s1y0)g' % locals()
    p = part.map(X=X)

    #   X=(X'-x0)*(Y*(s1-s0)+s0*y1-s1*y0)/(y1-y0)+x0
    p.bounds = part.map_bounds(
        X='+f%(x0)g*-Xf%(x0)g/-+*Yf%(ds)gf%(s0y1)gf%(s1y0)gf%(dy)g'
           % locals())

    return p

################################################################################

@matching
def blend(p0, p1, amount):
    if not p0.shape or not p1.shape:
        raise TypeError('Arguments must be math objects with shape=True')
    joint = p0 + p1

    # sqrt(abs(p0)) + sqrt(abs(p1)) - amount
    fillet = MathTree('-+rb%srb%sf%g' % (p0.math, p1.math, amount),
                      shape=True)
    out = joint + fillet
    out.bounds = [b for b in joint.bounds]

    return out

################################################################################

def color(part, rgb):
    p = part.clone()
    p.color = rgb
    return p

########NEW FILE########
__FILENAME__ = shapes3d
import math

from koko.c.interval    import Interval
from koko.fab.tree      import MathTree, X, Y, Z, matching

import koko.lib.shapes2d as s2d

################################################################################

def extrusion(part, z0, z1):
    # max(part, max(z0-Z, Z-z1))
    s = MathTree('a%sa-f%gZ-Zf%g' % (part.math, z0, z1))
    s.bounds = part.bounds[0:4] + [z0, z1]
    s.shape = True
    s.color = part.color
    return s

def cylinder(x0, y0, z0, z1, r):
    return extrusion(s2d.circle(x0, y0, r), z0, z1)

def sphere(x0, y0, z0, r):
    s = MathTree('-r++q%sq%sq%sf%g' % (('-Xf%g' % x0) if x0 else 'X',
                                       ('-Yf%g' % y0) if y0 else 'Y',
                                       ('-Zf%g' % z0) if z0 else 'Z',
                                       r))
    s.xmin, s.xmax = x0-r, x0+r
    s.ymin, s.ymax = y0-r, y0+r
    s.zmin, s.zmax = z0-r, z0+r
    s.shape = True
    return s

def cube(x0, x1, y0, y1, z0, z1):
    return extrusion(s2d.rectangle(x0, x1, y0, y1), z0, z1)

def cone(x0, y0, z0, z1, r):
    cyl = cylinder(x0, y0, z0, z1, r)
    return taper_xy_z(cyl, x0, y0, z0, z1, 1.0, 0.0)

def pyramid(x0, x1, y0, y1, z0, z1):
    c = cube(x0, x1, y0, y1, z0, z1)
    return taper_xy_z(c, (x0+x1)/2., (y0+y1)/2., z0, z1, 1.0, 0.0)

################################################################################

move        = s2d.move
translate   = s2d.translate
add         = s2d.add
subtract    = s2d.subtract

def rotate_x(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(Y='+*f%(ca)gY*f%(sa)gZ'  % locals(),
                 Z='+*f%(nsa)gY*f%(ca)gZ' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa
    p.bounds = part.map_bounds(Y='+*f%(ca)gY*f%(sa)gZ' % locals(),
                               Z='+*f%(nsa)gY*f%(ca)gZ' % locals())
    return p

def rotate_y(part, angle):

    angle *= math.pi/180
    ca, sa = math.cos(angle), math.sin(angle)
    nsa    = -sa

    p = part.map(X='+*f%(ca)gX*f%(sa)gZ'  % locals(),
                 Z='+*f%(nsa)gX*f%(ca)gZ' % locals())

    ca, sa = math.cos(-angle), math.sin(-angle)
    nsa    = -sa

    p.bounds = part.map_bounds(X='+*f%(ca)gX*f%(sa)gZ' % locals(),
                               Z='+*f%(nsa)gX*f%(ca)gZ' % locals())
    return p

rotate_z = s2d.rotate

################################################################################

reflect_x = s2d.reflect_x
reflect_y = s2d.reflect_y

def reflect_z(part, z0=0):
    p = part.map(Z='-*f2f%gZ' % z0 if z0 else 'nZ')
    p.bounds = part.map_bounds(Z='-*f2f%gZ' % z0 if z0 else 'nZ')
    return p

reflect_xy = s2d.reflect_xy
def reflect_xz(part):
    p = part.map(X='Z', Z='X')
    p.bounds = part.map_bounds(X='Z', Z='X')
    return p

def reflect_yz(part):
    p = part.map(Y='Z', Z='Y')
    p.bounds = part.map_bounds(Y='Z', Z='Y')
    return p

################################################################################

scale_x = s2d.scale_x
scale_y = s2d.scale_y

def scale_z(part, z0, sz):
    p = part.map(Z='+f%(z0)g/-Zf%(z0)gf%(sz)g' % locals()
                    if z0 else '/Zf%g' % sz)
    p.bounds = part.map_bounds(Z='+f%(z0)g*f%(sz)g-Zf%(z0)g' % locals()
                               if z0 else '*Zf%g' % sz)
    return p

################################################################################

shear_x_y = s2d.shear_x_y

def shear_x_z(part, z0, z1, dx0, dx1):

    #   X' = X-dx0-(dx1-dx0)*(Z-z0)/(z1-z0)
    p = part.map(X='--Xf%(dx0)g/*f%(dx)g-Zf%(z0)gf%(dz)g' % locals())

    #   X = X'+dx0+(dx1-dx0)*(Z-z0)/(z1-z0)
    p.bounds = part.map_bounds(X='++Xf%(dx0)g/*f%(dx)g-Zf%(z0)gf%(dz)g'
                                  % locals())
    return p

################################################################################

taper_x_y = s2d.taper_x_y

def taper_xy_z(part, x0, y0, z0, z1, s0, s1):

    dz = z1 - z0

    # X' =  x0 +(X-x0)*dz/(s1*(Z-z0) + s0*(z1-Z))
    # Y' =  y0 +(Y-y0)*dz/(s1*(Z-z0) + s0*(z1-Z))
    p = part.map(
        X='+f%(x0)g/*-Xf%(x0)gf%(dz)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZ'
            % locals(),
        Y='+f%(y0)g/*-Yf%(y0)gf%(dz)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZ'
            % locals())

    # X  = (X' - x0)*(s1*(Z-z0) + s0*(z1-Z))/dz + x0
    # Y  = (Y' - y0)*(s1*(Z-z0) + s0*(z1-Z))/dz + y0
    p.bounds = part.map_bounds(
        X='+/*-Xf%(x0)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZf%(dz)gf%(x0)g'
            % locals(),
        Y='+/*-Yf%(y0)g+*f%(s1)g-Zf%(z0)g*f%(s0)g-f%(z1)gZf%(dz)gf%(y0)g'
            % locals())

    return p

################################################################################

def revolve_y(part):
    ''' Revolve a part in the XY plane about the Y axis. '''
    #   X' = sqrt(X**2 + Z**2)
    p = part.map(X='r+qXqZ')

    if part.bounds[0] and part.bounds[1]:
        p.xmin = min(-abs(part.xmin), -abs(part.xmax))
        p.xmax = max( abs(part.xmin),  abs(part.xmax))
        p.ymin, p.ymax = part.ymin, part.ymax
        p.zmin, p.zmax = p.xmin, p.xmax
    return p


def revolve_x(part):
    ''' Revolve a part in the XY plane about the X axis. '''
    #   Y' = sqrt(Y**2 + Z**2)
    p = part.map(Y='r+qYqZ')

    if part.bounds[0] and part.bounds[1]:
        p.xmin, p.xmax = part.xmin, part.xmax
        p.ymin = min(-abs(part.ymin), -abs(part.ymax))
        p.ymax = max( abs(part.ymin),  abs(part.ymax))
        p.zmin, p.zmax =  p.ymin, p.ymax
    return p

################################################################################

@matching
def loft(p0, p1, z0, z1):
    if not p0.shape or not p1.shape:
        raise TypeError('Arguments must be math objects with shape=True')
    """
    (((Z-z1)*(Z-z2)/((z0-z1)*(z0-z2))+
    0.5*(Z-z0)*(Z-z2)/((z1-z0)*(z1-z2)))*(part0)+
    (0.5*(Z-z0)*(Z-z2)/((z1-z0)*(z1-z2))+
    (Z-z0)*(Z-z1)/((z2-z0)*(z2-z1)))*(part1))
    """

########NEW FILE########
__FILENAME__ = text
#   koko.lib.text.py
#   Simple math-string based font.

#   Matt Keeter
#   matt.keeter@cba.mit.edu

#   kokompe.cba.mit.edu

################################################################################

from koko.lib.shapes2d import *

def text(text, x, y, height = 1, align = 'CC'):

    dx, dy = 0, -1
    text_shape = None

    for line in text.split('\n'):
        line_shape = None

        for c in line:
            if not c in _glyphs.keys():
                print 'Warning:  Unknown character "%s" in koko.lib.text' % c
            else:
                chr_math = move(_glyphs[c], dx, dy)
                if line_shape is None:  line_shape  = chr_math
                else:                   line_shape += chr_math
                dx += _glyphs[c].width + 0.1
        dx -= 0.1

        if line_shape is not None:
            if align[0] == 'L':
                pass
            elif align[0] == 'C':
                line_shape = move(line_shape, -dx / 2, 0)
            elif align[0] == 'R':
                line_shape = move(line_shape, -dx, 0)

            text_shape += line_shape

        dy -= 1.55
        dx = 0

    dy += 1.55
    if text_shape is None:  return None

    if align[1] == 'T':
        pass
    elif align[1] == 'B':
        text_shape = move(text_shape, 0, -dy,)
    elif align[1] == 'C':
        text_shape = move(text_shape, 0, -dy/2)

    if height != 1:
        text_shape = scale_xy(text_shape, 0, 0, height)
        dx *= height
        dy *= height

    return move(text_shape, x, y)


_glyphs = {}

shape = triangle(0, 0, 0.35, 1, 0.1, 0)
shape += triangle(0.1, 0, 0.35, 1, 0.45, 1)
shape += triangle(0.35, 1, 0.45, 1, 0.8, 0)
shape += triangle(0.7, 0, 0.35, 1, 0.8, 0)
shape += rectangle(0.2, 0.6, 0.3, 0.4)
shape.width = 0.8
_glyphs['A'] = shape


shape = circle(0.25, 0.275, 0.275)
shape -= circle(0.25, 0.275, 0.175)
shape = shear_x_y(shape, 0, 0.35, 0, 0.1)
shape += rectangle(0.51, 0.61, 0, 0.35)
shape = move(shape, -0.05, 0)
shape.width = 0.58
_glyphs['a'] = shape


shape = circle(0.3, 0.725, 0.275)
shape -= circle(0.3, 0.725, 0.175)
shape += circle(0.3, 0.275, 0.275)
shape -= circle(0.3, 0.275, 0.175)
shape &= rectangle(0.3, 1, 0, 1)
shape += rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.3, 0, 0.1)
shape += rectangle(0.1, 0.3, 0.45, 0.55)
shape += rectangle(0.1, 0.3, 0.9, 1)
shape.width = 0.575
_glyphs['B'] = shape


shape = circle(0.25, 0.275, 0.275)
shape -= circle(0.25, 0.275, 0.175)
shape &= rectangle(0.25, 1, 0, 0.275) + rectangle(0, 1, 0.275, 1)
shape += rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.25, 0, 0.1)
shape.width = 0.525
_glyphs['b'] = shape


shape = circle(0.3, 0.7, 0.3) - circle(0.3, 0.7, 0.2)
shape += circle(0.3, 0.3, 0.3) - circle(0.3, 0.3, 0.2)
shape -= rectangle(0, 0.6, 0.3, 0.7)
shape -= triangle(0.3, 0.5, 1, 1.5, 1, -0.5)
shape -= rectangle(0.3, 0.6, 0.2, 0.8)
shape += rectangle(0, 0.1, 0.3, 0.7)
shape.width = 0.57
_glyphs['C'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape -= triangle(0.275, 0.275, 0.55, 0.55, 0.55, 0)
shape.width = 0.48
_glyphs['c'] = shape


shape = circle(0.1, 0.5, 0.5) - circle(0.1, 0.5, 0.4)
shape &= rectangle(0, 1, 0, 1)
shape += rectangle(0, 0.1, 0, 1)
shape.width = 0.6
_glyphs['D'] = shape


shape = reflect_x(_glyphs['b'], _glyphs['b'].width/2)
shape.width = _glyphs['b'].width
_glyphs['d'] = shape


shape = rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.6, 0.9, 1)
shape += rectangle(0.1, 0.6, 0, 0.1)
shape += rectangle(0.1, 0.5, 0.45, 0.55)
shape.width = 0.6
_glyphs['E'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape -= triangle(0.1, 0.275, 0.75, 0.275, 0.6, 0)
shape += rectangle(0.05, 0.55, 0.225, 0.315)
shape &=  circle(0.275, 0.275, 0.275)
shape.width = 0.55
_glyphs['e'] = shape


shape = rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.6, 0.9, 1)
shape += rectangle(0.1, 0.5, 0.45, 0.55)
shape.width = 0.6
_glyphs['F'] = shape


shape = circle(0.4, 0.75, 0.25) - circle(0.4, 0.75, 0.15)
shape &= rectangle(0, 0.4, 0.75, 1)
shape += rectangle(0, 0.4, 0.45, 0.55)
shape += rectangle(0.15, 0.25, 0, 0.75)
shape.width = 0.4
_glyphs['f'] = shape


shape = circle(0.275, -0.1, 0.275)
shape -= circle(0.275, -0.1, 0.175)
shape &= rectangle(0, 0.55, -0.375, -0.1)
shape += circle(0.275, 0.275, 0.275) - circle(0.275, 0.275, 0.175)
shape += rectangle(0.45, 0.55, -0.1, 0.55)
shape.width = 0.55
_glyphs['g'] = shape


shape = circle(0.3, 0.7, 0.3) - circle(0.3, 0.7, 0.2)
shape += circle(0.3, 0.3, 0.3) - circle(0.3, 0.3, 0.2)
shape -= rectangle(0, 0.6, 0.3, 0.7)
shape += rectangle(0, 0.1, 0.3, 0.7)
shape += rectangle(0.5, 0.6, 0.3, 0.4)
shape += rectangle(0.3, 0.6, 0.4, 0.5)
shape.width = 0.6
_glyphs['G'] = shape


shape = rectangle(0, 0.1, 0, 1)
shape += rectangle(0.5, 0.6, 0, 1)
shape += rectangle(0.1, 0.5, 0.45, 0.55)
shape.width = 0.6
_glyphs['H'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape &= rectangle(0, 0.55, 0.275, 0.55)
shape += rectangle(0, 0.1, 0, 1)
shape += rectangle(0.45, 0.55, 0, 0.275)
shape.width = 0.55
_glyphs['h'] = shape


shape = rectangle(0, 0.5, 0, 0.1)
shape += rectangle(0, 0.5, 0.9, 1)
shape += rectangle(0.2, 0.3, 0.1, 0.9)
shape.width = 0.5
_glyphs['I'] = shape


shape = rectangle(0.025, 0.125, 0, 0.55)
shape += circle(0.075, 0.7, 0.075)
shape.width = 0.15
_glyphs['i'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape &= rectangle(0, 0.55, 0, 0.275)
shape += rectangle(0.45, 0.55, 0.275, 1)
shape.width = 0.55
_glyphs['J'] = shape


shape = circle(0.0, -0.1, 0.275)
shape -= circle(0.0, -0.1, 0.175)
shape &= rectangle(0, 0.55, -0.375, -0.1)
shape += rectangle(0.175, 0.275, -0.1, 0.55)
shape += circle(0.225, 0.7, 0.075)
shape.width = 0.3
_glyphs['j'] = shape


shape = rectangle(0, 0.6, 0, 1)
shape -= triangle(0.1, 1, 0.5, 1, 0.1, 0.6)
shape -= triangle(0.5, 0, 0.1, 0, 0.1, 0.4)
shape -= triangle(0.6, 0.95, 0.6, 0.05, 0.18, 0.5)
shape.width = 0.6
_glyphs['K'] = shape


shape = rectangle(0, 0.5, 0, 1)
shape -= triangle(0.1, 1, 0.5, 1, 0.1, 0.45)
shape -= triangle(0.36, 0, 0.1, 0, 0.1, 0.25)
shape -= triangle(0.6, 1, 0.5, 0.0, 0.18, 0.35)
shape -= triangle(0.1, 1, 0.6, 1, 0.6, 0.5)
shape.width = 0.5
_glyphs['k'] = shape


shape = rectangle(0, 0.6, 0, 0.1)
shape += rectangle(0, 0.1, 0, 1)
shape.width = 0.6
_glyphs['L'] = shape


shape = rectangle(0.025, 0.125, 0, 1)
shape.width = 0.15
_glyphs['l'] = shape


shape = rectangle(0, 0.1, 0, 1)
shape += rectangle(0.7, 0.8, 0, 1)
shape += triangle(0, 1, 0.1, 1, 0.45, 0)
shape += triangle(0.45, 0, 0.35, 0, 0, 1)
shape += triangle(0.7, 1, 0.8, 1, 0.35, 0)
shape += triangle(0.35, 0, 0.8, 1, 0.45, 0)
shape.width = 0.8
_glyphs['M'] = shape


shape = circle(0.175, 0.35, 0.175) - circle(0.175, 0.35, 0.075)
shape += circle(0.425, 0.35, 0.175) - circle(0.425, 0.35, 0.075)
shape &= rectangle(0, 0.65, 0.35, 0.65)
shape += rectangle(0, 0.1, 0, 0.525)
shape += rectangle(0.25, 0.35, 0, 0.35)
shape += rectangle(0.5, 0.6, 0, 0.35)
shape.width = 0.6
_glyphs['m'] = shape


shape = rectangle(0, 0.1, 0, 1)
shape += rectangle(0.5, 0.6, 0, 1)
shape += triangle(0, 1, 0.1, 1, 0.6, 0)
shape += triangle(0.6, 0, 0.5, 0, 0, 1)
shape.width = 0.6
_glyphs['N'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape &= rectangle(0, 0.55, 0.325, 0.55)
shape += rectangle(0, 0.1, 0, 0.55)
shape += rectangle(0.45, 0.55, 0, 0.325)
shape.width = 0.55
_glyphs['n'] = shape


shape = circle(0.3, 0.7, 0.3) - circle(0.3, 0.7, 0.2)
shape += circle(0.3, 0.3, 0.3) - circle(0.3, 0.3, 0.2)
shape -= rectangle(0, 0.6, 0.3, 0.7)
shape += rectangle(0, 0.1, 0.3, 0.7)
shape += rectangle(0.5, 0.6, 0.3, 0.7)
shape.width = 0.6
_glyphs['O'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape.width = 0.55
_glyphs['o'] = shape


shape = circle(0.3, 0.725, 0.275)
shape -= circle(0.3, 0.725, 0.175)
shape &= rectangle(0.3, 1, 0, 1)
shape += rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.3, 0.45, 0.55)
shape += rectangle(0.1, 0.3, 0.9, 1)
shape.width = 0.575
_glyphs['P'] = shape


shape = circle(0.275, 0.275, 0.275)
shape -= circle(0.275, 0.275, 0.175)
shape += rectangle(0, 0.1, -0.375, 0.55)
shape.width = 0.55
_glyphs['p'] = shape


shape = circle(0.3, 0.7, 0.3) - circle(0.3, 0.7, 0.2)
shape += circle(0.3, 0.3, 0.3) - circle(0.3, 0.3, 0.2)
shape -= rectangle(0, 0.6, 0.3, 0.7)
shape += rectangle(0, 0.1, 0.3, 0.7)
shape += rectangle(0.5, 0.6, 0.3, 0.7)
shape += triangle(0.5, 0.1, 0.6, 0.1, 0.6, 0)
shape += triangle(0.5, 0.1, 0.5, 0.3, 0.6, 0.1)
shape.width = 0.6
_glyphs['Q'] = shape


shape = circle(0.275, 0.275, 0.275) - circle(0.275, 0.275, 0.175)
shape += rectangle(0.45, 0.55, -0.375, 0.55)
shape.width = 0.55
_glyphs['q'] = shape


shape = circle(0.3, 0.725, 0.275)
shape -= circle(0.3, 0.725, 0.175)
shape &= rectangle(0.3, 1, 0, 1)
shape += rectangle(0, 0.1, 0, 1)
shape += rectangle(0.1, 0.3, 0.45, 0.55)
shape += rectangle(0.1, 0.3, 0.9, 1)
shape += triangle(0.3, 0.5, 0.4, 0.5, 0.575, 0)
shape += triangle(0.475, 0.0, 0.3, 0.5, 0.575, 0)
shape.width = 0.575
_glyphs['R'] = shape


shape = circle(0.55, 0, 0.55) - scale_x(circle(0.55, 0, 0.45), 0.55, 0.8)
shape &= rectangle(0, 0.55, 0, 0.55)
shape = scale_x(shape, 0, 0.7)
shape += rectangle(0, 0.1, 0, 0.55)
shape.width = 0.385
_glyphs['r'] = shape


shape = circle(0.275, 0.725, 0.275)
shape -= circle(0.275, 0.725, 0.175)
shape -= rectangle(0.275, 0.55, 0.45, 0.725)
shape += reflect_x(reflect_y(shape, 0.5), .275)
shape.width = 0.55
_glyphs['S'] = shape


shape = circle(0.1625, 0.1625, 0.1625)
shape -= scale_x(circle(0.165, 0.165, 0.0625), 0.165, 1.5)
shape -= rectangle(0, 0.1625, 0.1625, 0.325)
shape += reflect_x(reflect_y(shape, 0.275), 0.1625)
shape = scale_x(shape, 0, 1.5)
shape.width = 0.4875
_glyphs['s'] = shape


shape = rectangle(0, 0.6, 0.9, 1) + rectangle(0.25, 0.35, 0, 0.9)
shape.width = 0.6
_glyphs['T'] = shape


shape = circle(0.4, 0.25, 0.25) - circle(0.4, 0.25, 0.15)
shape &= rectangle(0, 0.4, 0, 0.25)
shape += rectangle(0, 0.4, 0.55, 0.65)
shape += rectangle(0.15, 0.25, 0.25, 1)
shape.width = 0.4
_glyphs['t'] = shape


shape = circle(0.3, 0.3, 0.3) - circle(0.3, 0.3, 0.2)
shape &= rectangle(0, 0.6, 0, 0.3)
shape += rectangle(0, 0.1, 0.3, 1)
shape += rectangle(0.5, 0.6, 0.3, 1)
shape.width = 0.6
_glyphs['U'] = shape


shape = circle(0.275, 0.275, 0.275) - circle(0.275, 0.275, 0.175)
shape &= rectangle(0, 0.55, 0, 0.275)
shape += rectangle(0, 0.1, 0.275, 0.55)
shape += rectangle(0.45, 0.55, 0, 0.55)
shape.width = 0.55
_glyphs['u'] = shape


shape = triangle(0, 1, 0.1, 1, 0.35, 0)
shape += triangle(0.35, 0, 0.25, 0, 0, 1)
shape += reflect_x(shape, 0.3)
shape.width = 0.6
_glyphs['V'] = shape


shape = triangle(0, 0.55, 0.1, 0.55, 0.35, 0)
shape += triangle(0.35, 0, 0.25, 0, 0, 0.55)
shape += reflect_x(shape, 0.3)
shape.width = 0.6
_glyphs['v'] = shape


shape = triangle(0, 1, 0.1, 1, 0.25, 0)
shape += triangle(0.25, 0, 0.15, 0, 0, 1)
shape += triangle(0.15, 0, 0.35, 1, 0.45, 1)
shape += triangle(0.45, 1, 0.25, 0, 0.15, 0)
shape += reflect_x(shape, 0.4)
shape.width = 0.8
_glyphs['W'] = shape


shape = triangle(0, 0.55, 0.1, 0.55, 0.25, 0)
shape += triangle(0.25, 0, 0.15, 0, 0, 0.55)
shape += triangle(0.15, 0, 0.35, 0.5, 0.45, 0.5)
shape += triangle(0.45, 0.5, 0.25, 0, 0.15, 0)
shape += reflect_x(shape, 0.4)
shape.width = 0.8
_glyphs['w'] = shape


shape = triangle(0, 1, 0.125, 1, 0.8, 0)
shape += triangle(0.8, 0, 0.675, 0, 0, 1)
shape += reflect_x(shape, 0.4)
shape.width = 0.8
_glyphs['X'] = shape


shape = triangle(0, 0.55, 0.125, 0.55, 0.55, 0)
shape += triangle(0.55, 0, 0.425, 0, 0, 0.55)
shape += reflect_x(shape, 0.275)
shape.width = 0.55
_glyphs['x'] = shape


shape = triangle(0, 1, 0.1, 1, 0.45, 0.5)
shape += triangle(0.45, 0.5, 0.35, 0.5, 0, 1)
shape += reflect_x(shape, 0.4)
shape += rectangle(0.35, 0.45, 0, 0.5)
shape.width = 0.8
_glyphs['Y'] = shape


shape = triangle(0, 0.55, 0.1, 0.55, 0.325, 0)
shape += triangle(0.325, 0, 0.225, 0, 0, 0.55)
shape += reflect_x(shape, 0.275) + move(reflect_x(shape, 0.275), -0.225, -0.55)
shape &= rectangle(0, 0.55, -0.375, 0.55)
shape.width = 0.55
_glyphs['y'] = shape


shape = rectangle(0, 0.6, 0, 1)
shape -= triangle(0, 0.1, 0, 0.9, 0.45, 0.9)
shape -= triangle(0.6, 0.1, 0.15, 0.1, 0.6, 0.9)
shape.width = 0.6
_glyphs['Z'] = shape


shape = rectangle(0, 0.6, 0, 0.55)
shape -= triangle(0, 0.1, 0, 0.45, 0.45, 0.45)
shape -= triangle(0.6, 0.1, 0.15, 0.1, 0.6, 0.45)
shape.width = 0.6
_glyphs['z'] = shape


shape = MathTree.Constant(1)
shape.bounds = [0,0,0,0,None,None,None]
shape.shape = True
shape.width = 0.55
shape.xmin, shape.xmax = 0, 0.55
shape.ymin, shape.ymax = 0, 1
_glyphs[' '] = shape


shape = circle(0.075, 0.075, 0.075)
shape = scale_y(shape, 0.075, 3)
shape &= rectangle(0.0, 0.15, -0.15, 0.075)
shape -= triangle(0.075, 0.075, 0.0, -0.15, -0.5, 0.075)
shape += circle(0.1, 0.075, 0.075)
shape.width = 0.175
_glyphs[','] = shape


shape = circle(0.075, 0.075, 0.075)
shape.width = 0.15
_glyphs['.'] = shape


shape = rectangle(0, 0.1, 0.55, 0.8)
shape.width = 0.1
_glyphs["'"] = shape

shape = rectangle(0, 0.1, 0.55, 0.8) + rectangle(0.2, 0.3, 0.55, 0.8)
shape.width = 0.3
_glyphs['"'] = shape


shape = circle(0.075, 0.15, 0.075) + circle(0.075, 0.45, 0.075)
shape.width = 0.15
_glyphs[':'] = shape


shape = circle(0.075, 0.15, 0.075)
shape = scale_y(shape, 0.15, 3)
shape &= rectangle(0.0, 0.15, -0.075, 0.15)
shape -= triangle(0.075, 0.15, 0.0, -0.075, -0.5, 0.15)
shape += circle(0.075, 0.45, 0.075)
shape += circle(0.1, 0.15, 0.075)
shape.width = 0.15
_glyphs[';'] = shape


shape = rectangle(0.025, 0.125, 0.3, 1)
shape += circle(0.075, 0.075, 0.075)
shape.width = 0.1
_glyphs['!'] = shape


shape = rectangle(0.05, 0.4, 0.35, 0.45)
shape.width = 0.45
_glyphs['-'] = shape


shape = circle(0, 0.4, 0.6) - scale_x(circle(0, 0.4, 0.5), 0, 0.7)
shape &= rectangle(0, 0.6, -0.2, 1)
shape = scale_x(shape, 0, 1/2.)
shape.width = 0.3
_glyphs[')'] = shape


shape = circle(0.6, 0.4, 0.6) - scale_x(circle(0.6, 0.4, 0.5), 0.6, 0.7)
shape &= rectangle(0, 0.6, -0.2, 1)
shape = scale_x(shape, 0, 1/2.)
shape.width = 0.3
_glyphs['('] = shape


shape = rectangle(0, 0.3, 0, 1)
shape -= circle(0, 1, 0.2)
shape -= rectangle(0, 0.2, 0, 0.7)
shape.width = 0.3
_glyphs['1'] = shape


shape = circle(0.275, .725, .275)
shape -= circle(0.275, 0.725, 0.175)
shape -= rectangle(0, 0.55, 0, 0.725)
shape += rectangle(0, 0.55, 0, 0.1)
shape += triangle(0, 0.1, 0.45, 0.775, 0.55, 0.725)
shape += triangle(0, 0.1, 0.55, 0.725, 0.125, 0.1)
shape.width = 0.55
_glyphs['2'] = shape


shape = circle(0.3, 0.725, 0.275)
shape -= circle(0.3, 0.725, 0.175)
shape += circle(0.3, 0.275, 0.275)
shape -= circle(0.3, 0.275, 0.175)
shape -= rectangle(0, 0.275, 0.275, 0.725)
shape.width = 0.55
_glyphs['3'] = shape


shape = triangle(-0.10, 0.45, 0.4, 1, 0.4, 0.45)
shape += rectangle(0.4, 0.5, 0, 1)
shape -= triangle(0.4, 0.85, 0.4, 0.55, 0.1, 0.55)
shape &= rectangle(0, 0.5, 0, 1)
shape.width = 0.5
_glyphs['4'] = shape


shape = circle(0.325, 0.325, 0.325) - circle(0.325, 0.325, 0.225)
shape -= rectangle(0, 0.325, 0.325, 0.65)
shape += rectangle(0, 0.325, 0.55, 0.65)
shape += rectangle(0, 0.1, 0.55, 1)
shape += rectangle(0.1, 0.65, 0.9, 1)
shape.width = 0.65
_glyphs['5'] = shape


shape = circle(0.275, 0.725, 0.275) - scale_y(circle(0.275, 0.725, 0.175), .725, 1.2)
shape &= rectangle(0, 0.55, 0.725, 1)
shape -= triangle(0.275, 0.925, 0.55, 0.9, 0.55, 0.725)
shape = scale_y(shape, 1, 2)
shape = scale_x(shape, 0, 1.1)
shape -= rectangle(0.275, 0.65, 0., 0.7)
shape += rectangle(0, 0.1, 0.275, 0.45)
shape += circle(0.275, 0.275, 0.275) - circle(0.275, 0.275, 0.175)
shape.width = 0.55
_glyphs['6'] = shape


shape = rectangle(0, 0.6, 0.9, 1)
shape += triangle(0, 0, 0.475, 0.9, 0.6, 0.9)
shape += triangle(0, 0, 0.6, 0.9, 0.125, 0)
shape.width = 0.6
_glyphs['7'] = shape


shape = circle(0.3, 0.725, 0.275)
shape -= circle(0.3, 0.725, 0.175)
shape += circle(0.3, 0.275, 0.275)
shape -= circle(0.3, 0.275, 0.175)
shape.width = 0.55
_glyphs['8'] = shape


shape = reflect_x(reflect_y(_glyphs['6'], 0.5), _glyphs['6'].width/2)
shape.width = _glyphs['6'].width
_glyphs['9'] = shape


shape = circle(0.5, 0.5, 0.5) - scale_x(circle(0.5, 0.5, 0.4), 0.5, 0.7**0.5)
shape = scale_x(shape, 0, 0.7)
shape.width = 0.7
_glyphs['0'] = shape


shape = rectangle(0., 0.5, 0.45, 0.55)
shape += rectangle(0.2, 0.3, 0.25, 0.75)
shape.width = 0.55
_glyphs['+'] = shape


shape = triangle(0, 0, 0.425, 1, 0.55, 1)
shape += triangle(0, 0, 0.55, 1, 0.125, 0)
shape.width = 0.55
_glyphs['/'] = shape


shape = circle(0.275, 0.725, 0.275) - circle(0.275, 0.725, 0.175)
shape -= rectangle(0, 0.275, 0.45, 0.725)
shape += rectangle(0.225, 0.325, 0.3, 0.55)
shape += circle(0.275, 0.075, 0.075)
shape.width = 0.55
_glyphs['?'] = shape

del shape

########NEW FILE########
__FILENAME__ = core
import  math
import  inspect

import  wx

import  koko
from    koko.prims.evaluator import Evaluator, NameEvaluator
from    koko.prims.editpanel import EditPanel

################################################################################

class PrimSet(object):

    class PrimDict(object):
        def __init__(self, L):  self.L = L
        def __getitem__(self, name):
            if name in dir(math):   return getattr(math, name)
            found = [s for s in self.L if s.name == name]
            if found:   return found[0]
            else:       raise KeyError(name)

    def __init__(self, reconstructor=None):
        self.shapes = []
        self.map = PrimSet.PrimDict(self.shapes)
        if reconstructor:
            self.reconstruct(reconstructor)
        self.undo_stack = [[]]

    def add(self, s):
        if isinstance(s, list): self.shapes += s
        else:                   self.shapes.append(s)

    ########################################

    def reconstructor(self):
        '''Returns a set of reconstructor objects, used to regenerate
           a set of primitives.'''
        return [s.reconstructor() for s in self.shapes]

    def to_script(self):
        ''' Returns a string that can be embedded in a script;
            this is the same as a normal reconstructor, but classes
            have been replaced by their names.'''
        r = [s.reconstructor() for s in self.shapes]
        def clsname(cls):
            return cls.__module__ + '.' + cls.__name__
        r = [(clsname(q[0]), q[1]) for q in r]
        return '[' + ','.join('(%s, %s)' % q for q in r) + ']'

    ########################################

    def reconstruct(self, R):
        ''' Reload the set of shapes from a reconstructor object.
            Returns self.'''
        self.clear()
        for r in R:
            self.shapes += [r[0](**r[1])]

    ########################################

    def clear(self):
        ''' Delete all shapes. '''
        while self.shapes:
            self.delete(self.shapes[0])

    ########################################

    def delete(self, s):
        ''' Delete a particular shape.'''

        if s in self.shapes:
            s.deleted = True
            s.close_panel()
            self.shapes.remove(s)

            self.modified = True
        elif hasattr(s, 'parent'):
            self.delete(s.parent)

    ########################################

    def mouse_pos(self, x, y):
        ''' Update the hover state of nodes based on mouse movement,
            returning True if anything changed (which implies a redraw). '''

        return True

        t = self.get_target(x, y)
        changed = False
        for s in self.shapes:
            if s == t:  continue
            if s.hover: changed = True
            s.hover = False

        if t:
            if not t.hover: changed = True
            t.hover = True

        return changed

    ########################################

    def get_target(self, x, y):
        ''' Returns the shape at the given x,y coordinates
            with the lowest priority. '''

        r = 10/koko.CANVAS.scale
        found = [f for f in [s.intersects(x, y, r) for s in self.shapes]
                 if f is not None]
        if all(f is None for f in found):   return None
        min_rank = min(f.priority for f in found if f is not None)
        return [f for f in found if f.priority == min_rank][0]

    ########################################

    def draw(self, canvas):
        for s in self.shapes:
            if s.panel: s.panel.slide()

        ranked = {}
        for s in self.shapes:
            ranked[s.priority] = ranked.get(s.priority, []) + [s]
        for k in sorted(ranked.keys())[::-1]:
            for s in ranked[k]:
                s.draw(canvas)

        for s in self.shapes:
            if (s.hover or s.dragging) and not s.panel:
                s.draw_label(canvas)

    ########################################

    def push_stack(self):
        ''' Stores a reconstructor on the stack for undo functionality.'''
        R = self.reconstructor()
        if self.undo_stack == [] or R != self.undo_stack[-1]:
            self.undo_stack.append(R)
            koko.APP.savepoint(False)

    def undo(self, event=None):
        ''' Undoes the last operation.

            (He sees what's left of the Rippling Walls,
             years of work undone in an instant.)'''
        R = self.reconstructor()

        try:                target = [s for s in self.shapes if s.panel][0]
        except IndexError:  target = None

        if R != self.undo_stack[-1]:
            self.reconstruct(self.undo_stack[-1])
        elif len(self.undo_stack) >= 2:
            self.reconstruct(self.undo_stack[-2])
            self.undo_stack = self.undo_stack[:-1]

        # If we find a shape in the restored set with the same name
        # as the one with an open panel initially, then re-open the
        # panel
        try:    target = [s for s in self.shapes if s.name == target.name][0]
        except (IndexError, AttributeError):    pass
        else:   target.open_panel()

        koko.APP.savepoint(False)
        koko.APP.mark_changed_design()

    @property
    def can_undo(self):
        return (len(self.undo_stack) >= 2 or
                self.reconstructor() != self.undo_stack[-1])

    ########################################

    def get_name(self, prefix, count=1, i=0):
        '''Returns a non-colliding name with the given prefix.'''

        names = [s.name for s in self.shapes]
        results = []
        while len(results) < count:
            while '%s%i' % (prefix, i) in names:
                i += 1
            results.append('%s%i' % (prefix, i))
            names.append(results[-1])

        return results[0] if count == 1 else results

    ########################################

    def update_panels(self):
        for p in [s.panel for s in self.shapes if s.panel]:
            p.update()

    def close_panels(self):
        for s in self.shapes: s.close_panel()

    ########################################

    @property
    def dict(self):
        return dict((s.name, s) for s in self.shapes)

################################################################################

class Primitive(object):
    '''Defines a geometric object that the user can interact with.'''

    def __init__(self, name='primitive'):

        self.parameters = {'name': NameEvaluator(name)}

        # Variables related to user interaction.
        self.deleted    = False

        self.panel      = None

        # Priority for selection (lower is more important)
        self.priority = 0

    @property
    def name(self):
        ''' Returns the primitive's name.'''
        return self.parameters['name'].eval()

    @property
    def valid(self):
        '''Returns true if all parameters are valid.'''
        return all(p.valid for p in self.parameters.itervalues())

    @property
    def modified(self):
        ''' Returns true if any parameters are modified.'''
        return any(p.modified for p in self.parameters.itervalues())

    @modified.setter
    def modified(self, value):
        ''' Sets the modified flag of each parameter to the provided value.'''
        for p in self.parameters.itervalues():
            p.modified = value

    # Child classes should redefine these to appropriate values.
    @property
    def x(self): return 0
    @property
    def y(self): return 0

    @property
    def hover(self):
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    @property
    def dragging(self):
        return koko.CANVAS.drag_target == self

    def drag(self, dx, dy):
        ''' This function should drag a point by the given offsets.'''
        pass

    def reconstructor(self):
        ''' Function that defines how to reconstruct this object.

            Returns a tuple containing the object class and a
            dictionary mapping parameter names to their expressions.'''

        argspec = inspect.getargspec(self.__class__.__init__)
        args = argspec.args[1:]
        return (self.__class__,
                dict((k, self.parameters[k].expr) for k in self.parameters
                if k in args))


    def create_evaluators(self, **kwargs):
        ''' Create a set of evaluators with initial values and types.

            Arguments should be of the form
                name = (expression, type)
            e.g.
                child = ('otherPoint', Point)
                x = (12.3, float)

            The evaluators live in self.parameters, and are also added
            to the class as a property (so they can be accessed as
            self.child, self.x, etc.)
           '''

        for arg in kwargs.keys():

            # Create an evaluator with initial expression and desired type
            self.parameters[arg] = Evaluator(*kwargs[arg])

            # Create a property to automatically get a value from
            # the evaluator.  The lambda is a bit strange looking to
            # prevent problems with for loop variable binding.
            prop = property(lambda instance, p=arg:
                                instance.parameters[p].eval())
            setattr(self.__class__, arg, prop)

    def draw_label(self, canvas):
        ''' Labels this node with its name.'''

        x, y = canvas.pos_to_pixel(self.x, self.y)

        canvas.dc.SetFont(wx.Font(12 + 4*self.priority,
                                  wx.FONTFAMILY_DEFAULT,
                                  wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_NORMAL))

        w, h = canvas.dc.GetTextExtent(self.name)

        canvas.dc.SetBrush(wx.Brush((0, 0, 0, 150)))
        canvas.dc.SetPen(wx.TRANSPARENT_PEN)
        canvas.dc.DrawRectangle(x, y - h - 10, w + 10, h+10)

        canvas.dc.SetTextForeground((255,255,255))
        canvas.dc.DrawText(self.name, x + 5, y - h - 5)

    def close_panel(self, event=None):

        # Close the panel itself
        if self.panel:
            koko.PRIMS.push_stack()
            self.panel.Destroy()
        self.panel = None
        koko.CANVAS.Refresh()

    def open_panel(self, event=None):
        self.close_panel()
        self.panel = EditPanel(self)
        koko.CANVAS.Refresh()

########NEW FILE########
__FILENAME__ = editpanel
import wx

import koko
from koko.themes          import APP_THEME
from koko.prims.evaluator import Evaluator

class EditPanel(wx.Panel):
    ''' Panel that allows us to edit parameters of a Primitive.
        Child of the global canvas instance.'''

    def __init__(self, target):
        wx.Panel.__init__(self, koko.CANVAS)

        self.target = target

        sizer = wx.FlexGridSizer(
            rows=len(target.PARAMETERS)+2,
            cols = 2)

        txt = wx.StaticText(self, label='type', size=(-1, 25),
                            style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        sizer.Add(txt, border=3, flag=wx.BOTTOM|wx.TOP|wx.RIGHT|wx.EXPAND)

        # Add this panel's class
        classTxt =  wx.StaticText(self, size=(-1, 25),
                                  label=target.__class__.__name__)
        classTxt.SetFont(wx.Font(14, family=wx.FONTFAMILY_DEFAULT,
                                 style=wx.ITALIC, weight=wx.BOLD))
        sizer.Add(classTxt, border=1, flag=wx.BOTTOM|wx.TOP|wx.LEFT|wx.EXPAND)

        boxes = []
        for p in target.PARAMETERS:
            boxes.append(self.add_row(sizer, p))
        self.update = lambda: [b.pull() for b in boxes]

        outer = wx.BoxSizer()
        outer.Add(sizer, border=10, flag=wx.ALL)
        self.SetSizerAndFit(outer)
        APP_THEME.apply(self)

        koko.CANVAS.Refresh()

    ########################################

    def add_row(self, sizer, label):
        ''' Helper function to add a row to a sizer.

            Returns a TextCtrl with extra field 'label'.
        '''

        # Create label
        labelTxt = wx.StaticText(self, label=label,
                                 style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE,
                                 size=(-1, 25))
        sizer.Add(labelTxt, border=3,
                  flag=wx.BOTTOM|wx.TOP|wx.RIGHT|wx.EXPAND)

        # Create input box
        inputBox = wx.TextCtrl(self, size=(150, 25),
                               style=wx.NO_BORDER|wx.TE_PROCESS_ENTER)
        sizer.Add(inputBox, border=3,
                  flag=wx.BOTTOM|wx.TOP|wx.LEFT|wx.EXPAND)

        # Add extra field to input box
        inputBox.label = label

        # Silly hack to avoid selecting all of the text when
        # this row gets focus.
        def focus(event):
            txt = event.GetEventObject()
            txt.SetSelection(0,0)
            if hasattr(txt, 'lastInsertionPoint'):
                txt.SetInsertionPoint(txt.lastInsertionPoint)
                del txt.lastInsertionPoint
        def lost_focus(event):
            txt = event.GetEventObject()
            txt.lastInsertionPoint = txt.GetInsertionPoint()

        inputBox.Bind(wx.EVT_SET_FOCUS, focus)
        inputBox.Bind(wx.EVT_KILL_FOCUS, lost_focus)

        # pull() synchronizes the text in the box with the
        # parameter or property referred to in the target object
        def pull():
            try:
                a = self.target.parameters[label]
                if a.expr != inputBox.GetValue():
                    ip = inputBox.GetInsertionPoint()
                    inputBox.SetValue(a.expr)
                    inputBox.SetInsertionPoint(ip)
            except KeyError:
                a = getattr(self.target, label)
                if str(a) != inputBox.GetValue():
                    inputBox.SetValue(str(a))
        inputBox.pull = pull

        # push() synchronizes the parameter expression in the
        # target object with the text in the input box.
        def push():
            a = self.target.parameters[label]
            a.set_expr(inputBox.GetValue())
            a.eval()
            inputBox.SetForegroundColour(APP_THEME.foreground
                                         if a.valid else
                                         wx.Colour(255, 80, 60))
        inputBox.push = push

        inputBox.pull()

#        inputBox.Bind(wx.EVT_CHAR, self.char)
        inputBox.Bind(wx.EVT_TEXT, self.changed)
        inputBox.Bind(wx.EVT_TEXT_ENTER, self.target.close_panel)

        return inputBox

    ########################################

    def changed(self, event):

        event.GetEventObject().push()
        koko.CANVAS.Refresh()

    ########################################

    def slide(self):
        pt = (wx.Point(*koko.CANVAS.pos_to_pixel(self.target.x, self.target.y)) +
              wx.Point(4,4))
        self.Move(pt)


########NEW FILE########
__FILENAME__ = evaluator
import re

import koko

class Evaluator(object):
    '''Class to do lazy evaluation of expressions.'''

    def __init__(self, expr, out):
        self.type   = out
        self._expr  = str(expr)

        # Add a default value for self.result
        self.recursing  = False
        self.cached     = False

        self.result = out() if out is not None else None
        self.eval()

    def eval(self):
        '''Evaluate the given expression.

           Sets self.valid to True or False depending on whether the
           evaluation succeeded.'''

        if self.cached: return self.result

        # Prevent recursive loops (e.g. defining pt0.x = pt0.x)
        if self.recursing:
            self.valid = False
            raise RuntimeError('Bad recursion')

        # Set a few local variables
        self.recursing  = True
        self.valid      = True

        try:
            c = eval(self._expr, {}, koko.PRIMS.map)
        except:
            self.valid = False
        else:
            # If we have a desired type and we got something else,
            # try to coerce the returned value into the desired type
            if self.type is not None and not isinstance(c, self.type):
                try:    c = self.type(c)
                except: self.valid = False

            # Make sure that we haven't ended up invalid
            # due to bad recursion somewhere down the line
            if self.valid: self.result = c

        # We're no longer recursing, so we can unflag the variable
        self.recursing = False

        return self.result

    @property
    def expr(self):
        return self._expr
    @expr.setter
    def expr(self, value):
        self.set_expr(value)
    def set_expr(self, value):
        new = str(value)
        old = self._expr
        self._expr = new
        if new != old:
            self.cached = False
            koko.APP.mark_changed_design()
            koko.PRIMS.update_panels()

################################################################################

class NameEvaluator(Evaluator):
    '''Class to store valid variable names.'''
    def __init__(self, expr):
        Evaluator.__init__(self, expr, str)

    def eval(self):
        ''' Check to see that the expression is a valid variable name
            and return it.'''
        if self.cached: return self.result

        if self.valid_regex.match(self.expr):
            self.valid = True
            self.result = self.expr
        else:
            self.valid = False
        self.cached = True
        return self.result


    valid_regex = re.compile('[a-zA-Z_][0-9a-zA-Z_]*$')

########NEW FILE########
__FILENAME__ = lines
import  math
import  wx

import  koko
from    koko.prims.core     import Primitive
from    koko.prims.points   import Point

MENU_NAME = 'Lines'

class Line(Primitive):
    ''' Defines a line terminated at two points.'''

    MENU_NAME = 'Line'
    PARAMETERS = ['name','A','B']

    def __init__(self, name='line', A='pt0', B='pt1'):
        Primitive.__init__(self, name)
        self.priority = 1
        self.create_evaluators(A=(A, Primitive), B=(B, Primitive))

    @property
    def x(self):    return (self.A.x + self.B.x)/2.
    @property
    def y(self):    return (self.A.y + self.B.y)/2.

    @property
    def hover(self):
        if self.A.dragging or self.B.dragging:    return False
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    @classmethod
    def new(cls, x, y, scale):
        names = koko.PRIMS.get_name('pt',2)
        A = Point(names[0], x-scale, y)
        B = Point(names[1], x+scale, y)
        return A, B, cls(koko.PRIMS.get_name('line'), *names)

    def draw(self, canvas):
        canvas.dc.SetPen(wx.Pen((100, 150, 255), 4))
        x0, y0 = canvas.pos_to_pixel(self.A.x, self.A.y)
        x1, y1 = canvas.pos_to_pixel(self.B.x, self.B.y)
        canvas.dc.DrawLine(x0, y0, x1, y1)

    def intersects(self, x, y, r):

        x0, y0 = self.A.x, self.A.y
        x1, y1 = self.B.x, self.B.y
        L = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)

        # Find unit vectors running parallel and perpendicular to the line
        try:    perp = ((y1 - y0)/L, -(x1 - x0)/L)
        except ZeroDivisionError:   perp = (float('inf'), float('inf'))
        try:    para = ((x1 - x0)/L,  (y1 - y0)/L)
        except ZeroDivisionError:   para = (float('inf'), float('inf'))

        para = -((x0 - x)*para[0] + (y0 - y)*para[1])
        if para <  -r:   return None
        if para > L+r:   return None

        # Perpendicular distance to line
        return self if abs((x0 - x)*perp[0] +
                           (y0 - y)*perp[1]) < r else None

    def drag(self, dx, dy):
        self.A.drag(dx, dy)
        self.B.drag(dx, dy)



########NEW FILE########
__FILENAME__ = menu
import inspect

import wx

from   koko.prims.core import Primitive

import koko.prims.points
import koko.prims.utils
import koko.prims.lines

constructors = {}
for _, module in inspect.getmembers(koko.prims):
    if not inspect.ismodule(module):        continue
    try:    menu_name = module.MENU_NAME
    except AttributeError:  continue

    for _, cls in inspect.getmembers(module):
        if not inspect.isclass(cls) or not issubclass(cls, Primitive):
            continue

        if inspect.getmodule(cls) != module:    continue

        try:    name = cls.MENU_NAME
        except AttributeError:  continue

        if not name in constructors:    constructors[menu_name] = {}
        constructors[menu_name][name] = cls.new

def show_menu():
    ''' Returns a menu of constructors for a prim objects. '''

    def build_from(init):
        ''' Decorator that calls the provided method with appropriate
            values for x, y, and scale.  Results are added to the global
            PrimSet object in koko.PRIMS. '''

        koko.CANVAS.mouse = (wx.GetMousePosition() -
                             koko.CANVAS.GetScreenPosition())
        koko.CANVAS.click = koko.CANVAS.mouse
        x, y = koko.CANVAS.pixel_to_pos(*koko.CANVAS.mouse)
        scale = 100/koko.CANVAS.scale

        p = init(x, y, scale)
        if type(p) is list:         p = tuple(p)
        elif type(p) is not tuple:  p = (p,)

        koko.CANVAS.drag_target = p[-1]
        for q in p: koko.PRIMS.add(q)
        koko.PRIMS.close_panels()

    menu = wx.Menu()
    for T in sorted(constructors):
        sub = wx.Menu()
        for name in sorted(constructors[T]):
            init = constructors[T][name]
            m = sub.Append(wx.ID_ANY, text=name)
            koko.CANVAS.Bind(wx.EVT_MENU, lambda e, c=init: build_from(c), m)
        menu.AppendMenu(wx.ID_ANY, T, sub)
    return menu

########NEW FILE########
__FILENAME__ = points
import  wx
import  koko
from    koko.prims.core import Primitive

MENU_NAME = 'Points'

class Point(Primitive):
    ''' Defines a basic point with intersect and draw functions.'''

    MENU_NAME = 'Point'
    PARAMETERS = ['name','x','y']

    def __init__(self, name='point', x=0, y=0):
        Primitive.__init__(self, name)
        self.create_evaluators(x=(x,float), y=(y,float))

    @classmethod
    def new(cls, x, y, scale):
        name = koko.PRIMS.get_name('pt')
        return cls(name, x, y)

    def drag(self, dx, dy):
        try:    x = float(self.parameters['x'].expr)
        except ValueError:  pass
        else:   self.parameters['x'].expr = str(x+dx)

        try:    y = float(self.parameters['y'].expr)
        except ValueError:  pass
        else:   self.parameters['y'].expr = str(y+dy)

    def intersects(self, x, y, r):
        ''' Checks whether a circle with center (x,y) and radius r
            intersects this point.'''
        distance = ((x - self.x)**2 + (y - self.y)**2)**0.5
        return self if distance < r else None

    def draw(self, canvas):
        ''' Draws a vertex on the given canvas.

            A valid point is drawn as a circle, while an invalid vertex
            is drawn as a red X.  In each case, a highlight is drawn
            if the object is hovered, selected, or dragged.
        '''

        # Find canvas-space coordinates
        x, y = canvas.pos_to_pixel(self.x, self.y)

        if self.valid:
            light = (200, 200, 200)
            dark  = (100, 100, 100)
        else:
            light = (255, 80, 60)
            dark  = (255, 0, 0)

        # Valid vertexs are drawn as circles
        if self.valid:

            # Draw small marks to show if we can drag the point
            if self.dragging or self.hover:
                self.draw_handles(canvas)

            canvas.dc.SetBrush(wx.Brush(light))
            canvas.dc.SetPen(wx.Pen(dark, 2))
            canvas.dc.DrawCircle(x, y, 6)

        # Invalid vertexs are drawn as red Xs
        else:
            r = 3
            if self.hover or self.dragging:
                canvas.dc.SetPen(wx.Pen(light, 8))
                canvas.dc.DrawLine(x-r, y-r, x+r, y+r)
                canvas.dc.DrawLine(x-r, y+r, x+r, y-r)
            canvas.dc.SetPen(wx.Pen(dark, 4))
            canvas.dc.DrawLine(x-r, y-r, x+r, y+r)
            canvas.dc.DrawLine(x-r, y+r, x+r, y-r)

    def draw_handles(self, canvas):
        ''' Draws small handles based on whether we can drag this
            point around on its two axes. '''

        x, y = canvas.pos_to_pixel(self.x, self.y)

        try:    float(self.parameters['x'].expr)
        except ValueError:  x_free = False
        else:               x_free = True

        try:    float(self.parameters['y'].expr)
        except ValueError:  y_free = False
        else:               y_free = True

        x_light = (200, 200, 200) if x_free else (100, 100, 100)
        x_dark  = (100, 100, 100) if x_free else(60, 60, 60)

        y_light = (200, 200, 200) if y_free else (100, 100, 100)
        y_dark  = (100, 100, 100) if y_free else(60, 60, 60)


        canvas.dc.SetPen(wx.Pen(x_dark, 8))
        canvas.dc.DrawLine(x-10, y, x+10, y)

        canvas.dc.SetPen(wx.Pen(y_dark, 8))
        canvas.dc.DrawLine(x, y-10, x, y+10)

        canvas.dc.SetPen(wx.Pen(x_light, 4))
        canvas.dc.DrawLine(x-10, y, x+10, y)

        canvas.dc.SetPen(wx.Pen(y_light, 4))
        canvas.dc.DrawLine(x, y-10, x, y+10)

########NEW FILE########
__FILENAME__ = utils
import  wx
import  koko
import  math

from    koko.prims.core import Primitive

MENU_NAME = 'Utilities'

class Slider(Primitive):
    ''' Defines a slider that you can slide. '''

    MENU_NAME = 'Slider'
    PARAMETERS = ['name','min','max','value','size']

    ################################################################
    class Handle(Primitive):
        def __init__(self, parent):
            Primitive.__init__(self, 'slider')
            self.parent = parent

        def drag(self, dx, dy):
            dx *= (self.parent.max - self.parent.min) / self.parent.size
            self.parent.parameters['value'].expr = self.parent.value + dx

        def intersects(self, x, y, r):
            if (abs(y - self.y) < 10/koko.CANVAS.scale and
                abs(x - self.x) < 5/koko.CANVAS.scale):
                return self

        @property
        def hover(self):
            if self.parent.dragging:    return False
            x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                              koko.CANVAS.GetScreenPosition()))
            r = 5 / koko.CANVAS.scale
            return self.intersects(x, y, r) == self

        @property
        def x(self):
            d = float(self.parent.max - self.parent.min)
            if d:   p = (self.parent.value - self.parent.min) / d
            else:   p = 0
            L = self.parent.size
            return self.parent.x - L/2. + L*p
        @property
        def y(self):    return self.parent.y

        def draw(self, canvas):
            if self.parent.value < self.parent.min:
                self.parent.parameters['value'].expr = self.parent.min
            if self.parent.value > self.parent.max:
                self.parent.parameters['value'].expr = self.parent.max
            x, y = canvas.pos_to_pixel(self.x, self.y)

            if self.parent.valid:
                highlight = (160, 160, 160)
                glow = (128, 128, 128, 128)
                light = (128, 128, 128)
                dark  = (64, 64, 64)
            else:
                highlight = (255, 160, 140)
                glow = (255, 80, 60, 128)
                light = (255, 80, 60)
                dark  = (255, 0, 0)

            if self.hover or self.dragging:
                self.draw_label(canvas)
                canvas.dc.SetBrush(wx.Brush(light))
                canvas.dc.SetPen(wx.Pen(glow, 6))
                canvas.dc.DrawRectangle(x - 5, y-10, 10, 20)

            canvas.dc.SetBrush(wx.Brush(light))
            canvas.dc.SetPen(wx.Pen(dark, 2))
            canvas.dc.DrawRectangle(x - 5, y-10, 10, 20)
            p = wx.Pen(highlight, 2)
            p.SetCap(wx.CAP_BUTT)
            canvas.dc.SetPen(p)
            canvas.dc.DrawLine(x+3, y-9, x+3, y+9)

        def draw_label(self, canvas):
            ''' Labels this node with its name and value.'''

            x, y = canvas.pos_to_pixel(self.x, self.y)

            canvas.dc.SetFont(wx.Font(12 + 4*self.priority,
                                      wx.FONTFAMILY_DEFAULT,
                                      wx.FONTSTYLE_NORMAL,
                                      wx.FONTWEIGHT_NORMAL))

            txt = '%s: %2g' % (self.parent.name, self.parent.value)
            w, h = canvas.dc.GetTextExtent(txt)
            x -= w/2
            y -= 14

            canvas.dc.SetBrush(wx.Brush((0, 0, 0, 150)))
            canvas.dc.SetPen(wx.TRANSPARENT_PEN)
            canvas.dc.DrawRectangle(x-5, y - h - 5, w + 10, h+10)

            canvas.dc.SetTextForeground((255,255,255))
            canvas.dc.DrawText(txt, x, y - h)

        def open_panel(self):   self.parent.open_panel()
        def close_panel(self):  self.parent.close_panel()

    ################################################################

    def __init__(self, name='point', x=0, y=0, min=0, max=1,
                 value=0.5, size=1):
        Primitive.__init__(self, name)
        self.handle = Slider.Handle(self)
        self.create_evaluators(x=(x,float), y=(y,float),
                               min=(min,float), max=(max,float),
                               value=(value, float), size=(size, float))

    @classmethod
    def new(cls, x, y, scale):
        name = koko.PRIMS.get_name('slider')
        return cls(name, x, y, size=2.5*float('%.1f' % scale))

    @property
    def hover(self):
        if self.handle.dragging:    return False
        x, y = koko.CANVAS.pixel_to_pos(*(wx.GetMousePosition() -
                                          koko.CANVAS.GetScreenPosition()))
        r = 5 / koko.CANVAS.scale
        return self.intersects(x, y, r) == self

    def drag(self, dx, dy):
        self.parameters['x'].expr = str(self.x + dx)
        self.parameters['y'].expr = str(self.y + dy)

    def intersects(self, x, y, r):
        if self.handle.intersects(x, y, r):
            return self.handle
        elif abs(y - self.y) < r and abs(x - self.x) < self.size/2 + r:
            return self

    def draw(self, canvas):
        x, y = canvas.pos_to_pixel(self.x, self.y)
        w    = canvas.pos_to_pixel(self.size)

        if self.valid:
            highlight = (128, 128, 128, 128)
            light = (128, 128, 128)
            dark  = (64, 64, 64)
        else:
            highlight = (255, 80, 60, 128)
            light = (255, 80, 60)
            dark  = (255, 0, 0)

        if self.hover:
            canvas.dc.SetPen(wx.Pen(highlight, 10))
            canvas.dc.DrawLine(x - w/2, y, x+w/2, y)
        elif self.dragging:
            canvas.dc.SetPen(wx.Pen(highlight, 8))
            canvas.dc.DrawLine(x - w/2, y, x+w/2, y)

        canvas.dc.SetPen(wx.Pen(dark, 6))
        canvas.dc.DrawLine(x - w/2, y, x+w/2, y)
        canvas.dc.SetPen(wx.Pen(light, 4))
        canvas.dc.DrawLine(x - w/2, y, x+w/2, y)

        self.handle.draw(canvas)

########NEW FILE########
__FILENAME__ = render
from    datetime    import datetime
import  Queue
import  re
import  StringIO
import  sys
import  threading
import  traceback

import  wx

import  koko
from    koko.struct         import Struct
from    koko.fab.asdf       import ASDF
from    koko.fab.tree       import MathTree
from    koko.fab.fabvars    import FabVars
from    koko.fab.mesh       import Mesh

from    koko.c.region       import Region


class RenderTask(object):
    """ @class RenderTask
        @brief A render job running in a separate thread
    """

    def __init__(self, view, script=None, cad=None):
        """ @brief Constructs and starts a render task.
            @param view Render view (Struct with xmin, xmax, ymin, ymax, zmin, zmax, and pixels_per_unit member variables)
            @param script Source script to render
            @param cad Data structure from previous run
        """

        if not (bool(script) ^ bool(cad)):
            raise Exception('RenderTask must be initialized with either a script or a cad structure.')

        ## @var view
        # Struct representing render view
        self.view    = view

        ## @var script
        # String containing design script
        self.script  = script

        ## @var cad
        # FabVars structure containing pre-computed results
        self.cad     = cad

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var output
        # String holding text to be loaded into the output panel
        self.output  = ''

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

########################################

    def run(self):
        """ @brief Runs the given task
            @details Renders file and loads results into canvas(es) if successful.
        """
        start = datetime.now()

        # Clear markings from previous runs
        koko.CANVAS.border   = None
        koko.GLCANVAS.border = None
        koko.FRAME.status = ''
        koko.EDITOR.error_marker = None

        # Add the top-level header to the output pane
        self.output += '####       Rendering image      ####\n'

        # Run cad_math to generate a cad structure
        make_mesh = self.cad is None or koko.GLCANVAS.loaded is False

        # Try to generate the cad structure, aborting if failed
        if not self.cad and not self.cad_math():     return

        # If the cad structure defines a render mode, then enforce it.
        height = koko.FRAME.get_menu('View','2D')
        shaded = koko.FRAME.get_menu('View', '3D')
        dual = koko.FRAME.get_menu('View', 'Both')

        # If the cad file overrides the render mode, then disable
        # the menu items so that the user can't change render mode.
        if self.cad.render_mode is None:
            wx.CallAfter(height.Enable, True)
            wx.CallAfter(shaded.Enable, True)
            wx.CallAfter(dual.Enable,   True)
        else:
            wx.CallAfter(height.Enable, False)
            wx.CallAfter(shaded.Enable, False)
            wx.CallAfter(dual.Enable,   False)

        if self.cad.render_mode == '3D' and not shaded.IsChecked():
            render_mode = '3D'
            wx.CallAfter(shaded.Check, True)
            wx.CallAfter(koko.APP.render_mode, '3D')
        elif self.cad.render_mode == '2D' and not height.IsChecked():
            render_mode = '2D'
            wx.CallAfter(height.Check,True)
            wx.CallAfter(koko.APP.render_mode, '2D')
        elif shaded.IsChecked():
            render_mode = '3D'
        elif height.IsChecked():
            render_mode = '2D'
        else:
            render_mode = ('3D','2D')

        # Render and load a height-map image
        if '2D' in render_mode:

            imgs = self.make_images()
            if self.event.is_set(): return

            # Push images to the global canvas object
            koko.CANVAS.load_images(imgs, self.cad.mm_per_unit)


        # Render and load a triangulated mesh
        if make_mesh and '3D' in render_mode:
            koko.GLCANVAS.loaded = False

            images = []
            meshes = []
            try:
                image_scale = max(
                    (1e6/expr.dx*expr.dy)**0.5 for expr in self.cad.shapes
                    if not expr.dz
                )
            except ValueError:
                image_scale = 1

            for e in self.cad.shapes:
                if self.event.is_set(): return

                # If this is a full 3D model, then render it
                if e.bounded:
                    meshes.append(self.make_mesh(e))

                # If it is a 2D model, then render it as an image
                elif (self.cad.dx is not None and
                      self.cad.dy is not None):
                    images.append(self.make_flat_image(e, image_scale))

                else:
                    koko.FRAME.status = (
                        'Error:  Objects must have valid bounds!'
                    )
                    koko.GLCANVAS.border = (255, 0, 0)
                    return


            if not self.event.is_set():
                koko.GLCANVAS.clear()
                if images:  koko.GLCANVAS.load_images(images)
                if meshes:  koko.GLCANVAS.load_meshes(meshes)

                koko.GLCANVAS.loaded = True


        # Update the output pane
        koko.GLCANVAS.border = None
        koko.CANVAS.border   = None
        koko.FRAME.status = ''

        # Update the output pane
        self.output += "# #    Total time: %s s\n#" % (datetime.now() - start)

        if self.event.is_set(): return
        koko.FRAME.output = self.output

########################################

    def cad_math(self):
        """ @brief Evaluates a script to generate a FabVars data structure
            @details Stores results in self.cad and modifies UI accordingly.
            @returns True if success, False or None otherwise
        """

        koko.FRAME.status = "Converting to math string"
        now = datetime.now()

        vars = koko.PRIMS.dict
        vars['cad'] = FabVars()
        self.output += '>>  Compiling to math file\n'

        if self.event.is_set(): return

        # Modify stdout to record messages
        buffer = StringIO.StringIO()
        sys.stdout = buffer

        try:
            exec(self.script, vars)
        except:
            sys.stdout = sys.__stdout__

            # If we've failed, color the border(s) red
            koko.CANVAS.border   = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)

            # Figure out where the error occurred
            errors = traceback.format_exc().split('\n')
            errors = errors[0]+'\n'+'\n'.join(errors[3:])
            for m in re.findall(r'File "<string>", line (\d+)', errors):
                error_line = int(m) - 1
            errors = errors.replace(koko.BASE_DIR, '')

            self.output += buffer.getvalue() + errors

            # Update the status line and add an error mark in the text editor
            try:
                koko.EDITOR.error_marker = error_line
                koko.FRAME.status = "cad_math failed (line %i)" % (error_line+1)
            except NameError:
                koko.FRAME.status = "cad_math failed"
        else:
            try:                self.cad = vars['cad']
            except KeyError:    self.cad = None

            self.output += buffer.getvalue()
            dT = datetime.now() - now
            self.output += "#   cad_math time: %s \n" % dT

        # Put stdout back in place
        sys.stdout = sys.__stdout__

        koko.FRAME.output = self.output

        if not self.cad:
            koko.FRAME.states = 'Error: cad_math failed'
            koko.CANVAS.border = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)
            return
        elif self.cad.shapes == []:
            koko.FRAME.status = ('Error:  No shape defined!')
            koko.CANVAS.border = (255, 0, 0)
            koko.GLCANVAS.border = (255, 0, 0)
            return

        # Parse the math expression into a tree
        koko.FRAME.status = 'Converting to tree'
        for e in self.cad.shapes:
            self.output += ">>  Parsing string into tree\n"
            start = datetime.now()
            if bool(e.ptr):
                self.output += '#   parse time: %s\n' % (datetime.now() - start)
            # If we failed to parse the math expression, note the failure
            # and return False to indicate
            else:
                self.output += "Invalid math string!\n"
                koko.FRAME.status = ('Error:  Invalid math string.')
                koko.CANVAS.border = (255, 0, 0)
                self.cad = None
                return False


        koko.FRAME.output = self.output

        # Return True if we succeeded, false otherwise.
        return self.cad != None

########################################

    def make_images(self):
        """ @brief Renders a set of images from self.cad.shapes
            @returns List of Image objects
        """
        zmin = self.cad.zmin if self.cad.zmin is not None else 0
        zmax = self.cad.zmax if self.cad.zmax is not None else 0

        imgs = []
        for e in self.cad.shapes:
            if self.event.is_set(): return
            imgs.append(self.make_image(e, zmin, zmax))

        return imgs


    def make_flat_image(self, expr, scale):
        """ @brief Renders a flat single image
            @param expr MathTree expression
            @returns An Image object
        """
        region = Region(
            (expr.xmin-self.cad.border*expr.dx,
             expr.ymin-self.cad.border*expr.dy,
             0),
            (expr.xmax+self.cad.border*expr.dx,
             expr.ymax+self.cad.border*expr.dy,
             0),
            scale
        )

        koko.FRAME.status = 'Rendering with libfab'
        self.output += ">>  Rendering image with libfab\n"

        start = datetime.now()
        img = expr.render(region, interrupt=self.c_event,
                          mm_per_unit=self.cad.mm_per_unit)
        img.color = expr.color

        dT = datetime.now() - start
        self.output += "#   libfab render time: %s\n" % dT
        return img


    def make_image(self, expr, zmin, zmax):
        """ @brief Renders an expression
            @param expr MathTree expression
            @param zmin Minimum Z value (arbitrary units)
            @param zmax Maximum Z value (arbitrary units)
            @returns None for a null image, False for a failure, the Image if success.
        """

        # Adjust view bounds based on cad file scale
        # (since view bounds are in mm, we have to convert to the cad
        #  expression's unitless measure)
        xmin = self.view.xmin
        xmax = self.view.xmax
        ymin = self.view.ymin
        ymax = self.view.ymax

        if expr.xmin is None:   xmin = xmin
        else:   xmin = max(xmin, expr.xmin - self.cad.border*expr.dx)

        if expr.xmax is None:   xmax = xmax
        else:   xmax = min(xmax, expr.xmax + self.cad.border*expr.dx)

        if expr.ymin is None:   ymin = ymin
        else:   ymin = max(ymin, expr.ymin - self.cad.border*expr.dy)

        if expr.ymax is None:   ymax = ymax
        else:   ymax = min(ymax, expr.ymax + self.cad.border*expr.dy)

        region = Region( (xmin, ymin, zmin), (xmax, ymax, zmax),
                         self.view.pixels_per_unit )

        koko.FRAME.status = 'Rendering with libfab'
        self.output += ">>  Rendering image with libfab\n"

        start = datetime.now()
        img = expr.render(region, interrupt=self.c_event,
                          mm_per_unit=self.cad.mm_per_unit)

        img.color = expr.color
        dT = datetime.now() - start
        self.output += "#   libfab render time: %s\n" % dT
        return img

################################################################################

    def make_mesh(self, expr):
        """ @brief Converts an expression into a mesh.
            @returns The mesh, or False if failure.
        """

        self.output += '>>  Generating triangulated mesh\n'

        DEPTH = 0
        while DEPTH <= 4:

            region = Region(
                (expr.xmin - self.cad.border*expr.dx,
                 expr.ymin - self.cad.border*expr.dy,
                 expr.zmin - self.cad.border*expr.dz),
                (expr.xmax + self.cad.border*expr.dx,
                 expr.ymax + self.cad.border*expr.dy,
                 expr.zmax + self.cad.border*expr.dz),
                 depth=DEPTH
            )

            koko.FRAME.status = 'Rendering to ASDF'

            start = datetime.now()
            asdf = expr.asdf(region=region, mm_per_unit=self.cad.mm_per_unit,
                             interrupt=self.c_event)

            self.output += '#   ASDF render time: %s\n' % (datetime.now() - start)
            if self.event.is_set(): return
            koko.FRAME.output = self.output

            koko.FRAME.status = 'Triangulating'
            start = datetime.now()
            mesh = asdf.triangulate(interrupt=self.c_event)

            if mesh.vcount: break
            else:           DEPTH += 1

        mesh.source = Struct(
            type=MathTree, expr=expr.clone(),
            depth=DEPTH, scale=self.cad.mm_per_unit
        )

        if self.event.is_set(): return

        self.output += '#   Meshing time: %s\n' % (datetime.now() - start)
        self.output += "Generated {:,} vertices and {:,} triangles\n".format(
            mesh.vcount if mesh else 0, mesh.tcount if mesh else 0)

        koko.FRAME.output = self.output
        return mesh

################################################################################

class RefineTask(object):
    """ @class RefineTask
        @brief Task that refines a mesh in a separate thread.
    """

    def __init__(self, mesh):
        """ @brief Constructs a refine operation on a mesh and starts running in separate thread.
            @param mesh Mesh to refine
        """
        ## @var mesh
        # Target mesh
        self.mesh  = mesh

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        """ @brief Refines a mesh (should be run in separate thread)
        """

        koko.FRAME.status = 'Refining mesh'
        self.mesh.refine()
        koko.GLCANVAS.reload_vbos()

################################################################################

class CollapseTask(object):
    """ @class CollapseTask
        @brief Task that collapses a mesh in a separate thread.
    """

    def __init__(self, mesh):
        """ @brief Constructs a collapse operation on a mesh and starts running in separate thread.
            @param mesh Mesh to collapse
        """

        ## @var mesh
        # Target mesh
        self.mesh  = mesh

        ## @var event
        # threading.Event used to halt rendering
        self.event   = threading.Event()

        ## @var c_event
        # threading.Event used to halt rendering in C functions
        self.c_event = threading.Event()

        ## @var thread
        # threading.Thread that actually runs the task
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        """ @brief Collapses a mesh (should be run in separate thread)
        """

        koko.FRAME.status = 'Collapsing mesh'
        self.mesh.collapse()
        koko.GLCANVAS.reload_vbos()

########NEW FILE########
__FILENAME__ = struct
class Struct:
    """ @class Struct
        @brief Class with named member variables.
    """
    def __init__(self, **entries):
        """ @brief Struct constructor
            @param entries
        """
        self.__dict__.update(entries)

    def __str__(self):
        s = ''
        for d in self.__dict__:
            s += '%s:  %s\n' % (d, self.__dict__[d])
        return s[:-1]

########NEW FILE########
__FILENAME__ = taskbot
import threading
import operator
import random

import koko
from   koko.render import RenderTask, RefineTask, CollapseTask
from   koko.export import ExportTaskCad, ExportTaskASDF

from   koko.fab.fabvars import FabVars

class TaskBot(object):
    """ @class TaskBot
        @brief Manages various application threads
        @details It may hold multiple render threads, up to one export thread,
        and up to one fab subprocess.  It also keeps track of the current cad structure.
    """

    def __init__(self):
        """@brief TaskBot constructor.
        """

        ## @var cached_cad
        # Saved FabVars cad structure
        self.cached_cad     = None

        ## @var export_task
        # An ExportTask exporting the current model
        self.export_task    = None

        ## @var cam_task
        # A threading.Thread generating a CAM toolpath
        self.cam_task       = None

        ## @var refine_task
        # A RefineTask or CollapseTask modifying the displayed mesh
        self.refine_task    = None

        ## @var tasks
        # A list of RenderTask objects
        self.tasks = []

    def render(self, view, script=''):
        """ @brief Begins a new render task
            @param view View Struct (from Canvas.view)
            @param script Script text (if blank, uses cached result)
        """

        self.stop_threads()
        self.join_threads()

        if script:  self.tasks += [RenderTask(view, script=script)]
        else:       self.tasks += [RenderTask(view, cad=self.cached_cad)]


    def export(self, obj, path, **kwargs):
        """ @brief Begins a new export task
            @param obj Object to export (FabVars or ASDF)
            @param path Filename (extension is used to determine export function)
        """
        if isinstance(obj, FabVars):
            self.export_task = ExportTaskCad(path, obj, **kwargs)
        else:
            self.export_task = ExportTaskASDF(path, obj, **kwargs)


    def start_cam(self):
        """ @brief Starts a CAM path generation task
            @details The CAM thread is stored in self.cam_task.
        """
        self.cam_task = threading.Thread(target=koko.FAB.run)
        self.cam_task.daemon = True
        self.cam_task.start()

    def reset(self):
        """ @brief Attempts to halt all threads and clears cached cad data.
        """
        self.cached_cad = None
        self.stop_threads()

    def stop_threads(self):
        """ @brief Informs each thread that it should stop.
            @details Threads are collected in join_threads once they obey.
        """
        for task in self.tasks:
            task.event.set()
            task.c_event.set()

        if self.refine_task:
            self.refine_task.event.set()
            self.refine_task.c_event.set()


    def join_threads(self):
        """ @brief Joins any thread whose work is finished.

            @details Grabs the cad data structure from render threads, storing
            it as cached_cad (for later re-use).
        """

        for task in filter(lambda t: not t.thread.is_alive(), self.tasks):
            self.cached_cad = task.cad
            if task.script:    koko.FAB.set_input(task.cad)
            task.thread.join()
            task.thread = None

        self.tasks = filter(lambda t: t.thread is not None, self.tasks)

        if self.cam_task and not self.cam_task.is_alive():
            self.cam_task.join()
            self.cam_task = None

        if self.export_task and not self.export_task.thread.is_alive():
            self.export_task.thread.join()
            self.export_task = None

        if self.refine_task and not self.refine_task.thread.is_alive():
            self.refine_task.thread.join()
            self.refine_task = None


    def refine(self):
        """ @brief Refines or collapses mesh as needed.
        """
        if not koko.GLCANVAS.IsShown(): return

        if (self.export_task is not None or self.refine_task is not None or
            self.cam_task is not None):
            return

        if koko.GLCANVAS.border:    return
        if koko.GLCANVAS.LOD_complete:  return

        # Make sure that at least one leaf is expandable.
        expandable = False
        for L in koko.GLCANVAS.leafs:
            if L.expandable():  expandable = True
        if not expandable:  return


        samples = koko.GLCANVAS.sample()

        expandable = {k:samples[k] for k in samples if k.expandable()}
        collapsible = {}
        for m in koko.GLCANVAS.meshes:
            collapsible.update(m.get_fills(samples))

        # Pick the section with the smallest voxel count that occupies
        # more than 5% of the screen's visible area
        best = None
        depths = set(v.source.depth for v in expandable)
        while depths:
            c = min(depths)
            b = max(
                expandable[v] for v in expandable if v.source.depth == c
            )
            if b >= 0.05:
                best = b
                break
            depths.remove(c)

        # Pick the section with the smallest voxel count that occupies
        # less than 2.5% of the screen's visible area
        worst = None
        depths = set(v.source.depth for v in collapsible)
        while depths:
            c = min(depths)
            b = min(
                collapsible[v] for v in collapsible if v.source.depth == c
            )
            if b <= 0.025:
                worst = b
                break
            depths.remove(c)


        if worst is not None:
            mesh = [d for d in collapsible if collapsible[d] == worst][0]
            self.refine_task = CollapseTask(mesh)
        elif best is not None:
            mesh = [d for d in expandable if expandable[d] == best][0]
            self.refine_task = RefineTask(mesh)
        else:
            koko.FRAME.status = ''
            koko.GLCANVAS.LOD_complete = True


########NEW FILE########
__FILENAME__ = template
TEMPLATE = '''from koko.lib.shapes import *

cad.shape = circle(0, 0, 0.5)
'''

########NEW FILE########
__FILENAME__ = themes
import wx
import wx.py
import wx.stc

class Theme:
    def __init__(self, txt, background, header, foreground, txtbox):
        self.txt = txt
        self.background = background
        self.header = header
        self.foreground = foreground
        self.txtbox = txtbox


    def apply(self, target, depth=0):
        ''' Recursively apply the theme to a frame or sizer. '''
        if isinstance(target, wx.Sizer):
            sizer = target
        else:
            if isinstance(target, wx.py.editwindow.EditWindow):
                for s in self.txt:
                    if len(s) == 3:
                        target.StyleSetBackground(s[0], s[1])
                        target.StyleSetForeground(s[0], s[2])
                    else:
                        target.StyleSetBackground(s[0], self.background)
                        target.StyleSetForeground(s[0], s[1])
            elif isinstance(target, wx.TextCtrl):
                target.SetBackgroundColour(self.txtbox)
                target.SetForegroundColour(self.foreground)
            elif hasattr(target, 'header'):
                try:
                    target.SetBackgroundColour(self.header)
                    target.SetForegroundColour(self.foreground)
                except AttributeError:
                    pass
            elif hasattr(target, 'immune'):
                pass
            else:
                try:
                    target.SetBackgroundColour(self.background)
                    target.SetForegroundColour(self.foreground)
                except AttributeError:
                    pass
            sizer = target.Sizer

        if sizer is None:   return

        for c in sizer.Children:
            if c.Window is not None:
                self.apply(c.Window, depth+1)
            elif c.Sizer is not None:
                self.apply(c.Sizer, depth+1)

DARK_THEME = Theme(
    txt=[
        (wx.stc.STC_STYLE_DEFAULT,    '#000000', '#000000'),
        (wx.stc.STC_STYLE_LINENUMBER, '#303030', '#c8c8c8'),
        (wx.stc.STC_P_CHARACTER,      '#000000', '#ff73fd'),
        (wx.stc.STC_P_CLASSNAME,      '#000000', '#96cbfe'),
        (wx.stc.STC_P_COMMENTBLOCK,   '#000000', '#7f7f7f'),
        (wx.stc.STC_P_COMMENTLINE,    '#000000', '#a8ff60'),
        (wx.stc.STC_P_DEFAULT,        '#000000', '#ffffff'),
        (wx.stc.STC_P_DEFNAME,        '#000000', '#96cbfe'),
        (wx.stc.STC_P_IDENTIFIER,     '#000000', '#ffffff'),
        (wx.stc.STC_P_NUMBER,         '#000000', '#ffffff'),
        (wx.stc.STC_P_OPERATOR,       '#000000', '#ffffff'),
        (wx.stc.STC_P_STRING,         '#000000', '#ff73fd'),
        (wx.stc.STC_P_STRINGEOL,      '#000000', '#ffffff'),
        (wx.stc.STC_P_TRIPLE,         '#000000', '#ff6c60'),
        (wx.stc.STC_P_TRIPLEDOUBLE,   '#000000', '#96cbfe'),
        (wx.stc.STC_P_WORD,           '#000000', '#b5dcff')
    ],
    background='#252525',
    header='#303030',
    foreground='#c8c8c8',
    txtbox='#353535')

SOLARIZED_THEME = Theme(
     txt=[
        (wx.stc.STC_STYLE_DEFAULT,    '#002b36' '#002b36'), # base00
        (wx.stc.STC_STYLE_LINENUMBER, '#073642','#839496'),
        (wx.stc.STC_P_CHARACTER,      '#2aa198'), # cyan
        (wx.stc.STC_P_CLASSNAME,      '#268bd2'), # blue
        (wx.stc.STC_P_COMMENTBLOCK,   '#586e75'), # base01
        (wx.stc.STC_P_COMMENTLINE,    '#586e75'), # base01
        (wx.stc.STC_P_DEFAULT,        '#657b83'), # base00
        (wx.stc.STC_P_DEFNAME,        '#268bd2'), # blue
        (wx.stc.STC_P_IDENTIFIER,     '#657b83'), # base00
        (wx.stc.STC_P_NUMBER,         '#2aa198'), # blue
        (wx.stc.STC_P_OPERATOR,       '#657b83'), # base00
        (wx.stc.STC_P_STRING,         '#2aa198'), # cyan
        (wx.stc.STC_P_STRINGEOL,      '#657b83'), # base00
        (wx.stc.STC_P_TRIPLE,         '#dc322f'), # red
        (wx.stc.STC_P_TRIPLEDOUBLE,   '#268bd2'), # blue
        (wx.stc.STC_P_WORD,           '#cb4b16')  # green
    ],
    background='#002b36',   # base03
    header='#073642',       # base02
    foreground='#839496',   # base0
    txtbox='#073642'        # base02
)
# http://www.zovirl.com/2011/07/22/solarized_cheat_sheet/

APP_THEME = DARK_THEME

########NEW FILE########
__FILENAME__ = vol
"""
UI Panel for importing .vol CT data
"""

import os
from   math import log, ceil

import wx
import wx.lib.stattext

import  koko
from    koko.fab.asdf   import ASDF
from    koko.c.region   import Region
from    koko.c.libfab   import libfab
from    koko.glcanvas   import DragHandler
from    koko.themes     import DARK_THEME
import  koko.dialogs as dialogs

class ImportPanel(wx.Panel):
    def __init__(self, app, parent):
        wx.Panel.__init__(self,parent)

        vs = wx.BoxSizer(wx.VERTICAL)

        title = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='.vol to ASDF import'
        )
        title.header = True
        vs.Add(title, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        self.file_text = wx.StaticText(self, wx.ID_ANY, '')
        hs.Add(self.file_text, flag=wx.EXPAND, proportion=1)

        preview = wx.Button(self, label='Preview')
        preview.Bind(wx.EVT_BUTTON, self.preview)
        hs.Add(preview, flag=wx.LEFT|wx.ALIGN_CENTER, border=10, proportion=1)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        gs = wx.GridSizer(3, 2)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='File parameters'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        for t in [('X samples','ni'),('Y samples','nj'),
                ('Z samples','nk')]:
            gs.Add(
                wx.StaticText(self, wx.ID_ANY, t[0]),
                flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT|wx.EXPAND, border=10)
            txt = wx.TextCtrl(self, style=wx.NO_BORDER)
            setattr(self, t[1], txt)
            gs.Add(txt, flag=wx.TOP|wx.LEFT, border=10)
            txt.Bind(wx.EVT_TEXT, self.update_size)

        vs.Add(gs, flag=wx.EXPAND)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Import settings'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        gs = wx.GridSizer(3, 2)
        for t in [('Density threshold','density'),
                ('Voxel size (mm)','mm')]:
            gs.Add(
                wx.StaticText(self, wx.ID_ANY, t[0]),
                flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT|wx.EXPAND, border=10)
            setattr(self, t[1], wx.TextCtrl(self, style=wx.NO_BORDER))
            gs.Add(getattr(self, t[1]), flag=wx.TOP|wx.LEFT, border=10)
            if 'samples' in t[0]:
                getattr(self, t[1]).Bind(wx.EVT_TEXT, self.update_size)
        gs.Add(wx.StaticText(self, label='Close boundary'),
            flag=wx.TOP|wx.LEFT, border=10)
        self.boundary = wx.CheckBox(self)
        self.boundary.SetValue(True)
        gs.Add(self.boundary, flag=wx.TOP|wx.LEFT, border=10)
        vs.Add(gs, flag=wx.EXPAND)


        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Target region'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        hs = wx.BoxSizer()
        hs.Add(wx.StaticText(self, label='Entire region'),
                flag = wx.RIGHT, border=20, proportion=1)
        self.entire = wx.CheckBox(self)
        hs.Add(self.entire, proportion=1)
        self.entire.Bind(wx.EVT_CHECKBOX, self.edit_region)
        vs.Add(hs, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        bpanel = wx.Panel(self)
        bounds = wx.FlexGridSizer(6, 3)
        bounds.AddGrowableCol(0, 1)
        bounds.AddGrowableCol(2, 1)
        self.bounds = {}
        self.bounds_sliders = {}
        for i in ['imin','imax','jmin','jmax','kmin','kmax']:
            s = wx.Slider(bpanel, size=(100, 10), name=i)
            s.Bind(wx.EVT_SCROLL, lambda e, q=i: self.sync_text(q))
            self.bounds_sliders[i] = s
            bounds.Add(s, flag=wx.LEFT|wx.TOP, border=10)

            t = wx.TextCtrl(bpanel, style=wx.NO_BORDER)
            t.Bind(wx.EVT_TEXT, lambda e, q=i: self.sync_slider(q))
            self.bounds[i] = t
            bounds.Add(t, flag=wx.LEFT|wx.TOP, border=10)

            bounds.Add(wx.StaticText(bpanel, label=i),
                    flag=wx.TOP|wx.LEFT, border=10, proportion=1)

        bpanel.SetSizerAndFit(bounds)
        self.show_bounds = lambda b: bpanel.Show(b)
        vs.Add(bpanel)

        t = wx.lib.stattext.GenStaticText(
                self, style=wx.ALIGN_CENTER, label='Begin import'
        )
        t.header = True
        vs.Add(t, flag=wx.TOP|wx.LEFT|wx.EXPAND, border=10)

        run_button = wx.Button(self, label='Import')
        run_button.Bind(wx.EVT_BUTTON, self.run)


        vs.Add(run_button, flag=wx.TOP|wx.LEFT|wx.ALIGN_CENTER, border=10)

        self.SetSizerAndFit(vs)

    def sync_text(self, t):
        self.bounds[t].SetValue(str(self.bounds_sliders[t].GetValue()))
        koko.GLCANVAS.Refresh()

    def sync_slider(self, t):
        try:
            i = int(self.bounds[t].GetValue())
        except ValueError:
            return
        else:
            self.bounds_sliders[t].SetValue(i)
        koko.GLCANVAS.Refresh()

    class CornerDrag(DragHandler):
        """ @brief Handle to drag corner from GLCanvas
        """
        def __init__(self, corner):
            DragHandler.__init__(self)
            self.corner = corner
        def drag(self, dx, dy):
            proj = self.deproject(dx, dy)
            for b, d in zip(['i','j','k'], proj):
                try:
                    new_value = (
                        int(koko.IMPORT.bounds[b+self.corner].GetValue()) +
                        int(d*10)
                    )
                except ValueError:  continue

                if self.corner == 'min':
                    min_value = 0
                    max_value = koko.IMPORT.bounds_sliders[b+'max'].GetValue() - 1
                elif self.corner == 'max':
                    min_value = koko.IMPORT.bounds_sliders[b+'min'].GetValue() + 1
                    max_value = koko.IMPORT.bounds_sliders[b+'max'].GetMax()
                if new_value < min_value:   new_value = min_value
                if new_value > max_value:   new_value = max_value
                koko.IMPORT.bounds[b+self.corner].SetValue(str(new_value))
                koko.IMPORT.sync_slider(b+self.corner)

    def top_drag(self):
        return self.CornerDrag('max')
    def bottom_drag(self):
        return self.CornerDrag('min')


    def update_size(self, evt):
        for a in 'ijk':
            try:                i = int(getattr(self, 'n'+a).GetValue())
            except ValueError:  continue
            self.bounds_sliders[a+'min'].SetMax(max(0,i-1))
            self.bounds_sliders[a+'max'].SetMax(max(0,i-1))
            self.sync_text(a+'min')
            self.sync_text(a+'max')


    def set_target(self, directory, filename):
        self.directory = directory
        self.filename = os.path.join(directory, filename)
        self.file_text.SetLabel("File: %s" % filename)
        self.entire.SetValue(True)
        self.edit_region()

    def edit_region(self, event=None):
        if self.entire.IsChecked():
            self.show_bounds(False)
        else:
            self.show_bounds(True)
            for a in 'ijk':
                self.bounds_sliders[a+'min'].SetValue(0)
                self.bounds_sliders[a+'max'].SetValue(
                    self.bounds_sliders[a+'max'].GetMax()
                )
                self.sync_text(a+'min')
                self.sync_text(a+'max')
        koko.FRAME.Layout()
        koko.GLCANVAS.Refresh()


    def clear(self):
        self.Hide()
        koko.FRAME.Layout()
        koko.FRAME.Refresh()

    def get_params(self, show_error=True, get_bounds=True):
        try:
            ni, nj, nk = map(
                lambda d: int(d.GetValue()),
                [self.ni, self.nj, self.nk]
            )
        except ValueError:
            if show_error:   dialogs.error('Invalid sample count.')
            return

        size = os.path.getsize(self.filename)
        if size != ni*nj*nk*4:
            if show_error:
                dialogs.error('File size does not match provided dimensions.')
            return

        try:
            density = float(self.density.GetValue())
        except ValueError:
            if show_error:
                dialogs.error('Invalid density value (must be a floating-point number)')
            return

        try:
           mm = float(self.mm.GetValue())
        except ValueError:
            if show_error:
                dialogs.error('Invalid voxel size (must be a floating-point number)')
            return

        close_boundary = self.boundary.IsChecked()
        params = {'ni': ni, 'nj': nj, 'nk': nk,
                'density': density, 'mm': mm,
                'close_boundary':close_boundary}

        if get_bounds is False: return params

        if self.entire.IsChecked():
            params.update({
                'imin': 0, 'imax': ni-1,
                'jmin': 0, 'jmax': nj-1,
                'kmin': 0, 'kmax': nk-1
            })
        else:
            for c in ['imin','jmin','kmin','imax','jmax','kmax']:
                try:
                    params[c] = int(self.bounds[c].GetValue())
                except ValueError:
                    if show_error:
                        dialogs.error('Invalid parameter for %s' % c)
                    return
        for a in 'ijk':
            if params[a+'min'] >= params[a+'max']:
                if show_error:
                    dialogs.error('%smin cannot be larger than %smax' % (a,a))
                return

        return params

    def preview(self, event):
        """ @brief Load a downsampled version of the full ASDF
        """
        params = self.get_params(get_bounds=False)
        if params is None:  return
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        voxels = ni * nj * nk

        shift = int(ceil(log(voxels / 128.**3, 8)))
        full = Region(
            (0, 0, 0), (ni-1, nj-1, nk-1), 1, dummy=True
        )
        libfab.build_arrays(
            full, 0, 0, 0, ni*mm, nj*mm, nk*mm
        )
        full.free_arrays = True

        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, shift, density,
                True, close_boundary
            )
        )
        mesh = asdf.triangulate()

        koko.FRAME.get_menu('View', '3D').Check(True)
        koko.APP.render_mode('3D')
        koko.GLCANVAS.load_mesh(mesh)
        koko.GLCANVAS.snap = True


    def bounding_cube(self):
        if not self.IsShown() or self.entire.IsChecked():   return
        params = self.get_params(show_error=False)
        if params is None:  return

        for p in params:    exec('{0} = params["{0}"]'.format(p))
        return (imin*mm, imax*mm, jmin*mm, jmax*mm, kmin*mm, kmax*mm)

    def run(self, event):
        params = self.get_params()
        for p in params:    exec('{0} = params["{0}"]'.format(p))

        full = Region(
            (imin, jmin, kmin),
            (imax, jmax, kmax),
            1, dummy=True
        )
        libfab.build_arrays(
            full, imin*mm, jmin*mm, kmin*mm, (imax+1)*mm, (jmax+1)*mm, (kmax+1)*mm
        )
        # Position the lower corner based on imin, jmin, kmin
        full.imin = imin
        full.jmin = jmin
        full.kmin = kmin
        full.free_arrays = True

        koko.FRAME.status = 'Importing ASDF'
        wx.Yield()

        asdf = ASDF(
            libfab.import_vol_region(
                self.filename, ni, nj, nk, full, 0, density,
                True, close_boundary
            )
        )

        koko.FRAME.status = 'Triangulating'
        wx.Yield()

        mesh = asdf.triangulate()
        koko.FRAME.get_menu('View', '3D').Check(True)
        koko.APP.render_mode('3D')
        koko.GLCANVAS.load_mesh(mesh)
        koko.GLCANVAS.snap = True
        koko.FAB.set_input(asdf)

        koko.FRAME.status = ''
        koko.APP.mode = 'asdf'
        koko.APP.filename = None
        koko.APP.savepoint(False)

########NEW FILE########
__FILENAME__ = make_app
#!/usr/bin/env python
"""
This is a setup.py script generated by py2applet

Usage:
    python setup.py py2app
"""

from setuptools import setup
import shutil
import os
import stat
import subprocess
import glob

# Import the make_icon module, which uses ImageMagick and png2icns
# to make an application icon
if (not os.path.isfile('ko.icns') or
        os.path.getctime('ko.icns') < os.path.getctime('make_icon.py')):
    print "Generating icon using ImageMagick and png2icns"
    import make_icon

# Trick to make this run properly
import sys
sys.argv += ['py2app']

subprocess.call(['make'], cwd='../..')

try:    shutil.rmtree('build')
except OSError: pass

try:    shutil.rmtree('koko')
except OSError: pass

try:    os.remove('kokopelli.py')
except OSError: pass

try:    shutil.rmtree('kokopelli.app')
except OSError: pass

try:    shutil.rmtree('examples')
except OSError: pass

# Modify a line in __init__.py to store current hash
git_hash = subprocess.check_output(
    "git log --pretty=format:'%h' -n 1".split(' '))[1:-1]
if 'working directory clean' not in subprocess.check_output(['git','status']):
    git_hash += '+'

# This is the pythons script that we're bundling into an application.
shutil.copy('../../kokopelli','kokopelli.py')
shutil.copytree('../../koko','koko')

with open('koko/__init__.py', 'r') as f:
    lines = f.readlines()

with open('koko/__init__.py', 'w') as f:
    for L in lines:
        if 'HASH = None' in L:
            f.write("HASH = '%s'\n" % git_hash)
        else:
            f.write(L)


# Setup details for py2app
APP = ['kokopelli.py']
DATA_FILES = glob.glob('../../koko/lib/*.py')

OPTIONS = {'argv_emulation': True,
           'iconfile':'ko.icns'}

# Run py2app to bundle everything.
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

# Copy libtree
shutil.copy('../../libfab/libfab.dylib',
            'dist/kokopelli.app/Contents/Frameworks/libfab.dylib')
shutil.copy('/usr/local/lib/libpng.dylib',
            'dist/kokopelli.app/Contents/Frameworks/libpng.dylib')

# Copy the readme and examples into the distribution directory, then zip it up
shutil.rmtree('build')
shutil.rmtree('koko')
shutil.os.remove('kokopelli.py')

shutil.move('dist/kokopelli.app', '.')
shutil.rmtree('dist')

shutil.copytree('../../examples', './examples')
subprocess.call(
    'tar -cvzf kokopelli.tar.gz README kokopelli.app examples'.split(' ')
)
shutil.rmtree('examples')

if 'mkeeter' in subprocess.check_output('whoami') and git_hash[-1] != '+':
    print "Uploading to mattkeeter.com (Ctrl+C to cancel)"
    subprocess.call(
        'scp kokopelli.tar.gz mkeeter@mattkeeter.com:mattkeeter.com/projects/kokopelli/kokopelli.tar.gz'.split(' ')
    )

########NEW FILE########
__FILENAME__ = make_icon
#!/usr/bin/env python

import subprocess
import sys
import os
import shutil

def convert(args):
    subprocess.call('convert ' + args.replace('\n',' '), shell=True)

def progress(i, j, t=4):
    print '\r' + ' '*t + '[' + '|'*i + '-'*(j-i) + ']',
    sys.stdout.flush()

def gen(side, indent=4):
    black = '-size %{0}x{0} canvas:black'.format(side)
    blank = black + ' -alpha transparent'.format(side)

    progress(0,10,indent)
    convert(blank + '''
        -fill black -draw "roundrectangle {0},{0} {1},{1} {2},{2}"
        -channel RGBA -gaussian-blur 0x{3} shadow.png'''.format(
            side/20, side - side/20, side/40, side/50
        )
    )

    progress(1,10,indent)
    convert(black + """
        -fill white -draw "roundrectangle {0},{0} {1},{1} {2},{2}" mask.png
        """.format(
            side/20, side - side/20, side/40
        )
    )


    progress(2,10,indent)
    convert('''
        -size {0}x{0} radial-gradient: -crop {1}x{1}+{1}+0
        -level 19.5%,20% -negate gradient.png'''.format(
            side*4, side
        )
    )

    progress(3,10,indent)
    convert('''
        gradient.png mask.png -alpha Off -compose Multiply -composite
        gradient.png
    ''')

    progress(4,10,indent)
    convert('''
        gradient.png +clone -compose CopyOpacity -composite gradient.png
    ''')
    convert('''
        gradient.png -fill "rgb(88,110,117)" -colorize 100%
        -compose CopyOpacity gradient.png -composite gradient.png
    ''')

    progress(5,10,indent)
    convert(black + '''
        -fill "rgb(240,240,240)" -font {3} -pointsize {0}
        -annotate +{1}+{2} "ko" text.png'''.format(
            side*0.7, side*0.15, side*0.75, 'Myriad-Pro-Bold-SemiCondensed'
        )
    )

    progress(6,10,indent)
    convert('''text.png
        -motion-blur 0x{0}
        -motion-blur 0x{0}+-90
        -motion-blur 0x{0}+-45
        -brightness-contrast 40
        text.png
        -alpha Off -compose CopyOpacity -composite text.png'''.format(
            side/140.
        )
    )

    progress(7,10,indent)
    convert(blank + """
        -fill "rgb(0,43,54)" -draw "roundrectangle {0},{0} {1},{1} {2},{2}"
        base.png""".format(
            side/20, side - side/20, side/40
        )
    )

    progress(9,10,indent)
    convert('''
        base.png gradient.png -composite base.png
    ''')

    progress(8,10,indent)
    convert('''shadow.png base.png -composite text.png -composite icon.png''')

    progress(10,10,indent)
    shutil.copy('icon.png', 'icon%i.png' % side)

    for img in ['icon', 'gradient', 'text', 'base', 'mask', 'shadow']:
        os.remove('%s.png' % img)

if len(sys.argv) < 2:
    sizes = (16, 32, 128, 256, 512)
    for i in sizes:
        print '%i:' % i
        gen(i)
        print ''
    subprocess.call(
        ['png2icns', 'ko.icns'] +
        ['icon%i.png' % i for i in sizes[::-1]]
    )
    subprocess.call(['rm'] + ['icon%i.png' % i for i in sizes])

else:
    gen(int(sys.argv[1]), indent=0)

########NEW FILE########
__FILENAME__ = doxypy
#!/Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python

__applicationName__ = "doxypy"
__blurb__ = """
doxypy is an input filter for Doxygen. It preprocesses python
files so that docstrings of classes and functions are reformatted
into Doxygen-conform documentation blocks.
"""

__doc__ = __blurb__ + \
"""
In order to make Doxygen preprocess files through doxypy, simply
add the following lines to your Doxyfile:
	FILTER_SOURCE_FILES = YES
	INPUT_FILTER = "python /path/to/doxypy.py"
"""

__version__ = "0.4.2"
__date__ = "14th October 2009"
__website__ = "http://code.foosel.org/doxypy"

__author__ = (
	"Philippe 'demod' Neumann (doxypy at demod dot org)",
	"Gina 'foosel' Haeussge (gina at foosel dot net)"
)

__licenseName__ = "GPL v2"
__license__ = """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import re

from optparse import OptionParser, OptionGroup

class FSM(object):
	"""Implements a finite state machine.
	
	Transitions are given as 4-tuples, consisting of an origin state, a target
	state, a condition for the transition (given as a reference to a function
	which gets called with a given piece of input) and a pointer to a function
	to be called upon the execution of the given transition.
	"""
	
	"""
	@var transitions holds the transitions
	@var current_state holds the current state
	@var current_input holds the current input
	@var current_transition hold the currently active transition
	"""
	
	def __init__(self, start_state=None, transitions=[]):
		self.transitions = transitions
		self.current_state = start_state
		self.current_input = None
		self.current_transition = None
		
	def setStartState(self, state):
		self.current_state = state

	def addTransition(self, from_state, to_state, condition, callback):
		self.transitions.append([from_state, to_state, condition, callback])
		
	def makeTransition(self, input):
		"""Makes a transition based on the given input.
		
		@param	input	input to parse by the FSM
		"""
		for transition in self.transitions:
			[from_state, to_state, condition, callback] = transition
			if from_state == self.current_state:
				match = condition(input)
				if match:
					self.current_state = to_state
					self.current_input = input
					self.current_transition = transition
					if options.debug:
						print >>sys.stderr, "# FSM: executing (%s -> %s) for line '%s'" % (from_state, to_state, input)
					callback(match)
					return

class Doxypy(object):
	def __init__(self):
		string_prefixes = "[uU]?[rR]?"
		
		self.start_single_comment_re = re.compile("^\s*%s(''')" % string_prefixes)
		self.end_single_comment_re = re.compile("(''')\s*$")
		
		self.start_double_comment_re = re.compile("^\s*%s(\"\"\")" % string_prefixes)
		self.end_double_comment_re = re.compile("(\"\"\")\s*$")
		
		self.single_comment_re = re.compile("^\s*%s(''').*(''')\s*$" % string_prefixes)
		self.double_comment_re = re.compile("^\s*%s(\"\"\").*(\"\"\")\s*$" % string_prefixes)
		
		self.defclass_re = re.compile("^(\s*)(def .+:|class .+:)")
		self.empty_re = re.compile("^\s*$")
		self.hashline_re = re.compile("^\s*#.*$")
		self.importline_re = re.compile("^\s*(import |from .+ import)")

		self.multiline_defclass_start_re = re.compile("^(\s*)(def|class)(\s.*)?$")
		self.multiline_defclass_end_re = re.compile(":\s*$")
		
		## Transition list format
		#  ["FROM", "TO", condition, action]
		transitions = [
			### FILEHEAD
			
			# single line comments
			["FILEHEAD", "FILEHEAD", self.single_comment_re.search, self.appendCommentLine],
			["FILEHEAD", "FILEHEAD", self.double_comment_re.search, self.appendCommentLine],
			
			# multiline comments
			["FILEHEAD", "FILEHEAD_COMMENT_SINGLE", self.start_single_comment_re.search, self.appendCommentLine],
			["FILEHEAD_COMMENT_SINGLE", "FILEHEAD", self.end_single_comment_re.search, self.appendCommentLine],
			["FILEHEAD_COMMENT_SINGLE", "FILEHEAD_COMMENT_SINGLE", self.catchall, self.appendCommentLine],
			["FILEHEAD", "FILEHEAD_COMMENT_DOUBLE", self.start_double_comment_re.search, self.appendCommentLine],
			["FILEHEAD_COMMENT_DOUBLE", "FILEHEAD", self.end_double_comment_re.search, self.appendCommentLine],
			["FILEHEAD_COMMENT_DOUBLE", "FILEHEAD_COMMENT_DOUBLE", self.catchall, self.appendCommentLine],
			
			# other lines
			["FILEHEAD", "FILEHEAD", self.empty_re.search, self.appendFileheadLine],
			["FILEHEAD", "FILEHEAD", self.hashline_re.search, self.appendFileheadLine],
			["FILEHEAD", "FILEHEAD", self.importline_re.search, self.appendFileheadLine],
			["FILEHEAD", "DEFCLASS", self.defclass_re.search, self.resetCommentSearch],
			["FILEHEAD", "DEFCLASS_MULTI", self.multiline_defclass_start_re.search, self.resetCommentSearch],			
			["FILEHEAD", "DEFCLASS_BODY", self.catchall, self.appendFileheadLine],

			### DEFCLASS
			
			# single line comments
			["DEFCLASS", "DEFCLASS_BODY", self.single_comment_re.search, self.appendCommentLine],
			["DEFCLASS", "DEFCLASS_BODY", self.double_comment_re.search, self.appendCommentLine],
			
			# multiline comments
			["DEFCLASS", "COMMENT_SINGLE", self.start_single_comment_re.search, self.appendCommentLine],
			["COMMENT_SINGLE", "DEFCLASS_BODY", self.end_single_comment_re.search, self.appendCommentLine],
			["COMMENT_SINGLE", "COMMENT_SINGLE", self.catchall, self.appendCommentLine],
			["DEFCLASS", "COMMENT_DOUBLE", self.start_double_comment_re.search, self.appendCommentLine],
			["COMMENT_DOUBLE", "DEFCLASS_BODY", self.end_double_comment_re.search, self.appendCommentLine],
			["COMMENT_DOUBLE", "COMMENT_DOUBLE", self.catchall, self.appendCommentLine],

			# other lines
			["DEFCLASS", "DEFCLASS", self.empty_re.search, self.appendDefclassLine],
			["DEFCLASS", "DEFCLASS", self.defclass_re.search, self.resetCommentSearch],
			["DEFCLASS", "DEFCLASS_MULTI", self.multiline_defclass_start_re.search, self.resetCommentSearch],
			["DEFCLASS", "DEFCLASS_BODY", self.catchall, self.stopCommentSearch],
			
			### DEFCLASS_BODY
			
			["DEFCLASS_BODY", "DEFCLASS", self.defclass_re.search, self.startCommentSearch],
			["DEFCLASS_BODY", "DEFCLASS_MULTI", self.multiline_defclass_start_re.search, self.startCommentSearch],
			["DEFCLASS_BODY", "DEFCLASS_BODY", self.catchall, self.appendNormalLine],

			### DEFCLASS_MULTI
			["DEFCLASS_MULTI", "DEFCLASS", self.multiline_defclass_end_re.search, self.appendDefclassLine],
			["DEFCLASS_MULTI", "DEFCLASS_MULTI", self.catchall, self.appendDefclassLine],
		]
		
		self.fsm = FSM("FILEHEAD", transitions)
		self.outstream = sys.stdout
		
		self.output = []
		self.comment = []
		self.filehead = []
		self.defclass = []
		self.indent = ""

	def __closeComment(self):
		"""Appends any open comment block and triggering block to the output."""
		
		if options.autobrief:
			if len(self.comment) == 1 \
			or (len(self.comment) > 2 and self.comment[1].strip() == ''):
				self.comment[0] = self.__docstringSummaryToBrief(self.comment[0])
			
		if self.comment:
			block = self.makeCommentBlock()
			self.output.extend(block)
			
		if self.defclass:
			self.output.extend(self.defclass)

	def __docstringSummaryToBrief(self, line):
		"""Adds \\brief to the docstrings summary line.
		
		A \\brief is prepended, provided no other doxygen command is at the
		start of the line.
		"""
		stripped = line.strip()
		if stripped and not stripped[0] in ('@', '\\'):
			return "\\brief " + line
		else:
			return line
	
	def __flushBuffer(self):
		"""Flushes the current outputbuffer to the outstream."""
		if self.output:
			try:
				if options.debug:
					print >>sys.stderr, "# OUTPUT: ", self.output
				print >>self.outstream, "\n".join(self.output)
				self.outstream.flush()
			except IOError:
				# Fix for FS#33. Catches "broken pipe" when doxygen closes
				# stdout prematurely upon usage of INPUT_FILTER, INLINE_SOURCES
				# and FILTER_SOURCE_FILES.
				pass
		self.output = []

	def catchall(self, input):
		"""The catchall-condition, always returns true."""
		return True
	
	def resetCommentSearch(self, match):
		"""Restarts a new comment search for a different triggering line.
		
		Closes the current commentblock and starts a new comment search.
		"""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: resetCommentSearch"
		self.__closeComment()
		self.startCommentSearch(match)
	
	def startCommentSearch(self, match):
		"""Starts a new comment search.
		
		Saves the triggering line, resets the current comment and saves
		the current indentation.
		"""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: startCommentSearch"
		self.defclass = [self.fsm.current_input]
		self.comment = []
		self.indent = match.group(1)
	
	def stopCommentSearch(self, match):
		"""Stops a comment search.
		
		Closes the current commentblock, resets	the triggering line and
		appends the current line to the output.
		"""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: stopCommentSearch"
		self.__closeComment()
		
		self.defclass = []
		self.output.append(self.fsm.current_input)
	
	def appendFileheadLine(self, match):
		"""Appends a line in the FILEHEAD state.
		
		Closes the open comment	block, resets it and appends the current line.
		"""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: appendFileheadLine"
		self.__closeComment()
		self.comment = []
		self.output.append(self.fsm.current_input)

	def appendCommentLine(self, match):
		"""Appends a comment line.
		
		The comment delimiter is removed from multiline start and ends as
		well as singleline comments.
		"""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: appendCommentLine"
		(from_state, to_state, condition, callback) = self.fsm.current_transition
		
		# single line comment
		if (from_state == "DEFCLASS" and to_state == "DEFCLASS_BODY") \
		or (from_state == "FILEHEAD" and to_state == "FILEHEAD"):
			# remove comment delimiter from begin and end of the line
			activeCommentDelim = match.group(1)
			line = self.fsm.current_input
			self.comment.append(line[line.find(activeCommentDelim)+len(activeCommentDelim):line.rfind(activeCommentDelim)])

			if (to_state == "DEFCLASS_BODY"):
				self.__closeComment()
				self.defclass = []
		# multiline start
		elif from_state == "DEFCLASS" or from_state == "FILEHEAD":
			# remove comment delimiter from begin of the line
			activeCommentDelim = match.group(1)
			line = self.fsm.current_input
			self.comment.append(line[line.find(activeCommentDelim)+len(activeCommentDelim):])
		# multiline end
		elif to_state == "DEFCLASS_BODY" or to_state == "FILEHEAD":
			# remove comment delimiter from end of the line
			activeCommentDelim = match.group(1)
			line = self.fsm.current_input
			self.comment.append(line[0:line.rfind(activeCommentDelim)])
			if (to_state == "DEFCLASS_BODY"):
				self.__closeComment()
				self.defclass = []
		# in multiline comment
		else:
			# just append the comment line
			self.comment.append(self.fsm.current_input)
	
	def appendNormalLine(self, match):
		"""Appends a line to the output."""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: appendNormalLine"
		self.output.append(self.fsm.current_input)
		
	def appendDefclassLine(self, match):
		"""Appends a line to the triggering block."""
		if options.debug:
			print >>sys.stderr, "# CALLBACK: appendDefclassLine"
		self.defclass.append(self.fsm.current_input)
	
	def makeCommentBlock(self):
		"""Indents the current comment block with respect to the current
		indentation level.

		@returns a list of indented comment lines
		"""
		doxyStart = "##"
		commentLines = self.comment
		
		commentLines = map(lambda x: "%s# %s" % (self.indent, x), commentLines)
		l = [self.indent + doxyStart]
		l.extend(commentLines)
			
		return l
	
	def parse(self, input):
		"""Parses a python file given as input string and returns the doxygen-
		compatible representation.
		
		@param	input	the python code to parse
		@returns the modified python code
		"""
		lines = input.split("\n")
		
		for line in lines:
			self.fsm.makeTransition(line)
			
		if self.fsm.current_state == "DEFCLASS":
			self.__closeComment()
		
		return "\n".join(self.output)
	
	def parseFile(self, filename):
		"""Parses a python file given as input string and returns the doxygen-
		compatible representation.
		
		@param	input	the python code to parse
		@returns the modified python code
		"""
		f = open(filename, 'r')
		
		for line in f:
			self.parseLine(line.rstrip('\r\n'))
		if self.fsm.current_state == "DEFCLASS":
			self.__closeComment()
			self.__flushBuffer()
		f.close()
	
	def parseLine(self, line):
		"""Parse one line of python and flush the resulting output to the
		outstream.
		
		@param	line	the python code line to parse
		"""
		self.fsm.makeTransition(line)
		self.__flushBuffer()
	
def optParse():
	"""Parses commandline options."""
	parser = OptionParser(prog=__applicationName__, version="%prog " + __version__)
	
	parser.set_usage("%prog [options] filename")
	parser.add_option("--autobrief",
		action="store_true", dest="autobrief",
		help="use the docstring summary line as \\brief description"
	)
	parser.add_option("--debug",
		action="store_true", dest="debug",
		help="enable debug output on stderr"
	)
	
	## parse options
	global options
	(options, filename) = parser.parse_args()
	
	if not filename:
		print >>sys.stderr, "No filename given."
		sys.exit(-1)
	
	return filename[0]

def main():
	"""Starts the parser on the file given by the filename as the first
	argument on the commandline.
	"""
	filename = optParse()
	fsm = Doxypy()
	fsm.parseFile(filename)

if __name__ == "__main__":
	main()

########NEW FILE########
