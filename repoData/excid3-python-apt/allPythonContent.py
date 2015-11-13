__FILENAME__ = cache
# cache.py - apt cache abstraction
#  
#  Copyright (c) 2005 Canonical
#  
#  Author: Michael Vogt <michael.vogt@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import apt_pkg
from apt import Package
import apt.progress
import os
import sys

class FetchCancelledException(IOError):
    " Exception that is thrown when the user cancels a fetch operation "
    pass
class FetchFailedException(IOError):
    " Exception that is thrown when fetching fails "
    pass
class LockFailedException(IOError):
    " Exception that is thrown when locking fails "
    pass

class Cache(object):
    """ Dictionary-like package cache 
        This class has all the packages that are available in it's
        dictionary
    """

    def __init__(self, progress=None, rootdir=None, memonly=False):
        self._callbacks = {}
        if memonly:
            # force apt to build its caches in memory
            apt_pkg.Config.Set("Dir::Cache::pkgcache","")
        if rootdir:
            apt_pkg.Config.Set("Dir", rootdir)
            apt_pkg.Config.Set("Dir::State::status", rootdir + "/var/lib/dpkg/status")
        self.open(progress)

    def _runCallbacks(self, name):
        """ internal helper to run a callback """
        if self._callbacks.has_key(name):
            for callback in self._callbacks[name]:
                callback()
        
    def open(self, progress):
        """ Open the package cache, after that it can be used like
            a dictionary
        """
        self._runCallbacks("cache_pre_open")
        self._cache = apt_pkg.GetCache(progress)
        self._depcache = apt_pkg.GetDepCache(self._cache)
        self._records = apt_pkg.GetPkgRecords(self._cache)
        self._list = apt_pkg.GetPkgSourceList()
        self._list.ReadMainList()
        self._dict = {}

        # build the packages dict
        if progress != None:
            progress.Op = "Building data structures"
        i=last=0
        size=len(self._cache.Packages)
        for pkg in self._cache.Packages:
            if progress != None and last+100 < i:
                progress.update(i/float(size)*100)
                last=i
            # drop stuff with no versions (cruft)
            if len(pkg.VersionList) > 0:
                self._dict[pkg.Name] = Package(self._cache, self._depcache,
                                               self._records, self._list,
                                               self, pkg)
                
            i += 1
        if progress != None:
            progress.done()
        self._runCallbacks("cache_post_open")
        
    def __getitem__(self, key):
        """ look like a dictionary (get key) """
        return self._dict[key]

    def __iter__(self):
        for pkgname in self._dict.keys():
            yield self._dict[pkgname]
        raise StopIteration

    def has_key(self, key):
        return self._dict.has_key(key)

    def __contains__(self, key):
        return key in self._dict

    def __len__(self):
        return len(self._dict)

    def keys(self):
        return self._dict.keys()

    def getChanges(self):
        """ Get the marked changes """
        changes = [] 
        for name in self._dict.keys():
            p = self._dict[name]
            if p.markedUpgrade or p.markedInstall or p.markedDelete or \
               p.markedDowngrade or p.markedReinstall:
                changes.append(p)
        return changes

    def upgrade(self, distUpgrade=False):
        """ Upgrade the all package, DistUpgrade will also install
            new dependencies
        """
        self.cachePreChange()
        self._depcache.Upgrade(distUpgrade)
        self.cachePostChange()

    @property
    def reqReinstallPkgs(self):
        " return the packages not downloadable packages in reqreinst state "
        reqreinst = set()
        for pkg in self:
            if (not pkg.candidateDownloadable and 
                (pkg._pkg.InstState == apt_pkg.InstStateReInstReq or
                 pkg._pkg.InstState == apt_pkg.InstStateHoldReInstReq)):
                reqreinst.add(pkg.name)
        return reqreinst

    def _runFetcher(self, fetcher):
        # do the actual fetching
        res = fetcher.Run()
        
        # now check the result (this is the code from apt-get.cc)
        failed = False
        transient = False
        errMsg = ""
        for item in fetcher.Items:
            if item.Status == item.StatDone:
                continue
            if item.StatIdle:
                transient = True
                continue
            errMsg += "Failed to fetch %s %s\n" % (item.DescURI,item.ErrorText)
            failed = True

        # we raise a exception if the download failed or it was cancelt
        if res == fetcher.ResultCancelled:
            raise FetchCancelledException, errMsg
        elif failed:
            raise FetchFailedException, errMsg
        return res

    def _fetchArchives(self, fetcher, pm):
        """ fetch the needed archives """

        # get lock
        lockfile = apt_pkg.Config.FindDir("Dir::Cache::Archives") + "lock"
        lock = apt_pkg.GetLock(lockfile)
        if lock < 0:
            raise LockFailedException, "Failed to lock %s" % lockfile

        try:
            # this may as well throw a SystemError exception
            if not pm.GetArchives(fetcher, self._list, self._records):
                return False
            # now run the fetcher, throw exception if something fails to be
            # fetched
            return self._runFetcher(fetcher)
        finally:
            os.close(lock)

    def update(self, fetchProgress=None):
        " run the equivalent of apt-get update "
        lockfile = apt_pkg.Config.FindDir("Dir::State::Lists") + "lock"
        lock = apt_pkg.GetLock(lockfile)
        if lock < 0:
            raise LockFailedException, "Failed to lock %s" % lockfile

        try:
            if fetchProgress == None:
                fetchProgress = apt.progress.FetchProgress()
            return self._cache.Update(fetchProgress, self._list)
        finally:
            os.close(lock)
        
    def installArchives(self, pm, installProgress):
        installProgress.startUpdate()
        res = installProgress.run(pm)
        installProgress.finishUpdate()
        return res
    
    def commit(self, fetchProgress=None, installProgress=None):
        """ Apply the marked changes to the cache """
        # FIXME:
        # use the new acquire/pkgmanager interface here,
        # raise exceptions when a download or install fails
        # and send proper error strings to the application.
        # Current a failed download will just display "error"
        # which is less than optimal!

        if fetchProgress == None:
            fetchProgress = apt.progress.FetchProgress()
        if installProgress == None:
            installProgress = apt.progress.InstallProgress()

        pm = apt_pkg.GetPackageManager(self._depcache)
        fetcher = apt_pkg.GetAcquire(fetchProgress)
        while True:
            # fetch archives first
            res = self._fetchArchives(fetcher, pm)

            # then install
            res = self.installArchives(pm, installProgress)
            if res == pm.ResultCompleted:
                break
            if res == pm.ResultFailed:
                raise SystemError, "installArchives() failed"
            # reload the fetcher for media swaping
            fetcher.Shutdown()
        return (res == pm.ResultCompleted)

    # cache changes
    def cachePostChange(self):
        " called internally if the cache has changed, emit a signal then "
        self._runCallbacks("cache_post_change")

    def cachePreChange(self):
        """ called internally if the cache is about to change, emit
            a signal then """
        self._runCallbacks("cache_pre_change")

    def connect(self, name, callback):
        """ connect to a signal, currently only used for
            cache_{post,pre}_{changed,open} """
        if not self._callbacks.has_key(name):
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

# ----------------------------- experimental interface
class Filter(object):
    """ Filter base class """
    def apply(self, pkg):
        """ Filter function, return True if the package matchs a
            filter criteria and False otherwise
        """
        return True

class MarkedChangesFilter(Filter):
    """ Filter that returns all marked changes """
    def apply(self, pkg):
        if pkg.markedInstall or pkg.markedDelete or pkg.markedUpgrade:
            return True
        else:
            return False

class FilteredCache(object):
    """ A package cache that is filtered.

        Can work on a existing cache or create a new one
    """
    def __init__(self, cache=None, progress=None):
        if cache == None:
            self.cache = Cache(progress)
        else:
            self.cache = cache
        self.cache.connect("cache_post_change", self.filterCachePostChange)
        self.cache.connect("cache_post_open", self.filterCachePostChange)
        self._filtered = {}
        self._filters = []
    def __len__(self):
        return len(self._filtered)
    
    def __getitem__(self, key):
        return self.cache._dict[key]

    def keys(self):
        return self._filtered.keys()

    def has_key(self, key):
        return self._filtered.has_key(key)

    def _reapplyFilter(self):
        " internal helper to refilter "
        self._filtered = {}
        for pkg in self.cache._dict.keys():
            for f in self._filters:
                if f.apply(self.cache._dict[pkg]):
                    self._filtered[pkg] = 1
                    break
    
    def setFilter(self, filter):
        " set the current active filter "
        self._filters = []
        self._filters.append(filter)
        #self._reapplyFilter()
        # force a cache-change event that will result in a refiltering
        self.cache.cachePostChange()

    def filterCachePostChange(self):
        " called internally if the cache changes, emit a signal then "
        #print "filterCachePostChange()"
        self._reapplyFilter()

#    def connect(self, name, callback):
#        self.cache.connect(name, callback)

    def __getattr__(self, key):
        " we try to look exactly like a real cache "
        #print "getattr: %s " % key
        if self.__dict__.has_key(key):
            return self.__dict__[key]
        else:
            return getattr(self.cache, key)
            

def cache_pre_changed():
    print "cache pre changed"

def cache_post_changed():
    print "cache post changed"


# internal test code
if __name__ == "__main__":
    print "Cache self test"
    apt_pkg.init()
    c = Cache(apt.progress.OpTextProgress())
    c.connect("cache_pre_change", cache_pre_changed)
    c.connect("cache_post_change", cache_post_changed)
    print c.has_key("aptitude")
    p = c["aptitude"]
    print p.name
    print len(c)

    for pkg in c.keys():
        x= c[pkg].name

    c.upgrade()
    changes = c.getChanges()
    print len(changes)
    for p in changes:
        #print p.name
        x = p.name


    # see if fetching works
    for d in ["/tmp/pytest", "/tmp/pytest/partial"]:
        if not os.path.exists(d):
            os.mkdir(d)
    apt_pkg.Config.Set("Dir::Cache::Archives","/tmp/pytest")
    pm = apt_pkg.GetPackageManager(c._depcache)
    fetcher = apt_pkg.GetAcquire(apt.progress.TextFetchProgress())
    c._fetchArchives(fetcher, pm)
    #sys.exit(1)

    print "Testing filtered cache (argument is old cache)"
    f = FilteredCache(c)
    f.cache.connect("cache_pre_change", cache_pre_changed)
    f.cache.connect("cache_post_change", cache_post_changed)
    f.cache.upgrade()
    f.setFilter(MarkedChangesFilter())
    print len(f)
    for pkg in f.keys():
        #print c[pkg].name
        x = f[pkg].name
    
    print len(f)

    print "Testing filtered cache (no argument)"
    f = FilteredCache(progress=OpTextProgress())
    f.cache.connect("cache_pre_change", cache_pre_changed)
    f.cache.connect("cache_post_change", cache_post_changed)
    f.cache.upgrade()
    f.setFilter(MarkedChangesFilter())
    print len(f)
    for pkg in f.keys():
        #print c[pkg].name
        x = f[pkg].name
    
    print len(f)

########NEW FILE########
__FILENAME__ = cdrom
import apt_pkg
from progress import CdromProgress

class Cdrom(object):
    def __init__(self, progress=None, mountpoint=None, nomount=True):
        """ Support for apt-cdrom like features.
            Options:
            - progress: optional progress.CdromProgress() subclass
            - mountpoint: optional alternative mountpoint
            - nomount: do not mess with mount/umount the CD
        """
        self._cdrom = apt_pkg.GetCdrom()
        if progress is None:
            self._progress = CdromProgress()
        else:
            self._progress = progress
        # see if we have a alternative mountpoint
        if mountpoint is not None:
            apt_pkg.Config.Set("Acquire::cdrom::mount",mountpoint)
        # do not mess with mount points by default
        if nomount is True:
            apt_pkg.Config.Set("APT::CDROM::NoMount", "true")
        else:
            apt_pkg.Config.Set("APT::CDROM::NoMount", "false")
    def add(self):
        " add cdrom to the sources.list "
        return self._cdrom.Add(self._progress)
    def ident(self):
        " identify the cdrom "
        (res, ident) = self._cdrom.Ident(self._progress)
        if res:
            return ident
        return None
    @property
    def inSourcesList(self):
        " check if the cdrom is already in the current sources.list "
        cdid = self.ident()
        if cdid is None:
            # FIXME: throw exception instead
            return False
        # FIXME: check sources.list.d/ as well
        for line in open(apt_pkg.Config.FindFile("Dir::Etc::sourcelist")):
            line = line.strip()
            if not line.startswith("#") and cdid in line:
                return True
        return False
        

########NEW FILE########
__FILENAME__ = debfile
import apt_inst
import apt_pkg
from apt_inst import arCheckMember

from gettext import gettext as _

class NoDebArchiveException(IOError):
    pass

class DebPackage(object):

    _supported_data_members = ("data.tar.gz", "data.tar.bz2", "data.tar.lzma")

    def __init__(self, filename=None):
        self._section = {}
        if filename:
            self.open(filename)

    def open(self, filename):
        " open given debfile "
        self.filename = filename
        if not arCheckMember(open(self.filename), "debian-binary"):
            raise NoDebArchiveException, _("This is not a valid DEB archive, missing '%s' member" % "debian-binary")
        control = apt_inst.debExtractControl(open(self.filename))
        self._sections = apt_pkg.ParseSection(control)
        self.pkgname = self._sections["Package"]

    def __getitem__(self, key):
        return self._sections[key]
        
    def filelist(self):
        """ return the list of files in the deb """
        files = []
        def extract_cb(What,Name,Link,Mode,UID,GID,Size,MTime,Major,Minor):
            #print "%s '%s','%s',%u,%u,%u,%u,%u,%u,%u"\
            #      % (What,Name,Link,Mode,UID,GID,Size, MTime, Major, Minor)
            files.append(Name)
        for member in self._supported_data_members:
            if arCheckMember(open(self.filename), member):
                try:
                    apt_inst.debExtract(open(self.filename), extract_cb, member)
                    break
                except SystemError, e:
                    return [_("List of files for '%s'could not be read" % self.filename)]
        return files
    filelist = property(filelist)



if __name__ == "__main__":
    import sys
    
    d = DebPackage(sys.argv[1])
    print d["Section"]
    print d["Maintainer"]
    print "Files:"
    print "\n".join(d.filelist)
    

########NEW FILE########
__FILENAME__ = package
# package.py - apt package abstraction
#  
#  Copyright (c) 2005 Canonical
#  
#  Author: Michael Vogt <michael.vogt@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import apt_pkg
import sys
import random
import string

#from gettext import gettext as _
import gettext
def _(s): return gettext.dgettext("python-apt", s)

class BaseDependency(object):
    " a single dependency "
    def __init__(self, name, rel, ver, pre):
        self.name = name
        self.relation = rel
        self.version = ver
        self.preDepend = pre

class Dependency(object):
    def __init__(self, alternatives):
        self.or_dependencies = alternatives

class Record(object):
    """ represents a pkgRecord, can be accessed like a
        dictionary and gives the original package record
        if accessed as a string """
    def __init__(self, s):
        self._str = s
        self._rec = apt_pkg.ParseSection(s)
    def __str__(self):
        return self._str
    def __getitem__(self, key):
        k = self._rec.get(key)
        if k is None:
            raise KeyError
        return k
    def has_key(self, key):
        return self._rec.has_key(key)

