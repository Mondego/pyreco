__FILENAME__ = AXCallbacks
# Copyright (c) 2010 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

def elemDisappearedCallback(retelem, obj, **kwargs):
   ''' Callback for checking if a UI element is no longer onscreen

       kwargs should contains some unique set of identifier (e.g. title /
       value, role)
       Returns:  Boolean
   '''
   return (not obj.findFirstR(**kwargs))


def returnElemCallback(retelem):
   ''' Callback for when a sheet appears

       Returns: element returned by observer callback
   '''
   return retelem

########NEW FILE########
__FILENAME__ = AXClasses
# Copyright (c) 2010-2011 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

import fnmatch
import AppKit
import Quartz
import time

from PyObjCTools import AppHelper
from collections import deque

from . import _a11y
import AXKeyboard
import AXCallbacks
import AXKeyCodeConstants


class BaseAXUIElement(_a11y.AXUIElement):
   '''BaseAXUIElement - Base class for UI elements.

      BaseAXUIElement implements four major things:
      1) Factory class methods for getAppRef and getSystemObject which
         properly instantiate the class.
      2) Generators and methods for finding objects for use in child classes.
      3) __getattribute__ call for invoking actions.
      4) waitFor utility based upon AX notifications.
   '''
   @classmethod
   def _getRunningApps(cls):
      '''Get a list of the running applications'''
      def runLoopAndExit():
         AppHelper.stopEventLoop()
      AppHelper.callLater(1, runLoopAndExit)
      AppHelper.runConsoleEventLoop()
      # Get a list of running applications
      ws = AppKit.NSWorkspace.sharedWorkspace()
      apps = ws.runningApplications()
      return apps

   @classmethod
   def getAppRefByPid(cls, pid):
      '''getAppRef - Get the top level element for the application specified
      by pid
      '''
      return _a11y.getAppRefByPid(cls, pid)

   @classmethod
   def getAppRefByBundleId(cls, bundleId):
      '''getAppRefByBundleId - Get the top level element for the application
         with the specified bundle ID, such as com.vmware.fusion
      '''
      ra = AppKit.NSRunningApplication
      # return value (apps) is always an array. if there is a match it will
      # have an item, otherwise it won't.
      apps = ra.runningApplicationsWithBundleIdentifier_(bundleId)
      if len(apps) == 0:
         raise ValueError(('Specified bundle ID not found in '
                           'running apps: %s' % bundleId))
      pid = apps[0].processIdentifier()
      return cls.getAppRefByPid(pid)

   @classmethod
   def getAppRefByLocalizedName(cls, name):
      '''getAppRefByLocalizedName - Get the top level element for the
         application with the specified localized name, such as
         VMware Fusion.

         Wildcards are also allowed.
      '''
      # Refresh the runningApplications list
      apps = cls._getRunningApps()
      for app in apps:
         if fnmatch.fnmatch(app.localizedName(), name):
            pid = app.processIdentifier()
            return cls.getAppRefByPid(pid)
      raise ValueError('Specified application not found in running apps.')

   @classmethod
   def getFrontmostApp(cls):
      '''getFrontmostApp - Get the current frontmost application.

         Raise a ValueError exception if no GUI applications are found.
      '''
      # Refresh the runningApplications list
      apps = cls._getRunningApps()
      for app in apps:
         pid = app.processIdentifier()
         ref = cls.getAppRefByPid(pid)
         try:
            if ref.AXFrontmost:
               return ref
         except (_a11y.ErrorUnsupported,
                 _a11y.ErrorCannotComplete,
                 _a11y.ErrorAPIDisabled):
            # Some applications do not have an explicit GUI
            # and so will not have an AXFrontmost attribute
            # Trying to read attributes from Google Chrome Helper returns
            # ErrorAPIDisabled for some reason - opened radar bug 12837995
            pass
      raise ValueError('No GUI application found.')
    
   @classmethod
   def getAnyAppWithWindow(cls):
      '''getAnyAppWithApp - Get a randow app that has windows.
        
         Raise a ValueError exception if no GUI applications are found.
      '''
      # Refresh the runningApplications list
      apps = cls._getRunningApps()
      for app in apps:
         pid = app.processIdentifier()
         ref = cls.getAppRefByPid(pid)
         if hasattr(ref, 'windows') and len(ref.windows()) > 0:
            return ref
      raise ValueError('No GUI application found.')

   @classmethod
   def getSystemObject(cls):
      '''getSystemObject - Get the top level system accessibility object'''
      return _a11y.getSystemObject(cls)

   @classmethod
   def setSystemWideTimeout(cls, timeout=0.0):
      '''setSystemWideTimeout - Set the system-wide accessibility timeout

         Optional: timeout (non-negative float; defaults to 0)
                   A value of 0 will reset the timeout to the system default
         Returns: None
      '''
      return cls.getSystemObject().setTimeout(timeout)

   @staticmethod
   def launchAppByBundleId(bundleID):
      '''launchByBundleId - launch the application with the specified bundle
         ID
      '''
      # This constant does nothing on any modern system that doesn't have
      # the classic environment installed. Encountered a bug when passing 0
      # for no options on 10.6 PyObjC.
      NSWorkspaceLaunchAllowingClassicStartup = 0x00020000
      ws = AppKit.NSWorkspace.sharedWorkspace()
      # Sorry about the length of the following line
      r=ws.launchAppWithBundleIdentifier_options_additionalEventParamDescriptor_launchIdentifier_(
         bundleID,
         NSWorkspaceLaunchAllowingClassicStartup,
         AppKit.NSAppleEventDescriptor.nullDescriptor(),
         None)
      # On 10.6, this returns a tuple - first element bool result, second is
      # a number. Let's use the bool result.
      if r[0] == False:
         raise RuntimeError('Error launching specified application.')

   @staticmethod
   def launchAppByBundlePath(bundlePath):
        ''' launchAppByBundlePath - Launch app with a given bundle path
            Return True if succeed
        '''
        ws = AppKit.NSWorkspace.sharedWorkspace()
        return ws.launchApplication_(bundlePath)

   @staticmethod
   def terminateAppByBundleId(bundleID):
       ''' terminateAppByBundleId - Terminate app with a given bundle ID
           Requires 10.6
           Return True if succeed
       '''
       ra = AppKit.NSRunningApplication
       if getattr(ra, "runningApplicationsWithBundleIdentifier_"):
           appList = ra.runningApplicationsWithBundleIdentifier_(bundleID)
           if appList and len(appList) > 0:
               app = appList[0]
               return app and app.terminate() and True or False
       return False

   def setTimeout(self, timeout=0.0):
      '''Set the accessibiltiy API timeout on the given reference

         Optional: timeout (non-negative float; defaults to 0)
                   A value of 0 will reset the timeout to the system-wide
                   value
         Returns: None
      '''
      self._setTimeout(timeout)

   def _postQueuedEvents(self, interval=0.01):
      ''' Private method to post queued events (e.g. Quartz events)

          Each event in queue is a tuple (event call, args to event call)
      '''
      while (len(self.eventList) > 0):
         (nextEvent, args) = self.eventList.popleft()
         nextEvent(*args)
         time.sleep(interval)

   def _clearEventQueue(self):
      ''' Clear the event queue '''
      if (hasattr(self, 'eventList')):
         self.eventList.clear()

   def _queueEvent(self, event, args):
      ''' Private method to queue events to run

          Each event in queue is a tuple (event call, args to event call)
      '''
      if (not hasattr(self, 'eventList')):
         self.eventList = deque([(event, args)])
         return
      self.eventList.append((event, args))

   def _addKeyToQueue(self, keychr, modFlags=0, globally=False):
      ''' Add keypress to queue

          Parameters: key character or constant referring to a non-alpha-numeric
                      key (e.g. RETURN or TAB)
                      modifiers
                      global or app specific
          Returns: None or raise ValueError exception
      '''
      # Awkward, but makes modifier-key-only combinations possible
      # (since sendKeyWithModifiers() calls this)
      if (not keychr):
         return

      if (not hasattr(self, 'keyboard')):
         self.keyboard = AXKeyboard.loadKeyboard()

      if (keychr in self.keyboard['upperSymbols'] and not modFlags):
         self._sendKeyWithModifiers(keychr, [AXKeyCodeConstants.SHIFT])
         return

      if (keychr.isupper() and not modFlags):
         self._sendKeyWithModifiers(keychr.lower(), [AXKeyCodeConstants.SHIFT])
         return

      if (keychr not in self.keyboard):
          self._clearEventQueue()
          raise ValueError('Key %s not found in keyboard layout' % keychr)

      # Press the key
      keyDown = Quartz.CGEventCreateKeyboardEvent(None,
                                                  self.keyboard[keychr],
                                                  True)
      # Release the key
      keyUp = Quartz.CGEventCreateKeyboardEvent(None,
                                                self.keyboard[keychr],
                                                False)
      # Set modflags on keyDown (default None):
      Quartz.CGEventSetFlags(keyDown, modFlags)
      # Set modflags on keyUp:
      Quartz.CGEventSetFlags(keyUp, modFlags)

      # Post the event to the given app
      if not globally:
          # To direct output to the correct application need the PSN:
          appPsn = self._getPsnForPid(self._getPid())
          self._queueEvent(Quartz.CGEventPostToPSN, (appPsn, keyDown))
          self._queueEvent(Quartz.CGEventPostToPSN, (appPsn, keyUp))
      else:
          self._queueEvent(Quartz.CGEventPost, (0, keyDown))
          self._queueEvent(Quartz.CGEventPost, (0, keyUp))

   def _sendKey(self, keychr, modFlags=0, globally=False):
      ''' Send one character with no modifiers

          Parameters: key character or constant referring to a non-alpha-numeric
                      key (e.g. RETURN or TAB)
                      modifier flags,
                      global or app specific
          Returns: None or raise ValueError exception
      '''
      escapedChrs = {
                       '\n': AXKeyCodeConstants.RETURN,
                       '\r': AXKeyCodeConstants.RETURN,
                       '\t': AXKeyCodeConstants.TAB,
                    }
      if keychr in escapedChrs:
         keychr = escapedChrs[keychr]

      self._addKeyToQueue(keychr, modFlags, globally=globally)
      self._postQueuedEvents()

   def _sendKeys(self, keystr):
      ''' Send a series of characters with no modifiers

          Parameters: keystr
          Returns: None or raise ValueError exception
      '''
      for nextChr in keystr:
         self._sendKey(nextChr)

   def _pressModifiers(self, modifiers, pressed=True, globally=False):
      ''' Press given modifiers (provided in list form)

          Parameters: modifiers list, global or app specific
          Optional:  keypressed state (default is True (down))
          Returns: Unsigned int representing flags to set
      '''
      if (not isinstance(modifiers, list)):
         raise TypeError('Please provide modifiers in list form')

      if (not hasattr(self, 'keyboard')):
         self.keyboard = AXKeyboard.loadKeyboard()

      modFlags = 0

      # Press given modifiers
      for nextMod in modifiers:
         if (nextMod not in self.keyboard):
            errStr = 'Key %s not found in keyboard layout'
            self._clearEventQueue()
            raise ValueError(errStr % self.keyboard[nextMod])
         modEvent = Quartz.CGEventCreateKeyboardEvent(Quartz.CGEventSourceCreate(0),
                                                      self.keyboard[nextMod],
                                                      pressed)
         if (not pressed):
            # Clear the modflags:
            Quartz.CGEventSetFlags(modEvent, 0)
         if globally:
             self._queueEvent(Quartz.CGEventPost, (0, modEvent))
         else:
             # To direct output to the correct application need the PSN:
             appPsn = self._getPsnForPid(self._getPid())
             self._queueEvent(Quartz.CGEventPostToPSN, (appPsn, modEvent))
         # Add the modifier flags
         modFlags += AXKeyboard.modKeyFlagConstants[nextMod]

      return modFlags

   def _holdModifierKeys(self, modifiers):
      ''' Hold given modifier keys (provided in list form)

          Parameters: modifiers list
          Returns: Unsigned int representing flags to set
      '''
      modFlags = self._pressModifiers(modifiers)
      # Post the queued keypresses:
      self._postQueuedEvents()
      return modFlags


   def _releaseModifiers(self, modifiers, globally=False):
      ''' Release given modifiers (provided in list form)

          Parameters: modifiers list
          Returns: None
      '''
      # Release them in reverse order from pressing them:
      modifiers.reverse()
      modFlags = self._pressModifiers(modifiers, pressed=False,
                                      globally=globally)
      return modFlags

   def _releaseModifierKeys(self, modifiers):
      ''' Release given modifier keys (provided in list form)

          Parameters: modifiers list
          Returns: Unsigned int representing flags to set
      '''
      modFlags = self._releaseModifiers(modifiers)
      # Post the queued keypresses:
      self._postQueuedEvents()
      return modFlags

   def _sendKeyWithModifiers(self, keychr, modifiers, globally=False):
      ''' Send one character with the given modifiers pressed

          Parameters: key character, list of modifiers, global or app specific
          Returns: None or raise ValueError exception
      '''
      if (len(keychr) > 1):
         raise ValueError('Please provide only one character to send')

      if (not hasattr(self, 'keyboard')):
         self.keyboard = AXKeyboard.loadKeyboard()

      modFlags = self._pressModifiers(modifiers, globally=globally)

      # Press the non-modifier key
      self._sendKey(keychr, modFlags, globally=globally)

      # Release the modifiers
      self._releaseModifiers(modifiers, globally=globally)

      # Post the queued keypresses:
      self._postQueuedEvents()

   def _queueMouseButton(self, coord, mouseButton, modFlags, clickCount=1, dest_coord = None):
      ''' Private method to handle generic mouse button clicking

          Parameters: coord (x, y) to click, mouseButton (e.g.,
                      kCGMouseButtonLeft), modFlags set (int)
          Optional: clickCount (default 1; set to 2 for double-click; 3 for
                    triple-click on host)
          Returns: None
      '''
      # For now allow only left and right mouse buttons:
      mouseButtons = {
                        Quartz.kCGMouseButtonLeft: 'LeftMouse',
                        Quartz.kCGMouseButtonRight: 'RightMouse',
                     }
      if (mouseButton not in mouseButtons):
         raise ValueError('Mouse button given not recognized')

      eventButtonDown = getattr(Quartz,
                                'kCGEvent%sDown' % mouseButtons[mouseButton])
      eventButtonUp = getattr(Quartz,
                              'kCGEvent%sUp' % mouseButtons[mouseButton])
      eventButtonDragged = getattr(Quartz,
                              'kCGEvent%sDragged' % mouseButtons[mouseButton])   

      # Press the button
      buttonDown = Quartz.CGEventCreateMouseEvent(None,
                                                  eventButtonDown,
                                                  coord,
                                                  mouseButton)
      # Set modflags (default None) on button down:
      Quartz.CGEventSetFlags(buttonDown, modFlags)

      # Set the click count on button down:
      Quartz.CGEventSetIntegerValueField(buttonDown,
                                         Quartz.kCGMouseEventClickState,
                                         int(clickCount))

      if dest_coord:
         #Drag and release the button
         buttonDragged = Quartz.CGEventCreateMouseEvent(None,
                                                eventButtonDragged,
                                                dest_coord,
                                                mouseButton)
         # Set modflags on the button dragged:
         Quartz.CGEventSetFlags(buttonDragged, modFlags)
    
        
          
         buttonUp = Quartz.CGEventCreateMouseEvent(None,
                                                eventButtonUp,
                                                dest_coord,
                                                mouseButton)
      else:
          # Release the button
         buttonUp = Quartz.CGEventCreateMouseEvent(None,
                                                eventButtonUp,
                                                coord,
                                                mouseButton)
      # Set modflags on the button up:
      Quartz.CGEventSetFlags(buttonUp, modFlags)

      # Set the click count on button up:
      Quartz.CGEventSetIntegerValueField(buttonUp,
                                         Quartz.kCGMouseEventClickState,
                                         int(clickCount))
      # Queue the events
      self._queueEvent(Quartz.CGEventPost,
                       (Quartz.kCGSessionEventTap, buttonDown))
      if dest_coord:
          self._queueEvent(Quartz.CGEventPost,
                           (Quartz.kCGHIDEventTap, buttonDragged))
      self._queueEvent(Quartz.CGEventPost,
                       (Quartz.kCGSessionEventTap, buttonUp))

   def _waitFor(self, timeout, notification, **kwargs):
      '''waitFor - Wait for a particular UI event to occur; this can be built
         upon in NativeUIElement for specific convenience methods.
      '''
      callback = self._matchOther
      retelem = None
      callbackArgs = None
      callbackKwargs = None

      # Allow customization of the callback, though by default use the basic
      # _match() method
      if ('callback' in kwargs):
         callback = kwargs['callback']
         del kwargs['callback']

         # Deal with these only if callback is provided:
         if ('args' in kwargs):
            if (not isinstance(kwargs['args'], tuple)):
               errStr = 'Notification callback args not given as a tuple'
               raise TypeError(errStr)

            # If args are given, notification will pass back the returned
            # element in the first positional arg
            callbackArgs = kwargs['args']
            del kwargs['args']

         if ('kwargs' in kwargs):
            if (not isinstance(kwargs['kwargs'], dict)):
               errStr = 'Notification callback kwargs not given as a dict'
               raise TypeError(errStr)

            callbackKwargs = kwargs['kwargs']
            del kwargs['kwargs']
         # If kwargs are not given as a dictionary but individually listed
         # need to update the callbackKwargs dict with the remaining items in
         # kwargs
         if (kwargs):
            if (callbackKwargs):
               callbackKwargs.update(kwargs)
            else:
               callbackKwargs = kwargs
      else:
         callbackArgs = (retelem, )
         # Pass the kwargs to the default callback
         callbackKwargs = kwargs

      return self._setNotification(timeout, notification, callback,
                                   callbackArgs,
                                   callbackKwargs);

   def _getActions(self):
      '''getActions - Retrieve a list of actions supported by the object'''
      actions = _a11y.AXUIElement._getActions(self)
      # strip leading AX from actions - help distinguish them from attributes
      return [action[2:] for action in actions]

   def _performAction(self, action):
      '''performAction - Perform the specified action'''
      _a11y.AXUIElement._performAction(self, 'AX%s' % action)

   def _generateChildren(self):
      '''_generateChildren - generator which yields all AXChildren of the
         object
      '''
      try:
         children = self.AXChildren
      except _a11y.Error:
         return
      if children:
        for child in children:
           yield child

   def _generateChildrenR(self, target=None):
      '''_generateChildrenR - generator which recursively yields all AXChildren
         of the object.
      '''
      if target is None:
         target = self
      try:
         children = target.AXChildren
      except _a11y.Error:
         return
      if children:
         for child in children:
            yield child
            for c in self._generateChildrenR(child):
               yield c

   def _match(self, **kwargs):
      '''_match - Method which indicates if the object matches specified
         criteria.

         Match accepts criteria as kwargs and looks them up on attributes.
         Actual matching is performed with fnmatch, so shell-like wildcards
         work within match strings. Examples:

         obj._match(AXTitle='Terminal*')
         obj._match(AXRole='TextField', AXRoleDescription='search text field')
      '''
      for k in kwargs.keys():
         try:
            val = getattr(self, k)
         except _a11y.Error:
            return False
         # Not all values may be strings (e.g. size, position)
         if (isinstance(val, (unicode, str))):
            if not fnmatch.fnmatch(unicode(val), kwargs[k]):
               return False
         else:
            if (not (val == kwargs[k])):
               return False
      return True

   def _matchOther(self, obj, **kwargs):
      '''matchOther - match but on another object, not self'''
      if (obj is not None):
         # Need to check that the returned UI element wasn't destroyed first:
         if (self._findFirstR(**kwargs)):
            return obj._match(**kwargs)
      return False

   def _generateFind(self, **kwargs):
      '''_generateFind - Generator which yields matches on AXChildren.'''
      for needle in self._generateChildren():
         if needle._match(**kwargs):
            yield needle

   def _generateFindR(self, **kwargs):
      '''_generateFindR - Generator which yields matches on AXChildren and
         their children.
      '''
      for needle in self._generateChildrenR():
         if needle._match(**kwargs):
            yield needle

   def _findAll(self, **kwargs):
      '''_findAll - Return a list of all children that match the specified
         criteria.
      '''
      result = []
      for item in self._generateFind(**kwargs):
         result.append(item)
      return result

   def _findAllR(self, **kwargs):
      '''_findAllR - Return a list of all children (recursively) that match
         the specified criteria.
      '''
      result = []
      for item in self._generateFindR(**kwargs):
         result.append(item)
      return result

   def _findFirst(self, **kwargs):
      '''_findFirst - Return the first object that matches the criteria.'''
      for item in self._generateFind(**kwargs):
         return item

   def _findFirstR(self, **kwargs):
      '''_findFirstR - search recursively for the first object that matches the
         criteria.
      '''
      for item in self._generateFindR(**kwargs):
         return item

   def _getApplication(self):
      '''_getApplication - get the base application UIElement.

         If the UIElement is a child of the application, it will try
         to get the AXParent until it reaches the top application level
         element.
      '''
      app = self
      while True:
         try:
            app = app.AXParent
         except _a11y.ErrorUnsupported:
            break
      return app

   def _menuItem(self, menuitem, *args):
      '''_menuItem - Return the specified menu item

         Example - refer to items by name:

         app._menuItem(app.AXMenuBar, 'File', 'New').Press()
         app._menuItem(app.AXMenuBar, 'Edit', 'Insert', 'Line Break').Press()

         Refer to items by index:

         app._menuitem(app.AXMenuBar, 1, 0).Press()

         Refer to items by mix-n-match:

         app._menuitem(app.AXMenuBar, 1, 'About TextEdit').Press()
      '''
      self._activate()
      for item in args:
         # If the item has an AXMenu as a child, navigate into it.
         # This seems like a silly abstraction added by apple's a11y api.
         if menuitem.AXChildren[0].AXRole == 'AXMenu':
            menuitem = menuitem.AXChildren[0]
         # Find AXMenuBarItems and AXMenuItems using a handy wildcard
         role = 'AXMenu*Item'
         try:
            menuitem = menuitem.AXChildren[int(item)]
         except ValueError:
            menuitem = menuitem.findFirst(AXRole='AXMenu*Item', AXTitle=item)
      return menuitem

   def _activate(self):
      '''_activate - activate the application (bringing menus and windows
         forward)
      '''
      ra = AppKit.NSRunningApplication
      app = ra.runningApplicationWithProcessIdentifier_(
               self._getPid())
      # NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps
      # == 3 - PyObjC in 10.6 does not expose these constants though so I have
      # to use the int instead of the symbolic names
      app.activateWithOptions_(3)

   def _getBundleId(self):
      '''_getBundleId - returns the bundle ID of the application'''
      ra = AppKit.NSRunningApplication
      app = ra.runningApplicationWithProcessIdentifier_(
               self._getPid())
      return app.bundleIdentifier()

   def _getLocalizedName(self):
      '''_getLocalizedName - returns the localized name of the application'''
      return self._getApplication().AXTitle

   def __getattr__(self, name):
      '''__getattr__ - Handle attribute requests in several ways:

         1) If it starts with AX, it is probably an a11y attribute. Pass
            it to the handler in _a11y which will determine that for sure.
         2) See if the attribute is an action which can be invoked on the
            UIElement. If so, return a function that will invoke the attribute.
      '''
      if (name.startswith('AX')):
         try:
            attr = self._getAttribute(name)
            return attr
         except AttributeError:
            pass

      # Populate the list of callable actions:
      actions = []
      try:
         actions = self._getActions()
      except Exception:
         pass

      if (name.startswith('AX') and (name[2:] in actions)):
         errStr = 'Actions on an object should be called without AX prepended'
         raise AttributeError(errStr)

      if name in actions:
         def performSpecifiedAction():
            # activate the app before performing the specified action
            self._activate()
            return self._performAction(name)
         return performSpecifiedAction
      else:
         raise AttributeError('Object %s has no attribute %s' % (self, name))

   def __setattr__(self, name, value):
      '''setattr - set attributes on the object'''
      if name.startswith('AX'):
         return self._setAttribute(name, value)
      else:
         _a11y.AXUIElement.__setattr__(self, name, value)

   def __repr__(self):
      '''__repr__ - Build a descriptive string for UIElements.'''
      title = repr('')
      role = '<No role!>'
      c=repr(self.__class__).partition('<class \'')[-1].rpartition('\'>')[0]
      try:
         title=repr(self.AXTitle)
      except Exception:
         try:
            title=repr(self.AXValue)
         except Exception:
            try:
               title=repr(self.AXRoleDescription)
            except Exception:
               pass
      try:
         role=self.AXRole
      except Exception:
         pass
      if len(title) > 20:
        title = title[:20] + '...\''
      return '<%s %s %s>' % (c, role, title)


