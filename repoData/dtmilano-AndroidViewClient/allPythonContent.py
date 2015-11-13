__FILENAME__ = apidemos-app-alert_dialog-list_dialog-command_three
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Sep 5, 2012

@author: diego
'''


import re
import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient, View

device, serialno = ViewClient.connectToDeviceOrExit()

FLAG_ACTIVITY_NEW_TASK = 0x10000000
#09-06 01:01:34.964: I/ActivityManager(873): START {act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.example.android.apis/.ApiDemos bnds=[784,346][880,442]} from pid 991
componentName = 'com.example.android.apis/.ApiDemos'
device.startActivity(component=componentName, flags=FLAG_ACTIVITY_NEW_TASK)

ViewClient.sleep(3)
vc = ViewClient(device=device, serialno=serialno)
app = vc.findViewWithText('App')
if app:
   app.touch()
   ViewClient.sleep(3)
   # windows changed, request a new dump
   vc.dump()
   ad = vc.findViewWithText('Alert Dialogs')
   if ad:
      ad.touch()
      ViewClient.sleep(3)
      # windows changed, request a new dump
      vc.dump()
      ld = vc.findViewWithText('List dialog')
      if ld:
         ld.touch()
         ViewClient.sleep(3)
         # windows changed, request a new dump
         vc.dump()
         c3 = vc.findViewWithText('Command three')
         if c3:
            c3.touch()
            ViewClient.sleep(10)
            device.press('KEYCODE_BACK')
         else:
            print >> sys.stderr, "Cannot find 'Command three'"
      else:
         print >> sys.stderr, "Cannot find 'List dialog'"
   else:
      print >> sys.stderr, "Cannot find 'Alert Dialogs'"
else:
   print >> sys.stderr, "Cannot find 'App'"


########NEW FILE########
__FILENAME__ = apidemos-preference-advanced_preferences
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Sep 18, 2012

@author: diego
'''


import re
import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

import com.dtmilano.android.viewclient as viewclient
if viewclient.__version__ < '1.0':
    print >> sys.stderr, "%s: This script requires viewclient 1.0 or greater." % os.path.basename(sys.argv[0])
    sys.exit(1)

device, serialno = viewclient.ViewClient.connectToDeviceOrExit()

FLAG_ACTIVITY_NEW_TASK = 0x10000000
#09-06 01:01:34.964: I/ActivityManager(873): START {act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.example.android.apis/.ApiDemos bnds=[784,346][880,442]} from pid 991
componentName = 'com.example.android.apis/.ApiDemos'
device.startActivity(component=componentName, flags=FLAG_ACTIVITY_NEW_TASK)

viewclient.ViewClient.sleep(3)
vc = viewclient.ViewClient(device=device, serialno=serialno)
vc.findViewWithTextOrRaise('Preference').touch()
vc.dump()
vc.findViewWithTextOrRaise(re.compile('.*Advanced preferences')).touch()
vc.dump()
myPreference = vc.findViewWithTextOrRaise('My preference')
if vc.getSdkVersion() >= 16:
    _id = 'id/no_id/22'
else:
    _id = 'id/mypreference_widget'
value0 = vc.findViewByIdOrRaise(_id).getText()
for i in range(10):
    myPreference.touch()
vc.dump()
value1 = vc.findViewByIdOrRaise(_id).getText()
print "My preference started with value %s and is now %s" % (value0, value1)

########NEW FILE########
__FILENAME__ = browser-open-url
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Mar 13, 2012

@author: diego
'''


import re
import sys
import os
import string

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

USE_BROWSER = True
# Starting: Intent { act=android.intent.action.MAIN flg=0x10000000 cmp=com.android.browser/.BrowserActivity }
if USE_BROWSER:
    package = 'com.android.browser'
    activity = '.BrowserActivity'
else:
    package = 'com.android.chrome'
    activity = 'com.google.android.apps.chrome.Main'
component = package + "/" + activity
uri = 'http://dtmilano.blogspot.com'

device, serialno = ViewClient.connectToDeviceOrExit()
device.startActivity(component=component, uri=uri)
ViewClient.sleep(5)

vc = ViewClient(device, serialno)
if vc.getSdkVersion() >= 16:
    if USE_BROWSER:
        url = vc.findViewByIdOrRaise("id/no_id/12").getText()
    else:
        url = vc.findViewWithContentDescription("Search or type url").getText()
else:
    url = vc.findViewByIdOrRaise("id/url").getText()
if string.find(uri, url) != -1:
    print "%s successfully loaded" % uri
else:
    print "%s was not loaded, url=%s" % (uri, url)

########NEW FILE########
__FILENAME__ = browser-view-page-source
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Oct 12, 2012

@author: diego
'''


import re
import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient


VPS = "javascript:alert(document.getElementsByTagName('html')[0].innerHTML);"
USE_BROWSER = True
if USE_BROWSER:
    package = 'com.android.browser'
    activity = '.BrowserActivity'
    _id = 'id/no_id/12'
else:
    package = 'com.android.chrome'
    activity = 'com.google.android.apps.chrome.Main'
    _id = 'id/no_id/28'
component = package + "/" + activity
uri = 'http://dtmilano.blogspot.com'
                   

device, serialno = ViewClient.connectToDeviceOrExit()

device.startActivity(component=component, uri=uri)
ViewClient.sleep(5)

vc = ViewClient(device=device, serialno=serialno)
sdkVersion = vc.getSdkVersion()

if sdkVersion > 10:
    device.drag((240, 180), (240, 420), 1, 20)
else:
    for i in range(10):
        device.press('KEYCODE_DPAD_UP')
        ViewClient.sleep(1)

vc.findViewByIdOrRaise(_id if sdkVersion >= 16 else 'id/url' if sdkVersion > 10 else 'id/title').touch()
ViewClient.sleep(1)

device.press('KEYCODE_DEL')
device.type(VPS)
ViewClient.sleep(1)
device.press('KEYCODE_ENTER')
ViewClient.sleep(3)

vc.dump()
print vc.findViewByIdOrRaise('id/no_id/11' if sdkVersion >= 16 else 'id/message').getText().replace('\\n', "\n")

device.press('KEYCODE_BACK' if sdkVersion > 10 else 'KEYCODE_ENTER')

########NEW FILE########
__FILENAME__ = check-import
#! /usr/bin/env python
'''
Created on Aug 29, 2012

@author: diego
'''

import re
import sys
import os

debug = False
if '--debug' in sys.argv or '-X' in sys.argv:
    debug = True

try:
    if os.environ.has_key('ANDROID_VIEW_CLIENT_HOME'):
        avcd = os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src')
        if os.path.isdir(avcd):
            sys.path.append(avcd)
        else:
            print >>sys.stderr, "WARNING: '%s' is not a directory and is pointed by ANDROID_VIEW_CLIENT_HOME environment variable" % avcd
except:
    pass

if debug:
    print >>sys.stderr, "sys.path=", sys.path
for d in sys.path:
    if d in [ '__classpath__', '__pyclasspath__/']:
        continue
    if not os.path.exists(d):
        if re.search('/Lib$', d):
            if not os.path.exists(re.sub('/Lib$', '', d)):
                print >>sys.stderr, "WARNING: '%s' is in sys.path but doesn't exist" % d
import com
import com.dtmilano
import com.dtmilano.android
import com.dtmilano.android.viewclient
from com.dtmilano.android.viewclient import ViewClient, View
print "OK"

########NEW FILE########
__FILENAME__ = click-button-by-text
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on May 5, 2012

@author: diego
'''

import sys
import os
import time

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

vc = ViewClient(*ViewClient.connectToDeviceOrExit())

for bt in [ 'One', 'Two', 'Three', 'Four', 'Five' ]:
    b = vc.findViewWithText(bt)
    if b:
        (x, y) = b.getXY()
        print >>sys.stderr, "clicking b%s @ (%d,%d) ..." % (bt, x, y)
        b.touch()
    else:
        print >>sys.stderr, "b%s not found" % bt
    time.sleep(7)

print >>sys.stderr, "bye"

########NEW FILE########
__FILENAME__ = click-no-id-button
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Aug 7, 2012

@author: diego
'''

import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient


vc = ViewClient(*ViewClient.connectToDeviceOrExit())

for i in range(1, 9):
    view = vc.findViewById("id/no_id/%d" % i)
    if view:
        print view.__tinyStr__()
        view.touch()

########NEW FILE########
__FILENAME__ = development-settings-show-running-processes
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 3, 2012

@author: diego
'''


import re
import sys
import os


try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

# 01-04 18:23:42.000: I/ActivityManager(4288): Displayed com.android.development/.DevelopmentSettings: +379ms
package = 'com.android.development'
activity = '.DevelopmentSettings'
component = package + "/" + activity
device, serialno = ViewClient.connectToDeviceOrExit()
device.startActivity(component=component)
ViewClient.sleep(5)

vc = ViewClient(device, serialno)

showCpu = vc.findViewWithTextOrRaise("Show CPU usage")
showLoad = vc.findViewWithTextOrRaise("Show running processes")
alwaysFinish = vc.findViewWithTextOrRaise("Immediately destroy activities")

if not showLoad.isChecked():
    print "touching @", showLoad.getCenter()
    showLoad.touch()

if not alwaysFinish.isChecked():
    print "touching @", alwaysFinish.getCenter()
    alwaysFinish.touch()

if not showCpu.isChecked():
    # WARNING: Show CPU usage is de-activated as soon as it's activated, that's why it seems it
    # is never set
    print "touching @", showCpu.getCenter()
    showCpu.touch()

########NEW FILE########
__FILENAME__ = dump-all-windows-lib
#! /usr/bin/env shebang monkeyrunner -plugin $ANDROID_VIEW_CLIENT_HOME/bin/androidviewclient-$ANDROID_VIEW_CLIENT_VERSION.jar @!
#
# Linux:
#! /usr/local/bin/shebang monkeyrunner -plugin $AVC_HOME/bin/androidviewclient-$AVC_VERSION.jar @!
#
# Other:
#! /path/to/monkeyrunner -plugin /path/to/androidviewclient/bin/androidviewclient-2.3.14.jar
#
# No shebang:
# c:>path\to\monkeyrunner -plugin \path\to\androidviewclient-2.3.13.jar dump-all-windows-lib.py

'''
Copyright (C) 2012  Diego Torres Milano
Created on Apr 30, 2013

@author: diego
'''

from com.dtmilano.android.viewclient import ViewClient

kwargs2 = {'autodump': False}
vc = ViewClient(*ViewClient.connectToDeviceOrExit(), **kwargs2)
windows = vc.list()
for wId in windows.keys():
    print ">>> window=", wId, windows[wId]
    vc.dump(window=wId)
    vc.traverse(transform=ViewClient.TRAVERSE_CIT, indent="    ")

########NEW FILE########
__FILENAME__ = dump-all-windows
#! /usr/bin/env python

'''
Copyright (C) 2014  Diego Torres Milano
Created on Apr 24, 2014

@author: diego
'''

from com.dtmilano.android.viewclient import ViewClient

kwargs1 = {'verbose': True, 'ignoresecuredevice': True}
kwargs2 = {'startviewserver': True, 'forceviewserveruse': True, 'autodump': False, 'ignoreuiautomatorkilled': True}
vc = ViewClient(*ViewClient.connectToDeviceOrExit(**kwargs1), **kwargs2)
windows = vc.list()
for wId in windows.keys():
    print ">>> window=", wId, windows[wId]
    vc.dump(window=wId)
    vc.traverse(transform=ViewClient.TRAVERSE_CIT, indent="    ")

########NEW FILE########
__FILENAME__ = dump-simple-lib
#! /usr/bin/env shebang monkeyrunner -plugin $ANDROID_VIEW_CLIENT_HOME/bin/androidviewclient-$ANDROID_VIEW_CLIENT_VERSION.jar @!
#
# Linux:
#! /usr/local/bin/shebang monkeyrunner -plugin $AVC_HOME/bin/androidviewclient-$AVC_VERSION.jar @!
#
# Other:
#! /path/to/monkeyrunner -plugin /path/to/androidviewclient/bin/androidviewclient-2.3.14.jar
#
# No shebang:
# c:>path\to\monkeyrunner -plugin \path\to\androidviewclient-2.3.13.jar dump-simple-lib.py

'''
Copyright (C) 2012  Diego Torres Milano
Created on Apr 30, 2013

@author: diego
'''

from com.dtmilano.android.viewclient import ViewClient

ViewClient(*ViewClient.connectToDeviceOrExit()).traverse(transform=ViewClient.TRAVERSE_CIT)

########NEW FILE########
__FILENAME__ = dump-simple
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Apr 30, 2013

@author: diego
'''


import sys
import os

# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

ViewClient(*ViewClient.connectToDeviceOrExit(verbose=True)).traverse(transform=ViewClient.TRAVERSE_CIT)

########NEW FILE########
__FILENAME__ = dump
#! /usr/bin/env python

print '''
Notice:
-------
'dump.py' was moved to the 'tools' directory and renamed 'dump'.
A simpler example is now in 'dump-simple.py'.

'''

########NEW FILE########
__FILENAME__ = email-send
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Oct 1, 2012

@author: diego
'''


import re
import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient, TextView, EditText

device, serialno = ViewClient.connectToDeviceOrExit()
vc = ViewClient(device=device, serialno=serialno)
#send = vc.findViewWithTextOrRaise('Send')
send = vc.findViewByIdOrRaise('id/send')
#to = EditText(vc.findViewByIdOrRaise('id/to'))
to = vc.findViewByIdOrRaise('id/to')
subject = vc.findViewByIdOrRaise('id/subject')
subject.touch()
subject.type('AVCSample')
ViewClient.sleep(10)
to.touch()
#to.type('androidviewclient@gmail.com')
device.type('androidviewclient@gmail.com')
ViewClient.sleep(10)
send.touch()

########NEW FILE########
__FILENAME__ = gallery-select-album
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 3, 2012

@author: diego
'''


import sys
import os
import re
import time

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass
    
try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import *

package = 'com.android.gallery'
activity = 'com.android.camera.GalleryPicker'
component = package + "/" + activity

device, serialno = ViewClient.connectToDeviceOrExit()
device.startActivity(component=component)
time.sleep(3)
vc = ViewClient(device, serialno)
if vc.build[VERSION_SDK_PROPERTY] != 15:
    print 'This script is intended to run on API-15'
    sys.exit(1)
ALL_PICTURES = 'All pictures'
vc.findViewWithTextOrRaise(re.compile('%s \(\d+\)' % ALL_PICTURES)).touch()
vc.dump()
vc.findViewWithTextOrRaise(ALL_PICTURES)
print "'%s' found" % ALL_PICTURES

########NEW FILE########
__FILENAME__ = list
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Apr 23, 2013

@author: diego
'''


import sys
import os
import getopt

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

HELP = 'help'
VERBOSE = 'verbose'
IGNORE_SECURE_DEVICE = 'ignore-secure-device'
FORCE_VIEW_SERVER_USE = 'force-view-server-use'
DO_NOT_START_VIEW_SERVER = 'do-not-start-view-server'
# -u,-s,-p,-v eaten by monkeyrunner
SHORT_OPTS = 'HVIFS'
LONG_OPTS =  [HELP, VERBOSE, IGNORE_SECURE_DEVICE, FORCE_VIEW_SERVER_USE, DO_NOT_START_VIEW_SERVER]

def usage(exitVal=1):
    print >> sys.stderr, 'usage: list.py [-H|--%s] [-V|--%s] [-I|--%s] [-F|--%s] [-S|--%s] [serialno]' % \
        tuple(LONG_OPTS)
    sys.exit(exitVal)

try:
    opts, args = getopt.getopt(sys.argv[1:], SHORT_OPTS, LONG_OPTS)
except getopt.GetoptError, e:
    print >>sys.stderr, 'ERROR:', str(e)
    usage()

kwargs1 = {VERBOSE: False, 'ignoresecuredevice': False}
kwargs2 = {'forceviewserveruse': False, 'startviewserver': True, 'autodump': False}
for o, a in opts:
    o = o.strip('-')
    if o in ['H', HELP]:
        usage(0)
    elif o in ['V', VERBOSE]:
        kwargs1[VERBOSE] = True
    elif o in ['I', IGNORE_SECURE_DEVICE]:
        kwargs1['ignoresecuredevice'] = True
    elif o in ['F', FORCE_VIEW_SERVER_USE]:
        kwargs2['forceviewserveruse'] = True
    elif o in ['S', DO_NOT_START_VIEW_SERVER]:
        kwargs2['startviewserver'] = False

print ViewClient(*ViewClient.connectToDeviceOrExit(**kwargs1), **kwargs2).list()

########NEW FILE########
__FILENAME__ = monkeyrunner-issue-36544-workaround
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Sep 8, 2012

@author: diego

@see: http://code.google.com/p/android/issues/detail?id=36544
'''


import re
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
       if not p in sys.path:
          sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass
from com.dtmilano.android.viewclient import ViewClient, View


device, serialno = ViewClient.connectToDeviceOrExit()

FLAG_ACTIVITY_NEW_TASK = 0x10000000
# We are not using Settings as the bug describes because there's no WiFi dialog in emulator
#componentName = 'com.android.settings/.Settings'
componentName = 'com.dtmilano.android.sampleui/.MainActivity'
device.startActivity(component=componentName, flags=FLAG_ACTIVITY_NEW_TASK)
ViewClient.sleep(3)

# Set it to True or False to decide if AndroidViewClient or plain monkeyrunner is used
USE_AVC = True

if USE_AVC:
    # AndroidViewClient
    vc = ViewClient(device=device, serialno=serialno)
    showDialogButton = vc.findViewById('id/show_dialog_button')
    if showDialogButton:
        showDialogButton.touch()
        vc.dump()
        vc.findViewById('id/0x123456').type('Donald')
        ok = vc.findViewWithText('OK')
        if ok:
            # 09-08 20:17:47.860: D/MonkeyStub(2033): translateCommand: tap 265 518
            ok.touch()
        vc.dump()
        hello = vc.findViewById('id/hello')
        if hello:
            if hello.getText() == "Hello Donald":
                print "OK"
            else:
                print "FAIL"
        else:
            print >> sys.stderr, "'hello' not found"
    else:
        print >> sys.stderr, "'Show Dialog' button not found"
else:
    # MonkeyRunner
    from com.android.monkeyrunner.easy import EasyMonkeyDevice
    from com.android.monkeyrunner.easy import By
    easyDevice = EasyMonkeyDevice(device)
    showDialogButton = By.id('id/show_dialog_button')
    if showDialogButton:
        easyDevice.touch(showDialogButton, MonkeyDevice.DOWN_AND_UP)
        ViewClient.sleep(3)
        editText = By.id('id/0x123456')
        print editText
        easyDevice.type(editText, 'Donald')
        ViewClient.sleep(3)
        ok = By.id('id/button1')
        if ok:
            # 09-08 20:16:41.119: D/MonkeyStub(1992): translateCommand: tap 348 268
            easyDevice.touch(ok, MonkeyDevice.DOWN_AND_UP)
        hello = By.id('id/hello')
        if hello:
            if easyDevice.getText(hello) == "Hello Donald":
                print "OK"
            else:
                print "FAIL"
        else:
            print >> sys.stderr, "'hello' not found"


########NEW FILE########
__FILENAME__ = sample-ui-dialog_activity-button
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Aug 31, 2012

@author: diego
'''


import re
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
       if not p in sys.path:
          sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass
from com.dtmilano.android.viewclient import ViewClient, View


vc = ViewClient(*ViewClient.connectToDeviceOrExit())

button = vc.findViewWithTextOrRaise('Show Dialog')
print "button: ", button.getClass(), button.getId(), button.getCoords()


########NEW FILE########
__FILENAME__ = sample-ui-toggle-buttons
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Aug 31, 2012

@author: diego
'''


import re
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
       if not p in sys.path:
          sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass
from com.dtmilano.android.viewclient import ViewClient, ViewNotFoundException

vc = ViewClient(*ViewClient.connectToDeviceOrExit())
if vc.useUiAutomator:
    print "ViewClient: using UiAutomator backend"

# Find the 3 toggle buttons, because the first 2 change their text if they are selected
# we use a regex to find them.
# Once found, we touch them changing their state
for t in [re.compile('Button 1 .*'), re.compile('Button 2 .*'), 'Button with ID']:
    try:
        vc.findViewWithTextOrRaise(t).touch()
    except ViewNotFoundException:
        print >>sys.stderr, "Couldn't find button with text=", t


########NEW FILE########
__FILENAME__ = screenshot-monkeyrunner
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Set 5, 2013

@author: diego
'''


import sys
import os


if len(sys.argv) < 2:
    print >> sys.stderr, "usage: %s filename.png" % sys.argv[0]
    sys.exit(1)

filename = sys.argv.pop(1)
device = MonkeyRunner.waitForConnection()
device.takeSnapshot().writeToFile(filename, 'PNG')

########NEW FILE########
__FILENAME__ = screenshot
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Aug 31, 2013

@author: diego
'''


import sys
import os

from com.dtmilano.android.viewclient import ViewClient

if len(sys.argv) < 2:
    sys.exit("usage: %s filename.png [serialno]" % sys.argv[0])

filename = sys.argv.pop(1)
device, serialno = ViewClient.connectToDeviceOrExit(verbose=False)
device.takeSnapshot().save(filename, 'PNG')

########NEW FILE########
__FILENAME__ = settings-display
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Aug 15, 2012

@author: diego
'''


import re
import sys
import os

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient, View


START_ACTIVITY = True
FLAG_ACTIVITY_NEW_TASK = 0x10000000

package='com.android.settings'
activity='.Settings'
component=package + "/" + activity

device, serialno = ViewClient.connectToDeviceOrExit()

if START_ACTIVITY:
    device.startActivity(component=component, flags=FLAG_ACTIVITY_NEW_TASK)
    ViewClient.sleep(3)

vc = ViewClient(device, serialno)

# this may help you find the attributes for specific Views
#vc.traverse(vc.getRoot())
text = 'Display'
view = vc.findViewWithText(text)
if view:
	print view.__smallStr__()
	print view.getCoords()
	print view.getX(), ',', view.getY()
else:
	print "View with text='%s' was not found" % text

########NEW FILE########
__FILENAME__ = settings-sound-phone_ringtone
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Sep 8, 2012

@author: diego

@see: http://code.google.com/p/android/issues/detail?id=36544
'''


import re
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
       if not p in sys.path:
          sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass
from com.dtmilano.android.viewclient import ViewClient, View


device, serialno = ViewClient.connectToDeviceOrExit()

DEBUG = True
FLAG_ACTIVITY_NEW_TASK = 0x10000000
# We are not using Settings as the bug describes because there's no WiFi dialog in emulator
componentName = 'com.android.settings/.Settings'
device.startActivity(component=componentName, flags=FLAG_ACTIVITY_NEW_TASK)
ViewClient.sleep(3)

vc = ViewClient(device=device, serialno=serialno)
if DEBUG: vc.traverse(transform=ViewClient.TRAVERSE_CIT)
sound = vc.findViewWithText('Sound')
if sound:
    sound.touch()
    vc.dump()
    phoneRingtone = vc.findViewWithText('Phone ringtone')
    if phoneRingtone:
        phoneRingtone.touch()
        vc.dump()
        vespa = vc.findViewWithText('Vespa')
        if vespa:
            vespa.touch()
        ViewClient.sleep(1)
        ok = vc.findViewById('id/button1')
        if ok:
            ok.touch()
            vc.dump()
            vespa = vc.findViewWithText('Vespa')
            # If for some reason the dialog is still there we will have Vespa and OK
            ok = vc.findViewById('id/button1')
            if vespa and not ok:
                print "OK"
            else:
                print "FAIL to set ringtone Vespa"
                sys.exit(1)
        else:
            print >> sys.stderr, "'OK' not found"
    else:
        print >> sys.stderr, "'Phone ringtone' not found"
else:
    print >> sys.stderr, "'Sound' not found"

########NEW FILE########
__FILENAME__ = settings
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 1, 2012

@author: diego
'''


import re
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

package='com.android.settings'
activity='.Settings'
component=package + "/" + activity
device, serialno = ViewClient.connectToDeviceOrExit()

if True:
    device.startActivity(component=component)
    ViewClient.sleep(3)
    device.press('KEYCODE_DPAD_DOWN') # extra VMT setting WARNING!
    ViewClient.sleep(1)
    device.press('KEYCODE_DPAD_CENTER', MonkeyDevice.DOWN_AND_UP)
    device.press('KEYCODE_DPAD_DOWN', MonkeyDevice.DOWN_AND_UP)
    #device.press('KEYCODE_DPAD_DOWN', MonkeyDevice.DOWN_AND_UP)
    #device.press('KEYCODE_DPAD_DOWN', MonkeyDevice.DOWN_AND_UP)
    #device.press('KEYCODE_DPAD_CENTER', "DOWN_AND_UP")
    #device.press('KEYCODE_DPAD_CENTER', "DOWN_AND_UP")

vc = ViewClient(device, serialno)
regex = "id/checkbox.*"
p = re.compile(regex)
found = False
for id in vc.getViewIds():
    #print id
    m = p.match(id)
    if m:
        found = True
        attrs =  vc.findViewById(id)
        if attrs['isSelected()'] == 'true':
            print "Wi-Fi is",
            if attrs['isChecked()'] != 'true':
                print "not",
            print "set"

if not found:
    print "No Views found that match " + regex

########NEW FILE########
__FILENAME__ = temperature-converter-get-conversion
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 3, 2012

This example starts the TemperatureConverter activity then type '123' into the 'Celsius' field.
Then a ViewClient is created to obtain the view dump and the current values of the views with
id/celsius and id/fahrenheit are obtained and the conversion printed to stdout.
Finally, the fields are obtained by using their tags and again, conversion printed to stdout.

If --localViewServer is passed in the command line then LocalViewServer provided by
TemperatureConverter is used. This is very useful when the device is secure and ViewServer
cannot be started.

@author: diego
'''


import re
import sys
import os
import time

# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

localViewServer = False
if len(sys.argv) > 1 and sys.argv[1] == '--localViewServer':
    localViewServer = True
    sys.argv.pop(1)

device, serialno = ViewClient.connectToDeviceOrExit(ignoresecuredevice=localViewServer)

FLAG_ACTIVITY_NEW_TASK = 0x10000000
package = 'com.example.i2at.tc'
activity = '.TemperatureConverterActivity'
componentName = package + "/" + activity

device.startActivity(component=componentName, flags=FLAG_ACTIVITY_NEW_TASK)
time.sleep(5)


device.type("123")
time.sleep(3)

vc = ViewClient(device, serialno, startviewserver=(not localViewServer))

if vc.build['ro.build.version.sdk'] >= 16:
    # obtain the views by contentDescription
    celsius = vc.findViewWithContentDescriptionOrRaise("celsius")
    fahrenheit = vc.findViewWithContentDescriptionOrRaise("fahrenheit")
else:
    # obtain the views by id
    celsius = vc.findViewByIdOrRaise("id/celsius")
    fahrenheit = vc.findViewByIdOrRaise("id/fahrenheit")

ct = celsius.getText()
if ct:
   c = float(ct)
else:
   print >> sys.stderr, "Celsius is empty"
   sys.exit(1)
ft = fahrenheit.getText()
if ft:
   f = float(ft)
else:
   print >> sys.stderr, "Fahrenheit is empty"
   sys.exit(1)
print "by id: %.2f C => %.2f F" % (c, f)

# obtain the views by tag
#celsius = vc.findViewByTagOrRaise("celsius")
#fahrenheit = vc.findViewByTagOrRaise("fahrenheit")
#
#c = float(celsius.getText())
#f = float(fahrenheit.getText())
#print "by tag: %.2f C => %.2f F" % (c, f)

########NEW FILE########
__FILENAME__ = test-connect-to-device
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Oct 15, 2012

@author: diego
'''


import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

ViewClient.connectToDeviceOrExit(verbose=True)

########NEW FILE########
__FILENAME__ = trashcan-fullscreenactivity-touches
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Mar 13, 2012

@author: diego
'''


import re
import sys
import os
import string

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

package = 'com.example.trashcan'
activity = '.FullScreenActivity'
component = package + "/" + activity

device, serialno = ViewClient.connectToDeviceOrExit()
#device.startActivity(component=component)
#ViewClient.sleep(3)

vc = ViewClient(device, serialno)
button = vc.findViewWithTextOrRaise('Button')
button.touch()
toggle = vc.findViewWithTextOrRaise(re.compile('(ON)|(OFF)'))
toggle.touch()

########NEW FILE########
__FILENAME__ = viewserveractivity-new-activity
#! /usr/bin/env python
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 3, 2012

@author: diego
'''


import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import ViewClient

device, serialno = ViewClient.connectToDeviceOrExit(ignoresecuredevice=True)
vc = ViewClient(device=device, serialno=serialno, startviewserver=False)
vc.findViewWithTextOrRaise("New activity").touch()

########NEW FILE########
__FILENAME__ = write-image-to-file
#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2013  Diego Torres Milano
Created on 2014-03-10 by Culebra v4.10.1

                      __    __    __    __
                     /  \  /  \  /  \  /  \ 
____________________/  __\/  __\/  __\/  __\_____________________________
___________________/  /__/  /__/  /__/  /________________________________
                   | / \   / \   / \   / \   \___
                   |/   \_/   \_/   \_/   \    o \ 
                                           \_____/--<
@author: Diego Torres Milano
@author: Jennifer E. Swofford (ascii art snake)
'''


import re
import sys
import os


from com.dtmilano.android.viewclient import ViewClient

if len(sys.argv) < 2:
    sys.exit("usage: %s /path/to/filename.png [serialno]" % sys.argv[0])

filename = sys.argv.pop(1)
kwargs1 = {'verbose': False, 'ignoresecuredevice': False}
device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
kwargs2 = {'startviewserver': True, 'forceviewserveruse': False, 'autodump': False, 'ignoreuiautomatorkilled': True}
vc = ViewClient(device, serialno, **kwargs2)
vc.dump(window='-1')

vc.findViewWithContentDescriptionOrRaise('''Home screen 3''').writeImageToFile(filename, 'PNG')

########NEW FILE########
__FILENAME__ = adbclient
'''
Copyright (C) 2012-2013  Diego Torres Milano
Created on Dec 1, 2012

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Diego Torres Milano
'''

__version__ = '7.0.2'

import sys
import warnings
if sys.executable:
    if 'monkeyrunner' in sys.executable:
        warnings.warn(
    '''

    You should use a 'python' interpreter, not 'monkeyrunner' for this module

    ''', RuntimeWarning)
import socket
import time
import re
import signal
import os
import types
import platform

DEBUG = False

HOSTNAME = 'localhost'
try:
    PORT = int(os.environ['ANDROID_ADB_SERVER_PORT'])
except KeyError:
    PORT = 5037

OKAY = 'OKAY'
FAIL = 'FAIL'

UP = 0
DOWN = 1
DOWN_AND_UP = 2

TIMEOUT = 15

# some device properties
VERSION_SDK_PROPERTY = 'ro.build.version.sdk'
VERSION_RELEASE_PROPERTY = 'ro.build.version.release'


class Device:
    @staticmethod
    def factory(_str):
        if DEBUG:
            print >> sys.stderr, "Device.factory(", _str, ")"
        values = _str.split(None, 2)
        if DEBUG:
            print >> sys.stderr, "values=", values
        return Device(*values)

    def __init__(self, serialno, status, qualifiers=None):
        self.serialno = serialno
        self.status = status
        self.qualifiers = qualifiers

    def __str__(self):
        return "<<<" + self.serialno + ", " + self.status + ", %s>>>" % self.qualifiers


