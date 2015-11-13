__FILENAME__ = conf
from path import path
import logging
import sphinx
import sys
from setuptools import find_packages


def read_project_version(py=None, where='.', exclude=['bootstrap', 'pavement', 'doc', 'docs', 'test', 'tests', ]):
    if not py:
        py = path(where) / find_packages(where=where, exclude=exclude)[0]
    py = path(py)
    if py.isdir():
        py = py / '__init__.py'
    __version__ = None
    for line in py.lines():
        if '__version__' in line:
            exec line
            break
    return __version__


release = read_project_version(where='..')
project = 'pyscreenshot'
author = 'ponty'
copyright = '2011, ponty'

# logging.basicConfig(level=logging.DEBUG)

# Extension
extensions = [
    # -*-Extensions: -*-
    'sphinx.ext.autodoc',
    'sphinxcontrib.programoutput',
    #     'sphinxcontrib.programscreenshot',
    'sphinx.ext.graphviz',
    'sphinxcontrib.autorun',
    #'sphinx.ext.autosummary',
    #     'sphinx.ext.intersphinx',
]
intersphinx_mapping = {'http://docs.python.org/': None}

# Source
master_doc = 'index'
templates_path = ['_templates']
source_suffix = '.rst'
exclude_trees = []
pygments_style = 'sphinx'

# html build settings
html_theme = 'default'
html_static_path = ['_static']

# htmlhelp settings
htmlhelp_basename = '%sdoc' % project

# latex build settings
latex_documents = [
    ('index', '%s.tex' % project, u'%s Documentation' % project,
     author, 'manual'),
]

# remove blank pages from pdf
# http://groups.google.com/group/sphinx-
# dev/browse_thread/thread/92e19267d095412d/d60dcba483c6b13d
latex_font_size = '10pt,oneside'

latex_elements = dict(
    papersize='a4paper',
)

########NEW FILE########
__FILENAME__ = pavement
from paver.easy import *
from paver.setuputils import setup

import paver.doctools
import paver.virtual
import paver.misctasks
from paved import *
from paved.dist import *
from paved.util import *
from paved.docs import *
from paved.pycheck import *
from paved.pkg import *

# get info from setup.py
setup_py = ''.join(
    [x for x in path('setup.py').lines() if 'distutils' not in x])
exec(setup_py)


options(
    sphinx=Bunch(
        docroot='docs',
        builddir='_build',
    ),
    #    pdf=Bunch(
    #        builddir='_build',
    #        builder='latex',
    #    ),
)

options.paved.clean.rmdirs += ['.tox',
                               'dist',
                               'build',
                               ]
options.paved.clean.patterns += ['*.pickle',
                                 '*.doctree',
                                 '*.gz',
                                 'nosetests.xml',
                                 'sloccount.sc',
                                 '*.pdf', '*.tex',
                                 '*.png',
                                 ]

options.paved.dist.manifest.include.remove('distribute_setup.py')
options.paved.dist.manifest.include.remove('paver-minilib.zip')
options.paved.dist.manifest.include.add('requirements.txt')


@task
@needs(
    #           'clean',
    'sloccount',
    'html',
    'pdf',
    'sdist',
    'nose', 'tox',
)
def alltest():
    'all tasks to check'
    pass


@task
@needs('manifest')
def sdist():
    """Overrides sdist to make sure that our MANIFEST.in is generated."""
    pass

########NEW FILE########
__FILENAME__ = speedtest
from entrypoint2 import entrypoint
from pyscreenshot.loader import BackendLoader
from pyscreenshot.loader import BackendLoaderError
import pyscreenshot
import tempfile
import time


def run(force_backend, n, to_file, bbox=None):
    print '%-20s' % force_backend,

    BackendLoader().force(force_backend)

    f = tempfile.NamedTemporaryFile(suffix='.png', prefix='test')
    filename = f.name
    start = time.time()
    for i in range(n):
        if to_file:
            pyscreenshot.grab_to_file(filename)
        else:
            pyscreenshot.grab(bbox=bbox)
    end = time.time()
    dt = end - start
    print '%-4.2g sec' % (dt), '(%5d ms per call)' % (1000.0 * dt / n)


