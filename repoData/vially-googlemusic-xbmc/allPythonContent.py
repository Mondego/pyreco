__FILENAME__ = default
import sys, xbmc, xbmcgui, xbmcplugin, xbmcaddon

# plugin constants
version = "0.8.x"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')
__info__ = settings.getAddonInfo
__icon__ = __info__('icon')

dbg = settings.getSetting( "debug" ) == "true"
dbglevel = 3

# plugin variables
storage = ""

# utility functions
def parameters_string_to_dict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

def log(message):
    if dbg:
        print "[%s] %s" % (plugin, message)

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

    import GoogleMusicStorage
    storage = GoogleMusicStorage.GoogleMusicStorage()

    import GoogleMusicPlaySong
    song = GoogleMusicPlaySong.GoogleMusicPlaySong()

    params = parameters_string_to_dict(sys.argv[2])
    get = params.get

    if (get("action") == "play_song"):
        song.play(get("song_id"),params)
    else:

        import GoogleMusicNavigation
        navigation = GoogleMusicNavigation.GoogleMusicNavigation()

        if (not params):
 
            import GoogleMusicLogin
            login = GoogleMusicLogin.GoogleMusicLogin()
 
            if not settings.getSetting('version') or settings.getSetting('version') != version:
               storage.clearCache()
               login.clearCookie()
               settings.setSetting('version',version)
               
            # check for initing cookies, db and library only on main menu
            storage.checkDbInit()

            login.checkCredentials()
            login.checkCookie()
            login.initDevice()

            if not storage.isPlaylistFetched('all_songs'):
                xbmc.executebuiltin("XBMC.Notification("+plugin+",'Loading library',5000,"+__icon__ +")")
                log('Loading library')
                navigation.api.loadLibrary()

            navigation.listMenu()
        elif (get("action")):
            navigation.executeAction(params)
        elif (get("path")):
            navigation.listMenu(params)
        else:
            print plugin + " ARGV Nothing done.. verify params " + repr(params)
            

########NEW FILE########
__FILENAME__ = GoogleMusicApi
import sys

