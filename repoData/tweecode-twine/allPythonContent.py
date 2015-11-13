__FILENAME__ = app
#!/usr/bin/env python2

import sys, os, locale, re, pickle, wx, platform, traceback
import metrics
from header import Header
from storyframe import StoryFrame
from prefframe import PreferenceFrame
from version import versionString

class App(wx.App):
    """This bootstraps our application and keeps track of preferences, etc."""

    NAME = 'Twine'
    VERSION = '%s (running on %s %s)' % (versionString, platform.system(), platform.release()) #Named attributes not available in Python 2.6
    RECENT_FILES = 10

    def __init__(self, redirect = False):
        """Initializes the application."""
        wx.App.__init__(self, redirect = redirect)
        locale.setlocale(locale.LC_ALL, '')
        self.stories = []
        self.loadPrefs()
        self.determinePaths()
        self.loadTargetHeaders()

        # try to load our app icon
        # if it doesn't work, we continue anyway

        self.icon = wx.EmptyIcon()

        try:
            self.icon = wx.Icon(self.iconsPath + 'app.ico', wx.BITMAP_TYPE_ICO)
        except:
            pass


        # restore save location

        try:
            os.chdir(self.config.Read('savePath'))
        except:
            os.chdir(os.path.expanduser('~'))

        if not self.openOnStartup():
            if self.config.HasEntry('LastFile') \
            and os.path.exists(self.config.Read('LastFile')):
                self.open(self.config.Read('LastFile'))
            else:
                self.newStory()

    def newStory(self, event = None):
        """Opens a new, blank story."""
        s = StoryFrame(parent = None, app = self)
        self.stories.append(s)
        s.Show(True)

    def removeStory(self, story, byMenu = False):
        """Removes a story from our collection. Should be called when it closes."""
        try:
            self.stories.remove(story)
            if byMenu:
                counter = 0
                for s in self.stories:
                    if isinstance(s, StoryFrame):
                        counter = counter + 1
                if counter == 0:
                    self.newStory()

        except ValueError:
            None

    def openDialog(self, event = None):
        """Opens a story file of the user's choice."""
        opened = False
        dialog = wx.FileDialog(None, 'Open Story', os.getcwd(), "", "Twine Story (*.tws)|*.tws", \
                               wx.FD_OPEN | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            opened = True
            self.config.Write('savePath', os.getcwd())
            self.addRecentFile(dialog.GetPath())
            self.open(dialog.GetPath())

        dialog.Destroy()

    def openRecent(self, story, index):
        """Opens a recently-opened file."""
        filename = story.recentFiles.GetHistoryFile(index)
        if not os.path.exists(filename):
            self.removeRecentFile(story, index)
        else:
            self.open(filename)
            self.addRecentFile(filename)

    def MacOpenFile(self, path):
        """OS X support"""
        self.open(path)

    def open(self, path):
        """Opens a specific story file."""
        try:
            openedFile = open(path, 'r')
            newStory = StoryFrame(None, app = self, state = pickle.load(openedFile))
            newStory.saveDestination = path
            self.stories.append(newStory)
            newStory.Show(True)
            self.addRecentFile(path)
            self.config.Write('LastFile', path)
            openedFile.close()

            # weird special case:
            # if we only had one story opened before
            # and it's pristine (e.g. no changes ever made to it),
            # then we close it after opening the file successfully

            if (len(self.stories) == 2) and (self.stories[0].pristine):
                self.stories[0].Destroy()

        except:
            self.displayError('opening your story')

    def openOnStartup(self):
        """
        Opens any files that were passed via argv[1:]. Returns
        whether anything was opened.
        """
        if len(sys.argv) is 1:
            return False

        for file in sys.argv[1:]:
            self.open(file)

        return True

    def exit(self, event = None):
        """Closes all open stories, implicitly quitting."""
        # need to make a copy of our stories list since
        # stories removing themselves will alter the list midstream
        for s in list(self.stories):
            if isinstance(s, StoryFrame):
                s.Close()

    def showPrefs(self, event = None):
        """Shows the preferences dialog."""
        if (not hasattr(self, 'prefFrame')):
            self.prefFrame = PreferenceFrame(self)
        else:
            try:
                self.prefFrame.Raise()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'prefFrame')
                self.showPrefs(event)

    def addRecentFile(self, path):
        """Adds a path to the recent files history and updates the menus."""
        for s in self.stories:
            if isinstance(s, StoryFrame):
                s.recentFiles.AddFileToHistory(path)
                s.recentFiles.Save(self.config)

    def removeRecentFile(self, story, index):
        """Remove all missing files from the recent files history and update the menus."""

        def removeRecentFile_do(story, index, showdialog = True):
            filename = story.recentFiles.GetHistoryFile(index)
            story.recentFiles.RemoveFileFromHistory(index)
            story.recentFiles.Save(self.config)
            if showdialog:
                text = 'The file ' + filename + ' no longer exists.\n' + \
                       'This file has been removed from the Recent Files list.'
                dlg = wx.MessageDialog(None, text, 'Information', wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                return True
            else:
                return False
        showdialog = True
        for s in self.stories:
            if s != story and isinstance(s, StoryFrame):
                removeRecentFile_do(s, index, showdialog)
                showdialog = False
        removeRecentFile_do(story, index, showdialog)

    def verifyRecentFiles(self, story):
        done = False
        while done == False:
            for index in range(story.recentFiles.GetCount()):
                if not os.path.exists(story.recentFiles.GetHistoryFile(index)):
                    self.removeRecentFile(story, index)
                    done = False
                    break
            else:
                done = True

    def about(self, event = None):
        """Shows the about dialog."""
        info = wx.AboutDialogInfo()
        info.SetName(self.NAME)
        info.SetVersion(self.VERSION)
        info.SetIcon(self.icon)
        info.SetWebSite('http://twinery.org/')
        info.SetDescription('An open-source tool for telling interactive stories\nwritten by Chris Klimas')
        info.SetDevelopers(['Leon Arnott','Emmanuel Turner','Henry Soule','Misty De Meo','Phillip Sutton','Thomas M. Edwards','Maarten ter Huurne','and others.'])

        info.SetLicense('The Twine development application and its Python source code is free software: you can redistribute it and/or modify'
                          + ' it under the terms of the GNU General Public License as published by the Free Software'
                          + ' Foundation, either version 3 of the License, or (at your option) any later version.'
                          + ' See the GNU General Public License for more details.\n\nThe Javascript game engine in compiled game files is a derivative work of Jeremy Ruston\'s TiddlyWiki project,'
                          + ' and is used under the terms of the MIT license.')
        wx.AboutBox(info)

    def storyFormatHelp(self, event = None):
        """Opens the online manual to the section on story formats."""
        wx.LaunchDefaultBrowser('http://twinery.org/wiki/story_format')

    def openForum(self, event = None):
        """Opens the forum."""
        wx.LaunchDefaultBrowser('http://twinery.org/forum/')

    def openDocs(self, event = None):
        """Opens the online manual."""
        wx.LaunchDefaultBrowser('http://twinery.org/wiki/')

    def openGitHub(self, event = None):
        """Opens the GitHub page."""
        wx.LaunchDefaultBrowser('https://github.com/tweecode/twine')

    def loadPrefs(self):
        """Loads user preferences into self.config, setting up defaults if none are set."""
        sc = self.config = wx.Config('Twine')

        monoFont = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT)

        for k,v in {
            'savePath' : os.path.expanduser('~'),
            'fsTextColor' : '#afcdff',
            'fsBgColor' : '#100088',
            'fsFontFace' : metrics.face('mono'),
            'fsFontSize' : metrics.size('fsEditorBody'),
            'fsLineHeight' : 120,
            'windowedFontFace' : metrics.face('mono'),
            'monospaceFontFace' : metrics.face('mono2'),
            'windowedFontSize' : metrics.size('editorBody'),
            'monospaceFontSize' : metrics.size('editorBody'),
            'flatDesign' : False,
            'storyFrameToolbar' : True,
            'storyPanelSnap' : False,
            'fastStoryPanel' : False,
            'imageArrows' : True,
            'displayArrows' : True,
            'createPassagePrompt' : True,
            'importImagePrompt' : True,
            'passageWarnings' : True
        }.iteritems():
            if not sc.HasEntry(k):
                if type(v) == str:
                    sc.Write(k,v)
                elif type(v) == int:
                    sc.WriteInt(k,v)
                elif type(v) == bool:
                    sc.WriteBool(k,v)

    def applyPrefs(self):
        """Asks all of our stories to update themselves based on a preference change."""
        map(lambda s: s.applyPrefs(), self.stories)

    def displayError(self, activity):
        """
        Displays an error dialog with diagnostic info. Call with what you were doing
        when the error occurred (e.g. 'saving your story', 'building your story'.)
        """
        exception = sys.exc_info()
        text = 'An error occurred while ' + activity + '.\n\n'
        text += ''.join(traceback.format_exc(5))
        error = wx.MessageDialog(None, text, 'Error', wx.OK | wx.ICON_ERROR)
        error.ShowModal()

    def MacReopenApp(self):
        """OS X support"""
        self.GetTopWindow().Raise()

    def determinePaths(self):
        """Determine the paths to relevant files used by application"""
        scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        if sys.platform == 'win32':
            # Windows py2exe'd apps add an extraneous library.zip at the end
            scriptPath = re.sub('\\\\\w*.zip', '', scriptPath)
        elif sys.platform == "darwin":
            scriptPath = re.sub('MacOS\/.*', '', scriptPath)

        scriptPath += os.sep
        self.iconsPath = scriptPath + 'icons' + os.sep
        self.builtinTargetsPath = scriptPath + 'targets' + os.sep

        if sys.platform == "darwin":
            self.externalTargetsPath = re.sub('[^/]+.app/.*', 'targets' + os.sep, self.builtinTargetsPath)
            if not os.path.isdir(self.externalTargetsPath):
                self.externalTargetsPath = ''
        else:
            self.externalTargetsPath = ''

    def loadTargetHeaders(self):
        """Load the target headers and populate the self.headers dictionary"""
        self.headers = {}
        # Get paths to built-in targets
        paths = [(t, self.builtinTargetsPath + t + os.sep) for t in os.listdir(self.builtinTargetsPath)]
        if self.externalTargetsPath:
            # Get paths to external targets
            paths += [(t, self.externalTargetsPath + t + os.sep) for t in os.listdir(self.externalTargetsPath)]
        # Look in subdirectories only for the header file
        for path in paths:
            try:
                if not os.path.isfile(path[1]) and os.access(path[1] + 'header.html', os.R_OK):
                    header = Header.factory(*path, builtinPath = self.builtinTargetsPath)
                    self.headers[header.id] = header
            except:
                pass


# start things up if we were called directly
if __name__ == "__main__":
    app = App()
    app.MainLoop()

########NEW FILE########
__FILENAME__ = buildapp
#!/usr/bin/env python2
#
# This builds an .app out of Twine for use with OS X.
# Call this with this command line: buildapp.py py2app

from distutils.core import setup
from version import versionString
import py2app

setup(app = ['app.py'], options = dict(py2app = dict( argv_emulation = True,
                                       iconfile = 'appicons/app.icns', \
                                       resources = ['icons', 'targets', 'appicons/doc.icns'], \
                                       plist = dict( \
                                       CFBundleShortVersionString = versionString, \
                                       CFBundleName = 'Twine', \
                                       CFBundleSignature = 'twee', \
                                       CFBundleIconFile = 'app.icns',\
                                       CFBundleGetInfoString = 'An open-source tool for telling interactive stories',\
                                       CFBundleDocumentTypes = [dict( \
                                           CFBundleTypeIconFile = 'doc.icns',\
                                           CFBundleTypeName = 'Twine story',\
                                           CFBundleTypeRole = 'Editor',\
                                           CFBundleTypeExtensions=["tws"]\
                                       )],\
                                       NSHumanReadableCopyright = 'GNU General Public License v3'))))

########NEW FILE########
__FILENAME__ = buildexe

# This builds an .exe out of Tweebox for use with Windows.
# Call this with this command line: buildexe.py
# py2exe is inserted as a command line parameter automatically.

import sys, os, py2exe
from distutils.core import setup
from version import versionString

manifest = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="1.3.5.1"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.30729.6161"
            processorArchitecture="X86"
            publicKeyToken="1fc8b3b9a1e18e3b"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''


# Force use of py2exe for building Win32.exe
sys.argv.append('py2exe')

# Clear out the dist/win32 directory
for root, dirs, files in os.walk('dist' + os.sep + 'win32', topdown=False):
    for name in files:
        os.remove(os.path.join(root, name))
    for name in dirs:
        os.rmdir(os.path.join(root, name))


# Build the exe
setup(
    name = 'Twine',
    description = 'Twine',
    version = versionString,

    windows = [{
        'script': 'app.py',
        'icon_resources': [(0x0004, 'appicons\\app.ico'), (0x0005, 'appicons\\doc.ico')],
        'dest_base': 'twine',
        'other_resources': [(24, 1, manifest % dict(prog='Twine'))],
    }],

    data_files = [
        ('targets' + os.sep + 'jonah',      ['targets' + os.sep + 'jonah'      + os.sep + 'header.html',
                                             'targets' + os.sep + 'jonah'      + os.sep + 'code.js']),
        ('targets' + os.sep + 'sugarcane',  ['targets' + os.sep + 'sugarcane'  + os.sep + 'header.html',
                                             'targets' + os.sep + 'sugarcane'  + os.sep + 'code.js']),
        ('targets' + os.sep + 'Responsive', ['targets' + os.sep + 'Responsive' + os.sep + 'header.html']),
        ('targets', [
            'targets' + os.sep + 'engine.js',
            'targets' + os.sep + 'jquery.js',
            'targets' + os.sep + 'modernizr.js']),
        ('icons', [
            # toolbar icons
            'icons' + os.sep + 'newpassage.png',
            'icons' + os.sep + 'zoomin.png',
            'icons' + os.sep + 'zoomout.png',
            'icons' + os.sep + 'zoomfit.png',
            'icons' + os.sep + 'zoom1.png',
            'icons' + os.sep + 'zoomfit.png',

            # other icons
            'icons' + os.sep + 'brokenemblem.png',
            'icons' + os.sep + 'externalemblem.png',
            'appicons' + os.sep + 'app.ico',
        ]),
    ],

    options = {
                  'py2exe': {
                        'dist_dir': 'dist' + os.sep + 'win32',
                        'bundle_files': 3,
                        'optimize': 2,
                        'ignores': ['_scproxy'],
                        'dll_excludes': ['w9xpopen.exe', 'MSVCP90.dll'],
                        'compressed': True,
                  }
    },
    zipfile = 'library.zip',
)

print 'Check the ./dist/win32 folder'

########NEW FILE########
__FILENAME__ = fseditframe
import sys, wx, wx.stc

class FullscreenEditFrame(wx.Frame):
    """
    This opens a modal fullscreen editor with some text. When the user's done,
    this calls the callback function passed to the constructor with the new text.

    A lot of the stuff dealing with wx.stc.StyledTextCtrl comes from:
    http://www.psychicorigami.com/2009/01/05/a-5k-python-fullscreen-text-editor/
    """

    def __init__(self, parent, app, frame = None, title = '', initialText = '', callback = lambda i: i):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = title, size = (400, 400))
        self.app = app
        self.callback = callback
        self.frame = frame
        self.cursorVisible = True

        # menu bar
        # this is never seen by the user,
        # but lets them hit ctrl-S to save

        menuBar = wx.MenuBar()
        menu = wx.Menu()
        menu.Append(wx.ID_SAVE, '&Save Story\tCtrl-S')
        self.Bind(wx.EVT_MENU, lambda e: self.frame.widget.parent.parent.save, id = wx.ID_SAVE)
        menuBar.Append(menu, 'Commands')
        self.SetMenuBar(menuBar)

        # margins

        self.marginPanel = wx.Panel(self)
        marginSizer = wx.BoxSizer(wx.VERTICAL)  # doesn't really matter
        self.marginPanel.SetSizer(marginSizer)

        # content

        self.panel = wx.Panel(self.marginPanel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        marginSizer.Add(self.panel, 1, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 100)

        # controls

        self.editCtrl = wx.stc.StyledTextCtrl(self.panel, style = wx.NO_BORDER | wx.TE_NO_VSCROLL | \
                                              wx.TE_MULTILINE | wx.TE_PROCESS_TAB)
        self.editCtrl.SetMargins(0, 0)
        self.editCtrl.SetMarginWidth(1, 0)
        self.editCtrl.SetWrapMode(wx.stc.STC_WRAP_WORD)
        self.editCtrl.SetText(initialText)
        self.editCtrl.SetUseHorizontalScrollBar(False)
        self.editCtrl.SetUseVerticalScrollBar(False)
        self.editCtrl.SetCaretPeriod(750)

        self.directions = wx.StaticText(self.panel, label = FullscreenEditFrame.DIRECTIONS, style = wx.ALIGN_CENTRE)
        labelFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        labelFont.SetPointSize(FullscreenEditFrame.LABEL_FONT_SIZE)
        self.directions.SetFont(labelFont)

        self.applyPrefs()
        sizer.Add(self.editCtrl, 1, flag = wx.EXPAND | wx.ALL)
        sizer.Add(self.directions, 0, flag = wx.TOP | wx.BOTTOM, border = 6)
        self.panel.SetSizer(sizer)

        # events

        self.Bind(wx.EVT_KEY_DOWN, self.keyListener)
        self.Bind(wx.EVT_MOTION, self.showCursor)
        self.editCtrl.Bind(wx.EVT_KEY_DOWN, self.keyListener)
        self.editCtrl.Bind(wx.EVT_MOTION, self.showCursor)

        self.editCtrl.SetFocus()
        self.editCtrl.SetSelection(-1, -1)
        self.SetIcon(self.app.icon)
        self.Show(True)
        self.ShowFullScreen(True)

    def close(self):
        self.callback(self.editCtrl.GetText())
        if sys.platform == 'darwin': self.ShowFullScreen(False)
        self.Close()

    def applyPrefs(self):
        """
        Applies user preferences to this frame.
        """
        editFont = wx.Font(self.app.config.ReadInt('fsFontSize'), wx.FONTFAMILY_MODERN, \
                           wx.FONTSTYLE_NORMAL, wx.NORMAL, False, self.app.config.Read('fsFontFace'))
        bgColor = self.app.config.Read('fsBgColor')
        textColor = self.app.config.Read('fsTextColor')
        lineHeight = self.app.config.ReadInt('fslineHeight') / float(100)

        self.panel.SetBackgroundColour(bgColor)
        self.marginPanel.SetBackgroundColour(bgColor)

        self.editCtrl.SetBackgroundColour(bgColor)
        self.editCtrl.SetForegroundColour(textColor)
        self.editCtrl.StyleSetBackground(wx.stc.STC_STYLE_DEFAULT, bgColor)
        self.editCtrl.SetCaretForeground(textColor)
        self.editCtrl.SetSelBackground(True, textColor)
        self.editCtrl.SetSelForeground(True, bgColor)

        defaultStyle = self.editCtrl.GetStyleAt(0)
        self.editCtrl.StyleSetForeground(defaultStyle, textColor)
        self.editCtrl.StyleSetBackground(defaultStyle, bgColor)
        self.editCtrl.StyleSetFont(defaultStyle, editFont)

        # we stuff a larger font into a style def we never use
        # to force line spacing

        editFont.SetPointSize(editFont.GetPointSize() * lineHeight)
        self.editCtrl.StyleSetFont(wx.stc.STC_STYLE_BRACELIGHT, editFont)

        self.directions.SetForegroundColour(textColor)

    def keyListener(self, event):
        """
        Listens for a key that indicates this frame should close; otherwise lets the event propagate.
        This also hides the mouse cursor; the showCursor method, bound to the mouse motion event,
        restores it when the user moves it.
        """
        key = event.GetKeyCode()

        if key == wx.WXK_F12:
            self.close()

        if key == wx.WXK_ESCAPE:
            self.close()
            self.frame.Destroy()

        self.hideCursor()
        event.Skip()

    def hideCursor(self, event = None):
        if self.cursorVisible:
            self.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))
            self.editCtrl.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))
            self.cursorVisible = False

    def showCursor(self, event = None):
        if not self.cursorVisible:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            self.editCtrl.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))
            self.cursorVisible = True

    DIRECTIONS = 'Press Escape to close this passage, F12 to leave fullscreen.'
    LABEL_FONT_SIZE = 10

########NEW FILE########
__FILENAME__ = geometry
"""
This module has basic utilities for working with wx.Rects
and Lines (which are tuples of wx.Points).
"""

import math, wx

def clipLineByRects(line, *rects):
    """
    Clips a line (e.g. an array of wx.Points) so it does
    not overlap any of the rects passed. The line must be
    the first parameter, but you may pass any number of rects.
    """
    result = line

    for rect in rects:
        rectLines = None
        for i in range(2):
            if rect.Contains(result[i]):
                intersection = lineRectIntersection(result, rect, excludeTrivial = True)
                if intersection:
                    result[i] = intersection
                    break
    return result

def endPointProjectedFrom(line, angle, distance):
    """
    Projects an endpoint from the second wx.Point of a line at
    a given angle and distance. The angle should be given in radians.
    """
    length = lineLength(line)
    if length == 0: return line[1]

    # taken from http://mathforum.org/library/drmath/view/54146.html

    lengthRatio = distance / lineLength(line)

    x = line[1].x - ((line[1].x - line[0].x) * math.cos(angle) - \
                     (line[1].y - line[0].y) * math.sin(angle)) * lengthRatio
    y = line[1].y - ((line[1].y - line[0].y) * math.cos(angle) + \
                     (line[1].x - line[0].x) * math.sin(angle)) * lengthRatio

    return wx.Point(x, y)

def pointsToRect(p1, p2):
    """
    Returns the smallest wx.Rect that encloses two points.
    """
    left = min(p1[0], p2[0])
    right = max(p1[0], p2[0])
    top = min(p1[1], p2[1])
    bottom = max(p1[1], p2[1])

    rect = wx.Rect(0, 0, 0, 0)
    rect.SetTopLeft((left, top))
    rect.SetBottomRight((right, bottom))

    return rect

def rectToLines(rect):
    """
    Converts a wx.Rect into an array of lines
    (e.g. tuples of wx.Points)
    """
    topLeft = rect.GetTopLeft()
    topRight = rect.GetTopRight()
    bottomLeft = rect.GetBottomLeft()
    bottomRight = rect.GetBottomRight()
    return (topLeft, topRight), (topLeft, bottomLeft), (topRight, bottomRight), \
           (bottomLeft, bottomRight)

def lineLength(line):
    """
    Returns the length of a line.
    """
    return math.sqrt((line[1].x - line[0].x) ** 2 + (line[1].y - line[0].y) ** 2)

def lineRectIntersection(line, rect, excludeTrivial = False):
    """
    Returns a wx.Point corresponding to where a line and a
    wx.Rect intersect. If they do not intersect, then None
    is returned. This returns the first intersection it happens
    to find, not all of them.

    By default, it will immediately return an endpoint if one of
    them is inside the rectangle. The excludeTrivial prevents
    this behavior.
    """

    # check for trivial case, where one point is inside the rect

    if not excludeTrivial:
        for i in range(2):
            if rect.Contains(line[i]): return line[i]

    # check for intersection with borders

    rectLines = rectToLines(rect)
    for rectLine in rectLines:
        intersection = lineIntersection(line, rectLine)
        if intersection: return intersection
    return None

def lineIntersection(line1, line2):
    """
    Returns a wx.Point corresponding to where two line
    segments intersect. If they do not intersect, then None
    is returned.
    """

    # this is translated from
    # http://workshop.evolutionzone.com/2007/09/10/code-2d-line-intersection/

    # distances of the two lines

    distX1 = line1[1].x - line1[0].x
    distX2 = line2[1].x - line2[0].x
    distY1 = line1[1].y - line1[0].y
    distY2 = line2[1].y - line2[0].y
    distX3 = line1[0].x - line2[0].x
    distY3 = line1[0].y - line2[0].y

    # length of the lines

    line1Length = math.sqrt(distX1 ** 2 + distY1 ** 2)
    line2Length = math.sqrt(distX2 ** 2 + distY2 ** 2)

    if line1Length == 0 or line2Length == 0: return None

    # angle between lines

    dotProduct = distX1 * distX2 + distY1 * distY2
    angle = dotProduct / (line1Length * line2Length)

    # check to see if lines are parallel

    if abs(angle) == 1:
        return None

    # find the intersection point
    # we cast the divisor as a float
    # to force uA and uB to be floats too

    divisor = float(distY2 * distX1 - distX2 * distY1)
    uA = (distX2 * distY3 - distY2 * distX3) / divisor
    uB = (distX1 * distY3 - distY1 * distX3) / divisor
    intersection = wx.Point(line1[0].x + uA * distX1, \
                            line1[0].y + uA * distY1)

    # find the combined length of the two segments
    # between intersection and line1's endpoints

    distX1 = intersection.x - line1[0].x
    distX2 = intersection.x - line1[1].x
    distY1 = intersection.y - line1[0].y
    distY2 = intersection.y - line1[1].y
    distLine1 = math.sqrt(distX1 ** 2 + distY1 ** 2) + \
                    math.sqrt(distX2 ** 2 + distY2 ** 2)

    # ... and then for line2

    distX1 = intersection.x - line2[0].x
    distX2 = intersection.x - line2[1].x
    distY1 = intersection.y - line2[0].y
    distY2 = intersection.y - line2[1].y
    distLine2 = math.sqrt(distX1 ** 2 + distY1 ** 2) + \
                    math.sqrt(distX2 ** 2 + distY2 ** 2)

    # if these two are the same, then we know
    # the intersection is actually on the line segments, and not in space
    #
    # I had to goose the accuracy down a lot :(

    if (abs(distLine1 - line1Length) < 0.2) and \
       (abs(distLine2 - line2Length) < 0.2):
        return intersection
    else:
        return None

########NEW FILE########
__FILENAME__ = header
import os, imp, re, tweeregex, tweelexer
from collections import OrderedDict
from random import shuffle

class Header(object):

    def __init__(self, id, path, builtinPath):
        self.id = id.lower()
        self.path = path
        self.label = id.capitalize()
        self.builtinPath = builtinPath

    def filesToEmbed(self):
        """Returns an Ordered Dictionary of file names to embed into the output.

        The item key is the label to look for within the output.
        The item value is the name of the file who's contents will be embedded into the output.

        Internal headers referring to files outside their folders should use
        the following form for paths: self.builtinPath + ...

        External headers must use the following form for paths: self.path + "filename.js"
        """
        return OrderedDict([
            ('"JONAH"', self.builtinPath + os.sep + 'jonah' + os.sep + 'code.js'),
            ('"SUGARCANE"', self.builtinPath + os.sep + 'sugarcane' + os.sep + 'code.js'),
            ('"ENGINE"', self.builtinPath + os.sep + 'engine.js')
        ])

    def storySettings(self):
        """
        Returns a list of StorySettings dictionaries.
        Alternatively, it could return a string saying that it isn't supported, and suggesting an alternative.
        """

        return [{
                "type": "checkbox",
                "name": "undo",
                "label": "Let the player undo moves",
                "desc": "In Sugarcane, this enables the browser's back button.\nIn Jonah, this lets the player click links in previous passages.",
                "default": "on"
            },{
                "type": "checkbox",
                "name": "bookmark",
                "label": "Let the player use passage bookmarks",
                "desc": "This enables the Bookmark links in Jonah and Sugarcane.\n(If the player can't undo, bookmarks are always disabled.)",
                "requires": "undo",
                "default": "on"
            },{
                "type": "checkbox",
                "name": "hash",
                "label": "Automatic URL hash updates",
                "desc": "The story's URL automatically updates, so that it always links to the \ncurrent passage. Naturally, this renders the bookmark link irrelevant.",
                "requires": "undo",
                "default": "off"
            },{
                "type": "checkbox",
                "name": "exitprompt",
                "label": "Prompt before closing or reloading the page",
                "desc": "In most browsers, this asks the player to confirm closing or reloading the \npage after they've made at least 1 move.",
                "default": "off"
            },{
                "type": "checkbox",
                "name": "blankcss",
                "label": "Don't use the Story Format's default CSS",
                "desc": "Removes most of the story format's CSS styling, so that you can\nwrite stylesheets without having to override the default styles.\n"
                        +"Individual stylesheets may force this on by containing the text 'blank stylesheet'",
                "default": "off"
            },{
                "type": "checkbox",
                "name": "obfuscate",
                "label": "Use ROT13 to obscure spoilers in the HTML source code?",
                "values": ("rot13", "off"),
                "default": "off"
            },{
                "type": "checkbox",
                "name": "jquery",
                "label": "Include the jQuery script library?",
                "desc": "This enables the jQuery() function and the $() shorthand.\nIndividual scripts may force this on by containing the text 'requires jQuery'.",
            },{
                "type": "checkbox",
                "name": "modernizr",
                "label": "Include the Modernizr script library?",
                "desc": "This adds CSS classes to the <html> element that can be used to write\nmore compatible CSS or scripts. See http://modernizr.com/docs for details.\nIndividual scripts/stylesheets may force this on by containing the\ntext 'requires Modernizr'.",
            }]

    def isEndTag(self, name, tag):
        """Return true if the name is equal to an endtag."""
        return (name == ('end' + tag))

    def nestedMacros(self):
        """Returns a list of macro names that support nesting."""
        return ['if', 'silently', 'nobr']
    
    def passageTitleColor(self, passage):
        """
        Returns a tuple pair of colours for a given passage's title.
        Colours can be HTML 1 hex strings like "#555753", or int triples (85, 87, 83)
        or wx.Colour objects.
        First is the normal colour, second is the Flat Design(TM) colour.
        """
        if passage.isScript():
            return ((89, 66, 28),(226, 170, 80))
        elif passage.isStylesheet():
            return ((111, 49, 83),(234, 123, 184))
        elif passage.isInfoPassage():
            return ((28, 89, 74), (41, 214, 113))
        elif passage.title == "Start":
            return ("#4ca333", "#4bdb24")
        
    def invisiblePassageTags(self):
        """Returns a list of passage tags which, for whatever reason, shouldn't be displayed on the Story Map."""
        return frozenset()
    
    def passageChecks(self):
        """
        Returns tuple of list of functions to perform on the passage whenever it's closed.
        The main tuple's three lists are: Twine checks, then Stylesheet checks, then Script checks.
        """
        
        """
        Twine code checks
        Each function should return an iterable (or be a generator) of tuples containing:
            * warning message string,
            * None, or a tuple:
                * start index where to begin substitution
                * string to substitute
                * end index
        """
        def checkUnmatchedMacro(tag, start, end, style, passage=None):
            if style == tweelexer.TweeLexer.BAD_MACRO:
                matchKind = "start" if "end" in tag else "end"
                yield ("The macro tag " + tag + "\ndoes not have a matching " + matchKind + " tag.", None)
        
        def checkInequalityExpression(tag, start, end, style, passage=None):
            if style == tweelexer.TweeLexer.MACRO:
                r = re.search(r"\s+((and|or|\|\||&&)\s+([gl]te?|is|n?eq|(?:[=!<]|>(?!>))=?))\s+" + tweeregex.UNQUOTED_REGEX, tag)
                if r:
                    yield (tag + ' contains "' + r.group(1) + '", which isn\'t valid code.\n'
                            + 'There should probably be an expression, or a variable, between "' + r.group(2) + '" and "' + r.group(3) + '".', None)
        
        def checkIfMacro(tag, start, end, style, passage=None):
            if style == tweelexer.TweeLexer.MACRO:
                ifMacro = re.search(tweeregex.MACRO_REGEX.replace(r"([^>\s]+)", r"(if\b|else ?if\b)"), tag)
                if ifMacro:
                    # Check that the single = assignment isn't present in an if/elseif condition.
                    r = re.search(r"([^=<>!~])(=(?!=))(.?)" + tweeregex.UNQUOTED_REGEX, tag)
                    if r:
                        warning = tag + " contains the = operator.\nYou must use 'is' instead of '=' in <<if>> and <<else if>> tags."
                        insertion = "is"
                        if r.group(1) != " ":
                            insertion = " "+insertion
                        if r.group(3) != " ":
                            insertion += " "
                        # Return the warning message, and a 3-tuple consisting of
                        # start index of replacement, the replacement, end index of replacement
                        yield (warning, (start+r.start(2), insertion, start+r.end(2)))

        def checkHTTPSpelling(tag, start, end, style, passage=None):
            if style == tweelexer.TweeLexer.EXTERNAL:
                # Corrects the incorrect spellings "http//" and "http:/" (and their https variants)
                regex = re.search(r"\bhttp(s?)(?:\/\/|\:\/(?=[^\/]))", tag)
                if regex:
                    yield (r"You appear to have misspelled 'http" + regex.group(1) + "://'.",
                            (start+regex.start(0), "http" + regex.group(1) + "://", start+regex.end(0)))
            
        """
        Script checks
        """
        def checkScriptTagsInScriptPassage(passage):
            # Check that a script passage does not contain "<script type='text/javascript'>" style tags.
            ret = []
            scriptTags = re.finditer(r"(?:</?script\b[^>]*>)" + tweeregex.UNQUOTED_REGEX, passage.text)
            for scriptTag in scriptTags:
                warning = "This script contains " + scriptTag.group(0) + ".\nScript passages should only contain Javascript code, not raw HTML."
                ret.append((warning, (scriptTag.start(0), "", scriptTag.end(0))))
            return ret
        
        return ([checkUnmatchedMacro, checkInequalityExpression, checkIfMacro, checkHTTPSpelling],[],[checkScriptTagsInScriptPassage])

    @staticmethod
    def factory(type, path, builtinPath):
        header_def = path + type + '.py'
        if os.access(header_def, os.R_OK):
            py_mod = imp.load_source(type, header_def)
            obj = py_mod.Header(type, path, builtinPath)
        else:
            obj = Header(type, path, builtinPath)
        return obj


########NEW FILE########
__FILENAME__ = images
"""
A module for handling base64 encoded images and other assets.
"""

import sys, cStringIO, wx, re

def AddURIPrefix(text, mimeType):
    """ Adds the Data URI MIME prefix to the base64 data"""
    # SVG MIME-type is the same for both images and fonts
    mimeType = mimeType.lower()
    if mimeType in 'gif|jpg|jpeg|png|webp|svg':
        mimeGroup = "image/"
    elif mimeType == 'woff':
        mimeGroup = "application/font-"
    elif mimeType in 'ttf|otf':
        mimeGroup = "application/x-font-"
    else:
        mimeGroup = "application/octet-stream"

    # Correct certain MIME types
    if mimeType == "jpg":
        mimeType == "jpeg"
    elif mimeType == "svg":
        mimeType += "+xml"
    return "data:" + mimeGroup + mimeType + ";base64," + text

def RemoveURIPrefix(text):
    """Removes the Data URI part of the base64 data"""
    index = text.find(';base64,')
    return text[index+8:] if index else text

def Base64ToBitmap(text):
    """Converts the base64 data URI back into a bitmap"""
    try:
        # Remove data URI prefix and MIME type
        text = RemoveURIPrefix(text)
        # Convert to bitmap
        imgData = text.decode('base64')
        stream = cStringIO.StringIO(imgData)
        return wx.BitmapFromImage(wx.ImageFromStream(stream))
    except:
        pass

