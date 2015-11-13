__FILENAME__ = test_xerox
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xerox
import unittest

class BasicAPITestCase(unittest.TestCase):
    def setUp(self):
        self.text = 'And now for something completely different.'
        
    def test_copy(self):
        xerox.copy(self.text)
        self.assertEqual(xerox.paste(), self.text)
        
    def test_paste(self):
        xerox.copy(self.text)
        self.assertEqual(xerox.paste(), self.text)
        
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

class ToolNotFound(Exception):
    """A needed tool was not found."""
    
class Pywin32NotFound(ToolNotFound):
    """PyWin32 must be installed."""

class ClrNotFound(ToolNotFound):
    """clr must be installed."""

class XcodeNotFound(ToolNotFound):
    """xcode must be installed."""

class XclipNotFound(ToolNotFound):
    """xclip must be installed.
       On Ubuntu,
       $ apt-get install xclip
    """

########NEW FILE########
__FILENAME__ = cli
""" Copy + Paste in Windows
"""

# found @ http://code.activestate.com/recipes/150115/

from .base import * 

try:
    import clr 
    clr.AddReference('PresentationCore')
    import System.Windows.Clipboard as clip
except ImportError as why:
    raise ClrNotFound


def copy(string): 
    """Copy given string into system clipboard."""

    clip.SetText(string)
    return
    

def paste():
    """Returns system clipboard contents."""

    if clip.ContainsText():
        return clip.GetText()
    
    return None 

 

########NEW FILE########
__FILENAME__ = core
import sys

__title__ = 'xerox'
__version__ = '0.2.1'
__author__ = 'Kenneth Reitz'
__license__ = 'MIT'

if sys.platform == 'darwin':
    from .darwin import *
    
elif sys.platform.startswith('linux'):
    from .linux import *
    
elif sys.platform == 'win32':
    from .win import *

elif sys.platform == 'cli':
    from .cli import *

########NEW FILE########
__FILENAME__ = darwin
# -*- coding: utf-8 -*-

""" Copy + Paste in OS X
"""


import subprocess

from .base import *


def copy(string):
    """Copy given string into system clipboard."""
    try:
        subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE).communicate(
                string.encode("utf-8"))
    except OSError as why:
        raise XcodeNotFound

    return


def paste():
    """Returns system clipboard contents."""
    try:
        return subprocess.Popen(
            ['pbpaste'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')

    except OSError as why:
        raise XcodeNotFound


########NEW FILE########
__FILENAME__ = linux
# -*- coding: utf-8 -*-

""" Copy + Paste in Linux
"""

import subprocess
from .base import *


def copy(string):
    """Copy given string into system clipboard."""
    try:
        _cmd = ["xclip", "-selection", "clipboard"]
        subprocess.Popen(_cmd, stdin=subprocess.PIPE).communicate(
                string.encode('utf-8'))
        return
    except OSError as why:
        raise XclipNotFound
    
def paste():
    """Returns system clipboard contents."""
    try:
        return subprocess.Popen(["xclip", "-selection", "clipboard", "-o"], stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
    except OSError as why:
        raise XclipNotFound


########NEW FILE########
__FILENAME__ = win
""" Copy + Paste in Windows
"""

# found @ http://code.activestate.com/recipes/150115/

from .base import * 

try:
    import win32clipboard as clip
    import win32con
except ImportError as why:
    raise Pywin32NotFound


def copy(string): 
    """Copy given string into system clipboard."""

    clip.OpenClipboard()
    clip.EmptyClipboard()
    clip.SetClipboardData(win32con.CF_UNICODETEXT, string) 
    clip.CloseClipboard()

    return
    

def paste():
    """Returns system clipboard contents."""

    clip.OpenClipboard() 
    d = clip.GetClipboardData(win32con.CF_TEXT) 
    clip.CloseClipboard() 
    return d 

 

########NEW FILE########
