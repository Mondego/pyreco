__FILENAME__ = bitcount_example
#!/usr/bin/python
"""
Example of using the unique id counter object
"""
__author__ = 'dvirsky'
from kickass_redis.util import TimeSampler
from kickass_redis.patterns.bitmap_counter import BitmapCounter, IdMapper
import random
import time

import logging

if __name__ == '__main__':


    #logging.basicConfig(level=0)

    #create a non sequential to sequential id mapper if needed. for this example we don't really need it, it's here just to show it
    idMapper = IdMapper('uzrs')

    counter = BitmapCounter('unique_users', timeResolutions=(1,),idMapper=idMapper )
    daily_mobile_counter = BitmapCounter('mobile_users', timeResolutions=(BitmapCounter.RES_DAY,),idMapper=idMapper )

    week = tuple((int(time.time() - i*86400) for i in  xrange(7, 0, -1)))
    #print counter.cohortAnalysis(week, 86400)
    #sampling current user
    counter.add(3)


    #Filling with junk entries
    for i in xrange(5000):
        userId = random.randint(1, 1000)
        counter.add(userId)

        if userId % 2 == 0:
            daily_mobile_counter.add(userId)

        time.sleep(0.001)

    timePoints = tuple((time.time() - i for i in  xrange(5, 0, -1)))
    print "Total unique users: %s" % counter.getCount(timePoints)
    print "Total Mobile users: %s" % daily_mobile_counter.getCount([timePoints[0]])
    print "Cohort all users: %s" % counter.cohortAnalysis(timePoints, 1)
    print "Cohort mobile users: %s" % counter.cohortAnalysis(timePoints, 1, filterBitmapKey=daily_mobile_counter.getKey(timePoints[0]))

    print "Funnel all users: %s" % counter.funnelAnalysis(timePoints, 1)
    print "Funnel mobile users: %s" % counter.funnelAnalysis(timePoints, 1, filterBitmapKey=daily_mobile_counter.getKey(timePoints[0]))



    #Getting the unique user count for today
#    counter.getCount((time.time(),), counter.RES_DAY)
#
#    #Getting the the weekly unique users in the past minute
#    timePoints = tuple((time.time() - i for i in  xrange(60, 0, -1)))
#    uniq = counter.aggregateCounts(timePoints, counter.OP_TOTAL, timeResolution=1)
#    print "Unique users for range: %s" % uniq
#
#    #average DAU for the past minute
#    avg = counter.aggregateCounts(timePoints, counter.OP_AVG, timeResolution=1)
#    print "Average users per second in range: %s"  % avg



########NEW FILE########
__FILENAME__ = lua_example
__author__ = 'dvirsky'


import redis
from kickass_redis.patterns.lua import LuaCall, LuaScriptError

#A lua script that multiplies two numbers and stores the result in a key

lua_str = '''
            local val = ARGV[1]*ARGV[2]
            redis.call('set', KEYS[1], val)
            return redis.call('get', KEYS[1])
            '''
conn = redis.Redis()
#Define the call
mult = LuaCall(lua_str, conn)

#Call it once:
print "Result: %s" % mult(keys = ('foor',), args = (3,10))

print "Result: %s" % mult(keys = ('foor2',), args = (5,20))

########NEW FILE########
__FILENAME__ = music_indexer
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

'''
This module demonstrates a very simple music library indexed by artists and titles, with full text search on track details

@author: dvirsky
'''

import redis 
import tagpy
import logging
import os
from kickass_redis.util import InstanceCache, Rediston
from kickass_redis.patterns.object_store.indexing import FullTextKey, UnorderedKey
from kickass_redis.patterns.object_store.condition import  Condition
from kickass_redis.patterns.object_store.objects import IndexedObject, KeySpec


class Track(IndexedObject):
    """
    This class represents a track
    """
    _keySpec = KeySpec(
        FullTextKey( prefix='trk', alias='trackName', fields = {'title': 10, 'artist': 5, 'album': 1 }, delimiter=' '),
        UnorderedKey(fields=('artist','album'),prefix='trk'),
        UnorderedKey(fields=('artist',), prefix='trk')
    )
    _spec = ['path', 'title', 'artist', 'album', 'year', 'genre', 'length']
    
    def __init__(self, **kwargs):

        IndexedObject.__init__(self, **kwargs)

        if hasattr(self,'path'):
            self.basename = os.path.basename(self.path or '') 
    

        
class MusicLibrary(object):
    '''

    '''


    def __init__(self, folders, redisHost = 'localhost', redisPort = 6379, redisDb = 0):
        '''
        Constructor
        @param folders a list of folders to index or monitor
        '''
        
        self.folders = folders
        Track.config(host=redisHost, port=redisPort, db=redisDb)

        
    def scanFolders(self):
        """
        Scan all the folders recursively and index the files in redis
        """
        i = 0
        for folder in self.folders:
            for root, dirs, files in os.walk(folder):
                
                for file in files:
                    
                    try:
                        self._indexFile(root, file)
                    except:
                        
                        logging.exception("Cannot index file %s", file)
                    
        
    def getAll(self, *fields):
        
        return Track.getAll(self.redis, *fields)

    def getAlbum(self, artist, album):

        return Track.get(Condition({'artist': artist, 'album': album}))

    def getArtist(self, artist):

        return Track.get(Condition({'artist': artist}))


    def findTracks(self, string):
        """
        Find tracks according to a string query
        """
        return Track.get(Condition({'trackName': string}))
    
    def get(self, *ids):
        """
        Find tracks according to a string query
        """
        return Track.loadObjects(ids)
        
        
    def _indexFile(self, root, file):
        """
        Index one track in redis based on id3 tags
        """
        path = '%s/%s' % (root, file)
        
    
        try:
            try:
                f = tagpy.FileRef(path)
            except:
                return
            t = f.tag()
            try:
                p = f.audioProperties()
                length = p.length
            except:
                length = 0
            
            
            trk = Track(path = path, title = t.title, album = t.album, artist=t.artist, year = t.year, genre = t.genre, length = length)
            trk.save()
            
        except:
            logging.exception("could not index file")

        
        
if __name__ == '__main__':
    
    
    lib = MusicLibrary(['/path/to/Music'])
    
    lib.scanFolders()
    print lib.findTracks(u'the pixies')
    print lib.getArtist(u'Metronomy')
    print lib.getAlbum(u'The Killers', u'Live From The Royal Albert Hall')
    
########NEW FILE########
__FILENAME__ = users_example
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

__author__ = 'dvirsky'

from kickass_redis.patterns.object_store.objects import IndexedObject, KeySpec
from kickass_redis.patterns.object_store.indexing import UnorderedKey, OrderedNumericalKey, UniqueKey, UniqueKeyDuplicateError
from kickass_redis.patterns.object_store.condition import Condition

import time
import logging
from hashlib import md5



