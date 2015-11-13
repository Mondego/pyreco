__FILENAME__ = app
import xbmc
xbmc.executebuiltin("RunApp(app://tv.boxee.grooveshark)")
########NEW FILE########
__FILENAME__ = app
import xbmc
xbmc.executebuiltin("RunApp(app://pandora)")
########NEW FILE########
__FILENAME__ = app
import xbmc
xbmc.executebuiltin("RunApp(app://spotify)")
########NEW FILE########
__FILENAME__ = default
import sys
import os
import xbmcgui
import xbmc
import string

__scriptname__ = "OpenSubtitles"
__author__ = "Leo"
__url__ = ""
__svn_url__ = ""
__credits__ = "Leo"
__version__ = "1.0"

BASE_RESOURCE_PATH = os.path.join( os.getcwd().replace( ";", "" ), "resources" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
import language
__language__ = language.Language().localized

if ( __name__ == "__main__" ):

	import gui
	window = "main"

	search_string = ""
	path_string = ""
	type = "file"
	if len( sys.argv ) > 1:
		tmp_string = sys.argv[1]
		tmp_string.strip()
		path_string = tmp_string[tmp_string.find( "[PATH]" ) + len( "[PATH]" ):tmp_string.find( "[/PATH]" )]
		if ( tmp_string.find( "[MOVIE]" ) > -1 ):
			search_string = tmp_string[tmp_string.find( "[MOVIE]" ) + len( "[MOVIE]" ):tmp_string.find( "[/MOVIE]" )]
			tmp_list = search_string.split()
			search_string = string.join( tmp_list, '+' )
			type = "movie"
		elif ( tmp_string.find( "[TV]" ) > -1 ):
			search_string = tmp_string[tmp_string.find( "[TV]" ) + len( "[TV]" ):tmp_string.find( "[/TV]" )]			
			tmp_list = search_string.split()
			tmp_string = tmp_list.pop( 0 )
			if ( int( tmp_string ) < 10 ):
				search_string = "S0" + tmp_string
			else:
				search_string = "S" + tmp_string
			tmp_string = tmp_list.pop( 0 )
			if ( int( tmp_string ) < 10 ):
				search_string = search_string + "E0" + tmp_string
			else:
				search_string = search_string + "E" + tmp_string
			search_string = search_string + "+" + string.join( tmp_list, '+' )
			type = "tv"

	ui = gui.GUI( "script-%s-%s.xml" % ( __scriptname__.replace( " ", "_" ), window, ), os.getcwd(), "Boxee")
	ui.set_filepath( path_string )
	ui.set_searchstring( search_string )
	ui.set_type( type )
	ui.doModal()
	del ui

########NEW FILE########
__FILENAME__ = gui
import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import threading
import socket
import urllib
from Queue import Queue
import plugins
import ConfigParser
import logging
import difflib

try: current_dlg_id = xbmcgui.getCurrentWindowDialogId()
except: current_dlg_id = 0
current_win_id = xbmcgui.getCurrentWindowId()

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__

STATUS_LABEL = 100
LOADING_IMAGE = 110
SUBTITLES_LIST = 120

trans_lang = {'aa' : 'Afar',
'ab' : 'Abkhaz',
'ae' : 'Avestan',
'af' : 'Afrikaans',
'ak' : 'Akan',
'am' : 'Amharic',
'an' : 'Aragonese',
'ar' : 'Arabic',
'as' : 'Assamese',
'av' : 'Avaric',
'ay' : 'Aymara',
'az' : 'Azerbaijani',
'ba' : 'Bashkir',
'be' : 'Belarusian',
'bg' : 'Bulgarian',
'bh' : 'Bihari',
'bi' : 'Bislama',
'bm' : 'Bambara',
'bn' : 'Bengali',
'bo' : 'Tibetan',
'br' : 'Breton',
'bs' : 'Bosnian',
'ca' : 'Catalan',
'ce' : 'Chechen',
'ch' : 'Chamorro',
'co' : 'Corsican',
'cr' : 'Cree',
'cs' : 'Czech',
'cu' : 'Old Church Slavonic',
'cv' : 'Chuvash',
'cy' : 'Welsh',
'da' : 'Danish',
'de' : 'German',
'dv' : 'Divehi',
'dz' : 'Dzongkha',
'ee' : 'Ewe',
'el' : 'Greek',
'en' : 'English',
'eo' : 'Esperanto',
'es' : 'Spanish',
'et' : 'Estonian',
'eu' : 'Basque',
'fa' : 'Persian',
'ff' : 'Fula',
'fi' : 'Finnish',
'fj' : 'Fijian',
'fo' : 'Faroese',
'fr' : 'French',
'fy' : 'Western Frisian',
'ga' : 'Irish',
'gd' : 'Scottish Gaelic',
'gl' : 'Galician',
'gn' : 'Guaraní',
'gu' : 'Gujarati',
'gv' : 'Manx',
'ha' : 'Hausa',
'he' : 'Hebrew',
'hi' : 'Hindi',
'ho' : 'Hiri Motu',
'hr' : 'Croatian',
'ht' : 'Haitian',
'hu' : 'Hungarian',
'hy' : 'Armenian',
'hz' : 'Herero',
'ia' : 'Interlingua',
'id' : 'Indonesian',
'ie' : 'Interlingue',
'ig' : 'Igbo',
'ii' : 'Nuosu',
'ik' : 'Inupiaq',
'io' : 'Ido',
'is' : 'Icelandic',
'it' : 'Italian',
'iu' : 'Inuktitut',
'ja' : 'Japanese (ja)',
'jv' : 'Javanese (jv)',
'ka' : 'Georgian',
'kg' : 'Kongo',
'ki' : 'Kikuyu',
'kj' : 'Kwanyama',
'kk' : 'Kazakh',
'kl' : 'Kalaallisut',
'km' : 'Khmer',
'kn' : 'Kannada',
'ko' : 'Korean',
'kr' : 'Kanuri',
'ks' : 'Kashmiri',
'ku' : 'Kurdish',
'kv' : 'Komi',
'kw' : 'Cornish',
'ky' : 'Kirghiz, Kyrgyz',
'la' : 'Latin',
'lb' : 'Luxembourgish',
'lg' : 'Luganda',
'li' : 'Limburgish',
'ln' : 'Lingala',
'lo' : 'Lao',
'lt' : 'Lithuanian',
'lu' : 'Luba-Katanga',
'lv' : 'Latvian',
'mg' : 'Malagasy',
'mh' : 'Marshallese',
'mi' : 'Maori',
'mk' : 'Macedonian',
'ml' : 'Malayalam',
'mn' : 'Mongolian',
'mr' : 'Marathi',
'ms' : 'Malay',
'mt' : 'Maltese',
'my' : 'Burmese',
'na' : 'Nauru',
'nb' : 'Norwegian',
'nd' : 'North Ndebele',
'ne' : 'Nepali',
'ng' : 'Ndonga',
'nl' : 'Dutch',
'nn' : 'Norwegian Nynorsk',
'no' : 'Norwegian',
'nr' : 'South Ndebele',
'nv' : 'Navajo, Navaho',
'ny' : 'Chichewa; Chewa; Nyanja',
'oc' : 'Occitan',
'oj' : 'Ojibwe, Ojibwa',
'om' : 'Oromo',
'or' : 'Oriya',
'os' : 'Ossetian, Ossetic',
'pa' : 'Panjabi, Punjabi',
'pi' : 'Pali',
'pl' : 'Polish',
'ps' : 'Pashto, Pushto',
'pt' : 'Portuguese',
'pb' : 'Brazilian',
'qu' : 'Quechua',
'rm' : 'Romansh',
'rn' : 'Kirundi',
'ro' : 'Romanian',
'ru' : 'Russian',
'rw' : 'Kinyarwanda',
'sa' : 'Sanskrit',
'sc' : 'Sardinian',
'sd' : 'Sindhi',
'se' : 'Northern Sami',
'sg' : 'Sango',
'si' : 'Sinhala, Sinhalese',
'sk' : 'Slovak',
'sl' : 'Slovene',
'sm' : 'Samoan',
'sn' : 'Shona',
'so' : 'Somali',
'sq' : 'Albanian',
'sr' : 'Serbian',
'ss' : 'Swati',
'st' : 'Southern Sotho',
'su' : 'Sundanese',
'sv' : 'Swedish',
'sw' : 'Swahili',
'ta' : 'Tamil',
'te' : 'Telugu',
'tg' : 'Tajik',
'th' : 'Thai',
'ti' : 'Tigrinya',
'tk' : 'Turkmen',
'tl' : 'Tagalog',
'tn' : 'Tswana',
'to' : 'Tonga',
'tr' : 'Turkish',
'ts' : 'Tsonga',
'tt' : 'Tatar',
'tw' : 'Twi',
'ty' : 'Tahitian',
'ug' : 'Uighur',
'uk' : 'Ukrainian',
'ur' : 'Urdu',
'uz' : 'Uzbek',
've' : 'Venda',
'vi' : 'Vietnamese',
'vo' : 'Volapük',
'wa' : 'Walloon',
'wo' : 'Wolof',
'xh' : 'Xhosa',
'yi' : 'Yiddish',
'yo' : 'Yoruba',
'za' : 'Zhuang, Chuang',
'zh' : 'Chinese',
'zu' : 'Zulu' }


SELECT_ITEM = ( 11, 256, 61453, )

EXIT_SCRIPT = ( 10, 247, 275, 61467, 216, 257, 61448, )

CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )

GET_EXCEPTION = ( 216, 260, 61448, )

SELECT_BUTTON = ( 229, 259, 261, 61453, )

MOVEMENT_UP = ( 166, 270, 61478, )

MOVEMENT_DOWN = ( 167, 271, 61480, )

DEBUG_MODE = 5

# Log status codes
LOG_INFO, LOG_ERROR, LOG_NOTICE, LOG_DEBUG = range( 1, 5 )

def LOG( status, format, *args ):
    if ( DEBUG_MODE >= status ):
        xbmc.output( "%s: %s\n" % ( ( "INFO", "ERROR", "NOTICE", "DEBUG", )[ status - 1 ], format % args, ) )

def sort_inner(inner):
	if("hash" in inner and inner["hash"] == True):
		return 100
	return inner["percent"]

class GUI( xbmcgui.WindowXMLDialog ):
    socket.setdefaulttimeout(10.0) #seconds
	
    def __init__( self, *args, **kwargs ):
        pass

    def set_filepath( self, path ):
        LOG( LOG_INFO, "set_filepath [%s]" , ( path ) )
        self.file_original_path = path
        self.file_path = path[path.find(os.sep):len(path)]

    def set_filehash( self, hash ):
        LOG( LOG_INFO, "set_filehash [%s]" , ( hash ) )
        self.file_hash = hash

    def set_filesize( self, size ):
        LOG( LOG_INFO, "set_filesize [%s]" , ( size ) )
        self.file_size = size

    def set_searchstring( self, search ):
        LOG( LOG_INFO, "set_searchstring [%s]" , ( search ) )
        self.search_string = search
    
    def set_type( self, type ):
	self.file_type = type

    def onInit( self ):
        LOG( LOG_INFO, "onInit" )
        self.setup_all()
        if self.file_path:
            self.connThread = threading.Thread( target=self.connect, args=() )
            self.connThread.start()
        
    def setup_all( self ):
        self.setup_variables()
        
    def setup_variables( self ):
        self.controlId = -1
        self.allow_exception = False
        if xbmc.Player().isPlayingVideo():
            self.set_filepath( xbmc.Player().getPlayingFile() )

    def connect( self ):
	self.setup_all()
        logging.basicConfig()
	self.getControl( LOADING_IMAGE ).setVisible( True )
        self.getControl( STATUS_LABEL ).setLabel( "Searching" )
	sub_filename = os.path.basename(self.file_original_path)
	title = sub_filename[0:sub_filename.rfind(".")]
	self.getControl( 180 ).setLabel("[B][UPPERCASE]$LOCALIZE[293]:[/B] " + title + "[/UPPERCASE]");
	langs = None
	subtitles = []
	q = Queue()
	self.config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })
	basepath = "/data/etc" # os.path.dirname(__file__)
	self.config.read(basepath + "/.subtitles")
		
	config_plugins = self.config.get("DEFAULT", "plugins")
	if(self.file_type == "tv"):
		config_plugins = self.config.get("DEFAULT", "tvplugins")
	elif(self.file_type == "movie"):
		config_plugins = self.config.get("DEFAULT", "movieplugins")

	use_plugins = map(lambda x : x.strip(), config_plugins.split(","))

	config_langs = self.config.get("DEFAULT", "lang") 
	if(config_langs != "All" and config_langs != ""):
		use_langs = map(lambda x : x.strip(), config_langs.split(","))
	else:
		use_langs = None

	for name in use_plugins:
	    filep = self.file_original_path
            try :
                plugin = getattr(plugins, name)(self.config, '/data/hack/cache')
                LOG( LOG_INFO, "Searching on %s ", (name) )
                thread = threading.Thread(target=plugin.searchInThread, args=(q, str(filep), use_langs))
                thread.start()
            except ImportError, (e) :
		LOG( LOG_INFO, "Plugin %s is not a valid plugin name. Skipping it.", ( e) )		

        # Get data from the queue and wait till we have a result
        count = 0
        for name in use_plugins:
            subs = q.get(True)
	    count = count + 1
	    self.getControl( STATUS_LABEL ).setLabel( "Searching " + str(count) + "/" + str(len(use_plugins)) )
            if subs and len(subs) > 0:
                if not use_langs:
                    subtitles += subs
                else:
                    for sub in subs:
			lang_code = sub["lang"]
			if(lang_code == "pt-br"):
                                lang_code = "pb"
                        if lang_code in use_langs:
                            subtitles += [sub]
	
	if(len(subtitles) > 0):
		self.sublist = subtitles
		for item in subtitles:
			sub_filename = os.path.basename( self.file_original_path )
                	sub_filename = sub_filename[0:sub_filename.rfind(".")]
			percent = (round(difflib.SequenceMatcher(None, sub_filename, item["release"]).ratio(), 2) * 100)
			item["percent"] = percent
		subtitles.sort(key=sort_inner,reverse=True)	
		for item in subtitles:
			if(item["lang"] and item["release"]):
				if(item["lang"] == "pt-br"):
					item["lang"] = "pb"
				if(item["lang"] in trans_lang):
					language = trans_lang[item["lang"]]
				else:
					language = item["lang"]
                    		listitem = xbmcgui.ListItem( label=language, label2=item["release"], iconImage="0.0", thumbnailImage="flags/" + item["lang"] + ".png" )
                    		listitem.setProperty( "source", str(item["plugin"].__class__.__name__))
				listitem.setProperty( "release", item["release"])
		        	listitem.setProperty( "equals", str(item["percent"]) + "%")
				if("hash" in item and item["hash"] == True):
        	                	listitem.setProperty( "sync", "true" )
	                	else:
            	        		listitem.setProperty( "sync", "false" )
	
				self.getControl( SUBTITLES_LIST ).addItem( listitem )
							
        self.setFocus( self.getControl( SUBTITLES_LIST ) )
	self.getControl( SUBTITLES_LIST ).selectItem( 0 )
	self.getControl( LOADING_IMAGE ).setVisible( False )
        self.getControl( STATUS_LABEL ).setVisible( False )
        
    def download_subtitles(self, pos):
	if self.sublist:
	    item = self.sublist[pos]
	    ok = xbmcgui.Dialog().yesno( "BoxeeSubs", _( 242 ), ( _( 243 ) % ( item["release"], ) ), "", _( 260 ), _( 259 ) )
            if not ok:
                self.getControl( STATUS_LABEL ).setLabel( _( 645 ) )
                return
            else:
		local_path = xbmc.translatePath("special://home/subtitles")
		dp = xbmcgui.DialogProgress()
		dp.create( __scriptname__, _( 633 ), os.path.basename( self.file_path ) )
		sub_filename = os.path.basename( self.file_path )
		sub_filename = sub_filename[0:sub_filename.rfind(".")] + "." + item["lang"] + ".srt"
		item["plugin"].downloadFile(item["link"], os.path.join( local_path, sub_filename ))
		dp.close()
		xbmc.Player().setSubtitles( os.path.join( local_path, sub_filename ) )
		xbmc.showNotification( 652, '', '' )
		self.getControl( STATUS_LABEL ).setLabel( _( 652 ) )
		
            self.getControl( STATUS_LABEL ).setLabel( _( 649 ) )
            self.exit_script()

    def exit_script( self, restart=False ):
        self.connThread.join()
        self.close()

    def onClick( self, controlId ):
        if ( self.controlId == SUBTITLES_LIST ):
            self.download_subtitles( self.getControl( SUBTITLES_LIST ).getSelectedPosition() )

    def onFocus( self, controlId ):
        self.controlId = controlId

    def onAction( self, action ):
        try:
                if ( action.getButtonCode() in CANCEL_DIALOG ):
                    self.exit_script()
        except:
                self.exit_script()


