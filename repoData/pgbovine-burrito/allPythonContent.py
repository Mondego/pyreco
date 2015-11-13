__FILENAME__ = bash_burrito_to_json
# This command runs before EVERY bash command, as dictated by bash_burrito.sh

import os, sys, time, json

LOGFILE = '/var/log/burrito/current-session/bash-history.log'

def get_ms_since_epoch():
  milliseconds_since_epoch = int(time.time() * 1000)
  return milliseconds_since_epoch


# Parse arguments:
bash_pid = int(sys.argv[1])
pwd      = sys.argv[2]
command  = sys.argv[3:] # note that this is a list!

result = dict(command=command, bash_pid=bash_pid, pwd=pwd,timestamp=get_ms_since_epoch())

assert os.path.isdir(pwd) # sanity check

# If you want to remove symlinks in pwd, use ...
#   os.path.realpath(pwd) # canonicalize the path to remove symlinks

# use the most compact separators:
compactJSON = json.dumps(result, separators=(',',':'))

f = open(LOGFILE, 'a')
print >> f, compactJSON
f.close()

########NEW FILE########
__FILENAME__ = BurritoUtils
import time, json, datetime

def get_ms_since_epoch():
  milliseconds_since_epoch = int(time.time() * 1000)
  return milliseconds_since_epoch

def to_compact_json(obj):
  # use the most compact separators:
  return json.dumps(obj, separators=(',',':'))

# this is dumb since mongodb stores datetimes internally as int64s!!!
def encode_datetime(t):
  return datetime.datetime.fromtimestamp(float(t) / 1000)


import os

HOMEDIR = os.environ['HOME']
assert HOMEDIR

def prettify_filename(fn):
  # abbreviate home directory:
  if fn.startswith(HOMEDIR):
    fn = '~' + fn[len(HOMEDIR):]
  return fn


########NEW FILE########
__FILENAME__ = BurritoUtils
../BurritoUtils.py
########NEW FILE########
__FILENAME__ = ClipboardLogger
# Logs clipboard copy-and-paste activity in JSON format
#
# Timestamps and click coordinates can be synchronized with the
# GUItracer.py log to get the source and destination windows for the
# copy and paste, respectively.


'''
Limitations: Can only detect paste events of the 'primary' clipboard,
which are triggered with a mouse middle-click.

This script CANNOT detect paste events of the Gtk clipboard, which can
either be triggered by Ctrl-V or by selecting from a menu item.

Known bug: If you copy and then middle-click paste on another
gnome-terminal without first clicking on it, then the mouse click event
triggers BEFORE the window switch event, so the system will think that
you pasted in your OLD window ... wow this doesn't happen ALL the time
... sometimes it happens, though.  i guess it depends on the order of
at-spi receiving "mouse button released" and active window focus change
events.

  - Note: I've seen this happen with Google Chrome as well!

  - One possible workaround (which I haven't implemented yet) is to
  detect such cases (by seeing whether the click was OUT OF BOUNDS of
  the supposedly active window in the matched paste destination
  DesktopState), and then finding the NEXT DesktopState entry in the
  list, which should be the one right AFTER the window switch.

'''

import time
import pyatspi
import gtk, gobject
from BurritoUtils import *


def middleMouseEventHandler(event):
  global theClipboard

  # if there's an empty clipboard, don't bother doing anything!!!
  if not theClipboard.primary_clipboard_text: return

  xCoord = int(event.detail1)
  yCoord = int(event.detail2)
  paste_time_ms = get_ms_since_epoch()

  # log the paste event now ...
  serializedState = dict(x=xCoord, y=yCoord,
                         copy_time_ms=theClipboard.copy_time_ms,
                         timestamp=paste_time_ms,
                         event_type='paste',
                         contents=theClipboard.primary_clipboard_text)

  compactJSON = to_compact_json(serializedState)
  print >> outf, compactJSON
  outf.flush() # don't forget!


# Clipboard code adapted from:
#   Glipper - Clipboardmanager for GNOME
#   Copyright (C) 2007 Glipper Team
class Clipboard(gobject.GObject):
   def __init__(self):
      gobject.GObject.__init__(self)

      # primary X clipboard ... highlight to copy, middle-mouse-click to paste
      self.primary_clipboard = gtk.clipboard_get("PRIMARY")

      self.primary_clipboard_text = None
      self.copy_time_ms = None

      # 'owner-change' event is triggered when there's a new clipboard entry
      self.primary_clipboard.connect('owner-change', self.on_primary_clipboard_owner_change)


      # We don't support the Gtk clipboard for now since we can't detect
      # paste events.
      # Ctrl-C copy, Ctrl-V paste
      #self.default_clipboard = gtk.clipboard_get()
      #self.default_clipboard_text = self.default_clipboard.wait_for_text()
      #self.default_clipboard.connect('owner-change', self.on_default_clipboard_owner_change)
 
  
   def on_primary_clipboard_owner_change(self, clipboard, event):
      assert clipboard == self.primary_clipboard
      self.copy_time_ms = get_ms_since_epoch()
      self.primary_clipboard_text = self.primary_clipboard.wait_for_text()

      # log the copy event right away, but just record the timestamp and
      # not the contents ...
      global outf
      serializedState = dict(timestamp=self.copy_time_ms, event_type='copy')
      compactJSON = to_compact_json(serializedState)
      print >> outf, compactJSON
      outf.flush() # don't forget!

     
   #def on_default_clipboard_owner_change(self, clipboard, event):
   #   assert clipboard == self.default_clipboard
   #   self.default_clipboard_text = self.default_clipboard.wait_for_text()
   #   print 'DEFAULT:', self.default_clipboard_text

 
# global singleton
theClipboard = Clipboard()
outf = None

def initialize(reg):
  global outf
  outf = open('/var/log/burrito/current-session/clipboard.log', 'w')

  # register the middle mouse button click
  # VERY IMPORTANT: register the RELEASE event ('2r') of the middle mouse
  # button, since that's the only way to get the PROPER x and y
  # coordinates; otherwise if you register the PRESS event ('2p'), then
  # the coordinates will be INCORRECT ... AHHHHH!
  reg.registerEventListener(middleMouseEventHandler, 'mouse:button:2r')


def teardown():
  global outf
  outf.close()


########NEW FILE########
__FILENAME__ = evince_demo
import pyatspi

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)
 
def foo(event):
  if event.host_application.name != 'evince': return
  print event

reg.registerEventListener(foo, 'object')
reg.registerEventListener(foo, 'window')
reg.registerEventListener(foo, 'focus')

try:
   pyatspi.Registry.start()
except KeyboardInterrupt:
   pass

pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = mouseTracer
import time
import pyatspi

reg = pyatspi.Registry()    # get the Registry singleton

def get_ms_since_epoch():
  milliseconds_since_epoch = int(time.time() * 1000)
  return milliseconds_since_epoch

def mouseEventHandler(event):
  xCoord = int(event.detail1)
  yCoord = int(event.detail2)
  print xCoord, yCoord, dir(event)

reg.registerEventListener(mouseEventHandler, 'mouse:button:2p')

try:
   pyatspi.Registry.start()
except KeyboardInterrupt:
   pass
finally:
  pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = printDesktopTree
# Prints the entire f***ing desktop tree

import pyatspi

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)
 
def printAndRecurse(elt, indents=2):
  for (i, child) in enumerate(elt):
    print (' ' * (indents+2)), i, child
    printAndRecurse(child, indents+2)


for app in desktop:
  if app:
    print app
    printAndRecurse(app)


########NEW FILE########
__FILENAME__ = tracker_demo
# Adapted from:
#   http://developers-blog.org/blog/default/2010/08/21/Track-window-and-widget-events-with-AT-SPI

# TODO: can I get PIDs of controlling processes of each window?


'''
Notes about window events:

- When you drag to move a window, it first generates 'window:deactivate'
  when you start dragging, and then 'window:activate' when you release the
  mouse and finish dragging

- When you finish resizing a window, a 'window:activate' event fires

- 'window:minimize', 'window:maximize', and 'window:restore' are for
  minimizing, restoring, and maximizing windows, respectively

- 'window:create' is when a new window pops up.  Perhaps this is a good
  time to update the list of running applications?

- when a window is closed, it seems like only a 'window:deactivate'
  event fires (there's no window close event???)


Notes about object events:

- 'object:state-changed:active' fires on a 'frame' object whenever it
  comes into focus (with event.detail1 == 1)

- 'object:bounds-changed' fires on a 'frame' object whenever it's
  resized

- 'object:property-change:accessible-name' fires on a 'frame' object
  whenever its title changes ... good for detecting webpage and terminal
  title changes

'''


import pyatspi

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)
 

def genericEventCallback(event):
  print "GENERIC:", event
  print


# SUPER hacky way of getting the current URL string from Google
# Chrome and Firefox ... there MUST be a better way :)
#
# use Accerciser to find the exact location of the URL bar ...
# note that this will BREAK if the user's Chrome/Firefox GUI even
# looks slightly different than my own GUI:
def getChromeUrlField(frameElt):
  return frameElt[0][0][2][0][0][1][0][1][1][0][0]

def getFirefoxUrlField(frameElt):
  return frameElt[11][6][1]


def windowEventCallback(event):
  print event
  print
  return # stent
  for app in desktop:
    if app:
      print app
      for child in app:
        if child.getRoleName() == 'frame':
          print '  window title:', child.name
          comp = child.queryComponent()
          print '    abs. position:', comp.getPosition(0)
          #print '    rel. position:', comp.getPosition(1)
          print '    size:', comp.getSize()

          urlField = None
          if app.name == 'google-chrome':
            urlField = getChromeUrlField(child)
          elif app.name == 'Firefox':
            urlField = getFirefoxUrlField(child)

          if urlField:
            urlTextField = urlField.queryEditableText()
            urlString = urlTextField.getText(0, urlTextField.characterCount)
            print '    URL bar:', urlString
  print '---'


def stateChangedEventCallback(event):

  if event.source.getRoleName() != 'frame': return

  print event
  print
  return # stent

  # filter to make it less inefficient:
  if event.source.getRoleName() != 'text':
    return

  evt_app = event.source.getApplication().name
  if evt_app != 'google-chrome' and evt_app != 'Firefox':
    return


  # TODO: this is really inefficient right now ... store these fields in
  # a local cache somewhere :)
  for app in desktop:
    if app:
      if app.name in ('google-chrome', 'Firefox'):
        for child in app:
          if child.getRoleName() == 'frame':
            if app.name == 'google-chrome':
              urlField = getChromeUrlField(child)
            else:
              urlField = getFirefoxUrlField(child)
            if event.source == urlField:
              urlTextField = urlField.queryEditableText()
              urlString = urlTextField.getText(0, urlTextField.characterCount)
              print '  CHANGED window URL bar:', urlString


#reg.registerEventListener(windowEventCallback, 'window')

#reg.registerEventListener(genericEventCallback, 'focus') # doesn't seem to work well


#reg.registerEventListener(stateChangedEventCallback, 'object:state-changed')



# Detects when a frame becomes 'active', which happens when it comes
# into focus or when it's finished being moved ... seems pretty robust
def frameActive(event):
  if event.source.getRoleName() != 'frame': return
  if event.detail1 == 1:
    print event
    print event.host_application
    print

reg.registerEventListener(frameActive, 'object:state-changed:active')


def frameTitleChange(event):
  if event.source.getRoleName() != 'frame': return
  print event

reg.registerEventListener(frameTitleChange, 'object:property-change:accessible-name')


#def windowEvent(event):
#  print event
#
#reg.registerEventListener(windowEvent, 'window')


try:
   pyatspi.Registry.start()
except KeyboardInterrupt:
   pass

pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = window
import pyatspi

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)
 
def foo(event):
  if event.source.getRole() != pyatspi.constants.ROLE_FRAME: return

  print dir(event)
  if event.detail1 == 0:
    print event

reg.registerEventListener(foo, 'window')
reg.registerEventListener(foo, 'object:state-changed:visible')

try:
   pyatspi.Registry.start()
except KeyboardInterrupt:
   pass

pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = window_create
import pyatspi

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)
 
def foo(event):
  if event.source.getRole() != pyatspi.constants.ROLE_FRAME: return
  print event, event.source, event.source.getIndexInParent()

reg.registerEventListener(foo, 'window:create')

try:
   pyatspi.Registry.start()
except KeyboardInterrupt:
   pass

pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = xpad_demo
import os, pyatspi, time, gobject, json

# get the Registry singleton
reg = pyatspi.Registry()

# get desktop
desktop = reg.getDesktop(0)

XPAD_DATA_DIR = os.path.join(os.getenv("HOME"), ".config/xpad/")


last_xpad_event_timestamp = 0
POLLING_INTERVAL_MS = 5000

# heuristic to detect if you're still typing when poll_for_xpad_change is
# called, in which case, DON'T do a save
CONTINUOUS_TYPING_MS = 500

def get_ms_since_epoch():
  milliseconds_since_epoch = int(time.time() * 1000)
  return milliseconds_since_epoch
 

def xpad_text_changed(event):
  if event.host_application.name != 'xpad': return # VERY IMPORTANT!
  global last_xpad_event_timestamp
  last_xpad_event_timestamp = get_ms_since_epoch()


def save_xpad_buffers(t):
  # the xpad data files are saved in $HOME/.config/xpad/content-*
  xpad_data_files = [e for e in os.listdir(XPAD_DATA_DIR) if e.startswith('content-')]

  result = {}
  result['timestamp'] = t
  for f in xpad_data_files:
    path = os.path.join(XPAD_DATA_DIR, f)
    result[f] = open(path).read()

  # use the most compact separators:
  compactJSON = json.dumps(result, separators=(',',':'))

  outf = open('/var/log/burrito/current-session/xpad-notes.log', 'a') # append!
  print >> outf, compactJSON
  outf.close()


def poll_for_xpad_change():
  global last_xpad_event_timestamp
  t = get_ms_since_epoch()

  delta = (t - last_xpad_event_timestamp)

  # if the user still appears to be typing, then don't save!
  if CONTINUOUS_TYPING_MS < delta < POLLING_INTERVAL_MS:
    save_xpad_buffers(t)

  return True # so that gobject.timeout_add will keep firing!


reg.registerEventListener(xpad_text_changed, 'object:text-changed')

def asyncHandler():
  pyatspi.Registry.pumpQueuedEvents()
  return True # so that gobject.timeout_add will keep firing!

gobject.timeout_add(200, asyncHandler)
gobject.timeout_add(POLLING_INTERVAL_MS, poll_for_xpad_change)

save_xpad_buffers(get_ms_since_epoch()) # do a save of the initial start-up state

try:
 # asynchronous is mandatory if you want poll_for_xpad_change to work!
 pyatspi.Registry.start(async=True, gil=False)
except KeyboardInterrupt:
 pass
finally:
  pyatspi.Registry.stop()


########NEW FILE########
__FILENAME__ = GUItracer
# GUI tracer that works with the Linux AT-SPI Accessibility API
#
# Tested on Fedora 14 running the GNOME GUI environment
#
# Pre-req: Before this script will work, you need to first go to
#          this menu: System -> Preferences -> Assistive Technologies
#          check the "Enable assistive technologies" box,
#          then log out and log back in.

# TODO: Factor out Chrome tracing code into its own module to better
# separate out the "platform" from the "apps"

import sys
from BurritoUtils import *
import XpadTracer
import ClipboardLogger


# Output to a series of log files with the prefix of:
# /var/log/burrito/current-session/gui.trace and the
# suffix of .0, .1, etc., switching over to a new file whenever
# MAX_LINES_IN_LOGFILE has been reached
MAX_LINES_IN_LOGFILE = 10000 # 10000 * ~1K per entry = ~10MB per log file
OUTFILE_BASE = '/var/log/burrito/current-session/gui.trace'
num_lines_in_cur_file = 0
cur_file_index = 0
cur_fd = open(OUTFILE_BASE + '.' + str(cur_file_index), 'w')


import pyatspi
import gobject # requires pygtk, i think


# Let's not support Firefox for now since it seems to have some quirks.
#
# e.g., when a window is minimized, its state set usually contains:
#      pyatspi.constants.STATE_ICONIFIED
# except that it doesn't work for Firefox for some reason!!!

# SUPER hacky way of getting the current URL text string from
# Google Chrome and Firefox ... there MUST be a better way :)
#
# Use printDesktopTree.py to find out the exact path to the URL boxes
#
# use the accessibility API to find the exact location of the URL bar.
# Note that this will BREAK if the user's Chrome/Firefox GUI even
# looks slightly different than my own GUI:
def getChromeUrlField(frameElt):
  return frameElt[0][0][2][0][0][1][0][1][1][0][0]

def getFirefoxUrlField(frameElt):
  return frameElt[10][6][1]


# Note: pyatspi has some potentially useful utility functions:
#   http://people.gnome.org/~parente/pyatspi/doc/pyatspi.utils-module.html


# TODO: can I get PIDs of controlling processes of each window?
# (the 'application names' collected by pyatspi sometimes don't exactly
# match the names collected by SystemTap)
# - ugh, sadly I don't think so :(


# What happens when the user has multiple virtual desktops?
#   ahhh, very interesting ... when you move an app to another virtual
#   desktop, it shows up as STATE_ICONIFIED, so it's like it was MINIMIZED


# Class hierarchy: A Desktop contains 0 or more Application instances,
# and each Application contains 1 or more Window instances.
# (ignore applications with no windows)

class Desktop:
  def __init__(self, atspiDesktop):
    # Key:   app ID (INTEGER!  hopefully unique ... try to open multiple
    #                'evince' windows to see how app names are NOT unique,
    #                but IDs are)
    # Value: Application instance
    self.appsDict = {}

    self.atspiDesktop = atspiDesktop
    self.__updateAppsDict()


  # update self.appsDict by scanning through self.atspiDesktop again so
  # that we can check for apps that have been newly-created or deleted
  #
  # return True if the number of apps has changed
  def __updateAppsDict(self):
    newAppsDict = {}

    for app in self.atspiDesktop:
      if not app: continue # some app entries are None; weird

      intID = int(app.id) # ugh, gross casts!

      if intID in self.appsDict:
        # do a straight-up copy for efficiency
        newAppsDict[intID] = self.appsDict[intID]
      else:
        # create a new one, which might incur a *slight* delay
        newApp = Application(app)
        # only add to self.apps if there are SOME windows
        if len(newApp.windows):
          newAppsDict[intID] = newApp

    appNumChanged = (len(self.appsDict) != len(newAppsDict))

    self.appsDict = newAppsDict # VERY important!
    return appNumChanged


  # do an incremental update for efficiency
  def updateApp(self, atspiApp):
    self.__updateAppsDict() # check for added/deleted apps

    try:
      # make sure to cast ID as an int!!!
      self.appsDict[int(atspiApp.id)].updateAllFrames()
    except LookupError:
      # the atspiApp object might now be screwy
      pass


  def printMe(self):
    print '=== DESKTOP ==='
    for appID in sorted(self.appsDict.keys()):
      self.appsDict[appID].printMe()

  
  # serialize the current state to a big dict, which can later be
  # converted to JSON
  def serialize(self):
    out = {}
    for appID in self.appsDict:
      out[appID] = self.appsDict[appID].serialize()

    return out


class Application:
  def __init__(self, app):
    self.name = app.name
    self.atspiApp = app

    # Key: unique index of Window object (as given by int(getIndexInParent()))
    # Value: Window object
    self.windows = {}
    self.updateAllFrames()

  # do the super-simple thing and just create NEW Window objects for all
  # frames in this app ...
  def updateAllFrames(self):
    self.windows = {} # clear first!

    for child in self.atspiApp:
      # sometimes apps will have null or non-frame children, so skip those!
      if not child: continue
      if child.getRole() != pyatspi.constants.ROLE_FRAME: continue

      # create a new Window object, which might incur a *slight* delay
      self.windows[int(child.getIndexInParent())] = Window(child, self)


  # return True if the number of frames or cur_atspiFrame have changed
  def updateFrame(self, cur_atspiFrame):
    # update self.windows to account for the fact that frames might
    # have been added or deleted to this app since the last update
    newWindows = {}
    vals = self.windows.values()
    for child in self.atspiApp:
      # recycle existing Window instances if found (for efficiency)
      childFound = False
      for w in vals:
        if child == w.atspiFrame:
          newWindows[int(child.getIndexInParent())] = w
          childFound = True
          break

      # new frame!
      if not childFound:
        if child.getRole() != pyatspi.constants.ROLE_FRAME: continue
        # create a new Window object, which might incur a *slight* delay
        newWindows[int(child.getIndexInParent())] = Window(child, self)

    frameNumChanged = (len(self.windows) != len(newWindows))
    self.windows = newWindows

    for w in self.windows.values():
      if cur_atspiFrame == w.atspiFrame:
        curFrameChanged = w.update()
        return frameNumChanged or curFrameChanged

    # bug triggered when you open Firefox
    assert False # should never reach here


  def printMe(self):
    print 'APP:', self.name
    for w in self.windows.values():
      w.printMe()

  def serialize(self):
    return dict(name=self.name, windows=dict([(k,w.serialize()) for (k,w) in self.windows.iteritems()]))


# pyatspi uses the term 'frame' to refer to what we think of as windows
class Window:
  def __init__(self, frame, parentApp):
    self.parent = parentApp
    self.atspiFrame = frame

    self.title = frame.name

    comp = frame.queryComponent()
    self.x, self.y = comp.getPosition(0)
    self.width, self.height = comp.getSize()

    myStates = frame.getState().getStates()
    self.is_active = pyatspi.constants.STATE_ACTIVE in myStates
    self.is_minimized = pyatspi.constants.STATE_ICONIFIED in myStates

    # special field for Firefox and Google Chrome
    self.browserURL = self.getURL()

    assert not (self.is_active and self.is_minimized)


  # returns a URL string if applicable, or 'None' if the Window isn't a
  # Firefox or Chrome web browser window
  def getURL(self):
    urlField = None
    if self.parent.name == 'google-chrome':
      urlField = getChromeUrlField(self.atspiFrame)
    elif self.parent.name == 'Firefox':
      urlField = getFirefoxUrlField(self.atspiFrame)

    if urlField:
      urlTextField = urlField.queryEditableText()

      # for some weird reason, google-chrome puts an extra 'junk'
      # two bytes at the end of urlString, so adjust accordingly
      nChars = urlTextField.characterCount
      if self.parent.name == 'google-chrome':
        assert nChars > 0
        nChars -= 2
      return urlTextField.getText(0, nChars)

    return None


  # update fields by re-querying self.atspiFrame
  # and return 'True' if any field has been modified
  def update(self):
    modified = False

    new_title = self.atspiFrame.name
    comp = self.atspiFrame.queryComponent()
    new_x, new_y = comp.getPosition(0)
    new_width, new_height = comp.getSize()
    new_states = self.atspiFrame.getState().getStates()
    new_is_active = pyatspi.constants.STATE_ACTIVE in new_states
    new_is_minimized = pyatspi.constants.STATE_ICONIFIED in new_states
    new_browserURL = self.getURL()

    if self.title != new_title:
      self.title = new_title
      modified = True

    if self.x != new_x:
      self.x = new_x
      modified = True

    if self.y != new_y:
      self.y = new_y
      modified = True

    if self.width != new_width:
      self.width = new_width
      modified = True

    if self.height != new_height:
      self.height = new_height
      modified = True

    if self.is_active != new_is_active:
      self.is_active = new_is_active
      modified = True

    if self.is_minimized != new_is_minimized:
      self.is_minimized = new_is_minimized
      modified = True

    if self.browserURL != new_browserURL:
      self.browserURL = new_browserURL
      modified = True

    assert not (self.is_active and self.is_minimized)
    return modified


  def printMe(self):
    if self.is_active:
      print '*',
    elif self.is_minimized:
      print 'm',
    else:
      print ' ',

    print self.title

    print '    x:%d,y:%d (%dx%d)' % (self.x, self.y, self.width, self.height)
    if self.browserURL:
      print '   ', self.browserURL


  def serialize(self):
    out = {}

    out['title'] = self.title
    out['x'] = self.x
    out['y'] = self.y
    out['width'] = self.width
    out['height'] = self.height
    out['is_active'] = self.is_active
    out['is_minimized'] = self.is_minimized
    if self.browserURL is not None:
      out['browserURL'] = self.browserURL

    return out


reg = pyatspi.Registry()    # get the Registry singleton
atspiDesktop = reg.getDesktop(0) # get desktop

# The plan here is to initialize a singleton myDesktop instance at the
# beginning of execution and to selectively update myDesktop as events
# occur while making AS FEW QUERIES to the at-spi API as possible, since
# these queries can be SLOW!

myDesktop = Desktop(atspiDesktop) # singleton

'''
Notes about window events:

- When you drag to move a window, it first generates 'window:deactivate'
  when you start dragging, and then 'window:activate' when you release the
  mouse and finish dragging

- When you finish resizing a window, a 'window:activate' event fires
  (doesn't seem to happen for Google Chrome, though)

- 'window:minimize', 'window:maximize', and 'window:restore' are for
  minimizing, restoring, and maximizing windows, respectively

- 'window:create' is when a new window pops up.  Perhaps this is a good
  time to update the list of running applications?

- when a window is closed, it seems like only a 'window:deactivate'
  event fires (there's no window close event???)


Notes about object events:

- 'object:state-changed:active' fires on a 'frame' object whenever it
  comes into focus (with event.detail1 == 1)

- 'object:state-changed:iconified' fires whenever it gets "minimized",
  it seems

- 'object:bounds-changed' fires on a 'frame' object whenever it's
  resized

- 'object:property-change:accessible-name' fires on a 'frame' object
  whenever its title changes ... good for detecting webpage and terminal
  title changes


'focus' events are kinda flaky, but they seem to be triggered when the
mouse clicks on a particular GUI element like a panel or something.


Adapted from:
   http://developers-blog.org/blog/default/2010/08/21/Track-window-and-widget-events-with-AT-SPI
'''


def printDesktopState(event=None):
  # nasty globals!
  global cur_fd, num_lines_in_cur_file, cur_file_index

 
  desktop_state = myDesktop.serialize()
  timestamp     = get_ms_since_epoch()

  serializedState = dict(desktop_state=desktop_state, timestamp=timestamp)

  # for some sorts of events, we should include the event info:
  if event and event.type == 'window:create':
    assert event.source.getRole() == pyatspi.constants.ROLE_FRAME
    wIdx = int(event.source.getIndexInParent()) # make sure to cast as int!

    # can be negative on error, so punt on those ...
    if wIdx >= 0:
      serializedState['event_type'] = 'window:create'
      serializedState['src_app_id'] = int(event.host_application.id)
      serializedState['src_frame_index'] = wIdx

      # sanity checks!!!
      assert serializedState['src_app_id'] in desktop_state
      assert serializedState['src_frame_index'] in desktop_state[serializedState['src_app_id']]['windows']


  compactJSON = to_compact_json(serializedState)

  # for debugging ...
  '''
  if event and event.type == 'window:create':
    for i in range(100): print
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(serializedState)
  '''


  print >> cur_fd, compactJSON

  cur_fd.flush() # force a flush to disk

  # roll over to a new file if necessary
  num_lines_in_cur_file += 1
  if num_lines_in_cur_file >= MAX_LINES_IN_LOGFILE:
    cur_fd.close()

    cur_file_index += 1
    num_lines_in_cur_file = 0
    cur_fd = open(OUTFILE_BASE + '.' + str(cur_file_index), 'w')



def frameEventHandler(event):
  try:
    if event.source.getRole() != pyatspi.constants.ROLE_FRAME:
      return
  except LookupError:
    # silently fail on weird at-spi lookup errors o.O
    return

  myDesktop.updateApp(event.host_application)

  #print event # debugging
  printDesktopState(event)


# the minimal set of required listeners to get what we want ...
#
# Known shortcomings:
# - won't fire an update event when a Chrome window is moved :(
#
# - for SOME apps, won't fire an update event when you CLOSE a window
# without first putting it in focus (since the focus never changed from
# the foreground window, and stateChangedHandler doesn't work either)


# we want to detect BOTH when a frame becomes active and also inactive
reg.registerEventListener(frameEventHandler, 'object:state-changed:active')

# frame title changes
reg.registerEventListener(frameEventHandler, 'object:property-change:accessible-name')

# If you detect (event.detail1 == 0) for a 'frame', then that means the
# frame has gone invisible.  This detects SOME cases of when you close a
# window without first putting it in focus (but doesn't work on all apps)
def stateChangedHandler(event):
  # only handle for when object:state-changed:visible is 0 ...
  if event.detail1 == 0:
    frameEventHandler(event)

reg.registerEventListener(stateChangedHandler, 'object:state-changed:visible')


reg.registerEventListener(frameEventHandler, 'window:create')
reg.registerEventListener(frameEventHandler, 'window:minimize')
reg.registerEventListener(frameEventHandler, 'window:maximize')
reg.registerEventListener(frameEventHandler, 'window:restore')



printDesktopState()   # print the initial desktop state


# initialize 'plug-ins'
#XpadTracer.initialize(reg)
ClipboardLogger.initialize(reg)


def goodbye():
  print >> sys.stderr, "GOODBYE from GUItracer.py"
  global cur_fd
  pyatspi.Registry.stop()
  cur_fd.close()
  
  # Tear down 'plug-ins'
  #XpadTracer.teardown()
  ClipboardLogger.teardown()


# We need to make sure signal handlers get set BEFORE the weird pyatspi
# and gobject event-related calls ...
from signal import signal, SIGINT, SIGTERM
import atexit

atexit.register(goodbye)
signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run


# This idiom of gobject.timeout_add, pumpQueuedEvents, and async=True
# was taken from the Accerciser project

def asyncHandler():
  pyatspi.Registry.pumpQueuedEvents()
  return True # so that gobject.timeout_add will keep firing!

gobject.timeout_add(200, asyncHandler)


# being asynchronous is MANDATORY if you want object.timeout_add events to work!
try:
  pyatspi.Registry.start(async=True, gil=False)
except KeyboardInterrupt:
  pass


########NEW FILE########
__FILENAME__ = parse_gui_trace
# Parse the GUI trace log file produced by GUItracer.py

# Pass in the DIRECTORY containing gui.trace.* as sys.argv[1]

import os, json, sys, datetime

# If you want to vary the amount of filtering, you can set the various
# threshold constants later in this file ...

# Optimization passes:
def optimize_gui_trace(input_lst):
  # NOP for an empty list ...
  if not input_lst: return input_lst

  # file format sanity checks:
  assert type(input_lst[0][0]) in (int, long)
  assert input_lst[0][1].__class__ is DesktopState

  l2 = coalesceAndDedup(input_lst)
  l3 = removeInactiveStates(l2)

  return l3

  # TODO: investigate this below ...

  # do another round just for good times (since removeInactiveStates
  # might introduce some new duplicates)
  #l4 = coalesceAndDedup(l3)
  # TODO: I don't know whether this is sufficient, or whether we have to
  # keep running until fixpoint


# A DesktopState is only supposed to have at most ONE active window,
# but sometimes there is some "stickiness" in GUI events, so that there
# will be a DesktopState with TWO active windows.  What happens is that
# a new window will become active, but the old one won't have
# deactivated yet.  So let's correct this dirtiness ...
#
# For every pair of neighboring states (prev, cur), if 'cur' has more
# than one active window, then DEACTIVATE the window in 'cur' that
# matches the sole active window in 'prev'.
#
# Run this pass BEFORE coalesceAndDedup(), since this optimization pass
# might create some duplicates that can be eliminated in coalesceAndDedup()
#
# SUPER GROSS HACK: also pass in prev_final_entry to account for the
# case when the FIRST element of lst has more than one active window,
# in which case we have to consult prev_final_entry for the proper
# window to deactivate in the first element of lst.
def enforceSoloActiveWindow(lst, prev_final_entry):
  ret = []
  cInd = 0

  orig_len = len(lst)

  # ugh this is so ugly ...
  augmented_lst = [prev_final_entry] + lst

  # start counting at 1 since we want to SKIP prev_final_entry
  for cInd in xrange(1, len(augmented_lst)):
    prev = augmented_lst[cInd - 1]
    cur  = augmented_lst[cInd]

    if not prev: # what if we have no prev_final_entry?
      assert cur[1].num_active_windows() <= 1
      ret.append(cur)
    else:
      pState = prev[1]
      cState = cur[1]

      n = cState.num_active_windows()
      assert n <= 2 # there should never be more than 2 active windows!!!

      if n > 1:
        assert n == 2

        pActiveWindowsLst = pState.get_active_windows()

        assert len(pActiveWindowsLst) <= 1
        if len(pActiveWindowsLst) == 1:
          pActiveWindow = pActiveWindowsLst[0]

          # modify cState to DEACTIVATE the window that matches pActiveWindow
          for (appId, a) in cState.appsDict.iteritems():
            for (windowIndex, w) in a.windows.iteritems():
              if w.is_active:
                if (appId, windowIndex) == pActiveWindow:
                  w.is_active = False # MUTATE IT!
        else:
          # pState has no active windows, so punt to the desperation case ...
          pass

        # in the RARE case that we still haven't eliminated multiple
        # windows, then simply issue a warning and just disable one window
        # chosen at 'random' ... this is non-ideal but hopefully should
        # be rare ...
        if cur[1].num_active_windows() > 1:
          activeWindows = cState.get_active_windows()
          assert len(activeWindows) == 2
          (random_a, random_w) = activeWindows[0]
          cState[random_a][random_w].is_active = False
          print >> sys.stderr, "WARNING in enforceSoloActiveWindow: Disabled arbitrary window in DesktopState at timestamp", cur[0]


      ret.append(cur)


  # end-to-end sanity checks ...
  assert len(ret) == orig_len
  for e in ret:
    assert e[1].num_active_windows() <= 1

  return ret


