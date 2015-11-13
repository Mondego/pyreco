__FILENAME__ = simple-client
# simple isk-daemon test program
from xmlrpclib import ServerProxy

server = ServerProxy("http://localhost:31128/RPC")
data_dir = "/media/media2/prj/net.imgseek.imgdb/src-tests/data/"

#server = ServerProxy("http://192.168.2.6:31128/RPC")
#data_dir = "/home/rnc/workspace/net.imgseek.imgdb/src-tests/data/"

print server

def start_test(tst):
    print '-'*8 + ' ' + tst

def full_run():
    
    start_test('create db')
    
    assert server.createDb(1) == True
    
    start_test('add imgs')
    
    assert server.addImg(1, 7,data_dir+"DSC00007.JPG") == 1
    assert server.addImg(1, 6,data_dir+"DSC00006.JPG") == 1
    assert server.addImg(1, 14,data_dir+"DSC00014.JPG") == 1
    assert server.addImg(1, 17,data_dir+"DSC00017.JPG") == 1
    
    start_test('img count')
    
    assert server.getDbImgCount(1) == 4
    
    start_test('image is on db')
    
    assert server.isImgOnDb(1,7) == True
    
    start_test('save db')
    
    assert server.saveAllDbs() == 1
    
    start_test('reset db')
    
    assert server.resetDb(1) == 1
    assert server.getDbImgCount(1) == 0
    
    start_test('load db')
    
    assert server.loadAllDbs() == 1
    
    assert server.getDbImgCount(1) == 4
    
    assert server.isImgOnDb(1,7) == 1
    assert server.isImgOnDb(1,733) == 0
    
    start_test('remove img')
    
    assert server.removeImg(1,7) == 1
    assert server.removeImg(1,73232) == 0
    assert server.getDbImgCount(1) == 3
    assert server.isImgOnDb(1,7) == 0
    assert server.getDbImgIdList(1) == [6,14,17]
            
    start_test('list database spaces')
    
    assert server.getDbList() == [1]
    
    start_test('add more random images')
    
    fnames = [data_dir+"DSC00007.JPG",
              data_dir+"DSC00006.JPG",
              data_dir+"DSC00014.JPG",
              data_dir+"DSC00017.JPG"
              ]
    
    import random
    for i in range(20,60):
        assert server.addImg(1, i, random.choice(fnames)) == 1
    
    start_test('add keywords')
    
    assert server.addKeywordImg(1,142,3) == False
    assert server.addKeywordImg(1,14,1) == True
    assert server.addKeywordImg(1,14,2) == True
    assert server.addKeywordImg(1,14,3) == True
    assert server.addKeywordImg(1,14,4) == True
    assert server.addKeywordImg(1,17,3) == True
    assert server.addKeywordImg(1,21,3) == True
    assert server.addKeywordImg(1,22,5) == True
    
    start_test('get keywords')
    
    assert server.getKeywordsImg(1,14) == [1,2,3,4]
    assert server.getKeywordsImg(1,17) == [3]
    assert server.getKeywordsImg(1,21) == [3]
    assert server.getKeywordsImg(1,20) == []
    
    start_test('remove keywords')
    
    assert server.removeAllKeywordImg(1,17) == True
    assert server.getKeywordsImg(1,17) == []
    
    start_test('save db')
    
    assert server.saveAllDbs() == 1
    
    start_test('reset db')
    
    assert server.resetDb(1) == 1
    assert server.getDbImgCount(1) == 0
    
    start_test('load db')
    
    assert server.loadAllDbs() == 1
    assert server.getDbImgCount(1) == 43
    
    start_test('get keywords')
    
    assert server.getKeywordsImg(1,14) == [1,2,3,4]

    start_test('query by a keyword')

    # 3: 14, 17, 21
    # 4: 14
    # 5: 22
    
    
    res = server.getAllImgsByKeywords(1, 30, 1, '3')
    assert 14 in res
    assert 17 in res
    assert 21 in res 

    res = server.getAllImgsByKeywords(1, 30, 0, '3,4')
    assert 14 in res
    assert 17 in res
    assert 21 in res
     
    res = server.getAllImgsByKeywords(1, 30, 0, '3,4,5')
    assert 14 in res
    assert 17 in res
    assert 21 in res 
    assert 22 in res 

    res = server.getAllImgsByKeywords(1, 30, 1, '5') 
    assert 22 in res
     
    res = server.getAllImgsByKeywords(1, 30, 1, '3,4') 
    assert 14 in res
    
    start_test('query similarity')
    
    assert len(server.queryImgID(1,6, 3)) == 4    

    start_test('query similarity by a keyword')
    
    #def queryImgIDKeywords(dbId, imgId, numres, kwJoinType, keywords):
    res = server.queryImgIDKeywords(1,6, 3,0,'3,4')
    resids = [r[0] for r in res]
    assert 17 in resids
   
   #  start_test('mostPopularKeywords')
   #  
   #  assert server.addKeywordImg(1,50,1) == True
   #  assert server.addKeywordImg(1,50,2) == True
   #  assert server.addKeywordImg(1,50,3) == True
   #  assert server.addKeywordImg(1,51,1) == True
   #  assert server.addKeywordImg(1,51,2) == True
   #  assert server.addKeywordImg(1,51,3) == True
   #  assert server.addKeywordImg(1,52,3) == True
   #  
   # # dbId, imgs, excludedKwds, count, mode    
   #  res = server.mostPopularKeywords(1, '50,51,52', '1', 3, 0)
   #  resmap = {}
   #  for i in range(len(res)/2):
   #      resmap[res[i*2]] = res[i*2+1]
   #  assert 1 not in resmap.keys()
   #  assert resmap[3] == 3
    
    start_test('full_run finished')

start_test('all tests STARTED')    
full_run()
start_test('all tests FINISHED')
########NEW FILE########
__FILENAME__ = facades
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Jan  8 21:24:38 BRST 2012
# copyright            : (C) 2012 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import utils
from imgdbapi import *

from twisted.web import xmlrpc, resource 
from twisted.spread import pb

class XMLRPCIskResource(xmlrpc.XMLRPC):
    """Will be injected with XML-RPC remote facade methods later"""
    pass

SOAPIskResource = None
# check for SOAP support
has_soap = True
try:
    from twisted.web import soap
except:
    has_soap = False

if has_soap:
    class nSOAPIskResource(soap.SOAPPublisher):
        """Will be injected with SOAP remote facade methods later"""
        pass
    SOAPIskResource = nSOAPIskResource
        
class DataExportResource(resource.Resource):
    """Bulk data export remote facade"""    
    isLeaf = False
    
    def render_GET(self, request):
        if request.args['m'][0] == 'imgidlist':
            dbid = int(request.args['dbid'][0])
            return ','.join([str(x) for x in getDbImgIdList(dbid)])
            
        return "Invalid method. <a href='/'>Return to main page</a>."

class iskPBClient:
    """Remote isk-daemon cluster peers mgmt"""

    def __init__(self, settings, addr):
        
        self.settings = settings
        
        self.addr = addr
        host,port = addr.split(':')
        self.host = host
        self.port = int(port) + 100
        self.root = None # hasn't connected yet
        self.imgIds = {}
        self.failedAttempts = 0

        # try first connection
        self.doFirstHandshake()

    def doFirstHandshake(self):
        rootLog.info('Attempting to connect to isk-deamon instance server at %s:%s ...' % (self.host,self.port))
        
        reactor.connectTCP(self.host, self.port, pbFactory) #IGNORE:E1101
        d = pbFactory.getRootObject()
        d.addCallback(self.connectSuccess)
        d.addErrback(self.connectFailed)
        
    def connectSuccess(self, object):
        rootLog.info("Peer connected succesfully: %s" % self.addr)
        self.root = object
        # announce myself
        self.root.callRemote("remoteConnected", 
                          self.settings.core.get('cluster', 'bindHostname')+":%d"%(self.settings.core.getint('daemon','basePort')))

    def connectFailed(self, reason):
        self.failedAttempts += 1
        rootLog.warn(reason)
        
    def resetFailures(self):
        self.failedAttempts = 0
        
    def onNewStatus(self, status):
        self.globalServerStats = status[1]
        self.imgIds = status[2]
        
    @utils.dumpArgs
    def hasImgId(self, dbId, imgId):
        for dbId in self.imgIds:
            if imgId in self.imgIds[dbId]: return True
        return False
    
class ServiceFacade(pb.Root):
    """Remote methods for isk-daemon server cluster comm"""
        
    peerRefreshRate = 2 # seconds between peer poll for status TODO: should be at settings.py
    maxFailedAttempts = 10
    
    def __init__(self, settings):
        self.settings = settings
        self.knownPeers = []
        self.peerAddressMap = {}
        self.externalFullAddr = self.settings.core.get('cluster', 'bindHostname')+":%d"%(self.settings.core.getint('daemon','basePort'))

        if self.settings.core.getboolean('cluster','isClustered'):
            global pbFactory
            pbFactory = pb.PBClientFactory()
            self.knownPeers = self.settings.core.get('cluster', 'seedPeers') #TODO parse/split list
            reactor.callLater(ServiceFacade.peerRefreshRate, self.refreshPeers) 
            rootLog.info('| Running in cluster mode')            
        else:
            pass
            #rootLog.info('| Cluster mode disabled')  #TODO uncomment when clustering works

    def peerFailed(self, reason, iskClient):
        rootLog.warn("Peer failed: "+iskClient.addr+" : "+str(reason))
        iskClient.failedAttempts += 1
        self.expirePeer(iskClient)
        
    def expirePeer(self, iskClient):
        if iskClient.failedAttempts > ServiceFacade.maxFailedAttempts:
            rootLog.warn("Instance at %s exceeded max failures. Removing from known peers." % iskClient.addr)
            del self.peerAddressMap[iskClient.addr]
            self.knownPeers.remove(iskClient.addr)

    def refreshPeers(self):
        
        def gotStatus(status,iskClient):            
            iskClient.resetFailures()
            #rootLog.debug("%s retd %s" %(iskClient.addr,status[0]))
            
            # sync db ids
            for dbid in status[2]:
                if not imgDB.isValidDB(dbid):
                    imgDB.createdb(dbid)
            
            # update stubs with new data
            iskClient.onNewStatus(status)
            
            # see if theres a new peer
            for addr in status[0]:
                self.remote_addPeer(addr)
                
        for peer in self.knownPeers:
            if peer == ():
                rootLog.error("instance shouldnt have itself as peer, removing")
                self.knownPeers.remove(peer)
                continue
            if not self.peerAddressMap.has_key(peer):
                self.remote_addPeer(peer)
                continue
            iskClient = self.peerAddressMap[peer]
            if not iskClient.root: # hasn't managed to connect and get proxy root obj yet
                iskClient.doFirstHandshake()
                self.expirePeer(iskClient)
                continue
            try:
                d = iskClient.root.callRemote("getStatus")
            except Exception, e:
                self.peerFailed(e,iskClient)
                continue
            d.addCallback(gotStatus, iskClient)
            d.addErrback(self.peerFailed, iskClient)

        # schedule next refresh
        reactor.callLater(ServiceFacade.peerRefreshRate, self.refreshPeers) #IGNORE:E1101        

    def remote_getStatus(self):
        #TODO implment using bloom filters
        #TODO cache for some seconds
        imgIds = {}
        for dbid in imgDB.getDBList():
            imgIds[dbid] = imgDB.getImgIdList(dbid) 
                            
        return [self.knownPeers+[self.externalFullAddr],
                getGlobalServerStats(),
                imgIds]

    def remote_addPeer(self, addr):
        # dont try to connect to myself
        if addr == (self.externalFullAddr): return False
        # add only if new
        if addr not in self.knownPeers:
            self.knownPeers.append(addr)
        if not self.peerAddressMap.has_key(addr):
            self.peerAddressMap[addr] = iskPBClient(self.settings, addr)
        return True

    def remote_remoteConnected(self, hostNamePort):
        rootLog.info('peer %s connected to me' % hostNamePort)        
        return self.remote_addPeer(hostNamePort)

def injectCommonDatabaseFacade(instance, prefix):
    for fcn in CommonDatabaseFacadeFunctions:
        setattr(instance, prefix+fcn.__name__, fcn)



########NEW FILE########
__FILENAME__ = imgdbapi
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Jan  8 21:24:38 BRST 2012
# copyright            : (C) 2012 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

__doc__ = '''
@undocumented:  getClusterKeywords getClusterDb getKeywordsPopular getKeywordsVisualDistance getIdsBloomFilter
 '''

# More epydoc fields:
# http://epydoc.sourceforge.net/manual-fields.html

import time
import logging
import os

import statistics
from urldownloader import urlToFile
import settings
from imgSeekLib.ImageDB import ImgDB

# Globals
remoteCache = None    # global remote cache (memcached) singleton
pbFactory = None     # perspective factory
daemonStartTime = time.time()
hasShutdown = False
iskVersion = "0.9.3"

# misc daemon inits
rootLog = logging.getLogger('imgdbapi')
rootLog.info('+- Initializing isk-daemon server (version %s) ...' % iskVersion)
imgDB = ImgDB(settings)
imgDB.loadalldbs(os.path.expanduser(settings.core.get('database', 'databasePath')))

rootLog.info('| image database initialized')