########NEW FILE########
__FILENAME__ = language
"""
Language module

Nuka1195
"""

import os
import xbmc
import xml.dom.minidom


class Language:
    """ Language Class: creates a dictionary of localized strings { int: string } """
    def __init__( self ):
        """ initializer """
        # language folder
        base_path = os.path.join( os.getcwd().replace( ";", "" ), "resources", "language" )
        # get the current language
        language = self._get_language( base_path )
        # create strings dictionary
        self._create_localized_dict( base_path, language )
        
    def _get_language( self, base_path ):
        """ returns the current language if a strings.xml file exists else returns english """
        # get the current users language setting
        language = xbmc.getLanguage().lower()
        # if no strings.xml file exists, default to english
        if ( not os.path.isfile( os.path.join( base_path, language, "strings.xml" ) ) ):
            language = "english"
        return language

    def _create_localized_dict( self, base_path, language ):
        """ initializes self.strings and calls _parse_strings_file """
        # localized strings dictionary
        self.strings = {}
        # add localized strings
        self._parse_strings_file( os.path.join( base_path, language, "strings.xml" ) )
        # fill-in missing strings with english strings
        if ( language != "english" ):
            self._parse_strings_file( os.path.join( base_path, "english", "strings.xml" ) )
        
    def _parse_strings_file( self, language_path ):
        """ adds localized strings to self.strings dictionary """
        try:
            # load and parse strings.xml file
            doc = xml.dom.minidom.parse( language_path )
            # make sure this is a valid <strings> xml file
            root = doc.documentElement
            if ( not root or root.tagName != "strings" ): raise
            # parse and resolve each <string id="#"> tag
            strings = root.getElementsByTagName( "string" )
            for string in strings:
                # convert id attribute to an integer
                string_id = int( string.getAttribute( "id" ) )
                # if a valid id add it to self.strings dictionary
                if ( string_id not in self.strings and string.hasChildNodes() ):
                    self.strings[ string_id ] = string.firstChild.nodeValue
        except:
            # print the error message to the log and debug window
            xbmc.output( "ERROR: Language file %s can't be parsed!" % ( language_path, ) )
        # clean-up document object
        try: doc.unlink()
        except: pass

    def localized( self, code ):
        """ returns the localized string if it exists """
        return self.strings.get( code, "Invailid Id %d" % ( code, ) )

########NEW FILE########
__FILENAME__ = Addic7ed
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import zipfile, os, urllib2, urllib, logging, traceback, httplib, re, socket
from BeautifulSoup import BeautifulSoup

import SubtitleDatabase

LANGUAGES = {u"English" : "en",
			 u"English (US)" : "en",
			 u"English (UK)" : "en",
			 u"Italian" : "it",
			 u"Portuguese" : "pt",
			 u"Portuguese (Brazilian)" : "pt-br",
			 u"Romanian" : "ro",
			 u"Español (Latinoamérica)" : "es",
			 u"Español (España)" : "es",
			 u"Spanish (Latin America)" : "es",
			 u"Español" : "es",
			 u"Spanish" : "es",
			 u"Spanish (Spain)" : "es",
			 u"French" : "fr",
			 u"Greek" : "el",
			 u"Arabic" : "ar",
			 u"German" : "de",
			 u"Croatian" : "hr",
			 u"Indonesian" : "id",
			 u"Hebrew" : "he",
			 u"Russian" : "ru",
			 u"Turkish" : "tr",
			 u"Swedish" : "se",
			 u"Czech" : "cs",
			 u"Dutch" : "nl",
			 u"Hungarian" : "hu",
			 u"Norwegian" : "no",
			 u"Polish" : "pl",
			 u"Persian" : "fa"}

class Addic7ed(SubtitleDatabase.SubtitleDB):
	url = "http://www.addic7ed.com"
	site_name = "Addic7ed"

	def __init__(self, config, cache_folder_path):
		super(Addic7ed, self).__init__(langs=None,revertlangs=LANGUAGES)
		#http://www.addic7ed.com/serie/Smallville/9/11/Absolute_Justice
		self.host = "http://www.addic7ed.com"
		self.release_pattern = re.compile(" \nVersion (.+), ([0-9]+).([0-9])+ MBs")
		

	def process(self, filepath, langs):
		''' main method to call on the plugin, pass the filename and the wished 
		languages and it will query the subtitles source '''
		fname = unicode(self.getFileName(filepath).lower())
		guessedData = self.guessFileData(fname)
		if guessedData['type'] == 'tvshow':
			subs = self.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], langs)
			return subs
		else:
			return []
	
	def query(self, name, season, episode, teams, langs=None):
		''' makes a query and returns info (link, lang) about found subtitles'''
		sublinks = []
		name = name.lower().replace(" ", "_")
		searchurl = "%s/serie/%s/%s/%s/%s" %(self.host, name, season, episode, name)
		logging.debug("dl'ing %s" %searchurl)
		try:
			socket.setdefaulttimeout(3)
			page = urllib2.urlopen(searchurl)
		except urllib2.HTTPError, (inst):
			logging.info("Error : %s - %s" %(searchurl, inst))
			return sublinks
		except urllib2.URLError, (inst):
			logging.info("TimeOut : %s" %inst)
			return sublinks
		
		#HTML bug in addic7ed
		content = page.read()
		content = content.replace("The safer, easier way", "The safer, easier way \" />")
		soup = BeautifulSoup(content)
		for subs in soup("td", {"class":"NewsTitle", "colspan" : "3"}):
			if not self.release_pattern.match(str(subs.contents[1])):
				continue
			subteams = self.release_pattern.match(str(subs.contents[1])).groups()[0].lower()
			# Addic7ed only takes the real team	into account
			fteams = []
			for team in teams:
				fteams += team.split("-")
			teams = set(fteams)
			subteams = self.listTeams([subteams], [".", "_", " "])
			logging.debug("[Addic7ed] Team from website: %s" %subteams)
			logging.debug("[Addic7ed] Team from file: %s" %teams)
			logging.debug("[Addic7ed] match ? %s" %subteams.issubset(teams))
			langs_html = subs.findNext("td", {"class" : "language"})
			
			p = re.compile('Works with (.*)')
			works_with = subs.findNext("td", {"class" : "newsDate"})
			works_with = works_with.contents[0].encode('utf-8').strip()
			works_with_match = p.findall(works_with)
			
			
			lang = self.getLG(langs_html.contents[0].strip().replace('&nbsp;', ''))
			#logging.debug("[Addic7ed] Language : %s - lang : %s" %(langs_html, lang))
			statusTD = langs_html.findNext("td")
			
			status = statusTD.find("b").string.strip()
			# take the last one (most updated if it exists)
			links = statusTD.findNext("td").findAll("a")
			link = "%s%s"%(self.host,links[len(links)-1]["href"])
			#logging.debug("%s - match : %s - lang : %s" %(status == "Completed", subteams.issubset(teams), (not langs or lang in langs)))
			if status == "Completed" and (not langs or lang in langs) :
				result = {}
				result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("_", ".").title(), int(season), int(episode), '.'.join(subteams)
)
				if(len(works_with_match) > 0):
					result["release"] = result["release"].decode('utf-8').strip() + " / " + works_with_match[0].decode('utf-8').strip()
				result["lang"] = lang
				result["link"] = link
				result["page"] = searchurl
				sublinks.append(result)
		return sublinks
		
	def listTeams(self, subteams, separators):
		teams = []
		for sep in separators:
			subteams = self.splitTeam(subteams, sep)
		#logging.debug(subteams)
		return set(subteams)
	
	def splitTeam(self, subteams, sep):
		teams = []
		for t in subteams:
			teams += t.split(sep)
		return teams

	def createFile(self, subtitle):
		'''pass the URL of the sub and the file it matches, will unzip it
		and return the path to the created file'''
		suburl = subtitle["link"]
		videofilename = subtitle["filename"]
		srtbasefilename = videofilename.rsplit(".", 1)[0]
		srtfilename = srtbasefilename +".srt"
		self.downloadFile(suburl, srtfilename)
		return srtfilename

	def downloadFile(self, url, srtfilename):
		''' Downloads the given url to the given filename '''
		req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
		
		f = urllib2.urlopen(req)
		dump = open(srtfilename, "wb")
		dump.write(f.read())
		dump.close()
		f.close()
		logging.debug("Download finished to file %s. Size : %s"%(srtfilename,os.path.getsize(srtfilename)))

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2010, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.2.1"
__copyright__ = "Copyright (c) 2004-2012 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        # (Possibly) special case some findAll*(...) searches
        elif text is None and not limit and not attrs and not kwargs:
            # findAll*(True)
            if name is True:
                return [element for element in generator()
                        if isinstance(element, Tag)]
            # findAll*('tag-name')
            elif isinstance(name, basestring):
                return [element for element in generator()
                        if isinstance(element, Tag) and
                        element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        # Build a SoupStrainer
        else:
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"


class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        # Substitute outgoing XML entities.
        data = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, self)
        if encoding:
            return data.encode(encoding)
        else:
            return data

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs is None:
            attrs = []
        elif isinstance(attrs, dict):
            attrs = attrs.items()
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if other is self:
            return True
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isinstance(val, basestring):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif hasattr(portion, '__iter__'): # is a list
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not hasattr(self.markupMassage, "__iter__"):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript',)

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if isinstance(sub, tuple):
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = BierDopje
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import urllib
import urllib2
import logging
import os
import xbmc
import pickle
from xml.dom import minidom
import ConfigParser

import SubtitleDatabase
import version

log = logging.getLogger(__name__)

exceptions = {
    'the office' : 10358,
    'the office us' : 10358,
    'greys anatomy' : 3733,
    'sanctuary us' : 7904,
    'human target 2010' : 12986,
    'csi miami' : 2187,
    'castle 2009' : 12708,
    'chase 2010' : 14228,
    'the defenders 2010' : 14225,
    'hawaii five-0 2010' : 14211,
}

class BierDopje(SubtitleDatabase.SubtitleDB):
    url = "http://bierdopje.com/"
    site_name = "BierDopje"

    def __init__(self, config, cache_folder_path):
        super(BierDopje, self).__init__(None)
        #http://api.bierdopje.com/23459DC262C0A742/GetShowByName/30+Rock
        #http://api.bierdopje.com/23459DC262C0A742/GetAllSubsFor/94/5/1/en (30 rock, season 5, episode 1)
        self.api = None
        try:
            key = config.get("BierDopje", "key") # You need to ask for it
            self.api = "http://api.bierdopje.com/%s/" %key
        except ConfigParser.NoSectionError:
            return
        self.headers = {'User-Agent' : 'BoxeeSubs/1.0'}
        self.cache_path = os.path.join(cache_folder_path, "bierdopje.cache")
        if not os.path.exists(cache_folder_path):
	    os.makedirs(cache_folder_path)
	if not os.path.exists(self.cache_path):
            log.info("Creating cache file %s" % self.cache_path)
            f = open(self.cache_path, 'w')
            pickle.dump({'showids' : {}}, f)
            f.close()
        f = open(self.cache_path, 'r')
        self.cache = pickle.load(f)
        f.close()

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = self.getFileName(filepath)
        try:
            subs = self.query(fname, langs)
            if not subs and fname.rfind(".[") > 0:
                # Try to remove the [VTV] or [EZTV] at the end of the file
                teamless_filename = fname[0 : fname.rfind(".[")]
                subs = self.query(teamless_filename, langs)
                return subs
            else:
                return subs
        except Exception, e:
            log.exception("Error raised by plugin")
            return []
            
    def createFile(self, subtitle):
        '''get the URL of the sub, download it and return the path to the created file'''
        sublink = subtitle["link"]
        subpath = subtitle["filename"].rsplit(".", 1)[0] + '.srt'
        self.downloadFile(sublink, subpath)
        return subpath
    
    def query(self, token, langs=None):
        ''' makes a query and returns info (link, lang) about found subtitles'''
        if not self.api:
            log.error("BierDopje requires an API key. Ask a personnal on on http://www.bierdopje.com/forum")
            return []
            
        guessedData = self.guessFileData(token)
        if "tvshow" != guessedData['type'] :
            return []
        elif langs and not set(langs).intersection((['en', 'nl'])): # lang is given but does not include nl or en
            return []
            
        if not langs :
            availableLangs = ['nl', 'en']
        else :
            availableLangs = list(set(langs).intersection((['en', 'nl'])))
        log.debug("possible langs : %s " % availableLangs)
        sublinks = []
        
        # Query the show to get the show id
        showName = guessedData['name'].lower()
        if exceptions.has_key(showName):
            show_id = exceptions.get(showName)
        elif self.cache['showids'].has_key(showName):
            show_id = self.cache['showids'].get(showName)
        else :
            getShowId_url = "%sGetShowByName/%s" %(self.api, urllib.quote(showName))
            log.debug("Looking for show Id @ %s" % getShowId_url)
            
            req = urllib2.Request(getShowId_url, headers = self.headers )
            page = urllib2.urlopen(req)
            dom = minidom.parse(page)
            if not dom or len(dom.getElementsByTagName('showid')) == 0 :
                page.close()
                return []
            show_id = dom.getElementsByTagName('showid')[0].firstChild.data
            self.cache['showids'][showName] = show_id
            f = open(self.cache_path, 'w')
            pickle.dump(self.cache, f)
            f.close()
            page.close()

        # Query the episode to get the subs
        for lang in availableLangs :
            getAllSubs_url = "%sGetAllSubsFor/%s/%s/%s/%s" %(self.api, show_id, guessedData['season'], guessedData['episode'], lang)
            log.debug("Looking for subs @ %s" %getAllSubs_url)
            req = urllib2.Request(getAllSubs_url, headers = self.headers )
            page = urllib2.urlopen(req)
            dom = minidom.parse(page)
            page.close()
            for sub in dom.getElementsByTagName('result'):
		release = sub.getElementsByTagName('filename')[0].firstChild.data
                if release.endswith(".srt"):
                    release = release[:-4]
                dllink = sub.getElementsByTagName('downloadlink')[0].firstChild.data
                log.debug("Release found : %s" % release.lower())
                log.debug("Searching for : %s" % token.lower())
                result = {}
                result["release"] = release
                result["link"] = dllink
                result["page"] = dllink
                result["lang"] = lang
                sublinks.append(result)
            
        return sublinks

