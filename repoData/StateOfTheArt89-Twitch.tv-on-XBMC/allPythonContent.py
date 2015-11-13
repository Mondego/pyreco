__FILENAME__ = converter
# -*- coding: utf-8 -*-
from twitch import Keys
import json

class JsonListItemConverter(object):

    def __init__(self, PLUGIN, title_length):
        self.plugin = PLUGIN
        self.titleBuilder = TitleBuilder(PLUGIN, title_length)

    def convertGameToListItem(self, game):
        name = game[Keys.NAME].encode('utf-8')
        image = game[Keys.BOX].get(Keys.LARGE, '')
        return {'label': name,
                'path': self.plugin.url_for('createListForGame',
                                            gameName=name, index='0'),
                'icon': image,
		'thumbnail': image
                }

    def convertTeamToListItem(self, team):
        name = team['name']
        return {'label': name,
                'path': self.plugin.url_for(endpoint='createListOfTeamStreams',
                                            team=name),
                'icon': team.get(Keys.LOGO, ''),
                'thumbnail': team.get(Keys.LOGO, '')
                }

    def convertTeamChannelToListItem(self, teamChannel):
        images = teamChannel.get('image', '')
        image = '' if not images else images.get('size600', '')

        channelname = teamChannel['name']
        titleValues = {'streamer': teamChannel.get('display_name'),
                       'title': teamChannel.get('title'),
                       'viewers': teamChannel.get('current_viewers')}

        title = self.titleBuilder.formatTitle(titleValues)
        return {'label': title,
                'path': self.plugin.url_for(endpoint='playLive', name=channelname),
                'is_playable': True,
                'icon': image,
		'thumbnail': image
		}
                
    def convertFollowersToListItem(self, follower):
        videobanner = follower.get(Keys.LOGO, '')
        return {'label': follower[Keys.DISPLAY_NAME],
                'path': self.plugin.url_for(endpoint='channelVideos',
                                            name=follower[Keys.NAME]),
                'icon': videobanner,
		'thumbnail': videobanner 
                }
                
    def convertVideoListToListItem(self,video):
        return {'label': video['title'],
                'path': self.plugin.url_for(endpoint='playVideo',
                                            id=video['_id']),
                'is_playable': True,
                'icon': video.get(Keys.PREVIEW, ''),
		'thumbnail': video.get(Keys.PREVIEW, '')
                }

    def convertStreamToListItem(self, stream):
        channel = stream[Keys.CHANNEL]
        videobanner = channel.get(Keys.VIDEO_BANNER, '')
        logo = channel.get(Keys.LOGO, '')
        return {'label': self.getTitleForStream(stream),
                'path': self.plugin.url_for(endpoint='playLive',
                                            name=channel[Keys.NAME]),
                'is_playable': True,
                'icon': videobanner if videobanner else logo,
		'thumbnail': videobanner if videobanner else logo
        }

    def getTitleForStream(self, stream):
        titleValues = self.extractStreamTitleValues(stream)
        return self.titleBuilder.formatTitle(titleValues)

    def extractStreamTitleValues(self, stream):
        channel = stream[Keys.CHANNEL]
        print json.dumps(channel, indent=4, sort_keys=True)

        if Keys.VIEWERS in channel:
            viewers = channel.get(Keys.VIEWERS);
        else:
            viewers = stream.get(Keys.VIEWERS, self.plugin.get_string(30062))

        return {'streamer': channel.get(Keys.DISPLAY_NAME,
                                        self.plugin.get_string(30060)),
                'title': channel.get(Keys.STATUS,
                                     self.plugin.get_string(30061)),
                'viewers': viewers}