class GoogleMusicApi():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.storage   = self.main.storage
        self.api       = None
        self.device    = None
        self.login     = None
        
    def getApi(self,nocache=False):
        if self.api == None :
            import GoogleMusicLogin
            self.login = GoogleMusicLogin.GoogleMusicLogin()
            self.login.login(nocache)
            self.api = self.login.getApi()
            self.device = self.login.getDevice()
        return self.api

    def getDevice(self):
        if self.device == None:
            self.getApi()
        return self.device

    def getLogin(self):
        if self.login == None:
            self.getApi()
        return self.login
                
    def getPlaylistSongs(self, playlist_id, forceRenew=False):
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky'):
            return self.storage.getAutoPlaylistSongs(playlist_id)

        if not self.storage.isPlaylistFetched(playlist_id) or forceRenew:
            self.updatePlaylistSongs(playlist_id)

        songs = self.storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type, forceRenew=False):
        if playlist_type == 'auto':
            return [['thumbsup','Highly Rated'],['lastadded','Last Added'],
                    ['freepurchased','Free and Purchased'],['mostplayed','Most Played']]

        if forceRenew:
            self.updatePlaylists(playlist_type)

        playlists = self.storage.getPlaylists()
        if len(playlists) == 0 and not forceRenew:
            self.updatePlaylists(playlist_type)
            playlists = self.storage.getPlaylists()

        return playlists

    def getSong(self, song_id):
        return self.storage.getSong(song_id)
        
    def loadLibrary(self):
        #gen = self.gmusicapi.get_all_songs(incremental=True)
        #for chunk in gen:
        #    for song in chunk:
                #print song
        #        api_songs.append(song)
        #    break
        #api_songs = [song for chunk in api_songs for song in chunk]
        api_songs = self.getApi().get_all_songs()
        self.main.log("Library Size: "+repr(len(api_songs)))
        #self.main.log("First Song: "+repr(api_songs[0]))
        self.storage.storeApiSongs(api_songs, 'all_songs')

    def updatePlaylistSongs(self, playlist_id):
        if self.getDevice():
            self.storage.storePlaylistSongs(self.api.get_all_user_playlist_contents())
        else:
            self.storage.storeApiSongs(self.api.get_playlist_songs(playlist_id), playlist_id)

    def updatePlaylists(self, playlist_type):
        if self.getDevice():
            self.storage.storePlaylistSongs(self.api.get_all_user_playlist_contents())
        else:
            playlists = self.api.get_all_playlist_ids(playlist_type)
            self.storage.storePlaylists(playlists[playlist_type], playlist_type)

    def getSongStreamUrl(self, song_id):
        # using cached cookies fails with all access tracks
        self.getApi(nocache=True)
        device_id = self.getDevice()
        self.main.log("getSongStreamUrl device: "+device_id)

        if device_id:
            stream_url = self.api.get_stream_url(song_id, device_id)
        else:
            streams = self.api.get_stream_urls(song_id)
            if len(streams) > 1:
                self.main.xbmc.executebuiltin("XBMC.Notification("+plugin+",'All Access track not playable')")
                raise Exception('All Access track not playable, no mobile device found in account!')
            stream_url = streams[0]

        self.storage.updateSongStreamUrl(song_id, stream_url)
        self.main.log("getSongStreamUrl: "+stream_url)
        return stream_url

    def getFilterSongs(self, filter_type, filter_criteria):
        return self.storage.getFilterSongs(filter_type, filter_criteria)

    def getCriteria(self, criteria, artist=''):
        return self.storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        return self.storage.getSearch(query)

    def clearCache(self):
        self.storage.clearCache()
        self.clearCookie()

    def clearCookie(self):
        self.getLogin().clearCookie()

    def getStations(self):
        stations = {}
        try:
            stations = self.getApi().get_all_stations()
            #self.main.log("STATIONS: "+repr(stations))
        except Exception as e:
            self.main.log("*** NO STATIONS *** "+repr(e))
        return stations

    def getStationTracks(self, station_id):
        tracks = {}
        try:
            tracks = self.getApi().get_station_tracks(station_id)
            #self.main.log("TRACKS *** "+repr(tracks))
        except Exception as e:
            self.main.log("*** NO TRACKS *** "+repr(e))
        return tracks
########NEW FILE########
__FILENAME__ = GoogleMusicLogin
import os
import sys
import time
from datetime import datetime

from gmusicapi import Mobileclient, Webclient


class GoogleMusicLogin():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.xbmcgui   = self.main.xbmcgui
        self.xbmc      = self.main.xbmc
        self.settings  = self.main.settings

        if self.getDevice():
            self.gmusicapi = Mobileclient(debug_logging=False,validate=False)
        else:
            self.gmusicapi = Webclient(debug_logging=False,validate=False)


    def checkCookie(self):
        # Remove cookie data if it is older then 7 days
        if self.settings.getSetting('cookie-date') != None and len(self.settings.getSetting('cookie-date')) > 0:
            if (datetime.now() - datetime(*time.strptime(self.settings.getSetting('cookie-date'), '%Y-%m-%d %H:%M:%S.%f')[0:6])).days >= 7:
                self.clearCookie()

    def checkCredentials(self):
        if not self.settings.getSetting('username'):
            self.settings.openSettings()

    def getApi(self):
        return self.gmusicapi

    def getDevice(self):
        return self.settings.getSetting('device_id')

    def initDevice(self):
        device_id = self.settings.getSetting('device_id')

        if not device_id:
            self.main.log('Trying to fetch the device_id')
            webclient = Webclient(debug_logging=False,validate=False)
            self.checkCredentials()
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')
            webclient.login(username, password)
            if webclient.is_authenticated():
                devices = webclient.get_registered_devices()
                self.main.log(repr(devices))
                for device in devices:
                    if device["type"] in ("PHONE","IOS"):
                        device_id = str(device["id"])
                        break
            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                self.settings.setSetting('device_id',device_id)
                self.main.log('Found device_id: '+device_id)


    def clearCookie(self):
        self.settings.setSetting('logged_in', "")
        self.settings.setSetting('authtoken', "")
        self.settings.setSetting('cookie-xt', "")
        self.settings.setSetting('cookie-sjsaid', "")
        self.settings.setSetting('device_id', "")

    def logout(self):
        self.gmusicapi.logout()

    def login(self,nocache=False):
        if nocache or not self.settings.getSetting('logged_in'):
            self.main.log('Logging in')
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            try:
                self.gmusicapi.login(username, password)
            except Exception as e:
                self.main.log(repr(e))
            if not self.gmusicapi.is_authenticated():
                self.main.log("Login failed")
                self.settings.setSetting('logged_in', "")
                self.language = self.settings.getLocalizedString
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                self.settings.openSettings()
            else:
                self.main.log("Login succeeded")
                if not nocache:
                    self.settings.setSetting('logged_in', "1")
                    self.settings.setSetting('authtoken', self.gmusicapi.session._authtoken)
                    self.settings.setSetting('cookie-xt', self.gmusicapi.session._rsession.cookies['xt'])
                    self.settings.setSetting('cookie-sjsaid', self.gmusicapi.session._rsession.cookies['sjsaid'])
                    self.settings.setSetting('cookie-date', str(datetime.now()))
        else:

            self.main.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = self.settings.getSetting('authtoken')
            self.gmusicapi.session._rsession.cookies['xt'] = self.settings.getSetting('cookie-xt')
            self.gmusicapi.session._rsession.cookies['sjsaid'] = self.settings.getSetting('cookie-sjsaid')
            self.gmusicapi.session.is_authenticated = True