class NativeUIElement(BaseAXUIElement):
   '''NativeUIElement class - expose the accessibility API in the simplest,
      most natural way possible.
   '''
   def getAttributes(self):
      '''getAttributes - get a list of the attributes available on the
         element.
      '''
      return self._getAttributes()

   def getActions(self):
      '''getActions - return a list of the actions available on the element.'''
      return self._getActions()

   def setString(self, attribute, string):
      '''setString - set the specified attribute to the specified string.'''
      return self._setString(attribute, string)

   def findFirst(self, **kwargs):
      '''findFirst - Return the first object that matches the criteria.'''
      return self._findFirst(**kwargs)

   def findFirstR(self, **kwargs):
      '''findFirstR - search recursively for the first object that matches the
         criteria.
      '''
      return self._findFirstR(**kwargs)

   def findAll(self, **kwargs):
      '''findAll - Return a list of all children that match the specified
         criteria.
      '''
      return self._findAll(**kwargs)

   def findAllR(self, **kwargs):
      '''findAllR - Return a list of all children (recursively) that match
         the specified criteria.
      '''
      return self._findAllR(**kwargs)

   def activate(self):
      '''activate - activate the application (bringing menus and windows
         forward)
      '''
      return self._activate()

   def getApplication(self):
      '''getApplication - get the base application UIElement.

         If the UIElement is a child of the application, it will try
         to get the AXParent until it reaches the top application level
         element.
      '''
      return self._getApplication()

   def menuItem(self, *args):
      '''menuItem - Return the specified menu item

         Example - refer to items by name:

         app.menuItem('File', 'New').Press()
         app.menuItem('Edit', 'Insert', 'Line Break').Press()

         Refer to items by index:

         app.menuitem(1, 0).Press()

         Refer to items by mix-n-match:

         app.menuitem(1, 'About TextEdit').Press()
      '''
      menuitem = self._getApplication().AXMenuBar
      return self._menuItem(menuitem, *args)

   def popUpItem(self, *args):
      '''popUpItem - Return the specified item in a pop up menu'''
      self.Press()
      time.sleep(.5)
      return self._menuItem(self, *args)

   def getBundleId(self):
      '''getBundleId - returns the bundle ID of the application'''
      return self._getBundleId()

   def getLocalizedName(self):
      '''getLocalizedName - returns the localized name of the application'''
      return self._getLocalizedName()

   def sendKey(self, keychr):
      '''sendKey - send one character with no modifiers'''
      return self._sendKey(keychr)

   def sendKeys(self, keystr):
      '''sendKeys - send a series of characters with no modifiers'''
      return self._sendKeys(keystr)

   def pressModifiers(self, modifiers):
      '''Hold modifier keys (e.g. [Option])'''
      return self._holdModifierKeys(modifiers)

   def releaseModifiers(self, modifiers):
      '''Release modifier keys (e.g. [Option])'''
      return self._releaseModifierKeys(modifiers)

   def sendKeyWithModifiers(self, keychr, modifiers):
      '''sendKeyWithModifiers - send one character with modifiers pressed

         Parameters: key character, modifiers (list) (e.g. [SHIFT] or
                     [COMMAND, SHIFT] (assuming you've first used
                     from pyatom.AXKeyCodeConstants import *))
      '''
      return self._sendKeyWithModifiers(keychr, modifiers, False)

   def sendGlobalKeyWithModifiers(self, keychr, modifiers):
      '''sendGlobalKeyWithModifiers - global send one character with modifiers pressed
         See sendKeyWithModifiers
      '''
      return self._sendKeyWithModifiers(keychr, modifiers, True)

   def dragMouseButtonLeft(self, coord, dest_coord, interval = 0.5):
      ''' Drag the left mouse button without modifiers pressed

          Parameters: coordinates to click on screen (tuple (x, y))
                      dest coordinates to drag to (tuple (x, y))
                      interval to send event of btn down, drag and up
          Returns: None
      '''
          
      modFlags = 0
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags, dest_coord = dest_coord)
      self._postQueuedEvents(interval = interval)
          
   def clickMouseButtonLeft(self, coord, interval=None):
      ''' Click the left mouse button without modifiers pressed

          Parameters: coordinates to click on screen (tuple (x, y))
          Returns: None
      '''
          
      modFlags = 0
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags)
      if interval:
          self._postQueuedEvents(interval=interval)
      else:
          self._postQueuedEvents()

   def clickMouseButtonRight(self, coord):
      ''' Click the right mouse button without modifiers pressed

          Parameters: coordinates to click on scren (tuple (x, y))
          Returns: None
      '''
      modFlags = 0
      self._queueMouseButton(coord, Quartz.kCGMouseButtonRight, modFlags)
      self._postQueuedEvents()

   def clickMouseButtonLeftWithMods(self, coord, modifiers, interval = None):
      ''' Click the left mouse button with modifiers pressed

          Parameters: coordinates to click; modifiers (list) (e.g. [SHIFT] or
                      [COMMAND, SHIFT] (assuming you've first used
                      from pyatom.AXKeyCodeConstants import *))
          Returns: None
      '''
      modFlags = self._pressModifiers(modifiers)
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags)
      self._releaseModifiers(modifiers)
      if interval:
         self._postQueuedEvents(interval=interval)
      else:
         self._postQueuedEvents()

   def clickMouseButtonRightWithMods(self, coord, modifiers):
      ''' Click the right mouse button with modifiers pressed

          Parameters: coordinates to click; modifiers (list)
          Returns: None
      '''
      modFlags = self._pressModifiers(modifiers)
      self._queueMouseButton(coord, Quartz.kCGMouseButtonRight, modFlags)
      self._releaseModifiers(modifiers)
      self._postQueuedEvents()

   def doubleClickMouse(self, coord):
      ''' Double-click primary mouse button

          Parameters: coordinates to click (assume primary is left button)
          Returns: None
      '''
      modFlags = 0
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags)
      # This is a kludge:
      # If directed towards a Fusion VM the clickCount gets ignored and this
      # will be seen as a single click, so in sequence this will be a double-
      # click
      # Otherwise to a host app only this second one will count as a double-
      # click
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags,
                             clickCount=2)
      self._postQueuedEvents()

   def tripleClickMouse(self, coord):
      ''' Triple-click primary mouse button

          Parameters: coordinates to click (assume primary is left button)
          Returns: None
      '''
      # Note above re: double-clicks applies to triple-clicks
      modFlags = 0
      for i in range(2):
         self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags)
      self._queueMouseButton(coord, Quartz.kCGMouseButtonLeft, modFlags,
                             clickCount=3)
      self._postQueuedEvents()

   def waitFor(self, timeout, notification, **kwargs):
      '''waitFor - generic wait for a UI event that matches the specified
         criteria to occur.

         For customization of the callback, use keyword args labeled
         'callback', 'args', and 'kwargs' for the callback fn, callback args,
         and callback kwargs, respectively.  Also note that on return,
         the observer-returned UI element will be included in the first
         argument if 'args' are given.  Note also that if the UI element is
         destroyed, callback should not use it, otherwise the function will
         hang.
      '''
      return self._waitFor(timeout, notification, **kwargs)

   def waitForCreation(self, timeout=10, notification='AXCreated'):
      ''' Convenience method to wait for creation of some UI element

          Returns: The element created
      '''
      callback = AXCallbacks.returnElemCallback
      retelem = None
      args = (retelem, )

      return self.waitFor(timeout, notification, callback=callback,
                          args=args)

   def waitForWindowToAppear(self, winName, timeout=10):
      ''' Convenience method to wait for a window with the given name to appear

          Returns: Boolean
      '''
      return self.waitFor(timeout, 'AXWindowCreated', AXTitle=winName)

   def waitForWindowToDisappear(self, winName, timeout=10):
      ''' Convenience method to wait for a window with the given name to
          disappear

          Returns: Boolean
      '''
      callback = AXCallbacks.elemDisappearedCallback
      retelem = None
      args = (retelem, self)

      # For some reason for the AXUIElementDestroyed notification to fire,
      # we need to have a reference to it first
      win = self.findFirst(AXRole='AXWindow', AXTitle=winName)
      return self.waitFor(timeout, 'AXUIElementDestroyed',
                          callback=callback, args=args,
                          AXRole='AXWindow', AXTitle=winName)

   def waitForSheetToAppear(self, timeout=10):
      ''' Convenience method to wait for a sheet to appear

          Returns: the sheet that appeared (element) or None
      '''
      return self.waitForCreation(timeout, 'AXSheetCreated')

   def waitForValueToChange(self, timeout=10):
      ''' Convenience method to wait for value attribute of given element to
          change

          Some types of elements (e.g. menu items) have their titles change,
          so this will not work for those.  This seems to work best if you set
          the notification at the application level.

          Returns: Element or None
      '''
      # Want to identify that the element whose value changes matches this
      # object's.  Unique identifiers considered include role and position
      # This seems to work best if you set the notification at the application
      # level
      callback = AXCallbacks.returnElemCallback
      retelem = None
      return self.waitFor(timeout, 'AXValueChanged', callback=callback,
                          args=(retelem, ))

   def waitForFocusToChange(self, newFocusedElem, timeout=10):
      ''' Convenience method to wait for focused element to change (to new
          element given)

          Returns: Boolean
      '''
      return self.waitFor(timeout, 'AXFocusedUIElementChanged',
                          AXRole=newFocusedElem.AXRole,
                          AXPosition=newFocusedElem.AXPosition)

   def waitForFocusedWindowToChange(self, nextWinName, timeout=10):
      ''' Convenience method to wait for focused window to change

          Returns: Boolean
      '''
      callback = AXCallbacks.returnElemCallback
      retelem = None
      return self.waitFor(timeout, 'AXFocusedWindowChanged',
                          AXTitle=nextWinName)

   def _convenienceMatch(self, role, attr, match):
      '''Method used by role based convenience functions to find a match'''
      kwargs = {}
      # If the user supplied some text to search for, supply that in the kwargs
      if match:
         kwargs[attr] = match
      return self.findAll(AXRole=role, **kwargs)

   def _convenienceMatchR(self, role, attr, match):
      '''Method used by role based convenience functions to find a match'''
      kwargs = {}
      # If the user supplied some text to search for, supply that in the kwargs
      if match:
         kwargs[attr] = match
      return self.findAllR(AXRole=role, **kwargs)

   def textAreas(self, match=None):
      '''Return a list of text areas with an optional match parameter'''
      return self._convenienceMatch('AXTextArea', 'AXTitle', match)

   def textAreasR(self, match=None):
      '''Return a list of text areas with an optional match parameter'''
      return self._convenienceMatchR('AXTextArea', 'AXTitle', match)

   def textFields(self, match=None):
      '''Return a list of textfields with an optional match parameter'''
      return self._convenienceMatch('AXTextField', 'AXRoleDescription', match)

   def textFieldsR(self, match=None):
      '''Return a list of textfields with an optional match parameter'''
      return self._convenienceMatchR('AXTextField', 'AXRoleDescription', match)

   def buttons(self, match=None):
      '''Return a list of buttons with an optional match parameter'''
      return self._convenienceMatch('AXButton', 'AXTitle', match)

   def buttonsR(self, match=None):
      '''Return a list of buttons with an optional match parameter'''
      return self._convenienceMatchR('AXButton', 'AXTitle', match)

   def windows(self, match=None):
      '''Return a list of windows with an optional match parameter'''
      return self._convenienceMatch('AXWindow', 'AXTitle', match)

   def windowsR(self, match=None):
      '''Return a list of windows with an optional match parameter'''
      return self._convenienceMatchR('AXWindow', 'AXTitle', match)

   def sheets(self, match=None):
      '''Return a list of sheets with an optional match parameter'''
      return self._convenienceMatch('AXSheet', 'AXDescription', match)

   def sheetsR(self, match=None):
      '''Return a list of sheets with an optional match parameter'''
      return self._convenienceMatchR('AXSheet', 'AXDescription', match)

   def staticTexts(self, match=None):
      '''Return a list of statictexts with an optional match parameter'''
      return self._convenienceMatch('AXStaticText', 'AXValue', match)

   def staticTextsR(self, match=None):
      '''Return a list of statictexts with an optional match parameter'''
      return self._convenienceMatchR('AXStaticText', 'AXValue', match)

   def groups(self, match=None):
      '''Return a list of groups with an optional match parameter'''
      return self._convenienceMatch('AXGroup', 'AXRoleDescription', match)

   def groupsR(self, match=None):
      '''Return a list of groups with an optional match parameter'''
      return self._convenienceMatchR('AXGroup', 'AXRoleDescription', match)

   def radioButtons(self, match=None):
      '''Return a list of radio buttons with an optional match parameter'''
      return self._convenienceMatch('AXRadioButton', 'AXTitle', match)

   def radioButtonsR(self, match=None):
      '''Return a list of radio buttons with an optional match parameter'''
      return self._convenienceMatchR('AXRadioButton', 'AXTitle', match)

   def popUpButtons(self, match=None):
      '''Return a list of popup menus with an optional match parameter'''
      return self._convenienceMatch('AXPopUpButton', 'AXTitle', match)

   def popUpButtonsR(self, match=None):
      '''Return a list of popup menus with an optional match parameter'''
      return self._convenienceMatchR('AXPopUpButton', 'AXTitle', match)

   def rows(self, match=None):
      '''Return a list of rows with an optional match parameter'''
      return self._convenienceMatch('AXRow', 'AXTitle', match)

   def rowsR(self, match=None):
      '''Return a list of rows with an optional match parameter'''
      return self._convenienceMatchR('AXRow', 'AXTitle', match)

   def sliders(self, match=None):
      '''Return a list of sliders with an optional match parameter'''
      return self._convenienceMatch('AXSlider', 'AXValue', match)

   def slidersR(self, match=None):
      '''Return a list of sliders with an optional match parameter'''
      return self._convenienceMatchR('AXSlider', 'AXValue', match)

########NEW FILE########
__FILENAME__ = AXKeyboard
# Copyright (c) 2010 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

import Quartz

from AXKeyCodeConstants import *


# Based on the flags provided in the Quartz documentation it does not seem
# that we can distinguish between left and right modifier keys, even though
# there are different virtual key codes offered between the two sets.
# Thus for now we offer only a generic modifier key set w/o L-R distinction.
modKeyFlagConstants = {
                         COMMAND:    Quartz.kCGEventFlagMaskCommand,
                         SHIFT:      Quartz.kCGEventFlagMaskShift,
                         OPTION:     Quartz.kCGEventFlagMaskAlternate,
                         CONTROL:    Quartz.kCGEventFlagMaskControl,
                      }


def loadKeyboard():
   ''' Load a given keyboard mapping (of characters to virtual key codes)

       Default is US keyboard
       Parameters: None (relies on the internationalization settings)
       Returns: A dictionary representing the current keyboard mapping (of
                characters to keycodes)
   '''
   # Currently assumes US keyboard
   keyboardLayout = {}
   keyboardLayout = DEFAULT_KEYBOARD
   keyboardLayout.update(specialKeys)

   return keyboardLayout

########NEW FILE########
__FILENAME__ = AXKeyCodeConstants
# Copyright (c) 2010 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

# Special keys
TAB            = '<tab>'
RETURN         = '<return>'
ESCAPE         = '<escape>'
CAPS_LOCK      = '<capslock>'
DELETE         = '<delete>'
NUM_LOCK       = '<num_lock>'
SCROLL_LOCK    = '<scroll_lock>'
PAUSE          = '<pause>'
BACKSPACE      = '<backspace>'
INSERT         = '<insert>'

# Cursor movement
UP             = '<cursor_up>'
DOWN           = '<cursor_down>'
LEFT           = '<cursor_left>'
RIGHT          = '<cursor_right>'
PAGE_UP        = '<page_up>'
PAGE_DOWN      = '<page_down>'
HOME           = '<home>'
END            = '<end>'

# Numeric keypad
NUM_0          = '<num_0>'
NUM_1          = '<num_1>'
NUM_2          = '<num_2>'
NUM_3          = '<num_3>'
NUM_4          = '<num_4>'
NUM_5          = '<num_5>'
NUM_6          = '<num_6>'
NUM_7          = '<num_7>'
NUM_8          = '<num_8>'
NUM_9          = '<num_9>'
NUM_ENTER      = '<num_enter>'
NUM_PERIOD     = '<num_.>'
NUM_PLUS       = '<num_+>'
NUM_MINUS      = '<num_->'
NUM_MULTIPLY   = '<num_*>'
NUM_DIVIDE     = '<num_/>'

# Function keys
F1             = '<f1>'
F2             = '<f2>'
F3             = '<f3>'
F4             = '<f4>'
F5             = '<f5>'
F6             = '<f6>'
F7             = '<f7>'
F8             = '<f8>'
F9             = '<f9>'
F10            = '<f10>'
F11            = '<f11>'
F12            = '<f12>'

# Modifier keys
COMMAND_L      = '<command_l>'
SHIFT_L        = '<shift_l>'
OPTION_L       = '<option_l>'
CONTROL_L      = '<control_l>'

COMMAND_R      = '<command_r>'
SHIFT_R        = '<shift_r>'
OPTION_R       = '<option_r>'
CONTROL_R      = '<control_r>'

# Default modifier keys -> left:
COMMAND        = COMMAND_L
SHIFT          = SHIFT_L
OPTION         = OPTION_L
CONTROL        = CONTROL_L


# Define a dictionary representing characters mapped to their virtual key codes
# Lifted from the mappings found in kbdptr.h in the osxvnc project
# Mapping is: character -> virtual keycode for each character / symbol / key
# as noted below