class User(IndexedObject):

    #Used to salt paasswords
    __SALT = 'DFG3rg3egef92f29f2h9f7hAAA'

    #which fields should be saved to redis
    _spec = ('id', 'name', 'email', 'pwhash', 'registrationDate', 'score')

    #The keys for this object
    _keySpec = KeySpec(
        #UnorderedKey(prefix='users',fields=('name',)),
        OrderedNumericalKey(prefix='users', field='score'),
        UniqueKey('users', ('name',))
    )

    def __init__(self, **kwargs):
        IndexedObject.__init__(self, **kwargs)
        self.registrationDate = int(kwargs.get('registrationDate', time.time()))


    def _hashPTPassword(self, pw):
        md = md5()
        md.update(pw + self.__SALT)
        return md.hexdigest()


    def save(self):
        #create a random score...
        if not hasattr(self, 'score'):
            self.score = random.randint(0, 100)
        IndexedObject.save(self)

    def setPassword(self, password, doSave = False):
        self.pwhash = self._hashPTPassword(password)
        if doSave:
            self.save()


    def login(self, email, password):
        users = User.get({'email': email})
        pwhash  =self._hashPTPassword(password)
        if not users:
            logging.warn("Invalid login: %s, %s. no such email", email, password)
            return None

        user = users[0]
        if user.pwhash == pwhash:
            logging.info("Logged user %s successfully!", user)
            return user

        else:
            logging.warn("Passwords do not match. expected %s, got %s", user.pwhash, pwhash)

        return None


if __name__ == '__main__':
    import random
    import time
    from multiprocessing import Pool
    #users =  User.get(Condition({'email': user.email}))



    def creationRunner(n):
        #print "Running %d times!" % int(n)
        for i in xrange(int(n)):

            uid = random.randint(1, 10000000)
            user = User(email = 'user%s@domain.com' % uid, name = 'User %s' % uid)
            user.setPassword('q1w2e3')
            user.save()

    def getRunner(n):
        hits = 0
        for i in xrange(int(n)):

            #uid = random.randint(1, 10000000)
            user = User.loadObjects([i])

            if user:
                hits += 1
            #print user
        #print hits, '/', n


    total = 0

    uid = random.randint(1, 10000000)
    user1 = User(email = 'user%s@domain.com' % uid, name = 'User %s' % uid)
    print "SAVE 1"
    user1.save()
    print "SAVE 2"
    user2 = User(email = 'user%s@domain.com' % uid, name = 'User %s' % uid)
    print "SAVE 3"
    try:
        user2.save()
    except UniqueKeyDuplicateError:
        print "Duplicate caught! yay!"

    u = User.get(Condition({'name': user1.name}))
    print "found %s" % u
    #creationRunner(100)

    #users = User.get(Condition({'score': Condition.Between(95, 100)}, paging= (0,1)))
    #print users
#    for z in xrange(20):
#        st = time.time()
#        N = 100000#
#        procs = 8
#        p = Pool(procs)
#        p.map(creationRunner, [N/procs] * procs)
#        et = time.time()
#        writeTime = et-st
#        total += N
#        print "After %d inserts, rate is %.02f" % (total,N/writeTime)



    #print users
########NEW FILE########
__FILENAME__ = bandit
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.
from __future__ import absolute_import

from ..object_store.objects import  IndexedObject, KeySpec
from ..object_store.indexing import *
import math
import random


class Option(IndexedObject):

    _spec = ('id', 'name', 'playCount', 'reward', 'testId')

    _keySpec = KeySpec(
        OrderedNumericalKey('opt', 'testId'),
        UnorderedKey('opt', ('name','testId'))
    )

    def __init__(self, name = '', playCount = 0, reward = 0, testId = 0, **kwargs):

        IndexedObject.__init__(self,
                                name = name,
                                playCount = int(playCount),
                                reward = int(reward),
                                testId = int(testId),
                                **kwargs)

    @classmethod
    def addReward(cls, testId, name, amount = 1):
        cls.incrementWhere(Condition({'testId': testId, 'name': name}), 'reward', amount)



class Bandit(IndexedObject):

    _spec = ('id', 'name', 'benchmarkLen')

    ALGO_UCB1 = 'ucb1'
    ALGO_EPSILON_GREEDY = 'epsgreedy'

    def __init__(self, name, algo = ALGO_UCB1, benchmarkLen = 60, **kwargs):


        IndexedObject.__init__(self,
                                algo = algo,
                                name = name,
                                benchmarkLen = int(benchmarkLen),
                                **kwargs)
        self.options = []

        #set the algorithm
        if algo == self.ALGO_UCB1:
            self.algo = self._ucb1
        else:
            self.algo = self._epsilon_greedy


    def addOption(self, name):

        opt = Option(name = name, testId = self.id)
        opt.save()
        self.options.append(opt)

    def loadOptions(self, noCache = True):

        if not noCache and self.options:
            return len(self.options)

        self.options = Option.get(Condition({'testId': self.id}))

        return len(self.options)


    def selectOptionByScore(self,noCache = True):

        if not self.loadOptions(noCache):
            raise RuntimeError("Could not load any options for test %s" % self)


        self.totalPlays = sum((opt.playCount for opt in self.options))
        selected = max(self.options, key = self.algo)

        #increment option playcount
        selected.update(playCount = selected.playCount + 1)
        return selected



    def rewardOption(self, option, amount = 1):

        option.update(reward = option.reward + amount)



    def _ucb1(self, option):
        '''
        the actual ucb1 algorithm doesn't start before the preliminary benchmark is done,
        will keep pop options from a list, according to the definition done using init_test,
        until the list if empty.
        after benchmarking, will return the option with the current max ucb score.
        '''

        #for the benchmark rounds - just find the option with the smallest playCount
        if self.totalPlays < len(self.options) * self.benchmarkLen:
            return -option.playCount

        avg_score = float(option.reward) / option.playCount
        return avg_score + math.sqrt(2*math.log(self.totalPlays) / float(option.playCount))

    def _epsilon_greedy(self,  option):
        '''
        naive bandit implementation, will always explore 10% of the times.
        '''
        choice = None
        #sometimes... you just want a random option, man
        if random.random() < 0.1:
            return random.randint(0, len(self.options)**2)

        else:

            return (float(option.reward) / option.playCount) if option.playCount else 0



if __name__ == '__main__':

    bandito = Bandit.createNew(name = 'test_foo%d' % random.randint(1, 1000000000),
                                algo=Bandit.ALGO_EPSILON_GREEDY,
                                benchmarkLen=100)


    for i in xrange(3):

        bandito.addOption('option_%d' % i)


    rounds = 0
    import time
    while rounds < 10000:

        option = bandito.selectOptionByScore(noCache = True)


        r = random.randint(1,10)

        idx = bandito.options.index(option) + 2

        if r%idx ==0 or r % 3 == 0:
            #print "Rewarding option %d" % (idx - 1)

            bandito.rewardOption(option, 1)



        if rounds == bandito.benchmarkLen or rounds % 1000 == 0:
            print "After %d rounds" % rounds
            for option in bandito.options:
                print option
            print "-----------------------------------"

        rounds += 1