# If two neighboring entries are duplicates of one another, then only
# keep the EARLIER one (since that's when the GUI was FIRST in that state)
#
# Also coalesce entries that occur within 'threshold' milliseconds of one
# another and keep on the LAST one in a streak, to make the output stream
# a bit cleaner.
#
# Oftentimes the GUI generates several events in quick succession,
# and it's only useful to keep the LAST one in a streak.
COALESCE_WINDOW_MS = 500 # half a second seems to work pretty darn well

def coalesceAndDedup(lst):
  ret = []
  pInd = 0
  cInd = 1

  # Make sure that pinned states remain in the final list:
  pinned_elts = [e for e in lst if e[1].pinned]

  # Do the normal coalesce/dedup:
  while cInd < len(lst):
    prev = lst[pInd]
    cur  = lst[cInd]
    deltaTime = cur[0] - prev[0]

    # Dedup: remember, the cadr of the tuple is the payload ...
    if prev[1] == cur[1]:
      # advance cInd to "skip" this entry;
      # we want to keep pInd in the same place to keep the EARLIER one
      cInd += 1
    elif deltaTime >= COALESCE_WINDOW_MS:
      ret.append(prev)
      pInd = cInd
      cInd = pInd + 1
    else:
      pInd += 1
      cInd += 1

  if lst:
    ret.append(lst[-1]) # always append the final entry

  # Put pinned states back in ret
  for p in pinned_elts:
    if p not in ret:
      ret.append(p)

  # sort chronologically again!
  ret.sort(key=lambda e:e[0])

  return ret


# Delete all DesktopState instances without an active window if they're
# followed < N seconds later by a state WITH an active window.
#
# The justification here is that when windows are being moved or
# resized, there is temporarily NO active window for a few seconds,
# and when the move/resize is completed, there's an active window again.
#
# Our current 4-second heuristic seems to work well in practice.
INACTIVE_DEDUP_THRESHOLD_MS = 4000

def removeInactiveStates(lst):
  ret = []
  cInd = 0
  nInd = 1

  while cInd < len(lst):
    cur  = lst[cInd]

    # Remember, the cadr of the tuple is the payload ...
    # make sure not to skip pinned entries!
    if cur[1].num_active_windows() == 0 and (not cur[1].pinned):
      next = None

      # edge case!
      if nInd < len(lst):
        next = lst[nInd]
        deltaTime = next[0] - cur[0]

      if not next or deltaTime > INACTIVE_DEDUP_THRESHOLD_MS:
        ret.append(cur)

      # otherwise SKIP cur
    else:
      ret.append(cur)

    cInd += 1
    nInd += 1

  return ret


# represents the current state of the user's desktop
class DesktopState:
  def __init__(self, dat):
    assert type(dat) is dict
    # Key:   app ID
    # Value: ApplicationState
    self.appsDict = {}
    for (k, v) in dat.iteritems():
      # convert key into an INTEGER since JSON only supports keys of
      # type 'string', but they're conceptually INTEGERS!
      self.appsDict[int(k)] = ApplicationState(v)

    # if this is True, then do NOT optimize this state away,
    # since we probably need to keep it around for cross-reference
    self.pinned = False

  def __eq__(self, other):
    return self.pinned == other.pinned and self.appsDict == other.appsDict

  # serialize for MongoDB; note that we need to add an _id field later
  def serialize(self):
    ret = {}
    ret['apps'] = []

    for (k,v) in self.appsDict.iteritems():
      ret['apps'].append(dict(app_id=k, app=v.serialize()))

    active_windows = self.get_active_windows()
    assert len(active_windows) <= 1
    if len(active_windows) == 1:
      app_id, window_idx = active_windows[0]
      ret['active_app_id'] = app_id
      ret['active_window_index'] = window_idx
    else:
      ret['active_app_id'] = -1
      ret['active_window_index'] = -1

    return ret

  @staticmethod
  def from_mongodb(mongodb_dat):
    ret = DesktopState({}) # start with an empty desktop
    for e in mongodb_dat['apps']:
      ret.appsDict[int(e['app_id'])] = ApplicationState.from_mongodb(e['app'])
    return ret

  def __getitem__(self, i):
    return self.appsDict[i]

  def printMe(self, indent=0):
    if self.pinned:
      print "PINNED!!!"
    for appId in sorted(self.appsDict.keys()):
      self.appsDict[appId].printMe(indent)

  # should normally be 1 ... anything other than 1 is WEIRD!
  def num_active_windows(self):
    n = 0
    for a in self.appsDict.itervalues():
      for w in a.windows.itervalues():
        if w.is_active:
          n += 1
    return n

  # returns a list of pairs (app ID, window index)
  def get_active_windows(self):
    ret = []
    for (appId, a) in self.appsDict.iteritems():
      for (windowIndex, w) in a.windows.iteritems():
        if w.is_active:
          ret.append((appId, windowIndex))

    return ret


  # returns the actual WindowState instance (or None)
  def get_first_active_window(self):
    for (appId, a) in self.appsDict.iteritems():
      for (windowIndex, w) in a.windows.iteritems():
        if w.is_active:
          return w
    return None



class ApplicationState:
  def __init__(self, dat):
    self.name = dat['name']
    w = dat['windows']
    assert type(w) is dict
    self.windows = {}
    for (k,v) in w.iteritems():
      # convert key into an INTEGER since JSON only supports keys of
      # type 'string', but they're conceptually INTEGERS!
      self.windows[int(k)] = WindowState(v)

    # Update with a PID by matching up with the SystemTap logs.
    #
    # For simplicity ...
    # we're assuming here that an 'application' only has one PID;
    # for apps that spawn off multiple processes, try to grab the master
    # controlling process (we can always grab its children later using
    # the process tree)
    self.pid = None


  def __eq__(self, other):
    return (self.name == other.name and \
            self.pid == other.pid and \
            self.windows == other.windows)

  def __str__(self):
    return '%s [PID: %s]' % (self.name, str(self.pid))

  # serialize for MongoDB
  def serialize(self):
    ret = {}
    ret['name'] = self.name
    ret['pid'] = self.pid
    ret['windows'] = []
    for (k,v) in self.windows.iteritems():
      ret['windows'].append(dict(window_index=k, window=v.serialize()))

    return ret

  @staticmethod
  def from_mongodb(mongodb_dat):
    dat = {}
    dat['name'] = mongodb_dat['name']
    dat['windows'] = {}
    for e in mongodb_dat['windows']:
      dat['windows'][e['window_index']] = e['window']

    ret = ApplicationState(dat)  # use the regular ApplicationState constructor
    ret.pid = mongodb_dat['pid'] # don't forget to tack this on!
    return ret

  def __getitem__(self, i):
    return self.windows[i]


  def printMe(self, indent=0):
    print (' ' * indent), self

    for k in sorted(self.windows.keys()):
      self.windows[k].printMe(indent)


class WindowState:
  def __init__(self, dat):
    self.__dict__.update(dat) # 1337 trick!

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  # serialize for MongoDB
  def serialize(self):
    return self.__dict__

  def printMe(self, indent=0):
    print ' ' * indent,
    if self.is_active:
      print '*',
    elif self.is_minimized:
      print 'm',
    else:
      print ' ',

    print self.title, '| (%d,%d) [%dx%d]' % (self.x, self.y, self.width, self.height)
    if hasattr(self, 'browserURL'):
      print (' ' * indent), '   URL:', self.browserURL


# Generate entries one at a time from the file named 'fn'
def gen_gui_entries_from_file(fn):
  print >> sys.stderr, "gen_gui_entries_from_file('%s')" % (fn,)
  for line in open(fn):
    data = json.loads(line) # each line must be valid JSON!
    yield data


def gen_gui_entries_from_dir(dn):
  log_files = [e for e in os.listdir(dn) if e.startswith('gui.trace')]

  # go through log_files in CHRONOLOGIAL order, which isn't the same as
  # an alphabetical sort by name.  e.g., we want "gui.trace.out.2" to
  # come BEFORE "gui.trace.out.10", but if we alphabetically sort, then
  # "gui.trace.out.10" will come first!
  for i in range(len(log_files)):
    cur_fn = 'gui.trace.' + str(i)
    assert cur_fn in log_files, cur_fn
    fullpath = os.path.join(dn, cur_fn)

    for entry in gen_gui_entries_from_file(fullpath):
      yield entry


# lst should be a list of (timestamp, DesktopState) pairs:
def interactive_print(lst):
  idx = 0
  while True:
    (t, s) = lst[idx]

    for i in range(100): print
    print "%d / %d" % (idx + 1, len(lst)), datetime.datetime.fromtimestamp(float(t) / 1000), t
    print
    s.printMe()
    print
    print "Next state: <Enter>"
    print "Prev state: 'p'+<Enter>"
    print "Next PINNED state: 'a'+<Enter>"
    print "Jump: <state number>'+<Enter>"

    k = raw_input()
    if k == 'p':
      if idx > 0:
        idx -= 1
    elif k == 'a':
      idx += 1
      while True:
        (t, s) = lst[idx]
        if not s.pinned:
          idx += 1
        else:
          break
    else:
      try:
        jmpIdx = int(k)
        if 0 <= jmpIdx < len(lst):
          idx = (jmpIdx - 1)
      except ValueError:
        if idx < len(lst) - 1:
          idx += 1


def print_window_diff(old, new, app_name, print_inactive=False):
  diffstrs = []
  if old.is_active != new.is_active:
    if new.is_active:
      diffstrs.append('went active')

    # don't print when a window goes INACTIVE unless there are NO active
    # windows anywhere throughout the entire DesktopState
    # (otherwise it's redundant since SOME other window is going active)
    elif old.is_active and print_inactive:
      diffstrs.append('went inactive')

  if old.is_minimized != new.is_minimized:
    if new.is_minimized:
      diffstrs.append('minimized')
    else:
      diffstrs.append('un-minimized')

  if old.title != new.title:
    diffstrs.append('title changed from "%s"' % (old.title,))

  if (old.x, old.y) != (new.x, new.y):
    diffstrs.append('moved (%d,%d) -> (%d,%d)' % (old.x, old.y, new.x, new.y))

  if (old.width, old.height) != (new.width, new.height):
    diffstrs.append('resized [%dx%d] -> [%dx%d]' % (old.width, old.height, new.width, new.height))

  # awkward!
  if hasattr(old, 'browserURL') and hasattr(new, 'browserURL'):
    if old.browserURL != new.browserURL:
      diffstrs.append('URL changed to "%s"' % (new.browserURL,))

  if diffstrs:
    print app_name, ': "%s"' % (new.title,),
    print ', '.join(diffstrs)


def print_app_diff(old, new, print_inactive_window=False):
  old_windowIdxs = set(old.windows.keys())
  new_windowIdxs = set(new.windows.keys())

  added_windowIdxs = new_windowIdxs - old_windowIdxs
  if added_windowIdxs:
    for w in new_windowIdxs:
      print new.name, "created window:",
      new.windows[w].printMe()

  deleted_windowIdxs = old_windowIdxs - new_windowIdxs
  if deleted_windowIdxs:
    for w in deleted_windowIdxs:
      print old.name, "deleted window:",
      old.windows[w].printMe()
 
  # now diff the windows in common:
  for w in old_windowIdxs.intersection(new_windowIdxs):
    print_window_diff(old.windows[w], new.windows[w], new.name, print_inactive_window)


# Pretty-print a diff of two DesktopState instances
def print_desktop_diff(old, new):
  old_appIDs = set(old.appsDict.keys())
  new_appIDs = set(new.appsDict.keys())

  added_appIDs = new_appIDs - old_appIDs
  if added_appIDs:
    print "New application:"
    for a in added_appIDs:
      new.appsDict[a].printMe(2)

  deleted_appIDs = old_appIDs - new_appIDs
  if deleted_appIDs:
    print "Deleted application:"
    for a in deleted_appIDs:
      print '  ', old.appsDict[a]


  new_has_no_active_windows = (new.num_active_windows() == 0)

  # now diff the apps that are in common ...
  for a in old_appIDs.intersection(new_appIDs):
    print_app_diff(old.appsDict[a], new.appsDict[a], new_has_no_active_windows)


########NEW FILE########
__FILENAME__ = XpadTracer
# 'xpad' tracing module for GUItracer.py
# 2011-11-20

# To track xpad history, first install it and then uncomment the
# XpadTracer lines in GUItracer.py
#
#   Install xpad sticky notes app
#     sudo yum install xpad
# 
#   Now add 'xpad' to your GNOME Startup Applications panel
#   (System -> Preferences -> Startup Applications), so that it
#   always runs on start-up.


import os, gobject
from BurritoUtils import *


XPAD_DATA_DIR = os.path.join(os.getenv("HOME"), ".config/xpad/")

last_xpad_event_timestamp = 0
POLLING_INTERVAL_MS = 15000

outf = None


def xpad_text_changed(event):
  if not event: return
  if not event.host_application: return
  if event.host_application.name != 'xpad': return # VERY IMPORTANT!
  global last_xpad_event_timestamp
  last_xpad_event_timestamp = get_ms_since_epoch()


def save_xpad_buffers(t):
  # the xpad raw data files are saved in $HOME/.config/xpad/content-*
  xpad_data_files = [e for e in os.listdir(XPAD_DATA_DIR) if e.startswith('content-')]

  result = {}
  result['timestamp'] = t
  for f in xpad_data_files:
    path = os.path.join(XPAD_DATA_DIR, f)
    result[f] = open(path).read()

  compactJSON = to_compact_json(result)

  #print "SAVE", t
  global outf
  print >> outf, compactJSON
  outf.flush() # don't forget!


def poll_for_xpad_change():
  global last_xpad_event_timestamp
  t = get_ms_since_epoch()

  delta = (t - last_xpad_event_timestamp)

  #print "POLL", t
  if delta < POLLING_INTERVAL_MS:
    save_xpad_buffers(last_xpad_event_timestamp) # save the last typed timestamp!

  return True # so that gobject.timeout_add will keep firing!


def initialize(reg):
  global outf
  outf = open('/var/log/burrito/current-session/xpad-notes.log', 'w')

  save_xpad_buffers(get_ms_since_epoch()) # do a save of the initial start-up state
  reg.registerEventListener(xpad_text_changed, 'object:text-changed')
  gobject.timeout_add(POLLING_INTERVAL_MS, poll_for_xpad_change)

def teardown():
  poll_for_xpad_change() # do one final check

  global outf
  outf.close()


########NEW FILE########
__FILENAME__ = incremental_integrator
# Integrate all burrito data streams into a centralized MongoDB database
# Created: 2011-11-25

# This process is meant to be run continuously in the background, doing
# incremental indexing approximately every INDEXING_PERIOD_SEC seconds.
# It is a SINGLE-THREADED process, so it will complete one full round of
# incremental indexing, pause for INDEXING_PERIOD_SEC, and then resume
# the next round.  It will run exit_handler() when gracefully killed.

# Note that you can also run this script on an archival dataset (that's
# no longer changing), and it will still work fine.

# TODO: Monitor error output and think about how to make this script
# more failure-oblivious, since we want it to always run in the
# background throughout the duration of the user's session.

'''
Collections within MongoDB burrito_db:

burrito_db.process_trace
  - contains the cleaned output from pass-lite.out.*
  - _id is a concatenation of creation timestamp and PID
  - most_recent_event_timestamp is the most recent time that this
    process entry was updated

burrito_db.gui_trace
  - contains the cleaned output from gui.trace.*,
    integrated with PID information from burrito_db.process_trace
  - _id is the unique timestamp of the GUI event

burrito_db.clipboard_trace
  - contains information about X Window copy/paste events. Fields:
    - contents:       string contents of clipboard
    - copy_time:      datetime of copy event (not necessarily unique
                      since there can be multiple pastes for one copy)
    - _id:            datetime of paste event (should be unique primary key)
    - src_desktop_id: key of source desktop state in burrito_db.gui_trace
    - dst_desktop_id: key of destination desktop state in burrito_db.gui_trace


burrito_db.apps.xpad
burrito_db.apps.vim
burrito_db.apps.bash
burrito_db.apps.chrome
burrito_db.apps.evince
burrito_db.apps.pidgin
  etc. etc. etc.
  - custom logs for individual apps that plug into burrito
  - all logs are indexed by the 'timestamp' field by default (i.e.,
    convert it to a Python datetime and set it as a unique '_id' field
    for MongoDB)

burrito_db.session_status
  - _id:               unique session tag (e.g., sub-directory name within
                       /var/log/burrito)
  - last_updated_time: timestamp of last update to this session

'''

INDEXING_PERIOD_SEC = 10
#INDEXING_PERIOD_SEC = 30


import os, sys, time, optparse
from signal import signal, SIGTERM
from sys import exit
import atexit

import GUItracing
import SystemTap
from SystemTap import Process, parse_raw_pass_lite_line
from BurritoUtils import *

from pymongo import Connection, ASCENDING


# for gen_entries_from_multifile_log
gui_trace_parser_state = {'file_prefix': 'gui.trace.',
                          'callback': json.loads,
                          'cur_file_index': 0, 'cur_line' : 0}

pass_lite_parser_state = {'file_prefix': 'pass-lite.out.',
                          'callback': parse_raw_pass_lite_line,
                          'cur_file_index': 0, 'cur_line' : 0}


# for gen_entries_from_json_log, using json.loads() to parse each line
clipboard_json_parser_state = {'filename': 'clipboard.log', 'cur_line': 0}
bash_json_parser_state      = {'filename': 'bash-history.log', 'cur_line': 0}
vim_json_parser_state       = {'filename': 'vim-trace.log', 'cur_line': 0}
xpad_json_parser_state      = {'filename': 'xpad-notes.log', 'cur_line': 0}


# In our current 'epoch' of indexing, we only snapshot the contents of
# all logs that occurred STRICTLY BEFORE this timestamp
cur_epoch_timestamp  = 0
prev_epoch_timestamp = 0

# The FINAL DesktopState object from the previous epoch, which is
# necessary for detecting copy-and-paste events.
prev_epoch_final_gui_state = None # type is (timestamp, DesktopState)


# GUI states that are the source of clipboard copy events
#
# Key: timestamp of COPY event
# Value: (timestamp of DesktopState, DesktopState)
clipboard_copy_gui_states = {}


# Dict mapping PIDs to active processes (i.e., haven't yet exited)
# Key: PID
# Value: Process object
pid_to_active_processes = {}

# the PARENT pids of all exited processes
exited_process_ppids = set()


# Use time proximity and name heuristics to try to find the PID that
# matches a particular app name and window creation event timestamp
#
# 8 seconds might seem like a LONG time, but sometimes when I launch
# Google Chrome for the first time, it takes up to 6 seconds to start up
# in my slow-ass VM.  Of course, the longer you wait, the greater chance
# you have of false positives creeping up, so be somewhat cautious!
EXECVE_TO_WINDOW_APPEAR_THRESHOLD_MS = 8000

# Each element is an '_id' field from an entry in the MongoDB proc_col
# collection that's already been matched against a GUI element.  This is
# important for implementing "first-come, first-served" behavior for apps
# like 'evince' which launch multiple processes in rapid succession.
# i.e., the first window gets the earliest-execve'd process, etc.
#
# This set is VERY IMPORTANT because without it, if you execve multiple
# identically-named processes (e.g., evince) within a time span of
# EXECVE_TO_WINDOW_APPEAR_THRESHOLD_MS, then there's a chance that all
# of the windows will match up against the PID of the first-launched
# process.  This way, the first window to appear matches up against the
# first-launched PID, the second with the second, etc.
#
# This correspondence is correct assuming that process execve order
# corresponds to GUI window creation order, which is a reasonable
# (although not perfect) assumption.
already_matched_processes = set()


# Keep an ongoing record of which GUI apps are matched with which PIDs,
# and also the 'end times' of those processes, so that we know when to
# 'expire' the matches ...
#
# Note that this global dict persists across multiple calls to
# incremental_index_gui_trace_logs ...
#
# Key: (app ID, app name)
# Value: (matched PID, end time of matched process as a datetime object)
currently_matched_apps = {}


in_critical_section = False # crude "lock"


# also adds session tag!
def save_tagged_db_entry(col, json_entry):
  global session_tag
  json_entry['session_tag'] = session_tag
  col.save(json_entry) # does an insert (if not-exist) or update (if exists)


# Parse one line at a time, and as a side effect, update parser_state so
# that we can know where we've parsed up to, so that we can resume where
# we left off during the next round of processing.
def gen_entries_from_multifile_log(parser_state, max_timestamp):
  global logdir
  print "gen_entries_from_multifile_log {"

  callback = parser_state['callback']

  while True:
    filename = parser_state['file_prefix'] + str(parser_state['cur_file_index'])
    fullpath = os.path.join(logdir, filename)

    if not os.path.isfile(fullpath):
      # PUNT EARLY!
      print >> sys.stderr, "WARNING: skipping non-existent file '%s'" % (fullpath,)
      return

    f = open(fullpath)

    print "  Processing", fullpath, "at line", parser_state['cur_line']

    for (line_no, line) in enumerate(f):
      # skip directly to cur_line
      if line_no < parser_state['cur_line']:
        continue

      # If any parse error occurs, just straight-up QUIT and wait until
      # the next round of indexing when hopefully the file's contents will
      # be more intact.  In rare cases, our loggers out partial lines
      # to the output file, despite printf newline buffering.
      try:
        entry = callback(line.rstrip())
        # don't parse entries greater than current timestamp

        # each entry should either have an attribute named timestamp or
        # a dict key named 'timestamp'

        entry_timestamp = None
        if hasattr(entry, 'timestamp'):
          entry_timestamp = entry.timestamp
        else:
          entry_timestamp = entry['timestamp']
        assert type(entry_timestamp) in (int, long)
        if entry_timestamp >= max_timestamp:
          print "} max_timestamp reached (file index: %d, line: %d)" % (parser_state['cur_file_index'], parser_state['cur_line'])
          return

        yield entry
      except:
        # failure oblivious, baby!
        print >> sys.stderr, "WARNING: skipping line %d in %s due to uncaught exception" % (line_no, fullpath)
        pass

      parser_state['cur_line'] = line_no + 1

    f.close()

    # ok, so if the NEXT sequentially-higher log file actually exists,
    # then move onto processing it.  but if it doesn't exist, then keep
    # the counter at THIS file and simply return.
    next_file = parser_state['file_prefix'] + str(parser_state['cur_file_index'] + 1)
    if os.path.isfile(os.path.join(logdir, next_file)):
      parser_state['cur_file_index'] += 1
      parser_state['cur_line'] = 0
    else:
      print "} file ended (file index: %d, line: %d)" % (parser_state['cur_file_index'], parser_state['cur_line'])
      return

  assert False


# Parse one line at a time using json.loads, and as a side effect,
# update parser_state so that we can know where we've parsed up to, so
# that we can resume where we left off during the next round of
# processing.
def gen_entries_from_json_log(parser_state, max_timestamp):
  global logdir
  print "gen_entries_from_json_log {"

  fullpath = os.path.join(logdir, parser_state['filename'])
  if not os.path.isfile(fullpath):
    print "} file", fullpath, "doesn't exist"
    return

  f = open(fullpath)

  print "  Processing", fullpath, "at line", parser_state['cur_line']

  for (line_no, line) in enumerate(f):
    # skip directly to cur_line
    if line_no < parser_state['cur_line']:
      continue

    # If any parse error occurs, just straight-up QUIT and wait until
    # the next round of indexing when hopefully the file's contents will
    # be more intact.  In rare cases, our loggers out partial lines
    # to the output file, despite printf newline buffering.
    try:
      entry = json.loads(line.rstrip())

      # don't parse entries greater than current timestamp
      # each entry should either have a dict key named 'timestamp'

      entry_timestamp = entry['timestamp']
      assert type(entry_timestamp) in (int, long)
      if entry_timestamp >= max_timestamp:
        print "} max_timestamp reached (line: %d)" % (parser_state['cur_line'],)
        return

      yield entry
    except:
      f.close()
      print "} exception (line: %d)" % (parser_state['cur_line'],)
      return

    parser_state['cur_line'] = line_no + 1


  f.close()
  print "} file ended (line: %d)" % (parser_state['cur_line'],)


# This function runs when the process is killed by civilized means
# (i.e., not "kill -9")
def exit_handler():
  global session_status_col
  cur_time = get_ms_since_epoch()
  print >> sys.stderr, "GOODBYE incremental_integrator.py: in_critical_section =", in_critical_section, ", time:", cur_time
  session_status_col.save({'_id': session_tag, 'last_updated_time': datetime.datetime.now()})

  # Since this call is asynchronous, we might be in the midst of
  # executing a critical section.  In this case, just don't do anything
  # to rock the boat :)  Since MongoDB doesn't have traditional db
  # transactions, our db still might not be in a great state, but it's
  # better than us mucking more with it!!!
  if not in_critical_section:
    do_incremental_index() # go for one last hurrah!

    # now make all active processes into exited processes since our
    # session has ended!
    for p in pid_to_active_processes.values():
      p.mark_exit(cur_time, -1) # use a -1 exit code to mark that it was "rudely" killed :)
      handle_process_exit_event(p)


### pass-lite logs ###

def handle_process_exit_event(p):
  global pid_to_active_processes, exited_process_ppids, proc_col

  assert p.exited

  del pid_to_active_processes[p.pid]
  proc_col.remove({'_id': p.unique_id()}) # remove and later (maybe) re-insert

  skip_me = False

  # Optimization: if this process is 'empty' (i.e., has no phases)
  # and isn't the parent of any previously-exited process or
  # currently-active process, then there is NO POINT in storing it
  # into the database.
  if (not p.phases):
    active_process_ppids = set()
    for p in pid_to_active_processes.itervalues():
      active_process_ppids.add(p.ppid)
    if (p.pid not in exited_process_ppids) and (p.pid not in active_process_ppids):
      skip_me = True

  if not skip_me:
    save_tagged_db_entry(proc_col, p.serialize())
    exited_process_ppids.add(p.ppid)


def incremental_index_pass_lite_logs():
  global proc_col, cur_epoch_timestamp, prev_epoch_timestamp, pid_to_active_processes

  for pl_entry in gen_entries_from_multifile_log(pass_lite_parser_state, cur_epoch_timestamp):
    if pl_entry.pid not in pid_to_active_processes:
      # remember, creating a new process adds it to
      # the pid_to_active_processes dict (weird, I know!)
      p = Process(pl_entry.pid, pl_entry.ppid, pl_entry.uid, pl_entry.timestamp, pid_to_active_processes)
      assert pid_to_active_processes[pl_entry.pid] == p # sanity check
    else:
      p = pid_to_active_processes[pl_entry.pid]

    is_exited = p.add_entry(pl_entry)

    if is_exited:
      handle_process_exit_event(p)


  # Optimization: don't bother updating the database with info for
  # active processes that haven't changed since the previous indexing
  # epoch, since their data will be identical ...
  changed_active_processes = []
  for p in pid_to_active_processes.itervalues():
    if p.most_recent_event_timestamp >= prev_epoch_timestamp:
      changed_active_processes.append(p)

  for p in changed_active_processes:
    save_tagged_db_entry(proc_col, p.serialize())

  print "=== %d active procs (%d changed) ===" % (len(pid_to_active_processes), len(changed_active_processes))


### GUI tracer logs ###

def match_gui_proc_name(gui_app_name, process_name):
  # WTF in the ultimate form of dumbassery, the SystemTap execname()
  # function seems to only return the first 15 characters of a process
  # name.  It seems like the 15-character limit is in /proc/<pid>/status
  #   http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=513460
  #   http://blogs.oracle.com/bnitz/entry/dtrace_and_process_names
  #
  # e.g., a process named "gnome-system-monitor" will show up with
  #   gui_app_name = "gnome-system-monitor"
  #   process_name = "gnome-system-mo"
  #
  # the best we can do is to do a prefix match for such names ...
  if len(process_name) == 15:
    return gui_app_name.startswith(process_name)
  else:
    # normal case
    return gui_app_name == process_name

  # Ha, seems like there's no more need for this special-case hack for #
  # now ...
  #
  # This still isn't satisfying, though, since the google-chrome process
  # sometimes DIES while chrome is still running ... ugh
  #if gui_app_name == 'google-chrome':
  #  return process_name == 'chrome'
  #else:
  #  return gui_app_name == process_name


# returns either None or a pair of (PID, process exit_time)
def find_PID_and_endtime(gui_app_name, window_create_timestamp):
  global proc_col, already_matched_processes, EXECVE_TO_WINDOW_APPEAR_THRESHOLD_MS

  lower_bound = encode_datetime(window_create_timestamp - EXECVE_TO_WINDOW_APPEAR_THRESHOLD_MS)
  upper_bound = encode_datetime(window_create_timestamp)

  # match then sort chronologically by process phase start_time to get
  # the EARLIEST process first:
  matches = proc_col.find({"phases.start_time":{"$gt":lower_bound, "$lt":upper_bound}}, {"phases.name":1, "pid":1, "exit_time":1}).sort("phases.start_time", ASCENDING)

  #print >> sys.stderr, "find_PID_and_endtime:", gui_app_name, lower_bound, upper_bound
  for m in matches:
    #print >> sys.stderr, ' candidate:', m

    # if the process CROAKED before your window was even created, then
    # obviously skip it!
    if m['exit_time'] and m['exit_time'] < upper_bound:
      continue

    phase_lst = m['phases']
    for p in phase_lst:
      proc_name = p['name']
      if proc_name:
        # note that already_matched_processes implements "first-come,
        # first-served" behavior for apps like 'evince' which launch
        # multiple processes in succession.  i.e., the first window gets
        # the earliest-execve'd process, etc.
        # (if we don't use this, then BOTH evince windows will get
        # associated to the FIRST-launched 'evince. process.)
        if match_gui_proc_name(gui_app_name, proc_name) and (m['_id'] not in already_matched_processes):
          already_matched_processes.add(m['_id'])
          #print >> sys.stderr, '   MATCH:', proc_name, m['pid'], m['exit_time']
          assert m['pid'] > 0
          return (m['pid'], m['exit_time'])

  return None