def BitmapToBase64PNG(bmp):
    img = bmp.ConvertToImage()
    # "PngZL" in wxPython 2.9 is equivalent to wx.IMAGE_OPTION_PNG_COMPRESSION_LEVEL in wxPython Phoenix
    img.SetOptionInt("PngZL", 9)
    stream = cStringIO.StringIO()
    try:
        img.SaveStream(stream, wx.BITMAP_TYPE_PNG)
        return "data:image/png;base64," + stream.getvalue().encode('base64')
    except:
        pass

def GetImageType(text):
    """Returns the part of the Data URI's MIME type that refers to the type of the image."""
    # By using (\w+), "svg+xml" becomes "svg"
    search = re.search(r"data:image/(\w+)", text)
    if (search):
        return "." + search.group(1)
    #Fallback
    search = re.search(r"application:x-(\w+)", text)
    if (search):
        return "." + search.group(1)
    return ""

########NEW FILE########
__FILENAME__ = metrics
"""
This module offers advice on how to size the UI appropriately
for the OS we're running on.
"""

import sys

def size(type):
    """
    Returns the number of pixels to use for a certain context.
    Recognized keywords:

    windowBorder - around the edges of a window
    buttonSpace - between buttons
    relatedControls - between related controls
    unrelatedControls - between unrelated controls
    focusRing - space to leave to allow for focus rings
    fontMin - smallest font size to ever use
    fontMax - largest font size to use, as a recommendation
    widgetTitle - starting font size for widget titles, as a recommendation
    editorBody - starting font size for body editor, as a recommendation
    fsEditorBody - starting font size for fullscreen editor, as a recommendation
    """
    if type == 'windowBorder':
        if sys.platform == 'win32': return 11
        if sys.platform == 'darwin': return 16
        return 13

    if type == 'relatedControls':
        if sys.platform == 'win32': return 7
        if sys.platform == 'darwin': return 6
        return 9

    if type == 'unrelatedControls':
        if sys.platform == 'win32': return 11
        if sys.platform == 'darwin': return 12
        return 9

    if type == 'buttonSpace':
        if sys.platform == 'win32': return 7
        if sys.platform == 'darwin': return 12
        return 9

    if type == 'focusRing':
        return 3

    if type == 'fontMin':
        if sys.platform == 'win32': return 8
        if sys.platform == 'darwin': return 11

    if type == 'fontMax':
        return 24

    if type == 'widgetTitle':
        if sys.platform == 'win32': return 9
        if sys.platform == 'darwin': return 13
        return 11

    if type == 'editorBody':
        if sys.platform == 'win32': return 11
        if sys.platform == 'darwin': return 13
        return 11

    if type == 'fsEditorBody':
        if sys.platform == 'win32': return 16
        if sys.platform == 'darwin': return 20
        return 11

def face(type):
    """
    Returns a font face name.
    Recognized keywords:

    sans - sans-serif
    mono - monospaced
    """
    if type == 'sans':
        if sys.platform == 'win32': return 'Arial'
        if sys.platform == 'darwin': return 'Helvetica'
        return 'Sans'

    if type == 'mono':
        if sys.platform == 'win32': return 'Consolas'
        if sys.platform == 'darwin': return 'Monaco'
        return 'Fixed'

    if type == 'mono2':
        if sys.platform in ['win32', 'darwin']: return 'Courier New'
        return 'Fixed'

########NEW FILE########
__FILENAME__ = passageframe
import sys, os, re, types, threading, wx, wx.lib.scrolledpanel, wx.animate, base64, time, tweeregex
import metrics, images
from version import versionString
from tweelexer import TweeLexer
from tweestyler import TweeStyler
from tiddlywiki import TiddlyWiki
from passagesearchframe import PassageSearchFrame
from fseditframe import FullscreenEditFrame
import cStringIO

class PassageFrame(wx.Frame):
    """
    A PassageFrame is a window that allows the user to change the contents
    of a passage. This must be paired with a PassageWidget; it gets to the
    underlying passage via it, and also notifies it of changes made here.

    This doesn't require the user to save their changes -- as they make
    changes, they are automatically updated everywhere.

    nb: This does not make use of wx.stc's built-in find/replace functions.
    This is partially for user interface reasons, as find/replace at the
    StoryPanel level uses Python regexps, not Scintilla ones. It's also
    because SearchPanel and ReplacePanel hand back regexps, so we wouldn't
    know what flags to pass to wx.stc.
    """

    def __init__(self, parent, widget, app):
        self.widget = widget
        self.app = app
        self.syncTimer = None
        self.lastFindRegexp = None
        self.lastFindFlags = None
        self.usingLexer = self.LEXER_NORMAL
        self.titleInvalid = False

        wx.Frame.__init__(self, parent, wx.ID_ANY, title = 'Untitled Passage - ' + self.app.NAME + ' ' + versionString, \
                          size = PassageFrame.DEFAULT_SIZE)

        # Passage menu

        passageMenu = wx.Menu()

        passageMenu.Append(PassageFrame.PASSAGE_EDIT_SELECTION, 'Create &Link From Selection\tCtrl-L')
        self.Bind(wx.EVT_MENU, self.editSelection, id = PassageFrame.PASSAGE_EDIT_SELECTION)

        self.outLinksMenu = wx.Menu()
        self.outLinksMenuTitle = passageMenu.AppendMenu(wx.ID_ANY, 'Outgoing Links', self.outLinksMenu)
        self.inLinksMenu = wx.Menu()
        self.inLinksMenuTitle = passageMenu.AppendMenu(wx.ID_ANY, 'Incoming Links', self.inLinksMenu)
        self.brokenLinksMenu = wx.Menu()
        self.brokenLinksMenuTitle = passageMenu.AppendMenu(wx.ID_ANY, 'Broken Links', self.brokenLinksMenu)

        passageMenu.AppendSeparator()

        passageMenu.Append(wx.ID_SAVE, '&Save Story\tCtrl-S')
        self.Bind(wx.EVT_MENU, self.widget.parent.parent.save, id = wx.ID_SAVE)
        
        passageMenu.Append(PassageFrame.PASSAGE_VERIFY, '&Verify Passage\tCtrl-E')
        self.Bind(wx.EVT_MENU, lambda e: (self.widget.verifyPassage(self), self.offerAssistance()),\
                  id = PassageFrame.PASSAGE_VERIFY)
        
        passageMenu.Append(PassageFrame.PASSAGE_TEST_HERE, '&Test Play From Here\tCtrl-T')
        self.Bind(wx.EVT_MENU, lambda e: self.widget.parent.parent.testBuild(e, startAt = self.widget.passage.title),\
                  id = PassageFrame.PASSAGE_TEST_HERE)
        
        passageMenu.Append(PassageFrame.PASSAGE_REBUILD_STORY, '&Rebuild Story\tCtrl-R')
        self.Bind(wx.EVT_MENU, self.widget.parent.parent.rebuild, id = PassageFrame.PASSAGE_REBUILD_STORY)

        passageMenu.AppendSeparator()

        passageMenu.Append(PassageFrame.PASSAGE_FULLSCREEN, '&Fullscreen View\tF12')
        self.Bind(wx.EVT_MENU, self.openFullscreen, id = PassageFrame.PASSAGE_FULLSCREEN)

        passageMenu.Append(wx.ID_CLOSE, '&Close Passage\tCtrl-W')
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), id = wx.ID_CLOSE)

        # Edit menu

        editMenu = wx.Menu()

        editMenu.Append(wx.ID_UNDO, '&Undo\tCtrl-Z')
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Undo(), id = wx.ID_UNDO)

        if sys.platform == 'darwin':
            shortcut = 'Ctrl-Shift-Z'
        else:
            shortcut = 'Ctrl-Y'

        editMenu.Append(wx.ID_REDO, '&Redo\t' + shortcut)
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Redo(), id = wx.ID_REDO)

        editMenu.AppendSeparator()

        editMenu.Append(wx.ID_CUT, 'Cu&t\tCtrl-X')
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Cut(), id = wx.ID_CUT)

        editMenu.Append(wx.ID_COPY, '&Copy\tCtrl-C')
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Copy(), id = wx.ID_COPY)

        editMenu.Append(wx.ID_PASTE, '&Paste\tCtrl-V')
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Paste(), id = wx.ID_PASTE)

        editMenu.Append(wx.ID_SELECTALL, 'Select &All\tCtrl-A')
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.SelectAll(), id = wx.ID_SELECTALL)

        editMenu.AppendSeparator()

        editMenu.Append(wx.ID_FIND, '&Find...\tCtrl-F')
        self.Bind(wx.EVT_MENU, lambda e: self.showSearchFrame(PassageSearchFrame.FIND_TAB), id = wx.ID_FIND)

        editMenu.Append(PassageFrame.EDIT_FIND_NEXT, 'Find &Next\tCtrl-G')
        self.Bind(wx.EVT_MENU, self.findNextRegexp, id = PassageFrame.EDIT_FIND_NEXT)

        if sys.platform == 'darwin':
            shortcut = 'Ctrl-Shift-H'
        else:
            shortcut = 'Ctrl-H'

        editMenu.Append(wx.ID_REPLACE, '&Replace...\t' + shortcut)
        self.Bind(wx.EVT_MENU, lambda e: self.showSearchFrame(PassageSearchFrame.REPLACE_TAB), id = wx.ID_REPLACE)

        # help menu

        helpMenu = wx.Menu()

        if (self.widget.passage.isStylesheet()):
            helpMenu.Append(PassageFrame.HELP1, 'About Stylesheets')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/stylesheet'), id = PassageFrame.HELP1)
        elif (self.widget.passage.isScript()):
            helpMenu.Append(PassageFrame.HELP1, 'About Scripts')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/script'), id = PassageFrame.HELP1)
        else:
            helpMenu.Append(PassageFrame.HELP1, 'About Passages')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/passage'), id = PassageFrame.HELP1)
    
            helpMenu.Append(PassageFrame.HELP2, 'About Text Syntax')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/syntax'), id = PassageFrame.HELP2)
    
            helpMenu.Append(PassageFrame.HELP3, 'About Links')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/link'), id = PassageFrame.HELP3)
            
            helpMenu.Append(PassageFrame.HELP4, 'About Macros')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/macro'), id = PassageFrame.HELP4)
    
            helpMenu.Append(PassageFrame.HELP5, 'About Tags')
            self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/tag'), id = PassageFrame.HELP5)

        # menus

        self.menus = wx.MenuBar()
        self.menus.Append(passageMenu, '&Passage')
        self.menus.Append(editMenu, '&Edit')
        self.menus.Append(helpMenu, '&Help')
        self.SetMenuBar(self.menus)

        # controls

        self.panel = wx.Panel(self)
        allSizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(allSizer)

        # title/tag controls

        self.topControls = wx.Panel(self.panel)
        topSizer = wx.FlexGridSizer(3, 2, metrics.size('relatedControls'), metrics.size('relatedControls'))

        self.titleLabel = wx.StaticText(self.topControls, style = wx.ALIGN_RIGHT, label = PassageFrame.TITLE_LABEL)
        self.titleInput = wx.TextCtrl(self.topControls)
        tagsLabel = wx.StaticText(self.topControls, style = wx.ALIGN_RIGHT, label = PassageFrame.TAGS_LABEL)
        self.tagsInput = wx.TextCtrl(self.topControls)
        topSizer.Add(self.titleLabel, 0, flag = wx.ALL, border = metrics.size('focusRing'))
        topSizer.Add(self.titleInput, 1, flag = wx.EXPAND | wx.ALL, border = metrics.size('focusRing'))
        topSizer.Add(tagsLabel, 0, flag = wx.ALL, border = metrics.size('focusRing'))
        topSizer.Add(self.tagsInput, 1, flag = wx.EXPAND | wx.ALL, border = metrics.size('focusRing'))
        topSizer.AddGrowableCol(1, 1)
        self.topControls.SetSizer(topSizer)

        # body text

        self.bodyInput = wx.stc.StyledTextCtrl(self.panel, style = wx.TE_PROCESS_TAB | wx.BORDER_SUNKEN)
        self.bodyInput.SetUseHorizontalScrollBar(False)
        self.bodyInput.SetMargins(8, 8)
        self.bodyInput.SetMarginWidth(1, 0)
        self.bodyInput.SetTabWidth(4)
        self.bodyInput.SetWrapMode(wx.stc.STC_WRAP_WORD)
        self.bodyInput.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.bodyInput.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        self.bodyInput.SetFocus()

        # The default keyboard shortcuts for StyledTextCtrl are
        # nonstandard on Mac OS X
        if sys.platform == "darwin":
            # cmd-left/right to move to beginning/end of line
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_LEFT, wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_HOMEDISPLAY)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_LEFT, wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_HOMEDISPLAYEXTEND)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_RIGHT, wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_LINEENDDISPLAY)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_RIGHT, wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_LINEENDDISPLAYEXTEND)
            # opt-left/right to move forward/back a word
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_LEFT, wx.stc.STC_SCMOD_ALT, wx.stc.STC_CMD_WORDLEFT)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_LEFT, wx.stc.STC_SCMOD_ALT | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_WORDLEFTEXTEND)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_RIGHT, wx.stc.STC_SCMOD_ALT, wx.stc.STC_CMD_WORDRIGHT)
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_RIGHT, wx.stc.STC_SCMOD_ALT | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_WORDRIGHTEXTEND)
            # cmd-delete to delete from the cursor to beginning of line
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_BACK, wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_DELLINELEFT)
            # opt-delete to delete the previous/current word
            self.bodyInput.CmdKeyAssign(wx.stc.STC_KEY_BACK, wx.stc.STC_SCMOD_ALT, wx.stc.STC_CMD_DELWORDLEFT)
            # cmd-shift-z to redo
            self.bodyInput.CmdKeyAssign(ord('Z'), wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_REDO)

        # final layout

        allSizer.Add(self.topControls, flag = wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border = metrics.size('windowBorder'))
        allSizer.Add(self.bodyInput, proportion = 1, flag = wx.TOP | wx.EXPAND, border = metrics.size('relatedControls'))
        self.lexer = TweeStyler(self.bodyInput, self)
        self.applyPrefs()
        self.syncInputs()
        self.bodyInput.EmptyUndoBuffer()
        self.updateSubmenus()
        self.setLexer()

        # event bindings
        # we need to do this AFTER setting up initial values

        self.titleInput.Bind(wx.EVT_TEXT, self.syncPassage)
        self.tagsInput.Bind(wx.EVT_TEXT, self.syncPassage)
        self.bodyInput.Bind(wx.stc.EVT_STC_CHANGE, self.syncPassage)
        self.bodyInput.Bind(wx.stc.EVT_STC_START_DRAG, self.prepDrag)
        self.Bind(wx.EVT_CLOSE, self.closeEditor)
        self.Bind(wx.EVT_MENU_OPEN, self.updateSubmenus)
        self.Bind(wx.EVT_UPDATE_UI, self.updateUI)

        if not re.match('Untitled Passage \d+', self.widget.passage.title):
            self.bodyInput.SetFocus()
            self.bodyInput.SetSelection(-1, -1)

        # Hack to force titles (>18 char) to display correctly.
        # NOTE: stops working if moved above bodyInput code. 
        self.titleInput.SetInsertionPoint(0)

        self.SetIcon(self.app.icon)
        self.Show(True)

    def title(self, title = None):
        if not title:
            title = self.widget.passage.title
        return title + ' - ' + self.widget.parent.parent.title + ' - ' + self.app.NAME + ' ' + versionString
    
    def syncInputs(self):
        """Updates the inputs based on the passage's state."""
        self.titleInput.SetValue(self.widget.passage.title)
        self.bodyInput.SetText(self.widget.passage.text)

        tags = ''

        for tag in self.widget.passage.tags:
            tags += tag + ' '

        self.tagsInput.SetValue(tags)
        self.SetTitle(self.title())

    def syncPassage(self, event = None):
        """Updates the passage based on the inputs; asks our matching widget to repaint."""
        title = self.titleInput.GetValue() if len(self.titleInput.GetValue()) > 0 else ""
        title = title.replace('\n','')

        def error():
           self.titleInput.SetBackgroundColour((240,130,130))
           self.titleInput.Refresh()
           self.titleInvalid = True

        if title:
        # Check for title conflict
            otherTitled = self.widget.parent.findWidget(title)
            if otherTitled and otherTitled != self.widget:
                self.titleLabel.SetLabel("Title is already in use!")
                error()
            elif self.widget.parent.includedPassageExists(title):
                self.titleLabel.SetLabel("Used by a StoryIncludes file.")
                error()
            elif "|" in title or "]" in title:
                self.titleLabel.SetLabel("No | or ] symbols allowed!")
                error()
            elif title == "StorySettings":
                self.titleLabel.SetLabel("That title is reserved.")
                error()
            else:
                if self.titleInvalid:
                    self.titleLabel.SetLabel(self.TITLE_LABEL)
                    self.titleInput.SetBackgroundColour((255,255,255))
                    self.titleInput.Refresh()
                    self.titleInvalid = True
                self.widget.passage.title = title

        # Set body text
        self.widget.passage.text = self.bodyInput.GetText()
        self.widget.passage.modified = time.localtime()
        # Preserve the special (uneditable) tags
        self.widget.passage.tags = []
        self.widget.clearPaintCache()

        for tag in self.tagsInput.GetValue().split(' '):
            if tag != '' and tag not in TiddlyWiki.SPECIAL_TAGS:
                self.widget.passage.tags.append(tag)
            if tag == "StoryIncludes" and self.widget.parent.parent.autobuildmenuitem.IsChecked():
                self.widget.parent.parent.autoBuildStart();

        self.SetTitle(self.title())

        # immediately mark the story dirty

        self.widget.parent.parent.setDirty(True)

        # reposition if changed size
        self.widget.findSpace()

        # reset redraw timer

        def reallySync(self):
            try:
                self.widget.parent.Refresh()
            except:
                pass

        if (self.syncTimer):
            self.syncTimer.cancel()

        self.syncTimer = threading.Timer(PassageFrame.PARENT_SYNC_DELAY, reallySync, [self], {})
        self.syncTimer.start()

        # update links/displays lists
        self.widget.passage.update()

        # change our lexer as necessary

        self.setLexer()

    def openFullscreen(self, event = None):
        """Opens a FullscreenEditFrame for this passage's body text."""
        self.Hide()
        self.fullscreen = FullscreenEditFrame(None, self.app, \
                                              title = self.title(), \
                                              initialText = self.widget.passage.text, \
                                              callback = self.setBodyText, frame = self)
        
    def offerAssistance(self):
        """
        Offer to fulfill certain incomplete tasks evident from the state of the passage text.
        (Technically, none of this needs to be on passageFrame instead of passageWidget.)
        """
        
        # Offer to create passage for broken links
        if self.app.config.ReadBool('createPassagePrompt'):
            brokens = links = filter(lambda text: TweeLexer.linkStyle(text) == TweeLexer.BAD_LINK, self.widget.getBrokenLinks())
            if brokens :
                if len(brokens) > 1:
                    brokenmsg = 'create ' + str(len(brokens)) + ' new passages to match these broken links?'
                else:
                    brokenmsg = 'create the passage "' + brokens[0] + '"?'
                dialog = wx.MessageDialog(self, 'Do you want to ' + brokenmsg, 'Create Passages', \
                                                  wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT)
                check = dialog.ShowModal()
                if check == wx.ID_YES:
                    for title in brokens:
                        self.widget.parent.newWidget(title = title, pos = self.widget.parent.toPixels (self.widget.pos))
                elif check == wx.ID_CANCEL:
                    return
        
        # Offer to import external images
        if self.app.config.ReadBool('importImagePrompt'):
            regex = tweeregex.EXTERNAL_IMAGE_REGEX
            externalimages = re.finditer(regex, self.widget.passage.text)
            check = None
            downloadedurls = {}
            storyframe = self.widget.parent.parent
            for img in externalimages:
                if not check:
                    dialog = wx.MessageDialog(self, 'Do you want to import the image files linked\nin this passage into the story file?', 'Import Images', \
                                                  wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT);
                    check = dialog.ShowModal()
                    if check == wx.ID_NO:
                        break  
                    elif check == wx.ID_CANCEL:
                        return
                # Download the image if it's at an absolute URL
                imgurl = img.group(4) or img.group(7)
                if not imgurl:
                    continue
                # If we've downloaded it before, don't do it again
                if imgurl not in downloadedurls:
                    # Internet image, or local image?
                    if any(imgurl.startswith(t) for t in ['http://', 'https://', 'ftp://']):
                        imgpassagename = storyframe.importImageURL(imgurl, showdialog=False)
                    else:
                        imgpassagename = storyframe.importImageFile(storyframe.getLocalDir()+os.sep+imgurl, showdialog=False)
                    if not imgpassagename:
                        continue
                    downloadedurls[imgurl] = imgpassagename
            
            # Replace all found images
            for old, new in downloadedurls.iteritems():
                self.widget.passage.text = re.sub(regex.replace(tweeregex.IMAGE_FILENAME_REGEX, re.escape(old)),
                                                  lambda m: m.group(0).replace(old, new), self.widget.passage.text)
        
        self.bodyInput.SetText(self.widget.passage.text)
        
    def closeEditor(self, event = None):
        """
        Do extra stuff on closing the editor
        """
        #Closes this editor's fullscreen counterpart, if any.
        try: self.fullscreen.Destroy()
        except: pass
        
        # Show warnings, do replacements
        if self.app.config.ReadBool('passageWarnings'):
            if self.widget.verifyPassage(self) == -1: return
        
        # Do help    
        self.offerAssistance()
        
        self.widget.passage.update()
        event.Skip()

    def openOtherEditor(self, event = None, title = None):
        """
        Opens another passage for editing. If it does not exist, then
        it creates it next to this one and then opens it. You may pass
        this a string title OR an event. If you pass an event, it presumes
        it is a wx.CommandEvent, and uses the exact text of the menu as the title.
        """

        # we seem to be receiving CommandEvents, not MenuEvents,
        # so we can only see menu item IDs
        # unfortunately all our menu items are dynamically generated
        # so we gotta work our way back to a menu name

        if not title: title = self.menus.FindItemById(event.GetId()).GetLabel()
        found = False

        # check if the passage already exists

        editingWidget = self.widget.parent.findWidget(title = title)

        if not editingWidget:
            editingWidget = self.widget.parent.newWidget(title = title, pos = self.widget.parent.toPixels (self.widget.pos))

        editingWidget.openEditor()

    def showSearchFrame(self, type):
        """
        Shows a PassageSearchFrame for this frame, creating it if need be.
        The type parameter should be one of the constants defined in
        PassageSearchFrame, e.g. FIND_TAB or REPLACE_TAB.
        """
        if (not hasattr(self, 'searchFrame')):
            self.searchFrame = PassageSearchFrame(self, self, self.app, type)
        else:
            try:
                self.searchFrame.Raise()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'searchFrame')
                self.showSearchFrame(type)

    def setBodyText(self, text):
        """Changes the body text field directly."""
        self.bodyInput.SetText(text)
        self.Show(True)

    def prepDrag(self, event):
        """
        Tells our StoryPanel about us so that it can tell us what to do in response to
        dropping some text into it.
        """
        event.SetDragAllowMove(True)
        self.widget.parent.textDragSource = self

    def getSelection(self):
        """
        Returns the beginning and end of the selection as a tuple.
        """
        return self.bodyInput.GetSelection()

    def getSelectedText(self):
        """
        Returns the text currently selected.
        """
        return self.bodyInput.GetSelectedText()

    def setSelection(self, range):
        """
        Changes the current selection to the range passed.
        """
        self.bodyInput.SetSelection(range[0], range[1])

    def editSelection(self, event = None):
        """
        If the selection isn't already double-bracketed, then brackets are added.
        If a passage with the selection title doesn't exist, it is created.
        Finally, an editor is opened for the passage.
        """
        rawSelection = self.bodyInput.GetSelectedText()
        title = self.stripCrud(rawSelection)
        if not re.match(r'^\[\[.*\]\]$', rawSelection): self.linkSelection()
        self.openOtherEditor(title = title)
        self.updateSubmenus()

    def linkSelection(self):
        """Transforms the selection into a link by surrounding it with double brackets."""
        selStart = self.bodyInput.GetSelectionStart()
        selEnd = self.bodyInput.GetSelectionEnd()
        self.bodyInput.SetSelection(selStart, selEnd)
        self.bodyInput.ReplaceSelection("[["+self.bodyInput.GetSelectedText()+"]]")

    def findRegexp(self, regexp, flags):
        """
        Selects a regexp in the body text.
        """
        self.lastFindRegexp = regexp
        self.lastFindFlags = flags

        # find the beginning of our search

        text = self.bodyInput.GetText()
        oldSelection = self.bodyInput.GetSelection()

        # try past the selection

        match = re.search(regexp, text[oldSelection[1]:], flags)
        if match:
            self.bodyInput.SetSelection(match.start() + oldSelection[1], match.end() + oldSelection[1])
        else:
            # try before the selection
            match = re.search(regexp, text[:oldSelection[1]], flags)
            if match:
                self.bodyInput.SetSelection(match.start(), match.end())
            else:
                # give up
                dialog = wx.MessageDialog(self, 'The text you entered was not found in this passage.', \
                                          'Not Found', wx.ICON_INFORMATION | wx.OK)
                dialog.ShowModal()

    def findNextRegexp(self, event = None):
        """
        Performs a search for the last regexp that was searched for.
        """
        self.findRegexp(self.lastFindRegexp, self.lastFindFlags)

    def replaceOneRegexp(self, findRegexp, flags, replaceRegexp):
        """
        If the current selection matches the search regexp, a replacement
        is made. Otherwise, it calls findRegexp().
        """
        compiledRegexp = re.compile(findRegexp, flags)
        selectedText = self.bodyInput.GetSelectedText()
        match = re.match(findRegexp, selectedText, flags)

        if match and match.endpos == len(selectedText):
            oldStart = self.bodyInput.GetSelectionStart()
            newText = re.sub(compiledRegexp, replaceRegexp, selectedText)
            self.bodyInput.ReplaceSelection(newText)
            self.bodyInput.SetSelection(oldStart, oldStart + len(newText))
        else:
            # look for the next instance
            self.findRegexp(findRegexp, flags)

    def replaceAllRegexps(self, findRegexp, flags, replaceRegexp):
        """
        Replaces all instances of text in the body text and
        shows the user an alert about how many replacements
        were made.
        """
        replacements = 0
        compiledRegexp = re.compile(findRegexp, flags)

        newText, replacements = re.subn(compiledRegexp, replaceRegexp, self.bodyInput.GetText())
        if replacements > 0: self.bodyInput.SetText(newText)

        message = '%d replacement' % replacements
        if replacements != 1:
            message += 's were '
        else:
            message += ' was '
        message += 'made in this passage.'

        dialog = wx.MessageDialog(self, message, 'Replace Complete', wx.ICON_INFORMATION | wx.OK)
        dialog.ShowModal()

    def stripCrud(self, text):
        """Strips extraneous crud from around text, likely a partial selection of a link."""
        return text.strip(""" "'<>[]""")

    def setCodeLexer(self, css = False):
        """Basic CSS highlighting"""
        monoFont = wx.Font(self.app.config.ReadInt('monospaceFontSize'), wx.MODERN, wx.NORMAL, \
                           wx.NORMAL, False, self.app.config.Read('monospaceFontFace'))
        body = self.bodyInput
        body.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, monoFont);
        body.StyleClearAll()
        if css:
            for i in range(1,17):
                body.StyleSetFont(i, monoFont)
            body.StyleSetForeground(wx.stc.STC_CSS_IMPORTANT, TweeStyler.MACRO_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_COMMENT, TweeStyler.COMMENT_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_ATTRIBUTE, TweeStyler.GOOD_LINK_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_CLASS, TweeStyler.MARKUP_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_ID, TweeStyler.MARKUP_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_TAG, TweeStyler.PARAM_BOOL_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_PSEUDOCLASS, TweeStyler.EXTERNAL_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_UNKNOWN_PSEUDOCLASS, TweeStyler.EXTERNAL_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_DIRECTIVE, TweeStyler.PARAM_VAR_COLOR);
            body.StyleSetForeground(wx.stc.STC_CSS_UNKNOWN_IDENTIFIER, TweeStyler.GOOD_LINK_COLOR);

            for i in [wx.stc.STC_CSS_CLASS, wx.stc.STC_CSS_ID, wx.stc.STC_CSS_TAG,
                      wx.stc.STC_CSS_PSEUDOCLASS, wx.stc.STC_CSS_OPERATOR, wx.stc.STC_CSS_IMPORTANT,
                      wx.stc.STC_CSS_UNKNOWN_PSEUDOCLASS, wx.stc.STC_CSS_DIRECTIVE]:
                body.StyleSetBold(i, True)

    def setLexer(self):
        """
        Sets our custom lexer for the body input so long as the passage
        is part of the story.
        """
        oldLexing = self.usingLexer

        if self.widget.passage.isStylesheet():
            if oldLexing != self.LEXER_CSS:
                self.setCodeLexer(css = True)
                self.usingLexer = self.LEXER_CSS
                self.bodyInput.SetLexer(wx.stc.STC_LEX_CSS)
        elif not self.widget.passage.isStoryText() and not self.widget.passage.isAnnotation():
            if oldLexing != self.LEXER_NONE:
                self.usingLexer = self.LEXER_NONE
                self.setCodeLexer()
                self.bodyInput.SetLexer(wx.stc.STC_LEX_NULL)
        elif oldLexing != self.LEXER_NORMAL:
            self.usingLexer = self.LEXER_NORMAL
            self.bodyInput.SetLexer(wx.stc.STC_LEX_CONTAINER)

        if oldLexing != self.usingLexer:
            if self.usingLexer == self.LEXER_NORMAL:
                self.lexer.initStyles()
            self.bodyInput.Colourise(0, len(self.bodyInput.GetText()))

    def updateUI(self, event):
        """Updates menus."""

        # basic edit menus

        undoItem = self.menus.FindItemById(wx.ID_UNDO)
        undoItem.Enable(self.bodyInput.CanUndo())

        redoItem = self.menus.FindItemById(wx.ID_REDO)
        redoItem.Enable(self.bodyInput.CanRedo())

        hasSelection = self.bodyInput.GetSelectedText() != ''

        cutItem = self.menus.FindItemById(wx.ID_CUT)
        cutItem.Enable(hasSelection)
        copyItem = self.menus.FindItemById(wx.ID_COPY)
        copyItem.Enable(hasSelection)

        pasteItem = self.menus.FindItemById(wx.ID_PASTE)
        pasteItem.Enable(self.bodyInput.CanPaste())

        # find/replace

        findNextItem = self.menus.FindItemById(PassageFrame.EDIT_FIND_NEXT)
        findNextItem.Enable(self.lastFindRegexp != None)

        # link selected text menu item

        editSelected = self.menus.FindItemById(PassageFrame.PASSAGE_EDIT_SELECTION)
        selection = self.bodyInput.GetSelectedText()

        if selection != '':
            if not re.match(r'^\[\[.*\]\]$', selection):
                if len(selection) < 25:
                    editSelected.SetText('Create &Link "' + selection + '"\tCtrl-L')
                else:
                    editSelected.SetText('Create &Link From Selected Text\tCtrl-L')
            else:
                if len(selection) < 25:
                    editSelected.SetText('&Edit Passage "' + self.stripCrud(selection) + '"\tCtrl-L')
                else:
                    editSelected.SetText('&Edit Passage From Selected Text\tCtrl-L')
            editSelected.Enable(True)
        else:
            editSelected.SetText('Create &Link From Selected Text\tCtrl-L')
            editSelected.Enable(False)

    def updateSubmenus(self, event = None):
        """
        Updates our passage menus. This should be called sparingly, i.e. not during
        a UI update event, as it is doing a bunch of removing and adding of items.
        """

        # separate outgoing and broken links

        outgoing = []
        incoming = []
        broken = []

        # Remove externals

        links = filter(lambda text: TweeLexer.linkStyle(text) == TweeLexer.BAD_LINK, self.widget.passage.links)
        for link in links:
            if len(link) > 0:
                found = False

                for widget in self.widget.parent.widgets:
                    if widget.passage.title == link:
                        outgoing.append(link)
                        found = True
                        break

                if not found and self.widget.parent.includedPassageExists(link): found = True

                if not found: broken.append(link)

        # incoming links

        for widget in self.widget.parent.widgets:
            if self.widget.passage.title in widget.passage.links \
            and len(widget.passage.title) > 0:
                incoming.append(widget.passage.title)

        # repopulate the menus

        def populate(menu, links):
            for item in menu.GetMenuItems():
                menu.DeleteItem(item)

            if len(links):
                for link in links:
                    item = menu.Append(-1, link)
                    self.Bind(wx.EVT_MENU, self.openOtherEditor, item)
            else:
                item = menu.Append(wx.ID_ANY, '(None)')
                item.Enable(False)

        outTitle = 'Outgoing Links'
        if len(outgoing) > 0: outTitle += ' (' + str(len(outgoing)) + ')'
        self.outLinksMenuTitle.SetText(outTitle)
        populate(self.outLinksMenu, outgoing)

        inTitle = 'Incoming Links'
        if len(incoming) > 0: inTitle += ' (' + str(len(incoming)) + ')'
        self.inLinksMenuTitle.SetText(inTitle)
        populate(self.inLinksMenu, incoming)

        brokenTitle = 'Broken Links'
        if len(broken) > 0: brokenTitle += ' (' + str(len(broken)) + ')'
        self.brokenLinksMenuTitle.SetText(brokenTitle)
        populate(self.brokenLinksMenu, broken)

    def applyPrefs(self):
        """Applies user prefs to this frame."""
        bodyFont = wx.Font(self.app.config.ReadInt('windowedFontSize'), wx.MODERN, wx.NORMAL,
                           wx.NORMAL, False, self.app.config.Read('windowedFontFace'))
        defaultStyle = self.bodyInput.GetStyleAt(0)
        self.bodyInput.StyleSetFont(defaultStyle, bodyFont)
        if hasattr(self, 'lexer'): self.lexer.initStyles()

    def __repr__(self):
        return "<PassageFrame '" + self.widget.passage.title + "'>"

    def getHeader(self):
        """Returns the current selected target header for this Passage Frame."""
        return self.widget.getHeader()

    # timing constants

    PARENT_SYNC_DELAY = 0.5

    # control constants

    DEFAULT_SIZE = (550, 600)
    TITLE_LABEL = 'Title'
    TAGS_LABEL = 'Tags (separate with spaces)'

    # menu constants (not defined by wx)

    EDIT_FIND_NEXT = 2001
    [PASSAGE_FULLSCREEN, PASSAGE_EDIT_SELECTION, PASSAGE_REBUILD_STORY, PASSAGE_TEST_HERE, PASSAGE_VERIFY] = range(1001,1006)
    [HELP1, HELP2, HELP3, HELP4, HELP5] = range(3001,3006)

    [LEXER_NONE, LEXER_NORMAL, LEXER_CSS] = range(0,3)