US_keyboard = {
                 # Letters
                 'a':  0,
                 'b':  11,
                 'c':  8,
                 'd':  2,
                 'e':  14,
                 'f':  3,
                 'g':  5,
                 'h':  4,
                 'i':  34,
                 'j':  38,
                 'k':  40,
                 'l':  37,
                 'm':  46,
                 'n':  45,
                 'o':  31,
                 'p':  35,
                 'q':  12,
                 'r':  15,
                 's':  1,
                 't':  17,
                 'u':  32,
                 'v':  9,
                 'w':  13,
                 'x':  7,
                 'y':  16,
                 'z':  6,

                 # Numbers
                 '0':  29,
                 '1':  18,
                 '2':  19,
                 '3':  20,
                 '4':  21,
                 '5':  23,
                 '6':  22,
                 '7':  26,
                 '8':  28,
                 '9':  25,

                 # Symbols
                 '!':  18,
                 '@':  19,
                 '#':  20,
                 '$':  21,
                 '%':  23,
                 '^':  22,
                 '&':  26,
                 '*':  28,
                 '(':  25,
                 ')':  29,
                 '-':  27,        # Dash
                 '_':  27,        # Underscore
                 '=':  24,
                 '+':  24,
                 '`':  50,        # Backtick
                 '~':  50,
                 '[':  33,
                 ']':  30,
                 '{':  33,
                 '}':  30,
                 ';':  41,
                 ':':  41,
                 "'":  39,
                 '"':  39,
                 ',':  43,
                 '<':  43,
                 '.':  47,
                 '>':  47,
                 '/':  44,
                 '?':  44,
                 '\\': 42,
                 '|':  42,        # Pipe
                 TAB:  48,        # Tab: Shift-Tab sent for Tab
                 ' ':  49,        # Space

                 # Characters that on the US keyboard require use with Shift
                 'upperSymbols': [
                                     '!',
                                     '@',
                                     '#',
                                     '$',
                                     '%',
                                     '^',
                                     '&',
                                     '*',
                                     '(',
                                     ')',
                                     '_',
                                     '+',
                                     '~',
                                     '{',
                                     '}',
                                     ':',
                                     '"',
                                     '<',
                                     '>',
                                     '?',
                                     '|',
                                 ]
             }


# Mapping for special (meta) keys
specialKeys = {
                 # Special keys
                 RETURN:           36,
                 DELETE:           117,
                 TAB:              48,
                 ESCAPE:           53,
                 CAPS_LOCK:        57,
                 NUM_LOCK:         71,
                 SCROLL_LOCK:      107,
                 PAUSE:            113,
                 BACKSPACE:        51,
                 INSERT:           114,

                 # Cursor movement
                 UP:               126,
                 DOWN:             125,
                 LEFT:             123,
                 RIGHT:            124,
                 PAGE_UP:          116,
                 PAGE_DOWN:        121,

                 # Numeric keypad
                 NUM_0:            82,
                 NUM_1:            83,
                 NUM_2:            84,
                 NUM_3:            85,
                 NUM_4:            86,
                 NUM_5:            87,
                 NUM_6:            88,
                 NUM_7:            89,
                 NUM_8:            91,
                 NUM_9:            92,
                 NUM_ENTER:        76,
                 NUM_PERIOD:       65,
                 NUM_PLUS:         69,
                 NUM_MINUS:        78,
                 NUM_MULTIPLY:     67,
                 NUM_DIVIDE:       75,

                 # Function keys
                 F1:               122,
                 F2:               120,
                 F3:               99,
                 F4:               118,
                 F5:               96,
                 F6:               97,
                 F7:               98,
                 F8:               100,
                 F9:               101,
                 F10:              109,
                 F11:              103,
                 F12:              111,

                  # Modifier keys
                 COMMAND_L:        55,
                 SHIFT_L:          56,
                 OPTION_L:         58,
                 CONTROL_L:        59,

                 COMMAND_R:        54,
                 SHIFT_R:          60,
                 OPTION_R:         61,
                 CONTROL_R:        62,
              }

# Default keyboard layout
DEFAULT_KEYBOARD = US_keyboard

########NEW FILE########
__FILENAME__ = Clipboard
# Copyright (c) 2010 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

import types
import AppKit
import pprint
import logging
import Foundation


class Clipboard(object):
   ''' Class to represent clipboard-related operations for text '''

   # String encoding type
   utf8encoding = Foundation.NSUTF8StringEncoding

   # Class attributes to distinguish types of data:
   # Reference:
   # http://developer.apple.com/mac/library/documentation/Cocoa/Reference/
   #     ApplicationKit/Classes/NSPasteboard_Class/Reference/Reference.html

   # Text data type
   STRING = AppKit.NSStringPboardType
   # Rich-text format data type (e.g. rtf documents)
   RTF = AppKit.NSRTFPboardType
   # Image datatype (e.g. tiff)
   IMAGE = AppKit.NSTIFFPboardType
   # URL data type (not just web but file locations also)
   URL = AppKit.NSURLPboardType
   # Color datatype - not sure if we'll have to use this one
   # Supposedly replaced in 10.6 but the pyobjc AppKit module doesn't have the
   # new data type as an attribute
   COLOR = AppKit.NSColorPboardType

   # You can extend this list of data types
   # e.g. File copy and paste between host and guest
   # Not sure if text copy and paste between host and guest falls under STRING/
   # RTF or not
   # List of PboardTypes I found in AppKit:
   # NSColorPboardType
   # NSCreateFileContentsPboardType
   # NSCreateFilenamePboardType
   # NSDragPboard
   # NSFileContentsPboardType
   # NSFilenamesPboardType
   # NSFilesPromisePboardType
   # NSFindPanelSearchOptionsPboardType
   # NSFindPboard
   # NSFontPboard
   # NSFontPboardType
   # NSGeneralPboard
   # NSHTMLPboardType
   # NSInkTextPboardType
   # NSMultipleTextSelectionPboardType
   # NSPDFPboardType
   # NSPICTPboardType
   # NSPostScriptPboardType
   # NSRTFDPboardType
   # NSRTFPboardType
   # NSRulerPboard
   # NSRulerPboardType
   # NSSoundPboardType
   # NSStringPboardType
   # NSTIFFPboardType
   # NSTabularTextPboardType
   # NSURLPboardType
   # NSVCardPboardType

   @classmethod
   def paste(cls):
      ''' Method to get the clipboard data ('Paste')

          Returns: Data (string) retrieved or None if empty.  Exceptions from
          AppKit will be handled by caller.
      '''
      data = None

      pb = AppKit.NSPasteboard.generalPasteboard()

      # If we allow for multiple data types (e.g. a list of data types)
      # we will have to add a condition to check just the first in the
      # list of datatypes)
      data = pb.stringForType_(cls.STRING)
      return data

   @classmethod
   def copy(cls, data):
      ''' Method to set the clipboard data ('Copy')

          Parameters: data to set (string)
          Optional: datatype if it's not a string
          Returns: True / False on successful copy, Any exception raised (like
                   passes the NSPasteboardCommunicationError) should be caught
                   by the caller.
      '''
      pp = pprint.PrettyPrinter()

      copyData = 'Data to copy (put in pasteboard): %s'
      logging.debug(copyData % pp.pformat(data))

      # Clear the pasteboard first:
      cleared = cls.clearAll()
      if (not cleared):
         logging.warning('Clipboard could not clear properly')
         return False

      # Prepare to write the data
      # If we just use writeObjects the sequence to write to the clipboard is
      # a) Call clearContents()
      # b) Call writeObjects() with a list of objects to write to the clipboard
      if (type(data) is not types.ListType):
         data = [data]

      pb = AppKit.NSPasteboard.generalPasteboard()
      pbSetOk = pb.writeObjects_(data)

      return bool(pbSetOk)

   @classmethod
   def clearContents(cls):
      ''' Clear contents of general pasteboard

          Future enhancement can include specifying which clipboard to clear
          Returns: True on success; caller should expect to catch exceptions,
                   probably from AppKit (ValueError)
      '''
      logMsg = 'Request to clear contents of pasteboard: general'
      logging.debug(logMsg)
      pb = AppKit.NSPasteboard.generalPasteboard()
      pb.clearContents()
      return True

   @classmethod
   def clearProperties(cls):
      ''' Clear properties of general pasteboard

          Future enhancement can include specifying which clipboard's properties
          to clear
          Returns: True on success; caller should catch exceptions raised,
                   e.g. from AppKit (ValueError)
      '''
      logMsg = 'Request to clear properties of pasteboard: general'
      logging.debug(logMsg)
      pb = AppKit.NSPasteboard.generalPasteboard()
      pb.clearProperties()

      return True

   @classmethod
   def clearAll(cls):
      ''' Clear contents and properties of general pasteboard

          Future enhancement can include specifying which clipboard's properties
          to clear
          Returns: Boolean True on success; caller should handle exceptions
      '''
      contentsCleared = cls.clearContents()
      propsCleared = cls.clearProperties()

      return True

   @classmethod
   def isEmpty(cls, datatype=None):
      ''' Method to test if the general pasteboard is empty or not with respect
          to the type of object you want

          Parameters: datatype (defaults to strings)
          Returns: Boolean True (empty) / False (has contents); Raises
                   exception (passes any raised up)
      '''
      if (not datatype):
         datatype = AppKit.NSString
      if (type(datatype) is not types.ListType):
         datatype = [datatype]
      pp = pprint.PrettyPrinter()
      logging.debug('Desired datatypes: %s' % pp.pformat(datatype))
      optDict = {}
      logging.debug('Results filter is: %s' % pp.pformat(optDict))

      try:
         logMsg = 'Request to verify pasteboard is empty'
         logging.debug(logMsg)
         pb = AppKit.NSPasteboard.generalPasteboard()
         # canReadObjectForClasses_options_() seems to return an int (> 0 if
         # True)
         # Need to negate to get the sense we want (True if can not read the
         # data type from the pasteboard)
         itsEmpty = not bool(pb.canReadObjectForClasses_options_(datatype,
                                                                 optDict))
      except ValueError, error:
         logging.error(error)
         raise

      return bool(itsEmpty)


########NEW FILE########
__FILENAME__ = client
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Eitan Isaacson <eitan@ascender.com>
#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009 Eitan Isaacson
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""client routines for LDTP"""

import os
import re
import sys
import time
import signal
import platform
import traceback
import subprocess
from socket import error as SocketError
from atomac.ldtp.log import logger
from atomac.ldtp.client_exception import LdtpExecutionError, ERROR_CODE

try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
_python3 = False
_python26 = False
if sys.version_info[:2] <= (2, 6):
    _python26 = True
if sys.version_info[:2] >= (3, 0):
    _python3 = True
_ldtp_windows_env = False
if 'LDTP_DEBUG' in os.environ:
    _ldtp_debug = os.environ['LDTP_DEBUG']
else:
    _ldtp_debug = None
if 'LDTP_XML_DEBUG' in os.environ:
    verbose = 1
else:
    verbose = 0
if 'LDTP_SERVER_ADDR' in os.environ:
    _ldtp_server_addr = os.environ['LDTP_SERVER_ADDR']
else:
    _ldtp_server_addr = 'localhost'
if 'LDTP_SERVER_PORT' in os.environ:
    _ldtp_server_port = os.environ['LDTP_SERVER_PORT']
else:
    _ldtp_server_port = '4118'
if 'LDTP_WINDOWS' in os.environ or (sys.platform.find('darwin') == -1 and
                                    sys.platform.find('win') != -1):
    if 'LDTP_LINUX' in os.environ:
        _ldtp_windows_env = False
    else:
        _ldtp_windows_env = True
else:
   _ldtp_windows_env = False

class _Method(xmlrpclib._Method):
    def __call__(self, *args, **kwargs):
        if _ldtp_debug:
            logger.debug('%s(%s)' % (self.__name, \
                                         ', '.join(map(repr, args) + ['%s=%s' % (k, repr(v)) \
                                                                          for k, v in kwargs.items()])))
        return self.__send(self.__name, args)

class Transport(xmlrpclib.Transport):
    def _handle_signal(self, signum, frame):
        if _ldtp_debug:
            if signum == signal.SIGCHLD:
                print("ldtpd exited!")
            elif signum == signal.SIGUSR1:
                print("SIGUSR1 received. ldtpd ready for requests.")
            elif signum == signal.SIGALRM:
                print("SIGALRM received. Timeout waiting for SIGUSR1.")

    def _spawn_daemon(self):
        pid = os.getpid()
        if _ldtp_windows_env:
            if _ldtp_debug:
                cmd = 'start cmd /K CobraWinLDTP.exe'
            else:
                cmd = 'CobraWinLDTP.exe'
            subprocess.Popen(cmd, shell = True)
            self._daemon = True
        elif platform.mac_ver()[0] != '':
            pycmd = 'import atomac.ldtpd; atomac.ldtpd.main(parentpid=%s)' % pid
            self._daemon = os.spawnlp(os.P_NOWAIT, 'python',
                                      'python', '-c', pycmd)
        else:
            pycmd = 'import ldtpd; ldtpd.main(parentpid=%s)' % pid
            self._daemon = os.spawnlp(os.P_NOWAIT, 'python',
                                      'python', '-c', pycmd)
    # http://www.itkovian.net/base/transport-class-for-pythons-xml-rpc-lib/
    ##
    # Connect to server.
    #
    # @param host Target host.
    # @return A connection handle.

    if not _python26 and not _python3:
        # Add to the class, only if > python 2.5
        def make_connection(self, host):
            # create a HTTP connection object from a host descriptor
            import httplib
            host, extra_headers, x509 = self.get_host_info(host)
            return httplib.HTTPConnection(host)
    ##
    # Send a complete request, and parse the response.
    #
    # @param host Target host.
    # @param handler Target PRC handler.
    # @param request_body XML-RPC request body.
    # @param verbose Debugging flag.
    # @return XML response.

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        retry_count = 1
        while True:
            try:
                if _python26:
                    # Noticed this in Hutlab environment (Windows 7 SP1)
                    # Activestate python 2.5, use the old method
                    return xmlrpclib.Transport.request(
                        self, host, handler, request_body, verbose=verbose)
                if not _python3:
  		    # Follwing implementation not supported in Python <= 2.6
                    h = self.make_connection(host)
                    if verbose:
                        h.set_debuglevel(1)

                    self.send_request(h, handler, request_body)
                    self.send_host(h, host)
                    self.send_user_agent(h)
                    self.send_content(h, request_body)
                else:
                    h=self.send_request(host, handler, request_body, bool(verbose))

                response = h.getresponse()

                if response.status != 200:
                    raise xmlrpclib.ProtocolError(host + handler, response.status,
                                        response.reason, response.msg.headers)

                payload = response.read()
                parser, unmarshaller = self.getparser()
                parser.feed(payload)
                parser.close()

                return unmarshaller.close()
            except SocketError as e:
                if ((_ldtp_windows_env and e[0] == 10061) or \
                        (hasattr(e, 'errno') and (e.errno == 111 or \
                                                      e.errno == 61 or \
                                                      e.errno == 146))) \
                        and 'localhost' in host:
                    if hasattr(self, 'close'):
                        # On Windows XP SP3 / Python 2.5, close doesn't exist
                        self.close()
                    if retry_count == 1:
                        retry_count += 1
                        if not _ldtp_windows_env:
                            sigusr1 = signal.signal(signal.SIGUSR1, self._handle_signal)
                            sigalrm = signal.signal(signal.SIGALRM, self._handle_signal)
                            sigchld = signal.signal(signal.SIGCHLD, self._handle_signal)
                        self._spawn_daemon()
                        if _ldtp_windows_env:
                            time.sleep(5)
                        else:
                            signal.alarm(15) # Wait 15 seconds for ldtpd
                            signal.pause()
                            # restore signal handlers
                            signal.alarm(0)
                            signal.signal(signal.SIGUSR1, sigusr1)
                            signal.signal(signal.SIGALRM, sigalrm)
                            signal.signal(signal.SIGCHLD, sigchld)
                        continue
                    else:
                        raise
                # else raise exception
                raise
            except xmlrpclib.Fault as e:
                if hasattr(self, 'close'):
                    self.close()
                if e.faultCode == ERROR_CODE:
                    raise LdtpExecutionError(e.faultString.encode('utf-8'))
                else:
                    raise e

    def __del__(self):
        try:
            self.kill_daemon()
        except:
            # To fix https://github.com/pyatom/pyatom/issues/61
            pass

    def kill_daemon(self):
        try:
            if _ldtp_windows_env and self._daemon:
                # If started by the current current, then terminate
                # else, silently quit
                subprocess.Popen('taskkill /F /IM CobraWinLDTP.exe',
                                 shell = True, stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE).communicate()
            else:
                os.kill(self._daemon, signal.SIGKILL)
        except AttributeError:
            pass

class LdtpClient(xmlrpclib.ServerProxy):
    def __init__(self, uri, encoding=None, verbose=0, use_datetime=0):
        xmlrpclib.ServerProxy.__init__(
            self, uri, Transport(), encoding, verbose, 1, use_datetime)

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self._ServerProxy__request, name)

    def kill_daemon(self):
        self._ServerProxy__transport.kill_daemon()

    def setHost(self, host):
        setattr(self, '_ServerProxy__host', host)

_client = LdtpClient('http://%s:%s' % (_ldtp_server_addr, _ldtp_server_port),
                     verbose = verbose)

########NEW FILE########
__FILENAME__ = client_exception
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Eitan Isaacson <eitan@ascender.com>
#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009 Eitan Isaacson
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Python LDTP exception"""

ERROR_CODE = 123

class LdtpExecutionError(Exception):
    pass

########NEW FILE########
__FILENAME__ = log
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Eitan Isaacson <eitan@ascender.com>
#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009 Eitan Isaacson
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Log routines for LDTP"""

from os import environ as env
import logging

AREA = 'ldtp.client'
ENV_LOG_LEVEL = 'LDTP_LOG_LEVEL'
ENV_LOG_OUT = 'LDTP_LOG_OUT'

log_level = getattr(logging, env.get(ENV_LOG_LEVEL, 'NOTSET'), logging.NOTSET)

logger = logging.getLogger(AREA)

if ENV_LOG_OUT not in env:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(name)-11s %(levelname)-8s %(message)s'))
else:
    handler = logging.FileHandler(env[ENV_LOG_OUT])
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))

logger.addHandler(handler)

logger.setLevel(log_level)

########NEW FILE########
__FILENAME__ = state
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Python routines for LDTP"""

ICONIFIED = "iconified"
INVALID = "invalid"
PRESSED = "pressed"
EXPANDABLE = "expandable"
VISIBLE = "visible"
LAST_DEFINED = "last_defined"
BUSY = "busy"
EXPANDED = "expanded"
MANAGES_DESCENDANTS = "manages_descendants"
IS_DEFAULT = "is_default"
INDETERMINATE = "indeterminate"
REQUIRED = "required"
TRANSIENT = "transient"
CHECKED = "checked"
SENSITIVE = "sensitive"
COLLAPSED = "collapsed"
STALE = "stale"
OPAQUE = "opaque"
ENABLED = "enabled"
HAS_TOOLTIP = "has_tooltip"
SUPPORTS_AUTOCOMPLETION = "supports_autocompletion"
FOCUSABLE = "focusable"
SELECTABLE = "selectable"
ACTIVE = "active"
HORIZONTAL = "horizontal"
VISITED = "visited"
INVALID_ENTRY = "invalid_entry"
FOCUSED = "focused"
MODAL = "modal"
VERTICAL = "vertical"
SELECTED = "selected"
SHOWING = "showing"
ANIMATED = "animated"
EDITABLE = "editable"
MULTI_LINE = "multi_line"
SINGLE_LINE = "single_line"
SELECTABLE_TEXT = "selectable_text"
ARMED = "armed"
DEFUNCT = "defunct"
MULTISELECTABLE = "multiselectable"
RESIZABLE = "resizable"
TRUNCATED = "truncated"