class Package(object):
    """ This class represents a package in the cache
    """
    def __init__(self, cache, depcache, records, sourcelist, pcache, pkgiter):
        """ Init the Package object """
        self._cache = cache             # low level cache
        self._depcache = depcache
        self._records = records
        self._pkg = pkgiter
        self._list = sourcelist               # sourcelist
        self._pcache = pcache           # python cache in cache.py
        pass

    # helper
    def _lookupRecord(self, UseCandidate=True):
        """ internal helper that moves the Records to the right
            position, must be called before _records is accessed """
        if UseCandidate:
            ver = self._depcache.GetCandidateVer(self._pkg)
        else:
            ver = self._pkg.CurrentVer

        # check if we found a version
        if ver == None:
            #print "No version for: %s (Candidate: %s)" % (self._pkg.Name, UseCandidate)
            return False
        
        if ver.FileList == None:
            print "No FileList for: %s " % self._pkg.Name()
            return False
        f, index = ver.FileList.pop(0)
        self._records.Lookup((f,index))
        return True


    # basic information (implemented as properties)

    # FIXME once python2.3 is dropped we can use @property instead
    # of name = property(name)

    def name(self):
        """ Return the name of the package """
        return self._pkg.Name
    name = property(name)

    def id(self):
        """ Return a uniq ID for the pkg, can be used to store
            additional information about the pkg """
        return self._pkg.ID
    id = property(id)

    def installedVersion(self):
        """ Return the installed version as string """
        ver = self._pkg.CurrentVer
        if ver != None:
            return ver.VerStr
        else:
            return None
    installedVersion = property(installedVersion)

    def candidateVersion(self):
        """ Return the candidate version as string """
        ver = self._depcache.GetCandidateVer(self._pkg)
        if ver != None:
            return ver.VerStr
        else:
            return None
    candidateVersion = property(candidateVersion)

    def _getDependencies(self, ver):
        depends_list = []
        depends = ver.DependsList
        for t in ["PreDepends", "Depends"]:
            if not depends.has_key(t):
                continue
            for depVerList in depends[t]:
                base_deps = []
                for depOr in depVerList:
                    base_deps.append(BaseDependency(depOr.TargetPkg.Name, depOr.CompType, depOr.TargetVer, (t == "PreDepends")))
                depends_list.append(Dependency(base_deps))
        return depends_list
        
    def candidateDependencies(self):
        """ return a list of candidate dependencies """
        candver = self._depcache.GetCandidateVer(self._pkg)
        if candver == None:
            return []
        return self._getDependencies(candver)
    candidateDependencies = property(candidateDependencies)
    
    def installedDependencies(self):
        """ return a list of installed dependencies """
        ver = self._pkg.CurrentVer
        if ver == None:
            return []
        return self._getDependencies(ver)
    installedDependencies = property(installedDependencies)

    def architecture(self):
        if not self._lookupRecord():
            return None
        sec = apt_pkg.ParseSection(self._records.Record)
        if sec.has_key("Architecture"):
            return sec["Architecture"]
        return None
    architecture = property(architecture)

    def _downloadable(self, useCandidate=True):
        """ helper, return if the version is downloadable """
        if useCandidate:
            ver = self._depcache.GetCandidateVer(self._pkg)
        else:
            ver = self._pkg.CurrentVer
        if ver == None:
            return False
        return ver.Downloadable
    def candidateDownloadable(self):
        " returns if the canidate is downloadable "
        return self._downloadable(useCandidate=True)
    candidateDownloadable = property(candidateDownloadable)

    def installedDownloadable(self):
        " returns if the installed version is downloadable "
        return self._downloadable(useCandidate=False)
    installedDownloadable = property(installedDownloadable)

    def sourcePackageName(self):
        """ Return the source package name as string """
        if not self._lookupRecord():
            if not self._lookupRecord(UseCandidate=False):
                return self._pkg.Name
        src = self._records.SourcePkg
        if src != "":
            return src
        else:
            return self._pkg.Name
    sourcePackageName = property(sourcePackageName)

    def homepage(self):
        """ Return the homepage field as string """
        if not self._lookupRecord():
            return None
        return self._records.Homepage
    homepage = property(homepage)

    def section(self):
        """ Return the section of the package"""
        return self._pkg.Section
    section = property(section)

    def priority(self):
        """ Return the priority (of the candidate version)"""
        ver = self._depcache.GetCandidateVer(self._pkg)
        if ver:
            return ver.PriorityStr
        else:
            return None
    priority = property(priority)

    def installedPriority(self):
        """ Return the priority (of the installed version)"""
        ver = self._depcache.GetCandidateVer(self._pkg)
        if ver:
            return ver.PriorityStr
        else:
            return None
    installedPriority = property(installedPriority)

    def summary(self):
        """ Return the short description (one line summary) """
        if not self._lookupRecord():
            return ""
        ver = self._depcache.GetCandidateVer(self._pkg)
        desc_iter = ver.TranslatedDescription
        self._records.Lookup(desc_iter.FileList.pop(0))
        return self._records.ShortDesc
    summary = property(summary)

    def description(self, format=True):
        """ Return the formated long description """
        if not self._lookupRecord():
            return ""
        # get the translated description
        ver = self._depcache.GetCandidateVer(self._pkg)
        desc_iter = ver.TranslatedDescription
        self._records.Lookup(desc_iter.FileList.pop(0))
        desc = ""
        try:
            s = unicode(self._records.LongDesc,"utf-8")
        except UnicodeDecodeError,e:
            s = _("Invalid unicode in description for '%s' (%s). "
                  "Please report.") % (self.name,e)
        for line in string.split(s,"\n"):
                tmp = string.strip(line)
                if tmp == ".":
                    desc += "\n"
                else:
                    desc += tmp + "\n"
        return desc
    description = property(description)

    def rawDescription(self):
        """ return the long description (raw)"""
        if not self._lookupRecord():
            return ""
        return self._records.LongDesc
    rawDescription = property(rawDescription)
        
    def candidateRecord(self):
        " return the full pkgrecord as string of the candidate version "
        if not self._lookupRecord(True):
            return None
        return Record(self._records.Record)
    candidateRecord = property(candidateRecord)

    def installedRecord(self):
        " return the full pkgrecord as string of the installed version "
        if not self._lookupRecord(False):
            return None
        return Record(self._records.Record)
    installedRecord = property(installedRecord)

    # depcache states
    def markedInstall(self):
        """ Package is marked for install """
        return self._depcache.MarkedInstall(self._pkg)
    markedInstall = property(markedInstall)

    def markedUpgrade(self):
        """ Package is marked for upgrade """
        return self._depcache.MarkedUpgrade(self._pkg)
    markedUpgrade = property(markedUpgrade)

    def markedDelete(self):
        """ Package is marked for delete """
        return self._depcache.MarkedDelete(self._pkg)
    markedDelete = property(markedDelete) 

    def markedKeep(self):
        """ Package is marked for keep """
        return self._depcache.MarkedKeep(self._pkg)
    markedKeep = property(markedKeep)

    def markedDowngrade(self):
        """ Package is marked for downgrade """
        return self._depcache.MarkedDowngrade(self._pkg)
    markedDowngrade = property(markedDowngrade)

    def markedReinstall(self):
        """ Package is marked for reinstall """
        return self._depcache.MarkedReinstall(self._pkg)
    markedReinstall = property(markedReinstall)

    def isInstalled(self):
        """ Package is installed """
        return (self._pkg.CurrentVer != None)
    isInstalled = property(isInstalled)

    def isUpgradable(self):
        """ Package is upgradable """    
        return self.isInstalled and self._depcache.IsUpgradable(self._pkg)
    isUpgradable = property(isUpgradable)

    def isAutoRemovable(self):
        """ 
        Package is installed as a automatic dependency and is
        no longer required
        """
        return self.isInstalled and self._depcache.IsGarbage(self._pkg)
    isAutoRemovable = property(isAutoRemovable)

    # size
    def packageSize(self):
        """ The size of the candidate deb package """
        ver = self._depcache.GetCandidateVer(self._pkg)
        return ver.Size
    packageSize = property(packageSize)

    def installedPackageSize(self):
        """ The size of the installed deb package """
        ver = self._pkg.CurrentVer
        return ver.Size
    installedPackageSize = property(installedPackageSize)

    def candidateInstalledSize(self, UseCandidate=True):
        """ The size of the candidate installed package """
        ver = self._depcache.GetCandidateVer(self._pkg)
    candidateInstalledSize = property(candidateInstalledSize)

    def installedSize(self):
        """ The size of the currently installed package """
        ver = self._pkg.CurrentVer
        if ver is None:
            return 0
        return ver.InstalledSize
    installedSize = property(installedSize)

    # canidate origin
    class Origin:
        def __init__(self, pkg, VerFileIter):
            self.component = VerFileIter.Component
            self.archive = VerFileIter.Archive
            self.origin = VerFileIter.Origin
            self.label = VerFileIter.Label
            self.site = VerFileIter.Site
            # check the trust
            indexfile = pkg._list.FindIndex(VerFileIter)
            if indexfile and indexfile.IsTrusted:
                self.trusted = True
            else:
                self.trusted = False
        def __repr__(self):
            return "component: '%s' archive: '%s' origin: '%s' label: '%s' " \
                   "site '%s' isTrusted: '%s'"%  (self.component, self.archive,
                                                  self.origin, self.label,
                                                  self.site, self.trusted)
        
    def candidateOrigin(self):
        ver = self._depcache.GetCandidateVer(self._pkg)
        if not ver:
            return None
        origins = []
        for (verFileIter,index) in ver.FileList:
            origins.append(self.Origin(self, verFileIter))
        return origins
    candidateOrigin = property(candidateOrigin)

    # depcache actions
    def markKeep(self):
        """ mark a package for keep """
        self._pcache.cachePreChange()
        self._depcache.MarkKeep(self._pkg)
        self._pcache.cachePostChange()
    def markDelete(self, autoFix=True, purge=False):
        """ mark a package for delete. Run the resolver if autoFix is set.
            Mark the package as purge (remove with configuration) if 'purge'
            is set.
            """
        self._pcache.cachePreChange()
        self._depcache.MarkDelete(self._pkg, purge)
        # try to fix broken stuffsta
        if autoFix and self._depcache.BrokenCount > 0:
            Fix = apt_pkg.GetPkgProblemResolver(self._depcache)
            Fix.Clear(self._pkg)
            Fix.Protect(self._pkg)
            Fix.Remove(self._pkg)
            Fix.InstallProtect()
            Fix.Resolve()
        self._pcache.cachePostChange()
    def markInstall(self, autoFix=True, autoInst=True, fromUser=True):
        """ mark a package for install. Run the resolver if autoFix is set,
            automatically install required dependencies if autoInst is set
            record it as automatically installed when fromuser is set to false
        """
        self._pcache.cachePreChange()
        self._depcache.MarkInstall(self._pkg, autoInst, fromUser)
        # try to fix broken stuff
        if autoFix and self._depcache.BrokenCount > 0:
            fixer = apt_pkg.GetPkgProblemResolver(self._depcache)
            fixer.Clear(self._pkg)
            fixer.Protect(self._pkg)
            fixer.Resolve(True)
        self._pcache.cachePostChange()
    def markUpgrade(self):
        """ mark a package for upgrade """
        if self.isUpgradable:
            self.markInstall()
        else:
            # FIXME: we may want to throw a exception here
            sys.stderr.write("MarkUpgrade() called on a non-upgrable pkg: '%s'\n"  %self._pkg.Name)

    def commit(self, fprogress, iprogress):
        """ commit the changes, need a FetchProgress and InstallProgress
            object as argument
        """
        self._depcache.Commit(fprogress, iprogress)
        

# self-test
if __name__ == "__main__":
    print "Self-test for the Package modul"
    apt_pkg.init()
    cache = apt_pkg.GetCache()
    depcache = apt_pkg.GetDepCache(cache)
    records = apt_pkg.GetPkgRecords(cache)
    sourcelist = apt_pkg.GetPkgSourceList()

    pkgiter = cache["apt-utils"]
    pkg = Package(cache, depcache, records, sourcelist, None, pkgiter)
    print "Name: %s " % pkg.name
    print "ID: %s " % pkg.id
    print "Priority (Candidate): %s " % pkg.priority
    print "Priority (Installed): %s " % pkg.installedPriority
    print "Installed: %s " % pkg.installedVersion
    print "Candidate: %s " % pkg.candidateVersion
    print "CandidateDownloadable: %s" % pkg.candidateDownloadable
    print "CandidateOrigins: %s" % pkg.candidateOrigin
    print "SourcePkg: %s " % pkg.sourcePackageName
    print "Section: %s " % pkg.section
    print "Summary: %s" % pkg.summary
    print "Description (formated) :\n%s" % pkg.description
    print "Description (unformated):\n%s" % pkg.rawDescription
    print "InstalledSize: %s " % pkg.installedSize
    print "PackageSize: %s " % pkg.packageSize
    print "Dependencies: %s" % pkg.installedDependencies
    for dep in pkg.candidateDependencies:
        print ",".join(["%s (%s) (%s) (%s)" % (o.name,o.version,o.relation, o.preDepend) for o in dep.or_dependencies])
    print "arch: %s" % pkg.architecture
    print "homepage: %s" % pkg.homepage
    print "rec: ",pkg.candidateRecord

    # now test install/remove
    import apt
    progress = apt.progress.OpTextProgress()
    cache = apt.Cache(progress)
    for i in [True, False]:
        print "Running install on random upgradable pkgs with AutoFix: %s " % i
        for name in cache.keys():
            pkg = cache[name]
            if pkg.isUpgradable:
                if random.randint(0,1) == 1:
                    pkg.markInstall(i)
        print "Broken: %s " % cache._depcache.BrokenCount
        print "InstCount: %s " % cache._depcache.InstCount

    print
    # get a new cache
    for i in [True, False]:
        print "Randomly remove some packages with AutoFix: %s" % i
        cache = apt.Cache(progress)
        for name in cache.keys():
            if random.randint(0,1) == 1:
                try:
                    cache[name].markDelete(i)
                except SystemError:
                    print "Error trying to remove: %s " % name
        print "Broken: %s " % cache._depcache.BrokenCount
        print "DelCount: %s " % cache._depcache.DelCount

########NEW FILE########
__FILENAME__ = progress
# Progress.py - progress reporting classes
#  
#  Copyright (c) 2005 Canonical
#  
#  Author: Michael Vogt <michael.vogt@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import sys
import os
import re
import fcntl
import string
from errno import *
import select
import apt_pkg

import apt

class OpProgress(object):
    """ Abstract class to implement reporting on cache opening
        Subclass this class to implement simple Operation progress reporting
    """
    def __init__(self):
        pass
    def update(self, percent):
        pass
    def done(self):
        pass

class OpTextProgress(OpProgress):
    """ A simple text based cache open reporting class """
    def __init__(self):
        OpProgress.__init__(self)
    def update(self, percent):
        sys.stdout.write("\r%s: %.2i  " % (self.subOp,percent))
        sys.stdout.flush()
    def done(self):
        sys.stdout.write("\r%s: Done\n" % self.op)



class FetchProgress(object):
    """ Report the download/fetching progress
        Subclass this class to implement fetch progress reporting
    """

    # download status constants
    dlDone = 0
    dlQueued = 1
    dlFailed = 2
    dlHit = 3
    dlIgnored = 4
    dlStatusStr = {dlDone : "Done",
                   dlQueued : "Queued",
                   dlFailed : "Failed",
                   dlHit : "Hit",
                   dlIgnored : "Ignored"}
    
    def __init__(self):
        self.eta = 0.0
        self.percent = 0.0
        pass
    
    def start(self):
        pass
    
    def stop(self):
        pass
    
    def updateStatus(self, uri, descr, shortDescr, status):
        pass

    def pulse(self):
        """ called periodically (to update the gui), importend to
            return True to continue or False to cancel
        """
        self.percent = ((self.currentBytes + self.currentItems)*100.0)/float(self.totalBytes+self.totalItems)
        if self.currentCPS > 0:
            self.eta = (self.totalBytes-self.currentBytes)/float(self.currentCPS)
        return True
    def mediaChange(self, medium, drive):
        pass

class TextFetchProgress(FetchProgress):
    """ Ready to use progress object for terminal windows """
    def __init__(self):
        self.items = {}
    def updateStatus(self, uri, descr, shortDescr, status):
        if status != self.dlQueued:
            print "\r%s %s" % (self.dlStatusStr[status], descr)
        self.items[uri] = status
    def pulse(self):
        FetchProgress.pulse(self)
        if self.currentCPS > 0:
            s = "[%2.f%%] %sB/s %s" % (self.percent,
                                       apt_pkg.SizeToStr(int(self.currentCPS)),
                                       apt_pkg.TimeToStr(int(self.eta)))
        else:
            s = "%2.f%% [Working]" % (self.percent)
        print "\r%s" % (s),
        sys.stdout.flush()
        return True
    def stop(self):
        print "\rDone downloading            " 
    def mediaChange(self, medium, drive):
        """ react to media change events """
        res = True;
        print "Media change: please insert the disc labeled \
               '%s' in the drive '%s' and press enter" % (medium,drive)
        s = sys.stdin.readline()
        if(s == 'c' or s == 'C'):
            res = false;
        return res

