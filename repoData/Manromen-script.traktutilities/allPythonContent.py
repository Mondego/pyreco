__FILENAME__ = default
# -*- coding: utf-8 -*-
# 

import os
import xbmcgui,xbmcaddon,xbmc
from utilities import *
from sync_update import *
from watchlist import *
from recommend import *
from friends import *
from trending import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

#read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

Debug("default: " + __settings__.getAddonInfo("id") + " - version: " + __settings__.getAddonInfo("version"))

# Usermenu:
def menu():

    # check if needed settings are set
    if checkSettings() == False:
        return

    options = [__language__(1210).encode( "utf-8", "ignore" ), __language__(1211).encode( "utf-8", "ignore" ), __language__(1212).encode( "utf-8", "ignore" ), __language__(1213).encode( "utf-8", "ignore" ), __language__(1214).encode( "utf-8", "ignore" )]
    
    while True:
        select = xbmcgui.Dialog().select("Trakt Utilities", options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        else:
            if select == 0: # Watchlist
                submenuWatchlist()
            elif select == 1: # Friends
                showFriends()
            elif select == 2: # Recommendations
                submenuRecommendations()
            elif select == 3: # Trending Movies / TV Shows
                submenuTrendingMoviesTVShows()
            elif select == 4: # Update / Sync / Clean
                submenuUpdateSyncClean()


def submenuUpdateSyncClean():

    options = [__language__(1217).encode( "utf-8", "ignore" ), __language__(1218).encode( "utf-8", "ignore" ), __language__(1219).encode( "utf-8", "ignore" ), __language__(1220).encode( "utf-8", "ignore" ), __language__(1221).encode( "utf-8", "ignore" ), __language__(1222).encode( "utf-8", "ignore" )]
    
    while True:
        select = xbmcgui.Dialog().select("Trakt Utilities", options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        elif select == 0: # Update Movie Collection
            updateMovieCollection()
        elif select == 1: # Sync seen Movies
            syncSeenMovies()
        elif select == 2: # Update TV Show Collection
            updateTVShowCollection()
        elif select == 3: # Sync seen TV Shows
            syncSeenTVShows()
        elif select == 4: # Clean Movie Collection
            cleanMovieCollection()
        elif select == 5: # Clean TV Show Collection
            cleanTVShowCollection()

def submenuTrendingMoviesTVShows():

    options = [__language__(1250).encode( "utf-8", "ignore" ), __language__(1251).encode( "utf-8", "ignore" )]
    
    while True:
        select = xbmcgui.Dialog().select(__language__(1213).encode( "utf-8", "ignore" ), options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        if select == 0: # Trending Movies
            showTrendingMovies()
        elif select == 1: # Trending TV Shows
            showTrendingTVShows()

def submenuWatchlist():

    options = [__language__(1252).encode( "utf-8", "ignore" ), __language__(1253).encode( "utf-8", "ignore" )]
    
    while True:
        select = xbmcgui.Dialog().select(__language__(1210).encode( "utf-8", "ignore" ), options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        if select == 0: # Watchlist Movies
            showWatchlistMovies()
        elif select == 1: # Watchlist TV Shows
            showWatchlistTVShows()

def submenuRecommendations():
    
    options = [__language__(1255).encode( "utf-8", "ignore" ), __language__(1256).encode( "utf-8", "ignore" )]
    
    while True:
        select = xbmcgui.Dialog().select(__language__(1212).encode( "utf-8", "ignore" ), options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        if select == 0: # Watchlist Movies
            showRecommendedMovies()
        elif select == 1: # Watchlist TV Shows
            showRecommendedTVShows()

menu()

########NEW FILE########
__FILENAME__ = friends
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
from utilities import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )
https = __settings__.getSetting( "https" )

if (https == 'true'):
    conn = httplib.HTTPSConnection('api.trakt.tv')
else:
    conn = httplib.HTTPConnection('api.trakt.tv')

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def showFriends():

    options = []
    data = getFriendsFromTrakt()
    
    if data == None: # data = None => there was an error
        return # error already displayed in utilities.py
    
    for friend in data:
        try:
            if friend['full_name'] != None:
                options.append(friend['full_name']+" ("+friend['username']+")")
            else:
                options.append(friend['username'])
        except KeyError:
            pass # Error ? skip this movie
    
    if len(options) == 0:
        xbmcgui.Dialog().ok("Trakt Utilities", "you have not added any friends on Trakt")
        return
    
    while True:
        select = xbmcgui.Dialog().select(__language__(1211).encode( "utf-8", "ignore" ), options) # Friends
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        showFriendSubmenu(data[select])
 
def showFriendSubmenu(user):
    #check what (if anything) the user is watching
    watchdata = getWatchingFromTraktForUser(user['username'])
    currentitem = "Nothing"
    if len(watchdata) != 0:
        if watchdata['type'] == "movie":
            currentitem = watchdata['movie']['title']+" ["+str(watchdata['movie']['year'])+"]"
        elif watchdata['type'] == "episode":
            currentitem = watchdata['show']['title']+" "+str(watchdata['episode']['season'])+"x"+str(watchdata['episode']['number'])+" - "+watchdata['episode']['title']
    
    options = [(__language__(1280)+": "+currentitem).encode( "utf-8", "ignore" ), __language__(1281).encode( "utf-8", "ignore" ), __language__(1282).encode( "utf-8", "ignore" ), __language__(1283).encode( "utf-8", "ignore" ), __language__(1284).encode( "utf-8", "ignore" )]
    while True:
        select = xbmcgui.Dialog().select((__language__(1211)+" - "+user['username']).encode( "utf-8", "ignore" ), options)
        Debug("Select: " + str(select))
        if select == -1:
            Debug ("menu quit by user")
            return
        else:
            if select == 0: # Select (friends) currenty playing
                xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")
            elif select == 1: # Friends watchlist
                showFriendsWatchlist(user)
            elif select == 2: # Friends watched
                showFriendsWatched(user)
            elif select == 3: # Friends library
                showFriendsLibrary(user)
            elif select == 4: # Friends profile
                showFriendsProfile(user)

def showFriendsWatchlist(user):
    xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")

def showFriendsWatched(user):
    xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")

def showFriendsLibrary(user):
    xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")

def showFriendsProfile(user):
    xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")
########NEW FILE########
__FILENAME__ = instant_sync
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
import telnetlib, time

try: import simplejson as json
except ImportError: import json

import threading
from utilities import *
from instant_sync import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

# Move this to its own file
def instantSyncPlayCount(data):
    if data['params']['data']['item']['type'] == 'episode':
        info = getEpisodeDetailsFromXbmc(data['params']['data']['item']['id'], ['tvshowid','showtitle', 'season', 'episode'])
        rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails','params':{'tvshowid': info['tvshowid'], 'properties': ['imdbnumber']}, 'id': 1})
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
        Debug("[Instant-sync] (TheTVDB ID: )"+str(result))
        if info == None: return
        Debug("[Instant-sync] (episode playcount): "+str(info))
        if data['params']['data']['playcount'] == 0:
            res = setEpisodesUnseenOnTrakt(result['result']['tvshowdetails']['imdbnumber'], info['showtitle'], None, [{'season':info['season'], 'episode':info['episode']}])
        elif data['params']['data']['playcount'] == 1:
            res = setEpisodesSeenOnTrakt(result['result']['tvshowdetails']['imdbnumber'], info['showtitle'], None, [{'season':info['season'], 'episode':info['episode']}])
        else:
            return
        Debug("[Instant-sync] (episode playcount): responce "+str(res))
    if data['params']['data']['item']['type'] == 'movie':
        info = getMovieDetailsFromXbmc(data['params']['data']['item']['id'], ['imdbnumber', 'title', 'year', 'playcount', 'lastplayed'])
        if info == None: return
        Debug("[Instant-sync] (movie playcount): "+str(info))
        if 'lastplayed' not in info: info['lastplayed'] = None
        if data['params']['data']['playcount'] == 0:
            res = setMoviesUnseenOnTrakt([{'imdb_id':info['imdbnumber'], 'title':info['title'], 'year':info['year'], 'plays':data['params']['data']['playcount'], 'last_played':info['lastplayed']}])
        elif data['params']['data']['playcount'] == 1:
            res = setMoviesSeenOnTrakt([{'imdb_id':info['imdbnumber'], 'title':info['title'], 'year':info['year'], 'plays':data['params']['data']['playcount'], 'last_played':info['lastplayed']}])
        else:
            return
        Debug("[Instant-sync] (movie playcount): responce "+str(res))
########NEW FILE########
__FILENAME__ = nbhttpconnection
# -*- coding: utf-8 -*-
# 

import os, sys
import time, socket
import urllib
import thread
import threading

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# Allows non-blocking http requests
class NBHTTPConnection():    
    def __init__(self, host, port = None, strict = None, timeout = None):
        self.rawConnection = httplib.HTTPConnection(host, port, strict, timeout)
        self.responce = None
        self.responceLock = threading.Lock()
        self.closing = False
    
    def request(self, method, url, body = None, headers = {}):
        self.rawConnection.request(method, url, body, headers);
    
    def hasResult(self):
        if self.responceLock.acquire(False):
            self.responceLock.release()
            return True
        else:
            return False
        
    def getResult(self):
        while not self.hasResult() and not self.closing:
            time.sleep(1)
        return self.responce
    
    def go(self):
        self.responceLock.acquire()
        thread.start_new_thread ( NBHTTPConnection._run, ( self, ) )
        
    def _run(self):
        self.responce = self.rawConnection.getresponse()
        self.responceLock.release()
        
    def close(self):
        self.closing = True
        self.rawConnection.close()
    
########NEW FILE########
__FILENAME__ = nbhttpsconnection
# -*- coding: utf-8 -*-
# 

import os, sys
import time, socket
import urllib
import thread
import threading

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# Allows non-blocking http requests
class NBHTTPSConnection():    
    def __init__(self, host, port = None, strict = None, timeout = None):
        self.rawConnection = httplib.HTTPSConnection(host, port, strict, timeout)
        self.responce = None
        self.responceLock = threading.Lock()
        self.closing = False
    
    def request(self, method, url, body = None, headers = {}):
        self.rawConnection.request(method, url, body, headers);
    
    def hasResult(self):
        if self.responceLock.acquire(False):
            self.responceLock.release()
            return True
        else:
            return False
        
    def getResult(self):
        while not self.hasResult() and not self.closing:
            time.sleep(1)
        return self.responce
    
    def go(self):
        self.responceLock.acquire()
        thread.start_new_thread ( NBHTTPSConnection._run, ( self, ) )
        
    def _run(self):
        self.responce = self.rawConnection.getresponse()
        self.responceLock.release()
        
    def close(self):
        self.closing = True
        self.rawConnection.close()
    

########NEW FILE########
__FILENAME__ = notification_service
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
import telnetlib, time

try: import simplejson as json
except ImportError: import json

import threading
from utilities import *
from rating import *
from sync_update import *
from instant_sync import *
from scrobbler import Scrobbler

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

# Receives XBMC notifications and passes them off to the rating functions
class NotificationService(threading.Thread):
    abortRequested = False
    def run(self):        
        #while xbmc is running
        scrobbler = Scrobbler()
        scrobbler.start()
        
        while (not (self.abortRequested or xbmc.abortRequested)):
            time.sleep(1)
            try:
                tn = telnetlib.Telnet('localhost', 9090, 10)
            except IOError as (errno, strerror):
                #connection failed, try again soon
                Debug("[Notification Service] Telnet too soon? ("+str(errno)+") "+strerror)
                time.sleep(1)
                continue
            
            Debug("[Notification Service] Waiting~");
            bCount = 0
            
            while (not (self.abortRequested or xbmc.abortRequested)):
                try:
                    if bCount == 0:
                        notification = ""
                        inString = False
                    [index, match, raw] = tn.expect(["(\\\\)|(\\\")|[{\"}]"], 0.2) #note, pre-compiled regex might be faster here
                    notification += raw
                    if index == -1: # Timeout
                        continue
                    if index == 0: # Found escaped quote
                        match = match.group(0)
                        if match == "\"":
                            inString = not inString
                            continue
                        if match == "{":
                            bCount += 1
                        if match == "}":
                            bCount -= 1
                    if bCount > 0:
                        continue
                    if bCount < 0:
                        bCount = 0
                except EOFError:
                    break #go out to the other loop to restart the connection
                
                Debug("[Notification Service] message: " + str(notification))
                
                # Parse recieved notification
                data = json.loads(notification)
                
                # Forward notification to functions
                if 'method' in data and 'params' in data and 'sender' in data['params'] and data['params']['sender'] == 'xbmc':
                    if data['method'] == 'Player.OnStop':
                        scrobbler.playbackEnded()
                    elif data['method'] == 'Player.OnPlay':
                        if 'data' in data['params'] and 'item' in data['params']['data'] and 'id' in data['params']['data']['item'] and 'type' in data['params']['data']['item']:
                            scrobbler.playbackStarted(data['params']['data'])
                    elif data['method'] == 'Player.OnPause':
                        scrobbler.playbackPaused()
                    elif data['method'] == 'VideoLibrary.OnUpdate':
                        if 'data' in data['params'] and 'playcount' in data['params']['data']:
                            instantSyncPlayCount(data)
                    elif data['method'] == 'System.OnQuit':
                        self.abortRequested = True
        try:
            tn.close()
        except:
            Debug("[NotificationService] Encountered error attempting to close the telnet connection")
            raise
        scrobbler.abortRequested = True
        Debug("Notification service stopping")
########NEW FILE########
__FILENAME__ = rating
# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
from utilities import *
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def ratingCheck(curVideo, watchedTime, totalTime, playlistLength):
    __settings__ = xbmcaddon.Addon( "script.traktutilities" ) #read settings again, encase they have changed
    # you can disable rating in options
    rateMovieOption = __settings__.getSetting("rate_movie")
    rateEpisodeOption = __settings__.getSetting("rate_episode")
    rateEachInPlaylistOption = __settings__.getSetting("rate_each_playlist_item")
    rateMinViewTimeOption = __settings__.getSetting("rate_min_view_time")

    if (watchedTime/totalTime)*100>=float(rateMinViewTimeOption):
        if (playlistLength <= 1) or (rateEachInPlaylistOption == 'true'):
            if curVideo['type'] == 'movie' and rateMovieOption == 'true':
                doRateMovie(curVideo['id'])
            if curVideo['type'] == 'episode' and rateEpisodeOption == 'true':
                doRateEpisode(curVideo['id'])

# ask user if they liked the movie
def doRateMovie(movieid=None, imdbid=None, title=None, year=None):
    if (movieid <> None) :
        match = getMovieDetailsFromXbmc(movieid, ['imdbnumber','title','year'])
        if not match:
            #add error message here
            return
        
        imdbid = match['imdbnumber']
        title = match['title']
        year = match['year']
        
    # display rate dialog
    import windows
    ui = windows.RateMovieDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initDialog(imdbid, title, year, getMovieRatingFromTrakt(imdbid, title, year))
    ui.doModal()
    del ui

# ask user if they liked the episode
def doRateEpisode(episodeId):
    match = getEpisodeDetailsFromXbmc(episodeId, ['showtitle', 'season', 'episode'])
    if not match:
        #add error message here
        return
    
    tvdbid = None #match['tvdbnumber']
    title = match['showtitle']
    year = None #match['year']
    season = match['season']
    episode = match['episode']
    
    # display rate dialog
    import windows
    ui = windows.RateEpisodeDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initDialog(tvdbid, title, year, season, episode, getEpisodeRatingFromTrakt(tvdbid, title, year, season, episode))
    ui.doModal()
    del ui

########NEW FILE########
__FILENAME__ = raw_xbmc_database
import os, xbmc
from utilities import Debug
#provides access to the raw xbmc video database


global _RawXbmcDb__conn
_RawXbmcDb__conn = None
class RawXbmcDb():

    # make a httpapi based XBMC db query (get data)
    @staticmethod
    def query(str):
        global _RawXbmcDb__conn
        if _RawXbmcDb__conn is None:
            _RawXbmcDb__conn = _findXbmcDb()

        Debug("[RawXbmcDb] query: "+str)
        cursor = _RawXbmcDb__conn.cursor()
        cursor.execute(str)

        matches = []
        for row in cursor:
            matches.append(row)
        
        Debug("[RawXbmcDb] matches: "+unicode(matches))

        _RawXbmcDb__conn.commit()
        cursor.close()
        return matches

    # execute a httpapi based XBMC db query (set data)
    @staticmethod
    def execute(str):
        return RawXbmcDb.query(str)

def _findXbmcDb():
    import re
    type = None
    host = None
    port = 3306
    name = 'MyVideos'
    user = None
    passwd = None
    version = re.findall( "<field>((?:[^<]|<(?!/))*)</field>", xbmc.executehttpapi("QueryVideoDatabase(SELECT idVersion FROM version)"),)[0]
    Debug(version)
    if not os.path.exists(xbmc.translatePath("special://userdata/advancedsettings.xml")):
        type = 'sqlite3'
    else:
        from xml.etree.ElementTree import ElementTree
        advancedsettings = ElementTree()
        advancedsettings.parse(xbmc.translatePath("special://userdata/advancedsettings.xml"))
        settings = advancedsettings.getroot().find("videodatabase")
        if settings is not None:
            for setting in settings:
                if setting.tag == 'type':
                    type = setting.text
                elif setting.tag == 'host':
                    host = setting.text
                elif setting.tag == 'port':
                    port = setting.text
                elif setting.tag == 'name':
                    name = setting.text
                elif setting.tag == 'user':
                    user = setting.text
                elif setting.tag == 'pass':
                    passwd = setting.text
        else:
            type = 'sqlite3'
    
    if type == 'sqlite3':
        if host is None:
            path = xbmc.translatePath("special://userdata/Database")
            files = os.listdir(path)
            latest = ""
            for file in files:
                if file[:8] == 'MyVideos' and file[-3:] == '.db':
                    if file > latest:
                        latest = file
            host = os.path.join(path,latest)
        else:
            host += version+".db"
        Debug("[RawXbmcDb] Found sqlite3db: "+str(host))
        import sqlite3
        return sqlite3.connect(host)
    if type == 'mysql':
        if version >= 60:
            database = name+version
        else:
            database = name
        Debug("[RawXbmcDb] Found mysqldb: "+str(host)+":"+str(port)+", "+str(database))
        import mysql.connector
        return mysql.connector.Connect(host = str(host), port = int(port), database = str(database), user = str(user), password = str(passwd))        
########NEW FILE########
__FILENAME__ = recommend
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
from utilities import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )
https = __settings__.getSetting('https')

if (https == 'true'):
    conn = httplib.HTTPSConnection('api.trakt.tv')
else:
    conn = httplib.HTTPConnection('api.trakt.tv')

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

# list reccomended movies
def showRecommendedMovies():

    movies = getRecommendedMoviesFromTrakt()
    watchlist = traktMovieListByImdbID(getWatchlistMoviesFromTrakt())
    
    if movies == None: # movies = None => there was an error
        return # error already displayed in utilities.py
    
    if len(movies) == 0:
        xbmcgui.Dialog().ok(__language__(1201).encode( "utf-8", "ignore" ), __language__(1158).encode( "utf-8", "ignore" )) # Trakt Utilities, there are no movies recommended for you
        return
    
    for movie in movies:
        if movie['imdb_id'] in watchlist:
            movie['watchlist'] = True
        else:
            movie['watchlist'] = False
    
    # display recommended movies list
    import windows
    ui = windows.MoviesWindow("movies.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(movies, 'recommended')
    ui.doModal()
    del ui
    
# list reccomended tv shows
def showRecommendedTVShows():

    tvshows = getRecommendedTVShowsFromTrakt()
    
    if tvshows == None: # tvshows = None => there was an error
        return # error already displayed in utilities.py
    
    if len(tvshows) == 0:
        xbmcgui.Dialog().ok(__language__(1201).encode( "utf-8", "ignore" ), __language__(1159).encode( "utf-8", "ignore" )) # Trakt Utilities, there are no tv shows recommended for you
        return
    
    for tvshow in tvshows:
        tvshow['watchlist'] = tvshow['in_watchlist']
        
    # display recommended tv shows
    import windows
    ui = windows.TVShowsWindow("tvshows.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(tvshows, 'recommended')
    ui.doModal()
    del ui
    

########NEW FILE########
__FILENAME__ = scrobbler
# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
import threading
import time

from utilities import *
from rating import *
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a' # scrobbling requires this dev key
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

class Scrobbler(threading.Thread):
    totalTime = 1
    watchedTime = 0
    startTime = 0
    curVideo = None
    pinging = False
    playlistLength = 1
    abortRequested = False
    
    def run(self):
        # When requested ping trakt to say that the user is still watching the item
        count = 0
        while (not (self.abortRequested or xbmc.abortRequested)):
            time.sleep(5) # 1min wait
            #Debug("[Scrobbler] Cycling " + str(self.pinging))
            if self.pinging:
                count += 1
                if count>=100:
                    Debug("[Scrobbler] Pinging watching "+str(self.curVideo))
                    tmp = time.time()
                    self.watchedTime += tmp - self.startTime
                    self.startTime = tmp
                    self.startedWatching()
                    count = 0
            else:
                count = 0
        
        Debug("Scrobbler stopping")
    
    def playbackStarted(self, data):
        self.curVideo = data['item']
        if self.curVideo <> None:
            if 'type' in self.curVideo and 'id' in self.curVideo:
                Debug("[Scrobbler] Watching: "+self.curVideo['type']+" - "+str(self.curVideo['id']))
                try:
                    if not xbmc.Player().isPlayingVideo():
                        Debug("[Scrobbler] Suddenly stopped watching item")
                        return
                    time.sleep(1) # Wait for possible silent seek (caused by resuming)
                    self.watchedTime = xbmc.Player().getTime()
                    self.totalTime = xbmc.Player().getTotalTime()
                    if self.totalTime == 0:
                        if self.curVideo['type'] == 'movie':
                            self.totalTime = 90
                        elif self.curVideo['type'] == 'episode':
                            self.totalTime = 30
                        else:
                            self.totalTime = 1
                    self.playlistLength = getPlaylistLengthFromXBMCPlayer(data['player']['playerid'])
                    if (self.playlistLength == 0):
                        Debug("[Scrobbler] Warning: Cant find playlist length?!, assuming that this item is by itself")
                        self.playlistLength = 1
                except:
                    Debug("[Scrobbler] Suddenly stopped watching item, or error: "+str(sys.exc_info()[0]))
                    self.curVideo = None
                    self.startTime = 0
                    return
                self.startTime = time.time()
                self.startedWatching()
                self.pinging = True
            else:
                self.curVideo = None
                self.startTime = 0

    def playbackPaused(self):
        if self.startTime <> 0:
            self.watchedTime += time.time() - self.startTime
            Debug("[Scrobbler] Paused after: "+str(self.watchedTime))
            self.startTime = 0

    def playbackEnded(self):
        if self.startTime <> 0:
            if self.curVideo == None:
                Debug("[Scrobbler] Warning: Playback ended but video forgotten")
                return
            self.watchedTime += time.time() - self.startTime
            self.pinging = False
            if self.watchedTime <> 0:
                if 'type' in self.curVideo and 'id' in self.curVideo:
                    self.check()
                    ratingCheck(self.curVideo, self.watchedTime, self.totalTime, self.playlistLength)
                self.watchedTime = 0
            self.startTime = 0
            
    def startedWatching(self):
        scrobbleMovieOption = __settings__.getSetting("scrobble_movie")
        scrobbleEpisodeOption = __settings__.getSetting("scrobble_episode")
        
        if self.curVideo['type'] == 'movie' and scrobbleMovieOption == 'true':
            match = getMovieDetailsFromXbmc(self.curVideo['id'], ['imdbnumber','title','year'])
            if match == None:
                return
            responce = watchingMovieOnTrakt(match['imdbnumber'], match['title'], match['year'], self.totalTime/60, int(100*self.watchedTime/self.totalTime))
            if responce != None:
                Debug("[Scrobbler] Watch responce: "+str(responce));
        elif self.curVideo['type'] == 'episode' and scrobbleEpisodeOption == 'true':
            match = getEpisodeDetailsFromXbmc(self.curVideo['id'], ['showtitle', 'season', 'episode'])
            if match == None:
                return
            responce = watchingEpisodeOnTrakt(None, match['showtitle'], None, match['season'], match['episode'], self.totalTime/60, int(100*self.watchedTime/self.totalTime))
            if responce != None:
                Debug("[Scrobbler] Watch responce: "+str(responce));
        
    def stoppedWatching(self):
        scrobbleMovieOption = __settings__.getSetting("scrobble_movie")
        scrobbleEpisodeOption = __settings__.getSetting("scrobble_episode")
        
        if self.curVideo['type'] == 'movie' and scrobbleMovieOption == 'true':
            responce = cancelWatchingMovieOnTrakt()
            if responce != None:
                Debug("[Scrobbler] Cancel watch responce: "+str(responce));
        elif self.curVideo['type'] == 'episode' and scrobbleEpisodeOption == 'true':
            responce = cancelWatchingEpisodeOnTrakt()
            if responce != None:
                Debug("[Scrobbler] Cancel watch responce: "+str(responce));
            
    def scrobble(self):
        scrobbleMovieOption = __settings__.getSetting("scrobble_movie")
        scrobbleEpisodeOption = __settings__.getSetting("scrobble_episode")
        
        if self.curVideo['type'] == 'movie' and scrobbleMovieOption == 'true':
            match = getMovieDetailsFromXbmc(self.curVideo['id'], ['imdbnumber','title','year'])
            if match == None:
                return
            responce = scrobbleMovieOnTrakt(match['imdbnumber'], match['title'], match['year'], self.totalTime/60, int(100*self.watchedTime/self.totalTime))
            if responce != None:
                Debug("[Scrobbler] Scrobble responce: "+str(responce));
        elif self.curVideo['type'] == 'episode' and scrobbleEpisodeOption == 'true':
            match = getEpisodeDetailsFromXbmc(self.curVideo['id'], ['showtitle', 'season', 'episode'])
            if match == None:
                return
            responce = scrobbleEpisodeOnTrakt(None, match['showtitle'], None, match['season'], match['episode'], self.totalTime/60, int(100*self.watchedTime/self.totalTime))
            if responce != None:
                Debug("[Scrobbler] Scrobble responce: "+str(responce));

    def check(self):
        __settings__ = xbmcaddon.Addon( "script.traktutilities" ) #read settings again, encase they have changed
        scrobbleMinViewTimeOption = __settings__.getSetting("scrobble_min_view_time")
        
        if (self.watchedTime/self.totalTime)*100>=float(scrobbleMinViewTimeOption):
            self.scrobble()
        else:
            self.stoppedWatching()

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
from utilities import *
from rating import *
from sync_update import *
from notification_service import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

Debug("service: " + __settings__.getAddonInfo("id") + " - version: " + __settings__.getAddonInfo("version"))

# starts update/sync
def autostart():
    if checkSettings(True):
        notificationThread = NotificationService()
        notificationThread.start()
        
        autosync_moviecollection = __settings__.getSetting("autosync_moviecollection")
        autosync_tvshowcollection = __settings__.getSetting("autosync_tvshowcollection")
        autosync_cleanmoviecollection = __settings__.getSetting("autosync_cleanmoviecollection")
        autosync_cleantvshowcollection = __settings__.getSetting("autosync_cleantvshowcollection")
        autosync_seenmovies = __settings__.getSetting("autosync_seenmovies")
        autosync_seentvshows = __settings__.getSetting("autosync_seentvshows")
        try:
            if autosync_moviecollection == "true":
                notification("Trakt Utilities", __language__(1180).encode( "utf-8", "ignore" )) # start movie collection update
                updateMovieCollection(True)
                if autosync_cleanmoviecollection: cleanMovieCollection(True)
            if xbmc.abortRequested: raise SystemExit()
            
            if autosync_tvshowcollection == "true":
                notification("Trakt Utilities", __language__(1181).encode( "utf-8", "ignore" )) # start tvshow collection update
                updateTVShowCollection(True)
                if autosync_cleantvshowcollection: cleanTVShowCollection(True)
            if xbmc.abortRequested: raise SystemExit()
            
            if autosync_seenmovies == "true":
                Debug("autostart sync seen movies")
                notification("Trakt Utilities", __language__(1182).encode( "utf-8", "ignore" )) # start sync seen movies
                syncSeenMovies(True)
            if xbmc.abortRequested: raise SystemExit()
            
            if autosync_seentvshows == "true":
                Debug("autostart sync seen tvshows")
                notification("Trakt Utilities", __language__(1183).encode( "utf-8", "ignore" )) # start sync seen tv shows
                syncSeenTVShows(True)
            if xbmc.abortRequested: raise SystemExit()
            
            if autosync_moviecollection == "true" or autosync_tvshowcollection == "true" or autosync_seenmovies == "true" or autosync_seentvshows == "true":
                notification("Trakt Utilities", __language__(1184).encode( "utf-8", "ignore" )) # update / sync done
        except SystemExit:
            notificationThread.abortRequested = True
            Debug("[Service] Auto sync processes aborted due to shutdown request")
            
        notificationThread.join()

autostart()

########NEW FILE########
__FILENAME__ = sync_update
# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
import time, socket
from utilities import *

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

import datetime
year = datetime.datetime.now().year

# updates movie collection entries on trakt (don't unlibrary)
def updateMovieCollection(daemon=False):

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1132).encode( "utf-8", "ignore" )) # Checking Database for new Episodes
    
    # get the required informations
    trakt_movies = traktMovieListByImdbID(getMovieCollectionFromTrakt())
    xbmc_movies = getMoviesFromXBMC()
    
    if xbmc_movies == None or trakt_movies == None: # error
        return

    movie_collection = []
    
    for i in range(0, len(xbmc_movies)):
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progress.update(100 / len(xbmc_movies) * i)
            if progress.iscanceled():
                notification ("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                return
        try:
            imdbid = xbmc_movies[i]['imdbnumber']
            try:
                Debug("found Movie: " + repr(xbmc_movies[i]['label']) + " - IMDb ID: " + str(imdbid.encode("utf-8", "ignore")))
            except KeyError:
                Debug("found Movie with IMDb ID: " + str(imdbid.encode("utf-8", "ignore")))
        except KeyError:
            try:
                Debug("skipping " + repr(xbmc_movies[i]['label']) + " - no IMDb ID found")
            except KeyError:
                try:
                    Debug("skipping " + repr(xbmc_movies[i]['title']) + " - no IMDb ID found")
                except KeyError:
                    Debug("skipping a movie: no title and no IMDb ID found")
            continue
        
        try:
            trakt_movie = trakt_movies[imdbid]
        except KeyError: # movie not on trakt right now
            if xbmc_movies[i]['year'] > 0:
                try:
                    movie_collection.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': xbmc_movies[i]['year']})
                except KeyError:
                    movie_collection.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': xbmc_movies[i]['year']})
            else:
                try:
                    movie_collection.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': 0})
                except KeyError:
                    try:
                        movie_collection.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': 0})
                    except KeyError:
                        try:
                            movie_collection.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['label'], 'year': 0})
                        except KeyError:
                            try:
                                movie_collection.append({'imdb_id': imdbid, 'title': "", 'year': 0})
                            except KeyError:
                                Debug("skipping a movie: no title, label, year and IMDb ID found")
                
    if not daemon:
        progress.close()
    
    movies_string = ""
    for i in range(0, len(movie_collection)):
        if xbmc.abortRequested: raise SystemExit()
        if i == 0:
            movies_string += movie_collection[i]['title']
        elif i > 5:
            break
        else:
            movies_string += ", " + movie_collection[i]['title']

    # add movies to trakt library (collection):
    if len(movie_collection) > 0:
        inserted = 0
        exist = 0
        skipped = 0
        
        if not daemon:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(len(movie_collection)) + " " + __language__(1125).encode( "utf-8", "ignore" ), movies_string) # Movies will be added to Trakt Collection
            if choice == False:
                return
        first = 0
        last = 0
        while last <= len(movie_collection):
            if xbmc.abortRequested: raise SystemExit()
            last = first+25
            data = traktJsonRequest('POST', '/movie/library/%%API_KEY%%', {'movies': movie_collection[first:last]}, returnStatus=True)
            first = last
            
            if data['status'] == 'success':
                Debug ("successfully uploaded collection: ")
                Debug ("inserted: " + str(data['inserted']) + " already_exist: " + str(data['already_exist']) + " skipped: " + str(data['skipped']))
                if data['skipped'] > 0:
                    Debug ("skipped movies: " + repr(data['skipped_movies']))
                inserted += data['inserted']
                exist += data['already_exist']
                skipped += data['skipped']
                
            elif data['status'] == 'failure':
                Debug ("Error uploading movie collection: " + str(data['error']))
                if not daemon:
                    xbmcgui.Dialog().ok("Trakt Utilities", __language__(1121).encode( "utf-8", "ignore" ), str(data['error'])) # Error uploading movie collection
        if not daemon:
                xbmcgui.Dialog().ok("Trakt Utilities", str(inserted) + " " + __language__(1126).encode( "utf-8", "ignore" ), str(skipped) + " " + __language__(1138).encode( "utf-8", "ignore" )) # Movies updated on Trakt / Movies skipped
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1122).encode( "utf-8", "ignore" )) # No new movies in XBMC library to update