class TitleBuilder(object):

    class Templates(object):
        TITLE = u"{title}"
        STREAMER = u"{streamer}"
        STREAMER_TITLE = u"{streamer} - {title}"
        VIEWERS_STREAMER_TITLE = u"{viewers} - {streamer} - {title}"
        ELLIPSIS = u'...'

    def __init__(self, PLUGIN, line_length):
        self.plugin = PLUGIN
        self.line_length = line_length

    def formatTitle(self, titleValues):
        titleSetting = int(self.plugin.get_setting('titledisplay', unicode))
        template = self.getTitleTemplate(titleSetting)

        for key, value in titleValues.iteritems():
            titleValues[key] = self.cleanTitleValue(value)
        title = template.format(**titleValues)

        return self.truncateTitle(title)

    def getTitleTemplate(self, titleSetting):
        options = {0: TitleBuilder.Templates.STREAMER_TITLE,
                   1: TitleBuilder.Templates.VIEWERS_STREAMER_TITLE,
                   2: TitleBuilder.Templates.TITLE,
                   3: TitleBuilder.Templates.STREAMER}
        return options.get(titleSetting, TitleBuilder.Templates.STREAMER)

    def cleanTitleValue(self, value):
        if isinstance(value, basestring):
            return unicode(value).replace('\r\n', ' ').strip()
        else:
            return value

    def truncateTitle(self, title):
        shortTitle = title[:self.line_length]
        ending = (title[self.line_length:] and TitleBuilder.Templates.ELLIPSIS)
        return shortTitle + ending

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
from converter import JsonListItemConverter
from functools import wraps
from twitch import TwitchTV, TwitchVideoResolver, Keys, TwitchException
from xbmcswift2 import Plugin  # @UnresolvedImport
import urllib2, json, sys

ITEMS_PER_PAGE = 20
LINE_LENGTH = 60

PLUGIN = Plugin()
CONVERTER = JsonListItemConverter(PLUGIN, LINE_LENGTH)
TWITCHTV = TwitchTV(PLUGIN.log)


def managedTwitchExceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TwitchException as error:
            handleTwitchException(error)
    return wrapper


def handleTwitchException(exception):
    codeTranslations = {TwitchException.NO_STREAM_URL   : 30023,
                        TwitchException.STREAM_OFFLINE  : 30021,
                        TwitchException.HTTP_ERROR      : 30020,
                        TwitchException.JSON_ERROR      : 30027}
    code = exception.code
    title = 30010
    msg = codeTranslations[code]
    PLUGIN.notify(PLUGIN.get_string(title), PLUGIN.get_string(msg))


@PLUGIN.route('/')
def createMainListing():
    items = [
        {'label': PLUGIN.get_string(30005),
         'path': PLUGIN.url_for(endpoint='createListOfFeaturedStreams')
         },
        {'label': PLUGIN.get_string(30001),
         'path': PLUGIN.url_for(endpoint='createListOfGames', index='0')
         },
        {'label': PLUGIN.get_string(30002),
         'path': PLUGIN.url_for(endpoint='createFollowingList')
         },
        {'label': PLUGIN.get_string(30006),
         'path': PLUGIN.url_for(endpoint='createListOfTeams', index='0')
         },
        {'label': PLUGIN.get_string(30003),
         'path': PLUGIN.url_for(endpoint='search')
         },
        {'label': PLUGIN.get_string(30004),
         'path': PLUGIN.url_for(endpoint='showSettings')
         }
    ]
    return items


@PLUGIN.route('/createListOfFeaturedStreams/')
@managedTwitchExceptions
def createListOfFeaturedStreams():
    featuredStreams = TWITCHTV.getFeaturedStream()
    return [CONVERTER.convertStreamToListItem(featuredStream[Keys.STREAM])
            for featuredStream in featuredStreams]


@PLUGIN.route('/createListOfGames/<index>/')
@managedTwitchExceptions
def createListOfGames(index):
    index, offset, limit = calculatePaginationValues(index)

    games = TWITCHTV.getGames(offset, limit)
    items = [CONVERTER.convertGameToListItem(element[Keys.GAME]) for element in games]

    items.append(linkToNextPage('createListOfGames', index))
    return items


@PLUGIN.route('/createListForGame/<gameName>/<index>/')
@managedTwitchExceptions
def createListForGame(gameName, index):
    index, offset, limit = calculatePaginationValues(index)
    items = [CONVERTER.convertStreamToListItem(stream) for stream
             in TWITCHTV.getGameStreams(gameName, offset, limit)]

    items.append(linkToNextPage('createListForGame', index, gameName=gameName))
    return items