class StorySettingsFrame(PassageFrame):
    """A window which presents the current header's StorySettings."""

    def __init__(self, parent, widget, app):
        self.widget = widget
        self.app = app

        wx.Frame.__init__(self, parent, wx.ID_ANY, title = self.widget.passage.title + ' - ' + self.app.NAME + ' ' + versionString, \
                          size = (450, 550), style=wx.DEFAULT_FRAME_STYLE)
        # menus

        self.menus = wx.MenuBar()
        self.SetMenuBar(self.menus)

        # controls

        self.panel = wx.lib.scrolledpanel.ScrolledPanel(self)
        self.panel.SetupScrolling()
        allSizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(allSizer)

        # Read the storysettings definitions for this header
        self.storySettingsData = self.widget.parent.parent.header.storySettings()
        
        if not self.storySettingsData or type(self.storySettingsData) is str:
            label = self.storySettingsData or "The currently selected story format does not use StorySettings."
            allSizer.Add(wx.StaticText(self.panel, label = label),flag=wx.ALL|wx.EXPAND, border=metrics.size('windowBorder'))
            self.storySettingsData = {}
        
        self.ctrls = {}
        
        for data in self.storySettingsData:
            ctrlset = []
            name = ''
            if data["type"] == "checkbox":
                checkbox = wx.CheckBox(self.panel, label = data["label"])
                name = data["name"]
                # Read current value, and default it if it's not present
                currentValue = self.getSetting(name).lower()
                if not currentValue:
                    currentValue = data.get('default', 'off')
                    self.saveSetting(name, currentValue)
                checkbox.SetValue(currentValue not in ["off", "false", '0'])
                values = data.get("values", ("on","off"))
                checkbox.Bind(wx.EVT_CHECKBOX, lambda e, checkbox=checkbox, name=name, values=values:
                              self.saveSetting(name, values[0] if checkbox.GetValue() else values[1] ))
                allSizer.Add(checkbox,flag=wx.ALL, border=metrics.size('windowBorder'))
                ctrlset.append(checkbox)
            
            elif data["type"] == "text":
                textlabel = wx.StaticText(self.panel, label = data["label"])
                textctrl = wx.TextCtrl(self.panel)
                name = data["name"]
                # Read current value
                currentValue = self.getSetting(name).lower()
                if not currentValue:
                    currentValue = data.get('default', '')
                    self.saveSetting(name, currentValue)
                textctrl.SetValue(currentValue or data.get("default",''))

                textctrl.Bind(wx.EVT_TEXT, lambda e, name=name, textctrl=textctrl:
                              self.saveSetting(name,textctrl.GetValue()))
                # Setup sizer for label/textctrl pair
                hSizer = wx.BoxSizer(wx.HORIZONTAL)
                hSizer.Add(textlabel,1,wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
                hSizer.Add(textctrl,1,wx.EXPAND)
                allSizer.Add(hSizer,flag=wx.ALL|wx.EXPAND, border=metrics.size('windowBorder'))
                ctrlset += [textlabel, textctrl]
            else:
                continue
            
            if "desc" in data:
                desc = wx.StaticText(self.panel, label = data["desc"])
                allSizer.Add(desc, 0, flag=wx.LEFT|wx.BOTTOM, border = metrics.size('windowBorder'))
                ctrlset.append(desc)
            
            self.ctrls[name] = ctrlset
            
        self.SetIcon(self.app.icon)
        self.SetTitle(self.title())
        self.Layout()
        self.enableCtrls()
        self.Show(True)
    
    def enableCtrls(self):
        # Check if each ctrl has a requirement or an incompatibility,
        # look it up, and enable/disable if so
        for data in self.storySettingsData:
            name = data["name"]
            if name in self.ctrls:
                if 'requires' in data:
                    set = self.getSetting(data['requires'])
                    for i in self.ctrls[name]:
                        i.Enable(set not in ["off", "false", '0'])
    
    def getSetting(self, valueName):
        search = re.search(r"(?:^|\n)"+valueName + r"\s*:\s*(\w*)\s*(?:\n|$)", self.widget.passage.text, flags=re.I)
        if search:
            return search.group(1)
        return ''

    def saveSetting(self, valueName, value):
        newEntry = valueName+":"+str(value)+'\n'
        sub = re.subn("^"+valueName+r"\s*:\s*[^\n]+\n", newEntry, self.widget.passage.text, flags=re.I|re.M)
        if sub[1]:
            self.widget.passage.text = sub[0]
        else:
            self.widget.passage.text += newEntry
        self.widget.passage.modified = time.localtime()
        self.widget.parent.parent.setDirty(True)
        self.widget.clearPaintCache()
        self.widget.passage.update()
        self.enableCtrls()


class ImageFrame(PassageFrame):
    """
    A window which only displays passages whose text consists of base64 encoded images -
    the image is converted to a bitmap and displayed, if possible.
    """

    def __init__(self, parent, widget, app):
        self.widget = widget
        self.app = app
        self.syncTimer = None
        self.image = None
        self.gif = None

        wx.Frame.__init__(self, parent, wx.ID_ANY, title = 'Untitled Passage - ' + self.app.NAME + ' ' + versionString, \
                          size = PassageFrame.DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE)

        # controls

        self.panel = wx.Panel(self)
        allSizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(allSizer)

        # title control

        self.topControls = wx.Panel(self.panel)
        topSizer = wx.FlexGridSizer(3, 2, metrics.size('relatedControls'), metrics.size('relatedControls'))

        titleLabel = wx.StaticText(self.topControls, style = wx.ALIGN_RIGHT, label = PassageFrame.TITLE_LABEL)
        self.titleInput = wx.TextCtrl(self.topControls)
        self.titleInput.SetValue(self.widget.passage.title)
        self.SetTitle(self.title())

        topSizer.Add(titleLabel, 0, flag = wx.ALL, border = metrics.size('focusRing'))
        topSizer.Add(self.titleInput, 1, flag = wx.EXPAND | wx.ALL, border = metrics.size('focusRing'))
        topSizer.AddGrowableCol(1, 1)
        self.topControls.SetSizer(topSizer)

        # image pane

        self.imageScroller = wx.ScrolledWindow(self.panel)
        self.imageSizer = wx.GridSizer(1,1)
        self.imageScroller.SetSizer(self.imageSizer)

        # image menu

        passageMenu = wx.Menu()

        passageMenu.Append(self.IMPORT_IMAGE, '&Replace Image...\tCtrl-O')
        self.Bind(wx.EVT_MENU, self.replaceImage, id = self.IMPORT_IMAGE)

        passageMenu.Append(self.SAVE_IMAGE, '&Save Image...')
        self.Bind(wx.EVT_MENU, self.saveImage, id = self.SAVE_IMAGE)

        passageMenu.AppendSeparator()

        passageMenu.Append(wx.ID_SAVE, '&Save Story\tCtrl-S')
        self.Bind(wx.EVT_MENU, self.widget.parent.parent.save, id = wx.ID_SAVE)

        passageMenu.Append(PassageFrame.PASSAGE_REBUILD_STORY, '&Rebuild Story\tCtrl-R')
        self.Bind(wx.EVT_MENU, self.widget.parent.parent.rebuild, id = PassageFrame.PASSAGE_REBUILD_STORY)

        passageMenu.AppendSeparator()

        passageMenu.Append(wx.ID_CLOSE, '&Close Image\tCtrl-W')
        self.Bind(wx.EVT_MENU, lambda e: self.Destroy(), id = wx.ID_CLOSE)

        # edit menu

        editMenu = wx.Menu()

        editMenu.Append(wx.ID_COPY, '&Copy\tCtrl-C')
        self.Bind(wx.EVT_MENU, self.copyImage, id = wx.ID_COPY)

        editMenu.Append(wx.ID_PASTE, '&Paste\tCtrl-V')
        self.Bind(wx.EVT_MENU, self.pasteImage, id = wx.ID_PASTE)

        # menu bar

        self.menus = wx.MenuBar()
        self.menus.Append(passageMenu, '&Image')
        self.menus.Append(editMenu, '&Edit')
        self.SetMenuBar(self.menus)

        # finish

        allSizer.Add(self.topControls, flag = wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border = metrics.size('windowBorder'))
        allSizer.Add(self.imageScroller, proportion = 1, flag = wx.TOP | wx.EXPAND, border = metrics.size('relatedControls'))

        # bindings
        self.titleInput.Bind(wx.EVT_TEXT, self.syncPassage)

        self.SetIcon(self.app.icon)
        self.updateImage()
        self.Show(True)

    def syncPassage(self, event = None):
        """Updates the image based on the title input; asks our matching widget to repaint."""
        if len(self.titleInput.GetValue()) > 0:
            self.widget.passage.title = self.titleInput.GetValue()
        else:
            self.widget.passage.title = 'Untitled Image'
        self.widget.clearPaintCache()

        self.SetTitle(self.title())

        # immediately mark the story dirty

        self.widget.parent.parent.setDirty(True)

        # reset redraw timer

        def reallySync(self):
            self.widget.parent.Refresh()

        if (self.syncTimer):
            self.syncTimer.cancel()

        self.syncTimer = threading.Timer(PassageFrame.PARENT_SYNC_DELAY, reallySync, [self], {})
        self.syncTimer.start()


    def updateImage(self):
        """Assigns a bitmap to this frame's StaticBitmap component,
        unless it's a GIF, in which case, animate it."""
        if self.gif:
            self.gif.Stop()
        self.imageSizer.Clear(True)
        self.gif = None
        self.image = None
        size = (32,32)

        t = self.widget.passage.text
        # Get the bitmap (will be used as inactive for GIFs)
        bmp = self.widget.bitmap
        if bmp:
            size = bmp.GetSize()

            # GIF animation
            if t.startswith("data:image/gif"):

                self.gif = wx.animate.AnimationCtrl(self.imageScroller, size = size)
                self.imageSizer.Add(self.gif, 1, wx.ALIGN_CENTER)

                # Convert the full GIF to an Animation
                anim = wx.animate.Animation()
                data = base64.b64decode(t[t.index("base64,")+7:])
                anim.Load(cStringIO.StringIO(data))

                # Load the Animation into the AnimationCtrl

                # Crashes OS X..
                #self.gif.SetInactiveBitmap(bmp)
                self.gif.SetAnimation(anim)
                self.gif.Play()

            # Static images
            else:
                self.image = wx.StaticBitmap(self.imageScroller, style = wx.TE_PROCESS_TAB | wx.BORDER_SUNKEN)
                self.imageSizer.Add(self.image, 1, wx.ALIGN_CENTER)
                self.image.SetBitmap(bmp)

        self.SetSize((min(max(size[0], 320),1024),min(max(size[1], 240),768)+64))
        self.imageScroller.SetScrollRate(2,2)
        self.Refresh()

        # Update copy menu
        copyItem = self.menus.FindItemById(wx.ID_COPY)
        copyItem.Enable(not not bmp)

    def replaceImage(self, event = None):
        """Replace the image with a new file, if possible."""
        self.widget.parent.parent.importImageDialog(replace = self.widget)
        self.widget.parent.parent.setDirty(True)
        self.updateImage()

    def saveImage(self, event = None):
        """Saves the base64 image as a file."""
        t = self.widget.passage.text;
        # Get the extension
        extension = images.GetImageType(t)
        dialog = wx.FileDialog(self, 'Save Image', os.getcwd(), self.widget.passage.title + extension, \
                               'Image File|*' + extension + '|All Files (*.*)|*.*', wx.SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            try:
                path = dialog.GetPath()

                dest = open(path, 'wb')

                data = base64.b64decode(images.RemoveURIPrefix(t))
                dest.write(data)

                dest.close()
            except:
                self.app.displayError('saving the image')

        dialog.Destroy()

    def copyImage(self, event = None):
        """Copy the bitmap to the clipboard"""
        clip = wx.TheClipboard
        if self.image and clip.Open():
            clip.SetData(wx.BitmapDataObject(self.image.GetBitmap() if not self.gif else self.gif.GetInactiveBitmap()))
            clip.Flush()
            clip.Close()

    def pasteImage(self, event = None):
        """Paste from the clipboard, converting to a PNG"""
        clip = wx.TheClipboard
        bdo = wx.BitmapDataObject()
        pasted = False

        # Try and read from the clipboard
        if clip.Open():
            pasted = clip.GetData(bdo)
            clip.Close()
        if not pasted:
            return

        # Convert bitmap to PNG
        bmp = bdo.GetBitmap()
        self.widget.passage.text = images.BitmapToBase64PNG(bmp)
        self.widget.updateBitmap()
        self.updateImage()

    IMPORT_IMAGE = 1004
    EXPORT_IMAGE = 1005
    SAVE_IMAGE = 1006



########NEW FILE########
__FILENAME__ = passagesearchframe
import re, wx
from searchpanels import FindPanel, ReplacePanel

class PassageSearchFrame(wx.Frame):
    """
    This allows a user to do search and replaces on a PassageFrame.
    By default, this shows the Find tab initially, but this can be
    set via the constructor.
    """

    def __init__(self, parent, passageFrame, app, initialState = 0):
        self.passageFrame = passageFrame
        self.app = app
        wx.Frame.__init__(self, parent, title = 'Find/Replace In Passage')
        panel = wx.Panel(self)
        panelSizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(panelSizer)

        self.notebook = wx.Notebook(panel)
        self.findPanel = FindPanel(self.notebook, onFind = self.passageFrame.findRegexp, \
                                   onClose = lambda: self.Close())
        self.replacePanel = ReplacePanel(self.notebook, onFind = self.passageFrame.findRegexp, \
                                         onReplace = self.passageFrame.replaceOneRegexp, \
                                         onReplaceAll = self.passageFrame.replaceAllRegexps, \
                                         onClose = lambda: self.Close())
        self.notebook.AddPage(self.findPanel, 'Find')
        self.notebook.AddPage(self.replacePanel, 'Replace')
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onChangeTab)

        self.notebook.ChangeSelection(initialState)
        if initialState == PassageSearchFrame.FIND_TAB:
            self.findPanel.focus()
        else:
            self.replacePanel.focus()

        panelSizer.Add(self.notebook, 1, wx.EXPAND)
        panelSizer.Fit(self)
        self.SetIcon(self.app.icon)
        self.Show()

    def onChangeTab(self, event):
        if event.GetSelection() == PassageSearchFrame.FIND_TAB:
            self.findPanel.focus()
        else:
            self.replacePanel.focus()

        # for some reason, we have to manually propagate the event from here

        event.Skip(True)

    FIND_TAB = 0
    REPLACE_TAB = 1


########NEW FILE########
__FILENAME__ = passagewidget
import sys, os, copy, math, colorsys, re, wx, storypanel, tiddlywiki, tweelexer
import geometry, metrics, images
from passageframe import PassageFrame, ImageFrame, StorySettingsFrame

class PassageWidget:
    """
    A PassageWidget is a box standing in for a proxy for a single
    passage in a story. Users can drag them around, double-click
    to open a PassageFrame, and so on.

    This must have a StoryPanel as its parent.

    See the comments on StoryPanel for more information on the
    coordinate systems are used here. In general, you should
    always pass methods logical coordinates, and expect back
    logical coordinates. Use StoryPanel.toPixels() to convert.
    """

    def __init__(self, parent, app, id = wx.ID_ANY, pos = (0, 0), title = '', text = '', tags = [], state = None):
        # inner state

        self.parent = parent
        self.app = app
        self.dimmed = False
        self.brokenEmblem = wx.Bitmap(self.app.iconsPath + 'brokenemblem.png')
        self.externalEmblem = wx.Bitmap(self.app.iconsPath + 'externalemblem.png')
        self.paintBuffer = wx.MemoryDC()
        self.paintBufferBounds = None        
        if state:
            self.passage = state['passage']
            self.pos = list(pos) if pos != (0,0) else state['pos']
            self.selected = state['selected']
        else:
            self.passage = tiddlywiki.Tiddler('')
            self.selected = False
            self.pos = list(pos)
        if title: self.passage.title = title
        if text: self.passage.text = text
        if tags: self.passage.tags += tags

        self.bitmap = None
        self.updateBitmap()
        self.passage.update()

    def getSize(self):
        """Returns this instance's logical size."""
        if self.passage.isAnnotation():
            return (PassageWidget.SIZE+self.parent.GRID_SPACING, PassageWidget.SIZE+self.parent.GRID_SPACING)
        return (PassageWidget.SIZE, PassageWidget.SIZE)

    def getCenter(self):
        """Returns this instance's center in logical coordinates."""
        pos = list(self.pos)
        pos[0] += self.getSize()[0] / 2
        pos[1] += self.getSize()[1] / 2
        return pos

    def getLogicalRect(self):
        """Returns this instance's rectangle in logical coordinates."""
        size = self.getSize()
        return wx.Rect(self.pos[0], self.pos[1], size[0], size[1])

    def getPixelRect(self):
        """Returns this instance's rectangle onscreen."""
        origin = self.parent.toPixels(self.pos)
        size = self.parent.toPixels(self.getSize(), scaleOnly = True)
        return wx.Rect(origin[0], origin[1], size[0], size[1])

    def getDirtyPixelRect(self):
        """
        Returns a pixel rectangle of everything that needs to be redrawn for the widget
        in its current position. This includes the widget itself as well as any
        other widgets it links to.
        """
        dirtyRect = self.getPixelRect()

        # first, passages we link to

        for link in self.passage.links:
            widget = self.parent.findWidget(link)
            if widget: dirtyRect = dirtyRect.Union(widget.getPixelRect())

        # then, those that link to us
        # Python closures are odd, require lists to affect things outside

        bridge = [ dirtyRect ]

        def addLinkingToRect(widget):
            if self.passage.title in widget.passage.links:
                dirtyRect = bridge[0].Union(widget.getPixelRect())

        self.parent.eachWidget(addLinkingToRect)

        return dirtyRect

    def offset(self, x = 0, y = 0):
        """Offsets this widget's position by logical coordinates."""
        self.pos = list(self.pos)
        self.pos[0] += x
        self.pos[1] += y

    def findSpace(self):
        """Moves this widget so it doesn't overlap any others."""
        turns = 0.0
        movecount = 1
        """
        Don't adhere to the grid if snapping isn't enabled.
        Instead, move in 1/5 grid increments.
        """
        griddivision = 1 if self.parent.snapping else 0.2

        while self.intersectsAny() and turns < 99*griddivision:
            """Move in an Ulam spiral pattern: n spaces left, n spaces up, n+1 spaces right, n+1 spaces down"""
            self.pos[int(math.floor((turns*2) % 2))] += self.parent.GRID_SPACING * griddivision * int(math.copysign(1, turns % 2 - 1));
            movecount -= 1
            if movecount <= 0:
                turns += 0.5
                movecount = int(math.ceil(turns)/griddivision)

    def findSpaceQuickly(self):
        """ A quicker findSpace where the position and visibility doesn't really matter """
        while self.intersectsAny():
            self.pos[0] += self.parent.GRID_SPACING
            rightEdge = self.pos[0] + PassageWidget.SIZE
            maxWidth = self.parent.toLogical((self.parent.GetSize().width - self.parent.INSET[0], -1), \
                                             scaleOnly = True)[0]
            if rightEdge > maxWidth:
                self.pos[0] = 10
                self.pos[1] += self.parent.GRID_SPACING


    def containsRegexp(self, regexp, flags):
        """
        Returns whether this widget's passage contains a regexp.
        """
        return (re.search(regexp, self.passage.title, flags) != None \
                or re.search(regexp, self.passage.text, flags) != None)

    def replaceRegexp(self, findRegexp, replaceRegexp, flags):
        """
        Performs a regexp replace in this widget's passage title and
        body text. Returns the number of replacements actually made.
        """
        compiledRegexp = re.compile(findRegexp, flags)
        titleReps = textReps = 0

        self.passage.title, titleReps = re.subn(compiledRegexp, replaceRegexp, self.passage.title)
        self.passage.text, textReps = re.subn(compiledRegexp, replaceRegexp, self.passage.text)

        return titleReps + textReps

    def linksAndDisplays(self):
        return self.passage.linksAndDisplays() + self.getShorthandDisplays()

    def getShorthandDisplays(self):
        """Returns a list of macro tags which match passage names."""
        return filter(lambda a: self.parent.passageExists(a), self.passage.macros)

    def getBrokenLinks(self):
        """Returns a list of broken links in this widget."""
        return filter(lambda a: not self.parent.passageExists(a), self.passage.links)
    
    def getIncludedLinks(self):
        """Returns a list of included passages in this widget."""
        return filter(lambda a: self.parent.includedPassageExists(a), self.passage.links)
    
    def getVariableLinks(self):
        """Returns a list of links which use variables/functions, in this widget."""
        return filter(lambda a: tweelexer.TweeLexer.linkStyle(a)==tweelexer.TweeLexer.PARAM, self.passage.links)

    def setSelected(self, value, exclusive = True):
        """
        Sets whether this widget should be selected. Pass a false value for
        exclusive to prevent other widgets from being deselected.
        """

        if (exclusive):
            self.parent.eachWidget(lambda i: i.setSelected(False, False))

        old = self.selected
        self.selected = value
        if self.selected != old:
            self.clearPaintCache()

            # Figure out the dirty rect
            dirtyRect = self.getPixelRect()
            for link in self.linksAndDisplays() + self.passage.images:
                widget = self.parent.findWidget(link)
                if widget:
                    dirtyRect = dirtyRect.Union(widget.getDirtyPixelRect())
            if self.passage.isStylesheet():
                for t in self.passage.tags:
                    if t not in tiddlywiki.TiddlyWiki.INFO_TAGS:
                        for widget in self.parent.taggedWidgets(t):
                            if widget:
                                dirtyRect = dirtyRect.Union(widget.getDirtyPixelRect())
            self.parent.Refresh(True, dirtyRect)

    def setDimmed(self, value):
        """Sets whether this widget should be dimmed."""
        old = self.dimmed
        self.dimmed = value
        if self.dimmed != old:
            self.clearPaintCache()

    def clearPaintCache(self):
        """
        Forces the widget to be repainted from scratch.
        """
        self.paintBufferBounds = None

    def openContextMenu(self, event):
        """Opens a contextual menu at the event position given."""
        self.parent.PopupMenu(PassageWidgetContext(self), event.GetPosition())

    def openEditor(self, event = None, fullscreen = False):
        """Opens a PassageFrame to edit this passage."""
        image = self.passage.isImage()

        if (not hasattr(self, 'passageFrame')):
            if image:
                self.passageFrame = ImageFrame(None, self, self.app)
            elif self.passage.title == "StorySettings":
                self.passageFrame = StorySettingsFrame(None, self, self.app)
            else:
                self.passageFrame = PassageFrame(None, self, self.app)
                if fullscreen: self.passageFrame.openFullscreen()
        else:
            try:
                self.passageFrame.Iconize(False)
                self.passageFrame.Raise()
                if fullscreen and not image: self.passageFrame.openFullscreen()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'passageFrame')
                self.openEditor(event, fullscreen)

    def closeEditor(self, event = None):
        """Closes the PassageFrame associated with this, if it exists."""
        try: self.passageFrame.closeFullscreen()
        except: pass
        try: self.passageFrame.Destroy()
        except: pass
            
    def verifyPassage(self, window):
        """
        Check that the passage syntax is well-formed.
        Return -(corrections made) if the check was aborted, +(corrections made) otherwise
        """
        passage = self.passage
        checks = tweelexer.VerifyLexer(self).check()
        
        broken = False
        problems = 0
        
        oldtext = passage.text
        newtext = ""
        index = 0
        for warning, replace in checks:
            problems += 1
            if replace:
                start, sub, end = replace
                answer = wx.MessageDialog(window, warning + "\n\nMay I try to fix this for you?", 'Problem in '+self.passage.title, wx.ICON_WARNING | wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT) \
                    .ShowModal()
                if answer == wx.ID_YES:
                    newtext += oldtext[index:start] + sub
                    index = end
                    if hasattr(self, 'passageFrame') and self.passageFrame:
                        self.passageFrame.bodyInput.SetText(newtext + oldtext[index:])
                elif answer == wx.ID_CANCEL:
                    return -problems
            else:
                answer = wx.MessageDialog(window, warning+"\n\nKeep checking?", 'Problem in '+self.passage.title, wx.ICON_WARNING | wx.YES_NO) \
                    .ShowModal()
                if answer == wx.ID_NO:
                    return problems
                    
            passage.text = newtext + oldtext[index:]
        
        return problems

    def intersectsAny(self, dragging = False):
        """Returns whether this widget intersects any other in the same StoryPanel."""

        #Enforce positive coordinates
        if not 'Twine.hide' in self.passage.tags:
            if ((self.pos[0] < 0) or (self.pos[1] < 0)):
                return True

        # we do this manually so we don't have to go through all of them

        for widget in (self.parent.notDraggingWidgets if dragging else self.parent.widgets):
            if (widget != self) and (self.intersects(widget)):
                return True

        return False

    def intersects(self, other):
        """
        Returns whether this widget intersects another widget or wx.Rect.
        This uses logical coordinates, so you can do this without actually moving the widget onscreen.
        """
        selfRect = self.getLogicalRect()

        if isinstance(other, PassageWidget):
            other = other.getLogicalRect()
        return selfRect.Intersects(other)

    def applyPrefs(self):
        """Passes on the message to any editor windows."""
        self.clearPaintCache()
        try: self.passageFrame.applyPrefs()
        except: pass
        try: self.passageFrame.fullscreen.applyPrefs()
        except: pass

    def updateBitmap(self):
        """If an image passage, updates the bitmap to match the contained base64 data."""
        if self.passage.isImage():
            self.bitmap = images.Base64ToBitmap(self.passage.text)
        
    def getConnectorLine(self, otherWidget):
        """
        Get the line that would be drawn between this widget and another.
        """
        start = self.parent.toPixels(self.getCenter())
        end = self.parent.toPixels(otherWidget.getCenter())

        # Additional tweak to make overlapping arrows more visible

        length = min(math.sqrt((start[0]-end[0])**2 + (start[1]-end[1])**2)/32, 16)

        if start[1] != end[1]:
            start[0] += length * math.copysign(1, start[1] - end[1]);
            end[0] += length * math.copysign(1, start[1] - end[1]);
        if start[0] != end[0]:
            start[1] += length * math.copysign(1, start[0] - end[0]);
            end[1] += length * math.copysign(1, start[0] - end[0]);

        # Clip the end of the arrow

        start, end = geometry.clipLineByRects([start, end], otherWidget.getPixelRect())
        
        return (start, end)
        

    def paintConnectorTo(self, otherWidget, arrowheads, color, width, gc, updateRect = None):
        """
        Paints a connecting line between this widget and another,
        with optional arrowheads. You may pass either a wx.GraphicsContext
        (anti-aliased drawing) or a wx.PaintDC.
        """
        start, end = self.getConnectorLine(otherWidget)

        # does it actually need to be drawn?

        if otherWidget == self:
            return

        if updateRect and not geometry.lineRectIntersection([start, end], updateRect):
            return

        # ok, really draw the line

        lineWidth = max(self.parent.toPixels((width, 0), scaleOnly = True)[0], 1)
        gc.SetPen(wx.Pen(color, lineWidth))

        if isinstance(gc, wx.GraphicsContext):
            gc.StrokeLine(start[0], start[1], end[0], end[1])
        else:
            gc.DrawLine(start[0], start[1], end[0], end[1])

        # arrowheads at end

        if not arrowheads: return

        flat = self.app.config.ReadBool('flatDesign')
        
        arrowheadLength = max(self.parent.toPixels((PassageWidget.ARROWHEAD_LENGTH, 0), scaleOnly = True)[0], 1)
        arrowhead = geometry.endPointProjectedFrom((start, end), angle = PassageWidget.ARROWHEAD_ANGLE, \
                                                   distance = arrowheadLength)

        if flat:
            pass
        elif isinstance(gc, wx.GraphicsContext):
            gc.StrokeLine(end[0], end[1], arrowhead[0], arrowhead[1])
        else:
            gc.DrawLine(end[0], end[1], arrowhead[0], arrowhead[1])

        arrowhead2 = geometry.endPointProjectedFrom((start, end), angle = 0 - PassageWidget.ARROWHEAD_ANGLE, \
                                                   distance = arrowheadLength)

        
        if flat:
            gc.SetBrush(wx.Brush(color))
            if isinstance(gc, wx.GraphicsContext):
                gc.DrawLines([wx.Point2D(*arrowhead2), wx.Point2D(*end), wx.Point2D(*arrowhead) ])
            else:
                gc.DrawPolygon([wx.Point(*arrowhead2), wx.Point(*end), wx.Point(*arrowhead)])
        elif isinstance(gc, wx.GraphicsContext):
            gc.StrokeLine(end[0], end[1], arrowhead2[0], arrowhead2[1])
        else:
            gc.DrawLine(end[0], end[1], arrowhead2[0], arrowhead2[1])


    def getConnectedWidgets(self):
        """
        Returns a list of titles of all widgets that will have lines drawn to them.
        """
        ret = []
        for link in self.linksAndDisplays():
            if (link in self.passage.links or self.app.config.ReadBool('displayArrows')):
                widget = self.parent.findWidget(link)
                if widget:
                    ret.append(widget)
        
        if self.app.config.ReadBool('imageArrows'):
            for link in self.passage.images:
                widget = self.parent.findWidget(link)
                if widget:
                    ret.append(widget)
            
            if self.passage.isStylesheet():
                for t in self.passage.tags:
                    if t not in tiddlywiki.TiddlyWiki.INFO_TAGS:
                        for otherWidget in self.parent.taggedWidgets(t):
                            if not otherWidget.dimmed and not otherWidget.passage.isStylesheet():
                                ret.append(otherWidget)
        return ret
            
    def paintConnectors(self, gc, arrowheads = True, updateRect = None):
        """
        Paints all connectors originating from this widget. This accepts
        a list of widget titles that will not be drawn to. It returns this
        list, along with any other bad links this widget contains.

        As with other paint calls, you may pass either a wx.GraphicsContext
        or wx.PaintDC.
        """
        
        flat = self.app.config.ReadBool('flatDesign')
        colors = PassageWidget.FLAT_COLORS if flat else PassageWidget.COLORS
        
        if not self.app.config.ReadBool('fastStoryPanel'):
            gc = wx.GraphicsContext.Create(gc)

        widgets = self.getConnectedWidgets()
        if widgets:
            for widget in widgets:
                link = widget.passage.title
                
                if self.passage.isAnnotation():
                    color = colors['connectorAnnotation']
                elif (link in self.passage.displays + self.passage.macros) and link not in self.passage.links:
                    color = colors['connectorDisplay']
                elif link in self.passage.images or self.passage.isStylesheet():
                    color = colors['connectorResource']
                else:
                    color = colors['connector']
                width = (2 if self.selected else 1) * (2 * flat + 1)
                self.paintConnectorTo(widget, arrowheads, color, width, gc, updateRect)
    
    def paint(self, dc):
        """
        Handles paint events, either blitting our paint buffer or
        manually redrawing.
        """
        pixPos = self.parent.toPixels(self.pos)
        pixSize = self.parent.toPixels(self.getSize(), scaleOnly = True)
        rect = wx.Rect(pixPos[0], pixPos[1], pixSize[0], pixSize[1])

        if (not self.paintBufferBounds) \
            or (rect.width != self.paintBufferBounds.width \
                or rect.height != self.paintBufferBounds.height):
            self.cachePaint(wx.Size(rect.width, rect.height))

        dc.Blit(rect.x, rect.y, rect.width, rect.height, self.paintBuffer, 0, 0)

    def getTitleColor(self):
        """
        Returns the title bar style that matches this widget's passage.
        """
        flat = self.app.config.ReadBool('flatDesign')
        # First, rely on the header to supply colours
        custom = self.getHeader().passageTitleColor(self.passage)
        if custom:
            return custom[flat]
        # Use default colours
        if self.passage.isAnnotation():
            ind = 'annotation'
        elif self.passage.isImage():
            ind = 'imageTitleBar'
        elif any(t.startswith('Twine.') for t in self.passage.tags):
            ind = 'privateTitleBar'
        elif not self.linksAndDisplays() and not self.getIncludedLinks() and not self.passage.variableLinks:
            ind = 'endTitleBar'
        else:
            ind = 'titleBar'
        colors = PassageWidget.FLAT_COLORS if flat else PassageWidget.COLORS
        return colors[ind]

    def cachePaint(self, size):
        """
        Caches the widget so self.paintBuffer is up-to-date.
        """

        def wordWrap(text, lineWidth, gc, lineBreaks = False):
            """
            Returns a list of lines from a string
            This is somewhat based on the wordwrap function built into wx.lib.
            (For some reason, GraphicsContext.GetPartialTextExtents()
            is returning totally wrong numbers but GetTextExtent() works fine.)

            This assumes that you've already set up the font you want on the GC.
            It gloms multiple spaces together, but for our purposes that's ok.
            """
            words = re.finditer('\S+\s*', text.replace('\r',''))
            lines = ''
            currentLine = ''

            for w in words:
                word = w.group(0)
                wordWidth = gc.GetTextExtent(currentLine + word)[0]
                if wordWidth < lineWidth:
                    currentLine += word
                    if '\n' in word:
                        lines += currentLine
                        currentLine = ''
                else:
                    lines += currentLine + '\n'
                    currentLine = word
            lines += currentLine
            return lines.split('\n')

        # Which set of colors to use
        flat = self.app.config.ReadBool('flatDesign')
        colors = PassageWidget.FLAT_COLORS if flat else PassageWidget.COLORS
        
        def dim(c, dim, flat=flat):
            """Lowers a color's alpha if dim is true."""
            if isinstance(c, wx.Colour): c = list(c.Get(includeAlpha = True))
            elif type(c) is str: c = list(ord(a) for a in c[1:].decode('hex'))
            else: c = list(c)
            if len(c) < 4:
                c.append(255)
            if dim:
                a = PassageWidget.FLAT_DIMMED_ALPHA if flat else PassageWidget.DIMMED_ALPHA
                if not self.app.config.ReadBool('fastStoryPanel'):
                    c[3] *= a
                else:
                    c[0] *= a
                    c[1] *= a
                    c[2] *= a
            return wx.Colour(*c)
        
        # set up our buffer

        bitmap = wx.EmptyBitmap(size.width, size.height)
        self.paintBuffer.SelectObject(bitmap)

        # switch to a GraphicsContext as necessary

        if self.app.config.ReadBool('fastStoryPanel'):
            gc = self.paintBuffer
        else:
            gc = wx.GraphicsContext.Create(self.paintBuffer)

        # text font sizes
        # wxWindows works with points, so we need to doublecheck on actual pixels

        titleFontSize = self.parent.toPixels((metrics.size('widgetTitle'), -1), scaleOnly = True)[0]
        titleFontSize = min(titleFontSize, metrics.size('fontMax'))
        titleFontSize = max(titleFontSize, metrics.size('fontMin'))
        excerptFontSize = min(titleFontSize * 0.9, metrics.size('fontMax'))
        excerptFontSize = max(excerptFontSize, metrics.size('fontMin'))
        if self.app.config.ReadBool('flatDesign'):
            titleFont = wx.Font(titleFontSize, wx.SWISS, wx.NORMAL, wx.LIGHT, False, 'Arial')
            excerptFont = wx.Font(excerptFontSize, wx.SWISS, wx.NORMAL, wx.LIGHT, False, 'Arial')
        else:
            titleFont = wx.Font(titleFontSize, wx.SWISS, wx.NORMAL, wx.BOLD, False, 'Arial')
            excerptFont = wx.Font(excerptFontSize, wx.SWISS, wx.NORMAL, wx.NORMAL, False, 'Arial')
        titleFontHeight = math.fabs(titleFont.GetPixelSize()[1])
        excerptFontHeight = math.fabs(excerptFont.GetPixelSize()[1])
        tagBarColor = dim( tuple(i*256 for i in colorsys.hsv_to_rgb(0.14 + math.sin(hash("".join(self.passage.tags)))*0.08,
                                                                    0.58 if flat else 0.28, 0.88)), self.dimmed)
        tags = set(self.passage.tags) - (tiddlywiki.TiddlyWiki.INFO_TAGS | self.getHeader().invisiblePassageTags() )

        # inset for text (we need to know this for layout purposes)

        inset = titleFontHeight / 3

        # frame
        if self.passage.isAnnotation():
            frameColor = colors['frame']
            c = wx.Colour(*colors['annotation'])
            frameInterior = (c,c)
        else:
            frameColor = dim(colors['frame'], self.dimmed)
            frameInterior = (dim(colors['bodyStart'], self.dimmed), \
                         dim(colors['bodyEnd'], self.dimmed))
        
        if not flat:
            gc.SetPen(wx.Pen(frameColor, 1))
    
            if isinstance(gc, wx.GraphicsContext):
                gc.SetBrush(gc.CreateLinearGradientBrush(0, 0, 0, size.height, \
                                                         frameInterior[0], frameInterior[1]))
            else:
                gc.GradientFillLinear(wx.Rect(0, 0, size.width - 1, size.height - 1), \
                                frameInterior[0], frameInterior[1], wx.SOUTH)
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
    
            gc.DrawRectangle(0, 0, size.width - 1, size.height - 1)
        else:
            gc.SetPen(wx.Pen(frameInterior[0]))
            gc.SetBrush(wx.Brush(frameInterior[0]))
            gc.DrawRectangle(0, 0, size.width, size.height)

        greek = size.width <= PassageWidget.MIN_GREEKING_SIZE * (2 if self.passage.isAnnotation() else 1)
        
        # title bar

        titleBarHeight = PassageWidget.GREEK_HEIGHT*3 if greek else titleFontHeight + (2 * inset)
        if self.passage.isAnnotation():
            titleBarColor = frameInterior[0]
        else:
            titleBarColor = dim(self.getTitleColor(), self.dimmed)
        gc.SetPen(wx.Pen(titleBarColor, 1))
        gc.SetBrush(wx.Brush(titleBarColor))
        if flat:
            gc.DrawRectangle(0, 0, size.width, titleBarHeight)
        else:
            gc.DrawRectangle(1, 1, size.width - 3, titleBarHeight)

        if not greek:
            # draw title
            # we let clipping prevent writing over the frame

            if isinstance(gc, wx.GraphicsContext):
                gc.ResetClip()
                gc.Clip(inset, inset, size.width - (inset * 2), titleBarHeight - 2)
            else:
                gc.DestroyClippingRegion()
                gc.SetClippingRect(wx.Rect(inset, inset, size.width - (inset * 2), titleBarHeight - 2))

            titleTextColor = dim(colors['titleText'], self.dimmed)

            if isinstance(gc, wx.GraphicsContext):
                gc.SetFont(titleFont, titleTextColor)
            else:
                gc.SetFont(titleFont)
                gc.SetTextForeground(titleTextColor)

            if self.passage.title:
                gc.DrawText(self.passage.title, inset, inset)

            # draw excerpt

            if not self.passage.isImage():
                excerptTop = inset + titleBarHeight

                # we split the excerpt by line, then draw them in turn
                # (we use a library to determine breaks, but have to draw the lines ourselves)

                if isinstance(gc, wx.GraphicsContext):
                    gc.ResetClip()
                    gc.Clip(inset, inset, size.width - (inset * 2), size.height - (inset * 2)-1)
                else:
                    gc.DestroyClippingRegion()
                    gc.SetClippingRect(wx.Rect(inset, inset, size.width - (inset * 2), size.height - (inset * 2)-1))

                if self.passage.isAnnotation():
                    excerptTextColor = wx.Colour(*colors['annotationText'])
                else:
                    excerptTextColor = dim(colors['excerptText'], self.dimmed)

                if isinstance(gc, wx.GraphicsContext):
                    gc.SetFont(excerptFont, excerptTextColor)
                else:
                    gc.SetFont(excerptFont)
                    gc.SetTextForeground(excerptTextColor)

                excerptLines = wordWrap(self.passage.text, size.width - (inset * 2), gc, self.passage.isAnnotation())

                for line in excerptLines:
                    gc.DrawText(line, inset, excerptTop)
                    excerptTop += excerptFontHeight * PassageWidget.LINE_SPACING \
                        * min(1.75,max(1,1.75*size.width/260 if (self.passage.isAnnotation() and line) else 1))
                    if excerptTop + excerptFontHeight > size.height - inset: break
            
            if (self.passage.isStoryText() or self.passage.isStylesheet()) and tags:
                
                tagBarHeight = excerptFontHeight + (2 * inset)
                gc.SetPen(wx.Pen(tagBarColor, 1))
                gc.SetBrush(wx.Brush(tagBarColor))
                gc.DrawRectangle(0, size.height-tagBarHeight-1, size.width, tagBarHeight+1)

                # draw tags

                tagTextColor = dim(colors['frame'], self.dimmed)

                if isinstance(gc, wx.GraphicsContext):
                    gc.SetFont(excerptFont, tagTextColor)
                else:
                    gc.SetFont(excerptFont)
                    gc.SetTextForeground(tagTextColor)

                text = wordWrap(" ".join(tags),
                                size.width - (inset * 2), gc)[0]

                gc.DrawText(text, inset*2, (size.height-tagBarHeight))
        else:
            # greek title

            gc.SetPen(wx.Pen(colors['titleText'], PassageWidget.GREEK_HEIGHT))
            height = inset
            width = (size.width - inset) / 2

            if isinstance(gc, wx.GraphicsContext):
                gc.StrokeLine(inset, height, width, height)
            else:
                gc.DrawLine(inset, height, width, height)

            height += PassageWidget.GREEK_HEIGHT * 3

            # greek body text
            if not self.passage.isImage():

                gc.SetPen(wx.Pen(colors['annotationText'] \
                    if self.passage.isAnnotation() else colors['greek'], PassageWidget.GREEK_HEIGHT))

                chars = len(self.passage.text)
                while height < size.height - inset and chars > 0:
                    width = size.height - inset

                    if height + (PassageWidget.GREEK_HEIGHT * 2) > size.height - inset:
                        width /= 2
                    elif chars < 80:
                        width = max(4, width * chars / 80)

                    if isinstance(gc, wx.GraphicsContext):
                        gc.StrokeLine(inset, height, width, height)
                    else:
                        gc.DrawLine(inset, height, width, height)

                    height += PassageWidget.GREEK_HEIGHT * 2
                    chars -= 80

            # greek tags

            if (self.passage.isStoryText() or self.passage.isStylesheet()) and tags:

                tagBarHeight = PassageWidget.GREEK_HEIGHT*3
                gc.SetPen(wx.Pen(tagBarColor, 1))
                gc.SetBrush(wx.Brush(tagBarColor))
                height = size.height-tagBarHeight-2
                width = size.width-4
                gc.DrawRectangle(2, height, width, tagBarHeight)

                gc.SetPen(wx.Pen(colors['greek'], PassageWidget.GREEK_HEIGHT))
                height += inset
                width = (width-inset*2)/2

                if isinstance(gc, wx.GraphicsContext):
                    gc.StrokeLine(inset, height, width, height)
                else:
                    gc.DrawLine(inset, height, width, height)

        if self.passage.isImage():
            if self.bitmap:
                if isinstance(gc, wx.GraphicsContext):
                    gc.ResetClip()
                    gc.Clip(1, titleBarHeight + 1, size.width - 3, size.height - 3)
                else:
                    gc.DestroyClippingRegion()
                    gc.SetClippingRect(wx.Rect(1, titleBarHeight + 1, size.width - 3, size.height - 3))

                width = size.width
                height = size.height - titleBarHeight

                # choose smaller of vertical and horizontal scale factor, to preserve aspect ratio
                scale = min(width/float(self.bitmap.GetWidth()), height/float(self.bitmap.GetHeight()));

                img = self.bitmap.ConvertToImage();
                if scale != 1:
                    img = img.Scale(scale*self.bitmap.GetWidth(),scale*self.bitmap.GetHeight());

                # offset image horizontally or vertically, to centre after scaling
                offsetWidth = (width - img.GetWidth())/2
                offsetHeight = (height - img.GetHeight())/2
                if isinstance(gc, wx.GraphicsContext):
                    gc.DrawBitmap(img.ConvertToBitmap(self.bitmap.GetDepth()), 1 + offsetWidth, titleBarHeight + 1 + offsetHeight, img.GetWidth(), img.GetHeight())
                else:
                    gc.DrawBitmap(img.ConvertToBitmap(self.bitmap.GetDepth()), 1 + offsetWidth, titleBarHeight + 1 + offsetHeight)

        if isinstance(gc, wx.GraphicsContext):
            gc.ResetClip()
        else:
            gc.DestroyClippingRegion()

        # draw a broken link emblem in the bottom right if necessary
        # fixme: not sure how to do this with transparency

        def showEmblem(emblem, gc=gc, size=size, inset=inset):
            emblemSize = emblem.GetSize()
            emblemPos = [ size.width - (emblemSize[0] + inset), \
                          size.height - (emblemSize[1] + inset) ]

            if isinstance(gc, wx.GraphicsContext):
                gc.DrawBitmap(emblem, emblemPos[0], emblemPos[1], emblemSize[0], emblemSize[1])
            else:
                gc.DrawBitmap(emblem, emblemPos[0], emblemPos[1])
            
        if len(self.getBrokenLinks()):
            showEmblem(self.brokenEmblem)
        elif len(self.getIncludedLinks()) or len(self.passage.variableLinks):
            showEmblem(self.externalEmblem)

        # finally, draw a selection over ourselves if we're selected

        if self.selected:
            color = dim(titleBarColor if flat else wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT), self.dimmed)
            if self.app.config.ReadBool('fastStoryPanel'):
                gc.SetPen(wx.Pen(color, 2 + flat))
            else:
                gc.SetPen(wx.TRANSPARENT_PEN)

            if isinstance(gc, wx.GraphicsContext):
                r, g, b = color.Get(False)
                color = wx.Colour(r, g, b, 64)
                gc.SetBrush(wx.Brush(color))
            else:
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                
            gc.DrawRectangle(0, 0, size.width, size.height)

        self.paintBufferBounds = size

    def serialize(self):
        """Returns a dictionary with state information suitable for pickling."""
        return { 'selected': self.selected, 'pos': self.pos, 'passage': copy.copy(self.passage) }

    def sort(first, second):
        """
        Sorts PassageWidgets so that the results appear left to right,
        top to bottom. A certain amount of slack is assumed here in
        terms of positioning.
        """
        xDistance = int(first.pos[0] - second.pos[0])
        yDistance = int(first.pos[1] - second.pos[1])

        if abs(yDistance) > 5:
            return yDistance
        else:
            if xDistance != 0:
                return xDistance
            else:
                return 1 # punt on ties

    def __repr__(self):
        return "<PassageWidget '" + self.passage.title + "'>"

    def getHeader(self):
        """Returns the current selected target header for this Passage Widget."""
        return self.parent.getHeader()

    MIN_PIXEL_SIZE = 10
    MIN_GREEKING_SIZE = 50
    GREEK_HEIGHT = 2
    SIZE = 120
    SHADOW_SIZE = 5
    COLORS = {
               'frame': (0, 0, 0), \
               'bodyStart': (255, 255, 255), \
               'bodyEnd': (212, 212, 212), \
               'annotation': (85, 87, 83), \
               'endTitleBar': (16, 51, 96), \
               'titleBar': (52, 101, 164), \
               'imageTitleBar': (8, 138, 133), \
               'privateTitleBar': (130, 130, 130), \
               'titleText': (255, 255, 255), \
               'excerptText': (0, 0, 0), \
               'annotationText': (255,255,255), \
               'greek': (102, 102, 102),
               'connector': (186, 189, 182),
               'connectorDisplay': (132, 164, 189),
               'connectorResource': (110, 112, 107),
               'connectorAnnotation': (0, 0, 0),
            }
    FLAT_COLORS = {
               'frame': (0, 0, 0),
               'bodyStart':  (255, 255, 255),
               'bodyEnd':  (255, 255, 255),
               'annotation': (212, 212, 212),
               'endTitleBar': (36, 54, 219),
               'titleBar': (36, 115, 219),
               'imageTitleBar': (36, 219, 213),
               'privateTitleBar': (153, 153, 153),
               'titleText': (255, 255, 255),
               'excerptText': (96, 96, 96),
               'annotationText': (0,0,0),
               'greek': (192, 192, 192),
               'connector': (143, 148, 137),
               'connectorDisplay': (137, 193, 235),
               'connectorResource': (186, 188, 185),
               'connectorAnnotation': (255, 255, 255),
               'selection': (28, 102, 176)
            }
    DIMMED_ALPHA = 0.5
    FLAT_DIMMED_ALPHA = 0.9
    LINE_SPACING = 1.2
    CONNECTOR_WIDTH = 2.0
    CONNECTOR_SELECTED_WIDTH = 5.0
    ARROWHEAD_LENGTH = 10
    MIN_ARROWHEAD_LENGTH = 5
    ARROWHEAD_ANGLE = math.pi / 6