########NEW FILE########
__FILENAME__ = bitmap_counter
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.
from __future__ import absolute_import
__author__ = 'dvirsky'


from ..util import Rediston, TimeSampler, InstanceCache
import logging
import time

from ..patterns.idgenerator import  IncrementalIdGenerator

class BitmapCounter(Rediston):
    """
    This class wraps a unique id counter, mainly to be used as a user counter
    It can be set to sample specific time resolutions, the default is daily
    It can aggregate several time resolutions into one count, to be cached for memory optimization
    (TBD: the calss should be able to do this)
    """

    RES_WEEK = 604800
    RES_DAY = 86400
    RES_HOUR = 3600
    RES_MINUTE = 60
    
    SNAP_SUNDAY = 259200
    SNAP_MONDAY = 345600
    
    TZ_GMT = 0
    TZ_PST = -8
    TZ_EST = -5

    OP_TOTAL = 'TOTAL'
    OP_AVG = 'AVG'
    OP_INTERESECT = 'INTERSECT'



    def __init__(self, metricName, timeResolutions=(86400,), snapWeekTo=SNAP_SUNDAY, timeZone=TZ_GMT, idMapper=None):
        """
        Constructor
        @param metricName the name of the metric we're sampling, to be used as the redis key
        @param timeResolutions a tuple of resolutions to be sampled, in seconds
        @param idMapper optional IdMapper object that can convert non sequential ids to sequential ones
        @param snapWeekTo used when a week resolution is set, defines to which day should the timestamp be snapped
        @param timeZone for week snaps, define time zone by difference from GMT in hours
        NOTE: there will be an extra counter key in redis for each resolution, so lots of resolutions can cause huge RAM overhead
        """
        self.metric = metricName
        self.timeResolutions = timeResolutions
        self.idMapper = idMapper
        self.snapWeekTo = snapWeekTo
        self.timeZone = timeZone * self.RES_HOUR

    def getKey(self, timestamp, resolution=None):
        """
        Get the redis key for this object, for internal use
        """
        
        snap = 0
        resolution = resolution or self.timeResolutions[0]
        if resolution == self.RES_WEEK:
            snap = self.snapWeekTo - self.timeZone
        return 'uc:%s:%s:%s' % (self.metric, resolution, int(timestamp - ((timestamp - snap) % resolution)))


    def add(self, objectId, timestamp=None, sequentialIdMappingPrefix=None):
        """
        Add one sample.
        TODO: enable multiple samples in one pipeline
        @param objectId an integer of the object's id. NOTE: do not use this on huge numbers
        @param timestamp the event time, defaults to now
        """

        #map to a sequential id if needed
        if self.idMapper:
            objectId = self.idMapper.getSequentialId(objectId)

        timestamp = timestamp or time.time()

        #get the keys to sample to
        keys = [self.getKey(timestamp, res) for res in self.timeResolutions]
        pipe = self._getPipeline()
        #set the bits
        [pipe.setbit(key, int(objectId), 1) for key in keys]
        pipe.execute()

    def isSet(self, objectId, timestamp, timeResolution=None):
        """
        Tell us whether a specific objectId is set in the counter for a specific resolution
        @param objectId the object to test
        @param timestamp the time to test
        @param timeResolution the time slot to test, defaults to the first resolution given to the counter
        """
        timeResolution = timeResolution or self.timeResolutions[0]
        key = self.getKey(timestamp, timeResolution)
        return self._getConnection().getbit(key, objectId)


    def getCount(self, timestamps, timeResolution=None):
        """
        Count the cardinality of time slots
        @param timestamps a list of timestamps to test
        @param timeResolution the time slot to aggregate, defaults to the first resolution given to the counter
        @return a list of [(timestamp, count), ...]
        """
        timeResolution = timeResolution or self.timeResolutions[0]
        pipe = self._getPipeline()

        [pipe.bitcount(self.getKey(timestamp, timeResolution)) for timestamp in timestamps]
        return zip(timestamps, pipe.execute())



    def aggregateCounts(self, timestamps, op=OP_TOTAL, timeResolution=None, expire=True):
        """
        Aggregate a few time slots, either summing the unique total, average or memebers in all slots
        @param timestamps a list of timestamps to test
        @param op should be one of SUM, AVG, INTERSECT
        @param timeResolution the time slot to aggregate, defaults to the first resolution given to the counter
        @param expire if set to true, we expire the result
        """
        timeResolution = timeResolution or self.timeResolutions[0]

        if op not in  (BitmapCounter.OP_INTERESECT, BitmapCounter.OP_TOTAL, BitmapCounter.OP_AVG):
            raise ValueError("Invalid aggregation op %s" % op)

        if op == BitmapCounter.OP_INTERESECT:
            bitop = 'AND'
        else:
            bitop = 'OR'

        dest = 'aggregate:%s:%s' % (self.metric, hash(timestamps))
        pipe = self._getPipeline()
        pipe.bitop(bitop, dest, *(self.getKey(timestamp, timeResolution) for timestamp in timestamps))
        pipe.bitcount(dest)
        if expire:
            pipe.expire(dest, 60)
        rx = pipe.execute()
        ret = rx[1]
        if op == BitmapCounter.OP_AVG:
            return float(ret) / len(timestamps)
        else:
            return ret

    def cohortAnalysis(self, timestamps, timeResolution, filterBitmapKey=None):
        """
        Given a list of timestamps, generates a list of retention measures of the first timestamp, for each later timestamp
        @param timestamps a tuple of timestamps to sample
        @param timeResolution time resolution to sample
        @param filterBitmapKey if set, we intersect it with each sample, to enable selective cohort
        @return a list of tuples [(timestamp,num),...]
        """

        #put the first timestamp as the first record in what we return
        ret = []
        conn = self._getConnection()
        #get the count for each timestamp
        for idx, ts in enumerate(timestamps):
            dest = 'cohort:%s:%s:%s' % (self.metric, ts, idx)
            bitmaps = [self.getKey(timestamps[0], timeResolution), self.getKey(ts, timeResolution)]

            #add filtering bitmap if needed
            if filterBitmapKey:
                bitmaps.append(filterBitmapKey)

            conn.bitop('AND', dest, *bitmaps)
            count = conn.bitcount(dest)

            ret.append((ts, count))
            conn.expire(dest, 60)


        return ret


    def funnelAnalysis(self, timestamps, timeResolution, filterBitmapKey=None):
        """
        Given a list of timestamps, return a funnel analysis - i.e. for each timestamp, an interesection of it and all the previous points
        @param timestamps a tuple of timestamps to sample
        @param timeResolution time resolution to sample
        @param filterBitmapKey if set, we intersect it with the first sample, to enable selective funnel
        @return a list of tuples [(timestamp,num),...]
        """
        conn = self._getConnection()

        prev = None
        ret = []
        #get the count for each timestamp
        for i in xrange(len(timestamps)):
            dest = 'funnel:%s:%s:%s' % (self.metric, timestamps[i], i)
            conn.bitop('AND', dest, prev or filterBitmapKey or self.getKey(timestamps[0], timeResolution),
                                 self.getKey(timestamps[i], timeResolution))

            count = conn.bitcount(dest)
            prev = dest
            logging.info("Funnel for timestamp %s: %s", timestamps[i], count)
            ret.append((timestamps[i], count))
            conn.expire(dest, 60)


        return ret