@PLUGIN.route('/createFollowingList/')
@managedTwitchExceptions
def createFollowingList():
    username = getUserName()
    streams = TWITCHTV.getFollowingStreams(username)
    liveStreams = [CONVERTER.convertStreamToListItem(stream) for stream in streams['live']]
    liveStreams.insert(0,{'path': PLUGIN.url_for(endpoint='createFollowingList'), 'icon': u'', 'is_playable': False, 'label': PLUGIN.get_string(30012)})
    liveStreams.append({'path': PLUGIN.url_for(endpoint='createFollowingList'), 'icon': u'', 'is_playable': False, 'label': PLUGIN.get_string(30013)})
    liveStreams.extend([CONVERTER.convertFollowersToListItem(follower) for follower in streams['others']])
    return liveStreams


@PLUGIN.route('/channelVideos/<name>/')
@managedTwitchExceptions
def channelVideos(name):
    items = [
        {'label': 'Past Broadcasts',
         'path': PLUGIN.url_for(endpoint='channelVideosList', name=name, index=0, past='true')
        },
        {'label': 'Video Highlights',
         'path': PLUGIN.url_for(endpoint='channelVideosList', name=name, index=0, past='false')
        }
    ]
    return items
    
    
@PLUGIN.route('/channelVideosList/<name>/<index>/<past>/')
@managedTwitchExceptions
def channelVideosList(name,index,past):
    index = int(index)
    offset = index * 8
    videos = TWITCHTV.getFollowerVideos(name,offset,past)
    items = [CONVERTER.convertVideoListToListItem(video) for video in videos[Keys.VIDEOS]]
    if videos[Keys.TOTAL] > (offset + 8):
        items.append(linkToNextPage('channelVideosList', index, name=name, past=past))
    return items
    
    
@PLUGIN.route('/playVideo/<id>/')
@managedTwitchExceptions
def playVideo(id):
    
    playList = TWITCHTV.getVideoChunksPlaylist(id)
    
    # Doesn't fullscreen video, might be because of xbmcswift
    #xbmc.Player().play(playlist) 
    
    try:
        # Gotta wrap this in a try/except, xbmcswift causes an error when passing a xbmc.PlayList()
        # but still plays the playlist properly
        PLUGIN.set_resolved_url(playlist)
    except:
        pass
    
    
@PLUGIN.route('/search/')
@managedTwitchExceptions
def search():
    query = PLUGIN.keyboard('', PLUGIN.get_string(30007))
    if query:
        target = PLUGIN.url_for(endpoint='searchresults', query=query, index='0')
    else:
        target = PLUGIN.url_for(endpoint='createMainListing')
    PLUGIN.redirect(target)


@PLUGIN.route('/searchresults/<query>/<index>/')
@managedTwitchExceptions
def searchresults(query, index='0'):
    index, offset, limit = calculatePaginationValues(index)
    streams = TWITCHTV.searchStreams(query, offset, limit)

    items = [CONVERTER.convertStreamToListItem(stream) for stream in streams]
    items.append(linkToNextPage('searchresults', index, query=query))
    return items


@PLUGIN.route('/showSettings/')
def showSettings():
    #there is probably a better way to do this
    PLUGIN.open_settings()
    
    
@PLUGIN.route('/playLive/<name>/')
@managedTwitchExceptions
def playLive(name):
    
    #Get Required Quality From Settings
    videoQuality = getVideoQuality()
    
    plpath = xbmc.translatePath('special://temp') + 'hlsplaylist.m3u8'
    resolver = TwitchVideoResolver(PLUGIN.log)
    resolver.saveHLSToPlaylist(name,videoQuality,plpath)
    #Play Custom Playlist
    xbmc.Player().play(plpath)
    PLUGIN.set_resolved_url(plpath)


@PLUGIN.route('/createListOfTeams/<index>/')
@managedTwitchExceptions
def createListOfTeams(index):
    index = int(index)
    teams = TWITCHTV.getTeams(index)
    items = [CONVERTER.convertTeamToListItem(item)for item in teams]
    if len(teams) == 25:
        items.append(linkToNextPage('createListOfTeams', index))
    return items


@PLUGIN.route('/createListOfTeamStreams/<team>/')
@managedTwitchExceptions
def createListOfTeamStreams(team):
    return [CONVERTER.convertTeamChannelToListItem(channel[Keys.CHANNEL])
            for channel in TWITCHTV.getTeamStreams(team)]


def calculatePaginationValues(index):
    index = int(index)
    limit = ITEMS_PER_PAGE
    offset = index * limit
    return  index, offset, limit