############ Common functions for all comm backends
#@memoize.simple_memoized
def queryImgID(dbId, id, numres=12, sketch=0, fast=False):
    """
    Return the most similar images to the supplied one. The supplied image must be already indexed, and is referenced by its ID.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id.
    @type  numres: number
    @param numres: Number of results to return. The target image is on the result list.
    @type  sketch: number
    @param sketch: 0 for photographs, 1 for hand-sketched images or low-resolution vector images. 
    @type fast: boolean
    @param fast: if true, only the average color for each image is considered. Image geometry/features are ignored. Search is faster this way.

    @rtype:   array
    @since: 0.7
    @change: 0.9.3: added parameter 'sketch'
    @return:  array of arrays: M{[[image id 1, score],[image id 2, score],[image id 3, score], ...]} (id is Integer, score is Double)
    """    
    dbId = int(dbId)
    id = int(id)
    numres = int(numres)
    
    # load balancing
    global ServiceFacadeInstance
    if settings.core.getboolean('cluster','isClustered') and not imgDB.isImageOnDB(dbId, id):
        for iskc in ServiceFacadeInstance.peerAddressMap.values():
            if iskc.hasImgId(dbId, id): # remote instance has this image. Forward query
                try:
                    d = iskc.root.callRemote("queryImgID", dbId,id,numres,fast)
                    return d #TODO this was using blockOn(d)
                except Exception, e:
                    #TODO peer failure should be noticed
                    #self.peerFailed(e,iskClient)
                    rootLog.error(e)
                    break
    # no remote peer has this image, try locally
    return imgDB.queryImgID(dbId, id, numres,sketch,fast)

def queryImgBlob(dbId, data, numres=12, sketch=0, fast=False):
    """
    Return the most similar images to the supplied one. The target image is specified by its raw binary file data. Most common formats are supported.

    @type  dbId: number
    @param dbId: Database space id.
    @type  data: binary data
    @param data: Target image file binary data.
    @type  numres: number
    @param numres: Number of results to return. The target image is on the result list.
    @type  sketch: number
    @param sketch: 0 for photographs, 1 for hand-sketched images or low-resolution vector images. 
    @type fast: boolean
    @param fast: if true, only the average color for each image is considered. Image geometry/features are ignored. Search is faster this way.
    @rtype:   array
    
    @since: 0.9.3
    @return:  array of arrays: M{[[image id 1, score],[image id 2, score],[image id 3, score], ...]} (id is Integer, score is Double)
    """    
    dbId = int(dbId)
    numres = int(numres)
    
    return imgDB.queryImgBlob(dbId, data.data, numres,sketch,fast)

def queryImgPath(dbId, path, numres=12, sketch=0, fast=False):
    """
    Return the most similar images to the supplied one. The target image is specified using it's full path on the server filesystem.

    @type  dbId: number
    @param dbId: Database space id.
    @type  path: string
    @param path: Target image pth on the server disk.
    @type  numres: number
    @param numres: Number of results to return. The target image is on the result list.
    @type  sketch: number
    @param sketch: 0 for photographs, 1 for hand-sketched images or low-resolution vector images. 
    @type fast: boolean
    @param fast: if true, only the average color for each image is considered. Image geometry/features are ignored. Search is faster this way.
    @rtype:   array
    
    @since: 0.9.3
    @return:  array of arrays: M{[[image id 1, score],[image id 2, score],[image id 3, score], ...]} (id is Integer, score is Double)
    """    
    dbId = int(dbId)
    numres = int(numres)
    
    return imgDB.queryImgPath(dbId, path, numres,sketch,fast)

def addImgBlob(dbId, id, data):
    """
    Add image to database space. Image data is passed directly. It is then processed and indexed. 

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id. The image located on filename will be indexed and from now on should be refered to isk-daemon as this supplied id.
    @type  data: binary 
    @param data: Image binary data
    @rtype:   number
    
    @since: 0.9.3
    @return:  1 in case of success.
    """
    dbId = int(dbId)
    id = int(id)

    try:
        #TODO id should be unsigned long int or something even bigger, also must review swig declarations
        res = imgDB.addImageBlob(dbId, data.data, id)
    except Exception, e:
        if str(e) == 'image already in db':
            rootLog.warn(e)        
        else:
            rootLog.error(e)
        return res
    
    return res

def addImg(dbId, id, filename, fileIsUrl=False):
    """
    Add image to database space. Image file is read, processed and indexed. After this indexing is done, image can be removed from file system.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id. The image located on filename will be indexed and from now on should be refered to isk-daemon as this supplied id.
    @type  filename: string
    @param filename: Physical full file path for the image to be indexed. Should be in one of the supported formats ('jpeg', 'jpg', 'gif', 'png', 'rgb', 'pbm', 'pgm', 'ppm', 'tiff', 'tif', 'rast', 'xbm', 'bmp'). For better results image should have dimension of at least 128x128. Thumbnails are ok. Bigger images will be scaled down to 128x128.
    @type  fileIsUrl: boolean
    @param fileIsUrl: if true, filename is interpreted as an HTTP url and the remote image it points to downloaded and saved to a temporary location (same directory where database file is) before being added to database.
    @rtype:   number
    
    @since: 0.7
    @return:  1 in case of success.
    """
    dbId = int(dbId)
    id = int(id)

    if fileIsUrl: # download it first
        tempFName = os.path.expanduser(settings.core.get('database','databasePath')) + ('_tmp_%d_%d.jpg' % (dbId,id))
        urlToFile(filename,tempFName)
        filename = tempFName
    res = 0
    try:
        #TODO id should be unsigned long int or something even bigger, also must review swig declarations
        res = imgDB.addImage(dbId, filename, id)
    except Exception, e:
        if str(e) == 'image already in db':
            rootLog.warn(e)        
        else:
            rootLog.error(e)
        return res
    
    if (fileIsUrl): os.remove(filename)    
    
    return res

def saveDb(dbId):
    """
    Save the supplied database space if the it has already been saved with a filename (previous call to L{saveDbAs}).
    B{NOTE}: This operation should be used for exporting single database spaces. For regular server instance database persistance, use L{saveAllDbs} and L{loadAllDbs}.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   number
    
    @since: 0.7
    @return:  1 in case of success.
    """        
    dbId = int(dbId)
    return imgDB.savedb(dbId)

def saveDbAs(dbId, filename):
    """
    Save the supplied database space if the it has already been saved with a filename (subsequent save calls can be made to L{saveDb}).

    @type  dbId: number
    @param dbId: Database space id.
    @type  filename: string
    @param filename: Target filesystem full path of the file where data should be stored at. B{NOTE}: This data file contains a single database space and should be used for import/export purposes only. Do not try to load it with a call to L{loadAllDbs}.
    @rtype:   number
    
    @since: 0.7
    @return:  1 in case of success.
    """
    dbId = int(dbId)
    return imgDB.savedbas(dbId, filename)

def loadDb(dbId, filename):
    """
    Load the supplied single-database-space-dump into a database space of given id. An existing database space with the given id will be completely replaced.

    @type  dbId: number
    @param dbId: Database space id.
    @type  filename: string
    @param filename: Target filesystem full path of the file where data is stored at. B{NOTE}: This data file contains a single database space and should be used for import/export purposes only. Do not try to load it with a call to L{loadAllDbs} and vice versa.
    @rtype:   number
    
    @since: 0.7
    @return:  dbId in case of success.
    """    
    dbId = int(dbId)    
    return imgDB.loaddb(dbId, filename)

def removeImg(dbId, id):
    """
    Remove image from database space.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id.
    @rtype:   number
    
    @since: 0.7
    @return:  1 in case of success.
    """    
    id = int(id)
    dbId = int(dbId)    
    return imgDB.removeImg(dbId, id)

def resetDb(dbId):
    """
    Removes all images from a database space, frees memory, reset statistics.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   number
    
    @since: 0.7
    @return:  1 in case of success.
    """    
    dbId = int(dbId)    
    return imgDB.resetdb(dbId)

def createDb(dbId):
    """
    Create new db space. Overwrite database space statistics if one with supplied id already exists.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   number
    
    @since: 0.7
    @return:  dbId in case of success
    """    
    dbId = int(dbId)
    return imgDB.createdb(dbId)
    
def shutdownServer():
    """
    Request a shutdown of this server instance.

    @rtype:   number
    
    @since: 0.7
    @return:  always M{1}
    """
    global hasShutdown

    if hasShutdown: return 1 # already went through a shutdown
    
    if settings.core.getboolean('daemon','saveAllOnShutdown'):
            saveAllDbs()
            imgDB.closedb()

    rootLog.info("Shuting instance down...")
    from twisted.internet import reactor
    reactor.callLater(1, reactor.stop) 
    hasShutdown = True
    return 1

def getDbImgCount(dbId):
    """
    Return count of indexed images on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   number
    
    @since: 0.7
    @return:  image count
    """    
    dbId = int(dbId)
    return imgDB.getImgCount(dbId)

def isImgOnDb(dbId, id):
    """
    Return whether image id exists on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    id = int(id)
    return imgDB.isImageOnDB( dbId, id)

def getImgDimensions(dbId, id):
    """
    Returns image original dimensions when indexed into database.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id.
    @rtype:   array
    
    @since: 0.7
    @return:  array in the form M{[width, height]}
    """    
    dbId = int(dbId)
    id = int(id)
    return imgDB.getImageDimensions(dbId, id)

def calcImgAvglDiff(dbId, id1, id2):
    """
    Return average luminance (over three color channels) difference ratio

    @type  dbId: number
    @param dbId: Database space id.
    @type  id1: number
    @param id1: Target image 1 id.
    @type  id2: number
    @param id2: Target image 2 id.
    @rtype:   number
    
    @since: 0.7
    @return:  float representing difference. The smaller, the most similar.
    """    
    dbId = int(dbId)
    id1 = int(id1)
    id2 = int(id2)
    return imgDB.calcAvglDiff(dbId, id1, id2)

def calcImgDiff(dbId, id1,  id2):
    """
    Return image similarity difference ratio. One value alone for an image pair doesn't mean much. These values should be compared pairwise against each other. 
    
    The smaller the value between two images is (i.e. the more negative the value is), the more similar the 2 images are.

    Comparing one image against itself is a degenerate case and the value returned should be ignored.

    @type  dbId: number
    @param dbId: Database space id.
    @type  id1: number
    @param id1: Target image 1 id.
    @type  id2: number
    @param id2: Target image 2 id.
    @rtype:   number
    
    @since: 0.7
    @return:  float representing difference. The smaller, the most similar.
    """    
    dbId = int(dbId)
    id1 = int(id1)
    id2 = int(id2)
    
    return imgDB.calcDiff(dbId, id1,  id2)

def getImgAvgl(dbId, id):
    """
    Return image average color levels on the three color channels (YIQ color system)

    @type  dbId: number
    @param dbId: Database space id.
    @type  id: number
    @param id: Target image id.
    @rtype:   array of double
    
    @since: 0.7
    @return:  values for YIQ color channels
    """    
    dbId = int(dbId)
    id1 = int(id)
    return imgDB.getImageAvgl(dbId, id1)

def getDbList():
    """
    Return list defined database spaces.

    @rtype:   array
    
    @since: 0.7
    @return:  array of db space ids
    """    
    return imgDB.getDBList()

def getDbImgIdList(dbId):
    """
    Return list of image ids on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   array
    
    @since: 0.7
    @return:  array of image ids
    """    
    
    dbId = int(dbId)
    return imgDB.getImgIdList(dbId)

def getDbDetailedList():
    """
    Return details for all database spaces.

    @rtype:   map
    
    @since: 0.7
    @return:  map key is database space id (as an integer), associated value is array with [getImgCount,
                            queryCount,
                            lastQueryPerMin,
                            queryMinCount,
                            queryMinCur,
                            lastAddPerMin,
                            addMinCount,
                            addMinCur,
                            addCount,
                            addSinceLastSave,
                            lastId,
                            lastSaveTime,
                            fileName
                            ]
    """    
    
    return imgDB.getDBDetailedList()

def saveAllDbsAs(path):
    """
    Persist all existing database spaces.

    @type  path: string
    @param path: Target filesystem full path of the file where data is stored at.
    @rtype:   number
    
    @since: 0.7
    @return:  total db spaces written
    """    
    
    return imgDB.savealldbs(path)


def addKeywordImg(dbId, imgId, hash):
    """
    Adds a keyword to an image.

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id.
    @type  hash: number
    @param hash: Keyword id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if operation was succesful
    """
    dbId = int(dbId)
    imgId = int(imgId)
    return imgDB.addKeywordImg(dbId, imgId, hash)

def getIdsBloomFilter(dbId):
    """
    Return bloom filter containing all images on given db id.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   bloom filter
    
    @since: 0.7
    @return:  bloom filter containing all images on given db id.
    """
    dbId = int(dbId)
    return imgDB.getIdsBloomFilter(dbId)

def getClusterKeywords(dbId, numClusters,keywords):
    """
    Return whether image id exists on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    return imgDB.getClusterKeywords(dbId, numClusters,keywords)

def getClusterDb(dbId, numClusters):
    """
    Return whether image id exists on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    return imgDB.getClusterDb(dbId, numClusters)

def getKeywordsPopular(dbId, numres):
    """
    Return whether image id exists on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    return imgDB.getKeywordsPopular(dbId, numres)

def getKeywordsVisualDistance(dbId, distanceType,  keywords):
    """
    Return whether image id exists on database space.

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    return imgDB.getKeywordsVisualDistance(dbId, distanceType,  keywords)

def getAllImgsByKeywords(dbId, numres, kwJoinType, keywords):
    """
    Return all images with the given keywords

    @type  dbId: number
    @param dbId: Database space id.
    @type  numres: number
    @param numres Number of results desired
    @type  kwJoinType: number
    @param kwJoinType: Logical operator for target keywords: 1 for AND, 0 for OR
    @type  keywords: string
    @param keywords: comma separated list of keyword ids. An empty string will return random images.
    @rtype:   array
    
    @since: 0.7
    @return:  array of image ids
    """    
    dbId = int(dbId)
    keywordIds = [int(x) for x in keywords.split(',') if len(x) > 0]
    if len(keywordIds) == 0:
        keywordIds=[0]
    
    return imgDB.getAllImgsByKeywords(dbId, numres, kwJoinType, keywordIds)

def queryImgIDFastKeywords(dbId, imgId, numres, kwJoinType, keywords):
    """
    Fast query (only considers average color) for similar images considering keywords

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId Target image id. If '0', random images containing the target keywords will be returned.
    @type  numres: number
    @param numres Number of results desired
    @type  kwJoinType: number
    @param kwJoinType: logical operator for keywords: 1 for AND, 0 for OR
    @type  keywords: string
    @param keywords: comma separated list of keyword ids.
    @rtype:   array
    
    @since: 0.7
    @return:  array of arrays: M{[[image id 1, score],[image id 2, score],[image id 3, score], ...]} (id is Integer, score is Double)
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    keywordIds = [int(x) for x in keywords.split(',') if len(x) > 0]
    return imgDB.queryImgIDFastKeywords(dbId, imgId, numres, kwJoinType, keywords)

