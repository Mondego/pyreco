__FILENAME__ = accounts
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from offlineimap import threadutil, mbnames, CustomConfig
import offlineimap.repository.Base, offlineimap.repository.LocalStatus
from offlineimap.ui import UIBase
from offlineimap.threadutil import InstanceLimitedThread, ExitNotifyThread
from subprocess import Popen, PIPE
from threading import Event, Lock
import os
from Queue import Queue, Empty
import sys

class SigListener(Queue):
    def __init__(self):
        self.folderlock = Lock()
        self.folders = None
        Queue.__init__(self, 20)
    def put_nowait(self, sig):
        self.folderlock.acquire()
        try:
            if sig == 1:
                if self.folders is None or not self.autorefreshes:
                    # folders haven't yet been added, or this account is once-only; drop signal
                    return
                elif self.folders:
                    for foldernr in range(len(self.folders)):
                        # requeue folder
                        self.folders[foldernr][1] = True
                    self.quick = False
                    return
                # else folders have already been cleared, put signal...
        finally:
            self.folderlock.release()
        Queue.put_nowait(self, sig)
    def addfolders(self, remotefolders, autorefreshes, quick):
        self.folderlock.acquire()
        try:
            self.folders = []
            self.quick = quick
            self.autorefreshes = autorefreshes
            for folder in remotefolders:
                # new folders are queued
                self.folders.append([folder, True])
        finally:
            self.folderlock.release()
    def clearfolders(self):
        self.folderlock.acquire()
        try:
            for folder, queued in self.folders:
                if queued:
                    # some folders still in queue
                    return False
            self.folders[:] = []
            return True
        finally:
            self.folderlock.release()
    def queuedfolders(self):
        self.folderlock.acquire()
        try:
            dirty = True
            while dirty:
                dirty = False
                for foldernr, (folder, queued) in enumerate(self.folders):
                    if queued:
                        # mark folder as no longer queued
                        self.folders[foldernr][1] = False
                        dirty = True
                        quick = self.quick
                        self.folderlock.release()
                        yield (folder, quick)
                        self.folderlock.acquire()
        finally:
            self.folderlock.release()

def getaccountlist(customconfig):
    return customconfig.getsectionlist('Account')

def AccountListGenerator(customconfig):
    return [Account(customconfig, accountname)
            for accountname in getaccountlist(customconfig)]

def AccountHashGenerator(customconfig):
    retval = {}
    for item in AccountListGenerator(customconfig):
        retval[item.getname()] = item
    return retval

mailboxes = []

class Account(CustomConfig.ConfigHelperMixin):
    def __init__(self, config, name):
        self.config = config
        self.name = name
        self.metadatadir = config.getmetadatadir()
        self.localeval = config.getlocaleval()
        self.ui = UIBase.getglobalui()
        self.refreshperiod = self.getconffloat('autorefresh', 0.0)
        self.quicknum = 0
        if self.refreshperiod == 0.0:
            self.refreshperiod = None

    def getlocaleval(self):
        return self.localeval

    def getconfig(self):
        return self.config

    def getname(self):
        return self.name

    def getsection(self):
        return 'Account ' + self.getname()

    def sleeper(self, siglistener):
        """Sleep handler.  Returns same value as UIBase.sleep:
        0 if timeout expired, 1 if there was a request to cancel the timer,
        and 2 if there is a request to abort the program.

        Also, returns 100 if configured to not sleep at all."""
        
        if not self.refreshperiod:
            return 100

        kaobjs = []

        if hasattr(self, 'localrepos'):
            kaobjs.append(self.localrepos)
        if hasattr(self, 'remoterepos'):
            kaobjs.append(self.remoterepos)

        for item in kaobjs:
            item.startkeepalive()
        
        refreshperiod = int(self.refreshperiod * 60)
#         try:
#             sleepresult = siglistener.get_nowait()
#             # retrieved signal before sleep started
#             if sleepresult == 1:
#                 # catching signal 1 here means folders were cleared before signal was posted
#                 pass
#         except Empty:
#             sleepresult = self.ui.sleep(refreshperiod, siglistener)
        sleepresult = self.ui.sleep(refreshperiod, siglistener)
        if sleepresult == 1:
            self.quicknum = 0

        # Cancel keepalive
        for item in kaobjs:
            item.stopkeepalive()
        return sleepresult
            
class AccountSynchronizationMixin:
    def syncrunner(self, siglistener):
        self.ui.registerthread(self.name)
        self.ui.acct(self.name)
        accountmetadata = self.getaccountmeta()
        if not os.path.exists(accountmetadata):
            os.mkdir(accountmetadata, 0700)            

        self.remoterepos = offlineimap.repository.Base.LoadRepository(self.getconf('remoterepository'), self, 'remote')

        # Connect to the local repository.
        self.localrepos = offlineimap.repository.Base.LoadRepository(self.getconf('localrepository'), self, 'local')

        # Connect to the local cache.
        self.statusrepos = offlineimap.repository.LocalStatus.LocalStatusRepository(self.getconf('localrepository'), self)

        #might need changes here to ensure that one account sync does not crash others...
        if not self.refreshperiod:
            try:
                self.sync(siglistener)
            except:
                self.ui.warn("Error occured attempting to sync account " + self.name \
                    + ": " + str(sys.exc_info()[1]))
            finally:
                self.ui.acctdone(self.name)

            return


        looping = 1
        while looping:
            try:
                self.sync(siglistener)
            except:
                self.ui.warn("Error occured attempting to sync account " + self.name \
                    + ": " + str(sys.exc_info()[1]))
            finally:
                looping = self.sleeper(siglistener) != 2
                self.ui.acctdone(self.name)


    def getaccountmeta(self):
        return os.path.join(self.metadatadir, 'Account-' + self.name)

    def sync(self, siglistener):
        # We don't need an account lock because syncitall() goes through
        # each account once, then waits for all to finish.

        hook = self.getconf('presynchook', '')
        self.callhook(hook)

        quickconfig = self.getconfint('quick', 0)
        if quickconfig < 0:
            quick = True
        elif quickconfig > 0:
            if self.quicknum == 0 or self.quicknum > quickconfig:
                self.quicknum = 1
                quick = False
            else:
                self.quicknum = self.quicknum + 1
                quick = True
        else:
            quick = False

        try:
            remoterepos = self.remoterepos
            localrepos = self.localrepos
            statusrepos = self.statusrepos
            self.ui.syncfolders(remoterepos, localrepos)
            remoterepos.syncfoldersto(localrepos, [statusrepos])

            siglistener.addfolders(remoterepos.getfolders(), bool(self.refreshperiod), quick)

            while True:
                folderthreads = []
                for remotefolder, quick in siglistener.queuedfolders():
                    thread = InstanceLimitedThread(\
                        instancename = 'FOLDER_' + self.remoterepos.getname(),
                        target = syncfolder,
                        name = "Folder sync %s[%s]" % \
                        (self.name, remotefolder.getvisiblename()),
                        args = (self.name, remoterepos, remotefolder, localrepos,
                                statusrepos, quick))
                    thread.setDaemon(1)
                    thread.start()
                    folderthreads.append(thread)
                threadutil.threadsreset(folderthreads)
                if siglistener.clearfolders():
                    break
            mbnames.write()
            localrepos.forgetfolders()
            remoterepos.forgetfolders()
            localrepos.holdordropconnections()
            remoterepos.holdordropconnections()
        finally:
            pass

        hook = self.getconf('postsynchook', '')
        self.callhook(hook)

    def callhook(self, cmd):
        if not cmd:
            return
        try:
            self.ui.callhook("Calling hook: " + cmd)
            p = Popen(cmd, shell=True,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE,
                      close_fds=True)
            r = p.communicate()
            self.ui.callhook("Hook stdout: %s\nHook stderr:%s\n" % r)
            self.ui.callhook("Hook return code: %d" % p.returncode)
        except:
            self.ui.warn("Exception occured while calling hook")
    
class SyncableAccount(Account, AccountSynchronizationMixin):
    pass

def syncfolder(accountname, remoterepos, remotefolder, localrepos,
               statusrepos, quick):
    global mailboxes
    ui = UIBase.getglobalui()
    ui.registerthread(accountname)
    try:
        # Load local folder.
        localfolder = localrepos.\
                      getfolder(remotefolder.getvisiblename().\
                                replace(remoterepos.getsep(), localrepos.getsep()))
        # Write the mailboxes
        mbnames.add(accountname, localfolder.getvisiblename())

        # Load status folder.
        statusfolder = statusrepos.getfolder(remotefolder.getvisiblename().\
                                             replace(remoterepos.getsep(),
                                                     statusrepos.getsep()))
        if localfolder.getuidvalidity() == None:
            # This is a new folder, so delete the status cache to be sure
            # we don't have a conflict.
            statusfolder.deletemessagelist()

        statusfolder.cachemessagelist()

        if quick:
            if not localfolder.quickchanged(statusfolder) \
                   and not remotefolder.quickchanged(statusfolder):
                ui.skippingfolder(remotefolder)
                localrepos.restore_atime()
                return

        # Load local folder
        ui.syncingfolder(remoterepos, remotefolder, localrepos, localfolder)
        ui.loadmessagelist(localrepos, localfolder)
        localfolder.cachemessagelist()
        ui.messagelistloaded(localrepos, localfolder, len(localfolder.getmessagelist().keys()))

        # If either the local or the status folder has messages and there is a UID
        # validity problem, warn and abort.  If there are no messages, UW IMAPd
        # loses UIDVALIDITY.  But we don't really need it if both local folders are
        # empty.  So, in that case, just save it off.
        if len(localfolder.getmessagelist()) or len(statusfolder.getmessagelist()):
            if not localfolder.isuidvalidityok():
                ui.validityproblem(localfolder)
                localrepos.restore_atime()
                return
            if not remotefolder.isuidvalidityok():
                ui.validityproblem(remotefolder)
                localrepos.restore_atime()
                return
        else:
            localfolder.saveuidvalidity()
            remotefolder.saveuidvalidity()

        # Load remote folder.
        ui.loadmessagelist(remoterepos, remotefolder)
        remotefolder.cachemessagelist()
        ui.messagelistloaded(remoterepos, remotefolder,
                             len(remotefolder.getmessagelist().keys()))


        #

        if not statusfolder.isnewfolder():
            # Delete local copies of remote messages.  This way,
            # if a message's flag is modified locally but it has been
            # deleted remotely, we'll delete it locally.  Otherwise, we
            # try to modify a deleted message's flags!  This step
            # need only be taken if a statusfolder is present; otherwise,
            # there is no action taken *to* the remote repository.

            remotefolder.syncmessagesto_delete(localfolder, [localfolder,
                                                             statusfolder])
            ui.syncingmessages(localrepos, localfolder, remoterepos, remotefolder)
            localfolder.syncmessagesto(statusfolder, [remotefolder, statusfolder])

        # Synchronize remote changes.
        ui.syncingmessages(remoterepos, remotefolder, localrepos, localfolder)
        remotefolder.syncmessagesto(localfolder, [localfolder, statusfolder])

        # Make sure the status folder is up-to-date.
        ui.syncingmessages(localrepos, localfolder, statusrepos, statusfolder)
        localfolder.syncmessagesto(statusfolder)
        statusfolder.save()
        localrepos.restore_atime()
    except:
        ui.warn("ERROR in syncfolder for " + accountname + " folder  " + \
        remotefolder.getvisiblename() +" : " +str(sys.exc_info()[1]))

########NEW FILE########
__FILENAME__ = CustomConfig
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from ConfigParser import ConfigParser
from offlineimap.localeval import LocalEval
import os

class CustomConfigParser(ConfigParser):
    def getdefault(self, section, option, default, *args, **kwargs):
        """Same as config.get, but returns the "default" option if there
        is no such option specified."""
        if self.has_option(section, option):
            return apply(self.get, [section, option] + list(args), kwargs)
        else:
            return default
    
    def getdefaultint(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getint, [section, option] + list(args), kwargs)
        else:
            return default

    def getdefaultfloat(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getfloat, [section, option] + list(args), kwargs)
        else:
            return default

    def getdefaultboolean(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getboolean, [section, option] + list(args),
                         kwargs)
        else:
            return default

    def getmetadatadir(self):
        metadatadir = os.path.expanduser(self.getdefault("general", "metadata", "~/.offlineimap"))
        if not os.path.exists(metadatadir):
            os.mkdir(metadatadir, 0700)
        return metadatadir

    def getlocaleval(self):
        if self.has_option("general", "pythonfile"):
            path = os.path.expanduser(self.get("general", "pythonfile"))
        else:
            path = None
        return LocalEval(path)

    def getsectionlist(self, key):
        """Returns a list of sections that start with key + " ".  That is,
        if key is "Account", returns all section names that start with
        "Account ", but strips off the "Account ".  For instance, for
        "Account Test", returns "Test"."""

        key = key + ' '
        return [x[len(key):] for x in self.sections() \
                if x.startswith(key)]

def CustomConfigDefault():
    """Just a sample constant that won't occur anywhere else to use for the
    default."""
    pass

class ConfigHelperMixin:
    def _confighelper_runner(self, option, default, defaultfunc, mainfunc):
        if default != CustomConfigDefault:
            return apply(defaultfunc, [self.getsection(), option, default])
        else:
            return apply(mainfunc, [self.getsection(), option])

    def getconf(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefault,
                                         self.getconfig().get)

    def getconfboolean(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultboolean,
                                         self.getconfig().getboolean)

    def getconfint(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultint,
                                         self.getconfig().getint)
    
    def getconffloat(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultfloat,
                                         self.getconfig().getfloat)
    

########NEW FILE########
__FILENAME__ = Base
# Base folder support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
from offlineimap import threadutil
from offlineimap.threadutil import InstanceLimitedThread
from offlineimap.ui import UIBase
import os.path, re
import sys

class BaseFolder:
    def __init__(self):
        self.uidlock = Lock()
        
    def getname(self):
        """Returns name"""
        return self.name

    def suggeststhreads(self):
        """Returns true if this folder suggests using threads for actions;
        false otherwise.  Probably only IMAP will return true."""
        return 0

    def waitforthread(self):
        """For threading folders, waits until there is a resource available
        before firing off a thread.  For all others, returns immediately."""
        pass

    def getcopyinstancelimit(self):
        """For threading folders, returns the instancelimitname for
        InstanceLimitedThreads."""
        raise NotImplementedException

    def storesmessages(self):
        """Should be true for any backend that actually saves message bodies.
        (Almost all of them).  False for the LocalStatus backend.  Saves
        us from having to slurp up messages just for localstatus purposes."""
        return 1

    def getvisiblename(self):
        return self.name

    def getrepository(self):
        """Returns the repository object that this folder is within."""
        return self.repository

    def getroot(self):
        """Returns the root of the folder, in a folder-specific fashion."""
        return self.root

    def getsep(self):
        """Returns the separator for this folder type."""
        return self.sep

    def getfullname(self):
        if self.getroot():
            return self.getroot() + self.getsep() + self.getname()
        else:
            return self.getname()
    
    def getfolderbasename(self):
        foldername = self.getname()
        foldername = foldername.replace(self.repository.getsep(), '.')
        foldername = re.sub('/\.$', '/dot', foldername)
        foldername = re.sub('^\.$', 'dot', foldername)
        return foldername

    def isuidvalidityok(self):
        if self.getsaveduidvalidity() != None:
            return self.getsaveduidvalidity() == self.getuidvalidity()
        else:
            self.saveuidvalidity()
            return 1

    def _getuidfilename(self):
        return os.path.join(self.repository.getuiddir(),
                            self.getfolderbasename())
            
    def getsaveduidvalidity(self):
        if hasattr(self, '_base_saved_uidvalidity'):
            return self._base_saved_uidvalidity
        uidfilename = self._getuidfilename()
        if not os.path.exists(uidfilename):
            self._base_saved_uidvalidity = None
        else:
            file = open(uidfilename, "rt")
            self._base_saved_uidvalidity = long(file.readline().strip())
            file.close()
        return self._base_saved_uidvalidity

    def saveuidvalidity(self):
        newval = self.getuidvalidity()
        uidfilename = self._getuidfilename()
        self.uidlock.acquire()
        try:
            file = open(uidfilename + ".tmp", "wt")
            file.write("%d\n" % newval)
            file.close()
            os.rename(uidfilename + ".tmp", uidfilename)
            self._base_saved_uidvalidity = newval
        finally:
            self.uidlock.release()

    def getuidvalidity(self):
        raise NotImplementedException

    def cachemessagelist(self):
        """Reads the message list from disk or network and stores it in
        memory for later use.  This list will not be re-read from disk or
        memory unless this function is called again."""
        raise NotImplementedException

    def getmessagelist(self):
        """Gets the current message list.
        You must call cachemessagelist() before calling this function!"""
        raise NotImplementedException

    def getmessage(self, uid):
        """Returns the content of the specified message."""
        raise NotImplementedException

    def savemessage(self, uid, content, flags, rtime):
        """Writes a new message, with the specified uid.
        If the uid is < 0, the backend should assign a new uid and return it.

        If the backend cannot assign a new uid, it returns the uid passed in
        WITHOUT saving the message.

        If the backend CAN assign a new uid, but cannot find out what this UID
        is (as is the case with many IMAP servers), it returns 0 but DOES save
        the message.
        
        IMAP backend should be the only one that can assign a new uid.

        If the uid is > 0, the backend should set the uid to this, if it can.
        If it cannot set the uid to that, it will save it anyway.
        It will return the uid assigned in any case.
        """
        raise NotImplementedException

    def getmessagetime(self, uid):
        """Return the received time for the specified message."""
        raise NotImplementedException

    def getmessageflags(self, uid):
        """Returns the flags for the specified message."""
        raise NotImplementedException

    def savemessageflags(self, uid, flags):
        """Sets the specified message's flags to the given set."""
        raise NotImplementedException

    def addmessageflags(self, uid, flags):
        """Adds the specified flags to the message's flag set.  If a given
        flag is already present, it will not be duplicated."""
        newflags = self.getmessageflags(uid)
        for flag in flags:
            if not flag in newflags:
                newflags.append(flag)
        newflags.sort()
        self.savemessageflags(uid, newflags)

    def addmessagesflags(self, uidlist, flags):
        for uid in uidlist:
            self.addmessageflags(uid, flags)

    def deletemessageflags(self, uid, flags):
        """Removes each flag given from the message's flag set.  If a given
        flag is already removed, no action will be taken for that flag."""
        newflags = self.getmessageflags(uid)
        for flag in flags:
            if flag in newflags:
                newflags.remove(flag)
        newflags.sort()
        self.savemessageflags(uid, newflags)

    def deletemessagesflags(self, uidlist, flags):
        for uid in uidlist:
            self.deletemessageflags(uid, flags)

    def deletemessage(self, uid):
        raise NotImplementedException

    def deletemessages(self, uidlist):
        for uid in uidlist:
            self.deletemessage(uid)

    def syncmessagesto_neguid_msg(self, uid, dest, applyto, register = 1):
        if register:
            UIBase.getglobalui().registerthread(self.getaccountname())
        UIBase.getglobalui().copyingmessage(uid, self, applyto)
        successobject = None
        successuid = None
        message = self.getmessage(uid)
        flags = self.getmessageflags(uid)
        rtime = self.getmessagetime(uid)
        for tryappend in applyto:
            successuid = tryappend.savemessage(uid, message, flags, rtime)
            if successuid >= 0:
                successobject = tryappend
                break
        # Did we succeed?
        if successobject != None:
            if successuid:       # Only if IMAP actually assigned a UID
                # Copy the message to the other remote servers.
                for appendserver in \
                        [x for x in applyto if x != successobject]:
                    appendserver.savemessage(successuid, message, flags, rtime)
                    # Copy to its new name on the local server and delete
                    # the one without a UID.
                    self.savemessage(successuid, message, flags, rtime)
            self.deletemessage(uid) # It'll be re-downloaded.
        else:
            # Did not find any server to take this message.  Ignore.
            pass
        

    def syncmessagesto_neguid(self, dest, applyto):
        """Pass 1 of folder synchronization.

        Look for messages in self with a negative uid.  These are messages in
        Maildirs that were not added by us.  Try to add them to the dests,
        and once that succeeds, get the UID, add it to the others for real,
        add it to local for real, and delete the fake one."""

        uidlist = [uid for uid in self.getmessagelist().keys() if uid < 0]
        threads = []

        usethread = None
        if applyto != None:
            usethread = applyto[0]
        
        for uid in uidlist:
            if usethread and usethread.suggeststhreads():
                usethread.waitforthread()
                thread = InstanceLimitedThread(\
                    usethread.getcopyinstancelimit(),
                    target = self.syncmessagesto_neguid_msg,
                    name = "New msg sync from %s" % self.getvisiblename(),
                    args = (uid, dest, applyto))
                thread.setDaemon(1)
                thread.start()
                threads.append(thread)
            else:
                self.syncmessagesto_neguid_msg(uid, dest, applyto, register = 0)
        for thread in threads:
            thread.join()

    def copymessageto(self, uid, applyto, register = 1):
        # Sometimes, it could be the case that if a sync takes awhile,
        # a message might be deleted from the maildir before it can be
        # synced to the status cache.  This is only a problem with
        # self.getmessage().  So, don't call self.getmessage unless
        # really needed.
        try:
            if register:
                UIBase.getglobalui().registerthread(self.getaccountname())
            UIBase.getglobalui().copyingmessage(uid, self, applyto)
            message = ''
            # If any of the destinations actually stores the message body,
            # load it up.
            
            for object in applyto:
                if object.storesmessages():
                    message = self.getmessage(uid)
                    break
            flags = self.getmessageflags(uid)
            rtime = self.getmessagetime(uid)
            for object in applyto:
                newuid = object.savemessage(uid, message, flags, rtime)
                if newuid > 0 and newuid != uid:
                    # Change the local uid.
                    self.savemessage(newuid, message, flags, rtime)
                    self.deletemessage(uid)
                    uid = newuid
        except:
            UIBase.getglobalui().warn("ERROR attempting to copy message " + str(uid) \
                 + " for account " + self.getaccountname() + ":" + str(sys.exc_info()[1]))
        

    def syncmessagesto_copy(self, dest, applyto):
        """Pass 2 of folder synchronization.

        Look for messages present in self but not in dest.  If any, add
        them to dest."""
        threads = []
        
	dest_messagelist = dest.getmessagelist()
        for uid in self.getmessagelist().keys():
            if uid < 0:                 # Ignore messages that pass 1 missed.
                continue
            if not uid in dest_messagelist:
                if self.suggeststhreads():
                    self.waitforthread()
                    thread = InstanceLimitedThread(\
                        self.getcopyinstancelimit(),
                        target = self.copymessageto,
                        name = "Copy message %d from %s" % (uid,
                                                            self.getvisiblename()),
                        args = (uid, applyto))
                    thread.setDaemon(1)
                    thread.start()
                    threads.append(thread)
                else:
                    self.copymessageto(uid, applyto, register = 0)
        for thread in threads:
            thread.join()

    def syncmessagesto_delete(self, dest, applyto):
        """Pass 3 of folder synchronization.

        Look for message present in dest but not in self.
        If any, delete them."""
        deletelist = []
	self_messagelist = self.getmessagelist()
        for uid in dest.getmessagelist().keys():
            if uid < 0:
                continue
            if not uid in self_messagelist:
                deletelist.append(uid)
        if len(deletelist):
            UIBase.getglobalui().deletingmessages(deletelist, applyto)
            for object in applyto:
                object.deletemessages(deletelist)

    def syncmessagesto_flags(self, dest, applyto):
        """Pass 4 of folder synchronization.

        Look for any flag matching issues -- set dest message to have the
        same flags that we have."""

        # As an optimization over previous versions, we store up which flags
        # are being used for an add or a delete.  For each flag, we store
        # a list of uids to which it should be added.  Then, we can call
        # addmessagesflags() to apply them in bulk, rather than one
        # call per message as before.  This should result in some significant
        # performance improvements.

        addflaglist = {}
        delflaglist = {}
        
        for uid in self.getmessagelist().keys():
            if uid < 0:                 # Ignore messages missed by pass 1
                continue
            selfflags = self.getmessageflags(uid)
            destflags = dest.getmessageflags(uid)

            addflags = [x for x in selfflags if x not in destflags]

            for flag in addflags:
                if not flag in addflaglist:
                    addflaglist[flag] = []
                addflaglist[flag].append(uid)

            delflags = [x for x in destflags if x not in selfflags]
            for flag in delflags:
                if not flag in delflaglist:
                    delflaglist[flag] = []
                delflaglist[flag].append(uid)

        for object in applyto:
            for flag in addflaglist.keys():
                UIBase.getglobalui().addingflags(addflaglist[flag], flag, [object])
                object.addmessagesflags(addflaglist[flag], [flag])
            for flag in delflaglist.keys():
                UIBase.getglobalui().deletingflags(delflaglist[flag], flag, [object])
                object.deletemessagesflags(delflaglist[flag], [flag])
                
    def syncmessagesto(self, dest, applyto = None):
        """Syncs messages in this folder to the destination.
        If applyto is specified, it should be a list of folders (don't forget
        to include dest!) to which all write actions should be applied.
        It defaults to [dest] if not specified.  It is important that
        the UID generator be listed first in applyto; that is, the other
        applyto ones should be the ones that "copy" the main action."""
        if applyto == None:
            applyto = [dest]

        try:
            self.syncmessagesto_neguid(dest, applyto)
        except:
            UIBase.getglobalui().warn("ERROR attempting to handle negative uids " \
                + "for account " + self.getaccountname() + ":" + str(sys.exc_info()[1]))

        #all threads launched here are in try / except clauses when they copy anyway...
        self.syncmessagesto_copy(dest, applyto)

        try:
            self.syncmessagesto_delete(dest, applyto)
        except:
            UIBase.getglobalui().warn("ERROR attempting to delete messages " \
                + "for account " + self.getaccountname() + ":" + str(sys.exc_info()[1]))

        # Now, the message lists should be identical wrt the uids present.
        # (except for potential negative uids that couldn't be placed
        # anywhere)

        try:
            self.syncmessagesto_flags(dest, applyto)
        except:
            UIBase.getglobalui().warn("ERROR attempting to sync flags " \
                + "for account " + self.getaccountname() + ":" + str(sys.exc_info()[1]))
        
            