class DumbInstallProgress(object):
    """ Report the install progress
        Subclass this class to implement install progress reporting
    """
    def __init__(self):
        pass
    def startUpdate(self):
        pass
    def run(self, pm):
        return pm.DoInstall()
    def finishUpdate(self):
        pass
    def updateInterface(self):
        pass

class InstallProgress(DumbInstallProgress):
    """ A InstallProgress that is pretty useful.
        It supports the attributes 'percent' 'status' and callbacks
        for the dpkg errors and conffiles and status changes 
     """
    def __init__(self):
        DumbInstallProgress.__init__(self)
        self.selectTimeout = 0.1
        (read, write) = os.pipe()
        self.writefd=write
        self.statusfd = os.fdopen(read, "r")
        fcntl.fcntl(self.statusfd.fileno(), fcntl.F_SETFL,os.O_NONBLOCK)
        self.read = ""
        self.percent = 0.0
        self.status = ""
    def error(self, pkg, errormsg):
        " called when a error is detected during the install "
        pass
    def conffile(self,current,new):
        " called when a conffile question from dpkg is detected "
        pass
    def statusChange(self, pkg, percent, status):
	" called when the status changed "
	pass
    def updateInterface(self):
        if self.statusfd != None:
                try:
		    while not self.read.endswith("\n"):
	                    self.read += os.read(self.statusfd.fileno(),1)
                except OSError, (errno,errstr):
                    # resource temporarly unavailable is ignored
                    if errno != EAGAIN and errnor != EWOULDBLOCK:
                        print errstr
                if self.read.endswith("\n"):
                    s = self.read
                    #print s
                    try:
                        (status, pkg, percent, status_str) = string.split(s, ":",3)
                    except ValueError, e:
                        # silently ignore lines that can't be parsed
                        self.read = ""
                        return
                    #print "percent: %s %s" % (pkg, float(percent)/100.0)
                    if status == "pmerror":
                        self.error(pkg,status_str)
                    elif status == "pmconffile":
                        # we get a string like this:
                        # 'current-conffile' 'new-conffile' useredited distedited
                        match = re.compile("\s*\'(.*)\'\s*\'(.*)\'.*").match(status_str)
                        if match:
                            self.conffile(match.group(1), match.group(2))
                    elif status == "pmstatus":
                        if float(percent) != self.percent or \
                           status_str != self.status:
                            self.statusChange(pkg, float(percent), status_str.strip())
                        self.percent = float(percent)
                        self.status = string.strip(status_str)
                    self.read = ""
    def fork(self):
        return os.fork()
    def waitChild(self):
        while True:
            select.select([self.statusfd],[],[], self.selectTimeout)
            self.updateInterface()
            (pid, res) = os.waitpid(self.child_pid,os.WNOHANG)
            if pid == self.child_pid:
                break
        return os.WEXITSTATUS(res)
    def run(self, pm):
        pid = self.fork()
        if pid == 0:
            # child
            res = pm.DoInstall(self.writefd)
            os._exit(res)
        self.child_pid = pid
        res = self.waitChild()
        return res

class CdromProgress:
    """ Report the cdrom add progress
        Subclass this class to implement cdrom add progress reporting
    """
    def __init__(self):
        pass
    def update(self, text, step):
        """ update is called regularly so that the gui can be redrawn """
        pass
    def askCdromName(self):
        pass
    def changeCdrom(self):
        pass

# module test code
if __name__ == "__main__":
    import apt_pkg
    apt_pkg.init()
    progress = OpTextProgress()
    cache = apt_pkg.GetCache(progress)
    depcache = apt_pkg.GetDepCache(cache)
    depcache.Init(progress)

    fprogress = TextFetchProgress()
    cache.Update(fprogress)

########NEW FILE########
__FILENAME__ = distinfo
#!/usr/bin/env python
#  
#  distinfo.py - provide meta information for distro repositories
#
#  Copyright (c) 2005 Gustavo Noronha Silva
#                2006-2007 Sebastian Heinlein
#
#  Author: Gustavo Noronha Silva <kov@debian.org>
#          Sebastian Heinlein <glatzor@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import os
import gettext
from os import getenv
import ConfigParser
import string
import apt_pkg

#from gettext import gettext as _
import gettext
def _(s): return gettext.dgettext("python-apt", s)

import re

class Template:
    def __init__(self):
        self.name = None
        self.child = False
        self.parents = []          # ref to parent template(s)
        self.match_name = None
        self.description = None
        self.base_uri = None
        self.type = None
        self.components = []
        self.children = []
        self.match_uri = None
        self.mirror_set = {}
        self.distribution = None
        self.available = True

    def has_component(self, comp):
        ''' Check if the distribution provides the given component '''
        return comp in map(lambda c: c.name, self.components)
    
    def is_mirror(self, url):
        ''' Check if a given url of a repository is a valid mirror '''
        proto, hostname, dir = split_url(url)
        if self.mirror_set.has_key(hostname):
            return self.mirror_set[hostname].has_repository(proto, dir)
        else:
            return False

class Component:
    def __init__(self, name, desc=None, long_desc=None):
        self.name = name
        self.description = desc
        self.description_long = long_desc
    def get_description(self):
        if self.description_long != None:
            return self.description_long
        elif self.description != None:
            return self.description
        else:
            return None
    def set_description(self, desc):
        self.description = desc
    def set_description_long(self, desc):
        self.description_long = desc
    def get_description_long(self):
        return self.description_long

class Mirror:
    ''' Storage for mirror related information '''
    def __init__(self, proto, hostname, dir, location=None):
        self.hostname = hostname
        self.repositories = []
        self.add_repository(proto, dir)
        self.location = location
    def add_repository(self, proto, dir):
        self.repositories.append(Repository(proto, dir))
    def get_repositories_for_proto(self, proto):
        return filter(lambda r: r.proto == proto, self.repositories)
    def has_repository(self, proto, dir):
        if dir is None:
            return False
        for r in self.repositories:
            if r.proto == proto and dir in r.dir:
                return True
        return False
    def get_repo_urls(self):
        return map(lambda r: r.get_url(self.hostname), self.repositories)
    def get_location(self):
        return self.location
    def set_location(self, location):
        self.location = location

class Repository:
    def __init__(self, proto, dir):
        self.proto = proto
        self.dir = dir
    def get_info(self):
        return self.proto, self.dir
    def get_url(self, hostname):
        return "%s://%s/%s" % (self.proto, hostname, self.dir)

def split_url(url):
    ''' split a given URL into the protocoll, the hostname and the dir part '''
    return map(lambda a,b: a, re.split(":*\/+", url, maxsplit=2),
                              [None, None, None])

class DistInfo:
    def __init__(self,
                 dist = None,
                 base_dir = "/usr/share/python-apt/templates"):
        self.metarelease_uri = ''
        self.templates = []
        self.arch = apt_pkg.Config.Find("APT::Architecture")

        location = None
        match_loc = re.compile(r"^#LOC:(.+)$")
        match_mirror_line = re.compile(r"^(#LOC:.+)|(((http)|(ftp)|(rsync)|(file)|(https))://[A-Za-z/\.:\-_]+)$")
        #match_mirror_line = re.compile(r".+")

        if not dist:
            pipe = os.popen("lsb_release -i -s")
            dist = pipe.read().strip()
            pipe.close()
            del pipe

        self.dist = dist


        map_mirror_sets = {}

        dist_fname = "%s/%s.info" % (base_dir, dist)
        dist_file = open (dist_fname)
        if not dist_file:
            return
        template = None
        component = None
        for line in dist_file:
            tokens = line.split (':', 1)
            if len (tokens) < 2:
                continue
            field = tokens[0].strip ()
            value = tokens[1].strip ()
            if field == 'ChangelogURI':
                self.changelogs_uri = _(value)
            elif field == 'MetaReleaseURI':
                self.metarelease_uri = value
            elif field == 'Suite':
                self.finish_template(template, component)
                component=None
                template = Template()
                template.name = value
                template.distribution = dist
                template.match_name = "^%s$" % value
            elif field == 'MatchName':
                template.match_name = value
            elif field == 'ParentSuite':
                template.child = True
                for nanny in self.templates:
                    # look for parent and add back ref to it
                    if nanny.name == value:
                        template.parents.append(nanny)
                        nanny.children.append(template)
            elif field == 'Available':
                template.available = value
            elif field == 'RepositoryType':
                template.type = value
            elif field == 'BaseURI' and not template.base_uri:
                template.base_uri = value
            elif field == 'BaseURI-%s' % self.arch:
                template.base_uri = value
            elif field == 'MatchURI' and not template.match_uri:
                template.match_uri = value
            elif field == 'MatchURI-%s' % self.arch:
                template.match_uri = value
            elif (field == 'MirrorsFile' or 
                  field == 'MirrorsFile-%s' % self.arch):
                if not map_mirror_sets.has_key(value):
                    mirror_set = {}
                    try:
                        mirror_data = filter(match_mirror_line.match,
                                             map(string.strip, open(value)))
                    except:
                        print "WARNING: Failed to read mirror file"
                        mirror_data = []
                    for line in mirror_data:
                        if line.startswith("#LOC:"):
                            location = match_loc.sub(r"\1", line)
                            continue
                        (proto, hostname, dir) = split_url(line)
                        if mirror_set.has_key(hostname):
                            mirror_set[hostname].add_repository(proto, dir)
                        else:
                            mirror_set[hostname] = Mirror(proto, hostname, dir, location)
                    map_mirror_sets[value] = mirror_set
                template.mirror_set = map_mirror_sets[value]
            elif field == 'Description':
                template.description = _(value)
            elif field == 'Component':
                if component and not template.has_component(component.name):
                    template.components.append(component)
                component = Component(value)
            elif field == 'CompDescription':
                component.set_description(_(value))
            elif field == 'CompDescriptionLong':
                component.set_description_long(_(value))
        self.finish_template(template, component)
        template=None
        component=None

    def finish_template(self, template, component):
        " finish the current tempalte "
        if not template:
            return
        # reuse some properties of the parent template
        if template.match_uri == None and template.child:
            for t in template.parents:
                if t.match_uri:
                    template.match_uri = t.match_uri
                    break
        if template.mirror_set == {} and template.child:
            for t in template.parents:
                if t.match_uri:
                    template.mirror_set = t.mirror_set
                    break
        if component and not template.has_component(component.name):
            template.components.append(component)
            component = None
        self.templates.append(template)    


if __name__ == "__main__":
    d = DistInfo ("Ubuntu", "/usr/share/python-apt/templates")
    print d.changelogs_uri
    for template in d.templates:
        print "\nSuite: %s" % template.name
        print "Desc: %s" % template.description
        print "BaseURI: %s" % template.base_uri
        print "MatchURI: %s" % template.match_uri
        if template.mirror_set != {}:
            print "Mirrors: %s" % template.mirror_set.keys()
        for comp in template.components:
            print " %s -%s -%s" % (comp.name, 
                                   comp.description, 
                                   comp.description_long)
        for child in template.children:
            print "  %s" % child.description

########NEW FILE########
__FILENAME__ = distro
#  distro.py - Provide a distro abstraction of the sources.list
#
#  Copyright (c) 2004-2007 Canonical Ltd.
#                2006-2007 Sebastian Heinlein
#  
#  Authors: Sebastian Heinlein <glatzor@ubuntu.com>
#           Michael Vogt <mvo@debian.org>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import string
import gettext
import re
import os
import sys

import gettext
def _(s): return gettext.dgettext("python-apt", s)


class NoDistroTemplateException(Exception):
  pass

