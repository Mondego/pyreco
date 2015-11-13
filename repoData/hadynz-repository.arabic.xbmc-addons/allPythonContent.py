__FILENAME__ = addons_xml_generator
""" downloaded from http://xbmc-addons.googlecode.com/svn/addons/ """
""" addons.xml generator """

import os
import md5


class Generator:
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from the root of
        the checked-out repo. Only handles single depth folder structure.
    """
    def __init__( self ):
        # generate files
        self._generate_addons_file()
        self._generate_md5_file()
        # notify user
        print "Finished updating addons xml and md5 files"

    def _generate_addons_file( self ):
        # addon list
        addons = os.listdir( "." )
        # final addons text
        addons_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n"
        # loop thru and add each addons addon.xml file
        for addon in addons:
            try:
                # skip any file or .git folder
                if ( not os.path.isdir( addon ) or addon == ".git" ): continue
                # create path
                _path = os.path.join( addon, "addon.xml" )
                # split lines for stripping
                xml_lines = open( _path, "r" ).read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if ( line.find( "<?xml" ) >= 0 ): continue
                    # add line
                    addon_xml += unicode( line.rstrip() + "\n", "utf-8" )
                    # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception, e:
                # missing or poorly formatted addon.xml
                print "Excluding %s for %s" % ( _path, e, )
            # clean and add closing tag
        addons_xml = addons_xml.strip() + u"\n</addons>\n"
        # save file
        self._save_file( addons_xml.encode( "utf-8" ), file="addons.xml" )

    def _generate_md5_file( self ):
        try:
            # create a new md5 hash
            m = md5.new( open( "addons.xml" ).read() ).hexdigest()
            # save file
            self._save_file( m, file="addons.xml.md5" )
        except Exception, e:
            # oops
            print "An error occurred creating addons.xml.md5 file!\n%s" % ( e, )

    def _save_file( self, data, file ):
        try:
            # write data to the file
            open( file, "w" ).write( data )
        except Exception, e:
            # oops
            print "An error occurred saving %s file!\n%s" % ( file, e, )


if ( __name__ == "__main__" ):
    # start
    Generator()
########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/3alshasha
# Version 1.0.2
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "3alshasha"

# Entry point
def run():
    plugintools.log("3alshasha.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("3alshasha.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib,itertools

import time


__settings__ = xbmcaddon.Addon(id='plugin.video.alarab')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'http://wadeni.com/images/icons/0alarab-net.jpg'))
	addDir('مسلسلات عربية','http://tv1.alarab.net/view-1_%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9_8',1,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('افلام عربية','http://tv1.alarab.net/view-1_%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9_1',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('افلام كرتون','http://tv1.alarab.net/view-1_%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D9%83%D8%B1%D8%AA%D9%88%D9%86_295',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('فيديو كليب','http://tv1.alarab.net/view-1_%D9%81%D9%8A%D8%AF%D9%8A%D9%88-%D9%83%D9%84%D9%8A%D8%A8_10',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('برامج تلفزيون','http://tv1.alarab.net/view-1_%D8%A8%D8%B1%D8%A7%D9%85%D8%AC-%D8%AA%D9%84%D9%81%D8%B2%D9%8A%D9%88%D9%86_311',1,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('مسلسلات كرتون','http://tv1.alarab.net/view-1_%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D9%83%D8%B1%D8%AA%D9%88%D9%86_4',1,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('مسلسلات تركية','http://tv1.alarab.net/view-1_%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%AA%D8%B1%D9%83%D9%8A%D8%A9_299',1,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('مسلسلات اجنبية','http://tv1.alarab.net/view-1_%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A%D8%A9_1951',1,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('افلام هندية','http://tv1.alarab.net/view-1_افلام-هندية_297',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('افلام اجنبية','http://tv1.alarab.net/view-1_%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A%D8%A9_5553',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('مقاطع مضحكة ','http://tv1.alarab.net/view-1_%D9%85%D9%82%D8%A7%D8%B7%D8%B9-%D9%85%D8%B6%D8%AD%D9%83%D8%A9_309',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	addDir('مسرحيات','http://tv1.alarab.net/view-1_%D9%85%D8%B3%D8%B1%D8%AD%D9%8A%D8%A7%D8%AA_313',4,'http://www.alfnnews.com/files/pic/2012/5/19/2012561916144-alarb.gif')
	
	
	
	
def checkURL(url):
    p = urlparse(url)
    h = HTTP(p[1])
    h.putrequest('HEAD', p[2])
    h.endheaders()
    if h.getreply()[0] == 200: return 1
    else: return 0


def index_series(url):
	try:
		url_mod=url
		url_mod=url_mod.split("_")
		
		for items in url_mod:
			mooded= str( url_mod[0]).split("-")
			for elements in mooded:
				second= mooded[0]
				first= mooded[1]
		
		for i in range(1,20):
		
			result_url=second+"-"+str(i)+"_"+url_mod[1]+"_"+url_mod[2]
			req = urllib2.Request(result_url)
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			url_ch=(re.compile('<img src="(.+?)" alt="(.+?)"  />').findall(link))
			url_ch_2=(re.compile('<a href="(.+?)" title="').findall(link))
			final_series=[]
			response.close()
			for items in url_ch_2:
				if "series" in items:
					if items not in final_series:
						final_series.append(items)
			for items,elements in itertools.izip(url_ch,final_series):
				image= items[0]
				name= items [1]
				url_serie=elements
				#print name
				#print "http://tv1.alarab.net"+url_serie
				addDir(name,"http://tv1.alarab.net"+str(url_serie),2,image)
	except Exception:
		print "Exception in index_series "

def list_eposodes(url):
    try:
		for counter in range(1,8):
			req = urllib2.Request(url+"_"+str(counter))
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			url_ch=(re.compile('<a href="(.+?)" title="(.+?)" class="vd_title">').findall(link))
			response.close()
			item_list=[]
			for items in url_ch:
				for element in items:
					if items[1] not in item_list:
						
						name= str(items[1])
						name=name.replace("تحميل", "")
						name=name.replace("مسلسل", "")
						name=name.replace("مدبلجة", "")
						name=name.replace("مدبلجة", "")
						name=name.replace("بالعربية", "")
						name=name.replace("لاين", "")
						name=name.replace("كاملة", "")
						name=name.replace("مدبلجة", "")
						name=name.replace("مترجم", "")
						name=name.replace("فيلم", "")
						name=name.replace("dvd", "")
						name=name.replace("لابن", "")
						name=name.replace("مشاهدة", "")
						name=name.replace("اونلاين", "")
						name=name.replace("بجودة", "")
						name=name.replace("عالية", "")
						name=name.replace("مباشرة", "")
						name=name.replace("على", "")
						name=name.replace("العرب", "")
						name=name.replace("تحميل", "")
						name=name.replace("جودة", "")
						name=name.replace("كامل", "")
						name=name.replace("بدون", "")
						name=name.replace("اون", "")
						name=name.replace("كواليتي", "")
						name=name.strip()
						
						#print name
						#print items[0]
						addLink(name,"http://tv1.alarab.net"+str(items[0]),3,"")
						item_list.append(items[1])
    except Exception:
		print "Exception in list_epos "
					
def list_films(url):
	try:
		url_mod=url
		url_mod=url_mod.split("_")
		
		for items in url_mod:
			mooded= str( url_mod[0]).split("-")
			for elements in mooded:
				second= mooded[0]
				first= mooded[1]
		
		for i in range(1,20):
		
			result_url=second+"-"+str(i)+"_"+url_mod[1]+"_"+url_mod[2]
			req = urllib2.Request(result_url)
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			response.close()
			url_ch=(re.compile('<a href="(.+?)" title="(.+?)dvd اونلاين "').findall(link))
			print url_ch
			url_ch_2=(re.compile('<img src="(.+?)" alt="(.+?)"  />').findall(link))
			 
			for items,elements in itertools.izip( url_ch,url_ch_2):
				
				name=str( items[1]).replace("جودة", "")
				name=name.replace("مشاهدة", "").strip()
				name=name.replace("dvd", "")
				name=name.replace("فيلم", "")
				name=name.replace("لاين", "")
				name=name.replace("اون", "")
				name=name.replace("اونلاين", "")
				name=name.replace("بجودة", "")
				name=name.replace("عالية", "")
				name=name.replace("مباشرة", "")
				name=name.replace("على", "")
				name=name.replace("العرب", "")
				name=name.replace("تحميل", "")
				name=name.replace("جودة", "")
				name=name.replace("كواليتي", "")
				name=name.replace("بدون", "")
				name=name.replace("كامل", "")
				name=name.strip()
				addLink(name,"http://tv1.alarab.net"+str(items[0]),3,elements[0])
	except Exception:
		print "Exception in list_films "
	
				

def get_epos_video(url,name):
	try:
		url=str(url).split("_")
    
		tnumber=str( url[0])
		tnumber=tnumber.replace("http://tv1.alarab.net/viewVedio/","")
		tnumber=tnumber.replace("http://tv1.alarab.net/v", "")
		tnumber=tnumber.replace("-", "").strip()
		tnumber="http://alarabplayers.alarab.net/test.php?vid="+tnumber
		
		req = urllib2.Request(tnumber)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		
		response.close()
		url_ch=(re.compile("'file': '(.+?)',").findall(link))
		url_ch=str(url_ch).replace("['", "")
		video=str(url_ch).replace("']", "").strip()
		
		image=(re.compile("'image': '(.+?)',").findall(link))
		image=str(image).replace("['", "")
		image=str(image).replace("']", "").strip()
		
		if "www.youtube" in video:
			video=video.split("v=")
			print "youtube after split: "+str(video)
			video_id=str(video[1])
			video_id=video_id.replace(".flv","").strip()
			print "first item of youtube: "+str(video_id)
			playback_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % video_id 
			
			listItem = xbmcgui.ListItem(path=str(playback_url))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
			
			
		else:
			video = str(video)+'|Referer=http://alarabplayers.alarab.net/jwplayer/player.swf'
			listItem = xbmcgui.ListItem(path=video)
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
			
	except Exception:
		print "Exception in get_epos_video "
			
	

	
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLinkOLD(name,url,iconimage):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
        return ok

def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	
def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        index_series(url)
	
elif mode==2:
        print ""+url
        list_eposodes(url)
elif mode==3:
		get_epos_video(url,name)
elif mode==4:
		list_films(url)

	

xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin
import urllib2, urllib, cgi, re
import HTMLParser
import xbmcaddon
import traceback
import os
import sys
import json

addon_id = 'plugin.video.albernameg'
__settings__ = xbmcaddon.Addon(id=addon_id)
__addonname__ = __settings__.getAddonInfo('name')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')

selfAddon = xbmcaddon.Addon(id=addon_id)
addonPath = xbmcaddon.Addon().getAddonInfo("path")
addonArt = os.path.join(addonPath, 'resources/images')
communityStreamPath = os.path.join(addonPath, 'resources/community')

mainurl = 'http://www.albernameg.com/'
apikey = 'AIzaSyBI4me7Tk-7MU5AwLEXUqJXoB24TvUtRcU'




def addDir(name, url, mode, iconimage, showContext=False, isItFolder=True, pageNumber="", isHTML=True,
           addIconForPlaylist=False):
    #	print name
    #	name=name.decode('utf-8','replace')
    if isHTML:
        h = HTMLParser.HTMLParser()
        name = h.unescape(name).decode("utf-8")
        rname = name.encode("utf-8")
    else:
        #h = HTMLParser.HTMLParser()
        #name =h.unescape(name).decode("utf-8")
        rname = name.encode("utf-8")
    #		url=  url.encode("utf-8")
    #	url= url.encode('ascii','ignore')
    #print rname
    #print iconimage
    u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode) + "&name=" + urllib.quote_plus(rname)
    if len(pageNumber):
        u += "&pagenum=" + pageNumber
    if addIconForPlaylist:
        u += "&addIconForPlaylist=yes"
    ok = True
    #	print iconimage
    liz = xbmcgui.ListItem(rname, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    #liz.setInfo( type="Video", infoLabels={ "Title": name } )
    if showContext == True:
        cmd1 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "l3")
        cmd2 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "xdn")
        cmd3 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "ak")
        liz.addContextMenuItems(
            [('Play using L3 Cdn', cmd1), ('Play using XDN Cdn', cmd2), ('Play using AK Cdn', cmd3)])

    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=isItFolder)
    return ok


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param




def PlayYoutube(url):
    uurl = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % url
    xbmc.executebuiltin("xbmc.PlayMedia(" + uurl + ")")


def AddYoutubePlaylists(channelId):
    print 'in AddYoutubePlaylists(channelId)'
    #if not username.startswith('https://www.googleapis'):
    #	channelId=getChannelIdByUserName(username)#passusername
    #else:
    #	channelId=username
    #channelId=username
    playlists, next_page = getYouTubePlayList(channelId);
    for playList in playlists:
        print playList
        addDir(playList[0], playList[1], 3, playList[2], isItFolder=True, isHTML=False)  #name,url,mode,icon
    if next_page:
        addDir('Next', next_page, 2, addonArt + '/next.png', isItFolder=True)  #name,url,mode,icon


def getYouTubePlayList(channelId):
    print 'in getYouTubePlayList(channelId)'
    if not channelId.startswith('https://www.googleapis'):
        u_url = 'https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId=%s&maxResults=50&key=%s' % (
            channelId, apikey)
    else:
        u_url = channelId
    doc = getJson(u_url)
    ret = []
    for playlist_item in doc['items']:
        title = playlist_item["snippet"]["title"]
        id = playlist_item["id"]
        if not title == 'Private video' and type(title) != type(object) and str(title.encode('utf8', 'ignore')).__contains__('كامل'):
            imgurl = ''
            try:
                imgurl = playlist_item["snippet"]["thumbnails"]["high"]["url"]
            except:
                pass
            if imgurl == '':
                try:
                    imgurl = playlist_item["snippet"]["thumbnails"]["default"]["url"]
                except:
                    pass
            ret.append([title, id, imgurl])
    nextItem = None
    if 'nextPageToken' in doc:
        nextItem = doc["nextPageToken"]
    else:
        nextItem = None

    nextUrl = None
    if nextItem:
        if not '&pageToken' in u_url:
            nextUrl = u_url + '&pageToken=' + nextItem
        else:
            nextUrl = u_url.split('&pageToken=')[0] + '&pageToken=' + nextItem

    return ret, nextUrl;


def AddYoutubeVideosByPlaylist(playListId, AddPlayListIcon=False, channelid=None):
    print 'AddYoutube', url
    videos, next_page = getYoutubeVideosByPlaylist(playListId);
    if AddPlayListIcon:
        addDir('Playists', channelid, 2, addonArt + '/playlist.png', isHTML=False)

    for video in videos:
        #print chName
        print video
        addDir(video[0], video[1], 1, video[2], isItFolder=False, isHTML=False)  #name,url,mode,icon
    if next_page:
        addDir('Next', next_page, 3, addonArt + '/next.png', isItFolder=True)  #name,url,mode,icon


def getJson(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent',
                   'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
    response = urllib2.urlopen(req)
    #link=response.read()
    #response.close()
    decoded = json.load(response)
    return decoded


def getChannelIdByUserName(username):
    u_url = 'https://www.googleapis.com/youtube/v3/channels?part=id&forUsername=%s&key=%s' % (username, apikey)
    channelData = getJson(u_url)
    return channelData['items'][0]['id']


def getYoutubeVideosByPlaylist(playlistId):
    if playlistId.startswith('https://www'):
        #nextpage
        u_url = playlistId
    else:
        u_url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId=%s&key=%s' % (
            playlistId, apikey)
    videos = getJson(u_url)
    return prepareYoutubeVideoItems(videos, u_url)


def prepareYoutubeVideoItems(videos, urlUsed):
    print 'urlUsed', urlUsed
    if 'nextPageToken' in videos:
        nextItem = videos["nextPageToken"]
    else:
        nextItem = None
    ret = []
    for playlist_item in videos["items"]:
        title = playlist_item["snippet"]["title"]
        print 'urlUsed', urlUsed
        if not 'search?part=snippet' in urlUsed:
            video_id = playlist_item["snippet"]["resourceId"]["videoId"]
        else:
            video_id = playlist_item["id"]["videoId"]
        if not title == 'Private video':
            imgurl = ''
            try:
                imgurl = playlist_item["snippet"]["thumbnails"]["high"]["url"]
            except:
                pass
            if imgurl == '':
                try:
                    imgurl = playlist_item["snippet"]["thumbnails"]["default"]["url"]
                except:
                    pass
            #print "%s (%s)" % (title, video_id)
            ret.append([title, video_id, imgurl])
    nextUrl = None
    if nextItem:
        if not '&pageToken' in urlUsed:
            nextUrl = urlUsed + '&pageToken=' + nextItem
        else:
            nextUrl = urlUsed.split('&pageToken=')[0] + '&pageToken=' + nextItem
    return ret, nextUrl;

#print "i am here"
params = get_params()
url = None
name = None
mode = None
linkType = None
pageNumber = None

try:
    url = urllib.unquote_plus(params["url"])
except:
    pass
try:
    name = urllib.unquote_plus(params["name"])
except:
    pass
try:
    mode = int(params["mode"])
except:
    pass

try:
    pageNumber = params["pagenum"]
except:
    pageNumber = "";

args = cgi.parse_qs(sys.argv[2][1:])
cdnType = ''
try:
    cdnType = args.get('cdnType', '')[0]
except:
    pass

addIconForPlaylist = ""
try:
    addIconForPlaylist = args.get('addIconForPlaylist', '')[0]
except:
    pass

print    mode, pageNumber

try:
    if mode == None or url == None or len(url) < 1:
        print "Entered Get channel and add playlists"
        chId = getChannelIdByUserName('albernameg')
        AddYoutubePlaylists(chId)
    elif mode == 1:  #add communutycats
        print "play youtube url is " + url, mode
        PlayYoutube(url);
    elif mode == 2:  #add communutycats
        print "play youtube url is " + url, mode
        AddYoutubePlaylists(url);
    elif mode == 3:  #add communutycats
        print "play youtube url is " + url, mode
        AddYoutubeVideosByPlaylist(url);
except:
    print 'somethingwrong'
    traceback.print_exc(file=sys.stdout)


xbmcplugin.endOfDirectory(int(sys.argv[1]))


########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/aljadeedonline
# Version 1.0.2
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "aljadeedonline"

# Entry point
def run():
    plugintools.log("aljadeedonline.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("3alshasha.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/Aljadeedprograms
# Version 1.0.2
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "Aljadeedprograms"

# Entry point
def run():
    plugintools.log("Aljadeedprograms.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("3alshasha.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
import os
from xbmcswift2 import Plugin
from resources.lib.qaheraalyoum.api import QaheraAlYoumAPI
from resources.lib.qaheraalyoum.utils import extract_youtube_vid

PLUGIN_NAME = 'Al Qahera Al Youm'
PLUGIN_ID = 'plugin.video.alqaheraalyoum'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

CACHE_DURATION_MINUTES = 7
cache = plugin.get_storage('clips_cache.txt', TTL=CACHE_DURATION_MINUTES)
api = QaheraAlYoumAPI(cache)

@plugin.route('/')
def list_categories():
    categories = api.get_clips()

    items = [{
        'label': "%s ([COLOR blue]%s[/COLOR] clip%s)" % (category.name, category.count, 's' if category.count > 1 else ''),
        'path': plugin.url_for('list_category_clips', category=category.name),
        'thumbnail': _art('art', '%s.jpg' % category.name.lower()),
        'properties': [
            ('fanart_image', _art('fanart.jpg'))
        ]
    } for category in categories]

    return items

@plugin.route('/clips/<category>/')
def list_category_clips(category):
    plugin.log.info('Listing category: %s' % category)
    clips = api.get_clips_for_category(category)

    items = [{
        'label': u'%s | [B]%s[/B]' % (clip.addedWhen, clip.name),
        'path': plugin.url_for('play_clip', url=clip.url),
        'is_playable': True,
        'thumbnail': clip.thumbnail,
        'properties': [
            ('fanart_image', _art('fanart.jpg'))
        ]
    } for clip in reversed(clips)]

    return plugin.finish(items)

@plugin.route('/play/<url>/')
def play_clip(url):
    plugin.log.info('Playing clip in url: %s' % url)
    stream_url = api.get_stream_url(url)

    # If a YouTube clip, need to play clip using the XBMC YouTube plugin
    if "youtube.com" in stream_url:
        vid = extract_youtube_vid(stream_url)[0]
        stream_url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=%s" % vid
        plugin.log.info('Playing YouTube clip at [vid=%s]' % vid)
    else:
        plugin.log.info('Extracted stream url: %s' % stream_url)

    return plugin.set_resolved_url(stream_url)

def _art(file, *args):
    return os.path.join(plugin.addon.getAddonInfo('path'), file, *args)

if __name__ == '__main__':
    plugin.run()

########NEW FILE########
__FILENAME__ = api
import re
from itertools import groupby
from scraper import (get_clips, get_stream_url)

'''The main API object. Useful as a starting point to get available subjects. '''
class QaheraAlYoumAPI(object):

    def __init__(self, cache):
        self.cache = cache

    def _get_clips(self):

        # cache is empty or expired, fetch from service
        if 'clips' not in self.cache:
            clips = [Clip(info) for info in get_clips()]
            self.cache['clips'] = clips

        return self.cache['clips']

    def get_clips(self):
        """Returns a list of subjects available on the website."""
        flatList = self._get_clips()

        items = []
        for key, group in groupby(flatList, lambda x: x.category):
            clipsList = list(clip for clip in group)
            items.append(Category(key, len(clipsList)))

        return items

    def get_clips_for_category(self, category):
        flatList = self._get_clips()
        return filter(lambda x: x.category == category, flatList)

    def get_stream_url(self, clip_url):
        return get_stream_url(clip_url)


class Category:

    def __init__(self, title, count):
        self.name = title
        self.count = count

class Clip(object):

    def __init__(self, el):
        self.thumbnail = el['thumbnail']
        self.url = el['url']
        self.name = el['name']

        self._addedWhen = el['addedWhen']
        self._date = el['date'][el['date'].find('|') + 2:]

        # Using REGEX instead of .Replace - weird behaviour in some cases by latter
        p1 = re.compile(' hours')
        p2 = re.compile(' minutes')
        p3 = re.compile(' day')
        self.addedWhen = p1.sub('hrs', p2.sub('min', p3.sub('day', self._addedWhen)))

        self.date = self._date.replace('/', '.')

    @property
    def category(self):
        if "day" not in self._addedWhen:
            return 'Today'
        elif "1 day" in self._addedWhen:
            return "Yesterday"
        else:
            return re.sub(r'days.*', 'days ago', self._addedWhen)

########NEW FILE########
__FILENAME__ = scraper
import re
from urllib2 import urlopen
from urlparse import urljoin
from utils import get_redirect_flv_stream_url
from BeautifulSoup import BeautifulSoup

BASE_URL = 'http://www.alqaheraalyoum.net/videos/newvideos.php'

def _url(path=''):
    """Returns a full url for the given path"""
    return urljoin(BASE_URL, path)

def get(url):
    """Performs a GET request for the given url and returns the response"""
    conn = urlopen(url)
    resp = conn.read()
    conn.close()
    return resp

def _html(url):
    """Downloads the resource at the given url and parses via BeautifulSoup"""
    return BeautifulSoup(get(url), convertEntities=BeautifulSoup.HTML_ENTITIES)

def get_stream_url(clip_url):

    # A simple rename in the clip URL can usually correctly map to the
    # correct streaming URL. Check URL after correction and return if positive
    streamUrl = re.sub('playvideo.php', 'videos.php', clip_url)
    flvUrl = get_redirect_flv_stream_url(streamUrl)

    if not flvUrl is '':
        return flvUrl

    # Do an expensive fetch to the clip's page, and extract stream link from there
    html = get(clip_url)
    matchObj = re.search( r'file: \'(.*)\'', html, re.M|re.I)
    return matchObj.group(1)

def get_clips():
    """Returns a list of subjects for the website. Each subject is a dict with keys of 'name' and 'url'."""
    url = _url()
    html = _html(url)

    clips = html.find('div', { 'id': 'newvideos_results' }).findAll('tr', { 'class' : None })
    return [_get_clip(clip) for clip in clips]

def _get_clip(el):
    return {
        'thumbnail': el.find('img')['src'],
        'url': el.find('a')['href'],
        'name': el.findAll('td')[1].contents[0],
        'addedWhen': el.findAll('td')[3].contents[0],
        'date': el.findAll('td')[2].find('a').contents[0]
    }
########NEW FILE########
__FILENAME__ = utils
import httplib
import urlparse

def get_redirect_flv_stream_url(url):
    """
    Al qahera al youm's server redirects a video URL to a FLV file
    location in most times. If location is empty, a YouTube URL is being used
    """
    host, path, params, query = urlparse.urlparse(url)[1:5]    # elems [1] and [2]
    try:
        conn = httplib.HTTPConnection(host)
        conn.request('HEAD', path + '?' + query)
        return conn.getresponse().getheader('location')
    except StandardError:
        return None

def _get_server_status_code(url):
    """
    Download just the header of a URL and
    return the server's status code.
    """
    # http://stackoverflow.com/questions/1140661
    host, path, params, query = urlparse.urlparse(url)[1:5]    # elems [1] and [2]
    try:
        conn = httplib.HTTPConnection(host)
        conn.request('HEAD', path + '?' + query)
        return conn.getresponse().status
    except StandardError:
        return None

def check_url(url):
    """
    Check if a URL exists without downloading the whole file.
    We only check the URL header.
    """
    # see also http://stackoverflow.com/questions/2924422
    good_codes = [httplib.OK, httplib.FOUND, httplib.MOVED_PERMANENTLY]
    return _get_server_status_code(url) in good_codes

def extract_youtube_vid(url):
    if isinstance(url, str):
        url = [url]

    ret_list = []
    for item in url:
        item = item[item.find("v=") + 2:]
        if item.find("&") > -1:
            item = item[:item.find("&")]
        ret_list.append(item)

    return ret_list

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib
import time

__settings__ = xbmcaddon.Addon(id='plugin.video.alqudseyes')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'https://pbs.twimg.com/profile_images/1124212894/qudseyes.jpg'))
	addDir('افلام','http://aflam.alqudseyes.com/',1,'http://aflam.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات','http://mosalsalat.alqudseyes.com/',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('برامج تلفزيون','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D8%A8%D8%B1%D8%A7%D9%85%D8%AC-%D8%AA%D9%84%D9%81%D8%B2%D9%8A%D9%88%D9%86/c8',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات تركية','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%AA%D8%B1%D9%83%D9%8A%D8%A9/c1',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات خليجية','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%AE%D9%84%D9%8A%D8%AC%D9%8A%D8%A9/c6',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات رمضان 2011','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%B1%D9%85%D8%B6%D8%A7%D9%86-2011/c10',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات رمضان 2012','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%B1%D9%85%D8%B6%D8%A7%D9%86-2012/c11',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات سورية','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%B3%D9%88%D8%B1%D9%8A%D8%A9/c4',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات كارتون','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D9%83%D8%A7%D8%B1%D8%AA%D9%88%D9%86/c7',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات لبنانية','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D9%84%D8%A8%D9%86%D8%A7%D9%86%D9%8A%D8%A9/c5',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات مدبلجة','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D9%85%D8%AF%D8%A8%D9%84%D8%AC%D8%A9/c12',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	addDir('مسلسلات مصرية','http://mosalsalat.alqudseyes.com/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D9%85%D8%B5%D8%B1%D9%8A%D8%A9/c9',2,'http://mosalsalat.alqudseyes.com/site_images/aqe_logo_new.png')
	
def checkURL(url):
    p = urlparse(url)
    h = HTTP(p[1])
    h.putrequest('HEAD', p[2])
    h.endheaders()
    if h.getreply()[0] == 200: return 1
    else: return 0
	

def listEpos(url):
    
   
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    target= re.findall(r'<div class="thumbnail">(.*?)\s(.*?)<h2 class="itemtitle">', link, re.DOTALL)
    response.close()
    for items in  target:
        mytarg=str( items[1]).split('" width="150" height="225" /><br />')
        mytarg=str( mytarg[0]).strip()
        mytarg=str( mytarg).split('">')
        name_and_path=str(mytarg[0]).replace('<a title="', '')
            #print name_and_path
        thumb=str(mytarg[1]).replace('<img src="', '').strip()
        thumb=(str(thumb).split('" width="150"'))[0]
        name=str((str( name_and_path).split(" href="))[0]).replace('"', '').strip()
        path=str((str( name_and_path).split(" href="))[1]).replace('"', '').strip()
            #print path
        path='http://mosalsalat.alqudseyes.com'+path
        thumb='http://mosalsalat.alqudseyes.com'+thumb
        print name
        print path
        addLink(name,path,3,thumb)
		
def getAllFilms(url,videoType):
    
    my_url=url
    for i in range(0,40):
        url=my_url+"/page/"+str(i)
    
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        response = urllib2.urlopen(req)
        link=response.read()
        target= re.findall(r'<div class="thumbnail">(.*?)\s(.*?)<h2 class="itemtitle">', link, re.DOTALL)
        response.close()
        for items in  target:
            mytarg=str( items[1]).split('" width="150" height="225" /><br />')
            mytarg=str( mytarg[0]).strip()
            mytarg=str( mytarg).split('">')
            name_and_path=str(mytarg[0]).replace('<a title="', '')
            #print name_and_path
            thumb=str(mytarg[1]).replace('<img src="', '').strip()
            name=str((str( name_and_path).split(" href="))[0]).replace('"', '').strip()
            path=str((str( name_and_path).split(" href="))[1]).replace('"', '').strip()
            #print path
            if videoType=='film':
				path='http://aflam.alqudseyes.com'+path
				thumb='http://aflam.alqudseyes.com'+thumb
				addLink(name,path,3,thumb)
                
            elif videoType=='mosalsal':
				path='http://mosalsalat.alqudseyes.com'+path
				thumb='http://mosalsalat.alqudseyes.com'+thumb
				addDir(name,path,4,thumb)
           


	
def get_film_video_file(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
   
	url_ch=str(re.compile("'file': '(.+?)',").findall(link))
	url_ch=url_ch.replace("['", "")
	url_ch=url_ch.replace("']", "").strip()
    #rtmp://media.alqudseyes.com/vod/ swfUrl=http://mosalsalat.alqudseyes.com/player/jw6/jwplayer.flash.swf playpath=mp4:/series/Tarabish/E003.m4v
	url_ch=str(url_ch).split('mp4:')
    
	url_ch=url_ch[0]+' swfUrl=http://mosalsalat.alqudseyes.com/player/jw6/jwplayer.flash.swf playpath=mp4:'+url_ch[1]
	#url_ch='http://assets.delvenetworks.com/player/loader.swf?playerForm=64fc5d4a5f47400fac523fba125a8de8&&mediaId=92bb83bb29d145d99b057cb8ef7d3020&&defaultQuality=Download&amp;allowHttpDownload=true&amp;pdBitrate=224&amp;allowSharePanel=true&amp;allowEmbed=true'
	listItem = xbmcgui.ListItem(path=str(url_ch))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	
			

                
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None

from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
try:
    import json
except:
    import simplejson as json
	
	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        getAllFilms(url,'film')
	
elif mode==2:
        print ""+url
        getAllFilms(url,'mosalsal')
elif mode==3:
        print ""+url
        get_film_video_file(url)
elif mode==4:
        print ""+url
        listEpos(url)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import httplib
import time
from random import randint
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import cookielib

__settings__ = xbmcaddon.Addon(id='plugin.video.arabicchannels')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])


def getCookies(url):

    #Create a CookieJar object to hold the cookies
    cj = cookielib.CookieJar()
    #Create an opener to open pages using the http protocol and to process cookies.
    opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
    #create a request object to be used to get the page.
    req = Request(url)
    req.add_header('Host', 'www.arabichannels.com')
    req.add_header('Cache-Control', 'max-age=0')
    req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
    req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
    req.add_header('Referer', 'http://www.arabichannels.com/')
    req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
    f = opener.open(req)
    #see the first few lines of the page
    cj=str(cj).replace('<cookielib.CookieJar[<Cookie', '').replace('/>]>', '')
    cj=str(cj).strip()
    return cj
	
def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	addDir('All Channels','http://www.arabichannels.com/',1,'http://www.arabichannels.com/images/general.jpg')
	
	
		
def indexChannels(url):
	req = urllib2.Request(url)
	req.add_header('Host', 'www.arabichannels.com')
	req.add_header('Cache-Control', 'max-age=0')
	req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
	req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
	req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
	req.add_header('Referer', 'http://www.arabichannels.com/')
	req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
	req.add_header('Cookie', '  tzLogin='+str(getCookies('http://www.arabichannels.com/')))
	response = urllib2.urlopen(req)
	link=response.read()
	matchObj=(re.compile('<div class="(.+?)"><a href="#" onclick="document.getElementById(.+?)><span class="nume"(.+?)</span><img src="(.+?)"/></a></div>').findall(link))
	for items in matchObj:
		path=str( items[1]).split("src='")
		path=path[1]
		path="http://www.arabichannels.com/"+str(path).replace(';"',"").replace("'", '').strip()
		name=str( items[2]).replace(">", "").strip()
		image=str( items[3]).strip()
		if not "http:"  in image:
			if "./"  in image:
				image=str(image).replace("./","")
				image="http://www.arabichannels.com/"+image
			elif "/images/" in image:
				image="http://www.arabichannels.com"+image
		if "IPTV Receiver" not in str(name):
			if "ArabiChannels TV" not in str(name):
				addLink(name,path,2,image)
		
def playChannel(url):

	if ".php" in str(url):

		req = urllib2.Request(url)
		req.add_header('Host', 'www.arabichannels.com')
		req.add_header('Cache-Control', 'max-age=0')
		req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
		req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
		req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
		req.add_header('Referer', 'http://www.arabichannels.com/')
		req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
		req.add_header('Cookie', '  tzLogin='+str(getCookies('http://www.arabichannels.com/')))
		response = urllib2.urlopen(req)
		link=response.read()
		streamer=(re.compile("'streamer':(.+?)',").findall(link))
		swf=(re.compile("{type: 'flash', src: '(.+?)'},").findall(link))
		swf=str(swf).replace("['", "").replace("']", "").strip()
		streamer=str(streamer).replace('[', "").replace('"]', "").strip()
		streamer=str(streamer).replace("'", "").replace('"', "").strip().replace("]/", "").strip()
		fileLoc=(re.compile("'file':(.+?)',").findall(link))
		fileLoc=str(fileLoc[0]).replace("'", "").strip()
		fileLoc=str(fileLoc).replace("'", "").replace('"', "").strip()
		mynr1=randint(10,20)
		mynr2=randint(0,10)
		mynr3=randint(100,900)
		mynr=randint(10000,500000)
		
		#complete=streamer + ' swfUrl=http://arabichannels.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
		complete=streamer +'/'+fileLoc+ ' swfUrl=http://www.arabichannels.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
		listItem = xbmcgui.ListItem(path=str(complete))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		time.sleep(6)
		if xbmc.Player().isPlayingVideo()==False:
			complete=streamer + ' swfUrl=http://www.arabichannels.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
			listItem = xbmcgui.ListItem(path=str(complete))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		
		
		
		
		
	elif ".html" in str(url):
        
			myfinalpath=' '
			req = urllib2.Request(url)
			req.add_header('Host', 'www.arabichannels.com')
			req.add_header('Cache-Control', 'max-age=0')
			req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
			req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
			req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
			req.add_header('Referer', 'http://www.arabichannels.com/')
			req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
			req.add_header('Cookie', '  tzLogin='+str(getCookies('http://www.arabichannels.com/')))
			#req.add_header('Cookie', '  tzLogin=t5r8fm4vpck03ap6feeakj3of4; __qca=P0-831467814-1383850814929; HstCfa2398318=1383850815237; HstCmu2398318=1383850815237; HstCla2398318=1384292777596; HstPn2398318=1; HstPt2398318=6; HstCnv2398318=3; HstCns2398318=5; MLR72398318=1384292780000; __zlcmid=LodILVkuY96YpR; _pk_id.1.c9f1=ab7e13fd2cf6be07.1383850815.4.1384292879.1384285142.')
			response = urllib2.urlopen(req)
			link=response.read()
			mypath=(re.compile("file: '(.+?)',").findall(link))
			for item in  mypath:
				if "smil" in str(item):
					mydest="http://www.arabichannels.com/"+str( item).strip()
					req2 = urllib2.Request(mydest)
					req2.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
					response2 = urllib2.urlopen(req2)
					link2=response2.read()
					videosource=(re.compile('<video src="(.+?)" system-bitrate="400000"').findall(link2))
					myfinalpath=(re.compile(' <meta base="(.+?)"/>').findall(link2))
					myfinalpath=str(myfinalpath).replace("['", "").replace("']", "").strip()
					videosource=str(videosource).replace("['", "").replace("']", "").replace("'","").strip()
					myfinalpath=myfinalpath + ' playpath=' + videosource + ' swfUrl=http://www.arabichannels.com/player4/jwplayer.flash.swf live=1 buffer=300000 timeout=15 swfVfy=1 pageUrl=http://www.arabichannels.com'
					listItem = xbmcgui.ListItem(path=str(myfinalpath))
					xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	
			

def retrieveChannel(url):
	if "youtube" in str(url):
		finalurl=str(url).split("v=")
		finalurl=finalurl[1]
		playback_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % finalurl
	elif "youtube" not in str(url):
		playback_url=url
	return playback_url
	
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param





def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        indexChannels(url)
	
elif mode==2:
        print ""+url
        playChannel(url)
		


xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO,itertools
import urllib2,urllib
import re
import httplib
import time
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import cookielib
from random import randint

__settings__ = xbmcaddon.Addon(id='plugin.video.ArabicStreamSuperCollection')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
	
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def mainDir():
	addDir('Teledunet Channels','http://www.teledunet.com/list_chaines.php',9,'http://www.itwebsystems.co.uk/resources/icon.png')
	addDir('Arabic Filmon Channels','http://www.filmon.com/group/arabic-tv',3,'http://static.filmon.com/couch/channels/689/extra_big_logo.png')
	addDir('Mashup Arabic Streams','https://raw.github.com/mash2k3/MashUpStreams/master/CrusadersDir.xml',5,'http://www.mirrorservice.org/sites/addons.superrepo.org/Frodo/.metadata/plugin.video.movie25.jpg')
	addDir('TvIraq.net','http://www.tviraq.net/',8,'http://4.bp.blogspot.com/-mAFM9C7G3x8/Urg65k7EBsI/AAAAAAAADBU/FJ1UVeYz-5s/s1600/al+jazeera+mubasher++tv+live+logo.png')
	#addDir('hdarabic.com (Free channels)','http://www.hdarabic.com/',11,'http://www.hdarabic.com/images/general.jpg')
	addDir('OtherSources',' ',13,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
	addDir('Livestation','http://www.livestation.com/',16,'http://www.livestation.com/assets/new_logo.png')
	
def otherSourcesCat():
	addDir('Entertainment','http://jinnahtv.com/apps_mng/service_files/arab_tv_entertainment_channels.php',14,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
	addDir('Relegious','http://jinnahtv.com/apps_mng/service_files/live_tv_religious_channels.php',14,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
	addDir('News','http://jinnahtv.com/apps_mng/service_files/live_tv_news_channels.php',14,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
	addDir('Sports','http://jinnahtv.com/apps_mng/service_files/live_tv_sports_channels.php',14,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
	addDir('Different channels','http://steinmann.webs.com/tvhd.xml',18,'http://t1.ftcdn.net/jpg/00/29/62/30/400_F_29623050_hk7Oy2QPH8ZS6qa2vrYXz28O65G248ic.jpg')
def GetOtherChannels(url):
    
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	chName=(re.compile(' <title>(.+?)</title>').findall(link))
	chName.pop(0)
	chPath=(re.compile('<otherUrl url="(.+?)" />').findall(link))
	for elements,items in itertools.izip(chName,chPath):
		myChannelName=str( elements).strip()
		myChannelPath=str( items).strip()
		addLink(myChannelName,myChannelPath,15,'')

def GetLiveStations(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    base='http://www.livestation.com'
    url_target=(re.compile('<a href="(.+?)" class="(.+?)" data-action="(.+?)data-label="(.+?)" itemprop="(.+?)src="(.+?)"').findall(link))
    for items in url_target:
        if'language_selector' not in str(items):
            path=base+str( items[0]).strip()
            name=str( items[3]).strip()
            img=str( items[5]).strip()
            addLink(name,path,17,img)
            
def playLiveStations(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	try:
		url_target=(re.compile('<video id="(.+?)"video/').findall(link))
		url_target=str( url_target).split('><source src="')[1]
		url_target=str( url_target).split('m3u8')[0]+'m3u8'
		listItem = xbmcgui.ListItem(path=str(url_target))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	except:
		pass


	
def PlayOtherChannels(url):
	listItem = xbmcgui.ListItem(path=str(url))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)

def checkUrl(url):
    p = urlparse(url)
    conn = httplib.HTTPConnection(p.netloc)
    conn.request('HEAD', p.path)
    resp = conn.getresponse()
    return resp.status < 400

def getCookies(url):

    #Create a CookieJar object to hold the cookies
    cj = cookielib.CookieJar()
    #Create an opener to open pages using the http protocol and to process cookies.
    opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
    #create a request object to be used to get the page.
    req = urllib2.Request(url)
    req.add_header('Host', 'www.teledunet.com')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Referer', 'http://www.teledunet.com/')
    req.add_header('Connection', 'keep-alive')
    f = opener.open(req)
    #see the first few lines of the page
    cj=str(cj).replace('<cookielib.CookieJar[<Cookie', '').replace('/>]>', '').replace('for www.tviraq.net', '')
    cj=str(cj).strip()
    return cj
	

def getFilmOnCreds(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	filmOnUrl=(re.compile('<iframe frameborder=(.+?)width=').findall(link))
	filmOnUrl=str(str( filmOnUrl).split('src="')[1]).replace("']", "").replace('"', '').strip()
	req = urllib2.Request(filmOnUrl)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	myUrl=(re.compile('var startupChannel =(.+?);').findall(link))
	myUrl=str( myUrl).split(',')
	idStream=''
	rtmp=''
	stream=''
	for itr in myUrl:
		
		if 'streams' in itr:
			print 'this is stream '+itr
			stream=str( itr).replace('"streams":[{"name":"', '').replace('"', '').replace("low","high").strip()
   
		if 'rtmp' in itr:
			itr2=str( itr).replace('itr','').replace('"}]', '').replace('"', "").replace("\\", "").replace("url:",'').strip()
			rtmp= itr2
			idStream=str(itr2).split('id=')[1]
        
	
	if len(stream)>1 and len (idStream)>1 and len(rtmp)>1 :
		finalUrl=rtmp+' playpath='+str(stream)+' app=live/?id='+str(idStream)+' swfUrl=http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'+' tcUrl='+str(rtmp)+' pageurl=http://www.filmon.com/ live=true'
		listItem = xbmcgui.ListItem(path=str(finalUrl))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	
def isFilmOnCreds(url):
    try:
		req = urllib2.Request(url)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		filmOnUrl=(re.compile('<iframe frameborder=(.+?)width=').findall(link))
		print filmOnUrl
		
        
		if 'filmon' in str(filmOnUrl):
			filmOnUrl=str(str( filmOnUrl).split('src="')[1]).replace("']", "").replace('"', '').strip()
			return 'OK'
            
    except (urllib2.HTTPError):
        pass
        return 'Error'

def getCategories(url):
	
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	name=''
	path=''
	target= re.findall(r"<div class='widget-content list-label-widget-content'>(.*?)\s(.*?)<div class='clear'></div>", link, re.DOTALL)
	for items in target:
		myChannels=str( items[1]).split('>')
		for itr in myChannels:
			if "<a dir='rtl' href='" in itr:
				path= str(itr).split("href=")[1]
				path=str(path).replace("'","")
			if "</a" in itr:
				name=str( itr).replace("</a", "").strip()
				print name
				print path
				addDir(name,path,1,'')
				
def getCrusaderDir(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    
    response.close()
    target= re.findall(r'<name>(.*?)\s(.*?)<date>', link, re.DOTALL)
    for items in  target:
        names=str( items[0]).replace("</name>", "").strip()
        ImgPath=str( items[1])
        ImgPath=str( ImgPath).split('</link>')
        path=str( ImgPath[0]).replace('<link>', '').strip()
        image=str( ImgPath[1]).replace("</thumbnail>", "").replace("<thumbnail>", "").strip()
        addDir(names,path,6,image)
 

 
def getCrusaderChannels(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    target= re.findall(r'<item>(.*?)\s(.*?)</item>', link, re.DOTALL)
    for itr in target:
		mytarget=str( itr[1]).split('>')
		name=str( mytarget[1]).replace("</title", "").strip()
		path= str( mytarget[3]).replace("</link", "").strip()
		image= str( mytarget[5]).replace("</thumbnail", "").strip()
		addLink(name,path,7,image)
		
def playCrusadersChannel(url):
	listItem = xbmcgui.ListItem(path=str(url))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		
def indexIraqiChannels(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    thumbnail=''
    path=''
    name=''
    target= re.findall(r"<h3 class='post-title entry-title' itemprop='name'>(.*?)\s(.*?)<script type=", link, re.DOTALL)
    for ch in  target:
        myPath=str( ch[1]).split('>')
        for items in myPath:
           
            if '<a href=' in str(items):
                path=str(items).replace("<a href='", '').replace("'", "").replace('<a href="', "").replace('" target="_blank"', "").strip()
				
            if 'img border=' in str(items):
                thumbnail=str(items).split('src="')[1]
                thumbnail=str(thumbnail).split('" width="')[0]
                thumbnail=str(thumbnail).strip()
            if '</a' in str(items):
                name=str(items).replace('</a', '').strip()
            
        print name
        print path
        addLink(name,path,2,thumbnail)
        
def playIraqiChannels(url):
	if isFilmOnCreds(url)=='OK':
		getFilmOnCreds(url)
    
	else:
	
		req = urllib2.Request(url)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		#print link
		swfPlayer=(re.compile('<object bgcolor="#000000" data="(.+?)" height=').findall(link))
		target= re.findall(r'aboutlink: "http://www.tviraq.net",(.*?)\s(.*?)logo:', link, re.DOTALL) 
		swfPlayer=str(swfPlayer).replace("['", "").replace("']", "").strip()
		mytarget=str( target[0]).split(',') 
		path=str( mytarget[1] ).replace("' file: ", '').replace('"', "").strip()   
		#image=str( mytarget[2] ).split("image: ")[1]
		#image=str(image).replace('"', "").strip()
		rtmpUrl=path
		base=str(rtmpUrl).split("/")
		playPath= base.pop()
		playPath=str( playPath).strip()
		app=base.pop()
		if "www.youtube" in str(path):
			video=path.split("v=")
			#print "youtube after split: "+str(video)
			video_id=str(video[1])
			video_id=video_id.replace(".flv","").strip()
			print "first item of youtube: "+str(video_id)
			playback_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % video_id
			listItem = xbmcgui.ListItem(path=str(playback_url))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		if 'm3u8' in str(path):
			playback_url = path
			listItem = xbmcgui.ListItem(path=str(playback_url))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		
		
		else:
			
			playback_url=str(path)+" playpath="+str(playPath)+" swfUrl="+str(swfPlayer)+" flashVer=WIN119900170"+" live=true swfVfy=true timeout=10"
			listItem = xbmcgui.ListItem(path=str(playback_url))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
			
def getFilmonChannels(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    channelId=(re.compile('<li class="(.+?)channel_id="(.+?)">').findall(link))
    channelNameImage=(re.compile('<img class="channel_logo" src="(.+?)" title="(.+?)" style=').findall(link))
    for (items,itr) in itertools.izip  (channelId,channelNameImage):
        channelid='http://www.filmon.com/tv/channel/export?channel_id='+str( items[1]).strip()
        nameImage= itr
        image=str(nameImage).split(',')[0]
        name=str(nameImage).split(',')[1]
        name=str(name).replace("'", '').replace(")", "").strip()
        image=str(image).replace("('", '').replace("'", "").strip()
        addLink(name,channelid,4,image)
			
def playFilmOnChannel(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	myUrl=(re.compile('var startupChannel =(.+?);').findall(link))
	myUrl=str( myUrl).split(',')
	idStream=''
	rtmp=''
	stream=''
	for itr in myUrl:
		if 'streams' in itr:
			stream=str( itr).replace('"streams":[{"name":"', '').replace('"', '').replace("low","high").strip()
		if 'rtmp' in itr:
			itr2=str( itr).replace('itr','').replace('"}]', '').replace('"', "").replace("\\", "").replace("url:",'').strip()
			rtmp= itr2
			idStream=str(itr2).split('id=')[1]

	finalUrl=rtmp+' playpath='+str(stream)+' app=live/?id='+str(idStream)+' swfUrl=http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'+' tcUrl='+str(rtmp)+' pageurl=http://www.filmon.com/ live=true timeout=15'
	listItem = xbmcgui.ListItem(path=str(finalUrl))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)

def getFilmOnCreds2(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    filmOnUrl=(re.compile('<iframe frameborder=(.+?)width=').findall(link))
    if len(filmOnUrl)>1:
        
        filmOnUrl=str(str( filmOnUrl).split('src="')[1]).replace("']", "").replace('"', '').strip()
        
        req = urllib2.Request(filmOnUrl)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        response = urllib2.urlopen(req)
        link=response.read()
        response.close()
        myUrl=(re.compile('var startupChannel =(.+?);').findall(link))
        myUrl=str( myUrl).split(',')
        idStream=''
        rtmp=''
        stream=''
        for itr in myUrl:
            if 'streams' in itr:
                stream=str( itr).replace('"streams":[{"name":"', '').replace('"', '').replace("low","high").strip()
                
            if 'rtmp' in itr:
                itr2=str( itr).replace('itr','').replace('"}]', '').replace('"', "").replace("\\", "").replace("url:",'').strip()
                rtmp= itr2
                idStream=str(itr2).split('id=')[1]
               
            
       
        finalUrl=rtmp+' playpath='+str(stream)+' app=live/?id='+str(idStream)+' swfUrl=http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'+' tcUrl='+str(rtmp)+' pageurl=http://www.filmon.com/ live=true'
        listItem = xbmcgui.ListItem(path=str(finalUrl))
        xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
    else:
        
        myUrl=(re.compile('var startupChannel =(.+?);').findall(link))
        myUrl=str( myUrl).split(',')
        idStream=''
        rtmp=''
        stream=''
        for itr in myUrl:
            if 'streams' in itr:
                stream=str( itr).replace('"streams":[{"name":"', '').replace('"', '').replace("low","high").strip()
            
            
            if 'live' in itr:
                itr2=str( itr).replace('itr','').replace('"}]', '').replace('"', "").replace("\\", "").replace("url:",'').strip()
                rtmp= itr2
                idStream=str(itr2).split('id=')[1]
                
        finalUrl=rtmp+' playpath='+str(stream)+' app=live/?id='+str(idStream)+' swfUrl=http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'+' tcUrl='+str(rtmp)+' pageurl=http://www.filmon.com/ live=true'
        listItem = xbmcgui.ListItem(path=str(finalUrl))
        xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		
	 ###########################TELEDUNET CODE ##########################################
def index_Teledunet(url):
	url="http://www.teledunet.com/list_chaines.php"
	req = urllib2.Request(url)
	req.add_header('Host', 'www.teledunet.com')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:28.0) Gecko/20100101 Firefox/28.0')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3')
	req.add_header('Accept-Encoding', 'gzip, deflate')
	req.add_header('Connection', ' keep-alive')
	
	response = urllib2.urlopen(req,timeout=15)
	link=response.read()
	response.close()
	style=(re.compile('<div  id="(.+?)class=div_channel>').findall(link))
	image=(re.compile('<img onerror="(.+?)src="(.+?)" height=').findall(link))
	nameUrl=(re.compile('onclick="set_favoris(.+?);" style=').findall(link))
	imgArray=[]
	colorArray=[]
	nameArray=[]
	pathArray=[]
	global globalIp
	
	addLink('MBC','rtmp://www.teledunet.com:1935/teledunet/mbc_1',10,'https://si0.twimg.com/profile_images/1133033554/mbc-fb.JPG')
	addLink('MBC DRAMA','rtmp://www.teledunet.com:1935/teledunet/mbc_drama',10,'http://www.allied-media.com/ARABTV/images/mbc_drama.jpg')
	#addLink('beIn Sports 1','rtmp://www.teledunet.com:1935/teledunet/jsc_1',10,'')
	#addLink('beIn Sports 2','rtmp://www.teledunet.com:1935/teledunet/jsc_2',10,'')
	#addLink('beIn Sports 3','rtmp://www.teledunet.com:1935/teledunet/jsc_3',10,'')
	#addLink('beIn Sports 4','rtmp://www.teledunet.com:1935/teledunet/jsc_4',10,'')
	#addLink('beIn Sports 5','rtmp://www.teledunet.com:1935/teledunet/jsc_5',10,'')
	#addLink('beIn Sports 6','rtmp://www.teledunet.com:1935/teledunet/jsc_6',10,'')
	#addLink('beIn Sports 7','rtmp://www.teledunet.com:1935/teledunet/jsc_7',10,'')
	#addLink('beIn Sports 8','rtmp://www.teledunet.com:1935/teledunet/jsc_8',10,'')
	#addLink('beIn Sports 11','rtmp://www.teledunet.com:1935/teledunet/jsc_9',10,'')
	#addLink('beIn Sports 12','rtmp://www.teledunet.com:1935/teledunet/jsc_10',10,'')
	#addLink('JSC 1 HD','rtmp://www.teledunet.com:1935/teledunet/tele_1_hd',10,'')
	#addLink('JSC 2 HD','rtmp://www.teledunet.com:1935/teledunet/tele_2_hd',10,'')
	addLink('Abu Dhabi Al Oula','rtmp://www.teledunet.com:1935/teledunet/abu_dhabi',10,'https://www.zawya.com/pr/images/2009/ADTV_One_RGB_2009_10_08.jpg')
	addLink('Abu Dhabi Sports','rtmp://www.teledunet.com:1935/teledunet/abu_dhabi_sports_1',10,'https://si0.twimg.com/profile_images/2485587448/2121.png')
	addLink('Al Jazeera','rtmp://www.teledunet.com:1935/teledunet/aljazeera',10,'http://www.chicagonow.com/chicago-sports-media-watch/files/2013/04/Al-Jazeera.jpg')
	addLink('Al Jazeera Mubasher Masr','rtmp://www.teledunet.com:1935/teledunet/aljazeera_mubasher_masr',10,'http://www.chicagonow.com/chicago-sports-media-watch/files/2013/04/Al-Jazeera.jpg')
	addLink('Al Jazeera Children','rtmp://www.teledunet.com:1935/teledunet/aljazeera_children',10,'http://3.bp.blogspot.com/-UX1XBY8-02g/Uoku7OTIrFI/AAAAAAAAASk/-0eEX7fumJw/s1600/al_jazeera_children.png')
	addLink('Al Jazeera Documentation','rtmp://www.teledunet.com:1935/teledunet/aljazeera_doc',10,'http://upload.wikimedia.org/wikipedia/en/e/e6/Al_Jazeera_Doc.png')
	addLink('ART Cinema','rtmp://www.teledunet.com:1935/teledunet/art_aflam_1',10,'http://www.lyngsat-logo.com/hires/aa/art_cinema.png')
	addLink('ART Aflam 2','rtmp://www.teledunet.com:1935/teledunet/art_aflam_2',10,'http://www.invision.com.sa/en/sites/default/files/imagecache/216x216/channels/2011/10/11/1138.jpg')
	addLink('Cartoon Network','rtmp://www.teledunet.com:1935/teledunet/cartoon_network',10,'http://upload.wikimedia.org/wikipedia/commons/b/bb/Cartoon_Network_Arabic_logo.png')
	addLink('MTV Lebanon','rtmp://www.teledunet.com:1935/teledunet/mtv',10,'http://mtv.com.lb/images/mtv-social-logo1.jpg')
	addLink('AlJadeed','rtmp://www.teledunet.com:1935/teledunet/aljaded_sat',10,'')
	addLink('NBN','rtmp://www.teledunet.com:1935/teledunet/nbn',10,'http://upload.wikimedia.org/wikipedia/en/1/14/Nbn_lebanon.png')
	addLink('Otv Lebanon','rtmp://www.teledunet.com:1935/teledunet/otv_lebanon',10,'http://www.worldmedia.com.au/Portals/0/Images/Logo_s/otv.png')
	addLink('Al Hayat','rtmp://www.teledunet.com:1935/teledunet/alhayat_1',10,'http://3.bp.blogspot.com/--uP1DsoBB7s/T4EMosYH5uI/AAAAAAAAF9E/RdbY8-E3Riw/s320/Al%2Bhayat.jpg')
	addLink('Al Hayat Cinema','rtmp://www.teledunet.com:1935/teledunet/alhayat_cinema',10,'http://www.lyngsat-logo.com/hires/aa/alhayat_cinema.png')
	addLink('Alarabiya','rtmp://www.teledunet.com:1935/teledunet/alarabiya',10,'http://www.debbieschlussel.com/archives/alarabiya2.jpg')
	addLink('Tele Sports','rtmp://www.teledunet.com:1935/teledunet/tele_sports',10,'http://www.itwebsystems.co.uk/resources/icon.png')
	addLink('Noursat','rtmp://www.teledunet.com:1935/teledunet/noursat',10,'')
	addLink('TF1','rtmp://www.teledunet.com:1935/teledunet/tf1',10,'')
	addLink('Al Masriyah','rtmp://www.teledunet.com:1935/teledunet/al_masriyah',10,'')
	addLink('Iqra','rtmp://www.teledunet.com:1935/teledunet/Iqra',10,'')
	addLink('Canal Plus','rtmp://www.teledunet.com:1935/teledunet/canal_plus',10,'')
	addLink('Melody TV','rtmp://www.teledunet.com:1935/teledunet/melody',10,'')
	addLink('Alrahma','rtmp://www.teledunet.com:1935/teledunet/alrahma',10,'')
	addLink('Assadissa','rtmp://www.teledunet.com:1935/teledunet/assadissa',10,'')
	addLink('Dzair 24','rtmp://www.teledunet.com:1935/teledunet/dzair_24',10,'')
	addLink('Dzair TV','rtmp://www.teledunet.com:1935/teledunet/dzair_tv',10,'')
	addLink('M6','rtmp://www.teledunet.com:1935/teledunet/m6',10,'')
	addLink('Noursat','rtmp://www.teledunet.com:1935/teledunet/noursat',10,'')
	addLink('ORTB TV','rtmp://www.teledunet.com:1935/teledunet/ortb_tv',10,'')
	addLink('Roya','rtmp://www.teledunet.com:1935/teledunet/roya',10,'')
	addLink('TNN','rtmp://www.teledunet.com:1935/teledunet/tnn',10,'')
	addLink('W9','rtmp://www.teledunet.com:1935/teledunet/w9',10,'')
    
	for itemNameUrl in nameUrl:
		myItems=str(itemNameUrl).split(',')
		name=str(myItems[1]).replace("'",'').strip()
		path=str(myItems[2]).replace("'",'').replace(")",'').strip()
		if not 'www' in path:
			globalIp=str( path).split('teledunet')[0]
			globalIp=str(globalIp).replace("1935/","1935")
			#print globalIp
		#path=str(path).replace("rtmp://www.teledunet.com:1935/",str(globalIp))
		nameArray.append(name) 
		pathArray.append(path) 
    
	for itemsImg in  image:
		myImage="http://www.teledunet.com/"+str( itemsImg[1] )
		imgArray.append(myImage) 
	
	for (names,images,paths) in itertools.izip (nameArray,imgArray,pathArray):
		
		addLink(names,paths,10,images)

def getCookies(url):

    #Create a CookieJar object to hold the cookies
	cj = cookielib.CookieJar()
	print "this is oookie " + str(url)
    #Create an opener to open pages using the http protocol and to process cookies.
	opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
	#create a request object to be used to get the page.
	req = urllib2.Request(url)
	req.add_header('Host', 'www.teledunet.com')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Accept-Encoding', 'gzip, deflate')
	req.add_header('Referer', 'http://www.teledunet.com/')
	req.add_header('Connection', 'keep-alive')
	f = opener.open(req)
    #see the first few lines of the page
	cj=str(cj).replace('<cookielib.CookieJar[<Cookie', '').replace('/>]>', '').replace('for www.teledunet.com', '')
	cj=str(cj).strip()
	return cj


def getId(channel):
    url="http://www.teledunet.com/player/?channel="+channel+"&no_pub"
    req = urllib2.Request(url)
    req.add_header('Host', 'www.teledunet.com')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:28.0) Gecko/20100101 Firefox/28.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Referer', "http://www.teledunet.com/?channel="+channel)
    req.add_header('Connection', ' keep-alive')
    response = urllib2.urlopen(req,timeout=5)
    link=response.read()
    response.close()
    nameUrl=(re.compile("time_player=(.+?);").findall(link))
    nameUrl = str(nameUrl).replace('"]',"").strip()
    nameUrl=str( nameUrl).replace("['", '').replace("']", '').replace(".","").replace("E+13","00").strip()
    return nameUrl
	

def GetHDSITEChannels(url):
	req = urllib2.Request('http://steinmann.webs.com/tvhd.xml')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
   
	response.close()
	target= re.findall(r'<items>(.*?)\s(.*?)</items>', link, re.DOTALL)
	target=str( target).split('<item')
	name=''
	img=''
	path=''

	for itr in target:
		if ('TV="') in itr:
			mypath=str( itr).replace('title="', ' DELIM ').replace('coverImage="', ' DELIM ').replace('TV="', ' DELIM ').replace('picture="', ' DELIM ')
			mypath=str(mypath).split(' DELIM ')
			for items in mypath:
				newpath=str( items).split('\r\n')
				for itr in newpath:
					if ('http' in str( itr)) or '"' in itr:
						finalPath=itr.replace('"',"").strip()
						if 'http://www.cookiesjar.net/letsapp/listen/quran/free.jpg' not in itr:
							if 'http' in str(finalPath):
								if "png" in str(finalPath) or "gif" in str(finalPath) or "jpg" in str(finalPath):
									img=finalPath
								else:
									path=finalPath
							else:
								name=finalPath
								name= name[:-4]
								img= img[:-4]
								path= path[:-4]
								addLink('',path,15,img)
	
def getChanelRtmp(channel):
    url="http://www.teledunet.com/player/?channel="+channel
    req = urllib2.Request(url)
    req.add_header('Host', 'www.teledunet.com')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:28.0) Gecko/20100101 Firefox/28.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Referer', "http://www.teledunet.com/?channel="+channel)
    req.add_header('Connection', ' keep-alive')
    response = urllib2.urlopen(req,timeout=5)
    link=response.read()
    
    response.close()
    nameUrl=(re.compile("curent_media='(.+?)';").findall(link))
    return nameUrl[0]
	
                    
def PlayTeledunet(url):
	firstPart=str(url).split('teledunet/')[1]
	streamer = getChanelRtmp(firstPart)
	finalPayPath=streamer+' app=teledunet swfUrl=http://www.teledunet.com/player/player/player_2.swf?bufferlength=5&repeat=single&autostart=true&id0='+str(getId(firstPart))+'&streamer='+streamer+'&file='+str(firstPart)+'&provider=rtmp playpath='+str(firstPart)+' live=1 pageUrl=http://www.teledunet.com/tv/?channel='+str(firstPart)+'&no_pub'
	listItem = xbmcgui.ListItem(path=str(finalPayPath))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	

############################################ hdarabic.com################################################################

def getCookiesARC(url):

    #Create a CookieJar object to hold the cookies
    cj = cookielib.CookieJar()
    #Create an opener to open pages using the http protocol and to process cookies.
    opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
    #create a request object to be used to get the page.
    req = Request(url)
    req.add_header('Host', 'www.hdarabic.com')
    req.add_header('Cache-Control', 'max-age=0')
    req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
    req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
    req.add_header('Referer', 'http://www.hdarabic.com/')
    req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
    f = opener.open(req)
    #see the first few lines of the page
    cj=str(cj).replace('<cookielib.CookieJar[<Cookie', '').replace('/>]>', '')
    cj=str(cj).strip()
    return cj

def indexArChannels(url):
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	link=response.read()
    
	req = urllib2.Request(url)
	req.add_header('Host', 'hdarabic.com')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	#req.add_header('Referer', ' http://arabichannels.com/')
	req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
	req.add_header('Accept-Encoding', 'identity')
	req.add_header('Connection', 'close')
	target= re.findall(r'<ul id="menu">(.*?)\s(.*?)<ul></div> ', link, re.DOTALL)
    
	for items in target:
		myBaseUrl= items[1]
		myBaseUrl=str(myBaseUrl).split('"/></a></div>')
		for itr in myBaseUrl:
			try:
				theTarget=str( itr).split("src='")[1]
				theTarget=str(theTarget).replace(';"><span class="nume">', 'DELIM').replace('" alt="','DELIM')
				theTarget=str(theTarget).split('DELIM')
				path='http://www.hdarabic.com/'+str( theTarget[0]).replace("'", "").strip()
				nameImage= str(theTarget[1]).split('</span><img src="')
				name=str( nameImage[0]).strip()
				image=str(nameImage[1]).replace("./", "/").strip()
                
				if 'http' in str( image):
					image=image
				else:
					image="http://www.hdarabic.com"+image
                
				if 'iptv' not in str(path):
					addLink(name,path,12,image)
			except:
				pass
   
					
	
            
					
					
def playARCChannel(url):

	if ".php" in str(url):

		req = urllib2.Request(url)
		req.add_header('Host', 'www.hdarabic.com')
		req.add_header('Cache-Control', 'max-age=0')
		req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
		req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
		req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
		req.add_header('Referer', 'http://www.hdarabic.com/')
		req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
		req.add_header('Cookie', '  tzLogin='+str(getCookies('http://www.hdarabic.com/')))
		response = urllib2.urlopen(req)
		link=response.read()
		streamer=(re.compile("'streamer':(.+?)',").findall(link))
		swf=(re.compile("{type: 'flash', src: '(.+?)'},").findall(link))
		swf=str(swf).replace("['", "").replace("']", "").strip()
		streamer=str(streamer).replace('[', "").replace('"]', "").strip()
		streamer=str(streamer).replace("'", "").replace('"', "").strip().replace("]/", "").strip()
		fileLoc=(re.compile("'file':(.+?)',").findall(link))
		fileLoc=str(fileLoc[0]).replace("'", "").strip()
		fileLoc=str(fileLoc).replace("'", "").replace('"', "").strip()
		mynr1=randint(10,20)
		mynr2=randint(0,10)
		mynr3=randint(100,900)
		mynr=randint(10000,500000)
		
		#complete=streamer + ' swfUrl=http://hdarabic.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
		complete=streamer +'/'+fileLoc+ ' swfUrl=http://www.hdarabic.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
		listItem = xbmcgui.ListItem(path=str(complete))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		time.sleep(6)
		if xbmc.Player().isPlayingVideo()==False:
			complete=streamer + ' swfUrl=http://www.hdarabic.com' + swf + ' playpath=' + fileLoc +  ' flashVer='+str(mynr1)+'.'+str(mynr2)+'.'+str(mynr3)+' live=1 swfVfy=true pageUrl='+str(url)
			listItem = xbmcgui.ListItem(path=str(complete))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		
		
		
		
		
	elif ".html" in str(url):
        
			myfinalpath=' '
			req = urllib2.Request(url)
			req.add_header('Host', 'www.hdarabic.com')
			req.add_header('Cache-Control', 'max-age=0')
			req.add_header('Accept', ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
			req.add_header('User-Agent', ' Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36')
			req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
			req.add_header('Referer', 'http://www.hdarabic.com/')
			req.add_header('Accept-Language', 'sv,en-US;q=0.8,en;q=0.6,en-GB;q=0.4')
			req.add_header('Cookie', '  tzLogin='+str(getCookies('http://www.hdarabic.com/')))
			#req.add_header('Cookie', '  tzLogin=t5r8fm4vpck03ap6feeakj3of4; __qca=P0-831467814-1383850814929; HstCfa2398318=1383850815237; HstCmu2398318=1383850815237; HstCla2398318=1384292777596; HstPn2398318=1; HstPt2398318=6; HstCnv2398318=3; HstCns2398318=5; MLR72398318=1384292780000; __zlcmid=LodILVkuY96YpR; _pk_id.1.c9f1=ab7e13fd2cf6be07.1383850815.4.1384292879.1384285142.')
			response = urllib2.urlopen(req)
			link=response.read()
			mypath=(re.compile("file: '(.+?)',").findall(link))
			for item in  mypath:
				if "smil" in str(item):
					mydest="http://www.hdarabic.com/"+str( item).strip()
					req2 = urllib2.Request(mydest)
					req2.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
					response2 = urllib2.urlopen(req2)
					link2=response2.read()
					videosource=(re.compile('<video src="(.+?)" system-bitrate="400000"').findall(link2))
					myfinalpath=(re.compile(' <meta base="(.+?)"/>').findall(link2))
					myfinalpath=str(myfinalpath).replace("['", "").replace("']", "").strip()
					videosource=str(videosource).replace("['", "").replace("']", "").replace("'","").strip()
					myfinalpath=myfinalpath + ' playpath=' + videosource + ' swfUrl=http://www.hdarabic.com/player4/jwplayer.flash.swf live=1 buffer=300000 timeout=15 swfVfy=1 pageUrl=http://www.hdarabic.com'
					listItem = xbmcgui.ListItem(path=str(myfinalpath))
					xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	
			

def retrieveChannel(url):
	if "youtube" in str(url):
		finalurl=str(url).split("v=")
		finalurl=finalurl[1]
		playback_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % finalurl
	elif "youtube" not in str(url):
		playback_url=url
	return playback_url


		
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None

	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        mainDir()
       
elif mode==1:
        print ""+url
        indexIraqiChannels(url)
	
elif mode==2:
        playIraqiChannels(url)
elif mode==3:
        getFilmonChannels(url)
elif mode==4:
        getFilmOnCreds2(url)
elif mode==5:
        getCrusaderDir(url)
elif mode==6:
        getCrusaderChannels(url)
elif mode==7:
        playCrusadersChannel(url)		
elif mode==8:
        getCategories(url)	
elif mode==9:
        index_Teledunet(url)
elif mode==10:
        PlayTeledunet(url)
elif mode==11:
        indexArChannels(url)
elif mode==12:
        playARCChannel(url)
elif mode==13:
        otherSourcesCat()
elif mode==14:
        GetOtherChannels(url)
elif mode==15:
        PlayOtherChannels(url)
elif mode==16:
        GetLiveStations(url)
elif mode==17:
        playLiveStations(url)
elif mode==18:
	GetHDSITEChannels(url)
		
xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = channels_xml_generator
from itertools import groupby

class Channel:
    def __init__(self, channelArr):
        self.channelID = channelArr[0]
        self.title = channelArr[1]
        self.thumbnail = channelArr[2]
        self.categoryName = channelArr[3]

class Generator:
    """
        Generates a new channels.xml file from channels.csv file that
        can be used by the ATN Network XBMC plugin. Must be run from the
        root of the checked-out repo. Only handles single depth folder structure.
    """
    def __init__( self ):
        # generate files
        self._generate_addons_file()
        # notify user
        print "Finished creating ATN channels xml file"

    def _generate_addons_file( self ):
        # final addons text
        channels_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<categories>\n"

        try:
            _path = ".\\resources\\data\\channels.csv"
            csv_lines = open(_path, "r" ).read().splitlines()

            channels_list = []

            for line in csv_lines[1:]:  # skip header row: [1:]
                channel = Channel(line.split(","))
                channels_list.append(channel)

            channels_list.sort(key=lambda c: c.categoryName)

            for key, group in groupby(channels_list, lambda  x: x.categoryName):
                channels_xml += "<category title='%s'>\n" % key
                for thing in group:
                    channels_xml += "<channel id='%s' title='%s' thumbnail='%s' />\n" % (thing.channelID, thing.title, thing.thumbnail)
                channels_xml += "</category>\n"

        except Exception, e:
            # missing or poorly formatted addon.xml
            print "Excluding %s for %s" % ( _path, e, )
            # clean and add closing tag

        channels_xml = channels_xml.strip() + u"\n</categories>\n"

        # save file
        self._save_file( channels_xml.encode( "utf-8" ), file=".\\resources\\data\\channels.xml" )

    def _save_file( self, data, file ):
        try:
            # write data to the file
            open( file, "w" ).write( data )
        except Exception, e:
            # oops
            print "An error occurred saving %s file!\n%s" % ( file, e, )


if ( __name__ == "__main__" ):
    # start
    Generator()
########NEW FILE########
__FILENAME__ = default
import os
import sys
import xbmcplugin
import xbmcgui
import xbmcaddon

from UtilsCommon import UtilsCommon
from UtilsATN import UtilsATN
from UtilsChannelsFile import UtilsChannelsFile

plugin = int(sys.argv[1])
settings = xbmcaddon.Addon(id='plugin.video.atnnetwork')
language = settings.getLocalizedString
pluginPath = settings.getAddonInfo('path')

utilsATN = UtilsATN()
utilsCommon = UtilsCommon()
utilsChannelsFile = UtilsChannelsFile()

# Setting constants
MODE_LIST_CATEGORY_CHANNELS = 1
MODE_LIST_ATN_PACKAGES = 2
MODE_LIST_ATN_PACKAGE_CHANNELS = 3
MODE_PLAY_VIDEO = 4
MODE_SHOW_SETTINGS = 5

ATN_ARABIC_PACKAGE_NO = 15

def getRootCategories():
    if not(utilsATN.hasValidLogin()):
        addDir(language(30500), MODE_SHOW_SETTINGS, '')

    else:
        addDir(language(30501), MODE_LIST_ATN_PACKAGES, '')
        for category in utilsChannelsFile.getCategories():
            addDir(category.title, MODE_LIST_CATEGORY_CHANNELS, ATN_ARABIC_PACKAGE_NO)

    xbmcplugin.endOfDirectory(plugin)

def listChannelsForCategory(categoryTitle):
    channelsList = utilsChannelsFile.getChannelsByCategoryTitle(categoryTitle)
    for channel in channelsList:
        addLink(channel.title, channel.id, MODE_PLAY_VIDEO, ATN_ARABIC_PACKAGE_NO, channel.thumbnail, len(channelsList))

    xbmcplugin.endOfDirectory(plugin)

def listATNPackages():
    packages = utilsATN.getATNSubscriptionPackages()

    for package in packages:
        print package['Name'] + ', ' + package['ID']
        addDir(package['Name'], MODE_LIST_ATN_PACKAGE_CHANNELS, package['ID'])

    xbmcplugin.endOfDirectory(plugin)

def listChannelsForATNPackage(packageNo):
    channels_json = utilsATN.getAllChannels(packageNo)
    resultsCount = len(channels_json)

    for channel in channels_json:
        addLink(channel['Name'], channel['ID'], MODE_PLAY_VIDEO, packageNo, channel['Logo'], resultsCount)

    xbmcplugin.endOfDirectory(plugin)

def playVideo(channelID, packageNo):
    clipStreamingUrl = utilsATN.getChannelStreamUrl(channelID, packageNo)
    listItem = xbmcgui.ListItem(path=clipStreamingUrl)

    # Check if user's current subscription is upto date and valid
    if utilsATN.login() is False:
        dialog = xbmcgui.Dialog()
        dialog.ok(language(30603), language(30604), '', language(30605))
        return

    return xbmcplugin.setResolvedUrl(plugin, True, listItem)

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

def login():
    xbmcaddon.Addon(id='plugin.video.atnnetwork').openSettings()
    success = utilsATN.login()

    if not success:
        utilsCommon.showErrorMessage("", language(30602))

def addDir(name, mode, packageNo):
    u = sys.argv[0] + "?mode=" + str(mode) + "&packageNo=" + str(packageNo) + "&channelName=" + str(name)

    thumbnail = os.path.join(pluginPath, 'art', name.lower() + '.jpg')

    li = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=thumbnail)
    li.setInfo(type="Video", infoLabels={"Title": name})
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=li, isFolder=True)
    return ok

def addLink(name, channelID, mode, packageNo, iconImage, totalItems):
    u = sys.argv[0] + "?channelID=" + str(channelID) + "&packageNo=" + str(packageNo) + "&mode=" + str(mode)
    li = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconImage)
    li.setInfo(type="Video", infoLabels={"Title": name})
    li.setProperty('IsPlayable', 'true')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=li, totalItems=totalItems)
    return ok

def tryParse(array, key):
    value = None

    try:
        value = array[key]
    except:
        pass

    return value

# ---------------------------------------------------------------------------------

#
# Parse query string parameters
params = get_params()
lastMode = None

try:
    lastMode = int(params["mode"])
except:
    pass

channelID   = tryParse(params, "channelID")
channelName = tryParse(params, "channelName")
packageNo   = tryParse(params, "packageNo")

#
# Controller Logic
print "Current URL: " + sys.argv[2]

if lastMode is None:
    getRootCategories()

elif lastMode == MODE_LIST_ATN_PACKAGES:
    listATNPackages()

elif lastMode == MODE_LIST_ATN_PACKAGE_CHANNELS:
    listChannelsForATNPackage(packageNo)

elif lastMode == MODE_LIST_CATEGORY_CHANNELS:
    listChannelsForCategory(channelName)

elif lastMode == MODE_PLAY_VIDEO:
    playVideo(channelID, packageNo)

elif lastMode == MODE_SHOW_SETTINGS:
    login()
########NEW FILE########
__FILENAME__ = UtilsATN
import cookielib
import hashlib
import json
import sys
import urllib2

class UtilsATN:

    # ATN Feeds
    urls = {}
    urls['login_querystring'] = "email={email}&password={password}"
    urls['get_packages'] = "http://api.arabtvnet.tv/get_packages?{loginTicket}"
    urls['get_channel'] = "http://api.arabtvnet.tv/channel?{loginTicket}&package={packageNo}&channel={channelID}"
    urls['get_channels'] = "http://api.arabtvnet.tv/channels?package={packageNo}"

    def __init__(self):
        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.plugin = sys.modules["__main__"].plugin

        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))

    def loginTicket(self):
        username = self.settings.getSetting('username')
        password = self.settings.getSetting('password')
        md5Password = hashlib.md5(password).hexdigest()

        return self.urls['login_querystring'].format(email=username, password=md5Password)

    def hasValidLogin(self):
        return self.settings.getSetting('validLogin') == "True"

    def getData(self, url):
        response = self.opener.open(url)
        data = response.read()
        self.opener.close()

        return json.loads(data)

    def getATNSubscriptionPackages(self):
        url = self.urls['get_packages'].format(loginTicket=self.loginTicket())
        return self.getData(url)

    def login(self):
        atnPackageData = self.getATNSubscriptionPackages()

        success = False

        # User has 1 or more ATN package subscriptions
        if len(atnPackageData) > 0:
            success = atnPackageData[0]['Expiry'] is not None

        # Mark that the user has a successful login credential
        self.settings.setSetting('validLogin', str(success))

        return success

    def getAllChannels(self, packageNo):
        url = self.urls['get_channels'].format(packageNo=packageNo)
        return self.getData(url)

    def getChannelStreamUrl(self, channelID, packageNo):
        # Call get_channel service to fetch http cdn URL
        url = self.urls['get_channel'].format(loginTicket=self.loginTicket(), packageNo=packageNo, channelID=channelID)
        channelData = self.getData(url)

        return channelData["Message"]

########NEW FILE########
__FILENAME__ = UtilsChannelsFile
import os
import sys
from BeautifulSoup import BeautifulSoup

class Category:
    def __init__(self, categoryEl):
        self.title = categoryEl['title']

class Channel:
    def __init__(self, channelEl):
        self.id = channelEl['id']
        self.title = channelEl['title']
        self.thumbnail = channelEl['thumbnail']

class UtilsChannelsFile:

    _channelsXmlFile = os.path.join('resources', 'data', 'channels.xml')

    def __init__(self):
        self.pluginPath = sys.modules["__main__"].pluginPath

    def readChannelsFileAsSoup(self):
        filename = os.path.join(self.pluginPath, self._channelsXmlFile)
        handler = open(filename).read()
        return BeautifulSoup(handler)

    def getCategories(self):
        soup = self.readChannelsFileAsSoup()
        categoryListEl = soup.findAll('category')

        list = []

        for categoryEl in categoryListEl:
            list.append(Category(categoryEl))

        return list

    def getChannelsByCategoryTitle(self, categoryTitle):
        soup = self.readChannelsFileAsSoup()
        channelListEl = soup.find('category', {'title' : categoryTitle}).findAll('channel')

        list = []

        for channelEl in channelListEl:
            list.append(Channel(channelEl))

        return list
########NEW FILE########
__FILENAME__ = UtilsCommon
import sys

class UtilsCommon:
    def __init__(self):
        self.xbmc = sys.modules["__main__"].xbmc
        self.language = sys.modules["__main__"].language
        self.duration = 2000

    # Shows a more user-friendly notification
    def showMessage(self, heading, message):
        self.xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % (heading, message, self.duration))

    # Standardised error handler
    def showErrorMessage(self, title="", result="", status=500):
        if title == "":
            title = self.language(30600)    # "Error"

        if result == "":
            self.showMessage(title, self.language(30601))   # "Unknown Error"
        else:
            self.showMessage(title, result)
########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib
import time
import xbmcgui
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import cookielib
import datetime




__settings__ = xbmcaddon.Addon(id='plugin.video.bokra')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])



def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)



def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'http://upload.wikimedia.org/wikipedia/he/b/b1/Bokra.net_logo.jpg'))
	addDir('مسلسلات رمضان 2013','http://www.bokra.net/VideoCategory/125/مسلسلات_رمضان_2013.html',6,'http://images.bokra.net/bokra//28-11-2010/4shobek.jpg')
	addDir('مسلسلات عربية','http://www.bokra.net/VideoCategory/98/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA_%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9.html',1,'http://images.bokra.net/bokra//28-11-2010/4shobek.jpg')
	addDir('مسلسلات متنوعة','http://www.bokra.net/VideoCategory/43/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA.html',3,'http://images.bokra.net/bokra//28-11-2010/4shobek.jpg')
	addDir('افلام عربية','http://www.bokra.net/VideoCategory/100/أفلام_عربية.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir(' افلام فلسطينية','http://www.bokra.net/VideoCategory/18/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D9%81%D9%84%D8%B3%D8%B7%D9%8A%D9%86%D9%8A%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('افلام وثائقيه','http://www.bokra.net/VideoCategory/23/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D9%88%D8%AB%D8%A7%D8%A6%D9%82%D9%8A%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('افلام قديمة','http://www.bokra.net/VideoCategory/51/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D9%82%D8%AF%D9%8A%D9%85%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('افلام دينية','http://www.bokra.net/VideoCategory/24/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%AF%D9%8A%D9%86%D9%8A%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('مسرحيات','http://www.bokra.net/VideoCategory/44/%D9%85%D8%B3%D8%B1%D8%AD%D9%8A%D8%A7%D8%AA.html',4,'http://images.bokra.net/bokra/25.10.2011/msr7//DSCF0480.jpg')
	addDir('كليبات وحفلات','http://www.bokra.net/VideoCategory/118/%D9%83%D9%84%D9%8A%D8%A8%D8%A7%D8%AA_%D9%88%D8%AD%D9%81%D9%84%D8%A7%D8%AA.html',4,'http://images.bokra.net/new/402839.jpg')
	addDir('برامج تلفزيونية','http://www.bokra.net/VideoCategory/39/%D8%A8%D8%B1%D8%A7%D9%85%D8%AC_%D8%AA%D9%84%D9%81%D8%B2%D9%8A%D9%88%D9%86.html',3,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('افلام اطفال ','http://www.bokra.net/VideoCategory/57/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%A7%D8%B7%D9%81%D8%A7%D9%84.html',4,'http://images.bokra.net/bokra/15.8.2012/kods//1231.JPG')
	addDir('بكرا TV','http://www.bokra.net/VideoCategory/113/%D8%A8%D9%83%D8%B1%D8%A7_TV.html',1,'http://www.bokra.net/images//logobokra.png')
	addDir('مسلسلات كرتون','http://www.bokra.net/VideoCategory/56/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA_%D9%83%D8%B1%D8%AA%D9%88%D9%86.html',3,'http://images.bokra.net/bokra//16-10-2011/0WeddingCartoon1.jpg')
	addDir('مسلسلات اجنبية','http://www.bokra.net/VideoCategory/93/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA_%D8%A7%D8%AC%D9%86%D8%A8%D9%8A%D8%A9.html',3,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('مسلسلات تركية','http://www.bokra.net/VideoCategory/27/مسلسلات_تركية_.html',1,'http://images.bokra.net/bokra//28-11-2010/4shobek.jpg')
	addDir('افلام تركية','http://www.bokra.net/VideoCategory/48/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%AA%D8%B1%D9%83%D9%8A%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('افلام اجنبية','http://www.bokra.net/VideoCategory/46/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%A7%D8%AC%D9%86%D8%A8%D9%8A%D8%A9.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	addDir('منوعات','http://www.bokra.net/VideoCategory/45/%D9%85%D9%86%D9%88%D8%B9%D8%A7%D8%AA_+.html',4,'http://images.bokra.net/bokra//25-11-2012/0777777.jpg')
	
	
	
def retrive_max_page(url):
    try:
		req = urllib2.Request(url)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		url_ch=(re.compile('<span class="curpage">1</span>(.+?)</div>').findall(link))
		url_ch=str(url_ch)
		url_ch=(url_ch.split('>'))
		page_list=[]
		for items in  url_ch  :
			mystring=items.split('.') 
			for elements in mystring:
				if 'html' in elements:
					elements=str(elements)
					elements=elements.replace('html/', '')
					elements=elements.replace('"', '')
					elements=elements.strip()
					page_list.append(elements)
		
		
			return max(page_list)
    except Exception:
        return 1

def checkURL(url):
    p = urlparse(url)
    h = HTTP(p[1])
    h.putrequest('HEAD', p[2])
    h.endheaders()
    if h.getreply()[0] == 200: return 1
    else: return 0

def getCookies(url):
    #url ="http://bokra.net/Skip/?ref="+str(url)
    #Create a CookieJar object to hold the cookies
    cj = cookielib.CookieJar()
    #Create an opener to open pages using the http protocol and to process cookies.
    opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
    #create a request object to be used to get the page.
    req = Request(url)
    
    req = urllib2.Request(url)
    req.add_header('Host', 'bokra.net')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36')
    req.add_header('Referer', 'http://bokra.net/Skip/?ref='+str(url))
    req.add_header('Accept-Encoding', ' gzip,deflate,sdch')
    req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.6,en;q=0.4')
    f = opener.open(req)
    #see the first few lines of the page
    cj=str(cj).split("for")[0]
    cj=str(cj).split("Cookie")[2]
    cj=str(cj).strip()
    return cj

def indexNewSeries(url):
	match = False
	while (match == False):
		form_data = {'pass': '1'}
		params = urllib.urlencode(form_data)
		response = urllib2.urlopen(url, params)
		link = response.read()
		response.close()
		matchSerie = re.compile(' <div class="video_box">(.+?)<div class="spacer_videobox"></div>', re.DOTALL).findall(link)
		for item in matchSerie:
			myTempTarget=str(item).split('</div>')
			tempAll= str(myTempTarget[2]).replace('<div class ="textarea">', '').strip()
		   
			mypath=str(tempAll).replace('onClick="javascript: pageTracker._trackPageview(', 'del').replace(';" title="', 'del').replace('">  <div class="title">',"del")
			mypath=str(mypath).split('del')
			myName=str( mypath[2]).strip()
		   
			myUrl=str( mypath[0]).replace('<a href="', '').replace('"', '').strip()
			match = True 
			addLink(myName,myUrl,5,'')


	
def index(url):
	cookie = getCookies(url)
	match = False
	while (match == False):
		try:
			counter=0
			orig=url
			kurl=url
			maxvalue=int(retrive_max_page(kurl))+14
			final_items=[]
			for counter in range(0,int(maxvalue)):
				
				kurl=orig+'/'+str(counter)
				req = urllib2.Request(kurl)
				req.add_header('Host', 'www.bokra.net')
				req.add_header('Cache-Control', 'max-age=0')
				req.add_header('max-age=0', 'www.bokra.net')
				req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
				req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36')
				req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
				req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.6,en;q=0.4')
				req.add_header('Cookie', 'WRUID=699958697.415178061; __CT_Data=gpv=5&apv_40_www14=5&cpv_40_www14=2; __atuvc=6%7C7; __utma=1.2014423701.1391851573.1392150214.1392152127.9; __utmz=1.1391851573.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); noadvtday=0; '+str(cookie))
				response = urllib2.urlopen(req)
				link=response.read()
				response.close()
				
				url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="(.+?);"><img class="lazy" data-original="(.+?)" width="(.+?)" title="').findall(link))
				if len(str(url_ch))<3:
					url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="javascript:(.+?);"><img class="lazy" data-original="(.+?)" width="139" height="96"').findall(link))
				
				for items in url_ch:
				   
					for elements in items:
						
						for i in items:
							url= items[0].strip()
							name= items[1].replace("pageTracker._trackPageview('/VideoAlbum/","")
							name=name.replace("html","")
							name=name.replace(".')","")
							name=name.rsplit("/",1)
							name = name[1].strip() 
							
							image= items[2].strip()
							if image not in final_items:
								final_items.append(name)
								final_items.append(url)
								final_items.append(image)
				for items in final_items:
				#print elements
					if final_items.__len__()>0:
						
						name=final_items.pop(0)
						
					if final_items.__len__()>0:
						
						url=final_items.pop(0)
						
					if final_items.__len__()>0:
						
						image=final_items.pop(0)
						addDir(name,url,8,image)
						match = True
					
		except Exception:
			print "Film series Exception occured"


def indexRest(url):
	
	match = False
	while (match == False):
		try:
			counter=0
			orig=url
			kurl=url
			maxvalue=int(retrive_max_page(kurl))+14
			final_items=[]
			for counter in range(0,int(maxvalue)):
				
				kurl=orig+'/'+str(counter)
				form_data = {'pass': '1'}
				params = urllib.urlencode(form_data)
				response = urllib2.urlopen(kurl, params)
				link = response.read()
				response.close()
            	
				url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="(.+?);"><img class="lazy" data-original="(.+?)" width="(.+?)" title="').findall(link))
				if len(str(url_ch))<3:
					url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="javascript:(.+?);"><img class="lazy" data-original="(.+?)" width="139" height="96"').findall(link))
				
				for items in url_ch:
				   
					for elements in items:
						
						for i in items:
							url= items[0].strip()
							name= items[1].replace("pageTracker._trackPageview('/VideoAlbum/","")
							name=name.replace("html","")
							name=name.replace(".')","")
							name=name.rsplit("/",1)
							name = name[1].strip() 
							
							image= items[2].strip()
							if image not in final_items:
								final_items.append(name)
								final_items.append(url)
								final_items.append(image)
				for items in final_items:
				#print elements
					if final_items.__len__()>0:
						
						name=final_items.pop(0)
						
					if final_items.__len__()>0:
						
						url=final_items.pop(0)
						
					if final_items.__len__()>0:
						
						image=final_items.pop(0)
						match = True
						addDir(name,url,8,image)
					
		except Exception:
			print "Film series Exception occured"
		
		
def indexRamadanSeries(url):
	match = False
	while (match == False):
		form_data = {'pass': '1'}
		params = urllib.urlencode(form_data)
		response = urllib2.urlopen(url, params)
		link = response.read()
		response.close()
		matchSerie = re.compile(' <div class="items">(.+?)<div class="bigBanner">', re.DOTALL).findall(link)
		for items in matchSerie:
			
			myTarget=str( items).split('<div class="item">')
			for itr in myTarget:
				mySecTarget=str( itr).split('/></a></div>')
				mytempPath= mySecTarget[0] 
				if 'spacer8' not in str(mytempPath):
					mypath=str(mytempPath).replace('<div class="pic"><a href="', 'del').replace('onClick="javascript: pageTracker._trackPageview(', 'del').replace(');"><img class="lazy" data-original="',"del").replace('title="','del')
					mypath=str(mypath).split('del')
					finalImage=str( mypath[3]).split('" width=')[0]
					finalName=str( mypath[4]).replace('"', '').strip()
					finalImage=str(finalImage).strip()
					finalUrl=str( mypath[1]).replace('"', '').strip()
					match = True
					addDir(finalName,finalUrl,2,finalImage)

			
			
				
		
def index_films(url):
	
	
	try:
		counter=0
		orig=url
		kurl=url
		final_items=[]
		maxvalue=int(retrive_max_page(kurl))+12
		print "this is max  "+str(maxvalue)
		for counter in range(0,int(maxvalue)):
		   
			kurl=orig+'/'+str(counter)
		 	form_data = {'pass': '1'}
			params = urllib.urlencode(form_data)
			response = urllib2.urlopen(kurl, params)
			link = response.read()
			response.close()
			url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="javascript:(.+?);"><img class="lazy" data-original="(.+?)" width="139" height="96"').findall(link))
			
			
			for items in url_ch:
			   
				for elements in items:
					
					for i in items:
						url= items[0].strip()
						name= items[1].replace("pageTracker._trackPageview('/VideoAlbum/","")
						name=name.replace("html","")
						name=name.replace(".')","")
						name=name.rsplit("/",1)
						name = name[1].strip()  
						image= items[2].strip()
						if image not in final_items:
							final_items.append(name)
							final_items.append(url)
							final_items.append(image)
			for items in final_items:
			#print elements
				if final_items.__len__()>0:
					
					name=final_items.pop(0)
					
				if final_items.__len__()>0:
					
					url=final_items.pop(0)
					
				if final_items.__len__()>0:
					
					image=final_items.pop(0)
					addLink(name,url,5,image)
	except Exception:
		print "Film Exception occured"

			
def listSeries(url):
	match = False
	pointer=False
	stop = datetime.timedelta(seconds=10)  ## run for one second
	ctr = 0
	start_time = datetime.datetime.now()
	diff = start_time - start_time  ## initialize at zero
	while (match == False) or (pointer==False) or (diff < stop):
		counter=0
		ctr += 1
		diff = datetime.datetime.now() - start_time 
		final_items=[]
		kurl=url
		maxvalue=int(retrive_max_page(kurl))+5
		
		for counter in range(1,int(maxvalue)):
			test_url=kurl+'/'+str(counter)
			form_data = {'pass': '1'}
			params = urllib.urlencode(form_data)
			response = urllib2.urlopen(url, params)
			link = response.read()
			response.close()
			url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="javascript:(.+?);"><img class="lazy" data-original="(.+?)" width="').findall(link))
			if len(str(url_ch))<3:
				url_ch=(re.compile('<div class="pic"><a href="(.+?)" onClick="javascript:(.+?);"><img src="(.+?)" width="147" height="107').findall(link))
				for items in url_ch:
					for elements in items:
						for i in items:
							url= items[0].strip()
							name= items[1].replace("pageTracker._trackPageview('/VideoAlbum/","")
							name=name.replace("html","")
							name=name.replace(".')","")
							name=name.rsplit("/",1)
							name = name[1].strip()  
							image= items[2].strip()
							if url not in final_items:
								if 'اعلان' not in name:
									final_items.append(name)
									final_items.append(url)
									final_items.append(image)
									pointer=True
									match = False
				
				
					addLink(name,url,3,image)
				return pointer
					


def Playbokra(url):
		videoFilm = ""
		form_data = {'pass': '1'}
		params = urllib.urlencode(form_data)
		response = urllib2.urlopen(url, params)
		link = response.read()
		response.close()
		
		url_ch=(re.compile('<iframe class="video_frame" src="(.+?)&width=').findall(link))
		if 'GetVideoPlayer' in str( url_ch):
			myPath = str(url_ch).replace('[','').replace(']','').replace("'","").strip()+'&width=380&height=220'
			
			responseMypath = urllib2.urlopen(myPath)
			linkMypath = responseMypath.read()
			myVideo=(re.compile('<script type="text/javascript" charset=(.+?)" ></script>').findall(linkMypath))
			finalVideoId=str(myVideo).split('data-publisher-id="')
			
			myJson= str(finalVideoId[1]).split('"')
			data_publisher_id=str( myJson[0]).strip()
			data_video_id=str( myJson[2]).replace("']","").strip()
			playWirePath = 'http://cdn.playwire.com/v2/'+str(data_publisher_id)+'/config/'+str(data_video_id)+".json"
			responseJson = urllib2.urlopen(playWirePath)
			linkJson = responseJson.read()
			myJsonVidep = (re.compile('{"src":"(.+?)","vastSrc"').findall(linkJson))
			myJsonVidep=str( myJsonVidep).replace("['","").replace("']","").strip()
			listItem = xbmcgui.ListItem(path=str(myJsonVidep))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
			
		else:
			try:
				url_ch=str( url_ch).split("videoid=")[1]
			except:
				url_ch=str(url_ch).split("=")[1] 
				
				pass
			
			
			url_ch=str( url_ch).split("&width")[0]
			url_ch = str(url_ch).replace("']","").strip()
			if len(url_ch)>1:
				final_url="http://front.drubit.com/generalXML.php?autostart=0&videoid="+url_ch+"&ref="+str(url)
				form_data = {'pass': '1'}
				params = urllib.urlencode(form_data)
				response = urllib2.urlopen(final_url, params)
				link = response.read()
				response.close()
				url_ch=(re.compile('<file>(.+?)vtraffid').findall(link))
				
				url_ch=str(url_ch)
				url_ch= url_ch.replace("['", "")
				url_ch= url_ch.replace("']", "")
				url_ch=url_ch.replace("?","")
				videoFilm= url_ch.strip()
			listItem = xbmcgui.ListItem(path=str(videoFilm))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)

def getBokraRamadanEpos(url):
		match = False
		stop = datetime.timedelta(seconds=10)
		ctr = 0
		start_time = datetime.datetime.now()
		diff = start_time - start_time
		while (match == False) or (diff < stop):
			ctr += 1
			diff = datetime.datetime.now() - start_time 
			form_data = {'pass': '1'}
			params = urllib.urlencode(form_data)
			response = urllib2.urlopen(url, params)
			link = response.read()
			response.close()
			target= re.findall(r'<div class="item">(.*?)\s(.*?)</div>', link, re.DOTALL)
			counter = 0
			for item in target:
				if "Videos" in str(item):
					counter = counter + 1
			
			for item in target:
				if "Videos" in str(item):
					
					title = "الحلقة"+" "+str(counter)
					myData =  str(item).split('<div class="pic"><a href="')[1]
					myurl= str( myData).split('" onClick="')[0]
					myurl = str(myurl).strip()
					restof = str( myData).split('data-original="')[1]
					image = str( restof).split('" width="')[0]
					image = str(image).strip()
					addLink(title,myurl,5,image)
					counter = counter -1
					match = True
					
def getBokraSeries(url):
		match = False
		Cookie = str(getCookies(url))
		
		
		while (match == False):
			
			form_data = {'pass': '1'}
			params = urllib.urlencode(form_data)
			response = urllib2.urlopen(url, params)
			link = response.read()
			response.close()
            
			target= re.findall(r'<div class="video_box">(.*?)\s(.*?)</div>', link, re.DOTALL)
			counter = 0
			for items in target:
				counter = counter + 1
				
			for items in target:
				path = str( items).split('" onClick="')[0]
				path = str( path).split('href="')[1]
				path = str(path).strip()
				img = str(items).split('data-original="')[1]
				img = str(img).split('"')[0]
				img = str(img).strip()
				title = "الحلقة"+" "+str(counter)
				counter = counter -1
				match = True
				addLink(title,path,5,img)
                
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param



def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        index(url)
	
elif mode==2:
	print ""+url
	getBokraRamadanEpos(url)
			
			
elif mode==3:
	print ""+url
	indexRest(url)
elif mode==4:
	print ""+url
	index_films(url)

elif mode==5:
	print ""+url
	Playbokra(url)
elif mode==6:
	print ""+url
	indexRamadanSeries(url)
elif mode==7:
	print ""+url
	getBokraSeries(url)

elif mode ==8 :
		print ""+url
		indexNewSeries(url)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import httplib
import zlib,gzip



__settings__ = xbmcaddon.Addon(id='plugin.video.cartoonarabi')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner

httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)



def GetCartoonArabiSeries(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    myNames=[]
    url_target=(re.compile('<li class=""><a href="(.+?)" class="">(.+?)</a>').findall(link))

    for items in url_target:
        path=str( items[0]).strip()
        name=str( items[1]).strip()
        addDir(name,path,1,'')

def GetCartoonArabiEpos(url):
	for itr in range(1,6):
		req = urllib2.Request(url+'&page='+str(itr))
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		url_target=(re.compile('<a href="(.+?)" class="(.+?)class="pm-thumb-fix-clip"><img src="(.+?)" alt="(.+?)"').findall(link))
		for items in url_target:
			path=str( items[0]).strip()
			name=str( items[3]).strip()
			img=str( items[2]).strip()
			addLink(name,path,2,img)

def decode (page):
    encoding = page.info().get("Content-Encoding")
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        content = page.read()
        if encoding == 'deflate':
            data = StringIO.StringIO(zlib.decompress(content))
        else:
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
        page = data.read()

    return page


def playContent(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	link2=link
	response.close()
	url_target=(re.compile('<iframe frameborder=(.+?)src="(.+?)"></iframe>').findall(link))
	if 'syndication' in str( url_target):
		videoId=str( url_target[0]).split(',')
		videoId=str( videoId[1]).split('?syndication=')
		videoId=str( videoId[0] ).replace("'http://www.dailymotion.com/embed/video/", '').strip()
		playback_url = 'plugin://plugin.video.dailymotion_com/?mode=playVideo&url='+ str(videoId)
		listItem = xbmcgui.ListItem(path=str(playback_url))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	else:
		url_target=(re.compile('<embed src="(.+?)"(.+?)autostart="').findall(link))
		url2=str( url_target[0]).split(("',"))
		url2=url2[0]
		url2=str(url2).replace("('", '').strip()
		opener = urllib2.build_opener()
		opener.addheaders = [('Referer', 'http://www.4shared.com'),('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'), ('Accept-Encoding', 'gzip,deflate,sdch')]
		usock = opener.open(url2)
		url2 = usock.geturl()
		usock.close()
		videoFile=str( url2).split('&streamer=')[0]
		videoFile=str( videoFile).split('fileId=')[1]
		videoFile=str(videoFile).split('&image=')[0]
		videoFile=str(videoFile).split('&apiURL=')[0]
		videoFile=str( videoFile).strip()
		restUrl = str ('http://www.4shared.com/web/rest/files/' + videoFile + '/embed/meta.xml')
		req = urllib2.Request(restUrl)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		videoLink=response.read()
		response.close()
		videoLink = str( videoLink ).split('</previewUrl>')[0]
		videoLink = str( videoLink ).split('<previewUrl>')[1]
		playback_url = urllib.unquote ( videoLink )
		listItem = xbmcgui.ListItem(path=str(playback_url))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)


def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok



def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]

        return param

params=get_params()
url=None
name=None
mode=None



try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        GetCartoonArabiSeries('http://www.cartoonarabi.com/newvideos.php?&page=1')

elif mode==1:
        print ""+url
        GetCartoonArabiEpos(url)

elif mode==2:
		print ""+url
		playContent(url)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
########NEW FILE########
__FILENAME__ = default
import os
import xbmcplugin, xbmcgui, xbmcaddon
from xbmcswift2 import Plugin
from resources.lib.dailytube4u.api import DailyTube4uAPI

PLUGIN_NAME = 'DailyTube4U.com'
PLUGIN_ID = 'plugin.video.dailytube4u.com'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

api = DailyTube4uAPI()

@plugin.cached_route('/', TTL=60*5)
def list_all_channels():
    shows = api.get_channels()

    for show in shows:
        show['path'] = plugin.url_for('list_show_clips', show_path=show['path'])
        show['properties'] = [
            ('fanart_image', _art('fanart.jpg'))
        ]

    return shows

@plugin.cached_route('/list/shows/<show_path>', TTL=60)
def list_show_clips(show_path):
    clips = api.get_clips_for_show(show_path)

    plugin.set_content('movies')

    for clip in clips:
        clip['path'] = plugin.url_for('play_video', video_id=clip['path'])

    return clips

@plugin.route('/play/<video_id>/')
def play_video(video_id):
    url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % video_id
    plugin.log.info('Playing url: %s' % url)

    return plugin.set_resolved_url(url)

def _art(file, *args):
    return os.path.join(plugin.addon.getAddonInfo('path'), file, *args)

if __name__ == '__main__':
    plugin.run()

########NEW FILE########
__FILENAME__ = api
from scraper import (get_clips_for_show, get_channels)

'''The main API object. Useful as a starting point to get available subjects. '''
class DailyTube4uAPI():

    def get_channels(self):
        return get_channels()

    def get_clips_for_show(self, show_path):
        return get_clips_for_show(show_path)


########NEW FILE########
__FILENAME__ = scraper
from urllib2 import (urlopen )
from BeautifulSoup import BeautifulSoup
import re
from datetime import datetime, timedelta
from time import mktime, strptime

SCRAPE_SOURCE_URL = 'http://dailytube4u.com/%s'

def get(url):
    """Performs a GET request for the given url and returns the response"""
    conn = urlopen(url)
    resp = conn.read()
    conn.close()
    return resp

def _html(url):
    """Downloads the resource at the given url and parses via BeautifulSoup"""
    return BeautifulSoup(get(url), convertEntities=BeautifulSoup.HTML_ENTITIES)

def get_clips_for_show(show_path):

    # Workaround the HTML being malformed were an anchor tag has an attribute
    # that contains quotes in them e.g. <a title="Something \"in\" quotes" ..>...</a>
    content = get(SCRAPE_SOURCE_URL % show_path)
    content = content.replace("\\\"", "")
    html = BeautifulSoup(content, convertEntities=BeautifulSoup.HTML_ENTITIES)

    items = []

    for clipEl in html.find('div', { 'class' : 'maincharts' }).findAll('div', {'class' : re.compile(r'\bvideoBox\b')}):

        timespan = clipEl.find('span', { 'class' : 'timestamp' }).contents[0]

        try:
            h, m, s = map(int, timespan.split(':'))
        except :
            h = 0
            m, s = map(int, timespan.split(':'))

        duration = timedelta(hours=h, minutes=m, seconds=s)
        duration_min = duration.seconds / 60 # convert datetime to minutes

        thumbnail = clipEl.find('img')['data-src']
        title = clipEl.find('a', { 'class' : 'videotitlelink'})['title']

        # Extract youtube vid from thumbnail
        #   Wrap vid extraction in try/catch because a minority of clips use
        #   Dailymotion as a service; we are happy to ignore those at the moment
        try:
            matchObj = re.search( r'.*img.youtube.com\/vi\/(.*)/.*', thumbnail, re.M|re.I)
            video_id = matchObj.group(1)
            link = video_id

            items.append({
                'label': _parse_title(title),
                'path' : link,
                'thumbnail' : thumbnail,
                'info' : {
                    'duration' : str(duration_min)
                },
                'is_playable' : True
            })

        except Exception as ex:
            print 'Error parsing clip title and link: %s' % ex

    return items

def get_channels():
    html = _html(SCRAPE_SOURCE_URL % '')

    items = []

    for anchorEl in html.find('select', { 'class' : 'categsselectmn-mob' }).findAll('option')[1:]:
        items.append({
            'label': anchorEl.contents[0],
            'path' : anchorEl['value']
        })

    return items

def _parse_title(raw_title):

    try:
        # Handle Al-Qahera-Al-Youm title format
        # e.g. '2-27-02-2013 ....'
        m = re.search('(.*) ([0-9]{4}-[0-9][0-9]?-[0-9][0-9]?)-([1-9])', raw_title.encode('utf-8'), re.M|re.I)
        if m:
            title = m.group(1)
            release_date = _strptime(m.group(2))
            part = m.group(3)

            return '[[COLOR blue]Part %s[/COLOR], %s] %s ' % (part, release_date.strftime('%a %b %e'), title)

        # Handle Ibrahim Eisa, Huna Al Qahera tile format
        # e.g. '27-2-2013 ...'
        m = re.search('(.*) ([0-9]{4}-[0-9][0-9]?-[0-9][0-9]?)', raw_title.encode('utf-8'), re.M|re.I)
        if m:
            title = m.group(1)
            release_date = _strptime(m.group(2))

            return '[%s] %s ' % (release_date.strftime('%a %b %e'), title)

    except Exception as ex:
        print 'Error parsing clip title: %s' % ex

    # General cleanup
    # Replace \' with '
    return raw_title.replace("\\'", "'")

def _strptime(date_string, format='%Y-%m-%d'):
    timestamp = mktime(strptime(date_string, format))
    return datetime.fromtimestamp(timestamp)

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib
import time,itertools

__settings__ = xbmcaddon.Addon(id='plugin.video.dardarkom')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])



def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def getCategories():
	addDir('أفلام اجنبية اون لاين','http://www.dardarkom.com/filme-enline/filme-gharbi',1,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,7,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام هندية اون لاين','http://www.dardarkom.com/hindi-movies',4,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,7,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('افلام اسيوية','http://www.dardarkom.com/watch-asian-movies-on-line',3,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,30,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام اوروبية عالمية','http://www.dardarkom.com/watch-european-movies',1,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,7,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام انمي كرتون اون لاين','http://www.dardarkom.com/anime',1,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,7,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام وثائقية اون لاين','http://www.dardarkom.com/documentary-films',5,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,10,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام مصرية أون لاين','http://www.dardarkom.com/filme-enline/filme-egypt',3,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,30,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام مصرية قديمة أون لاين','http://www.dardarkom.com/filme-enline/classic',5,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,10,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام مغربية اون لاين','http://www.dardarkom.com/filme-enline/filme-maroc',5,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,7,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")
	addDir('أفلام عربية اون لاين','http://www.dardarkom.com/filme-enline/arabic',5,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',1,10,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A","N/A")

def removeArabicCharsFromString(myString):
    finalString=''
    allowedChars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- "
    for chars in myString:
        if chars in allowedChars:
            
            finalString= finalString+chars
            
    return str(finalString).strip()
	
	
def getImdbCred(movieName):
    
    movieName=str(movieName).replace(" ", "%20")
    url='http://www.omdbapi.com/?t='+str(movieName)
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    myImdbArray={"Year":"","Genre":"","Poster":"", "Plot":"","imdbRating":"","Actors":"","Runtime":"","Writer":"","Director":""}
    
    if 'Response":"False"' in str(link):
		myImdbArray["Year"]="No Year found"
		myImdbArray["Genre"]="No Genre found"
		myImdbArray["Poster"]="No Poster found"
		myImdbArray["Plot"]="No Plot found"
		myImdbArray["imdbRating"]="No Rating found"
		myImdbArray["Actors"]="No Actors found"
		myImdbArray["Runtime"]="No Runtime found"
		myImdbArray["Writer"]="No Writer found"
		myImdbArray["Director"]="No Director found"
		 
        
    if 'Response":"True"' in str(link):
        try:
            Year=(re.compile('"Year":"(.+?)",').findall(link))
            Year=str(Year).replace("['", "").replace("']", "").strip()
            myImdbArray["Year"]=Year
        except:
            myImdbArray["Year"]="No Year found"
            pass
        
        try:
            Genre=(re.compile('"Genre":"(.+?)",').findall(link))
            Genre=str(Genre).replace("['", "").replace("']", "").strip()
            myImdbArray["Genre"]=Genre
        except:
            myImdbArray["Genre"]="No Genre found"
            pass
        
        try:
            Poster=(re.compile('"Poster":"(.+?)",').findall(link))
            Poster=str(Poster).replace("['", "").replace("']", "").strip()
            myImdbArray["Poster"]=Poster
           
        except:
            myImdbArray["Poster"]="No Poster found"
            pass
        
        try:
            Plot=(re.compile('"Plot":"(.+?)",').findall(link))
            Plot=str(Plot).replace("['", "").replace("']", "").strip()
            myImdbArray["Plot"]=Plot
           
        except:
            myImdbArray["Plot"]="No Plot found"
            pass
        
        try:
            imdbRating=(re.compile('"imdbRating":"(.+?)",').findall(link))
            imdbRating=str(imdbRating).replace("['", "").replace("']", "").strip()
            myImdbArray["imdbRating"]=imdbRating
            
        except:
            myImdbArray["imdbRating"]="No Rating found"
            pass
        
        try:
            Actors=(re.compile('"Actors":"(.+?)",').findall(link))
            Actors=str(Actors).replace("['", "").replace("']", "").strip()
            myImdbArray["Actors"]=Actors
            
        except:
            myImdbArray["Actors"]="No Actors found"
            pass
        
        try:
            Writer=(re.compile('"Writer":"(.+?)",').findall(link))
            Writer=str(Writer).replace("['", "").replace("']", "").strip()
            myImdbArray["Writer"]=Writer
            
        except:
            myImdbArray["Writer"]="No Writer found"
            pass
        
        try:
            Director=(re.compile('"Director":"(.+?)",').findall(link))
            Director=str(Director).replace("['", "").replace("']", "").strip()
            myImdbArray["Director"]=Director
            
        except:
            myImdbArray["Director"]="No Director found"
            pass
        
        try:
            
            Runtime=(re.compile('"Runtime":"(.+?)",').findall(link))
            Runtime=str(Runtime).replace("['", "").replace("']", "").strip()
            
            if 'h' not in Runtime:
                Runtime=str(Runtime).replace("min", "").strip()
                myImdbArray["Runtime"]=Runtime 
                            
            elif 'h' and 'min' in Runtime:
                
                Runtime=str(Runtime).split("h")
                hours= 60*int(Runtime[0])
                minutes=str(Runtime[1]).replace("min", "")
                Runtime=int(minutes)+ hours
                myImdbArray["Runtime"]=Runtime
                        
            elif 'h' in Runtime and not "min" in Runtime:
                Runtime=str(Runtime).replace("h", "").strip()
                Runtime=60*int(Runtime)
                myImdbArray["Runtime"]=Runtime
                
        except:
            myImdbArray["Runtime"]="No Runtime found"
            pass
    return myImdbArray
	
def indexIndian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director):
	try:
		for counter in range(initial,max+1):
			dlg = xbmcgui.DialogProgress()
			line1 = 'Getting the movies...'
			dlg.create('In progress, Please wait...', line1)
			percent = int((counter * 100) / max)
			label = str(counter)+" out of "+str(max)+" pages"
			dlg.update(percent, line1, label)
			
			req = urllib2.Request(url+'/page/'+str(counter)+'/')
			response = urllib2.urlopen(req)
			link=response.read()
			url_target=(re.compile('<a href="(.+?)"><font color="(.+?)">(.+?)</font>   </a>').findall(link))
			url_2=(re.compile('<a href="(.+?)" onclick="return hs.expand').findall(link))
			target= re.findall(r'<div  style="font-family:Tahoma;font-size:9pt;color: #5C7287;;text-align:right;padding:10px; margin-right:10px;">(.*?)\s(.*?)</div>', link, re.DOTALL)
			name=''
			
			for (itr,items,it) in itertools.izip  (url_target,url_2,target):
				name=str( itr[2]).strip()
				path =str(itr[0]).strip()
				image=str(items).strip()
				plot=str( it[1]).strip()
				plot=str(plot).replace("&quot;","").replace(";quot&","")
				name2=removeArabicCharsFromString(name)
				myResult=(getImdbCred(name2))
				myFanart=str(myResult["Poster"]).strip()
				rating=str(myResult["imdbRating"]).strip()
				genre=str(myResult["Genre"]).strip()
				cast=str(myResult["Actors"]).strip()
				year=str(myResult["Year"]).strip()
				duration=str(myResult["Runtime"]).strip()
				writer=str(myResult["Writer"]).strip()
				director=str(myResult["Director"]).strip()
				genre = "[COLOR=%s]%s[/COLOR]" % ( "FF00FF00", genre  )
				year = "[COLOR=%s]%s[/COLOR]" % ( "FFFF0000  ", year  )
				if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
					addLink(name+" "+genre+" "+year,path,2,image,image,plot,' ',"N/A","N/A","N/A","N/A","N/A","N/A")
				else:
					plot2= getImdbCred(name2)["Plot"]
					combinedPlot=str(plot)+"\n"+"\n"+str(plot2)+"\n"+"Actors: "+str(cast)
					addLink(name+" "+genre+" "+year,path,2,image,myFanart,combinedPlot,rating,genre,cast,year,duration,writer,director)
					
			if len(str(name))<2:
				url_target2=(re.compile('<a href="(.+?)">(.+?)</a></center>').findall(link))
				url_2=(re.compile('<center><div class="boxshort"> <img src="(.+?)" alt="').findall(link))
				for (itr,items) in itertools.izip  (url_target2,url_2):
					path=str( itr[0]).strip()
					name=str( itr[1]).strip()
					image=str(items).strip()
					name2=removeArabicCharsFromString(name)
					myResult=(getImdbCred(name2))
					myFanart=str(myResult["Poster"]).strip()
					rating=str(myResult["imdbRating"]).strip()
					genre=str(myResult["Genre"]).strip()
					cast=str(myResult["Actors"]).strip()
					year=str(myResult["Year"]).strip()
					duration=str(myResult["Runtime"]).strip()
					writer=str(myResult["Writer"]).strip()
					director=str(myResult["Director"]).strip()
					genre = "[COLOR=%s]%s[/COLOR]" % ( "FF00FF00", genre  )
					year = "[COLOR=%s]%s[/COLOR]" % ( "FFFF0000  ", year  )
					if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
						addLink(name+" "+genre+" "+year,path,2,image,image,plot,' ',"N/A","N/A","N/A","N/A","N/A","N/A")
					else:
						plot2= getImdbCred(name2)["Plot"]
						combinedPlot=str(plot)+"\n"+"\n"+str(plot2)+"\n"+"Actors: "+str(cast)
						addLink(name+" "+genre+" "+year,path,2,image,myFanart,combinedPlot,rating,genre,cast,year,duration,writer,director)
	except:
		pass
				
	initial=initial+10
	max=max + 10
	
	addDir('<<<< اضهار افلام جديدة',url,4,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',initial,max,'DESCRIPTION','0.0')

	
def indexOldEgyptian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director):
	try:
		for counter in range(initial,max+1):
			dlg = xbmcgui.DialogProgress()
			line1 = 'Getting the movies...'
			dlg.create('In progress, Please wait...', line1)
			percent = int((counter * 100) / max)
			label = str(counter)+" out of "+str(max)+" pages"
			dlg.update(percent, line1, label)
			
			req = urllib2.Request(url+'/page/'+str(counter)+'/')
			response = urllib2.urlopen(req)
			link=response.read()
			url_target=(re.compile('<a href="(.+?)"><font color="(.+?)">(.+?)</font>   </a>').findall(link))
			url_2=(re.compile('<a href="(.+?)" onclick="return hs.expand').findall(link))
			target= re.findall(r'<div  style="font-family:Tahoma;font-size:9pt;color: #5C7287;;text-align:right;padding:10px; margin-right:10px;">(.*?)\s(.*?)</div>', link, re.DOTALL)
			name=''
			
			for (itr,items,it) in itertools.izip  (url_target,url_2,target):
				name=str( itr[2]).strip()
				path =str(itr[0]).strip()
				image=str(items).strip()
				plot=str( it[1]).strip()
				plot=str(plot).replace("&quot;","").replace(";quot&","")
				name2=removeArabicCharsFromString(name)
				myResult=(getImdbCred(name2))
				myFanart=str(myResult["Poster"]).strip()
				rating=str(myResult["imdbRating"]).strip()
				genre=str(myResult["Genre"]).strip()
				cast=str(myResult["Actors"]).strip()
				year=str(myResult["Year"]).strip()
				duration=str(myResult["Runtime"]).strip()
				writer=str(myResult["Writer"]).strip()
				director=str(myResult["Director"]).strip()
				if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
					addLink(name,path,2,image,image,plot,' ',"N/A","N/A","N/A","N/A","N/A","N/A")
				else:
					plot2= getImdbCred(name2)["Plot"]
					combinedPlot=str(plot)+"\n"+"\n"+str(plot2)+"\n"+"Actors: "+str(cast)
					addLink(name,path,2,image,myFanart,combinedPlot,rating,genre,cast,year,duration,writer,director)
					
			if len(str(name))<2:
				url_target2=(re.compile('<a href="(.+?)">(.+?)</a></center>').findall(link))
				url_2=(re.compile('<center><div class="boxshort"> <img src="(.+?)" alt="').findall(link))
				for (itr,items) in itertools.izip  (url_target2,url_2):
					path=str( itr[0]).strip()
					name=str( itr[1]).strip()
					image=str(items).strip()
					name2=removeArabicCharsFromString(name)
					myResult=(getImdbCred(name2))
					myFanart=str(myResult["Poster"]).strip()
					rating=str(myResult["imdbRating"]).strip()
					genre=str(myResult["Genre"]).strip()
					cast=str(myResult["Actors"]).strip()
					year=str(myResult["Year"]).strip()
					duration=str(myResult["Runtime"]).strip()
					writer=str(myResult["Writer"]).strip()
					director=str(myResult["Director"]).strip()
					if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
						addLink(name,path,2,image,image,plot,' ',"N/A","N/A","N/A","N/A","N/A","N/A")
					else:
						plot2= getImdbCred(name2)["Plot"]
						combinedPlot=str(plot)+"\n"+"\n"+str(plot2)+"\n"+"Actors: "+str(cast)
						addLink(name,path,2,image,myFanart,combinedPlot,rating,genre,cast,year,duration,writer,director)
	except:
		pass
	initial=initial+10
	max=max + 10
	addDir('<<<< اضهار افلام جديدة',url,5,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',initial,max,'DESCRIPTION','0.0')

	
def indexSeries(url,initial,max,plot,rating,genre,cast,year,duration,writer,director):
	try:
	
		for counter in range(initial,max+1):
			url_target=""
			url_2=""
			target=""
			name=''
			fanart=''
			link=""
			
			dlg = xbmcgui.DialogProgress()
			line1 = 'Getting the movies...'
			dlg.create('In progress, Please wait...', line1)
			percent = int((counter * 100) / max)
			label = str(counter)+" out of "+str(max)+" pages"
			dlg.update(percent, line1, label)
			
			try:
				req = urllib2.Request(url+'/page/'+str(counter)+'/')
				response = urllib2.urlopen(req)
				link=response.read()
				url_target=(re.compile('<a href="(.+?)"><font color="(.+?)">(.+?)</font>   </a>').findall(link))
				url_2=(re.compile('<a href="(.+?)" onclick="return hs.expand').findall(link))
				target= re.findall(r'<div  style="font-family:Tahoma;font-size:9pt;color: #5C7287;;text-align:right;padding:10px; margin-right:10px;">(.*?)\s(.*?)</div>', link, re.DOTALL)
				
				
			except:
				pass
				
			
			for (itr,items,it) in itertools.izip  (url_target,url_2,target):
				name=str( itr[2]).strip()
				
				path =str(itr[0]).strip()
				image=str(items).strip()
				plot=str( it[1]).strip()
				plot=str(plot).replace("&quot;","").replace(";quot&","")
				name2=removeArabicCharsFromString(name)
				myResult=(getImdbCred(name2))
				myFanart=str(myResult["Poster"]).strip()
				rating=str(myResult["imdbRating"]).strip()
				genre=str(myResult["Genre"]).strip()
				cast=str(myResult["Actors"]).strip()
				year=str(myResult["Year"]).strip()
				duration=str(myResult["Runtime"]).strip()
				writer=str(myResult["Writer"]).strip()
				director=str(myResult["Director"]).strip()
				genre = "[COLOR=%s]%s[/COLOR]" % ( "FF00FF00", genre  )
				year = "[COLOR=%s]%s[/COLOR]" % ( "FFFF0000  ", year  )
				if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
					addLink(name2+" "+genre+" "+year,path,2,image,image,plot,'N/A','N/A','N/A','N/A','N/A')
				else:
					plot2= getImdbCred(name2)["Plot"]
					combinedPlot=str(plot)+"\n"+"\n"+str(plot2)+"\n"+"Actors: "+str(cast)
					addLink(name2+" "+genre+" "+year,path,2,image,myFanart,combinedPlot,rating,genre,cast,year,duration,writer,director)
							
			if len(str(name))<2:
				url_target2=(re.compile('<a href="(.+?)">(.+?)</a></center>').findall(link))
				url_2=(re.compile('<center><div class="boxshort"> <img src="(.+?)" alt="').findall(link))
				for (itr,items) in itertools.izip  (url_target2,url_2):
					path=str( itr[0]).strip()
					name=str( itr[1]).strip()
					image=str(items).strip()
					name2=removeArabicCharsFromString(name)
					myResult=(getImdbCred(name2))
					genre = "[COLOR=%s]%s[/COLOR]" % ( "FF00FF00", genre  )
					year = "[COLOR=%s]%s[/COLOR]" % ( "FFFF0000  ", year  )
					if  myResult["Plot"]=="No Plot found" and myResult["Poster"]=="No Poster found" and rating=="No Rating found" and genre=="No Genre found" and year=="No Year found" and cast=="No Actors found" and duration=="No Runtime found" and writer=="No Writer found" and director=="No Director found":
						addLink(name2+" "+genre+" "+year,path,2,image,image," ","N/A","N/A","N/A","N/A")
					else:
						myFanart=str(myResult["Poster"]).strip()
						plot2= getImdbCred(name2)["Plot"]
						rating=str(myResult["imdbRating"]).strip()
						genre=str(myResult["Genre"]).strip()
						cast=str(myResult["Actors"]).strip()
						plot2=str(plot2)+"\n"+"\n"+"Actors: "+str(cast)
						year=str(myResult["Year"]).strip()
						duration=str(myResult["Runtime"]).strip()
						writer=str(myResult["Writer"]).strip()
						director=str(myResult["Director"]).strip()
						genre = "[COLOR=%s]%s[/COLOR]" % ( "FF00FF00", genre  )
						year = "[COLOR=%s]%s[/COLOR]" % ( "FFFF0000  ", year  )
						addLink(name2+" "+genre+" "+year,path,2,image,myFanart,plot2,rating,genre,cast,year,duration,writer,director)
			
					
	except:
		pass
	initial=initial+7
	max=max + 7
	addDir(' <<<< اضهار افلام جديدة',url,1,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',initial,max,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A")
		

def indexEgyptian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director):
	try:
		for counter in range(initial,max+1):
			
			dlg = xbmcgui.DialogProgress()
			line1 = 'Getting the movies...'
			dlg.create('In progress, Please wait...', line1)
			percent = int((counter * 100) / max)
			label = str(counter)+" out of "+str(max)+" pages"
			dlg.update(percent, line1, label)
			req = urllib2.Request(url+'/page/'+str(counter)+'/')
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			url_target=(re.compile('<a href="(.+?)" onclick="(.+?)title="(.+?)"').findall(link))
			url_path=(re.compile('<a href="(.+?)">شاهد الأن</a>').findall(link))
			targetPlot= re.findall(r'<div  style="font-family:Tahoma;font-size:9pt;color: #5C7287;;text-align:right;padding:10px; margin-right:10px;" dir="rtl">(.*?)\s(.*?)</div>', link, re.DOTALL)
			
			for (itr,i,trpl) in itertools.izip  (url_target,url_path,targetPlot):
				image=str( itr[0]).strip()
				name=str( itr[2]).strip()
				path=str(i).strip()
				plot=str( trpl[1]).strip()
				plot=str(plot).replace("&quot;","").replace(";quot&","")
				addLink(name,path,2,image,image,plot," ","N/A","N/A","N/A","N/A","N/A","N/A")
	
	except:
		pass
		
	initial=initial+30
	max=max + 30
	addDir(' <<<< اضهار افلام جديدة',url,3,'http://www.theonestopfunshop.com/product_images/uploaded_images/movie-night.jpg',initial,max,'DESCRIPTION','0.0',"N/A","N/A","N/A","N/A","N/A")	
	
			
def playDarDar(url):
	try:
		req1 = urllib2.Request(url)
		response1 = urllib2.urlopen(req1)
		link1=response1.read()
		url_target1=(re.compile('<a href="(.+?)" target="_blank"><img src=').findall(link1))
		myurl=str( url_target1[0]).strip()
		print myurl
		req2 = urllib2.Request(myurl)
		response2 = urllib2.urlopen(req2)
		link2=response2.read()
		url_target2=(re.compile('<div id="(.+?)src="(.+?)" width=').findall(link2))
		url_target2=str( url_target2).split(',')[1]
		url_target2=str( url_target2).replace("'", '').replace("')]", "").replace(')]','').strip()
		print url_target2
		req3 = urllib2.Request(url_target2)
		response3 = urllib2.urlopen(req3)
		link3=response3.read()
		url_target3=(re.compile('<param name="flashvars" value="(.+?)"></param>').findall(link3))
		final= str(url_target3).split('&amp;')
		for mp4 in final:
			if 'url360=' in str(mp4):
				playpath=str( mp4).replace('url360=', '')
				listItem = xbmcgui.ListItem(path=str(playpath))
				xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	except:
		pass
		xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('Info','This film could not be played!!!',4000, 'http://blog.spamfighter.com/wp-content/uploads/g1-error-768519.png'))
	            
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLink(name,url,mode,iconimage,fanart,plot='',rating="",genre="",cast="",year="",duration="",writer="",director=""):
	ok=True
	u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
	
	liz=xbmcgui.ListItem(name,iconImage="DefaultVideo.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot":plot,"rating":rating,"genre":genre,"Cast":cast,"year":year,"duration":duration,"writer":writer,"director":director})
	liz.setProperty( "Fanart_Image", fanart )
	liz.setProperty("IsPlayable","true");
	ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
	return ok


def addDir(name,url,mode,iconimage,initial,max,plot='',rating="",genre="",cast="",year="",duration="",writer="",director=""):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&initial="+str(initial)+"&max="+str(max)+"&rating="+str(rating)+"&genre="+str(genre)+"&Cast="+str(cast)+"&year="+str(year)+"&duration="+str(duration)+"&writer="+str(writer)+"&director="+str(director)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name,"Plot":plot,"rating":rating,"genre":genre,"Cast":cast,"year":year,"duration":duration,"writer":writer,"director":director} )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None
initial=None
max=None
rating=None
cast=None
year=None
genre=None
duration=None
writer=None
director=None

	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
	
try:
        mode=int(params["mode"])
except:
        pass
try:
        initial=int(params["initial"])
except:
        pass
try:
        max=int(params["max"])
except:
        pass
try:
        plot=urllib.unquote_plus(params["plot"])
except:
        plot=''
try:
        rating=urllib.unquote_plus(params["rating"])
except:
        rating=''

try:
        year=urllib.unquote_plus(params["year"])
except:
        year=''
try:
        cast=urllib.unquote_plus(params["cast"])
except:
        pass
try:
        genre=urllib.unquote_plus(params["genre"])
except:
        genre=''
		
try:
        duration=urllib.unquote_plus(params["duration"])
except:
        duration=''
		
try:
        writer=urllib.unquote_plus(params["writer"])
except:
        writer=''

try:
        director=urllib.unquote_plus(params["director"])
except:
        director=''
		


print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)
print "initial: "+str(initial)
print "max: "+str(max)
print "plot: "+str(plot)
if mode==None or url==None or len(url)<1:
        print ""
        getCategories()
       
elif mode==1:
        print ""+url
        indexSeries(url,initial,max,plot,rating,genre,cast,year,duration,writer,director)
elif mode==2:
        print ""+url
        playDarDar(url)
		
elif mode==3:
        print ""+url
        indexEgyptian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director)

elif mode==4:
        print ""+url
        indexIndian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director)
		
elif mode==5:
        print ""+url
        indexOldEgyptian(url,initial,max,plot,rating,genre,cast,year,duration,writer,director)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import httplib



__settings__ = xbmcaddon.Addon(id='plugin.video.dramacafe')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
	
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def GetCategories():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely, Nobody has the right to charge you for this addon', 16000, 'https://pbs.twimg.com/profile_images/1908891822/R5MpO.gif'))
	url='http://www.online.dramacafe.tv/index.html'
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Host', 'www.online.dramacafe.tv')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Cookie', 'popNum=8; __atuvc=6%7C34%2C3%7C35; popundr=1; PHPSESSID=478ff84e532ad811df5d63854f4f0fe1; watched_video_list=MTgzNDY%3D')
	response = urllib2.urlopen(req)
	link=response.read()
	mylist=[]
	
	url_categories=(re.compile('<li class="topcat"><a href="(.+?)" class="topcat">(.+?)</a>').findall(link))
	url_categories_2=(re.compile('<li class=""><a href="(.+?)" class="">(.+?)</a>').findall(link))
	for items in url_categories:
		catName= str(items[1]).strip()
		catPath=str(items[0]).strip()
		if 'افلام اجنبية' not in catName:
			if 'Movies Pack | سلاسل افلام' not in catName:
				if 'افلام هندية' not in catName:
					if 'Movies | افلام الانمي المدبلجة والمترجمة' not in catName:
						if catName not in mylist:
								mylist.append(catName)
								if 'مسلسلات'  in catName:
									addDir(catName,str(catPath),1,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
								
								if 'افلام'  in catName:
									addDir(catName,str(catPath),4,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
								if 'المسرحيات'  in catName:
									addDir(catName,str(catPath),1,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
			
				
	for itr in url_categories_2:
		catName_2= str(itr[1]).strip()
		catPath_2=str(itr[0]).strip()
		if 'افلام اجنبية' not in catName_2:
			if 'Movies Pack | سلاسل افلام' not in catName_2:
				if 'افلام هندية' not in catName_2:
					if 'Movies | افلام الانمي المدبلجة والمترجمة' not in catName_2:
					
						if catName_2 not in mylist:
							mylist.append(catName_2)
							if 'Movies' in catName_2:
								addDir(catName_2,str(catPath_2),4,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
							if 'الدراما' in catName_2:
								addDir(catName_2,str(catPath_2),1,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
							if 'افلام'  in catName_2:
								addDir(catName_2,str(catPath_2),4,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
							if 'المسرحيات'  in catName_2:
								addDir(catName_2,str(catPath_2),1,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
							if 'مسلسلات'  in catName_2:
									addDir(catName_2,str(catPath_2),1,'http://www.portal.dramacafe.tv/themes/nhstyle_4cols/images/header/header.jpg')
				
def indexSerie(url):
    firstPart=str(url).split('videos')[0]
    nameList=[]
    secPart='videos-'
    lastPart='-date.html'
    counter=0
    for myIndex in range (0,20):
        counter=counter+1
        url=str(firstPart)+secPart+str(counter)+(lastPart)
        print url
        if checkUrl(url):
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
            req.add_header('Host', 'www.online.dramacafe.tv')
            req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            req.add_header('Cookie', 'popNum=8; __atuvc=6%7C34%2C3%7C35; popundr=1; PHPSESSID=478ff84e532ad811df5d63854f4f0fe1; watched_video_list=MTgzNDY%3D')
            response = urllib2.urlopen(req)
            link=response.read()
            target= re.findall(r'<span class="pm-video-li-thumb-info">(.*?)\s(.*?) <div class="pm-video-attr">', link, re.DOTALL)
            finalSerieImage=''
            for items in target:
                if str( items[1].split('</span>')[1]):
                    myPath=str( items[1].split('</span>')[1])
                    entirePath=str( myPath).replace("str( items[1].split('</span>')[1])", ' deLiM ').replace('" class="pm-thumb-fix pm-thumb-145"><span class="pm-thumb-fix-clip"><img src="',' deLiM ').replace('" alt="',' deLiM ').replace('" width="',' deLiM ')
                    entirePath=str(entirePath).split(' deLiM ')
                    try:
                        finalSerieImage=str( entirePath[1]).strip()
                    except:
                        finalSerieImage=''
                    if len(entirePath)>1:
                        finalSeriePath=str( entirePath[0]).replace('<a href="', '').strip()
                        finalSerieName=str( entirePath[2]).strip()
                        serieName= str(finalSerieName).split('-')[0]
                        serieName=str(serieName).strip()
                        if ('شارة' and 'الافلام' and 'افلام' and 'المسرحيات ' ) not in serieName:
                            if serieName not in nameList:
                                nameList.append(serieName)
                                addDir(serieName,finalSeriePath,2,finalSerieImage)
								

def indexFilm(url):
    firstPart=str(url).split('videos')[0]
    nameList=[]
    secPart='videos-'
    lastPart='-date.html'
    counter=0
    for myIndex in range (0,20):
        counter=counter+1
        url=str(firstPart)+secPart+str(counter)+(lastPart)
        print url
        if checkUrl(url):
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
            req.add_header('Host', 'www.online.dramacafe.tv')
            req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            req.add_header('Cookie', 'popNum=8; __atuvc=6%7C34%2C3%7C35; popundr=1; PHPSESSID=478ff84e532ad811df5d63854f4f0fe1; watched_video_list=MTgzNDY%3D')
            response = urllib2.urlopen(req)
            link=response.read()
            target= re.findall(r'<span class="pm-video-li-thumb-info">(.*?)\s(.*?) <div class="pm-video-attr">', link, re.DOTALL)
            finalSerieImage=''
            for items in target:
                if str( items[1].split('</span>')[1]):
                    myPath=str( items[1].split('</span>')[1])
                    entirePath=str( myPath).replace("str( items[1].split('</span>')[1])", ' deLiM ').replace('" class="pm-thumb-fix pm-thumb-145"><span class="pm-thumb-fix-clip"><img src="',' deLiM ').replace('" alt="',' deLiM ').replace('" width="',' deLiM ')
                    entirePath=str(entirePath).split(' deLiM ')
                    try:
                        finalSerieImage=str( entirePath[1]).strip()
                    except:
                        finalSerieImage=''
                    if len(entirePath)>1:
                        finalSeriePath=str( entirePath[0]).replace('<a href="', '').strip()
                        finalSerieName=str( entirePath[2]).strip()
                        serieName= str(finalSerieName).split('-')[0]
                        serieName=str(serieName).strip()
                        if ('شارة' and 'الافلام' and 'افلام' and 'المسرحيات ' ) not in serieName:
                            if serieName not in nameList:
                                nameList.append(serieName)
                                addLink(serieName,finalSeriePath,3,finalSerieImage)



def checkUrl(url):
	p = urlparse(url)
	conn = httplib.HTTPConnection(p.netloc)
	conn.request('HEAD', p.path)
	resp = conn.getresponse()
	return resp.status < 400
								
def getEpos(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Host', 'www.online.dramacafe.tv')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Cookie', 'popNum=8; __atuvc=6%7C34%2C3%7C35; popundr=1; PHPSESSID=478ff84e532ad811df5d63854f4f0fe1; watched_video_list=MTgzNDY%3D')
	response = urllib2.urlopen(req)
	link=response.read()
	target= re.findall(r'<span class="pm-video-li-thumb-info">(.*?)\s(.*?)<h3 dir=', link, re.DOTALL)
	for items in target:
		myItems=str( items[1]).split('</span>')[1]
		myItems=str(myItems).replace('<a href="', ' DELIM ').replace('" class="pm-thumb-fix pm-thumb-74"><span class="pm-thumb-fix-clip"><img src="', ' DELIM ').replace('" alt="', ' DELIM ').replace('" width="74"><span class="vertical-align">', ' DELIM ')
		myItems=str(myItems).split(' DELIM ')
		myPath=str( myItems[1]).strip()
		myImage=str( myItems[2]).strip()
		myName=str( myItems[3]).strip()
		if '|' not in myName:
			addLink(myName,myPath,3,myImage)


def playContent(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Host', 'www.online.dramacafe.tv')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Cookie', 'popNum=8; __atuvc=6%7C34%2C3%7C35; popundr=1; PHPSESSID=478ff84e532ad811df5d63854f4f0fe1; watched_video_list=MTgzNDY%3D')
	response = urllib2.urlopen(req)
	link=response.read()
	url_video=(re.compile('<iframe frameborder="0" width="560" height="317" src="(.+?)"></iframe>').findall(link))
	try:
		url_video=str(url_video).split('video/')
		url_video=str(url_video[1]).split('?syndication=')[0]
		url_video=str(url_video).strip()
		playback_url = 'plugin://plugin.video.dailymotion_com/?mode=playVideo&url='+ str(url_video)
		listItem = xbmcgui.ListItem(path=str(playback_url))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	except:
		addLink('No video was found !','',334,'http://portal.aolcdn.com/p5/forms/4344/2af553bd-0f81-41d1-a061-8858924b83ca.jpg')
	
		
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param



def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        GetCategories()
       
elif mode==1:
        print ""+url
        indexSerie(url)
	
elif mode==2:
		print ""+url
		getEpos(url)
			
elif mode==3:
	print ""+url
	playContent(url)
	
elif mode==4:
	print ""+url
	indexFilm(url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib
import time

__settings__ = xbmcaddon.Addon(id='plugin.video.dubaitv')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
	
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def checkUrl(url):
    p = urlparse(url)
    conn = httplib.HTTPConnection(p.netloc)
    conn.request('HEAD', p.path)
    resp = conn.getresponse()
    return resp.status < 400



def getCategories():
    
    url='http://vod.dmi.ae/'
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    response = urllib2.urlopen(req)
    link=response.read()
    url_categories=(re.compile('<li><a href="/(.+?)">(.+?)</a></li>').findall(link))
    for myItems in url_categories:
        myTempObj= str(myItems[0])
        myTempName= str(myItems[1])
        if 'category' in myTempObj:
            
            catPath ='http://vod.dmi.ae/'+ myTempObj
            catPath=str(catPath).strip()
            catName=myTempName
            catName=str(catName).strip()
            addDir(catName,catPath,1,'http://1.bp.blogspot.com/-2dgsZzVtZdo/TsVKjel898I/AAAAAAAAA90/A0bD4FRKHuU/s200/dubai-tv.jpg')
            
        
def getSeries(url):
    counter=0
    
    for sites in range(0,50):
        counter=counter+1
        url=url+'/'+str(counter)
        if checkUrl(url):
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
            req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            response = urllib2.urlopen(req)
            link=response.read()
            target= re.findall(r'<div class="video" style="height: 140px;"(.*?)\s(.*?)</div>', link, re.DOTALL)
            for items in target:
				myPath=str( items[1]).replace('<div class="thumb">', ' DELIM ').replace('<img src="', ' DELIM ').replace('alt="', ' DELIM ')
				myPath=str(myPath).split(' DELIM ')
				try:
					theUrl='http://vod.dmi.ae/'+str(myPath[1]).replace('<a href="/', '').replace('">', '').strip()
					theImage=str(myPath[2]).replace('<img src="', '').replace('"', '').strip()
					theName=str(myPath[3]).replace('" />', '').strip()
					addDir(theName,theUrl,2,theImage)
				except:
					pass

def getEpisodes(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    response = urllib2.urlopen(req)
    link=response.read()
    target= re.findall(r'<div class="thumb">(.*?)\s<div class="icon"></div>', link, re.DOTALL)
    for items in target:
        myPath=str(items).replace('<a href="', ' DELIM ').replace('"><img src="', ' DELIM ').replace('" alt="', ' DELIM ').replace('" /></a>', ' DELIM ')
        myPath=str(myPath).split(' DELIM ')
        path='http://vod.dmi.ae'+str( myPath[1]).strip()
        thumbNail=str( myPath[2]).strip()
        serieName=str( myPath[3]).strip()
        addLink(serieName,path,3,thumbNail)
        
def playVideo(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	response = urllib2.urlopen(req)
	link=response.read()
	target= re.findall(r'var mediaItem =(.*?)\jwplayer.key =', link, re.DOTALL)
	videoPath=str( target).split('"fileUrl":"')[1]
	videoPath=str(videoPath).split('?cdnParams=')[0]
	videoPath=str(videoPath).replace('\/','deli').strip()
	videoPath=str(videoPath).replace('\deli','/').strip()
	listItem = xbmcgui.ListItem(path=str(videoPath))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	            
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None

from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
try:
    import json
except:
    import simplejson as json
	
	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        getCategories()
       
elif mode==1:
        print ""+url
        getSeries(url)
	
elif mode==2:
        getEpisodes(url)
		
elif mode==3:
        print ""+url
        playVideo(url)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
import urllib,urllib2,re,os,cookielib
import xbmcplugin,xbmcgui,xbmcaddon
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP

addon = xbmcaddon.Addon('plugin.video.glarab')
profile = xbmc.translatePath(addon.getAddonInfo('profile'))

sys.path.append(os.path.join(addon.getAddonInfo('path'), 'resources'))
import urllib3, workerpool

__settings__ = xbmcaddon.Addon(id='plugin.video.glarab')
home = __settings__.getAddonInfo('path')
icon = xbmc.translatePath( os.path.join( home, 'icon.png' ) )

if __settings__.getSetting('paid_account') == "true":
        if (__settings__.getSetting('username') == "") or (__settings__.getSetting('password') == ""):
                xbmc.executebuiltin("XBMC.Notification('GLArab','Enter username and password.',30000,"+icon+")")
                __settings__.openSettings()

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

def login():
	resp = opener.open('http://www.glarab.com/')
	html_data = resp.read();
	soup = BeautifulSoup(html_data)
	eventVal = soup.find('input',id='__EVENTVALIDATION',type='hidden')
	viewState = soup.find('input',id='__VIEWSTATE',type='hidden')
	loginURL = 'http://www.glarab.com/homepage.aspx'
	data = '__EVENTARGUMENT=&__EVENTTARGET=&__EVENTVALIDATION=%s&__VIEWSTATE=%s&pageHeader%%24ScriptManager1=pageHeader%%24UpdatePanel1%%7CpageHeader%%24buttonLogin&pageHeader%%24buttonLogin=%%20&pageHeader%%24txtPassword=%s&pageHeader%%24txtUsername=%s' % (urllib.quote(eventVal['value']), urllib.quote(viewState['value']), urllib.quote(__settings__.getSetting('password')), urllib.quote(__settings__.getSetting('username')))
	opener.open(loginURL, data)
	resp = opener.open('http://www.glarab.com/ajax.aspx?channel=tvlist&type=reg&genre=1')
	html_data = resp.read();
	return html_data != 'NoAccess'	

def getCategories():
	if __settings__.getSetting('paid_account') == "true":
		while not login():
        	        xbmc.executebuiltin("XBMC.Notification('GLArab','INVALID username and/or password.',30000,"+icon+")")
	                __settings__.openSettings()
		try:
			resp = opener.open('http://www.glarab.com/ajax.aspx?channel=tvlist&type=reg&genre=1')
			html_data = resp.read();
			soup = BeautifulSoup(html_data)
			categories = soup.find('ul',id='categoryContainer')
			pattern = re.compile('tvChannelsStart\(\'(.*?)\'\);')
			for li in categories:
				name = li.contents[0].strip()
				dirurl = pattern.search(li['onclick']).groups()[0]
				dirurl = 'http://www.glarab.com/ajax.aspx?channel=tv&genre=' + dirurl
				addDir(name,dirurl,1)			
		except:
			return
	else:
		try:
			resp = opener.open('http://www.glarab.com/ajax.aspx?channel=tv&type=free&genre=1')
			html_data = resp.read();
			soup = BeautifulSoup(html_data)
			categories = soup.find('ul',id='listContainerTopMenu')
			pattern = re.compile('\&genre=(.*?)\&')
			for li in categories:
				name = li.contents[0].strip()
				dirurl = 'http://www.glarab.com/ajax.aspx?channel=tv&genre=' + pattern.search(li['onclick']).groups()[0]
				addDir(name,dirurl,1)
		except:
			return
       
class FetchJob(workerpool.Job):
	def __init__(self, span, pattern, http):
		self.span = span
		self.pattern = pattern
		self.http = http

	def run(self):
		try:
			itemurl = 'http://www.glarab.com/' + self.pattern.search(self.span['onclick']).groups()[0]
		     	
			if __settings__.getSetting('show_thumbnail') == "true":
                                thumbnail = self.span.contents[0]['src']
                        name = self.span.contents[len(self.span) - 1].strip()

                        r = self.http.request('GET', itemurl)
                        link = r.data

                        splittedLink = link.split('|')
                        itemurl = 'http://%s:4500/channel.flv?user=%s&session=%s&server=%s&port=%s&channel=%s&mode=3' % (urllib.quote(__settings__.getSetting('proxy')), urllib.quote(splittedLink[0]), urllib.quote(splittedLink[1]), urllib.quote(splittedLink[2].split(':')[0]), urllib.quote(splittedLink[2].split(':')[1]), urllib.quote(splittedLink[3]))
                        addLink(itemurl,name,thumbnail)
			
		except:
			pass

def getChannels(url):
	if __settings__.getSetting('paid_account') == "true":
		while not login():
        	        xbmc.executebuiltin("XBMC.Notification('GLArab','INVALID username and/or password.',30000,"+icon+")")
	                __settings__.openSettings()
		url += '&type=reg'
	else:
		url += '&type=free'

	resp = opener.open(url)
	inner_data = resp.read();
	inner_soup = BeautifulSoup(inner_data)
	container = inner_soup.find('div',id='listContainerScroll')

	thumbnail = "DefaultVideo.png"
	pattern = re.compile("\makeHttpRequest\(\'(.*?)\&\',")

	NUM_SOCKETS = 5
	NUM_WORKERS = 8
	
	http = urllib3.PoolManager(maxsize=NUM_SOCKETS)
	workers = workerpool.WorkerPool(size=NUM_WORKERS)
	
	for span in container:
		workers.put(FetchJob(span, pattern, http))
	
	workers.shutdown()
	workers.wait()

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param


def addDir(name,url,mode):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage="DefaultFolder.png")
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

def addLink(url,name,iconimage):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
        return ok

            
params=get_params()
url=None
name=None
mode=None

try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

if mode==None:
        print ""
        getCategories()

elif mode==1:
        print ""+url
        getChannels(url)
        
xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = connectionpool
# urllib3/connectionpool.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import logging
import socket

from socket import error as SocketError, timeout as SocketTimeout

try:   # Python 3
    from http.client import HTTPConnection, HTTPException
    from http.client import HTTP_PORT, HTTPS_PORT
except ImportError:
    from httplib import HTTPConnection, HTTPException
    from httplib import HTTP_PORT, HTTPS_PORT

try:   # Python 3
    from queue import LifoQueue, Empty, Full
except ImportError:
    from Queue import LifoQueue, Empty, Full


try:   # Compiled with SSL?
    HTTPSConnection = object
    BaseSSLError = None
    ssl = None

    try:   # Python 3
        from http.client import HTTPSConnection
    except ImportError:
        from httplib import HTTPSConnection

    import ssl
    BaseSSLError = ssl.SSLError

except (ImportError, AttributeError):
    pass


from .request import RequestMethods
from .response import HTTPResponse
from .util import get_host, is_connection_dropped
from .exceptions import (
    EmptyPoolError,
    HostChangedError,
    MaxRetryError,
    SSLError,
    TimeoutError,
)

from .packages.ssl_match_hostname import match_hostname, CertificateError
from .packages import six


xrange = six.moves.xrange

log = logging.getLogger(__name__)

_Default = object()

port_by_scheme = {
    'http': HTTP_PORT,
    'https': HTTPS_PORT,
}


## Connection objects (extension of httplib)

class VerifiedHTTPSConnection(HTTPSConnection):
    """
    Based on httplib.HTTPSConnection but wraps the socket with
    SSL certification.
    """
    cert_reqs = None
    ca_certs = None

    def set_cert(self, key_file=None, cert_file=None,
                 cert_reqs='CERT_NONE', ca_certs=None):
        ssl_req_scheme = {
            'CERT_NONE': ssl.CERT_NONE,
            'CERT_OPTIONAL': ssl.CERT_OPTIONAL,
            'CERT_REQUIRED': ssl.CERT_REQUIRED
        }

        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = ssl_req_scheme.get(cert_reqs) or ssl.CERT_NONE
        self.ca_certs = ca_certs

    def connect(self):
        # Add certificate verification
        sock = socket.create_connection((self.host, self.port), self.timeout)

        # Wrap socket using verification with the root certs in
        # trusted_root_certs
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                    cert_reqs=self.cert_reqs,
                                    ca_certs=self.ca_certs)
        if self.ca_certs:
            match_hostname(self.sock.getpeercert(), self.host)


## Pool objects

class ConnectionPool(object):
    """
    Base class for all connection pools, such as
    :class:`.HTTPConnectionPool` and :class:`.HTTPSConnectionPool`.
    """

    scheme = None
    QueueCls = LifoQueue

    def __init__(self, host, port=None):
        self.host = host
        self.port = port

    def __str__(self):
        return '%s(host=%r, port=%r)' % (type(self).__name__,
                                         self.host, self.port)


class HTTPConnectionPool(ConnectionPool, RequestMethods):
    """
    Thread-safe connection pool for one host.

    :param host:
        Host used for this HTTP Connection (e.g. "localhost"), passed into
        :class:`httplib.HTTPConnection`.

    :param port:
        Port used for this HTTP Connection (None is equivalent to 80), passed
        into :class:`httplib.HTTPConnection`.

    :param strict:
        Causes BadStatusLine to be raised if the status line can't be parsed
        as a valid HTTP/1.0 or 1.1 status line, passed into
        :class:`httplib.HTTPConnection`.

    :param timeout:
        Socket timeout for each individual connection, can be a float. None
        disables timeout.

    :param maxsize:
        Number of connections to save that can be reused. More than 1 is useful
        in multithreaded situations. If ``block`` is set to false, more
        connections will be created but they will not be saved once they've
        been used.

    :param block:
        If set to True, no more than ``maxsize`` connections will be used at
        a time. When no free connections are available, the call will block
        until a connection has been released. This is a useful side effect for
        particular multithreaded situations where one does not want to use more
        than maxsize connections per host to prevent flooding.

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.
    """

    scheme = 'http'

    def __init__(self, host, port=None, strict=False, timeout=None, maxsize=1,
                 block=False, headers=None):
        super(HTTPConnectionPool, self).__init__(host, port)

        self.strict = strict
        self.timeout = timeout
        self.pool = self.QueueCls(maxsize)
        self.block = block
        self.headers = headers or {}

        # Fill the queue up so that doing get() on it will block properly
        for _ in xrange(maxsize):
            self.pool.put(None)

        # These are mostly for testing and debugging purposes.
        self.num_connections = 0
        self.num_requests = 0

    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPConnection`.
        """
        self.num_connections += 1
        log.info("Starting new HTTP connection (%d): %s" %
                 (self.num_connections, self.host))
        return HTTPConnection(host=self.host, port=self.port)

    def _get_conn(self, timeout=None):
        """
        Get a connection. Will return a pooled connection if one is available.

        If no connections are available and :prop:`.block` is ``False``, then a
        fresh connection is returned.

        :param timeout:
            Seconds to wait before giving up and raising
            :class:`urllib3.exceptions.EmptyPoolError` if the pool is empty and
            :prop:`.block` is ``True``.
        """
        conn = None
        try:
            conn = self.pool.get(block=self.block, timeout=timeout)

            # If this is a persistent connection, check if it got disconnected
            if conn and is_connection_dropped(conn):
                log.info("Resetting dropped connection: %s" % self.host)
                conn.close()

        except Empty:
            if self.block:
                raise EmptyPoolError(self,
                                     "Pool reached maximum size and no more "
                                     "connections are allowed.")
            pass  # Oh well, we'll create a new connection then

        return conn or self._new_conn()

    def _put_conn(self, conn):
        """
        Put a connection back into the pool.

        :param conn:
            Connection object for the current host and port as returned by
            :meth:`._new_conn` or :meth:`._get_conn`.

        If the pool is already full, the connection is discarded because we
        exceeded maxsize. If connections are discarded frequently, then maxsize
        should be increased.
        """
        try:
            self.pool.put(conn, block=False)
        except Full:
            # This should never happen if self.block == True
            log.warning("HttpConnectionPool is full, discarding connection: %s"
                        % self.host)

    def _make_request(self, conn, method, url, timeout=_Default,
                      **httplib_request_kw):
        """
        Perform a request on a given httplib connection object taken from our
        pool.
        """
        self.num_requests += 1

        if timeout is _Default:
            timeout = self.timeout

        conn.timeout = timeout # This only does anything in Py26+
        conn.request(method, url, **httplib_request_kw)

        # Set timeout
        sock = getattr(conn, 'sock', False) # AppEngine doesn't have sock attr.
        if sock:
            sock.settimeout(timeout)

        httplib_response = conn.getresponse()

        log.debug("\"%s %s %s\" %s %s" %
                  (method, url,
                   conn._http_vsn_str, # pylint: disable-msg=W0212
                   httplib_response.status, httplib_response.length))

        return httplib_response


    def is_same_host(self, url):
        """
        Check if the given ``url`` is a member of the same host as this
        connection pool.
        """
        # TODO: Add optional support for socket.gethostbyname checking.
        scheme, host, port = get_host(url)

        if self.port and not port:
            # Use explicit default port for comparison when none is given.
            port = port_by_scheme.get(scheme)

        return (url.startswith('/') or
                (scheme, host, port) == (self.scheme, self.host, self.port))

    def urlopen(self, method, url, body=None, headers=None, retries=3,
                redirect=True, assert_same_host=True, timeout=_Default,
                pool_timeout=None, release_conn=None, **response_kw):
        """
        Get a connection from the pool and perform an HTTP request. This is the
        lowest level call for making a request, so you'll need to specify all
        the raw details.

        .. note::

           More commonly, it's appropriate to use a convenience method provided
           by :class:`.RequestMethods`, such as :meth:`request`.

        .. note::

           `release_conn` will only behave as expected if
           `preload_content=False` because we want to make
           `preload_content=False` the default behaviour someday soon without
           breaking backwards compatibility.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param body:
            Data to send in the request body (useful for creating
            POST requests, see HTTPConnectionPool.post_url for
            more convenience).

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Number of retries to allow before raising a MaxRetryError exception.

        :param redirect:
            Automatically handle redirects (status codes 301, 302, 303, 307),
            each redirect counts as a retry.

        :param assert_same_host:
            If ``True``, will make sure that the host of the pool requests is
            consistent else will raise HostChangedError. When False, you can
            use the pool on an HTTP proxy and request foreign hosts.

        :param timeout:
            If specified, overrides the default timeout for this one request.

        :param pool_timeout:
            If set and the pool is set to block=True, then this method will
            block for ``pool_timeout`` seconds and raise EmptyPoolError if no
            connection is available within the time period.

        :param release_conn:
            If False, then the urlopen call will not release the connection
            back into the pool once a response is received (but will release if
            you read the entire contents of the response such as when
            `preload_content=True`). This is useful if you're not preloading
            the response's content immediately. You will need to call
            ``r.release_conn()`` on the response ``r`` to return the connection
            back into the pool. If None, it takes the value of
            ``response_kw.get('preload_content', True)``.

        :param \**response_kw:
            Additional parameters are passed to
            :meth:`urllib3.response.HTTPResponse.from_httplib`
        """
        if headers is None:
            headers = self.headers

        if retries < 0:
            raise MaxRetryError(self, url)

        if timeout is _Default:
            timeout = self.timeout

        if release_conn is None:
            release_conn = response_kw.get('preload_content', True)

        # Check host
        if assert_same_host and not self.is_same_host(url):
            host = "%s://%s" % (self.scheme, self.host)
            if self.port:
                host = "%s:%d" % (host, self.port)

            raise HostChangedError(self, url, retries - 1)

        conn = None

        try:
            # Request a connection from the queue
            # (Could raise SocketError: Bad file descriptor)
            conn = self._get_conn(timeout=pool_timeout)

            # Make the request on the httplib connection object
            httplib_response = self._make_request(conn, method, url,
                                                  timeout=timeout,
                                                  body=body, headers=headers)

            # If we're going to release the connection in ``finally:``, then
            # the request doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = not release_conn and conn

            # Import httplib's response into our own wrapper object
            response = HTTPResponse.from_httplib(httplib_response,
                                                 pool=self,
                                                 connection=response_conn,
                                                 **response_kw)

            # else:
            #     The connection will be put back into the pool when
            #     ``response.release_conn()`` is called (implicitly by
            #     ``response.read()``)

        except Empty as e:
            # Timed out by queue
            raise TimeoutError(self, "Request timed out. (pool_timeout=%s)" %
                               pool_timeout)

        except SocketTimeout as e:
            # Timed out by socket
            raise TimeoutError(self, "Request timed out. (timeout=%s)" %
                               timeout)

        except BaseSSLError as e:
            # SSL certificate error
            raise SSLError(e)

        except CertificateError as e:
            # Name mismatch
            raise SSLError(e)

        except (HTTPException, SocketError) as e:
            # Connection broken, discard. It will be replaced next _get_conn().
            conn = None
            # This is necessary so we can access e below
            err = e

        finally:
            if conn and release_conn:
                # Put the connection back to be reused
                self._put_conn(conn)

        if not conn:
            log.warn("Retrying (%d attempts remain) after connection "
                     "broken by '%r': %s" % (retries, err, url))
            return self.urlopen(method, url, body, headers, retries - 1,
                                redirect, assert_same_host)  # Try again

        # Handle redirect?
        redirect_location = redirect and response.get_redirect_location()
        if redirect_location:
            log.info("Redirecting %s -> %s" % (url, redirect_location))
            return self.urlopen(method, redirect_location, body, headers,
                                retries - 1, redirect, assert_same_host)

        return response


class HTTPSConnectionPool(HTTPConnectionPool):
    """
    Same as :class:`.HTTPConnectionPool`, but HTTPS.

    When Python is compiled with the :mod:`ssl` module, then
    :class:`.VerifiedHTTPSConnection` is used, which *can* verify certificates,
    instead of :class:httplib.HTTPSConnection`.

    The ``key_file``, ``cert_file``, ``cert_reqs``, and ``ca_certs`` parameters
    are only used if :mod:`ssl` is available and are fed into
    :meth:`ssl.wrap_socket` to upgrade the connection socket into an SSL socket.
    """

    scheme = 'https'

    def __init__(self, host, port=None,
                 strict=False, timeout=None, maxsize=1,
                 block=False, headers=None,
                 key_file=None, cert_file=None,
                 cert_reqs='CERT_NONE', ca_certs=None):

        super(HTTPSConnectionPool, self).__init__(host, port,
                                                  strict, timeout, maxsize,
                                                  block, headers)
        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = cert_reqs
        self.ca_certs = ca_certs

    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPSConnection`.
        """
        self.num_connections += 1
        log.info("Starting new HTTPS connection (%d): %s"
                 % (self.num_connections, self.host))

        if not ssl: # Platform-specific: Python compiled without +ssl
            if not HTTPSConnection or HTTPSConnection is object:
                raise SSLError("Can't connect to HTTPS URL because the SSL "
                               "module is not available.")

            return HTTPSConnection(host=self.host, port=self.port)

        connection = VerifiedHTTPSConnection(host=self.host, port=self.port)
        connection.set_cert(key_file=self.key_file, cert_file=self.cert_file,
                            cert_reqs=self.cert_reqs, ca_certs=self.ca_certs)
        return connection


def connection_from_url(url, **kw):
    """
    Given a url, return an :class:`.ConnectionPool` instance of its host.

    This is a shortcut for not having to parse out the scheme, host, and port
    of the url before creating an :class:`.ConnectionPool` instance.

    :param url:
        Absolute URL string that must include the scheme. Port is optional.

    :param \**kw:
        Passes additional parameters to the constructor of the appropriate
        :class:`.ConnectionPool`. Useful for specifying things like
        timeout, maxsize, headers, etc.

    Example: ::

        >>> conn = connection_from_url('http://google.com/')
        >>> r = conn.request('GET', '/')
    """
    scheme, host, port = get_host(url)
    if scheme == 'https':
        return HTTPSConnectionPool(host, port=port, **kw)
    else:
        return HTTPConnectionPool(host, port=port, **kw)

########NEW FILE########
__FILENAME__ = ntlmpool
# urllib3/contrib/ntlmpool.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
NTLM authenticating pool, contributed by erikcederstran

Issue #10, see: http://code.google.com/p/urllib3/issues/detail?id=10
"""

try:
    from http.client import HTTPSConnection
except ImportError:
    from httplib import HTTPSConnection
from logging import getLogger
from ntlm import ntlm

from urllib3 import HTTPSConnectionPool


log = getLogger(__name__)


class NTLMConnectionPool(HTTPSConnectionPool):
    """
    Implements an NTLM authentication version of an urllib3 connection pool
    """

    scheme = 'https'

    def __init__(self, user, pw, authurl, *args, **kwargs):
        """
        authurl is a random URL on the server that is protected by NTLM.
        user is the Windows user, probably in the DOMAIN\username format.
        pw is the password for the user.
        """
        super(NTLMConnectionPool, self).__init__(*args, **kwargs)
        self.authurl = authurl
        self.rawuser = user
        user_parts = user.split('\\', 1)
        self.domain = user_parts[0].upper()
        self.user = user_parts[1]
        self.pw = pw

    def _new_conn(self):
        # Performs the NTLM handshake that secures the connection. The socket
        # must be kept open while requests are performed.
        self.num_connections += 1
        log.debug('Starting NTLM HTTPS connection no. %d: https://%s%s' %
                  (self.num_connections, self.host, self.authurl))

        headers = {}
        headers['Connection'] = 'Keep-Alive'
        req_header = 'Authorization'
        resp_header = 'www-authenticate'

        conn = HTTPSConnection(host=self.host, port=self.port)

        # Send negotiation message
        headers[req_header] = (
            'NTLM %s' % ntlm.create_NTLM_NEGOTIATE_MESSAGE(self.rawuser))
        log.debug('Request headers: %s' % headers)
        conn.request('GET', self.authurl, None, headers)
        res = conn.getresponse()
        reshdr = dict(res.getheaders())
        log.debug('Response status: %s %s' % (res.status, res.reason))
        log.debug('Response headers: %s' % reshdr)
        log.debug('Response data: %s [...]' % res.read(100))

        # Remove the reference to the socket, so that it can not be closed by
        # the response object (we want to keep the socket open)
        res.fp = None

        # Server should respond with a challenge message
        auth_header_values = reshdr[resp_header].split(', ')
        auth_header_value = None
        for s in auth_header_values:
            if s[:5] == 'NTLM ':
                auth_header_value = s[5:]
        if auth_header_value is None:
            raise Exception('Unexpected %s response header: %s' %
                            (resp_header, reshdr[resp_header]))

        # Send authentication message
        ServerChallenge, NegotiateFlags = \
            ntlm.parse_NTLM_CHALLENGE_MESSAGE(auth_header_value)
        auth_msg = ntlm.create_NTLM_AUTHENTICATE_MESSAGE(ServerChallenge,
                                                         self.user,
                                                         self.domain,
                                                         self.pw,
                                                         NegotiateFlags)
        headers[req_header] = 'NTLM %s' % auth_msg
        log.debug('Request headers: %s' % headers)
        conn.request('GET', self.authurl, None, headers)
        res = conn.getresponse()
        log.debug('Response status: %s %s' % (res.status, res.reason))
        log.debug('Response headers: %s' % dict(res.getheaders()))
        log.debug('Response data: %s [...]' % res.read()[:100])
        if res.status != 200:
            if res.status == 401:
                raise Exception('Server rejected request: wrong '
                                'username or password')
            raise Exception('Wrong server response: %s %s' %
                            (res.status, res.reason))

        res.fp = None
        log.debug('Connection established')
        return conn

    def urlopen(self, method, url, body=None, headers=None, retries=3,
                redirect=True, assert_same_host=True):
        if headers is None:
            headers = {}
        headers['Connection'] = 'Keep-Alive'
        return super(NTLMConnectionPool, self).urlopen(method, url, body,
                                                       headers, retries,
                                                       redirect,
                                                       assert_same_host)

########NEW FILE########
__FILENAME__ = exceptions
# urllib3/exceptions.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


## Base Exceptions

class HTTPError(Exception):
    "Base exception used by this module."
    pass


class PoolError(HTTPError):
    "Base exception for errors caused within a pool."
    def __init__(self, pool, message):
        self.pool = pool
        HTTPError.__init__(self, "%s: %s" % (pool, message))


class SSLError(HTTPError):
    "Raised when SSL certificate fails in an HTTPS connection."
    pass


## Leaf Exceptions

class MaxRetryError(PoolError):
    "Raised when the maximum number of retries is exceeded."

    def __init__(self, pool, url):
        message = "Max retries exceeded with url: %s" % url
        PoolError.__init__(self, pool, message)

        self.url = url


class HostChangedError(PoolError):
    "Raised when an existing pool gets a request for a foreign host."

    def __init__(self, pool, url, retries=3):
        message = "Tried to open a foreign host with url: %s" % url
        PoolError.__init__(self, pool, message)

        self.url = url
        self.retries = retries


class TimeoutError(PoolError):
    "Raised when a socket timeout occurs."
    pass


class EmptyPoolError(PoolError):
    "Raised when a pool runs out of connections and no more are allowed."
    pass


class LocationParseError(ValueError, HTTPError):
    "Raised when get_host or similar fails to parse the URL input."

    def __init__(self, location):
        message = "Failed to parse: %s" % location
        super(LocationParseError, self).__init__(self, message)

        self.location = location

########NEW FILE########
__FILENAME__ = filepost
# urllib3/filepost.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import codecs
import mimetypes

try:
    from mimetools import choose_boundary
except ImportError:
    from .packages.mimetools_choose_boundary import choose_boundary

from io import BytesIO

from .packages import six
from .packages.six import b

writer = codecs.lookup('utf-8')[3]


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def iter_fields(fields):
    """
    Iterate over fields.

    Supports list of (k, v) tuples and dicts.
    """
    if isinstance(fields, dict):
        return ((k, v) for k, v in six.iteritems(fields))

    return ((k, v) for k, v in fields)


def encode_multipart_formdata(fields, boundary=None):
    """
    Encode a dictionary of ``fields`` using the multipart/form-data mime format.

    :param fields:
        Dictionary of fields or list of (key, value) field tuples.  The key is
        treated as the field name, and the value as the body of the form-data
        bytes. If the value is a tuple of two elements, then the first element
        is treated as the filename of the form-data section.

        Field names and filenames must be unicode.

    :param boundary:
        If not specified, then a random boundary will be generated using
        :func:`mimetools.choose_boundary`.
    """
    body = BytesIO()
    if boundary is None:
        boundary = choose_boundary()

    for fieldname, value in iter_fields(fields):
        body.write(b('--%s\r\n' % (boundary)))

        if isinstance(value, tuple):
            filename, data = value
            writer(body).write('Content-Disposition: form-data; name="%s"; '
                               'filename="%s"\r\n' % (fieldname, filename))
            body.write(b('Content-Type: %s\r\n\r\n' %
                       (get_content_type(filename))))
        else:
            data = value
            writer(body).write('Content-Disposition: form-data; name="%s"\r\n'
                               % (fieldname))
            body.write(b'Content-Type: text/plain\r\n\r\n')

        if isinstance(data, int):
            data = str(data)  # Backwards compatibility

        if isinstance(data, six.text_type):
            writer(body).write(data)
        else:
            body.write(data)

        body.write(b'\r\n')

    body.write(b('--%s--\r\n' % (boundary)))

    content_type = b('multipart/form-data; boundary=%s' % boundary)

    return body.getvalue(), content_type

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

#Copyright (c) 2010-2011 Benjamin Peterson

#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in
#the Software without restriction, including without limitation the rights to
#use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
#the Software, and to permit persons to whom the Software is furnished to do so,
#subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
#FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
#IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
#CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.1.0"


# True if we are running on Python 3.
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
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
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
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules["six.moves"] = _MovedItems("moves")


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

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


if PY3:
    def get_unbound_function(unbound):
        return unbound


    advance_iterator = next

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)
else:
    def get_unbound_function(unbound):
        return unbound.im_func


    def advance_iterator(it):
        return it.next()

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return getattr(d, _itervalues)()

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return getattr(d, _iteritems)()


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
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
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


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


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = poolmanager
# urllib3/poolmanager.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import logging

from ._collections import RecentlyUsedContainer
from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from .connectionpool import get_host, connection_from_url, port_by_scheme
from .exceptions import HostChangedError
from .request import RequestMethods


__all__ = ['PoolManager', 'ProxyManager', 'proxy_from_url']


pool_classes_by_scheme = {
    'http': HTTPConnectionPool,
    'https': HTTPSConnectionPool,
}

log = logging.getLogger(__name__)


class PoolManager(RequestMethods):
    """
    Allows for arbitrary requests while transparently keeping track of
    necessary connection pools for you.

    :param num_pools:
        Number of connection pools to cache before discarding the least recently
        used pool.

    :param \**connection_pool_kw:
        Additional parameters are used to create fresh
        :class:`urllib3.connectionpool.ConnectionPool` instances.

    Example: ::

        >>> manager = PoolManager(num_pools=2)
        >>> r = manager.urlopen("http://google.com/")
        >>> r = manager.urlopen("http://google.com/mail")
        >>> r = manager.urlopen("http://yahoo.com/")
        >>> len(manager.pools)
        2

    """

    # TODO: Make sure there are no memory leaks here.

    def __init__(self, num_pools=10, **connection_pool_kw):
        self.connection_pool_kw = connection_pool_kw
        self.pools = RecentlyUsedContainer(num_pools)

    def connection_from_host(self, host, port=80, scheme='http'):
        """
        Get a :class:`ConnectionPool` based on the host, port, and scheme.

        Note that an appropriate ``port`` value is required here to normalize
        connection pools in our container most effectively.
        """
        pool_key = (scheme, host, port)

        # If the scheme, host, or port doesn't match existing open connections,
        # open a new ConnectionPool.
        pool = self.pools.get(pool_key)
        if pool:
            return pool

        # Make a fresh ConnectionPool of the desired type
        pool_cls = pool_classes_by_scheme[scheme]
        pool = pool_cls(host, port, **self.connection_pool_kw)

        self.pools[pool_key] = pool

        return pool

    def connection_from_url(self, url):
        """
        Similar to :func:`urllib3.connectionpool.connection_from_url` but
        doesn't pass any additional parameters to the
        :class:`urllib3.connectionpool.ConnectionPool` constructor.

        Additional parameters are taken from the :class:`.PoolManager`
        constructor.
        """
        scheme, host, port = get_host(url)

        port = port or port_by_scheme.get(scheme, 80)

        return self.connection_from_host(host, port=port, scheme=scheme)

    def urlopen(self, method, url, **kw):
        """
        Same as :meth:`urllib3.connectionpool.HTTPConnectionPool.urlopen`.

        ``url`` must be absolute, such that an appropriate
        :class:`urllib3.connectionpool.ConnectionPool` can be chosen for it.
        """
        conn = self.connection_from_url(url)
        try:
            return conn.urlopen(method, url, **kw)

        except HostChangedError as e:
            kw['retries'] = e.retries # Persist retries countdown
            return self.urlopen(method, e.url, **kw)


class ProxyManager(RequestMethods):
    """
    Given a ConnectionPool to a proxy, the ProxyManager's ``urlopen`` method
    will make requests to any url through the defined proxy.
    """

    def __init__(self, proxy_pool):
        self.proxy_pool = proxy_pool

    def _set_proxy_headers(self, headers=None):
        headers = headers or {}

        # Same headers are curl passes for --proxy1.0
        headers['Accept'] = '*/*'
        headers['Proxy-Connection'] = 'Keep-Alive'

        return headers

    def urlopen(self, method, url, **kw):
        "Same as HTTP(S)ConnectionPool.urlopen, ``url`` must be absolute."
        kw['assert_same_host'] = False
        kw['headers'] = self._set_proxy_headers(kw.get('headers'))
        return self.proxy_pool.urlopen(method, url, **kw)


def proxy_from_url(url, **pool_kw):
    proxy_pool = connection_from_url(url, **pool_kw)
    return ProxyManager(proxy_pool)

########NEW FILE########
__FILENAME__ = request
# urllib3/request.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from .filepost import encode_multipart_formdata


__all__ = ['RequestMethods']


class RequestMethods(object):
    """
    Convenience mixin for classes who implement a :meth:`urlopen` method, such
    as :class:`~urllib3.connectionpool.HTTPConnectionPool` and
    :class:`~urllib3.poolmanager.PoolManager`.

    Provides behavior for making common types of HTTP request methods and
    decides which type of request field encoding to use.

    Specifically,

    :meth:`.request_encode_url` is for sending requests whose fields are encoded
    in the URL (such as GET, HEAD, DELETE).

    :meth:`.request_encode_body` is for sending requests whose fields are
    encoded in the *body* of the request using multipart or www-orm-urlencoded
    (such as for POST, PUT, PATCH).

    :meth:`.request` is for making any kind of request, it will look up the
    appropriate encoding format and use one of the above two methods to make
    the request.
    """

    _encode_url_methods = set(['DELETE', 'GET', 'HEAD', 'OPTIONS'])

    _encode_body_methods = set(['PATCH', 'POST', 'PUT', 'TRACE'])

    def urlopen(self, method, url, body=None, headers=None,
                encode_multipart=True, multipart_boundary=None,
                **kw): # Abstract
        raise NotImplemented("Classes extending RequestMethods must implement "
                             "their own ``urlopen`` method.")

    def request(self, method, url, fields=None, headers=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the appropriate encoding of
        ``fields`` based on the ``method`` used.

        This is a convenience method that requires the least amount of manual
        effort. It can be used in most situations, while still having the option
        to drop down to more specific methods when necessary, such as
        :meth:`request_encode_url`, :meth:`request_encode_body`,
        or even the lowest level :meth:`urlopen`.
        """
        method = method.upper()

        if method in self._encode_url_methods:
            return self.request_encode_url(method, url, fields=fields,
                                            headers=headers,
                                            **urlopen_kw)
        else:
            return self.request_encode_body(method, url, fields=fields,
                                             headers=headers,
                                             **urlopen_kw)

    def request_encode_url(self, method, url, fields=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the url. This is useful for request methods like GET, HEAD, DELETE, etc.
        """
        if fields:
            url += '?' + urlencode(fields)
        return self.urlopen(method, url, **urlopen_kw)

    def request_encode_body(self, method, url, fields=None, headers=None,
                            encode_multipart=True, multipart_boundary=None,
                            **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the body. This is useful for request methods like POST, PUT, PATCH, etc.

        When ``encode_multipart=True`` (default), then
        :meth:`urllib3.filepost.encode_multipart_formdata` is used to encode the
        payload with the appropriate content type. Otherwise
        :meth:`urllib.urlencode` is used with the
        'application/x-www-form-urlencoded' content type.

        Multipart encoding must be used when posting files, and it's reasonably
        safe to use it in other times too. However, it may break request signing,
        such as with OAuth.

        Supports an optional ``fields`` parameter of key/value strings AND
        key/filetuple. A filetuple is a (filename, data) tuple. For example: ::

            fields = {
                'foo': 'bar',
                'fakefile': ('foofile.txt', 'contents of foofile'),
                'realfile': ('barfile.txt', open('realfile').read()),
                'nonamefile': ('contents of nonamefile field'),
            }

        When uploading a file, providing a filename (the first parameter of the
        tuple) is optional but recommended to best mimick behavior of browsers.

        Note that if ``headers`` are supplied, the 'Content-Type' header will be
        overwritten because it depends on the dynamic random boundary string
        which is used to compose the body of the request. The random boundary
        string can be explicitly set with the ``multipart_boundary`` parameter.
        """
        if encode_multipart:
            body, content_type = encode_multipart_formdata(fields or {},
                                    boundary=multipart_boundary)
        else:
            body, content_type = (urlencode(fields or {}),
                                    'application/x-www-form-urlencoded')

        headers = headers or {}
        headers.update({'Content-Type': content_type})

        return self.urlopen(method, url, body=body, headers=headers,
                            **urlopen_kw)

########NEW FILE########
__FILENAME__ = response
# urllib3/response.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import gzip
import logging
import zlib

from io import BytesIO

from .exceptions import HTTPError
from .packages.six import string_types as basestring


log = logging.getLogger(__name__)


def decode_gzip(data):
    gzipper = gzip.GzipFile(fileobj=BytesIO(data))
    return gzipper.read()


def decode_deflate(data):
    try:
        return zlib.decompress(data)
    except zlib.error:
        return zlib.decompress(data, -zlib.MAX_WBITS)


class HTTPResponse(object):
    """
    HTTP Response container.

    Backwards-compatible to httplib's HTTPResponse but the response ``body`` is
    loaded and decoded on-demand when the ``data`` property is accessed.

    Extra parameters for behaviour not present in httplib.HTTPResponse:

    :param preload_content:
        If True, the response's body will be preloaded during construction.

    :param decode_content:
        If True, attempts to decode specific content-encoding's based on headers
        (like 'gzip' and 'deflate') will be skipped and raw data will be used
        instead.

    :param original_response:
        When this HTTPResponse wrapper is generated from an httplib.HTTPResponse
        object, it's convenient to include the original for debug purposes. It's
        otherwise unused.
    """

    CONTENT_DECODERS = {
        'gzip': decode_gzip,
        'deflate': decode_deflate,
    }

    def __init__(self, body='', headers=None, status=0, version=0, reason=None,
                 strict=0, preload_content=True, decode_content=True,
                 original_response=None, pool=None, connection=None):
        self.headers = headers or {}
        self.status = status
        self.version = version
        self.reason = reason
        self.strict = strict

        self._decode_content = decode_content
        self._body = body if body and isinstance(body, basestring) else None
        self._fp = None
        self._original_response = original_response

        self._pool = pool
        self._connection = connection

        if hasattr(body, 'read'):
            self._fp = body

        if preload_content and not self._body:
            self._body = self.read(decode_content=decode_content)

    def get_redirect_location(self):
        """
        Should we redirect and where to?

        :returns: Truthy redirect location string if we got a redirect status
            code and valid location. ``None`` if redirect status and no
            location. ``False`` if not a redirect status code.
        """
        if self.status in [301, 302, 303, 307]:
            return self.headers.get('location')

        return False

    def release_conn(self):
        if not self._pool or not self._connection:
            return

        self._pool._put_conn(self._connection)
        self._connection = None

    @property
    def data(self):
        # For backwords-compat with earlier urllib3 0.4 and earlier.
        if self._body:
            return self._body

        if self._fp:
            return self.read(cache_content=True)

    def read(self, amt=None, decode_content=None, cache_content=False):
        """
        Similar to :meth:`httplib.HTTPResponse.read`, but with two additional
        parameters: ``decode_content`` and ``cache_content``.

        :param amt:
            How much of the content to read. If specified, decoding and caching
            is skipped because we can't decode partial content nor does it make
            sense to cache partial content as the full response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header. (Overridden if ``amt`` is set.)

        :param cache_content:
            If True, will save the returned data such that the same result is
            returned despite of the state of the underlying file object. This
            is useful if you want the ``.data`` property to continue working
            after having ``.read()`` the file object. (Overridden if ``amt`` is
            set.)
        """
        content_encoding = self.headers.get('content-encoding')
        decoder = self.CONTENT_DECODERS.get(content_encoding)
        if decode_content is None:
            decode_content = self._decode_content

        if self._fp is None:
            return

        try:
            if amt is None:
                # cStringIO doesn't like amt=None
                data = self._fp.read()
            else:
                return self._fp.read(amt)

            try:
                if decode_content and decoder:
                    data = decoder(data)
            except IOError:
                raise HTTPError("Received response with content-encoding: %s, but "
                                "failed to decode it." % content_encoding)

            if cache_content:
                self._body = data

            return data

        finally:
            if self._original_response and self._original_response.isclosed():
                self.release_conn()

    @classmethod
    def from_httplib(ResponseCls, r, **response_kw):
        """
        Given an :class:`httplib.HTTPResponse` instance ``r``, return a
        corresponding :class:`urllib3.response.HTTPResponse` object.

        Remaining parameters are passed to the HTTPResponse constructor, along
        with ``original_response=r``.
        """

        # Normalize headers between different versions of Python
        headers = {}
        for k, v in r.getheaders():
            # Python 3: Header keys are returned capitalised
            k = k.lower()

            has_value = headers.get(k)
            if has_value: # Python 3: Repeating header keys are unmerged.
                v = ', '.join([has_value, v])

            headers[k] = v

        # HTTPResponse objects in Python 3 don't have a .strict attribute
        strict = getattr(r, 'strict', 0)
        return ResponseCls(body=r,
                           headers=headers,
                           status=r.status,
                           version=r.version,
                           reason=r.reason,
                           strict=strict,
                           original_response=r,
                           **response_kw)

    # Backwards-compatibility methods for httplib.HTTPResponse
    def getheaders(self):
        return self.headers

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

########NEW FILE########
__FILENAME__ = util
# urllib3/util.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


from base64 import b64encode

try:
    from select import poll, POLLIN
except ImportError: # `poll` doesn't exist on OSX and other platforms
    poll = False
    try:
        from select import select
    except ImportError: # `select` doesn't exist on AppEngine.
        select = False

from .packages import six
from .exceptions import LocationParseError


def make_headers(keep_alive=None, accept_encoding=None, user_agent=None,
                 basic_auth=None):
    """
    Shortcuts for generating request headers.

    :param keep_alive:
        If ``True``, adds 'connection: keep-alive' header.

    :param accept_encoding:
        Can be a boolean, list, or string.
        ``True`` translates to 'gzip,deflate'.
        List will get joined by comma.
        String will be used as provided.

    :param user_agent:
        String representing the user-agent you want, such as
        "python-urllib3/0.6"

    :param basic_auth:
        Colon-separated username:password string for 'authorization: basic ...'
        auth header.

    Example: ::

        >>> make_headers(keep_alive=True, user_agent="Batman/1.0")
        {'connection': 'keep-alive', 'user-agent': 'Batman/1.0'}
        >>> make_headers(accept_encoding=True)
        {'accept-encoding': 'gzip,deflate'}
    """
    headers = {}
    if accept_encoding:
        if isinstance(accept_encoding, str):
            pass
        elif isinstance(accept_encoding, list):
            accept_encoding = ','.join(accept_encoding)
        else:
            accept_encoding = 'gzip,deflate'
        headers['accept-encoding'] = accept_encoding

    if user_agent:
        headers['user-agent'] = user_agent

    if keep_alive:
        headers['connection'] = 'keep-alive'

    if basic_auth:
        headers['authorization'] = 'Basic ' + \
            b64encode(six.b(basic_auth)).decode('utf-8')

    return headers


def get_host(url):
    """
    Given a url, return its scheme, host and port (None if it's not there).

    For example: ::

        >>> get_host('http://google.com/mail/')
        ('http', 'google.com', None)
        >>> get_host('google.com:80')
        ('http', 'google.com', 80)
    """

    # This code is actually similar to urlparse.urlsplit, but much
    # simplified for our needs.
    port = None
    scheme = 'http'

    if '://' in url:
        scheme, url = url.split('://', 1)
    if '/' in url:
        url, _path = url.split('/', 1)
    if '@' in url:
        _auth, url = url.split('@', 1)
    if ':' in url:
        url, port = url.split(':', 1)

        if not port.isdigit():
            raise LocationParseError("Failed to parse: %s" % url)

        port = int(port)

    return scheme, url, port



def is_connection_dropped(conn):
    """
    Returns True if the connection is dropped and should be closed.

    :param conn:
        ``HTTPConnection`` object.

    Note: For platforms like AppEngine, this will always return ``False`` to
    let the platform handle connection recycling transparently for us.
    """
    sock = getattr(conn, 'sock', False)
    if not sock: #Platform-specific: AppEngine
        return False

    if not poll: # Platform-specific
        if not select: #Platform-specific: AppEngine
            return False

        return select([sock], [], [], 0.0)[0]

    # This version is better on platforms that support it.
    p = poll()
    p.register(sock, POLLIN)
    for (fno, ev) in p.poll(0.0):
        if fno == sock.fileno():
            # Either data is buffered (bad), or the connection is dropped.
            return True

########NEW FILE########
__FILENAME__ = _collections
# urllib3/_collections.py
# Copyright 2008-2012 Andrey Petrov and contributors (see CONTRIBUTORS.txt)
#
# This module is part of urllib3 and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from collections import deque

from threading import RLock

__all__ = ['RecentlyUsedContainer']


class AccessEntry(object):
    __slots__ = ('key', 'is_valid')

    def __init__(self, key, is_valid=True):
        self.key = key
        self.is_valid = is_valid


class RecentlyUsedContainer(dict):
    """
    Provides a dict-like that maintains up to ``maxsize`` keys while throwing
    away the least-recently-used keys beyond ``maxsize``.
    """

    # If len(self.access_log) exceeds self._maxsize * CLEANUP_FACTOR, then we
    # will attempt to cleanup the invalidated entries in the access_log
    # datastructure during the next 'get' operation.
    CLEANUP_FACTOR = 10

    def __init__(self, maxsize=10):
        self._maxsize = maxsize

        self._container = {}

        # We use a deque to to store our keys ordered by the last access.
        self.access_log = deque()
        self.access_log_lock = RLock()

        # We look up the access log entry by the key to invalidate it so we can
        # insert a new authorative entry at the head without having to dig and
        # find the old entry for removal immediately.
        self.access_lookup = {}

        # Trigger a heap cleanup when we get past this size
        self.access_log_limit = maxsize * self.CLEANUP_FACTOR

    def _invalidate_entry(self, key):
        "If exists: Invalidate old entry and return it."
        old_entry = self.access_lookup.get(key)
        if old_entry:
            old_entry.is_valid = False

        return old_entry

    def _push_entry(self, key):
        "Push entry onto our access log, invalidate the old entry if exists."
        self._invalidate_entry(key)

        new_entry = AccessEntry(key)
        self.access_lookup[key] = new_entry

        self.access_log_lock.acquire()
        self.access_log.appendleft(new_entry)
        self.access_log_lock.release()

    def _prune_entries(self, num):
        "Pop entries from our access log until we popped ``num`` valid ones."
        while num > 0:
            self.access_log_lock.acquire()
            p = self.access_log.pop()
            self.access_log_lock.release()

            if not p.is_valid:
                continue # Invalidated entry, skip

            dict.pop(self, p.key, None)
            self.access_lookup.pop(p.key, None)
            num -= 1

    def _prune_invalidated_entries(self):
        "Rebuild our access_log without the invalidated entries."
        self.access_log_lock.acquire()
        self.access_log = deque(e for e in self.access_log if e.is_valid)
        self.access_log_lock.release()

    def _get_ordered_access_keys(self):
        "Return ordered access keys for inspection. Used for testing."
        self.access_log_lock.acquire()
        r = [e.key for e in self.access_log if e.is_valid]
        self.access_log_lock.release()

        return r

    def __getitem__(self, key):
        item = dict.get(self, key)

        if not item:
            raise KeyError(key)

        # Insert new entry with new high priority, also implicitly invalidates
        # the old entry.
        self._push_entry(key)

        if len(self.access_log) > self.access_log_limit:
            # Heap is getting too big, try to clean up any tailing invalidated
            # entries.
            self._prune_invalidated_entries()

        return item

    def __setitem__(self, key, item):
        # Add item to our container and access log
        dict.__setitem__(self, key, item)
        self._push_entry(key)

        # Discard invalid and excess entries
        self._prune_entries(len(self) - self._maxsize)

    def __delitem__(self, key):
        self._invalidate_entry(key)
        self.access_lookup.pop(key, None)
        dict.__delitem__(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

########NEW FILE########
__FILENAME__ = exceptions
# exceptions.py - Exceptions used in the operation of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

class TerminationNotice(Exception):
    "This exception is raised inside a thread when it's time for it to die."
    pass

########NEW FILE########
__FILENAME__ = jobs
# jobs.py - Generic jobs used with the worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from exceptions import TerminationNotice

__all__ = ['Job', 'SuicideJob', 'SimpleJob']

class Job(object):
    "Interface for a Job object."
    def __init__(self):
        pass

    def run(self):
        "The actual task for the job should be implemented here."
        pass

class SuicideJob(Job):
    "A worker receiving this job will commit suicide."
    def run(self, **kw):
        raise TerminationNotice()

class SimpleJob(Job):
    """
    Given a `result` queue, a `method` pointer, and an `args` dictionary or
    list, the method will execute r = method(*args) or r = method(**args), 
    depending on args' type, and perform result.put(r).
    """
    def __init__(self, result, method, args=[]):
        self.result = result
        self.method = method
        self.args = args

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            r = self.method(*self.args)
        elif isinstance(self.args, dict):
            r = self.method(**self.args)
        self._return(r)

    def _return(self, r):
        "Handle return value by appending to the ``self.result`` queue."
        self.result.put(r)

########NEW FILE########
__FILENAME__ = pools
# workerpool.py - Module for distributing jobs to a pool of worker threads.
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php


from Queue import Queue
if not hasattr(Queue, 'task_done'):
    # Graft Python 2.5's Queue functionality onto Python 2.4's implementation
    # TODO: The extra methods do nothing for now. Make them do something.
    from QueueWrapper import Queue

from workers import Worker
from jobs import SimpleJob, SuicideJob


__all__ = ['WorkerPool', 'default_worker_factory']


def default_worker_factory(job_queue):
    return Worker(job_queue)


class WorkerPool(Queue):
    """
    WorkerPool servers two functions: It is a Queue and a master of Worker
    threads. The Queue accepts Job objects and passes it on to Workers, who are
    initialized during the construction of the pool and by using grow().

    Jobs are inserted into the WorkerPool with the `put` method.
    Hint: Have the Job append its result into a shared queue that the caller
    holds and then the caller reads an expected number of results from it.

    The shutdown() method must be explicitly called to terminate the Worker
    threads when the pool is no longer needed.

    Construction parameters:

    size = 1
        Number of active worker threads the pool should contain.

    maxjobs = 0
        Maximum number of jobs to allow in the queue at a time. Will block on
        `put` if full.

    default_worker = default_worker_factory
        The default worker factory is called with one argument, which is the
        jobs Queue object that it will read from to acquire jobs. The factory
        will produce a Worker object which will be added to the pool.
    """
    def __init__(self, size=1, maxjobs=0, worker_factory=default_worker_factory):
        if not callable(worker_factory):
            raise TypeError("worker_factory must be callable")

        self.worker_factory = worker_factory # Used to build new workers
        self._size = 0 # Number of active workers we have

        # Initialize the Queue
        Queue.__init__(self, maxjobs) # The queue contains job that are read by workers
        self._jobs = self # Pointer to the queue, for backwards compatibility with version 0.9.1 and earlier

        # Hire some workers!
        for i in xrange(size):
            self.grow()

    def grow(self):
        "Add another worker to the pool."
        t = self.worker_factory(self)
        t.start()
        self._size += 1

    def shrink(self):
        "Get rid of one worker from the pool. Raises IndexError if empty."
        if self._size <= 0:
            raise IndexError("pool is already empty")
        self._size -= 1
        self.put(SuicideJob())

    def shutdown(self):
        "Retire the workers."
        for i in xrange(self.size()):
            self.put(SuicideJob())

    def size(self):
        "Approximate number of active workers (could be more if a shrinking is in progress)."
        return self._size

    def map(self, fn, *seq):
        "Perform a map operation distributed among the workers. Will block until done."
        results = Queue()
        args = zip(*seq)
        for seq in args:
            j = SimpleJob(results, fn, seq)
            self.put(j)

        # Aggregate results
        r = []
        for i in xrange(len(args)):
            r.append(results.get())

        return r

    def wait(self):
        "DEPRECATED: Use join() instead."
        self.join()

########NEW FILE########
__FILENAME__ = QueueWrapper
# NewQueue.py - Implements Python 2.5 Queue functionality for Python 2.4
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

# TODO: The extra methods provided here do nothing for now. Add real functionality to them someday.

from Queue import Queue as OldQueue

__all__ = ['Queue']

class Queue(OldQueue):
    def task_done(self):
        "Does nothing in Python 2.4"
        pass

    def join(self):
        "Does nothing in Python 2.4"
        pass

########NEW FILE########
__FILENAME__ = workers
# workers.py - Worker objects who become members of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from threading import Thread
from jobs import Job, SimpleJob
from exceptions import TerminationNotice

__all__ = ['Worker', 'EquippedWorker']

class Worker(Thread):
    """
    A loyal worker who will pull jobs from the `jobs` queue and perform them.

    The run method will get jobs from the `jobs` queue passed into the
    constructor, and execute them. After each job, task_done() must be executed
    on the `jobs` queue in order for the pool to know when no more jobs are
    being processed.
    """

    def __init__(self, jobs):
        self.jobs = jobs
        Thread.__init__(self)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            # Sleep until there is a job to perform.
            job = self.jobs.get()

            # Yawn. Time to get some work done.
            try:
                job.run()
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break 

class EquippedWorker(Worker):
    """
    Each worker will create an instance of ``toolbox`` and hang on to it during
    its lifetime. This can be used to pass in a resource such as a persistent 
    connections to services that the worker will be using.

    The toolbox factory is called without arguments to produce an instance of
    an object which contains resources necessary for this Worker to perform.
    """
    # TODO: Should a variation of this become the default Worker someday?

    def __init__(self, jobs, toolbox_factory):
        self.toolbox = toolbox_factory()
        Worker.__init__(self, jobs)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            job = self.jobs.get()
            try:
                job.run(toolbox=self.toolbox)
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/islamickhotba
# Version 1.0.1
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "rajarojola"

# Entry point
def run():
    plugintools.log("rajarojola.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("rajarojola.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/mtvlebanon
# Version 1.0.2
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "mtvlebanon"

# Entry point
def run():
    plugintools.log("mtvlebanon.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("3alshasha.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib
import time

__settings__ = xbmcaddon.Addon(id='plugin.video.panet')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'http://pschools.haifanet.org.il/abd.relchaj/2010/panet.jpg'))
	addDir('مسلسلات رمضان 2013','http://www.panet.co.il/Ext/series.php?name=category&id=32&country=NL&page=',29,'',0,0)
	addDir('مسلسلات سورية ولبنانية','http://www.panet.co.il/Ext/series.php?name=category&id=18&country=NL&page=',29,'',0,0)
	addDir('مسلسلات مصرية','http://www.panet.co.il/Ext/series.php?name=category&id=19&country=NL&page=',29,'',0,0)
	addDir('مسلسلات خليجية','http://www.panet.co.il/Ext/series.php?name=category&id=21&country=NL&page=',29,'',0,0)
	addDir('افلام عربية ','http://www.panet.co.il/online/video/movies/P-0.html/',1,'',0,30)
	addDir('افلام متحركة  ','http://www.panet.co.il/Ext/series.php?name=folder&id=257',29,'',0,0)
	addDir('مسلسلات تركية','http://www.panet.co.il/Ext/series.php?name=category&id=17&country=TR&page=',29,'',0,0)
	addDir('مسلسلات مكسيكية و عالمية','http://www.panet.co.il/Ext/series.php?name=category&id=20&country=NL&page=',29,'',0,0)
	addDir('رسوم متحركة , برامج اطفال','http://www.panet.co.il/Ext/series.php?name=category&id=15&country=NL&page=',29,'',0,0)
	addDir('برامج ومنوعات','http://www.panet.co.il/Ext/series.php?name=category&id=27&country=NL&page=',29,'',0,0)
	
		

	
def checkURL(url):
    p = urlparse(url)
    h = HTTP(p[1])
    h.putrequest('HEAD', p[2])
    h.endheaders()
    if h.getreply()[0] == 200: return 1
    else: return 0
	
def PanetListSeries(url):
    siteMax=15
    Serie=0
    mynamearray=[]
    myimagesarray=[]
    myurlarray=[]
    
    
    while Serie!=siteMax:
		
		kurl=str(url)+str(Serie)
		req = urllib2.Request(kurl)
		req.add_header('Host', 'www.panet.co.il')
		req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36')
		req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
		req.add_header('Accept-Language', 'sv-SE,sv;q=0.8,en-US;q=0.6,en;q=0.4')
		response = urllib2.urlopen(req)
		link=response.read()
		Serie=Serie+1
		buf = StringIO.StringIO(link)
		buf2 = StringIO.StringIO(link)
        
		for names in link.split():
			line=buf.readline()
			if ('><font face="Tahoma" size="2" color="Black"><b>') in line:
				name=str((str(line).split('"Black"><b>'))[1]).replace('</b><br/>', '').strip()
				mynamearray.append(name)
		for imagesandurls in link.split():
			line=buf2.readline()
			if '<a href="/Ext/series.php?name=folder&id=' and '"><img border="0" src="' and '" width="150" height="83"></a><br>' in line:
				both=str( line).split('"><img border="0" src="')
				myurl=str(both[0]).replace('<a href="', '').strip()
				myurl='http://www.panet.co.il'+myurl
				myurl=str(myurl).split('&country=')
				myurl=str(myurl[0]).strip()
				myurlarray.append(myurl)
				myimage=str(both[1]).replace('" width="150" height="83"></a><br>', '').strip()
				myimagesarray.append(myimage)
    for i in range(0,400):
        try:
            
            addDir(mynamearray[i],myurlarray[i],30,myimagesarray[i],0,0)
        except:
            pass
         
def getPanetEpos(url): 
    
    for i in range(0,5):   
        req = urllib2.Request(url+"&autostart=105194&page="+str(i))
        response = urllib2.urlopen(req)
        link=response.read()
        target= re.findall(r'<div class="series-table-item">(.*?)\s(.*?)</font>', link, re.DOTALL)
        counter =0
        for items in target:
            counter = counter +1
        for itr in  target:
			path = str( itr).split('"><img')[0]
			path = str(path).split('href="')[1]
			path = str(path).replace('&autostart=105194&page=0', '')
			path=str(path).strip()
			path =str(path).split('autostart=')[1]
			path =str(path).split('&page=0')[0]
			img = str( itr).split('" width="')[0]
			img = str( img).split('src="')[1]
			img =str(img).strip()
			name = "الحلقة" +" "+ str(counter)
			counter = counter -1
			addLink(name,path,31,img)

	
def GET_VIDEO_FILE(name, url):
	url="http://www.panet.co.il/Ext/vplayer_lib.php?media="+str(url)+'&start=false'
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	req.add_header('Accept',' text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Accept-Language',' en-US,en;q=0.5')
	req.add_header('Accept-Encoding', 'deflate')
	req.add_header('Referer',' http://www.panet.co.il/Ext/players/flv5/player.swf')
	req.add_header('Cookie',' __auc=82d7ffe213cb1b4ce1d273c7ba1; __utma=31848767.848342890.1360191082.1360611183.1360620657.4; __utmz=31848767.1360191082.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmb=31848767.4.10.1360620660; __utmc=31848767; __asc=169c084d13ccb4fa36df421055e')
	req.add_header('Connection',' keep-alive')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	match_url_thumb=(re.compile('<link rel="video_src" href="(.+?)"/>').findall(link))
	match_url_thumb=str(match_url_thumb).replace("['", "")
	match_url_thumb=str(match_url_thumb).replace("']", "").strip()
	match_url_thumb=match_url_thumb.replace('%3A',':')
	match_url_thumb=match_url_thumb.replace('%2F','/')
	match_url_thumb=match_url_thumb.replace('http://','')
	match_url_thumb=match_url_thumb.replace('file=','file=http://')
	match_url_thumb=match_url_thumb.replace("www.panet.co.il/Ext/players/flv/playern.swf?type=http&streamer=start&file=","")
	match_url_thumb=match_url_thumb+'|Referer=http://www.panet.co.il/Ext/players/flv5/player.swf'
	listItem = xbmcgui.ListItem(path=str(match_url_thumb))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	


def retrievePanetMovies(MINIMUM,MAXIMUM):
	try:

		for iterator in range(MINIMUM,MAXIMUM+1):
			url=str('http://www.panet.co.il/online/video/movies/P-'+str(iterator)+'.html')
			req = urllib2.Request(url)
			response = urllib2.urlopen(req)
			link=response.read()
			mytarget = (re.compile('<div style="float:right; margin-left:4px;"><a href="(.+?)" border=').findall(link))
			for items in  mytarget:
				filmPath = str(items).split('"><img src=')[0]
				filmPath ="http://pms.panet.co.il"+str(filmPath).strip()
				image = str(items).split('img src="')[1]
				image = str(image).split('" height=')[0]
				image =str(image).strip()
				name = str(items).split('alt="')[1]
				name = str(name).strip()
				addLink(name,filmPath,2,image)
		
	except:
		pass
	
	MINIMUM = MINIMUM+30
	MAXIMUM = MAXIMUM+30
	addDir('View more movies -->',url,1,'',MINIMUM,MAXIMUM)				
		
def VIDEOLINKS(url,name):
	
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	match2=re.compile('"video_src" href="(.+?)"/>').findall(link)
	if len(match2) :
		filmPath = str(match2).split('type=')[1]
		filmPath = str(filmPath).split('&image')[0]
		filmPath = str(filmPath).strip()
		videoPath= filmPath.replace('%3A',':')
		videoPath=videoPath.replace('%2F','/')
		videoPath =str(videoPath) .split('file=')[1]
		videoPath = str(videoPath).strip()
		listItem = xbmcgui.ListItem(path=str(videoPath))
		xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
			

                
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param




def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok


def addDir(name,url,mode,iconimage,MINIMUM,MAXIMUM):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&MINIMUM="+str(MINIMUM)+"&MAXIMUM="+str(MAXIMUM)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None
MINIMUM = None
MAXIMUM = None


from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
try:
    import json
except:
    import simplejson as json
	
	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass
		
try:
        MINIMUM=int(params["MINIMUM"])
except:
        pass
try:
        MAXIMUM=int(params["MAXIMUM"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        retrievePanetMovies(MINIMUM,MAXIMUM)
	
elif mode==2:
        print ""+url
        VIDEOLINKS(url,name) 

if mode==29:
	PanetListSeries(url)
elif mode==30:
	getPanetEpos(url)
elif mode==31:
	GET_VIDEO_FILE(name,url)
	
	
xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import httplib
import time,itertools



__settings__ = xbmcaddon.Addon(id='plugin.video.rotana')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])



def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	addDir('مسلسلات','http://khalijia.rotana.net/r/tv-series?page=',1,'https://sphotos-a-ord.xx.fbcdn.net/hphotos-ash4/p206x206/406270_444278592272780_2031707310_n.jpg')
	addDir('برامج','http://khalijia.rotana.net/r/tv-shows?page=',1,'https://sphotos-a-ord.xx.fbcdn.net/hphotos-ash4/p206x206/406270_444278592272780_2031707310_n.jpg')
	addDir('افلام','http://cinema.rotana.net/r/movies-asc?page=',2,'http://img809.imageshack.us/img809/5535/rotana.jpg')
	addDir('موسيقا','http://mousica.rotana.net/r/clips?page=',5,'http://www.arabasl.com/pic/rotana_mousica.png')
	
	
		
def indexSeries(url):
            page=0
            try:
                for i in range(0,40):
                    page=page+1
                    req = urllib2.Request(url+str(page))
                    response = urllib2.urlopen(req)
                    link=response.read()
                    matchObj=(re.compile('<a href="(.+?)" class="pull-left item"><img src="(.+?)"><h2 class="site_color">(.+?)</h2><span class="viewFull">').findall(link))
                    for items in matchObj:
                        name=str( items[2]).strip()
                        path='http://khalijia.rotana.net'+str( items[0]).strip()
                        thumbnail=str( items[1]).strip()
                        print name
                        print path
                        addDir(name,path,3,thumbnail)
            except:
                pass
	

def indexFilms(url):
            
            page=0
            try:
                for i in range(0,40):
                    page=page+1
                    req = urllib2.Request(url+str(page))
                    response = urllib2.urlopen(req)
                    link=response.read()
                    matchObj= re.findall(r'<div class="carousel-item pull-left ">(.*?)\s(.*?)<div class="overlay-text">(.*?)</div>', link, re.DOTALL)
                    for items in matchObj:
                        thum_film=str( items[1]).split('<a href="')
                        thumb=str(thum_film[0]).replace('<img src="', '').replace('" width="150" height="190">', '').strip()
                        path=str(thum_film[1]).replace('"></a>', '').strip()
                        path=str(path).split('" class="click-layer')
                        path="http://cinema.rotana.net"+str(path[0]).strip()
                        name=str( items[2]).split('</a><br><br')
                        name=str(name[0]).split('"overlay-link">')
                        name=str(name[1]).strip()
                        print name
                        print path
                        addLink(name,path,4,thumb)
            except:
                pass
				
   
                                 

def getEpos(url):
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            link=response.read()
            matchObjPath=(re.compile('a href="(.+?)" class="pull-left r-item"').findall(link))
            matchObjThumb=(re.compile('style="background-image: url(.+?)"><h2 class="belowtxt">(.+?)<span class="hasVideo">').findall(link))
            for (items,itr)in itertools.izip( matchObjPath,matchObjThumb):
                
                thumb=str( itr[0])
                thumb=str(thumb).replace("('", '').replace("')","")
                thumb=str(thumb).strip()
                
                path='http://khalijia.rotana.net'+str(items)
                name=str(items).split('episodes/')
                name=str(name[1]).replace("-", " ").strip()
                print name
                print path
                addLink(name,path,4,thumb)

def playSerieVideio(url):
            try:
				req = urllib2.Request(url)
				response = urllib2.urlopen(req)
				link=response.read()
				matchObj=(re.compile('<span class="LimelightEmbeddedPlayer"><object id="kaltura_player_1364712831" name="kaltura_player_1364712831" type="application/x-shockwave-flash" allowFullScreen="true" allowNetworking="all" allowScriptAccess="always" height="373" width="620" bgcolor="#000000" xmlns:dc="http://purl.org/dc/terms/" xmlns:media="http://search.yahoo.com/searchmonkey/media/" rel="media:video" resource="(.+?)" data="').findall(link))
				matchObj=str(matchObj).split('entry_id/')
				matchObj=str(matchObj[1]).replace("']",'').strip()
				matchObj='http://myvideo.itworkscdn.com/p/105/sp/10500/raw/entry_id/'+matchObj
				listItem = xbmcgui.ListItem(path=str(matchObj))
				xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
				print matchObj
            except:
				req = urllib2.Request(url)
				response = urllib2.urlopen(req)
				link=response.read()
				matchObj=(re.compile('<object id="kaltura_player_1364712831" name="kaltura_player_1364712831" type="application/x-shockwave-flash" allowFullScreen="true" allowNetworking="all" allowScriptAccess="always" height="565" width="940" bgcolor="#000000" xmlns:dc="http://purl.org/dc/terms/" xmlns:media="http://search.yahoo.com/searchmonkey/media/" rel="media:video" resource="(.+?)" data="').findall(link))
				matchObj=str(matchObj).split('entry_id/')
				matchObj=str(matchObj[1]).replace("']",'').strip()
				matchObj='http://myvideo.itworkscdn.com/p/105/sp/10500/raw/entry_id/'+matchObj
				listItem = xbmcgui.ListItem(path=str(matchObj))
				xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
				pass
				
def indexClips(url):
	try:
		page=0
		for i in range(0,100):
			page=page+1
			req = urllib2.Request(str(url)+str(page))
			response = urllib2.urlopen(req)
			link=response.read()
			matchObj= re.findall(r'<div class="items">(.*?)\s(.*?)<div class="pagination pagination-inverse">', link, re.DOTALL)
			for items in matchObj:
				mypath= items[1]
				mypath=str(mypath).split('</h3><span')
				for itr in mypath:
					mytarget= str(itr).split('" class="pull-left item"><img src="')
									
					try:
						mypath= mytarget[0]
						thumb=mytarget[1]
						thumb=str( thumb).split('&w=150&h=')
						thumb=thumb[0]
						thumb=str(thumb).strip()
						mypath=str(mypath).split('<a href="')
						path='http://mousica.rotana.net'+str(mypath[1])
						name=str(path).split('video_clips/')
						name=str(name[1]).replace('-', ' ')
						addLink(name,path,4,thumb)
					except:
						pass
	except:
		pass
					
		

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param





def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        indexSeries(url)
	
elif mode==2:
        print ""+url
        indexFilms(url)
elif mode==3:
	print ""+url
	getEpos(url)
	
elif mode==4:
        print ""+url
        playSerieVideio(url)
elif mode==5:
        print ""+url
        indexClips(url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# XBMC Add-on for http://www.youtube.com/user/samiratv
# Version 1.0.1
#------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube addon
#------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.2
# - Playable items no use isPlayable=True and folder=False
#---------------------------------------------------------------------------

import os
import sys
import plugintools

YOUTUBE_CHANNEL_ID = "UCZgQePCttsrCUEgWR-RurJQ"

# Entry point
def run():
    plugintools.log("UCZgQePCttsrCUEgWR-RurJQ.run")
    
    # Get params
    params = plugintools.get_params()
    
    if params.get("action") is None:
        main_list(params)
    else:
        action = params.get("action")
        exec action+"(params)"
    
    plugintools.close_item_list()

# Main menu
def main_list(params):
    plugintools.log("UCZgQePCttsrCUEgWR-RurJQ.main_list "+repr(params))

    # On first page, pagination parameters are fixed
    if params.get("url") is None:
        params["url"] = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=1&max-results=50"

    # Fetch video list from YouTube feed
    data = plugintools.read( params.get("url") )
    
    # Extract items from feed
    pattern = ""
    matches = plugintools.find_multiple_matches(data,"<entry>(.*?)</entry>")
    
    for entry in matches:
        plugintools.log("entry="+entry)
        
        # Not the better way to parse XML, but clean and easy
        title = plugintools.find_single_match(entry,"<titl[^>]+>([^<]+)</title>")
        plot = plugintools.find_single_match(entry,"<media\:descriptio[^>]+>([^<]+)</media\:description>")
        thumbnail = plugintools.find_single_match(entry,"<media\:thumbnail url='([^']+)'")
        video_id = plugintools.find_single_match(entry,"http\://www.youtube.com/watch\?v\=([0-9A-Za-z_-]{11})")
        url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+video_id

        # Appends a new item to the xbmc item list
        plugintools.add_item( action="play" , title=title , plot=plot , url=url ,thumbnail=thumbnail , isPlayable=True, folder=False )
    
    # Calculates next page URL from actual URL
    start_index = int( plugintools.find_single_match( params.get("url") ,"start-index=(\d+)") )
    max_results = int( plugintools.find_single_match( params.get("url") ,"max-results=(\d+)") )
    next_page_url = "http://gdata.youtube.com/feeds/api/users/"+YOUTUBE_CHANNEL_ID+"/uploads?start-index=%d&max-results=%d" % ( start_index+max_results , max_results)

    plugintools.add_item( action="main_list" , title=">> Next page" , url=next_page_url , folder=True )

def play(params):
    plugintools.play_resolved_url( params.get("url") )

run()
########NEW FILE########
__FILENAME__ = plugintools
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.2
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# Author: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
#---------------------------------------------------------------------------

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import re
import sys
import os

module_log_enabled = False

# Write something on XBMC log
def log(message):
    xbmc.log(message)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("plugintools."+message)

# Parse XBMC params - based on script.module.parsedom addon    
def get_params():
    _log("get_params")
    
    param_string = sys.argv[2]
    
    _log("get_params "+str(param_string))
    
    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = urllib.unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    
    return data

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item( action="" , title="" , plot="" , url="" ,thumbnail="" , isPlayable = False, folder=True ):
    _log("add_item action=["+action+"] title=["+title+"] url=["+url+"] thumbnail=["+thumbnail+"] isPlayable=["+str(isPlayable)+"] folder=["+str(folder)+"]")

    listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail )
    listitem.setInfo( "video", { "Title" : title, "FileName" : title, "Plot" : plot } )
    
    if url.startswith("plugin://"):
        itemurl = url
        listitem.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    elif isPlayable:
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)
    else:
        itemurl = '%s?action=%s&title=%s&url=%s&thumbnail=%s&plot=%s' % ( sys.argv[ 0 ] , action , urllib.quote_plus( title ) , urllib.quote_plus(url) , urllib.quote_plus( thumbnail ) , urllib.quote_plus( plot ))
        xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=folder)

def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url):
    _log("play_resolved_url ["+url+"]")

    listitem = xbmcgui.ListItem(path=url)
    listitem.setProperty('IsPlayable', 'true')
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", path=url)
    except:
        xlistitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", )
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def get_temp_path():
    _log("get_temp_path")

    dev = xbmc.translatePath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = xbmc.translatePath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text=""):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

f = open( os.path.join( os.path.dirname(__file__) , "addon.xml") )
data = f.read()
f.close()

addon_id = find_single_match(data,'id="([^"]+)"')
if addon_id=="":
    addon_id = find_single_match(data,"id='([^']+)'")

__settings__ = xbmcaddon.Addon(id=addon_id)
__language__ = __settings__.getLocalizedString

########NEW FILE########
__FILENAME__ = default
import xbmcplugin
import xbmcgui
import xbmcaddon
import copy
from xbmcswift2 import Plugin, actions
from resources.lib.shahidnet.utils import imagePath
from resources.lib.shahidnet.api import ShahidNetAPI
from resources.lib.shahidnet.models import MediaType
from resources.lib.shahidnet.scraper import FILTER_GENRE, FILTER_DIALECT, FILTER_PROGRAM_TYPE


plugin = Plugin()

SEARCH_LIMIT = 10

CACHE_NEW_FILTER = plugin.get_storage('CACHE_NEW_FILTER')

CACHE_FILTERS = plugin.get_storage('CACHE_FILTERS')
#CACHE_FILTERS.clear()

STRINGS = {
    # Root menu
    'filter': 30000,
    'channels': 30001,
    'search': 30002,
    'most_popular': 30003,
    'date_released': 30004,
    'add_filter': 30005,
    'program_type': 30006,
    'genre': 30007,
    'dialect': 30008,
    'save': 30009,
    'latest_episodes': 30010,
    'latest_programs': 30011,
    'latest_clips': 30012,
    'most_popular_episodes': 30013,
    'most_popular_clips': 30014,

    # Context menu
    'delete_filter': 30100,

    # Dialogs
    'delete_filter_head': 30110,
    'delete_filter_confirm': 30111,
    'success': 30112,
    'filter_success': 30113,
    'search_shahid': 30114,
}


@plugin.route('/')
def list_main_menu():

    # Initialise cached filters list if required
    if CACHE_FILTERS.get('list') is None:
        CACHE_FILTERS['list'] = []

    filterCount = len(CACHE_FILTERS['list'])

    items = [{
                 'label': _('filter') if filterCount == 0 else '%s ([COLOR blue]%s[/COLOR])' % (_('filter'), str(filterCount)),
                 'path': plugin.url_for('list_filters', hasSaved='False'),
                 'thumbnail': imagePath(plugin, 'art', 'filter.png')
             },
             {
                 'label': _('channels'),
                 'path': plugin.url_for('list_all_channels'),
                 'thumbnail': imagePath(plugin, 'art', 'channels.png')
             },
             {
                 'label': _('search'),
                 'path': plugin.url_for('search'),
                 'thumbnail': imagePath(plugin, 'art', 'search.png')
             },
             {
                 'label': _('most_popular'),
                 'path': plugin.url_for('list_most_popular'),
                 'thumbnail': imagePath(plugin, 'art', 'most_popular.png')
             },
             {
                 'label': _('date_released'),
                 'path': plugin.url_for('list_by_date_released'),
                 'thumbnail': imagePath(plugin, 'art', 'date_released.png')
             }
    ]

    return items


@plugin.route('/filter/remove/<indexId>')
def remove_filter_option(indexId):
    confirmed = xbmcgui.Dialog().yesno(
        _('delete_filter_head'),
        _('delete_filter_confirm')
    )

    if confirmed:
        del CACHE_FILTERS['list'][int(indexId)]

        plugin.notify(msg=_('success'))
        plugin.redirect(plugin.url_for('list_filters', hasSaved='False'))


@plugin.route('/list/filters/save', name='save_new_filter', options={'hasSaved': 'True'})
@plugin.route('/list/filters', options={'hasSaved': 'False'})
def list_filters(hasSaved='False'):
    def make_filter_ctx(filterIndex):
        return (
            _('delete_filter'),
            actions.background(plugin.url_for('remove_filter_option', indexId=filterIndex))
        )

    def filter_link(filter):
        dialectId = filter['dialect']['id'] if 'dialect' in filter else '0'
        genreId = filter['genre']['id'] if 'genre' in filter else '0'
        typeId = filter['type']['id'] if 'type' in filter else '0'

        return plugin.url_for('list_filtered_programs', dialectId=dialectId, genreId=genreId, typeId=typeId)


    def filter_name(filter):
        list = []

        for f in filter:
            list.append(filter[f]['title'])

        return ' + '.join(list)


    # Persist any new filters to the cached list of filters
    canSave = hasSaved == 'True' and len(CACHE_NEW_FILTER.keys()) > 0

    if canSave:
        newfilter = copy.deepcopy(CACHE_NEW_FILTER) # Copy new filter
        CACHE_FILTERS['list'].append(newfilter)
        CACHE_NEW_FILTER.clear()    # Clear copied filter - save to do so because we copied it before
        plugin.notify(msg=_('filter_success'))


    # Create menu items
    items = [{
                 'label': '[COLOR blue]%s...[/COLOR]' % _('add_filter'),
                 'path': plugin.url_for('add_filter')
             }
    ]

    for idx, filter in enumerate(CACHE_FILTERS.get('list')):
        items.append({
            'label': filter_name(filter),
            'path': filter_link(filter),
            'context_menu': [
                make_filter_ctx(str(idx))
            ],
            'replace_context_menu': True,
        })

    return plugin.finish(items, update_listing=canSave)


@plugin.route('/list/programs/filtered/<dialectId>/<genreId>/<typeId>')
def list_filtered_programs(dialectId, genreId, typeId):
    programs = api.get_filtered_programs(dialectId, genreId, typeId)

    items = [{
                 'label': program.name,
                 'path': _program_path(program),
                 'thumbnail': program.thumbnail
             } for program in programs]

    return items


def __filter_items():
    def display_title(title, type):
        if type in CACHE_NEW_FILTER:
            return '%s: [COLOR white][B]%s[/B][/COLOR]' % (title, CACHE_NEW_FILTER[type]['title'])

        return 'Set %s...' % title

    items = [{
                 'label': display_title(_('program_type'), 'programType'),
                 'path': plugin.url_for('add_filter_list', type='programType'),
             },
             {
                 'label': display_title(_('genre'), 'genre'),
                 'path': plugin.url_for('add_filter_list', type='genre'),
             },
             {
                 'label': display_title(_('dialect'), 'dialect'),
                 'path': plugin.url_for('add_filter_list', type='dialect'),
             },
    ]

    # User has set at least one filter option - is allowed to save
    if len(CACHE_NEW_FILTER.keys()) > 0:
        items.append({
            'label': '[COLOR blue]%s[/COLOR]' % _('save'),
            'path': plugin.url_for('save_new_filter')
        })

    return items


@plugin.route('/filters/add')
def add_filter():
    # Clear the new filter working object since user is starting again from scratch
    CACHE_NEW_FILTER.clear()

    items = __filter_items()
    return plugin.finish(items, update_listing=(len(CACHE_NEW_FILTER.keys()) > 0))


@plugin.route('/filters/add/list/<type>')
def add_filter_list(type):
    if type == 'genre':
        options = FILTER_GENRE
    elif type == 'dialect':
        options = FILTER_DIALECT
    else:
        options = FILTER_PROGRAM_TYPE

    # Show select dropdown dialog
    selected = xbmcgui.Dialog().select(
        'Choose a %s' % type,
        map(lambda x: x['title'], options)
    )

    # Add selected filter option to persistent storage
    if selected >= 0:
        CACHE_NEW_FILTER[type] = options[selected]

    # Return updated list of items after user selection
    items = __filter_items()

    return plugin.finish(items, update_listing=True)


@plugin.route('/menu/date_released/')
def list_by_date_released():
    items = [{
                 'label': _('latest_episodes'),
                 'path': plugin.url_for('list_media_items_latest', mediaType=MediaType.EPISODE),
                 'thumbnail': imagePath(plugin, 'art', 'episodes.png')
             },
             {
                 'label': _('latest_programs'),
                 'path': plugin.url_for('list_channel_programs', channelID=' '),
                 'thumbnail': imagePath(plugin, 'art', 'programs.png')
             },
             {
                 'label': _('latest_clips'),
                 'path': plugin.url_for('list_media_items_latest', mediaType=MediaType.CLIP),
                 'thumbnail': imagePath(plugin, 'art', 'clips.png')
             }
    ]

    return plugin.finish(items)


@plugin.route('/menu/most_popular/')
def list_most_popular():
    items = [{
                 'label': _('most_popular_episodes'),
                 'path': plugin.url_for('list_most_watched', programType=MediaType.EPISODE),
                 'thumbnail': imagePath(plugin, 'art', 'episodes.png')
             },
             {
                 'label': _('most_popular_clips'),
                 'path': plugin.url_for('list_most_watched', programType=MediaType.CLIP),
                 'thumbnail': imagePath(plugin, 'art', 'clips.png')
             },
    ]

    return plugin.finish(items)


@plugin.route('/search')
def search():
    search_string = plugin.keyboard(heading=_('search_shahid'))

    url = plugin.url_for('list_main_menu')

    if search_string:
        url = plugin.url_for('search_result', search_string=search_string)

    plugin.redirect(url)


@plugin.route('/search/<search_string>/')
def search_result(search_string):
    programs = api.search(search_term=search_string, limit=SEARCH_LIMIT)

    items = [{
                 'label': program.name,
                 'path': _program_path(program),
                 'thumbnail': program.thumbnail,
                 'properties': [
                     ('fanart_image', program.bgImage)
                 ]
             } for program in programs]

    return items


@plugin.cached_route('/list/channels', TTL=60 * 24) # Cache for 24hours
def list_all_channels():
    channels = api.get_channels()
    sorted_channels = sorted(channels, key=lambda channel: channel.name)

    items = [{
                 'label': channel.name,
                 'path': plugin.url_for('list_channel_programs', channelID=channel.id),
                 'thumbnail': channel.thumbnail,
                 'properties': [
                     ('fanart_image', channel.bgImage)
                 ]
             } for channel in sorted_channels]

    return items


@plugin.cached_route('/list/channels/<channelID>', TTL=60 * 5) # Cache for 5hours
def list_channel_programs(channelID):
    programs = api.get_channel_programs(channelID)

    if channelID.strip() is not '':
        programs = sorted(programs, key=lambda program: program.name)

    items = [{
                 'label': program.name,
                 'path': _program_path(program),
                 'thumbnail': program.thumbnail,
                 'properties': [
                     ('fanart_image', program.bgImage)
                 ]
             } for program in programs]

    return items


@plugin.cached_route('/list/most_watched/<programType>', TTL=60 * 2)
def list_most_watched(programType):
    media_list = api.get_most_watched(programType)

    items = [{
                 'label': media.displayName(),
                 'path': plugin.url_for('play_video_by_url', url=media.url),
                 'thumbnail': media.thumbnail,
                 'is_playable': True
             } for media in media_list]

    return items


def _program_path(program):
    if program.hasEpisodesOnly():
        return plugin.url_for('list_media_items', mediaType=MediaType.EPISODE, programID=program.id)

    if program.hasClipsOnly():
        return plugin.url_for('list_media_items', mediaType=MediaType.CLIP, programID=program.id)

    return plugin.url_for('list_episode_clip_choice', programID=program.id, episodeCount=str(program.episodeCount),
                          clipsCount=str(program.clipCount))


@plugin.cached_route('/list/media/program/<programID>/episode/<episodeCount>/clips/<clipsCount>', TTL=60 * 5)
def list_episode_clip_choice(programID, episodeCount, clipsCount):
    items = [{
                 'label': "Episodes ([COLOR blue]%s[/COLOR] episode%s)" % (
                     episodeCount, 's' if episodeCount > 1 else ''),
                 'path': plugin.url_for('list_media_items', programID=programID, mediaType=MediaType.EPISODE),
                 'thumbnail': imagePath(plugin, 'art', 'episodes.png')
             },
             {
                 'label': "Clips ([COLOR blue]%s[/COLOR] clip%s)" % (clipsCount, 's' if clipsCount > 1 else ''),
                 'path': plugin.url_for('list_media_items', programID=programID, mediaType=MediaType.CLIP),
                 'thumbnail': imagePath(plugin, 'art', 'clips.png')
             }
    ]

    return plugin.finish(items)


@plugin.cached_route('/list/clips/<mediaType>', name='list_media_items_latest', TTL=60 * 2)
@plugin.cached_route('/list/clips/<mediaType>/<programID>', TTL=60 * 2)
def list_media_items(mediaType, programID=''):
    mediaItems = api.get_program_media(programID, mediaType)

    # When programID is not set, we are fetching latest media items; don't modify any sorting
    if programID is not '':
        mediaItems = reversed(mediaItems)

    plugin.set_content('episodes')

    items = [{
                 'label': media.displayName(),
                 'path': plugin.url_for('play_video', programID=programID if programID is not '' else media.seriesId,
                                        mediaType=mediaType,
                                        mediaID=media.id),
                 'thumbnail': media.thumbnail,
                 'info': {
                     'title': media.displayName(),
                     'duration': media.duration,
                     'episode': media.episodeNumber,
                     'dateadded': media.dateAdded,
                     'tvshowtitle': media.seriesName
                 },
                 'is_playable': True
             } for media in mediaItems]

    return items


@plugin.route('/play/<programID>/<mediaType>/<mediaID>')
def play_video(programID, mediaType, mediaID):
    quality = plugin.get_setting('quality')
    url = api.get_media_stream_by_media_id(quality, programID, mediaType, mediaID)

    plugin.log.info('Play Quality: %s' % quality)
    plugin.log.info('Playing url: %s' % url)

    return plugin.set_resolved_url(url)


@plugin.route('/play/<url>')
def play_video_by_url(url):
    '''
        This method is used to play any Shahid.Net videos that have been scraped from their website.
        We don't have the video's media_id, but only have the clip's video URL
    '''
    quality = plugin.get_setting('quality')
    url = api.get_media_stream_by_url(quality, url)

    plugin.log.info('Play Quality: %s' % quality)
    plugin.log.info('Playing url: %s' % url)

    return plugin.set_resolved_url(url)


def log(text):
    plugin.log.info(text)


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        log('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    api = ShahidNetAPI()
    if api:
        plugin.run()

########NEW FILE########
__FILENAME__ = api
from scraper import get_most_watched, get_filtered_programs
from webservice import (get_channels, get_channel_programs, get_program_media, get_media_stream_by_media_id, get_media_stream_by_url, search)


class ShahidNetAPI:


    def get_channels(self):
        """
        :return: List of Channels
        :rtype : list ChannelItem
        """
        return get_channels()


    def get_channel_programs(self, channelID):
        """
        :param channelID:
        :return: List of programs for a Channel ID
        :rtype: list of ProgramItem
        """
        return get_channel_programs(channelID)


    def get_program_media(self, programID, mediaType):
        """
        :param programID: Program ID
        :param mediaType: Media type - either 'episodes' or 'clips'
        :return: List of media items for the current Program ID and media type
        :rtype: list of MediaItem
        """
        return get_program_media(programID, mediaType)


    def get_media_stream_by_media_id(self, quality, programID, mediaType, mediaID):
        '''
        Quality can be one of the following options:
            -> "360p LOW", "720p HD", "240p LOWEST", "520p HIGH"
        '''
        return get_media_stream_by_media_id(quality, programID, mediaType, mediaID)


    def get_media_stream_by_url(self, quality, video_url):
        return get_media_stream_by_url(quality, video_url)


    def get_most_watched(self, mediaType):
        return get_most_watched(mediaType)


    def search(self, search_term, limit=20):
        return search(search_term, limit)

    def get_filtered_programs(self, dialectId, genreId, typeId):
        return get_filtered_programs(dialectId, genreId, typeId)
########NEW FILE########
__FILENAME__ = models
from utils import isEnglish


class MediaType:
    EPISODE = 'episodes'
    CLIP = 'clips'
    PROGRAM = 'programs'


class FilterType:
    GENRE = 'genre'
    DIALECT = 'dialect'
    PROGRAM_Type = 'program'


class ChannelItem:
    def __init__(self, json):
        self.id = json['id']
        self.name = json['name'].strip()
        self.thumbnail = json['thumb_url']
        self.bgImage = json['image_url']


class ProgramItem(ChannelItem):
    def __init__(self, json):
        ChannelItem.__init__(self, json)

        self.episodeCount = int(json['episode_count'])
        self.clipCount = int(json['clip_count'])
        self.viewCount = json['total_views']

    def hasEpisodesOnly(self):
        return int(self.episodeCount) > 0 and int(self.clipCount) is 0

    def hasClipsOnly(self):
        return int(self.episodeCount) is 0 and int(self.clipCount) > 0


class MediaItem():
    def __init__(self, json):
        self.id = json.get("id", '')
        self.type = json.get("type", '').encode('utf-8')
        self.description = json.get("summary", '').strip().encode('utf-8')
        self.seriesName = json.get("series_name", '').encode("utf8")
        self.seriesId = json.get("series_id", '')
        self.episodeNumber = json.get("episode_number", '').encode('utf-8')
        self.seasonNumber = json.get("season_number", '').encode('utf-8')
        self.viewCount = json.get("total_views", '')
        self.thumbnail = json.get("thumb_url", '')
        self.duration = json.get("duration", '')
        self.dateAdded = json.get("tx_date", '')
        self.url = json.get("url", '')  # populated only for items scraped from the web

    def displayName(self):

        display_list = ['[COLOR white][B]%s[/B][/COLOR]' % self.seriesName]

        if self.description:
            if isEnglish(self.description.decode('utf-8')):
                display_list.append('-')

            if not isEnglish(self.description.decode('utf-8')):
                display_list.append('I')

            display_list.append(self.description)

        display_list.append('{start}Episode {no}{end}'.format(start='(' if self.description else '',
                                                              no=self.episodeNumber,
                                                              end=',' if self.description else ''
        ))

        display_list.append('{start}Season {no})'.format(start='' if self.description else '(', no=self.seasonNumber))

        return ' '.join(display_list)


    def isEpisode(self):
        return self.type == 'episode'

    def isClip(self):
        return self.type == 'clip'

########NEW FILE########
__FILENAME__ = scraper
import re
from models import MediaType
from utils import html
from models import ChannelItem, ProgramItem, MediaItem


MAX_LIMIT = 25

URL_MOST_WATCHED = "http://shahid.mbc.net/Ajax/popular?operation={operation}&time_period=month&&offset={offset}&limit={maxLimit}"
URL_LATEST = "http://shahid.mbc.net/Ajax/recent/{operation}/0/0/0/4?offset={offset}&limit={maxLimit}"
URL_FILTER = "http://shahid.mbc.net/Ajax/seriesFilter?year=0&dialect={dialect}&title=0&genre={genre}&channel=0&prog_type={type}&media_type=0&airing=0&sort=latest&series_id=0&offset=0&sub_type=0&limit={limit}"

FILTER_PROGRAM_TYPE = [
    {'id': '22', 'title': 'Cartoon'},
    {'id': '21', 'title': 'Documentary'},
    {'id': '20', 'title': 'Programs'},
    {'id': '19', 'title': 'Series'},
]

FILTER_GENRE = [
    {'id': '24', 'title': 'Comedy'},
    {'id': '2', 'title': 'Drama'},
    {'id': '22', 'title': 'Educational'},
    {'id': '3', 'title': 'Entertainment'},
    {'id': '4', 'title': 'Game Show'},
    {'id': '14', 'title': 'Health'},
    {'id': '5', 'title': 'History'},
    {'id': '6', 'title': 'Horror'},
    {'id': '11', 'title': 'Lifestyle'},
    {'id': '8', 'title': 'Music'},
    {'id': '19', 'title': 'News'},
    {'id': '10', 'title': 'Politics'},
    {'id': '15', 'title': 'Reality TV'},
    {'id': '9', 'title': 'Religious'},
    {'id': '7', 'title': 'Romance'},
    {'id': '17', 'title': 'Social'},
    {'id': '21', 'title': 'Sports'},
    {'id': '18', 'title': 'Talk Show'},
    {'id': '13', 'title': 'Tourism'},
    {'id': '25', 'title': 'Wrestling'}
]

FILTER_DIALECT = [
    {'id': '2', 'title': 'Arabic'},
    {'id': '12', 'title': 'Bedouin'},
    {'id': '8', 'title': 'Dubbed Indian'},
    {'id': '15', 'title': 'Dubbed Korean'},
    {'id': '7', 'title': 'Dubbed Latin'},
    {'id': '6', 'title': 'Dubbed Turkish'},
    {'id': '3', 'title': 'Egyptian'},
    {'id': '13', 'title': 'English'},
    {'id': '1', 'title': 'Gulf'},
    {'id': '14', 'title': 'Iraqi'},
    {'id': '5', 'title': 'Jordanian'},
    {'id': '11', 'title': 'Lebanese'},
    {'id': '4', 'title': 'Syrian'},
]

MOST_WATCHED_MAP = {
    MediaType.PROGRAM: 'load_popular_programs',
    MediaType.EPISODE: 'load_popular_episodes',
    MediaType.CLIP: 'load_popular_clips'
}

LATEST_MAP = {
    MediaType.PROGRAM: 'load_recent_series',
    MediaType.EPISODE: 'load_recent_episodes',
    MediaType.CLIP: 'load_recent_clips'
}

MEDIA_TYPE = {
    MediaType.EPISODE: 'episode',
    MediaType.CLIP: 'clip',
    MediaType.PROGRAM: 'program',
}


def get_most_watched(programType):
    url = URL_MOST_WATCHED.format(operation=MOST_WATCHED_MAP[programType], offset='0', maxLimit=MAX_LIMIT)
    html_response = html(url)

    items = html_response.find('ul').findAll('a', {'class': 'tip_anchor'})
    return [_get_item(clip, programType) for clip in items]


def _get_item(el, mediaType):
    span_list = el.findAll('span', {'class': re.compile(r"\b.*title.*\b")})
    description = el.find('span', {'class': 'title_minor'})
    season_episode_str = span_list[2].contents[0].strip()

    # Extract Season and Episode no from a mixed string (e.g. "Season 1, Episode 3) in Arabic
    digits_list = re.findall(r'\d{1,5}', season_episode_str)

    json = {
        'type': MEDIA_TYPE[mediaType],
        'summary': '' if len(description.contents) == 0 else description.contents[0].strip(),
        'series_name': span_list[0].contents[0].strip(' -'),
        'episode_number': digits_list[1] if len(digits_list) > 1 else '',
        'season_number': digits_list[0],
        'thumb_url': el.find('img')['src'],
        'url': re.sub('(.*[0-9]\/).*', r'\g<1>', el['href']), # strip out troublesome ascii characters
    }

    return MediaItem(json)


def get_latest(mediaType):
    '''
    Deprecated. Using Shahid.Net API to fetch the latest media items by different media types
    '''
    url = URL_LATEST.format(operation=LATEST_MAP[mediaType], offset='0', maxLimit=MAX_LIMIT)
    response = html(url)
    return response


def _get_program_item(el):
    span_list = el.find('a', {'class': 'tip_anchor'}).findAll('span', {'class': re.compile(r"\b.*title.*\b")})
    season_episode_str = span_list[-1].contents[0].strip()
    digits_list = re.findall(r'\d{1,5}', season_episode_str)

    json = {
        'id': el['class'].replace('ser_', ''),
        'name': span_list[0].contents[0].strip(' -'),
        'thumb_url': el.find('img')['src'],
        'image_url': '',
        'episode_count': digits_list[0],
        'clip_count': '0',
        'total_views': '',
    }

    return ProgramItem(json)


def get_filtered_programs(dialectId, genreId, typeId):
    url = URL_FILTER.format(dialect=dialectId, genre=genreId, type=typeId, limit=MAX_LIMIT)
    html_response = html(url)

    items = html_response.find('ul').findAll('a', {'class': 'tip_anchor'})
    items = html_response.findAll('li')
    return [_get_program_item(clip) for clip in items]


def debug():
    #for item in get_most_watched(MediaType.CLIP):
    #    print item.description
    #    print get_latest(MediaType.PROGRAM)

    #print get_most_watched(MediaType.CLIP)
    print get_filtered_programs('6', '4', '0')


if __name__ == '__main__':
    debug()



########NEW FILE########
__FILENAME__ = utils
import json as j
import os
from urllib2 import urlopen
from BeautifulSoup import BeautifulSoup
import unicodedata


latin_letters= {}


def get(url):
    """Performs a GET request for the given url and returns the response"""
    conn = urlopen(url)
    resp = conn.read()
    conn.close()
    return resp


def html(url):
    """Downloads the resource at the given url and parses via BeautifulSoup"""
    return BeautifulSoup(get(url), convertEntities=BeautifulSoup.HTML_ENTITIES)


def json(url):
    print 'Fetching JSON from: ' + url
    response = get(url).decode("utf-8-sig")
    return j.loads(response)


def isEnglish(unistr):
    return all(_is_latin(uchr)
           for uchr in unistr
           if uchr.isalpha()) # isalpha suggested by John Machin


def _is_latin(uchr):
    try: return latin_letters[uchr]
    except KeyError:
         return latin_letters.setdefault(uchr, 'LATIN' in unicodedata.name(uchr))


def imagePath(plugin, folder, *args):
    return os.path.join(plugin.addon.getAddonInfo('path'), folder, *args)
########NEW FILE########
__FILENAME__ = webservice
import re
from models import ChannelItem, ProgramItem, MediaItem
from utils import json


API_KEY = '4cd216240b9e47c3d97450b9b4866d3f'


URL_CHANNEL_LIST = "http://shahid.mbc.net/api/channelList?api_key={apiKey}&offset=0&limit=60"
URL_PROGRAMS_LIST = "http://shahid.mbc.net/api/programsList?api_key={apiKey}&offset=0&limit=60&channel_id={channelID}"
URL_MEDIA_LIST = "http://shahid.mbc.net/api/mediaList?api_key={apiKey}&offset=0&limit=60&program_id={programID}&sub_type={mediaType}"
URL_MEDIA_INFO = "http://shahid.mbc.net/api/mediaInfoList?api_key={apiKey}&media_id={mediaID}&offset=0&limit=60&program_id={programID}&sub_type={mediaType}"

URL_MEDIA_STREAM_BY_MEDIA_ID = "http://hadynz-shahid.appspot.com/scrape?m={mediaHash}"
URL_MEDIA_STREAM_BY_VIDEO_ID = "http://hadynz-shahid.appspot.com/scrape?v={videoId}"

URL_SEARCH = "http://shahid.mbc.net/api/programsList?api_key={apiKey}&offset=0&limit={limit}&keyword={keyword}"


def get_channels():
    """
    :return: Returns list of all Channels
    :rtype : list of ChannelItem
    """
    response = json(URL_CHANNEL_LIST.format(apiKey=API_KEY))
    return [ChannelItem(channelJson) for channelJson in response['channels']]


def get_channel_programs(channelID):
    """
    :param channelID: Channel ID
    :return: list of programs for th current Channel ID
    :rtype: list of ProgramItem
    """
    response = json(URL_PROGRAMS_LIST.format(apiKey=API_KEY, channelID=channelID))
    programs = [ProgramItem(programJson) for programJson in response['programs']]

    # Only return programs with one or more episodes/clips
    return filter(lambda x: (x.episodeCount + x.clipCount) > 0, programs)


def get_program_media(programID, mediaType):
    response = json(URL_MEDIA_LIST.format(apiKey=API_KEY, programID=programID, mediaType=mediaType))
    return [MediaItem(mediaJson) for mediaJson in response['media']]


def _get_media_info(programID, mediaType, mediaID):
    response = json(URL_MEDIA_INFO.format(apiKey=API_KEY, programID=programID, mediaType=mediaType, mediaID=mediaID))
    return response['media']


def _get_media_id_hash(programID, mediaType, mediaID):
    mediaInfo = _get_media_info(programID, mediaType, mediaID)
    mediaUrl = mediaInfo['media_url']

    try:
        matchObj = re.search(r'media\/(.*)\.m3u8', mediaUrl, re.M | re.I)
        mediaHash = matchObj.group(1)

        return mediaHash

    except Exception as ex:
        print 'Error parsing media hash from media url: %s' % ex

    return None


def get_media_stream_by_media_id(quality, programID, mediaType, mediaID):
    mediaHash = _get_media_id_hash(programID, mediaType, mediaID)

    streams = json(URL_MEDIA_STREAM_BY_MEDIA_ID.format(mediaHash=mediaHash))
    return _get_matching_stream_quality(quality, streams)


def get_media_stream_by_url(quality, url):
    match_obj = re.search(r'.*video\/(.*)\/.*', url, re.M | re.I)
    video_id = match_obj.group(1)

    streams = json(URL_MEDIA_STREAM_BY_VIDEO_ID.format(videoId=video_id))
    return _get_matching_stream_quality(quality, streams)


def _get_matching_stream_quality(quality, streams):
    for stream in streams:
        if quality == stream['Quality']:
            return stream['URL']

    return None


def search(search_term, limit=20):
    response = json(URL_SEARCH.format(apiKey=API_KEY, keyword=search_term, limit=limit))
    programs = [ProgramItem(programJson) for programJson in response['programs']]
    return programs


def debug():
    '''
    for program in get_channel_programs('8'):
        print program['mobile_image_url'] + ' id=' + program['id'] + ' clip_count=' + program['clip_count'] + ' episode_count=' +  program['episode_count'] + ' item_type=' + program['item_type']

    for media in get_program_media('1559', 'episodes'):
        print media

    print get_media_stream('360p LOW', '1559', 'episodes', '53899')
    '''

    #url = 'http://shahid.mbc.net/media/video/46534/Arabs_got_talent_%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9_7'
    #print get_media_stream_by_url('360p LOW', url)

    print search('Ar')


if __name__ == '__main__':
    debug()

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin
import urllib2,urllib,cgi, re
import HTMLParser
import xbmcaddon
import json
import traceback
import os
import sys
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP, Tag,NavigableString
try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
	try:
	  # Python 2.5
	  import xml.etree.ElementTree as etree
	  print("running with ElementTree on Python 2.5+")
	except ImportError:
	  try:
		# normal cElementTree install
		import cElementTree as etree
		print("running with cElementTree")
	  except ImportError:
		try:
		  # normal ElementTree install
		  import elementtree.ElementTree as etree
		  print("running with ElementTree")
		except ImportError:
		  print("Failed to import ElementTree from any known place")

import json

__addon__       = xbmcaddon.Addon()
__addonname__   = __addon__.getAddonInfo('name')
__icon__        = __addon__.getAddonInfo('icon')
addon_id = 'plugin.video.shahidmbcnet'
selfAddon = xbmcaddon.Addon(id=addon_id)
addonPath = xbmcaddon.Addon().getAddonInfo("path")
addonArt = os.path.join(addonPath,'resources/images')
communityStreamPath = os.path.join(addonPath,'resources/community')
profile_path =  xbmc.translatePath(selfAddon.getAddonInfo('profile'))
 
mainurl='http://shahid.mbc.net'
apikey='AIzaSyCl5mHLlE0mwsyG4uvNHu5k1Ej1LQ_3RO4'

def getMainUrl():
	rMain=mainurl
	#check setting and see if we have proxy define, ifso, use that
	isProxyEnabled=defaultCDN=selfAddon.getSetting( "isProxyEnabled" )
	proxyAddress=defaultCDN=selfAddon.getSetting( "proxyName" )
	if isProxyEnabled:#if its not None
		#print 'isProxyEnabled',isProxyEnabled,proxyAddress
		if isProxyEnabled=="true":
			#print 'its enabled'
			rMain=proxyAddress
		#else: #print 'Proxy not enable'
	return rMain
	
	
	

VIEW_MODES = {
    'thumbnail': {
        'skin.confluence': 500,
        'skin.aeon.nox': 551,
        'skin.confluence-vertical': 500,
        'skin.jx720': 52,
        'skin.pm3-hd': 53,
        'skin.rapier': 50,
        'skin.simplicity': 500,
        'skin.slik': 53,
        'skin.touched': 500,
        'skin.transparency': 53,
        'skin.xeebo': 55,
    },
}

def get_view_mode_id( view_mode):
	view_mode_ids = VIEW_MODES.get(view_mode.lower())
	if view_mode_ids:
		return view_mode_ids.get(xbmc.getSkinDir())
	return None

def addLink(name,url,iconimage):
	ok=True
	liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name } )
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
	return ok

def Colored(text = '', colorid = '', isBold = False):
	if colorid == 'one':
		color = 'FF11b500'
	elif colorid == 'two':
		color = 'FFe37101'
	elif colorid == 'bold':
		return '[B]' + text + '[/B]'
	else:
		color = colorid
		
	if isBold == True:
		text = '[B]' + text + '[/B]'
	return '[COLOR ' + color + ']' + text + '[/COLOR]'	
	
def addDir(name,url,mode,iconimage	,showContext=False,isItFolder=True,pageNumber="", isHTML=True,addIconForPlaylist=False, AddRemoveMyChannels=None):
#	print name
#	name=name.decode('utf-8','replace')
	if isHTML:
		h = HTMLParser.HTMLParser()
		name= h.unescape(name).decode("utf-8")
		rname=  name.encode("utf-8")
	else:
		#h = HTMLParser.HTMLParser()
		#name =h.unescape(name).decode("utf-8")
		rname=  name.encode("utf-8")
#		url=  url.encode("utf-8")
#	url= url.encode('ascii','ignore')

	
	#print rname
	#print iconimage
	u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(rname)
	if len(pageNumber):
		u+="&pagenum="+pageNumber
	if addIconForPlaylist:
		u+="&addIconForPlaylist=yes"
	ok=True
#	print iconimage
	liz=xbmcgui.ListItem(rname, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	#liz.setInfo( type="Video", infoLabels={ "Title": name } )

	if showContext==True:
		cmd1 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "l3")
		cmd2 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "xdn")
		cmd3 = "XBMC.RunPlugin(%s&cdnType=%s)" % (u, "ak")
		liz.addContextMenuItems([('Play using L3 Cdn',cmd1),('Play using XDN Cdn',cmd2),('Play using AK Cdn',cmd3)])

	if not AddRemoveMyChannels==None:
		if AddRemoveMyChannels:
			cmd1 = "XBMC.RunPlugin(%s&AddRemoveMyChannels=add)" % (u)
			liz.addContextMenuItems([('Add to My Channels',cmd1)])
		else:
			cmd1 = "XBMC.RunPlugin(%s&AddRemoveMyChannels=remove)" % (u)
			liz.addContextMenuItems([('Remove from My Channels',cmd1)])
			
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=isItFolder)
	return ok
	


def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]
				
	return param




def Addtypes():
	#2 is series=3 are links
	addDir('Shahid Vod by Channels' ,getMainUrl()+'/ar/channel-browser.html' ,2,addonArt+'/channels.png') #links #2 channels,3 series,4 video entry, 5 play
	addDir('Shahid Vod by Series' ,getMainUrl()+'/ar/series-browser.html' ,6,addonArt+'/serial.png')
	#addDir('Streams' ,'streams' ,9,addonArt+'/stream.png')
	addDir('Shahid Live' ,'CCats' ,14,addonArt+'/Network-1-icon.png')
	addDir('Shahid Youtube' ,'http://gdata.youtube.com/feeds/api/users/aljadeedonline' ,18,addonArt+'/youtube.png')    
	addDir('Download Files' ,'cRefresh' ,17,addonArt+'/download-icon.png',isItFolder=False)
	addDir('Settings' ,'Settings' ,8,addonArt+'/setting.png',isItFolder=False) ##
	return

def AddYoutubeLanding(url):
	if not url.lower().startswith('http'):
		if url=='LOCAL':
			filename=selfAddon.getSetting( "localyoutubexmlpath" )
		else:
			filename=url
		#print 'filename',filename
		if len(filename)>0:
			data = open(filename.decode('utf-8'), "r").read()
			#print data
			directories=getETreeFromString(data)
		else:
			dialog = xbmcgui.Dialog()
			ok = dialog.ok('XBMC', 'File not defined')
			return
	else:
		directories=getETreeFromUrl(url)
	for dir in directories.findall('dir'):
		name = dir.find('name').text
		link= dir.find('link')
		if not link==None: link=link.text
		videouser= dir.find('youtubeuser')
		if not videouser==None: videouser=videouser.text
		
		channelID= dir.find('channelid')
		if not channelID==None: channelID=channelID.text
		
		thumbnail= dir.find('thumbnail')
		if not thumbnail==None: thumbnail=thumbnail.text
		
		
		#print name,link
		thumbnail= dir.find('thumbnail').text
		if thumbnail==None:
			thumbnail=''
		#print 'thumbnail',thumbnail
		type = dir.find('type')

		if type==None:
			#check the link and decide
			if not link==None:
				if link.endswith('playlists'):
					type='playlist'
				elif link.endswith('uploads'):
					type='videos'
				elif 'watch?v' in link:
					type='video'
				else:
					type='dir'
			else:
				type='dir'
		else:
			type=type.text
		#print 'channelID',channelID
		if type=='playlist' or  type=='videos':
			if channelID==None or  len(channelID)==0:
				if videouser==None:
					#get it from the link
					link=link.split('/')[-2]
				else:
					link=videouser
				#print 'link for Channelid',link
				link=getChannelIdByUserName(link)#passusername
			else:
				link=channelID
		icon=addonArt+'/video.png'
		if (not thumbnail==None) and len(thumbnail)>0:
			icon=thumbnail
		#print 'icon',icon
		if type=='playlist':
			addDir(name ,link ,22,addonArt+'/playlist.png',isHTML=False) 
		elif type=='videos':
			addDir(name ,link ,20,icon,isHTML=False)
		elif type=='video':
			addDir(name ,link  ,21,thumbnail,isItFolder=False, isHTML=False)		#name,url,mode,icon
		else:
			addDir(name ,link  ,19,thumbnail,isItFolder=True, isHTML=False)		#name,url,mode,icon
	 
	
	
def checkAndRefresh():
	try:
		import time
		lastUpdate=selfAddon.getSetting( "lastupdate" )
		do_update=False
		now_date=time.strftime("%d/%m/%Y")
		if lastUpdate==None or lastUpdate=="":
			do_update=True
		else:
			#print 'lastUpdate',lastUpdate,now_date
			if not now_date==lastUpdate:
				do_update=True
		selfAddon.setSetting( id="lastupdate" ,value=now_date)
		if do_update:
			RefreshResources(True)
	except: pass

def RefreshResources(auto=False):
#	print Fromurl
	pDialog = xbmcgui.DialogProgress()
	if auto:
		ret = pDialog.create('XBMC', 'Daily Auto loading Fetching resources...')
	else:
		ret = pDialog.create('XBMC', 'Fetching resources...')
	baseUrlForDownload='https://raw.githubusercontent.com/Shani-08/ShaniXBMCWork/master/plugin.video.shahidmbcnet/resources/community/'
	Fromurl=baseUrlForDownload+'Resources.xml'
	req = urllib2.Request(Fromurl)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	data=response.read()
	response.close()
	#data='<resources><file fname="Categories.xml"/><file fname="palestinecoolUrls.xml" url="http://goo.gl/yNlwCM"/></resources>'
	pDialog.update(20, 'Importing modules...')
	soup= BeautifulSOAP(data, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
	resources=soup('file')
	fileno=1
	totalFile = len(resources)
	
	for rfile in resources:
		progr = (fileno*80)/totalFile
		fname = rfile['fname']
		remoteUrl=None
		try:
			remoteUrl = rfile['url']
		except: pass
		if remoteUrl:
			fileToDownload = remoteUrl
		else:
			fileToDownload = baseUrlForDownload+fname
		#print fileToDownload
		req = urllib2.Request(fileToDownload)
		req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
		response = urllib2.urlopen(req)
		data=response.read()
		if len(data)>0:
			with open(os.path.join(communityStreamPath, fname), "wb") as filewriter:
				filewriter.write(data)
			pDialog.update(20+progr, 'imported ...'+fname)
		else:
			pDialog.update(20+progr, 'Failed..zero byte.'+fname)
		fileno+=1
	pDialog.close()
	dialog = xbmcgui.Dialog()
	ok = dialog.ok('XBMC', 'Download finished. Close close Addon and come back')

def removeLoginFile():
	try:
		COOKIEFILE = communityStreamPath+'/livePlayerLoginCookie.lwp'
		os.remove(COOKIEFILE)
	except: pass
	try:
		COOKIEFILE = communityStreamPath+'/teletdunetPlayerLoginCookie.lwp'
		os.remove(COOKIEFILE)
	except: pass

def ShowSettings(Fromurl):
	selfAddon.openSettings()
	removeLoginFile()
	return
	
def AddSeries(Fromurl,pageNumber=""):
#	print Fromurl
	req = urllib2.Request(Fromurl)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	#print Fromurl
#	print "addshows"
#	match=re.compile('<param name="URL" value="(.+?)">').findall(link)
#	match=re.compile('<a href="(.+?)"').findall(link)
#	match=re.compile('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>').findall(link)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);".?>(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('<div class=\"post-title\"><a href=\"(.*?)\".*<b>(.*)<\/b><\/a>', link, re.IGNORECASE)
#	match =re.findall('<img src="(.*?)" alt=".*".+<\/a>\n*.+<div class="post-title"><a href="(.*?)".*<b>(.*)<\/b>', link, re.UNICODE)
	#regstring='<a href="(.*?)">[\s\t\r\n\f]*.*[\s\t\r\n\f]+.*[\s\t\r\n\f].*<img .*?alt="(.*?)" src="(.*?)"'
	regstring='<a href="(\/ar\/(show|series).*?)">\s.*\s*.*\s.*alt="(.*)" src="(.*?)" '
	match =re.findall(regstring, link)
	#print match
	#match=re.compile('<a href="(.*?)"targe.*?<img.*?alt="(.*?)" src="(.*?)"').findall(link)
	#print Fromurl


	for cname in match:
		addDir(cname[2] ,getMainUrl()+cname[0] ,4,cname[3])#name,url,img
	if mode==6:
		if not pageNumber=="":
			pageNumber=str(int(pageNumber)+1);#parseInt(1)+1;
		else:
			pageNumber="1";

		purl=getMainUrl()+'/ar/series-browser/autoGeneratedContent/seriesBrowserGrid~browse~-param-.sort-latest.pageNumber-%s.html' % pageNumber
		addDir('Next Page' ,purl ,6,addonArt+'/next.png', False,pageNumber=pageNumber)		#name,url,mode,icon
	
#	<a href="http://www.zemtv.com/page/2/">&gt;</a></li>
#	match =re.findall('<a href="(.*)">&gt;<\/a><\/li>', link, re.IGNORECASE)
	
#	if len(match)==1:
#		addDir('Next Page' ,match[0] ,2,'')
#       print match
	
	return

def AddEnteries(Fromurl,pageNumber=0):
#	print Fromurl
	req = urllib2.Request(Fromurl)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
#	print link
#	print "addshows"
#	match=re.compile('<param name="URL" value="(.+?)">').findall(link)
#	match=re.compile('<a href="(.+?)"').findall(link)
#	match=re.compile('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>').findall(link)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);".?>(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('<div class=\"post-title\"><a href=\"(.*?)\".*<b>(.*)<\/b><\/a>', link, re.IGNORECASE)
#	match =re.findall('<img src="(.*?)" alt=".*".+<\/a>\n*.+<div class="post-title"><a href="(.*?)".*<b>(.*)<\/b>', link, re.UNICODE)
#	print Fromurl
	match =re.findall('<a href="(\/ar\/episode.*?)">\s.*\s.*\s.*\s.*\s.*\s.*<img .*?alt="(.*?)" src="(.*?)".*\s.*.*\s.*.*\s.*.*\s.*.*\s.*.*\s.*\s*.*?>(.*?)<\/div>\s*.*?>(.*?)<\/div>', link, re.UNICODE)
#	print Fromurl

	#print match
	#h = HTMLParser.HTMLParser()
	
	#print match
	totalEnteries=len(match)
	for cname in match:
		finalName=cname[1];
		if len(finalName)>0: finalName+=' '
		finalName+=cname[3].replace('<span>','').replace('</span>','')
		
		#print 'a1'
		
		#if len(finalName)>0: finalName+=u" ";
		#print 'a2'
		if len(finalName)>0: finalName+=' '
		finalName+=cname[4]
		#print 'a3'
		#finalName+=cname[3]
		#print 'a4'
        
		#print cname[2]
		addDir(finalName ,getMainUrl()+cname[0] ,5,cname[2],showContext=True,isItFolder=False)
		
		
	if totalEnteries==24:
		match =re.findall('<li class="arrowrgt"><a.*?this, \'(.*?(relatedEpisodeListingDynamic).*?)\'', link, re.UNICODE)
		if len(match)>0 or mode==7  :
			if not pageNumber=="":
				pageNumber=str(int(pageNumber)+1);#parseInt(1)+1;
			else:
				pageNumber="1";
			if mode==7:
				newurl=(Fromurl.split('pageNumber')[0]+'-%s.html')%pageNumber
			else:
				newurl=getMainUrl()+match[0][0]+'.sort-number:DESC.pageNumber-%s.html'%pageNumber;
			addDir('Next Page' ,newurl ,7,addonArt+'/next.png', False,pageNumber=pageNumber)		#name,url,mode,icon
	
		
		
#	<a href="http://www.zemtv.com/page/2/">&gt;</a></li>
	#match =re.findall('<link rel=\'next\' href=\'(.*?)\' \/>', link, re.IGNORECASE)
	
	#if len(match)==1:
#		addDir('Next Page' ,match[0] ,3,'')
#       print match
	
	return
	
def AddChannels(liveURL):
	req = urllib2.Request(liveURL)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
#	print link
#	match=re.compile('<param name="URL" value="(.+?)">').findall(link)
#	match=re.compile('<a href="(.+?)"').findall(link)
#	match=re.compile('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>').findall(link)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);">(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('onclick="playChannel\(\'(.*?)\'\);".?>(.*?)</a>', link, re.DOTALL|re.IGNORECASE)
#	match =re.findall('<div class=\"post-title\"><a href=\"(.*?)\".*<b>(.*)<\/b><\/a>', link, re.IGNORECASE)
#	match =re.findall('<img src="(.*?)" alt=".*".+<\/a>\n*.+<div class="post-title"><a href="(.*?)".*<b>(.*)<\/b>', link, re.UNICODE)

	match =re.findall('<div class="subitem".*?id="(.*)">\s*.*\s*<a href="(.*?)".*\s.*\s*<.*src="(.*?)"', link,re.M)

	#print match
	#h = HTMLParser.HTMLParser()
	#print match
	for cname in match:
		chName=cname[1].split('/')[-1].split('.htm')[0]
		#print chName
		addDir(chName ,getMainUrl()+cname[1] ,3,cname[2], False,isItFolder=True)		#name,url,mode,icon

	return	
	
def AddYoutubeSources(url):
	addDir('Most Popular' ,'MOSTPOP' ,23,addonArt+'/top.png',isHTML=False)
	addDir('Most Popular Today' ,'MOSTPOPToday' ,23,addonArt+'/toptday.png',isHTML=False)
	#addDir('Most Viewed' ,'https://gdata.youtube.com/feeds/api/standardfeeds/most_popular?orderby=viewCount' ,20,addonArt+'/topview.png',isHTML=False)
	data=getYoutubeSources()
	addDir('Your Videos' ,'LOCAL' ,19,addonArt+'/yourtube.png',isItFolder=True, isHTML=False)		#name,url,mode,icon

	for stuff in data:
		addDir(stuff[0] ,stuff[1] ,19,stuff[2],isItFolder=True, isHTML=False)		#name,url,mode,icon
	



def getYoutubeSources():
	#Ssoup=getSoup('YoutubeSources.xml');
	sources=getEtreeFromFile('YoutubeSources.xml');
	ret=[]
	try:
		for source in sources.findall('source'):
			isEnabled = source.findtext('enabled').lower()
			if isEnabled=="true":
				ret.append([source.findtext('sname'),source.findtext('url'),source.findtext('imageurl')])
	except:
		traceback.print_exc(file=sys.stdout)
		pass
	return ret
		
def PlayYoutube(url):
	youtubecode=url
	uurl = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % youtubecode
	xbmc.executebuiltin("xbmc.PlayMedia("+uurl+")")

def AddYoutubePlaylists(channelId):
	#if not username.startswith('https://www.googleapis'):
	#	channelId=getChannelIdByUserName(username)#passusername
	#else:
	#	channelId=username
	#channelId=username
	playlists,next_page=getYouTubePlayList(channelId);
	for playList in playlists:
		#print playList
		addDir(playList[0] ,playList[1] ,23,playList[2],isItFolder=True, isHTML=False)		#name,url,mode,icon
	if next_page:
		addDir('Next' ,next_page ,22,addonArt+'/next.png',isItFolder=True)		#name,url,mode,icon
	
		
def getYouTubePlayList(channelId):
	if not channelId.startswith('https://www.googleapis'):
		u_url='https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId=%s&maxResults=25&key=%s'%(channelId,apikey)
	else:
		u_url=channelId
	doc=getJson(u_url)
	ret=[]
	for playlist_item in doc['items']:
		
		title = playlist_item["snippet"]["title"]
		id = playlist_item["id"]
		if not title=='Private video':
			imgurl=''
			try:
				imgurl= playlist_item["snippet"]["thumbnails"]["high"]["url"]
			except: pass
			if imgurl=='':
				try:
					imgurl= playlist_item["snippet"]["thumbnails"]["default"]["url"]
				except: pass
			ret.append([title,id,imgurl])
	nextItem=None
	if 'nextPageToken' in doc:
		nextItem=doc["nextPageToken"]
	else:
		nextItem=None
		
	nextUrl=None
	if nextItem:
		if not '&pageToken' in u_url:
			nextUrl=u_url+'&pageToken='+nextItem
		else:
			nextUrl=u_url.split('&pageToken=')[0]+'&pageToken='+nextItem
		
	return ret,nextUrl;
	
def AddYoutubeVideosByChannelID(channelId,addIconForPlaylist):
	AddPlayListIcon=True #add all the time
	#if AddPlayListIcon="yes":
	#	AddPlayListIcon=True
	#channelId=getChannelIdByUserName(url)#passusername
	playlist=getUploadPlaylist(channelId)
	AddYoutubeVideosByPlaylist(playlist,AddPlayListIcon,channelId)

def AddYoutubeVideosByPlaylist(playListId,AddPlayListIcon=False, channelid=None):
	#print 'AddYoutube',url
	if playListId=='MOSTPOP':
		videos,next_page=getYoutubeVideosPopular();
	elif playListId=='MOSTPOPToday':
		videos,next_page=getYoutubeVideosPopular(True);
	else:
		videos,next_page=getYoutubeVideosByPlaylist(playListId);
	if AddPlayListIcon:
		addDir('Playlists' ,channelid ,22,addonArt+'/playlist.png',isHTML=False) 
	
	for video in videos:
		#print chName
		#print video
		addDir(video[0] ,video[1] ,21,video[2],isItFolder=False, isHTML=False)		#name,url,mode,icon
	if next_page:
		addDir('Next' ,next_page ,23,addonArt+'/next.png',isItFolder=True)		#name,url,mode,icon

def getFirstElement(elements,attrib, val):
	for el in elements:
		#print el.attrib[attrib]
		if el.attrib[attrib]==val:
			print 'found next'
			return el
	return None

def getJson(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	#link=response.read()
	#response.close()
	decoded = json.load(response)
	return decoded
	
	
def getChannelIdByUserName(username):
	u_url='https://www.googleapis.com/youtube/v3/channels?part=id&forUsername=%s&key=%s'%(username,apikey)
	channelData=getJson(u_url)
	return channelData['items'][0]['id']

def getUploadPlaylist(mainChannel):
	u_url='https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id=%s&key=%s'%(mainChannel,apikey)
	doc=getJson(u_url)
	upload_feed=doc['items'][0]['contentDetails']['relatedPlaylists']['uploads']
	return upload_feed

	
def getYoutubeVideosByPlaylist(playlistId):
	if playlistId.startswith('https://www'):
		#nextpage
		u_url=playlistId
	else:
		u_url='https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=25&playlistId=%s&key=%s'%(playlistId,apikey)
	videos=getJson(u_url)
	return prepareYoutubeVideoItems(videos,u_url)

def getYoutubeVideosPopular(today=False):
	if not today:
		u_url='https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=25&order=viewCount&type=video&key=%s'%(apikey)
	else:
		import datetime
		t=datetime.datetime.utcnow()-datetime.timedelta(days=1)
		yesterday=t.strftime("%Y-%m-%dT%H:%M:%SZ")
		u_url='https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=25&order=viewCount&type=video&key=%s&publishedAfter=%s'%(apikey,yesterday)
	videos=getJson(u_url)
	return prepareYoutubeVideoItems(videos,u_url)




def prepareYoutubeVideoItems(videos,urlUsed):
	#print 'urlUsed',urlUsed
	if 'nextPageToken' in videos:
		nextItem=videos["nextPageToken"]
	else:
		nextItem=None
	ret=[]
	for playlist_item in videos["items"]:
		title = playlist_item["snippet"]["title"]
		#print 'urlUsed',urlUsed
		if not 'search?part=snippet' in urlUsed:
			video_id = playlist_item["snippet"]["resourceId"]["videoId"]
		else:
			video_id =playlist_item["id"]["videoId"]
		if not title=='Private video':
			imgurl=''
			try:
				imgurl= playlist_item["snippet"]["thumbnails"]["high"]["url"]
			except: pass
			if imgurl=='':
				try:
					imgurl= playlist_item["snippet"]["thumbnails"]["default"]["url"]
				except: pass
		#print "%s (%s)" % (title, video_id)
			ret.append([title,video_id,imgurl])
	nextUrl=None
	if nextItem:
		if not '&pageToken' in urlUsed:
			nextUrl=urlUsed+'&pageToken='+nextItem
		else:
			nextUrl=urlUsed.split('&pageToken=')[0]+'&pageToken='+nextItem
	return ret,nextUrl;

def AddStreams():
	match=getStreams();
	#print 'match',match
	match=sorted(match,key=lambda x:x[0].lower())
	cstream='<channels>'
	infostream='<streamingInfos>'
	#print 'match',match
	for cname in match:
		if 'hdarabic' in cname[1]:
			chName=Colored(cname[0],'one',False);
			chUrl = cname[1]
			if not 'http:' in cname[2]:
				imageUrl = 'http://www.hdarabic.com/./images/'+cname[2]+'.jpg'
			else:
				imageUrl=cname[2]
			#print imageUrl
			#print chName
			addDir(chName ,chUrl ,10,imageUrl, False,isItFolder=False)		#name,url,mode,icon
		else:
			chName=Colored(cname[1],'two',False);
			chUrl = cname[0]
			imageUrl = 'http://www.teledunet.com/tv_/icones/%s.jpg'%cname[0]
			#print imageUrl
			#print chName
			addDir(chName ,chUrl ,11,imageUrl, False,isItFolder=False)		#name,url,mode,icon#<assignedcategory></assignedcategory>
			cstream+='<channel><id>%s</id><cname>%s</cname><imageurl>%s</imageurl><enabled>True</enabled></channel>'%(chUrl,cname[1],imageUrl)
			infostream+='<streaminginfo><id>%s</id><url>%s</url></streaminginfo>'%(chUrl,chUrl)
	cstream+='</channels>'
	infostream+='</streamingInfos>'
	#print cstream
	#print infostream
	return
	
def PlayStream(url, name, mode):

	if mode==10:
		req = urllib2.Request(url)
		req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		match =re.findall('file: "rtmp([^"]*)', link)

		rtmpLink=match[0]
		#rtmpLink='://192.95.32.7:1935/live/dubai_sport?user=MjA5N2Q3YjA2M2Q2ZjhiNWNjODAzYWJmM2RmNzU4YWE=&pass=fc9226bd032346a2deab1f903652229b'
		liveLink="rtmp%s app=live/ swfUrl=http://www.hdarabic.com/jwplayer.flash.swf pageUrl=http://www.hdarabic.com live=1 timeout=15"%rtmpLink
	else:
		newURL='http://www.teledunet.com/tv_/?channel=%s&no_pub'%url
		req = urllib2.Request(newURL)
		req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
		req.add_header('Referer',newURL)

		response = urllib2.urlopen(req)
		link=response.read()
		response.close()
		match =re.findall('time_player=(.*?);', link)
		match=str(long(float(match[0])))

		liveLink='rtmp://5.135.134.110:1935/teledunet playpath=%s swfUrl=http://www.teledunet.com/tv_/player.swf?id0=%s&skin=bekle/bekle.xml&channel=%s  pageUrl=http://www.teledunet.com/tv_/?channel=%s&no_pub live=1  timeout=15'%(url,match,url,url)
		
	#print 'liveLink',liveLink

	listitem = xbmcgui.ListItem( label = str(name), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=liveLink )
	xbmc.Player().play( liveLink,listitem)


def getSourceAndStreamInfo(channelId, returnOnFirst,pDialog):
	try:
		ret=[]
		#Ssoup=getSoup('Sources.xml');
		sourcesXml=getEtreeFromFile('Sources.xml');
		orderlist={}
		for n in range(6):
			val=selfAddon.getSetting( "order"+str(n+1) )
			if val and not val=="":
				orderlist[val]=n*100
		#print orderlist
		#print 'sources',sources
		num=0
		pDialog.update(30, 'Looping on sources')
		sources=sourcesXml.findall('source')
		for source in sources:
			num+=1
			pDialog.update(30+(num*70)/len(sources) , 'Checking ..'+source.findtext('sname'))
			try:
				#print 'source....................',source
				xmlfile = source.findtext('urlfile')
				isEnabled = source.findtext('enabled').lower()
				sid = source.findtext('id')
				sname = source.findtext('sname')
				#print 'sid',sid,xmlfile
				isAbSolutePath=False
				if sname=="Local":
					#
					isAbSolutePath=True
					isEnabled="false"
					filename=selfAddon.getSetting( "localstreampath" ).decode('utf-8')
					if filename and len(filename)>0:
						isEnabled="true"
						xmlfile=filename
				settingname="is"+sname.replace('.','')+"SourceDisabled"
				settingDisabled=selfAddon.getSetting(settingname)  
				#print 'settingDisabled',settingDisabled
				if isEnabled=="true" and not settingDisabled=="true":
					#print 'source is enabled',sid
					#csoup=getSoup(xmlfile,isAbSolutePath);
					streamingxml=getEtreeFromFile(xmlfile,isAbSolutePath);
					#ccsoup = csoup("streaminginfo")
					#print 'csoup',csoup,channelId
					#print csoup 
					#sInfo=csoup.findAll('streaminginfo',{'cname':re.compile("^"+channelId+"$", re.I)})
					#sInfo=csoup.findAll('streaminginfo',{'cname':channelId})
					#sInfo=csoup.findAll('streaminginfo',{'cname':channelId})
					sInfos=streamingxml.findall('streaminginfo')
					sInfo=[]
					for inf in sInfos:
						if inf.findtext('cname').lower()==channelId.lower():
							sInfo.append(inf)
					name_find=sname
					if name_find in orderlist:
						order= orderlist[name_find]
					else:
						order=1000
					order+=num
					if not sInfo==None and len(sInfo)>0:
						#print 'sInfo...................',len(sInfo)
						
						for single in sInfo:
							ret.append([source,single,order])
						#if returnOnFirst:
						#	break;
			except:
				traceback.print_exc(file=sys.stdout)
				pass
	except:
		traceback.print_exc(file=sys.stdout)
		pass
	#print 'unsorted ret',ret
	return sorted(ret,key=lambda x:x[2])

def selectSource(sources):
    if 1==1 or len(sources) > 1:
        #print 'total sources',len(sources)
        dialog = xbmcgui.Dialog()
        titles = []
        for source in sources:
            (s,i,o) =source
            #print 'i',i.id,i
            if s.findtext('id')=="generic":
                try:
                    print 'trying generic name'
                    titles.append(s.findtext('sname')+': '+i.find('item').findtext('title'))
                    print 'trying generic name end '
                except:
                    titles.append(s.findtext('sname'))
            else:
                titles.append(s.findtext('sname'))
        index = dialog.select('Choose your stream', titles)
        if index > -1:
            return sources[index]
        else:
            return False

def PlayCommunityStream(channelId, name, mode):
	try:
		#print 'PlayCommunityStream'
		xbmcplugin.endOfDirectory(int(sys.argv[1]))
		pDialog = xbmcgui.DialogProgress()
		ret = pDialog.create('XBMC', 'Finding available resources...')
		#print 'channelId',channelId
		playFirst=selfAddon.getSetting( "playFirstChannel" )
		if playFirst==None or playFirst=="" or playFirst=="false":
			playFirst=False
		else:
			playFirst=True
		playFirst=bool(playFirst)
		pDialog.update(20, 'Finding sources..')
		providers=getSourceAndStreamInfo(channelId,playFirst,pDialog)
		if len(providers)==0:
			pDialog.close()
			time = 2000  #in miliseconds
			line1="No sources found"
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))
			return
		pDialog.update(30, 'Processing sources..')
		pDialog.close()
		#source=providers[""]

		
		enforceSourceSelection=False
		#print 'playFirst',playFirst
		done_playing=False
		while not done_playing:
			#print 'trying again',enforceSourceSelection
			ret = pDialog.create('XBMC', 'Trying to play the source')
			#print 'dialogue creation'
			done_playing=True
			if enforceSourceSelection or (len (providers)>1 and not playFirst):
				#print 'select sources'
				selectedprovider=selectSource(providers)
				if not selectedprovider:
					return
			else:
				selectedprovider=providers[0]
				enforceSourceSelection=True
			#print 'picking source'
			(source,sInfo,order)=selectedprovider #pick first one
			#print source

			processor = source.findtext('processor')
			sourcename = source.findtext('sname')

			if communityStreamPath not in sys.path:
				sys.path.append(communityStreamPath)
			#print processor
		
		
			#from importlib import import_module
			processorObject=import_module(processor.replace('.py',''))
		
		
			pDialog.update(60, 'Trying to play..')
			pDialog.close()
			sinfoSoup= BeautifulSOAP(etree.tostring(sInfo), convertEntities=BeautifulStoneSoup.XML_ENTITIES)
			done_playing=processorObject.PlayStream(source,sinfoSoup,name,channelId)
			#print 'done_playing',done_playing
			if not done_playing:
				time = 2000  #in miliseconds
				line1="Failed playing from "+sourcename
				xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))
			#print 'donexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
		return 
	except:
		traceback.print_exc(file=sys.stdout)

def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]
	
def PlayShowLink ( url ): 
#	url = tabURL.replace('%s',channelName);

	line1 = "Finding stream"
	time = 500  #in miliseconds
	line1 = "Playing video Link"
	xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))

	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
#	print url


	#print "PlayLINK"
	playURL= match =re.findall('id  : "(.*?)",\s*pricingPlanId  : "(.*?)"', link)
	videoID=match[0][0]# check if not found then try other methods
	paymentID=match[0][1]
	playlistURL=getMainUrl()+"/arContent/getPlayerContent-param-.id-%s.type-player.pricingPlanId-%s.html" % ( videoID,paymentID)
	req = urllib2.Request(playlistURL)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	jsonData=json.loads(link)
	#print jsonData;
	url=jsonData["data"]["url"]
	#print url
	
	
	defaultCDN="Default"
	defaultCDN=selfAddon.getSetting( "DefaultCDN" )
	
	#print 'default CDN',defaultCDN,cdnType
	changeCDN=""
	
	#print 'tesing if cdn change is rquired'
	if cdnType=="l3" or (cdnType=="" and defaultCDN=="l3"):
		changeCDN="l3"
	elif cdnType=="xdn" or (cdnType=="" and defaultCDN=="xdn"):
		changeCDN="xdn"
	elif cdnType=="ak" or (cdnType=="" and defaultCDN=="ak"):
		changeCDN="ak"
	#print 'changeCDN',changeCDN
	if len(changeCDN)>0:
		#print 'Changing CDN based on critertia',changeCDN
		#http://l3md.shahid.net/web/mediaDelivery/media/12af648b9ffe4423a64e8ab8c0100701.m3u8?cdn=l3
		#print 'url received',url
		playURL= re.findall('\/media\/(.*?)\.', url)
		url="http://%smd.shahid.net/web/mediaDelivery/media/%s.m3u8?cdn=%s" % (changeCDN,playURL[0],changeCDN)
		
		#print 'new url',url
		line1 = "Using the CDN %s" % changeCDN
		time = 2000  #in miliseconds
		xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))

		
	cName=name
	listitem = xbmcgui.ListItem( label = str(cName), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=url )
	#print "playing stream name: " + str(cName) 
	listitem.setInfo( type="video", infoLabels={ "Title": cName, "Path" : url } )
	listitem.setInfo( type="video", infoLabels={ "Title": cName, "Plot" : cName, "TVShowTitle": cName } )
	#print 'playurl',url
	xbmc.Player().play( url,listitem)
	#print 'ol..'
	return

def addToMyChannels(cname):
	try:
		fileName=os.path.join(profile_path, 'MyChannels.xml')
		print fileName
		MyChannelList=getSoup(fileName,True)
	except: MyChannelList=None
	if not MyChannelList:
		MyChannelList= BeautifulSOAP('<channels></channels>')
	
	val=MyChannelList.find("channel",{"cname":cname})
	print 'val is ',val
	if not val:
		channeltag = Tag(MyChannelList, "channel")
		channeltag['cname']=cname
		#cnametag = Tag(MyChannelList, "cname")
		#ctext = NavigableString(cname)
		#cnametag.insert(0, ctext)
		#channeltag.insert(0, cnametag)
		MyChannelList.channels.insert(0, channeltag)
		print MyChannelList.prettify()

		with open(fileName, "wb") as filewriter:
			filewriter.write(str(MyChannelList))

def removeFromMyChannels(cname):
	try:
		fileName=os.path.join(profile_path, 'MyChannels.xml')
		print fileName
		MyChannelList=getSoup(fileName,True)
	except: return
	if not MyChannelList:
		return
	
	val=MyChannelList.find("channel",{"cname":cname})
	if val:
		print 'val to be deleted',val
		val.extract()

		with open(fileName, "wb") as filewriter:
			filewriter.write(str(MyChannelList))

def addCommunityCats():
	#soup=getSoup('Categories.xml');
	cats=getEtreeFromFile('Categories.xml');
#	print cats 

	addDir('My Channels' ,'My Channels' ,15,addonArt+'/mychannels.png', False,isItFolder=True)		#name,url,mode,icon

	for cat in cats.findall('category'):
		chName=cat.findtext('catname')
		chUrl = cat.findtext('id')
		imageUrl = cat.findtext('imageurl')
		addDir(chName ,chUrl ,15,imageUrl, False,isItFolder=True)		#name,url,mode,icon
	return

def getCommunityChannels(catType):
	#soup=getSoup('Channels.xml');#changetoEtree
	Channelsxml=getEtreeFromFile('Channels.xml')
	#channels=soup('channel')
	retVal=[]
		
	#for channel in channels:
	searchCall='channel'
	#if not catType=="all":
	searchCall='.//category'
	print searchCall
	MyChannelList=None
	if catType=="My Channels":
		try:
			fileName=os.path.join(profile_path, 'MyChannels.xml')
			print fileName
			MyChannelList=getSoup(fileName,True)
			print MyChannelList
		except: MyChannelList=None
		
	for channel in Channelsxml.findall('channel'):
		#print channel
		chName=channel.findtext('cname')
		if 1==1:
			if not catType=="all":
				exists=False
				if not catType=="My Channels":
					supportCats= channel.findall(searchCall)
					if len(supportCats)==0:
						continue
					
					for c in supportCats:
						if c.text.lower()==catType.lower():
							exists=True
							break
				else:
					#check if channel exists in file
					if MyChannelList:
						val=MyChannelList.find("channel",{"cname":chName})
						if val:
							exists=True
				if not exists:
					continue
			

		
		#chUrl = channel.id.text
		imageUrl =channel.findtext('imageurl')
 		retVal.append([chName,chName,imageUrl])
	return retVal
	

def addCommunityChannels(catType):
	channels=getCommunityChannels(catType)
	channels=sorted(channels,key=lambda x:x[1].lower())
	for channel in channels:
		chName=channel[1]
		chUrl = channel[0]
		imageUrl = channel[2]
		addRemoveMyChannel=not catType=="My Channels"
 		addDir(chName ,chUrl ,16,imageUrl, False,isItFolder=False,AddRemoveMyChannels=addRemoveMyChannel)		#name,url,mode,icon
	return

def getEtreeFromFile(fileName, isabsolutePath=False):
	strpath=os.path.join(communityStreamPath, fileName)
	if isabsolutePath:
		strpath=fileName
	data = open(strpath, "r").read()
	return getETreeFromString(data)

#obselete
def getSoup(fileName, isabsolutePath=False):
	strpath=os.path.join(communityStreamPath, fileName)
	if isabsolutePath:
		strpath=fileName
	data = open(strpath, "r").read()
	return BeautifulSOAP(data)#, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
	#return BeautifulStoneSoup(data,convertEntities=BeautifulStoneSoup.XML_ENTITIES);

def getETreeFromUrl(video_url):
	req = urllib2.Request(video_url)
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	data=response.read()
	response.close()

	return getETreeFromString(data)
	#return BeautifulSOAP(data)
def getETreeFromString(str):
	return etree.fromstring(str)
	
def getStreams():
	defaultStream="All"
	defaultStream=selfAddon.getSetting( "DefaultStream" )
	if defaultStream=="": defaultStream="All"
	hdArab= [('Al Jazeera','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Al Jazeera Mubasher','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Al Jazeera Egypt','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Al Jazeera Documentary','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Al Jazeera English','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Al Jazeera America','http://www.hdarabic.com/aljazeera.php','jazeera'),
	('Hurra Iraq','http://www.hdarabic.com/alhurra_iraq.php','hurra_iraq'),
	('Al Iraqia','http://www.hdarabic.com/aliraqiya.php','iraqiay'),
	('SemSem','http://www.hdarabic.com/semsem.php','semsem_tv'),
	('Al Arabiya','http://www.hdarabic.com/alarabiya.php','alarabiya'),
	('France 24','http://www.hdarabic.com/f24.php','f24'), 
	('France 24 English','http://www.hdarabic.com/f24.php','f24'),
	('France 24 France','http://www.hdarabic.com/f24.php','f24'),
	('Al hiwar','http://www.hdarabic.com/alhiwar.php','alhiwar'),
	('Skynews','http://www.hdarabic.com/skynews.php','skynews'),
	('Skynews English','http://www.hdarabic.com/skynews.php','skynews'),
	('BBC Arabic','http://www.hdarabic.com/bbc.php','bbc'),
	('Al mayadeen','http://www.hdarabic.com/almayaden.php','almayaden'),
	('TAHA','http://www.hdarabic.com/taha.php','taha'),
	('National Wild','http://www.hdarabic.com/national_wild.php','national_wild'),
	('National Geographic Abu','http://www.hdarabic.com/national.php','ng'),
	('HODHOD','http://www.hdarabic.com/hod_hod.php','hod_hod'),
	('Karamesh','http://www.hdarabic.com/karamesh.php','karamesh'),
	('Al Jazeera Children','http://www.hdarabic.com/jazeerakids.php','jsckids'),
	('Qatar','http://www.hdarabic.com/qatar.php','qatar'),
	('Tunisia 1','http://www.hdarabic.com/tunis1.php','tunisia1'),
	('Tunisia 2','http://www.hdarabic.com/tunisia_2.php','tv_tunisia2'),
	('Sama Dubai','http://www.hdarabic.com/sama_dubai.php','Sama-dubai'),
	('B4U plus','http://www.hdarabic.com/b4u+.php','b4u+'),
	('B4U Aflam','http://www.hdarabic.com/b4u_aflam.php','b4u_aflam'),
	('Saudi Sport','http://www.hdarabic.com/saudi_sport.php','saudi_sport'),
	('Dubai Sport','http://www.hdarabic.com/dubai_sport.php','dubai-sport'),
	('Dubai Sport 3','http://www.hdarabic.com/dubai_sport_3.php','dubai-sport'),
	('Dubai Racing','http://www.hdarabic.com/dubai_racing.php','dubai_racing'),
	('Oman','http://www.hdarabic.com/oman.php','oman_tv'),
	('Dubai','http://www.hdarabic.com/dubai.php','dubai'),
	('Play Hekayat','http://www.hdarabic.com/play_hekayat.php','play_hekayat'),
	('Watan','http://www.hdarabic.com/play_hekayat.php','watan'),
	('Watan Plus','http://www.hdarabic.com/play_hekayat.php','watan_plus'),
	('Watan ghanawi','http://www.hdarabic.com/play_hekayat.php','watan_ghanawi'),
	('Fox Movie','http://www.hdarabic.com/fox_movie.php','fox_movies'),
	('ART Aflam 1','http://www.hdarabic.com/art_1.php','art1'),
	('ART Aflam 2','http://www.hdarabic.com/art2.php','art_aflam2'),
	('ART Cinema ','http://www.hdarabic.com/art.php','art'),
	('ART Hekayat','http://www.hdarabic.com/art_hekayat.php','art_hekayat'),
	('ART Hekayat 2','http://www.hdarabic.com/art_hekayat_2.php','art_hekayat_2'),
	('Melody Arabia','http://www.hdarabic.com/melody.php','melodytv'),
	('Melody Aflam','http://www.hdarabic.com/melody_aflam.php','melodytv'),
	('Melody Classic','http://www.hdarabic.com/melody_classic.php','melodytv'),
	('Melody Hits','http://www.hdarabic.com/melody_hits.php','melodytv'),
	('Melody Drama','http://www.hdarabic.com/melody_drama.php','melodytv'),
	('Mehwar','http://www.hdarabic.com/mehwar.php','mehwar'),
	('Mehwar 2','http://www.hdarabic.com/mehwar2.php','mehwar2'),
	('Talaki','http://www.hdarabic.com/mehwar2.php','talaki'),
	('Syria News','http://www.hdarabic.com/mehwar2.php','syria_news'),
	('Oscar Drama','http://www.hdarabic.com/oscar_drama.php','oscar_drama'),
	('Cima','http://www.hdarabic.com/cima.php','cima'),
	('Cairo Cinema','http://www.hdarabic.com/cairo_cinema.php','cairo_cinema'),
	('Cairo Film','http://www.hdarabic.com/cairo_film.php','cairo_film'),
	('Cairo Drama','http://www.hdarabic.com/cairo_drama.php','cairo_drama'),
	('IFilm Arabic','http://www.hdarabic.com/cairo_drama.php','ifilm'),
	('IFilm English','http://www.hdarabic.com/cairo_drama.php','ifilm'),
	('IFilm Farsi','http://www.hdarabic.com/cairo_drama.php','ifilm'),
	('Gladiator','http://www.hdarabic.com/gladiator.php','gladiator'),
	('ESC1','http://www.hdarabic.com/esc1.php','al_masriya_eg'),
	('ESC2','http://www.hdarabic.com/esc2.php','masriaesc2'),
	('Bein Sport 1','http://www.hdarabic.com/jsc1.php','bein_sport'),
	('Bein Sport 2','http://www.hdarabic.com/jsc2.php','bein_sport'),
	('Bein Sport 3','http://www.hdarabic.com/jsc3.php','bein_sport'),
	('Bein Sport 4','http://www.hdarabic.com/jsc4.php','bein_sport'),
	('Bein Sport 5','http://www.hdarabic.com/jsc5.php','bein_sport'),
	('Bein Sport 6','http://www.hdarabic.com/jsc6.php','bein_sport'),
	('Bein Sport 7','http://www.hdarabic.com/jsc7.php','bein_sport'),
	('Bein Sport 8','http://www.hdarabic.com/jsc8.php','bein_sport'),
	('Bein Sport 11','http://www.hdarabic.com/jsc9.php','bein_sport'),
	('Bein Sport 12','http://www.hdarabic.com/jsc10.php','bein_sport'),
	('Panorama Film','http://www.hdarabic.com/panorama_film.php','panorama_film'),
	('TF1','http://www.hdarabic.com/tf1.php','tf1'),
	('M6 Boutique','http://www.hdarabic.com/m6_boutique.php','m6'),
	('TV5','http://www.hdarabic.com/tv5.php','tv5_monde_europe'),
	('Guilli','http://www.hdarabic.com/guilli.php','guilli'),
	('Libya','http://www.hdarabic.com/libya.php','libya'),
	('Assema','http://www.hdarabic.com/assema.php','assema'),
	('Libya Awalan','http://www.hdarabic.com/libya_awalan.php','libya_awalan'),
	('RTM Tamazight','http://www.hdarabic.com/tamazight.php','tamazight'),
	('Al maghribiya','http://www.hdarabic.com/maghribiya.php','maghribiya'),
	('Sadissa','http://www.hdarabic.com/sadissa.php','sadisa'),
	('A3','http://www.hdarabic.com/a3.php','a3'),
	('Algerie 4','http://www.hdarabic.com/algerie_4.php','algerie_4'),
	('Algerie 5','http://www.hdarabic.com/algerie5.php','algerie5'),
	('Al Nahar Algerie','http://www.hdarabic.com/nahar_algerie.php','nahar_algerie'),
	('Chorouk TV','http://www.hdarabic.com/chorouk.php','chorouk'),
	('El Beit Beitak','http://www.hdarabic.com/beitak.php','beitak'),
	('Insen','http://www.hdarabic.com/insen.php','insen'),
	('Nesma','http://www.hdarabic.com/nesma.php','rouge'),
	('Tounsiya','http://www.hdarabic.com/tounsiya.php','tounsiya'),
	('Aghanina','http://www.hdarabic.com/aghanina.php','aghanina'),
	('Nojoom','http://www.hdarabic.com/nojoom.php','nojoom'),
	('Funoon','http://www.hdarabic.com/funoon.php','funoon'),
	('Mazazik','http://www.hdarabic.com/mazazik.php','mazazik'),
	('Mazzika','http://www.hdarabic.com/mazzika.php','logo-mazzika'),
	('Power Turk','http://www.hdarabic.com/power_turk.php','power_turk'),
	('Al Haneen','http://www.hdarabic.com/alhaneen.php','alhaneen'),
	('Heya','http://www.hdarabic.com/heya.php','heya'),
	('CBC','http://www.hdarabic.com/cbc.php','cbc'),
	('CBC Extra','http://www.hdarabic.com/cbc.php','cbc_extra'),
	('CBC Drama','http://www.hdarabic.com/cbc_drama.php','cbc_drama'),
	('CBC Sofra','http://www.hdarabic.com/cbc_sofra.php','cbc_sofra'),
	('Al Hayat 2 TV ','http://www.hdarabic.com/hayat_2.php','hayat_2'),
	('Top Movies ','http://www.hdarabic.com/top_movie.php','top_movies_eg'),
	('Dream 1','http://www.hdarabic.com/dream1.php','dream1'),
	('Nile Comedy','http://www.hdarabic.com/nile_comedy.php','nile_comedy'),
	('Nile News','http://www.hdarabic.com/nile_news.php','nile_news'),
	('Nile Family','http://www.hdarabic.com/nile_family.php','nile_family'),
	('Nile Education','http://www.hdarabic.com/nile_educ.php','nile_educational'),
	('Rotana Cinema','http://www.hdarabic.com/rotana_cinema.php','rotana_cinema'),
	('Rotana Clip','http://www.hdarabic.com/rotana_clip.php','rotana_clip'),
	('Rotana Classic','http://www.hdarabic.com/rotana_classic.php','rotana_classic'),
	('Rotana Khalijia','http://www.hdarabic.com/rotana_khalijiya.php','rotana-khalijia'),
	('ANB','http://www.hdarabic.com/anb.php','anb'),
	('MTV Lebanon','http://www.hdarabic.com/mtvlebanon.php','mtv1'),
	('Arabica ','http://www.hdarabic.com/arabica.php','arabica-tv'),
	('MTV Arabia','http://www.hdarabic.com/mtv_arabia.php','mtv_arabia'),
	('MBC','http://www.hdarabic.com/mbc.php','mbc'),
	('MBC 2','http://www.hdarabic.com/mbc2.php','mbc2'),
	('MBC 3','http://www.hdarabic.com/mbc3.php','mbc3'),
	('MBC Action','http://www.hdarabic.com/mbc_action.php','mbc_action'),
	('MBC Max','http://www.hdarabic.com/mbc_max.php','mbc_max'),
	('MBC Drama','http://www.hdarabic.com/mbc_drama.php','mbc_drama'),
	('MBC Masr','http://www.hdarabic.com/mbc_masr.php','mbc_masr'),
	('MBC Masr Drama','http://www.hdarabic.com/mbc_masr_drama.php','mbc_masr_drama'),
	('MBC Bollywood','http://www.hdarabic.com/mbc_bollywood.php','mbc_bollywoodl'),
	('Wanasah','http://www.hdarabic.com/wanasah.php','wanasah'),
	('Al Nahar','http://www.hdarabic.com/nahar_egy.php','Nahar-TV'),
	('Nahar +2','http://www.hdarabic.com/nahar_egy.php','nahar+2'),
	('Nahar Sport','http://www.hdarabic.com/nahar_sport.php','al_nahar_sport'),
	('LBC Europe','http://www.hdarabic.com/lbc_europe.php','lbc'),
	('Tele Liban','http://www.hdarabic.com/teleliban.php','teleliban'),
	('Syria ','http://www.hdarabic.com/syria.php','syria'),
	('Sama Syria ','http://www.hdarabic.com/sama_syria.php','sama_syria'),
	('MBC Maghreb','http://www.hdarabic.com/mbc_maghreb.php','mbc_maghreb'),
	('Abu Dhabi Sport','http://www.hdarabic.com/abu_dhabi_sport.php','abu_dhabi_sporti'),
	('Abu Dhabi','http://www.hdarabic.com/abu_dhabi_sport.php','abudhabi'),
	('Abu Dhabi Emarate','http://www.hdarabic.com/abu_emarat.php','abu_dhabi_al_emarat'),
	('Bahrain','http://www.hdarabic.com/bahrein.php','bahrain_tv'),
	('Kuwait','http://www.hdarabic.com/kowait1.php','kuwait'),
	('Kuwait 2','http://www.hdarabic.com/kowait2.php','kuwait2'),
	('Kuwait 3','http://www.hdarabic.com/kowait3.php','kuwait3'),
	('Kuwait 4','http://www.hdarabic.com/kowait4.php','kuwait4'),
	('Kuwait 5','http://www.hdarabic.com/kowait5.php','kuwait5'),
	('Kuwait 6','http://www.hdarabic.com/kowait6.php','kuwait6'),
	('LBC','http://www.hdarabic.com/lbc.php','lbc'),
	('LBC Drama','http://www.hdarabic.com/lbc_drama.php','lbc_drama'),
	('LDC','http://www.hdarabic.com/ldc.php','ldc'),
	('AL Sharqia','http://www.hdarabic.com/sharqia.php','sharqia'),
	('Al Sharqia News','http://www.hdarabic.com/sharqia_news.php','al_sharqiya_news'),
	('Orient News','http://www.hdarabic.com/orient_news.php','orientnews'),
	('Al Alam','http://www.hdarabic.com/alalam.php','alalam'),
	('Nabaa ','http://www.hdarabic.com/nabaa.php','nabaa_tv_sa'),
	('Baghdadia ','http://www.hdarabic.com/baghdad.php','al-baghdadia'),
	('Baghdadia 2','http://www.hdarabic.com/baghdad2.php','baghdad2'),
	('Kaifa','http://www.hdarabic.com/kaifa.php','kaifa'),
	('Suna Nabawiya','http://www.hdarabic.com/sunah.php','sunah'),
	('Iqrae','http://www.hdarabic.com/iqra.php','iqra'),
	('Rahma','http://www.hdarabic.com/rahma.php','rahma'),
	('Al Maaref','http://www.hdarabic.com/almaaref.php','almaaref'),
	('Sirat','http://www.hdarabic.com/sirat.php','sirat'),
	('Wesal TV','http://www.hdarabic.com/wesal.php','wesal_tv'),
	('Al Majd Massah','http://www.hdarabic.com/majd_massah.php','al_majd'),
	('Al Majd Nature','http://www.hdarabic.com/majd_nature.php','al_majd'),
	('Al Afassi','http://www.hdarabic.com/afasi.php','afasi'),
	('Al AAN','http://www.hdarabic.com/alan.php','al_aan_tv'),
	('Al Ressala','http://www.hdarabic.com/resala.php','alressala'),
	('Ctv Coptic','http://www.hdarabic.com/ctv_coptic.php','ctv_eg'),
	('Sat7','http://www.hdarabic.com/sat7.php','sat7'),
	('Sat7 Kids','http://www.hdarabic.com/sat7_kids.php','sat7_kids'),
	('Aghapy','http://www.hdarabic.com/aghapy.php','aghapy_tv'),
	('Noursat','http://www.hdarabic.com/nour_sat.php','nour_sat'),
	('Miracle','http://www.hdarabic.com/miracle.php','miracle'),
	('Royali Somali','http://www.hdarabic.com/royali_somali.php','royali_somali'),
	('Somali Channel','http://www.hdarabic.com/somali_channel.php','somali_channel'),
	('Cartoon Network','http://www.hdarabic.com/cartoon.php','cartoon_network'),
	('Baraem','http://www.hdarabic.com/baraem.php','baraem_95x64'),
	('Space Power','http://www.hdarabic.com/space_power.php','space_power'),
	('Majd Kids','http://www.hdarabic.com/majd_kids.php','majd_kids'),
	('Majd Kids 2','http://www.hdarabic.com/majd_kids_2.php','majd_kids'),
	('Majd Roda','http://www.hdarabic.com/majd_roda.php','almajd'),
	('Majd Taghrid','http://www.hdarabic.com/majd_taghrid.php','almajd'),
	('Toyor Al Janah 1','http://www.hdarabic.com/toyorjana1.php','toyor'),
	('Toyor Baby','http://www.hdarabic.com/toyorbaby.php','baby'),
	('Ajyal','http://www.hdarabic.com/ajyal.php','ajyal'),
	('ANN','http://www.hdarabic.com/ann.php','ann_95x44'),
	('Al Magharibiya','http://www.hdarabic.com/magharibia.php','http://tv.webactu-webtv.com/algerie1/magharibia.png')]
	
	if defaultStream=="hdarabic.com": return hdArab
	
	req = urllib2.Request('http://www.teledunet.com/')
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	match =re.findall('set_favoris\(\'(.*?)\',\'(.*?)\'\s?(.)', link)
	if defaultStream=="teledunet.com": return match
	
	return match+hdArab
	
	


	
#print "i am here"
params=get_params()
url=None
name=None
mode=None
linkType=None
pageNumber=None
AddRemoveMyChannels=None
try:
	url=urllib.unquote_plus(params["url"])
except:
	pass
try:
	name=urllib.unquote_plus(params["name"])
except:
	pass
try:
	mode=int(params["mode"])
except:
	pass

try:
	pageNumber=params["pagenum"]
except:
	pageNumber="";

args = cgi.parse_qs(sys.argv[2][1:])
cdnType=''
try:
	cdnType=args.get('cdnType', '')[0]
except:
	pass

addIconForPlaylist=""
try:
	addIconForPlaylist=args.get('addIconForPlaylist', '')[0]
except:
	pass


AddRemoveMyChannels=None
try:
	AddRemoveMyChannels=args.get('AddRemoveMyChannels', None)[0]
except:
	pass

	



print 	mode,pageNumber

try:
	if not AddRemoveMyChannels==None:
		if AddRemoveMyChannels=="add":
			addToMyChannels(url)
			line1 = 'Channel has been added to My Channels list'
			time = 2000  #in miliseconds
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))
			mode=-1
		else:
			removeFromMyChannels(url)
			line1 = 'Channel has been removed from My Channels list'
			time = 2000  #in miliseconds
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, time, __icon__))
			mode=15
			url="My Channels"
			print mode
	if mode==None or url==None or len(url)<1:
		print "InAddTypes"
		checkAndRefresh()        
		Addtypes()

	elif mode==2:
		print "Ent url is "+name,url
		AddChannels(url)

	elif mode==3 or mode==6:
		print "Ent url is "+url
		AddSeries(url,pageNumber)

	elif mode==4 or mode==7:
		print "Play url is "+url
		AddEnteries(url,pageNumber)

	elif mode==5:
		PlayShowLink(url)
	elif mode==8:
		print "Play url is "+url,mode
		ShowSettings(url)
	elif mode==9:
		print "Play url is "+url,mode
		AddStreams();
	elif mode==10 or mode==11:
		print "Play url is "+url,mode
		PlayStream(url,name,mode);
	elif mode==14: #add communutycats
		print "Play url is "+url,mode
		addCommunityCats();
	elif mode==15: #add communutycats
		print "Play url is "+url,mode
		addCommunityChannels(url);
	elif mode==16: #add communutycats
		print "PlayCommunityStream Play url is "+url,mode
		PlayCommunityStream(url,name,mode);	
	elif mode==17: #add communutycats
		print "RefreshResources Play url is "+url,mode
		RefreshResources();
	elif mode==18: #
		print "youtube url is "+url,mode
		AddYoutubeSources(url)
	elif mode==19: #
		print "youtube url is "+url,mode
		AddYoutubeLanding(url)
	elif mode==20: #add communutycats
		print "youtube url is "+url,mode
		AddYoutubeVideosByChannelID(url,addIconForPlaylist);	
	elif mode==21: #add communutycats
		print "play youtube url is "+url,mode
		PlayYoutube(url);	
	elif mode==22: #add communutycats
		print "play youtube url is "+url,mode
		AddYoutubePlaylists(url);	
	elif mode==23: #add communutycats
		print "play youtube url is "+url,mode
		AddYoutubeVideosByPlaylist(url);	
except:
	print 'somethingwrong'
	traceback.print_exc(file=sys.stdout)

try:
	if (not mode==None) and mode>1:
		view_mode_id = get_view_mode_id('thumbnail')
		if view_mode_id is not None:
			print 'view_mode_id',view_mode_id
			xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)
except: pass
if not ( mode==5 or mode==10 or mode==8 or mode==11 or mode==16 or mode==17):
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


########NEW FILE########
__FILENAME__ = CustomPlayer
# -*- coding: utf-8 -*-
import xbmc


class MyXBMCPlayer(xbmc.Player):
    def __init__( self, *args, **kwargs ):
        self.is_active = True
        self.urlplayed = False
        print "#XBMCPlayer#"
    
    def onPlayBackPaused( self ):
        xbmc.log("#Im paused#")
        
    def onPlayBackResumed( self ):
        xbmc.log("#Im Resumed #")
        
    def onPlayBackStarted( self ):
        print "#Playback Started#"
        try:
            print "#Im playing :: " + self.getPlayingFile()
        except:
            print "#I failed get what Im playing#"
        self.urlplayed = True
            
    def onPlayBackEnded( self ):
        print "#Playback Ended#"
        self.is_active = False
        
    def onPlayBackStopped( self ):
        print "## Playback Stopped ##"
        self.is_active = False


########NEW FILE########
__FILENAME__ = genericPlayer
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin
import urllib2,urllib,cgi, re
import HTMLParser
import xbmcaddon
import json
import traceback
import os
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
import time
import sys
import  CustomPlayer

__addon__       = xbmcaddon.Addon()
__addonname__   = __addon__.getAddonInfo('name')
__icon__        = __addon__.getAddonInfo('icon')
addon_id = 'plugin.video.shahidmbcnet'
selfAddon = xbmcaddon.Addon(id=addon_id)
addonPath = xbmcaddon.Addon().getAddonInfo("path")
addonArt = os.path.join(addonPath,'resources/images')
communityStreamPath = os.path.join(addonPath,'resources/community')


def PlayStream(sourceEtree, urlSoup, name, url):
	try:
		#url = urlSoup.url.text
		pDialog = xbmcgui.DialogProgress()
		pDialog.create('XBMC', 'Parsing the xml file')
		pDialog.update(10, 'fetching channel info')
		title=''
		link=''
		sc=''
		try:
			title=urlSoup.item.title.text
			
			link=urlSoup.item.link.text
			sc=sourceEtree.findtext('sname')
		except: pass
		if link=='':
			timeD = 2000  #in miliseconds
			line1="couldn't read title and link"
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, timeD, __icon__))
			return False
		regexs = urlSoup.find('regex')
		pDialog.update(80, 'Parsing info')
		if (not regexs==None) and len(regexs)>0:
			liveLink=	getRegexParsed(urlSoup,link)
		else:
			liveLink=	link
		liveLink=liveLink
		if len(liveLink)==0:
			timeD = 2000  #in miliseconds
			line1="couldn't read title and link"
			xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__,line1, timeD, __icon__))
			return False
			
		timeD = 2000  #in miliseconds
		line1="Resource found,playing now."
		pDialog.update(80, line1)
		liveLink=replaceSettingsVariables(liveLink)
		name+='-'+sc+':'+title
		print 'liveLink',liveLink
		pDialog.close()
		listitem = xbmcgui.ListItem( label = str(name), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=liveLink )
		player = CustomPlayer.MyXBMCPlayer()
		start = time.time() 
		#xbmc.Player().play( liveLink,listitem)
		player.play( liveLink,listitem)
		while player.is_active:
			xbmc.sleep(200)
		#return player.urlplayed
		done = time.time()
		elapsed = done - start
		if player.urlplayed and elapsed>=3:
			return True
		else:
			return False  
	except:
		traceback.print_exc(file=sys.stdout)    
	return False  

def getRegexParsed(regexs, url,cookieJar=None,forCookieJarOnly=False,recursiveCall=False):#0,1,2 = URL, regexOnly, CookieJarOnly

	cachedPages = {}
	#print 'url',url
	doRegexs = re.compile('\$doregex\[([^\]]*)\]').findall(url)
	print 'doRegexs',doRegexs,regexs

	for rege in doRegexs:
		k=regexs.find("regex",{"name":rege})
		if not k==None:
			cookieJarParam=False
			if k.cookiejar:
				cookieJarParam=k.cookiejar.text;
				if  '$doregex' in cookieJarParam:
					cookieJar=getRegexParsed(regexs, cookieJarParam,cookieJar,True, True)
					cookieJarParam=True
				else:
					cookieJarParam=True
			if cookieJarParam:
				if cookieJar==None:
					#print 'create cookie jar'
					import cookielib
					cookieJar = cookielib.LWPCookieJar()
					#print 'cookieJar new',cookieJar
			page = k.page.text
			if  '$doregex' in page:
				page=getRegexParsed(regexs, page,cookieJar,recursiveCall=True)
				
			postInput=None
			if k.post:
				postInput = k.post.text
				if  '$doregex' in postInput:
					postInput=getRegexParsed(regexs, postInput,cookieJar,recursiveCall=True)
				print 'post is now',postInput
				
				
			if page in cachedPages :
				link = cachedPages[page]
			else:
				#print 'Ingoring Cache',m['page']
				req = urllib2.Request(page)
				req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
				if k.refer:
					req.add_header('Referer', k.refer.text)
				if k.agent:
					req.add_header('User-agent', k.agent.text)

				if not cookieJar==None:
					#print 'cookieJarVal',cookieJar
					cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
					opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
					opener = urllib2.install_opener(opener)
				#print 'after cookie jar'

				post=None
				if postInput:
					postData=postInput
					splitpost=postData.split(',');
					post={}
					for p in splitpost:
						n=p.split(':')[0];
						v=p.split(':')[1];
						post[n]=v
					post = urllib.urlencode(post)

				if post:
					response = urllib2.urlopen(req,post)
				else:
					response = urllib2.urlopen(req)

				link = response.read()

				response.close()
				cachedPages[page] = link
				if forCookieJarOnly:
					return cookieJar# do nothing
			print 'link',link
			print k.expres.text
			reg = re.compile(k.expres.text).search(link)
			
			url = url.replace("$doregex[" + rege + "]", reg.group(1).strip())
			if recursiveCall: return url
	print 'final url',url
	return url

def replaceSettingsVariables(str):
	retVal=str
	if '$setting' in str:
		matches=re.findall('\$(setting_.*?)\$', str)
		for m in matches:
			setting_val=selfAddon.getSetting( m )
			retVal=retVal.replace('$'+m+'$',setting_val)
	return retVal

########NEW FILE########
__FILENAME__ = livetvPlayer
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin
import urllib2,urllib,cgi, re
import HTMLParser
import xbmcaddon
import json
import traceback
import os
import cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
import datetime
import sys
import time
import CustomPlayer


__addon__       = xbmcaddon.Addon()
__addonname__   = __addon__.getAddonInfo('name')
__icon__        = __addon__.getAddonInfo('icon')
addon_id = 'plugin.video.shahidmbcnet'
selfAddon = xbmcaddon.Addon(id=addon_id)
addonPath = xbmcaddon.Addon().getAddonInfo("path")
addonArt = os.path.join(addonPath,'resources/images')
communityStreamPath = os.path.join(addonPath,'resources/community')


def PlayStream(sourceEtree, urlSoup, name, url):
	try:
		playpath=urlSoup.chnumber.text
		pDialog = xbmcgui.DialogProgress()
		pDialog.create('XBMC', 'Communicating with Livetv')
		pDialog.update(40, 'Attempting to Login')
		code=getcode(shoudforceLogin());
		print 'firstCode',code
		if not code or code[0:1]=="w":
			pDialog.update(40, 'Refreshing Login')
			code=getcode(True);
			print 'secondCode',code
		liveLink= sourceEtree.findtext('rtmpstring')
		pDialog.update(80, 'Login Completed, now playing')
		print 'rtmpstring',liveLink
		#liveLink=liveLink%(playpath,match)
		liveLink=liveLink%(playpath,code)
		name+='-LiveTV'
		print 'liveLink',liveLink
		listitem = xbmcgui.ListItem( label = str(name), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=liveLink )
		pDialog.close()
		player = CustomPlayer.MyXBMCPlayer()
		start = time.time()
		#xbmc.Player().play( liveLink,listitem)
		player.play( liveLink,listitem)
		while player.is_active:
			xbmc.sleep(200)
		#return player.urlplayed
		#done = time.time()
		done = time.time()
		elapsed = done - start
		if player.urlplayed and elapsed>=3:
			return True
		else:
			return False 
	except:
		traceback.print_exc(file=sys.stdout)    
	return False    

def getcode(forceLogin=False):
	#url = urlSoup.url.text
	cookieJar= getCookieJar(forceLogin)
	cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
	opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
	opener = urllib2.install_opener(opener)
	req = urllib2.Request('http://www.livetv.tn/index.php')
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	match =re.findall('code=([^\']*)', link)
	return match[0]

def getCookieJar(login=False):
	cookieJar=None
	COOKIEFILE = communityStreamPath+'/livePlayerLoginCookie.lwp'
	try:
		cookieJar = cookielib.LWPCookieJar()
		cookieJar.load(COOKIEFILE)
	except: 
		cookieJar=None
	
	if login or not cookieJar:
		cookieJar=performLogin()
	if cookieJar:
		cookieJar.save (COOKIEFILE)
	return cookieJar

	
def performLogin():
	print 'performing login'
	userName=selfAddon.getSetting( "liveTvLogin" )
	password=selfAddon.getSetting( "liveTvPassword" )
	cookieJar = cookielib.LWPCookieJar()
	cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
	opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
	opener = urllib2.install_opener(opener)
	req = urllib2.Request('http://www.livetv.tn/login.php')
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	post={'pseudo':userName,'mpass':password}
	post = urllib.urlencode(post)
	response = urllib2.urlopen(req,post)
	now_datetime=datetime.datetime.now()
	selfAddon.setSetting( id="lastLivetvLogin" ,value=now_datetime.strftime("%Y-%m-%d %H:%M:%S"))
	return cookieJar;


def shoudforceLogin():
    try:
#        import dateime
        lastUpdate=selfAddon.getSetting( "lastLivetvLogin" )
        print 'lastUpdate',lastUpdate
        do_login=False
        now_datetime=datetime.datetime.now()
        if lastUpdate==None or lastUpdate=="":
            do_login=True
        else:
            print 'lastlogin',lastUpdate
            try:
                lastUpdate=datetime.datetime.strptime(lastUpdate,"%Y-%m-%d %H:%M:%S")
            except TypeError:
                lastUpdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(lastUpdate, "%Y-%m-%d %H:%M:%S")))
        
            t=(now_datetime-lastUpdate).seconds/60
            print 'lastUpdate',lastUpdate,now_datetime
            print 't',t
            if t>15:
                do_login=True
        print 'do_login',do_login
        return do_login
    except:
        traceback.print_exc(file=sys.stdout)
    return True

########NEW FILE########
__FILENAME__ = teledunetPlayer
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin
import urllib2,urllib,cgi, re
import HTMLParser
import xbmcaddon
import json
import traceback
import os
import cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
import datetime
import time
import sys
import CustomPlayer

__addon__       = xbmcaddon.Addon()
__addonname__   = __addon__.getAddonInfo('name')
__icon__        = __addon__.getAddonInfo('icon')
addon_id = 'plugin.video.shahidmbcnet'
selfAddon = xbmcaddon.Addon(id=addon_id)
addonPath = xbmcaddon.Addon().getAddonInfo("path")
addonArt = os.path.join(addonPath,'resources/images')
communityStreamPath = os.path.join(addonPath,'resources/community')

def PlayStream(sourceEtree, urlSoup, name, url):
	try:
		channelId = urlSoup.url.text
		pDialog = xbmcgui.DialogProgress()
		pDialog.create('XBMC', 'Communicating with Teledunet')
		pDialog.update(10, 'fetching channel page')
		loginName=selfAddon.getSetting( "teledunetTvLogin" )

		if not (loginName==None or loginName==""):
			cookieJar,loginPerformed= getCookieJar(shoudforceLogin())
			if cookieJar and not loginPerformed:
				print 'adding cookie jar'
				now_datetime=datetime.datetime.now()
				selfAddon.setSetting( id="lastteledunetLogin" ,value=now_datetime.strftime("%Y-%m-%d %H:%M:%S"))
				cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
				opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
				opener = urllib2.install_opener(opener)
			
		if 1==1:
			newURL='http://www.teledunet.com/mobile/?con'
			print 'newURL',newURL
			req = urllib2.Request(newURL)
			req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
			req.add_header('Referer',newURL)
			response = urllib2.urlopen(req)
			link=response.read()
			response.close()
			match =re.findall('aut=\'\?id0=(.*?)\'', link)
			print match
			timesegment=match[0];str(long(float(match[0])))
			try:
				rtmp =re.findall(('rtmp://(.*?)/%s\''%channelId), link)[0]
				rtmp='rtmp://%s/%s'%(rtmp,channelId)
				#if '5.135.134.110' in rtmp and 'bein' in channelId:
				#	rtmp=rtmp.replace('5.135.134.110','www.teledunet.com')
			except:
				traceback.print_exc(file=sys.stdout)  
				rtmp='rtmp://5.135.134.110:1935/teledunet/%s'%(channelId)
		pDialog.update(80, 'trying to play')
		liveLink= sourceEtree.findtext('rtmpstring');

		print 'rtmpstring',liveLink,rtmp
#		liveLink=liveLink%(rtmp,channelId,match,channelId,channelId)
		liveLink=liveLink%(rtmp,channelId,timesegment,channelId)
		name+='-Teledunet'
		print 'liveLink',liveLink
		pDialog.close()
		listitem = xbmcgui.ListItem( label = str(name), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=liveLink )
		player = CustomPlayer.MyXBMCPlayer()
		#xbmc.Player().play( liveLink,listitem)
		start = time.time()  
		player.play( liveLink,listitem)  
		while player.is_active:
			xbmc.sleep(200)
		#return player.urlplayed
		done = time.time()
		elapsed = done - start
		if player.urlplayed and elapsed>=3:
			return True
		else:
			return False
	except:
		traceback.print_exc(file=sys.stdout)    
	return False  



def getCookieJar(login=False):
	try:
		cookieJar=None
		COOKIEFILE = communityStreamPath+'/teletdunetPlayerLoginCookie.lwp'
		try:
			cookieJar = cookielib.LWPCookieJar()
			cookieJar.load(COOKIEFILE)
		except:
			traceback.print_exc(file=sys.stdout)	
			cookieJar=None
		loginPerformed=False
		if login or not cookieJar==None:
			cookieJar=performLogin()
			loginPerformed=True
		if cookieJar:
			cookieJar.save (COOKIEFILE)
		return cookieJar,loginPerformed
	except:
		traceback.print_exc(file=sys.stdout)
		return None, False
	
def performLogin():
	print 'performing login'
	userName=selfAddon.getSetting( "teledunetTvLogin" )
	password=selfAddon.getSetting( "teledunetTvPassword" )
	cookieJar = cookielib.LWPCookieJar()
	cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
	opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
	opener = urllib2.install_opener(opener)
	req = urllib2.Request('http://www.teledunet.com/boutique/connexion.php')
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	post={'login_user':userName,'pass_user':password}
	post = urllib.urlencode(post)
	response = urllib2.urlopen(req,post)
	link=response.read()
	response.close()
	now_datetime=datetime.datetime.now()
	req = urllib2.Request('http://www.teledunet.com/')#access main page too
	req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
	response = urllib2.urlopen(req)
	link=response.read()
	response.close()
	return cookieJar;


def shoudforceLogin():
    return True #disable login
    try:
#        import dateime
        lastUpdate=selfAddon.getSetting( "lastteledunetLogin" )
        print 'lastUpdate',lastUpdate
        do_login=False
        now_datetime=datetime.datetime.now()
        if lastUpdate==None or lastUpdate=="":
            do_login=True
        else:
            print 'lastlogin',lastUpdate
            try:
                lastUpdate=datetime.datetime.strptime(lastUpdate,"%Y-%m-%d %H:%M:%S")
            except TypeError:
                lastUpdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(lastUpdate, "%Y-%m-%d %H:%M:%S")))
        
            t=(now_datetime-lastUpdate).seconds/60
            print 'lastUpdate',lastUpdate,now_datetime
            print 't',t
            if t>15:
                do_login=True
        print 'do_login',do_login
        return do_login
    except:
        traceback.print_exc(file=sys.stdout)
    return True

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import httplib
import time


__settings__ = xbmcaddon.Addon(id='plugin.video.sonara')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])



def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'http://upload.wikimedia.org/wikipedia/he/e/ed/Sonara_logo_.gif'))
	addDir('مسلسلات رمضان 2013','http://www.sonara.net/videon-85.html',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('مسلسلات عربية','http://www.sonara.net/vncat/49/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA_%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('كرتون ','http://www.sonara.net/vncat/53/%D9%83%D8%B1%D8%AA%D9%88%D9%86',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('افلام عربية','http://www.sonara.net/vcat/603/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9',4,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('افلام اسود و ابيض','http://www.sonara.net/vcat/722/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%A7%D8%A8%D9%8A%D8%B6_%D9%88%D8%A7%D8%B3%D9%88%D8%AF',4,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	#addDir('افلام وثائقية','http://www.sonara.net/video_cat-970.html',4,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('برامج','http://www.sonara.net/vncat/52/%D8%A8%D8%B1%D8%A7%D9%85%D8%AC',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	#addDir('خاص بالصنارة','http://www.sonara.net/videon-54.html',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('مسلسلات تركية','http://www.sonara.net/vncat/50/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA_%D8%AA%D8%B1%D9%83%D9%8A%D8%A9',1,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	addDir('افلام تركية','http://www.sonara.net/vcat/860/%D8%A7%D9%81%D9%84%D8%A7%D9%85_%D8%AA%D8%B1%D9%83%D9%8A%D8%A9',4,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	#addDir('افلام هندية','http://www.sonara.net/video_cat-604.html',4,'http://profile.ak.fbcdn.net/hprofile-ak-ash4/s160x160/416801_327989490581599_1718150811_a.jpg')
	
	
		
def listContent(url):
	  
    req = urllib2.Request(url)
    req.add_header('Host', 'www.sonara.net')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:21.0) Gecko/20100101 Firefox/21.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Language', 'en-US,en;q=0.5')
    req.add_header('Cookie', 'InterstitialAd=1; __utma=261095506.1294916015.1370631116.1370631116.1370631116.1; __utmb=261095506.1.10.1370631116; __utmc=261095506; __utmz=261095506.1370631116.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)')
   
    
    req.add_header('Connection', 'keep-alive')
    response = urllib2.urlopen(req)
    link=response.read()
    name = ""
    img = ""
    path = ""
    base = "http://sonara.net"
    target= re.findall(r"<div class='mediasection'>(.*?)\s(.*?)<div class='footer'>", link, re.DOTALL)
    for itr in target:
        myPath=str( itr[1]).split("'>")
        for items in myPath:
        
            if "<a href=" in str( items):
                path=str( items).split("<a href='")[1]
                path=base+str( path).strip()
                
            if "<img src='" in str( items):
                img=str( items).split("<img src='")[1]
                img=str(img).strip()
                
            if "<h4>" in str( items):
                name=str( items).split("</h4></a>")[0]
                name=str(name).replace("<h4>","").strip()
                addDir(name,path,2,img)

def listFilmContent(url):
    req = urllib2.Request(url)
    req.add_header('Host', 'www.sonara.net')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:21.0) Gecko/20100101 Firefox/21.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Language', 'en-US,en;q=0.5')
    req.add_header('Cookie', 'InterstitialAd=1; __utma=261095506.1294916015.1370631116.1370631116.1370631116.1; __utmb=261095506.1.10.1370631116; __utmc=261095506; __utmz=261095506.1370631116.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)')
   
    
    req.add_header('Connection', 'keep-alive')
    response = urllib2.urlopen(req)
    link=response.read()
    name = ""
    img = ""
    path = ""
    base = "http://sonara.net"
    target= re.findall(r"<div class='video_listrel'>(.*?)\s(.*?)<div class='footer'>", link, re.DOTALL)
    for itr in target:
        myPath=str( itr[1]).split("'>")
        for items in myPath:
        
            if "<a href=" in str( items):
				path=str( items).split("<a href='")[1]
				path=str( path).strip()
				path=str( path).split("/")
				path =str( path[2]).strip()
                
            if "<img src='" in str( items):
                img=str( items).split("<img src='")[1]
                img=str(img).strip()
                
            if "<h4>" in str( items):
                name=str( items).split("</h4></a>")[0]
                name=str(name).replace("<h4>","").strip()
                addLink(name,path,3,img)
                                 

def listEpos(url):
	req = urllib2.Request(url)
	req.add_header('Host', 'www.sonara.net')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:21.0) Gecko/20100101 Firefox/21.0')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Accept-Language', 'en-US,en;q=0.5')
	req.add_header('Cookie', 'InterstitialAd=1; __utma=261095506.1294916015.1370631116.1370631116.1370631116.1; __utmb=261095506.1.10.1370631116; __utmc=261095506; __utmz=261095506.1370631116.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)')
	req.add_header('Connection', 'keep-alive')
	response = urllib2.urlopen(req)
	link=response.read()
	name = ""
	img = ""
	path = ""
	base = "http://sonara.net"
	target= re.findall(r"<div class='long_after_video'></div>(.*?)\s(.*?)<div class='footer'>", link, re.DOTALL)
	for itr in target:
		myPath=str( itr[1]).split("'>")
		for items in myPath:
			
			if "<a href=" in str( items):
				path=str( items).split("<a href='")[1]
				path=str( path).split("/")
				path =str( path[2]).strip()
            
			if "<img src='" in str( items):
				img=str( items).split("<img src='")[1]
				img=str(img).strip()
            
			if "<h4>" in str( items):
				name=str( items).split("</h4></a>")[0]
				name=str(name).replace("<h4>","").strip()
				addLink(name,path,3,img)
    

def getVideoFile(url):
	try:
			url='http://www.sonara.net/video_player_new.php?ID='+str(url) 
			req = urllib2.Request(url)
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			req.add_header('Cookie', 'InterstitialAd=1; __utma=261095506.1294916015.1370631116.1370631116.1370631116.1; __utmb=261095506.9.10.1370631116; __utmc=261095506; __utmz=261095506.1370631116.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); geo_user=INT; popupbannerA=1')
			response = urllib2.urlopen(req)
			link=response.read()
			target= re.findall(r"<script type='text/javascript'>(.*?)\s(.*?)</script>", link, re.DOTALL)
			target=str(target).split(',')
			mp4File=''
			swfFile=''
			rtmp=''
			for itr in target:
				
				if 'mp4' in itr:
					mp4File=str(itr).split("&image=")[0]
					mp4File=str(mp4File).replace("\'mp4:","").strip()
					mp4File=str(mp4File).replace("\/","mp4:/").strip()
				if ("flv") in itr:
					mp4File = str(itr).split("&image")[0]
					mp4File=str(mp4File).replace("\'flv:","").strip()
					mp4File=str(mp4File).replace("\/","flv:/").strip()
					mp4File = str(mp4File).split("/")[1]
				if 'SWFObject' in itr:
					swfFile=str( itr).split("SWFObject")[1]
					swfFile=str(swfFile).split("http:")[1]
					swfFile=str(swfFile).split(".swf")[0]
					swfFile="http:"+swfFile+".swf"
				if 'rtmp' in itr:
					rtmp=str( itr).split("');")[0]
					rtmp=str( rtmp).split("rtmp:")[1]
					rtmp=rtmp[:-1]
					rtmp="rtmp:"+rtmp
					swfFile="http://www.sonara.net/mediaplayera/player.swf"
				
			playingpath=rtmp+" swfUrl="+swfFile+" playpath="+mp4File+" timeout=15"
			listItem = xbmcgui.ListItem(path=str(playingpath))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	except:
		pass
				
    
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param





def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        listContent(url)
	
elif mode==2:
        print ""+url
        listEpos(url)
elif mode==3:
	print ""+url
	getVideoFile(url)
	
elif mode==4:
        print ""+url
        listFilmContent(url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
import urllib, urllib2, re, cookielib
import xbmcplugin, xbmcgui, xbmcaddon
from BeautifulSoup import BeautifulSoup
import sys

thisPlugin = int(sys.argv[1])

# Setting constants
MODE_GOTO_MOVIE_CATEGORIES = 1
MODE_GOTO_MOVIE_LISTINGS = 2
MODE_PLAYVIDEO = 3
MODE_NOVIDEOS = 4

LISTING_MOST_RECENT = "mr";
LISTING_MOST_VIEWED = "mv";
LISTING_TOP_RATED = "tr";
LISTING_RECENTLY_FEATURED = "rf";
LISTING_RECENTLY_VIEWED = "rv";
LISTING_RANDOM = "ran";

URL_PATTERN_MOVIES = "http://www.sotwesoora.tv/categories&cid=1&c=Movies&lo=detailed&s={listingType}&t=a&p={pageNo}"
URL_PATTERN_XML_CONFIG = "http://www.sotwesoora.tv/flv_player/data/playerConfig/{videoId}.xml"

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

class VideoClipRow():
    def __init__(self, el):
        imgEl = el.find('img')
        self.thumbnail = imgEl['src']
        self.name = imgEl['alt']
        self.url = el.find('a')['href'].encode('utf-8')

def getRootCategories():
    addDir("Movies", MODE_GOTO_MOVIE_CATEGORIES)
    xbmcplugin.endOfDirectory(thisPlugin)

def getMovieCategories():
    addDir("Recently Featured", MODE_GOTO_MOVIE_LISTINGS, LISTING_RECENTLY_FEATURED)
    addDir("Recently Viewed", MODE_GOTO_MOVIE_LISTINGS, LISTING_RECENTLY_VIEWED)
    addDir("Most Recent", MODE_GOTO_MOVIE_LISTINGS, LISTING_MOST_RECENT)
    addDir("Most Viewed", MODE_GOTO_MOVIE_LISTINGS, LISTING_MOST_VIEWED)
    addDir("Top Rated", MODE_GOTO_MOVIE_LISTINGS, LISTING_TOP_RATED)
    addDir("Random", MODE_GOTO_MOVIE_LISTINGS, LISTING_RANDOM)
    xbmcplugin.endOfDirectory(thisPlugin)

def getMovieLinks(listingType, pageNo):
    pageUrl = URL_PATTERN_MOVIES.format(listingType=listingType, pageNo=pageNo)

    response = opener.open(pageUrl)
    inner_data = response.read();
    opener.close()

    soup = BeautifulSoup(inner_data)

    boxRowElList = soup.findAll('div', {'class': 'box'})
    resultsCount = len(boxRowElList)

    for boxRowEl in boxRowElList:
        clip = VideoClipRow(boxRowEl)
        addLink(clip.name, clip.url, MODE_PLAYVIDEO, clip.thumbnail, resultsCount)

    addDir("Next Page >>", MODE_GOTO_MOVIE_LISTINGS, listingType, pageNo + 1)

    xbmcplugin.endOfDirectory(thisPlugin)

def playVideo(thumbnailUrl):
    m = re.search('.*\/(\d+)\/.*', thumbnailUrl, re.M|re.I)
    videoId = m.group(1)
    playerConfigUrl = URL_PATTERN_XML_CONFIG.format(videoId=videoId)

    response = opener.open(playerConfigUrl)
    html_data = response.read()
    opener.close()

    soup = BeautifulSoup(html_data)
    clipStreamingUrl = soup.find('video')['sd']

    listItem = xbmcgui.ListItem(path=clipStreamingUrl)
    return xbmcplugin.setResolvedUrl(thisPlugin, True, listItem)

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

def addDir(name, mode, listingType=None, pageIndex=None):
    u = sys.argv[0] + "?mode=" + str(mode) + "&listingType=" + str(listingType) + "&pageIndex=" + str(pageIndex)
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage="DefaultFolder.png")
    liz.setInfo(type="Video", infoLabels={"Title": name})
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok

def addLink(name, url, mode, iconImage, totalItems):
    u = sys.argv[0] + "?url=" + urllib.quote_plus(url) + "&mode=" + str(mode)
    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconImage)
    liz.setInfo(type="Video", infoLabels={"Title": name})
    liz.setProperty('IsPlayable', 'true')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, totalItems=totalItems)
    return ok

params = get_params()
url = None
lastMode = None
listingType = None
pageIndex = 1

try:
    url = urllib.unquote_plus(params["url"])
except:
    pass
try:
    lastMode = int(params["mode"])
except:
    pass
try:
    listingType = params["listingType"]
except:
    pass
try:
    pageIndex = int(params["pageIndex"])
except:
    pass

if lastMode is None:
    getRootCategories()

elif lastMode == MODE_GOTO_MOVIE_CATEGORIES:
    getMovieCategories()

elif lastMode == MODE_GOTO_MOVIE_LISTINGS:
    getMovieLinks(listingType, pageIndex)

elif lastMode == MODE_PLAYVIDEO:
    playVideo(url)

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib,itertools

import time


__settings__ = xbmcaddon.Addon(id='plugin.video.syriadrama')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])



def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	#xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('WARNING','This addon is completely FREE DO NOT buy any products from http://tvtoyz.com/', 16000, 'https://lh5.googleusercontent.com/-ZaRTz8kxk-k/AAAAAAAAAAI/AAAAAAAAAAA/f643_NNxkOU/s48-c-k-no/photo.jpg'))
	addDir('SYRIA DRAMA','http://www.syria-drama.net/video-category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA/',1,'http://www.english.globalarabnetwork.com/images/stories/2009/August/Syria_Drama_Channel_Officially_Launched.jpg')
	
	
def indexContent(url):
   
	max=6
	for counter in range(1,max):
		try:
			myPath=str(url)+"page/"+str(counter)+"/"
			req = urllib2.Request(myPath)
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			target= re.findall(r'tooltip_n" href="(.*?)\s(.*?)</span></a>', link, re.DOTALL)
			for items in target:
				mySerie=items[1]              
				myUrl=str( items[0]).replace('"','').strip()
				name=str(mySerie).split('"><img width=')[0]
				name=str(name).replace('title="', '').strip()
				image=str(mySerie).split('class="attachment-post-thumbnail')[0]
				image=str(image).split('src="')[1]
				image=str(image).replace('"', "").replace("..jpg",".jpg").strip()
				print name
				print image
				print myUrl
				
				if "مسلسل" in name:
					addDir(name,myUrl,2,image)
				else:
					addLink(name,myUrl,3,image)
					
		except:
			pass	

def indexEpos (url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	target= re.findall(r'<ul class="episode">(.*?)\s(.*?)<div class="clear"></div>', link, re.DOTALL)
	try:
		for items in target:
			myPath=str( items[1]).split('</li>')
			for i in myPath:
				name=str( i).split(' href="')[0]
				myPath=str( i).split(' href="')[1]
				myPath=str(myPath).split('">')[0]
				myPath=str(myPath).replace('"', '').strip()
				name=str(name).replace('<li><a class="tooltip_s" title="', '').replace('"',"").replace("</ul>","").strip()
				addLink(name,myPath,3,'')
				print name
				print myPath
	except:
		pass
def playVideo(url):
		req = urllib2.Request(url)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib2.urlopen(req)
		link=response.read()
		myVideo=(re.compile('<iframe width="520" height="400" src="(.+?)"></iframe>').findall(link))
		
		myVideo=str(myVideo).replace("['", '').replace("']", '').replace("http://www.youtube.com/embed/","").strip()
		if  str(myVideo) > 1 :
			print "YOUTUBE VIDEO "+str(myVideo)
			playback_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % myVideo
			listItem = xbmcgui.ListItem(path=str(playback_url))
			xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
		else :
			 myVideo2=(re.compile('<source src="(.+?)" type="video/flash" />').findall(link))
			 myVideo2=str(myVideo).replace("['", '').replace("']", '').strip()
			 listItem = xbmcgui.ListItem(path=str(myVideo2))
			 xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
        
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param





def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        indexContent(url)
	
elif mode==2:
        print ""+url
        indexEpos(url)
elif mode==3:
	print ""+url
	playVideo(url)


xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = default
from operator import itemgetter
import os
import xbmcplugin
import xbmcgui
import xbmcaddon
from xbmcswift2 import Plugin


# Setup global variables
from resources.lib.teledunet import scraper
from resources.lib.teledunet.api import TeledunetAPI


CACHE_DURATION_MINUTES = 24 * 60     # Cache for 5hrs

plugin = Plugin()


@plugin.route('/')
def list_categories():
    items = [{
                 'label': 'All',
                 'path': plugin.url_for('list_all_channels'),
                 'thumbnail': _art('art', 'all.png')

             }, {
                 'label': 'Browse by Category',
                 'path': plugin.url_for('browse_by_category'),
                 'thumbnail': _art('art', 'category.png')
             }, {
                 'label': 'Browse by Network',
                 'path': plugin.url_for('browse_by_network'),
                 'thumbnail': _art('art', 'network.png')
             }]

    return items


@plugin.route('/list/all/')
def list_all_channels():
    items = [{
                 'label': channel.display_name(),
                 'path': plugin.url_for('play_video', url=channel.path),
                 'thumbnail': channel.thumbnail,
                 'is_playable': True,
             } for channel in api.get_channels()]

    return plugin.finish(items, sort_methods=['label'])


@plugin.route('/list/browse_by_category/')
def browse_by_category():
    categories = api.get_channels_grouped_by_category()

    for category in categories:
        category['path'] = plugin.url_for('list_channels_for_category', category_name=category['category_name'])
        del category['category_name']

    return sorted(categories, key=itemgetter('label'))


@plugin.route('/list/browse_by_network/')
def browse_by_network():
    networks = api.get_channels_grouped_by_network()

    for network in networks:
        network['path'] = plugin.url_for('list_channels_for_network', network_name=network['network_name'])
        del network['network_name']

    return sorted(networks, key=itemgetter('label'))


@plugin.route('/list/category/<category_name>')
def list_channels_for_category(category_name):
    channels = api.get_channels()
    category_channels = api.get_channels_for_category(channels, category_name)

    items = [{
                 'label': channel.display_name(),
                 'path': plugin.url_for('play_video', url=channel.path),
                 'thumbnail': channel.thumbnail,
                 'is_playable': True,
             } for channel in category_channels]

    return plugin.finish(items, sort_methods=['label'])


@plugin.route('/list/network/<network_name>')
def list_channels_for_network(network_name):
    channels = api.get_channels()
    network_channels = api.get_channels_for_network(channels, network_name)

    items = [{
                 'label': channel.display_name(),
                 'path': plugin.url_for('play_video', url=channel.path),
                 'thumbnail': channel.thumbnail,
                 'is_playable': True,
             } for channel in network_channels]

    return plugin.finish(items, sort_methods=['label'])


@plugin.route('/play/<url>')
def play_video(url):
    rtmp_params = scraper.get_rtmp_params(url)

    def rtmpdump_output(rtmp_params):
        return (
                   'rtmpdump.exe '
                   '--rtmp "%(rtmp_url)s" '
                   '--app "%(app)s" '
                   '--swfUrl "%(swf_url)s" '
                   '--playpath "%(playpath)s" '
                   '-o test.flv'
               ) % rtmp_params

    def xbmc_output(rtmp_params):
        return (
                   '%(rtmp_url)s '
                   'app=%(app)s '
                   'swfUrl=%(swf_url)s '
                   'playpath=%(playpath)s '
                   'live=%(live)s '
                   'pageUrl=%(video_page_url)s '
               ) % rtmp_params

    playback_url = xbmc_output(rtmp_params)
    plugin.log.info('RTMP cmd: %s' % rtmpdump_output(rtmp_params))
    plugin.log.info('XBMC cmd: %s' % xbmc_output(rtmp_params))

    return plugin.set_resolved_url(playback_url)


def _art(file, *args):
    return os.path.join(plugin.addon.getAddonInfo('path'), file, *args)


if __name__ == '__main__':
    cache = plugin.get_storage('teledunet_cache.txt', TTL=CACHE_DURATION_MINUTES)
    api = TeledunetAPI(cache)

    if api:
        plugin.run()

########NEW FILE########
__FILENAME__ = api
from scraper import (get_rtmp_params, get_channels)

NETWORKS = {
    'Rotana': [],
    'Abu Dhabi': [],
    'Alarabiya': [],
    'Alhayat': [],
    'Aljazeera': ['JSC'],
    'CBC': [],
    'Dubai': [],
    'Dream': [],
    'MBC': [],
    'Panorama': [],
    'Persian': [],
    'Rotana': [],
    'Sama ': [],
    'Nile': [],
    'Melody': [],
    'Fox': [],
    'Al Nahar': ['Al-Nahar', 'Nahar']
}

CATEGORIES = {
    'Movies': ['Cinema', 'Aflam', 'Film', 'Cima'],
    'Drama': ['Series', 'Hekayat'],
    'Comedy': [],
    'Cooking': ['Fatafeat'],
    'Children': ['Ajyal', 'Baraem', 'Cartoon', 'Founon', 'Cocuk', 'Spacepower', 'Toyor'],
    'General': ['Alhayat', 'Dream', 'CBC', 'Faraeen', 'MBC Masr', 'MBC 1', 'MBC 3', 'MBC 4',
                'Masria', 'Masriya', 'Mehwar', 'Misr 25', 'Life', 'On TV', 'Ontv', 'Qatar', 'Dubai', 'Syria',
                'Sharjah'],
    'News': ['Alarabiya', 'Aljazeera', 'France', 'Geographic'],
    'Sport': ['riadia', 'Gladiator', 'JSC', 'Mosar3'],
    'Music': ['Aghanina', 'Hits', 'Zaman', 'Khaliji', 'Clip', 'Arabica', 'Ghinwa', 'Mawal', 'Mazzika', 'Mazeka', 'Melody Tv', 'Mtv', 'Zaman'],
    'Religion': ['Rahma', 'Anwar', 'Kawthar', 'Resala', 'Alnas', 'Coran', 'Iqra'],
    'English': ['Dubai One', 'Top Movies', 'MBC 2', 'Fx', 'MBC Action', 'MBC Drama', 'MBC Max', 'MBC Maghreb']
}

'''The main API object. Useful as a starting point to get available subjects. '''


class TeledunetAPI(object):
    def __init__(self, cache):
        self.cache = cache

    def get_rtmp_params(self, channel_name):
        return get_rtmp_params(channel_name)

    def get_channels(self):
        if 'data' not in self.cache:
            self.cache['data'] = get_channels()

        return self.cache.get('data')

    def get_channels_grouped_by_network(self):
        items = []
        channels = self.get_channels()

        for network in NETWORKS:
            children = self.get_channels_for_network(channels, network)
            items.append({
                'network_name': network,
                'label': '%(channel)s ([COLOR blue]%(count)s[/COLOR])' % {'channel': network, 'count': len(children)}
            })

        return items

    def get_channels_grouped_by_category(self):
        items = []
        channels = self.get_channels()

        for category in CATEGORIES:
            children = self.get_channels_for_category(channels, category)
            items.append({
                'category_name': category,
                'label': '%(channel)s ([COLOR blue]%(count)s[/COLOR])' % {'channel': category, 'count': len(children)}
            })

        return items

    def get_channels_for_category(self, channels, channel_name):
        def __belongsToNetwork(channel):
            for prefix in CATEGORIES[channel_name]:
                if prefix in channel.title:
                    return True
            return channel_name in channel.title

        return filter(__belongsToNetwork, channels)

    def get_channels_for_network(self, channels, network_name):

        def __belongsToNetwork(channel):
            for prefix in NETWORKS[network_name]:
                if channel.title.startswith(prefix):
                    return True
            return channel.title.startswith(network_name)

        return filter(__belongsToNetwork, channels)
########NEW FILE########
__FILENAME__ = hardcode
HARDCODED_STREAMS = [{
                         'title': 'MBC',
                         'thumbnail': 'http://www.teledunet.com//player/icones/mbc_1.jpg',
                         'path': 'mbc_1'},
                     {
                         'title': 'BeIn Sport 1',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_1.jpg',
                         'path': 'bein_sport_1'},
                     {
                         'title': 'BeIn Sport 2',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_2.jpg',
                         'path': 'bein_sport_2'},
                     {
                         'title': 'BeIn Sport 3',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_3.jpg',
                         'path': 'bein_sport_3'},
                     {
                         'title': 'BeIn Sport 4',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_4.jpg',
                         'path': 'bein_sport_4'},
                     {
                         'title': 'BeIn Sport 5',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_5.jpg',
                         'path': 'bein_sport_5'},
                     {
                         'title': 'BeIn Sport 6',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_6.jpg',
                         'path': 'bein_sport_6'},
                     {
                         'title': 'BeIn Sport 7',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_7.jpg',
                         'path': 'bein_sport_7'},
                     {
                         'title': 'BeIn Sport 8',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_8.jpg',
                         'path': 'bein_sport_8'},
                     {
                         'title': 'BeIn Sport 9',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_9.jpg',
                         'path': 'bein_sport_9'},
                     {
                         'title': 'BeIn Sport 10',
                         'thumbnail': 'http://www.teledunet.com//player/icones/bein_sport_10.jpg',
                         'path': 'bein_sport_10'},
                     {
                         'title': 'Abu Dhabi Al Oula',
                         'thumbnail': 'http://www.teledunet.com//player/icones/abu_dhabi.jpg',
                         'path': 'abu_dhabi'},
                     {
                         'title': 'Abu Dhabi Sports',
                         'thumbnail': 'http://www.teledunet.com//player/icones/abu_dhabi_sports_1.jpg',
                         'path': 'abu_dhabi_sports_1'},
                     {
                         'title': 'Al Jazeera',
                         'thumbnail': 'http://www.teledunet.com//player/icones/aljazeera.jpg',
                         'path': 'aljazeera'},
                     {
                         'title': 'Aljadeed',
                         'thumbnail': 'http://www.teledunet.com//player/icones/aljadeed.jpg',
                         'path': 'aljadeed'},
                     {
                         'title': 'OTV Lebanon',
                         'thumbnail': 'http://www.teledunet.com//player/icones/otv_lebanon.jpg',
                         'path': 'otv_lebanon'},
                     {
                         'title': 'Al-Nahar',
                         'thumbnail': 'http://www.teledunet.com//player/icones/al_nahar.jpg',
                         'path': 'al_nahar'},
                     {
                         'title': 'Al Hayat 1',
                         'thumbnail': 'http://www.teledunet.com//player/icones/alhayat_1.jpg',
                         'path': 'alhayat_1'},
                     {
                         'title': 'Al Hayat Series',
                         'thumbnail': 'http://www.teledunet.com//player/icones/alhayat_series.jpg',
                         'path': 'alhayat_series'},
                     {
                         'title': 'Al Hayat Cinema',
                         'thumbnail': 'http://www.teledunet.com//player/icones/alhayat_cinema.jpg',
                         'path': 'alhayat_cinema'},
                     {
                         'title': 'ART Aflam 2',
                         'thumbnail': 'http://www.teledunet.com//player/icones/art_aflam_2.jpg',
                         'path': 'art_aflam_2'},
                     {
                         'title': 'Al Jazeera Children',
                         'thumbnail': 'http://www.teledunet.com//player/icones/aljazeera_children.jpg',
                         'path': 'aljazeera_children'},
                     {
                         'title': 'ART Cinema',
                         'thumbnail': 'http://www.teledunet.com//player/icones/art_aflam_1.jpg',
                         'path': 'art_aflam_1'},
                     {
                         'title': 'Tele Liban',
                         'thumbnail': 'http://www.teledunet.com//player/icones/tele_liban.jpg',
                         'path': 'tele_liban'},
                     {
                         'title': 'Al Hayat 2',
                         'thumbnail': 'http://www.teledunet.com//player/icones/alhayat_2.jpg',
                         'path': 'alhayat_2'},
                     {
                         'title': 'Alarabiya',
                         'thumbnail': 'http://www.teledunet.com//player/icones/alarabiya.jpg',
                         'path': 'alarabiya'},
                     {
                         'title': 'Al Moutawassit',
                         'thumbnail': 'http://www.teledunet.com//player/icones/al_moutawasit.jpg',
                         'path': 'al_mutawasit'},
                     {
                         'title': 'CBC',
                         'thumbnail': 'http://www.teledunet.com/logo/CBC.jpg',
                         'path': 'cbc'},
                     {
                         'title': 'CBC Extra',
                         'thumbnail': 'http://www.teledunet.com/logo/CBC%20Extra.jpg',
                         'path': 'cbc_extra'},
                     {
                         'title': 'CBC 2',
                         'thumbnail': 'http://www.teledunet.com/logo/CBC%202.jpg',
                         'path': 'cbc_2'},
                     {
                         'title': 'CBC Sofra',
                         'thumbnail': 'http://www.teledunet.com/logo/CBC%20Sofra.jpg',
                         'path': 'cbc_sofra'},
                     {
                         'title': 'Al Rafidain',
                         'thumbnail': 'http://www.teledunet.com//player/icones/al_rafidain.jpg',
                         'path': 'al_rafidain'},
                     {
                         'title': 'Dzair 24',
                         'thumbnail': 'http://www.teledunet.com//player/icones/dzair_24.jpg',
                         'path': 'dzair_24'},
                     {
                         'title': 'NBN',
                         'thumbnail': 'http://www.teledunet.com//player/icones/nbn.jpg',
                         'path': 'nbn'},
                     {
                         'title': 'Panorama Drama 2',
                         'thumbnail': 'http://www.teledunet.com//player/icones/panorama_drama_2.jpg',
                         'path': 'panorama_drama_2'},
                     {
                         'title': 'Panorama Drama',
                         'thumbnail': 'http://www.teledunet.com/logo/Panorama%20Drama.jpg',
                         'path': 'panorama_drama'},
                     {
                         'title': 'Panorama Comedy',
                         'thumbnail': 'http://www.teledunet.com//player/icones/panorama_comedy.jpg',
                         'path': 'panorama_comedy'},
                     {
                         'title': 'Sada El Balad +2',
                         'thumbnail': 'http://www.teledunet.com/logo/Sada%20Albalad.jpg',
                         'path': 'sada_albalad'},
                     {
                         'title': 'Libya AlAhrar',
                         'thumbnail': 'http://www.teledunet.com//player/icones/libya_alahrar.jpg',
                         'path': 'libya_alahrar'},
                     {
                         'title': 'Libya Alwatania 1',
                         'thumbnail': 'http://www.teledunet.com//player/icones/libya_alwatania_1.jpg',
                         'path': 'libya_alwatania_1'},
                     {
                         'title': 'Dzair TV',
                         'thumbnail': 'http://www.teledunet.com//player/icones/dzair_tv.jpg',
                         'path': 'dzair_tv'},
                     {
                         'title': 'Sada El Balad',
                         'thumbnail': 'http://www.teledunet.com/logo/Sada%20Albalad.jpg',
                         'path': 'sada_el_balad'},
                     {
                         'title': 'MBC 3',
                         'thumbnail': 'http://www.teledunet.com//player/icones/mbc_3.jpg',
                         'path': 'mbc_3'},
                     {
                         'title': 'MBC Drama',
                         'thumbnail': 'http://www.teledunet.com//player/icones/mbc_drama.jpg',
                         'path': 'mbc_drama'},
                     {
                         'title': 'MBC Masr',
                         'thumbnail': 'http://www.teledunet.com//player/icones/mbc_masr.jpg',
                         'path': 'mbc_masr'},
                     {
                         'title': 'On Tv',
                         'thumbnail': 'http://www.teledunet.com//player/icones/on_tv.jpg',
                         'path': 'on_tv'},
                     {
                         'title': 'Oromia TV',
                         'thumbnail': 'http://www.teledunet.com//player/icones/oromia_tv.jpg',
                         'path': 'oromia_tv'},
                     {
                         'title': 'Tchad',
                         'thumbnail': 'http://www.teledunet.com//player/icones/tchad.jpg',
                         'path': 'tchad'},
                     {
                         'title': 'Wanasah',
                         'thumbnail': 'http://www.teledunet.com//player/icones/wanasah.jpg',
                         'path': 'wanasah'},
                     {
                         'title': 'Roya',
                         'thumbnail': 'http://www.teledunet.com//player/icones/roya.jpg',
                         'path': 'roya'},
                     {
                         'title': 'Kalsan TV',
                         'thumbnail': 'http://www.teledunet.com//player/icones/kalsan_tv.jpg',
                         'path': 'kalsan_tv'},
                     {
                         'title': 'Eriteria TV',
                         'thumbnail': 'http://www.teledunet.com//player/icones/eriteria_tv.jpg',
                         'path': 'eriteria_tv'},
                     {
                         'title': 'El Djazairia',
                         'thumbnail': 'http://www.teledunet.com//player/icones/el_djazairia.jpg',
                         'path': 'el_djazairia'},
                     {
                         'title': 'Al Ekhbariyah Al Syria',
                         'thumbnail': 'http://www.teledunet.com/logo/Al%20Ikhbaria.jpg',
                         'path': 'al_ikhbaria'},
                     {
                         'title': 'MTV LB',
                         'thumbnail': 'http://www.teledunet.com//player/icones/mtv.jpg',
                         'path': 'mtv'},
                     {
                         'title': 'Djibouti TV',
                         'thumbnail': 'http://www.teledunet.com//player/icones/djibouti.jpg',
                         'path': 'djibouti'},
                     {
                         'title': 'OSN Yahala HD +2',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_ya_hala_hd_plus2.png',
                         'path': 'osn_yahala'},
                     {
                         'title': 'OSN Yahala Drama',
                         'thumbnail': 'http://press.osn.com/logo/logos/OYA.png',
                         'path': 'osn_yahala_Drama'},
                     {
                         'title': 'OSN Yahala HD',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_ya_hala_hd.png',
                         'path': 'osn_yahala_hd'},
                     {
                         'title': 'OSN Movies Action HD',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_movies_action_hd.png',
                         'path': 'osn_moies_action'},
                     {
                         'title': 'OSN Movies HD +2',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_movies_hd_plus2.png',
                         'path': 'osn_moies_2'},
                     {
                         'title': 'OSN Movies Comedy',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_movies_comedy_hd.png',
                         'path': 'osn_moies_comdy'},
                     {
                         'title': 'ART Hekayat',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/aa/art_hekayat.png',
                         'path': 'art-hek'},
                     {
                         'title': 'ART Hekayat 2',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/aa/art_hekayat2.png',
                         'path': 'art-hek2'},
                     {
                         'title': 'OSN Movies Premiere HD',
                         'thumbnail': 'http://www.lyngsat-logo.com/hires/oo/osn_movies_hd.png',
                         'path': 'osn_moies_prem'},
                     {
                         'title': 'Cartoon Network',
                         'thumbnail': 'http://www.teledunet.com//player/icones/cartoon_network.jpg',
                         'path': 'cartoon_network'}]
########NEW FILE########
__FILENAME__ = models
import re


class ChannelItem:
    def __init__(self, el=None, json=None):
        if json is None:
            self.__parseElement(el)
        else:
            self.__parseJSON(json)

    def __parseElement(self, el):
        anchorEl = el.find('a')
        match_channel_name = re.match(r'.*\(\'(.*?)\'.*', anchorEl['onclick'], re.M | re.I)

        self.title = str(anchorEl.findAll('span')[-1].contents[0])  # Copy out channel name, and not reference
        self.thumbnail = anchorEl.find('img')['src']
        if self.thumbnail: self.thumbnail=self.thumbnail.replace('tv_/icones','logo')
        if not self.thumbnail.startswith('http'): self.thumbnail='http://www.teledunet.com/'+self.thumbnail
        self.path = match_channel_name.group(1)
        self.isHD = len(anchorEl.findAll('font')) > 2

    def __parseJSON(self, json):
        self.title = json['title']
        self.thumbnail = json['thumbnail']
        if self.thumbnail: self.thumbnail=self.thumbnail.replace('tv_/icones','logo')
        if not self.thumbnail.startswith('http'): self.thumbnail='http://www.teledunet.com/'+self.thumbnail
        self.path = json['path']
        self.isHD = False

    def display_name(self):
        if self.isHD:
            return '%s [COLOR red]HD[/COLOR]' % self.title

        return self.title


########NEW FILE########
__FILENAME__ = scraper
import cookielib
import re
import urllib2,urllib
from BeautifulSoup import BeautifulSoup
from models import ChannelItem
from hardcode import HARDCODED_STREAMS
import xbmcaddon
#addon_id = 'plugin.video.shahidmbcnet'
selfAddon = xbmcaddon.Addon()

#HEADER_REFERER = 'http://www.teledunet.com/'
HEADER_REFERER = 'http://www.teledunet.com/list_chaines.php'
HEADER_HOST = 'www.teledunet.com'
HEADER_USER_AGENT = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
TELEDUNET_TIMEPLAYER_URL = 'http://www.teledunet.com/mobile/?con'
PPV_CHANNEL_URL='rtmp://5.135.134.110:1935/teledunet/'

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))


def _get(request,post=None):
    """Performs a GET request for the given url and returns the response"""
    return opener.open(request,post).read()

def _html(url):
    """Downloads the resource at the given url and parses via BeautifulSoup"""
    headers = { "User-Agent": HEADER_USER_AGENT  }
    request = urllib2.Request (url , headers = headers)
    return BeautifulSoup(_get(request), convertEntities=BeautifulSoup.HTML_ENTITIES)


def __get_cookie_session():
    # Fetch the main Teledunet website to be given a Session ID
    _html('http://www.teledunet.com/')

    for cookie in cj:
        if cookie.name == 'PHPSESSID':
            return 'PHPSESSID=%s' % cookie.value

    raise Exception('Cannot find PHP session from Teledunet')

def performLogin():
    print 'performing login'
    userName=selfAddon.getSetting( "teledunetTvLogin" )
    password=selfAddon.getSetting( "teledunetTvPassword" )
    req = urllib2.Request('http://www.teledunet.com/boutique/connexion.php')
    req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
    post={'login_user':userName,'pass_user':password}
    post = urllib.urlencode(post)
    link = _get(req,post)

    req = urllib2.Request('http://www.teledunet.com/')#access main page too
    req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
    _get(req,post)


def __get_channel_time_player(channel_name):
    loginname=selfAddon.getSetting( "teledunetTvLogin" )
    
    if not (loginname==None or loginname==""):
        performLogin()
        
    url = TELEDUNET_TIMEPLAYER_URL# % channel_name
    print url
    # Set custom header parameters to simulate request is coming from website
    req = urllib2.Request(url)
    req.add_header('Referer', HEADER_REFERER)
    req.add_header('Host', HEADER_HOST)
    req.add_header('User-agent', HEADER_USER_AGENT)
    req.add_header('Cookie', __get_cookie_session())

    html = _get(req)
    m = re.search('aut=\'\?id0=(.*?)\'', html, re.M | re.I)
    time_player_str = eval(m.group(1))

    
    #print 'set_favoris\(\''+channel_name+'\'.*?rtmp://(.*?)\''
    m = re.search('rtmp://(.*?)/%s\''%channel_name, html, re.M | re.I)
    if  m ==None:
        print 'geting from backup file'
        req = urllib2.Request("https://dl.dropboxusercontent.com/s/ku3n4n53qphqnmn/Frame-code.txt")
        html = _get(req)
        m = re.search('rtmp://(.*?)/%s\''%channel_name, html, re.M | re.I)

    if  m ==None:
        rtmp_url=PPV_CHANNEL_URL+channel_name        
    else:
        rtmp_url = m.group(1)
        rtmp_url='rtmp://%s/%s'%(rtmp_url,channel_name)
    play_path = rtmp_url[rtmp_url.rfind("/") + 1:]
    return rtmp_url, play_path, repr(time_player_str).rstrip('0').rstrip('.')


def get_rtmp_params(channel_name):
    rtmp_url, play_path, time_player_id = __get_channel_time_player(channel_name)

    return {
        'rtmp_url': rtmp_url,
        'playpath': play_path,
        'app': 'teledunet',
        'swf_url': ('http://www.teledunet.com/player.swf?'
                    'id0=%(time_player)s&'
                   ) % {'time_player': time_player_id, 'channel_name': play_path, 'rtmp_url': rtmp_url},
        'video_page_url': 'http://www.teledunet.com/player/?channel=%s conn=N:1 flashVer=WIN12,0,0,77' % play_path,
        'live': '1'
    }

def get_channels():
    html = _html(HEADER_REFERER)
    channel_divs = lambda soup : soup.findAll("div", { "class" : re.compile("div_channel") })
    channels = [ChannelItem(el=el) for el in channel_divs(html)]

    # Extend Teledunet list with custom hardcoded list created by community
    channels.extend(__get_hardcoded_streams())
    return channels


def __get_hardcoded_streams():
    return [ChannelItem(json=json) for json in HARDCODED_STREAMS]


def debug():
    print len(get_channels())
    #print __get_channel_time_player('2m')
    #print get_rtmp_params('2m')
    pass


if __name__ == '__main__':
    debug()
########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from httplib import HTTP
from urlparse import urlparse
import StringIO
import urllib2,urllib
import re
import httplib,itertools
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import cookielib
import time


__settings__ = xbmcaddon.Addon(id='plugin.video.unofficalteledunet')
__icon__ = __settings__.getAddonInfo('icon')
__fanart__ = __settings__.getAddonInfo('fanart')
__language__ = __settings__.getLocalizedString
_thisPlugin = int(sys.argv[1])
_pluginName = (sys.argv[0])
globalIp=''


def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial

    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


def CATEGORIES():
	addDir('All Channels','http://www.teledunet.com/list_chaines.php',1,'http://www.mirrorservice.org/sites/addons.superrepo.org/Frodo/.metadata/plugin.video.teledunet.png')
	
	
	
		
def index(url):
	addLink('MBC','rtmp://5.135.134.110:1935/teledunet/mbc_1',2,'https://si0.twimg.com/profile_images/1133033554/mbc-fb.JPG')
	addLink('MBC DRAMA','rtmp://5.135.134.110:1935/teledunet/mbc_drama',2,'http://www.allied-media.com/ARABTV/images/mbc_drama.jpg')
	addLink('JSC +1','rtmp://5.135.134.110:1935/teledunet/jsc_1',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +2','rtmp://5.135.134.110:1935/teledunet/jsc_2',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +3','rtmp://5.135.134.110:1935/teledunet/jsc_3',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +4','rtmp://5.135.134.110:1935/teledunet/jsc_4',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +5','rtmp://5.135.134.110:1935/teledunet/jsc_5',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +6','rtmp://5.135.134.110:1935/teledunet/jsc_6',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +7','rtmp://5.135.134.110:1935/teledunet/jsc_7',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +8','rtmp://5.135.134.110:1935/teledunet/jsc_8',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +9','rtmp://5.135.134.110:1935/teledunet/jsc_9',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC +10','rtmp://5.135.134.110:1935/teledunet/jsc_10',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('JSC 1 HD','rtmp://5.135.134.110:1935/teledunet/tele_1_hd',2,'')
	addLink('JSC 2 HD','rtmp://5.135.134.110:1935/teledunet/tele_2_hd',2,'')
	addLink('JSC 3 HD','rtmp://5.135.134.110:1935/teledunet/tele_3_hd',2,'')
	addLink('JSC 4 HD','rtmp://5.135.134.110:1935/teledunet/tele_4_hd',2,'')
	addLink('Abu Dhabi Al Oula','rtmp://5.135.134.110:1935/teledunet/abu_dhabi',2,'https://www.zawya.com/pr/images/2009/ADTV_One_RGB_2009_10_08.jpg')
	addLink('Abu Dhabi Sports','rtmp://5.135.134.110:1935/teledunet/abu_dhabi_sports_1',2,'https://si0.twimg.com/profile_images/2485587448/2121.png')
	addLink('Al Jazeera','rtmp://5.135.134.110:1935/teledunet/aljazeera',2,'http://www.chicagonow.com/chicago-sports-media-watch/files/2013/04/Al-Jazeera.jpg')
	addLink('Al Jazeera Sport Global','rtmp://5.135.134.110:1935/teledunet/aljazeera_sport_global',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('Al Jazeera Sport 1','rtmp://5.135.134.110:1935/teledunet/aljazeera_sport_1',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('Al Jazeera Sport 2','rtmp://5.135.134.110:1935/teledunet/aljazeera_sport_2',2,'http://nowwatchtvlive.com/wp-content/uploads/2011/07/AljazeeraSport-264x300.jpg')
	addLink('Al Jazeera Mubasher Masr','rtmp://5.135.134.110:1935/teledunet/aljazeera_mubasher_masr',2,'http://www.chicagonow.com/chicago-sports-media-watch/files/2013/04/Al-Jazeera.jpg')
	addLink('Al Jazeera Children','rtmp://5.135.134.110:1935/teledunet/aljazeera_children',2,'http://3.bp.blogspot.com/-UX1XBY8-02g/Uoku7OTIrFI/AAAAAAAAASk/-0eEX7fumJw/s1600/al_jazeera_children.png')
	addLink('Al Jazeera Documentation','rtmp://5.135.134.110:1935/teledunet/aljazeera_doc',2,'http://upload.wikimedia.org/wikipedia/en/e/e6/Al_Jazeera_Doc.png')
	addLink('ART Cinema','rtmp://5.135.134.110:1935/teledunet/art_aflam_1',2,'http://www.lyngsat-logo.com/hires/aa/art_cinema.png')
	addLink('ART Aflam 2','rtmp://5.135.134.110:1935/teledunet/art_aflam_2',2,'http://www.invision.com.sa/en/sites/default/files/imagecache/216x216/channels/2011/10/11/1138.jpg')
	addLink('Cartoon Network','rtmp://5.135.134.110:1935/teledunet/cartoon_network',2,'http://upload.wikimedia.org/wikipedia/commons/b/bb/Cartoon_Network_Arabic_logo.png')
	addLink('MTV Lebanon','rtmp://5.135.134.110:1935/teledunet/mtv',2,'http://mtv.com.lb/images/mtv-social-logo1.jpg')
	addLink('AlJadeed','rtmp://5.135.134.110:1935/teledunet/aljaded_sat',2,'')
	addLink('NBN','rtmp://5.135.134.110:1935/teledunet/nbn',2,'http://upload.wikimedia.org/wikipedia/en/1/14/Nbn_lebanon.png')
	addLink('Otv Lebanon','rtmp://5.135.134.110:1935/teledunet/otv_lebanon',2,'http://www.worldmedia.com.au/Portals/0/Images/Logo_s/otv.png')
	addLink('Al Hayat','rtmp://5.135.134.110:1935/teledunet/alhayat_1',2,'http://3.bp.blogspot.com/--uP1DsoBB7s/T4EMosYH5uI/AAAAAAAAF9E/RdbY8-E3Riw/s320/Al%2Bhayat.jpg')
	addLink('Al Hayat Cinema','rtmp://5.135.134.110:1935/teledunet/alhayat_cinema',2,'http://www.lyngsat-logo.com/hires/aa/alhayat_cinema.png')
	addLink('Alarabiya','rtmp://5.135.134.110:1935/teledunet/alarabiya',2,'http://www.debbieschlussel.com/archives/alarabiya2.jpg')
	addLink('Tele Sports','rtmp://5.135.134.110:1935/teledunet/tele_sports',2,'http://www.itwebsystems.co.uk/resources/icon.png')
	addLink('Noursat','rtmp://5.135.134.110:1935/teledunet/noursat',2,'')
	addLink('TF1','rtmp://5.135.134.110:1935/teledunet/tf1',2,'')
	addLink('Al Masriyah','rtmp://5.135.134.110:1935/teledunet/al_masriyah',2,'')
	addLink('Iqra','rtmp://5.135.134.110:1935/teledunet/Iqra',2,'')
	addLink('Canal Plus','rtmp://5.135.134.110:1935/teledunet/canal_plus',2,'')
	addLink('Euro SPort 1','rtmp://5.135.134.110:1935/teledunet/euro_sport_1',2,'')
	addLink('France 2','rtmp://5.135.134.110:1935/teledunet/france_2',2,'')
	addLink('Melody Arabia','rtmp://5.135.134.110:1935/teledunet/melody',2,'')
    
	url="http://www.teledunet.com/list_chaines.php"
	req = urllib2.Request(url)
	req.add_header('Host', 'www.teledunet.com')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0')
	req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
	req.add_header('Accept-Encoding', 'gzip, deflate')
	req.add_header('Referer', 'http://www.teledunet.com/')
	req.add_header('Cookie', str(getCookies(url)))
	req.add_header('Connection', 'keep-alive')
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
	response = urllib2.urlopen(req)
	link=response.read()
	
	response.close()
	style=(re.compile('<div  id="(.+?)class=div_channel>').findall(link))
	#print style
	image=(re.compile('<img onerror="(.+?)src="(.+?)" height=').findall(link))
	
	
	nameUrl=(re.compile('onclick="set_favoris(.+?);" style=').findall(link))
	
	imgArray=[]
	colorArray=[]
	nameArray=[]
	pathArray=[]
	
	
	for itemNameUrl in nameUrl:
		myItems=str(itemNameUrl).split(',')
		
		name=str(myItems[1]).replace("'",'').strip()
		print name
		path=str(myItems[2]).replace("'",'').replace(")",'').strip()
		print path
		nameArray.append(name) 
		pathArray.append(path) 
    
	for itemsImg in  image:
		myImage="http://www.teledunet.com/"+str( itemsImg[1] )
		print 
		imgArray.append(myImage) 
	
	for (names,images,paths) in itertools.izip (nameArray,imgArray,pathArray):
		
		addLink(names,paths,2,images)
	

def getCookies(url):

    #Create a CookieJar object to hold the cookies
    cj = cookielib.CookieJar()
    #Create an opener to open pages using the http protocol and to process cookies.
    opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())
    #create a request object to be used to get the page.
    req = urllib2.Request(url)
    req.add_header('Host', 'www.teledunet.com')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Referer', 'http://www.teledunet.com/')
    req.add_header('Connection', 'keep-alive')
    f = opener.open(req)
    #see the first few lines of the page
    cj=str(cj).replace('<cookielib.CookieJar[<Cookie', '').replace('/>]>', '').replace('for www.teledunet.com', '')
    cj=str(cj).strip()
    return cj


def getId(channel):
    url="http://www.teledunet.com/tv_/?channel="+str(channel)
    req = urllib2.Request(url)
    req.add_header('Host', 'www.teledunet.com')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0')
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Referer', 'http://www.teledunet.com/')
    req.add_header('Cookie', str(getCookies(url)))
    req.add_header('Connection', 'keep-alive')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    nameUrl=(re.compile('time_player=(.+?);').findall(link))
    nameUrl=str( nameUrl).replace("['", '').replace("']", '').replace(".","").replace("E+13","00").strip()
    return nameUrl
	
                    
def PlayChannels(url):
	firstPart=str(url).split('teledunet/')[1]
	print str(url).split('teledunet/')
	finalPayPath=url+' app=teledunet swfUrl=http://www.teledunet.com/tv/player.swf?bufferlength=5&repeat=single&autostart=true&id0='+str(getId(firstPart))+'&streamer='+str(url)+'&file='+str(firstPart)+'&provider=rtmp playpath='+str(firstPart)+' live=1 pageUrl=http://www.teledunet.com/tv/?channel='+str(firstPart)+'&no_pub'
	listItem = xbmcgui.ListItem(path=str(finalPayPath))
	xbmcplugin.setResolvedUrl(_thisPlugin, True, listItem)
	
	
		
def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param





def addLink(name,url,mode,iconimage):
    u=_pluginName+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty("IsPlayable","true");
    ok=xbmcplugin.addDirectoryItem(handle=_thisPlugin,url=u,listitem=liz,isFolder=False)
    return ok
	


def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

              
params=get_params()
url=None
name=None
mode=None


	
try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
        print ""
        CATEGORIES()
       
elif mode==1:
        print ""+url
        index(url)
	
elif mode==2:
        print ""+url
        PlayChannels(url)



xbmcplugin.endOfDirectory(int(sys.argv[1]))

########NEW FILE########