# updates tvshow collection entries on trakt (no unlibrary)
def updateTVShowCollection(daemon=False):

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1133).encode( "utf-8", "ignore" )) # Checking Database for new Episodes

    # get the required informations
    trakt_tvshowlist = getTVShowCollectionFromTrakt()
    xbmc_tvshows = getTVShowsFromXBMC()
    
    if xbmc_tvshows == None or trakt_tvshowlist == None: # error
        return
    
    trakt_tvshows = {}

    for i in range(0, len(trakt_tvshowlist)):
        trakt_tvshows[trakt_tvshowlist[i]['tvdb_id']] = trakt_tvshowlist[i]
        
    seasonid = -1
    seasonid2 = 0
    tvshows_toadd = []
    tvshow = {}
    foundseason = False
        
    for i in range(0, xbmc_tvshows['limits']['total']):
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progress.update(100 / xbmc_tvshows['limits']['total'] * i)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                return
            
        seasons = getSeasonsFromXBMC(xbmc_tvshows['tvshows'][i])
        try:
            tvshow['title'] = xbmc_tvshows['tvshows'][i]['title']
        except KeyError:
            # no title? try label
            try:
                tvshow['title'] = xbmc_tvshows['tvshows'][i]['label']
            except KeyError:
                # no titel, no label ... sorry no upload ...
                continue
                
        try:
            tvshow['year'] = xbmc_tvshows['tvshows'][i]['year']
            tvshow['tvdb_id'] = xbmc_tvshows['tvshows'][i]['imdbnumber']
        except KeyError:
            # no year, no tvdb id ... sorry no upload ...
            continue
            
        tvshow['episodes'] = []
        
        for j in range(0, seasons['limits']['total']):
            while True:
                seasonid += 1
                episodes = getEpisodesFromXBMC(xbmc_tvshows['tvshows'][i], seasonid)
                
                if episodes['limits']['total'] > 0:
                    break
                if seasonid > 250 and seasonid < 1900:
                    seasonid = 1900  # check seasons that are numbered by year
                if seasonid > year+2:
                    break # some seasons off the end?!
            if seasonid > year+2:
                continue
            try:
                foundseason = False
                for k in range(0, len(trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'])):
                    if trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'][k]['season'] == seasonid:
                        foundseason = True
                        for l in range(0, len(episodes['episodes'])):
                            if episodes['episodes'][l]['episode'] in trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'][k]['episodes']:
                                pass
                            else:
                                # add episode
                                tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][l]['episode']})
                if foundseason == False:
                    # add season
                    for k in range(0, len(episodes['episodes'])):
                        tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][k]['episode']})
            except KeyError:
                # add season (whole tv show missing)
                for k in range(0, len(episodes['episodes'])):
                    tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][k]['episode']})
        
        seasonid = -1
        # if there are episodes to add to trakt - append to list
        if len(tvshow['episodes']) > 0:
            tvshows_toadd.append(tvshow)
            tvshow = {}
        else:
            tvshow = {}
    
    if not daemon:
        progress.close()
            
    count = 0
    for i in range(0, len(tvshows_toadd)):
        for j in range(0, len(tvshows_toadd[i]['episodes'])):
            count += 1
            
    tvshows_string = ""
    for i in range(0, len(tvshows_toadd)):
        if i == 0:
            tvshows_string += tvshows_toadd[i]['title']
        elif i > 5:
            break
        else:
            tvshows_string += ", " + tvshows_toadd[i]['title']
    
    # add episodes to library (collection):
    if count > 0:
        if daemon:
            notification("Trakt Utilities", str(count) + " " + __language__(1131).encode( "utf-8", "ignore" )) # TVShow Episodes will be added to Trakt Collection
        else:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(count) + " " + __language__(1131).encode( "utf-8", "ignore" ), tvshows_string) # TVShow Episodes will be added to Trakt Collection
            if choice == False:
                return
        
        error = None
        
        # refresh connection (don't want to get tcp timeout)
        conn = getTraktConnection()
        
        for i in range(0, len(tvshows_toadd)):
            if xbmc.abortRequested: raise SystemExit()
            data = traktJsonRequest('POST', '/show/episode/library/%%API_KEY%%', {'tvdb_id': tvshows_toadd[i]['tvdb_id'], 'title': tvshows_toadd[i]['title'], 'year': tvshows_toadd[i]['year'], 'episodes': tvshows_toadd[i]['episodes']}, returnStatus=True, conn = conn)
            
            if data['status'] == 'success':
                Debug ("successfully uploaded collection: " + str(data['message']))
            elif data['status'] == 'failure':
                Debug ("Error uploading tvshow collection: " + str(data['error']))
                error = data['error']
                
        if error == None:
            if not daemon:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1137).encode( "utf-8", "ignore" )) # Episodes sucessfully updated to Trakt
        else:
            if daemon:
                notification("Trakt Utilities", __language__(1135).encode( "utf-8", "ignore" ) + str(error)) # Error uploading TVShow collection
            else:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1135).encode( "utf-8", "ignore" ), error) # Error uploading TVShow collection
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1136).encode( "utf-8", "ignore" )) # No new episodes in XBMC library to update