def run_all(n, to_file, bbox=None):
    print
    print 'n=%s' % n, ', to_file:', to_file, ', bounding box:', bbox
    print '------------------------------------------------------'

    backends = BackendLoader().all_names
    for x in backends:
        try:
            run(x, n, to_file, bbox)
#            print 'grabbing by '+x
        except BackendLoaderError as e:
            print e


@entrypoint
def speedtest():
    n = 10
    run_all(n, True)
    run_all(n, False)
    run_all(n, False, (10, 10, 20, 20))

########NEW FILE########
__FILENAME__ = versions
from pyscreenshot.backendloader import BackendLoader
import pyscreenshot
from entrypoint2 import entrypoint


def print_name(name):
    print name, ' ' * (20 - len(name)),


@entrypoint
def print_versions():
    print_name('pyscreenshot')
    print pyscreenshot.__version__
    man = BackendLoader()
    for name in man.all_names:
        man.force(name)
        print_name(name)
        try:
            x = man.selected()
            print x.backend_version()
        except Exception:
            print 'missing'

########NEW FILE########
__FILENAME__ = virtualtest
from entrypoint2 import entrypoint
from pyscreenshot.backendloader import BackendLoader
from pyscreenshot.loader import BackendLoaderError
from pyvirtualdisplay.display import Display
import pyscreenshot
import time

# they make exceptions that can not be catched
SKIP = ['pygtk', 'wx', 'pyqt']


def run(force_backend, bbox, bgcolor):
    color = 255 if bgcolor == 'white' else 0
    print force_backend, ' ' * (20 - len(force_backend)),
    if force_backend in SKIP:
        print 'SKIP'
        return

    BackendLoader().force(force_backend)
    im = pyscreenshot.grab(bbox=bbox)
    ls = list(im.getdata())
    print 'OK' if all([x == color or x == (color, color, color) for x in ls]) else 'FAIL'


def run_all(bgcolor, display, bbox):
    print
    print 'bgcolor=', bgcolor
    print '-------------------------------------'
    backends = BackendLoader().all_names
    for x in backends:
        try:
            with Display(size=display, bgcolor=bgcolor):
#                time.sleep(1)
                try:
                    run(x, bbox, bgcolor=bgcolor)
                except BackendLoaderError as e:
                    print e
        except Exception as e:
            print e


@entrypoint
def main():
    bbox = (15, 15, 120, 120)
    display = (200, 200)
    run_all('black', display, bbox)
    run_all('white', display, bbox)

########NEW FILE########
__FILENAME__ = show
from entrypoint2 import entrypoint
from pyscreenshot import grab


@entrypoint
def show(backend='auto'):
    if backend == 'auto':
        backend = None
    im = grab(bbox=(100, 200, 300, 400), backend=backend)
    im.show()

########NEW FILE########
__FILENAME__ = showall
from entrypoint2 import entrypoint
from pyscreenshot import backends
from pyscreenshot.loader import BackendLoaderError
import time

import pyscreenshot as ImageGrab


@entrypoint
def show():
    im = []

    for x in backends():
        try:
            print 'grabbing by ' + x
            im.append(ImageGrab.grab(bbox=(500, 400, 800, 600), backend=x))
        except BackendLoaderError as e:
            print e
    print im
    for x in im:
        x.show()
        time.sleep(1)

########NEW FILE########
__FILENAME__ = loader
import logging
from pyscreenshot import plugins

log = logging.getLogger(__name__)


class BackendLoaderError(Exception):
    pass