class IdMapper(Rediston):

    """
    This class creates a compact mapping between a non sequential object id to a sequential id
    Create a mapper an pass it to the bitmap counter if you want to convert big or textual ids to sequentials
    """


    def __init__(self, prefix):

        self.prefix = prefix
        self.idgen = IncrementalIdGenerator(namespace=self._redisKey())

    def _redisKey(self):

        return 'idmap:%s' % self.prefix

    def getSequentialId(self, objectId):
        """
        Convert a non sequential id to sequential id, by either creating a new mapping or retrieving an old one
        """

        conn = self._getConnection()
        rc = conn.hget(self._redisKey(), objectId)
        if rc:
            logging.info("Found id mapping for %s:%s: %s", self.prefix, objectId, rc)
            return rc
        else:
            id = self.idgen.getId()
            rc = conn.hsetnx(self._redisKey(), objectId, id)
            if rc: #the write was successful
                logging.info("Created new sequential id for %s:%s: %s", self.prefix, objectId, rc)
                return id
            else: #possible race condition
                logging.info("Got new sequential id for %s:%s: %s", self.prefix, objectId, rc)
                return conn.hget(self._redisKey(), objectId)








########NEW FILE########
__FILENAME__ = idgenerator
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.
from __future__ import absolute_import

__author__ = 'dvirsky'

from ..util import Rediston, InstanceCache
from threading import RLock
from collections import deque
import logging


class IncrementalIdGenerator(Rediston):
    """
    This class generates guaranteed unique incremental object ids, using redis, that can be pulled from many machines.
    To optimize performance, it doesn't need to request a new id from redis each time.
    Instead it reserves N ids in the clients, and hands them out until they run out.
    This is thread safe and can be used from multiple processes or machines
    """
    def __init__(self, namespace, maxReserveBuffer = 100):
        """
        @param namespace this is the namespace of the ids to be generated. each namespace is a single id generator
        @param maxReserveBuffer how many ids we want to reserve from redis. If you can't accept any "holes" in object
        ids in case of a process crash, set this to 1
        """
        self.namespace = namespace
        self.maxReserveBuffer = maxReserveBuffer
        self.reservedIdsCache = deque()
        self.__lock = RLock()

    @InstanceCache
    def __redisKey(self):
        """
        The redis key for the generator
        """
        return ':%s:idgen' % self.namespace

    def __reserveIds(self):
        """
        Call redis and reserve more ids
        """
        with self.__lock:
            conn = self._getConnection('master')
            res = conn.incr(self.__redisKey(), self.maxReserveBuffer)
            self.reservedIdsCache = deque((res - (self.maxReserveBuffer - i - 1) for i in xrange(self.maxReserveBuffer)))

            #logging.info("Reserved new ids: %s", list(self.reservedIdsCache))

    def getId(self):
        """
        Pop one id, request more from redis if there aren't any left in the cache
        """
        with self.__lock:
            try:
                return self.reservedIdsCache.popleft()
            except IndexError: #queue is empty
                self.__reserveIds()
                return self.reservedIdsCache.popleft()







########NEW FILE########
__FILENAME__ = lua
import redis
from redis.exceptions import RedisError
class LuaScriptError(RedisError):
    pass


class LuaCall(object):
    """
    A class that helps you treat lua functions like they were actual functions.
    Example:
    >>> lua_str = '''
                    local val = ARGV[1]*ARGV[2]
                    redis.call('set', KEYS[1], val)
                    return redis.call('get', KEYS[1])
                '''
    >>> mult = LuaCall(lua_str, myConnection) # also acceptable: mult = LuaCall(open('mult.lua'), myConnection)
    >>> print mult(keys = ('foo',), args = (3,10))
    30

    """
    def __init__(self, sourceOrFile, redisConn = None):
        """
        construct the functin
        @param sourceOrFile either a lua string, or a reference to a file in read mode containing the source
        @param redisConn a redis connection. if not given here, you'll have to give it on each call (useful for master/slave)
        """

        self.source = sourceOrFile if type(sourceOrFile) == str else sourceOrFile.read()
        self.conn = redisConn

        #if a connection was given - try to preload the function. if not - it will have to be given later
        if self.conn:
            self.__load()

    def __call__(self,  keys=(), args=(), conn = None):

        conn = conn or self.conn
        #try to execute
        try:
            return conn.evalsha(self.sha, len(keys), *(keys + args))
        except RedisError, e:
            #check for script doesn't exist error
            if e.message.startswith('NOSCRIPT'):

                #try and reload
                self.__load(conn)

                #one more time, with feeling!
                try:

                    return conn.evalsha(self.sha, len(keys), *(keys + args))
                except redis.RedisError, e:
                    raise LuaScriptError("Could not execute lua call: %s" % e.message)
            else:
                raise LuaScriptError(e)


    def __load(self, conn = None):
        """
        Silently preload the function to redis to be used in the future
        """
        conn = conn or self.conn
        self.sha = conn.script_load(self.source)

    def isCached(self, conn = None):
        """
        Check if our function exists
        """
        conn = conn or self.conn
        return conn.script_exists(self.sha)






########NEW FILE########
__FILENAME__ = condition
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

__author__ = 'dvirsky'

class Condition(object):

    """
    This class represents a condition to fetch objects
    conditions are constructed with a dictionary of field values or ranges, and paging offsets
    """
    class ConditionType(object):
        def __repr__(self):

            return '%s (%s)' % (self.__class__.__name__, self.__dict__)
    """Condition types"""
    class Is(ConditionType):
        """
        Just like ==
        """
        def __init__(self, value):
            self.value = value

    class In(ConditionType):
        """
        Valus is in a multiple option
        """
        def __init__(self, *values):
            raise NotImplementedError("Not implemented yet in any key")
            self.values = values

    class Between(ConditionType):
        """
        Range condition
        """
        def __init__(self, min, max):
            self.min = min
            self.max = max

    def __init__(self, fieldsAndValues, paging = None):
        """
        @param fieldsAndValues a dictionary of fields and their requested values
        @param paging a tuple of (offset, num) to get
        """

        self.fieldsAndValues = fieldsAndValues
        self.paging = paging

    def getValuesFor(self, *fields):

        return [self.fieldsAndValues[f] for f in fields]

    def __repr__(self):

        return 'Condition(%s, paging: %s)' % (self.fieldsAndValues, self.paging)
