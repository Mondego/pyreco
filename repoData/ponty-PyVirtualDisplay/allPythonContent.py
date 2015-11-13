__FILENAME__ = conf
from easyprocess import EasyProcess
import logging


p = EasyProcess('python setup.py --version', cwd='..').call()
release = p.stdout.splitlines()[-1]
print release

project = 'PyVirtualDisplay'
author = 'ponty'
copyright = '2011, ponty'

# logging.basicConfig(level=logging.DEBUG)

# Extension
extensions = [
    # -*-Extensions: -*-
    'sphinx.ext.autodoc',
    'sphinxcontrib.programoutput',
    'sphinxcontrib.programscreenshot',
    'sphinx.ext.graphviz',
    #'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
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
from setuptools import find_packages

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
sys.path.append('.')
setup_py = ''.join(
    [x for x in path('setup.py').lines() if 'distutils' not in x])
exec(setup_py)
sys.path.pop()


options(
    sphinx=Bunch(
        docroot='docs',
        builddir="_build",
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
                                 '*.zip',
                                 'distribute_setup.py',
                                 ]

options.paved.dist.manifest.include.remove('distribute_setup.py')
options.paved.dist.manifest.include.remove('paver-minilib.zip')
options.paved.dist.manifest.include.add('requirements.txt')
options.paved.dist.manifest.include.add('versioneer.py')


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
@needs('manifest',
       'distutils.command.sdist',
       )
def sdist():
    """Overrides sdist to make sure that our MANIFEST.in is generated.
    """
    pass

########NEW FILE########
__FILENAME__ = abstractdisplay
from easyprocess import EasyProcess
import fnmatch
import logging
import os
import time

log = logging.getLogger(__name__)

# TODO: not perfect
# randomize to avoid possible conflicts
RANDOMIZE_DISPLAY_NR = True
if RANDOMIZE_DISPLAY_NR:
    import random
    random.seed()

MIN_DISPLAY_NR = 1000


class AbstractDisplay(EasyProcess):
    '''
    Common parent for Xvfb and Xephyr
    '''

    def __init__(self):
        self.display = self.search_for_display()
        EasyProcess.__init__(self, self._cmd)

    @property
    def new_display_var(self):
        return ':%s' % (self.display)

    @property
    def _cmd(self):
        raise NotImplementedError()

    def lock_files(self):
        tmpdir = '/tmp'
        pattern = '.X*-lock'
#        ls = path('/tmp').files('.X*-lock')
        # remove path.py dependency
        names = fnmatch.filter(os.listdir(tmpdir), pattern)
        ls = [os.path.join(tmpdir, child) for child in names]
        ls = [p for p in ls if os.path.isfile(p)]
        return ls

    def search_for_display(self):
        # search for free display
        ls = map(
            lambda x: int(x.split('X')[1].split('-')[0]), self.lock_files())
        if len(ls):
            display = max(MIN_DISPLAY_NR, max(ls) + 1)
        else:
            display = MIN_DISPLAY_NR

        if RANDOMIZE_DISPLAY_NR:
            display += random.randint(0, 100)
        return display

    def redirect_display(self, on):
        '''
        on:
         * True -> set $DISPLAY to virtual screen
         * False -> set $DISPLAY to original screen

        :param on: bool
        '''
        d = self.new_display_var if on else self.old_display_var
        log.debug('DISPLAY=' + d)
        os.environ['DISPLAY'] = d

    def start(self):
        '''
        start display

        :rtype: self
        '''
        EasyProcess.start(self)

        # https://github.com/ponty/PyVirtualDisplay/issues/2
        self.old_display_var = os.environ[
            'DISPLAY'] if 'DISPLAY' in os.environ else ':0'

        self.redirect_display(True)
        # wait until X server is active
        # TODO: better method
        time.sleep(0.1)
        return self

    def stop(self):
        '''
        stop display

        :rtype: self
        '''
        self.redirect_display(False)
        EasyProcess.stop(self)
        return self

########NEW FILE########
__FILENAME__ = display
from pyvirtualdisplay.abstractdisplay import AbstractDisplay
from pyvirtualdisplay.xephyr import XephyrDisplay
from pyvirtualdisplay.xvfb import XvfbDisplay
from pyvirtualdisplay.xvnc import XvncDisplay


class Display(AbstractDisplay):
    '''
    Common class

    :param color_depth: [8, 16, 24, 32]
    :param size: screen size (width,height)
    :param bgcolor: background color ['black' or 'white']
    :param visible: True -> Xephyr, False -> Xvfb
    :param backend: 'xvfb', 'xvnc' or 'xephyr', ignores ``visible``
    '''
    def __init__(self, backend=None, visible=False, size=(1024, 768), color_depth=24, bgcolor='black', **kwargs):
        self.color_depth = color_depth
        self.size = size
        self.bgcolor = bgcolor
        self.screen = 0
        self.process = None
        self.display = None
        self.visible = visible
        self.backend = backend

        if not self.backend:
            if self.visible:
                self.backend = 'xephyr'
            else:
                self.backend = 'xvfb'

        self._obj = self.display_class(
            size=size,
            color_depth=color_depth,
            bgcolor=bgcolor,
            **kwargs)
        AbstractDisplay.__init__(self)

    @property
    def display_class(self):
        assert self.backend
        if self.backend == 'xvfb':
            cls = XvfbDisplay
        if self.backend == 'xvnc':
            cls = XvncDisplay
        if self.backend == 'xephyr':
            cls = XephyrDisplay

        # TODO: check only once
        cls.check_installed()

        return cls

    @property
    def _cmd(self):
        self._obj.display = self.display
        return self._obj._cmd

########NEW FILE########
__FILENAME__ = lowres
from easyprocess import EasyProcess
from pyvirtualdisplay import Display

Display(visible=1, size=(320, 240)).start()
EasyProcess('gnumeric').start()

########NEW FILE########
__FILENAME__ = screenshot1
from easyprocess import EasyProcess
from pyvirtualdisplay.smartdisplay import SmartDisplay

disp = SmartDisplay(visible=0, bgcolor='black').start()
xmessage = EasyProcess('xmessage hello').start()
img = disp.waitgrab()
xmessage.stop()
disp.stop()
img.show()

########NEW FILE########
__FILENAME__ = screenshot3
'''
using :keyword:`with` statement
'''
import logging
logging.basicConfig(level=logging.DEBUG)

from easyprocess import EasyProcess
from pyvirtualdisplay.smartdisplay import SmartDisplay

with SmartDisplay(visible=0, bgcolor='black') as disp:
    with EasyProcess('xmessage hello'):
        img = disp.waitgrab()


img.show()

########NEW FILE########
__FILENAME__ = screenshot4
'''
two calls
'''
import logging
logging.basicConfig(level=logging.DEBUG)

from easyprocess import EasyProcess
from pyvirtualdisplay.smartdisplay import SmartDisplay

backend1 = 'wx'
backend2 = 'wx'


with SmartDisplay(visible=0, bgcolor='black') as disp:
    disp.pyscreenshot_backend = backend1
    with EasyProcess('xmessage test1'):
        img1 = disp.waitgrab()

with SmartDisplay(visible=0, bgcolor='black') as disp:
    disp.pyscreenshot_backend = backend2
    with EasyProcess('xmessage test2'):
        img2 = disp.waitgrab()

img1.show()
img2.show()

########NEW FILE########
__FILENAME__ = vncserver
'''
Example for Xvnc backend
'''

from easyprocess import EasyProcess
from entrypoint2 import entrypoint
from pyvirtualdisplay.display import Display


@entrypoint
def main(rfbport=5904):
    with Display(backend='xvnc', rfbport=rfbport) as disp:
        with EasyProcess('xmessage hello') as proc:
            proc.wait()

########NEW FILE########
__FILENAME__ = smartdisplay
from pyvirtualdisplay.display import Display
from PIL import Image
from PIL import ImageChops
import logging
import pyscreenshot
import time


log = logging.getLogger(__name__)


# class DisplayError(Exception):
#    pass

class DisplayTimeoutError(Exception):
    pass


class SmartDisplay(Display):
    pyscreenshot_backend = None
    pyscreenshot_childprocess = False

    def autocrop(self, im):
        '''Crop borders off an image.

        :param im: Source image.
        :param bgcolor: Background color, using either a color tuple or a color name (1.1.4 only).
        :return: An image without borders, or None if there's no actual content in the image.
        '''
        if im.mode != "RGB":
            im = im.convert("RGB")
        bg = Image.new("RGB", im.size, self.bgcolor)
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)
        return None  # no contents

    def grab(self, autocrop=True):
        try:
            # first try newer pyscreenshot version
            img = pyscreenshot.grab(
                childprocess=self.pyscreenshot_childprocess,
                backend=self.pyscreenshot_backend,
            )
        except TypeError:
            # try older pyscreenshot version
            img = pyscreenshot.grab()

        if autocrop:
            img = self.autocrop(img)
        return img

    def waitgrab(self, timeout=60, autocrop=True, cb_imgcheck=None):
        '''start process and create screenshot.
        Repeat screenshot until it is not empty and
        cb_imgcheck callback function returns True
        for current screenshot.

        :param autocrop: True -> crop screenshot
        :param timeout: int
        :param cb_imgcheck: None or callback for testing img,
                            True = accept img,
                            False = reject img
        '''
        t = 0
        sleep_time = 0.3  # for fast windows
        repeat_time = 1
        while 1:
            log.debug('sleeping %s secs' % str(sleep_time))
            time.sleep(sleep_time)
            t += sleep_time
            img = self.grab(autocrop=autocrop)
            if img:
                if not cb_imgcheck:
                    break
                if cb_imgcheck(img):
                    break
            sleep_time = repeat_time
            repeat_time += 1  # progressive
            if t > timeout:
                msg = 'Timeout! elapsed time:%s timeout:%s ' % (t, timeout)
                raise DisplayTimeoutError(msg)
                break

            log.debug('screenshot is empty, next try..')
        assert img
#        if not img:
#            log.debug('screenshot is empty!')
        return img

########NEW FILE########
__FILENAME__ = xephyr
from easyprocess import EasyProcess
from pyvirtualdisplay.abstractdisplay import AbstractDisplay

PROGRAM = 'Xephyr'
URL = None
PACKAGE = 'xephyr'


class XephyrDisplay(AbstractDisplay):
    '''
    Xephyr wrapper

    Xephyr is an X server outputting to a window on a pre-existing X display
    '''
    def __init__(self, size=(1024, 768), color_depth=24, bgcolor='black'):
        '''
        :param bgcolor: 'black' or 'white'
        '''
        self.color_depth = color_depth
        self.size = size
        self.bgcolor = bgcolor
        self.screen = 0
        self.process = None
        self.display = None
        AbstractDisplay.__init__(self)

    @classmethod
    def check_installed(cls):
        EasyProcess([PROGRAM, '-help'], url=URL,
                    ubuntu_package=PACKAGE).check_installed()

    @property
    def _cmd(self):
        cmd = [PROGRAM,
               dict(black='-br', white='-wr')[self.bgcolor],
               '-screen',
               'x'.join(map(str, list(self.size) + [self.color_depth])),
               self.new_display_var,
               ]
        return cmd

########NEW FILE########
__FILENAME__ = xvfb
from easyprocess import EasyProcess
from pyvirtualdisplay.abstractdisplay import AbstractDisplay
import logging

log = logging.getLogger(__name__)

PROGRAM = 'Xvfb'
URL = None
PACKAGE = 'xvfb'


class XvfbDisplay(AbstractDisplay):
    '''
    Xvfb wrapper

    Xvfb is an X server that can run on machines with no display
    hardware and no physical input devices. It emulates a dumb
    framebuffer using virtual memory.
    '''
    def __init__(self, size=(1024, 768), color_depth=24, bgcolor='black', fbdir=None):
        '''
        :param bgcolor: 'black' or 'white'
        :param fbdir: If non-null, the virtual screen is memory-mapped
            to a file in the given directory ('-fbdir' option)
        '''
        self.screen = 0
        self.size = size
        self.color_depth = color_depth
        self.process = None
        self.bgcolor = bgcolor
        self.display = None
        self.fbdir = fbdir
        AbstractDisplay.__init__(self)

    @classmethod
    def check_installed(cls):
        EasyProcess([PROGRAM, '-help'], url=URL,
                    ubuntu_package=PACKAGE).check_installed()

    @property
    def _cmd(self):
        cmd = [
               dict(black='-br', white='-wr')[self.bgcolor],
               '-screen',
               str(self.screen),
               'x'.join(map(str, list(self.size) + [self.color_depth])),
               self.new_display_var,
               ]
        if self.fbdir:
            cmd += ['-fbdir', self.fbdir]
        return [PROGRAM] + cmd

########NEW FILE########
__FILENAME__ = xvnc
from easyprocess import EasyProcess
from pyvirtualdisplay.abstractdisplay import AbstractDisplay
import logging

log = logging.getLogger(__name__)

PROGRAM = 'Xvnc'
URL = None
PACKAGE = 'tightvncserver'


class XvncDisplay(AbstractDisplay):
    '''
    Xvnc wrapper
    '''
    def __init__(self, size=(1024, 768), color_depth=24, bgcolor='black', rfbport=5900):
        '''
        :param bgcolor: 'black' or 'white'
        :param rfbport: Specifies the TCP port on which Xvnc listens for connections from viewers (the protocol used in VNC is called RFB - "remote framebuffer"). The default is 5900 plus the display number.
        '''
        self.screen = 0
        self.size = size
        self.color_depth = color_depth
        self.process = None
        self.bgcolor = bgcolor
        self.display = None
        self.rfbport = rfbport
        AbstractDisplay.__init__(self)

    @classmethod
    def check_installed(cls):
        EasyProcess([PROGRAM, '-help'], url=URL,
                    ubuntu_package=PACKAGE).check_installed()

    @property
    def _cmd(self):
        cmd = [PROGRAM,
               '-depth', str(self.color_depth),
               '-geometry', '%dx%d' % (self.size[0], self.size[1]),
               '-rfbport', str(self.rfbport),
               self.new_display_var,
               ]
        return cmd

########NEW FILE########
__FILENAME__ = _version

# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.10 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "pyvirtualdisplay-"
versionfile_source = "pyvirtualdisplay/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)


########NEW FILE########
__FILENAME__ = slowgui
from easyprocess import EasyProcess
import time


def main():
    time.sleep(5)
    EasyProcess('zenity --question').start()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_core
from nose.tools import ok_
from pyvirtualdisplay.display import Display
from pyvirtualdisplay.xephyr import XephyrDisplay
from pyvirtualdisplay.xvfb import XvfbDisplay
from pyvirtualdisplay.xvnc import XvncDisplay
import sys
from unittest import TestCase


class Test(TestCase):
    def test_virt(self):
        vd = Display().start().stop()
#        self.assertEquals(vd.return_code, 0)
        ok_(not vd.is_alive())

    def test_nest(self):
        vd = Display().start()
        ok_(vd.is_alive())

        nd = Display(visible=1).start().stop()

#        self.assertEquals(nd.return_code, 0)

        vd.stop()
        ok_(not vd.is_alive())

    def test_disp(self):
        vd = Display().start()
        ok_(vd.is_alive())

        d = Display(visible=1).start().sleep(2).stop()
#        self.assertEquals(d.return_code, 0)

        d = Display(visible=0).start().stop()
#        self.assertEquals(d.return_code, 0)

        vd.stop()
        ok_(not vd.is_alive())


def test_repr():
    display = Display()
    print(repr(display))


def test_repr2():
    display = XvfbDisplay()
    print(repr(display))


def test_repr3():
    display = XvncDisplay()
    print(repr(display))


def test_repr4():
    display = XephyrDisplay()
    print(repr(display))

########NEW FILE########
__FILENAME__ = test_examples
from easyprocess import EasyProcess
from pyvirtualdisplay.display import Display
import logging
import time


log = logging.getLogger(__name__)


VISIBLE = 0


def test_screenshot3():
    with Display(visible=VISIBLE):
        with EasyProcess('python -m pyvirtualdisplay.examples.screenshot3'):
            time.sleep(1)

########NEW FILE########
__FILENAME__ = test_smart
from easyprocess import EasyProcess
from nose.tools import eq_
from path import path
from pyvirtualdisplay.smartdisplay import SmartDisplay, DisplayTimeoutError
from unittest import TestCase
import sys


class Test(TestCase):
    def test_disp(self):
        vd = SmartDisplay().start()

        d = SmartDisplay(visible=1).start().sleep(2).stop()
        self.assertEquals(d.return_code, 0)

        d = SmartDisplay(visible=0).start().stop()
        self.assertEquals(d.return_code, 0)

        vd.stop()

    def test_slowshot(self):
        disp = SmartDisplay(visible=0).start()
        py = path(__file__).parent / ('slowgui.py')
        proc = EasyProcess('python ' + py).start()
        img = disp.waitgrab()
        proc.stop()
        disp.stop()
        eq_(img is not None, True)

    def test_slowshot_wrap(self):
        disp = SmartDisplay(visible=0)
        py = path(__file__).parent / ('slowgui.py')
        proc = EasyProcess('python ' + py)
        f = disp.wrap(proc.wrap(disp.waitgrab))
        img = f()
        eq_(img is not None, True)

    def test_empty(self):
        disp = SmartDisplay(visible=0)
        proc = EasyProcess(sys.executable)
        f = disp.wrap(proc.wrap(disp.waitgrab))
        self.assertRaises(Exception, f)

    def test_slowshot_timeout(self):
        disp = SmartDisplay(visible=0)
        py = path(__file__).parent / ('slowgui.py')
        proc = EasyProcess('python ' + py)
        f = disp.wrap(proc.wrap(lambda: disp.waitgrab(timeout=1)))
        self.assertRaises(DisplayTimeoutError, f)

########NEW FILE########
__FILENAME__ = test_smart2
from easyprocess import EasyProcess
from nose.tools import eq_
from pyvirtualdisplay.smartdisplay import SmartDisplay, DisplayTimeoutError
from unittest import TestCase
from path import path
import pyscreenshot


class Test(TestCase):
    def check_double(self, backend1, backend2=None):
        if not backend2:
            backend2 = backend1

        with SmartDisplay(visible=0, bgcolor='black') as disp:
            disp.pyscreenshot_backend = backend1
            disp.pyscreenshot_childprocess = True  # error if FALSE
            with EasyProcess('xmessage hello1'):
                img = disp.waitgrab()
                eq_(img is not None, True)

        with SmartDisplay(visible=0, bgcolor='black') as disp:
            disp.pyscreenshot_backend = backend2
            disp.pyscreenshot_childprocess = True  # error if FALSE
            with EasyProcess('xmessage hello2'):
                img = disp.waitgrab()
                eq_(img is not None, True)

    def test_double_wx(self):
        self.check_double('wx')

    def test_double_pygtk(self):
        self.check_double('pygtk')

    def test_double_pyqt(self):
        self.check_double('pyqt')

    def test_double_imagemagick(self):
        self.check_double('imagemagick')

    def test_double_scrot(self):
        self.check_double('scrot')

    def test_double_wx_pygtk(self):
        self.check_double('wx', 'pygtk')

    def test_double_wx_pyqt(self):
        self.check_double('wx', 'pyqt')

    def test_double_pygtk_pyqt(self):
        self.check_double('pygtk', 'pyqt')

########NEW FILE########
__FILENAME__ = test_with
from nose.tools import ok_, eq_
from pyvirtualdisplay.display import Display


def test_with():
    with Display(visible=0, size=(800, 600)) as vd:
        ok_(vd.is_alive())
    eq_(vd.return_code, 0)
    ok_(not vd.is_alive())

########NEW FILE########
__FILENAME__ = versioneer

# Version: 0.10

"""
The Versioneer
==============

* like a rocketeer, but for versions!
* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Compatible With: python2.6, 2.7, and 3.2, 3.3

[![Build Status](https://travis-ci.org/warner/python-versioneer.png?branch=master)](https://travis-ci.org/warner/python-versioneer)

This is a tool for managing a recorded version number in distutils-based
python projects. The goal is to remove the tedious and error-prone "update
the embedded version string" step from your release process. Making a new
release should be as easy as recording a new tag in your version-control
system, and maybe making new tarballs.


## Quick Install

* `pip install versioneer` to somewhere to your $PATH
* run `versioneer-installer` in your source tree: this installs `versioneer.py`
* follow the instructions below (also in the `versioneer.py` docstring)

## Version Identifiers

Source trees come from a variety of places:

* a version-control system checkout (mostly used by developers)
* a nightly tarball, produced by build automation
* a snapshot tarball, produced by a web-based VCS browser, like github's
  "tarball from tag" feature
* a release tarball, produced by "setup.py sdist", distributed through PyPI

Within each source tree, the version identifier (either a string or a number,
this tool is format-agnostic) can come from a variety of places:

* ask the VCS tool itself, e.g. "git describe" (for checkouts), which knows
  about recent "tags" and an absolute revision-id
* the name of the directory into which the tarball was unpacked
* an expanded VCS variable ($Id$, etc)
* a `_version.py` created by some earlier build step

For released software, the version identifier is closely related to a VCS
tag. Some projects use tag names that include more than just the version
string (e.g. "myproject-1.2" instead of just "1.2"), in which case the tool
needs to strip the tag prefix to extract the version identifier. For
unreleased software (between tags), the version identifier should provide
enough information to help developers recreate the same tree, while also
giving them an idea of roughly how old the tree is (after version 1.2, before
version 1.3). Many VCS systems can report a description that captures this,
for example 'git describe --tags --dirty --always' reports things like
"0.7-1-g574ab98-dirty" to indicate that the checkout is one revision past the
0.7 tag, has a unique revision id of "574ab98", and is "dirty" (it has
uncommitted changes.

The version identifier is used for multiple purposes:

* to allow the module to self-identify its version: `myproject.__version__`
* to choose a name and prefix for a 'setup.py sdist' tarball

## Theory of Operation

Versioneer works by adding a special `_version.py` file into your source
tree, where your `__init__.py` can import it. This `_version.py` knows how to
dynamically ask the VCS tool for version information at import time. However,
when you use "setup.py build" or "setup.py sdist", `_version.py` in the new
copy is replaced by a small static file that contains just the generated
version data.

`_version.py` also contains `$Revision$` markers, and the installation
process marks `_version.py` to have this marker rewritten with a tag name
during the "git archive" command. As a result, generated tarballs will
contain enough information to get the proper version.


## Installation

First, decide on values for the following configuration variables:

* `versionfile_source`:

  A project-relative pathname into which the generated version strings should
  be written. This is usually a `_version.py` next to your project's main
  `__init__.py` file. If your project uses `src/myproject/__init__.py`, this
  should be `src/myproject/_version.py`. This file should be checked in to
  your VCS as usual: the copy created below by `setup.py versioneer` will
  include code that parses expanded VCS keywords in generated tarballs. The
  'build' and 'sdist' commands will replace it with a copy that has just the
  calculated version string.

*  `versionfile_build`:

  Like `versionfile_source`, but relative to the build directory instead of
  the source directory. These will differ when your setup.py uses
  'package_dir='. If you have `package_dir={'myproject': 'src/myproject'}`,
  then you will probably have `versionfile_build='myproject/_version.py'` and
  `versionfile_source='src/myproject/_version.py'`.

* `tag_prefix`:

  a string, like 'PROJECTNAME-', which appears at the start of all VCS tags.
  If your tags look like 'myproject-1.2.0', then you should use
  tag_prefix='myproject-'. If you use unprefixed tags like '1.2.0', this
  should be an empty string.

* `parentdir_prefix`:

  a string, frequently the same as tag_prefix, which appears at the start of
  all unpacked tarball filenames. If your tarball unpacks into
  'myproject-1.2.0', this should be 'myproject-'.

This tool provides one script, named `versioneer-installer`. That script does
one thing: write a copy of `versioneer.py` into the current directory.

To versioneer-enable your project:

* 1: Run `versioneer-installer` to copy `versioneer.py` into the top of your
  source tree.

* 2: add the following lines to the top of your `setup.py`, with the
  configuration values you decided earlier:

        import versioneer
        versioneer.versionfile_source = 'src/myproject/_version.py'
        versioneer.versionfile_build = 'myproject/_version.py'
        versioneer.tag_prefix = '' # tags are like 1.2.0
        versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'

* 3: add the following arguments to the setup() call in your setup.py:

        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),

* 4: now run `setup.py versioneer`, which will create `_version.py`, and
  will modify your `__init__.py` to define `__version__` (by calling a
  function from `_version.py`). It will also modify your `MANIFEST.in` to
  include both `versioneer.py` and the generated `_version.py` in sdist
  tarballs.

* 5: commit these changes to your VCS. To make sure you won't forget,
  `setup.py versioneer` will mark everything it touched for addition.

## Post-Installation Usage

Once established, all uses of your tree from a VCS checkout should get the
current version string. All generated tarballs should include an embedded
version string (so users who unpack them will not need a VCS tool installed).

If you distribute your project through PyPI, then the release process should
boil down to two steps:

* 1: git tag 1.0
* 2: python setup.py register sdist upload

If you distribute it through github (i.e. users use github to generate
tarballs with `git archive`), the process is:

* 1: git tag 1.0
* 2: git push; git push --tags

Currently, all version strings must be based upon a tag. Versioneer will
report "unknown" until your tree has at least one tag in its history. This
restriction will be fixed eventually (see issue #12).

## Version-String Flavors

Code which uses Versioneer can learn about its version string at runtime by
importing `_version` from your main `__init__.py` file and running the
`get_versions()` function. From the "outside" (e.g. in `setup.py`), you can
import the top-level `versioneer.py` and run `get_versions()`.

Both functions return a dictionary with different keys for different flavors
of the version string:

* `['version']`: condensed tag+distance+shortid+dirty identifier. For git,
  this uses the output of `git describe --tags --dirty --always` but strips
  the tag_prefix. For example "0.11-2-g1076c97-dirty" indicates that the tree
  is like the "1076c97" commit but has uncommitted changes ("-dirty"), and
  that this commit is two revisions ("-2-") beyond the "0.11" tag. For
  released software (exactly equal to a known tag), the identifier will only
  contain the stripped tag, e.g. "0.11".

* `['full']`: detailed revision identifier. For Git, this is the full SHA1
  commit id, followed by "-dirty" if the tree contains uncommitted changes,
  e.g. "1076c978a8d3cfc70f408fe5974aa6c092c949ac-dirty".

Some variants are more useful than others. Including `full` in a bug report
should allow developers to reconstruct the exact code being tested (or
indicate the presence of local changes that should be shared with the
developers). `version` is suitable for display in an "about" box or a CLI
`--version` output: it can be easily compared against release notes and lists
of bugs fixed in various releases.

In the future, this will also include a
[PEP-0440](http://legacy.python.org/dev/peps/pep-0440/) -compatible flavor
(e.g. `1.2.post0.dev123`). This loses a lot of information (and has no room
for a hash-based revision id), but is safe to use in a `setup.py`
"`version=`" argument. It also enables tools like *pip* to compare version
strings and evaluate compatibility constraint declarations.

The `setup.py versioneer` command adds the following text to your
`__init__.py` to place a basic version in `YOURPROJECT.__version__`:

    from ._version import get_versions
    __version = get_versions()['version']
    del get_versions

## Updating Versioneer

To upgrade your project to a new release of Versioneer, do the following:

* install the new Versioneer (`pip install -U versioneer` or equivalent)
* re-run `versioneer-installer` in your source tree to replace `versioneer.py`
* edit `setup.py`, if necessary, to include any new configuration settings indicated by the release notes
* re-run `setup.py versioneer` to replace `SRC/_version.py`
* commit any changed files

## Future Directions

This tool is designed to make it easily extended to other version-control
systems: all VCS-specific components are in separate directories like
src/git/ . The top-level `versioneer.py` script is assembled from these
components by running make-versioneer.py . In the future, make-versioneer.py
will take a VCS name as an argument, and will construct a version of
`versioneer.py` that is specific to the given VCS. It might also take the
configuration arguments that are currently provided manually during
installation by editing setup.py . Alternatively, it might go the other
direction and include code from all supported VCS systems, reducing the
number of intermediate scripts.


## License

To make Versioneer easier to embed, all its code is hereby released into the
public domain. The `_version.py` that it creates is also in the public
domain.

"""

import os, sys, re
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"


LONG_VERSION_PY = '''
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.10 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %%s" %% args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %%s" %% (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %%d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%%s', no digits" %% ",".join(refs-tags))
    if verbose:
        print("likely tags: %%s" %% ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)

'''


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}
import os.path
import sys