# removes deleted movies from trakt collection
def cleanMovieCollection(daemon=False):

    # display warning
    if not daemon:
        choice = xbmcgui.Dialog().yesno("Trakt Utilities", __language__(1153).encode( "utf-8", "ignore" ), __language__(1154).encode( "utf-8", "ignore" ), __language__(1155).encode( "utf-8", "ignore" )) # 
        if choice == False:
            return
    
    # display progress
    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1139).encode( "utf-8", "ignore" )) # Checking Database for deleted Movies

    # get the required informations
    trakt_movies = traktMovieListByImdbID(getMoviesFromTrakt())
    xbmc_movies = getMoviesFromXBMC()
    
    if xbmc_movies == None or trakt_movies == None: # error
        if not daemon:
            progress.close()
        return

    to_unlibrary = []
    
    # to get xbmc movies by imdbid
    xbmc_movies_imdbid = {}
    for i in range(0, len(xbmc_movies)):
        try:
            xbmc_movies_imdbid[xbmc_movies[i]['imdbnumber']] = xbmc_movies[i]
        except KeyError:
            continue
    
    progresscount = 0
    for movie in trakt_movies.items():
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progresscount += 1
            progress.update(100 / len(trakt_movies.items()) * progresscount)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                return
        if movie[1]['in_collection']:
            try:
                xbmc_movies_imdbid[movie[1]['imdb_id']]
            except KeyError: # not on xbmc database
                to_unlibrary.append(movie[1])
                Debug (repr(movie[1]['title']) + " not found in xbmc library")
    
    if len(to_unlibrary) > 0:
        data = traktJsonRequest('POST', '/movie/unlibrary/%%API_KEY%%', {'movies': to_unlibrary}, returnStatus = True)
        
        if data['status'] == 'success':
            Debug ("successfully cleared collection: " + str(data['message']))
            if not daemon:
                xbmcgui.Dialog().ok("Trakt Utilities", str(data['message']))
        elif data['status'] == 'failure':
            Debug ("Error uploading movie collection: " + str(data['error']))
            if daemon:
                notification("Trakt Utilities", __language__(1121).encode( "utf-8", "ignore" ), str(data['error'])) # Error uploading movie collection
            else:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1121).encode( "utf-8", "ignore" ), str(data['error'])) # Error uploading movie collection
    else:
        if not daemon:
			xbmcgui.Dialog().ok("Trakt Utilities", __language__(1130).encode( "utf-8", "ignore" )) # No new movies in library to update
    if not daemon:
        progress.close()