########NEW FILE########
__FILENAME__ = OpenSubtitles
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os, struct, xmlrpclib, commands, gzip, traceback, logging
import xbmc
import socket # For timeout purposes

import SubtitleDatabase

log = logging.getLogger(__name__)

OS_LANGS ={ "en": "eng", 
            "fr" : "fre", 
            "hu": "hun", 
            "cs": "cze", 
            "pl" : "pol", 
            "sk" : "slo", 
            "pt" : "por", 
            "pt-br" : "pob", 
            "es" : "spa", 
            "el" : "ell", 
            "ar":"ara",
            'sq':'alb',
            "hy":"arm",
            "ay":"ass",
            "bs":"bos",
            "bg":"bul",
            "ca":"cat",
            "zh":"chi",
            "hr":"hrv",
            "da":"dan",
            "nl":"dut",
            "eo":"epo",
            "et":"est",
            "fi":"fin",
            "gl":"glg",
            "ka":"geo",
            "de":"ger",
            "he":"heb",
            "hi":"hin",
            "is":"ice",
            "id":"ind",
            "it":"ita",
            "ja":"jpn",
            "kk":"kaz",
            "ko":"kor",
            "lv":"lav",
            "lt":"lit",
            "lb":"ltz",
            "mk":"mac",
            "ms":"may",
            "no":"nor",
            "oc":"oci",
            "fa":"per",
            "ro":"rum",
            "ru":"rus",
            "sr":"scc",
            "sl":"slv",
            "sv":"swe",
            "th":"tha",
            "tr":"tur",
            "uk":"ukr",
            "vi":"vie"}

class OpenSubtitles(SubtitleDatabase.SubtitleDB):
    url = "http://www.opensubtitles.org/"
    site_name = "OpenSubtitles"
    
    def __init__(self, config, cache_folder_path):
        super(OpenSubtitles, self).__init__(OS_LANGS)
        self.server_url = 'http://api.opensubtitles.org/xml-rpc'
        self.revertlangs = dict(map(lambda item: (item[1],item[0]), self.langs.items()))

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query OpenSubtitles.org '''

	subs = []
        filehash = self.hashFile(filepath)
        # disabled this part because getFileSize gives negative values for large files
        # on BoxeeBox, which makes this useless for larger movies
	fname = self.getFileName(filepath)
        if xbmc.getFileSize(filepath):
            log.debug(filehash)
            size = long(xbmc.getFileSize(filepath))
            fname = self.getFileName(filepath)
            subs += self.query(moviehash=filehash, langs=langs, bytesize=size, filename=fname)
  
        subs += self.query(langs=langs, filename=fname)
	return subs
        
    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        
	content = self.downloadContent(suburl)
        f = gzip.open(srtbasefilename+".srt.gz")
        dump = open(srtbasefilename+".srt", "wb")
        dump.write(f.read())
        dump.close()
        f.close()
        os.remove(srtbasefilename+".srt.gz")
        return srtbasefilename+".srt"

    def downloadFile(self, link, path):
	content = self.downloadContent(link)
	dump = open(path+".gz", "wb")
        dump.write(content)
        dump.close()
        f = gzip.open(path+".gz")
        dump = open(path, "wb")
        dump.write(f.read())
        dump.close()
        f.close()
        os.remove(path+".gz")
        return path	

    def query(self, filename, imdbID=None, moviehash=None, bytesize=None, langs=None):
        ''' Makes a query on opensubtitles and returns info about found subtitles.
            Note: if using moviehash, bytesize is required.    '''
        log.debug('query')
        #Prepare the search
        search = {}
        sublinks = []
	gotHash = False
	fileHash = ''
	if(moviehash):
		gotHash = True
		fileHash = moviehash
		
        if moviehash: 
            search['moviehash'] = moviehash
            gotHash = True
        if imdbID: search['imdbid'] = imdbID
        if bytesize: search['moviebytesize'] = str(bytesize)
        if len(search) == 0:
            log.debug("No search term, we'll use the filename")
            # Let's try to guess what to search:
            guessed_data = self.guessFileData(filename)
	    searchstring = guessed_data['name']
	    if guessed_data['type'] == 'tvshow':
	    	if(int(guessed_data['season']) < 10):
                	guessed_data['season'] = "0"+str(guessed_data['season'])
            	if(int(guessed_data['episode']) < 10):
                	guessed_data['episode'] = "0"+str(guessed_data['episode'])
            
		searchstring = "%s S%sE%s" % (guessed_data['name'], guessed_data['season'], guessed_data['episode'])

            search['query'] = searchstring
            log.debug(search['query'])
            
        #Login
        self.server = xmlrpclib.Server(self.server_url)
        socket.setdefaulttimeout(10)
        try:
            log_result = self.server.LogIn("","","eng","periscope")
            log.debug(log_result)
            token = log_result["token"]
        except Exception:
            log.error("Open subtitles could not be contacted for login")
            token = None
            socket.setdefaulttimeout(None)
            return []
        if not token:
            log.error("Open subtitles did not return a token after logging in.")
            return []            
            
        # Search
        self.filename = filename #Used to order the results
        sublinks += self.get_results(token, search, gotHash, fileHash)

        # Logout
        try:
            self.server.LogOut(token)
        except:
            log.error("Open subtitles could not be contacted for logout")
        socket.setdefaulttimeout(None)
        return sublinks
        
    def get_results(self, token, search, gotHash, fileHash):
        log.debug("query: token='%s', search='%s'" % (token, search))
        try:
            if search:
                results = self.server.SearchSubtitles(token, [search])
        except Exception, e:
            log.error("Could not query the server OpenSubtitles")
            log.debug(e)
            return []
        log.debug("Result: %s" %str(results))

        sublinks = []
        if results['data']:
            log.debug(results['data'])
            # OpenSubtitles hash function is not robust ... We'll use the MovieReleaseName to help us select the best candidate
            for r in sorted(results['data'], self.sort_by_moviereleasename):
                # Only added if the MovieReleaseName matches the file
                result = {}
                result["release"] = r['SubFileName']
                result["link"] = r['SubDownloadLink']
                result["page"] = r['SubDownloadLink']
		if(gotHash == True and r['MovieHash'] == fileHash):
			result["hash"] = True
                result["lang"] = self.getLG(r['SubLanguageID'])
                if search.has_key("query") : #We are using the guessed file name, let's remove some results

                    # We're not actually removing, since due to some BoxeeBox issues we're
                    # always searching by filename. And if a user renames their files (which)
                    # works better with Boxee, then these names will probably never match
                    # so we only prioritize the matches, but keep everything else in there as
                    # well...
                    if r["MovieReleaseName"].startswith(self.filename):
                        sublinks.insert(0,result)
                    else:
                        sublinks.append(result)
                        log.debug("Removing %s because release '%s' has not right start %s" %(result["release"], r["MovieReleaseName"], self.filename))
                else :
                    sublinks.append(result)
        return sublinks

    def sort_by_moviereleasename(self, x, y):
        ''' sorts based on the movierelease name tag. More matching, returns 1'''
        #TODO add also support for subtitles release
        xmatch = x['MovieReleaseName'] and (x['MovieReleaseName'].find(self.filename)>-1 or self.filename.find(x['MovieReleaseName'])>-1)
        ymatch = y['MovieReleaseName'] and (y['MovieReleaseName'].find(self.filename)>-1 or self.filename.find(y['MovieReleaseName'])>-1)
        #print "analyzing %s and %s = %s and %s" %(x['MovieReleaseName'], y['MovieReleaseName'], xmatch, ymatch)
        if xmatch and ymatch:
            if x['MovieReleaseName'] == self.filename or x['MovieReleaseName'].startswith(self.filename) :
                return -1
            return 0
        if not xmatch and not ymatch:
            return 0
        if xmatch and not ymatch:
            return -1
        if not xmatch and ymatch:
            return 1
        return 0


########NEW FILE########
__FILENAME__ = regexes
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

# all regexes are case insensitive

ep_regexes = [
              ('standard_repeat',
               # Show.Name.S01E02.S01E03.Source.Quality.Etc-Group
               # Show Name - S01E02 - S01E03 - S01E04 - Ep Name
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               s(?P<season_num>\d+)[. _-]*                 # S01 and optional separator
               e(?P<ep_num>\d+)                            # E02 and separator
               ([. _-]+s(?P=season_num)[. _-]*             # S01 and optional separator
               e(?P<extra_ep_num>\d+))+                    # E03/etc and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('fov_repeat',
               # Show.Name.1x02.1x03.Source.Quality.Etc-Group
               # Show Name - 1x02 - 1x03 - 1x04 - Ep Name
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               (?P<season_num>\d+)x                        # 1x
               (?P<ep_num>\d+)                             # 02 and separator
               ([. _-]+(?P=season_num)x                    # 1x
               (?P<extra_ep_num>\d+))+                     # 03/etc and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('standard',
               # Show.Name.S01E02.Source.Quality.Etc-Group
               # Show Name - S01E02 - My Ep Name
               # Show.Name.S01.E03.My.Ep.Name
               # Show.Name.S01E02E03.Source.Quality.Etc-Group
               # Show Name - S01E02-03 - My Ep Name
               # Show.Name.S01.E02.E03
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               s(?P<season_num>\d+)[. _-]*                 # S01 and optional separator
               e(?P<ep_num>\d+)                            # E02 and separator
               (([. _-]*e|-)(?P<extra_ep_num>\d+))*        # additional E03/etc
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),

              ('fov',
               # Show_Name.1x02.Source_Quality_Etc-Group
               # Show Name - 1x02 - My Ep Name
               # Show_Name.1x02x03x04.Source_Quality_Etc-Group
               # Show Name - 1x02-03-04 - My Ep Name
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (?P<season_num>\d+)x                        # 1x
               (?P<ep_num>\d+)                             # 02 and separator
               (([. _-]*x|-)(?P<extra_ep_num>\d+))*        # additional x03/etc
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
        
              ('scene_date_format',
               # Show.Name.2010.11.23.Source.Quality.Etc-Group
               # Show Name - 2010-11-23 - Ep Name
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (?P<air_year>\d{4})[. _-]+                  # 2010 and separator
               (?P<air_month>\d{2})[. _-]+                 # 11 and separator
               (?P<air_day>\d{2})                          # 23 and separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''),
              
              ('stupid',
               # tpz-abc102
               '''
               (?P<release_group>.+?)-\w+?[\. ]?           # tpz-abc
               (?P<season_num>\d{1,2})                     # 1
               (?P<ep_num>\d{2})$                          # 02
               '''),
              
              ('bare',
               # Show.Name.102.Source.Quality.Etc-Group
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show_Name and separator
               (?P<season_num>\d{1,2})                     # 1
               (?P<ep_num>\d{2})                           # 02 and separator
               ([. _-]+(?P<extra_info>(?!\d{3}[. _-]+)[^-]+) # Source_Quality_Etc-
               (-(?P<release_group>.+))?)?$                # Group
               '''),
              
              ('verbose',
               # Show Name Season 1 Episode 2 Ep Name
               '''
               ^(?P<series_name>.+?)[. _-]+                # Show Name and separator
               season[. _-]+                               # season and separator
               (?P<season_num>\d+)[. _-]+                  # 1
               episode[. _-]+                              # episode and separator
               (?P<ep_num>\d+)[. _-]+                      # 02 and separator
               (?P<extra_info>.+)$                         # Source_Quality_Etc-
               '''),
              
              ('season_only',
               # Show.Name.S01.Source.Quality.Etc-Group
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               s(eason[. _-])?                             # S01/Season 01
               (?P<season_num>\d+)[. _-]*                  # S01 and optional separator
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),

              ('no_season_general',
               # Show.Name.E23.Test
               # Show.Name.Part.3.Source.Quality.Etc-Group
               # Show.Name.Part.1.and.Part.2.Blah-Group
               # Show Name Episode 3 and 4
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (e(p(isode)?)?|part|pt)[. _-]?              # e, ep, episode, or part
               (?P<ep_num>(\d+|[ivx]+))                    # first ep num
               ([. _-]+((and|&|to)[. _-]+)?                # and/&/to joiner
               ((e(p(isode)?)?|part|pt)[. _-]?)?           # e, ep, episode, or part
               (?P<extra_ep_num>(\d+|[ivx]+)))*            # second ep num
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),

               
              ('no_season',
               # Show Name - 01 - Ep Name
               # 01 - Ep Name
               '''
               ^((?P<series_name>.+?)[. _-]+)?             # Show_Name and separator
               (?P<ep_num>\d{2})                           # 02
               [. _-]*((?P<extra_info>.+?)                 # Source_Quality_Etc-
               ((?<![. _-])-(?P<release_group>[^-]+))?)?$  # Group
               '''
               ),
              ]


########NEW FILE########
__FILENAME__ = SubsWiki
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import zipfile, os, urllib2, urllib, logging, traceback, httplib, re
from BeautifulSoup import BeautifulSoup

import SubtitleDatabase

LANGUAGES = {u"English (US)" : "en",
             u"English (UK)" : "en",
             u"English" : "en",
             u"French" : "fr",
             u"Brazilian" : "pt-br",
             u"Portuguese" : "pt",
             u"Español (Latinoamérica)" : "es",
             u"Español (España)" : "es",
             u"Español" : "es",
             u"Italian" : "it",
             u"Català" : "ca"}