# contextual menu

class PassageWidgetContext(wx.Menu):
    def __init__(self, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        title = '"' + parent.passage.title + '"'

        if parent.passage.isStoryPassage():
            test = wx.MenuItem(self, wx.NewId(), 'Test Play From Here')
            self.AppendItem(test)
            self.Bind(wx.EVT_MENU, lambda e: self.parent.parent.parent.testBuild(startAt = parent.passage.title), id = test.GetId())

        edit = wx.MenuItem(self, wx.NewId(), 'Edit ' + title)
        self.AppendItem(edit)
        self.Bind(wx.EVT_MENU, self.parent.openEditor, id = edit.GetId())

        delete = wx.MenuItem(self, wx.NewId(), 'Delete ' + title)
        self.AppendItem(delete)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.parent.removeWidget(self.parent), id = delete.GetId())



########NEW FILE########
__FILENAME__ = prefframe
import wx
import metrics

class PreferenceFrame(wx.Frame):
    """
    This allows the user to set their preferences. Changes automatically
    update as the user makes them; when they're done, they close the window.
    """

    def __init__(self, app, parent = None):
        self.app = app
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = self.app.NAME + ' Preferences', \
                          style = wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.CAPTION | wx.SYSTEM_MENU)

        panel = wx.Panel(parent = self, id = wx.ID_ANY)
        borderSizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(borderSizer)
        panelSizer = wx.FlexGridSizer(14, 2, metrics.size('relatedControls'), metrics.size('relatedControls'))
        borderSizer.Add(panelSizer, flag = wx.ALL, border = metrics.size('windowBorder'))

        self.editorFont = wx.FontPickerCtrl(panel, style = wx.FNTP_FONTDESC_AS_LABEL)
        self.editorFont.SetSelectedFont(self.getPrefFont('windowed'))
        self.editorFont.Bind(wx.EVT_FONTPICKER_CHANGED, lambda e: self.saveFontPref('windowed', \
                             self.editorFont.GetSelectedFont()))

        self.monoFont = wx.FontPickerCtrl(panel, style = wx.FNTP_FONTDESC_AS_LABEL)
        self.monoFont.SetSelectedFont(self.getPrefFont('monospace'))
        self.monoFont.Bind(wx.EVT_FONTPICKER_CHANGED, lambda e: self.saveFontPref('monospace', \
                             self.monoFont.GetSelectedFont()))

        self.fsFont = wx.FontPickerCtrl(panel, style = wx.FNTP_FONTDESC_AS_LABEL)
        self.fsFont.SetSelectedFont(self.getPrefFont('fs'))
        self.fsFont.Bind(wx.EVT_FONTPICKER_CHANGED, lambda e: self.saveFontPref('fs', \
                         self.fsFont.GetSelectedFont()))

        self.fsTextColor = wx.ColourPickerCtrl(panel)
        self.fsTextColor.SetColour(self.app.config.Read('fsTextColor'))
        self.fsTextColor.Bind(wx.EVT_COLOURPICKER_CHANGED, lambda e: self.savePref('fsTextColor', \
                              self.fsTextColor.GetColour()))

        self.fsBgColor = wx.ColourPickerCtrl(panel)
        self.fsBgColor.SetColour(self.app.config.Read('fsBgColor'))
        self.fsBgColor.Bind(wx.EVT_COLOURPICKER_CHANGED, lambda e: self.savePref('fsBgColor', \
                              self.fsBgColor.GetColour()))

        fsLineHeightPanel = wx.Panel(panel)
        fsLineHeightSizer = wx.BoxSizer(wx.HORIZONTAL)
        fsLineHeightPanel.SetSizer(fsLineHeightSizer)

        self.fsLineHeight = wx.ComboBox(fsLineHeightPanel, choices = ('100', '125', '150', '175', '200'))
        self.fsLineHeight.Bind(wx.EVT_TEXT, lambda e: self.savePref('fsLineHeight', int(self.fsLineHeight.GetValue())))
        self.fsLineHeight.SetValue(str(self.app.config.ReadInt('fslineHeight')))

        fsLineHeightSizer.Add(self.fsLineHeight, flag = wx.ALIGN_CENTER_VERTICAL)
        fsLineHeightSizer.Add(wx.StaticText(fsLineHeightPanel, label = '%'), flag = wx.ALIGN_CENTER_VERTICAL)
        
        def checkbox(self, name, label, panel=panel):
            setattr(self, name, wx.CheckBox(panel, label=label))
            attr = getattr(self, name)
            attr.Bind(wx.EVT_CHECKBOX, lambda e, name=name, attr=attr: self.savePref(name, attr.GetValue()))
            attr.SetValue(self.app.config.ReadBool(name))

        checkbox(self, "fastStoryPanel", 'Faster but rougher story map display')
        checkbox(self, "flatDesign", 'Flat Design(TM) mode')
        checkbox(self, "imageArrows", 'Connector arrows for images and stylesheets')
        checkbox(self, "displayArrows", 'Connector arrows for <<display>>ed passages')
        checkbox(self, "createPassagePrompt", 'Offer to create new passages for broken links')
        checkbox(self, "importImagePrompt", 'Offer to import externally linked images')  
        checkbox(self, "passageWarnings", 'Warn about possible passage code errors')

        panelSizer.Add(wx.StaticText(panel, label = 'Normal Font'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.editorFont)
        panelSizer.Add(wx.StaticText(panel, label = 'Monospace Font'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.monoFont)
        panelSizer.Add(wx.StaticText(panel, label = 'Fullscreen Editor Font'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.fsFont)
        panelSizer.Add(wx.StaticText(panel, label = 'Fullscreen Editor Text Color'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.fsTextColor)
        panelSizer.Add(wx.StaticText(panel, label = 'Fullscreen Editor Background Color'), \
                       flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.fsBgColor)
        panelSizer.Add(wx.StaticText(panel, label = 'Fullscreen Editor Line Spacing'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(fsLineHeightPanel, flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add(self.fastStoryPanel)
        panelSizer.Add((1,2))
        panelSizer.Add(self.flatDesign)
        panelSizer.Add((1,2))
        panelSizer.Add(self.imageArrows)
        panelSizer.Add((1,2))
        panelSizer.Add(self.displayArrows)
        panelSizer.Add((1,2))
        panelSizer.Add(wx.StaticText(panel, label = 'When closing a passage:'), flag = wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add((1,2))
        panelSizer.Add(self.createPassagePrompt)
        panelSizer.Add((1,2))
        panelSizer.Add(self.importImagePrompt)
        panelSizer.Add((1,2))
        panelSizer.Add(self.passageWarnings)
        
        panelSizer.Fit(self)
        borderSizer.Fit(self)
        self.SetIcon(self.app.icon)
        self.Show()
        self.panelSizer = panelSizer
        self.borderSizer = borderSizer

    def getPrefFont(self, key):
        """
        Returns a font saved in preferences as a wx.Font instance.
        """
        return wx.Font(self.app.config.ReadInt(key + 'FontSize'), wx.FONTFAMILY_MODERN, \
                       wx.FONTSTYLE_NORMAL, wx.NORMAL, False, self.app.config.Read(key + 'FontFace'))

    def savePref(self, key, value):
        """
        Saves changes to a preference and sends an update message to the application.
        """
        if isinstance(value, wx.Colour):
            self.app.config.Write(key, value.GetAsString(wx.C2S_HTML_SYNTAX))
        elif type(value) is int:
            self.app.config.WriteInt(key, value)
        elif type(value) is bool:
            self.app.config.WriteBool(key, value)
        else:
            self.app.config.Write(key, value)

        self.app.applyPrefs()

    def saveFontPref(self, key, font):
        """
        Saves a user-chosen font to preference keys, then sends an update message to the application.
        """
        self.app.config.Write(key + 'FontFace', font.GetFaceName())
        self.app.config.WriteInt(key + 'FontSize', font.GetPointSize())
        self.app.applyPrefs()
        self.panelSizer.Fit(self)
        self.borderSizer.Fit(self)


########NEW FILE########
__FILENAME__ = searchpanels
import re, wx
import metrics

class FindPanel(wx.Panel):
    """
    This allows the user to enter a search term and select various
    criteria (i.e. "match case", etc.) There are two callbacks:

    onFind (regexp, flags)
    Regexp corresponds to the user's search, and flags should be used
    when performing that search.

    onClose()
    When the user clicks the Close button.
    """

    def __init__(self, parent, onFind = None, onClose = None):
        self.findCallback = onFind
        self.closeCallback = onClose

        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # find text and label

        findSizer = wx.BoxSizer(wx.HORIZONTAL)

        findSizer.Add(wx.StaticText(self, label = 'Find'), flag = wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, \
                      border = metrics.size('relatedControls'), proportion = 0)
        self.findField = wx.TextCtrl(self)
        findSizer.Add(self.findField, proportion = 1, flag = wx.BOTTOM | wx.EXPAND, \
                      border = metrics.size('relatedControls'))
        sizer.Add(findSizer, flag = wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border = metrics.size('windowBorder'))

        # option checkboxes

        optionSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.caseCheckbox = wx.CheckBox(self, label = 'Match Case')
        self.wholeWordCheckbox = wx.CheckBox(self, label = 'Whole Word')
        self.regexpCheckbox = wx.CheckBox(self, label = 'Regular Expression')

        optionSizer.Add(self.caseCheckbox, flag = wx.BOTTOM | wx.RIGHT, border = metrics.size('relatedControls'))
        optionSizer.Add(self.wholeWordCheckbox, flag = wx.BOTTOM | wx.LEFT | wx.RIGHT, \
                        border = metrics.size('relatedControls'))
        optionSizer.Add(self.regexpCheckbox, flag = wx.BOTTOM | wx.LEFT, \
                        border = metrics.size('relatedControls'))
        sizer.Add(optionSizer, flag = wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, \
                  border = metrics.size('windowBorder'))

        # find and close buttons

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.closeButton = wx.Button(self, label = 'Close')
        self.closeButton.Bind(wx.EVT_BUTTON, self.onClose)

        self.findButton = wx.Button(self, label = 'Find Next')
        self.findButton.Bind(wx.EVT_BUTTON, self.onFind)

        buttonSizer.Add(self.closeButton, flag = wx.TOP | wx.RIGHT, border = metrics.size('buttonSpace'))
        buttonSizer.Add(self.findButton, flag = wx.TOP, border = metrics.size('buttonSpace'))
        sizer.Add(buttonSizer, flag = wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, \
                  border = metrics.size('windowBorder'))
        sizer.Fit(self)

    def focus(self):
        """
        Focuses the proper text input and sets our default button.
        """
        self.findField.SetFocus()
        self.findButton.SetDefault()

    def updateUI(self, event):
        pass

    def onFind(self, event):
        """
        Assembles a regexp based on field values and passes it on to our callback.
        """
        if self.findCallback:
            regexp = self.findField.GetValue()
            flags = None

            if not self.caseCheckbox.GetValue():
                flags = re.IGNORECASE

            if not self.regexpCheckbox.GetValue():
                regexp = re.escape(regexp)

            if self.wholeWordCheckbox.GetValue():
                regexp = r'\b' + regexp + r'\b'

            self.findCallback(regexp, flags)

    def onClose(self, event):
        """
        Passes on a close message to our callback.
        """
        if self.closeCallback: self.closeCallback()

class ReplacePanel(wx.Panel):
    """
    This allows the user to enter a search and replace term and select
    various criteria (i.e. "match case", etc.) There are two callbacks:

    onFind (regexp, flags)
    Regexp corresponds to the user's search, and flags should be used
    when performing that search.

    onReplace (regexp, flags, replaceTerm)
    Like find, only with a replaceTerm.

    onReplaceAll (regexp, flags, replaceTerm)
    Like replace, only the user is signalling that they want to replace
    all instances at once.

    onClose()
    When the user clicks the Close button.

    You may also pass in a parameter to set whether users can perform
    incremental searches, or if they may only replace all.
    """

    def __init__(self, parent, allowIncremental = True, \
                  onFind = None, onReplace = None, onReplaceAll = None, onClose = None):
        self.allowIncremental = allowIncremental
        self.findCallback = onFind
        self.replaceCallback = onReplace
        self.replaceAllCallback = onReplaceAll
        self.closeCallback = onClose

        wx.Panel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        fieldSizer = wx.FlexGridSizer(2, 2)
        fieldSizer.AddGrowableCol(1, 1)

        # find text and label

        fieldSizer.Add(wx.StaticText(self, label = 'Find'), \
                       flag = wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, \
                       border = metrics.size('relatedControls'), proportion = 0)
        self.findField = wx.TextCtrl(self)
        fieldSizer.Add(self.findField, proportion = 1, flag = wx.BOTTOM | wx.EXPAND, \
                       border = metrics.size('relatedControls'))

        # replace text and label

        fieldSizer.Add(wx.StaticText(self, label = 'Replace With'), \
                       flag = wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, \
                       border = metrics.size('relatedControls'), proportion = 0)
        self.replaceField = wx.TextCtrl(self)
        fieldSizer.Add(self.replaceField, proportion = 1, flag = wx.BOTTOM | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, \
                       border = metrics.size('relatedControls'))

        sizer.Add(fieldSizer, flag = wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border = metrics.size('windowBorder'))

        # option checkboxes

        optionSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.caseCheckbox = wx.CheckBox(self, label = 'Match Case')
        self.wholeWordCheckbox = wx.CheckBox(self, label = 'Whole Word')
        self.regexpCheckbox = wx.CheckBox(self, label = 'Regular Expression')

        optionSizer.Add(self.caseCheckbox, flag = wx.BOTTOM | wx.TOP | wx.RIGHT, \
                        border = metrics.size('relatedControls'))
        optionSizer.Add(self.wholeWordCheckbox, flag = wx.BOTTOM | wx.TOP | wx.LEFT | wx.RIGHT, \
                        border = metrics.size('relatedControls'))
        optionSizer.Add(self.regexpCheckbox, flag = wx.BOTTOM | wx.TOP | wx.LEFT, \
                        border = metrics.size('relatedControls'))
        sizer.Add(optionSizer, flag = wx.LEFT | wx.RIGHT, border = metrics.size('windowBorder'))

        # find and close buttons

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.closeButton = wx.Button(self, label = 'Close')
        self.closeButton.Bind(wx.EVT_BUTTON, self.onClose)
        buttonSizer.Add(self.closeButton, flag = wx.TOP | wx.RIGHT, border = metrics.size('buttonSpace'))

        if allowIncremental:
            buttonSizer.Add(wx.Panel(self))
            self.findButton = wx.Button(self, label = 'Find Next')
            self.findButton.Bind(wx.EVT_BUTTON, self.onFind)
            buttonSizer.Add(self.findButton, flag = wx.TOP | wx.LEFT | wx.RIGHT, \
                            border = metrics.size('buttonSpace'))
            self.replaceButton = wx.Button(self, label = 'Replace')
            self.replaceButton.Bind(wx.EVT_BUTTON, self.onReplace)
            buttonSizer.Add(self.replaceButton, flag = wx.TOP | wx.RIGHT, border = metrics.size('buttonSpace'))

        self.replaceAllButton = wx.Button(self, label = 'Replace All')
        self.replaceAllButton.Bind(wx.EVT_BUTTON, self.onReplaceAll)
        buttonSizer.Add(self.replaceAllButton, flag = wx.TOP, border = metrics.size('buttonSpace'))

        sizer.Add(buttonSizer, flag = wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, \
                  border = metrics.size('windowBorder'))
        sizer.Fit(self)

    def focus(self):
        """
        Focuses the proper text input and sets our default button.
        """
        self.findField.SetFocus()
        if self.allowIncremental:
            self.replaceButton.SetDefault()
        else:
            self.replaceAllButton.SetDefault()

    def onFind(self, event):
        """
        Passes a find message to our callback.
        """
        if self.findCallback:
            regexps = self.assembleRegexps()
            self.findCallback(regexps['find'], regexps['flags'])

    def onReplace(self, event):
        """
        Passes a replace message to our callback.
        """
        if self.replaceCallback:
            regexps = self.assembleRegexps()
            self.replaceCallback(regexps['find'], regexps['flags'], regexps['replace'])

    def onReplaceAll(self, event):
        """
        Passes a replace all message to our callback.
        """
        if self.replaceAllCallback:
            regexps = self.assembleRegexps()
            self.replaceAllCallback(regexps['find'], regexps['flags'], regexps['replace'])

    def onClose(self, event):
        """
        Passes on a close message to our callback.
        """
        if self.closeCallback: self.closeCallback()

    def assembleRegexps(self):
        """
        Builds up the regexp the user is searching for. Returns a dictionary with
        keys 'find', 'replace', and 'flags'.
        """
        result = {}
        result['find'] = self.findField.GetValue()
        result['replace'] = self.replaceField.GetValue()
        result['flags'] = None

        if not self.regexpCheckbox.GetValue():
            result['find'] = re.escape(result['find'])

        if not self.caseCheckbox.GetValue():
            result['flags'] = re.IGNORECASE

        if self.wholeWordCheckbox.GetValue():
            result['find'] = r'\b' + result['find'] + r'\b'

        return result

########NEW FILE########
__FILENAME__ = statisticsdialog
import wx, re, locale
from tiddlywiki import TiddlyWiki
import tweeregex
import metrics

class StatisticsDialog(wx.Dialog):
    """
    A StatisticsDialog displays the number of characters, words,
    passages, links, and broken links in a StoryPanel.

    This is not a live count.
    """

    def __init__(self, parent, storyPanel, app, id = wx.ID_ANY):
        wx.Dialog.__init__(self, parent, id, title = 'Story Statistics')
        self.storyPanel = storyPanel

        # layout

        panel = wx.Panel(parent = self)
        self.panelSizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(self.panelSizer)

        # count controls

        countPanel = wx.Panel(parent = panel)
        countPanelSizer = wx.FlexGridSizer(6, 2, metrics.size('relatedControls'), metrics.size('relatedControls'))
        countPanel.SetSizer(countPanelSizer)

        self.characters = wx.StaticText(countPanel)
        countPanelSizer.Add(self.characters, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Characters'))

        self.words = wx.StaticText(countPanel)
        countPanelSizer.Add(self.words, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Words'))

        self.passages = wx.StaticText(countPanel)
        countPanelSizer.Add(self.passages, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Passages'))

        self.links = wx.StaticText(countPanel)
        countPanelSizer.Add(self.links, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Links'))

        self.brokenLinks = wx.StaticText(countPanel)
        countPanelSizer.Add(self.brokenLinks, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Broken Links'))

        self.variablesCount = wx.StaticText(countPanel)
        countPanelSizer.Add(self.variablesCount, flag = wx.ALIGN_RIGHT)
        countPanelSizer.Add(wx.StaticText(countPanel, label = 'Variables Used'))

        self.panelSizer.Add(countPanel, flag = wx.ALL | wx.ALIGN_CENTER, border = metrics.size('relatedControls'))

        self.count(panel)

        okButton = wx.Button(parent = panel, label = 'OK')
        okButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.panelSizer.Add(okButton, flag = wx.ALL | wx.ALIGN_CENTER, border = metrics.size('relatedControls'))

        self.panelSizer.Fit(self)

        size = self.GetSize()
        if size.width < StatisticsDialog.MIN_WIDTH:
            size.width = StatisticsDialog.MIN_WIDTH
            self.SetSize(size)

        self.panelSizer.Layout()
        self.SetIcon(app.icon)
        self.Show()

    def count(self, panel):
        """
        Sets values for the various counts.
        """

        # have to do some trickery here because Python doesn't do
        # closures the way JavaScript does

        counts = { 'words': 0, 'chars': 0, 'passages': 0, 'links': 0, 'brokenLinks': 0 }
        variables = set()
        tags = set()

        def count(widget, counts):
            if widget.passage.isStoryText():
                counts['chars'] += len(widget.passage.text)
                counts['words'] += len(widget.passage.text.split(None))
                counts['passages'] += 1
                counts['links'] += len(widget.passage.links)
                counts['brokenLinks'] += len(widget.getBrokenLinks())
                # Find variables
                iterator = re.finditer(tweeregex.MACRO_REGEX + "|" + tweeregex.LINK_REGEX, widget.passage.text, re.U|re.I);
                for p in iterator:
                    iterator2 = re.finditer(tweeregex.MACRO_PARAMS_REGEX, p.group(0), re.U|re.I)
                    for p2 in iterator2:
                        if p2.group(4):
                            variables.add(p2.group(4));
                # Find tags
                for a in widget.passage.tags:
                    if a not in TiddlyWiki.INFO_TAGS:
                        tags.add(a)

        self.storyPanel.eachWidget(lambda w: count(w, counts))
        for key in counts:
            counts[key] = locale.format('%d', counts[key], grouping = True)

        self.characters.SetLabel(str(counts['chars']))
        self.words.SetLabel(str(counts['words']))
        self.passages.SetLabel(str(counts['passages']))
        self.links.SetLabel(str(counts['links']))
        self.brokenLinks.SetLabel(str(counts['brokenLinks']))
        self.variablesCount.SetLabel(str(len(variables)))

        if len(variables):
            text = ', '.join(sorted(variables));
            variablesCtrl = wx.TextCtrl(panel, -1, size=(StatisticsDialog.MIN_WIDTH*.9, 60), style=wx.TE_MULTILINE|wx.TE_READONLY)
            variablesCtrl.AppendText(text)
            self.panelSizer.Add(variablesCtrl, flag = wx.ALIGN_CENTER)

        if len(tags):
            text = ', '.join(sorted(tags));
            tagsCtrl = wx.TextCtrl(panel, -1, size=(StatisticsDialog.MIN_WIDTH*.9, 60), style=wx.TE_MULTILINE|wx.TE_READONLY)
            tagsCtrl.AppendText(text)
            self.panelSizer.Add(wx.StaticText(panel, label = str(len(tags)) + " Tags"), flag = wx.ALIGN_CENTER)
            self.panelSizer.Add(tagsCtrl, flag = wx.ALIGN_CENTER)

    MIN_WIDTH = 300


########NEW FILE########
__FILENAME__ = storyframe
import sys, re, os, urllib, urlparse, pickle, wx, codecs, time, tempfile, images, version
from wx.lib import imagebrowser
from tiddlywiki import TiddlyWiki
from storypanel import StoryPanel
from passagewidget import PassageWidget
from statisticsdialog import StatisticsDialog
from storysearchframes import StoryFindFrame, StoryReplaceFrame
from storymetadataframe import StoryMetadataFrame

class StoryFrame(wx.Frame):
    """
    A StoryFrame displays an entire story. Its main feature is an
    instance of a StoryPanel, but it also has a menu bar and toolbar.
    """

    def __init__(self, parent, app, state = None):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = StoryFrame.DEFAULT_TITLE, \
                          size = StoryFrame.DEFAULT_SIZE)
        self.app = app
        self.parent = parent
        self.pristine = True    # the user has not added any content to this at all
        self.dirty = False      # the user has not made unsaved changes
        self.storyFormats = {}  # list of available story formats
        self.lastTestBuild = None
        self.title = ""

        # inner state

        if (state):
            self.buildDestination = state.get('buildDestination','')
            self.saveDestination = state.get('saveDestination','')
            self.setTarget(state.get('target','sugarcane').lower())
            self.identity = state.get('identity','')
            self.description = state.get('description','')
            self.storyPanel = StoryPanel(self, app, state = state['storyPanel'])
            self.pristine = False
        else:
            self.buildDestination = ''
            self.saveDestination = ''
            self.identity = ''
            self.description = ''
            self.setTarget('sugarcane')
            self.storyPanel = StoryPanel(self, app)
            
        self.storyPanel.refreshIncludedPassageList()
        
        # window events

        self.Bind(wx.EVT_CLOSE, self.checkClose)
        self.Bind(wx.EVT_UPDATE_UI, self.updateUI)

        # Timer for the auto build file watcher
        self.autobuildtimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.autoBuildTick, self.autobuildtimer)

        # File menu

        fileMenu = wx.Menu()

        fileMenu.Append(wx.ID_NEW, '&New Story\tCtrl-Shift-N')
        self.Bind(wx.EVT_MENU, self.app.newStory, id = wx.ID_NEW)

        fileMenu.Append(wx.ID_OPEN, '&Open Story...\tCtrl-O')
        self.Bind(wx.EVT_MENU, self.app.openDialog, id = wx.ID_OPEN)

        recentFilesMenu = wx.Menu()
        self.recentFiles = wx.FileHistory(self.app.RECENT_FILES)
        self.recentFiles.Load(self.app.config)
        self.app.verifyRecentFiles(self)
        self.recentFiles.UseMenu(recentFilesMenu)
        self.recentFiles.AddFilesToThisMenu(recentFilesMenu)
        fileMenu.AppendMenu(wx.ID_ANY, 'Open &Recent', recentFilesMenu)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 0), id = wx.ID_FILE1)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 1), id = wx.ID_FILE2)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 2), id = wx.ID_FILE3)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 3), id = wx.ID_FILE4)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 4), id = wx.ID_FILE5)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 5), id = wx.ID_FILE6)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 6), id = wx.ID_FILE7)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 7), id = wx.ID_FILE8)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 8), id = wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, lambda e: self.app.openRecent(self, 9), id = wx.ID_FILE9 + 1)

        fileMenu.AppendSeparator()

        fileMenu.Append(wx.ID_SAVE, '&Save Story\tCtrl-S')
        self.Bind(wx.EVT_MENU, self.save, id = wx.ID_SAVE)

        fileMenu.Append(wx.ID_SAVEAS, 'S&ave Story As...\tCtrl-Shift-S')
        self.Bind(wx.EVT_MENU, self.saveAs, id = wx.ID_SAVEAS)

        fileMenu.Append(wx.ID_REVERT_TO_SAVED, '&Revert to Saved')
        self.Bind(wx.EVT_MENU, self.revert, id = wx.ID_REVERT_TO_SAVED)

        fileMenu.AppendSeparator()

        # Import submenu

        importMenu = wx.Menu()

        importMenu.Append(StoryFrame.FILE_IMPORT_HTML, 'Compiled &HTML File...')
        self.Bind(wx.EVT_MENU, self.importHtmlDialog, id = StoryFrame.FILE_IMPORT_HTML)
        importMenu.Append(StoryFrame.FILE_IMPORT_SOURCE, 'Twee Source &Code...')
        self.Bind(wx.EVT_MENU, self.importSourceDialog, id = StoryFrame.FILE_IMPORT_SOURCE)

        fileMenu.AppendMenu(wx.ID_ANY, '&Import', importMenu)

        # Export submenu

        exportMenu = wx.Menu()

        exportMenu.Append(StoryFrame.FILE_EXPORT_SOURCE, 'Twee Source &Code...')
        self.Bind(wx.EVT_MENU, self.exportSource, id = StoryFrame.FILE_EXPORT_SOURCE)

        exportMenu.Append(StoryFrame.FILE_EXPORT_PROOF, '&Proofing Copy...')
        self.Bind(wx.EVT_MENU, self.proof, id = StoryFrame.FILE_EXPORT_PROOF)

        fileMenu.AppendMenu(wx.ID_ANY, '&Export', exportMenu)

        fileMenu.AppendSeparator()

        fileMenu.Append(wx.ID_CLOSE, '&Close Story\tCtrl-W')
        self.Bind(wx.EVT_MENU, self.checkCloseMenu, id = wx.ID_CLOSE)

        fileMenu.Append(wx.ID_EXIT, 'E&xit Twine\tCtrl-Q')
        self.Bind(wx.EVT_MENU, lambda e: self.app.exit(), id = wx.ID_EXIT)



        # Edit menu

        editMenu = wx.Menu()

        editMenu.Append(wx.ID_UNDO, '&Undo\tCtrl-Z')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.undo(), id = wx.ID_UNDO)

        if sys.platform == 'darwin':
            shortcut = 'Ctrl-Shift-Z'
        else:
            shortcut = 'Ctrl-Y'

        editMenu.Append(wx.ID_REDO, '&Redo\t' + shortcut)
        self.Bind(wx.EVT_MENU, lambda e: self.bodyInput.Redo(), id = wx.ID_REDO)

        editMenu.AppendSeparator()

        editMenu.Append(wx.ID_CUT, 'Cu&t\tCtrl-X')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.cutWidgets(), id = wx.ID_CUT)

        editMenu.Append(wx.ID_COPY, '&Copy\tCtrl-C')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.copyWidgets(), id = wx.ID_COPY)

        editMenu.Append(wx.ID_PASTE, '&Paste\tCtrl-V')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.pasteWidgets(), id = wx.ID_PASTE)

        editMenu.Append(wx.ID_DELETE, '&Delete\tDel')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.removeWidgets(e, saveUndo = True), id = wx.ID_DELETE)

        editMenu.Append(wx.ID_SELECTALL, 'Select &All\tCtrl-A')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.eachWidget(lambda i: i.setSelected(True, exclusive = False)), id = wx.ID_SELECTALL)

        editMenu.AppendSeparator()

        editMenu.Append(wx.ID_FIND, 'Find...\tCtrl-F')
        self.Bind(wx.EVT_MENU, self.showFind, id = wx.ID_FIND)

        editMenu.Append(StoryFrame.EDIT_FIND_NEXT, 'Find Next\tCtrl-G')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.findWidgetRegexp(), id = StoryFrame.EDIT_FIND_NEXT)

        if sys.platform == 'darwin':
            shortcut = 'Ctrl-Shift-H'
        else:
            shortcut = 'Ctrl-H'

        editMenu.Append(wx.ID_REPLACE, 'Replace Across Story...\t' + shortcut)
        self.Bind(wx.EVT_MENU, self.showReplace, id = wx.ID_REPLACE)

        editMenu.AppendSeparator()

        editMenu.Append(wx.ID_PREFERENCES, 'Preferences...\tCtrl-,')
        self.Bind(wx.EVT_MENU, self.app.showPrefs, id = wx.ID_PREFERENCES)

        # View menu

        viewMenu = wx.Menu()

        viewMenu.Append(wx.ID_ZOOM_IN, 'Zoom &In\t=')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.zoom('in'), id = wx.ID_ZOOM_IN)

        viewMenu.Append(wx.ID_ZOOM_OUT, 'Zoom &Out\t-')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.zoom('out'), id = wx.ID_ZOOM_OUT)

        viewMenu.Append(wx.ID_ZOOM_FIT, 'Zoom to &Fit\t0')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.zoom('fit'), id = wx.ID_ZOOM_FIT)

        viewMenu.Append(wx.ID_ZOOM_100, 'Zoom &100%\t1')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.zoom(1), id = wx.ID_ZOOM_100)

        viewMenu.AppendSeparator()

        viewMenu.Append(StoryFrame.VIEW_SNAP, 'Snap to &Grid', kind = wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.toggleSnapping(), id = StoryFrame.VIEW_SNAP)

        viewMenu.Append(StoryFrame.VIEW_CLEANUP, '&Clean Up Passages')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.cleanup(), id = StoryFrame.VIEW_CLEANUP)

        viewMenu.AppendSeparator()

        viewMenu.Append(StoryFrame.VIEW_TOOLBAR, '&Toolbar', kind = wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.toggleToolbar, id = StoryFrame.VIEW_TOOLBAR)

        # Story menu

        self.storyMenu = wx.Menu()

        # New Passage submenu

        self.newPassageMenu = wx.Menu()

        self.newPassageMenu.Append(StoryFrame.STORY_NEW_PASSAGE, '&Passage\tCtrl-N')
        self.Bind(wx.EVT_MENU, self.storyPanel.newWidget, id = StoryFrame.STORY_NEW_PASSAGE)

        self.newPassageMenu.AppendSeparator()

        self.newPassageMenu.Append(StoryFrame.STORY_NEW_STYLESHEET, 'S&tylesheet')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.newWidget(text = self.storyPanel.FIRST_CSS, \
                                                                   tags = ['stylesheet']), id = StoryFrame.STORY_NEW_STYLESHEET)

        self.newPassageMenu.Append(StoryFrame.STORY_NEW_SCRIPT, '&Script')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.newWidget(tags = ['script']), id = StoryFrame.STORY_NEW_SCRIPT)

        self.newPassageMenu.Append(StoryFrame.STORY_NEW_ANNOTATION, '&Annotation')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.newWidget(tags = ['annotation']), id = StoryFrame.STORY_NEW_ANNOTATION)

        self.storyMenu.AppendMenu(wx.ID_ANY, 'New', self.newPassageMenu)

        self.storyMenu.Append(wx.ID_EDIT, '&Edit Passage\tCtrl-E')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.eachSelectedWidget(lambda w: w.openEditor(e)), id = wx.ID_EDIT)

        self.storyMenu.Append(StoryFrame.STORY_EDIT_FULLSCREEN, 'Edit in &Fullscreen\tF12')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.eachSelectedWidget(lambda w: w.openEditor(e, fullscreen = True)), \
                  id = StoryFrame.STORY_EDIT_FULLSCREEN)

        self.storyMenu.AppendSeparator()

        self.importImageMenu = wx.Menu()
        self.importImageMenu.Append(StoryFrame.STORY_IMPORT_IMAGE, 'From &File...')
        self.Bind(wx.EVT_MENU, self.importImageDialog, id = StoryFrame.STORY_IMPORT_IMAGE)
        self.importImageMenu.Append(StoryFrame.STORY_IMPORT_IMAGE_URL, 'From Web &URL...')
        self.Bind(wx.EVT_MENU, self.importImageURLDialog, id = StoryFrame.STORY_IMPORT_IMAGE_URL)

        self.storyMenu.AppendMenu(wx.ID_ANY, 'Import &Image', self.importImageMenu)

        self.storyMenu.Append(StoryFrame.STORY_IMPORT_FONT, 'Import &Font...')
        self.Bind(wx.EVT_MENU, self.importFontDialog, id = StoryFrame.STORY_IMPORT_FONT)

        self.storyMenu.AppendSeparator()

        # Story Settings submenu

        self.storySettingsMenu = wx.Menu()

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_START, 'Start')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_START)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_TITLE, 'StoryTitle')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_TITLE)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_SUBTITLE, 'StorySubtitle')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_SUBTITLE)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_AUTHOR, 'StoryAuthor')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_AUTHOR)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_MENU, 'StoryMenu')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_MENU)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_INIT, 'StoryInit')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_INIT)

        # Separator for 'visible' passages (title, subtitle) and those that solely affect compilation
        self.storySettingsMenu.AppendSeparator()

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_SETTINGS, 'StorySettings')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_SETTINGS)

        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_INCLUDES, 'StoryIncludes')
        self.Bind(wx.EVT_MENU, self.createInfoPassage, id = StoryFrame.STORYSETTINGS_INCLUDES)

        self.storySettingsMenu.AppendSeparator()
        
        self.storySettingsMenu.Append(StoryFrame.STORYSETTINGS_HELP, 'About Special Passages')
        self.Bind(wx.EVT_MENU, lambda e: wx.LaunchDefaultBrowser('http://twinery.org/wiki/special_passages'), id = StoryFrame.STORYSETTINGS_HELP)
        
        self.storyMenu.AppendMenu(wx.ID_ANY, 'Special Passages', self.storySettingsMenu)

        self.storyMenu.AppendSeparator()

        # Story Format submenu

        storyFormatMenu = wx.Menu()
        storyFormatCounter = StoryFrame.STORY_FORMAT_BASE

        for key in sorted(app.headers.keys()):
            header = app.headers[key]
            storyFormatMenu.Append(storyFormatCounter, header.label, kind = wx.ITEM_CHECK)
            self.Bind(wx.EVT_MENU, lambda e,target=key: self.setTarget(target), id = storyFormatCounter)
            self.storyFormats[storyFormatCounter] = header
            storyFormatCounter += 1

        if storyFormatCounter:
            storyFormatMenu.AppendSeparator()

        storyFormatMenu.Append(StoryFrame.STORY_FORMAT_HELP, '&About Story Formats')
        self.Bind(wx.EVT_MENU, lambda e: self.app.storyFormatHelp(), id = StoryFrame.STORY_FORMAT_HELP)

        self.storyMenu.AppendMenu(wx.ID_ANY, 'Story &Format', storyFormatMenu)
        
        self.storyMenu.Append(StoryFrame.STORY_METADATA, 'Story &Metadata...')
        self.Bind(wx.EVT_MENU, self.showMetadata, id = StoryFrame.STORY_METADATA)

        self.storyMenu.Append(StoryFrame.STORY_STATS, 'Story &Statistics\tCtrl-I')
        self.Bind(wx.EVT_MENU, self.stats, id = StoryFrame.STORY_STATS)

        # Build menu

        buildMenu = wx.Menu()

        buildMenu.Append(StoryFrame.BUILD_TEST, '&Test Play\tCtrl-T')
        self.Bind(wx.EVT_MENU, self.testBuild, id = StoryFrame.BUILD_TEST)

        buildMenu.Append(StoryFrame.BUILD_TEST_HERE, 'Test Play From Here\tCtrl-Shift-T')
        self.Bind(wx.EVT_MENU, lambda e: self.storyPanel.eachSelectedWidget(lambda w: self.testBuild(startAt = w.passage.title)), \
            id = StoryFrame.BUILD_TEST_HERE)
        
        buildMenu.Append(StoryFrame.BUILD_VERIFY, '&Verify All Passages')
        self.Bind(wx.EVT_MENU, self.verify, id = StoryFrame.BUILD_VERIFY)

        buildMenu.AppendSeparator()
        buildMenu.Append(StoryFrame.BUILD_BUILD, '&Build Story...\tCtrl-B')
        self.Bind(wx.EVT_MENU, self.build, id = StoryFrame.BUILD_BUILD)

        buildMenu.Append(StoryFrame.BUILD_REBUILD, '&Rebuild Story\tCtrl-R')
        self.Bind(wx.EVT_MENU, self.rebuild, id = StoryFrame.BUILD_REBUILD)

        buildMenu.Append(StoryFrame.BUILD_VIEW_LAST, '&Rebuild and View\tCtrl-L')
        self.Bind(wx.EVT_MENU, lambda e: self.rebuild(displayAfter = True), id = StoryFrame.BUILD_VIEW_LAST)
        
        buildMenu.AppendSeparator()
           
        self.autobuildmenuitem = buildMenu.Append(StoryFrame.BUILD_AUTO_BUILD, '&Auto Build', kind = wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.autoBuild, self.autobuildmenuitem)
        buildMenu.Check(StoryFrame.BUILD_AUTO_BUILD, False)

        # Help menu

        helpMenu = wx.Menu()

        helpMenu.Append(StoryFrame.HELP_MANUAL, 'Twine &Wiki')
        self.Bind(wx.EVT_MENU, self.app.openDocs, id = StoryFrame.HELP_MANUAL)

        helpMenu.Append(StoryFrame.HELP_FORUM, 'Twine &Forum')
        self.Bind(wx.EVT_MENU, self.app.openForum, id = StoryFrame.HELP_FORUM)

        helpMenu.Append(StoryFrame.HELP_GITHUB, 'Twine\'s Source Code on &GitHub')
        self.Bind(wx.EVT_MENU, self.app.openGitHub, id = StoryFrame.HELP_GITHUB)

        helpMenu.AppendSeparator()

        helpMenu.Append(wx.ID_ABOUT, '&About Twine')
        self.Bind(wx.EVT_MENU, self.app.about, id = wx.ID_ABOUT)

        # add menus

        self.menus = wx.MenuBar()
        self.menus.Append(fileMenu, '&File')
        self.menus.Append(editMenu, '&Edit')
        self.menus.Append(viewMenu, '&View')
        self.menus.Append(self.storyMenu, '&Story')
        self.menus.Append(buildMenu, '&Build')
        self.menus.Append(helpMenu, '&Help')
        self.SetMenuBar(self.menus)

        # enable/disable paste menu option depending on clipboard contents

        self.clipboardMonitor = ClipboardMonitor(self.menus.FindItemById(wx.ID_PASTE).Enable)
        self.clipboardMonitor.Start(100)

        # extra shortcuts

        self.SetAcceleratorTable(wx.AcceleratorTable([ \
                                    (wx.ACCEL_NORMAL, wx.WXK_RETURN, wx.ID_EDIT), \
                                    (wx.ACCEL_CTRL, wx.WXK_RETURN, StoryFrame.STORY_EDIT_FULLSCREEN) \
                                                      ]))

        iconPath = self.app.iconsPath

        self.toolbar = self.CreateToolBar(style = wx.TB_FLAT | wx.TB_NODIVIDER)
        self.toolbar.SetToolBitmapSize((StoryFrame.TOOLBAR_ICON_SIZE, StoryFrame.TOOLBAR_ICON_SIZE))

        self.toolbar.AddLabelTool(StoryFrame.STORY_NEW_PASSAGE, 'New Passage', \
                                  wx.Bitmap(iconPath + 'newpassage.png'), \
                                  shortHelp = StoryFrame.NEW_PASSAGE_TOOLTIP)
        self.Bind(wx.EVT_TOOL, lambda e: self.storyPanel.newWidget(), id = StoryFrame.STORY_NEW_PASSAGE)

        self.toolbar.AddSeparator()

        self.toolbar.AddLabelTool(wx.ID_ZOOM_IN, 'Zoom In', \
                                  wx.Bitmap(iconPath + 'zoomin.png'), \
                                  shortHelp = StoryFrame.ZOOM_IN_TOOLTIP)
        self.Bind(wx.EVT_TOOL, lambda e: self.storyPanel.zoom('in'), id = wx.ID_ZOOM_IN)

        self.toolbar.AddLabelTool(wx.ID_ZOOM_OUT, 'Zoom Out', \
                                  wx.Bitmap(iconPath + 'zoomout.png'), \
                                  shortHelp = StoryFrame.ZOOM_OUT_TOOLTIP)
        self.Bind(wx.EVT_TOOL, lambda e: self.storyPanel.zoom('out'), id = wx.ID_ZOOM_OUT)

        self.toolbar.AddLabelTool(wx.ID_ZOOM_FIT, 'Zoom to Fit', \
                                  wx.Bitmap(iconPath + 'zoomfit.png'), \
                                  shortHelp = StoryFrame.ZOOM_FIT_TOOLTIP)
        self.Bind(wx.EVT_TOOL, lambda e: self.storyPanel.zoom('fit'), id = wx.ID_ZOOM_FIT)

        self.toolbar.AddLabelTool(wx.ID_ZOOM_100, 'Zoom to 100%', \
                                  wx.Bitmap(iconPath + 'zoom1.png'), \
                                  shortHelp = StoryFrame.ZOOM_ONE_TOOLTIP)
        self.Bind(wx.EVT_TOOL, lambda e: self.storyPanel.zoom(1.0), id = wx.ID_ZOOM_100)

        self.SetIcon(self.app.icon)

        if app.config.ReadBool('storyFrameToolbar'):
            self.showToolbar = True
            self.toolbar.Realize()
        else:
            self.showToolbar = False
            self.toolbar.Realize()
            self.toolbar.Hide()

    def revert(self, event = None):
        """Reverts to the last saved version of the story file."""
        bits = os.path.splitext(self.saveDestination)
        title = '"' + os.path.basename(bits[0]) + '"'
        if title == '""': title = 'your story'

        message = 'Revert to the last saved version of ' + title + '?'
        dialog = wx.MessageDialog(self, message, 'Revert to Saved', wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT)

        if (dialog.ShowModal() == wx.ID_YES):
            self.Destroy()
            self.app.open(self.saveDestination)
            self.dirty = False;
            self.checkClose(None)

    def checkClose(self, event):
        self.checkCloseDo(event,byMenu=False)

    def checkCloseMenu(self, event):
        self.checkCloseDo(event,byMenu=True)

    def checkCloseDo(self, event, byMenu):
        """
        If this instance's dirty flag is set, asks the user if they want to save the changes.
        """

        if (self.dirty):
            bits = os.path.splitext(self.saveDestination)
            title = '"' + os.path.basename(bits[0]) + '"'
            if title == '""': title = 'your story'

            message = 'Do you want to save the changes to ' + title + ' before closing?'
            dialog = wx.MessageDialog(self, message, 'Unsaved Changes', \
                                      wx.ICON_WARNING | wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT)
            result = dialog.ShowModal();
            if (result == wx.ID_CANCEL):
                event.Veto()
                return
            elif (result == wx.ID_NO):
                self.dirty = False
            else:
                self.save(None)
                if self.dirty:
                    event.Veto()
                    return

        # ask all our widgets to close any editor windows

        for w in list(self.storyPanel.widgets):
            if isinstance(w, PassageWidget):
                w.closeEditor()

        if self.lastTestBuild and os.path.exists(self.lastTestBuild.name):
            try:
                os.remove(self.lastTestBuild.name)
            except OSError, ex:
                print >>sys.stderr, 'Failed to remove lastest test build:', ex
        self.lastTestBuild = None

        self.app.removeStory(self, byMenu)
        if event != None:
            event.Skip()
        self.Destroy()

    def saveAs(self, event = None):
        """Asks the user to choose a file to save state to, then passes off control to save()."""
        dialog = wx.FileDialog(self, 'Save Story As', os.getcwd(), "", \
                         "Twine Story (*.tws)|*.tws|Twine Story without private content [copy] (*.tws)|*.tws", \
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            if dialog.GetFilterIndex() == 0:
                self.saveDestination = dialog.GetPath()
                self.app.config.Write('savePath', os.getcwd())
                self.app.addRecentFile(self.saveDestination)
                self.save(None)
            elif dialog.GetFilterIndex() == 1:
                npsavedestination = dialog.GetPath()
                try:
                    dest = open(npsavedestination, 'wb')
                    pickle.dump(self.serialize_noprivate(npsavedestination), dest)
                    dest.close()
                    self.app.addRecentFile(npsavedestination)
                except:
                    self.app.displayError('saving your story')

        dialog.Destroy()

    def exportSource(self, event = None):
        """Asks the user to choose a file to export source to, then exports the wiki."""
        dialog = wx.FileDialog(self, 'Export Source Code', os.getcwd(), "", \
                               'Twee File (*.twee;* .tw; *.txt)|*.twee;*.tw;*.txt|All Files (*.*)|*.*', wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR)
        if dialog.ShowModal() == wx.ID_OK:
            try:
                path = dialog.GetPath()
                tw = TiddlyWiki()

                for widget in self.storyPanel.widgets: tw.addTiddler(widget.passage)
                dest = codecs.open(path, 'w', 'utf-8-sig', 'replace')
                order = map(lambda w: w.passage.title, self.storyPanel.sortedWidgets())
                dest.write(tw.toTwee(order))
                dest.close()
            except:
                self.app.displayError('exporting your source code')

        dialog.Destroy()

    def importHtmlDialog(self, event = None):
        """Asks the user to choose a file to import HTML tiddlers from, then imports into the current story."""
        dialog = wx.FileDialog(self, 'Import From Compiled HTML', os.getcwd(), '', \
                               'HTML Twine game (*.html;* .htm; *.txt)|*.html;*.htm;*.txt|All Files (*.*)|*.*', wx.FD_OPEN | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            self.importHtml(dialog.GetPath())

    def importHtml(self, path):
        """Imports the tiddler objects in a HTML file into the story."""
        self.importSource(path, True)

    def importSourceDialog(self, event = None):
        """Asks the user to choose a file to import source from, then imports into the current story."""
        dialog = wx.FileDialog(self, 'Import Source Code', os.getcwd(), '', \
                               'Twee File (*.twee;* .tw; *.txt)|*.twee;*.tw;*.txt|All Files (*.*)|*.*', wx.FD_OPEN | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            self.importSource(dialog.GetPath())

    def importSource(self, path, html = False):
        """Imports the tiddler objects in a Twee file into the story."""

        try:
            # have a TiddlyWiki object parse it for us
            tw = TiddlyWiki()
            if html:
                tw.addHtmlFromFilename(path)
            else:
                tw.addTweeFromFilename(path)

            allWidgetTitles = []

            self.storyPanel.eachWidget(lambda e: allWidgetTitles.append(e.passage.title))

            # add passages for each of the tiddlers the TiddlyWiki saw
            if len(tw.tiddlers):
                removedWidgets = []
                skippedTitles = []

                # Check for passage title conflicts
                for t in tw.tiddlers:

                    if t in allWidgetTitles:
                        dialog = wx.MessageDialog(self, 'There is already a passage titled "' + t \
                                              + '" in this story. Replace it with the imported passage?', 'Passage Title Conflict', \
                                              wx.ICON_WARNING | wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT);
                        check = dialog.ShowModal();
                        if check == wx.ID_YES:
                            removedWidgets.append(t)
                        elif check == wx.ID_CANCEL:
                            return
                        elif check == wx.ID_NO:
                            skippedTitles.append(t)

                # Remove widgets elected to be replaced
                for t in removedWidgets:
                    self.storyPanel.removeWidget(self.storyPanel.findWidget(t))

                # Insert widgets now
                lastpos = [0, 0]
                addedWidgets = []
                for t in tw.tiddlers:
                    t = tw.tiddlers[t]
                    if t.title in skippedTitles:
                        continue
                    new = self.storyPanel.newWidget(title = t.title, tags = t.tags, text = t.text, quietly = True,
                                                    pos = t.pos if t.pos else lastpos)
                    lastpos = new.pos
                    addedWidgets.append(new)

                self.setDirty(True, 'Import')
                for t in addedWidgets:
                    t.clearPaintCache()
            else:
                if html:
                    what = "compiled HTML"
                else:
                    what = "Twee source"
                dialog = wx.MessageDialog(self, 'No passages were found in this file. Make sure ' + \
                                          'this is a ' + what + ' file.', 'No Passages Found', \
                                          wx.ICON_INFORMATION | wx.OK)
                dialog.ShowModal()
        except:
            self.app.displayError('importing')

    def importImageURL(self, url, showdialog = True):
        """
        Downloads the image file from the url and creates a passage.
        Returns the resulting passage name, or None
        """
        try:
            # Download the file
            urlfile = urllib.urlopen(url)
            path = urlparse.urlsplit(url)[2]
            title = os.path.splitext(os.path.basename(path))[0]
            file = urlfile.read().encode('base64').replace('\n', '')

            # Now that the file's read, check the info
            maintype = urlfile.info().getmaintype();
            if maintype != "image":
                raise Exception("The server served "+maintype+" instead of an image.")
            # Convert the file
            mimeType = urlfile.info().gettype()
            urlfile.close()
            text = "data:"+mimeType+";base64,"+file
            return self.finishImportImage(text, title, showdialog=showdialog)
        except:
            self.app.displayError('importing from the web')
            return None
            
    def importImageURLDialog(self, event = None):
        dialog = wx.TextEntryDialog(self, "Enter the image URL (GIFs, JPEGs, PNGs, SVGs and WebPs only)", "Import Image from Web", "http://")
        if dialog.ShowModal() == wx.ID_OK:
            self.importImageURL(dialog.GetValue())

    def importImageFile(self, file, replace = None, showdialog = True):
        """
        Perform the file I/O to import an image file, then add it as an image passage.
        Returns the name of the resulting passage, or None
        """
        try:
            if not replace:
                text, title = self.openFileAsBase64(file)
                return self.finishImportImage(text, title, showdialog=showdialog)
            else:
                replace.passage.text = self.openFileAsBase64(file)[0]
                replace.updateBitmap()
                return replace.passage.title
        except IOError:
            self.app.displayError('importing an image')
            return None
        
    def importImageDialog(self, event = None, useImageDialog = False, replace = None):
        """Asks the user to choose an image file to import, then imports into the current story.
           replace is a Tiddler, if any, that will be replaced by the image."""
        # Use the wxPython image browser?
        if useImageDialog:
            dialog = imagebrowser.ImageDialog(self, os.getcwd())
            dialog.ChangeFileTypes([ ('Web Image File', '*.(gif|jpg|jpeg|png|webp|svg)')])
            dialog.ResetFiles()
        else:
            dialog = wx.FileDialog(self, 'Import Image File', os.getcwd(), '', \
                                   'Web Image File|*.gif;*.jpg;*.jpeg;*.png;*.webp;*.svg|All Files (*.*)|*.*', wx.FD_OPEN | wx.FD_CHANGE_DIR)
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetFile() if useImageDialog else dialog.GetPath()
            self.importImageFile(file, replace)

    def importFontDialog(self, event = None):
        """Asks the user to choose a font file to import, then imports into the current story."""
        dialog = wx.FileDialog(self, 'Import Font File', os.getcwd(), '', \
                                   'Web Font File (.ttf, .otf, .woff, .svg)|*.ttf;*.otf;*.woff;*.svg|All Files (*.*)|*.*', wx.FD_OPEN | wx.FD_CHANGE_DIR)
        if dialog.ShowModal() == wx.ID_OK:
            self.importFont(dialog.GetPath())

    def openFileAsBase64(self, file):
        """Opens a file and returns its base64 representation, expressed as a Data URI with MIME type"""
        file64 = open(file, 'rb').read().encode('base64').replace('\n', '')
        title, mimeType = os.path.splitext(os.path.basename(file))
        return (images.AddURIPrefix(file64, mimeType[1:]), title)

    def newTitle(self, title):
        """ Check if a title is being used, and increment its number if it is."""
        while self.storyPanel.passageExists(title):
            try:
                match = re.search(r'(\s\d+)$', title)
                if match:
                    title = title[:match.start(1)] + " " + str(int(match.group(1)) + 1)
                else:
                    title += " 2"
            except: pass
        return title

    def finishImportImage(self, text, title, showdialog = True):
        """Imports an image into the story as an image passage."""
        # Check for title usage
        title = self.newTitle(title)

        self.storyPanel.newWidget(text = text, title = title, tags = ['Twine.image'])
        if showdialog:
            dialog = wx.MessageDialog(self, 'Image file imported successfully.\n' + \
                                      'You can include the image in your passages with this syntax:\n\n' + \
                                      '[img[' + title + ']]', 'Image added', \
                                      wx.ICON_INFORMATION | wx.OK)
            dialog.ShowModal()
        return title

    def importFont(self, file, showdialog = True):
        """Imports a font into the story as a font passage."""
        try:
            text, title = self.openFileAsBase64(file)

            title2 = self.newTitle(title)

            # Wrap in CSS @font-face declaration
            text = \
"""font[face=\"""" + title + """\"] {
    font-family: \"""" + title + """\";
}
@font-face {
    font-family: \"""" + title + """\";

    src: url(""" + text + """);
}"""

            self.storyPanel.newWidget(text = text, title = title2, tags = ['stylesheet'])
            if showdialog:
                dialog = wx.MessageDialog(self, 'Font file imported successfully.\n' + \
                                          'You can use the font in your stylesheets with this CSS attribute syntax:\n\n' + \
                                          'font-family: '+ title + ";", 'Font added', \
                                          wx.ICON_INFORMATION | wx.OK)
                dialog.ShowModal()
            return True
        except IOError:
            self.app.displayError('importing a font')
            return False

    def defaultTextForPassage(self, title):
        if title == 'Start':
            return "Your story will display this passage first. Edit it by double clicking it."

        elif title == 'StoryTitle':
            return self.DEFAULT_TITLE

        elif title == 'StorySubtitle':
            return "This text appears below the story's title."

        elif title == 'StoryAuthor':
            return "Anonymous"

        elif title == 'StoryMenu':
            return "This passage's text will be included in the menu for this story."

        elif title == 'StoryInit':
            return """/% Place your story's setup code in this passage.
Any macros in this passage will be run before the Start passage (or any passage you wish to Test Play) is run. %/
"""

        elif title == 'StoryIncludes':
            return """List the file paths of any .twee or .tws files that should be merged into this story when it's built.

You can also include URLs of .tws and .twee files, too.
"""

        else:
            return ""

    def createInfoPassage(self, event):
        """Open an editor for a special passage; create it if it doesn't exist yet."""

        id = event.GetId()
        title = self.storySettingsMenu.FindItemById(id).GetLabel()

        # What to do about StoryIncludes files?
        editingWidget = self.storyPanel.findWidget(title)
        if editingWidget is None:
            editingWidget = self.storyPanel.newWidget(title = title, text = self.defaultTextForPassage(title))

        editingWidget.openEditor()

    def save(self, event = None):
        if (self.saveDestination == ''):
            self.saveAs()
            return

        try:
            dest = open(self.saveDestination, 'wb')
            pickle.dump(self.serialize(), dest)
            dest.close()
            self.setDirty(False)
            self.app.config.Write('LastFile', self.saveDestination)
        except:
            self.app.displayError('saving your story')

    def verify(self, event = None):
        """Runs the syntax checks on all passages."""
        noprobs = True
        for widget in self.storyPanel.widgets:
            result = widget.verifyPassage(self)
            if result == -1: break
            elif result > 0: noprobs = False
        if noprobs:
            wx.MessageDialog(self, "No obvious problems found in "+str(len(self.storyPanel.widgets)) + " passage" + ("s." if len(self.storyPanel.widgets)>1 else ".")\
                             + "\n\n(There may still be problems when the story is played, of course.)",
                             "Verify All Passages", wx.ICON_INFORMATION).ShowModal()

    def build(self, event = None):
        """Asks the user to choose a location to save a compiled story, then passed control to rebuild()."""
        path, filename = os.path.split(self.buildDestination)
        dialog = wx.FileDialog(self, 'Build Story', path or os.getcwd(), filename, \
                         "Web Page (*.html)|*.html", \
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            self.buildDestination = dialog.GetPath()
            self.rebuild(None, displayAfter = True)

        dialog.Destroy()

    def testBuild(self, event = None, startAt = ''):
        self.rebuild(temp = True, startAt = startAt, displayAfter = True)

    def rebuild(self, event = None, temp = False, displayAfter = False, startAt = ''):
        """
        Builds an HTML version of the story. Pass whether to use a temp file, and/or open the file afterwards.
        """
        try:
            # assemble our tiddlywiki and write it out
            hasstartpassage = False
            tw = TiddlyWiki()
            for widget in self.storyPanel.widgets:
                if widget.passage.title == 'StoryIncludes':
                    
                    def callback(passage, tw=tw):
                        # Check for uniqueness
                        if self.storyPanel.findWidget(passage.title):
                            # Not bothering with a Yes/No dialog here.
                            raise Exception('A passage titled "'+ passage.title + '" is already present in this story')
                        elif tw.hasTiddler(passage.title):
                            raise Exception('A passage titled "'+ passage.title + '" has been included by a previous StoryIncludes file')

                        tw.addTiddler(passage)
                        self.storyPanel.addIncludedPassage(passage.title)
                    
                    self.readIncludes(widget.passage.text.splitlines(), callback)
                    # Might as well suppress the warning for a StoryIncludes file
                    hasstartpassage = True
                    
                elif TiddlyWiki.NOINCLUDE_TAGS.isdisjoint(widget.passage.tags):
                    widget.passage.pos = widget.pos
                    tw.addTiddler(widget.passage)
                    if widget.passage.title == "Start":
                        hasstartpassage = True

            # is there a Start passage?
            if hasstartpassage == False:
                self.app.displayError('building your story because there is no "Start" passage. ' + "\n"
                                      + 'Your story will build but the web browser will not be able to run the story. ' + "\n"
                                      + 'Please add a passage with the title "Start"')

            
            for widget in self.storyPanel.widgets:
                # Decode story settings
                if widget.passage.title == 'StorySettings':
                    lines = widget.passage.text.splitlines()
                    for line in lines:
                        if ':' in line:
                            (skey,svalue) = line.split(':')
                            skey = skey.strip().lower()
                            svalue = svalue.strip()
                            tw.storysettings[skey] = svalue
                    break

            # Write the output file
            header = self.app.headers.get(self.target)
            metadata = {'description': self.description, 'identity': self.identity}
            if temp:
                # This implicitly closes the previous test build
                if self.lastTestBuild and os.path.exists(self.lastTestBuild.name):
                    os.remove(self.lastTestBuild.name)
                path = (os.path.exists(self.buildDestination) and self.buildDestination) \
                    or (os.path.exists(self.saveDestination) and self.saveDestination) or None
                self.lastTestBuild = tempfile.NamedTemporaryFile(mode = 'wb', suffix = ".html", delete = False,
                    dir = (path and os.path.dirname(path)) or None)
                self.lastTestBuild.write(tw.toHtml(self.app, header, startAt = startAt, defaultName = self.title, metadata = metadata).encode('utf-8-sig'))
                self.lastTestBuild.close()
                if displayAfter: self.viewBuild(name = self.lastTestBuild.name)
            else:
                dest = open(self.buildDestination, 'wb')
                dest.write(tw.toHtml(self.app, header, defaultName = self.title, metadata = metadata).encode('utf-8-sig'))
                dest.close()
                if displayAfter: self.viewBuild()
        except:
            self.app.displayError('building your story')
    
    def getLocalDir(self):
        if self.saveDestination == '':
            return os.getcwd()
        else:
            return os.path.dirname(self.saveDestination)
    
    def readIncludes(self, lines, callback):
        """
        Examines all of the source files included via StoryIncludes, and performs a callback on each passage found.
        
        callback is a function that takes 1 Tiddler object.
        """
        twinedocdir = self.getLocalDir()
        
        excludetags = TiddlyWiki.NOINCLUDE_TAGS
        self.storyPanel.clearIncludedPassages()
        for line in lines:
            try:
                if line.strip():
                    extension = os.path.splitext(line)[1]
                    if extension == '.tws':
                        if any(line.startswith(t) for t in ['http://', 'https://', 'ftp://']):
                            openedFile = urllib.urlopen(line)
                        else:
                            openedFile = open(os.path.join(twinedocdir, line), 'r')
                        s = StoryFrame(None, app = self.app, state = pickle.load(openedFile))
                        openedFile.close()

                        for widget in s.storyPanel.widgets:
                            if excludetags.isdisjoint(widget.passage.tags):
                                callback(widget.passage)
                        s.Destroy()

                    elif extension == '.tw' or extension == '.txt' or extension == '.twee':

                        if any(line.startswith(t) for t in ['http://', 'https://', 'ftp://']):
                            openedFile = urllib.urlopen(line)
                            s = openedFile.read()
                            openedFile.close()
                            t = tempfile.NamedTemporaryFile(delete=False)
                            cleanuptempfile = True
                            t.write(s)
                            t.close()
                            filename = t.name
                        else:
                            filename = line
                            cleanuptempfile = False

                        tw1 = TiddlyWiki()
                        tw1.addTweeFromFilename(filename)
                        if cleanuptempfile: os.remove(filename)
                        tiddlerkeys = tw1.tiddlers.keys()
                        for tiddlerkey in tiddlerkeys:
                            passage = tw1.tiddlers[tiddlerkey]
                            if excludetags.isdisjoint(passage.tags):
                                callback(passage)

                    else:
                        raise Exception('File format not recognized')
            except:
                self.app.displayError('reading the file named "' + line + '" which is referred to by the StoryIncludes passage\n')

    def viewBuild(self, event = None, name = ''):
        """
        Opens the last built file in a Web browser.
        """
        path = u'file://' + urllib.pathname2url((name or self.buildDestination).encode('utf-8'))
        path = path.replace('file://///', 'file:///')
        wx.LaunchDefaultBrowser(path)

    def autoBuild(self, event = None):
        """
        Toggles the autobuild feature
        """
        if self.autobuildmenuitem.IsChecked():
            self.autobuildtimer.Start(5000)
            self.autoBuildStart();
        else:
            self.autobuildtimer.Stop()

    def autoBuildTick(self, event = None):
        """
        Called whenever the autobuild timer checks up on things
        """
        for pathname, oldmtime in self.autobuildfiles.iteritems():
            newmtime = os.stat(pathname).st_mtime
            if newmtime != oldmtime:
                #print "Auto rebuild triggered by: ", pathname
                self.autobuildfiles[pathname] = newmtime
                self.rebuild()
                break

    def autoBuildStart(self):
        self.autobuildfiles = { }
        if self.saveDestination == '':
            twinedocdir = os.getcwd()
        else:
            twinedocdir = os.path.dirname(self.saveDestination)

        for widget in self.storyPanel.widgets:
            if widget.passage.title == 'StoryIncludes':
                for line in widget.passage.text.splitlines():
                    if (not line.startswith(t) for t in ['http://', 'https://', 'ftp://']):
                        pathname = os.path.join(twinedocdir, line)
                        # Include even non-existant files, in case they eventually appear
                        mtime = os.stat(pathname).st_mtime
                        self.autobuildfiles[pathname] = mtime

    def stats(self, event = None):
        """
        Displays a StatisticsDialog for this frame.
        """

        statFrame = StatisticsDialog(parent = self, storyPanel = self.storyPanel, app = self.app)
        statFrame.ShowModal()

    def showMetadata(self, event = None):
        """
        Shows a StoryMetadataFrame for this frame.
        """

        if (not hasattr(self, 'metadataFrame')):
            self.metadataFrame = StoryMetadataFrame(parent = self, app = self.app)
        else:
            try:
                self.metadataFrame.Raise()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'metadataFrame')
                self.showMetadata(event)

    def showFind(self, event = None):
        """
        Shows a StoryFindFrame for this frame.
        """

        if (not hasattr(self, 'findFrame')):
            self.findFrame = StoryFindFrame(self.storyPanel, self.app)
        else:
            try:
                self.findFrame.Raise()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'findFrame')
                self.showFind(event)

    def showReplace(self, event = None):
        """
        Shows a StoryReplaceFrame for this frame.
        """
        if (not hasattr(self, 'replaceFrame')):
            self.replaceFrame = StoryReplaceFrame(self.storyPanel, self.app)
        else:
            try:
                self.replaceFrame.Raise()
            except wx._core.PyDeadObjectError:
                # user closed the frame, so we need to recreate it
                delattr(self, 'replaceFrame')
                self.showReplace(event)

    def proof(self, event = None):
        """
        Builds an RTF version of the story. Pass whether to open the destination file afterwards.
        """

        # ask for our destination

        dialog = wx.FileDialog(self, 'Proof Story', os.getcwd(), "", \
                         "RTF Document (*.rtf)|*.rtf", \
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        try:
            # open destination for writing

            dest = open(path, 'w')

            # assemble our tiddlywiki and write it out

            tw = TiddlyWiki()
            for widget in self.storyPanel.sortedWidgets():
                tw.addTiddler(widget.passage)

            order = map(lambda w: w.passage.title, self.storyPanel.sortedWidgets())
            dest.write(tw.toRtf(order))
            dest.close()
        except:
            self.app.displayError('building a proofing copy of your story')

    def setTarget(self, target):
        self.target = target
        self.header = self.app.headers[target]

    def updateUI(self, event = None):
        """Adjusts menu items to reflect the current state."""

        hasSelection = self.storyPanel.hasSelection()
        multipleSelection = self.storyPanel.hasMultipleSelection()

        # window title

        if self.saveDestination == '':
            self.title = StoryFrame.DEFAULT_TITLE
        else:
            bits = os.path.splitext(self.saveDestination)
            self.title = os.path.basename(bits[0])

        percent = str(int(round(self.storyPanel.scale * 100)))
        dirty = ''
        if self.dirty: dirty = ' *'

        self.SetTitle(self.title + dirty + ' (' + percent + '%) ' + '- ' + self.app.NAME + ' ' + version.versionString)

        if not self.menus: return

        # File menu

        revertItem = self.menus.FindItemById(wx.ID_REVERT_TO_SAVED)
        revertItem.Enable(self.saveDestination != '' and self.dirty)

        # Edit menu

        undoItem = self.menus.FindItemById(wx.ID_UNDO)
        undoItem.Enable(self.storyPanel.canUndo())
        if self.storyPanel.canUndo():
            undoItem.SetText('Undo ' + self.storyPanel.undoAction() + '\tCtrl-Z')
        else:
            undoItem.SetText("Can't Undo\tCtrl-Z")

        redoItem = self.menus.FindItemById(wx.ID_REDO)
        redoItem.Enable(self.storyPanel.canRedo())
        if self.storyPanel.canRedo():
            redoItem.SetText('Redo ' + self.storyPanel.redoAction() + '\tCtrl-Y')
        else:
            redoItem.SetText("Can't Redo\tCtrl-Y")

        cutItem = self.menus.FindItemById(wx.ID_CUT)
        cutItem.Enable(hasSelection)
        copyItem = self.menus.FindItemById(wx.ID_COPY)
        copyItem.Enable(hasSelection)
        deleteItem = self.menus.FindItemById(wx.ID_DELETE)
        deleteItem.Enable(hasSelection)

        findAgainItem = self.menus.FindItemById(StoryFrame.EDIT_FIND_NEXT)
        findAgainItem.Enable(self.storyPanel.lastSearchRegexp != None)

        # View menu

        toolbarItem = self.menus.FindItemById(StoryFrame.VIEW_TOOLBAR)
        toolbarItem.Check(self.showToolbar)
        snapItem = self.menus.FindItemById(StoryFrame.VIEW_SNAP)
        snapItem.Check(self.storyPanel.snapping)

        # Story menu, Build menu

        editItem = self.menus.FindItemById(wx.ID_EDIT)
        testItem = self.menus.FindItemById(StoryFrame.BUILD_TEST_HERE)
        editItem.SetItemLabel("&Edit Passage");
        editItem.Enable(False)
        testItem.SetItemLabel("Test Play From Here");
        testItem.Enable(False)
        if hasSelection and not multipleSelection:
            widget = self.storyPanel.selectedWidget();
            editItem.SetItemLabel("Edit \"" + widget.passage.title + "\"")
            editItem.Enable(True)
            # Only allow test plays from story pasages
            if widget.passage.isStoryPassage():
                testItem.SetItemLabel("Test Play From \"" + widget.passage.title + "\"")
                testItem.Enable(True)

        editFullscreenItem = self.menus.FindItemById(StoryFrame.STORY_EDIT_FULLSCREEN)
        editFullscreenItem.Enable(hasSelection and not multipleSelection)

        rebuildItem = self.menus.FindItemById(StoryFrame.BUILD_REBUILD)
        rebuildItem.Enable(self.buildDestination != '')

        viewLastItem = self.menus.FindItemById(StoryFrame.BUILD_VIEW_LAST)
        viewLastItem.Enable(self.buildDestination != '')

        autoBuildItem = self.menus.FindItemById(StoryFrame.BUILD_AUTO_BUILD)
        autoBuildItem.Enable(self.buildDestination != '' and self.storyPanel.findWidget("StoryIncludes") != None)

        # Story format submenu
        for key in self.storyFormats:
            self.menus.FindItemById(key).Check(self.target == self.storyFormats[key].id)

    def toggleToolbar(self, event = None):
        """Toggles the toolbar onscreen."""
        if (self.showToolbar):
            self.showToolbar = False
            self.toolbar.Hide()
            self.app.config.WriteBool('storyFrameToolbar', False)
        else:
            self.showToolbar = True
            self.toolbar.Show()
            self.app.config.WriteBool('storyFrameToolbar', True)
        self.SendSizeEvent()

    def setDirty(self, value, action = None):
        """
        Sets the dirty flag to the value passed. Make sure to use this instead of
        setting the dirty property directly, as this method automatically updates
        the pristine property as well.

        If you pass an action parameter, this action will be saved for undoing under
        that name.
        """
        self.dirty = value
        self.pristine = False

        if value is True and action:
            self.storyPanel.pushUndo(action)

    def applyPrefs(self):
        """Passes on the apply message to child widgets."""
        self.storyPanel.eachWidget(lambda w: w.applyPrefs())
        self.storyPanel.Refresh()

    def serialize(self):
        """Returns a dictionary of state suitable for pickling."""
        return { 'target': self.target, 'buildDestination': self.buildDestination, \
                 'saveDestination': self.saveDestination, \
                 'storyPanel': self.storyPanel.serialize(),
                 'identity': self.identity,
                 'description': self.description }

    def serialize_noprivate(self, dest):
        """Returns a dictionary of state suitable for pickling."""
        return { 'target': self.target, 'buildDestination': '', \
                 'saveDestination': dest, \
                 'storyPanel': self.storyPanel.serialize_noprivate() }

    def __repr__(self):
        return "<StoryFrame '" + self.saveDestination + "'>"

    def getHeader(self):
        """Returns the current selected target header for this Story Frame."""
        return self.header

    # menu constants
    # (that aren't already defined by wx)

    FILE_IMPORT_SOURCE = 101
    FILE_EXPORT_PROOF = 102
    FILE_EXPORT_SOURCE = 103
    FILE_IMPORT_HTML = 104

    EDIT_FIND_NEXT = 201

    VIEW_SNAP = 301
    VIEW_CLEANUP = 302
    VIEW_TOOLBAR = 303

    [STORY_NEW_PASSAGE, STORY_NEW_SCRIPT, STORY_NEW_STYLESHEET, STORY_NEW_ANNOTATION, STORY_EDIT_FULLSCREEN, STORY_STATS, STORY_METADATA, \
     STORY_IMPORT_IMAGE, STORY_IMPORT_IMAGE_URL, STORY_IMPORT_FONT, STORY_FORMAT_HELP, STORYSETTINGS_START, STORYSETTINGS_TITLE, STORYSETTINGS_SUBTITLE, STORYSETTINGS_AUTHOR, \
     STORYSETTINGS_MENU, STORYSETTINGS_SETTINGS, STORYSETTINGS_INCLUDES, STORYSETTINGS_INIT, STORYSETTINGS_HELP] = range(401,421)

    STORY_FORMAT_BASE = 501

    [BUILD_VERIFY, BUILD_TEST, BUILD_TEST_HERE, BUILD_BUILD, BUILD_REBUILD, BUILD_VIEW_LAST, BUILD_AUTO_BUILD] = range(601, 608)

    [HELP_MANUAL, HELP_GROUP, HELP_GITHUB, HELP_FORUM] = range(701,705)

    # tooltip labels

    NEW_PASSAGE_TOOLTIP = 'Add a new passage to your story'
    ZOOM_IN_TOOLTIP = 'Zoom in'
    ZOOM_OUT_TOOLTIP = 'Zoom out'
    ZOOM_FIT_TOOLTIP = 'Zoom so all passages are visible onscreen'
    ZOOM_ONE_TOOLTIP = 'Zoom to 100%'

    # size constants

    DEFAULT_SIZE = (800, 600)
    TOOLBAR_ICON_SIZE = 32

    # misc stuff

    DEFAULT_TITLE = 'Untitled Story'


class ClipboardMonitor(wx.Timer):
    """
    Monitors the clipboard and notifies a callback when the format of the contents
    changes from or to Twine passage data.
    """

    def __init__(self, callback):
        wx.Timer.__init__(self)
        self.callback = callback
        self.dataFormat = wx.CustomDataFormat(StoryPanel.CLIPBOARD_FORMAT)
        self.state = None

    def Notify(self):
        if wx.TheClipboard.Open():
            newState = wx.TheClipboard.IsSupported(self.dataFormat)
            wx.TheClipboard.Close()
            if newState != self.state:
                self.state = newState
                self.callback(newState)

########NEW FILE########
__FILENAME__ = storymetadataframe
import wx
import metrics

class StoryMetadataFrame(wx.Frame):
    """
    Changes automatically update as the user makes them;
    """

    def __init__(self, app, parent = None):
        self.app = app
        self.parent = parent
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = parent.title + ' Metadata', \
                          style = wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.CAPTION | wx.SYSTEM_MENU)

        panel = wx.Panel(parent = self, id = wx.ID_ANY)
        borderSizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(borderSizer)
        panelSizer = wx.FlexGridSizer(8, 1, metrics.size('relatedControls'), metrics.size('relatedControls'))
        borderSizer.Add(panelSizer, flag = wx.ALL, border = metrics.size('windowBorder'))
        
        ctrlset = {}
        
        for name, desc in \
            [
              ("identity", ("What your work identifies as:",
                            "Is it a game, a story, a poem, or something else?\n(This is used for dialogs and error messages only.)",
                            False)),
              ("description", ("A short description of your work:",
                               "This is inserted in the HTML file's <meta> description tag, used by\nsearch engines and other automated tools.",
                               True))
            ]:
            textlabel = wx.StaticText(panel, label = desc[0])
            if desc[2]:
                textctrl = wx.TextCtrl(panel, size=(200,60), style=wx.TE_MULTILINE)
            else:
                textctrl = wx.TextCtrl(panel, size=(200,-1))
            textctrl.SetValue(getattr(parent, name, ''))
            textctrl.Bind(wx.EVT_TEXT, lambda e, name=name, textctrl=textctrl:
                              self.saveSetting(name,textctrl.GetValue()))
            
            hSizer = wx.BoxSizer(wx.HORIZONTAL)
            hSizer.Add(textlabel,1,wx.ALIGN_LEFT|wx.ALIGN_TOP)
            hSizer.Add(textctrl,1,wx.EXPAND)
            panelSizer.Add(hSizer,flag=wx.ALL|wx.EXPAND)
            panelSizer.Add(wx.StaticText(panel, label = desc[1]))
            panelSizer.Add((1,2))
        
        panelSizer.Fit(self)
        borderSizer.Fit(self)
        self.SetIcon(self.app.icon)
        self.Show()
        self.panelSizer = panelSizer
        self.borderSizer = borderSizer

    def saveSetting(self, name, value):
        setattr(self.parent, name, value)
        self.parent.setDirty(True)

########NEW FILE########
__FILENAME__ = storypanel
import sys, math, wx, re, os, pickle
import geometry, time
from tiddlywiki import TiddlyWiki
from passagewidget import PassageWidget

class StoryPanel(wx.ScrolledWindow):
    """
    A StoryPanel is a container for PassageWidgets. It translates
    between logical coordinates and pixel coordinates as the user
    zooms in and out, and communicates those changes to its widgets.

    A discussion on coordinate systems: logical coordinates are notional,
    and do not change as the user zooms in and out. Pixel coordinates
    are extremely literal: (0, 0) is the top-left corner visible to the
    user, no matter where the scrollbar position is.

    This class (and PassageWidget) deal strictly in logical coordinates, but
    incoming events are in pixel coordinates. We convert these to logical
    coordinates as soon as possible.
    """

    def __init__(self, parent, app, id = wx.ID_ANY, state = None):
        wx.ScrolledWindow.__init__(self, parent, id)
        self.app = app
        self.parent = parent

        # inner state

        self.snapping = self.app.config.ReadBool('storyPanelSnap')
        self.widgets = []
        self.visibleWidgets = None
        self.includedPassages = set()
        self.draggingMarquee = False
        self.draggingWidgets = None
        self.notDraggingWidgets = None
        self.undoStack = []
        self.undoPointer = -1
        self.lastSearchRegexp = None
        self.lastSearchFlags = None
        self.lastScrollPos = -1
        self.trackinghover = None
        self.tooltiptimer = wx.PyTimer(self.tooltipShow)
        self.tooltipplace = ''
        self.tooltipobj = None
        self.textDragSource = None

        if (state):
            self.scale = state['scale']
            for widget in state['widgets']:
                self.widgets.append(PassageWidget(self, self.app, state = widget))
            if ('snapping' in state):
                self.snapping = state['snapping']
        else:
            self.scale = 1
            for title in ('Start', 'StoryTitle', 'StoryAuthor'):
                self.newWidget(title = title, text = self.parent.defaultTextForPassage(title), quietly = True)

        self.pushUndo(action = '')
        self.undoPointer -= 1

        # cursors

        self.dragCursor = wx.StockCursor(wx.CURSOR_SIZING)
        self.badDragCursor = wx.StockCursor(wx.CURSOR_NO_ENTRY)
        self.scrollCursor = wx.StockCursor(wx.CURSOR_SIZING)
        self.defaultCursor = wx.StockCursor(wx.CURSOR_ARROW)
        self.SetCursor(self.defaultCursor)

        # events

        self.SetDropTarget(StoryPanelDropTarget(self))
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: e)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)
        self.Bind(wx.EVT_LEFT_DOWN, self.handleClick)
        self.Bind(wx.EVT_LEFT_DCLICK, self.handleDoubleClick)
        self.Bind(wx.EVT_RIGHT_UP, self.handleRightClick)
        self.Bind(wx.EVT_MIDDLE_UP, self.handleMiddleClick)
        self.Bind(wx.EVT_ENTER_WINDOW, self.handleHoverStart)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.handleHoverStop)
        self.Bind(wx.EVT_MOTION, self.handleHover)

    def newWidget(self, title = None, text = '', tags = [], pos = None, quietly = False, logicals = False):
        """Adds a new widget to the container."""

        # defaults

        if not title:
            if tags and tags[0] in TiddlyWiki.INFO_TAGS:
                type = "Untitled " + tags[0].capitalize()
            else:
                type = "Untitled Passage"
            title = self.untitledName(type)
        if not pos: pos = StoryPanel.INSET
        if not logicals: pos = self.toLogical(pos)

        new = PassageWidget(self, self.app, title = title, text = text, tags = tags, pos = pos)
        self.widgets.append(new)
        self.snapWidget(new, quietly)
        self.resize()
        self.Refresh()
        if not quietly: self.parent.setDirty(True, action = 'New Passage')
        return new

    def snapWidget(self, widget, quickly = False):
        """
        Snaps a widget to our grid if self.snapping is set.
        Then, call findSpace()
        """
        if self.snapping:
            pos = list(widget.pos)

            for coord in range(2):
                distance = pos[coord] % StoryPanel.GRID_SPACING
                if (distance > StoryPanel.GRID_SPACING / 2):
                    pos[coord] += StoryPanel.GRID_SPACING - distance
                else:
                    pos[coord] -= distance
                pos[coord] += StoryPanel.INSET[coord]

            widget.pos = pos
            self.Refresh()
        if quickly:
            widget.findSpaceQuickly()
        else:
            widget.findSpace()

    def cleanup(self):
        """Snaps all widgets to the grid."""
        oldSnapping = self.snapping
        self.snapping = True
        self.eachWidget(self.snapWidget)
        self.snapping = oldSnapping
        self.parent.setDirty(True, action = 'Clean Up')
        self.Refresh()

    def toggleSnapping(self):
        """Toggles whether snapping is on."""
        self.snapping = self.snapping is not True
        self.app.config.WriteBool('storyPanelSnap', self.snapping)

    def copyWidgets(self):
        """Copies selected widgets into the clipboard."""
        data = []
        for widget in self.widgets:
            if widget.selected: data.append(widget.serialize())

        clipData = wx.CustomDataObject(wx.CustomDataFormat(StoryPanel.CLIPBOARD_FORMAT))
        clipData.SetData(pickle.dumps(data, 1))

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(clipData)
            wx.TheClipboard.Close()

    def cutWidgets(self):
        """Cuts selected widgets into the clipboard."""
        self.copyWidgets()
        self.removeWidgets()
        self.Refresh()

    def pasteWidgets(self, pos = (0,0)):
        """Pastes widgets from the clipboard."""
        clipFormat = wx.CustomDataFormat(StoryPanel.CLIPBOARD_FORMAT)
        clipData = wx.CustomDataObject(clipFormat)

        if wx.TheClipboard.Open():
            gotData = wx.TheClipboard.IsSupported(clipFormat) and wx.TheClipboard.GetData(clipData)
            wx.TheClipboard.Close()

            if gotData:
                data = pickle.loads(clipData.GetData())

                self.eachWidget(lambda w: w.setSelected(False, False))

                for widget in data:
                    newPassage = PassageWidget(self, self.app, state = widget, pos = pos, title = self.untitledName(widget['passage'].title))
                    newPassage.findSpace()
                    newPassage.setSelected(True, False)
                    self.widgets.append(newPassage)

                self.parent.setDirty(True, action = 'Paste')
                self.resize()
                self.Refresh()


    def removeWidget(self, widget, saveUndo = False):
        """
        Deletes a passed widget. You can ask this to save an undo state manually,
        but by default, it doesn't.
        """
        self.widgets.remove(widget)
        if widget in self.visibleWidgets: self.visibleWidgets.remove(widget)
        if self.tooltipplace == widget:
            self.tooltipplace = None
        if saveUndo: self.parent.setDirty(True, action = 'Delete')
        self.Refresh()

    def removeWidgets(self, event = None, saveUndo = False):
        """
        Deletes all selected widgets. You can ask this to save an undo state manually,
        but by default, it doesn't.
        """

        selected = []
        connected = []

        for widget in self.widgets:
            if widget.selected: selected.append(widget)

        for widget in self.widgets:
            if not widget.selected:
                for link in widget.linksAndDisplays():
                    if len(link) > 0:
                        for widget2 in selected:
                            if widget2.passage.title == link:
                                connected.append(widget)

        if len(connected):
            message = 'Are you sure you want to delete ' + \
                      (('"' + selected[0].passage.title + '"? Links to it') if len(selected) == 1 else
                      (str(len(selected)+1) + ' passages? Links to them')) + \
                       ' from ' + \
                      (('"' + connected[0].passage.title + '"') if len(connected) == 1 else
                      (str(len(connected)+1) + ' other passages')) + \
                      ' will become broken.'
            dialog = wx.MessageDialog(self.parent, message,
                                      'Delete Passage' + ('s' if len(selected) > 1 else ''), \
                                      wx.ICON_WARNING | wx.OK | wx.CANCEL )

            if dialog.ShowModal() != wx.ID_OK:
                return

        for widget in selected:
            self.widgets.remove(widget)
            if widget in self.visibleWidgets: self.visibleWidgets.remove(widget)
            if self.tooltipplace == widget:
                self.tooltipplace = None
        if len(selected):
            self.Refresh()
            if saveUndo: self.parent.setDirty(True, action = 'Delete')

    def findWidgetRegexp(self, regexp = None, flags = None):
        """
        Finds the next PassageWidget that matches the regexp passed.
        You may leave off the regexp, in which case it uses the last
        search performed. This begins its search from the current selection.
        If nothing is found, then an error alert is shown.
        """

        if regexp == None:
            regexp = self.lastSearchRegexp
            flags = self.lastSearchFlags

        self.lastSearchRegexp = regexp
        self.lastSearchFlags = flags

        # find the current selection
        # if there are multiple selections, we just use the first

        i = -1

        # look for selected PassageWidgets
        for num, widget in enumerate(self.widgets):
            if widget.selected:
                i = num
                break

        # if no widget is selected, start at first widget
        if i==len(self.widgets)-1:
            i=-1

        for widget in self.widgets[i+1:]:
            if widget.containsRegexp(regexp, flags):
                widget.setSelected(True)
                self.scrollToWidget(widget)
                return
            i += 1

        # fallthrough: text not found

        dialog = wx.MessageDialog(self, 'The text you entered was not found in your story.', \
                                  'Not Found', wx.ICON_INFORMATION | wx.OK)
        dialog.ShowModal()

    def replaceRegexpInSelectedWidget(self, findRegexp, replacementRegexp, flags):
        for widget in self.widgets:
            if widget.selected:
                widget.replaceRegexp(findRegexp, replacementRegexp, flags)
                widget.clearPaintCache()
                self.Refresh()
                self.parent.setDirty(True, action = 'Replace in Currently Selected Widget')

    def replaceRegexpInWidgets(self, findRegexp, replacementRegexp, flags):
        """
        Performs a string replace on all widgets in this StoryPanel.
        It shows an alert once done to tell the user how many replacements were
        made.
        """
        replacements = 0

        for widget in self.widgets:
            replacements += widget.replaceRegexp(findRegexp, replacementRegexp, flags)

        if replacements > 0:
            self.Refresh()
            self.parent.setDirty(True, action = 'Replace Across Entire Story')

        message = '%d replacement' % replacements
        if replacements != 1:
            message += 's were '
        else:
            message += ' was '
        message += 'made in your story.'

        dialog = wx.MessageDialog(self, message, 'Replace Complete', wx.ICON_INFORMATION | wx.OK)
        dialog.ShowModal()

    def scrollToWidget(self, widget):
        """
        Scrolls so that the widget passed is visible.
        """
        widgetRect = widget.getPixelRect()
        xUnit,yUnit = self.GetScrollPixelsPerUnit()
        sx = (widgetRect.x-20) / float(xUnit)
        sy = (widgetRect.y-20) / float(yUnit)
        self.Scroll(max(sx, 0), max(sy - 20, 0))

    def pushUndo(self, action):
        """
        Pushes the current state onto the undo stack. The name parameter describes
        the action that triggered this call, and is displayed in the Undo menu.
        """

        # delete anything above the undoPointer

        while self.undoPointer < len(self.undoStack) - 2: self.undoStack.pop()

        # add a new state onto the stack

        state = { 'action': action, 'widgets': [] }
        for widget in self.widgets: state['widgets'].append(widget.serialize())
        self.undoStack.append(state)
        self.undoPointer += 1
        
    def undo(self):
        """
        Restores the undo state at self.undoPointer to the current view, then
        decreases self.undoPointer by 1.
        """
        self.widgets = []
        self.visibleWidgets = None
        state = self.undoStack[self.undoPointer]
        for widget in state['widgets']:
            self.widgets.append(PassageWidget(self, self.app, state = widget))
        self.undoPointer -= 1
        self.Refresh()

    def redo(self):
        """
        Moves the undo pointer up 2, then calls undo() to restore state.
        """
        self.undoPointer += 2
        self.undo()

    def canUndo(self):
        """Returns whether an undo is available to the user."""
        return self.undoPointer > -1

    def undoAction(self):
        """Returns the name of the action that the user will be undoing."""
        return self.undoStack[self.undoPointer + 1]['action']

    def canRedo(self):
        """Returns whether a redo is available to the user."""
        return self.undoPointer < len(self.undoStack) - 2

    def redoAction(self):
        """Returns the name of the action that the user will be redoing."""
        return self.undoStack[self.undoPointer + 2]['action']

    def handleClick(self, event):
        """
        Passes off execution to either startMarquee or startDrag,
        depending on whether the user clicked a widget.
        """
        # start a drag if the user clicked a widget
        # or a marquee if they didn't

        for widget in self.widgets:
            if widget.getPixelRect().Contains(event.GetPosition()):
                if not widget.selected: widget.setSelected(True, not event.ShiftDown())
                self.startDrag(event, widget)
                return
        self.startMarquee(event)

    def handleDoubleClick(self, event):
        """Dispatches an openEditor() call to a widget the user clicked."""
        for widget in self.widgets:
            if widget.getPixelRect().Contains(event.GetPosition()): widget.openEditor()

    def handleRightClick(self, event):
        """Either opens our own contextual menu, or passes it off to a widget."""
        for widget in self.widgets:
            if widget.getPixelRect().Contains(event.GetPosition()):
                widget.openContextMenu(event)
                return
        self.PopupMenu(StoryPanelContext(self, event.GetPosition()), event.GetPosition())

    def handleMiddleClick(self, event):
        """Creates a new widget centered at the mouse position."""
        pos = event.GetPosition()
        offset = self.toPixels((PassageWidget.SIZE / 2, 0), scaleOnly = True)
        pos.x = pos.x - offset[0]
        pos.y = pos.y - offset[0]
        self.newWidget(pos = pos)

    def startMarquee(self, event):
        """Starts a marquee selection."""
        if not self.draggingMarquee:
            self.draggingMarquee = True
            self.dragOrigin = event.GetPosition()
            self.dragCurrent = event.GetPosition()
            self.dragRect = geometry.pointsToRect(self.dragOrigin, self.dragOrigin)

            # deselect everything

            map(lambda w: w.setSelected(False, False), self.widgets)

            # grab mouse focus

            self.Bind(wx.EVT_MOUSE_EVENTS, self.followMarquee)
            self.CaptureMouse()
            self.Refresh()

    def followMarquee(self, event):
        """
        Follows the mouse during a marquee selection.
        """
        if event.LeftIsDown():
            # scroll and adjust coordinates

            offset = self.scrollWithMouse(event)
            self.oldDirtyRect = self.dragRect.Inflate(2, 2)
            self.oldDirtyRect.x -= offset[0]
            self.oldDirtyRect.y -= offset[1]

            self.dragCurrent = event.GetPosition()
            self.dragOrigin.x -= offset[0]
            self.dragOrigin.y -= offset[1]
            self.dragCurrent.x -= offset[0]
            self.dragCurrent.y -= offset[1]

            # dragRect is what is drawn onscreen
            # it is in unscrolled coordinates

            self.dragRect = geometry.pointsToRect(self.dragOrigin, self.dragCurrent)

            # select all enclosed widgets

            logicalOrigin = self.toLogical(self.CalcUnscrolledPosition(self.dragRect.x, self.dragRect.y), scaleOnly = True)
            logicalSize = self.toLogical((self.dragRect.width, self.dragRect.height), scaleOnly = True)
            logicalRect = wx.Rect(logicalOrigin[0], logicalOrigin[1], logicalSize[0], logicalSize[1])

            for widget in self.widgets:
                widget.setSelected(widget.intersects(logicalRect), False)

            self.Refresh(True, self.oldDirtyRect.Union(self.dragRect))
        else:
            self.draggingMarquee = False

            # clear event handlers

            self.Bind(wx.EVT_MOUSE_EVENTS, None)
            self.ReleaseMouse()
            self.Refresh()

    def startDrag(self, event, clickedWidget):
        """
        Starts a widget drag. The initial event is caught by PassageWidget, but
        it passes control to us so that we can move all selected widgets at once.
        """
        if not self.draggingWidgets or not len(self.draggingWidgets):
            # cache the sets of dragged vs not-dragged widgets
            self.draggingWidgets = []
            self.notDraggingWidgets = []
            self.clickedWidget = clickedWidget
            self.actuallyDragged = False
            self.dragCurrent = event.GetPosition()
            self.oldDirtyRect = clickedWidget.getPixelRect()

            # have selected widgets remember their original position
            # in case they need to snap back to it after a bad drag

            for widget in self.widgets:
                if widget.selected:
                    self.draggingWidgets.append(widget)
                    widget.predragPos = widget.pos
                else:
                    self.notDraggingWidgets.append(widget)

            # grab mouse focus

            self.Bind(wx.EVT_MOUSE_EVENTS, self.followDrag)
            self.CaptureMouse()

    def followDrag(self, event):
        """Follows mouse motions during a widget drag."""
        if event.LeftIsDown():
            self.actuallyDragged = True
            pos = event.GetPosition()

            # find change in position
            deltaX = pos[0] - self.dragCurrent[0]
            deltaY = pos[1] - self.dragCurrent[1]

            deltaX = self.toLogical((deltaX, -1), scaleOnly = True)[0]
            deltaY = self.toLogical((deltaY, -1), scaleOnly = True)[0]

            # offset selected passages

            for widget in self.draggingWidgets: widget.offset(deltaX, deltaY)
            self.dragCurrent = pos

            # if there any overlaps, then warn the user with a bad drag cursor

            goodDrag = True

            for widget in self.draggingWidgets:
                if widget.intersectsAny(dragging = True):
                    goodDrag = False
                    break

            # in fast drawing, we dim passages
            # to indicate no connectors should be drawn for them
            # while dragging is occurring
            #
            # in slow drawing, we dim passages
            # to indicate you're not allowed to drag there

            for widget in self.draggingWidgets:
                widget.setDimmed(self.app.config.ReadBool('fastStoryPanel') or not goodDrag)

            if goodDrag: self.SetCursor(self.dragCursor)
            else: self.SetCursor(self.badDragCursor)

            # scroll in response to the mouse,
            # and shift passages accordingly

            widgetScroll = self.toLogical(self.scrollWithMouse(event), scaleOnly = True)
            for widget in self.draggingWidgets: widget.offset(widgetScroll[0], widgetScroll[1])

            # figure out our dirty rect

            dirtyRect = self.oldDirtyRect

            for widget in self.draggingWidgets:
                dirtyRect = dirtyRect.Union(widget.getDirtyPixelRect())
                for link in widget.linksAndDisplays():
                    widget2 = self.findWidget(link)
                    if widget2:
                        dirtyRect = dirtyRect.Union(widget2.getDirtyPixelRect())

            self.oldDirtyRect = dirtyRect
            self.Refresh(True, dirtyRect)
        else:

            if self.actuallyDragged:
                # is this a bad drag?

                goodDrag = True

                for widget in self.draggingWidgets:
                    if widget.intersectsAny(dragging = True):
                        goodDrag = False
                        break

                if goodDrag:
                    for widget in self.draggingWidgets:
                        self.snapWidget(widget)
                        widget.setDimmed(False)
                    self.parent.setDirty(True, action = 'Move')
                    self.resize()
                else:
                    for widget in self.draggingWidgets:
                        widget.pos = widget.predragPos
                        widget.setDimmed(False)

                self.Refresh()

            else:
                # change the selection
                self.clickedWidget.setSelected(True, not event.ShiftDown())

            # general cleanup
            self.draggingWidgets = None
            self.notDraggingWidgets = None
            self.Bind(wx.EVT_MOUSE_EVENTS, None)
            self.ReleaseMouse()
            self.SetCursor(self.defaultCursor)

    def scrollWithMouse(self, event):
        """
        If the user has moved their mouse outside the window
        bounds, this tries to scroll to keep up. This returns a tuple
        of pixels of the scrolling; if none has happened, it returns (0, 0).
        """
        pos = event.GetPosition()
        size = self.GetSize()
        scroll = [0, 0]
        changed = False

        if pos.x < 0:
            scroll[0] = -1
            changed = True
        else:
            if pos.x > size[0]:
                scroll[0] = 1
                changed = True

        if pos.y < 0:
            scroll[1] = -1
            changed = True
        else:
            if pos.y > size[1]:
                scroll[1] = 1
                changed = True

        pixScroll = [0, 0]

        if changed:
            # scroll the window

            oldPos = self.GetViewStart()
            self.Scroll(oldPos[0] + scroll[0], oldPos[1] + scroll[1])

            # return pixel change
            # check to make sure we actually were able to scroll the direction we asked

            newPos = self.GetViewStart()

            if oldPos[0] != newPos[0]:
                pixScroll[0] = scroll[0] * StoryPanel.SCROLL_SPEED
            if oldPos[1] != newPos[1]:
                pixScroll[1] = scroll[1] * StoryPanel.SCROLL_SPEED

        return pixScroll

    def untitledName(self, base = "Untitled Passage"):
        """Returns a string for an untitled PassageWidget."""
        number = 1

        if not "Untitled " in base:
            if not self.findWidget(base):
                return base

        for widget in self.widgets:
            match = re.match(re.escape(base) + ' (\d+)', widget.passage.title)
            if match: number = int(match.group(1)) + 1

        return base + ' ' + str(number)

    def eachWidget(self, function):
        """Runs a function on every passage in the panel."""
        for widget in self.widgets:
            function(widget)

    def sortedWidgets(self):
        """Returns a sorted list of widgets, left to right, top to bottom."""
        return sorted(self.widgets, PassageWidget.sort)

    def taggedWidgets(self, tag):
        """Returns widgets that have the given tag"""
        return (a for a in self.widgets if tag in a.passage.tags)

    def selectedWidget(self):
        """Returns any one selected widget."""
        for widget in self.widgets:
            if widget.selected: return widget
        return None

    def eachSelectedWidget(self, function):
        """Runs a function on every selected passage in the panel."""
        for widget in self.widgets:
            if widget.selected: function(widget)

    def hasSelection(self):
        """Returns whether any passages are selected."""
        for widget in self.widgets:
            if widget.selected: return True
        return False

    def hasMultipleSelection(self):
        """Returns whether multiple passages are selected."""
        selected = 0
        for widget in self.widgets:
            if widget.selected:
                selected += 1
                if selected > 1: return True
        return False

    def findWidget(self, title):
        """Returns a PassageWidget with the title passed. If none exists, it returns None."""
        for widget in self.widgets:
            if widget.passage.title == title: return widget
        return None

    def passageExists(self, title, includeIncluded = True):
        """
        Returns whether a given passage exists in the story.
        
        If includeIncluded then will also check external passages referenced via StoryIncludes
        """
        return self.findWidget(title) != None or (includeIncluded and self.includedPassageExists(title))

    def clearIncludedPassages(self):
        """Clear the includedPassages set"""
        self.includedPassages.clear()

    def addIncludedPassage(self, title):
        """Add a title to the set of external passages"""
        self.includedPassages.add(title)

    def includedPassageExists(self, title):
        """Add a title to the set of external passages"""
        return (title in self.includedPassages)
    
    def refreshIncludedPassageList(self):
        for widget in self.widgets:
            if widget.passage.title == 'StoryIncludes':
                self.parent.readIncludes(widget.passage.text.splitlines(), lambda a: self.addIncludedPassage(a.title))

    def toPixels(self, logicals, scaleOnly = False):
        """
        Converts a tuple of logical coordinates to pixel coordinates. If you need to do just
        a straight conversion from logicals to pixels without worrying about where the scrollbar
        is, then call with scaleOnly set to True.
        """
        converted = (logicals[0] * self.scale, logicals[1] * self.scale)
        if not scaleOnly: converted = self.CalcScrolledPosition(converted)
        return converted

    def toLogical(self, pixels, scaleOnly = False):
        """
        Converts a tuple of pixel coordinates to logical coordinates. If you need to do just
        a straight conversion without worrying about where the scrollbar is, then call with
        scaleOnly set to True.
        """
        # order of operations here is important, though I don't totally understand why

        if scaleOnly:
            converted = pixels
        else:
            converted = self.CalcUnscrolledPosition(pixels)

        converted = (converted[0] / self.scale, converted[1] / self.scale)
        return converted

    def getSize(self):
        """
        Returns a tuple (width, height) of the smallest rect needed to
        contain all children widgets.
        """
        width, height = 0, 0

        for i in self.widgets:
            rightSide = i.pos[0] + i.getSize()[0]
            bottomSide = i.pos[1] + i.getSize()[1]
            width = max(width, rightSide)
            height = max(height, bottomSide)
        return (width, height)

    def zoom(self, scale):
        """
        Sets zoom to a certain level. Pass a number to set the zoom
        exactly, pass 'in' or 'out' to zoom relatively, and 'fit'
        to set the zoom so that all children are visible.
        """
        oldScale = self.scale

        if (isinstance(scale, float)):
            self.scale = scale
        else:
            if (scale == 'in'):
                self.scale += 0.2
            if (scale == 'out'):
                self.scale -= 0.2
            if (scale == 'fit'):
                self.zoom(1.0)
                neededSize = self.toPixels(self.getSize(), scaleOnly = True)
                actualSize = self.GetSize()
                widthRatio = actualSize.width / neededSize[0]
                heightRatio = actualSize.height / neededSize[1]
                self.scale = min(widthRatio, heightRatio)
                self.Scroll(0, 0)

        self.scale = max(self.scale, 0.2)
        scaleDelta = self.scale - oldScale

        # figure out what our scroll bar positions should be moved to
        # to keep in scale

        origin = list(self.GetViewStart())
        origin[0] += scaleDelta * origin[0]
        origin[1] += scaleDelta * origin[1]

        self.resize()
        self.Refresh()
        self.Scroll(origin[0], origin[1])
        self.parent.updateUI()

    def paint(self, event):
        """Paints marquee selection, widget connectors, and widgets onscreen."""
        # do NOT call self.DoPrepareDC() no matter what the docs may say
        # we already take into account our scroll origin in our
        # toPixels() method

        # in fast drawing, we ask for a standard paint context
        # in slow drawing, we ask for a anti-aliased one
        #
        # OS X already double buffers drawing for us; if we try to do it
        # ourselves, performance is horrendous

        if (sys.platform == 'darwin'):
            gc = wx.PaintDC(self)
        else:
            gc = wx.BufferedPaintDC(self)

        updateRect = self.GetUpdateRegion().GetBox()
        
        # Determine visible passages
        scrollPos = (self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL))
        if self.visibleWidgets == None or scrollPos != self.lastScrollPos:
            self.lastScrollPos = scrollPos
            updateRect = self.GetClientRect()
            self.visibleWidgets = [widget for widget in self.widgets
                                   # It's visible if it's in the client rect, or is being moved.
                                   if (widget.dimmed
                                       or updateRect.Intersects(widget.getPixelRect())
                                       # It's also visible if an arrow FROM it intersects with the Client Rect
                                       or [w2 for w2 in widget.getConnectedWidgets()
                                           if geometry.lineRectIntersection(w2.getConnectorLine(widget), updateRect)])]
        
        # background

        gc.SetBrush(wx.Brush(StoryPanel.FLAT_BG_COLOR if self.app.config.ReadBool('flatDesign') else StoryPanel.BACKGROUND_COLOR ))

        gc.DrawRectangle(updateRect.x - 1, updateRect.y - 1, updateRect.width + 2, updateRect.height + 2)

        # connectors

        arrowheads = (self.scale > StoryPanel.ARROWHEAD_THRESHOLD)

        for widget in self.visibleWidgets:
            if not widget.dimmed:
                widget.paintConnectors(gc, arrowheads, updateRect)
        
        for widget in self.visibleWidgets:
            # Could be "visible" only insofar as its arrow is visible
            if updateRect.Intersects(widget.getPixelRect()):
                widget.paint(gc)

        # marquee selection
        # with slow drawing, use alpha blending for interior

        if self.draggingMarquee:
            if self.app.config.ReadBool('fastStoryPanel'):
                gc.SetPen(wx.Pen('#ffffff', 1, wx.DOT))
                gc.SetBrush(wx.Brush(wx.WHITE, wx.TRANSPARENT))
            else:
                gc = wx.GraphicsContext.Create(gc)
                marqueeColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
                gc.SetPen(wx.Pen(marqueeColor))
                r, g, b = marqueeColor.Get(False)
                marqueeColor = wx.Colour(r, g, b, StoryPanel.MARQUEE_ALPHA)
                gc.SetBrush(wx.Brush(marqueeColor))

            gc.DrawRectangle(self.dragRect.x, self.dragRect.y, self.dragRect.width, self.dragRect.height)

    def resize(self, event = None):
        """
        Sets scrollbar settings based on panel size and widgets inside.
        This is designed to always give the user more room than they actually need
        to see everything already created, so that they can scroll down or over
        to add more things.
        """
        neededSize = self.toPixels(self.getSize(), scaleOnly = True)
        visibleSize = self.GetClientSize()

        maxWidth = max(neededSize[0], visibleSize[0]) + visibleSize[0]
        maxHeight = max(neededSize[1], visibleSize[1]) + visibleSize[1]

        self.SetVirtualSize((maxWidth, maxHeight))
        self.SetScrollRate(StoryPanel.SCROLL_SPEED, StoryPanel.SCROLL_SPEED)
        self.visibleWidgets = None

    def serialize(self):
        """Returns a dictionary of state suitable for pickling."""
        state = { 'scale': self.scale, 'widgets': [], 'snapping': self.snapping }

        for widget in self.widgets:
            state['widgets'].append(widget.serialize())

        return state

    def serialize_noprivate(self):
        """Returns a dictionary of state suitable for pickling without passage marked with a Twine.private tag."""
        state = { 'scale': self.scale, 'widgets': [], 'snapping': self.snapping }

        for widget in self.widgets:
            if not any('Twine.private' in t for t in widget.passage.tags):
                state['widgets'].append(widget.serialize())

        return state

    def handleHoverStart(self, event):
        """Turns on hover tracking when mouse enters the frame."""
        self.trackinghover = True

    def handleHoverStop(self, event):
        """Turns off hover tracking when mouse leaves the frame."""
        self.trackinghover = False

    def tooltipShow(self):
        """ Show the tooltip, showing a text sample for text passages,
        and some image size info for image passages."""
        if self.tooltipplace != None and self.trackinghover and not self.draggingWidgets:
            m = wx.GetMousePosition()
            p = self.tooltipplace.passage
            length = len(p.text);
            if p.isImage():
                mimeType = "unknown"
                mimeTypeRE = re.search(r"data:image/([^;]*);",p.text)
                if mimeTypeRE:
                    mimeType = mimeTypeRE.group(1)
                # Including the data URI prefix in the byte count, just because.
                text = "Image type: " + mimeType + "\nSize: "+ str(len(p.text)/1024)+" KB"
            else:
                text = "Title: " + p.title + "\n" + ("Tags: " + ", ".join(p.tags) + '\n\n' if p.tags else "")
                text += p.text[:840]
                if length >= 840:
                    text += "..."
            # Don't show a tooltip for a 0-length passage
            if length > 0:
                self.tooltipobj = wx.TipWindow(self, text, min(240, max(160,length/2)), wx.Rect(m[0],m[1],1,1))

    def handleHover(self, event):
        if self.trackinghover and not self.draggingWidgets and not self.draggingMarquee:
            for widget in self.widgets:
                if widget.getPixelRect().Contains(event.GetPosition()):
                    if widget != self.tooltipplace:
                        # Stop current timer
                        if self.tooltiptimer.IsRunning():
                            self.tooltiptimer.Stop()
                        self.tooltiptimer.Start(800, wx.TIMER_ONE_SHOT)
                        self.tooltipplace = widget
                        if self.tooltipobj:
                            if isinstance(self.tooltipobj, wx.TipWindow):
                                try:
                                    self.tooltipobj.Close()
                                except:
                                    pass
                            self.tooltipobj = None
                    return

        self.tooltiptimer.Stop()
        self.tooltipplace = None
        if self.tooltipobj:
            if isinstance(self.tooltipobj, wx.TipWindow):
                try:
                    self.tooltipobj.Close()
                except:
                    pass
            self.tooltipobj = None

    def getHeader(self):
        """Returns the current selected target header for this Story Panel."""
        return self.parent.getHeader()


    INSET = (10, 10)
    ARROWHEAD_THRESHOLD = 0.5   # won't be drawn below this zoom level
    FIRST_CSS = """/* Your story will use the CSS in this passage to style the page.
Give this passage more tags, and it will only affect passages with those tags.
Example selectors: */

body {
\t/* This affects the entire page */
\t
\t
}
.passage {
\t/* This only affects passages */
\t
\t
}
.passage a {
\t/* This affects passage links */
\t
\t
}
.passage a:hover {
\t/* This affects links while the cursor is over them */
\t
\t
}"""
    BACKGROUND_COLOR = '#555753'
    FLAT_BG_COLOR = '#c6c6c6'
    MARQUEE_ALPHA = 32 # out of 256
    SCROLL_SPEED = 25
    EXTRA_SPACE = 200
    GRID_SPACING = 140
    CLIPBOARD_FORMAT = 'TwinePassages'
    UNDO_LIMIT = 10