class AdbClient:

    def __init__(self, serialno=None, hostname=HOSTNAME, port=PORT, settransport=True, reconnect=True):
        self.serialno = serialno
        self.hostname = hostname
        self.port = port

        self.reconnect = reconnect
        self.__connect()

        self.checkVersion()

        self.build = {}
        ''' Build properties '''

        self.isTransportSet = False
        if settransport and serialno != None:
            self.__setTransport()
            self.build[VERSION_SDK_PROPERTY] = self.__getProp(VERSION_SDK_PROPERTY)


    @staticmethod
    def setAlarm(timeout):
        osName = platform.system()
        if osName.startswith('Windows'):  # alarm is not implemented in Windows
            return
        if DEBUG:
            print >> sys.stderr, "setAlarm(%d)" % timeout
        signal.alarm(timeout)

    def setSerialno(self, serialno):
        if self.isTransportSet:
            raise ValueError("Transport is already set, serialno cannot be set once this is done.")
        self.serialno = serialno
        self.__setTransport()
        self.build[VERSION_SDK_PROPERTY] = self.__getProp(VERSION_SDK_PROPERTY)
        
    def setReconnect(self, val):
        self.reconnect = val

    def __connect(self):
        if DEBUG:
            print >> sys.stderr, "__connect()"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TIMEOUT)
        try:
            self.socket.connect((self.hostname, self.port))
        except socket.error, ex:
            raise RuntimeError("ERROR: Connecting to %s:%d: %s.\nIs adb running on your computer?" % (self.socket, self.port, ex))

    def close(self):
        if DEBUG:
            print >> sys.stderr, "Closing socket...", self.socket
        if self.socket:
            self.socket.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def __send(self, msg, checkok=True, reconnect=False):
        if DEBUG:
            print >> sys.stderr, "__send(%s, checkok=%s, reconnect=%s)" % (msg, checkok, reconnect)
        if not re.search('^host:', msg):
            if not self.isTransportSet:
                self.__setTransport()
        else:
            self.checkConnected()
        b = bytearray(msg, 'utf-8')
        self.socket.send('%04X%s' % (len(b), b))
        if checkok:
            self.__checkOk()
        if reconnect:
            if DEBUG:
                print >> sys.stderr, "    __send: reconnecting"
            self.__connect()
            self.__setTransport()

    def __receive(self, nob=None):
        if DEBUG:
            print >> sys.stderr, "__receive()"
        self.checkConnected()
        if nob is None:
            nob = int(self.socket.recv(4), 16)
        if DEBUG:
            print >> sys.stderr, "    __receive: receiving", nob, "bytes"
        recv = bytearray()
        nr = 0
        while nr < nob:
            chunk = self.socket.recv(min((nob - nr), 4096))
            recv.extend(chunk)
            nr += len(chunk)
        if DEBUG:
            print >> sys.stderr, "    __receive: returning len=", len(recv)
        return str(recv)

    def __checkOk(self):
        if DEBUG:
            print >> sys.stderr, "__checkOk()"
        self.checkConnected()
        self.setAlarm(TIMEOUT)
        recv = self.socket.recv(4)
        if DEBUG:
            print >> sys.stderr, "    __checkOk: recv=", repr(recv)
        try:
            if recv != OKAY:
                error = self.socket.recv(1024)
                raise RuntimeError("ERROR: %s %s" % (repr(recv), error))
        finally:
            self.setAlarm(0)
        if DEBUG:
            print >> sys.stderr, "    __checkOk: returning True"
        return True

    def checkConnected(self):
        if DEBUG:
            print >> sys.stderr, "checkConnected()"
        if not self.socket:
            raise RuntimeError("ERROR: Not connected")
        if DEBUG:
            print >> sys.stderr, "    checkConnected: returning True"
        return True

    def checkVersion(self, reconnect=True):
        if DEBUG:
            print >> sys.stderr, "checkVersion(reconnect=%s)" % reconnect
        self.__send('host:version', reconnect=False)
        version = self.socket.recv(8)
        VERSION = '0004001f'
        if version != VERSION:
            raise RuntimeError("ERROR: Incorrect ADB server version %s (expecting %s)" % (version, VERSION))
        if reconnect:
            self.__connect()

    def __setTransport(self):
        if DEBUG:
            print >> sys.stderr, "__setTransport()"
        if not self.serialno:
            raise ValueError("serialno not set, empty or None")
        self.checkConnected()
        serialnoRE = re.compile(self.serialno)
        found = False
        for device in self.getDevices():
            if serialnoRE.match(device.serialno):
                found = True
                break
        if not found:
            raise RuntimeError("ERROR: couldn't find device that matches '%s'" % self.serialno)
        self.serialno = device.serialno
        msg = 'host:transport:%s' % self.serialno
        if DEBUG:
            print >> sys.stderr, "    __setTransport: msg=", msg
        self.__send(msg, reconnect=False)
        self.isTransportSet = True

    def getDevices(self):
        if DEBUG:
            print >> sys.stderr, "getDevices()"
        self.__send('host:devices-l', checkok=False)
        try:
            self.__checkOk()
        except RuntimeError, ex:
            print >> sys.stderr, "**ERROR:", ex
            return None
        devices = []
        for line in self.__receive().splitlines():
            devices.append(Device.factory(line))
        self.__connect()
        return devices

    def shell(self, cmd=None):
        if DEBUG:
            print >> sys.stderr, "shell(cmd=%s)" % cmd
        if cmd:
            self.__send('shell:%s' % cmd, checkok=True, reconnect=False)
            out = ''
            while True:
                _str = None
                try:
                    _str = self.socket.recv(4096)
                except Exception, ex:
                    print >> sys.stderr, "ERROR:", ex
                if not _str:
                    break
                out += _str
            if self.reconnect:
                if DEBUG:
                    print >> sys.stderr, "Reconnecting..."
                self.close()
                self.__connect()
                self.__setTransport()
            return out
        else:
            self.__send('shell:')
            # sin = self.socket.makefile("rw")
            # sout = self.socket.makefile("r")
            # return (sin, sin)
            sout = adbClient.socket.makefile("r")
            return sout

    def getRestrictedScreen(self):
        ''' Gets C{mRestrictedScreen} values from dumpsys. This is a method to obtain display dimensions '''

        rsRE = re.compile('\s*mRestrictedScreen=\((?P<x>\d+),(?P<y>\d+)\) (?P<w>\d+)x(?P<h>\d+)')
        for line in self.shell('dumpsys window').splitlines():
            m = rsRE.match(line)
            if m:
                return m.groups()
        raise RuntimeError("Couldn't find mRestrictedScreen in dumpsys")

    def __getProp(self, key, strip=True):
        prop = self.shell('getprop %s' % key)
        if strip:
            prop = prop.rstrip('\r\n')
        return prop

    def __getDisplayWidth(self, key, strip=True):
        (x, y, w, h) = self.getRestrictedScreen()
        return int(w)

    def __getDisplayHeight(self, key, strip=True):
        (x, y, w, h) = self.getRestrictedScreen()
        return int(h)

    def getSystemProperty(self, key, strip=True):
        return self.getProperty(key, strip)

    def getProperty(self, key, strip=True):
        ''' Gets the property value for key '''

        import collections
        MAP_KEYS = collections.OrderedDict([
                          (re.compile('display.width'), self.__getDisplayWidth),
                          (re.compile('display.height'), self.__getDisplayHeight),
                          (re.compile('.*'), self.__getProp),
                          ])
        '''Maps properties key values (as regexps) to instance methods to obtain its values.'''

        for kre in MAP_KEYS.keys():
            if kre.match(key):
                return MAP_KEYS[kre](key=key, strip=strip)
        raise ValueError("key='%s' does not match any map entry")

    def getSdkVersion(self):
        '''
        Gets the SDK version.
        '''

        return self.build[VERSION_SDK_PROPERTY]

    def press(self, name, eventType=DOWN_AND_UP):
        cmd = 'input keyevent %s' % name
        if DEBUG:
            print >> sys.stderr, "press(%s)" % cmd
        self.shell(cmd)

    def longPress(self, name):
        # WORKAROUND:
        # Using 'input keyevent --longpress POWER' does not work correctly in
        # KitKat (API 19), it sends a short instead of a long press.
        # This uses the events instead, but it may vary from device to device.
        # The events sent are device dependent and may not work on other devices.
        # If this does not work on your device please do:
        #     $ adb shell getevent -l
        # and post the output to https://github.com/dtmilano/AndroidViewClient/issues
        # specifying the device and API level.
        if name == 'POWER' or name == 'KEY_POWER':
            self.shell('sendevent /dev/input/event0 1 116 1')
            self.shell('sendevent /dev/input/event0 0 0 0')
            time.sleep(0.5)
            self.shell('sendevent /dev/input/event0 1 116 0')
            self.shell('sendevent /dev/input/event0 0 0 0')
            return

        version = self.getSdkVersion()
        if version >= 19:
            cmd = 'input keyevent --longpress %s' % name
            if DEBUG:
                print >> sys.stderr, "longPress(%s)" % cmd
            self.shell(cmd)
        else:
            raise RuntimeError("longpress: not supported for API < 19 (version=%d)" % version)

    def startActivity(self, component=None, flags=None, uri=None):
        cmd = 'am start'
        if component:
            cmd += ' -n %s' % component
        if flags:
            cmd += ' -f %s' % flags
        if uri:
            cmd += ' %s' % uri
        if DEBUG:
            print >> sys.stderr, "Starting activity: %s" % cmd
        out = self.shell(cmd)
        if re.search(r"(Error type)|(Error: )|(Cannot find 'App')", out, re.IGNORECASE | re.MULTILINE):
            raise RuntimeError(out)

    def takeSnapshot(self, reconnect=False):
        '''
        Takes a snapshot of the device and return it as a PIL Image.
        '''

        try:
            from PIL import Image
        except:
            raise Exception("You have to install PIL to use takeSnapshot()")
        self.__send('framebuffer:', checkok=True, reconnect=False)
        import struct
        # case 1: // version
        #           return 12; // bpp, size, width, height, 4*(length, offset)
        received = self.__receive(1 * 4 + 12 * 4)
        (version, bpp, size, width, height, roffset, rlen, boffset, blen, goffset, glen, aoffset, alen) = struct.unpack('<' + 'L' * 13, received)
        if DEBUG:
            print >> sys.stderr, "    takeSnapshot:", (version, bpp, size, width, height, roffset, rlen, boffset, blen, goffset, glen, aoffset, alen)
        offsets = {roffset:'R', goffset:'G', boffset:'B'}
        if bpp == 32:
            if alen != 0:
                offsets[aoffset] = 'A'
            else:
                warnings.warn('''framebuffer is specified as 32bpp but alpha length is 0''')
        argMode = ''.join([offsets[o] for o in sorted(offsets)])
        if DEBUG:
            print >> sys.stderr, "    takeSnapshot:", (version, bpp, size, width, height, roffset, rlen, boffset, blen, goffset, blen, aoffset, alen, argMode)
        if argMode == 'BGRA':
            argMode = 'RGBA'
        if bpp == 16:
            mode = 'RGB'
            argMode += ';16'
        else:
            mode = argMode
        self.__send('\0', checkok=False, reconnect=False)
        if DEBUG:
            print >> sys.stderr, "    takeSnapshot: reading %d bytes" % (size)
        received = self.__receive(size)
        if reconnect:
            self.__connect()
            self.__setTransport()
        if DEBUG:
            print >> sys.stderr, "    takeSnapshot: Image.frombuffer(%s, %s, %s, %s, %s, %s, %s)" % (mode, (width, height), 'data', 'raw', argMode, 0, 1)
        return Image.frombuffer(mode, (width, height), received, 'raw', argMode, 0, 1)

    def touch(self, x, y, eventType=DOWN_AND_UP):
        self.shell('input tap %d %d' % (x, y))

    def drag(self, (x0, y0), (x1, y1), duration, steps=1):
        '''
        Sends drag event (actually it's using C{input swipe} command.

        @param (x0, y0): starting point
        @param (x1, y1): ending point
        @param duration: duration of the event in ms
        @param steps: number of steps (currently ignored by @{input swipe}
        '''

        version = self.getSdkVersion()
        if version <= 15:
            raise RuntimeError('drag: API <= 15 not supported (version=%d)' % version)
        elif version <= 17:
            self.shell('input swipe %d %d %d %d' % (x0, y0, x1, y1))
        else:
            self.shell('input touchscreen swipe %d %d %d %d %d' % (x0, y0, x1, y1, duration))

    def type(self, text):
        self.shell(u'input text "%s"' % text)

    def wake(self):
        if not self.isScreenOn():
            self.shell('input keyevent POWER')

    def isLocked(self):
        '''
        Checks if the device screen is locked.

        @return True if the device screen is locked
        '''

        lockScreenRE = re.compile('mShowingLockscreen=(true|false)')
        m = lockScreenRE.search(self.shell('dumpsys window policy'))
        if m:
            return (m.group(1) == 'true')
        raise RuntimeError("Couldn't determine screen lock state")

    def isScreenOn(self):
        '''
        Checks if the screen is ON.

        @return True if the device screen is ON
        '''

        screenOnRE = re.compile('mScreenOnFully=(true|false)')
        m = screenOnRE.search(self.shell('dumpsys window policy'))
        if m:
            return (m.group(1) == 'true')
        raise RuntimeError("Couldn't determine screen ON state")
        
    def unlock(self):
        '''
        Unlocks the screen of the device.
        '''

        self.shell('input keyevent MENU')
        self.shell('input keyevent BACK')

    @staticmethod
    def percentSame(image1, image2):
        '''
        Returns the percent of pixels that are equal

        @author: catshoes
        '''

        # If the images differ in size, return 0% same.
        size_x1, size_y1 = image1.size
        size_x2, size_y2 = image2.size
        if (size_x1 != size_x2 or
            size_y1 != size_y2):
            return 0

        # Images are the same size
        # Return the percent of pixels that are equal.
        numPixelsSame = 0
        numPixelsTotal = size_x1 * size_y1
        image1Pixels = image1.load()
        image2Pixels = image2.load()

        # Loop over all pixels, comparing pixel in image1 to image2
        for x in range(size_x1):
            for y in range(size_y1):
                if (image1Pixels[x, y] == image2Pixels[x, y]):
                    numPixelsSame += 1

        return numPixelsSame / float(numPixelsTotal)

    @staticmethod
    def sameAs(image1, image2, percent=1.0):
        '''
        Compares 2 images

        @author: catshoes
        '''

        return (AdbClient.percentSame(image1, image2) >= percent)


if __name__ == '__main__':
    adbClient = AdbClient(os.environ['ANDROID_SERIAL'])
    INTERACTIVE = False
    if INTERACTIVE:
        sout = adbClient.shell()
        prompt = re.compile(".+@android:(.*) [$#] \r\r\n")
        while True:
            try:
                cmd = raw_input('adb $ ')
            except EOFError:
                break
            if cmd == 'exit':
                break
            adbClient.socket.__send(cmd + "\r\n")
            sout.readline(4096)  # eat first line, which is the command
            while True:
                line = sout.readline(4096)
                if prompt.match(line):
                    break
                print line,
                if not line:
                    break

        print "\nBye"
    else:
        print 'date:', adbClient.shell('date')