class Distribution:
  def __init__(self, id, codename, description, release):
    """ Container for distribution specific informations """
    # LSB information
    self.id = id
    self.codename = codename
    self.description = description
    self.release = release

    self.binary_type = "deb"
    self.source_type = "deb-src"

  def get_sources(self, sourceslist):
    """
    Find the corresponding template, main and child sources 
    for the distribution 
    """

    self.sourceslist = sourceslist
    # corresponding sources
    self.source_template = None
    self.child_sources = []
    self.main_sources = []
    self.disabled_sources = []
    self.cdrom_sources = []
    self.download_comps = []
    self.enabled_comps = []
    self.cdrom_comps = []
    self.used_media = []
    self.get_source_code = False
    self.source_code_sources = []

    # location of the sources
    self.default_server = ""
    self.main_server = ""
    self.nearest_server = ""
    self.used_servers = []

    # find the distro template
    for template in self.sourceslist.matcher.templates:
        if self.is_codename(template.name) and\
           template.distribution == self.id:
            #print "yeah! found a template for %s" % self.description
            #print template.description, template.base_uri, template.components
            self.source_template = template
            break
    if self.source_template == None:
        raise (NoDistroTemplateException,
               "Error: could not find a distribution template")

    # find main and child sources
    media = []
    comps = []
    cdrom_comps = []
    enabled_comps = []
    source_code = []
    for source in self.sourceslist.list:
        if source.invalid == False and\
           self.is_codename(source.dist) and\
           source.template and\
           self.is_codename(source.template.name):
            #print "yeah! found a distro repo:  %s" % source.line
            # cdroms need do be handled differently
            if source.uri.startswith("cdrom:") and \
               source.disabled == False:
                self.cdrom_sources.append(source)
                cdrom_comps.extend(source.comps)
            elif source.uri.startswith("cdrom:") and \
                 source.disabled == True:
                self.cdrom_sources.append(source)
            elif source.type == self.binary_type  and \
                 source.disabled == False:
                self.main_sources.append(source)
                comps.extend(source.comps)
                media.append(source.uri)
            elif source.type == self.binary_type and \
                 source.disabled == True:
                self.disabled_sources.append(source)
            elif source.type == self.source_type and source.disabled == False:
                self.source_code_sources.append(source)
            elif source.type == self.source_type and source.disabled == True:
                self.disabled_sources.append(source)
        if source.invalid == False and\
           source.template in self.source_template.children:
            if source.disabled == False and source.type == self.binary_type:
                self.child_sources.append(source)
            elif source.disabled == False and source.type == self.source_type:
                self.source_code_sources.append(source)
            else:
                self.disabled_sources.append(source)
    self.download_comps = set(comps)
    self.cdrom_comps = set(cdrom_comps)
    enabled_comps.extend(comps)
    enabled_comps.extend(cdrom_comps)
    self.enabled_comps = set(enabled_comps)
    self.used_media = set(media)

    self.get_mirrors()
  
  def get_mirrors(self, mirror_template=None):
    """
    Provide a set of mirrors where you can get the distribution from
    """
    # the main server is stored in the template
    self.main_server = self.source_template.base_uri

    # other used servers
    for medium in self.used_media:
        if not medium.startswith("cdrom:"):
            # seems to be a network source
            self.used_servers.append(medium)

    if len(self.main_sources) == 0:
        self.default_server = self.main_server
    else:
        self.default_server = self.main_sources[0].uri

    # get a list of country codes and real names
    self.countries = {}
    try:
        f = open("/usr/share/iso-codes/iso_3166.tab", "r")
        lines = f.readlines()
        for line in lines:
            parts = line.split("\t")
            self.countries[parts[0].lower()] = parts[1].strip()
    except:
        print "could not open file '%s'" % file
    else:
        f.close()

    # try to guess the nearest mirror from the locale
    self.country = None
    self.country_code = None
    locale = os.getenv("LANG", default="en_UK")
    a = locale.find("_")
    z = locale.find(".")
    if z == -1:
        z = len(locale)
    country_code = locale[a+1:z].lower()

    if mirror_template:
      self.nearest_server = mirror_template % country_code

    if self.countries.has_key(country_code):
        self.country = self.countries[country_code]
        self.country_code = country_code

  def _get_mirror_name(self, server):
      ''' Try to get a human readable name for the main mirror of a country
          Customize for different distributions '''
      country = None
      i = server.find("://")
      l = server.find(".archive.ubuntu.com")
      if i != -1 and l != -1:
          country = server[i+len("://"):l]
      if self.countries.has_key(country):
          # TRANSLATORS: %s is a country
          return _("Server for %s") % \
                 gettext.dgettext("iso_3166",
                                  self.countries[country].rstrip()).rstrip()
      else:
          return("%s" % server.rstrip("/ "))

  def get_server_list(self):
    ''' Return a list of used and suggested servers '''
    def compare_mirrors(mir1, mir2):
        '''Helper function that handles comaprision of mirror urls
           that could contain trailing slashes'''
        return re.match(mir1.strip("/ "), mir2.rstrip("/ "))
    
    # Store all available servers:
    # Name, URI, active
    mirrors = []
    if len(self.used_servers) < 1 or \
       (len(self.used_servers) == 1 and \
        compare_mirrors(self.used_servers[0], self.main_server)):
        mirrors.append([_("Main server"), self.main_server, True]) 
        mirrors.append([self._get_mirror_name(self.nearest_server), 
                       self.nearest_server, False])
    elif len(self.used_servers) == 1 and not \
         compare_mirrors(self.used_servers[0], self.main_server):
        mirrors.append([_("Main server"), self.main_server, False]) 
        # Only one server is used
        server = self.used_servers[0]

        # Append the nearest server if it's not already used            
        if not compare_mirrors(server, self.nearest_server):
            mirrors.append([self._get_mirror_name(self.nearest_server), 
                           self.nearest_server, False])
        mirrors.append([self._get_mirror_name(server), server, True])

    elif len(self.used_servers) > 1:
        # More than one server is used. Since we don't handle this case
        # in the user interface we set "custom servers" to true and 
        # append a list of all used servers 
        mirrors.append([_("Main server"), self.main_server, False])
        mirrors.append([self._get_mirror_name(self.nearest_server), 
                                        self.nearest_server, False])
        mirrors.append([_("Custom servers"), None, True])
        for server in self.used_servers:
            if compare_mirrors(server, self.nearest_server) or\
               compare_mirrors(server, self.main_server):
                continue
            elif not [self._get_mirror_name(server), server, False] in mirrors:
                mirrors.append([self._get_mirror_name(server), server, False])

    return mirrors

  def add_source(self, type=None, 
                 uri=None, dist=None, comps=None, comment=""):
    """
    Add distribution specific sources
    """
    if uri == None:
        # FIXME: Add support for the server selector
        uri = self.default_server
    if dist == None:
        dist = self.codename
    if comps == None:
        comps = list(self.enabled_comps)
    if type == None:
        type = self.binary_type
    new_source = self.sourceslist.add(type, uri, dist, comps, comment)
    # if source code is enabled add a deb-src line after the new
    # source
    if self.get_source_code == True and type == self.binary_type:
        self.sourceslist.add(self.source_type, uri, dist, comps, comment,
                             file=new_source.file,
                             pos=self.sourceslist.list.index(new_source)+1)

  def enable_component(self, comp):
    """
    Enable a component in all main, child and source code sources
    (excluding cdrom based sources)

    comp:         the component that should be enabled
    """
    def add_component_only_once(source, comps_per_dist):
        """
        Check if we already added the component to the repository, since
        a repository could be splitted into different apt lines. If not
        add the component
        """
        # if we don't that distro, just reutnr (can happen for e.g.
        # dapper-update only in deb-src
        if not comps_per_dist.has_key(source.dist):
          return
        # if we have seen this component already for this distro,
        # return (nothing to do
        if comp in comps_per_dist[source.dist]:
          return
        # add it
        source.comps.append(comp)
        comps_per_dist[source.dist].add(comp)

    sources = []
    sources.extend(self.main_sources)
    sources.extend(self.child_sources)
    # store what comps are enabled already per distro (where distro is
    # e.g. "dapper", "dapper-updates")
    comps_per_dist = {}
    comps_per_sdist = {}
    for s in sources:
      if s.type == self.binary_type: 
        if not comps_per_dist.has_key(s.dist):
          comps_per_dist[s.dist] = set()
        map(comps_per_dist[s.dist].add, s.comps)
    for s in self.source_code_sources:
      if s.type == self.source_type:
        if not comps_per_sdist.has_key(s.dist):
          comps_per_sdist[s.dist] = set()
        map(comps_per_sdist[s.dist].add, s.comps)

    # check if there is a main source at all
    if len(self.main_sources) < 1:
        # create a new main source
        self.add_source(comps=["%s"%comp])
    else:
        # add the comp to all main, child and source code sources
        for source in sources:
             add_component_only_once(source, comps_per_dist)

    # check if there is a main source code source at all
    if self.get_source_code == True:
        if len(self.source_code_sources) < 1:
            # create a new main source
            self.add_source(type=self.source_type, comps=["%s"%comp])
        else:
            # add the comp to all main, child and source code sources
            for source in self.source_code_sources:
                add_component_only_once(source, comps_per_sdist)

  def disable_component(self, comp):
    """
    Disable a component in all main, child and source code sources
    (excluding cdrom based sources)
    """
    sources = []
    sources.extend(self.main_sources)
    sources.extend(self.child_sources)
    sources.extend(self.source_code_sources)
    if comp in self.cdrom_comps:
        sources = []
        sources.extend(self.main_sources)
    for source in sources:
        if comp in source.comps: 
            source.comps.remove(comp)
            if len(source.comps) < 1: 
               self.sourceslist.remove(source)

  def change_server(self, uri):
    ''' Change the server of all distro specific sources to
        a given host '''
    def change_server_of_source(source, uri, seen):
        # Avoid creating duplicate entries
        source.uri = uri
        for comp in source.comps:
            if [source.uri, source.dist, comp] in seen:
                source.comps.remove(comp)
            else:
                seen.append([source.uri, source.dist, comp])
        if len(source.comps) < 1:
            self.sourceslist.remove(source)
    seen_binary = []
    seen_source = []
    self.default_server = uri
    for source in self.main_sources:
        change_server_of_source(source, uri, seen_binary)
    for source in self.child_sources:
        # Do not change the forces server of a child source
        if source.template.base_uri == None or \
           source.template.base_uri != source.uri:
            change_server_of_source(source, uri, seen_binary)
    for source in self.source_code_sources:
        change_server_of_source(source, uri, seen_source)

  def is_codename(self, name):
    ''' Compare a given name with the release codename. '''
    if name == self.codename:
        return True
    else:
        return False

class DebianDistribution(Distribution):
  ''' Class to support specific Debian features '''

  def is_codename(self, name):
    ''' Compare a given name with the release codename and check if
        if it can be used as a synonym for a development releases '''
    if name == self.codename or self.release in ("testing", "unstable"):
        return True
    else:
        return False

  def _get_mirror_name(self, server):
      ''' Try to get a human readable name for the main mirror of a country
          Debian specific '''
      country = None
      i = server.find("://ftp.")
      l = server.find(".debian.org")
      if i != -1 and l != -1:
          country = server[i+len("://ftp."):l]
      if self.countries.has_key(country):
          # TRANSLATORS: %s is a country
          return _("Server for %s") % \
                 gettext.dgettext("iso_3166",
                                  self.countries[country].rstrip()).rstrip()
      else:
          return("%s" % server.rstrip("/ "))

  def get_mirrors(self):
    Distribution.get_mirrors(self,
                             mirror_template="http://ftp.%s.debian.org/debian/")

class UbuntuDistribution(Distribution):
  ''' Class to support specific Ubuntu features '''
  def get_mirrors(self):
    Distribution.get_mirrors(self,
                             mirror_template="http://%s.archive.ubuntu.com/ubuntu/")

def get_distro(id=None,codename=None,description=None,release=None):
    """ 
    Check the currently used distribution and return the corresponding
    distriubtion class that supports distro specific features. 
    
    If no paramter are given the distro will be auto detected via
    a call to lsb-release
    """
    # make testing easier
    if not (id and codename and description and release):
      lsb_info = []
      for lsb_option in ["-i", "-c", "-d", "-r"]:
        pipe = os.popen("lsb_release %s -s" % lsb_option)
        lsb_info.append(pipe.read().strip())
        del pipe
      (id, codename, description, release) = lsb_info
    if id == "Ubuntu":
        return UbuntuDistribution(id, codename, description, 
                                  release)
    elif id == "Debian":
        return DebianDistribution(id, codename, description, release)
    else:
        return Distribution(id, codename, description, release)


########NEW FILE########
__FILENAME__ = sourceslist
#  aptsource.py - Provide an abstraction of the sources.list
#  
#  Copyright (c) 2004-2007 Canonical Ltd.
#                2004 Michiel Sikkes
#                2006-2007 Sebastian Heinlein
#  
#  Author: Michiel Sikkes <michiel@eyesopened.nl>
#          Michael Vogt <mvo@debian.org>
#          Sebastian Heinlein <glatzor@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA
 
import string
import gettext
import re
import apt_pkg
import glob
import shutil
import time
import os.path
import sys

#from UpdateManager.Common.DistInfo import DistInfo
from distinfo import DistInfo

# some global helpers
def is_mirror(master_uri, compare_uri):
  """check if the given add_url is idential or a mirror of orig_uri
    e.g. master_uri = archive.ubuntu.com
      compare_uri = de.archive.ubuntu.com
      -> True
  """
  # remove traling spaces and "/"
  compare_uri = compare_uri.rstrip("/ ")
  master_uri = master_uri.rstrip("/ ")
  # uri is identical
  if compare_uri == master_uri:
    #print "Identical"
    return True
  # add uri is a master site and orig_uri has the from "XX.mastersite"
  # (e.g. de.archive.ubuntu.com)
  try:
    compare_srv = compare_uri.split("//")[1]
    master_srv = master_uri.split("//")[1]
    #print "%s == %s " % (add_srv, orig_srv)
  except IndexError: # ok, somethings wrong here
    #print "IndexError"
    return False
  # remove the leading "<country>." (if any) and see if that helps
  if "." in compare_srv and \
         compare_srv[compare_srv.index(".")+1:] == master_srv:
    #print "Mirror"
    return True
  return False

def uniq(s):
  """ simple and efficient way to return uniq list """
  return list(set(s))

class SourceEntry:
  """ single sources.list entry """
  def __init__(self, line,file=None):
    self.invalid = False            # is the source entry valid
    self.disabled = False           # is it disabled ('#' in front)
    self.type = ""                  # what type (deb, deb-src)
    self.uri = ""                   # base-uri
    self.dist = ""                  # distribution (dapper, edgy, etc)
    self.comps = []                 # list of available componetns (may empty)
    self.comment = ""               # (optional) comment
    self.line = line                # the original sources.list line
    if file == None:                
      file = apt_pkg.Config.FindDir("Dir::Etc")+apt_pkg.Config.Find("Dir::Etc::sourcelist")
    self.file = file               # the file that the entry is located in
    self.parse(line)
    self.template = None           # type DistInfo.Suite
    self.children = []

  def __eq__(self, other):         
    """ equal operator for two sources.list entries """
    return (self.disabled == other.disabled and
            self.type == other.type and
            self.uri == other.uri and
            self.dist == other.dist and
            self.comps == other.comps)


  def mysplit(self, line):
    """ a split() implementation that understands the sources.list
        format better and takes [] into account (for e.g. cdroms) """
    line = string.strip(line)
    pieces = []
    tmp = ""
    # we are inside a [..] block
    p_found = False
    space_found = False
    for i in range(len(line)):
      if line[i] == "[":
        p_found=True
        tmp += line[i]
      elif line[i] == "]":
        p_found=False
        tmp += line[i]
      elif space_found and not line[i].isspace(): # we skip one or more space
        space_found = False
        pieces.append(tmp)
        tmp = line[i]
      elif line[i].isspace() and not p_found:     # found a whitespace
        space_found = True
      else:
        tmp += line[i]
    # append last piece
    if len(tmp) > 0:
      pieces.append(tmp)
    return pieces

  def parse(self,line):
    """ parse a given sources.list (textual) line and break it up
        into the field we have """
    line  = string.strip(self.line)
    #print line
    # check if the source is enabled/disabled
    if line == "" or line == "#": # empty line
      self.invalid = True
      return
    if line[0] == "#":
      self.disabled = True
      pieces = string.split(line[1:])
      # if it looks not like a disabled deb line return 
      if not pieces[0] in ("rpm", "rpm-src", "deb", "deb-src"):
        self.invalid = True
        return
      else:
        line = line[1:]
    # check for another "#" in the line (this is treated as a comment)
    i = line.find("#")
    if i > 0:
      self.comment = line[i+1:]
      line = line[:i]
    # source is ok, split it and see what we have
    pieces = self.mysplit(line)
    # Sanity check
    if len(pieces) < 3:
        self.invalid = True
        return
    # Type, deb or deb-src
    self.type = string.strip(pieces[0])
    # Sanity check
    if self.type not in ("deb", "deb-src", "rpm", "rpm-src"):
      self.invalid = True
      return
    # URI
    self.uri = string.strip(pieces[1])
    if len(self.uri) < 1:
      self.invalid = True
    # distro and components (optional)
    # Directory or distro
    self.dist = string.strip(pieces[2])
    if len(pieces) > 3:
      # List of components
      self.comps = pieces[3:]
    else:
      self.comps = []

  def set_enabled(self, new_value):
    """ set a line to enabled or disabled """
    self.disabled = not new_value
    # enable, remove all "#" from the start of the line
    if new_value == True:
      i=0
      self.line = string.lstrip(self.line)
      while self.line[i] == "#":
        i += 1
      self.line = self.line[i:]
    else:
      # disabled, add a "#" 
      if string.strip(self.line)[0] != "#":
        self.line = "#" + self.line

  def __str__(self):
    """ debug helper """
    return self.str().strip()

  def str(self):
    """ return the current line as string """
    if self.invalid:
      return self.line
    line = ""
    if self.disabled:
      line = "# "
    line += "%s %s %s" % (self.type, self.uri, self.dist)
    if len(self.comps) > 0:
      line += " " + " ".join(self.comps)
    if self.comment != "":
      line += " #"+self.comment
    line += "\n"
    return line
    
class NullMatcher(object):
  """ a Matcher that does nothing """
  def match(self, s):
    return True