########NEW FILE########
__FILENAME__ = combo_box
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Combobox class."""

import re
from atomac import AXKeyCodeConstants

from utils import Utils
from server_exception import LdtpServerException

class ComboBox(Utils):
    def selectitem(self, window_name, object_name, item_name):
        """
        Select combo box / layered pane item
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param item_name: Item name to select
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        self._grabfocus(object_handle.AXWindow)
        try:
            object_handle.Press()
        except AttributeError:
            # AXPress doesn't work with Instruments
            # So did the following work around
            x, y, width, height=self._getobjectsize(object_handle)
            # Mouse left click on the object
            # Note: x + width/2, y + height / 2 doesn't work
            self.generatemouseevent(x + 5, y + 5, "b1c")
            self.wait(5)
            handle=self._get_sub_menu_handle(object_handle, item_name)
            x, y, width, height=self._getobjectsize(handle)
            # on OSX 10.7 default "b1c" doesn't work
            # so using "b1d", verified with Fusion test, this works
            self.generatemouseevent(x + 5, y + 5, "b1d")
            return 1
        # Required for menuitem to appear in accessibility list
        self.wait(1)
        menu_list=re.split(";", item_name)
        try:
            menu_handle=self._internal_menu_handler(object_handle, menu_list,
                                                    True)
            # Required for menuitem to appear in accessibility list
            self.wait(1)
            if not menu_handle.AXEnabled:
                raise LdtpServerException(u"Object %s state disabled" % \
                                          menu_list[-1])
            menu_handle.Press()
        except LdtpServerException:
            object_handle.activate()
            object_handle.sendKey(AXKeyCodeConstants.ESCAPE)
            raise
        return 1

    # Since selectitem and comboselect implementation are same,
    # for Linux/Windows API compatibility let us assign selectitem to comboselect
    comboselect=selectitem

    def selectindex(self, window_name, object_name, item_index):
        """
        Select combo box item / layered pane based on index
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param item_index: Item index to select
        @type object_name: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        self._grabfocus(object_handle.AXWindow)
        try:
            object_handle.Press()
        except AttributeError:
            # AXPress doesn't work with Instruments
            # So did the following work around
            x, y, width, height=self._getobjectsize(object_handle)
            # Mouse left click on the object
            # Note: x + width/2, y + height / 2 doesn't work
            self.generatemouseevent(x + 5, y + 5, "b1c")
        # Required for menuitem to appear in accessibility list
        self.wait(2)
        if not object_handle.AXChildren:
            raise LdtpServerException(u"Unable to find menu")
        # Get AXMenu
        children=object_handle.AXChildren[0]
        if not children:
            raise LdtpServerException(u"Unable to find menu")
        children=children.AXChildren
        tmp_children=[]
        for child in children:
            role, label=self._ldtpize_accessible(child)
            # Don't add empty label
            # Menu separator have empty label's
            if label:
                tmp_children.append(child)
        children=tmp_children
        length=len(children)
        try:
            if item_index < 0 or item_index > length:
                raise LdtpServerException(u"Invalid item index %d" % item_index)
            menu_handle=children[item_index]
            if not menu_handle.AXEnabled:
                raise LdtpServerException(u"Object %s state disabled" % menu_list[-1])
            self._grabfocus(menu_handle)
            x, y, width, height=self._getobjectsize(menu_handle)
            # on OSX 10.7 default "b1c" doesn't work
            # so using "b1d", verified with Fusion test, this works
            window=object_handle.AXWindow
            # For some reason,
            # self.generatemouseevent(x + 5, y + 5, "b1d")
            # doesn't work with Fusion settings
            # Advanced window, so work around with this
            # ldtp.selectindex('*Advanced', 'Automatic', 1)
            """
            Traceback (most recent call last):
               File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/utils.py", line 178, in _dispatch
                  return getattr(self, method)(*args)
               File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/combo_box.py", line 146, in selectindex
                  self.generatemouseevent(x + 5, y + 5, "b1d")
               File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/mouse.py", line 97, in generatemouseevent
                  window=self._get_front_most_window()
               File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/utils.py", line 185, in _get_front_most_window
                  front_app=atomac.NativeUIElement.getFrontmostApp()
               File "build/bdist.macosx-10.8-intel/egg/atomac/AXClasses.py", line 114, in getFrontmostApp
                  raise ValueError('No GUI application found.')
            ValueError: No GUI application found.
            """
            window.doubleClickMouse((x + 5, y + 5))
            # If menuitem already pressed, set child to None
            # So, it doesn't click back in combobox in finally block
            child=None
        finally:
            if child:
                child.Cancel()
        return 1

    # Since selectindex and comboselectindex implementation are same,
    # for backward compatibility let us assign selectindex to comboselectindex
    comboselectindex=selectindex

    def getallitem(self, window_name, object_name):
        """
        Get all combo box item

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: list of string on success.
        @rtype: list
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        object_handle.Press()
        # Required for menuitem to appear in accessibility list
        self.wait(1)
        child=None
        try:
            if not object_handle.AXChildren:
                raise LdtpServerException(u"Unable to find menu")
            # Get AXMenu
            children=object_handle.AXChildren[0]
            if not children:
                raise LdtpServerException(u"Unable to find menu")
            children=children.AXChildren
            items=[]
            for child in children:
                label = self._get_title(child)
                # Don't add empty label
                # Menu separator have empty label's
                if label:
                    items.append(label)
        finally:
            if child:
                # Set it back, by clicking combo box
                child.Cancel()
        return items

    def showlist(self, window_name, object_name):
        """
        Show combo box list / menu
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        object_handle.Press()
        return 1

    def hidelist(self, window_name, object_name):
        """
        Hide combo box list / menu
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        object_handle.activate()
        object_handle.sendKey(AXKeyCodeConstants.ESCAPE)
        return 1

    def verifydropdown(self, window_name, object_name):
        """
        Verify drop down list / menu poped up
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if not object_handle.AXEnabled or not object_handle.AXChildren:
                return 0
            # Get AXMenu
            children=object_handle.AXChildren[0]
            if children:
                return 1
        except LdtpServerException:
            pass
        return 0

    def verifyshowlist(self, window_name, object_name):
        """
        Verify drop down list / menu poped up
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        return self.verifydropdown(window_name, object_name)

    def verifyhidelist(self, window_name, object_name):
        """
        Verify list / menu is hidden in combo box
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if not object_handle.AXEnabled:
                return 0
            if not object_handle.AXChildren:
                return 1
            # Get AXMenu
            children=object_handle.AXChildren[0]
            if not children:
                return 1
            return 1
        except LdtpServerException:
            pass
        return 0

    def verifyselect(self, window_name, object_name, item_name):
        """
        Verify the item selected in combo box
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param item_name: Item name to select
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if not object_handle.AXEnabled:
                return 0
            role, label=self._ldtpize_accessible(object_handle)
            title=self._get_title(object_handle)
            if re.match(item_name, title, re.M | re.U | re.L) or \
                    re.match(item_name, label, re.M | re.U | re.L) or \
                    re.match(item_name, u"%u%u" % (role, label),
                             re.M | re.U | re.L):
                return 1
        except LdtpServerException:
            pass
        return 0

    def getcombovalue(self, window_name, object_name):
        """
        Get current selected combobox value
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: selected item on success, else LdtpExecutionError on failure.
        @rtype: string
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return self._get_title(object_handle)

########NEW FILE########
__FILENAME__ = constants
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Constants class."""

abbreviated_roles = {
    "AXWindow" : "frm",
    "AXTextArea" : "txt",
    "AXTextField" : "txt",
    "AXButton" : "btn",
    "AXStaticText" : "lbl",
    "AXRadioButton" : "rbtn",
    "AXSlider" : "sldr",
    "AXCell" : "tblc",
    "AXImage" : "img",
    "AXToolbar" : "tbar",
    "AXScrollBar" : "scbr",
    "AXMenuItem" : "mnu",
    "AXMenu" : "mnu",
    "AXMenuBar" : "mnu",
    "AXMenuBarItem" : "mnu",
    "AXCheckBox" : "chk",
    "AXTabGroup" : "ptl",
    "AXList" : "lst",
    # Not sure what"s the following object equivalent in LDTP
    "AXMenuButton" : "cbo", # Maybe combo-box ?
    "AXRow" : "tblc",
    "AXColumn" : "col",
    "AXTable" : "tbl",
    "AXScrollArea" : "sar",
    "AXOutline" : "otl",
    "AXValueIndicator" : "val",
    "AXDisclosureTriangle" : "dct",
    "AXGroup" : "grp",
    "AXPopUpButton" : "pubtn",
    "AXApplication" : "app",
    "AXDocItem" : "doc",
    "AXHeading" : "tch",
    "AXGenericElement" : "gen",
    }
ldtp_class_type = {
    "AXWindow" : "frame",
    "AXApplication" : "application",
    "AXTextArea" : "text",
    "AXTextField" : "text",
    "AXButton" : "push_button",
    "AXStaticText" : "label",
    "AXRadioButton" : "radion_button",
    "AXSlider" : "slider",
    "AXCell" : "table_cell",
    "AXImage" : "image",
    "AXToolbar" : "toolbar",
    "AXScrollBar" : "scroll_bar",
    "AXMenuItem" : "menu_item",
    "AXMenu" : "menu",
    "AXMenuBar" : "menu_bar",
    "AXMenuBarItem" : "menu_bar_item",
    "AXCheckBox" : "check_box",
    "AXTabGroup" : "page_tab_list",
    "AXList" : "list",
    "AXColumn" : "column",
    "AXRow" : "table_cell",
    "AXTable" : "table",
    "AXScrollArea" : "scroll_area",
    "AXPopUpButton" : "popup_button",
    "AXDocItem" : "doc_item",
    "AXHeading" : "heading",
    "AXGenericElement" : "generic_element",
    }

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Core class to be exposed via XMLRPC in LDTP daemon."""

import re
import time
import atomac
import fnmatch
import traceback

from menu import Menu
from text import Text
from mouse import Mouse
from table import Table
from value import Value
from generic import Generic
from combo_box import ComboBox
from constants import ldtp_class_type
from page_tab_list import PageTabList
from utils import Utils, ProcessStats
from server_exception import LdtpServerException

try:
    import psutil
except ImportError:
    pass

class Core(ComboBox, Menu, Mouse, PageTabList, Text, Table, Value, Generic):
    def __init__(self):
        super(Core, self).__init__()
        self._process_stats={}

    def __del__(self):
        for key in self._process_stats.keys():
            # Stop all process monitoring instances
            self._process_stats[key].stop()

    """Core LDTP class"""
    def appundertest(self, app_name):
        """
        Application under test
        app_name: Application name should be app identifier
        eg: com.apple.AppleSpell', 'com.apple.talagent', 'com.apple.dock',
        'com.adiumX.adiumX', 'com.apple.notificationcenterui', 'org.3rddev.xchatazure',
        'com.skype.skype', 'com.mcafee.McAfeeReporter', 'com.microsoft.outlook.database_daemon',
        'com.apple.photostream-agent', 'com.google.GoogleTalkPluginD',
        'com.microsoft.SyncServicesAgent', 'com.google.Chrome.helper.EH',
        'com.apple.dashboard.client', 'None', 'com.vmware.fusionStartMenu',
        'com.apple.ImageCaptureExtension2', 'com.apple.loginwindow', 'com.mozypro.status',
        'com.apple.Preview', 'com.google.Chrome.helper', 'com.apple.calculator',
        'com.apple.Terminal', 'com.apple.iTunesHelper', 'com.apple.ActivityMonitor',
        'net.juniper.NetworkConnect', 'com.google.Chrome', 'com.apple.dock.extra',
        'com.apple.finder', 'com.yourcompany.Menulet', 'com.apple.systemuiserver'

        @return: return 1 on success
        @rtype: int
        """
        self._app_under_test=app_name
        return 1

    def getapplist(self):
        """
        Get all accessibility application name that are currently running

        @return: list of appliction name of string type on success.
        @rtype: list
        """
        app_list=[]
        # Update apps list, before parsing the list
        self._update_apps()
        for gui in self._running_apps:
            name=gui.localizedName()
            # default type was objc.pyobjc_unicode
            # convert to Unicode, else exception is thrown
            # TypeError: "cannot marshal <type 'objc.pyobjc_unicode'> objects"
            try:
                name=unicode(name)
            except UnicodeEncodeError:
                pass
            app_list.append(name)
        # Return unique application list
        return list(set(app_list))

    def getwindowlist(self):
        """
        Get all accessibility window that are currently open
        
        @return: list of window names in LDTP format of string type on success.
        @rtype: list
        """
        return self._get_windows(True).keys()
    
    def isalive(self):
        """
        Client will use this to verify whether the server instance is alive or not.

        @return: True on success.
        @rtype: boolean
        """
        return True

    def poll_events(self):
        """
        Poll for any registered events or window create events

        @return: window name
        @rtype: string
        """

        if not self._callback_event:
            return ''
        return self._callback_event.pop()

    def getlastlog(self):
        """
        Returns one line of log at any time, if any available, else empty string

        @return: log as string
        @rtype: string
        """

        if not self._custom_logger.log_events:
            return ''
        
        return self._custom_logger.log_events.pop()

    def startprocessmonitor(self, process_name, interval=2):
        """
        Start memory and CPU monitoring, with the time interval between
        each process scan

        @param process_name: Process name, ex: firefox-bin.
        @type process_name: string
        @param interval: Time interval between each process scan
        @type interval: double

        @return: 1 on success
        @rtype: integer
        """
        if self._process_stats.has_key(process_name):
            # Stop previously running instance
            # At any point, only one process name can be tracked
            # If an instance already exist, then stop it
            self._process_stats[process_name].stop()
        # Create an instance of process stat
        self._process_stats[process_name]=ProcessStats(process_name, interval)
        # start monitoring the process
        self._process_stats[process_name].start()
        return 1

    def stopprocessmonitor(self, process_name):
        """
        Stop memory and CPU monitoring

        @param process_name: Process name, ex: firefox-bin.
        @type process_name: string

        @return: 1 on success
        @rtype: integer
        """
        if self._process_stats.has_key(process_name):
            # Stop monitoring process
            self._process_stats[process_name].stop()
        return 1

    def getcpustat(self, process_name):
        """
        get CPU stat for the give process name

        @param process_name: Process name, ex: firefox-bin.
        @type process_name: string

        @return: cpu stat list on success, else empty list
                If same process name, running multiple instance,
                get the stat of all the process CPU usage
        @rtype: list
        """
        # Create an instance of process stat
        _stat_inst=ProcessStats(process_name)
        _stat_list=[]
        for p in _stat_inst.get_cpu_memory_stat():
            try:
                _stat_list.append(p.get_cpu_percent())
            except psutil.AccessDenied:
                pass
        return _stat_list

    def getmemorystat(self, process_name):
        """
        get memory stat

        @param process_name: Process name, ex: firefox-bin.
        @type process_name: string

        @return: memory stat list on success, else empty list
                If same process name, running multiple instance,
                get the stat of all the process memory usage
        @rtype: list
        """
        # Create an instance of process stat
        _stat_inst=ProcessStats(process_name)
        _stat_list=[]
        for p in _stat_inst.get_cpu_memory_stat():
            # Memory percent returned with 17 decimal values
            # ex: 0.16908645629882812, round it to 2 decimal values
            # as 0.03
            try:
                _stat_list.append(round(p.get_memory_percent(), 2))
            except psutil.AccessDenied:
                pass
        return _stat_list

    def getobjectlist(self, window_name):
        """
        Get list of items in given GUI.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string

        @return: list of items in LDTP naming convention.
        @rtype: list
        """
        try:
            window_handle, name, app=self._get_window_handle(window_name, True)
            object_list=self._get_appmap(window_handle, name, True)
        except atomac._a11y.ErrorInvalidUIElement:
            # During the test, when the window closed and reopened
            # ErrorInvalidUIElement exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            window_handle, name, app=self._get_window_handle(window_name, True)
            object_list=self._get_appmap(window_handle, name, True)
        return object_list.keys()

    def getobjectinfo(self, window_name, object_name):
        """
        Get object properties.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: list of properties
        @rtype: list
        """
        try:
            obj_info=self._get_object_map(window_name, object_name,
                                          wait_for_object=False)
        except atomac._a11y.ErrorInvalidUIElement:
            # During the test, when the window closed and reopened
            # ErrorInvalidUIElement exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            obj_info=self._get_object_map(window_name, object_name,
                                          wait_for_object=False)
        props = []
        if obj_info:
            for obj_prop in obj_info.keys():
                if not obj_info[obj_prop] or obj_prop == "obj":
                    # Don't add object handle to the list
                    continue
                props.append(obj_prop)
        return props

    def getobjectproperty(self, window_name, object_name, prop):
        """
        Get object property value.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param prop: property name.
        @type prop: string

        @return: property
        @rtype: string
        """
        try:
            obj_info=self._get_object_map(window_name, object_name,
                                          wait_for_object=False)
        except atomac._a11y.ErrorInvalidUIElement:
            # During the test, when the window closed and reopened
            # ErrorInvalidUIElement exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            obj_info=self._get_object_map(window_name, object_name,
                                          wait_for_object=False)
        if obj_info and prop != "obj" and prop in obj_info:
            if prop == "class":
                # ldtp_class_type are compatible with Linux and Windows class name
                # If defined class name exist return that,
                # else return as it is
                return ldtp_class_type.get(obj_info[prop], obj_info[prop])
            else:
                return obj_info[prop]
        raise LdtpServerException('Unknown property "%s" in %s' % \
                                      (prop, object_name))

    def getchild(self, window_name, child_name = '', role = '', parent = ''):
        """
        Gets the list of object available in the window, which matches
        component name or role name or both.
       
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param child_name: Child name to search for.
        @type child_name: string
        @param role: role name to search for, or an empty string for wildcard.
        @type role: string
        @param parent: parent name to search for, or an empty string for wildcard.
        @type role: string
        @return: list of matched children names
        @rtype: list
        """
        matches = []
        if role:
            role = re.sub(' ', '_', role)
        self._windows={}
        if parent and (child_name or role):
            _window_handle, _window_name = \
                self._get_window_handle(window_name)[0:2]
            if not _window_handle:
                raise LdtpServerException('Unable to find window "%s"' % \
                                              window_name)
            appmap = self._get_appmap(_window_handle, _window_name)
            obj = self._get_object_map(window_name, parent)
            def _get_all_children_under_obj(obj, child_list):
                if role and obj['class'] == role:
                    child_list.append(obj['label'])
                elif child_name and self._match_name_to_appmap(child_name, obj):
                    child_list.append(obj['label'])
                if obj:
                    children = obj['children']
                if not children:
                    return child_list
                for child in children.split():
                    return _get_all_children_under_obj( \
                        appmap[child],
                        child_list)
           
            matches = _get_all_children_under_obj(obj, [])
            if not matches:
                if child_name:
                    _name = 'name "%s" ' % child_name
                if role:
                    _role = 'role "%s" ' % role
                if parent:
                    _parent = 'parent "%s"' % parent
                exception = 'Could not find a child %s%s%s' % (_name, _role, _parent)
                raise LdtpServerException(exception)
 
            return matches
 
        _window_handle, _window_name = \
            self._get_window_handle(window_name)[0:2]
        if not _window_handle:
            raise LdtpServerException('Unable to find window "%s"' % \
                                          window_name)
        appmap = self._get_appmap(_window_handle, _window_name)
        for name in appmap.keys():
            obj = appmap[name]
            # When only role arg is passed
            if role and not child_name and obj['class'] == role:
                matches.append(name)
            # When parent and child_name arg is passed
            if parent and child_name and not role and \
                    self._match_name_to_appmap(parent, obj):
                matches.append(name)
            # When only child_name arg is passed
            if child_name and not role and \
                    self._match_name_to_appmap(child_name, obj):
                return name
                matches.append(name)
            # When role and child_name args are passed
            if role and child_name and obj['class'] == role and \
                    self._match_name_to_appmap(child_name, obj):
                matches.append(name)
 
        if not matches:
            _name = ''
            _role = ''
            _parent = ''
            if child_name:
                _name = 'name "%s" ' % child_name
            if role:
                _role = 'role "%s" ' % role
            if parent:
                _parent = 'parent "%s"' % parent
            exception = 'Could not find a child %s%s%s' % (_name, _role, _parent)
            raise LdtpServerException(exception)
 
        return matches

    def launchapp(self, cmd, args = [], delay = 0, env = 1, lang = "C"):
        """
        Launch application.

        @param cmd: Command line string to execute.
        @type cmd: string
        @param args: Arguments to the application
        @type args: list
        @param delay: Delay after the application is launched
        @type delay: int
        @param env: GNOME accessibility environment to be set or not
        @type env: int
        @param lang: Application language to be used
        @type lang: string

        @return: 1 on success
        @rtype: integer

        @raise LdtpServerException: When command fails
        """
        try:
            atomac.NativeUIElement.launchAppByBundleId(cmd)
            return 1
        except RuntimeError:
            if atomac.NativeUIElement.launchAppByBundlePath(cmd):
                # Let us wait so that the application launches
                try:
                    time.sleep(int(delay))
                except ValueError:
                    time.sleep(5)
                return 1
            else:
                raise LdtpServerException(u"Unable to find app '%s'" % cmd)

    def wait(self, timeout=5):
        """
        Wait a given amount of seconds.

        @param timeout: Wait timeout in seconds
        @type timeout: double

        @return: 1
        @rtype: integer
        """
        time.sleep(timeout)
        return 1

    def closewindow(self, window_name):
        """
        Close window.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string

        @return: 1 on success.
        @rtype: integer
        """
        return self._singleclick(window_name, "btnclosebutton")

    def minimizewindow(self, window_name):
        """
        Minimize window.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string

        @return: 1 on success.
        @rtype: integer
        """
        return self._singleclick(window_name, "btnminimizebutton")

    def maximizewindow(self, window_name):
        """
        Maximize window.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string

        @return: 1 on success.
        @rtype: integer
        """
        return self._singleclick(window_name, "btnzoombutton")

    def activatewindow(self, window_name):
        """
        Activate window.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string

        @return: 1 on success.
        @rtype: integer
        """
        window_handle=self._get_window_handle(window_name)
        self._grabfocus(window_handle)
        return 1

    def click(self, window_name, object_name):
        """
        Click item.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=self._getobjectsize(object_handle)
        self._grabfocus(object_handle)
        self.wait(0.5)
        # If object doesn't support Press, trying clicking with the object
        # coordinates, where size=(x, y, width, height)
        # click on center of the widget
        # Noticed this issue on clicking AXImage
        # click('Instruments*', 'Automation')
        self.generatemouseevent(size[0] + size[2]/2, size[1] + size[3]/2, "b1c")
        return 1

    def getallstates(self, window_name, object_name):
        """
        Get all states of given object
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: list of string on success.
        @rtype: list
        """
        object_handle=self._get_object_handle(window_name, object_name)
        _obj_states = []
        if object_handle.AXEnabled:
            _obj_states.append("enabled")
        if object_handle.AXFocused:
            _obj_states.append("focused")
        else:
            try:
                if object_handle.AXFocused:
                    _obj_states.append("focusable")
            except:
                pass
        if re.match("AXCheckBox", object_handle.AXRole, re.M | re.U | re.L) or \
                re.match("AXRadioButton", object_handle.AXRole,
                         re.M | re.U | re.L):
            if object_handle.AXValue:
                _obj_states.append("checked")
        return _obj_states

    def hasstate(self, window_name, object_name, state, guiTimeOut = 0):
        """
        has state
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @type window_name: string
        @param state: State of the current object.
        @type object_name: string
        @param guiTimeOut: Wait timeout in seconds
        @type guiTimeOut: integer

        @return: 1 on success.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if state == "enabled":
                return int(object_handle.AXEnabled)
            elif state == "focused":
                return int(object_handle.AXFocused)
            elif state == "focusable":
                return int(object_handle.AXFocused)
            elif state == "checked":
                if re.match("AXCheckBox", object_handle.AXRole,
                            re.M | re.U | re.L) or \
                            re.match("AXRadioButton", object_handle.AXRole,
                                     re.M | re.U | re.L):
                    if object_handle.AXValue:
                        return 1
        except:
            pass
        return 0

    def getobjectsize(self, window_name, object_name=None):
        """
        Get object size
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: x, y, width, height on success.
        @rtype: list
        """
        if not object_name: 
            handle, name, app=self._get_window_handle(window_name)
        else:
            handle=self._get_object_handle(window_name, object_name)
        return self._getobjectsize(handle)

    def getwindowsize(self, window_name):
        """
        Get window size.
        
        @param window_name: Window name to get size of.
        @type window_name: string

        @return: list of dimensions [x, y, w, h]
        @rtype: list
        """
        return self.getobjectsize(window_name)

    def grabfocus(self, window_name, object_name=None):
        """
        Grab focus.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        if not object_name:
            handle, name, app=self._get_window_handle(window_name)
        else:
            handle=self._get_object_handle(window_name, object_name)
        return self._grabfocus(handle)

    def guiexist(self, window_name, object_name=None):
        """
        Checks whether a window or component exists.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            self._windows={}
            if not object_name:
                handle, name, app=self._get_window_handle(window_name, False)
            else:
                handle=self._get_object_handle(window_name, object_name,
                                               wait_for_object=False)
            # If window and/or object exist, exception will not be thrown
            # blindly return 1
            return 1
        except LdtpServerException:
            pass
        return 0

    def guitimeout(self, timeout):
      """
      Change GUI timeout period, default 30 seconds.

      @param timeout: timeout in seconds
      @type timeout: integer

      @return: 1 on success.
      @rtype: integer
      """
      self._window_timeout=timeout
      return 1

    def objtimeout(self, timeout):
      """
      Change object timeout period, default 5 seconds.

      @param timeout: timeout in seconds
      @type timeout: integer

      @return: 1 on success.
      @rtype: integer
      """
      self._obj_timeout=timeout
      return 1

    def waittillguiexist(self, window_name, object_name = '',
                         guiTimeOut = 30, state = ''):
        """
        Wait till a window or component exists.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type object_name: string
        @param guiTimeOut: Wait timeout in seconds
        @type guiTimeOut: integer
        @param state: Object state used only when object_name is provided.
        @type object_name: string

        @return: 1 if GUI was found, 0 if not.
        @rtype: integer
        """
        timeout = 0
        while timeout < guiTimeOut:
            if self.guiexist(window_name, object_name):
                return 1
            # Wait 1 second before retrying
            time.sleep(1)
            timeout += 1
        # Object and/or window doesn't appear within the timeout period
        return 0

    def waittillguinotexist(self, window_name, object_name = '', guiTimeOut = 30):
        """
        Wait till a window does not exist.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type object_name: string
        @param guiTimeOut: Wait timeout in seconds
        @type guiTimeOut: integer

        @return: 1 if GUI has gone away, 0 if not.
        @rtype: integer
        """
        timeout = 0
        while timeout < guiTimeOut:
            if not self.guiexist(window_name, object_name):
                return 1
            # Wait 1 second before retrying
            time.sleep(1)
            timeout += 1
        # Object and/or window still appears within the timeout period
        return 0

    def objectexist(self, window_name, object_name):
        """
        Checks whether a window or component exists.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type object_name: string

        @return: 1 if GUI was found, 0 if not.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            return 1
        except LdtpServerException:
            return 0

    def stateenabled(self, window_name, object_name):
        """
        Check whether an object state is enabled or not
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if object_handle.AXEnabled:
                return 1
        except LdtpServerException:
            pass
        return 0

    def check(self, window_name, object_name):
        """
        Check item.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        # FIXME: Check for object type
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        if object_handle.AXValue == 1:
            # Already checked
            return 1
        # AXPress doesn't work with Instruments
        # So did the following work around
        self._grabfocus(object_handle)
        x, y, width, height=self._getobjectsize(object_handle)
        # Mouse left click on the object
        # Note: x + width/2, y + height / 2 doesn't work
        self.generatemouseevent(x + width / 2, y + height / 2, "b1c")
        return 1

    def uncheck(self, window_name, object_name):
        """
        Uncheck item.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        if object_handle.AXValue == 0:
            # Already unchecked
            return 1
        # AXPress doesn't work with Instruments
        # So did the following work around
        self._grabfocus(object_handle)
        x, y, width, height=self._getobjectsize(object_handle)
        # Mouse left click on the object
        # Note: x + width/2, y + height / 2 doesn't work
        self.generatemouseevent(x + width / 2, y + height / 2, "b1c")
        return 1

    def verifycheck(self, window_name, object_name):
        """
        Verify check item.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name,
                                                  wait_for_object=False)
            if object_handle.AXValue == 1:
                return 1
        except LdtpServerException:
            pass
        return 0

    def verifyuncheck(self, window_name, object_name):
        """
        Verify uncheck item.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name,
                                                  wait_for_object=False)
            if object_handle.AXValue == 0:
                return 1
        except LdtpServerException:
            pass
        return 0

    def getaccesskey(self, window_name, object_name):
        """
        Get access key of given object

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: access key in string format on success, else LdtpExecutionError on failure.
        @rtype: string
        """
        # Used http://www.danrodney.com/mac/ as reference for
        # mapping keys with specific control
        # In Mac noticed (in accessibility inspector) only menu had access keys
        # so, get the menu_handle of given object and
        # return the access key
        menu_handle=self._get_menu_handle(window_name, object_name)
        key=menu_handle.AXMenuItemCmdChar
        modifiers=menu_handle.AXMenuItemCmdModifiers
        glpyh=menu_handle.AXMenuItemCmdGlyph
        virtual_key=menu_handle.AXMenuItemCmdVirtualKey
        modifiers_type=""
        if modifiers == 0:
            modifiers_type="<command>"
        elif modifiers == 1:
            modifiers_type="<shift><command>"
        elif modifiers == 2:
            modifiers_type="<option><command>"
        elif modifiers == 3:
            modifiers_type="<option><shift><command>"
        elif modifiers == 4:
            modifiers_type="<ctrl><command>"
        elif modifiers == 6:
            modifiers_type="<ctrl><option><command>"
        # Scroll up
        if virtual_key==115 and glpyh==102:
            modifiers="<option>"
            key="<cursor_left>"
        # Scroll down
        elif virtual_key==119 and glpyh==105:
            modifiers="<option>"
            key="<right>"
        # Page up
        elif virtual_key==116 and glpyh==98:
            modifiers="<option>"
            key="<up>"
        # Page down
        elif virtual_key==121 and glpyh==107:
            modifiers="<option>"
            key="<down>"
        # Line up
        elif virtual_key==126 and glpyh==104:
            key="<up>"
        # Line down
        elif virtual_key==125 and glpyh==106:
            key="<down>"
        # Noticed in  Google Chrome navigating next tab
        elif virtual_key==124 and glpyh==101:
            key="<right>"
        # Noticed in  Google Chrome navigating previous tab
        elif virtual_key==123 and glpyh==100:
            key="<left>"
        # List application in a window to Force Quit
        elif virtual_key==53 and glpyh==27:
            key="<escape>"
        # FIXME:
        # * Instruments Menu View->Run Browser
        # modifiers==12 virtual_key==48 glpyh==2
        # * Terminal Menu Edit->Start Dictation
        # fn fn - glpyh==148 modifiers==24
        # * Menu Chrome->Clear Browsing Data in Google Chrome 
        # virtual_key==51 glpyh==23 [Delete Left (like Backspace on a PC)]
        if not key:
            raise LdtpServerException("No access key associated")
        return modifiers_type + key

########NEW FILE########
__FILENAME__ = generic
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Yingjun Li <yingjunli@gmail.com>                                                                                                      
#@copyright: Copyright (c) 2009-12 Yingjun Li                                                                                                  

#http://ldtp.freedesktop.org                                                                                                                           

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Generic class."""