def incremental_index_gui_trace_logs():
  global gui_col, prev_epoch_timestamp, cur_epoch_timestamp, currently_matched_apps, prev_epoch_final_gui_state

  # each element is a pair of (timestamp, DesktopState)
  # that falls between prev_epoch_timestamp and cur_epoch_timestamp
  timesAndStates = []


  # return the (timestamp, DesktopState) within timesAndStates
  # corresponding to the most recent entry whose timestamp <= target_time
  def get_gui_state_at_time(target_time):
    if not len(timesAndStates) or target_time < timesAndStates[0][0]:
      # crap, we've got no new GUI states in this epoch, so let's rely on prev_epoch_final_gui_state
      assert prev_epoch_final_gui_state
      assert prev_epoch_final_gui_state[0] <= target_time # TODO: this assertion sometimes fails :(
      return prev_epoch_final_gui_state
    else:
      assert target_time >= timesAndStates[0][0] # boundary condition

      for ((prev_t, prev_state), (cur_t, cur_state)) in zip(timesAndStates, timesAndStates[1:]):
        assert prev_t <= cur_t # sanity check

        # use a half-open interval, preferring the PAST
        if prev_t <= target_time < cur_t:
          return (prev_t, prev_state)

      # check the FINAL entry if there's no match yet:
      final_time, final_state = timesAndStates[-1]
      assert target_time >= final_time
      return timesAndStates[-1]


  for data in gen_entries_from_multifile_log(gui_trace_parser_state, cur_epoch_timestamp):
    timestamp = data['timestamp']

    # in RARE cases, GUI log entries come in out of time order, which is
    # really really bizarre ... so the best we can do now is to DROP
    # those entries and issue a warning
    if timesAndStates and (timestamp < timesAndStates[-1][0]):
      print >> sys.stderr, "WARNING: GUI trace entry is not in chronological order, so skipping"
      print >> sys.stderr, "(its timestamp [%d] is less than the prev. timestamp [%d])" % (timestamp, timesAndStates[-1][0])
      print >> sys.stderr, data
      print >> sys.stderr
      continue


    assert prev_epoch_timestamp <= timestamp < cur_epoch_timestamp # sanity check! # TODO: this assertion sometimes fails :(

    timestamp_dt = encode_datetime(timestamp)
    dt = GUItracing.DesktopState(data['desktop_state'])

    timesAndStates.append((timestamp, dt))


    # first fill in PID fields from currently_matched_apps
    for (appId, app) in dt.appsDict.iteritems():
      k = (appId, app.name)
      if k in currently_matched_apps:
        matched_PID, matched_proc_end_dt = currently_matched_apps[k]
        # this entry has expired, so get rid of it!!!
        if matched_proc_end_dt and matched_proc_end_dt < timestamp_dt:
          #print >> sys.stderr, "DELETE:", k
          del currently_matched_apps[k]
        else:
          app.pid = matched_PID # set it!
          #print >> sys.stderr, "Set", app.name, "to pid", app.pid

    # Try to find a PID match for a window creation event ...
    if 'event_type' in data and data['event_type'] == 'window:create':
      t        = data['timestamp']
      appId    = data['src_app_id']
      frameIdx = data['src_frame_index']

      assert type(t) in (int, long)
      assert type(appId) is int
      assert type(frameIdx) is int

      app = dt.appsDict[appId]

      if not app.pid: # don't DOUBLE-SET the pid field!
        ret = find_PID_and_endtime(app.name, t)
        if ret:
          pid, _ = ret
          app.pid = pid
          currently_matched_apps[(appId, app.name)] = ret
          #print >> sys.stderr, "INSERT:", (appId, app.name), "->", ret


  # This is an important step that must be run BEFORE doing copy-paste
  # event detection, since that stage assumes that there is at most one
  # active window at copy/paste time ...
  timesAndStates = GUItracing.enforceSoloActiveWindow(timesAndStates, prev_epoch_final_gui_state)


  # Incrementally process the clipboard log ...
  # (do this BEFORE optimizing timesAndStates, since we don't want the
  # states disappearing)
  for data in gen_entries_from_json_log(clipboard_json_parser_state, cur_epoch_timestamp):
    event_timestamp = data['timestamp']

    (desktop_state_timestamp, desktop_state) = get_gui_state_at_time(event_timestamp)
    assert desktop_state_timestamp <= event_timestamp

    # first pin the appropriate desktop_state instance so that it
    # doesn't get optimized away (and actually gets stored to the db)
    desktop_state.pinned = True


    global clipboard_copy_gui_states
    if data['event_type'] == 'copy':
      # remember that the key is the COPY EVENT's timestamp!!!
      clipboard_copy_gui_states[event_timestamp] = (desktop_state_timestamp, desktop_state)
    else:
      assert data['event_type'] == 'paste'

      copy_time_ms  = data['copy_time_ms']
      paste_x       = data['x']
      paste_y       = data['y']

      (src_desktop_timestamp, src_desktop_state) = clipboard_copy_gui_states[copy_time_ms]

      try:
        assert src_desktop_state.num_active_windows() == 1
        assert desktop_state.num_active_windows() == 1

        # Bounds-check the x & y coordinates with paste_window ...
        paste_window = desktop_state.get_first_active_window()
        assert paste_window.x <= paste_x <= (paste_window.x + paste_window.width)
        assert paste_window.y <= paste_y <= (paste_window.y + paste_window.height)
      except AssertionError:
        print >> sys.stderr, "AssertionError when processing copy/paste event:", data
        continue # be failure-oblivious


      serialized_state = {}
      serialized_state['copy_time'] = encode_datetime(copy_time_ms)
      serialized_state['_id'] = encode_datetime(event_timestamp) # unique primary key
      serialized_state['src_desktop_id'] = encode_datetime(src_desktop_timestamp)
      serialized_state['dst_desktop_id'] = encode_datetime(desktop_state_timestamp)
      serialized_state['contents'] = data['contents']

      # yet more sanity checks ...
      assert serialized_state['src_desktop_id'] <= serialized_state['copy_time']
      assert serialized_state['dst_desktop_id'] <= serialized_state['_id']

      save_tagged_db_entry(clipboard_col, serialized_state)
      #print "  Added copy/paste event:", serialized_state['src_desktop_id'], ',', serialized_state['dst_desktop_id']


  # confirm that all timestamps are UNIQUE, so they can be used as
  # unique MongoDB keys (i.e., '_id' field)
  uniqueTimes = set(e[0] for e in timesAndStates)
  assert len(uniqueTimes) == len(timesAndStates)

  # pin the final entry so that it doesn't get optimized away; we might
  # need it for copy-and-paste detection during the next iteration
  if len(timesAndStates):
    timesAndStates[-1][1].pinned = True
    prev_epoch_final_gui_state = timesAndStates[-1]


  # As a FINAL step, optimize timesAndStates to cut down on noise ...
  #
  # Note that we have to do clipboard entry matching BEFORE we optimize
  # the trace, or else the matching GUI states might be optimized away
  timesAndStates = GUItracing.optimize_gui_trace(timesAndStates)

  if len(timesAndStates):
    assert timesAndStates[-1] == prev_epoch_final_gui_state

  for (t, s) in timesAndStates:
    serialized_state = s.serialize()
    serialized_state['_id'] = encode_datetime(t) # unique!
    save_tagged_db_entry(gui_col, serialized_state)

  if len(timesAndStates):
    print "=== Added %d GUI trace entries ===" % (len(timesAndStates))



# use the 'timestamp' field as the unique MongoDB '_id' (after
# converting to datetime)
def incremental_index_app_plugin(parser_state, db_cursor):
  global cur_epoch_timestamp
  for json_data in gen_entries_from_json_log(parser_state, cur_epoch_timestamp):
    json_data['_id'] = encode_datetime(json_data['timestamp']) # convert to datetime object!
    del json_data['timestamp']
    save_tagged_db_entry(db_cursor, json_data)


def do_incremental_index():
  global cur_epoch_timestamp, prev_epoch_timestamp
  cur_epoch_timestamp = get_ms_since_epoch()

  # process the pass-lite logs BEFORE GUI logs, since we want to
  # integrate the latest data from pass-lite logs into the GUI stream
  # to find desktop app PIDs

  incremental_index_pass_lite_logs()
  incremental_index_gui_trace_logs()

  # do incremental parsing for custom apps:
  incremental_index_app_plugin(vim_json_parser_state, vim_col)
  incremental_index_app_plugin(bash_json_parser_state, bash_col)
  incremental_index_app_plugin(xpad_json_parser_state, xpad_col)

  session_status_col.save({'_id': session_tag, 'last_updated_time': encode_datetime(cur_epoch_timestamp)})
  prev_epoch_timestamp = cur_epoch_timestamp


if __name__ == "__main__":
  parser = optparse.OptionParser()

  parser.add_option("-s", "--session", dest="session_tag",
                    help="Session tag")
  parser.add_option("-d", "--delete-session", dest="delete_session",
                    action="store_true",
                    help="Remove all db entries for session")
  parser.add_option("-o", "--one-shot", dest="one_shot",
                    action="store_true",
                    help="Run only one full round of indexing and then exit")

  (options, args) = parser.parse_args()

  logdir = args[0]
  assert os.path.isdir(logdir)

  # Unique tag name for this session.  Usually set this to the
  # sub-directory name of this session within /var/log/burrito
  #
  # This tag comes in handy both for discovering the origin of some
  # document in the database and also for bulk-clearing all the documents
  # matching a particular session tag.
  session_tag = options.session_tag
  assert session_tag


  # Setup MongoDB stuff:
  c = Connection()
  db = c.burrito_db

  proc_col = db.process_trace
  gui_col = db.gui_trace
  clipboard_col = db.clipboard_trace
  xpad_col = db.apps.xpad
  vim_col = db.apps.vim
  bash_col = db.apps.bash
  session_status_col = db.session_status

  all_cols = [proc_col, gui_col, clipboard_col, xpad_col, vim_col, bash_col]

  # First clear all entries matching session_tag:
  for c in all_cols:
    c.remove({"session_tag": session_tag})
  session_status_col.remove({"_id": session_tag})

  if options.delete_session:
    print "Done deleting session named '%s'" % (session_tag,)
    sys.exit(0)


  # Create indices

  # TODO: I don't know whether it's wasteful or dumb to KEEP creating
  # these indices every time you start up the connection ...
  proc_col.ensure_index('pid')
  proc_col.ensure_index('exited')
  proc_col.ensure_index('most_recent_event_timestamp')

  # For time range searches!  This multi-key index ensures fast
  # searches for creation_time alone too!
  proc_col.ensure_index([('creation_time', ASCENDING), ('exit_time', ASCENDING)])

  proc_col.ensure_index('phases.name')
  proc_col.ensure_index('phases.start_time')
  proc_col.ensure_index('phases.files_read.timestamp')
  proc_col.ensure_index('phases.files_written.timestamp')
  proc_col.ensure_index('phases.files_renamed.timestamp')

  # index all collections by session_tag:
  for c in all_cols:
    c.ensure_index('session_tag')


  # one-shot mode is useful for debugging or running on archival logs
  if options.one_shot:
    do_incremental_index()
    sys.exit(0)


  atexit.register(exit_handler)
  signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run

  # this loop can only be interrupted by exit_handler()
  while True:
    # sleep first so that we can give the logs some time to build up at
    # the beginning of a login session ...
    time.sleep(INDEXING_PERIOD_SEC)
    in_critical_section = True
    do_incremental_index()
    in_critical_section = False


########NEW FILE########
__FILENAME__ = launch_activity_feed
#!/usr/bin/env python

# Make this executable and use this to launch the Activity Feed
import os
os.chdir('/home/researcher/burrito/post-integration/burrito-feed/')
os.system('python burrito_feed.py')


########NEW FILE########
__FILENAME__ = chcp_ss_all
# Change all checkpoints into snapshots

# (this takes quite a while to run, so hopefully we only need to do it once)
import commands, sys

MAX_INDEX = 159496 # maximum index we're using in our USENIX experiments

for i in range(1, MAX_INDEX+1):
  (status, output) = commands.getstatusoutput('sudo chcp ss %d' % i)
  if i % 1000 == 0:
    print i


########NEW FILE########
__FILENAME__ = diff_snapshots
# Parses snapshot summary pickle files in SNAPSHOT_DIR

import os, cPickle

SNAPSHOT_DIR = '/tmp/nilfs-snapshots/pickles-backup/'

MIN_INDEX = 21     # the first snapshot where shit doesn't appear whacked
MAX_INDEX = 159496 # maximum index we're using in our USENIX experiments


# Returns a dict with:
#   'only_left':  list of files that are only in left
#   'only_right': list of files that are only in right
#   'diffs':      list of files that differed between left and right
def diff_snapshots(idx1, idx2):
  ret = {}

  pickle1 = SNAPSHOT_DIR + str(idx1) + '.pickle'
  pickle2 = SNAPSHOT_DIR + str(idx2) + '.pickle'

  assert os.path.isfile(pickle1)
  assert os.path.isfile(pickle2)

  snapshot1 = cPickle.load(open(pickle1))
  snapshot2 = cPickle.load(open(pickle2))

  # sanity checks
  assert snapshot1['index'] == idx1
  assert snapshot2['index'] == idx2

  snapshot1_files = set(snapshot1['files'].iterkeys())
  snapshot2_files = set(snapshot2['files'].iterkeys())

  only_in_1 = snapshot1_files - snapshot2_files
  ret['only_left'] = sorted(only_in_1)

  only_in_2 = snapshot2_files - snapshot1_files
  ret['only_right'] = sorted(only_in_2)

  ret['diffs'] = []

  # check files in common for diffs based on md5 checksum:
  for f in snapshot1_files.intersection(snapshot2_files):
    if snapshot1['files'][f] != snapshot2['files'][f]:
      ret['diffs'].append(f)
  
  return ret


# return the files changed that AREN'T part of dot directories and
# aren't dotfiles
def non_dotfiles_changed(diff_dict):
  ret = []
  for f in (diff_dict['only_left'] + diff_dict['only_right'] + diff_dict['diffs']):
    # dot directory!!!
    if f.startswith('.'): continue

    bn = os.path.basename(f)
    if bn.startswith('.'): continue

    ret.append(f)

  return ret


for i in range(MIN_INDEX, MAX_INDEX+1):
  diffs = diff_snapshots(i, i+1)
  real_diffs = non_dotfiles_changed(diffs)
  if len(real_diffs):
    print i+1


########NEW FILE########
__FILENAME__ = print_snapshot_stats
# print stats for the current snapshot

# assumes that chcp_ss_all.py has already been run

MIN_INDEX = 6      # the first snapshot where "/home/researcher" exists
MAX_INDEX = 159496 # maximum index we're using in our USENIX experiments

import commands, sys, os, md5, cPickle


# From: http://www.joelverhagen.com/blog/2011/02/md5-hash-of-file-in-python/
import hashlib
def md5Checksum(filePath):
    fh = open(filePath, 'rb')
    m = hashlib.md5()
    while True:
        data = fh.read(8192)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def mount_snapshot(index):
  assert 1 <= index < MAX_INDEX
  mountpoint = '/tmp/nilfs-snapshots/%d' % index
  assert not os.path.isdir(mountpoint)
  os.mkdir(mountpoint)
  mount_cmd = 'sudo mount -t nilfs2 -n -o ro,cp=%d /dev/dm-3 %s' % (index, mountpoint)
  (status, output) = commands.getstatusoutput(mount_cmd)
  assert status == 0


def unmount_snapshot(index):
  assert 1 <= index < MAX_INDEX
  mountpoint = '/tmp/nilfs-snapshots/%d' % index
  assert os.path.isdir(mountpoint)
  umount_cmd = 'sudo umount ' + mountpoint
  (status, output) = commands.getstatusoutput(umount_cmd)
  assert status == 0
  os.rmdir(mountpoint)


# returns a dict
def get_stats(index):
  ret = {}

  ret['omitted_dotfiles'] = True # we're gonna omit dotfiles and dotdirectories

  assert 1 <= index < MAX_INDEX
  mountpoint = '/tmp/nilfs-snapshots/%d' % index
  homedir = mountpoint + '/researcher/'
  assert os.path.isdir(homedir)

  ret['index'] = index
  (status, output) = commands.getstatusoutput('du -sb ' + homedir)
  assert status == 0
  ret['total_bytes'] = int(output.split()[0])

  filesDict = {}
  ret['files'] = filesDict

  for (d, sd, files) in os.walk(homedir):
    for f in files:
      path = os.path.join(d, f)

      pretty_path = path[len(homedir):]

      # SKIP THESE to GREATLY GREATLY speed things up!!!
      if pretty_path.startswith('.'): continue # dot directory within $HOME
      if f.startswith('.'): continue # dotfile!

      # sometimes 'path' isn't a real file, so DON'T count those
      try:
        filesDict[pretty_path] = md5Checksum(path)
      except:
        print 'md5sum error on', path

  return ret


if __name__ == '__main__':
  #mount_snapshot(25585)
  #get_stats_fast(25585)
  #unmount_snapshot(25585)
  #sys.exit(0)

  #for i in range(149000, MAX_INDEX+1):
  for i in range(MAX_INDEX, MAX_INDEX+1):
    try:
      mount_snapshot(i)
      cPickle.dump(get_stats(i), open('/tmp/nilfs-snapshots/%d.pickle' % i, 'w'), -1)
      unmount_snapshot(i)
    except:
      print 'Uncaught exception at index', i
      continue

    if i % 100 == 0:
      print i


########NEW FILE########
__FILENAME__ = annotation_component
# PyGTK component for creating, loading, viewing, and saving
# annotations into a MongoDB database
#
# Created on 2011-12-13

import pygtk
pygtk.require('2.0')
import gtk, pango
from pygtk_burrito_utils import *
from pymongo import Connection


# db_liaison needs to have three methods to interact with an underlying
# database: insert_annotation(), delete_annotation(), load_annotation()
#
# if display_when_empty is non-null, then display the given message
# when there's no annotation
class AnnotationComponent:
  def __init__(self, width, db_liaison, display_when_empty=False):
    self.display_when_empty = display_when_empty

    ci = gtk.TextView()
    ci.set_wrap_mode(gtk.WRAP_WORD)
    ci.set_border_width(1)
    ci.set_left_margin(3)
    ci.set_right_margin(3)
    ci.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('#999999')) # need a gray border
    ci.modify_font(pango.FontDescription("sans 9"))

    comment_input = gtk.ScrolledWindow()
    comment_input.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    comment_input.set_size_request(width, 50)
    comment_input.add(ci)

    comment_post_btn = gtk.Button(' Post ')
    comment_post_btn.connect('clicked', self.post_comment)
    comment_cancel_btn = gtk.Button('Cancel')
    comment_cancel_btn.connect('clicked', self.cancel_comment)
    comment_button_hbox = gtk.HBox()
    comment_button_hbox.pack_start(comment_post_btn, expand=False)
    comment_button_hbox.pack_start(comment_cancel_btn, expand=False, padding=5)

    comment_box = gtk.VBox()
    comment_box.pack_start(comment_input)
    comment_box.pack_start(comment_button_hbox, padding=3)

    comment_display = gtk.Label()
    comment_display.modify_font(pango.FontDescription("sans 9"))
    # make annotations colored ...
    comment_display.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color('#3D477B'))
    comment_display.set_line_wrap(True) # turn on word-wrapping!

    comment_display.set_size_request(width, -1)

    comment_display_lalign = gtk.Alignment(0, 0, 0, 0)

    # only use the "Edit annotation" context menu when
    # display_when_empty is non-null
    if display_when_empty:
      edit_menu = gtk.Menu()
      edit_item = gtk.MenuItem('Edit annotation')
      edit_item.connect("activate", self.show_comment_box)
      edit_menu.append(edit_item)

      comment_display_evt_box = create_clickable_event_box(comment_display, edit_menu)
      comment_display_lalign.add(comment_display_evt_box)
    else:
      comment_display.set_selectable(True)
      comment_display_lalign.add(comment_display)

    comment_display_lalign.set_padding(0, 5, 2, 0)


    input_and_display_box = gtk.VBox()
    input_and_display_box.pack_start(comment_box, expand=False)
    input_and_display_box.pack_start(comment_display_lalign, expand=False)

    # enforce suggested width by putting it in an lalign:
    annotation_lalign = gtk.Alignment(0, 0, 0, 0)
    annotation_lalign.set_padding(2, 2, 8, 0)
    annotation_lalign.add(input_and_display_box)

    self.widget = annotation_lalign
    self.comment_input_text_buffer = ci.get_buffer()
    self.comment_box = comment_box
    self.comment_display = comment_display

    self.db_liaison = db_liaison
    self.saved_comment = self.db_liaison.load_annotation()

    show_all_local_widgets(locals())

    if self.saved_comment:
      self.comment_display.set_label(self.saved_comment)
      self.comment_input_text_buffer.set_text(self.saved_comment)
    else:
      self.show_empty_comment_display()

    self.comment_box.hide()


  def show_empty_comment_display(self):
    if self.display_when_empty:
      self.comment_display.set_label(self.display_when_empty)
      self.comment_display.show()
    else:
      self.comment_display.hide()


  def show_comment_box(self, *rest):
    self.comment_display.hide()
    self.comment_box.show()

  def post_comment(self, _ignore):
    self.comment_box.hide()

    # strip only trailing spaces
    self.saved_comment = self.get_comment_input_text().rstrip()

    if self.saved_comment:
      self.comment_display.set_label(self.saved_comment)
      self.comment_display.show()
      self.db_liaison.insert_annotation(self.saved_comment)
    else:
      self.show_empty_comment_display()
      self.db_liaison.delete_annotation()


  def cancel_comment(self, _ignore):
    self.comment_box.hide()
    if self.saved_comment:
      self.comment_display.show()
    else:
      self.show_empty_comment_display()


  def get_comment_input_text(self):
    return self.comment_input_text_buffer.get_text(*self.comment_input_text_buffer.get_bounds())

  def get_widget(self):
    return self.widget

  def get_saved_comment(self):
    return self.saved_comment


if __name__ == "__main__":
  window = gtk.Window(gtk.WINDOW_TOPLEVEL)
  window.connect("destroy", lambda w: gtk.main_quit())
  window.set_title("Annotator Component")
  window.set_border_width(8)

  c = Connection()
  annotation_test_collection = c.burrito_db.annotation_test

  a = AnnotationComponent(250, annotation_test_collection, 123)
  a.show_comment_box()

  window.add(a.get_widget())
  window.show()

  gtk.main()


########NEW FILE########
__FILENAME__ = BurritoUtils
../../BurritoUtils.py
########NEW FILE########
__FILENAME__ = burrito_feed
# Created on 2011-12-08
# implement a (near)real-time feed of user activities, sorta like a
# Facebook Feed or Twitter stream


import pygtk
pygtk.require('2.0')
import gtk, pango, gobject

import os, sys, gc
import datetime
import filecmp

import atexit
from signal import signal, SIGTERM

from pymongo import Connection, ASCENDING, DESCENDING

from pygtk_burrito_utils import *

from BurritoUtils import *
from urlparse import urlparse

from annotation_component import AnnotationComponent
from event_fetcher import *

import source_file_prov_viewer, output_file_prov_viewer

from file_version_manager import FileVersionManager, ONE_SEC


WINDOW_WIDTH = 300

FIVE_SECS = datetime.timedelta(seconds=5)


# use the primary X Window clipboard ...
g_clipboard = gtk.Clipboard(selection="PRIMARY")


# Ugh, kludgy globals ... relies on the fact that BurritoFeed is a
# singleton here ... will break down if this isn't the case :)

diff_left_half = None # type: FileFeedEvent.FileEventDisplay
diff_menu_items = []


# Key:   filename
# Value: FileEventDisplay object which is the baseline version to watch for changes
watch_files = {}

# Key: filename
# Value: timestamp of most recent read to this file
file_read_timestamps = {}

# each elt is a FileWriteEvent instance
# Key:   filename
# Value: list of FileWriteEvent instances in sorted order
sorted_write_events = {}


# http://stackoverflow.com/questions/69645/take-a-screenshot-via-a-python-script-linux
def save_screenshot(output_filename):
  assert output_filename.endswith('.png')
  w = gtk.gdk.get_default_root_window()
  sz = w.get_size()
  pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8,sz[0],sz[1])
  pb = pb.get_from_drawable(w,w.get_colormap(),0,0,0,0,sz[0],sz[1])
  if (pb != None):
    pb.save(output_filename, 'png')
    # To prevent a gross memory leak:
    # http://faq.pygtk.org/index.py?req=show&file=faq08.004.htp
    del pb
    gc.collect()
  else:
    print >> sys.stderr, "Failed to save screenshot to", output_filename


# Code taken from: http://stackoverflow.com/questions/1551382/python-user-friendly-time-format
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) in (int, long):
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time 
    elif not time:
        diff = now - now
    else:
        assert False, time
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"


# iterates in reverse over a list of FeedEvent instances and terminates
# either when the list ends or when an element's timestamp is older
# than target_time 
def gen_reverse_bounded_time_elts(lst, target_time):
  for e in reversed(lst):
    if e.timestamp < target_time:
      return
    yield e


class FeedEvent:
  PANGO_TIMESTAMP_TEMPLATE = '<span font_family="sans" size="8000" foreground="#999999">%s</span>'

  def __init__(self, dt, icon_filename):
    self.timestamp = dt # type datetime.datetime

    event_icon = gtk.Image()
    event_icon.set_from_file(icon_filename)

    # start empty
    timestamp_lalign = gtk.Alignment(0, 0.6, 0, 0)
    timestamp_lab = gtk.Label()
    timestamp_lalign.add(timestamp_lab)

    event_header = create_hbox((event_icon, timestamp_lalign), (0, 5))

    show_all_local_widgets(locals())
    self.timestamp_label = timestamp_lab
    self.header = event_header


  def get_widget(self):
    return self.widget

  def update_timestamp(self):
    self.timestamp_label.set_markup(FeedEvent.PANGO_TIMESTAMP_TEMPLATE % pretty_date(self.timestamp))


# represents a user-posted comment
class CommentFeedEvent(FeedEvent):
  def __init__(self, comment, dt, icon_filename, screenshot_filename=None):
    FeedEvent.__init__(self, dt, icon_filename)
    self.comment = comment

    context_menu = gtk.Menu()
    copy_item = gtk.MenuItem('Copy comment')
    copy_item.connect("activate", self.copy_comment)
    hashtag_item = gtk.MenuItem('Copy event hashtag')
    hashtag_item.connect("activate", self.copy_event_hashtag)
    context_menu.append(copy_item)
    context_menu.append(hashtag_item)

    lab = gtk.Label(self.comment)
    lab.modify_font(pango.FontDescription("sans 9"))
    lab.set_line_wrap(True) # turn on word-wrapping!
    lab.set_size_request(WINDOW_WIDTH - 35, -1) # request a reasonable initial width
    lab_box = create_clickable_event_box(lab, context_menu)
    comment_event_body = create_alignment(lab_box)

    comment_vbox = gtk.VBox()
    comment_vbox.pack_start(self.header)

    if screenshot_filename:
      screenshot_link = gtk.Label()
      screenshot_link.set_markup('<span font_family="sans" size="9000"><a href="file://%s">View screenshot</a></span>' % screenshot_filename)
      screenshot_lalign = create_alignment(screenshot_link, ptop=3)
      comment_vbox.pack_start(screenshot_lalign)

    comment_vbox.pack_start(comment_event_body, padding=5)

    show_all_local_widgets(locals())
    self.widget = comment_vbox
    self.update_timestamp()

  def save_to_db(self):
    self.event.save_to_db() # polymorphic!

  def copy_comment(self, _ignore):
    g_clipboard.set_text(self.comment)

  def copy_event_hashtag(self, _ignore):
    g_clipboard.set_text(self.event.get_hashtag())


class StatusUpdateFeedEvent(CommentFeedEvent):
  def __init__(self, status_update_event):
    self.event = status_update_event
    CommentFeedEvent.__init__(self, self.event.annotation,
                                    self.event.timestamp,
                                    "accessories-text-editor-24x24.png")

class HappyFaceFeedEvent(CommentFeedEvent):
  def __init__(self, happy_face_event):
    self.event = happy_face_event
    CommentFeedEvent.__init__(self, self.event.annotation,
                                    self.event.timestamp,
                                    "yellow-happy-face-24x24-antialiased.xpm",
                                    self.event.screenshot_filename)

class SadFaceFeedEvent(CommentFeedEvent):
  def __init__(self, sad_face_event):
    self.event = sad_face_event
    CommentFeedEvent.__init__(self, self.event.annotation,
                                    self.event.timestamp,
                                    "red-sad-face-24x24-antialiased.xpm",
                                    self.event.screenshot_filename)


# represents a BASH shell event object in the feed
class BashFeedEvent(FeedEvent):

  class BashCommandDisplay:
    def __init__(self, bash_cmd_event):
      self.bash_cmd_event = bash_cmd_event # BashCommandEvent instance
      self.cmd_str = ' '.join(bash_cmd_event.cmd)
      self.annotator = AnnotationComponent(WINDOW_WIDTH-50, bash_cmd_event)


      command_context_menu = gtk.Menu()
      cc_item1 = gtk.MenuItem('Copy command')
      cc_item1.connect("activate", self.copy_cmd)
      cc_item2 = gtk.MenuItem('Copy event hashtag')
      cc_item2.connect("activate", self.copy_event_hashtag)
      add_comment_item = gtk.MenuItem('Annotate invocation')
      add_comment_item.connect("activate", self.annotator.show_comment_box)

      command_context_menu.append(cc_item1)
      command_context_menu.append(cc_item2)
      command_context_menu.append(add_comment_item)

      cmd_label = gtk.Label(self.cmd_str)
      cmd_label.modify_font(pango.FontDescription("monospace 8"))
      cmd_label_box = create_clickable_event_box(cmd_label, command_context_menu)
      cmd_label_box.set_has_tooltip(True)
      cmd_label_box.connect('query-tooltip', show_tooltip, self.cmd_str)

      cmd_lalign = create_alignment(cmd_label_box, ptop=2, pbottom=2, pleft=2)

      cmd_vbox = create_vbox((cmd_lalign, self.annotator.get_widget()))

      show_all_local_widgets(locals())
      self.widget = cmd_vbox


    def copy_cmd(self, _ignore):
      g_clipboard.set_text(self.cmd_str)

    def copy_event_hashtag(self, _ignore):
      g_clipboard.set_text(self.bash_cmd_event.get_hashtag())

    def get_widget(self):
      return self.widget


  def copy_pwd(self, _ignore):
    g_clipboard.set_text('cd ' + self.pwd)

  def __init__(self, pwd):
    FeedEvent.__init__(self, None, "terminal-24x24-icon.png")
    self.pwd = pwd

    def create_pwd_popup_menu():
      menu = gtk.Menu()
      item = gtk.MenuItem('Copy directory')
      item.connect("activate", self.copy_pwd)
      item.show()
      menu.append(item)
      return menu # don't show() the menu itself; wait for a popup() call

    pwd_popup_menu = create_pwd_popup_menu()

    pwd_display = gtk.Label()
    pwd_display.set_markup('<span underline="single" font_family="monospace" size="9000" foreground="#555555">%s</span>' % prettify_filename(pwd))

    pwd_display.set_has_tooltip(True)
    pwd_display.connect('query-tooltip', show_tooltip, prettify_filename(pwd))

    pwd_display_box = create_clickable_event_box(pwd_display, pwd_popup_menu)

    bash_event_body = gtk.VBox()

    pwd_valign = create_alignment(pwd_display_box, ptop=3, pbottom=4, pleft=1)
    bash_event_body.pack_start(pwd_valign)

    bash_vbox = gtk.VBox()
    bash_vbox.pack_start(self.header)
    bash_vbox.pack_start(bash_event_body)

    show_all_local_widgets(locals())

    # assign these locals to instance vars after they've been shown ...
    self.widget = bash_vbox
    self.events_vbox = bash_event_body
    self.commands_set = set()


  def add_command_chron_order(self, bash_cmd_event):
    # since we're presumably inserting in chronological order,
    # then update the timestamp when inserting each comment in
    # succession, even if it's already in the collection
    assert not self.timestamp or bash_cmd_event.timestamp > self.timestamp
    self.timestamp = bash_cmd_event.timestamp
    self.update_timestamp()

    cmd_str = ' '.join(bash_cmd_event.cmd)

    # eliminate duplicates
    if cmd_str in self.commands_set:
      return
    self.commands_set.add(cmd_str)

    n = BashFeedEvent.BashCommandDisplay(bash_cmd_event)
    self.events_vbox.pack_start(n.get_widget(), expand=True)