# context menu

class StoryPanelContext(wx.Menu):
    def __init__(self, parent, pos):
        wx.Menu.__init__(self)
        self.parent = parent
        self.pos = pos

        if self.parent.parent.menus.IsEnabled(wx.ID_PASTE):
            pastePassage = wx.MenuItem(self, wx.NewId(), 'Paste Passage Here')
            self.AppendItem(pastePassage)
            self.Bind(wx.EVT_MENU, lambda e: self.parent.pasteWidgets(self.getPos()), id = pastePassage.GetId())
            
        newPassage = wx.MenuItem(self, wx.NewId(), 'New Passage Here')
        self.AppendItem(newPassage)
        self.Bind(wx.EVT_MENU, self.newWidget, id = newPassage.GetId())

        self.AppendSeparator()

        newPassage = wx.MenuItem(self, wx.NewId(), 'New Stylesheet Here')
        self.AppendItem(newPassage)
        self.Bind(wx.EVT_MENU, lambda e: self.newWidget(e, text = StoryPanel.FIRST_CSS, tags = ['stylesheet']), id = newPassage.GetId())

        newPassage = wx.MenuItem(self, wx.NewId(), 'New Script Here')
        self.AppendItem(newPassage)
        self.Bind(wx.EVT_MENU, lambda e: self.newWidget(e, tags = ['script']), id = newPassage.GetId())

        newPassage = wx.MenuItem(self, wx.NewId(), 'New Annotation Here')
        self.AppendItem(newPassage)
        self.Bind(wx.EVT_MENU, lambda e: self.newWidget(e, tags = ['annotation']), id = newPassage.GetId())

    def getPos(self):
        pos = self.pos
        offset = self.parent.toPixels((PassageWidget.SIZE / 2, 0), scaleOnly = True)
        pos.x = pos.x - offset[0]
        pos.y = pos.y - offset[0]
        return pos
    
    def newWidget(self, event, text = '', tags = []):
        self.parent.newWidget(pos = self.getPos(), text = text, tags = tags)

