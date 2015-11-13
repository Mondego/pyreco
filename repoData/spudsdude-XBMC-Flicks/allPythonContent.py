__FILENAME__ = default
"""
    Plugin for streaming your Netflix Instant Queue
"""

# main imports
import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import urllib

# plugin constants
__plugin__ = "xbmcflicks"
__author__ = "teamumx"
__url__ = ""
__svn_url__ = ""
__useragent__ = ""
__credits__ = "Team UMX"
__version__ = "1.0.0"
__svn_revision__ = "$Revision$"
__XBMC_Revision__ = "22965"
#__settings__ = xbmcaddon.Addon(id='plugin.video.xbmcflicks')

if ( __name__ == "__main__" ):
        import resources.lib.menu as menu
        menu



########NEW FILE########
__FILENAME__ = iqueue
from Netflix import *
import getopt
import time 
import re
import xbmcplugin, xbmcaddon, xbmcgui, xbmc
import urllib, urllib2
import webbrowser
import os
from settings import *
from xinfo import *
import simplejson

# parameter keys
PARAMETER_KEY_MODE = "mode"
SUBMENU1a = "Movies"
SUBMENU1b = "TV Shows"
MODE1a = 11
MODE1b = 12

MY_USER = {
        'request': {
             'key': '',
             'secret': ''
        },
        'access': {
            'key': '',
            'secret': ''
        }
}

def __init__(self):
    self.data = []

def startBrowser(url):
	cmd="open /Applications/Firefox.app '"+url+"'"
	print cmd
	os.system(cmd)
	

# AUTH 
def getAuth(netflix, verbose):
    print ".. getAuth called .."
    print "OSX Setting is set to: " + str(OSX)
    netflix.user = NetflixUser(MY_USER,netflix)
    print ".. user configured .."

    #handles all the initial auth with netflix
    if MY_USER['request']['key'] and not MY_USER['access']['key']:
        tok = netflix.user.getAccessToken( MY_USER['request'] )
        if(VERBOSE_USER_LOG):
            print "now put this key / secret in MY_USER.access so you don't have to re-authorize again:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
        MY_USER['access']['key'] = tok.key
        MY_USER['access']['secret'] = tok.secret
        saveUserInfo()
        dialog = xbmcgui.Dialog()
        dialog.ok("Settings completed", "You must restart the xbmcflicks plugin")
        print "Settings completed", "You must restart the xbmcflicks plugin"
        sys.exit(1)

    elif not MY_USER['access']['key']:
        (tok, url) = netflix.user.getRequestToken()
        if(VERBOSE_USER_LOG):
            print "Authorize user access here: %s" % url
            print "and then put this key / secret in MY_USER.request:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
            print "and run again."
        #open web page with urllib so customer can authorize the app

        if(OSX):
            startBrowser(url)
        else:
            webbrowser.open(url)
            print "browser open has completed"
            
        #display click ok when finished adding xbmcflicks as authorized app for your netflix account
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("After you have linked xbmcflick in netflix.", "Click OK after you finished the link in your browser window.")
        print "The dialog was displayed, hopefully you read the text and waited until you authorized it before clicking ok."
        MY_USER['request']['key'] = tok.key
        if(VERBOSE_USER_LOG):
            print "user key set to: " + tok.key
        MY_USER['request']['secret'] = tok.secret
        if(VERBOSE_USER_LOG):
            print "user secret set to: " + tok.secret
        #now run the second part, getting the access token
        tok = netflix.user.getAccessToken( MY_USER['request'] )
        if(VERBOSE_USER_LOG):
            print "now put this key / secret in MY_USER.access so you don't have to re-authorize again:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
        MY_USER['access']['key'] = tok.key
        MY_USER['access']['secret'] = tok.secret
        #now save out the settings
        saveUserInfo()
        #exit script, user must restart
        dialog.ok("Settings completed", "You must restart XBMC")
        print "Settings completed", "You must restart XBMC"
        exit
        sys.exit(1)

    return netflix.user

def saveUserInfo():
    #create the file
    f = open(os.path.join(str(USERINFO_FOLDER), 'userinfo.txt'),'w+')
    setting ='requestKey=' + MY_USER['request']['key'] + '\n' + 'requestSecret=' + MY_USER['request']['secret'] + '\n' +'accessKey=' + MY_USER['access']['key']+ '\n' + 'accessSecret=' + MY_USER['access']['secret']
    f.write(setting)
    f.close()

# END AUTH
def checkplayercore():
    checkFile = os.path.join(str(XBMCPROFILE), 'playercorefactory.xml')
    havefile = os.path.isfile(checkFile)
    if(not havefile):
        #copy file data from addon folder
        fileWithData = os.path.join(str(RESOURCE_FOLDER), 'playercorefactory.xml')
        if not os.path.exists('C:\Program Files (x86)'):
            fileWithData = os.path.join(str(RESOURCE_FOLDER), 'playercorefactory32.xml')
        if not os.path.exists('C:\Program Files'):
            fileWithData = os.path.join(str(RESOURCE_FOLDER), 'playercorefactoryOSX.xml')
        data = open(str(fileWithData),'r').read()
        f = open(checkFile,'w+')
        f.write(data)
        f.close()
    
def checkadvsettings():
    checkFile = os.path.join(str(XBMCPROFILE), 'advancedsettings.xml')
    havefile = os.path.isfile(checkFile)
    if(not havefile):
        #copy file from addon folder
        fileWithData = os.path.join(str(RESOURCE_FOLDER), 'advancedsettings.xml')
        data = open(str(fileWithData),'r').read()
        f = open(checkFile,'w+')
        f.write(data)
        f.close()

def addDirectoryItem(curX, isFolder=True, parameters={}, thumbnail=None):
    ''' Add a list item to the XBMC UI.'''
    if thumbnail:
        li = xbmcgui.ListItem(curX.Title, thumbnailImage=thumbnail)
    else:
        li = xbmcgui.ListItem(curX.Title)
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)
    li.setInfo( type="Video", infoLabels={ "Mpaa": curX.Mpaa, "TrackNumber": int(curX.Position), "Year": int(curX.Year), "OriginalTitle": curX.Title, "Title": curX.TitleShort, "Rating": float(curX.Rating)*2, "Duration": str(int(curX.Runtime)/60), "Director": curX.Directors, "Genre": curX.Genres, "CastAndRole": curX.Cast, "Plot": curX.Synop})
    commands = []
    modScripLoc = os.path.join(str(LIB_FOLDER), 'modQueue.py')   
    argsRemove = str(curX.ID) + "delete"
    argsAdd = str(curX.ID) + "post"
    argsSimilar = str(curX.ID)
    runnerRemove = "XBMC.RunScript(" + modScripLoc + ", " + argsRemove + ")"
    runnerAdd = "XBMC.RunScript(" + modScripLoc + ", " + argsAdd + ")"
    runnerSearch = "XBMC.RunScript(" + modScripLoc + ", " + argsSimilar + ")"

    argsRemoveD = str(curX.ID) + "discdelete"
    argsAddD = str(curX.ID) + "discpost"
    argsAddTopD = str(curX.ID) + "disctoppost"
    argsSimilarD = str(curX.ID)
    runnerRemoveD = "XBMC.RunScript(" + modScripLoc + ", " + argsRemoveD + ")"
    runnerAddD = "XBMC.RunScript(" + modScripLoc + ", " + argsAddD + ")"
    runnerAddTopD = "XBMC.RunScript(" + modScripLoc + ", " + argsAddTopD + ")"
    runnerSearchD = "XBMC.RunScript(" + modScripLoc + ", " + argsSimilarD + ")"

    if(not curX.nomenu):
        if(not curX.TvEpisode):
            commands.append(( 'Netflix: Add to Disc Queue', runnerAddD, ))
            commands.append(( 'Netflix: Remove From Disc Queue', runnerRemoveD, ))
            commands.append(( 'Netflix: Add to Top of Disc Queue', runnerAddTopD, ))
        else:
            commands.append(( 'Netflix: Add Season to Disc Queue', runnerAddD, ))
            commands.append(( 'Netflix: Remove Season From Disc Queue', runnerRemoveD, ))
            commands.append(( 'Netflix: Add to Top of Disc Queue', runnerAddTopD, ))

        if(not curX.TvEpisode):
            commands.append(( 'Netflix: Add to Instant Queue', runnerAdd, ))
            commands.append(( 'Netflix: Remove From Instant Queue', runnerRemove, ))
            #commands.append(( 'Netflix: Find Similar', runnerSearch, ))
        else:
            commands.append(( 'Netflix: Add Entire Season to Instant Queue', runnerAdd, ))
            commands.append(( 'Netflix: Remove Entire Season From Instant Queue', runnerRemove, ))

    li.addContextMenuItems( commands )
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url, listitem=li, isFolder=isFolder)

def addLink(name,url,curX,rootID=None):
    ok=True
    rFolder = str(ROOT_FOLDER)
    lFolder = str(LIB_FOLDER)
    commands = []

    modScripLoc = os.path.join(lFolder, 'modQueue.py')
    argsRemove = str(curX.ID) + "delete"
    argsAdd = str(curX.ID) + "post"
    argsSimilar = str(curX.ID)
    if rootID:
        argsRemove = str(rootID) + "delete"
        argsAdd = str(rootID) + "post"
        argsSimilar = str(rootID)
    runnerRemove = "XBMC.RunScript(" + modScripLoc + ", " + argsRemove + ")"
    runnerAdd = "XBMC.RunScript(" + modScripLoc + ", " + argsAdd + ")"
    runnerSearch = "XBMC.RunScript(" + modScripLoc + ", " + argsSimilar + ")"

    if(not curX.TvEpisode):
        commands.append(( 'Netflix: Add to Instant Queue', runnerAdd, ))
        commands.append(( 'Netflix: Remove From Instant Queue', runnerRemove, ))
        #commands.append(( 'Netflix: Find Similar', runnerSearch, ))
    else:
        commands.append(( 'Netflix: Add Entire Season to Instant Queue', runnerAdd, ))
        commands.append(( 'Netflix: Remove Entire Season From Instant Queue', runnerRemove, ))
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=curX.Poster)
    liz.setInfo( type="Video", infoLabels={ "Mpaa": str(curX.Mpaa), "TrackNumber": int(str(curX.Position)), "Year": int(str(curX.Year)), "OriginalTitle": str(curX.Title), "Title": str(curX.TitleShort), "Rating": float(curX.Rating)*2, "Duration": str(int(curX.Runtime)/60), "Director": str(curX.Directors), "Genre": str(curX.Genres), "CastAndRole": str(curX.Cast), "Plot": str(curX.Synop) })
    liz.addContextMenuItems( commands )
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz, isFolder=False)

    return ok

def addLinkDisc(name,url,curX,rootID=None):
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=curX.Poster)
    liz.setInfo( type="Video", infoLabels={ "Mpaa": str(curX.Mpaa), "TrackNumber": int(str(curX.Position)), "Year": int(str(curX.Year)), "OriginalTitle": str(curX.Title), "Title": str(curX.TitleShort), "Rating": float(curX.Rating)*2, "Duration": str(int(curX.Runtime)/60), "Director": str(curX.Directors), "Genre": str(curX.Genres), "CastAndRole": str(curX.Cast), "Plot": str(curX.Synop) })

    commands = []
    filename = curX.ID + '_disc.html'
    url = os.path.join(str(REAL_LINK_PATH), filename)

    modScripLoc = os.path.join(str(LIB_FOLDER), 'modQueue.py')
    
    argsRemoveD = str(curX.ID) + "discdelete"
    argsAddD = str(curX.ID) + "discpost"
    argsAddTopD = str(curX.ID) + "disctoppost"
    
    argsSimilarD = str(curX.ID)
    if rootID:
        argsRemoveD = str(rootID) + "discdelete"
        argsAddD = str(rootID) + "discpost"
        argsSimilarD = str(rootID)
    runnerRemoveD = "XBMC.RunScript(" + modScripLoc + ", " + argsRemoveD + ")"
    runnerAddD = "XBMC.RunScript(" + modScripLoc + ", " + argsAddD + ")"
    runnerAddTopD = "XBMC.RunScript(" + modScripLoc + ", " + argsAddTopD + ")"
    runnerSearchD = "XBMC.RunScript(" + modScripLoc + ", " + argsSimilarD + ")"

    if(not curX.TvEpisode):
        commands.append(( 'Netflix: Add to Disc Queue', runnerAddD, ))
        commands.append(( 'Netflix: Remove From Disc Queue', runnerRemoveD, ))
        commands.append(( 'Netflix: Add to Top of Disc Queue', runnerAddTopD, ))
    else:
        commands.append(( 'Netflix: Add Season to Disc Queue', runnerAddD, ))
        commands.append(( 'Netflix: Remove Season From Disc Queue', runnerRemoveD, ))
        commands.append(( 'Netflix: Add to Top of Disc Queue', runnerAddTopD, ))

    liz.addContextMenuItems( commands )
    whichHandler = sys.argv[1]
    ok=xbmcplugin.addDirectoryItem(handle=int(whichHandler),url=url,listitem=liz, isFolder=False)

    return ok

def writeLinkFile(id, title):
    #check to see if we already have the file
    filename = id + '.html'
    fileLoc = os.path.join(str(LINKS_FOLDER), str(filename))
    havefile = os.path.isfile(fileLoc)
    if(not havefile):
        #create the file
        player = "WiPlayerCommunityAPI"
        if(useAltPlayer):
            player = "WiPlayer"
        if(not IN_CANADA):
            redirect = "<!doctype html public \"-//W3C//DTD HTML 4.0 Transitional//EN\"><html><head><title>Requesting Video: " + title + "</title><meta http-equiv=\"REFRESH\" content=\"0;url=http://www.netflix.com/" + player + "?lnkctr=apiwn&nbb=y&devKey=gnexy7jajjtmspegrux7c3dj&movieid=" + id + "\"></head><body bgcolor=\"#FF0000\"> <p>Redirecting to Netflix in a moment ...</p></body></html>"
        else:
            redirect = "<!doctype html public \"-//W3C//DTD HTML 4.0 Transitional//EN\"><html><head><title>Requesting Video: " + title + "</title><meta http-equiv=\"REFRESH\" content=\"0;url=http://www.netflix.ca/" + player + "?lnkctr=apiwn&nbb=y&devKey=gnexy7jajjtmspegrux7c3dj&movieid=" + id + "\"></head><body bgcolor=\"#FF0000\"> <p>Redirecting to Netflix in a moment ...</p></body></html>"
        f = open(fileLoc,'w+')
        f.write(redirect)
        f.close()

#writeDiscLinkFile
def writeDiscLinkFile(id, title, webURL):
    #check to see if we already have the file
    filename = id + '_disc.html'
    fileLoc = os.path.join(str(LINKS_FOLDER), str(filename))
    havefile = os.path.isfile(fileLoc)
    if(not havefile):
        #create the file
        player = "WiPlayerCommunityAPI"
        if(useAltPlayer):
            player = "WiPlayer"
        redirect = "<!doctype html public \"-//W3C//DTD HTML 4.0 Transitional//EN\"><html><head><title>Requesting Video: " + title + "</title><meta http-equiv=\"REFRESH\" content=\"0;url=" + webURL + "\"></head><body bgcolor=\"#0000cc\"> <p>Redirecting to Netflix in a moment ...</p></body></html>"
        f = open(fileLoc,'w+')
        f.write(redirect)
        f.close()

def checkFormat(netflix, curX):
    strLinkUrl = "http://api.netflix.com/catalog/titles/movies/" + curX.ID
    try:
        movie = netflix.catalog.getTitle(strLinkUrl)
        disc = NetflixDisc(movie['catalog_title'],netflix)
    except:
        print "unable to get details of the format of the movie, returning empty object"
        return False
    formats = disc.getInfo('formats')
    strFormats = simplejson.dumps(formats,indent=4)
    if(VERBOSE_USER_LOG):
        print "formats json: " + strFormats
    matchFormat = re.search(r'"label": "instant"', strFormats)
    if matchFormat:
        return True
    else:
        return False