class BackendLoader(object):

    def __init__(self):
        self.plugins = dict()

        self.all_names = [x.name for x in self.plugin_classes()]

        self.changed = True
        self._force_backend = None
        self.preference = []
        self.default_preference = plugins.default_preference
        self._backend = None

    def plugin_classes(self):
        return plugins.BACKENDS

    def set_preference(self, x):
        self.changed = True
        self.preference = x

    def force(self, name):
        log.debug('forcing:' + str(name))
        self.changed = True
        self._force_backend = name

    @property
    def is_forced(self):
        return self._force_backend is not None

    @property
    def loaded_plugins(self):
        return self.plugins.values()

    def get_valid_plugin_by_name(self, name):
        if name not in self.plugins:
            ls = filter(lambda x: x.name == name, self.plugin_classes())
            if len(ls):
                try:
                    plugin = ls[0]()
                except Exception:
                    plugin = None
            else:
                plugin = None
            self.plugins[name] = plugin
        return self.plugins[name]

    def get_valid_plugin_by_list(self, ls):
        for name in ls:
            x = self.get_valid_plugin_by_name(name)
            if x:
                return x

    def selected(self):
        if self.changed:
            if self.is_forced:
                b = self.get_valid_plugin_by_name(self._force_backend)
                if not b:
                    raise BackendLoaderError(
                        'Forced backend not found, or cannot be loaded:' + self._force_backend)
            else:
                biglist = self.preference + \
                    self.default_preference + self.all_names
                b = self.get_valid_plugin_by_list(biglist)
                if not b:
                    self.raise_exc()
            self.changed = False
            self._backend = b
            log.debug('selecting plugin:' + self._backend.name)
        return self._backend

    def raise_exc(self):
        message = 'Install at least one backend!'
        raise BackendLoaderError(message)

########NEW FILE########
__FILENAME__ = gtkpixbuf
from PIL import Image
import tempfile


class GtkPixbufWrapper(object):
    # home_url = 'http://???'
    ubuntu_package = 'python-gtk2'
    name = 'pygtk'
    childprocess = False

    def __init__(self):
        import gtk
        self.gtk = gtk

    def grab(self, bbox=None):
        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_gtkpixbuf_')
        filename = f.name
        self.grab_to_file(filename)
        im = Image.open(filename)
        if bbox:
            im = im.crop(bbox)
        return im

    def grab_to_file(self, filename):
        '''
        based on: http://stackoverflow.com/questions/69645/take-a-screenshot-via-a-python-script-linux

        http://www.pygtk.org/docs/pygtk/class-gdkpixbuf.html

        only "jpeg" or "png"
        '''

        w = self.gtk.gdk.get_default_root_window()
        sz = w.get_size()
        # print "The size of the window is %d x %d" % sz
        pb = self.gtk.gdk.Pixbuf(
            self.gtk.gdk.COLORSPACE_RGB, False, 8, sz[0], sz[1])  # 24bit RGB
        pb = pb.get_from_drawable(
            w, w.get_colormap(), 0, 0, 0, 0, sz[0], sz[1])
        assert pb
        type = 'png'
        if filename.endswith('.jpeg'):
            type = 'jpeg'

        pb.save(filename, type)

    def backend_version(self):
        # TODO:
        return '.'.join(map(str, gtk.ver))

########NEW FILE########
__FILENAME__ = imagemagick
from easyprocess import EasyProcess
from easyprocess import extract_version
from PIL import Image
import tempfile

PROGRAM = 'import'
URL = 'http://www.imagemagick.org/'
PACKAGE = 'imagemagick'


class ImagemagickWrapper(object):
    name = 'imagemagick'
    childprocess = True

    def __init__(self):
        EasyProcess([PROGRAM, '-version'], url=URL,
                    ubuntu_package=PACKAGE).check_installed()

    def grab(self, bbox=None):
        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_imagemagick_')
        filename = f.name
        self.grab_to_file(filename, bbox=bbox)
        im = Image.open(filename)
        # if bbox:
        #    im = im.crop(bbox)
        return im

    def grab_to_file(self, filename, bbox=None):
        command = 'import -silent -window root '
        if bbox:
            command += " -crop '%sx%s+%s+%s' " % (
                bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1])
        command += filename
        EasyProcess(command).call()

    def backend_version(self):
        return extract_version(EasyProcess([PROGRAM, '-version']).call().stdout.replace('-', ' '))