########NEW FILE########
__FILENAME__ = Gmail
# Gmail IMAP folder support
# Copyright (C) 2008 Riccardo Murri <riccardo.murri@gmail.com>
# Copyright (C) 2002-2007 John Goerzen <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""Folder implementation to support features of the Gmail IMAP server.
"""

from IMAP import IMAPFolder
import imaplib
from offlineimap import imaputil, imaplibutil
from offlineimap.ui import UIBase
from copy import copy


class GmailFolder(IMAPFolder):
    """Folder implementation to support features of the Gmail IMAP server.
    Specifically, deleted messages are moved to folder `Gmail.TRASH_FOLDER`
    (by default: ``[Gmail]/Trash``) prior to expunging them, since
    Gmail maps to IMAP ``EXPUNGE`` command to "remove label".

    For more information on the Gmail IMAP server:
      http://mail.google.com/support/bin/answer.py?answer=77657&topic=12815
    """

    def __init__(self, imapserver, name, visiblename, accountname, repository):
        self.realdelete = repository.getrealdelete(name)
        self.trash_folder = repository.gettrashfolder(name)
        #: Gmail will really delete messages upon EXPUNGE in these folders
        self.real_delete_folders =  [ self.trash_folder, repository.getspamfolder() ]
        IMAPFolder.__init__(self, imapserver, name, visiblename, \
                            accountname, repository)

    def deletemessages_noconvert(self, uidlist):
        uidlist = [uid for uid in uidlist if uid in self.messagelist]
        if not len(uidlist):
            return        

        if self.realdelete and not (self.getname() in self.real_delete_folders):
            # IMAP expunge is just "remove label" in this folder,
            # so map the request into a "move into Trash"

            imapobj = self.imapserver.acquireconnection()
            try:
                imapobj.select(self.getfullname())
                result = imapobj.uid('copy',
                                     imaputil.listjoin(uidlist),
                                     self.trash_folder)
                assert result[0] == 'OK', \
                       "Bad IMAPlib result: %s" % result[0]
            finally:
                self.imapserver.releaseconnection(imapobj)
            for uid in uidlist:
                del self.messagelist[uid]
        else:
            IMAPFolder.deletemessages_noconvert(self, uidlist)
            
    def processmessagesflags(self, operation, uidlist, flags):
        # XXX: the imapobj.myrights(...) calls dies with an error
        # report from Gmail server stating that IMAP command
        # 'MYRIGHTS' is not implemented.  So, this
        # `processmessagesflags` is just a copy from `IMAPFolder`,
        # with the references to `imapobj.myrights()` deleted This
        # shouldn't hurt, however, Gmail users always have full
        # control over all their mailboxes (apparently).
        if len(uidlist) > 101:
            # Hack for those IMAP ervers with a limited line length
            self.processmessagesflags(operation, uidlist[:100], flags)
            self.processmessagesflags(operation, uidlist[100:], flags)
            return
        
        imapobj = self.imapserver.acquireconnection()
        try:
            imapobj.select(self.getfullname())
            r = imapobj.uid('store',
                            imaputil.listjoin(uidlist),
                            operation + 'FLAGS',
                            imaputil.flagsmaildir2imap(flags))
            assert r[0] == 'OK', 'Error with store: ' + '. '.join(r[1])
            r = r[1]
        finally:
            self.imapserver.releaseconnection(imapobj)

        needupdate = copy(uidlist)
        for result in r:
            if result == None:
                # Compensate for servers that don't return anything from
                # STORE.
                continue
            attributehash = imaputil.flags2hash(imaputil.imapsplit(result)[1])
            if not ('UID' in attributehash and 'FLAGS' in attributehash):
                # Compensate for servers that don't return a UID attribute.
                continue
            flags = attributehash['FLAGS']
            uid = long(attributehash['UID'])
            self.messagelist[uid]['flags'] = imaputil.flagsimap2maildir(flags)
            try:
                needupdate.remove(uid)
            except ValueError:          # Let it slide if it's not in the list
                pass
        for uid in needupdate:
            if operation == '+':
                for flag in flags:
                    if not flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].append(flag)
                    self.messagelist[uid]['flags'].sort()
            elif operation == '-':
                for flag in flags:
                    if flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].remove(flag)

########NEW FILE########
__FILENAME__ = IMAP
# IMAP folder support
# Copyright (C) 2002-2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Base import BaseFolder
import imaplib
from offlineimap import imaputil, imaplibutil
from offlineimap.ui import UIBase
from offlineimap.version import versionstr
import rfc822, time, string, random, binascii, re
from StringIO import StringIO
from copy import copy
import time


class IMAPFolder(BaseFolder):
    def __init__(self, imapserver, name, visiblename, accountname, repository):
        self.config = imapserver.config
        self.expunge = repository.getexpunge()
        self.name = imaputil.dequote(name)
        self.root = None # imapserver.root
        self.sep = imapserver.delim
        self.imapserver = imapserver
        self.messagelist = None
        self.visiblename = visiblename
        self.accountname = accountname
        self.repository = repository
        self.randomgenerator = random.Random()
        BaseFolder.__init__(self)

    def selectro(self, imapobj):
        """Select this folder when we do not need write access.
        Prefer SELECT to EXAMINE if we can, since some servers
        (Courier) do not stabilize UID validity until the folder is
        selected."""
        try:
            imapobj.select(self.getfullname())
        except imapobj.readonly:
            imapobj.select(self.getfullname(), readonly = 1)

    def getaccountname(self):
        return self.accountname

    def suggeststhreads(self):
        return 1

    def waitforthread(self):
        self.imapserver.connectionwait()

    def getcopyinstancelimit(self):
        return 'MSGCOPY_' + self.repository.getname()

    def getvisiblename(self):
        return self.visiblename

    def getuidvalidity(self):
        imapobj = self.imapserver.acquireconnection()
        try:
            # Primes untagged_responses
            self.selectro(imapobj)
            return long(imapobj.untagged_responses['UIDVALIDITY'][0])
        finally:
            self.imapserver.releaseconnection(imapobj)
    
    def quickchanged(self, statusfolder):
        # An IMAP folder has definitely changed if the number of
        # messages or the UID of the last message have changed.  Otherwise
        # only flag changes could have occurred.
        imapobj = self.imapserver.acquireconnection()
        try:
            # Primes untagged_responses
            imapobj.select(self.getfullname(), readonly = 1, force = 1)
            try:
                # Some mail servers do not return an EXISTS response if
                # the folder is empty.
                maxmsgid = long(imapobj.untagged_responses['EXISTS'][0])
            except KeyError:
                return True

            # Different number of messages than last time?
            if maxmsgid != len(statusfolder.getmessagelist()):
                return True

            if maxmsgid < 1:
                # No messages; return
                return False

            # Now, get the UID for the last message.
            response = imapobj.fetch('%d' % maxmsgid, '(UID)')[1]
        finally:
            self.imapserver.releaseconnection(imapobj)

        # Discard the message number.
        messagestr = string.split(response[0], maxsplit = 1)[1]
        options = imaputil.flags2hash(messagestr)
        if not options.has_key('UID'):
            return True
        uid = long(options['UID'])
        saveduids = statusfolder.getmessagelist().keys()
        saveduids.sort()
        if uid != saveduids[-1]:
            return True

        return False

    # TODO: Make this so that it can define a date that would be the oldest messages etc.
    def cachemessagelist(self):
        imapobj = self.imapserver.acquireconnection()
        self.messagelist = {}

        try:
            # Primes untagged_responses
            imapobj.select(self.getfullname(), readonly = 1, force = 1)

            maxage = self.config.getdefaultint("Account " + self.accountname, "maxage", -1)
            maxsize = self.config.getdefaultint("Account " + self.accountname, "maxsize", -1)

            if (maxage != -1) | (maxsize != -1):
                try:
                    search_condition = "(";

                    if(maxage != -1):
                        #find out what the oldest message is that we should look at
                        oldest_time_struct = time.gmtime(time.time() - (60*60*24*maxage))

                        #format this manually - otherwise locales could cause problems
                        monthnames_standard = ["Jan", "Feb", "Mar", "Apr", "May", \
                            "June", "July", "Aug", "Sep", "Oct", "Nov", "Dec"]

                        our_monthname = monthnames_standard[oldest_time_struct[1]-1]
                        daystr = "%(day)02d" % {'day' : oldest_time_struct[2]}
                        date_search_str = "SINCE " + daystr + "-" + our_monthname \
                            + "-" + str(oldest_time_struct[0])

                        search_condition += date_search_str

                    if(maxsize != -1):
                        if(maxage != 1): #There are two conditions - add a space
                            search_condition += " "

                        search_condition += "SMALLER " + self.config.getdefault("Account " + self.accountname, "maxsize", -1)

                    search_condition += ")"
                    searchresult = imapobj.search(None, search_condition)

                    #result would come back seperated by space - to change into a fetch
                    #statement we need to change space to comma
                    messagesToFetch = searchresult[1][0].replace(" ", ",")
                except KeyError:
                    return
                if len(messagesToFetch) < 1:
                    # No messages; return
                    return
            else:
                try:
                    # Some mail servers do not return an EXISTS response if
                    # the folder is empty.

                    maxmsgid = long(imapobj.untagged_responses['EXISTS'][0])
                    messagesToFetch = '1:%d' % maxmsgid;
                except KeyError:
                    return
                if maxmsgid < 1:
                    #no messages; return
                    return
            # Now, get the flags and UIDs for these.
            # We could conceivably get rid of maxmsgid and just say
            # '1:*' here.
            response = imapobj.fetch(messagesToFetch, '(FLAGS UID)')[1]
        finally:
            self.imapserver.releaseconnection(imapobj)
        for messagestr in response:
            # Discard the message number.
            messagestr = string.split(messagestr, maxsplit = 1)[1]
            options = imaputil.flags2hash(messagestr)
            if not options.has_key('UID'):
                UIBase.getglobalui().warn('No UID in message with options %s' %\
                                          str(options),
                                          minor = 1)
            else:
                uid = long(options['UID'])
                flags = imaputil.flagsimap2maildir(options['FLAGS'])
                rtime = imaplibutil.Internaldate2epoch(messagestr)
                self.messagelist[uid] = {'uid': uid, 'flags': flags, 'time': rtime}

    def getmessagelist(self):
        return self.messagelist

    def getmessage(self, uid):
        ui = UIBase.getglobalui()
        imapobj = self.imapserver.acquireconnection()
        try:
            imapobj.select(self.getfullname(), readonly = 1)
            initialresult = imapobj.uid('fetch', '%d' % uid, '(BODY.PEEK[])')
            ui.debug('imap', 'Returned object from fetching %d: %s' % \
                     (uid, str(initialresult)))
            return initialresult[1][0][1].replace("\r\n", "\n")
                
        finally:
            self.imapserver.releaseconnection(imapobj)

    def getmessagetime(self, uid):
        return self.messagelist[uid]['time']
    
    def getmessageflags(self, uid):
        return self.messagelist[uid]['flags']

    def savemessage_getnewheader(self, content):
        headername = 'X-OfflineIMAP-%s-' % str(binascii.crc32(content)).replace('-', 'x')
        headername += binascii.hexlify(self.repository.getname()) + '-'
        headername += binascii.hexlify(self.getname())
        headervalue= '%d-' % long(time.time())
        headervalue += str(self.randomgenerator.random()).replace('.', '')
        headervalue += '-v' + versionstr
        return (headername, headervalue)

    def savemessage_addheader(self, content, headername, headervalue):
        ui = UIBase.getglobalui()
        ui.debug('imap',
                 'savemessage_addheader: called to add %s: %s' % (headername,
                                                                  headervalue))
        insertionpoint = content.find("\r\n")
        ui.debug('imap', 'savemessage_addheader: insertionpoint = %d' % insertionpoint)
        leader = content[0:insertionpoint]
        ui.debug('imap', 'savemessage_addheader: leader = %s' % repr(leader))
        if insertionpoint == 0 or insertionpoint == -1:
            newline = ''
            insertionpoint = 0
        else:
            newline = "\r\n"
        newline += "%s: %s" % (headername, headervalue)
        ui.debug('imap', 'savemessage_addheader: newline = ' + repr(newline))
        trailer = content[insertionpoint:]
        ui.debug('imap', 'savemessage_addheader: trailer = ' + repr(trailer))
        return leader + newline + trailer

    def savemessage_searchforheader(self, imapobj, headername, headervalue):
        if imapobj.untagged_responses.has_key('APPENDUID'):
            return long(imapobj.untagged_responses['APPENDUID'][-1].split(' ')[1])

        ui = UIBase.getglobalui()
        ui.debug('imap', 'savemessage_searchforheader called for %s: %s' % \
                 (headername, headervalue))
        # Now find the UID it got.
        headervalue = imapobj._quote(headervalue)
        try:
            matchinguids = imapobj.uid('search', 'HEADER', headername, headervalue)[1][0]
        except imapobj.error, err:
            # IMAP server doesn't implement search or had a problem.
            ui.debug('imap', "savemessage_searchforheader: got IMAP error '%s' while attempting to UID SEARCH for message with header %s" % (err, headername))
            return 0
        ui.debug('imap', 'savemessage_searchforheader got initial matchinguids: ' + repr(matchinguids))

        if matchinguids == '':
            ui.debug('imap', "savemessage_searchforheader: UID SEARCH for message with header %s yielded no results" % headername)
            return 0

        matchinguids = matchinguids.split(' ')
        ui.debug('imap', 'savemessage_searchforheader: matchinguids now ' + \
                 repr(matchinguids))
        if len(matchinguids) != 1 or matchinguids[0] == None:
            raise ValueError, "While attempting to find UID for message with header %s, got wrong-sized matchinguids of %s" % (headername, str(matchinguids))
        matchinguids.sort()
        return long(matchinguids[0])

    def savemessage(self, uid, content, flags, rtime):
        imapobj = self.imapserver.acquireconnection()
        ui = UIBase.getglobalui()
        ui.debug('imap', 'savemessage: called')
        try:
            try:
                imapobj.select(self.getfullname()) # Needed for search
            except imapobj.readonly:
                ui.msgtoreadonly(self, uid, content, flags)
                # Return indicating message taken, but no UID assigned.
                # Fudge it.
                return 0
            
            # This backend always assigns a new uid, so the uid arg is ignored.
            # In order to get the new uid, we need to save off the message ID.

            message = rfc822.Message(StringIO(content))
            datetuple_msg = rfc822.parsedate(message.getheader('Date'))
            # Will be None if missing or not in a valid format.

            # If time isn't known
            if rtime == None and datetuple_msg == None:
                datetuple = time.localtime()
            elif rtime == None:
                datetuple = datetuple_msg
            else:
                datetuple = time.localtime(rtime)

            try:
                if datetuple[0] < 1981:
                    raise ValueError

                # Check for invalid date
                datetuple_check = time.localtime(time.mktime(datetuple))
                if datetuple[:2] != datetuple_check[:2]:
                    raise ValueError

                # This could raise a value error if it's not a valid format.
                date = imaplib.Time2Internaldate(datetuple) 
            except (ValueError, OverflowError):
                # Argh, sometimes it's a valid format but year is 0102
                # or something.  Argh.  It seems that Time2Internaldate
                # will rause a ValueError if the year is 0102 but not 1902,
                # but some IMAP servers nonetheless choke on 1902.
                date = imaplib.Time2Internaldate(time.localtime())

            ui.debug('imap', 'savemessage: using date ' + str(date))
            content = re.sub("(?<!\r)\n", "\r\n", content)
            ui.debug('imap', 'savemessage: initial content is: ' + repr(content))

            (headername, headervalue) = self.savemessage_getnewheader(content)
            ui.debug('imap', 'savemessage: new headers are: %s: %s' % \
                     (headername, headervalue))
            content = self.savemessage_addheader(content, headername,
                                                 headervalue)
            ui.debug('imap', 'savemessage: new content is: ' + repr(content))
            ui.debug('imap', 'savemessage: new content length is ' + \
                     str(len(content)))

            assert(imapobj.append(self.getfullname(),
                                       imaputil.flagsmaildir2imap(flags),
                                       date, content)[0] == 'OK')

            # Checkpoint.  Let it write out the messages, etc.
            assert(imapobj.check()[0] == 'OK')

            # Keep trying until we get the UID.
            ui.debug('imap', 'savemessage: first attempt to get new UID')
            uid = self.savemessage_searchforheader(imapobj, headername,
                                                   headervalue)
            # See docs for savemessage in Base.py for explanation of this and other return values
            if uid <= 0:
                ui.debug('imap', 'savemessage: first attempt to get new UID failed.  Going to run a NOOP and try again.')
                assert(imapobj.noop()[0] == 'OK')
                uid = self.savemessage_searchforheader(imapobj, headername,
                                                       headervalue)
        finally:
            self.imapserver.releaseconnection(imapobj)

        if uid: # avoid UID FETCH 0 crash happening later on
            self.messagelist[uid] = {'uid': uid, 'flags': flags}

        ui.debug('imap', 'savemessage: returning %d' % uid)
        return uid

    def savemessageflags(self, uid, flags):
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().flagstoreadonly(self, [uid], flags)
                return
            result = imapobj.uid('store', '%d' % uid, 'FLAGS',
                                 imaputil.flagsmaildir2imap(flags))
            assert result[0] == 'OK', 'Error with store: ' + '. '.join(r[1])
        finally:
            self.imapserver.releaseconnection(imapobj)
        result = result[1][0]
        if not result:
            self.messagelist[uid]['flags'] = flags
        else:
            flags = imaputil.flags2hash(imaputil.imapsplit(result)[1])['FLAGS']
            self.messagelist[uid]['flags'] = imaputil.flagsimap2maildir(flags)

    def addmessageflags(self, uid, flags):
        self.addmessagesflags([uid], flags)

    def addmessagesflags_noconvert(self, uidlist, flags):
        self.processmessagesflags('+', uidlist, flags)

    def addmessagesflags(self, uidlist, flags):
        """This is here for the sake of UIDMaps.py -- deletemessages must
        add flags and get a converted UID, and if we don't have noconvert,
        then UIDMaps will try to convert it twice."""
        self.addmessagesflags_noconvert(uidlist, flags)

    def deletemessageflags(self, uid, flags):
        self.deletemessagesflags([uid], flags)

    def deletemessagesflags(self, uidlist, flags):
        self.processmessagesflags('-', uidlist, flags)

    def processmessagesflags(self, operation, uidlist, flags):
        if len(uidlist) > 101:
            # Hack for those IMAP ervers with a limited line length
            self.processmessagesflags(operation, uidlist[:100], flags)
            self.processmessagesflags(operation, uidlist[100:], flags)
            return
        
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().flagstoreadonly(self, uidlist, flags)
                return
            r = imapobj.uid('store',
                            imaputil.listjoin(uidlist),
                            operation + 'FLAGS',
                            imaputil.flagsmaildir2imap(flags))
            assert r[0] == 'OK', 'Error with store: ' + '. '.join(r[1])
            r = r[1]
        finally:
            self.imapserver.releaseconnection(imapobj)
        # Some IMAP servers do not always return a result.  Therefore,
        # only update the ones that it talks about, and manually fix
        # the others.
        needupdate = copy(uidlist)
        for result in r:
            if result == None:
                # Compensate for servers that don't return anything from
                # STORE.
                continue
            attributehash = imaputil.flags2hash(imaputil.imapsplit(result)[1])
            if not ('UID' in attributehash and 'FLAGS' in attributehash):
                # Compensate for servers that don't return a UID attribute.
                continue
            lflags = attributehash['FLAGS']
            uid = long(attributehash['UID'])
            self.messagelist[uid]['flags'] = imaputil.flagsimap2maildir(lflags)
            try:
                needupdate.remove(uid)
            except ValueError:          # Let it slide if it's not in the list
                pass
        for uid in needupdate:
            if operation == '+':
                for flag in flags:
                    if not flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].append(flag)
                    self.messagelist[uid]['flags'].sort()
            elif operation == '-':
                for flag in flags:
                    if flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].remove(flag)

    def deletemessage(self, uid):
        self.deletemessages_noconvert([uid])

    def deletemessages(self, uidlist):
        self.deletemessages_noconvert(uidlist)

    def deletemessages_noconvert(self, uidlist):
        # Weed out ones not in self.messagelist
        uidlist = [uid for uid in uidlist if uid in self.messagelist]
        if not len(uidlist):
            return        

        self.addmessagesflags_noconvert(uidlist, ['T'])
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().deletereadonly(self, uidlist)
                return
            if self.expunge:
                assert(imapobj.expunge()[0] == 'OK')
        finally:
            self.imapserver.releaseconnection(imapobj)
        for uid in uidlist:
            del self.messagelist[uid]
        
        

########NEW FILE########
__FILENAME__ = LocalStatus
# Local status cache virtual folder
# Copyright (C) 2002 - 2008 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Base import BaseFolder
import os, threading

magicline = "OFFLINEIMAP LocalStatus CACHE DATA - DO NOT MODIFY - FORMAT 1"

class LocalStatusFolder(BaseFolder):
    def __init__(self, root, name, repository, accountname, config):
        self.name = name
        self.root = root
        self.sep = '.'
        self.config = config
        self.dofsync = config.getdefaultboolean("general", "fsync", True)
        self.filename = os.path.join(root, name)
        self.filename = repository.getfolderfilename(name)
        self.messagelist = None
        self.repository = repository
        self.savelock = threading.Lock()
        self.doautosave = 1
        self.accountname = accountname
        BaseFolder.__init__(self)

    def getaccountname(self):
        return self.accountname

    def storesmessages(self):
        return 0

    def isnewfolder(self):
        return not os.path.exists(self.filename)

    def getname(self):
        return self.name

    def getroot(self):
        return self.root

    def getsep(self):
        return self.sep

    def getfullname(self):
        return self.filename

    def deletemessagelist(self):
        if not self.isnewfolder():
            os.unlink(self.filename)

    def cachemessagelist(self):
        if self.isnewfolder():
            self.messagelist = {}
            return
        file = open(self.filename, "rt")
        self.messagelist = {}
        line = file.readline().strip()
        if not line and not line.read():
            # The status file is empty - should not have happened,
            # but somehow did.
            file.close()
            return
        assert(line == magicline)
        for line in file.xreadlines():
            line = line.strip()
            uid, flags = line.split(':')
            uid = long(uid)
            flags = [x for x in flags]
            self.messagelist[uid] = {'uid': uid, 'flags': flags}
        file.close()

    def autosave(self):
        if self.doautosave:
            self.save()

    def save(self):
        self.savelock.acquire()
        try:
            file = open(self.filename + ".tmp", "wt")
            file.write(magicline + "\n")
            for msg in self.messagelist.values():
                flags = msg['flags']
                flags.sort()
                flags = ''.join(flags)
                file.write("%s:%s\n" % (msg['uid'], flags))
            file.flush()
            if self.dofsync:
                os.fsync(file.fileno())
            file.close()
            os.rename(self.filename + ".tmp", self.filename)

            if self.dofsync:
                try:
                    fd = os.open(os.path.dirname(self.filename), os.O_RDONLY)
                    os.fsync(fd)
                    os.close(fd)
                except:
                    pass

        finally:
            self.savelock.release()

    def getmessagelist(self):
        return self.messagelist

    def savemessage(self, uid, content, flags, rtime):
        if uid < 0:
            # We cannot assign a uid.
            return uid

        if uid in self.messagelist:     # already have it
            self.savemessageflags(uid, flags)
            return uid

        self.messagelist[uid] = {'uid': uid, 'flags': flags, 'time': rtime}
        self.autosave()
        return uid

    def getmessageflags(self, uid):
        return self.messagelist[uid]['flags']

    def getmessagetime(self, uid):
        return self.messagelist[uid]['time']

    def savemessageflags(self, uid, flags):
        self.messagelist[uid]['flags'] = flags
        self.autosave()

    def deletemessage(self, uid):
        self.deletemessages([uid])

    def deletemessages(self, uidlist):
        # Weed out ones not in self.messagelist
        uidlist = [uid for uid in uidlist if uid in self.messagelist]
        if not len(uidlist):
            return

        for uid in uidlist:
            del(self.messagelist[uid])
        self.autosave()

########NEW FILE########
__FILENAME__ = Maildir
# Maildir folder support
# Copyright (C) 2002 - 2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import os.path, os, re, time, socket
from Base import BaseFolder
from offlineimap import imaputil
from offlineimap.ui import UIBase
from threading import Lock

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

uidmatchre = re.compile(',U=(\d+)')
flagmatchre = re.compile(':.*2,([A-Z]+)')
timestampmatchre = re.compile('(\d+)');

timeseq = 0
lasttime = long(0)
timelock = Lock()

def gettimeseq():
    global lasttime, timeseq, timelock
    timelock.acquire()
    try:
        thistime = long(time.time())
        if thistime == lasttime:
            timeseq += 1
            return (thistime, timeseq)
        else:
            lasttime = thistime
            timeseq = 0
            return (thistime, timeseq)
    finally:
        timelock.release()

class MaildirFolder(BaseFolder):
    def __init__(self, root, name, sep, repository, accountname, config):
        self.name = name
        self.config = config
        self.dofsync = config.getdefaultboolean("general", "fsync", True)
        self.root = root
        self.sep = sep
        self.messagelist = None
        self.repository = repository
        self.accountname = accountname
        BaseFolder.__init__(self)

    def getaccountname(self):
        return self.accountname

    def getfullname(self):
        return os.path.join(self.getroot(), self.getname())

    def getuidvalidity(self):
        """Maildirs have no notion of uidvalidity, so we just return a magic
        token."""
        return 42

    #Checks to see if the given message is within the maximum age according
    #to the maildir name which should begin with a timestamp
    def _iswithinmaxage(self, messagename, maxage):
        #In order to have the same behaviour as SINCE in an IMAP search
        #we must convert this to the oldest time and then strip off hrs/mins
        #from that day
        oldest_time_utc = time.time() - (60*60*24*maxage)
        oldest_time_struct = time.gmtime(oldest_time_utc)
        oldest_time_today_seconds = ((oldest_time_struct[3] * 3600) \
            + (oldest_time_struct[4] * 60) \
            + oldest_time_struct[5])
        oldest_time_utc -= oldest_time_today_seconds

        timestampmatch = timestampmatchre.search(messagename)
        timestampstr = timestampmatch.group()
        timestamplong = long(timestampstr)
        if(timestamplong < oldest_time_utc):
            return False
        else:
            return True


    def _scanfolder(self):
        """Cache the message list.  Maildir flags are:
        R (replied)
        S (seen)
        T (trashed)
        D (draft)
        F (flagged)
        and must occur in ASCII order."""
        retval = {}
        files = []
        nouidcounter = -1               # Messages without UIDs get
                                        # negative UID numbers.
        foldermd5 = md5(self.getvisiblename()).hexdigest()
        folderstr = ',FMD5=' + foldermd5
        for dirannex in ['new', 'cur']:
            fulldirname = os.path.join(self.getfullname(), dirannex)
            files.extend(os.path.join(fulldirname, filename) for
                         filename in os.listdir(fulldirname))
        for file in files:
            messagename = os.path.basename(file)

            #check if there is a parameter for maxage / maxsize - then see if this
            #message should be considered or not
            maxage = self.config.getdefaultint("Account " + self.accountname, "maxage", -1)
            maxsize = self.config.getdefaultint("Account " + self.accountname, "maxsize", -1)

            if(maxage != -1):
                isnewenough = self._iswithinmaxage(messagename, maxage)
                if(isnewenough != True):
                    #this message is older than we should consider....
                    continue

            #Check and see if the message is too big if the maxsize for this account is set
            if(maxsize != -1):
                filesize = os.path.getsize(file)
                if(filesize > maxsize):
                    continue
            

            foldermatch = messagename.find(folderstr) != -1
            if not foldermatch:
                # If there is no folder MD5 specified, or if it mismatches,
                # assume it is a foreign (new) message and generate a
                # negative uid for it
                uid = nouidcounter
                nouidcounter -= 1
            else:                       # It comes from our folder.
                uidmatch = uidmatchre.search(messagename)
                uid = None
                if not uidmatch:
                    uid = nouidcounter
                    nouidcounter -= 1
                else:
                    uid = long(uidmatch.group(1))
            flagmatch = flagmatchre.search(messagename)
            flags = []
            if flagmatch:
                flags = [x for x in flagmatch.group(1)]
            flags.sort()
            retval[uid] = {'uid': uid,
                           'flags': flags,
                           'filename': file}
        return retval

    def quickchanged(self, statusfolder):
        self.cachemessagelist()
        savedmessages = statusfolder.getmessagelist()
        if len(self.messagelist) != len(savedmessages):
            return True
        for uid in self.messagelist.keys():
            if uid not in savedmessages:
                return True
            if self.messagelist[uid]['flags'] != savedmessages[uid]['flags']:
                return True
        return False

    def cachemessagelist(self):
        if self.messagelist is None:
            self.messagelist = self._scanfolder()
            
    def getmessagelist(self):
        return self.messagelist

    def getmessage(self, uid):
        filename = self.messagelist[uid]['filename']
        file = open(filename, 'rt')
        retval = file.read()
        file.close()
        return retval.replace("\r\n", "\n")

    def getmessagetime( self, uid ):
        filename = self.messagelist[uid]['filename']
        st = os.stat(filename)
        return st.st_mtime

    def savemessage(self, uid, content, flags, rtime):
        # This function only ever saves to tmp/,
        # but it calls savemessageflags() to actually save to cur/ or new/.
        ui = UIBase.getglobalui()
        ui.debug('maildir', 'savemessage: called to write with flags %s and content %s' % \
                 (repr(flags), repr(content)))
        if uid < 0:
            # We cannot assign a new uid.
            return uid
        if uid in self.messagelist:
            # We already have it.
            self.savemessageflags(uid, flags)
            return uid

        # Otherwise, save the message in tmp/ and then call savemessageflags()
        # to give it a permanent home.
        tmpdir = os.path.join(self.getfullname(), 'tmp')
        messagename = None
        attempts = 0
        while 1:
            if attempts > 15:
                raise IOError, "Couldn't write to file %s" % messagename
            timeval, timeseq = gettimeseq()
            messagename = '%d_%d.%d.%s,U=%d,FMD5=%s' % \
                          (timeval,
                           timeseq,
                           os.getpid(),
                           socket.gethostname(),
                           uid,
                           md5(self.getvisiblename()).hexdigest())
            if os.path.exists(os.path.join(tmpdir, messagename)):
                time.sleep(2)
                attempts += 1
            else:
                break
        tmpmessagename = messagename.split(',')[0]
        ui.debug('maildir', 'savemessage: using temporary name %s' % tmpmessagename)
        file = open(os.path.join(tmpdir, tmpmessagename), "wt")
        file.write(content)

        # Make sure the data hits the disk
        file.flush()
        if self.dofsync:
            os.fsync(file.fileno())

        file.close()
        if rtime != None:
            os.utime(os.path.join(tmpdir,tmpmessagename), (rtime,rtime))
        ui.debug('maildir', 'savemessage: moving from %s to %s' % \
                 (tmpmessagename, messagename))
        if tmpmessagename != messagename: # then rename it
            os.rename(os.path.join(tmpdir, tmpmessagename),
                    os.path.join(tmpdir, messagename))

        if self.dofsync:
            try:
                # fsync the directory (safer semantics in Linux)
                fd = os.open(tmpdir, os.O_RDONLY)
                os.fsync(fd)
                os.close(fd)
            except:
                pass

        self.messagelist[uid] = {'uid': uid, 'flags': [],
                                 'filename': os.path.join(tmpdir, messagename)}
        self.savemessageflags(uid, flags)
        ui.debug('maildir', 'savemessage: returning uid %d' % uid)
        return uid
        
    def getmessageflags(self, uid):
        return self.messagelist[uid]['flags']

    def savemessageflags(self, uid, flags):
        oldfilename = self.messagelist[uid]['filename']
        newpath, newname = os.path.split(oldfilename)
        tmpdir = os.path.join(self.getfullname(), 'tmp')
        if 'S' in flags:
            # If a message has been seen, it goes into the cur
            # directory.  CR debian#152482, [complete.org #4]
            newpath = os.path.join(self.getfullname(), 'cur')
        else:
            newpath = os.path.join(self.getfullname(), 'new')
        infostr = ':'
        infomatch = re.search('(:.*)$', newname)
        if infomatch:                   # If the info string is present..
            infostr = infomatch.group(1)
            newname = newname.split(':')[0] # Strip off the info string.
        infostr = re.sub('2,[A-Z]*', '', infostr)
        flags.sort()
        infostr += '2,' + ''.join(flags)
        newname += infostr
        
        newfilename = os.path.join(newpath, newname)
        if (newfilename != oldfilename):
            os.rename(oldfilename, newfilename)
            self.messagelist[uid]['flags'] = flags
            self.messagelist[uid]['filename'] = newfilename

        # By now, the message had better not be in tmp/ land!
        final_dir, final_name = os.path.split(self.messagelist[uid]['filename'])
        assert final_dir != tmpdir

    def deletemessage(self, uid):
        if not uid in self.messagelist:
            return
        filename = self.messagelist[uid]['filename']
        try:
            os.unlink(filename)
        except OSError:
            # Can't find the file -- maybe already deleted?
            newmsglist = self._scanfolder()
            if uid in newmsglist:       # Nope, try new filename.
                os.unlink(newmsglist[uid]['filename'])
            # Yep -- return.
        del(self.messagelist[uid])
        

########NEW FILE########
__FILENAME__ = UIDMaps
# Base folder support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
from offlineimap import threadutil
from offlineimap.threadutil import InstanceLimitedThread
from offlineimap.ui import UIBase
from IMAP import IMAPFolder
import os.path, re

class MappingFolderMixIn:
    def _initmapping(self):
        self.maplock = Lock()
        (self.diskr2l, self.diskl2r) = self._loadmaps()
        self._mb = self.__class__.__bases__[1]

    def _getmapfilename(self):
        return os.path.join(self.repository.getmapdir(),
                            self.getfolderbasename())
        
    def _loadmaps(self):
        self.maplock.acquire()
        try:
            mapfilename = self._getmapfilename()
            if not os.path.exists(mapfilename):
                return ({}, {})
            file = open(mapfilename, 'rt')
            r2l = {}
            l2r = {}
            while 1:
                line = file.readline()
                if not len(line):
                    break
                line = line.strip()
                (str1, str2) = line.split(':')
                loc = long(str1)
                rem = long(str2)
                r2l[rem] = loc
                l2r[loc] = rem
            return (r2l, l2r)
        finally:
            self.maplock.release()

    def _savemaps(self, dolock = 1):
        mapfilename = self._getmapfilename()
        if dolock: self.maplock.acquire()
        try:
            file = open(mapfilename + ".tmp", 'wt')
            for (key, value) in self.diskl2r.iteritems():
                file.write("%d:%d\n" % (key, value))
            file.close()
            os.rename(mapfilename + '.tmp', mapfilename)
        finally:
            if dolock: self.maplock.release()

    def _uidlist(self, mapping, items):
        return [mapping[x] for x in items]

    def cachemessagelist(self):
        self._mb.cachemessagelist(self)
        reallist = self._mb.getmessagelist(self)

        self.maplock.acquire()
        try:
            # OK.  Now we've got a nice list.  First, delete things from the
            # summary that have been deleted from the folder.

            for luid in self.diskl2r.keys():
                if not reallist.has_key(luid):
                    ruid = self.diskl2r[luid]
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]

            # Now, assign negative UIDs to local items.
            self._savemaps(dolock = 0)
            nextneg = -1

            self.r2l = self.diskr2l.copy()
            self.l2r = self.diskl2r.copy()

            for luid in reallist.keys():
                if not self.l2r.has_key(luid):
                    ruid = nextneg
                    nextneg -= 1
                    self.l2r[luid] = ruid
                    self.r2l[ruid] = luid
        finally:
            self.maplock.release()

    def getmessagelist(self):
        """Gets the current message list.
        You must call cachemessagelist() before calling this function!"""

        retval = {}
        localhash = self._mb.getmessagelist(self)
        self.maplock.acquire()
        try:
            for key, value in localhash.items():
                try:
                    key = self.l2r[key]
                except KeyError:
                    # Sometimes, the IMAP backend may put in a new message,
                    # then this function acquires the lock before the system
                    # has the chance to note it in the mapping.  In that case,
                    # just ignore it.
                    continue
                value = value.copy()
                value['uid'] = self.l2r[value['uid']]
                retval[key] = value
            return retval
        finally:
            self.maplock.release()

    def getmessage(self, uid):
        """Returns the content of the specified message."""
        return self._mb.getmessage(self, self.r2l[uid])

    def savemessage(self, uid, content, flags, rtime):
        """Writes a new message, with the specified uid.
        If the uid is < 0, the backend should assign a new uid and return it.

        If the backend cannot assign a new uid, it returns the uid passed in
        WITHOUT saving the message.

        If the backend CAN assign a new uid, but cannot find out what this UID
        is (as is the case with many IMAP servers), it returns 0 but DOES save
        the message.
        
        IMAP backend should be the only one that can assign a new uid.

        If the uid is > 0, the backend should set the uid to this, if it can.
        If it cannot set the uid to that, it will save it anyway.
        It will return the uid assigned in any case.
        """
        if uid < 0:
            # We cannot assign a new uid.
            return uid
        if uid in self.r2l:
            self.savemessageflags(uid, flags)
            return uid
        newluid = self._mb.savemessage(self, -1, content, flags, rtime)
        if newluid < 1:
            raise ValueError, "Backend could not find uid for message"
        self.maplock.acquire()
        try:
            self.diskl2r[newluid] = uid
            self.diskr2l[uid] = newluid
            self.l2r[newluid] = uid
            self.r2l[uid] = newluid
            self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def getmessageflags(self, uid):
        return self._mb.getmessageflags(self, self.r2l[uid])

    def getmessagetime(self, uid):
        return None

    def savemessageflags(self, uid, flags):
        self._mb.savemessageflags(self, self.r2l[uid], flags)

    def addmessageflags(self, uid, flags):
        self._mb.addmessageflags(self, self.r2l[uid], flags)

    def addmessagesflags(self, uidlist, flags):
        self._mb.addmessagesflags(self, self._uidlist(self.r2l, uidlist),
                                  flags)

    def _mapped_delete(self, uidlist):
        self.maplock.acquire()
        try:
            needssave = 0
            for ruid in uidlist:
                luid = self.r2l[ruid]
                del self.r2l[ruid]
                del self.l2r[luid]
                if ruid > 0:
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]
                    needssave = 1
            if needssave:
                self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def deletemessageflags(self, uid, flags):
        self._mb.deletemessageflags(self, self.r2l[uid], flags)

    def deletemessagesflags(self, uidlist, flags):
        self._mb.deletemessagesflags(self, self._uidlist(self.r2l, uidlist),
                                     flags)

    def deletemessage(self, uid):
        self._mb.deletemessage(self, self.r2l[uid])
        self._mapped_delete([uid])

    def deletemessages(self, uidlist):
        self._mb.deletemessages(self, self._uidlist(self.r2l, uidlist))
        self._mapped_delete(uidlist)

    #def syncmessagesto_neguid_msg(self, uid, dest, applyto, register = 1):
    # does not need changes because it calls functions that make the changes   
    # same goes for all other sync messages types.
    

# Define a class for local part of IMAP.
class MappedIMAPFolder(MappingFolderMixIn, IMAPFolder):
    def __init__(self, *args, **kwargs):
	apply(IMAPFolder.__init__, (self,) + args, kwargs)
        self._initmapping()

########NEW FILE########
__FILENAME__ = imaplibutil
# imaplib utilities
# Copyright (C) 2002-2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import re, string, types, binascii, socket, time, random, subprocess, sys, os
from offlineimap.ui import UIBase
from imaplib import *

# Import the symbols we need that aren't exported by default
from imaplib import IMAP4_PORT, IMAP4_SSL_PORT, InternalDate, Mon2num

try:
    import ssl
    ssl_wrap = ssl.wrap_socket
except ImportError:
    ssl_wrap = socket.ssl

class IMAP4_Tunnel(IMAP4):
    """IMAP4 client class over a tunnel

    Instantiate with: IMAP4_Tunnel(tunnelcmd)

    tunnelcmd -- shell command to generate the tunnel.
    The result will be in PREAUTH stage."""

    def __init__(self, tunnelcmd):
        IMAP4.__init__(self, tunnelcmd)

    def open(self, host, port):
        """The tunnelcmd comes in on host!"""
        self.process = subprocess.Popen(host, shell=True, close_fds=True,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (self.outfd, self.infd) = (self.process.stdin, self.process.stdout)

    def read(self, size):
        retval = ''
        while len(retval) < size:
            retval += self.infd.read(size - len(retval))
        return retval

    def readline(self):
        return self.infd.readline()

    def send(self, data):
        self.outfd.write(data)

    def shutdown(self):
        self.infd.close()
        self.outfd.close()
        self.process.wait()
        
class sslwrapper:
    def __init__(self, sslsock):
        self.sslsock = sslsock
        self.readbuf = ''

    def write(self, s):
        return self.sslsock.write(s)

    def _read(self, n):
        return self.sslsock.read(n)

    def read(self, n):
        if len(self.readbuf):
            # Return the stuff in readbuf, even if less than n.
            # It might contain the rest of the line, and if we try to
            # read more, might block waiting for data that is not
            # coming to arrive.
            bytesfrombuf = min(n, len(self.readbuf))
            retval = self.readbuf[:bytesfrombuf]
            self.readbuf = self.readbuf[bytesfrombuf:]
            return retval
        retval = self._read(n)
        if len(retval) > n:
            self.readbuf = retval[n:]
            return retval[:n]
        return retval

    def readline(self):
        retval = ''
        while 1:
            linebuf = self.read(1024)
            nlindex = linebuf.find("\n")
            if nlindex != -1:
                retval += linebuf[:nlindex + 1]
                self.readbuf = linebuf[nlindex + 1:] + self.readbuf
                return retval
            else:
                retval += linebuf

def new_mesg(self, s, secs=None):
            if secs is None:
                secs = time.time()
            tm = time.strftime('%M:%S', time.localtime(secs))
            UIBase.getglobalui().debug('imap', '  %s.%02d %s' % (tm, (secs*100)%100, s))

class WrappedIMAP4_SSL(IMAP4_SSL):
    def open(self, host = '', port = IMAP4_SSL_PORT):
        IMAP4_SSL.open(self, host, port)
        self.sslobj = sslwrapper(self.sslobj)

    def readline(self):
        return self.sslobj.readline()

def new_open(self, host = '', port = IMAP4_PORT):
        """Setup connection to remote server on "host:port"
            (default: localhost:standard IMAP4 port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        res = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                 socket.SOCK_STREAM)

        # Try each address returned by getaddrinfo in turn until we
        # manage to connect to one.
        # Try all the addresses in turn until we connect()
        last_error = 0
        for remote in res:
            af, socktype, proto, canonname, sa = remote
            self.sock = socket.socket(af, socktype, proto)
            last_error = self.sock.connect_ex(sa)
            if last_error == 0:
                break
            else:
                self.sock.close()
        if last_error != 0:
            # FIXME
            raise socket.error(last_error)
        self.file = self.sock.makefile('rb')

