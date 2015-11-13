__FILENAME__ = autoProcessComics
import sys
import urllib
import os.path
import time
import ConfigParser
import logging
import socket

from nzbToMediaEnv import *
from nzbToMediaUtil import *
from nzbToMediaSceneExceptions import process_all_exceptions

Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)
    
    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)


def processEpisode(dirName, nzbName=None, status=0, inputCategory=None):

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)
    
    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure
    
    config.read(configFilename)

    section = "Mylar"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory
    host = config.get(section, "host")
    port = config.get(section, "port")
    username = config.get(section, "username")
    password = config.get(section, "password")
    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0
    
    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        watch_dir = config.get(section, "watch_dir")
    except ConfigParser.NoOptionError:
        watch_dir = ""
    params = {}

    nzbName, dirName = converto_to_ascii(nzbName, dirName)

    if dirName == "Manual Run" and watch_dir != "":
        dirName = watch_dir
    
    params['nzb_folder'] = dirName
    if nzbName != None:
        params['nzb_name'] = nzbName
        
    myOpener = AuthURLOpener(username, password)
    
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/post_process?" + urllib.urlencode(params)
    
    Logger.debug("Opening URL: %s", url)
    
    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure
    
    result = urlObj.readlines()
    for line in result:
         Logger.info("%s", line)
    
    time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
    return 0 # Success        

########NEW FILE########
__FILENAME__ = autoProcessGames
import sys
import urllib
import os
import shutil
import ConfigParser
import datetime
import time
import json
import logging
import socket

from nzbToMediaEnv import *
from nzbToMediaUtil import *

Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

def process(dirName, nzbName=None, status=0, inputCategory=None):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    section = "Gamez"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory

    host = config.get(section, "host")
    port = config.get(section, "port")
    apikey = config.get(section, "apikey")

    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    nzbName, dirName = converto_to_ascii(nzbName, dirName)

    baseURL = protocol + host + ":" + port + web_root + "/api?api_key=" + apikey + "&mode="

    fields = nzbName.split("-")
    gamezID = fields[0].replace("[","").replace("]","").replace(" ","")
    downloadStatus = 'Wanted'
    if status == 0:
        downloadStatus = 'Downloaded'

    url = baseURL + "UPDATEREQUESTEDSTATUS&db_id=" + gamezID + "&status=" + downloadStatus

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = urllib.urlopen(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure

    result = json.load(urlObj)
    Logger.info("Gamez returned %s", result)
    if result['success']:
        Logger.info("Status for %s has been set to %s in Gamez", gamezID, downloadStatus)
        return 0 # Success
    else:
        Logger.error("Status for %s has NOT been updated in Gamez", gamezID)
        return 1 # failure

########NEW FILE########
__FILENAME__ = autoProcessMovie
import sys
import urllib
import os
import shutil
import ConfigParser
import datetime
import time
import json
import logging
import socket

import Transcoder
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from nzbToMediaSceneExceptions import process_all_exceptions

Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

def get_imdb(nzbName, dirName):
 
    imdbid = ""    

    a = nzbName.find('.cp(') + 4 #search for .cptt( in nzbName
    b = nzbName[a:].find(')') + a
    if a > 3: # a == 3 if not exist
        imdbid = nzbName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in name", imdbid) 
        return imdbid
    
    a = dirName.find('.cp(') + 4 #search for .cptt( in dirname
    b = dirName[a:].find(')') + a
    if a > 3: # a == 3 if not exist
        imdbid = dirName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in directory", imdbid) 
        return imdbid

    else:
        Logger.debug("Could not find an imdb id in directory or name")
        return ""

def get_movie_info(baseURL, imdbid, download_id):
    
    if not imdbid and not download_id:
        return "", None, imdbid

    movie_id = ""
    releaselist = []
    movieid = []
    library = []
    offset = int(0)
    while True:
        url = baseURL + "media.list/?status=active&release_status=snatched&limit_offset=50," + str(offset)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            break

        movieid2 = []
        library2 = []
        try:
            result = json.load(urlObj)
            movieid2 = [item["id"] for item in result["movies"]]
            library2 = [item["library"]["identifier"] for item in result["movies"]]
        except:
            Logger.exception("Unable to parse json data for movies")
            break

        movieid.extend(movieid2)
        library.extend(library2)
        if len(movieid2) < int(50): # finished parsing list of movies. Time to break.
            break
        offset = offset + 50

    result = None # reset
    for index in range(len(movieid)):
        if not imdbid:
            url = baseURL + "media.get/?id=" + str(movieid[index])
            Logger.debug("Opening URL: %s", url)
            try:
                urlObj = urllib.urlopen(url)
            except:
                Logger.exception("Unable to open URL")
                return "", None, imdbid
            try:
                result = json.load(urlObj)
                releaselist = [item["info"]["download_id"] for item in result["media"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower()]  
            except:
                Logger.exception("Unable to parse json data for releases")
                return "", None, imdbid

            if len(releaselist) > 0:
                movie_id = str(movieid[index])
                imdbid = str(library[index])
                Logger.info("Found movie id %s and imdb %s in database via download_id %s", movie_id, imdbid, download_id)
                break
            else:
                continue

        if library[index] == imdbid:
            movie_id = str(movieid[index])
            Logger.info("Found movie id %s in CPS database for movie %s", movie_id, imdbid)
            break

    if not movie_id:
        Logger.exception("Could not parse database results to determine imdbid or movie id")

    return movie_id, result, imdbid 

def get_status(baseURL, movie_id, clientAgent, download_id, result=None):
    
    if not movie_id:
        return "", clientAgent, "none", "none"

    Logger.debug("Looking for status of movie: %s - with release sent to clientAgent: %s and download_id: %s", movie_id, clientAgent, download_id)
    if not result: # we haven't already called media.get
        url = baseURL + "media.get/?id=" + str(movie_id)
        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            return "", clientAgent, "none", "none"
        result = json.load(urlObj)
    try:
        movie_status = result["media"]["status"]["identifier"]
        Logger.debug("This movie is marked as status %s in CouchPotatoServer", movie_status)
    except: # index out of range/doesn't exist?
        Logger.exception("Could not find a status for this movie")
        movie_status = ""
    try:
        release_status = "none"
        if download_id != "" and download_id != "none": # we have the download id from the downloader. Let's see if it's valid.
            release_statuslist = [item["status"]["identifier"] for item in result["media"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower()]
            clientAgentlist = [item["info"]["download_downloader"] for item in result["media"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower()]
            if len(release_statuslist) == 1: # we have found a release by this id. :)
                release_status = release_statuslist[0]
                clientAgent = clientAgentlist[0]
                Logger.debug("Found a single release with download_id: %s for clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                return movie_status, clientAgent, download_id, release_status
            elif len(release_statuslist) > 1: # we have found many releases by this id. Check for snatched status
                clients = [item for item in clientAgentlist if item.lower() == clientAgent.lower()]
                clientAgent = clients[0]
                if len(clients) == 1: # ok.. a unique entry for download_id and clientAgent ;)
                    release_status = [item["status"]["identifier"] for item in result["media"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower() and item["info"]["download_downloader"] == clientAgent][0]
                    Logger.debug("Found a single release for download_id: %s and clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                else: # doesn't matter. only really used as secondary confirmation of movie status change. Let's continue.                
                    Logger.debug("Found several releases for download_id: %s and clientAgent: %s. Cannot determine the release status", download_id, clientAgent)
                return movie_status, clientAgent, download_id, release_status
            else: # clearly the id we were passed doesn't match the database. Reset it and search all snatched releases.... hence the next if (not elif ;) )
                download_id = "" 
        if download_id == "none": # if we couldn't find this initially, there is no need to check next time around.
            return movie_status, clientAgent, download_id, release_status
        elif download_id == "": # in case we didn't get this from the downloader.
            download_idlist = [item["info"]["download_id"] for item in result["media"]["releases"] if item["status"]["identifier"] == "snatched"]
            clientAgentlist = [item["info"]["download_downloader"] for item in result["media"]["releases"] if item["status"]["identifier"] == "snatched"]
            if len(clientAgentlist) == 1:
                if clientAgent == "manual":
                    clientAgent = clientAgentlist[0]
                    download_id = download_idlist[0]
                    release_status = "snatched"
                elif clientAgent.lower() == clientAgentlist[0].lower():
                    download_id = download_idlist[0]
                    clientAgent = clientAgentlist[0]
                    release_status = "snatched"
                Logger.debug("Found a single download_id: %s and clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status) 
            elif clientAgent == "manual":
                download_id = "none"
                release_status = "none"
            else:
                index = [index for index in range(len(clientAgentlist)) if clientAgentlist[index].lower() == clientAgent.lower()]            
                if len(index) == 1:
                    download_id = download_idlist[index[0]]
                    clientAgent = clientAgentlist[index[0]]
                    release_status = "snatched"
                    Logger.debug("Found download_id: %s for clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                else:
                    Logger.info("Found a total of %s releases snatched for clientAgent: %s. Cannot determine download_id. Will perform a renamenr scan to try and process.", len(index), clientAgent)                
                    download_id = "none"
                    release_status = "none"
        else: #something went wrong here.... we should never get to this.
            Logger.info("Could not find a download_id in the database for this movie")
            release_status = "none"
    except: # index out of range/doesn't exist?
        Logger.exception("Could not find a download_id for this movie")
        download_id = "none"
    return movie_status, clientAgent, download_id, release_status

def process(dirName, nzbName=None, status=0, clientAgent = "manual", download_id = "", inputCategory=None):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    section = "CouchPotato"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory

    host = config.get(section, "host")
    port = config.get(section, "port")
    apikey = config.get(section, "apikey")
    delay = float(config.get(section, "delay"))
    method = config.get(section, "method")
    delete_failed = int(config.get(section, "delete_failed"))
    wait_for = int(config.get(section, "wait_for"))

    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""
        
    try:    
        transcode = int(config.get("Transcoder", "transcode"))
    except (ConfigParser.NoOptionError, ValueError):
        transcode = 0

    try:
        remoteCPS = int(config.get(section, "remoteCPS"))
    except (ConfigParser.NoOptionError, ValueError):
        remoteCPS = 0

    nzbName = str(nzbName) # make sure it is a string
    
    imdbid = get_imdb(nzbName, dirName)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    baseURL = protocol + host + ":" + port + web_root + "/api/" + apikey + "/"
    
    movie_id, result, imdbid = get_movie_info(baseURL, imdbid, download_id) # get the CPS database movie id for this movie.
   
    initial_status, clientAgent, download_id, initial_release_status = get_status(baseURL, movie_id, clientAgent, download_id, result)
    
    process_all_exceptions(nzbName.lower(), dirName)
    nzbName, dirName = converto_to_ascii(nzbName, dirName)

    TimeOut2 = int(wait_for) * 60 # If transfering files across directories, it now appears CouchPotato can take a while to confirm this url request... Try using wait_for timing.
    socket.setdefaulttimeout(int(TimeOut2)) #initialize socket timeout. We may now be able to remove the delays from the wait_for section below?

    if status == 0:
        if transcode == 1:
            result = Transcoder.Transcode_directory(dirName)
            if result == 0:
                Logger.debug("Transcoding succeeded for files in %s", dirName)
            else:
                Logger.warning("Transcoding failed for files in %s", dirName)

        if method == "manage":
            command = "manage.update"
        else:
            command = "renamer.scan"
            if clientAgent != "manual" and download_id != "none":
                if remoteCPS == 1:
                    command = command + "/?downloader=" + clientAgent + "&download_id=" + download_id
                else:
                    command = command + "/?media_folder=" + urllib.quote(dirName) + "&downloader=" + clientAgent + "&download_id=" + download_id

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow CPS to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = json.load(urlObj)
        Logger.info("CouchPotatoServer returned %s", result)
        if result['success']:
            Logger.info("%s scan started on CouchPotatoServer for %s", method, nzbName)
        else:
            Logger.error("%s scan has NOT started on CouchPotatoServer for %s. Exiting", method, nzbName)
            return 1 # failure

    else:
        Logger.info("Download of %s has failed.", nzbName)
        Logger.info("Trying to re-cue the next highest ranked release")
        
        if not movie_id:
            Logger.warning("Cound not find a movie in the database for release %s", nzbName)
            Logger.warning("Please manually ignore this release and refresh the wanted movie")
            Logger.error("Exiting autoProcessMovie script")
            return 1 # failure

        url = baseURL + "movie.searcher.try_next/?id=" + movie_id

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = urlObj.readlines()
        for line in result:
            Logger.info("%s", line)

        Logger.info("Movie %s set to try the next best release on CouchPotatoServer", movie_id)
        if delete_failed and not dirName in ['sys.argv[0]','/','']:
            Logger.info("Deleting failed files and folder %s", dirName)
            try:
                shutil.rmtree(dirName)
            except:
                Logger.exception("Unable to delete folder %s", dirName)
        return 0 # success
    
    if nzbName == "Manual Run" or download_id == "none":
        return 0 # success

    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

    start = datetime.datetime.now()  # set time for timeout
    pause_for = int(wait_for) * 10 # keep this so we only ever have 6 complete loops. This may not be necessary now?
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=wait_for):  # only wait 2 (default) minutes, then return.
        movie_status, clientAgent, download_id, release_status = get_status(baseURL, movie_id, clientAgent, download_id) # get the current status fo this movie.
        if movie_status != initial_status:  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This movie is now marked as status %s in CouchPotatoServer", movie_status)
            return 0 # success
        time.sleep(pause_for) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:
        if release_status != initial_release_status and release_status != "none":  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This release is now marked as status %s in CouchPotatoServer", release_status)
            return 0 # success
        else: # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now. 
            Logger.warning("The movie does not appear to have changed status after %s minutes. Please check CouchPotato Logs", wait_for)
            return 1 # failure

########NEW FILE########
__FILENAME__ = autoProcessMusic
import sys
import urllib
import os
import shutil
import ConfigParser
import datetime
import time
import json
import logging
import socket

from nzbToMediaEnv import *
from nzbToMediaUtil import *

Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

def process(dirName, nzbName=None, status=0, inputCategory=None):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    section = "HeadPhones"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory

    host = config.get(section, "host")
    port = config.get(section, "port")
    apikey = config.get(section, "apikey")
    delay = float(config.get(section, "delay"))

    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    nzbName, dirName = converto_to_ascii(nzbName, dirName)

    baseURL = protocol + host + ":" + port + web_root + "/api?apikey=" + apikey + "&cmd="

    if status == 0:
        command = "forceProcess"

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow HeadPhones to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = urlObj.readlines()
        Logger.info("HeadPhones returned %s", result)
        if result[0] == "OK":
            Logger.info("%s started on HeadPhones for %s", command, nzbName)
        else:
            Logger.error("%s has NOT started on HeadPhones for %s. Exiting", command, nzbName)
            return 1 # failure
            
    else:
        Logger.info("The download failed. Nothing to process")
        return 0 # Success (as far as this script is concerned)

    if nzbName == "Manual Run":
        return 0 # success

    # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
    ## Hopefully we can use a "getHistory" check in here to confirm processing complete...
    start = datetime.datetime.now()  # set time for timeout
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=1):  # only wait 2 minutes, then return to TorrentToMedia
        time.sleep(20) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:  # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
        Logger.info("This album should have completed processing. Please check HeadPhones Logs")
        # Logger.warning("The album does not appear to have changed status after 2 minutes. Please check HeadPhones Logs")
    # return 1 # failure
    return 0 # success for now.

########NEW FILE########
__FILENAME__ = autoProcessTV
import sys
import urllib
import os
import ConfigParser
import logging
import shutil
import time
import socket

import Transcoder
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from nzbToMediaSceneExceptions import process_all_exceptions

Logger = logging.getLogger()

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)


def delete(dirName):
    Logger.info("Deleting failed files and folder %s", dirName)
    try:
        shutil.rmtree(dirName, True)
    except:
        Logger.exception("Unable to delete folder %s", dirName)


def processEpisode(dirName, nzbName=None, failed=False, clientAgent=None, inputCategory=None):

    status = int(failed)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    section = "SickBeard"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory

    watch_dir = ""
    host = config.get(section, "host")
    port = config.get(section, "port")
    username = config.get(section, "username")
    password = config.get(section, "password")
    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        watch_dir = config.get(section, "watch_dir")
    except ConfigParser.NoOptionError:
        watch_dir = ""

    try:
        fork = config.get(section, "fork")
    except ConfigParser.NoOptionError:
        fork = "default"

    try:    
        transcode = int(config.get("Transcoder", "transcode"))
    except (ConfigParser.NoOptionError, ValueError):
        transcode = 0

    try:
        delete_failed = int(config.get(section, "delete_failed"))
    except (ConfigParser.NoOptionError, ValueError):
        delete_failed = 0
    try:
        delay = float(config.get(section, "delay"))
    except (ConfigParser.NoOptionError, ValueError):
        delay = 0
    try:
        wait_for = int(config.get(section, "wait_for"))
    except (ConfigParser.NoOptionError, ValueError):
        wait_for = 5
    try:
        SampleIDs = (config.get("Extensions", "SampleIDs")).split(',')
    except (ConfigParser.NoOptionError, ValueError):
        SampleIDs = ['sample','-s.']
    try:
        nzbExtractionBy = config.get(section, "nzbExtractionBy")
    except (ConfigParser.NoOptionError, ValueError):
        nzbExtractionBy = "Downloader"

    TimeOut = 60 * int(wait_for) # SickBeard needs to complete all moving and renaming before returning the log sequence via url.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')
    minSampleSize = int(config.get("Extensions", "minSampleSize"))

    if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
        dirName = os.path.split(os.path.normpath(dirName))[0]

    SpecificPath = os.path.join(dirName, nzbName)
    cleanName = os.path.splitext(SpecificPath)
    if cleanName[1] == ".nzb":
        SpecificPath = cleanName[0]
    if os.path.isdir(SpecificPath):
        dirName = SpecificPath

    SICKBEARD_TORRENT_USE = SICKBEARD_TORRENT

    if clientAgent in ['nzbget','sabnzbd'] and not nzbExtractionBy == "Destination": #Assume Torrent actions (unrar and link) don't happen. We need to check for valid media here.
        SICKBEARD_TORRENT_USE = []

    if not fork in SICKBEARD_TORRENT_USE:
        process_all_exceptions(nzbName.lower(), dirName)
        nzbName, dirName = converto_to_ascii(nzbName, dirName)

    if nzbName != "Manual Run" and not fork in SICKBEARD_TORRENT_USE:
        # Now check if movie files exist in destination:
        video = int(0)
        for dirpath, dirnames, filenames in os.walk(dirName):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileExtension = os.path.splitext(file)[1]
                if fileExtension in mediaContainer:  # If the file is a video file
                    if is_sample(filePath, nzbName, minSampleSize, SampleIDs):
                        Logger.debug("Removing sample file: %s", filePath)
                        os.unlink(filePath)  # remove samples
                    else:
                        video = video + 1
        if video > 0:  # Check that a video exists. if not, assume failed.
            flatten(dirName) # to make sure SickBeard can find the video (not in sub-folder)
        else:
            Logger.warning("No media files found in directory %s. Processing this as a failed download", dirName)
            status = int(1)
            failed = True

    if watch_dir != "" and (not host in ['localhost', '127.0.0.1'] or nzbName == "Manual Run"):
        dirName = watch_dir

    params = {}

    params['quiet'] = 1
    if fork in SICKBEARD_DIRNAME:
        params['dirName'] = dirName
    else:
        params['dir'] = dirName

    if nzbName != None:
        params['nzbName'] = nzbName

    if fork in SICKBEARD_FAILED:
        params['failed'] = failed

    if status == 0:
        Logger.info("The download succeeded. Sending process request to SickBeard's %s branch", fork)
    elif fork in SICKBEARD_FAILED:
        Logger.info("The download failed. Sending 'failed' process request to SickBeard's %s branch", fork)
    else:
        Logger.info("The download failed. SickBeard's %s branch does not handle failed downloads. Nothing to process", fork)
        if delete_failed and os.path.isdir(dirName) and not dirName in ['sys.argv[0]','/','']:
            Logger.info("Deleting directory: %s", dirName)
            delete(dirName)
        return 0 # Success (as far as this script is concerned)
    
    if status == 0 and transcode == 1: # only transcode successful downlaods
        result = Transcoder.Transcode_directory(dirName)
        if result == 0:
            Logger.debug("Transcoding succeeded for files in %s", dirName)
        else:
            Logger.warning("Transcoding failed for files in %s", dirName)

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(params)

    Logger.info("Waiting for %s seconds to allow SB to process newly extracted files", str(delay))

    time.sleep(delay)

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure

    result = urlObj.readlines()
    for line in result:
        Logger.info("%s", line.rstrip())
    if status != 0 and delete_failed and not dirName in ['sys.argv[0]','/','']:
        delete(dirName)
    return 0 # Success

########NEW FILE########
__FILENAME__ = migratecfg
#System imports
import ConfigParser
import sys
import os

def migrate():
    confignew = ConfigParser.ConfigParser()
    confignew.optionxform = str
    configFilenamenew = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")
    confignew.read(configFilenamenew)

    configold = ConfigParser.ConfigParser()
    configold.optionxform = str

    categories = []

    section = "CouchPotato"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilenameold): # lets look back for an older version.
        configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMovie.cfg")
        if not os.path.isfile(configFilenameold): # no config available
            configFilenameold = ""
    if configFilenameold: # read our old config.
        configold.read(configFilenameold)
        try:
            original = configold.items(section)
        except:
            pass
    for item in original:
        option, value = item
        if option == "category": # change this old format
            option = "cpsCategory"
        if option == "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(value))[0]
            confignew.set("Torrent", option, value)
            continue
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        if option == "cpsCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    section = "SickBeard"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilenameold): # lets look back for an older version.
        configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
        if not os.path.isfile(configFilenameold): # no config available
            configFilenameold = ""
    if configFilenameold: # read our old config.
        configold.read(configFilenameold)
        try:
            original = configold.items(section)
        except:
            pass
    for item in original:
        option, value = item
        if option == "category": # change this old format
            option = "sbCategory"
        if option == "failed_fork": # change this old format
            option = "fork"
            if int(value) == 1:
                value = "failed"
            else:
                value = "default"
        if option == "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(value))[0]
            confignew.set("Torrent", option, value)
            continue
        if option == "sbCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value) 

    section = "HeadPhones"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if os.path.isfile(configFilenameold): # read our old config.
        configold.read(configFilenameold)
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        option, value = item
        if option == "hpCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value) 

    section = "Mylar"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option == "mlCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    section = "Gamez"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        if option == "gzCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    for section in categories:
        original = []
        try:
            original = configold.items(section)
        except:
            continue
        try:
            confignew.add_section(section)
        except:
            pass
        for item in original:
            option, value = item
            confignew.set(section, option, value) 

    section = "Torrent"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
            section = "Extensions" # these were moved
        if option == "useLink": # Sym links supported now as well.
            try:
                num_value = int(value)
                if num_value == 1:
                    value = "hard"
                else:
                    value = "no"
            except ValueError:
                pass
        confignew.set(section, option, value)
        section = "Torrent" # reset in case extensions out of order.

    section = "Extensions"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "Transcoder"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "WakeOnLan"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "UserScript"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "ASCII"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "passwords"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "loggers"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "handlers"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "formatters"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "logger_root"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "handler_console"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "formatter_generic"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    # writing our configuration file to 'autoProcessMedia.cfg.sample'
    with open(configFilenamenew, 'wb') as configFile:
        confignew.write(configFile)

    # create a backup of our old config
    if os.path.isfile(configFilenameold):
        backupname = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.old")
        if os.path.isfile(backupname): # remove older backups
            os.unlink(backupname)
        os.rename(configFilenameold, backupname)

    if os.path.isfile(configFilenamenew):
        # rename our newly edited autoProcessMedia.cfg.sample to autoProcessMedia.cfg
        os.rename(configFilenamenew, configFilenameold)
        return

def addnzbget():
    confignew = ConfigParser.ConfigParser()
    confignew.optionxform = str
    configFilenamenew = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    confignew.read(configFilenamenew)

    section = "CouchPotato"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR']
    cfgKeys = ['cpsCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for']
    for index in range(len(envKeys)):
        key = 'NZBPO_CPS' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)


    section = "SickBeard"
    envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'WAIT_FOR']
    cfgKeys = ['sbCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'wait_for']
    for index in range(len(envKeys)):
        key = 'NZBPO_SB' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "HeadPhones"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY']
    cfgKeys = ['hpCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay']
    for index in range(len(envKeys)):
        key = 'NZBPO_HP' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value) 

    section = "Mylar"
    envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT']
    cfgKeys = ['mlCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root']
    for index in range(len(envKeys)):
        key = 'NZBPO_ML' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "Gamez"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT']
    cfgKeys = ['gzCategory', 'apikey', 'host', 'port', 'ssl', 'web_root']
    for index in range(len(envKeys)):
        key = 'NZBPO_GZ' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "Extensions"
    envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
    cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
    for index in range(len(envKeys)):
        key = 'NZBPO_' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "Transcoder"
    envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC', 'OUTPUTAUDIOBITRATE', 'OUTPUTSUBTITLECODEC']
    cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputVideoExtension', 'outputVideoCodec', 'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec', 'outputAudioBitrate', 'outputSubtitleCodec']
    for index in range(len(envKeys)):
        key = 'NZBPO_' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "WakeOnLan"
    envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
    cfgKeys = ['wake', 'host', 'port', 'mac']
    for index in range(len(envKeys)):
        key = 'NZBPO_WOL' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)


    # writing our configuration file to 'autoProcessMedia.cfg'
    with open(configFilenamenew, 'wb') as configFile:
        confignew.write(configFile)

    return

########NEW FILE########
__FILENAME__ = nzbToMediaEnv
# Make things easy and less error prone by centralising all common values

# Global Constants
VERSION = 'V9.2'
TimeOut = 60

# Constants pertinant to SabNzb
SABNZB_NO_OF_ARGUMENTS = 8
SABNZB_0717_NO_OF_ARGUMENTS = 9

# Constants pertaining to SickBeard Branches: 
# extend this list to include all branches/forks that use "failed" to handle failed downloads.
SICKBEARD_FAILED = ["failed", "TPB-failed", "Pistachitos", "TPB"]
# extend this list to include all branches/forks that use "dirName" not "dir"
SICKBEARD_DIRNAME = ["failed"] 
# extend this list to include all branches/forks that process rar and link files for torrents and therefore skip extraction and linking in TorrentToMedia.
SICKBEARD_TORRENT = ["TPB", "TPB-failed", "Pistachitos"]



########NEW FILE########
__FILENAME__ = nzbToMediaSceneExceptions
# System imports
import os
import logging

# Custom imports
from nzbToMediaUtil import iterate_media_files


Logger = logging.getLogger()


def process_all_exceptions(name, dirname):
    for group, exception in __customgroups__.items():
        if not (group in name or group in dirname):
            continue
        process_exception(exception, name, dirname)


def process_exception(exception, name, dirname):
    for parentDir, filename in iterate_media_files(dirname):
        exception(filename, parentDir)


def process_qoq(filename, dirname):
    Logger.debug("Reversing the file name for a QoQ release %s", filename)
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    newname = head[::-1]
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    os.rename(filename, newfilePath)
    Logger.debug("New file name is %s", newfile)

# dict for custom groups
# we can add more to this list
__customgroups__ = {'Q o Q': process_qoq}

########NEW FILE########
__FILENAME__ = nzbToMediaUtil
import logging
import logging.config
import os
import re
import sys
import shutil
import struct
import socket
import time
import ConfigParser

import linktastic.linktastic as linktastic

Logger = logging.getLogger()


def safeName(name):
    safename = re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", name) #make this name safe for use in directories for windows etc.
    return safename


def nzbtomedia_configure_logging(dirname):
    logFile = os.path.join(dirname, "postprocess.log")
    logging.config.fileConfig(os.path.join(dirname, "autoProcessMedia.cfg"))
    fileHandler = logging.handlers.RotatingFileHandler(logFile, mode='a', maxBytes=1048576, backupCount=1, encoding='utf-8', delay=True)
    fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
    fileHandler.level = logging.DEBUG
    logging.getLogger().addHandler(fileHandler)


def create_destination(outputDestination):
    if os.path.exists(outputDestination):
        return
    try:
        Logger.info("CREATE DESTINATION: Creating destination folder: %s", outputDestination)
        os.makedirs(outputDestination)
    except:
        Logger.exception("CREATE DESTINATION: Not possible to create destination folder. Exiting")
        sys.exit(-1)

def category_search(inputDirectory, inputName, inputCategory, root, categories):
    if not os.path.isdir(inputDirectory) and os.path.isfile(inputDirectory): # If the input directory is a file, assume single file downlaod and split dir/name.
        inputDirectory,inputName = os.path.split(os.path.normpath(inputDirectory))

    if inputCategory and os.path.isdir(os.path.join(inputDirectory, inputCategory)):
        Logger.info("SEARCH: Found category directory %s in input directory directory %s", inputCategory, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputCategory)
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    if inputName and os.path.isdir(os.path.join(inputDirectory, inputName)):
        Logger.info("SEARCH: Found torrent directory %s in input directory directory %s", inputName, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputName)
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    if inputName and os.path.isdir(os.path.join(inputDirectory, safeName(inputName))):
        Logger.info("SEARCH: Found torrent directory %s in input directory directory %s", safeName(inputName), inputDirectory)
        inputDirectory = os.path.join(inputDirectory, safeName(inputName))
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    
    categorySearch = [os.path.normpath(inputDirectory), ""]  # initializie
    notfound = 0
    unique = int(0)
    for x in range(10):  # loop up through 10 directories looking for category.
        try:
            categorySearch2 = os.path.split(os.path.normpath(categorySearch[0]))
        except:  # this might happen when we can't go higher.
            if unique == int(0):
                if inputCategory and inputName:  # if these exists, we are ok to proceed, but assume we are in a root/common directory.
                    Logger.info("SEARCH: Could not find a category in the directory structure")
                    Logger.info("SEARCH: We will try and determine which files to process, individually")
                    root = 1
                    break  # we are done
                elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
                    Logger.info("SEARCH: Could not find a torrent name or category in the directory structure")
                    Logger.info("SEARCH: We will try and determine which files to process, individually")
                    root = 2
                    break  # we are done
                elif inputName:  # we didn't find category after 10 loops. This is a problem.
                    Logger.info("SEARCH: Could not find a category in the directory structure")
                    Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
                    root = 1
                    break  # we are done
                else:  # we didn't find this after 10 loops. This is a problem.
                    Logger.info("SEARCH: Could not identify category or torrent name from the directory structure.")
                    Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
                    root = 2
                    break  # we are done

        if categorySearch2[1] in categories:
            Logger.debug("SEARCH: Found Category: %s in directory structure", categorySearch2[1])
            if not inputCategory:
                Logger.info("SEARCH: Determined Category to be: %s", categorySearch2[1])
                inputCategory = categorySearch2[1]
            if inputName and categorySearch[0] != os.path.normpath(inputDirectory):  # if we are not in the root directory and we have inputName we can continue.
                if ('.cp(tt' in categorySearch[1]) and (not '.cp(tt' in inputName):  # if the directory was created by CouchPotato, and this tag is not in Torrent name, we want to add it.
                    Logger.info("SEARCH: Changing Torrent Name to %s to preserve imdb id.", categorySearch[1])
                    inputName = categorySearch[1]
                    Logger.info("SEARCH: Identified Category: %s and Torrent Name: %s. We are in a unique directory, so we can proceed.", inputCategory, inputName)
                break  # we are done
            elif categorySearch[1] and not inputName:  # assume the the next directory deep is the torrent name.
                inputName = categorySearch[1]
                Logger.info("SEARCH: Found torrent name: %s", categorySearch[1])
                if os.path.isdir(os.path.join(categorySearch[0], categorySearch[1])):
                    Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], categorySearch[1]), categorySearch[0])
                    inputDirectory = os.path.normpath(os.path.join(categorySearch[0], categorySearch[1]))
                elif os.path.isfile(os.path.join(categorySearch[0], categorySearch[1])): # Our inputdirectory is actually the full file path for single file download.
                    Logger.info("SEARCH: %s is a file, not a directory.", os.path.join(categorySearch[0], categorySearch[1]))
                    Logger.info("SEARCH: Setting input directory to %s", categorySearch[0])
                    root = 1
                    inputDirectory = os.path.normpath(categorySearch[0])
                else: # The inputdirectory given can't have been valid. Start at the category directory and search for date modified.
                    Logger.info("SEARCH: Input Directory %s doesn't exist as a directory or file", inputDirectory)
                    Logger.info("SEARCH: Setting input directory to %s and checking for files by date modified.", categorySearch[0])
                    root = 2
                    inputDirectory = os.path.normpath(categorySearch[0])
                break  # we are done
            elif ('.cp(tt' in categorySearch[1]) and (not '.cp(tt' in inputName):  # if the directory was created by CouchPotato, and this tag is not in Torrent name, we want to add it.
                Logger.info("SEARCH: Changing Torrent Name to %s to preserve imdb id.", categorySearch[1])
                inputName = categorySearch[1]
                break  # we are done
            elif inputName and os.path.isdir(os.path.join(categorySearch[0], inputName)):  # testing for torrent name in first sub directory
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], inputName), categorySearch[0])
                if categorySearch[0] == os.path.normpath(inputDirectory):  # only true on first pass, x =0
                    inputDirectory = os.path.join(categorySearch[0], inputName)  # we only want to search this next dir up.
                break  # we are done
            elif inputName and os.path.isdir(os.path.join(categorySearch[0], safeName(inputName))):  # testing for torrent name in first sub directory
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], safeName(inputName)), categorySearch[0])
                if categorySearch[0] == os.path.normpath(inputDirectory):  # only true on first pass, x =0
                    inputDirectory = os.path.join(categorySearch[0], safeName(inputName))  # we only want to search this next dir up.
                break  # we are done
            elif inputName and os.path.isfile(os.path.join(categorySearch[0], inputName)) or os.path.isfile(os.path.join(categorySearch[0], safeName(inputName))):  # testing for torrent name name as file inside category directory
                Logger.info("SEARCH: Found torrent file %s in category directory %s", os.path.join(categorySearch[0], safeName(inputName)), categorySearch[0])
                root = 1
                inputDirectory = os.path.normpath(categorySearch[0])
                break  # we are done
            elif inputName:  # if these exists, we are ok to proceed, but we are in a root/common directory.
                Logger.info("SEARCH: Could not find a unique torrent folder in the directory structure")
                Logger.info("SEARCH: The directory passed is the root directory for category %s", categorySearch2[1])
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 1
                break  # we are done
            else:  # this is a problem! if we don't have Torrent name and are in the root category dir, we can't proceed.
                Logger.warn("SEARCH: Could not identify a torrent name and the directory passed is common to all downloads for category %s.", categorySearch[1])
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 2
                break
        elif inputName and safeName(categorySearch2[1]) == safeName(inputName) and os.path.isdir(categorySearch[0]):  # we have identified a unique directory.
            Logger.info("SEARCH: Files appear to be in their own directory")
            unique = int(1)
            if inputCategory:  # we are ok to proceed.
                break  # we are done
            else:
                Logger.debug("SEARCH: Continuing scan to determin category.")
                categorySearch = categorySearch2  # ready for next loop
                continue  # keep going
        else:
            if x == 9:  # This is the last pass in the loop and we didn't find anything.
                notfound = 1
                break    # we are done
            else:
                categorySearch = categorySearch2  # ready for next loop
                continue   # keep going

    if notfound == 1 and not unique == int(1):
        if inputCategory and inputName:  # if these exists, we are ok to proceed, but assume we are in a root/common directory.
            Logger.info("SEARCH: Could not find a category in the directory structure")
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 1
        elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
            Logger.info("SEARCH: Could not find a torrent name or category in the directory structure")
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 2
        elif inputName:  # we didn't find category after 10 loops. This is a problem.
            Logger.info("SEARCH: Could not find a category in the directory structure")
            Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
            root = 1
        else:  # we didn't find this after 10 loops. This is a problem.
            Logger.info("SEARCH: Could not identify category or torrent name from the directory structure.")
            Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
            root = 2

    return inputDirectory, inputName, inputCategory, root