# drag and drop listener

class StoryPanelDropTarget(wx.PyDropTarget):
    def __init__(self, panel):
        wx.PyDropTarget.__init__(self)
        self.panel = panel
        self.data = wx.DataObjectComposite()
        self.filedrop = wx.FileDataObject()
        self.textdrop = wx.TextDataObject()
        self.data.Add(self.filedrop,False)
        self.data.Add(self.textdrop,False)
        self.SetDataObject(self.data)

    def OnData(self, x, y, d):
        if self.GetData():
            type = self.data.GetReceivedFormat().GetType()
            if type in [wx.DF_UNICODETEXT, wx.DF_TEXT]:
                # add the new widget

                # Check for invalid characters, or non-unique titles
                text = self.textdrop.GetText()
                if "|" in text:
                    return None
                else:
                    if self.panel.passageExists(text):
                        return None

                self.panel.newWidget(title = text, pos = (x, y))

                # update the source text with a link
                # this is set by PassageFrame.prepDrag()
                # (note: if text is dragged from outside Twine into it,
                # then it won't be set for the destination.)
                if self.panel.textDragSource:
                    self.panel.textDragSource.linkSelection()
                    # Cancel the deletion of the source text by returning None
                    return None

            elif type == wx.DF_FILENAME:

                imageRegex = r'\.(?:jpe?g|png|gif|webp|svg)$'
                files = self.filedrop.GetFilenames();

                # Check if dropped files contains multiple images,
                # so the correct dialogs are displayed

                imagesImported = 0
                multipleImages = len([re.search(imageRegex, file) for file in files]) > 1

                for file in files:

                    fname = file.lower()
                    # Open a file if it's .tws

                    if fname.endswith(".tws"):
                        self.panel.app.open(file)

                    # Import a file if it's HTML, .tw or .twee

                    elif fname.endswith(".twee") or fname.endswith(".tw"):
                        self.panel.parent.importSource(file)
                    elif fname.endswith(".html") or fname.endswith(".htm"):
                        self.panel.parent.importHtml(file)
                    elif re.search(imageRegex, fname):
                        text, title = self.panel.parent.openFileAsBase64(fname)
                        imagesImported += 1 if self.panel.parent.finishImportImage(text, title, showdialog = not multipleImages) else 0

                if imagesImported > 1:
                    dialog = wx.MessageDialog(self.panel.parent, 'Multiple image files imported successfully.', 'Images added', \
                          wx.ICON_INFORMATION | wx.OK)
                    dialog.ShowModal()

        return d