class SourcesList:
  """ represents the full sources.list + sources.list.d file """
  def __init__(self,
               withMatcher=True,
               matcherPath="/usr/share/python-apt/templates/"):
    self.list = []          # the actual SourceEntries Type 
    if withMatcher:
      self.matcher = SourceEntryMatcher(matcherPath)
    else:
      self.matcher = NullMatcher()
    self.refresh()

  def refresh(self):
    """ update the list of known entries """
    self.list = []
    # read sources.list
    dir = apt_pkg.Config.FindDir("Dir::Etc")
    file = apt_pkg.Config.Find("Dir::Etc::sourcelist")
    self.load(dir+file)
    # read sources.list.d
    partsdir = apt_pkg.Config.FindDir("Dir::Etc::sourceparts")
    for file in glob.glob("%s/*.list" % partsdir):
      self.load(file)
    # check if the source item fits a predefined template
    for source in self.list:
        if source.invalid == False:
            self.matcher.match(source)

  def __iter__(self):
    """ simple iterator to go over self.list, returns SourceEntry
        types """
    for entry in self.list:
      yield entry
    raise StopIteration

  def add(self, type, uri, dist, orig_comps, comment="", pos=-1, file=None):
    """
    Add a new source to the sources.list.
    The method will search for existing matching repos and will try to 
    reuse them as far as possible
    """
    # create a working copy of the component list so that
    # we can modify it later
    comps = orig_comps[:]
    # check if we have this source already in the sources.list
    for source in self.list:
      if source.disabled == False and source.invalid == False and \
         source.type == type and uri == source.uri and \
         source.dist == dist:
        for new_comp in comps:
          if new_comp in source.comps:
            # we have this component already, delete it from the new_comps
            # list
            del comps[comps.index(new_comp)]
            if len(comps) == 0:
              return source
    for source in self.list:
      # if there is a repo with the same (type, uri, dist) just add the
      # components
      if source.disabled == False and source.invalid == False and \
         source.type == type and uri == source.uri and \
         source.dist == dist:
        comps = uniq(source.comps + comps)
        source.comps = comps
        return source
      # if there is a corresponding repo which is disabled, enable it
      elif source.disabled == True and source.invalid == False and \
           source.type == type and uri == source.uri and \
           source.dist == dist and \
           len(set(source.comps) & set(comps)) == len(comps):
        source.disabled = False
        return source
    # there isn't any matching source, so create a new line and parse it
    line = "%s %s %s" % (type,uri,dist)
    for c in comps:
      line = line + " " + c;
    if comment != "":
      line = "%s #%s\n" %(line,comment)
    line = line + "\n"
    new_entry = SourceEntry(line)
    if file != None:
      new_entry.file = file
    self.matcher.match(new_entry)
    self.list.insert(pos, new_entry)
    return new_entry

  def remove(self, source_entry):
    """ remove the specified entry from the sources.list """
    self.list.remove(source_entry)

  def restoreBackup(self, backup_ext):
    " restore sources.list files based on the backup extension "
    dir = apt_pkg.Config.FindDir("Dir::Etc")
    file = apt_pkg.Config.Find("Dir::Etc::sourcelist")
    if os.path.exists(dir+file+backup_ext) and \
       os.path.exists(dir+file):
      shutil.copy(dir+file+backup_ext,dir+file)
    # now sources.list.d
    partsdir = apt_pkg.Config.FindDir("Dir::Etc::sourceparts")
    for file in glob.glob("%s/*.list" % partsdir):
      if os.path.exists(file+backup_ext):
        shutil.copy(file+backup_ext,file)

  def backup(self, backup_ext=None):
    """ make a backup of the current source files, if no backup extension
        is given, the current date/time is used (and returned) """
    already_backuped = set()
    if backup_ext == None:
      backup_ext = time.strftime("%y%m%d.%H%M")
    for source in self.list:
      if not source.file in already_backuped and os.path.exists(source.file):
        shutil.copy(source.file,"%s%s" % (source.file,backup_ext))
    return backup_ext

  def load(self,file):
    """ (re)load the current sources """
    try:
      f = open(file, "r")
      lines = f.readlines()
      for line in lines:
        source = SourceEntry(line,file)
        self.list.append(source)
    except:
      print "could not open file '%s'" % file
    else:
      f.close()

  def save(self):
    """ save the current sources """
    files = {}
    # write an empty default config file if there aren't any sources
    if len(self.list) == 0:
      path = "%s%s" % (apt_pkg.Config.FindDir("Dir::Etc"),
                       apt_pkg.Config.Find("Dir::Etc::sourcelist"))
      header = ("## See sources.list(5) for more information, especialy\n"
                "# Remember that you can only use http, ftp or file URIs\n"
                "# CDROMs are managed through the apt-cdrom tool.\n")
      open(path,"w").write(header)
      return
    for source in self.list:
      if not files.has_key(source.file):
        files[source.file]=open(source.file,"w")
      files[source.file].write(source.str())
    for f in files:
      files[f].close()

  def check_for_relations(self, sources_list):
    """get all parent and child channels in the sources list"""
    parents = []
    used_child_templates = {}
    for source in sources_list:
      # try to avoid checking uninterressting sources
      if source.template == None:
        continue
      # set up a dict with all used child templates and corresponding 
      # source entries
      if source.template.child == True:
          key = source.template
          if not used_child_templates.has_key(key):
              used_child_templates[key] = []
          temp = used_child_templates[key]
          temp.append(source)
      else:
          # store each source with children aka. a parent :)
          if len(source.template.children) > 0:
              parents.append(source)
    #print self.used_child_templates
    #print self.parents
    return (parents, used_child_templates)

# matcher class to make a source entry look nice
# lots of predefined matchers to make it i18n/gettext friendly
class SourceEntryMatcher:
  def __init__(self, matcherPath):
    self.templates = []
    # Get the human readable channel and comp names from the channel .infos
    spec_files = glob.glob("%s/*.info" % matcherPath)
    for f in spec_files:
        f = os.path.basename(f)
        i = f.find(".info")
        f = f[0:i]
        dist = DistInfo(f,base_dir=matcherPath)
        for template in dist.templates:
            if template.match_uri != None:
                self.templates.append(template)
    return

  def match(self, source):
    """Add a matching template to the source"""
    _ = gettext.gettext
    found = False
    for template in self.templates:
      if (re.search(template.match_uri, source.uri) and 
          re.match(template.match_name, source.dist)):
        found = True
        source.template = template
        break
      elif (template.is_mirror(source.uri) and 
          re.match(template.match_name, source.dist)):
        found = True
        source.template = template
        break
    return found


# some simple tests
if __name__ == "__main__":
  apt_pkg.InitConfig()
  sources = SourcesList()

  for entry in sources:
    print entry.str()
    #print entry.uri

  mirror = is_mirror("http://archive.ubuntu.com/ubuntu/",
                     "http://de.archive.ubuntu.com/ubuntu/")
  print "is_mirror(): %s" % mirror
  
  print is_mirror("http://archive.ubuntu.com/ubuntu",
                  "http://de.archive.ubuntu.com/ubuntu/")
  print is_mirror("http://archive.ubuntu.com/ubuntu/",
                  "http://de.archive.ubuntu.com/ubuntu")


########NEW FILE########
__FILENAME__ = acquire
import apt
import apt_pkg
import os
import sys
import tempfile

def get_file(fetcher, uri, destFile):
	# get the file
	af = apt_pkg.GetPkgAcqFile(fetcher,
                           uri=uri,
                           descr="sample descr", destFile=destFile)
	res = fetcher.Run()
	if res != fetcher.ResultContinue:
		return False
	return True

apt_pkg.init()

#apt_pkg.Config.Set("Debug::pkgDPkgPM","1");
#apt_pkg.Config.Set("Debug::pkgPackageManager","1");
#apt_pkg.Config.Set("Debug::pkgDPkgProgressReporting","1");

cache = apt_pkg.GetCache()
depcache = apt_pkg.GetDepCache(cache)

recs = apt_pkg.GetPkgRecords(cache)
list = apt_pkg.GetPkgSourceList()
list.ReadMainList()

# show the amount fetch needed for a dist-upgrade 
depcache.Upgrade(True)
progress = apt.progress.TextFetchProgress()
fetcher = apt_pkg.GetAcquire(progress)
pm = apt_pkg.GetPackageManager(depcache)
pm.GetArchives(fetcher,list,recs)
print "%s (%s)" % (apt_pkg.SizeToStr(fetcher.FetchNeeded), fetcher.FetchNeeded)
actiongroup = apt_pkg.GetPkgActionGroup(depcache)
for pkg in cache.Packages:
    depcache.MarkKeep(pkg)

try:
    os.mkdir("/tmp/pyapt-test")
    os.mkdir("/tmp/pyapt-test/partial")
except OSError:
    pass
apt_pkg.Config.Set("Dir::Cache::archives","/tmp/pyapt-test")

pkg = cache["3ddesktop"]
depcache.MarkInstall(pkg)

progress = apt.progress.TextFetchProgress()
fetcher = apt_pkg.GetAcquire(progress)
#fetcher = apt_pkg.GetAcquire()
pm = apt_pkg.GetPackageManager(depcache)

print pm
print fetcher

get_file(fetcher, "ftp://ftp.debian.org/debian/dists/README", "/tmp/lala")

pm.GetArchives(fetcher,list,recs)

for item in fetcher.Items:
    print item
    if item.Status == item.StatError:
        print "Some error ocured: '%s'" % item.ErrorText
    if item.Complete == False:
        print "No error, still nothing downloaded (%s)" % item.ErrorText
    print
                                                         

res = fetcher.Run()
print "fetcher.Run() returned: %s" % res

print "now runing pm.DoInstall()"
res = pm.DoInstall(1)
print "pm.DoInstall() returned: %s"% res




########NEW FILE########
__FILENAME__ = action
#!/usr/bin/python
# example how to deal with the depcache

import apt_pkg
import sys
import copy
from apt.progress import OpTextProgress
from progress import TextFetchProgress

# init
apt_pkg.init()

progress = OpTextProgress()
cache = apt_pkg.GetCache(progress)
print "Available packages: %s " % cache.PackageCount

print "Fetching"
progress = TextFetchProgress()
cache.Update(progress)

print "Exiting"
sys.exit(0)










iter = cache["base-config"]
print "example package iter: %s" % iter

# get depcache
print "\n\n depcache"
depcache = apt_pkg.GetDepCache(cache, progress)
depcache.ReadPinFile()
print "got a depcache: %s " % depcache
print "Marked for install: %s " % depcache.InstCount

print "\n\n Reinit"
depcache.Init(progress)

#sys.exit()


# get a canidate version
ver= depcache.GetCandidateVer(iter)
print "Candidate version: %s " % ver

print "\n\nQuerry interface"
print "%s.IsUpgradable(): %s" % (iter.Name, depcache.IsUpgradable(iter))

print "\nMarking interface"
print "Marking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install count: %s " % depcache.InstCount
print "%s.MarkedInstall(): %s" % (iter.Name, depcache.MarkedInstall(iter))
print "%s.MarkedUpgrade(): %s" % (iter.Name, depcache.MarkedUpgrade(iter))
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))

print "Marking %s for delete" % iter.Name
depcache.MarkDelete(iter)
print "DelCount: %s " % depcache.DelCount
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))


iter = cache["3dchess"]
print "\nMarking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install count: %s " % depcache.InstCount
print "%s.MarkedInstall(): %s" % (iter.Name, depcache.MarkedInstall(iter))
print "%s.MarkedUpgrade(): %s" % (iter.Name, depcache.MarkedUpgrade(iter))
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))

print "Marking %s for keep" % iter.Name
depcache.MarkKeep(iter)
print "Install: %s " % depcache.InstCount

iter = cache["3dwm-server"]
print "\nMarking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install: %s " % depcache.InstCount
print "Broken count: %s" % depcache.BrokenCount
print "FixBroken() "
depcache.FixBroken()
print "Broken count: %s" % depcache.BrokenCount

print "\nPerforming Upgrade"
depcache.Upgrade()
print "Keep: %s " % depcache.KeepCount
print "Install: %s " % depcache.InstCount
print "Delete: %s " % depcache.DelCount
print "UsrSize: %s " % apt_pkg.SizeToStr(depcache.UsrSize)
print "DebSize: %s " % apt_pkg.SizeToStr(depcache.DebSize)

for pkg in cache.Packages:
    if pkg.CurrentVer != None and not depcache.MarkedInstall(pkg) and depcache.IsUpgradable(pkg):
        print "Upgrade didn't upgrade (kept): %s" % pkg.Name


print "\nPerforming DistUpgrade"
depcache.Upgrade(True)
print "Keep: %s " % depcache.KeepCount
print "Install: %s " % depcache.InstCount
print "Delete: %s " % depcache.DelCount
print "UsrSize: %s " % apt_pkg.SizeToStr(depcache.UsrSize)
print "DebSize: %s " % apt_pkg.SizeToStr(depcache.DebSize)

# overview about what would happen
for pkg in cache.Packages:
    if depcache.MarkedInstall(pkg):
        if pkg.CurrentVer != None:
            print "Marked upgrade: %s " % pkg.Name
        else:
            print "Marked install: %s" % pkg.Name
    elif depcache.MarkedDelete(pkg):
        print "Marked delete: %s" % pkg.Name
    elif depcache.MarkedKeep(pkg):
        print "Marked keep: %s" % pkg.Name

########NEW FILE########
__FILENAME__ = all_deps
#!/usr/bin/env python

import sys
import apt


def dependencies(cache, pkg, deps, key="Depends"):
    #print "pkg: %s (%s)" % (pkg.name, deps)
    candver = cache._depcache.GetCandidateVer(pkg._pkg)
    if candver == None:
        return deps
    dependslist = candver.DependsList
    if dependslist.has_key(key):
        for depVerList in dependslist[key]:
            for dep in depVerList:
                if cache.has_key(dep.TargetPkg.Name):
                    if pkg.name != dep.TargetPkg.Name and not dep.TargetPkg.Name in deps:
                        deps.add(dep.TargetPkg.Name)
                        dependencies(cache, cache[dep.TargetPkg.Name], deps, key)
    return deps


pkgname = sys.argv[1]
c = apt.Cache()
pkg = c[pkgname]

deps = set()

deps = dependencies(c,pkg, deps, "Depends")
print " ".join(deps)

preDeps = set()
preDeps = dependencies(c,pkg, preDeps, "PreDepends")
print " ".join(preDeps)

########NEW FILE########
__FILENAME__ = build-deps
#!/usr/bin/python
# this is a example how to access the build dependencies of a package

import apt_pkg
import sys
import sets    # only needed for python2.3, python2.4 supports this naively 

def get_source_pkg(pkg, records, depcache):
	""" get the source package name of a given package """
	version = depcache.GetCandidateVer(pkg)
	if not version:
		return None
	file, index = version.FileList.pop(0)
	records.Lookup((file, index))
	if records.SourcePkg != "":
		srcpkg = records.SourcePkg
	else:
		srcpkg = pkg.Name
	return srcpkg

# main
apt_pkg.init()
cache = apt_pkg.GetCache()
depcache = apt_pkg.GetDepCache(cache)
depcache.Init()
records = apt_pkg.GetPkgRecords(cache)
srcrecords = apt_pkg.GetPkgSrcRecords()

# base package that we use for build-depends calculation
if len(sys.argv) < 2:
	print "need a package name as argument"
	sys.exit(1)
try:
	base = cache[sys.argv[1]]
except KeyError:
	print "No package %s found" % sys.argv[1]
	sys.exit(1)
all_build_depends = sets.Set()

# get the build depdends for the package itself
srcpkg_name = get_source_pkg(base, records, depcache)
print "srcpkg_name: %s " % srcpkg_name
if not srcpkg_name:
	print "Can't find source package for '%s'" % pkg.Name
srcrec = srcrecords.Lookup(srcpkg_name)
if srcrec:
	print "Files:"
	print srcrecords.Files
	bd = srcrecords.BuildDepends
	print "build-depends of the package: %s " % bd
        for b in bd:
        	all_build_depends.add(b[0])

# calculate the build depends for all dependencies
depends = depcache.GetCandidateVer(base).DependsList
for dep in depends["Depends"]: # FIXME: do we need to consider PreDepends?
	pkg = dep[0].TargetPkg
	srcpkg_name = get_source_pkg(pkg, records, depcache)
	if not srcpkg_name:
		print "Can't find source package for '%s'" % pkg.Name
		continue
	srcrec = srcrecords.Lookup(srcpkg_name)
	if srcrec:
		#print srcrecords.Package
		#print srcrecords.Binaries
		bd = srcrecords.BuildDepends
		#print "%s: %s " % (srcpkg_name, bd)
		for b in bd:
			all_build_depends.add(b[0])
			

print "\n".join(all_build_depends)

########NEW FILE########
__FILENAME__ = cdrom
#!/usr/bin/python
# example how to deal with the depcache

import apt_pkg
import sys, os
import copy

from progress import CdromProgress


# init
apt_pkg.init()

cdrom = apt_pkg.GetCdrom()
print cdrom

progress = CdromProgress()

(res,ident) = cdrom.Ident(progress)
print "ident result is: %s (%s) " % (res, ident)

apt_pkg.Config.Set("APT::CDROM::Rename", "True")
cdrom.Add(progress)



print "Exiting"
sys.exit(0)





########NEW FILE########
__FILENAME__ = checkstate
#!/usr/bin/python
#
#
# this example is not usefull to find out about updated, upgradable packages
# use the depcache.py example for it (because a pkgPolicy is not used here)
#

import apt_pkg
apt_pkg.init()

cache = apt_pkg.GetCache()
packages = cache.Packages

uninstalled, updated, upgradable = {}, {}, {}

for package in packages:
	versions = package.VersionList
	if not versions:
		continue
	version = versions[0]
	for other_version in versions:
		if apt_pkg.VersionCompare(version.VerStr, other_version.VerStr)<0:
			version = other_version
	if package.CurrentVer:
		current = package.CurrentVer
		if apt_pkg.VersionCompare(current.VerStr, version.VerStr)<0:
			upgradable[package.Name] = version
			break
		else:
			updated[package.Name] = current
	else:
		uninstalled[package.Name] = version


for l in (uninstalled, updated, upgradable):
	print l.items()[0]

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# Example demonstrating how to use the configuration/commandline system
# for configuration.
# Some valid command lines..
#   config.py -h --help            ; Turn on help
#   config.py -no-h --no-help --help=no  ; Turn off help
#   config.py -qqq -q=3            ; verbosity to 3
#   config.py -c /etc/apt/apt.conf ; include that config file]
#   config.py -o help=true         ; Turn on help by giving a config file string
#   config.py -no-h -- -help       ; Turn off help, specify the file '-help'
# -c and -o are standard APT-program options.