import os
import tempfile
from base64 import b64encode
from AppKit import *
from Quartz.CoreGraphics import *

from utils import Utils
from server_exception import LdtpServerException

class Generic(Utils):
    def imagecapture(self, window_name = None, x = 0, y = 0,
                     width = None, height = None):
        """
        Captures screenshot of the whole desktop or given window
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param x: x co-ordinate value
        @type x: int
        @param y: y co-ordinate value
        @type y: int
        @param width: width co-ordinate value
        @type width: int
        @param height: height co-ordinate value
        @type height: int

        @return: screenshot with base64 encoded for the client
        @rtype: string
        """
        if x or y or (width and width != -1) or (height and height != -1):
            raise LdtpServerException("Not implemented")
        if window_name:
            handle, name, app=self._get_window_handle(window_name)
            try:
                self._grabfocus(handle)
            except:
                pass
            rect = self._getobjectsize(handle)
            screenshot = CGWindowListCreateImage(NSMakeRect(rect[0],
                rect[1], rect[2], rect[3]), 1, 0, 0)
        else:
            screenshot = CGWindowListCreateImage(CGRectInfinite, 1, 0, 0)
        image = CIImage.imageWithCGImage_(screenshot)
        bitmapRep = NSBitmapImageRep.alloc().initWithCIImage_(image)
        blob = bitmapRep.representationUsingType_properties_(NSPNGFileType, None)
        tmpFile = tempfile.mktemp('.png', 'ldtpd_')
        blob.writeToFile_atomically_(tmpFile, False)
        rv = b64encode(open(tmpFile).read())
        os.remove(tmpFile)
        return rv


########NEW FILE########
__FILENAME__ = keypress_actions
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""KeyboardOp class."""

import time
from atomac.AXKeyCodeConstants import *
from server_exception import LdtpServerException

class KeyCombo:
  def __init__(self):
    self.modifiers=False
    self.value=''
    self.modVal=None

class KeyboardOp:
  def __init__(self):
    self._undefined_key=None
    self._max_tokens=256
    self._max_tok_size=15

  def _get_key_value(self, keyval):
    return_val=KeyCombo()
    if keyval == "command":
      keyval="command_l"
    elif keyval == "option":
      keyval="option_l"
    elif keyval == "control":
      keyval="control_l"
    elif keyval == "shift":
      keyval="shift_l"
    elif keyval == "left":
      keyval="cursor_left"
    elif keyval == "right":
      keyval="cursor_right"
    elif keyval == "up":
      keyval="cursor_up"
    elif keyval == "down":
      keyval="cursor_down"
    elif keyval == "bksp":
      keyval="backspace"
    elif keyval == "enter":
      keyval="return"
    elif keyval == "pgdown":
      keyval="page_down"
    elif keyval == "pagedown":
      keyval="page_down"
    elif keyval == "pgup":
      keyval="page_up"
    elif keyval == "pageup":
      keyval="page_up"
    key="<%s>" % keyval
    # This will identify Modifiers
    if key in ["<command_l>", "<command_r>",
               "<shift_l>", "<shift_r>",
               "<control_l>", "<control_r>",
               "<option_l>", "<option_r>"]:
        return_val.modifiers=True
        return_val.modVal=[key]
        return return_val
    # This will identify all US_keyboard characters
    if keyval.lower() in US_keyboard:
        return_val.value=keyval
        return return_val
    # This will identify all specialKeys
    if key in specialKeys:
        return_val.value=key
        return return_val
    # Key Undefined
    return return_val

  def get_keyval_id(self, input_str):
    index=0
    key_vals=[]
    lastModifiers=None
    while index  < len(input_str):
      token=''
      # Identified a Non Printing Key
      if input_str[index] == '<':
        index += 1
        i=0
        while input_str[index] != '>' and i < self._max_tok_size:
          token += input_str[index]
          index += 1
          i += 1
        if input_str[index] != '>':
          # Premature end of string without an opening '<'
          return None
        index += 1
      else:
        token=input_str[index]
        index += 1

      key_val=self._get_key_value(token)
      # Deal with modifier and undefined keys.
      # Modifiers: if we got modifier in previous
      # step, extend the previous KeyCombo object instead
      # of creating a new one.
      if lastModifiers and key_val.value != self._undefined_key:
        last_item = key_vals.pop()
        if key_val.modifiers:
          lastModifiers = key_val
          last_item.modVal.extend(key_val.modVal)
          key_val = last_item
        else:
          last_item.value = key_val.value
          key_val = last_item
          lastModifiers=None
      elif key_val.modifiers:
        if not lastModifiers:
          lastModifiers=key_val
        else:
          last_item=key_vals.pop()
          last_item.modVal.extend(key_val.modVal)
          key_val=last_item
      elif key_val.value == self._undefined_key:
        # Invalid key
        return None
      key_vals.append(key_val)
    return key_vals

class KeyComboAction:
    def __init__(self, window, data):
        self._data=data
        self._window=window
        _keyOp=KeyboardOp()
        self._keyvalId=_keyOp.get_keyval_id(data)
        if not self._keyvalId:
          raise LdtpServerException("Unsupported keys passed")
        self._doCombo()

    def _doCombo(self):
        for key_val in self._keyvalId:
            if key_val.modifiers:
              self._window.sendKeyWithModifiers(key_val.value, key_val.modVal)
            else:
              self._window.sendKey(key_val.value)
            time.sleep(0.01)

class KeyPressAction:
    def __init__(self, window, data):
        self._data=data
        self._window=window
        _keyOp=KeyboardOp()
        self._keyvalId=_keyOp.get_keyval_id(data)
        if not self._keyvalId:
          raise LdtpServerException("Unsupported keys passed")
        self._doPress()

    def _doPress(self):
       for key_val in self._keyvalId:
          if key_val.modifiers:
             self._window.pressModifiers(key_val.modVal)
          else:
             raise LdtpServerException("Unsupported modifiers")
          time.sleep(0.01)

class KeyReleaseAction:
    def __init__(self, window, data):
        self._data=data
        self._window=window
        _keyOp=KeyboardOp()
        self._keyvalId=_keyOp.get_keyval_id(data)
        if not self._keyvalId:
            raise LdtpServerException("Unsupported keys passed")
        self._doRelease()

    def _doRelease(self):
       for key_val in self._keyvalId:
          if key_val.modifiers:
             self._window.releaseModifiers(key_val.modVal)
          else:
             raise LdtpServerException("Unsupported modifiers")
          time.sleep(0.01)

########NEW FILE########
__FILENAME__ = menu
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Menu class."""

import re
import atomac

from utils import Utils
from server_exception import LdtpServerException

class Menu(Utils):
    def _get_menu_handle(self, window_name, object_name,
                               wait_for_window=True):
        menu_list=re.split(";", object_name)
        # Call base class get_menu_handle
        try:
            menu_handle=Utils._get_menu_handle(self, window_name,
                                               menu_list[0], wait_for_window)
        except (atomac._a11y.ErrorCannotComplete, atomac._a11y.ErrorInvalidUIElement):
            # During the test, when the window closed and reopened
            # ErrorCannotComplete exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            menu_handle=Utils._get_menu_handle(self, window_name,
                                               menu_list[0], wait_for_window)
        if len(menu_list) <= 1:
            # If only first level menu is given, return the handle
            return menu_handle
        return self._internal_menu_handler(menu_handle, menu_list[1:])

    def selectmenuitem(self, window_name, object_name):
        """
        Select (click) a menu item.

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        menu_handle=self._get_menu_handle(window_name, object_name)
        if not menu_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        menu_handle.Press()
        return 1

    def doesmenuitemexist(self, window_name, object_name):
        """
        Check a menu item exist.

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string
        @param strict_hierarchy: Mandate menu hierarchy if set to True
        @type object_name: boolean

        @return: 1 on success.
        @rtype: integer
        """
        try:
            menu_handle=self._get_menu_handle(window_name, object_name,
                                              False)
            return 1
        except LdtpServerException:
            return 0

    def menuitemenabled(self, window_name, object_name):
        """
        Verify a menu item is enabled

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            menu_handle=self._get_menu_handle(window_name, object_name,
                                              False)
            if menu_handle.AXEnabled:
                return 1
        except LdtpServerException:
            pass
        return 0

    def listsubmenus(self, window_name, object_name):
        """
        List children of menu item
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: menu item in list on success.
        @rtype: list
        """
        menu_handle=self._get_menu_handle(window_name, object_name)
        role, label=self._ldtpize_accessible(menu_handle)
        menu_clicked=False
        try:
            if not menu_handle.AXChildren:
                menu_clicked=True
                try:
                    menu_handle.Press()
                    self.wait(1)
                except atomac._a11y.ErrorCannotComplete:
                    pass
                if not menu_handle.AXChildren:
                    raise LdtpServerException(u"Unable to find children under menu %s" % \
                                                  label)
            children=menu_handle.AXChildren[0]
            sub_menus=[]
            for current_menu in children.AXChildren:
                role, label=self._ldtpize_accessible(current_menu)
                if not label:
                    # All splitters have empty label
                    continue
                sub_menus.append(u"%s%s" % (role, label))
        finally:
            if menu_clicked:
                menu_handle.Cancel()
        return sub_menus

    def verifymenucheck(self, window_name, object_name):
        """
        Verify a menu item is checked

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            menu_handle=self._get_menu_handle(window_name, object_name,
                                                      False)
            try:
                if menu_handle.AXMenuItemMarkChar:
                    # Checked
                    return 1
            except atomac._a11y.Error:
                pass
        except LdtpServerException:
            pass
        return 0

    def verifymenuuncheck(self, window_name, object_name):
        """
        Verify a menu item is un-checked

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            menu_handle=self._get_menu_handle(window_name, object_name,
                                              False)
            try:
                if not menu_handle.AXMenuItemMarkChar:
                    # Unchecked
                    return 1
            except atomac._a11y.Error:
                return 1
        except LdtpServerException:
            pass
        return 0

    def menucheck(self, window_name, object_name):
        """
        Check (click) a menu item.

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        menu_handle=self._get_menu_handle(window_name, object_name)
        if not menu_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        try:
            if menu_handle.AXMenuItemMarkChar:
                # Already checked
                return 1
        except atomac._a11y.Error:
            pass
        menu_handle.Press()
        return 1

    def menuuncheck(self, window_name, object_name):
        """
        Uncheck (click) a menu item.

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        menu_handle=self._get_menu_handle(window_name, object_name)
        if not menu_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        try:
            if not menu_handle.AXMenuItemMarkChar:
                # Already unchecked
                return 1
        except atomac._a11y.Error:
            return 1
        menu_handle.Press()
        return 1

########NEW FILE########
__FILENAME__ = mouse
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Mouse class."""

from utils import Utils
from server_exception import LdtpServerException

class Mouse(Utils):
    def mouseleftclick(self, window_name, object_name):
        """
        Mouse left click on an object.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle = self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        self._grabfocus(object_handle)
        x, y, width, height = self._getobjectsize(object_handle)
        # Mouse left click on the object
        object_handle.clickMouseButtonLeft((x + width / 2, y + height / 2))
        return 1

    def mouserightclick(self, window_name, object_name):
        """
        Mouse right click on an object.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle = self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        self._grabfocus(object_handle)
        x, y, width, height = self._getobjectsize(object_handle)
        # Mouse right click on the object
        object_handle.clickMouseButtonRight((x + width / 2, y + height / 2))
        return 1

    def generatemouseevent(self, x, y, eventType = "b1c"):
        """
        Generate mouse event on x, y co-ordinates.
        
        @param x: X co-ordinate
        @type x: int
        @param y: Y co-ordinate
        @type y: int
        @param eventType: Mouse click type
        @type eventType: string

        @return: 1 on success.
        @rtype: integer
        """
        if eventType == "b1c":
            try:
                window=self._get_front_most_window()
            except (IndexError, ):
                window=self._get_any_window()
            window.clickMouseButtonLeft((x, y))
            return 1
        elif eventType == "b3c":
            try:
                window=self._get_front_most_window()
            except (IndexError, ):
                window=self._get_any_window()
            window.clickMouseButtonRight((x, y))
            return 1
        elif eventType == "b1d":
            try:
                window=self._get_front_most_window()
            except (IndexError, ):
                window=self._get_any_window()
            window.doubleClickMouse((x, y))
            return 1
        raise LdtpServerException("Not implemented")

    def mousemove(self, window_name, object_name):
        """
        Mouse move on an object.
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        raise LdtpServerException("Not implemented")

    def doubleclick(self, window_name, object_name):
        """
        Double click on the object
        
        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle = self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        self._grabfocus(object_handle)
        x, y, width, height = self._getobjectsize(object_handle)
        window=self._get_front_most_window()
        # Mouse double click on the object
        #object_handle.doubleClick()
        window.doubleClickMouse((x + width / 2, y + height / 2))
        return 1

    def simulatemousemove(self, source_x, source_y, dest_x, dest_y, delay = 0.0):
        """
        @param source_x: Source X
        @type source_x: integer
        @param source_y: Source Y
        @type source_y: integer
        @param dest_x: Dest X
        @type dest_x: integer
        @param dest_y: Dest Y
        @type dest_y: integer
        @param delay: Sleep time between the mouse move
        @type delay: double

        @return: 1 if simulation was successful, 0 if not.
        @rtype: integer
        """
        raise LdtpServerException("Not implemented")

########NEW FILE########
__FILENAME__ = page_tab_list
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""PageTabList class."""