# represents a webpage visit event object in the feed
class WebpageFeedEvent(FeedEvent):

  class WebpageDisplay:
    def __init__(self, webpage_event):
      self.webpage_event = webpage_event # WebpageVisitEvent instance
      self.annotator = AnnotationComponent(WINDOW_WIDTH-50, webpage_event)

      webpage_context_menu = gtk.Menu()
      hashtag_item = gtk.MenuItem('Copy event hashtag')
      hashtag_item.connect("activate", self.copy_event_hashtag)
      add_comment_item = gtk.MenuItem('Annotate web visit')
      add_comment_item.connect("activate", self.annotator.show_comment_box)
      webpage_context_menu.append(hashtag_item)
      webpage_context_menu.append(add_comment_item)

      # make the domain name concise:
      domain_name = urlparse(webpage_event.url).netloc
      if domain_name.startswith('www.'):
        domain_name = domain_name[len('www.'):]

      domain_display = gtk.Label()
      domain_display.set_markup('<span font_family="sans" size="8000" foreground="#666666">[%s] </span>' % domain_name)
      domain_display_box = create_clickable_event_box(domain_display, webpage_context_menu)
      domain_display_box.set_has_tooltip(True)
      domain_display_box.connect('query-tooltip', show_tooltip, webpage_event.url)

      link_display = gtk.Label()
      encoded_url = webpage_event.url.replace('&', '&amp;')
      encoded_title = webpage_event.title.replace('&', '&amp;')

      link_display.set_markup('<span font_family="sans" size="8000"><a href="%s">%s</a></span>' % (encoded_url, encoded_title))

      domain_and_link_display = create_hbox((domain_display_box, link_display))
      webpage_display_lalign = create_alignment(domain_and_link_display, ptop=2, pbottom=1, pleft=1)

      disp_vbox = create_vbox((webpage_display_lalign, self.annotator.get_widget()))

      show_all_local_widgets(locals())
      self.widget = disp_vbox


    def copy_event_hashtag(self, _ignore):
      g_clipboard.set_text(self.webpage_event.get_hashtag())

    def get_widget(self):
      return self.widget


  def __init__(self):
    FeedEvent.__init__(self, None, "google-chrome.png")

    webpage_event_body = gtk.VBox()
    webpage_vbox = gtk.VBox()
    webpage_vbox.pack_start(self.header)
    webpage_vbox.pack_start(webpage_event_body)

    show_all_local_widgets(locals())

    self.widget = webpage_vbox
    self.webpage_event_body = webpage_event_body
    self.stored_URLs = set()


  def add_webpage_chron_order(self, webpage_event):
    # since we're presumably inserting in chronological order,
    # then update the timestamp when inserting each comment in
    # succession, even if it's already in the collection
    assert not self.timestamp or webpage_event.timestamp >= self.timestamp
    self.timestamp = webpage_event.timestamp
    self.update_timestamp()

    # eliminate dups (but still update timestamp unconditionally)
    if webpage_event.url in self.stored_URLs:
      return
    self.stored_URLs.add(webpage_event.url)

    n = WebpageFeedEvent.WebpageDisplay(webpage_event)
    self.webpage_event_body.pack_start(n.get_widget())


THUMBNAIL_WIDTH = 250

class DoodleFeedEvent(FeedEvent):
  def __init__(self, doodle_event, fvm):
    FeedEvent.__init__(self, doodle_event.timestamp, 'mypaint.png')
    self.doodle_event = doodle_event # type: DoodleSaveEvent
    self.timestamp = doodle_event.timestamp
    self.update_timestamp()
    self.fvm = fvm

    thumbnail = gtk.Image()

    thumbnail_lalign = create_alignment(thumbnail, ptop=3, pbottom=4)

    thumbnail_event_box = gtk.EventBox()
    thumbnail_event_box.add(thumbnail_lalign)
    set_white_background(thumbnail_event_box)
    thumbnail_event_box.connect('realize',
                                lambda e:e.window.set_cursor(g_handcursor))

    thumbnail_event_box.connect("button_press_event", self.load_fullsize_image)

    doodle_vbox = gtk.VBox()
    doodle_vbox.pack_start(self.header)
    doodle_vbox.pack_start(thumbnail_event_box)

    show_all_local_widgets(locals())
    self.widget = doodle_vbox
    self.thumbnail = thumbnail # don't load the image just yet!


  def load_thumbnail(self):
    # regular behavior:
    if self.doodle_event.filename in sorted_write_events:
      # ok, we need to grab the version of the file that existed after
      # self.timestamp and BEFORE the next write to that file, since the
      # user might have CLOBBERED this doodle image file with newer doodles,
      # so self.filename might not be correct (or it could be non-existent!)
      filename = self.fvm.checkout_file_before_next_write(self.doodle_event,
                                                          sorted_write_events[self.doodle_event.filename])
    else:
      # if we don't have sorted_write_events, just use the following
      # approximation ...
      filename = self.fvm.checkout_file(self.doodle_event.filename,
                                        self.doodle_event.timestamp + datetime.timedelta(seconds=5))

    assert filename

    # resize the doodle down to a respectable size
    # http://faq.pygtk.org/index.py?req=show&file=faq08.006.htp
    pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
    w = pixbuf.get_width()
    h = pixbuf.get_height()
    if w > THUMBNAIL_WIDTH:
      scaled_buf = pixbuf.scale_simple(THUMBNAIL_WIDTH,
                                       int(float(THUMBNAIL_WIDTH) * float(h) / float(w)),
                                       gtk.gdk.INTERP_BILINEAR)
      self.thumbnail.set_from_pixbuf(scaled_buf)
    else:
      self.thumbnail.set_from_file(filename)
    self.thumbnail.show()


  def load_fullsize_image(self, _ignore, _ignore2):
    if self.doodle_event.filename in sorted_write_events:
      # dynamically generate the filename since the path might have
      # changed (due to new writes ... tricky and subtle!)
      filename = self.fvm.checkout_file_before_next_write(self.doodle_event,
                                                          sorted_write_events[self.doodle_event.filename])
    else:
      filename = self.fvm.checkout_file(self.doodle_event.filename,
                                        self.doodle_event.timestamp + datetime.timedelta(seconds=5))

    assert filename
    os.system('gnome-open "%s" &' % filename)


class FileFeedEvent(FeedEvent):

  class FileEventDisplay:
    def __init__(self, file_provenance_event, parent):
      self.file_provenance_event = file_provenance_event
      self.parent = parent # sub-class of FileFeedEvent
      self.fvm = parent.fvm # instance of FileVersionManager

      self.annotator = AnnotationComponent(WINDOW_WIDTH-50, file_provenance_event)

      file_context_menu = gtk.Menu()

      diff_cur_item = gtk.MenuItem('Diff against latest')
      diff_cur_item.connect("activate", self.diff_with_latest)

      diff_pred_item = gtk.MenuItem('Diff against predecessor')
      diff_pred_item.connect("activate", self.diff_with_predecessor)

      mark_diff = gtk.MenuItem('Select for diff')
      mark_diff.connect("activate", self.mark_for_diff)

      global diff_menu_items
      diff_menu_items.append(mark_diff)

      view = gtk.MenuItem('Open')
      view.connect("activate", self.open_to_view, 'current')
      view_pred = gtk.MenuItem('Open predecessor')
      view_pred.connect("activate", self.open_to_view, 'predecessor')

      revert_current = gtk.MenuItem('Revert to current')
      revert_current.connect("activate", self.revert, 'current')
      revert_pred = gtk.MenuItem('Revert to predecessor')
      revert_pred.connect("activate", self.revert, 'predecessor')
      watch_me = gtk.MenuItem('Watch for changes')
      watch_me.connect("activate", self.watch_for_changes)
      view_source_prov = gtk.MenuItem('View source file provenance')
      view_source_prov.connect("activate", self.view_source_prov)
      view_output_prov = gtk.MenuItem('View output file provenance')
      view_output_prov.connect("activate", self.view_output_prov)

      # not implemented yet
      item5 = gtk.MenuItem('Ignore file')
      item6 = gtk.MenuItem('Ignore directory')

      copy_filename_item = gtk.MenuItem('Copy filename')
      copy_filename_item.connect("activate", self.copy_filename)
      hashtag_item = gtk.MenuItem('Copy event hashtag')
      hashtag_item.connect("activate", self.copy_event_hashtag)
      add_comment_item = gtk.MenuItem('Annotate file version')
      add_comment_item.connect("activate", self.annotator.show_comment_box)

      separator1 = gtk.SeparatorMenuItem()
      separator2 = gtk.SeparatorMenuItem()
      separator3 = gtk.SeparatorMenuItem()
      separator4 = gtk.SeparatorMenuItem()

      file_context_menu.append(copy_filename_item)
      file_context_menu.append(hashtag_item)
      file_context_menu.append(add_comment_item)
      file_context_menu.append(separator1)
      file_context_menu.append(diff_cur_item)
      file_context_menu.append(diff_pred_item)
      file_context_menu.append(mark_diff)
      file_context_menu.append(separator2)
      file_context_menu.append(view)
      file_context_menu.append(view_pred)
      file_context_menu.append(watch_me)
      file_context_menu.append(separator3)
      file_context_menu.append(revert_current)
      file_context_menu.append(revert_pred)
      file_context_menu.append(separator4)
      file_context_menu.append(view_source_prov)
      file_context_menu.append(view_output_prov)
      #file_context_menu.append(item5)
      #file_context_menu.append(item6)

      # only show base path in label for brevity
      file_label = gtk.Label(os.path.basename(self.file_provenance_event.filename))
      file_label.modify_font(pango.FontDescription("monospace 8"))
      file_label_box = create_clickable_event_box(file_label, file_context_menu)
      # ... but show FULL file path in tooltip
      file_label_box.set_has_tooltip(True)
      file_label_box.connect('query-tooltip', show_tooltip, prettify_filename(self.file_provenance_event.filename))

      icon_and_label_box = gtk.HBox()
      icon_and_label_box.pack_end(file_label_box, expand=False)

      file_lalign = create_alignment(icon_and_label_box, ptop=2, pbottom=2, pleft=2)

      file_vbox = create_vbox((file_lalign, self.annotator.get_widget()))

      show_all_local_widgets(locals())
      self.widget = file_vbox
      self.icon_and_label_box = icon_and_label_box
      self.watchme_icon_alignment = None # lazily allocate to save memory


      global watch_files
      try:
        old_version_path = watch_files[self.file_provenance_event.filename].checkout_and_get_path()
        if os.path.exists(old_version_path):
          if not filecmp.cmp(old_version_path, self.file_provenance_event.filename):
            # there's a diff!
            changed_icon = gtk.Image()
            changed_icon.set_from_file('red-exclamation-point-16x16.png')
            changed_icon.show()
            changed_icon_alignment = create_alignment(changed_icon, pright=3)
            changed_icon_alignment.show()
            self.icon_and_label_box.pack_end(changed_icon_alignment)
            file_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color('#800517')) # make it red!
          else:
            # 'passed' the informal regression test set by watchfile
            test_pass_icon = gtk.Image()
            test_pass_icon.set_from_file('tasque-check-box.png')
            test_pass_icon.show()
            test_pass_icon_alignment = create_alignment(test_pass_icon, pright=3)
            test_pass_icon_alignment.show()
            self.icon_and_label_box.pack_end(test_pass_icon_alignment)
      except KeyError:
        pass


    def get_widget(self):
      return self.widget
    
    def get_filename(self):
      return self.file_provenance_event.filename

    def copy_filename(self, _ignore):
      g_clipboard.set_text(self.file_provenance_event.filename)

    def copy_event_hashtag(self, _ignore):
      g_clipboard.set_text(self.file_provenance_event.get_hashtag())


    def checkout_and_get_path(self):
      return self.fvm.checkout_file_before_next_write(self.file_provenance_event,
                                                      sorted_write_events[self.file_provenance_event.filename])

    # to find the predecessor, simply check out the file one second
    # before the write occurred ...
    #
    # TODO: this isn't exactly correct, since you could've had a bunch
    # of coalesced writes, so you might want to get the version BEFORE
    # the series of coalesced writes.
    def checkout_predecessor_and_get_path(self):
      return self.fvm.checkout_file(self.get_filename(),
                                    self.file_provenance_event.timestamp - ONE_SEC)


    def diff_with_latest(self, _ignore):
      # requires the 'meld' visual diff tool to be installed
      old_version_path = self.checkout_and_get_path()
      fn = self.file_provenance_event.filename
      os.system('meld "%s" "%s" &' % (old_version_path, fn))


    def diff_with_predecessor(self, _ignore):
      post_write_path = self.checkout_and_get_path()
      predecessor_path = self.checkout_predecessor_and_get_path()
      os.system('meld "%s" "%s" &' % (predecessor_path, post_write_path))


    def mark_for_diff(self, _ignore):
      global diff_left_half, diff_menu_items # KLUDGY!
      if diff_left_half:
        diff_right_half_path = self.checkout_and_get_path()
        diff_left_half_path = diff_left_half.checkout_and_get_path()
        os.system('meld "%s" "%s" &' % (diff_left_half_path, diff_right_half_path))

        # RESET!
        diff_left_half = None
        for e in diff_menu_items:
          e.set_label('Select for diff')
      else:
        diff_left_half = self 
        for e in diff_menu_items:
          e.set_label('Diff against selected file')


    def open_to_view(self, _ignore, option):
      if option == 'current':
        old_version_path = self.checkout_and_get_path()
      elif option == 'predecessor':
        old_version_path = self.checkout_predecessor_and_get_path()
      else:
        assert False

      # gnome-open to the rescue!!!  uses a file's type to determine the
      # proper viewer application :)
      if not os.path.isfile(old_version_path):
        create_popup_error_dialog("File not found:\n" + old_version_path)
      else:
        os.system('gnome-open "%s" &' % old_version_path)


    def view_source_prov(self, _ignore):
      global cur_session
      spv = source_file_prov_viewer.SourceFileProvViewer(self.get_filename(), cur_session, self.fvm)

    def view_output_prov(self, _ignore):
      global cur_session # KLUDGY!
      print 'view_output_prov:', self.get_filename(), cur_session
      opv = output_file_prov_viewer.OutputFileProvViewer(self.get_filename(), cur_session, self.fvm)


    def watch_for_changes(self, _ignore):
      global watch_files
      fn = self.file_provenance_event.filename
      if fn in watch_files:
        # un-watch the other file:
        other = watch_files[fn]
        assert other.watchme_icon_alignment
        other.icon_and_label_box.remove(other.watchme_icon_alignment)

        # if other is actually self, then un-watch!
        if other == self:
          del watch_files[fn]
          return # PUNTTT!

      watch_files[fn] = self

      # "freeze" the enclosing FileMutatedFeedEvent object when you
      # create a watchpoint so that subsequent writes don't coalesce into
      # this FileMutatedFeedEvent entry and possibly destroy the current
      # FileEventDisplay object in the # process!
      self.parent.frozen = True

      watchme_icon = gtk.Image()
      watchme_icon.set_from_file('magnifying-glass-16x16.png')
      watchme_icon.show()
      self.watchme_icon_alignment = create_alignment(watchme_icon, pright=3)
      self.watchme_icon_alignment.show()

      self.icon_and_label_box.pack_end(self.watchme_icon_alignment)


    # option = 'current' or 'predecessor'
    def revert(self, _ignore, option):
      if option == 'current':
        old_version_path = self.checkout_and_get_path()
      elif option == 'predecessor':
        old_version_path = self.checkout_predecessor_and_get_path()
      else:
        assert False

      if not os.path.isfile(old_version_path):
        create_popup_error_dialog("File not found:\n" + old_version_path)
      else:
        # pop-up a confirmation dialog before taking drastic action!
        d = gtk.MessageDialog(None,
                              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                              gtk.MESSAGE_QUESTION,
                              gtk.BUTTONS_YES_NO,
                              message_format="Are you sure you want to revert\n\n  %s\n\nto\n\n  %s" % \
                                             (self.get_filename(), old_version_path))
        d.show()
        response = d.run()
        d.destroy()

        if response == gtk.RESPONSE_YES:

          # VERY INTERESTING: the 'cp' command sometimes doesn't work
          # for NILFS, since it thinks that the snapshot version is
          # IDENTICAL to the latest current version of the file and will
          # thus refuse to do the copy even though their contents are
          # clearly different.
          #
          # Thus, we will do a super-hack where we copy the file to
          # tmp_blob and then rename it to the real filename ...
          tmp_blob = '/tmp/tmp-reverted-file'
          revert_cmd = "cp '%s' '%s'; mv '%s' '%s'" % (old_version_path, tmp_blob,
                                                       tmp_blob, self.get_filename())
          os.system(revert_cmd)


  def revert_all_files_to_pred(self, _ignore):
    for v in self.contents.itervalues():
      v.revert(None, 'predecessor')

  def watch_all_files(self, _ignore):
    for v in self.contents.itervalues():
      v.watch_for_changes(None)


  def __init__(self, process_name, fvm, icon_filename):
    FeedEvent.__init__(self, None, icon_filename)
    self.process_name = process_name
    self.fvm = fvm

    self.frozen = False # if frozen, then don't allow any more coalescing into it!

    def create_proc_popup_menu():
      menu = gtk.Menu()
      #item1 = gtk.MenuItem('Ignore process')

      revert_all = gtk.MenuItem('Revert all files to predecessors')
      revert_all.connect('activate', self.revert_all_files_to_pred)
      revert_all.show()

      watch_all_files = gtk.MenuItem('Watch all files for changes')
      watch_all_files.connect('activate', self.watch_all_files)
      watch_all_files.show()

      menu.append(watch_all_files)
      menu.append(revert_all)
      return menu # don't show() the menu itself; wait for a popup() call


    proc_display = gtk.Label()
    proc_display.set_markup('<span underline="single" font_family="monospace" size="9000" foreground="#555555">%s</span>' % self.process_name)

    # Punt on this menu for now ...
    proc_popup_menu = create_proc_popup_menu()
    proc_display_box = create_clickable_event_box(proc_display, proc_popup_menu)

    proc_valign = create_alignment(proc_display_box, ptop=3, pbottom=4, pleft=1)
    file_event_body = gtk.VBox()
    file_event_body.pack_start(proc_valign)

    file_vbox = gtk.VBox()
    file_vbox.pack_start(self.header)
    file_vbox.pack_start(file_event_body)

    show_all_local_widgets(locals())

    # assign these locals to instance vars after they've been shown ...
    self.widget = file_vbox
    self.events_vbox = file_event_body

    # Key: filename
    # Value: FileFeedEvent.FileEventDisplay object
    self.contents = {}


  def add_file_evt_chron_order(self, file_provenance_event):
    # since we're presumably inserting in chronological order,
    # then update the timestamp when inserting each comment in
    # succession, even if it's already in the collection
    #
    # loosened the '>' comparison to '>=' to handle some corner cases:
    assert not self.timestamp or file_provenance_event.timestamp >= self.timestamp
    self.timestamp = file_provenance_event.timestamp
    self.update_timestamp()

    fn = file_provenance_event.filename

    # de-dup by removing existing widget for this filename (if it exists)
    try:
      existing_widget = self.contents[fn].get_widget()
      self.events_vbox.remove(existing_widget)
    except KeyError:
      pass

    # ALWAYS add the latest entry (so we can have an up-to-date timestamp) ...
    n = FileFeedEvent.FileEventDisplay(file_provenance_event, self)
    self.contents[fn] = n
    self.events_vbox.pack_start(n.get_widget(), expand=True)


# represents a file 'read' event (either a read or the source of a
# rename operation) by a particular process
class FileObservedFeedEvent(FileFeedEvent):
  def __init__(self, process_name, fvm):
    FileFeedEvent.__init__(self, process_name, fvm, "magnifying-glass.png")

# represents a file-mutated event in the feed (either a write or the
# target of a rename operation), whereby one or more files are being
# mutated by a particular process (either active or exited).
class FileMutatedFeedEvent(FileFeedEvent):
  def __init__(self, process_name, fvm):
    FileFeedEvent.__init__(self, process_name, fvm, "media-floppy.png")