class SubsWiki(SubtitleDatabase.SubtitleDB):
    url = "http://www.subswiki.com"
    site_name = "SubsWiki"

    def __init__(self, config, config_folder_path):
        super(SubsWiki, self).__init__(langs=None,revertlangs=LANGUAGES)
        #http://www.subswiki.com/serie/Dexter/4/1/
        self.host = "http://www.subswiki.com"
        self.release_pattern = re.compile("\nVersion (.+), ([0-9]+).([0-9])+ MBs")
        

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = unicode(self.getFileName(filepath).lower())
        guessedData = self.guessFileData(fname)
        if guessedData['type'] == 'tvshow':
            subs = self.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], langs)
            return subs
        else:
            return []
    
    def query(self, name, season, episode, teams, langs=None):
        ''' makes a query and returns info (link, lang) about found subtitles'''
        sublinks = []
        name = name.lower().replace(" ", "_")
        searchurl = "%s/serie/%s/%s/%s/" %(self.host, name, season, episode)
        logging.debug("dl'ing %s" %searchurl)
        try:
            page = urllib2.urlopen(searchurl)
            ''' test if no redirect was made '''
            if page.geturl() != searchurl :
                return sublinks
        except urllib2.HTTPError, (inst):
            logging.debug("Error : %s for %s" % (searchurl, inst))
            return sublinks
        
        soup = BeautifulSoup(page)
        for subs in soup("td", {"class":"NewsTitle"}):
            subteams = subs.findNext("b").string.lower()            
            teams = set(teams)
            subteams = self.listTeams([subteams], [".", "_", " ", " y "])
            
            #logging.debug("Team from website: %s" %subteams)
            #logging.debug("Team from file: %s" %teams)
            
            #langs_html = subs.findNext("td", {"class" : "language"})
            #lang = self.getLG(langs_html.string.strip())
            
            nexts = subs.parent.parent.findAll("td", {"class" : "language"})
            for langs_html in nexts:
                lang = self.getLG(langs_html.string.strip())
                #logging.debug("lang: %s" %lang)
                statusTD = langs_html.findNext("td")
                status = statusTD.find("strong").string.strip()
                #logging.debug("status: %s" %status)

                link = statusTD.findNext("td").find("a")["href"]

                if ((status == "Completed" or status == "Completado")) :
                    result = {}
                    result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("-", ".").title(), int(season), int(episode), '.'.join(subteams))
                    result["lang"] = lang
                    result["link"] = self.host + link
                    result["page"] = searchurl
                    sublinks.append(result)
                
        return sublinks
        
    def listTeams(self, subteams, separators):
        teams = []
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        logging.debug(subteams)
        return set(subteams)
    
    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        srtfilename = srtbasefilename +".srt"
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
        
        f = urllib2.urlopen(req)
        dump = open(filename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()

########NEW FILE########
__FILENAME__ = SubtitleDatabase
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os, shutil, urllib2, sys, logging, traceback, zipfile
import xbmc
import struct
import socket # For timeout purposes
import re

log = logging.getLogger(__name__)

USER_AGENT = 'BoxeeSubs/1.0'

class SubtitleDB(object):
    ''' Base (kind of abstract) class that represent a SubtitleDB, usually a website. Should be rewritten using abc module in Python 2.6/3K'''
    def __init__(self, langs, revertlangs = None):
        if langs:
            self.langs = langs
            self.revertlangs = dict(map(lambda item: (item[1],item[0]), self.langs.items()))
        if revertlangs:
            self.revertlangs = revertlangs
            self.langs = dict(map(lambda item: (item[1],item[0]), self.revertlangs.items()))
        self.tvshowRegex = re.compile('(?P<show>.*)S(?P<season>[0-9]{2})E(?P<episode>[0-9]{2}).(?P<teams>.*)', re.IGNORECASE)
        self.tvshowRegex2 = re.compile('(?P<show>.*).(?P<season>[0-9]{1,2})x(?P<episode>[0-9]{1,2}).(?P<teams>.*)', re.IGNORECASE)
        self.movieRegex = re.compile('(?P<movie>.*)[\.|\[|\(| ]{1}(?P<year>(?:(?:19|20)[0-9]{2}))(?P<teams>.*)', re.IGNORECASE)

    def searchInThread(self, queue, filename, langs):
        ''' search subtitles with the given filename for the given languages'''
        try:
            subs = self.process(filename, langs)
            map(lambda item: item.setdefault("plugin", self), subs)
            map(lambda item: item.setdefault("filename", filename), subs)
            log.info("%s writing %s items to queue" % (self.__class__.__name__, len(subs)))
        except:
            log.exception("Error occured")
            subs = []
        queue.put(subs, True) # Each plugin must write as the caller periscopy.py waits for an result on the queue
    
    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = self.getFileName(filepath)
        try:
            return self.query(fname, langs)
        except Exception, e:
            log.exception("Error occured")
            return []
        
    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        zipfilename = srtbasefilename +".zip"
        self.downloadFile(suburl, zipfilename)
        
        if zipfile.is_zipfile(zipfilename):
            log.debug("Unzipping file " + zipfilename)
            zf = zipfile.ZipFile(zipfilename, "r")
            for el in zf.infolist():
                if el.orig_filename.rsplit(".", 1)[1] in ("srt", "sub", "txt"):
                    outfile = open(srtbasefilename + "." + el.orig_filename.rsplit(".", 1)[1], "wb")
                    outfile.write(zf.read(el.orig_filename))
                    outfile.flush()
                    outfile.close()
                else:
                    log.info("File %s does not seem to be valid " %el.orig_filename)
            # Deleting the zip file
            zf.close()
            os.remove(zipfilename)
            return srtbasefilename + ".srt"
        else:
            log.info("Unexpected file type (not zip)")
            os.remove(zipfilename)
            return None

    def downloadContent(self, url, timeout = None):
        ''' Downloads the given url and returns its contents.'''
        try:
            log.debug("Downloading %s" % url)
            req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : USER_AGENT})
            if timeout:
                socket.setdefaulttimeout(timeout)
            f = urllib2.urlopen(req)
            content = f.read()
            f.close()
            return content
        except urllib2.HTTPError, e:
            log.warning("HTTP Error: %s - %s" % (e.code, url))
        except urllib2.URLError, e:
            log.warning("URL Error: %s - %s" % (e.reason, url))

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        content = self.downloadContent(url)
        dump = open(filename, "wb")
        dump.write(content)
        dump.close()
        log.debug("Download finished to file %s. Size : %s"%(filename,os.path.getsize(filename)))
        
    def getLG(self, language):
        ''' Returns the short (two-character) representation of the long language name'''
        try:
            return self.revertlangs[language]
        except KeyError, e:
            log.warn("Ooops, you found a missing language in the config file of %s: %s. Send a bug report to have it added." %(self.__class__.__name__, language))
        
    def getLanguage(self, lg):
        ''' Returns the long naming of the language on a two character code '''
        try:
            return self.langs[lg]
        except KeyError, e:
            log.warn("Ooops, you found a missing language in the config file of %s: %s. Send a bug report to have it added." %(self.__class__.__name__, lg))
    
    def query(self, token):
        raise TypeError("%s has not implemented method '%s'" %(self.__class__.__name__, sys._getframe().f_code.co_name))
        
    def fileExtension(self, filename):
        ''' Returns the file extension (without the dot)'''
        return os.path.splitext(filename)[1][1:].lower()
        
    def getFileName(self, filepath):
        return os.path.basename(filepath)
                
    def guessFileData(self, filename):
        filename = unicode(self.getFileName(filename).lower())
        matches_tvshow = self.tvshowRegex.match(filename)
        if matches_tvshow: # It looks like a tv show
            (tvshow, season, episode, teams) = matches_tvshow.groups()
            tvshow = tvshow.replace(".", " ").strip()
            teams = teams.split('.')
            return {'type' : 'tvshow', 'name' : tvshow.strip(), 'season' : int(season), 'episode' : int(episode), 'teams' : teams}
        else:
            matches_tvshow = self.tvshowRegex2.match(filename)
            if matches_tvshow:
                (tvshow, season, episode, teams) = matches_tvshow.groups()
                tvshow = tvshow.replace(".", " ").strip()
                teams = teams.split('.')
                return {'type' : 'tvshow', 'name' : tvshow.strip(), 'season' : int(season), 'episode' : int(episode), 'teams' : teams}
            else:
                matches_movie = self.movieRegex.match(filename)
                if matches_movie:
                    (movie, year, teams) = matches_movie.groups()
                    teams = teams.split('.')
                    part = None
                    if "cd1" in teams :
                        teams.remove('cd1')
                        part = 1
                    if "cd2" in teams :
                        teams.remove('cd2')
                        part = 2
                    return {'type' : 'movie', 'name' : movie.strip(), 'year' : year, 'teams' : teams, 'part' : part}
                else:
                    return {'type' : 'unknown', 'name' : filename, 'teams' : [] }

    def hashFile(self, name):
	return xbmc.getFileHash(name)	

    def hashFile2(self, name):
        '''
        Calculates the Hash à-la Media Player Classic as it is the hash used by OpenSubtitles.
        By the way, this is not a very robust hash code.
        ''' 
        longlongformat = 'Q'  # unsigned long long little endian
        bytesize = struct.calcsize(longlongformat)
        format= "<%d%s" % (65536//bytesize, longlongformat)
        
        f = open(name, "rb") 
        filesize = os.fstat(f.fileno()).st_size
        hash = filesize 
        
        if filesize < 65536 * 2:
            log.error('File is too small')
            return "SizeError" 
        
        buffer= f.read(65536)
        longlongs= struct.unpack(format, buffer)
        hash+= sum(longlongs)
        
        f.seek(-65536, os.SEEK_END) # size is always > 131072
        buffer= f.read(65536)
        longlongs= struct.unpack(format, buffer)
        hash+= sum(longlongs)
        hash&= 0xFFFFFFFFFFFFFFFF
        
        f.close() 
        returnedhash =  "%016x" % hash
	log.warn(returnedhash)
        return returnedhash


class InvalidFileException(Exception):
    ''' Exception object to be raised when the file is invalid'''
    def __init__(self, filename, reason):
        self.filename = filename
        self.reason = reason
    def __str__(self):
        return (repr(filename), repr(reason))

########NEW FILE########
__FILENAME__ = Subtitulos
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import zipfile, os, urllib2, urllib, logging, traceback, httplib, re
from BeautifulSoup import BeautifulSoup

import SubtitleDatabase

log = logging.getLogger(__name__)

LANGUAGES = {u"English (US)" : "en",
             u"English (UK)" : "en",
             u"English" : "en",
             u"French" : "fr",
             u"Brazilian" : "pt-br",
             u"Portuguese" : "pt",
             u"Español (Latinoamérica)" : "es",
             u"Español (España)" : "es",
             u"Español" : "es",
             u"Italian" : "it",
             u"Català" : "ca"}

class Subtitulos(SubtitleDatabase.SubtitleDB):
    url = "http://www.subtitulos.es"
    site_name = "Subtitulos"

    def __init__(self, config, cache_folder_path):
        super(Subtitulos, self).__init__(langs=None,revertlangs=LANGUAGES)
        #http://www.subtitulos.es/dexter/4x01
        self.host = "http://www.subtitulos.es"
        self.release_pattern = re.compile("Versi&oacute;n (.+) ([0-9]+).([0-9])+ megabytes")
        

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = unicode(self.getFileName(filepath).lower())
        guessedData = self.guessFileData(fname)
        if guessedData['type'] == 'tvshow':
            subs = self.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], langs)
            return subs
        else:
            return []
    
    def query(self, name, season, episode, teams, langs=None):
        ''' makes a query and returns info (link, lang) about found subtitles'''
        sublinks = []
        name = name.lower().replace(" ", "-")
        searchurl = "%s/%s/%sx%s" %(self.host, name, season, episode)
        content = self.downloadContent(searchurl, 10)
        if not content:
            return sublinks
        soup = BeautifulSoup(content)
        for subs in soup("div", {"id":"version"}):
            version = subs.find("p", {"class":"title-sub"})
            subteams = self.release_pattern.search("%s"%version.contents[1]).group(1).lower()            
            teams = set(teams)
            subteams = self.listTeams([subteams], [".", "_", " ", "/"])
            
            log.debug("Team from website: %s" %subteams)
            log.debug("Team from file: %s" %teams)

            nexts = subs.findAll("ul", {"class":"sslist"})
            for lang_html in nexts:
                langLI = lang_html.findNext("li",{"class":"li-idioma"} )
                lang = self.getLG(langLI.find("strong").contents[0].string.strip())
        
                statusLI = lang_html.findNext("li",{"class":"li-estado green"} )
                status = statusLI.contents[0].string.strip()

                link = statusLI.findNext("span", {"class":"descargar green"}).find("a")["href"]
                if status == "Completado" :
                    result = {}
                    result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("-", ".").title(), int(season), int(episode), '.'.join(subteams))
                    result["lang"] = lang
                    result["link"] = link
                    result["page"] = searchurl
                    sublinks.append(result)
                
        return sublinks
        
    def listTeams(self, subteams, separators):
        teams = []
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        log.debug(subteams)
        return set(subteams)
    
    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        srtfilename = srtbasefilename +".srt"
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
        
        f = urllib2.urlopen(req)
        dump = open(filename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import TheSubDB
import BierDopje
import logging

logging.basicConfig(level=logging.DEBUG)

filename = "/burn/30.Rock.S05E16.HDTV.XviD-LOL.avi"

p = TheSubDB.TheSubDB(None, None)
subfname = filename[:-3]+"srt"
logging.info("Processing %s" % filename)
subs = p.process(filename, ["en", "pt"])

print subs

if not subs:
    p.uploadFile(filename, subfname, 'en')
    subs = p.process(filename, ["en", "pt"])
    print subs


#bd = BierDopje.BierDopje()
#subs = bd.process(filename, ["en"])




########NEW FILE########
__FILENAME__ = Undertexter

# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, logging, time, shutil
from BeautifulSoup import BeautifulSoup


import ConfigParser

import SubtitleDatabase
import version

log = logging.getLogger(__name__)

def rematch(pattern, inp):
    matcher = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    matches = matcher.match(inp)
    if matches:
        yield matches


class Undertexter(SubtitleDatabase.SubtitleDB):
    main_url = "http://www.undertexter.se/"
    eng_download_url = "http://eng.undertexter.se/"
    debug_pretext = ""

    #====================================================================================================================
    # Functions
    #====================================================================================================================

    def __init__(self, config, cache_folder_path):
        super(Undertexter, self).__init__(None)
        self.headers = {'User-Agent' : 'BoxeeSubs/1.0'}


    def process(self, filepath, langs):
            ''' main method to call on the plugin, pass the filename and the wished
            languages and it will query the subtitles source '''
            fname = self.getFileName(filepath)
            try:
                subs = self.query(fname, langs)
                if not subs and fname.rfind(".[") > 0:
                    # Try to remove the [VTV] or [EZTV] at the end of the file
                    teamless_filename = fname[0 : fname.rfind(".[")]
                    subs = self.query(teamless_filename, langs)
                    return subs
                else:
                    return subs
            except Exception, e:
                log.exception("Error raised by plugin")
                return []


    def query(self, token, langs=None):
        ''' makes a query and returns info (link, lang) about found subtitles'''

        guessedData = self.guessFileData(token)
        if langs and not set(langs).intersection((['en', 'sv'])): # lang is given but does not include nl or en
            return []

        if not langs :
            availableLangs = ['sv', 'en']
        else :
            availableLangs = list(set(langs).intersection((['en', 'sv'])))
        log.debug("possible langs : %s " % availableLangs)
        sublinks = []

        if guessedData['type'] == 'tvshow':
	    if(int(guessedData['season']) < 10):
		guessedData['season'] = "0"+str(guessedData['season'])
	    if(int(guessedData['episode']) < 10):
                guessedData['episode'] = "0"+str(guessedData['episode'])
            searchstring = "%s S%sE%s" % (guessedData['name'], guessedData['season'], guessedData['episode'])
	else:
	    searchstring = guessedData['name']
        for lang in availableLangs :
            if(lang == "sv"):
                url = self.main_url + "?p=soek&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
            else:
                url = self.main_url + "?group1=on&p=eng_search&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
            req = urllib2.Request(url, headers = self.headers )
            page = urllib2.urlopen(req)
            content = page.read()
            page.close()

	    soup = BeautifulSoup(content)
	    for subs in soup("table", {"width" : "460", "cellpadding" : "0", "cellspacing" : "0"}):
		for tr in subs("tr"):
			links = tr.findAll("a")
			result = {}
			id = 0
			if(len(links) > 0):
				for m in rematch("http://www.undertexter.se/laddatext.php\?id=(.*)", links[0]['href']):
					id = m.group(1)
				for m in rematch("http://eng.undertexter.se/subtitle.php\?id=(.*)", links[0]['href']):
                        		id = m.group(1)
				if(int(id) > 0):
					if(lang == "sv"):
						link = "http://www.undertexter.se/laddatext.php?id=" + id
					else:
						link = "http://eng.undertexter.se/subtitle.php?id=" + id
					
					release = ""
					for a in tr.findAll('td')[0].childGenerator(): 
						release = str(a).strip()
					
					if(release != ""):
						result["link"] = link
						result["page"] = link			
						result["lang"] = lang
						result["release"] = release
						sublinks.append(result)

        return sublinks

    def downloadFile(self, url, filename):
	req = urllib2.Request(url, headers = self.headers)
        f = urllib2.urlopen(req)
        content = f.read()
        f.close()
	orig_sub_dir = os.path.dirname(os.path.abspath(filename))
	tmp_sub_dir = os.path.dirname(os.path.abspath(filename))
	tmp_sub_dir = tmp_sub_dir+"/dl"
	if os.path.exists(tmp_sub_dir):
		files = os.listdir(tmp_sub_dir)
                for file in files:
			os.remove(os.path.join(tmp_sub_dir, file))		
	else:
		os.mkdir(tmp_sub_dir)
	pass
	if content is not None:
            header = content[:4]
	    print header
            if header == 'Rar!':
                local_tmp_file = filename + ".rar"
                packed = True
            elif header == 'PK':
                local_tmp_file = filename + ".zip"
                packed = True
            else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
                local_tmp_file = filename
                subs_file = local_tmp_file
                packed = False
        try:
	    if os.path.exists(local_tmp_file):
		os.remove(local_tmp_file)
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (self.debug_pretext, local_tmp_file))

	print packed
	print local_tmp_file
        if packed:
        	print tmp_sub_dir
		files = os.listdir(tmp_sub_dir)
		init_filecount = len(files)
		max_mtime = 0
		filecount = init_filecount
		print filecount
		for file in files:
                	if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                		mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                		if mtime > max_mtime:
                			max_mtime =  mtime
            	init_max_mtime = max_mtime
		time.sleep(2)
            	xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
		time.sleep(1)
            	waittime  = 0
            	while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                	time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                	files = os.listdir(tmp_sub_dir)
                	filecount = len(files)
			print filecount
                	# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                	for file in files:
                    		if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        		mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        		if (mtime > max_mtime):
                            			max_mtime =  mtime
                	waittime  = waittime + 1
		print 'out of loopie yayyy'
            	if waittime == 20:
                	print "%s Failed to unpack subtitles in '%s'" % ("", tmp_sub_dir)
           	else:
                	print "%s Unpacked files in '%s'" % ("", tmp_sub_dir)
                	for file in files:
                    		# there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    		if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        		print "%s Unpacked subtitles file '%s'" % ("", file)
                        		subs_file = os.path.join(tmp_sub_dir, file)
			shutil.move(subs_file, filename)
			subs_file = filename
			print subs_file
            	os.remove(local_tmp_file)

        return subs_file