########NEW FILE########
__FILENAME__ = indexing
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.
from __future__ import absolute_import

import string

import codecs
import re
from ...util import Rediston, InstanceCache
from .condition import Condition
import pyhash
import logging


class AbstractKey(object):

    def __init__(self, prefix,fields):

        self.prefix = prefix
        self.fields = fields
        self.fieldSet = set(fields)


    def update(self, obj, pipeline = None):
        pass

    def updateMany(self, idsAndKeyValues = ()):
        pass

    def __repr__(self):

        return '%s(%s:%s)' % (self.__class__.__name__, self.prefix, ','.join(self.fields))


class FullTextKey(AbstractKey, Rediston):
    '''
    classdocs
    '''
    
    trantab = string.maketrans("-_'", "   ")
    stopchars = "\"'\\`'[]{}(),./?:)(*&^%$#@!="

    def __init__(self, prefix, alias, fields, objectScoringCallback = None, delimiter = ' '):
        '''
        Constructor
        '''

        AbstractKey.__init__(self, prefix, fields = [alias,])
        Rediston.__init__(self)
        self.fieldSpec = fields #we don't use the key's "fields" to be able to query multiple fields at once
        self.delimiter = delimiter
        self.scoringCallback = objectScoringCallback

    def getKey(self, word):
        
        return 'ft:%s:%s' % (self.prefix, word)
    
        
    def normalizeString(self, str_):
        
        str_ = codecs.encode(str_, 'utf-8')
        
        return str_.translate(self.trantab, self.stopchars)
        
        
    def update(self, obj, pipeline = None):

        score = 1.0

        #if the object suppports scoring, call the callback now
        if self.scoringCallback:
            score = self.scoringCallback(obj)

        pipe = pipeline or self._getPipeline(transaction=False)
        indexKeys = {}
        #split the words
        for field, factor in self.fieldSpec.iteritems():

            for token in re.split(self.delimiter, getattr(obj, field, '')):
                
                t = self.normalizeString(token.lower().strip())
                
                if t:
                    indexKeys[t]= indexKeys.get(t, 0) + float(factor)*score

        for x in indexKeys:

            pipe.zadd(self.getKey(x), obj.id, indexKeys[x])

        if not pipeline:
            pipe.execute()
            
        
    def find(self, condition):


        string = condition.getValuesFor(self.fields[0])[0]

        tokens = filter(None, (self.normalizeString(value.lower().strip()) for value in re.split(self.delimiter, string)))
        
        
        if not tokens:
            return []
        keys = [self.getKey(t) for t in tokens]
        
        destKey = ('tk:%s' % '|'.join(tokens))
        pipe = self._getPipeline(transaction=False)
        pipe.zinterstore(destKey, keys, 'SUM')
        pipe.zrevrange(destKey, 0, -1, False)
        rx = pipe.execute()
        return rx[1]




class UnorderedKey(AbstractKey, Rediston):
    """
    A simple catch all key, non unique, ideal for short texts (emails, etc). case sensitive.
    it uses hashing of the value as a score in a sorted set
    """
    def __init__(self, prefix, fields):
        '''
        Constructor
        '''
        AbstractKey.__init__(self, prefix, fields)
        Rediston.__init__(self)
        self.hasher = pyhash.fnv1a_64()


    def getValue(self, _dict):


        vals = '::'.join(('%s' % _dict[f] for f in self.fields))

        #make a hash val that is 52 bits and can fit as a sorted set score
        hashval = self.hasher(vals) & 0b11111111111111111111111111111111111111111111111111111

        logging.info("Vals for key %s: %s. hashval: %s", self, vals, hashval)

        return hashval

    @InstanceCache
    def redisKey(self):

        return 'k:%s:%s' % (self.prefix, ','.join(self.fields))

    def update(self, obj, pipeline = None):
        """
        Update the key with the value of this object
        """

        hashval = self.getValue(obj.__dict__)
        conn = pipeline or self._getConnection('master')
        conn.zadd(self.redisKey(), **{str(obj.id): hashval})



    def updateMany(self, ids, cls):

        #first, get the values for these ids
        objs = cls.loadObjects(ids, *self.fields)

        #build a dictionary of all the values to be updated
        updateDict = {}
        for obj in objs:
            if obj:
                updateDict[obj.id] = self.getValue(obj.__dict__)

        conn = self._getConnection('master')
        conn.zadd(self.redisKey(), **updateDict)


    def find(self, condition):
        """
        find objects matching  a certian condition
        currently the condition has to be exactly field=value. no multiple options and no ranges allowed
        """
        hashval = self.getValue(condition.fieldsAndValues)
        conn = self._getConnection()
        return conn.zrangebyscore(self.redisKey(), min=hashval,max=hashval,
                                    start = 0 if not condition.paging else condition.paging[0],
                                    num = -1 if not condition.paging else condition.paging[0] + condition.paging[1] )



class OrderedNumericalKey(AbstractKey, Rediston):
    """
    A key for numerical fields (ints or floats) that can sort and page results
    """
    def __init__(self, prefix, field):
        '''
        Constructor
        '''
        AbstractKey.__init__(self, prefix, (field,))
        Rediston.__init__(self)
        self.field = field


    def getValue(self, _dict):

        return float(_dict[self.field])

    @InstanceCache
    def redisKey(self):

        return 'ok:%s:%s' % (self.prefix, ','.join(self.fields))

    def update(self, obj, pipeline = None):
        """
        Update the key with the value of this object
        """
        val = self.getValue(obj.__dict__)
        conn = pipeline or self._getConnection('master')
        conn.zadd(self.redisKey(), **{str(obj.id): val})



    def updateMany(self, ids, cls):

        #first, get the values for these ids
        objs = cls.loadObjects(ids, self.field)

        #build a dictionary of all the values to be updated
        updateDict = {}
        for obj in objs:
            if obj:
                updateDict[obj.id] = self.getValue(obj.__dict__)

        conn = self._getConnection('master')
        conn.zadd(self.redisKey(), **updateDict)


    def find(self, condition):
        """
        find objects matching  a certian condition
        currently the condition has to be exactly field=value. no multiple options and no ranges allowed
        """

        _min = None
        _max = None
        conditionValue = condition.getValuesFor(self.field)[0]
        #if this is a range query, get the min/max of the query
        if isinstance(conditionValue, Condition.Between):
            _min = float(conditionValue.min)
            _max = float(conditionValue.max)
        elif isinstance(conditionValue, Condition.ConditionType):
            _min = _max = float(conditionValue.value)
        else:
            _min = _max = float(conditionValue)

        conn = self._getConnection()
        return conn.zrangebyscore(self.redisKey(), min=_min,max=_max,
            start = 0 if not condition.paging else condition.paging[0],
            num = -1 if not condition.paging else condition.paging[0] + condition.paging[1] )