def getUserName():
    username = PLUGIN.get_setting('username', unicode).lower()
    if not username:
        PLUGIN.open_settings()
        username = PLUGIN.get_setting('username', unicode).lower()
    return username


def getVideoQuality():
    chosenQuality = PLUGIN.get_setting('video', unicode)
    qualities = {'0': 0, '1': 1, '2': 2, '3': 3, '4' : 4}
    return qualities.get(chosenQuality, sys.maxint)


def linkToNextPage(target, currentIndex, **kwargs):
    return {'label': PLUGIN.get_string(30011),
            'path': PLUGIN.url_for(target, index=str(currentIndex + 1), **kwargs)
            }

if __name__ == '__main__':
    PLUGIN.run()

########NEW FILE########
__FILENAME__ = twitch
#-*- encoding: utf-8 -*-
import xbmcgui, xbmc
import sys
try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus
    from urllib2 import Request, urlopen

try:
    import json
except:
    import simplejson as json  # @UnresolvedImport

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'


class JSONScraper(object):
    '''
    Encapsulates execution request and parsing of response
    '''
    
    def __init__(self, logger):
        object.__init__(self)
        self.logger = logger
        
    '''
        Download Data from an url and returns it as a String
        @param url Url to download from (e.g. http://www.google.com)
        @param headers currently unused, backwards compability
        @returns String of data from URL
    '''
    def downloadWebData(self, url, headers=None):
        data = ""
        try:
            req = Request(url)
            req.add_header(Keys.USER_AGENT, USER_AGENT)
            response = urlopen(req)
            
            if sys.version_info < (3, 0):
                data = response.read()
            else:
                data = response.readall().decode('utf-8')
            response.close()
        except:
            raise TwitchException(TwitchException.HTTP_ERROR)
        return data
        
    '''
        Download Data from an url and returns it as JSON
        @param url Url to download from
        @param headers currently unused, backwards compability
        @returns JSON Object with data from URL
    '''
    def getJson(self, url, headers=None):
        try:
            jsonString = self.downloadWebData(url, headers)
        except:
            raise TwitchException(TwitchException.HTTP_ERROR)
        try:
            jsonDict = json.loads(jsonString)
            self.logger.debug(json.dumps(jsonDict, indent=4, sort_keys=True))
            return jsonDict
        except:
            raise TwitchException(TwitchException.JSON_ERROR)


