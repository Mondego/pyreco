__FILENAME__ = class
# -*- coding: utf-8 -*-
#
#  ___FILENAME___
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

#import os
#import sys



########NEW FILE########
__FILENAME__ = class
# -*- coding: utf-8 -*-
#
#  ___FILENAME___
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

class ___FILEBASENAMEASIDENTIFIER___(NSDocument):
    def windowNibName(self):
        # Implement this to return a nib to load OR 
        # implement -makeWindowControllers to manually create your controllers.
        return u"___FILEBASENAMEASIDENTIFIER___"

    def windowControllerDidLoadNib_(self, aController):
        super(___FILEBASENAMEASIDENTIFIER___, self).windowControllerDidLoadNib_(aController)
        # Any UI customization that must be done after the NIB is loaded goes here.

    def dataOfType_error_(self, typeName, outError):
        # Insert code here to write your document to data of the specified type. If the given outError != NULL, 
        # ensure that you set *outError when returning nil.  You can also choose to override -fileWrapperOfType:error:, -writeToURL:ofType:error:,
        # or -writeToURL:ofType:forSaveOperation:originalContentsURL:error: instead.
        return None

    def readFromData_ofType_error_(self, data, typeName, outError):
        # Insert code here to read your document from the given data of the specified type.  If the given outError != NULL,
        # ensure that you set *outError when returning NO.  You can also choose to override -readFromFileWrapper:ofType:error:
        # or -readFromURL:ofType:error: instead. 
        return NO

########NEW FILE########
__FILENAME__ = class
# -*- coding: utf-8 -*-
#
#  ___FILENAME___
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from Foundation import *

class ___FILEBASENAMEASIDENTIFIER___(NSObject):
    pass

########NEW FILE########
__FILENAME__ = class
# -*- coding: utf-8 -*-
#
#  ___FILENAME___
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

class ___FILEBASENAMEASIDENTIFIER___(NSView):
    def initWithFrame_(self, frame):
        self = super(___FILEBASENAMEASIDENTIFIER___, self).initWithFrame_(frame)
        if self:
            # initialization code here
            pass
        return self

    def drawRect_(self, rect):
        # drawing code here


########NEW FILE########
__FILENAME__ = class
# -*- coding: utf-8 -*-
#
#  ___FILENAME___
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

class ___FILEBASENAMEASIDENTIFIER___(NSWindowController):
    pass

########NEW FILE########
__FILENAME__ = AppDelegate
# -*- coding: utf-8 -*-
#
#  ___PROJECTNAMEASIDENTIFIER___AppDelegate.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from Foundation import *
from AppKit import *

class ___VARIABLE_classPrefix:identifier___AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, sender):
        NSLog("Application did finish launching.")

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#  main.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

# import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import ___VARIABLE_classPrefix:identifier___AppDelegate

# pass control to AppKit
AppHelper.runEventLoop()

########NEW FILE########
__FILENAME__ = AppDelegate
# -*- coding: utf-8 -*-
#
#  ___PROJECTNAMEASIDENTIFIER___AppDelegate.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *
from CoreData import *

import os