def is_sample(filePath, inputName, minSampleSize, SampleIDs):
    # 200 MB in bytes
    SIZE_CUTOFF = minSampleSize * 1024 * 1024
    if os.path.getsize(filePath) < SIZE_CUTOFF:
        if 'SizeOnly' in SampleIDs:
            return True
        # Ignore 'sample' in files unless 'sample' in Torrent Name
        for ident in SampleIDs:
            if ident.lower() in filePath.lower() and not ident.lower() in inputName.lower(): 
                return True
    # Return False if none of these were met.
    return False


def copy_link(filePath, targetDirectory, useLink, outputDestination):
    if os.path.isfile(targetDirectory):
        Logger.info("COPYLINK: target file already exists. Nothing to be done")
        return True

    create_destination(outputDestination)
    if useLink == "hard":
        try:
            Logger.info("COPYLINK: Hard linking %s to %s", filePath, targetDirectory)
            linktastic.link(filePath, targetDirectory)
        except:
            Logger.exception("COPYLINK")
            if os.path.isfile(targetDirectory):
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, copying instead")
                Logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "sym":
        try:
            Logger.info("COPYLINK: Moving %s to %s before sym linking", filePath, targetDirectory)
            shutil.move(filePath, targetDirectory)
            Logger.info("COPYLINK: Sym linking %s to %s", targetDirectory, filePath)
            linktastic.symlink(targetDirectory, filePath)
        except:
            Logger.exception("COPYLINK")
            if os.path.isfile(targetDirectory):
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                Logger.info("COPYLINK: Something went wrong in linktastic.link, copying instead")
                Logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "move":
        Logger.debug("Moving %s to %s", filePath, targetDirectory)
        shutil.move(filePath, targetDirectory)
    else:
        Logger.debug("Copying %s to %s", filePath, targetDirectory)
        shutil.copy(filePath, targetDirectory)
    return True


def flatten(outputDestination):
    Logger.info("FLATTEN: Flattening directory: %s", outputDestination)
    for dirpath, dirnames, filenames in os.walk(outputDestination):  # Flatten out the directory to make postprocessing easier
        if dirpath == outputDestination:
            continue  # No need to try and move files in the root destination directory
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            target = os.path.join(outputDestination, filename)
            try:
                shutil.move(source, target)
            except:
                Logger.exception("FLATTEN: Could not flatten %s", source)
    removeEmptyFolders(outputDestination)  # Cleanup empty directories


def removeEmptyFolders(path):
    Logger.info("REMOVER: Removing empty folders in: %s", path)
    if not os.path.isdir(path):
        return

    # Remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                removeEmptyFolders(fullpath)

    # If folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0:
        Logger.debug("REMOVER: Removing empty folder: %s", path)
        os.rmdir(path)

def iterate_media_files(dirname):
    mediaContainer = [ '.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv',
        '.mp4', '.mpg', '.mpeg', '.iso' ]

    for dirpath, dirnames, filesnames in os.walk(dirname):
        for filename in filesnames:
            fileExtension = os.path.splitext(filename)[1]
            if not (fileExtension in mediaContainer):
                continue
            yield dirpath, os.path.join(dirpath, filename)


#Wake function
def WakeOnLan(ethernet_address):

    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
    int(addr_byte[1], 16),
    int(addr_byte[2], 16),
    int(addr_byte[3], 16),
    int(addr_byte[4], 16),
    int(addr_byte[5], 16))

    # Build the Wake-On-LAN "Magic Packet"...

    msg = '\xff' * 6 + hw_addr * 16

    # ...and send it to the broadcast address using UDP

    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()


#Test Connection function
def TestCon(host, port):
    try:
        socket.create_connection((host, port))
        return "Up"
    except:
        return "Down"


def WakeUp():
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return

    config.read(configFilename)
    wake = int(config.get("WakeOnLan", "wake"))
    if wake == 0: # just return if we don't need to wake anything.
        return
    Logger.info("Loading WakeOnLan config from %s", configFilename)
    config.get("WakeOnLan", "host")
    host = config.get("WakeOnLan", "host")
    port = int(config.get("WakeOnLan", "port"))
    mac = config.get("WakeOnLan", "mac")

    i=1
    while TestCon(host, port) == "Down" and i < 4:
        Logger.info("Sending WakeOnLan Magic Packet for mac: %s", mac)
        WakeOnLan(mac)
        time.sleep(20)
        i=i+1

    if TestCon(host,port) == "Down": # final check.
        Logger.warning("System with mac: %s has not woken after 3 attempts. Continuing with the rest of the script.", mac)
    else:
        Logger.info("System with mac: %s has been woken. Continuing with the rest of the script.", mac)

def converto_to_ascii(nzbName, dirName):
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return nzbName, dirName
    config.read(configFilename)
    ascii_convert = int(config.get("ASCII", "convert"))
    if ascii_convert == 0 or os.name == 'nt': # just return if we don't want to convert or on windows os and "\" is replaced!.
        return nzbName, dirName
    
    nzbName2 = str(nzbName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    dirName2 = str(dirName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    if dirName != dirName2:
        Logger.info("Renaming directory:%s  to: %s.", dirName, dirName2)
        shutil.move(dirName, dirName2)
    for dirpath, dirnames, filesnames in os.walk(dirName2):
        for filename in filesnames:
            filename2 = str(filename.decode('ascii', 'replace').replace(u'\ufffd', '_'))
            if filename != filename2:
                Logger.info("Renaming file:%s  to: %s.", filename, filename2)
                shutil.move(filename, filename2)
    nzbName = nzbName2
    dirName = dirName2
    return nzbName, dirName

def parse_other(args):
    return os.path.normpath(args[1]), '', '', '', ''

def parse_rtorrent(args):
    # rtorrent usage: system.method.set_key = event.download.finished,TorrentToMedia,
    # "execute={/path/to/nzbToMedia/TorrentToMedia.py,\"$d.get_base_path=\",\"$d.get_name=\",\"$d.get_custom1=\",\"$d.get_hash=\"}"
    inputDirectory = os.path.normpath(args[1])
    try:
        inputName = args[2]
    except:
        inputName = ''
    try:
        inputCategory = args[3]
    except:
        inputCategory = ''
    try:
        inputHash = args[4]
    except:
        inputHash = ''
    try:
        inputID = args[4]
    except:
        inputID = ''

    return inputDirectory, inputName, inputCategory, inputHash, inputID

def parse_utorrent(args):
    # uTorrent usage: call TorrentToMedia.py "%D" "%N" "%L" "%I"
    inputDirectory = os.path.normpath(args[1])
    inputName = args[2]
    try:
        inputCategory = args[3]
    except:
        inputCategory = ''
    try:
        inputHash = args[4]
    except:
        inputHash = ''
    try:
        inputID = args[4]
    except:
        inputID = ''

    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    inputDirectory = os.path.normpath(sys.argv[3])
    inputName = sys.argv[2]
    inputCategory = ''  # We dont have a category yet
    inputHash = sys.argv[1]
    inputID = sys.argv[1]
    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    inputName = os.getenv('TR_TORRENT_NAME')
    inputCategory = ''  # We dont have a category yet
    inputHash = os.getenv('TR_TORRENT_HASH')
    inputID = os.getenv('TR_TORRENT_ID')
    return inputDirectory, inputName, inputCategory, inputHash, inputID


__ARG_PARSERS__ = {
    'other': parse_other,
    'rtorrent': parse_rtorrent,
    'utorrent': parse_utorrent,
    'deluge': parse_deluge,
    'transmission': parse_transmission,
}


def parse_args(clientAgent):
    parseFunc = __ARG_PARSERS__.get(clientAgent, None)
    if not parseFunc:
        raise RuntimeError("Could not find client-agent")
    return parseFunc(sys.argv)

########NEW FILE########
__FILENAME__ = Transcoder
import sys
import os
import ConfigParser
import logging
import errno
from subprocess import call

Logger = logging.getLogger()

def Transcode_directory(dirName):
    
    if os.name == 'nt':
        ffmpeg = os.path.join(os.path.dirname(sys.argv[0]), 'ffmpeg\\bin\\ffmpeg.exe') # note, will need to package in this dir.
        useNiceness = False
        if not os.path.isfile(ffmpeg): # problem
            Logger.error("ffmpeg not found. ffmpeg needs to be located at: %s", ffmpeg) 
            Logger.info("Cannot transcode files in folder %s", dirName)
            return 1 # failure
    else:
        if call(['which', 'ffmpeg']) != 0:
            res = call([os.path.join(os.path.dirname(sys.argv[0]),'getffmpeg.sh')])
            if res or call(['which', 'ffmpeg']) != 0: # did not install or ffmpeg still not found.
                Logger.error("Failed to install ffmpeg. Please install manually") 
                Logger.info("Cannot transcode files in folder %s", dirName)
                return 1 # failure
            else:
                ffmpeg = 'ffmpeg'
        else:
            ffmpeg = 'ffmpeg'
        useNiceness = True
    
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)
    
    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')
    duplicate = int(config.get("Transcoder", "duplicate"))
    ignoreExtensions = (config.get("Transcoder", "ignoreExtensions")).split(',')
    outputVideoExtension = config.get("Transcoder", "outputVideoExtension").strip()
    outputVideoCodec = config.get("Transcoder", "outputVideoCodec").strip()
    outputVideoPreset = config.get("Transcoder", "outputVideoPreset").strip()
    outputVideoFramerate = config.get("Transcoder", "outputVideoFramerate").strip()
    outputVideoBitrate = config.get("Transcoder", "outputVideoBitrate").strip()
    outputAudioCodec = config.get("Transcoder", "outputAudioCodec").strip()
    outputAudioBitrate = config.get("Transcoder", "outputAudioBitrate").strip()
    outputSubtitleCodec = config.get("Transcoder", "outputSubtitleCodec").strip()
    outputFastStart = int(config.get("Transcoder", "outputFastStart"))
    outputQualityPercent = int(config.get("Transcoder", "outputQualityPercent"))
    if useNiceness:
        niceness = int(config.get("Transcoder", "niceness"))

    map(lambda ext: ext.strip(), mediaContainer)
    map(lambda ext: ext.strip(), ignoreExtensions)
    
    Logger.info("Checking for files to be transcoded")
    final_result = 0 # initialize as successful
    for dirpath, dirnames, filenames in os.walk(dirName):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            name, ext = os.path.splitext(filePath)
            if ext in mediaContainer:  # If the file is a video file
                if ext in ignoreExtensions:
                    Logger.info("No need to transcode video type %s", ext)
                    continue
                if ext == outputVideoExtension: # we need to change the name to prevent overwriting itself.
                    outputVideoExtension = '-transcoded' + outputVideoExtension # adds '-transcoded.ext'
                newfilePath = os.path.normpath(name + outputVideoExtension)

                command = [ffmpeg, '-loglevel', 'warning', '-i', filePath, '-map', '0'] # -map 0 takes all input streams

                if useNiceness:
                    command = ['nice', '-%d' % niceness] + command

                if len(outputVideoCodec) > 0:
                    command.append('-c:v')
                    command.append(outputVideoCodec)
                    if outputVideoCodec == 'libx264' and outputVideoPreset:
                        command.append('-preset')
                        command.append(outputVideoPreset)
                else:
                    command.append('-c:v')
                    command.append('copy')
                if len(outputVideoFramerate) > 0:
                    command.append('-r')
                    command.append(str(outputVideoFramerate))
                if len(outputVideoBitrate) > 0:
                    command.append('-b:v')
                    command.append(str(outputVideoBitrate))
                if len(outputAudioCodec) > 0:
                    command.append('-c:a')
                    command.append(outputAudioCodec)
                    if outputAudioCodec == 'aac': # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                        command.append('-strict')
                        command.append('-2')
                else:
                    command.append('-c:a')
                    command.append('copy')
                if len(outputAudioBitrate) > 0:
                    command.append('-b:a')
                    command.append(str(outputAudioBitrate))
                if outputFastStart > 0:
                    command.append('-movflags')
                    command.append('+faststart')
                if outputQualityPercent > 0:
                    command.append('-q:a')
                    command.append(str(outputQualityPercent))
                if len(outputSubtitleCodec) > 0: # Not every subtitle codec can be used for every video container format!
                    command.append('-c:s')
                    command.append(outputSubtitleCodec) # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
                else:
                    command.append('-sn')  # Don't copy the subtitles over
                command.append(newfilePath)
                
                try: # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
                    os.remove(newfilePath)
                except OSError, e:
                    if e.errno != errno.ENOENT: # Ignore the error if it's just telling us that the file doesn't exist
                        Logger.debug("Error when removing transcoding target: %s", e)
                except Exception, e:
                    Logger.debug("Error when removing transcoding target: %s", e)

                Logger.info("Transcoding video: %s", file)
                cmd = ""
                for item in command:
                    cmd = cmd + " " + item
                Logger.debug("calling command:%s", cmd)
                result = 1 # set result to failed in case call fails.
                try:
                    result = call(command)
                except:
                    Logger.exception("Transcoding of video %s has failed", filePath)
                if result == 0:
                    Logger.info("Transcoding of video %s to %s succeeded", filePath, newfilePath)
                    if duplicate == 0: # we get rid of the original file
                        os.unlink(filePath)
                else:
                    Logger.error("Transcoding of video %s to %s failed", filePath, newfilePath)
                # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
                final_result = final_result + result 
    return final_result

########NEW FILE########
__FILENAME__ = DeleteSamples
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Delete ".sample" files.
#
# This script removed sample files from the download directory.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

# Media Extensions
#
# This is a list of media extensions that may be deleted if a Sample_id is in the filename.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

# maxSampleSize
#
# This is the maximum size (in MiB) to be be considered as sample file.
#maxSampleSize=200

# SampleIDs
#
# This is a list of identifiers used for samples. e.g sample,-s. Use 'SizeOnly' to delete all media files less than maxSampleSize.
#SampleIDs=sample,-s. 

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys


def is_sample(filePath, inputName, maxSampleSize, SampleIDs):
    # 200 MB in bytes
    SIZE_CUTOFF = int(maxSampleSize) * 1024 * 1024
    if os.path.getsize(filePath) < SIZE_CUTOFF:
        if 'SizeOnly' in SampleIDs:
            return True
        # Ignore 'sample' in files unless 'sample' in Torrent Name
        for ident in SampleIDs:
            if ident.lower() in filePath.lower() and not ident.lower() in inputName.lower(): 
                return True
    # Return False if none of these were met.
    return False


# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "Script triggered from NZBGet (11.0 or later)."

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        print "Please enable option \"Unpack\" in nzbget configuration file, exiting."
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        print "Par-check successful, but Par-repair disabled, exiting."
        print "Please check your Par-repair settings for future downloads."
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print "Par-repair failed, setting status \"failed\"."
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "Unpack failed, setting status \"failed\"."
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            print "Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"."
            print "Please check your Par-check/repair settings for future downloads."
            status = 1

        else:
            print "Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful."
            print "Please check your Par-check/repair settings for future downloads."

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        print "Nothing to post-process: destination directory", os.environ['NZBPP_DIRECTORY'], "doesn't exist. Setting status \"failed\"."
        status = 1

    # All checks done, now launching the script.

    if status == 1:
        sys.exit(POSTPROCESS_NONE)

    mediaContainer = os.environ['NZBPO_MEDIAEXTENSIONS'].split(',')
    SampleIDs = os.environ['NZBPO_SAMPLEIDS'].split(',')
    for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, os.environ['NZBPP_NZBNAME'], os.environ['NZBPO_MAXSAMPLESIZE'], SampleIDs):  # Ignore samples
                    print "Deleting sample file: ", filePath
                    try:
                        os.unlink(filePath)
                    except:
                        print "Error: unable to delete file", filePath
                        sys.exit(POSTPROCESS_ERROR)
    sys.exit(POSTPROCESS_SUCCESS)