class TwitchTV(object):
    '''
    Uses Twitch API to fetch json-encoded objects
    every method returns a dict containing the objects\' values
    '''
    def __init__(self, logger):
        self.logger = logger
        self.scraper = JSONScraper(logger)

    def getFeaturedStream(self):
        url = ''.join([Urls.STREAMS, Keys.FEATURED])
        return self._fetchItems(url, Keys.FEATURED)

    def getGames(self, offset=10, limit=10):
        options = Urls.OPTIONS_OFFSET_LIMIT.format(offset, limit)
        url = ''.join([Urls.GAMES, Keys.TOP, options])
        return self._fetchItems(url, Keys.TOP)

    def getGameStreams(self, gameName, offset=10, limit=10):
        quotedName = quote_plus(gameName)
        options = Urls.OPTIONS_OFFSET_LIMIT_GAME.format(offset, limit, quotedName)
        url = ''.join([Urls.BASE, Keys.STREAMS, options])
        return self._fetchItems(url, Keys.STREAMS)

    def searchStreams(self, query, offset=10, limit=10):
        quotedQuery = quote_plus(query)
        options = Urls.OPTIONS_OFFSET_LIMIT_QUERY.format(offset, limit, quotedQuery)
        url = ''.join([Urls.SEARCH, Keys.STREAMS, options])
        return self._fetchItems(url, Keys.STREAMS)

    def getFollowingStreams(self, username):
        #Get ChannelNames
        followingChannels = self.getFollowingChannelNames(username)
        channelNames = self._filterChannelNames(followingChannels)

        #get Streams of that Channels
        options = '?channel=' + ','.join([channels[Keys.NAME] for channels in channelNames])
        url = ''.join([Urls.BASE, Keys.STREAMS, options])
        channels = {'live' : self._fetchItems(url, Keys.STREAMS)}
        channels['others'] = channelNames
        return channels
        
    def getFollowerVideos(self, username, offset, past):
        url = Urls.CHANNEL_VIDEOS.format(username,offset,past)
        items = self.scraper.getJson(url)
        return {Keys.TOTAL : items[Keys.TOTAL], Keys.VIDEOS : items[Keys.VIDEOS]}
        
    def getVideoChunks(self, id):
        url = Urls.VIDEO_CHUNKS.format(id)
        return self.scraper.getJson(url)
        
    def getVideoTitle(self, id):
        url = Urls.VIDEO_INFO.format(id)
        return self._fetchItems(url, 'title')
        
    
    def getVideoChunksPlaylist(self, id):
        vidChunks = self.getVideoChunks(id)
        chunks = vidChunks['chunks']['live']
        title = self.getVideoTitle(id)
        itemTitle = '%s - Part {0} of %s' % (title, len(chunks))
        
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        
        # For some reason first item is skipped, so added a dummy first item to fix
        # theres probably a better way
        playlist.add('', xbmcgui.ListItem('', thumbnailImage=vidChunks['preview']))
        curN = 0
        for chunk in chunks:
            curN += 1
            playlist.add(chunk['url'], xbmcgui.ListItem(itemTitle.format(curN), thumbnailImage=vidChunks['preview']))
            
        return playlist
        
    def getFollowingChannelNames(self, username):
        quotedUsername = quote_plus(username)
        url = Urls.FOLLOWED_CHANNELS.format(quotedUsername)
        return self._fetchItems(url, Keys.FOLLOWS)

    def getTeams(self, index):
        return self._fetchItems(Urls.TEAMS.format(str(index * 25)), Keys.TEAMS)

    def getTeamStreams(self, teamName):
        '''
        Consider this method to be unstable, because the
        requested resource is not part of the official Twitch API
        '''
        quotedTeamName = quote_plus(teamName)
        url = Urls.TEAMSTREAM.format(quotedTeamName)
        return self._fetchItems(url, Keys.CHANNELS)

    def _filterChannelNames(self, channels):
        tmp = [{Keys.DISPLAY_NAME : item[Keys.CHANNEL][Keys.DISPLAY_NAME], Keys.NAME : item[Keys.CHANNEL][Keys.NAME], Keys.LOGO : item[Keys.CHANNEL][Keys.LOGO]} for item in channels]
        return sorted(tmp, key=lambda k: k[Keys.DISPLAY_NAME]) 

    def _fetchItems(self, url, key):
        items = self.scraper.getJson(url)
        return items[key] if items else []