# This shows how to use the system for configuration and option control.
# The other varient is for ISC object config files. See configisc.py.
import apt_pkg,sys,posixpath;

# Create a new empty Configuration object - there is also the system global
# configuration object apt_pkg.Config which is used interally by apt-pkg
# routines to control unusual situations. I recommend using the sytem global
# whenever possible..
Cnf = apt_pkg.newConfiguration();

print "Command line is",sys.argv

# Load the default configuration file, InitConfig() does this better..
Cnf.Set("config-file","/etc/apt/apt.conf");  # or Cnf["config-file"] = "..";
if posixpath.exists(Cnf.FindFile("config-file")):
   apt_pkg.ReadConfigFile(Cnf,"/etc/apt/apt.conf");

# Merge the command line arguments into the configuration space
Arguments = [('h',"help","help"),
             ('v',"version","version"),
             ('q',"quiet","quiet","IntLevel"),
             ('c',"config-file","","ConfigFile"),
	     ('o',"option","","ArbItem")]
print "FileNames",apt_pkg.ParseCommandLine(Cnf,Arguments,sys.argv);

print "Quiet level selected is",Cnf.FindI("quiet",0);

# Do some stuff with it
if Cnf.FindB("version",0) == 1:
   print "Version selected - 1.1";

if Cnf.FindB("help",0) == 1:
   print "python-apt",apt_pkg.Version,"compiled on",apt_pkg.Date,apt_pkg.Time;
   print "Hi, I am the help text for this program";
   sys.exit(0);

print "No help for you, try -h";

# Print the configuration space
print "The Configuration space looks like:";
for I in Cnf.keys():
   print "%s \"%s\";"%(I,Cnf[I]);

########NEW FILE########
__FILENAME__ = configisc
#!/usr/bin/python
# Example demonstrating how to use the configuration/commandline system
# for object setup.

# This parses the given config file in 'ISC' style where the sections
# represent object instances and shows how to iterate over the sections.
# Pass it the sample apt-ftparchive configuration,
# doc/examples/ftp-archive.conf
# or a bind8 config file..

import apt_pkg,sys,posixpath;

ConfigFile = apt_pkg.ParseCommandLine(apt_pkg.Config,[],sys.argv);

if len(ConfigFile) != 1:
   print "Must have exactly 1 file name";
   sys.exit(0);

Cnf = apt_pkg.newConfiguration();
apt_pkg.ReadConfigFileISC(Cnf,ConfigFile[0]);

# Print the configuration space
#print "The Configuration space looks like:";
#for I in Cnf.keys():
#   print "%s \"%s\";"%(I,Cnf[I]);

# bind8 config file..
if Cnf.has_key("Zone"):
   print "Zones: ",Cnf.SubTree("zone").List();
   for I in Cnf.List("zone"):
      SubCnf = Cnf.SubTree(I);
      if SubCnf.Find("type") == "slave":
         print "Masters for %s: %s"%(SubCnf.MyTag(),SubCnf.ValueList("masters"));
else:
   print "Tree definitions:";
   for I in Cnf.List("tree"):
      SubCnf = Cnf.SubTree(I);
      # This could use Find which would eliminate the possibility of exceptions.
      print "Subtree %s with sections '%s' and architectures '%s'"%(SubCnf.MyTag(),SubCnf["Sections"],SubCnf["Architectures"]);

########NEW FILE########
__FILENAME__ = deb_inspect
#!/usr/bin/env python
# some example for apt_inst

import apt_pkg
import apt_inst
import sys
import os.path

def Callback(What,Name,Link,Mode,UID,GID,Size,MTime,Major,Minor):
    """ callback for debExtract """
    
    print "%s '%s','%s',%u,%u,%u,%u,%u,%u,%u"\
          % (What,Name,Link,Mode,UID,GID,Size, MTime, Major, Minor);


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "need filename argumnet"
        sys.exit(1)
    file = sys.argv[1]

    print "Working on: %s" % file
    print "Displaying data.tar.gz:"
    apt_inst.debExtract(open(file), Callback, "data.tar.gz")

    print "Now extracting the control file:"
    control = apt_inst.debExtractControl(open(file))
    sections = apt_pkg.ParseSection(control)

    print "Maintainer is: "
    print sections["Maintainer"]

    print
    print "DependsOn: "
    depends = sections["Depends"]
    print apt_pkg.ParseDepends(depends)


    print "extracting archive"
    dir = "/tmp/deb"
    os.mkdir(dir)
    apt_inst.debExtractArchive(open(file),dir)
    def visit(arg, dirname, names):
        print "%s/" % dirname
        for file in names:
            print "\t%s" % file
    os.path.walk(dir, visit, None)

########NEW FILE########
__FILENAME__ = depcache
#!/usr/bin/python
# example how to deal with the depcache

import apt
import apt_pkg
import sys
import copy
from progress import TextProgress


# init
apt_pkg.init()

progress = TextProgress()
cache = apt_pkg.GetCache(progress)
print "Available packages: %s " % cache.PackageCount

iter = cache["base-config"]
print "example package iter: %s" % iter

# get depcache
print "\n\n depcache"
depcache = apt_pkg.GetDepCache(cache)
depcache.ReadPinFile()
# init is needed after the creation/pin file reading
depcache.Init(progress)
print "got a depcache: %s " % depcache
print "Marked for install: %s " % depcache.InstCount

print "\n\n Reinit"
depcache.Init(progress)

#sys.exit()


# get a canidate version
ver= depcache.GetCandidateVer(iter)
print "Candidate version: %s " % ver

print "\n\nQuerry interface"
print "%s.IsUpgradable(): %s" % (iter.Name, depcache.IsUpgradable(iter))

print "\nMarking interface"
print "Marking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install count: %s " % depcache.InstCount
print "%s.MarkedInstall(): %s" % (iter.Name, depcache.MarkedInstall(iter))
print "%s.MarkedUpgrade(): %s" % (iter.Name, depcache.MarkedUpgrade(iter))
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))

print "Marking %s for delete" % iter.Name
depcache.MarkDelete(iter)
print "DelCount: %s " % depcache.DelCount
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))


iter = cache["3dchess"]
print "\nMarking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install count: %s " % depcache.InstCount
print "%s.MarkedInstall(): %s" % (iter.Name, depcache.MarkedInstall(iter))
print "%s.MarkedUpgrade(): %s" % (iter.Name, depcache.MarkedUpgrade(iter))
print "%s.MarkedDelete(): %s" % (iter.Name, depcache.MarkedDelete(iter))

print "Marking %s for keep" % iter.Name
depcache.MarkKeep(iter)
print "Install: %s " % depcache.InstCount

iter = cache["synaptic"]
print "\nMarking '%s' for install" % iter.Name
depcache.MarkInstall(iter)
print "Install: %s " % depcache.InstCount
print "Broken count: %s" % depcache.BrokenCount
print "FixBroken() "
depcache.FixBroken()
print "Broken count: %s" % depcache.BrokenCount

print "\nPerforming Upgrade"
depcache.Upgrade()
print "Keep: %s " % depcache.KeepCount
print "Install: %s " % depcache.InstCount
print "Delete: %s " % depcache.DelCount
print "UsrSize: %s " % apt_pkg.SizeToStr(depcache.UsrSize)
print "DebSize: %s " % apt_pkg.SizeToStr(depcache.DebSize)

for pkg in cache.Packages:
    if pkg.CurrentVer != None and not depcache.MarkedInstall(pkg) and depcache.IsUpgradable(pkg):
        print "Upgrade didn't upgrade (kept): %s" % pkg.Name


print "\nPerforming DistUpgrade"
depcache.Upgrade(True)
print "Keep: %s " % depcache.KeepCount
print "Install: %s " % depcache.InstCount
print "Delete: %s " % depcache.DelCount
print "UsrSize: %s " % apt_pkg.SizeToStr(depcache.UsrSize)
print "DebSize: %s " % apt_pkg.SizeToStr(depcache.DebSize)

# overview about what would happen
for pkg in cache.Packages:
    if depcache.MarkedInstall(pkg):
        if pkg.CurrentVer != None:
            print "Marked upgrade: %s " % pkg.Name
        else:
            print "Marked install: %s" % pkg.Name
    elif depcache.MarkedDelete(pkg):
        print "Marked delete: %s" % pkg.Name
    elif depcache.MarkedKeep(pkg):
        print "Marked keep: %s" % pkg.Name

########NEW FILE########
__FILENAME__ = dependant-pkgs
#!/usr/bin/env python

import apt
import sys

pkgs = set()
cache = apt.Cache()
for pkg in cache:
	candver = cache._depcache.GetCandidateVer(pkg._pkg)
	if candver == None:
		continue
	dependslist = candver.DependsList
	for dep in dependslist.keys():
		# get the list of each dependency object
		for depVerList in dependslist[dep]:
			for z in depVerList:
				# get all TargetVersions of
				# the dependency object
				for tpkg in z.AllTargets():
					if sys.argv[1] == tpkg.ParentPkg.Name:
						pkgs.add(pkg.name)

main = set()
universe = set()
for pkg in pkgs:
	if "universe" in cache[pkg].section:
		universe.add(cache[pkg].sourcePackageName)
	else:
		main.add(cache[pkg].sourcePackageName)

print "main:"		
print "\n".join(main)
print

print "universe:"		
print "\n".join(universe)

########NEW FILE########
__FILENAME__ = desc

import apt_pkg

apt_pkg.init()

apt_pkg.Config.Set("APT::Acquire::Translation","de")

cache = apt_pkg.GetCache()
depcache = apt_pkg.GetDepCache(cache)

pkg = cache["gcc"]
cand = depcache.GetCandidateVer(pkg)
print cand

desc = cand.TranslatedDescription
print desc
print desc.FileList
(f,index) = desc.FileList.pop(0)

records = apt_pkg.GetPkgRecords(cache)
records.Lookup((f,index))
desc = records.LongDesc
print len(desc)
print desc


########NEW FILE########
__FILENAME__ = gui-inst
#!/usr/bin/python
# example how to install in a custom terminal widget
# see also gnome bug: #169201

import apt
import apt_pkg
import sys, os, fcntl
import copy
import string
import fcntl

import pygtk
pygtk.require('2.0')
import gtk
import vte
import time
import posix

from apt.progress import OpProgress, FetchProgress, InstallProgress

class GuiFetchProgress(gtk.Window, FetchProgress):
    def __init__(self):
	gtk.Window.__init__(self)
	self.vbox = gtk.VBox()
	self.vbox.show()
	self.add(self.vbox)
	self.progress = gtk.ProgressBar()
	self.progress.show()
	self.label = gtk.Label()
	self.label.show()
	self.vbox.pack_start(self.progress)
	self.vbox.pack_start(self.label)
	self.resize(300,100)
    def start(self):
        print "start"
	self.progress.set_fraction(0.0)
        self.show()
    def stop(self):
	self.hide()
    def pulse(self):
        FetchProgress.pulse(self)
        self.label.set_text("Speed: %s/s" % apt_pkg.SizeToStr(self.currentCPS))
	#self.progressbar.set_fraction(self.currentBytes/self.totalBytes)
	while gtk.events_pending():
		gtk.main_iteration()
        return True

class TermInstallProgress(InstallProgress, gtk.Window):
    def __init__(self):
	gtk.Window.__init__(self)
        InstallProgress.__init__(self)
	self.show()
        box = gtk.VBox()
        box.show()
        self.add(box)
	self.term = vte.Terminal()
	self.term.show()
        # check for the child
        self.reaper = vte.reaper_get()
        self.reaper.connect("child-exited",self.child_exited)
        self.finished = False
	box.pack_start(self.term)
        self.progressbar = gtk.ProgressBar()
        self.progressbar.show()
        box.pack_start(self.progressbar)
    def child_exited(self,term, pid, status):
        print "child_exited: %s %s %s %s" % (self,term,pid,status)
        self.apt_status = posix.WEXITSTATUS(status)
        self.finished = True
    def startUpdate(self):
        print "start"
        self.show()
    def waitChild(self):
        while not self.finished:
            self.updateInterface()
            while gtk.events_pending():
                gtk.main_iteration()
            time.sleep(0.001)
        sys.stdin.readline()
        return self.apt_status
    def statusChange(self, pkg, percent, status):
        print "statusChange", pkg, percent
        self.progressbar.set_fraction(float(percent)/100.0)
        self.progressbar.set_text(string.strip(status))
    def fork(self):
        env = ["VTE_PTY_KEEP_FD=%s"%self.writefd]
        return self.term.forkpty(envv=env)

cache = apt.Cache()
print "Available packages: %s " % cache._cache.PackageCount


# update the cache
fprogress = GuiFetchProgress()
iprogress = TermInstallProgress()

# update the cache
#cache.Update(fprogress)
#cache = apt_pkg.GetCache(progress)
#depcache = apt_pkg.GetDepCache(cache)
#depcache.ReadPinFile()
#depcache.Init(progress)


# show the interface
while gtk.events_pending():
	gtk.main_iteration()
  

pkg = cache["3dchess"]
print "\n%s"%pkg.name

# install or remove, the importend thing is to keep us busy :)
if pkg.isInstalled:
	pkg.markDelete()
else:
	pkg.markInstall()
cache.commit(fprogress, iprogress)

print "Exiting"
sys.exit(0)




########NEW FILE########
__FILENAME__ = indexfile

import apt_pkg

apt_pkg.init()

sources = apt_pkg.GetPkgSourceList()
sources.ReadMainList()

cache = apt_pkg.GetCache()
depcache = apt_pkg.GetDepCache(cache)
pkg = cache["libimlib2"]
cand = depcache.GetCandidateVer(pkg)
for (f,i) in cand.FileList:
    index = sources.FindIndex(f)
    print index
    if index:
        print index.Size
        print index.IsTrusted
        print index.Exists
        print index.HasPackages
        print index.ArchiveURI("some/path")

########NEW FILE########
__FILENAME__ = inst
#!/usr/bin/python
# example how to deal with the depcache

import apt
import sys, os
import copy
import time

from apt.progress import InstallProgress

class TextInstallProgress(InstallProgress):
	def __init__(self):
		apt.progress.InstallProgress.__init__(self)
		self.last = 0.0
	def updateInterface(self):
		InstallProgress.updateInterface(self)
		if self.last >= self.percent:
			return
		sys.stdout.write("\r[%s] %s\n" %(self.percent, self.status))
		sys.stdout.flush()
		self.last = self.percent
	def conffile(self,current,new):
		print "conffile prompt: %s %s" % (current,new)
	def error(self, errorstr):
		print "got dpkg error: '%s'" % errorstr

cache = apt.Cache(apt.progress.OpTextProgress())

fprogress = apt.progress.TextFetchProgress()
iprogress = TextInstallProgress()

pkg = cache["3dchess"]

# install or remove, the importend thing is to keep us busy :)
if pkg.isInstalled:
	print "Going to delete %s" % pkg.name
	pkg.markDelete()
else:
	print "Going to install %s" % pkg.name
	pkg.markInstall()
res = cache.commit(fprogress, iprogress)
print res

sys.exit(0)





########NEW FILE########
__FILENAME__ = metaindex

import apt_pkg

apt_pkg.init()

sources = apt_pkg.GetPkgSourceList()
sources.ReadMainList()


for metaindex in sources.List:
    print metaindex
    print "URI: ",metaindex.URI
    print "Dist: ",metaindex.Dist
    print "IndexFiles: ","\n".join([str(i) for i in metaindex.IndexFiles])
    print

########NEW FILE########
__FILENAME__ = print_uris
#!/usr/bin/env python
#
# a example that prints the URIs of all upgradable packages
#

import apt
import apt_pkg


cache = apt.Cache()
upgradable = filter(lambda p: p.isUpgradable, cache)


for pkg in upgradable:
	pkg._lookupRecord(True)
	path = apt_pkg.ParseSection(pkg._records.Record)["Filename"]
	cand = pkg._depcache.GetCandidateVer(pkg._pkg)
	for (packagefile,i) in cand.FileList:
		indexfile = cache._list.FindIndex(packagefile)
		if indexfile:
			uri = indexfile.ArchiveURI(path)
			print uri