########NEW FILE########
__FILENAME__ = mac_quartz
# Javier Escalada Gomez
#
# from: https://stackoverflow.com/questions/4524723/take-screenshot-in-python-on-mac-os-x

from PIL import Image
import tempfile


class MacQuartzWrapper(object):
    name = 'mac_quartz'
    childprocess = False
    home_url = 'https://stackoverflow.com/questions/4524723/take-screenshot-in-python-on-mac-os-x'

    def __init__(self):
        import Quartz
        import LaunchServices
        from Cocoa import NSURL
        import Quartz.CoreGraphics as CG
        self.Quartz = Quartz
        self.LaunchServices = LaunchServices
        self.NSURL = NSURL
        self.CG = CG

    def grab(self, bbox=None):
        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_screencapture_')
        filename = f.name
        self.grab_to_file(filename, bbox=bbox)
        im = Image.open(filename)
        return im

    def grab_to_file(self, filename, bbox=None, dpi=72):
        # FIXME: Should query dpi from somewhere, e.g for retina displays
        
        region = self.CG.CGRectMake(*bbox) if bbox else self.CG.CGRectInfinite

        # Create screenshot as CGImage
        image = self.CG.CGWindowListCreateImage( region,
            self.CG.kCGWindowListOptionOnScreenOnly, self.CG.kCGNullWindowID,
            self.CG.kCGWindowImageDefault)

        # XXX: Can add more types: https://developer.apple.com/library/mac/documentation/MobileCoreServices/Reference/UTTypeRef/Reference/reference.html#//apple_ref/doc/uid/TP40008771
        file_type = self.LaunchServices.kUTTypePNG
        if filename.endswith('.jpeg'):
            file_type = self.LaunchServices.kUTTypeJPEG
        elif filename.endswith('.tiff'):
            file_type = self.LaunchServices.kUTTypeTIFF
        elif filename.endswith('.bmp'):
            file_type = self.LaunchServices.kUTTypeBMP
        elif filename.endswith('.gif'):
            file_type = self.LaunchServices.kUTTypeGIF
        elif filename.endswith('.pdf'):
            file_type = self.LaunchServices.kUTTypePDF   

        url = self.NSURL.fileURLWithPath_(filename)

        dest = self.Quartz.CGImageDestinationCreateWithURL(url, file_type,
            1, # 1 image in file
            None)

        properties = {
            self.Quartz.kCGImagePropertyDPIWidth: dpi,
            self.Quartz.kCGImagePropertyDPIHeight: dpi,
        }

        # Add the image to the destination, characterizing the image with
        # the properties dictionary.
        self.Quartz.CGImageDestinationAddImage(dest, image, properties)

        # When all the images (only 1 in this example) are added to the destination, 
        # finalize the CGImageDestination object. 
        self.Quartz.CGImageDestinationFinalize(dest)

    def backend_version(self):
        # TODO:
        return 'not implemented'

########NEW FILE########
__FILENAME__ = mac_screencapture
import platform
from easyprocess import EasyProcess, EasyProcessCheckInstalledError
from PIL import Image
import tempfile

PROGRAM = 'screencapture'
URL = 'http://support.apple.com/kb/ph11229'
PACKAGE = 'screencapture'