class UniqueKeyDuplicateError(Exception):

    pass



class UniqueKey(AbstractKey, Rediston):
    """
    Unique value key, for strings or numbers
    It uses a HASH of value=>objectId to make sure no two objects have the same value
    it raises UniqueKeyDuplicateError if you hit a duplicate value
    """
    def __init__(self, prefix, fields):
        '''
        Constructor
        '''
        AbstractKey.__init__(self, prefix, fields)
        Rediston.__init__(self)


    def getValue(self, _dict):


        return '::'.join(('%s' % _dict[f] for f in self.fields))

    @InstanceCache
    def redisKey(self):

        return 'uk:%s:%s' % (self.prefix, ','.join(self.fields))


    def update(self, obj, pipeline = None):
        """
        Update the key with the value of this object
        """

        val = self.getValue(obj.__dict__)
        pipe = self._getPipeline('master')

        #we set and check the value at once, in case the key is already taken we need to check the current object...
        pipe.hsetnx(self.redisKey(), val, obj.id)
        pipe.hget(self.redisKey(), val)

        rx = pipe.execute()
        #this means
        if rx[0] == 0:
            currentObjId= rx[1]
            logging.info("Possible unique key collision, checking... object: %s, current in key: %s", obj.id, currentObjId)

            if currentObjId != '%s' % obj.id:
                logging.warn("Unique Key collision. wanted to set %s but key already has %s", obj, currentObjId)
                raise UniqueKeyDuplicateError("Duplicate error for key %s" % self)
            else:
                logging.info("Unique key set to the same object")
        else:
            logging.info("Unique key %s set new value for %s:%s", self, obj.id, val)

    def updateMany(self, ids, cls):

        #first, get the values for these ids
        objs = cls.loadObjects(ids, *self.fields)

        #build a dictionary of all the values to be updated
        updateDict = {}
        for obj in objs:
            if obj:
                self.update(obj)




    def find(self, condition):
        """
        find objects matching  a certian condition
        currently the condition has to be exactly field=value. no multiple options and no ranges allowed
        """
        val = self.getValue(condition.fieldsAndValues)
        conn = self._getConnection()
        id = conn.hget(self.redisKey(), val)
        return [id] if id is not None else []


########NEW FILE########
__FILENAME__ = objects
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

from __future__ import absolute_import
__author__ = 'dvirsky'

import logging
from ...util import  InstanceCache, Rediston
from ..idgenerator import IncrementalIdGenerator


class KeySpec(object):
    """
    Object key descriptor
    """

    def __init__(self, *keys):
        """
        @param keys all the keys to be included in this spec
        """
        self._keys = list(keys)


    def getKey(self, condition):
        """
        Get the proper key for a query
        TODO: Support multiple keys for a single query to be crossed
        @param condition a condition object
        """
        queryKeys = set(condition.fieldsAndValues.iterkeys())
        logging.info("Query keys: %s", queryKeys)

        for key in self._keys:

            if queryKeys == key.fieldSet:
                logging.info("Found key for condition: %s", key)
                return key

        raise ValueError("Could not find key for condition %s", condition)


    def keys(self):
        return self._keys

    @InstanceCache
    def findKeysForUpdate(self, fields):

        fields = set(fields)
        return [key for key  in self._keys if key.fieldSet.intersection(fields)]




class IndexedObject(Rediston):


    #This is the specification of which fields you want to index. override in child classes
    _keySpec = KeySpec()

    #this is the specification of which fields should be saved to redis
    _spec = ('id',)

    #the id generator for the class. by default it is initialized to an incremental id generator
    #you can replace it with another id generator if you want
    _idGenerator = None


    def __init__(self, **kwargs):
        """
        default constructor, override in subclasses to force strict field typing
        """
        self.id = kwargs.get('id', None)
        self.__dict__.update(kwargs)

        #create id generator the first time needed. this can be overriden in child classes
        if not self.__class__._idGenerator:
            self.__class__._idGenerator = IncrementalIdGenerator(self.__name())


    @classmethod
    def createNew(cls, *args, **kwargs):
        """
        Create a new object and save it immeditely
        """
        obj = cls(*args, **kwargs)
        obj.save()
        return obj

    @classmethod
    def __name(cls):
        """
        the object's name for saving
        """
        if not hasattr(cls, '_oredis_name'):
            setattr(cls, '_oredis_name', cls.__name__.lower())

        return cls._oredis_name

    @classmethod
    def __createId(cls):
        """
       create a new id for an object
        """

        return cls._idGenerator.getId()


    @classmethod
    def __key(cls, id):
        """
        Get the actual id of an object based on a given id
        """
        return '%s:%s' % (cls.__name(), id)

    @classmethod
    def config(cls, host, port, db, timeout = None):

        for k in cls._keySpec.keys():
            k.__class__.config(host, port, db, timeout)

        cls._host = host
        cls._port = port
        cls._db = db
        cls._timeout = timeout


        cls.__connPool = None

    @classmethod
    def loadObjects(cls, ids, *fields):
        """
        Load a list of objects by ids
        @param ids a list of object ids (not keys)
        @param fields optional list of fields to pass if you do not want ALL the object
        """

        p = cls._getPipeline()

        if not fields:

            [p.hgetall(cls.__key(id)) for id in ids]
        else:
            #we get the id anyway,no point in getting it from redis
            if 'id' in fields:
                fields.remove('id')
            [p.hmget(cls.__key(id), fields) for id in ids]

        ret = p.execute()

        objs = []
        for idx,r in enumerate(ret):
            if r:
                r['id'] = ids[idx]
                obj = cls( **r)
                objs.append(obj)
        return objs


    def __repr__(self):

        return '%s(%s)' % (self.__class__.__name__, self.__dict__)

    @classmethod
    def getAll(cls, first = 0, num = -1, *fields):
        """
        Get all the objects of a given type, with optional paging
        """
        redisConn = self._getConnection()
        ids = redisConn.zrange(cls.__classKey(), first, num)
        return cls.loadObjects(ids, redisConn, *fields)




    def __index(self, pipeline = None):
        """
        update the object's indexes
        """

        if not self._keySpec:
            return

        p = pipeline or self._getPipeline('master', transaction=False)
        for k in self._keySpec.keys():

            k.update(self, p)
        if not pipeline:
            p.execute()

    @classmethod
    def __classKey(cls):
        """
        Get the master key of all the available ids in the class
        """
        return 'ids:%s' % cls.__name()

    def __getId(self):
        """
        Get the object's id or create a new one if needed
        """


        if self.id is None:
            self.id = self.__createId()
        return self.id

    def save(self):

        #redisConn = self._getConnection('master')
        _id = self.__getId()

        saveDict = {k: getattr(self, k, None) for k in self._spec}

        pipe =self._getPipeline('master', True)
        #save all properties
        pipe.hmset(self.__key(_id), saveDict )
        #add the id to the master object list
        pipe.zadd(self.__classKey(), **{str(_id): float(_id)})

        #index all the relevant keys
        self.__index(pipe)
        pipe.execute()




    def update(self, **keyValues):
        """
        Set a field(s) in the object and save it to the database
        @param keyValues free form x=y kwargs
        """

        if not self.id:
            raise ValueError("Cannot update a value for an unsaved object")

        #set the data in redis
        ret = self._getConnection('master').hmset(self.__key(self.id), keyValues )

        #update the keys
        updateAbleKeys = self._keySpec.findKeysForUpdate(keyValues.iterkeys())
        for k in updateAbleKeys:
            k.update(self, keyValues)

        #set the data in the object (after successful redis update, to avoid invalid objects)
        for k, v in keyValues.iteritems():
            setattr(self, k, v)

        return ret


    @classmethod
    def incrementWhere(cls, condition, fieldName, amount):
        """
        Increment a field by an amount, updating the database
        @return a list of updated ids and the new value afterupdate of the field
        """

        ids = cls.find(condition)
        pipe = cls._getPipeline('master')
        for id in ids:
            pipe.hincrby(cls.__key(id), fieldName, amount)

        #execute the pipe and get the new values
        newVals = pipe.execute()

        #udpate the keys
        updateAbleKeys = cls._keySpec.findKeysForUpdate((fieldName,))
        for key in updateAbleKeys:
            key.updateMany(((id, newVals[idx]) for idx, id in enumerate(ids)))


        return [(id, newVals[idx]) for idx, id in enumerate(ids)]

    @classmethod
    def updateWhere(condition, **keyValues):
        """
        Update fields with new values for objects matching a condition
        """
        ids = cls.find(condition)
        pipe = self._getPipeline('master')
        #update the database
        for id in ids:
            pipe.hmset(cls.__key(id), keyValues)

        #execute the pipe and get the new values
        res = pipe.execute()

        #udpate the keys
        updateAbleKeys = self.__keySpec.findKeysForUpdate(keyValues.iterkeys())
        for key in updateAbleKeys:
            key.updateMany(((id, keyValues) for ids in ids))

        return ids

    @classmethod
    def get(cls, condition, *fields):
        """
        Load a class by a named key indexing some if its fields
        value can by a multiple token string
        """

        ids = cls.find(condition)

        return cls.loadObjects(ids, *fields )

    @classmethod
    def find(cls, condition):
        """
        Find object ids for a given condition
        """

        key = cls._keySpec.getKey(condition)

        ids = key.find(condition)

        logging.debug("Ids for %s: %s", condition, ids)
        return ids