########NEW FILE########
__FILENAME__ = progress
import apt
from apt import SizeToStr
import sys
import time
import string

class TextProgress(apt.OpProgress):
    def __init__(self):
        self.last=0.0

    def update(self, percent):
        if (self.last + 1.0) <= percent:
            sys.stdout.write("\rProgress: %i.2          " % (percent))
            self.last = percent
        if percent >= 100:
            self.last = 0.0

    def done(self):
        self.last = 0.0
        print "\rDone                      "


class TextFetchProgress(apt.FetchProgress):
    def __init__(self):
        pass
    
    def start(self):
        pass
    
    def stop(self):
        pass
    
    def updateStatus(self, uri, descr, shortDescr, status):
        print "UpdateStatus: '%s' '%s' '%s' '%i'" % (uri,descr,shortDescr, status)
    def pulse(self):
        print "Pulse: CPS: %s/s; Bytes: %s/%s; Item: %s/%s" % (SizeToStr(self.currentCPS), SizeToStr(self.currentBytes), SizeToStr(self.totalBytes), self.currentItems, self.totalItems)
        return True

    def mediaChange(self, medium, drive):
	print "Please insert medium %s in drive %s" % (medium, drive)
	sys.stdin.readline()
        #return False


class TextInstallProgress(apt.InstallProgress):
    def __init__(self):
        apt.InstallProgress.__init__(self)
        pass
    def startUpdate(self):
        print "StartUpdate"
    def finishUpdate(self):
        print "FinishUpdate"
    def statusChange(self, pkg, percent, status):
        print "[%s] %s: %s" % (percent, pkg, status)
    def updateInterface(self):
        apt.InstallProgress.updateInterface(self)
        # usefull to e.g. redraw a GUI
        time.sleep(0.1)


class TextCdromProgress(apt.CdromProgress):
    def __init__(self):
        pass
    # update is called regularly so that the gui can be redrawn
    def update(self, text, step):
        # check if we actually have some text to display
        if text != "":
            print "Update: %s %s" % (string.strip(text), step)
    def askCdromName(self):
        print "Please enter cd-name: ",
        cd_name = sys.stdin.readline()
        return (True, string.strip(cd_name))
    def changeCdrom(self):
        print "Please insert cdrom and press <ENTER>"
        answer =  sys.stdin.readline()
        return True


if __name__ == "__main__":
    c = apt.Cache()
    pkg = c["3dchess"]
    if pkg.isInstalled:
        pkg.markDelete()
    else:
        pkg.markInstall()

    res = c.commit(TextFetchProgress(), TextInstallProgress())

    print res

########NEW FILE########
__FILENAME__ = recommends
#!/usr/bin/python

import apt_pkg
apt_pkg.init()

cache = apt_pkg.GetCache()

class Wanted:

	def __init__(self, name):
		self.name = name
		self.recommended = []
		self.suggested = []

wanted = {}

for package in cache.Packages:
	current = package.CurrentVer
	if not current:
		continue
	depends = current.DependsList
	for (key, attr) in (('Suggests', 'suggested'), 
	                    ('Recommends', 'recommended')):
		list = depends.get(key, [])
		for dependency in list:
			name = dependency[0].TargetPkg.Name
			dep = cache[name]
			if dep.CurrentVer:
				continue
			getattr(wanted.setdefault(name, Wanted(name)),
			        attr).append(package.Name)

ks = wanted.keys()
ks.sort()

for want in ks:
	print want, wanted[want].recommended, wanted[want].suggested





########NEW FILE########
__FILENAME__ = records
#!/usr/bin/env python

import apt

cache = apt.Cache()

for pkg in cache:
   if not pkg.candidateRecord:
      continue
   if pkg.candidateRecord.has_key("Task"):
      print "Pkg %s is part of '%s'" % (pkg.name, pkg.candidateRecord["Task"].split())
      #print pkg.candidateRecord

########NEW FILE########
__FILENAME__ = sources
#!/usr/bin/python

import apt_pkg

apt_pkg.init()

#cache = apt_pkg.GetCache()
#sources = apt_pkg.GetPkgSrcRecords(cache)

sources = apt_pkg.GetPkgSrcRecords()
sources.Restart()
while sources.Lookup('hello'):
	print sources.Package, sources.Version, sources.Maintainer, sources.Section, `sources.Binaries`
	print sources.Files
	print sources.Index.ArchiveURI(sources.Files[0][2])

########NEW FILE########
__FILENAME__ = tagfile
#!/usr/bin/env python
import apt_pkg

Parse = apt_pkg.ParseTagFile(open("/var/lib/dpkg/status","r"));

while Parse.Step() == 1:
   print Parse.Section.get("Package");
   print apt_pkg.ParseDepends(Parse.Section.get("Depends",""));

########NEW FILE########
__FILENAME__ = update
import apt
import apt_pkg
import os.path

if __name__ == "__main__":
    apt_pkg.Config.Set("APT::Update::Pre-Invoke::",
                       "touch /tmp/update-about-to-run")
    apt_pkg.Config.Set("APT::Update::Post-Invoke::",
                       "touch /tmp/update-was-run")
    c = apt.Cache()
    res = c.update(apt.progress.TextFetchProgress())
    print "res: ",res
    assert(os.path.exists("/tmp/update-about-to-run"))

########NEW FILE########
__FILENAME__ = versiontest
#!/usr/bin/python

# This is a simple clone of tests/versiontest.cc
import apt_pkg,sys,re,string;
apt_pkg.InitConfig();
apt_pkg.InitSystem();

TestFile = apt_pkg.ParseCommandLine(apt_pkg.Config,[],sys.argv);
if len(TestFile) != 1:
   print "Must have exactly 1 file name";
   sys.exit(0);

# Go over the file.. 
List = open(TestFile[0],"r");
CurLine = 0;
while(1):
   Line = List.readline();
   CurLine = CurLine + 1;
   if Line == "":
      break;
   Line = string.strip(Line);
   if len(Line) == 0 or Line[0] == '#':
      continue;
   
   Split = re.split("[ \n]",Line);

   # Check forward   
   if apt_pkg.VersionCompare(Split[0],Split[1]) != int(Split[2]):
     print "Comparision failed on line %u. '%s' ? '%s' %i != %i"%(CurLine,
             Split[0],Split[1],apt_pkg.VersionCompare(Split[0],Split[1]),
             int(Split[2]));
   # Check reverse
   if apt_pkg.VersionCompare(Split[1],Split[0]) != -1*int(Split[2]):
     print "Comparision failed on line %u. '%s' ? '%s' %i != %i"%(CurLine,
             Split[1],Split[0],apt_pkg.VersionCompare(Split[1],Split[0]),
             -1*int(Split[2]));

########NEW FILE########
__FILENAME__ = apt-test
import warnings
warnings.filterwarnings("ignore", "apt API not stable yet", FutureWarning)
import apt


if __name__ == "__main__":
    progress = apt.progress.OpTextProgress()
    cache = apt.Cache(progress)
    print cache
    for pkg in cache:
        if pkg.isUpgradable:
            pkg.markInstall()
    for pkg in cache.getChanges():
        #print pkg.Name()
        pass
    print "Broken: %s " % cache._depcache.BrokenCount
    print "InstCount: %s " % cache._depcache.InstCount

    # get a new cache
    cache = apt.Cache(progress)
    for name in cache.keys():
        import random
        if random.randint(0,1) == 1:
            cache[name].markDelete()
    print "Broken: %s " % cache._depcache.BrokenCount
    print "DelCount: %s " % cache._depcache.DelCount

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python2.4
#
# Test for the pkgCache code
# 

import apt_pkg
import sys

def main():
	apt_pkg.init()
	cache = apt_pkg.GetCache()
	depcache = apt_pkg.GetDepCache(cache)
	depcache.Init()
	i=0
	all=cache.PackageCount
	print "Running Cache test on all packages:"
	# first, get all pkgs
	for pkg in cache.Packages:
		i += 1
		x = pkg.Name
		# then get each version
		for ver in pkg.VersionList:
			# get some version information
			a = ver.FileList
			b = ver.VerStr
			c = ver.Arch
			d = ver.DependsListStr
			dl = ver.DependsList
			# get all dependencies (a dict of string->list, 
			# e.g. "depends:" -> [ver1,ver2,..]
			for dep in dl.keys():
				# get the list of each dependency object
				for depVerList in dl[dep]:
					for z in depVerList:
						# get all TargetVersions of
						# the dependency object
						for j in z.AllTargets():
							f = j.FileList
							g = ver.VerStr
							h = ver.Arch
							k = ver.DependsListStr
							j = ver.DependsList
							pass
				
		print "\r%i/%i=%.3f%%    " % (i,all,(float(i)/float(all)*100)),

if __name__ == "__main__":
	main()
	sys.exit(0)

########NEW FILE########
__FILENAME__ = depcache
#!/usr/bin/env python2.4
#
# Test for the DepCache code
# 

import apt_pkg
import sys

def main():
	apt_pkg.init()
	cache = apt_pkg.GetCache()
	depcache = apt_pkg.GetDepCache(cache)
	depcache.Init()
	i=0
	all=cache.PackageCount
	print "Running DepCache test on all packages"
	print "(trying to install each and then mark it keep again):"
	# first, get all pkgs
	for pkg in cache.Packages:
		i += 1
		x = pkg.Name
		# then get each version
		ver =depcache.GetCandidateVer(pkg)
		if ver != None:
			depcache.MarkInstall(pkg)
			if depcache.InstCount == 0:
				if depcache.IsUpgradable(pkg):
					print "Error marking %s for install" % x
			for p in cache.Packages:
				if depcache.MarkedInstall(p):
					depcache.MarkKeep(p)
			if depcache.InstCount != 0:
				print "Error undoing the selection for %s (InstCount: %s)" % (x,depcache.InstCount)
		print "\r%i/%i=%.3f%%    " % (i,all,(float(i)/float(all)*100)),

	print
	print "Trying Upgrade:"
	depcache.Upgrade()
	print "To install: %s " % depcache.InstCount
	print "To remove: %s " % depcache.DelCount
	print "Kept back: %s " % depcache.KeepCount

	print "Trying DistUpgrade:"
	depcache.Upgrade(True)
	print "To install: %s " % depcache.InstCount
	print "To remove: %s " % depcache.DelCount
	print "Kept back: %s " % depcache.KeepCount


if __name__ == "__main__":
	main()
	sys.exit(0)

########NEW FILE########
__FILENAME__ = lock
#!/usr/bin/env python2.4
#
# Test for the pkgCache code
# 

import apt_pkg
import sys, os


if __name__ == "__main__":
    lock = "/tmp/test.lck"
    
    apt_pkg.init()

    # system-lock
    apt_pkg.PkgSystemLock()

    pid = os.fork()
    if pid == 0:
        try:
            apt_pkg.PkgSystemLock()
        except SystemError, s:
            print "Can't get lock: (error text:\n%s)" % s
	sys.exit(0)

    apt_pkg.PkgSystemUnLock()

    # low-level lock
    fd = apt_pkg.GetLock(lock,True)
    print "Lockfile fd: %s" % fd

    # try to get lock without error flag
    pid = os.fork()
    if pid == 0:
        # child
        fd = apt_pkg.GetLock(lock,False)
        print "Lockfile fd (child): %s" % fd
	sys.exit(0)

    # try to get lock with error flag
    pid = os.fork()
    if pid == 0:
        # child
        fd = apt_pkg.GetLock(lock,True)
        print "Lockfile fd (child): %s" % fd
	sys.exit(0)
    

########NEW FILE########
__FILENAME__ = memleak
#!/usr/bin/python

import apt
import apt_pkg
import time
import gc
import sys


cache = apt.Cache()

# memleak
for i in range(100):
	cache.open(None)
	print cache["apt"].name
	time.sleep(1)
	gc.collect()
	f = open("%s" % i,"w")
	for obj in gc.get_objects():
		f.write("%s\n" % str(obj))
	f.close()

# memleak	
#for i in range(100):
#	cache = apt.Cache()
#	time.sleep(1)
#	cache = None
#	gc.collect()

# no memleak, but more or less the apt.Cache.open() code
for i in range(100):
	cache = apt_pkg.GetCache()
	depcache = apt_pkg.GetDepCache(cache)
	records = apt_pkg.GetPkgRecords(cache)
	list = apt_pkg.GetPkgSourceList()
	list.ReadMainList()
	dict = {}
	for pkg in cache.Packages:
            if len(pkg.VersionList) > 0:
		    dict[pkg.Name] = apt.Package(cache,depcache,
						 records, list, None, pkg)

	print cache["apt"]
	time.sleep(1)

	gc.collect()

########NEW FILE########
__FILENAME__ = pkgproblemresolver
#!/usr/bin/env python2.4
#
# Test for the DepCache code
# 

import apt_pkg
import sys

def main():
	apt_pkg.init()
	cache = apt_pkg.GetCache()
	depcache = apt_pkg.GetDepCache(cache)
	depcache.Init()
	i=0
	all=cache.PackageCount
	print "Running DepCache test on all packages"
	print "(trying to install each and then mark it keep again):"
	# first, get all pkgs
	for pkg in cache.Packages:
		i += 1
		x = pkg.Name
		# then get each version
		ver =depcache.GetCandidateVer(pkg)
		if ver != None:
			depcache.MarkInstall(pkg)
			if depcache.BrokenCount > 0:
				fixer = apt_pkg.GetPkgProblemResolver(depcache)
				fixer.Clear(pkg)
				fixer.Protect(pkg)
				# we first try to resolve the problem
				# with the package that should be installed
				# protected 
				try:
					fixer.Resolve(True)
				except SystemError:
					# the pkg seems to be broken, the
					# returns a exception
					fixer.Clear(pkg)
					fixer.Resolve(True)
					if not depcache.MarkedInstall(pkg):
						print "broken in archive: %s " % pkg.Name
				fixer = None
			if depcache.InstCount == 0:
				if depcache.IsUpgradable(pkg):
					print "Error marking %s for install" % x
			for p in cache.Packages:
				if depcache.MarkedInstall(p) or depcache.MarkedUpgrade(p):
					depcache.MarkKeep(p)
			if depcache.InstCount != 0:
				print "Error undoing the selection for %s" % x
		print "\r%i/%i=%.3f%%    " % (i,all,(float(i)/float(all)*100)),

	print
	print "Trying Upgrade:"
	depcache.Upgrade()
	print "To install: %s " % depcache.InstCount
	print "To remove: %s " % depcache.DelCount
	print "Kept back: %s " % depcache.KeepCount

	print "Trying DistUpgrade:"
	depcache.Upgrade(True)
	print "To install: %s " % depcache.InstCount
	print "To remove: %s " % depcache.DelCount
	print "Kept back: %s " % depcache.KeepCount


if __name__ == "__main__":
	main()
	sys.exit(0)

########NEW FILE########
__FILENAME__ = pkgrecords
#!/usr/bin/env python2.4
#
# Test for the PkgSrcRecords code
# it segfaults for python-apt < 0.5.37
# 

import apt_pkg
import sys

def main():
	apt_pkg.init()
	cache = apt_pkg.GetCache()
	depcache = apt_pkg.GetDepCache(cache)
	depcache.Init()
	i=0
	print "Running PkgRecords test on all packages:"
	for pkg in cache.Packages:
		i += 1
		records = apt_pkg.GetPkgRecords(cache)
		if len(pkg.VersionList) == 0:
			#print "no available version, cruft"
			continue
		version = depcache.GetCandidateVer(pkg)
		if not version:
			continue
		file, index = version.FileList.pop(0)
		if records.Lookup((file,index)):
			#print records.FileName
			x = records.FileName
			y = records.LongDesc
			pass
		print "\r%i/%i=%.3f%%    " % (i,cache.PackageCount, (float(i)/float(cache.PackageCount)*100)),

if __name__ == "__main__":
	main()
	sys.exit(0)

########NEW FILE########
__FILENAME__ = pkgsrcrecords
#!/usr/bin/env python2.4
#
# Test for the PkgSrcRecords code
# it segfaults for python-apt < 0.5.37
# 

import apt_pkg
import sys