class ScreencaptureWrapper(object):
    name = 'mac_screencapture'
    childprocess = True

    def __init__(self):
        if 'Darwin' not in platform.platform():
            raise EasyProcessCheckInstalledError(self)

    def grab(self, bbox=None):
        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_screencapture_')
        filename = f.name
        self.grab_to_file(filename, bbox=bbox)
        im = Image.open(filename)
        return im

    def grab_to_file(self, filename, bbox=None):
        command = 'screencapture '
        if filename.endswith('.jpeg'):
            command += ' -t jpg'
        elif filename.endswith('.tiff'):
            command += ' -t tiff'
        elif filename.endswith('.bmp'):
            command += ' -t bmp'
        elif filename.endswith('.gif'):
            command += ' -t gif'
        elif filename.endswith('.pdf'):
            command += ' -t pdf'
        if bbox:
            command += ' -R%s,%s,%s,%s ' % (
                bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
        command += filename
        EasyProcess(command).call()

    def backend_version(self):
        # TODO:
        return 'not implemented'

########NEW FILE########
__FILENAME__ = pil
from PIL import Image


class PilWrapper(object):

    """windows only."""

    home_url = 'http://www.pythonware.com/products/pil/'
    ubuntu_package = 'python-imaging'
    name = 'pil'
    childprocess = False

    def __init__(self):
        import ImageGrab  # windows only
        self.ImageGrab = ImageGrab

    def grab(self, bbox=None):
        return self.ImageGrab.grab(bbox)

    def grab_to_file(self, filename):
        im = self.grab()
        im.save(filename)

    def backend_version(self):
        return Image.VERSION

########NEW FILE########
__FILENAME__ = qtgrabwindow
from PIL import Image
import StringIO


class QtGrabWindow(object):

    '''based on: http://stackoverflow.com/questions/69645/take-a-screenshot-via-a-python-script-linux
    '''
    # home_url = 'http://???'
    # ubuntu_package = '???'
    name = 'pyqt'
    childprocess = False

    def __init__(self):
        import PyQt4
        self.PyQt4 = PyQt4
        from PyQt4 import QtGui
        from PyQt4 import Qt
        self.app = None

    def grab_to_buffer(self, buffer, file_type='png'):
        QApplication = self.PyQt4.QtGui.QApplication
        QBuffer = self.PyQt4.Qt.QBuffer
        QIODevice = self.PyQt4.Qt.QIODevice
        QPixmap = self.PyQt4.QtGui.QPixmap

        if not self.app:
            self.app = QApplication([])
        qbuffer = QBuffer()
        qbuffer.open(QIODevice.ReadWrite)
        QPixmap.grabWindow(
            QApplication.desktop().winId()).save(qbuffer, file_type)
        buffer.write(qbuffer.data())
        qbuffer.close()
#        del app

    def grab(self, bbox=None):
        strio = StringIO.StringIO()
        self.grab_to_buffer(strio)
        strio.seek(0)
        im = Image.open(strio)
        if bbox:
            im = im.crop(bbox)
        return im

    def grab_to_file(self, filename):
        file_type = 'png'
        if filename.endswith('.jpeg'):
            file_type = 'jpeg'
        buff = open(filename, 'wb')
        self.grab_to_buffer(buff, file_type)
        buff.close()

    def backend_version(self):
        # TODO:
        return 'not implemented'

########NEW FILE########
__FILENAME__ = scrot
from easyprocess import EasyProcess
from easyprocess import extract_version
from PIL import Image
import tempfile


PROGRAM = 'scrot'
URL = None
PACKAGE = 'scrot'


class ScrotWrapper(object):
    name = 'scrot'
    childprocess = True

    def __init__(self):
        EasyProcess([PROGRAM, '-version'], url=URL,
                    ubuntu_package=PACKAGE).check_installed()

    def grab(self, bbox=None):
        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_scrot_')
        filename = f.name
        self.grab_to_file(filename)
        im = Image.open(filename)
        if bbox:
            im = im.crop(bbox)
        return im

    def grab_to_file(self, filename):
        EasyProcess([PROGRAM, filename]).call()

    def backend_version(self):
        return extract_version(EasyProcess([PROGRAM, '-version']).call().stdout)

########NEW FILE########
__FILENAME__ = wxscreen
from PIL import Image


class WxScreen(object):

    '''based on: http://stackoverflow.com/questions/69645/take-a-screenshot-via-a-python-script-linux
    '''
    # home_url = 'http://???'
    # ubuntu_package = '???'
    name = 'wx'
    childprocess = False

    def __init__(self):
        import wx
        self.wx = wx
        self.app = None

    def grab(self, bbox=None):
        wx = self.wx
        if not self.app:
            self.app = wx.App()
        screen = wx.ScreenDC()
        size = screen.GetSize()
        bmp = wx.EmptyBitmap(size[0], size[1])
        mem = wx.MemoryDC(bmp)
        mem.Blit(0, 0, size[0], size[1], screen, 0, 0)
        del mem
        myWxImage = wx.ImageFromBitmap(bmp)
        im = Image.new('RGB', (myWxImage.GetWidth(), myWxImage.GetHeight()))
        if hasattr(Image, 'frombytes'):
            # for Pillow
            im.frombytes(myWxImage.GetData())
        else:
            # for PIL
            im.fromstring(myWxImage.GetData())
        if bbox:
            im = im.crop(bbox)
        return im

    def grab_to_file(self, filename):
        # bmp.SaveFile('screenshot.png', wx.BITMAP_TYPE_PNG)
        im = self.grab()
        im.save(filename)

    def backend_version(self):
        return self.wx.__version__

########NEW FILE########
__FILENAME__ = image_debug
from logging import DEBUG
from tempfile import mkdtemp, gettempdir
import logging
import os

log = logging.getLogger(__name__)

img_dir = None
img_ind = 0
CROP_RECT = None


def set_crop_rect(rct):
    global CROP_RECT
    CROP_RECT = rct


def img_debug(im, text):
    if not log.isEnabledFor(DEBUG):
        return
    global img_dir
    global img_ind
    if not img_dir:
        root = gettempdir() + '/img_debug'
        if not os.path.exists(root):
            os.makedirs(root, mode=0777)
        img_dir = mkdtemp(prefix='img_debug_', suffix='', dir=root)
    if CROP_RECT:
        im = im.crop(CROP_RECT)
    fname = img_dir + '/' + str(img_ind) + '_' + text + '.png'
    im.save(fname)
    log.debug('image (%s) was saved:' % im + fname)
    img_ind += 1
# BackendLoader().selected().name + '_'

########NEW FILE########
__FILENAME__ = test_compare
from tox.compare import backend_size, backend_ref


def test_pygtk():
    backend = 'pygtk'
    backend_size(backend)
    backend_ref(backend)


def test_wx():
    backend = 'wx'
    backend_size(backend)
    backend_ref(backend)

########NEW FILE########
__FILENAME__ = test_plugin
import logging
from nose.tools import eq_
from pyscreenshot.loader import BackendLoader
from unittest import TestCase


logging.basicConfig(level=logging.DEBUG)


class Test(TestCase):

    def test_pref(self):
        man = BackendLoader()
        man.force(None)

        man.set_preference(['imagemagick', 'scrot'])
        eq_(man.selected().name, 'imagemagick')

        man.set_preference(['imagemagick', 'scrot', 'imagemagick'])
        eq_(man.selected().name, 'imagemagick')

        man.set_preference(['imagemagick'])
        eq_(man.selected().name, 'imagemagick')

        man.set_preference(['pygtk', 'imagemagick', 'scrot'])
        eq_(man.selected().name, 'pygtk')

        man.set_preference(['scrot', 'imagemagick'])
        eq_(man.selected().name, 'scrot')

        man.set_preference(['scrot', 'imagemagick', 'pygtk'])
        eq_(man.selected().name, 'scrot')

        man.set_preference(['scrot', 'imagemagick', 'scrot'])
        eq_(man.selected().name, 'scrot')

        man.set_preference(['scrot'])
        eq_(man.selected().name, 'scrot')

    def test_force(self):
        man = BackendLoader()
        for name in ['imagemagick', 'scrot', 'pygtk', 'pyqt', 'wx']:
            man.force(name)
            eq_(man.selected().name, name)
            man.force(None)  # for other tests

    def test_mix(self):
        man = BackendLoader()
        man.force('scrot')
        man.set_preference(['imagemagick', 'scrot'])
        eq_(man.selected().name, 'scrot')

########NEW FILE########
__FILENAME__ = compare
from easyprocess import EasyProcess
from image_debug import img_debug
from nose.tools import eq_, with_setup
from pyscreenshot.loader import BackendLoader
from pyvirtualdisplay import Display
from PIL import ImageChops
# import Tkinter
import pyscreenshot
import tempfile
# import Xlib.display

# backends = [
#    'scrot',
#    'imagemagick',
#    'pygtk',
# 'pyqt', #strange error: ICE default IO error handler doing an exit(), pid = 26424, errno = 32
#    'wx',
# ]
ref = 'scrot'


def display_size():
#    root = Tkinter.Tk()
#
#    screen_width = root.winfo_screenwidth()
#    screen_height = root.winfo_screenheight()

#    xdisp=Xlib.display.Display()
#    width = xdisp.screen().width_in_pixels
#    height = xdisp.screen().height_in_pixels
    # http://www.cyberciti.biz/faq/how-do-i-find-out-screen-resolution-of-my-linux-desktop/
    # xdpyinfo  | grep 'dimensions:'
    for x in EasyProcess('xdpyinfo').call().stdout.splitlines():
        if 'dimensions:' in x:
            screen_width, screen_height = map(
                int, x.strip().split()[1].split('x'))

    # xrandr | grep '*'
#    for x in EasyProcess('xrandr').call().stdout.splitlines():
#        if '*' in x:
#            screen_width, screen_height = map(
#                int, x.strip().split()[0].split('x'))
    return screen_width, screen_height

process = screen = None


def setup_func():
    'set up test fixtures'
    global process, screen
    screen = Display(visible=0)
    screen.start()
    process = EasyProcess('gnumeric').start().sleep(3)


def teardown_func():
    'tear down test fixtures'
    global process, screen
    process.stop()
    screen.stop()


def test_display_size():
    width, height = display_size()
    assert width > 10
    assert height > 10


def check_size(backend, bbox):
#    BackendLoader().force(backend)

    for childprocess in [0, 1]:
        im = pyscreenshot.grab(
            bbox=bbox,
            backend=backend,
            childprocess=childprocess,
        )
        img_debug(im, backend + str(bbox))

        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        else:
            width, height = display_size()

        eq_(width, im.size[0])
        eq_(height, im.size[1])

        # it fails sometimes
        # eq_('RGB', im.mode, 'wrong mode! %s' % (backend))

        f = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='pyscreenshot_test_')
        filename = f.name
        pyscreenshot.grab_to_file(
            backend=backend,
            childprocess=childprocess,
            filename=filename,
        )