########NEW FILE########
__FILENAME__ = redis_unit
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

__author__ = 'dvirsky'


import redis
import sys
import contextlib
import re

class RedisAssertionError(Exception):

    def __init__(self, msg, *args):

        if args:
            msg = msg % args
        Exception.__init__(self, msg)




class RedisDataTest(object):
    """
    This class has a unittest like API that enables testing redis databases for consistency and automatic assertions about data
    It can either be used by calling these functions, or by inheriting it, implementing tests in fucntions starting with \
    "test", and then calling run() on the test instance.
    Assertion failures raise the RedisAssertionError exception
    """

    T_STRING = 'string'
    T_HASH = 'hash'
    T_ZSET = 'zset'
    T_LIST = 'list'
    T_SET = 'set'

    ############################################################################################
    ## Static methods below are used to validate values of keys by applying lambdas on them
    # Example: test.assertKeyValue('foo', RedisDataTest.greaterThan(0)) => asserts that the value in 'foo' > 0
    @staticmethod
    def equals(y):
        return lambda x: x == y
    @staticmethod
    def greaterThan(y):
        return lambda x: float(x) > y

    @staticmethod
    def greaterThanOrEqual(y):
        return lambda x: x >= y

    @staticmethod
    def lessThan(y):
        return lambda x: x < y

    @staticmethod
    def lessThanOrEqual(y):
        return lambda x: x <= y
    @staticmethod
    def matches(exp):
        return lambda x: bool(re.match(exp, x))

    @staticmethod
    def isNumeric(x):
        try:
            float(x)
            return True
        except ValueError:
            return False

    #End of validation lambdas
    #########################################


    def __init__(self, host = 'localhost', port = 6379, db = 0, timeout = None, verbose = True):
        """
        @param verbose whether we want to output messages or not
        """
        self.redis = redis.Redis(host, port, db, timeout)
        self.verbose = verbose

    @contextlib.contextmanager
    def _message(self, msg, *args):
        """
        Wrapping tests with messages and [PASS] stamps
        """
        if self.verbose:
            if args:
                msg = msg % args
            sys.stderr.write(msg + '...')
        yield

        if self.verbose:
            sys.stderr.write('\t[PASS]\n')


    def assertKeysExists(self, *keys):
        """
        Assert that a key(s) exists in redis
        """

        with self._message("Asserting the existence of %s (%d keys)...", keys[:5], len(keys)):
            p = self.redis.pipeline()
            [p.exists(k) for k in keys]
            for idx, exists in enumerate(p.execute()):
                if not exists:
                    raise RedisAssertionError("Key %s does not exist" % keys[idx])


    def assertKeysType(self,  ktype, *keys):
        """
        Assert that a bunch of keys all belong to a type
        @param ktype a string representing the type, use the T_* static constants, e.g RedisDataTest.T_STRING
        """

        with self._message("Testing if '%s (%d keys)' is of type %s", keys[:5], len(keys), ktype):
            p = self.redis.pipeline()
            [p.type(k) for k in keys]
            for idx, t in enumerate(p.execute()):
                if not t==ktype:
                    raise RedisAssertionError("Key %s is of type %s - expected %s" % (keys[idx], t, ktype))

    def countPrefix(self, prefix):
        """
        Return the number of keys in a prefix
        @warning: DO NOT USE IN PRODUCTION DATABASES!
        """
        keys = self.redis.keys(prefix)
        return len(keys)


    def assertPrefixCount(self, prefix, minAmount, maxAmount = None):
        """
        Check that a prefix does not appear more than maxAmount times and no less of minAmount times
        @param prefix - the prefix to be tested
        @warning: DO NOT USE IN PRODUCTION DATABASES!
        """
        with self._message("Assering that keys with prefix '%s' are between %s and %s", prefix, minAmount, maxAmount or 'infinity'):
            num = self.countPrefix(prefix)
            if num < minAmount:
                raise RedisAssertionError("Expected at least %d elements for '%s', got %d", minAmount, prefix, num)
            elif maxAmount is not None and num > maxAmount:
                raise RedisAssertionError("Expected at most %d elements for '%s', got %d", maxAmount, prefix, num)


    def assertListSize(self, key, min, max = None):
        """
        Assert the size of a LIST is between min and max. if max is none only min applies
        """
        self.__assertLen(key, 'llen', min, max = None)

    def assertHashLen(self, key, min, max = None):
        """
        Assert the size of a HASH is between min and max. if max is none only min applies
        """
        self.__assertLen(key, 'hlen', min, max = None)

    def assertSetCardinality(self, key, min,max = None):
        """
        Assert the size of a set is between min and max. if max is none only min applies
        """
        self.__assertLen(key, 'scard', min, max)

    def assertSortedSetSize(self, key, min, max = None):
        """
        Assert the size of a sorted set is between min and max. if max is none only min applies
        """
        self.__assertLen(key, 'zcard', min, max)

    def assertStringLength(self, key, min, max = None):

        self.__assertLen(key, 'strlen', min, max = None)

    def __assertLen(self, key, command, min, max):
        """
        Internal function. Assert the size of a an element is between min and max. if max is none only min applies
        """
        with self._message('Checking length of %s, between %s and %s', key, min, max or 'infinity'):
            num = self.redis.execute_command(command, key)
            if num < min:
                raise RedisAssertionError("Expected at least %d elements for '%s', got %d", min, key, num)
            elif max is not None and num > max:
                raise RedisAssertionError("Expected at most %d elements for '%s', got %d", min, key, num)


    def assertHashKeysExist(self, key, *fields):
        """
        Assert that several sub-keys exist in a hash
        """
        with self._message("Checking if keys %s exist in hash %s", fields, key):

            hkeys = set(self.redis.hkeys(key))
            nonExistentKeys = [k for k in fields if k not in hkeys]
            if nonExistentKeys:
                raise RedisAssertionError("Keys '%s' of hash %s do not exist!", nonExistentKeys, key)

    def assertKeyValue(self, key, expectedValueOrCallback):
        """
        Make an assertion about the value of a certain key.
        @param expectedValueOrCallback if set to a non callable object - we just compare it. else - we run the callback
        use the static lambda returning callbacks in the beginning of this module here
        """
        with self._message("Checking value for %s", key):
            val = self.redis.get(key)

            if callable(expectedValueOrCallback):
                rc = expectedValueOrCallback(val)
            else:

                rc = val == expectedValueOrCallback
            if not rc:
                raise RedisAssertionError("Value test failed on %s. got value %s", key,  val)

    def assertHashValue(self, key, hkey, valueTestCAllback = lambda x: x is not None, testDescription = None):
        """
        Make an assertion about the value inside a sub-key of a HASH
        @param key the HASH
        @param hkey the HASH sub key
        @param valueTestCAllback a function that makes an assertion about the value. by default we check that it's not null
        """
        with self._message("Checking value for %s in hash %s", hkey, key):
            val = self.redis.hget(key, hkey)
            if not valueTestCAllback(val):
                raise RedisAssertionError("Hash Value test %s failed on %s/%s. got value %s", testDescription or '', key, hkey, val)


    def assertValueInSortedSet(self, key, value, assertRank = None, revrank = False):
        """
        Check if a value is inside a sorted set
        @param key the sorted set's key
        @param value the value inside the sorted set
        @param assertRank if set to a number, we check that the rank of the value is identical to this
        @param revrank if set to True, we use ZREVRANK to assert the rank
        """
        with self._message("Checking value %s in sorted set %s", value, key):


            rank = (self.redis.zrank if not revrank else self.redis.zrevrank)(key, value)
            if rank is None:
                raise RedisAssertionError("value %s is not in sorted set %s", value, key)

            if assertRank is not None and assertRank != rank:
                raise RedisAssertionError("value %s in sorted set %s has rank of %s, expected %s", value, key, rank, assertRank)


    def run(self):

        """
        Run all functions that start with test*
        """

        for memberName, member in self.__class__.__dict__.iteritems():

            if memberName.startswith('test') and callable(member):

                getattr(self, memberName)()