########NEW FILE########
__FILENAME__ = viewclient
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2014  Diego Torres Milano
Created on Feb 2, 2012

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Diego Torres Milano
'''

__version__ = '5.6.3'

import sys
import warnings
if sys.executable:
    if 'monkeyrunner' in sys.executable:
        warnings.warn(
    '''

    You should use a 'python' interpreter, not 'monkeyrunner' for this module

    ''', RuntimeWarning)
import subprocess
import re
import socket
import os
import types
import time
import signal
import copy
import pickle
import platform
import xml.parsers.expat
from com.dtmilano.android.adb import adbclient

DEBUG = False
DEBUG_DEVICE = DEBUG and False
DEBUG_RECEIVED = DEBUG and False
DEBUG_TREE = DEBUG and False
DEBUG_GETATTR = DEBUG and False
DEBUG_CALL = DEBUG and False
DEBUG_COORDS = DEBUG and False
DEBUG_TOUCH = DEBUG and False
DEBUG_STATUSBAR = DEBUG and False
DEBUG_WINDOWS = DEBUG and False
DEBUG_BOUNDS = DEBUG and False
DEBUG_DISTANCE = DEBUG and False

WARNINGS = False

VIEW_SERVER_HOST = 'localhost'
VIEW_SERVER_PORT = 4939

ADB_DEFAULT_PORT = 5555

OFFSET = 25
''' This assumes the smallest touchable view on the screen is approximately 50px x 50px
    and touches it at M{(x+OFFSET, y+OFFSET)} '''

USE_ADB_CLIENT_TO_GET_BUILD_PROPERTIES = True
''' Use C{AdbClient} to obtain the needed properties. If this is
    C{False} then C{adb shell getprop} is used '''

SKIP_CERTAIN_CLASSES_IN_GET_XY_ENABLED = False
''' Skips some classes related with the Action Bar and the PhoneWindow$DecorView in the
    coordinates calculation
    @see: L{View.getXY()} '''

VIEW_CLIENT_TOUCH_WORKAROUND_ENABLED = False
''' Under some conditions the touch event should be longer [t(DOWN) << t(UP)]. C{True} enables a
    workaround to delay the events.'''

# some device properties
VERSION_SDK_PROPERTY = 'ro.build.version.sdk'
VERSION_RELEASE_PROPERTY = 'ro.build.version.release'

# some constants for the attributes
ID_PROPERTY = 'mID'
ID_PROPERTY_UI_AUTOMATOR = 'uniqueId'
TEXT_PROPERTY = 'text:mText'
TEXT_PROPERTY_API_10 = 'mText'
TEXT_PROPERTY_UI_AUTOMATOR = 'text'
WS = "\xfe" # the whitespace replacement char for TEXT_PROPERTY
LEFT_PROPERTY = 'layout:mLeft'
LEFT_PROPERTY_API_8 = 'mLeft'
TOP_PROPERTY = 'layout:mTop'
TOP_PROPERTY_API_8 = 'mTop'
WIDTH_PROPERTY = 'layout:getWidth()'
WIDTH_PROPERTY_API_8 = 'getWidth()'
HEIGHT_PROPERTY = 'layout:getHeight()'
HEIGHT_PROPERTY_API_8 = 'getHeight()'
GET_VISIBILITY_PROPERTY = 'getVisibility()'
LAYOUT_TOP_MARGIN_PROPERTY = 'layout:layout_topMargin'

# visibility
VISIBLE = 0x0
INVISIBLE = 0x4
GONE = 0x8

RegexType = type(re.compile(''))
IP_RE = re.compile('^(\d{1,3}\.){3}\d{1,3}$')
ID_RE = re.compile('id/([^/]*)(/(\d+))?')

def _nd(name):
    '''
    @return: Returns a named decimal regex
    '''
    return '(?P<%s>\d+)' % name

def _nh(name):
    '''
    @return: Returns a named hex regex
    '''
    return '(?P<%s>[0-9a-f]+)' % name

def _ns(name, greedy=False):
    '''
    NOTICE: this is using a non-greedy (or minimal) regex

    @type name: str
    @param name: the name used to tag the expression
    @type greedy: bool
    @param greedy: Whether the regex is greedy or not

    @return: Returns a named string regex (only non-whitespace characters allowed)
    '''
    return '(?P<%s>\S+%s)' % (name, '' if greedy else '?')


class Window:
    '''
    Window class
    '''

    def __init__(self, num, winId, activity, wvx, wvy, wvw, wvh, px, py, visibility):
        '''
        Constructor

        @type num: int
        @param num: Ordering number in Window Manager
        @type winId: str
        @param winId: the window ID
        @type activity: str
        @param activity: the activity (or sometimes other component) owning the window
        @type wvx: int
        @param wvx: window's virtual X
        @type wvy: int
        @param wvy: window's virtual Y
        @type wvw: int
        @param wvw: window's virtual width
        @type wvh: int
        @param wvh: window's virtual height
        @type px: int
        @param px: parent's X
        @type py: int
        @param py: parent's Y
        @type visibility: int
        @param visibility: visibility of the window
        '''

        if DEBUG_COORDS: print >> sys.stderr, "Window(%d, %s, %s, %d, %d, %d, %d, %d, %d, %d)" % \
                (num, winId, activity, wvx, wvy, wvw, wvh, px, py, visibility)
        self.num = num
        self.winId = winId
        self.activity = activity
        self.wvx = wvx
        self.wvy = wvy
        self.wvw = wvw
        self.wvh = wvh
        self.px = px
        self.py = py
        self.visibility = visibility

    def __str__(self):
        return "Window(%d, wid=%s, a=%s, x=%d, y=%d, w=%d, h=%d, px=%d, py=%d, v=%d)" % \
                (self.num, self.winId, self.activity, self.wvx, self.wvy, self.wvw, self.wvh, self.px, self.py, self.visibility)


class ViewNotFoundException(Exception):
    '''
    ViewNotFoundException is raised when a View is not found.
    '''

    def __init__(self, attr, value, root):
        if isinstance(value, RegexType):
            msg = "Couldn't find View with %s that matches '%s' in tree with root=%s" % (attr, value.pattern, root)
        else:
            msg = "Couldn't find View with %s='%s' in tree with root=%s" % (attr, value, root)
        super(Exception, self).__init__(msg)

class View:
    '''
    View class
    '''

    @staticmethod
    def factory(arg1, arg2, version=-1, forceviewserveruse=False):
        '''
        View factory

        @type arg1: ClassType or dict
        @type arg2: View instance or AdbClient
        '''

        if type(arg1) == types.ClassType:
            cls = arg1
            attrs = None
        else:
            cls = None
            attrs = arg1
        if isinstance(arg2, View):
            view = arg2
            device = None
        else:
            device = arg2
            view = None

        if attrs and attrs.has_key('class'):
            clazz = attrs['class']
            if clazz == 'android.widget.TextView':
                return TextView(attrs, device, version, forceviewserveruse)
            elif clazz == 'android.widget.EditText':
                return EditText(attrs, device, version, forceviewserveruse)
            else:
                return View(attrs, device, version, forceviewserveruse)
        elif cls:
            if view:
                return cls.__copy(view)
            else:
                return cls(attrs, device, version, forceviewserveruse)
        elif view:
            return copy.copy(view)
        else:
            return View(attrs, device, version, forceviewserveruse)

    @classmethod
    def __copy(cls, view):
        '''
        Copy constructor
        '''

        return cls(view.map, view.device, view.version, view.forceviewserveruse)

    def __init__(self, map, device, version=-1, forceviewserveruse=False):
        '''
        Constructor

        @type map: map
        @param map: the map containing the (attribute, value) pairs
        @type device: MonkeyDevice
        @param device: the device containing this View
        @type version: int
        @param version: the Android SDK version number of the platform where this View belongs. If
                        this is C{-1} then the Android SDK version will be obtained in this
                        constructor.
        @type forceviewserveruse: boolean
        @param forceviewserveruse: Force the use of C{ViewServer} even if the conditions were given
                        to use C{UiAutomator}.
        '''

        self.map = map
        ''' The map that contains the C{attr},C{value} pairs '''
        self.device = device
        ''' The MonkeyDevice '''
        self.children = []
        ''' The children of this View '''
        self.parent = None
        ''' The parent of this View '''
        self.windows = {}
        self.currentFocus = None
        ''' The current focus '''
        self.build = {}
        ''' Build properties '''
        self.version = version
        ''' API version number '''
        self.forceviewserveruse = forceviewserveruse
        ''' Force ViewServer use '''

        if version != -1:
            self.build[VERSION_SDK_PROPERTY] = version
        else:
            try:
                if USE_ADB_CLIENT_TO_GET_BUILD_PROPERTIES:
                    self.build[VERSION_SDK_PROPERTY] = int(device.getProperty(VERSION_SDK_PROPERTY))
                else:
                    self.build[VERSION_SDK_PROPERTY] = int(device.shell('getprop ' + VERSION_SDK_PROPERTY)[:-2])
            except:
                self.build[VERSION_SDK_PROPERTY] = -1

        version = self.build[VERSION_SDK_PROPERTY]
        self.useUiAutomator = (version >= 16) and not forceviewserveruse
        ''' Whether to use UIAutomator or ViewServer '''
        self.idProperty = None
        ''' The id property depending on the View attribute format '''
        self.textProperty = None
        ''' The text property depending on the View attribute format '''
        self.leftProperty = None
        ''' The left property depending on the View attribute format '''
        self.topProperty = None
        ''' The top property depending on the View attribute format '''
        self.widthProperty = None
        ''' The width property depending on the View attribute format '''
        self.heightProperty = None
        ''' The height property depending on the View attribute format '''
        if version >= 16 and self.useUiAutomator:
            self.idProperty = ID_PROPERTY_UI_AUTOMATOR
            self.textProperty = TEXT_PROPERTY_UI_AUTOMATOR
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        elif version > 10 and (version < 16 or self.useUiAutomator):
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        elif version == 10:
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY_API_10
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        elif version >= 7 and version < 10:
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY_API_10
            self.leftProperty = LEFT_PROPERTY_API_8
            self.topProperty = TOP_PROPERTY_API_8
            self.widthProperty = WIDTH_PROPERTY_API_8
            self.heightProperty = HEIGHT_PROPERTY_API_8
        elif version > 0 and version < 7:
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY_API_10
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        elif version == -1:
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        else:
            self.idProperty = ID_PROPERTY
            self.textProperty = TEXT_PROPERTY
            self.leftProperty = LEFT_PROPERTY
            self.topProperty = TOP_PROPERTY
            self.widthProperty = WIDTH_PROPERTY
            self.heightProperty = HEIGHT_PROPERTY
        
    def __getitem__(self, key):
        return self.map[key]

    def __getattr__(self, name):
        if DEBUG_GETATTR:
            print >>sys.stderr, "__getattr__(%s)    version: %d" % (name, self.build[VERSION_SDK_PROPERTY])

        # NOTE:
        # I should try to see if 'name' is a defined method
        # but it seems that if I call locals() here an infinite loop is entered

        if self.map.has_key(name):
            r = self.map[name]
        elif self.map.has_key(name + '()'):
            # the method names are stored in the map with their trailing '()'
            r = self.map[name + '()']
        elif name.count("_") > 0:
            mangledList = self.allPossibleNamesWithColon(name)
            mangledName = self.intersection(mangledList, self.map.keys())
            if len(mangledName) > 0 and self.map.has_key(mangledName[0]):
                r = self.map[mangledName[0]]
            else:
                # Default behavior
                raise AttributeError, name
        else:
            # try removing 'is' prefix
            if DEBUG_GETATTR:
                print >> sys.stderr, "    __getattr__: trying without 'is' prefix"
            suffix = name[2:].lower()
            if self.map.has_key(suffix):
                r = self.map[suffix]
            else:
                # Default behavior
                raise AttributeError, name

        # if the method name starts with 'is' let's assume its return value is boolean
#         if name[:2] == 'is':
#             r = True if r == 'true' else False
        if r == 'true':
            r = True
        elif r == 'false':
            r = False

        # this should not cached in some way
        def innerMethod():
            if DEBUG_GETATTR:
                print >>sys.stderr, "innerMethod: %s returning %s" % (innerMethod.__name__, r)
            return r

        innerMethod.__name__ = name

        # this should work, but then there's problems with the arguments of innerMethod
        # even if innerMethod(self) is added
        #setattr(View, innerMethod.__name__, innerMethod)
        #setattr(self, innerMethod.__name__, innerMethod)

        return innerMethod

    def __call__(self, *args, **kwargs):
        if DEBUG_CALL:
            print >>sys.stderr, "__call__(%s)" % (args if args else None)

    def getClass(self):
        '''
        Gets the L{View} class

        @return:  the L{View} class or C{None} if not defined
        '''

        try:
            return self.map['class']
        except:
            return None

    def getId(self):
        '''
        Gets the L{View} Id

        @return: the L{View} C{Id} or C{None} if not defined
        @see: L{getUniqueId()}
        '''

        try:
            return self.map['resource-id']
        except:
            pass

        try:
            return self.map[self.idProperty]
        except:
            return None

    def getContentDescription(self):
        '''
        Gets the content description.
        '''

        try:
            return self.map['content-desc']
        except:
            return None

    def getParent(self):
        '''
        Gets the parent.
        '''

        return self.parent

    def getText(self):
        '''
        Gets the text attribute.

        @return: the text attribute or C{None} if not defined
        '''

        try:
            return self.map[self.textProperty]
        except Exception:
            return None

    def getHeight(self):
        '''
        Gets the height.
        '''

        if self.useUiAutomator:
            return self.map['bounds'][1][1] - self.map['bounds'][0][1]
        else:
            try:
                return int(self.map[self.heightProperty])
            except:
                return 0

    def getWidth(self):
        '''
        Gets the width.
        '''

        if self.useUiAutomator:
            return self.map['bounds'][1][0] - self.map['bounds'][0][0]
        else:
            try:
                return int(self.map[self.widthProperty])
            except:
                return 0

    def getUniqueId(self):
        '''
        Gets the unique Id of this View.

        @see: L{ViewClient.__splitAttrs()} for a discussion on B{Unique Ids}
        '''

        try:
            return self.map['uniqueId']
        except:
            return None

    def getVisibility(self):
        '''
        Gets the View visibility
        '''

        try:
            if self.map[GET_VISIBILITY_PROPERTY] == 'VISIBLE':
                return VISIBLE
            elif self.map[GET_VISIBILITY_PROPERTY] == 'INVISIBLE':
                return INVISIBLE
            elif self.map[GET_VISIBILITY_PROPERTY] == 'GONE':
                return GONE
            else:
                return -2
        except:
            return -1

    def getX(self):
        '''
        Gets the View X coordinate
        '''

        if DEBUG_COORDS:
            print >>sys.stderr, "getX(%s %s ## %s)" % (self.getClass(), self.getId(), self.getUniqueId())
        x = 0

        if self.useUiAutomator:
            x = self.map['bounds'][0][0]
        else:
            try:
                if GET_VISIBILITY_PROPERTY in self.map and self.map[GET_VISIBILITY_PROPERTY] == 'VISIBLE':
                    _x = int(self.map[self.leftProperty])
                    if DEBUG_COORDS: print >>sys.stderr, "   getX: VISIBLE adding %d" % _x
                    x += _x
            except:
                warnings.warn("View %s has no '%s' property" % (self.getId(), self.leftProperty))

        if DEBUG_COORDS: print >>sys.stderr, "   getX: returning %d" % (x)
        return x

    def getY(self):
        '''
        Gets the View Y coordinate
        '''

        if DEBUG_COORDS:
            print >>sys.stderr, "getY(%s %s ## %s)" % (self.getClass(), self.getId(), self.getUniqueId())
        y = 0

        if self.useUiAutomator:
            y = self.map['bounds'][0][1]
        else:
            try:
                if GET_VISIBILITY_PROPERTY in self.map and self.map[GET_VISIBILITY_PROPERTY] == 'VISIBLE':
                    _y = int(self.map[self.topProperty])
                    if DEBUG_COORDS: print >>sys.stderr, "   getY: VISIBLE adding %d" % _y
                    y += _y
            except:
                warnings.warn("View %s has no '%s' property" % (self.getId(), self.topProperty))

        if DEBUG_COORDS: print >>sys.stderr, "   getY: returning %d" % (y)
        return y

    def getXY(self, debug=False):
        '''
        Returns the I{screen} coordinates of this C{View}.

        @return: The I{screen} coordinates of this C{View}
        '''

        if DEBUG_COORDS or debug:
            try:
                id = self.getId()
            except:
                id = "NO_ID"
            print >> sys.stderr, "getXY(%s %s ## %s)" % (self.getClass(), id, self.getUniqueId())

        x = self.getX()
        y = self.getY()
        if self.useUiAutomator:
            return (x, y)

        parent = self.parent
        if DEBUG_COORDS: print >> sys.stderr, "   getXY: x=%s y=%s parent=%s" % (x, y, parent.getUniqueId() if parent else "None")
        hx = 0
        ''' Hierarchy accumulated X '''
        hy = 0
        ''' Hierarchy accumulated Y '''

        if DEBUG_COORDS: print >> sys.stderr, "   getXY: not using UiAutomator, calculating parent coordinates"
        while parent != None:
            if DEBUG_COORDS: print >> sys.stderr, "      getXY: parent: %s %s <<<<" % (parent.getClass(), parent.getId())
            if SKIP_CERTAIN_CLASSES_IN_GET_XY_ENABLED:
                if parent.getClass() in [ 'com.android.internal.widget.ActionBarView',
                                   'com.android.internal.widget.ActionBarContextView',
                                   'com.android.internal.view.menu.ActionMenuView',
                                   'com.android.internal.policy.impl.PhoneWindow$DecorView' ]:
                    if DEBUG_COORDS: print >> sys.stderr, "   getXY: skipping %s %s (%d,%d)" % (parent.getClass(), parent.getId(), parent.getX(), parent.getY())
                    parent = parent.parent
                    continue
            if DEBUG_COORDS: print >> sys.stderr, "   getXY: parent=%s x=%d hx=%d y=%d hy=%d" % (parent.getId(), x, hx, y, hy)
            hx += parent.getX()
            hy += parent.getY()
            parent = parent.parent

        (wvx, wvy) = self.__dumpWindowsInformation(debug=debug)
        if DEBUG_COORDS or debug:
            print >>sys.stderr, "   getXY: wv=(%d, %d) (windows information)" % (wvx, wvy)
        try:
            fw = self.windows[self.currentFocus]
            if DEBUG_STATUSBAR:
                print >> sys.stderr, "    getXY: focused window=", fw
                print >> sys.stderr, "    getXY: deciding whether to consider statusbar offset because current focused windows is at", (fw.wvx, fw.wvy), "parent", (fw.px, fw.py)
        except KeyError:
            fw = None
        (sbw, sbh) = self.__obtainStatusBarDimensionsIfVisible()
        if DEBUG_COORDS or debug:
            print >>sys.stderr, "   getXY: sb=(%d, %d) (statusbar dimensions)" % (sbw, sbh)
        statusBarOffset = 0
        pwx = 0
        pwy = 0

        if fw:
            if DEBUG_COORDS:
                print >>sys.stderr, "    getXY: focused window=", fw, "sb=", (sbw, sbh)
            if fw.wvy <= sbh: # it's very unlikely that fw.wvy < sbh, that is a window over the statusbar
                if DEBUG_STATUSBAR: print >>sys.stderr, "        getXY: yes, considering offset=", sbh
                statusBarOffset = sbh
            else:
                if DEBUG_STATUSBAR: print >>sys.stderr, "        getXY: no, ignoring statusbar offset fw.wvy=", fw.wvy, ">", sbh

            if fw.py == fw.wvy:
                if DEBUG_STATUSBAR: print >>sys.stderr, "        getXY: but wait, fw.py == fw.wvy so we are adjusting by ", (fw.px, fw.py)
                pwx = fw.px
                pwy = fw.py
            else:
                if DEBUG_STATUSBAR: print >>sys.stderr, "    getXY: fw.py=%d <= fw.wvy=%d, no adjustment" % (fw.py, fw.wvy)

        if DEBUG_COORDS or DEBUG_STATUSBAR or debug:
            print >>sys.stderr, "   getXY: returning (%d, %d) ***" % (x+hx+wvx+pwx, y+hy+wvy-statusBarOffset+pwy)
            print >>sys.stderr, "                     x=%d+%d+%d+%d" % (x,hx,wvx,pwx)
            print >>sys.stderr, "                     y=%d+%d+%d-%d+%d" % (y,hy,wvy,statusBarOffset,pwy)
        return (x+hx+wvx+pwx, y+hy+wvy-statusBarOffset+pwy)

    def getCoords(self):
        '''
        Gets the coords of the View

        @return: A tuple containing the View's coordinates ((L, T), (R, B))
        '''

        if DEBUG_COORDS:
            print >>sys.stderr, "getCoords(%s %s ## %s)" % (self.getClass(), self.getId(), self.getUniqueId())

        (x, y) = self.getXY();
        w = self.getWidth()
        h = self.getHeight()
        return ((x, y), (x+w, y+h))

    def getPositionAndSize(self):
        '''
        Gets the position and size (X,Y, W, H)

        @return: A tuple containing the View's coordinates (X, Y, W, H)
        '''

        (x, y) = self.getXY();
        w = self.getWidth()
        h = self.getHeight()
        return (x, y, w, h)


    def getCenter(self):
        '''
        Gets the center coords of the View

        @author: U{Dean Morin <https://github.com/deanmorin>}
        '''

        (left, top), (right, bottom) = self.getCoords()
        x = left + (right - left) / 2
        y = top + (bottom - top) / 2
        return (x, y)

    def __obtainStatusBarDimensionsIfVisible(self):
        sbw = 0
        sbh = 0
        for winId in self.windows:
            w = self.windows[winId]
            if DEBUG_COORDS: print >> sys.stderr, "      __obtainStatusBarDimensionsIfVisible: w=", w, "   w.activity=", w.activity, "%%%"
            if w.activity == 'StatusBar':
                if w.wvy == 0 and w.visibility == 0:
                    if DEBUG_COORDS: print >> sys.stderr, "      __obtainStatusBarDimensionsIfVisible: statusBar=", (w.wvw, w.wvh)
                    sbw = w.wvw
                    sbh = w.wvh
                break

        return (sbw, sbh)

    def __obtainVxVy(self, m):
        wvx = int(m.group('vx'))
        wvy = int(m.group('vy'))
        return wvx, wvy

    def __obtainVwVh(self, m):
        (wvx, wvy) = self.__obtainVxVy(m)
        wvx1 = int(m.group('vx1'))
        wvy1 = int(m.group('vy1'))
        return (wvx1-wvx, wvy1-wvy)

    def __obtainPxPy(self, m):
        px = int(m.group('px'))
        py = int(m.group('py'))
        return (px, py)

    def __dumpWindowsInformation(self, debug=False):
        self.windows = {}
        self.currentFocus = None
        dww = self.device.shell('dumpsys window windows')
        if DEBUG_WINDOWS or debug: print >> sys.stderr, dww
        lines = dww.split('\n')
        widRE = re.compile('^ *Window #%s Window{%s (u\d+ )?%s?.*}:' %
                            (_nd('num'), _nh('winId'), _ns('activity', greedy=True)))
        currentFocusRE = re.compile('^  mCurrentFocus=Window{%s .*' % _nh('winId'))
        viewVisibilityRE = re.compile(' mViewVisibility=0x%s ' % _nh('visibility'))
        # This is for 4.0.4 API-15
        containingFrameRE = re.compile('^   *mContainingFrame=\[%s,%s\]\[%s,%s\] mParentFrame=\[%s,%s\]\[%s,%s\]' %
                             (_nd('cx'), _nd('cy'), _nd('cw'), _nd('ch'), _nd('px'), _nd('py'), _nd('pw'), _nd('ph')))
        contentFrameRE = re.compile('^   *mContentFrame=\[%s,%s\]\[%s,%s\] mVisibleFrame=\[%s,%s\]\[%s,%s\]' %
                             (_nd('x'), _nd('y'), _nd('w'), _nd('h'), _nd('vx'), _nd('vy'), _nd('vx1'), _nd('vy1')))
        # This is for 4.1 API-16
        framesRE = re.compile('^   *Frames: containing=\[%s,%s\]\[%s,%s\] parent=\[%s,%s\]\[%s,%s\]' %
                               (_nd('cx'), _nd('cy'), _nd('cw'), _nd('ch'), _nd('px'), _nd('py'), _nd('pw'), _nd('ph')))
        contentRE = re.compile('^     *content=\[%s,%s\]\[%s,%s\] visible=\[%s,%s\]\[%s,%s\]' %
                               (_nd('x'), _nd('y'), _nd('w'), _nd('h'), _nd('vx'), _nd('vy'), _nd('vx1'), _nd('vy1')))
        policyVisibilityRE = re.compile('mPolicyVisibility=%s ' % _ns('policyVisibility', greedy=True))

        for l in range(len(lines)):
            m = widRE.search(lines[l])
            if m:
                num = int(m.group('num'))
                winId = m.group('winId')
                activity = m.group('activity')
                wvx = 0
                wvy = 0
                wvw = 0
                wvh = 0
                px = 0
                py = 0
                visibility = -1
                policyVisibility = 0x0

                for l2 in range(l+1, len(lines)):
                    m = widRE.search(lines[l2])
                    if m:
                        l += (l2-1)
                        break
                    m = viewVisibilityRE.search(lines[l2])
                    if m:
                        visibility = int(m.group('visibility'))
                        if DEBUG_COORDS: print >> sys.stderr, "__dumpWindowsInformation: visibility=", visibility
                    if self.build[VERSION_SDK_PROPERTY] >= 17:
                        wvx, wvy = (0, 0)
                        wvw, wvh = (0, 0)
                    if self.build[VERSION_SDK_PROPERTY] >= 16:
                        m = framesRE.search(lines[l2])
                        if m:
                            px, py = self.__obtainPxPy(m)
                            m = contentRE.search(lines[l2+1])
                            if m:
                                # FIXME: the information provided by 'dumpsys window windows' in 4.2.1 (API 16)
                                # when there's a system dialog may not be correct and causes the View coordinates
                                # be offset by this amount, see
                                # https://github.com/dtmilano/AndroidViewClient/issues/29
                                wvx, wvy = self.__obtainVxVy(m)
                                wvw, wvh = self.__obtainVwVh(m)
                    elif self.build[VERSION_SDK_PROPERTY] == 15:
                        m = containingFrameRE.search(lines[l2])
                        if m:
                            px, py = self.__obtainPxPy(m)
                            m = contentFrameRE.search(lines[l2+1])
                            if m:
                                wvx, wvy = self.__obtainVxVy(m)
                                wvw, wvh = self.__obtainVwVh(m)
                    elif self.build[VERSION_SDK_PROPERTY] == 10:
                        m = containingFrameRE.search(lines[l2])
                        if m:
                            px, py = self.__obtainPxPy(m)
                            m = contentFrameRE.search(lines[l2+1])
                            if m:
                                wvx, wvy = self.__obtainVxVy(m)
                                wvw, wvh = self.__obtainVwVh(m)
                    else:
                        warnings.warn("Unsupported Android version %d" % self.build[VERSION_SDK_PROPERTY])

                    #print >> sys.stderr, "Searching policyVisibility in", lines[l2]
                    m = policyVisibilityRE.search(lines[l2])
                    if m:
                        policyVisibility = 0x0 if m.group('policyVisibility') == 'true' else 0x8

                self.windows[winId] = Window(num, winId, activity, wvx, wvy, wvw, wvh, px, py, visibility + policyVisibility)
            else:
                m = currentFocusRE.search(lines[l])
                if m:
                    self.currentFocus = m.group('winId')

        if self.currentFocus in self.windows and self.windows[self.currentFocus].visibility == 0:
            if DEBUG_COORDS or debug:
                print >> sys.stderr, "__dumpWindowsInformation: focus=", self.currentFocus
                print >> sys.stderr, "__dumpWindowsInformation:", self.windows[self.currentFocus]
            w = self.windows[self.currentFocus]
            return (w.wvx, w.wvy)
        else:
            if DEBUG_COORDS: print >> sys.stderr, "__dumpWindowsInformation: (0,0)"
            return (0,0)

    def touch(self, type=adbclient.DOWN_AND_UP):
        '''
        Touches the center of this C{View}
        '''

        (x, y) = self.getCenter()
        if DEBUG_TOUCH:
            print >>sys.stderr, "should touch @ (%d, %d)" % (x, y)
        if VIEW_CLIENT_TOUCH_WORKAROUND_ENABLED and type == adbclient.DOWN_AND_UP:
            if WARNINGS:
                print >> sys.stderr, "ViewClient: touch workaround enabled"
            self.device.touch(x, y, adbclient.DOWN)
            time.sleep(50/1000.0)
            self.device.touch(x+10, y+10, adbclient.UP)
        else:
            self.device.touch(x, y, type)

    def allPossibleNamesWithColon(self, name):
        l = []
        for i in range(name.count("_")):
            name = name.replace("_", ":", 1)
            l.append(name)
        return l

    def intersection(self, l1, l2):
        return list(set(l1) & set(l2))

    def containsPoint(self, (x, y)):
        (X, Y, W, H) = self.getPositionAndSize()
        return (((x >= X) and (x <= (X+W)) and ((y >= Y) and (y <= (Y+H)))))

    def add(self, child):
        '''
        Adds a child

        @type child: View
        @param child: The child to add
        '''
        child.parent = self
        self.children.append(child)

    def isClickable(self):
        return self.__getattr__('isClickable')()

    def variableNameFromId(self):
        _id = self.getId()
        if _id:
            var = _id.replace('.', '_').replace(':', '___').replace('/', '_')
        else:
            _id = self.getUniqueId()
            m = ID_RE.match(_id)
            if m:
                var = m.group(1)
                if m.group(3):
                    var += m.group(3)
                if re.match('^\d', var):
                    var = 'id_' + var
        return var

    def writeImageToFile(self, filename, format="PNG"):
        '''
        Write the View image to the specified filename in the specified format.

        @type filename: str
        @param filename: Absolute path and optional filename receiving the image. If this points to
                         a directory, then the filename is determined by this View unique ID and
                         format extension.
        @type format: str
        @param format: Image format (default format is PNG)
        '''

        if not os.path.isabs(filename):
            raise ValueError("writeImageToFile expects an absolute path")
        if os.path.isdir(filename):
            filename = os.path.join(filename, self.variableNameFromId() + '.' + format.lower())
        if DEBUG:
            print >> sys.stderr, "writeImageToFile: saving image to '%s' in %s format" % (filename, format)
        #self.device.takeSnapshot().getSubImage(self.getPositionAndSize()).writeToFile(filename, format)
        # crop:
        # im.crop(box) ⇒ image
        # Returns a copy of a rectangular region from the current image.
        # The box is a 4-tuple defining the left, upper, right, and lower pixel coordinate.
        ((l, t), (r, b)) = self.getCoords()
        box = (l, t, r, b)
        if DEBUG:
            print >> sys.stderr, "writeImageToFile: cropping", box, "    reconnect=", self.device.reconnect
        self.device.takeSnapshot(reconnect=self.device.reconnect).crop(box).save(filename, format)

    def __smallStr__(self):
        __str = unicode("View[", 'utf-8', 'replace')
        if "class" in self.map:
            __str += " class=" + self.map['class']
        __str += " id=%s" % self.getId()
        __str += " ]   parent="
        if self.parent and "class" in self.parent.map:
            __str += "%s" % self.parent.map["class"]
        else:
            __str += "None"

        return __str

    def __tinyStr__(self):
        __str = unicode("View[", 'utf-8', 'replace')
        if "class" in self.map:
            __str += " class=" + re.sub('.*\.', '', self.map['class'])
        __str += " id=%s" % self.getId()
        __str += " ]"

        return __str

    def __microStr__(self):
        __str = unicode('', 'utf-8', 'replace')
        if "class" in self.map:
            __str += re.sub('.*\.', '', self.map['class'])
        id = self.getId().replace('id/no_id/', '-')
        __str += id
        ((L, T), (R, B)) = self.getCoords()
        __str += '@%04d%04d%04d%04d' % (L, T, R, B)
        __str += ''

        return __str


    def __str__(self):
        __str = unicode("View[", 'utf-8', 'replace')
        if "class" in self.map:
            __str += " class=" + self.map["class"].__str__() + " "
        for a in self.map:
            __str += a + "="
            # decode() works only on python's 8-bit strings
            if isinstance(self.map[a], unicode):
                __str += self.map[a]
            else:
                __str += unicode(str(self.map[a]), 'utf-8', errors='replace')
            __str += " "
        __str += "]   parent="
        if self.parent:
            if "class" in self.parent.map:
                __str += "%s" % self.parent.map["class"]
            else:
                __str += self.parent.getId().__str__()
        else:
            __str += "None"

        return __str

class TextView(View):
    '''
    TextView class.
    '''

    pass

class EditText(TextView):
    '''
    EditText class.
    '''
    
    def type(self, text):
        self.touch()
        time.sleep(0.5)
        escaped = text.replace('%s', '\\%s')
        encoded = escaped.replace(' ', '%s')
        self.device.type(encoded)
        time.sleep(0.5)

    def backspace(self):
        self.touch()
        time.sleep(1)
        self.device.press('KEYCODE_DEL', adbclient.DOWN_AND_UP)

class UiAutomator2AndroidViewClient():
    '''
    UiAutomator XML to AndroidViewClient
    '''

    def __init__(self, device, version):
        self.device = device
        self.version = version
        self.root = None
        self.nodeStack = []
        self.parent = None
        self.views = []
        self.idCount = 1

    def StartElement(self, name, attributes):
        '''
        Expat start element event handler
        '''
        if name == 'hierarchy':
            pass
        elif name == 'node':
            # Instantiate an Element object
            attributes['uniqueId'] = 'id/no_id/%d' % self.idCount
            bounds = re.split('[\][,]', attributes['bounds'])
            attributes['bounds'] = ((int(bounds[1]), int(bounds[2])), (int(bounds[4]), int(bounds[5])))
            if DEBUG_BOUNDS:
                print >> sys.stderr, "bounds=", attributes['bounds']
            self.idCount += 1
            child = View.factory(attributes, self.device, self.version)
            self.views.append(child)
            # Push element onto the stack and make it a child of parent
            if not self.nodeStack:
                self.root = child
            else:
                self.parent = self.nodeStack[-1]
                self.parent.add(child)
            self.nodeStack.append(child)

    def EndElement(self, name):
        '''
        Expat end element event handler
        '''

        if name == 'hierarchy':
            pass
        elif name == 'node':
            self.nodeStack.pop()

    def CharacterData(self, data):
        '''
        Expat character data event handler
        '''

        if data.strip():
            data = data.encode()
            element = self.nodeStack[-1]
            element.cdata += data

    def Parse(self, uiautomatorxml):
        # Create an Expat parser
        parser = xml.parsers.expat.ParserCreate()
        # Set the Expat event handlers to our methods
        parser.StartElementHandler = self.StartElement
        parser.EndElementHandler = self.EndElement
        parser.CharacterDataHandler = self.CharacterData
        # Parse the XML File
        try:
            parserStatus = parser.Parse(uiautomatorxml.encode(encoding='utf-8', errors='replace'), True)
        except xml.parsers.expat.ExpatError, ex:
            print >>sys.stderr, "ERROR: Offending XML:\n", repr(uiautomatorxml)
            raise RuntimeError(ex)
        return self.root

class Excerpt2Code():
    ''' Excerpt XML to code '''

    def __init__(self):
        self.data = None

    def StartElement(self, name, attributes):
        '''
        Expat start element event handler
        '''
        if name == 'excerpt':
            pass
        else:
            warnings.warn("Unexpected element: '%s'" % name)

    def EndElement(self, name):
        '''
        Expat end element event handler
        '''

        if name == 'excerpt':
            pass

    def CharacterData(self, data):
        '''
        Expat character data event handler
        '''

        if data.strip():
            data = data.encode()
            if not self.data:
                self.data = data
            else:
                self.data += data

    def Parse(self, excerpt):
        # Create an Expat parser
        parser = xml.parsers.expat.ParserCreate()
        # Set the Expat event handlers to our methods
        parser.StartElementHandler = self.StartElement
        parser.EndElementHandler = self.EndElement
        parser.CharacterDataHandler = self.CharacterData
        # Parse the XML
        parserStatus = parser.Parse(excerpt, 1)
        return self.data

class ViewClient:
    '''
    ViewClient is a I{ViewServer} client.

    ViewServer backend
    ==================
    If not running the ViewServer is started on the target device or emulator and then the port
    mapping is created.

    UiAutomator backend
    ===================
    No service is started.
    '''

    def __init__(self, device, serialno, adb=None, autodump=True, forceviewserveruse=False, localport=VIEW_SERVER_PORT, remoteport=VIEW_SERVER_PORT, startviewserver=True, ignoreuiautomatorkilled=False):
        '''
        Constructor

        @type device: MonkeyDevice
        @param device: The device running the C{View server} to which this client will connect
        @type serialno: str
        @param serialno: the serial number of the device or emulator to connect to
        @type adb: str
        @param adb: the path of the C{adb} executable or None and C{ViewClient} will try to find it
        @type autodump: boolean
        @param autodump: whether an automatic dump is performed at the end of this constructor
        @type forceviewserveruse: boolean
        @param forceviewserveruse: Force the use of C{ViewServer} even if the conditions to use
                            C{UiAutomator} are satisfied
        @type localport: int
        @param localport: the local port used in the redirection
        @type remoteport: int
        @param remoteport: the remote port used to start the C{ViewServer} in the device or
                           emulator
        @type startviewserver: boolean
        @param startviewserver: Whether to start the B{global} ViewServer
        @type ignoreuiautomatorkilled: boolean
        @param ignoreuiautomatorkilled: Ignores received B{Killed} message from C{uiautomator}
        '''

        if not device:
            raise Exception('Device is not connected')
        self.device = device
        ''' The C{MonkeyDevice} device instance '''

        if not serialno:
            raise ValueError("Serialno cannot be None")
        self.serialno = self.__mapSerialNo(serialno)
        ''' The serial number of the device '''

        if DEBUG_DEVICE: print >> sys.stderr, "ViewClient: using device with serialno", self.serialno

        if adb:
            if not os.access(adb, os.X_OK):
                raise Exception('adb="%s" is not executable' % adb)
        else:
            # Using adbclient we don't need adb executable yet (maybe it's needed if we want to
            # start adb if not running)
            adb = ViewClient.__obtainAdbPath()

        self.adb = adb
        ''' The adb command '''
        self.root = None
        ''' The root node '''
        self.viewsById = {}
        ''' The map containing all the L{View}s indexed by their L{View.getUniqueId()} '''
        self.display = {}
        ''' The map containing the device's display properties: width, height and density '''
        for prop in [ 'width', 'height', 'density' ]:
            self.display[prop] = -1
            if USE_ADB_CLIENT_TO_GET_BUILD_PROPERTIES:
                try:
                    self.display[prop] = int(device.getProperty('display.' + prop))
                except:
                    if WARNINGS:
                        warnings.warn("Couldn't determine display %s" % prop)
            else:
                # these values are usually not defined as properties, so we stick to the -1 set
                # before
                pass

        self.build = {}
        ''' The map containing the device's build properties: version.sdk, version.release '''

        for prop in [VERSION_SDK_PROPERTY, VERSION_RELEASE_PROPERTY]:
            self.build[prop] = -1
            try:
                if USE_ADB_CLIENT_TO_GET_BUILD_PROPERTIES:
                    self.build[prop] = device.getProperty(prop)
                else:
                    self.build[prop] = device.shell('getprop ro.build.' + prop)[:-2]
            except:
                if WARNINGS:
                    warnings.warn("Couldn't determine build %s" % prop)

            if prop == VERSION_SDK_PROPERTY:
                # we expect it to be an int
                self.build[prop] = int(self.build[prop] if self.build[prop] else -1)

        self.ro = {}
        ''' The map containing the device's ro properties: secure, debuggable '''
        for prop in ['secure', 'debuggable']:
            try:
                self.ro[prop] = device.shell('getprop ro.' + prop)[:-2]
            except:
                if WARNINGS:
                    warnings.warn("Couldn't determine ro %s" % prop)
                self.ro[prop] = 'UNKNOWN'

        self.forceViewServerUse = forceviewserveruse
        ''' Force the use of ViewServer even if the conditions to use UiAutomator are satisfied '''
        self.useUiAutomator = (self.build[VERSION_SDK_PROPERTY] >= 16) and not forceviewserveruse # jelly bean 4.1 & 4.2
        if DEBUG:
            print >> sys.stderr, "    ViewClient.__init__: useUiAutomator=", self.useUiAutomator, "sdk=", self.build[VERSION_SDK_PROPERTY], "forceviewserveruse=", forceviewserveruse
        ''' If UIAutomator is supported by the device it will be used '''
        self.ignoreUiAutomatorKilled = ignoreuiautomatorkilled
        ''' On some devices (i.e. Nexus 7 running 4.2.2) uiautomator is killed just after generating
        the dump file. In many cases the file is already complete so we can ask to ignore the 'Killed'
        message by setting L{ignoreuiautomatorkilled} to C{True}.

        Changes in v2.3.21 that uses C{/dev/tty} instead of a file may have turned this variable
        unnecessary, however it has been kept for backward compatibility.
        '''

        if self.useUiAutomator:
            self.textProperty = TEXT_PROPERTY_UI_AUTOMATOR
        else:
            if self.build[VERSION_SDK_PROPERTY] <= 10:
                self.textProperty = TEXT_PROPERTY_API_10
            else:
                self.textProperty = TEXT_PROPERTY
            if startviewserver:
                if not self.serviceResponse(device.shell('service call window 3')):
                    try:
                        self.assertServiceResponse(device.shell('service call window 1 i32 %d' %
                                                        remoteport))
                    except:
                        msg = 'Cannot start View server.\n' \
                            'This only works on emulator and devices running developer versions.\n' \
                            'Does hierarchyviewer work on your device?\n' \
                            'See https://github.com/dtmilano/AndroidViewClient/wiki/Secure-mode\n\n' \
                            'Device properties:\n' \
                            '    ro.secure=%s\n' \
                            '    ro.debuggable=%s\n' % (self.ro['secure'], self.ro['debuggable'])
                        raise Exception(msg)

            self.localPort = localport
            self.remotePort = remoteport
            # FIXME: it seems there's no way of obtaining the serialno from the MonkeyDevice
            subprocess.check_call([self.adb, '-s', self.serialno, 'forward', 'tcp:%d' % self.localPort,
                                    'tcp:%d' % self.remotePort])

        self.windows = None
        ''' The list of windows as obtained by L{ViewClient.list()} '''

        if autodump:
            self.dump()

    def __del__(self):
        # should clean up some things
        pass

    @staticmethod
    def __obtainAdbPath():
        '''
        Obtains the ADB path attempting know locations for different OSs
        '''

        osName = platform.system()
        isWindows = False
        if osName.startswith('Windows'):
            adb = 'adb.exe'
            isWindows = True
        else:
            adb = 'adb'

        ANDROID_HOME = os.environ['ANDROID_HOME'] if os.environ.has_key('ANDROID_HOME') else '/opt/android-sdk'
        HOME = os.environ['HOME'] if os.environ.has_key('HOME') else ''

        possibleChoices = [ os.path.join(ANDROID_HOME, 'platform-tools', adb),
                           os.path.join(HOME,  "android", 'platform-tools', adb),
                           os.path.join(HOME,  "android-sdk", 'platform-tools', adb),
                           adb,
                           ]

        if osName.startswith('Windows'):
            possibleChoices.append(os.path.join("""C:\Program Files\Android\android-sdk\platform-tools""", adb))
            possibleChoices.append(os.path.join("""C:\Program Files (x86)\Android\android-sdk\platform-tools""", adb))
        elif osName.startswith('Linux'):
            possibleChoices.append(os.path.join("opt", "android-sdk-linux",  'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "opt", "android-sdk-linux",  'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "android-sdk-linux",  'platform-tools', adb))
        elif osName.startswith('Mac'):
            possibleChoices.append(os.path.join("opt", "android-sdk-mac_x86",  'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "opt", "android-sdk-mac", 'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "android-sdk-mac", 'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "opt", "android-sdk-mac_x86",  'platform-tools', adb))
            possibleChoices.append(os.path.join(HOME,  "android-sdk-mac_x86",  'platform-tools', adb))
        else:
            # Unsupported OS
            pass

        for exeFile in possibleChoices:
            if os.access(exeFile, os.X_OK):
                return exeFile

        for path in os.environ["PATH"].split(os.pathsep):
            exeFile = os.path.join(path, adb)
            if exeFile != None and os.access(exeFile, os.X_OK if not isWindows else os.F_OK):
                return exeFile

        raise Exception('adb="%s" is not executable. Did you forget to set ANDROID_HOME in the environment?' % adb)

    @staticmethod
    def __mapSerialNo(serialno):
        serialno = serialno.strip()
        #ipRE = re.compile('^\d+\.\d+.\d+.\d+$')
        if IP_RE.match(serialno):
            if DEBUG_DEVICE: print >>sys.stderr, "ViewClient: adding default port to serialno", serialno, ADB_DEFAULT_PORT
            return serialno + ':%d' % ADB_DEFAULT_PORT

        ipPortRE = re.compile('^\d+\.\d+.\d+.\d+:\d+$')
        if ipPortRE.match(serialno):
            # nothing to map
            return serialno

        if re.search("[.*()+]", serialno):
            raise ValueError("Regular expression not supported as serialno in ViewClient")

        return serialno

    @staticmethod
    def __obtainDeviceSerialNumber(device):
        if DEBUG_DEVICE: print >>sys.stderr, "ViewClient: obtaining serial number for connected device"
        serialno = device.getProperty('ro.serialno')
        if not serialno:
            serialno = device.shell('getprop ro.serialno')
            if serialno:
                serialno = serialno[:-2]
        if not serialno:
            qemu = device.shell('getprop ro.kernel.qemu')
            if qemu:
                qemu = qemu[:-2]
                if qemu and int(qemu) == 1:
                    # FIXME !!!!!
                    # this must be calculated from somewhere, though using a fixed serialno for now
                    warnings.warn("Running on emulator but no serial number was specified then 'emulator-5554' is used")
                    serialno = 'emulator-5554'
        if not serialno:
            # If there's only one device connected get its serialno
            adb = ViewClient.__obtainAdbPath()
            if DEBUG_DEVICE: print >>sys.stderr, "    using adb=%s" % adb
            s = subprocess.Popen([adb, 'get-serialno'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}).communicate()[0][:-1]
            if s != 'unknown':
                serialno = s
        if DEBUG_DEVICE: print >>sys.stderr, "    serialno=%s" % serialno
        if not serialno:
            warnings.warn("Couldn't obtain the serialno of the connected device")
        return serialno

    @staticmethod
    def setAlarm(timeout):
        osName = platform.system()
        if osName.startswith('Windows'): # alarm is not implemented in Windows
            return
        signal.alarm(timeout)

    @staticmethod
    def connectToDeviceOrExit(timeout=60, verbose=False, ignoresecuredevice=False, serialno=None):
        '''
        Connects to a device which serial number is obtained from the script arguments if available
        or using the default regex C{.*}.

        If the connection is not successful the script exits.
        L{MonkeyRunner.waitForConnection()} returns a L{MonkeyDevice} even if the connection failed.
        Then, to detect this situation, C{device.wake()} is attempted and if it fails then it is
        assumed the previous connection failed.

        @type timeout: int
        @param timeout: timeout for the connection
        @type verbose: bool
        @param verbose: Verbose output
        @type ignoresecuredevice: bool
        @param ignoresecuredevice: Ignores the check for a secure device
        @type serialno: str
        @param serialno: The device or emulator serial number

        @return: the device and serialno used for the connection
        '''

        progname = os.path.basename(sys.argv[0])
        if serialno is None:
            # eat all the extra options the invoking script may have added
            args = sys.argv
            while len(args) > 1 and args[1][0] == '-':
                args.pop(1)
            serialno = args[1] if len(args) > 1 else \
                    os.environ['ANDROID_SERIAL'] if os.environ.has_key('ANDROID_SERIAL') \
                    else '.*'
        if IP_RE.match(serialno):
            # If matches an IP address format and port was not specified add the default
            serialno += ':%d' % ADB_DEFAULT_PORT
        if verbose:
            print >> sys.stderr, 'Connecting to a device with serialno=%s with a timeout of %d secs...' % \
                (serialno, timeout)
        ViewClient.setAlarm(timeout+5)
        device = adbclient.AdbClient(serialno)
        ViewClient.setAlarm(0)
        if verbose:
            print >> sys.stderr, 'Connected to device with serialno=%s' % serialno
        secure = device.getSystemProperty('ro.secure')
        debuggable = device.getSystemProperty('ro.debuggable')
        versionProperty = device.getProperty(VERSION_SDK_PROPERTY)
        if versionProperty:
            version = int(versionProperty)
        else:
            if verbose:
                print "Couldn't obtain device SDK version"
            version = -1

        # we are going to use UiAutomator for versions >= 16 that's why we ignore if the device
        # is secure if this is true
        if secure == '1' and debuggable == '0' and not ignoresecuredevice and version < 16:
            print >> sys.stderr, "%s: ERROR: Device is secure, AndroidViewClient won't work." % progname
            if verbose:
                print >> sys.stderr, "    secure=%s debuggable=%s version=%d ignoresecuredevice=%s" % \
                    (secure, debuggable, version, ignoresecuredevice)
            sys.exit(2)
        if re.search("[.*()+]", serialno) and not re.search("(\d{1,3}\.){3}\d{1,3}", serialno):
            # if a regex was used we have to determine the serialno used
            serialno = ViewClient.__obtainDeviceSerialNumber(device)
        if verbose:
            print >> sys.stderr, 'Actual device serialno=%s' % serialno
        return device, serialno

    @staticmethod
    def traverseShowClassIdAndText(view, extraInfo=None, noextrainfo=None):
        '''
        Shows the View class, id and text if available.
        This function can be used as a transform function to L{ViewClient.traverse()}

        @type view: I{View}
        @param view: the View
        @type extraInfo: method
        @param extraInfo: the View method to add extra info
        @type noextrainfo: bool
        @param noextrainfo: Don't add extra info

        @return: the string containing class, id, and text if available
        '''

        try:
            eis = ''
            if extraInfo:
                eis = extraInfo(view).__str__()
                if not eis and noextrainfo:
                    eis = noextrainfo
            if eis:
                eis = ' ' + eis
            return "%s %s %s%s" % (view.getClass(), view.getId(), view.getText(), eis)
        except Exception, e:
            return "Exception in view=%s: %s" % (view.__smallStr__(), e)

    @staticmethod
    def traverseShowClassIdTextAndUniqueId(view):
        '''
        Shows the View class, id, text if available and unique id.
        This function can be used as a transform function to L{ViewClient.traverse()}

        @type view: I{View}
        @param view: the View
        @return: the string containing class, id, and text if available and unique Id
        '''

        return ViewClient.traverseShowClassIdAndText(view, View.getUniqueId)

    @staticmethod
    def traverseShowClassIdTextAndContentDescription(view):
        '''
        Shows the View class, id, text if available and unique id.
        This function can be used as a transform function to L{ViewClient.traverse()}

        @type view: I{View}
        @param view: the View
        @return: the string containing class, id, and text if available and the content description
        '''

        return ViewClient.traverseShowClassIdAndText(view, View.getContentDescription, 'NAF')

    @staticmethod
    def traverseShowClassIdTextAndCenter(view):
        '''
        Shows the View class, id and text if available.
        This function can be used as a transform function to L{ViewClient.traverse()}

        @type view: I{View}
        @param view: the View
        @return: the string containing class, id, and text if available
        '''

        return ViewClient.traverseShowClassIdAndText(view, View.getCenter)

    @staticmethod
    def traverseShowClassIdTextPositionAndSize(view):
        '''
        Shows the View class, id and text if available.
        This function can be used as a transform function to L{ViewClient.traverse()}

        @type view: I{View}
        @param view: the View
        @return: the string containing class, id, and text if available
        '''

        return ViewClient.traverseShowClassIdAndText(view, View.getPositionAndSize)

    # methods that can be used to transform ViewClient.traverse output
    TRAVERSE_CIT = traverseShowClassIdAndText
    ''' An alias for L{traverseShowClassIdAndText(view)} '''
    TRAVERSE_CITUI = traverseShowClassIdTextAndUniqueId
    ''' An alias for L{traverseShowClassIdTextAndUniqueId(view)} '''
    TRAVERSE_CITCD = traverseShowClassIdTextAndContentDescription
    ''' An alias for L{traverseShowClassIdTextAndContentDescription(view)} '''
    TRAVERSE_CITC = traverseShowClassIdTextAndCenter
    ''' An alias for L{traverseShowClassIdTextAndCenter(view)} '''
    TRAVERSE_CITPS = traverseShowClassIdTextPositionAndSize
    ''' An alias for L{traverseShowClassIdTextPositionAndSize(view)} '''

    @staticmethod
    def sleep(secs=1.0):
        '''
        Sleeps for the specified number of seconds.

        @type secs: float
        @param secs: number of seconds
        '''
        time.sleep(secs)

    def assertServiceResponse(self, response):
        '''
        Checks whether the response received from the server is correct or raises and Exception.

        @type response: str
        @param response: Response received from the server

        @raise Exception: If the response received from the server is invalid
        '''

        if not self.serviceResponse(response):
            raise Exception('Invalid response received from service.')

    def serviceResponse(self, response):
        '''
        Checks the response received from the I{ViewServer}.

        @return: C{True} if the response received matches L{PARCEL_TRUE}, C{False} otherwise
        '''

        PARCEL_TRUE = "Result: Parcel(00000000 00000001   '........')\r\n"
        ''' The TRUE response parcel '''
        if DEBUG:
            print >>sys.stderr, "serviceResponse: comparing '%s' vs Parcel(%s)" % (response, PARCEL_TRUE)
        return response == PARCEL_TRUE

    def setViews(self, received):
        '''
        Sets L{self.views} to the received value splitting it into lines.

        @type received: str
        @param received: the string received from the I{View Server}
        '''

        if not received or received == "":
            raise ValueError("received is empty")
        self.views = []
        ''' The list of Views represented as C{str} obtained after splitting it into lines after being received from the server. Done by L{self.setViews()}. '''
        self.__parseTree(received.split("\n"))
        if DEBUG:
            print >>sys.stderr, "there are %d views in this dump" % len(self.views)

    def setViewsFromUiAutomatorDump(self, received):
        '''
        Sets L{self.views} to the received value parsing the received XML.

        @type received: str
        @param received: the string received from the I{UI Automator}
        '''

        if not received or received == "":
            raise ValueError("received is empty")
        self.views = []
        ''' The list of Views represented as C{str} obtained after splitting it into lines after being received from the server. Done by L{self.setViews()}. '''
        self.__parseTreeFromUiAutomatorDump(received)
        if DEBUG:
            print >>sys.stderr, "there are %d views in this dump" % len(self.views)


    def __splitAttrs(self, strArgs):
        '''
        Splits the C{View} attributes in C{strArgs} and optionally adds the view id to the C{viewsById} list.

        Unique Ids
        ==========
        It is very common to find C{View}s having B{NO_ID} as the Id. This turns very difficult to
        use L{self.findViewById()}. To help in this situation this method assigns B{unique Ids}.

        The B{unique Ids} are generated using the pattern C{id/no_id/<number>} with C{<number>} starting
        at 1.

        @type strArgs: str
        @param strArgs: the string containing the raw list of attributes and values

        @return: Returns the attributes map.
        '''

        if self.useUiAutomator:
            raise RuntimeError("This method is not compatible with UIAutomator")
        # replace the spaces in text:mText to preserve them in later split
        # they are translated back after the attribute matches
        textRE = re.compile('%s=%s,' % (self.textProperty, _nd('len')))
        m = textRE.search(strArgs)
        if m:
            __textStart = m.end()
            __textLen = int(m.group('len'))
            __textEnd = m.end() + __textLen
            s1 = strArgs[__textStart:__textEnd]
            s2 = s1.replace(' ', WS)
            strArgs = strArgs.replace(s1, s2, 1)

        idRE = re.compile("(?P<viewId>id/\S+)")
        attrRE = re.compile('%s(?P<parens>\(\))?=%s,(?P<val>[^ ]*)' % (_ns('attr'), _nd('len')), flags=re.DOTALL)
        hashRE = re.compile('%s@%s' % (_ns('class'), _nh('oid')))

        attrs = {}
        viewId = None
        m = idRE.search(strArgs)
        if m:
            viewId = m.group('viewId')
            if DEBUG:
                print >>sys.stderr, "found view with id=%s" % viewId

        for attr in strArgs.split():
            m = attrRE.match(attr)
            if m:
                __attr = m.group('attr')
                __parens = '()' if m.group('parens') else ''
                __len = int(m.group('len'))
                __val = m.group('val')
                if WARNINGS and __len != len(__val):
                    warnings.warn("Invalid len: expected: %d   found: %d   s=%s   e=%s" % (__len, len(__val), __val[:50], __val[-50:]))
                if __attr == self.textProperty:
                    # restore spaces that have been replaced
                    __val = __val.replace(WS, ' ')
                attrs[__attr + __parens] = __val
            else:
                m = hashRE.match(attr)
                if m:
                    attrs['class'] = m.group('class')
                    attrs['oid'] = m.group('oid')
                else:
                    if DEBUG:
                        print >>sys.stderr, attr, "doesn't match"

        if True: # was assignViewById
            if not viewId:
                # If the view has NO_ID we are assigning a default id here (id/no_id) which is
                # immediately incremented if another view with no id was found before to generate
                # a unique id
                viewId = "id/no_id/1"
            if viewId in self.viewsById:
                # sometimes the view ids are not unique, so let's generate a unique id here
                i = 1
                while True:
                    newId = re.sub('/\d+$', '', viewId) + '/%d' % i
                    if not newId in self.viewsById:
                        break
                    i += 1
                viewId = newId
                if DEBUG:
                    print >>sys.stderr, "adding viewById %s" % viewId
            # We are assigning a new attribute to keep the original id preserved, which could have
            # been NO_ID repeated multiple times
            attrs['uniqueId'] = viewId

        return attrs

    def __parseTree(self, receivedLines):
        '''
        Parses the View tree contained in L{receivedLines}. The tree is created and the root node assigned to L{self.root}.
        This method also assigns L{self.viewsById} values using L{View.getUniqueId} as the key.

        @type receivedLines: str
        @param receivedLines: the string received from B{View Server}
        '''

        self.root = None
        self.viewsById = {}
        self.views = []
        parent = None
        parents = []
        treeLevel = -1
        newLevel = -1
        lastView = None
        for v in receivedLines:
            if v == '' or v == 'DONE' or v == 'DONE.':
                break
            attrs = self.__splitAttrs(v)
            if not self.root:
                if v[0] == ' ':
                    raise Exception("Unexpected root element starting with ' '.")
                self.root = View.factory(attrs, self.device, self.build[VERSION_SDK_PROPERTY], self.forceViewServerUse)
                if DEBUG: self.root.raw = v
                treeLevel = 0
                newLevel = 0
                lastView = self.root
                parent = self.root
                parents.append(parent)
            else:
                newLevel = (len(v) - len(v.lstrip()))
                if newLevel == 0:
                    raise Exception("newLevel==0 treeLevel=%d but tree can have only one root, v=%s" % (treeLevel, v))
                child = View.factory(attrs, self.device, self.build[VERSION_SDK_PROPERTY], self.forceViewServerUse)
                if DEBUG: child.raw = v
                if newLevel == treeLevel:
                    parent.add(child)
                    lastView = child
                elif newLevel > treeLevel:
                    if (newLevel - treeLevel) != 1:
                        raise Exception("newLevel jumps %d levels, v=%s" % ((newLevel-treeLevel), v))
                    parent = lastView
                    parents.append(parent)
                    parent.add(child)
                    lastView = child
                    treeLevel = newLevel
                else: # newLevel < treeLevel
                    for i in range(treeLevel - newLevel):
                        parents.pop()
                    parent = parents.pop()
                    parents.append(parent)
                    parent.add(child)
                    treeLevel = newLevel
                    lastView = child
            self.views.append(lastView)
            self.viewsById[lastView.getUniqueId()] = lastView

    def __parseTreeFromUiAutomatorDump(self, receivedXml):
        parser = UiAutomator2AndroidViewClient(self.device, self.build[VERSION_SDK_PROPERTY])
        self.root = parser.Parse(receivedXml)
        self.views = parser.views
        self.viewsById = {}
        for v in self.views:
            self.viewsById[v.getUniqueId()] = v

    def getRoot(self):
        '''
        Gets the root node of the C{View} tree

        @return: the root node of the C{View} tree
        '''
        return self.root

    def traverse(self, root="ROOT", indent="", transform=View.__str__, stream=sys.stdout):
        '''
        Traverses the C{View} tree and prints its nodes.

        The nodes are printed converting them to string but other transformations can be specified
        by providing a method name as the C{transform} parameter.

        @type root: L{View}
        @param root: the root node from where the traverse starts
        @type indent: str
        @param indent: the indentation string to use to print the nodes
        @type transform: method
        @param transform: a method to use to transform the node before is printed
        '''

        if type(root) == types.StringType and root == "ROOT":
            root = self.root

        return ViewClient.__traverse(root, indent, transform, stream)
#         if not root:
#             return
#
#         s = transform(root)
#         if s:
#             print >>stream, "%s%s" % (indent, s)
#
#         for ch in root.children:
#             self.traverse(ch, indent=indent+"   ", transform=transform, stream=stream)

    @staticmethod
    def __traverse(root, indent="", transform=View.__str__, stream=sys.stdout):
        if not root:
            return

        s = transform(root)
        if s:
            ius = "%s%s" % (indent, s if isinstance(s, unicode) else unicode(s, 'utf-8', 'replace'))
            print >>stream, ius.encode('utf-8', 'replace')

        for ch in root.children:
            ViewClient.__traverse(ch, indent=indent+"   ", transform=transform, stream=stream)

    def dump(self, window=-1, sleep=1):
        '''
        Dumps the window content.

        Sleep is useful to wait some time before obtaining the new content when something in the
        window has changed.

        @type window: int or str
        @param window: the window id or name of the window to dump.
                    The B{name} is the package name or the window name (i.e. StatusBar) for
                    system windows.
                    The window id can be provided as C{int} or C{str}. The C{str} should represent
                    and C{int} in either base 10 or 16.
                    Use -1 to dump all windows.
                    This parameter only is used when the backend is B{ViewServer} and it's
                    ignored for B{UiAutomator}.
        @type sleep: int
        @param sleep: sleep in seconds before proceeding to dump the content

        @return: the list of Views as C{str} received from the server after being split into lines
        '''

        if sleep > 0:
            time.sleep(sleep)

        if self.useUiAutomator:
            # NOTICE:
            # Using /dev/tty this works even on devices with no sdcard
            received = unicode(self.device.shell('uiautomator dump /dev/tty >/dev/null'), encoding='utf-8', errors='replace')
            if not received:
                raise RuntimeError('ERROR: Empty UiAutomator dump was received')
            if DEBUG:
                self.received = received
            if DEBUG_RECEIVED:
                print >>sys.stderr, "received %d chars" % len(received)
                print >>sys.stderr
                print >>sys.stderr, repr(received)
                print >>sys.stderr
            onlyKilledRE = re.compile('[\n\S]*Killed[\n\r\S]*', re.MULTILINE)
            if onlyKilledRE.search(received):
                raise RuntimeError('''ERROR: UiAutomator output contains no valid information. UiAutomator was killed, no reason given.''')
            if self.ignoreUiAutomatorKilled:
                if DEBUG_RECEIVED:
                    print >>sys.stderr, "ignoring UiAutomator Killed"
                killedRE = re.compile('</hierarchy>[\n\S]*Killed', re.MULTILINE)
                if killedRE.search(received):
                    received = re.sub(killedRE, '</hierarchy>', received)
                elif DEBUG_RECEIVED:
                    print "UiAutomator Killed: NOT FOUND!"
                # It seems that API18 uiautomator spits this message to stdout
                dumpedToDevTtyRE = re.compile('</hierarchy>[\n\S]*UI hierchary dumped to: /dev/tty.*', re.MULTILINE)
                if dumpedToDevTtyRE.search(received):
                    received = re.sub(dumpedToDevTtyRE, '</hierarchy>', received)
                # API19 seems to send this warning as part of the XML.
                # Let's remove it if present
                received = received.replace('WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.\r\n', '')
                if DEBUG_RECEIVED:
                    print >>sys.stderr, "received=", received
            if re.search('\[: not found', received):
                raise RuntimeError('''ERROR: Some emulator images (i.e. android 4.1.2 API 16 generic_x86) does not include the '[' command.
While UiAutomator back-end might be supported 'uiautomator' command fails.
You should force ViewServer back-end.''')
            self.setViewsFromUiAutomatorDump(received)
        else:
            if isinstance(window, str):
                if window != '-1':
                    self.list(sleep=0)
                    found = False
                    for wId in self.windows:
                        try:
                            if window == self.windows[wId]:
                                window = wId
                                found = True
                                break
                        except:
                            pass
                        try:
                            if int(window) == wId:
                                window = wId
                                found = True
                                break
                        except:
                            pass
                        try:
                            if int(window, 16) == wId:
                                window = wId
                                found = True
                                break
                        except:
                            pass

                    if not found:
                        raise RuntimeError("ERROR: Cannot find window '%s' in %s" % (window, self.windows))
                else:
                    window = -1

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((VIEW_SERVER_HOST, self.localPort))
            except socket.error, ex:
                raise RuntimeError("ERROR: Connecting to %s:%d: %s" % (VIEW_SERVER_HOST, self.localPort, ex))
            cmd = 'dump %x\r\n' % window
            if DEBUG:
                print >>sys.stderr, "executing: '%s'" % cmd
            s.send(cmd)
            received = ""
            doneRE = re.compile("DONE")
            ViewClient.setAlarm(120)
            while True:
                if DEBUG_RECEIVED:
                    print >>sys.stderr, "    reading from socket..."
                received += s.recv(1024)
                if doneRE.search(received[-7:]):
                    break
            s.close()
            ViewClient.setAlarm(0)
            if DEBUG:
                self.received = received
            if DEBUG_RECEIVED:
                print >>sys.stderr, "received %d chars" % len(received)
                print >>sys.stderr
                print >>sys.stderr, received
                print >>sys.stderr
            self.setViews(received)

            if DEBUG_TREE:
                self.traverse(self.root)

        return self.views

    def list(self, sleep=1):
        '''
        List the windows.

        Sleep is useful to wait some time before obtaining the new content when something in the
        window has changed.
        This also sets L{self.windows} as the list of windows.

        @type sleep: int
        @param sleep: sleep in seconds before proceeding to dump the content

        @return: the list of windows
        '''

        if sleep > 0:
            time.sleep(sleep)

        if self.useUiAutomator:
            raise Exception("Not implemented yet: listing windows with UiAutomator")
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((VIEW_SERVER_HOST, self.localPort))
            except socket.error, ex:
                raise RuntimeError("ERROR: Connecting to %s:%d: %s" % (VIEW_SERVER_HOST, self.localPort, ex))
            s.send('list\r\n')
            received = ""
            doneRE = re.compile("DONE")
            while True:
                received += s.recv(1024)
                if doneRE.search(received[-7:]):
                    break
            s.close()
            if DEBUG:
                self.received = received
            if DEBUG_RECEIVED:
                print >>sys.stderr, "received %d chars" % len(received)
                print >>sys.stderr
                print >>sys.stderr, received
                print >>sys.stderr

            self.windows = {}
            for line in received.split('\n'):
                if not line:
                    break
                if doneRE.search(line):
                    break
                values = line.split()
                if len(values) > 1:
                    package = values[1]
                else:
                    package = "UNKNOWN"
                if len(values) > 0:
                    wid = values[0]
                else:
                    wid = '00000000'
                self.windows[int('0x' + wid, 16)] = package
            return self.windows


    def findViewById(self, viewId, root="ROOT", viewFilter=None):
        '''
        Finds the View with the specified viewId.

        @type viewId: str
        @param viewId: the ID of the view to find
        @type root: str
        @type root: View
        @param root: the root node of the tree where the View will be searched
        @type: viewFilter: function
        @param viewFilter: a function that will be invoked providing the candidate View as a parameter
                           and depending on the return value (C{True} or C{False}) the View will be
                           selected and returned as the result of C{findViewById()} or ignored.
                           This can be C{None} and no extra filtering is applied.

        @return: the C{View} found or C{None}
        '''

        if not root:
            return None

        if type(root) == types.StringType and root == "ROOT":
            return self.findViewById(viewId, self.root, viewFilter)

        if root.getId() == viewId:
            if viewFilter:
                if viewFilter(root):
                    return root
            else:
                return root

        if re.match('^id/no_id', viewId) or re.match('^id/.+/.+', viewId):
            if root.getUniqueId() == viewId:
                if viewFilter:
                    if viewFilter(root):
                        return root;
                else:
                    return root


        for ch in root.children:
            foundView = self.findViewById(viewId, ch, viewFilter)
            if foundView:
                if viewFilter:
                    if viewFilter(foundView):
                        return foundView
                else:
                    return foundView

    def findViewByIdOrRaise(self, viewId, root="ROOT", viewFilter=None):
        '''
        Finds the View or raise a ViewNotFoundException.

        @type viewId: str
        @param viewId: the ID of the view to find
        @type root: str
        @type root: View
        @param root: the root node of the tree where the View will be searched
        @type: viewFilter: function
        @param viewFilter: a function that will be invoked providing the candidate View as a parameter
                           and depending on the return value (C{True} or C{False}) the View will be
                           selected and returned as the result of C{findViewById()} or ignored.
                           This can be C{None} and no extra filtering is applied.
        @return: the View found
        @raise ViewNotFoundException: raise the exception if View not found
        '''

        view = self.findViewById(viewId, root, viewFilter)
        if view:
            return view
        else:
            raise ViewNotFoundException("ID", viewId, root)

    def findViewByTag(self, tag, root="ROOT"):
        '''
        Finds the View with the specified tag
        '''

        return self.findViewWithAttribute('getTag()', tag, root)

    def findViewByTagOrRaise(self, tag, root="ROOT"):
        '''
        Finds the View with the specified tag or raise a ViewNotFoundException
        '''

        view = self.findViewWithAttribute('getTag()', tag, root)
        if view:
            return view
        else:
            raise ViewNotFoundException("tag", tag, root)

    def __findViewWithAttributeInTree(self, attr, val, root):
        if not self.root:
            print >>sys.stderr, "ERROR: no root, did you forget to call dump()?"
            return None

        if type(root) == types.StringType and root == "ROOT":
            root = self.root

        if DEBUG: print >>sys.stderr, "__findViewWithAttributeInTree: type val=", type(val)
        if DEBUG: print >>sys.stderr, "__findViewWithAttributeInTree: checking if root=%s has attr=%s == %s" % (root.__smallStr__(), attr, val)

        if isinstance(val, RegexType):
            return self.__findViewWithAttributeInTreeThatMatches(attr, val, root)
        else:
            if root and attr in root.map and root.map[attr] == val:
                if DEBUG: print >>sys.stderr, "__findViewWithAttributeInTree:  FOUND: %s" % root.__smallStr__()
                return root
            else:
                for ch in root.children:
                    v = self.__findViewWithAttributeInTree(attr, val, ch)
                    if v:
                        return v

        return None

    def __findViewWithAttributeInTreeOrRaise(self, attr, val, root):
        view = self.__findViewWithAttributeInTree(attr, val, root)
        if view:
            return view
        else:
            raise ViewNotFoundException(attr, val, root)

    def __findViewWithAttributeInTreeThatMatches(self, attr, regex, root, rlist=[]):
        if not self.root:
            print >>sys.stderr, "ERROR: no root, did you forget to call dump()?"
            return None

        if type(root) == types.StringType and root == "ROOT":
            root = self.root

        if DEBUG: print >>sys.stderr, "__findViewWithAttributeInTreeThatMatches: checking if root=%s attr=%s matches %s" % (root.__smallStr__(), attr, regex)

        if root and attr in root.map and regex.match(root.map[attr]):
            if DEBUG: print >>sys.stderr, "__findViewWithAttributeInTreeThatMatches:  FOUND: %s" % root.__smallStr__()
            return root
            #print >>sys.stderr, "appending root=%s to rlist=%s" % (root.__smallStr__(), rlist)
            #return rlist.append(root)
        else:
            for ch in root.children:
                v = self.__findViewWithAttributeInTreeThatMatches(attr, regex, ch, rlist)
                if v:
                    return v
                    #print >>sys.stderr, "appending v=%s to rlist=%s" % (v.__smallStr__(), rlist)
                    #return rlist.append(v)

        return None
        #return rlist

    def findViewWithAttribute(self, attr, val, root="ROOT"):
        '''
        Finds the View with the specified attribute and value
        '''

        return self.__findViewWithAttributeInTree(attr, val, root)

    def findViewWithAttributeOrRaise(self, attr, val, root="ROOT"):
        '''
        Finds the View or raise a ViewNotFoundException.

        @return: the View found
        @raise ViewNotFoundException: raise the exception if View not found
        '''

        view = self.findViewWithAttribute(attr, val, root)
        if view:
            return view
        else:
            raise ViewNotFoundException(attr, val, root)

    def findViewWithAttributeThatMatches(self, attr, regex, root="ROOT"):
        '''
        Finds the list of Views with the specified attribute matching
        regex
        '''

        return self.__findViewWithAttributeInTreeThatMatches(attr, regex, root)

    def findViewWithText(self, text, root="ROOT"):
        if DEBUG:
            print >>sys.stderr, "findViewWithText(%s, %s)" % (text, root)
        if isinstance(text, RegexType):
            return self.findViewWithAttributeThatMatches(self.textProperty, text, root)
            #l = self.findViewWithAttributeThatMatches(TEXT_PROPERTY, text)
            #ll = len(l)
            #if ll == 0:
            #    return None
            #elif ll == 1:
            #    return l[0]
            #else:
            #    print >>sys.stderr, "WARNING: findViewWithAttributeThatMatches invoked by findViewWithText returns %d items." % ll
            #    return l
        else:
            return self.findViewWithAttribute(self.textProperty, text, root)

    def findViewWithTextOrRaise(self, text, root="ROOT"):
        '''
        Finds the View or raise a ViewNotFoundException.

        @return: the View found
        @raise ViewNotFoundException: raise the exception if View not found
        '''

        if DEBUG:
            print >>sys.stderr, "findViewWithTextOrRaise(%s, %s)" % (text, root)
        view = self.findViewWithText(text, root)
        if view:
            return view
        else:
            raise ViewNotFoundException("text", text, root)

    def findViewWithContentDescription(self, contentdescription, root="ROOT"):
        '''
        Finds the View with the specified content description
        '''

        return self.__findViewWithAttributeInTree('content-desc', contentdescription, root)

    def findViewWithContentDescriptionOrRaise(self, contentdescription, root="ROOT"):
        '''
        Finds the View with the specified content description
        '''

        return self.__findViewWithAttributeInTreeOrRaise('content-desc', contentdescription, root)

    def findViewsContainingPoint(self, (x, y), filter=None):
        '''
        Finds the list of Views that contain the point (x, y).
        '''

        if not filter:
            filter = lambda v: True

        return [v for v in self.views if (v.containsPoint((x,y)) and filter(v))]

    def getViewIds(self):
        '''
        @deprecated: Use L{getViewsById} instead.

        Returns the Views map.
        '''

        return self.viewsById

    def getViewsById(self):
        '''
        Returns the Views map. The keys are C{uniqueIds} and the values are C{View}s.
        '''

        return self.viewsById

    def __getFocusedWindowPosition(self):
        return self.__getFocusedWindowId()

    def getSdkVersion(self):
        '''
        Gets the SDK version.
        '''

        return self.build[VERSION_SDK_PROPERTY]

    def isKeyboardShown(self):
        '''
        Whether the keyboard is displayed.
        '''

        dim = self.device.shell('dumpsys input_method')
        if dim:
            # FIXME: API >= 15 ?
            return "mInputShown=true" in dim
        return False

    def writeImageToFile(self, filename, format="PNG"):
        '''
        Write the View image to the specified filename in the specified format.

        @type filename: str
        @param filename: Absolute path and optional filename receiving the image. If this points to
                         a directory, then the filename is determined by the serialno of the device and
                         format extension.
        @type format: str
        @param format: Image format (default format is PNG)
        '''

        if not os.path.isabs(filename):
            raise ValueError("writeImageToFile expects an absolute path")
        if os.path.isdir(filename):
            filename = os.path.join(filename, self.serialno + '.' + format.lower())
        if DEBUG:
            print >> sys.stderr, "writeImageToFile: saving image to '%s' in %s format" % (filename, format)
        self.device.takeSnapshot().save(filename, format)

    @staticmethod
    def __pickleable(tree):
        '''
        Makes the tree pickleable.
        '''

        def removeDeviceReference(view):
            '''
            Removes the reference to a L{MonkeyDevice}.
            '''

            view.device = None

        ###########################################################################################
        # FIXME: Unfortunatelly deepcopy does not work with MonkeyDevice objects, which is
        # sadly the reason why we cannot pickle the tree and we need to remove the MonkeyDevice
        # references.
        # We wanted to copy the tree to preserve the original and make piclkleable the copy.
        #treeCopy = copy.deepcopy(tree)
        treeCopy = tree
        # IMPORTANT:
        # This assumes that the first element in the list is the tree root
        ViewClient.__traverse(treeCopy[0], transform=removeDeviceReference)
        ###########################################################################################
        return treeCopy

    def distance(self, tree):
        '''
        Calculates the distance between this tree and the tree passed as argument.

        @type tree: list of Views
        @param tree: Tree of Views
        @return: the distance
        '''
        ################################################################
        #FIXME: this should copy the entire tree and then transform it #
        ################################################################
        pickleableViews = ViewClient.__pickleable(self.views)
        pickleableTree = ViewClient.__pickleable(tree)
        s1 = pickle.dumps(pickleableViews)
        s2 = pickle.dumps(pickleableTree)

        if DEBUG_DISTANCE:
            print >>sys.stderr, "distance: calculating distance between", s1[:20], "and", s2[:20]

        l1 = len(s1)
        l2 = len(s2)
        t = float(max(l1, l2))

        if l1 == l2:
            if DEBUG_DISTANCE:
                print >>sys.stderr, "distance: trees have same length, using Hamming distance"
            return ViewClient.__hammingDistance(s1, s2)/t
        else:
            if DEBUG_DISTANCE:
                print >>sys.stderr, "distance: trees have different length, using Levenshtein distance"
            return ViewClient.__levenshteinDistance(s1, s2)/t

    @staticmethod
    def __hammingDistance(s1, s2):
        '''
        Finds the Hamming distance between two strings.

        @param s1: string
        @param s2: string
        @return: the distance
        @raise ValueError: if the lenght of the strings differ
        '''

        l1 = len(s1)
        l2 = len(s2)

        if l1 != l2:
            raise ValueError("Hamming distance requires strings of same size.")

        return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))

    def hammingDistance(self, tree):
        '''
        Finds the Hamming distance between this tree and the one passed as argument.
        '''

        s1 = ' '.join(map(View.__str__, self.views))
        s2 = ' '.join(map(View.__str__, tree))

        return ViewClient.__hammingDistance(s1, s2)

    @staticmethod
    def __levenshteinDistance(s, t):
        '''
        Find the Levenshtein distance between two Strings.

        Python version of Levenshtein distance method implemented in Java at
        U{http://www.java2s.com/Code/Java/Data-Type/FindtheLevenshteindistancebetweentwoStrings.htm}.

        This is the number of changes needed to change one String into
        another, where each change is a single character modification (deletion,
        insertion or substitution).

        The previous implementation of the Levenshtein distance algorithm
        was from U{http://www.merriampark.com/ld.htm}

        Chas Emerick has written an implementation in Java, which avoids an OutOfMemoryError
        which can occur when my Java implementation is used with very large strings.
        This implementation of the Levenshtein distance algorithm
        is from U{http://www.merriampark.com/ldjava.htm}::

            StringUtils.getLevenshteinDistance(null, *)             = IllegalArgumentException
            StringUtils.getLevenshteinDistance(*, null)             = IllegalArgumentException
            StringUtils.getLevenshteinDistance("","")               = 0
            StringUtils.getLevenshteinDistance("","a")              = 1
            StringUtils.getLevenshteinDistance("aaapppp", "")       = 7
            StringUtils.getLevenshteinDistance("frog", "fog")       = 1
            StringUtils.getLevenshteinDistance("fly", "ant")        = 3
            StringUtils.getLevenshteinDistance("elephant", "hippo") = 7
            StringUtils.getLevenshteinDistance("hippo", "elephant") = 7
            StringUtils.getLevenshteinDistance("hippo", "zzzzzzzz") = 8
            StringUtils.getLevenshteinDistance("hello", "hallo")    = 1

        @param s:  the first String, must not be null
        @param t:  the second String, must not be null
        @return: result distance
        @raise ValueError: if either String input C{null}
        '''
        if s is None or t is None:
            raise ValueError("Strings must not be null")

        n = len(s)
        m = len(t)

        if n == 0:
            return m
        elif m == 0:
            return n

        if n > m:
            tmp = s
            s = t
            t = tmp
            n = m;
            m = len(t)

        p = [None]*(n+1)
        d = [None]*(n+1)

        for i in range(0, n+1):
            p[i] = i

        for j in range(1, m+1):
            if DEBUG_DISTANCE:
                if j % 100 == 0:
                    print >>sys.stderr, "DEBUG:", int(j/(m+1.0)*100),"%\r",
            t_j = t[j-1]
            d[0] = j

            for i in range(1, n+1):
                cost = 0 if s[i-1] == t_j else 1
                #  minimum of cell to the left+1, to the top+1, diagonally left and up +cost
                d[i] = min(min(d[i-1]+1, p[i]+1), p[i-1]+cost)

            _d = p
            p = d
            d = _d

        if DEBUG_DISTANCE:
            print >> sys.stderr, "\n"
        return p[n]

    def levenshteinDistance(self, tree):
        '''
        Finds the Levenshtein distance between this tree and the one passed as argument.
        '''

        s1 = ' '.join(map(View.__microStr__, self.views))
        s2 = ' '.join(map(View.__microStr__, tree))

        return ViewClient.__levenshteinDistance(s1, s2)

    @staticmethod
    def excerpt(str, execute=False):
        code = Excerpt2Code().Parse(str)
        if execute:
            exec code
        else:
            return code


if __name__ == "__main__":
    try:
        vc = ViewClient(None)
    except:
        print "%s: Don't expect this to do anything" % __file__



########NEW FILE########
__FILENAME__ = allTests
#! /usr/bin/env monkeyrunner
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 5, 2012

@author: diego
'''
import unittest
import sys
import os

# This must be imported before MonkeyRunner and MonkeyDevice,
# otherwise the import fails.
# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.environ['ANDROID_VIEW_CLIENT_HOME'])
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass



if __name__ == "__main__":
    #sys.argv = ['', 'ViewTest.testName']
    import tests.com.dtmilano.android.viewclient
    unittest.main()

########NEW FILE########
__FILENAME__ = adbclient
'''
Created on Aug 6, 2013

@author: diego
'''
import sys
import time
import re
import unittest

from com.dtmilano.android.adb.adbclient import AdbClient

VERBOSE = True

#ANDROIANDROID_SERIAL = 'emulator-5554'

class AdbClientTest(unittest.TestCase):

    androidSerial = None
    ''' The Android device serial number used by default'''

    @classmethod
    def setUpClass(cls):
        # we use 'fakeserialno' and settransport=False so AdbClient does not try to find the
        # serialno in setTransport()
        try:
            adbClient = AdbClient('fakeserialno', settransport=False)
        except RuntimeError, ex:
            if re.search('Connection refused', str(ex)):
                raise RuntimeError("adb is not running")
            raise(ex)
        devices = adbClient.getDevices()
        if len(devices) == 0:
            raise RuntimeError("This tests require at least one device connected. None was found.")
        for device in devices:
            if device.status == 'device':
                cls.androidSerial = device.serialno
                if VERBOSE:
                    print "AdbClientTest: using device %s" % cls.androidSerial
                return
        raise RuntimeError("No on-line devices found")

    def setUp(self):
        self.adbClient = AdbClient(self.androidSerial)
        self.assertIsNotNone(self.adbClient, "adbClient is None")

    def tearDown(self):
        self.adbClient.close()

    def testSerialno_none(self):
        try:
            AdbClient(None)
            self.fail("No exception was generated")
        except ValueError:
            pass

    def testSerialno_nonExistent(self):
        try:
            AdbClient('doesnotexist')
        except RuntimeError, ex:
            self.assertIsNotNone(re.search("ERROR: couldn't find device that matches 'doesnotexist'", str(ex)), "Couldn't find error message: %s" % ex)

    def testSerialno_empty(self):
        try:
            AdbClient('')
            self.fail("No exception was generated")
        except ValueError:
            pass

    def testGetDevices(self):
        # we use 'fakeserialno' and settransport=False so AdbClient does not try to find the
        # serialno in setTransport()
        adbclient = AdbClient('fakeserialno', settransport=False)
        self.assertTrue(len(adbclient.getDevices()) >= 1)

    def testGetDevices_androidSerial(self):
        devs = self.adbClient.getDevices()
        self.assertTrue(self.androidSerial in [d.serialno for d in devs])

    def testGetDevices_regex(self):
        adbclient = AdbClient('.*', settransport=False)
        self.assertTrue(len(adbclient.getDevices()) >= 1)

    #@unittest.skipIf(not re.search('emulator', AdbClientTest.androidSerial), "Supported only when emulator is connected")
    def testAdbClient_serialnoNoRegex(self):
        if re.search('emulator', AdbClientTest.androidSerial):
            adbClient = AdbClient('emulator-5554')
            self.assertIsNotNone(adbClient)
            self.assertEqual('emulator-5554', adbClient.serialno)

    #@unittest.skipIf(not re.search('emulator', AdbClientTest.androidSerial), "Supported only when emulator is connected")
    def testAdbClient_serialnoRegex(self):
        if re.search('emulator', AdbClientTest.androidSerial):
            adbClient = AdbClient('emulator-.*')
            self.assertIsNotNone(adbClient)
            self.assertTrue(re.match('emulator-.*', adbClient.serialno))

    def testCheckVersion(self):
        self.adbClient.checkVersion()

    def testShell(self):
        date = self.adbClient.shell('date +"%Y/%m/%d"')
        # this raises a ValueError if the format is not correct
        time.strptime(date, '%Y/%m/%d\r\n')

    def testShell_noOutput(self):
        empty = self.adbClient.shell('sleep 3')
        self.assertIs('', empty, "Expected empty output but found '%s'" % empty)

    def testGetProp_ro_serialno(self):
        serialno = self.adbClient.getProperty('ro.serialno')
        self.assertIsNotNone(serialno)
        if re.search('emulator-.*', self.androidSerial):
            self.assertEqual(serialno, '')
        else:
            self.assertEqual(serialno, self.androidSerial)

    def testGetProp_ro_kernel_qemu(self):
        qemu = self.adbClient.getProperty('ro.kernel.qemu')
        self.assertIsNotNone(qemu)
        if re.search('emulator-.*', self.androidSerial):
            self.assertEqual(qemu, '1')
        else:
            self.assertEqual(qemu, '')

    def testPress(self):
        self.adbClient.press('KEYCODE_DPAD_UP')

    def testTouch(self):
        self.adbClient.touch(480, 1250)

    def testType(self):
        self.adbClient.type('Android is cool')

    def testType_digits(self):
        self.adbClient.type('1234')

    def testType_digits_asInt(self):
        self.adbClient.type(1234)

    def testStartActivity_component(self):
        self.adbClient.startActivity('com.example.i2at.tc/.TemperatureConverterActivity')

    def testStartActivity_uri(self):
        self.adbClient.startActivity(uri='http://www.google.com')

    #@unittest.skip("sequence")
    def testCommandsSequence(self):
        self.adbClient.setReconnect(True)
        if VERBOSE:
            print "Sending touch(480, 800)"
        self.adbClient.touch(480, 800)
        self.assertTrue(self.adbClient.checkConnected())
        if VERBOSE:
            print "Typing 'command 1'"
        self.adbClient.type("command 1")
        self.assertTrue(self.adbClient.checkConnected())
        if VERBOSE:
            print "Typing 'command 2'"
        self.adbClient.type("command 2")
        self.assertTrue(self.adbClient.checkConnected())
        if VERBOSE:
            print "Pressing ENTER"
        self.adbClient.press('KEYCODE_ENTER')
        self.assertTrue(self.adbClient.checkConnected())

    #def testWake(self):
    #    self.adbClient.wake()

if __name__ == "__main__":
    #print >> sys.stderr, "sys.path=", sys.path
    #sys.argv = ['', 'AdbClientTest']
    unittest.main()
########NEW FILE########
__FILENAME__ = mocks
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 6, 2012

@author: diego
'''

import re

DEBUG = True

TRUE_PARCEL = "Result: Parcel(00000000 00000001   '........')\r\n"
FALSE_PARCEL = "Result: Parcel(00000000 00000000   '........')\r\n"

DUMP = """\
com.android.internal.policy.impl.PhoneWindow$DecorView@412a9d08 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,800 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2122315464 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,800 layout:getLayoutDirection()=7,INHERIT layout_horizontalWeight=3,0.0 layout_flags_FLAG_LAYOUT_IN_SCREEN=5,0x100 layout_flags_FLAG_LAYOUT_INSET_DECOR=7,0x10000 layout_flags_FLAG_SPLIT_TOUCH=8,0x800000 layout_flags_FLAG_HARDWARE_ACCELERATED=9,0x1000000 layout_flags=8,25231616 layout_type=21,TYPE_BASE_APPLICATION layout_verticalWeight=3,0.0 layout_x=1,0 layout_y=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
 android.widget.LinearLayout@412aaaf8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=3,800 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=2,38 measurement:mMeasuredHeight=3,800 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830334 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,800 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  com.android.internal.widget.ActionBarContainer@412ab6e0 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=23,id/action_bar_container layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,38 layout:mBottom=3,110 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   com.android.internal.widget.ActionBarView@412abdf0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=13,id/action_bar layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.LinearLayout@412b7498 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,140 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,140 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,24 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,72 layout:mLeft=2,61 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704080 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,201 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,24 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744813920 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,140 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@412b8158 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,id/up layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=2,19 layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.LinearLayout@412b84b8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=2,37 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,116 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,37 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,116 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,17 layout:mBottom=2,54 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,37 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=2,19 layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,116 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@412b89a8 text:mText=8,TrashCan getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,116 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,37 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=19,id/action_bar_title layout:mRight=3,116 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,37 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,29 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,37 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,116 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@412b97a0 text:mText=0, getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128605152 text:mResolvedTextDirection=12,FIRST_STRONG mID=22,id/action_bar_subtitle layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,8 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,-4 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.internal.widget.ActionBarView$HomeView@412b40e8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=2,48 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,72 layout:mLeft=2,13 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704080 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=2,61 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744813920 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@412b5758 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,24 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,24 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130691040 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,id/up layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=3,-11 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ImageView@412b5ad8 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,36 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,48 layout:mLeft=1,6 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=7,id/home layout:mRight=2,42 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,12 layout:mBottom=2,60 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=2,12 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=2,12 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,12 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,36 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.internal.view.menu.ActionMenuView@412c27c8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=5,false measurement:mOrientation=1,0 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=3,480 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128606160 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,36 layout:mBottom=2,36 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   com.android.internal.widget.ActionBarContextView@412b9f28 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120215264 text:mResolvedTextDirection=12,FIRST_STRONG mID=21,id/action_context_bar layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830328 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  android.widget.FrameLayout@412ba620 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=2,55 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,690 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/content layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,110 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,690 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,0 layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   android.widget.LinearLayout@412bb588 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=3,690 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,690 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,690 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,690 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.Button@412bba70 text:mText=1,1 getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=2,72 measurement:mMinWidth=2,96 padding:mPaddingBottom=2,12 padding:mPaddingLeft=2,18 padding:mPaddingRight=2,18 padding:mPaddingTop=2,12 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/button1 layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,72 padding:mUserPaddingBottom=2,12 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,18 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,18 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,46 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.Button@412bc610 text:mText=1,2 getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=2,72 measurement:mMinWidth=2,96 padding:mPaddingBottom=2,12 padding:mPaddingLeft=2,18 padding:mPaddingRight=2,18 padding:mPaddingTop=2,12 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/button2 layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,72 layout:mBottom=3,144 padding:mUserPaddingBottom=2,12 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,18 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,18 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,46 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.Button@412bd078 text:mText=1,3 getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=2,72 measurement:mMinWidth=2,96 padding:mPaddingBottom=2,12 padding:mPaddingLeft=2,18 padding:mPaddingRight=2,18 padding:mPaddingTop=2,12 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/button3 layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,144 layout:mBottom=3,216 padding:mUserPaddingBottom=2,12 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,18 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,18 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,46 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.Button@412bdae0 text:mText=1,4 getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=2,72 measurement:mMinWidth=2,96 padding:mPaddingBottom=2,12 padding:mPaddingLeft=2,18 padding:mPaddingRight=2,18 padding:mPaddingTop=2,12 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/button4 layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,216 layout:mBottom=3,288 padding:mUserPaddingBottom=2,12 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,18 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,18 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,46 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.Button@412be548 text:mText=1,5 getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=2,72 measurement:mMinWidth=2,96 padding:mPaddingBottom=2,12 padding:mPaddingLeft=2,18 padding:mPaddingRight=2,18 padding:mPaddingTop=2,12 measurement:mMeasuredHeight=2,72 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/button5 layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,288 layout:mBottom=3,360 padding:mUserPaddingBottom=2,12 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,18 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,18 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,46 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,72 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.TextView@412beff8 text:mText=11,Medium Text getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=3,480 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,330 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=7,id/info layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,360 layout:mBottom=3,690 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,29 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,330 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
  com.android.internal.widget.ActionBarContainer@412baa00 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 text:mResolvedTextDirection=12,FIRST_STRONG mID=19,id/split_action_bar layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
DONE.
DONE
"""

DUMP_SAMPLE_UI = """\
com.android.internal.policy.impl.PhoneWindow$DecorView@b4784e48 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,752 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2122315464 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,752 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,752 layout:getLayoutDirection()=7,INHERIT layout_horizontalWeight=3,0.0 layout_flags_FLAG_LAYOUT_IN_SCREEN=5,0x100 layout_flags_FLAG_LAYOUT_INSET_DECOR=7,0x10000 layout_flags_FLAG_SPLIT_TOUCH=8,0x800000 layout_flags_FLAG_HARDWARE_ACCELERATED=9,0x1000000 layout_flags=8,25231616 layout_type=21,TYPE_BASE_APPLICATION layout_verticalWeight=3,0.0 layout_x=1,0 layout_y=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
 android.widget.LinearLayout@b47b13f0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=3,752 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,752 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,752 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830334 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,752 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  com.android.internal.widget.ActionBarContainer@b47a46a8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=23,id/action_bar_container layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   com.android.internal.widget.ActionBarView@b4776570 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=13,id/action_bar layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.LinearLayout@b477e350 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=2,98 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=2,98 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,16 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=2,65 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704080 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=3,163 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,16 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744813920 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,98 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@b47b9b08 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,id/up layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=2,19 layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.LinearLayout@b47f82f0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=2,25 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=2,82 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,25 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=2,82 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,15 layout:mBottom=2,40 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=2,19 layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,82 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b4722880 text:mText=9,Sample UI getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=2,82 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,25 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=19,id/action_bar_title layout:mRight=2,82 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,25 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,20 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,82 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@b4785130 text:mText=0, getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128605152 text:mResolvedTextDirection=12,FIRST_STRONG mID=22,id/action_bar_subtitle layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,9 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,-2 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.internal.widget.ActionBarView$HomeView@b4777390 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=2,56 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=1,9 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704080 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=2,65 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744813920 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,56 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@b47a0930 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,16 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,16 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130691040 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,id/up layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830456 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=2,-7 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ImageView@b47b7e60 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,48 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,48 layout:mLeft=1,4 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=7,id/home layout:mRight=2,52 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,4 layout:mBottom=2,52 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,4 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,8 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,4 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.internal.view.menu.ActionMenuView@b4727510 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=5,false measurement:mOrientation=1,0 measurement:mTotalLength=2,64 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=2,64 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=4,1216 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,64 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.internal.view.menu.ActionMenuPresenter$OverflowMenuButton@b47cca60 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,64 measurement:mMinHeight=2,56 measurement:mMinWidth=2,64 padding:mPaddingBottom=1,0 padding:mPaddingLeft=2,12 padding:mPaddingRight=2,12 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,56 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=2,64 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,56 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,12 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,12 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744683007 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 layout:getLayoutDirection()=7,INHERIT layout:layout_cellsUsed=1,0 layout:layout_expandable=5,false layout:layout_extraPixels=1,0 layout:layout_isOverflowButton=4,true layout:layout_preventEdgeOffset=5,false layout:layout_gravity=15,CENTER_VERTICAL layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,64 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
   com.android.internal.widget.ActionBarContextView@b47bb880 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120215264 text:mResolvedTextDirection=12,FIRST_STRONG mID=21,id/action_context_bar layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830328 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  android.widget.FrameLayout@b47847a0 drawing:mForeground=52,android.graphics.drawable.NinePatchDrawable@b47b29c0 padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=2,55 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,696 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/content layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,56 layout:mBottom=3,752 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,696 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,0 layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.widget.RelativeLayout@b47cc868 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1280 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,696 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=3,696 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,696 layout:getLayoutDirection()=7,INHERIT layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1280 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.LinearLayout@b4727ca8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=3,419 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=4,1240 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=3,419 layout:mLeft=2,40 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2122314448 text:mResolvedTextDirection=12,FIRST_STRONG mID=17,id/content_layout layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,80 layout:mBottom=3,499 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,419 layout:getLayoutDirection()=7,INHERIT layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,40 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,80 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1240 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ToggleButton@b4728a80 isChecked()=5,false text:mText=12,Button 1 OFF getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1140 measurement:mMinHeight=2,48 measurement:mMinWidth=2,64 padding:mPaddingBottom=1,4 padding:mPaddingLeft=2,12 padding:mPaddingRight=2,12 padding:mPaddingTop=1,4 measurement:mMeasuredHeight=2,48 layout:mLeft=2,50 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1190 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=2,50 layout:mBottom=2,98 padding:mUserPaddingBottom=1,4 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,12 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,12 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,29 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=2,10 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,50 layout:layout_rightMargin=2,50 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,50 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=7,button1 getVisibility()=7,VISIBLE layout:getWidth()=4,1140 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.TextView@b472d690 text:mText=37,(50.0,50.0) (90,186) (90,186) (40,80) getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1240 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,25 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=12,id/textView1 layout:mRight=4,1240 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,108 layout:mBottom=3,133 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,20 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1240 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ToggleButton@b477da08 isChecked()=5,false text:mText=12,Button 2 OFF getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1140 measurement:mMinHeight=2,48 measurement:mMinWidth=2,64 padding:mPaddingBottom=1,4 padding:mPaddingLeft=2,12 padding:mPaddingRight=2,12 padding:mPaddingTop=1,4 measurement:mMeasuredHeight=2,48 layout:mLeft=2,50 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=5,NO_ID layout:mRight=4,1190 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,183 layout:mBottom=3,231 padding:mUserPaddingBottom=1,4 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,12 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,12 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,29 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=2,10 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,50 layout:layout_rightMargin=2,50 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,50 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=7,button2 getVisibility()=7,VISIBLE layout:getWidth()=4,1140 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.TextView@b477e678 text:mText=38,(50.0,183.0) (90,319) (90,319) (40,80) getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1240 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,25 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=12,id/textView2 layout:mRight=4,1240 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,241 layout:mBottom=3,266 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,20 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1240 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ToggleButton@b4781818 isChecked()=5,false text:mText=14,Button with ID getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1140 measurement:mMinHeight=2,48 measurement:mMinWidth=2,64 padding:mPaddingBottom=1,4 padding:mPaddingLeft=2,12 padding:mPaddingRight=2,12 padding:mPaddingTop=1,4 measurement:mMeasuredHeight=2,48 layout:mLeft=2,50 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=17,id/button_with_id layout:mRight=4,1190 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,316 layout:mBottom=3,364 padding:mUserPaddingBottom=1,4 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=2,12 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=2,12 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744814079 layout:getBaseline()=2,29 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=2,10 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,50 layout:layout_rightMargin=2,50 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,50 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1140 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.TextView@b477c2f8 text:mText=38,(50.0,316.0) (90,452) (90,452) (40,80) getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMeasuredWidth=4,1240 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,25 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=12,id/textView3 layout:mRight=4,1240 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=3,374 layout:mBottom=3,399 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830464 layout:getBaseline()=2,20 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=2,20 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=4,1240 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.ZoomControls@b477ec78 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,158 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 drawing:mDrawLayers=4,true focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMeasuredWidth=3,158 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,48 layout:mLeft=4,1122 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703184 text:mResolvedTextDirection=12,FIRST_STRONG mID=7,id/zoom layout:mRight=4,1280 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,48 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1744830336 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=4,true layout:layout_mRules_alignParentRight=4,true layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,158 focus:hasFocus()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ZoomButton@b4784998 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,79 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=2,11 padding:mPaddingLeft=1,4 padding:mPaddingRight=1,0 padding:mPaddingTop=1,7 measurement:mMeasuredHeight=2,48 layout:mLeft=1,0 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=10,id/zoomOut layout:mRight=2,79 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,48 padding:mUserPaddingBottom=2,11 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,4 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1742716927 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,79 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ZoomButton@b4727eb0 layout:getBaseline()=2,-1 measurement:mMeasuredWidth=2,79 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=2,47 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,4 padding:mPaddingTop=1,0 measurement:mMeasuredHeight=2,48 layout:mLeft=2,79 drawing:mLayerType=4,NONE mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 text:mResolvedTextDirection=12,FIRST_STRONG mID=9,id/zoomIn layout:mRight=3,158 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 text:mTextDirection=7,INHERIT layout:mTop=1,0 layout:mBottom=2,48 padding:mUserPaddingBottom=2,47 padding:mUserPaddingEnd=2,-1 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRelative=5,false padding:mUserPaddingRight=1,4 padding:mUserPaddingStart=2,-1 mViewFlags=11,-1742716927 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:getLayoutDirection()=7,INHERIT layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT layout:getResolvedLayoutDirection()=22,RESOLVED_DIRECTION_LTR getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,79 focus:hasFocus()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
DONE.
DONE
"""

DUMP_API_10 = """\
com.android.internal.policy.impl.PhoneWindow$DecorView@4066e808 drawing:mForeground=4,null drawing:mForegroundInPadding=4,true padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=3,800 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,25169208 mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,800 layout_flags_FLAG_LAYOUT_IN_SCREEN=5,0x100 layout_flags=5,65792 layout_type=21,TYPE_BASE_APPLICATION layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=4,true isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
 android.widget.LinearLayout@40667158 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,51 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=3,800 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=2,38 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=3,800 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653314 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,800 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=4,true isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  android.widget.FrameLayout@40676d60 drawing:mForeground=4,null drawing:mForegroundInPadding=4,true padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,2 padding:mPaddingLeft=1,6 padding:mPaddingRight=1,6 padding:mPaddingTop=1,1 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,38 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,25169200 mID=5,NO_ID layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,38 layout:mBottom=2,76 padding:mUserPaddingBottom=1,2 padding:mUserPaddingRight=1,6 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,38 layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=2,38 layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   android.widget.TextView@4063f6d8 mText=8,Settings getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,468 measurement:mMeasuredHeight=2,35 layout:mLeft=1,6 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,474 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,1 layout:mBottom=2,36 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,25 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,35 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,468 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
  android.widget.FrameLayout@40677f28 drawing:mForeground=52,android.graphics.drawable.NinePatchDrawable@406cffd0 drawing:mForegroundInPadding=4,true padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=2,55 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=3,724 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16911408 mID=10,id/content layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,76 layout:mBottom=3,800 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,724 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=1,0 layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=4,true isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.widget.ListView@40666588 list:recycleOnMeasure()=4,true getSelectedView()=4,null isFastScrollEnabled()=5,false isScrollingCacheEnabled()=4,true isSmoothScrollbarEnabled()=4,true isStackFromBottom()=5,false isTextFilterEnabled()=5,false scrolling:mFirstPosition=1,0 list:mNextSelectedPosition=2,-1 list:mSelectedPosition=2,-1 list:mItemCount=2,18 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=5,false isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=3,724 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,18483250 mID=7,id/list layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=3,724 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402940417 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,724 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=4,true isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=4,true focus:isFocused()=4,true isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@406c54c0 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,96 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406ff510 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@40704660 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@406af6c8 mText=19,Wireless & networks getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,303 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,303 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,303 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@406c33b8 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@406a44f8 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,97 layout:mBottom=3,193 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406ae108 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@4063a5d8 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@406e1d48 mText=13,Call settings getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,180 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,180 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,180 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@406f0d20 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@406c0f98 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,194 layout:mBottom=3,290 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406eba90 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@40670c00 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@40702d28 mText=20,CyanogenMod settings getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,337 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,337 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,337 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@40720668 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@406f0368 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,291 layout:mBottom=3,387 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406f0b10 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@406f1780 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@40710e30 mText=11,ADWLauncher getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,209 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,209 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,209 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@406b24c0 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@40700580 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,388 layout:mBottom=3,484 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@40702b18 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@4070c698 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@406d83e8 mText=5,Sound getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,92 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=2,92 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,92 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@40672ce8 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@406dc988 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,485 layout:mBottom=3,581 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406e1998 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@4066cce8 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@406715b8 mText=8,Profiles getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,113 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,113 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,113 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@40673968 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@4069f7b0 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,582 layout:mBottom=3,678 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406a3120 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@40680448 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@4067a4f8 mText=7,Display getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,109 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,109 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,109 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@406a5598 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.LinearLayout@4063ae20 measurement:mBaselineChildTop=1,0 measurement:mGravity=2,19 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,480 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,15 padding:mPaddingTop=1,0 measurement:mMinHeight=2,96 measurement:mMeasuredWidth=3,480 measurement:mMeasuredHeight=2,96 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=15,id/widget_frame layout:mRight=3,480 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=3,679 layout:mBottom=3,775 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=2,15 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,96 list:layout_forceAdd=5,false list:layout_recycledHeaderFooter=5,false list:layout_viewType=21,ITEM_VIEW_TYPE_IGNORE layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,480 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ImageView@406f1990 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=2,48 measurement:mMeasuredHeight=2,48 layout:mLeft=1,9 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780336 mID=7,id/icon layout:mRight=2,57 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,24 layout:mBottom=2,72 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653184 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,9 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=2,48 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.RelativeLayout@40701910 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,387 measurement:mMeasuredHeight=2,44 layout:mLeft=2,69 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16780464 mID=5,NO_ID layout:mRight=3,456 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=2,26 layout:mBottom=2,70 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653312 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,9 layout:layout_leftMargin=1,3 layout:layout_rightMargin=1,9 layout:layout_topMargin=1,9 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,387 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@406fdc48 mText=19,Location & security getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=3,283 measurement:mMeasuredHeight=2,44 layout:mLeft=1,0 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16779312 mID=8,id/title layout:mRight=3,283 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=2,44 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402657280 layout:getBaseline()=2,35 getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,44 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=7,VISIBLE layout:getWidth()=3,283 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.TextView@40720b90 mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 measurement:mMinHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMeasuredHeight=1,0 layout:mLeft=1,0 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=8,16781312 mID=10,id/summary layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 layout:mTop=1,0 layout:mBottom=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingRight=1,0 mViewFlags=9,402653192 layout:getBaseline()=2,-1 getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=8,id/title layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=8,id/title layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT getTag()=4,null getVisibility()=4,GONE layout:getWidth()=1,0 focus:hasFocus()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isInTouchMode()=4,true drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
DONE.
DONE
"""

VIEW_MAP = {'padding:mUserPaddingRight': '12', 'drawing:getSolidColor()': '0', 'getFilterTouchesWhenObscured()': 'false', 'drawing:isOpaque()': 'false', 'mPrivateFlags_DRAWING_CACHE_INVALID': '0x0', 'focus:isFocusable()': 'true', 'mSystemUiVisibility': '0', 'isSoundEffectsEnabled()': 'true', 'layout:layout_width': 'MATCH_PARENT', 'layout:getWidth()': '1140', 'drawing:isDrawingCacheEnabled()': 'false', 'mPrivateFlags_DRAWN': '0x20', 'text:getSelectionEnd()': '-1', 'getTag()': 'null', 'getEllipsize()': 'null', 'focus:hasFocus()': 'false', 'layout:getResolvedLayoutDirection()': 'RESOLVED_DIRECTION_LTR', 'measurement:mMinWidth': '64', 'padding:mUserPaddingEnd': '-1', 'isFocusableInTouchMode()': 'false', 'text:mTextDirection': 'INHERIT', 'isHovered()': 'false', 'layout:layout_leftMargin': '50', 'layout:layout_endMargin': '-2147483648', 'padding:mPaddingBottom': '4', 'measurement:mMeasuredHeight': '48', 'layout:getLayoutDirection()': 'INHERIT', 'layout:mBottom': '364', 'mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE': '0x0', 'layout:layout_startMargin': '-2147483648', 'class': 'android.widget.ToggleButton', 'text:mText': 'Button with ID', 'padding:mPaddingRight': '12', 'mPrivateFlags': '-2130704336', 'layout:layout_bottomMargin': '10', 'layout:layout_height': 'WRAP_CONTENT', 'uniqueId': 'id/button_with_id', 'focus:isFocused()': 'false', 'measurement:mMeasuredWidth': '1140', 'padding:mUserPaddingRelative': 'false', 'text:getSelectionStart()': '-1', 'mViewFlags': '-1744814079', 'isClickable()': 'true', 'getScrollBarStyle()': 'INSIDE_OVERLAY', 'layout:layout_rightMargin': '50', 'padding:mUserPaddingLeft': '12', 'oid': 'b4781818', 'layout:getBaseline()': '29', 'isEnabled()': 'true', 'isChecked()': 'false', 'drawing:mLayerType': 'NONE', 'drawing:willNotDraw()': 'false', 'layout:mRight': '1190', 'drawing:willNotCacheDrawing()': 'false', 'layout:mTop': '316', 'isHapticFeedbackEnabled()': 'true', 'getVisibility()': 'VISIBLE', 'scrolling:mScrollX': '0', 'text:mResolvedTextDirection': 'FIRST_STRONG', 'isInTouchMode()': 'true', 'padding:mPaddingTop': '4', 'layout:layout_weight': '0.0', 'measurement:mMinHeight': '48', 'mID': 'id/button_with_id', 'layout:layout_topMargin': '50', 'padding:mUserPaddingStart': '-1', 'padding:mPaddingLeft': '12', 'isSelected()': 'false', 'isActivated()': 'false', 'padding:mUserPaddingBottom': '4', 'layout:layout_gravity': 'NONE', 'layout:mLeft': '50', 'layout:isLayoutRtl()': 'false', 'layout:getHeight()': '48', 'scrolling:mScrollY': '0'}

VIEW_MAP_API_8 = {'padding:mUserPaddingRight': '12', 'drawing:getSolidColor()': '0', 'getFilterTouchesWhenObscured()': 'false', 'drawing:isOpaque()': 'false', 'mPrivateFlags_DRAWING_CACHE_INVALID': '0x0', 'focus:isFocusable()': 'true', 'mSystemUiVisibility': '0', 'isSoundEffectsEnabled()': 'true', 'layout:layout_width': 'MATCH_PARENT', 'layout:getWidth()': '1140', 'drawing:isDrawingCacheEnabled()': 'false', 'mPrivateFlags_DRAWN': '0x20', 'text:getSelectionEnd()': '-1', 'getTag()': 'null', 'getEllipsize()': 'null', 'focus:hasFocus()': 'false', 'layout:getResolvedLayoutDirection()': 'RESOLVED_DIRECTION_LTR', 'measurement:mMinWidth': '64', 'padding:mUserPaddingEnd': '-1', 'isFocusableInTouchMode()': 'false', 'text:mTextDirection': 'INHERIT', 'isHovered()': 'false', 'layout:layout_leftMargin': '50', 'layout:layout_endMargin': '-2147483648', 'padding:mPaddingBottom': '4', 'measurement:mMeasuredHeight': '48', 'layout:getLayoutDirection()': 'INHERIT', 'layout:mBottom': '364', 'mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE': '0x0', 'layout:layout_startMargin': '-2147483648', 'class': 'android.widget.ToggleButton', 'text:mText': 'Button with ID', 'padding:mPaddingRight': '12', 'mPrivateFlags': '-2130704336', 'layout:layout_bottomMargin': '10', 'layout:layout_height': 'WRAP_CONTENT', 'uniqueId': 'id/button_with_id', 'focus:isFocused()': 'false', 'measurement:mMeasuredWidth': '1140', 'padding:mUserPaddingRelative': 'false', 'text:getSelectionStart()': '-1', 'mViewFlags': '-1744814079', 'isClickable()': 'true', 'getScrollBarStyle()': 'INSIDE_OVERLAY', 'layout:layout_rightMargin': '50', 'padding:mUserPaddingLeft': '12', 'oid': 'b4781818', 'layout:getBaseline()': '29', 'isEnabled()': 'true', 'isChecked()': 'false', 'drawing:mLayerType': 'NONE', 'drawing:willNotDraw()': 'false', 'layout:mRight': '1190', 'drawing:willNotCacheDrawing()': 'false', 'mTop': '316', 'isHapticFeedbackEnabled()': 'true', 'getVisibility()': 'VISIBLE', 'scrolling:mScrollX': '0', 'text:mResolvedTextDirection': 'FIRST_STRONG', 'isInTouchMode()': 'true', 'padding:mPaddingTop': '4', 'layout:layout_weight': '0.0', 'measurement:mMinHeight': '48', 'mID': 'id/button_with_id', 'layout:layout_topMargin': '50', 'padding:mUserPaddingStart': '-1', 'padding:mPaddingLeft': '12', 'isSelected()': 'false', 'isActivated()': 'false', 'padding:mUserPaddingBottom': '4', 'layout:layout_gravity': 'NONE', 'mLeft': '50', 'layout:isLayoutRtl()': 'false', 'layout:getHeight()': '48', 'scrolling:mScrollY': '0'}

VIEW_MAP_API_17 = {u'clickable': u'true', u'bounds': ((323, 725), (475, 881)), u'enabled': u'true', 'uniqueId': 'id/no_id/33', u'text': u'6', u'selected': u'false', u'scrollable': u'false', u'focused': u'false', u'long-clickable': u'false', u'class': u'android.widget.Button', u'focusable': u'true', u'content-desc': u'', u'package': u'com.android.calculator2', u'checked': u'false', u'password': u'false', u'checkable': u'false', u'index': u'2'}

DUMPSYS_WINDOW_PARTIAL = '''

WINDOW MANAGER LAST ANR (dumpsys window lastanr)
  <no ANR has occurred since boot>

WINDOW MANAGER POLICY STATE (dumpsys window policy)
    mSafeMode=false mSystemReady=true mSystemBooted=true
    mLidState=-1 mLidOpenRotation=-1 mHdmiPlugged=false
    mLastSystemUiFlags=0x400 mResettingSystemUiFlags=0x0 mForceClearedSystemUiFlags=0x0
    mUiMode=1 mDockMode=0 mCarDockRotation=-1 mDeskDockRotation=-1
    mUserRotationMode=0 mUserRotation=0 mAllowAllRotations=0
    mCurrentAppOrientation=5
    mCarDockEnablesAccelerometer=true mDeskDockEnablesAccelerometer=true
    mLidKeyboardAccessibility=0 mLidNavigationAccessibility=0 mLidControlsSleep=false
    mLongPressOnPowerBehavior=-1 mHasSoftInput=true
    mScreenOnEarly=true mScreenOnFully=true mOrientationSensorEnabled=true
    mOverscanScreen=(0,0) 768x1280
    mRestrictedOverscanScreen=(0,0) 768x1184
    mUnrestrictedScreen=(0,0) 768x1280
    mRestrictedScreen=(0,0) 768x1184
    mStableFullscreen=(0,0)-(768,1184)
    mStable=(0,50)-(768,1184)
    mSystem=(0,50)-(768,1184)

'''

DUMPSYS_WINDOW_WINDOWS = """
mock data
mock data
"""

DUMPSYS_WINDOW_WINDOWS_SAMPLE_UI = """WINDOW MANAGER WINDOWS (dumpsys window windows)
  Window #7 Window{b4d250b0 RecentsPanel paused=false}:
    mSession=Session{b4d254d0 uid 1000} mClient=android.os.BinderProxy@b4c60590
    mAttrs=WM.LayoutParams{(0,0)(fillxfill) gr=#53 sim=#31 ty=2014 fl=#820100 fmt=-3 wanim=0x7f0c0008}
    Requested w=480 h=800 mLayoutSeq=20
    mBaseLayer=151000 mSubLayer=0 mAnimLayer=151000+0=151000 mLastLayer=0
    mToken=WindowToken{b4c000b0 token=null}
    mRootToken=WindowToken{b4c000b0 token=null}
    mViewVisibility=0x8 mLastHidden=false mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration=null
    mShownFrame=[0.0,0.0][0.0,0.0]
    mFrame=[0,0][480,800] last=[0,0][0,0]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[0,0][480,800]
    mContentFrame=[0,0][480,800] mVisibleFrame=[0,0][480,800]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=false
  Window #6 Window{b4d27678 StatusBar paused=false}:
    mSession=Session{b4d254d0 uid 1000} mClient=android.os.BinderProxy@b4d27488
    mAttrs=WM.LayoutParams{(0,0)(fillx38) gr=#37 sim=#20 ty=2000 fl=#800048 fmt=4 wanim=0x7f0c0009}
    Requested w=480 h=38 mLayoutSeq=102
    mBaseLayer=141000 mSubLayer=0 mAnimLayer=141000+0=141000 mLastLayer=141000
    mSurface=Surface(name=StatusBar, identity=6)
    Surface: shown=true layer=141000 alpha=1.0 rect=(0.0,0.0) 480.0 x 38.0
    mToken=WindowToken{b4c000b0 token=null}
    mRootToken=WindowToken{b4c000b0 token=null}
    mViewVisibility=0x0 mLastHidden=false mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[0.0,0.0][480.0,38.0]
    mFrame=[0,0][480,38] last=[0,0][480,38]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[0,0][480,800]
    mContentFrame=[0,0][480,38] mVisibleFrame=[0,0][480,38]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
  Window #5 Window{b4d1bc30 StatusBarExpanded paused=false}:
    mSession=Session{b4d254d0 uid 1000} mClient=android.os.BinderProxy@b4dca320
    mAttrs=WM.LayoutParams{(0,-800)(480x762) gr=#37 sim=#10 ty=2017 fl=#811328 pfl=0x8 fmt=-3 wanim=0x1030000}
    Requested w=480 h=762 mLayoutSeq=102
    mBaseLayer=131000 mSubLayer=0 mAnimLayer=131005+0=131005 mLastLayer=131005
    mSurface=Surface(name=StatusBarExpanded, identity=13)
    Surface: shown=true layer=131005 alpha=1.0 rect=(0.0,-800.0) 480.0 x 762.0
    mToken=WindowToken{b4c000b0 token=null}
    mRootToken=WindowToken{b4c000b0 token=null}
    mViewVisibility=0x0 mLastHidden=false mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[0.0,-800.0][480.0,-38.0]
    mFrame=[0,-800][480,-38] last=[0,-800][480,-38]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[-10000,-10000][10000,10000]
    mContentFrame=[0,-800][480,-38] mVisibleFrame=[0,-800][480,-38]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
  Window #4 Window{b4d62e40 TrackingView paused=false}:
    mSession=Session{b4d254d0 uid 1000} mClient=android.os.BinderProxy@b4d62ca8
    mAttrs=WM.LayoutParams{(0,-800)(fillxfill) gr=#37 sim=#20 ty=2017 fl=#20300 fmt=-3}
    Requested w=480 h=800 mLayoutSeq=17
    mBaseLayer=131000 mSubLayer=0 mAnimLayer=131000+0=131000 mLastLayer=0
    mToken=WindowToken{b4c000b0 token=null}
    mRootToken=WindowToken{b4c000b0 token=null}
    mViewVisibility=0x8 mLastHidden=false mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration=null
    mShownFrame=[0.0,0.0][0.0,0.0]
    mFrame=[0,-800][480,0] last=[0,0][0,0]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[-10000,-10000][10000,10000]
    mContentFrame=[0,-800][480,0] mVisibleFrame=[0,-800][480,0]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=false
  Window #3 Window{b4c01158 Keyguard paused=false}:
    mSession=Session{b4be1be8 uid 1000} mClient=android.view.ViewRootImpl$W@b4c12f70
    mAttrs=WM.LayoutParams{(0,0)(fillxfill) sim=#10 ty=2004 fl=#10120800 pfl=0x8 fmt=-3 wanim=0x10301da or=5}
    Requested w=480 h=762 mLayoutSeq=32
    mBaseLayer=111000 mSubLayer=0 mAnimLayer=111000+0=111000 mLastLayer=111000
    mToken=WindowToken{b4c000b0 token=null}
    mRootToken=WindowToken{b4c000b0 token=null}
    mViewVisibility=0x8 mLastHidden=true mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[0.0,38.0][480.0,800.0]
    mFrame=[0,38][480,800] last=[0,38][480,800]
    mContainingFrame=[0,38][480,800] mParentFrame=[0,38][480,800] mDisplayFrame=[0,38][480,800]
    mContentFrame=[0,38][480,800] mVisibleFrame=[0,38][480,800]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mShownAlpha=1.0 mAlpha=1.0 mLastAlpha=0.0
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
  Window #2 Window{b4d2a948 com.dtmilano.android.sampleui/com.dtmilano.android.sampleui.MainActivity paused=false}:
    mSession=Session{b4d3cdf0 uid 10046} mClient=android.os.BinderProxy@b4c09bf0
    mAttrs=WM.LayoutParams{(0,0)(fillxfill) sim=#120 ty=1 fl=#1810100 pfl=0x8 wanim=0x1030292}
    Requested w=480 h=800 mLayoutSeq=102
    mBaseLayer=21000 mSubLayer=0 mAnimLayer=21010+0=21010 mLastLayer=21010
    mSurface=Surface(name=com.dtmilano.android.sampleui/com.dtmilano.android.sampleui.MainActivity, identity=28)
    Surface: shown=true layer=21010 alpha=1.0 rect=(0.0,0.0) 480.0 x 800.0
    mToken=AppWindowToken{b4d8bf80 token=Token{b4d3ab58 ActivityRecord{b4d3aa20 com.dtmilano.android.sampleui/.MainActivity}}}
    mRootToken=AppWindowToken{b4d8bf80 token=Token{b4d3ab58 ActivityRecord{b4d3aa20 com.dtmilano.android.sampleui/.MainActivity}}}
    mAppToken=AppWindowToken{b4d8bf80 token=Token{b4d3ab58 ActivityRecord{b4d3aa20 com.dtmilano.android.sampleui/.MainActivity}}}
    mViewVisibility=0x0 mLastHidden=false mHaveFrame=true mObscured=false
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[0.0,0.0][480.0,800.0]
    mFrame=[0,0][480,800] last=[0,0][480,800]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[0,0][480,800]
    mContentFrame=[0,38][480,800] mVisibleFrame=[0,38][480,800]
    mContentInsets=[0,38][0,0] last=[0,38][0,0] mVisibleInsets=[0,38][0,0] last=[0,38][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
  Window #1 Window{b4d78098 com.android.launcher/com.android.launcher2.Launcher paused=false}:
    mSession=Session{b4d35180 uid 10012} mClient=android.os.BinderProxy@b4d3b188
    mAttrs=WM.LayoutParams{(0,0)(fillxfill) sim=#20 ty=1 fl=#1910100 pfl=0x8 fmt=-2 wanim=0x1030292}
    Requested w=480 h=800 mLayoutSeq=37
    mBaseLayer=21000 mSubLayer=0 mAnimLayer=21005+0=21005 mLastLayer=21005
    mToken=AppWindowToken{b4d14528 token=Token{b4d12ab8 ActivityRecord{b4d12688 com.android.launcher/com.android.launcher2.Launcher}}}
    mRootToken=AppWindowToken{b4d14528 token=Token{b4d12ab8 ActivityRecord{b4d12688 com.android.launcher/com.android.launcher2.Launcher}}}
    mAppToken=AppWindowToken{b4d14528 token=Token{b4d12ab8 ActivityRecord{b4d12688 com.android.launcher/com.android.launcher2.Launcher}}}
    mViewVisibility=0x8 mLastHidden=true mHaveFrame=true mObscured=true
    mSeq=0 mSystemUiVisibility=0x0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[0.0,0.0][480.0,800.0]
    mFrame=[0,0][480,800] last=[0,0][480,800]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[0,0][480,800]
    mContentFrame=[0,38][480,800] mVisibleFrame=[0,38][480,800]
    mContentInsets=[0,38][0,0] last=[0,38][0,0] mVisibleInsets=[0,38][0,0] last=[0,38][0,0]
    mShownAlpha=1.0 mAlpha=1.0 mLastAlpha=0.0
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
    mWallpaperX=0.5 mWallpaperY=0.5
    mWallpaperXStep=0.25 mWallpaperYStep=1.0
  Window #0 Window{b4d2e648 com.android.systemui.ImageWallpaper paused=false}:
    mSession=Session{b4d254d0 uid 1000} mClient=android.os.BinderProxy@b4d82d48
    mAttrs=WM.LayoutParams{(0,0)(960x800) gr=#33 ty=2013 fl=#318 fmt=2 wanim=0x10301e4}
    Requested w=960 h=800 mLayoutSeq=43
    mIsImWindow=false mIsWallpaper=true mIsFloatingLayer=true mWallpaperVisible=false
    mBaseLayer=21000 mSubLayer=0 mAnimLayer=21000+0=21000 mLastLayer=21000
    mSurface=Surface(name=com.android.systemui.ImageWallpaper, identity=8)
    Surface: shown=false layer=21000 alpha=1.0 rect=(-240.0,0.0) 960.0 x 800.0
    mToken=WindowToken{b4c64f60 token=android.os.Binder@b4bead18}
    mRootToken=WindowToken{b4c64f60 token=android.os.Binder@b4bead18}
    mViewVisibility=0x0 mLastHidden=true mHaveFrame=true mObscured=true
    mSeq=0 mSystemUiVisibility=0x0
    Offsets x=-240 y=0
    mGivenContentInsets=[0,0][0,0] mGivenVisibleInsets=[0,0][0,0]
    mConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
    mShownFrame=[-240.0,0.0][720.0,800.0]
    mFrame=[0,0][960,800] last=[0,0][960,800]
    mContainingFrame=[0,0][480,800] mParentFrame=[0,0][480,800] mDisplayFrame=[-10000,-10000][10000,10000]
    mContentFrame=[0,0][960,800] mVisibleFrame=[0,0][960,800]
    mContentInsets=[0,0][0,0] last=[0,0][0,0] mVisibleInsets=[0,0][0,0] last=[0,0][0,0]
    mDrawPending=false mCommitDrawPending=false mReadyToShow=false mHasDrawn=true
    mWallpaperX=0.5 mWallpaperY=0.5
    mWallpaperXStep=0.25 mWallpaperYStep=1.0

  Display: init=480x800 base=480x800 cur=480x800 app=480x800 raw=480x800
  mCurConfiguration={1.0 310mcc260mnc en_US layoutdir=0 sw320dp w320dp h508dp nrml long port finger qwerty/v/v tball/v s.5}
  mCurrentFocus=Window{b4d2a948 com.dtmilano.android.sampleui/com.dtmilano.android.sampleui.MainActivity paused=false}
  mFocusedApp=AppWindowToken{b4d8bf80 token=Token{b4d3ab58 ActivityRecord{b4d3aa20 com.dtmilano.android.sampleui/.MainActivity}}}
  mInTouchMode=true mLayoutSeq=102
  mWallpaperTarget=null
  mLastWallpaperX=0.5 mLastWallpaperY=0.5
  mWindowAnimationBackgroundSurface:
    mDimSurface=Surface(name=DimSurface, identity=20)
    mDimShown=false mLayer=21009 mDimColor=0xff000000
    mLastDimWidth=480 mLastDimWidth=480
  mSystemBooted=true mDisplayEnabled=true
  mLayoutNeeded=false mBlurShown=false
  mDimAnimator:
    mDimSurface=Surface(name=DimAnimator, identity=17) 480 x 800
    mDimShown=true current=0.0 target=0.0 delta=-0.002727273 lastAnimTime=0
  mDisplayFrozen=false mWindowsFreezingScreen=false mAppsFreezingScreen=0 mWaitingForConfig=false
  mRotation=0 mAltOrientation=false
  mLastWindowForcedOrientation-1 mForcedAppOrientation=-1
  mDeferredRotationPauseCount=0
  mAnimationPending=false mWindowAnimationScale=1.0 mTransitionWindowAnimationScale=1.0
  mNextAppTransition=0xffffffff mAppTransitionReady=false
  mAppTransitionRunning=false mAppTransitionTimeout=false
  mStartingIconInTransition=false, mSkipAppTransitionAnimation=false
"""

UIAUTOMATOR_DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
    <node index="0" text="" class="android.widget.FrameLayout"
        package="com.android.launcher" content-desc="" checkable="false"
        checked="false" clickable="false" enabled="true" focusable="false"
        focused="false" scrollable="false" long-clickable="false" password="false"
        selected="false" bounds="[0,0][480,800]">
        <node index="0" text="" class="android.widget.LinearLayout"
            package="com.android.launcher" content-desc="" checkable="false"
            checked="false" clickable="false" enabled="true" focusable="false"
            focused="false" scrollable="false" long-clickable="false" password="false"
            selected="false" bounds="[0,0][480,800]">
            <node index="0" text="" class="android.widget.FrameLayout"
                package="com.android.launcher" content-desc="" checkable="false"
                checked="false" clickable="false" enabled="true" focusable="false"
                focused="false" scrollable="false" long-clickable="false" password="false"
                selected="false" bounds="[0,38][480,800]">
                <node index="0" text="" class="android.widget.FrameLayout"
                    package="com.android.launcher" content-desc="" checkable="false"
                    checked="false" clickable="false" enabled="true" focusable="false"
                    focused="false" scrollable="false" long-clickable="false" password="false"
                    selected="false" bounds="[0,38][480,800]">
                    <node index="0" text="" class="android.widget.TabHost"
                        package="com.android.launcher" content-desc="" checkable="false"
                        checked="false" clickable="false" enabled="true" focusable="true"
                        focused="true" scrollable="false" long-clickable="false" password="false"
                        selected="false" bounds="[0,38][480,800]">
                        <node index="0" text="" class="android.widget.LinearLayout"
                            package="com.android.launcher" content-desc="" checkable="false"
                            checked="false" clickable="false" enabled="true" focusable="false"
                            focused="false" scrollable="false" long-clickable="false"
                            password="false" selected="false" bounds="[0,38][480,800]">
                            <node index="0" text="" class="android.widget.FrameLayout"
                                package="com.android.launcher" content-desc="" checkable="false"
                                checked="false" clickable="false" enabled="true" focusable="false"
                                focused="false" scrollable="false" long-clickable="false"
                                password="false" selected="false" bounds="[1,38][479,116]">
                                <node index="0" text="" class="android.widget.TabWidget"
                                    package="com.android.launcher" content-desc="" checkable="false"
                                    checked="false" clickable="false" enabled="true" focusable="true"
                                    focused="false" scrollable="false" long-clickable="false"
                                    password="false" selected="false" bounds="[1,38][479,116]">
                                    <node index="0" text="Apps" class="android.widget.TextView"
                                        package="com.android.launcher" content-desc="Apps" checkable="false"
                                        checked="false" clickable="true" enabled="true" focusable="true"
                                        focused="false" scrollable="false" long-clickable="false"
                                        password="false" selected="true" bounds="[1,38][105,116]" />
                                </node>
                            </node>
                        </node>
                    </node>
                </node>
            </node>
        </node>
    </node>
</hierarchy>
"""

UIAUTOMATOR_DUMP_API17_CHINESE = '''<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>
<hierarchy rotation="0">
    <node index="0" text="" class="android.widget.FrameLayout"
        package="android" content-desc="" checkable="false" checked="false"
        clickable="false" enabled="true" focusable="false" focused="false"
        scrollable="false" long-clickable="false" password="false" selected="false"
        bounds="[0,0][800,1216]">
        <node index="0" text="" class="android.widget.FrameLayout"
            package="android" content-desc="" checkable="false" checked="false"
            clickable="false" enabled="true" focusable="false" focused="false"
            scrollable="false" long-clickable="false" password="false" selected="false"
            bounds="[0,33][800,1216]">
            <node index="0" text="" class="android.view.View" package="android"
                content-desc="" checkable="false" checked="false" clickable="false"
                enabled="true" focusable="false" focused="false" scrollable="false"
                long-clickable="false" password="false" selected="false" bounds="[0,33][800,1216]">
                <node index="0" text="" class="android.view.View" package="android"
                    content-desc="" checkable="false" checked="false" clickable="false"
                    enabled="true" focusable="false" focused="false" scrollable="true"
                    long-clickable="false" password="false" selected="false" bounds="[0,0][800,1216]">
                    <node index="0" text="" class="android.widget.FrameLayout"
                        package="android"
                        content-desc="\xe7\xa9\xba\xe7\x99\xbd\xe5\xb0\x8f\xe9\x83\xa8\xe4\xbb\xb6\xe3\x80\x82"
                        checkable="false" checked="false" clickable="false" enabled="true"
                        focusable="false" focused="false" scrollable="false"
                        long-clickable="true" password="false" selected="false" bounds="[0,66][100,625]" />
                    <node index="1" text="" class="android.widget.FrameLayout"
                        package="android"
                        content-desc="\xe7\x8a\xb6\xe6\x80\x81\xe5\xb0\x8f\xe9\x83\xa8\xe4\xbb\xb6\xe3\x80\x82"
                        checkable="false" checked="false" clickable="false" enabled="true"
                        focusable="false" focused="false" scrollable="false"
                        long-clickable="true" password="false" selected="false"
                        bounds="[113,66][686,625]">
                        <node index="0" text="" class="android.widget.GridLayout"
                            package="android" content-desc="\xe7\x8a\xb6\xe6\x80\x81"
                            checkable="false" checked="false" clickable="false" enabled="true"
                            focusable="false" focused="false" scrollable="false"
                            long-clickable="false" password="false" selected="false"
                            bounds="[123,76][676,615]">
                            <node index="0" text="" class="android.widget.LinearLayout"
                                package="android" content-desc="" checkable="false" checked="false"
                                clickable="false" enabled="true" focusable="true" focused="false"
                                scrollable="false" long-clickable="false" password="false"
                                selected="false" bounds="[123,76][676,351]">
                                <node index="0" text="" class="android.widget.RelativeLayout"
                                    package="android" content-desc="" checkable="false" checked="false"
                                    clickable="false" enabled="true" focusable="false" focused="false"
                                    scrollable="false" long-clickable="false" password="false"
                                    selected="false" bounds="[267,76][609,324]">
                                    <node index="0" text="6:40" class="android.widget.TextView"
                                        package="android" content-desc="" checkable="false" checked="false"
                                        clickable="false" enabled="true" focusable="false" focused="false"
                                        scrollable="false" long-clickable="false" password="false"
                                        selected="false" bounds="[267,76][609,324]" />
                                </node>
                                <node index="1" text="" class="android.widget.LinearLayout"
                                    package="android" content-desc="" checkable="false" checked="false"
                                    clickable="false" enabled="true" focusable="false" focused="false"
                                    scrollable="false" long-clickable="false" password="false"
                                    selected="false" bounds="[401,304][676,351]">
                                    <node index="0"
                                        text="语言"
                                        class="android.widget.TextView" package="android"
                                        content-desc="" checkable="false" checked="false" clickable="false"
                                        enabled="true" focusable="false" focused="false" scrollable="false"
                                        long-clickable="false" password="false" selected="true"
                                        bounds="[401,304][609,351]" />
                                </node>
                            </node>
                        </node>
                    </node>
                </node>
                <node index="1" text="" class="android.widget.FrameLayout"
                    package="android" content-desc="" checkable="false" checked="false"
                    clickable="false" enabled="true" focusable="false" focused="false"
                    scrollable="false" long-clickable="false" password="false"
                    selected="false" bounds="[120,654][679,1187]">
                    <node index="0" text="" class="android.widget.ViewFlipper"
                        package="android" content-desc="" checkable="false" checked="false"
                        clickable="false" enabled="true" focusable="false" focused="false"
                        scrollable="false" long-clickable="false" password="false"
                        selected="false" bounds="[120,654][679,1187]">
                        <node index="0" text="" class="android.widget.LinearLayout"
                            package="android"
                            content-desc="\xe6\xbb\x91\xe5\x8a\xa8\xe8\xa7\xa3\xe9\x94\x81\xe3\x80\x82"
                            checkable="false" checked="false" clickable="false" enabled="true"
                            focusable="false" focused="false" scrollable="false"
                            long-clickable="false" password="false" selected="false"
                            bounds="[136,670][663,1171]">
                            <node index="0" text="" class="android.widget.FrameLayout"
                                package="android" content-desc="" checkable="false" checked="false"
                                clickable="false" enabled="true" focusable="false" focused="false"
                                scrollable="false" long-clickable="false" password="false"
                                selected="false" bounds="[136,670][663,1171]">
                                <node index="0" text="" class="android.view.View" package="android"
                                    content-desc="\xe6\xbb\x91\xe5\x8a\xa8\xe5\x8c\xba\xe5\x9f\x9f\xe3\x80\x82"
                                    checkable="false" checked="false" clickable="false" enabled="true"
                                    focusable="false" focused="false" scrollable="false"
                                    long-clickable="false" password="false" selected="false"
                                    bounds="[136,670][663,1171]" />
                                <node index="1"
                                    text="\xe6\xad\xa3\xe5\x9c\xa8\xe5\x85\x85\xe7\x94\xb5\xef\xbc\x8c50%"
                                    class="android.widget.TextView" package="android" content-desc=""
                                    checkable="false" checked="false" clickable="true" enabled="true"
                                    focusable="false" focused="false" scrollable="false"
                                    long-clickable="false" password="false" selected="true"
                                    bounds="[136,670][663,699]" />
                                <node index="2" text="" class="android.widget.LinearLayout"
                                    package="android" content-desc="" checkable="false" checked="false"
                                    clickable="true" enabled="true" focusable="false" focused="false"
                                    scrollable="false" long-clickable="false" password="false"
                                    selected="false" bounds="[136,1107][663,1171]">
                                    <node index="1" text="ANDROID" class="android.widget.TextView"
                                        package="android" content-desc="" checkable="false" checked="false"
                                        clickable="false" enabled="true" focusable="false" focused="false"
                                        scrollable="false" long-clickable="false" password="false"
                                        selected="true" bounds="[355,1124][444,1153]" />
                                </node>
                                <node index="3" text="" class="android.view.View" package="android"
                                    content-desc="" checkable="false" checked="false" clickable="false"
                                    enabled="true" focusable="false" focused="false" scrollable="false"
                                    long-clickable="false" password="false" selected="false"
                                    bounds="[157,670][642,1171]" />
                            </node>
                        </node>
                    </node>
                </node>
            </node>
        </node>
    </node>
</hierarchy>
'''

WINDOWS = {1:'Window1', 2: 'com.example.window', 0xb523d938: 'com.android.launcher', 0xb52f7c88:'StatusBar'}

LIST = '''\
b522d3f8 com.android.systemui.ImageWallpaper
b523d938 com.android.launcher/com.android.launcher2.Launcher
b5339540 com.android.contacts/com.android.contacts.activities.PeopleActivity
b5252410 com.android.contacts/com.android.contacts.activities.ContactEditorActivity
b51ea228 InputMethod
b51da498 Keyguard
b52f7c88 StatusBar
b533b2c0 NavigationBar
b521d218 SearchPanel
DONE.
'''

DUMP_STATUSBAR = '''\
com.android.systemui.statusbar.phone.StatusBarWindowView@b506ea18 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=6,278611 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,800 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653315 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout_horizontalWeight=3,0.0 layout_flags_FLAG_NOT_FOCUSABLE=3,0x8 layout_flags_FLAG_TOUCHABLE_WHEN_WAKING=4,0x40 layout_flags_FLAG_SPLIT_TOUCH=8,0x800000 layout_flags_FLAG_HARDWARE_ACCELERATED=9,0x1000000 layout_flags=8,25165896 layout_type=15,TYPE_STATUS_BAR layout_verticalWeight=3,0.0 layout_x=1,0 layout_y=1,0 layout:layout_height=2,33 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=3,LTR text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,800 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
 com.android.systemui.statusbar.phone.PhoneStatusBarView@b50702b8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2375763 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_state_mUseColor=9,-16777216 layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,800 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=13,id/status_bar mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,25201968 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653315 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,33 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,800 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  android.widget.ImageView@b50709a0 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=26,id/notification_lights_out mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
  android.widget.LinearLayout@b50878b8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,800 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,800 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=22,id/status_bar_contents mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,800 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   android.widget.LinearLayout@b5087c00 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,672 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,8 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,684 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=25,id/notification_icon_area mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,692 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=1,0 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,684 drawing:getX()=3,8.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    com.android.systemui.statusbar.StatusBarIconView@b5088758 mSlot=4,null layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/moreIcon mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=4,0.65 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=4,0.75 drawing:getScaleY()=4,0.75 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.systemui.statusbar.phone.IconMerger@b508b758 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=2,32 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,672 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=20,id/notificationIcons mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130670416 layout:mRight=3,672 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,672 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     com.android.systemui.statusbar.StatusBarIconView@b6257070 mSlot=17,android/0x1040453 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=2,32 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=5,35888 layout:mRight=2,32 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=4,0.65 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,33 layout:layout_width=2,32 drawing:getPivotX()=4,16.0 drawing:getPivotY()=4,16.5 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=4,0.75 drawing:getScaleY()=4,0.75 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,32 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.widget.LinearLayout@b508bab0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,100 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=3,692 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,100 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=19,id/system_icon_area mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,792 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,100 drawing:getX()=5,692.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.LinearLayout@b508be00 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/statusIcons mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128606032 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     com.android.systemui.statusbar.StatusBarIconView@b50f1dc0 mSlot=12,sync_failing layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b5078b18 mSlot=11,sync_active layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b529cba0 mSlot=9,bluetooth layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b5297d68 mSlot=3,tty layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b5115bd8 mSlot=6,volume layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b529a1d8 mSlot=8,cdma_eri layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.StatusBarIconView@b529e3f8 mSlot=11,alarm_clock layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478496 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
    android.widget.LinearLayout@b508c150 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity=2,17 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=2,51 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=2,51 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,3 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=25,id/signal_battery_cluster mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=2,51 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,3 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,51 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     com.android.systemui.statusbar.SignalClusterView@b508cec0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=2,27 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,3 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,27 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=17,id/signal_cluster mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=2,30 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,28 layout:mTop=1,4 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,27 drawing:getX()=3,3.0 drawing:getY()=3,4.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.FrameLayout@b508d3e8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=13,id/wifi_combo mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701152 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653320 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=2,-7 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
       android.widget.ImageView@b508d7b8 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/wifi_signal mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701312 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784256 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
       android.widget.ImageView@b508daa0 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=13,id/wifi_inout mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701312 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.view.View@b508eb00 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=9,id/spacer mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,8 layout:layout_width=1,8 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.FrameLayout@b508ed28 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,27 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=2,27 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,24 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,27 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
       android.view.View@b508f0b0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,8 measurement:mMeasuredWidth=1,8 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130703312 layout:mRight=1,8 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,8 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,8 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,8 layout:layout_width=1,8 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=1,8 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
       android.widget.FrameLayout@b508f2d0 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,27 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=15,id/mobile_combo mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=2,27 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,24 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=20,3G Phone three bars. getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,27 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
        android.widget.ImageView@b508f650 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,26 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=16,id/mobile_signal mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813104 layout:mRight=2,26 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,24 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,26 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        android.widget.ImageView@b508f938 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,27 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/mobile_type mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813104 layout:mRight=2,27 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,24 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,27 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        android.widget.ImageView@b508fc20 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=2,27 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=15,id/mobile_inout mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128606160 layout:mRight=2,27 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,24 layout:mTop=2,24 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=4,27.0 drawing:getY()=4,24.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      android.widget.ImageView@b508ff08 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/airplane mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ImageView@b50901f8 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=2,30 measurement:mMeasuredHeight=2,24 measurement:mMeasuredWidth=2,21 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,5 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=10,id/battery mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813104 layout:mRight=2,51 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,28 layout:mTop=1,4 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,5 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=19,Battery 50 percent. getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,24 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,21 drawing:getX()=4,30.0 drawing:getY()=3,4.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.systemui.statusbar.policy.Clock@b50908f0 text:mText=4,6:32 getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,21.0 bg_=4,null layout:mLeft=2,51 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=2,49 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=8,id/clock mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16812080 layout:mRight=3,100 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,25 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,49 drawing:getX()=4,51.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
  android.widget.LinearLayout@b5091968 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=3,800 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244659 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=5,false drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,33 measurement:mMeasuredWidth=3,800 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=9,id/ticker mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,33 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,800 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   android.widget.ImageSwitcher@b5091f38 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=4,true drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,8 measurement:mMeasuredHeight=2,32 measurement:mMeasuredWidth=2,32 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=13,id/tickerIcon mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=2,40 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,32 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,32 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,5 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=4,16.0 drawing:getPivotY()=4,16.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=4,0.75 drawing:getScaleY()=4,0.75 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,32 drawing:getX()=3,8.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    com.android.systemui.statusbar.AnimatedImageView@b50923b8 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,32 measurement:mMeasuredWidth=2,32 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813104 layout:mRight=2,32 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,32 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784256 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,32 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,32 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
    com.android.systemui.statusbar.AnimatedImageView@b50926a8 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,32 measurement:mMeasuredWidth=2,32 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130691040 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=2,32 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
   com.android.systemui.statusbar.phone.TickerView@b5092df8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=4,true drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=2,45 measurement:mMeasuredHeight=2,30 measurement:mMeasuredWidth=3,755 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,13 padding:mPaddingTop=1,3 drawing:mLayerType=4,NONE mID=13,id/tickerText mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16813232 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,30 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=2,13 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,21 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,30 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=1,0 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,755 drawing:getX()=4,45.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.TextView@b5093350 text:mText=0, getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,19.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,27 measurement:mMeasuredWidth=3,742 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=8,16812080 layout:mRight=3,742 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,30 layout:mTop=1,3 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,21 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,27 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,742 drawing:getX()=3,0.0 drawing:getY()=3,3.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.TextView@b50937e8 text:mText=0, getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,19.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,27 measurement:mMeasuredWidth=3,742 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594912 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,21 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
 com.android.systemui.statusbar.phone.PanelHolder@b5093fb8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2245715 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=4,true drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=3,800 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=15,id/panel_holder mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128606032 layout:mRight=3,800 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,33 layout:mTop=2,33 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=2,33 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,800 drawing:getX()=3,0.0 drawing:getY()=4,33.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
  com.android.systemui.statusbar.phone.NotificationPanelView@b5094cd8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=2,21 measurement:mMeasuredHeight=11,-2147483648 measurement:mMeasuredWidth=10,1073741822 measurement:mMinHeight=3,486 measurement:mMinWidth=1,0 padding:mPaddingBottom=2,21 padding:mPaddingLeft=2,21 padding:mPaddingRight=2,21 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=21,id/notification_panel mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593616 layout:mRight=3,657 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=2,21 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=2,21 padding:mUserPaddingRight=2,21 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653320 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=19,Notification shade. getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,21 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=3,636 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=3,636 drawing:getX()=4,21.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   android.view.View@b5099878 layout:mLeft=2,21 measurement:mMeasuredHeight=2,48 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,5 drawing:mLayerType=4,NONE mID=9,id/handle mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130696144 layout:mRight=3,615 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,48 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,48 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=3,594 drawing:getX()=4,21.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.widget.Space@b50a3c10 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=2,48 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,32 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.widget.LinearLayout@b50a3e78 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=2,64 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=2,21 measurement:mMeasuredHeight=2,64 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593776 layout:mRight=3,615 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=2,43 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=4,21.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
    android.widget.LinearLayout@b50a4430 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=5,false measurement:mOrientation=1,0 measurement:mTotalLength=3,277 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_state_mUseColor=9,-16777216 layout:mLeft=1,0 measurement:mMeasuredHeight=2,64 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=9,id/header mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120205040 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,64 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,64 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,64 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.RelativeLayout@b50a4998 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=2,64 measurement:mMeasuredWidth=3,204 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=2,11 padding:mPaddingRight=2,11 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/datetime mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594672 layout:mRight=3,204 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,64 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=2,11 padding:mUserPaddingRight=2,11 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,64 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,204 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      com.android.systemui.statusbar.policy.Clock@b50aa640 text:mText=4,6:32 getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,43.0 bg_=4,null layout:mLeft=2,11 measurement:mMeasuredHeight=2,58 measurement:mMeasuredWidth=2,81 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=8,id/clock mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593904 layout:mRight=2,92 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,61 layout:mTop=1,3 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,58 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=11,false/NO_ID layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=11,false/NO_ID layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=4,true layout:layout_mRules_startOf=11,false/NO_ID layout:layout_mRules_endOf=11,false/NO_ID layout:layout_mRules_alignStart=11,false/NO_ID layout:layout_mRules_alignEnd=11,false/NO_ID layout:layout_mRules_alignParentStart=11,false/NO_ID layout:layout_mRules_alignParentEnd=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=2,11 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,81 drawing:getX()=4,11.0 drawing:getY()=3,3.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      com.android.systemui.statusbar.policy.DateView@b50ab028 text:mText=11,Sat, May 11 getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=3,103 measurement:mMeasuredHeight=2,22 measurement:mMeasuredWidth=2,90 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/date mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128598000 layout:mRight=3,193 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,54 layout:mTop=2,32 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,17 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,22 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_mRules_leftOf=11,false/NO_ID layout:layout_mRules_rightOf=8,id/clock layout:layout_mRules_above=11,false/NO_ID layout:layout_mRules_below=11,false/NO_ID layout:layout_mRules_alignBaseline=8,id/clock layout:layout_mRules_alignLeft=11,false/NO_ID layout:layout_mRules_alignTop=11,false/NO_ID layout:layout_mRules_alignRight=11,false/NO_ID layout:layout_mRules_alignBottom=11,false/NO_ID layout:layout_mRules_alignParentLeft=11,false/NO_ID layout:layout_mRules_alignParentTop=11,false/NO_ID layout:layout_mRules_alignParentRight=11,false/NO_ID layout:layout_mRules_alignParentBottom=11,false/NO_ID layout:layout_mRules_center=11,false/NO_ID layout:layout_mRules_centerHorizontal=11,false/NO_ID layout:layout_mRules_centerVertical=11,false/NO_ID layout:layout_mRules_startOf=11,false/NO_ID layout:layout_mRules_endOf=11,false/NO_ID layout:layout_mRules_alignStart=11,false/NO_ID layout:layout_mRules_alignEnd=11,false/NO_ID layout:layout_mRules_alignParentStart=11,false/NO_ID layout:layout_mRules_alignParentEnd=11,false/NO_ID layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,90 drawing:getX()=5,103.0 drawing:getY()=4,32.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.Space@b50ab960 bg_=4,null layout:mLeft=3,204 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130695120 layout:mRight=3,521 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,32 layout:mTop=2,32 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,0 layout:layout_width=1,0 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=3,317 drawing:getX()=5,204.0 drawing:getY()=4,32.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.TextView@b50abbc8 text:mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,15.0 bg_=4,null layout:mLeft=3,521 measurement:mMeasuredHeight=2,27 measurement:mMeasuredWidth=1,6 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,3 padding:mPaddingRight=1,3 padding:mPaddingTop=1,3 drawing:mLayerType=4,NONE mID=20,id/header_debug_info mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130695120 layout:mRight=3,527 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,45 layout:mTop=2,18 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,3 padding:mUserPaddingRight=1,3 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,19 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,27 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=15,CENTER_VERTICAL layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=1,6 drawing:getX()=5,521.0 drawing:getY()=4,18.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     android.widget.ImageView@b50ac150 layout:getBaseline()=2,-1 layout:mLeft=3,527 measurement:mMeasuredHeight=2,67 measurement:mMeasuredWidth=2,67 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=19,id/clear_all_button mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130704336 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,66 layout:mTop=2,-1 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402800676 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=24,Clear all notifications. getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,67 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,67 layout:layout_width=2,67 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=2,67 drawing:getX()=5,527.0 drawing:getY()=4,-1.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
     android.widget.FrameLayout@b5034b58 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=25,id/settings_button_holder mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701152 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653320 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,16 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,67 layout:layout_width=2,67 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.ImageView@b5023fd8 layout:getBaseline()=2,-1 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=18,id/settings_button mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130702336 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402800640 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=15,Quick settings. getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,67 layout:layout_width=2,67 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
      android.widget.ImageView@b506fb28 layout:getBaseline()=2,-1 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=22,id/notification_button mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130702304 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784264 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=14,Notifications. getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,67 layout:layout_width=2,67 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
    android.widget.TextView@b50993f8 text:mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,5 padding:mPaddingLeft=1,5 padding:mPaddingRight=1,5 padding:mPaddingTop=1,5 drawing:mLayerType=4,NONE mID=23,id/emergency_calls_only mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,5 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,5 padding:mUserPaddingRight=1,5 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669576 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    android.widget.FrameLayout@b50351b0 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593776 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,64 layout:mTop=2,64 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=3,0.0 drawing:getY()=4,64.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.view.ViewStub@b5008050 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=21,id/flip_settings_stub mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478368 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=1,0 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=1,0 mViewFlags=3,136 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=3,LTR text:getRawTextAlignment()=7,INHERIT text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=5,false isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=5,false drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     android.widget.ScrollView@b5006bf0 layout:mFillViewport=5,false drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2375763 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=9,id/scroll mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2127021040 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=7,9043968 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653185 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
      com.android.systemui.statusbar.policy.NotificationRowLayout@b5005d98 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=3,277 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/latestItems mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593776 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,93 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,93 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
       android.widget.FrameLayout@b6252e48 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402686080 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,93 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=7,android text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=4,true isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
        android.view.View@b6253288 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/top_glow mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128604128 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,4 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        android.widget.Button@b61f8758 text:mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,24.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=2,64 measurement:mMinWidth=2,85 padding:mPaddingBottom=1,0 padding:mPaddingLeft=2,11 padding:mPaddingRight=2,11 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/veto mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130702304 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=2,11 padding:mUserPaddingRight=2,11 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669577 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=19,Clear notification. getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=2,no accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=4,-106 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=2,64 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        com.android.systemui.statusbar.LatestItemView@b61f8ca8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2506835 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=23,FOCUS_BLOCK_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=10,id/content mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669697 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,4 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,4 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
         com.android.internal.widget.SizeAdaptiveLayout@b61f9138 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/adaptive mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
          android.view.View@b61f9480 bg_state_mUseColor=9,-16777216 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120215520 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_maxHeight=2,-1 layout:layout_minHeight=2,-1 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
          android.widget.FrameLayout@b61e3008 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=34,id/status_bar_latest_event_content mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120216288 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653320 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_maxHeight=2,85 layout:layout_minHeight=2,85 layout:layout_height=2,85 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
           android.widget.ImageView@b61e3748 layout:getBaseline()=2,-1 bg_state_mUseColor=9,859026917 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/icon mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701312 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402784256 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,85 layout:layout_width=2,85 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=4,true drawing:willNotDraw()=5,false
           android.widget.LinearLayout@b61e3c48 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=2,85 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,0 padding:mPaddingRight=2,11 padding:mPaddingTop=1,3 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=2,11 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=2,11 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,85 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,85 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
            android.widget.LinearLayout@b61e3fe0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,8 drawing:mLayerType=4,NONE mID=8,id/line1 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,11 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,11 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
             android.widget.TextView@b61e4490 text:mText=19,Choose input method getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,24.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=8,id/title mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128604160 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
             android.view.ViewStub@b61e57d8 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/time mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478368 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=1,0 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=1,0 mViewFlags=3,136 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=3,LTR text:getRawTextAlignment()=7,INHERIT text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=5,false isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=5,false drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
             android.view.ViewStub@b61e5a18 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/chronometer mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2147478368 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=1,0 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=1,0 mViewFlags=3,136 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=3,LTR text:getRawTextAlignment()=7,INHERIT text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=5,false isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=5,false drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
            android.widget.TextView@b61e5c58 text:mText=0, getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=8,id/text2 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657288 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=2,-2 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,11 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,11 layout:layout_topMargin=2,-2 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
            android.widget.ProgressBar@b61e63e8 progress:getMax()=3,100 progress:getProgress()=1,0 progress:getSecondaryProgress()=1,0 progress:isIndeterminate()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=2,21 measurement:mMinWidth=2,64 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=11,id/progress mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130702304 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,11 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,11 layout:layout_topMargin=1,0 layout:layout_height=2,16 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
            android.widget.LinearLayout@b624d1b8 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388627 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,0 measurement:mTotalLength=1,0 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=8,id/line3 mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701184 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=4,NONE layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,11 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,11 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
             android.widget.TextView@b624d558 text:mText=38,English (US) - Android keyboard (AOSP) getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,19.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/text mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128604160 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,1.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=1,0 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
             android.widget.TextView@b624dbd0 text:mText=0, getEllipsize()=3,END text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=2,11 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=7,id/info mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130701312 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=2,11 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=2,11 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
             android.widget.ImageView@b624e080 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=13,id/right_icon mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653192 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=2,11 layout:layout_rightMargin=1,0 layout:layout_startMargin=2,11 layout:layout_topMargin=1,0 layout:layout_height=2,21 layout:layout_width=2,21 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        android.view.View@b61fa1b8 layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=14,id/bottom_glow mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128604128 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=1,4 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
        android.widget.TextView@b61fa530 text:mText=0, getEllipsize()=4,null text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,12.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,3 padding:mPaddingRight=1,3 padding:mPaddingTop=1,3 drawing:mLayerType=4,NONE mID=13,id/debug_info mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130701280 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,3 padding:mUserPaddingRight=1,3 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
  com.android.systemui.statusbar.phone.SettingsPanelView@b506aff8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags_PADDING_NOT_NULL=4,0x20 mGroupFlags=7,2244723 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=3,143 measurement:mMeasuredHeight=11,-2147483648 measurement:mMeasuredWidth=10,1073741822 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=2,21 padding:mPaddingLeft=2,21 padding:mPaddingRight=2,21 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=17,id/settings_panel mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593616 layout:mRight=3,779 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=2,21 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=2,21 padding:mUserPaddingRight=2,21 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653352 drawing:getAlpha()=3,0.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=15,Quick settings. getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=2,21 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=3,636 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=3,636 drawing:getX()=5,143.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=5,false focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
   com.android.systemui.statusbar.phone.QuickSettingsScrollView@b5007d38 layout:mFillViewport=5,false drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2375763 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=23,FOCUS_AFTER_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=2,21 measurement:mMeasuredHeight=3,505 measurement:mMeasuredWidth=2,43 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2127021040 layout:mRight=3,615 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653697 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=2,43 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=4,21.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=4,true isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
    com.android.systemui.statusbar.phone.QuickSettingsContainerView@b50075c8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=3,505 measurement:mMeasuredWidth=2,43 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=27,id/quick_settings_container mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593776 layout:mRight=3,594 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=7,1572864 layout:mBottom=3,505 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,505 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,594 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b5119340 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120210160 layout:mRight=3,195 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=11,User Owner. getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.FrameLayout@b512b5c8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128597872 layout:mRight=3,195 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
       android.widget.ImageView@b512ba10 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=17,id/user_imageview mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128598000 layout:mRight=3,195 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,MATCH_PARENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
       android.widget.TextView@b509c250 text:mText=5,Owner getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_state_mUseColor=10,-872415232 layout:mLeft=1,0 measurement:mMeasuredHeight=2,25 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=16,id/user_textview mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128599024 layout:mRight=3,195 scrolling:mScrollX=6,524199 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=3,140 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,17 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=5,140.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50ae1f0 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=3,200 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120206064 layout:mRight=3,395 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=5,200.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b509a950 text:mText=10,Brightness getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=2,41 measurement:mMeasuredHeight=2,84 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=22,id/brightness_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594928 layout:mRight=3,154 scrolling:mScrollX=6,524240 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,124 layout:mTop=2,40 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,84 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,113 drawing:getX()=4,41.0 drawing:getY()=4,40.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b509c5e8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=3,400 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120206064 layout:mRight=3,595 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,165 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=5,400.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b5091158 text:mText=8,Settings getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=2,51 measurement:mMeasuredHeight=2,84 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=20,id/settings_tileview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594928 layout:mRight=3,143 scrolling:mScrollX=6,524250 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,124 layout:mTop=2,40 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,84 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,92 drawing:getX()=4,51.0 drawing:getY()=4,40.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50bcfa8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120210160 layout:mRight=3,195 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,335 layout:mTop=3,170 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=11,Wifi off..  getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=5,170.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50cb510 text:mText=9,Wi-Fi Off getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=2,53 measurement:mMeasuredHeight=2,84 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=16,id/wifi_textview mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128599024 layout:mRight=3,142 scrolling:mScrollX=6,524252 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,124 layout:mTop=2,40 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,76 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,84 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,89 drawing:getX()=4,53.0 drawing:getY()=4,40.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50a1250 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=3,200 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120206064 layout:mRight=3,395 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,335 layout:mTop=3,170 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=5,200.0 drawing:getY()=5,170.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50cb7b0 text:mText=11,Auto Rotate getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=2,37 measurement:mMeasuredHeight=2,84 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=25,id/rotation_lock_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594928 layout:mRight=3,157 scrolling:mScrollX=6,524236 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,124 layout:mTop=2,40 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,84 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,120 drawing:getX()=4,37.0 drawing:getY()=4,40.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50a06b8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=3,400 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=8,16777227 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120206064 layout:mRight=3,595 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,335 layout:mTop=3,170 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=22,Battery Charging, 50%. getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=5,400.0 drawing:getY()=5,170.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.LinearLayout@b509f5f0 measurement:mBaselineChildTop=1,0 measurement:mGravity_NONE=3,0x0 measurement:mGravity_TOP=4,0x30 measurement:mGravity_LEFT=3,0x3 measurement:mGravity_START=8,0x800003 measurement:mGravity_CENTER_VERTICAL=4,0x10 measurement:mGravity_CENTER_HORIZONTAL=3,0x1 measurement:mGravity_CENTER=4,0x11 measurement:mGravity_RELATIVE=8,0x800000 measurement:mGravity=7,8388659 layout:mBaselineAlignedChildIndex=2,-1 layout:mBaselineAligned=4,true measurement:mOrientation=1,1 measurement:mTotalLength=2,81 layout:mUseLargestChild=5,false layout:mWeightSum=4,-1.0 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false bg_=4,null layout:mLeft=2,31 measurement:mMeasuredHeight=2,81 measurement:mMeasuredWidth=8,16777227 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128593776 layout:mRight=3,163 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,123 layout:mTop=2,42 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653312 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,81 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,132 drawing:getX()=4,31.0 drawing:getY()=4,42.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
       android.widget.ImageView@b509ed78 layout:getBaseline()=2,-1 bg_=4,null layout:mLeft=2,44 measurement:mMeasuredHeight=2,56 measurement:mMeasuredWidth=8,16777227 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=2,13 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=16,id/battery_image mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128598000 layout:mRight=2,87 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,56 layout:mTop=1,0 padding:mUserPaddingBottom=2,13 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653184 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,56 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=2,43 drawing:getX()=4,44.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
       android.widget.TextView@b50d3720 text:mText=13,Charging, 50% getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=2,25 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=19,id/battery_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128594928 layout:mRight=3,132 scrolling:mScrollX=6,524230 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,81 layout:mTop=2,56 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,25 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_gravity=6,CENTER layout:layout_weight=3,0.0 layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,132 drawing:getX()=3,0.0 drawing:getY()=4,56.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b509f938 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=3,165 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120210160 layout:mRight=3,195 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,505 layout:mTop=3,340 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669696 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=19,Airplane Mode Off.. getFilterTouchesWhenObscured()=5,false layout:getHeight()=3,165 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=2,11 drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,195 drawing:getX()=3,0.0 drawing:getY()=5,340.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50d39c0 text:mText=13,Airplane mode getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=2,28 measurement:mMeasuredHeight=2,84 measurement:mMeasuredWidth=2,11 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=25,id/airplane_mode_textview mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2128599024 layout:mRight=3,167 scrolling:mScrollX=6,524227 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=3,124 layout:mTop=2,40 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,76 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,84 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=3,139 drawing:getX()=4,28.0 drawing:getY()=4,40.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b509ffb0 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120216288 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669704 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=15,Alarm set for . getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50e5da8 text:mText=0, getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=17,id/alarm_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130702336 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50a09a8 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120216288 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669704 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50e6048 text:mText=0, getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=20,id/location_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130702336 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b509fc70 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120216288 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669704 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50f7730 text:mText=16,Wireless Display getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=24,id/wifi_display_textview mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130702336 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
     com.android.systemui.statusbar.phone.QuickSettingsTileView@b50a0328 drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 padding:mForegroundPaddingLeft=1,0 padding:mForegroundPaddingRight=1,0 padding:mForegroundPaddingTop=1,0 drawing:mForegroundInPadding=4,true measurement:mMeasureAllChildren=5,false drawing:mForegroundGravity=3,119 events:mLastTouchDownX=3,0.0 events:mLastTouchDownTime=1,0 events:mLastTouchDownY=3,0.0 events:mLastTouchDownIndex=2,-1 mGroupFlags_CLIP_CHILDREN=3,0x1 mGroupFlags_CLIP_TO_PADDING=3,0x2 mGroupFlags=7,2244691 layout:mChildCountWithTransientState=1,0 focus:getDescendantFocusability()=24,FOCUS_BEFORE_DESCENDANTS drawing:getPersistentDrawingCache()=9,SCROLLING drawing:isAlwaysDrawnWithCacheEnabled()=4,true isAnimationCacheEnabled()=4,true drawing:isChildrenDrawingOrderEnabled()=5,false drawing:isChildrenDrawnWithCacheEnabled()=5,false layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags_DIRTY=8,0x200000 mPrivateFlags=11,-2120216288 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402669704 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=3,165 layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=4,GONE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=4,true drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=4,true isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=4,true
      android.widget.TextView@b50f79d0 text:mText=15,Take bug report getEllipsize()=7,MARQUEE text:getSelectionEnd()=2,-1 text:getSelectionStart()=2,-1 text:getTextSize()=4,16.0 bg_=4,null layout:mLeft=1,0 measurement:mMeasuredHeight=1,0 measurement:mMeasuredWidth=1,0 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,3 padding:mPaddingLeft=1,8 padding:mPaddingRight=1,8 padding:mPaddingTop=1,0 drawing:mLayerType=4,NONE mID=5,NO_ID mPrivateFlags_FORCE_LAYOUT=6,0x1000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_NOT_DRAWN=3,0x0 mPrivateFlags=11,-2130702336 layout:mRight=1,0 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=1,0 layout:mTop=1,0 padding:mUserPaddingBottom=1,3 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,8 padding:mUserPaddingRight=1,8 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402657280 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=1,0 accessibility:getImportantForAccessibility()=3,yes accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=12,WRAP_CONTENT layout:layout_width=12,WRAP_CONTENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=7,VISIBLE layout:getWidth()=1,0 drawing:getX()=3,0.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
   android.view.View@b506f8f0 layout:mLeft=2,21 measurement:mMeasuredHeight=2,48 measurement:mMeasuredWidth=2,43 measurement:mMinHeight=1,0 measurement:mMinWidth=1,0 padding:mPaddingBottom=1,0 padding:mPaddingLeft=1,0 padding:mPaddingRight=1,0 padding:mPaddingTop=1,5 drawing:mLayerType=4,NONE mID=9,id/handle mPrivateFlags_LAYOUT_REQUIRED=6,0x2000 mPrivateFlags_DRAWING_CACHE_INVALID=3,0x0 mPrivateFlags_DRAWN=4,0x20 mPrivateFlags=11,-2130696144 layout:mRight=3,615 scrolling:mScrollX=1,0 scrolling:mScrollY=1,0 mSystemUiVisibility_SYSTEM_UI_FLAG_VISIBLE=3,0x0 mSystemUiVisibility=1,0 layout:mBottom=2,48 layout:mTop=1,0 padding:mUserPaddingBottom=1,0 padding:mUserPaddingEnd=11,-2147483648 padding:mUserPaddingLeft=1,0 padding:mUserPaddingRight=1,0 padding:mUserPaddingStart=11,-2147483648 mViewFlags=9,402653188 drawing:getAlpha()=3,1.0 layout:getBaseline()=2,-1 accessibility:getContentDescription()=4,null getFilterTouchesWhenObscured()=5,false layout:getHeight()=2,48 accessibility:getImportantForAccessibility()=4,auto accessibility:getLabelFor()=2,-1 layout:getLayoutDirection()=22,RESOLVED_DIRECTION_LTR layout:layout_bottomMargin=1,0 layout:layout_endMargin=11,-2147483648 layout:layout_leftMargin=1,0 layout:layout_rightMargin=1,0 layout:layout_startMargin=11,-2147483648 layout:layout_topMargin=1,0 layout:layout_height=2,48 layout:layout_width=12,MATCH_PARENT drawing:getPivotX()=3,0.0 drawing:getPivotY()=3,0.0 layout:getRawLayoutDirection()=7,INHERIT text:getRawTextAlignment()=7,GRAVITY text:getRawTextDirection()=7,INHERIT drawing:getRotation()=3,0.0 drawing:getRotationX()=3,0.0 drawing:getRotationY()=3,0.0 drawing:getScaleX()=3,1.0 drawing:getScaleY()=3,1.0 getScrollBarStyle()=14,INSIDE_OVERLAY drawing:getSolidColor()=1,0 getTag()=4,null text:getTextAlignment()=7,GRAVITY drawing:getTranslationX()=3,0.0 drawing:getTranslationY()=3,0.0 getVisibility()=9,INVISIBLE layout:getWidth()=3,594 drawing:getX()=4,21.0 drawing:getY()=3,0.0 focus:hasFocus()=5,false layout:hasTransientState()=5,false isActivated()=5,false isClickable()=5,false drawing:isDrawingCacheEnabled()=5,false isEnabled()=4,true focus:isFocusable()=5,false isFocusableInTouchMode()=5,false focus:isFocused()=5,false isHapticFeedbackEnabled()=4,true isHovered()=5,false isInTouchMode()=4,true layout:isLayoutRtl()=5,false drawing:isOpaque()=5,false isSelected()=5,false isSoundEffectsEnabled()=4,true drawing:willNotCacheDrawing()=5,false drawing:willNotDraw()=5,false
DONE.
DONE
'''

RUNNING = 1
STOPPED = 0

class MockDevice(object):
    '''
    Mocks an Android device
    '''


    def __init__(self, serialno="MOCK12345678", version=15, startviewserver=False, uiautomatorkilled=False, language='en'):
        '''
        Constructor
        '''

        self.serialno = serialno
        self.version = version
        self.service = STOPPED
        self.viewServer = "WHAT?"
        if startviewserver:
            if DEBUG:
                print >> sys.stderr, "\n**** Starting ViewServer... ****", self
            self.viewServer = MockViewServer()
        else:
            self.viewServer = None
        self.uiAutomatorKilled = uiautomatorkilled
        self.language = language
        self.uiAutomatorDump = {}
        self.uiAutomatorDump['en'] = UIAUTOMATOR_DUMP
        # FIXME: MockDevice could not be API17
        self.uiAutomatorDump['zh'] = UIAUTOMATOR_DUMP_API17_CHINESE

#     def __del__(self):
#         self.shutdownMockViewServer()

    def shell(self, cmd):
        if cmd == 'service call window 3':
            return FALSE_PARCEL
        elif re.compile('service call window 1 i32 \d+').match(cmd):
            self.service = RUNNING
            return TRUE_PARCEL
        elif re.compile('service call window 2').match(cmd):
            self.service = STOPPED
            return TRUE_PARCEL
        elif cmd == 'dumpsys window':
            return DUMPSYS_WINDOW_PARTIAL
        elif cmd == 'dumpsys window windows':
            return DUMPSYS_WINDOW_WINDOWS

        m = re.match('uiautomator dump (\S+)', cmd)
        if m:
            if self.version >= 16:
                # it was simulating a dump to sdcard before
                #return 'dumped %s' % m.group(1)
                if not self.uiAutomatorKilled:
                    return self.uiAutomatorDump[self.language]
                else:
                    return self.uiAutomatorDump[self.language] + "Killed\r\n"
            else:
                return "uiautomator: command not found"

        m = re.match('cat (\S+) .*', cmd)
        if m:
            return self.uiAutomatorDump[self.language]

    def getProperty(self, property):
        if property == 'ro.serialno':
            return self.serialno
        elif property == 'build.version.sdk' or property == 'ro.build.version.sdk':
            return self.version
        elif property == 'display.width':
            return 768
        elif property == 'display.height':
            return 1184
        return None

    def shutdownMockViewServer(self):
        if DEBUG:
            print >> sys.stderr, "MockDevice.shutdownMockViewServer()", self,
            try:
                print >> sys.stderr, "viewServer=", self.viewServer
            except:
                print >> sys.stderr, "NO VIEWSERVER !!!!", dir(self)
        if self.viewServer:
            if DEBUG:
                print >> sys.stderr, "    shutdownMockViewServer: shutting down ViewServer"
            self.viewServer.shutdown()
            #del(self.viewServer)

import sys
import time
import select
#from select import cpython_compatible_select as select
import threading
import socket
import SocketServer


class MockViewServer():
    HOST, PORT = "localhost", 4939

    class MockViewServerHandler(SocketServer.BaseRequestHandler):
        def handle(self):
            if DEBUG:
                print >>sys.stderr, "MockViewServerHandler: handling request (self=%s)" % self
            # self.request is the TCP socket connected to the client
            self.data = self.request.recv(1024).strip()
            if DEBUG:
                print >>sys.stderr, "MockViewServerHandler: data='%s'" % self.data
            if self.data == 'SHUTDOWN':
                self.running = False
                return
            elif self.data.lower() == 'dump -1':
                self.request.sendall(DUMP)
            elif self.data.lower() == 'list':
                self.request.sendall(LIST)
            elif self.data.lower() == 'dump b52f7c88':
                self.request.sendall(DUMP_STATUSBAR)
            else:
                raise Exception("MockViewServerHandler: unknown command '%s'" % self.data)
            #print "{} wrote:".format(self.client_address[0])

    class ServerThread(threading.Thread):
        def __init__(self, server):
            super(MockViewServer.ServerThread, self).__init__()
            self.server = server
            self.running = True
            self.pollInterval = 1

        def run(self):
            if DEBUG:
                print >> sys.stderr, "ServerThread: serving running=", self.running
            # In 2.5 serve_forever() never exits and there's no way of stopping the server
            #self.server.serve_forever(self.pollInterval)
            while self.running:
                if DEBUG:
                    print >> sys.stderr, "ServerThread: polling (self=%s)" % self
                r, w, e = select.select([self.server], [], [], self.pollInterval)
                if r:
                    if self.server:
                        try:
                            self.server.handle_request()
                        except:
                            print >> sys.stderr, "ServerThread: the socket may have been closed"


    def __init__(self, host=HOST, port=PORT):
        # Create the server, binding to localhost on port
        if DEBUG:
            print >>sys.stderr, "MockViewServer: starting server on host=%s port=%s" % (host, port)
        self.server = SocketServer.TCPServer((host, port), MockViewServer.MockViewServerHandler)
        self.server.socket.setblocking(0)
        self.host = host
        self.port = port
        # In 2.5 serve_forever() never exits and there's no way of stopping the server
        #self.server.serve_forever(1)
        #print >> sys.stderr, "MockViewServer: NEVER REACHED on Linux"
        # Activate the server; this will keep running until you shutdown
        self.serverThread = MockViewServer.ServerThread(self.server)
        self.serverThread.start()

    def shutdown(self):
        if DEBUG:
            print >> sys.stderr, "**** MockViewServer.shutdown() ****"
        try:
            self.server.socket.shutdown(socket.SHUT_RDWR)
            #if DEBUG:
            #    print >> sys.stderr, "    shutdown: shutting down the server, serve_forever() should exit"
            #self.server.shutdown()
            if DEBUG:
                print >> sys.stderr, "    shutdown: DONE"
        except Exception, ex:
            print >> sys.stderr, "ERROR", ex
            pass
        self.serverThread.running = False
        #self.server.socket.shutdown(socket.SHUT_RDWR)
        self.server.socket.close()
#        del(self.server.socket)
        #del(self.server)
        time.sleep(120)
        time.sleep(5)


########NEW FILE########
__FILENAME__ = viewclient-with-real-devices-connected
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 5, 2012

@author: diego
'''

import sys
import os
import unittest

# PyDev sets PYTHONPATH, use it
for p in os.environ['PYTHONPATH'].split(':'):
    if not p in sys.path:
        sys.path.append(p)
try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import View, TextView, EditText, ViewClient



class ViewClientTest(unittest.TestCase):

    serialno1 = 'emulator-5554'
    device1 = None
    serialno2 = 'emulator-5556'
    device2 = None

    @classmethod
    def setUpClass(cls):
        '''
        Set ups the class.

        The preconditions to run this test is to have at least 2 emulators running:
           - emulator-5554
           - emulator-5556
        '''
        sys.argv = ['testViewClient_localPort_remotePort', serialno1]
        cls.device1, cls.serialno1 = ViewClient.connectToDeviceOrExit(timeout=30)

        sys.argv = ['testViewClient_localPort_remotePort', serialno2]
        cls.device2, cls.serialno2 = ViewClient.connectToDeviceOrExit(timeout=30)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def testConnectToDeviceOrExit_none(self):
        sys.argv = [ 'VIEWCLIENT']
        device, serialno = ViewClient.connectToDeviceOrExit()
        self.assertNotEquals(None, device)
        self.assertNotEquals(None, serialno)

    def testConnectToDeviceOrExit_emulator_5556(self):
        sys.argv = [ 'VIEWCLIENT', 'emulator-5556']
        device, serialno = ViewClient.connectToDeviceOrExit()
        self.assertNotEquals(None, device)
        self.assertNotEquals(None, serialno)

#    @unittest.skip("until multiple devices could be connected")
#    def testViewClient_localPort_remotePort(self):
#        serialno = 'emulator-5554'
#        sys.argv = ['testViewClient_localPort_remotePort', serialno]
#        device, serialno = ViewClient.connectToDeviceOrExit(timeout=30)
#        localPort = 9005
#        remotePort = 9006
#        vc = ViewClient(device=device, serialno=serialno, localport=localPort, remoteport=remotePort, autodump=True)
#        self.assertTrue(vc.getRoot() != None)

    def testViewClient_oneDevice_TwoViewClients(self):
        localPort1 = 9005
        remotePort1 = 9006
        print "Conencting to", remotePort1
        vc1 = ViewClient(device=ViewClientTest.device1, serialno=ViewClientTest.serialno1,
                         localport=localPort1, remoteport=remotePort1, autodump=True)
        self.assertTrue(vc1.getRoot() != None)
        vc1.traverse()

        localPort2 = 9007
        remotePort2 = 9008
        print "Conencting to", remotePort2
        vc2 = ViewClient(device=ViewClientTest.device2, serialno=ViewClientTest.serialno2,
                         localport=localPort2, remoteport=remotePort2, autodump=True)
        self.assertTrue(vc2.getRoot() != None)
        vc2.traverse()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

########NEW FILE########
__FILENAME__ = viewclient
#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012  Diego Torres Milano
Created on Feb 5, 2012

@author: diego
'''

import sys
import os
import time
import StringIO
import unittest
import exceptions
import platform

# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import *
from mocks import MockDevice, MockViewServer
from mocks import DUMP, DUMP_SAMPLE_UI, VIEW_MAP, VIEW_MAP_API_8, VIEW_MAP_API_17, RUNNING, STOPPED, WINDOWS

os_name = platform.system()
if os_name.startswith('Linux'):
    TRUE = '/bin/true'
else:
    TRUE = '/usr/bin/true'

class ViewTest(unittest.TestCase):

    def setUp(self):
        self.view = View(VIEW_MAP, None, -1)

    def tearDown(self):
        try:
            del os.environ['ANDROID_SERIAL']
        except:
            pass

    def testViewFactory_View(self):
        attrs = {'class': 'android.widget.AnyView', 'text:mText': 'Button with ID'}
        view = View.factory(attrs, None, -1)
        self.assertTrue(isinstance(view, View))

    def testViewFactory_TextView(self):
        attrs = {'class': 'android.widget.TextView', 'text:mText': 'Button with ID'}
        view = View.factory(attrs, None, -1)
        self.assertTrue(isinstance(view, TextView))

    def testViewFactory_TextView(self):
        attrs = {'class': 'android.widget.EditText', 'text:mText': 'Button with ID'}
        view = View.factory(attrs, None, -1)
        self.assertTrue(isinstance(view, EditText))

    def testView_notSpecifiedSdkVersion(self):
        device = MockDevice()
        view = View(VIEW_MAP, device, -1)
        self.assertEqual(device.version, view.build[VERSION_SDK_PROPERTY])

    def testView_specifiedSdkVersion_8(self):
        view = View(VIEW_MAP_API_8, MockDevice(), 8)
        self.assertEqual(8, view.build[VERSION_SDK_PROPERTY])

    def testView_specifiedSdkVersion_10(self):
        view = View(VIEW_MAP, MockDevice(), 10)
        self.assertEqual(10, view.build[VERSION_SDK_PROPERTY])

    def testView_specifiedSdkVersion_16(self):
        view = View(VIEW_MAP, MockDevice(), 16)
        self.assertEqual(16, view.build[VERSION_SDK_PROPERTY])

    def testInnerMethod(self):
        v = View({'isChecked()':'true'}, None)
        self.assertTrue(v.isChecked())
        v.map['isChecked()'] = 'false'
        self.assertFalse(v.isChecked(), "Expected False but is %s {%s}" % (v.isChecked(), v.map['isChecked()']))
        self.assertFalse(v.isChecked())
        v.map['other'] = 1
        self.assertEqual(1, v.other())
        v.map['evenMore'] = "ABC"
        self.assertEqual("ABC", v.evenMore())
        v.map['more'] = "abc"
        v.map['more'] = v.evenMore()
        self.assertEqual("ABC", v.more())
        v.map['isMore()'] = 'true'
        self.assertTrue(v.isMore())

    def testGetClass(self):
        self.assertEqual('android.widget.ToggleButton', self.view.getClass())

    def testGetId(self):
        self.assertEqual('id/button_with_id', self.view.getId())

    def testTextPropertyForDifferentSdkVersions(self):
        VP = { -1:TEXT_PROPERTY, 8:TEXT_PROPERTY_API_10, 10:TEXT_PROPERTY_API_10, 15:TEXT_PROPERTY, 16:TEXT_PROPERTY_UI_AUTOMATOR, 17:TEXT_PROPERTY_UI_AUTOMATOR}
        for version, textProperty in VP.items():
            view = View(None, None, version)
            self.assertEqual(textProperty, view.textProperty, msg='version %d: expected: %s actual: %s' % (version, textProperty, view.textProperty))

    def testTextPropertyForDifferentSdkVersions_device(self):
        VP = { -1:TEXT_PROPERTY, 8:TEXT_PROPERTY_API_10, 10:TEXT_PROPERTY_API_10, 15:TEXT_PROPERTY, 16:TEXT_PROPERTY_UI_AUTOMATOR, 17:TEXT_PROPERTY_UI_AUTOMATOR}
        for version, textProperty in VP.items():
            device = MockDevice(version=version)
            view = View(None, device, -1)
            self.assertEqual(textProperty, view.textProperty, msg='version %d' % version)

    def testLeftPropertyForDifferentSdkVersions(self):
        VP = { -1:LEFT_PROPERTY, 8:LEFT_PROPERTY_API_8, 10:LEFT_PROPERTY, 15:LEFT_PROPERTY, 16:LEFT_PROPERTY, 17:LEFT_PROPERTY}
        for version, leftProperty in VP.items():
            view = View(None, None, version)
            self.assertEqual(leftProperty, view.leftProperty, msg='version %d' % version)

    def testLeftPropertyForDifferentSdkVersions_device(self):
        VP = { -1:LEFT_PROPERTY, 8:LEFT_PROPERTY_API_8, 10:LEFT_PROPERTY, 15:LEFT_PROPERTY, 16:LEFT_PROPERTY, 17:LEFT_PROPERTY}
        for version, leftProperty in VP.items():
            device = MockDevice(version=version)
            view = View(None, device, -1)
            self.assertEqual(leftProperty, view.leftProperty, msg='version %d' % version)

    def testTopPropertyForDifferentSdkVersions(self):
        VP = { -1:TOP_PROPERTY, 8:TOP_PROPERTY_API_8, 10:TOP_PROPERTY, 15:TOP_PROPERTY, 16:TOP_PROPERTY, 17:TOP_PROPERTY}
        for version, topProperty in VP.items():
            view = View(None, None, version)
            self.assertEqual(topProperty, view.topProperty, msg='version %d' % version)

    def testTopPropertyForDifferentSdkVersions_device(self):
        VP = { -1:TOP_PROPERTY, 8:TOP_PROPERTY_API_8, 10:TOP_PROPERTY, 15:TOP_PROPERTY, 16:TOP_PROPERTY, 17:TOP_PROPERTY}
        for version, topProperty in VP.items():
            device = MockDevice(version=version)
            view = View(None, device, -1)
            self.assertEqual(topProperty, view.topProperty, msg='version %d' % version)

    def testWidthPropertyForDifferentSdkVersions(self):
        VP = { -1:WIDTH_PROPERTY, 8:WIDTH_PROPERTY_API_8, 10:WIDTH_PROPERTY, 15:WIDTH_PROPERTY, 16:WIDTH_PROPERTY, 17:WIDTH_PROPERTY}
        for version, widthProperty in VP.items():
            view = View(None, None, version)
            self.assertEqual(widthProperty, view.widthProperty, msg='version %d' % version)

    def testWidthPropertyForDifferentSdkVersions_device(self):
        VP = { -1:WIDTH_PROPERTY, 8:WIDTH_PROPERTY_API_8, 10:WIDTH_PROPERTY, 15:WIDTH_PROPERTY, 16:WIDTH_PROPERTY, 17:WIDTH_PROPERTY}
        for version, widthProperty in VP.items():
            device = MockDevice(version=version)
            view = View(None, device, -1)
            self.assertEqual(widthProperty, view.widthProperty, msg='version %d' % version)

    def testHeightPropertyForDifferentSdkVersions(self):
        VP = { -1:HEIGHT_PROPERTY, 8:HEIGHT_PROPERTY_API_8, 10:HEIGHT_PROPERTY, 15:HEIGHT_PROPERTY, 16:HEIGHT_PROPERTY, 17:HEIGHT_PROPERTY}
        for version, heightProperty in VP.items():
            view = View(None, None, version)
            self.assertEqual(heightProperty, view.heightProperty, msg='version %d' % version)

    def testHeightPropertyForDifferentSdkVersions_device(self):
        VP = { -1:HEIGHT_PROPERTY, 8:HEIGHT_PROPERTY_API_8, 10:HEIGHT_PROPERTY, 15:HEIGHT_PROPERTY, 16:HEIGHT_PROPERTY, 17:HEIGHT_PROPERTY}
        for version, heightProperty in VP.items():
            device = MockDevice(version=version)
            view = View(None, device, -1)
            self.assertEqual(heightProperty, view.heightProperty, msg='version %d' % version)

    def testGetText(self):
        self.assertTrue(self.view.map.has_key('text:mText'))
        self.assertEqual('Button with ID', self.view.getText())
        self.assertEqual('Button with ID', self.view['text:mText'])

    def testGetX_specifiedSdkVersion_8(self):
        view = View(VIEW_MAP_API_8, MockDevice(), 8)
        self.assertEqual(8, view.build[VERSION_SDK_PROPERTY])
        self.assertEqual(50, view.getX())

    def testGetX_specifiedSdkVersion_10(self):
        view = View(VIEW_MAP, MockDevice(), 10)
        self.assertEqual(10, view.build[VERSION_SDK_PROPERTY])
        self.assertEqual(50, view.getX())

    def testGetY_specifiedSdkVersion_8(self):
        view = View(VIEW_MAP_API_8, MockDevice(), 8)
        self.assertEqual(8, view.build[VERSION_SDK_PROPERTY])
        self.assertEqual(316, view.getY())

    def testGetY_specifiedSdkVersion_10(self):
        view = View(VIEW_MAP, MockDevice(), 10)
        self.assertEqual(10, view.build[VERSION_SDK_PROPERTY])
        self.assertEqual(316, view.getY())

    def testGetWidth(self):
        self.assertEqual(1140, self.view.getWidth())

    def testGetHeight(self):
        self.assertEqual(48, self.view.getHeight())

    def testGetUniqueId(self):
        self.assertEqual('id/button_with_id', self.view.getUniqueId())

    def testGetUniqueIdEqualsToIdWhenIdIsSpecified(self):
        self.assertEqual(self.view.getId(), self.view.getUniqueId())

    def testName_Layout_mLeft(self):
        v = View({'layout:mLeft':200}, None)
        self.assertEqual(200, v.layout_mLeft())

    def testNameWithColon_this_is_a_fake_name(self):
        v = View({'this:is_a_fake_name':1}, None)
        self.assertEqual(1, v.this_is_a_fake_name())

    def testNameWith2Colons_this_is_another_fake_name(self):
        v = View({'this:is:another_fake_name':1}, None)
        self.assertEqual(1, v.this_is_another_fake_name())

    def testViewWithoutId(self):
        v = View({'mID':'id/NO_ID', 'text:mText':'Some text'}, None)
        self.assertEqual('id/NO_ID', v.getId())

    def testInexistentMethodName(self):
        v = View({'foo':1}, None)
        try:
            v.bar()
            raise Exception("AttributeError not raised")
        except AttributeError:
            pass

    def testViewTreeRoot(self):
        root = View({'root':1}, None)
        self.assertTrue(root.parent == None)

    def testViewTree(self):
        root = View({'root':1}, None)
        children = ["A", "B", "C"]
        for s in children:
            root.add(View({s:1}, None))

        self.assertEquals(len(children), len(root.children))

    def testViewTreeParent(self):
        root = View({'root':1}, None)
        children = ["A", "B", "C"]
        for s in children:
            root.add(View({s:1}, None))

        for ch in root.children:
            self.assertTrue(ch.parent == root)

    def testContainsPoint_api15(self):
        v = View(VIEW_MAP, MockDevice(), 15)
        (X, Y, W, H) = v.getPositionAndSize()
        self.assertEqual(X, v.getX())
        self.assertEqual(Y, v.getY())
        self.assertEqual(W, v.getWidth())
        self.assertEqual(H, v.getHeight())
        self.assertTrue(v.containsPoint((v.getCenter())))

    def testContainsPoint_api17(self):
        v = View(VIEW_MAP_API_17, MockDevice(), 17)
        (X, Y, W, H) = v.getPositionAndSize()
        self.assertEqual(X, v.getX())
        self.assertEqual(Y, v.getY())
        self.assertEqual(W, v.getWidth())
        self.assertEqual(H, v.getHeight())
        self.assertTrue(v.containsPoint((v.getCenter())))

    def testIsClickable_api15(self):
        v = View(VIEW_MAP, MockDevice(), 15)
        self.assertTrue(v.isClickable())

    def testIsClickable_api17(self):
        v = View(VIEW_MAP_API_17, MockDevice(), 17)
        self.assertTrue(v.isClickable())

class ViewClientTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testInit_adb(self):
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEqual(None, vc)

    def testInit_adbNone(self):
        device = MockDevice()
        try:
            vc = ViewClient(device, device.serialno, adb=None, autodump=False)
            self.assertNotEqual(None, vc)
        except subprocess.CalledProcessError:
            # This is needed because the ports cannot be forwarded if there is no device connected
            pass

    def testExceptionDeviceNotConnected(self):
        try:
            vc = ViewClient(None, None)
        except Exception, e:
            self.assertEqual('Device is not connected', e.message)

    def testConnectToDeviceOrExit_environ(self):
        sys.argv = ['']
        os.environ['ANDROID_SERIAL'] = 'ABC123'
        try:
            ViewClient.connectToDeviceOrExit(timeout=1, verbose=True)
        except RuntimeError, e:
            msg = str(e)
            if re.search('Is adb running on your computer?', msg):
                # This test required adb running
                self.fail(msg)
            elif not re.search("couldn't find device that matches 'ABC123'", msg):
                self.fail(msg)
        except exceptions.SystemExit, e:
            self.assertEquals(3, e.code)
        except Exception, e: #FIXME: java.lang.NullPointerException:
            self.fail('Serialno was not taken from environment: ' + msg)

    def testConnectToDeviceOrExit_serialno(self):
        sys.argv = ['']
        try:
            ViewClient.connectToDeviceOrExit(timeout=1, verbose=True, serialno='ABC123')
        except RuntimeError, e:
            msg = str(e)
            if re.search('Is adb running on your computer?', msg):
                # This test required adb running
                self.fail(msg)
            elif not re.search("couldn't find device that matches 'ABC123'", msg):
                self.fail(msg)
        except exceptions.SystemExit, e:
            self.assertEquals(3, e.code)
        except Exception, e: #FIXME: java.lang.NullPointerException:
            self.fail('Serialno was not taken from argument: ' + str(e))

    def testConstructor(self):
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)

    def testMapSerialNo_noPortSpecified(self):
        vc = ViewClient(MockDevice(), serialno='192.168.1.100', adb=TRUE, autodump=False)
        self.assertEqual('192.168.1.100:5555', vc.serialno)

    def testMapSerialNo_portSpecified(self):
        vc = ViewClient(MockDevice(), serialno='192.168.1.100:5555', adb=TRUE, autodump=False)
        self.assertEqual('192.168.1.100:5555', vc.serialno)

    def testMapSerialNo_emulator(self):
        vc = ViewClient(MockDevice(), serialno='emulator-5556', adb=TRUE, autodump=False)
        self.assertEqual('emulator-5556', vc.serialno)

    def testMapSerialNo_regex(self):
        # This is an edge case. A regex should not be used as the serialno in ViewClient as it's
        # behavior is not well defined.
        # MonkeyRunner.waitForConnection() accepts a regexp as serialno but adb -s doesn't
        try:
            ViewClient(MockDevice(),  serialno='.*', adb=TRUE, autodump=False)
            self.fail()
        except ValueError:
            pass

    def testMapSerialNo_None(self):
        device = MockDevice()
        try:
            ViewClient(device, None, adb=TRUE, autodump=False)
            self.fail()
        except ValueError:
            pass

    def testGetProperty_displayWidth(self):
        device = MockDevice()
        self.assertEqual(768, device.getProperty('display.width'))

    def testGetProperty_displayHeight(self):
        device = MockDevice()
        self.assertEqual(1184, device.getProperty('display.height'))

    def __mockTree(self, dump=DUMP, version=15, language='en'):
        device = MockDevice(version=version, language=language)
        vc = ViewClient(device, serialno=device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        if version <= 15:
            # We don't want to invoke the ViewServer or MockViewServer for this
            vc.setViews(dump)
        else:
            vc.dump()
        return vc

    def __mockWindows(self, windows=WINDOWS):
        device = MockDevice()
        vc = ViewClient(device, serialno=device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.windows = windows
        return vc

    def testRoot(self):
        vc = self.__mockTree()
        root = vc.root
        self.assertTrue(root != None)
        self.assertTrue(root.parent == None)
        self.assertTrue(root.getClass() == 'com.android.internal.policy.impl.PhoneWindow$DecorView')

    def testParseTree(self):
        vc = self.__mockTree()
        # eat all the output
        vc.traverse(vc.root, transform=self.__eatIt)
        # We know there are 23 views in ViewServer mock tree
        self.assertEqual(23, len(vc.getViewIds()))

    def testParsetree_api17(self):
        vc = self.__mockTree(version=17)
        # eat all the output
        vc.traverse(vc.root, transform=self.__eatIt)
        # We know there are 9 views in UiAutomator mock tree
        self.assertEqual(9, len(vc.getViewIds()))

    def testParsetree_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        # eat all the output
        vc.traverse(vc.root, transform=self.__eatIt)
        # We know there are 21 views in UiAutomator mock tree
        self.assertEqual(21, len(vc.getViewIds()))

    def __testViewByIds_apiIndependent(self, vc):
        viewsbyId = vc.getViewsById()
        self.assertNotEquals(None, viewsbyId)
        for k, v in viewsbyId.items():
            self.assertTrue(isinstance(k, str))
            self.assertTrue(isinstance(v, View), "v=" + str(v) + " is not a View")
            self.assertTrue(re.match("id/.*", v.getUniqueId()) != None)
            self.assertEquals(k, v.getUniqueId())

    def testGetViewsById(self):
        vc = self.__mockTree()
        self.__testViewByIds_apiIndependent(vc)

    def testGetViewsById_api17(self):
        vc = self.__mockTree(version=17)
        self.__testViewByIds_apiIndependent(vc)

    def testGetViewsById_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        self.__testViewByIds_apiIndependent(vc)

    def testNewViewClientInstancesDontDuplicateTree(self):
        vc = {}
        n = {}
        for i in range(10):
            vc[i] = self.__mockTree()
            n[i] = len(vc[i].getViewIds())

        for i in range(1, 10):
            self.assertEquals(n[0], n[i])

    def testTraverseShowClassIdAndText(self):
        device = MockDevice()
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        treeStr = StringIO.StringIO()
        vc.traverse(root=root, transform=ViewClient.TRAVERSE_CIT, stream=treeStr)
        self.assertNotEquals(None, treeStr.getvalue())
        lines = treeStr.getvalue().splitlines()
        self.assertEqual(5, len(lines))
        self.assertEqual('None None 0', lines[0])
        citRE = re.compile(' +None None \d+')
        for l in lines[1:]:
            self.assertTrue(citRE.match(l))


    def testTraverseShowClassIdTextAndCenter(self):
        device = MockDevice()
        root = View({'mID':'0', 'text:mText':'0', 'layout:mLeft':0, 'layout:mTop':0}, device)
        root.add(View({'mID':'1', 'text:mText':'1', 'layout:mLeft':1, 'layout:mTop':1}, device))
        root.add(View({'mID':'2', 'text:mText':'2', 'layout:mLeft':2, 'layout:mTop':2}, device))
        v3 = View({'mID':'3', 'text:mText':'3', 'layout:mLeft':3, 'layout:mTop':3}, device)
        root.add(v3)
        v35 = View({'mID':'5', 'text:mText':'5', 'getTag()':'v35', 'layout:mLeft':5, 'layout:mTop':5}, device)
        v3.add(v35)
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        treeStr = StringIO.StringIO()
        vc.traverse(root=root, transform=ViewClient.TRAVERSE_CITC, stream=treeStr)
        self.assertNotEquals(None, treeStr.getvalue())
        lines = treeStr.getvalue().splitlines()
        self.assertEqual(5, len(lines))
        self.assertEqual('None 0 0 (0, 0)', lines[0])
        citRE = re.compile(' +None \d+ \d+ \(\d+, \d+\)')
        for l in lines[1:]:
            self.assertTrue(citRE.match(l))

    def __getClassAndId(self, view):
        try:
            return "%s %s %s %s" % (view.getClass(), view.getId(), view.getUniqueId(), view.getCoords())
        except Exception, e:
            return "Exception in view=%s: %s" % (view.__smallStr__(), e)

    def __eatIt(self, view):
        return ""

    def testViewWithNoIdReceivesUniqueId(self):
        vc = self.__mockTree()

        # We know there are 6 views without id in the mock tree
        for i in range(1, 6):
            self.assertNotEquals(None, vc.findViewById("id/no_id/%d" % i))

    def testTextWithSpaces(self):
        vc = self.__mockTree()
        self.assertNotEqual(None, vc.findViewWithText('Medium Text'))

    def testTextWithVeryLargeContent(self):
        TEXT = """\
MOCK@412a9d08 mID=7,id/test drawing:mForeground=4,null padding:mForegroundPaddingBottom=1,0 text:mText=319,[!   "   #   $   %   &   '   (   )   *   +   ,   -   .   /   0   1   2   3   4   5   6   7   8   9   :   ;   <   =   >   ?   @   A   B   C   D   E   F   G   H   I   J   K   L   M   N   O   P   Q   R   S   T   U   V   W   X   Y   Z   [   \   ]   ^   _   `   a   b   c   d   e   f   g   h   i   j   k   l   m   n   o   p] mViewFlags=11,-1744830336\
"""
        vc = self.__mockTree(TEXT)
        test = vc.findViewById('id/test')
        text = test.getText()
        self.assertEqual(319, len(text))
        self.assertEqual('[', text[0])
        self.assertEqual(']', text[318])
        self.assertEqual('-1744830336', test['mViewFlags'])

    def testActionBarSubtitleCoordinates(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        toggleButton = vc.findViewById('id/button_with_id')
        self.assertNotEqual(None, toggleButton)
        textView3 = vc.findViewById('id/textView3')
        self.assertNotEqual(None, textView3)
        x = toggleButton.getX()
        y = toggleButton.getY()
        w = toggleButton.getWidth()
        h = toggleButton.getHeight()
        xy = toggleButton.getXY()
        coords = toggleButton.getCoords()
        self.assertNotEqual(None, textView3.getText())
        self.assertNotEqual("", textView3.getText().strip())
        list = [ eval(v) for v in textView3.getText().strip().split() ]
        tx = list[0][0]
        ty = list[0][1]
        tsx = list[1][0]
        tsy = list[1][1]
        self.assertEqual(tx, x)
        self.assertEqual(ty, y)
        self.assertEqual((tsx, tsy), xy)
        self.assertEqual(((tsx, tsy), (xy[0] + w, xy[1] + h)), coords)

    def testServiceStoppedAfterDestructor(self):
        device = MockDevice()
        self.assertTrue(device.service == STOPPED)
        if True:
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            self.assertTrue(device.service == RUNNING)
            vc.__del__()
        # Perhpas there are other ViewClients using the same server, we cannot expect it stops
        #self.assertTrue(device.service == STOPPED)

    def testList(self):
        vc = self.__mockWindows()
        self.assertNotEqual(None, vc.windows)

    def testFindViewByIdOrRaise(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        vc.findViewByIdOrRaise('id/up')

    def testFindViewByIdOrRaise_api17(self):
        vc = self.__mockTree(version=17)
        vc.traverse()
        vc.findViewByIdOrRaise('id/no_id/9')

    def testFindViewByIdOrRaise_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        vc.traverse()
        vc.findViewByIdOrRaise('id/no_id/21')

    def testFindViewByIdOrRaise_nonExistentView(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        try:
            vc.findViewByIdOrRaise('id/nonexistent')
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewByIdOrRaise_nonExistentView_api17(self):
        vc = self.__mockTree(version=17)
        try:
            vc.findViewByIdOrRaise('id/nonexistent')
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewByIdOrRaise_nonExistentView_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        try:
            vc.findViewByIdOrRaise('id/nonexistent')
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewById_root(self):
        device = None
        root = View({'mID':'0'}, device)
        root.add(View({'mID':'1'}, device))
        root.add(View({'mID':'2'}, device))
        v3 = View({'mID':'3'}, device)
        root.add(v3)
        v35 = View({'mID':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'mID':'4'}, device)
        root.add(v4)
        v45 = View({'mID':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewById('5')
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewById('5', root=v4)
        self.assertNotEqual(v5, None)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewById('5', root=v3)
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())

    def testFindViewById_viewFilter(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        def vf(view):
            return view.getClass() == 'android.widget.ImageView'
        view = vc.findViewById('id/up', viewFilter=vf)
        self.assertNotEqual(view, None)

    def testFindViewById_viewFilterUnmatched(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        def vf(view):
            return view.getClass() == 'android.widget.TextView'
        view = vc.findViewById('id/up', viewFilter=vf)
        self.assertEqual(view, None)

    def testFindViewByIdOrRaise_root(self):
        device = None
        root = View({'mID':'0'}, device)
        root.add(View({'mID':'1'}, device))
        root.add(View({'mID':'2'}, device))
        v3 = View({'mID':'3'}, device)
        root.add(v3)
        v35 = View({'mID':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'mID':'4'}, device)
        root.add(v4)
        v45 = View({'mID':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewByIdOrRaise('5')
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewByIdOrRaise('5', root=v4)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewByIdOrRaise('5', root=v3)
        self.assertEqual('v35', v5.getTag())

    def testFindViewByIdOrRaise_viewFilter(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        def vf(view):
            return view.getClass() == 'android.widget.ImageView'
        view = vc.findViewByIdOrRaise('id/up', viewFilter=vf)

    def testFindViewByIdOrRaise_viewFilterUnmatched(self):
        vc = self.__mockTree(dump=DUMP_SAMPLE_UI)
        def vf(view):
            return view.getClass() == 'android.widget.TextView'
        try:
            view = vc.findViewByIdOrRaise('id/up', viewFilter=vf)
        except ViewNotFoundException:
            pass

    def testFindViewWithText_root(self):
        device = None
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewWithText('5')
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewWithText('5', root=v4)
        self.assertNotEqual(v5, None)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewWithText('5', root=v3)
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())

    def testFindViewWithText_regexRoot(self):
        device = None
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewWithText(re.compile('[5]'))
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewWithText(re.compile('[5]'), root=v4)
        self.assertNotEqual(v5, None)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewWithText(re.compile('[5]'), root=v3)
        self.assertNotEqual(v5, None)
        self.assertEqual('v35', v5.getTag())

    def testFindViewWithTextOrRaise_root(self):
        device = None
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewWithTextOrRaise('5')
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewWithTextOrRaise('5', root=v4)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewWithTextOrRaise('5', root=v3)
        self.assertEqual('v35', v5.getTag())

    def testFindViewWithTextOrRaise_root_disappearingView(self):
        device = None
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v5 = vc.findViewWithTextOrRaise('5')
        self.assertEqual('v35', v5.getTag())
        v5 = vc.findViewWithTextOrRaise('5', root=v4)
        self.assertEqual('v45', v5.getTag())
        v5 = vc.findViewWithTextOrRaise('5', root=v3)
        self.assertEqual('v35', v5.getTag())
        # Then remove v4 and its children
        root.children.remove(v4)
        #vc.dump()
        v4 = vc.findViewWithText('4')
        self.assertEqual(v4, None, "v4 has not disappeared")

    def testFindViewWithTextOrRaise_rootNonExistent(self):
        device = None
        root = View({'text:mText':'0'}, device)
        root.add(View({'text:mText':'1'}, device))
        root.add(View({'text:mText':'2'}, device))
        v3 = View({'text:mText':'3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'5', 'getTag()':'v35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'5', 'getTag()':'v45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        try:
            vc.findViewWithTextOrRaise('Non Existent', root=v4)
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewWithTextOrRaise_api17(self):
        vc = self.__mockTree(version=17)
        vc.findViewWithTextOrRaise("Apps")

    def testFindViewWithTextOrRaise_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        vc.traverse(transform=ViewClient.TRAVERSE_CIT)
        vc.findViewWithTextOrRaise(u'语言')

    def testFindViewWithTextOrRaise_nonExistent_api17(self):
        vc = self.__mockTree(version=17)
        try:
            vc.findViewWithTextOrRaise('nonexistent text')
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewWithTextOrRaise_nonExistent_api17_zh(self):
        vc = self.__mockTree(version=17, language='zh')
        try:
            vc.findViewWithTextOrRaise(u'不存在的文本')
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewWithContentDescription_root(self):
        device = None
        root = View({'text:mText':'0', 'content-desc':'CD0'}, device)
        root.add(View({'text:mText':'1', 'content-desc':'CD1'}, device))
        root.add(View({'text:mText':'2', 'content-desc':'CD2'}, device))
        v3 = View({'text:mText':'3', 'content-desc':'CD3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'35', 'content-desc':'CD35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4', 'conent-desc':'CD4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'45', 'content-desc':'CD45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v45 = vc.findViewWithContentDescription('CD45')
        self.assertNotEqual(v45, None)
        self.assertEqual('45', v45.getText())
        v45 = vc.findViewWithContentDescription('CD45', root=v4)
        self.assertNotEqual(v45, None)
        self.assertEqual('45', v45.getText())
        v35 = vc.findViewWithContentDescription('CD35', root=v3)
        self.assertNotEqual(v35, None)
        self.assertEqual('35', v35.getText())

    def testFindViewWithContentDescription_regexRoot(self):
        device = None
        root = View({'text:mText':'0', 'content-desc':'CD0'}, device)
        root.add(View({'text:mText':'1', 'content-desc':'CD1'}, device))
        root.add(View({'text:mText':'2', 'content-desc':'CD2'}, device))
        v3 = View({'text:mText':'3', 'content-desc':'CD3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'35', 'content-desc':'CD35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4', 'conent-desc':'CD4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'45', 'content-desc':'CD45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v45 = vc.findViewWithContentDescription(re.compile('CD4\d'))
        self.assertNotEqual(v45, None)
        self.assertEqual('45', v45.getText())
        v45 = vc.findViewWithContentDescription(re.compile('CD4\d'), root=v4)
        self.assertNotEqual(v45, None)
        self.assertEqual('45', v45.getText())
        v35 = vc.findViewWithContentDescription(re.compile('CD3\d'), root=v3)
        self.assertNotEqual(v35, None)
        self.assertEqual('35', v35.getText())

    def testFindViewWithContentDescriptionOrRaise_root(self):
        device = None
        root = View({'text:mText':'0', 'content-desc':'CD0'}, device)
        root.add(View({'text:mText':'1', 'content-desc':'CD1'}, device))
        root.add(View({'text:mText':'2', 'content-desc':'CD2'}, device))
        v3 = View({'text:mText':'3', 'content-desc':'CD3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'35', 'content-desc':'CD35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4', 'conent-desc':'CD4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'45', 'content-desc':'CD45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        v45 = vc.findViewWithContentDescriptionOrRaise('CD45')
        self.assertEqual('45', v45.getText())
        v45 = vc.findViewWithContentDescriptionOrRaise('CD45', root=v4)
        self.assertEqual('45', v45.getText())
        v35 = vc.findViewWithContentDescriptionOrRaise('CD35', root=v3)
        self.assertEqual('35', v35.getText())

    def testFindViewWithContentDescriptionOrRaise_rootNonExistent(self):
        device = None
        root = View({'text:mText':'0', 'content-desc':'CD0'}, device)
        root.add(View({'text:mText':'1', 'content-desc':'CD1'}, device))
        root.add(View({'text:mText':'2', 'content-desc':'CD2'}, device))
        v3 = View({'text:mText':'3', 'content-desc':'CD3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'35', 'content-desc':'CD35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4', 'conent-desc':'CD4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'45', 'content-desc':'CD45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        try:
            vc.findViewWithContentDescriptionOrRaise('Non Existent', root=v4)
            self.fail()
        except ViewNotFoundException:
            pass

    def testFindViewWithContentDescriptionOrRaiseExceptionMessage_regexpRoot(self):
        device = None
        root = View({'text:mText':'0', 'content-desc':'CD0'}, device)
        root.add(View({'text:mText':'1', 'content-desc':'CD1'}, device))
        root.add(View({'text:mText':'2', 'content-desc':'CD2'}, device))
        v3 = View({'text:mText':'3', 'content-desc':'CD3'}, device)
        root.add(v3)
        v35 = View({'text:mText':'35', 'content-desc':'CD35'}, device)
        v3.add(v35)
        v4 = View({'text:mText':'4', 'conent-desc':'CD4'}, device)
        root.add(v4)
        v45 = View({'text:mText':'45', 'content-desc':'CD45'}, device)
        v4.add(v45)
        device = MockDevice()
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
        self.assertNotEquals(None, vc)
        vc.root = root
        try:
            vc.findViewWithContentDescriptionOrRaise(re.compile('Non Existent'), root=v4)
            self.fail()
        except ViewNotFoundException, e:
            self.assertNotEquals(None, re.search("that matches 'Non Existent'", e.message))

    def testUiAutomatorDump(self):
        device = MockDevice(version=16)
        vc = ViewClient(device, device.serialno, adb=TRUE, autodump=True)

    def testUiAutomatorKilled(self):
        device = MockDevice(version=16, uiautomatorkilled=True)
        try:
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=True, ignoreuiautomatorkilled=True)
        except Exception, e:
            self.assertIsNotNone(re.search('''ERROR: UiAutomator output contains no valid information. UiAutomator was killed, no reason given.''', str(e)))

    def testUiViewServerDump(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            vc.dump()
            vc.findViewByIdOrRaise('id/home')
        finally:
            if device:
                device.shutdownMockViewServer()

    def testUiViewServerDump_windowStr(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            vc.dump(window='StatusBar')
            vc.findViewByIdOrRaise('id/status_bar')
        finally:
            if device:
                device.shutdownMockViewServer()

    def testUiViewServerDump_windowInt(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            vc.dump(window=0xb52f7c88)
            vc.findViewByIdOrRaise('id/status_bar')
        finally:
            if device:
                device.shutdownMockViewServer()

    def testUiViewServerDump_windowIntStr(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            vc.dump(window='0xb52f7c88')
            vc.findViewByIdOrRaise('id/status_bar')
        finally:
            if device:
                device.shutdownMockViewServer()

    def testUiViewServerDump_windowIntM1(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE, autodump=False)
            vc.dump(window=-1)
            vc.findViewByIdOrRaise('id/home')
        finally:
            if device:
                device.shutdownMockViewServer()

    def testFindViewsContainingPoint_api15(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE)
            list = vc.findViewsContainingPoint((200, 200))
            self.assertNotEquals(None, list)
            self.assertNotEquals(0, len(list))
        finally:
            if device:
                device.shutdownMockViewServer()

    def testFindViewsContainingPoint_api17(self):
        device = MockDevice(version=17)
        vc = ViewClient(device, device.serialno, adb=TRUE)
        list = vc.findViewsContainingPoint((55, 75))
        self.assertNotEquals(None, list)
        self.assertNotEquals(0, len(list))

    def testFindViewsContainingPoint_filterApi15(self):
        device = None
        try:
            device = MockDevice(version=15, startviewserver=True)
            vc = ViewClient(device, device.serialno, adb=TRUE)
            list = vc.findViewsContainingPoint((200, 200), filter=View.isClickable)
            self.assertNotEquals(None, list)
            self.assertNotEquals(0, len(list))
        finally:
            if device:
                device.shutdownMockViewServer()

    def testFindViewsContainingPoint_filterApi17(self):
        device = MockDevice(version=17)
        vc = ViewClient(device, device.serialno, adb=TRUE)
        list = vc.findViewsContainingPoint((55, 75), filter=View.isClickable)
        self.assertNotEquals(None, list)
        self.assertNotEquals(0, len(list))

if __name__ == "__main__":
    print >> sys.stderr, "ViewClient.__main__:"
    print >> sys.stderr, "argv=", sys.argv
    #import sys;sys.argv = ['', 'Test.testName']
    #sys.argv.append('ViewClientTest.testFindViewsContainingPoint_filterApi17')
    unittest.main()

########NEW FILE########
__FILENAME__ = viewclientconnected
'''
Created on 2012-10-25

@author: diego
'''

import sys
import os
import unittest


# PyDev sets PYTHONPATH, use it
try:
    for p in os.environ['PYTHONPATH'].split(':'):
        if not p in sys.path:
            sys.path.append(p)
except:
    pass

try:
    sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
    pass

from com.dtmilano.android.viewclient import *
from mocks import MockDevice

VERBOSE = True

# NOTE:
# Because there's no way of disconnect a MonkeyDevice and there's no
# either the alternative of connecting twice from the same script
# this is the only alternative
SERIALNO = 'emulator-5554'
sys.argv = ['ViewClientConnectedTest', SERIALNO]
device, serialno = ViewClient.connectToDeviceOrExit(verbose=VERBOSE, serialno=SERIALNO)

class ViewClientConnectedTest(unittest.TestCase):

    def setUp(self):
        self.device = device
        self.serialno = serialno


    def tearDown(self):
        # WARNING:
        # There's no way of disconnect the device
        pass


    def testInit_adbNone(self):
        device = MockDevice()
        vc = ViewClient(device, serialno, adb=None, autodump=False)
        self.assertNotEqual(None, vc)

    def testAutodumpVsDump(self):
        vc = ViewClient(self.device, self.serialno, forceviewserveruse=True)
        ids = vc.getViewIds()
        views = vc.dump()
        self.assertEquals(len(ids), len(views))

    def testNewViewClientInstancesDontDuplicateTreeConnected(self):
        vc = {}
        n = {}
        m = {}
        d = {}

        for i in range(10):
            vc[i] = ViewClient(self.device, self.serialno, forceviewserveruse=True)
            n[i] = len(vc[i].getViewIds())
            m[i] = len(vc[i].dump())
            d[i] = len(vc[i].getViewIds())
            if VERBOSE:
                print "Pass %d: Found %d views and %d after dump with %d view Ids" % \
                    (i, n[i], m[i], d[i])

        for i in range(1, 10):
            self.assertEquals(n[0], n[i])
            self.assertEquals(n[0], m[i])
            self.assertEquals(n[0], d[i])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

########NEW FILE########