def getSummary(netflix, curX):
    #time.sleep(.11)
    strCastClean = ""
    strSynopsisCleaned = ""
    strDirectorsCleaned = ""
    strLinkUrl = "http://api.netflix.com/catalog/titles/movies/" + curX.ID
    #try to get movie from catalog
    movie = None
    disc = None
    
    try:
        movie = netflix.catalog.getTitle(strLinkUrl)
        disc = NetflixDisc(movie['catalog_title'],netflix)
    except:
        #unable to get details, return empty object
        return curX
    
    #try to get synop
    try:
        synopsis = disc.getInfo('synopsis')
        strSynopsis = simplejson.dumps(synopsis, indent=4)
        strSynopsisCleaned = strSynopsis
        #clean out all html tags
        for match in re.finditer(r"(?sm)(<[^>]+>)", strSynopsis):
            strSynopsisCleaned = strSynopsisCleaned.replace(match.group(1),"")
        #clean out actor names that follows the name of character in movie
        for match2 in re.finditer(r"(?sm)(\([^\)]+\))", strSynopsisCleaned):
            strSynopsisCleaned = strSynopsisCleaned.replace(match2.group(1),"")
        #strip out the text ""synopsis": " and "{}|" and then clean up
        strSynopsisCleaned = strSynopsisCleaned.replace("\"synopsis\": ", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("{", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("}", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("|", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("  ", " ")
        strSynopsisCleaned = strSynopsisCleaned.replace("\"", "")
        strSynopsisCleaned = strSynopsisCleaned.strip()
        if(DEBUG):
            print "Cleaned Synopsis: %s" % strSynopsisCleaned
    except:
        print "No Synop Data available for " + curX.Title
    curX.Synop = strSynopsisCleaned

    return curX

def availableTimeRemaining(expires):
    """Get seconds since epoch (UTC)."""
    curTime = int(time.time())
##    if(DEBUG):
##        print "current time: " + str(curTime)
##        print "expires: " + str(expires)
    try:
        result = str(time.strftime("%d %b %Y", time.localtime(int(expires))))
##        if(DEBUG):
##            print "result of time conversion is" + str(result)
        return result
    except:
        try:
            expiresObj = re.search(r"(\d*)000", expires)
            if expiresObj:
                expires = expiresObj.group(1)
            result = str(time.strftime("%d %b %Y", time.localtime(int(expires))))
            if(DEBUG):
                print "result of time conversion is" + str(result)
            return result
        except:
            return ""

def checkIsAvailable(strStart, strEnd):
    startTime = 0
    endTime = 0
    curTime = int(time.time())
    print "current time is: " + str(curTime)
    startsObj = re.search(r"(\d*)000", strStart)
    if startsObj:
        startTime = startsObj.group(1)
##        print "start time of: " + str(startTime)
    else:
        return False
    expiresObj = re.search(r"(\d*)000", strEnd)
    if expiresObj:
        endTime = expiresObj.group(1)
##        print "end time of: " + str(endTime)
    else:
        return False
    if(int(startTime) <= int(curTime)):
##        print "start is prior to current time"
        if(int(endTime) >= int(curTime)):
##            print "end is greater then current time"
            return True
    return False

def getMovieDataFromFeed(curX, curQueueItem, bIsEpisode, netflix, instantAvail, intDisplayWhat, forceExpand=None):
    #if display what = 0, will only show instant queue items
    #if display what = 1, will only display movies
    #if display what = 2, will only display tv shows
    #if display what = 3, working with Movies in Disc Queue
    #if display what = 4, working with TvShows in Disc Queue
    #if display what = 5, working with Everything in Disc Queue
    #if the value is not set, everything is shown (instant queue items)

    showTvShow = True
    showMovies = True
    discQueue = False
    
    if intDisplayWhat:
        if (int(intDisplayWhat) == 0):
            discQueue = False
        if (int(intDisplayWhat) == 1):
            showTvShow = False
        if (int(intDisplayWhat) == 2):
            showMovies = False
        if (int(intDisplayWhat) == 3):
            discQueue = True
        if (int(intDisplayWhat) == 4):
            showTvShow = False
            discQueue = True
        if (int(intDisplayWhat) == 5):
            showMovies = False
            discQueue = True

    if(instantAvail):
        discQueue = False
    
    #if it's a tv show it should be a folder, not a listing
    if re.search(r"{(u'episode_short'.*?)}", curQueueItem, re.DOTALL | re.MULTILINE):
        curX.TvShow = True
    if re.search(r"u'name': u'Television'", curQueueItem, re.IGNORECASE):
        curX.TvShow = True
    
    if (curX.TvShow):
        if(not showTvShow):
            return curX
    else:
        if(not showMovies):
            return curX

    iRating = 10001

    matchAvailObj = re.search(r'"NetflixCatalog.Model.InstantAvailability".*?}, "Available": (?P<iAvail>true|false|null), "AvailableFrom": .*?\((?P<availFrom>\d*)\).*?, "AvailableTo": ".*?\((?P<availUntil>\d*)\).*?"Runtime": (\d*), "Rating": .*?\}', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchAvailObj:
        curX.oData = True
        result = matchAvailObj.group(1)
        print "----------------------------------"
        print " matched formats for oData "
        print " iAvail: " + str(matchAvailObj.group(1).strip())
        curX.oData = True
        if(matchAvailObj.group(1).strip() == "true"):
            curX.iAvail = True
        if(matchAvailObj.group(1).strip() == "True"):
            curX.iAvail = True
        else:
            curX.iAvail = False
        curX.iAvailFrom = matchAvailObj.group("availFrom")
        curX.iAvailTil = matchAvailObj.group("availUntil")
        curX.iAvail = checkIsAvailable(curX.iAvailFrom, curX.iAvailTil)
        if(DEBUG):
            print "------------------"
            print "is avail: " + str(curX.iAvail) + " avail from: " + str(curX.iAvailFrom) + " until: " + str(curX.iAvailTil)

    #mpaa
    if(DEBUG):
        print "-------------------------------------"
        print curQueueItem
    matchMpaa = re.search(r'[\'"]scheme[\'"]: u{0,1}[\'"]http://api.netflix.com/categories/mpaa_ratings[\'"],.*?[\'"]label[\'"]: u{0,1}[\'"](.*?)"', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchMpaa:
        curX.Mpaa = matchMpaa.group(1).strip()
    else:
        #matching by maturity_level
        matchRating = re.search(r"maturity_level': (\d{1,4}),", curQueueItem, re.DOTALL | re.MULTILINE)
        if matchRating:
            iRating = int(matchRating.group(1).strip())
            curX.MaturityLevel = iRating
            if (iRating == 0):
                curX.Mpaa = "0 Rating"
            elif (iRating == 10):
                curX.Mpaa = "TV-Y"
            elif (iRating == 20):
                curX.Mpaa = "TV-Y7"
            elif (iRating == 40):
                curX.Mpaa = "G"
            elif (iRating == 50):
                curX.Mpaa = "TV-G" 
            elif (iRating == 60):
                curX.Mpaa = "PG"
            elif (iRating == 75):
                curX.Mpaa = "NR (Kids)"
            elif (iRating == 80):
                curX.Mpaa = "PG-13"
            elif (iRating == 90):
                curX.Mpaa = "TV-14"
            elif (iRating == 100):
                curX.Mpaa = "R"
            elif (iRating == 110):
                curX.Mpaa = "TV-MA"
            elif (iRating == 130):
                curX.Mpaa = "NR (Mature)"
            elif (iRating == 1000):
                curX.Mpaa = "UR (Mature)"
            else:
                curX.Mpaa = matchRating.group(1)
        else:
            matchRating2 = re.search(r'"Synopsis": "(.*?)", "AverageRating": (.{1,5}), "ReleaseYear": (\d{4}), "Url": ".*?", "Runtime": (\d{1,10}), "Rating": "(.*?)"', curQueueItem)
            if matchRating2:
                curX.Mpaa = matchRating2.group(5).strip()
            else:
                matchRating3 = re.search(r'"Runtime": (\d{1,10}), "Rating": "(.*?)"', curQueueItem)
                if matchRating3:
                    curX.Mpaa = matchRating3.group(2).strip()
            
            if curX.Mpaa == "TV-Y":
                iRating = 10
            elif curX.Mpaa == "TV-Y7":
                iRating = 20
            elif curX.Mpaa == "G":
                iRating = 40
            elif curX.Mpaa == "TV-G": 
                iRating = 50
            elif curX.Mpaa == "PG":
                iRating = 60
            elif curX.Mpaa == "NR (Kids)":
                iRating = 75
            elif curX.Mpaa == "PG-13":
                iRating = 80
            elif curX.Mpaa == "TV-14":
                iRating = 90
            elif curX.Mpaa == "R":
                iRating = 100
            elif curX.Mpaa == "TV-MA":
                iRating = 110
            elif curX.Mpaa == "NR (Mature)":
                iRating = 130
            elif curX.Mpaa == "UR (Mature)":
                iRating = 1000
            else:
                iRating = 1000
    #check rating against max rating
    if (not int(iRating) <= int(MAX_RATING)):
        print "iRating is cur item is: " + str(iRating) + " which has the MPAA value of " + str(curX.Mpaa)
        print "Item failed rating check, not adding.."
        return curX

    #genre
    matchGenre = re.search(r"genres': \[?{.*?u'name': u'(.*?)'}", curQueueItem, re.DOTALL | re.MULTILINE)
    if matchGenre:
        curX.Genres = matchGenre.group(1).strip()

    #year
    matchYear = re.search(r'[\'"]release_year[\'"]: u{0,1}[\'"](\d{4})[\'"]', curQueueItem)
    if matchYear:
        curX.Year = matchYear.group(1).strip()
    else:
        matchYear2 = re.search(r'"ReleaseYear": (\d{4})', curQueueItem, re.IGNORECASE)
        if matchYear2:
            curX.Year = matchYear2.group(1).strip()
    if(not int(curX.Year) >= int(YEAR_LIMITER)):
        print "couldn't parse year"
        #return curX



    
    #title
    #bengalih - added line below to deal with abrupt termination of title's with a single quote
    curQueueItem = curQueueItem.replace("\\\'", "'")

    matchTitle = re.search(r'[\'"]title[\'"]: {.*?[\'"]regular[\'"]: u{0,1}(\'|")(.*?)\1.*?},', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchTitle:
        curX.Title = matchTitle.group(2).strip()
        #bengalih - added line below to revert single quote escape character to non-escaped quote
        curX.Title = curX.Title.replace("'", "\'")
    else:
        matchTitleSQuoted = re.search(r'[\'"]title[\'"]: {.*?[\'"]regular[\'"]: u{0,1}[\'](.*?)[\'].*?},', curQueueItem, re.DOTALL | re.MULTILINE)
        if matchTitleSQuoted:
            curX.Title = matchTitleSQuoted.group(1).strip()
        else:
            matchTitleQuoted = re.search(r'[\'"]title[\'"]: {.*?[\'"]regular[\'"]: u{0,1}[\'"](.*?)[\'"].*?},', curQueueItem, re.DOTALL | re.MULTILINE)
            if matchTitleQuoted:
                curX.Title = matchTitleQuoted.group(1).strip()
            else:
                matchTitle3 = re.search('"ShortName": "(.*?)"',curQueueItem, re.DOTALL | re.MULTILINE)
                if matchTitle3:
                    curX.Title = matchTitle3.group(1).strip()

    #position
    matchPosition = re.search(r'[\'"]position[\'"]: u{0,1}[\'"](\d{1,6})[\'"], ', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchPosition:
        curX.Position = matchPosition.group(1)

    #runtime
    matchRuntime = re.search(r'[\'"]runtime[\'"]: u{0,1}[\'"](\d{1,6})[\'"], ', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchRuntime:
        curX.Runtime = matchRuntime.group(1)
    else:
        matchRuntime2 = re.search(r"u'runtime': ([\d]*?)}", curQueueItem)
        if matchRuntime2:
            curX.Runtime = matchRuntime2.group(1)
        else:
            matchRuntime3 = re.search(r'"NetflixCatalog.Model.InstantAvailability".*?}, "Available": (?P<iAvail>true|false|null), "AvailableFrom": (?P<iAvailFrom>.*?), "AvailableTo": ".*?\((?P<availUntil>\d*)\).*?"Runtime": (\d*), "Rating": .*?\}', curQueueItem, re.DOTALL | re.MULTILINE)
            if matchRuntime3:
                curX.Runtime = matchRuntime3.group(4)
            else:
                matchRuntime4 = re.search(r"u'runtime': ([\d]{1,50})", curQueueItem)
                if matchRuntime4:
                    curX.Runtime = matchRuntime4.group(1)

    #Available Until (in seconds since EPOC)
    matchAvailUntil = re.search(r"available_until': (\d{8,15})", curQueueItem, re.DOTALL | re.MULTILINE)
    if matchAvailUntil:
        curX.AvailableUntil = matchAvailUntil.group(1)
    else:
        #"NetflixCatalog.Model.InstantAvailability".*?}, "Available": (?P<iAvail>true|false|null), "AvailableFrom": (?P<iAvailFrom>.*?), "AvailableTo": (?P<iAvailTil>.*?)
        matchAvailUntil = re.search(r'"NetflixCatalog.Model.InstantAvailability".*?}, "Available": (?P<iAvail>true|false|null), "AvailableFrom": (?P<iAvailFrom>.*?), "AvailableTo": ".*?\((?P<availUntil>\d*)\)', curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if matchAvailUntil:
            curX.AvailableUntil = matchAvailUntil.group(3)
            if(DEBUG):
                print "matched avail until date from oData source regex"
                print str(curX.AvailableUntil)

    matchWebURL = re.search(r"u'web_page': u'(.*?)'", curQueueItem)
    if matchWebURL:
        curX.WebURL = matchWebURL.group(1)
                
    #shorttitle
    matchTitleShort = re.search('[\'"]title[\'"]: {.*?[\'"](title_)?short[\'"]: u{0,1}[\'](.*?)[\'].*?},', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchTitleShort:
        curX.TitleShort = matchTitleShort.group(2).strip()
    else:
        matchTitleShortQuotes = re.search('[\'"]title[\'"]: {.*?[\'"](title_)?short[\'"]: u{0,1}[\'"](.*?)[\'"].*?},', curQueueItem, re.DOTALL | re.MULTILINE)
        if matchTitleShortQuotes:
            curX.TitleShort = matchTitleShortQuotes.group(2).strip()
        else:
            matchTitleShort3 = re.search('"ShortName": "(.*?)"',curQueueItem, re.DOTALL | re.MULTILINE)
            if matchTitleShort3:
                curX.TitleShort = matchTitleShort3.group(1).strip()

    firstM = True
    #director
    for matchDir in re.finditer(r"directors': \[(.*?)\]", curQueueItem):
        firstM = True
        for matchDir2 in re.finditer(r"u'name': u'(.*?)'(?:}],)?", str(matchDir.group(1))):
            if (firstM):
                curX.Directors = curX.Directors + str(matchDir2.groups(1))
                firstM = False
            else:
                curX.Directors = curX.Directors + str(matchDir2.groups(1)) + ", "
    curX.Directors = curX.Directors.replace("(", "")
    curX.Directors = curX.Directors.replace(")", "")
    curX.Directors = curX.Directors.replace("'", "")
    curX.Directors = curX.Directors.replace(",,", ",")
        
    #rating
    matchRating = re.search('[\'"]average_rating[\'"]: [\'"]?(.*?)\}?[\'"]?}?,', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchRating:
        curX.Rating = matchRating.group(1)
        curX.Rating = curX.Rating.replace("}", "")
        curX.Rating = curX.Rating.replace("]", "")
        curX.Rating = curX.Rating.strip()
    else:
        matchRating2 = re.search(r'"Synopsis": "(.*?)", "AverageRating": (.{1,5}), "ReleaseYear": (\d{4}),', curQueueItem)
        if matchRating2:
            curX.Rating = matchRating2.group(2)
            curX.Rating = curX.Rating.replace("}", "")
            curX.Rating = curX.Rating.replace("]", "")
            curX.Rating = curX.Rating.strip()
    #print "attempting to get id next"   
    #id and fullid
    matchIds = re.search(r"u'web_page': u'http://.*?/(\d{1,15})'", curQueueItem, re.DOTALL | re.MULTILINE)
    if matchIds:
        curX.ID = matchIds.group(1).strip()
        #print "id regex: matched matchIds"
    else:
        #print "didnt' match matchIds"
        match = re.search(r"u'\d{1,3}pix_w': u'http://.*?.nflximg.com/US/boxshots/(small|tiny|large|ghd|small_epx|ghd_epx|large_epx|88_epx|tiny_epx)/(\d{1,15}).jpg'", curQueueItem, re.DOTALL | re.MULTILINE)
        if match:
            #print "id regex: matched match"
            curX.ID = match.group(2).strip()
        else:
            #print "didn't match match"
            matchIds2 = re.search(r'id[\'"]: u{0,1}[\'"](?P<fullId>.*?/(?P<idNumber>\d{1,15}))[\'"].*?', curQueueItem, re.DOTALL | re.MULTILINE)
            if matchIds2:
                #print "id regex: matched matchIds2"
                curX.FullId = matchIds2.group(1)
                curX.ID = matchIds2.group(2)
            else:
                #print "didn't match matchIds2"
                matchIds3 = re.search(r'"media_src": "http://.*?.nflximg.com/[^/]*?/boxshots/(small|tiny|large|ghd|small_epx|ghd_epx|large_epx|88_epx|tiny_epx)/(\d{1,15}).jpg"', curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                if matchIds3:
                    #print "id regex: matched matchIds3"
                    curX.FullId = matchIds3.group(1)
                    curX.ID = matchIds3.group(2)
                else:
                    matchIds4 = re.search(r'"type": "NetflixCatalog.Model.BoxArt".*?}, ".*Url": "http://.*?.nflximg.com/us/boxshots/(small|tiny|large|ghd|small_epx|ghd_epx|large_epx|88_epx|tiny_epx)/(\d{1,15}).jpg"', curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                    if matchIds4:
                        #print "id regex: matched matchIds3"
                        curX.FullId = matchIds4.group(1)
                        curX.ID = matchIds4.group(2)
                    else:
                        print "CRITICAL ERROR: Unable to parse ID of item. Stopping parse..."
                        return curX
    #print "got id of : " + curX.ID
    #show info
    curX.TvShowSeriesID = curX.ID
    matchShowData = re.search(r"http://api.netflix.*?/catalog/titles/series/(\d*)/seasons/(\d*)", curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    if (matchShowData):
        curX.TvShow = True
        curX.TvShowSeriesID = matchShowData.group(1).strip()
        curX.TvShowSeasonID = matchShowData.group(2).strip()

    #synop
    matchSynop = re.search(r"u'synopsis': {.*?u'regular': u[\'\"](.*?)}", curQueueItem, re.DOTALL | re.MULTILINE)
    if matchSynop:
        curX.Synop = matchSynop.group(1)
    else:
        matchSynop2 = re.search(r"u'synopsis': {.*?u'short_synopsis': u[\'\"](.*?)}", curQueueItem, re.DOTALL | re.MULTILINE)
        if matchSynop2:
            curX.Synop = matchSynop2.group(1)
        else:
            matchSynop3 = re.search(r'"Synopsis": "(.*?)", "AverageRating": (.{1,5}), "ReleaseYear": (\d{4}),', curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if matchSynop3:
                curX.Synop = matchSynop3.group(1)

    #cleanup synop
    try:
        strSynopsis = curX.Synop
        strSynopsisCleaned = strSynopsis
        #clean out all html tags
        for match in re.finditer(r"(?sm)(<[^>]+>)", strSynopsis):
            strSynopsisCleaned = strSynopsisCleaned.replace(match.group(1),"")
        for match in re.finditer(r"(&.*?;)", strSynopsis):
            strSynopsisCleaned = strSynopsisCleaned.replace(match.group(1),"")
        #clean out actor names that follows the name of character in movie
        for match2 in re.finditer(r"(?sm)(\([^\)]+\))", strSynopsisCleaned):
            strSynopsisCleaned = strSynopsisCleaned.replace(match2.group(1),"")
        #strip out the text ""synopsis": " and "{}|" and then clean up
        strSynopsisCleaned = strSynopsisCleaned.replace("\"synopsis\": ", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("{", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("}", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("|", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("  ", " ")
        strSynopsisCleaned = strSynopsisCleaned.replace("\"", "")
        strSynopsisCleaned = strSynopsisCleaned.replace("\\'", "'")
        strSynopsisCleaned = strSynopsisCleaned.strip()
        curX.Synop = strSynopsisCleaned
        #print "Cleaned Synopsis: %s" % strSynopsisCleaned
    except:
        print "No Synop Data available for " + curX.Title

    curX.Synop = "Available Until: " + availableTimeRemaining(curX.AvailableUntil) + "\n" + curX.Synop

    curX.TitleShortOriginal = curX.TitleShort
    #Appending MPAA Rating to Title
    if(SHOW_RATING_IN_TITLE):
        curX.TitleShort = curX.TitleShort + " [" + curX.Mpaa + "]"

    #poster
    posterLoc = ""
    if(posterLoc == ""):
        #bengalih - changed below six lines to account for TV Seasons (Watched) and TV Series (Recommended) or else missing downloads will ensue..
        if(curX.TvShow):
            posterLoc = "http://cdn-" + str(get_CurMirrorNum()) + ".nflximg.com/us/boxshots/" + POSTER_QUAL + "/" + curX.TvShowSeriesID + ".jpg"
            if(curX.TvShowSeasonID):
                posterLoc = "http://cdn-" + str(get_CurMirrorNum()) + ".nflximg.com/us/boxshots/" + POSTER_QUAL + "/" + curX.TvShowSeasonID + ".jpg"            
        else:
             posterLoc = "http://cdn-" + str(get_CurMirrorNum()) + ".nflximg.com/us/boxshots/" + POSTER_QUAL + "/" + curX.ID + ".jpg"
    curX.Poster = posterLoc
    
    #title
    curX.TitleShortLink = curX.ID
    curX.TitleShortLink.strip()

    #append year to shorttitle based on user pref
    if(APPEND_YEAR_TO_TITLE):
        curX.TitleShort = curX.TitleShort + " (" + curX.Year + ")"

    if (DEBUG):
        print "curMpaa: " + curX.Mpaa
        print "curPosition: " + curX.Position
        print "curYear: " + curX.Year
        print "curTitle: " + curX.Title
        print "curTitleShort: " + curX.TitleShort
        print "curRating: " + curX.Rating
        print "curRuntime: " + curX.Runtime
        print "curGenres: " + curX.Genres
        print "curID: " + curX.ID
        print "curPoster: " + curX.Poster
        print "curSynop: " + curX.Synop
        print "curDirector: " + curX.Directors
    if (VERBOSE_USER_LOG):
        print "curFullId: " + curX.FullId

    if (discQueue):
        addLinkDisc(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.TitleShortLink + '.html')), curX)
        #write the link file for Disc items that will link to the webpage
        writeDiscLinkFile(curX.TitleShortLink, curX.Title, curX.WebURL)
        return curX
        
    #see if we are filtering for Instant Only Items
    if (instantAvail):
        #see if the source is odata, if so, ensure iAvail is set to true (return on fail)
        if(curX.oData):
            if(not curX.iAvail):
                return curX
            else:
                curX.IsInstantAvailable = True
        else:
            #api data will return a string the following regex will parse
            matchIA = re.search(r"delivery_formats': {(.*?instant.*?)}", curQueueItem, re.DOTALL | re.MULTILINE)
            if matchIA:
                matched = re.search(r"instant", matchIA.group(1))
                if(not matched):
                    print "Item Filtered Out, it's not viewable instantly: " + curX.Title
                    return curX
                else:
                    curX.IsInstantAvailable = True
            else:
				curX.IsInstantAvailable = True
				#return curX

    if(not curX.TvShow):
        ciName = str(curX.TitleShortLink + '.html')
        ciPath = str(REAL_LINK_PATH)
        ciFullPath = os.path.join(ciPath, ciName )
        addLink(curX.TitleShort,ciFullPath, curX)
        #write the link file
        writeLinkFile(curX.TitleShortLink, curX.Title)
        return curX

    #if we are here, it's a tvshow, see if we should expand them automatically (user setting)
    if(not forceExpand):
        if(not AUTO_EXPAND_EPISODES):
            #it's a tvshow and we are not autoexpanding the episodes, we want to add the item as a folder with it's list of episodes
            boolDiscQueue = False
            if(discQueue):
                boolDiscQueue = True
            addDirectoryItem(curX, parameters={ PARAMETER_KEY_MODE:"tvExpand" + "shId" + curX.TvShowSeriesID + "seId" + curX.TvShowSeasonID + str(boolDiscQueue) }, isFolder=True, thumbnail=curX.Poster)

            #add the link to UI
            #addLink(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.TitleShortLink + '.html')), curX)
            #write the link file
            #writeLinkFile(curX.TitleShortLink, curX.Title)
            return curX
        
    matchAllEpData = re.search(r'(?sm){(u{0,1}[\'"]episode_short[\'"].*?)}', curQueueItem, re.DOTALL | re.MULTILINE)
    if matchAllEpData:
        data = matchAllEpData.group(1)
    else:
        data = ""

    foundMatch = False
    #if still processing, we want to auto-expand the episode lets add the folder, and then parse the episodes into that folder
    for matchAllEp in re.finditer('(?sm)(u{0,1}[\'"]episode_short[\'"].*?)}', curQueueItem):
        foundMatch = True
        curXe = XInfo()
        curXe.Mpaa = curX.Mpaa
        curXe.Position = curX.Position
        curXe.Year = curX.Year
        curXe.Rating = curX.Rating
        curXe.Runtime = "0"
        curXe.Genres = curX.Genres
        curXe.Directors = curX.Directors
        curXe.FullId = ""
        curXe.Poster = curX.Poster
        curXe.Cast = curX.Cast

        matchTitle = re.search('(?sm)u{0,1}[\'"]title[\'"]: u{0,1}[\'"](?P<title>.*?)[\'"],', matchAllEp.group())
        if matchTitle:
            curXe.Title = str(matchTitle.group("title"))
	
        curXe.Synop = curXe.Title + "\n\n" + curX.Synop
        
        matchEpNum = re.search('(?sm)u{0,1}[\'"]sequence[\'"]: u{0,1}(?P<episodeNum>\\d{1,3})', matchAllEp.group())
        if matchEpNum:
            curXe.TvEpisodeEpisodeNum = str(matchEpNum.group("episodeNum"))

        matchSeasonNum = re.search('(?sm)u{0,1}[\'"]season_number[\'"]: u{0,1}(?P<seasonNum>\\d{1,3})', matchAllEp.group())
        if matchSeasonNum:
            curXe.TvEpisodeEpisodeSeasonNum = str(matchSeasonNum.group("seasonNum"))

        matchShortTitle = re.search('(?sm)u{0,1}[\'"]episode_short_raw[\'"]: u{0,1}[\'"](?P<shorttitle>.*?)[\'"]', matchAllEp.group())
        if matchShortTitle:
            shortTitleString = str(matchShortTitle.group("shorttitle"))
            
        if re.search(r"Episode", curQueueItem, re.DOTALL | re.MULTILINE):
            if(not forceExpand):
                curXe.TitleShort = curX.TitleShort + " " + shortTitleString
            else:
                curXe.TitleShort = shortTitleString
        else:
            if(not forceExpand):
                curXe.TitleShort = curX.TitleShortOriginal + " " + "Episode: " + str(curXe.TvEpisodeEpisodeNum) + " " + shortTitleString
            else:
                curXe.TitleShort = "s" + str(curXe.TvEpisodeEpisodeSeasonNum) + "e" + str(curXe.TvEpisodeEpisodeNum) + " - " + shortTitleString

        curXe.TvShow = True
        curXe.TvShowLink = curX.TvShowLink
        curXe.TvShowSeasonID = curX.TvShowSeasonID
        curXe.TvShowSeriesID = curX.TvShowSeriesID
        curXe.TvEpisode = True
        
        matchNetflixID = re.search('(?sm)u{0,1}[\'"]id[\'"]: u{0,1}[\'"](?P<mgid>.*?)[\'"],', matchAllEp.group())
        if matchNetflixID:
            curXe.TvEpisodeNetflixID = str(matchNetflixID.group("mgid"))
            
        curXe.TvEpisodeEpisodeSeasonNum = 0
        curXe.IsInstantAvailable = curX.IsInstantAvailable
        curXe.MaturityLevel = curX.MaturityLevel
        curXe.AvailableUntil = curX.AvailableUntil
        #curXe.TvEpisodeEpisodeNum = matchAllEpisodes.group("eNum")
        #curXe.TvEpisodeEpisodeSeasonNum = matchAllEpisodes.group("title")

        matchAllEpisodesRealID = re.search(r"http://api-public.netflix.com/catalog/titles/programs/\d{1,15}/(?P<id>\d{1,15})", curXe.TvEpisodeNetflixID, re.DOTALL | re.MULTILINE)
        if matchAllEpisodesRealID:
            curXe.ID = matchAllEpisodesRealID.group("id").strip()
            curXe.TitleShortLink = curXe.ID
            curXe.TitleShortLink.strip()
            #add and write file
            ciName2 = str(curXe.TitleShortLink + '.html')
            ciPath2 = str(REAL_LINK_PATH)
            ciFullPath2 = os.path.join(ciPath2, ciName2 )
            addLink(curXe.TitleShort, ciFullPath2, curXe, curX.ID)
            writeLinkFile(curXe.TitleShortLink, curXe.Title)
        else:
            #don't add it
            print "not adding episode, couldn't parse id"
    
    if (not foundMatch):
        #this is to cover those tv shows that are just a single episode
        ciName = str(curX.TitleShortLink + '.html')
        ciPath = str(REAL_LINK_PATH)
        ciFullPath = os.path.join(ciPath, ciName )
        addLink(curX.TitleShort,ciFullPath, curX)
        #write the link file
        writeLinkFile(curX.TitleShortLink, curX.Title)

    return curX

def addDir(name,url,mode,iconimage,data):
    whichHandler = sys.argv[1]

    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    #u= "mode=" + urllib.quote_plus(data)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    ok=xbmcplugin.addDirectoryItem(handle=int(whichHandler),url=u,listitem=liz,isFolder=True)
    return ok

def getUserDiscQueue(netflix,user,displayWhat):
    print "*** What's in the Disc Queue? ***"
    feeds = netflix.user.getDiscQueue(None,None,500,None,IN_CANADA)
    if (VERBOSE_USER_LOG):
        print feeds
  
    counter = 0
    reobj = re.compile(r"(?sm)(?P<main>('item': )((?!('item': )).)*)", re.DOTALL | re.MULTILINE)
    #real processing begins here
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)

        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflix, False,displayWhat)

def getUserAtHomeItems(netflix,user):
    print "*** What's Disc from the Queue are shipped or at the home? ***"
    feeds = netflix.user.getAtHomeList(None,None,500)
    if (VERBOSE_USER_LOG):
        print feeds
  
    counter = 0
    reobj = re.compile(r"(?sm)(?P<main>('item': )((?!('item': )).)*)", re.DOTALL | re.MULTILINE)
    #real processing begins here
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)

        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflix, False, False)


def getUserInstantQueue(netflix,user, displayWhat):
    print "*** What's in the Instant Queue? ***"
    #get user setting for max number to download
    feeds = netflix.user.getInstantQueue(None,None,MAX_INSTANTQUEUE_RETREVE,None,IN_CANADA)
    print "Max value: " + str(MAX_INSTANTQUEUE_RETREVE)
    print "In CA: " + str(IN_CANADA)
    if (VERBOSE_USER_LOG):
        print feeds
    
    counter = 0
    reobj = re.compile(r"(?sm)(?P<main>('item': )((?!('item': )).)*)", re.DOTALL | re.MULTILINE)
    #real processing begins here
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)

        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflix, False,displayWhat)
  

	# match start: matchAllEpisodes.start()
	# match end (exclusive): matchAllEpisodes.end()
	# matched text: matchAllEpisodes.group()
        
##        matchIsTvShow = re.search(r'href": "(http://.*?/series/(\d{1,15})/seasons/(\d{1,15})/episodes)".*?title": "episodes"', curQueueItem, re.DOTALL | re.IGNORECASE | re.MULTILINE)
##        if(matchIsTvShow):
##            curX.TvShow = True
##            curX.TvShowSeriesID = matchIsTvShow.group(2).strip()
##            print curX.TvShowSeriesID
##            curX.TvShowSeasonID = matchIsTvShow.group(3).strip()
##            print curX.TvShowSeasonID
##            curX.TvShowLink = 'http://api.netflix.com/catalog/titles/series/'+ str(curX.TvShowSeriesID) + '/seasons/' + str(curX.TvShowSeasonID)
##            print curX.TvShowLink
##            if(AUTO_EXPAND_EPISODES):
##                epfeeds = netflix.user.getInstantQueueTvShowEpisodes(curX.TvShowSeriesID, curX.TvShowSeasonID)
##                epjFeeds = simplejson.dumps(epfeeds,indent=4)
##                if(VERBOSE_USER_LOG):
##                    print epjFeeds
##                for match in reobj.finditer(epjFeeds):
##                    curQueueItemTvE = match.group(1)
##                    curX.IsEpisode = True
##                    curX = getMovieDataFromFeed(curX, curQueueItemTvE, True, netflix, False)

def getUserRecommendedQueue(netflix,user):
    initApp()
    feeds = netflixClient.user.getRecommendedQueue(0,100,None,IN_CANADA)
    if(DEBUG):
        print simplejson.dumps(feeds,indent=4)
    counter = 0
    #parse each item in queue by looking for the category: [ string 
    reobj = re.compile(r"(?sm)(?P<main>('directors': )((?!('directors': )).)*)", re.DOTALL | re.MULTILINE)
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)
        if(DEBUG):
            print "current queue item from regex is: " + str(curQueueItem)
        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflixClient, True, False)
    time.sleep(1)
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getUrlString(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    data=response.read()
    response.close()
    return data 

def cleanString(strToClean):
    result = str(strToClean)
    result = re.sub(r"&quot;", r'"', result)
    result = re.sub(r"&amp;", r'&', result)
    return result

def parseRSSFeedItem(curQueueItem, curX):
    try:
        reobj = re.compile(r"<title>(.*?)</title>.*?<link>(.*?)</link>.*?<description>.*;{1}(.*?)</description>", re.DOTALL | re.MULTILINE)
        match = reobj.search(curQueueItem)
        if match:
            curX.Title = cleanString(match.group(1))
            curX.TitleShort = cleanString(match.group(1))
            curX.Synop = cleanString(match.group(3))
            curX.WebURL = match.group(2)
            reobj = re.compile(r".*?/(\d{1,15})", re.DOTALL | re.MULTILINE)
            matchID = reobj.search(match.group(2))
            if matchID:
                curX.ID = matchID.group(1)
            curX.Poster = "http://cdn-8.nflximg.com/us/boxshots/" + str(POSTER_QUAL) + "/" + curX.ID + ".jpg"
    except:
        print "error parsing data from RSS feed Item"
    return curX


def parseFeedburnerItem(curQueueItem, curX):
    try:
        reobjCurItem = re.compile(r'<strong>(?P<title>.*?)</strong><br/><a href="http://www\.netflix\.ca/[^"]*"><img src="(?P<posterPrefix>http://cdn-0\.nflximg\.com/en_CA/boxshots/)small/\d{2,14}\.jpg" /></a><br />(?P<summary>.*?)<a href="http://www\.netflix\.ca/[^"]*">More details</a> / <a href="http://www\.netflix\.ca/WiPlayer\?movieid=(?P<id>\d{2,14})">Watch now</a>', re.DOTALL | re.MULTILINE)
        matchCurItem = reobjCurItem.search(curQueueItem)
        if matchCurItem:
            curX.Title = matchCurItem.group(1)
            curX.TitleShort = matchCurItem.group(1)
            curX.Synop = matchCurItem.group(3)
            curX.WebURL = matchCurItem.group(4)
            curX.ID = matchCurItem.group(5)
            curX.Poster = matchCurItem.group(2) + str(POSTER_QUAL) + "/" + curX.ID + ".jpg"
    except:
        print "error parsing data from Feedburner RSS feed Item"        
    return curX

def convertFeedburnerFeed(tData, intLimit, DiscQueue=None):
    #parse feed to curX object
    curX = XInfo()
    intCount = 0
    for match in re.finditer(r"(?sm)<li.*?>(.*?)</li>", tData):
        for matchItem in re.finditer(r"(?sm)<p>(.*?)</p>", match.group(1)):
            intCount = intCount + 1
            if(intCount > int(intLimit)):
                return
            curQueueItem = match.group(1)
            parseFeedburnerItem(curQueueItem, curX)
            
            if(curX.ID == ""):
                print "fatal error: unable to parse ID in string " + curQueueItem
            else:
                #add the link to the UI
                if(DiscQueue):
                    addLinkDisc(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.ID + '_disc.html')), curX)
                    writeDiscLinkFile(curX.ID, curX.Title, curX.WebURL)
                else:
                    addLink(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.ID + '.html')), curX)            
                    #write the link file
                    writeLinkFile(curX.ID, curX.Title) 

def convertRSSFeed(tData, intLimit, DiscQueue=None, strArg=None):
    #strArg (0 = all, 1 = movies, 2 = tv)
    incMovie = False
    incTV = False
    
    if(strArg):
        if(str(strArg) == "0"):
            incMovie = True
            incTV = True
            if(DEBUG):
                print "No filter"
        elif(str(strArg) == "1"):
            incMovie = True
            incTV = False
            if(DEBUG):
                print "Filtering for Movies"
        elif(str(strArg) == "2"):
            incMovie = False
            incTV = True
            if(DEBUG):
                print "Filtering for TV"
    else:
        incMovie = True
        incTV = True
            
    #parse feed to curX object
    curX = XInfo()
    intCount = 0
    for match in re.finditer(r"(?sm)<item>(.*?)</item>", tData):
        curQueueItem = match.group(1)
        parseRSSFeedItem(curQueueItem, curX)

        if(curX.ID == ""):
            print "fatal error: unable to parse ID in string " + curQueueItem
            exit

        isMovie = False
        isTV = False
        skip = True
        if re.search(r"(Season|Vol\.|: Chapter)", curX.Title, re.DOTALL | re.MULTILINE):
            isTV = True
        else:
            isMovie = True
            
        if (isMovie & incMovie):
            intCount = intCount + 1
            if (DEBUG):
                print "triggered count on movies limiter:" + str(intCount) + " of " + str(intLimit)
            skip = False
        elif (isTV & incTV):
            intCount = intCount + 1
            if (DEBUG):
                print "triggered count on tv limiter:" + str(intCount) + " of " + str(intLimit)
            skip = False
        #print str(intCount)
        if(intCount > int(intLimit)):
            return

        if(not skip):
        #add the link to the UI
            if(DiscQueue):
                addLinkDisc(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.ID + '_disc.html')), curX)
                writeDiscLinkFile(curX.ID, curX.Title, curX.WebURL)
            else:
                addLink(curX.TitleShort,os.path.join(str(REAL_LINK_PATH), str(curX.ID + '.html')), curX)            
                #write the link file
                writeLinkFile(curX.ID, curX.Title)


def getUserRentalHistory(netflix, user, strHistoryType, displayWhat=None):
    print "*** What's the rental history? ***"
    feeds = ""
    if(not strHistoryType):
        feeds = netflix.user.getRentalHistory(None,None,200)
    else:
        feeds = netflix.user.getRentalHistory(strHistoryType,None,200)
        
    if (VERBOSE_USER_LOG):
        print feeds
  
    counter = 0
    reobj = re.compile(r"(?sm)(?P<main>('item': )((?!('item': )).)*)", re.DOTALL | re.MULTILINE)
    #real processing begins here
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)
        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflix, False, displayWhat)

CUR_IMAGE_MIRROR_NUM = 0

def get_CurMirrorNum():
    global CUR_IMAGE_MIRROR_NUM
    if(CUR_IMAGE_MIRROR_NUM == 8):
        CUR_IMAGE_MIRROR_NUM
        CUR_IMAGE_MIRROR_NUM = 1
    else:
        CUR_IMAGE_MIRROR_NUM = int(CUR_IMAGE_MIRROR_NUM) + 1
    return CUR_IMAGE_MIRROR_NUM

def initApp():
    global APP_NAME
    global API_KEY
    global API_SECRET
    global CALLBACK
    global user
    global counter
    global DEBUG
    global VERBOSE_USER_LOG
    global AUTO_EXPAND_EPISODES
    global OSX
    global useAltPlayer
    global arg
    global netflixClient
    global pg
    global IN_CANADA
    global APPEND_YEAR_TO_TITLE
    global POSTER_QUAL
    global MAX_INSTANTQUEUE_RETREVE
    global MAX_RATING
    global SHOW_RATING_IN_TITLE
    global YEAR_LIMITER
    global CUR_IMAGE_MIRROR_NUM

    global ROOT_FOLDER
    global WORKING_FOLDER
    global LINKS_FOLDER
    global REAL_LINK_PATH
    global RESOURCE_FOLDER
    global LIB_FOLDER
    global USERINFO_FOLDER
    global XBMCPROFILE

    #genre settings
    global SGACTION
    global SGANIME
    global SGBLURAY
    global SGCHILDREN
    global SGCLASSICS
    global SGCOMEDY
    global SGDOCUMENTARY
    global SGDRAMA
    global SGFAITH
    global SGFOREIGN
    global SGGAY
    global SGHORROR
    global SGINDIE
    global SGMUSIC
    global SGROMANCE
    global SGSCIFI
    global SGSPECIALINTEREST
    global SGSPORTS
    global SGTV
    global SGTHRILLERS
    
    arg = int(sys.argv[1])
    APP_NAME = 'xbmcflix'
    API_KEY = 'gnexy7jajjtmspegrux7c3dj'
    API_SECRET = '179530/200BkrsGGSgwP6446x4x22astmd5118'
    CALLBACK = ''
    counter = '0'
    #get user settings
    DEBUG = getUserSettingDebug(arg)
    VERBOSE_USER_LOG = getUserSettingVerboseUserInfo(arg)
    OSX = getUserSettingOSX(arg)
    IN_CANADA = getUserSettingCaUser(arg)
    AUTO_EXPAND_EPISODES = getUserSettingExpandEpisodes(arg)
    useAltPlayer = getUserSettingAltPlayer(arg)
    POSTER_QUAL = getUserSettingPosterQuality(arg)
    APPEND_YEAR_TO_TITLE = getUserSettingAppendYear(arg)
    
    MAX_INSTANTQUEUE_RETREVE = getUserSettingMaxIQRetreve(arg)
    MAX_RATING = getUserSettingRatingLimit(arg)
    SHOW_RATING_IN_TITLE = getUserSettingShowRatingInTitle(arg)
    YEAR_LIMITER = getUserSettingYearLimit(arg)

    SGACTION = getUserSettingGenreDisplay(arg, "sgAction")
    SGANIME = getUserSettingGenreDisplay(arg, "sgAnime")
    SGBLURAY = getUserSettingGenreDisplay(arg, "sgBluray")
    SGCHILDREN = getUserSettingGenreDisplay(arg, "sgChildren")
    SGCLASSICS = getUserSettingGenreDisplay(arg, "sgClassics")
    SGCOMEDY = getUserSettingGenreDisplay(arg, "sgComedy")
    SGDOCUMENTARY = getUserSettingGenreDisplay(arg, "sgDocumentary")
    SGDRAMA = getUserSettingGenreDisplay(arg, "sgDrama")
    SGFAITH = getUserSettingGenreDisplay(arg, "sgFaith")
    SGFOREIGN = getUserSettingGenreDisplay(arg, "sgForeign")
    SGGAY = getUserSettingGenreDisplay(arg, "sgGay")
    SGHORROR = getUserSettingGenreDisplay(arg, "sgHorror")
    SGINDIE = getUserSettingGenreDisplay(arg, "sgIndie")
    SGMUSIC = getUserSettingGenreDisplay(arg, "sgMusic")
    SGROMANCE = getUserSettingGenreDisplay(arg, "sgRomance")
    SGSCIFI = getUserSettingGenreDisplay(arg, "sgSciFi")
    SGSPECIALINTEREST = getUserSettingGenreDisplay(arg, "sgSpecialInterest")
    SGSPORTS = getUserSettingGenreDisplay(arg, "sgSports")
    SGTV = getUserSettingGenreDisplay(arg, "sgTV")
    SGTHRILLERS = getUserSettingGenreDisplay(arg, "sgThrillers")
    
    #get addon info
    __settings__ = xbmcaddon.Addon(id='plugin.video.xbmcflicks')
    ROOT_FOLDER = __settings__.getAddonInfo('path')
    RESOURCE_FOLDER = os.path.join(str(ROOT_FOLDER), 'resources')
    LIB_FOLDER = os.path.join(str(RESOURCE_FOLDER), 'lib')
    WORKING_FOLDER = xbmc.translatePath(__settings__.getAddonInfo("profile"))
    LINKS_FOLDER = os.path.join(str(WORKING_FOLDER), 'links')
    REAL_LINK_PATH = os.path.join(str(WORKING_FOLDER), 'links')
    USERINFO_FOLDER = WORKING_FOLDER
    XBMCPROFILE = xbmc.translatePath('special://profile')
    if(DEBUG):
        print "root folder: " + ROOT_FOLDER
        print "working folder: " + WORKING_FOLDER
        print "links folder: " + LINKS_FOLDER
        print "real link path: " + REAL_LINK_PATH
        print "resource folder: " + RESOURCE_FOLDER
        print "lib folder: " + LIB_FOLDER
        print "userinfo folder: " + USERINFO_FOLDER

    #check playercorefactory and advancedsettings, create if missing
    checkplayercore()
    checkadvsettings()
    
    reobj = re.compile(r"200(.{10}).*?644(.*?)4x2(.).*?5118")
    match = reobj.search(API_SECRET)
    if match:
        result = match.group(1)
        API_SECRET = result

    #ensure we have a links folder in addon_data
    if not os.path.exists(LINKS_FOLDER):
        os.makedirs(LINKS_FOLDER)
    
    #get user info
    userInfoFileLoc = os.path.join(str(USERINFO_FOLDER), 'userinfo.txt')
    print "USER INFO FILE LOC: " + userInfoFileLoc
    havefile = os.path.isfile(userInfoFileLoc)
    if(not havefile):
        f = open(userInfoFileLoc,'w+')
        f.write("")
        f.close()

    userstring = open(str(userInfoFileLoc),'r').read()
        
    reobj = re.compile(r"requestKey=(.*)\nrequestSecret=(.*)\naccessKey=(.*)\naccessSecret=(.*)")
    match = reobj.search(userstring)
    if match:
        print "matched file contents, it is in the correct format"
        MY_USER['request']['key'] = match.group(1).strip()
        MY_USER['request']['secret'] = match.group(2).strip()
        MY_USER['access']['key'] = match.group(3).strip()
        MY_USER['access']['secret'] = match.group(4).strip()
        print "finished loading up user information from file"
    else:
        #no match, need to fire off the user auth from the start
        print "couldn't load user information from userinfo.txt file"
    #auth the user
    netflixClient = NetflixClient(APP_NAME, API_KEY, API_SECRET, CALLBACK, VERBOSE_USER_LOG)
    user = getAuth(netflixClient,VERBOSE_USER_LOG)
    if(not user):
        exit

def getInstantQueue(displayWhat=None):
    initApp()
    getUserInstantQueue(netflixClient,user, displayWhat)
    if(not user):
        exit
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getRecommendedQueue():
    initApp()
    if(not user):
        exit
    getUserRecommendedQueue(netflixClient, user)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getNewToWatchInstantCA(strArg):
    initApp()
    if(not user):
        exit
    curUrl = "http://www.netflix.ca/NewWatchInstantlyRSS"
    convertRSSFeed(getUrlString(curUrl), 500, None, strArg)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getNewToWatchInstantCATopX(strArg):
    initApp()
    if(not user):
        exit
    curUrl = "http://www.netflix.ca/NewWatchInstantlyRSS"
    convertRSSFeed(getUrlString(curUrl), 25, None, strArg)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getNewToWatchInstant(strArg):
    initApp()
    if(not user):
        exit
    curUrl = "http://www.netflix.com/NewWatchInstantlyRSS"
    convertRSSFeed(getUrlString(curUrl), 500, None, strArg)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getNewToWatchInstantTopX(strArg):
    initApp()
    if(not user):
        exit    
    curUrl = "http://www.netflix.com/NewWatchInstantlyRSS"
    convertRSSFeed(getUrlString(curUrl), 25, None, strArg)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getTop25Feed(strArg):
    initApp()
    curUrl = "http://rss.netflix.com/Top25RSS?gid=" + str(strArg)
    convertRSSFeed(getUrlString(curUrl), 25)
    time.sleep(1)
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getTop25FeedD(strArg):
    initApp()
    curUrl = "http://rss.netflix.com/Top25RSS?gid=" + str(strArg)
    convertRSSFeed(getUrlString(curUrl), 25, True)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def normalize_params(params):
    # Escape key values before sorting.
    key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
        for k,v in params.items()]
    # Combine key value pairs into a string.
    return '?' + '&'.join(['$%s=%s' % (k, v) for k, v in key_values])

def checkGenre(strGenreName):
    result = False
    if SGGAY:
        if re.search(r"(lesb|gay|sex|erotic|experimental)", strGenreName, re.IGNORECASE):
            return "lesbian.png&genre=Gay & Lesbian"
    else:
        if re.search(r"(lesb|gay|sex|erotic|experimental)", strGenreName, re.IGNORECASE):
            return False

    if SGACTION:
        if re.search(r"(action|adventures|mobster|heist|swashbucklers|westerns|epics|blockbusters)", strGenreName, re.IGNORECASE):
            return "action.png&genre=Action & Adventure"
    if SGANIME:
        if re.search(r"(anime|animation)", strGenreName, re.IGNORECASE):
            return "anime.png&genre=Anime"
##    if SGBLURAY:
##        if re.search(r"blu", strGenreName, re.IGNORECASE):
##            return "bluray.png&genre=Blu-ray"
    if SGCHILDREN:
        if re.search(r"(book characters|animal tales|dinosaurs|nickelodeon|children|family|ages 0-2|ages 2-4|ages 5-7|ages 8-10|ages 11-12|cartoon|comic|kids|disney|inspirational|magic)", strGenreName, re.IGNORECASE):
            return "children.png&genre=Children & Family"
    if SGCOMEDY:
        if re.search(r"(mock|spoof|screwball|stand-up|saturday night live|slapstick|comedy|comedies|humor)", strGenreName, re.IGNORECASE):
            return "comedy.png&genre=Comedy"
    if SGDOCUMENTARY:
        if re.search(r"document", strGenreName, re.IGNORECASE):
            return "documentary.png&genre=Documentary"
    if SGDRAMA:
        if re.search(r"biographies|suspense|drama|mystery|underdogs|epics|blockbusters", strGenreName, re.IGNORECASE):
            return "drama.png&genre=Drama"
    if SGFAITH:
        if re.search(r"(religious|god|faith|pray|spirit)", strGenreName, re.IGNORECASE):
            return "faith.png&genre=Faith & Spirituality"
    if SGHORROR:
        if re.search(r"(monsters|satanic|horror|scream|dead|slash|kill)", strGenreName, re.IGNORECASE):
            return "horror.png&genre=Horror"
    if SGINDIE:
        if re.search(r"(indie|independent|IMAX|LOGO|film noir)", strGenreName, re.IGNORECASE):
            return "independent.png&genre=Independant"
    if SGMUSIC:
        if re.search(r"(blues|swing|reggae|singer|tunes|art|music|rock|rap|guitar|bass|jazz|r&b|folk|language|drum|guitar|banjo|karaoke|pop|concerts|piano|disco|country|new age|keyboard|opera)", strGenreName, re.IGNORECASE):
            return "music.png&genre=Music"
    if SGROMANCE:
        if re.search(r"(shakespeare|tearjerk|romance)", strGenreName, re.IGNORECASE):
            return "romance.png&genre=Romance"
    if SGSCIFI:
        if re.search(r"(sci-fi|scifi|science|fantasy)", strGenreName, re.IGNORECASE):
            return "scifi.png&genre=Sci-Fi"
    if SGSPECIALINTEREST:
        if re.search(r"(world|coming of age|theatrical|period pieces|sculpture|wine|social studies|sytle|beauty|voice lessons|technology|math|meditation|body|home|garden|pets|special|hobbies|math|food|heal|homespecial|blaxploitation|painting|poker|goth|computer|hobby|entertaining|preganancy|parent|career|bollywood|cooking)", strGenreName, re.IGNORECASE):
            return "special_interest.png&genre=Special Interest"
    if SGTV:
        if re.search(r"(car culture|tv|television)", strGenreName, re.IGNORECASE):
            return "television.png&genre=Television"
    if SGSPORTS:
        if re.search(r"(skateboarding|climbing|soccer|skiing|self-def|snowboard|wrestling|yoga|tai chi|climbing|golf|stunts|tennis|fishing|pilates|fitness|car|hockey|biking|olympics|bmx|bodybuilding|car|kung fu|strength|sports|racing|baseball|basketball|boxing|aerobics|cycling|dance|boxing|karate|martial arts|extreme combat|glutes|football|workout|motorcycle|hunting|boat)", strGenreName, re.IGNORECASE):
            return "sports.png&genre=Sports"
    if SGTHRILLERS:
        if re.search(r"(thrill|werewolves|vampires|frankenstein|zombies|creature)", strGenreName, re.IGNORECASE):
            return "thrillers.png&genre=Thrillers"
    if SGCLASSICS:
        if re.search(r"(classic|silent)", strGenreName, re.IGNORECASE):
            return "classics.png&genre=Classics"
    if SGFOREIGN:
        if re.search(r"(russia|china|foreign|scandinavia|asia|spain|thailand|united kingdom|brazil|australia|czech|africa|argentina|belgium|eastern|france|germany|greece|hong kong|india|iran|israel|italy|japan|judaica|korea|latin america|mexico|middle east|netherlands|philippines|poland)", strGenreName, re.IGNORECASE):
            return "foreign.png&genre=Foreign"
    if(DEBUG):
        print "Filtered out: " + strGenreName
    return False

def getInstantGenres():
    initApp()
    boolDiscQueue = False
    parameters = {}
    parameters['format'] = "json"
    parameters['callback'] = "render"
    requestUrl = "http://odata.netflix.com/Catalog/Genres"
    requestUri = requestUrl + normalize_params(parameters)
    print requestUri
    data = getUrlString(requestUri)
    #print data
    reobj = re.compile(r"(?sm)(?sm)(?P<main>(__metadata)((?!(__metadata)).)*)", re.DOTALL | re.MULTILINE)
    #real processing begins here
    for matchGenre in reobj.finditer(str(data)):
        curQueueItem = matchGenre.group(1)
        #now parse out each item
        reobj = re.compile('"uri": "http://odata.netflix.com/Catalog/Genres\\(\'(?P<linkname>[^\']*?)\'\\)", "type": "Netflix.Catalog.v2.Genre".*?}, "Name": "(?P<displayname>.*?)", "Titles": {', re.DOTALL | re.MULTILINE)
        for matchGenreItem in reobj.finditer(curQueueItem):
            curX = XInfo()
            curX.Title = matchGenreItem.group(2)
            curX.LinkName = matchGenreItem.group(1)
            curGenreCheckData = checkGenre(curX.Title)
            match = re.search(r"(.*\.png)&genre=(.*)", str(curGenreCheckData))
            if match:
                curX.Poster = os.path.join(str(RESOURCE_FOLDER), str(match.group(1)))
                curX.Genres = match.group(2)
                curX.nomenu = True
                addDirectoryItem(curX, parameters={ PARAMETER_KEY_MODE:"gExpand" + "lId" + curX.LinkName + str(boolDiscQueue) }, isFolder=True, thumbnail=curX.Poster)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def oDataSearch(strSeachValue, sDiscMode):
    #http://odata.netflix.com/Catalog/Titles?$filter=substringof%28%27xxx%27,%20Name%29
    instantOnly = False
    strType = "0"
    initApp()
    parameters = {}
    searchString = "substringof('" + str(strSeachValue) + "', Name)"
    parameters['filter'] = searchString
    parameters['format'] = "json"
    parameters['callback'] = "render"
    if(sDiscMode == "False"):
        instantOnly = True
        #parameters['filter'] = searchString + " and Instant/Available eq true"
    requestUrl = "http://odata.netflix.com/Catalog/Titles"
    requestUri = requestUrl + normalize_params(parameters)
    print requestUri
    data = getUrlString(requestUri)
    #print data
    if(DEBUG):
        print data
        #simplejson.dumps(data,indent=4)
    counter = 0
    reobj = re.compile(r'(?sm)(?P<main>(__metadata": {.{1,100}"uri")((?!(__metadata": {.{1,100}"uri")).)*)', re.DOTALL | re.IGNORECASE | re.MULTILINE)
    for match in reobj.finditer(str(data)):
        curX = XInfo()
        curQueueItem = match.group(1)
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflixClient, instantOnly, strType)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
def getGenreListing(nGenreLID, sDiscMode):
    instantOnly = False
    strType = "0"
    initApp()
    parameters = {}
    parameters['format'] = "json"
    parameters['callback'] = "render"
    if(sDiscMode == "False"):
        parameters['filter'] = "Instant/Available eq true"
    requestUrl = "http://odata.netflix.com/Catalog/Genres('" + nGenreLID + "')/Titles"
    requestUri = requestUrl + normalize_params(parameters)
    data = getUrlString(requestUri)
    #print data
    if(DEBUG):
        print data
        #simplejson.dumps(data,indent=4)
    counter = 0
    reobj = re.compile(r'(?sm)(?P<main>(__metadata": {.{1,100}"uri")((?!(__metadata": {.{1,100}"uri")).)*)', re.DOTALL | re.IGNORECASE | re.MULTILINE)
    for match in reobj.finditer(str(data)):
        curX = XInfo()
        curQueueItem = match.group(1)
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflixClient, instantOnly, strType)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
##    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
##    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_STUDIO )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getEpisodeListing(nShowID, nSeasonID, sDiscMode):
    print "iQueue TV ShowID : " + nShowID
    print "iQueue TV SeasonID : : " + nSeasonID
    print "FormatMode?: " + sDiscMode
    instantOnly = True
    strType = "5"
    initApp()
    if(not user):
        exit    
    feeds = netflixClient.user.getSeries(nShowID,nSeasonID,sDiscMode,0,100)
    if(DEBUG):
        print simplejson.dumps(feeds,indent=4)
    counter = 0
    #parse each item in queue by looking for the category: [ string 
    reobj = re.compile(r"(?sm)(?P<main>('catalog_title': )((?!('catalog_title': )).)*)", re.DOTALL | re.MULTILINE)
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)
        if(DEBUG):
            print "current feed item from regex is: " + curQueueItem
        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflixClient, instantOnly, strType, True)
    time.sleep(1)
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def doSearch(strArg, strQueue, strInstantOnly=None):
    instantOnly = False
    strType = "3"
    if(strInstantOnly):
        instantOnly = True
        strType = "5"
    #title search
    print "looking for items that match " + str(strArg ) + " in " + str(strQueue)  + " instant only is set to: " + str(instantOnly)
    initApp()
    print "Instant set to: " + str(instantOnly)
    print "Queue set to: " + str(strQueue)
    print "Search String is: " + str(strQueue)
    if(not user):
        exit    
    feeds = netflixClient.user.searchTitles(strArg,strQueue,0,100)
    if(DEBUG):
        print simplejson.dumps(feeds,indent=4)
    counter = 0
    #parse each item in queue by looking for the category: [ string 
    reobj = re.compile(r"(?sm)(?P<main>('directors': )((?!('directors': )).)*)", re.DOTALL | re.MULTILINE)
    for match in reobj.finditer(str(feeds)):
        curX = XInfo()
        curQueueItem = match.group(1)
        if(DEBUG):
            print "current queue item from regex is: " + str(curQueueItem)
        #now parse out each item
        curX = getMovieDataFromFeed(curX, curQueueItem, False, netflixClient, instantOnly, strType)
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getDVDQueue(displayWhat):
    initApp()
    getUserDiscQueue(netflixClient,user, displayWhat)
    if(not user):
        exit
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def rhShipped():
    initApp()
    getUserRentalHistory(netflixClient,user, "shipped", "3")
    if(not user):
        exit
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def rhReturned():
    initApp()
    getUserRentalHistory(netflixClient,user, "returned", "3")
    if(not user):
        exit
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def rhWatched():
    initApp()
    getUserRentalHistory(netflixClient,user, "watched")
    if(not user):
        exit
    time.sleep(1)
    #bengalih - added default unsorted method on line below to replicate standard Netflix timeline display
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getHomeList():
    initApp()
    getUserAtHomeItems(netflixClient,user)
    if(not user):
        exit
    time.sleep(1)
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )
    xbmcplugin.setContent(int(sys.argv[1]),'Movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = menu
import sys
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import urllib
from iqueue import *

# plugin modes
MODE0iw = 0
MODE0d = 1
MODE1 = 10
MODE1a = 11
MODE1b = 12
MODE2 = 20
MODE3 = 30
MODE3a = 31
MODE3b = 32
MODE4 = 40
MODE4ex = 41
MODE5 = 50
MODE5a = 51
MODE5b = 52
MODE6 = 60
MODE6a = 61
MODE6b = 62
MODE6c = 63
MODE6d = 64
MODE6e = 65
MODE6f = 66
MODE6g = 67
MODE6h = 68
MODE6i = 69
MODE6j = 70
MODE6k = 71
MODE6l = 72
MODE7 = 80
MODE7a = 81
MODE7b = 82
MODE7c = 83
MODE7d = 84
MODE7e = 85
MODE7f = 86
MODE7g = 87
MODE7h = 88
MODE7i = 89
MODE7j = 90
MODE7k = 91
MODE7l = 92
MODE7m = 93
MODE7n = 94
MODE7o = 95
MODE7p = 96
MODE7q = 97
MODE7r = 98
MODE7s = 99
MODE7t = 100

MODED1 = 500
MODED1m = 510
MODED1t = 520

MODED2 = 600
MODED3 = 700

MODED7 = 800
MODED7a = 801
MODED7b = 802
MODED7c = 803
MODED7d = 804
MODED7e = 805
MODED7f = 806
MODED7g = 807
MODED7h = 808
MODED7i = 809
MODED7j = 810
MODED7k = 811
MODED7l = 812
MODED7m = 813
MODED7n = 814
MODED7o = 815
MODED7p = 816
MODED7q = 817
MODED7r = 818
MODED7s = 819
MODED7t = 820

MODER = 900
MODER1 = 901
MODER2 = 902
MODER3 = 903

MODEO1 = 10001

# parameter keys
PARAMETER_KEY_MODE = "mode"

# menu item names
SUBMENU0iw = "Instant Movies and Shows"
SUBMENU0d = "Disc by Mail"

SUBMENU1 = "Instant Queue: All"
SUBMENU1a = "Instant Queue: Movies"
SUBMENU1b = "Instant Queue: TV"
SUBMENU2 = "Recommended"
SUBMENU3 = "All New Arrivals"
SUBMENU3a = "All New Arrivals: Movies"
SUBMENU3b = "All New Arrivals: TV"
SUBMENU4 = "Search..."
SUBMENU4ex = "Experimental Search..."
SUBMENU5 = "Top 25 New Arrivals"
SUBMENU5a = "Top 25 New Arrivals: Movies"
SUBMENU5b = "Top 25 New Arrivals: TV"
SUBMENU6 = "By Genre"
SUBMENU6a = "Action & Adventure"
SUBMENU6b = "Children & Family"
SUBMENU6c = "Classics"
SUBMENU6d = "Comedy"
SUBMENU6e = "Documentary"
SUBMENU6f = "Drama"
SUBMENU6g = "Foreign"
SUBMENU6h = "Horror"
SUBMENU6i = "Romance"
SUBMENU6j = "Sci-Fi & Fantasy"
SUBMENU6k = "Television"
SUBMENU6l = "Thrillers"
##Top 25 by Genre
SUBMENU7 = "Top 10 By Genre"
SUBMENU7a = "Action & Adventure"
SUBMENU7b = "Anime & Animation"
SUBMENU7c = "Blu-ray"
SUBMENU7d = "Children & Family"
SUBMENU7e = "Classics"
SUBMENU7f = "Comedy"
SUBMENU7g = "Documentary"
SUBMENU7h = "Drama"
SUBMENU7i = "Faith & Spirituality"
SUBMENU7j = "Foreign"
SUBMENU7k = "Gay & Lesbian"
SUBMENU7l = "Horror"
SUBMENU7m = "Independent"
SUBMENU7n = "Music & Musicals"
SUBMENU7o = "Romance"
SUBMENU7p = "Sci-Fi & Fantasy"
SUBMENU7q = "Special Interest"
SUBMENU7r = "Sports & Fitness"
SUBMENU7s = "Television"
SUBMENU7t = "Thrillers"

##DVD Queue
SUBMENUD1 = "Disc Queue: All"
SUBMENUD1m = "Disc Queue: Movies"
SUBMENUD1t = "Disc Queue: TV"

SUBMENUD2 = "Search..."
SUBMENUD3 = "At Home"

##Top 25 by Genre
SUBMENUD7 = "Top 25's By Genre"
SUBMENUD7a = "Action & Adventure"
SUBMENUD7b = "Anime & Animation"
SUBMENUD7c = "Blu-ray"
SUBMENUD7d = "Children & Family"
SUBMENUD7e = "Classics"
SUBMENUD7f = "Comedy"
SUBMENUD7g = "Documentary"
SUBMENUD7h = "Drama"
SUBMENUD7i = "Faith & Spirituality"
SUBMENUD7j = "Foreign"
SUBMENUD7k = "Gay & Lesbian"
SUBMENUD7l = "Horror"
SUBMENUD7m = "Independent"
SUBMENUD7n = "Music & Musicals"
SUBMENUD7o = "Romance"
SUBMENUD7p = "Sci-Fi & Fantasy"
SUBMENUD7q = "Special Interest"
SUBMENUD7r = "Sports & Fitness"
SUBMENUD7s = "Television"
SUBMENUD7t = "Thrillers"

## Rental History
SUBMENUR = "Rental History"
SUBMENUR1 = "Shipped"
SUBMENUR2 = "Returned"
SUBMENUR3 = "Watched"


## Genre Browse
SUBMENUO1 = "Browse by Genre"
# plugin handle
handle = int(sys.argv[1])

# settings
global IN_CANADA
IN_CANADA = getUserSettingCaUser(handle)
global SGACTION
global SGANIME
global SGBLURAY
global SGCHILDREN
global SGCLASSICS
global SGCOMEDY
global SGDOCUMENTARY
global SGDRAMA
global SGFAITH
global SGFOREIGN
global SGGAY
global SGHORROR
global SGINDIE
global SGMUSIC
global SGROMANCE
global SGSCIFI
global SGSPECIALINTEREST
global SGSPORTS
global SGTV
global SGTHRILLERS

SGACTION = getUserSettingGenreDisplay(handle, "sgAction")
SGANIME = getUserSettingGenreDisplay(handle, "sgAnime")
SGBLURAY = getUserSettingGenreDisplay(handle, "sgBluray")
SGCHILDREN = getUserSettingGenreDisplay(handle, "sgChildren")
SGCLASSICS = getUserSettingGenreDisplay(handle, "sgClassics")
SGCOMEDY = getUserSettingGenreDisplay(handle, "sgComedy")
SGDOCUMENTARY = getUserSettingGenreDisplay(handle, "sgDocumentary")
SGDRAMA = getUserSettingGenreDisplay(handle, "sgDrama")
SGFAITH = getUserSettingGenreDisplay(handle, "sgFaith")
SGFOREIGN = getUserSettingGenreDisplay(handle, "sgForeign")
SGGAY = getUserSettingGenreDisplay(handle, "sgGay")
SGHORROR = getUserSettingGenreDisplay(handle, "sgHorror")
SGINDIE = getUserSettingGenreDisplay(handle, "sgIndie")
SGMUSIC = getUserSettingGenreDisplay(handle, "sgMusic")
SGROMANCE = getUserSettingGenreDisplay(handle, "sgRomance")
SGSCIFI = getUserSettingGenreDisplay(handle, "sgSciFi")
SGSPECIALINTEREST = getUserSettingGenreDisplay(handle, "sgSpecialInterest")
SGSPORTS = getUserSettingGenreDisplay(handle, "sgSports")
SGTV = getUserSettingGenreDisplay(handle, "sgTV")
SGTHRILLERS = getUserSettingGenreDisplay(handle, "sgThrillers")


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

def addDirectoryItem(name, isFolder=True, parameters={}, thumbnail=None):
   ''' Add a list item to the XBMC UI.'''
   if thumbnail:
      li = xbmcgui.ListItem(name, thumbnailImage=thumbnail)
   else:
      li = xbmcgui.ListItem(name)
   url = sys.argv[0] + '?' + urllib.urlencode(parameters)
   return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url, listitem=li, isFolder=isFolder)