import re
import fnmatch

from utils import Utils
from server_exception import LdtpServerException

class PageTabList(Utils):
    def _get_tab_children(self, window_name, object_name):
        object_handle = self._get_object_handle(window_name, object_name)
        if not object_handle:
            raise LdtpServerException(u"Unable to find object %s" % object_name)
        return object_handle.AXChildren

    def _get_tab_handle(self, window_name, object_name, tab_name):
        children = self._get_tab_children(window_name, object_name)
        tab_handle = None
        for current_tab in children:
            role, label = self._ldtpize_accessible(current_tab)
            tmp_tab_name = fnmatch.translate(tab_name)
            if re.match(tmp_tab_name, label) or \
                    re.match(tmp_tab_name, u"%s%s" % (role, label)):
                tab_handle = current_tab
                break
        if not tab_handle:
            raise LdtpServerException(u"Unable to find tab %s" % tab_name)
        if not tab_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return tab_handle

    def selecttab(self, window_name, object_name, tab_name):
        """
        Select tab based on name.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param tab_name: tab to select
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        tab_handle = self._get_tab_handle(window_name, object_name, tab_name)
        tab_handle.Press()
        return 1

    def selecttabindex(self, window_name, object_name, tab_index):
        """
        Select tab based on index.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param tab_index: tab to select
        @type data: integer

        @return: 1 on success.
        @rtype: integer
        """
        children = self._get_tab_children(window_name, object_name)
        length = len(children)
        if tab_index < 0 or tab_index > length:
            raise LdtpServerException(u"Invalid tab index %s" % tab_index)
        tab_handle = children[tab_index]
        if not tab_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        tab_handle.Press()
        return 1

    def verifytabname(self, window_name, object_name, tab_name):
        """
        Verify tab name.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param tab_name: tab to select
        @type data: string

        @return: 1 on success 0 on failure
        @rtype: integer
        """
        try:
            tab_handle = self._get_tab_handle(window_name, object_name, tab_name)
            if tab_handle.AXValue:
                return 1
        except LdtpServerException:
            pass
        return 0

    def gettabcount(self, window_name, object_name):
        """
        Get tab count.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: tab count on success.
        @rtype: integer
        """
        children = self._get_tab_children(window_name, object_name)
        return len(children)

    def gettabname(self, window_name, object_name, tab_index):
        """
        Get tab name
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param tab_index: Index of tab (zero based index)
        @type object_name: int

        @return: text on success.
        @rtype: string
        """
        children = self._get_tab_children(window_name, object_name)
        length = len(children)
        if tab_index < 0 or tab_index > length:
            raise LdtpServerException(u"Invalid tab index %s" % tab_index)
        tab_handle = children[tab_index]
        if not tab_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return tab_handle.AXTitle

########NEW FILE########
__FILENAME__ = server_exception
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Exception class."""

import xmlrpclib

ERROR_CODE = 123

class LdtpServerException(xmlrpclib.Fault):
    def __init__(self, message):
        xmlrpclib.Fault.__init__(self, ERROR_CODE, message)

########NEW FILE########
__FILENAME__ = table
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Mouse class."""

import re
import fnmatch
from text import Text
from utils import Utils
from server_exception import LdtpServerException

class Table(Utils):
    def getrowcount(self, window_name, object_name):
        """
        Get count of rows in table object.

        @param window_name: Window name to look for, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to look for, either full name,
        LDTP's name convention, or a Unix glob. Or menu heirarchy
        @type object_name: string

        @return: Number of rows.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return len(object_handle.AXRows)

    def selectrow(self, window_name, object_name, row_text, partial_match = False):
        """
        Select row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to select
        @type row_text: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        for cell in object_handle.AXRows:
            if re.match(row_text,
                        cell.AXChildren[0].AXValue):
                if not cell.AXSelected:
                    object_handle.activate()
                    cell.AXSelected=True
                else:
                    # Selected
                    pass
                return 1
        raise LdtpServerException(u"Unable to select row: %s" % row_text)

    def multiselect(self, window_name, object_name, row_text_list, partial_match = False):
        """
        Select multiple row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text_list: Row list with matching text to select
        @type row_text: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        object_handle.activate()
        selected = False
        window=self._get_front_most_window()
        for row_text in row_text_list:
            selected = False
            for cell in object_handle.AXRows:
                parent_cell = cell
                cell = self._getfirstmatchingchild(cell, "(AXTextField|AXStaticText)")
                if not cell:
                    continue
                if re.match(row_text, cell.AXValue):
                    selected = True
                    if not parent_cell.AXSelected:
                        x, y, width, height = self._getobjectsize(parent_cell)
                        window.clickMouseButtonLeftWithMods((x + width / 2,
                                                             y + height / 2),
                                                            ['<command_l>'])
                        # Following selection doesn't work
                        # parent_cell.AXSelected=True
                        self.wait(0.5)
                    else:
                        # Selected
                        pass
                    break
            if not selected:
                raise LdtpServerException(u"Unable to select row: %s" % row_text)
        if not selected:
            raise LdtpServerException(u"Unable to select any row")
        return 1

    def multiremove(self, window_name, object_name, row_text_list, partial_match = False):
        """
        Remove multiple row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text_list: Row list with matching text to select
        @type row_text: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        object_handle.activate()
        unselected = False
        window=self._get_front_most_window()
        for row_text in row_text_list:
            selected = False
            for cell in object_handle.AXRows:
                parent_cell = cell
                cell = self._getfirstmatchingchild(cell, "(AXTextField|AXStaticText)")
                if not cell:
                    continue
                if re.match(row_text, cell.AXValue):
                    unselected = True
                    if parent_cell.AXSelected:
                        x, y, width, height = self._getobjectsize(parent_cell)
                        window.clickMouseButtonLeftWithMods((x + width / 2,
                                                             y + height / 2),
                                                            ['<command_l>'])
                        # Following selection doesn't work
                        # parent_cell.AXSelected=False
                        self.wait(0.5)
                    else:
                        # Unselected
                        pass
                    break
            if not unselected:
                raise LdtpServerException(u"Unable to select row: %s" % row_text)
        if not unselected:
            raise LdtpServerException(u"Unable to unselect any row")
        return 1

    def selectrowpartialmatch(self, window_name, object_name, row_text):
        """
        Select row partial match

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to select
        @type row_text: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        for cell in object_handle.AXRows:
            if re.search(row_text,
                         cell.AXChildren[0].AXValue):
                if not cell.AXSelected:
                    object_handle.activate()
                    cell.AXSelected=True
                else:
                    # Selected
                    pass
                return 1
        raise LdtpServerException(u"Unable to select row: %s" % row_text)

    def selectrowindex(self, window_name, object_name, row_index):
        """
        Select row index

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to select
        @type row_index: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        count=len(object_handle.AXRows)
        if row_index < 0 or row_index > count:
            raise LdtpServerException('Row index out of range: %d' % row_index)
        cell=object_handle.AXRows[row_index]
        if not cell.AXSelected:
            object_handle.activate()
            cell.AXSelected=True
        else:
            # Selected
            pass
        return 1

    def selectlastrow(self, window_name, object_name):
        """
        Select last row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        cell=object_handle.AXRows[-1]
        if not cell.AXSelected:
            object_handle.activate()
            cell.AXSelected=True
        else:
            # Selected
            pass
        return 1

    def setcellvalue(self, window_name, object_name, row_index,
                     column=0, data=None):
        """
        Set cell value

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer
        @param data: data, default value None
                None, used for toggle button
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        raise LdtpServerException("Not implemented")

    def getcellvalue(self, window_name, object_name, row_index, column=0):
        """
        Get cell value

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer

        @return: cell value on success.
        @rtype: string
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        count=len(object_handle.AXRows)
        if row_index < 0 or row_index > count:
            raise LdtpServerException('Row index out of range: %d' % row_index)
        cell=object_handle.AXRows[row_index]
        count=len(cell.AXChildren)
        if column < 0 or column > count:
            raise LdtpServerException('Column index out of range: %d' % column)
        obj=cell.AXChildren[column]
        if not re.search("AXColumn", obj.AXRole):
            obj=cell.AXChildren[column]
        return obj.AXValue

    def getcellsize(self, window_name, object_name, row_index, column=0):
        """
        Get cell size

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer

        @return: cell coordinates on success.
        @rtype: list
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        count=len(object_handle.AXRows)
        if row_index < 0 or row_index > count:
            raise LdtpServerException('Row index out of range: %d' % row_index)
        cell=object_handle.AXRows[row_index]
        count=len(cell.AXChildren)
        if column < 0 or column > count:
            raise LdtpServerException('Column index out of range: %d' % column)
        obj=cell.AXChildren[column]
        if not re.search("AXColumn", obj.AXRole):
            obj=cell.AXChildren[column]
        return self._getobjectsize(obj)

    def rightclick(self, window_name, object_name, row_text):
        """
        Right click on table cell

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to right click
        @type row_text: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        object_handle.activate()
        self.wait(1)
        for cell in object_handle.AXRows:
            cell = self._getfirstmatchingchild(cell, "(AXTextField|AXStaticText)")
            if not cell:
                continue
            if re.match(row_text, cell.AXValue):
                x, y, width, height = self._getobjectsize(cell)
                # Mouse right click on the object
                cell.clickMouseButtonRight((x + width / 2, y + height / 2))
                return 1
        raise LdtpServerException(u'Unable to right click row: %s' % row_text)

    def checkrow(self, window_name, object_name, row_index, column = 0):
        """
        Check row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer

        @return: cell value on success.
        @rtype: string
        """
        raise LdtpServerException("Not implemented")

    def expandtablecell(self, window_name, object_name, row_index, column = 0):
        """
        Expand or contract table cell

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer

        @return: cell value on success.
        @rtype: string
        """
        raise LdtpServerException("Not implemented")

    def uncheckrow(self, window_name, object_name, row_index, column = 0):
        """
        Check row

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column: Column index to get, default value 0
        @type column: integer

        @return: 1 on success.
        @rtype: integer
        """
        raise LdtpServerException("Not implemented")

    def gettablerowindex(self, window_name, object_name, row_text):
        """
        Get table row index matching given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to select
        @type row_text: string

        @return: row index matching the text on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        index=0
        for cell in object_handle.AXRows:
            if re.match(row_text,
                        cell.AXChildren[0].AXValue):
                return index
            index += 1
        raise LdtpServerException(u"Unable to find row: %s" % row_text)

    def singleclickrow(self, window_name, object_name, row_text):
        """
        Single click row matching given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to select
        @type row_text: string

        @return: row index matching the text on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        object_handle.activate()
        self.wait(1)
        for cell in object_handle.AXRows:
            cell = self._getfirstmatchingchild(cell, "(AXTextField|AXStaticText)")
            if not cell:
                continue
            if re.match(row_text, cell.AXValue):
                x, y, width, height = self._getobjectsize(cell)
                # Mouse left click on the object
                cell.clickMouseButtonLeft((x + width / 2, y + height / 2))
                return 1
        raise LdtpServerException('Unable to get row text: %s' % row_text)

    def doubleclickrow(self, window_name, object_name, row_text):
        """
        Double click row matching given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to select
        @type row_text: string

        @return: row index matching the text on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        object_handle.activate()
        self.wait(1)
        for cell in object_handle.AXRows:
            cell = self._getfirstmatchingchild(cell, "(AXTextField|AXStaticText)")
            if not cell:
                continue
            if re.match(row_text, cell.AXValue):
                x, y, width, height = self._getobjectsize(cell)
                # Mouse double click on the object
                cell.doubleClickMouse((x + width / 2, y + height / 2))
                return 1
        raise LdtpServerException('Unable to get row text: %s' % row_text)

    def doubleclickrowindex(self, window_name, object_name, row_index, col_index=0):
        """
        Double click row matching given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type object_name: string
        @param row_index: Row index to click
        @type row_index: integer
        @param col_index: Column index to click
        @type col_index: integer

        @return: row index matching the text on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)

        count=len(object_handle.AXRows)
        if row_index < 0 or row_index > count:
            raise LdtpServerException('Row index out of range: %d' % row_index)
        cell=object_handle.AXRows[row_index]
        self._grabfocus(cell)
        x, y, width, height = self._getobjectsize(cell)
        # Mouse double click on the object
        cell.doubleClickMouse((x + width / 2, y + height / 2))
        return 1

    def verifytablecell(self, window_name, object_name, row_index,
                        column_index, row_text):
        """
        Verify table cell value with given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column_index: Column index to get, default value 0
        @type column_index: integer
        @param row_text: Row text to match
        @type string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            value=getcellvalue(window_name, object_name, row_index, column_index)
            if re.match(row_text, value):
                return 1
        except LdtpServerException:
            pass
        return 0

    def doesrowexist(self, window_name, object_name, row_text,
                     partial_match = False):
        """
        Verify table cell value with given text

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_text: Row text to match
        @type string
        @param partial_match: Find partial match strings
        @type boolean

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if not object_handle.AXEnabled:
                return 0

            for cell in object_handle.AXRows:
                if not partial_match and re.match(row_text,
                                                  cell.AXChildren[0].AXValue):
                    return 1
                elif partial_match and re.search(row_text,
                                                 cell.AXChildren[0].AXValue):
                    return 1
        except LdtpServerException:
            pass
        return 0

    def verifypartialtablecell(self, window_name, object_name, row_index,
                               column_index, row_text):
        """
        Verify partial table cell value

        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param row_index: Row index to get
        @type row_index: integer
        @param column_index: Column index to get, default value 0
        @type column_index: integer
        @param row_text: Row text to match
        @type string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            value=getcellvalue(window_name, object_name, row_index, column_index)
            if re.searchmatch(row_text, value):
                return 1
        except LdtpServerException:
            pass
        return 0

########NEW FILE########
__FILENAME__ = test
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Core class to be exposed via XMLRPC in LDTP daemon."""

import core

test=core.Core()
#test.launchapp('Calculator')
#print test.launchapp('Chicken of the VNC')
#print test.launchapp('app does not exist')
#test.wait(5)
#test.generatekeyevent('<return>')
#test.generatekeyevent('d')
#test.generatekeyevent('<tab><tab>')
#test.generatekeyevent('<command>t')
#test.generatekeyevent('<command>n')
#test.generatekeyevent('<command_l><tab>') # Not working
#test.keypress('<shift_l>') # Not working
#test.generatekeyevent('<shift>abc')
#test.generatekeyevent('xyz')
#test.generatekeyevent('<capslock>abc') # Caps lock not working
#test.keyrelease('<shift_l>') # Not working
#test.imagecapture('Untitled')
#apps=test.getapplist()
#windows=test.getwindowlist()
#test.generatemouseevent(10, 10)
#test.wait(3)
#size=test.getobjectsize("Jay")
#test.generatemouseevent(size[0] + 100, size[1] + 5, "b3c")
#test.generatemouseevent(size[0]-100, size[1], "b1d")
#print test.guiexist("gedit")
#print test.guiexist("gedit", "txt0")
#print test.guiexist("Open")
#print test.guiexist("Open", "btnCancel")
#print test.guiexist("Open", "C0ncel")
#print "waittillguiexist"
#print test.waittillguiexist("Open")
#print test.waittillguiexist("Open", "btnCancel")
#print test.waittillguiexist("Open", "C0ncel", 10)
#print "waittillguinotexist"
#print test.waittillguinotexist("Open", guiTimeOut=5)
#print test.waittillguinotexist("Open", "btnCancel", 5)
#print test.waittillguinotexist("Open", "C0ncel")
#print windows
#objList = test.getobjectlist("frmTryitEditorv1.5")
#for obj in objList:
    #if re.search("^tbl\d", obj):
        #print obj, test.getrowcount("frmTryitEditorv1.5", obj)
#print test.selectrow("Accounts", "tbl0", "VMware")
#print test.selectrowpartialmatch("Accounts", "tbl0", "Zim")
#print test.selectrowindex("Accounts", "tbl0", 0)
#print test.selectlastrow("Accounts", "tbl0")
#print test.getcellvalue("Accounts", "tbl0", 1)
#print test.scrollup("Downloads", "scbr0")
#print test.oneright("Downloads", "scbr1", 3)
#print len(apps), len(windows)
#print apps, windows
#print test.getobjectlist("Contacts")
#print test.click("Open", "Cancel")
#print test.comboselect("frmInstruments", "cboAdd", "UiAutomation.js")
#print test.comboselect("frmInstruments", "Choose Target", "Choose Target;Octopus")
#print test.getobjectlist("frmInstruments")
#print test.check("frmInstruments", "chkRecordOnce")
#print test.wait(1)
#print test.uncheck("frmInstruments", "chkRepeatRecording")
#print test.uncheck("frmInstruments", "chkPause")
#print test.verifyuncheck("frmInstruments", "chkPause")
#print test.verifycheck("frmInstruments", "chkRepeatRecording")
#print test.doesmenuitemexist("Instru*", "File;Open...")
#print test.doesmenuitemexist("Instruments*", "File;Open...")
#print test.doesmenuitemexist("Instruments*", "File;Open*")
#print test.selectmenuitem("Instruments*", "File;Open*")
#print test.checkmenu("Instruments*", "View;Instruments")
#test.wait(1)
#print test.checkmenu("Instruments*", "View;Instruments")
#print test.uncheckmenu("Instruments*", "View;Instruments")
#test.wait(1)
#print test.verifymenucheck("Instruments*", "View;Instruments")
#print test.verifymenuuncheck("Instruments*", "View;Instruments")
#print test.checkmenu("Instruments*", "View;Instruments")
#test.wait(1)
#print test.verifymenucheck("Instruments*", "View;Instruments")
#print test.verifymenuuncheck("Instruments*", "View;Instruments")
# Instruments Open dialog
#print test.mouseleftclick("Open", "Cancel")
#a=test.getobjectlist("Open")
#for i in a:
#    if i.find("txt") != -1:
#        print i
#print test.settextvalue("Open", "txttextfield", "pyatom ldtp")
#print test.gettextvalue("Open", "txttextfield")
#print test.getobjectinfo('Open', 'txttextfield')
#print test.getobjectproperty('Open', 'txttextfield', 'class')
#print test.inserttext("Open", "txttextfield", 0, "pyatom ldtp")
#print test.getcharcount("Open", "txttextfield")
#print test.menuitemenabled("Instruments*", "File;Record Trace")
#print test.menuitemenabled("Instruments*", "File;Pause Trace")
#print test.listsubmenus("Instruments*", "Fi*")
#print test.listsubmenus("Instruments*", "File;OpenRecent")
#print test.listsubmenus("Instruments*", "File;mnuOpenRecent")
#print test.listsubmenus("Instruments*", "File;GetInfo")
#try:
#    print test.listsubmenus("Instruments*", "File;ding")
#except LdtpServerException:
#    pass
#try:
#    print test.listsubmenus("Instruments*", "ding")
#except LdtpServerException:
#    pass
#try:
#    print test.listsubmenus("ding", "dong")
#except LdtpServerException:
#    pass
#print test.getcursorposition("Open", "txttextfield")
#print test.setcursorposition("Open", "txttextfield", 10)
#print test.cuttext("Open", "txttextfield", 2)
#print test.cuttext("Open", "txttextfield", 2, 20)
#print test.pastetext("Open", "txttextfield", 2)
#print test.gettabname("*ldtpd*python*", "ptl0", 2)
#print test.gettabcount("*ldtpd*python*", "ptl0")
#print test.selecttabindex("*ldtpd*python*", "ptl0", 2)
#print test.selecttab("*ldtpd*python*", "ptl0", "*bash*")
#print test.verifytabname("*ldtpd*python*", "ptl0", "*gabe*")
#print test.selectindex("frmInstruments", "cboAdd", 1)
#print test.getallitem("frmInstruments", "cboAdd")
#print test.selectindex("frmInstruments", "cboAdd", 10)
#print test.showlist("frmInstruments", "cboAdd")
#test.wait(1)
#print test.verifydropdown("frmInstruments", "cboAdd")
#print test.hidelist("frmInstruments", "cboAdd")
#test.wait(1)
#print test.verifydropdown("frmInstruments", "cboAdd")
#print test.showlist("frmInstruments", "cboAdd")
#test.wait(1)
#print test.verifyshowlist("frmInstruments", "cboAdd")
#print test.hidelist("frmInstruments", "cboAdd")
#test.wait(1)
#print test.verifyhidelist("frmInstruments", "cboAdd")
# Terminal settings window
#print test.comboselect("frmInstruments", "lst0", "Trace Log")
#print test.getallstates("Settings", "chkUseboldfonts")
#print test.getallstates("Settings", "chkAntialiastext")
#print test.getallstates("Settings", "rbtn*Block")
#print test.getallstates("Settings", "rbtn*Underline")
#print test.getaccesskey("test*Python*", "Window;Zoom") # Will raise exception
#print test.getaccesskey("test*Python*", "View;Scroll to Bottom")
# Based on preview open dialog
#print test.singleclickrow('Open', 'otloutline1', '31_09.jpeg')
#print test.doubleclickrow('Open', 'otloutline1', '31_09.jpeg')
#print test.doubleclickrowindex('Open', 'otloutline1', 0)
#print test.rightclick('Open', 'otloutline1', '31_09.jpeg')
# Based on Adium
#print test.ldtp.multiselect('Contacts', 'otloutline', ['Nagappan A', 'nagappanal'])
#test.wait(1)
#print test.ldtp.multiremove('Contacts', 'otloutline', ['Nagappan A', 'nagappanal'])