def main():
	apt_pkg.init()
	cache = apt_pkg.GetCache()
	i=0
	print "Running PkgSrcRecords test on all packages:"
	for x in cache.Packages:
		i += 1
		src = apt_pkg.GetPkgSrcRecords()
		if src.Lookup(x.Name):
			#print src.Package
			pass
		print "\r%i/%i=%.3f%%    " % (i,cache.PackageCount, (float(i)/float(cache.PackageCount)*100)),

if __name__ == "__main__":
	main()
	sys.exit(0)

########NEW FILE########
__FILENAME__ = refcount
#!/usr/bin/python-dbg

from pprint import pprint,pformat
import apt
import sys
import gc
import difflib

# get initial cache
print sys.gettotalrefcount()
progress= apt.progress.OpTextProgress()
c = apt.Cache(progress)
print "refcount after first cache instance: ", sys.gettotalrefcount()

# test open()
c.open(progress)
print "refcount after cache open: ", sys.gettotalrefcount()
#pprint(sys.getobjects(10))

c.open(apt.progress.OpProgress())
print "refcount after seconf cache open: ", sys.gettotalrefcount()
#pprint(sys.getobjects(10))

# FIXME: find a way to get a efficient diff
#before = gc.get_objects()
#c.open(apt.progress.OpProgress())
#after = gc.get_objects()


# test update()
print "refcount before cache.update(): ", sys.gettotalrefcount()
c.update()
gc.collect()
print "refcount after cache.update(): ", sys.gettotalrefcount()
c.update()
gc.collect()
print "refcount after second cache.update(): ", sys.gettotalrefcount()
#pprint(sys.getobjects(20))


# test install()
c.open(apt.progress.OpProgress())
gc.collect()
print "refcount before cache['hello'].markInstall(): ", sys.gettotalrefcount()
c["hello"].markInstall()
c.commit(apt.progress.FetchProgress(), apt.progress.InstallProgress())
gc.collect()
print "refcount after: ", sys.gettotalrefcount()
c.open(apt.progress.OpProgress())
c["hello"].markDelete()
c.commit(apt.progress.FetchProgress(), apt.progress.InstallProgress())
gc.collect()
print "refcount after: ", sys.gettotalrefcount()
pprint(sys.getobjects(10))

########NEW FILE########
__FILENAME__ = test_aptsources
#!/usr/bin/env python

import unittest
import apt_pkg
import os
import copy

import sys
sys.path.insert(0, "../")
import aptsources
import aptsources.sourceslist
import aptsources.distro

class TestAptSources(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        apt_pkg.init()
        apt_pkg.Config.Set("Dir::Etc", os.getcwd())
        apt_pkg.Config.Set("Dir::Etc::sourceparts","/xxx")

    def testIsMirror(self):
        self.assertTrue(aptsources.sourceslist.is_mirror("http://archive.ubuntu.com",
                                                         "http://de.archive.ubuntu.com"))
        self.assertFalse(aptsources.sourceslist.is_mirror("http://archive.ubuntu.com",
                                                          "http://ftp.debian.org"))

    def testSourcesListReading(self):
        apt_pkg.Config.Set("Dir::Etc::sourcelist","data/sources.list")
        sources = aptsources.sourceslist.SourcesList()
        self.assertEqual(len(sources.list), 6)
        # test load
        sources.list = []
        sources.load("data/sources.list")
        self.assertEqual(len(sources.list), 6)

    def testSourcesListAdding(self):
        apt_pkg.Config.Set("Dir::Etc::sourcelist","data/sources.list")
        sources = aptsources.sourceslist.SourcesList()
        # test to add something that is already there (main)
        before = copy.deepcopy(sources)
        sources.add("deb","http://de.archive.ubuntu.com/ubuntu/",
                    "edgy",
                    ["main"])
        self.assertTrue(sources.list == before.list)
        # test to add something that is already there (restricted)
        before = copy.deepcopy(sources)
        sources.add("deb","http://de.archive.ubuntu.com/ubuntu/",
                    "edgy",
                    ["restricted"])
        self.assertTrue(sources.list == before.list)
        # test to add something new: multiverse
        sources.add("deb","http://de.archive.ubuntu.com/ubuntu/",
                    "edgy",
                    ["multiverse"])
        found = False
        for entry in sources:
            if (entry.type == "deb" and
                entry.uri == "http://de.archive.ubuntu.com/ubuntu/" and
                entry.dist == "edgy" and
                "multiverse" in entry.comps):
                found = True
        self.assertTrue(found)
        # test to add something new: multiverse *and* 
        # something that is already there
        before = copy.deepcopy(sources)
        sources.add("deb","http://de.archive.ubuntu.com/ubuntu/",
                    "edgy",
                    ["universe", "something"])
        found_universe = 0
        found_something = 0
        for entry in sources:
            if (entry.type == "deb" and
                entry.uri == "http://de.archive.ubuntu.com/ubuntu/" and
                entry.dist == "edgy"):
                for c in entry.comps:
                    if c == "universe":
                        found_universe += 1
                    if c == "something":
                        found_something += 1
        #print "\n".join([s.str() for s in sources])
        self.assertEqual(found_something, 1)
        self.assertEqual(found_universe, 1)

    def testMatcher(self):
        apt_pkg.Config.Set("Dir::Etc::sourcelist","data/sources.list.testDistribution")
        sources = aptsources.sourceslist.SourcesList()
        distro = aptsources.distro.get_distro()
        distro.get_sources(sources)
        # test if all suits of the current distro were detected correctly
        dist_templates = set()
        for s in sources:
            if not s.template:
                self.fail("source entry '%s' has no matcher" % s)

    def testDistribution(self):
        apt_pkg.Config.Set("Dir::Etc::sourcelist","data/sources.list.testDistribution")
        sources = aptsources.sourceslist.SourcesList()
        distro = aptsources.distro.get_distro()
        distro.get_sources(sources)
        # test if all suits of the current distro were detected correctly
        dist_templates = set()
        for s in sources:
            if s.template:
                dist_templates.add(s.template.name)
        #print dist_templates
        for d in ["hardy","hardy-security","hardy-updates","intrepid","hardy-backports"]:
            self.assertTrue(d in dist_templates)
        # test enable 
        comp = "restricted"
        distro.enable_component(comp)
        found = {}
        for entry in sources:
            if (entry.type == "deb" and
                entry.uri == "http://de.archive.ubuntu.com/ubuntu/" and
                "edgy" in entry.dist):
                for c in entry.comps:
                    if c == comp:
                        if not found.has_key(entry.dist):
                            found[entry.dist] = 0
                        found[entry.dist] += 1
        #print "".join([s.str() for s in sources])
        for key in found:
            self.assertEqual(found[key], 1)

        # add a not-already available component
        comp = "multiverse"
        distro.enable_component(comp)
        found = {}
        for entry in sources:
            if (entry.type == "deb" and
                entry.template and
                entry.template.name == "edgy"):
                for c in entry.comps:
                    if c == comp:
                        if not found.has_key(entry.dist):
                            found[entry.dist] = 0
                        found[entry.dist] += 1
        #print "".join([s.str() for s in sources])
        for key in found:
            self.assertEqual(found[key], 1)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_aptsources_ports
#!/usr/bin/env python

import unittest
import apt_pkg
import os
import copy

import sys
sys.path.insert(0, "../")
import aptsources
import aptsources.sourceslist
import aptsources.distro

class TestAptSources(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        apt_pkg.init()
        apt_pkg.Config.Set("APT::Architecture","powerpc")
        apt_pkg.Config.Set("Dir::Etc", os.path.join(os.getcwd(),"test-data-ports"))
        apt_pkg.Config.Set("Dir::Etc::sourceparts","/xxx")

    def testMatcher(self):
        apt_pkg.Config.Set("Dir::Etc::sourcelist","sources.list")
        sources = aptsources.sourceslist.SourcesList()
        distro = aptsources.distro.get_distro("Ubuntu","hardy","desc","8.04")
        distro.get_sources(sources)
        # test if all suits of the current distro were detected correctly
        dist_templates = set()
        for s in sources:
            if not s.line.strip() or s.line.startswith("#"):
                continue
            if not s.template:
                self.fail("source entry '%s' has no matcher" % s)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_debextract
#!/usr/bin/python

import apt_inst
import sys

def Callback(What,Name,Link,Mode,UID,GID,Size,MTime,Major,Minor):
    print "%s '%s','%s',%u,%u,%u,%u,%u,%u,%u" % (
        What,Name,Link,Mode,UID,GID,Size, MTime, Major, Minor)

member = "data.tar.lzma" 
if len(sys.argv) > 2:
    member = sys.argv[2]
apt_inst.debExtract(open(sys.argv[1]), Callback, member)

########NEW FILE########
__FILENAME__ = test_extract_archive
#!/usr/bin/python

import apt
import apt_inst
import os
import sys

print os.getcwd()
apt_inst.debExtractArchive(open(sys.argv[1]), "/tmp/")
print os.getcwd()

########NEW FILE########
__FILENAME__ = test_hashsums
#!/usr/bin/python

import unittest
import apt_pkg

class testHashes(unittest.TestCase):
    " test the hashsum functions against strings and files "

    def testMD5(self):
        # simple
        s = "foo"
        s_md5 = "acbd18db4cc2f85cedef654fccc4a4d8"
        res = apt_pkg.md5sum(s)
        self.assert_(res == s_md5)
        # file
        res = apt_pkg.md5sum(open("hashsum_test.data"))
        self.assert_(res == s_md5)
        # with zero (\0) in the string
        s = "foo\0bar"
        s_md5 = "f6f5f8cd0cb63668898ba29025ae824e"
        res = apt_pkg.md5sum(s)
        self.assert_(res == s_md5)
        # file
        res = apt_pkg.md5sum(open("hashsum_test_with_zero.data"))
        self.assert_(res == s_md5)

    def testSHA1(self):
        # simple
        s = "foo"
        s_hash = "0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        res = apt_pkg.sha1sum(s)
        self.assert_(res == s_hash)
        # file
        res = apt_pkg.sha1sum(open("hashsum_test.data"))
        self.assert_(res == s_hash)
        # with zero (\0) in the string
        s = "foo\0bar"
        s_hash = "e2c300a39311a2dfcaff799528415cb74c19317f"
        res = apt_pkg.sha1sum(s)
        self.assert_(res == s_hash)
        # file
        res = apt_pkg.sha1sum(open("hashsum_test_with_zero.data"))
        self.assert_(res == s_hash)

    def testSHA256(self):
        # simple
        s = "foo"
        s_hash = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        res = apt_pkg.sha256sum(s)
        self.assert_(res == s_hash)
        # file
        res = apt_pkg.sha256sum(open("hashsum_test.data"))
        self.assert_(res == s_hash)
        # with zero (\0) in the string
        s = "foo\0bar"
        s_hash = "d6b681bfce7155d44721afb79c296ef4f0fa80a9dd6b43c5cf74dd0f64c85512"
        res = apt_pkg.sha256sum(s)
        self.assert_(res == s_hash)
        # file
        res = apt_pkg.sha256sum(open("hashsum_test_with_zero.data"))
        self.assert_(res == s_hash)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = get_debian_mirrors
#!/usr/bin/env python
#
#  get_debian_mirrors.py
#
#  Download the latest list with available mirrors from the Debian 
#  website and extract the hosts from the raw page
#
#  Copyright (c) 2006 Free Software Foundation Europe
#
#  Author: Sebastian Heinlein <glatzor@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import urllib2
import re
import os
import commands
import sys

# the list of official Ubuntu servers
mirrors = []
# path to the local mirror list
list_path = "../data/templates/Debian.mirrors"

req = urllib2.Request("http://www.debian.org/mirror/mirrors_full")
match = re.compile("^.*>([A-Za-z0-9-.\/_]+)<\/a>.*\n$")
match_location = re.compile('^<strong><a name="([A-Z]+)">.*')

def add_sites(line, proto, sites, mirror_type):
    path = match.sub(r"\1", line)
    for site in sites:
        mirror_type.append("%s://%s%s\n" % (proto, site.lstrip(), path))

try:
    print "Downloading mirrors list from the Debian website..."
    uri=urllib2.urlopen(req)
    for line in uri.readlines():
        if line.startswith('<strong><a name="'):
            location = match_location.sub(r"\1", line)
            if location:
                mirrors.append("#LOC:%s" % location)
        if line.startswith("Site:"):
            sites = line[6:-1].split(",")
        elif line.startswith('Packages over HTTP'):
            add_sites(line, "http", sites, mirrors)
        elif line.startswith('Packages over FTP'):
            add_sites(line, "ftp", sites, mirrors)
    uri.close()
except:
    print "Failed to download or to extract the mirrors list!"
    sys.exit(1)

print "Writing local mirrors list: %s" % list_path
list = open(list_path, "w")
for mirror in mirrors:
    list.write("%s" % mirror)
list.close()
print "Done."

########NEW FILE########
__FILENAME__ = get_ubuntu_mirrors
#!/usr/bin/env python
#
#  get_ubuntu_mirrors.py
#
#  Download the latest list with available mirrors from the Ubuntu
#  wiki and extract the hosts from the raw page
#
#  Copyright (c) 2006 Free Software Foundation Europe
#
#  Author: Sebastian Heinlein <glatzor@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import urllib2
import re
import os
import commands
import sys

# the list of official Ubuntu servers
mirrors = []
# path to the local mirror list
list_path = "../data/templates/Ubuntu.mirrors"

req = urllib2.Request("https://wiki.ubuntu.com/Archive?action=raw")

try:
    print "Downloading mirrors list from the Ubuntu wiki..."
    uri=urllib2.urlopen(req)
    p = re.compile('^.*((http|ftp):\/\/[A-Za-z0-9-.:\/_]+).*\n*$')
    for line in uri.readlines():
         if r"[[Anchor(dvd-images)]]" in line:
             break
         if "http://" in line or "ftp://" in line:
             mirrors.append(p.sub(r"\1", line))
    uri.close()
except:
    print "Failed to download or extract the mirrors list!"
    sys.exit(1)

print "Writing local mirrors list: %s" % list_path
list = open(list_path, "w")
for mirror in mirrors:
    list.write("%s\n" % mirror)
list.close()
print "Done."



########NEW FILE########
__FILENAME__ = get_ubuntu_mirrors_from_lp
#!/usr/bin/env python
#
#  get_ubuntu_lp_mirrors.py
#
#  Download the latest list with available Ubuntu mirrors from Launchpad.net
#  and extract the hosts from the raw page
#
#  Copyright (c) 2006 Free Software Foundation Europe
#
#  Author: Sebastian Heinlein <glatzor@ubuntu.com>
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import urllib2
import re
import sys

# the list of official Ubuntu servers
mirrors = []
# path to the local mirror list
list_path = "../data/templates/Ubuntu.mirrors"


try:
    f = open("/usr/share/iso-codes/iso_3166.tab", "r")
    lines = f.readlines()
    f.close()
except:
    print "Could not read country information"
    sys.exit(1)

countries = {}
for line in lines:
    parts = line.split("\t")
    countries[parts[1].strip()] = parts[0].lower()

req = urllib2.Request("https://launchpad.net/ubuntu/+archivemirrors")
print "Downloading mirrors list from Launchpad..."
try:
    uri=urllib2.urlopen(req)
    content = uri.read()
    uri.close()
except:
    print "Failed to download or extract the mirrors list!"
    sys.exit(1)

content = content.replace("\n", "")

content_splits = re.split(r'<tr class="highlighted"',
                          re.findall(r'<table class="listing" '
                                      'id="mirrors_list">.+?</table>',
                                     content)[0])
lines=[]
def find(split):
    country = re.search(r"<strong>(.+?)</strong>", split)
    if not country:
        return
    if countries.has_key(country.group(1)):
        lines.append("#LOC:%s" % countries[country.group(1)].upper())
    else:
        lines.append("#LOC:%s" % country.group(1))
    # FIXME: currently the protocols are hardcoded: ftp http
    urls = re.findall(r'<a href="(?![a-zA-Z:/_\-]+launchpad.+?">)'
                       '(((http)|(ftp)).+?)">',
                      split)
    map(lambda u: lines.append(u[0]), urls)

map(find, content_splits)

print "Writing local mirrors list: %s" % list_path
list = open(list_path, "w")
for line in lines:
    list.write("%s\n" % line)
list.close()
print "Done."

########NEW FILE########