# UI builder functions
def show_root_menu():
   addDirectoryItem(name=SUBMENU0iw, parameters={ PARAMETER_KEY_MODE:MODE0iw }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_watch_main.png'))
   if(not IN_CANADA):
      addDirectoryItem(name=SUBMENU0d, parameters={ PARAMETER_KEY_MODE:MODE0d }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_by_mail.png'))
   addDirectoryItem(name=SUBMENUR, parameters={ PARAMETER_KEY_MODE:MODER }, isFolder=True, thumbnail=os.path.join(resourcePath, 'rental_history.png'))

   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)   

def show_instant_menu():
   if(not IN_CANADA):
      addDirectoryItem(name=SUBMENU1, parameters={ PARAMETER_KEY_MODE:MODE1 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_queue_all.png'))
      addDirectoryItem(name=SUBMENU1a, parameters={ PARAMETER_KEY_MODE:MODE1a }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_queue_movies.png'))
      addDirectoryItem(name=SUBMENU1b, parameters={ PARAMETER_KEY_MODE:MODE1b }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_queue_tv.png'))

   addDirectoryItem(name=SUBMENU2, parameters={ PARAMETER_KEY_MODE:MODE2 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_watch_recommended.png'))

   addDirectoryItem(name=SUBMENU5, parameters={ PARAMETER_KEY_MODE:MODE5 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_top25.png'))
   #addDirectoryItem(name=SUBMENU5a, parameters={ PARAMETER_KEY_MODE:MODE5a }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_top25_movies.png'))
   #addDirectoryItem(name=SUBMENU5b, parameters={ PARAMETER_KEY_MODE:MODE5b }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_top25_tv.png'))

   addDirectoryItem(name=SUBMENU3, parameters={ PARAMETER_KEY_MODE:MODE3 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_all.png'))
   #addDirectoryItem(name=SUBMENU3a, parameters={ PARAMETER_KEY_MODE:MODE3a }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_all_movies.png'))
   #addDirectoryItem(name=SUBMENU3b, parameters={ PARAMETER_KEY_MODE:MODE3b }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_new_all_tv.png'))
   addDirectoryItem(name=SUBMENUO1, parameters={ PARAMETER_KEY_MODE:MODEO1 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'browse_by_genre.png'))      
   addDirectoryItem(name=SUBMENU4, parameters={ PARAMETER_KEY_MODE:MODE4 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_search.png'))
   addDirectoryItem(name=SUBMENU4ex, parameters={ PARAMETER_KEY_MODE:MODE4ex }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_search.png'))
   #addDirectoryItem(name=SUBMENU6, parameters={ PARAMETER_KEY_MODE:MODE6 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'instant_watch_top25s.png'))
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_disc_menu():
   if(not IN_CANADA):
      addDirectoryItem(name=SUBMENUD1, parameters={ PARAMETER_KEY_MODE:MODED1 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_queue_all.png'))
      addDirectoryItem(name=SUBMENUD1m, parameters={ PARAMETER_KEY_MODE:MODED1m }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_queue_movies.png'))
      addDirectoryItem(name=SUBMENUD1t, parameters={ PARAMETER_KEY_MODE:MODED1t }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_queue_tv.png'))
      addDirectoryItem(name=SUBMENUD7, parameters={ PARAMETER_KEY_MODE:MODED7 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_bygenre.png'))
      addDirectoryItem(name=SUBMENUD2, parameters={ PARAMETER_KEY_MODE:MODED2 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_search.png'))
      addDirectoryItem(name=SUBMENUD3, parameters={ PARAMETER_KEY_MODE:MODED3 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_queue_at_home.png'))
   
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_rentalhistory_menu():
   if(not IN_CANADA):
      addDirectoryItem(name=SUBMENUR1, parameters={ PARAMETER_KEY_MODE:MODER1 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'rental_history_shipped.png'))
      addDirectoryItem(name=SUBMENUR2, parameters={ PARAMETER_KEY_MODE:MODER2 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'rental_history_returned.png'))

   addDirectoryItem(name=SUBMENUR3, parameters={ PARAMETER_KEY_MODE:MODER3 }, isFolder=True, thumbnail=os.path.join(resourcePath, 'rental_history_watched.png'))
   
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_SUBMENU1():
   ''' Show first submenu. '''
   for i in range(0, 5):
       name = "%s Item %d" % (SUBMENU1, i)
       addDirectoryItem(name, isFolder=False)
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_SUBMENU2():
   ''' Show second submenu. '''
   for i in range(0, 10):
       name = "%s Item %d" % (SUBMENU2, i)
       addDirectoryItem(name, isFolder=False)
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_SUBMENU6():
   #add in the genre folders
   addDirectoryItem(name=SUBMENU6a, parameters={ PARAMETER_KEY_MODE:MODE6a }, isFolder=True)
   addDirectoryItem(name=SUBMENU6b, parameters={ PARAMETER_KEY_MODE:MODE6b }, isFolder=True)
   addDirectoryItem(name=SUBMENU6c, parameters={ PARAMETER_KEY_MODE:MODE6c }, isFolder=True)
   addDirectoryItem(name=SUBMENU6d, parameters={ PARAMETER_KEY_MODE:MODE6d }, isFolder=True)
   addDirectoryItem(name=SUBMENU6e, parameters={ PARAMETER_KEY_MODE:MODE6e }, isFolder=True)
   addDirectoryItem(name=SUBMENU6f, parameters={ PARAMETER_KEY_MODE:MODE6f }, isFolder=True)
   addDirectoryItem(name=SUBMENU6g, parameters={ PARAMETER_KEY_MODE:MODE6g }, isFolder=True)
   addDirectoryItem(name=SUBMENU6h, parameters={ PARAMETER_KEY_MODE:MODE6h }, isFolder=True)
   addDirectoryItem(name=SUBMENU6i, parameters={ PARAMETER_KEY_MODE:MODE6i }, isFolder=True)
   addDirectoryItem(name=SUBMENU6j, parameters={ PARAMETER_KEY_MODE:MODE6j }, isFolder=True)
   addDirectoryItem(name=SUBMENU6k, parameters={ PARAMETER_KEY_MODE:MODE6k }, isFolder=True)
   addDirectoryItem(name=SUBMENU6l, parameters={ PARAMETER_KEY_MODE:MODE6l }, isFolder=True)
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def show_SUBMENU7():
   #add in the genre folders for the Top 25 items
   addDirectoryItem(name=SUBMENU7a, parameters={ PARAMETER_KEY_MODE:MODE7a }, isFolder=True)
   addDirectoryItem(name=SUBMENU7b, parameters={ PARAMETER_KEY_MODE:MODE7b }, isFolder=True)
   addDirectoryItem(name=SUBMENU7c, parameters={ PARAMETER_KEY_MODE:MODE7c }, isFolder=True)
   addDirectoryItem(name=SUBMENU7d, parameters={ PARAMETER_KEY_MODE:MODE7d }, isFolder=True)
   addDirectoryItem(name=SUBMENU7e, parameters={ PARAMETER_KEY_MODE:MODE7e }, isFolder=True)
   addDirectoryItem(name=SUBMENU7f, parameters={ PARAMETER_KEY_MODE:MODE7f }, isFolder=True)
   addDirectoryItem(name=SUBMENU7g, parameters={ PARAMETER_KEY_MODE:MODE7g }, isFolder=True)
   addDirectoryItem(name=SUBMENU7h, parameters={ PARAMETER_KEY_MODE:MODE7h }, isFolder=True)
   addDirectoryItem(name=SUBMENU7i, parameters={ PARAMETER_KEY_MODE:MODE7i }, isFolder=True)
   addDirectoryItem(name=SUBMENU7j, parameters={ PARAMETER_KEY_MODE:MODE7j }, isFolder=True)
   addDirectoryItem(name=SUBMENU7k, parameters={ PARAMETER_KEY_MODE:MODE7k }, isFolder=True)
   addDirectoryItem(name=SUBMENU7l, parameters={ PARAMETER_KEY_MODE:MODE7l }, isFolder=True)
   addDirectoryItem(name=SUBMENU7m, parameters={ PARAMETER_KEY_MODE:MODE7m }, isFolder=True)
   addDirectoryItem(name=SUBMENU7n, parameters={ PARAMETER_KEY_MODE:MODE7n }, isFolder=True)
   addDirectoryItem(name=SUBMENU7o, parameters={ PARAMETER_KEY_MODE:MODE7o }, isFolder=True)
   addDirectoryItem(name=SUBMENU7p, parameters={ PARAMETER_KEY_MODE:MODE7p }, isFolder=True)
   addDirectoryItem(name=SUBMENU7q, parameters={ PARAMETER_KEY_MODE:MODE7q }, isFolder=True)
   addDirectoryItem(name=SUBMENU7r, parameters={ PARAMETER_KEY_MODE:MODE7r }, isFolder=True)
   addDirectoryItem(name=SUBMENU7s, parameters={ PARAMETER_KEY_MODE:MODE7s }, isFolder=True)
   addDirectoryItem(name=SUBMENU7t, parameters={ PARAMETER_KEY_MODE:MODE7t }, isFolder=True)
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)
   
def show_SUBMENUD7():
   #add in the disc genre folders for the Top 25 items
   if SGACTION:
      addDirectoryItem(name=SUBMENUD7a, parameters={ PARAMETER_KEY_MODE:MODED7a }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_action2.png'))
   if SGANIME:
      addDirectoryItem(name=SUBMENUD7b, parameters={ PARAMETER_KEY_MODE:MODED7b }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_anime2.png'))
   if SGBLURAY:
      addDirectoryItem(name=SUBMENUD7c, parameters={ PARAMETER_KEY_MODE:MODED7c }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_bluray2.png'))
   if SGCHILDREN:
      addDirectoryItem(name=SUBMENUD7d, parameters={ PARAMETER_KEY_MODE:MODED7d }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_children2.png'))
   if SGCLASSICS:
      addDirectoryItem(name=SUBMENUD7e, parameters={ PARAMETER_KEY_MODE:MODED7e }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_classics2.png'))
   if SGCOMEDY:
      addDirectoryItem(name=SUBMENUD7f, parameters={ PARAMETER_KEY_MODE:MODED7f }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_comedy2.png'))
   if SGDOCUMENTARY:
      addDirectoryItem(name=SUBMENUD7g, parameters={ PARAMETER_KEY_MODE:MODED7g }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_documentary2.png'))
   if SGDRAMA:
      addDirectoryItem(name=SUBMENUD7h, parameters={ PARAMETER_KEY_MODE:MODED7h }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_drama2.png'))
   if SGFAITH:
      addDirectoryItem(name=SUBMENUD7i, parameters={ PARAMETER_KEY_MODE:MODED7i }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_faith2.png'))
   if SGFOREIGN:
      addDirectoryItem(name=SUBMENUD7j, parameters={ PARAMETER_KEY_MODE:MODED7j }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_foreign2.png'))
   if SGGAY:
      addDirectoryItem(name=SUBMENUD7k, parameters={ PARAMETER_KEY_MODE:MODED7k }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_lesbian2.png'))
   if SGHORROR:
      addDirectoryItem(name=SUBMENUD7l, parameters={ PARAMETER_KEY_MODE:MODED7l }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_horror2.png'))
   if SGINDIE:
      addDirectoryItem(name=SUBMENUD7m, parameters={ PARAMETER_KEY_MODE:MODED7m }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_independent2.png'))
   if SGMUSIC:
      addDirectoryItem(name=SUBMENUD7n, parameters={ PARAMETER_KEY_MODE:MODED7n }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_music2.png'))
   if SGROMANCE:
      addDirectoryItem(name=SUBMENUD7o, parameters={ PARAMETER_KEY_MODE:MODED7o }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_romance2.png'))
   if SGSCIFI:
      addDirectoryItem(name=SUBMENUD7p, parameters={ PARAMETER_KEY_MODE:MODED7p }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_scifi2.png'))
   if SGSPECIALINTEREST:
      addDirectoryItem(name=SUBMENUD7q, parameters={ PARAMETER_KEY_MODE:MODED7q }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_special_interest2.png'))
   if SGSPORTS:
      addDirectoryItem(name=SUBMENUD7r, parameters={ PARAMETER_KEY_MODE:MODED7r }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_sports2.png'))
   if SGTV:
      addDirectoryItem(name=SUBMENUD7s, parameters={ PARAMETER_KEY_MODE:MODED7s }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_television2.png'))
   if SGTHRILLERS:
      addDirectoryItem(name=SUBMENUD7t, parameters={ PARAMETER_KEY_MODE:MODED7t }, isFolder=True, thumbnail=os.path.join(resourcePath, 'disc_top25_thrillers2.png'))
   xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

# parameter values
print "##########################################################"
print("Arg1: %s" % sys.argv[1])
print("Arg2: %s" % sys.argv[2])
global addonPath
global resourcePath
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmcflicks')
addonPath = __settings__.getAddonInfo('path')
resourcePath = os.path.join(addonPath, 'resources')

params = parameters_string_to_dict(sys.argv[2])
submode = ""
if re.search(r"tvExpand", sys.argv[2]):
   #do expand tv show into ui list
   tvShowID = ""
   tvSeasonID = ""
   tvMode = ""
   matchTvEpExp = re.search(r"tvExpandshId(\d*)seId(\d*)(True|False)", sys.argv[2])
   if matchTvEpExp:
      tvShowID = matchTvEpExp.group(1)
      tvSeasonID = matchTvEpExp.group(2)
      tvMode = matchTvEpExp.group(3)
   else:
      "expand called but could not figure out the id from the call, the menu link is invalid in iqueue.py"
      mode = "failed to parse mode"

   print "TV Episode Expand Called for show with Show ID: " + tvShowID + " Season ID: " + tvSeasonID + " DiscMode: " + tvMode
   mode = "tvexp"
elif re.search(r"gExpand", sys.argv[2]):
   #do expand genre items into ui list
   genreLink = ""
   genreMode = ""
   matchTvEpExp = re.search(r"gExpandlId(.*?)(True|False)", sys.argv[2])
   if matchTvEpExp:
      genreLink = matchTvEpExp.group(1)
      genreMode = matchTvEpExp.group(2)
   else:
      "expand called but could not figure out the genre from the call, the menu link is invalid in iqueue.py"
      mode = "failed to parse mode"

   print "Genre Expand Called for show with Show ID: " + genreLink + " DiscMode: " + genreMode
   mode = "genreexp"
else:
   mode = int(params.get(PARAMETER_KEY_MODE, "0"))

print("Mode: %s" % mode)
print "##########################################################"

# Depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
   # new start
   show_root_menu()
elif mode == "tvexp":
   #expand tv episodes
   print "expanding episode list"
   if(tvMode == False):
      getEpisodeListing(tvShowID,tvSeasonID,"instant")
   else:
      getEpisodeListing(tvShowID,tvSeasonID,"Disc")
elif mode == "genreexp":
   #expand tv episodes
   print "expanding genre list"
   getGenreListing(genreLink,genreMode)
elif mode == MODE0iw:
   show_instant_menu()
elif mode == MODE0d:
   show_disc_menu()   
elif mode == MODE1:
   getInstantQueue()
elif mode == MODE1a:
   getInstantQueue(1)
elif mode == MODE1b:
   getInstantQueue(2)
elif mode == MODE2:
   getRecommendedQueue()

elif mode == MODE3:
   if(not IN_CANADA):
      getNewToWatchInstant("0")
   else:
      getNewToWatchInstantCA("0")
elif mode == MODE3a:
   if(not IN_CANADA):
      getNewToWatchInstant("1")
   else:
      getNewToWatchInstantCA("1")
elif mode == MODE3b:
   if(not IN_CANADA):
      getNewToWatchInstant("2")
   else:
      getNewToWatchInstantCA("2")

elif mode == MODE4:
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if (keyboard.isConfirmed()):
      arg = keyboard.getText()
      #print "keyboard returned: " + keyboard.getText()
      doSearch(arg, "instant", True)
      #oDataSearch(arg, "True")
    else:
      print "user canceled"

elif mode == MODE4ex:
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if (keyboard.isConfirmed()):
      arg = keyboard.getText()
      #print "keyboard returned: " + keyboard.getText()
      #doSearch(arg, "instant", True)
      oDataSearch(arg, "False")
    else:
      print "user canceled"

elif mode == MODE5:
   if(not IN_CANADA):
      getNewToWatchInstantTopX("0")
   else:
      getNewToWatchInstantCATopX("0")
elif mode == MODE5a:
   if(not IN_CANADA):
      getNewToWatchInstantTopX("1")
   else:
      getNewToWatchInstantCATopX("1")
elif mode == MODE5b:
   if(not IN_CANADA):
      getNewToWatchInstantTopX("2")
   else:
      getNewToWatchInstantCATopX("2")
     
elif mode == MODE6:
   ok = show_SUBMENU6()
elif mode == MODE6a:
   ok = show_SUBMENU6()
elif mode == MODE6b:
   ok = show_SUBMENU6()
elif mode == MODE6c:
   ok = show_SUBMENU6()
elif mode == MODE6d:
   ok = show_SUBMENU6()
elif mode == MODE6e:
   ok = show_SUBMENU6()
elif mode == MODE6f:
   ok = show_SUBMENU6()
elif mode == MODE6g:
   ok = show_SUBMENU6()
elif mode == MODE6h:
   ok = show_SUBMENU6()
elif mode == MODE6i:
   ok = show_SUBMENU6()
elif mode == MODE6j:
   ok = show_SUBMENU6()
elif mode == MODE6k:
   ok = show_SUBMENU6()
elif mode == MODE6l:
   ok = show_SUBMENU6()
elif mode == MODE7:
   ok = show_SUBMENU7()
elif mode == MODE7a:
   getTop25Feed("296")
elif mode == MODE7b:
   getTop25Feed("623")
elif mode == MODE7c:
   getTop25Feed("2444")
elif mode == MODE7d:
   getTop25Feed("302")
elif mode == MODE7e:
   getTop25Feed("306")
elif mode == MODE7f:
   getTop25Feed("307")
elif mode == MODE7g:
   getTop25Feed("864")
elif mode == MODE7h:
   getTop25Feed("315")
elif mode == MODE7i:
   getTop25Feed("2108")
elif mode == MODE7j:
   getTop25Feed("2514")
elif mode == MODE7k:
   getTop25Feed("330")
elif mode == MODE7l:
   getTop25Feed("338")
elif mode == MODE7m:
   getTop25Feed("343")
elif mode == MODE7n:
   getTop25Feed("2310")
elif mode == MODE7o:
   getTop25Feed("371")
elif mode == MODE7p:
   getTop25Feed("373")
elif mode == MODE7q:
   getTop25Feed("2223")
elif mode == MODE7r:
   getTop25Feed("2190")
elif mode == MODE7s:
   getTop25Feed("2197")
elif mode == MODE7t:
   getTop25Feed("387")
elif mode == MODED1:
   getDVDQueue(3)
elif mode == MODED1m:
   getDVDQueue(4)
elif mode == MODED1t:
   getDVDQueue(5)
elif mode == MODED2:
   keyboard = xbmc.Keyboard()
   keyboard.doModal()
   if (keyboard.isConfirmed()):
      arg = keyboard.getText()
      #print "keyboard returned: " + keyboard.getText()
      doSearch(arg, "Disc")
   else:
      print "user canceled"
elif mode == MODED3:
   getHomeList()
elif mode == MODED7:
   ok = show_SUBMENUD7()
elif mode == MODED7a:
   getTop25FeedD("296")
elif mode == MODED7b:
   getTop25FeedD("623")
elif mode == MODED7c:
   getTop25FeedD("2444")
elif mode == MODED7d:
   getTop25FeedD("302")
elif mode == MODED7e:
   getTop25FeedD("306")
elif mode == MODED7f:
   getTop25FeedD("307")
elif mode == MODED7g:
   getTop25FeedD("864")
elif mode == MODED7h:
   getTop25FeedD("315")
elif mode == MODED7i:
   getTop25FeedD("2108")
elif mode == MODED7j:
   getTop25FeedD("2514")
elif mode == MODED7k:
   getTop25FeedD("330")
elif mode == MODED7l:
   getTop25FeedD("338")
elif mode == MODED7m:
   getTop25FeedD("343")
elif mode == MODED7n:
   getTop25FeedD("2310")
elif mode == MODED7o:
   getTop25FeedD("371")
elif mode == MODED7p:
   getTop25FeedD("373")
elif mode == MODED7q:
   getTop25FeedD("2223")
elif mode == MODED7r:
   getTop25FeedD("2190")
elif mode == MODED7s:
   getTop25FeedD("2197")
elif mode == MODED7t:
   getTop25FeedD("387")
elif mode == MODER:
   show_rentalhistory_menu()
elif mode == MODER1:
   rhShipped()
elif mode == MODER2:
   rhReturned()
elif mode == MODER3:
   rhWatched()

#genre browsing
elif mode == MODEO1:
   getInstantGenres()

########NEW FILE########
__FILENAME__ = modQueue
from Netflix import *
import getopt
import time 
import re
import xbmcplugin, xbmcaddon, xbmcgui, xbmc
import urllib
import webbrowser
from xinfo import *

MY_USER = {
        'request': {
             'key': '',
             'secret': ''
        },
        'access': {
            'key': '',
            'secret': ''
        }
}

def __init__(self):
    self.data = []

# AUTH 
def getAuth(netflix, verbose):
    print ".. getAuth called .."
    print "OSX Setting is set to: " + str(OSX)
    netflix.user = NetflixUser(MY_USER,netflix)
    print ".. user configured .."

    #handles all the initial auth with netflix
    if MY_USER['request']['key'] and not MY_USER['access']['key']:
        tok = netflix.user.getAccessToken( MY_USER['request'] )
        if(VERBOSE_USER_LOG):
            print "now put this key / secret in MY_USER.access so you don't have to re-authorize again:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
        MY_USER['access']['key'] = tok.key
        MY_USER['access']['secret'] = tok.secret
        saveUserInfo()
        dialog = xbmcgui.Dialog()
        dialog.ok("Settings completed", "You must restart the xbmcflicks plugin")
        print "Settings completed", "You must restart the xbmcflicks plugin"
        sys.exit(1)

    elif not MY_USER['access']['key']:
        (tok, url) = netflix.user.getRequestToken()
        if(VERBOSE_USER_LOG):
            print "Authorize user access here: %s" % url
            print "and then put this key / secret in MY_USER.request:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
            print "and run again."
        #open web page with urllib so customer can authorize the app

        if(OSX):
            startBrowser(url)
        else:
            webbrowser.open(url)
            
        #display click ok when finished adding xbmcflicks as authorized app for your netflix account
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("After you have linked xbmcflick in netflix.", "Click OK after you finished the link in your browser window.")
        MY_USER['request']['key'] = tok.key
        MY_USER['request']['secret'] = tok.secret
        #now run the second part, getting the access token
        tok = netflix.user.getAccessToken( MY_USER['request'] )
        if(VERBOSE_USER_LOG):
            print "now put this key / secret in MY_USER.access so you don't have to re-authorize again:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
        MY_USER['access']['key'] = tok.key
        MY_USER['access']['secret'] = tok.secret
        #now save out the settings
        saveUserInfo()
        #exit script, user must restart
        dialog.ok("Settings completed", "You must restart the xbmcflicks plugin")
        print "Settings completed", "You must restart the xbmcflicks plugin"
        exit
        sys.exit(1)

    return netflix.user

def saveUserInfo():
    #create the file
    f = open(os.path.join(str(USERINFO_FOLDER), 'userinfo.txt'),'w+')
    setting ='requestKey=' + MY_USER['request']['key'] + '\n' + 'requestSecret=' + MY_USER['request']['secret'] + '\n' +'accessKey=' + MY_USER['access']['key']+ '\n' + 'accessSecret=' + MY_USER['access']['secret']
    f.write(setting)
    f.close()

# END AUTH

def initApp():
    global APP_NAME
    global API_KEY
    global API_SECRET
    global CALLBACK
    global user
    global counter
    global ROOT_FOLDER
    global WORKING_FOLDER
    global LINKS_FOLDER
    global REAL_LINK_PATH
    global IMAGE_FOLDER
    global USERINFO_FOLDER
    global VERBOSE_USER_LOG
    global DEBUG
    global OSX
    
    APP_NAME = 'xbmcflix'
    API_KEY = 'gnexy7jajjtmspegrux7c3dj'
    API_SECRET = '179530/200BkrsGGSgwP6446x4x22astmd5118'
    CALLBACK = ''
    VERBOSE_USER_LOG = False
    DEBUG = False
    OSX = False

    #get addon info
    __settings__ = xbmcaddon.Addon(id='plugin.video.xbmcflicks')
    ROOT_FOLDER = __settings__.getAddonInfo('path')
    RESOURCE_FOLDER = os.path.join(str(ROOT_FOLDER), 'resources')
    LIB_FOLDER = os.path.join(str(RESOURCE_FOLDER), 'lib')
    WORKING_FOLDER = xbmc.translatePath(__settings__.getAddonInfo("profile"))
    LINKS_FOLDER = os.path.join(str(WORKING_FOLDER), 'links')
    REAL_LINK_PATH = os.path.join(str(WORKING_FOLDER), 'links')
    USERINFO_FOLDER = WORKING_FOLDER
    XBMCPROFILE = xbmc.translatePath('special://profile')
    
    reobj = re.compile(r"200(.{10}).*?644(.*?)4x2(.).*?5118")
    match = reobj.search(API_SECRET)
    if match:
        result = match.group(1)
        API_SECRET = result

    #ensure we have a links folder in addon_data
    if not os.path.exists(LINKS_FOLDER):
        os.makedirs(LINKS_FOLDER)
    
    #get user info
    userInfoFileLoc = os.path.join(str(USERINFO_FOLDER), 'userinfo.txt')
    print "USER INFO FILE LOC: " + userInfoFileLoc
    havefile = os.path.isfile(userInfoFileLoc)
    if(not havefile):
        f = open(userInfoFileLoc,'w+')
        f.write("")
        f.close()

    userstring = open(str(userInfoFileLoc),'r').read()
        
    reobj = re.compile(r"requestKey=(.*)\nrequestSecret=(.*)\naccessKey=(.*)\naccessSecret=(.*)")
    match = reobj.search(userstring)
    if match:
        print "matched file contents, it is in the correct format"
        MY_USER['request']['key'] = match.group(1).strip()
        MY_USER['request']['secret'] = match.group(2).strip()
        MY_USER['access']['key'] = match.group(3).strip()
        MY_USER['access']['secret'] = match.group(4).strip()
        print "finished loading up user information from file"
    else:
        #no match, need to fire off the user auth from the start
        print "couldn't load user information from userinfo.txt file"
    #auth the user
    netflixClient = NetflixClient(APP_NAME, API_KEY, API_SECRET, CALLBACK, VERBOSE_USER_LOG)
    user = getAuth(netflixClient,VERBOSE_USER_LOG)
    if(not user):
        exit

if __name__ == '__main__':
    initApp()
    if ( len( sys.argv ) > 1 ):
        print str(len(sys.argv))
        print str(sys.argv[0])
        print str(sys.argv[1])

    strArgs = str(sys.argv[1])
    movieid = ""
    action = ""
    actionParams = ""
    verboseAction = ""
    verboseDirection = ""
    details = ""
    position = ""
    discQueue = False
    
    match = re.search(r"(.*?)(delete|post|discdelete|discpost|disctoppost)", strArgs, re.IGNORECASE)
    if match:
        movieid = match.group(1)
        print movieid
        action = match.group(2)
        actionParams = match.group(2)
        print action
    else:
        "print unable to parse action item, exiting"
        exit

    if(action == "post"):
        verboseAction = "Add"
        verboseDirection = "to"
    elif(action == "delete"):
        verboseAction = "Remove"
        verboseDirection = "from"
    elif(action == "discpost"):
        action = "post"
        verboseAction = "Add"
        verboseDirection = "to"
        discQueue = True
    elif(action == "disctoppost"):
        action = "post"
        verboseAction = "Add"
        verboseDirection = "to"
        discQueue = True
        position = "1"
    elif(action == "discdelete"):
        action = "delete"
        verboseAction = "Remove"
        verboseDirection = "from"
        discQueue = True

    netflixClient = NetflixClient(APP_NAME, API_KEY, API_SECRET, CALLBACK, VERBOSE_USER_LOG)
    #auth the user
    user = getAuth(netflixClient,VERBOSE_USER_LOG)

    #if we have a user, do the action
    if user:
        if(not discQueue):         
            result = user.modifyQueue(str(movieid), str(action))
            matchr = re.search(r"'message': u'(.*?)'", str(result), re.IGNORECASE)
            if matchr:
                details = matchr.group(1)
            else:
                details = str(result)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Instant Queue: " + verboseAction + " " + movieid, details)
        if(discQueue):
            if(position == ""):
                result = user.modifyQueueDisc(str(movieid), str(action))
            else:
                result = user.modifyQueueDisc(str(movieid), str(action), position)
            matchr = re.search(r"'message': u'(.*?)'", str(result), re.IGNORECASE)
            if matchr:
                details = matchr.group(1)
            else:
                details = str(result)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Disc Queue: " + verboseAction + " " + movieid, details)
         
        #refresh UI on delete, disc delete, or move to top
        if(actionParams == "delete"):
            xbmc.executebuiltin("Container.Refresh")
        elif(actionParams == "discdelete"):
            xbmc.executebuiltin("Container.Refresh")
        elif(actionParams == "disctoppost"):
            xbmc.executebuiltin("Container.Refresh")
    else:
        print "Failed to get user information from main init of modQueue script"

########NEW FILE########
__FILENAME__ = Netflix
#
# Library for accessing the REST API from Netflix
# Represents each resource in an object-oriented way
#

import sys
import os.path
import re
import oauth as oauth
import httplib
import time
from xml.dom.minidom import parseString
import simplejson
from urlparse import urlparse

HOST              = 'api-public.netflix.com'
PORT              = '80'
REQUEST_TOKEN_URL = 'http://api-public.netflix.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'http://api-public.netflix.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api-user.netflix.com/oauth/login'

class NetflixUser:

    def __init__(self, user, client):
        self.requestTokenUrl = REQUEST_TOKEN_URL
        self.accessTokenUrl  = ACCESS_TOKEN_URL
        self.authorizationUrl = AUTHORIZATION_URL
        self.accessToken = oauth.OAuthToken(user['access']['key'], user['access']['secret'] )
        self.client = client
        self.data = None

    def getRequestToken(self):
        client = self.client
        oauthRequest = oauth.OAuthRequest.from_consumer_and_token(
                                    client.consumer,
                                    http_url=self.requestTokenUrl)
        oauthRequest.sign_request(
                                    client.signature_method_hmac_sha1,
                                    client.consumer,
                                    None)
        client.connection.request(
                                    oauthRequest.http_method,
                                    self.requestTokenUrl,
                                    headers=oauthRequest.to_header())
        response = client.connection.getresponse()
        requestToken = oauth.OAuthToken.from_string(response.read())

        params = {'application_name': client.CONSUMER_NAME, 
                  'oauth_consumer_key': client.CONSUMER_KEY}

        oauthRequest = oauth.OAuthRequest.from_token_and_callback(
                                    token=requestToken,
                                    callback=client.CONSUMER_CALLBACK,
                                    http_url=self.authorizationUrl,
                                    parameters=params)

        return ( requestToken, oauthRequest.to_url() )
   
    def getAccessToken(self, requestToken):
        client = self.client
        
        if not isinstance(requestToken, oauth.OAuthToken):
                requestToken = oauth.OAuthToken(requestToken['key'], requestToken['secret'] )
        oauthRequest = oauth.OAuthRequest.from_consumer_and_token(  
                                    client.consumer,
                                    token=requestToken,
                                    http_url=self.accessTokenUrl)
        oauthRequest.sign_request(  client.signature_method_hmac_sha1,
                                    client.consumer,
                                    requestToken)
        client.connection.request(  oauthRequest.http_method,
                                    self.accessTokenUrl,
                                    headers=oauthRequest.to_header())
        response = client.connection.getresponse()
        accessToken = oauth.OAuthToken.from_string(response.read())
        return accessToken
    
    def getData(self):
        accessToken=self.accessToken

        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )
        
        requestUrl = '/users/%s' % (accessToken.key)
        
        info = simplejson.loads( self.client._getResource(requestUrl, token=accessToken ), 'latin-1' )
        self.data = info['user']
        return self.data
        
    def getInfo(self, field):
        accessToken=self.accessToken
        
        if not self.data:
            self.getData()
            
        fields = []
        url = ''
        for link in self.data['link']:
                fields.append(link['title'])
                if link['title'] == field:
                    url = link['href']
                    
        if not url:
            errorString =           "Invalid or missing field.  " + \
                                    "Acceptable fields for this object are:"+ \
                                    "\n\n".join(fields)
            print errorString
            sys.exit(1)
        try:
            info = simplejson.loads(self.client._getResource(url,token=accessToken ), 'latin-1')
        except:
            return []
        else:
            return info
        
    def getRatings(self, discInfo=[], urls=[]):
        accessToken=self.accessToken
        
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken( 
                                    accessToken['key'], 
                                    accessToken['secret'] )
        
        requestUrl = '/users/%s/ratings/title' % (accessToken.key)
        if not urls:
            if isinstance(discInfo,list):
                for disc in discInfo:
                    urls.append(disc['id'])
            else:
                urls.append(discInfo['id'])
        parameters = { 'title_refs': ','.join(urls) }
        
        info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        
        ret = {}
        for title in info['ratings']['ratings_item']:
                ratings = {
                        'average': title['average_rating'],
                        'predicted': title['predicted_rating'],
                }
                try:
                    ratings['user'] = title['user_rating']
                except:
                    pass
                
                ret[ title['title']['regular'] ] = ratings
        
        return ret

    def getRentalHistoryv1(self,historyType=None,startIndex=None,
                                    maxResults=None,updatedMin=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin

        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        if not historyType:
            requestUrl = '/users/%s/rental_history' % (accessToken.key)
        else:
            requestUrl = '/users/%s/rental_history/%s' % (accessToken.key,historyType)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getRentalHistory(self,historyType=None,startIndex=None, maxResults=None,updatedMin=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin

        parameters['v'] = str('2.0')
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )
        #history type must be: NULL, shipped, returned, or watched
        if not historyType:
            requestUrl = '/users/%s/rental_history' % (accessToken.key)
        else:
            requestUrl = '/users/%s/rental_history/%s' % (accessToken.key,historyType)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getInstantQueue(self,historyType=None,startIndex=None,maxResults=None,updatedMin=None,caUser=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if caUser:
            if (caUser == True):
                parameters['country'] = "ca"
        print "params: " + str(parameters)    
        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/instant'
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        if not historyType:
            requestUrl = '/users/%s/queues/instant' % (accessToken.key)
        else:
            requestUrl = '/users/%s/queues/instant/%s' % (accessToken.key,historyType)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getDiscQueue(self,historyType=None,startIndex=None,maxResults=None,updatedMin=None,caUser=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if caUser:
            if (caUser == True):
                parameters['country'] = "ca"
            
        parameters['v'] = str('2.0')
        #parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/disc'
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        if not historyType:
            requestUrl = '/users/%s/queues/disc' % (accessToken.key)
        else:
            requestUrl = '/users/%s/queues/disc/available/%s' % (accessToken.key,historyType)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getAtHomeList(self,historyType=None,startIndex=None,maxResults=None,updatedMin=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin

        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/instant'
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken( 
                                    accessToken['key'],
                                    accessToken['secret'] )

        #if not historyType:
        requestUrl = '/users/%s/at_home' % (accessToken.key)
        #else:
        #    requestUrl = '/users/%s/queues/instant/available/%s' % (accessToken.key,historyType)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getRecommendedQueue(self,startIndex=None,maxResults=None,updatedMin=None,caUser=None):
        accessToken=self.accessToken
        parameters = {}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if caUser:
            if (caUser == True):
                parameters['country'] = "ca"
            
        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/instant'
        parameters['expand'] = '@title,@cast,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'

        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        requestUrl = '/users/%s/recommendations' % (accessToken.key)
        
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
        return info


    #http://api-public.netflix.com/catalog/titles/series/60030529/seasons/60030679/episodes
    def getInstantQueueTvShowEpisodes(self, seriesId, seasonId):
        parameters = {}
        parameters['max_results'] = str('500')
        accessToken=self.accessToken
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken( 
                                    accessToken['key'],
                                    accessToken['secret'] )

        requestUrl = '/catalog/titles/series/' + str(seriesId) + '/seasons/' + str(seasonId) + "/episodes"
      
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info
    
    def getSimilarMovies(self, ID, maxResults=None):
        accessToken=self.accessToken
        parameters = {}
        if maxResults:
            parameters['max_results'] = maxResults

        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/instant'

        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        requestUrl = '/catalog/titles/movies/' + str(ID) + '/similars'
        print requestUrl
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def getSeries(self, curTID, curSeasonID, queue, startIndex=None,maxResults=None,caUser=None):
        accessToken=self.accessToken
        parameters = {}
        requestUrl1 = '/catalog/titles/series/'+curTID
        requestUrl2 = '/seasons/'+curSeasonID
        if(not curSeasonID == ""):
            requestUrl = requestUrl1 + requestUrl2
        else:
            requestUrl = requestUrl1
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if caUser:
            if (caUser == True):
                parameters['country'] = "ca"
            
        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/' + queue
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )
        info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1')
        if re.search(r"Invalid Series", str(info), re.DOTALL | re.IGNORECASE | re.MULTILINE):
            #reset url to programs
            requestUrl = '/catalog/titles/programs/'+curTID
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1')
        if re.search(r"Resource Not Found", str(info), re.DOTALL | re.IGNORECASE | re.MULTILINE):
            #reset url to movies
            requestUrl = '/catalog/titles/movies/'+curTID
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1')
        return info

    def searchTitles(self, term, queue, startIndex=None,maxResults=None,caUser=None):
        accessToken=self.accessToken
        requestUrl = '/catalog/titles'
        parameters = {'term': term}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if caUser:
            if (caUser == True):
                parameters['country'] = "ca"
            
        parameters['v'] = str('2.0')
        parameters['filters'] = 'http://api-public.netflix.com/categories/title_formats/' + queue
        parameters['expand'] = '@title,@synopsis,@directors,@formats,@episodes,@short_synopsis'
        parameters['output'] = 'json'
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )
        info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1')
        return info

    def modifyQueue(self, ID, method):
        accessToken=self.accessToken
        parameters = {}
        #to add, use Post, to remove use Delete
        parameters['method'] = method
        if (method == "post"):
            parameters['title_ref'] = 'http://api-public.netflix.com/catalog/titles/movies/' + str(ID)
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        if (method == "post"):
            requestUrl = '/users/'+ accessToken.key + '/queues/instant/available'
        else:
            requestUrl = '/users/'+ accessToken.key + '/queues/instant/available/' + str(ID) 
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    def modifyQueueDisc(self, ID, method, position=None):
        accessToken=self.accessToken
        parameters = {}
        #to add, use Post, to remove use Delete
        parameters['method'] = method
        if(position):
            parameters['position'] = str(position)
        if (method == "post"):
            parameters['title_ref'] = 'http://api-public.netflix.com/catalog/titles/movies/' + str(ID)
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(accessToken['key'], accessToken['secret'] )

        if (method == "post"):
            requestUrl = '/users/'+ accessToken.key + '/queues/disc/available'
        else:
            requestUrl = '/users/'+ accessToken.key + '/queues/disc/available/' + str(ID) 
        print "------- REQUESTED URL IS: " + requestUrl
        try:
            info = simplejson.loads( self.client._getResource(requestUrl, parameters=parameters, token=accessToken ), 'latin-1' )
        except:
            return {}
            
        return info

    
class NetflixCatalog:

    def __init__(self,client):
        self.client = client
    
    def searchTitles(self, term,startIndex=None,maxResults=None):
        requestUrl = '/catalog/titles'
        parameters = {'term': term}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        info = simplejson.loads( self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters), 'latin-1')

        return info['catalog_titles']['catalog_title']

    def searchStringTitles(self, term,startIndex=None,maxResults=None):
        requestUrl = '/catalog/titles/autocomplete'
        parameters = {'term': term}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults

        info = simplejson.loads( self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters), 'latin-1')
        print simplejson.dumps(info)
        return info['autocomplete']['autocomplete_item']
    
    def getTitle(self, url):
        requestUrl = url
        info = simplejson.loads( self.client._getResource( requestUrl ), 'latin-1')
        return info

    def searchPeople(self, term,startIndex=None,maxResults=None):
        requestUrl = '/catalog/people'
        parameters = {'term': term}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults

        try:
            info = simplejson.loads( self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters), 'latin-1')
        except:
            return []

        return info['people']['person']

    def getPerson(self,url):
        requestUrl = url
        try:
            info = simplejson.loads( self.client._getResource( requestUrl ), 'latin-1')
        except:
            return {}
        return info       

 
class NetflixUserQueue:

    def __init__(self,user):
        self.user = user
        self.client = user.client
        self.tag = None

    def getContents(self, sort=None, startIndex=None, 
                                    maxResults=None, updatedMin=None):
        parameters={}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if sort and sort in ('queue_sequence','date_added','alphabetical'):
            parameters['sort'] = sort
        
        requestUrl = '/users/%s/queues' % (self.user.accessToken.key)
        try:
            info = simplejson.loads(self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters,
                                    token=self.user.accessToken ), 'latin-1')
        except:
            return []
        else:
            return info
            
    def getAvailable(self, sort=None, startIndex=None, 
                                    maxResults=None, updatedMin=None,
                                    queueType='disc'):
        parameters={}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if sort and sort in ('queue_sequence','date_added','alphabetical'):
            parameters['sort'] = sort

        requestUrl = '/users/%s/queues/%s/available' % (
                                    self.user.accessToken.key,
                                    queueType)
        try:
            info = simplejson.loads(self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters,
                                    token=self.user.accessToken ), 'latin-1')
        except:
            return []
        else:
            return info

    def getSaved(self, sort=None, startIndex=None, 
                                    maxResults=None, updatedMin=None,
                                    queueType='disc'):
        parameters={}
        if startIndex:
            parameters['start_index'] = startIndex
        if maxResults:
            parameters['max_results'] = maxResults
        if updatedMin:
            parameters['updated_min'] = updatedMin
        if sort and sort in ('queue_sequence','date_added','alphabetical'):
            parameters['sort'] = sort

        requestUrl = '/users/%s/queues/%s/saved' % (
                                    self.user.accessToken.key,
                                    queueType)
        try:
            info = simplejson.loads(self.client._getResource( 
                                    requestUrl,
                                    parameters=parameters,
                                    token=self.user.accessToken ), 'latin-1')
        except:
            return []
        else:
            return info
 
    def addTitle(self, discInfo=[], urls=[],queueType='disc',position=None):
        accessToken=self.user.accessToken
        parameters={}
        if position:
            parameters['position'] = position
            
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken( 
                                    accessToken['key'],
                                    accessToken['secret'] )

        requestUrl = '/users/%s/queues/disc' % (accessToken.key)
        if not urls:
            for disc in discInfo:
                urls.append( disc['id'] )
        parameters['title_ref'] = ','.join(urls)

        if not self.tag:
            response = self.client._getResource( 
                                    requestUrl, 
                                    token=accessToken )
            response = simplejson.loads(response, 'latin-1')
            self.tag = response["queue"]["etag"]
        parameters['etag'] = self.tag
        response = self.client._postResource( 
                                    requestUrl, 
                                    token=accessToken,
                                    parameters=parameters )
        return response

    def removeTitle(self, id, queueType='disc'):
        accessToken=self.user.accessToken
        entryID = None
        parameters={}
        if not isinstance(accessToken, oauth.OAuthToken):
            accessToken = oauth.OAuthToken(
                                    accessToken['key'],
                                    accessToken['secret'] )

        # First, we gotta find the entry to delete
        queueparams = {'max_results': 500}
        requestUrl = '/users/%s/queues/disc' % (accessToken.key)
        response = self.client._getResource( 
                                    requestUrl,
                                    token=accessToken,
                                    parameters=queueparams )
        print "Response is " + response
        response = simplejson.loads(response, 'latin-1')
        titles = response["queue"]["queue_item"]
        
        for disc in titles:
            discID = os.path.basename(urlparse(disc['id']).path)
            if discID == id:
                entryID = disc['id']

        if not entryID:
            return
        firstResponse = self.client._getResource( 
                                    entryID,
                                    token=accessToken,
                                    parameters=parameters )
        
        response = self.client._deleteResource( entryID, token=accessToken )
        return response


class NetflixDisc:

    def __init__(self,discInfo,client):
        self.info = discInfo
        self.client = client
    
    def getInfo(self,field):
        fields = []
        url = ''
        for link in self.info['link']:
            fields.append(link['title'])
            if link['title'] == field:
                url = link['href']
        if not url:
            errorString =          "Invalid or missing field.  " + \
                                    "Acceptable fields for this object are:" + \
                                    "\n\n".join(fields)
            print errorString
            sys.exit(1)
        try:
            print "==============  the url request is going to" + url
            info = simplejson.loads(self.client._getResource( url ), 'latin-1')
        except:
            return []
        else:
            return info
 
           
class NetflixClient:

    def __init__(self, name, key, secret, callback='',verbose=False):
        self.connection = httplib.HTTPConnection("%s:%s" % (HOST, PORT))
        self.server = HOST
        self.verbose = verbose
        self.user = None
        self.catalog = NetflixCatalog(self)
        
        self.CONSUMER_NAME=name
        self.CONSUMER_KEY=key
        self.CONSUMER_SECRET=secret
        self.CONSUMER_CALLBACK=callback
        self.consumer = oauth.OAuthConsumer(
                                    self.CONSUMER_KEY,
                                    self.CONSUMER_SECRET)
        self.signature_method_hmac_sha1 = \
                                    oauth.OAuthSignatureMethod_HMAC_SHA1()
    
    def _getResource(self, url, token=None, parameters={}):
        if not re.match('http',url):
            url = "http://%s%s" % (HOST, url)
        parameters['output'] = 'json'
        oauthRequest = oauth.OAuthRequest.from_consumer_and_token(
                                    self.consumer,
                                    http_url=url,
                                    parameters=parameters,
                                    token=token)
        oauthRequest.sign_request(  
                                    self.signature_method_hmac_sha1,
                                    self.consumer,
                                    token)
        if (self.verbose):
            print oauthRequest.to_url()
        self.connection.request('GET', oauthRequest.to_url())
        response = self.connection.getresponse()
        return response.read()
    
    def _postResource(self, url, token=None, parameters=None):
        if not re.match('http',url):
            url = "http://%s%s" % (HOST, url)
        
        oauthRequest = oauth.OAuthRequest.from_consumer_and_token(  
                                    self.consumer,
                                    http_url=url,
                                    parameters=parameters,
                                    token=token,
                                    http_method='POST')
        oauthRequest.sign_request(
                                    self.signature_method_hmac_sha1, 
                                    self.consumer, 
                                    token)
        
        if (self.verbose):
            print "POSTING TO" + oauthRequest.to_url()
        
        headers = {'Content-Type':'application/x-www-form-urlencoded'}
        self.connection.request('POST', url, 
                                    body=oauthRequest.to_postdata(), 
                                    headers=headers)
        response = self.connection.getresponse()
        return response.read()
        
    def _deleteResource(self, url, token=None, parameters=None):
        if not re.match('http',url):
            url = "http://%s%s" % (HOST, url)
        
        oauthRequest = oauth.OAuthRequest.from_consumer_and_token(  
                                    self.consumer,
                                    http_url=url,
                                    parameters=parameters,
                                    token=token,
                                    http_method='DELETE')
        oauthRequest.sign_request(
                                    self.signature_method_hmac_sha1, 
                                    self.consumer, 
                                    token)

        if (self.verbose):
            print "DELETING FROM" + oauthRequest.to_url()

        self.connection.request('DELETE', oauthRequest.to_url())
        response = self.connection.getresponse()
        return response.read()

class NetflixError(Exception):
    pass

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii
import re

VERSION = '1.0'
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        strResult = str(s)
        if re.search(r"(invalid|error|date|time)", strResult, re.DOTALL | re.IGNORECASE | re.MULTILINE):
            print "Token result was: " + str(strResult)
            print "If the timestamp shows invalid, your computers date/time is off, sync it to an NTP server or fix it by setting the correct values"
        else:
            print "Token did not contain any errors"
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
__FILENAME__ = settings
import xbmcplugin

def getUserSettingAltPlayer(arg):
    uap = xbmcplugin.getSetting(arg,'useAltPlayer')
    v = False
    if(uap == "0"):
        v = True
    if(uap == "1"):
        v = False
    return v

def getUserSettingOSX(arg):
    osx = xbmcplugin.getSetting(arg,'isOSX')
    v = False
    if(osx == "0"):
        v = True
    if(osx == "1"):
        v = False
    return v

def getUserSettingCaUser(arg):
    cau = xbmcplugin.getSetting(arg,'caUser')
    v = False
    if(cau == "0"):
        v = True
    if(cau == "1"):
        v = False
    return v

def getUserSettingExpandEpisodes(arg):
    #no longer used, return False
    ee = xbmcplugin.getSetting(arg,'expandEpisodes')
    v = False
    return False
    if(ee == "0"):
        v = True
    if(ee == "1"):
        v = False
    return v


def getUserSettingDebug(arg):
    deb = xbmcplugin.getSetting(arg,'debug')
    v = False
    if(deb == "0"):
        v = True
    if(deb == "1"):
        v = False
    return v

def getUserSettingVerboseUserInfo(arg):
    vui = xbmcplugin.getSetting(arg,'verboseuser')
    v = False
    if(vui == "0"):
        v = True
    if(vui == "1"):
        v = False
    return v

def getUserSettingAppendYear(arg):
    ay = xbmcplugin.getSetting(arg,'appendYear')
    v = False
    if(ay == "0"):
        v = True
    if(ay == "1"):
        v = False
    return v

def getUserSettingYearLimit(arg):
    ylim = xbmcplugin.getSetting(arg, 'yearLimit')
    return str(ylim)

def getUserSettingShowRatingInTitle(arg):
    ay = xbmcplugin.getSetting(arg,'showRatingInTitle')
    v = False
    if(ay == "0"):
        v = True
    if(ay == "1"):
        v = False
    return v

def getUserSettingPosterQuality(arg):
    pqs = xbmcplugin.getSetting(arg,'pQuality')
    v = "ghd"
    if(pqs == "0"):
        v = "ghd"
    if(pqs == "1"):
        v =  "large"
    if(pqs == "2"):
        v =  "medium"
    if(pqs == "3"):
        v =  "small"
    return v

def getUserSettingRatingLimit(arg):
    maxr = xbmcplugin.getSetting(arg,'mrLimit')
    v = ""
    if(maxr == "0"):
        v = "10000"
    elif(maxr == "1"):
        v =  "1000"
    elif(maxr == "2"):
        v =  "130"
    elif(maxr == "3"):
        v =  "110"
    elif(maxr == "4"):
        v =  "100"
    elif(maxr == "5"):
        v =  "90"
    elif(maxr == "6"):
        v =  "80"
    elif(maxr == "7"):
        v =  "75"
    elif(maxr == "8"):
        v =  "60"
    elif(maxr == "9"):
        v =  "50"
    elif(maxr == "10"):
        v =  "40"
    elif(maxr == "11"):
        v =  "20"
    elif(maxr == "12"):
        v =  "10"
    return v

def getUserSettingGenreDisplay(arg, sgGenre):
    vui = xbmcplugin.getSetting(arg, str(sgGenre))
    v = False
    if(vui == "0"):
        v = True
    if(vui == "1"):
        v = False
    return v

def getUserSettingMaxIQRetreve(arg):
    maxr = xbmcplugin.getSetting(arg,'maxIqR')
    v = ""
    if(maxr == "0"):
        v = "10"
    if(maxr == "1"):
        v =  "25"
    if(maxr == "2"):
        v =  "50"
    if(maxr == "3"):
        v =  "75"
    if(maxr == "4"):
        v =  "100"
    if(maxr == "5"):
        v =  "200"
    if(maxr == "6"):
        v =  "300"
    if(maxr == "7"):
        v =  "400"
    if(maxr == "8"):
        v =  "500"
    return v

########NEW FILE########
__FILENAME__ = xinfo
class XInfo:
    def __init__(self):
        self.Mpaa = "n/a"
        self.Position = "0"
        self.Year = "0000"
        self.Title = "Item Full Title Name"
        self.TitleShort = "Short Item Title"
        self.TitleShortOriginal = "Original Short Item Title"
        self.TitleShortLink = "Short Item Title with no spaces"
        self.Rating = "0.0"
        self.Runtime = "0"
        self.Genres = ""
        self.Directors = ""
        self.ID = ""
        self.FullId = ""
        self.Poster = ""
        self.Cast = ""
        self.Synop = ""
        self.TvShow = False
        self.TvShowLink = ""
        self.TvShowSeasonID = ""
        self.TvShowSeriesID = ""
        self.TvEpisode = False
        self.TvEpisodeList = []
        self.TvEpisodeNetflixID = ""
        self.TvEpisodeEpisodeNum = 0
        self.TvEpisodeEpisodeSeasonNum = 0
        self.IsInstantAvailable = False
        self.MaturityLevel = "0"
        self.AvailableUntil = "0"
        self.WebURL = ""
        self.LinkName = ""
        self.oData = False
        self.iAvail = False
        self.iAvailFrom = ""
        self.iAvailTil = ""
        self.dAvail = False
        self.dAvailFrom = ""
        self.dAvailTil = ""
        self.bAvail = False
        self.bAvailFrom = ""
        self.bAvailTil = ""
        self.nomenu = False
        



########NEW FILE########