def queryImgIDKeywords(dbId, imgId, numres, kwJoinType, keywords):
    """
    Query for similar images considering keywords. The input keywords are used for narrowing the
    search space.

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id. If '0', random images containing the target keywords will be returned.
    @type  numres: number
    @param numres: Number of results desired
    @type  kwJoinType: number
    @param kwJoinType: logical operator for keywords: 1 for AND, 0 for OR
    @type  keywords: string
    @param keywords: comma separated list of keyword ids. 
    @rtype:   array
    
    @since: 0.7
    @return:  array of arrays: M{[[image id 1, score],[image id 2, score],[image id 3, score], ...]} (id is Integer, score is Double)
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    keywordIds = [int(x) for x in keywords.split(',') if len(x) > 0]
    return imgDB.queryImgIDKeywords(dbId, imgId, numres, kwJoinType, keywordIds)

def mostPopularKeywords(dbId, imgs, excludedKwds, count, mode):
    """
    Returns the most frequent keywords associated with a given set of images 

    @type  dbId: number
    @param dbId Database space id.
    @type  imgs: string
    @param imgs: Comma separated list of target image ids
    @type  excludedKwds: string
    @param excludedKwds: Comma separated list of keywords ids to be excluded from the frequency count
    @type  count: number
    @param count Number of keyword results desired
    @type  mode: number
    @param mode: ignored, will be used on future versions.
    @rtype:   array
    
    @since: 0.7
    @return:  array of keyword ids and frequencies: [kwd1_id, kwd1_freq, kwd2_id, kwd2_freq, ...]
    """    
    dbId = int(dbId)
    excludedKwds = [int(x) for x in excludedKwds.split(',') if len(x) > 0]
    imgs = [int(x) for x in imgs.split(',') if len(x) > 0]
    
    return imgDB.mostPopularKeywords(dbId, imgs, excludedKwds, count, mode)

def getKeywordsImg(dbId, imgId):
    """
    Returns all keywords currently associated with an image.

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id.
    @rtype:   array
    
    @since: 0.7
    @return:  array of keyword ids
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    return imgDB.getKeywordsImg(dbId, imgId)

def removeAllKeywordImg(dbId, imgId):
    """
    Remove all keyword associations this image has.
    
    Known issue: keyword based queries will continue to consider the image to be associated to this keyword until the database is saved and restored.

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if operation succeeded
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    return imgDB.removeAllKeywordImg(dbId, imgId)

def removeKeywordImg(dbId, imgId, hash):
    """
    Remove the association of a keyword to an image
    
    Known issue: keyword based queries will continue to consider the image to be associated to this keyword until the database is saved and restored.    

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id.
    @type  hash: number
    @param hash: Keyword id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if operation succeeded
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    return imgDB.removeKeywordImg(dbId, imgId, hash)

def addKeywordsImg(dbId, imgId, hashes):
    """
    Associate keywords to image

    @type  dbId: number
    @param dbId: Database space id.
    @type  imgId: number
    @param imgId: Target image id.
    @type  hashes: list of number
    @param hashes: Keyword hashes to associate
    @rtype:   boolean
    
    @since: 0.7
    @return:  true if image id exists
    """    
    dbId = int(dbId)
    imgId = int(imgId)
    return imgDB.addKeywordsImg(dbId, imgId, hashes)

def addDir(dbId, path, recurse):
    """
    Visits a directory recursively and add supported images into database space.

    @type  dbId: number
    @param dbId: Database space id.
    @type  path: string
    @param path: Target filesystem full path of the initial dir.
    @type  recurse: number
    @param recurse: 1 if should visit recursively
    @rtype:   number
    
    @since: 0.7
    @return:  count of images succesfully added
    """    
    
    dbId = int(dbId)
    return imgDB.addDir(dbId, path, recurse)

def loadAllDbsAs(path):
    """
    Loads from disk all previously persisted database spaces. (File resulting from a previous call to L{saveAllDbs}).

    @type  path: string
    @param path: Target filesystem full path of the file where data is stored at.
    @rtype:   number
    
    @since: 0.7
    @return:  total db spaces read
    """    
    
    return imgDB.loadalldbs(path)

def saveAllDbs():
    """
    Persist all existing database spaces on the data file defined at the config file I{settings.py}

    @rtype:   number
    
    @since: 0.7
    @return:  count of persisted db spaces
    """
    
    return imgDB.savealldbs(settings.core.get('database','databasePath'))

def loadAllDbs():
    """
    Loads from disk all previously persisted database spaces on the data file defined at the config file I{settings.py}

    @rtype:   number
    
    @since: 0.7
    @return:  count of persisted db spaces
    """    
    
    return imgDB.loadalldbs(settings.core.get('database','databasePath'))

def removeDb(dbid):
    """
    Remove a database. All images associated with it are also removed.

    @rtype:   boolean
    
    @since: 0.7
    @return:  true if succesful
    """    
    
    return imgDB.removeDb(dbid)

def getGlobalServerStats():
    """
    Return the most similar images to the supplied one.

    @rtype:   map
    
    @since: 0.7
    @return:  key is stat name, value is value. Keys are ['isk-daemon uptime', 'Number of databases', 'Total memory usage', 'Resident memory usage', 'Stack memory usage']
    """    
    
    stats = {}
    
    stats['isk-daemon uptime'] = statistics.human_readable(time.time() - daemonStartTime)
    stats['Number of databases'] = len(imgDB.getDBList())
    stats['Total memory usage'] = statistics.memory()
    stats['Resident memory usage'] = statistics.resident()
    stats['Stack memory usage'] = statistics.stacksize()    
    
    return stats

def isValidDb(dbId):
    """
    Return whether database space id has already been defined

    @type  dbId: number
    @param dbId: Database space id.
    @rtype:   boolean
    
    @since: 0.7
    @return:  True if exists
    """    
    
    dbId = int(dbId)
    return imgDB.isValidDB(dbId)

def getIskLog(window = 30):
    """
    Returns the last lines of text in the iskdaemon instance log

    @type  window: number
    @param window: number of lines to retrieve 

    @rtype:   string
    @return:  text block
    @since: 0.9.3
    """
    from utils import tail
    
    return tail(open(settings.core.get('daemon','logPath')), window)

CommonDatabaseFacadeFunctions = [
                                 queryImgID,
                                 addImg,
                                 saveDb,
                                 loadDb,
                                 removeImg,
                                 resetDb,
                                 removeDb,
                                 createDb,
                                 getDbImgCount,
                                 isImgOnDb,
                                 getImgDimensions,
                                 calcImgAvglDiff,
                                 calcImgDiff,
                                 getImgAvgl,
                                 getDbList,
                                 getDbDetailedList,
                                 getDbImgIdList,
                                 isValidDb,
                                 getGlobalServerStats,
                                 saveDbAs,
                                 saveAllDbs,
                                 loadAllDbs,
                                 saveAllDbsAs,
                                 loadAllDbsAs,
                                 addDir,
                                 shutdownServer,
                                 addKeywordImg,
                                 addKeywordsImg,
                                 removeKeywordImg,
                                 removeAllKeywordImg,
                                 getKeywordsImg,
                                 queryImgIDKeywords,
                                 queryImgIDFastKeywords,
                                 getAllImgsByKeywords,
                                 getKeywordsVisualDistance,
                                 getKeywordsPopular,
                                 getClusterDb,
                                 getClusterKeywords,
                                 getIdsBloomFilter,     
                                 mostPopularKeywords,                                                             
                                 getIskLog,
                                 queryImgBlob,
                                 queryImgPath,
                                 addImgBlob,
                                    ]



########NEW FILE########
__FILENAME__ = settings
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Jan  8 21:24:38 BRST 2012
# copyright            : (C) 2012 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import ConfigParser
import os
import logging

logger = logging.getLogger('isk-daemon')

# Defaults
core = ConfigParser.SafeConfigParser({
    'startAsDaemon' : 'false',                     # run as background process on UNIX systems
    'basePort' : '31128',                          # base tcp port to start listening at for HTTP requests (admin interface, XML-RPC requests, etc)
    'debug' : 'true',                              # print debug messages to console
    'saveAllOnShutdown' : 'true',                  # automatically save all database spaces on server shutdown
    'databasePath' : "~/isk-db",                 # file where to store database files
    'saveInterval' : '120'    ,                    # seconds between each automatic database save
    'automaticSave' : 'false' ,                    # whether the database should be saved automatically
    'isClustered' : 'false'   ,                     # run in cluster mode ? If True, make sure subsequent settings are ok
    'seedPeers' : 'isk2host:31128',                            
    'bindHostname': 'isk1host' ,                 # hostname for this instance. Other instances may try to connect to this hostname
    'logPath': 'isk-daemon.log',
    'logDebug': 'true',
    })

# read from many possible locations
conffile = core.read(['isk-daemon.conf', 
            os.path.expanduser('~/isk-daemon.conf'), 
            "/etc/iskdaemon/isk-daemon.conf", 
            #os.path.join(os.environ.get("ISKCONF"),'isk-daemon.conf'),
            ])

for sec in ['database', 'daemon','cluster']:
    if not core.has_section(sec): core.add_section(sec)

# perform some clean up/bulletproofing
core.set('database', 'databasePath', os.path.expanduser(core.get('database','databasePath')))

# fix windows stuff
if os.name == 'nt': # fix windows stuff
    core.set('database', 'databasePath', os.path.expanduser(core.get('database','databasePath').replace('/','\\')))

def setupLogging():
    # set up logging to file - see previous section for more details
    if core.getboolean('daemon','logDebug'): 
        llevel = logging.DEBUG
    else:
        llevel = logging.INFO
    logging.basicConfig(level = llevel,
                        format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt = '%m-%d %H:%M',
                        filename = core.get('daemon','logPath'),
                        )
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)  # INFO
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    
setupLogging()


if len(conffile) < 1:
    logger.warn('| no config file (isk-daemon.conf) found. Looked at local dir, home user dir and /etc/iskdaemon. Using defaults for everything.')
else:
    logger.info('| using config file "%s"' % conffile[0])



########NEW FILE########
__FILENAME__ = statistics
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import string
import time
import os

def uptime ():
    return string.atof (
            string.split (
                    open ('/proc/uptime', 'r').readline()
                    )[1]
            )