########NEW FILE########
__FILENAME__ = text
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Text class."""

import re
import fnmatch
import atomac.Clipboard as Clipboard

from utils import Utils
from keypress_actions import KeyComboAction, KeyPressAction, KeyReleaseAction
from server_exception import LdtpServerException

class Text(Utils):
    def generatekeyevent(self, data):
        """
        Functionality of generatekeyevent is similar to typekey of 
        LTFX project.
        
        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            window=self._get_front_most_window()
        except (IndexError, ):
            window=self._get_any_window()
        key_combo_action = KeyComboAction(window, data)
        return 1

    def keypress(self, data):
        """
        Press key. NOTE: keyrelease should be called

        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        window=self._get_front_most_window()
        key_press_action = KeyPressAction(window, data)
        return 1

    def keyrelease(self, data):
        """
        Release key. NOTE: keypress should be called before this

        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        window=self._get_front_most_window()
        key_release_action = KeyReleaseAction(window, data)
        return 1

    def enterstring(self, window_name, object_name='', data=''):
        """
        Type string sequence.
        
        @param window_name: Window name to focus on, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to focus on, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        if not object_name and not data:
            return self.generatekeyevent(window_name)
        else:
            object_handle=self._get_object_handle(window_name, object_name)
            if not object_handle.AXEnabled:
                raise LdtpServerException(u"Object %s state disabled" % object_name)
            self._grabfocus(object_handle)
            object_handle.sendKeys(data)
            return 1

    def settextvalue(self, window_name, object_name, data):
        """
        Type string sequence.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        object_handle.AXValue=data
        return 1

    def gettextvalue(self, window_name, object_name, startPosition=0, endPosition=0):
        """
        Get text value
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param startPosition: Starting position of text to fetch
        @type: startPosition: int
        @param endPosition: Ending position of text to fetch
        @type: endPosition: int

        @return: text on success.
        @rtype: string
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return object_handle.AXValue

    def inserttext(self, window_name, object_name, position, data):
        """
        Insert string sequence in given position.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param position: position where text has to be entered.
        @type data: int
        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        existing_data=object_handle.AXValue
        size=len(existing_data)
        if position < 0:
            position=0
        if position > size:
            position=size
        object_handle.AXValue=existing_data[:position] + data + \
            existing_data[position:]
        return 1

    def verifypartialmatch(self, window_name, object_name, partial_text):
        """
        Verify partial text
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param partial_text: Partial text to match
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            if re.search(fnmatch.translate(partial_text),
                         self.gettextvalue(window_name,
                                           object_name)):
                return 1
        except:
            pass
        return 0

    def verifysettext(self, window_name, object_name, text):
        """
        Verify text is set correctly
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param text: text to match
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        try:
            return int(re.match(fnmatch.translate(text),
                                self.gettextvalue(window_name,
                                                  object_name)))
        except:
            return 0

    def istextstateenabled(self, window_name, object_name):
        """
        Verifies text state enabled or not
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success 0 on failure.
        @rtype: integer
        """
        try:
            object_handle=self._get_object_handle(window_name, object_name)
            if object_handle.AXEnabled:
                return 1
        except LdtpServerException:
            pass
        return 0

    def getcharcount(self, window_name, object_name):
        """
        Get character count
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return object_handle.AXNumberOfCharacters

    def appendtext(self, window_name, object_name, data):
        """
        Append string sequence.
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param data: data to type.
        @type data: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        object_handle.AXValue += data
        return 1

    def getcursorposition(self, window_name, object_name):
        """
        Get cursor position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string

        @return: Cursor position on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        return object_handle.AXSelectedTextRange.loc

    def setcursorposition(self, window_name, object_name, cursor_position):
        """
        Set cursor position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param cursor_position: Cursor position to be set
        @type object_name: string

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        object_handle.AXSelectedTextRange.loc=cursor_position
        return 1

    def cuttext(self, window_name, object_name, start_position, end_position=-1):
        """
        cut text from start position to end position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param start_position: Start position
        @type object_name: integer
        @param end_position: End position, default -1
        Cut all the text from start position till end
        @type object_name: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=object_handle.AXNumberOfCharacters
        if end_position == -1 or end_position > size:
            end_position=size
        if start_position < 0:
            start_position=0
        data=object_handle.AXValue
        Clipboard.copy(data[start_position:end_position])
        object_handle.AXValue=data[:start_position] + data[end_position:]
        return 1

    def copytext(self, window_name, object_name, start_position, end_position=-1):
        """
        copy text from start position to end position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param start_position: Start position
        @type object_name: integer
        @param end_position: End position, default -1
        Copy all the text from start position till end
        @type object_name: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=object_handle.AXNumberOfCharacters
        if end_position == -1 or end_position > size:
            end_position=size
        if start_position < 0:
            start_position=0
        data=object_handle.AXValue
        Clipboard.copy(data[start_position:end_position])
        return 1


    def deletetext(self, window_name, object_name, start_position, end_position=-1):
        """
        delete text from start position to end position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param start_position: Start position
        @type object_name: integer
        @param end_position: End position, default -1
        Delete all the text from start position till end
        @type object_name: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=object_handle.AXNumberOfCharacters
        if end_position == -1 or end_position > size:
            end_position=size
        if start_position < 0:
            start_position=0
        data=object_handle.AXValue
        object_handle.AXValue=data[:start_position] + data[end_position:]
        return 1

    def pastetext(self, window_name, object_name, position=0):
        """
        paste text from start position to end position
        
        @param window_name: Window name to type in, either full name,
        LDTP's name convention, or a Unix glob.
        @type window_name: string
        @param object_name: Object name to type in, either full name,
        LDTP's name convention, or a Unix glob. 
        @type object_name: string
        @param position: Position to paste the text, default 0
        @type object_name: integer

        @return: 1 on success.
        @rtype: integer
        """
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=object_handle.AXNumberOfCharacters
        if position > size:
            position=size
        if position < 0:
            position=0
        clipboard=Clipboard.paste()
        data=object_handle.AXValue
        object_handle.AXValue=data[:position] + clipboard + data[position:]
        return 1

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Utils class."""

import os
import re
import time
import atomac
import fnmatch
import logging
import threading
import traceback
import logging.handlers

from constants import abbreviated_roles, ldtp_class_type
from server_exception import LdtpServerException

importPsUtil = False
try:
    import psutil
    importPsUtil=True
except ImportError:
    pass

class LdtpCustomLog(logging.Handler):
    """
    Custom LDTP log, inherit logging.Handler and implement
    required API
    """
    def __init__(self):
        # Call base handler
        logging.Handler.__init__(self)
        # Log all the events in list
        self.log_events=[]

    def emit(self, record):
        # Get the message and add to the list
        # Later the list element can be poped out
        self.log_events.append(u'%s-%s' % (record.levelname, record.getMessage()))

# Add LdtpCustomLog handler
logging.handlers.LdtpCustomLog=LdtpCustomLog
# Create instance of LdtpCustomLog handler
_custom_logger=logging.handlers.LdtpCustomLog()
# Set default log level as ERROR
_custom_logger.setLevel(logging.ERROR)
# Add handler to root logger
logger=logging.getLogger('')
# Add custom logger to the root logger
logger.addHandler(_custom_logger)

LDTP_LOG_MEMINFO=60
LDTP_LOG_CPUINFO=61
logging.addLevelName(LDTP_LOG_MEMINFO, 'MEMINFO')
logging.addLevelName(LDTP_LOG_CPUINFO, 'CPUINFO')

class ProcessStats(threading.Thread):
    """
    Capturing Memory and CPU Utilization statistics for an application and its related processes
    NOTE: You have to install python-psutil package
    EXAMPLE USAGE:

    xstats = ProcessStats('evolution', 2)
    # Start Logging by calling start
    xstats.start()
    # Stop the process statistics gathering thread by calling the stopstats method
    xstats.stop()
    """

    def __init__(self, appname, interval = 2):
        """
        Start memory and CPU monitoring, with the time interval between
        each process scan

        @param appname: Process name, ex: firefox-bin.
        @type appname: string
        @param interval: Time interval between each process scan
        @type interval: float
        """
        if not importPsUtil:
            raise LdtpServerException('python-psutil package is not installed')
        threading.Thread.__init__(self)
        self._appname = appname
        self._interval = interval
        self._stop = False
        self.running = True

    def __del__(self):
        self._stop = False
        self.running = False

    def get_cpu_memory_stat(self):
        proc_list = []
        for p in psutil.process_iter():
            if self._stop:
                self.running = False
                return proc_list
            if not re.match(fnmatch.translate(self._appname),
                            p.name, re.U | re.L):
                # If process name doesn't match, continue
                continue
            proc_list.append(p)
        return proc_list

    def run(self):
        while not self._stop:
            for p in self.get_cpu_memory_stat():
                try:
                    # Add the stats into ldtp log
                    # Resident memory will be in bytes, to convert it to MB
                    # divide it by 1024*1024
                    logger.log(LDTP_LOG_MEMINFO, '%s(%s) - %s' % \
                                   (p.name, str(p.pid), p.get_memory_percent()))
                    # CPU percent returned with 14 decimal values
                    # ex: 0.0281199122531, round it to 2 decimal values
                    # as 0.03
                    logger.log(LDTP_LOG_CPUINFO, '%s(%s) - %s' % \
                                   (p.name, str(p.pid), p.get_cpu_percent()))
                except psutil.AccessDenied:
                    pass
            # Wait for interval seconds before gathering stats again
            try:
                time.sleep(self._interval)
            except KeyboardInterrupt:
                self._stop = True

    def stop(self):
        self._stop = True
        self.running = False

class Utils(object):
    def __init__(self):
        self._appmap={}
        self._windows={}
        self._obj_timeout=5
        self._window_timeout=30
        self._callback_event=[]
        self._app_under_test=None
        self._custom_logger=_custom_logger
        # Current opened applications list will be updated
        self._running_apps=atomac.NativeUIElement._getRunningApps()
        if os.environ.has_key("LDTP_DEBUG"):
            self._ldtp_debug=True
            self._custom_logger.setLevel(logging.DEBUG)
        else:
            self._ldtp_debug=False
        self._ldtp_debug_file = os.environ.get('LDTP_DEBUG_FILE', None)

    def _listMethods(self):
        _methods=[]
        for symbol in dir(self):
            if symbol.startswith('_'): 
                continue
            _methods.append(symbol)
        return _methods

    def _methodHelp(self, method):
        return getattr(self, method).__doc__

    def _dispatch(self, method, args):
        try:
            return getattr(self, method)(*args)
        except:
            if self._ldtp_debug:
                print(traceback.format_exc())
            if self._ldtp_debug_file:
                with open(self._ldtp_debug_file, "a") as fp:
                    fp.write(traceback.format_exc())
            raise

    def _get_front_most_window(self):
        app=atomac.NativeUIElement.getFrontmostApp()
        return app.windows()[0]

    def _get_any_window(self):
        front_app=atomac.NativeUIElement.getAnyAppWithWindow()
        return front_app.windows()[0]

    def _ldtpize_accessible(self, acc):
        """
        Get LDTP format accessibile name

        @param acc: Accessible handle
        @type acc: object

        @return: object type, stripped object name (associated / direct),
                        associated label
        @rtype: tuple
        """
        actual_role=self._get_role(acc)
        label=self._get_title(acc)
        if re.match("AXWindow", actual_role, re.M | re.U | re.L):
            # Strip space and new line from window title
            strip=r"( |\n)"
        else:
            # Strip space, colon, dot, underscore and new line from
            # all other object types
            strip=r"( |:|\.|_|\n)"
        if label:
            # Return the role type (if, not in the know list of roles,
            # return ukn - unknown), strip the above characters from name
            # also return labely_by string
            if not isinstance(label, unicode):
                label=u"%s" % label
            label=re.sub(strip, u"", label)
        role=abbreviated_roles.get(actual_role, "ukn")
        if self._ldtp_debug and role == "ukn":
            print(actual_role, acc)
        return role, label

    def _glob_match(self, pattern, string):
        """
        Match given string, by escaping regex characters
        """
        # regex flags Multi-line, Unicode, Locale
        return bool(re.match(fnmatch.translate(pattern), string,
                             re.M | re.U | re.L))
 
    def _match_name_to_appmap(self, name, acc):
        if not name:
            return 0
        if self._glob_match(name, acc['obj_index']):
            return 1
        if self._glob_match(name, acc['label']):
            return 1
        role = acc['class']
        if role == 'frame' or role == 'dialog' or role == 'window':
            strip = '( |\n)'
        else:
            strip = '( |:|\.|_|\n)'
        obj_name = re.sub(strip, '', name)
        if acc['label']:
            _tmp_name = re.sub(strip, '', acc['label'])
            if self._glob_match(obj_name, _tmp_name):
                return 1
        return 0

    def _insert_obj(self, obj_dict, obj, parent, child_index):
        ldtpized_name=self._ldtpize_accessible(obj)
        if ldtpized_name[0] in self._ldtpized_obj_index:
            self._ldtpized_obj_index[ldtpized_name[0]] += 1
        else:
            self._ldtpized_obj_index[ldtpized_name[0]]=0
        try:
            key="%s%s" % (ldtpized_name[0], ldtpized_name[1])
        except UnicodeEncodeError:
            key="%s%s" % (ldtpized_name[0],
                          ldtpized_name[1].decode("utf-8"))
        if not ldtpized_name[1]:
            index=0
            # Object doesn't have any associated label
            key="%s%d" % (ldtpized_name[0], index)
        else:
            index=1
        while obj_dict.has_key(key):
            # If the same object type with matching label exist
            # add index to it
            try:
                key="%s%s%d" % (ldtpized_name[0],
                                ldtpized_name[1], index)
            except UnicodeEncodeError:
                key="%s%s%d" % (ldtpized_name[0],
                                ldtpized_name[1].decode("utf-8"), index)
            index += 1
        if ldtpized_name[0] == "frm":
            # Window
            # FIXME: As in Linux (app#index, rather than window#index)
            obj_index="%s#%d" % (ldtpized_name[0],
                                 self._ldtpized_obj_index[ldtpized_name[0]])
        else:
            # Object inside the window
            obj_index="%s#%d" % (ldtpized_name[0],
                                 self._ldtpized_obj_index[ldtpized_name[0]])
        if parent in obj_dict:
            _current_children=obj_dict[parent]["children"]
            if _current_children:
                _current_children="%s %s" % (_current_children, key)
            else:
                _current_children=key
            obj_dict[parent]["children"]=_current_children
        actual_role=self._get_role(obj)
        obj_dict[key]={"obj" : obj,
                       # Use Linux based class type for compatibility
                       # If class type doesn't exist in list, use actual type
                       "class" : ldtp_class_type.get(actual_role, actual_role),
                       "label" : ldtpized_name[1],
                       "parent" : parent,
                       "children" : "",
                       "child_index" : child_index,
                       "obj_index" : obj_index}
        return key

    def _get_windows(self, force_remap=False):
        if not force_remap and self._windows:
            # Get the windows list from cache
            return self._windows
        # Update current running applications
        # as force_remap flag has been set
        self._update_apps()
        windows={}
        self._ldtpized_obj_index={}
        for gui in set(self._running_apps):
            if self._app_under_test and \
                    self._app_under_test != gui.bundleIdentifier() and \
                    self._app_under_test != gui.localizedName():
                # Not the app under test, search next application
                continue
            # Get process id
            pid=gui.processIdentifier()
            # Get app id
            app=atomac.getAppRefByPid(pid)
            # Get all windows of current app
            app_windows=app.windows()
            try:
                # Tested with
                # selectmenuitem('appChickenoftheVNC', 'Connection;Open Connection…')
                if not app_windows and app.AXRole == "AXApplication":
                    # If app doesn't have any windows and its role is AXApplication
                    # add to window list
                    key=self._insert_obj(windows, app, "", -1)
                    windows[key]["app"]=app
                    continue
            except (atomac._a11y.ErrorAPIDisabled, \
                        atomac._a11y.ErrorCannotComplete, \
                        atomac._a11y.Error, \
                        atomac._a11y.ErrorInvalidUIElement):
                pass
            # Navigate all the windows
            for window in app_windows:
                if not window:
                    continue
                key=self._insert_obj(windows, window, "", -1)
                windows[key]["app"]=app
        # Replace existing windows list
        self._windows=windows
        return windows

    def _get_title(self, obj):
        title=""
        role=""
        try:
            role=obj.AXRole
            desc=obj.AXRoleDescription
            if re.match("(AXStaticText|AXRadioButton|AXButton)",
                        role, re.M | re.U | re.L) and \
                    (desc == "text" or desc == "radio button" or \
                         desc == "button") and obj.AXValue:
                return obj.AXValue
        except:
            pass
        try:
            checkBox=re.match("AXCheckBox", role, re.M | re.U | re.L)
            if checkBox:
                # Instruments doesn't have AXTitle, AXValue for AXCheckBox
                try:
                    title=obj.AXHelp
                except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                    pass
            if not title:
                title=obj.AXTitle
        except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
            try:
                text=re.match("(AXTextField|AXTextArea)", role,
                                re.M | re.U | re.L)
                if text:
                    title=obj.AXFilename
                else:
                    if not re.match("(AXTabGroup)", role,
                                    re.M | re.U | re.L):
                        # Tab group has AXRadioButton as AXValue
                        # So skip it
                        if re.match("(AXScrollBar)", role,
                                    re.M | re.U | re.L):
                            # ScrollBar value is between 0 to 1
                            # which is used to get the current location
                            # of the ScrollBar, rather than the object name
                            # Let us have the title as empty string and
                            # refer the ScrollBar as scbr0 (Vertical),
                            # scbr1 (Horizontal)
                            title=""
                        else:
                            title=obj.AXValue
            except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                if re.match("AXButton", role,
                            re.M | re.U | re.L):
                    try:
                        title=obj.AXDescription
                        if title:
                            return title
                    except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                        pass
                try:
                    if not re.match("(AXList|AXTable)", role,
                                    re.M | re.U | re.L):
                        # List have description as list
                        # So skip it
                        title=obj.AXRoleDescription
                except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                    pass
        if not title:
            if re.match("(AXButton|AXCheckBox)", role,
                        re.M | re.U | re.L):
                try:
                    title=obj.AXRoleDescription
                    if title:
                       return title
                except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                    pass
            elif re.match("(AXStaticText)", role,
                          re.M | re.U | re.L):
                try:
                    title=obj.AXValue
                    if title:
                       return title
                except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
                    pass
            # Noticed that some of the above one assigns title as None
            # in that case return empty string
            return ""
        return title

    def _get_role(self, obj):
        role=""
        try:
            role=obj.AXRole
        except (atomac._a11y.ErrorUnsupported, atomac._a11y.Error):
            pass
        return role

    def _update_apps(self):
        # Current opened applications list will be updated
        self._running_apps=atomac.NativeUIElement._getRunningApps()

    def _singleclick(self, window_name, object_name):
        object_handle=self._get_object_handle(window_name, object_name)
        if not object_handle.AXEnabled:
            raise LdtpServerException(u"Object %s state disabled" % object_name)
        size=self._getobjectsize(object_handle)
        self._grabfocus(object_handle)
        self.wait(0.5)
        self.generatemouseevent(size[0] + size[2]/2, size[1] + size[3]/2, "b1c")
        return 1

    def _grabfocus(self, handle):
        if not handle:
            raise LdtpServerException("Invalid handle")
        
        try:
            if handle.AXRole == "AXWindow":
                # Raise window
                handle.Raise()
        except (AttributeError,):
            try:
                if handle[0].AXRole == "AXWindow":
                    handle[0].Raise()
            except (IndexError, AttributeError):
                # First bring the window to front
                handle.AXWindow.Raise()
                # Focus object
                handle.activate()
        return 1

    def _getobjectsize(self, handle):
        if not handle:
            raise LdtpServerException("Invalid handle")
        x, y=handle.AXPosition
        width, height=handle.AXSize
        return x, y, width, height

    def _get_window_handle(self, window_name, wait_for_window=True):
        if not window_name:
            raise LdtpServerException("Invalid argument passed to window_name")
        # Will be used to raise the exception with user passed window name
        orig_window_name=window_name
        window_obj=(None, None, None)
        strip=r"( |\n)"
        if not isinstance(window_name, unicode):
            # Convert to unicode string
            window_name=u"%s" % window_name
        stripped_window_name=re.sub(strip, u"", window_name)
        window_name=fnmatch.translate(window_name)
        stripped_window_name=fnmatch.translate(stripped_window_name)
        windows=self._get_windows()
        def _internal_get_window_handle(windows):
            # To handle retry this function has been introduced
            for window in windows:
                label=windows[window]["label"]
                strip=r"( |\n)"
                if not isinstance(label, unicode):
                    # Convert to unicode string
                    label=u"%s" % label
                stripped_label=re.sub(strip, u"", label)
                # FIXME: Find window name in LDTP format 
                if re.match(window_name, window) or \
                        re.match(window_name, label) or \
                        re.match(window_name, stripped_label) or \
                        re.match(stripped_window_name, window) or \
                        re.match(stripped_window_name, label) or \
                        re.match(stripped_window_name, stripped_label):
                    # Return window handle and window name
                    return (windows[window]["obj"], window, windows[window]["app"])
            return (None, None, None)
        if wait_for_window:
            window_timeout=self._obj_timeout
        else:
            # don't wait for the window 
            window_timeout=1
        for retry in range(0, window_timeout):
            window_obj=_internal_get_window_handle(windows)
            if window_obj[0]:
                # If window object found, return immediately
                return window_obj
            if window_timeout <= 1:
                # Don't wait for the window
                break
            time.sleep(1)
            windows=self._get_windows(True)
        if not window_obj[0]:
            raise LdtpServerException('Unable to find window "%s"' % \
                                          orig_window_name)
        return window_obj

    def _get_object_handle(self, window_name, obj_name, obj_type=None,
                           wait_for_object=True):
        try:
            return self._internal_get_object_handle(window_name, obj_name,
                                                    obj_type, wait_for_object)
        except atomac._a11y.ErrorInvalidUIElement:
            # During the test, when the window closed and reopened
            # ErrorInvalidUIElement exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            return self._internal_get_object_handle(window_name, obj_name,
                                                    obj_type, wait_for_object)

    def _internal_get_object_handle(self, window_name, obj_name, obj_type=None,
                                    wait_for_object=True):
        try:
            obj=self._get_object_map(window_name, obj_name, obj_type,
                                     wait_for_object)
            # Object might not exist, just check whether it exist
            object_handle=obj["obj"]
            # Look for Window's role, on stale windows this will
            # throw AttributeError exception, if so relookup windows
            # and search for the object
            object_handle.AXWindow.AXRole
        except (atomac._a11y.ErrorCannotComplete,
                atomac._a11y.ErrorUnsupported,
                atomac._a11y.ErrorInvalidUIElement, AttributeError):
            # During the test, when the window closed and reopened
            # ErrorCannotComplete exception will be thrown
            self._windows={}
            # Call the method again, after updating apps
            obj=self._get_object_map(window_name, obj_name, obj_type,
                                     wait_for_object, True)
        # Return object handle
        # FIXME: Check object validity before returning
        # if object state is invalid, then remap
        return obj["obj"]

    def _get_object_map(self, window_name, obj_name, obj_type=None,
                           wait_for_object=True, force_remap=False):
        if not window_name:
            raise LdtpServerException("Unable to find window %s" % window_name)
        window_handle, ldtp_window_name, app=self._get_window_handle(window_name,
                                                                     wait_for_object)
        if not window_handle:
            raise LdtpServerException("Unable to find window %s" % window_name)
        strip=r"( |:|\.|_|\n)"
        if not isinstance(obj_name, unicode):
            # Convert to unicode string
            obj_name=u"%s" % obj_name
        stripped_obj_name=re.sub(strip, u"", obj_name)
        obj_name=fnmatch.translate(obj_name)
        stripped_obj_name=fnmatch.translate(stripped_obj_name)
        object_list=self._get_appmap(window_handle, ldtp_window_name, force_remap)
        def _internal_get_object_handle(object_list):
            # To handle retry this function has been introduced
            for obj in object_list:
                if obj_type and object_list[obj]["class"] != obj_type:
                    # If object type is provided and doesn't match
                    # don't proceed further, just continue searching
                    # next element, even though the label matches
                    continue
                label=object_list[obj]["label"]
                strip=r"( |:|\.|_|\n)"
                if not isinstance(label, unicode):
                    # Convert to unicode string
                    label=u"%s" % label
                stripped_label=re.sub(strip, u"", label)
                # FIXME: Find object name in LDTP format
                if re.match(obj_name, obj) or re.match(obj_name, label) or \
                        re.match(obj_name, stripped_label) or \
                        re.match(stripped_obj_name, obj) or \
                        re.match(stripped_obj_name, label) or \
                        re.match(stripped_obj_name, stripped_label):
                    # Return object map
                    return object_list[obj]
        if wait_for_object:
            obj_timeout=self._obj_timeout
        else:
            # don't wait for the object 
            obj_timeout=1
        for retry in range(0, obj_timeout):
            obj=_internal_get_object_handle(object_list)
            if obj:
                # If object found, return immediately
                return obj
            if obj_timeout <= 1:
                # Don't wait for the object
                break
            time.sleep(1)
            # Force remap
            object_list=self._get_appmap(window_handle,
                                         ldtp_window_name, True)
            # print(object_list)
        raise LdtpServerException("Unable to find object %s" % obj_name)

    def _populate_appmap(self, obj_dict, obj, parent, child_index):
        index=-1
        if obj:
            if child_index != -1:
                parent=self._insert_obj(obj_dict, obj, parent, child_index)
            try:
                if not obj.AXChildren:
                    return
            except atomac._a11y.Error:
                return
            for child in obj.AXChildren:
                index += 1
                if not child:
                    continue
                self._populate_appmap(obj_dict, child, parent, index)

    def _get_appmap(self, window_handle, window_name, force_remap=False):
        if not window_handle or not window_name:
            # If invalid argument return empty dict
            return {}
        if not force_remap and self._appmap.has_key(window_name):
            # If available in cache then use that
            # unless remap is forced
            return self._appmap[window_name]
        obj_dict={}
        self._ldtpized_obj_index={}
        # Populate the appmap and cache it
        self._populate_appmap(obj_dict, window_handle, "", -1)
        # Cache the object dictionary
        self._appmap[window_name]=obj_dict
        return obj_dict

    def _get_menu_handle(self, window_name, object_name,
                         wait_for_window=True):
        window_handle, name, app=self._get_window_handle(window_name,
                                                         wait_for_window)
        if not window_handle:
            raise LdtpServerException("Unable to find window %s" % window_name)
        # pyatom doesn't understand LDTP convention mnu, strip it off
        menu=re.sub("mnu", "", object_name)
        if re.match("^\d", menu):
            obj_dict=self._get_appmap(window_handle, name)
            return obj_dict[object_name]["obj"]
        menu_handle=app.menuItem(menu)
        if  menu_handle:
            return menu_handle
        # Above one looks for menubar item
        # Following looks for menuitem inside the window
        menu_handle_list=window_handle.findAllR(AXRole="AXMenu")
        for menu_handle in menu_handle_list:
            sub_menu_handle=self._get_sub_menu_handle(menu_handle, object_name)
            if sub_menu_handle:
                return sub_menu_handle
        raise LdtpServerException("Unable to find menu %s" % object_name)

    def _get_sub_menu_handle(self, children, menu):
        strip=r"( |:|\.|_|\n)"
        tmp_menu=fnmatch.translate(menu)
        stripped_menu=fnmatch.translate(re.sub(strip, u"", menu))
        for current_menu in children.AXChildren:
            role, label=self._ldtpize_accessible(current_menu)
            if re.match(tmp_menu, label) or \
                    re.match(tmp_menu, u"%s%s" % (role, label)) or \
                    re.match(stripped_menu, label) or \
                    re.match(stripped_menu, u"%s%s" % (role, label)):
                return current_menu
        raise LdtpServerException("Unable to find menu %s" % menu)

    def _internal_menu_handler(self, menu_handle, menu_list,
                               perform_action = False):
        if not menu_handle or not menu_list:
            raise LdtpServerException("Unable to find menu %s" % [0])
        for menu in menu_list:
            # Get AXMenu
            if not menu_handle.AXChildren:
                try:
                    # Noticed this issue, on clicking Skype
                    # menu in notification area
                    menu_handle.Press()
                except atomac._a11y.ErrorCannotComplete:
                    if self._ldtp_debug:
                        print traceback.format_exc()
                    if self._ldtp_debug_file:
                        with open(self._ldtp_debug_file, "a") as fp:
                            fp.write(traceback.format_exc())
            # For some reason, on accessing the lenght first
            # doesn't crash, else
            """
            Traceback (most recent call last):
              File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/utils.py", line 178, in _dispatch
                return getattr(self, method)(*args)
              File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/menu.py", line 63, in selectmenuitem
                menu_handle=self._get_menu_handle(window_name, object_name)
              File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/menu.py", line 47, in _get_menu_handle
                return self._internal_menu_handler(menu_handle, menu_list[1:])
              File "build/bdist.macosx-10.8-intel/egg/atomac/ldtpd/utils.py", line 703, in _internal_menu_handler
                children=menu_handle.AXChildren[0]
            IndexError: list index out of range
            """
            len(menu_handle.AXChildren)
            # Now with above line, everything works fine
            # on doing selectmenuitem('appSystemUIServer', 'mnu0;Open Display*')
            children=menu_handle.AXChildren[0]
            if not children:
                raise LdtpServerException("Unable to find menu %s" % menu)
            menu_handle=self._get_sub_menu_handle(children, menu)
            # Don't perform action on last item
            if perform_action and menu_list[-1] != menu:
                if not menu_handle.AXEnabled:
                    # click back on combo box
                    menu_handle.Cancel()
                    raise LdtpServerException("Object %s state disabled" % \
                                              menu)
                    # Click current menuitem, required for combo box
                    menu_handle.Press()
                    # Required for menuitem to appear in accessibility list
                    self.wait(1) 
            if not menu_handle:
                raise LdtpServerException("Unable to find menu %s" % menu)
        return menu_handle

    def _getfirstmatchingchild(self, obj, role):
        if not obj or not role:
            return
        if re.match(role, obj.AXRole):
            return obj
        if  not obj.AXChildren:
            return
        for child in obj.AXChildren:
            matching_child = self._getfirstmatchingchild(child, role)
            if matching_child:
                return matching_child
        return