class BurritoFeed:
  def create_status_pane(self):

    happy_img = gtk.Image()
    happy_img.set_from_file("yellow-happy-face.xpm")
    happy_face = gtk.Button()
    happy_face.add(happy_img)
    happy_face.set_relief(gtk.RELIEF_HALF)
    happy_face.connect('clicked', self.happy_face_button_clicked)

    sad_img = gtk.Image()
    sad_img.set_from_file("red-sad-face.xpm")
    sad_face = gtk.Button()
    sad_face.add(sad_img)
    sad_face.set_relief(gtk.RELIEF_HALF)
    sad_face.connect('clicked', self.sad_face_button_clicked)

    happy_sad_face_pane = gtk.HBox()
    happy_sad_face_pane.pack_start(happy_face, expand=True, fill=True, padding=15)
    happy_sad_face_pane.pack_end(sad_face, expand=True, fill=True, padding=15)


    su_input = gtk.TextView()
    su_input.set_wrap_mode(gtk.WRAP_WORD)
    su_input.set_left_margin(3)
    su_input.set_right_margin(3)
    # add a thin gray border around the text input box:
    su_input.set_border_width(1)
    su_input.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('#bbbbbb'))

    # I dunno how to set the number of displayed rows, so I just did a
    # hack and set the requested size to be something fairly small ...
    su_input.set_size_request(0, 50)

    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(su_input)

    status_update_pane = gtk.VBox()
    status_update_pane.pack_start(sw, padding=3)

    su_post_button = gtk.Button("   Post   ")
    su_post_button.connect('clicked', self.post_button_clicked)

    l = gtk.Label("What's on your mind?")
    l.set_alignment(0, 0.5)

    post_pane = gtk.HBox()
    post_pane.pack_start(l, expand=True, fill=True)

    post_pane.pack_end(su_post_button, expand=False, fill=False)
    status_update_pane.pack_start(post_pane, padding=2)

    status_pane = create_vbox((happy_sad_face_pane, status_update_pane), (5, 0))

    show_all_local_widgets(locals())

    su_input.grab_focus() # do this as late as possible

    # kinda impure, but whatever ...
    self.status_input = su_input
    self.most_recent_status_str = None # to prevent accidental multiple-clicks

    return status_pane


  def __init__(self, cur_session):
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.window.connect("destroy", lambda w: gtk.main_quit())

    self.cur_session = cur_session # unique session ID

    self.window.set_title("Activity Feed")
    self.window.set_icon_from_file("yellow-happy-face.xpm")
    self.window.set_border_width(5)

    vpane = gtk.VBox()
    self.window.add(vpane)

    self.status_pane = self.create_status_pane()

    feed_pane = gtk.ScrolledWindow()
    feed_pane.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    feed_vbox = gtk.VBox()

    vp = gtk.Viewport()
    vp.add(feed_vbox)
    vp.set_shadow_type(gtk.SHADOW_NONE)
    vp.set_size_request(int((WINDOW_WIDTH * 2.0) / 3), 20) # limit its width
    set_white_background(vp)
    feed_pane.add(vp)

    hs = gtk.HSeparator()
    vpane.pack_start(self.status_pane, expand=False, padding=5)
    vpane.pack_start(hs, expand=False, padding=3)
    vpane.pack_start(feed_pane, expand=True) # fill up the rest of the vbox!


    # move window to left side and make it as tall as the desktop
    self.window.move(0, 0)
    #_w, _h = self.window.get_size()
    self.window.resize(WINDOW_WIDTH, self.window.get_screen().get_height())

    set_white_background(self.window)

    show_all_local_widgets(locals())
    self.window.show() # show the window last

    self.feed_vbox = feed_vbox

    self.feed_events = [] # each element is an instance of a FeedEvent subclass


    # MongoDB stuff
    c = Connection()
    self.db = c.burrito_db

    # we want to incrementally update events in a 'sandwiched' time
    # range between prev_db_last_updated_time and cur_db_last_updated_time
    self.prev_db_last_updated_time = None
    self.cur_db_last_updated_time  = None

    # for making sure we always fetch fresh new FileProvenanceEvent objects
    # each elt is the return value from FileProvenanceEvent.get_unique_id()
    self.file_events_seen = set()

    self.first_time = True

    # for managing NILFS file versions:
    self.fvm = FileVersionManager()


  # returns a list of BashCommandEvent objects
  def fetch_new_bash_events(self):
    db_bash_collection = self.db.apps.bash
    ret = []
    
    if self.prev_db_last_updated_time:
      # tricky tricky ... start looking from the PREVIOUS epoch
      query = db_bash_collection.find({"session_tag": self.cur_session, "_id":{"$gte":self.prev_db_last_updated_time}})
    else:
      query = db_bash_collection.find({"session_tag": self.cur_session})

    for m in query:
      evt = fetch_bash_command_event(m)
      if evt:
        ret.append(evt)

    return ret


  # returns a list of WebpageVisitEvent objects
  def fetch_new_webpage_events(self):
    db_gui_collection = self.db.gui_trace
    ret = []

    if self.prev_db_last_updated_time:
      # tricky tricky ... start looking from the PREVIOUS epoch
      query = db_gui_collection.find({"session_tag": self.cur_session, "_id":{"$gte":self.prev_db_last_updated_time}})
    else:
      query = db_gui_collection.find({"session_tag": self.cur_session})

    for m in query:
      evt = fetch_webpage_visit_event(m)
      if evt:
        ret.append(evt)

    return ret


  # returns a list of FileProvenanceEvent objects
  def fetch_new_file_events(self):
    db_proc_collection = self.db.process_trace

    ret = []
    if self.prev_db_last_updated_time:
      # tricky tricky ... start looking from the PREVIOUS epoch
      query = db_proc_collection.find({"session_tag": self.cur_session,
                                       "most_recent_event_timestamp":{"$gte":self.prev_db_last_updated_time}},
                                       {'pid':1, 'uid':1, 'phases':1})
    else:
      query = db_proc_collection.find({"session_tag": self.cur_session},
                                      {'pid':1, 'uid':1, 'phases':1})

    for m in query:
      evts = fetch_file_prov_event_lst(m, self.cur_session)
      # de-dup!!!
      for e in evts:
        e_id = e.get_unique_id()
        if e_id not in self.file_events_seen:
          ret.append(e)
          self.file_events_seen.add(e_id)

    return ret


  def fetch_new_status_update_events(self):
    # ONLY RUN THIS ONCE at the beginning of execution!!!
    if self.first_time:
      return fetch_toplevel_annotation_events(self.cur_session)
    else:
      return []


  def poll_for_all_event_updates(self):
    bash_events = self.fetch_new_bash_events()
    web_events  = self.fetch_new_webpage_events()
    file_events = self.fetch_new_file_events()
    status_update_events = self.fetch_new_status_update_events()

    db_bash_collection = self.db.apps.bash

    print datetime.datetime.now()
    print '# bash events:', len(bash_events)
    print '# web events:', len(web_events)
    print '# file events:', len(file_events)
    print '# status events :', len(status_update_events)
    print

    self.first_time = False


    # Now "weave" together all streams of event updates:
    all_events = bash_events + web_events + file_events + status_update_events
 
    all_events.sort(key=lambda e:e.timestamp) # chronologically

    new_doodle_feed_events = []

    last_feed_event = None
    for evt in all_events:
      if self.feed_events:
        last_feed_event = self.feed_events[-1]

      if evt.__class__ == BashCommandEvent:
        if (last_feed_event and \
            last_feed_event.__class__ == BashFeedEvent and \
            last_feed_event.pwd == evt.pwd):
          last_feed_event.add_command_chron_order(evt)
        else:
          n = BashFeedEvent(evt.pwd)
          n.add_command_chron_order(evt)
          self.push_feed_event(n)

      elif evt.__class__ == WebpageVisitEvent:
        if (last_feed_event and \
            last_feed_event.__class__ == WebpageFeedEvent):
          last_feed_event.add_webpage_chron_order(evt)
        else:
          n = WebpageFeedEvent()
          n.add_webpage_chron_order(evt)
          self.push_feed_event(n)

      elif evt.__class__ == DoodleSaveEvent:
        # copy-and-paste from FileWriteEvent
        if evt.filename in sorted_write_events:
          assert sorted_write_events[evt.filename][-1].timestamp < evt.timestamp
        else:
          sorted_write_events[evt.filename] = []

        sorted_write_events[evt.filename].append(evt)

        n = DoodleFeedEvent(evt, self.fvm)
        self.push_feed_event(n)
        new_doodle_feed_events.append(n)

      elif evt.__class__ == FileWriteEvent:
        if evt.filename in sorted_write_events:
          assert sorted_write_events[evt.filename][-1].timestamp <= evt.timestamp
        else:
          sorted_write_events[evt.filename] = []

        sorted_write_events[evt.filename].append(evt)

        # First try to coalesce with last_feed_event, regardless of its timestamp ...
        # (unless it's frozen)
        if (last_feed_event and \
            last_feed_event.__class__ == FileMutatedFeedEvent and \
            last_feed_event.process_name == evt.phase_name and \
            not last_feed_event.frozen):

          # except if there's a read barrier!
          last_read_time = None
          try:
            last_read_time = file_read_timestamps[evt.filename]
          except KeyError:
            pass

          if not last_read_time or last_read_time <= evt.timestamp:
            last_feed_event.add_file_evt_chron_order(evt)
            #print 'C:', evt.phase_name, evt.filename
            continue # move along!


        # Process coalescing heuristic: try to go back FIVE SECONDS in
        # the feed to see if there are any matching events with the same
        # process name, and if so, coalesce evt into that process's
        # feed entry.
        #
        # The rationale for this heuristic is that when you're running a
        # ./configure or make compile job, there are often several
        # related 'friend' processes such as cc1/as, sed/grep/cat, etc.
        # that run very quickly back-and-forth, so if you don't
        # coalesce, then you would create a TON of separate
        # FileMutatedFeedEvent instances, when in fact the multiple
        # invocations could be grouped into one instance.  e.g., if you
        # didn't coalesce, you would get something like:
        #   [cc1, as, cc1, as, cc1, as, cc1, as, cc1, as ...]
        #
        # but if you coalesce, you get something much cleaner:
        #   [cc1, as]

        coalesced = False
        for cur_feed_elt in gen_reverse_bounded_time_elts(self.feed_events, evt.timestamp - FIVE_SECS):

          # VERY IMPORTANT!  If there is an intervening read of THIS
          # PARTICULAR FILE, then break right away, because we don't want
          # to coalesce writes beyond read barriers
          try:
            last_read_time = file_read_timestamps[evt.filename]
            if last_read_time > cur_feed_elt.timestamp:
              break
          except KeyError:
            pass

          if (cur_feed_elt.__class__ == FileMutatedFeedEvent and \
              cur_feed_elt.process_name == evt.phase_name):
            if not cur_feed_elt.frozen:
              cur_feed_elt.add_file_evt_chron_order(evt)
              coalesced = True

            # exit loop after the first FileMutatedFeedEvent regardless
            # of whether it's been frozen
            break


        # fallback is to create a new FileMutatedFeedEvent
        if not coalesced:
          n = FileMutatedFeedEvent(evt.phase_name, self.fvm)
          n.add_file_evt_chron_order(evt)
          self.push_feed_event(n)


      elif evt.__class__ == FileReadEvent:
        # add a "read barrier" to prevent write coalescing
        # over-optimizations
        file_read_timestamps[evt.filename] = evt.timestamp

      elif evt.__class__ == StatusUpdateEvent:
        n = StatusUpdateFeedEvent(evt)
        self.push_feed_event(n)

      elif evt.__class__ == HappyFaceEvent:
        n = HappyFaceFeedEvent(evt)
        self.push_feed_event(n)

      elif evt.__class__ == SadFaceEvent:
        n = SadFaceFeedEvent(evt)
        self.push_feed_event(n)

      else:
        print evt
        assert False


    # defer loading of thumnbnails until ALL DoodleFeedEvent instances
    # have been processed, since that's the only way we can ensure that
    # the proper versions of the files are loaded for the thumbnails
    for d in new_doodle_feed_events:
      d.load_thumbnail()


  def push_feed_event(self, evt):
    self.feed_events.append(evt)
    # push new entries to the TOP of the feed
    self.feed_vbox.pack_end(evt.get_widget(), expand=False, padding=6)
    self.update_all_timestamps()

  def update_all_timestamps(self):
    for e in self.feed_events:
      e.update_timestamp()

  def post_button_clicked(self, widget):
    buf = self.status_input.get_buffer()
    status_str = buf.get_text(*buf.get_bounds())
    if status_str and status_str != self.most_recent_status_str:
      self.most_recent_status_str = status_str # to prevent accidental multiple-submits
      n = StatusUpdateFeedEvent(StatusUpdateEvent(status_str,
                                                  datetime.datetime.now(),
                                                  self.cur_session))
      self.push_feed_event(n)
      n.save_to_db() # very important!!!

  def happy_face_button_clicked(self, widget):
    self.commit_handler(widget, True)

  def sad_face_button_clicked(self, widget):
    self.commit_handler(widget, False)

  def commit_handler(self, widget, is_happy):
    if is_happy:
      state = 'happy'
    else:
      state = 'sad'

    label = gtk.Label("What just made you %s?" % state)

    ci = gtk.TextView()
    ci.set_wrap_mode(gtk.WRAP_WORD)
    ci.set_border_width(1)
    ci.set_left_margin(3)
    ci.set_right_margin(3)
    ci.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('#999999'))
    ci.modify_font(pango.FontDescription("sans 10"))

    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.add(ci)
    sw.set_size_request(350, 150)

    dialog = gtk.Dialog("%s snapshot" % state,
                       None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                        gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
    dialog.vbox.pack_start(label, expand=False, padding=8)
    dialog.vbox.pack_start(sw, expand=False)

    # move dialog to where the mouse pointer is
    rootwin = widget.get_screen().get_root_window()
    x, y, mods = rootwin.get_pointer()
    dialog.move(x, y)

    show_all_local_widgets(locals())
    response = dialog.run()

    # get text before destroying the dialog
    buf = ci.get_buffer()
    msg_str = buf.get_text(*buf.get_bounds())

    dialog.destroy() # destroy the dialog first so it doesn't show up in screenshot

    if response == gtk.RESPONSE_ACCEPT: # 'OK' button pressed
      # don't allow empty commit messages
      if msg_str:
        self.push_commit_event(msg_str, is_happy)


  def push_commit_event(self, msg_str, is_happy):
    now = get_ms_since_epoch()
    now_dt = encode_datetime(now)
    if is_happy:
      prefix = 'happy'
    else:
      prefix = 'sad'
    output_filename = os.path.join(SCREENSHOTS_DIR, 'screenshot-%s.%d.png' % (prefix, now))
    save_screenshot(output_filename)
    if is_happy:
      n = HappyFaceFeedEvent(HappyFaceEvent(msg_str, now_dt, self.cur_session, output_filename))
    else:
      n = SadFaceFeedEvent(SadFaceEvent(msg_str, now_dt, self.cur_session, output_filename))
    bff.push_feed_event(n)
    n.save_to_db() # very important!!!


  def timer_interrupt(self):
    # update BEFORE polling for events
    db_last_updated_time = None
    e = self.db.session_status.find_one({'_id': self.cur_session})
    if e:
      db_last_updated_time = e['last_updated_time']


    if db_last_updated_time != self.cur_db_last_updated_time:
      if self.cur_db_last_updated_time:
        assert db_last_updated_time > self.cur_db_last_updated_time

      self.prev_db_last_updated_time = self.cur_db_last_updated_time
      self.cur_db_last_updated_time = db_last_updated_time

    #print 'Prev:', self.prev_db_last_updated_time
    #print 'Cur: ', self.cur_db_last_updated_time
    #print

    self.poll_for_all_event_updates()

    self.update_all_timestamps()

    # now we've presumably pulled all MongoDB events up to
    # self.prev_db_last_updated_time, so push it forward:
    self.prev_db_last_updated_time = self.cur_db_last_updated_time

    return True # to keep timer interrupts firing


  def main(self):
    gtk.main()


def exit_handler():
  global bff
  bff.fvm.memoize_checkpoints()
  bff.fvm.unmount_all_snapshots()


if __name__ == "__main__":
  if len(sys.argv) > 1:
    cur_session = sys.argv[1]
  else:
    # if you don't pass in an argument, then use the CONTENTS of
    # /var/log/burrito/current-session as the session tag
    cur_session = os.readlink('/var/log/burrito/current-session').strip()

  assert cur_session[-1] != '/' # don't have a weird trailing slash!

  SCREENSHOTS_DIR = '/var/log/burrito/%s/' % cur_session
  assert os.path.isdir(SCREENSHOTS_DIR)

  # have tooltips pop up fairly quickly
  gtk.settings_get_default().set_long_property('gtk-tooltip-timeout', 300, '')

  bff = BurritoFeed(cur_session)

  atexit.register(exit_handler)
  signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run

  bff.timer_interrupt() # call it once on start-up
  gobject.timeout_add(5000, bff.timer_interrupt)
  bff.main() # infinite loop!!!


########NEW FILE########
__FILENAME__ = event_fetcher
# Functions to fetch events from the master MongoDB burrito_db database

'''
File version annotations are stored in:

  burrito_db.annotations.file_annotations

with schema:
  _id: <filename>-<timestamp.isoformat()>
  filename: absolute path to file
  timestamp: datetime object
  annotation: string annotation
  session_tag: session ID


Status update posts are stored in:
  
  burrito_db.annotations.happy_face
  burrito_db.annotations.sad_face
  burrito_db.annotations.status

with schema:
  _id: timestamp
  annotation: comment
  screenshot_filename: full filename of PNG screenshot (only for happy_face and sad_face)
  session_tag: session ID


Webpage and bash command annotations are stored as 'annotation' fields
within their respective original collections.

  burrito_db.gui_trace (for webpage events)
  burrito_db.apps.bash (for bash events)
'''

from pymongo import Connection
c = Connection()
db = c.burrito_db

import sys
sys.path.insert(0, '../../GUItracing/')
from parse_gui_trace import DesktopState

import os, md5

# only display file events for processes with the user's own UID (and
# not, say, system daemons)
MY_UID = os.getuid()


# TODO: make this user-customizable!!!

# ignore certain boring commands, like 'cd', since that simply
# changes pwd and can lead to a proliferation of boring entries
IGNORED_BASH_COMMANDS = set(['cd', 'echo'])

IGNORED_PROCESSES    = set(['xpad', 'stapio', 'gconfd-2'])
IGNORE_PATH_PREFIXES = ['/home/researcher/.', '/tmp/', '/var/', 'PIPE-']

# right now there's NO POINT in displaying files that aren't in /home,
# since those files aren't being versioned by NILFS anyways
HOMEDIR_PREFIX = '/home/'

def ignore_file(filename):
  if not filename.startswith(HOMEDIR_PREFIX):
    return True

  for p in IGNORE_PATH_PREFIXES:
    if filename.startswith(p):
      return True
  return False


# my MongoDB schema overloads timestamp as either a single element
# or a string (kind of an ugly premature optimization, I suppose!)
def get_timestamp_lst(timestamp_field):
  if type(timestamp_field) is list:
    return timestamp_field
  else:
    return [timestamp_field]


class WebpageVisitEvent:
  def __init__(self, title, url, timestamp):
    self.title = title
    self.url = url
    self.timestamp = timestamp
    self.mongodb_collection = db.gui_trace


  # returns a pair: (entire GUI trace object, active window)
  def __get_db_active_window(self):
    m = self.mongodb_collection.find_one({'_id': self.timestamp})
    assert m # should always be found, or we have a problem!
    # find the active GUI window ... GROSS!!!
    active_app_id = m['active_app_id']
    active_window_index = m['active_window_index']
    for a in m['apps']:
      if a['app_id'] == active_app_id:
        for w in a['app']['windows']:
          if w['window_index'] == active_window_index:
            window_dict = w['window']
            return (m, window_dict)
    assert False

  def get_hashtag(self):
    return '#web-' + md5.md5(self.timestamp.isoformat()).hexdigest()[:10] # make it short


  def insert_annotation(self, annotation):
    (gui_trace_obj, active_window_dict) = self.__get_db_active_window()
    active_window_dict['annotation'] = annotation
    # write the WHOLE element back into the database
    self.mongodb_collection.update({'_id': self.timestamp}, gui_trace_obj,
                                   False, False)

  def delete_annotation(self):
    (gui_trace_obj, active_window_dict) = self.__get_db_active_window()
    if 'annotation' in active_window_dict:
      del active_window_dict['annotation']
      # write the WHOLE element back into the database
      self.mongodb_collection.update({'_id': self.timestamp}, gui_trace_obj,
                                     False, False)

  def load_annotation(self):
    (gui_trace_obj, active_window_dict) = self.__get_db_active_window()
    if 'annotation' in active_window_dict:
      return active_window_dict['annotation']
    else:
      return ''

  def printme(self):
    print 'WEB:\t%s "%s"' % (str(self.timestamp), self.title.encode('ascii', 'replace'))


class BashCommandEvent:
  def __init__(self, cmd, pwd, timestamp):
    self.cmd = cmd # a list of all arguments
    self.pwd = pwd
    self.timestamp = timestamp
    self.mongodb_collection = db.apps.bash

  def get_hashtag(self):
    return '#bash-' + md5.md5(self.timestamp.isoformat()).hexdigest()[:10] # make it short

  def insert_annotation(self, annotation):
    self.mongodb_collection.update({'_id': self.timestamp},
                                   {'$set':{'annotation':annotation}}, False, False)

  def delete_annotation(self):
    self.mongodb_collection.update({'_id': self.timestamp},
                                   {'$unset':{'annotation':1}}, False, False)

  def load_annotation(self):
    # try to load the 'annotation' field from the database:
    m = self.mongodb_collection.find_one({'_id':self.timestamp}, {'annotation':1})
    if m and 'annotation' in m: 
      return m['annotation']
    else:
      return ''

  def printme(self):
    print 'BASH:\t%s %s' % (str(self.timestamp), ' '.join(self.cmd))


class FileProvenanceEvent:
  def __init__(self, timestamp, pid, phase_name, session_tag):
    self.timestamp = timestamp
    self.pid = pid

    # remember that a process can have multiple phases when there are
    # multiple execve calls
    self.phase_name = phase_name
    self.mongodb_collection = db.annotations.file_annotations
    self.session_tag = session_tag


  # remember we're annotating a particular version of a file, so make
  # the _id field as the concatenation of the timestamp and filename
  def insert_annotation(self, annotation):
    fn = self.filename
    self.mongodb_collection.save({'_id': fn + '-' + self.timestamp.isoformat(),
                                  'filename': fn,
                                  'timestamp': self.timestamp,
                                  'annotation': annotation,
                                  'session_tag': self.session_tag})

  def delete_annotation(self):
    fn = self.filename
    self.mongodb_collection.remove({'_id': fn + '-' + self.timestamp.isoformat()})

  def load_annotation(self):
    fn = self.filename
    m = self.mongodb_collection.find_one({'_id': fn + '-' + self.timestamp.isoformat()})
    if m:
      return m['annotation']
    else:
      return ''

  # kind of a dumb hashtag, but whatever ...
  def get_hashtag(self):
    id_tuple = self.get_unique_id()
    return '#file-' + md5.md5(str(id_tuple)).hexdigest()[:10] # make it SHORT


class FileReadEvent(FileProvenanceEvent):
  def __init__(self, filename, timestamp, pid, phase_name, session_tag):
    FileProvenanceEvent.__init__(self, timestamp, pid, phase_name, session_tag)
    self.filename = filename

  # create a unique identifier that can be used for de-duplication:
  def get_unique_id(self):
    return ('file_read', self.pid, self.phase_name, self.filename, self.timestamp)

  def printme(self):
    print 'READ:\t%s [PID: %s] %s' % (str(self.timestamp), self.pid, self.filename)


class FileWriteEvent(FileProvenanceEvent):
  def __init__(self, filename, timestamp, pid, phase_name, session_tag):
    FileProvenanceEvent.__init__(self, timestamp, pid, phase_name, session_tag)
    self.filename = filename

  # create a unique identifier that can be used for de-duplication:
  def get_unique_id(self):
    return ('file_write', self.pid, self.phase_name, self.filename, self.timestamp)

  def printme(self):
    print 'WRITE:\t%s [PID: %s] %s' % (str(self.timestamp), self.pid, self.filename)


class DoodleSaveEvent(FileWriteEvent):
  def __init__(self, filename, timestamp, pid, phase_name, session_tag):
    FileWriteEvent.__init__(self, filename, timestamp, pid, phase_name, session_tag)

  def printme(self):
    print 'DOODLE:\t%s [PID: %s] %s' % (str(self.timestamp), self.pid, self.filename)


# Given an entry from the burrito_db.db.gui_trace collection, either
# create a new WebpageVisitEvent or None, if there's no webpage visit
def fetch_webpage_visit_event(gui_trace_elt):
  timestamp = gui_trace_elt['_id']
  desktop_state = DesktopState.from_mongodb(gui_trace_elt)
  active_w = desktop_state.get_first_active_window()

  # ignore non-existent or empty URLs:
  if hasattr(active_w, 'browserURL') and active_w.browserURL:
    prettified_URL = active_w.browserURL
    # urlparse needs a URL to start with something like 'http://'
    if not prettified_URL.startswith('http://') and \
       not prettified_URL.startswith('https://'):
      prettified_URL = 'http://' + prettified_URL

    prettified_title = active_w.title

    # special hacks for Google Chrome:
    if prettified_title.endswith(' - Google Chrome'):
      prettified_title = prettified_title[:(-1 * len(' - Google Chrome'))]
    if prettified_title == 'New Tab':
      return None
    if active_w.browserURL == u'\u200b': # weird EMPTY URL string in Chrome
      return None

    return WebpageVisitEvent(prettified_title, prettified_URL, timestamp)

  return None


# Given an entry from the burrito_db.apps.bash collection, either create
# a new BashCommandEvent or None, if there's no valid event
def fetch_bash_command_event(bash_trace_elt):
  timestamp  = bash_trace_elt['_id']
  my_pwd = bash_trace_elt['pwd']
  cmd_components = bash_trace_elt['command']

  if cmd_components[0] in IGNORED_BASH_COMMANDS:
    return None

  return BashCommandEvent(cmd_components, my_pwd, timestamp)


# Given an entry from the burrito_db.process_trace collection, then
# create a (possibly-empty) list of FileProvenanceEvent objects
def fetch_file_prov_event_lst(process_trace_elt, session_tag):
  ret = []

  # only match the user's own processes!
  if process_trace_elt['uid'] != MY_UID:
    return ret

  pid = process_trace_elt['pid']

  for phase in process_trace_elt['phases']:
    phase_name = phase['name']

    if phase_name in IGNORED_PROCESSES:
      continue

    if phase['files_read']:
      for e in phase['files_read']:
        fn = e['filename']
        if not ignore_file(fn):
          for t in get_timestamp_lst(e['timestamp']):
            ret.append(FileReadEvent(fn, t, pid, phase_name, session_tag))

    if phase['files_written']:
      for e in phase['files_written']:
        fn = e['filename']
        if not ignore_file(fn):
          for t in get_timestamp_lst(e['timestamp']):
            # create a special DoodleSaveEvent if phase_name is
            # gnome-paint, since that represents a doodle (sketch)!
            if phase_name == 'gnome-paint':
              evt = DoodleSaveEvent(fn, t, pid, phase_name, session_tag)
            else:
              evt = FileWriteEvent(fn, t, pid, phase_name, session_tag)
            ret.append(evt)

    if phase['files_renamed']:
      for e in phase['files_renamed']:
        old_fn = e['old_filename']
        new_fn = e['new_filename']

        # create a virtual 'read' for old_fn and a virtual 'write' for new_fn

        if not ignore_file(old_fn):
          for t in get_timestamp_lst(e['timestamp']):
            ret.append(FileReadEvent(old_fn, t, pid, phase_name, session_tag))

        if not ignore_file(new_fn):
          for t in get_timestamp_lst(e['timestamp']):
            ret.append(FileWriteEvent(new_fn, t, pid, phase_name, session_tag))

  return ret



class ToplevelAnnotationEvent:
  def __init__(self, annotation, timestamp, session_tag, screenshot_filename=None):
    self.annotation = annotation
    self.timestamp = timestamp
    self.session_tag = session_tag
    self.screenshot_filename = screenshot_filename

  def serialize(self):
    return {'_id': self.timestamp,
            'screenshot_filename': self.screenshot_filename,
            'annotation': self.annotation,
            'session_tag': self.session_tag}


class HappyFaceEvent(ToplevelAnnotationEvent):
  def __init__(self, annotation, timestamp, session_tag, screenshot_filename):
    ToplevelAnnotationEvent.__init__(self, annotation, timestamp, session_tag, screenshot_filename)

  def save_to_db(self):
    db.annotations.happy_face.save(self.serialize())

  def get_hashtag(self):
    return '#happy-' + md5.md5(self.timestamp.isoformat()).hexdigest()[:10] # make it short

  def printme(self):
    print 'HAPPY:', self.timestamp, self.annotation


class SadFaceEvent(ToplevelAnnotationEvent):
  def __init__(self, annotation, timestamp, session_tag, screenshot_filename):
    ToplevelAnnotationEvent.__init__(self, annotation, timestamp, session_tag, screenshot_filename)

  def save_to_db(self):
    db.annotations.sad_face.save(self.serialize())

  def get_hashtag(self):
    return '#sad-' + md5.md5(self.timestamp.isoformat()).hexdigest()[:10] # make it short

  def printme(self):
    print 'SAD:', self.timestamp, self.annotation


class StatusUpdateEvent(ToplevelAnnotationEvent):
  def __init__(self, annotation, timestamp, session_tag):
    ToplevelAnnotationEvent.__init__(self, annotation, timestamp, session_tag)

  def save_to_db(self):
    db.annotations.status.save(self.serialize())

  def get_hashtag(self):
    return '#status-' + md5.md5(self.timestamp.isoformat()).hexdigest()[:10] # make it short

  def printme(self):
    print 'STATUS_UPDATE:', self.timestamp, self.annotation


def fetch_toplevel_annotation_events(session_tag):
  ret = []

  for m in db.annotations.happy_face.find({'session_tag': session_tag}):
    ret.append(HappyFaceEvent(m['annotation'], m['_id'], m['session_tag'], m['screenshot_filename']))

  for m in db.annotations.sad_face.find({'session_tag': session_tag}):
    ret.append(SadFaceEvent(m['annotation'], m['_id'], m['session_tag'], m['screenshot_filename']))

  for m in db.annotations.status.find({'session_tag': session_tag}):
    ret.append(StatusUpdateEvent(m['annotation'], m['_id'], m['session_tag']))

  return ret


# somewhat gimpy
class ActiveGUIWindowEvent:
  def __init__(self, desktop_state, timestamp):
    self.desktop_state = desktop_state
    self.timestamp = timestamp

    active_windows_lst = desktop_state.get_active_windows()
    assert len(active_windows_lst) == 1
    active_appID, active_windowIndex = active_windows_lst[0]

    active_app = desktop_state[active_appID]
    active_window = active_app[active_windowIndex]

    self.active_app_pid = active_app.pid
    self.active_window_title = active_window.title

  def printme(self):
    print 'GUI:\t%s [PID: %s] "%s"' % (str(self.timestamp), str(self.active_app_pid), self.active_window_title)


def fetch_active_gui_window_event(gui_trace_elt):
  timestamp = gui_trace_elt['_id']
  desktop_state = DesktopState.from_mongodb(gui_trace_elt)

  if desktop_state.num_active_windows() > 0:
    return ActiveGUIWindowEvent(desktop_state, timestamp)
  else:
    return None


class ActiveVimBufferEvent:
  def __init__(self, pid, filename, timestamp):
    self.pid = pid
    self.filename = filename
    self.timestamp = timestamp

  def printme(self):
    print 'VIM:\t%s [PID: %s] %s' % (str(self.timestamp), str(self.pid), self.filename)


def fetch_active_vim_buffer_event(vim_trace_elt):
  if vim_trace_elt['event'] == 'BufEnter':
    return ActiveVimBufferEvent(vim_trace_elt['pid'], vim_trace_elt['filename'], vim_trace_elt['_id'])
  else:
    return None


########NEW FILE########
__FILENAME__ = screenshot
# http://stackoverflow.com/questions/69645/take-a-screenshot-via-a-python-script-linux

import gtk.gdk

w = gtk.gdk.get_default_root_window()
sz = w.get_size()
print "The size of the window is %d x %d" % sz
pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8,sz[0],sz[1])
pb = pb.get_from_drawable(w,w.get_colormap(),0,0,0,0,sz[0],sz[1])
if (pb != None):
    pb.save("screenshot.png","png")
    print "Screenshot saved to screenshot.png."
else:
    print "Unable to get the screenshot."

########NEW FILE########
__FILENAME__ = file_version_manager
# File version manager for NILFS
# Created on 2011-12-15 by Philip Guo

# Heavily inspired by nilfs2_ss_manager in the TimeBrowse project by
# Jiro SEKIBA <jir@unicus.jp>


# Change this to the exact name of your LVM home partition:
NILFS_DEV_NAME = '/dev/vg_burritofedora/lv_home'



# TODO: instead of using a pickle file, simply use a MongoDB collection
# to store the lscp cached data ;)


'''
Required setup to run nilfs commands with 'sudo' WITHOUT entering a password!

Add these lines to /etc/sudoers by editing it using "sudo visudo":

  researcher      ALL=(ALL)       ALL
  researcher      ALL=NOPASSWD: /bin/mount
  researcher      ALL=NOPASSWD: /bin/umount
  researcher      ALL=NOPASSWD: /sbin/mount.nilfs2
  researcher      ALL=NOPASSWD: /sbin/umount.nilfs2
  researcher      ALL=NOPASSWD: /usr/bin/chcp
  researcher      ALL=NOPASSWD: /usr/bin/mkcp
  researcher      ALL=NOPASSWD: /usr/bin/rmcp

The first line gives user 'researcher' full sudo access.  All subsequent
lines say that 'researcher' can run those commands as 'sudo' WITHOUT
TYPING A PASSWORD!  Note that those commands still must be run as
'sudo', but no password is required :)
'''

import nilfs2
import os, sys, datetime
import commands
import cPickle

import atexit
from signal import signal, SIGTERM


NILFS_SNAPSHOT_BASE = '/tmp/nilfs-snapshots'
assert os.path.isdir(NILFS_SNAPSHOT_BASE)

assert os.path.exists(NILFS_DEV_NAME)

# Note that this cached file might be outdated since the script might
# have changed some checkpoint ('cp') into a snapshot ('ss'), but that
# might not be reflected in the pickle file
CACHED_CHECKPOINTS_FILE = os.path.join(NILFS_SNAPSHOT_BASE, 'lscp.out.pickle')

HOMEDIR_PREFIX = '/home/'
ONE_SEC = datetime.timedelta(seconds=1)


class FileVersionManager:
  def __init__(self):
    self.unmount_all_snapshots() # RESET EVERYTHING UP FRONT!!!

    self.nilfs = nilfs2.NILFS2()
    self.checkpoints = []

    if os.path.isfile(CACHED_CHECKPOINTS_FILE):
      self.checkpoints = cPickle.load(open(CACHED_CHECKPOINTS_FILE))
      print >> sys.stderr, "Loaded %d cached checkpoints from %s" % (len(self.checkpoints), CACHED_CHECKPOINTS_FILE)

    self.update_checkpoints() # always do an incremental update!

    # Key: checkpoint ID
    # Value: mountpoint of snapshot
    self.active_snapshots = {}


  def memoize_checkpoints(self):
    print >> sys.stderr, "Saving %d cached checkpoints in %s" % (len(self.checkpoints), CACHED_CHECKPOINTS_FILE)
    cPickle.dump(self.checkpoints, open(CACHED_CHECKPOINTS_FILE, 'w'))


  # perform fast incremental updates using the lscp '-i' option
  def update_checkpoints(self):
    if not self.checkpoints:
      self.checkpoints = self.nilfs.lscp()
    else:
      last_checkpoint_id = self.checkpoints[-1]['cno']
      # start a 1 beyond last_checkpoint_id to prevent dups!!!
      new_checkpoints = self.nilfs.lscp(index=last_checkpoint_id+1)
      self.checkpoints.extend(new_checkpoints)

    # sanity check
    lst = [e['cno'] for e in self.checkpoints]
    assert lst == sorted(lst)


  # returns the checked-out mountpoint on success (or None on failure)
  # which represents the last mountpoint occurring BEFORE timestamp
  #
  # however, this isn't totally accurate, because NILFS timestamps only
  # have second-level granularity, but timestamps issued by client
  # applications could have microsecond granularity.  e.g., if the
  # actual timestamp of a snapshot is at 1:15.90, then NILFS stores it
  # as 1:15.  So checkout_snapshot(self, 1:15.10) will return that 1:15
  # snapshot, even though its ACTUAL timestamp (1:15.90) is after the
  # timestamp argument.  to be more safe, subtact 1 second from timestamp
  # BEFORE passing it into this function.
  def checkout_snapshot(self, timestamp):
    self.update_checkpoints() # make sure we're up-to-date!

    # TODO: optimize to binary search if necessary
    prev = None
    for e in self.checkpoints:
      if e['date'] > timestamp:
        break
      prev = e

    # prev stores the latest checkpoint with time <= timestamp
    target_checkpoint_num = prev['cno']
    target_checkpoint_date = prev['date']

    mountpoint = os.path.join(NILFS_SNAPSHOT_BASE, target_checkpoint_date.strftime("%Y.%m.%d-%H.%M.%S"))

    # fast path ...
    if target_checkpoint_num in self.active_snapshots:
      assert os.path.isdir(mountpoint)
      return mountpoint # already mounted (presumably)

    os.mkdir(mountpoint)

    # first make sure it's a snapshot, so we can mount it:
    if not prev['ss']:
      self.nilfs.chcp(target_checkpoint_num, True)
      prev['ss'] = True

    mount_cmd = 'sudo mount -t nilfs2 -n -o ro,cp=%d "%s" "%s"' % (target_checkpoint_num, NILFS_DEV_NAME, mountpoint)
    (status, output) = commands.getstatusoutput(mount_cmd)
    if output:
      print output

    if (status == 0):
      self.active_snapshots[target_checkpoint_num] = mountpoint
      return mountpoint
    else:
      return None


  # returns the path of the checked-out file
  def checkout_file(self, filename, timestamp):
    snapshot_dir = self.checkout_snapshot(timestamp)

    # find the version of filename within snapshot_dir
    # strip HOMEDIR_PREFIX off of filename ...
    assert filename.startswith(HOMEDIR_PREFIX)
    decapitated_fn = filename[len(HOMEDIR_PREFIX):]

    old_version_path = os.path.join(snapshot_dir, decapitated_fn)
    return old_version_path


  # This is kinda kludgy because it depends on event_fetcher.py
  def checkout_file_before_next_write(self, write_evt, sorted_write_events_lst):
    # Complex pre-conditions:
    # (TODO: eliminate checks if too slow)
    assert write_evt in sorted_write_events_lst
    assert sorted(sorted_write_events_lst, key=lambda e:e.timestamp) == sorted_write_events_lst
    for e in sorted_write_events_lst: assert write_evt.filename == e.filename

    # Retrieves the timestamp RIGHT BEFORE the next write to filename.  The
    # reason why we need to do this is due to pass-lite's write coalescing
    # optimization.  If we just get the snapshot at evt.timestamp, that might
    # not be the timestamp of the LAST write in a series of writes to the same
    # file descriptor.  Consider the case where it takes 10 seconds to
    # completely save a file foo.txt.  If the first write occurred at time t,
    # then evt.timestamp will be t, but the version at time t isn't the
    # complete foo.txt.  In order to get the complete foo.txt, we need to get
    # the version at time t+10.  However, we don't know that it took 10
    # seconds to write the file, since pass-lite coalesced all of the (tons
    # of) writes into ONE write at time t.  So the best we can do is to find
    # the NEXT time that this file was written to and return a timestamp right
    # before its timestamp.
    #
    # return None if this is the most recent write, so there's NO successor
    def get_before_next_write_timestamp():
      # TODO: optimize with a sub-linear search if necessary
      idx = sorted_write_events_lst.index(write_evt)
      num_writes = len(sorted_write_events_lst)

      assert 0 <= idx < num_writes

      # if we're the LAST one, then return None
      if idx == num_writes - 1:
        return None
      else:
        next_evt = sorted_write_events_lst[idx + 1]

        assert next_evt.timestamp - write_evt.timestamp >= ONE_SEC

        # subtract one second to get the "epsilon" before the next write
        ret = next_evt.timestamp - ONE_SEC
        return ret

    event_time = get_before_next_write_timestamp()
    if event_time:
      return self.checkout_file(write_evt.filename, event_time)
    else:
      # eee, the current working version IS what we want!
      return write_evt.filename


  def unmount_all_snapshots(self):
    for d in os.listdir(NILFS_SNAPSHOT_BASE):
      fullpath = os.path.join(NILFS_SNAPSHOT_BASE, d)
      if os.path.isdir(fullpath):
        commands.getstatusoutput('sudo umount ' + fullpath)
        os.rmdir(fullpath)


def exit_handler():
  global fvm
  fvm.memoize_checkpoints()
  fvm.unmount_all_snapshots()


if __name__ == '__main__':
  fvm = FileVersionManager()
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 9, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 10, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 11, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 12, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 13, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 14, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 15, 0, 0))
  print fvm.checkout_snapshot(datetime.datetime(2011, 12, 15, 16, 0, 0))
  #fvm.unmount_all_snapshots()

  atexit.register(exit_handler)
  signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run

  sys.exit(0)

  import time

  print 'updating ...',
  sys.stdout.flush()
  fvm.update_checkpoints()
  print len(fvm.checkpoints)
  time.sleep(5)

  print 'updating ...',
  sys.stdout.flush()
  fvm.update_checkpoints()
  print len(fvm.checkpoints)
  time.sleep(5)

  print 'updating ...',
  sys.stdout.flush()
  fvm.update_checkpoints()
  print len(fvm.checkpoints)


########NEW FILE########
__FILENAME__ = html_utils
MY_CSS = '''
body
{
  margin-left: 20px;
  margin-top: 15px;
  background-color: white;
  font-family: verdana, arial, helvetica, sans-serif;
  font-size: 10pt;
}

td.header {
  font-size: 12pt;
  font-weight: bold;
  text-align: center;
}

td {
  border-bottom: 1px solid #cccccc;
  border-left: 1px solid #cccccc;
  padding: 10px;
  font-size: 10pt;
}

h1 {
  font-size: 18pt;
}

h2 {
  font-size: 14pt;
}
'''


########NEW FILE########
__FILENAME__ = nilfs2
# Code originally taken from the TimeBrowse project:
#   http://sourceforge.net/projects/timebrowse/
# and then adapted by Philip Guo

#!/usr/bin/env python
#
# copyright(c) 2011 - Jiro SEKIBA <jir@unicus.jp>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#

"""NILFS2 module"""

__author__    = "Jiro SEKIBA"
__copyright__ = "Copyright (c) 2011 - Jiro SEKIBA <jir@unicus.jp>"
__license__   = "LGPL"
__version__   = "0.6"

import commands
import re
import datetime

class NILFS2:
    # if you don't pass in a device name, nilfs tools will look in
    # /proc/mounts, so if there's exactly ONE nilfs FS mounted on
    # your machine, then you're fine!
    def __init__(self, device=''):
        self.cpinfo_regex = re.compile(
            r'^ +([1-9]|[1-9][0-9]+) +([^ ]+ [^ ]+) +(ss|cp) +([^ ]+) +.*$',
            re.M)
        self.device = device

    def __run_cmd__(self, line):
        result = commands.getstatusoutput(line)
        if result[0] != 0:
            raise Exception(result[1])
        return result[1]

    def __parse_lscp_output__(self, output):
        a = self.cpinfo_regex.findall(output)

        a = [ {'cno'  : int(e[0]),
               'date' : datetime.datetime.strptime(e[1], "%Y-%m-%d %H:%M:%S"),
               'ss'  : e[2] == 'ss'}
               for e in a if e[3] != 'i' ] # don't count internal ('i') checkpoints

        if not a:
            return []

        return a
        
        '''
        # Drop checkpoints that have the same timestamp with its
        # predecessor.  If a snapshot is present in the series of
        # coinstantaneous checkpoints, we leave it rather than plain
        # checkpoints.
        prev = a.pop(0)
        if not a:
            return [prev]

        ss = prev if prev['ss'] else None
        l = []
        for e in a:
            if e['date'] != prev['date']:
                l.append(ss if ss else prev)
                ss = None
            prev = e
            if prev['ss']:
                ss = prev
        l.append(ss if ss else a[-1])
        '''
        return l

    def lscp(self, index=1):
        result = self.__run_cmd__("lscp -i %d %s" % (index, self.device))
        return self.__parse_lscp_output__(result)

    def chcp(self, cno, ss=False):
        line = "chcp cp "
        if ss:
            line = "chcp ss "
        line += self.device + " %i" % cno
        line = 'sudo ' + line # run as sudo!!!
        return self.__run_cmd__(line)

    def mkcp(self, ss=False):
        line = "mkcp"
        if ss:
            line += " -s"
        line += " " + self.device
        line = 'sudo ' + line # run as sudo!!!
        return self.__run_cmd__(line)