# os.path.relpath only appeared in Python-2.6 . Define it here for 2.5.
def os_path_relpath(path, start=os.path.curdir):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
    path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return os.path.curdir
    return os.path.join(*rel_list)

def do_vcs_install(manifest_in, versionfile_source, ipy):
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    files = [manifest_in, versionfile_source, ipy]
    try:
        me = __file__
        if me.endswith(".pyc") or me.endswith(".pyo"):
            me = os.path.splitext(me)[0] + ".py"
        versioneer_file = os_path_relpath(me)
    except NameError:
        versioneer_file = "versioneer.py"
    files.append(versioneer_file)
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass    
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        files.append(".gitattributes")
    run_command(GITS, ["add", "--"] + files)

SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.10) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    f.close()
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))

def get_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def get_versions(default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    # I am in versioneer.py, which must live at the top of the source tree,
    # which we use to compute the root directory. py2exe/bbfreeze/non-CPython
    # don't have __file__, in which case we fall back to sys.argv[0] (which
    # ought to be the setup.py script). We prefer __file__ since that's more
    # robust in cases where setup.py was invoked in some weird way (e.g. pip)
    root = get_root()
    versionfile_abs = os.path.join(root, versionfile_source)

    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_abs)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile_abs)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile_abs,ver))
        return ver

    ver = versions_from_vcs(tag_prefix, root, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, root, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
    from cx_Freeze.dist import build_exe as _build_exe

    class cmd_build_exe(_build_exe):
        def run(self):
            versions = get_versions(verbose=True)
            target_versionfile = versionfile_source
            print("UPDATING %s" % target_versionfile)
            os.unlink(target_versionfile)
            f = open(target_versionfile, "w")
            f.write(SHORT_VERSION_PY % versions)
            f.close()
            _build_exe.run(self)
            os.unlink(target_versionfile)
            f = open(versionfile_source, "w")
            f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                       "TAG_PREFIX": tag_prefix,
                                       "PARENTDIR_PREFIX": parentdir_prefix,
                                       "VERSIONFILE_SOURCE": versionfile_source,
                                       })
            f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "install/upgrade Versioneer files: __init__.py SRC/_version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()

        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)

        # Make sure both the top-level "versioneer.py" and versionfile_source
        # (PKG/_version.py, used by runtime code) are in MANIFEST.in, so
        # they'll be copied into source distributions. Pip won't be able to
        # install the package without this.
        manifest_in = os.path.join(get_root(), "MANIFEST.in")
        simple_includes = set()
        try:
            for line in open(manifest_in, "r").readlines():
                if line.startswith("include "):
                    for include in line.split()[1:]:
                        simple_includes.add(include)
        except EnvironmentError:
            pass
        # That doesn't cover everything MANIFEST.in can do
        # (http://docs.python.org/2/distutils/sourcedist.html#commands), so
        # it might give some false negatives. Appending redundant 'include'
        # lines is safe, though.
        if "versioneer.py" not in simple_includes:
            print(" appending 'versioneer.py' to MANIFEST.in")
            f = open(manifest_in, "a")
            f.write("include versioneer.py\n")
            f.close()
        else:
            print(" 'versioneer.py' already in MANIFEST.in")
        if versionfile_source not in simple_includes:
            print(" appending versionfile_source ('%s') to MANIFEST.in" %
                  versionfile_source)
            f = open(manifest_in, "a")
            f.write("include %s\n" % versionfile_source)
            f.close()
        else:
            print(" versionfile_source already in MANIFEST.in")

        # Make VCS-specific changes. For git, this means creating/changing
        # .gitattributes to mark _version.py for export-time keyword
        # substitution.
        do_vcs_install(manifest_in, versionfile_source, ipy)

def get_cmdclass():
    cmds = {'version': cmd_version,
            'versioneer': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }
    if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
        cmds['build_exe'] = cmd_build_exe
        del cmds['build']

    return cmds

########NEW FILE########