else:
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)

########NEW FILE########
__FILENAME__ = extractor
import os
import sys
import ConfigParser
sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]),'autoProcess/'))
import logging
from subprocess import call, Popen, PIPE
from autoProcess.nzbToMediaUtil import create_destination


Logger = logging.getLogger()

# which() and os_platform() breaks when running in Transmission (has to do with os.environ)

def os_platform():
    # Author Credit: Matthew Scouten @ http://stackoverflow.com/a/7260315
    true_platform = os.environ['PROCESSOR_ARCHITECTURE']
    try:
            true_platform = os.environ["PROCESSOR_ARCHITEW6432"]
    except KeyError:
            pass
            #true_platform not assigned to if this does not exist
    return true_platform

def which(program):
    # Author Credit: Jay @ http://stackoverflow.com/a/377028
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def extract(filePath, outputDestination):
    # Using Windows
    if os.name == 'nt':
        if os_platform() == 'AMD64':
            platform = 'x64'
        else:
            platform = 'x86'
        if not os.path.dirname(sys.argv[0]):
            chplocation = os.path.normpath(os.path.join(os.getcwd(), 'extractor/bin/chp.exe'))
            sevenzipLocation = os.path.normpath(os.path.join(os.getcwd(), 'extractor/bin/' + platform + '/7z.exe'))
        else:
            chplocation = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), 'extractor/bin/chp.exe'))
            sevenzipLocation = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), 'extractor/bin/' + platform + '/7z.exe'))
        if not os.path.exists(sevenzipLocation):
            Logger.error("EXTRACTOR: Could not find 7-zip, Exiting")
            return False
        else:
            if not os.path.exists(chplocation):
                cmd_7zip = [sevenzipLocation, "x", "-y"]
            else:
                cmd_7zip = [chplocation, sevenzipLocation, "x", "-y"]
            ext_7zip = [".rar",".zip",".tar.gz","tgz",".tar.bz2",".tbz",".tar.lzma",".tlz",".7z",".xz"]
            EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds=["unrar", "unzip", "tar", "unxz", "unlzma", "7zr", "bunzip2"]
        ## Possible future suport:
        # gunzip: gz (cmd will delete original archive)
        ## the following do not extract to dest dir
        # ".xz": ["xz", "-d --keep"],
        # ".lzma": ["xz", "-d --format=lzma --keep"],
        # ".bz2": ["bzip2", "-d --keep"],

        EXTRACT_COMMANDS = {
            ".rar": ["unrar", "x", "-o+", "-y"],
            ".tar": ["tar", "-xf"],
            ".zip": ["unzip"],
            ".tar.gz": ["tar", "-xzf"], ".tgz": ["tar", "-xzf"],
            ".tar.bz2": ["tar", "-xjf"], ".tbz": ["tar", "-xjf"],
            ".tar.lzma": ["tar", "--lzma", "-xf"], ".tlz": ["tar", "--lzma", "-xf"],
            ".tar.xz": ["tar", "--xz", "-xf"], ".txz": ["tar", "--xz", "-xf"],
            ".7z": ["7zr", "x"],
            }
        # Test command exists and if not, remove
        if not os.getenv('TR_TORRENT_DIR'):
            for cmd in required_cmds:
                if call(['which', cmd]): #note, returns 0 if exists, or 1 if doesn't exist.
                    for k, v in EXTRACT_COMMANDS.items():
                        if cmd in v[0]:
                            Logger.error("EXTRACTOR: %s not found, disabling support for %s", cmd, k)
                            del EXTRACT_COMMANDS[k]
        else:
            Logger.warn("EXTRACTOR: Cannot determine which tool to use when called from Transmission")

        if not EXTRACT_COMMANDS:
            Logger.warn("EXTRACTOR: No archive extracting programs found, plugin will be disabled")

    ext = os.path.splitext(filePath)
    if ext[1] in (".gz", ".bz2", ".lzma"):
    # Check if this is a tar
        if os.path.splitext(ext[0])[1] == ".tar":
            cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
    elif ext[1] in (".1", ".01", ".001") and os.path.splitext(ext[0])[1] in (".rar", ".zip", ".7z"): #support for *.zip.001, *.zip.002 etc.
            cmd = EXTRACT_COMMANDS[os.path.splitext(ext[0])[1]]
    else:
        if ext[1] in EXTRACT_COMMANDS:
            cmd = EXTRACT_COMMANDS[ext[1]]
        else:
            Logger.debug("EXTRACTOR: Unknown file type: %s", ext[1])
            return False

    # Create outputDestination folder
    create_destination(outputDestination)

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("MAIN: Loading config from %s", configFilename)
    config.read(configFilename)                         
    passwordsfile = config.get("passwords", "PassWordFile")
    if passwordsfile != "" and os.path.isfile(os.path.normpath(passwordsfile)):
        passwords = [line.strip() for line in open(os.path.normpath(passwordsfile))]
    else:
        passwords = []

    Logger.info("Extracting %s to %s", filePath, outputDestination)
    Logger.debug("Extracting %s %s %s", cmd, filePath, outputDestination)
    pwd = os.getcwd() # Get our Present Working Directory
    os.chdir(outputDestination) # Not all unpack commands accept full paths, so just extract into this directory
    try: # now works same for nt and *nix
        cmd.append(filePath) # add filePath to final cmd arg.
        cmd2 = cmd
        cmd2.append("-p-") # don't prompt for password.
        p = Popen(cmd2) # should extract files fine.
        res = p.wait()
        if (res >= 0 and os.name == 'nt') or res == 0: # for windows chp returns process id if successful or -1*Error code. Linux returns 0 for successful.
            Logger.info("EXTRACTOR: Extraction was successful for %s to %s", filePath, outputDestination)
        elif len(passwords) > 0:
            Logger.info("EXTRACTOR: Attempting to extract with passwords")
            pass_success = int(0)
            for password in passwords:
                if password == "": # if edited in windows or otherwise if blank lines.
                    continue
                cmd2 = cmd
                #append password here.
                passcmd = "-p" + password
                cmd2.append(passcmd)
                p = Popen(cmd2) # should extract files fine.
                res = p.wait()
                if (res >= 0 and os.name == 'nt') or res == 0: # for windows chp returns process id if successful or -1*Error code. Linux returns 0 for successful.
                    Logger.info("EXTRACTOR: Extraction was successful for %s to %s using password: %s", filePath, outputDestination, password)
                    pass_success = int(1)
                    break
                else:
                    continue
            if pass_success == int(0):
                Logger.error("EXTRACTOR: Extraction failed for %s. 7zip result was %s", filePath, res)
    except:
        Logger.exception("EXTRACTOR: Extraction failed for %s. Could not call command %s", filePath, cmd)
    os.chdir(pwd) # Go back to our Original Working Directory
    return True

########NEW FILE########
__FILENAME__ = linktastic
# Linktastic Module
# - A python2/3 compatible module that can create hardlinks/symlinks on windows-based systems
#
# Linktastic is distributed under the MIT License.  The follow are the terms and conditions of using Linktastic.
#
# The MIT License (MIT)
#  Copyright (c) 2012 Solipsis Development
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import subprocess
from subprocess import CalledProcessError
import os


# Prevent spaces from messing with us!
def _escape_param(param):
	return '"%s"' % param


# Private function to create link on nt-based systems
def _link_windows(src, dest):
	try:
		subprocess.check_output(
			'cmd /C mklink /H %s %s' % (_escape_param(dest), _escape_param(src)),
			stderr=subprocess.STDOUT)
	except CalledProcessError as err:

		raise IOError(err.output.decode('utf-8'))

	# TODO, find out what kind of messages Windows sends us from mklink
	# print(stdout)
	# assume if they ret-coded 0 we're good


def _symlink_windows(src, dest):
	try:
		subprocess.check_output(
			'cmd /C mklink %s %s' % (_escape_param(dest), _escape_param(src)),
			stderr=subprocess.STDOUT)
	except CalledProcessError as err:
		raise IOError(err.output.decode('utf-8'))

	# TODO, find out what kind of messages Windows sends us from mklink
	# print(stdout)
	# assume if they ret-coded 0 we're good


# Create a hard link to src named as dest
# This version of link, unlike os.link, supports nt systems as well
def link(src, dest):
	if os.name == 'nt':
		_link_windows(src, dest)
	else:
		os.link(src, dest)


# Create a symlink to src named as dest, but don't fail if you're on nt
def symlink(src, dest):
	if os.name == 'nt':
		_symlink_windows(src, dest)
	else:
		os.symlink(src, dest)

########NEW FILE########
__FILENAME__ = nzbToCouchPotato
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## CouchPotato

# CouchPotato script category.
#
# category that gets called for post-processing with CouchPotatoServer.
#cpsCategory=movie

# CouchPotato api key.
#cpsapikey=

# CouchPotato host.
#cpshost=localhost

# CouchPotato port.
#cpsport=5050

# CouchPotato uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#cpsssl=0

# CouchPotato URL_Base
#
# set this if using a reverse proxy.
#cpsweb_root=

# CouchPotato Postprocess Delay.
#
# must be at least 60 seconds.
#cpsdelay=65

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

# CouchPotato wait_for
#
# Set the number of minutes to wait before timing out. If transfering files across drives or network, increase this to longer than the time it takes to copy a movie.
#cpswait_for=5

# CouchPotatoServer and NZBGet are a different system (0, 1).
#
# set to 1 if CouchPotato and NZBGet are on a different system, or 0 if on the same system.
#remoteCPS = 0

## Extensions

# Media Extensions
#
# This is a list of media extensions that may be transcoded if transcoder is enabled below.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

## Transcoder

# Transcode (0, 1).
#
# set to 1 to transcode, otherwise set to 0.
#transcode=0

# create a duplicate, or replace the original (0, 1).
#
# set to 1 to cretae a new file or 0 to replace the original
#duplicate=1

# ignore extensions
#
# list of extensions that won't be transcoded. 
#ignoreExtensions=.avi,.mkv

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=libmp3lame
#outputAudioBitrate=128k
#outputSubtitleCodec=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessMovie as autoProcessMovie
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToCouchPotato %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    download_id = ""
    if os.environ.has_key('NZBPR_COUCHPOTATO'):
        download_id = os.environ['NZBPR_COUCHPOTATO']
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessMovie...")
    result = autoProcessMovie.process(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status, clientAgent, download_id)
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessMovie...")
    clientAgent = "sabnzbd"
    result = autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent)
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessMovie...")
    clientAgent = "sabnzbd"
    result = autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent)
else:
    Logger.warn("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessMovie as a manual run...")
    clientAgent = "manual"
    result = autoProcessMovie.process('Manual Run', 'Manual Run', 0, clientAgent)