if __name__ == '__main__':
  import sys
  nilfs = NILFS2()
  all_checkpoints = nilfs.lscp()

  prev = None
  for e in all_checkpoints:
    print e['cno'], e['date'],
    if prev and prev['date'] == e['date']:
      print "UGH!"
    else:
      print

    prev = e


########NEW FILE########
__FILENAME__ = output_file_prov_viewer
# Output file provenance viewer, showing a tabular view where each row consists of:
#
# 1.) Input code files (diffs from baseline)
# 2.) Command parameters
# 3.) Output file
# 4.) Annotations


# TODO: support filtering by a time range rather than just a session tag


import pygtk
pygtk.require('2.0')
import gtk, pango, gobject

import os, sys
import datetime
import filecmp
import difflib
import mimetypes

import cgi

from pymongo import Connection, ASCENDING, DESCENDING

from pygtk_burrito_utils import *

from BurritoUtils import *
from urlparse import urlparse

sys.path.insert(0, '../../GUItracing/')

from annotation_component import AnnotationComponent
from event_fetcher import *
from collections import defaultdict

import atexit
from signal import signal, SIGTERM

from file_version_manager import FileVersionManager

import source_file_prov_viewer
import burrito_feed


# KLUDGY GLOBAL :(
diff_left_half = None
diff_menu_items = [] # really kludgy!


# Represents a command invocation that involves reading some input files
# and writing ONE particular output file.
# (Note that the command might write additional output files, but for
# the purposes of the file provenance viewer, we are only focused on ONE
# output file.)
class CommandInvocation:
  def __init__(self, cmd_event, read_event_lst, output_event, sorted_write_events_lst, fvm, session_tag):
    self.cmd_event = cmd_event           # type: BashCommandEvent
    self.read_event_lst = read_event_lst # type: list of FileReadEvent
    self.output_event = output_event     # type: FileWriteEvent
    self.fvm = fvm                       # type: FileVersionManager
    self.sorted_write_events_lst = sorted_write_events_lst # type: list of FileWriteEvent
    self.session_tag = session_tag


  def get_output_filename(self):
    return self.output_event.filename

  def get_timestamp(self):
    return self.cmd_event.timestamp

  def view_file_version(self, _ignore, read_evt):
    # gnome-open to the rescue!!!  uses a file's type to determine the
    # proper viewer application :)
    old_version_path = self.fvm.checkout_file(read_evt.filename, read_evt.timestamp)
    if not os.path.isfile(old_version_path):
      d = gtk.MessageDialog(None,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_ERROR,
                            gtk.BUTTONS_OK,
                            message_format="File not found:\n" + old_version_path)
      d.run()
      d.destroy()
    else:
      os.system('gnome-open "%s" &' % old_version_path)


  def mark_for_diff(self, _ignore, read_evt):
    global diff_left_half, diff_menu_items
    if not diff_left_half:
      diff_left_half = read_evt

      for e in diff_menu_items:
        e.set_label('Diff against selected file')
    else:
      diff_left_half_path = self.fvm.checkout_file(diff_left_half.filename,
                                                   diff_left_half.timestamp)
      diff_right_half_path = self.fvm.checkout_file(read_evt.filename,
                                                    read_evt.timestamp)

      os.system('meld "%s" "%s" &' % (diff_left_half_path, diff_right_half_path))

      # reset!
      diff_left_half = None
      for e in diff_menu_items:
        e.set_label('Select for diff')


  def view_source_prov(self, _ignore, read_evt):
    spv = source_file_prov_viewer.SourceFileProvViewer(read_evt.filename,
                                                       self.session_tag,
                                                       self.fvm)


  # returns a string representing the diff of all input files
  # (the Python HTML diff option looks really ugly, so don't use it!)
  def diff_input_files(self, other):
    unchanged_files = []

    diff_result = []

    for cur_re in self.read_event_lst:
      cur_filepath = self.fvm.checkout_file(cur_re.filename, cur_re.timestamp)

      for other_re in other.read_event_lst:
        if other_re.filename == cur_re.filename:
          other_filepath = self.fvm.checkout_file(other_re.filename, other_re.timestamp)

          if filecmp.cmp(cur_filepath, other_filepath):
            unchanged_files.append(cur_re.filename)

          else:
            # there's a diff, so print if possible

            # render 'other' first!
            d = difflib.unified_diff(open(other_filepath, 'U').readlines(),
                                     open(cur_filepath, 'U').readlines(),
                                     prettify_filename(other_re.filename),
                                     prettify_filename(cur_re.filename),
                                     other_re.timestamp,
                                     cur_re.timestamp)
            diff_result.extend([line for line in d])

          break # break after first match


    # tack all unchanged files on at the end
    for e in unchanged_files:
      diff_result.append('\nUNCHANGED: ' + prettify_filename(e))

    diff_result_str = ''.join(diff_result) # each line already has trailing '\n'
    return diff_result_str


  def diff_output_file(self, cur_output_filepath, other):
    other_output_filepath = self.fvm.checkout_file_before_next_write(other.output_event,
                                                                     other.sorted_write_events_lst)

    # display diff
    if filecmp.cmp(cur_output_filepath, other_output_filepath):
      str_to_display = 'UNCHANGED'
    else:
      # render 'other' first!
      d = difflib.unified_diff(open(other_output_filepath, 'U').readlines(),
                               open(cur_output_filepath, 'U').readlines(),
                               prettify_filename(self.get_output_filename()),
                               prettify_filename(self.get_output_filename()),
                               other.get_timestamp(),
                               self.get_timestamp())

      str_to_display = ''.join([line for line in d])

    return str_to_display


  def render_table_row(self, prev_cmd_invocation, tbl, row_index):
    XPADDING=8
    YPADDING=15
    # using "yoptions=gtk.SHRINK" in table.attach seems to do the trick
    # in not having the table cells expand vertically like nuts

    # Print inputs:

    widgets = []

    for re in self.read_event_lst:
      lab = gtk.Label(prettify_filename(re.filename))
      lab.modify_font(pango.FontDescription("monospace 9"))
      lab.show()

      menu = gtk.Menu()

      view_item = gtk.MenuItem('Open')
      view_item.connect("activate", self.view_file_version, re)
      view_item.show()
      mark_diff_item = gtk.MenuItem('Select for diff')
      mark_diff_item.connect("activate", self.mark_for_diff, re)
      mark_diff_item.show()
      prov_item = gtk.MenuItem('View source file provenance')
      prov_item.connect("activate", self.view_source_prov, re)
      prov_item.show()
      menu.append(view_item)
      menu.append(mark_diff_item)
      menu.append(prov_item)

      global diff_menu_items
      diff_menu_items.append(mark_diff_item)

      lab_box = create_clickable_event_box(lab, menu)
      lab_box.show()

      lab_align = create_alignment(lab_box, pbottom=5)
      lab_align.show()
      widgets.append(lab_align)

    if prev_cmd_invocation:
      diff_result_str = self.diff_input_files(prev_cmd_invocation)

      # TODO: adjust height based on existing height of row/column
      text_widget = create_simple_text_view_widget(diff_result_str, 400, 200)
      #text_widget = create_simple_text_view_widget(diff_result_str, 500, 300)

      widgets.append(text_widget)

    input_vbox = create_vbox(widgets)
    tbl.attach(input_vbox, 0, 1, row_index, row_index+1,
               xpadding=XPADDING + 5,
               ypadding=YPADDING,
               yoptions=gtk.SHRINK)
   

    # Print command:

    # cool that we get to re-use BashFeedEvent objects
    n = burrito_feed.BashFeedEvent(self.cmd_event.pwd)
    n.add_command_chron_order(self.cmd_event)

    # make it not expand like crazy in either the horizontal or vertical directions
    tbl.attach(n.get_widget(), 1, 2, row_index, row_index+1, xpadding=XPADDING, ypadding=YPADDING,
               xoptions=gtk.SHRINK, yoptions=gtk.SHRINK)

    # Print output:
    mime_type_guess = mimetypes.guess_type(self.get_output_filename())[0]

    cur_output_filepath = self.fvm.checkout_file_before_next_write(self.output_event,
                                                                   self.sorted_write_events_lst)

    if 'image/' in mime_type_guess:
      output_image = gtk.Image()
      output_image.set_from_file(cur_output_filepath)
      tbl.attach(output_image, 2, 3, row_index, row_index+1, xpadding=XPADDING, ypadding=YPADDING, yoptions=gtk.SHRINK)

    elif 'text/' in mime_type_guess:
      if prev_cmd_invocation:
        str_to_display = self.diff_output_file(cur_output_filepath, prev_cmd_invocation)
      else:
        # display entire file contents:
        str_to_display = open(cur_output_filepath, 'U').read()

      text_widget = create_simple_text_view_widget(str_to_display, 500, 350)
      tbl.attach(text_widget, 2, 3, row_index, row_index+1, xpadding=XPADDING, ypadding=YPADDING, yoptions=gtk.SHRINK)


    # Print annotations associated with self.output_event:
    annotator = AnnotationComponent(300, self.output_event, '<Click to enter a new note>')
    tbl.attach(annotator.get_widget(), 3, 4, row_index, row_index+1, xpadding=XPADDING, ypadding=YPADDING, yoptions=gtk.SHRINK)

    show_all_local_widgets(locals())


  def render_table_row_HTML(self, prev_cmd_invocation, fd):
    print >> fd, '<tr>'
  

    # Print input diffs
    print >> fd, '<td>'

    if prev_cmd_invocation:
      print >> fd, '<pre>'
      print >> fd, self.diff_input_files(prev_cmd_invocation)
      print >> fd, '</pre>'
    else:
      print >> fd, "<p>Initial version:</p>"
      print >> fd, '<pre>'
      for re in self.read_event_lst:
        print >> fd, prettify_filename(re.filename)
      print >> fd, '</pre>'

    print >> fd, '</td>'


    # Print command
    print >> fd, '<td>'

    print >> fd, '<pre>'
    print >> fd, self.cmd_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    print >> fd, prettify_filename(self.cmd_event.pwd)
    print >> fd
    print >> fd, ' '.join(self.cmd_event.cmd)
    print >> fd, '</pre>'

    print >> fd, '</td>'

    
    # Print output:
    print >> fd, '<td>'

    mime_type_guess = mimetypes.guess_type(self.get_output_filename())[0]

    cur_output_filepath = self.fvm.checkout_file_before_next_write(self.output_event,
                                                                   self.sorted_write_events_lst)

    if 'image/' in mime_type_guess:
      print >> fd, '<img src="%s"/>' % cur_output_filepath
    elif 'text/' in mime_type_guess:
      if prev_cmd_invocation:
        str_to_display = self.diff_output_file(cur_output_filepath, prev_cmd_invocation)
      else:
        # display entire file contents:
        str_to_display = open(cur_output_filepath, 'U').read()

      print >> fd, '<pre>'
      print >> fd, str_to_display
      print >> fd, '</pre>'


    print >> fd, '</td>'

 
    # Print notes:
    print >> fd, '<td>'
    print >> fd, cgi.escape(self.output_event.load_annotation()).replace('\n', '<br/>')
    print >> fd, '</td>'

    print >> fd, '</tr>'


class OutputFileProvViewer():
  def __init__(self, target_output_filename, session_tag, fvm):
    self.target_output_filename = target_output_filename
    self.session_tag = session_tag
    self.fvm = fvm

    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    #self.window.connect("destroy", lambda w: gtk.main_quit())

    self.window.set_title("Output file provenance viewer")
    self.window.set_border_width(0)
    set_white_background(self.window)

    self.window.resize(500, 500)
    self.window.maximize()

    # MongoDB stuff
    c = Connection()
    self.db = c.burrito_db
    db_proc_collection = self.db.process_trace
    db_bash_collection = self.db.apps.bash


    bash_events = []
    # chronological order:
    for m in db_bash_collection.find({'session_tag': session_tag}).sort('_id'):
      evt = fetch_bash_command_event(m)
      if evt:
        bash_events.append(evt)


    # fetch file provenance events

    file_prov_events = []

    for m in db_proc_collection.find({"session_tag": session_tag},
                                     {'pid':1, 'uid':1, 'phases':1}):
      evts = fetch_file_prov_event_lst(m, session_tag)
      file_prov_events.extend(evts)


    # Key: PID
    # Value: list of FileProvenanceEvent instances
    file_evts_by_pid = defaultdict(list)

    for evt in file_prov_events:
      file_evts_by_pid[evt.pid].append(evt)


    target_file_write_events = []
    for evt in file_prov_events:
      if (evt.__class__ == FileWriteEvent and \
          evt.filename == self.target_output_filename):
        target_file_write_events.append(evt)

    target_file_write_events.sort(key=lambda e:e.timestamp)

    cmd_invocation_lst = []

    for evt in target_file_write_events:
      sorted_evts = sorted(file_evts_by_pid[evt.pid], key=lambda e:e.timestamp)

      earliest_timestamp_from_pid = sorted_evts[0].timestamp

      # don't insert duplicates in file_read_events, so in essence we're
      # grabbing the FIRST read out of a series ...
      filenames_read_set = set()
      file_read_events = []

      # find files read by the corresponding process
      for e in sorted_evts:
        if e.__class__ == FileReadEvent and e.filename not in filenames_read_set:
          file_read_events.append(e)
          filenames_read_set.add(e.filename)


      # Use a time- and name-based heuristic for finding the proper bash
      # command that led to the current process.
      #
      # TODO: in the future, we can match the parent pid (ppid) of evt's
      # process to bash_pid, but we STILL can't avoid using a time-based
      # heuristic.
      bash_evts_preceeding_pid = []
      for bash_evt in bash_events:
        if bash_evt.timestamp > earliest_timestamp_from_pid:
          break
        bash_evts_preceeding_pid.append(bash_evt)

      # for now, naively assume that the most recent event preceeding
      # earliest_timestamp_from_pid is the one we want, without regards
      # for its actual name.  In the future, use evt.phase_name to try
      # to disambiguate.
      my_bash_cmd = bash_evts_preceeding_pid[-1]

      n = CommandInvocation(my_bash_cmd, file_read_events, evt, target_file_write_events, self.fvm, self.session_tag)
      cmd_invocation_lst.append(n)


    tbl = gtk.Table(rows=len(cmd_invocation_lst) + 1, columns=4)
    tbl_scroller = gtk.ScrolledWindow()
    tbl_scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    tbl_scroller.add_with_viewport(tbl)
    set_white_background(tbl_scroller.get_children()[0])

    self.window.add(tbl_scroller)

    # header row
    col1_label = gtk.Label("Inputs")
    col1_label.modify_font(pango.FontDescription("sans 12"))
    col2_label = gtk.Label("Command")
    col2_label.modify_font(pango.FontDescription("sans 12"))
    col3_label = gtk.Label("Output: " + prettify_filename(self.target_output_filename))
    col3_label.modify_font(pango.FontDescription("sans 12"))
    col4_label = gtk.Label("Notes")
    col4_label.modify_font(pango.FontDescription("sans 12"))
    tbl.attach(col1_label, 0, 1, 0, 1, ypadding=8)
    tbl.attach(col2_label, 1, 2, 0, 1, ypadding=8)
    tbl.attach(col3_label, 2, 3, 0, 1, ypadding=8)
    tbl.attach(col4_label, 3, 4, 0, 1, ypadding=8)

    # sort in reverse chronological order:
    cmd_invocation_lst.sort(key=lambda e:e.get_timestamp(), reverse=True)

    # show the window and all widgets first!!!
    show_all_local_widgets(locals())
    self.window.show()

    row_index = 1
    for (cur, prev) in zip(cmd_invocation_lst, cmd_invocation_lst[1:]):
      # ... then use this trick to update the GUI between each loop
      # iteration, since each iteration takes a second or two
      # (this will make the GUI seem more responsive, heh)
      #
      #   http://faq.pygtk.org/index.py?req=show&file=faq03.007.htp
      while gtk.events_pending(): gtk.main_iteration(False)

      print >> sys.stderr, "OutputFileProvViewer rendering row", row_index, "of", len(cmd_invocation_lst)
      cur.render_table_row(prev, tbl, row_index)

      row_index += 1


    while gtk.events_pending(): gtk.main_iteration(False)
    print >> sys.stderr, "OutputFileProvViewer rendering row", row_index, "of", len(cmd_invocation_lst)
    cmd_invocation_lst[-1].render_table_row(None, tbl, row_index) # print baseline (FIRST ENTRY)


    # TODO: make this experimental HTML export mode into an event
    # handler triggered by some button or menu selection:
    ''' 
    fd = open('/tmp/output_prov.html', 'w')
    self.print_html_header(fd)


    chronological_cmd_list = cmd_invocation_lst[::-1]

    row_index = 1
    print >> sys.stderr, "OutputFileProvViewer rendering HTML row", row_index, "of", len(chronological_cmd_list)
    chronological_cmd_list[0].render_table_row_HTML(None, fd)

    for (prev, cur) in zip(chronological_cmd_list, chronological_cmd_list[1:]):
      row_index += 1
      print >> sys.stderr, "OutputFileProvViewer rendering HTML row", row_index, "of", len(chronological_cmd_list)
      cur.render_table_row_HTML(prev, fd)

    self.print_html_footer(fd)

    fd.close()
    os.system('cp output_prov_viewer.css /tmp/ && gnome-open "/tmp/output_prov.html" &')
    ''' 


  def print_html_header(self, fd):
    print >> fd, '<html><head>'
    print >> fd, '<title>%s</title>' % "Output file provenance viewer"
    print >> fd, '<link rel="stylesheet" href="output_prov_viewer.css"/>'

    print >> fd, '</head><body>'
    print >> fd, '<h1>Output file provenance viewer</h1>'
    print >> fd, '<h2>Filename: %s</h2>' % prettify_filename(self.target_output_filename)
    print >> fd, '<table>'

    print >> fd, '<tr>'
    print >> fd, '<td class="header">Inputs</td>'
    print >> fd, '<td class="header">Command</td>'
    print >> fd, '<td class="header">Output file</td>'
    print >> fd, '<td class="header">Notes</td>'
    print >> fd, '</tr>'

  def print_html_footer(self, fd):
    print >> fd, '</table>'
    print >> fd, '</body></html>'



def exit_handler():
  global fvm
  fvm.memoize_checkpoints()
  fvm.unmount_all_snapshots()


if __name__ == '__main__':
  atexit.register(exit_handler)
  signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run

  fvm = FileVersionManager()
  filename = sys.argv[1]
  session_tag = sys.argv[2]
  OutputFileProvViewer(filename, session_tag, fvm)
  gtk.main()


########NEW FILE########
__FILENAME__ = print_html_summary
# Prints an HTML summary of a particular login session


# TODO: display annotations

# TODO: scan through annotations for hashtags (e.g., #bash-238348) and
#       highlight those as HTML hyperlinks to other parts of the
#       document (or later to other documents)

import os, sys
from pymongo import Connection
from event_fetcher import *

from collections import defaultdict
from html_utils import *


# 'Checkpoints' are indicated by:
# 1.) Happy face events
# 2.) Sad face events
# 3.) Status update posts
CHECKPOINT_TYPES = (HappyFaceEvent, SadFaceEvent, StatusUpdateEvent)

IGNORED_FILES = ['bash_burrito_to_json.py']


session_tag = sys.argv[1]

c = Connection()
db = c.burrito_db

db_bash_collection = db.apps.bash
db_proc_collection = db.process_trace
db_gui_trace = db.gui_trace


# fetch bash commands:
all_events = []
for m in db_bash_collection.find({'session_tag': session_tag}):
  evt = fetch_bash_command_event(m)
  if evt:
    all_events.append(evt)

# fetch file provenance events:
for m in db_proc_collection.find({"session_tag": session_tag},
                                 {'pid':1, 'uid':1, 'phases':1}):
  evts = fetch_file_prov_event_lst(m, session_tag)
  all_events.extend(evts)

# fetch webpage visit events:
for m in db_gui_trace.find({"session_tag": session_tag}):
  web_visit_evt = fetch_webpage_visit_event(m)
  if web_visit_evt:
    all_events.append(web_visit_evt)

# fetch checkpoint events: HappyFaceEvent, SadFaceEvent, StatusUpdateEvent
all_events.extend(fetch_toplevel_annotation_events(session_tag))


class TreeNode:
  def __init__(self, path_component):
    self.path_component = path_component
    self.children = [] # TreeNode instances

    # for leaf nodes only
    self.fullpath = None
    self.labels = set()

  def get_child(self, path_component):
    for c in self.children:
      if c.path_component == path_component:
        return c
    return None

  def add_child(self, path_component):
    self.children.append(TreeNode(path_component))

  def printme(self, indent=0):
    print (' '*indent) + self.path_component,
    if self.fullpath:
      assert self.labels
      print '|', sorted(self.labels), self.fullpath
    else:
      print
    for c in self.children:
      c.printme(indent+2)


# adds filename to the tree rooted at tree_root by decomposing its path components
def add_path(filename, tree_root, label):
  assert filename[0] == '/' # we expect absolute paths!
  toks = filename.split('/')
  assert toks[0] == ''
  toks = toks[1:]

  cur_node = tree_root
  for (idx, path_component) in enumerate(toks):
    child = cur_node.get_child(path_component)
    if not child:
      cur_node.add_child(path_component)

    child = cur_node.get_child(path_component)
    assert child
    # leaf node
    if idx == len(toks) - 1:
      child.fullpath = filename
      child.labels.add(label)
      # exit!
    else:
      cur_node = child # recurse!


# print some sensible summary of the events in evts :0
def print_summary(evts):
  webpages_visited = set() # set of tuples (url, title)

  # Key:   pwd
  # Value: set of command (tuples) run in pwd
  bash_commands = defaultdict(set)

  doodles_drawn = []

  # Decomposes a file's full path into a 'tree'
  files_read_dict = {}
  files_written_dict = {}

  file_tree = TreeNode('/')

  for e in evts:
    if e.__class__ == DoodleSaveEvent:
      doodles_drawn.append(e)
    elif e.__class__ == FileReadEvent:
      add_path(e.filename, file_tree, 'read')
    elif e.__class__ == FileWriteEvent:
      add_path(e.filename, file_tree, 'write')
    elif e.__class__ == BashCommandEvent:
      bash_commands[e.pwd].add(tuple(e.cmd))
    elif e.__class__ == WebpageVisitEvent:
      webpages_visited.add((e.url, e.title))
    else:
      assert e.__class__ in CHECKPOINT_TYPES


  for pwd in sorted(bash_commands.keys()):
    print pwd
    for cmd in sorted(bash_commands[pwd]):
      print ' ', ' '.join(cmd)
  print

  for (url, title) in sorted(webpages_visited, key=lambda e:e[1]):
    print url, title
  print

  file_tree.printme()


  for d in doodles_drawn:
    d.printme()
  print


  # the last element MIGHT be in CHECKPOINT_TYPES, but it might not be either ...
  last_evt = evts[-1]
  if last_evt.__class__ in CHECKPOINT_TYPES:
    # render the checkpoint object
    last_evt.printme()


# Phases are separated by checkpoint events, which have type CHECKPOINT_TYPES
# Each phase is itself a list of events, ending in a checkpoint event
phases = []

cur_phase = []

# big alphabetical sort!
for e in sorted(all_events, key=lambda e:e.timestamp):
  cur_phase.append(e)
  if e.__class__ in CHECKPOINT_TYPES:
    phases.append(cur_phase)
    cur_phase = []

if cur_phase: phases.append(cur_phase) # get the last one!

for p in phases:
  print '---'
  print_summary(p)


########NEW FILE########
__FILENAME__ = pygtk_burrito_utils
import gtk, pango

g_handcursor = gtk.gdk.Cursor(gtk.gdk.HAND2)

# meta-hack to call '.show()' for all local variables representing
# GUI elements in one fell swoop:
# (remember, this doesn't pick up on instance vars)
def show_all_local_widgets(my_locals):
  for (varname, val) in my_locals.iteritems():
    if isinstance(val, gtk.Object) and hasattr(val, 'show'):
      val.show()

def set_white_background(elt):
  elt.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('#ffffff'))

def show_tooltip(item, x, y, keyboard_mode, tooltip, text):
  tooltip.set_text(text)
  return True

def mouse_press_for_context_menu(widget, event):
  if event.type == gtk.gdk.BUTTON_PRESS:
    widget.popup(None, None, None, event.button, event.time)
    # Tell calling code that we have handled this event the buck stops here.
    return True
  # Tell calling code that we have not handled this event pass it on.
  return False


# wrapper for creating a Gtk Alignment object with specified padding
def create_alignment(child, ptop=0, pbottom=0, pleft=0, pright=0):
  ret = gtk.Alignment(0, 0, 0, 0)
  ret.add(child)
  ret.set_padding(ptop, pbottom, pleft, pright)
  return ret

# wrapper for packing children tightly in an hbox, with an optional
# padding parameter for each element of children
def create_hbox(children, padding=None):
  ret = gtk.HBox()
  if not padding:
    padding = [0 for e in children]
  for c, p in zip(children, padding):
    ret.pack_start(c, expand=False, padding=p)
  return ret

def create_vbox(children, padding=None):
  ret = gtk.VBox()
  if not padding:
    padding = [0 for e in children]
  for c, p in zip(children, padding):
    ret.pack_start(c, expand=False, padding=p)
  return ret


def create_clickable_event_box(child, context_menu):
  ret = gtk.EventBox()
  ret.add(child)
  set_white_background(ret)
  ret.connect_object("button_press_event",
                     mouse_press_for_context_menu,
                     context_menu)
  ret.connect('realize', lambda e: e.window.set_cursor(g_handcursor))
  return ret


def create_simple_text_view_widget(str_to_display, width, height):
  lab = gtk.Label()
  lab.modify_font(pango.FontDescription("monospace 9"))
  lab.set_label(str_to_display)
  lab.set_line_wrap(False)

  lab_lalign = create_alignment(lab, pleft=4, ptop=4)

  vp = gtk.Viewport()
  vp.add(lab_lalign)
  set_white_background(vp)

  lab_scroller = gtk.ScrolledWindow()
  lab_scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  lab_scroller.add(vp)
  lab_scroller.set_size_request(width, height)

  show_all_local_widgets(locals())

  return lab_scroller


def create_popup_error_dialog(msg):
  d = gtk.MessageDialog(None,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        gtk.MESSAGE_ERROR,
                        gtk.BUTTONS_OK,
                        message_format=msg)
  d.run()
  d.destroy()


########NEW FILE########
__FILENAME__ = source_file_prov_viewer
# Demo of source file provenance viewer


# TODO: handle copy-and-paste events later if we want more precision
# for, say, ranking

# TODO: if we want to rank webpages/files more precisely, we could
# measure the relative amounts of time spent looking at those things in
# active GUI windows and rank accordingly

# TODO: support filtering by a time range rather than just a session tag

# TODO: support clicking on files to view that version's contents, diffs, etc.


import pygtk
pygtk.require('2.0')
import gtk, pango, gobject

import os, sys
import datetime
import filecmp
import difflib
import mimetypes

from pymongo import Connection, ASCENDING, DESCENDING

from pygtk_burrito_utils import *

from BurritoUtils import *
from urlparse import urlparse

sys.path.insert(0, '../../GUItracing/')

from annotation_component import AnnotationComponent
from event_fetcher import *
from collections import defaultdict

import atexit
from signal import signal, SIGTERM

from file_version_manager import FileVersionManager
from burrito_feed import *

from parse_gui_trace import DesktopState


# hard-code in a bunch of extensions for documents that we want to track:
def document_extension_whitelisted(fn):
  ext = os.path.splitext(fn)[-1].lower()
  return ext in ('.xls', '.doc', '.docx', '.pdf', '.ods', '.odp', '.odt', '.sxw')