########NEW FILE########
__FILENAME__ = unittests
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import unittest
import logging
import os

logging.basicConfig(level=logging.DEBUG)
'''
class TVShowRegexTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        subdb = OpenSubtitles.OpenSubtitles()
        filenames = ('Futurama.S06E05.HDTV.XviD-aAF.avi', 'Parenthood.2010.S01E13.Lost.and.Found.HDTV.XviD-FQM.avi')
        for filename in filenames:
            print "%s => %s" %(filename, subdb.guessFileData(filename))


class RegexTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        subdb = OpenSubtitles.OpenSubtitles()
        #filenames = ('Marley & Me.2008-L33t-DvDRiP.DivX.NoRaR', 'Dexter.S04E01.HDTV.XviD-NoTV', 'Night.Watch.2004.CD1.DVDRiP.XViD-FiCO' , 'Stargate.Universe.S01E06.HDTV.XviD-XII.avi', 'The.Office.US.S06E01.HDTV.XviD-2HD.[VTV]', 'Twilight[2008]DvDrip-aXXo', 'Heroes.S03E09.HDTV.XviD-LOL', 'Transformers.Revenge.of.the.Fallen.TS.XviD-DEViSE', 'My.Name.is.Earl.S04E24.HDTV.XviD-LOL', 'Wallace.And.Gromit.A.Matter.Of.Loaf.And.Death.HDTV.XviD-BiA', 'arw-spread.dvdrip-xvid', 'Rec.2.[Spanish].TS-Screener.XviD.[DTL]', 'X-Men Origins Wolverine [2009] dvd rip nlx', 'Saw VI (2009) TS DivXNL-Team', 'Michael Jackson This Is It 2009 CAM XVID-PrisM.NoRar.www.crazy-torrent.com', 'The.Goods.Live.Hard.Sell.Hard.2009.PROPER.DvDRiP.XviD-ExtraScene RG')
        #filenames = ('The.Hurt.Locker.2008.DVDRiP.XViD.CD1', 'Catwoman.CAM-NOX-CD2.avi','Marley & Me.2008-L33t-DvDRiP.DivX.NoRaR')
        filenames = ('Catwoman.CAM-NOX-CD2.avi', 'Funny People (2009) DVDRip XviD-MAXSPEED www.torentz.3xforum.ro')
        for filename in filenames:
            print "%s => %s" %(filename, subdb.guessFileData(filename))

class SubtitulosTestCase(unittest.TestCase):
    def runTest(self):
        import Subtitulos
        subdb = Subtitulos.Subtitulos()
        fname = "CSI.S10E13.HDTV.XvID-FQM.avi"
        fname = "rubicon.s01e01.repack.hdtv.xvid-fqm.avi"
        guessedData = subdb.guessFileData(fname)
        print fname
        print guessedData
        if guessedData['type'] == 'tvshow':
            subs = subdb.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'])
            print subs

class Addic7edTestCase(unittest.TestCase):
    def runTest(self):
        import Addic7ed
        subdb = Addic7ed.Addic7ed()
        fname = "The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD"
        guessedData = subdb.guessFileData(fname)
        print fname
        print guessedData
        if guessedData['type'] == 'tvshow':
            subs = subdb.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'])
            print subs

class Addic7edTestCase(unittest.TestCase):
    def runTest(self):
        import Addic7ed
        subdb = Addic7ed.Addic7ed()
        #fname = "rubicon.s01e01.repack.hdtv.xvid-fqm.avi"
        fname = "24.1x03.2.00.am_3.00.am.ac3.dvdrip_ws_xvid-fov.avi"
        guessedData = subdb.guessFileData(fname)
        print fname
        print guessedData
        if guessedData['type'] == 'tvshow':
            subs = subdb.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'])
            print subs

class OpenSubtitlesTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        subdb = OpenSubtitles.OpenSubtitles()
        # movie hash if for night watch : http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        results = subdb.query('Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', moviehash="09a2c497663259cb", bytesize="733589504")
        
        assert len(results) > 0, 'No result found for Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi by movie hash'

class OpenSubtitlesTestCase(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        subdb = OpenSubtitles.OpenSubtitles()
        # movie hash if for night watch : http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        results = subdb.process('/burn/The.Office.US.S07E08.Viewing.Party.HDTV.XviD-FQM.[VTV].avi', None)
        print results
        assert len(results) > 0, 'No result found for Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi by movie hash'

class OpenSubtitlesTestCaseFileName(unittest.TestCase):
    def runTest(self):
        import OpenSubtitles
        subdb = OpenSubtitles.OpenSubtitles()
        # movie hash if for night watch : http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        filenames = []
        #filename = 'Dexter.S04E01.HDTV.XviD-NoTV'
        #filename = 'The.Office.US.S06E01.HDTV.XviD-2HD.[VTV]'
        #filenames.append('Marley & Me.2008-L33t-DvDRiP.DivX.NoRaR')
        filenames.append("Twilight[2008]DvDrip-aXXo")
        
        for filename in filenames:
            results = subdb.query(filename)
        
            if results :
                print "Found %s results" %len(results)
                print "Showing first for unit test::"
                print results[0]
            assert len(results) > 0, 'No result found for %s' %filename

class SubtitleSourceTestCase(unittest.TestCase):
    def runTest(self):
        import SubtitleSource
        subdb = SubtitleSource.SubtitleSource()
        results = subdb.query("PrisM-Inception.2010")
        print results
        assert len(results) > 0, "No result could be found for Heroes 3X9 and no languages"

class SubtitleSourceTestCase2(unittest.TestCase):
    def runTest(self):
        import SubtitleSource
        subdb = SubtitleSource.SubtitleSource()
        results = subdb.query("Transformers.Revenge.of.the.Fallen.TS.XviD-DEViSE", ["en"])
        assert len(results) > 0, "No result could be found for Transformer 2 in English"

class SubtitleSourceTestCase3(unittest.TestCase):
    def runTest(self):
        import SubtitleSource
        subdb = SubtitleSource.SubtitleSource()
        results = subdb.query("Transformers.Revenge.of.the.Fallen.TS.XviD-DEViSE", ["en", "fi"])
        assert len(results) > 0, "No result could be found for Transformer 2 in English or Finnish"

class SubtitleSourceTestCase3(unittest.TestCase):
    def runTest(self):
        import Podnapisi
        subdb = Podnapisi.Podnapisi()
        results = subdb.query("My.Name.is.Earl.S04E24.HDTV.XviD-LOL", ["en"])
        assert len(results) > 0, "No result could be found for My.Name.is.Earl.S04E24.HDTV.XviD-LOL in any languages"

class SubSceneTestCase(unittest.TestCase):
    def runTest(self):
        import SubScene
        subdb = SubScene.SubScene()
        results = subdb.query("Dexter.S04E01.HDTV.XviD-NoTV")
        print results
        assert len(results) > 0, "No result could be found for Dexter.S04E01.HDTV.XviD-NoTV and no languages"

class SubSceneStep2TestCase(unittest.TestCase):
    def runTest(self):
        import SubScene
        subdb = SubScene.SubScene()
        subtitle = {'release': u'Dexter.S04E01.HDTV.XviD-NoTV', 'lang': 'ar', 'link': None, 'page': u'http://subscene.com/arabic/Dexter-Fourth-Season/subtitle-263042.aspx', 'filename' : '/tmp/testSubScene.avi'}
        srtfilename = subdb.createFile(subtitle)
        assert srtfilename != None, "Could download a subtitle"

class SubSceneStep3TestCase(unittest.TestCase):
    def runTest(self):
        import SubScene
        subdb = SubScene.SubScene()
        #suburl = "http://subscene.com/arabic/Dexter-Fourth-Season/subtitle-263042-dlpath-78348/zip.zipx"
        suburl = "http://subscene.com/arabic/Dexter-Fourth-Season/subtitle-263042.aspx"
        localFile = "/tmp/testSubScene.zip"
        subdb.downloadFile(suburl, localFile)
        print os.path.getsize(localFile)
        assert srtfilename != None, "Could download a subtitle"

class Podnapisi2TestCase(unittest.TestCase):
    def runTest(self):
        import Podnapisi2
        subdb = Podnapisi2.Podnapisi()
        results = subdb.process("/burn/Entourage.S07E01.Stunted.HDTV.XviD-FQM.avi", None)
        print results
        assert len(results) > 5, "Not enough result could be found for The.Office.US.S06E01.HDTV.XviD-2HD and no languages (expected 6)"
'''
class PodnapisiTestCase(unittest.TestCase):
    def runTest(self):
        import Podnapisi
        subdb = Podnapisi.Podnapisi(None, None)
        results = subdb.process("Game.Of.Thrones.S01E10.mkv", None)
        assert len(results) > 5, "Not enough result could be found for Community.S01E01.Pilot.HDTV.XviD-FQM.avi and no languages (expected 6)"
        
        # Download the first
        # Expected by the prog
        results[0]["filename"] = "/tmp/testPodnapisi.avi"
        subdb.createFile(results[0])
        #TODO Check that /tmp/testPodnapisi.srt exists
'''
class PodnapisiTestCaseMultiPart(unittest.TestCase):
    def runTest(self):
        import Podnapisi
        subdb = Podnapisi.Podnapisi()
        results = subdb.process("/tmp/Catwoman.CAM-NOX-CD1.avi", None)
        assert len(results) > 0
        results = subdb.process("/tmp/Catwoman.CAM-NOX-CD2.avi", None)
        assert len(results) > 0

class PodnapisiTestCaseTwoSerbian(unittest.TestCase):
    def runTest(self):
        import Podnapisi
        subdb = Podnapisi.Podnapisi()
        results = subdb.process("Twilight[2008]DvDrip-aXXo", None)
        assert len(results) > 0, "Not enough result could be found"

class TvSubtitlesTestCase(unittest.TestCase):
    def runTest(self):
        import TvSubtitles
        subdb = TvSubtitles.TvSubtitles()
        fname = "The.Big.Bang.Theory.S03E15.The.Large.Hadron.Collision.HDTV.XviD-FQM"
        guessedData = subdb.guessFileData(fname)
        subs = subdb.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], ['en'])
        for s in subs:
            print "Sub : %s" %s

class BierDopjeTestCase(unittest.TestCase):
    def runTest(self):
        import BierDopje
        subdb = BierDopje.BierDopje()
        video = "The.Office.US.S07E08.Viewing.Party.HDTV.XviD-FQM.[VTV]"
        #video = "Dexter.S04E01.HDTV.XviD-NoTV"
        #video = "the.walking.dead.s01e02.720p.hdtv.x264-ctu"
        video = "the.mentalist.s01e06.720p.hdtv.x264-ctu"
        results = subdb.query(video)
        print results
        assert len(results) > 0, "No result could be found for %s and no languages" %( video )
'''

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-

# This file is part of periscope.
# Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
# periscope is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# periscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with periscope; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

VERSION = "dev"

########NEW FILE########
__FILENAME__ = boxeehack_clear_cache
import os,mc
import xbmc, xbmcgui

def fanart_function():
    if mc.ShowDialogConfirm("Clear fanart cache", "Are you sure you want to clear the fanart cache?", "Cancel", "OK"):
        pass