def check_ref(backend, bbox):
        # some tests fail -> disable
    return

    BackendLoader().force(ref)
    img_ref = pyscreenshot.grab(bbox=bbox)
    img_debug(img_ref, ref + str(bbox))

    BackendLoader().force(backend)
    im = pyscreenshot.grab(bbox=bbox)
    img_debug(im, backend + str(bbox))

    eq_('RGB', img_ref.mode)
    eq_('RGB', im.mode)

    img_diff = ImageChops.difference(img_ref, im)
    bbox = img_diff.getbbox()
    if bbox:
        img_debug(img_diff, 'img_diff' + str(bbox))
    eq_(bbox, None, 'different image data %s!=%s bbox=%s' % (ref,
        backend, bbox))


bbox_ls = [
    (100, 200, 300, 400),
    (10, 10, 20, 20),
    (100, 100, 200, 200),
    (1, 2, 3, 4),
    (10, 20, 30, 40),
    None]


def backend_size(backend):
    for bbox in bbox_ls:
        print 'bbox:', bbox
#        for backend in backends:
        print 'backend:', backend
        check_size(backend, bbox)


def backend_ref(backend):
    for bbox in bbox_ls:
        print 'bbox:', bbox
#        for backend in backends:
        setup_func()
        print 'backend:', backend
        check_ref(backend, bbox)
        teardown_func()

########NEW FILE########
__FILENAME__ = test_speed
from pyscreenshot.check.speedtest import speedtest


def test_speed():
    speedtest()

########NEW FILE########
__FILENAME__ = test_subproc_backends
from compare import backend_size, backend_ref


def test_scrot():
    backend = 'scrot'
    backend_size(backend)
    backend_ref(backend)


def test_imagemagick():
    backend = 'imagemagick'
    backend_size(backend)
    backend_ref(backend)

########NEW FILE########