# Represents what happens during a particular Vim editing session,
# with a focus on target_filename
class VimFileEditSession:
  
  # represents a series of consecutive FileWriteEvent instances to
  # target_filename without any intervening barrier events
  class CoalescedWrite:
    def __init__(self, first_write_event):
      self.first_write_timestamp = first_write_event.timestamp
      self.timestamp = self.first_write_timestamp # for sorting purposes

      self.last_write_event = None
      self.last_write_timestamp = None
      self.add_write_event(first_write_event)

      self.ending_event = None # what's responsible for ending this streak?


    def add_write_event(self, write_evt):
      self.last_write_event = write_evt
      self.last_write_timestamp = self.last_write_event.timestamp

    def finalize(self, ending_event):
      self.ending_event = ending_event


    def printme(self):
      print 'CoalescedWrite: %s to %s' % \
            (str(self.first_write_timestamp), str(self.last_write_timestamp))


  # represents a faux version of target_filename
  class FauxVersion:
    def __init__(self, target_filename, start_timestamp, fvm):
      self.target_filename = target_filename
      self.start_timestamp = start_timestamp

      self.fvm = fvm

      # will update in finalize()
      self.coalesced_write_evt = None
      self.end_timestamp = None

      self.timestamp = start_timestamp # for sorting purposes

      # Each element is a WebpageVisitEvent (TODO: de-dup later)
      self.webpages_visited = []

      # Key: filename
      # Value: timestamp of FIRST read/write
      self.other_vim_files_read   = {}
      self.other_vim_files_edited = {}

      # files read by external non-vim programs
      # Key: filename
      # Value: timestamp of FIRST read
      self.non_vim_files_read = {}

      self.doodle_save_events = []
      self.happy_face_events = []
      self.sad_face_events = []
      self.status_update_events = []


    def get_last_write_event(self):
      return self.coalesced_write_evt.last_write_event


    def add_ending_event(self, coalesced_write_evt):
      assert not self.end_timestamp
      self.coalesced_write_evt = coalesced_write_evt
      self.end_timestamp = self.coalesced_write_evt.last_write_timestamp

      # if you ended on a HappyFaceEvent or SadFaceEvent, then add that
      # to self, since it's like a "commit message" for this faux version!
      e_evt = coalesced_write_evt.ending_event
      if e_evt:
        if e_evt.__class__ == HappyFaceEvent:
          self.happy_face_events.append(e_evt)
        elif e_evt.__class__ == SadFaceEvent:
          self.sad_face_events.append(e_evt)


    def printme(self):
      print 'FauxVersion: %s to %s' % \
            (str(self.start_timestamp), str(self.end_timestamp))
      print '  Last FileWriteEvent:',
      self.get_last_write_event().printme()
      print '  Ended due to', self.coalesced_write_evt.ending_event
      for e in self.webpages_visited:
        print '    Web:   ', e.title.encode('ascii', 'replace')
      for e in sorted(self.other_vim_files_read.keys()):
        print '    VIM read:  ', e
      for e in sorted(self.other_vim_files_edited.keys()):
        print '    VIM edited:', e
      for e in sorted(self.non_vim_files_read.keys()):
        print '    OTHER read:', e

      for e in self.doodle_save_events + self.happy_face_events + self.sad_face_events + self.status_update_events:
        print '   ',
        e.printme()


    def diff(self):
      left_filepath  = self.fvm.checkout_file(self.target_filename, self.start_timestamp)

      # add ONE_SEC so that we can get the effect of the last WRITE that
      # ended this faux version:
      right_filepath = self.fvm.checkout_file(self.target_filename, self.end_timestamp + ONE_SEC)

      EMPTY_FILE = '/tmp/empty'

      # hack: create a fake empty file to diff in case either doesn't exist
      if not os.path.isfile(left_filepath):
        ef = open('/tmp/empty', 'w')
        ef.close()
        left_filepath = EMPTY_FILE

      if not os.path.isfile(right_filepath):
        ef = open('/tmp/empty', 'w')
        ef.close()
        right_filepath = EMPTY_FILE

      # display diff
      if filecmp.cmp(left_filepath, right_filepath):
        str_to_display = 'UNCHANGED'
      else:
        # render 'other' first!
        d = difflib.unified_diff(open(left_filepath, 'U').readlines(),
                                 open(right_filepath, 'U').readlines(),
                                 prettify_filename(self.target_filename),
                                 prettify_filename(self.target_filename),
                                 self.start_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                 self.end_timestamp.strftime('%Y-%m-%d %H:%M:%S'))

        str_to_display = ''.join([line for line in d])

      return str_to_display


    def render_table_row(self, tbl, row_index):
      XPADDING=8
      YPADDING=15
      # using "yoptions=gtk.SHRINK" in table.attach seems to do the trick
      # in not having the table cells expand vertically like nuts


      # Print source file diffs

      sd = self.start_timestamp.strftime('%Y-%m-%d')
      ed = self.end_timestamp.strftime('%Y-%m-%d')

      st = self.start_timestamp.strftime('%H:%M:%S')
      et = self.end_timestamp.strftime('%H:%M:%S')

      # If the days are the same, then don't duplicate:
      if sd == ed:
        date_str = '%s to %s (%s)' % (st, et, sd)
      else:
        date_str = '%s %s to %s %s' % (sd, st, ed, et)

      date_lab = gtk.Label(date_str)
      date_lab.modify_font(pango.FontDescription("sans 8"))
      date_lab_lalign = create_alignment(date_lab, pbottom=3)

      diff_result_str = self.diff()

      # TODO: adjust height based on existing height of row/column
      text_widget = create_simple_text_view_widget(diff_result_str, 450, 200)


      source_file_vbox = create_vbox([date_lab_lalign, text_widget])
      tbl.attach(source_file_vbox, 0, 1, row_index, row_index+1,
                 xpadding=XPADDING + 5,
                 ypadding=YPADDING,
                 yoptions=gtk.SHRINK)


      # Print co-reads:
      # 1.) webpages visited
      # 2.) other vim files read
      # 3.) other non-vim files read
      co_read_widgets = []

      # TODO: make these labels clickable with pop-up context menus
      for (fn, timestamp) in self.other_vim_files_read.items() + \
                             self.non_vim_files_read.items():
        lab = gtk.Label(prettify_filename(fn))
        lab.modify_font(pango.FontDescription("monospace 9"))
        lab.set_selectable(True)
        lab.show()
        lab_lalign = create_alignment(lab, pbottom=3)
        lab_lalign.show()
        co_read_widgets.append(lab_lalign)


      # de-dup:
      urls_seen = set()

      if self.webpages_visited:
        n = WebpageFeedEvent()
        for w in self.webpages_visited:
          if w.url not in urls_seen:
            urls_seen.add(w.url)
            n.add_webpage_chron_order(w)

        n_lalign = create_alignment(n.get_widget(), ptop=3)
        co_read_widgets.append(n_lalign)


      co_reads_vbox = create_vbox(co_read_widgets)
      co_reads_vbox_lalign = create_alignment(co_reads_vbox)
      tbl.attach(co_reads_vbox_lalign, 1, 2, row_index, row_index+1,
                 xpadding=XPADDING, ypadding=YPADDING,
                 xoptions=gtk.SHRINK, yoptions=gtk.SHRINK)


      # Print co-writes
      # 1.) other vim files edited
      # 2.) doodle events
      # 3.) happy face events
      # 4.) sad face events
      # 5.) status update events
      co_write_widgets = []

      for (fn, timestamp) in self.other_vim_files_edited.iteritems():
        lab = gtk.Label(prettify_filename(fn))
        lab.modify_font(pango.FontDescription("monospace 9"))
        lab.set_selectable(True)
        lab.show()
        lab_lalign = create_alignment(lab)
        lab_lalign.show()
        co_write_widgets.append(lab_lalign)

      all_feed_evts = []

      for e in self.doodle_save_events:
        d = DoodleFeedEvent(e, self.fvm)
        d.load_thumbnail() # subtle but dumb!!!
        all_feed_evts.append(d)

      for e in self.happy_face_events:
        all_feed_evts.append(HappyFaceFeedEvent(e))

      for e in self.sad_face_events:
        all_feed_evts.append(SadFaceFeedEvent(e))

      for e in self.status_update_events:
        all_feed_evts.append(StatusUpdateFeedEvent(e))


      for e in all_feed_evts:
        co_write_widgets.append(e.get_widget())


      co_writes_vbox = create_vbox(co_write_widgets,
                                   [4 for e in co_write_widgets])
      co_writes_vbox_lalign = create_alignment(co_writes_vbox)

      tbl.attach(co_writes_vbox_lalign, 2, 3, row_index, row_index+1,
                 xpadding=XPADDING, ypadding=YPADDING,
                 xoptions=gtk.SHRINK, yoptions=gtk.SHRINK)


      # Print notes (annotations)

      # stick the annotation on the FINAL FileWriteEvent in this faux version:
      annotator = AnnotationComponent(300, self.get_last_write_event(), '<Click to enter a new note>')
      tbl.attach(annotator.get_widget(), 3, 4,
                 row_index, row_index+1,
                 xpadding=XPADDING, ypadding=YPADDING,
                 yoptions=gtk.SHRINK)

      show_all_local_widgets(locals())


  def __init__(self, target_filename, vim_pid, vim_start_time, vim_end_time, fvm):
    self.target_filename = target_filename
    self.vim_pid = vim_pid
    # start and end times of the vim session editing this file
    self.vim_start_time = vim_start_time
    self.vim_end_time   = vim_end_time

    self.fvm = fvm

    # sometimes processes don't have end times, so make up something
    # ridiculous:
    if not self.vim_end_time:
      print >> sys.stderr, "WARNING: VimFileEditSession [PID: %d] has no end time" % vim_pid
      self.vim_end_time = datetime.datetime(3000,1,1)


    # list of WebpageVisitEvent objects
    self.webpage_visit_events = []

    # list of ActiveVimBufferEvent objects where pid == self.vim_pid
    self.vim_active_buffer_events = []

    # list of FileWriteEvent objects where pid == self.vim_pid
    # (includes saves of ALL files, not just target_filename
    self.vim_file_save_events = []

    # list of ActiveGUIWindowEvent objects that DON'T belong to this vim session
    self.other_gui_events = []

    self.doodle_save_events = []   # list of DoodleSaveEvent
    self.happy_face_events = []    # list of HappyFaceEvent
    self.sad_face_events = []      # list of SadFaceEvent
    self.status_update_events = [] # list of StatusUpdateEvent

    # list of FileReadEvent objects where pid != self.vim_pid and filename == target_filename
    # (useful for creating barriers to write coalescing)
    self.other_process_read_events = []


    # list of CoalescedWrite objects
    self.coalesced_writes = []


    self.faux_versions = [] # see _create_faux_versions()


  def within_time_bounds(self, t):
    return self.vim_start_time <= t <= self.vim_end_time


  def add_vim_buffer_event(self, evt):
    if self.within_time_bounds(evt.timestamp) and evt.pid == self.vim_pid:
      self.vim_active_buffer_events.append(evt)

  def add_webpage_visit_event(self, evt):
    if self.within_time_bounds(evt.timestamp):
      self.webpage_visit_events.append(evt)

  def add_file_read_event(self, evt):
    if (self.within_time_bounds(evt.timestamp) and \
        evt.pid != self.vim_pid and
        evt.filename == self.target_filename):
      self.other_process_read_events.append(evt)


  def add_file_save_event(self, evt):
    # hack: ignore files ending in '~' and '*.swp' files,
    # since those are vim temporary backup files
    if (self.within_time_bounds(evt.timestamp) and \
        evt.pid == self.vim_pid and \
        evt.filename[-1] != '~' and \
        not evt.filename.endswith('.swp')):

      # SUPER HACK: if this write event has an annotation, then add an
      # 'annotation' field to it
      optional_note = evt.load_annotation()
      if optional_note:
        evt.annotation = optional_note

      self.vim_file_save_events.append(evt)


  def add_doodle_save_event(self, evt):
    if (self.within_time_bounds(evt.timestamp)):
      self.doodle_save_events.append(evt)

  def add_happy_face_event(self, evt):
    if (self.within_time_bounds(evt.timestamp)):
      self.happy_face_events.append(evt)

  def add_sad_face_event(self, evt):
    if (self.within_time_bounds(evt.timestamp)):
      self.sad_face_events.append(evt)

  def add_status_update_event(self, evt):
    if (self.within_time_bounds(evt.timestamp)):
      self.status_update_events.append(evt)

  def add_other_gui_event(self, evt):
    if not self.within_time_bounds(evt.timestamp):
      return

    if hasattr(evt, 'vim_event') and evt.vim_event.pid == self.vim_pid:
      return

    self.other_gui_events.append(evt)


  def gen_all_sorted_events(self):
    for e in sorted(self.webpage_visit_events + \
                    self.vim_active_buffer_events + \
                    self.vim_file_save_events + \
                    self.other_gui_events + \
                    self.other_process_read_events + \
                    self.doodle_save_events + \
                    self.happy_face_events + \
                    self.sad_face_events + \
                    self.status_update_events + \
                    self.coalesced_writes, key=lambda e:e.timestamp):
      yield e


  def printraw(self):
    print 'VimFileEditSession [PID: %d] %s to %s' % (self.vim_pid, str(self.vim_start_time), str(self.vim_end_time))

    for e in self.gen_all_sorted_events():
      e.printme()
      if e.__class__ == ActiveGUIWindowEvent and hasattr(e, 'vim_event'):
        print ' >',
        e.vim_event.printme()
    print


  def finalize(self):
    self._coalesce_write_events()
    self._create_faux_versions()

  
  # We coalesce writes of target_filename around the following barriers:
  #
  # 1.) READ events of target_filename made by another process
  #     (e.g., executing a script file, compiling a source file,
  #     compiling a LaTex file, etc.)
  # 2.) Any FileWriteEvent with a non-null annotation, since we don't
  #     want to hide annotations from the user in the GUI
  # 3.) HappyFaceEvent and SadFaceEvent, since those are like manual 'commits'
  def _coalesce_write_events(self):
    self.coalesced_writes = []

    # only try to coalesce for target_filename
    target_filename_writes = [e for e in self.vim_file_save_events if e.filename == self.target_filename]

    cur_cw = None
    cur_urls_visited = set()

    # now group together with all events that are possible write
    # barriers, then SORT the whole damn thing ...
    for e in sorted(target_filename_writes + \
                    self.happy_face_events + \
                    self.sad_face_events + \
                    self.other_process_read_events, key=lambda e:e.timestamp):
      if e.__class__ == FileWriteEvent:
        assert e.filename == self.target_filename   # MUY IMPORTANTE!

        if cur_cw:
          cur_cw.add_write_event(e) # coalesce!!!
        else:
          cur_cw = VimFileEditSession.CoalescedWrite(e)

        # if the write event has an annotation, then that's a write
        # barrier, so start a new cur_cw CoalescedWrite right after it
        if hasattr(e, 'annotation'):
          cur_cw.finalize(e)
          self.coalesced_writes.append(cur_cw)
          cur_cw = None # write barrier!

      else:
        # every other kind of event acts as a barrier
        if cur_cw:
          cur_cw.finalize(e)
          self.coalesced_writes.append(cur_cw)
          cur_cw = None # write barrier!
     
    # append on the final entry
    if cur_cw:
      self.coalesced_writes.append(cur_cw)


  # use coalesced write events to create faux 'versions' of
  # target_filename based on editing (and other) actions.
  # these versions will be displayed by the source file
  # provenance viewer GUI
  def _create_faux_versions(self):
    self.faux_versions = []

    for e in sorted(self.coalesced_writes + self.vim_active_buffer_events,
                    key=lambda e:e.timestamp):
      if not self.faux_versions:
        # create the first faux version by looking for the first
        # ActiveVimBufferEvent where target_filename is being edited
        # (or a regular CoalescedWrite entry)
        if e.__class__ == ActiveVimBufferEvent and e.filename == self.target_filename:
          self.faux_versions.append(VimFileEditSession.FauxVersion(self.target_filename, e.timestamp, self.fvm))
        elif e.__class__ == VimFileEditSession.CoalescedWrite:
          self.faux_versions.append(VimFileEditSession.FauxVersion(self.target_filename, e.first_write_timestamp, self.fvm))
      else:
        # creat additional versions split by CoalescedWrite entries
        cur = self.faux_versions[-1]
        if e.__class__ == VimFileEditSession.CoalescedWrite:
          cur.add_ending_event(e)

          self.faux_versions.append(VimFileEditSession.FauxVersion(self.target_filename, e.last_write_timestamp, self.fvm))

    # get rid of the last entry if it's incomplete
    if self.faux_versions and not self.faux_versions[-1].end_timestamp:
      self.faux_versions.pop()

    
    # sanity check:
    for (prev, cur) in zip(self.faux_versions, self.faux_versions[1:]):
      assert prev.start_timestamp <= prev.end_timestamp
      assert prev.end_timestamp <= cur.start_timestamp
      assert cur.start_timestamp <= cur.end_timestamp


    # ok, this is a bit gross, but HappyFaceEvent and SadFaceEvent
    # objects are used as "write barriers" to mark the end of a series
    # of coalesced writes.  if that's the case, then one of those
    # objects is in the ending_event field for that CoalescedWrite event
    # and thus should NOT be re-used in the next FauxVersion ...
    already_used_happy_sad_faces = set()

    # don't double-render doodle files ...
    doodle_filenames = set()

    cur_version = None
    for e in sorted(self.faux_versions + \
                    self.webpage_visit_events + \
                    self.other_gui_events + \
                    self.vim_active_buffer_events + \
                    self.doodle_save_events + \
                    self.happy_face_events + \
                    self.sad_face_events + \
                    self.status_update_events + \
                    self.vim_file_save_events,
                    key=lambda e:e.timestamp):
      if e.__class__ == VimFileEditSession.FauxVersion:
        cur_version = e
        # kludgy!
        already_used_happy_sad_faces.update(cur_version.happy_face_events)
        already_used_happy_sad_faces.update(cur_version.sad_face_events)
      elif cur_version:
        assert cur_version.start_timestamp <= e.timestamp

        # stay within the time range!
        if e.timestamp > cur_version.end_timestamp:
          continue

        elif e.__class__ == WebpageVisitEvent:
          cur_version.webpages_visited.append(e)
        elif e.__class__ == FileWriteEvent:
          if e.filename != self.target_filename:
            # only keep FIRST write timestamp
            if e.filename not in cur_version.other_vim_files_edited:
              cur_version.other_vim_files_edited[e.filename] = e.timestamp
        elif e.__class__ == ActiveVimBufferEvent:
          if e.filename != self.target_filename:
            # only keep FIRST read timestamp
            if e.filename not in cur_version.other_vim_files_read:
              cur_version.other_vim_files_read[e.filename] = e.timestamp

        elif e.__class__ == ActiveGUIWindowEvent:
          if hasattr(e, 'files_read_set'):
            for fr in e.files_read_set:
              if fr not in cur_version.non_vim_files_read:
                if fr not in doodle_filenames:
                  cur_version.non_vim_files_read[fr] = e.timestamp


        elif e.__class__ == StatusUpdateEvent:
          cur_version.status_update_events.append(e)
        elif e.__class__ == DoodleSaveEvent:
          cur_version.doodle_save_events.append(e)
          doodle_filenames.add(e.filename)
        elif e.__class__ == HappyFaceEvent:
          if e not in already_used_happy_sad_faces:
            cur_version.happy_face_events.append(e)
        elif e.__class__ == SadFaceEvent:
          if e not in already_used_happy_sad_faces:
            cur_version.sad_face_events.append(e)
        else:
          assert False, e


    for fv in self.faux_versions:
      # to eliminate redundancies, remove all entries from
      # other_vim_files_read if they're in other_vim_files_edited
      for f in fv.other_vim_files_edited:
        if f in fv.other_vim_files_read:
          del fv.other_vim_files_read[f]


class SourceFileProvViewer():
  def __init__(self, target_filename, session_tag, fvm):
    self.fvm = fvm
    self.session_tag = session_tag
    self.target_filename = target_filename

    # MongoDB stuff
    c = Connection()
    self.db = c.burrito_db

    all_events = []

    # Get GUI events
    for m in self.db.gui_trace.find({"session_tag": session_tag}):
      web_visit_evt = fetch_webpage_visit_event(m)
      if web_visit_evt:
        all_events.append(web_visit_evt)
      else:
        gui_evt = fetch_active_gui_window_event(m)
        if gui_evt:
          all_events.append(gui_evt)


    # Get file read/write events

    # Key:   child PID
    # Value: parent PID
    #
    # TODO: assumes that there is no recycling of PIDs, which should be an
    # okay assumption if we're operating within one session but needs to be
    # revised when we're querying over multiple sessions
    pid_parents = {}

    # Key:   PID
    # Value: process creation/exit time
    pid_creation_times = {}
    pid_exit_times = {}

    def get_pid_and_parents(pid):
      ret = [pid]
      try:
        parent = pid_parents[pid]
        while True:
          ret.append(parent)
          parent = pid_parents[parent]
      except KeyError:
        return ret

    for m in self.db.process_trace.find({"session_tag": session_tag},
                                        {'pid':1, 'ppid':1, 'uid':1, 'phases':1,
                                         'creation_time':1, 'exit_time':1}):
      pid_creation_times[m['pid']] = m['creation_time']
      pid_exit_times[m['pid']] = m['exit_time']
      pid_parents[m['pid']] = m['ppid']

      prov_evts = fetch_file_prov_event_lst(m, session_tag)
      all_events.extend(prov_evts)


    # Get VIM edit events
    for m in self.db.apps.vim.find({"session_tag": session_tag}):
      vim_evt = fetch_active_vim_buffer_event(m)
      if vim_evt:
        all_events.append(vim_evt)

    
    # Get HappyFaceEvent, SadFaceEvent, and StatusUpdateEvent events
    all_events.extend(fetch_toplevel_annotation_events(session_tag))


    # Key: PID
    # Value: set of files read by this process or by one of its children
    pid_to_read_files = defaultdict(set)

    # Key: PID
    # Value: VimFileEditSession
    # (each VimFileEditSession has a list of faux_versions)
    self.vim_sessions = {}

    # les means "latest edit session":
    # we are associating all events with the most recently-active vim session
    # (which is a reasonable simplifying assumption)
    les = None

    # massive chronological sort!
    all_events.sort(key=lambda e:e.timestamp)

    for (ind, e) in enumerate(all_events):
      if e.__class__ == FileReadEvent:
        # We want to associate GUI windows with files read by the application
        # that controls each window.  For example, we want to associate an
        # ActiveGUIWindowEvent for the OpenOffice Calc app with some *.xls
        # spreadsheet file that the app is currently editing.
        #
        # incrementally build up this set in chronological order,
        #
        # and for simplicity, just have a whitelist of document extensions
        # that we're looking for:
        if document_extension_whitelisted(e.filename):
          for p in get_pid_and_parents(e.pid):
            pid_to_read_files[p].add(e.filename)

        if les: les.add_file_read_event(e)
      elif e.__class__ == FileWriteEvent:
        if les: les.add_file_save_event(e)
      elif e.__class__ == WebpageVisitEvent:
        if les: les.add_webpage_visit_event(e)
      elif e.__class__ == ActiveGUIWindowEvent:
        # Now associate each ActiveGUIWindowEvent with the ActiveVimBufferEvent
        # directly preceeding it if ...
        #   ActiveVimBufferEvent.pid is a parent of ActiveVimBufferEvent.pid
        #
        # This forms a bond between an ActiveGUIWindowEvent and VIM by adding
        # a vim_event field to ActiveGUIWindowEvent
        #
        # go backwards ...
        for vim_event in reversed(all_events[:ind]):
          if vim_event.__class__ == ActiveVimBufferEvent:
            # the vim process will probably be a child of 'bash', which is
            # itself a child of 'gnome-terminal' (or whatever terminal app
            # controls the GUI window), so we need to match on parent
            # processes all the way up the chain
            candidate_pids = get_pid_and_parents(vim_event.pid)
            if e.active_app_pid in candidate_pids:
              e.vim_event = vim_event # establish a link
              break
        
        
        if not hasattr(e, 'vim_event'):
          # if this process of any of its children have read files, then add
          # the set of files as a new field called files_read_set
          if e.active_app_pid in pid_to_read_files:
            e.files_read_set = pid_to_read_files[e.active_app_pid]

        if les: les.add_other_gui_event(e)

      elif e.__class__ == ActiveVimBufferEvent:
        if e.pid not in self.vim_sessions:
          n = VimFileEditSession(self.target_filename, e.pid, pid_creation_times[e.pid], pid_exit_times[e.pid], self.fvm)
          self.vim_sessions[e.pid] = n

        les = self.vim_sessions[e.pid]

        # unconditionally add!
        les.add_vim_buffer_event(e)

      elif e.__class__ == DoodleSaveEvent:
        if les: les.add_doodle_save_event(e)
      elif e.__class__ == HappyFaceEvent:
        if les: les.add_happy_face_event(e)
      elif e.__class__ == SadFaceEvent:
        if les: les.add_sad_face_event(e)
      elif e.__class__ == StatusUpdateEvent:
        if les: les.add_status_update_event(e)
      else:
        assert False, e


    # SUPER important to finalize!
    for e in self.vim_sessions.values():
      e.finalize()


    self.all_faux_versions = []
    for e in self.vim_sessions.values():
      self.all_faux_versions.extend(e.faux_versions)

    # reverse chronological order
    self.all_faux_versions.sort(key=lambda e:e.timestamp, reverse=True)


    '''
    for e in sorted(self.vim_sessions.values(), key=lambda e:e.vim_start_time):
      e.printraw()
      print '---'
      for fv in e.faux_versions:
        fv.printme()
      print
    '''


    # ok, now time for the GUI part!
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.window.set_title("Source file provenance viewer")
    self.window.set_border_width(0)
    set_white_background(self.window)

    self.window.resize(500, 500)
    self.window.maximize()


    tbl = gtk.Table(rows=len(self.all_faux_versions) + 1, columns=4)
    tbl_scroller = gtk.ScrolledWindow()
    tbl_scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    tbl_scroller.add_with_viewport(tbl)
    set_white_background(tbl_scroller.get_children()[0])

    self.window.add(tbl_scroller)

    # header row
    col1_label = gtk.Label(prettify_filename(self.target_filename))
    col1_label.modify_font(pango.FontDescription("sans 12"))
    col2_label = gtk.Label("Co-reads")
    col2_label.modify_font(pango.FontDescription("sans 12"))
    col3_label = gtk.Label("Co-writes")
    col3_label.modify_font(pango.FontDescription("sans 12"))
    col4_label = gtk.Label("Notes")
    col4_label_lalign = create_alignment(col4_label, pleft=15)
    col4_label.modify_font(pango.FontDescription("sans 12"))
    tbl.attach(col1_label, 0, 1, 0, 1, ypadding=8)
    tbl.attach(col2_label, 1, 2, 0, 1, ypadding=8)
    tbl.attach(col3_label, 2, 3, 0, 1, ypadding=8)
    tbl.attach(col4_label_lalign, 3, 4, 0, 1, ypadding=8)


    # show the window and all widgets first!!!
    show_all_local_widgets(locals())
    self.window.show()


    row_index = 1

    for fv in self.all_faux_versions:
      # ... then use this trick to update the GUI between each loop
      # iteration, since each iteration takes a second or two
      # (this will make the GUI seem more responsive, heh)
      #
      #   http://faq.pygtk.org/index.py?req=show&file=faq03.007.htp
      while gtk.events_pending(): gtk.main_iteration(False)

      print >> sys.stderr, "SourceFileProvViewer rendering row", \
               row_index, "of", len(self.all_faux_versions)

      fv.render_table_row(tbl, row_index)
      row_index += 1

      # stent!
      #if row_index > 20: break


def exit_handler():
  global fvm
  fvm.memoize_checkpoints()
  fvm.unmount_all_snapshots()


if __name__ == '__main__':
  atexit.register(exit_handler)
  signal(SIGTERM, lambda signum,frame: exit(1)) # trigger the atexit function to run

  fvm = FileVersionManager()
  target_filename = sys.argv[1]
  session_tag = sys.argv[2]
  SourceFileProvViewer(target_filename, session_tag, fvm)
  gtk.main()


########NEW FILE########
__FILENAME__ = clobber_files
import datetime

n = datetime.datetime.now()

for i in range(10):
  f = open('output-%d.txt' % i, 'w')
  f.write('HAHAHA\n')
  f.write(str(n))
  f.write('\n')
  f.close()


########NEW FILE########
__FILENAME__ = BurritoUtils
../../BurritoUtils.py
########NEW FILE########
__FILENAME__ = clipboard_tester
# Test to see if burrito properly records clipboard copy/paste events

from pymongo import Connection, ASCENDING, DESCENDING
from BurritoUtils import *

import sys
sys.path.insert(0, '../../GUItracing/')

import pprint
p = pprint.PrettyPrinter()

from parse_gui_trace import DesktopState

c = Connection()
db = c.burrito_db

clipboard_col = db.clipboard_trace
gui_col = db.gui_trace

#for evt in clipboard_col.find(sort=[('_id', DESCENDING)], limit=1):
for evt in clipboard_col.find(sort=[('_id', DESCENDING)]):
  print evt['_id']

  src_desktop_cur = gui_col.find({'_id': evt['src_desktop_id']})
  dst_desktop_cur = gui_col.find({'_id': evt['dst_desktop_id']})

  # sanity checks
  assert src_desktop_cur.count() == 1, evt['src_desktop_id']
  assert dst_desktop_cur.count() == 1, evt['dst_desktop_id']

  src_desktop_json = src_desktop_cur[0]
  dst_desktop_json = dst_desktop_cur[0]

  src_desktop = DesktopState.from_mongodb(src_desktop_json)
  dst_desktop = DesktopState.from_mongodb(dst_desktop_json)

  print "Contents:", evt['contents']
  print "Src app:", src_desktop[src_desktop_json['active_app_id']]
  print " window:", src_desktop[src_desktop_json['active_app_id']][src_desktop_json['active_window_index']].title
  print "Dst app:", dst_desktop[dst_desktop_json['active_app_id']]
  print " window:", dst_desktop[dst_desktop_json['active_app_id']][dst_desktop_json['active_window_index']].title
  print


########NEW FILE########
__FILENAME__ = BurritoUtils
../../BurritoUtils.py
########NEW FILE########
__FILENAME__ = gui_state_visualizer
from pymongo import Connection, ASCENDING, DESCENDING
from BurritoUtils import *

import sys
sys.path.insert(0, '../../GUItracing/')

from parse_gui_trace import DesktopState


def interactive_print(lst):
  idx = 0
  while True:
    (t, s) = lst[idx]
    for i in range(100): print
    print "%d / %d" % (idx + 1, len(lst)), t
    print
    s.printMe()
    print
    print "Next state: <Enter>"
    print "Prev state: 'p'+<Enter>"
    print "Next PINNED state: 'a'+<Enter>"
    print "Jump: <state number>'+<Enter>"

    k = raw_input()
    if k == 'p':
      if idx > 0:
        idx -= 1
    elif k == 'a':
      idx += 1
      while True:
        (t, s) = lst[idx]
        if not s.pinned:
          idx += 1
        else:
          break
    else:
      try:
        jmpIdx = int(k)
        if 0 <= jmpIdx < len(lst):
          idx = (jmpIdx - 1)
      except ValueError:
        if idx < len(lst) - 1:
          idx += 1


# Each element is a (datetime object, DesktopState instance)
timesAndStates = []

if __name__ == "__main__":
  session_name = sys.argv[1]

  c = Connection()
  db = c.burrito_db

  gui_col = db.gui_trace

  for dat in gui_col.find({'session_tag': session_name}, sort=[('_id', ASCENDING)]):
    evt_time = dat['_id']
    dt = DesktopState.from_mongodb(dat)
    timesAndStates.append((evt_time, dt))

  interactive_print(timesAndStates)


########NEW FILE########
__FILENAME__ = chcp
# Change ALL checkpoints to snapshots (and vice versa)

import nilfs2
n = nilfs2.NILFS2()

for e in n.lscp():
  if not e['ss']:
    n.chcp(e['cno'], True)


########NEW FILE########
__FILENAME__ = diff_GUItracer
import os

cur_modtime = None
cur_snapshot = None

significant_snapshots = []

BASE_PATH = '/tmp/test-tmpfs/nilfs-%d/researcher/burrito/GUItracing/GUItracer.py'

for cno in range(4373, 20000):
  try:
    mtime = os.path.getmtime(BASE_PATH % (cno,))
    if cur_modtime and (mtime > cur_modtime):
      significant_snapshots.append((cur_snapshot, cur_modtime))
      print significant_snapshots[-1]

      if len(significant_snapshots) > 1:
        os.system(('diff -u ' + BASE_PATH + ' ' + BASE_PATH + ' >> guitracer.diff') % (significant_snapshots[-2][0], significant_snapshots[-1][0]))


    cur_modtime = mtime
    cur_snapshot = cno

  except OSError:
    pass


########NEW FILE########
__FILENAME__ = mount_everything
# Crazy idea ... mount ALL snapshots and see whether my VM explodes

# Run as 'sudo'


def create_dir(path):
    "Check if @path is present, and make the directory if not."
    if os.path.exists(path):
        if not os.path.isdir(path):
             info = "path is not directory: %s" % path
             raise Exception(info)
    else:
        os.mkdir(path)


import os
import commands

MOUNTDIR_BASE = '/tmp/test-tmpfs'
assert os.path.isdir(MOUNTDIR_BASE)

commands.getstatusoutput('umount %s' % (MOUNTDIR_BASE,))
result = commands.getstatusoutput('mount -t tmpfs none %s' % (MOUNTDIR_BASE,))
assert result[0] == 0

import nilfs2
n = nilfs2.NILFS2()

for e in n.lscp():
  if e['ss']:
    cno = e['cno']
    subdir_name = os.path.join(MOUNTDIR_BASE, 'nilfs-' + str(cno))
    create_dir(subdir_name)
    print "Mount", subdir_name
    commands.getstatusoutput('sudo mount -t nilfs2 -n -o ro,cp=%d /dev/dm-3 %s' % (cno, subdir_name))


########NEW FILE########
__FILENAME__ = nilfs2
# Code originally taken from the TimeBrowse project:
#   http://sourceforge.net/projects/timebrowse/
# and then adapted by Philip Guo

#!/usr/bin/env python
#
# copyright(c) 2011 - Jiro SEKIBA <jir@unicus.jp>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#

"""NILFS2 module"""

__author__    = "Jiro SEKIBA"
__copyright__ = "Copyright (c) 2011 - Jiro SEKIBA <jir@unicus.jp>"
__license__   = "LGPL"
__version__   = "0.6"

import commands
import re
import datetime

class NILFS2:
    # if you don't pass in a device name, nilfs tools will look in
    # /proc/mounts, so if there's exactly ONE nilfs FS mounted on
    # your machine, then you're fine!
    def __init__(self, device=''):
        self.cpinfo_regex = re.compile(
            r'^ +([1-9]|[1-9][0-9]+) +([^ ]+ [^ ]+) +(ss|cp) +([^ ]+) +.*$',
            re.M)
        self.device = device

    def __run_cmd__(self, line):
        result = commands.getstatusoutput(line)
        if result[0] != 0:
            raise Exception(result[1])
        return result[1]

    def __parse_lscp_output__(self, output):
        a = self.cpinfo_regex.findall(output)

        a = [ {'cno'  : int(e[0]),
               'date' : datetime.datetime.strptime(e[1], "%Y-%m-%d %H:%M:%S"),
               'ss'  : e[2] == 'ss'}
               for e in a if e[3] != 'i' ] # don't count internal ('i') checkpoints

        if not a:
            return []

        return a
        
        '''
        # Drop checkpoints that have the same timestamp with its
        # predecessor.  If a snapshot is present in the series of
        # coinstantaneous checkpoints, we leave it rather than plain
        # checkpoints.
        prev = a.pop(0)
        if not a:
            return [prev]

        ss = prev if prev['ss'] else None
        l = []
        for e in a:
            if e['date'] != prev['date']:
                l.append(ss if ss else prev)
                ss = None
            prev = e
            if prev['ss']:
                ss = prev
        l.append(ss if ss else a[-1])
        '''
        return l

    def lscp(self, index=1):
        result = self.__run_cmd__("lscp -i %d %s" % (index, self.device))
        return self.__parse_lscp_output__(result)

    def chcp(self, cno, ss=False):
        line = "chcp cp "
        if ss:
            line = "chcp ss "
        line += self.device + " %i" % cno
        return self.__run_cmd__(line)

    def mkcp(self, ss=False):
        line = "mkcp"
        if ss:
            line += " -s"
        line += " " + self.device
        return self.__run_cmd__(line)


if __name__ == '__main__':
  import sys
  nilfs = NILFS2()
  all_checkpoints = nilfs.lscp()

  prev = None
  for e in all_checkpoints:
    print e['cno'], e['date'],
    if prev and prev['date'] == e['date']:
      print "UGH!"
    else:
      print

    prev = e


########NEW FILE########
__FILENAME__ = print_pass_lite_stats
import os