def thumbnail_function():
    if mc.ShowDialogConfirm("Clear thumbnail cache", "Are you sure you want to clear the thumbnail cache?", "Cancel", "OK"):
        os.system("rm /data/etc/.fanart")
        os.system("find /data/.boxee/UserData/profiles/*/Thumbnails/ -name \*.tbn | xargs rm")
        mc.ShowDialogNotification("Clearing thumbnail cache")

if (__name__ == "__main__"):
    section = sys.argv[1]

    if section == "fanart":
        fanart_function()
    if section == "thumbnail":
        thumbnail_function()

########NEW FILE########
__FILENAME__ = boxeehack_grab_fanart
import xbmc, xbmcgui, mc
import time
import subprocess
import common
from random import randint

fanart = {}
fanart_changed = 0

from pysqlite2 import dbapi2 as sqlite

def get_fanart_list(exclude_blanks):
    global fanart
    showlist = common.file_get_contents("/data/etc/.fanart")
    if showlist == "":
        return
    
    showlist = showlist.split("\n")
    fanart = {}
    for line in showlist:
        if "=" in line:
            line = line.split("=")
            show = line[0].decode("utf-8")
            art = line[1].decode("utf-8")
            if art != "-" or exclude_blanks == False:
                fanart[show] = art

def store_fanart_list():
    global shows, fanart_changed
    
    file = ""
    for show in fanart:
        art = fanart[show]
        
        file = file + "%s=" % show
        file = file + "%s\n" % art
    
    common.file_put_contents("/data/etc/.fanart", file.encode("utf-8"))
    fanart_changed = 0
    
def grab_fanart_for_item(item):
    global fanart, fanart_changed

    if item.GetProperty("fanart") != "":
        return

    label = item.GetLabel().decode("utf-8")

    path = "%s" % item.GetPath()
    if "stack:" in path:
        path = path.split(" , ")
        path = path[len(path)-1]
        
    thumbnail = item.GetThumbnail()
    art = ""

    # to make sure we don't generate fanart entries for things like vimeo
    if path.find("http://") != -1:
        return

    if False:
        pass
    if path != "" and path.find("boxeedb://") == -1:
        art = path[0:path.rfind("/")+1] + "fanart.jpg"
    elif thumbnail.find("special://") == -1 and thumbnail.find("http://") == -1:
        art = thumbnail[0:thumbnail.rfind("/")+1] + "fanart.jpg"
    elif label in fanart:
        art = fanart[label].encode("utf-8")
    else:
        db_path = xbmc.translatePath('special://profile/Database/') + "../../../Database/boxee_catalog.db"
        conn = sqlite.connect(db_path)
        c = conn.cursor()
        if path.find("boxeedb://") == -1:
            # it must be a movie
            sql = "SELECT strPath FROM video_files WHERE strTitle=\"" + label + "\";"
        else:
            # it must be a tv show
            sql =  "SELECT strPath FROM video_files WHERE strShowTitle=\"" + label + "\";"

        data = c.execute(sql)
        for row in data:
            thumbnail = "%s" % row[0]
            if "/" in thumbnail:
                art = thumbnail[0:thumbnail.rfind("/")+1] + "fanart.jpg"

            if "/Season " in art:
                art = art[0:art.rfind("/Season ")+1] + "fanart.jpg"
            elif "/season " in art:
                art = art[0:art.rfind("/season ")+1] + "fanart.jpg"
            elif "/Season_" in art:
                art = art[0:art.rfind("/Season_")+1] + "fanart.jpg"
            elif "/season_" in art:
                art = art[0:art.rfind("/season_")+1] + "fanart.jpg"

        c.close()
        conn.close()

    if xbmc.getFileHash(art) == "0000000000000000":
        art = "-"
    
    if art != "" and art != "fanart.jpg":
        fanart[label] = art.decode("utf-8")
        fanart_changed = 1
        if art != "-":
            item.SetProperty("has-fanart", "1")
            item.SetProperty("fanart", str(art))
        else:
            item.SetProperty("has-fanart", "0")
        
def grab_random_fanart(controlNum, special):
    global fanart
    
    get_fanart_list(True)
    if len(fanart) == 0:
        return
    
    # sometimes the list control isn't available yet onload
    # so add some checking to make sure
    control = common.get_list(controlNum, special)
    count = 10
    while control == "" and count > 0:
        time.sleep(0.25)
        control = common.get_list(controlNum, special)
        count = count - 1
    
    window = common.get_window_id(special)
    if control == "":
        pass
    else:
        item = control.GetItem(0)
        while 1:
            if xbmcgui.getCurrentWindowDialogId() == 9999:
                art = fanart[fanart.keys()[randint(0, len(fanart) - 1)]].encode("utf-8")
                
                item.SetProperty("fanart", str(art))

            count = 5
            while count > 0:
                if window != common.get_window_id(special):
                    return
                time.sleep(2)
                count = count - 1

def grab_fanart_list(listNum, special):
    global fanart_changed
    
    get_fanart_list(False)
    
    # sometimes the list control isn't available yet onload
    # so add some checking to make sure
    lst = common.get_list(listNum, special)
    count = 10
    while lst == "" and count > 0:
        time.sleep(0.25)
        lst = common.get_list(listNum, special)
        count = count - 1

    window = common.get_window_id(special)
    if lst == "":
        pass
    else:
        # as long as the list exists (while the window exists)
        # the list gets updated at regular intervals. otherwise
        # the fanart disappears when you change sort-orders or
        # select a genre
        # should have very little overhead because all the values
        # get cached in memory
        focusedItem = ""
        while 1:
            # don't spend any time doing stuff if a dialog is open
            # 9999 is the dialog number when no dialogs are open
            # if special == True then the scanning is happening in
            # a dialog so we DO continue processing
            if xbmcgui.getCurrentWindowDialogId() == 9999 or special:
                theItem = mc.GetInfoString("Container(%s).ListItem.Label" % listNum)
                theItem = str(theItem)
                if theItem != "":
                    newFocusedItem = theItem
                else:
                    newFocusedItem = focusedItem
            
                if (newFocusedItem != focusedItem and newFocusedItem != "") or (newFocusedItem == "" and special):

                    lst = common.get_list(listNum, special)
                    if lst != "":
                        items = lst.GetItems()
                        if len(items) > 0:
                            if newFocusedItem == "":
                                newFocusedItem = items[0].GetLabel()
                            
                            for item in items:
                                grab_fanart_for_item(item)
                            focusedItem = newFocusedItem
                    
                        del items
                
            if window != common.get_window_id(special):
                return
            
            time.sleep(2)
            
            # store the fanart list for next time if the list
            # was modified
            if fanart_changed == 1:
                store_fanart_list()


if (__name__ == "__main__"):
    command = sys.argv[1]

    if command == "grab_fanart_list": grab_fanart_list(int(sys.argv[2]), False)
    if command == "grab_fanart_list_special": grab_fanart_list(int(sys.argv[2]), True)
    if command == "grab_random_fanart": grab_random_fanart(int(sys.argv[2]), False)

########NEW FILE########
__FILENAME__ = boxeehack_server
import socket
import common
import xbmc,time
import select
import urllib

def run_server():
    #Example of a simple tcp server using non-blocking sockets in a threaded script.
    # The combination of threaded script and non-blocking sockets ensures that
    # this script can be interrupted correctly when stopping the role (e.g. when
    # redeploying your project.) 

    #The server accepts only a single connection at time. It receives data until the
    # client either closes the connection or stops sending data for more than 2 seconds.
    # While receiving data it calculates the bit rate and outputs it on outputs[0].

    port = 2100

    #Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #bind to our desired port (on any available address)
    try:
        server_socket.bind(('', port))
    except:
        return

    #set to non-blocking operation
    server_socket.setblocking(0)

    #main loop for the threaded script
    while 1:
        #listen for incoming connection requests
        server_socket.listen(1)
    
        #use select to determine when a connection is available
        server_rfds, server_wfds, server_xfds = select.select([server_socket], [], [], 2)
        if server_socket in server_rfds:
            #accept the connection
            connection, address = server_socket.accept()
        
            #make new connection non-blocking
            connection.setblocking(0)
        
            #loop receiving data and calculate bit rate
            start = time.time()
            bitrate = 0.0
            data_bits = 0.0
            conn_closed = 0
            while conn_closed == 0:
                #use select to wait for data on connection, timeout after 2 seconds
                conn_rfds, conn_wfds, conn_xfds = select.select([connection], [], [connection], 2)
            
                #break on error
                if connection in conn_xfds:
                    break
            
                #check for data received, calculate bit rate
                elif connection in conn_rfds:
                    data = connection.recv(1024)
                    if len(data) == 0:
                        break

                    #calculate average bit rate in Mbps
                    data_bits += len(data) * 8.0
                    timediff = time.time() - start
                    if timediff > 0.0:
                        bitrate = (data_bits/timediff)/1000000
            
                    data = "".join(data.split("GET /")).split(" HTTP/")[0]
                    data = urllib.unquote(data).decode("utf-8")
                    xbmc.executebuiltin(str("%s" % data).encode("ascii"))
                    connection.send("HTTP/1.1 200 OK\nContent-type: text/html\n\n%s" % data)
                    connection.close()
                    conn_closed = 1
            
                #break if we have a timeout condition
                else:
                    break
        
            #close the inbound connection
            if conn_closed == 0:
                connection.close()

    #close the server on exit
    server_socket.close()

if (__name__ == "__main__"):
    command = sys.argv[1]

    if command == "run_server": run_server()
########NEW FILE########
__FILENAME__ = boxeehack_settings
import os
import xbmc, xbmcgui, mc
import ConfigParser
import common

available_providers = ['Addic7ed', 'BierDopje', 'OpenSubtitles', 'SubsWiki', 'Subtitulos', 'Undertexter']

# Set some default values for the subtitles handling
def register_defaults():
    subtitle_provider("get", "default")
    subtitle_provider("get", "tv")
    subtitle_provider("get", "movie")

    common.set_string("subtitles-plugin-language", get_subtitles_language_filter() )
    common.set_string("subtitles-plugin", get_subtitles_enabled() )
    common.set_string("featured-feed", get_featured_feed() )
    common.set_string("featured-name", get_featured_name() )
    common.set_string("browser-homepage", "".join(get_browser_homepage().split("http://")) )

    if not os.path.exists("/data/etc/.subtitles"):
        common.file_put_contents("/data/etc/.subtitles", """[DEFAULT]
lang = All
movieplugins = OpenSubtitles,Undertexter
tvplugins = BierDopje,OpenSubtitles,Addic7ed,Subtitulos,SubsWiki,Undertexter
plugins = BierDopje,OpenSubtitles,Subtitulos,SubsWiki,Addic7ed,Undertexter

[BierDopje]
key = C2FAFCBE34610608
""")
    
    set_home_enabled_strings()

    version_local = get_local_version()
    if version_local != "":
        common.set_string("boxeeplus-version", version_local )

def get_home_enabled_default_list():
    return "-,friends|Built-in,watchlater,shows|Built-in,movies|Built-in,music|Built-in,apps,files,web"
    
def set_home_enabled_strings():
    homeitems = get_home_enabled_default_list().split(",")

    for item in homeitems:
        item = item.split("|")[0]
        common.set_string("homeenabled-%s" % item, get_homeenabled(item))
        common.set_string("home-%s-replacement" % item, get_homereplacement(item))

def get_jump_to_last_unwatched_value():
    jumpenabled = common.file_get_contents("/data/etc/.jump_to_unwatched_enabled")
    if jumpenabled == "":
        jumpenabled = "0"
    return jumpenabled

def toggle_jump_to_last_unwatched():
    jumpenabled = get_jump_to_last_unwatched_value()
    
    if jumpenabled == "1":
        jumpenabled = "0"
    else:
        jumpenabled = "1"

    common.file_put_contents("/data/etc/.jump_to_unwatched_enabled", jumpenabled)
    common.set_string("jump-to-unwatched", jumpenabled)

def get_homeenabled_value():
    homeenabled = common.file_get_contents("/data/etc/.home_enabled")
    if homeenabled == "":
        homeenabled = get_home_enabled_default_list()
    return homeenabled.split("\n")[0]

def get_homereplacement(section):
    homeenabled = get_homeenabled_value().split(",")
    
    replacement = ""
    for item in homeenabled:
        item = item.split("|")
        if item[0] == section:
            if len(item) > 1:
                replacement = item[1]
            else:
                replacement = "Built-in"
                
    if replacement == "":
        replacement = "Off"
                
    return replacement
    
def get_homeenabled(section):
    homeenabled = get_homeenabled_value().split(",")
    
    section = "%s" % section
    for item in homeenabled:
        item = item.split("|")[0]
        if item == section:
            return "1"

    return "0"

def toggle_homeenabled(section, action):
    homeenabled = get_homeenabled_value().split(",")

    if section in ["friends","shows","movies","music"]:
        if section == "friends":
            types = ["Built-in", "Netflix", "Vudu", "Navi-X", "Spotify", "Grooveshark", "Pandora", "BBC iPlayer", "Revision3", "Crunchyroll", "Off"]
        if section == "shows":
            types = ["Built-in", "BBC iPlayer", "Revision3", "Crunchyroll", "Off"]
        if section == "movies":
            types = ["Built-in", "Netflix", "Vudu", "Navi-X", "Off"]
        if section == "music":
            types = ["Built-in", "Spotify", "Grooveshark", "Pandora", "Off"]

        replacement = get_homereplacement(section)
        
        for item in homeenabled:
            itemname = item.split("|")[0]
            if itemname == section:
                homeenabled.remove(item)
        
        pos = types.index(replacement)
        if action == "next":
            pos = pos + 1
        if action == "previous":
            pos = pos - 1
            
        if pos >= len(types):
            pos = 0
        if pos < 0:
            pos = len(types) - 1
        
        if types[pos] != "Off":
            homeenabled.append("%s|%s" % (section, types[pos]))
    
    else:
        found = 0
        for item in homeenabled:
            itemname = item.split("|")[0]
            if itemname == section:
                homeenabled.remove(item)
                found = 1
    
        if found == 0:
            homeenabled.append(section)

    common.file_put_contents("/data/etc/.home_enabled", ",".join(homeenabled))
    set_home_enabled_strings()

def get_browser_homepage():
    homepage = common.file_get_contents("/data/etc/.browser_homepage")

    if homepage == "":
        homepage = "http://www.myfav.es/boxee"

    return homepage

def set_browser_homepage():
    homepage = get_browser_homepage()

    kb = xbmc.Keyboard('default', 'heading', True)
    kb.setDefault(homepage)
    kb.setHeading('Enter homepage URL') # optional
    kb.setHiddenInput(False) # optional
    kb.doModal()

    if kb.isConfirmed():
        homepage = kb.getText()

        common.file_put_contents("/data/etc/.browser_homepage", homepage)

        template = common.file_get_contents("/data/hack/apps/browser2/template.xml")
        template = homepage.join(template.split("$URL$"))
        common.file_put_contents("/data/hack/apps/browser2/descriptor.xml", template)

        os.system("sh /data/hack/apps.sh")

        common.set_string("browser-homepage", "".join(get_browser_homepage().split("http://")) )