########NEW FILE########
__FILENAME__ = GoogleMusicNavigation
import os
import sys
import urllib
import GoogleMusicApi

class GoogleMusicNavigation():
    def __init__(self):
        self.main = sys.modules["__main__"]
        self.xbmc = self.main.xbmc
        self.xbmcgui = self.main.xbmcgui
        self.xbmcplugin = self.main.xbmcplugin

        self.language = self.main.settings.getLocalizedString

        self.api = GoogleMusicApi.GoogleMusicApi()
        self.song = self.main.song

        self.main_menu = (
            {'title':self.language(30209), 'params':{'path':"library"}},
            {'title':self.language(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.language(30208), 'params':{'path':"search"}}
        )
        self.lib_menu = (
            {'title':self.language(30210), 'params':{'path':"playlist", 'playlist_id':"feellucky"}},
            {'title':self.language(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.language(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.language(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.language(30207), 'params':{'path':"filter", 'criteria':"genre"}},
        )
        
    def listMenu(self, params={}):
        get = params.get
        self.path = get("path", "root")

        listItems = []
        updateListing = False

        if self.path == "root":
            listItems = self.getMenuItems(self.main_menu)
            if self.api.getDevice():
                listItems.insert(1,self.addFolderListItem(self.language(30203),{'path':"playlists",'playlist_type':"radio"}))
        elif self.path == "library":
            listItems = self.getMenuItems(self.lib_menu)
        elif self.path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
        elif self.path == "station":
            listItems = self.getStationTracks(get('id'))
        elif self.path == "playlists":
            listItems = self.getPlaylists(get('playlist_type'))
        elif self.path == "filter":
            listItems = self.getCriteria(get('criteria'))
        elif self.path == "artist":
            albumName = urllib.unquote_plus(get('name'))
            listItems = self.getCriteria("album",albumName)
            listItems.insert(0,self.addFolderListItem(self.language(30201),{'path':"artist_allsongs", 'name':albumName}))
        elif self.path == "artist_allsongs":
            listItems = self.listFilterSongs("artist",get('name'))
        elif self.path in ["genre","artist","album"]:
            listItems = self.listFilterSongs(self.path,get('name'))
        elif self.path == "search":
            import CommonFunctions as common
            query = common.getUserInput(self.language(30208), '')
            if query:
                listItems = self.getSearch(query)
            else:
                self.main.log("No query specified. Showing main menu")
                listItems = self.getMenuItems(self.main_menu)
                updateListing = True
        else:
            self.main.log("Invalid path: " + get("path"))

        self.xbmcplugin.addDirectoryItems(int(sys.argv[1]), listItems)
        self.xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, updateListing=updateListing)

    def getMenuItems(self,items):
        ''' Build the plugin root menu. '''
        menuItems = []
        for menu_item in items:
            params = menu_item['params']
            cm = []
            if 'playlist_id' in params:
                cm = self.getPlayAllContextMenuItems(params['playlist_id'])
            elif 'playlist_type' in params:
                cm = self.getPlaylistsContextMenuItems(params['playlist_type'])
            menuItems.append(self.addFolderListItem(menu_item['title'], params, cm))
        return menuItems

    def executeAction(self, params={}):
        get = params.get
        if (get("action") == "play_all"):
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.song.play(get("song_id"))
        elif (get("action") == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (get("action") == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (get("action") == "clear_cache"):
            self.api.clearCache()
        elif (get("action") == "clear_cookie"):
            self.api.clearCookie()
        else:
            self.main.log("Invalid action: " + get("action"))

    def addFolderListItem(self, name, params={}, contextMenu=[], album_art_url=""):
        li = self.xbmcgui.ListItem(label=name, iconImage=album_art_url, thumbnailImage=album_art_url)
        li.setProperty("Folder", "true")

        url = sys.argv[0] + '?' + urllib.urlencode(params)

        if len(contextMenu) > 0:
            li.addContextMenuItems(contextMenu, replaceItems=True)

        return url, li, "true"

    def addSongItem(self, song):
        if self.path == 'artist_allsongs' and song[7]:
            # add album name when showing all artist songs
            li = self.song.createItem(song, ('['+song[7]+'] '+song[8]))
        else:
            li = self.song.createItem(song)

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song[0])
        return url,li

    def listPlaylistSongs(self, playlist_id):
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        return self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        listItems = []
        for song in library:
            listItems.append(self.addSongItem(song))
        return listItems

    def getPlaylists(self, playlist_type):
        self.main.log("Getting playlists of type: " + playlist_type)
        if playlist_type == 'radio':
            return self.getStations()
        playlists = self.api.getPlaylistsByType(playlist_type)
        return self.addPlaylistsItems(playlists)

    def listFilterSongs(self, filter_type, filter_criteria):
        if filter_criteria:
            filter_criteria = urllib.unquote_plus(filter_criteria)
        songs = self.api.getFilterSongs(filter_type, filter_criteria)
        return self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria, artist=''):
        listItems = []
        genres = self.api.getCriteria(criteria,artist)
        for genre in genres:
            if len(genre)>1:
                art = genre[1]
            else:
                art = self.main.__icon__
            cm = self.getFilterContextMenuItems(criteria,genre[0])
            listItems.append(self.addFolderListItem(genre[0], {'path':criteria, 'name':genre[0]}, cm, art))
        return listItems

    def addPlaylistsItems(self, playlists):
        listItems = []
        for playlist_id, playlist_name in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_id)
            listItems.append(self.addFolderListItem(playlist_name, {'path':"playlist", 'playlist_id':playlist_id}, cm))
        return listItems

    def playAll(self, params={}):
        get = params.get

        playlist_id = get('playlist_id')
        if playlist_id:
            self.main.log("Loading playlist: " + playlist_id)
            songs = self.api.getPlaylistSongs(playlist_id)
        else:
            songs = self.api.getFilterSongs(get('filter_type'), get('filter_criteria'))

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s"
        for song in songs:
            playlist.add(song_url % (sys.argv[0], song[0]), self.song.createItem(song))

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true)" % (sys.argv[0], filter_type, filter_criteria)))
        return cm

    def getPlaylistsContextMenuItems(self, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        return cm

    def getSearch(self, query):
        return self.addSongsFromLibrary(self.api.getSearch(query))

    def getStations(self):
        listItems = []
        stations = self.api.getStations()
        for rs in stations:
           listItems.append(self.addFolderListItem(rs['name'], {'path':"station",'id':rs['id']}, album_art_url=rs['imageUrl']))
        return listItems

    def getStationTracks(self,station_id):
        import gmusicapi.utils.utils as utils
        listItems = []
        tracks = self.api.getStationTracks(station_id)
        for track in tracks:
            li = self.xbmcgui.ListItem(track['title'])
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Music', 'true')
            url = '%s?action=play_song&song_id=%s' % (sys.argv[0],utils.id_or_nid(track).encode('utf8'))
            infos = {}
            for k,v in track.iteritems():
                if k in ('title','album','artist'):
                    url = url+'&'+repr(k)+'='+repr(v)
                    infos[k] = v
            li.setInfo(type='music', infoLabels=infos)
            li.setPath(url)
            listItems.append([url,li])
        return listItems

########NEW FILE########
__FILENAME__ = GoogleMusicPlaySong
import sys, time

class GoogleMusicPlaySong():

    def __init__(self):
        self.main       = sys.modules["__main__"]
        self.xbmcgui    = self.main.xbmcgui

    def play(self, song_id, params={}):
        song = self.main.storage.getSong(song_id)
        prefetch = self.main.settings.getSetting( "prefetch" )

        if song:
            if prefetch=="false" or not song[24] or int(self.main.parameters_string_to_dict(song[24]).get('expire'))  < time.time():
                 self.main.log("Prefetch disabled or URL invalid or expired :")
                 url = self.__getSongStreamUrl(song_id)
            else:
                 url = song[24]

            li = self.createItem(song)
        else:
            self.main.log("Track not in library :: "+repr(params))
            if params:
                label=params.get('title')
            li = self.xbmcgui.ListItem(label)
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Music', 'true')
            li.setInfo(type='music', infoLabels=params)
            url = self.__getSongStreamUrl(song_id)

        self.main.log("URL :: "+repr(url))

        li.setPath(url)
        self.main.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

        if prefetch=="true":
            try:
                self.__prefetchUrl()
            except Exception as ex:
                self.main.log("ERROR trying to fetch url: "+repr(ex))
                #raise

    def __getSongStreamUrl(self,song_id):
        import GoogleMusicApi
        self.api = GoogleMusicApi.GoogleMusicApi()
        return self.api.getSongStreamUrl(song_id)

    def createItem(self, song, label=None):
        infoLabels = {
            'tracknumber': song[11],
            'duration': song[21],
            'year': song[6],
            'genre': song[14],
            'album': song[7],
            'artist': song[18],
            'title': song[8],
            'playcount': song[15]
        }

        if not label:
            label = song[23]

        if song[22]:
            li = self.xbmcgui.ListItem(label, iconImage=song[22], thumbnailImage=song[22])
        else:
            li = self.xbmcgui.ListItem(label)
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=infoLabels)

        return li

    def __prefetchUrl(self):
        import gmusicapi.compat as compat
        loadJson = compat.json.loads
        xbmc     = self.main.xbmc
        jsonGetPlaylistPos  = '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":0,"properties":["playlistid","position","percentage"]},"id":1}'
        jsonGetSongDuration = '{"jsonrpc":"2.0", "method":"Playlist.GetItems",    "params":{"playlistid":0, "properties":["file","duration"]}, "id":1}'

        # get song position in playlist
        playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
        while not 'result' in playerProperties:
          #wait for song playing and playlist ready
          xbmc.sleep(1000)
          playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        while playerProperties['result']['percentage'] > 5:
          #wait for new song playing
          xbmc.sleep(1000)
          playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        position = playerProperties['result']['position']
        self.main.log("position:"+str(position)+" percentage:"+str(playerProperties['result']['percentage']))

        # get next song id and fetch url
        playlistItems = loadJson(xbmc.executeJSONRPC(jsonGetSongDuration))
        #self.main.log("playlistItems:: "+repr(playlistItems))

        if position+1 >= len(playlistItems['result']['items']):
            self.main.log("playlist end:: position "+repr(position)+" size "+repr(len(playlistItems['result']['items'])))
            return

        song_id_next = self.main.parameters_string_to_dict(playlistItems['result']['items'][position+1]['file']).get("song_id")
        self.__getSongStreamUrl(song_id_next)

        # stream url expires in 1 minute, refetch to always have a valid one
        while True:
            xbmc.sleep(50000)

            # test if music changed
            playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
            if not 'result' in playerProperties or position != playerProperties['result']['position']:
                self.main.log("ending:: position "+repr(position)+" "+repr(playerProperties))
                break

            # before the stream url expires we fetch it again
            self.__getSongStreamUrl(song_id_next)
########NEW FILE########
__FILENAME__ = GoogleMusicStorage
import os
import sys
import sqlite3


class GoogleMusicStorage():
    def __init__(self):
        self.xbmc     = sys.modules["__main__"].xbmc
        self.settings = sys.modules["__main__"].settings
        self.path     = os.path.join(self.xbmc.translatePath("special://database"), self.settings.getSetting('sqlite_db'))

    def checkDbInit(self):
        # Make sure to initialize database when it does not exist.
        if not os.path.isfile(self.path):
            self.initializeDatabase()
            self.settings.setSetting("fetched_all_songs","0")

    def clearCache(self):
        if os.path.isfile(self.path):
            os.remove(self.path)
        self.settings.setSetting("fetched_all_songs", "0")

    def getPlaylistSongs(self, playlist_id):
        self._connect()
        if playlist_id == 'all_songs':
            result = self.curs.execute("SELECT * FROM songs ORDER BY display_name")
        else:
            result = self.curs.execute("SELECT * FROM songs INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id "+
                                       "WHERE playlists_songs.playlist_id = ?", (playlist_id,))

        songs = result.fetchall()
        self.conn.close()

        return songs

    def getFilterSongs(self, filter_type, filter_criteria):
        if filter_type == 'album':
            query = "select * from songs where album = ? order by disc asc, track asc"
        elif filter_type == 'artist':
            query = "select * from songs where artist = ? order by album asc, disc asc, track asc"
        else:
            query = "select * from songs where genre = ? order by title asc"

        self._connect()
        songs = self.curs.execute(query,(filter_criteria if filter_criteria else '',)).fetchall()
        self.conn.close()

        return songs

    def getCriteria(self, criteria, artist_name):
        self._connect()
        if (criteria == 'artist'):
            result = self.curs.execute("select artist, max(album_art_url) from songs group by artist")
        elif (criteria == 'album'):
            if artist_name:
               result = self.curs.execute("select album, max(album_art_url) from songs where artist=? group by album",(artist_name.decode('utf8'),))
            else:
               result = self.curs.execute("select album, max(album_art_url) from songs group by album")
        else:
            result = self.curs.execute("select genre from songs group by genre")

        criterias = result.fetchall()
        self.conn.close()

        return criterias

    def getPlaylists(self):
        self._connect()
        result = self.curs.execute("SELECT playlist_id, name FROM playlists ORDER BY name")
        playlists = result.fetchall()
        self.conn.close()
        return playlists

    def getAutoPlaylistSongs(self,playlist):
        querys = {'thumbsup':'SELECT * FROM songs WHERE rating = 5 ORDER BY display_name',
                  'lastadded':'SELECT * FROM songs ORDER BY creation_date desc LIMIT 500',
                  'mostplayed':'SELECT * FROM songs ORDER BY play_count desc LIMIT 500',
                  'freepurchased':'SELECT * FROM songs WHERE type = 0 OR type = 1',
                  'feellucky':'SELECT * FROM songs ORDER BY random() LIMIT 500',
                 }
        self._connect()
        result = self.curs.execute(querys[playlist]).fetchall()
        self.conn.close()
        return result

    def getSong(self, song_id):
        self._connect()
        result = self.curs.execute("SELECT * FROM songs WHERE song_id = ? ", (song_id,)).fetchone()
        self.conn.close()
        return result

    def getSearch(self, query):
        query = '%'+ query.replace('%','') + '%'
        self._connect()
        result = self.curs.execute("SELECT * FROM songs WHERE name like ? OR artist like ? ORDER BY display_name", (query,query,)).fetchall()
        self.conn.close()
        return result

    def storePlaylistSongs(self, playlists_songs):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        self.curs.execute("DELETE FROM playlists_songs")
        self.curs.execute("DELETE FROM playlists")

        api_songs = []

        for playlist in playlists_songs:
            print playlist['name']+' id:'+playlist['id']+' tracks:'+str(len(playlist['tracks']))
            playlistId = playlist['id']
            if len(playlist['name']) > 0:
                self.curs.execute("INSERT INTO playlists (name, playlist_id, type, fetched) VALUES (?, ?, 'user', 1)", (playlist['name'], playlistId) )
                for entry in playlist['tracks']:
                    self.curs.execute("INSERT INTO playlists_songs (playlist_id, song_id) VALUES (?, ?)", (playlistId, entry['trackId']))
                    if entry.has_key('track'):
                        api_songs.append(entry['track'])

        self.conn.commit()
        self.conn.close()

        self.storeInAllSongs(api_songs)

    def storeApiSongs(self, api_songs, playlist_id = 'all_songs'):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        if playlist_id == 'all_songs':
            self.curs.execute("DELETE FROM songs")
        else:
            self.curs.execute("DELETE FROM songs WHERE song_id IN (SELECT song_id FROM playlists_songs WHERE playlist_id = ?)", (playlist_id,))
            self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))
            self.curs.executemany("INSERT INTO playlists_songs (playlist_id, song_id) VALUES (?, ?)", [(playlist_id, s["track_id"]) for s in api_songs])

        if playlist_id == 'all_songs':
            self.settings.setSetting("fetched_all_songs", "1")
        else:
            self.curs.execute("UPDATE playlists SET fetched = 1 WHERE playlist_id = ?", (playlist_id,))

        self.conn.commit()
        self.conn.close()

        self.storeInAllSongs(api_songs)

    def storeInAllSongs(self, api_songs):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        def songs():
          for api_song in api_songs:
              yield {
                  'song_id': (api_song["id"] if "id" in api_song else api_song['storeId']), 
                  'comment': (api_song["comment"] if "comment" in api_song else ''),
                  'rating': (api_song["rating"] if "rating" in api_song else 0),
                  'last_played': (api_song["lastPlayed"] if "lastPlayed" in api_song else api_song.get("recentTimestamp",None)),
                  'disc': (api_song["disc"] if "disc" in api_song else api_song.get("discNumber",None)),
                  'composer': (api_song["composer"] if "composer" in api_song else 0),
                  'year': (api_song["year"] if "year" in api_song else 0),
                  'album': (api_song["album"] if "album" in api_song and api_song["album"] else '-Unknown-'),
                  'title': api_song["title"],
                  'album_artist': (api_song["albumArtist"] if "albumArtist" in api_song else '-Unknown-'),
                  'type': (api_song["type"] if "type" in api_song else 0),
                  'track': (api_song["track"] if "track" in api_song else api_song.get("trackNumber",None)),
                  'total_tracks': (api_song["total_tracks"] if "total_tracks" in api_song else api_song.get("totalTrackCount",None)),
                  'beats_per_minute': (api_song["beatsPerMinute"] if "beatsPerMinute" in api_song else 0),
                  'genre': (api_song["genre"] if "genre" in api_song and api_song["genre"] else '-Unknown-'),
                  'play_count': (api_song["playCount"] if "playCount" in api_song else 0),
                  'creation_date': (api_song["creationDate"] if "creationDate" in api_song else api_song.get("creationTimestamp", 0)),
                  'name': (api_song["name"] if "name" in api_song else api_song["title"]),
                  'artist': (api_song["artist"] if "artist" in api_song and api_song["artist"] else '-Unknown-'),
                  'url': api_song.get("url", None),
                  'total_discs': (api_song["total_discs"] if "total_discs" in api_song else api_song.get("totalDiscCount",None)),
                  'duration': int(api_song["durationMillis"])/1000,
                  'album_art_url': self._getAlbumArtUrl(api_song),
                  'display_name': self._getSongDisplayName(api_song),
              }

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES ("+
                              ":song_id, :comment, :rating, :last_played, :disc, :composer, :year, :album, :title, :album_artist,"+
                              ":type, :track, :total_tracks, :beats_per_minute, :genre, :play_count, :creation_date, :name, :artist, "+
                              ":url, :total_discs, :duration, :album_art_url, :display_name, NULL)", songs())

        self.conn.commit()
        self.conn.close()

    def storePlaylists(self, playlists, playlist_type):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        # (deletes will not cascade due to pragma)
        self.curs.execute("DELETE FROM playlists WHERE type = ?", (playlist_type,))

        # rebuild table
        def playlist_rows():
          for playlist_name, playlist_ids in playlists.iteritems():
             for playlist_id in playlist_ids:
                yield (playlist_name, playlist_id, playlist_type)

        self.curs.executemany("INSERT INTO playlists (name, playlist_id, type, fetched) VALUES (?, ?, ?, 0)", playlist_rows())

        # clean up dangling songs
        self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id NOT IN (SELECT playlist_id FROM playlists)")
        self.conn.commit()
        self.conn.close()

    def getSongStreamUrl(self, song_id):
        self._connect()
        song = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ?", (song_id,)).fetchone()
        stream_url = song[0]
        self.conn.close()

        return stream_url

    def isPlaylistFetched(self, playlist_id):
        fetched = False
        if playlist_id == 'all_songs':
            if self.settings.getSetting("fetched_all_songs"):
                fetched = bool(int(self.settings.getSetting("fetched_all_songs")))
        else:
            self._connect()
            playlist = self.curs.execute("SELECT fetched FROM playlists WHERE playlist_id = ?", (playlist_id,)).fetchone()
            fetched = bool(playlist[0])
            self.conn.close()

        return fetched

    def updateSongStreamUrl(self, song_id, stream_url):
        self._connect()
        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
        self.conn.commit()
        self.conn.close()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.conn.text_factory = str
        self.curs = self.conn.cursor()

    def initializeDatabase(self):
        self._connect()

        self.curs.execute('''CREATE TABLE IF NOT EXISTS songs (
                song_id VARCHAR NOT NULL PRIMARY KEY,           --# 0
                comment VARCHAR,                                --# 1
                rating INTEGER,                                 --# 2
                last_played INTEGER,                            --# 3
                disc INTEGER,                                   --# 4
                composer VARCHAR,                               --# 5
                year INTEGER,                                   --# 6
                album VARCHAR,                                  --# 7
                title VARCHAR,                                  --# 8
                album_artist VARCHAR,                           --# 9
                type INTEGER,                                   --# 10
                track INTEGER,                                  --# 11
                total_tracks INTEGER,                           --# 12
                beats_per_minute INTEGER,                       --# 13
                genre VARCHAR,                                  --# 14
                play_count INTEGER,                             --# 15
                creation_date INTEGER,                          --# 16
                name VARCHAR,                                   --# 17
                artist VARCHAR,                                 --# 18
                url VARCHAR,                                    --# 19
                total_discs INTEGER,                            --# 20
                duration INTEGER,                               --# 21
                album_art_url VARCHAR,                          --# 22
                display_name VARCHAR,                           --# 23
                stream_url VARCHAR                              --# 24
        )''')

        self.curs.execute('''CREATE TABLE IF NOT EXISTS playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                fetched BOOLEAN
        )''')

        self.curs.execute('''CREATE TABLE IF NOT EXISTS playlists_songs (
                playlist_id VARCHAR,
                song_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY(song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )''')

        self.curs.execute('''CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id)''')
        self.curs.execute('''CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id)''')

        self.conn.commit()
        self.conn.close()

    def _getSongDisplayName(self, api_song):
        displayName = "-Unknown-"
        song_name = api_song.get("title")
        song_artist = api_song.get("artist")

        if song_artist :
            displayName = song_artist.strip()
            if song_name:
                displayName += " - " + song_name.strip()
        elif song_name :
            displayName = song_name.strip()

        return displayName

    def _getAlbumArtUrl(self, api_song):
        url = ""
        if "albumArtUrl" in api_song:
            url = "http:"+api_song["albumArtUrl"]
        elif "albumArtRef" in api_song:
            url = api_song["albumArtRef"][0]["url"]
        return url

########NEW FILE########