class TwitchVideoResolver(object):
    '''
    Resolves the RTMP-Link to a given Channelname
    Uses Justin.TV API
    '''
    
    def __init__(self, logger):
        object.__init__(self)
        self.logger = logger
        self.scraper = JSONScraper(logger)

    def getRTMPUrl(self, channelName, maxQuality):
        swfUrl = self._getSwfUrl(channelName)
        streamQualities = self._getStreamsForChannel(channelName)
        
        self.logger.debug("=== URL and available Streams ===")
        self.logger.debug(json.dumps(swfUrl, sort_keys=True, indent=4))
        
        # check that api response isn't empty (i.e. stream is offline)
        if streamQualities:
            items = [self._parseStreamValues(stream, swfUrl)
                     for stream in streamQualities
                     if self._streamIsAccessible(stream)]
            if items:
                self.logger.debug("=== Accessible Streams ===")
                self.logger.debug(json.dumps(items, sort_keys=True, indent=4))
                return self._bestMatchForChosenQuality(items, maxQuality)[Keys.RTMP_URL]
            else:
                raise TwitchException(TwitchException.NO_STREAM_URL)
        else:
            raise TwitchException(TwitchException.STREAM_OFFLINE)

    #downloads Playlist from twitch and passes it to subfunction for custom playlist generation
    def saveHLSToPlaylist(self, channelName, maxQuality, fileName):
        #Get Access Token (not necessary at the moment but could come into effect at any time)
        tokenurl= Urls.CHANNEL_TOKEN.format(channelName)
        channeldata = self.scraper.getJson(tokenurl)
        channeltoken= channeldata['token']
        channelsig= channeldata['sig']
        
        #Download Multiple Quality Stream Playlist
        data = self.scraper.downloadWebData(Urls.HLS_PLAYLIST.format(channelName,channelsig,channeltoken))
        
        playlist = self._saveHLSToPlaylist(data,maxQuality)
        
        #Write Custom Playlist
        text_file = open(fileName, "w")
        text_file.write(str(playlist))
        text_file.close()
        return

    #split off from main function so we can feed custom data for test cases + speedtest
    def _saveHLSToPlaylist(self, data, maxQuality):
        #if channel is offline, quit here
        if(data=="<p>No Results</p>"):
            raise TwitchException(TwitchException.STREAM_OFFLINE)
        
        quality = ['Source','High','Medium','Low','Mobile'] # Define Qualities
        if(maxQuality>=len(quality)): #check if maxQuality is supported
            raise TwitchException()
        
        lines = data.split('\n') # split into lines
        
        playlist = lines[:2] # take first two lines into playlist
        qualities = [None] * len(quality) # create quality based None array
        
        lines_iterator = iter(lines[2:]) #start iterator after the first two lines
        for line in lines_iterator: # start after second line
            # if line contains 'EXT-X-TWITCH-RESTRICTED' drop the line
            if 'EXT-X-TWITCH-RESTRICTED' in line:
                continue
            
            def concat_next_3_lines(): # helper function for concatination
                return '\n'.join([line,next(lines_iterator),next(lines_iterator)])
                
            #if a line with quality is detected, put it into qualities array
            if quality[0] in line:
                qualities[0] = concat_next_3_lines()
            elif quality[1] in line:
                qualities[1] = concat_next_3_lines()
            elif quality[2] in line:
                qualities[2] = concat_next_3_lines()
            elif quality[3] in line:
                qualities[3] = concat_next_3_lines()
            elif quality[4] in line:
                qualities[4] = concat_next_3_lines()
            else:
                pass # drop other lines
        
        if qualities[maxQuality]: # prefered quality is not None -> available
            playlist.append(qualities[maxQuality])
        else: #prefered quality is not available, append all qualities that are not None, could be changed to respect maxQuality
            for q in qualities:
                if q is not None:
                    playlist.append(q)
        
        playlist = '\n'.join(playlist) + '\n'
        return playlist


    def _getSwfUrl(self, channelName):
        url = Urls.TWITCH_SWF + channelName
        headers = {Keys.USER_AGENT: USER_AGENT,
                   Keys.REFERER: Urls.TWITCH_TV + channelName}
        req = Request(url, None, headers)
        response = urlopen(req)
        return response.geturl()

    def _streamIsAccessible(self, stream):
        stream_is_public = (stream.get(Keys.NEEDED_INFO) != "channel_subscription")
        stream_has_token = stream.get(Keys.TOKEN)

        if stream.get(Keys.CONNECT) is None:
            return False

        return stream_is_public and stream_has_token

    def _getStreamsForChannel(self, channelName):
        scraper = JSONScraper(self.logger)
        url = Urls.TWITCH_API.format(channel=channelName)
        return scraper.getJson(url)

    def _parseStreamValues(self, stream, swfUrl):
        streamVars = {Keys.SWF_URL: swfUrl}
        streamVars[Keys.RTMP] = stream[Keys.CONNECT]
        streamVars[Keys.PLAYPATH] = stream.get(Keys.PLAY)

        if stream[Keys.TOKEN]:
            token = stream[Keys.TOKEN].replace('\\', '\\5c').replace(' ', '\\20').replace('"', '\\22')
        else:
            token = ''

        streamVars[Keys.TOKEN] = (' jtv=' + token) if token else ''
        quality = int(stream.get(Keys.VIDEO_HEIGHT, 0))
        bitrate = int(stream.get(Keys.BITRATE, 0))
        return {Keys.QUALITY: quality,
                Keys.BITRATE: bitrate,
                Keys.RTMP_URL: Urls.FORMAT_FOR_RTMP.format(**streamVars)}

    def _bestMatchForChosenQuality(self, streams, maxQuality):
        # sorting on resolution, then bitrate, both ascending 
        streams.sort(key=lambda t: (t[Keys.QUALITY], t[Keys.BITRATE]))
        self.logger.debug("Available streams sorted: %s" % streams)
        for stream in streams:
            if stream[Keys.QUALITY] <= maxQuality:
                bestMatch = stream
        self.logger.debug("Chosen Stream is: %s" % bestMatch)
        return bestMatch