########NEW FILE########
__FILENAME__ = storysearchframes
import re, wx
from searchpanels import FindPanel, ReplacePanel

class StoryFindFrame(wx.Frame):
    """
    This allows the user to search a StoryPanel for a string of text.
    This is just a front-end to method calls on StoryPanel.
    """

    def __init__(self, storyPanel, app, parent = None):
        self.storyPanel = storyPanel
        self.app = app
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = 'Find in Story', \
                          style = wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.CAPTION | wx.SYSTEM_MENU)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        findPanel = FindPanel(parent = self, onFind = self.onFind, onClose = self.onClose)
        findPanel.focus()
        sizer.Add(findPanel)
        sizer.Fit(self)
        self.SetIcon(self.app.icon)
        self.Show()

    def onFind(self, regexp, flags):
        self.storyPanel.findWidgetRegexp(regexp, flags)

    def onClose(self):
        self.Close()

class StoryReplaceFrame(wx.Frame):
    """
    This allows the user to replace text across an entire StoryPanel.
    This is just a front-end to method calls on StoryPanel.
    """

    def __init__(self, storyPanel, app, parent = None):
        self.storyPanel = storyPanel
        self.app = app
        wx.Frame.__init__(self, parent, wx.ID_ANY, title = 'Replace Across Entire Story', \
                          style = wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.CAPTION | wx.SYSTEM_MENU)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        replacePanel = ReplacePanel(self, allowIncremental = True, \
                                    onFind=self.onFind, onReplace=self.onReplace, \
                                    onReplaceAll = self.onReplaceAll, onClose = self.onClose)
        sizer.Add(replacePanel)
        replacePanel.focus()

        sizer.Fit(self)
        self.SetIcon(self.app.icon)
        self.Show()

    def onFind(self, regexp, flags):
        self.storyPanel.findWidgetRegexp(regexp, flags)

    def onReplace(self, findRegexp, flags, replaceRegexp):
        self.storyPanel.replaceRegexpInSelectedWidget(findRegexp, replaceRegexp, flags)

    def onReplaceAll(self, findRegexp, flags, replaceRegexp):
        self.storyPanel.replaceRegexpInWidgets(findRegexp, replaceRegexp, flags)

    def onClose(self):
        self.Close()

########NEW FILE########
__FILENAME__ = jonah
import header

class Header (header.Header):

    def __init__(self, id, path, builtinPath):
        super(Header, self).__init__(id, path, builtinPath)

    def filesToEmbed(self):
        """Returns an Ordered Dictionary of file names to embed into the output."""
        list = super(Header, self).filesToEmbed()
        return list

########NEW FILE########
__FILENAME__ = sugarcane
import header

class Header (header.Header):

    def __init__(self, id, path, builtinPath):
        super(Header, self).__init__(id, path, builtinPath)

    def filesToEmbed(self):
        """Returns an Ordered Dictionary of file names to embed into the output."""
        list = super(Header, self).filesToEmbed()
        return list

########NEW FILE########
__FILENAME__ = tiddlywiki
"""
A Python implementation of the Twee compiler.

This code was written by Chris Klimas <klimas@gmail.com>
It is licensed under the GNU General Public License v2
http://creativecommons.org/licenses/GPL/2.0/

This file defines two classes: Tiddler and TiddlyWiki. These match what
you'd normally see in a TiddlyWiki; the goal here is to provide classes
that translate between Twee and TiddlyWiki output seamlessly.
"""

import re, datetime, time, locale, os, sys, tempfile, codecs
import tweeregex
from tweelexer import TweeLexer

class TiddlyWiki:
    """An entire TiddlyWiki."""

    def __init__(self, author = 'twee'):
        self.author = author
        self.tiddlers = {}
        self.storysettings = {}

    def hasTiddler(self, name):
        return name in self.tiddlers

    def toTwee(self, order = None):
        """Returns Twee source code for this TiddlyWiki.
        The 'order' argument is a sequence of passage titles specifying the order
        in which passages should appear in the output string; by default passages
        are returned in arbitrary order.
        """
        tiddlers = self.tiddlers
        if order is None:
            order = tiddlers.keys()
        return u''.join(tiddlers[i].toTwee() for i in order)

    def read(self, filename):
        try:
            source = codecs.open(filename, 'rU', 'utf_8_sig', 'strict')
            w = source.read()
        except UnicodeDecodeError:
            try:
                source = codecs.open(filename, 'rU', 'utf16', 'strict')
                w = source.read()
            except:
                source = open(filename, 'rU')
                w = source.read()
        source.close()
        return w

    def toHtml(self, app, header = None, order = None, startAt = '', defaultName = '', metadata = {}):
        """Returns HTML code for this TiddlyWiki."""
        if not order: order = self.tiddlers.keys()
        output = u''

        if not header:
            app.displayError("building: no story format was specified.\n"
                            + "Please select another format from the Story Format submenu.\n\n")
            return

        try:
            headerPath = header.path + 'header.html'
            # TODO: Move file reading to Header class.
            output = self.read(headerPath)

        except IOError:
            app.displayError("building: the story format '" + header.label + "' isn't available.\n"
                + "Please select another format from the Story Format submenu.\n\n")
            return


        def insertEngine(app, output, filename, label, extra = ''):
            if output.count(label) > 0:
                try:
                    enginecode = self.read(filename)
                    return output.replace(label,enginecode + extra)

                except IOError:
                    app.displayError("building: the file '" + filename + "' used by the story format '" + header.label + "' wasn't found.\n\n")
                    return None
            else:
                return output

        # Insert version number
        output = output.replace('"VERSION"', "Made in " + app.NAME + " " + app.VERSION)

        # Insert timestamp
        # Due to Windows limitations, the timezone offset must be computed manually.
        tz_offset = (lambda t: '%s%02d%02d' % (('+' if t <= 0 else '-',) + divmod(abs(t) / 60, 60)))(time.timezone)
        # Obtain the encoding expected to be used by strftime in this locale
        strftime_encoding = locale.getlocale(locale.LC_TIME)[1] or locale.getpreferredencoding()
        # Write the timestamp
        output = output.replace('"TIME"', "Built on "+time.strftime("%d %b %Y at %H:%M:%S, "+tz_offset).decode(strftime_encoding))

        # Insert the test play "start at passage" value
        if (startAt):
            output = output.replace('"START_AT"', '"' + startAt.replace('\\', r'\\').replace('"', '\"') + '"')
        else:
            output = output.replace('"START_AT"', '""')

        # Embed any engine related files required by the header.
        
        embedded = header.filesToEmbed()
        for key in embedded.keys():
            output = insertEngine(app, output, embedded[key], key)
            if not output: return

        # Insert the Backup Story Title
        
        if defaultName:
            name = defaultName.replace('"',r'\"')
            # Just gonna assume the <title> has no attributes
            output = re.sub(r'<title>.*?<\/title>', '<title>'+name+'</title>', output, count=1, flags=re.I|re.M) \
                .replace('"Untitled Story"', '"'+name+'"')
                
        # Insert the metadata
        
        metatags = ''
        for name, content in metadata.iteritems():
            if content:
                metatags += '<meta name="' + name.replace('"','&quot;') + '" content="' + content.replace('"','&quot;') + '">\n'
        
        if metatags:
            # Just gonna assume <head> contains no attributes containing > symbols.
            output = re.sub(r'<head[^>]*>\s*\n?', lambda a: a.group(0) + metatags, output, flags=re.I, count=1)

        # Check if the scripts are personally requesting jQuery or Modernizr
        jquery = 'jquery' in self.storysettings and self.storysettings['jquery'] != "off"
        modernizr = 'modernizr' in self.storysettings and self.storysettings['modernizr'] != "off"
        blankCSS = 'blankcss' in self.storysettings and self.storysettings['blankcss'] != "off"
        
        for i in filter(lambda a: (a.isScript() or a.isStylesheet()), self.tiddlers.itervalues()):
            if not jquery and i.isScript() and re.search(r'requires? jquery', i.text, re.I):
                jquery = True
            if not modernizr and re.search(r'requires? modernizr', i.text, re.I):
                modernizr = True
            if not blankCSS and i.isStylesheet() and re.search(r'blank stylesheet', i.text, re.I):
                blankCSS = True
            if jquery and modernizr and noDefaultCSS:
                break
        
        # Insert jQuery
        if jquery:
            output = insertEngine(app, output, app.builtinTargetsPath + 'jquery.js', '"JQUERY"')
            if not output: return
        else:
            output = output.replace('"JQUERY"','')

        # Insert Modernizr
        if modernizr:
            output = insertEngine(app, output, app.builtinTargetsPath + 'modernizr.js', '"MODERNIZR"')
            if not output: return
        else:
            output = output.replace('"MODERNIZR"','')
            
        # Remove default CSS
        if blankCSS:
            # Just gonna assume the html id is quoted correctly if at all.
            output = re.sub(r'<style\s+id=["\']?defaultCSS["\']?\s*>(?:[^<]|<(?!\/style>))*<\/style>', '', output, flags=re.I|re.M, count=1)

        argEncoders = []
        bodyEncoders = []

        rot13 = 'obfuscate' in self.storysettings and \
            self.storysettings['obfuscate'] != 'off';
        # In case it was set to "swap" (legacy 1.4.1 file),
        # alter and remove old properties.
        if rot13:
            self.storysettings['obfuscate'] = "rot13"
            if 'obfuscatekey' in self.storysettings:
                del self.storysettings['obfuscatekey']

        # Finally add the passage data
        storyfragments = []
        for i in order:
            tiddler = self.tiddlers[i]
            # Strip out comments from storysettings and reflect any alterations made
            if tiddler.title == 'StorySettings':
                tiddler.text = ''.join([(str(k)+":"+str(v)+"\n") for k,v in self.storysettings.iteritems()])
            if self.NOINCLUDE_TAGS.isdisjoint(tiddler.tags):
                if not rot13 or tiddler.title == 'StorySettings' or tiddler.isImage() :
                    storyfragments.append(tiddler.toHtml(self.author, False))
                else:
                    storyfragments.append(tiddler.toHtml(self.author, rot13))
        storycode = u''.join(storyfragments)

        if output.count('"STORY_SIZE"') > 0:
            output = output.replace('"STORY_SIZE"', '"' + str(len(storyfragments)) + '"')
        
        if output.count('"STORY"') > 0:
            output = output.replace('"STORY"', storycode)
        else:
            output += storycode
            if (header):
                footername = header.path + 'footer.html'
                if os.path.exists(footername):
                    output += self.read(footername)
                else:
                    output += '</div></body></html>'

        return output

    def toRtf(self, order = None):
        """Returns RTF source code for this TiddlyWiki."""
        if not order: order = self.tiddlers.keys()

        def rtf_encode_char(unicodechar):
            if ord(unicodechar) < 128:
                return str(unicodechar)
            return r'\u' + str(ord(unicodechar)) + r'?'

        def rtf_encode(unicodestring):
            return r''.join(rtf_encode_char(c) for c in unicodestring)

        # preamble

        output = r'{\rtf1\ansi\ansicpg1251' + '\n'
        output += r'{\fonttbl\f0\fswiss\fcharset0 Arial;\f1\fmodern\fcharset0 Courier;}' + '\n'
        output += r'{\colortbl;\red128\green128\blue128;\red51\green51\blue204;}' + '\n'
        output += r'\margl1440\margr1440\vieww9000\viewh8400\viewkind0' + '\n'
        output += r'\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx792' + '\n'
        output += r'\tx8640\ql\qnatural\pardirnatural\pgnx720\pgny720' + '\n'

        # content

        for i in order:
            text = rtf_encode(self.tiddlers[i].text)
            text = re.sub(r'\n', '\\\n', text) # newlines
            text = re.sub(tweeregex.LINK_REGEX, r'\\b\cf2 \ul \1\ulnone \cf0 \\b0 ', text) # links
            text = re.sub(r"''(.*?)''", r'\\b \1\\b0 ', text) # bold
            text = re.sub(r'\/\/(.*?)\/\/', r'\i \1\i0 ', text) # italics
            text = re.sub(r"\^\^(.*?)\^\^", r'\\super \1\\nosupersub ', text) # sup
            text = re.sub(r"~~(.*?)~~", r'\\sub \1\\nosupersub ', text) # sub
            text = re.sub(r"==(.*?)==", r'\\strike \1\\strike0 ', text) # strike
            text = re.sub(r'(\<\<.*?\>\>)', r'\\f1\cf1 \1\cf0\\f0 ', text) # macros
            text = re.sub(tweeregex.HTML_REGEX, r'\\f1\cf1 \g<0>\cf0\\f0 ', text) # macros
            text = re.sub(tweeregex.MONO_REGEX, r'\\f1 \1\\f0 ', text) # monospace
            text = re.sub(tweeregex.COMMENT_REGEX, '', text) # comments

            output += r'\fs24\b1 ' + rtf_encode(self.tiddlers[i].title) + r'\b0\fs20 ' + '\\\n'
            output += text + '\\\n\\\n'

        output += '}'

        return output

    def addTwee(self, source):
        """Adds Twee source code to this TiddlyWiki.
        Returns the tiddler titles in the order they occurred in the Twee source.
        """
        source = source.replace("\r\n", "\n")
        source = '\n' + source
        tiddlers = source.split('\n::')[1:]

        order = []
        for i in tiddlers:
            tiddler = Tiddler('::' + i)
            self.addTiddler(tiddler)
            order.append(tiddler.title)
        return order

    def addHtml(self, source):
        """Adds HTML source code to this TiddlyWiki.
        Returns the tiddler titles in the order they occurred in the HTML.
        """
        order = []
        divs = re.search(r'<div\s+id=(["\']?)store(?:A|-a)rea\1(?:\s+data-size=(["\']?)\d+\2)?(?:\s+hidden)?\s*>(.*)</div>', source,
                        re.DOTALL)
        if divs:
            divs = divs.group(3);
            # HTML may be obfuscated.
            obfuscatekey = ''
            storysettings_re = r'[^>]*\stiddler=["\']?StorySettings["\']?[^>]*>.*?</div>'
            storysettings = re.search(r'<div'+storysettings_re, divs, re.DOTALL)
            if storysettings:
                ssTiddler = self.addTiddler(Tiddler(storysettings.group(0), 'html'))
                obfuscate = re.search(r'obfuscate\s*:\s*((?:[^\no]|o(?!ff))*)\s*(?:\n|$)', ssTiddler.text, re.I)
                if obfuscate:
                    if "swap" in obfuscate.group(1):
                        # Find the legacy 'obfuscatekey' option from 1.4.0.
                        match = re.search(r'obfuscatekey\s*:\s*(\w*)\s*(?:\n|$)', ssTiddler.text, re.I)
                        if match:
                            obfuscatekey = match.group(1)
                            nss = u''
                            for nsc in obfuscatekey:
                                if nss.find(nsc) == -1 and not nsc in ':\\\"n0':
                                    nss = nss + nsc
                            obfuscatekey = nss
                    else:
                        obfuscatekey = "anbocpdqerfsgthuivjwkxlymz"
                divs = divs[:storysettings.start(0)] + divs[storysettings.end(0):]

            for div in divs.split('<div'):
                div.strip()
                if div:
                    tiddler = Tiddler('<div' + div, 'html', obfuscatekey)
                    self.addTiddler(tiddler)
                    order.append(tiddler.title)
        return order

    def addHtmlFromFilename(self, filename):
        return self.addHtml(self.read(filename))

    def addTweeFromFilename(self, filename):
        return self.addTwee(self.read(filename))

    def addTiddler(self, tiddler):
        """Adds a Tiddler object to this TiddlyWiki."""

        if tiddler.title in self.tiddlers:
            if (tiddler == self.tiddlers[tiddler.title]) and \
                 (tiddler.modified > self.tiddlers[tiddler.title].modified):
                self.tiddlers[tiddler.title] = tiddler
        else:
            self.tiddlers[tiddler.title] = tiddler

        return tiddler

    FORMATTED_INFO_PASSAGES = frozenset([
            'StoryMenu', 'StoryTitle', 'StoryAuthor', 'StorySubtitle', 'StoryInit'])
    UNFORMATTED_INFO_PASSAGES = frozenset(['StoryIncludes', 'StorySettings'])
    INFO_PASSAGES = FORMATTED_INFO_PASSAGES | UNFORMATTED_INFO_PASSAGES
    SPECIAL_TAGS = frozenset(['Twine.image'])
    NOINCLUDE_TAGS = frozenset(['Twine.private', 'Twine.system'])
    INFO_TAGS = frozenset(['script', 'stylesheet', 'annotation']) | SPECIAL_TAGS | NOINCLUDE_TAGS