########NEW FILE########
__FILENAME__ = value
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Yingjun Li <yingjunli@gmail.com>                                                                                                      
#@copyright: Copyright (c) 2009-12 Yingjun Li                                                                                                  
#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Value class."""

import time

from utils import Utils
from server_exception import LdtpServerException

class Value(Utils):
   def verifyscrollbarvertical(self, window_name, object_name):
      """
      Verify scrollbar is vertical
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      try:
         object_handle = self._get_object_handle(window_name, object_name)
         if object_handle.AXOrientation == "AXVerticalOrientation":
            return 1
      except:
         pass
      return 0

   def verifyscrollbarhorizontal(self, window_name, object_name):
      """
      Verify scrollbar is horizontal
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      try:
         object_handle = self._get_object_handle(window_name, object_name)
         if object_handle.AXOrientation == "AXHorizontalOrientation":
            return 1
      except:
         pass
      return 0

   def setmax(self, window_name, object_name):
      """
      Set max value
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      object_handle = self._get_object_handle(window_name, object_name)
      object_handle.AXValue = 1
      return 1
   
   def setmin(self, window_name, object_name):
      """
      Set min value
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      object_handle = self._get_object_handle(window_name, object_name)
      object_handle.AXValue = 0
      return 1
   
   def scrollup(self, window_name, object_name):
      """
      Scroll up
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarvertical(window_name, object_name):
         raise LdtpServerException('Object not vertical scrollbar')
      return self.setmin(window_name, object_name)
   
   def scrolldown(self, window_name, object_name):
      """
      Scroll down
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarvertical(window_name, object_name):
         raise LdtpServerException('Object not vertical scrollbar')
      return self.setmax(window_name, object_name)

   def scrollleft(self, window_name, object_name):
      """
      Scroll left
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarhorizontal(window_name, object_name):
         raise LdtpServerException('Object not horizontal scrollbar')
      return self.setmin(window_name, object_name)
   
   def scrollright(self, window_name, object_name):
      """
      Scroll right
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarhorizontal(window_name, object_name):
         raise LdtpServerException('Object not horizontal scrollbar')
      return self.setmax(window_name, object_name)

   def onedown(self, window_name, object_name, iterations):
      """
      Press scrollbar down with number of iterations
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      @param interations: iterations to perform on slider increase
      @type iterations: integer
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarvertical(window_name, object_name):
         raise LdtpServerException('Object not vertical scrollbar')
      object_handle = self._get_object_handle(window_name, object_name)
      i = 0
      maxValue = 1.0 / 8
      flag = False
      while i < iterations:
         if object_handle.AXValue >= 1:
            raise LdtpServerException('Maximum limit reached')
         object_handle.AXValue += maxValue
         time.sleep(1.0 / 100)
         flag = True
         i += 1
      if flag:
         return 1
      else:
         raise LdtpServerException('Unable to increase scrollbar')
   
   def oneup(self, window_name, object_name, iterations):
      """
      Press scrollbar up with number of iterations
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      @param interations: iterations to perform on slider increase
      @type iterations: integer
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarvertical(window_name, object_name):
         raise LdtpServerException('Object not vertical scrollbar')
      object_handle = self._get_object_handle(window_name, object_name)
      i = 0
      minValue = 1.0 / 8
      flag = False
      while i < iterations:
         if object_handle.AXValue <= 0:
            raise LdtpServerException('Minimum limit reached')
         object_handle.AXValue -= minValue
         time.sleep(1.0 / 100)
         flag = True
         i += 1
      if flag:
         return 1
      else:
         raise LdtpServerException('Unable to decrease scrollbar')
      
   def oneright(self, window_name, object_name, iterations):
      """
      Press scrollbar right with number of iterations
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      @param interations: iterations to perform on slider increase
      @type iterations: integer
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarhorizontal(window_name, object_name):
         raise LdtpServerException('Object not horizontal scrollbar')
      object_handle = self._get_object_handle(window_name, object_name)
      i = 0
      maxValue = 1.0 / 8
      flag = False
      while i < iterations:
         if object_handle.AXValue >= 1:
            raise LdtpServerException('Maximum limit reached')
         object_handle.AXValue += maxValue
         time.sleep(1.0 / 100)
         flag = True
         i += 1
      if flag:
         return 1
      else:
         raise LdtpServerException('Unable to increase scrollbar')

   def oneleft(self, window_name, object_name, iterations):
      """
      Press scrollbar left with number of iterations
      
      @param window_name: Window name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type window_name: string
      @param object_name: Object name to type in, either full name,
      LDTP's name convention, or a Unix glob.
      @type object_name: string
      @param interations: iterations to perform on slider increase
      @type iterations: integer
      
      @return: 1 on success.
      @rtype: integer
      """
      if not self.verifyscrollbarhorizontal(window_name, object_name):
         raise LdtpServerException('Object not horizontal scrollbar')
      object_handle = self._get_object_handle(window_name, object_name)
      i = 0
      minValue = 1.0 / 8
      flag = False
      while i < iterations:
         if object_handle.AXValue <= 0:
            raise LdtpServerException('Minimum limit reached')
         object_handle.AXValue -= minValue
         time.sleep(1.0 / 100)
         flag = True
         i += 1
      if flag:
         return 1
      else:
         raise LdtpServerException('Unable to decrease scrollbar')

########NEW FILE########
__FILENAME__ = client_exception
# Copyright (c) 2012 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

#@author: Eitan Isaacson <eitan@ascender.com>
#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009 Eitan Isaacson
#@copyright: Copyright (c) 2009-12 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Python LDTP exception"""

ERROR_CODE = 123

class LdtpExecutionError(Exception):
    pass

########NEW FILE########
__FILENAME__ = log
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Eitan Isaacson <eitan@ascender.com>
#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009 Eitan Isaacson
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Log routines for LDTP"""

from os import environ as env
import logging

AREA = 'ldtp.client'
ENV_LOG_LEVEL = 'LDTP_LOG_LEVEL'
ENV_LOG_OUT = 'LDTP_LOG_OUT'

log_level = getattr(logging, env.get(ENV_LOG_LEVEL, 'NOTSET'), logging.NOTSET)

logger = logging.getLogger(AREA)

if ENV_LOG_OUT not in env:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(name)-11s %(levelname)-8s %(message)s'))
else:
    handler = logging.FileHandler(env[ENV_LOG_OUT])
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))

logger.addHandler(handler)

logger.setLevel(log_level)

########NEW FILE########
__FILENAME__ = state
# Copyright (c) 2013 Nagappan Alagappan All Rights Reserved.

# This file is part of ATOMac.

#@author: Nagappan Alagappan <nagappan@gmail.com>
#@copyright: Copyright (c) 2009-13 Nagappan Alagappan

#http://ldtp.freedesktop.org

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.
"""Python routines for LDTP"""

ICONIFIED = "iconified"
INVALID = "invalid"
PRESSED = "pressed"
EXPANDABLE = "expandable"
VISIBLE = "visible"
LAST_DEFINED = "last_defined"
BUSY = "busy"
EXPANDED = "expanded"
MANAGES_DESCENDANTS = "manages_descendants"
IS_DEFAULT = "is_default"
INDETERMINATE = "indeterminate"
REQUIRED = "required"
TRANSIENT = "transient"
CHECKED = "checked"
SENSITIVE = "sensitive"
COLLAPSED = "collapsed"
STALE = "stale"
OPAQUE = "opaque"
ENABLED = "enabled"
HAS_TOOLTIP = "has_tooltip"
SUPPORTS_AUTOCOMPLETION = "supports_autocompletion"
FOCUSABLE = "focusable"
SELECTABLE = "selectable"
ACTIVE = "active"
HORIZONTAL = "horizontal"
VISITED = "visited"
INVALID_ENTRY = "invalid_entry"
FOCUSED = "focused"
MODAL = "modal"
VERTICAL = "vertical"
SELECTED = "selected"
SHOWING = "showing"
ANIMATED = "animated"
EDITABLE = "editable"
MULTI_LINE = "multi_line"
SINGLE_LINE = "single_line"
SELECTABLE_TEXT = "selectable_text"
ARMED = "armed"
DEFUNCT = "defunct"
MULTISELECTABLE = "multiselectable"
RESIZABLE = "resizable"
TRUNCATED = "truncated"

########NEW FILE########
__FILENAME__ = Prefs
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Julián Romero.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.

from AppKit import NSWorkspace, NSUserDefaults, NSDictionary, NSMutableDictionary
from UserDict import UserDict
from os import path

__all__ = ["Prefs"]

class Prefs(UserDict):
    ''' NSUserDefaults proxy to read/write application preferences.
        It has been conceived to prepare the preferences before a test launch the app.
        Once a Prefs instance is created, it doesn't detect prefs changed elsewhere,
        so for now you need to create the instance right before reading/writing a pref.
        Defaults.plist with default values is expected to exist on the app bundle.

        p = Prefs('com.example.App')
        coolStuff = p['CoolStuff']
        p['CoolStuff'] = newCoolStuff

    '''
    def __init__(self, bundleID, bundlePath=None, defaultsPlistName='Defaults'):
        ''' bundleId: the application bundle identifier
            bundlePath: the full bundle path (useful to test a Debug build)
            defaultsPlistName: the name of the plist that contains default values
        '''
        self.__bundleID = bundleID
        self.__bundlePath = bundlePath
        UserDict.__init__(self)
        self.__setup(defaultsPlistName)

    def __setup(self, defaultsPlistName=None):
        NSUserDefaults.resetStandardUserDefaults()
        prefs = NSUserDefaults.standardUserDefaults()
        self.defaults = self.__defaults(defaultsPlistName)
        domainData = prefs.persistentDomainForName_(self.__bundleID)
        if domainData:
            self.data = domainData
        else:
            self.data = NSDictionary.dictionary()

    def __defaults(self, plistName='Defaults'):
        if self.__bundlePath is None:
            self.__bundlePath = NSWorkspace.sharedWorkspace().absolutePathForAppBundleWithIdentifier_(self.__bundleID)
        if self.__bundlePath:
            plistPath = path.join(self.__bundlePath, "Contents/Resources/%s.plist" % plistName)
            plist = NSDictionary.dictionaryWithContentsOfFile_(plistPath)
            if plist:
                return plist
        return NSDictionary.dictionary()

    def get(self, key):
        return self.__getitem__(key)

    def __getitem__(self, key):
        result = self.data.get(key, None)
        if result is None or result == '':
            if self.defaults:
                result = self.defaults.get(key, None)
        return result

    def set(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        mutableData = self.data.mutableCopy()
        mutableData[key] = value
        self.data = mutableData
        prefs = NSUserDefaults.standardUserDefaults()
        prefs.setPersistentDomain_forName_(self.data, self.__bundleID)


########NEW FILE########
__FILENAME__ = version
# Copyright (c) 2010 VMware, Inc. All Rights Reserved.

# This file is part of ATOMac.

# ATOMac is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 and no later version.

# ATOMac is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License version 2
# for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA.


__version__ = '1.1.1'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ATOMac documentation build configuration file, created by
# sphinx-quickstart on Wed Jun  1 18:08:59 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
# This should locate the parent directory for atomac
sys.path.insert(0, os.path.abspath('..'))

# Get info about the _a11y extension first
import distutils.command.build
from distutils.dist import Distribution

b = distutils.command.build.build(Distribution())
b.initialize_options()
b.finalize_options()

# Add to sys.path the path to the library build directory
# This will work only if the library has been built from commandline via
# python setup.py build
# TODO: Integrate building the _a11y module before building the docs
sys.path.insert(0, os.path.join(os.path.abspath('..'), b.build_platlib))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
              'sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.viewcode',
             ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ATOMac'
copyright = u'2012, Jesse Mendonca, Ken Song, James Tatum, Andrew Wu'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# Set the __version__ variable
execfile('../atomac/version.py') 
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'ATOMacdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'ATOMac.tex', u'ATOMac Documentation',
   u'Jesse Mendonca, Ken Song, James Tatum, Andrew Wu', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'atomac', u'ATOMac Documentation',
     [u'Jesse Mendonca, Ken Song, James Tatum, Andrew Wu'], 1)
]

########NEW FILE########