# removes deleted tvshow episodes from trakt collection (unlibrary)
def cleanTVShowCollection(daemon=False):

    # display warning
    if not daemon:
        choice = xbmcgui.Dialog().yesno("Trakt Utilities", __language__(1156).encode( "utf-8", "ignore" ), __language__(1154).encode( "utf-8", "ignore" ), __language__(1155).encode( "utf-8", "ignore" )) # 
        if choice == False:
            return

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1140).encode( "utf-8", "ignore" )) # Checking Database for deleted Episodes

    # get the required informations
    trakt_tvshowlist = getTVShowCollectionFromTrakt()
    xbmc_tvshows = getTVShowsFromXBMC()
    
    if xbmc_tvshows == None or trakt_tvshowlist == None: # error
        return
    
    trakt_tvshows = {}

    for i in range(0, len(trakt_tvshowlist)):
        trakt_tvshows[trakt_tvshowlist[i]['tvdb_id']] = trakt_tvshowlist[i]
    
    to_unlibrary = []
    
    xbmc_tvshows_tvdbid = {}
    tvshow = {}
    seasonid = -1
    foundseason = False
    progresscount = -1
    
    # make xbmc tvshows searchable by tvdbid
    for i in range(0, xbmc_tvshows['limits']['total']):
        try:
            xbmc_tvshows_tvdbid[xbmc_tvshows['tvshows'][i]['imdbnumber']] = xbmc_tvshows['tvshows'][i]
        except KeyError:
            continue # missing data, skip tvshow
    
    for trakt_tvshow in trakt_tvshows.items():
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progresscount += 1
            progress.update(100 / len(trakt_tvshows) * progresscount)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                return
        
        try:
            tvshow['title'] = trakt_tvshow[1]['title']
            tvshow['year'] = trakt_tvshow[1]['year']
            tvshow['tvdb_id'] = trakt_tvshow[1]['tvdb_id']
        except KeyError:
            # something went wrong
            Debug("cleanTVShowCollection: KeyError trakt_tvshow[1] title, year or tvdb_id")
            continue # skip this tvshow
            
        tvshow['episodes'] = []
        try:
            xbmc_tvshow = xbmc_tvshows_tvdbid[trakt_tvshow[1]['tvdb_id']]
            # check seasons
            xbmc_seasons = getSeasonsFromXBMC(xbmc_tvshow)
            for i in range(0, len(trakt_tvshow[1]['seasons'])):
                count = 0
                
                
                
                for j in range(0, xbmc_seasons['limits']['total']):
                    while True:
                        seasonid += 1
                        xbmc_episodes = getEpisodesFromXBMC(xbmc_tvshow, seasonid)
                        if xbmc_episodes['limits']['total'] > 0:
                            count += 1
                            if trakt_tvshow[1]['seasons'][i]['season'] == seasonid:
                                foundseason = True
                                # check episodes
                                for k in range(0, len(trakt_tvshow[1]['seasons'][i]['episodes'])):
                                    episodeid = trakt_tvshow[1]['seasons'][i]['episodes'][k]
                                    found = False
                                    for l in range(0, xbmc_episodes['limits']['total']):
                                        if xbmc_episodes['episodes'][l]['episode'] == episodeid:
                                            found = True
                                            break
                                    if found == False:
                                        # delte episode from trakt collection
                                        tvshow['episodes'].append({'season': seasonid, 'episode': episodeid})
                                break
                        if count >= xbmc_seasons['limits']['total']:
                            break
                        if seasonid > 250 and seasonid < 1900:
                            seasonid = 1900  # check seasons that are numbered by year
                        if seasonid > year+2:
                            break # some seasons off the end?!
                    if seasonid > year+2:
                        continue
                if foundseason == False:
                    Debug("Season not found: " + repr(trakt_tvshow[1]['title']) + ": " + str(trakt_tvshow[1]['seasons'][i]['season']))
                    # delte season from trakt collection
                    for episodeid in trakt_tvshow[1]['seasons'][i]['episodes']:
                        tvshow['episodes'].append({'season': trakt_tvshow[1]['seasons'][i]['season'], 'episode': episodeid})
                foundseason = False
                seasonid = -1
            
        except KeyError:
            Debug ("TVShow not found: " + repr(trakt_tvshow[1]['title']))
            # delete tvshow from trakt collection
            for season in trakt_tvshow[1]['seasons']:
                for episode in season['episodes']:
                    tvshow['episodes'].append({'season': season['season'], 'episode': episode})
                    
        if len(tvshow['episodes']) > 0:
            to_unlibrary.append(tvshow)
        tvshow = {}
    
    if not daemon:
        progress.close()
    
    for i in range(0, len(to_unlibrary)):
        episodes_debug_string = ""
        for j in range(0, len(to_unlibrary[i]['episodes'])):
            episodes_debug_string += "S" + str(to_unlibrary[i]['episodes'][j]['season']) + "E" + str(to_unlibrary[i]['episodes'][j]['episode']) + " "
        Debug("Found for deletion: " + to_unlibrary[i]['title'] + ": " + episodes_debug_string)
        
    count = 0
    for tvshow in to_unlibrary:
        count += len(tvshow['episodes'])
        
    tvshows_string = ""
    for i in range(0, len(to_unlibrary)):
        if to_unlibrary[i]['title'] is None:
            to_unlibrary[i]['title'] = "Unknown"
        if i == 0:
            tvshows_string += to_unlibrary[i]['title']
        elif i > 5:
            break
        else:
            tvshows_string += ", " + to_unlibrary[i]['title']
    
    # add episodes to library (collection):
    if count > 0:
        if not daemon:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(count) + " " + __language__(1141).encode( "utf-8", "ignore" ), tvshows_string) # TVShow Episodes will be removed from Trakt Collection
            if choice == False:
                return
            
        error = None
        
        # refresh connection (don't want to get tcp timeout)
        conn = getTraktConnection()
        
        for i in range(0, len(to_unlibrary)):
            if xbmc.abortRequested: raise SystemExit()
            data = traktJsonRequest('POST', '/show/episode/unlibrary/%%API_KEY%%', {'tvdb_id': to_unlibrary[i]['tvdb_id'], 'title': to_unlibrary[i]['title'], 'year': to_unlibrary[i]['year'], 'episodes': to_unlibrary[i]['episodes']}, returnStatus = True, conn = conn)
            
            if data['status'] == 'success':
                Debug ("successfully updated collection: " + str(data['message']))
            elif data['status'] == 'failure':
                Debug ("Error uploading tvshow collection: " + str(data['error']))
                error = data['error']
        
        if error == None:
            if daemon:
                notification("Trakt Utilities", __language__(1137).encode( "utf-8", "ignore" )) # Episodes sucessfully updated to Trakt
            else:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1137).encode( "utf-8", "ignore" )) # Episodes sucessfully updated to Trakt
        else:
            if daemon:
                notification("Trakt Utilities", __language__(1135).encode( "utf-8", "ignore" ) + unicode(error)) # Error uploading TVShow collection
            else:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1135).encode( "utf-8", "ignore" ), error) # Error uploading TVShow collection
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1142).encode( "utf-8", "ignore" )) # No episodes to remove from trakt

# updates seen movies on trakt
def syncSeenMovies(daemon=False):

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1300).encode( "utf-8", "ignore" )) # Checking XBMC Database for new seen Movies
    
    # get the required informations
    trakt_movies = traktMovieListByImdbID(getMoviesFromTrakt())
    xbmc_movies = getMoviesFromXBMC()
    
    if xbmc_movies == None or trakt_movies == None: # error
        if not daemon:
            progress.close()
        return
        
    movies_seen = []

    for i in range(0, len(xbmc_movies)):
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progress.update(100 / len(xbmc_movies) * i)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                break
        try:
            imdbid = xbmc_movies[i]['imdbnumber']
        except KeyError:
            try:
                Debug("skipping " + repr(xbmc_movies[i]['title']) + " - no IMDbID found")
            except KeyError:
                try:
                    Debug("skipping " + repr(xbmc_movies[i]['label']) + " - no IMDbID found")
                except KeyError:
                    Debug("skipping a movie - no IMDbID, title, or label found")
            continue
            
        try:
            trakt_movie = trakt_movies[imdbid]
        except KeyError: # movie not on trakt right now
            # if seen, add it
            if xbmc_movies[i]['playcount'] > 0:
                if xbmc_movies[i]['year'] > 0:
                    try:
                        test = xbmc_movies[i]['lastplayed']
                        try:                         
                            movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount'], 'last_played': int(time.mktime(time.strptime(xbmc_movies[i]['lastplayed'], '%Y-%m-%d %H:%M:%S')))})
                        except KeyError:
                            movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount'], 'last_played': int(time.mktime(time.strptime(xbmc_movies[i]['lastplayed'], '%Y-%m-%d %H:%M:%S')))})
                    except (KeyError, ValueError):
                        try:
                            movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount']})
                        except KeyError:
                            movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount']})
                else:
                    Debug("skipping " + repr(xbmc_movies[i]['title']) + " - unknown year")
            continue
            
        if xbmc_movies[i]['playcount'] > 0 and trakt_movie['plays'] == 0:
            if xbmc_movies[i]['year'] > 0:
                try:
                    test = xbmc_movies[i]['lastplayed']
                    try: 
                        movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount'], 'last_played': int(time.mktime(time.strptime(xbmc_movies[i]['lastplayed'], '%Y-%m-%d %H:%M:%S')))})
                    except KeyError:
                        movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount'], 'last_played': int(time.mktime(time.strptime(xbmc_movies[i]['lastplayed'], '%Y-%m-%d %H:%M:%S')))})
                except (KeyError, ValueError):
                    try:
                        movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['originaltitle'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount']})
                    except KeyError:
                        movies_seen.append({'imdb_id': imdbid, 'title': xbmc_movies[i]['title'], 'year': xbmc_movies[i]['year'], 'plays': xbmc_movies[i]['playcount']})
            else:
                Debug("skipping " + repr(xbmc_movies[i]['title']) + " - unknown year")
    
    movies_string = ""
    for i in range(0, len(movies_seen)):
        if i == 0:
            movies_string += movies_seen[i]['title']
        elif i > 5:
            break
        else:
            movies_string += ", " + movies_seen[i]['title']

    # set movies as seen on trakt:
    if len(movies_seen) > 0:
        
        if not daemon:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(len(movies_seen)) + " " + __language__(1127).encode( "utf-8", "ignore" ), movies_string) # Movies will be added as seen on Trakt
            if choice == False:
                if not daemon:
                    progress.close()
                return
        
        data = traktJsonRequest('POST', '/movie/seen/%%API_KEY%%', {'movies': movies_seen}, returnStatus = True)
        
        if data['status'] == 'success':
            Debug ("successfully uploaded seen movies: ")
            Debug ("inserted: " + str(data['inserted']) + " already_exist: " + str(data['already_exist']) + " skipped: " + str(data['skipped']))
            if data['skipped'] > 0:
                Debug ("skipped movies: " + str(data['skipped_movies']))
            notification ("Trakt Utilities", str(len(movies_seen) - data['skipped']) + " " + __language__(1126).encode( "utf-8", "ignore" )) # Movies updated
        elif data['status'] == 'failure':
            Debug ("Error uploading seen movies: " + str(data['error']))
            if not daemon:
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1123).encode( "utf-8", "ignore" ), str(data['error'])) # Error uploading seen movies
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1124).encode( "utf-8", "ignore" )) # no new seen movies to update for trakt
    
    xbmc_movies_imdbid = {}
    for i in range(0, len(xbmc_movies)):
        try:
            xbmc_movies_imdbid[xbmc_movies[i]['imdbnumber']] = xbmc_movies[i]
        except KeyError:
            continue

    if not daemon:
        progress.close()
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1301).encode( "utf-8", "ignore" )) # Checking Trakt Database for new seen Movies

    
    # set movies seen from trakt, that are unseen on xbmc:
    movies_seen = []
    progresscount = 0
    Debug("searching local...")
    for movie in trakt_movies.items():
        if not daemon:
            progresscount += 1
            progress.update(100 / len(trakt_movies.items()) * progresscount)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                break
        if movie[1]['plays'] > 0:
            try:
                if xbmc_movies_imdbid[movie[1]['imdb_id']]['playcount'] == 0:
                    movies_seen.append(movie[1])
            except KeyError: # movie not in xbmc database
                continue
    
    movies_string = ""
    for i in range(0, len(movies_seen)):
        if i == 0:
            movies_string += movies_seen[i]['title']
        elif i > 5:
            break
        else:
            movies_string += ", " + movies_seen[i]['title']
    
    if len(movies_seen) > 0:
        if not daemon:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(len(movies_seen)) + " " + __language__(1147).encode( "utf-8", "ignore" ), movies_string) # Movies will be added as seen on Trakt
            if choice == False:
                if not daemon:
                    progress.close()
                return
        
        for i in range(0, len(movies_seen)):
            if xbmc.abortRequested: raise SystemExit()
            setXBMCMoviePlaycount(movies_seen[i]['imdb_id'], movies_seen[i]['plays']) # set playcount on xbmc
        if daemon:
            notification("Trakt Utilities", str(len(movies_seen)) + " " + __language__(1129).encode( "utf-8", "ignore" )) # Movies updated on XBMC
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", str(len(movies_seen)) + " " + __language__(1129).encode( "utf-8", "ignore" )) # Movies updated on XBMC
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1128).encode( "utf-8", "ignore" )) # no new seen movies to update for xbmc
    if not daemon:
        progress.close()