class Keys(object):
    '''
    Should not be instantiated, just used to categorize
    string-constants
    '''

    BITRATE = 'bitrate'
    CHANNEL = 'channel'
    CHANNELS = 'channels'
    CONNECT = 'connect'
    BACKGROUND = 'background'
    DISPLAY_NAME = 'display_name'
    FEATURED = 'featured'
    FOLLOWS = 'follows'
    GAME = 'game'
    LOGO = 'logo'
    BOX = 'box'
    LARGE = 'large'
    NAME = 'name'
    NEEDED_INFO = 'needed_info'
    PLAY = 'play'
    PLAYPATH = 'playpath'
    QUALITY = 'quality'
    RTMP = 'rtmp'
    STREAMS = 'streams'
    REFERER = 'Referer'
    RTMP_URL = 'rtmpUrl'
    STATUS = 'status'
    STREAM = 'stream'
    SWF_URL = 'swfUrl'
    TEAMS = 'teams'
    TOKEN = 'token'
    TOP = 'top'
    TOTAL = '_total'
    USER_AGENT = 'User-Agent'
    VIDEOS = "videos"
    VIDEO_BANNER = 'video_banner'
    VIDEO_HEIGHT = 'video_height'
    VIEWERS = 'viewers'
    PREVIEW = 'preview'
    TITLE = 'title'


class Patterns(object):
    '''
    Should not be instantiated, just used to categorize
    string-constants
    '''
    VALID_FEED = "^https?:\/\/(?:[^\.]*.)?(?:twitch|justin)\.tv\/([a-zA-Z0-9_]+).*$"
    IP = '.*\d+\.\d+\.\d+\.\d+.*'
    EXPIRATION = '.*"expiration": (\d+)[^\d].*'


class Urls(object):
    '''
    Should not be instantiated, just used to categorize
    string-constants
    '''
    TWITCH_TV = 'http://www.twitch.tv/'

    BASE = 'https://api.twitch.tv/kraken/'
    FOLLOWED_CHANNELS = BASE + 'users/{0}/follows/channels?limit=100'
    GAMES = BASE + 'games/'
    STREAMS = BASE + 'streams/'
    SEARCH = BASE + 'search/'
    TEAMS = BASE + 'teams?limit=25&offset={0}'

    TEAMSTREAM = 'http://api.twitch.tv/api/team/{0}/live_channels.json'
    CHANNEL_TOKEN = 'http://api.twitch.tv/api/channels/{0}/access_token'

    OPTIONS_OFFSET_LIMIT = '?offset={0}&limit={1}'
    OPTIONS_OFFSET_LIMIT_GAME = OPTIONS_OFFSET_LIMIT + '&game={2}'
    OPTIONS_OFFSET_LIMIT_QUERY = OPTIONS_OFFSET_LIMIT + '&q={2}'

    TWITCH_API = "http://usher.justin.tv/find/{channel}.json?type=any&group=&channel_subscription="
    TWITCH_SWF = "http://www.justin.tv/widgets/live_embed_player.swf?channel="
    FORMAT_FOR_RTMP = "{rtmp}/{playpath} swfUrl={swfUrl} swfVfy=1 {token} live=1"  # Pageurl missing here
    HLS_PLAYLIST = 'http://usher.twitch.tv/select/{0}.m3u8?nauthsig={1}&nauth={2}&allow_source=true'
    
    CHANNEL_VIDEOS = 'https://api.twitch.tv/kraken/channels/{0}/videos?limit=8&offset={1}&broadcasts={2}'
    VIDEO_CHUNKS = 'https://api.twitch.tv/api/videos/{0}'
    VIDEO_INFO = 'https://api.twitch.tv/kraken/videos/{0}'
        


class TwitchException(Exception):

    NO_STREAM_URL = 0
    STREAM_OFFLINE = 1
    HTTP_ERROR = 2
    JSON_ERROR = 3

    def __init__(self, code):
        Exception.__init__(self)
        self.code = code

    def __str__(self):
        return repr(self.code)

########NEW FILE########