def new_open_ssl(self, host = '', port = IMAP4_SSL_PORT):
        """Setup connection to remote server on "host:port".
            (default: localhost:standard IMAP4 SSL port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        #This connects to the first ip found ipv4/ipv6
        #Added by Adriaan Peeters <apeeters@lashout.net> based on a socket
        #example from the python documentation:
        #http://www.python.org/doc/lib/socket-example.html
        res = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                 socket.SOCK_STREAM)
        # Try all the addresses in turn until we connect()
        last_error = 0
        for remote in res:
            af, socktype, proto, canonname, sa = remote
            self.sock = socket.socket(af, socktype, proto)
            last_error = self.sock.connect_ex(sa)
            if last_error == 0:
                break
            else:
                self.sock.close()
        if last_error != 0:
            # FIXME
            raise socket.error(last_error)
        self.sslobj = ssl_wrap(self.sock, self.keyfile, self.certfile)
        self.sslobj = sslwrapper(self.sslobj)

mustquote = re.compile(r"[^\w!#$%&'+,.:;<=>?^`|~-]")

def Internaldate2epoch(resp):
    """Convert IMAP4 INTERNALDATE to UT.

    Returns seconds since the epoch.
    """

    mo = InternalDate.match(resp)
    if not mo:
        return None

    mon = Mon2num[mo.group('mon')]
    zonen = mo.group('zonen')

    day = int(mo.group('day'))
    year = int(mo.group('year'))
    hour = int(mo.group('hour'))
    min = int(mo.group('min'))
    sec = int(mo.group('sec'))
    zoneh = int(mo.group('zoneh'))
    zonem = int(mo.group('zonem'))

    # INTERNALDATE timezone must be subtracted to get UT

    zone = (zoneh*60 + zonem)*60
    if zonen == '-':
        zone = -zone

    tt = (year, mon, day, hour, min, sec, -1, -1, -1)

    return time.mktime(tt)

########NEW FILE########
__FILENAME__ = imapserver
# IMAP server support
# Copyright (C) 2002 - 2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import imaplib
from offlineimap import imaplibutil, imaputil, threadutil
from offlineimap.ui import UIBase
from threading import *
import thread, hmac, os, time
import base64

from StringIO import StringIO
from platform import system

try:
    # do we have a recent pykerberos?
    have_gss = False
    import kerberos
    if 'authGSSClientWrap' in dir(kerberos):
        have_gss = True
except ImportError:
    pass

class UsefulIMAPMixIn:
    def getstate(self):
        return self.state
    def getselectedfolder(self):
        if self.getstate() == 'SELECTED':
            return self.selectedfolder
        return None

    def select(self, mailbox='INBOX', readonly=None, force = 0):
        if (not force) and self.getselectedfolder() == mailbox \
           and self.is_readonly == readonly:
            # No change; return.
            return
        result = self.__class__.__bases__[1].select(self, mailbox, readonly)
        if result[0] != 'OK':
            raise ValueError, "Error from select: %s" % str(result)
        if self.getstate() == 'SELECTED':
            self.selectedfolder = mailbox
        else:
            self.selectedfolder = None

    def _mesg(self, s, secs=None):
        imaplibutil.new_mesg(self, s, secs)

class UsefulIMAP4(UsefulIMAPMixIn, imaplib.IMAP4):
    def open(self, host = '', port = imaplib.IMAP4_PORT):
        imaplibutil.new_open(self, host, port)

    # This is a hack around Darwin's implementation of realloc() (which
    # Python uses inside the socket code). On Darwin, we split the
    # message into 100k chunks, which should be small enough - smaller
    # might start seriously hurting performance ...

    def read(self, size):
        if (system() == 'Darwin') and (size>0) :
            read = 0
            io = StringIO()
            while read < size:
                data = imaplib.IMAP4.read (self, min(size-read,8192))
                read += len(data)
                io.write(data)
            return io.getvalue()
        else:
            return imaplib.IMAP4.read (self, size)

class UsefulIMAP4_SSL(UsefulIMAPMixIn, imaplibutil.WrappedIMAP4_SSL):
    def open(self, host = '', port = imaplib.IMAP4_SSL_PORT):
        imaplibutil.new_open_ssl(self, host, port)

    # This is the same hack as above, to be used in the case of an SSL
    # connexion.

    def read(self, size):
        if (system() == 'Darwin') and (size>0) :
            read = 0
            io = StringIO()
            while read < size:
                data = imaplibutil.WrappedIMAP4_SSL.read (self, min(size-read,8192))
                read += len(data)
                io.write(data)
            return io.getvalue()
        else:
            return imaplibutil.WrappedIMAP4_SSL.read (self,size)

class UsefulIMAP4_Tunnel(UsefulIMAPMixIn, imaplibutil.IMAP4_Tunnel): pass

class IMAPServer:
    GSS_STATE_STEP = 0
    GSS_STATE_WRAP = 1
    def __init__(self, config, reposname,
                 username = None, password = None, hostname = None,
                 port = None, ssl = 1, maxconnections = 1, tunnel = None,
                 reference = '""', sslclientcert = None, sslclientkey = None):
        self.reposname = reposname
        self.config = config
        self.username = username
        self.password = password
        self.passworderror = None
        self.goodpassword = None
        self.hostname = hostname
        self.tunnel = tunnel
        self.port = port
        self.usessl = ssl
        self.sslclientcert = sslclientcert
        self.sslclientkey = sslclientkey
        self.delim = None
        self.root = None
        if port == None:
            if ssl:
                self.port = 993
            else:
                self.port = 143
        self.maxconnections = maxconnections
        self.availableconnections = []
        self.assignedconnections = []
        self.lastowner = {}
        self.semaphore = BoundedSemaphore(self.maxconnections)
        self.connectionlock = Lock()
        self.reference = reference
        self.gss_step = self.GSS_STATE_STEP
        self.gss_vc = None
        self.gssapi = False

    def getpassword(self):
        if self.goodpassword != None:
            return self.goodpassword

        if self.password != None and self.passworderror == None:
            return self.password

        self.password = UIBase.getglobalui().getpass(self.reposname,
                                                     self.config,
                                                     self.passworderror)
        self.passworderror = None

        return self.password

    def getdelim(self):
        """Returns this server's folder delimiter.  Can only be called
        after one or more calls to acquireconnection."""
        return self.delim

    def getroot(self):
        """Returns this server's folder root.  Can only be called after one
        or more calls to acquireconnection."""
        return self.root


    def releaseconnection(self, connection):
        """Releases a connection, returning it to the pool."""
        self.connectionlock.acquire()
        self.assignedconnections.remove(connection)
        self.availableconnections.append(connection)
        self.connectionlock.release()
        self.semaphore.release()

    def md5handler(self, response):
        ui = UIBase.getglobalui()
        challenge = response.strip()
        ui.debug('imap', 'md5handler: got challenge %s' % challenge)

        passwd = self.repos.getpassword()
        retval = self.username + ' ' + hmac.new(passwd, challenge).hexdigest()
        ui.debug('imap', 'md5handler: returning %s' % retval)
        return retval

    def plainauth(self, imapobj):
        UIBase.getglobalui().debug('imap',
                                   'Attempting plain authentication')
        imapobj.login(self.username, self.repos.getpassword())

    def gssauth(self, response):
        data = base64.b64encode(response)
        try:
            if self.gss_step == self.GSS_STATE_STEP:
                if not self.gss_vc:
                    rc, self.gss_vc = kerberos.authGSSClientInit('imap@' + 
                                                                 self.hostname)
                    response = kerberos.authGSSClientResponse(self.gss_vc)
                rc = kerberos.authGSSClientStep(self.gss_vc, data)
                if rc != kerberos.AUTH_GSS_CONTINUE:
                   self.gss_step = self.GSS_STATE_WRAP
            elif self.gss_step == self.GSS_STATE_WRAP:
                rc = kerberos.authGSSClientUnwrap(self.gss_vc, data)
                response = kerberos.authGSSClientResponse(self.gss_vc)
                rc = kerberos.authGSSClientWrap(self.gss_vc, response,
                                                self.username)
            response = kerberos.authGSSClientResponse(self.gss_vc)
        except kerberos.GSSError, err:
            # Kerberos errored out on us, respond with None to cancel the
            # authentication
            UIBase.getglobalui().debug('imap',
                                       '%s: %s' % (err[0][0], err[1][0]))
            return None

        if not response:
            response = ''
        return base64.b64decode(response)

    def acquireconnection(self):
        """Fetches a connection from the pool, making sure to create a new one
        if needed, to obey the maximum connection limits, etc.
        Opens a connection to the server and returns an appropriate
        object."""

        self.semaphore.acquire()
        self.connectionlock.acquire()
        imapobj = None

        if len(self.availableconnections): # One is available.
            # Try to find one that previously belonged to this thread
            # as an optimization.  Start from the back since that's where
            # they're popped on.
            threadid = thread.get_ident()
            imapobj = None
            for i in range(len(self.availableconnections) - 1, -1, -1):
                tryobj = self.availableconnections[i]
                if self.lastowner[tryobj] == threadid:
                    imapobj = tryobj
                    del(self.availableconnections[i])
                    break
            if not imapobj:
                imapobj = self.availableconnections[0]
                del(self.availableconnections[0])
            self.assignedconnections.append(imapobj)
            self.lastowner[imapobj] = thread.get_ident()
            self.connectionlock.release()
            return imapobj
        
        self.connectionlock.release()   # Release until need to modify data

        """ Must be careful here that if we fail we should bail out gracefully
        and release locks / threads so that the next attempt can try...
        """
        success = 0
        try:
            while not success:
                # Generate a new connection.
                if self.tunnel:
                    UIBase.getglobalui().connecting('tunnel', self.tunnel)
                    imapobj = UsefulIMAP4_Tunnel(self.tunnel)
                    success = 1
                elif self.usessl:
                    UIBase.getglobalui().connecting(self.hostname, self.port)
                    imapobj = UsefulIMAP4_SSL(self.hostname, self.port,
                                              self.sslclientkey, self.sslclientcert)
                else:
                    UIBase.getglobalui().connecting(self.hostname, self.port)
                    imapobj = UsefulIMAP4(self.hostname, self.port)

                imapobj.mustquote = imaplibutil.mustquote

                if not self.tunnel:
                    try:
                        # Try GSSAPI and continue if it fails
                        if 'AUTH=GSSAPI' in imapobj.capabilities and have_gss:
                            UIBase.getglobalui().debug('imap',
                                'Attempting GSSAPI authentication')
                            try:
                                imapobj.authenticate('GSSAPI', self.gssauth)
                            except imapobj.error, val:
                                self.gssapi = False
                                UIBase.getglobalui().debug('imap',
                                    'GSSAPI Authentication failed')
                            else:
                                self.gssapi = True
                                #if we do self.password = None then the next attempt cannot try...
                                #self.password = None

                        if not self.gssapi:
                            if 'AUTH=CRAM-MD5' in imapobj.capabilities:
                                UIBase.getglobalui().debug('imap',
                                                       'Attempting CRAM-MD5 authentication')
                                try:
                                    imapobj.authenticate('CRAM-MD5', self.md5handler)
                                except imapobj.error, val:
                                    self.plainauth(imapobj)
                            else:
                                self.plainauth(imapobj)
                        # Would bail by here if there was a failure.
                        success = 1
                        self.goodpassword = self.password
                    except imapobj.error, val:
                        self.passworderror = str(val)
                        raise
                        #self.password = None

            if self.delim == None:
                listres = imapobj.list(self.reference, '""')[1]
                if listres == [None] or listres == None:
                    # Some buggy IMAP servers do not respond well to LIST "" ""
                    # Work around them.
                    listres = imapobj.list(self.reference, '"*"')[1]
                self.delim, self.root = \
                            imaputil.imapsplit(listres[0])[1:]
                self.delim = imaputil.dequote(self.delim)
                self.root = imaputil.dequote(self.root)

            self.connectionlock.acquire()
            self.assignedconnections.append(imapobj)
            self.lastowner[imapobj] = thread.get_ident()
            self.connectionlock.release()
            return imapobj
        except:
            """If we are here then we did not succeed in getting a connection -
            we should clean up and then re-raise the error..."""
            self.semaphore.release()

            #Make sure that this can be retried the next time...
            self.passworderror = None
            if(self.connectionlock.locked()):
                self.connectionlock.release()
            raise
    
    def connectionwait(self):
        """Waits until there is a connection available.  Note that between
        the time that a connection becomes available and the time it is
        requested, another thread may have grabbed it.  This function is
        mainly present as a way to avoid spawning thousands of threads
        to copy messages, then have them all wait for 3 available connections.
        It's OK if we have maxconnections + 1 or 2 threads, which is what
        this will help us do."""
        threadutil.semaphorewait(self.semaphore)

    def close(self):
        # Make sure I own all the semaphores.  Let the threads finish
        # their stuff.  This is a blocking method.
        self.connectionlock.acquire()
        threadutil.semaphorereset(self.semaphore, self.maxconnections)
        for imapobj in self.assignedconnections + self.availableconnections:
            imapobj.logout()
        self.assignedconnections = []
        self.availableconnections = []
        self.lastowner = {}
        # reset kerberos state
        self.gss_step = self.GSS_STATE_STEP
        self.gss_vc = None
        self.gssapi = False
        self.connectionlock.release()

    def keepalive(self, timeout, event):
        """Sends a NOOP to each connection recorded.   It will wait a maximum
        of timeout seconds between doing this, and will continue to do so
        until the Event object as passed is true.  This method is expected
        to be invoked in a separate thread, which should be join()'d after
        the event is set."""
        ui = UIBase.getglobalui()
        ui.debug('imap', 'keepalive thread started')
        while 1:
            ui.debug('imap', 'keepalive: top of loop')
            time.sleep(timeout)
            ui.debug('imap', 'keepalive: after wait')
            if event.isSet():
                ui.debug('imap', 'keepalive: event is set; exiting')
                return
            ui.debug('imap', 'keepalive: acquiring connectionlock')
            self.connectionlock.acquire()
            numconnections = len(self.assignedconnections) + \
                             len(self.availableconnections)
            self.connectionlock.release()
            ui.debug('imap', 'keepalive: connectionlock released')
            threads = []
            imapobjs = []
        
            for i in range(numconnections):
                ui.debug('imap', 'keepalive: processing connection %d of %d' % (i, numconnections))
                imapobj = self.acquireconnection()
                ui.debug('imap', 'keepalive: connection %d acquired' % i)
                imapobjs.append(imapobj)
                thr = threadutil.ExitNotifyThread(target = imapobj.noop)
                thr.setDaemon(1)
                thr.start()
                threads.append(thr)
                ui.debug('imap', 'keepalive: thread started')

            ui.debug('imap', 'keepalive: joining threads')

            for thr in threads:
                # Make sure all the commands have completed.
                thr.join()

            ui.debug('imap', 'keepalive: releasing connections')

            for imapobj in imapobjs:
                self.releaseconnection(imapobj)

            ui.debug('imap', 'keepalive: bottom of loop')

class ConfigedIMAPServer(IMAPServer):
    """This class is designed for easier initialization given a ConfigParser
    object and an account name.  The passwordhash is used if
    passwords for certain accounts are known.  If the password for this
    account is listed, it will be obtained from there."""
    def __init__(self, repository, passwordhash = {}):
        """Initialize the object.  If the account is not a tunnel,
        the password is required."""
        self.repos = repository
        self.config = self.repos.getconfig()
        usetunnel = self.repos.getpreauthtunnel()
        if not usetunnel:
            host = self.repos.gethost()
            user = self.repos.getuser()
            port = self.repos.getport()
            ssl = self.repos.getssl()
            sslclientcert = self.repos.getsslclientcert()
            sslclientkey = self.repos.getsslclientkey()
        reference = self.repos.getreference()
        server = None
        password = None
        
        if repository.getname() in passwordhash:
            password = passwordhash[repository.getname()]

        # Connect to the remote server.
        if usetunnel:
            IMAPServer.__init__(self, self.config, self.repos.getname(),
                                tunnel = usetunnel,
                                reference = reference,
                                maxconnections = self.repos.getmaxconnections())
        else:
            if not password:
                password = self.repos.getpassword()
            IMAPServer.__init__(self, self.config, self.repos.getname(),
                                user, password, host, port, ssl,
                                self.repos.getmaxconnections(),
                                reference = reference,
                                sslclientcert = sslclientcert,
                                sslclientkey = sslclientkey)

########NEW FILE########
__FILENAME__ = imaputil
# IMAP utility module
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import re, string, types
from offlineimap.ui import UIBase
quotere = re.compile('^("(?:[^"]|\\\\")*")')

def debug(*args):
    msg = []
    for arg in args:
        msg.append(str(arg))
    UIBase.getglobalui().debug('imap', " ".join(msg))

def dequote(string):
    """Takes a string which may or may not be quoted and returns it, unquoted.
    This function does NOT consider parenthised lists to be quoted.
    """

    debug("dequote() called with input:", string)
    if not (string[0] == '"' and string[-1] == '"'):
        return string
    string = string[1:-1]               # Strip off quotes.
    string = string.replace('\\"', '"')
    string = string.replace('\\\\', '\\')
    debug("dequote() returning:", string)
    return string

def flagsplit(string):
    if string[0] != '(' or string[-1] != ')':
        raise ValueError, "Passed string '%s' is not a flag list" % string
    return imapsplit(string[1:-1])

def options2hash(list):
    debug("options2hash called with input:", list)
    retval = {}
    counter = 0
    while (counter < len(list)):
        retval[list[counter]] = list[counter + 1]
        counter += 2
    debug("options2hash returning:", retval)
    return retval

def flags2hash(string):
    return options2hash(flagsplit(string))

def imapsplit(imapstring):
    """Takes a string from an IMAP conversation and returns a list containing
    its components.  One example string is:

    (\\HasNoChildren) "." "INBOX.Sent"

    The result from parsing this will be:

    ['(\\HasNoChildren)', '"."', '"INBOX.Sent"']"""

    debug("imapsplit() called with input:", imapstring)
    if type(imapstring) != types.StringType:
        debug("imapsplit() got a non-string input; working around.")
        # Sometimes, imaplib will throw us a tuple if the input
        # contains a literal.  See Python bug
        # #619732 at https://sourceforge.net/tracker/index.php?func=detail&aid=619732&group_id=5470&atid=105470
        # One example is:
        # result[0] = '() "\\\\" Admin'
        # result[1] = ('() "\\\\" {19}', 'Folder\\2')
        #
        # This function will effectively get result[0] or result[1], so
        # if we get the result[1] version, we need to parse apart the tuple
        # and figure out what to do with it.  Each even-numbered
        # part of it should end with the {} number, and each odd-numbered
        # part should be directly a part of the result.  We'll
        # artificially quote it to help out.
        retval = []
        for i in range(len(imapstring)):
            if i % 2:                   # Odd: quote then append.
                arg = imapstring[i]
                # Quote code lifted from imaplib
                arg = arg.replace('\\', '\\\\')
                arg = arg.replace('"', '\\"')
                arg = '"%s"' % arg
                debug("imapsplit() non-string [%d]: Appending %s" %\
                      (i, arg))
                retval.append(arg)
            else:
                # Even -- we have a string that ends with a literal
                # size specifier.  We need to strip off that, then run
                # what remains through the regular imapsplit parser.
                # Recursion to the rescue.
                arg = imapstring[i]
                arg = re.sub('\{\d+\}$', '', arg)
                debug("imapsplit() non-string [%d]: Feeding %s to recursion" %\
                      (i, arg))
                retval.extend(imapsplit(arg))
        debug("imapsplit() non-string: returning %s" % str(retval))
        return retval
        
    workstr = imapstring.strip()
    retval = []
    while len(workstr):
        if workstr[0] == '(':
            rparenc = 1 # count of right parenthesis to match
            rpareni = 1 # position to examine
 	    while rparenc: # Find the end of the group.
 	    	if workstr[rpareni] == ')':  # end of a group
 			rparenc -= 1
 		elif workstr[rpareni] == '(':  # start of a group
 			rparenc += 1
 		rpareni += 1  # Move to next character.
            parenlist = workstr[0:rpareni]
            workstr = workstr[rpareni:].lstrip()
            retval.append(parenlist)
        elif workstr[0] == '"':
            quotelist = quotere.search(workstr).group(1)
            workstr = workstr[len(quotelist):].lstrip()
            retval.append(quotelist)
        else:
            splits = string.split(workstr, maxsplit = 1)
            splitslen = len(splits)
            # The unquoted word is splits[0]; the remainder is splits[1]
            if splitslen == 2:
                # There's an unquoted word, and more string follows.
                retval.append(splits[0])
                workstr = splits[1]    # split will have already lstripped it
                continue
            elif splitslen == 1:
                # We got a last unquoted word, but nothing else
                retval.append(splits[0])
                # Nothing remains.  workstr would be ''
                break
            elif splitslen == 0:
                # There was not even an unquoted word.
                break
    debug("imapsplit() returning:", retval)
    return retval
            
def flagsimap2maildir(flagstring):
    flagmap = {'\\seen': 'S',
               '\\answered': 'R',
               '\\flagged': 'F',
               '\\deleted': 'T',
               '\\draft': 'D'}
    retval = []
    imapflaglist = [x.lower() for x in flagstring[1:-1].split()]
    for imapflag in imapflaglist:
        if flagmap.has_key(imapflag):
            retval.append(flagmap[imapflag])
    retval.sort()
    return retval

def flagsmaildir2imap(list):
    flagmap = {'S': '\\Seen',
               'R': '\\Answered',
               'F': '\\Flagged',
               'T': '\\Deleted',
               'D': '\\Draft'}
    retval = []
    for mdflag in list:
        if flagmap.has_key(mdflag):
            retval.append(flagmap[mdflag])
    retval.sort()
    return '(' + ' '.join(retval) + ')'

def listjoin(list):
    start = None
    end = None
    retval = []

    def getlist(start, end):
        if start == end:
            return(str(start))
        else:
            return(str(start) + ":" + str(end))
        

    for item in list:
        if start == None:
            # First item.
            start = item
            end = item
        elif item == end + 1:
            # An addition to the list.
            end = item
        else:
            # Here on: starting a new list.
            retval.append(getlist(start, end))
            start = item
            end = item

    if start != None:
        retval.append(getlist(start, end))

    return ",".join(retval)



            
        

########NEW FILE########
__FILENAME__ = init
# OfflineIMAP initialization code
# Copyright (C) 2002-2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import imaplib
from offlineimap import imapserver, repository, folder, mbnames, threadutil, version, syncmaster, accounts
from offlineimap.localeval import LocalEval
from offlineimap.threadutil import InstanceLimitedThread, ExitNotifyThread
from offlineimap.ui import UIBase
import re, os, os.path, offlineimap, sys
from offlineimap.CustomConfig import CustomConfigParser
from threading import *
import threading, socket
from getopt import getopt
import signal

try:
    import fcntl
    hasfcntl = 1
except:
    hasfcntl = 0

lockfd = None

def lock(config, ui):
    global lockfd, hasfcntl
    if not hasfcntl:
        return
    lockfd = open(config.getmetadatadir() + "/lock", "w")
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        ui.locked()
        ui.terminate(1)

def startup(versionno):
    assert versionno == version.versionstr, "Revision of main program (%s) does not match that of library (%s).  Please double-check your PYTHONPATH and installation locations." % (versionno, version.versionstr)
    options = {}
    options['-k'] = []
    if '--help' in sys.argv[1:]:
        sys.stdout.write(version.getcmdhelp() + "\n")
        sys.exit(0)

    for optlist in getopt(sys.argv[1:], 'P:1oqa:c:d:l:u:hk:f:')[0]:
        if optlist[0] == '-k':
            options[optlist[0]].append(optlist[1])
        else:
            options[optlist[0]] = optlist[1]

    if options.has_key('-h'):
        sys.stdout.write(version.getcmdhelp())
        sys.stdout.write("\n")
        sys.exit(0)
    configfilename = os.path.expanduser("~/.offlineimaprc")
    if options.has_key('-c'):
        configfilename = options['-c']
    if options.has_key('-P'):
        if not options.has_key('-1'):
            sys.stderr.write("FATAL: profile mode REQUIRES -1\n")
            sys.exit(100)
        profiledir = options['-P']
        os.mkdir(profiledir)
        threadutil.setprofiledir(profiledir)
        sys.stderr.write("WARNING: profile mode engaged;\nPotentially large data will be created in " + profiledir + "\n")

    config = CustomConfigParser()
    if not os.path.exists(configfilename):
        sys.stderr.write(" *** Config file %s does not exist; aborting!\n" % configfilename)
        sys.exit(1)

    config.read(configfilename)

    # override config values with option '-k'
    for option in options['-k']:
        (key, value) = option.split('=', 1)
        if ':' in key:
            (secname, key) = key.split(':', 1)
            section = secname.replace("_", " ")
        else:
            section = "general"
        config.set(section, key, value)

    ui = offlineimap.ui.detector.findUI(config, options.get('-u'))
    UIBase.setglobalui(ui)

    if options.has_key('-l'):
        ui.setlogfd(open(options['-l'], 'wt'))

    ui.init_banner()

    if options.has_key('-d'):
        for debugtype in options['-d'].split(','):
            ui.add_debug(debugtype.strip())
            if debugtype == 'imap':
                imaplib.Debug = 5
            if debugtype == 'thread':
                threading._VERBOSE = 1

    if options.has_key('-o'):
        # FIXME: maybe need a better
        for section in accounts.getaccountlist(config):
            config.remove_option('Account ' + section, "autorefresh")

    if options.has_key('-q'):
        for section in accounts.getaccountlist(config):
            config.set('Account ' + section, "quick", '-1')

    if options.has_key('-f'):
        foldernames = options['-f'].replace(" ", "").split(",")
        folderfilter = "lambda f: f in %s" % foldernames
        folderincludes = "[]"
        for accountname in accounts.getaccountlist(config):
            account_section = 'Account ' + accountname
            remote_repo_section = 'Repository ' + \
                                  config.get(account_section, 'remoterepository')
            local_repo_section = 'Repository ' + \
                                 config.get(account_section, 'localrepository')
            for section in [remote_repo_section, local_repo_section]:
                config.set(section, "folderfilter", folderfilter)
                config.set(section, "folderincludes", folderincludes)

    lock(config, ui)

    def sigterm_handler(signum, frame):
        # die immediately
        ui.terminate(errormsg="terminating...")
    signal.signal(signal.SIGTERM,sigterm_handler)

    try:
        pidfd = open(config.getmetadatadir() + "/pid", "w")
        pidfd.write(str(os.getpid()) + "\n")
        pidfd.close()
    except:
        pass

    try:
        if options.has_key('-l'):
            sys.stderr = ui.logfile

        socktimeout = config.getdefaultint("general", "socktimeout", 0)
        if socktimeout > 0:
            socket.setdefaulttimeout(socktimeout)

        activeaccounts = config.get("general", "accounts")
        if options.has_key('-a'):
            activeaccounts = options['-a']
        activeaccounts = activeaccounts.replace(" ", "")
        activeaccounts = activeaccounts.split(",")
        allaccounts = accounts.AccountHashGenerator(config)

        syncaccounts = []
        for account in activeaccounts:
            if account not in allaccounts:
                if len(allaccounts) == 0:
                    errormsg = 'The account "%s" does not exist because no accounts are defined!'%account
                else:
                    errormsg = 'The account "%s" does not exist.  Valid accounts are:'%account
                    for name in allaccounts.keys():
                        errormsg += '\n%s'%name
                ui.terminate(1, errortitle = 'Unknown Account "%s"'%account, errormsg = errormsg)
            if account not in syncaccounts:
                syncaccounts.append(account)

        server = None
        remoterepos = None
        localrepos = None

        if options.has_key('-1'):
            threadutil.initInstanceLimit("ACCOUNTLIMIT", 1)
        else:
            threadutil.initInstanceLimit("ACCOUNTLIMIT",
                                         config.getdefaultint("general", "maxsyncaccounts", 1))

        for reposname in config.getsectionlist('Repository'):
            for instancename in ["FOLDER_" + reposname,
                                 "MSGCOPY_" + reposname]:
                if options.has_key('-1'):
                    threadutil.initInstanceLimit(instancename, 1)
                else:
                    threadutil.initInstanceLimit(instancename,
                                                 config.getdefaultint('Repository ' + reposname, "maxconnections", 1))
        siglisteners = []
        def sig_handler(signum, frame):
            if signum == signal.SIGUSR1:
                # tell each account to do a full sync asap
                signum = (1,)
            elif signum == signal.SIGHUP:
                # tell each account to die asap
                signum = (2,)
            elif signum == signal.SIGUSR2:
                # tell each account to do a full sync asap, then die
                signum = (1, 2)
            # one listener per account thread (up to maxsyncaccounts)
            for listener in siglisteners:
                for sig in signum:
                    listener.put_nowait(sig)
        signal.signal(signal.SIGHUP,sig_handler)
        signal.signal(signal.SIGUSR1,sig_handler)
        signal.signal(signal.SIGUSR2,sig_handler)

        threadutil.initexitnotify()
        t = ExitNotifyThread(target=syncmaster.syncitall,
                             name='Sync Runner',
                             kwargs = {'accounts': syncaccounts,
                                       'config': config,
                                       'siglisteners': siglisteners})
        t.setDaemon(1)
        t.start()
    except:
        ui.mainException()

    try:
        threadutil.exitnotifymonitorloop(threadutil.threadexited)
    except SystemExit:
        raise
    except:
        ui.mainException()                  # Also expected to terminate.

        

########NEW FILE########
__FILENAME__ = localeval
"""Eval python code with global namespace of a python source file."""

# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import imp
try:
    import errno
except:
    pass

class LocalEval:
    def __init__(self, path=None):
        self.namespace={}

        if path is not None:
            file=open(path, 'r')
            module=imp.load_module(
                '<none>',
                file,
                path,
                ('', 'r', imp.PY_SOURCE))
            for attr in dir(module):
                self.namespace[attr]=getattr(module, attr)

    def eval(self, text, namespace=None):
        names = {}
        names.update(self.namespace)
        if namespace is not None:
            names.update(namespace)
        return eval(text, names)

########NEW FILE########
__FILENAME__ = mbnames
# Mailbox name generator
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import os.path
import re                               # for folderfilter
from threading import *

boxes = {}
config = None
accounts = None
mblock = Lock()

def init(conf, accts):
    global config, accounts
    config = conf
    accounts = accts

def add(accountname, foldername):
    if not accountname in boxes:
        boxes[accountname] = []
    if not foldername in boxes[accountname]:
        boxes[accountname].append(foldername)

def write():
    # See if we're ready to write it out.
    for account in accounts:
        if account not in boxes:
            return

    genmbnames()

def genmbnames():
    """Takes a configparser object and a boxlist, which is a list of hashes
    containing 'accountname' and 'foldername' keys."""
    mblock.acquire()
    try:
        localeval = config.getlocaleval()
        if not config.getdefaultboolean("mbnames", "enabled", 0):
            return
        file = open(os.path.expanduser(config.get("mbnames", "filename")), "wt")
        file.write(localeval.eval(config.get("mbnames", "header")))
        folderfilter = lambda accountname, foldername: 1
        if config.has_option("mbnames", "folderfilter"):
            folderfilter = localeval.eval(config.get("mbnames", "folderfilter"),
                                          {'re': re})
        itemlist = []
        for accountname in boxes.keys():
            for foldername in boxes[accountname]:
                if folderfilter(accountname, foldername):
                    itemlist.append(config.get("mbnames", "peritem", raw=1) % \
                                    {'accountname': accountname,
                                     'foldername': foldername})
        file.write(localeval.eval(config.get("mbnames", "sep")).join(itemlist))
        file.write(localeval.eval(config.get("mbnames", "footer")))
        file.close()
    finally:
        mblock.release()
    
    

########NEW FILE########
__FILENAME__ = Base
# Base repository support
# Copyright (C) 2002-2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from offlineimap import CustomConfig
from offlineimap.ui import UIBase
import os.path
import sys

def LoadRepository(name, account, reqtype):
    from offlineimap.repository.Gmail import GmailRepository
    from offlineimap.repository.IMAP import IMAPRepository, MappedIMAPRepository
    from offlineimap.repository.Maildir import MaildirRepository
    if reqtype == 'remote':
        # For now, we don't support Maildirs on the remote side.
        typemap = {'IMAP': IMAPRepository,
                   'Gmail': GmailRepository}
    elif reqtype == 'local':
        typemap = {'IMAP': MappedIMAPRepository,
                   'Maildir': MaildirRepository}
    else:
        raise ValueError, "Request type %s not supported" % reqtype
    config = account.getconfig()
    repostype = config.get('Repository ' + name, 'type').strip()
    return typemap[repostype](name, account)

class BaseRepository(CustomConfig.ConfigHelperMixin):
    def __init__(self, reposname, account):
        self.account = account
        self.config = account.getconfig()
        self.name = reposname
        self.localeval = account.getlocaleval()
        self.accountname = self.account.getname()
        self.uiddir = os.path.join(self.config.getmetadatadir(), 'Repository-' + self.name)
        if not os.path.exists(self.uiddir):
            os.mkdir(self.uiddir, 0700)
        self.mapdir = os.path.join(self.uiddir, 'UIDMapping')
        if not os.path.exists(self.mapdir):
            os.mkdir(self.mapdir, 0700)
        self.uiddir = os.path.join(self.uiddir, 'FolderValidity')
        if not os.path.exists(self.uiddir):
            os.mkdir(self.uiddir, 0700)

    # The 'restoreatime' config parameter only applies to local Maildir
    # mailboxes.
    def restore_atime(self):
	if self.config.get('Repository ' + self.name, 'type').strip() != \
		'Maildir':
	    return

	if not self.config.has_option('Repository ' + self.name, 'restoreatime') or not self.config.getboolean('Repository ' + self.name, 'restoreatime'):
	    return

	return self.restore_folder_atimes()

    def connect(self):
        """Establish a connection to the remote, if necessary.  This exists
        so that IMAP connections can all be established up front, gathering
        passwords as needed.  It was added in order to support the
        error recovery -- we need to connect first outside of the error
        trap in order to validate the password, and that's the point of
        this function."""
        pass

    def holdordropconnections(self):
        pass

    def dropconnections(self):
        pass

    def getaccount(self):
        return self.account

    def getname(self):
        return self.name

    def getuiddir(self):
        return self.uiddir

    def getmapdir(self):
        return self.mapdir

    def getaccountname(self):
        return self.accountname

    def getsection(self):
        return 'Repository ' + self.name

    def getconfig(self):
        return self.config

    def getlocaleval(self):
        return self.account.getlocaleval()
    
    def getfolders(self):
        """Returns a list of ALL folders on this server."""
        return []

    def forgetfolders(self):
        """Forgets the cached list of folders, if any.  Useful to run
        after a sync run."""
        pass

    def getsep(self):
        raise NotImplementedError

    def makefolder(self, foldername):
        raise NotImplementedError

    def deletefolder(self, foldername):
        raise NotImplementedError

    def getfolder(self, foldername):
        raise NotImplementedError
    
    def syncfoldersto(self, dest, copyfolders):
        """Syncs the folders in this repository to those in dest.
        It does NOT sync the contents of those folders.

        For every time dest.makefolder() is called, also call makefolder()
        on each folder in copyfolders."""
        src = self
        srcfolders = src.getfolders()
        destfolders = dest.getfolders()

        # Create hashes with the names, but convert the source folders
        # to the dest folder's sep.

        srchash = {}
        for folder in srcfolders:
            srchash[folder.getvisiblename().replace(src.getsep(), dest.getsep())] = \
                                                           folder
        desthash = {}
        for folder in destfolders:
            desthash[folder.getvisiblename()] = folder

        #
        # Find new folders.
        #
        
        for key in srchash.keys():
            if not key in desthash:
                try:
                    dest.makefolder(key)
                    for copyfolder in copyfolders:
                        copyfolder.makefolder(key.replace(dest.getsep(), copyfolder.getsep()))
                except:
                    UIBase.getglobalui().warn("ERROR Attempting to make folder " \
                        + key + ":"  +str(sys.exc_info()[1]))
                

        #
        # Find deleted folders.
        #
        # We don't delete folders right now.

        #for key in desthash.keys():
        #    if not key in srchash:
        #        dest.deletefolder(key)
        
    ##### Keepalive

    def startkeepalive(self):
        """The default implementation will do nothing."""
        pass

    def stopkeepalive(self):
        """Stop keep alive, but don't bother waiting
        for the threads to terminate."""
        pass
    

########NEW FILE########
__FILENAME__ = Gmail
# Gmail IMAP repository support
# Copyright (C) 2008 Riccardo Murri <riccardo.murri@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from IMAP import IMAPRepository
from offlineimap import folder, imaputil
from offlineimap.imapserver import IMAPServer

class GmailRepository(IMAPRepository):
    """Gmail IMAP repository.

    Uses hard-coded host name and port, see:
      http://mail.google.com/support/bin/answer.py?answer=78799&topic=12814
    """

    #: Gmail IMAP server hostname
    HOSTNAME = "imap.gmail.com"

    #: Gmail IMAP server port
    PORT = 993
    
    def __init__(self, reposname, account):
        """Initialize a GmailRepository object."""
        account.getconfig().set('Repository ' + reposname,
                                'remotehost', GmailRepository.HOSTNAME)
        account.getconfig().set('Repository ' + reposname,
                                'remoteport', GmailRepository.PORT)
        account.getconfig().set('Repository ' + reposname,
                                'ssl', 'yes')
        IMAPRepository.__init__(self, reposname, account)

    def gethost(self):
        return GmailRepository.HOSTNAME

    def getport(self):
        return GmailRepository.PORT

    def getssl(self):
        return 1

    def getpreauthtunnel(self):
        return None

    def getfolder(self, foldername):
        return self.getfoldertype()(self.imapserver, foldername,
                                    self.nametrans(foldername),
                                    self.accountname, self)

    def getfoldertype(self):
        return folder.Gmail.GmailFolder

    def getrealdelete(self, foldername):
        # XXX: `foldername` is currently ignored - the `realdelete`
        # setting is repository-wide
        return self.getconfboolean('realdelete', 0)

    def gettrashfolder(self, foldername):
        #: Where deleted mail should be moved
        return  self.getconf('trashfolder','[Gmail]/Trash')
	
    def getspamfolder(self):
        #: Gmail also deletes messages upon EXPUNGE in the Spam folder
        return  self.getconf('spamfolder','[Gmail]/Spam')


########NEW FILE########
__FILENAME__ = IMAP
# IMAP repository support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Base import BaseRepository
from offlineimap import folder, imaputil, imapserver
from offlineimap.folder.UIDMaps import MappedIMAPFolder
from offlineimap.threadutil import ExitNotifyThread
import re, types, os, netrc, errno
from threading import *

class IMAPRepository(BaseRepository):
    def __init__(self, reposname, account):
        """Initialize an IMAPRepository object."""
        BaseRepository.__init__(self, reposname, account)
        self.imapserver = imapserver.ConfigedIMAPServer(self)
        self.folders = None
        self.nametrans = lambda foldername: foldername
        self.folderfilter = lambda foldername: 1
        self.folderincludes = []
        self.foldersort = cmp
        localeval = self.localeval
        if self.config.has_option(self.getsection(), 'nametrans'):
            self.nametrans = localeval.eval(self.getconf('nametrans'),
                                            {'re': re})
        if self.config.has_option(self.getsection(), 'folderfilter'):
            self.folderfilter = localeval.eval(self.getconf('folderfilter'),
                                               {'re': re})
        if self.config.has_option(self.getsection(), 'folderincludes'):
            self.folderincludes = localeval.eval(self.getconf('folderincludes'),
                                                 {'re': re})
        if self.config.has_option(self.getsection(), 'foldersort'):
            self.foldersort = localeval.eval(self.getconf('foldersort'),
                                             {'re': re})

    def startkeepalive(self):
        keepalivetime = self.getkeepalive()
        if not keepalivetime: return
        self.kaevent = Event()
        self.kathread = ExitNotifyThread(target = self.imapserver.keepalive,
                                         name = "Keep alive " + self.getname(),
                                         args = (keepalivetime, self.kaevent))
        self.kathread.setDaemon(1)
        self.kathread.start()

    def stopkeepalive(self):
        if not hasattr(self, 'kaevent'):
            # Keepalive is not active.
            return

        self.kaevent.set()
        del self.kathread
        del self.kaevent

    def holdordropconnections(self):
        if not self.getholdconnectionopen():
            self.dropconnections()

    def dropconnections(self):
        self.imapserver.close()

    def getholdconnectionopen(self):
        return self.getconfboolean("holdconnectionopen", 0)

    def getkeepalive(self):
        return self.getconfint("keepalive", 0)

    def getsep(self):
        return self.imapserver.delim

    def gethost(self):
        host = None
        localeval = self.localeval

        if self.config.has_option(self.getsection(), 'remotehosteval'):
            host = self.getconf('remotehosteval')
        if host != None:
            return localeval.eval(host)

        host = self.getconf('remotehost')
        if host != None:
            return host

    def getuser(self):
        user = None
        localeval = self.localeval

        if self.config.has_option(self.getsection(), 'remoteusereval'):
            user = self.getconf('remoteusereval')
        if user != None:
            return localeval.eval(user)

        user = self.getconf('remoteuser')
        if user != None:
            return user

        try:
            netrcentry = netrc.netrc().authenticators(self.gethost())
        except IOError, inst:
            if inst.errno != errno.ENOENT:
                raise
        else:
            if netrcentry:
                return netrcentry[0]

        try:
            netrcentry = netrc.netrc('/etc/netrc').authenticators(self.gethost())
        except IOError, inst:
            if inst.errno != errno.ENOENT:
                raise
        else:
            if netrcentry:
                return netrcentry[0]


    def getport(self):
        return self.getconfint('remoteport', None)

    def getssl(self):
        return self.getconfboolean('ssl', 0)

    def getsslclientcert(self):
        return self.getconf('sslclientcert', None)

    def getsslclientkey(self):
        return self.getconf('sslclientkey', None)

    def getpreauthtunnel(self):
        return self.getconf('preauthtunnel', None)

    def getreference(self):
        return self.getconf('reference', '""')

    def getmaxconnections(self):
        return self.getconfint('maxconnections', 1)

    def getexpunge(self):
        return self.getconfboolean('expunge', 1)

    def getpassword(self):
        passwd = None
        localeval = self.localeval

        if self.config.has_option(self.getsection(), 'remotepasseval'):
            passwd = self.getconf('remotepasseval')
        if passwd != None:
            return localeval.eval(passwd)

        password = self.getconf('remotepass', None)
        if password != None:
            return password
        passfile = self.getconf('remotepassfile', None)
        if passfile != None:
            fd = open(os.path.expanduser(passfile))
            password = fd.readline().strip()
            fd.close()
            return password

        try:
            netrcentry = netrc.netrc().authenticators(self.gethost())
        except IOError, inst:
            if inst.errno != errno.ENOENT:
                raise
        else:
            if netrcentry:
                user = self.getconf('remoteuser')
                if user == None or user == netrcentry[0]:
                    return netrcentry[2]
        try:
            netrcentry = netrc.netrc('/etc/netrc').authenticators(self.gethost())
        except IOError, inst:
            if inst.errno != errno.ENOENT:
                raise
        else:
            if netrcentry:
                user = self.getconf('remoteuser')
                if user == None or user == netrcentry[0]:
                    return netrcentry[2]
        return None

    def getfolder(self, foldername):
        return self.getfoldertype()(self.imapserver, foldername,
                                    self.nametrans(foldername),
                                    self.accountname, self)

    def getfoldertype(self):
        return folder.IMAP.IMAPFolder

    def connect(self):
        imapobj = self.imapserver.acquireconnection()
        self.imapserver.releaseconnection(imapobj)

    def forgetfolders(self):
        self.folders = None

    def getfolders(self):
        if self.folders != None:
            return self.folders
        retval = []
        imapobj = self.imapserver.acquireconnection()
        # check whether to list all folders, or subscribed only
        listfunction = imapobj.list
        if self.config.has_option(self.getsection(), 'subscribedonly'):
          if self.getconf('subscribedonly') == "yes":
            listfunction = imapobj.lsub
        try:
            listresult = listfunction(directory = self.imapserver.reference)[1]
        finally:
            self.imapserver.releaseconnection(imapobj)
        for string in listresult:
            if string == None or \
                   (type(string) == types.StringType and string == ''):
                # Bug in imaplib: empty strings in results from
                # literals.
                continue
            flags, delim, name = imaputil.imapsplit(string)
            flaglist = [x.lower() for x in imaputil.flagsplit(flags)]
            if '\\noselect' in flaglist:
                continue
            foldername = imaputil.dequote(name)
            if not self.folderfilter(foldername):
                continue
            retval.append(self.getfoldertype()(self.imapserver, foldername,
                                               self.nametrans(foldername),
                                               self.accountname, self))
        if len(self.folderincludes):
            imapobj = self.imapserver.acquireconnection()
            try:
                for foldername in self.folderincludes:
                    try:
                        imapobj.select(foldername, readonly = 1)
                    except ValueError:
                        continue
                    retval.append(self.getfoldertype()(self.imapserver,
                                                       foldername,
                                                       self.nametrans(foldername),
                                                       self.accountname, self))
            finally:
                self.imapserver.releaseconnection(imapobj)
                
        retval.sort(lambda x, y: self.foldersort(x.getvisiblename(), y.getvisiblename()))
        self.folders = retval
        return retval

    def makefolder(self, foldername):
        #if self.getreference() != '""':
        #    newname = self.getreference() + self.getsep() + foldername
        #else:
        #    newname = foldername
        newname = foldername
        imapobj = self.imapserver.acquireconnection()
        try:
            result = imapobj.create(newname)
            if result[0] != 'OK':
                raise RuntimeError, "Repository %s could not create folder %s: %s" % (self.getname(), foldername, str(result))
        finally:
            self.imapserver.releaseconnection(imapobj)
            
class MappedIMAPRepository(IMAPRepository):
    def getfoldertype(self):
        return MappedIMAPFolder

########NEW FILE########
__FILENAME__ = LocalStatus
# Local status cache repository support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Base import BaseRepository
from offlineimap import folder
import offlineimap.folder.LocalStatus
import os, re

class LocalStatusRepository(BaseRepository):
    def __init__(self, reposname, account):
        BaseRepository.__init__(self, reposname, account)
        self.directory = os.path.join(account.getaccountmeta(), 'LocalStatus')
        if not os.path.exists(self.directory):
            os.mkdir(self.directory, 0700)
        self.folders = None

    def getsep(self):
        return '.'

    def getfolderfilename(self, foldername):
        foldername = re.sub('/\.$', '/dot', foldername)
        foldername = re.sub('^\.$', 'dot', foldername)
        return os.path.join(self.directory, foldername)

    def makefolder(self, foldername):
        # "touch" the file, truncating it.
        filename = self.getfolderfilename(foldername)
        file = open(filename + ".tmp", "wt")
        file.write(offlineimap.folder.LocalStatus.magicline + '\n')
        file.flush()
        os.fsync(file.fileno())
        file.close()
        os.rename(filename + ".tmp", filename)
        
        # Invalidate the cache.
        self.folders = None

    def getfolders(self):
        retval = []
        for folder in os.listdir(self.directory):
            retval.append(folder.LocalStatus.LocalStatusFolder(self.directory,
                                                               folder, self, self.accountname, 
                                                               self.config))
        return retval

    def getfolder(self, foldername):
        return folder.LocalStatus.LocalStatusFolder(self.directory, foldername,
                                                    self, self.accountname,
                                                    self.config)


    

    

########NEW FILE########
__FILENAME__ = Maildir
# Maildir repository support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Base import BaseRepository
from offlineimap import folder, imaputil
from offlineimap.ui import UIBase
from mailbox import Maildir
import os
from stat import *

class MaildirRepository(BaseRepository):
    def __init__(self, reposname, account):
        """Initialize a MaildirRepository object.  Takes a path name
        to the directory holding all the Maildir directories."""
        BaseRepository.__init__(self, reposname, account)

        self.root = self.getlocalroot()
        self.folders = None
        self.ui = UIBase.getglobalui()
        self.debug("MaildirRepository initialized, sep is " + repr(self.getsep()))
	self.folder_atimes = []

        # Create the top-level folder if it doesn't exist
        if not os.path.isdir(self.root):
            os.mkdir(self.root, 0700)

    def _append_folder_atimes(self, foldername):
	p = os.path.join(self.root, foldername)
	new = os.path.join(p, 'new')
	cur = os.path.join(p, 'cur')
	f = p, os.stat(new)[ST_ATIME], os.stat(cur)[ST_ATIME]
	self.folder_atimes.append(f)

    def restore_folder_atimes(self):
	if not self.folder_atimes:
	    return

	for f in self.folder_atimes:
	    t = f[1], os.stat(os.path.join(f[0], 'new'))[ST_MTIME]
	    os.utime(os.path.join(f[0], 'new'), t)
	    t = f[2], os.stat(os.path.join(f[0], 'cur'))[ST_MTIME]
	    os.utime(os.path.join(f[0], 'cur'), t)

    def getlocalroot(self):
        return os.path.expanduser(self.getconf('localfolders'))

    def debug(self, msg):
        self.ui.debug('maildir', msg)

    def getsep(self):
        return self.getconf('sep', '.').strip()

    def makefolder(self, foldername):
        self.debug("makefolder called with arg " + repr(foldername))
        # Do the chdir thing so the call to makedirs does not make the
        # self.root directory (we'd prefer to raise an error in that case),
        # but will make the (relative) paths underneath it.  Need to use
        # makedirs to support a / separator.
        self.debug("Is dir? " + repr(os.path.isdir(foldername)))
        if self.getsep() == '/':
            for invalid in ['new', 'cur', 'tmp', 'offlineimap.uidvalidity']:
                for component in foldername.split('/'):
                    assert component != invalid, "When using nested folders (/ as a separator in the account config), your folder names may not contain 'new', 'cur', 'tmp', or 'offlineimap.uidvalidity'."

        assert foldername.find('./') == -1, "Folder names may not contain ../"
        assert not foldername.startswith('/'), "Folder names may not begin with /"

        oldcwd = os.getcwd()
        os.chdir(self.root)

        # If we're using hierarchical folders, it's possible that sub-folders
        # may be created before higher-up ones.  If this is the case,
        # makedirs will fail because the higher-up dir already exists.
        # So, check to see if this is indeed the case.

        if (self.getsep() == '/' or self.getconfboolean('existsok', 0) or foldername == '.') \
            and os.path.isdir(foldername):
            self.debug("makefolder: %s already is a directory" % foldername)
            # Already exists.  Sanity-check that it's not a Maildir.
            for subdir in ['cur', 'new', 'tmp']:
                assert not os.path.isdir(os.path.join(foldername, subdir)), \
                       "Tried to create folder %s but it already had dir %s" %\
                       (foldername, subdir)
        else:
            self.debug("makefolder: calling makedirs %s" % foldername)
            os.makedirs(foldername, 0700)
        self.debug("makefolder: creating cur, new, tmp")
        for subdir in ['cur', 'new', 'tmp']:
            os.mkdir(os.path.join(foldername, subdir), 0700)
        # Invalidate the cache
        self.folders = None
        os.chdir(oldcwd)

    def deletefolder(self, foldername):
        self.ui.warn("NOT YET IMPLEMENTED: DELETE FOLDER %s" % foldername)

    def getfolder(self, foldername):
	if self.config.has_option('Repository ' + self.name, 'restoreatime') and self.config.getboolean('Repository ' + self.name, 'restoreatime'):
	    self._append_folder_atimes(foldername)
        return folder.Maildir.MaildirFolder(self.root, foldername,
                                            self.getsep(), self, 
                                            self.accountname, self.config)
    
    def _getfolders_scandir(self, root, extension = None):
        self.debug("_GETFOLDERS_SCANDIR STARTING. root = %s, extension = %s" \
                   % (root, extension))
        # extension willl only be non-None when called recursively when
        # getsep() returns '/'.
        retval = []

        # Configure the full path to this repository -- "toppath"

        if extension == None:
            toppath = root
        else:
            toppath = os.path.join(root, extension)

        self.debug("  toppath = %s" % toppath)

        # Iterate over directories in top.
        for dirname in os.listdir(toppath) + ['.']:
            self.debug("  *** top of loop")
            self.debug("  dirname = %s" % dirname)
            if dirname in ['cur', 'new', 'tmp', 'offlineimap.uidvalidity']:
                self.debug("  skipping this dir (Maildir special)")
                # Bypass special files.
                continue
            fullname = os.path.join(toppath, dirname)
            self.debug("  fullname = %s" % fullname)
            if not os.path.isdir(fullname):
                self.debug("  skipping this entry (not a directory)")
                # Not a directory -- not a folder.
                continue
            foldername = dirname
            if extension != None:
                foldername = os.path.join(extension, dirname)
            if (os.path.isdir(os.path.join(fullname, 'cur')) and
                os.path.isdir(os.path.join(fullname, 'new')) and
                os.path.isdir(os.path.join(fullname, 'tmp'))):
                # This directory has maildir stuff -- process
                self.debug("  This is a maildir folder.")

                self.debug("  foldername = %s" % foldername)

		if self.config.has_option('Repository ' + self.name, 'restoreatime') and self.config.getboolean('Repository ' + self.name, 'restoreatime'):
		    self._append_folder_atimes(foldername)
                retval.append(folder.Maildir.MaildirFolder(self.root, foldername,
                                                           self.getsep(), self, self.accountname,
                                                           self.config))
            if self.getsep() == '/' and dirname != '.':
                # Check sub-directories for folders.
                retval.extend(self._getfolders_scandir(root, foldername))
        self.debug("_GETFOLDERS_SCANDIR RETURNING %s" % \
                   repr([x.getname() for x in retval]))
        return retval
    
    def getfolders(self):
        if self.folders == None:
            self.folders = self._getfolders_scandir(self.root)
        return self.folders
    

########NEW FILE########
__FILENAME__ = syncmaster
# OfflineIMAP synchronization master code
# Copyright (C) 2002-2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import imaplib
from offlineimap import imapserver, repository, folder, mbnames, threadutil, version
from offlineimap.threadutil import InstanceLimitedThread, ExitNotifyThread
import offlineimap.accounts
from offlineimap.accounts import SyncableAccount, SigListener
from offlineimap.ui import UIBase
import re, os, os.path, offlineimap, sys
from ConfigParser import ConfigParser
from threading import *

def syncaccount(threads, config, accountname, siglisteners):
    account = SyncableAccount(config, accountname)
    siglistener = SigListener()
    thread = InstanceLimitedThread(instancename = 'ACCOUNTLIMIT',
                                   target = account.syncrunner,
                                   name = "Account sync %s" % accountname,
                                   kwargs = {'siglistener': siglistener} )
    # the Sync Runner thread is the only one that will mutate siglisteners
    siglisteners.append(siglistener)
    thread.setDaemon(1)
    thread.start()
    threads.add(thread)
    
def syncitall(accounts, config, siglisteners):
    currentThread().setExitMessage('SYNC_WITH_TIMER_TERMINATE')
    ui = UIBase.getglobalui()
    threads = threadutil.threadlist()
    mbnames.init(config, accounts)
    for accountname in accounts:
        syncaccount(threads, config, accountname, siglisteners)
    # Wait for the threads to finish.
    threads.reset()

########NEW FILE########
__FILENAME__ = threadutil
# Copyright (C) 2002, 2003 John Goerzen
# Thread support module
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
from StringIO import StringIO
from Queue import Queue, Empty
import sys, traceback, thread, time
from offlineimap.ui import UIBase       # for getglobalui()

profiledir = None

def setprofiledir(newdir):
    global profiledir
    profiledir = newdir

######################################################################
# General utilities
######################################################################

def semaphorereset(semaphore, originalstate):
    """Wait until the semaphore gets back to its original state -- all acquired
    resources released."""
    for i in range(originalstate):
        semaphore.acquire()
    # Now release these.
    for i in range(originalstate):
        semaphore.release()
        
def semaphorewait(semaphore):
    semaphore.acquire()
    semaphore.release()
    
def threadsreset(threadlist):
    for thr in threadlist:
        thr.join()

class threadlist:
    def __init__(self):
        self.lock = Lock()
        self.list = []

    def add(self, thread):
        self.lock.acquire()
        try:
            self.list.append(thread)
        finally:
            self.lock.release()

    def remove(self, thread):
        self.lock.acquire()
        try:
            self.list.remove(thread)
        finally:
            self.lock.release()

    def pop(self):
        self.lock.acquire()
        try:
            if not len(self.list):
                return None
            return self.list.pop()
        finally:
            self.lock.release()

    def reset(self):
        while 1:
            thread = self.pop()
            if not thread:
                return
            thread.join()
            

######################################################################
# Exit-notify threads
######################################################################

exitthreads = Queue(100)
inited = 0

def initexitnotify():
    """Initialize the exit notify system.  This MUST be called from the
    SAME THREAD that will call monitorloop BEFORE it calls monitorloop.
    This SHOULD be called before the main thread starts any other
    ExitNotifyThreads, or else it may miss the ability to catch the exit
    status from them!"""
    pass

def exitnotifymonitorloop(callback):
    """Enter an infinite "monitoring" loop.  The argument, callback,
    defines the function to call when an ExitNotifyThread has terminated.
    That function is called with a single argument -- the ExitNotifyThread
    that has terminated.  The monitor will not continue to monitor for
    other threads until the function returns, so if it intends to perform
    long calculations, it should start a new thread itself -- but NOT
    an ExitNotifyThread, or else an infinite loop may result.  Furthermore,
    the monitor will hold the lock all the while the other thread is waiting.
    """
    global exitthreads
    while 1:                            # Loop forever.
        try:
            thrd = exitthreads.get(False)
            callback(thrd)
        except Empty:
            time.sleep(1)

def threadexited(thread):
    """Called when a thread exits."""
    ui = UIBase.getglobalui()
    if thread.getExitCause() == 'EXCEPTION':
        if isinstance(thread.getExitException(), SystemExit):
            # Bring a SystemExit into the main thread.
            # Do not send it back to UI layer right now.
            # Maybe later send it to ui.terminate?
            raise SystemExit
        ui.threadException(thread)      # Expected to terminate
        sys.exit(100)                   # Just in case...
        os._exit(100)
    elif thread.getExitMessage() == 'SYNC_WITH_TIMER_TERMINATE':
        ui.terminate()
        # Just in case...
        sys.exit(100)
        os._exit(100)
    else:
        ui.threadExited(thread)

class ExitNotifyThread(Thread):
    """This class is designed to alert a "monitor" to the fact that a thread has
    exited and to provide for the ability for it to find out why."""
    def run(self):
        global exitthreads, profiledir
        self.threadid = thread.get_ident()
        try:
            if not profiledir:          # normal case
                Thread.run(self)
            else:
                import profile
                prof = profile.Profile()
                try:
                    prof = prof.runctx("Thread.run(self)", globals(), locals())
                except SystemExit:
                    pass
                prof.dump_stats( \
                            profiledir + "/" + str(self.threadid) + "_" + \
                            self.getName() + ".prof")
        except:
            self.setExitCause('EXCEPTION')
            if sys:
                self.setExitException(sys.exc_info()[1])
                sbuf = StringIO()
                traceback.print_exc(file = sbuf)
                self.setExitStackTrace(sbuf.getvalue())
        else:
            self.setExitCause('NORMAL')
        if not hasattr(self, 'exitmessage'):
            self.setExitMessage(None)

        if exitthreads:
            exitthreads.put(self, True)

    def setExitCause(self, cause):
        self.exitcause = cause
    def getExitCause(self):
        """Returns the cause of the exit, one of:
        'EXCEPTION' -- the thread aborted because of an exception
        'NORMAL' -- normal termination."""
        return self.exitcause
    def setExitException(self, exc):
        self.exitexception = exc
    def getExitException(self):
        """If getExitCause() is 'EXCEPTION', holds the value from
        sys.exc_info()[1] for this exception."""
        return self.exitexception
    def setExitStackTrace(self, st):
        self.exitstacktrace = st
    def getExitStackTrace(self):
        """If getExitCause() is 'EXCEPTION', returns a string representing
        the stack trace for this exception."""
        return self.exitstacktrace
    def setExitMessage(self, msg):
        """Sets the exit message to be fetched by a subsequent call to
        getExitMessage.  This message may be any object or type except
        None."""
        self.exitmessage = msg
    def getExitMessage(self):
        """For any exit cause, returns the message previously set by
        a call to setExitMessage(), or None if there was no such message
        set."""
        return self.exitmessage
            

######################################################################
# Instance-limited threads
######################################################################

instancelimitedsems = {}
instancelimitedlock = Lock()

def initInstanceLimit(instancename, instancemax):
    """Initialize the instance-limited thread implementation to permit
    up to intancemax threads with the given instancename."""
    instancelimitedlock.acquire()
    if not instancelimitedsems.has_key(instancename):
        instancelimitedsems[instancename] = BoundedSemaphore(instancemax)
    instancelimitedlock.release()

class InstanceLimitedThread(ExitNotifyThread):
    def __init__(self, instancename, *args, **kwargs):
        self.instancename = instancename
                                                   
        apply(ExitNotifyThread.__init__, (self,) + args, kwargs)

    def start(self):
        instancelimitedsems[self.instancename].acquire()
        ExitNotifyThread.start(self)
        
    def run(self):
        try:
            ExitNotifyThread.run(self)
        finally:
            if instancelimitedsems and instancelimitedsems[self.instancename]:
                instancelimitedsems[self.instancename].release()
        
    
######################################################################
# Multi-lock -- capable of handling a single thread requesting a lock
# multiple times
######################################################################

class MultiLock:
    def __init__(self):
        self.lock = Lock()
        self.statuslock = Lock()
        self.locksheld = {}

    def acquire(self):
        """Obtain a lock.  Provides nice support for a single
        thread trying to lock it several times -- as may be the case
        if one I/O-using object calls others, while wanting to make it all
        an atomic operation.  Keeps a "lock request count" for the current
        thread, and acquires the lock when it goes above zero, releases when
        it goes below one.

        This call is always blocking."""
        
        # First, check to see if this thread already has a lock.
        # If so, increment the lock count and just return.
        self.statuslock.acquire()
        try:
            threadid = thread.get_ident()

            if threadid in self.locksheld:
                self.locksheld[threadid] += 1
                return
            else:
                # This is safe because it is a per-thread structure
                self.locksheld[threadid] = 1
        finally:
            self.statuslock.release()
        self.lock.acquire()

    def release(self):
        self.statuslock.acquire()
        try:
            threadid = thread.get_ident()
            if self.locksheld[threadid] > 1:
                self.locksheld[threadid] -= 1
                return
            else:
                del self.locksheld[threadid]
                self.lock.release()
        finally:
            self.statuslock.release()

        

########NEW FILE########
__FILENAME__ = Blinkenlights
# Blinkenlights base classes
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
from offlineimap.ui.UIBase import UIBase
import thread
from offlineimap.threadutil import MultiLock

class BlinkenBase:
    """This is a mix-in class that should be mixed in with either UIBase
    or another appropriate base class.  The Tk interface, for instance,
    will probably mix it in with VerboseUI."""

    def acct(s, accountname):
        s.gettf().setcolor('purple')
        s.__class__.__bases__[-1].acct(s, accountname)

    def connecting(s, hostname, port):
        s.gettf().setcolor('gray')
        s.__class__.__bases__[-1].connecting(s, hostname, port)

    def syncfolders(s, srcrepos, destrepos):
        s.gettf().setcolor('blue')
        s.__class__.__bases__[-1].syncfolders(s, srcrepos, destrepos)

    def syncingfolder(s, srcrepos, srcfolder, destrepos, destfolder):
        s.gettf().setcolor('cyan')
        s.__class__.__bases__[-1].syncingfolder(s, srcrepos, srcfolder, destrepos, destfolder)

    def skippingfolder(s, folder):
        s.gettf().setcolor('cyan')
        s.__class__.__bases__[-1].skippingfolder(s, folder)

    def loadmessagelist(s, repos, folder):
        s.gettf().setcolor('green')
        s._msg("Scanning folder [%s/%s]" % (s.getnicename(repos),
                                            folder.getvisiblename()))

    def syncingmessages(s, sr, sf, dr, df):
        s.gettf().setcolor('blue')
        s.__class__.__bases__[-1].syncingmessages(s, sr, sf, dr, df)

    def copyingmessage(s, uid, src, destlist):
        s.gettf().setcolor('orange')
        s.__class__.__bases__[-1].copyingmessage(s, uid, src, destlist)

    def deletingmessages(s, uidlist, destlist):
        s.gettf().setcolor('red')
        s.__class__.__bases__[-1].deletingmessages(s, uidlist, destlist)

    def deletingmessage(s, uid, destlist):
        s.gettf().setcolor('red')
        s.__class__.__bases__[-1].deletingmessage(s, uid, destlist)

    def addingflags(s, uidlist, flags, destlist):
        s.gettf().setcolor('yellow')
        s.__class__.__bases__[-1].addingflags(s, uidlist, flags, destlist)

    def deletingflags(s, uidlist, flags, destlist):
        s.gettf().setcolor('pink')
        s.__class__.__bases__[-1].deletingflags(s, uidlist, flags, destlist)

    def warn(s, msg, minor = 0):
        if minor:
            s.gettf().setcolor('pink')
        else:
            s.gettf().setcolor('red')
        s.__class__.__bases__[-1].warn(s, msg, minor)

    def init_banner(s):
        s.availablethreadframes = {}
        s.threadframes = {}
        s.tflock = MultiLock()

    def threadExited(s, thread):
        threadid = thread.threadid
        accountname = s.getthreadaccount(thread)
        s.tflock.acquire()
        try:
            if threadid in s.threadframes[accountname]:
                tf = s.threadframes[accountname][threadid]
                del s.threadframes[accountname][threadid]
                s.availablethreadframes[accountname].append(tf)
                tf.setthread(None)
        finally:
            s.tflock.release()

        UIBase.threadExited(s, thread)

    def gettf(s):
        threadid = thread.get_ident()
        accountname = s.getthreadaccount()

        s.tflock.acquire()

        try:
            if not accountname in s.threadframes:
                s.threadframes[accountname] = {}
                
            if threadid in s.threadframes[accountname]:
                return s.threadframes[accountname][threadid]

            if not accountname in s.availablethreadframes:
                s.availablethreadframes[accountname] = []

            if len(s.availablethreadframes[accountname]):
                tf = s.availablethreadframes[accountname].pop(0)
                tf.setthread(currentThread())
            else:
                tf = s.getaccountframe().getnewthreadframe()
            s.threadframes[accountname][threadid] = tf
            return tf
        finally:
            s.tflock.release()

    def callhook(s, msg):
        s.gettf().setcolor('white')
        s.__class__.__bases__[-1].callhook(s, msg)
            
    def sleep(s, sleepsecs, siglistener):
        s.gettf().setcolor('red')
        s.getaccountframe().startsleep(sleepsecs)
        return UIBase.sleep(s, sleepsecs, siglistener)

    def sleeping(s, sleepsecs, remainingsecs):
        if remainingsecs and s.gettf().getcolor() == 'black':
            s.gettf().setcolor('red')
        else:
            s.gettf().setcolor('black')
        return s.getaccountframe().sleeping(sleepsecs, remainingsecs)

    

########NEW FILE########
__FILENAME__ = Curses
# Curses-based interfaces
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from Blinkenlights import BlinkenBase
from UIBase import UIBase
from threading import *
import thread, time, sys, os, signal, time
from offlineimap import version, threadutil
from offlineimap.threadutil import MultiLock

import curses, curses.panel, curses.textpad, curses.wrapper

acctkeys = '1234567890abcdefghijklmnoprstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-=;/.,'

class CursesUtil:
    def __init__(self):
        self.pairlock = Lock()
        self.iolock = MultiLock()
        self.start()

    def initpairs(self):
        self.pairlock.acquire()
        try:
            self.pairs = {self._getpairindex(curses.COLOR_WHITE,
                                             curses.COLOR_BLACK): 0}
            self.nextpair = 1
        finally:
            self.pairlock.release()

    def lock(self):
        self.iolock.acquire()

    def unlock(self):
        self.iolock.release()
        
    def locked(self, target, *args, **kwargs):
        """Perform an operation with full locking."""
        self.lock()
        try:
            apply(target, args, kwargs)
        finally:
            self.unlock()

    def refresh(self):
        def lockedstuff():
            curses.panel.update_panels()
            curses.doupdate()
        self.locked(lockedstuff)

    def isactive(self):
        return hasattr(self, 'stdscr')

    def _getpairindex(self, fg, bg):
        return '%d/%d' % (fg,bg)

    def getpair(self, fg, bg):
        if not self.has_color:
            return 0
        pindex = self._getpairindex(fg, bg)
        self.pairlock.acquire()
        try:
            if self.pairs.has_key(pindex):
                return curses.color_pair(self.pairs[pindex])
            else:
                self.pairs[pindex] = self.nextpair
                curses.init_pair(self.nextpair, fg, bg)
                self.nextpair += 1
                return curses.color_pair(self.nextpair - 1)
        finally:
            self.pairlock.release()
    
    def start(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        try:
            curses.start_color()
            self.has_color = curses.has_colors()
        except:
            self.has_color = 0

        self.oldcursor = None
        try:
            self.oldcursor = curses.curs_set(0)
        except:
            pass
        
        self.stdscr.clear()
        self.stdscr.refresh()
        (self.height, self.width) = self.stdscr.getmaxyx()
        self.initpairs()

    def stop(self):
        if not hasattr(self, 'stdscr'):
            return
        #self.stdscr.addstr(self.height - 1, 0, "\n",
        #                   self.getpair(curses.COLOR_WHITE,
        #                                curses.COLOR_BLACK))
        if self.oldcursor != None:
            curses.curs_set(self.oldcursor)
        self.stdscr.refresh()
        self.stdscr.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        del self.stdscr

    def reset(self):
        # dirty walkaround for bug http://bugs.python.org/issue7567 in python 2.6 to 2.6.5 (fixed since #83743)
        if (sys.version_info[0:3] >= (2,6) and  sys.version_info[0:3] <= (2,6,5)): return
        self.stop()
        self.start()

class CursesAccountFrame:
    def __init__(s, master, accountname, ui):
        s.c = master
        s.children = []
        s.accountname = accountname
        s.ui = ui

    def drawleadstr(s, secs = None):
        if secs == None:
            acctstr = '%s: [active] %13.13s: ' % (s.key, s.accountname)
        else:
            acctstr = '%s: [%3d:%02d] %13.13s: ' % (s.key,
                                                    secs / 60, secs % 60,
                                                    s.accountname)
        s.c.locked(s.window.addstr, 0, 0, acctstr)
        s.location = len(acctstr)

    def setwindow(s, window, key):
        s.window = window
        s.key = key
        s.drawleadstr()
        for child in s.children:
            child.update(window, 0, s.location)
            s.location += 1

    def getnewthreadframe(s):
        tf = CursesThreadFrame(s.c, s.ui, s.window, 0, s.location)
        s.location += 1
        s.children.append(tf)
        return tf

    def startsleep(s, sleepsecs):
        s.sleeping_abort = 0

    def sleeping(s, sleepsecs, remainingsecs):
        if remainingsecs:
            s.c.lock()
            try:
                s.drawleadstr(remainingsecs)
                s.window.refresh()
            finally:
                s.c.unlock()
            time.sleep(sleepsecs)
        else:
            s.c.lock()
            try:
                s.drawleadstr()
                s.window.refresh()
            finally:
                s.c.unlock()
        return s.sleeping_abort

    def syncnow(s):
        s.sleeping_abort = 1

class CursesThreadFrame:
    def __init__(s, master, ui, window, y, x):
        """master should be a CursesUtil object."""
        s.c = master
        s.ui = ui
        s.window = window
        s.x = x
        s.y = y
        s.colors = []
        bg = curses.COLOR_BLACK
        s.colormap = {'black': s.c.getpair(curses.COLOR_BLACK, bg),
                         'gray': s.c.getpair(curses.COLOR_WHITE, bg),
                         'white': curses.A_BOLD | s.c.getpair(curses.COLOR_WHITE, bg),
                         'blue': s.c.getpair(curses.COLOR_BLUE, bg),
                         'red': s.c.getpair(curses.COLOR_RED, bg),
                         'purple': s.c.getpair(curses.COLOR_MAGENTA, bg),
                         'cyan': s.c.getpair(curses.COLOR_CYAN, bg),
                         'green': s.c.getpair(curses.COLOR_GREEN, bg),
                         'orange': s.c.getpair(curses.COLOR_YELLOW, bg),
                         'yellow': curses.A_BOLD | s.c.getpair(curses.COLOR_YELLOW, bg),
                         'pink': curses.A_BOLD | s.c.getpair(curses.COLOR_RED, bg)}
        #s.setcolor('gray')
        s.setcolor('black')

    def setcolor(self, color):
        self.color = self.colormap[color]
        self.colorname = color
        self.display()

    def display(self):
        def lockedstuff():
            if self.getcolor() == 'black':
                self.window.addstr(self.y, self.x, ' ', self.color)
            else:
                self.window.addstr(self.y, self.x, self.ui.config.getdefault("ui.Curses.Blinkenlights", "statuschar", '.'), self.color)
            self.c.stdscr.move(self.c.height - 1, self.c.width - 1)
            self.window.refresh()
        self.c.locked(lockedstuff)

    def getcolor(self):
        return self.colorname

    def getcolorpair(self):
        return self.color

    def update(self, window, y, x):
        self.window = window
        self.y = y
        self.x = x
        self.display()

    def setthread(self, newthread):
        self.setcolor('black')
        #if newthread:
        #    self.setcolor('gray')
        #else:
        #    self.setcolor('black')

class InputHandler:
    def __init__(s, util):
        s.c = util
        s.bgchar = None
        s.inputlock = Lock()
        s.lockheld = 0
        s.statuslock = Lock()
        s.startup = Event()
        s.startthread()

    def startthread(s):
        s.thread = threadutil.ExitNotifyThread(target = s.bgreaderloop,
                                               name = "InputHandler loop")
        s.thread.setDaemon(1)
        s.thread.start()

    def bgreaderloop(s):
        while 1:
            s.statuslock.acquire()
            if s.lockheld or s.bgchar == None:
                s.statuslock.release()
                s.startup.wait()
            else:
                s.statuslock.release()
                ch = s.c.stdscr.getch()
                s.statuslock.acquire()
                try:
                    if s.lockheld or s.bgchar == None:
                        curses.ungetch(ch)
                    else:
                        s.bgchar(ch)
                finally:
                    s.statuslock.release()

    def set_bgchar(s, callback):
        """Sets a "background" character handler.  If a key is pressed
        while not doing anything else, it will be passed to this handler.

        callback is a function taking a single arg -- the char pressed.

        If callback is None, clears the request."""
        s.statuslock.acquire()
        oldhandler = s.bgchar
        newhandler = callback
        s.bgchar = callback

        if oldhandler and not newhandler:
            pass
        if newhandler and not oldhandler:
            s.startup.set()
            
        s.statuslock.release()

    def input_acquire(s):
        """Call this method when you want exclusive input control.
        Make sure to call input_release afterwards!
        """

        s.inputlock.acquire()
        s.statuslock.acquire()
        s.lockheld = 1
        s.statuslock.release()

    def input_release(s):
        """Call this method when you are done getting input."""
        s.statuslock.acquire()
        s.lockheld = 0
        s.statuslock.release()
        s.inputlock.release()
        s.startup.set()
        
class Blinkenlights(BlinkenBase, UIBase):
    def init_banner(s):
        s.af = {}
        s.aflock = Lock()
        s.c = CursesUtil()
        s.text = []
        BlinkenBase.init_banner(s)
        s.setupwindows()
        s.inputhandler = InputHandler(s.c)
        s.gettf().setcolor('red')
        s._msg(version.banner)
        s.inputhandler.set_bgchar(s.keypress)
        signal.signal(signal.SIGWINCH, s.resizehandler)
        s.resizelock = Lock()
        s.resizecount = 0

    def resizehandler(s, signum, frame):
        s.resizeterm()

    def resizeterm(s, dosleep = 1):
        if not s.resizelock.acquire(0):
            s.resizecount += 1
            return
        signal.signal(signal.SIGWINCH, signal.SIG_IGN)
        s.aflock.acquire()
        s.c.lock()
        s.resizecount += 1
        while s.resizecount:
            s.c.reset()
            s.setupwindows()
            s.resizecount -= 1
        s.c.unlock()
        s.aflock.release()
        s.resizelock.release()
        signal.signal(signal.SIGWINCH, s.resizehandler)
        if dosleep:
            time.sleep(1)
            s.resizeterm(0)

    def isusable(s):
        # Not a terminal?  Can't use curses.
        if not sys.stdout.isatty() and sys.stdin.isatty():
            return 0

        # No TERM specified?  Can't use curses.
        try:
            if not len(os.environ['TERM']):
                return 0
        except: return 0

        # ncurses doesn't want to start?  Can't use curses.
        # This test is nasty because initscr() actually EXITS on error.
        # grr.

        pid = os.fork()
        if pid:
            # parent
            return not os.WEXITSTATUS(os.waitpid(pid, 0)[1])
        else:
            # child
            curses.initscr()
            curses.endwin()
            # If we didn't die by here, indicate success.
            sys.exit(0)

    def keypress(s, key):
        if key < 1 or key > 255:
            return
        
        if chr(key) == 'q':
            # Request to quit.
            s.terminate()
        
        try:
            index = acctkeys.index(chr(key))
        except ValueError:
            # Key not a valid one: exit.
            return

        if index >= len(s.hotkeys):
            # Not in our list of valid hotkeys.
            return

        # Trying to end sleep somewhere.

        s.getaccountframe(s.hotkeys[index]).syncnow()

    def getpass(s, accountname, config, errmsg = None):
        s.inputhandler.input_acquire()

        # See comment on _msg for info on why both locks are obtained.
        
        s.tflock.acquire()
        s.c.lock()
        try:
            s.gettf().setcolor('white')
            s._addline(" *** Input Required", s.gettf().getcolorpair())
            s._addline(" *** Please enter password for account %s: " % accountname,
                   s.gettf().getcolorpair())
            s.logwindow.refresh()
            password = s.logwindow.getstr()
        finally:
            s.tflock.release()
            s.c.unlock()
            s.inputhandler.input_release()
        return password

    def setupwindows(s):
        s.c.lock()
        try:
            s.bannerwindow = curses.newwin(1, s.c.width, 0, 0)
            s.setupwindow_drawbanner()
            s.logheight = s.c.height - 1 - len(s.af.keys())
            s.logwindow = curses.newwin(s.logheight, s.c.width, 1, 0)
            s.logwindow.idlok(1)
            s.logwindow.scrollok(1)
            s.logwindow.move(s.logheight - 1, 0)
            s.setupwindow_drawlog()
            accounts = s.af.keys()
            accounts.sort()
            accounts.reverse()

            pos = s.c.height - 1
            index = 0
            s.hotkeys = []
            for account in accounts:
                accountwindow = curses.newwin(1, s.c.width, pos, 0)
                s.af[account].setwindow(accountwindow, acctkeys[index])
                s.hotkeys.append(account)
                index += 1
                pos -= 1

            curses.doupdate()
        finally:
            s.c.unlock()

    def setupwindow_drawbanner(s):
        if s.c.has_color:
            color = s.c.getpair(curses.COLOR_WHITE, curses.COLOR_BLUE) | \
                    curses.A_BOLD
        else:
            color = curses.A_REVERSE
        s.bannerwindow.bkgd(' ', color) # Fill background with that color
        s.bannerwindow.addstr("%s %s" % (version.productname,
                                         version.versionstr))
        s.bannerwindow.addstr(0, s.bannerwindow.getmaxyx()[1] - len(version.copyright) - 1,
                              version.copyright)
        
        s.bannerwindow.noutrefresh()

    def setupwindow_drawlog(s):
        if s.c.has_color:
            color = s.c.getpair(curses.COLOR_WHITE, curses.COLOR_BLACK)
        else:
            color = curses.A_NORMAL
        s.logwindow.bkgd(' ', color)
        for line, color in s.text:
            s.logwindow.addstr("\n" + line, color)
        s.logwindow.noutrefresh()

    def getaccountframe(s, accountname = None):
        if accountname == None:
            accountname = s.getthreadaccount()
        s.aflock.acquire()
        try:
            if accountname in s.af:
                return s.af[accountname]

            # New one.
            s.af[accountname] = CursesAccountFrame(s.c, accountname, s)
            s.c.lock()
            try:
                s.c.reset()
                s.setupwindows()
            finally:
                s.c.unlock()
        finally:
            s.aflock.release()
        return s.af[accountname]


    def _display(s, msg, color = None):
        if "\n" in msg:
            for thisline in msg.split("\n"):
                s._msg(thisline)
            return

        # We must acquire both locks.  Otherwise, deadlock can result.
        # This can happen if one thread calls _msg (locking curses, then
        # tf) and another tries to set the color (locking tf, then curses)
        #
        # By locking both up-front here, in this order, we prevent deadlock.
        
        s.tflock.acquire()
        s.c.lock()
        try:
            if not s.c.isactive():
                # For dumping out exceptions and stuff.
                print msg
                return
            if color:
                s.gettf().setcolor(color)
            elif s.gettf().getcolor() == 'black':
                s.gettf().setcolor('gray')
            s._addline(msg, s.gettf().getcolorpair())
            s.logwindow.refresh()
        finally:
            s.c.unlock()
            s.tflock.release()

    def _addline(s, msg, color):
        s.c.lock()
        try:
            s.logwindow.addstr("\n" + msg, color)
            s.text.append((msg, color))
            while len(s.text) > s.logheight:
                s.text = s.text[1:]
        finally:
            s.c.unlock()

    def terminate(s, exitstatus = 0, errortitle = None, errormsg = None):
        s.c.stop()
        UIBase.terminate(s, exitstatus = exitstatus, errortitle = errortitle, errormsg = errormsg)

    def threadException(s, thread):
        s.c.stop()
        UIBase.threadException(s, thread)

    def mainException(s):
        s.c.stop()
        UIBase.mainException(s)

    def sleep(s, sleepsecs, siglistener):
        s.gettf().setcolor('red')
        s._msg("Next sync in %d:%02d" % (sleepsecs / 60, sleepsecs % 60))
        return BlinkenBase.sleep(s, sleepsecs, siglistener)
            
if __name__ == '__main__':
    x = Blinkenlights(None)
    x.init_banner()
    import time
    time.sleep(5)
    x.c.stop()
    fgs = {'black': curses.COLOR_BLACK, 'red': curses.COLOR_RED,
           'green': curses.COLOR_GREEN, 'yellow': curses.COLOR_YELLOW,
           'blue': curses.COLOR_BLUE, 'magenta': curses.COLOR_MAGENTA,
           'cyan': curses.COLOR_CYAN, 'white': curses.COLOR_WHITE}
    
    x = CursesUtil()
    win1 = curses.newwin(x.height, x.width / 4 - 1, 0, 0)
    win1.addstr("Black/normal\n")
    for name, fg in fgs.items():
        win1.addstr("%s\n" % name, x.getpair(fg, curses.COLOR_BLACK))
    win2 = curses.newwin(x.height, x.width / 4 - 1, 0, win1.getmaxyx()[1])
    win2.addstr("Blue/normal\n")
    for name, fg in fgs.items():
        win2.addstr("%s\n" % name, x.getpair(fg, curses.COLOR_BLUE))
    win3 = curses.newwin(x.height, x.width / 4 - 1, 0, win1.getmaxyx()[1] +
                         win2.getmaxyx()[1])
    win3.addstr("Black/bright\n")
    for name, fg in fgs.items():
        win3.addstr("%s\n" % name, x.getpair(fg, curses.COLOR_BLACK) | \
                    curses.A_BOLD)
    win4 = curses.newwin(x.height, x.width / 4 - 1, 0, win1.getmaxyx()[1] * 3)
    win4.addstr("Blue/bright\n")
    for name, fg in fgs.items():
        win4.addstr("%s\n" % name, x.getpair(fg, curses.COLOR_BLUE) | \
                    curses.A_BOLD)
        
        
    win1.refresh()
    win2.refresh()
    win3.refresh()
    win4.refresh()
    x.stdscr.refresh()
    import time
    time.sleep(5)
    x.stop()
    print x.has_color
    print x.height
    print x.width


########NEW FILE########
__FILENAME__ = debuglock
# Locking debugging code -- temporary
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
import traceback
logfile = open("/tmp/logfile", "wt")
loglock = Lock()

class DebuggingLock:
    def __init__(self, name):
        self.lock = Lock()
        self.name = name
        
    def acquire(self, blocking = 1):
        self.print_tb("Acquire lock")
        self.lock.acquire(blocking)
        self.logmsg("===== %s: Thread %s acquired lock\n" % (self.name, currentThread().getName()))

    def release(self):
        self.print_tb("Release lock")
        self.lock.release()

    def logmsg(self, msg):
        loglock.acquire()
        logfile.write(msg + "\n")
        logfile.flush()
        loglock.release()

    def print_tb(self, msg):
        self.logmsg(".... %s: Thread %s attempting to %s\n" % \
                    (self.name, currentThread().getName(), msg) + \
                    "\n".join(traceback.format_list(traceback.extract_stack())))
        


########NEW FILE########
__FILENAME__ = detector
# UI base class
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import offlineimap.ui
import sys

DEFAULT_UI_LIST = ('Curses.Blinkenlights', 'TTY.TTYUI',
                   'Noninteractive.Basic', 'Noninteractive.Quiet',
                   'Machine.MachineUI')

def findUI(config, chosenUI=None):
    uistrlist = list(DEFAULT_UI_LIST)
    namespace={}
    for ui in dir(offlineimap.ui):
        if ui.startswith('_') or ui in ('detector', 'UIBase'):
            continue
        namespace[ui]=getattr(offlineimap.ui, ui)

    if chosenUI is not None:
        uistrlist = [chosenUI]
    elif config.has_option("general", "ui"):
        uistrlist = config.get("general", "ui").replace(" ", "").split(",")

    for uistr in uistrlist:
        uimod = getUImod(uistr, config.getlocaleval(), namespace)
        if uimod:
            uiinstance = uimod(config)
            if uiinstance.isusable():
                return uiinstance
    sys.stderr.write("ERROR: No UIs were found usable!\n")
    sys.exit(200)
    
def getUImod(uistr, localeval, namespace):
    try:
        uimod = localeval.eval(uistr, namespace)
    except (AttributeError, NameError), e:
        #raise
        return None
    return uimod

########NEW FILE########
__FILENAME__ = Machine
# Copyright (C) 2007 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import offlineimap.version
import urllib, sys, re, time, traceback, threading, thread
from UIBase import UIBase
from threading import *

protocol = '6.0.0'

class MachineUI(UIBase):
    def __init__(s, config, verbose = 0):
        UIBase.__init__(s, config, verbose)
        s.safechars=" ;,./-_=+()[]"
        s.iswaiting = 0
        s.outputlock = Lock()
        s._printData('__init__', protocol)

    def isusable(s):
        return True

    def _printData(s, command, data, dolock = True):
        s._printDataOut('msg', command, data, dolock)

    def _printWarn(s, command, data, dolock = True):
        s._printDataOut('warn', command, data, dolock)

    def _printDataOut(s, datatype, command, data, dolock = True):
        if dolock:
            s.outputlock.acquire()
        try:
            print "%s:%s:%s:%s" % \
                    (datatype,
                     urllib.quote(command, s.safechars), 
                     urllib.quote(currentThread().getName(), s.safechars),
                     urllib.quote(data, s.safechars))
            sys.stdout.flush()
        finally:
            if dolock:
                s.outputlock.release()

    def _display(s, msg):
        s._printData('_display', msg)

    def warn(s, msg, minor):
        s._printData('warn', '%s\n%d' % (msg, int(minor)))

    def registerthread(s, account):
        UIBase.registerthread(s, account)
        s._printData('registerthread', account)

    def unregisterthread(s, thread):
        UIBase.unregisterthread(s, thread)
        s._printData('unregisterthread', thread.getName())

    def debugging(s, debugtype):
        s._printData('debugging', debugtype)

    def acct(s, accountname):
        s._printData('acct', accountname)

    def acctdone(s, accountname):
        s._printData('acctdone', accountname)

    def validityproblem(s, folder):
        s._printData('validityproblem', "%s\n%s\n%s\n%s" % \
                (folder.getname(), folder.getrepository().getname(),
                 folder.getsaveduidvalidity(), folder.getuidvalidity()))

    def connecting(s, hostname, port):
        s._printData('connecting', "%s\n%s" % (hostname, str(port)))

    def syncfolders(s, srcrepos, destrepos):
        s._printData('syncfolders', "%s\n%s" % (s.getnicename(srcrepos), 
                                                s.getnicename(destrepos)))

    def syncingfolder(s, srcrepos, srcfolder, destrepos, destfolder):
        s._printData('syncingfolder', "%s\n%s\n%s\n%s\n" % \
                (s.getnicename(srcrepos), srcfolder.getname(),
                 s.getnicename(destrepos), destfolder.getname()))

    def loadmessagelist(s, repos, folder):
        s._printData('loadmessagelist', "%s\n%s" % (s.getnicename(repos),
                                                    folder.getvisiblename()))

    def messagelistloaded(s, repos, folder, count):
        s._printData('messagelistloaded', "%s\n%s\n%d" % \
                (s.getnicename(repos), folder.getname(), count))

    def syncingmessages(s, sr, sf, dr, df):
        s._printData('syncingmessages', "%s\n%s\n%s\n%s\n" % \
                (s.getnicename(sr), sf.getname(), s.getnicename(dr),
                 df.getname()))

    def copyingmessage(s, uid, src, destlist):
        ds = s.folderlist(destlist)
        s._printData('copyingmessage', "%d\n%s\n%s\n%s"  % \
                (uid, s.getnicename(src), src.getname(), ds))
        
    def folderlist(s, list):
        return ("\f".join(["%s\t%s" % (s.getnicename(x), x.getname()) for x in list]))

    def deletingmessage(s, uid, destlist):
        s.deletingmessages(s, [uid], destlist)

    def uidlist(s, list):
        return ("\f".join([str(u) for u in list]))

    def deletingmessages(s, uidlist, destlist):
        ds = s.folderlist(destlist)
        s._printData('deletingmessages', "%s\n%s" % (s.uidlist(uidlist), ds))

    def addingflags(s, uidlist, flags, destlist):
        ds = s.folderlist(destlist)
        s._printData("addingflags", "%s\n%s\n%s" % (s.uidlist(uidlist),
                                                    "\f".join(flags),
                                                    ds))

    def deletingflags(s, uidlist, flags, destlist):
        ds = s.folderlist(destlist)
        s._printData('deletingflags', "%s\n%s\n%s" % (s.uidlist(uidlist),
                                                      "\f".join(flags),
                                                      ds))

    def threadException(s, thread):
        print s.getThreadExceptionString(thread)
        s._printData('threadException', "%s\n%s" % \
                     (thread.getName(), s.getThreadExceptionString(thread)))
        s.delThreadDebugLog(thread)
        s.terminate(100)

    def terminate(s, exitstatus = 0, errortitle = '', errormsg = ''):
        s._printData('terminate', "%d\n%s\n%s" % (exitstatus, errortitle, errormsg))
        sys.exit(exitstatus)

    def mainException(s):
        s._printData('mainException', s.getMainExceptionString())

    def threadExited(s, thread):
        s._printData('threadExited', thread.getName())
        UIBase.threadExited(s, thread)

    def sleeping(s, sleepsecs, remainingsecs):
        s._printData('sleeping', "%d\n%d" % (sleepsecs, remainingsecs))
        if sleepsecs > 0:
            time.sleep(sleepsecs)
        return 0


    def getpass(s, accountname, config, errmsg = None):
        s.outputlock.acquire()
        try:
            if errmsg:
                s._printData('getpasserror', "%s\n%s" % (accountname, errmsg),
                             False)
            s._printData('getpass', accountname, False)
            return (sys.stdin.readline()[:-1])
        finally:
            s.outputlock.release()

    def init_banner(s):
        s._printData('initbanner', offlineimap.version.banner)

    def callhook(s, msg):
        s._printData('callhook', msg)

########NEW FILE########
__FILENAME__ = Noninteractive
# Noninteractive UI
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import sys, time
from UIBase import UIBase

class Basic(UIBase):
    def getpass(s, accountname, config, errmsg = None):
        raise NotImplementedError, "Prompting for a password is not supported in noninteractive mode."

    def _display(s, msg):
        print msg
        sys.stdout.flush()

    def warn(s, msg, minor = 0):
        warntxt = 'WARNING'
        if minor:
            warntxt = 'warning'
        sys.stderr.write(warntxt + ": " + str(msg) + "\n")

    def sleep(s, sleepsecs, siglistener):
        if s.verbose >= 0:
            s._msg("Sleeping for %d:%02d" % (sleepsecs / 60, sleepsecs % 60))
        return UIBase.sleep(s, sleepsecs, siglistener)

    def sleeping(s, sleepsecs, remainingsecs):
        if sleepsecs > 0:
            time.sleep(sleepsecs)
        return 0

    def locked(s):
        s.warn("Another OfflineIMAP is running with the same metadatadir; exiting.")

class Quiet(Basic):
    def __init__(s, config, verbose = -1):
        Basic.__init__(s, config, verbose)

########NEW FILE########
__FILENAME__ = TTY
# TTY UI
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from UIBase import UIBase
from getpass import getpass
import select, sys
from threading import *

class TTYUI(UIBase):
    def __init__(s, config, verbose = 0):
        UIBase.__init__(s, config, verbose)
        s.iswaiting = 0
        s.outputlock = Lock()

    def isusable(s):
        return sys.stdout.isatty() and sys.stdin.isatty()
        
    def _display(s, msg):
        s.outputlock.acquire()
        try:
            if (currentThread().getName() == 'MainThread'):
                print msg
            else:
                print "%s:\n   %s" % (currentThread().getName(), msg)
            sys.stdout.flush()
        finally:
            s.outputlock.release()

    def getpass(s, accountname, config, errmsg = None):
        if errmsg:
            s._msg("%s: %s" % (accountname, errmsg))
        s.outputlock.acquire()
        try:
            return getpass("%s: Enter password: " % accountname)
        finally:
            s.outputlock.release()

    def mainException(s):
        if isinstance(sys.exc_info()[1], KeyboardInterrupt) and \
           s.iswaiting:
            sys.stdout.write("Timer interrupted at user request; program terminating.             \n")
            s.terminate()
        else:
            UIBase.mainException(s)


########NEW FILE########
__FILENAME__ = UIBase
# UI base class
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import offlineimap.version
import re, time, sys, traceback, threading, thread
from StringIO import StringIO
from Queue import Empty

debugtypes = {'imap': 'IMAP protocol debugging',
              'maildir': 'Maildir repository debugging',
              'thread': 'Threading debugging'}

globalui = None
def setglobalui(newui):
    global globalui
    globalui = newui
def getglobalui():
    global globalui
    return globalui

class UIBase:
    def __init__(s, config, verbose = 0):
        s.verbose = verbose
        s.config = config
        s.debuglist = []
        s.debugmessages = {}
        s.debugmsglen = 50
        s.threadaccounts = {}
        s.logfile = None
    
    ################################################## UTILS
    def _msg(s, msg):
        """Generic tool called when no other works."""
        s._log(msg)
        s._display(msg)

    def _log(s, msg):
        """Log it to disk.  Returns true if it wrote something; false
        otherwise."""
        if s.logfile:
            s.logfile.write("%s: %s\n" % (threading.currentThread().getName(),
                                          msg))
            return 1
        return 0

    def setlogfd(s, logfd):
        s.logfile = logfd
        logfd.write("This is %s %s\n" % \
                    (offlineimap.version.productname,
                     offlineimap.version.versionstr))
        logfd.write("Python: %s\n" % sys.version)
        logfd.write("Platform: %s\n" % sys.platform)
        logfd.write("Args: %s\n" % sys.argv)

    def _display(s, msg):
        """Display a message."""
        raise NotImplementedError

    def warn(s, msg, minor = 0):
        if minor:
            s._msg("warning: " + msg)
        else:
            s._msg("WARNING: " + msg)

    def registerthread(s, account):
        """Provides a hint to UIs about which account this particular
        thread is processing."""
        if s.threadaccounts.has_key(threading.currentThread()):
            raise ValueError, "Thread %s already registered (old %s, new %s)" %\
                  (threading.currentThread().getName(),
                   s.getthreadaccount(s), account)
        s.threadaccounts[threading.currentThread()] = account

    def unregisterthread(s, thr):
        """Recognizes a thread has exited."""
        if s.threadaccounts.has_key(thr):
            del s.threadaccounts[thr]

    def getthreadaccount(s, thr = None):
        if not thr:
            thr = threading.currentThread()
        if s.threadaccounts.has_key(thr):
            return s.threadaccounts[thr]
        return '*Control'

    def debug(s, debugtype, msg):
        thisthread = threading.currentThread()
        if s.debugmessages.has_key(thisthread):
            s.debugmessages[thisthread].append("%s: %s" % (debugtype, msg))
        else:
            s.debugmessages[thisthread] = ["%s: %s" % (debugtype, msg)]

        while len(s.debugmessages[thisthread]) > s.debugmsglen:
            s.debugmessages[thisthread] = s.debugmessages[thisthread][1:]

        if debugtype in s.debuglist:
            if not s._log("DEBUG[%s]: %s" % (debugtype, msg)):
                s._display("DEBUG[%s]: %s" % (debugtype, msg))

    def add_debug(s, debugtype):
        global debugtypes
        if debugtype in debugtypes:
            if not debugtype in s.debuglist:
                s.debuglist.append(debugtype)
                s.debugging(debugtype)
        else:
            s.invaliddebug(debugtype)

    def debugging(s, debugtype):
        global debugtypes
        s._msg("Now debugging for %s: %s" % (debugtype, debugtypes[debugtype]))

    def invaliddebug(s, debugtype):
        s.warn("Invalid debug type: %s" % debugtype)

    def locked(s):
        raise Exception, "Another OfflineIMAP is running with the same metadatadir; exiting."

    def getnicename(s, object):
        prelimname = str(object.__class__).split('.')[-1]
        # Strip off extra stuff.
        return re.sub('(Folder|Repository)', '', prelimname)

    def isusable(s):
        """Returns true if this UI object is usable in the current
        environment.  For instance, an X GUI would return true if it's
        being run in X with a valid DISPLAY setting, and false otherwise."""
        return 1

    ################################################## INPUT

    def getpass(s, accountname, config, errmsg = None):
        raise NotImplementedError

    def folderlist(s, list):
        return ', '.join(["%s[%s]" % (s.getnicename(x), x.getname()) for x in list])

    ################################################## WARNINGS
    def msgtoreadonly(s, destfolder, uid, content, flags):
        if not (s.config.has_option('general', 'ignore-readonly') and s.config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to synchronize message %d to folder %s[%s], but that folder is read-only.  The message will not be copied to that folder." % \
                   (uid, s.getnicename(destfolder), destfolder.getname()))

    def flagstoreadonly(s, destfolder, uidlist, flags):
        if not (s.config.has_option('general', 'ignore-readonly') and s.config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to modify flags for messages %s in folder %s[%s], but that folder is read-only.  No flags have been modified for that message." % \
                   (str(uidlist), s.getnicename(destfolder), destfolder.getname()))

    def deletereadonly(s, destfolder, uidlist):
        if not (s.config.has_option('general', 'ignore-readonly') and s.config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to delete messages %s in folder %s[%s], but that folder is read-only.  No messages have been deleted in that folder." % \
                   (str(uidlist), s.getnicename(destfolder), destfolder.getname()))

    ################################################## MESSAGES

    def init_banner(s):
        """Called when the UI starts.  Must be called before any other UI
        call except isusable().  Displays the copyright banner.  This is
        where the UI should do its setup -- TK, for instance, would
        create the application window here."""
        if s.verbose >= 0:
            s._msg(offlineimap.version.banner)

    def connecting(s, hostname, port):
        if s.verbose < 0:
            return
        if hostname == None:
            hostname = ''
        if port != None:
            port = ":%s" % str(port)
        displaystr = ' to %s%s.' % (hostname, port)
        if hostname == '' and port == None:
            displaystr = '.'
        s._msg("Establishing connection" + displaystr)

    def acct(s, accountname):
        if s.verbose >= 0:
            s._msg("***** Processing account %s" % accountname)

    def acctdone(s, accountname):
        if s.verbose >= 0:
            s._msg("***** Finished processing account " + accountname)

    def syncfolders(s, srcrepos, destrepos):
        if s.verbose >= 0:
            s._msg("Copying folder structure from %s to %s" % \
                   (s.getnicename(srcrepos), s.getnicename(destrepos)))

    ############################## Folder syncing
    def syncingfolder(s, srcrepos, srcfolder, destrepos, destfolder):
        """Called when a folder sync operation is started."""
        if s.verbose >= 0:
            s._msg("Syncing %s: %s -> %s" % (srcfolder.getname(),
                                             s.getnicename(srcrepos),
                                             s.getnicename(destrepos)))

    def skippingfolder(s, folder):
        """Called when a folder sync operation is started."""
        if s.verbose >= 0:
            s._msg("Skipping %s (not changed)" % folder.getname())

    def validityproblem(s, folder):
        s.warn("UID validity problem for folder %s (repo %s) (saved %d; got %d); skipping it" % \
               (folder.getname(), folder.getrepository().getname(),
                folder.getsaveduidvalidity(), folder.getuidvalidity()))

    def loadmessagelist(s, repos, folder):
        if s.verbose > 0:
            s._msg("Loading message list for %s[%s]" % (s.getnicename(repos),
                                                        folder.getname()))

    def messagelistloaded(s, repos, folder, count):
        if s.verbose > 0:
            s._msg("Message list for %s[%s] loaded: %d messages" % \
                   (s.getnicename(repos), folder.getname(), count))

    ############################## Message syncing

    def syncingmessages(s, sr, sf, dr, df):
        if s.verbose > 0:
            s._msg("Syncing messages %s[%s] -> %s[%s]" % (s.getnicename(sr),
                                                          sf.getname(),
                                                          s.getnicename(dr),
                                                          df.getname()))

    def copyingmessage(s, uid, src, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Copy message %d %s[%s] -> %s" % (uid, s.getnicename(src),
                                                     src.getname(), ds))

    def deletingmessage(s, uid, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting message %d in %s" % (uid, ds))

    def deletingmessages(s, uidlist, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting %d messages (%s) in %s" % \
                   (len(uidlist),
                    ", ".join([str(u) for u in uidlist]),
                    ds))

    def addingflags(s, uidlist, flags, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Adding flags %s to %d messages  on %s" % \
                   (", ".join(flags), len(uidlist), ds))

    def deletingflags(s, uidlist, flags, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting flags %s to %d messages on %s" % \
                   (", ".join(flags), len(uidlist), ds))

    ################################################## Threads

    def getThreadDebugLog(s, thread):
        if s.debugmessages.has_key(thread):
            message = "\nLast %d debug messages logged for %s prior to exception:\n"\
                       % (len(s.debugmessages[thread]), thread.getName())
            message += "\n".join(s.debugmessages[thread])
        else:
            message = "\nNo debug messages were logged for %s." % \
                      thread.getName()
        return message

    def delThreadDebugLog(s, thread):
        if s.debugmessages.has_key(thread):
            del s.debugmessages[thread]

    def getThreadExceptionString(s, thread):
        message = "Thread '%s' terminated with exception:\n%s" % \
                  (thread.getName(), thread.getExitStackTrace())
        message += "\n" + s.getThreadDebugLog(thread)
        return message

    def threadException(s, thread):
        """Called when a thread has terminated with an exception.
        The argument is the ExitNotifyThread that has so terminated."""
        s._msg(s.getThreadExceptionString(thread))
        s.delThreadDebugLog(thread)
        s.terminate(100)

    def getMainExceptionString(s):
        sbuf = StringIO()
        traceback.print_exc(file = sbuf)
        return "Main program terminated with exception:\n" + \
               sbuf.getvalue() + "\n" + \
               s.getThreadDebugLog(threading.currentThread())

    def mainException(s):
        s._msg(s.getMainExceptionString())

    def terminate(s, exitstatus = 0, errortitle = None, errormsg = None):
        """Called to terminate the application."""
        if errormsg <> None:
            if errortitle <> None:
                sys.stderr.write('ERROR: %s\n\n%s\n'%(errortitle, errormsg))
            else:
                sys.stderr.write('%s\n' % errormsg)
        sys.exit(exitstatus)

    def threadExited(s, thread):
        """Called when a thread has exited normally.  Many UIs will
        just ignore this."""
        s.delThreadDebugLog(thread)
        s.unregisterthread(thread)

    ################################################## Hooks

    def callhook(s, msg):
        if s.verbose >= 0:
            s._msg(msg)

    ################################################## Other

    def sleep(s, sleepsecs, siglistener):
        """This function does not actually output anything, but handles
        the overall sleep, dealing with updates as necessary.  It will,
        however, call sleeping() which DOES output something.

        Returns 0 if timeout expired, 1 if there is a request to cancel
        the timer, and 2 if there is a request to abort the program."""

        abortsleep = 0
        while sleepsecs > 0 and not abortsleep:
            try:
                abortsleep = siglistener.get_nowait()
                # retrieved signal while sleeping: 1 means immediately resynch, 2 means immediately die
            except Empty:
                # no signal
                abortsleep = s.sleeping(1, sleepsecs)
            sleepsecs -= 1
        s.sleeping(0, 0)               # Done sleeping.
        return abortsleep

    def sleeping(s, sleepsecs, remainingsecs):
        """Sleep for sleepsecs, remainingsecs to go.
        If sleepsecs is 0, indicates we're done sleeping.

        Return 0 for normal sleep, or 1 to indicate a request
        to sync immediately."""
        s._msg("Next refresh in %d seconds" % remainingsecs)
        if sleepsecs > 0:
            time.sleep(sleepsecs)
        return 0

########NEW FILE########
__FILENAME__ = version
productname = 'OfflineIMAP'
versionstr = "6.2.0"

versionlist = versionstr.split(".")
major = versionlist[0]
minor = versionlist[1]
patch = versionlist[2]
copyright = "Copyright (C) 2002 - 2009 John Goerzen"
author = "John Goerzen"
author_email = "jgoerzen@complete.org"
description = "Disconnected Universal IMAP Mail Synchronization/Reader Support"
bigcopyright = """%(productname)s %(versionstr)s
%(copyright)s <%(author_email)s>""" % locals()

banner = bigcopyright + """
This software comes with ABSOLUTELY NO WARRANTY; see the file
COPYING for details.  This is free software, and you are welcome
to distribute it under the conditions laid out in COPYING."""

homepage = "http://software.complete.org/offlineimap/"
license = """Copyright (C) 2002 - 2009 John Goerzen <jgoerzen@complete.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA"""

def getcmdhelp():
    from offlineimap.ui import detector
    import os
    uilist = ""
    for ui in detector.DEFAULT_UI_LIST:
        uilist += "                " + ui + os.linesep
    return """
       offlineimap [ -1 ] [ -P profiledir ] [ -a accountlist ]  [
       -c configfile  ] [ -d debugtype[,debugtype...]  ] [ -o ] [
       -u interface ] [ -q ]

       offlineimap -h | --help

       -1     Disable   all  multithreading  operations  and  use
              solely a single-thread sync.  This effectively sets
              the maxsyncaccounts and all maxconnections configu-
              ration file variables to 1.

       -P profiledir
              Sets OfflineIMAP into profile  mode.   The  program
              will create profiledir (it must not already exist).
              As it runs, Python profiling information about each
              thread  is  logged  into  profiledir.  Please note:
              This option is present for debugging and  optimiza-
              tion only, and should NOT be used unless you have a
              specific reason to do so.   It  will  significantly
              slow  program  performance, may reduce reliability,
              and can generate huge amounts of  data.   You  must
              use the -1 option when you use -P.


       -a accountlist
              Overrides  the accounts section in the config file.
              Lets you specify a particular  account  or  set  of
              accounts  to sync without having to edit the config
              file.   You  might  use  this  to  exclude  certain
              accounts,  or  to  sync some accounts that you nor-
              mally prefer not to.

       -c configfile
              Specifies a configuration file to use  in  lieu  of
              the default, ~/.offlineimaprc.

       -d debugtype[,debugtype...]
              Enables  debugging for OfflineIMAP.  This is useful
              if you are trying to track down  a  malfunction  or
              figure out what is going on under the hood.  I sug-
              gest that you use this with -1 in order to make the
              results more sensible.

              -d  now  requires one or more debugtypes, separated
              by commas.   These  define  what  exactly  will  be
              debugged,  and so far include two options: imap and
              maildir.  The imap option will enable IMAP protocol
              stream and parsing debugging.  Note that the output
              may contain passwords, so take care to remove  that
              from the debugging output before sending it to any-
              one else.  The maildir option will enable debugging
              for certain Maildir operations.

       -f foldername[,foldername...]
              Only sync the specified folders.  The "foldername"s
              are    the   *untranslated*    foldernames.    This
              command-line  option  overrides any  "folderfilter"
              and "folderincludes" options  in the  configuration 
              file.

       -k [section:]option=value
              Override configuration file option.  If"section" is
              omitted, it defaults to "general".  Any underscores
              "_" in the section name are replaced with spaces:
              for instance,  to override  option "autorefresh" in
              the "[Account Personal]" section in the config file
              one would use "-k Account_Personal:autorefresh=30".
              
       -o     Run only once,  ignoring any autorefresh setting in
              the config file.

       -q     Run  only quick synchronizations.   Ignore any flag
              updates on IMAP servers.

       -h, --help
              Show summary of options.

       -u interface
              Specifies an alternative user interface  module  to
              use.   This  overrides the default specified in the
              configuration file.  The UI specified with -u  will
              be  forced to be used, even if its isuable() method
              states that it cannot be.   Use  this  option  with
              care.   The  pre-defined  options, described in the
              USER INTERFACES section of the man page, are:
""" + uilist

########NEW FILE########
__FILENAME__ = offlineimap
#!/usr/bin/env python
# Startup from single-user installation
# Copyright (C) 2002 - 2008 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from offlineimap import init
init.startup('6.2.0')

########NEW FILE########