# Set the password for the telnet functionality    
def set_telnet_password():
    passwd = common.file_get_contents("/data/etc/passwd")
    kb = xbmc.Keyboard('default', 'heading', True)
    kb.setDefault(passwd) # optional
    kb.setHeading('Enter telnet password') # optional
    kb.setHiddenInput(True) # optional
    kb.doModal()
    if kb.isConfirmed():
        passwd = kb.getText()

        if passwd == "":
            dialog = xbmcgui.Dialog()
            ok = dialog.ok('Telnet', 'The telnet password must not be empty.')
        else:
            common.file_put_contents("/data/etc/passwd", passwd)    

# Determine whether subtitle functionality is enabled/enabled
def get_subtitles_enabled():
    subtitles = common.file_get_contents("/data/etc/.subtitles_enabled")
    if subtitles == "":
        subtitles = "0"
    return subtitles

def get_subtitles_language_filter():
    config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })
    if os.path.exists("/data/etc/.subtitles"):
        config.read("/data/etc/.subtitles")
    langs_config = config.get("DEFAULT", "lang")
    if(langs_config.strip() == "" or langs_config.strip() == "All"):
        return "0"
    else:
        return "1"

def featured_next():
    replace = get_featured_feed_value()
    num = int(replace) + 1
    if num > 4: num = 0

    replace = "%s" % num

    common.file_put_contents("/data/etc/.replace_featured_enabled", replace)
    common.set_string("featured-feed", get_featured_feed() )
    common.set_string("featured-name", get_featured_name() )

def featured_previous():
    replace = get_featured_feed_value()
    num = int(replace) - 1
    if num < 0: num = 4

    replace = "%s" % num

    common.file_put_contents("/data/etc/.replace_featured_enabled", replace)
    common.set_string("featured-feed", get_featured_feed() )
    common.set_string("featured-name", get_featured_name() )

def get_featured_feed():
    replace = get_featured_feed_value()
    feed = "feed://featured/?limit=15"

    if replace == "1": feed = "boxeedb://recent/?limit=15"
    if replace == "2": feed = "rss://vimeo.com/channels/staffpicks/videos/rss"
    if replace == "3": feed = "rss://gdata.youtube.com/feeds/api/standardfeeds/recently_featured?alt=rss"
    if replace == "4": feed = "about:blank"

    return feed

def get_featured_name():
    replace = get_featured_feed_value()
    name = "Boxee Featured"

    if replace == "1": name = "Recently added"
    if replace == "2": name = "Vimeo staff picks"
    if replace == "3": name = "Youtube featured"
    if replace == "4": name = "Fanart"

    return name

def get_featured_feed_value():
    replace = common.file_get_contents("/data/etc/.replace_featured_enabled")
    if replace == "":
        replace = "0"
    return replace

# Enable/disable the subtitle functionality
def toggle_subtitles(mode, current):
    if mode == "all":
        subtitles = get_subtitles_enabled()

        if subtitles == "1":
            subtitles = "0"
        else:
            subtitles = "1"

        common.file_put_contents("/data/etc/.subtitles_enabled", subtitles)
        os.system("sh /data/hack/subtitles.sh")
        common.set_string("subtitles-plugin", subtitles)

    if mode == "language":
        if get_subtitles_language_filter() == "0" and current != "1":
            common.set_string("subtitles-plugin-language","1")
        else:
            config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })
            if os.path.exists("/data/etc/.subtitles"):
                config.read("/data/etc/.subtitles")
            config.set("DEFAULT", "lang", "All")

            if os.path.exists("/data/etc/.subtitles"):
                configfile = open("/data/etc/.subtitles", "w")
                config.write(configfile)
                configfile.close()

            common.set_string("subtitles-plugin-language","0")

# Edit the subtitle providers
def subtitle_provider(method, section, provider=None):
    config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })

    if os.path.exists("/data/etc/.subtitles"):
        config.read("/data/etc/.subtitles")

    plugins = config.get("DEFAULT", "plugins")	
    plugin_section = "default"
    config_section = "plugins"

    if section == "tv":
        plugins = config.get("DEFAULT", "tvplugins")
        plugin_section = "tv"
        config_section = "tvplugins"

    if section == "movie":
        plugins = config.get("DEFAULT", "movieplugins")
        plugin_section = "movie"
        config_section = "movieplugins"

    enabled_providers = plugins.split(',')
    if method == "get":
        if provider != None:
            if provider in enabled_providers:
                return 1
            else:
                return 0

        for checkprovider in available_providers:
            result = 0
            if checkprovider in enabled_providers:
                result = 1
            common.set_string("subtitles-plugin-%s-%s" % (plugin_section, checkprovider), result)

    if method == "set":
        provider_status = 1
        if provider in enabled_providers:
            provider_status = 0

        if provider_status == 1:
            enabled_providers.append(provider)
            common.set_string("subtitles-plugin-%s-%s" % (plugin_section, provider), "1")
        else:
            enabled_providers.remove(provider)
            common.set_string("subtitles-plugin-%s-%s" % (plugin_section, provider), "0")
        config.set("DEFAULT", config_section, ",".join(enabled_providers).strip(','))
        if os.path.exists("/data/etc/.subtitles"):
            configfile = open("/data/etc/.subtitles", "w")
            config.write(configfile)
            configfile.close()

# Get the remote version number from github
def get_remote_version():
    import urllib2
    u = urllib2.urlopen('https://raw.github.com/boxeehacks/boxeehack/master/hack/version')
    version_remote = "%s" % u.read()
    return version_remote

# Get the version number for the locally installed version
def get_local_version():
    version_local = common.file_get_contents("/data/hack/version")
    return version_local

# Check for newer version
def check_new_version():
    version_remote = get_remote_version()
    version_local = get_local_version()
    
    version_remote_parts = version_remote.split(".")
    version_local_parts = version_local.split(".")

    hasnew = 0
    if version_remote_parts[0] > version_local_parts[0]:
        hasnew = 1
    elif version_remote_parts[0] == version_local_parts[0]:
        if version_remote_parts[1] > version_local_parts[1]:
            hasnew = 1
        elif version_remote_parts[1] == version_local_parts[1]:
            if version_remote_parts[2] > version_local_parts[2]:
                hasnew = 1
    issame = 0
    if version_remote_parts[0] == version_local_parts[0]:
        if version_remote_parts[1] == version_local_parts[1]:
            if version_remote_parts[2] == version_local_parts[2]:
                issame = 1

    dialog = xbmcgui.Dialog()
    if hasnew:
        if dialog.yesno("BOXEE+HACKS Version", "A new version of BOXEE+ is available. Upgrade to %s now?" % (version_remote)):
            os.system("sh /data/hack/upgrade.sh")
    elif issame:
        dialog.ok("BOXEE+HACKS Version", "Your BOXEE+ version is up to date.")
    else:
        dialog.ok("BOXEE+HACKS Version", "Hi there Doc Brown. How's the future?")

def shutdown():
    os.system("poweroff")

if (__name__ == "__main__"):
    command = sys.argv[1]

    if command == "telnet": set_telnet_password()
    if command == "subtitles": toggle_subtitles(sys.argv[2], sys.argv[3])
    if command == "version": check_new_version()
    if command == "defaults": register_defaults()
    if command == "subtitles-provider": subtitle_provider("set", sys.argv[2], sys.argv[3])
    if command == "featured_next": featured_next()
    if command == "featured_previous": featured_previous()
    if len(sys.argv) == 4:
        if command == "homeenabled": toggle_homeenabled(sys.argv[2], sys.argv[3])
    else:
        if command == "homeenabled": toggle_homeenabled(sys.argv[2], "")
        
    if command == "browser-homepage": set_browser_homepage()
    if command == "toggle-jump-to-last-unwatched": toggle_jump_to_last_unwatched()

    if command == "shutdown": shutdown()

########NEW FILE########
__FILENAME__ = boxeehack_setwatched
import time
import os,sys
import xbmc, xbmcgui, mc
import subprocess
import common
import time

from pysqlite2 import dbapi2 as sqlite

def get_window_id(special):
	if special == True:
		return xbmcgui.getCurrentWindowDialogId()
	else:
		return xbmcgui.getCurrentWindowId()

def get_list(listNum, special):
	try:
		lst = mc.GetWindow(get_window_id(special)).GetList(listNum)
	except:
		lst = ""
	return lst
	
def get_jump_to_last_unwatched_value():
	jumpenabled = common.file_get_contents("/data/etc/.jump_to_unwatched_enabled")
	if jumpenabled == "":
		jumpenabled = "0"
	return jumpenabled

def focus_last_unwatched(listNum):
	global fanart_changed
	
	jumpenabled = get_jump_to_last_unwatched_value()
	if jumpenabled == "0":
		return
	
	# sometimes the list control isn't available yet onload
	# so add some checking to make sure
	lst = get_list(listNum, False)
	prevLen = 0
	count = 10
	while count > 0:
		time.sleep(0.1)
		lst = get_list(listNum, False)
		count = count - 1
		
		if lst != "":
			newLen = len(lst.GetItems())
			if newLen != prevLen:
				count = 5
			prevLen = newLen
	
	if lst == "" or len(lst.GetItems()) <= 2:
		pass
	else:
		item = lst.GetItem(1)
		items = lst.GetItems()
		lastItem = items[-1]

		more = 1
		reverse = 0

		if item.GetSeason() < lastItem.GetSeason():
			reverse = 1
		if item.GetSeason() == lastItem.GetSeason() and item.GetEpisode() < lastItem.GetEpisode():
			reverse = 1
		if item.GetSeason() == 1 and item.GetEpisode() == 1:
			reverse = 1

		if reverse == 0:
			info_count = 0
			focus = info_count
			for item in items:
				watched = "%s" % mc.GetInfoString("Container(52).ListItem("+str(info_count)+").Property(watched)")
				
				info_count = info_count + 1
				if watched == "0" and info_count > focus and more == 1:
					focus = info_count
				
				if watched == "1":
					more = 0
		else:
			info_count = len(items) - 1
			focus = info_count
			for item in items:
				watched = "%s" % mc.GetInfoString("Container(52).ListItem("+str(info_count)+").Property(watched)")
				
				if watched == "0" and info_count < focus and more == 1:
					focus = info_count + 1
				info_count = info_count - 1
				
				if watched == "1":
					more = 0

		# make sure the list still exists
		lst = get_list(listNum, False)
		if lst != "":
			lst.SetFocusedItem(focus)

def set_watched(command):
	lst = get_list(52, False)
	count = 10
	while lst == "" and count > 0:
		time.sleep(0.1)
		lst = get_list(52, False)
		count = count - 1
		
	if lst == "":
		pass
	else:
		item = lst.GetItem(1)

		series = mc.GetInfoString("Container(52).ListItem.TVShowTitle")
		itemList = lst.GetItems()
		seasons = []
		episodes_count = 0
		for item in itemList:
			season = item.GetSeason()
			if(season != -1):
				seasons.append(season)
				episodes_count = episodes_count + 1

		seasons = dict.fromkeys(seasons)
		seasons = seasons.keys()

		use_season = -1
		display_name = series
		season_string = ""
		if(len(seasons) == 1):
			season_string = " Season %s" % (seasons[0])
			use_season = seasons[0]

		dialog = xbmcgui.Dialog()
		if dialog.yesno("Watched", "Do you want to mark all episodes of %s%s as %s?" % (series, season_string, command)):
			progress = xbmcgui.DialogProgress()
			progress.create('Updating episodes', 'Setting %s%s as %s' % (series, season_string, command))

			current_count = 0
			info_count = 0

			db_path = xbmc.translatePath('special://profile/Database/') + "./boxee_user_catalog.db"
			conn = sqlite.connect(db_path, 100000)
			c = conn.cursor()
			
			for item in itemList:
				episode = item.GetEpisode()
				boxeeid = mc.GetInfoString("Container(52).ListItem("+str(info_count)+").Property(boxeeid)")
				info_count = info_count + 1
				print boxeeid

				if(episode != -1):
					current_count = current_count+1
					percent = int( ( episodes_count / current_count ) * 100)
					message = "Episode " + str(current_count) + " out of " + str(episodes_count)
					progress.update( percent, "", message, "" )
					path = item.GetPath()

					# First make sure we don't get double values in the DB, so remove any old ones				
					sql = "DELETE FROM watched WHERE strPath = \""+str(path).strip()+"\" or (strBoxeeId != \"\" AND strBoxeeId = \""+str(boxeeid).strip()+"\");"
					c.execute(sql)

					if command == "watched":
						sql = "INSERT INTO watched VALUES(null, \""+path+"\", \""+boxeeid+"\", 1, 0, -1.0);"
						c.execute(sql)

			c.execute("REINDEX;")

			conn.commit()
			c.close()
			conn.close()
			
			lst = get_list(52, False)
			if lst != "":
				lst.Refresh()
			xbmc.executebuiltin("XBMC.ReplaceWindow(10483)")

			progress.close()

			mc.ShowDialogNotification("%s marked as %s..." % (display_name, command))

if (__name__ == "__main__"):
	command = sys.argv[1]
	if command == "watched": set_watched("watched")
	if command == "unwatched": set_watched("unwatched")
	if command == "focus_last_unwatched": focus_last_unwatched(int(sys.argv[2]))

########NEW FILE########
__FILENAME__ = boxeehack_sublangs
import sys
import os
import xbmcgui
import xbmc
import string
import ConfigParser

try: current_dlg_id = xbmcgui.getCurrentWindowDialogId()
except: current_dlg_id = 0
current_win_id = xbmcgui.getCurrentWindowId()

LANGUAGE_LIST = 120

SELECT_ITEM = ( 11, 256, 61453, )
EXIT_SCRIPT = ( 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )
SELECT_BUTTON = ( 229, 259, 261, 61453, )
MOVEMENT_UP = ( 166, 270, 61478, )
MOVEMENT_DOWN = ( 167, 271, 61480, )