# syncs seen tvshows between trakt and xbmc (no unlibrary)
def syncSeenTVShows(daemon=False):

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1143).encode( "utf-8", "ignore" )) # Checking XBMC Database for new seen Episodes

    # get the required informations
    trakt_tvshowlist = getWatchedTVShowsFromTrakt()
    xbmc_tvshows = getTVShowsFromXBMC()
    
    if xbmc_tvshows == None or trakt_tvshowlist == None: # error
        return
    
    trakt_tvshows = {}

    for i in range(0, len(trakt_tvshowlist)):
        trakt_tvshows[trakt_tvshowlist[i]['tvdb_id']] = trakt_tvshowlist[i]
    
    set_as_seen = []
    seasonid = -1
    tvshow = {}
    
    for i in range(0, xbmc_tvshows['limits']['total']):
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progress.update(100 / xbmc_tvshows['limits']['total'] * i)
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                break
        
        seasons = getSeasonsFromXBMC(xbmc_tvshows['tvshows'][i])
        try:
            tvshow['title'] = xbmc_tvshows['tvshows'][i]['title']
            tvshow['year'] = xbmc_tvshows['tvshows'][i]['year']
            tvshow['tvdb_id'] = xbmc_tvshows['tvshows'][i]['imdbnumber']
        except KeyError:
            continue # missing data, skip
            
        tvshow['episodes'] = []
        
        for j in range(0, seasons['limits']['total']):
            while True:
                seasonid += 1
                episodes = getEpisodesFromXBMC(xbmc_tvshows['tvshows'][i], seasonid)
                if episodes['limits']['total'] > 0:
                    break
                if seasonid > 250 and seasonid < 1900:
                    seasonid = 1900  # check seasons that are numbered by year
                if seasonid > year+2:
                    break # some seasons off the end?!
            if seasonid > year+2:
                continue
            try:
                foundseason = False
                for k in range(0, len(trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'])):
                    if trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'][k]['season'] == seasonid:
                        foundseason = True
                        for l in range(0, len(episodes['episodes'])):
                            if episodes['episodes'][l]['episode'] in trakt_tvshows[xbmc_tvshows['tvshows'][i]['imdbnumber']]['seasons'][k]['episodes']:
                                pass
                            else:
                                # add episode as seen if playcount > 0
                                try:
                                    if episodes['episodes'][l]['playcount'] > 0:
                                        tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][l]['episode']})
                                except KeyError:
                                    pass
                if foundseason == False:
                    # add season
                    for k in range(0, len(episodes['episodes'])):
                        try:
                            if episodes['episodes'][k]['playcount'] > 0:
                                tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][k]['episode']})
                        except KeyError:
                                    pass
            except KeyError:
                # add season as seen (whole tv show missing)
                for k in range(0, len(episodes['episodes'])):
                    try:
                        if episodes['episodes'][k]['playcount'] > 0:
                            tvshow['episodes'].append({'season': seasonid, 'episode': episodes['episodes'][k]['episode']})
                    except KeyError:
                        pass
        
        seasonid = -1
        # if there are episodes to add to trakt - append to list
        if len(tvshow['episodes']) > 0:
            set_as_seen.append(tvshow)
            tvshow = {}
        else:
            tvshow = {}
    
    if not daemon:
        progress.close()
            
    count = 0
    set_as_seen_titles = ""
    for i in range(0, len(set_as_seen)):
        if i == 0:
            set_as_seen_titles += set_as_seen[i]['title']
        elif i > 5:
            break
        else:
            set_as_seen_titles += ", " + set_as_seen[i]['title']
        for j in range(0, len(set_as_seen[i]['episodes'])):
            count += 1
    
    # add seen episodes to trakt library:
    if count > 0:
        if daemon:
            choice = True
        else:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(count) + " " + __language__(1144).encode( "utf-8", "ignore" ), set_as_seen_titles) # TVShow Episodes will be added as seen on Trakt
        
        if choice == True:
        
            error = None
            
            # refresh connection (don't want to get tcp timeout)
            conn = getTraktConnection()
            
            for i in range(0, len(set_as_seen)):
                if xbmc.abortRequested: raise SystemExit()
                data = traktJsonRequest('POST', '/show/episode/seen/%%API_KEY%%', {'tvdb_id': set_as_seen[i]['tvdb_id'], 'title': set_as_seen[i]['title'], 'year': set_as_seen[i]['year'], 'episodes': set_as_seen[i]['episodes']}, returnStatus = True, conn = conn)
                if data['status'] == 'failure':
                    Debug("Error uploading tvshow: " + repr(set_as_seen[i]['title']) + ": " + str(data['error']))
                    error = data['error']
                else:
                    Debug("Successfully uploaded tvshow " + repr(set_as_seen[i]['title']) + ": " + str(data['message']))
                
            if error == None:
                if daemon:
                    notification("Trakt Utilities", __language__(1137).encode( "utf-8", "ignore" )) # Episodes sucessfully updated to Trakt
                else:
                    xbmcgui.Dialog().ok("Trakt Utilities", __language__(1137).encode( "utf-8", "ignore" )) # Episodes sucessfully updated to Trakt
            else:
                if daemon:
                    notification("Trakt Utilities", __language__(1145).encode( "utf-8", "ignore" ) + str(error)) # Error uploading seen TVShows
                else:
                    xbmcgui.Dialog().ok("Trakt Utilities", __language__(1145).encode( "utf-8", "ignore" ), error) # Error uploading seen TVShows
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1146).encode( "utf-8", "ignore" )) # No new seen episodes in XBMC library to update

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", __language__(1148).encode( "utf-8", "ignore" )) # Checking Trakt Database for new seen Episodes
    progress_count = 0
    
    xbmc_tvshows_tvdbid = {}
    
    # make xbmc tvshows searchable by tvdbid
    for i in range(0, xbmc_tvshows['limits']['total']):
        try:
            xbmc_tvshows_tvdbid[xbmc_tvshows['tvshows'][i]['imdbnumber']] = xbmc_tvshows['tvshows'][i]
        except KeyError:
            continue

    set_as_seen = []
    tvshow_to_set = {}

    # add seen episodes to xbmc
    for tvshow in trakt_tvshowlist:
        if xbmc.abortRequested: raise SystemExit()
        if not daemon:
            progress.update(100 / len(trakt_tvshowlist) * progress_count)
            progress_count += 1
            if progress.iscanceled():
                xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                return
        try:
            tvshow_to_set['title'] = tvshow['title']
            tvshow_to_set['tvdb_id'] = tvshow['tvdb_id']
        except KeyError:
            continue # missing data, skip to next tvshow
            
        tvshow_to_set['episodes'] = []
        
        Debug("checking: " + repr(tvshow['title']))
        
        trakt_seasons = tvshow['seasons']
        for trakt_season in trakt_seasons:
            seasonid = trakt_season['season']
            episodes = trakt_season['episodes']
            try:
                xbmc_tvshow = xbmc_tvshows_tvdbid[tvshow['tvdb_id']]
            except KeyError:
                Debug("tvshow not found in xbmc database")
                continue # tvshow not in xbmc library

            xbmc_episodes = getEpisodesFromXBMC(xbmc_tvshow, seasonid)
            if xbmc_episodes['limits']['total'] > 0:
                # sort xbmc episodes by id
                xbmc_episodes_byid = {}
                for i in xbmc_episodes['episodes']:
                    xbmc_episodes_byid[i['episode']] = i
                
                for episode in episodes:
                    xbmc_episode = None
                    try:
                        xbmc_episode = xbmc_episodes_byid[episode]
                    except KeyError:
                        pass
                    try:
                        if xbmc_episode != None:
                            if xbmc_episode['playcount'] <= 0:
                                tvshow_to_set['episodes'].append([seasonid, episode])
                    except KeyError:
                        # episode not in xbmc database
                        pass
        
        if len(tvshow_to_set['episodes']) > 0:
            set_as_seen.append(tvshow_to_set)
        tvshow_to_set = {}
    
    if not daemon:
        progress.close()
    
    count = 0
    set_as_seen_titles = ""
    Debug ("set as seen length: " + str(len(set_as_seen)))
    for i in range(0, len(set_as_seen)):
        if i == 0:
            set_as_seen_titles += set_as_seen[i]['title']
        elif i > 5:
            break
        else:
            set_as_seen_titles += ", " + set_as_seen[i]['title']
        for j in range(0, len(set_as_seen[i]['episodes'])):
            count += 1
    
    # add seen episodes to xbmc library:
    if count > 0:
        if daemon:
            choice = True
        else:
            choice = xbmcgui.Dialog().yesno("Trakt Utilities", str(count) + " " + __language__(1149).encode( "utf-8", "ignore" ), set_as_seen_titles) # TVShow Episodes will be set as seen on XBMC
        
        if choice == True:
            
            if not daemon:
                progress = xbmcgui.DialogProgress()
                progress.create("Trakt Utilities", __language__(1150).encode( "utf-8", "ignore" )) # updating XBMC Database
            progress_count = 0

            for tvshow in set_as_seen:
                if xbmc.abortRequested: raise SystemExit()
                if not daemon:
                    progress.update(100 / len(set_as_seen) * progress_count)
                    progress_count += 1
                    if progress.iscanceled():
                        xbmcgui.Dialog().ok("Trakt Utilities", __language__(1134).encode( "utf-8", "ignore" )) # Progress Aborted
                        progress.close()
                        return
                    
                for episode in tvshow['episodes']:
                    setXBMCEpisodePlaycount(tvshow['tvdb_id'], episode[0], episode[1], 1)
    
            if not daemon:
                progress.close()
    else:
        if not daemon:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1151).encode( "utf-8", "ignore" )) # No new seen episodes on Trakt to update

########NEW FILE########
__FILENAME__ = trending
# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
import time, socket

try: import simplejson as json
except ImportError: import json

from utilities import *

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )
https = __settings__.getSetting('https')

if (https == 'true'):
    conn = httplib.HTTPSConnection('api.trakt.tv')
else:
    conn = httplib.HTTPConnection('api.trakt.tv')

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def showTrendingMovies():
    
    movies = getTrendingMoviesFromTrakt()
    watchlist = traktMovieListByImdbID(getWatchlistMoviesFromTrakt())
    
    if movies == None: # movies = None => there was an error
        return # error already displayed in utilities.py
    
    if len(movies) == 0:
        xbmcgui.Dialog().ok("Trakt Utilities", "there are no trending movies")
        return
    
    for movie in movies:
        if movie['imdb_id'] in watchlist:
            movie['watchlist'] = True
        else:
            movie['watchlist'] = False
    
    # display trending movie list
    import windows
    ui = windows.MoviesWindow("movies.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(movies, 'trending')
    ui.doModal()
    del ui

def showTrendingTVShows():

    tvshows = getTrendingTVShowsFromTrakt()
    watchlist = traktShowListByTvdbID(getWatchlistTVShowsFromTrakt())
    
    if tvshows == None: # tvshows = None => there was an error
        return # error already displayed in utilities.py
    
    if len(tvshows) == 0:
        xbmcgui.Dialog().ok("Trakt Utilities", "there are no trending tv shows")
        return
    
    for tvshow in tvshows:
        if tvshow['imdb_id'] in watchlist:
            tvshow['watchlist'] = True
        else:
            tvshow['watchlist'] = False
    
    # display trending tv shows
    import windows
    ui = windows.TVShowsWindow("tvshows.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(tvshows, 'trending')
    ui.doModal()
    del ui

########NEW FILE########
__FILENAME__ = utilities
# -*- coding: utf-8 -*-
# 

import os, sys
import xbmc,xbmcaddon,xbmcgui
import time, socket

try: import simplejson as json
except ImportError: import json

from nbhttpconnection import *
from nbhttpsconnection import *

import urllib, re

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'

username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def Debug(msg, force=False):
    if (debug == 'true' or force):
        try:
            print "Trakt Utilities: " + msg
        except UnicodeEncodeError:
            print "Trakt Utilities: " + msg.encode( "utf-8", "ignore" )

#This class needs debug
from raw_xbmc_database import RawXbmcDb

def notification( header, message, time=5000, icon=__settings__.getAddonInfo( "icon" ) ):
    xbmc.executebuiltin( "XBMC.Notification(%s,%s,%i,%s)" % ( header, message, time, icon ) )

def checkSettings(daemon=False):
    if username == "":
        if daemon:
            notification("Trakt Utilities", __language__(1106).encode( "utf-8", "ignore" )) # please enter your Username and Password in settings
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1106).encode( "utf-8", "ignore" )) # please enter your Username and Password in settings
            __settings__.openSettings()
        return False
    elif __settings__.getSetting("password") == "":
        if daemon:
            notification("Trakt Utilities", __language__(1107).encode( "utf-8", "ignore" )) # please enter your Password in settings
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1107).encode( "utf-8", "ignore" )) # please enter your Password in settings
            __settings__.openSettings()
        return False
    
    data = traktJsonRequest('POST', '/account/test/%%API_KEY%%', silent=True)
    if data == None: #Incorrect trakt login details
        if daemon:
            notification("Trakt Utilities", __language__(1110).encode( "utf-8", "ignore" )) # please enter your Password in settings
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1110).encode( "utf-8", "ignore" )) # please enter your Password in settings
            __settings__.openSettings()
        return False
        
    return True

# SQL string quote escaper
def xcp(s):
    return re.sub('''(['])''', r"''", unicode(s))

# get a connection to trakt
def getTraktConnection():
    https = __settings__.getSetting('https')
    try:
        if (https == 'true'):
            conn = NBHTTPSConnection('api.trakt.tv')
        else:
            conn = NBHTTPConnection('api.trakt.tv')
    except socket.timeout:
        Debug("getTraktConnection: can't connect to trakt - timeout")
        notification("Trakt Utilities", __language__(1108).encode( "utf-8", "ignore" ) + ": timeout") # can't connect to trakt
        return None
    return conn
    
# make a JSON api request to trakt
# method: http method (GET or POST)
# req: REST request (ie '/user/library/movies/all.json/%%API_KEY%%/%%USERNAME%%')
# args: arguments to be passed by POST JSON (only applicable to POST requests), default:{}
# returnStatus: when unset or set to false the function returns None apon error and shows a notification,
#   when set to true the function returns the status and errors in ['error'] as given to it and doesn't show the notification,
#   use to customise error notifications
# anon: anonymous (dont send username/password), default:False
# connection: default it to make a new connection but if you want to keep the same one alive pass it here
# silent: default is False, when true it disable any error notifications (but not debug messages)
# passVersions: default is False, when true it passes extra version information to trakt to help debug problems
def traktJsonRequest(method, req, args={}, returnStatus=False, anon=False, conn=False, silent=False, passVersions=False):
    closeConnection = False
    if conn == False:
        conn = getTraktConnection()
        closeConnection = True
    if conn == None:
        if returnStatus:
            data = {}
            data['status'] = 'failure'
            data['error'] = 'Unable to connect to trakt'
            return data
        return None

    try:
        req = req.replace("%%API_KEY%%",apikey)
        req = req.replace("%%USERNAME%%",username)
        if method == 'POST':
            if not anon:
                args['username'] = username
                args['password'] = pwd
            if passVersions:
                args['plugin_version'] = __settings__.getAddonInfo("version")
                args['media_center'] = 'xbmc'
                args['media_center_version'] = xbmc.getInfoLabel("system.buildversion")
                args['media_center_date'] = xbmc.getInfoLabel("system.builddate")
            jdata = json.dumps(args)
            conn.request('POST', req, jdata)
        elif method == 'GET':
            conn.request('GET', req)
        else:
            return None
        Debug("trakt json url: "+req)
    except socket.error:
        Debug("traktQuery: can't connect to trakt")
        if not silent: notification("Trakt Utilities", __language__(1108).encode( "utf-8", "ignore" )) # can't connect to trakt
        if returnStatus:
            data = {}
            data['status'] = 'failure'
            data['error'] = 'Socket error, unable to connect to trakt'
            return data;
        return None
     
    conn.go()
    
    while True:
        if xbmc.abortRequested:
            Debug("Broke loop due to abort")
            if returnStatus:
                data = {}
                data['status'] = 'failure'
                data['error'] = 'Abort requested, not waiting for responce'
                return data;
            return None
        if conn.hasResult():
            break
        time.sleep(0.1)
    
    response = conn.getResult()
    raw = response.read()
    if closeConnection:
        conn.close()
    
    try:
        data = json.loads(raw)
    except ValueError:
        Debug("traktQuery: Bad JSON responce: "+raw)
        if returnStatus:
            data = {}
            data['status'] = 'failure'
            data['error'] = 'Bad responce from trakt'
            return data
        if not silent: notification("Trakt Utilities", __language__(1109).encode( "utf-8", "ignore" ) + ": Bad responce from trakt") # Error
        return None
    
    if 'status' in data:
        if data['status'] == 'failure':
            Debug("traktQuery: Error: " + str(data['error']))
            if returnStatus:
                return data;
            if not silent: notification("Trakt Utilities", __language__(1109).encode( "utf-8", "ignore" ) + ": " + str(data['error'])) # Error
            return None
    
    return data
   
# get movies from trakt server
def getMoviesFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/movies/all.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getMoviesFromTrakt()'")
    return data

# get movie that are listed as in the users collection from trakt server
def getMovieCollectionFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/movies/collection.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getMovieCollectionFromTrakt()'")
    return data

# get easy access to movie by imdb_id
def traktMovieListByImdbID(data):
    trakt_movies = {}

    for i in range(0, len(data)):
        if data[i]['imdb_id'] == "": continue
        trakt_movies[data[i]['imdb_id']] = data[i]
        
    return trakt_movies

# get easy access to tvshow by tvdb_id
def traktShowListByTvdbID(data):
    trakt_tvshows = {}

    for i in range(0, len(data)):
        trakt_tvshows[data[i]['tvdb_id']] = data[i]
        
    return trakt_tvshows

# get seen tvshows from trakt server
def getWatchedTVShowsFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/shows/watched.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchedTVShowsFromTrakt()'")
    return data

# set episodes seen on trakt
def setEpisodesSeenOnTrakt(tvdb_id, title, year, episodes):
    data = traktJsonRequest('POST', '/show/episode/seen/%%API_KEY%%', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'episodes': episodes})
    if data == None:
        Debug("Error in request from 'setEpisodeSeenOnTrakt()'")
    return data

# set episodes unseen on trakt
def setEpisodesUnseenOnTrakt(tvdb_id, title, year, episodes):
    data = traktJsonRequest('POST', '/show/episode/unseen/%%API_KEY%%', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'episodes': episodes})
    if data == None:
        Debug("Error in request from 'setEpisodesUnseenOnTrakt()'")
    return data

# set movies seen on trakt
#  - movies, required fields are 'plays', 'last_played' and 'title', 'year' or optionally 'imdb_id'
def setMoviesSeenOnTrakt(movies):
    data = traktJsonRequest('POST', '/movie/seen/%%API_KEY%%', {'movies': movies})
    if data == None:
        Debug("Error in request from 'setMoviesSeenOnTrakt()'")
    return data