if __name__ == '__main__':

    class MyTest(RedisDataTest):

        def testMe(self):

            self.assertKeysExists('foo')


    t = MyTest()
    t.run()
########NEW FILE########
__FILENAME__ = util
#Copyright 2012 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

"""
Various Util functinos
"""
__author__ = 'dvirsky'

import redis

'''
Generic singleton wrapper
Created on Sep 21, 2011

@author: dvirsky
'''

import redis


class Rediston(object):
    """
    This is a base class that holds a connection pool and redis connection instances
    """

    __connPool = None

    _host = 'localhost'
    _port = 6379
    _db = 0
    _timeout = None

    @classmethod
    def _getConnection(cls, mode = 'master'):

        if not hasattr(cls, 'redis'):
            cls.redis = None

        if not cls.__connPool:
            cls.__connPool = redis.ConnectionPool(host = cls._host,
                port = cls._port,
                db = cls._db,
                socket_timeout = cls._timeout,
            )

        if not cls.redis:
            cls.redis = redis.Redis(connection_pool = cls.__connPool)

        return cls.redis

    @classmethod
    def _getPipeline(cls,  mode = 'master', transaction = False):
        """
        Create a pipeline object
        @TODO: support master/slave
        """
        conn = cls._getConnection(mode=mode)
        return conn.pipeline(transaction=transaction)



    @classmethod
    def config(cls, host, port, db, timeout = None):

        cls._host = host
        cls._port = port
        cls._db = db
        cls._timeout = timeout


        cls.__connPool = None


    def resetPool(self):
        """
        hard reconnect to avoid forked sockets etc
        """
        self.__class__.__connPool = None
        self.redis = None
        self.__connect()


    def flush(self):

        if getattr(self, 'pipeline', None):
            self.pipeline.execute()



import uuid, base64, struct
def generateRandomId():
    """
    Returns a short, random (see UUID4 RFC), unique id
    """

    i = uuid.uuid4().int
    return base64.b64encode(struct.pack('q', ((i >> 64) ^ i) & 0x7fffffffffffffff) , '-_').strip('=')


def InstanceCache(method):
    """
    Use this to wrap instance methods that return a value that doesn't change after the first calculation
    """

    def wrapped(*args, **kwargs):

        _hash = hash((args[1:], tuple(sorted(kwargs.items()))))
        _self = args[0]
        k = '__MethodCache__%s_%x' % (method.__name__, _hash)

        if hasattr(_self, k):
            return getattr(_self, k)

        ret = method(*args, **kwargs)
        setattr(_self, k, ret)
        return ret

    return wrapped

from contextlib import contextmanager
import time
import sys

@contextmanager
def TimeSampler(actionDescription, callback = None, minTimeFilterMS = 0):

    st = time.time()
    yield
    et = time.time()
    duration =  1000*(et - st)
    if duration < minTimeFilterMS:
        return

    msg = 'Action %s took %.03fms' % (actionDescription, duration)

    if callback:
        callback(msg)
    else:
        sys.stderr.write(msg)

########NEW FILE########