if result == 0:
    Logger.info("MAIN: The autoProcessMovie script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessMovie script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)

########NEW FILE########
__FILENAME__ = nzbToGamez
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Gamez.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## Gamez

# Gamez script category.
#
# category that gets called for post-processing with Gamez.
#gzCategory=games

# Gamez api key.
#gzapikey=

# Gamez host.
#gzhost=localhost

# Gamez port.
#gzport=8085

# Gamez uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#gzssl=0

# Gamez web_root.
#
# set this if using a reverse proxy.
#gzweb_root=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessGames as autoProcessGames
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToGamez %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessGames...")
    result = autoProcessGames.process(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status)
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessGames...")
    result = autoProcessGames.process(sys.argv[1], sys.argv[3], sys.argv[7])
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessGames...")
    result = autoProcessGames.process(sys.argv[1], sys.argv[3], sys.argv[7])
else:
    Logger.warn("MAIN: Invalid number of arguments received from client. Exiting")
    sys.exit(1)

if result == 0:
    Logger.info("MAIN: The autoProcessGames script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessGames script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)

########NEW FILE########
__FILENAME__ = nzbToHeadPhones
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to HeadPhones.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## HeadPhones

# HeadPhones script category.
#
# category that gets called for post-processing with HeadHones.
#hpCategory=music

# HeadPhones api key.
#hpapikey=

# HeadPhones host.
#hphost=localhost

# HeadPhones port.
#hpport=8181

# HeadPhones uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#hpssl=0

# HeadPhones web_root
#
# set this if using a reverse proxy.
#hpweb_root=

# HeadPhones Postprocess Delay.
#
# set as required to ensure correct processing.
#hpdelay=65

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessMusic as autoProcessMusic
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToHeadPhones %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessMusic...")
    result = autoProcessMusic.process(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status)
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessMusic...")
    result = autoProcessMusic.process(sys.argv[1], sys.argv[2], sys.argv[7])
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failue URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessMusic...")
    result = autoProcessMusic.process(sys.argv[1], sys.argv[2], sys.argv[7])
else:
    Logger.warn("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessMusic as a manual run...")
    result = autoProcessMusic.process('Manual Run', 'Manual Run', 0)

if result == 0:
    Logger.info("MAIN: The autoProcessMusic script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessMusic script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)

########NEW FILE########
__FILENAME__ = nzbToMedia
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato, SickBeard, Mylar, Gamez, HeadPhones.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## CouchPotato

# CouchPotato script category.
#
# category that gets called for post-processing with CouchPotatoServer.
#cpsCategory=movie

# CouchPotato api key.
#cpsapikey=

# CouchPotato host.
#cpshost=localhost

# CouchPotato port.
#cpsport=5050

# CouchPotato uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#cpsssl=0

# CouchPotato URL_Base
#
# set this if using a reverse proxy.
#cpsweb_root=

# CouchPotato Postprocess Delay.
#
# must be at least 60 seconds.
#cpsdelay=65

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

# CouchPotato wait_for
#
# Set the number of minutes to wait before timing out. If transfering files across drives or network, increase this to longer than the time it takes to copy a movie.
#cpswait_for=5

# CouchPotatoServer and NZBGet are a different system (0, 1).
#
# set to 1 if CouchPotato and NZBGet are on a different system, or 0 if on the same system.
#remoteCPS = 0

## SickBeard

# SickBeard script category.
#
# category that gets called for post-processing with SickBeard.
#sbCategory=tv

# SickBeard host.
#sbhost=localhost

# SickBeard port.
#sbport=8081

# SickBeard username.
#sbusername= 

# SickBeard password.
#sbpassword=

# SickBeard uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#sbssl=0

# SickBeard web_root
#
# set this if using a reverse proxy.
#sbweb_root=

# SickBeard delay
#
# Set the number of seconds to wait before calling post-process in SickBeard.
#sbdelay=0

# SickBeard wait_for
#
# Set the number of minutes to wait before timing out. If transferring files across drives or network, increase this to longer than the time it takes to copy an episode.
#sbwait_for=5

# SickBeard watch directory.
#
# set this if SickBeard and nzbGet are on different systems.
#sbwatch_dir=

# SickBeard fork.
#
# set to default or TPB or failed if using the custom "TPB" or "failed fork".
#sbfork=default

# SickBeard Delete Failed Downloads (0, 1)
#
# set to 1 to delete failed, or 0 to leave files in place.
#sbdelete_failed=0

## HeadPhones

# HeadPhones script category.
#
# category that gets called for post-processing with HeadHones.
#hpCategory=music

# HeadPhones api key.
#hpapikey=

# HeadPhones host.
#hphost=localhost

# HeadPhones port.
#hpport=8181

# HeadPhones uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#hpssl=0

# HeadPhones web_root
#
# set this if using a reverse proxy.
#hpweb_root=

# HeadPhones Postprocess Delay.
#
# set as required to ensure correct processing.
#hpdelay=65

## Mylar

# Mylar script category.
#
# category that gets called for post-processing with Mylar.
#myCategory=comics

# Mylar host.
#myhost=localhost

# Mylar port.
#myport=8090

# Mylar username.
#myusername= 

# Mylar password.
#mypassword=

# Mylar uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#myssl=0

# Mylar web_root
#
# set this if using a reverse proxy.
#myweb_root=

## Gamez

# Gamez script category.
#
# category that gets called for post-processing with Gamez.
#gzCategory=games

# Gamez api key.
#gzapikey=

# Gamez host.
#gzhost=localhost

# Gamez port.
#gzport=8085

# Gamez uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#gzssl=0

# Gamez web_root
#
# set this if using a reverse proxy.
#gzweb_root=

## Extensions

# Media Extensions
#
# This is a list of media extensions that may be transcoded if transcoder is enabled below.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

## Transcoder

# Transcode (0, 1).
#
# set to 1 to transcode, otherwise set to 0.
#transcode=0

# create a duplicate, or replace the original (0, 1).
#
# set to 1 to cretae a new file or 0 to replace the original
#duplicate=1

# ignore extensions
#
# list of extensions that won't be transcoded. 
#ignoreExtensions=.avi,.mkv

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=libmp3lame
#outputAudioBitrate=128k
#outputSubtitleCodec=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import ConfigParser
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessComics as autoProcessComics
import autoProcess.autoProcessGames as autoProcessGames
import autoProcess.autoProcessMusic as autoProcessMusic
import autoProcess.autoProcessTV as autoProcessTV
import autoProcess.autoProcessMovie as autoProcessMovie
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

# check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToMedia %s", VERSION)

WakeUp()

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
if not os.path.isfile(configFilename):
    Logger.error("MAIN: You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
    sys.exit(-1)
# CONFIG FILE
Logger.info("MAIN: Loading config from %s", configFilename)
config.read(configFilename)

cpsCategory = (config.get("CouchPotato", "cpsCategory")).split(',')                 # movie
sbCategory = (config.get("SickBeard", "sbCategory")).split(',')                     # tv
hpCategory = (config.get("HeadPhones", "hpCategory")).split(',')                    # music
mlCategory = (config.get("Mylar", "mlCategory")).split(',')                         # comics
gzCategory = (config.get("Gamez", "gzCategory")).split(',')                         # games

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    download_id = ""
    if os.environ.has_key('NZBPR_COUCHPOTATO'):
        download_id = os.environ['NZBPR_COUCHPOTATO']
    nzbDir, inputName, inputCategory = (os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBFILENAME'], os.environ['NZBPP_CATEGORY'])
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd")
    clientAgent = "sabnzbd"
    nzbDir, inputName, status, inputCategory, download_id = (sys.argv[1], sys.argv[2], sys.argv[7], sys.argv[5], '')
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+")
    clientAgent = "sabnzbd"
    nzbDir, inputName, status, inputCategory, download_id = (sys.argv[1], sys.argv[2], sys.argv[7], sys.argv[5], '')
else: # only CPS supports this manual run for now.
    Logger.warn("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessMovie as a manual run...")
    clientAgent = "manual"
    nzbDir, inputName, status, inputCategory, download_id = ('Manual Run', 'Manual Run', 0, cpsCategory[0], '')

if inputCategory in cpsCategory:
    Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
    result = autoProcessMovie.process(nzbDir, inputName, status, clientAgent, download_id, inputCategory)
elif inputCategory in sbCategory:
    Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
    result = autoProcessTV.processEpisode(nzbDir, inputName, status, clientAgent, inputCategory)
elif inputCategory in hpCategory:
    Logger.info("MAIN: Calling HeadPhones to post-process: %s", inputName)
    result = autoProcessMusic.process(nzbDir, inputName, status, inputCategory)
elif inputCategory in mlCategory:
    Logger.info("MAIN: Calling Mylar to post-process: %s", inputName)
    result = autoProcessComics.processEpisode(nzbDir, inputName, status, inputCategory)
elif inputCategory in gzCategory:
    Logger.info("MAIN: Calling Gamez to post-process: %s", inputName)
    result = autoProcessGames.process(nzbDir, inputName, status, inputCategory)
else:
    Logger.warning("MAIN: The download category %s does not match any category defined in autoProcessMedia.cfg. Exiting.", inputCategory)
    sys.exit(POSTPROCESS_ERROR)

if result == 0:
    Logger.info("MAIN: The autoProcess* script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcess* script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)
########NEW FILE########
__FILENAME__ = nzbToMylar
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Mylar.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## Mylar

# Mylar script category.
#
# category that gets called for post-processing with Mylar.
#myCategory=comics

# Mylar host.
#myhost=localhost

# Mylar port.
#myport=8090

# Mylar username.
#myusername= 

# Mylar password.
#mypassword=

# Mylar uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#myssl=0

# Mylar web_root
#
# set this if using a reverse proxy.
#myweb_root=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessComics as autoProcessComics
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToMylar %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessComics...")
    result = autoProcessComics.processEpisode(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status)
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessComics...")
    result = autoProcessComics.processEpisode(sys.argv[1], sys.argv[3], sys.argv[7])
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessComics...")
    result = autoProcessComics.processEpisode(sys.argv[1], sys.argv[3], sys.argv[7])
else:
    Logger.warn("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessComics as a manual run...")
    result = autoProcessComics.processEpisode('Manual Run', 'Manual Run', 0)

if result == 0:
    Logger.info("MAIN: The autoProcessComics script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessComics script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)

########NEW FILE########
__FILENAME__ = nzbToSickBeard
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to SickBeard.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## SickBeard

# SickBeard script category.
#
# category that gets called for post-processing with SickBeard.
#sbCategory=tv

# SickBeard host.
#sbhost=localhost

# SickBeard port.
#sbport=8081

# SickBeard username.
#sbusername= 

# SickBeard password.
#sbpassword=

# SickBeard uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#sbssl=0

# SickBeard web_root
#
# set this if using a reverse proxy.
#sbweb_root=

# SickBeard delay
#
# Set the number of seconds to wait before calling post-process in SickBeard.
#sbdelay=0

# SickBeard wait_for
#
# Set the number of minutes to wait before timing out. If transfering files across drives or network, increase this to longer than the time it takes to copy an episode.
#sbwait_for=5

# SickBeard watch directory.
#
# set this if SickBeard and nzbGet are on different systems.
#sbwatch_dir=

# SickBeard fork.
#
# set to default or TPB or failed if using the custom "TPB" or "failed fork".
#sbfork=default

# SickBeard Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#sbdelete_failed=0

## Extensions

# Media Extensions
#
# This is a list of media extensions that may be transcoded if transcoder is enabled below.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

## Transcoder

# Transcode (0, 1).
#
# set to 1 to transcode, otherwise set to 0.
#transcode=0

# create a duplicate, or replace the original (0, 1).
#
# set to 1 to cretae a new file or 0 to replace the original
#duplicate=1

# ignore extensions
#
# list of extensions that won't be transcoded. 
#ignoreExtensions=.avi,.mkv

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=libmp3lame
#outputAudioBitrate=128k
#outputSubtitleCodec=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessTV as autoProcessTV
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToSickBeard %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessTV...")
    clientAgent = "nzbget"
    result = autoProcessTV.processEpisode(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBFILENAME'], status, clientAgent, os.environ['NZBPP_CATEGORY'])
# SABnzbd Pre 0.7.17
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessTV...")
    clientAgent = "sabnzbd"
    result = autoProcessTV.processEpisode(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent, sys.argv[5])
# SABnzbd 0.7.17+
elif len(sys.argv) >= SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessTV...")
    clientAgent = "sabnzbd"
    result = autoProcessTV.processEpisode(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent, sys.argv[5])
else:
    Logger.debug("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessTV as a manual run...")
    result = autoProcessTV.processEpisode('Manual Run', 'Manual Run', 0)

if result == 0:
    Logger.info("MAIN: The autoProcessTV script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessTV script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)

########NEW FILE########
__FILENAME__ = ResetDateTime
#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Reset the Date Modified and Date Created for downlaoded files.
#
# This is useful for sorting "newly added" media.
# This should run before other scripts.
#
# NOTE: This script requires Python to be installed on your system.

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "Script triggered from NZBGet (11.0 or later)."

    # NZBGet argv: all passed as environment variables.
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        print "Please enable option \"Unpack\" in nzbget configuration file, exiting."
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        print "Par-check successful, but Par-repair disabled, exiting."
        print "Please check your Par-repair settings for future downloads."
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print "Par-repair failed, setting status \"failed\"."
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "Unpack failed, setting status \"failed\"."
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            print "Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"."
            print "Please check your Par-check/repair settings for future downloads."
            status = 1

        else:
            print "Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful."
            print "Please check your Par-check/repair settings for future downloads."

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        print "Nothing to post-process: destination directory", os.environ['NZBPP_DIRECTORY'], "doesn't exist. Setting status \"failed\"."
        status = 1

    # All checks done, now launching the script.

    if status == 1:
        sys.exit(POSTPROCESS_NONE)

    directory = os.path.normpath(os.environ['NZBPP_DIRECTORY'])
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            filepath = os.path.join(dirpath, file)
            print "reseting datetime for file", filepath
            try:
                os.utime(filepath, None)
                continue
            except:
                print "Error: unable to reset time for file", filePath
                sys.exit(POSTPROCESS_ERROR)
    sys.exit(POSTPROCESS_SUCCESS)

else:
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)

########NEW FILE########
__FILENAME__ = client
import os
import platform

from collections import defaultdict
from itertools import imap

from synchronousdeluge.exceptions import DelugeRPCError
from synchronousdeluge.protocol import DelugeRPCRequest, DelugeRPCResponse
from synchronousdeluge.transfer import DelugeTransfer

__all__ = ["DelugeClient"]


RPC_RESPONSE = 1
RPC_ERROR = 2
RPC_EVENT = 3


class DelugeClient(object):
    def __init__(self):
        """A deluge client session."""
        self.transfer = DelugeTransfer()
        self.modules = []
        self._request_counter = 0

    def _get_local_auth(self):
        auth_file = ""
        username = password = ""
        if platform.system() in ('Windows', 'Microsoft'):
            appDataPath = os.environ.get("APPDATA")
            if not appDataPath:
                import _winreg
                hkey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders")
                appDataReg = _winreg.QueryValueEx(hkey, "AppData")
                appDataPath = appDataReg[0]
                _winreg.CloseKey(hkey)

            auth_file = os.path.join(appDataPath, "deluge", "auth")
        else:
            from xdg.BaseDirectory import save_config_path
            try:
                auth_file = os.path.join(save_config_path("deluge"), "auth")
            except OSError, e:
                return username, password


        if os.path.exists(auth_file):
            for line in open(auth_file):
                if line.startswith("#"):
                    # This is a comment line
                    continue
                line = line.strip()
                try:
                    lsplit = line.split(":")
                except Exception, e:
                    continue

                if len(lsplit) == 2:
                    username, password = lsplit
                elif len(lsplit) == 3:
                    username, password, level = lsplit
                else:
                    continue

                if username == "localclient":
                    return (username, password)

        return ("", "")

    def _create_module_method(self, module, method):
        fullname = "{0}.{1}".format(module, method)

        def func(obj, *args, **kwargs):
            return self.remote_call(fullname, *args, **kwargs)

        func.__name__ = method

        return func

    def _introspect(self):
        self.modules = []

        methods = self.remote_call("daemon.get_method_list").get()
        methodmap = defaultdict(dict)
        splitter = lambda v: v.split(".")

        for module, method in imap(splitter, methods):
            methodmap[module][method] = self._create_module_method(module, method)

        for module, methods in methodmap.items():
            clsname = "DelugeModule{0}".format(module.capitalize())
            cls = type(clsname, (), methods)
            setattr(self, module, cls())
            self.modules.append(module)

    def remote_call(self, method, *args, **kwargs):
        req = DelugeRPCRequest(self._request_counter, method, *args, **kwargs)
        message = next(self.transfer.send_request(req))

        response = DelugeRPCResponse()

        if not isinstance(message, tuple):
            return

        if len(message) < 3:
            return

        message_type = message[0]

#        if message_type == RPC_EVENT:
#            event = message[1]
#            values = message[2]
#
#            if event in self._event_handlers:
#                for handler in self._event_handlers[event]:
#                    gevent.spawn(handler, *values)
#
#        elif message_type in (RPC_RESPONSE, RPC_ERROR):
        if message_type in (RPC_RESPONSE, RPC_ERROR):
            request_id = message[1]
            value = message[2]

            if request_id == self._request_counter :
                if message_type == RPC_RESPONSE:
                    response.set(value)
                elif message_type == RPC_ERROR:
                    err = DelugeRPCError(*value)
                    response.set_exception(err)

        self._request_counter += 1
        return response

    def connect(self, host="127.0.0.1", port=58846, username="", password=""):
        """Connects to a daemon process.

        :param host: str, the hostname of the daemon
        :param port: int, the port of the daemon
        :param username: str, the username to login with
        :param password: str, the password to login with
        """

        # Connect transport
        self.transfer.connect((host, port))

        # Attempt to fetch local auth info if needed
        if not username and host in ("127.0.0.1", "localhost"):
            username, password = self._get_local_auth()

        # Authenticate
        self.remote_call("daemon.login", username, password).get()

        # Introspect available methods
        self._introspect()

    @property
    def connected(self):
        return self.transfer.connected

    def disconnect(self):
        """Disconnects from the daemon."""
        self.transfer.disconnect()


########NEW FILE########
__FILENAME__ = exceptions
__all__ = ["DelugeRPCError"]

class DelugeRPCError(Exception):
    def __init__(self, name, msg, traceback):
        self.name = name
        self.msg = msg
        self.traceback = traceback

    def __str__(self):
        return "{0}: {1}: {2}".format(self.__class__.__name__, self.name, self.msg)


########NEW FILE########
__FILENAME__ = protocol
__all__ = ["DelugeRPCRequest", "DelugeRPCResponse"]

class DelugeRPCRequest(object):
    def __init__(self, request_id, method, *args, **kwargs):
        self.request_id = request_id
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def format(self):
        return (self.request_id, self.method, self.args, self.kwargs)

class DelugeRPCResponse(object):
    def __init__(self):
        self.value = None
        self._exception = None

    def successful(self):
        return self._exception is None

    @property
    def exception(self):
        if self._exception is not None:
            return self._exception

    def set(self, value=None):
        self.value = value
        self._exception = None

    def set_exception(self, exception):
        self._exception = exception

    def get(self):
        if self._exception is None:
            return self.value
        else:
            raise self._exception


########NEW FILE########
__FILENAME__ = rencode

"""
rencode -- Web safe object pickling/unpickling.

Public domain, Connelly Barnes 2006-2007.

The rencode module is a modified version of bencode from the
BitTorrent project.  For complex, heterogeneous data structures with
many small elements, r-encodings take up significantly less space than
b-encodings:

 >>> len(rencode.dumps({'a':0, 'b':[1,2], 'c':99}))
 13
 >>> len(bencode.bencode({'a':0, 'b':[1,2], 'c':99}))
 26

The rencode format is not standardized, and may change with different
rencode module versions, so you should check that you are using the
same rencode version throughout your project.
"""

__version__ = '1.0.1'
__all__ = ['dumps', 'loads']

# Original bencode module by Petru Paler, et al.
#
# Modifications by Connelly Barnes:
#
#  - Added support for floats (sent as 32-bit or 64-bit in network
#    order), bools, None.
#  - Allowed dict keys to be of any serializable type.
#  - Lists/tuples are always decoded as tuples (thus, tuples can be
#    used as dict keys).
#  - Embedded extra information in the 'typecodes' to save some space.
#  - Added a restriction on integer length, so that malicious hosts
#    cannot pass us large integers which take a long time to decode.
#
# Licensed by Bram Cohen under the "MIT license":
#
#  "Copyright (C) 2001-2002 Bram Cohen
#
#  Permission is hereby granted, free of charge, to any person
#  obtaining a copy of this software and associated documentation files
#  (the "Software"), to deal in the Software without restriction,
#  including without limitation the rights to use, copy, modify, merge,
#  publish, distribute, sublicense, and/or sell copies of the Software,
#  and to permit persons to whom the Software is furnished to do so,
#  subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  The Software is provided "AS IS", without warranty of any kind,
#  express or implied, including but not limited to the warranties of
#  merchantability,  fitness for a particular purpose and
#  noninfringement. In no event shall the  authors or copyright holders
#  be liable for any claim, damages or other liability, whether in an
#  action of contract, tort or otherwise, arising from, out of or in
#  connection with the Software or the use or other dealings in the
#  Software."
#
# (The rencode module is licensed under the above license as well).
#

import struct
import string
from threading import Lock

# Default number of bits for serialized floats, either 32 or 64 (also a parameter for dumps()).
DEFAULT_FLOAT_BITS = 32

# Maximum length of integer when written as base 10 string.
MAX_INT_LENGTH = 64

# The bencode 'typecodes' such as i, d, etc have been extended and
# relocated on the base-256 character set.
CHR_LIST    = chr(59)
CHR_DICT    = chr(60)
CHR_INT     = chr(61)
CHR_INT1    = chr(62)
CHR_INT2    = chr(63)
CHR_INT4    = chr(64)
CHR_INT8    = chr(65)
CHR_FLOAT32 = chr(66)
CHR_FLOAT64 = chr(44)
CHR_TRUE    = chr(67)
CHR_FALSE   = chr(68)
CHR_NONE    = chr(69)
CHR_TERM    = chr(127)

# Positive integers with value embedded in typecode.
INT_POS_FIXED_START = 0
INT_POS_FIXED_COUNT = 44

# Dictionaries with length embedded in typecode.
DICT_FIXED_START = 102
DICT_FIXED_COUNT = 25

# Negative integers with value embedded in typecode.
INT_NEG_FIXED_START = 70
INT_NEG_FIXED_COUNT = 32

# Strings with length embedded in typecode.
STR_FIXED_START = 128
STR_FIXED_COUNT = 64

# Lists with length embedded in typecode.
LIST_FIXED_START = STR_FIXED_START+STR_FIXED_COUNT
LIST_FIXED_COUNT = 64

def decode_int(x, f):
    f += 1
    newf = x.index(CHR_TERM, f)
    if newf - f >= MAX_INT_LENGTH:
        raise ValueError('overflow')
    try:
        n = int(x[f:newf])
    except (OverflowError, ValueError):
        n = long(x[f:newf])
    if x[f] == '-':
        if x[f + 1] == '0':
            raise ValueError
    elif x[f] == '0' and newf != f+1:
        raise ValueError
    return (n, newf+1)

def decode_intb(x, f):
    f += 1
    return (struct.unpack('!b', x[f:f+1])[0], f+1)

def decode_inth(x, f):
    f += 1
    return (struct.unpack('!h', x[f:f+2])[0], f+2)

def decode_intl(x, f):
    f += 1
    return (struct.unpack('!l', x[f:f+4])[0], f+4)

def decode_intq(x, f):
    f += 1
    return (struct.unpack('!q', x[f:f+8])[0], f+8)

def decode_float32(x, f):
    f += 1
    n = struct.unpack('!f', x[f:f+4])[0]
    return (n, f+4)

def decode_float64(x, f):
    f += 1
    n = struct.unpack('!d', x[f:f+8])[0]
    return (n, f+8)

def decode_string(x, f):
    colon = x.index(':', f)
    try:
        n = int(x[f:colon])
    except (OverflowError, ValueError):
        n = long(x[f:colon])
    if x[f] == '0' and colon != f+1:
        raise ValueError
    colon += 1
    s = x[colon:colon+n]
    try:
        t = s.decode("utf8")
        if len(t) != len(s):
            s = t
    except UnicodeDecodeError:
        pass
    return (s, colon+n)

def decode_list(x, f):
    r, f = [], f+1
    while x[f] != CHR_TERM:
        v, f = decode_func[x[f]](x, f)
        r.append(v)
    return (tuple(r), f + 1)

def decode_dict(x, f):
    r, f = {}, f+1
    while x[f] != CHR_TERM:
        k, f = decode_func[x[f]](x, f)
        r[k], f = decode_func[x[f]](x, f)
    return (r, f + 1)

def decode_true(x, f):
  return (True, f+1)

def decode_false(x, f):
  return (False, f+1)

def decode_none(x, f):
  return (None, f+1)

decode_func = {}
decode_func['0'] = decode_string
decode_func['1'] = decode_string
decode_func['2'] = decode_string
decode_func['3'] = decode_string
decode_func['4'] = decode_string
decode_func['5'] = decode_string
decode_func['6'] = decode_string
decode_func['7'] = decode_string
decode_func['8'] = decode_string
decode_func['9'] = decode_string
decode_func[CHR_LIST   ] = decode_list
decode_func[CHR_DICT   ] = decode_dict
decode_func[CHR_INT    ] = decode_int
decode_func[CHR_INT1   ] = decode_intb
decode_func[CHR_INT2   ] = decode_inth
decode_func[CHR_INT4   ] = decode_intl
decode_func[CHR_INT8   ] = decode_intq
decode_func[CHR_FLOAT32] = decode_float32
decode_func[CHR_FLOAT64] = decode_float64
decode_func[CHR_TRUE   ] = decode_true
decode_func[CHR_FALSE  ] = decode_false
decode_func[CHR_NONE   ] = decode_none

def make_fixed_length_string_decoders():
    def make_decoder(slen):
        def f(x, f):
            s = x[f+1:f+1+slen]
            try:
                t = s.decode("utf8")
                if len(t) != len(s):
                    s = t
            except UnicodeDecodeError:
                pass
            return (s, f+1+slen)
        return f
    for i in range(STR_FIXED_COUNT):
        decode_func[chr(STR_FIXED_START+i)] = make_decoder(i)

make_fixed_length_string_decoders()

def make_fixed_length_list_decoders():
    def make_decoder(slen):
        def f(x, f):
            r, f = [], f+1
            for i in range(slen):
                v, f = decode_func[x[f]](x, f)
                r.append(v)
            return (tuple(r), f)
        return f
    for i in range(LIST_FIXED_COUNT):
        decode_func[chr(LIST_FIXED_START+i)] = make_decoder(i)

make_fixed_length_list_decoders()

def make_fixed_length_int_decoders():
    def make_decoder(j):
        def f(x, f):
            return (j, f+1)
        return f
    for i in range(INT_POS_FIXED_COUNT):
        decode_func[chr(INT_POS_FIXED_START+i)] = make_decoder(i)
    for i in range(INT_NEG_FIXED_COUNT):
        decode_func[chr(INT_NEG_FIXED_START+i)] = make_decoder(-1-i)

make_fixed_length_int_decoders()

def make_fixed_length_dict_decoders():
    def make_decoder(slen):
        def f(x, f):
            r, f = {}, f+1
            for j in range(slen):
                k, f = decode_func[x[f]](x, f)
                r[k], f = decode_func[x[f]](x, f)
            return (r, f)
        return f
    for i in range(DICT_FIXED_COUNT):
        decode_func[chr(DICT_FIXED_START+i)] = make_decoder(i)

make_fixed_length_dict_decoders()

def encode_dict(x,r):
    r.append(CHR_DICT)
    for k, v in x.items():
        encode_func[type(k)](k, r)
        encode_func[type(v)](v, r)
    r.append(CHR_TERM)


def loads(x):
    try:
        r, l = decode_func[x[0]](x, 0)
    except (IndexError, KeyError):
        raise ValueError
    if l != len(x):
        raise ValueError
    return r

from types import StringType, IntType, LongType, DictType, ListType, TupleType, FloatType, NoneType, UnicodeType

def encode_int(x, r):
    if 0 <= x < INT_POS_FIXED_COUNT:
        r.append(chr(INT_POS_FIXED_START+x))
    elif -INT_NEG_FIXED_COUNT <= x < 0:
        r.append(chr(INT_NEG_FIXED_START-1-x))
    elif -128 <= x < 128:
        r.extend((CHR_INT1, struct.pack('!b', x)))
    elif -32768 <= x < 32768:
        r.extend((CHR_INT2, struct.pack('!h', x)))
    elif -2147483648 <= x < 2147483648:
        r.extend((CHR_INT4, struct.pack('!l', x)))
    elif -9223372036854775808 <= x < 9223372036854775808:
        r.extend((CHR_INT8, struct.pack('!q', x)))
    else:
        s = str(x)
        if len(s) >= MAX_INT_LENGTH:
            raise ValueError('overflow')
        r.extend((CHR_INT, s, CHR_TERM))

def encode_float32(x, r):
    r.extend((CHR_FLOAT32, struct.pack('!f', x)))

def encode_float64(x, r):
    r.extend((CHR_FLOAT64, struct.pack('!d', x)))

def encode_bool(x, r):
    r.extend({False: CHR_FALSE, True: CHR_TRUE}[bool(x)])

def encode_none(x, r):
    r.extend(CHR_NONE)

def encode_string(x, r):
    if len(x) < STR_FIXED_COUNT:
        r.extend((chr(STR_FIXED_START + len(x)), x))
    else:
        r.extend((str(len(x)), ':', x))

def encode_unicode(x, r):
    encode_string(x.encode("utf8"), r)

def encode_list(x, r):
    if len(x) < LIST_FIXED_COUNT:
        r.append(chr(LIST_FIXED_START + len(x)))
        for i in x:
            encode_func[type(i)](i, r)
    else:
        r.append(CHR_LIST)
        for i in x:
            encode_func[type(i)](i, r)
        r.append(CHR_TERM)

def encode_dict(x,r):
    if len(x) < DICT_FIXED_COUNT:
        r.append(chr(DICT_FIXED_START + len(x)))
        for k, v in x.items():
            encode_func[type(k)](k, r)
            encode_func[type(v)](v, r)
    else:
        r.append(CHR_DICT)
        for k, v in x.items():
            encode_func[type(k)](k, r)
            encode_func[type(v)](v, r)
        r.append(CHR_TERM)

encode_func = {}
encode_func[IntType] = encode_int
encode_func[LongType] = encode_int
encode_func[StringType] = encode_string
encode_func[ListType] = encode_list
encode_func[TupleType] = encode_list
encode_func[DictType] = encode_dict
encode_func[NoneType] = encode_none
encode_func[UnicodeType] = encode_unicode

lock = Lock()

try:
    from types import BooleanType
    encode_func[BooleanType] = encode_bool
except ImportError:
    pass

def dumps(x, float_bits=DEFAULT_FLOAT_BITS):
    """
    Dump data structure to str.

    Here float_bits is either 32 or 64.
    """
    lock.acquire()
    try:
        if float_bits == 32:
            encode_func[FloatType] = encode_float32
        elif float_bits == 64:
            encode_func[FloatType] = encode_float64
        else:
            raise ValueError('Float bits (%d) is not 32 or 64' % float_bits)
        r = []
        encode_func[type(x)](x, r)
    finally:
        lock.release()
    return ''.join(r)

def test():
    f1 = struct.unpack('!f', struct.pack('!f', 25.5))[0]
    f2 = struct.unpack('!f', struct.pack('!f', 29.3))[0]
    f3 = struct.unpack('!f', struct.pack('!f', -0.6))[0]
    L = (({'a':15, 'bb':f1, 'ccc':f2, '':(f3,(),False,True,'')},('a',10**20),tuple(range(-100000,100000)),'b'*31,'b'*62,'b'*64,2**30,2**33,2**62,2**64,2**30,2**33,2**62,2**64,False,False, True, -1, 2, 0),)
    assert loads(dumps(L)) == L
    d = dict(zip(range(-100000,100000),range(-100000,100000)))
    d.update({'a':20, 20:40, 40:41, f1:f2, f2:f3, f3:False, False:True, True:False})
    L = (d, {}, {5:6}, {7:7,True:8}, {9:10, 22:39, 49:50, 44: ''})
    assert loads(dumps(L)) == L
    L = ('', 'a'*10, 'a'*100, 'a'*1000, 'a'*10000, 'a'*100000, 'a'*1000000, 'a'*10000000)
    assert loads(dumps(L)) == L
    L = tuple([dict(zip(range(n),range(n))) for n in range(100)]) + ('b',)
    assert loads(dumps(L)) == L
    L = tuple([dict(zip(range(n),range(-n,0))) for n in range(100)]) + ('b',)
    assert loads(dumps(L)) == L
    L = tuple([tuple(range(n)) for n in range(100)]) + ('b',)
    assert loads(dumps(L)) == L
    L = tuple(['a'*n for n in range(1000)]) + ('b',)
    assert loads(dumps(L)) == L
    L = tuple(['a'*n for n in range(1000)]) + (None,True,None)
    assert loads(dumps(L)) == L
    assert loads(dumps(None)) == None
    assert loads(dumps({None:None})) == {None:None}
    assert 1e-10<abs(loads(dumps(1.1))-1.1)<1e-6
    assert 1e-10<abs(loads(dumps(1.1,32))-1.1)<1e-6
    assert abs(loads(dumps(1.1,64))-1.1)<1e-12
    assert loads(dumps(u"Hello World!!"))
try:
    import psyco
    psyco.bind(dumps)
    psyco.bind(loads)
except ImportError:
    pass


if __name__ == '__main__':
  test()

########NEW FILE########
__FILENAME__ = transfer
import zlib
import struct
import socket
import ssl

from synchronousdeluge import rencode


__all__ = ["DelugeTransfer"]

class DelugeTransfer(object):
    def __init__(self):
        self.sock = None
        self.conn = None
        self.connected = False

    def connect(self, hostport):
        if self.connected:
            self.disconnect()

        self.sock = socket.create_connection(hostport)
        self.conn = ssl.wrap_socket(self.sock, None, None, False, ssl.CERT_NONE, ssl.PROTOCOL_SSLv3)
        self.connected = True

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.connected = False

    def send_request(self, request):
        data = (request.format(),)
        payload = zlib.compress(rencode.dumps(data))
        self.conn.sendall(payload)

        buf = b""

        while True:
            data = self.conn.recv(1024)

            if not data:
                self.connected = False
                break

            buf += data
            dobj = zlib.decompressobj()

            try:
                message = rencode.loads(dobj.decompress(buf))
            except (ValueError, zlib.error, struct.error):
                # Probably incomplete data, read more
                continue
            else:
                buf = dobj.unused_data

            yield message



########NEW FILE########
__FILENAME__ = TorrentToMedia
#!/usr/bin/env python

#System imports
import os
import sys
import ConfigParser
import shutil
import logging
import datetime
import time
import re
from subprocess import call, Popen

# Custom imports
import autoProcess.migratecfg as migratecfg
import extractor.extractor as extractor
import autoProcess.autoProcessComics as autoProcessComics
import autoProcess.autoProcessGames as autoProcessGames 
import autoProcess.autoProcessMusic as autoProcessMusic
import autoProcess.autoProcessTV as autoProcessTV
import autoProcess.autoProcessMovie as autoProcessMovie
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *
from utorrent.client import UTorrentClient
from transmissionrpc.client import Client as TransmissionClient
from synchronousdeluge.client import DelugeClient

def main(inputDirectory, inputName, inputCategory, inputHash, inputID):

    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    video2 = int(0)
    foundFile = int(0)
    extracted_folder = []
    extractionSuccess = False
    copy_list = []
    useLink = useLink_in

    Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    inputDirectory, inputName, inputCategory, root = category_search(inputDirectory, inputName, inputCategory, root, categories)  # Confirm the category by parsing directory structure

    Logger.debug("MAIN: Determined Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    if  inputCategory in sbCategory and sbFork in SICKBEARD_TORRENT and Torrent_ForceLink != 1:
        Logger.info("MAIN: Calling SickBeard's %s branch to post-process: %s",sbFork ,inputName)
        result = autoProcessTV.processEpisode(inputDirectory, inputName, int(0))
        if result == 1:
            Logger.info("MAIN: A problem was reported in the autoProcess* script.")
        Logger.info("MAIN: All done.")
        sys.exit()

    outputDestination = ""
    for category in categories:
        if category == inputCategory:
            if os.path.basename(inputDirectory) == inputName and os.path.isdir(inputDirectory):
                Logger.info("MAIN: Download is a directory")
                outputDestination = os.path.normpath(os.path.join(outputDirectory, category, safeName(inputName)))
            else:
                Logger.info("MAIN: Download is not a directory")
                outputDestination = os.path.normpath(os.path.join(outputDirectory, category, os.path.splitext(safeName(inputName))[0]))
            Logger.info("MAIN: Output directory set to: %s", outputDestination)
            break
        else:
            continue
    if outputDestination == "":
        if inputCategory == "":
            inputCategory = "UNCAT" 
        if os.path.basename(inputDirectory) == inputName and os.path.isdir(inputDirectory):
            Logger.info("MAIN: Download is a directory")
            outputDestination = os.path.normpath(os.path.join(outputDirectory, inputCategory, safeName(inputName)))
        else:
            Logger.info("MAIN: Download is not a directory")
            outputDestination = os.path.normpath(os.path.join(outputDirectory, inputCategory, os.path.splitext(safeName(inputName))[0]))
        Logger.info("MAIN: Output directory set to: %s", outputDestination)

    processOnly = cpsCategory + sbCategory + hpCategory + mlCategory + gzCategory
    if not "NONE" in user_script_categories: # if None, we only process the 5 listed.
        if "ALL" in user_script_categories: # All defined categories
            processOnly = categories
        processOnly.extend(user_script_categories) # Adds all categories to be processed by userscript.

    if not inputCategory in processOnly:
        Logger.info("MAIN: No processing to be done for category: %s. Exiting", inputCategory) 
        Logger.info("MAIN: All done.")
        sys.exit()

    # Hardlink solution for uTorrent, need to implent support for deluge, transmission
    if clientAgent in ['utorrent', 'transmission', 'deluge'] and inputHash:
        if clientAgent == 'utorrent':
            try:
                Logger.debug("MAIN: Connecting to %s: %s", clientAgent, uTorrentWEBui)
                utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
            except:
                Logger.exception("MAIN: Failed to connect to uTorrent")
                utorrentClass = ""
        if clientAgent == 'transmission':
            try:
                Logger.debug("MAIN: Connecting to %s: http://%s:%s", clientAgent, TransmissionHost, TransmissionPort)
                TransmissionClass = TransmissionClient(TransmissionHost, TransmissionPort, TransmissionUSR, TransmissionPWD)
            except:
                Logger.exception("MAIN: Failed to connect to Transmission")
                TransmissionClass = ""
        if clientAgent == 'deluge':
            try:
                Logger.debug("MAIN: Connecting to %s: http://%s:%s", clientAgent, DelugeHost, DelugePort)
                delugeClient = DelugeClient()
                delugeClient.connect(host = DelugeHost, port = DelugePort, username = DelugeUSR, password = DelugePWD)
            except:
                Logger.exception("MAIN: Failed to connect to deluge")
                delugeClient = ""

        # if we are using links with uTorrent it means we need to pause it in order to access the files
        Logger.debug("MAIN: Stoping torrent %s in %s while processing", inputName, clientAgent)
        if clientAgent == 'utorrent' and utorrentClass != "":            
            utorrentClass.stop(inputHash)
        if clientAgent == 'transmission' and TransmissionClass !="":
            TransmissionClass.stop_torrent(inputID)
        if clientAgent == 'deluge' and delugeClient != "":
            delugeClient.core.pause_torrent([inputID])
        time.sleep(5)  # Give Torrent client some time to catch up with the change      

    Logger.debug("MAIN: Scanning files in directory: %s", inputDirectory)

    if inputCategory in hpCategory:
        noFlatten.extend(hpCategory) # Make sure we preserve folder structure for HeadPhones.
        if useLink in ['sym','move']: # These don't work for HeadPhones.
            useLink = 'no' # default to copy.

    if inputCategory in sbCategory and sbFork in SICKBEARD_TORRENT: # Don't flatten when sending to SICKBEARD_TORRENT
        noFlatten.extend(sbCategory)
      
    outputDestinationMaster = outputDestination # Save the original, so we can change this within the loop below, and reset afterwards.
    now = datetime.datetime.now()
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        Logger.debug("MAIN: Found %s files in %s", str(len(filenames)), dirpath)
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)
            if inputCategory in noFlatten:
                newDir = dirpath # find the full path
                newDir = newDir.replace(inputDirectory, "") #find the extra-depth directory
                if len(newDir) > 0 and newDir[0] == "/":
                    newDir = newDir[1:] # remove leading "/" to enable join to work.
                outputDestination = os.path.join(outputDestinationMaster, newDir) # join this extra directory to output.
                Logger.debug("MAIN: Setting outputDestination to %s to preserve folder structure", outputDestination)

            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                if foundFile == int(0): 
                    Logger.debug("MAIN: Looking for %s in: %s", inputName, file)
                if (safeName(inputName) in safeName(file)) or (safeName(fileName) in safeName(inputName)):
                    #pass  # This file does match the Torrent name
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s that matches Torrent Name %s", file, inputName)
                else:
                    continue  # This file does not match the Torrent name, skip it

            if root == 2:
                Logger.debug("MAIN: Looking for files with modified/created dates less than 5 minutes old.")
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                    #pass  # This file does match the date time criteria
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it

            if inputCategory in sbCategory and sbFork in SICKBEARD_TORRENT: # We want to link every file.
                Logger.info("MAIN: Found file %s in %s", fileExtension, filePath)
                try:
                    copy_link(filePath, targetDirectory, useLink, outputDestination)
                    copy_list.append([filePath, os.path.join(outputDestination, file)])
                except:
                    Logger.exception("MAIN: Failed to link file: %s", file)
                continue

            if fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize, SampleIDs) and not inputCategory in hpCategory:  # Ignore samples
                    Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                    continue
                else:
                    video = video + 1
                    Logger.info("MAIN: Found media file %s in %s", fileExtension, filePath)
                    try:
                        copy_link(filePath, targetDirectory, useLink, outputDestination)
                        copy_list.append([filePath, os.path.join(outputDestination, file)])
                    except:
                        Logger.exception("MAIN: Failed to link file: %s", file)
            elif fileExtension in metaContainer:
                Logger.info("MAIN: Found metadata file %s for file %s", fileExtension, filePath)
                try:
                    copy_link(filePath, targetDirectory, useLink, outputDestination)
                    copy_list.append([filePath, os.path.join(outputDestination, file)])
                except:
                    Logger.exception("MAIN: Failed to link file: %s", file)
                continue
            elif fileExtension in compressedContainer:
                if inputCategory in hpCategory: # We need to link all files for HP in order to move these back to support seeding.
                    Logger.info("MAIN: Linking compressed archive file %s for file %s", fileExtension, filePath)
                    try:
                        copy_link(filePath, targetDirectory, useLink, outputDestination)
                        copy_list.append([filePath, os.path.join(outputDestination, file)])
                    except:
                        Logger.exception("MAIN: Failed to link file: %s", file)
                # find part numbers in second "extension" from right, if we have more than 1 compressed file in the same directory.
                if re.search(r'\d+', os.path.splitext(fileName)[1]) and os.path.dirname(filePath) in extracted_folder and not (os.path.splitext(fileName)[1] in ['.720p','.1080p']):
                    part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                    if part == 1: # we only want to extract the primary part.
                        Logger.debug("MAIN: Found primary part of a multi-part archive %s. Extracting", file)                       
                    else:
                        Logger.debug("MAIN: Found part %s of a multi-part archive %s. Ignoring", part, file)
                        continue
                Logger.info("MAIN: Found compressed archive %s for file %s", fileExtension, filePath)
                try:
                    if inputCategory in hpCategory: # HP needs to scan the same dir as passed to downloader. 
                        extractor.extract(filePath, inputDirectory)
                    else:
                        extractor.extract(filePath, outputDestination)
                    extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (don't need to pause archived content)
                    extracted_folder.append(os.path.dirname(filePath))
                except:
                    Logger.exception("MAIN: Extraction failed for: %s", file)
                continue
            elif not inputCategory in cpsCategory + sbCategory: #process all for non-video categories.
                Logger.info("MAIN: Found file %s for category %s", filePath, inputCategory)
                copy_link(filePath, targetDirectory, useLink, outputDestination)
                copy_list.append([filePath, os.path.join(outputDestination, file)])
                continue
            else:
                Logger.debug("MAIN: Ignoring unknown filetype %s for file %s", fileExtension, filePath)
                continue

    outputDestination = outputDestinationMaster # Reset here.
    if not inputCategory in noFlatten: #don't flatten hp in case multi cd albums, and we need to copy this back later. 
        flatten(outputDestination)

    # Now check if movie files exist in destination:
    if inputCategory in cpsCategory + sbCategory and not (inputCategory in sbCategory and sbFork in SICKBEARD_TORRENT): 
        for dirpath, dirnames, filenames in os.walk(outputDestination):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in mediaContainer:  # If the file is a video file
                    if is_sample(filePath, inputName, minSampleSize, SampleIDs):
                        Logger.debug("MAIN: Removing sample file: %s", filePath)
                        os.unlink(filePath)  # remove samples
                    else:
                        Logger.debug("MAIN: Found media file: %s", filePath)
                        video2 = video2 + 1
                else:
                    Logger.debug("MAIN: File %s is not a media file", filePath)
        if video2 >= video and video2 > int(0):  # Check that all video files were moved
            Logger.debug("MAIN: Found %s media files", str(video2))
            status = int(0)
        else:
            Logger.debug("MAIN: Found %s media files in output. %s were found in input", str(video2), str(video))

    if inputCategory in sbCategory and sbFork in SICKBEARD_TORRENT:
        if len(copy_list) > 0:
            Logger.debug("MAIN: Found and linked %s files", str(len(copy_list)))
            status = int(0)

    processCategories = cpsCategory + sbCategory + hpCategory + mlCategory + gzCategory

    if (inputCategory in user_script_categories and not "NONE" in user_script_categories) or ("ALL" in user_script_categories and not inputCategory in processCategories):
        Logger.info("MAIN: Processing user script %s.", user_script)
        result = external_script(outputDestination,inputName,inputCategory)
    elif status == int(0) or (inputCategory in hpCategory + mlCategory + gzCategory): # if movies linked/extracted or for other categories.
        Logger.debug("MAIN: Calling autoProcess script for successful download.")
        status = int(0) # hp, my, gz don't support failed.
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    if inputCategory in cpsCategory:
        Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
        download_id = inputHash
        result = autoProcessMovie.process(outputDestination, inputName, status, clientAgent, download_id, inputCategory)
    elif inputCategory in sbCategory:
        Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
        result = autoProcessTV.processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif inputCategory in hpCategory:
        Logger.info("MAIN: Calling HeadPhones to post-process: %s", inputName)
        result = autoProcessMusic.process(inputDirectory, inputName, status, inputCategory)
    elif inputCategory in mlCategory:
        Logger.info("MAIN: Calling Mylar to post-process: %s", inputName)
        result = autoProcessComics.processEpisode(outputDestination, inputName, status, inputCategory)
    elif inputCategory in gzCategory:
        Logger.info("MAIN: Calling Gamez to post-process: %s", inputName)
        result = autoProcessGames.process(outputDestination, inputName, status, inputCategory)

    if result == 1:
        Logger.info("MAIN: A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")

    if inputCategory in hpCategory:
        # we need to move the output dir files back...
        Logger.debug("MAIN: Moving temporary HeadPhones files back to allow seeding.")
        for item in copy_list:
            if os.path.isfile(os.path.normpath(item[1])): # check to ensure temp files still exist.
                if os.path.isfile(os.path.normpath(item[0])): # both exist, remove temp version
                    Logger.debug("MAIN: File %s still present. Removing tempoary file %s", str(item[0]), str(item[1]))
                    os.unlink(os.path.normpath(item[1]))
                    continue
                else: # move temp version back to allow seeding or Torrent removal.
                    Logger.debug("MAIN: Moving %s to %s", str(item[1]), str(item[0]))
                    newDestination = os.path.split(os.path.normpath(item[0]))
                    try:
                        copy_link(os.path.normpath(item[1]), os.path.normpath(item[0]), 'move', newDestination[0])
                    except:
                        Logger.exception("MAIN: Failed to move file: %s", file)
                    continue

    # Hardlink solution for uTorrent, need to implent support for deluge, transmission
    if clientAgent in ['utorrent', 'transmission', 'deluge']  and inputHash:
        # Delete torrent and torrentdata from Torrent client if processing was successful.
        if deleteOriginal == 1 and result != 1:
            Logger.debug("MAIN: Deleting torrent %s from %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and utorrentClass != "":
                utorrentClass.removedata(inputHash)
                if not inputCategory in hpCategory:
                    utorrentClass.remove(inputHash)
            if clientAgent == 'transmission' and TransmissionClass !="":
                if inputCategory in hpCategory: #don't delete actual files for hp category, just remove torrent.
                    TransmissionClass.remove_torrent(inputID, False)
                else:
                    TransmissionClass.remove_torrent(inputID, True)
            if clientAgent == 'deluge' and delugeClient != "":
                delugeClient.core.remove_torrent(inputID, True)
        # we always want to resume seeding, for now manually find out what is wrong when extraction fails
        else:
            Logger.debug("MAIN: Starting torrent %s in %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and utorrentClass != "":
                utorrentClass.start(inputHash)
            if clientAgent == 'transmission' and TransmissionClass !="":
                TransmissionClass.start_torrent(inputID)
            if clientAgent == 'deluge' and delugeClient != "":
                delugeClient.core.resume_torrent([inputID])
        time.sleep(5)        
    #cleanup
    if inputCategory in processCategories and result == 0 and os.path.isdir(outputDestination):
        num_files_new = int(0)
        file_list = []
        for dirpath, dirnames, filenames in os.walk(outputDestination):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in mediaContainer or fileExtension in metaContainer:
                    num_files_new = num_files_new + 1
                    file_list.append(file)
        if num_files_new == int(0): 
            Logger.info("All files have been processed. Cleaning outputDirectory %s", outputDestination)
            shutil.rmtree(outputDestination)
        else:
            Logger.info("outputDirectory %s still contains %s media and/or meta files. This directory will not be removed.", outputDestination, num_files_new)
            for item in file_list:
                Logger.debug("media/meta file found: %s", item)
    Logger.info("MAIN: All done.")

def external_script(outputDestination,torrentName,torrentLabel):

    final_result = int(0) # start at 0.
    num_files = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in user_script_mediaExtensions or "ALL" in user_script_mediaExtensions:
                num_files = num_files + 1
                if user_script_runOnce == 1 and num_files > 1: # we have already run once, so just continue to get number of files.
                    continue
                command = [user_script]
                for param in user_script_param:
                    if param == "FN":
                        command.append(file)
                        continue
                    elif param == "FP":
                        command.append(filePath)
                        continue
                    elif param == "TN":
                        command.append(torrentName)
                        continue
                    elif param == "TL":
                        command.append(torrentLabel)
                        continue
                    elif param == "DN":
                        if user_script_runOnce == 1:
                            command.append(outputDestination)
                        else:
                            command.append(dirpath)
                        continue
                    else:
                        command.append(param)
                        continue
                cmd = ""
                for item in command:
                    cmd = cmd + " " + item
                Logger.info("Running script %s on file %s.", cmd, filePath)
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in user_script_successCodes: # Linux returns 0 for successful.
                        Logger.info("UserScript %s was successfull", command[0])
                        result = int(0)
                    else:
                        Logger.error("UserScript %s has failed with return code: %s", command[0], res)
                        Logger.info("If the UserScript completed successfully you should add %s to the user_script_successCodes", res)
                        result = int(1)
                except:
                    Logger.exception("UserScript %s has failed", command[0])
                    result = int(1)
                final_result = final_result + result

    time.sleep(user_delay)
    num_files_new = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in user_script_mediaExtensions or user_script_mediaExtensions == "ALL":
                num_files_new = num_files_new + 1

    if user_script_clean == int(1) and num_files_new == int(0) and final_result == int(0):
        Logger.info("All files have been processed. Cleaning outputDirectory %s", outputDestination)
        shutil.rmtree(outputDestination)
    elif user_script_clean == int(1) and num_files_new != int(0):
        Logger.info("%s files were processed, but %s still remain. outputDirectory will not be cleaned.", num_files, num_files_new)           
    return final_result

if __name__ == "__main__":

    #check to migrate old cfg before trying to load.
    if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
        migratecfg.migrate()
    
    # Logging
    nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
    Logger = logging.getLogger(__name__)

    Logger.info("====================") # Seperate old from new log
    Logger.info("TorrentToMedia %s", VERSION)

    WakeUp()

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        sys.exit(-1)

    # CONFIG FILE
    Logger.info("MAIN: Loading config from %s", configFilename)
    config.read(configFilename)
                                                                                        # EXAMPLE VALUES:
    clientAgent = config.get("Torrent", "clientAgent")                                  # utorrent | deluge | transmission | rtorrent | other
    useLink_in = config.get("Torrent", "useLink")                                          # no | hard | sym
    outputDirectory = config.get("Torrent", "outputDirectory")                          # /abs/path/to/complete/
    categories = (config.get("Torrent", "categories")).split(',')                       # music,music_videos,pictures,software
    noFlatten = (config.get("Torrent", "noFlatten")).split(',')

    uTorrentWEBui = config.get("Torrent", "uTorrentWEBui")                              # http://localhost:8090/gui/
    uTorrentUSR = config.get("Torrent", "uTorrentUSR")                                  # mysecretusr
    uTorrentPWD = config.get("Torrent", "uTorrentPWD")                                  # mysecretpwr

    TransmissionHost = config.get("Torrent", "TransmissionHost")                        # localhost
    TransmissionPort = config.get("Torrent", "TransmissionPort")                        # 8084
    TransmissionUSR = config.get("Torrent", "TransmissionUSR")                          # mysecretusr
    TransmissionPWD = config.get("Torrent", "TransmissionPWD")                          # mysecretpwr

    DelugeHost = config.get("Torrent", "DelugeHost")                                    # localhost
    DelugePort = config.get("Torrent", "DelugePort")                                    # 8084
    DelugeUSR = config.get("Torrent", "DelugeUSR")                                      # mysecretusr
    DelugePWD = config.get("Torrent", "DelugePWD")                                      # mysecretpwr
    
    deleteOriginal = int(config.get("Torrent", "deleteOriginal"))                       # 0
    
    compressedContainer = (config.get("Extensions", "compressedExtensions")).split(',') # .zip,.rar,.7z
    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')           # .mkv,.avi,.divx
    metaContainer = (config.get("Extensions", "metaExtensions")).split(',')             # .nfo,.sub,.srt
    minSampleSize = int(config.get("Extensions", "minSampleSize"))                      # 200 (in MB)
    SampleIDs = (config.get("Extensions", "SampleIDs")).split(',')                      # sample,-s.
    
    cpsCategory = (config.get("CouchPotato", "cpsCategory")).split(',')                 # movie
    sbCategory = (config.get("SickBeard", "sbCategory")).split(',')                     # tv
    sbFork = config.get("SickBeard", "fork")                                            # default
    Torrent_ForceLink = int(config.get("SickBeard", "Torrent_ForceLink"))               # 1
    hpCategory = (config.get("HeadPhones", "hpCategory")).split(',')                    # music
    mlCategory = (config.get("Mylar", "mlCategory")).split(',')                         # comics
    gzCategory = (config.get("Gamez", "gzCategory")).split(',')                         # games
    categories.extend(cpsCategory)
    categories.extend(sbCategory)
    categories.extend(hpCategory)
    categories.extend(mlCategory)
    categories.extend(gzCategory)

    user_script_categories = config.get("UserScript", "user_script_categories").split(',')         # NONE
    if not "NONE" in user_script_categories: 
        user_script_mediaExtensions = (config.get("UserScript", "user_script_mediaExtensions")).split(',')
        user_script = config.get("UserScript", "user_script_path")
        user_script_param = (config.get("UserScript", "user_script_param")).split(',')
        user_script_successCodes = (config.get("UserScript", "user_script_successCodes")).split(',')
        user_script_clean = int(config.get("UserScript", "user_script_clean"))
        user_delay = int(config.get("UserScript", "delay"))
        user_script_runOnce = int(config.get("UserScript", "user_script_runOnce"))
    
    transcode = int(config.get("Transcoder", "transcode"))

    n = 0    
    for arg in sys.argv:
        Logger.debug("arg %s is: %s", n, arg)
        n = n+1

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = parse_args(clientAgent)
    except:
        Logger.exception("MAIN: There was a problem loading variables")
        sys.exit(-1)

    main(inputDirectory, inputName, inputCategory, inputHash, inputID)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import re, time, operator, warnings, os
import base64
import json

from transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT
from transmissionrpc.error import TransmissionError, HTTPHandlerError
from transmissionrpc.utils import LOGGER, get_arguments, make_rpc_name, argument_value_convert, rpc_bool
from transmissionrpc.httphandler import DefaultHTTPHandler
from transmissionrpc.torrent import Torrent
from transmissionrpc.session import Session

from six import PY3, integer_types, string_types, iteritems

if PY3:
    from urllib.parse import urlparse
    from urllib.request import urlopen
else:
    from urlparse import urlparse
    from urllib2 import urlopen

def debug_httperror(error):
    """
    Log the Transmission RPC HTTP error.
    """
    try:
        data = json.loads(error.data)
    except ValueError:
        data = error.data
    LOGGER.debug(
        json.dumps(
            {
                'response': {
                    'url': error.url,
                    'code': error.code,
                    'msg': error.message,
                    'headers': error.headers,
                    'data': data,
                }
            },
            indent=2
        )
    )

def parse_torrent_id(arg):
    """Parse an torrent id or torrent hashString."""
    torrent_id = None
    if isinstance(arg, integer_types):
        # handle index
        torrent_id = int(arg)
    elif isinstance(arg, float):
        torrent_id = int(arg)
        if torrent_id != arg:
            torrent_id = None
    elif isinstance(arg, string_types):
        try:
            torrent_id = int(arg)
            if torrent_id >= 2**31:
                torrent_id = None
        except (ValueError, TypeError):
            pass
        if torrent_id is None:
            # handle hashes
            try:
                int(arg, 16)
                torrent_id = arg
            except (ValueError, TypeError):
                pass
    return torrent_id

def parse_torrent_ids(args):
    """
    Take things and make them valid torrent identifiers
    """
    ids = []

    if args is None:
        pass
    elif isinstance(args, string_types):
        for item in re.split('[ ,]+', args):
            if len(item) == 0:
                continue
            addition = None
            torrent_id = parse_torrent_id(item)
            if torrent_id is not None:
                addition = [torrent_id]
            if not addition:
                # handle index ranges i.e. 5:10
                match = re.match('^(\d+):(\d+)$', item)
                if match:
                    try:
                        idx_from = int(match.group(1))
                        idx_to = int(match.group(2))
                        addition = list(range(idx_from, idx_to + 1))
                    except ValueError:
                        pass
            if not addition:
                raise ValueError('Invalid torrent id, \"%s\"' % item)
            ids.extend(addition)
    elif isinstance(args, (list, tuple)):
        for item in args:
            ids.extend(parse_torrent_ids(item))
    else:
        torrent_id = parse_torrent_id(args)
        if torrent_id == None:
            raise ValueError('Invalid torrent id')
        else:
            ids = [torrent_id]
    return ids

"""
Torrent ids

Many functions in Client takes torrent id. A torrent id can either be id or
hashString. When supplying multiple id's it is possible to use a list mixed
with both id and hashString.

Timeouts

Since most methods results in HTTP requests against Transmission, it is
possible to provide a argument called ``timeout``. Timeout is only effective
when using Python 2.6 or later and the default timeout is 30 seconds.
"""

class Client(object):
    """
    Client is the class handling the Transmission JSON-RPC client protocol.
    """

    def __init__(self, address='localhost', port=DEFAULT_PORT, user=None, password=None, http_handler=None, timeout=None):
        if isinstance(timeout, (integer_types, float)):
            self._query_timeout = float(timeout)
        else:
            self._query_timeout = DEFAULT_TIMEOUT
        urlo = urlparse(address)
        if urlo.scheme == '':
            base_url = 'http://' + address + ':' + str(port)
            self.url = base_url + '/transmission/rpc/'
        else:
            if urlo.port:
                self.url = urlo.scheme + '://' + urlo.hostname + ':' + str(urlo.port) + urlo.path
            else:
                self.url = urlo.scheme + '://' + urlo.hostname + urlo.path
            LOGGER.info('Using custom URL "' + self.url + '".')
            if urlo.username and urlo.password:
                user = urlo.username
                password = urlo.password
            elif urlo.username or urlo.password:
                LOGGER.warning('Either user or password missing, not using authentication.')
        if http_handler is None:
            self.http_handler = DefaultHTTPHandler()
        else:
            if hasattr(http_handler, 'set_authentication') and hasattr(http_handler, 'request'):
                self.http_handler = http_handler
            else:
                raise ValueError('Invalid HTTP handler.')
        if user and password:
            self.http_handler.set_authentication(self.url, user, password)
        elif user or password:
            LOGGER.warning('Either user or password missing, not using authentication.')
        self._sequence = 0
        self.session = None
        self.session_id = 0
        self.server_version = None
        self.protocol_version = None
        self.get_session()
        self.torrent_get_arguments = get_arguments('torrent-get'
                                                   , self.rpc_version)

    def _get_timeout(self):
        """
        Get current timeout for HTTP queries.
        """
        return self._query_timeout

    def _set_timeout(self, value):
        """
        Set timeout for HTTP queries.
        """
        self._query_timeout = float(value)

    def _del_timeout(self):
        """
        Reset the HTTP query timeout to the default.
        """
        self._query_timeout = DEFAULT_TIMEOUT

    timeout = property(_get_timeout, _set_timeout, _del_timeout, doc="HTTP query timeout.")

    def _http_query(self, query, timeout=None):
        """
        Query Transmission through HTTP.
        """
        headers = {'x-transmission-session-id': str(self.session_id)}
        result = {}
        request_count = 0
        if timeout is None:
            timeout = self._query_timeout
        while True:
            LOGGER.debug(json.dumps({'url': self.url, 'headers': headers, 'query': query, 'timeout': timeout}, indent=2))
            try:
                result = self.http_handler.request(self.url, query, headers, timeout)
                break
            except HTTPHandlerError as error:
                if error.code == 409:
                    LOGGER.info('Server responded with 409, trying to set session-id.')
                    if request_count > 1:
                        raise TransmissionError('Session ID negotiation failed.', error)
                    session_id = None
                    for key in list(error.headers.keys()):
                        if key.lower() == 'x-transmission-session-id':
                            session_id = error.headers[key]
                            self.session_id = session_id
                            headers = {'x-transmission-session-id': str(self.session_id)}
                    if session_id is None:
                        debug_httperror(error)
                        raise TransmissionError('Unknown conflict.', error)
                else:
                    debug_httperror(error)
                    raise TransmissionError('Request failed.', error)
            request_count += 1
        return result

    def _request(self, method, arguments=None, ids=None, require_ids=False, timeout=None):
        """
        Send json-rpc request to Transmission using http POST
        """
        if not isinstance(method, string_types):
            raise ValueError('request takes method as string')
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError('request takes arguments as dict')
        ids = parse_torrent_ids(ids)
        if len(ids) > 0:
            arguments['ids'] = ids
        elif require_ids:
            raise ValueError('request require ids')

        query = json.dumps({'tag': self._sequence, 'method': method
                            , 'arguments': arguments})
        self._sequence += 1
        start = time.time()
        http_data = self._http_query(query, timeout)
        elapsed = time.time() - start
        LOGGER.info('http request took %.3f s' % (elapsed))

        try:
            data = json.loads(http_data)
        except ValueError as error:
            LOGGER.error('Error: ' + str(error))
            LOGGER.error('Request: \"%s\"' % (query))
            LOGGER.error('HTTP data: \"%s\"' % (http_data))
            raise

        LOGGER.debug(json.dumps(data, indent=2))
        if 'result' in data:
            if data['result'] != 'success':
                raise TransmissionError('Query failed with result \"%s\".' % (data['result']))
        else:
            raise TransmissionError('Query failed without result.')

        results = {}
        if method == 'torrent-get':
            for item in data['arguments']['torrents']:
                results[item['id']] = Torrent(self, item)
                if self.protocol_version == 2 and 'peers' not in item:
                    self.protocol_version = 1
        elif method == 'torrent-add':
            item = None
            if 'torrent-added' in data['arguments']:
                item = data['arguments']['torrent-added']
            elif 'torrent-duplicate' in data['arguments']:
                item = data['arguments']['torrent-duplicate']
            if item:
                results[item['id']] = Torrent(self, item)
            else:
                raise TransmissionError('Invalid torrent-add response.')
        elif method == 'session-get':
            self._update_session(data['arguments'])
        elif method == 'session-stats':
            # older versions of T has the return data in "session-stats"
            if 'session-stats' in data['arguments']:
                self._update_session(data['arguments']['session-stats'])
            else:
                self._update_session(data['arguments'])
        elif method in ('port-test', 'blocklist-update', 'free-space', 'torrent-rename-path'):
            results = data['arguments']
        else:
            return None

        return results

    def _update_session(self, data):
        """
        Update session data.
        """
        if self.session:
            self.session.from_request(data)
        else:
            self.session = Session(self, data)

    def _update_server_version(self):
        """Decode the Transmission version string, if available."""
        if self.server_version is None:
            version_major = 1
            version_minor = 30
            version_changeset = 0
            version_parser = re.compile('(\d).(\d+) \((\d+)\)')
            if hasattr(self.session, 'version'):
                match = version_parser.match(self.session.version)
                if match:
                    version_major = int(match.group(1))
                    version_minor = int(match.group(2))
                    version_changeset = match.group(3)
            self.server_version = (version_major, version_minor, version_changeset)

    @property
    def rpc_version(self):
        """
        Get the Transmission RPC version. Trying to deduct if the server don't have a version value.
        """
        if self.protocol_version is None:
            # Ugly fix for 2.20 - 2.22 reporting rpc-version 11, but having new arguments
            if self.server_version and (self.server_version[0] == 2 and self.server_version[1] in [20, 21, 22]):
                self.protocol_version = 12
            # Ugly fix for 2.12 reporting rpc-version 10, but having new arguments
            elif self.server_version and (self.server_version[0] == 2 and self.server_version[1] == 12):
                self.protocol_version = 11
            elif hasattr(self.session, 'rpc_version'):
                self.protocol_version = self.session.rpc_version
            elif hasattr(self.session, 'version'):
                self.protocol_version = 3
            else:
                self.protocol_version = 2
        return self.protocol_version

    def _rpc_version_warning(self, version):
        """
        Add a warning to the log if the Transmission RPC version is lower then the provided version.
        """
        if self.rpc_version < version:
            LOGGER.warning('Using feature not supported by server. RPC version for server %d, feature introduced in %d.'
                % (self.rpc_version, version))

    def add_torrent(self, torrent, timeout=None, **kwargs):
        """
        Add torrent to transfers list. Takes a uri to a torrent or base64 encoded torrent data in ``torrent``.
        Additional arguments are:

        ===================== ===== =========== =============================================================
        Argument              RPC   Replaced by Description
        ===================== ===== =========== =============================================================
        ``bandwidthPriority`` 8 -               Priority for this transfer.
        ``cookies``           13 -              One or more HTTP cookie(s).
        ``download_dir``      1 -               The directory where the downloaded contents will be saved in.
        ``files_unwanted``    1 -               A list of file id's that shouldn't be downloaded.
        ``files_wanted``      1 -               A list of file id's that should be downloaded.
        ``paused``            1 -               If True, does not start the transfer when added.
        ``peer_limit``        1 -               Maximum number of peers allowed.
        ``priority_high``     1 -               A list of file id's that should have high priority.
        ``priority_low``      1 -               A list of file id's that should have low priority.
        ``priority_normal``   1 -               A list of file id's that should have normal priority.
        ===================== ===== =========== =============================================================

        Returns a Torrent object with the fields.
        """
        if torrent is None:
            raise ValueError('add_torrent requires data or a URI.')
        torrent_data = None
        parsed_uri = urlparse(torrent)
        if parsed_uri.scheme in ['ftp', 'ftps', 'http', 'https']:
            # there has been some problem with T's built in torrent fetcher,
            # use a python one instead
            torrent_file = urlopen(torrent)
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if parsed_uri.scheme in ['file']:
            filepath = torrent
            # uri decoded different on linux / windows ?
            if len(parsed_uri.path) > 0:
                filepath = parsed_uri.path
            elif len(parsed_uri.netloc) > 0:
                filepath = parsed_uri.netloc
            torrent_file = open(filepath, 'rb')
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if not torrent_data:
            if torrent.endswith('.torrent') or torrent.startswith('magnet:'):
                torrent_data = None
            else:
                might_be_base64 = False
                try:
                    # check if this is base64 data
                    if PY3:
                        base64.b64decode(torrent.encode('utf-8'))
                    else:
                        base64.b64decode(torrent)
                    might_be_base64 = True
                except Exception:
                    pass
                if might_be_base64:
                    torrent_data = torrent
        args = {}
        if torrent_data:
            args = {'metainfo': torrent_data}
        else:
            args = {'filename': torrent}
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-add', argument, value, self.rpc_version)
            args[arg] = val
        return list(self._request('torrent-add', args, timeout=timeout).values())[0]

    def add(self, data, timeout=None, **kwargs):
        """

        .. WARNING::
            Deprecated, please use add_torrent.
        """
        args = {}
        if data:
            args = {'metainfo': data}
        elif 'metainfo' not in kwargs and 'filename' not in kwargs:
            raise ValueError('No torrent data or torrent uri.')
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-add', argument, value, self.rpc_version)
            args[arg] = val
        warnings.warn('add has been deprecated, please use add_torrent instead.', DeprecationWarning)
        return self._request('torrent-add', args, timeout=timeout)

    def add_uri(self, uri, **kwargs):
        """

        .. WARNING::
            Deprecated, please use add_torrent.
        """
        if uri is None:
            raise ValueError('add_uri requires a URI.')
        # there has been some problem with T's built in torrent fetcher,
        # use a python one instead
        parsed_uri = urlparse(uri)
        torrent_data = None
        if parsed_uri.scheme in ['ftp', 'ftps', 'http', 'https']:
            torrent_file = urlopen(uri)
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if parsed_uri.scheme in ['file']:
            filepath = uri
            # uri decoded different on linux / windows ?
            if len(parsed_uri.path) > 0:
                filepath = parsed_uri.path
            elif len(parsed_uri.netloc) > 0:
                filepath = parsed_uri.netloc
            torrent_file = open(filepath, 'rb')
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        warnings.warn('add_uri has been deprecated, please use add_torrent instead.', DeprecationWarning)
        if torrent_data:
            return self.add(torrent_data, **kwargs)
        else:
            return self.add(None, filename=uri, **kwargs)

    def remove_torrent(self, ids, delete_data=False, timeout=None):
        """
        remove torrent(s) with provided id(s). Local data is removed if
        delete_data is True, otherwise not.
        """
        self._rpc_version_warning(3)
        self._request('torrent-remove',
                    {'delete-local-data':rpc_bool(delete_data)}, ids, True, timeout=timeout)

    def remove(self, ids, delete_data=False, timeout=None):
        """

        .. WARNING::
            Deprecated, please use remove_torrent.
        """
        warnings.warn('remove has been deprecated, please use remove_torrent instead.', DeprecationWarning)
        self.remove_torrent(ids, delete_data, timeout)

    def start_torrent(self, ids, bypass_queue=False, timeout=None):
        """Start torrent(s) with provided id(s)"""
        method = 'torrent-start'
        if bypass_queue and self.rpc_version >= 14:
            method = 'torrent-start-now'
        self._request(method, {}, ids, True, timeout=timeout)

    def start(self, ids, bypass_queue=False, timeout=None):
        """

        .. WARNING::
            Deprecated, please use start_torrent.
        """
        warnings.warn('start has been deprecated, please use start_torrent instead.', DeprecationWarning)
        self.start_torrent(ids, bypass_queue, timeout)

    def start_all(self, bypass_queue=False, timeout=None):
        """Start all torrents respecting the queue order"""
        torrent_list = self.get_torrents()
        method = 'torrent-start'
        if self.rpc_version >= 14:
            if bypass_queue:
                method = 'torrent-start-now'
            torrent_list = sorted(torrent_list, key=operator.attrgetter('queuePosition'))
        ids = [x.id for x in torrent_list]
        self._request(method, {}, ids, True, timeout=timeout)

    def stop_torrent(self, ids, timeout=None):
        """stop torrent(s) with provided id(s)"""
        self._request('torrent-stop', {}, ids, True, timeout=timeout)

    def stop(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use stop_torrent.
        """
        warnings.warn('stop has been deprecated, please use stop_torrent instead.', DeprecationWarning)
        self.stop_torrent(ids, timeout)

    def verify_torrent(self, ids, timeout=None):
        """verify torrent(s) with provided id(s)"""
        self._request('torrent-verify', {}, ids, True, timeout=timeout)

    def verify(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use verify_torrent.
        """
        warnings.warn('verify has been deprecated, please use verify_torrent instead.', DeprecationWarning)
        self.verify_torrent(ids, timeout)

    def reannounce_torrent(self, ids, timeout=None):
        """Reannounce torrent(s) with provided id(s)"""
        self._rpc_version_warning(5)
        self._request('torrent-reannounce', {}, ids, True, timeout=timeout)

    def reannounce(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use reannounce_torrent.
        """
        warnings.warn('reannounce has been deprecated, please use reannounce_torrent instead.', DeprecationWarning)
        self.reannounce_torrent(ids, timeout)

    def get_torrent(self, torrent_id, arguments=None, timeout=None):
        """
        Get information for torrent with provided id.
        ``arguments`` contains a list of field names to be returned, when None
        all fields are requested. See the Torrent class for more information.

        Returns a Torrent object with the requested fields.
        """
        if not arguments:
            arguments = self.torrent_get_arguments
        torrent_id = parse_torrent_id(torrent_id)
        if torrent_id is None:
            raise ValueError("Invalid id")
        result = self._request('torrent-get', {'fields': arguments}, torrent_id, require_ids=True, timeout=timeout)
        if torrent_id in result:
            return result[torrent_id]
        else:
            for torrent in result.values():
                if torrent.hashString == torrent_id:
                    return torrent
            raise KeyError("Torrent not found in result")

    def get_torrents(self, ids=None, arguments=None, timeout=None):
        """
        Get information for torrents with provided ids. For more information see get_torrent.

        Returns a list of Torrent object.
        """
        if not arguments:
            arguments = self.torrent_get_arguments
        return list(self._request('torrent-get', {'fields': arguments}, ids, timeout=timeout).values())

    def info(self, ids=None, arguments=None, timeout=None):
        """

        .. WARNING::
            Deprecated, please use get_torrent or get_torrents. Please note that the return argument has changed in
            the new methods. info returns a dictionary indexed by torrent id.
        """
        warnings.warn('info has been deprecated, please use get_torrent or get_torrents instead.', DeprecationWarning)
        if not arguments:
            arguments = self.torrent_get_arguments
        return self._request('torrent-get', {'fields': arguments}, ids, timeout=timeout)

    def list(self, timeout=None):
        """

        .. WARNING::
            Deprecated, please use get_torrent or get_torrents. Please note that the return argument has changed in
            the new methods. list returns a dictionary indexed by torrent id.
        """
        warnings.warn('list has been deprecated, please use get_torrent or get_torrents instead.', DeprecationWarning)
        fields = ['id', 'hashString', 'name', 'sizeWhenDone', 'leftUntilDone'
            , 'eta', 'status', 'rateUpload', 'rateDownload', 'uploadedEver'
            , 'downloadedEver', 'uploadRatio', 'queuePosition']
        return self._request('torrent-get', {'fields': fields}, timeout=timeout)

    def get_files(self, ids=None, timeout=None):
        """
    	Get list of files for provided torrent id(s). If ids is empty,
    	information for all torrents are fetched. This function returns a dictionary
    	for each requested torrent id holding the information about the files.

    	::

    		{
    			<torrent id>: {
    				<file id>: {
    					'name': <file name>,
    					'size': <file size in bytes>,
    					'completed': <bytes completed>,
    					'priority': <priority ('high'|'normal'|'low')>,
    					'selected': <selected for download (True|False)>
    				}

    				...
    			}

    			...
    		}
        """
        fields = ['id', 'name', 'hashString', 'files', 'priorities', 'wanted']
        request_result = self._request('torrent-get', {'fields': fields}, ids, timeout=timeout)
        result = {}
        for tid, torrent in iteritems(request_result):
            result[tid] = torrent.files()
        return result

    def set_files(self, items, timeout=None):
        """
        Set file properties. Takes a dictionary with similar contents as the result
    	of `get_files`.

    	::

    		{
    			<torrent id>: {
    				<file id>: {
    					'priority': <priority ('high'|'normal'|'low')>,
    					'selected': <selected for download (True|False)>
    				}

    				...
    			}

    			...
    		}
        """
        if not isinstance(items, dict):
            raise ValueError('Invalid file description')
        for tid, files in iteritems(items):
            if not isinstance(files, dict):
                continue
            wanted = []
            unwanted = []
            high = []
            normal = []
            low = []
            for fid, file_desc in iteritems(files):
                if not isinstance(file_desc, dict):
                    continue
                if 'selected' in file_desc and file_desc['selected']:
                    wanted.append(fid)
                else:
                    unwanted.append(fid)
                if 'priority' in file_desc:
                    if file_desc['priority'] == 'high':
                        high.append(fid)
                    elif file_desc['priority'] == 'normal':
                        normal.append(fid)
                    elif file_desc['priority'] == 'low':
                        low.append(fid)
            args = {
                'timeout': timeout
            }
            if len(high) > 0:
                args['priority_high'] = high
            if len(normal) > 0:
                args['priority_normal'] = normal
            if len(low) > 0:
                args['priority_low'] = low
            if len(wanted) > 0:
                args['files_wanted'] = wanted
            if len(unwanted) > 0:
                args['files_unwanted'] = unwanted
            self.change_torrent([tid], **args)

    def change_torrent(self, ids, timeout=None, **kwargs):
        """
    	Change torrent parameters for the torrent(s) with the supplied id's. The
    	parameters are:

        ============================ ===== =============== =======================================================================================
        Argument                     RPC   Replaced by     Description
        ============================ ===== =============== =======================================================================================
        ``bandwidthPriority``        5 -                   Priority for this transfer.
        ``downloadLimit``            5 -                   Set the speed limit for download in Kib/s.
        ``downloadLimited``          5 -                   Enable download speed limiter.
        ``files_unwanted``           1 -                   A list of file id's that shouldn't be downloaded.
        ``files_wanted``             1 -                   A list of file id's that should be downloaded.
        ``honorsSessionLimits``      5 -                   Enables or disables the transfer to honour the upload limit set in the session.
        ``location``                 1 -                   Local download location.
        ``peer_limit``               1 -                   The peer limit for the torrents.
        ``priority_high``            1 -                   A list of file id's that should have high priority.
        ``priority_low``             1 -                   A list of file id's that should have normal priority.
        ``priority_normal``          1 -                   A list of file id's that should have low priority.
        ``queuePosition``            14 -                  Position of this transfer in its queue.
        ``seedIdleLimit``            10 -                  Seed inactivity limit in minutes.
        ``seedIdleMode``             10 -                  Seed inactivity mode. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.
        ``seedRatioLimit``           5 -                   Seeding ratio.
        ``seedRatioMode``            5 -                   Which ratio to use. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.
        ``speed_limit_down``         1 - 5 downloadLimit   Set the speed limit for download in Kib/s.
        ``speed_limit_down_enabled`` 1 - 5 downloadLimited Enable download speed limiter.
        ``speed_limit_up``           1 - 5 uploadLimit     Set the speed limit for upload in Kib/s.
        ``speed_limit_up_enabled``   1 - 5 uploadLimited   Enable upload speed limiter.
        ``trackerAdd``               10 -                  Array of string with announce URLs to add.
        ``trackerRemove``            10 -                  Array of ids of trackers to remove.
        ``trackerReplace``           10 -                  Array of (id, url) tuples where the announce URL should be replaced.
        ``uploadLimit``              5 -                   Set the speed limit for upload in Kib/s.
        ``uploadLimited``            5 -                   Enable upload speed limiter.
        ============================ ===== =============== =======================================================================================

    	.. NOTE::
    	   transmissionrpc will try to automatically fix argument errors.
        """
        args = {}
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-set' , argument, value, self.rpc_version)
            args[arg] = val

        if len(args) > 0:
            self._request('torrent-set', args, ids, True, timeout=timeout)
        else:
            ValueError("No arguments to set")

    def change(self, ids, timeout=None, **kwargs):
        """

        .. WARNING::
            Deprecated, please use change_torrent.
        """
        warnings.warn('change has been deprecated, please use change_torrent instead.', DeprecationWarning)
        self.change_torrent(ids, timeout, **kwargs)

    def move_torrent_data(self, ids, location, timeout=None):
        """Move torrent data to the new location."""
        self._rpc_version_warning(6)
        args = {'location': location, 'move': True}
        self._request('torrent-set-location', args, ids, True, timeout=timeout)

    def move(self, ids, location, timeout=None):
        """

        .. WARNING::
            Deprecated, please use move_torrent_data.
        """
        warnings.warn('move has been deprecated, please use move_torrent_data instead.', DeprecationWarning)
        self.move_torrent_data(ids, location, timeout)

    def locate_torrent_data(self, ids, location, timeout=None):
        """Locate torrent data at the provided location."""
        self._rpc_version_warning(6)
        args = {'location': location, 'move': False}
        self._request('torrent-set-location', args, ids, True, timeout=timeout)

    def locate(self, ids, location, timeout=None):
        """

        .. WARNING::
            Deprecated, please use locate_torrent_data.
        """
        warnings.warn('locate has been deprecated, please use locate_torrent_data instead.', DeprecationWarning)
        self.locate_torrent_data(ids, location, timeout)

    def rename_torrent_path(self, torrent_id, location, name, timeout=None):
        """
        Rename directory and/or files for torrent.
        Remember to use get_torrent or get_torrents to update your file information.
        """
        self._rpc_version_warning(15)
        torrent_id = parse_torrent_id(torrent_id)
        if torrent_id is None:
            raise ValueError("Invalid id")
        dirname = os.path.dirname(name)
        if len(dirname) > 0:
            raise ValueError("Target name cannot contain a path delimiter")
        args = {'path': location, 'name': name}
        result = self._request('torrent-rename-path', args, torrent_id, True, timeout=timeout)
        return (result['path'], result['name'])

    def queue_top(self, ids, timeout=None):
        """Move transfer to the top of the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-top', ids=ids, require_ids=True, timeout=timeout)

    def queue_bottom(self, ids, timeout=None):
        """Move transfer to the bottom of the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-bottom', ids=ids, require_ids=True, timeout=timeout)
        
    def queue_up(self, ids, timeout=None):
        """Move transfer up in the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-up', ids=ids, require_ids=True, timeout=timeout)

    def queue_down(self, ids, timeout=None):
        """Move transfer down in the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-down', ids=ids, require_ids=True, timeout=timeout)

    def get_session(self, timeout=None):
        """
        Get session parameters. See the Session class for more information.
        """
        self._request('session-get', timeout=timeout)
        self._update_server_version()
        return self.session

    def set_session(self, timeout=None, **kwargs):
        """
        Set session parameters. The parameters are:

        ================================ ===== ================= ==========================================================================================================================
        Argument                         RPC   Replaced by       Description
        ================================ ===== ================= ==========================================================================================================================
        ``alt_speed_down``               5 -                     Alternate session download speed limit (in Kib/s).
        ``alt_speed_enabled``            5 -                     Enables alternate global download speed limiter.
        ``alt_speed_time_begin``         5 -                     Time when alternate speeds should be enabled. Minutes after midnight.
        ``alt_speed_time_day``           5 -                     Enables alternate speeds scheduling these days.
        ``alt_speed_time_enabled``       5 -                     Enables alternate speeds scheduling.
        ``alt_speed_time_end``           5 -                     Time when alternate speeds should be disabled. Minutes after midnight.
        ``alt_speed_up``                 5 -                     Alternate session upload speed limit (in Kib/s).
        ``blocklist_enabled``            5 -                     Enables the block list
        ``blocklist_url``                11 -                    Location of the block list. Updated with blocklist-update.
        ``cache_size_mb``                10 -                    The maximum size of the disk cache in MB
        ``dht_enabled``                  6 -                     Enables DHT.
        ``download_dir``                 1 -                     Set the session download directory.
        ``download_queue_enabled``       14 -                    Enables download queue.
        ``download_queue_size``          14 -                    Number of slots in the download queue.
        ``encryption``                   1 -                     Set the session encryption mode, one of ``required``, ``preferred`` or ``tolerated``.
        ``idle_seeding_limit``           10 -                    The default seed inactivity limit in minutes.
        ``idle_seeding_limit_enabled``   10 -                    Enables the default seed inactivity limit
        ``incomplete_dir``               7 -                     The path to the directory of incomplete transfer data.
        ``incomplete_dir_enabled``       7 -                     Enables the incomplete transfer data directory. Otherwise data for incomplete transfers are stored in the download target.
        ``lpd_enabled``                  9 -                     Enables local peer discovery for public torrents.
        ``peer_limit``                   1 - 5 peer-limit-global Maximum number of peers.
        ``peer_limit_global``            5 -                     Maximum number of peers.
        ``peer_limit_per_torrent``       5 -                     Maximum number of peers per transfer.
        ``peer_port``                    5 -                     Peer port.
        ``peer_port_random_on_start``    5 -                     Enables randomized peer port on start of Transmission.
        ``pex_allowed``                  1 - 5 pex-enabled       Allowing PEX in public torrents.
        ``pex_enabled``                  5 -                     Allowing PEX in public torrents.
        ``port``                         1 - 5 peer-port         Peer port.
        ``port_forwarding_enabled``      1 -                     Enables port forwarding.
        ``queue_stalled_enabled``        14 -                    Enable tracking of stalled transfers.
        ``queue_stalled_minutes``        14 -                    Number of minutes of idle that marks a transfer as stalled.
        ``rename_partial_files``         8 -                     Appends ".part" to incomplete files
        ``script_torrent_done_enabled``  9 -                     Whether or not to call the "done" script.
        ``script_torrent_done_filename`` 9 -                     Filename of the script to run when the transfer is done.
        ``seed_queue_enabled``           14 -                    Enables upload queue.
        ``seed_queue_size``              14 -                    Number of slots in the upload queue.
        ``seedRatioLimit``               5 -                     Seed ratio limit. 1.0 means 1:1 download and upload ratio.
        ``seedRatioLimited``             5 -                     Enables seed ration limit.
        ``speed_limit_down``             1 -                     Download speed limit (in Kib/s).
        ``speed_limit_down_enabled``     1 -                     Enables download speed limiting.
        ``speed_limit_up``               1 -                     Upload speed limit (in Kib/s).
        ``speed_limit_up_enabled``       1 -                     Enables upload speed limiting.
        ``start_added_torrents``         9 -                     Added torrents will be started right away.
        ``trash_original_torrent_files`` 9 -                     The .torrent file of added torrents will be deleted.
        ``utp_enabled``                  13 -                    Enables Micro Transport Protocol (UTP).
        ================================ ===== ================= ==========================================================================================================================

        .. NOTE::
    	   transmissionrpc will try to automatically fix argument errors.
        """
        args = {}
        for key, value in iteritems(kwargs):
            if key == 'encryption' and value not in ['required', 'preferred', 'tolerated']:
                raise ValueError('Invalid encryption value')
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('session-set' , argument, value, self.rpc_version)
            args[arg] = val
        if len(args) > 0:
            self._request('session-set', args, timeout=timeout)

    def blocklist_update(self, timeout=None):
        """Update block list. Returns the size of the block list."""
        self._rpc_version_warning(5)
        result = self._request('blocklist-update', timeout=timeout)
        if 'blocklist-size' in result:
            return result['blocklist-size']
        return None

    def port_test(self, timeout=None):
        """
        Tests to see if your incoming peer port is accessible from the
        outside world.
        """
        self._rpc_version_warning(5)
        result = self._request('port-test', timeout=timeout)
        if 'port-is-open' in result:
            return result['port-is-open']
        return None

    def free_space(self, path, timeout=None):
        """
        Get the ammount of free space (in bytes) at the provided location.
        """
        self._rpc_version_warning(15)
        result = self._request('free-space', {'path': path}, timeout=timeout)
        if result['path'] == path:
            return result['size-bytes']
        return None

    def session_stats(self, timeout=None):
        """Get session statistics"""
        self._request('session-stats', timeout=timeout)
        return self.session

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import logging
from six import iteritems

LOGGER = logging.getLogger('transmissionrpc')
LOGGER.setLevel(logging.ERROR)

def mirror_dict(source):
    """
    Creates a dictionary with all values as keys and all keys as values.
    """
    source.update(dict((value, key) for key, value in iteritems(source)))
    return source

DEFAULT_PORT = 9091

DEFAULT_TIMEOUT = 30.0

TR_PRI_LOW    = -1
TR_PRI_NORMAL =  0
TR_PRI_HIGH   =  1

PRIORITY = mirror_dict({
    'low'    : TR_PRI_LOW,
    'normal' : TR_PRI_NORMAL,
    'high'   : TR_PRI_HIGH
})

TR_RATIOLIMIT_GLOBAL    = 0 # follow the global settings
TR_RATIOLIMIT_SINGLE    = 1 # override the global settings, seeding until a certain ratio
TR_RATIOLIMIT_UNLIMITED = 2 # override the global settings, seeding regardless of ratio

RATIO_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

TR_IDLELIMIT_GLOBAL     = 0 # follow the global settings
TR_IDLELIMIT_SINGLE     = 1 # override the global settings, seeding until a certain idle time
TR_IDLELIMIT_UNLIMITED  = 2 # override the global settings, seeding regardless of activity

IDLE_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

# A note on argument maps
# These maps are used to verify *-set methods. The information is structured in
# a tree.
# set +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |  +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |
# get +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#     +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]

# Arguments for torrent methods
TORRENT_ARGS = {
    'get' : {
        'activityDate':                 ('number', 1, None, None, None, 'Last time of upload or download activity.'),
        'addedDate':                    ('number', 1, None, None, None, 'The date when this torrent was first added.'),
        'announceResponse':             ('string', 1, 7, None, None, 'The announce message from the tracker.'),
        'announceURL':                  ('string', 1, 7, None, None, 'Current announce URL.'),
        'bandwidthPriority':            ('number', 5, None, None, None, 'Bandwidth priority. Low (-1), Normal (0) or High (1).'),
        'comment':                      ('string', 1, None, None, None, 'Torrent comment.'),
        'corruptEver':                  ('number', 1, None, None, None, 'Number of bytes of corrupt data downloaded.'),
        'creator':                      ('string', 1, None, None, None, 'Torrent creator.'),
        'dateCreated':                  ('number', 1, None, None, None, 'Torrent creation date.'),
        'desiredAvailable':             ('number', 1, None, None, None, 'Number of bytes avalable and left to be downloaded.'),
        'doneDate':                     ('number', 1, None, None, None, 'The date when the torrent finished downloading.'),
        'downloadDir':                  ('string', 4, None, None, None, 'The directory path where the torrent is downloaded to.'),
        'downloadedEver':               ('number', 1, None, None, None, 'Number of bytes of good data downloaded.'),
        'downloaders':                  ('number', 4, 7, None, None, 'Number of downloaders.'),
        'downloadLimit':                ('number', 1, None, None, None, 'Download limit in Kbps.'),
        'downloadLimited':              ('boolean', 5, None, None, None, 'Download limit is enabled'),
        'downloadLimitMode':            ('number', 1, 5, None, None, 'Download limit mode. 0 means global, 1 means signle, 2 unlimited.'),
        'error':                        ('number', 1, None, None, None, 'Kind of error. 0 means OK, 1 means tracker warning, 2 means tracker error, 3 means local error.'),
        'errorString':                  ('number', 1, None, None, None, 'Error message.'),
        'eta':                          ('number', 1, None, None, None, 'Estimated number of seconds left when downloading or seeding. -1 means not available and -2 means unknown.'),
        'etaIdle':                      ('number', 15, None, None, None, 'Estimated number of seconds left until the idle time limit is reached. -1 means not available and -2 means unknown.'),        
        'files':                        ('array', 1, None, None, None, 'Array of file object containing key, bytesCompleted, length and name.'),
        'fileStats':                    ('array', 5, None, None, None, 'Aray of file statistics containing bytesCompleted, wanted and priority.'),
        'hashString':                   ('string', 1, None, None, None, 'Hashstring unique for the torrent even between sessions.'),
        'haveUnchecked':                ('number', 1, None, None, None, 'Number of bytes of partial pieces.'),
        'haveValid':                    ('number', 1, None, None, None, 'Number of bytes of checksum verified data.'),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, 'True if session upload limits are honored'),
        'id':                           ('number', 1, None, None, None, 'Session unique torrent id.'),
        'isFinished':                   ('boolean', 9, None, None, None, 'True if the torrent is finished. Downloaded and seeded.'),
        'isPrivate':                    ('boolean', 1, None, None, None, 'True if the torrent is private.'),
        'isStalled':                    ('boolean', 14, None, None, None, 'True if the torrent has stalled (been idle for a long time).'),
        'lastAnnounceTime':             ('number', 1, 7, None, None, 'The time of the last announcement.'),
        'lastScrapeTime':               ('number', 1, 7, None, None, 'The time af the last successful scrape.'),
        'leechers':                     ('number', 1, 7, None, None, 'Number of leechers.'),
        'leftUntilDone':                ('number', 1, None, None, None, 'Number of bytes left until the download is done.'),
        'magnetLink':                   ('string', 7, None, None, None, 'The magnet link for this torrent.'),
        'manualAnnounceTime':           ('number', 1, None, None, None, 'The time until you manually ask for more peers.'),
        'maxConnectedPeers':            ('number', 1, None, None, None, 'Maximum of connected peers.'),
        'metadataPercentComplete':      ('number', 7, None, None, None, 'Download progress of metadata. 0.0 to 1.0.'),
        'name':                         ('string', 1, None, None, None, 'Torrent name.'),
        'nextAnnounceTime':             ('number', 1, 7, None, None, 'Next announce time.'),
        'nextScrapeTime':               ('number', 1, 7, None, None, 'Next scrape time.'),
        'peer-limit':                   ('number', 5, None, None, None, 'Maximum number of peers.'),
        'peers':                        ('array', 2, None, None, None, 'Array of peer objects.'),
        'peersConnected':               ('number', 1, None, None, None, 'Number of peers we are connected to.'),
        'peersFrom':                    ('object', 1, None, None, None, 'Object containing download peers counts for different peer types.'),
        'peersGettingFromUs':           ('number', 1, None, None, None, 'Number of peers we are sending data to.'),
        'peersKnown':                   ('number', 1, 13, None, None, 'Number of peers that the tracker knows.'),
        'peersSendingToUs':             ('number', 1, None, None, None, 'Number of peers sending to us'),
        'percentDone':                  ('double', 5, None, None, None, 'Download progress of selected files. 0.0 to 1.0.'),
        'pieces':                       ('string', 5, None, None, None, 'String with base64 encoded bitfield indicating finished pieces.'),
        'pieceCount':                   ('number', 1, None, None, None, 'Number of pieces.'),
        'pieceSize':                    ('number', 1, None, None, None, 'Number of bytes in a piece.'),
        'priorities':                   ('array', 1, None, None, None, 'Array of file priorities.'),
        'queuePosition':                ('number', 14, None, None, None, 'The queue position.'),
        'rateDownload':                 ('number', 1, None, None, None, 'Download rate in bps.'),
        'rateUpload':                   ('number', 1, None, None, None, 'Upload rate in bps.'),
        'recheckProgress':              ('double', 1, None, None, None, 'Progress of recheck. 0.0 to 1.0.'),
        'secondsDownloading':           ('number', 15, None, None, None, ''),
        'secondsSeeding':               ('number', 15, None, None, None, ''),
        'scrapeResponse':               ('string', 1, 7, None, None, 'Scrape response message.'),
        'scrapeURL':                    ('string', 1, 7, None, None, 'Current scrape URL'),
        'seeders':                      ('number', 1, 7, None, None, 'Number of seeders reported by the tracker.'),
        'seedIdleLimit':                ('number', 10, None, None, None, 'Idle limit in minutes.'),
        'seedIdleMode':                 ('number', 10, None, None, None, 'Use global (0), torrent (1), or unlimited (2) limit.'),
        'seedRatioLimit':               ('double', 5, None, None, None, 'Seed ratio limit.'),
        'seedRatioMode':                ('number', 5, None, None, None, 'Use global (0), torrent (1), or unlimited (2) limit.'),
        'sizeWhenDone':                 ('number', 1, None, None, None, 'Size of the torrent download in bytes.'),
        'startDate':                    ('number', 1, None, None, None, 'The date when the torrent was last started.'),
        'status':                       ('number', 1, None, None, None, 'Current status, see source'),
        'swarmSpeed':                   ('number', 1, 7, None, None, 'Estimated speed in Kbps in the swarm.'),
        'timesCompleted':               ('number', 1, 7, None, None, 'Number of successful downloads reported by the tracker.'),
        'trackers':                     ('array', 1, None, None, None, 'Array of tracker objects.'),
        'trackerStats':                 ('object', 7, None, None, None, 'Array of object containing tracker statistics.'),
        'totalSize':                    ('number', 1, None, None, None, 'Total size of the torrent in bytes'),
        'torrentFile':                  ('string', 5, None, None, None, 'Path to .torrent file.'),
        'uploadedEver':                 ('number', 1, None, None, None, 'Number of bytes uploaded, ever.'),
        'uploadLimit':                  ('number', 1, None, None, None, 'Upload limit in Kbps'),
        'uploadLimitMode':              ('number', 1, 5, None, None, 'Upload limit mode. 0 means global, 1 means signle, 2 unlimited.'),
        'uploadLimited':                ('boolean', 5, None, None, None, 'Upload limit enabled.'),
        'uploadRatio':                  ('double', 1, None, None, None, 'Seed ratio.'),
        'wanted':                       ('array', 1, None, None, None, 'Array of booleans indicated wanted files.'),
        'webseeds':                     ('array', 1, None, None, None, 'Array of webseeds objects'),
        'webseedsSendingToUs':          ('number', 1, None, None, None, 'Number of webseeds seeding to us.'),
    },
    'set': {
        'bandwidthPriority':            ('number', 5, None, None, None, 'Priority for this transfer.'),
        'downloadLimit':                ('number', 5, None, 'speed-limit-down', None, 'Set the speed limit for download in Kib/s.'),
        'downloadLimited':              ('boolean', 5, None, 'speed-limit-down-enabled', None, 'Enable download speed limiter.'),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, "Enables or disables the transfer to honour the upload limit set in the session."),
        'location':                     ('array', 1, None, None, None, 'Local download location.'),
        'peer-limit':                   ('number', 1, None, None, None, 'The peer limit for the torrents.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'queuePosition':                ('number', 14, None, None, None, 'Position of this transfer in its queue.'),
        'seedIdleLimit':                ('number', 10, None, None, None, 'Seed inactivity limit in minutes.'),
        'seedIdleMode':                 ('number', 10, None, None, None, 'Seed inactivity mode. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'seedRatioLimit':               ('double', 5, None, None, None, 'Seeding ratio.'),
        'seedRatioMode':                ('number', 5, None, None, None, 'Which ratio to use. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'speed-limit-down':             ('number', 1, 5, None, 'downloadLimit', 'Set the speed limit for download in Kib/s.'),
        'speed-limit-down-enabled':     ('boolean', 1, 5, None, 'downloadLimited', 'Enable download speed limiter.'),
        'speed-limit-up':               ('number', 1, 5, None, 'uploadLimit', 'Set the speed limit for upload in Kib/s.'),
        'speed-limit-up-enabled':       ('boolean', 1, 5, None, 'uploadLimited', 'Enable upload speed limiter.'),
        'trackerAdd':                   ('array', 10, None, None, None, 'Array of string with announce URLs to add.'),
        'trackerRemove':                ('array', 10, None, None, None, 'Array of ids of trackers to remove.'),
        'trackerReplace':               ('array', 10, None, None, None, 'Array of (id, url) tuples where the announce URL should be replaced.'),
        'uploadLimit':                  ('number', 5, None, 'speed-limit-up', None, 'Set the speed limit for upload in Kib/s.'),
        'uploadLimited':                ('boolean', 5, None, 'speed-limit-up-enabled', None, 'Enable upload speed limiter.'),
    },
    'add': {
        'bandwidthPriority':            ('number', 8, None, None, None, 'Priority for this transfer.'),
        'download-dir':                 ('string', 1, None, None, None, 'The directory where the downloaded contents will be saved in.'),
        'cookies':                      ('string', 13, None, None, None, 'One or more HTTP cookie(s).'),
        'filename':                     ('string', 1, None, None, None, "A file path or URL to a torrent file or a magnet link."),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'metainfo':                     ('string', 1, None, None, None, 'The content of a torrent file, base64 encoded.'),
        'paused':                       ('boolean', 1, None, None, None, 'If True, does not start the transfer when added.'),
        'peer-limit':                   ('number', 1, None, None, None, 'Maximum number of peers allowed.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
    }
}

# Arguments for session methods
SESSION_ARGS = {
    'get': {
        "alt-speed-down":               ('number', 5, None, None, None, 'Alternate session download speed limit (in Kib/s).'),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, 'True if alternate global download speed limiter is ebabled.'),
        "alt-speed-time-begin":         ('number', 5, None, None, None, 'Time when alternate speeds should be enabled. Minutes after midnight.'),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, 'True if alternate speeds scheduling is enabled.'),
        "alt-speed-time-end":           ('number', 5, None, None, None, 'Time when alternate speeds should be disabled. Minutes after midnight.'),
        "alt-speed-time-day":           ('number', 5, None, None, None, 'Days alternate speeds scheduling is enabled.'),
        "alt-speed-up":                 ('number', 5, None, None, None, 'Alternate session upload speed limit (in Kib/s)'),
        "blocklist-enabled":            ('boolean', 5, None, None, None, 'True when blocklist is enabled.'),
        "blocklist-size":               ('number', 5, None, None, None, 'Number of rules in the blocklist'),
        "blocklist-url":                ('string', 11, None, None, None, 'Location of the block list. Updated with blocklist-update.'),
        "cache-size-mb":                ('number', 10, None, None, None, 'The maximum size of the disk cache in MB'),
        "config-dir":                   ('string', 8, None, None, None, 'location of transmissions configuration directory'),
        "dht-enabled":                  ('boolean', 6, None, None, None, 'True if DHT enabled.'),
        "download-dir":                 ('string', 1, None, None, None, 'The download directory.'),
        "download-dir-free-space":      ('number', 12, None, None, None, 'Free space in the download directory, in bytes'),
        "download-queue-size":          ('number', 14, None, None, None, 'Number of slots in the download queue.'),
        "download-queue-enabled":       ('boolean', 14, None, None, None, 'True if the download queue is enabled.'),
        "encryption":                   ('string', 1, None, None, None, 'Encryption mode, one of ``required``, ``preferred`` or ``tolerated``.'),
        "idle-seeding-limit":           ('number', 10, None, None, None, 'Seed inactivity limit in minutes.'),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, 'True if the seed activity limit is enabled.'),
        "incomplete-dir":               ('string', 7, None, None, None, 'The path to the directory for incomplete torrent transfer data.'),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, 'True if the incomplete dir is enabled.'),
        "lpd-enabled":                  ('boolean', 9, None, None, None, 'True if local peer discovery is enabled.'),
        "peer-limit":                   ('number', 1, 5, None, 'peer-limit-global', 'Maximum number of peers.'),
        "peer-limit-global":            ('number', 5, None, 'peer-limit', None, 'Maximum number of peers.'),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, 'Maximum number of peers per transfer.'),
        "pex-allowed":                  ('boolean', 1, 5, None, 'pex-enabled', 'True if PEX is allowed.'),
        "pex-enabled":                  ('boolean', 5, None, 'pex-allowed', None, 'True if PEX is enabled.'),
        "port":                         ('number', 1, 5, None, 'peer-port', 'Peer port.'),
        "peer-port":                    ('number', 5, None, 'port', None, 'Peer port.'),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, 'Enables randomized peer port on start of Transmission.'),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, 'True if port forwarding is enabled.'),
        "queue-stalled-minutes":        ('number', 14, None, None, None, 'Number of minutes of idle that marks a transfer as stalled.'),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, 'True if stalled tracking of transfers is enabled.'),
        "rename-partial-files":         ('boolean', 8, None, None, None, 'True if ".part" is appended to incomplete files'),
        "rpc-version":                  ('number', 4, None, None, None, 'Transmission RPC API Version.'),
        "rpc-version-minimum":          ('number', 4, None, None, None, 'Minimum accepted RPC API Version.'),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, 'True if the done script is enabled.'),
        "script-torrent-done-filename": ('string', 9, None, None, None, 'Filename of the script to run when the transfer is done.'),
        "seedRatioLimit":               ('double', 5, None, None, None, 'Seed ratio limit. 1.0 means 1:1 download and upload ratio.'),
        "seedRatioLimited":             ('boolean', 5, None, None, None, 'True if seed ration limit is enabled.'),
        "seed-queue-size":              ('number', 14, None, None, None, 'Number of slots in the upload queue.'),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, 'True if upload queue is enabled.'),
        "speed-limit-down":             ('number', 1, None, None, None, 'Download speed limit (in Kib/s).'),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, 'True if the download speed is limited.'),
        "speed-limit-up":               ('number', 1, None, None, None, 'Upload speed limit (in Kib/s).'),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, 'True if the upload speed is limited.'),
        "start-added-torrents":         ('boolean', 9, None, None, None, 'When true uploaded torrents will start right away.'),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, 'When true added .torrent files will be deleted.'),
        'units':                        ('object', 10, None, None, None, 'An object containing units for size and speed.'),
        'utp-enabled':                  ('boolean', 13, None, None, None, 'True if Micro Transport Protocol (UTP) is enabled.'),
        "version":                      ('string', 3, None, None, None, 'Transmission version.'),
    },
    'set': {
        "alt-speed-down":               ('number', 5, None, None, None, 'Alternate session download speed limit (in Kib/s).'),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, 'Enables alternate global download speed limiter.'),
        "alt-speed-time-begin":         ('number', 5, None, None, None, 'Time when alternate speeds should be enabled. Minutes after midnight.'),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, 'Enables alternate speeds scheduling.'),
        "alt-speed-time-end":           ('number', 5, None, None, None, 'Time when alternate speeds should be disabled. Minutes after midnight.'),
        "alt-speed-time-day":           ('number', 5, None, None, None, 'Enables alternate speeds scheduling these days.'),
        "alt-speed-up":                 ('number', 5, None, None, None, 'Alternate session upload speed limit (in Kib/s).'),
        "blocklist-enabled":            ('boolean', 5, None, None, None, 'Enables the block list'),
        "blocklist-url":                ('string', 11, None, None, None, 'Location of the block list. Updated with blocklist-update.'),
        "cache-size-mb":                ('number', 10, None, None, None, 'The maximum size of the disk cache in MB'),
        "dht-enabled":                  ('boolean', 6, None, None, None, 'Enables DHT.'),
        "download-dir":                 ('string', 1, None, None, None, 'Set the session download directory.'),
        "download-queue-size":          ('number', 14, None, None, None, 'Number of slots in the download queue.'),
        "download-queue-enabled":       ('boolean', 14, None, None, None, 'Enables download queue.'),
        "encryption":                   ('string', 1, None, None, None, 'Set the session encryption mode, one of ``required``, ``preferred`` or ``tolerated``.'),
        "idle-seeding-limit":           ('number', 10, None, None, None, 'The default seed inactivity limit in minutes.'),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, 'Enables the default seed inactivity limit'),
        "incomplete-dir":               ('string', 7, None, None, None, 'The path to the directory of incomplete transfer data.'),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, 'Enables the incomplete transfer data directory. Otherwise data for incomplete transfers are stored in the download target.'),
        "lpd-enabled":                  ('boolean', 9, None, None, None, 'Enables local peer discovery for public torrents.'),
        "peer-limit":                   ('number', 1, 5, None, 'peer-limit-global', 'Maximum number of peers.'),
        "peer-limit-global":            ('number', 5, None, 'peer-limit', None, 'Maximum number of peers.'),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, 'Maximum number of peers per transfer.'),
        "pex-allowed":                  ('boolean', 1, 5, None, 'pex-enabled', 'Allowing PEX in public torrents.'),
        "pex-enabled":                  ('boolean', 5, None, 'pex-allowed', None, 'Allowing PEX in public torrents.'),
        "port":                         ('number', 1, 5, None, 'peer-port', 'Peer port.'),
        "peer-port":                    ('number', 5, None, 'port', None, 'Peer port.'),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, 'Enables randomized peer port on start of Transmission.'),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, 'Enables port forwarding.'),
        "rename-partial-files":         ('boolean', 8, None, None, None, 'Appends ".part" to incomplete files'),
        "queue-stalled-minutes":        ('number', 14, None, None, None, 'Number of minutes of idle that marks a transfer as stalled.'),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, 'Enable tracking of stalled transfers.'),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, 'Whether or not to call the "done" script.'),
        "script-torrent-done-filename": ('string', 9, None, None, None, 'Filename of the script to run when the transfer is done.'),
        "seed-queue-size":              ('number', 14, None, None, None, 'Number of slots in the upload queue.'),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, 'Enables upload queue.'),
        "seedRatioLimit":               ('double', 5, None, None, None, 'Seed ratio limit. 1.0 means 1:1 download and upload ratio.'),
        "seedRatioLimited":             ('boolean', 5, None, None, None, 'Enables seed ration limit.'),
        "speed-limit-down":             ('number', 1, None, None, None, 'Download speed limit (in Kib/s).'),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, 'Enables download speed limiting.'),
        "speed-limit-up":               ('number', 1, None, None, None, 'Upload speed limit (in Kib/s).'),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, 'Enables upload speed limiting.'),
        "start-added-torrents":         ('boolean', 9, None, None, None, 'Added torrents will be started right away.'),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, 'The .torrent file of added torrents will be deleted.'),
        'utp-enabled':                  ('boolean', 13, None, None, None, 'Enables Micro Transport Protocol (UTP).'),
    },
}

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from six import string_types, integer_types

class TransmissionError(Exception):
    """
	This exception is raised when there has occurred an error related to
	communication with Transmission. It is a subclass of Exception.
    """
    def __init__(self, message='', original=None):
        Exception.__init__(self)
        self.message = message
        self.original = original

    def __str__(self):
        if self.original:
            original_name = type(self.original).__name__
            return '%s Original exception: %s, "%s"' % (self.message, original_name, str(self.original))
        else:
            return self.message

class HTTPHandlerError(Exception):
    """
	This exception is raised when there has occurred an error related to
	the HTTP handler. It is a subclass of Exception.
    """
    def __init__(self, httpurl=None, httpcode=None, httpmsg=None, httpheaders=None, httpdata=None):
        Exception.__init__(self)
        self.url = ''
        self.code = 600
        self.message = ''
        self.headers = {}
        self.data = ''
        if isinstance(httpurl, string_types):
            self.url = httpurl
        if isinstance(httpcode, integer_types):
            self.code = httpcode
        if isinstance(httpmsg, string_types):
            self.message = httpmsg
        if isinstance(httpheaders, dict):
            self.headers = httpheaders
        if isinstance(httpdata, string_types):
            self.data = httpdata

    def __repr__(self):
        return '<HTTPHandlerError %d, %s>' % (self.code, self.message)

    def __str__(self):
        return 'HTTPHandlerError %d: %s' % (self.code, self.message)

    def __unicode__(self):
        return 'HTTPHandlerError %d: %s' % (self.code, self.message)

########NEW FILE########
__FILENAME__ = httphandler
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import sys

from transmissionrpc.error import HTTPHandlerError

from six import PY3

if PY3:
    from urllib.request import Request, build_opener, \
        HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, HTTPDigestAuthHandler
    from urllib.error import HTTPError, URLError
    from http.client import BadStatusLine
else:
    from urllib2 import Request, build_opener, \
        HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, HTTPDigestAuthHandler
    from urllib2 import HTTPError, URLError
    from httplib import BadStatusLine

class HTTPHandler(object):
    """
    Prototype for HTTP handling.
    """
    def set_authentication(self, uri, login, password):
        """
        Transmission use basic authentication in earlier versions and digest
        authentication in later versions.

         * uri, the authentication realm URI.
         * login, the authentication login.
         * password, the authentication password.
        """
        raise NotImplementedError("Bad HTTPHandler, failed to implement set_authentication.")

    def request(self, url, query, headers, timeout):
        """
        Implement a HTTP POST request here.

         * url, The URL to request.
         * query, The query data to send. This is a JSON data string.
         * headers, a dictionary of headers to send.
         * timeout, requested request timeout in seconds.
        """
        raise NotImplementedError("Bad HTTPHandler, failed to implement request.")

class DefaultHTTPHandler(HTTPHandler):
    """
    The default HTTP handler provided with transmissionrpc.
    """
    def __init__(self):
        HTTPHandler.__init__(self)
        self.http_opener = build_opener()

    def set_authentication(self, uri, login, password):
        password_manager = HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=uri, user=login, passwd=password)
        self.http_opener = build_opener(HTTPBasicAuthHandler(password_manager), HTTPDigestAuthHandler(password_manager))

    def request(self, url, query, headers, timeout):
        request = Request(url, query.encode('utf-8'), headers)
        try:
            if (sys.version_info[0] == 2 and sys.version_info[1] > 5) or sys.version_info[0] > 2:
                response = self.http_opener.open(request, timeout=timeout)
            else:
                response = self.http_opener.open(request)
        except HTTPError as error:
            if error.fp is None:
                raise HTTPHandlerError(error.filename, error.code, error.msg, dict(error.hdrs))
            else:
                raise HTTPHandlerError(error.filename, error.code, error.msg, dict(error.hdrs), error.read())
        except URLError as error:
            # urllib2.URLError documentation is horrendous!
            # Try to get the tuple arguments of URLError
            if hasattr(error.reason, 'args') and isinstance(error.reason.args, tuple) and len(error.reason.args) == 2:
                raise HTTPHandlerError(httpcode=error.reason.args[0], httpmsg=error.reason.args[1])
            else:
                raise HTTPHandlerError(httpmsg='urllib2.URLError: %s' % (error.reason))
        except BadStatusLine as error:
            raise HTTPHandlerError(httpmsg='httplib.BadStatusLine: %s' % (error.line))
        return response.read().decode('utf-8')

########NEW FILE########
__FILENAME__ = session
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from transmissionrpc.utils import Field

from six import iteritems, integer_types

class Session(object):
    """
    Session is a class holding the session data for a Transmission daemon.

    Access the session field can be done through attributes.
    The attributes available are the same as the session arguments in the
    Transmission RPC specification, but with underscore instead of hyphen.
    ``download-dir`` -> ``download_dir``.
    """

    def __init__(self, client=None, fields=None):
        self._client = client
        self._fields = {}
        if fields is not None:
            self._update_fields(fields)

    def __getattr__(self, name):
        try:
            return self._fields[name].value
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    def __str__(self):
        text = ''
        for key in sorted(self._fields.keys()):
            text += "% 32s: %s\n" % (key[-32:], self._fields[key].value)
        return text

    def _update_fields(self, other):
        """
        Update the session data from a Transmission JSON-RPC arguments dictionary
        """
        if isinstance(other, dict):
            for key, value in iteritems(other):
                self._fields[key.replace('-', '_')] = Field(value, False)
        elif isinstance(other, Session):
            for key in list(other._fields.keys()):
                self._fields[key] = Field(other._fields[key].value, False)
        else:
            raise ValueError('Cannot update with supplied data')

    def _dirty_fields(self):
        """Enumerate changed fields"""
        outgoing_keys = ['peer_port', 'pex_enabled']
        fields = []
        for key in outgoing_keys:
            if key in self._fields and self._fields[key].dirty:
                fields.append(key)
        return fields

    def _push(self):
        """Push changed fields to the server"""
        dirty = self._dirty_fields()
        args = {}
        for key in dirty:
            args[key] = self._fields[key].value
            self._fields[key] = self._fields[key]._replace(dirty=False)
        if len(args) > 0:
            self._client.set_session(**args)

    def update(self, timeout=None):
        """Update the session information."""
        self._push()
        session = self._client.get_session(timeout=timeout)
        self._update_fields(session)
        session = self._client.session_stats(timeout=timeout)
        self._update_fields(session)

    def from_request(self, data):
        """Update the session information."""
        self._update_fields(data)

    def _get_peer_port(self):
        """
        Get the peer port.
        """
        return self._fields['peer_port'].value

    def _set_peer_port(self, port):
        """
        Set the peer port.
        """
        if isinstance(port, integer_types):
            self._fields['peer_port'] = Field(port, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    peer_port = property(_get_peer_port, _set_peer_port, None, "Peer port. This is a mutator.")

    def _get_pex_enabled(self):
        """Is peer exchange enabled?"""
        return self._fields['pex_enabled'].value

    def _set_pex_enabled(self, enabled):
        """Enable/disable peer exchange."""
        if isinstance(enabled, bool):
            self._fields['pex_enabled'] = Field(enabled, True)
            self._push()
        else:
            raise TypeError("Not a valid type")

    pex_enabled = property(_get_pex_enabled, _set_pex_enabled, None, "Enable peer exchange. This is a mutator.")

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.4.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")



class Module_six_moves_urllib_parse(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")
sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib.parse")


class Module_six_moves_urllib_error(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib_error")
sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib_request")
sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib_response")
sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib_robotparser")
sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = torrent
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import sys, datetime

from transmissionrpc.constants import PRIORITY, RATIO_LIMIT, IDLE_LIMIT
from transmissionrpc.utils import Field, format_timedelta

from six import integer_types, string_types, text_type, iteritems


def get_status_old(code):
    """Get the torrent status using old status codes"""
    mapping = {
        (1<<0): 'check pending',
        (1<<1): 'checking',
        (1<<2): 'downloading',
        (1<<3): 'seeding',
        (1<<4): 'stopped',
    }
    return mapping[code]

def get_status_new(code):
    """Get the torrent status using new status codes"""
    mapping = {
        0: 'stopped',
        1: 'check pending',
        2: 'checking',
        3: 'download pending',
        4: 'downloading',
        5: 'seed pending',
        6: 'seeding',
    }
    return mapping[code]

class Torrent(object):
    """
    Torrent is a class holding the data received from Transmission regarding a bittorrent transfer.

    All fetched torrent fields are accessible through this class using attributes.
    This class has a few convenience properties using the torrent data.
    """

    def __init__(self, client, fields):
        if 'id' not in fields:
            raise ValueError('Torrent requires an id')
        self._fields = {}
        self._update_fields(fields)
        self._incoming_pending = False
        self._outgoing_pending = False
        self._client = client

    def _get_name_string(self, codec=None):
        """Get the name"""
        if codec is None:
            codec = sys.getdefaultencoding()
        name = None
        # try to find name
        if 'name' in self._fields:
            name = self._fields['name'].value
        # if name is unicode, try to decode
        if isinstance(name, text_type):
            try:
                name = name.encode(codec)
            except UnicodeError:
                name = None
        return name

    def __repr__(self):
        tid = self._fields['id'].value
        name = self._get_name_string()
        if isinstance(name, str):
            return '<Torrent %d \"%s\">' % (tid, name)
        else:
            return '<Torrent %d>' % (tid)

    def __str__(self):
        name = self._get_name_string()
        if isinstance(name, str):
            return 'Torrent \"%s\"' % (name)
        else:
            return 'Torrent'

    def __copy__(self):
        return Torrent(self._client, self._fields)

    def __getattr__(self, name):
        try:
            return self._fields[name].value
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    def _rpc_version(self):
        """Get the Transmission RPC API version."""
        if self._client:
            return self._client.rpc_version
        return 2

    def _dirty_fields(self):
        """Enumerate changed fields"""
        outgoing_keys = ['bandwidthPriority', 'downloadLimit', 'downloadLimited', 'peer_limit', 'queuePosition'
            , 'seedIdleLimit', 'seedIdleMode', 'seedRatioLimit', 'seedRatioMode', 'uploadLimit', 'uploadLimited']
        fields = []
        for key in outgoing_keys:
            if key in self._fields and self._fields[key].dirty:
                fields.append(key)
        return fields

    def _push(self):
        """Push changed fields to the server"""
        dirty = self._dirty_fields()
        args = {}
        for key in dirty:
            args[key] = self._fields[key].value
            self._fields[key] = self._fields[key]._replace(dirty=False)
        if len(args) > 0:
            self._client.change_torrent(self.id, **args)

    def _update_fields(self, other):
        """
        Update the torrent data from a Transmission JSON-RPC arguments dictionary
        """
        fields = None
        if isinstance(other, dict):
            for key, value in iteritems(other):
                self._fields[key.replace('-', '_')] = Field(value, False)
        elif isinstance(other, Torrent):
            for key in list(other._fields.keys()):
                self._fields[key] = Field(other._fields[key].value, False)
        else:
            raise ValueError('Cannot update with supplied data')
        self._incoming_pending = False
    
    def _status(self):
        """Get the torrent status"""
        code = self._fields['status'].value
        if self._rpc_version() >= 14:
            return get_status_new(code)
        else:
            return get_status_old(code)

    def files(self):
        """
        Get list of files for this torrent.

        This function returns a dictionary with file information for each file.
        The file information is has following fields:
        ::

            {
                <file id>: {
                    'name': <file name>,
                    'size': <file size in bytes>,
                    'completed': <bytes completed>,
                    'priority': <priority ('high'|'normal'|'low')>,
                    'selected': <selected for download>
                }
                ...
            }
        """
        result = {}
        if 'files' in self._fields:
            files = self._fields['files'].value
            indices = range(len(files))
            priorities = self._fields['priorities'].value
            wanted = self._fields['wanted'].value
            for item in zip(indices, files, priorities, wanted):
                selected = True if item[3] else False
                priority = PRIORITY[item[2]]
                result[item[0]] = {
                    'selected': selected,
                    'priority': priority,
                    'size': item[1]['length'],
                    'name': item[1]['name'],
                    'completed': item[1]['bytesCompleted']}
        return result

    @property
    def status(self):
        """
        Returns the torrent status. Is either one of 'check pending', 'checking',
        'downloading', 'seeding' or 'stopped'. The first two is related to
        verification.
        """
        return self._status()

    @property
    def progress(self):
        """Get the download progress in percent."""
        try:
            size = self._fields['sizeWhenDone'].value
            left = self._fields['leftUntilDone'].value
            return 100.0 * (size - left) / float(size)
        except ZeroDivisionError:
            return 0.0

    @property
    def ratio(self):
        """Get the upload/download ratio."""
        return float(self._fields['uploadRatio'].value)

    @property
    def eta(self):
        """Get the "eta" as datetime.timedelta."""
        eta = self._fields['eta'].value
        if eta >= 0:
            return datetime.timedelta(seconds=eta)
        else:
            raise ValueError('eta not valid')

    @property
    def date_active(self):
        """Get the attribute "activityDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['activityDate'].value)

    @property
    def date_added(self):
        """Get the attribute "addedDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['addedDate'].value)

    @property
    def date_started(self):
        """Get the attribute "startDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['startDate'].value)

    @property
    def date_done(self):
        """Get the attribute "doneDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['doneDate'].value)

    def format_eta(self):
        """
        Returns the attribute *eta* formatted as a string.

        * If eta is -1 the result is 'not available'
        * If eta is -2 the result is 'unknown'
        * Otherwise eta is formatted as <days> <hours>:<minutes>:<seconds>.
        """
        eta = self._fields['eta'].value
        if eta == -1:
            return 'not available'
        elif eta == -2:
            return 'unknown'
        else:
            return format_timedelta(self.eta)

    def _get_download_limit(self):
        """
        Get the download limit.
        Can be a number or None.
        """
        if self._fields['downloadLimited'].value:
            return self._fields['downloadLimit'].value
        else:
            return None

    def _set_download_limit(self, limit):
        """
        Get the download limit.
        Can be a number, 'session' or None.
        """
        if isinstance(limit, integer_types):
            self._fields['downloadLimited'] = Field(True, True)
            self._fields['downloadLimit'] = Field(limit, True)
            self._push()
        elif limit == None:
            self._fields['downloadLimited'] = Field(False, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    download_limit = property(_get_download_limit, _set_download_limit, None, "Download limit in Kbps or None. This is a mutator.")

    def _get_peer_limit(self):
        """
        Get the peer limit.
        """
        return self._fields['peer_limit'].value

    def _set_peer_limit(self, limit):
        """
        Set the peer limit.
        """
        if isinstance(limit, integer_types):
            self._fields['peer_limit'] = Field(limit, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    peer_limit = property(_get_peer_limit, _set_peer_limit, None, "Peer limit. This is a mutator.")

    def _get_priority(self):
        """
        Get the priority as string.
        Can be one of 'low', 'normal', 'high'.
        """
        return PRIORITY[self._fields['bandwidthPriority'].value]

    def _set_priority(self, priority):
        """
        Set the priority as string.
        Can be one of 'low', 'normal', 'high'.
        """
        if isinstance(priority, string_types):
            self._fields['bandwidthPriority'] = Field(PRIORITY[priority], True)
            self._push()

    priority = property(_get_priority, _set_priority, None
        , "Bandwidth priority as string. Can be one of 'low', 'normal', 'high'. This is a mutator.")

    def _get_seed_idle_limit(self):
        """
        Get the seed idle limit in minutes.
        """
        return self._fields['seedIdleLimit'].value

    def _set_seed_idle_limit(self, limit):
        """
        Set the seed idle limit in minutes.
        """
        if isinstance(limit, integer_types):
            self._fields['seedIdleLimit'] = Field(limit, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_idle_limit = property(_get_seed_idle_limit, _set_seed_idle_limit, None
        , "Torrent seed idle limit in minutes. Also see seed_idle_mode. This is a mutator.")

    def _get_seed_idle_mode(self):
        """
        Get the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        return IDLE_LIMIT[self._fields['seedIdleMode'].value]

    def _set_seed_idle_mode(self, mode):
        """
        Set the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        if isinstance(mode, str):
            self._fields['seedIdleMode'] = Field(IDLE_LIMIT[mode], True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_idle_mode = property(_get_seed_idle_mode, _set_seed_idle_mode, None,
        """
        Seed idle mode as string. Can be one of 'global', 'single' or 'unlimited'.

         * global, use session seed idle limit.
         * single, use torrent seed idle limit. See seed_idle_limit.
         * unlimited, no seed idle limit.

        This is a mutator.
        """
    )

    def _get_seed_ratio_limit(self):
        """
        Get the seed ratio limit as float.
        """
        return float(self._fields['seedRatioLimit'].value)

    def _set_seed_ratio_limit(self, limit):
        """
        Set the seed ratio limit as float.
        """
        if isinstance(limit, (integer_types, float)) and limit >= 0.0:
            self._fields['seedRatioLimit'] = Field(float(limit), True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_ratio_limit = property(_get_seed_ratio_limit, _set_seed_ratio_limit, None
        , "Torrent seed ratio limit as float. Also see seed_ratio_mode. This is a mutator.")

    def _get_seed_ratio_mode(self):
        """
        Get the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        return RATIO_LIMIT[self._fields['seedRatioMode'].value]

    def _set_seed_ratio_mode(self, mode):
        """
        Set the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        if isinstance(mode, str):
            self._fields['seedRatioMode'] = Field(RATIO_LIMIT[mode], True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_ratio_mode = property(_get_seed_ratio_mode, _set_seed_ratio_mode, None,
        """
        Seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.

         * global, use session seed ratio limit.
         * single, use torrent seed ratio limit. See seed_ratio_limit.
         * unlimited, no seed ratio limit.

        This is a mutator.
        """
    )

    def _get_upload_limit(self):
        """
        Get the upload limit.
        Can be a number or None.
        """
        if self._fields['uploadLimited'].value:
            return self._fields['uploadLimit'].value
        else:
            return None

    def _set_upload_limit(self, limit):
        """
        Set the upload limit.
        Can be a number, 'session' or None.
        """
        if isinstance(limit, integer_types):
            self._fields['uploadLimited'] = Field(True, True)
            self._fields['uploadLimit'] = Field(limit, True)
            self._push()
        elif limit == None:
            self._fields['uploadLimited'] = Field(False, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    upload_limit = property(_get_upload_limit, _set_upload_limit, None, "Upload limit in Kbps or None. This is a mutator.")

    def _get_queue_position(self):
        """Get the queue position for this torrent."""
        if self._rpc_version() >= 14:
            return self._fields['queuePosition'].value
        else:
            return 0

    def _set_queue_position(self, position):
        """Set the queue position for this torrent."""
        if self._rpc_version() >= 14:
            if isinstance(position, integer_types):
                self._fields['queuePosition'] = Field(position, True)
                self._push()
            else:
                raise ValueError("Not a valid position")
        else:
            pass

    queue_position = property(_get_queue_position, _set_queue_position, None, "Queue position")

    def update(self, timeout=None):
        """Update the torrent information."""
        self._push()
        torrent = self._client.get_torrent(self.id, timeout=timeout)
        self._update_fields(torrent)

    def start(self, bypass_queue=False, timeout=None):
        """
        Start the torrent.
        """
        self._incoming_pending = True
        self._client.start_torrent(self.id, bypass_queue=bypass_queue, timeout=timeout)

    def stop(self, timeout=None):
        """Stop the torrent."""
        self._incoming_pending = True
        self._client.stop_torrent(self.id, timeout=timeout)

    def move_data(self, location, timeout=None):
        """Move torrent data to location."""
        self._incoming_pending = True
        self._client.move_torrent_data(self.id, location, timeout=timeout)

    def locate_data(self, location, timeout=None):
        """Locate torrent data at location."""
        self._incoming_pending = True
        self._client.locate_torrent_data(self.id, location, timeout=timeout)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import socket, datetime, logging
from collections import namedtuple
import transmissionrpc.constants as constants
from transmissionrpc.constants import LOGGER

from six import string_types, iteritems

UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']

def format_size(size):
    """
    Format byte size into IEC prefixes, B, KiB, MiB ...
    """
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(UNITS):
        i += 1
        size /= 1024.0
    return (size, UNITS[i])

def format_speed(size):
    """
    Format bytes per second speed into IEC prefixes, B/s, KiB/s, MiB/s ...
    """
    (size, unit) = format_size(size)
    return (size, unit + '/s')

def format_timedelta(delta):
    """
    Format datetime.timedelta into <days> <hours>:<minutes>:<seconds>.
    """
    minutes, seconds = divmod(delta.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return '%d %02d:%02d:%02d' % (delta.days, hours, minutes, seconds)

def format_timestamp(timestamp, utc=False):
    """
    Format unix timestamp into ISO date format.
    """
    if timestamp > 0:
        if utc:
            dt_timestamp = datetime.datetime.utcfromtimestamp(timestamp)
        else:
            dt_timestamp = datetime.datetime.fromtimestamp(timestamp)
        return dt_timestamp.isoformat(' ')
    else:
        return '-'

class INetAddressError(Exception):
    """
    Error parsing / generating a internet address.
    """
    pass

def inet_address(address, default_port, default_address='localhost'):
    """
    Parse internet address.
    """
    addr = address.split(':')
    if len(addr) == 1:
        try:
            port = int(addr[0])
            addr = default_address
        except ValueError:
            addr = addr[0]
            port = default_port
    elif len(addr) == 2:
        try:
            port = int(addr[1])
        except ValueError:
            raise INetAddressError('Invalid address "%s".' % address)
        if len(addr[0]) == 0:
            addr = default_address
        else:
            addr = addr[0]
    else:
        raise INetAddressError('Invalid address "%s".' % address)
    try:
        socket.getaddrinfo(addr, port, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror:
        raise INetAddressError('Cannot look up address "%s".' % address)
    return (addr, port)

def rpc_bool(arg):
    """
    Convert between Python boolean and Transmission RPC boolean.
    """
    if isinstance(arg, string_types):
        try:
            arg = bool(int(arg))
        except ValueError:
            arg = arg.lower() in ['true', 'yes']
    return 1 if bool(arg) else 0

TR_TYPE_MAP = {
    'number' : int,
    'string' : str,
    'double': float,
    'boolean' : rpc_bool,
    'array': list,
    'object': dict
}

def make_python_name(name):
    """
    Convert Transmission RPC name to python compatible name.
    """
    return name.replace('-', '_')

def make_rpc_name(name):
    """
    Convert python compatible name to Transmission RPC name.
    """
    return name.replace('_', '-')

def argument_value_convert(method, argument, value, rpc_version):
    """
    Check and fix Transmission RPC issues with regards to methods, arguments and values.
    """
    if method in ('torrent-add', 'torrent-get', 'torrent-set'):
        args = constants.TORRENT_ARGS[method[-3:]]
    elif method in ('session-get', 'session-set'):
        args = constants.SESSION_ARGS[method[-3:]]
    else:
        return ValueError('Method "%s" not supported' % (method))
    if argument in args:
        info = args[argument]
        invalid_version = True
        while invalid_version:
            invalid_version = False
            replacement = None
            if rpc_version < info[1]:
                invalid_version = True
                replacement = info[3]
            if info[2] and info[2] <= rpc_version:
                invalid_version = True
                replacement = info[4]
            if invalid_version:
                if replacement:
                    LOGGER.warning(
                        'Replacing requested argument "%s" with "%s".'
                        % (argument, replacement))
                    argument = replacement
                    info = args[argument]
                else:
                    raise ValueError(
                        'Method "%s" Argument "%s" does not exist in version %d.'
                        % (method, argument, rpc_version))
        return (argument, TR_TYPE_MAP[info[0]](value))
    else:
        raise ValueError('Argument "%s" does not exists for method "%s".',
                         (argument, method))

def get_arguments(method, rpc_version):
    """
    Get arguments for method in specified Transmission RPC version.
    """
    if method in ('torrent-add', 'torrent-get', 'torrent-set'):
        args = constants.TORRENT_ARGS[method[-3:]]
    elif method in ('session-get', 'session-set'):
        args = constants.SESSION_ARGS[method[-3:]]
    else:
        return ValueError('Method "%s" not supported' % (method))
    accessible = []
    for argument, info in iteritems(args):
        valid_version = True
        if rpc_version < info[1]:
            valid_version = False
        if info[2] and info[2] <= rpc_version:
            valid_version = False
        if valid_version:
            accessible.append(argument)
    return accessible

def add_stdout_logger(level='debug'):
    """
    Add a stdout target for the transmissionrpc logging.
    """
    levels = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR}

    trpc_logger = logging.getLogger('transmissionrpc')
    loghandler = logging.StreamHandler()
    if level in list(levels.keys()):
        loglevel = levels[level]
        trpc_logger.setLevel(loglevel)
        loghandler.setLevel(loglevel)
    trpc_logger.addHandler(loghandler)

def add_file_logger(filepath, level='debug'):
    """
    Add a stdout target for the transmissionrpc logging.
    """
    levels = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR}

    trpc_logger = logging.getLogger('transmissionrpc')
    loghandler = logging.FileHandler(filepath, encoding='utf-8')
    if level in list(levels.keys()):
        loglevel = levels[level]
        trpc_logger.setLevel(loglevel)
        loghandler.setLevel(loglevel)
    trpc_logger.addHandler(loghandler)

Field = namedtuple('Field', ['value', 'dirty'])

########NEW FILE########
__FILENAME__ = client
#coding=utf8
import urllib
import urllib2
import urlparse
import cookielib
import re
import StringIO
try:
    import json 
except ImportError:
    import simplejson as json

from upload import MultiPartForm

class UTorrentClient(object):

    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.opener = self._make_opener('uTorrent', base_url, username, password)
        self.token = self._get_token()
        #TODO refresh token, when necessary

    def _make_opener(self, realm, base_url, username, password):
        '''uTorrent API need HTTP Basic Auth and cookie support for token verify.'''

        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm=realm,
                                  uri=base_url,
                                  user=username,
                                  passwd=password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)     

        cookie_jar = cookielib.CookieJar()
        cookie_handler = urllib2.HTTPCookieProcessor(cookie_jar)

        handlers = [auth_handler, cookie_handler]
        opener = urllib2.build_opener(*handlers)
        return opener

    def _get_token(self):
        url = urlparse.urljoin(self.base_url, 'token.html')
        response = self.opener.open(url)
        token_re = "<div id='token' style='display:none;'>([^<>]+)</div>"
        match = re.search(token_re, response.read())
        return match.group(1)

       
    def list(self, **kwargs):
        params = [('list', '1')]
        params += kwargs.items()
        return self._action(params)

    def start(self, *hashes):
        params = [('action', 'start'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
        
    def stop(self, *hashes):
        params = [('action', 'stop'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
 
    def pause(self, *hashes):
        params = [('action', 'pause'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
 
    def forcestart(self, *hashes):
        params = [('action', 'forcestart'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
        
    def remove(self, *hashes):
        params = [('action', 'remove'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
    
    def removedata(self, *hashes):
        params = [('action', 'removedata'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
        
    def recheck(self, *hashes):
        params = [('action', 'recheck'),]
        for hash in hashes:
            params.append(('hash', hash))
        return self._action(params)
 
    def getfiles(self, hash):
        params = [('action', 'getfiles'), ('hash', hash)]
        return self._action(params)
 
    def getprops(self, hash):
        params = [('action', 'getprops'), ('hash', hash)]
        return self._action(params)
        
    def setprio(self, hash, priority, *files):
        params = [('action', 'setprio'), ('hash', hash), ('p', str(priority))]
        for file_index in files:
            params.append(('f', str(file_index)))

        return self._action(params)
        
    def addfile(self, filename, filepath=None, bytes=None):
        params = [('action', 'add-file')]

        form = MultiPartForm()
        if filepath is not None:
            file_handler = open(filepath)
        else:
            file_handler = StringIO.StringIO(bytes)
            
        form.add_file('torrent_file', filename.encode('utf-8'), file_handler)

        return self._action(params, str(form), form.get_content_type())

    def _action(self, params, body=None, content_type=None):
        #about token, see https://github.com/bittorrent/webui/wiki/TokenSystem
        url = self.base_url + '?token=' + self.token + '&' + urllib.urlencode(params)
        request = urllib2.Request(url)

        if body:
            request.add_data(body)
            request.add_header('Content-length', len(body))
        if content_type:
            request.add_header('Content-type', content_type)

        try:
            response = self.opener.open(request)
            return response.code, json.loads(response.read())
        except urllib2.HTTPError,e:
            raise 
        

########NEW FILE########
__FILENAME__ = upload
#code copied from http://www.doughellmann.com/PyMOTW/urllib2/

import itertools
import mimetools
import mimetypes
from cStringIO import StringIO
import urllib
import urllib2

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return
    
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return
    
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

########NEW FILE########