# set movies unseen on trakt
#  - movies, required fields are 'plays', 'last_played' and 'title', 'year' or optionally 'imdb_id'
def setMoviesUnseenOnTrakt(movies):
    data = traktJsonRequest('POST', '/movie/unseen/%%API_KEY%%', {'movies': movies})
    if data == None:
        Debug("Error in request from 'setMoviesUnseenOnTrakt()'")
    return data

# get tvshow collection from trakt server
def getTVShowCollectionFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/shows/collection.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getTVShowCollectionFromTrakt()'")
    return data
    
# get tvshows from XBMC
def getTVShowsFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows','params':{'properties': ['title', 'year', 'imdbnumber', 'playcount']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getTVShowsFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        return result['result']
    except KeyError:
        Debug("getTVShowsFromXBMC: KeyError: result['result']")
        return None
    
# get seasons for a given tvshow from XBMC
def getSeasonsFromXBMC(tvshow):
    Debug("getSeasonsFromXBMC: "+str(tvshow))
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetSeasons','params':{'tvshowid': tvshow['tvshowid']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getSeasonsFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']
    except KeyError:
        Debug("getSeasonsFromXBMC: KeyError: result['result']")
        return None
    
# get episodes for a given tvshow / season from XBMC
def getEpisodesFromXBMC(tvshow, season):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes','params':{'tvshowid': tvshow['tvshowid'], 'season': season, 'properties': ['playcount', 'episode']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    # check for error
    try:
        error = result['error']
        Debug("getEpisodesFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']
    except KeyError:
        Debug("getEpisodesFromXBMC: KeyError: result['result']")
        return None

# get a single episode from xbmc given the id
def getEpisodeDetailsFromXbmc(libraryId, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails','params':{'episodeid': libraryId, 'properties': fields}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    # check for error
    try:
        error = result['error']
        Debug("getEpisodeDetailsFromXbmc: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']['episodedetails']
    except KeyError:
        Debug("getEpisodeDetailsFromXbmc: KeyError: result['result']['episodedetails']")
        return None

# get movies from XBMC
def getMoviesFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies','params':{'properties': ['title', 'year', 'originaltitle', 'imdbnumber', 'playcount', 'lastplayed']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getMoviesFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        return result['result']['movies']
        Debug("getMoviesFromXBMC: KeyError: result['result']['movies']")
    except KeyError:
        return None

# get a single movie from xbmc given the id
def getMovieDetailsFromXbmc(libraryId, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails','params':{'movieid': libraryId, 'properties': fields}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    # check for error
    try:
        error = result['error']
        Debug("getMovieDetailsFromXbmc: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']['moviedetails']
    except KeyError:
        Debug("getMovieDetailsFromXbmc: KeyError: result['result']['moviedetails']")
        return None

# sets the playcount of a given movie by imdbid
def setXBMCMoviePlaycount(imdb_id, playcount):

    # httpapi till jsonrpc supports playcount update
    # c09 => IMDB ID
    match = RawXbmcDb.query(
    "SELECT movie.idFile FROM movie"+
    " WHERE movie.c09='%(imdb_id)s'" % {'imdb_id':xcp(imdb_id)})
    
    if not match:
        #add error message here
        return
    
    try:
        match[0][0]
    except KeyError:
        return
    
    RawXbmcDb.execute(
    "UPDATE files"+
    " SET playcount=%(playcount)d" % {'playcount':int(playcount)}+
    " WHERE idFile=%(idFile)s" % {'idFile':xcp(match[0][0])})

# sets the playcount of a given episode by tvdb_id
def setXBMCEpisodePlaycount(tvdb_id, seasonid, episodeid, playcount):
    # httpapi till jsonrpc supports playcount update
    RawXbmcDb.execute(
    "UPDATE files"+
    " SET playcount=%(playcount)s" % {'playcount':xcp(playcount)}+
    " WHERE idFile IN ("+
    "  SELECT idFile"+
    "  FROM episode"+
    "  INNER JOIN tvshowlinkepisode ON episode.idEpisode = tvshowlinkepisode.idEpisode"+
    "   INNER JOIN tvshow ON tvshowlinkepisode.idShow = tvshow.idShow"+
    "   WHERE tvshow.c12='%(tvdb_id)s'" % {'tvdb_id':xcp(tvdb_id)}+
    "    AND episode.c12='%(seasonid)s'" % {'seasonid':xcp(seasonid)}+
    "    AND episode.c13='%(episodeid)s'" % {'episodeid':xcp(episodeid)}+
    " )")
    
# get current video being played from XBMC
def getCurrentPlayingVideoFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetActivePlayers','params':{}, 'id': 1})
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    # check for error
    try:
        error = result['error']
        Debug("[Util] getCurrentPlayingVideoFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        for player in result['result']:
            if player['type'] == 'video':
                rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetProperties','params':{'playerid': player['playerid'], 'properties':['playlistid', 'position']}, 'id': 1})
                result2 = xbmc.executeJSONRPC(rpccmd)
                result2 = json.loads(result2)
                # check for error
                try:
                    error = result2['error']
                    Debug("[Util] getCurrentPlayingVideoFromXBMC, Player.GetProperties: " + str(error))
                    return None
                except KeyError:
                    pass # no error
                playlistid = result2['result']['playlistid']
                position = result2['result']['position']
                
                rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Playlist.GetItems','params':{'playlistid': playlistid}, 'id': 1})
                result2 = xbmc.executeJSONRPC(rpccmd)
                result2 = json.loads(result2)
                # check for error
                try:
                    error = result2['error']
                    Debug("[Util] getCurrentPlayingVideoFromXBMC, Playlist.GetItems: " + str(error))
                    return None
                except KeyError:
                    pass # no error
                Debug("Current playlist: "+str(result2['result']))
                
                return result2['result'][position]
        Debug("[Util] getCurrentPlayingVideoFromXBMC: No current video player")
        return None
    except KeyError:
        Debug("[Util] getCurrentPlayingVideoFromXBMC: KeyError")
        return None
        
# get the length of the current video playlist being played from XBMC
def getPlaylistLengthFromXBMCPlayer(playerid):
    if playerid == -1:
        return 1 #Default player (-1) can't be checked properly
    if playerid < 0 or playerid > 2:
        Debug("[Util] getPlaylistLengthFromXBMCPlayer, invalid playerid: "+str(playerid))
        return 0
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetProperties','params':{'playerid': playerid, 'properties':['playlistid']}, 'id': 1})
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    # check for error
    try:
        error = result['error']
        Debug("[Util] getPlaylistLengthFromXBMCPlayer, Player.GetProperties: " + str(error))
        return 0
    except KeyError:
        pass # no error
    playlistid = result['result']['playlistid']
    
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Playlist.GetProperties','params':{'playlistid': playlistid, 'properties': ['size']}, 'id': 1})
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    # check for error
    try:
        error = result['error']
        Debug("[Util] getPlaylistLengthFromXBMCPlayer, Playlist.GetProperties: " + str(error))
        return 0
    except KeyError:
        pass # no error
    
    return result['result']['size']

def getMovieIdFromXBMC(imdb_id, title):
    # httpapi till jsonrpc supports searching for a single movie
    # Get id of movie by movies IMDB
    Debug("Searching for movie: "+imdb_id+", "+title)
    
    match = RawXbmcDb.query(
    " SELECT idMovie FROM movie"+
    "  WHERE c09='%(imdb_id)s'" % {'imdb_id':imdb_id}+
    " UNION"+
    " SELECT idMovie FROM movie"+
    "  WHERE upper(c00)='%(title)s'" % {'title':xcp(title.upper())}+
    " LIMIT 1")
    
    if not match:
        Debug("getMovieIdFromXBMC: cannot find movie in database")
        return -1
        
    return match[0]

def getShowIdFromXBMC(tvdb_id, title):
    # httpapi till jsonrpc supports searching for a single show
    # Get id of show by shows tvdb id
    
    Debug("Searching for show: "+str(tvdb_id)+", "+title)
    
    match = RawXbmcDb.query(
    " SELECT idShow FROM tvshow"+
    "  WHERE c12='%(tvdb_id)s'" % {'tvdb_id':xcp(tvdb_id)}+
    " UNION"+
    " SELECT idShow FROM tvshow"+
    "  WHERE upper(c00)='%(title)s'" % {'title':xcp(title.upper())}+
    " LIMIT 1")
    
    if not match:
        Debug("getShowIdFromXBMC: cannot find movie in database")
        return -1
        
    return match[0]

# returns list of movies from watchlist
def getWatchlistMoviesFromTrakt():
    data = traktJsonRequest('POST', '/user/watchlist/movies.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchlistMoviesFromTrakt()'")
    return data

# returns list of tv shows from watchlist
def getWatchlistTVShowsFromTrakt():
    data = traktJsonRequest('POST', '/user/watchlist/shows.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchlistTVShowsFromTrakt()'")
    return data

# add an array of movies to the watch-list
def addMoviesToWatchlist(data):
    movies = []
    for item in data:
        movie = {}
        if "imdb_id" in item:
            movie["imdb_id"] = item["imdb_id"]
        if "tmdb_id" in item:
            movie["tmdb_id"] = item["tmdb_id"]
        if "title" in item:
            movie["title"] = item["title"]
        if "year" in item:
            movie["year"] = item["year"]
        movies.append(movie)
    
    data = traktJsonRequest('POST', '/movie/watchlist/%%API_KEY%%', {"movies":movies})
    if data == None:
        Debug("Error in request from 'addMoviesToWatchlist()'")
    return data

# remove an array of movies from the watch-list
def removeMoviesFromWatchlist(data):
    movies = []
    for item in data:
        movie = {}
        if "imdb_id" in item:
            movie["imdb_id"] = item["imdb_id"]
        if "tmdb_id" in item:
            movie["tmdb_id"] = item["tmdb_id"]
        if "title" in item:
            movie["title"] = item["title"]
        if "year" in item:
            movie["year"] = item["year"]
        movies.append(movie)
    
    data = traktJsonRequest('POST', '/movie/unwatchlist/%%API_KEY%%', {"movies":movies})
    if data == None:
        Debug("Error in request from 'removeMoviesFromWatchlist()'")
    return data

# add an array of tv shows to the watch-list
def addTVShowsToWatchlist(data):
    shows = []
    for item in data:
        show = {}
        if "tvdb_id" in item:
            show["tvdb_id"] = item["tvdb_id"]
        if "imdb_id" in item:
            show["tmdb_id"] = item["imdb_id"]
        if "title" in item:
            show["title"] = item["title"]
        if "year" in item:
            show["year"] = item["year"]
        shows.append(show)
    
    data = traktJsonRequest('POST', '/show/watchlist/%%API_KEY%%', {"shows":shows})
    if data == None:
        Debug("Error in request from 'addMoviesToWatchlist()'")
    return data

# remove an array of tv shows from the watch-list
def removeTVShowsFromWatchlist(data):
    shows = []
    for item in data:
        show = {}
        if "tvdb_id" in item:
            show["tvdb_id"] = item["tvdb_id"]
        if "imdb_id" in item:
            show["imdb_id"] = item["imdb_id"]
        if "title" in item:
            show["title"] = item["title"]
        if "year" in item:
            show["year"] = item["year"]
        shows.append(show)
    
    data = traktJsonRequest('POST', '/show/unwatchlist/%%API_KEY%%', {"shows":shows})
    if data == None:
        Debug("Error in request from 'removeMoviesFromWatchlist()'")
    return data

#Set the rating for a movie on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateMovieOnTrakt(imdbid, title, year, rating):
    if not (rating in ("love", "hate", "unrate")):
        #add error message
        return
    
    Debug("Rating movie:" + rating)
    
    data = traktJsonRequest('POST', '/rate/movie/%%API_KEY%%', {'imdb_id': imdbid, 'title': title, 'year': year, 'rating': rating})
    if data == None:
        Debug("Error in request from 'rateMovieOnTrakt()'")
    
    if (rating == "unrate"):
        notification("Trakt Utilities", __language__(1166).encode( "utf-8", "ignore" )) # Rating removed successfully
    else :
        notification("Trakt Utilities", __language__(1167).encode( "utf-8", "ignore" )) # Rating submitted successfully
    
    return data

#Get the rating for a movie from trakt
def getMovieRatingFromTrakt(imdbid, title, year):
    if imdbid == "" or imdbid == None:
        return None #would be nice to be smarter in this situation
    
    data = traktJsonRequest('POST', '/movie/summary.json/%%API_KEY%%/'+str(imdbid))
    if data == None:
        Debug("Error in request from 'getMovieRatingFromTrakt()'")
        return None
        
    if 'rating' in data:
        return data['rating']
        
    print data
    Debug("Error in request from 'getMovieRatingFromTrakt()'")
    return None

#Set the rating for a tv episode on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateEpisodeOnTrakt(tvdbid, title, year, season, episode, rating):
    if not (rating in ("love", "hate", "unrate")):
        #add error message
        return
    
    Debug("Rating episode:" + rating)
    
    data = traktJsonRequest('POST', '/rate/episode/%%API_KEY%%', {'tvdb_id': tvdbid, 'title': title, 'year': year, 'season': season, 'episode': episode, 'rating': rating})
    if data == None:
        Debug("Error in request from 'rateEpisodeOnTrakt()'")
    
    if (rating == "unrate"):
        notification("Trakt Utilities", __language__(1166).encode( "utf-8", "ignore" )) # Rating removed successfully
    else :
        notification("Trakt Utilities", __language__(1167).encode( "utf-8", "ignore" )) # Rating submitted successfully
    
    return data
    
#Get the rating for a tv episode from trakt
def getEpisodeRatingFromTrakt(tvdbid, title, year, season, episode):
    if tvdbid == "" or tvdbid == None:
        return None #would be nice to be smarter in this situation
    
    data = traktJsonRequest('POST', '/show/episode/summary.json/%%API_KEY%%/'+str(tvdbid)+"/"+season+"/"+episode)
    if data == None:
        Debug("Error in request from 'getEpisodeRatingFromTrakt()'")
        return None
        
    if 'rating' in data:
        return data['rating']
        
    print data
    Debug("Error in request from 'getEpisodeRatingFromTrakt()'")
    return None

#Set the rating for a tv show on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateShowOnTrakt(tvdbid, title, year, rating):
    if not (rating in ("love", "hate", "unrate")):
        #add error message
        return
    
    Debug("Rating show:" + rating)
    
    data = traktJsonRequest('POST', '/rate/show/%%API_KEY%%', {'tvdb_id': tvdbid, 'title': title, 'year': year, 'rating': rating})
    if data == None:
        Debug("Error in request from 'rateShowOnTrakt()'")
    
    if (rating == "unrate"):
        notification("Trakt Utilities", __language__(1166).encode( "utf-8", "ignore" )) # Rating removed successfully
    else :
        notification("Trakt Utilities", __language__(1167).encode( "utf-8", "ignore" )) # Rating submitted successfully
    
    return data

#Get the rating for a tv show from trakt
def getShowRatingFromTrakt(tvdbid, title, year):
    if tvdbid == "" or tvdbid == None:
        return None #would be nice to be smarter in this situation
    
    data = traktJsonRequest('POST', '/show/summary.json/%%API_KEY%%/'+str(tvdbid))
    if data == None:
        Debug("Error in request from 'getShowRatingFromTrakt()'")
        return None
        
    if 'rating' in data:
        return data['rating']
        
    print data
    Debug("Error in request from 'getShowRatingFromTrakt()'")
    return None

def getRecommendedMoviesFromTrakt():
    data = traktJsonRequest('POST', '/recommendations/movies/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getRecommendedMoviesFromTrakt()'")
    return data

def getRecommendedTVShowsFromTrakt():
    data = traktJsonRequest('POST', '/recommendations/shows/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getRecommendedTVShowsFromTrakt()'")
    return data

def getTrendingMoviesFromTrakt():
    data = traktJsonRequest('GET', '/movies/trending.json/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getTrendingMoviesFromTrakt()'")
    return data

def getTrendingTVShowsFromTrakt():
    data = traktJsonRequest('GET', '/shows/trending.json/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getTrendingTVShowsFromTrakt()'")
    return data

def getFriendsFromTrakt():
    data = traktJsonRequest('POST', '/user/friends.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getFriendsFromTrakt()'")
    return data

def getWatchingFromTraktForUser(name):
    data = traktJsonRequest('POST', '/user/watching.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchingFromTraktForUser()'")
    return data

def playMovieById(idMovie):
    # httpapi till jsonrpc supports selecting a single movie
    Debug("Play Movie requested for id: "+str(idMovie))
    if idMovie == -1:
        return # invalid movie id
    else:
        rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.Open', 'params': {'item': {'movieid': int(idMovie)}}, 'id': 1})
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
        
        # check for error
        try:
            error = result['error']
            Debug("playMovieById, Player.Open: " + str(error))
            return None
        except KeyError:
            pass # no error
            
        try:
            if result['result'] == "OK":
                if xbmc.Player().isPlayingVideo():
                    return True
            notification("Trakt Utilities", __language__(1302).encode( "utf-8", "ignore" )) # Unable to play movie
        except KeyError:
            Debug("playMovieById, VideoPlaylist.Play: KeyError")
            return None

###############################
##### Scrobbling to trakt #####
###############################

#tell trakt that the user is watching a movie
def watchingMovieOnTrakt(imdb_id, title, year, duration, percent):
    responce = traktJsonRequest('POST', '/movie/watching/%%API_KEY%%', {'imdb_id': imdb_id, 'title': title, 'year': year, 'duration': duration, 'progress': percent}, passVersions=True)
    if responce == None:
        Debug("Error in request from 'watchingMovieOnTrakt()'")
    return responce

#tell trakt that the user is watching an episode
def watchingEpisodeOnTrakt(tvdb_id, title, year, season, episode, duration, percent):
    responce = traktJsonRequest('POST', '/show/watching/%%API_KEY%%', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent}, passVersions=True)
    if responce == None:
        Debug("Error in request from 'watchingEpisodeOnTrakt()'")
    return responce

#tell trakt that the user has stopped watching a movie
def cancelWatchingMovieOnTrakt():
    responce = traktJsonRequest('POST', '/movie/cancelwatching/%%API_KEY%%')
    if responce == None:
        Debug("Error in request from 'cancelWatchingMovieOnTrakt()'")
    return responce

#tell trakt that the user has stopped an episode
def cancelWatchingEpisodeOnTrakt():
    responce = traktJsonRequest('POST', '/show/cancelwatching/%%API_KEY%%')
    if responce == None:
        Debug("Error in request from 'cancelWatchingEpisodeOnTrakt()'")
    return responce

#tell trakt that the user has finished watching an movie
def scrobbleMovieOnTrakt(imdb_id, title, year, duration, percent):
    responce = traktJsonRequest('POST', '/movie/scrobble/%%API_KEY%%', {'imdb_id': imdb_id, 'title': title, 'year': year, 'duration': duration, 'progress': percent}, passVersions=True)
    if responce == None:
        Debug("Error in request from 'scrobbleMovieOnTrakt()'")
    return responce

#tell trakt that the user has finished watching an episode
def scrobbleEpisodeOnTrakt(tvdb_id, title, year, season, episode, duration, percent):
    responce = traktJsonRequest('POST', '/show/scrobble/%%API_KEY%%', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent}, passVersions=True)
    if responce == None:
        Debug("Error in request from 'scrobbleEpisodeOnTrakt()'")
    return responce


"""
ToDo:


"""


"""
for later:
First call "Player.GetActivePlayers" to determine the currently active player (audio, video or picture).
If it is audio or video call Audio/VideoPlaylist.GetItems and read the "current" field to get the position of the
currently playling item in the playlist. The "items" field contains an array of all items in the playlist and "items[current]" is
the currently playing file. You can also tell jsonrpc which fields to return for every item in the playlist and therefore you'll have all the information you need.

"""

########NEW FILE########
__FILENAME__ = watchlist
# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
import time, socket

try: import simplejson as json
except ImportError: import json

from utilities import *

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

apikey = '0a698a20b222d0b8637298f6920bf03a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )
https = __settings__.getSetting('https')

if (https == 'true'):
    conn = httplib.HTTPSConnection('api.trakt.tv')
else:
    conn = httplib.HTTPConnection('api.trakt.tv')

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

# list watchlist movies
def showWatchlistMovies():
    
    movies = getWatchlistMoviesFromTrakt()
    
    if movies == None: # movies = None => there was an error
        return # error already displayed in utilities.py
    
    if len(movies) == 0:
        xbmcgui.Dialog().ok(__language__(1201).encode( "utf-8", "ignore" ), __language__(1160).encode( "utf-8", "ignore" )) # Trakt Utilities, there are no movies in your watchlist
        return
        
    # display watchlist movie list
    import windows
    ui = windows.MoviesWindow("movies.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(movies, 'watchlist')
    ui.doModal()
    del ui

# list watchlist tv shows
def showWatchlistTVShows():

    tvshows = getWatchlistTVShowsFromTrakt()
    
    if tvshows == None: # tvshows = None => there was an error
        return # error already displayed in utilities.py
    
    if len(tvshows) == 0:
        xbmcgui.Dialog().ok(__language__(1201).encode( "utf-8", "ignore" ), __language__(1161).encode( "utf-8", "ignore" )) # Trakt Utilities, there are no tv shows in your watchlist
        return
    
    # display watchlist tv shows
    import windows
    ui = windows.TVShowsWindow("tvshows.xml", __settings__.getAddonInfo('path'), "Default")
    ui.initWindow(tvshows, 'watchlist')
    ui.doModal()
    del ui
    

########NEW FILE########
__FILENAME__ = windows
# -*- coding: utf-8 -*-
# 

import xbmc,xbmcaddon,xbmcgui
from utilities import *
from rating import *

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString

BACKGROUND = 102
TITLE = 103
OVERVIEW = 104
POSTER = 105
PLAY_BUTTON = 106
YEAR = 107
RUNTIME = 108
TAGLINE = 109
MOVIE_LIST = 110
TVSHOW_LIST = 110
RATING = 111
WATCHERS = 112

RATE_SCENE = 98
RATE_TITLE = 100
RATE_CUR_NO_RATING = 101
RATE_CUR_LOVE = 102
RATE_CUR_HATE = 103
RATE_SKIP_RATING = 104
RATE_LOVE_BTN = 105
RATE_HATE_BTN = 106
RATE_RATE_SHOW_BG = 107
RATE_RATE_SHOW_BTN = 108

#get actioncodes from keymap.xml
ACTION_PARENT_DIRECTORY = 9
ACTION_PREVIOUS_MENU = 10
ACTION_SELECT_ITEM = 7
ACTION_CONTEXT_MENU = 117

class MoviesWindow(xbmcgui.WindowXML):

    movies = None
    type = 'basic'

    def initWindow(self, movies, type):
        self.movies = movies
        self.type = type
        
    def onInit(self):
        self.getControl(MOVIE_LIST).reset()
        if self.movies != None:
            for movie in self.movies:
                li = xbmcgui.ListItem(movie['title'], '', movie['images']['poster'])
                if not ('idMovie' in movie):
                    movie['idMovie'] = getMovieIdFromXBMC(movie['imdb_id'], movie['title'])
                if movie['idMovie'] != -1:
                    li.setProperty('Available','true')
                if self.type <> 'watchlist':
                    if 'watchlist' in movie:
                        if movie['watchlist']:
                            li.setProperty('Watchlist','true')
                self.getControl(MOVIE_LIST).addItem(li)
            self.setFocus(self.getControl(MOVIE_LIST))
            self.listUpdate()
        else:
            Debug("MoviesWindow: Error: movies array is empty")
            self.close()

    def listUpdate(self):
        try:
            current = self.getControl(MOVIE_LIST).getSelectedPosition()
        except TypeError:
            return # ToDo: error output
        
        try:
            self.getControl(BACKGROUND).setImage(self.movies[current]['images']['fanart'])
        except KeyError:
            Debug("KeyError for Backround")
        except TypeError:
            Debug("TypeError for Backround")
        try:
            self.getControl(TITLE).setLabel(self.movies[current]['title'])
        except KeyError:
            Debug("KeyError for Title")
            self.getControl(TITLE).setLabel("")
        except TypeError:
            Debug("TypeError for Title")
        try:
            self.getControl(OVERVIEW).setText(self.movies[current]['overview'])
        except KeyError:
            Debug("KeyError for Overview")
            self.getControl(OVERVIEW).setText("")
        except TypeError:
            Debug("TypeError for Overview")
        try:
            self.getControl(YEAR).setLabel("Year: " + str(self.movies[current]['year']))
        except KeyError:
            Debug("KeyError for Year")
            self.getControl(YEAR).setLabel("")
        except TypeError:
            Debug("TypeError for Year")
        try:
            self.getControl(RUNTIME).setLabel("Runtime: " + str(self.movies[current]['runtime']) + " Minutes")
        except KeyError:
            Debug("KeyError for Runtime")
            self.getControl(RUNTIME).setLabel("")
        except TypeError:
            Debug("TypeError for Runtime")
        try:
            if self.movies[current]['tagline'] <> "":
                self.getControl(TAGLINE).setLabel("\""+self.movies[current]['tagline']+"\"")
            else:
                self.getControl(TAGLINE).setLabel("")
        except KeyError:
            Debug("KeyError for Tagline")
            self.getControl(TAGLINE).setLabel("")
        except TypeError:
            Debug("TypeError for Tagline")
        try:
            self.getControl(RATING).setLabel("Rating: " + self.movies[current]['certification'])
        except KeyError:
            Debug("KeyError for Rating")
            self.getControl(RATING).setLabel("")
        except TypeError:
            Debug("TypeError for Rating")
        if 'watchers' in self.movies[current]:
            try:
                self.getControl(WATCHERS).setLabel(str(self.movies[current]['watchers']) + " people watching")
            except KeyError:
                Debug("KeyError for Watchers")
                self.getControl(WATCHERS).setLabel("")
            except TypeError:
                Debug("TypeError for Watchers")
        
    def onFocus( self, controlId ):
        self.controlId = controlId
    
    def showContextMenu(self):
        movie = self.movies[self.getControl(MOVIE_LIST).getSelectedPosition()]
        li = self.getControl(MOVIE_LIST).getSelectedItem()
        options = []
        actions = []
        if movie['idMovie'] != -1:
            options.append("Play")
            actions.append('play')
        if self.type <> 'watchlist':
            if 'watchlist' in movie:
                if movie['watchlist']:
                    options.append("Remove from watchlist")
                    actions.append('unwatchlist')
                else:
                    options.append("Add to watchlist")
                    actions.append('watchlist')
        else:
            options.append("Remove from watchlist")
            actions.append('unwatchlist')
        options.append("Rate")
        actions.append('rate')
        
        select = xbmcgui.Dialog().select(movie['title']+" - "+str(movie['year']), options)
        if select != -1:
            Debug("Select: " + actions[select])
        if select == -1:
            Debug ("menu quit by user")
            return
        elif actions[select] == 'play':
            playMovieById(movie['idMovie'])
        elif actions[select] == 'unwatchlist':
            if removeMoviesFromWatchlist([movie]) == None:
                notification("Trakt Utilities", __language__(1311).encode( "utf-8", "ignore" )) # Failed to remove from watch-list
            else:
                notification("Trakt Utilities", __language__(1312).encode( "utf-8", "ignore" )) # Successfully removed from watch-list
                li.setProperty('Watchlist','false')
                movie['watchlist'] = False;
        elif actions[select] == 'watchlist':
            if addMoviesToWatchlist([movie]) == None:
                notification("Trakt Utilities", __language__(1309).encode( "utf-8", "ignore" )) # Failed to added to watch-list
            else:
                notification("Trakt Utilities", __language__(1310).encode( "utf-8", "ignore" )) # Successfully added to watch-list
                li.setProperty('Watchlist','true')
                movie['watchlist'] = True;
        elif actions[select] == 'rate':
            doRateMovie(imdbid=movie['imdb_id'], title=movie['title'], year=movie['year'])        
        
    def onAction(self, action):
        if action.getId() == 0:
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing MoviesWindow")
            self.close()
        elif action.getId() in (1,2,107):
            self.listUpdate()
        elif action.getId() == ACTION_SELECT_ITEM:
            movie = self.movies[self.getControl(MOVIE_LIST).getSelectedPosition()]
            if movie['idMovie'] == -1: # Error
                xbmcgui.Dialog().ok("Trakt Utilities", movie['title'].encode( "utf-8", "ignore" ) + " " + __language__(1162).encode( "utf-8", "ignore" )) # "moviename" not found in your XBMC Library
            else:
                playMovieById(movie['idMovie'])
        elif action.getId() == ACTION_CONTEXT_MENU:
            self.showContextMenu()
        else:
            Debug("Uncaught action (movies): "+str(action.getId()))

class MovieWindow(xbmcgui.WindowXML):

    movie = None

    def initWindow(self, movie):
        self.movie = movie
        
    def onInit(self):
        if self.movie != None:
            try:
                self.getControl(BACKGROUND).setImage(self.movie['images']['fanart'])
            except KeyError:
                Debug("KeyError for Backround")
            except TypeError:
                Debug("TypeError for Backround")
            try:
                self.getControl(POSTER).setImage(self.movie['images']['poster'])
            except KeyError:
                Debug("KeyError for Poster")
            except TypeError:
                Debug("TypeError for Poster")
            try:
                self.getControl(TITLE).setLabel(self.movie['title'])
            except KeyError:
                Debug("KeyError for Title")
            except TypeError:
                Debug("TypeError for Title")
            try:
                self.getControl(OVERVIEW).setText(self.movie['overview'])
            except KeyError:
                Debug("KeyError for Overview")
            except TypeError:
                Debug("TypeError for Overview")
            try:
                self.getControl(YEAR).setLabel("Year: " + str(self.movie['year']))
            except KeyError:
                Debug("KeyError for Year")
            except TypeError:
                Debug("TypeError for Year")
            try:
                self.getControl(RUNTIME).setLabel("Runtime: " + str(self.movie['runtime']) + " Minutes")
            except KeyError:
                Debug("KeyError for Runtime")
            except TypeError:
                Debug("TypeError for Runtime")
            try:
                self.getControl(TAGLINE).setLabel(self.movie['tagline'])
            except KeyError:
                Debug("KeyError for Runtime")
            except TypeError:
                Debug("TypeError for Runtime")
            try:
                self.playbutton = self.getControl(PLAY_BUTTON)
                self.setFocus(self.playbutton)
            except (KeyError,TypeError):
                pass
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def onClick(self, controlId):
        if controlId == PLAY_BUTTON:
            pass

    def onAction(self, action):
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        
        if action.getId() == 0:
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing MovieInfoWindow")
            self.close()
        else:
            Debug("Uncaught action (movie info): "+str(action.getId()))

class TVShowsWindow(xbmcgui.WindowXML):

    tvshows = None
    type = 'basic'

    def initWindow(self, tvshows, type):
        self.tvshows = tvshows
        self.type = type
        
    def onInit(self):
        if self.tvshows != None:
            for tvshow in self.tvshows:
                li = xbmcgui.ListItem(tvshow['title'], '', tvshow['images']['poster'])
                if not ('idShow' in tvshow):
                    tvshow['idShow'] = getShowIdFromXBMC(tvshow['tvdb_id'], tvshow['title'])
                if tvshow['idShow'] != -1:
                    li.setProperty('Available','true')
                if self.type <> 'watchlist':
                    if 'watchlist' in tvshow:
                        if tvshow['watchlist']:
                            li.setProperty('Watchlist','true')
                self.getControl(TVSHOW_LIST).addItem(li)
            self.setFocus(self.getControl(TVSHOW_LIST))
            self.listUpdate()
        else:
            Debug("TVShowsWindow: Error: tvshows array is empty")
            self.close()
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def listUpdate(self):
        
        try:
            current = self.getControl(TVSHOW_LIST).getSelectedPosition()
        except TypeError:
            return # ToDo: error output
        
        try:
            self.getControl(BACKGROUND).setImage(self.tvshows[current]['images']['fanart'])
        except KeyError:
            Debug("KeyError for Backround")
        except TypeError:
            Debug("TypeError for Backround")
        try:
            self.getControl(TITLE).setLabel(self.tvshows[current]['title'])
        except KeyError:
            Debug("KeyError for Title")
            self.getControl(TITLE).setLabel("")
        except TypeError:
            Debug("TypeError for Title")
        try:
            self.getControl(OVERVIEW).setText(self.tvshows[current]['overview'])
        except KeyError:
            Debug("KeyError for Overview")
            self.getControl(OVERVIEW).setText("")
        except TypeError:
            Debug("TypeError for Overview")
        try:
            self.getControl(YEAR).setLabel("Year: " + str(self.tvshows[current]['year']))
        except KeyError:
            Debug("KeyError for Year")
            self.getControl(YEAR).setLabel("")
        except TypeError:
            Debug("TypeError for Year")
        try:
            self.getControl(RUNTIME).setLabel("Runtime: " + str(self.tvshows[current]['runtime']) + " Minutes")
        except KeyError:
            Debug("KeyError for Runtime")
            self.getControl(RUNTIME).setLabel("")
        except TypeError:
            Debug("TypeError for Runtime")
        try:
            self.getControl(TAGLINE).setLabel(str(self.tvshows[current]['tagline']))
        except KeyError:
            Debug("KeyError for Tagline")
            self.getControl(TAGLINE).setLabel("")
        except TypeError:
            Debug("TypeError for Tagline")
        try:
            self.getControl(RATING).setLabel("Rating: " + self.tvshows[current]['certification'])
        except KeyError:
            Debug("KeyError for Rating")
            self.getControl(RATING).setLabel("")
        except TypeError:
            Debug("TypeError for Rating")
        if self.type == 'trending':
            try:
                self.getControl(WATCHERS).setLabel(str(self.tvshows[current]['watchers']) + " people watching")
            except KeyError:
                Debug("KeyError for Watchers")
                self.getControl(WATCHERS).setLabel("")
            except TypeError:
                Debug("TypeError for Watchers")

    def showContextMenu(self):
        show = self.tvshows[self.getControl(TVSHOW_LIST).getSelectedPosition()]
        li = self.getControl(TVSHOW_LIST).getSelectedItem()
        options = []
        actions = []
        if self.type <> 'watchlist':
            if 'watchlist' in show:
                if show['watchlist']:
                    options.append("Remove from watchlist")
                    actions.append('unwatchlist')
                else:
                    options.append("Add to watchlist")
                    actions.append('watchlist')
            else:
                options.append("Add to watchlist")
                actions.append('watchlist')
        else:
            options.append("Remove from watchlist")
            actions.append('unwatchlist')
        options.append("Rate")
        actions.append('rate')
        
        select = xbmcgui.Dialog().select(show['title'], options)
        if select != -1:
            Debug("Select: " + actions[select])
        if select == -1:
            Debug ("menu quit by user")
            return
        elif actions[select] == 'play':
            xbmcgui.Dialog().ok("Trakt Utilities", "comming soon")
        elif actions[select] == 'unwatchlist':
            if removeTVShowsFromWatchlist([show]) == None:
                notification("Trakt Utilities", __language__(1311).encode( "utf-8", "ignore" )) # Failed to remove from watch-list
            else:
                notification("Trakt Utilities", __language__(1312).encode( "utf-8", "ignore" )) # Successfully removed from watch-list
                li.setProperty('Watchlist','false')
                show['watchlist'] = False;
        elif actions[select] == 'watchlist':
            if addTVShowsToWatchlist([show]) == None:
                notification("Trakt Utilities", __language__(1309).encode( "utf-8", "ignore" )) # Failed to added to watch-list
            else:
                notification("Trakt Utilities", __language__(1310).encode( "utf-8", "ignore" )) # Successfully added to watch-list
                li.setProperty('Watchlist','true')
                show['watchlist'] = True;
        elif actions[select] == 'rate':
            rateShow = RateShowDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
            rateShow.initDialog(show['tvdb_id'], show['title'], show['year'], getShowRatingFromTrakt(show['tvdb_id'], show['title'], show['year']))
            rateShow.doModal()
            del rateShow 

    def onAction(self, action):

        if action.getId() == 0:
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing TV Shows Window")
            self.close()
        elif action.getId() in (1,2,107):
            self.listUpdate()
        elif action.getId() == ACTION_SELECT_ITEM:
            pass # do something here ?
        elif action.getId() == ACTION_CONTEXT_MENU:
            self.showContextMenu()
        else:
            Debug("Uncaught action (tv shows): "+str(action.getId()))

class RateMovieDialog(xbmcgui.WindowXMLDialog):

    def initDialog(self, imdbid, title, year, curRating):
        self.imdbid = imdbid
        self.title = title
        self.year = year
        self.curRating = curRating
        if self.curRating <> "love" and self.curRating <> "hate": self.curRating = None
        
    def onInit(self):
        self.getControl(RATE_TITLE).setLabel(__language__(1303).encode( "utf-8", "ignore" )) # How would you rate that movie?
        self.getControl(RATE_RATE_SHOW_BG).setVisible(False)
        self.getControl(RATE_RATE_SHOW_BTN).setVisible(False)
        self.getControl(RATE_CUR_NO_RATING).setEnabled(False)
        self.setFocus(self.getControl(RATE_SKIP_RATING))
        self.updateRatedButton();
        return
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def onClick(self, controlId):
        if controlId == RATE_LOVE_BTN:
            self.curRating = "love"
            self.updateRatedButton()
            rateMovieOnTrakt(self.imdbid, self.title, self.year, "love")
            self.close()
            return
        elif controlId == RATE_HATE_BTN:
            self.curRating = "hate"
            self.updateRatedButton()
            rateMovieOnTrakt(self.imdbid, self.title, self.year, "hate")
            self.close()
            return
        elif controlId == RATE_SKIP_RATING:
            self.close()
            return
        elif controlId in (RATE_CUR_LOVE, RATE_CUR_HATE): #unrate clicked
            self.curRating = None
            self.updateRatedButton()
            rateMovieOnTrakt(self.imdbid, self.title, self.year, "unrate")
            return
        else:
            Debug("Uncaught click (rate movie dialog): "+str(controlId))
    
    def onAction(self, action):
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        
        if action.getId() in (0, 107):
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing RateMovieDialog")
            self.close()
        else:
            Debug("Uncaught action (rate movie dialog): "+str(action.getId()))
            
    def updateRatedButton(self):
        self.getControl(RATE_CUR_NO_RATING).setVisible(False if self.curRating <> None else True)
        self.getControl(RATE_CUR_LOVE).setVisible(False if self.curRating <> "love" else True)
        self.getControl(RATE_CUR_HATE).setVisible(False if self.curRating <> "hate" else True)

class RateEpisodeDialog(xbmcgui.WindowXMLDialog):

    def initDialog(self, tvdbid, title, year, season, episode, curRating):
        self.tvdbid = tvdbid
        self.title = title
        self.year = year
        self.season = season
        self.episode = episode
        self.curRating = curRating
        if self.curRating <> "love" and self.curRating <> "hate": self.curRating = None
        
    def onInit(self):
        self.getControl(RATE_TITLE).setLabel(__language__(1304).encode( "utf-8", "ignore" )) # How would you rate that episode?
        self.getControl(RATE_RATE_SHOW_BTN).setLabel(__language__(1305).encode( "utf-8", "ignore" )) # Rate whole show
        self.getControl(RATE_CUR_NO_RATING).setEnabled(False)
        self.setFocus(self.getControl(RATE_SKIP_RATING))
        self.updateRatedButton();
        return
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def onClick(self, controlId):
        if controlId == RATE_LOVE_BTN:
            self.curRating = "love"
            self.updateRatedButton()
            rateEpisodeOnTrakt(self.tvdbid, self.title, self.year, self.season, self.episode, "love")
            self.close()
            return
        elif controlId == RATE_HATE_BTN:
            self.curRating = "hate"
            self.updateRatedButton()
            rateEpisodeOnTrakt(self.tvdbid, self.title, self.year, self.season, self.episode, "hate")
            self.close()
            return
        elif controlId == RATE_SKIP_RATING:
            self.close()
            return
        elif controlId in (RATE_CUR_LOVE, RATE_CUR_HATE): #unrate clicked
            self.curRating = None
            self.updateRatedButton();
            rateEpisodeOnTrakt(self.tvdbid, self.title, self.year, self.season, self.episode, "unrate")
            return
        elif controlId == RATE_RATE_SHOW_BTN:
            self.getControl(RATE_RATE_SHOW_BG).setVisible(False)
            self.getControl(RATE_RATE_SHOW_BTN).setVisible(False)
            self.setFocus(self.getControl(RATE_SKIP_RATING))
            rateShow = RateShowDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
            rateShow.initDialog(self.tvdbid, self.title, self.year, getShowRatingFromTrakt(self.tvdbid, self.title, self.year))
            rateShow.doModal()
            del rateShow
        else:
            Debug("Uncaught click (rate episode dialog): "+str(controlId))
    
    def onAction(self, action):
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        
        if action.getId() in (0, 107):
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing RateEpisodeDialog")
            self.close()
        else:
            Debug("Uncaught action (rate episode dialog): "+str(action.getId()))
            
    def updateRatedButton(self):
        self.getControl(RATE_CUR_NO_RATING).setVisible(False if self.curRating <> None else True)
        self.getControl(RATE_CUR_LOVE).setVisible(False if self.curRating <> "love" else True)
        self.getControl(RATE_CUR_HATE).setVisible(False if self.curRating <> "hate" else True)

class RateShowDialog(xbmcgui.WindowXMLDialog):

    def initDialog(self, tvdbid, title, year, curRating):
        self.tvdbid = tvdbid
        self.title = title
        self.year = year
        self.curRating = curRating
        if self.curRating <> "love" and self.curRating <> "hate": self.curRating = None
        
    def onInit(self):
        self.getControl(RATE_TITLE).setLabel(__language__(1306).encode( "utf-8", "ignore" )) # How would you rate that show?
        self.getControl(RATE_SCENE).setVisible(False)
        self.getControl(RATE_RATE_SHOW_BG).setVisible(False)
        self.getControl(RATE_RATE_SHOW_BTN).setVisible(False)
        self.getControl(RATE_CUR_NO_RATING).setEnabled(False)
        self.setFocus(self.getControl(RATE_SKIP_RATING))
        self.updateRatedButton();
        return
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def onClick(self, controlId):
        if controlId == RATE_LOVE_BTN:
            self.curRating = "love"
            self.updateRatedButton()
            rateShowOnTrakt(self.tvdbid, self.title, self.year, "love")
            self.close()
            return
        elif controlId == RATE_HATE_BTN:
            self.curRating = "hate"
            self.updateRatedButton()
            rateShowOnTrakt(self.tvdbid, self.title, self.year, "hate")
            self.close()
            return
        elif controlId == RATE_SKIP_RATING:
            self.close()
            return
        elif controlId in (RATE_CUR_LOVE, RATE_CUR_HATE): #unrate clicked
            self.curRating = None
            self.updateRatedButton();
            rateShowOnTrakt(self.tvdbid, self.title, self.year, "unrate")
            return
        elif controlId == RATE_RATE_SHOW_BTN:
            return
        else:
            Debug("Uncaught click (rate show dialog): "+str(controlId))
    
    def onAction(self, action):
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        
        if action.getId() in (0, 107):
            return
        if action.getId() in (ACTION_PARENT_DIRECTORY, ACTION_PREVIOUS_MENU):
            Debug("Closing RateShowDialog")
            self.close()
        else:
            Debug("Uncaught action (rate show dialog): "+str(action.getId()))
            
    def updateRatedButton(self):    
        self.getControl(RATE_CUR_NO_RATING).setVisible(False if self.curRating <> None else True)
        self.getControl(RATE_CUR_LOVE).setVisible(False if self.curRating <> "love" else True)
        self.getControl(RATE_CUR_HATE).setVisible(False if self.curRating <> "hate" else True)

########NEW FILE########
