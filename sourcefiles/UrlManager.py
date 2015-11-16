'''
@Author: Rohan Achar ra.rohan@gmail.com
'''

import os, shelve, re
try:
    import urlparse
    from Queue import Queue, Empty, Full
except ImportError:
    import urllib.parse as urlparse
    from queue import Queue, Empty, Full


from threading import Lock

from Crawler4py import Robot
from Crawler4py.OrderedSet import OrderedSet

class UrlManager:
    def __init__(self, config):
        self.config = config
        self.robot = Robot.Robot(self.config)
        self.Frontier = OrderedSet()
        self.Working = set()
        self.Done = set()
        self.Output = Queue(self.config.MaxQueueSize)
        self.FrontierLock = Lock()
        self.WorkingLock = Lock()
        self.DoneLock = Lock()
        self.ShelveLock = Lock()
        self.DocumentCount = 0
        self.ShelveObj = None
        self.__Init()
        

    def __Init(self):
        self.ShelveObj = None
        if self.config.Resumable:
            if (os.access(self.config.PersistentFile, os.F_OK)):
                self.ShelveObj = shelve.open(self.config.PersistentFile)
                keys = self.ShelveObj.keys()
                if len(keys) > 0:
                    for key in keys:
                        if not self.ShelveObj[key][0]:
                            self.Frontier.add((key.decode("utf-8","ignore"), self.ShelveObj[key][1]))
                    return

            self.ShelveObj = shelve.open(self.config.PersistentFile)

        for url in self.config.GetSeeds():
            self.AddToFrontier(url, 0)
        
        return


    def __CleanUrl(self, url):
        parsedset = urlparse.urlparse(url)
        parsedset = parsedset._replace(fragment = "")
        if parsedset.path != "" and parsedset.path[-1] != "/":
            pathparts = parsedset.path.split("/")
            if (len(pathparts) > 1):
                lastpart = pathparts[-1]
                if (re.match("index\..", lastpart)):
                    pathparts = pathparts[:-1]
            parsedset = parsedset._replace(path = ("/".join(pathparts)).rstrip("/"))
            url = urlparse.urlunparse(parsedset)
        return url.rstrip("/")

    def __Valid(self, url, depth):

        parsedset = urlparse.urlparse(url)
        return self.config.AllowedSchemes(parsedset.scheme)\
            and self.robot.Allowed(url)\
            and self.config.ValidUrl(url)\
            and (depth <= self.config.MaxDepth or self.config.MaxDepth <= 0)\
            and (self.DocumentCount <= self.config.NoOfDocToFetch or self.config.NoOfDocToFetch <= 0)

    def __IsShelveVisited(self, url):
        try:
            return self.ShelveObj.has_key(url.encode("utf-8","ignore"))
        except AttributeError:
            return url in self.ShelveObj

    def AddToFrontier(self, url, depth):
        url = self.__CleanUrl(url)
        if not self.__Valid(url, depth):
            
            return False

        complete = False
        with self.ShelveLock, self.FrontierLock, self.WorkingLock, self.DoneLock:
            shelved = False
            if self.config.Resumable:
                if self.__IsShelveVisited(url):
                    shelved = True
            
            if not shelved and url not in self.Frontier and url not in self.Working and url not in self.Done:
                self.Frontier.add((url, depth))
                if self.config.Resumable:
                    try:
                        self.ShelveObj[url.encode("utf-8","ignore")] = (False, depth)
                    except AttributeError:
                        self.ShelveObj[url] = (False, depth)
                    self.ShelveObj.sync()
                complete = True

        return complete

    def GetFromFrontier(self):
        obtained = False
        url = ""
        depth = 0
        with self.FrontierLock, self.WorkingLock:
            if len(self.Frontier) != 0:
                url, depth = self.Frontier.pop(self.config.DepthFirstTraversal)
                self.Working.add(url)
                obtained = True

        return obtained, url, depth

    def MarkUrlAsDone(self, url):
        with self.ShelveLock, self.WorkingLock, self.DoneLock:
            self.DocumentCount += 1
            self.Working.remove(url)
            self.Done.add(url)
            if self.config.Resumable:
                try:
                    depth = self.ShelveObj[url.encode("utf-8","ignore")][1]
                    self.ShelveObj[url.encode("utf-8","ignore")] = (True, depth)
                except AttributeError:
                    depth = self.ShelveObj[url][1]
                    self.ShelveObj[url] = (True, depth)
                self.ShelveObj.sync()


    def AddOutput(self, data):
        self.Output.put(data)

    def GetOutput(self):
        try:
            return (True, self.Output.get(True, self.config.OutBufferTimeOut))
        except Empty:
            print ("No value in Output buffer for " + str(self.config.OutBufferTimeOut) + " secs, dumping working set")
            print (self.Working)
            return (False,)
        
