__FILENAME__ = IEDAddPkgController
# -*- coding: utf-8 -*-
#
#  IEDAddPkgController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-22.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from AppKit import *
from objc import IBAction, IBOutlet
import os.path

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage, LogException
from IEDUtil import *
from IEDPackage import *


class IEDAddPkgController(NSObject):
    
    addPkgLabel = IBOutlet()
    tableView = IBOutlet()
    removeButton = IBOutlet()
    
    movedRowsType = u"se.gu.it.AdditionalPackages"
    
    def init(self):
        self = super(IEDAddPkgController, self).init()
        if self is None:
            return None
        
        self.packages = list()
        self.packagePaths = set()
        
        return self
    
    def awakeFromNib(self):
        self.tableView.setDataSource_(self)
        self.tableView.registerForDraggedTypes_([NSFilenamesPboardType, IEDAddPkgController.movedRowsType])
        self.dragEnabled = True
    
    # Helper methods.
    
    def disableControls(self):
        self.dragEnabled = False
        self.addPkgLabel.setTextColor_(NSColor.disabledControlTextColor())
        self.tableView.setEnabled_(False)
        self.removeButton.setEnabled_(False)
    
    def enableControls(self):
        self.dragEnabled = True
        self.addPkgLabel.setTextColor_(NSColor.controlTextColor())
        self.tableView.setEnabled_(True)
        self.removeButton.setEnabled_(True)
    
    
    
    # External state of controller.
    
    def packagesToInstall(self):
        return self.packages
    
    
    
    # Loading.
    
    def replacePackagesWithPaths_(self, packagePaths):
        del self.packages[:]
        self.packagePaths.clear()
        for path in packagePaths:
            package = IEDPackage.alloc().init()
            package.setName_(os.path.basename(path))
            package.setPath_(path)
            package.setSize_(IEDUtil.getPackageSize_(path))
            package.setImage_(NSWorkspace.sharedWorkspace().iconForFile_(path))
            self.packages.append(package)
            self.packagePaths.add(path)
        self.tableView.reloadData()
    
    
    
    # Act on remove button.
    
    @LogException
    @IBAction
    def removeButtonClicked_(self, sender):
        indexes = self.tableView.selectedRowIndexes()
        row = indexes.lastIndex()
        while row != NSNotFound:
            self.packagePaths.remove(self.packages[row].path())
            del self.packages[row]
            row = indexes.indexLessThanIndex_(row)
        self.tableView.reloadData()
        self.tableView.deselectAll_(self)
    
    
    
    # We're an NSTableViewDataSource.
    
    def numberOfRowsInTableView_(self, tableView):
        return len(self.packages)
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        # FIXME: Use bindings.
        if column.identifier() == u"image":
            return self.packages[row].image()
        elif column.identifier() == u"name":
            return self.packages[row].name()
    
    def tableView_validateDrop_proposedRow_proposedDropOperation_(self, tableView, info, row, operation):
        if not self.dragEnabled:
            return NSDragOperationNone
        if info.draggingSource() == tableView:
            return NSDragOperationMove
        pboard = info.draggingPasteboard()
        paths = [IEDUtil.resolvePath_(path) for path in pboard.propertyListForType_(NSFilenamesPboardType)]
        if not paths:
            return NSDragOperationNone
        for path in paths:
            # Don't allow multiple copies.
            if path in self.packagePaths:
                return NSDragOperationNone
            # Ensure the file extension is pkg or mpkg.
            name, ext = os.path.splitext(path)
            if ext.lower() not in (u".pkg", u".mpkg", u".app", u".dmg"):
                return NSDragOperationNone
        return NSDragOperationCopy
    
    def tableView_acceptDrop_row_dropOperation_(self, tableView, info, row, operation):
        if not self.dragEnabled:
            return False
        pboard = info.draggingPasteboard()
        # If the source is the tableView, we're reordering packages within the
        # table and the pboard contains the source row indexes.
        if info.draggingSource() == tableView:
            indexes = [int(i) for i in pboard.propertyListForType_(IEDAddPkgController.movedRowsType).split(u",")]
            # If the rows are dropped on top of another line, and the target
            # row is below the first source row, move the target row one line
            # down.
            if (operation == NSTableViewDropOn) and (indexes[0] < row):
                rowAdjust = 1
            else:
                rowAdjust = 0
            # Move the dragged rows out from the package list into draggedRows.
            draggedRows = list()
            for i in sorted(indexes, reverse=True):
                draggedRows.insert(0, (i, self.packages.pop(i)))
            # Adjust the target row since we have removed items.
            row -= len([x for x in draggedRows if x[0] < row])
            row += rowAdjust
            # Insert them at the new place.
            for i, (index, item) in enumerate(draggedRows):
                self.packages.insert(row + i, item)
            # Select the newly moved lines.
            selectedIndexes = NSIndexSet.indexSetWithIndexesInRange_(NSMakeRange(row, len(draggedRows)))
            tableView.selectRowIndexes_byExtendingSelection_(selectedIndexes, False)
        else:
            # Otherwise it's a list of paths to add to the table.
            paths = [IEDUtil.resolvePath_(path) for path in pboard.propertyListForType_(NSFilenamesPboardType)]
            # Remove duplicates from list.
            seen = set()
            paths = [x for x in paths if x not in seen and not seen.add(x)]
            for i, path in enumerate(paths):
                package = IEDPackage.alloc().init()
                package.setName_(os.path.basename(path))
                package.setPath_(path)
                package.setSize_(IEDUtil.getPackageSize_(path))
                package.setImage_(NSWorkspace.sharedWorkspace().iconForFile_(path))
                self.packages.insert(row + i, package)
                self.packagePaths.add(path)
        tableView.reloadData()
        return True
    
    def tableView_writeRowsWithIndexes_toPasteboard_(self, tableView, rowIndexes, pboard):
        # When reordering packages put a list of indexes as a string onto the pboard.
        indexes = list()
        index = rowIndexes.firstIndex()
        while index != NSNotFound:
            indexes.append(index)
            index = rowIndexes.indexGreaterThanIndex_(index)
        pboard.declareTypes_owner_([IEDAddPkgController.movedRowsType], self)
        pboard.setPropertyList_forType_(u",".join(unicode(i) for i in indexes), IEDAddPkgController.movedRowsType)
        return True

########NEW FILE########
__FILENAME__ = IEDAppDelegate
# -*- coding: utf-8 -*-
#
#  IEDAppDelegate.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-09-19.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from AppKit import *
from objc import IBAction, IBOutlet, __version__ as pyObjCVersion

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage, LogException
from IEDUtil import *
import platform


defaults = NSUserDefaults.standardUserDefaults()


class IEDAppDelegate(NSObject):
    
    mainWindowController = IBOutlet()
    appVersionController = IBOutlet()
    
    def init(self):
        self = super(IEDAppDelegate, self).init()
        if self is None:
            return None
        
        return self
    
    def initialize(self):
        # Log version info on startup.
        version, build = IEDUtil.getAppVersion()
        LogInfo(u"AutoDMG v%@ build %@", version, build)
        name, version, build = IEDUtil.readSystemVersion_(u"/")
        LogInfo(u"%@ %@ %@", name, version, build)
        LogInfo(u"%@ %@ (%@)", platform.python_implementation(),
                               platform.python_version(),
                               platform.python_compiler())
        LogInfo(u"PyObjC %@", pyObjCVersion)
        
        # Initialize user defaults before application starts.
        defaultsPath = NSBundle.mainBundle().pathForResource_ofType_(u"Defaults", u"plist")
        defaultsDict = NSDictionary.dictionaryWithContentsOfFile_(defaultsPath)
        defaults.registerDefaults_(defaultsDict)
    
    def applicationDidFinishLaunching_(self, sender):
        version, build = IEDUtil.getAppVersion()
        if version.lower().endswith(u"b"):
            NSApplication.sharedApplication().dockTile().setBadgeLabel_(u"beta")
        updateProfileInterval = defaults.integerForKey_(u"UpdateProfileInterval")
        if updateProfileInterval:
            lastCheck = defaults.objectForKey_(u"LastUpdateProfileCheck")
            if lastCheck.timeIntervalSinceNow() < -60 * 60 * 18:
                self.mainWindowController.updateController.checkForProfileUpdates_(self)
        
        appVersionCheckInterval = defaults.integerForKey_(u"AppVersionCheckInterval")
        if appVersionCheckInterval:
            lastCheck = defaults.objectForKey_(u"LastAppVersionCheck")
            if lastCheck.timeIntervalSinceNow() < -60 * 60 * 18:
                self.appVersionController.checkForAppUpdateSilently_(True)
    
    def applicationShouldTerminate_(self, sender):
        LogDebug(u"applicationShouldTerminate:")
        if self.mainWindowController.busy():
            alert = NSAlert.alloc().init()
            alert.setAlertStyle_(NSCriticalAlertStyle)
            alert.setMessageText_(u"Application busy")
            alert.setInformativeText_(u"Quitting now could leave the "
                                      u"system in an unpredictable state.")
            alert.addButtonWithTitle_(u"Quit")
            alert.addButtonWithTitle_(u"Stay")
            button = alert.runModal()
            if button == NSAlertSecondButtonReturn:
                return NSTerminateCancel
        return NSTerminateNow
    
    def applicationWillTerminate_(self, sender):
        LogDebug(u"applicationWillTerminate:")
        self.mainWindowController.cleanup()
    
    @LogException
    @IBAction
    def showHelp_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(defaults.stringForKey_(u"HelpURL")))
    
    
    
    # Trampolines for document handling.
    
    @LogException
    @IBAction
    def saveDocument_(self, sender):
        LogDebug(u"saveDocument:")
        self.mainWindowController.saveTemplate()
    
    @LogException
    @IBAction
    def saveDocumentAs_(self, sender):
        LogDebug(u"saveDocumentAs:")
        self.mainWindowController.saveTemplateAs()
    
    @LogException
    @IBAction
    def openDocument_(self, sender):
        LogDebug(u"openDocument:")
        self.mainWindowController.openTemplate()
    
    def validateMenuItem_(self, menuItem):
        return self.mainWindowController.validateMenuItem_(menuItem)
    
    def application_openFile_(self, application, filename):
        return self.mainWindowController.openTemplateAtURL_(NSURL.fileURLWithPath_(filename))

########NEW FILE########
__FILENAME__ = IEDAppVersionController
# -*- coding: utf-8 -*-
#
#  IEDAppVersionController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-31.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from objc import IBAction, IBOutlet

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage, LogException
from IEDUtil import *


class IEDAppVersionController(NSObject):
    
    def awakeFromNib(self):
        self.defaults = NSUserDefaults.standardUserDefaults()
    
    @LogException
    @IBAction
    def checkForAppUpdate_(self, sender):
        self.checkForAppUpdateSilently_(False)
    
    def checkForAppUpdateSilently_(self, silently):
        self.checkSilently = silently
        # Create a buffer for data.
        self.plistData = NSMutableData.alloc().init()
        # Start download.
        osVer, osBuild = IEDUtil.readSystemVersion_(u"/")[1:3]
        appVer, appBuild = IEDUtil.getAppVersion()
        urlString = u"%s?osVer=%s&osBuild=%s&appVer=%s&appBuild=%s" % (self.defaults.stringForKey_(u"AppVersionURL"),
                                                                       osVer,
                                                                       osBuild,
                                                                       appVer,
                                                                       appBuild)
        url = NSURL.URLWithString_(urlString)
        request = NSURLRequest.requestWithURL_(url)
        self.connection = NSURLConnection.connectionWithRequest_delegate_(request, self)
        LogDebug(u"connection = %@", self.connection)
        if not self.connection:
            LogWarning(u"Connection to %@ failed", url)
    
    def logFailure_(self, message):
        LogError(u"Version check failed: %@", message)
        if not self.checkSilently:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(u"Version check failed")
            alert.setInformativeText_(message)
            alert.runModal()
        
    def connection_didFailWithError_(self, connection, error):
        self.logFailure_(error.localizedDescription())
    
    def connection_didReceiveResponse_(self, connection, response):
        if response.statusCode() != 200:
            connection.cancel()
            message = NSString.stringWithFormat_(u"Server returned HTTP %d",
                                                 response.statusCode())
            self.logFailure_(message)
    
    def connection_didReceiveData_(self, connection, data):
        self.plistData.appendData_(data)
    
    def connectionDidFinishLoading_(self, connection):
        LogDebug(u"Downloaded version check data with %d bytes", self.plistData.length())
        # Decode the plist.
        plist, format, error = NSPropertyListSerialization.propertyListWithData_options_format_error_(self.plistData,
                                                                                                      NSPropertyListImmutable,
                                                                                                      None,
                                                                                                      None)
        if not plist:
            self.logFailure_(error.localizedDescription())
            return
        
        # Save the time stamp.
        self.defaults.setObject_forKey_(NSDate.date(), u"LastAppVersionCheck")
        
        # Get latest version and build.
        latestDisplayVersion = plist[u"Version"]
        if latestDisplayVersion.count(u".") == 1:
            latestPaddedVersion = latestDisplayVersion + u".0"
        else:
            latestPaddedVersion = latestDisplayVersion
        latestBuild = plist[u"Build"]
        latestVersionBuild = u"%s.%s" % (latestPaddedVersion, latestBuild)
        LogNotice(u"Latest published version is AutoDMG v%@ build %@", latestDisplayVersion, latestBuild)
        
        if self.checkSilently:
            # Check if we've already notified the user about this version.
            if latestVersionBuild == self.defaults.stringForKey_(u"NotifiedAppVersion"):
                LogDebug(u"User has already been notified of this version.")
                return
        
        # Convert latest version into a tuple with (major, minor, rev, build).
        latestTuple = tuple(int(x.strip(u"ab")) for x in latestVersionBuild.split(u"."))
        
        # Get the current version and convert it to a tuple.
        displayVersion, build = IEDUtil.getAppVersion()
        if displayVersion.count(u".") == 1:
            paddedVersion = displayVersion + u".0"
        else:
            paddedVersion = displayVersion
        versionBuild = u"%s.%s" % (paddedVersion, build)
        currentTuple = tuple(int(x.strip(u"ab")) for x in versionBuild.split(u"."))
        
        # Compare and notify
        if latestTuple > currentTuple:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(u"A new version of AutoDMG is available")
            alert.setInformativeText_(u"AutoDMG v%s build %s is available for download." % (latestDisplayVersion, latestBuild))
            alert.addButtonWithTitle_(u"Download")
            alert.addButtonWithTitle_(u"Skip")
            alert.addButtonWithTitle_(u"Later")
            button = alert.runModal()
            if button == NSAlertFirstButtonReturn:
                url = NSURL.URLWithString_(plist[u"URL"])
                NSWorkspace.sharedWorkspace().openURL_(url)
            elif button == NSAlertSecondButtonReturn:
                self.defaults.setObject_forKey_(latestVersionBuild, u"NotifiedAppVersion")
        elif not self.checkSilently:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(u"AutoDMG is up to date")
            if currentTuple > latestTuple:
                verString = u"bleeding edge"
            else:
                verString = u"current"
            alert.setInformativeText_(u"AutoDMG v%s build %s appears to be %s." % (displayVersion, build, verString))
            alert.runModal()

########NEW FILE########
__FILENAME__ = IEDCLIController
# -*- coding: utf-8 -*-
#
#  IEDCLIController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2014-01-28.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from AppKit import *

import os
import sys
import getpass
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
from IEDUpdateCache import *
from IEDProfileController import *
from IEDWorkflow import *
from IEDTemplate import *
from IEDUtil import *