class ___VARIABLE_classPrefix:identifier___AppDelegate(NSObject):
    window = IBOutlet()
    _managedObjectModel = None
    _persistentStoreCoordinator = None
    _managedObjectContext = None
    
    def applicationDidFinishLaunching_(self, sender):
        self.managedObjectContext()

    def applicationSupportFolder(self):
        paths = NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory, NSUserDomainMask, YES)
        basePath = paths[0] if (len(paths) > 0) else NSTemporaryDirectory()
        return os.path.join(basePath, "___PROJECTNAMEASIDENTIFIER___")

    def managedObjectModel(self):
        if self._managedObjectModel: return self._managedObjectModel
            
        self._managedObjectModel = NSManagedObjectModel.mergedModelFromBundles_(None)
        return self._managedObjectModel
    
    def persistentStoreCoordinator(self):
        if self._persistentStoreCoordinator: return self._persistentStoreCoordinator
        
        applicationSupportFolder = self.applicationSupportFolder()
        if not os.path.exists(applicationSupportFolder):
            os.mkdir(applicationSupportFolder)
        
        storePath = os.path.join(applicationSupportFolder, "___PROJECTNAMEASIDENTIFIER___.xml")
        url = NSURL.fileURLWithPath_(storePath)
        self._persistentStoreCoordinator = NSPersistentStoreCoordinator.alloc().initWithManagedObjectModel_(self.managedObjectModel())
        
        success, error = self._persistentStoreCoordinator.addPersistentStoreWithType_configuration_URL_options_error_(NSXMLStoreType, None, url, None, None)
        if not success:
            NSApp().presentError_(error)
        
        return self._persistentStoreCoordinator
        
    def managedObjectContext(self):
        if self._managedObjectContext:  return self._managedObjectContext
        
        coordinator = self.persistentStoreCoordinator()
        if coordinator:
            self._managedObjectContext = NSManagedObjectContext.alloc().init()
            self._managedObjectContext.setPersistentStoreCoordinator_(coordinator)
        
        return self._managedObjectContext
    
    def windowWillReturnUndoManager_(self, window):
        return self.managedObjectContext().undoManager()
        
    @IBAction
    def saveAction_(self, sender):
        success, error = self.managedObjectContext().save_(None)
        if not success:
            NSApp().presentError_(error)

    def applicationShouldTerminate_(self, sender):
        if not self._managedObjectContext:
            return NSTerminateNow
            
        if not self._managedObjectContext.commitEditing():
            NSLog(u'Delegate unable to commit editing to terminate')
            return NSTerminateCancel
        
        if not self._managedObjectContext.hasChanges():
            return NSTerminateNow
            
        success, error = self._managedObjectContext.save_(None)
        
        if success:
            return NSTerminateNow
        
        if NSApp().presentError_(error):
            return NSTerminateCancel
        else:
            question = NSLocalizedString(
                u"Could not save changes while quitting. Quit anyway?",
                u"Quit without saves error question message")
            info = NSLocalizedString(
                u"Quitting now will lose any changes you have made since the last successful save",
                u"Quit without saves error question info")
            quitButton = NSLocalizedString(
                "Quit anyway", "Quit anyway button title")
            cancelButton = NSLocalizedString(
                u"Cancel", u"Cancel button title")
            alert = NSAlert.alloc().init().autorelease()
            alert.setMessageText_(question)
            alert.setInformativeText_(info)
            alert.addButtonWithTitle_(quitButton)
            alert.addButtonWithTitle_(cancelButton)
            
            answer = alert.runModal()
    
            if answer == NSAlertAlternateReturn:
                return NSTerminateCancel

        return NSTerminateNow

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#  main.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

# import modules required by application
import objc
import Foundation
import AppKit
import CoreData

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import ___VARIABLE_classPrefix:identifier___AppDelegate

# pass control to AppKit
AppHelper.runEventLoop()

########NEW FILE########
__FILENAME__ = CocoaAppDocument
# -*- coding: utf-8 -*-
#
#  ___PROJECTNAMEASIDENTIFIER___Document.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from Foundation import *
from CoreData import *
from AppKit import *

class ___VARIABLE_classPrefix___Document(NSPersistentDocument):
    def init(self):
        self = super(___VARIABLE_classPrefix___Document, self).init()
        # initialization code
        return self
        
    def windowNibName(self):
        return u"___VARIABLE_classPrefix___Document"
    
    def windowControllerDidLoadNib_(self, aController):
        super(___VARIABLE_classPrefix___Document, self).windowControllerDidLoadNib_(aController)
        # user interface preparation code

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#  main.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

# import modules required by application
import objc
import Foundation
import AppKit
import CoreData

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import ___VARIABLE_classPrefix:identifier___Document

# pass control to AppKit
AppHelper.runEventLoop()

########NEW FILE########
__FILENAME__ = CocoaAppDocument
# -*- coding: utf-8 -*-
#
#  ___PROJECTNAMEASIDENTIFIER___Document.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

from Foundation import *
from AppKit import *

class ___VARIABLE_classPrefix:identifier___Document(NSDocument):
    def init(self):
        self = super(___VARIABLE_classPrefix:identifier___Document, self).init()
        # initialization code
        return self
        
    def windowNibName(self):
        return u"___VARIABLE_classPrefix:identifier___Document"
    
    def windowControllerDidLoadNib_(self, aController):
        super(___VARIABLE_classPrefix:identifier___Document, self).windowControllerDidLoadNib_(aController)

    def dataOfType_error_(self, typeName, outError):
        return None, NSError.errorWithDomain_code_userInfo_(NSOSStatusErrorDomain, -4, None) # -4 is unimpErr from CarbonCore
    
    def readFromData_ofType_error_(self, data, typeName, outError):
        return NO, NSError.errorWithDomain_code_userInfo_(NSOSStatusErrorDomain, -4, None) # -4 is unimpErr from CarbonCore

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#  main.py
#  ___PROJECTNAME___
#
#  Created by ___FULLUSERNAME___ on ___DATE___.
#  Copyright (c) ___YEAR___ ___ORGANIZATIONNAME___. All rights reserved.
#

# import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import ___VARIABLE_classPrefix:identifier___Document

# pass control to AppKit
AppHelper.runEventLoop()

########NEW FILE########