class Tiddler:
    """A single tiddler in a TiddlyWiki."""

    def __init__(self, source, type = 'twee', obfuscatekey = ""):
        # cache of passage names linked from this one
        self.links = []
        self.displays = []
        self.images = []
        self.macros = []
        self.modifier = None

        """Pass source code, and optionally 'twee' or 'html'"""
        if type == 'twee':
            self.initTwee(source)
        else:
            self.initHtml(source, obfuscatekey)

    def __getstate__(self):
        """Need to retain pickle format backwards-compatibility with Twine 1.3.5 """
        return {
            'created': self.created,
            'modified': self.modified,
            'title': self.title,
            'tags': self.tags,
            'text': self.text,
        }

    def __repr__(self):
        return "<Tiddler '" + self.title + "'>"

    def __cmp__(self, other):
        """Compares a Tiddler to another."""
        return hasattr(other, 'text') and self.text == other.text

    def initTwee(self, source):
        """Initializes a Tiddler from Twee source code."""

        # we were just born

        self.created = self.modified = time.localtime()
        # used only during builds
        self.pos = [0,0]

        # figure out our title

        lines = source.strip().split('\n')

        meta_bits = lines[0].split('[')
        self.title = meta_bits[0].strip(' :')

        # find tags

        self.tags = []

        if len(meta_bits) > 1:
            tag_bits = meta_bits[1].split(' ')

            for tag in tag_bits:
                self.tags.append(tag.strip('[]'))

        # and then the body text

        self.text = u''

        for line in lines[1:]:
            self.text += line + "\n"

        self.text = self.text.strip()


    def initHtml(self, source, obfuscatekey = ""):
        """Initializes a Tiddler from HTML source code."""

        def decode_obfuscate_swap(text):
            """
            Does basic character pair swapping obfuscation.
            No longer used since 1.4.2, but can decode passages from 1.4.0 and 1.4.1
            """
            r = ''
            for c in text:
                upper = c.isupper()
                p = obfuscatekey.find(c.lower())
                if p <> -1:
                    if p % 2 == 0:
                        p1 = p + 1
                        if p1 >= len(obfuscatekey):
                            p1 = p
                    else:
                        p1 = p - 1
                    c = obfuscatekey[p1].upper() if upper else obfuscatekey[p1]
                r = r + c
            return r
        
        # title

        self.title = 'Untitled Passage'
        title_re = re.compile(r'(?:data\-)?(?:tiddler|name)="([^"]*?)"')
        title = title_re.search(source)
        if title:
            self.title = title.group(1)
            if obfuscatekey:
                self.title = decode_obfuscate_swap(self.title);

        # tags

        self.tags = []
        tags_re = re.compile(r'(?:data\-)?tags="([^"]*?)"')
        tags = tags_re.search(source)
        if tags and tags.group(1) != '':
            if obfuscatekey:
                self.tags = decode_obfuscate_swap(tags.group(1)).split(' ');
            else: self.tags = tags.group(1).split(' ')

        # creation date

        self.created = time.localtime()
        created_re = re.compile(r'(?:data\-)?created="([^"]*?)"')
        created = created_re.search(source)
        if created:
            self.created = decode_date(created.group(1))

        # modification date

        self.modified = time.localtime()
        modified_re = re.compile(r'(?:data\-)?modified="([^"]*?)"')
        modified = modified_re.search(source)
        if (modified):
            self.modified = decode_date(modified.group(1))

        # modifier
        modifier_re = re.compile(r'(?:data\-)?modifier="([^"]*?)"')
        modifier = modifier_re.search(source)
        if modifier:
            self.modifier = modifier.group(1)

        # position
        self.pos = [0,0]
        pos_re = re.compile(r'(?:data\-)?(?:twine\-)?position="([^"]*?)"')
        pos = pos_re.search(source)
        if pos:
            coord = pos.group(1).split(',')
            if len(coord) == 2:
                try:
                    self.pos = map(int, coord)
                except ValueError:
                    pass

        # body text
        self.text = ''
        text_re = re.compile(r'<div(?:[^"]|(?:".*?"))*?>((?:[^<]|<(?!\/div>))*)<\/div>')
        text = text_re.search(source)
        if (text):
            self.text = decode_text(text.group(1))
            if obfuscatekey:
                self.text = decode_obfuscate_swap(self.text)

    def toHtml(self, author, rot13):
        """Returns an HTML representation of this tiddler.
        The encoder arguments are sequences of functions that take a single text argument
        and return a modified version of the given text.
        """

        def applyRot13(text):
            return text.decode('rot13') if rot13 else text

        args = (
            ('tiddler', applyRot13(self.title.replace('"', '&quot;'))),
            ('tags', ' '.join(applyRot13(tag) for tag in self.tags)),
            ('created', encode_date(self.created)),
            ('modifier', author.replace('"', '&quot;'))
            )

        return u'<div%s%s>%s</div>' % (
            ''.join(' %s="%s"' % arg for arg in args),
            ' twine-position="%d,%d"' % tuple(self.pos) if hasattr(self, "pos") else "",
            encode_text(applyRot13(self.text))
            )


    def toTwee(self):
        """Returns a Twee representation of this tiddler."""
        output = u':: ' + self.title

        if len(self.tags) > 0:
            output += u' ['
            for tag in self.tags:
                output += tag + ' '
            output = output.strip()
            output += u']'

        output += u"\n" + self.text + u"\n\n\n"
        return output

    def isImage(self):
        return 'Twine.image' in self.tags

    def isAnnotation(self):
        return 'annotation' in self.tags

    def isStylesheet(self):
        return 'stylesheet' in self.tags

    def isScript(self):
        return 'script' in self.tags
    
    def isInfoPassage(self):
        return self.title in TiddlyWiki.INFO_PASSAGES
    
    def isStoryText(self):
        """ Excludes passages which do not contain renderable Twine code. """
        return self.title not in TiddlyWiki.UNFORMATTED_INFO_PASSAGES \
            and TiddlyWiki.INFO_TAGS.isdisjoint(self.tags)

    def isStoryPassage(self):
        """ A more restrictive variant of isStoryText that excludes the StoryTitle, StoryMenu etc."""
        return self.title not in TiddlyWiki.INFO_PASSAGES \
            and TiddlyWiki.INFO_TAGS.isdisjoint(self.tags)

    def linksAndDisplays(self):
        return list(set(self.links+self.displays))

    def update(self):
        """
        Update the lists of all passages linked/displayed by this one.
        Returns internal links and <<choice>>/<<actions>> macros.
        """
        if not self.isStoryText() and not self.isAnnotation() and not self.isStylesheet():
            self.displays = []
            self.links = []
            self.variableLinks = []
            self.images = []
            self.macros = []
            return

        images = set()
        macros = set()
        links = set()
        variableLinks = set()
        
        def addLink(link):
            style = TweeLexer.linkStyle(link)
            if style == TweeLexer.PARAM:
                variableLinks.add(link)
            elif style != TweeLexer.EXTERNAL:
                links.add(link)
        
        # <<display>>
        self.displays = list(set(re.findall(r'\<\<display\s+[\'"]?(.+?)[\'"]?\s?\>\>', self.text, re.IGNORECASE)))

        macros = set()
        # other macros (including shorthand <<display>>)
        for m in re.finditer(tweeregex.MACRO_REGEX, self.text):
            # Exclude shorthand <<print>>
            if m.group(1) and m.group(1)[0] != '$':
                macros.add(m.group(1))
        self.macros = list(macros)

        # Regular hyperlinks (also matches wiki-style links inside macros)
        for m in re.finditer(tweeregex.LINK_REGEX, self.text):
            addLink(m.group(2) or m.group(1))

        # Include images
        for m in re.finditer(tweeregex.IMAGE_REGEX, self.text):
            if m.group(5):
                addLink(m.group(5))
                
        # HTML data-passage links
        for m in re.finditer(tweeregex.HTML_REGEX, self.text):
            attrs = m.group(2)
            if attrs:
                dataPassage = re.search(r"""data-passage\s*=\s*(?:([^<>'"=`\s]+)|'((?:[^'\\]*\\.)*[^'\\]*)'|"((?:[^"\\]*\\.)*[^"\\]*)")""", attrs)
                if dataPassage:
                    link = dataPassage.group(1) or dataPassage.group(2) or dataPassage.group(3)
                    if m.group(1) == "img":
                        images.add(link)
                    else:
                        addLink(link)
                
        # <<choice passage_name [link_text]>>
        for block in re.findall(r'\<\<choice\s+(.*?)\s?\>\>', self.text):
            item = re.match(r'(?:"([^"]*)")|(?:\'([^\']*)\')|([^"\'\[\s]\S*)', block)
            if item:
                links.add(''.join(item.groups('')))

        # <<actions '' ''>>
        for block in re.findall(r'\<\<actions\s+(.*?)\s?\>\>', self.text):
            links.update(re.findall(r'[\'"](.*?)[\'"]', block))

        self.links = list(links)
        self.variableLinks = list(variableLinks)

        # Images

        for block in re.finditer(tweeregex.IMAGE_REGEX, self.text):
            images.add(block.group(4))

        self.images = list(images)

#
# Helper functions
#

def encode_text(text):
    """Encodes a string for use in HTML output."""
    output = text.replace('\\', '\s') \
        .replace('\t', '\\t') \
        .replace('<', '&lt;') \
        .replace('>', '&gt;') \
        .replace('"', '&quot;') \
        .replace('\0', '&#0;')
    output = re.sub(r'\r?\n', r'\\n', output)
    return output

def decode_text(text):
    """Decodes a string from HTML."""
    return text.replace('\\n', '\n') \
        .replace('\\t', '\t') \
        .replace('\s', '\\') \
        .replace('&lt;', '<') \
        .replace('&gt;', '>') \
        .replace('&quot;', '"')

def encode_date(date):
    """Encodes a datetime in TiddlyWiki format."""
    return time.strftime('%Y%m%d%H%M', date)


def decode_date(date):
    """Decodes a datetime from TiddlyWiki format."""
    return time.strptime(date, '%Y%m%d%H%M')

########NEW FILE########
__FILENAME__ = tweelexer
import re
import tweeregex

class TweeLexer:
    """Abstract base class that does lexical scanning on TiddlyWiki formatted text.
    """

    def getText(self):
        """Returns the text to lex.
        """
        raise NotImplementedError

    def getHeader(self):
        """Returns the current selected target header for this Twee Lexer.
        """
        raise NotImplementedError

    def passageExists(self, title):
        """Returns whether a given passage exists in the story.
        """
        raise NotImplementedError

    def includedPassageExists(self, title):
        """Returns whether a given passage exists in a StoryIncludes resource.
        """
        raise NotImplementedError

    def applyStyle(self, start, end, style):
        """Applies a style to a certain range.
        """
        raise NotImplementedError

    def lexMatchToken(self, text):
        m = text[:2].lower()
        if m in self.MARKUPS:
            return (self.MARKUP, self.MARKUPS[m])

        # link
        m = re.match(tweeregex.LINK_REGEX,text,re.U|re.I)
        if m: return (self.GOOD_LINK, m)

        # macro
        m = re.match(tweeregex.MACRO_REGEX,text,re.U|re.I)
        if m: return (self.MACRO, m)

        # image (cannot have interior markup)
        m = re.match(tweeregex.IMAGE_REGEX,text,re.U|re.I)
        if m: return (self.IMAGE, m)

        # Old-version HTML block (cannot have interior markup)
        m = re.match(tweeregex.HTML_BLOCK_REGEX,text,re.U|re.I)
        if m: return (self.HTML_BLOCK, m)

        # Inline HTML tags
        m = re.match(tweeregex.HTML_REGEX,text,re.U|re.I)
        if m: return (self.HTML, m)

        # Inline styles
        m = re.match(tweeregex.INLINE_STYLE_REGEX,text,re.U|re.I)
        if m: return (self.INLINE_STYLE, m)

        # Monospace
        m = re.match(tweeregex.MONO_REGEX,text,re.U|re.I)
        if m: return (self.MONO, m)

        # Comment
        m = re.match(tweeregex.COMMENT_REGEX,text,re.U|re.I)
        if m: return (self.COMMENT, m)

        return (None, None)

    def lex(self):
        """Performs lexical analysis on the text.
        Calls applyStyle() for each region found.
        """

        def applyParamStyle(pos2, contents):
            iterator = re.finditer(tweeregex.MACRO_PARAMS_REGEX, contents, re.U)
            for param in iterator:
                if param.group(1):
                    # String
                    self.applyStyle(pos2 + param.start(1), len(param.group(1)), self.PARAM_STR)
                elif param.group(2):
                    # Number
                    self.applyStyle(pos2 + param.start(2), len(param.group(2)), self.PARAM_NUM)
                elif param.group(3):
                    # Boolean or null
                    self.applyStyle(pos2 + param.start(3), len(param.group(3)), self.PARAM_BOOL)
                elif param.group(4):
                    # Variable
                    self.applyStyle(pos2 + param.start(4), len(param.group(4)), self.PARAM_VAR)

        def applyMacroStyle(pos, m):
            length = m.end(0)
            if self.passageExists(m.group(1)):
                self.applyStyle(pos, length, self.GOOD_LINK)
            elif self.includedPassageExists(m.group(1)):
                self.applyStyle(pos, length, self.STORYINCLUDE_LINK)
            else:
                self.applyStyle(pos, length, self.MACRO)
            # Apply different style to the macro contents
            group = 2 if m.group(1)[0] != '$' else 1
            contents = m.group(group)
            if contents:
                pos2 = pos + m.start(group)
                self.applyStyle(pos2, len(m.group(group)), self.PARAM)
                applyParamStyle(pos2, contents)

        pos = 0
        prev = 0
        text = self.getText()
        style = self.DEFAULT
        styleStack = []
        styleStart = pos
        inSilence = False
        macroNestStack = []; # macro nesting
        header = self.getHeader()

        self.applyStyle(0, len(text), self.DEFAULT);

        iterator = re.finditer(re.compile(tweeregex.COMBINED_REGEX, re.U|re.I), text[pos:]);

        for p in iterator:
            prev = pos+1
            pos = p.start()

            nextToken, m = self.lexMatchToken(p.group(0))

            # important: all style ends must be handled before beginnings
            # otherwise we start treading on each other in certain circumstances

            # markup
            if not inSilence and nextToken == self.MARKUP:
                if (style <= self.THREE_STYLES and style & m) or style == self.MARKUP:
                    self.applyStyle(styleStart, pos-styleStart+2, style)
                    style = styleStack.pop() if styleStack else self.DEFAULT
                    styleStart = pos+2
                else:
                    self.applyStyle(styleStart, pos-styleStart, style)
                    styleStack.append(style)
                    markup = m
                    if markup <= self.THREE_STYLES and style <= self.THREE_STYLES:
                        style |= markup
                    else:
                        style = markup
                    styleStart = pos
                pos += 1

            #link
            elif nextToken == self.GOOD_LINK:
                length = m.end(0);
                self.applyStyle(styleStart, pos-styleStart, style)

                # check for prettylinks
                s2 = self.GOOD_LINK
                if not m.group(2):
                    if self.includedPassageExists(m.group(1)):
                        s2 = self.STORYINCLUDE_LINK
                    elif not self.passageExists(m.group(1)):
                        s2 = TweeLexer.linkStyle(m.group(1))
                else:
                    if self.includedPassageExists(m.group(2)):
                        s2 = self.STORYINCLUDE_LINK
                    elif not self.passageExists(m.group(2)):
                        s2 = TweeLexer.linkStyle(m.group(2))
                self.applyStyle(pos, length, s2)
                # Apply a plainer style to the text, if any
                if m.group(2):
                    self.applyStyle(pos + m.start(1), len(m.group(1)), self.BOLD)
                if m.group(3):
                    self.applyStyle(pos + m.start(3), len(m.group(3)), self.PARAM)
                    applyParamStyle(pos + m.start(3), m.group(3))
                pos += length-1
                styleStart = pos+1

            #macro
            elif nextToken == self.MACRO:
                name = m.group(1)
                length = m.end(0)
                # Finish the current style
                self.applyStyle(styleStart, pos-styleStart, style)
                styled = False

                for i in header.nestedMacros():
                    # For matching pairs of macros (if/endif etc)
                    if name == i:
                        styled = True
                        macroNestStack.append((i,pos, m))
                        if i=="silently":
                            inSilence = True;
                            styleStack.append(style)
                            style = self.SILENT
                    elif header.isEndTag(name, i):
                        if macroNestStack and macroNestStack[-1][0] == i:
                            # Re-style open macro
                            macroStart,macroMatch = macroNestStack.pop()[1:];
                            applyMacroStyle(macroStart,macroMatch)
                        else:
                            styled = True
                            self.applyStyle(pos, length, self.BAD_MACRO)
                        if i=="silently":
                            inSilence = False;
                            style = styleStack.pop() if styleStack else self.DEFAULT

                if not styled:
                    applyMacroStyle(pos,m)
                pos += length-1
                styleStart = pos+1

            # image (cannot have interior markup)
            elif nextToken == self.IMAGE:
                length = m.end(0);
                self.applyStyle(styleStart, pos-styleStart, style)
                # Check for linked images
                if m.group(5):
                    self.applyStyle(pos, m.start(5), self.IMAGE)
                    if not self.passageExists(m.group(5)):
                        s2 = TweeLexer.linkStyle(m.group(5))
                        self.applyStyle(pos+m.start(5)-1, (m.end(5)-m.start(5))+2, s2)
                    else:
                        self.applyStyle(pos+m.start(5)-1, (m.end(5)-m.start(5))+2, self.GOOD_LINK)
                    self.applyStyle(pos+length-1,1, self.IMAGE)
                else:
                    self.applyStyle(pos, length, self.IMAGE)
                pos += length-1
                styleStart = pos+1

            # Inline styles
            elif not inSilence and nextToken == self.INLINE_STYLE:
                if (style == self.INLINE_STYLE or style == self.BAD_INLINE_STYLE):
                    self.applyStyle(styleStart, pos-styleStart+2, style)
                    style = styleStack.pop() if styleStack else self.DEFAULT
                    styleStart = pos+2
                else:
                    self.applyStyle(styleStart, pos-styleStart, style)
                    styleStack.append(style)
                    n = re.match(tweeregex.INLINE_STYLE_PROP_REGEX,text[pos+2:],re.U|re.I)
                    if n:
                        style = self.INLINE_STYLE
                        length = len(n.group(0))+2
                    else:
                        style = self.BAD_INLINE_STYLE
                        length = 2
                    styleStart = pos
                    pos += length-1

            # others
            elif nextToken in [self.HTML, self.HTML_BLOCK, self.COMMENT, self.MONO]:
                length = m.end(0);
                self.applyStyle(styleStart, pos-styleStart, style)
                self.applyStyle(pos, length, nextToken)
                pos += length-1
                styleStart = pos+1

        # Finish up unclosed styles
        self.applyStyle(styleStart, len(text), style)

        # Fix up unmatched macros
        while macroNestStack:
            macroStart,macroMatch = macroNestStack.pop()[1:];
            self.applyStyle(macroStart, macroMatch.end(0), self.BAD_MACRO)

    @staticmethod
    def linkStyle(dest):
        """Apply style for a link destination which does not seem to be an existent passage"""
        for t in ['http:', 'https:', 'ftp:', 'mailto:', 'javascript:', 'data:', r'[\./]*/']:
            if re.match(t, dest.lower()):
                return TweeLexer.EXTERNAL
        iscode = re.search(tweeregex.MACRO_PARAMS_VAR_REGEX+"|"+tweeregex.MACRO_PARAMS_FUNC_REGEX, dest, re.U)
        return TweeLexer.PARAM if iscode else TweeLexer.BAD_LINK

    # style constants
    # ordering of BOLD through to THREE_STYLES is important
    STYLE_CONSTANTS = range(0,28)
    DEFAULT, BOLD, ITALIC, BOLD_ITALIC, UNDERLINE, BOLD_UNDERLINE, ITALIC_UNDERLINE, THREE_STYLES, \
    GOOD_LINK, STORYINCLUDE_LINK, BAD_LINK, MARKUP, MACRO, BAD_MACRO, SILENT, COMMENT, MONO, IMAGE, EXTERNAL, HTML, HTML_BLOCK, INLINE_STYLE, \
    BAD_INLINE_STYLE, PARAM_VAR, PARAM_STR, PARAM_NUM, PARAM_BOOL, PARAM = STYLE_CONSTANTS

    # markup constants

    MARKUPS = {"''" : BOLD, "//" : ITALIC, "__" : UNDERLINE, "^^" : MARKUP, "~~" : MARKUP, "==" : MARKUP}

    # nested macros

    NESTED_MACROS = [ "if", "silently" ]


class VerifyLexer(TweeLexer):
    """Looks for errors in passage bodies.
    """

    # Takes a PassageWidget instead of a PassageFrame
    def __init__(self, widget):
        self.widget = widget
        self.twineChecks, self.stylesheetChecks, self.scriptChecks = self.getHeader().passageChecks()

    def getText(self):
        return self.widget.passage.text

    def getHeader(self):
        return self.widget.parent.parent.header

    def passageExists(self, title):
        return (self.widget.parent.passageExists(title, False))

    def includedPassageExists(self, title):
        return (self.widget.parent.includedPassageExists(title))

    def check(self):
        """Collect error messages for this passage, using the overridden applyStyles() method."""
        self.errorList = []
        if self.widget.passage.isScript():
            for i in self.scriptChecks:
                self.errorList += [e for e in i(passage=self.widget.passage)]

        elif self.widget.passage.isStylesheet():
            for i in self.stylesheetChecks:
                self.errorList += [e for e in i(passage=self.widget.passage)]

        else:
            self.lex()
        return sorted(self.errorList, key = lambda a: (a[1][0] if a[1] else float('inf')))

    def applyStyle(self, start, length, style):
        """Runs all of the checks on the current lex token, then saves errors produced."""
        end = start+length
        tag = self.widget.passage.text[start:end]
        for i in self.twineChecks:
            self.errorList += [e for e in i(tag, start=start, end=end, style=style, passage=self.widget.passage)]

########NEW FILE########
__FILENAME__ = tweeregex
# regexes

UNQUOTED_REGEX = r"""(?=(?:[^"'\\]*(?:\\.|'(?:[^'\\]*\\.)*[^'\\]*'|"(?:[^"\\]*\\.)*[^"\\]*"))*[^'"]*$)"""
LINK_REGEX = r"\[\[([^\|]*?)(?:\|(.*?))?\](\[.*?\])?\]"
MACRO_REGEX = r"""<<([^>\s]+)(?:\s*)((?:\\.|'(?:[^'\\]*\\.)*[^'\\]*'|"(?:[^"\\]*\\.)*[^"\\]*"|[^'"\\>]|>(?!>))*)>>"""
IMAGE_REGEX = r"\[([<]?)(>?)img\[(?:([^\|\]]+)\|)?([^\[\]\|]+)\](?:\[([^\]]*)\]?)?(\])"
HTML_BLOCK_REGEX = r"<html>((?:.|\n)*?)</html>"
HTML_REGEX = r"<(?:\/?([\w\-]+)(?:(\s+[\w\-]+(?:\s*=\s*(?:\".*?\"|'.*?'|[^'\">\s]+))?)+\s*|\s*)\/?)>"
INLINE_STYLE_REGEX = "@@"
INLINE_STYLE_PROP_REGEX = r"((?:([^\(@]+)\(([^\)]+)(?:\):))|(?:([^:@]+):([^;@]+);)|(?:(\.[^\.;@]+);))+"
MONO_REGEX = r"^\{\{\{\n(?:(?:^[^\n]*\n)+?)(?:^\}\}\}$\n?)|\{\{\{((?:.|\n)*?)\}\}\}"
COMMENT_REGEX = r"/%((?:.|\n)*?)%/"

COMBINED_REGEX = '(' + ')|('.join([ LINK_REGEX, MACRO_REGEX, IMAGE_REGEX, HTML_BLOCK_REGEX, HTML_REGEX, INLINE_STYLE_REGEX,\
                    MONO_REGEX, COMMENT_REGEX, r"''|\/\/|__|\^\^|~~|==" ]) + ')'

# macro param regex - string or number or boolean or variable
# (Mustn't match all-digit names)
MACRO_PARAMS_VAR_REGEX = r'(\$[\w_\.]*[a-zA-Z_\.]+[\w_\.]*)'

# This isn't included because it's too general - but it's used by the broken link lexer
# (Not including whitespace between name and () because of false positives)
MACRO_PARAMS_FUNC_REGEX = r'([\w\d_\.]+\((.*?)\))'

MACRO_PARAMS_REGEX = r'(?:("(?:[^\\"]|\\.)*"|\'(?:[^\\\']|\\.)*\'|(?:\[\[(?:[^\]]*)\]\]))' \
    +r'|\b(\-?\d+\.?(?:[eE][+\-]?\d+)?|NaN)\b' \
    +r'|(true|false|null|undefined)' \
    +r'|'+MACRO_PARAMS_VAR_REGEX \
    +r')'


# This includes BMP even though you can't normally import it
IMAGE_FILENAME_REGEX = r"[^\"']+\.(?:jpe?g|a?png|gif|bmp|webp|svg)"
EXTERNAL_IMAGE_URL = r"\s*['\"]?(" + IMAGE_FILENAME_REGEX + ")['\"]?\s*"

EXTERNAL_IMAGE_REGEX = IMAGE_REGEX.replace(r"([^\[\]\|]+)", EXTERNAL_IMAGE_URL)
HTML_IMAGE_REGEX = r"src\s*=" + EXTERNAL_IMAGE_URL
CSS_IMAGE_REGEX = r"url\s*\(" + EXTERNAL_IMAGE_URL + r"\)"

########NEW FILE########
__FILENAME__ = tweestyler
from tweelexer import TweeLexer
import wx, wx.stc

class TweeStyler(TweeLexer):
    """Applies syntax highlighting for Twee syntax in a wx.StyledTextCtrl.
    This needs to be passed the control it will be lexing, so it can
    look up the body text as needed.
    """

    def __init__(self, control, frame):
        self.ctrl = control
        self.frame = frame
        self.app = frame.app
        self.ctrl.Bind(wx.stc.EVT_STC_STYLENEEDED, lambda event: self.lex())
        self.initStyles()

    def initStyles(self):
        """
        Initialize style definitions. This is automatically invoked when
        the constructor is called, but should be called any time font
        preferences are changed.
        """
        bodyFont = wx.Font(self.app.config.ReadInt('windowedFontSize'), wx.MODERN, wx.NORMAL, \
                           wx.NORMAL, False, self.app.config.Read('windowedFontFace'))
        monoFont = wx.Font(self.app.config.ReadInt('monospaceFontSize'), wx.MODERN, wx.NORMAL, \
                           wx.NORMAL, False, self.app.config.Read('monospaceFontFace'))

        self.ctrl.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, bodyFont)
        self.ctrl.StyleClearAll()

        for i in self.STYLE_CONSTANTS:
            self.ctrl.StyleSetFont(i, bodyFont)
        
        # Styles 1-8 are BOLD, ITALIC, UNDERLINE, and bitwise combinations thereof        
        for i in range(0,8):
            if (i & 1):
                self.ctrl.StyleSetBold(i, True)
            if (i & 2):
                self.ctrl.StyleSetItalic(i, True)
            if (i & 4):
                self.ctrl.StyleSetUnderline(i, True)

        self.ctrl.StyleSetBold(self.GOOD_LINK, True)
        self.ctrl.StyleSetForeground(self.GOOD_LINK, self.GOOD_LINK_COLOR)

        self.ctrl.StyleSetBold(self.BAD_LINK, True)
        self.ctrl.StyleSetForeground(self.BAD_LINK, self.BAD_LINK_COLOR)
        self.ctrl.StyleSetBold(self.BAD_MACRO, True)
        self.ctrl.StyleSetForeground(self.BAD_MACRO, self.BAD_LINK_COLOR)

        self.ctrl.StyleSetBold(self.STORYINCLUDE_LINK, True)
        self.ctrl.StyleSetForeground(self.STORYINCLUDE_LINK, self.STORYINCLUDE_COLOR)

        self.ctrl.StyleSetForeground(self.MARKUP, self.MARKUP_COLOR)

        self.ctrl.StyleSetForeground(self.INLINE_STYLE, self.MARKUP_COLOR)

        self.ctrl.StyleSetBold(self.BAD_INLINE_STYLE, True)
        self.ctrl.StyleSetForeground(self.BAD_INLINE_STYLE, self.BAD_LINK_COLOR)

        self.ctrl.StyleSetBold(self.HTML, True)
        self.ctrl.StyleSetForeground(self.HTML, self.HTML_COLOR)

        self.ctrl.StyleSetForeground(self.HTML_BLOCK, self.HTML_COLOR)

        self.ctrl.StyleSetBold(self.MACRO, True)
        self.ctrl.StyleSetForeground(self.MACRO, self.MACRO_COLOR)

        self.ctrl.StyleSetItalic(self.COMMENT, True)
        self.ctrl.StyleSetForeground(self.COMMENT, self.COMMENT_COLOR)

        self.ctrl.StyleSetForeground(self.SILENT, self.COMMENT_COLOR)

        self.ctrl.StyleSetFont(self.MONO, monoFont)

        self.ctrl.StyleSetBold(self.EXTERNAL, True)
        self.ctrl.StyleSetForeground(self.EXTERNAL, self.EXTERNAL_COLOR)

        self.ctrl.StyleSetBold(self.IMAGE, True)
        self.ctrl.StyleSetForeground(self.IMAGE, self.IMAGE_COLOR)

        self.ctrl.StyleSetBold(self.PARAM, True)
        self.ctrl.StyleSetForeground(self.PARAM, self.PARAM_COLOR)

        self.ctrl.StyleSetBold(self.PARAM_VAR, True)
        self.ctrl.StyleSetForeground(self.PARAM_VAR, self.PARAM_VAR_COLOR)

        self.ctrl.StyleSetBold(self.PARAM_STR, True)
        self.ctrl.StyleSetForeground(self.PARAM_STR, self.PARAM_STR_COLOR)

        self.ctrl.StyleSetBold(self.PARAM_NUM, True)
        self.ctrl.StyleSetForeground(self.PARAM_NUM, self.PARAM_NUM_COLOR)

        self.ctrl.StyleSetBold(self.PARAM_BOOL, True)
        self.ctrl.StyleSetForeground(self.PARAM_BOOL, self.PARAM_BOOL_COLOR)

    def getText(self):
        return self.ctrl.GetTextUTF8()

    def passageExists(self, title):
        return (self.frame.widget.parent.passageExists(title, False))

    def includedPassageExists(self, title):
        return (self.frame.widget.parent.includedPassageExists(title))

    def applyStyle(self, start, end, style):
        self.ctrl.StartStyling(start, self.TEXT_STYLES)
        self.ctrl.SetStyling(end, style)

    def getHeader(self):
        return self.frame.getHeader()

    # style colors

    GOOD_LINK_COLOR = '#3333cc'
    EXTERNAL_COLOR = '#337acc'
    STORYINCLUDE_COLOR = '#906fe2'
    BAD_LINK_COLOR = '#cc3333'
    MARKUP_COLOR = '#008200'
    MACRO_COLOR = '#a94286'
    COMMENT_COLOR = '#868686'
    IMAGE_COLOR = '#088A85'
    HTML_COLOR = '#4d4d9d'

    # param colours

    PARAM_COLOR = '#7f456a'
    PARAM_VAR_COLOR = '#005682'
    PARAM_BOOL_COLOR = '#626262'
    PARAM_STR_COLOR = '#008282'
    PARAM_NUM_COLOR = '#A15000'

    TEXT_STYLES = 31    # mask for StartStyling() to indicate we're only changing text styles

########NEW FILE########
__FILENAME__ = version
versionString = '1.4.2'

########NEW FILE########