class IEDCLIController(NSObject):
    """Main controller class for CLI interface.
    
    Methods starting with cmd are exposed as verbs to the CLI. A method named
    cmdVerb_() should have a corresponding addargsVerb_() that takes an
    argparser subparser object as its argument, which should be populated."""
    
    def init(self):
        self = super(IEDCLIController, self).init()
        if self is None:
            return None
        
        self.cache = IEDUpdateCache.alloc().initWithDelegate_(self)
        self.workflow = IEDWorkflow.alloc().initWithDelegate_(self)
        self.profileController = IEDProfileController.alloc().init()
        self.profileController.awakeFromNib()
        self.profileController.setDelegate_(self)
        self.cache.pruneAndCreateSymlinks(self.profileController.updatePaths)
        
        self.busy = False
        
        self.progressMax = 1.0
        self.lastMessage = u""
        
        self.hasFailed = False
        
        return self
    
    def listVerbs(self):
        return list(item[3:].rstrip(u"_").lower() for item in dir(self) if item.startswith(u"cmd"))
    
    def cleanup(self):
        self.workflow.cleanup()
    
    def waitBusy(self):
        runLoop = NSRunLoop.currentRunLoop()
        while self.busy:
            nextfire = runLoop.limitDateForMode_(NSDefaultRunLoopMode)
            if not self.busy:
                break
            if not runLoop.runMode_beforeDate_(NSDefaultRunLoopMode, nextfire):
                self.failWithMessage_(u"runMode:beforeDate: failed")
                break
    
    def failWithMessage_(self, message):
        LogError(u"%@", message)
        self.hasFailed = True
        self.busy = False
    
    
    # Build image.
    
    def cmdBuild_(self, args):
        """Build image"""
        
        # Parse arguments.
        
        sourcePath = IEDUtil.installESDPath_(args.source)
        if sourcePath:
            templatePath = None
        else:
            templatePath = self.checkTemplate_(args.source)
        
        if not sourcePath and not templatePath:
            self.failWithMessage_(u"'%s' is not a valid OS X installer or AutoDMG template" % args.source)
            return os.EX_DATAERR
        
        if templatePath:
            template = IEDTemplate.alloc().init()
            error = template.loadTemplateAndReturnError_(templatePath)
            if error:
                self.failWithMessage_(u"Couldn't load template from '%s': %s" % (templatePath, error))
                return os.EX_DATAERR
        else:
            template = IEDTemplate.alloc().initWithSourcePath_(sourcePath)
        
        if args.installer:
            template.setSourcePath_(args.installer)
        if args.output:
            template.setOutputPath_(args.output)
        if args.name:
            template.setVolumeName_(args.name)
        if args.updates is not None:
            template.setApplyUpdates_(True)
        if args.packages:
            if not template.setAdditionalPackages_(args.packages):
                self.failWithMessage_(u"Additional packages failed verification")
                return os.EX_DATAERR
        
        if not template.sourcePath:
            self.failWithMessage_(u"No source path")
            return os.EX_USAGE
        if not template.outputPath:
            self.failWithMessage_(u"No output path")
            return os.EX_USAGE
        
        LogNotice(u"Installer: %@", template.sourcePath)
        
        # Set the source.
        self.busy = True
        self.workflow.setSource_(template.sourcePath)
        self.waitBusy()
        if self.hasFailed:
            return os.EX_DATAERR
        
        template.resolveVariables_({
            u"OSNAME":      self.installerName,
            u"OSVERSION":   self.installerVersion,
            u"OSBUILD":     self.installerBuild,
        })
        
        LogNotice(u"Output Path: %@", template.outputPath)
        LogNotice(u"Volume Name: %@", template.volumeName)
        
        # Generate the list of updates to install.
        updates = list()
        if template.applyUpdates:
            profile = self.profileController.profileForVersion_Build_(self.installerVersion, self.installerBuild)
            if profile is None:
                self.failWithMessage_(self.profileController.whyNoProfileForVersion_build_(self.installerVersion,
                                                                                           self.installerBuild))
                return os.EX_DATAERR
            
            missingUpdates = list()
            
            for update in profile:
                LogNotice(u"Update: %@ (%@)", update[u"name"], IEDUtil.formatBytes_(update[u"size"]))
                package = IEDPackage.alloc().init()
                package.setName_(update[u"name"])
                package.setPath_(self.cache.updatePath_(update[u"sha1"]))
                package.setSize_(update[u"size"])
                package.setUrl_(update[u"url"])
                package.setSha1_(update[u"sha1"])
                if not self.cache.isCached_(update[u"sha1"]):
                    if args.download_updates:
                        missingUpdates.append(package)
                    else:
                        self.failWithMessage_(u"Can't apply updates, %s is missing from cache" % update[u"name"])
                        return os.EX_DATAERR
                updates.append(package)
            
            if missingUpdates:
                self.cache.downloadUpdates_(missingUpdates)
                self.busy = True
                self.waitBusy()
                if self.hasFailed:
                    self.failWithMessage_(u"Can't build due to updates missing from cache")
                    return 1    # EXIT_FAILURE
                updates.extend(missingUpdates)
                LogNotice(u"All updates for %@ %@ downloaded", self.installerVersion, self.installerBuild)
        
        # Generate the list of additional packages to install.
        template.resolvePackages()
        for package in template.packagesToInstall:
            LogNotice(u"Package: %@ (%@)", package.name(), IEDUtil.formatBytes_(package.size()))
        
        # Check the output path.
        if os.path.exists(template.outputPath):
            if args.force:
                try:
                    os.unlink(template.outputPath)
                except OSError as e:
                    self.failWithMessage_(u"Couldn't remove %s: %s" % (template.outputPath, unicode(e)))
                    return os.EX_CANTCREAT
            else:
                self.failWithMessage_(u"%s already exists" % template.outputPath)
                return os.EX_CANTCREAT
        else:
            outputDir = os.path.dirname(template.outputPath)
            if outputDir and not os.path.exists(outputDir):
                try:
                    os.makedirs(outputDir)
                except OSError as e:
                    self.failWithMessage_(u"%s does not exist and can't be created: %s" % (outputDir, unicode(e)))
                    return os.EX_CANTCREAT
        
        # If we're not running as root get the password for authentication.
        if os.getuid() != 0:
            username = getpass.getuser()
            password = getpass.getpass(u"Password for %s: " % username)
            self.workflow.setAuthUsername_(username)
            self.workflow.setAuthPassword_(password)
        
        # Start the workflow.
        self.busy = True
        self.workflow.setPackagesToInstall_(updates + template.packagesToInstall)
        self.workflow.setOutputPath_(template.outputPath)
        self.workflow.setVolumeName_(template.volumeName)
        self.workflow.setVolumeSize_(template.volumeSize)
        self.workflow.setTemplate_(template)
        self.workflow.start()
        self.waitBusy()
        if self.hasFailed:
            return 1    # EXIT_FAILURE
        
        return os.EX_OK
    
    def checkTemplate_(self, path):
        path = IEDUtil.resolvePath_(path)
        if not path:
            return None
        if not os.path.exists(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        if ext not in (u".plist", u".adtmpl"):
            return None
        return path
    
    def addargsBuild_(self, argparser):
        argparser.add_argument(u"source", help=u"OS X installer or AutoDMG template")
        argparser.add_argument(u"-o", u"--output", help=u"DMG output path")
        argparser.add_argument(u"-i", u"--installer", help=u"Override installer in template")
        argparser.add_argument(u"-n", u"--name", help=u"Installed system volume name")
        argparser.add_argument(u"-u", u"--updates", action=u"store_const", const=True, help=u"Apply updates")
        argparser.add_argument(u"-U", u"--download-updates", action=u"store_true", help=u"Download missing updates")
        argparser.add_argument(u"-f", u"--force", action=u"store_true", help=u"Overwrite output")
        argparser.add_argument(u"packages", nargs=u"*", help=u"Additional packages")
    
    
    
    # List updates.
    
    def cmdList_(self, args):
        """List updates"""
        
        profile = self.profileController.profileForVersion_Build_(args.version, args.build)
        if profile is None:
            self.failWithMessage_(self.profileController.whyNoProfileForVersion_build_(args.version, args.build))
            return os.EX_DATAERR
        
        LogNotice(u"%d update%@ for %@ %@:", len(profile), u"" if len(profile) == 1 else u"s", args.version, args.build)
        for update in profile:
            LogNotice(u"    %@%@ (%@)",
                      u"[cached] " if self.cache.isCached_(update[u"sha1"]) else u"",
                      update[u"name"],
                      IEDUtil.formatBytes_(update[u"size"]))
        
        return os.EX_OK
    
    def addargsList_(self, argparser):
        argparser.add_argument(u"version", help=u"OS X version")
        argparser.add_argument(u"build", help=u"OS X build")
    
    
    
    # Download updates.
    
    def cmdDownload_(self, args):
        """Download updates"""
        
        profile = self.profileController.profileForVersion_Build_(args.version, args.build)
        if profile is None:
            self.failWithMessage_(self.profileController.whyNoProfileForVersion_build_(args.version, args.build))
            return os.EX_DATAERR
        
        updates = list()
        for update in profile:
            if not self.cache.isCached_(update[u"sha1"]):
                package = IEDPackage.alloc().init()
                package.setName_(update[u"name"])
                package.setPath_(self.cache.updatePath_(update[u"sha1"]))
                package.setSize_(update[u"size"])
                package.setUrl_(update[u"url"])
                package.setSha1_(update[u"sha1"])
                updates.append(package)
        
        if updates:
            self.cache.downloadUpdates_(updates)
            self.busy = True
            self.waitBusy()
        
        if self.hasFailed:
            return 1    # EXIT_FAILURE
        
        LogNotice(u"All updates for %@ %@ downloaded", args.version, args.build)
        
        return os.EX_OK
    
    def addargsDownload_(self, argparser):
        argparser.add_argument(u"version", help=u"OS X version")
        argparser.add_argument(u"build", help=u"OS X build")
    
    
    
    # Update profiles.
    
    def cmdUpdate_(self, args):
        """Update profiles"""
        
        self.profileController.updateFromURL_(args.url)
        self.busy = True
        self.waitBusy()
        
        if self.hasFailed:
            return 1    # EXIT_FAILURE
        
        return os.EX_OK
    
    def addargsUpdate_(self, argparser):
        defaults = NSUserDefaults.standardUserDefaults()
        url = NSURL.URLWithString_(defaults.stringForKey_(u"UpdateProfilesURL"))
        argparser.add_argument(u"-u", u"--url", default=url, help=u"Profile URL")
    
    
    
    # Workflow delegate methods.
    
    def ejectingSource(self):
        LogInfo("%@", u"Ejecting source…")
    
    def examiningSource_(self, path):
        LogInfo("%@", u"Examining source…")
    
    def foundSourceForIcon_(self, path):
        pass
    
    def sourceSucceeded_(self, info):
        self.installerName = info[u"name"]
        self.installerVersion = info[u"version"]
        self.installerBuild = info[u"build"]
        LogNotice(u"Found installer: %s %s %s" % (info[u"name"], info[u"version"], info[u"build"]))
        self.busy = False
    
    def sourceFailed_text_(self, message, text):
        self.failWithMessage_(u"Source failed: %s" % message)
        self.failWithMessage_(u"    %s" % text)
    
    
    
    def buildStartingWithOutput_(self, outputPath):
        self.busy = True
        self.lastProgressPercent = -100.0
    
    def buildSetTotalWeight_(self, totalWeight):
        self.progressMax = totalWeight
    
    def buildSetPhase_(self, phase):
        LogNotice(u"phase: %@", phase)
    
    def buildSetProgress_(self, progress):
        percent = 100.0 * progress / self.progressMax
        if abs(percent - self.lastProgressPercent) >= 0.1:
            LogInfo(u"progress: %.1f%%", percent)
            self.lastProgressPercent = percent
    
    def buildSetProgressMessage_(self, message):
        if message != self.lastMessage:
            LogInfo(u"message: %@", message)
            self.lastMessage = message
    
    def buildSucceeded(self):
        LogNotice(u"Build successful")
    
    def buildFailed_details_(self, message, details):
        self.failWithMessage_(u"Build failed: %s" % message)
        self.failWithMessage_(u"    %s" % details)
    
    def buildStopped(self):
        self.busy = False
    
    
    
    # UpdateCache delegate methods.
    
    def downloadAllDone(self):
        LogDebug(u"downloadAllDone")
        self.busy = False
    
    def downloadStarting_(self, package):
        LogNotice(u"Downloading %@ (%@)", package.name(), IEDUtil.formatBytes_(package.size()))
        self.lastProgressPercent = -100.0
        self.lastProgressTimestamp = NSDate.alloc().init()
    
    def downloadStarted_(self, package):
        LogDebug(u"downloadStarted:")
    
    def downloadStopped_(self, package):
        LogDebug(u"downloadStopped:")
    
    def downloadGotData_bytesRead_(self, package, bytes):
        percent = 100.0 * float(bytes) / float(package.size())
        # Log progress if we've downloaded more than 10%, more than one second
        # has passed, or if we're at 100%.
        if (abs(percent - self.lastProgressPercent) >= 10.0) or \
           (abs(self.lastProgressTimestamp.timeIntervalSinceNow()) >= 1.0) or \
           (bytes == package.size()):
            LogInfo(u"progress: %.1f%%", percent)
            self.lastProgressPercent = percent
            self.lastProgressTimestamp = NSDate.alloc().init()
    
    def downloadSucceeded_(self, package):
        LogDebug(u"downloadSucceeded:")
    
    def downloadFailed_withError_(self, package, message):
        self.failWithMessage_(u"Download of %s failed: %s" % (package.name(), message))
    
    
    
    # IEDProfileController delegate methods.
    
    def profileUpdateAllDone(self):
        self.busy = False
    
    def profileUpdateFailed_(self, error):
        self.failWithMessage_(u"%@", error.localizedDescription())
    
    def profileUpdateSucceeded_(self, publicationDate):
        LogDebug(u"profileUpdateSucceeded:%@", publicationDate)
        defaults = NSUserDefaults.standardUserDefaults()
        defaults.setObject_forKey_(NSDate.date(), u"LastUpdateProfileCheck")
    
    def profilesUpdated(self):
        LogDebug(u"profilesUpdated")
        self.cache.pruneAndCreateSymlinks(self.profileController.updatePaths)

########NEW FILE########
__FILENAME__ = IEDController
# -*- coding: utf-8 -*-
#
#  IEDController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-09-19.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from AppKit import *
from objc import IBAction, IBOutlet

import os.path
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage, LogException
from IEDUpdateController import *
from IEDWorkflow import *
from IEDTemplate import *


class IEDController(NSObject):
    
    mainWindow = IBOutlet()
    
    sourceBox = IBOutlet()
    sourceImage = IBOutlet()
    sourceLabel = IBOutlet()
    
    updateController = IBOutlet()
    addPkgController = IBOutlet()
    logController = IBOutlet()
    
    buildButton = IBOutlet()
    
    buildProgressWindow = IBOutlet()
    buildProgressPhase = IBOutlet()
    buildProgressBar = IBOutlet()
    buildProgressMessage = IBOutlet()
    
    fileMenu = IBOutlet()
    openMenuItem = IBOutlet()
    saveMenuItem = IBOutlet()
    saveAsMenuItem = IBOutlet()
    
    advancedWindow = IBOutlet()
    volumeName = IBOutlet()
    volumeSize = IBOutlet()
    
    def awakeFromNib(self):
        LogDebug(u"awakeFromNib")
        
        # Initialize UI.
        self.buildProgressBar.setMaxValue_(100.0)
        self.buildProgressMessage.setStringValue_(u"")
        
        # We're a delegate for the drag and drop target, protocol:
        #   (void)acceptInstaller:(NSString *)path
        self.sourceBox.setDelegate_(self)
        self.sourceImage.setDelegate_(self)
        self.sourceLabel.setDelegate_(self)
        
        # We're a delegate for the update controller, protocol:
        #   (void)updateControllerChanged
        self.updateController.setDelegate_(self)
        
        # Main workflow logic.
        self.workflow = IEDWorkflow.alloc().initWithDelegate_(self)
        
        # Enabled state for main window.
        self.enabled = True
        
        # When busy is true quitting gets a confirmation prompt.
        self._busy = False
        
        # Currently loaded template.
        self.templateURL = None
    
    # Methods to communicate with app delegate.
    
    def cleanup(self):
        self.workflow.cleanup()
    
    def busy(self):
        return self._busy
    
    def setBusy_(self, busy):
        self._busy = busy
        if busy:
            self.disableMainWindowControls()
        else:
            self.enableMainWindowControls()
    
    # Helper methods.
    
    def validateMenuItem_(self, menuItem):
        if self.busy():
            if menuItem in (self.openMenuItem,
                            self.saveMenuItem,
                            self.saveAsMenuItem):
                return False
        return True
    
    def displayAlert_text_(self, message, text):
        LogDebug(u"Displaying alert: %@ (%@)", message, text)
        alert = NSAlert.alloc().init()
        alert.setMessageText_(message)
        alert.setInformativeText_(text)
        alert.runModal()
    
    def disableMainWindowControls(self):
        self.enabled = False
        self.sourceBox.stopAcceptingDrag()
        self.sourceImage.stopAcceptingDrag()
        self.sourceLabel.stopAcceptingDrag()
        self.updateController.disableControls()
        self.addPkgController.disableControls()
        self.buildButton.setEnabled_(False)
    
    def enableMainWindowControls(self):
        self.enabled = True
        self.sourceBox.startAcceptingDrag()
        self.sourceImage.startAcceptingDrag()
        self.sourceLabel.startAcceptingDrag()
        self.updateController.enableControls()
        self.addPkgController.enableControls()
        self.updateBuildButton()
    
    def updateBuildButton(self):
        buildEnabled = self.enabled and \
                       self.workflow.hasSource() and \
                       self.updateController.allUpdatesDownloaded()
        self.buildButton.setEnabled_(buildEnabled)
    
    
    
    # Common workflow delegate methods.
    
    def detachFailed_details_(self, dmgPath, details):
        self.displayAlert_text_(u"Failed to detach %s" % dmgPath, details)
    
    
    
    # Act on user dropping an installer.
    
    def acceptSource_(self, path):
        self.setBusy_(True)
        self.workflow.setSource_(path)
    
    # Workflow delegate methods.
    
    def ejectingSource(self):
        self.sourceImage.animator().setAlphaValue_(0.5)
        self.sourceLabel.setStringValue_(u"Ejecting")
        self.sourceLabel.setTextColor_(NSColor.disabledControlTextColor())
    
    def examiningSource_(self, path):
        self.foundSourceForIcon_(path)
        self.sourceLabel.setStringValue_(u"Examining")
        self.sourceLabel.setTextColor_(NSColor.disabledControlTextColor())
    
    def foundSourceForIcon_(self, path):
        icon = NSWorkspace.sharedWorkspace().iconForFile_(path)
        icon.setSize_(NSMakeSize(256.0, 256.0))
        tiff = icon.TIFFRepresentation()
        image = NSImage.alloc().initWithData_(tiff)
        self.sourceImage.animator().setAlphaValue_(1.0)
        self.sourceImage.animator().setImage_(image)
    
    def sourceSucceeded_(self, info):
        self.installerName = info[u"name"]
        self.installerVersion = info[u"version"]
        self.installerBuild = info[u"build"]
        self.sourceLabel.setStringValue_(u"%s %s %s" % (info[u"name"], info[u"version"], info[u"build"]))
        self.sourceLabel.setTextColor_(NSColor.controlTextColor())
        self.updateController.loadProfileForVersion_build_(info[u"version"], info[u"build"])
        template = info[u"template"]
        if template:
            LogInfo(u"Template found in image: %@", repr(template))
            # Don't default to applying updates to an image that was built
            # with updates applied, and vice versa.
            if template.applyUpdates:
                self.updateController.applyUpdatesCheckbox.setState_(NSOffState)
            else:
                self.updateController.applyUpdatesCheckbox.setState_(NSOnState)
        else:
            if info[u"sourceType"] == IEDWorkflow.SYSTEM_IMAGE:
                LogInfo(u"No template found in image")
                # If the image doesn't have a template inside, assume that updates
                # were applied.
                self.updateController.applyUpdatesCheckbox.setState_(NSOffState)
        self.setBusy_(False)
    
    def sourceFailed_text_(self, message, text):
        self.displayAlert_text_(message, text)
        self.sourceImage.animator().setImage_(NSImage.imageNamed_(u"Installer Placeholder"))
        self.sourceImage.animator().setAlphaValue_(1.0)
        self.sourceLabel.setStringValue_(u"Drop OS X Installer Here")
        self.sourceLabel.setTextColor_(NSColor.disabledControlTextColor())
        self.setBusy_(False)
    
    
    
    # Act on update controller changing.
    
    def updateControllerChanged(self):
        if self.enabled:
            self.updateBuildButton()
    
    
    
    # Act on user showing log window.
    
    @LogException
    @IBAction
    def displayAdvancedWindow_(self, sender):
        self.advancedWindow.makeKeyAndOrderFront_(self)
    
    
    
    # Act on build button.
    
    @LogException
    @IBAction
    def buildButtonClicked_(self, sender):
        panel = NSSavePanel.savePanel()
        panel.setExtensionHidden_(False)
        panel.setAllowedFileTypes_([u"dmg"])
        imageName = u"osx"
        formatter = NSDateFormatter.alloc().init()
        formatter.setDateFormat_(u"yyMMdd")
        if self.updateController.packagesToInstall():
            dateStr = formatter.stringFromDate_(self.updateController.profileController.publicationDate)
            imageName = u"osx_updated_%s" % dateStr
        if self.addPkgController.packagesToInstall():
            dateStr = formatter.stringFromDate_(NSDate.date())
            imageName = u"osx_custom_%s" % dateStr
        panel.setNameFieldStringValue_(u"%s-%s-%s.hfs" % (imageName, self.installerVersion, self.installerBuild))
        result = panel.runModal()
        if result != NSFileHandlingPanelOKButton:
            return
        
        exists, error = panel.URL().checkResourceIsReachableAndReturnError_(None)
        if exists:
            success, error = NSFileManager.defaultManager().removeItemAtURL_error_(panel.URL(), None)
            if not success:
                NSApp.presentError_(error)
                return
        
        # Create a template to save inside the image.
        template = IEDTemplate.alloc().init()
        template.setSourcePath_(self.workflow.source())
        if self.updateController.packagesToInstall():
            template.setApplyUpdates_(True)
        else:
            template.setApplyUpdates_(False)
        template.setAdditionalPackages_([x.path() for x in self.addPkgController.packagesToInstall()])
        template.setOutputPath_(panel.URL().path())
        if self.volumeName.stringValue():
            template.setVolumeName_(self.volumeName.stringValue())
            self.workflow.setVolumeName_(self.volumeName.stringValue().strip())
        if self.volumeSize.stringValue():
            template.setVolumeSize_(self.volumeSize.intValue())
            self.workflow.setVolumeSize_(self.volumeSize.intValue())
        self.workflow.setTemplate_(template)
        
        self.workflow.setPackagesToInstall_(self.updateController.packagesToInstall() +
                                            self.addPkgController.packagesToInstall())
        self.workflow.setOutputPath_(panel.URL().path())
        self.workflow.start()
    
    # Workflow delegate methods.
    
    def buildStartingWithOutput_(self, outputPath):
        self.buildProgressWindow.setTitle_(os.path.basename(outputPath))
        self.buildProgressPhase.setStringValue_(u"Starting")
        self.buildProgressBar.setIndeterminate_(True)
        self.buildProgressBar.startAnimation_(self)
        self.buildProgressBar.setDoubleValue_(0.0)
        self.buildProgressMessage.setStringValue_(u"")
        self.buildProgressWindow.makeKeyAndOrderFront_(self)
        self.setBusy_(True)
    
    def buildSetTotalWeight_(self, totalWeight):
        self.buildProgressBar.setMaxValue_(totalWeight)
    
    def buildSetPhase_(self, phase):
        self.buildProgressPhase.setStringValue_(phase)
    
    def buildSetProgress_(self, progress):
        self.buildProgressBar.setDoubleValue_(progress)
        self.buildProgressBar.setIndeterminate_(False)
    
    def buildSetProgressMessage_(self, message):
        self.buildProgressMessage.setStringValue_(message)
    
    def buildSucceeded(self):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(u"Build successful")
        alert.setInformativeText_(u"Built %s" % os.path.basename(self.workflow.outputPath()))
        alert.addButtonWithTitle_(u"OK")
        alert.addButtonWithTitle_(u"Reveal")
        button = alert.runModal()
        if button == NSAlertSecondButtonReturn:
            fileURL = NSURL.fileURLWithPath_(self.workflow.outputPath())
            NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_([fileURL])
    
    def buildFailed_details_(self, message, details):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(message)
        alert.setInformativeText_(details)
        alert.addButtonWithTitle_(u"OK")
        alert.addButtonWithTitle_(u"View Log")
        button = alert.runModal()
        if button == NSAlertSecondButtonReturn:
            self.logController.displayLogWindow_(self)
    
    def buildStopped(self):
        self.buildProgressWindow.orderOut_(self)
        self.setBusy_(False)
    
    
    
    # Load and save templates.
    
    def saveTemplate(self):
        if self.templateURL:
            self.saveTemplateToURL_(self.templateURL)
        else:
            self.saveTemplateAs()
    
    def saveTemplateAs(self):
        panel = NSSavePanel.savePanel()
        panel.setExtensionHidden_(False)
        panel.setAllowedFileTypes_([u"adtmpl"])
        formatter = NSDateFormatter.alloc().init()
        formatter.setDateFormat_(u"yyMMdd")
        dateStr = formatter.stringFromDate_(NSDate.date())
        panel.setNameFieldStringValue_(u"AutoDMG-%s.adtmpl" % (dateStr))
        result = panel.runModal()
        if result != NSFileHandlingPanelOKButton:
            return
        
        exists, error = panel.URL().checkResourceIsReachableAndReturnError_(None)
        if exists:
            success, error = NSFileManager.defaultManager().removeItemAtURL_error_(panel.URL(), None)
            if not success:
                NSApp.presentError_(error)
                return
        
        self.saveTemplateToURL_(panel.URL())
    
    def saveTemplateToURL_(self, url):
        LogDebug(u"saveTemplateToURL:%@", url)
        self.templateURL = url
        NSDocumentController.sharedDocumentController().noteNewRecentDocumentURL_(url)
        
        # Create a template from the current state.
        template = IEDTemplate.alloc().init()
        if self.workflow.source():
            template.setSourcePath_(self.workflow.source())
        if self.updateController.packagesToInstall():
            template.setApplyUpdates_(True)
        else:
            template.setApplyUpdates_(False)
        template.setAdditionalPackages_([x.path() for x in self.addPkgController.packagesToInstall()])
        
        error = template.saveTemplateAndReturnError_(url.path())
        if error:
            self.displayAlert_text_(u"Couldn't save template", error)
    
    def openTemplate(self):
        panel = NSOpenPanel.openPanel()
        panel.setExtensionHidden_(False)
        panel.setAllowedFileTypes_([u"adtmpl"])
        
        result = panel.runModal()
        if result != NSFileHandlingPanelOKButton:
            return
        
        return self.openTemplateAtURL_(panel.URL())
    
    def openTemplateAtURL_(self, url):
        LogDebug(u"openTemplateAtURL:%@", url)
        self.templateURL = None
        template = IEDTemplate.alloc().init()
        error = template.loadTemplateAndReturnError_(url.path())
        if error:
            self.displayAlert_text_(u"Couldn't open template", error)
            return False
        self.templateURL = url
        NSDocumentController.sharedDocumentController().noteNewRecentDocumentURL_(url)
        # AdditionalPackages.
        LogDebug(u"Setting additional packages to %@", template.additionalPackages)
        self.addPkgController.replacePackagesWithPaths_(template.additionalPackages)
        # ApplyUpdates.
        if template.applyUpdates:
            LogDebug(u"Enable updates")
            self.updateController.applyUpdatesCheckbox.setState_(NSOnState)
        else:
            LogDebug(u"Disable updates")
            self.updateController.applyUpdatesCheckbox.setState_(NSOffState)
        # VolumeName.
        self.volumeName.setStringValue_(u"")
        if template.volumeName:
            LogDebug(u"Setting volume name to %@", template.volumeName)
            self.volumeName.setStringValue_(template.volumeName)
        # VolumeSize.
        self.volumeSize.setStringValue_(u"")
        if template.volumeSize:
            LogDebug(u"Setting volume size to %@", template.volumeSize)
            self.volumeSize.setIntValue_(template.volumeSize)
        # SourcePath.
        if template.sourcePath:
            LogDebug(u"Setting source to %@", template.sourcePath)
            self.setBusy_(True)
            self.workflow.setSource_(template.sourcePath)
        return True

########NEW FILE########
__FILENAME__ = IEDDMGHelper
# -*- coding: utf-8 -*-
#
#  IEDDMGHelper.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-19.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
import subprocess
import plistlib
import time
import traceback

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage


class IEDDMGHelper(NSObject):
    
    def init(self):
        self = super(IEDDMGHelper, self).init()
        if self is None:
            return None
        
        # A dictionary of dmg paths and their respective mount points.
        # NB: we only handle a single mount point per dmg.
        self.dmgs = dict()
        
        return self
    
    def initWithDelegate_(self, delegate):
        self = self.init()
        if self is None:
            return None
        
        self.delegate = delegate
        
        return self
    
    # Send a message to delegate in the main thread.
    def tellDelegate_message_(self, selector, message):
        if self.delegate.respondsToSelector_(selector):
            self.delegate.performSelectorOnMainThread_withObject_waitUntilDone_(selector, message, False)
    
    def hdiutilAttach_(self, args):
        try:
            dmgPath, selector = args
            LogDebug(u"Attaching %@", dmgPath)
            p = subprocess.Popen([u"/usr/bin/hdiutil",
                                  u"attach",
                                  dmgPath,
                                  u"-mountRandom", u"/tmp",
                                  u"-nobrowse",
                                  u"-noverify",
                                  u"-plist"],
                                 bufsize=1,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out, err = p.communicate(u"Y\n")
            LogDebug(u"Checking result of attaching %@", dmgPath)
            if p.returncode != 0:
                errstr = u"hdiutil attach failed with return code %d" % p.returncode
                if err:
                    errstr += u": %s" % err.decode(u"utf-8")
                self.tellDelegate_message_(selector, {u"success": False,
                                                      u"dmg-path": dmgPath,
                                                      u"error-message": errstr})
                return
            # Strip EULA text.
            xmlStartIndex = out.find("<?xml")
            plist = plistlib.readPlistFromString(out[xmlStartIndex:])
            for partition in plist[u"system-entities"]:
                if partition.get(u"potentially-mountable") == 1:
                    if u"mount-point" in partition:
                        self.dmgs[dmgPath] = partition[u"mount-point"]
                        break
            else:
                self.tellDelegate_message_(selector, {u"success": False,
                                                      u"dmg-path": dmgPath,
                                                      u"error-message": u"No mounted filesystem in %s" % dmgPath})
                return
            self.tellDelegate_message_(selector, {u"success": True,
                                                  u"dmg-path": dmgPath,
                                                  u"mount-point": self.dmgs[dmgPath]})
        except Exception:
            exceptionInfo = traceback.format_exc()
            msg = u"Attach of %s crashed with exception:\n%s" % (dmgPath, exceptionInfo)
            self.tellDelegate_message_(selector, {u"success": False,
                                                  u"dmg-path": dmgPath,
                                                  u"error-message": msg})
    
    # Attach a dmg and send a success dictionary.
    def attach_selector_(self, dmgPath, selector):
        if dmgPath in self.dmgs:
            self.tellDelegate_message_(selector, {u"success": True,
                                                  u"dmg-path": dmgPath,
                                                  u"mount-point": self.dmgs[dmgPath]})
        else:
            self.performSelectorInBackground_withObject_(self.hdiutilAttach_, [dmgPath, selector])
    
    def hdiutilDetach_(self, args):
        try:
            dmgPath, target, selector = args
            LogDebug(u"Detaching %@", dmgPath)
            try:
                cmd = [u"/usr/bin/hdiutil",
                       u"detach",
                       self.dmgs[dmgPath]]
            except KeyError:
                target.performSelectorOnMainThread_withObject_waitUntilDone_(selector,
                                                                             {u"success": False,
                                                                              u"dmg-path": dmgPath,
                                                                              u"error-message": u"%s not mounted" % dmgPath},
                                                                             False)
                return
            del self.dmgs[dmgPath]
            maxtries = 5
            for tries in range(maxtries):
                if tries == maxtries >> 1:
                    cmd.append(u"-force")
                p = subprocess.Popen(cmd,
                                     bufsize=1,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                out, err = p.communicate()
                if p.returncode == 0:
                    target.performSelectorOnMainThread_withObject_waitUntilDone_(selector,
                                                                                 {u"success": True, u"dmg-path": dmgPath},
                                                                                 False)
                    return
                elif tries == maxtries - 1:
                    errstr = u"hdiutil detach failed with return code %d" % p.returncode
                    if err:
                        errstr += u": %s" % err.decode(u"utf-8")
                    target.performSelectorOnMainThread_withObject_waitUntilDone_(selector,
                                                                                 {u"success": False,
                                                                                  u"dmg-path": dmgPath,
                                                                                  u"error-message": errstr},
                                                                                 False)
                else:
                    time.sleep(1)
        except Exception:
            exceptionInfo = traceback.format_exc()
            msg = u"Detach of %s crashed with exception:\n%s" % (dmgPath, exceptionInfo)
            target.performSelectorOnMainThread_withObject_waitUntilDone_(selector,
                                                                         {u"success": False,
                                                                          u"dmg-path": dmgPath,
                                                                          u"error-message": msg},
                                                                         False)
    
    # Detach a dmg and send a success dictionary.
    def detach_selector_(self, dmgPath, selector):
        if dmgPath in self.dmgs:
            self.performSelectorInBackground_withObject_(self.hdiutilDetach_, [dmgPath, self.delegate, selector])
        else:
            self.tellDelegate_message_(selector, {u"success": False,
                                                  u"dmg-path": dmgPath,
                                                  u"error-message": u"%s isn't mounted" % dmgPath})
    
    # Detach all mounted dmgs and send a message with a dictionary of detach
    # failures.
    def detachAll_(self, selector):
        LogDebug(u"detachAll:%@", selector)
        self.detachAllFailed = dict()
        self.detachAllRemaining = len(self.dmgs)
        self.detachAllSelector = selector
        if self.dmgs:
            for dmgPath in self.dmgs.keys():
                self.performSelectorInBackground_withObject_(self.hdiutilDetach_, [dmgPath, self, self.handleDetachAllResult_])
        else:
            if self.delegate.respondsToSelector_(selector):
                self.delegate.performSelector_withObject_(selector, {})
    
    def handleDetachAllResult_(self, result):
        LogDebug(u"handleDetachAllResult:%@", result)
        if not result[u"success"]:
            self.detachAllFailed[result[u"dmg-path"]] = result[u"error-message"]
        self.detachAllRemaining -= 1
        if self.detachAllRemaining == 0:
            self.tellDelegate_message_(self.detachAllSelector, self.detachAllFailed)

########NEW FILE########
__FILENAME__ = IEDLog
# -*- coding: utf-8 -*-
#
#  IEDLog.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-25.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#


from Foundation import *
from AppKit import *
from objc import IBAction, IBOutlet

from IEDLogLine import *
import inspect
import syslog
import sys
import traceback


IEDLogLevelEmergency = 0
IEDLogLevelAlert     = 1
IEDLogLevelCritical  = 2
IEDLogLevelError     = 3
IEDLogLevelWarning   = 4
IEDLogLevelNotice    = 5
IEDLogLevelInfo      = 6
IEDLogLevelDebug     = 7

# Control which output channels are active.
IEDLogToController  = True
IEDLogToSyslog      = True
IEDLogToStdOut      = False
IEDLogToFile        = False

# Default log levels.
IEDLogStdOutLogLevel    = IEDLogLevelNotice
IEDLogFileLogLevel      = IEDLogLevelDebug

# File handle for log file.
IEDLogFileHandle = None


defaults = NSUserDefaults.standardUserDefaults()


def IEDLogLevelName(level):
    return (
        u"Emergency",
        u"Alert",
        u"Critical",
        u"Error",
        u"Warning",
        u"Notice",
        u"Info",
        u"Debug",
    )[level]


def LogException(func):
    """Wrap IBActions to catch exceptions."""
    def wrapper(c, s):
        global _log
        try:
            func(c, s)
        except Exception as e:
            exceptionInfo = traceback.format_exc()
            LogDebug(u"Uncaught exception in %@, %@", func.__name__, exceptionInfo.rstrip())
            alert = NSAlert.alloc().init()
            alert.setMessageText_(u"Uncaught exception")
            alert.setInformativeText_(exceptionInfo)
            alert.addButtonWithTitle_(u"Dismiss")
            alert.addButtonWithTitle_(u"Save Log…")
            while alert.runModal() == NSAlertSecondButtonReturn:
                _log.saveLog_(IEDLog.IEDLog, None)
    return wrapper


class IEDLog(NSObject):
    
    # Singleton instance.
    _instance = None
    
    logWindow = IBOutlet()
    logTableView = IBOutlet()
    levelSelector = IBOutlet()
    
    logLines = list()
    visibleLogLines = list()
    
    def init(self):
        # Initialize singleton.
        if IEDLog._instance is not None:
            return IEDLog._instance
        self = super(IEDLog, self).init()
        if self is None:
            return None
        IEDLog._instance = self
        self.logAtBottom = True
        return self
    
    def awakeFromNib(self):
        global defaults
        self.levelSelector.selectItemAtIndex_(defaults.integerForKey_(u"LogLevel"))
        self.logTableView.setDataSource_(self)
        nc = NSNotificationCenter.defaultCenter()
        nc.addObserver_selector_name_object_(self,
                                             self.logViewScrolled_,
                                             NSViewBoundsDidChangeNotification,
                                             self.logTableView.enclosingScrollView().contentView())
    
    # Helper methods.
    
    
    def addMessage_level_(self, message, level):
        logLine = IEDLogLine.alloc().initWithMessage_level_(message, level)
        self.logLines.append(logLine)
        if defaults.integerForKey_(u"LogLevel") >= level:
            self.visibleLogLines.append(logLine)
            if self.logTableView:
                self.logTableView.reloadData()
                if self.logAtBottom:
                    self.logTableView.scrollRowToVisible_(len(self.visibleLogLines) - 1)
    
    
    
    # Act on user showing log window.
    
    @LogException
    @IBAction
    def displayLogWindow_(self, sender):
        self.logAtBottom = True
        self.logTableView.scrollRowToVisible_(len(self.visibleLogLines) - 1)
        self.logWindow.makeKeyAndOrderFront_(self)
    
    
    
    # Act on notification for log being scrolled by user.
    
    def logViewScrolled_(self, notification):
        tableViewHeight = self.logTableView.bounds().size.height
        scrollView = self.logTableView.enclosingScrollView()
        scrollRect = scrollView.documentVisibleRect()
        scrollPos = scrollRect.origin.y + scrollRect.size.height
        
        if scrollPos >= tableViewHeight:
            self.logAtBottom = True
        else:
            self.logAtBottom = False
    
    # Act on user filtering log.
    
    @LogException
    @IBAction
    def setLevel_(self, sender):
        self.visibleLogLines = [x for x in self.logLines if x.level() <= self.levelSelector.indexOfSelectedItem()]
        self.logAtBottom = True
        self.logTableView.reloadData()
        self.logTableView.scrollRowToVisible_(len(self.visibleLogLines) - 1)
    
    
    
    # Act on user clicking save button.
    
    @LogException
    @IBAction
    def saveLog_(self, sender):
        panel = NSSavePanel.savePanel()
        panel.setExtensionHidden_(False)
        panel.setAllowedFileTypes_([u"log", u"txt"])
        formatter = NSDateFormatter.alloc().init()
        formatter.setDateFormat_(u"yyyy-MM-dd HH.mm")
        dateStr = formatter.stringFromDate_(NSDate.date())
        panel.setNameFieldStringValue_(u"AutoDMG %s" % dateStr)
        result = panel.runModal()
        if result != NSFileHandlingPanelOKButton:
            return
        
        exists, error = panel.URL().checkResourceIsReachableAndReturnError_(None)
        if exists:
            success, error = NSFileManager.defaultManager().removeItemAtURL_error_(panel.URL(), None)
            if not success:
                NSApp.presentError_(error)
                return
        
        success, error = NSData.data().writeToURL_options_error_(panel.URL(), 0, None)
        if not success:
            NSApp.presentError_(error)
            return
        
        fh, error = NSFileHandle.fileHandleForWritingToURL_error_(panel.URL(), None)
        if fh is None:
            NSAlert.alertWithError_(error).runModal()
            return
        formatter = NSDateFormatter.alloc().init()
        formatter.setDateFormat_(u"yyyy-MM-dd HH:mm:ss")
        for logLine in self.logLines:
            textLine = NSString.stringWithFormat_(u"%@ %@: %@\n",
                                                  formatter.stringFromDate_(logLine.date()),
                                                  IEDLogLevelName(logLine.level()),
                                                  logLine.message())
            fh.writeData_(textLine.dataUsingEncoding_(NSUTF8StringEncoding))
        fh.closeFile()
    
    
    
    # We're an NSTableViewDataSource.
    
    def numberOfRowsInTableView_(self, tableView):
        return len(self.visibleLogLines)
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        if column.identifier() == u"date":
            return self.visibleLogLines[row].date()
        elif column.identifier() == u"level":
            return IEDLogLevelName(self.visibleLogLines[row].level())
        elif column.identifier() == u"message":
            return self.visibleLogLines[row].message()


timestampFormatter = NSDateFormatter.alloc().init()
timestampFormatter.setDateStyle_(NSDateFormatterLongStyle)
timestampFormatter.setTimeStyle_(NSDateFormatterLongStyle)

def timestamp(dt=None):
    global timestampFormatter
    if dt is None:
        dt = NSDate.date()
    return timestampFormatter.stringFromDate_(dt)


def LogToSyslog(level, message):
    syslog.syslog(level, message.encode("utf-8"))


def LogToStdOut(level, message):
    print >>sys.stdout, message.encode(u"utf-8")


def LogToFile(level, message):
    global IEDLogFileHandle
    if IEDLogFileHandle is not None:
        print >>IEDLogFileHandle, \
            NSString.stringWithFormat_(u"%@  %@",
                                       timestamp(),
                                       message).encode(u"utf-8")
    else:
        NSLog(u"IEDLogFileHandle not open")


# Keep (singleton) instance of IEDLog.
_log = IEDLog.alloc().init()

def LogMessage(level, message):
    global _log
    
    # Prefix debug messages with the module name and line number.
    prefix = u""
    if level == IEDLogLevelDebug:
        for caller in inspect.stack()[1:]:
            modname = inspect.getmodule(caller[0]).__name__
            if modname == u"IEDLog":
                continue
            lineno = caller[2]
            prefix = u"(%s:%d) " % (modname, lineno)
            break
    
    # Control syslog verbosity with DebugToSyslog bool.
    if defaults.boolForKey_(u"DebugToSyslog"):
        syslogLevel = IEDLogLevelDebug
    else:
        syslogLevel = IEDLogLevelInfo
    
    # Log each line as a separate message.
    for line in message.split(u"\n"):
        
        # Prepend prefix.
        prefixedLine = prefix + line
        
        # Dispatch line to each active channel.
        
        if IEDLogToController:
            _log.addMessage_level_(prefixedLine, level)
        
        if IEDLogToSyslog and (level <= syslogLevel):
            LogToSyslog(level, prefixedLine)
        
        if IEDLogToStdOut and (level <= IEDLogStdOutLogLevel):
            LogToStdOut(level, prefixedLine)
        
        if IEDLogToFile and (level <= IEDLogFileLogLevel):
            LogToFile(level, prefixedLine)

def LogDebug(*args):
    LogMessage(IEDLogLevelDebug, NSString.stringWithFormat_(*args))

def LogInfo(*args):
    LogMessage(IEDLogLevelInfo, NSString.stringWithFormat_(*args))

def LogNotice(*args):
    LogMessage(IEDLogLevelNotice, NSString.stringWithFormat_(*args))

def LogWarning(*args):
    LogMessage(IEDLogLevelWarning, NSString.stringWithFormat_(*args))

def LogError(*args):
    LogMessage(IEDLogLevelError, NSString.stringWithFormat_(*args))

########NEW FILE########
__FILENAME__ = IEDLogLine
# -*- coding: utf-8 -*-
#
#  IEDLogLine.py
#  AutoDMG
#
#  Created by Pelle on 2013-10-28.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *


class IEDLogLine(NSObject):
    
    def init(self):
        self = super(IEDLogLine, self).init()
        if self is None:
            return None
        
        self._date = NSDate.date()
        self._message = u""
        self._level = 0
        
        return self
    
    def initWithMessage_level_(self, message, level):
        self = self.init()
        if self is None:
            return None
        
        self._message = message
        self._level = level
        
        return self
    
    def date(self):
        return self._date
    
    def setDate(self, date):
        self._date = date
    
    def message(self):
        return self._message
    
    def setMessage(self, message):
        self._message = message
    
    def level(self):
        return self._level
    
    def setLevel(self, level):
        self._level = level

########NEW FILE########
__FILENAME__ = IEDPackage
# -*- coding: utf-8 -*-
#
#  IEDPackage.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-26.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *


class IEDPackage(NSObject):

    def init(self):
        self = super(IEDPackage, self).init()
        if self is None:
            return None
        
        self._name = None
        self._path = None
        self._size = None
        self._url = None
        self._image = None
        self._sha1 = None
        
        return self
    
    def name(self):
        return self._name
    
    def setName_(self, name):
        self._name = name
    
    def path(self):
        return self._path
    
    def setPath_(self, path):
        self._path = path
    
    def size(self):
        return self._size
    
    def setSize_(self, size):
        self._size = size
    
    def url(self):
        return self._url
    
    def setUrl_(self, url):
        self._url = url
    
    def image(self):
        return self._image
    
    def setImage_(self, image):
        self._image = image
    
    def sha1(self):
        return self._sha1
    
    def setSha1_(self, sha1):
        self._sha1 = sha1

########NEW FILE########
__FILENAME__ = IEDProfileController
# -*- coding: utf-8 -*-
#
#  IEDProfileController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-21.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from AppKit import *
from Foundation import *
from objc import IBOutlet

import os.path
from collections import defaultdict
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage


class IEDProfileController(NSObject):
    """Keep track of update profiles, containing lists of the latest updates
    needed to build a fully updated OS X image."""
    
    profileUpdateWindow = IBOutlet()
    progressBar = IBOutlet()
    delegate = IBOutlet()
    
    def awakeFromNib(self):
        # Save the path to UpdateProfiles.plist in the user's application
        # support directory.
        fm = NSFileManager.defaultManager()
        url, error = fm.URLForDirectory_inDomain_appropriateForURL_create_error_(NSApplicationSupportDirectory,
                                                                                 NSUserDomainMask,
                                                                                 None,
                                                                                 True,
                                                                                 None)
        self.userUpdateProfilesPath = os.path.join(url.path(), u"AutoDMG", u"UpdateProfiles.plist")
        
        # Load UpdateProfiles from the application bundle.
        bundleUpdateProfilesPath = NSBundle.mainBundle().pathForResource_ofType_(u"UpdateProfiles", u"plist")
        bundleUpdateProfiles = NSDictionary.dictionaryWithContentsOfFile_(bundleUpdateProfilesPath)
        
        latestProfiles = self.updateUsersProfilesIfNewer_(bundleUpdateProfiles)
        # Load the profiles.
        self.loadProfilesFromPlist_(latestProfiles)
    
    def setDelegate_(self, delegate):
        self.delegate = delegate
    
    def profileForVersion_Build_(self, version, build):
        """Return the update profile for a certain OS X version and build."""
        
        try:
            profile = self.profiles[u"%s-%s" % (version, build)]
            LogInfo(u"Update profile for %@ %@: %@", version, build, u", ".join(u[u"name"] for u in profile))
        except KeyError:
            profile = None
            LogNotice(u"No update profile for %@ %@", version, build)
        return profile
    
    def whyNoProfileForVersion_build_(self, whyVersion, whyBuild):
        """Given a version and build that doesn't have a profile, try to
        provide a helpful explanation as to why that might be."""
        
        # Check if it has been deprecated.
        try:
            replacement = self.deprecatedInstallerBuilds[whyBuild]
            version, _, build = replacement.partition(u"-")
            return u"Installer deprecated by %s %s" % (version, build)
        except KeyError:
            pass
        
        whyVersionTuple = tuple(int(x) for x in whyVersion.split(u"."))
        whyMajor = whyVersionTuple[1]
        whyPoint = whyVersionTuple[2] if len(whyVersionTuple) > 2 else None
        
        buildsForVersion = defaultdict(set)
        supportedMajorVersions = set()
        supportedPointReleases = defaultdict(set)
        for versionBuild in self.profiles.keys():
            version, _, build = versionBuild.partition(u"-")
            buildsForVersion[version].add(build)
            versionTuple = tuple(int(x) for x in version.split(u"."))
            major = versionTuple[1]
            supportedMajorVersions.add(major)
            point = versionTuple[2] if len(versionTuple) > 2 else None
            supportedPointReleases[major].add(point)
        
        if whyMajor not in supportedMajorVersions:
            return "10.%d is not supported" % whyMajor
        elif whyVersion in buildsForVersion:
            return u"Unknown build %s" % whyBuild
        else:
            # It's a supported OS X version, but we don't have a profile for
            # this point release. Try to figure out if that's because it's too
            # old or too new.
            pointReleases = supportedPointReleases[whyMajor]
            oldestSupportedPointRelease = sorted(pointReleases)[0]
            newestSupportedPointRelease = sorted(pointReleases)[-1]
            if whyPoint < oldestSupportedPointRelease:
                return u"Deprecated installer"
            elif whyPoint > newestSupportedPointRelease:
                # If it's newer than any known release, just assume that we're
                # behind on updates and that all is well.
                return None
            else:
                # Well this is awkward.
                return u"Deprecated installer"
    
    def updateUsersProfilesIfNewer_(self, plist):
        """Update the user's update profiles if plist is newer. Returns
           whichever was the newest."""
        
        # Load UpdateProfiles from the user's application support directory.
        userUpdateProfiles = NSDictionary.dictionaryWithContentsOfFile_(self.userUpdateProfilesPath)
        
        # If the bundle's plist is newer, update the user's.
        if (not userUpdateProfiles) or (userUpdateProfiles[u"PublicationDate"].timeIntervalSinceDate_(plist[u"PublicationDate"]) < 0):
            LogDebug(u"Saving updated UpdateProfiles.plist")
            self.saveUsersProfiles_(plist)
            return plist
        else:
            return userUpdateProfiles
    
    def saveUsersProfiles_(self, plist):
        """Save UpdateProfiles.plist to application support."""
        
        LogInfo(u"Saving update profiles with PublicationDate %@", plist[u"PublicationDate"])
        if not plist.writeToFile_atomically_(self.userUpdateProfilesPath, False):
            LogError(u"Failed to write %@", self.userUpdateProfilesPath)
    
    def loadProfilesFromPlist_(self, plist):
        """Load UpdateProfiles from a plist dictionary."""
        
        LogInfo(u"Loading update profiles with PublicationDate %@", plist[u"PublicationDate"])
        self.profiles = dict()
        for name, updates in plist[u"Profiles"].iteritems():
            profile = list()
            for update in updates:
                profile.append(plist[u"Updates"][update])
            self.profiles[name] = profile
        self.publicationDate = plist[u"PublicationDate"]
        self.updatePaths = dict()
        for name, update in plist[u"Updates"].iteritems():
            filename, ext = os.path.splitext(os.path.basename(update[u"url"]))
            self.updatePaths[update[u"sha1"]] = u"%s(%s)%s" % (filename, update[u"sha1"][:7], ext)
        self.deprecatedInstallerBuilds = dict()
        try:
            for replacement, builds in plist[u"DeprecatedInstallers"].iteritems():
                for build in builds:
                    self.deprecatedInstallerBuilds[build] = replacement
        except KeyError:
            LogWarning(u"No deprecated installers")
        if self.delegate:
            self.delegate.profilesUpdated()
    
    
    
    # Update profiles.
    
    def updateFromURL_(self, url):
        """Download the latest UpdateProfiles.plist."""
        
        LogDebug(u"updateFromURL:%@", url)
        
        if self.profileUpdateWindow:
            # Show the progress window.
            self.progressBar.setIndeterminate_(True)
            self.progressBar.startAnimation_(self)
            self.profileUpdateWindow.makeKeyAndOrderFront_(self)
        
        # Create a buffer for data.
        self.profileUpdateData = NSMutableData.alloc().init()
        # Start download.
        request = NSURLRequest.requestWithURL_(url)
        self.connection = NSURLConnection.connectionWithRequest_delegate_(request, self)
        LogDebug(u"connection = %@", self.connection)
        if not self.connection:
            LogWarning(u"Connection to %@ failed", url)
            if self.profileUpdateWindow:
                self.profileUpdateWindow.orderOut_(self)
            self.delegate.profileUpdateFailed_(error)
    
    def connection_didFailWithError_(self, connection, error):
        LogError(u"Profile update failed: %@", error)
        if self.profileUpdateWindow:
            self.profileUpdateWindow.orderOut_(self)
        self.delegate.profileUpdateFailed_(error)
        self.delegate.profileUpdateAllDone()
    
    def connection_didReceiveResponse_(self, connection, response):
        LogDebug(u"%@ status code %d", connection, response.statusCode())
        if response.expectedContentLength() == NSURLResponseUnknownLength:
            LogDebug(u"unknown response length")
        else:
            LogDebug(u"Downloading profile with %d bytes", response.expectedContentLength())
            if self.profileUpdateWindow:
                self.progressBar.setMaxValue_(float(response.expectedContentLength()))
                self.progressBar.setDoubleValue_(float(response.expectedContentLength()))
                self.progressBar.setIndeterminate_(False)
    
    def connection_didReceiveData_(self, connection, data):
        self.profileUpdateData.appendData_(data)
        if self.profileUpdateWindow:
            self.progressBar.setDoubleValue_(float(self.profileUpdateData.length()))
    
    def connectionDidFinishLoading_(self, connection):
        LogDebug(u"Downloaded profile with %d bytes", self.profileUpdateData.length())
        if self.profileUpdateWindow:
            # Hide the progress window.
            self.profileUpdateWindow.orderOut_(self)
        # Decode the plist.
        plist, format, error = NSPropertyListSerialization.propertyListWithData_options_format_error_(self.profileUpdateData,
                                                                                                      NSPropertyListImmutable,
                                                                                                      None,
                                                                                                      None)
        if not plist:
            self.delegate.profileUpdateFailed_(error)
            return
        LogNotice(u"Downloaded update profiles with PublicationDate %@", plist[u"PublicationDate"])
        # Update the user's profiles if it's newer.
        latestProfiles = self.updateUsersProfilesIfNewer_(plist)
        # Load the latest profiles.
        self.loadProfilesFromPlist_(latestProfiles)
        # Notify delegate.
        self.delegate.profileUpdateSucceeded_(latestProfiles[u"PublicationDate"])
        self.delegate.profileUpdateAllDone()
    
    def cancelUpdateDownload(self):
        LogInfo(u"User canceled profile update")
        self.connection.cancel()
        self.profileUpdateWindow.orderOut_(self)

########NEW FILE########
__FILENAME__ = IEDSocketListener
# -*- coding: utf-8 -*-
#
#  IEDSocketListener.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-10.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
import os
import socket
import glob

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage


IEDSL_MAX_MSG_SIZE = 4096


class IEDSocketListener(NSObject):
    """Open a unix domain datagram socket and wait for messages encoded as
    plists, which are decoded and passed on to the delegate."""
    
    def listenOnSocket_withDelegate_(self, path, delegate):
        for oldsocket in glob.glob(u"%s.*" % path):
            LogDebug(u"Removing old socket %@", oldsocket)
            try:
                os.unlink(oldsocket)
            except:
                pass
        self.socketPath = NSString.stringWithFormat_(u"%@.%@", path, os.urandom(8).encode("hex"))
        LogDebug(u"Creating socket at %@", self.socketPath)
        self.delegate = delegate
        self.watchThread = NSThread.alloc().initWithTarget_selector_object_(self, u"listenInBackground:", None)
        self.watchThread.start()
        return self.socketPath
    
    def stopListening(self):
        LogDebug(u"stopListening")
        self.watchThread.cancel()
        try:
            os.unlink(self.socketPath)
        except BaseException as e:
            LogWarning(u"Couldn't remove listener socket %@: %@", self.socketPath, unicode(e))
    
    def listenInBackground_(self, ignored):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.bind(self.socketPath)
        except socket.error as e:
            LogError(u"Error creating datagram socket at %@: %@", self.socketPath, unicode(e))
            return
        
        LogDebug(u"Listening to socket in background thread")
        while True:
            msg = sock.recv(IEDSL_MAX_MSG_SIZE, socket.MSG_WAITALL)
            if not msg:
                continue
            msgData = NSData.dataWithBytes_length_(msg, len(msg))
            plist, format, error = NSPropertyListSerialization.propertyListWithData_options_format_error_(msgData,
                                                                                                          NSPropertyListImmutable,
                                                                                                          None,
                                                                                                          None)
            if not plist:
                LogError(u"Error decoding plist: %@", error)
                continue
            if self.delegate.respondsToSelector_(u"socketReceivedMessage:"):
                self.delegate.performSelectorOnMainThread_withObject_waitUntilDone_(u"socketReceivedMessage:", plist, NO)

########NEW FILE########
__FILENAME__ = IEDSourceSelector
# -*- coding: utf-8 -*-
#
#  IEDSourceSelector.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-09-19.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from AppKit import *
from objc import IBAction, IBOutlet, classAddMethods

import os.path
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
from IEDUtil import *


def awakeFromNib(self):
    self.registerForDraggedTypes_([NSFilenamesPboardType])
    self.startAcceptingDrag()

def setDelegate_(self, _delegate):
    self._delegate = _delegate

def startAcceptingDrag(self):
    self.dragEnabled = True

def stopAcceptingDrag(self):
    self.dragEnabled = False

def checkSource_(self, sender):
    pboard = sender.draggingPasteboard()
    filenames = pboard.propertyListForType_(NSFilenamesPboardType)
    if len(filenames) != 1:
        return None
    path = IEDUtil.resolvePath_(filenames[0])
    if os.path.exists(os.path.join(path,
                      u"Contents/SharedSupport/InstallESD.dmg")):
        return path
    elif path.lower().endswith(u".dmg"):
        return path
    else:
        return None

def draggingEntered_(self, sender):
    self.dragOperation = NSDragOperationNone
    if self.dragEnabled:
        if self.checkSource_(sender):
            self.dragOperation = NSDragOperationCopy
    return self.dragOperation

def draggingUpdated_(self, sender):
    return self.dragOperation

def performDragOperation_(self, sender):
    filename = self.checkSource_(sender)
    if filename:
        self._delegate.acceptSource_(filename)
        return True
    else:
        return False


class IEDBoxSourceSelector(NSBox):
    pass
classAddMethods(IEDBoxSourceSelector, [
    awakeFromNib,
    setDelegate_,
    startAcceptingDrag,
    stopAcceptingDrag,
    checkSource_,
    draggingEntered_,
    draggingUpdated_,
    performDragOperation_,
])

class IEDImageViewSourceSelector(NSImageView):
    pass
classAddMethods(IEDImageViewSourceSelector, [
    awakeFromNib,
    setDelegate_,
    startAcceptingDrag,
    stopAcceptingDrag,
    checkSource_,
    draggingEntered_,
    draggingUpdated_,
    performDragOperation_,
])

class IEDTextFieldSourceSelector(NSTextField):
    pass
classAddMethods(IEDTextFieldSourceSelector, [
    awakeFromNib,
    setDelegate_,
    startAcceptingDrag,
    stopAcceptingDrag,
    checkSource_,
    draggingEntered_,
    draggingUpdated_,
    performDragOperation_,
])

########NEW FILE########
__FILENAME__ = IEDTemplate
# -*- coding: utf-8 -*-
#
#  IEDTemplate.py
#  AutoDMG
#
#  Created by Per Olofsson on 2014-02-26.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

import objc
from Foundation import *

import os.path
import re
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
from IEDUtil import *
from IEDPackage import *


class IEDTemplate(NSObject):
    
    def init(self):
        self = super(IEDTemplate, self).init()
        if self is None:
            return None
        
        self.sourcePath = None
        self.outputPath = None
        self.applyUpdates = False
        self.additionalPackages = NSMutableArray.alloc().init()
        self.volumeName = u"Macintosh HD"
        self.volumeSize = None
        self.packagesToInstall = None
        
        self.loadedTemplates = set()
        
        return self
    
    def __repr__(self):
        return "\n".join(("<IEDTemplate",
                          "    sourcePath=%s" % repr(self.sourcePath),
                          "    outputPath=%s" % repr(self.outputPath),
                          "    applyUpdates=%s" % repr(self.applyUpdates),
                          "    additionalPackages=(%s)" % ", ".join(repr(x) for x in self.additionalPackages),
                          "    volumeName=%s" % repr(self.volumeName),
                          "    volumeSize=%s" % repr(self.volumeSize),
                          ">"))
    
    def initWithSourcePath_(self, path):
        self = self.init()
        if self is None:
            return None
        
        self.setSourcePath_(path)
        
        return self
    
    def saveTemplateAndReturnError_(self, path):
        plist = NSMutableDictionary.alloc().init()
        plist[u"TemplateFormat"] = self.templateFormat = u"1.0"
        plist[u"AdditionalPackages"] = self.additionalPackages
        plist[u"ApplyUpdates"] = self.applyUpdates
        plist[u"VolumeName"] = self.volumeName
        if self.sourcePath:
            plist[u"SourcePath"] = self.sourcePath
        if self.outputPath:
            plist[u"OutputPath"] = self.outputPath
        if self.volumeSize:
            plist[u"VolumeSize"] = self.volumeSize
        if plist.writeToFile_atomically_(path, False):
            return None
        else:
            error = u"Couldn't write dictionary to plist at %s" % (path)
            LogWarning(u"%@", error)
            return error
    
    def loadTemplateAndReturnError_(self, path):
        if path in self.loadedTemplates:
            return u"%s included recursively" % path
        else:
            self.loadedTemplates.add(path)
        
        plist = NSDictionary.dictionaryWithContentsOfFile_(path)
        if not plist:
            error = u"Couldn't read dictionary from plist at %s" % (path)
            LogWarning(u"%@", error)
            return error
        
        templateFormat = plist.get(u"TemplateFormat", u"1.0")
        
        if templateFormat != u"1.0":
            LogWarning(u"Unknown format version %@", templateFormat)
        
        for key in plist.keys():
            if key == u"IncludeTemplates":
                for includePath in plist[u"IncludeTemplates"]:
                    LogInfo(u"Including template %@", includePath)
                    error = self.loadTemplateAndReturnError_(includePath)
                    if error:
                        return error
            elif key == u"SourcePath":
                self.setSourcePath_(plist[u"SourcePath"])
            elif key == u"ApplyUpdates":
                self.setApplyUpdates_(plist[u"ApplyUpdates"])
            elif key == u"AdditionalPackages":
                if not self.setAdditionalPackages_(plist[u"AdditionalPackages"]):
                    return u"Additional packages failed verification"
            elif key == u"OutputPath":
                self.setOutputPath_(plist[u"OutputPath"])
            elif key == u"VolumeName":
                self.setVolumeName_(plist[u"VolumeName"])
            elif key == u"VolumeSize":
                self.setVolumeSize_(plist[u"VolumeSize"])
            elif key == u"TemplateFormat":
                pass
            
            else:
                LogWarning(u"Unknown key '%@' in template", key)
        
        return None
    
    def setSourcePath_(self, path):
        LogInfo(u"Setting source path to '%@'", path)
        self.sourcePath = IEDUtil.resolvePath_(os.path.expanduser(path))
    
    def setApplyUpdates_(self, shouldApplyUpdates):
        LogInfo(u"Setting apply updates to '%@'", shouldApplyUpdates)
        self.applyUpdates = shouldApplyUpdates
    
    def setAdditionalPackages_(self, packagePaths):
        for packagePath in packagePaths:
            path = IEDUtil.resolvePath_(os.path.expanduser(packagePath))
            if not path:
                LogError(u"Package '%@' not found", packagePath)
                return False
            if path not in self.additionalPackages:
                LogInfo(u"Adding '%@' to additional packages", path)
                self.additionalPackages.append(IEDUtil.resolvePath_(path))
            else:
                LogInfo(u"Skipping duplicate package '%@'", path)
        return True
    
    def setOutputPath_(self, path):
        LogInfo(u"Setting output path to '%@'", path)
        self.outputPath = os.path.abspath(os.path.expanduser(path))
    
    def setVolumeName_(self, name):
        LogInfo(u"Setting volume name to '%@'", name)
        self.volumeName = name
    
    def setVolumeSize_(self, size):
        LogInfo(u"Setting volume size to '%d'", size)
        self.volumeSize = size
    
    def resolvePackages(self):
        self.packagesToInstall = list()
        for path in self.additionalPackages:
            package = IEDPackage.alloc().init()
            package.setName_(os.path.basename(path))
            package.setPath_(path)
            package.setSize_(IEDUtil.getPackageSize_(path))
            package.setImage_(NSWorkspace.sharedWorkspace().iconForFile_(path))
            self.packagesToInstall.append(package)
    
    re_keyref = re.compile(r'%(?P<key>[A-Z][A-Z_0-9]*)%')
    
    def resolveVariables_(self, variables):
        formatter = NSDateFormatter.alloc().init()
        formatter.setDateFormat_(u"yyMMdd")
        variables[u"DATE"] = formatter.stringFromDate_(NSDate.date())
        formatter.setDateFormat_(u"HHmmss")
        variables[u"TIME"] = formatter.stringFromDate_(NSDate.date())
        
        def getvar(m):
            try:
                return variables[m.group("key")]
            except KeyError as err:
                LogWarning("Template references undefined variable: %%%@%%", m.group("key"))
                return u"%%%s%%" % m.group("key")
        
        self.volumeName = self.re_keyref.sub(getvar, self.volumeName)
        self.outputPath = self.re_keyref.sub(getvar, self.outputPath)

########NEW FILE########
__FILENAME__ = IEDUpdateCache
# -*- coding: utf-8 -*-
#
#  IEDUpdateCache.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-22.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
import os
import hashlib

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage


class IEDUpdateCache(NSObject):
    """Managed updates cached on disk in the Application Support directory."""
    
    def init(self):
        self = super(IEDUpdateCache, self).init()
        if self is None:
            return None
        
        fm = NSFileManager.defaultManager()
        url, error = fm.URLForDirectory_inDomain_appropriateForURL_create_error_(NSApplicationSupportDirectory,
                                                                                 NSUserDomainMask,
                                                                                 None,
                                                                                 True,
                                                                                 None)
        self.updateDir = os.path.join(url.path(), u"AutoDMG", u"Updates")
        if not os.path.exists(self.updateDir):
            try:
                os.makedirs(self.updateDir)
            except OSError as e:
                LogError(u"Failed to create %@: %@", self.updateDir, unicode(e))
        
        return self
    
    def initWithDelegate_(self, delegate):
        self = self.init()
        if self is None:
            return None
        
        self.delegate = delegate
        
        return self
    
    # Given a dictionary with sha1 hashes pointing to filenames, clean the
    # cache of unreferenced items, and create symlinks from the filenames to
    # the corresponding cache files.
    def pruneAndCreateSymlinks(self, symlinks):
        LogInfo(u"Pruning cache")
        
        self.symlinks = symlinks
        
        # Create a reverse dictionary and a set of filenames.
        names = dict()
        filenames = set()
        for sha1, name in symlinks.iteritems():
            names[name] = sha1
            filenames.add(name)
            filenames.add(sha1)
        
        for item in os.listdir(self.updateDir):
            try:
                itempath = os.path.join(self.updateDir, item)
                if item not in filenames:
                    LogInfo(u"Removing %s" % item)
                    os.unlink(itempath)
            except OSError as e:
                LogWarning(u"Cache pruning of %s failed: %s" % (item, unicode(e)))
        for sha1 in symlinks.iterkeys():
            sha1Path = self.cachePath_(sha1)
            linkPath = self.updatePath_(sha1)
            name = os.path.basename(linkPath)
            if os.path.exists(sha1Path):
                if os.path.lexists(linkPath):
                    if os.readlink(linkPath) == sha1:
                        LogInfo(u"Found %s -> %s" % (name, sha1))
                        continue
                    LogInfo(u"Removing stale link %s -> %s" % (name, os.readlink(linkPath)))
                    try:
                        os.unlink(linkPath)
                    except OSError as e:
                        LogWarning(u"Cache pruning of %s failed: %s" % (name, unicode(c)))
                        continue
                LogInfo(u"Creating %s -> %s" % (name, sha1))
                os.symlink(sha1, linkPath)
            else:
                if os.path.lexists(linkPath):
                    LogInfo(u"Removing stale link %s -> %s" % (name, os.readlink(linkPath)))
                    try:
                        os.unlink(linkPath)
                    except OSError as e:
                        LogWarning(u"Cache pruning of %s failed: %s" % (name, unicode(c)))
            
    
    def isCached_(self, sha1):
        return os.path.exists(self.cachePath_(sha1))
    
    def updatePath_(self, sha1):
        return os.path.join(self.updateDir, self.symlinks[sha1])
    
    def cachePath_(self, sha1):
        return os.path.join(self.updateDir, sha1)
    
    def cacheTmpPath_(self, sha1):
        return os.path.join(self.updateDir, sha1 + u".part")
    
    
    
    # Download updates to cache.
    #
    # Delegate methods:
    #
    #     - (void)downloadAllDone
    #     - (void)downloadStarting:(NSDictionary *)update
    #     - (void)downloadGotData:(NSDictionary *)update bytesRead:(NSString *)bytes
    #     - (void)downloadSucceeded:(NSDictionary *)update
    #     - (void)downloadFailed:(NSDictionary *)update withError:(NSString *)message
    
    def downloadUpdates_(self, updates):
        self.updates = updates
        self.downloadNextUpdate()
    
    def stopDownload(self):
        self.connection.cancel()
        self.delegate.downloadStopped_(self.package)
        self.delegate.downloadAllDone()
    
    def downloadNextUpdate(self):
        if self.updates:
            self.package = self.updates.pop(0)
            self.bytesReceived = 0
            self.checksum = hashlib.sha1()
            self.delegate.downloadStarting_(self.package)
            
            path = self.cacheTmpPath_(self.package.sha1())
            if not NSFileManager.defaultManager().createFileAtPath_contents_attributes_(path, None, None):
                error = u"Couldn't create temporary file at %s" % path
                self.delegate.downloadFailed_withError_(self.package, error)
                return
            self.fileHandle = NSFileHandle.fileHandleForWritingAtPath_(path)
            if not self.fileHandle:
                error = u"Couldn't open %s for writing" % path
                self.delegate.downloadFailed_withError_(self.package, error)
                return
            
            url = NSURL.URLWithString_(self.package.url())
            request = NSURLRequest.requestWithURL_(url)
            self.connection = NSURLConnection.connectionWithRequest_delegate_(request, self)
            if self.connection:
                self.delegate.downloadStarted_(self.package)
        else:
            self.delegate.downloadAllDone()
    
    def connection_didFailWithError_(self, connection, error):
        LogError(u"%@ failed: %@", self.package.name(), error)
        self.delegate.downloadStopped_(self.package)
        self.fileHandle.closeFile()
        self.delegate.downloadFailed_withError_(self.package, error.localizedDescription())
        self.delegate.downloadAllDone()
    
    def connection_didReceiveResponse_(self, connection, response):
        LogDebug(u"%@ status code %d", self.package.name(), response.statusCode())
    
    def connection_didReceiveData_(self, connection, data):
        try:
            self.fileHandle.writeData_(data)
        except BaseException as e:
            LogError(u"Write error: %@", unicode(e))
            connection.cancel()
            error = u"Writing to %s failed: %s" % (self.cacheTmpPath_(self.package.sha1()), unicode(e))
            self.fileHandle.closeFile()
            self.delegate.downloadFailed_withError_(self.package, error)
            return
        self.checksum.update(data)
        self.bytesReceived += data.length()
        self.delegate.downloadGotData_bytesRead_(self.package, self.bytesReceived)
    
    def connectionDidFinishLoading_(self, connection):
        LogInfo(u"%@ finished downloading to %@", self.package.name(), self.cacheTmpPath_(self.package.sha1()))
        self.fileHandle.closeFile()
        self.delegate.downloadStopped_(self.package)
        if self.checksum.hexdigest() == self.package.sha1():
            try:
                os.rename(self.cacheTmpPath_(self.package.sha1()),
                          self.cachePath_(self.package.sha1()))
            except OSError as e:
                error = u"Failed when moving download to %s: %s" % (self.cachePath_(self.package.sha1()), unicode(e))
                LogError(error)
                self.delegate.downloadFailed_withError_(self.package, error)
                return
            linkPath = self.updatePath_(self.package.sha1())
            try:
                os.symlink(self.package.sha1(), linkPath)
            except OSError as e:
                error = u"Failed when creating link from %s to %s: %s" % (self.package.sha1(),
                                                                          linkPath,
                                                                          unicode(e))
                LogError(error)
                self.delegate.downloadFailed_withError_(self.package, error)
                return
            LogNotice(u"%@ added to cache with sha1 %@", self.package.name(), self.package.sha1())
            self.delegate.downloadSucceeded_(self.package)
            self.downloadNextUpdate()
        else:
            error = u"Expected sha1 checksum %s but got %s" % (sha1.lower(), m.hexdigest().lower())
            LogError(error)
            self.delegate.downloadFailed_withError_(self.package, error)

########NEW FILE########
__FILENAME__ = IEDUpdateController
# -*- coding: utf-8 -*-
#
#  IEDUpdateController.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-22.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from objc import IBAction, IBOutlet

from IEDProfileController import *
from IEDUpdateCache import *
from IEDPackage import *
from IEDUtil import *
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage, LogException


class IEDUpdateController(NSObject):
    
    profileController = IBOutlet()
    
    applyUpdatesCheckbox = IBOutlet()
    updateTable = IBOutlet()
    updateTableImage = IBOutlet()
    updateTableLabel = IBOutlet()
    downloadButton = IBOutlet()
    
    downloadWindow = IBOutlet()
    downloadLabel = IBOutlet()
    downloadProgressBar = IBOutlet()
    downloadStopButton = IBOutlet()
    
    def init(self):
        self = super(IEDUpdateController, self).init()
        if self is None:
            return None
        
        self.cache = IEDUpdateCache.alloc().initWithDelegate_(self)
        self.updates = list()
        self.downloadTotalSize = 0
        self.downloads = list()
        self.delegate = None
        self.version = None
        self.build = None
        self.profileWarning = None
        
        return self
    
    def setDelegate_(self, delegate):
        self.delegate = delegate
    
    def awakeFromNib(self):
        self.cachedImage = NSImage.imageNamed_(u"Package")
        self.uncachedImage = NSImage.imageNamed_(u"Package blue arrow")
        
        self.updatesAllOKImage = NSImage.imageNamed_(u"Checkmark")
        self.updatesToDownloadImage = NSImage.imageNamed_(u"Download")
        self.updatesWarningImage = NSImage.imageNamed_(u"Exclamation")
        self.updateTableImage.setImage_(None)
        self.updateTableLabel.setStringValue_(u"")
        self.updateTable.setDataSource_(self)
    
    # Helper methods.
    
    def disableControls(self):
        LogDebug(u"disableControls")
        self.applyUpdatesCheckbox.setEnabled_(False)
        self.updateTable.setEnabled_(False)
        self.downloadButton.setEnabled_(False)
    
    def enableControls(self):
        LogDebug(u"enableControls")
        self.applyUpdatesCheckbox.setEnabled_(len(self.updates) > 0)
        self.updateTable.setEnabled_(len(self.updates) > 0)
        self.downloadButton.setEnabled_(len(self.downloads) > 0)
    
    def showRemainingDownloads(self):
        if self.profileWarning:
            self.updateTableImage.setImage_(self.updatesWarningImage)
            self.updateTableLabel.setStringValue_(self.profileWarning)
            self.updateTableLabel.setTextColor_(NSColor.controlTextColor())
            return
        
        if len(self.downloads) == 0:
            self.updateTableLabel.setStringValue_(u"All updates downloaded")
            self.updateTableLabel.setTextColor_(NSColor.disabledControlTextColor())
            self.updateTableImage.setImage_(self.updatesAllOKImage)
        else:
            sizeStr = IEDUtil.formatBytes_(self.downloadTotalSize)
            plurals = u"s" if len(self.downloads) >= 2 else u""
            downloadLabel = u"%d update%s to download (%s)" % (len(self.downloads), plurals, sizeStr)
            self.updateTableLabel.setStringValue_(downloadLabel)
            self.updateTableLabel.setEnabled_(True)
            self.updateTableLabel.setTextColor_(NSColor.controlTextColor())
            self.updateTableImage.setImage_(self.updatesToDownloadImage)
    
    def countDownloads(self):
        LogDebug(u"countDownloads")
        self.downloads = list()
        self.downloadTotalSize = 0
        for package in self.updates:
            if self.cache.isCached_(package.sha1()):
                package.setImage_(self.cachedImage)
            else:
                package.setImage_(self.uncachedImage)
                self.downloadTotalSize += package.size()
                self.downloads.append(package)
        self.updateTable.reloadData()
        self.showRemainingDownloads()
    
    # External state of controller.
    
    def allUpdatesDownloaded(self):
        if self.applyUpdatesCheckbox.state() == NSOffState:
            return True
        return len(self.downloads) == 0
    
    def packagesToInstall(self):
        if self.applyUpdatesCheckbox.state() == NSOffState:
            return []
        return self.updates
    
    
    
    # Act on profile update requested.
    
    @LogException
    @IBAction
    def checkForProfileUpdates_(self, sender):
        LogInfo(u"Checking for updates")
        self.disableControls()
        defaults = NSUserDefaults.standardUserDefaults()
        url = NSURL.URLWithString_(defaults.stringForKey_(u"UpdateProfilesURL"))
        self.profileController.updateFromURL_(url)
    
    @LogException
    @IBAction
    def cancelProfileUpdateCheck_(self, sender):
        self.profileController.cancelUpdateDownload()
    
    # IEDProfileController delegate methods.
    
    def profileUpdateAllDone(self):
        self.enableControls()
    
    def profileUpdateFailed_(self, error):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(error.localizedDescription())
        alert.setInformativeText_(error.userInfo()[NSErrorFailingURLStringKey])
        alert.runModal()
    
    def profileUpdateSucceeded_(self, publicationDate):
        LogDebug(u"profileUpdateSucceeded:%@", publicationDate)
        defaults = NSUserDefaults.standardUserDefaults()
        defaults.setObject_forKey_(NSDate.date(), u"LastUpdateProfileCheck")
    
    def profilesUpdated(self):
        LogDebug(u"profilesUpdated")
        self.cache.pruneAndCreateSymlinks(self.profileController.updatePaths)
        if self.version or self.build:
            self.loadProfileForVersion_build_(self.version, self.build)
    
    # Load update profile.
    
    def loadProfileForVersion_build_(self, version, build):
        LogDebug(u"loadProfileForVersion:%@ build:%@", version, build)
        self.version = version
        self.build = build
        self.updates = list()
        profile = self.profileController.profileForVersion_Build_(version, build)
        if profile is None:
            # No update profile for this build, try to figure out why.
            self.profileWarning = self.profileController.whyNoProfileForVersion_build_(version, build)
        else:
            self.profileWarning = None
            for update in profile:
                package = IEDPackage.alloc().init()
                package.setName_(update[u"name"])
                package.setPath_(self.cache.updatePath_(update[u"sha1"]))
                package.setSize_(update[u"size"])
                package.setUrl_(update[u"url"])
                package.setSha1_(update[u"sha1"])
                # Image is set by countDownloads().
                self.updates.append(package)
        self.countDownloads()
    
    
    
    # Act on apply updates checkbox changing.
    
    @LogException
    @IBAction
    def applyUpdatesCheckboxChanged_(self, sender):
        if self.delegate:
            self.delegate.updateControllerChanged()
    
    
    
    # Act on download button being clicked.
    
    @LogException
    @IBAction
    def downloadButtonClicked_(self, sender):
        self.disableControls()
        self.downloadLabel.setStringValue_(u"")
        self.downloadProgressBar.setIndeterminate_(True)
        self.downloadWindow.makeKeyAndOrderFront_(self)
        self.downloadCounter = 0
        self.downloadNumUpdates = len(self.downloads)
        self.cache.downloadUpdates_(self.downloads)
    
    # Act on download stop button being clicked.
    
    @LogException
    @IBAction
    def downloadStopButtonClicked_(self, sender):
        self.cache.stopDownload()
    
    # UpdateCache delegate methods.
    
    def downloadAllDone(self):
        LogDebug(u"downloadAllDone")
        self.downloadWindow.orderOut_(self)
        self.countDownloads()
        self.enableControls()
        if self.delegate:
            self.delegate.updateControllerChanged()
    
    def downloadStarting_(self, package):
        LogDebug(u"downloadStarting:")
        self.downloadProgressBar.setIndeterminate_(False)
        self.downloadProgressBar.setDoubleValue_(0.0)
        self.downloadProgressBar.setMaxValue_(package.size())
        self.downloadCounter += 1
        self.downloadLabel.setStringValue_(u"%s (%s)" % (package.name(), IEDUtil.formatBytes_(package.size())))
    
    def downloadStarted_(self, package):
        LogDebug(u"downloadStarted:")
        self.downloadStopButton.setEnabled_(True)
    
    def downloadStopped_(self, package):
        LogDebug(u"downloadStopped:")
        self.downloadStopButton.setEnabled_(False)
    
    def downloadGotData_bytesRead_(self, package, bytes):
        self.downloadProgressBar.setDoubleValue_(bytes)
    
    def downloadSucceeded_(self, package):
        LogDebug(u"downloadSucceeded:")
        self.countDownloads()
        if self.delegate:
            self.delegate.updateControllerChanged()
    
    def downloadFailed_withError_(self, package, message):
        LogDebug(u"downloadFailed:withError:")
        alert = NSAlert.alloc().init()
        alert.setMessageText_(u"Download failed")
        alert.setInformativeText_(message)
        alert.runModal()
    
    
    
    # We're an NSTableViewDataSource.
    
    def numberOfRowsInTableView_(self, tableView):
        return len(self.updates)
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        # FIXME: Use bindings.
        if column.identifier() == u"image":
            return self.updates[row].image()
        elif column.identifier() == u"name":
            return self.updates[row].name()

########NEW FILE########
__FILENAME__ = IEDUtil
# -*- coding: utf-8 -*-
#
#  IEDUtil.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-31.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
from Carbon.File import *
import MacOS

import os.path
import subprocess
import tempfile
import shutil
from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
try:
    IEDMountInfo = objc.lookUpClass(u"IEDMountInfo")
except objc.nosuchclass_error:
    # Create a dummy class to allow import from pure python for testing. Will
    # crash when an attempt is made to use the class.
    class IEDMountInfo(object):
        pass


class IEDUtil(NSObject):
    
    VERSIONPLIST_PATH = u"System/Library/CoreServices/SystemVersion.plist"
    
    @classmethod
    def readSystemVersion_(cls, rootPath):
        plist = NSDictionary.dictionaryWithContentsOfFile_(os.path.join(rootPath, cls.VERSIONPLIST_PATH))
        name = plist[u"ProductName"]
        version = plist[u"ProductUserVisibleVersion"]
        build = plist[u"ProductBuildVersion"]
        return (name, version, build)
    
    @classmethod
    def getAppVersion(cls):
        bundle = NSBundle.mainBundle()
        version = bundle.objectForInfoDictionaryKey_(u"CFBundleShortVersionString")
        build = bundle.objectForInfoDictionaryKey_(u"CFBundleVersion")
        return (version, build)
    
    @classmethod
    def resolvePath_(cls, path):
        """Expand symlinks and resolve aliases."""
        try:
            fsref, isFolder, wasAliased = FSResolveAliasFile(os.path.realpath(path), 1)
            return os.path.abspath(fsref.as_pathname().decode(u"utf-8"))
        except MacOS.Error as e:
            return None
    
    @classmethod
    def installESDPath_(cls, path):
        u"""Resolve aliases and return path to InstallESD."""
        path = cls.resolvePath_(path)
        if not path:
            return None
        if os.path.exists(os.path.join(path,
                          u"Contents/SharedSupport/InstallESD.dmg")):
            return path
        if (os.path.basename(path).lower().startswith(u"installesd") and
            os.path.basename(path).lower().endswith(u".dmg")) and \
           os.path.exists(path):
            return path
        else:
            return None
    
    @classmethod
    def getPackageSize_(cls, path):
        p = subprocess.Popen([u"/usr/bin/du", u"-sk", path],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            LogError(u"du failed with exit code %d", p.returncode)
            return 0
        else:
            return int(out.split()[0]) * 1024
    
    @classmethod
    def formatBytes_(cls, bytes):
        bytes = float(bytes)
        unitIndex = 0
        while len(str(int(bytes))) > 3:
            bytes /= 1000.0
            unitIndex += 1
        return u"%.1f %s" % (bytes, (u"bytes", u"kB", u"MB", u"GB", u"TB")[unitIndex])
    
    @classmethod
    def findMountPoint_(cls, path):
        path = os.path.abspath(path)
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        return path
    
    @classmethod
    def getInstalledPkgSize_(cls, pkgPath):
        # For apps just return the size on disk.
        name, ext = os.path.splitext(pkgPath)
        if ext == u".app":
            return cls.getPackageSize_(pkgPath)
        # For packages try to get the size requirements with installer.
        pkgFileName = os.path.os.path.basename(pkgPath)
        tempdir = tempfile.mkdtemp()
        try:
            symlinkPath = os.path.join(tempdir, pkgFileName)
            os.symlink(pkgPath, symlinkPath)
            p = subprocess.Popen([u"/usr/sbin/installer",
                                  u"-pkginfo",
                                  u"-verbose",
                                  u"-plist",
                                  u"-pkg",
                                  symlinkPath],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out, err = p.communicate()
        finally:
            try:
                shutil.rmtree(tempdir)
            except BaseException as e:
                LogWarning(u"Unable to remove tempdir: %@", unicode(e))
        # Try to handle some common scenarios when installer fails.
        if p.returncode == -11:
            LogWarning(u"Estimating package size since installer -pkginfo "
                       u"'%@' crashed", pkgPath)
            return cls.getPackageSize_(pkgPath) * 2
        elif p.returncode != 0:
            mountPoints = IEDMountInfo.getMountPoints()
            fsInfo = mountPoints[cls.findMountPoint_(pkgPath)]
            if not fsInfo[u"islocal"]:
                LogWarning(u"Estimating package size since installer -pkginfo "
                           u"failed and '%@' is on a remote (%@) filesystem",
                           pkgPath, fsInfo[u"fstypename"])
                return cls.getPackageSize_(pkgPath) * 2
            else:
                LogError(u"installer -pkginfo -pkg '%@' failed with exit code %d", pkgPath, p.returncode)
                return None
        outData = NSData.dataWithBytes_length_(out, len(out))
        plist, format, error = NSPropertyListSerialization.propertyListWithData_options_format_error_(outData,
                                                                                                      NSPropertyListImmutable,
                                                                                                      None,
                                                                                                      None)
        if not plist:
            LogError(u"Error decoding plist: %@", error)
            return None
        LogDebug(u"%@ requires %@", pkgPath, cls.formatBytes_(int(plist[u"Size"]) * 1024))
        return int(plist[u"Size"]) * 1024

########NEW FILE########
__FILENAME__ = IEDWorkflow
# -*- coding: utf-8 -*-
#
#  IEDWorkflow.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-10-24.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

from Foundation import *
import os.path
import platform
import glob
import grp
import traceback
import time
import tempfile
import shutil
import datetime

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
from IEDUtil import *
from IEDSocketListener import *
from IEDDMGHelper import *
from IEDTemplate import *


class IEDWorkflow(NSObject):
    """The workflow contains the logic needed to setup, execute, and report
    the result of the build.
    """
    
    INSTALL_ESD = 1
    SYSTEM_IMAGE = 2
    
    def init(self):
        self = super(IEDWorkflow, self).init()
        if self is None:
            return None
        
        # Helper class for managing disk images.
        self.dmgHelper = IEDDMGHelper.alloc().initWithDelegate_(self)
        
        # Socket for communicating with helper processes.
        self.listener = IEDSocketListener.alloc().init()
        self.listenerPath = self.listener.listenOnSocket_withDelegate_(u"/tmp/se.gu.it.IEDSocketListener", self)
        
        # State for the workflow.
        self._source = None
        self._outputPath = None
        self._volumeName = u"Macintosh HD"
        self.installerMountPoint = None
        self.additionalPackages = list()
        self.attachedPackageDMGs = dict()
        self.lastUpdateMessage = None
        self._authUsername = None
        self._authPassword = None
        self._volumeSize = None
        self._template = None
        self.tempDir = None
        self.templatePath = None
        
        return self
    
    def initWithDelegate_(self, delegate):
        self = self.init()
        if self is None:
            return None
        
        self.delegate = delegate
        
        return self
    
    # Helper methods.
    
    def cleanup(self):
        LogDebug(u"cleanup")
        self.listener.stopListening()
        self.dmgHelper.detachAll_(None)
    
    def handleDetachResult_(self, result):
        if result[u"success"]:
            try:
                del self.attachedPackageDMGs[result[u"dmg-path"]]
            except KeyError:
                pass
        else:
            self.delegate.detachFailed_details_(result[u"dmg-path"], result[u"error-message"])
    
    def detachInstallerDMGs(self):
        LogDebug(u"Detaching installer DMGs")
        for dmgPath, mountPoint in self.attachedPackageDMGs.iteritems():
            self.dmgHelper.detach_selector_(dmgPath, self.handleDetachResult_)
    
    def alertFailedUnmounts_(self, failedUnmounts):
        if failedUnmounts:
            text = u"\n".join(u"%s: %s" % (dmg, error) for dmg, error in failedUnmounts.iteritems())
            self.delegate.displayAlert_text_(u"Failed to eject dmgs", text)
    
    
    
    # External state of controller.
    
    def hasSource(self):
        return self.installerMountPoint is not None
    
    
    
    # Common delegate methods:
    #
    #     - (void)displayAlert:(NSString *)message text:(NSString *)text
    #     - (void)detachFailed:(NSString *)message details:(NSString *)details
    
    
    
    # Set a new installer source.
    #
    # Delegate methods:
    #
    #     - (void)ejectingSource
    #     - (void)examiningSource:(NSString *)path
    #     - (void)sourceSucceeded:(NSDictionary *)info
    #     - (void)sourceFailed:(NSString *)message text:(NSString *)text
    
    def setSource_(self, path):
        LogDebug(u"setSource:%@", path)
        
        self._source = None
        self.newSourcePath = path
        if self.installerMountPoint:
            self.delegate.ejectingSource()
            self.dmgHelper.detachAll_(self.continueSetSource_)
        else:
            self.continueSetSource_({})
    
    def source(self):
        return self._source
    
    def continueSetSource_(self, failedUnmounts):
        LogDebug(u"continueSetSource:%@", failedUnmounts)
        
        self.alertFailedUnmounts_(failedUnmounts)
        
        self.installESDPath = os.path.join(self.newSourcePath, u"Contents/SharedSupport/InstallESD.dmg")
        if not os.path.exists(self.installESDPath):
            self.installESDPath = self.newSourcePath
        
        self.delegate.examiningSource_(self.newSourcePath)
        
        self.installerMountPoint = None
        self.baseSystemMountedFromPath = None
        self.dmgHelper.attach_selector_(self.installESDPath, self.handleSourceMountResult_)
    
    # handleSourceMountResult: may be called twice, once for InstallESD.dmg
    # and once for BaseSystem.dmg.
    def handleSourceMountResult_(self, result):
        LogDebug(u"handleSourceMountResult:%@", result)
        
        if not result[u"success"]:
            self.delegate.sourceFailed_text_(u"Failed to mount %s" % result[u"dmg-path"],
                                             result[u"error-message"])
            return
        
        mountPoint = result[u"mount-point"]
        
        # Update the icon if we find an installer app.
        for path in glob.glob(os.path.join(mountPoint, u"Install*.app")):
            self.delegate.foundSourceForIcon_(path)
        
        # Don't set this again since 10.9 mounts BaseSystem.dmg after InstallESD.dmg.
        if self.installerMountPoint is None:
            self.installerMountPoint = mountPoint
            # Check if the source is an InstallESD or system image.
            if os.path.exists(os.path.join(mountPoint, u"Packages", u"OSInstall.mpkg")):
                self.sourceType = IEDWorkflow.INSTALL_ESD
                LogDebug(u"sourceType = INSTALL_ESD")
            else:
                self.sourceType = IEDWorkflow.SYSTEM_IMAGE
                LogDebug(u"sourceType = SYSTEM_IMAGE")
        
        baseSystemPath = os.path.join(mountPoint, u"BaseSystem.dmg")
        
        # If we find a SystemVersion.plist we proceed to the next step.
        if os.path.exists(os.path.join(mountPoint, IEDUtil.VERSIONPLIST_PATH)):
            self.checkVersion_(mountPoint)
        # Otherwise check if there's a BaseSystem.dmg that we need to examine.
        elif os.path.exists(baseSystemPath):
            self.baseSystemMountedFromPath = baseSystemPath
            self.dmgHelper.attach_selector_(baseSystemPath, self.handleSourceMountResult_)
        else:
            self.delegate.sourceFailed_text_(u"Invalid source",
                                             u"Couldn't find system version.")
    
    def checkVersion_(self, mountPoint):
        LogDebug(u"checkVersion:%@", mountPoint)
        
        # We're now examining InstallESD.dmg for 10.7/10.8, BaseSystem.dmg for
        # 10.9, or a system image.
        name, version, build = IEDUtil.readSystemVersion_(mountPoint)
        if self.baseSystemMountedFromPath:
            self.dmgHelper.detach_selector_(self.baseSystemMountedFromPath, self.handleDetachResult_)
        installerVersion = tuple(int(x) for x in version.split(u"."))
        runningVersion = tuple(int(x) for x in platform.mac_ver()[0].split(u"."))
        if installerVersion[:2] != runningVersion[:2]:
            self.delegate.ejectingSource()
            self.dmgHelper.detachAll_(self.rejectSource_)
            return
        LogNotice(u"Accepted source %@: %@ %@ %@", self.newSourcePath, name, version, build)
        self._source = self.newSourcePath
        self.installerName = name
        self.installerVersion = version
        self.installerBuild = build
        info = {
            u"name": name,
            u"version": version,
            u"build": build,
            u"template": self.loadImageTemplate_(mountPoint),
            u"sourceType": self.sourceType,
        }
        self.delegate.sourceSucceeded_(info)
        # There's no reason to keep the dmg mounted if it's not an installer.
        if self.sourceType == IEDWorkflow.SYSTEM_IMAGE:
            self.dmgHelper.detachAll_(self.ejectSystemImage_)
    
    def loadImageTemplate_(self, mountPoint):
        LogDebug(u"checkTemplate:%@", mountPoint)
        try:
            path = glob.glob(os.path.join(mountPoint, u"private/var/log/*.adtmpl"))[0]
        except IndexError:
            return None
        template = IEDTemplate.alloc().init()
        error = template.loadTemplateAndReturnError_(path)
        if error:
            LogWarning(u"Error reading %@ from image: %@", os.path.basename(path), error)
            return None
        return template
    
    def rejectSource_(self, failedUnmounts):
        self.delegate.sourceFailed_text_(u"Version mismatch",
                                         u"The major version of the installer and the current OS must match.")
        self.alertFailedUnmounts_(failedUnmounts)
    
    def ejectSystemImage_(self, failedUnmounts):
        self.alertFailedUnmounts_(failedUnmounts)
    
    
    
    # Set a list of packages to install after the OS.
    
    def setPackagesToInstall_(self, packages):
        self.additionalPackages = packages
    
    # Path to generated disk image.
    
    def outputPath(self):
        return self._outputPath
    
    def setOutputPath_(self, path):
        self._outputPath = path
    
    # Volume name.
    
    def volumeName(self):
        return self._volumeName
    
    def setVolumeName_(self, name):
        self._volumeName = name
    
    # Username and password.
    
    def authUsername(self):
        return self._authUsername
    
    def setAuthUsername_(self, authUsername):
        self._authUsername = authUsername
    
    def authPassword(self):
        return self._authPassword
    
    def setAuthPassword_(self, authPassword):
        self._authPassword = authPassword
    
    # DMG size.
    
    def volumeSize(self):
        return self._volumeSize
    
    def setVolumeSize_(self, size):
        self._volumeSize = size
    
    # Template to save in image.
    
    def template(self):
        return self._template
    
    def setTemplate_(self, template):
        self._template = template
    
    # Handle temporary directory during workflow.
    
    def createTempDir(self):
        self.tempDir = tempfile.mkdtemp()
    
    def deleteTempDir(self):
        if self.tempDir:
            try:
                shutil.rmtree(self.tempDir)
            except OSError as e:
                LogWarning(u"Can't remove temporary directory '%@': %@",
                           self.tempDir,
                           unicode(e))
            finally:
                self.tempDir = None
    
    # Start the workflow.
    #
    # Delegate methods:
    #
    #     - (void)buildStartingWithOutput:(NSString *)outputPath
    #     - (void)buildSetTotalWeight:(double)totalWeight
    #     - (void)buildSetPhase:(NSString *)phase
    #     - (void)buildSetProgress:(double)progress
    #     - (void)buildSetProgressMessage:(NSString *)message
    #     - (void)buildSucceeded
    #     - (void)buildFailed:(NSString *)message details:(NSString *)details
    #     - (void)buildStopped
    
    def start(self):
        LogNotice(u"Starting build")
        LogNotice(u"Using installer: %@ %@ %@", self.installerName, self.installerVersion, self.installerBuild)
        LogNotice(u"Using output path: %@", self.outputPath())
        self.delegate.buildStartingWithOutput_(self.outputPath())
        
        self.createTempDir()
        LogDebug(u"Created temporary directory at %@", self.tempDir)
        
        if not self.template():
            self.fail_details_(u"Template missing",
                               u"A template for inclusion in the image is required.")
            return
        
        datestamp = datetime.datetime.today().strftime("%Y%m%d")
        self.templatePath = os.path.join(self.tempDir, u"AutoDMG-%s.adtmpl" % datestamp)
        LogDebug(u"Saving template to %@", self.templatePath)
        error = self.template().saveTemplateAndReturnError_(self.templatePath)
        if error:
            self.fail_details_(u"Couldn't save template to tempdir", error)
            return
        
        # The workflow is split into tasks, and each task has one or more
        # phases. Each phase of the installation is given a weight for the
        # progress bar, calculated from the size of the installer package.
        # Phases that don't install packages get an estimated weight.
        
        self.tasks = list()
        
        # Prepare for install.
        self.tasks.append({
            u"method": self.taskPrepare,
            u"phases": [
                {u"title": u"Preparing", u"weight": 34 * 1024 * 1024},
            ],
        })
        
        # Perform installation.
        installerPhases = [
            {u"title": u"Starting install",    u"weight":       21 * 1024 * 1024},
            {u"title": u"Creating disk image", u"weight":       21 * 1024 * 1024},
        ]
        if self.sourceType == IEDWorkflow.INSTALL_ESD:
            installerPhases.append({
                u"title": u"Installing OS",
                u"weight": 4 * 1024 * 1024 * 1024,
            })
        for package in self.additionalPackages:
            installerPhases.append({
                u"title": u"Installing %s" % package.name(),
                # Add 100 MB to the weight to account for overhead.
                u"weight": package.size() + 100 * 1024 * 1024,
            })
        installerPhases.extend([
            # hdiutil convert.
            {u"title": u"Converting disk image", u"weight": 313 * 1024 * 1024},
        ])
        self.tasks.append({
            u"method": self.taskInstall,
            u"phases": installerPhases,
        })
        
        # Finalize image.
        self.tasks.append({
            u"method": self.taskFinalize,
            u"phases": [
                {u"title": u"Scanning disk image", u"weight":   2 * 1024 * 1024},
                {u"title": u"Scanning disk image", u"weight":   1 * 1024 * 1024},
                {u"title": u"Scanning disk image", u"weight": 150 * 1024 * 1024},
                {u"title": u"Scanning disk image", u"weight":  17 * 1024 * 1024, u"optional": True},
            ],
        })
        
        # Finish build.
        self.tasks.append({
            u"method": self.taskFinish,
            u"phases": [
                {u"title": u"Finishing", u"weight": 1 * 1024 * 1024},
            ],
        })
        
        # Calculate total weight of all phases.
        self.totalWeight = 0
        for task in self.tasks:
            LogInfo(u"Task %@ with %d phases:", task[u"method"].__name__, len(task[u"phases"]))
            for phase in task[u"phases"]:
                LogInfo(u"    Phase '%@' with weight %.1f", phase[u"title"], phase[u"weight"] / 1048576.0)
                self.totalWeight += phase[u"weight"]
        self.delegate.buildSetTotalWeight_(self.totalWeight)
        
        # Start the first task.
        self.progress = 0
        self.currentTask = None
        self.currentPhase = None
        self.nextTask()
    
    
    
    # Task and phase logic.
    
    def nextTask(self):
        LogDebug(u"nextTask, currentTask == %@", self.currentTask)
        
        if self.currentTask:
            if self.currentTask[u"phases"]:
                for phase in self.currentTask[u"phases"]:
                    if not phase.get(u"optional", False):
                        details = NSString.stringWithFormat_(u"Phases remaining: %@", self.currentTask[u"phases"])
                        self.fail_details_(u"Task finished prematurely", details)
                        return
        if self.tasks:
            self.currentTask = self.tasks.pop(0)
            LogNotice(u"Starting task with %d phases", len(self.currentTask[u"phases"]))
            self.nextPhase()
            self.currentTask[u"method"]()
        else:
            LogNotice(u"Build finished successfully, image saved to %@", self.outputPath())
            self.delegate.buildSucceeded()
            self.stop()
    
    def nextPhase(self):
        LogDebug(u"nextPhase, currentPhase == %@", self.currentPhase)
        
        if self.currentPhase:
            self.progress += self.currentPhase[u"weight"]
            LogInfo(u"Phase %@ with weight %ld finished after %.3f seconds",
                    self.currentPhase[u"title"],
                    self.currentPhase[u"weight"],
                    time.time() - self.phaseStartTime)
        self.phaseStartTime = time.time()
        try:
            self.currentPhase = self.currentTask[u"phases"].pop(0)
        except IndexError:
            self.fail_details_(u"No phase left in task", traceback.format_stack())
            return
        LogNotice(u"Starting phase: %@", self.currentPhase[u"title"])
        self.delegate.buildSetPhase_(self.currentPhase[u"title"])
        self.delegate.buildSetProgress_(self.progress)
    
    def fail_details_(self, message, text):
        LogError(u"Workflow failed: %@ (%@)", message, text)
        self.delegate.buildFailed_details_(message, text)
        self.stop()
    
    # Stop is called at the end of a workflow, regardless of if it succeeded
    # or failed.
    def stop(self):
        LogDebug(u"Workflow stopping")
        self.deleteTempDir()
        self.detachInstallerDMGs()
        self.delegate.buildStopped()
    
    
    
    # Task: Prepare.
    #
    #    1. Go through the list of packages to install and if they're
    #       contained in disk images, mount them.
    #    2. Generate a list of paths to the packages for the install task.
    
    def taskPrepare(self):
        LogDebug(u"taskPrepare")
        
        # Attach any disk images containing update packages.
        self.attachedPackageDMGs = dict()
        self.numberOfDMGsToAttach = 0
        for package in self.additionalPackages:
            if package.path().endswith(u".dmg"):
                self.numberOfDMGsToAttach += 1
                LogInfo(u"Attaching %@", package.path())
                self.dmgHelper.attach_selector_(package.path(), self.attachPackageDMG_)
        if self.numberOfDMGsToAttach == 0:
            self.continuePrepare()
    
    # This will be called once for each disk image.
    def attachPackageDMG_(self, result):
        LogDebug(u"attachPackageDMG:%@", result)
        
        if not result[u"success"]:
            self.fail_details_(u"Failed to attach %s" % result[u"dmg-path"],
                               result[u"error-message"])
            return
        # Save result in a dictionary of dmg paths and their mount points.
        self.attachedPackageDMGs[result[u"dmg-path"]] = result[u"mount-point"]
        # If this was the last image we were waiting for, continue preparing
        # for install.
        if len(self.attachedPackageDMGs) == self.numberOfDMGsToAttach:
            self.continuePrepare()
    
    def continuePrepare(self):
        LogDebug(u"continuePrepare")
        
        # Generate a list of packages to install.
        self.packagesToInstall = list()
        if self.sourceType == IEDWorkflow.INSTALL_ESD:
            self.packagesToInstall.append(os.path.join(self.installerMountPoint,
                                                       u"Packages",
                                                       u"OSInstall.mpkg"))
        for package in self.additionalPackages:
            if package.path().endswith(u".dmg"):
                mountPoint = self.attachedPackageDMGs[package.path()]
                LogDebug(u"Looking for packages and applications in %@: %@",
                         mountPoint,
                         glob.glob(os.path.join(mountPoint, "*")))
                packagePaths = glob.glob(os.path.join(mountPoint, "*.mpkg"))
                packagePaths += glob.glob(os.path.join(mountPoint, "*.pkg"))
                packagePaths += glob.glob(os.path.join(mountPoint, "*.app"))
                if len(packagePaths) == 0:
                    self.fail_details_(u"Nothing found to install",
                                       u"No package or application found in %s" % package.name())
                    return
                elif len(packagePaths) > 1:
                    LogWarning(u"Multiple items found in %s, using %s" % (package.path(), packagePaths[0]))
                self.packagesToInstall.append(packagePaths[0])
            else:
                self.packagesToInstall.append(package.path())
        if len(self.packagesToInstall) == 0:
            self.delegate.buildFailed_details_(u"Nothing to do",
                                               u"There are no packages to install")
            self.stop()
            return
        
        # Calculate disk image size requirements.
        sizeRequirement = 0
        LogInfo(u"%d packages to install:", len(self.packagesToInstall))
        for path in self.packagesToInstall:
            LogInfo(u"    %@", path)
            installedSize = IEDUtil.getInstalledPkgSize_(path)
            if installedSize is None:
                self.delegate.buildFailed_details_(u"Failed to determine installed size",
                                                   u"Unable to determine installation size requirements for %s" % path)
                self.stop()
                return
            sizeRequirement += installedSize
        sizeReqStr = IEDUtil.formatBytes_(sizeRequirement)
        LogInfo(u"Workflow requires a %@ disk image", sizeReqStr)
        
        if self.volumeSize() is None:
            # Calculate DMG size. Multiply package requirements by 1.1, round
            # to the nearest GB, and add 23.
            self.setVolumeSize_(int((float(sizeRequirement) * 1.1) / (1000.0 * 1000.0 * 1000.0) + 23.5))
        else:
            # Make sure user specified image size is large enough.
            if sizeRequirement > self.volumeSize() * 1000 * 1000 * 1000:
                details = u"Workflow requires %s and disk image is %d GB" % (sizeReqStr, self.volumeSize())
                self.delegate.buildFailed_details_(u"Disk image too small for workflow",
                                                   details)
                self.stop()
                return
        LogInfo(u"Using a %d GB disk image", self.volumeSize())
        
        # Task done.
        self.nextTask()
    
    
    
    # Task: Install.
    #
    #    1. Run the installesdtodmg.sh script with administrator privileges.
    #       Progress is sent back via notifications to the socket, which keeps
    #       the phases in sync with the script.
    
    def taskInstall(self):
        LogNotice(u"Install task running")
        
        # The script is wrapped with progresswatcher.py which parses script
        # output and sends it back as notifications to IEDSocketListener.
        try:
            groupName = grp.getgrgid(os.getgid()).gr_name
        except KeyError:
            groupName = unicode(os.getgid())
        args = [
            NSBundle.mainBundle().pathForResource_ofType_(u"progresswatcher", u"py"),
            u"--cd", NSBundle.mainBundle().resourcePath(),
            u"--socket", self.listenerPath,
            u"installesdtodmg",
            u"--user", NSUserName(),
            u"--group", groupName,
            u"--output", self.outputPath(),
            u"--volume-name", self.volumeName(),
            u"--size", unicode(self.volumeSize()),
            u"--template", self.templatePath,
        ]
        if self.sourceType == IEDWorkflow.SYSTEM_IMAGE:
            args.extend([u"--baseimage", self.source()])
        args.extend(self.packagesToInstall)
        LogInfo(u"Launching install with arguments:")
        for arg in args:
            LogInfo(u"    '%@'", arg)
        self.performSelectorInBackground_withObject_(self.launchScript_, args)
    
    def launchScript_(self, args):
        LogDebug(u"launchScript:")
        
        def escape(s):
            return s.replace(u"\\", u"\\\\").replace(u'"', u'\\"')
        
        # Generate an AppleScript snippet to launch a shell command with
        # administrator privileges.
        shellscript = u' & " " & '.join(u"quoted form of arg%d" % i for i in range(len(args)))
        scriptLines = list(u'set arg%d to "%s"' % (i, escape(arg)) for i, arg in enumerate(args))
        if self.authPassword() is not None:
            scriptLines.append(u'do shell script %s user name "%s" password "%s" '
                               u'with administrator privileges' % (shellscript,
                                                                   escape(self.authUsername()),
                                                                   escape(self.authPassword())))
        else:
            scriptLines.append(u'do shell script %s with administrator privileges' % shellscript)
        applescript = u"\n".join(scriptLines)
        trampoline = NSAppleScript.alloc().initWithSource_(applescript)
        evt, error = trampoline.executeAndReturnError_(None)
        if evt is None:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(self.handleLaunchScriptError_, error, False)
    
    def handleLaunchScriptError_(self, error):
        if error.get(NSAppleScriptErrorNumber) == -128:
            self.stop()
        else:
            self.fail_details_(u"Build failed", error.get(NSAppleScriptErrorMessage,
                                                          u"Unknown AppleScript error"))
    
    
    
    # Task: Finalize.
    #
    #    1. Scan the image for restore.
    
    def taskFinalize(self):
        LogNotice(u"Finalize task running")
        
        self.delegate.buildSetProgressMessage_(u"Scanning disk image for restore")
        # The script is wrapped with progresswatcher.py which parses script
        # output and sends it back as notifications to IEDSocketListener.
        args = [
            NSBundle.mainBundle().pathForResource_ofType_(u"progresswatcher", u"py"),
            u"--socket", self.listenerPath,
            u"imagescan",
            self.outputPath(),
        ]
        LogInfo(u"Launching finalize with arguments:")
        for arg in args:
            LogInfo(u"    '%@'", arg)
        subprocess.Popen(args)
    
    
    
    # Task: Finish
    #
    #    1. Just a dummy task to keep the progress bar from finishing
    #       prematurely.
    
    def taskFinish(self):
        LogNotice(u"Finish")
        self.delegate.buildSetProgress_(self.totalWeight)
        self.nextTask()
    
    # SocketListener delegate methods.
    
    def socketReceivedMessage_(self, msg):
        # The message is a dictionary with "action" as the only required key.
        action = msg[u"action"]
        
        if action == u"update_progress":
            percent = msg[u"percent"]
            currentProgress = self.progress + self.currentPhase[u"weight"] * percent / 100.0
            self.delegate.buildSetProgress_(currentProgress)
        
        elif action == u"update_message":
            if self.lastUpdateMessage != msg[u"message"]:
                # Only log update messages when they change.
                LogInfo(u"%@", msg[u"message"])
            self.lastUpdateMessage = msg[u"message"]
            self.delegate.buildSetProgressMessage_(msg[u"message"])
        
        elif action == u"select_phase":
            LogNotice(u"Script phase: %@", msg[u"phase"])
            self.nextPhase()
        
        elif action == u"log_message":
            LogMessage(msg[u"log_level"], msg[u"message"])
        
        elif action == u"notify_failure":
            self.fail_details_(u"Build failed", msg[u"message"])
        
        elif action == u"task_done":
            status = msg[u"termination_status"]
            if status == 0:
                self.nextTask()
            else:
                details = NSString.stringWithFormat_(u"Task exited with status %@", msg[u"termination_status"])
                LogError(u"%@", details)
                # Status codes 100-199 are from installesdtodmg.sh, and have
                # been preceeded by a "notify_failure" message.
                if (status < 100) or (status > 199):
                    self.fail_details_(u"Build failed", details)
        
        else:
            self.fail_details_(u"Unknown progress notification", u"Message: %@", msg)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#  main.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-09-19.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#

import os
import sys
import argparse
import traceback

import objc
import Foundation

objc.setVerbose(True)

from IEDLog import LogDebug, LogInfo, LogNotice, LogWarning, LogError, LogMessage
import IEDLog
from IEDUtil import *
import platform


def get_date_string():
    formatter = NSDateFormatter.alloc().init()
    formatter.setDateFormat_(u"yyyy-MM-dd")
    return formatter.stringFromDate_(NSDate.date())

def setup_log_dir():
    logDir = os.path.expanduser(u"~/Library/Logs/AutoDMG")
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    return logDir


def gui_unexpected_error_alert():
    exceptionInfo = traceback.format_exc()
    NSLog(u"AutoDMG died with an uncaught exception, %@", exceptionInfo)
    from AppKit import NSAlertSecondButtonReturn
    alert = NSAlert.alloc().init()
    alert.setMessageText_(u"AutoDMG died with an uncaught exception")
    alert.setInformativeText_(exceptionInfo)
    alert.addButtonWithTitle_(u"Quit")
    alert.addButtonWithTitle_(u"Save Log…")
    while alert.runModal() == NSAlertSecondButtonReturn:
        IEDLog.IEDLog.saveLog_(IEDLog.IEDLog, None)
    sys.exit(os.EX_SOFTWARE)

def gui_main():
    IEDLog.IEDLogToController  = True
    IEDLog.IEDLogToSyslog      = True
    IEDLog.IEDLogToStdOut      = True
    IEDLog.IEDLogStdOutLogLevel = IEDLog.IEDLogLevelDebug
    try:
        logFile = os.path.join(setup_log_dir(), u"AutoDMG-%s.log" % get_date_string())
        IEDLog.IEDLogFileHandle = open(logFile, u"a", buffering=1)
        IEDLog.IEDLogToFile = True
    except OSError as e:
        IEDLog.IEDLogToFile = False
        LogWarning(u"Couldn't open %s for writing" % (logFile)).encode(u"utf-8")
    
    import AppKit
    from PyObjCTools import AppHelper
    
    # import modules containing classes required to start application and load MainMenu.nib
    import IEDAppDelegate
    import IEDController
    import IEDSourceSelector
    import IEDAddPkgController
    import IEDAppVersionController
    
    # pass control to AppKit
    AppHelper.runEventLoop(unexpectedErrorAlert=gui_unexpected_error_alert)
    
    return os.EX_OK


def cli_main(argv):
    IEDLog.IEDLogToController  = False
    IEDLog.IEDLogToSyslog      = True
    IEDLog.IEDLogToStdOut      = True
    IEDLog.IEDLogToFile        = False
    
    from IEDCLIController import IEDCLIController
    clicontroller = IEDCLIController.alloc().init()
    
    try:
        # Initialize user defaults before application starts.
        defaults = NSUserDefaults.standardUserDefaults()
        defaultsPath = NSBundle.mainBundle().pathForResource_ofType_(u"Defaults", u"plist")
        defaultsDict = NSDictionary.dictionaryWithContentsOfFile_(defaultsPath)
        defaults.registerDefaults_(defaultsDict)
        
        p = argparse.ArgumentParser()
        p.add_argument(u"-v", u"--verbose", action=u"store_true", help=u"Verbose output")
        p.add_argument(u"-L", u"--log-level",
                       type=int, choices=range(0, 8), default=6,
                       metavar=u"LEVEL", help=u"Log level (0-7), default 6")
        p.add_argument(u"-l", u"--logfile", help=u"Log to file")
        p.add_argument(u"-r", u"--root", action=u"store_true", help=u"Allow running as root")
        sp = p.add_subparsers(title=u"subcommands", dest=u"subcommand")
        
        # Populate subparser for each verb.
        for verb in clicontroller.listVerbs():
            verb_method = getattr(clicontroller, u"cmd%s_" % verb.capitalize())
            addargs_method = getattr(clicontroller, u"addargs%s_" % verb.capitalize())
            parser = sp.add_parser(verb, help=verb_method.__doc__)
            addargs_method(parser)
            parser.set_defaults(func=verb_method)
        
        args = p.parse_args(argv)
        
        if args.verbose:
            IEDLog.IEDLogStdOutLogLevel = IEDLog.IEDLogLevelInfo
        else:
            IEDLog.IEDLogStdOutLogLevel = IEDLog.IEDLogLevelNotice
        
        IEDLog.IEDLogFileLogLevel = args.log_level
        
        if args.logfile == u"-":
            # Redirect log to stdout instead.
            IEDLog.IEDLogFileHandle = sys.stdout
            IEDLog.IEDLogToFile = True
            IEDLog.IEDLogToStdOut = False
        else:
            try:
                if args.logfile:
                    logFile = args.logfile
                else:
                    logFile = os.path.join(setup_log_dir(), u"AutoDMG-%s.log" % get_date_string())
                IEDLog.IEDLogFileHandle = open(logFile, u"a", buffering=1)
            except OSError as e:
                print >>sys.stderr, (u"Couldn't open %s for writing" % logFile).encode(u"utf-8")
                return os.EX_CANTCREAT
            IEDLog.IEDLogToFile = True
        
        # Check if we're running with root.
        if os.getuid() == 0:
            if args.root:
                fm = NSFileManager.defaultManager()
                url, error = fm.URLForDirectory_inDomain_appropriateForURL_create_error_(NSApplicationSupportDirectory,
                                                                                         NSUserDomainMask,
                                                                                         None,
                                                                                         False,
                                                                                         None)
                LogWarning(u"Running as root, using %@", os.path.join(url.path(), u"AutoDMG"))
            else:
                LogError(u"Running as root isn't recommended (use -r to override)")
                return os.EX_USAGE
        
        # Log version info on startup.
        version, build = IEDUtil.getAppVersion()
        LogInfo(u"AutoDMG v%@ build %@", version, build)
        name, version, build = IEDUtil.readSystemVersion_(u"/")
        LogInfo(u"%@ %@ %@", name, version, build)
        LogInfo(u"%@ %@ (%@)", platform.python_implementation(),
                               platform.python_version(),
                               platform.python_compiler())
        LogInfo(u"PyObjC %@", objc.__version__)
        
        return args.func(args)
    finally:
        clicontroller.cleanup()


def main():
    # Global exception handler to make sure we always log tracebacks.
    try:
        
        # Decode arguments as utf-8 and filter out arguments from Finder and
        # Xcode.
        decoded_argv = list()
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i].decode(u"utf-8")
            if arg.startswith(u"-psn"):
                pass
            elif arg == u"-NSDocumentRevisionsDebugMode":
                i += 1
            elif arg.startswith(u"-NS"):
                pass
            else:
                decoded_argv.append(arg)
            i += 1
        
        # If no arguments are supplied, assume the GUI should be started.
        if len(decoded_argv) == 0:
            return gui_main()
        # Otherwise parse the command line arguments.
        else:
            return cli_main(decoded_argv)
    
    except SystemExit as e:
        return e.code
    except Exception:
        NSLog(u"AutoDMG died with an uncaught exception, %@", traceback.format_exc())
        return os.EX_SOFTWARE


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = progresswatcher
#!/usr/bin/python

# -*- coding: utf-8 -*-
#
#  progresswatcher.py
#  AutoDMG
#
#  Created by Per Olofsson on 2013-09-26.
#  Copyright 2013-2014 Per Olofsson, University of Gothenburg. All rights reserved.
#


import os
import sys
import argparse
import socket
import re
import traceback
from Foundation import *


class ProgressWatcher(NSObject):
    
    re_installerlog = re.compile(r'^.+? installer\[[0-9a-f:]+\] (<(?P<level>[^>]+)>:)?(?P<message>.*)$')
    re_number = re.compile(r'^(\d+)')
    re_watchlog = re.compile(r'^.+? (?P<sender>install(d|_monitor))(\[\d+\]): (?P<message>.*)$')
    
    def watchTask_socket_mode_(self, args, sockPath, mode):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sockPath = sockPath
        
        nc = NSNotificationCenter.defaultCenter()
        
        self.isTaskRunning = True
        task = NSTask.alloc().init()
        
        outpipe = NSPipe.alloc().init()
        stdoutHandle = outpipe.fileHandleForReading()
        task.setStandardOutput_(outpipe)
        task.setStandardError_(outpipe)
        
        task.setLaunchPath_(args[0])
        task.setArguments_(args[1:])
        
        if mode == u"asr":
            progressHandler = u"notifyAsrProgressData:"
            self.asrProgressActive = False
            self.asrPhase = 0
        elif mode == u"ied":
            progressHandler = u"notifyIEDProgressData:"
            self.outputBuffer = u""
            self.watchLogHandle = None
            self.watchLogBuffer = u""
            self.lastSender = None
        
        nc.addObserver_selector_name_object_(self,
                                             progressHandler,
                                             NSFileHandleReadCompletionNotification,
                                             stdoutHandle)
        stdoutHandle.readInBackgroundAndNotify()
        
        nc.addObserver_selector_name_object_(self,
                                             u"notifyProgressTermination:",
                                             NSTaskDidTerminateNotification,
                                             task)
        task.launch()
    
    def shouldKeepRunning(self):
        return self.isTaskRunning
    
    def notifyProgressTermination_(self, notification):
        task = notification.object()
        if task.terminationStatus() == 0:
            pass
        self.postNotification_({u"action": u"task_done", u"termination_status": task.terminationStatus()})
        self.isTaskRunning = False
    
    def notifyAsrProgressData_(self, notification):
        data = notification.userInfo()[NSFileHandleNotificationDataItem]
        if data.length():
            progressStr = NSString.alloc().initWithData_encoding_(data, NSUTF8StringEncoding)
            if (not self.asrProgressActive) and (u"\x0a" in progressStr):
                progressStr = u"".join(progressStr.partition(u"\x0a")[1:])
            while progressStr:
                if progressStr.startswith(u"\x0a"):
                    progressStr = progressStr[1:]
                    self.asrProgressActive = False
                elif progressStr.startswith(u"Block checksum: "):
                    progressStr = progressStr[16:]
                    self.asrPercent = 0
                    self.asrProgressActive = True
                    self.asrPhase += 1
                    self.postNotification_({u"action": u"select_phase", u"phase": u"asr%d" % self.asrPhase})
                elif progressStr.startswith(u".") and self.asrProgressActive:
                    progressStr = progressStr[1:]
                    self.asrPercent += 2
                    self.postNotification_({u"action": u"update_progress", u"percent": float(self.asrPercent)})
                else:
                    m = self.re_number.match(progressStr)
                    if m and self.asrProgressActive:
                        progressStr = progressStr[len(m.group(0)):]
                        self.asrPercent = int(m.group(0))
                        self.postNotification_({u"action": u"update_progress", u"percent": float(self.asrPercent)})
                    else:
                        self.postNotification_({u"action": u"log_message", u"log_level": 6, u"message": u"asr output: " + progressStr.rstrip()})
                        break
            
            notification.object().readInBackgroundAndNotify()
    
    def notifyIEDProgressData_(self, notification):
        data = notification.userInfo()[NSFileHandleNotificationDataItem]
        if data.length():
            string = NSString.alloc().initWithData_encoding_(data, NSUTF8StringEncoding)
            if string:
                self.appendOutput_(string)
            else:
                NSLog(u"Couldn't decode %@ as UTF-8", data)
            notification.object().readInBackgroundAndNotify()
    
    def appendOutput_(self, string):
        self.outputBuffer += string
        while "\n" in self.outputBuffer:
            line, newline, self.outputBuffer = self.outputBuffer.partition("\n")
            self.parseProgress_(line)
    
    def parseProgress_(self, string):
        # Wrap progress parsing so app doesn't crash from bad input.
        try:
            if string.startswith(u"installer:"):
                self.parseInstallerProgress_(string[10:])
            elif string.startswith(u"IED:"):
                self.parseIEDProgress_(string[4:])
            elif string.startswith(u"MESSAGE:") or string.startswith(u"PERCENT:"):
                self.parseHdiutilProgress_(string)
            else:
                m = self.re_installerlog.match(string)
                if m:
                    level = m.group(u"level") if m.group(u"level") else u"stderr"
                    message = u"installer.%s: %s" % (level, m.group(u"message"))
                    self.postNotification_({u"action": u"log_message",
                                            u"log_level": 6,
                                            u"message": message})
                else:
                    self.postNotification_({u"action": u"log_message", u"log_level": 6, u"message": string})
        except BaseException as e:
            NSLog(u"Progress parsing failed: %s" % traceback.format_exc())
    
    def parseInstallerProgress_(self, string):
        if string.startswith(u"%"):
            progress = float(string[1:])
            self.postNotification_({u"action": u"update_progress", u"percent": progress})
        elif string.startswith(u"PHASE:"):
            message = string[6:]
            self.postNotification_({u"action": u"update_message", u"message": message})
        elif string.startswith(u"STATUS:"):
            self.postNotification_({u"action": u"log_message", u"log_level": 6, u"message": u"installer: " + string[7:]})
        else:
            self.postNotification_({u"action": u"log_message", u"log_level": 6, u"message": u"installer: " + string})
    
    def parseIEDProgress_(self, string):
        if string.startswith(u"MSG:"):
            message = string[4:]
            self.postNotification_({u"action": u"update_message", u"message": message})
        elif string.startswith(u"PHASE:"):
            phase = string[6:]
            self.postNotification_({u"action": u"select_phase", u"phase": phase})
        elif string.startswith(u"FAILURE:"):
            message = string[8:]
            self.postNotification_({u"action": u"notify_failure", u"message": message})
        elif string.startswith(u"WATCHLOG:"):
            self.watchLog_(string[9:])
        else:
            NSLog(u"(Unknown IED progress %@)", string)
    
    def parseHdiutilProgress_(self, string):
        if string.startswith(u"MESSAGE:"):
            message = string[8:]
            self.postNotification_({u"action": u"update_message", u"message": message})
        elif string.startswith(u"PERCENT:"):
            progress = float(string[8:])
            self.postNotification_({u"action": u"update_progress", u"percent": progress})
    
    def watchLog_(self, cmd):
        if cmd == u"START":
            self.watchLogHandle = NSFileHandle.fileHandleForReadingAtPath_(u"/var/log/install.log")
            self.watchLogHandle.seekToEndOfFile()
            nc = NSNotificationCenter.defaultCenter()
            nc.addObserver_selector_name_object_(self,
                                                 self.notifyWatchLogData_,
                                                 NSFileHandleReadCompletionNotification,
                                                 self.watchLogHandle)
            self.watchLogHandle.readInBackgroundAndNotify()
        elif cmd == u"STOP":
            if self.watchLogHandle:
                self.watchLogHandle.close()
            self.watchLogHandle = None
        else:
            NSLog(u"(Unknown watchLog command: %@)", repr(string))
    
    def notifyWatchLogData_(self, notification):
        data = notification.userInfo()[NSFileHandleNotificationDataItem]
        if data.length():
            string = NSString.alloc().initWithData_encoding_(data, NSUTF8StringEncoding)
            if string:
                self.appendWatchLog_(string)
            else:
                NSLog(u"Couldn't decode %@ as UTF-8", data)
            if self.watchLogHandle:
                self.watchLogHandle.readInBackgroundAndNotify()
        else:
            # No data means EOF, so we wait for a second before we try to read
            # again.
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(1.0,
                                                                                     self,
                                                                                     self.readAndNotify_,
                                                                                     self.watchLogHandle,
                                                                                     False)
    
    def readAndNotify_(self, timer):
        if self.watchLogHandle:
            self.watchLogHandle.readInBackgroundAndNotify()
    
    def appendWatchLog_(self, string):
        self.watchLogBuffer += string
        while "\n" in self.watchLogBuffer:
            line, newline, self.watchLogBuffer = self.watchLogBuffer.partition("\n")
            self.parseWatchLog_(line)
    
    def parseWatchLog_(self, string):
        # Multi-line messages start with a tab.
        if string.startswith(u"\t") and self.lastSender:
            message = u"%s: %s" % (self.lastSender, string[1:])
            self.postNotification_({u"action": u"log_message",
                                    u"log_level": 6,
                                    u"message": message})
        else:
            m = self.re_watchlog.match(string)
            if m:
                # Keep track of last sender for multi-line messages.
                self.lastSender = m.group(u"sender")
                message = u"%s: %s" % (m.group(u"sender"), m.group(u"message"))
                self.postNotification_({u"action": u"log_message",
                                        u"log_level": 6,
                                        u"message": message})
            else:
                self.lastSender = None
    
    def postNotification_(self, msgDict):
        msg, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(msgDict,
                                                                                            NSPropertyListBinaryFormat_v1_0,
                                                                                            0,
                                                                                            None)
        if not msg:
            if error:
                NSLog(u"plist encoding failed: %@", error)
            return
        if self.sockPath:
            try:
                self.sock.sendto(msg, self.sockPath)
            except socket.error, e:
                NSLog(u"Socket at %@ failed: %@", self.sockPath, unicode(e))
        else:
            NSLog(u"postNotification:%@", msgDict)
    

def run(args, sockPath, mode):
    pw = ProgressWatcher.alloc().init()
    pw.watchTask_socket_mode_(args, sockPath, mode)
    runLoop = NSRunLoop.currentRunLoop()
    while pw.shouldKeepRunning():
        runLoop.runMode_beforeDate_(NSDefaultRunLoopMode, NSDate.distantFuture())


def installesdtodmg(args):
    if args.cd:
        os.chdir(args.cd)
    if args.baseimage:
        baseimage = [args.baseimage]
    else:
        baseimage = []
    pwargs = [u"./installesdtodmg.sh",
              args.user,
              args.group,
              args.output,
              args.volume_name,
              args.size,
              args.template] + baseimage + args.packages
    run(pwargs, args.socket, u"ied")


def imagescan(args):
    if args.cd:
        os.chdir(args.cd)
    pwargs = [u"/usr/sbin/asr", u"imagescan", u"--source", args.image]
    run(pwargs, args.socket, u"asr")


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument(u"-d", u"--cd", help=u"Set current directory")
    p.add_argument(u"-s", u"--socket", help=u"Communications socket")
    sp = p.add_subparsers(title=u"subcommands", dest=u"subcommand")
    
    iedparser = sp.add_parser(u"installesdtodmg", help=u"Perform installation to DMG")
    iedparser.add_argument(u"-u", u"--user", help=u"Change owner of DMG", required=True)
    iedparser.add_argument(u"-g", u"--group", help=u"Change group of DMG", required=True)
    iedparser.add_argument(u"-o", u"--output", help=u"Set output path", required=True)
    iedparser.add_argument(u"-t", u"--template", help=u"Path to adtmpl", required=True)
    iedparser.add_argument(u"-n", u"--volume-name", default=u"Macintosh HD", help=u"Set installed system's volume name.")
    iedparser.add_argument(u"-s", u"--size", default=u"32", help=u"Disk image size in GB.")
    iedparser.add_argument(u"-b", u"--baseimage", default=None, help=u"Base system image for shadow mount.")
    iedparser.add_argument(u"packages", help=u"Packages to install", nargs=u"+")
    iedparser.set_defaults(func=installesdtodmg)
    
    asrparser = sp.add_parser(u"imagescan", help=u"Perform asr imagescan of dmg")
    asrparser.add_argument(u"image", help=u"DMG to scan")
    asrparser.set_defaults(func=imagescan)
    
    args = p.parse_args([x.decode(u"utf-8") for x in argv[1:]])
    args.func(args)
    
    return 0
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