class GUI( xbmcgui.WindowXMLDialog ):

    trans_lang = {'aa' : 'Afar',
    'ab' : 'Abkhaz',
    'ae' : 'Avestan',
    'af' : 'Afrikaans',
    'ak' : 'Akan',
    'am' : 'Amharic',
    'an' : 'Aragonese',
    'ar' : 'Arabic',
    'as' : 'Assamese',
    'av' : 'Avaric',
    'ay' : 'Aymara',
    'az' : 'Azerbaijani',
    'ba' : 'Bashkir',
    'be' : 'Belarusian',
    'bg' : 'Bulgarian',
    'bh' : 'Bihari',
    'bi' : 'Bislama',
    'bm' : 'Bambara',
    'bn' : 'Bengali',
    'bo' : 'Tibetan',
    'br' : 'Breton',
    'bs' : 'Bosnian',
    'ca' : 'Catalan',
    'ce' : 'Chechen',
    'ch' : 'Chamorro',
    'co' : 'Corsican',
    'cr' : 'Cree',
    'cs' : 'Czech',
    'cu' : 'Old Church Slavonic',
    'cv' : 'Chuvash',
    'cy' : 'Welsh',
    'da' : 'Danish',
    'de' : 'German',
    'dv' : 'Divehi',
    'dz' : 'Dzongkha',
    'ee' : 'Ewe',
    'el' : 'Greek',
    'en' : 'English',
    'eo' : 'Esperanto',
    'es' : 'Spanish',
    'et' : 'Estonian',
    'eu' : 'Basque',
    'fa' : 'Persian',
    'ff' : 'Fula',
    'fi' : 'Finnish',
    'fj' : 'Fijian',
    'fo' : 'Faroese',
    'fr' : 'French',
    'fy' : 'Western Frisian',
    'ga' : 'Irish',
    'gd' : 'Scottish Gaelic',
    'gl' : 'Galician',
    'gn' : 'Guaraní',
    'gu' : 'Gujarati',
    'gv' : 'Manx',
    'ha' : 'Hausa',
    'he' : 'Hebrew',
    'hi' : 'Hindi',
    'ho' : 'Hiri Motu',
    'hr' : 'Croatian',
    'ht' : 'Haitian',
    'hu' : 'Hungarian',
    'hy' : 'Armenian',
    'hz' : 'Herero',
    'ia' : 'Interlingua',
    'id' : 'Indonesian',
    'ie' : 'Interlingue',
    'ig' : 'Igbo',
    'ii' : 'Nuosu',
    'ik' : 'Inupiaq',
    'io' : 'Ido',
    'is' : 'Icelandic',
    'it' : 'Italian',
    'iu' : 'Inuktitut',
    'ja' : 'Japanese (ja)',
    'jv' : 'Javanese (jv)',
    'ka' : 'Georgian',
    'kg' : 'Kongo',
    'ki' : 'Kikuyu',
    'kj' : 'Kwanyama',
    'kk' : 'Kazakh',
    'kl' : 'Kalaallisut',
    'km' : 'Khmer',
    'kn' : 'Kannada',
    'ko' : 'Korean',
    'kr' : 'Kanuri',
    'ks' : 'Kashmiri',
    'ku' : 'Kurdish',
    'kv' : 'Komi',
    'kw' : 'Cornish',
    'ky' : 'Kirghiz, Kyrgyz',
    'la' : 'Latin',
    'lb' : 'Luxembourgish',
    'lg' : 'Luganda',
    'li' : 'Limburgish',
    'ln' : 'Lingala',
    'lo' : 'Lao',
    'lt' : 'Lithuanian',
    'lu' : 'Luba-Katanga',
    'lv' : 'Latvian',
    'mg' : 'Malagasy',
    'mh' : 'Marshallese',
    'mi' : 'Maori',
    'mk' : 'Macedonian',
    'ml' : 'Malayalam',
    'mn' : 'Mongolian',
    'mr' : 'Marathi',
    'ms' : 'Malay',
    'mt' : 'Maltese',
    'my' : 'Burmese',
    'na' : 'Nauru',
    'nb' : 'Norwegian',
    'nd' : 'North Ndebele',
    'ne' : 'Nepali',
    'ng' : 'Ndonga',
    'nl' : 'Dutch',
    'nn' : 'Norwegian Nynorsk',
    'no' : 'Norwegian',
    'nr' : 'South Ndebele',
    'nv' : 'Navajo, Navaho',
    'ny' : 'Chichewa; Chewa; Nyanja',
    'oc' : 'Occitan',
    'oj' : 'Ojibwe, Ojibwa',
    'om' : 'Oromo',
    'or' : 'Oriya',
    'os' : 'Ossetian, Ossetic',
    'pa' : 'Panjabi, Punjabi',
    'pi' : 'Pali',
    'pl' : 'Polish',
    'ps' : 'Pashto, Pushto',
    'pt' : 'Portuguese',
    'pb' : 'Brazilian',
    'qu' : 'Quechua',
    'rm' : 'Romansh',
    'rn' : 'Kirundi',
    'ro' : 'Romanian',
    'ru' : 'Russian',
    'rw' : 'Kinyarwanda',
    'sa' : 'Sanskrit',
    'sc' : 'Sardinian',
    'sd' : 'Sindhi',
    'se' : 'Northern Sami',
    'sg' : 'Sango',
    'si' : 'Sinhala, Sinhalese',
    'sk' : 'Slovak',
    'sl' : 'Slovene',
    'sm' : 'Samoan',
    'sn' : 'Shona',
    'so' : 'Somali',
    'sq' : 'Albanian',
    'sr' : 'Serbian',
    'ss' : 'Swati',
    'st' : 'Southern Sotho',
    'su' : 'Sundanese',
    'sv' : 'Swedish',
    'sw' : 'Swahili',
    'ta' : 'Tamil',
    'te' : 'Telugu',
    'tg' : 'Tajik',
    'th' : 'Thai',
    'ti' : 'Tigrinya',
    'tk' : 'Turkmen',
    'tl' : 'Tagalog',
    'tn' : 'Tswana',
    'to' : 'Tonga',
    'tr' : 'Turkish',
    'ts' : 'Tsonga',
    'tt' : 'Tatar',
    'tw' : 'Twi',
    'ty' : 'Tahitian',
    'ug' : 'Uighur',
    'uk' : 'Ukrainian',
    'ur' : 'Urdu',
    'uz' : 'Uzbek',
    've' : 'Venda',
    'vi' : 'Vietnamese',
    'vo' : 'Volapük',
    'wa' : 'Walloon',
    'wo' : 'Wolof',
    'xh' : 'Xhosa',
    'yi' : 'Yiddish',
    'yo' : 'Yoruba',
    'za' : 'Zhuang, Chuang',
    'zh' : 'Chinese',
    'zu' : 'Zulu' }

    def __init__( self, *args, **kwargs ):
        pass

    def onInit( self ):
        self.setup()

    def onClick(self, controlID):
        item = self.getControl( LANGUAGE_LIST ).getSelectedItem()
        pos = self.getControl( LANGUAGE_LIST ).getSelectedPosition()
        lang = self.items[pos]
        if(item.getProperty("set") == "true"):
            item.setProperty("set", "false")
            self.removeFromConfig(lang)
        else:
            item.setProperty("set", "true")
            self.addToConfig(lang)

    def addToConfig(self, lang):
        config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })
        if os.path.exists("/data/etc/.subtitles"):
            config.read("/data/etc/.subtitles")
        else:
            self.close();

        langs_config = config.get("DEFAULT", "lang")
        if(langs_config.strip() == "" or langs_config == "All"):
            enabled_langs = []
        else:
            enabled_langs = map(lambda x : x.strip(), langs_config.split(","))

        if(lang not in enabled_langs):
            enabled_langs.append(lang)
        new_value = ",".join(enabled_langs).strip(',')
        if(new_value == ""):
            new_value = "All"
        config.set("DEFAULT", "lang", new_value)
        if os.path.exists("/data/etc/.subtitles"):
            configfile = open("/data/etc/.subtitles", "w")
            config.write(configfile)
            configfile.close()

    def removeFromConfig(self, lang):
        config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })
        if os.path.exists("/data/etc/.subtitles"):
            config.read("/data/etc/.subtitles")
        else:
            self.close();

        langs_config = config.get("DEFAULT", "lang")
        if(langs_config == "".strip() or langs_config == "All"):
            enabled_langs = []
        else:
            enabled_langs = map(lambda x : x.strip(), langs_config.split(","))
        
        if lang in enabled_langs:
            enabled_langs.remove(lang)

        new_value = ",".join(enabled_langs).strip(',')
        if(new_value == ""):
            new_value = "All"
        config.set("DEFAULT", "lang", new_value)

        if os.path.exists("/data/etc/.subtitles"):
            configfile = open("/data/etc/.subtitles", "w")
            config.write(configfile)
            configfile.close()

    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def onAction(self, action):
        if action in CANCEL_DIALOG:
            self.close()

    def setup(self):
        self.controlId = -1
        self.items = []
        config = ConfigParser.SafeConfigParser({"lang": "All", "plugins" : "BierDopje,OpenSubtitles", "tvplugins" : "BierDopje,OpenSubtitles", "movieplugins" : "OpenSubtitles" })

        if os.path.exists("/data/etc/.subtitles"):
            config.read("/data/etc/.subtitles")
        else:
            self.close();
    
        langs_config = config.get("DEFAULT", "lang")
        if(langs_config == "".strip() or langs_config == "All"):
            enabled_langs = []
        else:
            enabled_langs = map(lambda x : x.strip(), langs_config.split(","))
        
        for attr in sorted(self.trans_lang, key=self.trans_lang.get):
            listitem = xbmcgui.ListItem( label=self.trans_lang[attr], label2=attr, iconImage="0.0", thumbnailImage="" )
            if(attr in enabled_langs):
                listitem.setProperty('set', 'true')
            else:
                listitem.setProperty('set', 'false')
            self.items.append(attr)
            self.getControl( LANGUAGE_LIST ).addItem( listitem )
        
        #self.setFocus( self.getControl( LANGUAGE_LIST ) )
        #self.getControl( LANGUAGE_LIST ).setCurrentListPosition(0)

if (__name__ == "__main__"):
    print os.getcwd()
    ui = GUI("boxeehack_sublangs.xml", os.getcwd(), "Boxee")
    ui.doModal()
    del ui

########NEW FILE########
__FILENAME__ = common
import os,sys,mc,xbmcgui,xbmc

sys.path.append(os.path.abspath("./external"))

if 'linux' in sys.platform:
    sys.path.append(os.path.abspath("./external/Linux"))
elif 'win32' in sys.platform:
    sys.path.append(os.path.abspath("./external/win32"))
elif 'darwin' in sys.platform:
    sys.path.append(os.path.abspath("./external/OSX"))

def set_string(theid, thestr):
	if thestr != "":
		xbmc.executebuiltin("Skin.SetString(%s,%s)" % (theid, thestr) )
	
def get_window_id(special):
    if special == True:
        return xbmcgui.getCurrentWindowDialogId()
    else:
        return xbmcgui.getCurrentWindowId()

def get_control(controlNum, special):
    try:
        control = mc.GetWindow(get_window_id(special)).GetControl(controlNum)
    except:
        control = ""
    return control

def get_list(listNum, special):
    try:
        lst = mc.GetWindow(get_window_id(special)).GetList(listNum)
    except:
        lst = ""
    return lst
    
# Read file contents into a string
def file_get_contents(filename):
    if os.path.exists(filename):
        fp = open(filename, "r")
        content = fp.read()
        fp.close()
        return content
    return ""

# Write string back to a file
def file_put_contents(filename, content):
    fp = open(filename, "w")
    fp.write(content)
    fp.close()
########NEW FILE########
__FILENAME__ = dbapi2
#-*- coding: ISO-8859-1 -*-
# pysqlite2/dbapi2.py: the DB-API 2.0 interface
#
# Copyright (C) 2004-2005 Gerhard Häring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import datetime
import time

from pysqlite2._sqlite import *

paramstyle = "qmark"

threadsafety = 1

apilevel = "2.0"

Date = datetime.date

Time = datetime.time

Timestamp = datetime.datetime

def DateFromTicks(ticks):
    return apply(Date, time.localtime(ticks)[:3])

def TimeFromTicks(ticks):
    return apply(Time, time.localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    return apply(Timestamp, time.localtime(ticks)[:6])

version_info = tuple([int(x) for x in version.split(".")])
sqlite_version_info = tuple([int(x) for x in sqlite_version.split(".")]) 

Binary = buffer

def register_adapters_and_converters():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    def convert_date(val):
        return datetime.date(*map(int, val.split("-")))

    def convert_timestamp(val):
        datepart, timepart = val.split(" ")
        year, month, day = map(int, datepart.split("-"))
        timepart_full = timepart.split(".")
        hours, minutes, seconds = map(int, timepart_full[0].split(":"))
        if len(timepart_full) == 2:
            microseconds = int(float("0." + timepart_full[1]) * 1000000)
        else:
            microseconds = 0

        val = datetime.datetime(year, month, day, hours, minutes, seconds, microseconds)
        return val


    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)

register_adapters_and_converters()

# Clean up namespace

del(register_adapters_and_converters)

########NEW FILE########
__FILENAME__ = dbapi2
#-*- coding: ISO-8859-1 -*-
# pysqlite2/dbapi2.py: the DB-API 2.0 interface
#
# Copyright (C) 2004-2005 Gerhard Häring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import datetime
import time
import os,sys

#mc.ShowDialogNotification("%s" % sys.platform)

from pysqlite2._sqlite import *

paramstyle = "qmark"

threadsafety = 1

apilevel = "2.0"

Date = datetime.date

Time = datetime.time

Timestamp = datetime.datetime

def DateFromTicks(ticks):
    return apply(Date, time.localtime(ticks)[:3])

def TimeFromTicks(ticks):
    return apply(Time, time.localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    return apply(Timestamp, time.localtime(ticks)[:6])

version_info = tuple([int(x) for x in version.split(".")])
sqlite_version_info = tuple([int(x) for x in sqlite_version.split(".")]) 

Binary = buffer

def register_adapters_and_converters():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    def convert_date(val):
        return datetime.date(*map(int, val.split("-")))

    def convert_timestamp(val):
        datepart, timepart = val.split(" ")
        year, month, day = map(int, datepart.split("-"))
        timepart_full = timepart.split(".")
        hours, minutes, seconds = map(int, timepart_full[0].split(":"))
        if len(timepart_full) == 2:
            microseconds = int(float("0." + timepart_full[1]) * 1000000)
        else:
            microseconds = 0

        val = datetime.datetime(year, month, day, hours, minutes, seconds, microseconds)
        return val


    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)

register_adapters_and_converters()

# Clean up namespace

del(register_adapters_and_converters)

########NEW FILE########
__FILENAME__ = dbapi2
#-*- coding: ISO-8859-1 -*-
# pysqlite2/dbapi2.py: the DB-API 2.0 interface
#
# Copyright (C) 2004-2007 Gerhard Häring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import datetime
import time

from pysqlite2._sqlite import *

paramstyle = "qmark"

threadsafety = 1

apilevel = "2.0"

Date = datetime.date

Time = datetime.time

Timestamp = datetime.datetime

def DateFromTicks(ticks):
    return apply(Date, time.localtime(ticks)[:3])

def TimeFromTicks(ticks):
    return apply(Time, time.localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    return apply(Timestamp, time.localtime(ticks)[:6])

version_info = tuple([int(x) for x in version.split(".")])
sqlite_version_info = tuple([int(x) for x in sqlite_version.split(".")])

Binary = buffer

def register_adapters_and_converters():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    def convert_date(val):
        return datetime.date(*map(int, val.split("-")))

    def convert_timestamp(val):
        datepart, timepart = val.split(" ")
        year, month, day = map(int, datepart.split("-"))
        timepart_full = timepart.split(".")
        hours, minutes, seconds = map(int, timepart_full[0].split(":"))
        if len(timepart_full) == 2:
            microseconds = int(timepart_full[1])
        else:
            microseconds = 0

        val = datetime.datetime(year, month, day, hours, minutes, seconds, microseconds)
        return val


    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)

register_adapters_and_converters()

# Clean up namespace

del(register_adapters_and_converters)

########NEW FILE########