# To iterate is human; to recurse, divine.
def dhms(m,t):
   if not t: return (m,)
   return dhms(m//t[0], t[1:]) + (m % t[0],)

def human_readable(msec):
    msec = msec * 1000
    return '%d days %d hours %d minutes %d seconds'% dhms(msec//1000, (60, 60, 24))

_proc_status = '/proc/%d/status' % os.getpid()

_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

def _VmB(VmKey):
    '''Private.
    '''
    global _proc_status, _scale
     # get pseudo file  /proc/<pid>/status
    try:
        t = open(_proc_status)
        v = t.read()
        t.close()
    except:
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index(VmKey)
    v = v[i:].split(None, 3)  # whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float(v[1]) * _scale[v[2]]


def memory(since=0.0):
    '''Return memory usage in bytes.
    '''
    return _VmB('VmSize:') - since


def resident(since=0.0):
    '''Return resident memory usage in bytes.
    '''
    return _VmB('VmRSS:') - since


def stacksize(since=0.0):
    '''Return stack size in bytes.
    '''
    return _VmB('VmStk:') - since


########NEW FILE########
__FILENAME__ = urldownloader
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import urllib2    

urlopen = urllib2.urlopen
Request = urllib2.Request

def urlToFile(theurl, destfile):
    data = urlData(theurl)
    if not data: return False
    
    f=open(destfile,'wb')
    f.write(data)
    f.close()
    return True

def urlData(theurl):
    if not theurl: return None
    if len(theurl) < 12: return None
    if theurl[:7].lower() != 'http://': return None
    
    txdata = None                                                                           # if we were making a POST type request, we could encode a dictionary of values here - using urllib.urlencode
    txheaders = {'User-agent' : 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7)', 'Referer' : theurl}
    
    try:
        req = Request(theurl, txdata, txheaders)            # create a request object
        handle = urlopen(req)                               # and open it to return a handle on the url
    except:
        return False
    else:
        data = handle.read()
        return data
    
    

########NEW FILE########
__FILENAME__ = utils
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import logging

log = logging.getLogger('core')

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    def newFunc(*args, **kwargs):
        log.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

def dumpArgs(func):
    "This decorator dumps out the arguments passed to a function before calling it"
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name
    def echoFunc(*args,**kwargs):
        log.debug(fname+ "(" + ', '.join('%s=%r' % entry
                                    for entry in zip(argnames,args) + kwargs.items() if entry[0] != 'self') + ')')
        return func(*args, **kwargs)
    return echoFunc

def requireKnownDbId(func):
    "Checks if the 1st parameter (which should be a dbId is valid (has an internal dbSpace entry)"
    def checkFunc(*args,**kwargs):
        if not args[0].dbSpaces.has_key(args[1]):
            raise ImageDBException("attempt to call %s with unknown dbid %d. Have you created it first with createdb() or loaddb()?" %(func.func_name, args[1]))
        return func(*args, **kwargs)
    return checkFunc

def tail( f, window=20 ):
    "returns last n ines from text file"
    # http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if (bytes - BUFSIZ > 0):
            # Seek back one whole BUFSIZ
            f.seek(block*BUFSIZ, 2)
            # read BUFFER
            data.append(f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.append(f.read(bytes))
        linesFound = data[-1].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return '\n'.join(''.join(data).splitlines()[-window:])

########NEW FILE########
__FILENAME__ = daemonize
"""Disk And Execution MONitor (Daemon)

http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731

Configurable daemon behaviors:

   1.) The current working directory set to the "/" directory.
   2.) The current file creation mode mask set to 0.
   3.) Close all open files (1024). 
   4.) Redirect standard I/O streams to "/dev/null".

A failed call to fork() now raises an exception.

References:
   1) Advanced Programming in the Unix Environment: W. Richard Stevens
   2) Unix Programming Frequently Asked Questions:
         http://www.erlenstar.demon.co.uk/unix/faq_toc.html
"""

__author__ = "Chad J. Schroeder"
__copyright__ = "Copyright (C) 2005 Chad J. Schroeder"

__revision__ = "$Id$"
__version__ = "0.2"

# Standard Python modules.
import os               # Miscellaneous OS interfaces.
import sys              # System-specific parameters and functions.

# Default daemon parameters.
# File mode creation mask of the daemon.
UMASK = 0

# Default working directory for the daemon.
WORKDIR = "/"

# Default maximum for the number of available file descriptors.
MAXFD = 1024

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"

def createDaemon():
   """Detach a process from the controlling terminal and run it in the
   background as a daemon.
   """

   try:
      # Fork a child process so the parent can exit.  This returns control to
      # the command-line or shell.  It also guarantees that the child will not
      # be a process group leader, since the child receives a new process ID
      # and inherits the parent's process group ID.  This step is required
      # to insure that the next call to os.setsid is successful.
      if os.name == 'nt':
          raise Exception, "Running as a background process is not support on Windows systems"
      pid = os.fork()
   except OSError, e:
      raise Exception, "%s [%d]" % (e.strerror, e.errno)

   if (pid == 0):    # The first child.
      # To become the session leader of this new session and the process group
      # leader of the new process group, we call os.setsid().  The process is
      # also guaranteed not to have a controlling terminal.
      os.setsid()

      # Is ignoring SIGHUP necessary?
      #
      # It's often suggested that the SIGHUP signal should be ignored before
      # the second fork to avoid premature termination of the process.  The
      # reason is that when the first child terminates, all processes, e.g.
      # the second child, in the orphaned group will be sent a SIGHUP.
      #
      # "However, as part of the session management system, there are exactly
      # two cases where SIGHUP is sent on the death of a process:
      #
      #   1) When the process that dies is the session leader of a session that
      #      is attached to a terminal device, SIGHUP is sent to all processes
      #      in the foreground process group of that terminal device.
      #   2) When the death of a process causes a process group to become
      #      orphaned, and one or more processes in the orphaned group are
      #      stopped, then SIGHUP and SIGCONT are sent to all members of the
      #      orphaned group." [2]
      #
      # The first case can be ignored since the child is guaranteed not to have
      # a controlling terminal.  The second case isn't so easy to dismiss.
      # The process group is orphaned when the first child terminates and
      # POSIX.1 requires that every STOPPED process in an orphaned process
      # group be sent a SIGHUP signal followed by a SIGCONT signal.  Since the
      # second child is not STOPPED though, we can safely forego ignoring the
      # SIGHUP signal.  In any case, there are no ill-effects if it is ignored.
      #
      # import signal           # Set handlers for asynchronous events.
      # signal.signal(signal.SIGHUP, signal.SIG_IGN)

      try:
         # Fork a second child and exit immediately to prevent zombies.  This
         # causes the second child process to be orphaned, making the init
         # process responsible for its cleanup.  And, since the first child is
         # a session leader without a controlling terminal, it's possible for
         # it to acquire one by opening a terminal in the future (System V-
         # based systems).  This second fork guarantees that the child is no
         # longer a session leader, preventing the daemon from ever acquiring
         # a controlling terminal.
         pid = os.fork()    # Fork a second child.
      except OSError, e:
         raise Exception, "%s [%d]" % (e.strerror, e.errno)

      if (pid == 0):    # The second child.
         # Since the current working directory may be a mounted filesystem, we
         # avoid the issue of not being able to unmount the filesystem at
         # shutdown time by changing it to the root directory.
         os.chdir(WORKDIR)
         # We probably don't want the file mode creation mask inherited from
         # the parent, so we give the child complete control over permissions.
         os.umask(UMASK)
      else:
         # exit() or _exit()?  See below.
         os._exit(0)    # Exit parent (the first child) of the second child.
   else:
      # exit() or _exit()?
      # _exit is like exit(), but it doesn't call any functions registered
      # with atexit (and on_exit) or any registered signal handlers.  It also
      # closes any open file descriptors.  Using exit() may cause all stdio
      # streams to be flushed twice and any temporary files may be unexpectedly
      # removed.  It's therefore recommended that child branches of a fork()
      # and the parent branch(es) of a daemon use _exit().
      os._exit(0)    # Exit parent of the first child.

   # Close all open file descriptors.  This prevents the child from keeping
   # open any file descriptors inherited from the parent.  There is a variety
   # of methods to accomplish this task.  Three are listed below.
   #
   # Try the system configuration variable, SC_OPEN_MAX, to obtain the maximum
   # number of open file descriptors to close.  If it doesn't exists, use
   # the default value (configurable).
   #
   # try:
   #    maxfd = os.sysconf("SC_OPEN_MAX")
   # except (AttributeError, ValueError):
   #    maxfd = MAXFD
   #
   # OR
   #
   # if (os.sysconf_names.has_key("SC_OPEN_MAX")):
   #    maxfd = os.sysconf("SC_OPEN_MAX")
   # else:
   #    maxfd = MAXFD
   #
   # OR
   #
   # Use the getrlimit method to retrieve the maximum file descriptor number
   # that can be opened by this process.  If there is not limit on the
   # resource, use the default value.
   #
   import resource        # Resource usage information.
   maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
   if (maxfd == resource.RLIM_INFINITY):
      maxfd = MAXFD
  
   # Iterate through and close all file descriptors.
   for fd in range(0, maxfd):
      try:
         os.close(fd)
      except OSError:    # ERROR, fd wasn't open to begin with (ignored)
         pass

   # Redirect the standard I/O file descriptors to the specified file.  Since
   # the daemon has no controlling terminal, most daemons redirect stdin,
   # stdout, and stderr to /dev/null.  This is done to prevent side-effects
   # from reads and writes to the standard I/O file descriptors.

   # This call to open is guaranteed to return the lowest file descriptor,
   # which will be 0 (stdin), since it was closed above.
   os.open(REDIRECT_TO, os.O_RDWR)    # standard input (0)

   # Duplicate standard input to standard output and standard error.
   os.dup2(0, 1)            # standard output (1)
   os.dup2(0, 2)            # standard error (2)

   return(0)

if __name__ == "__main__":

   retCode = createDaemon()

   # The code, as is, will create a new file in the root directory, when
   # executed with superuser privileges.  The file will contain the following
   # daemon related process parameters: return code, process ID, parent
   # process group ID, session ID, user ID, effective user ID, real group ID,
   # and the effective group ID.  Notice the relationship between the daemon's 
   # process ID, process group ID, and its parent's process ID.

   procParams = """
   return code = %s
   process ID = %s
   parent process ID = %s
   process group ID = %s
   session ID = %s
   user ID = %s
   effective user ID = %s
   real group ID = %s
   effective group ID = %s
   """ % (retCode, os.getpid(), os.getppid(), os.getpgrp(), os.getsid(0),
   os.getuid(), os.geteuid(), os.getgid(), os.getegid())

   open("createDaemon.log", "w").write(procParams + "\n")

   sys.exit(retCode)
########NEW FILE########
__FILENAME__ = ImageDB
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

# standard modules
import sys
import os
import traceback
import time
import logging

# isk modules
import utils

try:
    import imgdb
except:
    logging.error("""Unable to load the C++ extension \"_imgdb.so(pyd)\" module.""")
    logging.error("""See http://www.imgseek.net/isk-daemon/documents-1/compiling""")
    traceback.print_exc()
    sys.exit()

log = logging.getLogger('imageDB')

SUPPORTED_IMG_EXTS = [ 'jpeg', 'jpg', 'gif', 'png', 'rgb', 'jpe', 'pbm', 'pgm', 'ppm', 'tiff', 'tif', 'rast', 'xbm', 'bmp' ] # to help determining img format from extension

def safe_str(obj):
    """ return the byte string representation of obj """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return unicode(obj).encode('unicode_escape')

def addCount(dbSpace):
    # add per minutes counting
    dbSpace.addCount += 1
    if time.localtime()[4] > dbSpace.addMinCur:
        dbSpace.addMinCur = time.localtime()[4]
        dbSpace.lastAddPerMin = dbSpace.addMinCount
    else:
        dbSpace.addMinCount += 1

def countQuery(dbSpace):
    dbSpace.queryCount += 1
    if time.localtime()[4] > dbSpace.queryMinCur:
        dbSpace.queryMinCur = time.localtime()[4]
        dbSpace.lastQueryPerMin = dbSpace.queryMinCount
    else:
        dbSpace.queryMinCount += 1

def normalizeResults(results):
    """ normalize results returned by imgdb """

    res = []
    for i in range(len(results) / 2):
        rid = long(results[i*2])
        rsc = results[i*2+1]
        rsc = -100.0*rsc/38.70  # normalize #TODO is this normalization factor still valid?
        #sanity checks
        if rsc<0:rsc = 0.0
        if rsc>100:rsc = 100.0
        res.append([rid,rsc])
        
    res.reverse()
    return res

class DBSpace:
    def __init__(self, id):
        # statistics
        self.id = id
        self.queryCount = 0
        self.lastQueryPerMin = 0
        self.queryMinCount = 0
        self.queryMinCur = 0
        self.lastAddPerMin = 0
        self.addMinCount = 0
        self.addMinCur = 0
        self.addCount = 0        
        self.addSinceLastSave = 0                
        self.lastId = 1                
        self.lastSaveTime = 0
        self.fileName = 'not yet saved' # currently loaded data file
        
        if not imgdb.isValidDB(id): # only init if needed
            log.debug("New dbSpace requires init: %d"%id)
            imgdb.initDbase(id)
        
    def __str__(self):
        reprs = "DPSpace ; "
        for key in dir(self):
            if not key.startswith('__'):
                value = getattr(self,key)
                if not callable(value):
                    reprs += key + "=" + str(value) + "; "
        return reprs
        
    """
    #TODO not refactoring all ImgDB fcns into here in order to save some function calls
    So this class is in a sense a mere data structure.

    def postLoad(self):
        # adjust last added image id
        self.lastId = self._imgdb.getImageCount(self.id) + 1        
        log.info('Database loaded: ' + self)
    """

#TODO apply memoizing (see utils) to some methods ?
class ImgDB:   
    def __init__(self, settings):
        self.dbSpaces = {}
        self.globalFileName = 'global-imgdb-not-saved-yet'
        # global statistics
        self._settings = settings     
            
    @utils.dumpArgs
    def createdb(self,dbId):
        if self.dbSpaces.has_key(dbId):
            log.warn('Replacing existing database id:'+str(dbId))
        self.dbSpaces[dbId] = DBSpace(dbId)
        self.resetdb(dbId)        
        return dbId

    @utils.dumpArgs        
    def closedb(self):
        return imgdb.closeDbase()
        
    @utils.requireKnownDbId
    @utils.dumpArgs
    def resetdb(self, dbId):
        if imgdb.resetdb(dbId): # succeeded
            self.dbSpaces[dbId] = DBSpace(dbId)
            log.debug("resetdb() ok")            
            return 1
        return 0

    @utils.dumpArgs
    def loaddb(self, dbId, fname):
        if imgdb.resetdb(dbId):
            log.warn('Load is replacing existing database id:'+str(dbId))
        dbSpace = DBSpace(dbId)
        self.dbSpaces[dbId] = dbSpace
        dbSpace.fileName = fname
        
        if not imgdb.loaddb(dbId, fname):
            log.error("Error loading image database")
            del self.dbSpaces[dbId]
            return None
        # adjust last added image id
        log.info('| Database loaded: ' + str(dbSpace))
        dbSpace.lastId = self.getImgCount(dbSpace.id) + 1
        return dbId

    @utils.requireKnownDbId
    @utils.dumpArgs
    def savedb(self,dbId):        
        return imgdb.savedb(dbId, self.dbSpaces[dbId].fileName)
            
    @utils.requireKnownDbId
    @utils.dumpArgs
    def savedbas(self,dbId,fname):        
        if not imgdb.savedb(dbId, fname):
            log.error("Error saving image database")
            return 0
        else:
            dbSpace = self.dbSpaces[dbId]
            dbSpace.lastSaveTime = time.time()
            dbSpace.fileName = fname
            log.info('| Database id=%s saved to "%s"' % ( dbSpace, fname))
            return 1
        
    @utils.dumpArgs
    def loadalldbs(self, fname):
        try:
            dbCount = imgdb.loadalldbs(fname)
            for dbid in self.getDBList():
                self.dbSpaces[dbid] = DBSpace(dbid)
                self.dbSpaces[dbid].lastId = self.getImgCount(dbid) + 1
            log.debug('| Database (%s) loaded with %d spaces' %(fname, dbCount))
            self.globalFileName = fname
            return dbCount            
        except RuntimeError, e:
            log.error(e)
            return 0

    @utils.dumpArgs
    def savealldbs(self, fname=None):
        if not fname:
            fname = self.globalFileName
        res = imgdb.savealldbs(fname)
        if not res:
            log.error("Error saving image database")
            return res
        log.info('| All database spaces saved at "%s"' % fname)
        return res
            
    @utils.requireKnownDbId            
    @utils.dumpArgs    
    def addDir(self, dbId, path, recurse):
        
        path = safe_str(path)        
        
        addedCount = 0
        dbSpace = self.dbSpaces[dbId]
        if not os.path.isdir(path):
            log.error("'%s' does not exist or is not a directory"%path)
            return 0
        for fil in os.listdir(path):
            fil = safe_str(fil)
            fil = path + os.sep + fil 
            if len(fil) > 4 and fil.split('.')[-1].lower() in SUPPORTED_IMG_EXTS:
                try:
                    addedCount += self.addImage(dbId, fil, dbSpace.lastId)
                except RuntimeError, e:
                    log.error(e)
                continue
            if recurse and os.path.isdir(fil):
                addedCount += self.addDir(dbId, fil,recurse)
        return addedCount        

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def removeDb(self, dbId):
        if imgdb.removedb(dbId):
            del self.dbSpaces[dbId]
            return True
        return False

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def addImageBlob(self, dbId, data, newid = None):
        dbSpace = self.dbSpaces[dbId]
        
        if not newid:
            newid = dbSpace.lastId
            
        newid = long(newid)
        addCount(dbSpace)
        # call imgdb
        res = imgdb.addImageBlob(dbId, newid, data)

        if res != 0: # add successful
            dbSpace.lastId = newid + 1
            # time to save automatically ?            
            #TODO this should be a reactor timer
            if self._settings.core.getboolean('database','automaticSave') and \
               time.time() - dbSpace.lastSaveTime > self._settings.core.getint('database','saveInterval'):
                dbSpace.lastSaveTime = time.time()
                self.savealldbs()
        return res

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def addImage(self, dbId, fname,newid = None):
        dbSpace = self.dbSpaces[dbId]
        
        if not newid:
            newid = dbSpace.lastId
            
        newid = long(newid)
        addCount(dbSpace)
       # call imgdb
        res = imgdb.addImage(dbId, newid, fname)

        if res != 0: # add successful
            dbSpace.lastId = newid + 1
            # time to save automatically ?            
            if self._settings.core.getboolean('database','automaticSave') and \
               time.time() - dbSpace.lastSaveTime > self._settings.core.getint('database','saveInterval'):
                dbSpace.lastSaveTime = time.time()
                self.savealldbs()
        return res

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def removeImg(self,dbId,id):
        #TODO should also call the code that saves db after a number of ops
        #id = long(id)        
        return imgdb.removeID(dbId,id)

    def getDBDetailedList(self):
        dbids = self.getDBList()
        detlist = {}
        for id in dbids:
            dbSpace = self.dbSpaces[id]
            detlist[str(id)]= [
                            self.getImgCount(id),
                            dbSpace.queryCount,
                            dbSpace.lastQueryPerMin,
                            dbSpace.queryMinCount,
                            dbSpace.queryMinCur,
                            dbSpace.lastAddPerMin,
                            dbSpace.addMinCount,
                            dbSpace.addMinCur,
                            dbSpace.addCount,
                            dbSpace.addSinceLastSave,
                            dbSpace.lastId,
                            dbSpace.lastSaveTime,
                            dbSpace.fileName,
                            ]
        return detlist

    @utils.requireKnownDbId
    def isImageOnDB(self,dbId,id):
        return imgdb.isImageOnDB(dbId,id)

    @utils.requireKnownDbId
    def calcAvglDiff(self,dbId,id1,id2):
        return imgdb.calcAvglDiff(dbId, id1,id2)

    @utils.requireKnownDbId
    def calcDiff(self,dbId,id1,id2):
        return imgdb.calcDiff(dbId, id1,id2)

    @utils.requireKnownDbId
    def getImageDimensions(self,dbId,id):
        return [imgdb.getImageWidth(dbId,id),imgdb.getImageHeight(dbId,id)]

    @utils.requireKnownDbId
    def getImageAvgl(self,dbId,id):
        return imgdb.getImageAvgl(dbId,id)

    @utils.requireKnownDbId
    def getIdsBloomFilter(self,dbId):
        return imgdb.getIdsBloomFilter(dbId)

    @utils.requireKnownDbId
    def getImgCount(self,dbId):
        return imgdb.getImgCount(dbId)

    @utils.requireKnownDbId
    def getImgIdList(self,dbId):
        return imgdb.getImgIdList(dbId)
    
    def isValidDB(self,dbId):
        return imgdb.isValidDB(dbId)

    def getDBList(self):
        return imgdb.getDBList()
    
    @utils.requireKnownDbId
    def getQueryCount(self,dbId):
        return self.dbSpaces[dbId].queryCount

    @utils.requireKnownDbId
    def getQueryPerMinCount(self,dbId):
        return self.dbSpaces[dbId].lastQueryPerMin

    @utils.requireKnownDbId
    def getAddCount(self,dbId):
        return self.dbSpaces[dbId].addCount

    @utils.requireKnownDbId
    def getAddPerMinCount(self,dbId):
        return self.dbSpaces[dbId].lastAddPerMin

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def addKeywordImg(self, dbId, imgId, hash):
        return imgdb.addKeywordImg(dbId, imgId, hash)

    @utils.requireKnownDbId
    def getClusterKeywords(self,dbId, numClusters,keywords):
        return imgdb.getClusterKeywords(dbId, numClusters,keywords)
    
    @utils.requireKnownDbId
    def getClusterDb(self,dbId, numClusters):
        return imgdb.getClusterDb(dbId, numClusters)
    
    @utils.requireKnownDbId
    def getKeywordsPopular(self,dbId, numres):
        return imgdb.getKeywordsPopular(dbId, numres)
    
    @utils.requireKnownDbId
    def getKeywordsVisualDistance(self,dbId, distanceType,  keywords):
        return imgdb.getKeywordsVisualDistance(dbId, distanceType,  keywords)
    
    @utils.requireKnownDbId
    def getAllImgsByKeywords(self,dbId, numres, kwJoinType, keywords):
        return imgdb.getAllImgsByKeywords(dbId, numres, kwJoinType, keywords)
    
    @utils.requireKnownDbId
    def queryImgIDFastKeywords(self,dbId, imgId, numres, kwJoinType, keywords):
        return imgdb.queryImgIDFastKeywords(dbId, imgId, numres, kwJoinType, keywords)

    @utils.requireKnownDbId
    def queryImgIDKeywords(self,dbId, imgId, numres, kwJoinType, keywords, fast=False):
        dbSpace = self.dbSpaces[dbId]
        
        # return [[resId,resRatio]]
        # update internal counters
        numres = int(numres) + 1
        countQuery(dbSpace)

        # do query
        results = imgdb.queryImgIDKeywords(dbId, imgId, numres, kwJoinType, keywords,fast)            

        res = normalizeResults(results)

        log.debug("queryImgIDKeywords() ret="+str(res))
        return res

    @utils.requireKnownDbId
    def mostPopularKeywords(self,dbId, imgs, excludedKwds, count, mode):
        res = imgdb.mostPopularKeywords(dbId, imgs, excludedKwds, count, mode)        
        log.debug("mostPopularKeywords() ret="+str(res))
        return res

    @utils.requireKnownDbId
    def getKeywordsImg(self,dbId, imgId):
        res = imgdb.getKeywordsImg(dbId, imgId)
        log.debug("getKeywordsImg() ret="+str(res))
        return res
    
    @utils.requireKnownDbId
    @utils.dumpArgs    
    def removeAllKeywordImg(self,dbId, imgId):
        return imgdb.removeAllKeywordImg(dbId, imgId)
    
    @utils.requireKnownDbId
    @utils.dumpArgs    
    def removeKeywordImg(self,dbId, imgId, hash):
        return imgdb.removeKeywordImg(dbId, imgId, hash)
    
    @utils.requireKnownDbId
    @utils.dumpArgs    
    def addKeywordsImg(self,dbId, imgId, hashes):
        return imgdb.addKeywordsImg(dbId, imgId, hashes)

    @utils.requireKnownDbId
    def queryImgBlob(self,dbId,data,numres,sketch=0,fast = False):
        dbSpace = self.dbSpaces[dbId]
        
        # return [[resId,resRatio]]
        # update internal counters
        numres = int(numres) + 1
        countQuery(dbSpace)
        # do query
        results = imgdb.queryImgBlob(dbId,data,numres,sketch,fast)

        res = normalizeResults(results)

        log.debug("queryImgBlob() ret="+str(res))        
        return res

    @utils.requireKnownDbId
    @utils.dumpArgs    
    def queryImgPath(self,dbId,path,numres,sketch=0, fast = False):
        dbSpace = self.dbSpaces[dbId]
        
        # return [[resId,resRatio]]
        # update internal counters
        numres = int(numres) + 1
        countQuery(dbSpace)
        # do query
        results = imgdb.queryImgPath(dbId,path,numres,sketch, fast)

        res = normalizeResults(results)

        log.debug("queryImgPath() ret="+str(res))        
        return res    
    
    @utils.requireKnownDbId
    @utils.dumpArgs    
    def queryImgID(self,dbId,qid,numres,sketch=0,fast = False):
        dbSpace = self.dbSpaces[dbId]
        
        # return [[resId,resRatio]]
        # update internal counters
        numres = int(numres) + 1
        countQuery(dbSpace)
        # do query
        results = imgdb.queryImgID(dbId,qid,numres,sketch, fast)

        res = normalizeResults(results)

        log.debug("queryImgID() ret="+str(res))        
        return res

########NEW FILE########
__FILENAME__ = memcache
#!/usr/bin/env python

"""
client module for memcached (memory cache daemon)

Overview
========

See U{the MemCached homepage<http://www.danga.com/memcached>} for more about memcached.

Usage summary
=============

This should give you a feel for how this module operates::

    import memcache
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    mc.set("some_key", "Some value")
    value = mc.get("some_key")

    mc.set("another_key", 3)
    mc.delete("another_key")
    
    mc.set("key", "1")   # note that the key used for incr/decr must be a string.
    mc.incr("key")
    mc.decr("key")

The standard way to use memcache with a database is like this::

    key = derive_key(obj)
    obj = mc.get(key)
    if not obj:
        obj = backend_api.get(...)
        mc.set(obj)

    # we now have obj, and future passes through this code
    # will use the object from the cache.

Detailed Documentation
======================

More detailed documentation is available in the L{Client} class.
"""

import sys
import socket
import time
import types
try:
    import cPickle as pickle
except ImportError:
    import pickle

__author__    = "Evan Martin <martine@danga.com>"
__version__ = "1.34"
__copyright__ = "Copyright (C) 2003 Danga Interactive"
__license__   = "Python"

SERVER_MAX_KEY_LENGTH = 250

class _Error(Exception):
    pass

class Client:
    """
    Object representing a pool of memcache servers.
    
    See L{memcache} for an overview.

    In all cases where a key is used, the key can be either:
        1. A simple hashable type (string, integer, etc.).
        2. A tuple of C{(hashvalue, key)}.  This is useful if you want to avoid
        making this module calculate a hash value.  You may prefer, for
        example, to keep all of a given user's objects on the same memcache
        server, so you could use the user's unique id as the hash value.

    @group Setup: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog
    @group Insertion: set, add, replace
    @group Retrieval: get, get_multi
    @group Integers: incr, decr
    @group Removal: delete
    @sort: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog,\
           set, add, replace, get, get_multi, incr, decr, delete
    """
    _FLAG_PICKLE  = 1<<0
    _FLAG_INTEGER = 1<<1
    _FLAG_LONG    = 1<<2

    _SERVER_RETRIES = 10  # how many times to try finding a free server.

    # exceptions for Client
    class MemcachedKeyError(Exception):
      pass
    class MemcachedKeyLengthError(MemcachedKeyError):
      pass
    class MemcachedKeyCharacterError(MemcachedKeyError):
      pass

    def __init__(self, servers, debug=0):
        """
        Create a new Client object with the given list of servers.

        @param servers: C{servers} is passed to L{set_servers}.
        @param debug: whether to display error messages when a server can't be
        contacted.
        """
        self.set_servers(servers)
        self.debug = debug
        self.stats = {}
    
    def set_servers(self, servers):
        """
        Set the pool of servers used by this client.

        @param servers: an array of servers.
        Servers can be passed in two forms:
            1. Strings of the form C{"host:port"}, which implies a default weight of 1.
            2. Tuples of the form C{("host:port", weight)}, where C{weight} is
            an integer weight value.
        """
        self.servers = [_Host(s, self.debuglog) for s in servers]
        self._init_buckets()

    def get_stats(self):
        '''Get statistics from each of the servers.  

        @return: A list of tuples ( server_identifier, stats_dictionary ).
            The dictionary contains a number of name/value pairs specifying
            the name of the status field and the string value associated with
            it.  The values are not converted from strings.
        '''
        data = []
        for s in self.servers:
            if not s.connect(): continue
            name = '%s:%s (%s)' % ( s.ip, s.port, s.weight )
            s.send_cmd('stats')
            serverData = {}
            data.append(( name, serverData ))
            readline = s.readline
            while 1:
                line = readline()
                if not line or line.strip() == 'END': break
                stats = line.split(' ', 2)
                serverData[stats[1]] = stats[2]

        return(data)

    def flush_all(self):
        'Expire all data currently in the memcache servers.'
        for s in self.servers:
            if not s.connect(): continue
            s.send_cmd('flush_all')
            s.expect("OK")

    def debuglog(self, str):
        if self.debug:
            sys.stderr.write("MemCached: %s\n" % str)

    def _statlog(self, func):
        if not self.stats.has_key(func):
            self.stats[func] = 1
        else:
            self.stats[func] += 1

    def forget_dead_hosts(self):
        """
        Reset every host in the pool to an "alive" state.
        """
        for s in self.servers:
            s.dead_until = 0

    def _init_buckets(self):
        self.buckets = []
        for server in self.servers:
            for i in range(server.weight):
                self.buckets.append(server)

    def _get_server(self, key):
        if type(key) == types.TupleType:
            serverhash, key = key
        else:
            serverhash = hash(key)

        for i in range(Client._SERVER_RETRIES):
            server = self.buckets[serverhash % len(self.buckets)]
            if server.connect():
                #print "(using server %s)" % server,
                return server, key
            serverhash = hash(str(serverhash) + str(i))
        return None, None

    def disconnect_all(self):
        for s in self.servers:
            s.close_socket()
    
    def delete(self, key, time=0):
        '''Deletes a key from the memcache.
        
        @return: Nonzero on success.
        @rtype: int
        '''
        check_key(key)
        server, key = self._get_server(key)
        if not server:
            return 0
        self._statlog('delete')
        if time != None:
            cmd = "delete %s %d" % (key, time)
        else:
            cmd = "delete %s" % key

        try:
            server.send_cmd(cmd)
            server.expect("DELETED")
        except socket.error, msg:
            server.mark_dead(msg[1])
            return 0
        return 1

    def incr(self, key, delta=1):
        """
        Sends a command to the server to atomically increment the value for C{key} by
        C{delta}, or by 1 if C{delta} is unspecified.  Returns None if C{key} doesn't
        exist on server, otherwise it returns the new value after incrementing.

        Note that the value for C{key} must already exist in the memcache, and it
        must be the string representation of an integer.

        >>> mc.set("counter", "20")  # returns 1, indicating success
        1
        >>> mc.incr("counter")
        21
        >>> mc.incr("counter")
        22

        Overflow on server is not checked.  Be aware of values approaching
        2**32.  See L{decr}.

        @param delta: Integer amount to increment by (should be zero or greater).
        @return: New value after incrementing.
        @rtype: int
        """
        return self._incrdecr("incr", key, delta)

    def decr(self, key, delta=1):
        """
        Like L{incr}, but decrements.  Unlike L{incr}, underflow is checked and
        new values are capped at 0.  If server value is 1, a decrement of 2
        returns 0, not -1.

        @param delta: Integer amount to decrement by (should be zero or greater).
        @return: New value after decrementing.
        @rtype: int
        """
        return self._incrdecr("decr", key, delta)

    def _incrdecr(self, cmd, key, delta):
        check_key(key)
        server, key = self._get_server(key)
        if not server:
            return 0
        self._statlog(cmd)
        cmd = "%s %s %d" % (cmd, key, delta)
        try:
            server.send_cmd(cmd)
            line = server.readline()
            return int(line)
        except socket.error, msg:
            server.mark_dead(msg[1])
            return None

    def add(self, key, val, time=0):
        '''
        Add new key with value.
        
        Like L{set}, but only stores in memcache if the key doesn't already exist.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("add", key, val, time)
    def replace(self, key, val, time=0):
        '''Replace existing key with value.
        
        Like L{set}, but only stores in memcache if the key already exists.  
        The opposite of L{add}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("replace", key, val, time)
    def set(self, key, val, time=0):
        '''Unconditionally sets a key to a given value in the memcache.

        The C{key} can optionally be an tuple, with the first element being the
        hash value, if you want to avoid making this module calculate a hash value.
        You may prefer, for example, to keep all of a given user's objects on the
        same memcache server, so you could use the user's unique id as the hash
        value.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("set", key, val, time)
    
    def _set(self, cmd, key, val, time):
        check_key(key)
        server, key = self._get_server(key)
        if not server:
            return 0

        self._statlog(cmd)

        flags = 0
        if isinstance(val, types.StringTypes):
            pass
        elif isinstance(val, int):
            flags |= Client._FLAG_INTEGER
            val = "%d" % val
        elif isinstance(val, long):
            flags |= Client._FLAG_LONG
            val = "%d" % val
        else:
            flags |= Client._FLAG_PICKLE
            val = pickle.dumps(val, 2)
        
        fullcmd = "%s %s %d %d %d\r\n%s" % (cmd, key, flags, time, len(val), val)
        try:
            server.send_cmd(fullcmd)
            server.expect("STORED")
        except socket.error, msg:
            server.mark_dead(msg[1])
            return 0
        return 1

    def get(self, key):
        '''Retrieves a key from the memcache.
        
        @return: The value or None.
        '''
        check_key(key)
        server, key = self._get_server(key)
        if not server:
            return None

        self._statlog('get')

        try:
            server.send_cmd("get %s" % key)
            rkey, flags, rlen, = self._expectvalue(server)
            if not rkey:
                return None
            value = self._recv_value(server, flags, rlen)
            server.expect("END")
        except (_Error, socket.error), msg:
            if type(msg) is types.TupleType:
                msg = msg[1]
            server.mark_dead(msg)
            return None
        return value

    def get_multi(self, keys):
        '''
        Retrieves multiple keys from the memcache doing just one query.
        
        >>> success = mc.set("foo", "bar")
        >>> success = mc.set("baz", 42)
        >>> mc.get_multi(["foo", "baz", "foobar"]) == {"foo": "bar", "baz": 42}
        1

        This method is recommended over regular L{get} as it lowers the number of
        total packets flying around your network, reducing total latency, since
        your app doesn't have to wait for each round-trip of L{get} before sending
        the next one.

        @param keys: An array of keys.
        @return:  A dictionary of key/value pairs that were available.

        '''

        self._statlog('get_multi')

        server_keys = {}

        # build up a list for each server of all the keys we want.
        for key in keys:
            check_key(key)
            server, key = self._get_server(key)
            if not server:
                continue
            if not server_keys.has_key(server):
                server_keys[server] = []
            server_keys[server].append(key)

        # send out all requests on each server before reading anything
        dead_servers = []
        for server in server_keys.keys():
            try:
                server.send_cmd("get %s" % " ".join(server_keys[server]))
            except socket.error, msg:
                server.mark_dead(msg[1])
                dead_servers.append(server)

        # if any servers died on the way, don't expect them to respond.
        for server in dead_servers:
            del server_keys[server]

        retvals = {}
        for server in server_keys.keys():
            try:
                line = server.readline()
                while line and line != 'END':
                    rkey, flags, rlen = self._expectvalue(server, line)
                    #  Bo Yang reports that this can sometimes be None
                    if rkey is not None:
                        val = self._recv_value(server, flags, rlen)
                        retvals[rkey] = val
                    line = server.readline()
            except (_Error, socket.error), msg:
                server.mark_dead(msg)
        return retvals

    def _expectvalue(self, server, line=None):
        if not line:
            line = server.readline()

        if line[:5] == 'VALUE':
            resp, rkey, flags, len = line.split()
            flags = int(flags)
            rlen = int(len)
            return (rkey, flags, rlen)
        else:
            return (None, None, None)

    def _recv_value(self, server, flags, rlen):
        rlen += 2 # include \r\n
        buf = server.recv(rlen)
        if len(buf) != rlen:
            raise _Error("received %d bytes when expecting %d" % (len(buf), rlen))

        if len(buf) == rlen:
            buf = buf[:-2]  # strip \r\n

        if flags == 0:
            val = buf
        elif flags & Client._FLAG_INTEGER:
            val = int(buf)
        elif flags & Client._FLAG_LONG:
            val = long(buf)
        elif flags & Client._FLAG_PICKLE:
            try:
                val = pickle.loads(buf)
            except:
                self.debuglog('Pickle error...\n')
                val = None
        else:
            self.debuglog("unknown flags on get: %x\n" % flags)

        return val


class _Host:
    _DEAD_RETRY = 30  # number of seconds before retrying a dead server.

    def __init__(self, host, debugfunc=None):
        if isinstance(host, types.TupleType):
            host, self.weight = host
        else:
            self.weight = 1

        if host.find(":") > 0:
            self.ip, self.port = host.split(":")
            self.port = int(self.port)
        else:
            self.ip, self.port = host, 11211

        if not debugfunc:
            debugfunc = lambda x: x
        self.debuglog = debugfunc

        self.deaduntil = 0
        self.socket = None

        self.buffer = ''

    def _check_dead(self):
        if self.deaduntil and self.deaduntil > time.time():
            return 1
        self.deaduntil = 0
        return 0

    def connect(self):
        if self._get_socket():
            return 1
        return 0

    def mark_dead(self, reason):
        self.debuglog("MemCache: %s: %s.  Marking dead." % (self, reason))
        self.deaduntil = time.time() + _Host._DEAD_RETRY
        self.close_socket()
        
    def _get_socket(self):
        if self._check_dead():
            return None
        if self.socket:
            return self.socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Python 2.3-ism:  s.settimeout(1)
        try:
            s.connect((self.ip, self.port))
        except socket.error, msg:
            self.mark_dead("connect: %s" % msg[1])
            return None
        self.socket = s
        self.buffer = ''
        return s
    
    def close_socket(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_cmd(self, cmd):
        self.socket.sendall(cmd + '\r\n')

    def readline(self):
        buf = self.buffer
        recv = self.socket.recv
        while True:
            index = buf.find('\r\n')
            if index >= 0:
                break
            data = recv(4096)
            if not data:
                self.mark_dead('Connection closed while reading from %s'
                        % repr(self))
                break
            buf += data
        if index >= 0:
            self.buffer = buf[index+2:]
            buf = buf[:index]
        else:
            self.buffer = ''
        return buf

    def expect(self, text):
        line = self.readline()
        if line != text:
            self.debuglog("while expecting '%s', got unexpected response '%s'" % (text, line))
        return line
    
    def recv(self, rlen):
        self_socket_recv = self.socket.recv
        buf = self.buffer
        while len(buf) < rlen:
            foo = self_socket_recv(4096)
            buf += foo
            if len(foo) == 0:
                raise _Error, ( 'Read %d bytes, expecting %d, '
                        'read returned 0 length bytes' % ( len(buf), foo ))
        self.buffer = buf[rlen:]
        return buf[:rlen]

    def __str__(self):
        d = ''
        if self.deaduntil:
            d = " (dead until %d)" % self.deaduntil
        return "%s:%d%s" % (self.ip, self.port, d)

def check_key(key):
    """
    Checks to make sure the key is less than SERVER_MAX_KEY_LENGTH or contains control characters.
    If test fails throws MemcachedKeyLength error.
    """
    if len(key) > SERVER_MAX_KEY_LENGTH:
      raise Client.MemcachedKeyLengthError, "Key length is > %s" % SERVER_MAX_KEY_LENGTH
    for char in key:
      if ord(char) < 33:
        raise Client.MemcachedKeyCharacterError, "Control characters not allowed"

def _doctest():
    import doctest, memcache
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)
    globs = {"mc": mc}
    return doctest.testmod(memcache, globs=globs)

if __name__ == "__main__":
    print "Testing docstrings..."
    _doctest()
    print "Running tests:"
    print
    #servers = ["127.0.0.1:11211", "127.0.0.1:11212"]
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)

    def to_s(val):
        if not isinstance(val, types.StringTypes):
            return "%s (%s)" % (val, type(val))
        return "%s" % val
    def test_setget(key, val):
        print "Testing set/get {'%s': %s} ..." % (to_s(key), to_s(val)),
        mc.set(key, val)
        newval = mc.get(key)
        if newval == val:
            print "OK"
            return 1
        else:
            print "FAIL"
            return 0

    class FooStruct:
        def __init__(self):
            self.bar = "baz"
        def __str__(self):
            return "A FooStruct"
        def __eq__(self, other):
            if isinstance(other, FooStruct):
                return self.bar == other.bar
            return 0
        
    test_setget("a_string", "some random string")
    test_setget("an_integer", 42)
    if test_setget("long", long(1<<30)):
        print "Testing delete ...",
        if mc.delete("long"):
            print "OK"
        else:
            print "FAIL"
    print "Testing get_multi ...",
    print mc.get_multi(["a_string", "an_integer"])

    print "Testing get(unknown value) ...",
    print to_s(mc.get("unknown_value"))

    f = FooStruct()
    test_setget("foostruct", f)

    print "Testing incr ...",
    x = mc.incr("an_integer", 1)
    if x == 43:
        print "OK"
    else:
        print "FAIL"

    print "Testing decr ...",
    x = mc.decr("an_integer", 1)
    if x == 42:
        print "OK"
    else:
        print "FAIL"



# vim: ts=4 sw=4 et :

########NEW FILE########
__FILENAME__ = memoize
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

"""from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498110
"""

import logging

log = logging.getLogger('ImageDB')

import cPickle

__all__ = ['memoize']

# This would usually be defined elsewhere
class decoratorargs(object):
	def __new__(typ, *attr_args, **attr_kwargs):
		def decorator(orig_func):
			self = object.__new__(typ)
			self.__init__(orig_func, *attr_args, **attr_kwargs)
			return self
		
		return decorator


class memoize(decoratorargs):
	class Node:
		__slots__ = ['key', 'value', 'older', 'newer']
		def __init__(self, key, value, older=None, newer=None):
			self.key = key
			self.value = value
			self.older = older
			self.newer = newer
	
	def __init__(self, func, capacity, keyfunc=lambda *args, **kwargs: cPickle.dumps((args, kwargs))):
		self.func = func
		self.capacity = capacity
		self.keyfunc = keyfunc
		self.reset()
	
	def reset(self):
		self.mru = self.Node(None, None)
		self.mru.older = self.mru.newer = self.mru
		self.nodes = {self.mru.key: self.mru}
		self.count = 1
		self.hits = 0
		self.misses = 0
	
	def __call__(self, *args, **kwargs):
		key = self.keyfunc(*args, **kwargs)
		try:
			node = self.nodes[key]
			log.debug("internal cache hit for '%s'"%key)
		except KeyError:
			log.debug("internal cache miss for '%s'"%key)
			# We have an entry not in the cache
			self.misses += 1
			
			value = self.func(*args, **kwargs)

			lru = self.mru.newer  # Always true
			
			# If we haven't reached capacity
			if self.count < self.capacity:
				# Put it between the MRU and LRU - it'll be the new MRU
				node = self.Node(key, value, self.mru, lru)
				self.mru.newer = node
	
				lru.older = node
				self.mru = node
				self.count += 1
			else:
				# It's FULL! We'll make the LRU be the new MRU, but replace its
				# value first
				del self.nodes[lru.key]  # This mapping is now invalid
				lru.key = key
				lru.value = value
				self.mru = lru

			# Add the new mapping
			self.nodes[key] = self.mru
			return value
		
		# We have an entry in the cache
		self.hits += 1
		
		# If it's already the MRU, do nothing
		if node is self.mru:
			return node.value
		
		lru = self.mru.newer  # Always true
		
		# If it's the LRU, update the MRU to be it
		if node is lru:
			self.mru = lru
			return node.value
		
		# Remove the node from the list
		node.older.newer = node.newer
		node.newer.older = node.older
		
		# Put it between MRU and LRU
		node.older = self.mru
		self.mru.newer = node
		
		node.newer = lru
		lru.older = node
		
		self.mru = node
		return node.value

class simple_memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
      	 log.debug("internal cache miss for '%s'"%args)
         self.cache[args] = value = self.func(*args)
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__

   def __name__(self):
      """Return the function's docstring."""
      return "asda"
      return self.func.__name__+"_memoized"

"""

# Example usage - fib only needs a cache size of 3 to keep it from
# being an exponential-time algorithm
@memoize(3)
def fib(n): return (n > 1) and (fib(n - 1) + fib(n - 2)) or 1

fib(100)  # => 573147844013817084101L

# This is faster because it doesn't use the default key function -
# it doesn't need to call cPickle.dumps((*args, **kwargs))
@memoize(100, lambda n: n)
def fib(n): return (n > 1) and (fib(n - 1) + fib(n - 2)) or 1

fib(100)  # => 573147844013817084101L

# See what's in the cache
# => [(98, 218922995834555169026L), (99, 354224848179261915075L), (100, 573147844013817084101L)]
[(node.key, node.value) for node in fib.nodes.values()]

# Get an example of the key function working
fib.keyfunc(40)  # => 40

# Simple report on performance
# => Hit %: 0.492462
print 'Hit %%: %f' % (float(fib.hits) / (fib.hits + fib.misses))

# Resize the LRU cache
fib.capacity = 100
fib.reset()  # Not necessary unless you shrink it

"""
########NEW FILE########
__FILENAME__ = utils
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Sun Aug  6, 2006  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import logging

log = logging.getLogger('imageDB')

class ImageDBException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    def newFunc(*args, **kwargs):
        log.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

def dumpArgs(func):
    "This decorator dumps out the arguments passed to a function before calling it"
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name
    def echoFunc(*args,**kwargs):
        log.debug('| ' + fname+ "(" + ', '.join('%s=%r' % entry
                                    for entry in zip(argnames,args) + kwargs.items() if entry[0] != 'self') + ')')
        return func(*args, **kwargs)
    return echoFunc

def requireKnownDbId(func):
    "Checks if the 1st parameter (which should be a dbId is valid (has an internal dbSpace entry)"
    def checkFunc(*args,**kwargs):
        if not args[0].dbSpaces.has_key(args[1]):
            raise ImageDBException("attempt to call %s with unknown dbid %d. Have you created it first with createdb() or loaddb()?" %(func.func_name, args[1]))
        return func(*args, **kwargs)
    return checkFunc


########NEW FILE########
__FILENAME__ = iskdaemon
#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

###############################################################################
# begin                : Feb  5, 2007  4:58 PM
# copyright            : (C) 2003 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###############################################################################

# General imports
import logging
import os
import atexit
 
# isk-daemon imports
from core import settings
from core.imgdbapi import *
from core.facades import *

from imgSeekLib import utils
from imgSeekLib import daemonize

# Globals
rootLog = logging.getLogger('iskdaemon')
ServiceFacadeInstance = None

def startIskDaemon():    
    """ cmd-line daemon entry-point
    """

    # parse command line    
    from optparse import OptionParser
        
    parser = OptionParser(version="%prog "+iskVersion)
    #TODO-2 add option
    #parser.add_option("-f", "--file", dest="filename",
    #                  help="read settings from a file other than 'settings.py'", metavar="FILE")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print debug messages to stdout")
    (options, args) = parser.parse_args()
   
    #TODO-2 show which file was read
    #rootLog.info('+- Reading settings from "%s"' % options.filename)
    if settings.core.getboolean('daemon','startAsDaemon'): daemonize.createDaemon()
      
    rootLog.info('+- Starting HTTP service endpoints...')

    basePort = settings.core.getint('daemon', 'basePort')

    # TwistedMatrix imports
    from twisted.web import server, static
    from twisted.spread import pb
    from twisted.internet import reactor
    from twisted.internet.error import CannotListenError

    # Serve UI
    import ui 
    _ROOT = os.path.join(os.path.dirname(ui.__file__),"admin-www")
    if not os.path.exists(_ROOT): # on Windows? Try serving from current file dir
        import sys
        pathname, scriptname = os.path.split(sys.argv[0])
        _ROOT = os.path.join(pathname,'ui'+ os.sep + "admin-www")
    rootLog.info('| serving web admin from ' + _ROOT)        
    root = static.File(_ROOT)
    rootLog.info('| web admin interface listening for requests at http://localhost:%d/'% basePort)
    
    atexit.register(shutdownServer)
        
    # prepare remote command interfaces
    XMLRPCIskResourceInstance = XMLRPCIskResource()
    injectCommonDatabaseFacade(XMLRPCIskResourceInstance, 'xmlrpc_')

    if has_soap:
        SOAPIskResourceInstance = SOAPIskResource()
        injectCommonDatabaseFacade(SOAPIskResourceInstance, 'soap_')
    
        # expose remote command interfaces
        root.putChild('SOAP', SOAPIskResourceInstance)
        rootLog.info('| listening for SOAP requests at http://localhost:%d/SOAP'% basePort)
    else:
        rootLog.info('| Not listening for SOAP requests. Installing "SOAPpy" python package to enable it.')

    ServiceFacadeInstance = ServiceFacade(settings)
    injectCommonDatabaseFacade(ServiceFacadeInstance, 'remote_')

    # expose remote command interfaces
    root.putChild('RPC', XMLRPCIskResourceInstance)
    rootLog.info('| listening for XML-RPC requests at http://localhost:%d/RPC'% basePort)

    root.putChild('export', DataExportResource())
    rootLog.debug('| listening for data export requests at http://localhost:%d/export'% basePort)

    # start twisted reactor
    try:
        reactor.listenTCP(basePort, server.Site(root)) 
        rootLog.info('| HTTP service endpoints started. Binded to all local network interfaces.')
    except CannotListenError:
        rootLog.error("Socket port %s seems to be in use, is there another instance already running ? Try supplying a different one on the command line as the first argument. Cannot start isk-daemon." % basePort)
        return
        
    rootLog.debug('+- Starting internal service endpoint...')
    reactor.listenTCP(basePort+100, pb.PBServerFactory(ServiceFacadeInstance)) 
    rootLog.debug('| internal service listener started at pb://localhost:%d'% (basePort+100))
    rootLog.info('| Binded to all local network interfaces.')
    
    rootLog.info('+ init finished. Waiting for requests ...')
    reactor.run() 

if __name__ == "__main__":
    startIskDaemon()
    # profiling
    """
    import profile
    profile.run('startIskDaemon()', 'isk.prof')
    """

########NEW FILE########
__FILENAME__ = test_api
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

###############################################################################
# begin                : Sun Jan  8 23:42:48 BRST 2012
# copyright            : Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import xmlrpclib

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-d", "--datadir",
                  dest="datadir",
                  help="local data dir",
                  default=os.getcwd()+'/data/'
                    )
parser.add_option("-s", "--server",
                  dest="server",
                  help="server rpc endpoint url",
                  default='http://127.0.0.1:31128/RPC'
                    )

(options, args) = parser.parse_args()

server_url = options.server
data_dir = options.datadir

def start_test(x): print x

def testAddImage():
    print server_url
    print data_dir
    server = xmlrpclib.ServerProxy(server_url);

    assert server.createDb(1) == True

    start_test('add imgs')

    assert server.addImg(1, 7,data_dir+"DSC00007.JPG") == 1
    assert server.addImg(1, 6,data_dir+"DSC00006.JPG") == 1
    assert server.addImg(1, 14,data_dir+"DSC00014.JPG") == 1
    assert server.addImg(1, 17,data_dir+"DSC00017.JPG") == 1

    start_test('img count')

    assert server.getDbImgCount(1) == 4

    start_test('image is on db')

    assert server.isImgOnDb(1,7) == True

    start_test('save db')

    assert server.saveAllDbs() > 0

    start_test('reset db')

    assert server.resetDb(1) == 1
    assert server.getDbImgCount(1) == 0

    start_test('load db')

    assert server.loadAllDbs() > 0

    assert server.getDbImgCount(1) == 4

    assert server.isImgOnDb(1,7) == 1
    assert server.isImgOnDb(1,733) == 0

    start_test('remove img')

    assert server.removeImg(1,7) == 1
    assert server.removeImg(1,73232) == 0
    assert server.getDbImgCount(1) == 3
    assert server.isImgOnDb(1,7) == 0
    assert server.getDbImgIdList(1) == [6,14,17]

    start_test('list database spaces')

    assert 1 in server.getDbList()

    start_test('add more random images')

    fnames = [data_dir+"DSC00007.JPG",
              data_dir+"DSC00006.JPG",
              data_dir+"DSC00014.JPG",
              data_dir+"DSC00017.JPG"
              ]

    import random
    for i in range(20,60):
        assert server.addImg(1, i, random.choice(fnames)) == 1

    start_test('add keywords')

    assert server.addKeywordImg(1,142,3) == False
    assert server.addKeywordImg(1,14,1) == True
    assert server.addKeywordImg(1,14,2) == True
    assert server.addKeywordImg(1,14,3) == True
    assert server.addKeywordImg(1,14,4) == True
    assert server.addKeywordImg(1,17,3) == True
    assert server.addKeywordImg(1,21,3) == True
    assert server.addKeywordImg(1,22,5) == True

    start_test('get keywords')

    assert server.getKeywordsImg(1,14) == [1,2,3,4]
    assert server.getKeywordsImg(1,17) == [3]
    assert server.getKeywordsImg(1,21) == [3]
    assert server.getKeywordsImg(1,20) == []

    start_test('remove keywords')

    assert server.removeAllKeywordImg(1,17) == True
    assert server.getKeywordsImg(1,17) == []

    start_test('save db')

    assert server.saveAllDbs() > 0

    start_test('reset db')

    assert server.resetDb(1) == 1
    assert server.getDbImgCount(1) == 0

    start_test('load db')

    assert server.loadAllDbs() > 0
    assert server.getDbImgCount(1) == 43

    start_test('get keywords')

    assert server.getKeywordsImg(1,14) == [1,2,3,4]

    start_test('query by a keyword')

    # 3: 14, 17, 21
    # 4: 14
    # 5: 22


    res = server.getAllImgsByKeywords(1, 30, 1, '3')
    assert 14 in res
    assert 17 in res
    assert 21 in res

    res = server.getAllImgsByKeywords(1, 30, 0, '3,4')
    assert 14 in res
    assert 17 in res
    assert 21 in res

    res = server.getAllImgsByKeywords(1, 30, 0, '3,4,5')
    assert 14 in res
    assert 17 in res
    assert 21 in res
    assert 22 in res

    res = server.getAllImgsByKeywords(1, 30, 1, '5')
    assert 22 in res

    res = server.getAllImgsByKeywords(1, 30, 1, '3,4')
    assert 14 in res

    start_test('query similarity')

    assert len(server.queryImgID(1,6, 3)) == 4

    start_test('query similarity by a keyword')

    #def queryImgIDKeywords(dbId, imgId, numres, kwJoinType, keywords):
    res = server.queryImgIDKeywords(1,6, 3,0,'3,4')
    resids = [r[0] for r in res]
    assert 17 in resids

   #  start_test('mostPopularKeywords')
   #
   #  assert server.addKeywordImg(1,50,1) == True
   #  assert server.addKeywordImg(1,50,2) == True
   #  assert server.addKeywordImg(1,50,3) == True
   #  assert server.addKeywordImg(1,51,1) == True
   #  assert server.addKeywordImg(1,51,2) == True
   #  assert server.addKeywordImg(1,51,3) == True
   #  assert server.addKeywordImg(1,52,3) == True
   #
   # # dbId, imgs, excludedKwds, count, mode
   #  res = server.mostPopularKeywords(1, '50,51,52', '1', 3, 0)
   #  resmap = {}
   #  for i in range(len(res)/2):
   #      resmap[res[i*2]] = res[i*2+1]
   #  assert 1 not in resmap.keys()
   #  assert resmap[3] == 3


    #assertEqual(1,server.addImg(1,test_images_dir+"DSC00006.JPG",6,))

import unittest

class APITest(unittest.TestCase):

    def setUp(self):
        self.server = xmlrpclib.ServerProxy(server_url);

    def tearDown(self):
        pass

    def testGetLog(self):
        logs = self.server.getIskLog(2)
        print logs
        assert len(logs)> 10

    def testAddBlob(self):
        data = open(data_dir+"DSC00007.JPG",'rb').read()
        assert self.server.addImgBlob(1, 7,xmlrpclib.Binary(data))

    #TODO refactor the rest of tests into here

if __name__ == '__main__':
    testAddImage()
    unittest.main()

########NEW FILE########
__FILENAME__ = test_imgdb
﻿#!/usr/bin/env python
# -*- coding: UTF-8 -*-

###############################################################################
# begin                : 2008-12-04
# copyright            : Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import unittest
from imgSeekLib.ImageDB import ImgDB 
from core import settings

test_images_dir = 'test/data/'

class ImageDBTest(unittest.TestCase):
    
    def setUp(self):
        self.imgdb = ImgDB(settings)
        self.assertEqual(1,self.imgdb.createdb(1))

    def tearDown(self):
        #self.assertEqual(1,self.imgdb.resetdb(1));
        #self.imgdb.closedb()  
        pass

    def testAddImageUTF8(self):
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"テスト.JPG",6,))
        self.assertEqual(1,self.imgdb.getImgCount(1))
        self.assertEqual(1,self.imgdb.savedbas(1,test_images_dir+"imgdb.data"))
        self.assertEqual(1,self.imgdb.resetdb(1))    
        self.assertEqual(1,self.imgdb.loaddb(1,test_images_dir+"imgdb.data"))
        self.assertEqual(1,self.imgdb.getImgCount(1))

    def testPopular(self):
        #TODO
        # make sure the shuffled sequence does not lose any elements        
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00006.JPG",6,))
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00008.JPG",8))
        self.assertEqual(3,self.imgdb.getImgCount(1))
 
    def testAddImage(self):
        # make sure the shuffled sequence does not lose any elements        
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00006.JPG",6,))
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00008.JPG",8))
        # add by blob
        fname = test_images_dir+"DSC00008.JPG"

        f = open(fname,'rb')
        data = f.read()
        f.close()

        self.assertEqual(1,self.imgdb.addImageBlob(1, data,9))

        assert self.imgdb.calcAvglDiff(1,8,9) == 0
        self.assertEqual(4,self.imgdb.getImgCount(1))
        
        self.assertEqual(1,self.imgdb.isImageOnDB(1,6))
        self.assertEqual(1,self.imgdb.isImageOnDB(1,7))
        self.assertEqual(1,self.imgdb.isImageOnDB(1,8))
        self.assertEqual(1,self.imgdb.isImageOnDB(1,9))
        self.assertEqual(0,self.imgdb.isImageOnDB(1,81))
    
    def testsaveloaddb(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.savedbas(1,test_images_dir+"imgdb.data"))
        self.assertEqual(1,self.imgdb.savedb(1))
        self.assertEqual(1,self.imgdb.resetdb(1))    
        self.assertEqual(1,self.imgdb.loaddb(1,test_images_dir+"imgdb.data"))
        self.assertEqual(1, self.imgdb.getImgCount(1))
        self.assertEqual(1, self.imgdb.isImageOnDB(1,6))        

    def testsaveandloadalldbs(self):
        import os
        dataFile = 'alternate.image.data'

        self.assertEqual(2,self.imgdb.createdb(2))
        self.assertEqual(3,self.imgdb.createdb(3))
        
        self.assertEqual(1,self.imgdb.resetdb(1))
        self.assertEqual(1,self.imgdb.resetdb(2))
        self.assertEqual(1,self.imgdb.resetdb(3))
        
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"Copy of DSC00006.JPG",8))
        
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00021b.JPG",22))
        
        self.assertEqual(3,self.imgdb.savealldbs(dataFile))

        # reset
        self.assertEqual(1,self.imgdb.resetdb(1))
        self.assertEqual(1,self.imgdb.resetdb(2))
        self.assertEqual(1,self.imgdb.resetdb(3))

        self.assertEqual(0, self.imgdb.getImgCount(1))
        self.assertEqual(0, self.imgdb.getImgCount(2))
        self.assertEqual(0, self.imgdb.getImgCount(3))

        self.assertEqual(3,self.imgdb.loadalldbs(dataFile))
        
        self.assertEqual(6, self.imgdb.getImgCount(1))
        self.assertEqual(3, self.imgdb.getImgCount(2))
        self.assertEqual(6, self.imgdb.getImgCount(3))
        
    
    def testaddDir(self):
        self.assertEqual(16,self.imgdb.addDir(1,test_images_dir+"",True))
        self.assertEqual(16,self.imgdb.getImgCount(1))        
    
    def testremoveImg(self):
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1,test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(2,self.imgdb.getImgCount(1))
        self.assertEqual(1,self.imgdb.isImageOnDB(1,6))
        self.assertEqual(1,self.imgdb.removeImg(1,6))
        self.assertEqual(1,self.imgdb.getImgCount(1))
        self.assertEqual(0,self.imgdb.isImageOnDB(1,6))
        
    def testcalcAvglDiff(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        self.assert_(self.imgdb.calcAvglDiff(1, 19,21) > 0.016)
        self.assert_(self.imgdb.calcAvglDiff(1, 22,21) < 0.016)

    def testcalcDiff(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        #TODO   
        
    def testgetImageDimensions(self):
        #TODO
        pass        
    def testgetImageAvgl(self):
        #TODO
        pass        
    def testgetImageAvgl(self):
        #TODO
        pass        
    def testgetImgIdList(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        
        dv = self.imgdb.getImgIdList(1)
        self.assert_(6 in dv)
        self.assert_(8 in dv)
        self.assert_(28 not in dv)
        self.assert_(22 in dv)
        
    def testgetDBList(self):
        self.assertEqual(2,self.imgdb.createdb(2))
        self.assertEqual(3,self.imgdb.createdb(3))
        self.assertEqual(1,self.imgdb.resetdb(1))
        self.assertEqual(1,self.imgdb.resetdb(2))
        self.assertEqual(1,self.imgdb.resetdb(3))
        
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00007.JPG",7))
        
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00007.JPG",7))
        
        dblist = self.imgdb.getDBList()
        self.assert_(1 in dblist)
        self.assert_(2 in dblist)
        self.assert_(3 in dblist)
        self.assertEqual(3, len(dblist))
        
    def testgetQueryCount(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        
        dv = self.imgdb.queryImgID(1,6, 4)
        dv = self.imgdb.queryImgID(1,7, 4)
        dv = self.imgdb.queryImgID(1,8, 4)
        dv = self.imgdb.queryImgID(1,21, 4)
        
        self.assertEqual(4, self.imgdb.getQueryCount(1))
        
    def testgetAddCount(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))

        self.assertEqual(6, self.imgdb.getAddCount(1))
        
    def testqueryImage(self):
        self.assertEqual(2,self.imgdb.createdb(2))
        self.assertEqual(3,self.imgdb.createdb(3))
        self.assertEqual(1,self.imgdb.resetdb(1))
        self.assertEqual(1,self.imgdb.resetdb(2))
        self.assertEqual(1,self.imgdb.resetdb(3))
        
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(2, test_images_dir+"Copy of DSC00006.JPG",8))
        
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(3, test_images_dir+"DSC00021b.JPG",22))
        
        dv = self.imgdb.queryImgID(1,6, 4)
        self.assertEqual(5, len(dv))
       
        # are image clones really scoring as very similar?
        dv = self.imgdb.queryImgID(1,6, 3)
        self.assertEqual(4, len(dv))
        self.assertEqual(8, dv[0][0]) 
        self.assertEqual(6, dv[1][0])
        self.assertEqual(19, dv[2][0]) 

        # query by path
        dv = self.imgdb.queryImgPath(1,test_images_dir+"DSC00007.JPG", 3)
        self.assertEqual(4, len(dv))
        self.assertEqual(7, dv[0][0]) 
            # fast
        dv = self.imgdb.queryImgPath(1,test_images_dir+"DSC00007.JPG", 3,0,True)
        self.assertEqual(4, len(dv))
        self.assertEqual(7, dv[0][0]) 
            # sketch
        dv = self.imgdb.queryImgPath(1,test_images_dir+"DSC00007.JPG", 3,1)
        self.assertEqual(4, len(dv))
        self.assertEqual(7, dv[0][0]) 

        # query non existing
        dv = self.imgdb.queryImgID(2,1139, 4)
        self.assertEqual(0, len(dv))

        # query by blob
        fname = test_images_dir+"DSC00007.JPG"

        f = open(fname,'rb')
        data = f.read()
        f.close()

        dv = self.imgdb.queryImgBlob(1,data, 3)
        self.assertEqual(4, len(dv))
        self.assertEqual(7, dv[0][0]) 
       
        # test Fast search
        dv = self.imgdb.queryImgID(3,21, 4, True)
        self.assertEqual(5, len(dv))
        self.assertEqual(21, dv[0][0]) 
        self.assertEqual(22, dv[1][0])
        self.assertEqual(19, dv[2][0])
        self.assertEqual(7, dv[3][0]) 
        
        dv = self.imgdb.queryImgID(3,6, 2)
        self.assertEqual(3, len(dv))
        self.assertEqual(6, dv[0][0]) 
        self.assertEqual(8, dv[1][0])         
 
    def testgetImageHeight(self):
        pass

        #int getImageHeight(const int dbId, long int id);
        #int getImageWidth(const int dbId, long int id);
    def testaddImageBlob(self):
        pass

        #int addImageBlob(const int dbId, const long int id, const void *blob, const long length);
    def testisValidDB(self):
        self.assertEqual(True, self.imgdb.isValidDB(1))
        self.assertEqual(False, self.imgdb.isValidDB(1311))

    def testdestroydb(self):
        pass
        #int destroydb(const int dbId);
    def testremovedb(self):
        pass
        #bool removedb(const int dbId);

#// keywords in images
    def testremoveKeywordImg(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",1))
        self.imgdb.addKeywordImg(1,1,2)
        kwds = self.imgdb.getKeywordsImg(1,1)
        self.assert_(2 in kwds)
        self.imgdb.removeKeywordImg(1,1,2)
        kwds = self.imgdb.getKeywordsImg(1,1)
        self.assertEqual(0, len(kwds))

    def testremoveAllKeywordImg(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",1))
        self.imgdb.addKeywordImg(1,1,2)
        self.imgdb.removeAllKeywordImg(1, 1);
        kwds = self.imgdb.getKeywordsImg(1,1)
        self.assertEqual(0, len(kwds))

#// query by keywords
    def testqueryImgIDKeywords(self):
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00006.JPG",6))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00007.JPG",7))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"Copy of DSC00006.JPG",8))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00019.JPG",19))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021.JPG",21))
        self.assertEqual(1,self.imgdb.addImage(1, test_images_dir+"DSC00021b.JPG",22))
        
        self.imgdb.addKeywordImg(1,6,2)
        self.imgdb.addKeywordImg(1,7,3)
        self.imgdb.addKeywordImg(1,7,2)

        #std::vector<double> queryImgIDKeywords(const int dbId, long int id, int numres, int kwJoinType, int_vector keywords){
        #dv [[8L, 100], [6L, 100], [19L, 15.272009339950403], [22L, 14.274818233138154], [7L, 14.086848507770208]]

        dv = self.imgdb.queryImgIDKeywords(1,6, 4, 1, [2,3],False) # AND
        ids = [r[0] for r in dv]
        print ids
        self.assert_(7 in ids)
        self.assertEqual(1,len(dv))

        dv = self.imgdb.queryImgIDKeywords(1,6, 4, 0, [2,3],True) # OR
        ids = [r[0] for r in dv]
        print ids
        self.assert_(7 in ids)
        self.assert_(6 in ids)
        self.assertEqual(2,len(dv))

        dv = self.imgdb.queryImgIDKeywords(1,6, 4, 1, [3])
        ids = [r[0] for r in dv]
        print ids
        self.assert_(7 in ids)
        self.assertEqual(1,len(dv))
    
        # no keywords
        dv = self.imgdb.queryImgIDKeywords(1,6, 4, 1, [])
        ids = [r[0] for r in dv]
        print ids
        print dv
        self.assertEqual(0,len(dv))

        # random keywords
        dv = self.imgdb.queryImgIDKeywords(1,0, 4, 1, [3])
        ids = [r[0] for r in dv]
        print ids
        self.assert_(7 in ids)
        self.assertEqual(1,len(dv))

    def testqueryImgIDFastKeywords(self):
        pass
        #std::vector<double> queryImgIDFastKeywords(const int dbId, long int id, int numres, int kwJoinType, std::vector<int> keywords);
    def testtAllImgsByKeywords(self):
        pass
        #std::vector<long int> getAllImgsByKeywords(const int dbId, const int numres, int kwJoinType, std::vector<int> keywords);
    def testgetKeywordsVisualDistance(self):
        pass
        #double getKeywordsVisualDistance(const int dbId, int distanceType, std::vector<int> keywords);
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = win32_svc_wrapper
# -*- coding: iso-8859-1 -*-
###############################################################################
# begin                : Thu Jan 19 23:30:28 BRST 2012
# copyright            : (C) 2012 by Ricardo Niederberger Cabral
# email                : ricardo dot cabral at imgseek dot net
#
###############################################################################
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
###############################################################################

import win32service
import win32serviceutil
import win32event
import servicemanager
import winerror
import sys

class PySvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "iskdaemon"
    _svc_display_name_ = "isk-daemon"
    _svc_description_ = "Visual search image database"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        # create an event to listen for stop requests on
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
    
    def SvcDoRun(self):
        import servicemanager

        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))

        from iskdaemon import startIskDaemon
        startIskDaemon()
   
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        from twisted.internet import reactor
        reactor.stop()

if __name__ == '__main__':
    import os
    if len(sys.argv) == 1:
        try:
            evtsrc_dll = os.path.abspath(servicemanager.__file__)
            servicemanager.PrepareToHostSingle(PySvc)
            servicemanager.Initialize('iskdaemon', evtsrc_dll)
            servicemanager.StartServiceCtrlDispatcher()
        except win32service.error, details:
            if details[0] == winerror.ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
                win32serviceutil.usage()
    else:
        win32serviceutil.HandleCommandLine(PySvc)



########NEW FILE########