for i in range(494, 2000):
  try:
    print i, os.path.getmtime('/tmp/test-tmpfs/nilfs-%d/researcher/burrito/SystemTap/pass-lite.stp' % (i,))
  except:
    print i, "WTF???"


########NEW FILE########
__FILENAME__ = pag_visualizer
# Crappy PAG (Process And GUI) visualizer

from pymongo import Connection, ASCENDING, DESCENDING

import sys
sys.path.insert(0, '../../GUItracing/')
sys.path.insert(0, '../../SystemTap/')

from parse_gui_trace import DesktopState


session_name = sys.argv[1]

c = Connection()
db = c.burrito_db

proc_col = db.process_trace
gui_col = db.gui_trace

for dat in proc_col.find({'session_tag': session_name}, {'phases.name':1}, sort=[('_id', ASCENDING)]):
  for p in dat['phases']:
    if p['name'] and 'monitor' in p['name']:
      print p


########NEW FILE########
__FILENAME__ = pylogger
# Installation instructions: Load as $PYTHONSTARTUP
# e.g., put this line in your .bashrc:
#   export PYTHONSTARTUP=~/burrito/PythonLogger/pylogger.py 


# TODO: this script only partially works ... we need to figure out a way
# for _history_print to run on every type of command invocation, NOT just
# on expression evaluation (which sys.displayhook does).
#
# we are also approximating the timestamp of each invoked command by
# using the timestamp of the last evaluated expression, which is
# imprecise but the best we can do considering we're using
# sys.displayhook!

# Maybe I should instead just instrument IPython to log timestamped
# history entries, since it already keeps user input history!

'''
From Fernando Perez:

  The user input is read through raw_input, or its lower-level partner,
  the read method of sys.stdin.

  IPython itself logs all that to an sqlite history database, so you
  have all user inputs always, with timestamps and more.
'''

LOGFILE = open('/var/log/burrito/current-session/python.log', 'a')


import os, sys, readline

# inlined from BurritoUtils.py ...
import time, json, datetime

def get_ms_since_epoch():
  milliseconds_since_epoch = int(time.time() * 1000)
  return milliseconds_since_epoch

def to_compact_json(obj):
  # use the most compact separators:
  return json.dumps(obj, separators=(',',':'))


PID = os.getpid()

LAST_PRINTED_ENTRY = 1

def _history_print(arg):
  global LAST_PRINTED_ENTRY, PID
  history_length = readline.get_current_history_length()
  for i in range(LAST_PRINTED_ENTRY, history_length + 1):
    # TODO: this isn't quite accurate since we're using the same
    # timestamp for all the history entries we're printing on this
    # round, but it's the best we can do for now :/
    print >> LOGFILE, to_compact_json(dict(timestamp=get_ms_since_epoch(),
                                           command=readline.get_history_item(i),
                                           pid=PID))
    LOGFILE.flush()
  print arg
  LAST_PRINTED_ENTRY = history_length + 1

sys.displayhook = _history_print


########NEW FILE########
__FILENAME__ = run_all_tracers
#!/usr/bin/env python

# Top-level burrito start-up script
#
# Make this script executable and run at start-up time to run ALL tracer scripts!
#
# Go to System -> Preferences -> Startup Applications in the Fedora 14
# GNOME menu.  And create a new entry to execute:
#   <path to this script>

import os, time
from BurritoUtils import *

# Pause a bit before running incremental_integrator.py since that relies
# on the MongoDB database service already being up and running, and
# sometimes MongoDB might start slower than expected.
time.sleep(3)

LOG_BASEDIR = '/var/log/burrito'

PASS_LITE   = '/home/researcher/burrito/SystemTap/pass-lite.stp'

GUI_TRACER_BASE = "GUItracer"
GUI_TRACER  = '/home/researcher/burrito/GUItracing/%s.py' % (GUI_TRACER_BASE,)

INTEGRATOR_BASE = 'incremental_integrator'
INTEGRATOR  = '/home/researcher/burrito/%s.py' % (INTEGRATOR_BASE,)


assert os.path.isdir(LOG_BASEDIR)
assert os.path.isfile(PASS_LITE)
assert os.path.isfile(GUI_TRACER)
assert os.path.isfile(INTEGRATOR)


# Create a unique subdirectory session name consisting of the user's
# name and current time

SESSION_NAME = '%s-%d' % (os.getenv('USER'), get_ms_since_epoch())
d = os.path.join(LOG_BASEDIR, SESSION_NAME)
assert not os.path.isdir(d)
os.mkdir(d)


# rename the existing current-session/ symlink and add a new link to SESSION_NAME
cs = os.path.join(LOG_BASEDIR, 'current-session')
if os.path.exists(cs):
  os.rename(cs, os.path.join(LOG_BASEDIR, 'previous-session'))
os.symlink(SESSION_NAME, cs)


# kill old instances of GUItracer and run this first in the background ...
os.system("pkill -f %s" % (GUI_TRACER_BASE,))
os.system("python %s 2> %s/GUITracer.err &" % (GUI_TRACER, d))

# same with the integrator
os.system("pkill -f %s" % (INTEGRATOR_BASE,))
os.system("python %s %s -s %s 2> %s/integrator.err &" % (INTEGRATOR, d, SESSION_NAME,  d))

# Execute SystemTap
# (to prevent multiple simultaneous stap sessions from running, kill all
# other stap instances before launching ... otherwise if the user logs
# out and logs back in without first rebooting, MULTIPLE stap instances
# will be running, which is undesirable)
os.system("killall stap; stap -o %s/pass-lite.out -S 10 %s 2> %s/stap.err" % (d, PASS_LITE, d))

########NEW FILE########
__FILENAME__ = BurritoUtils
../BurritoUtils.py
########NEW FILE########
__FILENAME__ = parse_stap_out
# Parses the raw output of pass-lite.stp and puts entries into MongoDB
# Created: 2011-11-01

import os, sys
from copy import deepcopy

from BurritoUtils import *

from pymongo import Connection, ASCENDING


# similar to ignored files in cde.options
# (could also add /var/cache/, /var/lock/, /var/log/, /var/run/, /var/tmp/, /tmp/)
IGNORE_DIRS = ['/dev/', '/proc/', '/sys/']

# the double-pipe delimeter isn't perfect, but it'll do for now
FIELD_DELIMITER = '||'

OPEN_VARIANTS = ('OPEN_READ', 'OPEN_WRITE', 'OPEN_READWRITE')
RW_VARIANTS   = ('READ', 'WRITE', 'MMAP_READ', 'MMAP_WRITE', 'MMAP_READWRITE')


# sub-classes simply add new fields depending on syscall_name
class RawPassLiteLogEntry:
  def __init__(self, syscall_name, timestamp, pid, ppid, uid, proc_name):
    self.syscall_name = syscall_name
    self.timestamp = timestamp
    self.pid = pid
    self.ppid = ppid
    self.uid = uid
    self.proc_name = proc_name

  def __str__(self):
    return "%d %s %d %d %s" % (self.timestamp, self.syscall_name, self.pid, self.uid, self.proc_name)


# Parse according to the format outputted by pass-lite.stp
def parse_raw_pass_lite_line(line):
  # the double-pipe delimeter isn't perfect, but it'll do for now
  toks = line.split(FIELD_DELIMITER)

  # fields that all lines should have in common
  timestamp = int(toks[0])
  pid = int(toks[1])
  ppid = int(toks[2])
  uid = int(toks[3])
  proc_name = toks[4]
  syscall_name = toks[5]
  rest = toks[6:]

  entry = RawPassLiteLogEntry(syscall_name, timestamp, pid, ppid, uid, proc_name)


  if syscall_name in OPEN_VARIANTS:
    assert len(rest) == 2
    entry.filename = rest[0]
    entry.fd = int(rest[1])

  elif syscall_name == 'OPEN_ABSPATH':
    assert len(rest) == 1
    entry.filename_abspath = rest[0]
    assert entry.filename_abspath[0] == '/' # absolute path check

  elif syscall_name in RW_VARIANTS or syscall_name == 'CLOSE':
    assert len(rest) == 1
    entry.fd = int(rest[0])

  elif syscall_name == 'PIPE':
    assert len(rest) == 2
    entry.pipe_read_fd = int(rest[0])
    entry.pipe_write_fd = int(rest[1])

  elif syscall_name == 'DUP':
    assert len(rest) == 2
    entry.src_fd = int(rest[0])
    entry.dst_fd = int(rest[1])

  elif syscall_name == 'DUP2':
    assert len(rest) == 3
    entry.src_fd = int(rest[0])
    entry.dst_fd = int(rest[1])
    # sanity check
    assert int(rest[2]) == entry.dst_fd

  elif syscall_name == 'FORK':
    assert len(rest) == 1
    entry.child_pid = int(rest[0])

  elif syscall_name == 'EXECVE':
    # it's possible for the command line (argv) itself to contain
    # FIELD_DELIMITER, so .join() everything after rest[0]
    assert len(rest) >= 3
    entry.pwd = rest[0]
    entry.exec_filename = rest[1]
    entry.argv = FIELD_DELIMITER.join(rest[2:])

  elif syscall_name == 'EXECVE_RETURN':
    assert len(rest) == 1
    entry.return_code = int(rest[0])

  elif syscall_name == 'EXIT_GROUP':
    assert len(rest) == 1
    entry.exit_code = int(rest[0])

  elif syscall_name == 'RENAME':
    assert len(rest) == 2
    entry.old_filename = rest[0]
    entry.new_filename = rest[1]
    assert entry.old_filename[0] == '/' # absolute path check
    assert entry.new_filename[0] == '/' # absolute path check

  else:
    assert False, line

  return entry


# if multiple file read/write entries occur within this amount of time,
# only keep the earlier one
FILE_ACCESS_COALESCE_MS = 200

# A process has 1 or more 'phases', where during each phase it has some
# set name.  A process changes from one phase to the next when an EXECVE
# syscall is made, so that it morphs into another executable.
class ProcessPhase:
  def __init__(self, start_time, execve_filename=None, execve_pwd=None, execve_argv=None):
    self.start_time = start_time

    self.process_name = None # to be filled in by _set_or_confirm_name()

    # note that these might be 'None' if the ProcessPhase wasn't created
    # by an execve call (i.e., it's the first phase in the process)
    self.execve_filename = execve_filename
    self.execve_pwd = execve_pwd
    self.execve_argv = execve_argv

    # Each entry is a dict mapping from filename to a SORTED LIST of
    # timestamps
    #
    # Apply filters using IGNORE_DIRS to prevent weird pseudo-files from
    # being added to these sets
    self.files_read = {}
    self.files_written = {}

    # Each entry is a tuple of (timestamp, old_filename, new_filename)
    self.files_renamed = set()


  def is_empty(self):
    if self.process_name == None:
      # sanity checks
      assert not self.files_read
      assert not self.files_written
      assert not self.files_renamed
      return True
    else:
      return False


  def _insert_coalesced_time(self, lst, timestamp):
    # lst must be a list, of course :)
    if not lst:
      lst.append(timestamp)
    else:
      # weird out-of-order case
      if timestamp < lst[-1]:
        print >> sys.stderr, "WARNING: Inserting out-of-order timestamp", timestamp, "where the latest entry is", lst[-1]

        lst.append(timestamp)
        lst.sort() # keep things in order
        # TODO: maybe do coalescing here
      else:
        # coalescing optimization
        if (lst[-1] + FILE_ACCESS_COALESCE_MS) < timestamp:
          lst.append(timestamp)


  def add_file_read(self, proc_name, timestamp, filename):
    self._set_or_confirm_name(proc_name)

    if filename not in self.files_read:
      self.files_read[filename] = []
    self._insert_coalesced_time(self.files_read[filename], timestamp)


  def add_file_write(self, proc_name, timestamp, filename):
    self._set_or_confirm_name(proc_name)
    if filename not in self.files_written:
      self.files_written[filename] = []
    self._insert_coalesced_time(self.files_written[filename], timestamp)


  def add_file_rename(self, proc_name, timestamp, old_filename, new_filename):
    self._set_or_confirm_name(proc_name)
    self.files_renamed.add((timestamp, old_filename, new_filename))

  def _set_or_confirm_name(self, proc_name):
    if self.process_name:
      # make an exception for a process named 'exe', since programs like
      # Chrome do an execve on '/proc/self/exe' to re-execute "itself",
      # so the process name is temporarily 'exe' before it reverts back to
      # its original name ... weird, I know!!!
      #
      # other weird observed cases include 'mono' (for C# apps, I presume?)
      #
      # so for now, just issue a warning ...
      #
      # TODO: perhaps a better solution is to acknowledge that a phase
      # can have multiple names and keep track of ALL names for a phase
      # rather than just one name
      if self.process_name != proc_name:
        print >> sys.stderr, "WARNING: Process phase name changed from '%s' to '%s'" % (self.process_name, proc_name)

    self.process_name = proc_name # always override it!


  def get_latest_timestamp(self):
    max_time = self.start_time
    for times in self.files_read.values() + self.files_written.values():
      for t in times:
        max_time = max(t, max_time)
    for (t, _, _) in self.files_renamed:
      max_time = max(t, max_time)
    return max_time

  def printMe(self):
    print "  Phase start:", self.start_time, self.process_name
    if self.execve_filename:
      print "    execve:", self.execve_filename
      print "      argv:", self.execve_argv
      print "       pwd:", self.execve_pwd
    print "     Files: %d read, %d written, %d renamed" % (len(self.files_read), len(self.files_written), len(self.files_renamed))


  # serialize for MongoDB
  def serialize(self):
    ret = dict(name=self.process_name,
               start_time=encode_datetime(self.start_time),
               execve_filename=self.execve_filename,
               execve_pwd=self.execve_pwd,
               execve_argv=self.execve_argv)

    # Flatten these dicts into lists, since MongoDB doesn't like
    # filenames being used as dict keys (because they might contain DOT
    # characters, which are apparently not legal in BSON/MongoDB keys).
    #
    # Also, since most files have ONE access time, make the values into
    # an integer rather than a single-element list.  However, when there
    # is more than one access time, keep the list:

    serialized_files_read = []
    for (k,v) in self.files_read.iteritems():
      if len(v) > 1:
        serialized_files_read.append(dict(filename=k, timestamp=[encode_datetime(e) for e in v]))
      else:
        assert len(v) == 1
        serialized_files_read.append(dict(filename=k, timestamp=encode_datetime(v[0])))

    serialized_files_written = []
    for (k,v) in self.files_written.iteritems():
      if len(v) > 1:
        serialized_files_written.append(dict(filename=k, timestamp=[encode_datetime(e) for e in v]))
      else:
        assert len(v) == 1
        serialized_files_written.append(dict(filename=k, timestamp=encode_datetime(v[0])))

    serialized_renames = []
    for (t, old, new) in sorted(self.files_renamed):
      serialized_renames.append(dict(timestamp=encode_datetime(t), old_filename=old, new_filename=new))


    # turn empty collections into None for simplicity
    if not serialized_files_read:
      serialized_files_read = None
    if not serialized_files_written:
      serialized_files_written = None
    if not serialized_renames:
      serialized_renames = None

    ret['files_read'] = serialized_files_read
    ret['files_written'] = serialized_files_written
    ret['files_renamed'] = serialized_renames

    return ret  
 

class Process:
  def __init__(self, pid, ppid, uid, creation_time, active_processes_dict):
    self.pid = pid
    self.ppid = ppid
 
    self.uid = uid         # the initial UID at process creation time
    self.other_uids = None # for setuid executables, create a list to store other UIDs

    self.creation_time = creation_time

    # Open file descriptors (inherit from parent on fork)
    # Key: fd (int)
    # Value: (filename, mode) where mode can be: {'r', 'w', 'rw'}
    self.opened_files = {}

    # TODO: DON'T do the following pre-seeding, since some programs
    # (e.g., kernel-controlled daemons) don't reserve fd's 0, 1, 2
    # so those fd's can be used for regular files.
    #
    # Pre-seed with stdin/stdout/stderr
    # (even though STDIN is read-only, some weirdos try to write to
    # stdin as well, so don't croak on this)
    #self.opened_files = {0: ('STDIN', 'rw'), 1: ('STDOUT', 'w'), 2: ('STDERR', 'w')}

    # Open pipes (inherit from parent on fork)
    # Each element is a triple of (creator pid, read fd, write fd)
    self.opened_pipes = set()

    self.phases = [ProcessPhase(self.creation_time)]

    # Once the process exits, it's "locked" and shouldn't be modified anymore
    self.exited = False
    self.exit_code = None
    self.exit_time = None

    self.prev_entry = None # sometimes we want to refer back to the PREVIOUS entry

    # Optimization for incremental indexing ... always update this with
    # the timestamp of the most recent event, so that we can know when
    # this Process instance was last updated
    self.most_recent_event_timestamp = creation_time

    # This is pretty gross, but all Process objects should keep a
    # reference to the same dict which maps PIDs to Process objects that
    # are active (i.e., haven't yet exited)
    self.active_processes_dict = active_processes_dict

    # Now ADD YOURSELF to active_processes_dict:
    self.active_processes_dict[self.pid] = self


  def unique_id(self):
    # put creation_time first, so that we can alphabetically sort
    return '%d-%d' % (self.creation_time, self.pid)

  def _finalize(self):
    # filter out empty phases
    self.phases = [e for e in self.phases if not e.is_empty()]

    # do some sanity checks
    assert self.exit_time
    assert self.creation_time <= self.exit_time
    for p in self.phases:
      p_latest_timestamp = p.get_latest_timestamp()
      # relax this assertion since sometimes SystemTap produces
      # timestamps that are SLIGHTLY out of order
      # (hopefully < 1000 microseconds)
      #assert p.get_latest_timestamp() <= self.exit_time
      if p_latest_timestamp > self.exit_time:
        assert p_latest_timestamp <= (self.exit_time + 1000) # fudge factor
        print >> sys.stderr, 'WARNING: p_latest_timestamp[%d] > exit_time[%d] for PID %d ... patching with %d' % (p_latest_timestamp, self.exit_time, self.pid, p_latest_timestamp)
        self.exit_time = p_latest_timestamp
 

  def printMe(self):
    print "%d [ppid: %d, uid: %d]" % (self.pid, self.ppid, self.uid),
    if self.other_uids: print "| other uids:", self.other_uids
    else: print

    print "Created:", self.creation_time,
    if self.exited: print "| Exited:", self.exit_time, "with code", self.exit_code
    else: print

    print "  Last updated:", encode_datetime(self.most_recent_event_timestamp)

    for p in self.phases:
      p.printMe()


  # serialize for MongoDB
  def serialize(self):
    ret = dict(_id=self.unique_id(), # unique ID for MongoDB
               pid=self.pid,
               ppid=self.ppid,
               uid=self.uid,
               other_uids=self.other_uids,
               creation_time=encode_datetime(self.creation_time),
               most_recent_event_timestamp=encode_datetime(self.most_recent_event_timestamp),
               exited=self.exited,
               exit_code=self.exit_code,
               phases=[e.serialize() for e in self.phases])

    # ugh ...
    if self.exit_time:
      ret['exit_time'] = encode_datetime(self.exit_time)
    else:
      ret['exit_time'] = None

    return ret


  def mark_exit(self, exit_time, exit_code):
    self.exited = True
    self.exit_time = exit_time
    self.exit_code = exit_code

    assert self.creation_time

    if (self.exit_time < self.creation_time):
      # OMG there are KRAZY weird situations where timestamps are f***ed
      # up and not in order, so if the exit time appears to be smaller
      # than the creation_time, then loop through all the timestamps
      # in this entry and pick the LARGEST one and just use that as
      # the exit time (since that's the best info we have)

      max_time = self.creation_time
      for p in self.phases:
        max_time = max(p.get_latest_timestamp(), max_time)

      max_time += 1 # bump it up by 1 so that it doesn't overlap :)

      print >> sys.stderr, 'WARNING: exit_time[%d] < creation_time[%d] for PID %d ... patching with %d' % (self.exit_time, self.creation_time, self.pid, max_time)
      self.exit_time = max_time

    self._finalize() # finalize and freeze this entry!!!


  # only call this function when there's been a VISIBLE change to self!
  def _mark_changed(self, entry):
    self.most_recent_event_timestamp = entry.timestamp # VERY important!


  # return True if entry.syscall_name == 'EXIT_GROUP'
  def add_entry(self, entry):
    assert entry.pid == self.pid # sanity check

    # for setuid executables ...
    if entry.uid != self.uid:
      if self.other_uids:
        if entry.uid not in self.other_uids:
          self.other_uids.append(entry.uid)
          self._mark_changed(entry)
      else:
        self.other_uids = [entry.uid]
        self._mark_changed(entry)

    assert not self.exited # don't allow ANY more entries after you've exited


    if entry.syscall_name in OPEN_VARIANTS:
      # OPEN_ABSPATH always preceeds another OPEN_* entry,
      # or something is wrong ...
      assert self.prev_entry.syscall_name == 'OPEN_ABSPATH'
      # use the ABSOLUTE PATH filename from prev_entry
      filename_abspath = self.prev_entry.filename_abspath

      # ok this check is a bit too harsh ... issue a WARNING if it fails
      # rather than dying.  sometimes 'close' system calls get LOST, so
      # just assume that the previous file has been closed if this new
      # one is opened with the same fd
      #assert entry.fd not in self.opened_files
      if entry.fd in self.opened_files:
        print >> sys.stderr, "WARNING: On OPEN, fd", entry.fd, "is already being used by", self.opened_files[entry.fd]


      if entry.syscall_name == 'OPEN_READ':
        self.opened_files[entry.fd] = (filename_abspath, 'r')
      elif entry.syscall_name == 'OPEN_WRITE':
        self.opened_files[entry.fd] = (filename_abspath, 'w')
      elif entry.syscall_name == 'OPEN_READWRITE':
        self.opened_files[entry.fd] = (filename_abspath, 'rw')
      else:
        assert False

    elif entry.syscall_name == 'DUP' or entry.syscall_name == 'DUP2':
      # 'close' dst_fd if necessary
      if entry.dst_fd in self.opened_files:
        del self.opened_files[entry.dst_fd]

      # do the fd duplication!
      if entry.src_fd in self.opened_files:
        self.opened_files[entry.dst_fd] = self.opened_files[entry.src_fd]

    elif entry.syscall_name == 'CLOSE':
      # ignore CLOSE calls that don't match a corresponding OPEN
      if entry.fd in self.opened_files:
        del self.opened_files[entry.fd]
      else:
        #print >> sys.stderr, 'WARNING: orphan', entry.syscall_name, entry.pid, entry.proc_name, entry.fd
        pass

    elif entry.syscall_name in RW_VARIANTS:
      try:
        (fn, mode) = self.opened_files[entry.fd]

        skip_me = False
        # ignore reads to filenames that start with IGNORE_DIRS
        for d in IGNORE_DIRS:
          if fn.startswith(d):
            skip_me = True
            break

        if not skip_me:
          args = (entry.proc_name, entry.timestamp, fn)

          if entry.syscall_name in ('READ', 'MMAP_READ'):
            assert mode == 'r' or mode == 'rw'
            self.phases[-1].add_file_read(*args)
          elif entry.syscall_name in ('WRITE', 'MMAP_WRITE'):
            assert mode == 'w' or mode == 'rw', entry
            self.phases[-1].add_file_write(*args)
          elif entry.syscall_name == 'MMAP_READWRITE':
            self.phases[-1].add_file_read(*args)
            # sometimes there are weird MMAP_READWRITE calls when the file
            # is opened in 'r' mode, so only do add_file_write() if the
            # file was actually opened in 'w' or 'rw' mode
            if mode == 'w' or mode == 'rw':
              self.phases[-1].add_file_write(*args)

          self._mark_changed(entry)
      except KeyError:
        # ignore READ/WRITE calls where the fd isn't found!
        #print >> sys.stderr, 'WARNING: orphan', entry.syscall_name, entry.pid, entry.proc_name, entry.fd
        pass

    elif entry.syscall_name == 'RENAME':
      self.phases[-1].add_file_rename(entry.proc_name, entry.timestamp, entry.old_filename, entry.new_filename)
      self._mark_changed(entry)

    elif entry.syscall_name == 'EXIT_GROUP':
      self.mark_exit(entry.timestamp, entry.exit_code)
      self._mark_changed(entry)
      return True # bye, sucka!


    elif entry.syscall_name == 'EXECVE':
      # Optimization: REMOVE previous phase if it was empty:
      if self.phases and self.phases[-1].is_empty():
        self.phases.pop()

      n = ProcessPhase(entry.timestamp, entry.exec_filename, entry.pwd, entry.argv)
      self.phases.append(n)
      self._mark_changed(entry)

    elif entry.syscall_name == 'PIPE':
      assert entry.pipe_read_fd not in self.opened_files # sanity check
      assert entry.pipe_write_fd not in self.opened_files # sanity check
      # PIPE creates two new file descriptors ...
      # (encode the pid and fd in the pseudo-filename of the pipe)
      self.opened_files[entry.pipe_read_fd] =  ('PIPE-%d-%d' % (self.pid, entry.pipe_read_fd), 'r')
      self.opened_files[entry.pipe_write_fd] = ('PIPE-%d-%d' % (self.pid, entry.pipe_write_fd), 'w')
      self.opened_pipes.add((self.pid, entry.pipe_read_fd, entry.pipe_write_fd))

    elif entry.syscall_name == 'FORK':
      # add a Process object for your offspring ...
      if entry.child_pid not in self.active_processes_dict:
        child_proc = Process(entry.child_pid, self.pid, entry.uid, entry.timestamp, self.active_processes_dict)

        # child inherits fd's and pipes from parent ... make a deepcopy!
        child_proc.opened_files = deepcopy(self.opened_files)
        child_proc.opened_pipes = deepcopy(self.opened_pipes)
      else:
        # This shouldn't happen if the SystemTap logs were perfect, but
        # in reality, some entries come in slightly OUT OF ORDER, so if
        # entry.child_pid is already in self.active_processes_dict, then
        # just trust that entry!
        #print >> sys.stderr, "WARNING: fork() child PID", entry.child_pid, "already exists!"
        pass


    self.prev_entry = entry # set previous entry for reference
    return False


# Generate entries one at a time from the file named 'fn'
def gen_entries_from_file(fn):
  print >> sys.stderr, "gen_entries_from_file('%s')" % (fn,)
  for line in open(fn):
    #print >> sys.stderr, line, # debugging
    entry = parse_raw_pass_lite_line(line.rstrip()) # strip off trailing '\n'
    yield entry


def gen_entries_from_dir(dn):
  log_files = [e for e in os.listdir(dn) if e.startswith('pass-lite.out')]

  # go through log_files in CHRONOLOGIAL order, which isn't the same as
  # an alphabetical sort by name.  e.g., we want "pass-lite.out.2" to
  # come BEFORE "pass-lite.out.10", but if we alphabetically sort, then
  # "pass-lite.out.10" will come first!
  for i in range(len(log_files)):
    cur_fn = ('pass-lite.out.' + str(i))
    assert cur_fn in log_files
    fullpath = os.path.join(dn, cur_fn)

    for entry in gen_entries_from_file(fullpath):
      yield entry



if __name__ == "__main__":
  assert False # the code below is deprecated

  dirname = sys.argv[1]
  complete_session = (sys.argv[2] == 'complete')

  #print "Indexing time:", datetime.datetime.now()
  #print "Indexing time:", int(time.time() * 1000)

  assert os.path.isdir(dirname)

  # Dict mapping PIDs to active processes (i.e., haven't yet exited)
  # Key: PID
  # Value: Process object
  pid_to_active_processes = {}

  # Key: string consisting of creation_time and PID (unique key)
  # Value: Process object
  exited_processes = {}

  last_timestamp = None
  for entry in gen_entries_from_dir(dirname):
    last_timestamp = entry.timestamp

    if entry.pid not in pid_to_active_processes:
      pid_to_active_processes[entry.pid] = Process(entry.pid, entry.ppid, entry.uid, entry.timestamp, pid_to_active_processes)

    p = pid_to_active_processes[entry.pid]

    is_process_exited = p.add_entry(entry)

    if is_process_exited:
      exited_processes[p.unique_id()] = p
      del pid_to_active_processes[entry.pid]



  if complete_session:
    # If the session is complete, then mark all still-active processes
    # as exited with end time equal to last_timestamp, then add them to
    # exited_processes
    for p in pid_to_active_processes.values():
      p.mark_exit(last_timestamp, -1) # use a -1 exit code to mark that it was killed unceremoniously :)
      exited_processes[p.unique_id()] = p

    pid_to_active_processes = {}

    print "Before optimize:", len(exited_processes)

    # Optimization: remove all entries from exited_processes that have no
    # phases and ALSO aren't the parent of any other entry in
    # exited_processes.  It's important to keep 'empty' processes that
    # are some other processes' parent, in order to keep the process tree
    # intact.

    ppids = set() # efficiency!
    for p in exited_processes.itervalues():
      ppids.add(p.ppid)

    entries_to_kill = []

    for (k, v) in exited_processes.iteritems():
      if (not v.phases) and (v.pid not in ppids):
        entries_to_kill.append(k)

    for e in entries_to_kill:
      del exited_processes[e]

    print "After optimize:", len(exited_processes)

    print "Inserting into burrito_database.syscall_trace ..."

    c = Connection()
    db = c.burrito_database
    col = db.syscall_trace

    for k in sorted(exited_processes.keys()):
      col.insert(exited_processes[k].serialize())

    print "Creating indices ..."

    col.ensure_index('pid')
    # For time range searches!  This multi-key index ensures fast
    # searches for creation_time alone too!
    col.ensure_index([('creation_time', ASCENDING), ('exit_time', ASCENDING)])

    col.ensure_index('phases.name')
    col.ensure_index('phases.start_time')
    col.ensure_index('phases.files_read.timestamp')
    col.ensure_index('phases.files_written.timestamp')
    col.ensure_index('phases.files_renamed.timestamp')

    print "ALL DONE!"


  else:
    # TODO: handle incomplete sessions, since we need to keep
    # pid_to_active_processes open to the possibility that those entries
    # will be updated in a LATER run.

    print "Active processes", len(pid_to_active_processes)
    print "Exited processes", len(exited_processes)

    for p in pid_to_active_processes.values():
      p.printMe()
      print


########NEW FILE########
__FILENAME__ = print_stap_out_HTML
# Takes 'stap-out.pickle' generated by parse_stap_out.py
# and pretty-prints it in HTML format

from parse_stap_out import Process
import cPickle, datetime

def ms_to_datetime(ms):
  return datetime.datetime.fromtimestamp(float(ms) / 1000)


def pretty_duration_str(td):
  assert type(td) is datetime.timedelta

  if td.seconds == 0:
    # anything less than 1/10 second is "instant"
    if td.microseconds < 100000:
      return 'instant'
    else:
      return '%.2gs' % (float(td.microseconds) / 1000000)
  elif td.seconds < 3600:
    m = td.seconds / 60
    s = td.seconds % 60
    return '%02d:%02d' % (m, s)
  else:
    return str(td)


all_procs = cPickle.load(open('stap-out.pickle'))

# sort by creation_time
all_procs_lst = all_procs.values()
all_procs_lst.sort(key = lambda e: e.creation_time)

initial_dt = ms_to_datetime(all_procs_lst[0].creation_time)

import os
my_uid = os.getuid()

print "Session start", initial_dt
print

for proc in all_procs_lst:
  # only print out programs that YOU'VE launched!
  if proc.uid != my_uid: continue

  print 'Name:', proc.get_canonical_name()

  parent = None
  if proc.ppid in all_procs:
    parent = all_procs[proc.ppid]


  if parent:
    print "  Parent:", parent.get_canonical_name()
  else:
    print "  Parent not found :("

  start_dt = ms_to_datetime(proc.creation_time)
  rel_start_dt = start_dt - initial_dt
  print "Start:", rel_start_dt


  if proc.uid_changed:
    print "UID changed!"


  if proc.exited:
    print "Duration:", pretty_duration_str(ms_to_datetime(proc.exit_time) - start_dt)
    if proc.exit_code != 0:
      print "EXIT WITH ERROR", proc.exit_code
  else:
    print "NOT EXITED"

  for e in proc.execve_calls:
    print '  EXEC:', e
  '''
  for e in sorted(proc.files_read):
    print '  READ:  ', e
  for e in sorted(proc.files_written):
    print '  WRITE: ', e
  for e in sorted(proc.files_renamed):
    print '  RENAME:', e
  '''

  print


########NEW FILE########
