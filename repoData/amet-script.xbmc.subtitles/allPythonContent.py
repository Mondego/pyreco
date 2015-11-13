__FILENAME__ = default
# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import xbmcaddon

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

import gui
from utilities import Pause

if xbmc.Player().isPlayingVideo():
  pause = Pause()
  ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
  if (not ui.set_allparam() or not ui.Search_Subtitles(False)):
    if __addon__.getSetting("pause") == "true":
      pause.pause()
    ui.doModal()
        
  del ui
  pause.restore()
  sys.modules.clear()
else:
  xbmc.executebuiltin((u'Notification(%s,%s,%s)' %(__scriptname__, __language__(611), "1000")).encode("utf-8")) 


  

########NEW FILE########
__FILENAME__ = gui
# -*- coding: utf-8 -*-

import os
import re
import sys
import xbmc
import urllib
import socket
import xbmcgui

from utilities import *

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__      = sys.modules[ "__main__" ].__addon__
__profile__    = sys.modules[ "__main__" ].__profile__
__version__    = sys.modules[ "__main__" ].__version__

class GUI( xbmcgui.WindowXMLDialog ):

  def __init__( self, *args, **kwargs ):
    pass

  def onInit( self ):
    self.on_run()

  def on_run( self ):
    if not xbmc.getCondVisibility("VideoPlayer.HasSubtitles"):
      self.getControl( 111 ).setVisible( False )
    self.list_services()
    try:
      self.Search_Subtitles()
    except:
      errno, errstr = sys.exc_info()[:2]
      xbmc.sleep(2000)
      self.close()

  def set_allparam(self):
    self.list            = []
    service_list         = []
    self.stackPath       = []
    service              = ""
    self.man_search_str  = ""
    self.temp            = False
    self.rar             = False
    self.stack           = False
    self.autoDownload    = False
    self.focused         = False
    use_subs_folder      = __addon__.getSetting( "use_subs_folder" ) == "true"           # use 'Subs' subfolder for storing subtitles
    movieFullPath        = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
    useMovieFolderForSubs= __addon__.getSetting( "subfolder" ) == "true"                 # True for movie folder
    self.sub_folder      = xbmc.translatePath(__addon__.getSetting( "subfolderpath" )).decode("utf-8")   # User specified subtitle folder
    self.year            = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    self.season          = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    self.episode         = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    self.mansearch       =  __addon__.getSetting( "searchstr" ) == "true"                # Manual search string??
    self.parsearch       =  __addon__.getSetting( "par_folder" ) == "true"               # Parent folder as search string
    self.language_1      = languageTranslate(__addon__.getSetting( "Lang01" ), 4, 0)     # Full language 1
    self.language_2      = languageTranslate(__addon__.getSetting( "Lang02" ), 4, 0)     # Full language 2
    self.language_3      = languageTranslate(__addon__.getSetting( "Lang03" ), 4, 0)     # Full language 3
    self.tmp_sub_dir     = os.path.join( __profile__ ,"sub_tmp" )                        # Temporary subtitle extraction directory
    self.stream_sub_dir  = os.path.join( __profile__ ,"sub_stream" )                     # Stream subtitle directory

    self.clean_temp()                                                                   # clean temp dirs

    if ( movieFullPath.find("http") > -1 ):
      self.sub_folder = self.stream_sub_dir
      self.temp = True

    elif ( movieFullPath.find("rar://") > -1 ):
      self.rar = True
      movieFullPath = os.path.dirname(movieFullPath[6:])

    elif ( movieFullPath.find("stack://") > -1 ):
      self.stackPath = movieFullPath.split(" , ")
      movieFullPath = self.stackPath[0][8:]
      self.stack = True

    if useMovieFolderForSubs and not self.temp:
      if use_subs_folder:
        self.sub_folder = os.path.join(os.path.dirname( movieFullPath ),'Subs')
        xbmcvfs.mkdirs(self.sub_folder)
      else:
        self.sub_folder = os.path.dirname( movieFullPath )

    if not xbmcvfs.exists(self.sub_folder):
      xbmcvfs.mkdir(self.sub_folder)

    if self.episode.lower().find("s") > -1:                                      # Check if season is "Special"
      self.season = "0"                                                          #
      self.episode = self.episode[-1:]                                           #

    self.tvshow = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    self.title  = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    if self.title == "":
      log( __name__, "VideoPlayer.OriginalTitle not found")
      self.title  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title :)

    if self.tvshow == "":
      if str(self.year) == "":                                            # If we have a year, assume no tv show
        self.title, self.year = xbmc.getCleanMovieTitle( self.title )     # Clean before trying tvshow regex, else we get false results on some movies
        if str(self.year) == "":                                          # Still no year: *could* be a tvshow
          title, season, episode = regex_tvshow(False, self.title)
          if title != "" and season != "" and episode != "":
            self.season = str(int(season))
            self.episode = str(int(episode))
            self.tvshow = title
          else:
            self.season = ""                                              # Reset variables: could contain garbage from tvshow regex above
            self.episode = ""
            self.tvshow = ""
    else:
      self.year = ""

    self.file_original_path = urllib.unquote ( movieFullPath )             # Movie Path

    if (__addon__.getSetting( "fil_name" ) == "true"):                     # Display Movie name or search string
      self.file_name = os.path.basename( movieFullPath )
    else:
      if (len(str(self.year)) < 1 ) :
        self.file_name = self.title.encode('utf-8')
        if (len(self.tvshow) > 0):
          self.file_name = "%s S%.2dE%.2d" % (self.tvshow.encode('utf-8'),
                                              int(self.season),
                                              int(self.episode)
                                             )
      else:
        self.file_name = "%s (%s)" % (self.title.encode('utf-8'), str(self.year))

    if ((__addon__.getSetting( "auto_download" ) == "true") and
        (__addon__.getSetting( "auto_download_file" ) != os.path.basename( movieFullPath ))):
         self.autoDownload = True
         __addon__.setSetting("auto_download_file", "")
         xbmc.executebuiltin((u"Notification(%s,%s,10000)" % (__scriptname__, _(763))).encode("utf-8"))

    for name in os.listdir(SERVICE_DIR):
      if os.path.isdir(os.path.join(SERVICE_DIR,name)) and __addon__.getSetting( name ) == "true":
        service_list.append( name )
        service = name

    if len(self.tvshow) > 0:
      def_service = __addon__.getSetting( "deftvservice")
    else:
      def_service = __addon__.getSetting( "defmovieservice")

    if service_list.count(def_service) > 0:
      service = def_service

    if len(service_list) > 0:
      if len(service) < 1:
        self.service = service_list[0]
      else:
        self.service = service

      self.service_list = service_list
      self.next = list(service_list)

      log( __name__ ,"Addon Version: [%s]"         % __version__)
      log( __name__ ,"Manual Search : [%s]"        % self.mansearch)
      log( __name__ ,"Default Service : [%s]"      % self.service)
      log( __name__ ,"Services : [%s]"             % self.service_list)
      log( __name__ ,"Temp?: [%s]"                 % self.temp)
      log( __name__ ,"Rar?: [%s]"                  % self.rar)
      log( __name__ ,"File Path: [%s]"             % self.file_original_path)
      log( __name__ ,"Year: [%s]"                  % str(self.year))
      log( __name__ ,"Tv Show Title: [%s]"         % self.tvshow)
      log( __name__ ,"Tv Show Season: [%s]"        % self.season)
      log( __name__ ,"Tv Show Episode: [%s]"       % self.episode)
      log( __name__ ,"Movie/Episode Title: [%s]"   % self.title)
      log( __name__ ,"Subtitle Folder: [%s]"       % self.sub_folder)
      log( __name__ ,"Languages: [%s] [%s] [%s]"   % (self.language_1, self.language_2, self.language_3))
      log( __name__ ,"Parent Folder Search: [%s]"  % self.parsearch)
      log( __name__ ,"Stacked(CD1/CD2)?: [%s]"     % self.stack)

    return self.autoDownload

  def Search_Subtitles( self, gui = True ):
    self.subtitles_list = []
    self.session_id = ""
    if gui:
      self.getControl( SUBTITLES_LIST ).reset()
      self.getControl( LOADING_IMAGE ).setImage(
                                       xbmc.translatePath(
                                         os.path.join(
                                           SERVICE_DIR,
                                           self.service,
                                           "logo.png")))

    exec ( "from services.%s import service as Service" % (self.service))
    self.Service = Service
    if gui:
      self.getControl( STATUS_LABEL ).setLabel( _( 646 ))
    msg = ""
    socket.setdefaulttimeout(float(__addon__.getSetting( "timeout" )))
    try:
      self.subtitles_list, self.session_id, msg = self.Service.search_subtitles(
                                                       self.file_original_path,
                                                       self.title,
                                                       self.tvshow,
                                                       self.year,
                                                       self.season,
                                                       self.episode,
                                                       self.temp,
                                                       self.rar,
                                                       self.language_1,
                                                       self.language_2,
                                                       self.language_3,
                                                       self.stack
                                                       )
    except socket.error:
      errno, errstr = sys.exc_info()[:2]
      if errno == socket.timeout:
        msg = _( 656 )
      else:
        msg =  "%s: %s" % ( _( 653 ),str(errstr[1]), )
    except:
      errno, errstr = sys.exc_info()[:2]
      msg = "Error: %s" % ( str(errstr), )
    socket.setdefaulttimeout(None)
    if gui:
      self.getControl( STATUS_LABEL ).setLabel( _( 642 ) % ( "...", ))

    if not self.subtitles_list:
      if __addon__.getSetting( "search_next" )== "true" and len(self.next) > 1:
        xbmc.sleep(1500)
        self.next.remove(self.service)
        self.service = self.next[0]
        self.show_service_list(gui)
        log( __name__ ,"Auto Searching '%s' Service" % (self.service))
        self.Search_Subtitles(gui)
      else:
        self.next = list(self.service_list)
        if gui:
          select_index = 0
          if msg != "":
            self.getControl( STATUS_LABEL ).setLabel( msg )
          else:
            self.getControl( STATUS_LABEL ).setLabel( _( 657 ))
          self.show_service_list(gui)
      if self.autoDownload:
        xbmc.executebuiltin((u"Notification(%s,%s,%i)" % (__scriptname__, _(767), 1000)).encode("utf-8"))
    else:
      subscounter = 0
      itemCount = 0
      list_subs = []
      mainLangISO = languageTranslate(self.language_1, 0, 3)
      for item in self.subtitles_list:
        if (self.autoDownload and item["sync"] and
            languageTranslate(item["language_name"], 0, 3) == mainLangISO
        ):
          self.Download_Subtitles(itemCount, True, gui)
          __addon__.setSetting("auto_download_file",
                               os.path.basename( self.file_original_path ))
          if self.autoDownload:
            xbmc.executebuiltin((u"Notification(%s,%s,%i)" % (__scriptname__, _(765), 1000)).encode("utf-8"))
          return True
        else:
          if gui:
            listitem = xbmcgui.ListItem(label=_( languageTranslate(item["language_name"],0,5)),
                                        label2=item["filename"],
                                        iconImage=item["rating"],
                                        thumbnailImage=item["language_flag"]
                                       )
            if item["sync"]:
              listitem.setProperty( "sync", "true" )
            else:
              listitem.setProperty( "sync", "false" )

            if item.get("hearing_imp", False):
              listitem.setProperty( "hearing_imp", "true" )
            else:
              listitem.setProperty( "hearing_imp", "false" )

            self.list.append(subscounter)
            subscounter = subscounter + 1
            list_subs.append(listitem)
        itemCount += 1

      if gui:
        label = '%i %s '"' %s '"'' % (len ( self.subtitles_list ),_( 744 ),self.file_name)
        self.getControl( STATUS_LABEL ).setLabel( label )
        self.getControl( SUBTITLES_LIST ).addItems( list_subs )
        self.setFocusId( SUBTITLES_LIST )
        self.getControl( SUBTITLES_LIST ).selectItem( 0 )
      if self.autoDownload:
        xbmc.executebuiltin((u"Notification(%s,%s,%i)" % (__scriptname__, _(767), 1000)).encode("utf-8"))
      return False

  def Download_Subtitles( self, pos, auto = False, gui = True ):
    if gui:
      if auto:
        self.getControl( STATUS_LABEL ).setLabel(  _( 763 ))
      else:
        self.getControl( STATUS_LABEL ).setLabel(  _( 649 ))
    compressed_subs = os.path.join( self.tmp_sub_dir, "compressed_subs.ext")
    compressed, language, file = self.Service.download_subtitles(self.subtitles_list,
                                                             pos,
                                                             compressed_subs,
                                                             self.tmp_sub_dir,
                                                             self.sub_folder,
                                                             self.session_id
                                                             )
    sub_lang = str(languageTranslate(language,0,2))

    if compressed:
      # backward compatibility
      if (file == ""):
        file = "zip"
      suffixed_compressed_subs = re.sub("\.ext$",".%s" % file,compressed_subs)
      os.rename(compressed_subs,suffixed_compressed_subs)
      log(__name__,"Extracting %s" % suffixed_compressed_subs)
      self.Extract_Subtitles(suffixed_compressed_subs,sub_lang, gui)
    else:
      sub_ext  = os.path.splitext( file )[1]
      if self.temp:
        sub_name = "temp_sub"
      else:
        sub_name = os.path.splitext( os.path.basename( self.file_original_path ))[0]
      if (__addon__.getSetting( "lang_to_end" ) == "true"):
        file_name = u"%s.%s%s" % ( sub_name, sub_lang, sub_ext )
      else:
        file_name = u"%s%s" % ( sub_name, sub_ext )
      file_from = file
      file_to = xbmc.validatePath(os.path.join(self.sub_folder, file_name)).decode("utf-8")
      # Create a files list of from-to tuples so that multiple files may be
      # copied (sub+idx etc')
      files_list = [(file_from,file_to)]
      # If the subtitle's extension sub, check if an idx file exists and if so
      # add it to the list
      if ((sub_ext == ".sub") and (os.path.exists(file[:-3]+"idx"))):
          log( __name__ ,"found .sub+.idx pair %s + %s" % (file_from,file_from[:-3]+"idx"))
          files_list.append((file_from[:-3]+"idx",file_to[:-3]+"idx"))
      for cur_file_from, cur_file_to in files_list:
         subtitle_set,file_path  = copy_files( cur_file_from, cur_file_to )
      # Choose the last pair in the list, second item (destination file)
      if subtitle_set:
        subtitle = files_list[-1][1]
        xbmc.Player().setSubtitles(subtitle.encode("utf-8"))
        self.close()
      else:
        if gui:
          self.getControl( STATUS_LABEL ).setLabel( _( 654 ))
          self.show_service_list(gui)

  def Extract_Subtitles( self, zip_subs, subtitle_lang, gui = True ):
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_subs,self.tmp_sub_dir)).encode('utf-8'))
    xbmc.sleep(1000)
    files = os.listdir(self.tmp_sub_dir)
    sub_filename = os.path.basename( self.file_original_path )
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
    subtitle_set = False
    if len(files) < 1 :
      if gui:
        self.getControl( STATUS_LABEL ).setLabel( _( 654 ))
        self.show_service_list(gui)
    else :
      if gui:
        self.getControl( STATUS_LABEL ).setLabel( _( 652 ))
      subtitle_set = False
      movie_sub = False
      episode = 0
      for zip_entry in files:
        if os.path.splitext( zip_entry )[1] in exts:
          subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
          if len(self.tvshow) > 0:
            title, season, episode = regex_tvshow(False, zip_entry)
            if not episode : episode = -1
          else:
            if os.path.splitext( zip_entry )[1] in exts:
              movie_sub = True
          if ( movie_sub or int(episode) == int(self.episode)):
            if self.stack:
              try:
                for subName in self.stackPath:
                  if (re.split("(?x)(?i)\CD(\d)",
                      zip_entry)[1]) == (re.split("(?x)(?i)\CD(\d)",
                      urllib.unquote ( subName ))[1]
                      ):
                    subtitle_file, file_path = self.create_name(
                                                    zip_entry,
                                                    urllib.unquote(os.path.basename(subName[8:])),
                                                    subtitle_lang
                                                               )
                    subtitle_set,file_path = copy_files( subtitle_file, file_path )
                if re.split("(?x)(?i)\CD(\d)", zip_entry)[1] == "1":
                  subToActivate = file_path
              except:
                subtitle_set = False
            else:
              subtitle_set,subToActivate = copy_files( subtitle_file, file_path )

      if not subtitle_set:
        for zip_entry in files:
          if os.path.splitext( zip_entry )[1] in exts:
            subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
            subtitle_set,subToActivate  = copy_files( subtitle_file, file_path )

    if subtitle_set :
      xbmc.Player().setSubtitles(subToActivate.encode("utf-8"))
      self.close()
    else:
      if gui:
        self.getControl( STATUS_LABEL ).setLabel( _( 654 ))
        self.show_service_list(gui)

  def clean_temp( self ):
    for temp_dir in [self.stream_sub_dir,self.tmp_sub_dir]:
      rem_files(temp_dir)


  def show_service_list(self,gui):
    try:
      select_index = self.service_list.index(self.service)
    except IndexError:
      select_index = 0
    if gui:
      self.setFocusId( SERVICES_LIST )
      self.getControl( SERVICES_LIST ).selectItem( select_index )

  def create_name(self,zip_entry,sub_filename,subtitle_lang):
    if self.temp:
      name = "temp_sub"
    else:
      name = os.path.splitext( sub_filename )[0]
    if (__addon__.getSetting( "lang_to_end" ) == "true"):
      file_name = u"%s.%s%s" % ( name,
                                 subtitle_lang,
                                 os.path.splitext( zip_entry )[1] )
    else:
      file_name = u"%s%s" % ( name, os.path.splitext( zip_entry )[1] )
    log( __name__ ,"Sub in Archive [%s], File Name [%s]" % (zip_entry,
                                                        file_name))
    ret_zip_entry = xbmc.validatePath(os.path.join(self.tmp_sub_dir,zip_entry)).decode("utf-8")
    ret_file_name = xbmc.validatePath(os.path.join(self.sub_folder,file_name)).decode("utf-8")
    return ret_zip_entry,ret_file_name

  def list_services( self ):
    self.list = []
    all_items = []
    self.getControl( SERVICES_LIST ).reset()
    for serv in self.service_list:
      listitem = xbmcgui.ListItem( serv )
      self.list.append(serv)
      listitem.setProperty( "man", "false" )
      all_items.append(listitem)

    if self.mansearch :
        listitem = xbmcgui.ListItem( _( 612 ))
        listitem.setProperty( "man", "true" )
        self.list.append("Man")
        all_items.append(listitem)

    if self.parsearch :
        listitem = xbmcgui.ListItem( _( 747 ))
        listitem.setProperty( "man", "true" )
        self.list.append("Par")
        all_items.append(listitem)

    listitem = xbmcgui.ListItem( _( 762 ))
    listitem.setProperty( "man", "true" )
    self.list.append("Set")
    all_items.append(listitem)
    self.getControl( SERVICES_LIST ).addItems( all_items )

  def keyboard(self, parent):
    dir, self.year = xbmc.getCleanMovieTitle(self.file_original_path, self.parsearch)
    if not parent:
      if self.man_search_str != "":
        srchstr = self.man_search_str
      else:
        srchstr = "%s (%s)" % (dir,self.year)
      kb = xbmc.Keyboard(srchstr, _( 751 ), False)
      text = self.file_name
      kb.doModal()
      if (kb.isConfirmed()): text, self.year = xbmc.getCleanMovieTitle(kb.getText())
      self.title = text
      self.man_search_str = text
    else:
      self.title = dir

    log( __name__ ,"Manual/Keyboard Entry: Title:[%s], Year: [%s]" % (self.title, self.year))
    if self.year != "" :
      self.file_name = "%s (%s)" % (self.file_name, str(self.year))
    else:
      self.file_name = self.title
    self.tvshow = ""
    self.next = list(self.service_list)
    self.Search_Subtitles()

  def onClick( self, controlId ):
    if controlId == SUBTITLES_LIST:
      self.Download_Subtitles( self.getControl( SUBTITLES_LIST ).getSelectedPosition())

    elif controlId == SERVICES_LIST:
      xbmc.executebuiltin("Skin.Reset(SubtitleSourceChooserVisible)")
      selection = str(self.list[self.getControl( SERVICES_LIST ).getSelectedPosition()])
      self.setFocusId( 120 )

      if selection == "Man":
        self.keyboard(False)
      elif selection == "Par":
        self.keyboard(True)
      elif selection == "Set":
        __addon__.openSettings()
        self.set_allparam()
        self.on_run()
      else:
        self.service = selection
        self.next = list(self.service_list)
        self.Search_Subtitles()

  def onFocus( self, controlId ):
    if controlId == 150:
      if not self.focused:
        try:
          select_index = self.service_list.index(self.service)
        except IndexError:
          select_index = 0
        self.getControl( SERVICES_LIST ).selectItem(select_index)
        self.focused = True
    else:
      self.focused = False

  def onAction( self, action ):
    if ( action.getId() in CANCEL_DIALOG):
      self.close()


########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Subdivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__


main_url = "http://www.argenteam.net/search/"
debug_pretext = "argenteam"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

'''
<div class="search-item-desc">
	<a href="/episode/29322/The.Mentalist.%282008%29.S01E01-Pilot">
	
<div class="search-item-desc">
	<a href="/movie/25808/Awake.%282007%29">
'''

search_results_pattern = "<div\sclass=\"search-item-desc\">(.+?)<a\shref=\"/(episode|movie)/(.+?)/(.+?)\">(.+?)</a>"

subtitle_pattern = "<div\sclass=\"links\">(.+?)<strong>Descargado:</strong>(.+?)ve(ces|z)(.+?)<div>(.+?)<a\shref=\"/subtitles/(.+?)/(.+?)\">(.+?)</a>"

#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, tvshow, season, episode):
	
	if languageshort == "es":
		#log( __name__ ,"TVShow: %s" % (tvshow))
		if len(tvshow) > 0:
			url = main_url + urllib.quote_plus(searchstring)
		else:
			#searchstring = re.sub('\([0-9]{4}\)','',searchstring)
			url = main_url + urllib.quote_plus(searchstring)
			
	content = geturl(url)
	#subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': searchstring, 'sync': False, 'id' : 1, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
	#if isinstance(season, int ) and isinstance(episode, int ):
	
	#for matches in re.finditer(search_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
		#tipo = matches.group(2)
		#id = matches.group(3)
		#link = matches.group(4)
		
		#url_subtitle = "http://www.argenteam.net/" + tipo +"/"+ id +"/"+link
		
		#content_subtitle = geturl(url_subtitle)
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
			#log( __name__ ,"Descargas: %s" % (matches.group(2)))
			
		id = matches.group(6)
		filename=urllib.unquote_plus(matches.group(7))
		server = filename
		downloads = int(matches.group(2)) / 1000
		if (downloads > 10):
			downloads=10
			#server = matches.group(4).encode('ascii')
			#log( __name__ ,"Resultado Subtítulo 2: %s" % (matches.group(6)))
		subtitles_list.append({'rating': str(downloads), 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
	
	
def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        #log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    #log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    searchstring = searchstring + ' ' + year
    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)

    if spanish == 0:
        msg = "Won't work, argenteam is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    server = subtitles_list[pos][ "server" ]
    language = subtitles_list[pos][ "language_name" ]

    if string.lower(language) == "spanish":
        url = "http://www.argenteam.net/subtitles/" + id + "/"

    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            #log( __name__ ,"%s argenteam: el contenido es RAR" % (debug_pretext)) #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "argenteam.rar")
            #log( __name__ ,"%s argenteam: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "argenteam.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            #log( __name__ ,"%s argenteam: escribo en %s" % (debug_pretext, local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            pass
            #log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            #log( __name__ ,"%s argenteam: número de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file.encode("utf-8") + "," + tmp_sub_dir.encode("utf-8") +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output


########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Asiateam.net subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, urlparse
from utilities import log


_ = sys.modules[ "__main__" ].__language__


main_url = "http://subs.asia-team.net/search.php?term=%s&mtype=0&id=0&sort=file_name&order=asc&limit=900" #url changed
debug_pretext = "asiateam"
DEBUG = True

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

subtitle_pattern = "<a href=\"file.php\?id=(.*?)\">(.*?)</a>"

#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, tvshow, season, episode):		
		
	url= main_url.replace("%s",searchstring)
	url = url.replace(' ','%20') #replace spaces
	content= geturl(url)
	log(__name__ ,"%s Getting url: %s" % (debug_pretext, content))
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
		id = matches.group(1)
		filename=matches.group(2)
		server = "http://www.asia-team.net"
		subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    searchstring = title

    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)

    if spanish == 0:
        msg = "Won't work, Asia-Team is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    filename = subtitles_list[pos][ "filename" ]
    url = "http://subs.asia-team.net/download.php?id=" + id
	
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        opener = urllib2.build_opener(SmartRedirectHandler())
        content = opener.open(req)
    except ImportError, inst:
        status,location = inst	
        response= urllib.urlopen(location)
        content=response.read()
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            log( __name__ ,"%s asia-team: el contenido es RAR" % (debug_pretext))
            local_tmp_file = os.path.join(tmp_sub_dir, filename+".rar")
            log( __name__ ,"%s asia-team: local_tmp_file %s" % (debug_pretext, local_tmp_file))
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, filename+".zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "asia-team.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            log( __name__ ,"%s asia-team: escribo en %s" % (debug_pretext, local_tmp_file))
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,"%s asia-team: número de init_filecount %s" % (debug_pretext, init_filecount))
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))			
                try:
                    file = choice_one(files) #open new dialog to select file
                    subs_file = os.path.join(tmp_sub_dir,file)
                    return False, language, subs_file #standard output
                except:
                    return False, language, "" #standard output				

		
def choice_one(files):
    options = []
    sub_list = []
    Number = 0
    
    for file in files:
        if (string.split(file, '.')[-1] in ['srt','sub','txt','idx','ssa']):		
            Number = Number + 1
            options.append("%02d) %s" % (Number , file))
            sub_list.append(file)
    choice = xbmcgui.Dialog()
    selection = choice.select("Nº) SUBTITULO", options)
    log( __name__ ,"selection=%d" % (selection))
    if selection!= -1:
        return sub_list[selection]


class SmartRedirectHandler(urllib2.HTTPRedirectHandler):	
	def http_error_302(self, req, fp, code, msg, headers):
			# Some servers (incorrectly) return multiple Location headers
			# (so probably same goes for URI).  Use first header.
			if 'location' in headers:
				newurl = headers.getheaders('location')[0]
			elif 'uri' in headers:
				newurl = headers.getheaders('uri')[0]
			else:
				return
			newurl=newurl.replace(' ','%20') # <<< TEMP FIX - inserting this line temporarily fixes this problem
			newurl = urlparse.urljoin(req.get_full_url(), newurl)
			raise ImportError(302,newurl)
########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

import sys
import os
import re
import time
import urllib
import urllib2
import xbmc
import xbmcgui
import string
import shutil
from utilities import log, languageTranslate, getShowId
from xml.dom import minidom


_ = sys.modules[ "__main__" ].__language__

user_agent = 'Mozilla/5.0 (compatible; XBMC.Subtitle; XBMC)'

apikey = 'db81cb96baf8'
apiurl = 'api.betaseries.com'


def get_languages(languages):
    if languages == 'VF':
        code = 'fr'
    if languages == 'VO':
        code = 'en'
    if languages == 'VOVF':
        code = 'fr'
    return code 

def geturl(url):
    log( __name__ , " Getting url: %s" % (url))
    try:
        import urllib
        response = urllib.urlopen(url)
        content = response.read()
    except Exception, inst: 
        log( __name__ , " Failed to get url: %s" % (url))
        log( __name__ , " Error: %s" % (inst))
        content = None
    return(content)

def getShortTV(title):
    try:
        tvdbid = getShowId()
        if tvdbid:
            log( __name__ , 'found show from tvdb: %s' % (tvdbid))
            # get tvshow's url from TVDB's id
            searchurl = 'http://' + apiurl + '/shows/display/' + tvdbid + '.xml?key=' + apikey
            log( __name__ , " BetaSeries query : %s" % (searchurl))

            dom = minidom.parse(urllib.urlopen(searchurl))

            if len(dom.getElementsByTagName('url')):
                url = dom.getElementsByTagName('url')[0].childNodes[0]
                url = url.nodeValue
                return [url]

        else:
            log( __name__ , 'show not found from tvdb, try to find from betaseries search')
            searchurl = 'http://' + apiurl + '/shows/search.xml?title=' + urllib.quote(title) + '&key=' + apikey
            log( __name__ , "search %s on betaseries" % (searchurl))
            dom = minidom.parse(urllib.urlopen(searchurl))
            log( __name__ , " found %s shows" % (dom.getElementsByTagName('url').length) )
            return [ e.childNodes[0].nodeValue for e in dom.getElementsByTagName('url') ]
    except Exception as inst:
        log( __name__, "Error: %s" % (inst))

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""

    lang1 = languageTranslate(lang1,0,2)
    lang2 = languageTranslate(lang2,0,2)
    lang3 = languageTranslate(lang3,0,2)
    querylang = ""
    if lang1 == 'en' or lang2 == 'en' or lang3 == 'en': querylang = "VO"
    if lang1 == 'fr' or lang2 == 'fr' or lang3 == 'fr': querylang += "VF"
    log( __name__ , "query language: '%s'" % (querylang))

    lang_priorities = []
    for lang in [lang1, lang2, lang3]:
        if lang not in lang_priorities: lang_priorities.append(lang)

    if (len(file_original_path) > 0) and (len(tvshow) > 0) :

        shows = getShortTV(tvshow)
        if shows:
            for show in shows:
                searchurl = 'http://' + apiurl + '/subtitles/show/' + show + '.xml?season=' + season + '&episode=' + episode + '&language=' + querylang + '&key=' + apikey
                log( __name__ , "searchurl = '%s'" % (searchurl))

                try:
                    # parsing shows from xml
                    dom = minidom.parse(urllib.urlopen(searchurl))

                    #time.sleep(1)
                    subtitles = dom.getElementsByTagName('subtitle')
                    log( __name__ , "nb sub found for show '%s': '%s'" % (show, len(subtitles)))
                    for subtitle in subtitles:
                        url = subtitle.getElementsByTagName('url')[0].childNodes[0]
                        url = url.nodeValue

                        filename = subtitle.getElementsByTagName('file')[0].childNodes[0]
                        filename = filename.nodeValue

                        language = subtitle.getElementsByTagName('language')[0].childNodes[0]
                        language = get_languages(language.nodeValue)

                        rating = subtitle.getElementsByTagName('quality')[0].childNodes[0]
                        #rating = rating.nodeValue
                        rating = str(int(round(float(rating.nodeValue) / 5 * 9)))

                        ext = os.path.splitext(filename)[1]
                        #log( __name__ , "file : '%s' ext : '%s'" % (filename,ext))
                        if ext == '.zip':
                            if len(subtitle.getElementsByTagName('content'))>0:
                                #log( __name__ , "zip content ('%s')" % (filename))
                                content = subtitle.getElementsByTagName('content')[0]
                                items = content.getElementsByTagName('item')

                                for item in items:
                                    if len(item.childNodes) < 1 : continue
                                    subfile = item.childNodes[0].nodeValue

                                    if os.path.splitext(subfile)[1] == '.zip': continue # Not supported yet ;)

                                    search_string = "(s%#02de%#02d)|(%d%#02d)|(%dx%#02d)" % (int(season), int(episode),int(season), int(episode),int(season), int(episode))
                                    queryep = re.search(search_string, subfile, re.I)
                                    #log( __name__ , "ep: %s found: %s" % (search_string,queryep))
                                    if queryep == None: continue



                                    langs = re.search('\.(VF|VO|en|fr)\..*.{3}$',subfile,re.I)
                                    #langs = langs.group(1)
                                    #log( __name__ , "detect language... %s" % (subfile))
                                    try:
                                        langs = langs.group(1)
                                        lang = {
                                            "fr": 'fr',
                                            "FR": 'fr',
                                            "en": 'en',
                                            "EN": 'en',
                                            "VF": 'fr',
                                            "vf": 'fr',
                                            "VO": 'en',
                                            "vo": 'en'
                                        }[langs]
                                        #log( __name__ , "language: %s" % (lang))
                                    except:
                                        lang = language

                                    if lang != lang1 and lang != lang2 and lang != lang3: continue

                                    #log( __name__ , "subfile = '%s'" % (subfile))
                                    subtitles_list.append({
                                        'filename'          : subfile,
                                        'link'              : url,
                                        'language_name'     : languageTranslate(lang,2,0),
                                        'language_index'    : lang_priorities.index(lang),
                                        'language_flag'     : 'flags/' + lang + '.gif',
                                        'rating'            : rating,
                                        'sync'              : False,
                                        })
                            else:
                                log( __name__ , "not valid content! dumping XML...")
                                log( __name__ , dom.toxml())

                        else:
                            #log( __name__ , "sub found ('%s')" % (filename))

                            subtitles_list.append({
                                'filename'          : filename,
                                'link'              : url,
                                'language_name'     : languageTranslate(language,2,0),
                                'language_index'    : lang_priorities.index(language),
                                'language_flag'     : 'flags/' + language + '.gif',
                                'rating'            : rating,
                                'sync'              : False
                                })

                except Exception, inst:
                    log( __name__ , " Error: %s" % (inst))
                    return subtitles_list, "", msg #standard output

    return sorted(subtitles_list, key=lambda x: x['language_index']), "", msg #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    link = subtitles_list[pos][ "link" ]
    language = subtitles_list[pos][ "language_name" ]
    filename = subtitles_list[pos][ "filename" ]
    log( __name__ ,"language: %s" % (language))
    log( __name__ ,"filename: %s" % (filename))
    subs_file = ""
    content = geturl(link)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            log( __name__ ,"fichier RAR") #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.rar")
            log( __name__ ,"local_tmp_file %s" % (local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        try:
            log( __name__ ,"Writing %s" % (local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,"nombre de fichiers %s" % (init_filecount)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt','ass']):
                    mtime = os.stat(os.path.join(tmp_sub_dir.encode("utf-8"), file.encode("utf-8"))).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            log( __name__ ,"extraction... %s" % (local_tmp_file)) #EGO
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    log( __name__ ,"file inside: %s" % (file))
                    if (string.split(file,'.')[-1] in ['srt','sub','txt','ass']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                        if filecount == (init_filecount + 1): filename = file
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
            else:
                log( __name__ ,"Unpacked files in '%s'" % (tmp_sub_dir))
                log( __name__ ,"Checking our file '%s'" % (os.path.join(tmp_sub_dir, filename)))
                if os.path.exists(os.path.join(tmp_sub_dir, filename)):
                    file = str(os.path.normpath(os.path.join(tmp_sub_dir, filename)))
                    log( __name__ ,"selected file : '%s'" % ( file))
                    ext = os.path.splitext(file)[1]
                    if ext == '.zip':
                        log( __name__ ,"target file is zipped, copy to '%s'" % (zip_subs))
                        shutil.copy(file, zip_subs)
                        return True, language, ""

                    subs_file = file

    return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = service
import mechanize
import cookielib
import re
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import difflib
from utilities import languageTranslate, log
from BeautifulSoup import BeautifulSoup

main_url = "http://koray.al/"
debug_pretext = "Divxplanet:"

def getmediaUrl(mediaArgs):
    query = "site:divxplanet.com inurl:sub/m \"%s ekibi\" intitle:\"%s\" intitle:\"(%s)\"" % (mediaArgs[0], mediaArgs[1], mediaArgs[2])
    br = mechanize.Browser()
    log( __name__ ,"Finding media %s" % query)
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    br.open("http://www.google.com")
    # Select the search box and search for 'foo'
    br.select_form( 'f' )
    br.form[ 'q' ] = query
    br.submit()
    page = br.response().read()
    soup = BeautifulSoup(page)

    linkdictionary = []
    query.replace(" ", "-")
    for li in soup.findAll('li', attrs={'class':'g'}):
        sLink = li.find('a')
        sSpan = li.find('span', attrs={'class':'st'})
        if sLink:
            linkurl = re.search(r"\/url\?q=(http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/.*.\.html).*", sLink["href"])
            if linkurl:
                linkdictionary.append({"text": sSpan.getText().encode('ascii', 'ignore'), "name": mediaArgs[0], "url": linkurl.group(1)})
    log( __name__ ,"found media: %s" % (linkdictionary[0]["url"]))
    return linkdictionary[0]["url"]

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log( __name__ ,"searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        tvurl = getmediaUrl(["dizi",tvshow, year])
        log( __name__ ,"got media url %s" % (tvurl))
        divpname = re.search(r"http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/(.*.)\.html", tvurl).group(1)
        season = int(season)
        episode = int(episode)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            if info:
                tse = info[0].div.findAll("b", text="%d" % season)
                tep = info[0].div.findAll("b", text="%02d" % episode)
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                if tse and tep and lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    subtitles_list.append({'link'    : addr,
                                     'movie'         : tvshow,
                                     'filename'      : "%s" % (info[1].getText()),
                                     'description'   : "%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short),
                                     'language_flag' : "flags/%s.gif" % lan_short,
                                     'language_name' : language,
                                     'sync'          : False,
                                     'rating'        : "0" })
        br.close()
        log( __name__ ,"found %d subtitles" % (len(subtitles_list)))
    else:
        log( __name__ ,"searching subtitles for %s %s" % (title, year))
        tvurl = getmediaUrl(["film", title, year])
        log( __name__ ,"got media url %s" % (tvurl))
        divpname = re.search(r"http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/(.*.)\.html", tvurl).group(1)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            log( __name__ ,"found a link")
            if info:
                log( __name__ ,"found info: %s" % info)
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                log( __name__ ,"lan : %s lantext : %s" % (lan[0]["title"], lantext))
                if lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    filename = "no-description"
                    if info[0].getText() != "":
                        filename = info[0].getText()
                    log( __name__ ,"found a subtitle with description: %s" % (filename))
                    subtitles_list.append({'link'    : addr,
                                     'movie'         : title,
                                     'filename'      : "%s" % (filename),
                                     'description'   : "%s.%s" % (title, lan_short),
                                     'language_flag' : "flags/%s.gif" % lan_short,
                                     'language_name' : language,
                                     'sync'          : False,
                                     'rating'        : "0" })
                    log( __name__ ,"added subtitle to list")
        br.close()
        log( __name__ ,"found %d subtitles" % (len(subtitles_list)))
    return subtitles_list, "", ""


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    packed = True
    dlurl = "http://divxplanet.com%s" % subtitles_list[pos][ "link" ]
    language = subtitles_list[pos]["language_name"]
    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    html = br.open(dlurl).read()
    br.select_form(name="dlform")
    br.submit()

    log( __name__ ,"Fetching subtitles using url '%s" % (dlurl))
    local_tmp_file = os.path.join(tmp_sub_dir, subtitles_list[pos]["description"] + ".rar")
    try:
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        if not os.path.exists(tmp_sub_dir):
            os.makedirs(tmp_sub_dir)
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(br.response().get_data())
        local_file_handle.close()
    except:
        log( __name__ ,"%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
    if packed:
        files = os.listdir(tmp_sub_dir)
        init_filecount = len(files)
        max_mtime = 0
        filecount = init_filecount
        # determine the newest file from tmp_sub_dir
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
                mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                if mtime > max_mtime:
                    max_mtime =  mtime
        init_max_mtime = max_mtime
        time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
        waittime  = 0
        while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
            time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
            files = os.listdir(tmp_sub_dir)
            filecount = len(files)
            # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if (mtime > max_mtime):
                        max_mtime =  mtime
            waittime  = waittime + 1
        if waittime == 20:
            log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
        else:
            log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
            for file in files:
                # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                if (string.split(file, '.')[-1] in ['srt', 'sub']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                    log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                    subs_file = os.path.join(tmp_sub_dir, file)
    log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
    br.close()
    return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import sys
import os
import xbmc,xbmcgui

import urllib2,urllib,re
from utilities import log, hashFile, languageTranslate

_ = sys.modules[ "__main__" ].__language__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	log(__name__,"Starting search by TV Show")
	if (tvshow == None or tvshow == ''):
		log(__name__,"No TVShow name, stop")
		return [],"",""

	cli = EdnaClient()
	found_tv_shows = cli.search_show(tvshow)
	if (found_tv_shows.__len__() == 0):
		log(__name__,"TVShow not found, stop")
		return [],"",""
	elif (found_tv_shows.__len__() == 1):
		log(__name__,"One TVShow found, auto select")
		tvshow_url = found_tv_shows[0]['url']
	else:
		log(__name__,"More TVShows found, user dialog for select")
		menu_dialog = []
		for found_tv_show in found_tv_shows:
			menu_dialog.append(found_tv_show['title'])
		dialog = xbmcgui.Dialog()
		found_tv_show_id = dialog.select(_( 610 ), menu_dialog)
		if (found_tv_show_id == -1):
			return [],"",""
		tvshow_url = found_tv_shows[found_tv_show_id]['url']
	log(__name__,"Selected show URL: " + tvshow_url)

	found_season_subtitles = cli.list_show_subtitles(tvshow_url,season)

	episode_subtitle_list = None

	for found_season_subtitle in found_season_subtitles:
		if (found_season_subtitle['episode'] == int(episode) and found_season_subtitle['season'] == int(season)):
			episode_subtitle_list = found_season_subtitle
			break

	if episode_subtitle_list == None:
		return [], "", ""

	result_subtitles = []
	for episode_subtitle in episode_subtitle_list['versions']:

		result_subtitles.append({
			'filename': episode_subtitle_list['full_title'],
			'link': cli.server_url + episode_subtitle['link'],
			'lang': lng_short2long(episode_subtitle['lang']),
			'rating': "0",
			'sync': False,
			'language_flag': 'flags/' + lng_short2flag(episode_subtitle['lang']) + '.gif',
			'language_name': lng_short2long(episode_subtitle['lang']),
		})

	log(__name__,result_subtitles)

	# Standard output -
	# subtitles list
	# session id (e.g a cookie string, passed on to download_subtitles),
	# message to print back to the user
	# return subtitlesList, "", msg
	return result_subtitles, "", ""

def download_subtitles (subtitles_list, pos, extract_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	selected_subtitles = subtitles_list[pos]

	log(__name__,'Downloading subtitles')
	res = urllib.urlopen(selected_subtitles['link'])
	subtitles_filename = re.search("Content\-Disposition: attachment; filename=\"(.+?)\"",str(res.info())).group(1)
	log(__name__,'Filename: %s' % subtitles_filename)
	# subs are in .zip or .rar
	subtitles_format = re.search("\.(\w+?)$", subtitles_filename, re.IGNORECASE).group(1)
	log(__name__,"Subs in %s" % subtitles_format)

	store_path_file = open(extract_subs,'wb')
	store_path_file.write(res.read())
	store_path_file.close()

	# Standard output -
	# True if the file is packed as zip: addon will automatically unpack it.
	# language of subtitles,
	# Name of subtitles file if not packed (or if we unpacked it ourselves)
	# return False, language, subs_file
	return True, selected_subtitles['lang'], subtitles_format

def lng_short2long(lang):
	if lang == 'CZ': return 'Czech'
	if lang == 'SK': return 'Slovak'
	return 'English'

def lng_long2short(lang):
	if lang == 'Czech': return 'CZ'
	if lang == 'Slovak': return 'SK'
	return 'EN'

def lng_short2flag(lang):
	return languageTranslate(lng_short2long(lang),0,2)


class EdnaClient(object):

	def __init__(self):
		self.server_url = "http://www.edna.cz"

	def search_show(self,title):
		enc_title = urllib.urlencode({ "q" : title})
		res = urllib.urlopen(self.server_url + "/vyhledavani/?" + enc_title)
		shows = []
		if re.search("/vyhledavani/\?q=",res.geturl()):
			log(__name__,"Parsing search result")
			res_body = re.search("<ul class=\"list serieslist\">(.+?)</ul>",res.read(),re.IGNORECASE | re.DOTALL)
			if res_body:
				for row in re.findall("<li>(.+?)</li>", res_body.group(1), re.IGNORECASE | re.DOTALL):
					show = {}
					show_reg_exp = re.compile("<h3><a href=\"(.+?)\">(.+?)</a></h3>",re.IGNORECASE | re.DOTALL)
					show['url'], show['title'] = re.search(show_reg_exp, row).groups()
					shows.append(show)
		else:
			log(__name__,"Parsing redirect to show URL")
			show = {}
			show['url'] = re.search(self.server_url + "(.+)",res.geturl()).group(1)
			show['title'] = title
			shows.append(show)
		return shows

	def list_show_subtitles(self, show_url, show_series):
		res = urllib.urlopen(self.server_url + show_url + "titulky/?season=" + show_series)
		if not res.getcode() == 200: return []
		subtitles = []
		html_subtitle_table = re.search("<table class=\"episodes\">.+<tbody>(.+?)</tbody>.+</table>",res.read(), re.IGNORECASE | re.DOTALL)
		if html_subtitle_table == None: return []
		for html_episode in re.findall("<tr>(.+?)</tr>", html_subtitle_table.group(1), re.IGNORECASE | re.DOTALL):
			subtitle = {}
			show_title_with_numbers = re.sub("<[^<]+?>", "",re.search("<h3>(.+?)</h3>", html_episode).group(1))
			subtitle['full_title'] = show_title_with_numbers
			show_title_with_numbers = re.search("S([0-9]+)E([0-9]+): (.+)",show_title_with_numbers).groups()
			subtitle['season'] = int(show_title_with_numbers[0])
			subtitle['episode'] = int(show_title_with_numbers[1])
			subtitle['title'] = show_title_with_numbers[2]
			subtitle['versions'] = []
			for subs_url, subs_lang in re.findall("a href=\"(.+?)\" class=\"flag\".+?><i class=\"flag\-.+?\">(cz|sk)</i>",html_episode):
				subtitle_version = {}
				subtitle_version['link'] = re.sub("/titulky/#content","/titulky/?direct=1",subs_url)
				subtitle_version['lang'] = subs_lang.upper()
				subtitle['versions'].append(subtitle_version)
			if subtitle['versions'].__len__() > 0: subtitles.append(subtitle)
		return subtitles

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service euTorrents.ph version 0.0.3
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service euTorrents.ph v0.0.3:
# Service working again, changed .me to .ph
# Fixed download bug when XBMC is set to Portuguese language and probably any other lang!
# Code re-arrange... no more annoying messages!
#
# NEW on Service euTorrents.ph v0.0.2:
# Added all site languages.
# Messages now in xbmc choosen language.
# Code re-arrange...
#
# Initial release of Service euTorrents.ph v0.0.1:
# First version of the service. Requests are welcome.
# Works with every language available on the site.
#
# euTorrents.ph subtitles, based on a mod of Undertext subtitles

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import languageTranslate, log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://eutorrents.ph/"
debug_pretext = "euTorrents"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
isLang = xbmc.getLanguage()
#DEBUG ONLY
#log( __name__ ,"%s isLang: '%s'" % (debug_pretext, isLang))

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
			<tr>
				<td class="lista"><a href="index.php?page=torrent-details&id=0b6431c18917842465b658c2d429cb9f50f9becc" title="My Life in the Air (2008) Ma vie en l'air">My Life in the Air (2008) Ma vie en l'air</a></td>
				<td class="lista"><a href="index.php?page=userdetails&id=94803"><span style='color: #333333'>Sammahel</span></a></td>
				<td class="lista"><img src="images/flag/gb.png" alt="English" /> <a href="download-subtitle.php?subid=3321">English</a></td>
				<td class="lista"><a href="download-subtitle.php?subid=3321"><img src="images/download.gif" border="0" /></a></td>
				<td class="lista"></td>
				<td class="lista">94.93 KB</td>
				<td class="lista">39</td>
				<td class="lista">&nbsp;</td>
			</tr>
"""

subtitle_pattern = "<tr>[\n\r\t][\n\r\t].+?index.php\?page=torrent-details.+?\">(.+?)</a></td>[\n\r\t][\n\r\t].+?page=userdetails.+?\'>(.+?)</span></a></td>[\n\r\t][\n\r\t].+?alt=\"(.+?)\" />.+?\?subid=(.+?)\">.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?\">(.+?)</td>"

# group(1) = Name, group(2) = Uploader, group(3) = Language, group(4) = ID, group(5) = Downloads
#====================================================================================================================
# Functions
#====================================================================================================================
def _from_utf8(text):
    if isinstance(text, str):
        return text.decode('utf-8')
    else:
        return text

def msgnote(site, text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	text = _from_utf8(text)
	site = _from_utf8(site)
	#log( __name__ ,"%s ipath: %s" % (debug_pretext, icon))
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):
	

	page = 1
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "euTuser" )
	password = __addon__.getSetting( "euTpass" )
	login_data = urllib.urlencode({'uid' : username, 'pwd' : password})
	#This is where you are logged in
	resp = opener.open('http://eutorrents.ph/index.php?page=login', login_data)
	#log( __name__ ,"%s Getting '%s'  ..." % (debug_pretext, resp))

	url = main_url + "subtitles.php?action=search&language=" + languageshort + "&pages=" + str(page) + "&search=" + urllib.quote_plus(searchstring)
	content = opener.open(url)
	content = content.read()
	content = content.decode('latin1')
	#log( __name__ ,"%s CONTENT: '%s'" % (debug_pretext, content))
	

	#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))

	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL) and page < 6:
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
			hits = matches.group(5)
			id = matches.group(4)
			uploader = string.strip(matches.group(2))
			downloads = int(matches.group(5)) / 10
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(1))
			desc = string.strip(matches.group(1))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			uploader = re.sub('\n',' ',uploader)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			uploader = re.sub(r'<[^<]+?>','', uploader)
			desc = re.sub(r'<[^<]+?>|[~]','', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			filename = filename + " " + "(sent by: " + uploader + ")" + "  " + hits + "hits"
			subtitles_list.append({'rating': str(downloads), 'filename': filename, 'uploader': uploader, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageTranslate(languageshort,3,2) + '.gif', 'language_name': languagelong})

		page = page + 1
		url = main_url + "subtitles.php?action=search&language=" + languageshort + "&pages=" + str(page) + "&search=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		content = content.decode('latin1')
	
		
### ANNOYING ###
#	if subtitles_list == []:
#		msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
#		msgnote(debug_pretext,"Try manual or parent dir!", 2000)
#	elif subtitles_list != []:
#		lst = str(subtitles_list)
#		if languagelong in lst:
#			msgnote(debug_pretext,"Found sub(s) in "  + languagelong + ".", 2000)
#		else:
#			msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
#			msgnote(debug_pretext,"Try manual or parent dir!", 2000)
		
#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp




def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	
	msgnote(debug_pretext,__language__(30153), 6000)
	getallsubs(searchstring, languageTranslate(lang1,0,3), lang1, file_original_path, subtitles_list, searchstring_notclean)
	getallsubs(searchstring, languageTranslate(lang2,0,3), lang2, file_original_path, subtitles_list, searchstring_notclean)
	getallsubs(searchstring, languageTranslate(lang3,0,3), lang3, file_original_path, subtitles_list, searchstring_notclean)

	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext,__language__(30154), 6000)
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "euTuser" )
	password = __addon__.getSetting( "euTpass" )
	login_data = urllib.urlencode({'uid' : username, 'pwd' : password})
	#This is where you are logged in
	resp = opener.open('http://eutorrents.ph/index.php?page=login', login_data)
	language = subtitles_list[pos][ "language_name" ]
	#Now you download the subtitles
	content = opener.open('http://eutorrents.ph/download-subtitle.php?subid=' + id)

	downloaded_content = content.read()

	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	
	fname = os.path.join(tmp_sub_dir,str(id))
	if content.info().get('Content-Disposition').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(downloaded_content)
	f.close()
	
	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
	msgnote(debug_pretext,__language__(30155), 3000)
	xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
	time.sleep(2)
	legendas_tmp = []
	# brunoga fixed solution for non unicode caracters
	fs_encoding = sys.getfilesystemencoding()
	for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
		for file in files:
			dirfile = os.path.join(root, file)
			ext = os.path.splitext(dirfile)[1][1:].lower()
			if ext in sub_ext:
				legendas_tmp.append(dirfile)
			elif os.path.isfile(dirfile):
				os.remove(dirfile)
	
	msgnote(debug_pretext,__language__(30156), 3000)
	searchrars = recursive_glob(extract_path, packext)
	searchrarcount = len(searchrars)
	if searchrarcount > 1:
		for filerar in searchrars:
			if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
				try:
					xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
				except:
					return False
	time.sleep(1)
	searchsubs = recursive_glob(extract_path, subext)
	searchsubscount = len(searchsubs)
	for filesub in searchsubs:
		nopath = string.split(filesub, extract_path)[-1]
		justfile = nopath.split(os.sep)[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
		#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
		releasefilename = filesearch[1][:len(filesearch[1])-4]
		releasedirname = filesearch[0].split(os.sep)
		if 'rar' in israr:
			releasedirname = releasedirname[-2]
		else:
			releasedirname = releasedirname[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
		#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
		subsfilename = justfile[:len(justfile)-4]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
		#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
		#Check for multi CD Releases
		multicds_pattern = "\+?(cd\d)\+?"
		multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#Start choosing the right subtitle(s)
		if searchsubscount == 1 and sync == True:
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
			break
		elif string.lower(subsfilename) == string.lower(releasefilename):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
			break
		elif string.lower(subsfilename) == string.lower(releasedirname):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
			break
		elif (multicdsubs != None) and (multicdsrls != None):
			multicdsubs = string.lower(multicdsubs.group(1))
			multicdsrls = string.lower(multicdsrls.group(1))
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
			#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
			if multicdsrls == multicdsubs:
				subs_file = filesub
				subtitle = subs_file
				break

	else:
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
		if len(legendas_tmp) > 1:
			dialog = xbmcgui.Dialog()
			subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
			if subtitle == extract_path+"/": subtitle = ""
		elif legendas_tmp:
			subtitle = legendas_tmp[0]
	
	msgnote(debug_pretext,__language__(30157), 3000)
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output


#	if content is not None:
#		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
#		if header == 'rar':
#			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".rar")
#			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
#			packed = True
#		elif header == 'zip':
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".zip")
#			packed = True
#		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".srt") # assume unpacked sub file is an '.srt'
#			subs_file = local_tmp_file
#			packed = False
#		log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
#		try:
#			log( __name__ ,"%s file: write in %s" % (debug_pretext, local_tmp_file)) #EGO
#			local_file_handle = open(local_tmp_file, "wb")
#			shutil.copyfileobj(content.fp, local_file_handle)
#			local_file_handle.close()
#		except:
#			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
#		if packed:
#			files = os.listdir(tmp_sub_dir)
#			init_filecount = len(files)
#			log( __name__ ,"%s file: number init_filecount %s" % (debug_pretext, init_filecount)) #EGO
#			filecount = init_filecount
#			max_mtime = 0
#			# determine the newest file from tmp_sub_dir
#			for file in files:
#				if (string.split(file,'.')[-1] in ['srt','sub','txt']):
#					mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
#					if mtime > max_mtime:
#						max_mtime =  mtime
#			init_max_mtime = max_mtime
#			time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
#			msgnote(debug_pretext,__language__(30155), 6000)
#			xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
#			waittime  = 0
#			while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
#				time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
#				files = os.listdir(tmp_sub_dir)
#				log( __name__ ,"%s DIRLIST '%s'" % (debug_pretext, files))
#				filecount = len(files)
#				# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
#				for file in files:
#					if (string.split(file,'.')[-1] in ['srt','sub','txt']):
#						mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
#						if (mtime > max_mtime):
#							max_mtime =  mtime
#				waittime  = waittime + 1
#			if waittime == 20:
#				log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
#			else:
#				msgnote(debug_pretext,__language__(30156), 3000)
#				log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
#				searchrars = recursive_glob(tmp_sub_dir, packext)
#				searchrarcount = len(searchrars)
#				if searchrarcount > 1:
#					for filerar in searchrars:
#						if filerar != os.path.join(tmp_sub_dir,'ldivx.rar') and filerar != os.path.join(tmp_sub_dir,'ldivx.zip'):
#							xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + tmp_sub_dir +")")
#				time.sleep(1)
#				searchsubs = recursive_glob(tmp_sub_dir, subext)
#				searchsubscount = len(searchsubs)
#				for filesub in searchsubs:
#					nopath = string.split(filesub, tmp_sub_dir)[-1]
#					justfile = nopath.split(os.sep)[-1]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
#					#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
#					releasefilename = filesearch[1][:len(filesearch[1])-4]
#					releasedirname = filesearch[0].split(os.sep)
#					if 'rar' in israr:
#						releasedirname = releasedirname[-2]
#					else:
#						releasedirname = releasedirname[-1]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
#					#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
#					subsfilename = justfile[:len(justfile)-4]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
#					#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
#					#Check for multi CD Releases
#					multicds_pattern = "\+?(cd\d)\+?"
#					multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#					multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#					#Start choosing the right subtitle(s)
#					if searchsubscount == 1 and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
#						break
#					elif string.lower(subsfilename) == string.lower(releasefilename) and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
#						break
#					elif string.lower(subsfilename) == string.lower(releasedirname) and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
#						break
#					elif (multicdsubs != None) and (multicdsrls != None) and sync == True:
#						multicdsubs = string.lower(multicdsubs.group(1))
#						multicdsrls = string.lower(multicdsrls.group(1))
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
#						#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
#						if multicdsrls == multicdsubs:
#							subs_file = filesub
#							break
#				else:
#					#If none is found just open a dialog box for browsing the temporary subtitle folder
#					sub_ext = "srt,aas,ssa,sub,smi"
#					sub_tmp = []
#					for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
#						for file in files:
#							dirfile = os.path.join(root, file)
#							ext = os.path.splitext(dirfile)[1][1:].lower()
#							if ext in sub_ext:
#								sub_tmp.append(dirfile)
#							elif os.path.isfile(dirfile):
#								os.remove(dirfile)
#					
#					# If there are more than one subtitle in the temp dir, launch a browse dialog
#					# so user can choose. If only one subtitle is found, parse it to the addon.
#					if len(sub_tmp) > 1:
#						dialog = xbmcgui.Dialog()
#						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, tmp_sub_dir+"/")
#						if subs_file == tmp_sub_dir+"/": subs_file = ""
#					elif sub_tmp:
#						subs_file = sub_tmp[0]
#		
#		msgnote(debug_pretext,__language__(30157), 3000)
#
#		return False, language, subs_file #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

import sys
import os
import urllib2
import re
import xbmc, xbmcgui, xbmcvfs
from BeautifulSoup import BeautifulSoup
from utilities import log, languageTranslate
from utilities import hashFileMD5

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, language1, language2, language3, stack ): #standard input
    subtitles_list = []
    msg = ""

    log(__name__, "Search GomTV with a file name, "+file_original_path)
    movieFullPath = xbmc.Player().getPlayingFile()
    video_hash = hashFileMD5( movieFullPath, buff_size=1024*1024 )
    if video_hash is None:
        msg = _(755)
        return subtitles_list, "", msg  #standard output
    webService = GomTvWebService()
    if len(tvshow) > 0:                                            # TvShow
        OS_search_string = ("%s S%.2dE%.2d" % (tvshow,
                                           int(season),
                                           int(episode),)
                                          ).replace(" ","+")      
    else:                                                          # Movie or not in Library
        if str(year) == "":                                          # Not in Library
            title, year = xbmc.getCleanMovieTitle( title )
        else:                                                        # Movie in Library
            year  = year
            title = title
        OS_search_string = title.replace(" ","+")
    subtitles_list = webService.SearchSubtitlesFromTitle( OS_search_string ,video_hash)
    log(__name__, "Found %d subtitles in GomTV" %len(subtitles_list))

    return subtitles_list, "", msg  #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    language = subtitles_list[pos][ "language_name" ]
    link = subtitles_list[pos][ "link" ]
    webService = GomTvWebService()
    log(__name__,  "parse subtitle page at %s" %link)
    url = webService.GetSubtitleUrl( link )
    log(__name__,  "download subtitle from %s" %url)
    try:
        fname = "gomtv-%s.smi" % subtitles_list[pos]["ID"]
        tmp_fname = os.path.join(tmp_sub_dir, fname)
        resp = urllib2.urlopen(url)
        f = open(tmp_fname, "w")
        f.write(resp.read())
        f.close()
    except:
        return False, language, ""
    return False, language, tmp_fname    #standard output
  
class GomTvWebService:
    root_url = "http://gom.gomtv.com"
    agent_str = "GomPlayer 2, 1, 23, 5007 (KOR)"

    def __init__ (self):
        pass

        
    def SearchSubtitlesFromTitle (self, searchString,key):
        subtitles = []
        subtitles = []

        q_url = "http://gom.gomtv.com/jmdb/search.html?key=%s" %key
        log(__name__, "search subtitle at %s"  %q_url)

        # main page
        req = urllib2.Request(q_url)
        req.add_header("User-Agent", self.agent_str)
        html = urllib2.urlopen(req).read()
        if "<div id='search_failed_smi'>" in html:
            log(__name__, "no result found")
            return []
        elif "<script>location.href" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        elif "<script>top.location.replace" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        # regular search result page
        soup = BeautifulSoup(html)
        subtitles = []
        for row in soup.find("table",{"class":"tbl_lst"}).findAll("tr")[1:]:
            a_node = row.find("a")
            if a_node is None:
                continue
            title = a_node.text
            lang_node_string = row.find("span",{"class":"txt_clr3"}).string
            url = self.root_url + a_node["href"]
            if u"한글" in lang_node_string:
                langlong  = "Korean"
            elif u"영문" in lang_node_string:
                langlong  = "English"
            else:   # [통합]
                langlong  = "Korean"
            langshort = languageTranslate(langlong, 0, 2)
            subtitles.append( {
                "link"          : url,
                "filename"      : title,
                "ID"            : key,
                "format"        : "smi",
                "sync"          : True,
                "rating"        : "0",
                "language_name" : langlong,
                "language_flag" : "flags/%s.gif" %langshort
            } )            
            
        q_url = "http://gom.gomtv.com/main/index.html?ch=subtitles&pt=l&menu=subtitles&lang=0&sValue=%s" %searchString
        print q_url
        log(__name__, "search subtitle at %s"  %q_url)

        # main page
        req = urllib2.Request(q_url)
        req.add_header("User-Agent", self.agent_str)
        html = urllib2.urlopen(req).read()
        if "<div id='search_failed_smi'>" in html:
            log(__name__, "no result found")
            return []
        elif "<script>location.href" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        elif "<script>top.location.replace" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        # regular search result page
        soup = BeautifulSoup(html)
        for row in soup.find("table",{"class":"tbl_lst"}).findAll("tr")[1:]:
            if row is None:
        	      continue
            a_node = row.find("a")
            if a_node is None:
                continue
            title = a_node.text
            lang_node_string = row.find("span",{"class":"txt_clr3"}).string
            url = self.root_url + a_node["href"]
            if u"한글" in lang_node_string:
                langlong  = "Korean"
            elif u"영문" in lang_node_string:
                langlong  = "English"
            else:   # [통합]
                langlong  = "Korean"
            langshort = languageTranslate(langlong, 0, 2)
            subtitles.append( {
                "link"          : url,
                "filename"      : title,
                "ID"            : key,
                "format"        : "smi",
                "sync"          : False,
                "rating"        : "0",
                "language_name" : langlong,
                "language_flag" : "flags/%s.gif" %langshort
            } )            
        return subtitles

    def parseRedirectionPage(self, html):
        url = re.split("\'",html)[1]
        if 'noResult' in url:   # no result (old style)
            print "Unusual result page, "+page_url
            return subtitles
        return self.root_url+url

    def GetSubtitleUrl (self, page_url):
        html = urllib2.urlopen(page_url).read()
        sp2 = ""
        if "a href=\"jamak://gom.gomtv.com" in html:
            sp = re.split("a href=\"jamak://gom.gomtv.com",html)[1]
            sp2 = re.split("\"",sp)[0]
        elif "onclick=\"downJm(" in html:
            s1 = re.split("onclick=\"downJm",html)[1]
            intSeq = re.split("'",s1)[1]
            capSeq = re.split("'",s1)[3]
            sp2 = "/main/index.html?pt=down&ch=subtitles&intSeq="+intSeq+"&capSeq="+capSeq
        else:
       	    return None
       	print sp2
        return self.root_url+sp2

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

main_url = "http://www.italiansubs.net/"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

#<input type="hidden" name="return" value="aHR0cDovL3d3dy5pdGFsaWFuc3Vicy5uZXQv" /><input type="hidden" name="c10b48443ee5730c9b5a0927736bd09f" value="1" />
unique_pattern = '<input type="hidden" name="return" value="([^\n\r\t ]+?)" /><input type="hidden" name="([^\n\r\t ]+?)" value="([^\n\r\t ]+?)" />'
#<a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1170"> Castle</a>
show_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+&amp;func=select&amp;id=[^\n\r\t ]+?)"> %s</a>'
#href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1171"> Stagione 1</a>
season_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=select&amp;id=[^\n\r\t ]+?)"> Stagione %s</a>'
#<img src='http://www.italiansubs.net/components/com_remository/images/folder_icons/category.gif' width=20 height=20><a name="1172"><a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1172"> 720p</a>
category_pattern = '<img src=\'http://www\.italiansubs\.net/components/com_remository/images/folder_icons/category\.gif\' width=20 height=20><a name="[^\n\r\t ]+?"><a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=select&amp;id=[^\n\r\t ]+?)"> ([^\n\r\t]+?)</a>'
#<a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=fileinfo&amp;id=7348">Dexter 3x02</a>
subtitle_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=fileinfo&amp;id=([^\n\r\t ]+?))">(%s %sx%02d.*?)</a>'
#<a href='http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=download&amp;id=7228&amp;chk=5635630f675375afbdd6eec317d8d688&amp;no_html=1'>
subtitle_download_pattern = '<a href=\'http://www\.italiansubs\.net/(index\.php\?option=com_remository&amp;Itemid=\d+?&amp;func=download&amp;id=%s&amp;chk=[^\n\r\t ]+?&amp;no_html=1\')>'


#====================================================================================================================
# Functions
#====================================================================================================================

def geturl(url):
    log( __name__ , " Getting url: %s" % (url))
    try:
        response = urllib2.urlopen(url)
        content = response.read()
    except:
        log( __name__ , " Failed to get url:%s" % (url))
        content = None
    return(content)


def login(username, password):
    log( __name__ , " Logging in with username '%s' ..." % (username))
    content= geturl(main_url + 'index.php')
    if content is not None:
        match = re.search('logouticon.png', content, re.IGNORECASE | re.DOTALL)
        if match:
            return 1
        else:
            match = re.search(unique_pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return_value = match.group(1)
                unique_name = match.group(2)
                unique_value = match.group(3)
                login_postdata = urllib.urlencode({'username': username, 'passwd': password, 'remember': 'yes', 'Submit': 'Login', 'remember': 'yes', 'option': 'com_user', 'task': 'login', 'silent': 'true', 'return': return_value, unique_name: unique_value} )
                cj = cookielib.CookieJar()
                my_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
                my_opener.addheaders = [('Referer', main_url)]
                urllib2.install_opener(my_opener)
                request = urllib2.Request(main_url + 'index.php',login_postdata)
                response = urllib2.urlopen(request).read()
                match = re.search('logouticon.png', response, re.IGNORECASE | re.DOTALL)
                if match:
                    return 1
                else:
                    return 0
    else:
        return 0


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
        italian = 0
        if (string.lower(lang1) == "italian") or (string.lower(lang2) == "italian") or (string.lower(lang3) == "italian"):
            username = __addon__.getSetting( "ITuser" )
            password = __addon__.getSetting( "ITpass" )
            if login(username, password):
                log( __name__ , " Login successful")
                content= geturl(main_url + 'index.php?option=com_remository&Itemid=6')
                if content is not None:
                    match = re.search(show_pattern % tvshow, content, re.IGNORECASE | re.DOTALL)
                    if match is None and tvshow[-1] == ")":
                        log( __name__ ," Year Bug? '%s'" % tvshow)
                        tvshow = tvshow[:-7]
                        match = re.search(show_pattern % tvshow, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        log( __name__ ," Tv show '%s' found" % tvshow)
                        content= geturl(main_url + match.group(1))
                        if content is not None:
                            match = re.search(season_pattern % season, content, re.IGNORECASE | re.DOTALL)
                            if match:
                                log( __name__ ," Season %s of tv show '%s' found" % (season, tvshow))
                                category = 'normal'
                                categorypage = match.group(1)
                                content= geturl(main_url + categorypage)
                                if content is not None:
                                    for matches in re.finditer(subtitle_pattern % (tvshow, int(season), int(episode)), content, re.IGNORECASE | re.DOTALL):
                                        filename = matches.group(3)
                                        id = matches.group(2)
                                        log( __name__ ," Adding '%s' to list of subtitles" % filename)
                                        subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'link' : categorypage, 'language_flag': 'flags/it.gif', 'language_name': 'Italian'})
                                    for matches in re.finditer(category_pattern, content, re.IGNORECASE | re.DOTALL):
                                        categorypage = matches.group(1)
                                        category = matches.group(2)
                                        log( __name__ ," Page for category '%s' found" % category)
                                        content= geturl(main_url + categorypage)
                                        if content is not None:
                                            for matches in re.finditer(subtitle_pattern % (tvshow, int(season), int(episode)), content, re.IGNORECASE | re.DOTALL):
                                                id = matches.group(2)
                                                filename = matches.group(3)
                                                log( __name__ ," Adding '%s (%s)' to list of subtitles" % (filename, category))
                                                subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': "%s (%s)" % (filename, category), 'sync': False, 'id' : id, 'link' : categorypage, 'language_flag': 'flags/it.gif', 'language_name': 'Italian'})
                            else:
                                log( __name__ ," Season %s of tv show '%s' not found" % (season, tvshow))
                                msg = "Season %s of tv show '%s' not found" % (season, tvshow)
                    else:
                        log( __name__ ," Tv show '%s' not found." % tvshow)
                        msg = "Tv show '%s' not found" % tvshow
            else:
                log( __name__ ," Login to Itasa failed. Check your username/password at the addon configuration.")
                msg = "Login to Itasa failed. Check your username/password at the addon configuration."
        else:
            msg = "Won't work, Itasa is only for Italian subtitles."
    else:
        msg = "Won't work, Itasa is only for tv shows."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    username = __addon__.getSetting( "ITuser" )
    password = __addon__.getSetting( "ITpass" )
    if login(username, password):
        log( __name__ , " Login successful")
        id = subtitles_list[pos][ "id" ]
        link = subtitles_list[pos][ "link" ]
        content= geturl(main_url + link)
        match = re.search(subtitle_download_pattern % id, content, re.IGNORECASE | re.DOTALL)
        if match:
            language = subtitles_list[pos][ "language_name" ]
            log( __name__ ," Fetching subtitles using url %s" % (main_url + match.group(1)))
            content = geturl(main_url + match.group(1))
            if content is not None:
                header = content[:4]
                if header == 'Rar!':
                    local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.rar")
                    packed = True
                elif header == 'PK':
                    local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.zip")
                    packed = True
                else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
                    local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.srt") # assume unpacked subtitels file is an '.srt'
                    subs_file = local_tmp_file
                    packed = False
                log( __name__ ," Saving subtitles to '%s'" % (local_tmp_file))
                try:
                    local_file_handle = open(local_tmp_file, "wb")
                    local_file_handle.write(content)
                    local_file_handle.close()
                except:
                    log( __name__ ," Failed to save subtitles to '%s'" % (local_tmp_file))
                if packed:
                    files = os.listdir(tmp_sub_dir)
                    init_filecount = len(files)
                    max_mtime = 0
                    filecount = init_filecount
                    # determine the newest file from tmp_sub_dir
                    for file in files:
                        if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                            mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                            if mtime > max_mtime:
                                max_mtime =  mtime
                    init_max_mtime = max_mtime
                    time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
                    xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
                    waittime  = 0
                    while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                        time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                        files = os.listdir(tmp_sub_dir)
                        filecount = len(files)
                        # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                        for file in files:
                            if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                                mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                                if (mtime > max_mtime):
                                    max_mtime =  mtime
                        waittime  = waittime + 1
                    if waittime == 20:
                        log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
                    else:
                        log( __name__ ," Unpacked files in '%s'" % (tmp_sub_dir))
                        for file in files:
                            # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                            if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                                log( __name__ ," Unpacked subtitles file '%s'" % (file))
                                subs_file = os.path.join(tmp_sub_dir, file)
                return False, language, subs_file #standard output
    log( __name__ ," Login to Itasa failed. Check your username/password at the addon configuration.")

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service LegendasDivx.com version 0.2.8
# Code based on Undertext service and the download function encode fix from legendastv service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service LegendasDivx.com v0.2.8:
# Fixed download bug when XBMC is set to Portuguese language and probably others.
# Some code cleanup
#
# NEW on Service LegendasDivx.com v0.2.7:
# Fixed bug on openelec based XBMC prevent the script to work
# Removed some XBMC messages from the script who were annoying!
# Some code cleanup
#
# NEW on Service LegendasDivx.com v0.2.6:
# Added English and Spanish. Now searches all site languages.
# Messages now in xbmc choosen language.
# Code re-arrange...
#
# NEW on Service LegendasDivx.com v0.2.5:
# Added PortugueseBrazilian. After a few requests the language is now available.
#
# NEW on Service LegendasDivx.com v0.2.4:
# Added uuid for better file handling, no more hangups.
#
# NEW on Service LegendasDivx.com v0.2.3:
# Fixed typo on the version.
# Added built-in notifications.
#
# NEW on Service LegendasDivx.com v0.2.2:
# Fixed pathnames using (os.sep). For sure :)
#
# NEW on Service LegendasDivx.com v0.2.1:
# Fixed bug when the file is played from a root path, no parent dir search\sync when that happens.
# Fixed pathnames to work with all OS (Win, Unix, etc).
# Added pattern to search several subtitle extensions.
#
# NEW on Service LegendasDivx.com v0.2.0:
# Better "star" rating, remember that the start rating is calculated using the number of hits/downloads.
# Fixed a bug in the SYNC subtitles, it wouldn't assume that any were sync (in the code), a dialog box would open in multi packs.
#
# NEW on Service LegendasDivx.com v0.1.9:
# When no sync subtitle is found and the pack has more then 1 sub, it will open a dialog box for browsing the substitles inside the multi pack.
#
# NEW on Service LegendasDivx.com v0.1.8:
# Uncompress rar'ed subtitles inside a rar file... yeh weird site...
#
# NEW on Service LegendasDivx.com v0.1.7:
# BUG found in multi packs is now fixed.
# Added more accuracy to the selection of subtitle to load. Now checks the release dirname against the subtitles downloaded.
# When no sync is found and if the substitle name is not equal to the release dirname or release filename it will load one random subtitle from the package.
#
# NEW on Service LegendasDivx.com v0.1.6:
# Movies or TV eps with 2cds or more will now work.
# Sync subs is now much more accurate.
#
# Initial Release of Service LegendasDivx.com - v0.1.5:
# TV Season packs now downloads and chooses the best one available in the pack
# Movie packs with several releases now works too, tries to choose the sync sub using filename or dirname
# Search description for SYNC subtitles using filename or dirname
#
# KNOWN BUGS (TODO for next versions):
# Regex isn't perfect so a few results might have html tags still, not many but ...
# Filtering languages, shows only European Portuguese flag.

# LegendasDivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid, xbmcvfs
from utilities import languageTranslate, log
from BeautifulSoup import *
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://www.legendasdivx.com/"
debug_pretext = "LegendasDivx"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = "srt,aas,ssa,sub,smi"
packext = ['rar', 'zip']

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="sub_box">
<div class="sub_header">
<b>The Dark Knight</b> (2008) &nbsp; - &nbsp; Enviada por: <a href='modules.php?name=User_Info&username=tck17'><b>tck17</b></a> &nbsp; em 2010-02-03 02:44:09

</div>
<table class="sub_main color1" cellspacing="0">
<tr>
<th class="color2">Idioma:</th>
<td><img width="18" height="12" src="modules/Downloads/img/portugal.gif" /></td>
<th>CDs:</th>
<td>1&nbsp;</td>
<th>Frame Rate:</th>
<td>23.976&nbsp;</td>
<td rowspan="2" class="td_right color2">
<a href="?name=Downloads&d_op=ratedownload&lid=128943">
<img border="0" src="modules/Downloads/images/rank9.gif"><br>Classifique (3 votos)

</a>
</td>
</tr>
<tr>
<th class="color2">Hits:</th>
<td>1842</td>
<th>Pedidos:</th>
<td>77&nbsp;</td>
<th>Origem:</th>
<td>DVD Rip&nbsp;</td>
</tr>

<tr>
<th class="color2">Descri��o:</th>
<td colspan="5" class="td_desc brd_up">N�o s�o minhas.<br />
<br />
Release: The.Dark.Knight.2008.720p.BluRay.DTS.x264-ESiR</td>
"""

subtitle_pattern = "<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>"
# group(1) = Name, group(2) = Year, group(3) = Number Files, group(4) = ID, group(5) = Hits, group(6) = Requests, group(7) = Description
#====================================================================================================================
# Functions
#====================================================================================================================
def _from_utf8(text):
	if isinstance(text, str):
		return text.decode('utf-8')
	else:
		return text

def msgnote(site, text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	text = _from_utf8(text)
	site = _from_utf8(site)
	#log( __name__ ,"%s ipath: %s" % (debug_pretext, icon))
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	page = 1
	if languageshort == "pt":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
	elif languageshort == "pb":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=29&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
	elif languageshort == "es":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=30&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
	elif languageshort == "en":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=31&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
	else:
		url = main_url + "index.php"

	content = geturl(url)
	log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 6:
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(5)
			id = matches.group(4)
			movieyear = matches.group(2)
			no_files = matches.group(3)
			downloads = int(matches.group(5)) / 300
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(1))
			desc = string.strip(matches.group(7))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			desc = re.sub(':.','',desc)
			desc = re.sub('br />','',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]','', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 1
		
		if languageshort == "pt":
			url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		elif languageshort == "pb":
			url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=29&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		elif languageshort == "es":
			url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=30&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		elif languageshort == "en":
			url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=31&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		else:
			url = main_url + "index.php"
			
		content = geturl(url)

### ANNOYING ###
#	if subtitles_list == []:
#		msgnote(debug_pretext,__language__(30150) + " "  + languagelong + "!", 2000)
#		msgnote(debug_pretext,__language__(30151), 2000)
#	elif subtitles_list != []:
#		lst = str(subtitles_list)
#		if languagelong in lst:
#			msgnote(debug_pretext,__language__(30152) + " "  + languagelong + ".", 2000)
#		else:
#			msgnote(debug_pretext,__language__(30150) + " "  + languagelong + "!", 2000)
#			msgnote(debug_pretext,__language__(30151), 2000)
	
			
#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp


def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	hasLang = languageTranslate(lang1,0,2) + " " + languageTranslate(lang2,0,2) + " " + languageTranslate(lang3,0,2)
	
	if re.search('pt', hasLang) or re.search('en', hasLang) or re.search('es', hasLang) or re.search('pb', hasLang):
		msgnote(debug_pretext,__language__(30153), 6000)
		getallsubs(searchstring, languageTranslate(lang1,0,2), lang1, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang2,0,2), lang2, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang3,0,2), lang3, file_original_path, subtitles_list, searchstring_notclean)
	else:
		msg = "Won't work, LegendasDivx.com is only for PT, PTBR, ES or EN subtitles."

	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext,__language__(30154), 6000)
	legendas_tmp = []
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "LDivxuser" )
	password = __addon__.getSetting( "LDivxpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	login_data = urllib.urlencode({'username' : username, 'user_password' : password, 'op' : 'login'})
	#This is where you are logged in
	resp = opener.open('http://www.legendasdivx.com/modules.php?name=Your_Account', login_data)
	#Now you can go to member only pages
	resp1 = opener.open('http://www.legendasdivx.com/modules.php?name=Your_Account&op=userinfo&bypass=1')
	d = resp1.read()
	#Now you download the subtitles
	language = subtitles_list[pos][ "language_name" ]
	content = opener.open('http://www.legendasdivx.com/modules.php?name=Downloads&d_op=getit&lid=' + id + '&username=' + username)
	downloaded_content = content.read()
	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	
	# Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
	# Write the subtitle in binary mode.
	fname = os.path.join(tmp_sub_dir,str(id))
	if content.info().get('Content-Type').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(downloaded_content)
	f.close()
	
	# brunoga fixed solution for non unicode caracters
	# Ps. Windows allready parses Unicode filenames.
	fs_encoding = sys.getfilesystemencoding()
	extract_path = extract_path.encode(fs_encoding)
	
	def _UNICODE(text):
		if text:
			return unicode(BeautifulSoup(text, fromEncoding="utf-8",  smartQuotesTo=None))
		else:
			return text


	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
	def extract_and_copy(extraction=0):
		i = 0
		for root, dirs, files in os.walk(extract_path, topdown=False):
			for file in files:
				dirfile = os.path.join(root, file)
				
				# Sanitize filenames - converting them to ASCII - and remove them from folders
				f = xbmcvfs.File(dirfile)
				temp = f.read()
				f.close()
				xbmcvfs.delete(dirfile)
				dirfile_with_path_name = os.path.relpath(dirfile, extract_path)
				dirfile_with_path_name = re.sub(r"[/\\]{1,2}","-", dirfile_with_path_name)
				dirfile_with_path_name = _UNICODE(dirfile_with_path_name).encode('ascii', 'ignore')
				new_dirfile = os.path.join(extract_path, dirfile_with_path_name)
				os.write(os.open(new_dirfile, os.O_RDWR | os.O_CREAT), temp)
				
				# Get the file extention
				ext = os.path.splitext(new_dirfile)[1][1:].lower()
				if ext in sub_ext and xbmcvfs.exists(new_dirfile):
					if not new_dirfile in legendas_tmp:
						#Append the matching file
						legendas_tmp.append(new_dirfile)
				elif ext in "rar zip" and not extraction:
					# Extract compressed files, extracted priorly
					xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (new_dirfile, extract_path))
					xbmc.sleep(1000)
					extract_and_copy(1)
				elif ext not in "idx": 
					xbmcvfs.delete(new_dirfile)
			for dir in dirs:
				dirfolder = os.path.join(root, dir)
				xbmcvfs.rmdir(dirfolder)

	xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (fname, extract_path))
	xbmc.sleep(1000)
	extract_and_copy()

	searchsubs = recursive_glob(extract_path, subext)
	searchsubscount = len(searchsubs)
	for filesub in searchsubs:
		nopath = string.split(filesub, extract_path)[-1]
		justfile = nopath.split(os.sep)[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
		#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
		releasefilename = filesearch[1][:len(filesearch[1])-4]
		releasedirname = filesearch[0].split(os.sep)
		if 'rar' in israr:
			releasedirname = releasedirname[-2]
		else:
			releasedirname = releasedirname[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
		#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
		subsfilename = justfile[:len(justfile)-4]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
		#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
		#Check for multi CD Releases
		multicds_pattern = "\+?(cd\d)\+?"
		multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#Start choosing the right subtitle(s)
		if searchsubscount == 1 and sync == True:
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
			break
		elif string.lower(subsfilename) == string.lower(releasefilename):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
			break
		elif string.lower(subsfilename) == string.lower(releasedirname):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
			break
		elif (multicdsubs != None) and (multicdsrls != None):
			multicdsubs = string.lower(multicdsubs.group(1))
			multicdsrls = string.lower(multicdsrls.group(1))
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
			#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
			if multicdsrls == multicdsubs:
				subs_file = filesub
				subtitle = subs_file
				break

	else:
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
		if len(legendas_tmp) > 1:
			dialog = xbmcgui.Dialog()
			subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
			if subtitle == extract_path+"/": subtitle = ""
		elif legendas_tmp:
			subtitle = legendas_tmp[0]
	
	msgnote(debug_pretext,__language__(30157), 3000)
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-
# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 2.1.1

from operator import itemgetter
from threading import Thread
from BeautifulSoup import *
from utilities import log, languageTranslate, getShowId
import cookielib
import math
import os
import re
import sys
import time
import urllib
import urllib2
import xbmc
import xbmcvfs
import xbmcgui
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Service variables
sub_ext = 'srt aas ssa sub smi'
global regex_1, regex_2, regex_3
regex_1 = "<div class=\"f_left\"><p><a href=\"([^\"]*)\">([^<]*)</a></p><p class=\"data\">.*?downloads, nota (\d*?),.*?<img .*? title=\"([^\"]*)\" /></div>"
regex_2 = "<button class=\"ajax\" data-href=\"/util/carrega_legendas_busca/id_filme:\d*/page:\d*\">(\d*)</button>"
regex_3 = "<button class=\"icon_arrow\" onclick=\"window.open\(\'([^\']*?)\', \'_self\'\)\">DOWNLOAD</button>"

# XBMC specific variables
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

def XBMC_OriginalTitle(OriginalTitle):
    MovieName =  xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
    if MovieName:
        OriginalTitle = MovieName
    else:
        ShowID = getShowId()
        if ShowID:
            HTTPResponse = urllib2.urlopen("http://www.thetvdb.com//data/series/%s/" % str(ShowID)).read()
            if re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL):
                OriginalTitle = re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL)[0]
    return OriginalTitle.encode('ascii', 'replace')

class LTVThread(Thread):
    def __init__ (self, obj, count, main_id, page):
        Thread.__init__(self)
        self.count = count
        self.main_id = main_id
        self.page = page
        self.obj = obj
        self.status = -1
        
    def run(self):
        fnc = self.obj.pageDownload(self.count, self.main_id, self.page)
        self.status = fnc

class LegendasTV:
    def __init__(self, **kargs):
        self.RegThreads = []
        self.cookie = ""
    
    def Log(self, message):
#        print "####  %s" % message.encode("utf-8")
        log(__name__, message)
        
    def _urlopen(self, request):
        try:
            return urllib2.urlopen(request).read()
        except urllib2.HTTPError:
            return ""

    def login(self, username, password):
        if self.cookie:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            return self.cookie
        else:
            self.cookie = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            login_data = urllib.urlencode({'_method':'POST', 'data[User][username]':username, 'data[User][password]':password})
            request = urllib2.Request("http://minister.legendas.tv/login/", login_data)
            response = self._UNICODE(urllib2.urlopen(request).read())
            if response.__contains__(u'Usuário ou senha inválidos'):
                self.Log( u" Login Failed. Check your data at the addon configuration.")
                return 0
            else: 
                return self.cookie

    def chomp(self, s):
        s = re.sub("\s{2,20}", " ", s)
        a = re.compile("(\r|\n|^\s|\s$|\'|\"|,|;|[(]|[)])")
        b = re.compile("(\t|-|:|[/]|[?]|\[|\]|\.)")
        s = b.sub(" ", s)
        s = re.sub("[ ]{2,20}", " ", s)
        s = a.sub("", s)
        return s

    def CleanLTVTitle(self, s):
        s = re.sub("[(]?[0-9]{4}[)]?$", "", s)
        s = re.sub("[ ]?&[ ]?", " ", s)
        s = re.sub("'", " ", s)
        s = self.chomp(s)
        s = s.title()
        return s
    
    def _UNICODE(self,text):
        if text:
            return unicode(BeautifulSoup(text, fromEncoding="utf-8",  smartQuotesTo=None))
        else:
            return text
        
    def CalculateRatio(self, a, b):
        # Calculate the probability ratio and append the result
        counter = 0
        Ratio = 0
        if len(a.split(" ")) > len(b.split(" ")):
            Paradigm, Guess = a, b
        else: 
            Paradigm, Guess = b, a
        if len(Paradigm.split(" ")):
            for Term in Paradigm.split(" "):
                if re.search(r"(^|\s)%s(\s|$)" % re.escape(Term), Guess, re.I):
                    counter += 1
            if counter:
                Ratio = "%.2f" % (float(counter) / float(len(Paradigm.split(" "))))
            else:
                Ratio = "%.2f" % float(0)
        else:
            if re.search("(^|\s)%s(\s|$)" % re.escape(Paradigm), Guess, re.I):
                Ratio = "%.2f" % float(1)
            else:
                Ratio = "%.2f" % float(0)
        return Ratio
                
    def _log_List_dict(self, obj, keys="", maxsize=100):
        Content = ""
        if not len(obj):
            return 0
        for key in keys.split():
            if not obj[0].has_key(key):
                continue
            maximum = max(len(unicode(k[key])) for k in obj)
            maximum = max(maximum+2, len(key)+2)
            if maximum > maxsize: maximum = maxsize
            Content = Content + "%s" % unicode(key)[:maxsize-2].ljust(maximum)
        self.Log(Content)
        for x, Result in enumerate(obj):
            Content = ""
            for key in keys.split():
                if not obj[0].has_key(key):
                    continue
                value = unicode(Result[key])
                if not len(value): continue
                maximum = max(len(unicode(k[key])) for k in obj)
                maximum = max(maximum+2, len(key)+2)
                if maximum > maxsize: maximum = maxsize
                Content = Content + "%s" % unicode(value)[:maxsize-2].ljust(maximum)
            self.Log(Content)
            if x > 30:
                break
        self.Log(" ")
        return 0

    def findID(self, Movie, TVShow, Year, Season, SearchTitle, SearchString):
        allResults, discardedResults, filteredResults, LTVSeason, LTVYear = [], [], [], 0, 0
        Response = self._urlopen("http://minister.legendas.tv/util/busca_titulo/" + urllib.quote_plus(SearchString))
        Response =  simplejson.loads(unicode(Response, 'utf-8', errors='ignore'))
        # Load the results
        # Parse and filter the results
        self.Log("Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)
        for R in Response:
            LTVSeason = 0
            if R.has_key('Filme') and R['Filme'].has_key('dsc_nome'):
                LTVTitle = self.CleanLTVTitle(R['Filme']['dsc_nome'])
                TitleBR = R['Filme']['dsc_nome_br']
                if re.findall(".*? - (\d{1,2}).*?emporada", TitleBR):
                    LTVSeason = re.findall(".*? - (\d{1,2}).*?emporada", TitleBR)[0]
                ContentID = R['Filme']['id_filme']
                # Calculate the probability ratio and append the result
                Ratio = self.CalculateRatio(LTVTitle, SearchTitle)
                allResults.append({"id" : ContentID, "title" : LTVTitle, "ratio" : Ratio, "year" : LTVYear, "season" : LTVSeason})
        # Return if there are no results
        if not len(allResults):
            self.Log("Message: The search [%s] didn't returned viable results." % SearchString)
            return "", ""
        # Filter tvshows for season or movies by year
        else:
            allResults = sorted(allResults, key=lambda k: k["ratio"], reverse=True)
            for Result in allResults:
                if TVShow:
                    if int(Season) == int(Result["season"]) or (not Result["season"] and Result["ratio"] == "1.00"):
                        if len(filteredResults):
                            if Result["ratio"] == filteredResults[0]["ratio"]:
                                filteredResults.append(Result)
                            else:
                                discardedResults.append(Result)
                        else:
                            filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
                elif Movie:
#                     if abs(int(Result["year"]) - int(Year)) <= 1 and math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                    if math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                        filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
            if not len(filteredResults):
                self.Log("Message: After filtration, search [%s] didn't returned viable results." % SearchString)
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id")
                return discardedResults, ""
            else:
                # Log filtered results
                self.Log("Message: After filtration, the search [%s] returned %s viable results." % (SearchString, len(filteredResults)))
                self.Log(" ")
                self.Log("Viable results:")
                self._log_List_dict(filteredResults, "ratio year title season id")
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id")
                return discardedResults, filteredResults
            
    def pageDownload(self, MainID, MainIDNumber, Page):
        # Log the page download attempt.
        self.Log("Message: Retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        
        Response = self._urlopen("http://minister.legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % (Page, MainID["id"]))

        if not re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL):
            self.Log("Error: Failed retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        else:
            for x, content in enumerate(re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL), start=1):
                LanguageName, LanguageFlag, LanguagePreference = "", "", 0
                download_id = content[0]
                title = self._UNICODE(content[1])
                release = self._UNICODE(content[1])
                rating =  content[2]
                lang = self._UNICODE(content[3])
                if re.search("Portugu.s-BR", lang):   LanguageId = "pb" 
                elif re.search("Portugu.s-PT", lang): LanguageId = "pt"
                elif re.search("Ingl.s", lang):       LanguageId = "en" 
                elif re.search("Espanhol", lang):     LanguageId = "es"
                elif re.search("Franc.s", lang):      LanguageId = "fr"
                else: continue
                for Preference, LangName in self.Languages:
                    if LangName == languageTranslate(LanguageId, 2, 0):
                        LanguageName = LangName
                        LanguageFlag = "flags/%s.gif" % LanguageId
                        LanguagePreference = Preference
                        break
                if not LanguageName:
                    continue
                        
                self.DownloadsResults.append({
                                              "main_id_number": int(MainIDNumber),
                                              "page": int(Page),
                                              "position": int(x),
                                              "title": title,
                                              "filename": release,
                                              "language_name": LanguageName,
                                              "ID": download_id,
                                              "format": "srt",
                                              "sync": False,
                                              "rating":rating,
                                              "language_flag": LanguageFlag,
                                              "language_preference": int(LanguagePreference) })

            self.Log("Message: Retrieved [%s] results for page [%s], Movie[%s], Id[%s]." % (x, Page, MainID["title"], MainID["id"]))
                
    def Search(self, **kargs):   
        # Init all variables
        startTime = time.time()
        filteredResults, self.DownloadsResults, self.Languages = [], [], []
        Movie, TVShow, Year, Season, Episode = "", "", 0, 0, 0
        for key, value in kargs.iteritems():
            value = self._UNICODE(value)
            if key == "movie":             Movie = self.CleanLTVTitle(value)
            if key == "tvshow":            TVShow = self.CleanLTVTitle(value)
            if key == "year" and value:    Year = int(value)
            if key == "season" and value:  Season = int(value)
            if key == "episode" and value: Episode = int(value)
            if key == "lang1" and value:   self.Languages.append((0, value))
            if key == "lang2" and value:   self.Languages.append((1, value))
            if key == "lang3" and value:   self.Languages.append((2, value))
        self.Languages.sort()

        if Movie: SearchTitle = Movie
        else: SearchTitle = TVShow
        discardedResults, filteredResults = "", ""
        discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchTitle)
        if not filteredResults:
            # Searching for movie titles/tvshow ids using the lengthiest words
            if len(SearchTitle.split(" ")):
                for SearchString in sorted(SearchTitle.split(" "), key=len, reverse=True):
                    if SearchString in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ] or len(SearchString) < 2:
                        continue
                    discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchString)
                    if filteredResults: 
                        break
            else:
                discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchTitle)
        if not filteredResults and len(discardedResults):
            filteredResults = []
            for Result in discardedResults[0:4]:
                if Result["ratio"] == discardedResults[0]["ratio"]:
                    filteredResults.append(Result)
            self.Log("Message: Filtration failed, using discarded results.")
        elif not filteredResults:
            return ""
        # Initiate the "buscalegenda" search to search for all types and languages
        MainIDNumber = 1
        for MainID in filteredResults[0:4]:
            # Find how much pages are to download
            self.Log("Message: Retrieving results to id[%s]" % (MainID["id"]))
            Response = self._urlopen("http://minister.legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % ("1", MainID["id"]))
            regResponse = re.findall(regex_2, Response)
            TotalPages = len(regResponse) +1
            # Form and execute threaded downloads
            for Page in range(TotalPages):
                Page += 1
                current = LTVThread(self, MainID , MainIDNumber, Page)
                self.RegThreads.append(current)
                current.start()
            MainIDNumber += 1
        # Wait for all threads to finish
        for t in self.RegThreads:
            t.join()
        # Sorting and filtering the results by episode, including season packs
        self.DownloadsResults = sorted(self.DownloadsResults, key=itemgetter('main_id_number', 'page', 'position'))
        IncludedResults = []
        ExcludedResult = []
        if TVShow:
            Episodes, Packs = [], [] 
            for DownloadsResult in self.DownloadsResults:
                if re.search("\(PACK", DownloadsResult["filename"]):
                    DownloadsResult["filename"] = re.sub("\(PACK[^\)]*?\)", "", DownloadsResult["filename"])
                if re.search("(^|\s|[.])[Ss]%.2d(\.|\s|$)" % int(Season), DownloadsResult["filename"]):
                    DownloadsResult["filename"] = "(PACK) " + DownloadsResult["filename"]
                    Packs.append(DownloadsResult) 
                elif re.search("[Ss]%.2d[Ee]%.2d" % (int(Season), int(Episode)), DownloadsResult["filename"]):
                    Episodes.append(DownloadsResult)
                elif re.search("x%.2d" % (int(Episode)), DownloadsResult["filename"]):
                    Episodes.append(DownloadsResult)
                else:
                    ExcludedResult.append(DownloadsResult)
            IncludedResults.extend(Packs)
            IncludedResults.extend(Episodes)
        elif Movie:
            IncludedResults.extend(self.DownloadsResults)
        IncludedResults = sorted(IncludedResults, key=itemgetter('language_preference'))

        # # Log final results
        self.Log(" ")
        self.Log("Included results:")
        self._log_List_dict(IncludedResults, "filename language_name language_preference ID")
        self.Log("Excluded results:") 
        self._log_List_dict(ExcludedResult, "filename language_name language_preference ID")
        self.Log("Message: The service took %s seconds to complete." % (time.time() - startTime))
        # Return results
        return IncludedResults

def _XBMC_Notification(StringID):
    xbmc.executebuiltin("Notification(Legendas.TV,%s,10000])"%( _( StringID ).encode('utf-8') ))
 
def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):  # standard input
    try:
        global LTV
        LTV = LegendasTV()
        subtitles = ""
        if len(title): title = XBMC_OriginalTitle(title)
        elif len(tvshow): tvshow = XBMC_OriginalTitle(tvshow)
        cookie = LTV.login(__addon__.getSetting( "LTVuser" ), __addon__.getSetting( "LTVpass" ))
        if cookie:
            subtitles = LTV.Search(movie=title, tvshow=tvshow, year=year, season=season, 
                                   episode=episode, lang1=lang1, lang2=lang2, lang3=lang3)
        else:
            _XBMC_Notification(756)
        return subtitles, cookie, ""
    except:
        import traceback
        log(__name__, "\n%s" % traceback.format_exc())
        return "", "", _( 755 ).encode('utf-8')

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    #Create some variables
    subtitle = ""
    extract_path = os.path.join(tmp_sub_dir, "extracted")
    id = subtitles_list[pos][ "ID" ]
    language = subtitles_list[pos][ "language_name" ]
    legendas_tmp = []
    # Download the subtitle using its ID.
    Response = urllib2.urlopen("http://minister.legendas.tv%s" % id).read()
    downloadID = re.findall(regex_3, Response)[0] if re.search(regex_3, Response) else 0
    if not downloadID: return ""
    response = urllib2.urlopen(urllib2.Request("http://minister.legendas.tv%s" % downloadID))
    ltv_sub = response.read()
    # Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
    # Write the subtitle in binary mode.
    fname = os.path.join(tmp_sub_dir,"subtitle")
    if response.info().get("Content-Disposition").__contains__('rar'):
        fname += '.rar'
    else:
        fname += '.zip'
    f = open(fname,'wb')
    f.write(ltv_sub)
    f.close()

    # brunoga fixed solution for non unicode caracters
    # Ps. Windows allready parses Unicode filenames.
    fs_encoding = sys.getfilesystemencoding()
    extract_path = extract_path.encode(fs_encoding)

    # Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
    # then removes all files from the temp dir that aren't subtitles.
    def extract_and_copy(extraction=0):
        i = 0
        for root, dirs, files in os.walk(extract_path, topdown=False):
            for file in files:
                dirfile = os.path.join(root, file)
                
                # Sanitize filenames - converting them to ASCII - and remove them from folders
                f = xbmcvfs.File(dirfile)
                temp = f.read()
                f.close()
                xbmcvfs.delete(dirfile)
                dirfile_with_path_name = os.path.relpath(dirfile, extract_path)
                dirfile_with_path_name = re.sub(r"[/\\]{1,2}","-", dirfile_with_path_name)
                dirfile_with_path_name = LTV._UNICODE(dirfile_with_path_name).encode('ascii', 'ignore')
                new_dirfile = os.path.join(extract_path, dirfile_with_path_name)
                os.write(os.open(new_dirfile, os.O_RDWR | os.O_CREAT), temp)
                
                # Get the file extention
                ext = os.path.splitext(new_dirfile)[1][1:].lower()
                if ext in sub_ext and xbmcvfs.exists(new_dirfile):
                    if not new_dirfile in legendas_tmp:
                        #Append the matching file
                        legendas_tmp.append(new_dirfile)
                elif ext in "rar zip" and not extraction:
                    # Extract compressed files, extracted priorly
                    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (new_dirfile, extract_path))
                    xbmc.sleep(1000)
                    extract_and_copy(1)
                elif ext not in "idx": 
                    xbmcvfs.delete(new_dirfile)
            for dir in dirs:
                dirfolder = os.path.join(root, dir)
                xbmcvfs.rmdir(dirfolder)

    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (fname, extract_path))
    xbmc.sleep(1000)
    extract_and_copy()
    
    temp = []
    for sub in legendas_tmp:
        video_file = LTV.chomp(os.path.basename(sys.modules[ "__main__" ].ui.file_original_path))
        sub_striped =  LTV.chomp(os.path.basename(sub))
        Ratio = LTV.CalculateRatio(sub_striped, video_file)
        temp.append([Ratio, sub])
    legendas_tmp = sorted(temp, reverse=True)
    
    if len(legendas_tmp) > 1:
        dialog = xbmcgui.Dialog()
        sel = dialog.select("%s\n%s" % (_( 30152 ).encode("utf-8"), subtitles_list[pos][ "filename" ]) ,
                             [os.path.basename(y) for x, y in legendas_tmp])
        if sel >= 0:
            subtitle = legendas_tmp[sel][1]
    elif len(legendas_tmp) == 1:
        subtitle = legendas_tmp[0][1]
    return False, language, subtitle

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service Legendas-Zone.org version 0.2.1
# Code based on Undertext service and the download function encode fix from legendastv service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service Legendas-Zone.org v0.2.1:
# Service working again, developers change the page way too much!
# Fixed download bug when XBMC is set to Portuguese language
# Removed IMDB search since they are always changing code!
# Some code cleanup
#
# NEW on Service Legendas-Zone.org v0.2.0:
# Fixed bug on openelec based XBMC prevent the script to work
# Removed some XBMC messages from the script who were annoying!
# Some code cleanup
#
# NEW on Service Legendas-Zone.org v0.1.9:
# Added all site languages (English, Portuguese, Portuguese Brazilian and Spanish)
# Changed the way it would handle several patterns for much better finding (site not well formed...)
# Messages now in xbmc choosen language.
# Added new logo.
# Fixed download.
# Code re-arrange...
#
# NEW on Service Legendas-Zone.org v0.1.8:
# Added uuid for better file handling, no more hangups.
#
# NEW on Service Legendas-Zone.org v0.1.7:
# Changed 2 patterns that were crashing the plugin, now it works correctly.
# Better builtin notifications for better information.
#
# NEW on Service Legendas-Zone.org v0.1.6:
# Better search results with 3 types of searching. Single title, multi titles and IMDB search.
# Added builtin notifications for better information.
#
# Initial Release of Service Legendas-Zone.org - v0.1.5:
# TODO: re-arrange code :)
#
# Legendas-Zone.org subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import languageTranslate, log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://www.legendas-zone.org/"
debug_pretext = "Legendas-Zone"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
#Grabbing login and pass from xbmc settings
username = __addon__.getSetting( "LZuser" )
password = __addon__.getSetting( "LZpass" )

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
subtitle_pattern = "<b><a\shref=\"legendas.php\?modo=detalhes&amp;(.+?)\".+?[\r\n\t]+?.+?[\r\n\t]+?.+?onmouseover=\"Tip\(\'<table><tr><td><b>(.+?)</b></td></tr></table>.+?<b>Hits:</b>\s(.+?)\s<br>.+?<b>CDs:</b>\s(.+?)<br>.+?Uploader:</b>\s(.+?)</td>"
# group(1) = ID, group(2) = Name, group(3) = Hits, group(4) = Files, group(5) = Uploader
multiple_results_pattern = "<td\salign=\"left\".+?<b><a\shref=\"legendas.php\?imdb=(.+?)\"\stitle=\".+?\">"
# group(1) = IMDB
imdb_pattern = "<td class=\"result_text\"> <a\shref=\"\/title\/tt(.+?)\/\?"
# group(1) = IMDB
#====================================================================================================================
# Functions
#====================================================================================================================
def _from_utf8(text):
    if isinstance(text, str):
        return text.decode('utf-8')
    else:
        return text

def msgnote(site, text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	text = _from_utf8(text)
	site = _from_utf8(site)
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "LZuser" )
	password = __addon__.getSetting( "LZpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'username' : username, 'password' : password})
	opener.open(main_url+'fazendologin.php', login_data)
	
	

	page = 0
	if languageshort == "pb":
			languageshort = "br"
	#url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
	if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
		url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
	else:
		url = main_url + "index.php"

	content = opener.open(url)
	#log( __name__ ,"%s Content: '%s'" % (debug_pretext, content))
	content = content.read().decode('latin1')
	#log( __name__ ,"%s Contentread: '%s'" % (debug_pretext, content.decode('latin1')))
	if re.search(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) == None:
		log( __name__ ,"%s LangSingleSUBS: '%s'" % (debug_pretext, languageshort))
		log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "Single Title"))
		while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 3:
			for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
				hits = matches.group(3)
				downloads = int(matches.group(3)) / 5
				if (downloads > 10):
					downloads=10
				id = matches.group(1)
				filename = string.strip(matches.group(2))
				desc = string.strip(matches.group(2))
				no_files = matches.group(4)
				uploader = matches.group(5)
				#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
				filename_check = string.split(filename,' ')
				#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
				#Remove new lines on the commentaries
				filename = re.sub('\n',' ',filename)
				desc = re.sub('\n',' ',desc)
				desc = re.sub('&quot;','"',desc)
				#Remove HTML tags on the commentaries
				filename = re.sub(r'<[^<]+?>','', filename)
				desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
				#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
				global filesearch
				filesearch = os.path.abspath(file_original_path)
				#For DEBUG only uncomment next line
				#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
				filesearch = os.path.split(filesearch)
				#For DEBUG only uncomment next line
				#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
				dirsearch = filesearch[0].split(os.sep)
				#For DEBUG only uncomment next line
				#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
				dirsearch_check = string.split(dirsearch[-1], '.')
				#For DEBUG only uncomment next line
				#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
				if (searchstring_notclean != ""):
					sync = False
					if re.search(searchstring_notclean, desc):
						sync = True
				else:
					if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
						sync = False
						if len(dirsearch) > 1 and dirsearch[1] != '':
							if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
								sync = True
						else:
							if re.search(filesearch[1][:len(filesearch[1])-4], desc):
								sync = True
					else:
						sync = False
						if len(dirsearch) > 1 and dirsearch[1] != '':
							if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
								sync = True
						else:
							if re.search(filesearch[1][:len(filesearch[1])-4], desc):
								sync = True
				#filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
				if languageshort == "br":
					languageshort = "pb"
				subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits': hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
			page = page + 1
			if languageshort == "br":
				languageshort = "pb"
#			url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
			if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
				url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
			else:
				url = main_url + "index.php"
			content = opener.open(url)
			content = content.read().decode('latin1')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s Getting '%s' list part xxx..." % (debug_pretext, content))
	else:
		page = 0
		if languageshort == "pb":
			languageshort = "br"
		if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
			url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
		else:
			url = main_url + "index.php"
		#url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read().decode('latin1')
		maxsubs = re.findall(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#maxsubs = len(maxsubs)
		if maxsubs != "":
			log( __name__ ,"%s LangMULTISUBS: '%s'" % (debug_pretext, languageshort))
			#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "Less Then 10 Titles"))
			while re.search(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 1:
				for resmatches in re.finditer(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
					imdb = resmatches.group(1)
					page1 = 0
					if languageshort == "pb":
						languageshort = "br"
					if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
						content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
					else:
						content1 = main_url + "index.php"
					#content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
					content1 = content1.read()
					content1 = content1.decode('latin1')
					while re.search(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page1 == 0:
						for matches in re.finditer(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
							#log( __name__ ,"%s PAGE? '%s'" % (debug_pretext, page1))
							hits = matches.group(3)
							downloads = int(matches.group(3)) / 5
							if (downloads > 10):
								downloads=10
							id = matches.group(1)
							filename = string.strip(matches.group(2))
							desc = string.strip(matches.group(2))
							#desc = filename + " - uploader: " + desc
							no_files = matches.group(4)
							uploader = matches.group(5)
							#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
							filename_check = string.split(filename,' ')
							#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
							#Remove new lines on the commentaries
							filename = re.sub('\n',' ',filename)
							desc = re.sub('\n',' ',desc)
							desc = re.sub('&quot;','"',desc)
							#Remove HTML tags on the commentaries
							filename = re.sub(r'<[^<]+?>','', filename)
							desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
							#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
							#global filesearch
							filesearch = os.path.abspath(file_original_path)
							#For DEBUG only uncomment next line
							#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
							filesearch = os.path.split(filesearch)
							#For DEBUG only uncomment next line
							#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
							dirsearch = filesearch[0].split(os.sep)
							#For DEBUG only uncomment next line
							#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
							dirsearch_check = string.split(dirsearch[-1], '.')
							#For DEBUG only uncomment next line
							#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
							if (searchstring_notclean != ""):
								sync = False
								if re.search(searchstring_notclean, desc):
									sync = True
							else:
								if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
									sync = False
									if len(dirsearch) > 1 and dirsearch[1] != '':
										if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
											sync = True
									else:
										if re.search(filesearch[1][:len(filesearch[1])-4], desc):
											sync = True
								else:
									sync = False
									if len(dirsearch) > 1 and dirsearch[1] != '':
										if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
											sync = True
									else:
										if re.search(filesearch[1][:len(filesearch[1])-4], desc):
											sync = True
							filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
							if languageshort == "br":
								languageshort = "pb"
							subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
						page1 = page1 + 1
						if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
							content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
						else:
							content1 = main_url + "index.php"
						#content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
						content1 = content1.read().decode('latin1')
				page = page + 1
				if languageshort == "pb":
					languageshort = "br"
				#url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
				if languageshort == "pt" or languageshort == "br" or languageshort == "en" or languageshort == "es":
					url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
				else:
					url = main_url + "index.php"
				content = opener.open(url)
				content = content.read().decode('latin1')
################### IMDB DISABLED FOR NOW #######################################
#		else:
#			url = "http://uk.imdb.com/find?s=all&q=" + urllib.quote_plus(searchstring)
#			content = opener.open(url)
#			content = content.read().decode('latin1')
#			imdb = re.findall(imdb_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#			page1 = 0
#			log( __name__ ,"%s LangIMDB: '%s'" % (debug_pretext, languageshort))
#			if languageshort == "pb":
#				languageshort = "br"
#			content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb[0] + "&page=" + str(page1))
#			content1 = content1.read().decode('latin1')
#			#msgnote(pretext, "Too many hits. Grabbing IMDB title!", 6000)
#			while re.search(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
#				log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "IMDB Title"))
#				for matches in re.finditer(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
#					hits = matches.group(3)
#					downloads = int(matches.group(3)) / 5
#					if (downloads > 10):
#						downloads=10
#					id = matches.group(1)
#					filename = string.strip(matches.group(2))
#					desc = string.strip(matches.group(2))
#					#desc = filename + " - uploader: " + desc
#					no_files = matches.group(4)
#					uploader = matches.group(5)
#					#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
#					filename_check = string.split(filename,' ')
#					#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
#					#Remove new lines on the commentaries
#					filename = re.sub('\n',' ',filename)
#					desc = re.sub('\n',' ',desc)
#					desc = re.sub('&quot;','"',desc)
#					#Remove HTML tags on the commentaries
#					filename = re.sub(r'<[^<]+?>','', filename)
#					desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
#					#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
#					#global filesearch
#					filesearch = os.path.abspath(file_original_path)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
#					filesearch = os.path.split(filesearch)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
#					dirsearch = filesearch[0].split(os.sep)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
#					dirsearch_check = string.split(dirsearch[-1], '.')
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
#					if (searchstring_notclean != ""):
#						sync = False
#						if re.search(searchstring_notclean, desc):
#							sync = True
#					else:
#						if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
#							sync = False
#							if len(dirsearch) > 1 and dirsearch[1] != '':
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
#									sync = True
#							else:
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc):
#									sync = True
#						else:
#							sync = False
#							if len(dirsearch) > 1 and dirsearch[1] != '':
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
#									sync = True
#							else:
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc):
#									sync = True
#					filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
#					if languageshort == "br":
#						languageshort = "pb"
#					subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
#				page1 = page1 + 1
#				if languageshort == "pb":
#					languageshort = "br"
#				content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb[0] + "&page=" + str(page1))
#				content1 = content1.read().decode('latin1')
#				#For DEBUG only uncomment next line


##### ANNOYING #####
	#if subtitles_list == []:
		#msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
		#msgnote(debug_pretext,"Try manual or parent dir!", 2000)
	#elif subtitles_list != []:
	#	lst = str(subtitles_list)
	#	if languagelong in lst:
	#		msgnote(debug_pretext,"Found sub(s) in "  + languagelong + ".", 2000)
	#	else:
			#msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
			#msgnote(debug_pretext,"Try manual or parent dir!", 2000)

	#Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp


def get_download(url, download, id):
    req_headers = {
		'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
		'Referer': main_url,
		'Keep-Alive': '300',
		'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)
    download_data = urllib.urlencode({'sid' : id, 'submit' : '+', 'action' : 'Download'})
    request1 = urllib2.Request(download, download_data, req_headers)
    f = opener.open(request1)
    return f

def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	hasLang = languageTranslate(lang1,0,2) + " " + languageTranslate(lang2,0,2) + " " + languageTranslate(lang3,0,2)

	if re.search('pt', hasLang) or re.search('en', hasLang) or re.search('es', hasLang) or re.search('pb', hasLang):
		msgnote(debug_pretext,__language__(30153), 6000)
		getallsubs(searchstring, languageTranslate(lang1,0,2), lang1, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang2,0,2), lang2, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang3,0,2), lang3, file_original_path, subtitles_list, searchstring_notclean)
	else:
		msg = "Won't work, LegendasDivx.com is only for PT, PTBR, ES or EN subtitles."
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				log( __name__ ,"%s base: %s" % (debug_pretext, base)) #EGO
				log( __name__ ,"%s filename: %s" % (debug_pretext, filename)) #EGO
				base = base.decode('latin1')
				filename = filename.decode('latin1')
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext, "Downloading... Please Wait!", 6000)
	id = subtitles_list[pos][ "id" ]
	id = string.split(id,"=")
	id = id[-1]
	sync = subtitles_list[pos][ "sync" ]
	language = subtitles_list[pos][ "language_name" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))

	#This is where you are logged in and download
	content = get_download(main_url+'fazendologin.php', main_url+'downloadsub.php', id)

	downloaded_content = content.read()

	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	
	fname = os.path.join(tmp_sub_dir,str(id))
	if content.info().get('Content-Disposition').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(downloaded_content)
	f.close()
	
	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
	msgnote(debug_pretext,__language__(30155), 3000)
	xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
	time.sleep(2)
	legendas_tmp = []
	# brunoga fixed solution for non unicode caracters
	fs_encoding = sys.getfilesystemencoding()
	for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
		for file in files:
			dirfile = os.path.join(root, file)
			ext = os.path.splitext(dirfile)[1][1:].lower()
			if ext in sub_ext:
				legendas_tmp.append(dirfile)
			elif os.path.isfile(dirfile):
				os.remove(dirfile)
	
	msgnote(debug_pretext,__language__(30156), 3000)
	searchrars = recursive_glob(extract_path, packext)
	searchrarcount = len(searchrars)
	if searchrarcount > 1:
		for filerar in searchrars:
			if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
				try:
					xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
				except:
					return False
	time.sleep(1)
	searchsubs = recursive_glob(extract_path, subext)
	searchsubscount = len(searchsubs)
	for filesub in searchsubs:
		nopath = string.split(filesub, extract_path)[-1]
		justfile = nopath.split(os.sep)[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
		#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
		releasefilename = filesearch[1][:len(filesearch[1])-4]
		releasedirname = filesearch[0].split(os.sep)
		if 'rar' in israr:
			releasedirname = releasedirname[-2]
		else:
			releasedirname = releasedirname[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
		#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
		subsfilename = justfile[:len(justfile)-4]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
		#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
		#Check for multi CD Releases
		multicds_pattern = "\+?(cd\d)\+?"
		multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#Start choosing the right subtitle(s)
		if searchsubscount == 1 and sync == True:
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
			break
		elif string.lower(subsfilename) == string.lower(releasefilename):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
			break
		elif string.lower(subsfilename) == string.lower(releasedirname):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
			break
		elif (multicdsubs != None) and (multicdsrls != None):
			multicdsubs = string.lower(multicdsubs.group(1))
			multicdsrls = string.lower(multicdsrls.group(1))
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
			#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
			if multicdsrls == multicdsubs:
				subs_file = filesub
				subtitle = subs_file
				break

	else:
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
		if len(legendas_tmp) > 1:
			dialog = xbmcgui.Dialog()
			subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
			if subtitle == extract_path+"/": subtitle = ""
		elif legendas_tmp:
			subtitle = legendas_tmp[0]
	
	msgnote(debug_pretext,__language__(30157), 3000)
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import sys
import os
from utilities import languageTranslate
import xbmc
import xbmcvfs
import urllib

try:
  #Python 2.6 +
  from hashlib import md5
except ImportError:
  #Python 2.5 and earlier
  from md5 import new as md5

# Version 0.1 
# 
# Coding by gregd
# http://greg.pro
# License: GPL v2


_ = sys.modules[ "__main__" ].__language__

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):

    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = "000000000000"
        def run(self):
            self.result = func(*args, **kwargs)
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return it.result
    else:
        return it.result
        
def set_filehash(path,rar):
    d = md5();    
    qpath=urllib.quote(path)
    if rar:
        path="""rar://"""+qpath
    d.update(xbmcvfs.File(path,"rb").read(10485760))
    return d

def f(z):
        idx = [ 0xe, 0x3,  0x6, 0x8, 0x2 ]
        mul = [   2,   2,    5,   4,   3 ]
        add = [   0, 0xd, 0x10, 0xb, 0x5 ]

        b = []
        for i in xrange(len(idx)):
                a = add[i]
                m = mul[i]
                i = idx[i]

                t = a + int(z[i], 16)
                v = int(z[t:t+2], 16)
                b.append( ("%x" % (v*m))[-1] )

        return ''.join(b)

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
       
    ok = False
    msg = ""    
    subtitles_list = []    
    languages = {}
    for lang in (lang1,lang2,lang3):
        languages[lang]=languageTranslate(lang,0,2)
        
    d = timeout(set_filehash, args=(file_original_path, rar), timeout_duration=15)

    for lang,language in languages.items():
        str = "http://napiprojekt.pl/unit_napisy/dl.php?l="+language.upper()+"&f="+d.hexdigest()+"&t="+f(d.hexdigest())+"&v=dreambox&kolejka=false&nick=&pass=&napios="+os.name
        subs=urllib.urlopen(str).read()
        if subs[0:4]!='NPc0':		            
            flag_image = "flags/%s.gif" % (language,)            
            s={'filename':title,'link':subs,"language_name":lang,"language_flag":flag_image,"language_id":language,"ID":0,"sync":True, "format":"srt", "rating": "" }
            subtitles_list.append(s)        
            
    return subtitles_list, "", "" #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    local_tmp_file = os.path.join(tmp_sub_dir, "napiprojekt_subs.srt")
    local_file_handle = open(local_tmp_file, "w" + "b")
    local_file_handle.write(subtitles_list[pos][ "link" ])
    local_file_handle.close()  
    language = subtitles_list[pos][ "language_name" ]
    return False, language, local_tmp_file #standard output    

    

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

# Frankenstein Monster v 2.0
# Feel free to improve, change anything.
# Credits to amet, Guilherme Jardim, and many more.
# Big thanks to gaco for adding logging to site.
# mrto

import urllib2, re, string, xbmc, sys, os
from utilities import log, languageTranslate, hashFile
from BeautifulSoup import BeautifulSoup
from cookielib import CookieJar
from urllib import urlencode

_ = sys.modules[ "__main__" ].__language__
__addon__ = sys.modules[ "__main__" ].__addon__

if __addon__.getSetting( "Napisy24_type" ) == "0":
    subtitle_type = "sr"
elif __addon__.getSetting( "Napisy24_type" ) == "1":
    subtitle_type = "tmp"
elif __addon__.getSetting( "Napisy24_type" ) == "2":
    subtitle_type = "mdvd"
elif __addon__.getSetting( "Napisy24_type" ) == "3":
    subtitle_type = "mpl2"

main_url = "http://napisy24.pl/search.php?str="
base_download_url = "http://napisy24.pl/download/"
down_url = "%s%s/" % (base_download_url, subtitle_type)

def getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3):
    soup = BeautifulSoup(content)
    subs = soup("tr")
    sub_str = str(subs[1:])
    first_row = True
    languages_map = {'Polski': 'pl', 'Angielski': 'en', 'Niemiecki': 'de'}
    for row in subs[1:]:
        sub_number_re = 'a href=\"/download/(\d+)/\"><strong>'
        title_re = '<a href="/download/\d+?/"><strong>(.+?)</strong></a>'
        release_re = '<td>(.+?)<br />|<td.+?>(.+?)<br />'
        rating_re = 'rednia ocena: (\d\,\d\d)<br />'
        lang_re = 'zyk:.+?alt="(.+?)"'
        disc_amount_re = '<td.+?style="text-align: center;">[\r\n\t ]+?(\d)[\r\n\t ]+?</td>'
        video_file_size_re = 'Rozmiar pliku: <strong>(\d+?)</strong>'
        video_file_size_re_multi = 'Rozmiar pliku:<br />- CD1: <strong>(\d+?)</strong>'
        archive_re = '<a href="/download/archiwum/(\d+?)/">'
        row_str = str(row)
        archive = re.findall(archive_re, row_str)
        if len(archive) == 0:
            if first_row == True:
                sub_number = re.findall(sub_number_re, row_str)
                subtitle = re.findall(title_re, row_str)
                release = re.findall(release_re, row_str)
                disc_amount = re.findall(disc_amount_re, row_str)
                first_row = False
            else:
                file_size, SubHash = hashFile(file_original_path, False)
                if disc_amount[0] > '1':
                    video_file_size = re.findall(video_file_size_re_multi, row_str)
                else:
                    video_file_size = re.findall(video_file_size_re, row_str)
                
                if len(video_file_size) == 0:
                    video_file_size.append('0')
                    sync_value = False
                else:
                    video_file_size = unicode(video_file_size[0], "UTF-8")
                    video_file_size = video_file_size.replace(u"\u00A0", "")
                    if file_size == video_file_size:
                        sync_value = True
                    else:
                        sync_value = False

                rating = re.findall(rating_re, row_str)
                language = re.findall(lang_re, row_str)

                if language[0] in languages_map:
                    language = [languages_map[language[0]]]
                else:
                    language = []

                if len(language) > 0:
                    first_row = True
                    link = "%s%s/" % (down_url, sub_number[0])
                    log( __name__ ,"Subtitles found: %s %s (link=%s)" % (subtitle[0], release, link))

                    flag_pic = "flags/%s.gif" % (language[0])
                    lang = languageTranslate(language[0],2,0)

                    if lang == lang1 or lang == lang2 or lang == lang3:
                        
                        for rel in re.findall("\'(.*?)\'", str(release)):

                            rel = rel.replace(",",":").replace(" ","")

                            if len(rel) > 1:
                                rel_semicolon = "%s;" % (rel)
                                for rel_sync in re.findall('(.+?);', rel_semicolon):
                                    if rel_sync.upper() in file_original_path.upper():
                                        sync_value = True

                        filename_release = "%s - %s" % (subtitle[0], rel_semicolon)

                        rating_dot = rating[0].replace(",",".")
                        if rating_dot == '0.00':
                            sub_rating = '0'
                        else:
                            sub_rating = int(round(float(rating_dot) * 1.666,0))

                        if stack == False:
                            if disc_amount[0] > '1':
                                log( __name__ ,"Nonstacked video file - stacked subs")
                            else:
                                subtitles_list.append({'filename': filename_release, 'sync': sync_value, 'link': link, 'language_flag': flag_pic, 'language_name': lang,'rating': '%s' % (sub_rating)})
                        else:
                            if disc_amount[0] > '1':
                                subtitles_list.append({'filename': filename_release, 'sync': sync_value, 'link': link, 'language_flag': flag_pic, 'language_name': lang,'rating': '%s' % (sub_rating)})
                            else:
                                log( __name__ ,"Stacked video file - nonstacked subs")
                    else:
                        continue
                else:
                    continue

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
      for year in re.finditer(' \(\d\d\d\d\)', tvshow):
          year = year.group()
          if len(year) > 0:
              tvshow = tvshow.replace(year, "")
          else:
              continue
      tvshow_plus = tvshow.replace(" ","+")
      if len(season) < 2:
        season_full = '0%s' % (season)
      else:
        season_full = season
      if len(episode) < 2:
        episode_full = '0%s' % (episode)
      else:
        episode_full = episode
      url = '%s%s+%sx%s' % (main_url, tvshow_plus, season_full, episode_full)
    else:
      original_title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
      if len(original_title) == 0:
        log( __name__ ,"Original title not set")
        movie_title_plus = title.replace(" ","+")
        url = '%s%s' % (main_url, movie_title_plus)
      else:
        log( __name__ ,"Original title: [%s]" % (original_title))
        movie_title_plus = original_title.replace(" ","+")
        url = '%s%s' % (main_url, movie_title_plus)
    log( __name__ , "Fetching from [ %s ]" % (url))
    response = urllib2.urlopen(url)
    content = response.read()
    re_pages_string = 'postAction%3DszukajZaawansowane">(\d)</a>'
    page_nr = re.findall(re_pages_string, content)
    getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3)
    for i in page_nr:
        main_url_pages = 'http://napisy24.pl/szukaj/&stronaArch=1&strona='
        rest_url = '%26postAction%3DszukajZaawansowane'
        url_2 = '%s%s&szukajNapis=%s%s' % (main_url_pages, i, title, rest_url)
        response = urllib2.urlopen(url_2)
        content = response.read()    
        getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3)
    return subtitles_list, "", "" #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    cj = CookieJar()
    headers = {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Charset': 'UTF-8,*;q=0.5',
          'Accept-Encoding': 'gzip,deflate,sdch',
          'Accept-Language': 'pl,pl-PL;q=0.8,en-US;q=0.6,en;q=0.4',
          'Connection': 'keep-alive',
          'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1',
          'Referer': 'http://napisy24.pl/'
    }
    values = { 'form_logowanieMail' : __addon__.getSetting( "n24user" ), 'form_logowanieHaslo' :  __addon__.getSetting( "n24pass" ), 'postAction' : 'sendLogowanie' }
    data = urlencode(values)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    request = urllib2.Request("http://napisy24.pl/logowanie/", data, headers)
    response = opener.open(request)
    request = urllib2.Request(subtitles_list[pos][ "link" ], "", headers)
    f = opener.open(request)
    local_tmp_file = os.path.join(tmp_sub_dir, "zipsubs.zip")
    log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
    
    local_file = open(zip_subs, "w" + "b")
    local_file.write(f.read())
    local_file.close()
    opener.open("http://napisy24.pl/index.php?sendAction=Wyloguj")
    
    language = subtitles_list[pos][ "language_name" ]
    return True, language, "" #standard output

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service OmniSubs.net version 0.1.5
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service OmniSubs.net v0.1.6:
# Added uuid for better file handling, no more hangups.
#
# Initial Release of Service OmniSubs.net - v0.1.5:
# TODO: re-arrange code :)
#
# OmniSubs.NET subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

main_url = "http://www.omnisubs.net/"
debug_pretext = "OmniSubs"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
desc_pattern = "<td><b>Descri.+?</b><img\ssrc=\".+?/>(.+?)[\r\n\t]<hr\s/><b>Posted\sby:"
subtitle_pattern = "<tr><td><a\shref=\"(.+?)\">(.+?)</a></td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td></tr>"
# group(1) = Download link, group(2) = Name, group(3) = Downloads, group(4) = Data, group(5) = Comments, group(6) = User
#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "Omniuser" )
	password = __addon__.getSetting( "Omnipass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	opener.open(main_url+'index.php', login_data)

	page = 0
	if languageshort == "pt":
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	content = content.read()
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s Getting '%s' list ..." % (debug_pretext, content))
	#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(3)
			id = matches.group(1)
			no_files = matches.group(3)
			downloads = int(matches.group(3)) / 10
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(2))
			#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
			filename_check = string.split(filename,' ')
			#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
			if filename_check[0] == '[GT]':
				continue
			content_desc = opener.open(id)
			content_desc = content_desc.read()
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s Getting '%s' desc" % (debug_pretext, content_desc))
			for descmatch in re.finditer(desc_pattern, content_desc, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
				desc = string.strip(descmatch.group(1))
				log( __name__ ,"%s Desc: '%s'" % (debug_pretext, desc))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			desc = re.sub('&quot;','"',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			filename = filename + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 10
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s Getting '%s' list part xxx..." % (debug_pretext, content))

#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp





def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	portuguese = 0
	if string.lower(lang1) == "portuguese": portuguese = 1
	elif string.lower(lang2) == "portuguese": portuguese = 2
	elif string.lower(lang3) == "portuguese": portuguese = 3

	getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if portuguese == 0:
		msg = "Won't work, LegendasDivx is only for Portuguese subtitles!"
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	id = subtitles_list[pos][ "id" ]
	id = string.split(id,"=")
	id = id[-1]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "Omniuser" )
	password = __addon__.getSetting( "Omnipass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	#This is where you are logged in
	resp = opener.open('http://www.omnisubs.net/index.php', login_data)
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s resposta '%s' subs ..." % (debug_pretext, resp))
	#Now you download the subtitles
	language = subtitles_list[pos][ "language_name" ]
	if string.lower(language) == "portuguese":
		content = opener.open('http://www.omnisubs.net/index.php?action=downloads;sa=downfile;id=' + id)

	if content is not None:
		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
		if header == 'rar':
			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".rar")
			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
			packed = True
		elif header == 'zip':
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".zip")
			packed = True
		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".srt") # assume unpacked sub file is an '.srt'
			subs_file = local_tmp_file
			packed = False
		log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
		try:
			log( __name__ ,"%s file: write in %s" % (debug_pretext, local_tmp_file)) #EGO
			local_file_handle = open(local_tmp_file, "wb")
			shutil.copyfileobj(content.fp, local_file_handle)
			local_file_handle.close()
		except:
			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
		if packed:
			files = os.listdir(tmp_sub_dir)
			init_filecount = len(files)
			log( __name__ ,"%s file: number init_filecount %s" % (debug_pretext, init_filecount)) #EGO
			filecount = init_filecount
			max_mtime = 0
			# determine the newest file from tmp_sub_dir
			for file in files:
				if (string.split(file,'.')[-1] in ['srt','sub','txt']):
					mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
					if mtime > max_mtime:
						max_mtime =  mtime
			init_max_mtime = max_mtime
			time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
			xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
			waittime  = 0
			while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
				time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
				files = os.listdir(tmp_sub_dir)
				log( __name__ ,"%s DIRLIST '%s'" % (debug_pretext, files))
				filecount = len(files)
				# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
				for file in files:
					if (string.split(file,'.')[-1] in ['srt','sub','txt']):
						mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
						if (mtime > max_mtime):
							max_mtime =  mtime
				waittime  = waittime + 1
			if waittime == 20:
				log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
			else:
				log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
				searchrars = recursive_glob(tmp_sub_dir, packext)
				searchrarcount = len(searchrars)
				if searchrarcount > 1:
					for filerar in searchrars:
						if filerar != os.path.join(tmp_sub_dir,'ldivx.rar') and filerar != os.path.join(tmp_sub_dir,'ldivx.zip'):
							xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + tmp_sub_dir +")")
				time.sleep(1)
				searchsubs = recursive_glob(tmp_sub_dir, subext)
				searchsubscount = len(searchsubs)
				for filesub in searchsubs:
					nopath = string.split(filesub, tmp_sub_dir)[-1]
					justfile = nopath.split(os.sep)[-1]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
					#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
					releasefilename = filesearch[1][:len(filesearch[1])-4]
					releasedirname = filesearch[0].split(os.sep)
					if 'rar' in israr:
						releasedirname = releasedirname[-2]
					else:
						releasedirname = releasedirname[-1]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
					#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
					subsfilename = justfile[:len(justfile)-4]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
					#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
					#Check for multi CD Releases
					multicds_pattern = "\+?(cd\d)\+?"
					multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
					multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
					#Start choosing the right subtitle(s)
					if searchsubscount == 1 and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
						break
					elif string.lower(subsfilename) == string.lower(releasefilename) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
						break
					elif string.lower(subsfilename) == string.lower(releasedirname) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
						break
					elif (multicdsubs != None) and (multicdsrls != None) and sync == True:
						multicdsubs = string.lower(multicdsubs.group(1))
						multicdsrls = string.lower(multicdsrls.group(1))
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
						#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
						if multicdsrls == multicdsubs:
							subs_file = filesub
							break
				else:
					#If none is found just open a dialog box for browsing the temporary subtitle folder
					sub_ext = "srt,aas,ssa,sub,smi"
					sub_tmp = []
					for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
						for file in files:
							dirfile = os.path.join(root, file)
							ext = os.path.splitext(dirfile)[1][1:].lower()
							if ext in sub_ext:
								sub_tmp.append(dirfile)
							elif os.path.isfile(dirfile):
								os.remove(dirfile)
					
					# If there are more than one subtitle in the temp dir, launch a browse dialog
					# so user can choose. If only one subtitle is found, parse it to the addon.
					if len(sub_tmp) > 1:
						dialog = xbmcgui.Dialog()
						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, tmp_sub_dir+"/")
						if subs_file == tmp_sub_dir+"/": subs_file = ""
					elif sub_tmp:
						subs_file = sub_tmp[0]
							
		return False, language, subs_file #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, requests
from utilities import log

_ = sys.modules[ "__main__" ].__language__

main_url = "http://ondertitel.com/"
debug_pretext = ""
releases_types   = ['web-dl', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'aac20', 'hdtv', 'dvdrip', 'ac3', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

FETCH_NORMAL = 0
FETCH_COOKIE = 1
FETCH_SUBTITLE = 2

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<a href="/ondertitels/info/Dead-Man-Down/62137.html" style="color: #161616;" class="recent" id="<div class='div_ondertit_afbeeling'><img src='http://ondertitel.com/movie_images/ondertitelcom_84723_902.jpg' alt='' height='178'><div class='div_ondertit_afbeeling_p'>Poster: <strong>demario</strong></div></div>">Dead Man Down</a></strong> <img src="/images/nederlandse_vlag.jpg" height="11">  
					</div>
				</div>
				<div class="div_ondertitel_r_pos">
					<a href="http://www.imdb.com/title/tt2101341/?ref_=sr_1" target="_blank"><img src="/images/imdb_logo.gif" border="0"></a> <img src="/images/good_rate_small.png" height="17"> <font class="font_color_g">1</font> 
				</div>
				<br clear="both">

				<div class="div_ondertitel_vers">
					<i class="i_font">Dead.Man.Down.2013.DVDRip.XVID.AC3.HQ.Hive-CM8 1 CD</i>
"""
subtitle_pattern = "<a href=\"(/ondertitels/info/.+?)\".+?<i class=\"i_font\">(.+?)<\/i>"
# group(1) = link, group(2) = filename


# downloadlink pattern example:
"""
<a href="/getdownload.php?id=45071&userfile=94 Avatar (2009) PROPER TS XviD-MAXSPEED.zip"><b>Download</b></a>
"""
downloadlink_pattern = "a href=\"http://[a-zA-Z0-9\-\.]+/(getdownload.php\?id=\d{1,10}&userfile=.*?\.\w{3})\""
# group(1) = downloadlink

#====================================================================================================================
# Functions
#====================================================================================================================
def getallsubs(content, title, moviefile, subtitles_list):
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
		link = matches.group(1)
		filename = matches.group(2)
		log( __name__ ,"%s Subtitles found: %s (link=%s)" % (debug_pretext, filename, link))
		if isexactmatch(filename, moviefile):
			sync = True
			rating = 10
		else:
			rating = getrating(filename, moviefile)
			sync = False
		subtitles_list.append({'rating': str(rating), 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': sync, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})

def getrating(subsfile, videofile):
	rating = 0
	videofile = string.replace(string.lower("".join(string.split(videofile, '.')[:-1])), '.', '')
	subsfile = string.replace(string.lower(subsfile), '.', '')
	for release_type in releases_types:
		if (release_type in videofile) and (release_type in subsfile):
			rating += 1
	if string.split(videofile, '-')[-1] == string.split(subsfile, '-')[-1]:
		rating += 1
	if rating > 0:
		rating = rating * 2 - 1
		if rating > 9:
			rating = 9
	return rating

def isexactmatch(subsfile, videofile):
	videofile = string.replace(string.replace(string.lower("".join(string.split(videofile, '.')[:-1])), ' ', '.'), '.', '')
	subsfile = string.replace(string.lower(subsfile), '.', '')
	log( __name__ ," comparing subtitle file with videofile (sync?):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (subsfile, videofile) )
	if string.find(subsfile, videofile) > -1:
		log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (subsfile) )
		return True
	else:
		return False

def getdownloadlink(content):
	link = None
	i = 0
	for matches in re.finditer(downloadlink_pattern, content, re.IGNORECASE | re.DOTALL):
		link = matches.group(1)
		i = i + 1
	if i == 1:
		return link
	else:
		return None

def geturl(url, action=FETCH_NORMAL, cookiedata=''):
	log( __name__ ,"%s Getting url:%s" % (debug_pretext, url))
	try:
		if action == FETCH_SUBTITLE:
			r = requests.get(url, cookies=cookiedata)
			return r.content
		elif action == FETCH_COOKIE:
			r = requests.get(url)
			return (r.text, r)
		else:
			r = requests.get(url)
			return r.text
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		return None
		
def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
	subtitles_list = []
	msg = ""
	log( __name__ ,"%s Title = %s" % (debug_pretext, title))
	if len(tvshow) == 0: # only process movies
		url = main_url + "zoeken.php?type=1&trefwoord=" + urllib.quote_plus(title)
		Dutch = False
		if (string.lower(lang1) == "dutch") or (string.lower(lang2) == "dutch") or (string.lower(lang3) == "dutch"):
			Dutch = True
			content = geturl(url, FETCH_NORMAL)
			if content is not None:
				log( __name__ ,"%s Getting subs ..." % debug_pretext)
				moviefile = os.path.basename(file_original_path)
				getallsubs(content, title, moviefile, subtitles_list)
				subtitles_list.sort(key=lambda x: [ x['sync'], x['rating']], reverse = True)
		else:
			log( __name__ ,"%s Dutch language is not selected" % (debug_pretext))
			msg = "Won't work, Ondertitel is only for Dutch subtitles."
	else:
		log( __name__ ,"%s Tv show detected: %s" % (debug_pretext, tvshow))
		msg = "Won't work, Ondertitel is only for movies."
	return subtitles_list, "", msg #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	url = main_url + subtitles_list[pos][ "link" ]
	local_tmp_file = zip_subs
	content, cookie = geturl(url, FETCH_COOKIE)
	downloadlink = getdownloadlink(content)
	if downloadlink is not None:
		try:
			url = main_url + downloadlink
			url = string.replace(url," ","+")
			log( __name__ ,"%s Fetching subtitles using url %s - and cookie: %s" % (debug_pretext, url, cookie.cookies))
			content = geturl(url, FETCH_SUBTITLE)
			if content is not None:
				log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
				local_file_handle = open(local_tmp_file, "w" + "b")
				local_file_handle.write(content)
				local_file_handle.close()
		except:
			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
		log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
		language = subtitles_list[pos][ "language_name" ]
		return True, language, "" #standard output

########NEW FILE########
__FILENAME__ = os_utilities
# -*- coding: utf-8 -*- 

import os
import sys
import xmlrpclib
from utilities import *

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__

BASE_URL_XMLRPC = u"http://api.opensubtitles.org/xml-rpc"

class OSDBServer:

  def __init__( self, *args, **kwargs ):
    self.server = xmlrpclib.Server( BASE_URL_XMLRPC, verbose=0 )
    login = self.server.LogIn("", "", "en", "%s_v%s" %(__scriptname__.replace(" ","_"),__version__))    
    self.osdb_token  = login[ "token" ]

  def mergesubtitles( self ):
    self.subtitles_list = []
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list.sort(key=lambda x: [not x['sync'],x['lang_index']])

  def searchsubtitles( self, srch_string , lang1,lang2,lang3,hash_search, _hash = "000000000", size = "000000000"):
    msg                      = ""
    lang_index               = 3
    searchlist               = []
    self.subtitles_hash_list = []
    self.langs_ids           = [languageTranslate(lang1,0,2), languageTranslate(lang2,0,2), languageTranslate(lang3,0,2)]    
    language                 = languageTranslate(lang1,0,3)
    
    if lang1 != lang2:
      language += "," + languageTranslate(lang2,0,3)
    if lang3 != lang1 and lang3 != lang2:
      language += "," + languageTranslate(lang3,0,3)
  
    log( __name__ ,"Token:[%s]" % str(self.osdb_token))
  
    try:
      if ( self.osdb_token ) :
        if hash_search:
          searchlist.append({'sublanguageid':language, 'moviehash':_hash, 'moviebytesize':str( size ) })
        searchlist.append({'sublanguageid':language, 'query':srch_string })
        search = self.server.SearchSubtitles( self.osdb_token, searchlist )
        if search["data"]:
          for item in search["data"]:
            if item["ISO639"]:
              lang_index=0
              for user_lang_id in self.langs_ids:
                if user_lang_id == item["ISO639"]:
                  break
                lang_index+=1
              flag_image = "flags/%s.gif" % item["ISO639"]
            else:                                
              flag_image = "-.gif"

            if str(item["MatchedBy"]) == "moviehash":
              sync = True
            else:                                
              sync = False

            self.subtitles_hash_list.append({'lang_index'    : lang_index,
                                             'filename'      : item["SubFileName"],
                                             'link'          : item["ZipDownloadLink"],
                                             'language_name' : item["LanguageName"],
                                             'language_flag' : flag_image,
                                             'language_id'   : item["SubLanguageID"],
                                             'ID'            : item["IDSubtitleFile"],
                                             'rating'        : str(int(item["SubRating"][0])),
                                             'format'        : item["SubFormat"],
                                             'sync'          : sync,
                                             'hearing_imp'   : int(item["SubHearingImpaired"]) != 0
                                             })
            
    except:
      msg = "Error Searching For Subs"
    
    self.mergesubtitles()
    return self.subtitles_list, msg

  def download(self, ID, dest, token):
     try:
       import zlib, base64
       down_id=[ID,]
       result = self.server.DownloadSubtitles(self.osdb_token, down_id)
       if result["data"]:
         local_file = open(dest, "w" + "b")
         d = zlib.decompressobj(16+zlib.MAX_WBITS)
         data = d.decompress(base64.b64decode(result["data"][0]["data"]))
         local_file.write(data)
         local_file.close()
         return True
       return False
     except:
       return False
########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

import sys
import os
from utilities import log, hashFile
from os_utilities import OSDBServer
import xbmc

_ = sys.modules[ "__main__" ].__language__   

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
  ok = False
  msg = ""
  hash_search = False
  subtitles_list = []  
  if len(tvshow) > 0:                                            # TvShow
    OS_search_string = ("%s S%.2dE%.2d" % (tvshow,
                                           int(season),
                                           int(episode),)
                                          ).replace(" ","+")      
  else:                                                          # Movie or not in Library
    if str(year) == "":                                          # Not in Library
      title, year = xbmc.getCleanMovieTitle( title )
    else:                                                        # Movie in Library
      year  = year
      title = title
    OS_search_string = title.replace(" ","+")
  log( __name__ , "Search String [ %s ]" % (OS_search_string,))     
 
  if set_temp : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      file_size, SubHash = hashFile(file_original_path, rar)
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  
  log( __name__ ,"Search by hash and name %s" % (os.path.basename( file_original_path ),))
  subtitles_list, msg = OSDBServer().searchsubtitles( OS_search_string, lang1, lang2, lang3, hash_search, SubHash, file_size  )
      
  return subtitles_list, "", msg #standard output
  


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
  
  destination = os.path.join(tmp_sub_dir, "%s.srt" % subtitles_list[pos][ "ID" ])
  result = OSDBServer().download(subtitles_list[pos][ "ID" ], destination, session_id)
  if not result:
    import urllib
    urllib.urlretrieve(subtitles_list[pos][ "link" ],zip_subs)
  
  language = subtitles_list[pos][ "language_name" ]
  return not result,language, destination #standard output
    
    
    
    

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service pipocas.tv version 0.0.5
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# New on Service Pipocas.tv - v0.0.5:
# Developers changed the site security preventing the service to work. Service now works again.
# Fixed download bug when XBMC is set to Portuguese language and probably others.
# Some code cleanup
#
# New on Service Pipocas.tv - v0.0.4:
# Pipocas now is only for registered users so we had todo some changes to the code.
# Fixed bug on Openelec based XBMC preventing to download multiple subtitiles inside a compressed file.
# Some code cleanup
#
# New on Service Pipocas.tv - v0.0.3:
# Fixed bug on the authentication preventing to download the latest subtitles!
#
# New on Service Pipocas.tv - v0.0.2:
# Added authentication system. Now you don't need to wait 24h to download the new subtitles. Go register on the site!!!
# Added Portuguese Brazilian. Now has Portuguese and Portuguese Brazilian.
# Messages now in xbmc choosen language.
# Code re-arrange...
#
# Initial Release of Service Pipocas.tv - v0.0.1:
# Very first version of this service. Expect bugs. Regex is not the best way to parse html so nothing is perfect :)
# If you are watching this then you can see the several approaches I had with regex. The site code is a mess of html :)
# Fortunaly I came up with an ideia that sorted a few things and made the code work. Cheers!
# Expect new versions when the plugin core is changed, to due in a few weeks.
#

# pipocas.tv subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://pipocas.tv/"
debug_pretext = "Pipocas.tv"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
username = __addon__.getSetting( "Pipocasuser" )
password = __addon__.getSetting( "Pipocaspass" )

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="box last-box"> <!-- INFO: IF last box ... add class "last-box" -->
	<div class="colhead">
		<div class="colhead-corner"></div>
		<span class="align-right"> 20/10/2011 18:23:13</span>
				<span><img alt="Portugal" class="title-flag" src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-portugal.png" />  Batman: Year One (2011)</span>
	</div>
	<div class="box-content"><br />
		
		<h1 class="title">
			Release: <input value="Batman.Year.One.2011.DVDRiP.XviD-T00NG0D" style="font-size: 8pt; color:#666666; border: solid #E7E4E0 1px; background-color: #E7E4E0;" type="text" size="105" readonly="readonly" />		</h1>
		
		<ul class="sub-details">
			<li class="sub-box1">
				<img alt="Poster" src="http://img.pipocas.tv/images/1672723.jpg" />			</li>
			<li class="sub-box2">
				<ul>
					<li><span>Fonte:</span>  Tradu��o</li>
					<li><span>CDs:</span> 1</li>
					<li><span>FPS:</span> 23.976</li>
					<li><span>Hits:</span> 30</li>
					<li><span>Coment�rios:</span> 2</li>
					<li><span>Enviada por:</span> <a href="my.php?u=23019"><font style="font-weight:normal;"> arodri</font></a> </li>
				</ul>
			</li>
			<li class="sub-box3">
				<p>Legendas Relacionadas</p>
				<ul>
					<li><span>Portugal <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-portugal.png" alt="Portugal"/></span> <a href="legendas.php?release=1672723&amp;linguagem=portugues&amp;grupo=imdb">1</a></li>
					<li><span>Brasil <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-brazil.png" alt="Brasil"/></span> <a href="legendas.php?release=1672723&amp;linguagem=brasileiro&amp;grupo=imdb">1</a></li>
					<li><span>Espa�a <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-spain.png" alt="Espa�a"/></span> <a href="legendas.php?release=1672723&amp;linguagem=espanhol&amp;grupo=imdb">0</a></li>
					<li><span>England <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-uk.png" alt="UK"/></span> <a href="legendas.php?release=1672723&amp;linguagem=ingles&amp;grupo=imdb">0</a></li>
				</ul>
			</li>
			<li class="sub-box4"><div style="padding-left:25px;"><div id="rate_23671"><ul class="star-rating"><li style="width: 100%;" class="current-rating">.</li><li><a href="/rating.php?id=23671&amp;rate=1&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="one-star" onclick="do_rate(1,23671,'legenda'); return false" title="1 estrela de 5" >1</a></li><li><a href="/rating.php?id=23671&amp;rate=2&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="two-stars" onclick="do_rate(2,23671,'legenda'); return false" title="2 estrelas de 5" >2</a></li><li><a href="/rating.php?id=23671&amp;rate=3&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="three-stars" onclick="do_rate(3,23671,'legenda'); return false" title="3 estrelas de 5" >3</a></li><li><a href="/rating.php?id=23671&amp;rate=4&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="four-stars" onclick="do_rate(4,23671,'legenda'); return false" title="4 estrelas de 5" >4</a></li><li><a href="/rating.php?id=23671&amp;rate=5&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="five-stars" onclick="do_rate(5,23671,'legenda'); return false" title="5 estrelas de 5" >5</a></li></ul>5.00 / 5 de 1 Voto(s)</div></div><br />
				<a href="download.php?id=23671" class="download"></a>
				<a href="info/23671/Batman.Year.One.2011.DVDRiP.XviD-T00NG0D.html" class="info"></a>
								<a href="vagradecer.php?id=23671" class="thanks"></a> 			</li>
		</ul>
		<br class="clr"/>
		
		<div class="horizontal-divider"></div>
		
		<p class="description-title">Descri��o</p>
		<div class="description-box">
			<center><font color="#2B60DE">Batman: Year One </font></center><br />
<br />
<center><b><br />
<br />
Vers�o<br />
Batman.Year.One.2011.DVDRiP.XviD-T00NG0D<br />
<br />
</b></center><br />
<br />
Tradu��o Brasileira &nbsp;por The_Tozz e Dres<br />
<br />
<br />
A adapta��o PtPt: <center><span style="font-size:12px;"><font face="arial"><font color="#0000A0">arodri</font></font> </span></center><br />
<br />
Um agradecimento muito especial �<br />
<br />
<center><b><font color="#008000"><span style="font-size:14px;">FreedOM</span></font></b></center><br />
<br />
Pela revis�o total...<br />
<br />
"""
subtitle_pattern = "<a href=\"info.php(.+?)\" class=\"info\"></a>"
name_pattern = "<h1 class=\"title\">[\r\n\s].+?Release: (.+?)</h1>"
id_pattern = "download.php\?id=(.+?)\""
hits_pattern = "<li><span>Hits:</span> (.+?)</li>"
#desc_pattern = "<div class=\"description-box\">([\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*)<center><iframe"
uploader_pattern = "<a href=\"/my.php\?u.+?:normal;\"> (.+?)</font></a>"
#====================================================================================================================
# Functions
#====================================================================================================================
def _from_utf8(text):
    if isinstance(text, str):
        return text.decode('utf-8')
    else:
        return text

def msgnote(site, text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	text = _from_utf8(text)
	site = _from_utf8(site)
	#log( __name__ ,"%s ipath: %s" % (debug_pretext, icon))
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	# LOGIN FIRST AND THEN SEARCH
	url = main_url + 'vlogin.php'
	req_headers = {
	'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
	'Referer': main_url,
	'Keep-Alive': '300',
	'Connection': 'keep-alive'}
	request = urllib2.Request(url, headers=req_headers)
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	login_data = urllib.urlencode({'username' : username, 'password' : password})
	response = opener.open(request,login_data)

	page = 0
	if languageshort == "pt":
		url = main_url + "legendas.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
	if languageshort == "pb":
		url = main_url + "legendas.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	content = content.read()
	content = content.decode('latin1')
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL) and page < 2:
		#log( __name__ ,"%s Getting '%s' inside while ..." % (debug_pretext, subtitle_pattern))
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
			#log( __name__ ,"%s FILENAME: '%s' ..." % (debug_pretext, matches.group(1)))
			#hits = matches.group(4)
			#id = matches.group(2)
			#movieyear = matches.group(2)
			#no_files = matches.group(3)
			#uploader = string.strip(matches.group(2))
			#downloads = int(matches.group(2)) / 2
			#if (downloads > 10):
			#	downloads=10
			#filename = string.strip(matches.group(1))
			#desc = string.strip(matches.group(1))
			#desc = string.strip(matches.group(13))
			#Remove new lines on the commentaries
			details = matches.group(1)
			content_details = opener.open(main_url + "info.php" + details)
			content_details = content_details.read()
			content_details = content_details.decode('latin1')
			for namematch in re.finditer(name_pattern, content_details, re.IGNORECASE | re.DOTALL):
				filename = string.strip(namematch.group(1))
				desc = filename
				log( __name__ ,"%s FILENAME match: '%s' ..." % (debug_pretext, namematch.group(1)))			
			for idmatch in re.finditer(id_pattern, content_details, re.IGNORECASE | re.DOTALL):
				id = idmatch.group(1)
				log( __name__ ,"%s ID match: '%s' ..." % (debug_pretext, idmatch.group(1)))			
			for upmatch in re.finditer(uploader_pattern, content_details, re.IGNORECASE | re.DOTALL):
				uploader = upmatch.group(1)
			for hitsmatch in re.finditer(hits_pattern, content_details, re.IGNORECASE | re.DOTALL):
				hits = hitsmatch.group(1)
			log( __name__ ,"%s UP match: '%s' ..." % (debug_pretext, upmatch.group(1)))			
			#for descmatch in re.finditer(desc_pattern, content_details, re.IGNORECASE | re.DOTALL):
			#	desc = string.strip(descmatch.group(1))
			#	log( __name__ ,"%s DESC match: '%s' ..." % (debug_pretext, decmatch.group(1)))
			downloads = int(hits) / 4
			if (downloads > 10):
				downloads=10
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]','', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			#filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
			filename = filename + " " + "- Enviado por: " + uploader +  " - Hits: " + hits
			#subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
			subtitles_list.append({'rating': str(downloads), 'filename': filename, 'hits': hits, 'desc': desc, 'sync': sync, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 1
		if languageshort == "pt":
			url = main_url + "legendas.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
		if languageshort == "pb":
			url = main_url + "legendas.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		content = content.decode('latin1')

	
#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	portuguese = 0
	if string.lower(lang1) == "portuguese": portuguese = 1
	elif string.lower(lang2) == "portuguese": portuguese = 2
	elif string.lower(lang3) == "portuguese": portuguese = 3

	portuguesebrazil = 0
	if string.lower(lang1) == "portuguesebrazil": portuguesebrazil = 1
	elif string.lower(lang2) == "portuguesebrazil": portuguesebrazil = 2
	elif string.lower(lang3) == "portuguesebrazil": portuguesebrazil = 3
	
	if ((portuguese > 0) and (portuguesebrazil == 0)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguesebrazil > 0) and (portuguese == 0)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese > 0) and (portuguesebrazil > 0) and (portuguese < portuguesebrazil)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese > 0) and (portuguesebrazil > 0) and (portuguese > portuguesebrazil)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese == 0) and (portuguesebrazil == 0)):
			msg = "Won't work, Pipocas.tv is only for Portuguese and Portuguese Brazil subtitles."
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def get_download(url, download, id):
    req_headers = {
		'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
		'Referer': main_url,
		'Keep-Alive': '300',
		'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)
    download_data = urllib.urlencode({'id' : id})
    request1 = urllib2.Request(download, download_data, req_headers)
    f = opener.open(request1)
    return f 

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext,__language__(30154), 6000)
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
	language = subtitles_list[pos][ "language_name" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))

	url = main_url + 'vlogin.php'
	download = main_url + 'download.php?id=' + id
	req_headers = {
	'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
	'Referer': main_url,
	'Keep-Alive': '300',
	'Connection': 'keep-alive'}
	request = urllib2.Request(url, headers=req_headers)
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	login_data = urllib.urlencode({'username' : username, 'password' : password})
	response = opener.open(request,login_data)
	download_data = urllib.urlencode({'id' : id})
	request1 = urllib2.Request(download, download_data, req_headers)
	content = opener.open(request1)

	downloaded_content = content.read()

	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	
	fname = os.path.join(tmp_sub_dir,str(id))
	if content.info().get('Content-Disposition').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(downloaded_content)
	f.close()
	
	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
	msgnote(debug_pretext,__language__(30155), 3000)
	xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
	time.sleep(2)
	legendas_tmp = []
	# brunoga fixed solution for non unicode caracters
	fs_encoding = sys.getfilesystemencoding()
	for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
		for file in files:
			dirfile = os.path.join(root, file)
			ext = os.path.splitext(dirfile)[1][1:].lower()
			if ext in sub_ext:
				legendas_tmp.append(dirfile)
			elif os.path.isfile(dirfile):
				os.remove(dirfile)
	
	msgnote(debug_pretext,__language__(30156), 3000)
	searchrars = recursive_glob(extract_path, packext)
	searchrarcount = len(searchrars)
	if searchrarcount > 1:
		for filerar in searchrars:
			if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
				try:
					xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
				except:
					return False
	time.sleep(1)
	searchsubs = recursive_glob(extract_path, subext)
	searchsubscount = len(searchsubs)
	for filesub in searchsubs:
		nopath = string.split(filesub, extract_path)[-1]
		justfile = nopath.split(os.sep)[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
		#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
		releasefilename = filesearch[1][:len(filesearch[1])-4]
		releasedirname = filesearch[0].split(os.sep)
		if 'rar' in israr:
			releasedirname = releasedirname[-2]
		else:
			releasedirname = releasedirname[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
		#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
		subsfilename = justfile[:len(justfile)-4]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
		#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
		#Check for multi CD Releases
		multicds_pattern = "\+?(cd\d)\+?"
		multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#Start choosing the right subtitle(s)
		if searchsubscount == 1 and sync == True:
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
			break
		elif string.lower(subsfilename) == string.lower(releasefilename):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
			break
		elif string.lower(subsfilename) == string.lower(releasedirname):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
			break
		elif (multicdsubs != None) and (multicdsrls != None):
			multicdsubs = string.lower(multicdsubs.group(1))
			multicdsrls = string.lower(multicdsrls.group(1))
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
			#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
			if multicdsrls == multicdsubs:
				subs_file = filesub
				subtitle = subs_file
				break

	else:
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
		if len(legendas_tmp) > 1:
			dialog = xbmcgui.Dialog()
			subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
			if subtitle == extract_path+"/": subtitle = ""
		elif legendas_tmp:
			subtitle = legendas_tmp[0]
	
	msgnote(debug_pretext,__language__(30157), 3000)
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output
########NEW FILE########
__FILENAME__ = pn_utilities
# -*- coding: utf-8 -*- 

import sys
import os
import xmlrpclib
from utilities import *
from xml.dom import minidom
import urllib

try:
  # Python 2.6 +
  from hashlib import md5 as md5
  from hashlib import sha256
except ImportError:
  # Python 2.5 and earlier
  from md5 import md5
  from sha256 import sha256
  
__addon__      = sys.modules[ "__main__" ].__addon__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__

USER_AGENT = "%s_v%s" % (__scriptname__.replace(" ","_"),__version__ )

def compare_columns(b,a):
  return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] ) 

class OSDBServer:
  def create(self):
    self.subtitles_hash_list = []
    self.subtitles_list = []
    self.subtitles_name_list = []
 
  def mergesubtitles( self, stack ):
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_name_list ) > 0 ):
      for item in self.subtitles_name_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )                

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list = sorted(self.subtitles_list, compare_columns)

  def searchsubtitles_pod( self, movie_hash, lang1,lang2,lang3, stack):
#    movie_hash = "e1b45885346cfa0b" # Matrix Hash, Debug only
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')      
    pod_session = ""
    hash_pod =[str(movie_hash)]
    lang = []
    lang.append(lang1)
    if lang1!=lang2:
      lang.append(lang2)
    if lang3!=lang2 and lang3!=lang1:
      lang.append(lang3)
    try:
      init = podserver.initiate(USER_AGENT)
      hash = md5()
      hash.update(__addon__.getSetting( "PNpass" ))
      password256 = sha256(str(hash.hexdigest()) + str(init['nonce'])).hexdigest()
      if str(init['status']) == "200":
        pod_session = init['session']
        podserver.authenticate(pod_session, __addon__.getSetting( "PNuser" ), password256)
        podserver.setFilters(pod_session, True, lang , False)
        search = podserver.search(pod_session , hash_pod)
        if str(search['status']) == "200" and len(search['results']) > 0 :
          search_item = search["results"][movie_hash]
          for item in search_item["subtitles"]:
            if item["lang"]:
              flag_image = "flags/%s.gif" % (item["lang"],)
            else:                                                           
              flag_image = "-.gif"
            link = str(item["id"])
            if item['release'] == "":
              episode = search_item["tvEpisode"]
              if str(episode) == "0":
                name = "%s (%s)" % (str(search_item["movieTitle"]),str(search_item["movieYear"]),)
              else:
                name = "%s S(%s)E(%s)" % (str(search_item["movieTitle"]),str(search_item["tvSeason"]), str(episode), )
            else:
              name = item['release']
            if item["inexact"]:
              sync1 = False
            else:
              sync1 = True
            
            self.subtitles_hash_list.append({'filename'      : name,
                                             'link'          : link,
                                             "language_name" : languageTranslate((item["lang"]),2,0),
                                             "language_flag" : flag_image,
                                             "language_id"   : item["lang"],
                                             "ID"            : item["id"],
                                             "sync"          : sync1,
                                             "format"        : "srt",
                                             "rating"        : str(int(item['rating'])*2),
                                             "hearing_imp"   : "n" in item['flags']
                                             })
        self.mergesubtitles(stack)
      return self.subtitles_list,pod_session
    except :
      return self.subtitles_list,pod_session

  def searchsubtitlesbyname_pod( self, name, tvshow, season, episode, lang1, lang2, lang3, year, stack ):
    if len(tvshow) > 1:
      name = tvshow                
    search_url1 = None
    search_url2 = None
    search_url_base = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=%s&sJ=%s&sY=%s&sTS=%s&sTE=%s&sXML=1&lang=0" % (name.replace(" ","+"), "%s", str(year), str(season), str(episode))
    search_url = search_url_base % str(lang1)
    log( __name__ ,"%s - Language 1" % search_url)        
    if lang2!=lang1:
      search_url1 = search_url_base % str(lang2)
      log( __name__ ,"%s - Language 2" % search_url1)             
    if lang3!=lang1 and lang3!=lang2:
      search_url2 = search_url_base % str(lang3)
      log( __name__ ,"%s - Language 3" % search_url2)         
    try:
      subtitles = self.fetch(search_url)
      if search_url1 is not None: 
        subtitles1 = self.fetch(search_url1)
        if subtitles1:
          subtitles = subtitles + subtitles1             
      if search_url2 is not None: 
        subtitles2 = self.fetch(search_url2)
        if subtitles1:
          subtitles = subtitles + subtitles1
      if subtitles:
        url_base = "http://www.podnapisi.net/ppodnapisi/download/i/"
        for subtitle in subtitles:
          subtitle_id = 0
          rating      = 0
          filename    = ""
          movie       = ""
          lang_name   = ""
          lang_id     = ""
          flag_image  = ""
          link        = ""
          format      = "srt"
          hearing_imp = False
          if subtitle.getElementsByTagName("title")[0].firstChild:
            movie = subtitle.getElementsByTagName("title")[0].firstChild.data
          if subtitle.getElementsByTagName("release")[0].firstChild:
            filename = subtitle.getElementsByTagName("release")[0].firstChild.data
            if len(filename) < 2 :
              filename = "%s (%s).srt" % (movie,year,)
          else:
            filename = "%s (%s).srt" % (movie,year,) 
          if subtitle.getElementsByTagName("rating")[0].firstChild:
            rating = int(subtitle.getElementsByTagName("rating")[0].firstChild.data)*2
          if subtitle.getElementsByTagName("languageId")[0].firstChild:
            lang_name = languageTranslate(subtitle.getElementsByTagName("languageId")[0].firstChild.data, 1,2)
          if subtitle.getElementsByTagName("id")[0].firstChild:
            subtitle_id = subtitle.getElementsByTagName("id")[0].firstChild.data
          if subtitle.getElementsByTagName("flags")[0].firstChild:
              hearing_imp = "n" in subtitle.getElementsByTagName("flags")[0].firstChild.data
          flag_image = "flags/%s.gif" % ( lang_name, )
          link = str(subtitle_id)
          self.subtitles_name_list.append({'filename':filename,
                                           'link':link,
                                           'language_name' : languageTranslate((lang_name),2,0),
                                           'language_id'   : lang_id,
                                           'language_flag' : flag_image,
                                           'movie'         : movie,
                                           "ID"            : subtitle_id,
                                           "rating"        : str(rating),
                                           "format"        : format,
                                           "sync"          : False,
                                           "hearing_imp"   : hearing_imp
                                           })
        self.mergesubtitles(stack)
      return self.subtitles_list
    except :
      return self.subtitles_list
  
  def download(self,pod_session,  id):
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')  
    init = podserver.initiate(USER_AGENT)
    hash = md5()
    hash.update(__addon__.getSetting( "PNpass" ))
    id_pod =[]
    id_pod.append(str(id))
    password256 = sha256(str(hash.hexdigest()) + str(init['nonce'])).hexdigest()
    if str(init['status']) == "200":
      pod_session = init['session']
      auth = podserver.authenticate(pod_session, __addon__.getSetting( "PNuser" ), password256)
      if auth['status'] == 300: 
        log( __name__ ,"Authenticate [%s]" % "InvalidCredentials")
      download = podserver.download(pod_session , id_pod)
      if str(download['status']) == "200" and len(download['names']) > 0 :
        download_item = download["names"][0]
        if str(download["names"][0]['id']) == str(id):
          return "http://www.podnapisi.net/static/podnapisi/%s" % download["names"][0]['filename']
          
    return None  
  
  def fetch(self,url):
    socket = urllib.urlopen( url )
    result = socket.read()
    socket.close()
    xmldoc = minidom.parseString(result)
    return xmldoc.getElementsByTagName("subtitle")    

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

import sys
import os
from utilities import languageTranslate, log, hashFile
from pn_utilities import OSDBServer
import xbmc
import urllib

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input     
  ok = False
  msg = ""
  osdb_server = OSDBServer()
  osdb_server.create()    
  subtitles_list = []
  file_size = ""
  hashTry = ""
  language1 = languageTranslate(lang1,0,1)
  language2 = languageTranslate(lang2,0,1)
  language3 = languageTranslate(lang3,0,1)  
  if set_temp : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      file_size, SubHash = hashFile(file_original_path, False)
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  if hash_search :
    log( __name__ ,"Search for [%s] by hash" % (os.path.basename( file_original_path ),))
    subtitles_list, session_id = osdb_server.searchsubtitles_pod( SubHash ,language1, language2, language3, stack)
  if not subtitles_list:
    log( __name__ ,"Search for [%s] by name" % (os.path.basename( file_original_path ),))
    subtitles_list = osdb_server.searchsubtitlesbyname_pod( title, tvshow, season, episode, language1, language2, language3, year, stack )
  return subtitles_list, "", "" #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
  osdb_server = OSDBServer()
  url = osdb_server.download(session_id, subtitles_list[pos][ "link" ])
  if url != None:
    local_file = open(zip_subs, "w" + "b")
    f = urllib.urlopen(url)
    local_file.write(f.read())
    local_file.close()
  
  language = subtitles_list[pos][ "language_name" ]
  return True,language, "" #standard output
    
########NEW FILE########
__FILENAME__ = sha256
#!/usr/bin/python
__author__ = 'Thomas Dixon'
__license__ = 'MIT'

import copy, struct, sys

def new(m=None):
    return sha256(m)

class sha256(object):
    _k = (0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
          0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
          0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
          0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
          0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
          0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
          0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
          0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
          0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
          0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
          0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
          0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
          0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
          0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
          0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
          0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2)
    _h = (0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)
    _output_size = 8
    
    blocksize = 1
    block_size = 64
    digest_size = 32
    
    def __init__(self, m=None):        
        self._buffer = ''
        self._counter = 0
        
        if m is not None:
            if type(m) is not str:
                raise TypeError, '%s() argument 1 must be string, not %s' % (self.__class__.__name__, type(m).__name__)
            self.update(m)
        
    def _rotr(self, x, y):
        return ((x >> y) | (x << (32-y))) & 0xFFFFFFFF
                    
    def _sha256_process(self, c):
        w = [0]*64
        w[0:15] = struct.unpack('!16L', c)
        
        for i in range(16, 64):
            s0 = self._rotr(w[i-15], 7) ^ self._rotr(w[i-15], 18) ^ (w[i-15] >> 3)
            s1 = self._rotr(w[i-2], 17) ^ self._rotr(w[i-2], 19) ^ (w[i-2] >> 10)
            w[i] = (w[i-16] + s0 + w[i-7] + s1) & 0xFFFFFFFF
        
        a,b,c,d,e,f,g,h = self._h
        
        for i in range(64):
            s0 = self._rotr(a, 2) ^ self._rotr(a, 13) ^ self._rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = s0 + maj
            s1 = self._rotr(e, 6) ^ self._rotr(e, 11) ^ self._rotr(e, 25)
            ch = (e & f) ^ ((~e) & g)
            t1 = h + s1 + ch + self._k[i] + w[i]
            
            h = g
            g = f
            f = e
            e = (d + t1) & 0xFFFFFFFF
            d = c
            c = b
            b = a
            a = (t1 + t2) & 0xFFFFFFFF
            
        self._h = [(x+y) & 0xFFFFFFFF for x,y in zip(self._h, [a,b,c,d,e,f,g,h])]
        
    def update(self, m):
        if not m:
            return
        if type(m) is not str:
            raise TypeError, '%s() argument 1 must be string, not %s' % (sys._getframe().f_code.co_name, type(m).__name__)
        
        self._buffer += m
        self._counter += len(m)
        
        while len(self._buffer) >= 64:
            self._sha256_process(self._buffer[:64])
            self._buffer = self._buffer[64:]
            
    def digest(self):
        mdi = self._counter & 0x3F
        length = struct.pack('!Q', self._counter<<3)
        
        if mdi < 56:
            padlen = 55-mdi
        else:
            padlen = 119-mdi
        
        r = self.copy()
        r.update('\x80'+('\x00'*padlen)+length)
        return ''.join([struct.pack('!L', i) for i in r._h[:self._output_size]])
        
    def hexdigest(self):
        return self.digest().encode('hex')
        
    def copy(self):
        return copy.deepcopy(self)

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Service PT-SUBS.NET version 0.1.5
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service PT-SUBS.NET v0.1.6:
# Added uuid for better file handling, no more hangups.
#
# Initial Release of Service PT-SUBS.NET - v0.1.5:
# TODO: re-arrange code :)
#
# PT-SUBS.NET subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

main_url = "http://www.pt-subs.net/site/"
debug_pretext = "PT-SUBS"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
desc_pattern = "<td><b>Descri.+?</b><br\s/>(.+?)<br\s/><a\shref="
subtitle_pattern = "<tr><td><a\shref=\"(.+?)\">(.+?)</a></td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td></tr>"
# group(1) = Download link, group(2) = Name, group(3) = Visualizações, group(4) = N Legendas, group(5) = Tamanho, group(6) = Data
#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "PTSuser" )
	password = __addon__.getSetting( "PTSpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	opener.open(main_url+'index.php', login_data)

	page = 0
	if languageshort == "pt":
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	content = content.read()
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s Getting '%s' list ..." % (debug_pretext, content))
	#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(4)
			id = matches.group(1)
			no_files = matches.group(3)
			downloads = int(matches.group(4)) / 10
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(2))
			content_desc = opener.open(id)
			content_desc = content_desc.read()
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s Getting '%s' desc" % (debug_pretext, content_desc))
			for descmatch in re.finditer(desc_pattern, content_desc, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
				desc = string.strip(descmatch.group(1))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			desc = re.sub('&quot;','"',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			filename = filename + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 10
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s Getting '%s' list part xxx..." % (debug_pretext, content))

#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp





def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	portuguese = 0
	if string.lower(lang1) == "portuguese": portuguese = 1
	elif string.lower(lang2) == "portuguese": portuguese = 2
	elif string.lower(lang3) == "portuguese": portuguese = 3

	getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if portuguese == 0:
		msg = "Won't work, LegendasDivx is only for Portuguese subtitles!"
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	id = subtitles_list[pos][ "id" ]
	id = string.split(id,"=")
	id = id[-1]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "PTSuser" )
	password = __addon__.getSetting( "PTSpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	#This is where you are logged in
	resp = opener.open('http://www.pt-subs.net/site/index.php', login_data)
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s resposta '%s' subs ..." % (debug_pretext, resp))
	#Now you download the subtitles
	language = subtitles_list[pos][ "language_name" ]
	if string.lower(language) == "portuguese":
		content = opener.open('http://www.pt-subs.net/site/index.php?action=downloads;sa=downfile;id=' + id)

	if content is not None:
		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
		if header == 'rar':
			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".rar")
			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
			packed = True
		elif header == 'zip':
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".zip")
			packed = True
		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".srt") # assume unpacked sub file is an '.srt'
			subs_file = local_tmp_file
			packed = False
		log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
		try:
			log( __name__ ,"%s file: write in %s" % (debug_pretext, local_tmp_file)) #EGO
			local_file_handle = open(local_tmp_file, "wb")
			shutil.copyfileobj(content.fp, local_file_handle)
			local_file_handle.close()
		except:
			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
		if packed:
			files = os.listdir(tmp_sub_dir)
			init_filecount = len(files)
			log( __name__ ,"%s file: number init_filecount %s" % (debug_pretext, init_filecount)) #EGO
			filecount = init_filecount
			max_mtime = 0
			# determine the newest file from tmp_sub_dir
			for file in files:
				if (string.split(file,'.')[-1] in ['srt','sub','txt']):
					mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
					if mtime > max_mtime:
						max_mtime =  mtime
			init_max_mtime = max_mtime
			time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
			xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
			waittime  = 0
			while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
				time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
				files = os.listdir(tmp_sub_dir)
				log( __name__ ,"%s DIRLIST '%s'" % (debug_pretext, files))
				filecount = len(files)
				# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
				for file in files:
					if (string.split(file,'.')[-1] in ['srt','sub','txt']):
						mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
						if (mtime > max_mtime):
							max_mtime =  mtime
				waittime  = waittime + 1
			if waittime == 20:
				log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
			else:
				log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
				searchrars = recursive_glob(tmp_sub_dir, packext)
				searchrarcount = len(searchrars)
				if searchrarcount > 1:
					for filerar in searchrars:
						if filerar != os.path.join(tmp_sub_dir,'ldivx.rar') and filerar != os.path.join(tmp_sub_dir,'ldivx.zip'):
							xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + tmp_sub_dir +")")
				time.sleep(1)
				searchsubs = recursive_glob(tmp_sub_dir, subext)
				searchsubscount = len(searchsubs)
				for filesub in searchsubs:
					nopath = string.split(filesub, tmp_sub_dir)[-1]
					justfile = nopath.split(os.sep)[-1]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
					#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
					releasefilename = filesearch[1][:len(filesearch[1])-4]
					releasedirname = filesearch[0].split(os.sep)
					if 'rar' in israr:
						releasedirname = releasedirname[-2]
					else:
						releasedirname = releasedirname[-1]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
					#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
					subsfilename = justfile[:len(justfile)-4]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
					#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
					#Check for multi CD Releases
					multicds_pattern = "\+?(cd\d)\+?"
					multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
					multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
					#Start choosing the right subtitle(s)
					if searchsubscount == 1 and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
						break
					elif string.lower(subsfilename) == string.lower(releasefilename) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
						break
					elif string.lower(subsfilename) == string.lower(releasedirname) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
						break
					elif (multicdsubs != None) and (multicdsrls != None) and sync == True:
						multicdsubs = string.lower(multicdsubs.group(1))
						multicdsrls = string.lower(multicdsrls.group(1))
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
						#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
						if multicdsrls == multicdsubs:
							subs_file = filesub
							break
				else:
					#If none is found just open a dialog box for browsing the temporary subtitle folder
					sub_ext = "srt,aas,ssa,sub,smi"
					sub_tmp = []
					for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
						for file in files:
							dirfile = os.path.join(root, file)
							ext = os.path.splitext(dirfile)[1][1:].lower()
							if ext in sub_ext:
								sub_tmp.append(dirfile)
							elif os.path.isfile(dirfile):
								os.remove(dirfile)
					
					# If there are more than one subtitle in the temp dir, launch a browse dialog
					# so user can choose. If only one subtitle is found, parse it to the addon.
					if len(sub_tmp) > 1:
						dialog = xbmcgui.Dialog()
						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, tmp_sub_dir+"/")
						if subs_file == tmp_sub_dir+"/": subs_file = ""
					elif sub_tmp:
						subs_file = sub_tmp[0]
							
		return False, language, subs_file #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

#===============================================================================
# RegieLive.ro subtitles service.
# Version: 1.1
#
# Change log:
# 1.1 - Year is used for filtering (if available)
# 1.0 - First release.
#
# Created by: ThumbGen (2012)
#===============================================================================
import os, re, xbmc, xbmcgui, string, time, urllib2, cookielib
from utilities import log

BASE_URL = "http://subtitrari.regielive.ro/"
debug_pretext = ""
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11'
HOST = 'subtitrari.regielive.ro'
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

#===============================================================================
# Regular expression patterns
#===============================================================================

SEARCH_RESULTS_PATTERN = "An:</strong> (\d{4})<br/>.*?Subtitrari: </strong><a href=\"http://subtitrari\\.regielive\\.ro/([^/]+)/\""
SUBTITLE_LIST_PATTERN = 'subtitle_details left">[^<]+<a href="[^\"]+" class="b">(?P<title>[^<]+)</a> &nbsp;&nbsp;&nbsp;\[<a href="(?P<link>[^"]+)"  title="Download">Download</a>\]<br/>[^<]+<strong>Nr\. CD:</strong> (?P<cd>\d)(?P<opt>[^<]*<strong>Framerate:</strong>\s(?P<frame>[^\s]+) FPS)?.*?nota=\'(?P<rating>[\d\.]+)\' voturi'

TV_SEARCH_RESULTS_PATTERN = "An:</strong> (\d{4})<br/>.*?Subtitrari: </strong><a href=\"http://subtitrari\\.regielive\\.ro/([^/]+)/\""
TVSHOW_LIST_PATTERN_PREFIX = '</li>.*?<li class="subtitrare vers_\d+ ep_'
TVSHOW_LIST_PATTERN_SUFFIX = '">.*?<a href="[^"]+" class="download left" title="Download"></a>.*?<div class="subtitle_details left">[^<]+<a href="[^"]+" class="b">(?P<title>[^<]+)</a> &nbsp;&nbsp;&nbsp;\[<a href="(?P<link>[^"]+)"  title="Download">Download</a>\]<br/>(?P<opt2>[^<]+<strong>Nr\. CD:</strong> (?P<cd>\d))?(?P<opt>[^<]*<strong>Framerate:</strong>\s(?P<frame>[^\s]+) FPS)?.*?nota=\'(?P<rating>[\d\.]+)\' voturi'

#===============================================================================
# Private utility functions
#===============================================================================

# the function checks if the name of the subtitle is matching exactly the name of the video file
def isExactMatch(subsfile, videofile):
    match = re.match("(.*)\.", videofile)
    if match:
        videofile = string.lower(match.group(1))
        p = re.compile('(\s|\.|-)*cd\d(\s|\.|-)*', re.IGNORECASE)
        videofile = p.sub('', videofile)
        subsfile = string.lower(subsfile)
        if string.find(string.lower(subsfile),string.lower(videofile)) > -1:
            log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
            return True
        else:
            return False
    else:
        return False

# retrieves the content of the url (by using the specified referer in the headers)
def getURL(url, referer):
    #log( __name__ ,"Getting url: %s with referer %s" % (url, referer))
    opener.addheaders = [('User-agent', USER_AGENT),
                         ('Host', HOST),
                         ('Referer', referer)]
    content = None
    try:
        response = opener.open(url)
        content = response.read()
        response.close()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
    #log( __name__ ,"Got content from url: %s" % (url))
    return content
    
# returns the proper rating (converting the float rating from the website to the format accepted by the addon) 
def getFormattedRating(rating):
    return str(int(round(float(rating) * 2)))

# decide if the current subtitle is in sync
def isSync(title, file_original_path):
    return isExactMatch(title, os.path.basename(file_original_path))

def getReferer(pageId):
    return BASE_URL + pageId + '/'

def addSubtitle(subtitlesList, sync, title, link, referer, rating,cd):
    subtitlesList.append({'sync': sync,
                          'filename': title, 
                          'subtitle_id': link,
                          'referer': referer,
                          'rating':getFormattedRating(rating),
                          'language_flag': 'flags/ro.gif',
                          'language_name': "Romanian",
                          'cd':cd})
    
# sort subtitlesList first by sync then by rating
def sortSubtitlesList(subtitlesList):
    # Bubble sort, to put syncs on top
    #for n in range(0,len(subtitlesList)):
        #for i in range(1, len(subtitlesList)):
         #   temp = subtitlesList[i]
            #if subtitlesList[i]["sync"] > subtitlesList[i-1]["sync"]:
                #subtitlesList[i] = subtitlesList[i-1]
                #subtitlesList[i-1] = temp
    if( len (subtitlesList) > 0 ):
        subtitlesList.sort(key=lambda x: [ x['sync'],getFormattedRating(x['rating'])], reverse = True)
    
# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(file_original_path, subtitlePageID, subtitlesList):
    referer = getReferer(subtitlePageID)
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + subtitlePageID, referer)
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(SUBTITLE_LIST_PATTERN, subtitlePage, re.IGNORECASE | re.DOTALL)
    #log( __name__ ,"found subtitles: %d" % (len(foundSubtitles)))
    for (title,link,cd,opt,frame,rating) in foundSubtitles:
        #log( __name__ ,"title:%s link: %s  cd: %s, rating: %s" % (title, link, cd, getFormattedRating(rating)))
        addSubtitle(subtitlesList, isSync(title, file_original_path), title, link, referer, rating, cd)

# Same as getAllSubtitles() but receives season and episode numbers and find them.
def getAllTVSubtitles(file_original_path, subtitlePageID, subtitlesList, season, episode):
    referer = getReferer(subtitlePageID)
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + subtitlePageID + "/sezonul-" + season + ".html", referer)
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(TVSHOW_LIST_PATTERN_PREFIX + episode + TVSHOW_LIST_PATTERN_SUFFIX, subtitlePage, re.IGNORECASE | re.DOTALL)
    #log( __name__ ,"found subtitles: %d" % (len(foundSubtitles)))
    for (title,link,opt2,cd,opt,frame,rating) in foundSubtitles:
        #log( __name__ ,"title:%s link: %s  cd: %s, rating: %s" % (title, link, cd, getFormattedRating(rating)))
        addSubtitle(subtitlesList, isSync(title, file_original_path), title, link, referer, rating, cd)

def isYearMatch(year, syear):
    return (year == syear) or str(year) == "" or str(syear) == "";

#===============================================================================
# Public interface functions
#===============================================================================

# This function is called when the service is selected through the subtitles
# addon OSD.
# file_original_path -> Original system path of the file playing
# title -> Title of the movie or episode name
# tvshow -> Name of a tv show. Empty if video isn't a tv show (as are season and
#           episode)
# year -> Year
# season -> Season number
# episode -> Episode number
# set_temp -> True iff video is http:// stream
# rar -> True iff video is inside a rar archive
# lang1, lang2, lang3 -> Languages selected by the user
def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitlesList = []
    msg = ""
    categ = '0'
    # Check if searching for tv show or movie and build the search string
    if tvshow:
        searchString = tvshow.replace(" ","+")
        #optimize query to get tvshows only
        categ = '2' 
    else:
        searchString = title.replace(" ","+")
        #optimize query to get movies only
        categ = '1'
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchString))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "cauta.html?s=" + searchString + "&categ=" + categ, 'subtitrari.regielive.ro')
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Didn't find any subs, please try again later."

    # When searching for episode 1 Sratim.co.il returns episode 1,10,11,12 etc'
    # so we need to catch with out pattern the episode and season numbers and
    # only retrieve subtitles from the right result pages.
    if tvshow:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.IGNORECASE | re.DOTALL)
        # Go over all the subtitle pages and add results to our list if season
        # and episode match
        for (syear, sid) in subtitleIDs:
            if(isYearMatch(year,syear)):
                getAllTVSubtitles(file_original_path,sid,subtitlesList,season,episode)
    else:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN, searchResults, re.IGNORECASE | re.DOTALL)
        # Go over all the subtitle pages and add results to our list
        for (syear,sid) in subtitleIDs:
            if(isYearMatch(year,syear)):
                getAllSubtitles(file_original_path,sid,subtitlesList)
    # sort the subtitles list first by sync then by rating
    sortSubtitlesList(subtitlesList)
    
    # Standard output -
    # subtitles list (list of tuples built in getAllSubtitles),
    # session id (e.g a cookie string, passed on to download_subtitles),
    # message to print back to the user
    return subtitlesList, "", msg

# This function is called when a specific subtitle from the list generated by
# search_subtitles() is selected in the subtitles addon OSD.
# subtitles_list -> Same list returned in search function
# pos -> The selected item's number in subtitles_list
# zip_subs -> Full path of zipsubs.zip located in tmp location, if automatic
# extraction is used (see return values for details)
# tmp_sub_dir -> Temp folder used for both automatic and manual extraction
# sub_folder -> Folder where the sub will be saved
# session_id -> Same session_id returned in search function
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subtitle_id = subtitles_list[pos][ "subtitle_id" ]
    language = subtitles_list[pos][ "language_name" ]
    referer = subtitles_list[pos][ "referer" ]
    url = BASE_URL + subtitle_id
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    # get the subtitles .zip
    content = getURL(url, referer)
    # write the subs archive in the temp location
    subs_file = zip_subs
    try:
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, subs_file))
        local_file_handle = open(subs_file, "w" + "b")
        local_file_handle.write(content)
        local_file_handle.close()
    except:
        log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, subs_file))

    # Standard output -
    # True iff the file is packed as zip: addon will automatically unpack it.
    # language of subtitles,
    # Name of subtitles file if not packed (or if we unpacked it ourselves)
    return True, language, ''

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import sys
import os
import xbmc,xbmcgui

import urllib2,urllib,re
from utilities import log, hashFile, languageTranslate

_ = sys.modules[ "__main__" ].__language__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	log(__name__,"Starting search by TV Show")
	if (tvshow == None or tvshow == ''):
		log(__name__,"No TVShow name, stop")
		return [],"",""

	cli = SerialZoneClient()
	found_tv_shows = cli.search_show(tvshow)
	if (found_tv_shows.__len__() == 0):
		log(__name__,"TVShow not found, stop")
		return [],"",""
	elif (found_tv_shows.__len__() == 1):
		log(__name__,"One TVShow found, auto select")
		tvshow_url = found_tv_shows[0]['url']
	else:
		log(__name__,"More TVShows found, user dialog for select")
		menu_dialog = []
		for found_tv_show in found_tv_shows:
			if (found_tv_show['orig_title'] == found_tv_show['title']):
				menu_dialog.append(found_tv_show['title'] + " - " + found_tv_show['years'])
			else:
				menu_dialog.append(found_tv_show['title'] + " / " + found_tv_show['orig_title'] + " - " + found_tv_show['years'])
		dialog = xbmcgui.Dialog()
		found_tv_show_id = dialog.select(_( 610 ), menu_dialog)
		if (found_tv_show_id == -1):
			return [],"",""
		tvshow_url = found_tv_shows[found_tv_show_id]['url']
	log(__name__,"Selected show URL: " + tvshow_url)

	try:
		file_size, file_hash = hashFile(file_original_path, rar)
	except:
		file_size, file_hash = -1, None
	log(__name__, "File size: " + str(file_size))

	found_season_subtitles = cli.list_show_subtitles(tvshow_url,season)

	episode_subtitle_list = None

	for found_season_subtitle in found_season_subtitles:
		if (found_season_subtitle['episode'] == int(episode) and found_season_subtitle['season'] == int(season)):
			episode_subtitle_list = found_season_subtitle
			break

	if episode_subtitle_list == None:
		return [], "", ""

	max_down_count = 0
	for episode_subtitle in episode_subtitle_list['versions']:
		if max_down_count < episode_subtitle['down_count']:
			max_down_count = episode_subtitle['down_count']

	log(__name__,"Max download count: " + str(max_down_count))

	result_subtitles = []
	for episode_subtitle in episode_subtitle_list['versions']:

		print_out_filename = episode_subtitle['rip'] + " by " + episode_subtitle['author']
		if not episode_subtitle['notes'] == None:
			print_out_filename = print_out_filename + "(" + episode_subtitle['notes'] + ")"

		result_subtitles.append({ 
			'filename': print_out_filename,
			'link': episode_subtitle['link'],
			'lang': lng_short2long(episode_subtitle['lang']),
 			'rating': str(episode_subtitle['down_count']*10/max_down_count),
			'sync': (episode_subtitle['file_size'] == file_size),
			'language_flag': 'flags/' + lng_short2flag(episode_subtitle['lang']) + '.gif',
			'language_name': lng_short2long(episode_subtitle['lang']),
		})
	
	log(__name__,result_subtitles)

	# Standard output -
	# subtitles list
	# session id (e.g a cookie string, passed on to download_subtitles),
	# message to print back to the user
	# return subtitlesList, "", msg
	return result_subtitles, "", ""

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	selected_subtitles = subtitles_list[pos]

	log(__name__, selected_subtitles)

	log(__name__,'Downloading subtitle zip')
	res = urllib.urlopen(selected_subtitles['link'])
	subtitles_data = res.read()

	log(__name__,'Saving to file %s' % zip_subs)
	zip_file = open(zip_subs,'wb')
	zip_file.write(subtitles_data)
	zip_file.close()

	# Standard output -
	# True if the file is packed as zip: addon will automatically unpack it.
	# language of subtitles,
	# Name of subtitles file if not packed (or if we unpacked it ourselves)
	# return False, language, subs_file
	return True, selected_subtitles['lang'],""

def lng_short2long(lang):
	if lang == 'CZ': return 'Czech'
	if lang == 'SK': return 'Slovak'
	return 'English'

def lng_long2short(lang):
	if lang == 'Czech': return 'CZ'
	if lang == 'Slovak': return 'SK'
	return 'EN'

def lng_short2flag(lang):
	return languageTranslate(lng_short2long(lang),0,2)


class SerialZoneClient(object):

	def __init__(self):
		self.server_url = "http://www.serialzone.cz"

	def search_show(self,title):
		enc_title = urllib.urlencode({ "co" : title, "kde" : "serialy" })
		res = urllib.urlopen(self.server_url + "/hledani/?" + enc_title)
		shows = []
		try:
			res_body = re.search("<div class=\"column4 wd2 fl-left\">(.+?)<div class=\"cl12px fl-left\"></div>",res.read(), re.IGNORECASE | re.DOTALL).group(1)
		except:
			res_body = res.read()

		for row in re.findall('<li>(.+?)</li>', res_body, re.IGNORECASE | re.DOTALL):
			if re.search("\/serial\/", row):
				show = {}
				show_reg_exp = re.compile("<a href=\"(.+?)\">(.+?) <span class=\"vysilani\">\((.+?)\)</span></a><br />(.+?)$")
				show['url'], show['title'], show['years'], show['orig_title'] = re.search(show_reg_exp, row).groups()
				show['years'] = show['years'].replace("&#8211;", "-")
				shows.append(show)
		return shows

	def list_show_subtitles(self, show_url, show_series):
		res = urllib.urlopen(show_url + "titulky/" + show_series + "-rada/")
		if not res.getcode() == 200: return []
		subtitles = []
		for html_episode in re.findall('<div .+? class=\"sub\-line .+?>(.+?)</div></div></div></div>',res.read(), re.IGNORECASE | re.DOTALL):
			subtitle = {}
			for html_subtitle in html_episode.split("<div class=\"sb1\">"):
				show_numbers = re.search("<div class=\"sub-nr\">(.+?)</div>",html_subtitle)
				if not show_numbers == None:
					subtitle['season'], subtitle['episode'] = re.search("([0-9]+)x([0-9]+)", show_numbers.group(1)).groups()
					subtitle['season'] = int(subtitle['season'])
					subtitle['episode'] = int(subtitle['episode'])
					subtitle['versions'] = []
				else:
					subtitle_version = {}
					subtitle_version['lang'] = re.search("<div class=\"sub-info-menu sb-lang\">(.+?)</div>", html_subtitle).group(1)
					subtitle_version['link'] = re.search("<a href=\"(.+?)\" .+? class=\"sub-info-menu sb-down\">",html_subtitle).group(1)
					subtitle_version['author'] = re.sub("<[^<]+?>", "",(re.search("<div class=\"sub-info-auth\">(.+?)</div>",html_subtitle).group(1)))
					subtitle_version['rip'] = re.search("<div class=\"sil\">Verze / Rip:</div><div class=\"sid\"><b>(.+?)</b>",html_subtitle).group(1)
					try:
						subtitle_version['notes'] = re.search("<div class=\"sil\">Poznámka:</div><div class=\"sid\">(.+?)</div>",html_subtitle).group(1)
					except:
						subtitle_version['notes'] = None
					subtitle_version['down_count'] = int(re.search("<div class=\"sil\">Počet stažení:</div><div class=\"sid2\">(.+?)x</div>",html_subtitle).group(1))
					try:
						subtitle_version['file_size'] = re.search("<span class=\"fl-right\" title=\".+\">\((.+?) b\)</span>",html_subtitle).group(1)
						subtitle_version['file_size'] = int(subtitle_version['file_size'].replace(" ",""))
					except:
						subtitle_version['file_size'] = -1
					subtitle['versions'].append(subtitle_version)
			# print subtitle
			subtitles.append(subtitle)
		return subtitles

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# Shooter.cn subtitles
import sys,os
import hashlib
from httplib import HTTPConnection, OK

import struct
from cStringIO import StringIO
import gzip
import traceback
import random
from urlparse import urlparse

import string
import xbmc, xbmcgui, xbmcvfs
from utilities import log
_ = sys.modules[ "__main__" ].__language__

SVP_REV_NUMBER = 1543
CLIENTKEY = "SP,aerSP,aer %d &e(\xd7\x02 %s %s"
RETRY = 3

def grapBlock(f, offset, size):
    f.seek(offset, 0)
    return f.read(size)

def getBlockHash(f, offset):
    return hashlib.md5(grapBlock(f, offset, 4096)).hexdigest()

def genFileHash(fpath):
    f = xbmcvfs.File(fpath)
    ftotallen = f.size()
    if ftotallen < 8192:
        f.close()
        return ""
    offset = [4096, ftotallen/3*2, ftotallen/3, ftotallen - 8192]
    hash = ";".join(getBlockHash(f, i) for i in offset)
    f.close()
    return hash

def getShortNameByFileName(fpath):
    fpath = os.path.basename(fpath).rsplit(".",1)[0]
    fpath = fpath.lower()
    
    for stop in ["blueray","bluray","dvdrip","xvid","cd1","cd2","cd3","cd4","cd5","cd6","vc1","vc-1","hdtv","1080p","720p","1080i","x264","stv","limited","ac3","xxx","hddvd"]:
        i = fpath.find(stop)
        if i >= 0:
            fpath = fpath[:i]
    
    for c in "[].-#_=+<>,":
        fpath = fpath.replace(c, " ")
    
    return fpath.strip()

def getShortName(fpath):
    for i in range(3):
        shortname = getShortNameByFileName(os.path.basename(fpath))
        if not shortname:
            fpath = os.path.dirname(fpath)
        else:
            return shortname

def genVHash(svprev, fpath, fhash):
    """
    the clientkey is not avaliable now, but we can get it by reverse engineering splayer.exe
    to get the clientkey from splayer.exe:
    f = open("splayer","rb").read()
    i = f.find(" %s %s%s")"""
    global CLIENTKEY
    if CLIENTKEY:
        #sprintf_s( buffx, 4096, CLIENTKEY , SVP_REV_NUMBER, szTerm2, szTerm3, uniqueIDHash);
        vhash = hashlib.md5(CLIENTKEY%(svprev, fpath, fhash)).hexdigest()
    else:
        #sprintf_s( buffx, 4096, "un authiority client %d %s %s %s", SVP_REV_NUMBER, fpath.encode("utf8"), fhash.encode("utf8"), uniqueIDHash);
        vhash = hashlib.md5("un authiority client %d %s %s "%(svprev, fpath, fhash)).hexdigest()
    return vhash

def urlopen(url, svprev, formdata):
    ua = "SPlayer Build %d" % svprev
    #prepare data
    #generate a random boundary
    boundary = "----------------------------" + "%x"%random.getrandbits(48)
    data = []
    for item in formdata:
        data.append("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + item[0] + "\"\r\n\r\n" + item[1] + "\r\n")
    data.append("--" + boundary + "--\r\n")
    data = "".join(data)
    cl = str(len(data))
    
    r = urlparse(url)
    h = HTTPConnection(r.hostname)
    h.connect()
    h.putrequest("POST", r.path, skip_host=True, skip_accept_encoding=True)
    h.putheader("User-Agent", ua)
    h.putheader("Host", r.hostname)
    h.putheader("Accept", "*/*")
    h.putheader("Content-Length", cl)
    h.putheader("Content-Type", "multipart/form-data; boundary=" + boundary)
    h.endheaders()
    
    h.send(data)
    
    resp = h.getresponse()
    if resp.status != OK:
        raise Exception("HTTP response " + str(resp.status) + ": " + resp.reason)
    return resp

def downloadSubs(fpath, lang):
    global SVP_REV_NUMBER
    global RETRY
    pathinfo = fpath
    if os.path.sep != "\\":
        #*nix
        pathinfo = "E:\\" + pathinfo.replace(os.path.sep, "\\")
    filehash = genFileHash(fpath)
    shortname = getShortName(fpath)
    vhash = genVHash(SVP_REV_NUMBER, fpath.encode("utf-8"), filehash)
    formdata = []
    formdata.append(("pathinfo", pathinfo.encode("utf-8")))
    formdata.append(("filehash", filehash))
    if vhash:
        formdata.append(("vhash", vhash))
    formdata.append(("shortname", shortname.encode("utf-8")))
    if lang != "chn":
        formdata.append(("lang", lang))
    
    for server in ["www", "svplayer", "splayer1", "splayer2", "splayer3", "splayer4", "splayer5", "splayer6", "splayer7", "splayer8", "splayer9"]:
        for schema in ["http", "https"]:
            theurl = schema + "://" + server + ".shooter.cn/api/subapi.php"
            for i in range(1, RETRY+1):
                try:
                    print "trying %s (retry %d)" % (theurl, i)
                    handle = urlopen(theurl, SVP_REV_NUMBER, formdata)
                    resp = handle.read()
                    if len(resp) > 1024:
                        return resp
                    else:
                        return ''
                except Exception, e:
                    traceback.print_exc()
    return ''

class Package(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(1)
        self.SubPackageCount = struct.unpack("!B", c)[0]
        print "self.SubPackageCount: %d"%self.SubPackageCount
        self.SubPackages = []
        for i in range(self.SubPackageCount):
            sub = SubPackage(s)
            self.SubPackages.append(sub)

class SubPackage(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(8)
        self.PackageLength, self.DescLength = struct.unpack("!II", c)
        self.DescData = s.read(self.DescLength)
        c = s.read(5)
        self.FileDataLength, self.FileCount = struct.unpack("!IB", c)
        self.Files = []
        for i in range(self.FileCount):
            file = SubFile(s)
            self.Files.append(file)

class SubFile(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(8)
        self.FilePackLength, self.ExtNameLength = struct.unpack("!II", c)
        self.ExtName = s.read(self.ExtNameLength)
        c = s.read(4)
        self.FileDataLength = struct.unpack("!I", c)[0]
        self.FileData = s.read(self.FileDataLength)
        if self.FileData.startswith("\x1f\x8b"):
            gzipper = gzip.GzipFile(fileobj=StringIO(self.FileData))
            self.FileData = gzipper.read()

def getSub(fpath, languagesearch, languageshort, languagelong, subtitles_list):
    subdata = downloadSubs(fpath, languagesearch)
    if (subdata):
        package = Package(StringIO(subdata))
        basename = os.path.basename(fpath)
        barename = basename.rsplit(".",1)[0]
        for sub in package.SubPackages:
            for file in sub.Files:
                if (file.ExtName in ["srt", "txt", "ssa", "smi", "sub"]):
                    filename = ".".join([barename, file.ExtName])
                    subtitles_list.append({'filedata': sub.Files,'filename': filename,'language_name': languagelong,'language_flag':'flags/' + languageshort + '.gif',"rating":'0',"sync": True})

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""

    chinese = 0
    if string.lower(lang1) == "chinese": chinese = 1
    elif string.lower(lang2) == "chinese": chinese = 2
    elif string.lower(lang3) == "chinese": chinese = 3

    english = 0
    if string.lower(lang1) == "english": english = 1
    elif string.lower(lang2) == "english": english = 2
    elif string.lower(lang3) == "english": english = 3

    if ((chinese > 0) and (english == 0)):
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)

    if ((english > 0) and (chinese == 0)):
        getSub(file_original_path, "eng", "en", "English", subtitles_list)

    if ((chinese > 0) and (english > 0) and (chinese < english)):
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)
        getSub(file_original_path, "eng", "en", "English", subtitles_list)

    if ((chinese > 0) and (english > 0) and (chinese > english)):
        getSub(file_original_path, "eng", "en", "English", subtitles_list)
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)

    if ((chinese == 0) and (english == 0)):
        msg = "Won't work, Shooter.cn is only for Chinese and English subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ''
    barename = subtitles_list[pos][ "filename" ].rsplit(".",1)[0]
    language = subtitles_list[pos][ "language_name" ]
    for file in subtitles_list[pos][ "filedata" ]:
        filename = os.path.join(tmp_sub_dir, ".".join([barename, file.ExtName]))
        open(filename,"wb").write(file.FileData)
        if (file.ExtName in ["srt", "txt", "ssa", "smi", "sub"]):
            subs_file = filename
    return False, language, subs_file #standard output


########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-
#===============================================================================
# Subtitle.co.il subtitles service.
# Version: 3.0.4
#
# Change log:
# 1.1 - Fixed bug with movie search: forgot to replace spaces with + signs.
# 1.2 - Better handling of search timeout (no results returned instead of error)
# 2.0 - Changed RE patterns and links to match new site layout (Thanks Shai Bentin!)
#       Fixed TV show subtitles (now navigates site to find requested episode)
# 2.1 - Changed RE patterns again due to layout change (Thanks BBLN for also suggesting different fix).
# 2.2 - Changed url to subtitle.co.il
# 2.3 - Added User Agent to getURL, fixed string related bugs and patterns
# 2.3.1 - stripped (year) from tvshow
# 2.4 - Added support for idx+sub download from sendspace.com
# 3.0 - Added rating algorithem that will try to match correct subtitle release to filename
#       Sorted results list by rating
#       subtitle with rating>8 will have SYNC icon and ability to auto download
# 3.0.1 - Bug fix
# 3.0.2 - Added free user & password.
# 3.0.3 - Added email & password settings.
# 3.0.4 - Get ajax urls instead of load the whole file (saves KB)
#
# Created by: Ori Varon
# Changed by: MeatHook (2.3)
# Changed By: Maor Tal (2.4) 20/02/2013
# Changed By: Maor Tal (3.0) 17/03/2013
# Changed By: thisisbbln (3.0.2) 12/08/2013
# Changed By: thisisbbln (3.0.3) 12/08/2013
# Changed By: CaTz (3.0.4) 29/01/2014
#===============================================================================
import sys, os, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib

from utilities import languageTranslate, log

BASE_URL = "http://www.subtitle.co.il/"
debug_pretext = ""

__addon__      = sys.modules[ "__main__" ].__addon__

#===============================================================================
# Regular expression patterns
#===============================================================================

TV_SEARCH_RESULTS_PATTERN = "<a href=\"viewseries.php\?id=(\d+)[^>]*?title=.*?>"
SEARCH_RESULTS_PATTERN = "<a href=\"view.php\?id=(\d+)[^>]*?title=.*?>"
SUBTITLE_LIST_PATTERN = "downloadsubtitle\.php\?id=(?P<fid>\d*).*?subt_lang.*?title=\"(?P<language>.*?)\".*?subtitle_title.*?title=\"(?P<title>.*?)\""
SSUBTITLE_LIST_PATTERN = "l\.php\?surl=(?P<fid2>\d*).*?subt_lang.*?title=\"(?P<language2>.*?)\".*?subtitle_title.*?title=\"(?P<title2>.*?)\""
COMBINED = SUBTITLE_LIST_PATTERN + "|" + SSUBTITLE_LIST_PATTERN
TV_SEASON_PATTERN = "seasonlink_(?P<slink>\d+).*?>(?P<snum>\d+)</a>"
TV_EPISODE_PATTERN = "episodelink_(?P<elink>\d+).*?>(?P<enum>\d+)</a>"
USER_AGENT = "Mozilla%2F4.0%20(compatible%3B%20MSIE%207.0%3B%20Windows%20NT%206.0)"
releases_types   = ['2011','2009','2012','2010','2013','2014','web-dl', 'webrip', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'ac3', 'aac', 'hdtv', 'dvdscr' ,'dvdrip', 'ac3', 'brrip', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

#===============================================================================
# User data
#===============================================================================
user_email = __addon__.getSetting( "SRAemail" )
user_pass = __addon__.getSetting( "SRApass" )

cookies = cookielib.CookieJar()

#===============================================================================
# Private utility functions
#===============================================================================

def login():
    # Reading cookies into cookiejar, will be used in getUrl()
    log( __name__ ,"Login to Subtitle.co.il")
    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
        log( __name__ ,"Login to Subtitle.co.il 1")
        opener.addheaders = [('User-Agent', USER_AGENT)]
        log( __name__ ,"Login to Subtitle.co.il 2")
        data = urllib.urlencode({'email': user_email, 'password': user_pass, 'Login': 'התחבר' })
        log( __name__ ,"Login to Subtitle.co.il 3")
        # data returned from this pages contains redirection
        response = opener.open(BASE_URL + "login.php", data)
    except:
        log( __name__ ,"Subtitle.co.il - Login failed")
        log( __name__ ,sys.exc_info())

# Returns the corresponding script language name for the Hebrew unicode language
def sratimToScript(language):
    languages = {
        "עברית"     : "Hebrew",
        "אנגלית"    : "English",
        "ערבית"     : "Arabic",
        "צרפתית"    : "French",
        "גרמנית"    : "German",
        "רוסית"     : "Russian",
        "טורקית"    : "Turkish",
        "ספרדית"    : "Spanish"
    }
    return languages[language]
def getrating(subsfile, videofile):
    x=0
    rating = 0
    log(__name__ ,"# Comparing Releases:\n %s [subtitle-rls] \n %s  [filename-rls]" % (subsfile,videofile))
    videofile = "".join(videofile.split('.')[:-1]).lower()
    subsfile = subsfile.lower().replace('.', '')
    videofile = videofile.replace('.', '')
    for release_type in releases_types:
        if (release_type in videofile):
            x+=1
            if (release_type in subsfile): rating += 1
    if(x): rating=(rating/float(x))*4
    # Compare group name
    if videofile.split('-')[-1] == subsfile.split('-')[-1] : rating += 1
    # Group name didnt match 
    # try to see if group name is in the beginning (less info on file less weight)
    elif videofile.split('-')[0] == subsfile.split('-')[-1] : rating += 0.5
    if rating > 0:
        rating = rating * 2
    log(__name__ ,"# Result is:  %f" % rating)
    return round(rating)
    
# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):

    content = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
        opener.addheaders = [('User-Agent', USER_AGENT)]
        response = opener.open(url)  
        content = response.read()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
    return content

# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(fname,subtitlePageID,languageList):
    # Retrieve the subtitles page (html)
    subs= []
    subtitlePage = getURL(BASE_URL + "getajax.php?moviedetailssubtitles=" + subtitlePageID[1:] )
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(COMBINED, subtitlePage)
    for (fid,language,title,fid2,language2,title2) in foundSubtitles:
        log( __name__ ,"%s Is sendspace?: %s" % (debug_pretext, bool(fid2 and len(fid2)>0)))
        #Create Dictionery for XBMC Gui
        if(fid2 and len(fid2)>0):
            fid=fid2
            language=language2
            title=title2
        # Check if the subtitles found match one of our languages was selected
        # by the user
        if (sratimToScript(language) in languageList):
            rating=getrating(title,fname)
            subs.append({'rating': str(rating), 'sync': rating>=8,
                                  'filename': title, 'subtitle_id': fid,
                                  'language_flag': 'flags/' + \
                                  languageTranslate(sratimToScript(language),0,2) + \
                                  '.gif', 'language_name': sratimToScript(language), 'sendspace': (fid2 and len(fid2)>0)})
    return sorted(subs,key=lambda x: int(float(x['rating'])),reverse=True)

                                  
# Same as getAllSubtitles() but receives season and episode numbers and find them.
def getAllTVSubtitles(fname,subtitlePageID,languageList,season,episode):
    # Retrieve the subtitles page (html)
    subs= []
    subtitlePage = getURL(BASE_URL + "viewseries.php?id=" + subtitlePageID + "&m=subtitles#")
    # Retrieve the requested season
    foundSeasons = re.findall(TV_SEASON_PATTERN, subtitlePage)
    for (season_link,season_num) in foundSeasons:
        if (season_num == season):
            # Retrieve the requested episode
            subtitlePage = getURL(BASE_URL + "getajax.php?seasonid="+str(season_link))
            foundEpisodes = re.findall(TV_EPISODE_PATTERN, subtitlePage)
            for (episode_link,episode_num) in foundEpisodes:
                if (episode_num == episode):
                    subtitlePage = getURL(BASE_URL + "getajax.php?episodedetails="+str(episode_link))
                    # Create a list of all subtitles found on page
                    foundSubtitles = re.findall(COMBINED, subtitlePage)
                    for (fid,language,title,fid2,language2,title2) in foundSubtitles:
                        log( __name__ ,"%s Is sendspace?: %s" % (debug_pretext, bool(fid2 and len(fid2)>0)))
                        # Create Dictionery for XBMC Gui
                        if(fid2 and len(fid2)>0):
                            fid=fid2
                            language=language2
                            title=title2
                        # Check if the subtitles found match one of our languages was selected
                        # by the user
                        if (sratimToScript(language) in languageList):
                            rating=getrating(title,fname)
                            subs.append({'rating': str(rating), 'sync': rating>=8,
                                                  'filename': title, 'subtitle_id': fid,
                                                  'language_flag': 'flags/' + \
                                                  languageTranslate(sratimToScript(language),0,2) + \
                                                  '.gif', 'language_name': sratimToScript(language), 'sendspace': (fid2 and len(fid2)>0)})
    # sort, to put syncs on top
    return sorted(subs,key=lambda x: int(float(x['rating'])),reverse=True)




# Extracts the downloaded file and find a new sub/srt file to return.
# Based on Titlovi's service.py
def extractAndFindSub(tempSubDir,tempZipFile):
    # Remember the files currently in the folder and their number
    files = os.listdir(tempSubDir)
    init_filecount = len(files)
    filecount = init_filecount
    max_mtime = 0
    # Determine which is the newest subtitles file in tempSubDir
    for file in files:
        if (string.split(file,'.')[-1] in ['srt','sub']):
            mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
            if mtime > max_mtime:
                max_mtime =  mtime
    init_max_mtime = max_mtime
    # Wait 2 seconds so that the unpacked files are at least 1 second newer
    time.sleep(2)
    # Use XBMC's built-in extractor
    xbmc.executebuiltin("XBMC.Extract(" + tempZipFile + "," + tempSubDir +")")
    waittime  = 0
    while ((filecount == init_filecount) and (waittime < 20) and
           (init_max_mtime == max_mtime)): # Nothing extracted yet
        # Wait 1 second to let the builtin function 'XBMC.extract' unpack
        time.sleep(1)  
        files = os.listdir(tempSubDir)
        filecount = len(files)
        # Determine if there is a newer file created in tempSubDir
        # (indicates that the extraction had completed)
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
                mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
                if (mtime > max_mtime):
                    max_mtime =  mtime
        waittime  = waittime + 1
    if waittime == 20:
        log( __name__ ,"Failed to unpack subtitles in '%s'" % (tempSubDir))
        return ""
    else:
        log( __name__ ,"Unpacked files in '%s'" % (tempSubDir))        
        for file in files:
            # There could be more subtitle files in tempSubDir, so make sure we
            # get the newest subtitle file
            if ((string.split(file, '.')[-1] in ['srt', 'sub']) and
                (os.stat(os.path.join(tempSubDir, file)).st_mtime >
                 init_max_mtime)):
                log( __name__ ,"Unpacked subtitles file '%s'" % (file))        
                return os.path.join(tempSubDir, file)

#===============================================================================
# Public interface functions
#===============================================================================

# This function is called when the service is selected through the subtitles
# addon OSD.
# file_original_path -> Original system path of the file playing
# title -> Title of the movie or episode name
# tvshow -> Name of a tv show. Empty if video isn't a tv show (as are season and
#           episode)
# year -> Year
# season -> Season number
# episode -> Episode number
# set_temp -> True iff video is http:// stream
# rar -> True iff video is inside a rar archive
# lang1, lang2, lang3 -> Languages selected by the user
def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    login()

    subtitlesList = []
    # List of user languages - easier to manipulate
    languageList = [lang1, lang2, lang3]
    msg = ""
 
    # Check if searching for tv show or movie and build the search string
    if tvshow:
        searchString = re.split(r'\s\(\w+\)$',tvshow)[0].replace(" ","+")
    else:
        searchString = title.replace(" ","+")
        
    log( __name__ ,"%s Search string = *%s*" % (debug_pretext, title))
    
    # Retrieve the search results (html)

    searchResults = getURL(BASE_URL + "browse.php?q=" + searchString)
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Search timed out, please try again later."

    # When searching for episode 1 subtitle.co.il returns episode 1,10,11,12 etc'
    # so we need to catch with out pattern the episode and season numbers and
    # only retrieve subtitles from the right result pages.s
    if tvshow:
        # Find TvShow's subtitle page IDs
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,
                                 unicode(searchResults,"utf-8"))
        # Go over all the subtitle pages and add results to our list if season
        # and episode match
        for sid in subtitleIDs:
            subtitlesList =subtitlesList + getAllTVSubtitles(os.path.basename(file_original_path),sid,languageList,season,episode)
    else:
        # Find Movie's subtitle page IDs
        subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN, searchResults)
        # Go over all the subtitle pages and add results to our list
        for sid in subtitleIDs:
            subtitlesList =subtitlesList + getAllSubtitles(os.path.basename(file_original_path),sid,languageList)

    
    
    # Standard output -
    # subtitles list (list of tuples built in getAllSubtitles),
    # session id (e.g a cookie string, passed on to download_subtitles),
    # message to print back to the user
    return subtitlesList, "", msg

# This function is called when a specific subtitle from the list generated by
# search_subtitles() is selected in the subtitles addon OSD.
# subtitles_list -> Same list returned in search function
# pos -> The selected item's number in subtitles_list
# zip_subs -> Full path of zipsubs.zip located in tmp location, if automatic
# extraction is used (see return values for details)
# tmp_sub_dir -> Temp folder used for both automatic and manual extraction
# sub_folder -> Folder where the sub will be saved
# session_id -> Same session_id returned in search function
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subtitle_id = subtitles_list[pos][ "subtitle_id" ]
    language = subtitles_list[pos][ "language_name" ]   
    log( __name__ ,"%s Is subtitle related to sendspace? %s" % (debug_pretext, subtitles_list[pos][ "sendspace" ]))
    if (not subtitles_list[pos][ "sendspace" ]):
        url = BASE_URL + "downloadsubtitle.php?id=" + subtitle_id
        content = getURL(url)
        log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
        filename = "zipsubs.zip"
    else:
        url = BASE_URL + "l.php?surl=" + subtitle_id
        content = getURL(url)
        url = re.search(r'<a id="download_button" href?="(.+sendspace.+\.\w\w\w)" ', content)
        content = None
        if (url):
            url = url.group(1)
            log( __name__ ,"%s Fetching subtitles from sendspace.com using url %s" % (debug_pretext, url))
            content = getURL(url)
            filename = "rarsubs" + re.search(r'\.\w\w\w$',url).group(0)
    # Get the file content using geturl()
    
    if content:
        # Going to write them to file
        local_tmp_file = os.path.join(tmp_sub_dir, filename)
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))

        # Extract the zip file and find the new sub/srt file
        subs_file = extractAndFindSub(tmp_sub_dir,local_tmp_file)
            
    # Standard output -
    # True iff the file is packed as zip: addon will automatically unpack it.
    # language of subtitles,
    # Name of subtitles file if not packed (or if we unpacked it ourselves)
    return False, language, subs_file

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, shutil, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, uuid, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.subclub.eu/"
download_url = "http://www.subclub.eu/down.php?id="
debug_pretext = ""

sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi', 'txt']
packext = ['rar', 'zip']


subtitle_pattern='<a class="sc_link".+?/down.php\?id=([^"]+).+?>(.+?)</a>'

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):
    url = main_url + "jutud.php?tp=nimi&otsing=" + urllib.quote_plus(searchstring)
    content = geturl(url)
    content=content.replace('\r\n','')
    if content is not None:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        for id,filename in re.compile(subtitle_pattern).findall(content):
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
            filesearch = os.path.split(filesearch)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
            dirsearch = filesearch[0].split(os.sep)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
            dirsearch_check = string.split(dirsearch[-1], '.')
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))

            subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

        
def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content = response.read()
        return_url = response.geturl()
        if url != return_url:
            log( __name__ ,"%s Getting redirected url: %s" % (debug_pretext, return_url))
            if (' ' in return_url):
                log( __name__ ,"%s Redirected url contains space (workaround a bug in python redirection: 'http://bugs.python.org/issue1153027', should be solved, but isn't)" % (debug_pretext))
                return_url = return_url.replace(' ','%20')
            response = my_urlopener.open(return_url)
            content = response.read()
            return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    searchstring_notclean = ""
    searchstring = ""
    global israr
    israr = os.path.abspath(file_original_path)
    israr = os.path.split(israr)
    israr = israr[0].split(os.sep)
    israr = string.split(israr[-1], '.')
    israr = string.lower(israr[-1])
    
    if len(tvshow) == 0:
        if 'rar' in israr and searchstring is not None:
            if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
                dirsearch = os.path.abspath(file_original_path)
                dirsearch = os.path.split(dirsearch)
                dirsearch = dirsearch[0].split(os.sep)
                if len(dirsearch) > 1:
                    searchstring_notclean = dirsearch[-3]
                    searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                    searchstring = searchstring[0]
                else:
                    searchstring = title
            else:
                searchstring = title
        elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
            dirsearch = os.path.abspath(file_original_path)
            dirsearch = os.path.split(dirsearch)
            dirsearch = dirsearch[0].split(os.sep)
            if len(dirsearch) > 1:
                searchstring_notclean = dirsearch[-2]
                searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                searchstring = searchstring[0]
            else:
                #We are at the root of the drive!!! so there's no dir to lookup only file#
                title = os.path.split(file_original_path)
                searchstring = title[-1]
        else:
            if title == "":
                title = os.path.split(file_original_path)
                searchstring = title[-1]
            else:
                searchstring = title
            
    if len(tvshow) > 0:
        searchstring = "%s %#02dx%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    estonian = 0
    if string.lower(lang1) == "estonian": estonian = 1
    elif string.lower(lang2) == "estonian": estonian = 2
    elif string.lower(lang3) == "estonian": estonian = 3

    getallsubs(searchstring, "et", "Estonian", file_original_path, subtitles_list, searchstring_notclean)
    if estonian == 0:
        msg = "Won't work, subclub.eu is only for Estonian subtitles."

    return subtitles_list, "", msg #standard output
    
def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
	for extension in pattern:
	    for filename in fnmatch.filter(files, '*.' + extension):
		results.append(os.path.join(base, filename))
    return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    sync = subtitles_list[pos][ "sync" ]
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    if string.lower(language) == "estonian":
        content = opener.open(download_url + id)

    downloaded_content = content.read()
    #Create some variables
    subtitle = ""
    extract_path = os.path.join(tmp_sub_dir, "extracted")
    
    fname = os.path.join(tmp_sub_dir,str(id))
    if content.info().get('Content-Disposition').__contains__('rar'):
      fname += '.rar'
    else:
      fname += '.zip'
    f = open(fname,'wb')
    f.write(downloaded_content)
    f.close()
    
    xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
    time.sleep(2)
    subclub_tmp = []
    fs_encoding = sys.getfilesystemencoding()
    for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
      for file in files:
	dirfile = os.path.join(root, file)
	ext = os.path.splitext(dirfile)[1][1:].lower()
	if ext in sub_ext:
	  subclub_tmp.append(dirfile)
	elif os.path.isfile(dirfile):
	  os.remove(dirfile)
	  
    searchrars = recursive_glob(extract_path, packext)
    searchrarcount = len(searchrars)
    
    if searchrarcount > 1:
      for filerar in searchrars:
	if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
	  try:
	    xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
	  except:
	    return False
    time.sleep(1)
    searchsubs = recursive_glob(extract_path, sub_ext)
    searchsubscount = len(searchsubs)
    for filesub in searchsubs:
      nopath = string.split(filesub, extract_path)[-1]
      justfile = nopath.split(os.sep)[-1]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
      #log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
      releasefilename = filesearch[1][:len(filesearch[1])-4]
      releasedirname = filesearch[0].split(os.sep)
      if 'rar' in israr:
	releasedirname = releasedirname[-2]
      else:
	releasedirname = releasedirname[-1]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
      #log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
      subsfilename = justfile[:len(justfile)-4]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
      #log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
      #Check for multi CD Releases
      multicds_pattern = "\+?(cd\d)\+?"
      multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
      multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
      #Start choosing the right subtitle(s)
      if searchsubscount == 1 and sync == True:
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
	break
      elif string.lower(subsfilename) == string.lower(releasefilename):
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
	break
      elif string.lower(subsfilename) == string.lower(releasedirname):
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
	break
      elif (multicdsubs != None) and (multicdsrls != None):
	multicdsubs = string.lower(multicdsubs.group(1))
	multicdsrls = string.lower(multicdsrls.group(1))
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
	#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
	if multicdsrls == multicdsubs:
	  subs_file = filesub
	  subtitle = subs_file
	  break

    else:
    # If there are more than one subtitle in the temp dir, launch a browse dialog
    # so user can choose. If only one subtitle is found, parse it to the addon.
      if len(subclub_tmp) > 1:
	dialog = xbmcgui.Dialog()
	subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
	if subtitle == extract_path+"/": subtitle = ""
      elif subclub_tmp:
	subtitle = subclub_tmp[0]
    
    language = subtitles_list[pos][ "language_name" ]
    return False, language, subtitle #standard output
########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

import cPickle
import StringIO
import sys
import os
import random
import re
import time
import urllib
import urllib2
import xbmc
import xbmcgui
from utilities import log, languageTranslate

try:
  #Python 2.6 +
  from hashlib import md5
except ImportError:
  #Python 2.5 and earlier
  from md5 import new as md5
  
_ = sys.modules[ "__main__" ].__language__

base_url = 'http://api.thesubdb.com/?%s'
user_agent = 'SubDB/1.0 (XBMCSubtitles/0.1; https://github.com/jrhames/script.xbmc.subtitles)'

def get_languages(languages):
	subdb_languages = []
	for language in languages:
		code = languageTranslate(language,0,2)
		if code == 'pb':
			code = 'pt'
		subdb_languages.append(code)
	return subdb_languages

def get_hash(name):
	data = ""
	m = md5()
	readsize = 64 * 1024
	# with open(name, 'rb') as f:
	f = open(name, 'rb')
	try:
		size = os.path.getsize(name)
		data = f.read(readsize)
		f.seek(-readsize, 2)
		data += f.read(readsize)
	finally:
		f.close()
		
	m.update(data)
	return m.hexdigest()

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	
	if len(file_original_path) > 0:
		# get file hash
		hash = get_hash(file_original_path)
		# do the search
		languages = get_languages([lang1, lang2, lang3])
		params = {'action': 'search', 'hash': hash} #, 'language': ','.join(languages)
		url = base_url % urllib.urlencode(params)
		req = urllib2.Request(url)
		req.add_header('User-Agent', user_agent)
		try:
			# HTTP/1.1 200
			response = urllib2.urlopen(req)
			result = response.readlines()
			subtitles = result[0].split(',')
			for subtitle in subtitles:
				if subtitle in languages:
					filename = os.path.split(file_original_path)[1]
					params = {'action': 'download', 'language': subtitle, 'hash': hash }
					link = base_url % urllib.urlencode(params)
					if subtitle == "pt":						
						flag_image = 'flags/pb.gif'
					else:
						flag_image = "flags/%s.gif" % subtitle
						
					subtitles_list.append({'filename': filename,'link': link,'language_name': languageTranslate(subtitle, 2,0),'language_id':"0",'language_flag':flag_image,'movie':filename,"ID":subtitle,"rating":"10","format": "srt","sync": True})
		except urllib2.HTTPError, e:
			# HTTP/1.1 !200
			return subtitles_list, "", msg #standard output
		except urllib2.URLError, e:
			# Unknown or timeout url
			log( __name__ ,"Service did not respond in time, aborting...")
			msg = _(755)
			return subtitles_list, "", msg #standard output
	        
	return subtitles_list, "", msg #standard output
    
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	language = subtitles_list[pos][ "language_name" ]
	link = subtitles_list[pos][ "link" ]
	file = os.path.splitext(subtitles_list[pos]["filename"])[0]
	ext = ""
	req = urllib2.Request(link)
	req.add_header('User-Agent', user_agent)
	try:
		response = urllib2.urlopen(req)
		ext = response.info()['Content-Disposition'].split(".")[1]
		filename = os.path.join(tmp_sub_dir, "%s.%s" % (file, ext))
		local_file = open(filename, "w" + "b")
		local_file.write(response.read())
		local_file.close()
		return False, language, filename #standard output
	except:
		return False , language, "" #standard output	

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-
# Subdivx.com subtitles, based on a mod of Undertext subtitles
# Adaptation: enric_godes@hotmail.com | Please use email address for your comments

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__


main_url = "http://www.subdivx.com/"
debug_pretext = "subdivx"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================


#Subtitle pattern example:
#<div id="menu_titulo_buscador"><a class="titulo_menu_izq" href="http://www.subdivx.com/X6XMjEzMzIyX-iron-man-2-2010.html">Iron Man 2 (2010)</a></div>
#<img src="img/calif5.gif" class="detalle_calif">
#</div><div id="buscador_detalle">
#<div id="buscador_detalle_sub">Para la versión Iron.Man.2.2010.480p.BRRip.XviD.AC3-EVO, sacados de acá. ¡Disfruten!</div><div id="buscador_detalle_sub_datos"><b>Downloads:</b> 4673 <b>Cds:</b> 1 <b>Comentarios:</b> <a rel="nofollow" href="popcoment.php?idsub=MjEzMzIy" onclick="return hs.htmlExpand(this, { objectType: 'iframe' } )">14</a> <b>Formato:</b> SubRip <b>Subido por:</b> <a class="link1" href="http://www.subdivx.com/X9X303157">TrueSword</a> <img src="http://www.subdivx.com/pais/2.gif" width="16" height="12"> <b>el</b> 06/09/2010  </a></div></div>
#<div id="menu_detalle_buscador">

subtitle_pattern =  "<a\sclass=\"titulo_menu_izq\"\shref=\"http://www.subdivx.com/(.+?).html\">.+?<div\sid=\"buscador_detalle_sub\">(.*?)</div>.+?<b>Downloads:</b>(.+?)<b>Cds:</b>.+?</div></div>"
# group(1) = id to fetch the subs files, group(2) = user comments, may content filename, group(3)= downloads used for ratings



#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list):
    page = 1
    if languageshort == "es":
        url = main_url + "index.php?accion=5&masdesc=&oxdown=1&pg=" + str(page) + "&buscar=" + urllib.quote_plus(searchstring)

    content = geturl(url)
    log( __name__ ,u"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
    while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
            id = matches.group(1)
            downloads = int(re.sub(r',','',matches.group(3))) / 1000
            if (downloads > 10):
                downloads=10
            filename = string.strip(matches.group(2))
            #Remove new lines on the commentaries
            filename = re.sub('\n',' ',filename)
            #Remove Google Ads on the commentaries
            filename = re.sub(r'<script.+?script>','', filename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)
            #Remove HTML tags on the commentaries
            filename = re.sub(r'<[^<]+?>','', filename)
            #Find filename on the comentaries to show sync label
            filesearch = os.path.split(file_original_path)
            sync = False
            if re.search(filesearch[1][:len(filesearch[1])-4], filename):
                sync = True
            try:    
                log( __name__ ,u"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            except:
                pass
            #Find filename on the commentaries and put it in front
            title_first_word = re.split('[\W]+', searchstring)
            comments_list = re.split('\s', filename)
            n = 0
            version = None
            while n<len(comments_list) and version == None:
                version = re.search(title_first_word[0],comments_list[n], re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)
                n=n+1
            if version:
                filename = comments_list[n-1] + " | " + filename
            #End search filename
            subtitles_list.append({'rating': str(downloads), 'filename': filename, 'sync': sync, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        page = page + 1
        url = main_url + "index.php?accion=5&masdesc=&oxdown=1&pg=" + str(page) + "&buscar=" + urllib.quote_plus(searchstring)
        content = geturl(url)

    # Bubble sort, to put syncs on top
    for n in range(0,len(subtitles_list)):
        for i in range(1, len(subtitles_list)):
            temp = subtitles_list[i]
            if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
                subtitles_list[i] = subtitles_list[i-1]
                subtitles_list[i-1] = temp



def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,u"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,u"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,u"%s Search string = %s" % (debug_pretext, searchstring))

    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list)

    if spanish == 0:
        msg = "Won't work, Subdivx is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    url = main_url + str(id) #get the page with the subtitle link, ie http://www.subdivx.com/X6XMjE2NDM1X-iron-man-2-2010
    content = geturl(url)
    match=re.compile('bajar.php\?id=(.*?)&u=(.*?)\"',re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE).findall(content)

    language = subtitles_list[pos][ "language_name" ]
    url = main_url + "bajar.php?id=" + match[0][0] + "&u=" + match[0][1]
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,u"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,u"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,u"%s subdivx: número de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file.encode("utf-8") + "," + tmp_sub_dir.encode("utf-8") +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file.decode("utf-8"))).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,u"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,u"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,u"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file.decode("utf-8"))
        return False, language, subs_file #standard output


########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*- 

################################   Sublight.si #################################


import sys
import os
import xmlrpclib
from utilities import  languageTranslate, log
import time
import array
import httplib
import xbmc
import xml.dom.minidom
import xml.sax.saxutils as SaxUtils
import base64
import gui

try:
  #Python 2.6 +
  from hashlib import md5
except ImportError:
  #Python 2.5 and earlier
  from md5 import new as md5

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, language1, language2, language3, stack ): #standard input

  subtitles_list = []    
  for x in range(3):
    exec("if language%i == 'Serbian'            : language%i = 'SerbianLatin' "     % (x+1,x+1,))
    exec("if language%i == 'Bosnian'            : language%i = 'BosnianLatin' "     % (x+1,x+1,))
  sublightWebService = SublightWebService()
  session_id = sublightWebService.LogInAnonymous()
  
  try:
    video_hash = calculateVideoHash(file_original_path)
  except:
    video_hash = "0000000000000000000000000000000000000000000000000000"
  
  subtitles_list = []
  
  if len(tvshow) < 1:        
    movie_title = title
    episode = ""
    season = ""
  else:
    movie_title = tvshow     
  year = str(year)
       
  log( __name__ ,"Sublight Hash [%s]"                                   % str(video_hash) )
  log( __name__ ,"Language 1: [%s], Language 2: [%s], Language 3: [%s]" % (language1 ,language2 , language3,) )
  log( __name__ ,"Search Title:[%s]"                                    % movie_title )
  log( __name__ ,"Season:[%s]"                                          % season )
  log( __name__ ,"Episode:[%s]"                                         % episode )
  log( __name__ ,"Year:[%s]"                                            % year )
  
  subtitles_list = sublightWebService.SearchSubtitles(session_id,
                                                      video_hash,
                                                      movie_title,
                                                      year,season,
                                                      episode,
                                                      language2,
                                                      language1,
                                                      language3
                                                      )
  
  return subtitles_list, session_id, ""  #standard output
  


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

  subtitle_id              = subtitles_list[pos][ "ID" ]
  language                 = subtitles_list[pos][ "language_name" ]
  sublightWebService       = SublightWebService()
  ticket_id, download_wait = sublightWebService.GetDownloadTicket(session_id, subtitle_id)
  
  if ticket_id != "" :
    icon =  os.path.join(__cwd__,"icon.png")
    if download_wait > 0 :
      delay = int(download_wait)
      for i in range (int(download_wait)):
        line2 = "download will start in %i seconds" % (delay,)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,icon))
        delay -= 1
        time.sleep(1)

    subtitle_b64_data = sublightWebService.DownloadByID(session_id, subtitle_id, ticket_id)
    base64_file_path = os.path.join(tmp_sub_dir, "tmp_su.b64")
    base64_file      = open(base64_file_path, "wb")
    base64_file.write( subtitle_b64_data )
    base64_file.close()
    base64_file      = open(base64_file_path, "r")
    zip_file         = open(zip_subs, "wb")          
    base64.decode(base64_file, zip_file)
    base64_file.close()
    zip_file.close()
  
  return True,language, "" #standard output
  
#
# Integer => Hexadecimal
#
def dec2hex(n, l=0):
  # return the hexadecimal string representation of integer n
  s = "%X" % n
  if (l > 0) :
    while len(s) < l:
      s = "0" + s 
  return s


def calculateVideoHash(filename, isPlaying = True):
  #
  # Check file...
  #
  if not os.path.isfile(filename) :
    return ""
  
  if os.path.getsize(filename) < 5 * 1024 * 1024 :
    return ""

  #
  # Init
  #
  sum = 0
  hash = ""
  
  #
  # Byte 1 = 00 (reserved)
  #
  number = 0
  sum = sum + number
  hash = hash + dec2hex(number, 2) 
  
  #
  # Bytes 2-3 (video duration in seconds)
  #   
  seconds = int( xbmc.Player().getTotalTime() )
  # 
  sum = sum + (seconds & 0xff) + ((seconds & 0xff00) >> 8)
  hash = hash + dec2hex(seconds, 4)
  
  #
  # Bytes 4-9 (video length in bytes)
  #
  filesize = os.path.getsize(filename)
  
  sum = sum + (filesize & 0xff) + ((filesize & 0xff00) >> 8) + ((filesize & 0xff0000) >> 16) + ((filesize & 0xff000000) >> 24)
  hash = hash + dec2hex(filesize, 12) 
  
  #
  # Bytes 10-25 (md5 hash of the first 5 MB video data)
  #
  f = open(filename, mode="rb")
  buffer = f.read( 5 * 1024 * 1024 )
  f.close()
  
  md5hash = md5()
  md5hash.update(buffer)
  
  array_md5 = array.array('B')
  array_md5.fromstring(md5hash.digest())
  for b in array_md5 :
    sum = sum + b

  hash = hash + md5hash.hexdigest()
  
  #
  # Byte 26 (control byte)
  # 
  hash = hash + dec2hex(sum % 256, 2)
  hash = hash.upper()
  
  return hash
    
#
# SublightWebService class
#
class SublightWebService :
  def __init__ (self):
    self.SOAP_HOST                  = "www.sublight.si"
    self.SOAP_SUBTITLES_API_URL     = "/API/WS/Sublight.asmx"
    self.SOAP_SUBLIGHT_UTILITY_URL  = "/SublightUtility.asmx"
    self.LOGIN_ANONYMOUSLY_ACTION   = "http://www.sublight.si/LogInAnonymous4"
    self.SEARCH_SUBTITLES_ACTION    = "http://www.sublight.si/SearchSubtitles3"
    self.GET_DOWNLOAD_TICKET_ACTION = "http://www.sublight.si/GetDownloadTicket2"
    self.DOWNLOAD_BY_ID_ACTION      = "http://www.sublight.si/DownloadByID4"
    self.LOGOUT_ACTION              = "http://www.sublight.si/LogOut"
    
  #
  # Perform SOAP request...
  #
  def SOAP_POST (self, SOAPUrl, SOAPAction, SOAPRequestXML):
    # Handles making the SOAP request
    h = httplib.HTTPConnection(self.SOAP_HOST)
    headers = {
              'Host'           : self.SOAP_HOST,
              'Content-Type'   :'text/xml; charset=utf-8',
              'Content-Length' : len(SOAPRequestXML),
              'SOAPAction'     : '"%s"' % SOAPAction,
              }
    h.request ("POST", SOAPUrl, body=SOAPRequestXML, headers=headers)
    r = h.getresponse()
    d = r.read()
    h.close()
  
    return d
  
  #
  # LoginAnonymous3
  #
  def LogInAnonymous(self):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <LogInAnonymous4 xmlns="http://www.sublight.si/">
                          <clientInfo>
                            <ClientId>OpenSubtitles_OSD</ClientId>
                            <ApiKey>b44bc9b9-91f4-45be-8a49-c9b18ca86566</ApiKey>
                          </clientInfo>
                        </LogInAnonymous4>
                      </soap:Body>
                    </soap:Envelope>"""
    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.LOGIN_ANONYMOUSLY_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    sessionId = xmlUtils.getText( resultDoc, "LogInAnonymous4Result" )
    
    # Return value
    return sessionId


    #
    # LogOut
    #
  def LogOut(self, sessionId):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <LogOut xmlns="http://www.sublight.si/">
                          <session>%s</session>
                        </LogOut>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionId )
                      
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.LOGOUT_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "LogOutResult" )
    
    # Return value
    return result
    
  #
  # SearchSubtitles
  #
  def SearchSubtitles(self, sessionId, videoHash, title, year, season, episode,language1, language2, language3):
    title = SaxUtils.escape(title)    
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <SearchSubtitles3 xmlns="http://www.sublight.si/">
                          <session>%s</session>
                          <videoHash>%s</videoHash>
                          <title>%s</title>
                          %s
                          %s
                          %s
                          <languages>
                            %s
                            %s
                            %s
                          </languages>
                          <genres>
                            <Genre>Movie</Genre>
                            <Genre>Cartoon</Genre>
                            <Genre>Serial</Genre>
                            <Genre>Documentary</Genre>
                            <Genre>Other</Genre>
                            <Genre>Unknown</Genre>
                          </genres>
                          <rateGreaterThan xsi:nil="true" />
                        </SearchSubtitles3>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionId, 
                                            videoHash,
                                            title,
                                            ( "<year>%s</year>" % year, "<year xsi:nil=\"true\" />" ) [ year == "" ],
		( "<season>%s</season>" % season, "<season xsi:nil=\"true\" />" ) [ season == "" ],                                                  
		( "<episode>%s</episode>" % episode, "<episode xsi:nil=\"true\" />" ) [ episode == "" ],
		  "<SubtitleLanguage>%s</SubtitleLanguage>" % language1,
                                            ( "<SubtitleLanguage>%s</SubtitleLanguage>" % language2, "" ) [ language2 == "None" ],
                                            ( "<SubtitleLanguage>%s</SubtitleLanguage>" % language3, "" ) [ language3 == "None" ] )
    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.SEARCH_SUBTITLES_ACTION, requestXML)
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils() 
    result    = xmlUtils.getText(resultDoc, "SearchSubtitles3Result")
    subtitles = []      
    if (result == "true") :
      # Releases...
      releases = dict()
      releaseNodes = resultDoc.getElementsByTagName("Release")
      if releaseNodes != None :
        for releaseNode in releaseNodes :
          subtitleID  = xmlUtils.getText( releaseNode, "SubtitleID" )
          releaseName = xmlUtils.getText( releaseNode, "Name" )
          if releaseName > "" :
            releases[ subtitleID ] = releaseName
      # Subtitles...
      subtitleNodes = resultDoc.getElementsByTagName("Subtitle")
      for subtitleNode in subtitleNodes:
        title         = xmlUtils.getText( subtitleNode, "Title" )
        year          = xmlUtils.getText( subtitleNode, "Year" )
        try:
          release     = releases.get( subtitleID, ("%s (%s)" % ( title, year  ) ) )
        except :
          release     = "%s (%s)" % ( title, year )
        language      = xmlUtils.getText( subtitleNode, "Language" )
        subtitleID    = xmlUtils.getText( subtitleNode, "SubtitleID" )
        mediaType     = xmlUtils.getText( subtitleNode, "MediaType" )
        numberOfDiscs = xmlUtils.getText( subtitleNode, "NumberOfDiscs" ) 
        downloads     = xmlUtils.getText( subtitleNode, "Downloads" )
        isLinked      = xmlUtils.getText( subtitleNode, "IsLinked" )
        rate          = float(xmlUtils.getText( subtitleNode, "Rate" ))
        
        if language == "SerbianLatin": language = "Serbian"
        
        if isLinked == "true":
          linked = True
        else:
          linked = False    
        
        if len(language) > 1:
          flag_image = "flags/%s.gif" % (languageTranslate(language,0,2))
        else:                                                           
          flag_image = "-.gif"              

        subtitles.append( { "title"         : title,
                            "year"          : year,
                            "filename"      : release,
                            "language_name" : language,
                            "ID"            : subtitleID,
                            "mediaType"     : mediaType,
                            "numberOfDiscs" : numberOfDiscs,
                            "downloads"     : downloads,
                            "sync"          : linked,
                            "rating"        : str(int(round(rate*2))),
                            "language_flag" :flag_image
                            } )            
    
    # Return value
    return subtitles       
  
  #
  # GetDownloadTicket
  #
  def GetDownloadTicket(self, sessionID, subtitleID):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <GetDownloadTicket2 xmlns="http://www.sublight.si/">
                          <session>%s</session>
                          <id>%s</id>
                        </GetDownloadTicket2>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionID, subtitleID )
                    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.GET_DOWNLOAD_TICKET_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "GetDownloadTicket2Result" )
    
    ticket = ""
    if result == "true" :
      ticket  = xmlUtils.getText( resultDoc, "ticket" )
      que     = xmlUtils.getText( resultDoc, "que" )
        
    # Return value
    return ticket, que
  
  #
  # DownloadByID4 
  #
  def DownloadByID(self, sessionID, subtitleID, ticketID):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <DownloadByID4 xmlns="http://www.sublight.si/">
                          <sessionID>%s</sessionID>
                          <subtitleID>%s</subtitleID>
                          <codePage>1250</codePage>
                          <removeFormatting>false</removeFormatting>
                          <ticket>%s</ticket>
                        </DownloadByID4>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionID, subtitleID, ticketID )

    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.DOWNLOAD_BY_ID_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "DownloadByID4Result" )
    
    base64_data = ""
    if result == "true" :
      base64_data = xmlUtils.getText( resultDoc, "data" )
    
    # Return value
    return base64_data
        
#
#
#
class XmlUtils :
  def getText (self, nodeParent, childName ):
    # Get child node...
    node = nodeParent.getElementsByTagName( childName )[0]
    
    if node == None :
      return None
    
    # Get child text...
    text = ""
    for child in node.childNodes:
      if child.nodeType == child.TEXT_NODE :
        text = text + child.data
    return text

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import mechanize
from utilities import log
_ = sys.modules[ "__main__" ].__language__

movie_url = "http://www.small-industry.com"
tvshow_url = "http://www.subs4series.com"
debug_pretext = "subs4free"

def get_url(url,referer=None):
    if referer is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'}
    else:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 'Referer' : referer}
    req = urllib2.Request(url,None,headers)
    response = urllib2.urlopen(req)
    content = response.read()
    response.close()
    content = content.replace('\n','')
    return content

def get_rating(downloads):
    rating = int(downloads)
    if (rating < 50):
        rating = 1
    elif (rating >= 50 and rating < 100):
        rating = 2
    elif (rating >= 100 and rating < 150):
        rating = 3
    elif (rating >= 150 and rating < 200):
        rating = 4
    elif (rating >= 200 and rating < 250):
        rating = 5
    elif (rating >= 250 and rating < 300):
        rating = 6
    elif (rating >= 300 and rating < 350):
        rating = 7
    elif (rating >= 350 and rating < 400):
        rating = 8
    elif (rating >= 400 and rating < 450):
        rating = 9
    elif (rating >= 450):
        rating = 10
    return rating

def unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder):
    subs_file = ""
    files = os.listdir(tmp_sub_dir)
    init_filecount = len(files)
    max_mtime = 0
    filecount = init_filecount
    # determine the newest file from tmp_sub_dir
    for file in files:
        if (string.split(file,'.')[-1] in ['srt','sub','txt']):
            mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
            if mtime > max_mtime:
                max_mtime =  mtime
    init_max_mtime = max_mtime
    time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
    xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
    waittime  = 0
    while (filecount == init_filecount) and (waittime < 10) and (init_max_mtime == max_mtime): # nothing yet extracted
        time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
        files = os.listdir(tmp_sub_dir)
        filecount = len(files)
        # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                if (mtime > max_mtime):
                    max_mtime =  mtime
        waittime  = waittime + 1
    if waittime == 10:
        log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
        pass
    else:
        log( __name__ ," Unpacked files in '%s'" % (tmp_sub_dir))
        pass
        for file in files:
            # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
            if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                log( __name__ ," Unpacked subtitles file '%s'" % (file))
                subs_file = os.path.join(tmp_sub_dir, file)
    return subs_file

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
    subtitles_list = []
    msg = ""

    if not (string.lower(lang1) or string.lower(lang2) or string.lower(lang3)) == "greek":
        msg = "Won't work, subs4free is only for Greek subtitles."
        return subtitles_list, "", msg #standard output

    try:
        log( __name__ ,"%s Clean title = %s" % (debug_pretext, title))
        premiered = year
        title, year = xbmc.getCleanMovieTitle( title )
    except:
        pass

    content = 1
    if len(tvshow) == 0: # Movie
        searchstring = "%s (%s)" % (title, premiered)
    elif len(tvshow) > 0 and title == tvshow: # Movie not in Library
        searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
    elif len(tvshow) > 0: # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        content = 2
    else:
        searchstring = title

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))
    if content == 1:
        get_movie_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    else:
        get_tvshow_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    return subtitles_list, "", msg #standard output

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ""
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    name = subtitles_list[pos][ "filename" ]
    name = name.replace('.',' ')

    # Browser
    browser = mechanize.Browser()
    browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0')]
    browser.addheaders = [('Referer', id)]

    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, id))
        response = browser.open(id)
        content = response.read()
        log( __name__ ,"%s Getting subtitle link" % (debug_pretext))
        try:
            subtitle_id = re.compile('href="(getSub-.+?)"').findall(content.replace('\n',''))[1] # movie_url
        except:
            pass
        try:
            subtitle_id = re.compile('href="(/getSub-.+?)"').findall(content.replace('\n',''))[1] # tvshow_url
        except:
            pass
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, subtitle_id))
        response = browser.open(subtitle_id)
        content = response.read()
        type = response.info()["Content-type"]
    except:
        log( __name__ ,"%s Failed to parse url:%s" % (debug_pretext, id))
        return False, language, subs_file #standard output

    if type == 'application/x-rar-compressed':
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.rar")
        redirect = False
        packed = True
    elif type == 'application/zip':
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.zip")
        redirect = False
        packed = True
    elif not type.startswith('text/html'):
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.srt") # assume unpacked subtitels file is an '.srt'
        subs_file = local_tmp_file
        redirect = False
        packed = False
    else:
        redirect = True

    if redirect is False:
        try:
            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
            if packed:
                subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
            pass
    else:
        try:
            log( __name__ ,"%s Getting subtitles by subz.tv" % (debug_pretext))
            subtitles = re.compile("(<li style='margin-bottom.+?</li>)").findall(content.replace('\n',''))
            for subtitle in subtitles:
                try:
                    try:
                        subz = re.compile("<span.+?>(.+?)</span>.+?</b>").findall(subtitle)[0]
                        subz = subz.replace('.',' ')
                    except:
                        subz = ''
                        pass
                    id = re.compile("<a href='(.+?)'").findall(subtitle)[0]
                    id = id.replace('amp;','')
                    id = 'http://www.subz.tv/infusions/pro_download_panel/%s&dlok=on' % (id)
                    if re.search(subz,name) is not None:
                        response = browser.open(id)
                        content = response.read()
                        try:
                            local_tmp_file = os.path.join(tmp_sub_dir, "subztv.rar")
                            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
                            local_file_handle = open(local_tmp_file, "wb")
                            local_file_handle.write(content)
                            local_file_handle.close()
                            subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
                            if subs_file == "":
                                local_tmp_file2 = os.path.join(tmp_sub_dir, "subztv.srt")
                                os.rename(local_tmp_file, local_tmp_file2)
                                subs_file = local_tmp_file2
                        except:
                            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
                            pass
                        break
                except:
                    pass
        except:
            log( __name__ ,"%s Failed to get subtitles by subz.tv" % (debug_pretext))
            pass

    return False, language, subs_file #standard output

def get_movie_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search_report.php?search=%s&x=14&y=11&searchType=1' % (movie_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=movie_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(/el.gif" alt="Greek".+?</B>DLs)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('<B>(.+?)</B>').findall(subtitle)[0]
            id = re.compile('href="link.php[?]p=(.+?)"').findall(subtitle)[0]
            id = '%s/%s' % (movie_url, id)
            try:
                uploader = re.compile('<B>(.+?)</B>').findall(subtitle)[1]
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('<B>(.+?)</B>').findall(subtitle)[-1]
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

def get_tvshow_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search_report.php?search=%s&x=14&y=11&searchType=1' % (tvshow_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=tvshow_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(/el.gif" alt="Greek".+?</B>DLs)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('<B>(.+?)</B>').findall(subtitle)[0]
            id = re.compile('<a href="(.+?)"').findall(subtitle)[0]
            id = '%s%s' % (tvshow_url, id)
            try:
                uploader = re.compile('<B>(.+?)</B>').findall(subtitle)[1]
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('<B>(.+?)</B>').findall(subtitle)[-1]
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import difflib
from utilities import languageTranslate, log

main_url = "http://subscene.com/"
debug_pretext = ""

# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth", "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
    <td class="a1">
                <a href="/subtitles/iron-man-3/english/772801">
                    <div class="visited">
                    <span class="l r neutral-icon">
                        English
                    </span>
                    <span>
                        Iron.Man.3.2013.720p.WEB-DL.H264-WEBiOS [PublicHD] 
                    </span>
                    </div>
                </a>
            </td>
            <td class="a3">
                1
            </td>
            <td class="a41">
                &nbsp;
            </td>
            <td class="a5">

            <a href="/u/781496">
                Aakiful Islam
            </a>
            </td>
            <td class="a6">
                <div>
                    Hearing Impaired. Suits all the WEB-DL Releases.&nbsp;
                </div>
            </td>
"""

subtitle_pattern = "<a href=\"(/subtitles/[^\"]+)\">\s+<div class=\"visited\">\s+<span class=\"[^\"]+ (\w+-icon)\">\s+([^\r\n\t]+)\s+</span>\s+\
<span>\s+([^\r\n\t]+)\s+</span>\s+</div>\s+</a>\s+</td>\s+<td class=\"[^\"]+\">\s+[^\r\n\t]+\s+</td>\s+<td class=\"([^\"]+)\">"
# group(1) = downloadlink, group(2) = qualitycode, group(3) = language, group(4) = filename, group(5) = hearing impaired

# movie/seasonfound pattern example:
"""
    <div class="title">
        <a href="/subtitles/the-big-bang-theory-fifth-season-2011">The Big Bang Theory - Fifth Season (2011)</a>
    </div>
    <div class="subtle">

        547 subtitles
    </div>

"""
movie_season_pattern = "<a href=\"(/subtitles/[^\"]*)\">([^<]+)\((\d{4})\)</a>\s+</div>\s+<div class=\"subtle\">\s+(\d+)"
# group(1) = link, group(2) = movie_season_title,  group(3) = year, group(4) = num subtitles




# download link pattern example:
"""
        <a href="/subtitle/download?mac=LxawhQiaMYm9O2AsoNMHXbXDYN2b4yBreI8TJIBfpdw7UIo1JP5566Sbb2ei_zUC0" rel="nofollow" onclick="DownloadSubtitle(this)" id="downloadButton" class="button Positive">
"""
downloadlink_pattern = "...<a href=\"(.+?)\" rel=\"nofollow\" onclick=\"DownloadSubtitle"
# group(1) = link

# <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="/wEPDwUKLTk1MDk4NjQwM2Rk5ncGq+1a601mEFQDA9lqLwfzjaY=" />
viewstate_pattern = "<input type=\"hidden\" name=\"__VIEWSTATE\" id=\"__VIEWSTATE\" value=\"([^\n\r\t]*?)\" />"

# <input type="hidden" name="__PREVIOUSPAGE" id="__PREVIOUSPAGE" value="V1Stm1vgLeLd6Kbt-zkC8w2" />
previouspage_pattern = "<input type=\"hidden\" name=\"__PREVIOUSPAGE\" id=\"__PREVIOUSPAGE\" value=\"([^\n\r\t]*?)\" />"

# <input type="hidden" name="subtitleId" id="subtitleId" value="329405" />
subtitleid_pattern = "<input type=\"hidden\" name=\"subtitleId\" id=\"subtitleId\" value=\"(\d+?)\" />"

# <input type="hidden" name="typeId" value="zip" />
typeid_pattern = "<input type=\"hidden\" name=\"typeId\" value=\"([^\n\r\t]{3,15})\" />"

# <input type="hidden" name="filmId" value="78774" />
filmid_pattern = "<input type=\"hidden\" name=\"filmId\" value=\"(\d+?)\" />"


#====================================================================================================================
# Functions
#====================================================================================================================

def to_subscene_lang(language):
    if language == "Chinese":            return "Chinese BG code"
    elif language == "PortugueseBrazil": return "Brazillian Portuguese"
    elif language == "SerbianLatin":     return "Serbian"
    elif language == "Ukrainian":        return "Ukranian"
    else:                                return language



def find_movie(content, title, year):
    url_found = None
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        log( __name__ ,"%s Found movie on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)))
        if string.find(string.lower(matches.group(2)),string.lower(title)) > -1:
            if matches.group(3) == year:
                log( __name__ ,"%s Matching movie found on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)))
                url_found = matches.group(1)
                break
    return url_found


def find_tv_show_season(content, tvshow, season):
    url_found = None
    possible_matches = []
    all_tvshows = []

    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        #log( __name__ ,"%s Found tv show season on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
        s = difflib.SequenceMatcher(None, string.lower(matches.group(2) + ' ' + matches.group(3)), string.lower(tvshow))
        all_tvshows.append(matches.groups() + (s.ratio() * int(matches.group(4)),))

        if string.find(string.lower(matches.group(2)),string.lower(tvshow) + " ") > -1:
            if string.find(string.lower(matches.group(2)),string.lower(season)) > -1:
                log( __name__ ,"%s Matching tv show season found on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
                possible_matches.append(matches.groups())

    if len(possible_matches) > 0:
        possible_matches = sorted(possible_matches, key=lambda x: -int(x[3]))
        url_found = possible_matches[0][0]
        log( __name__ ,"%s Selecting matching tv show with most subtitles: %s (%s)" % (debug_pretext, possible_matches[0][1].decode("utf-8"), possible_matches[0][3].decode("utf-8")))
    else:
        if len(all_tvshows) > 0:
            all_tvshows = sorted(all_tvshows, key=lambda x: -int(x[4]))
            url_found = all_tvshows[0][0]
            log( __name__ ,"%s Selecting tv show with highest fuzzy string score: %s (score: %s subtitles: %s)" % (debug_pretext, all_tvshows[0][1].decode("utf-8"), all_tvshows[0][4], all_tvshows[0][3].decode("utf-8")))

    return url_found


def getallsubs(response_url, content, language, title, subtitles_list, search_string):
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        languagefound = matches.group(3)
        if languagefound == to_subscene_lang(language):
            link = main_url + matches.group(1)
            languageshort = languageTranslate(language,0,2)
            filename   = matches.group(4)
            hearing_imp = (matches.group(5) == "a41")
            rating = '0'
            if matches.group(2) == "bad-icon":
                continue
            if matches.group(2) == "positive-icon":
                rating = '5'
            if search_string != "":
                log( __name__ , "string.lower(filename) = >" + string.lower(filename) + "<" )
                log( __name__ , "string.lower(search_string) = >" + string.lower(search_string) + "<" )
                if string.find(string.lower(filename),string.lower(search_string)) > -1:
                    log( __name__ ,"%s Subtitles found: %s, %s" % (debug_pretext, languagefound, filename))
                    subtitles_list.append({'rating': rating, 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language, 'hearing_imp': hearing_imp})
            else:
                log( __name__ ,"%s Subtitles found: %s, %s" % (debug_pretext, languagefound, filename))
                subtitles_list.append({'rating': rating, 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language, 'hearing_imp': hearing_imp})


def geturl(url):
    log( __name__ ,"%s Getting url:%s" % (debug_pretext, url))
    try:
        response   = urllib2.urlopen(url)
        content    = response.read()
        #Fix non-unicode charachters in movie titles
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        content    = strip_unicode.sub('', content)
        return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
        return_url = None
    return(content, return_url)


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    log( __name__ ,"%s Search_subtitles = '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'" % 
         (debug_pretext, file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack))
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        search_string = title
    if len(tvshow) > 0:
        tvshow = string.strip(tvshow)
        search_string = tvshow + " - " + seasons[int(season)] + " Season"
    log( __name__ ,"%s Search string = %s" % (debug_pretext, search_string))
    url = main_url + "/subtitles/title?q=" + urllib.quote_plus(search_string)
    content, response_url = geturl(url)
    if content is not None:
        if re.search("subtitles-\d{2,10}\.aspx", response_url, re.IGNORECASE):
            log( __name__ ,"%s One movie found, getting subs ..." % debug_pretext)
            getallsubs(response_url, content, lang1, title, subtitles_list,  "")
            if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
            if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
        else:
            if len(tvshow) == 0:
                log( __name__ ,"%s Multiple movies found, searching for the right one ..." % debug_pretext)
                subspage_url = find_movie(content, title, year)
                if subspage_url is not None:
                    log( __name__ ,"%s Movie found in list, getting subs ..." % debug_pretext)
                    url = main_url + subspage_url
                    content, response_url = geturl(url)
                    if content is not None:
                        getallsubs(response_url, content, lang1, title, subtitles_list, "")
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                else:
                    log( __name__ ,"%s Movie not found in list: %s" % (debug_pretext, title))
                    if string.find(string.lower(title),"&") > -1:
                        title = string.replace(title, "&", "and")
                        log( __name__ ,"%s Trying searching with replacing '&' to 'and': %s" % (debug_pretext, title))
                        subspage_url = find_movie(content, title, year)
                        if subspage_url is not None:
                            log( __name__ ,"%s Movie found in list, getting subs ..." % debug_pretext)
                            url = main_url + subspage_url
                            content, response_url = geturl(url)
                            if content is not None:
                                getallsubs(response_url, content, lang1, title, subtitles_list, "")
                                if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                                if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                        else:
                            log( __name__ ,"%s Movie not found in list: %s" % (debug_pretext, title))
            if len(tvshow) > 0:
                log( __name__ ,"%s Multiple tv show seasons found, searching for the right one ..." % debug_pretext)
                tv_show_seasonurl = find_tv_show_season(content, tvshow, seasons[int(season)])
                if tv_show_seasonurl is not None:
                    log( __name__ ,"%s Tv show season found in list, getting subs ..." % debug_pretext)
                    url = main_url + tv_show_seasonurl
                    content, response_url = geturl(url)
                    if content is not None:
                        search_string = "s%#02de%#02d" % (int(season), int(episode))
                        getallsubs(response_url, content, lang1, title, subtitles_list, search_string)
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, search_string)
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, search_string)


    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url = subtitles_list[pos][ "link" ]
    language = subtitles_list[pos][ "language_name" ]
    content, response_url = geturl(url)
    match=  re.compile(downloadlink_pattern).findall(content)
    if match:
        downloadlink = "http://subscene.com"  + match[0]
        log( __name__ ,"%s Downloadlink: %s " % (debug_pretext, downloadlink))
        viewstate = 0
        previouspage = 0
        subtitleid = 0
        typeid = "zip"
        filmid = 0
        postparams = urllib.urlencode( { '__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '' , '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid} )
        class MyOpener(urllib.FancyURLopener):
            version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
        my_urlopener = MyOpener()
        my_urlopener.addheader('Referer', url)
        log( __name__ ,"%s Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, url, postparams))
        response = my_urlopener.open(downloadlink, postparams)
        local_tmp_file = os.path.join(tmp_sub_dir, "subscene.xxx")
        try:
            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            if not os.path.exists(tmp_sub_dir):
                os.makedirs(tmp_sub_dir)
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
            #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
            myfile = open(local_tmp_file, "rb")
            myfile.seek(0)
            if (myfile.read(1) == 'R'):
                typeid = "rar"
                packed = True
                log( __name__ , "Discovered RAR Archive")
            else:
                myfile.seek(0)
                if (myfile.read(1) == 'P'):
                    typeid = "zip"
                    packed = True
                    log( __name__ , "Discovered ZIP Archive")
                else:
                    typeid = "srt"
                    packed = False
                    subs_file = local_tmp_file
                    log( __name__ , "Discovered a non-archive file")
            myfile.close()
            local_tmp_file = os.path.join(tmp_sub_dir, "subscene." + typeid)
            os.rename(os.path.join(tmp_sub_dir, "subscene.xxx"), local_tmp_file)
            log( __name__ , "%s Saving to %s" % (debug_pretext,local_tmp_file))
        except:
            log( __name__ ,"%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
        if packed:
            files_before = os.listdir(tmp_sub_dir)
            filecount = init_filecount = len(files_before)
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            files_after = os.listdir(tmp_sub_dir)
            filecount = len(files_after)
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 200):
                files_after = os.listdir(tmp_sub_dir)
                filecount = len(files_after)
                waittime  = waittime + 1
                log( __name__ ,"%s Wait time is '%s'" % (debug_pretext, waittime))
                time.sleep(0.1)  # wait 0.1 second to let the builtin function 'XBMC.extract' unpack
            if waittime == 200:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for new_file in set(files_after) - set(files_before):
                    if string.split(new_file, '.')[-1] in ['srt', 'sub', 'txt']:
                        subs_file = os.path.join(tmp_sub_dir, new_file)
                        break
        log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

#===============================================================================
# Subscenter.org subtitles service.
# Version: 2.5
#
# Change log:
# 1.1 - Fixed downloading of non-Hebrew subtitles.
# 1.2 - Added key field for download URL
# 1.3 - Fixed null values in website dictionary (changed to None)
# 1.4 - Fixed key field (Thanks ILRHAES)
# 1.5 - Added User Agent to getURL, fixed string related bugs and patterns
# 1.5.5 - Bug Fix for (1.5)
# 2.0 - Added rating algorithem 
#       Added supports downloading IDX\SUBS from sendspace.compile
#       Added sync icon added to files with rating>8
#       Added sorted subtitlelist by rating
# 2.0.1 - Bug fix
# 2.5 - support for Subscenter new website + workaround (10x to CaTz)
#
# Created by: Ori Varon
# Changed by: MeatHook (1.5)
# Changed by: Maor Tal 21/01/2014 (1.5.5, 2.0, 2.5)
#===============================================================================
import os, re, xbmc, xbmcgui, string, time, urllib2
from utilities import languageTranslate, log

BASE_URL = "http://www.subscenter.org"
USER_AGENT = "Mozilla%2F4.0%20(compatible%3B%20MSIE%207.0%3B%20Windows%20NT%206.0)"
debug_pretext = ""

#===============================================================================
# Regular expression patterns
#===============================================================================

MULTI_RESULTS_PAGE_PATTERN = u"עמוד (?P<curr_page>\d*) \( סך הכל: (?P<total_pages>\d*) \)"
MOVIES_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/movie/.*?)">.*?<div class="generalWindowBottom">'
TV_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/series/.*?)">.*?<div class="generalWindowBottom">'
releases_types   = ['2011','2009','2012','2010','2013','2014','web-dl', 'webrip', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'ac3', 'aac', 'hdtv', 'dvdscr' ,'dvdrip', 'ac3', 'brrip', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

#===============================================================================
# Private utility functions
#===============================================================================

# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):
    # Fix URLs with spaces in them

    url = url.replace(" ","%20")
    content = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_unredirected_header('User-Agent', USER_AGENT)
        response = urllib2.urlopen(req)        
        content = response.read()
    except:
        log( __name__ ,"Failed to get url: %s" % (url))
    # Second parameter is the filename
    return content

def getURLfilename(url):
    # Fix URLs with spaces in them

    url = url.replace(" ","%20")
    filename = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_unredirected_header('User-Agent', USER_AGENT)
        response = urllib2.urlopen(req)        
        content = response.read()
        filename = response.headers['Content-Disposition']
        filename = filename[filename.index("filename="):]
    except:
        log( __name__ ,"Failed to get url: %s" % (url))
    # Second parameter is the filename
    return filename
    
def getrating(subsfile, videofile):
    x=0
    rating = 0
    log(__name__ ,"# Comparing Releases:\n %s [subtitle-rls] \n %s  [filename-rls]" % (subsfile,videofile))
    videofile = "".join(videofile.split('.')[:-1]).lower()
    subsfile = subsfile.lower().replace('.', '')
    videofile = videofile.replace('.', '')
    for release_type in releases_types:
        if (release_type in videofile):
            x+=1
            if (release_type in subsfile): rating += 1
    if(x): rating=(rating/float(x))*4
    # Compare group name
    if videofile.split('-')[-1] == subsfile.split('-')[-1] : rating += 1
    # Group name didnt match 
    # try to see if group name is in the beginning (less info on file less weight)
    elif videofile.split('-')[0] == subsfile.split('-')[-1] : rating += 0.5
    if rating > 0:
        rating = rating * 2
    log(__name__ ,"# Result is:  %f" % rating)
    return round(rating)
    
# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(subtitlePageID,languageList,fname):
    # Retrieve the subtitles page (html)
    subs= []
    try:
        subtitlePage = getURL(BASE_URL + subtitlePageID)
    except:
        # Didn't find the page - no such episode?
        return
    # Didn't find the page - no such episode?
    if (not subtitlePage):
        return
    # Find subtitles dictionary declaration on page
    toExec = "foundSubtitles = " + subtitlePage
    # Remove junk at the end of the line
    toExec = toExec[:toExec.rfind("}")+1]
    # Replace "null" with "None"
    toExec = toExec.replace("null","None")
    exec(toExec) in globals(), locals()
    log( __name__ ,"Built webpage dictionary")
    for language in foundSubtitles.keys():
        if (languageTranslate(language, 2, 0) in languageList): 
            for translator in foundSubtitles[language]:
                for quality in foundSubtitles[language][translator]:
                    for rating in foundSubtitles[language][translator][quality]:
                        title=foundSubtitles[language][translator][quality][rating]["subtitle_version"]
                        Srating=getrating(title,fname)
                        subs.append({'rating': str(Srating), 'sync': Srating>=8,
                            'filename': title,
                            'subtitle_id': foundSubtitles[language][translator][quality][rating]["id"],
                            'language_flag': 'flags/' + language + '.gif',
                            'language_name': languageTranslate(language, 2, 0),
                            'key': foundSubtitles[language][translator][quality][rating]["key"],
                            'notes': re.search('http://www\.sendspace\.com/file/\w+$',foundSubtitles[language][translator][quality][rating]["notes"])})
    # sort, to put syncs on top
    return sorted(subs,key=lambda x: int(float(x['rating'])),reverse=True)

# Extracts the downloaded file and find a new sub/srt file to return.
# Note that Sratim.co.il currently isn't hosting subtitles in .txt format but
# is adding txt info files in their zips, hence not looking for txt.
# Based on Titlovi's service.py
def extractAndFindSub(tempSubDir,tempZipFile):
    # Remember the files currently in the folder and their number
    files = os.listdir(tempSubDir)
    init_filecount = len(files)
    filecount = init_filecount
    max_mtime = 0
    # Determine which is the newest subtitles file in tempSubDir
    for file in files:
        if (string.split(file,'.')[-1] in ['srt','sub']):
            mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
            if mtime > max_mtime:
                max_mtime =  mtime
    init_max_mtime = max_mtime
    # Wait 2 seconds so that the unpacked files are at least 1 second newer
    time.sleep(2)
    # Use XBMC's built-in extractor
    xbmc.executebuiltin("XBMC.Extract(" + tempZipFile + "," + tempSubDir +")")
    waittime  = 0
    while ((filecount == init_filecount) and (waittime < 20) and
           (init_max_mtime == max_mtime)): # Nothing extracted yet
        # Wait 1 second to let the builtin function 'XBMC.extract' unpack
        time.sleep(1)  
        files = os.listdir(tempSubDir)
        filecount = len(files)
        # Determine if there is a newer file created in tempSubDir
        # (indicates that the extraction had completed)
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
                mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
                if (mtime > max_mtime):
                    max_mtime =  mtime
        waittime  = waittime + 1
    if waittime == 20:
        log( __name__ ,"Failed to unpack subtitles in '%s'" % (tempSubDir))
        return ""
    else:
        log( __name__ ,"Unpacked files in '%s'" % (tempSubDir))        
        for file in files:
            # There could be more subtitle files in tempSubDir, so make sure we
            # get the newest subtitle file
            if ((string.split(file, '.')[-1] in ['srt', 'sub']) and
                (os.stat(os.path.join(tempSubDir, file)).st_mtime >
                 init_max_mtime)):
                log( __name__ ,"Unpacked subtitles file '%s'" % (file))        
                return os.path.join(tempSubDir, file)

#===============================================================================
# Public interface functions
#===============================================================================

# This function is called when the service is selected through the subtitles
# addon OSD.
# file_original_path -> Original system path of the file playing
# title -> Title of the movie or episode name
# tvshow -> Name of a tv show. Empty if video isn't a tv show (as are season and
#           episode)
# year -> Year
# season -> Season number
# episode -> Episode number
# set_temp -> True iff video is http:// stream
# rar -> True iff video is inside a rar archive
# lang1, lang2, lang3 -> Languages selected by the user
def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitlesList = []
    # List of user languages - easier to manipulate
    languageList = [lang1, lang2, lang3]
    msg = ""

    # Check if tvshow and replace spaces with + in either case
    if tvshow:
        searchString = re.split(r'\s\(\w+\)$',tvshow)[0].replace(" ","+")
    else:
        searchString = title.replace(" ","+")

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchString.lower()))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Search timed out, please try again later."

    # Look for subtitles page links
    if tvshow:
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
    else:
        subtitleIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)    
    
    # Look for more subtitle pages
    pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
    # If we found them look inside for subtitles page links
    if (pages):
        while (not (int(pages.group("curr_page"))) == int(pages.group("total_pages"))):
            searchResults = getURL(BASE_URL + "/he/subtitle/search/?q="+searchString.lower()+"&page="+str(int(pages.group("curr_page"))+1))

            if tvshow:
                tempSIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
            else:
                tempSIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)



            for sid in tempSIDs:
                subtitleIDs.append(sid)
            pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
    # Uniqify the list
    subtitleIDs=list(set(subtitleIDs))
    # If looking for tvshos try to append season and episode to url

    for i in range(len(subtitleIDs)):
        subtitleIDs[i] = subtitleIDs[i].replace("/subtitle/","/cinemast/data/")
        if (tvshow):
            subtitleIDs[i]=subtitleIDs[i].replace("/series/","/series/sb/")
            subtitleIDs[i] += season+"/"+episode+"/"
        else:
            subtitleIDs[i]=subtitleIDs[i].replace("/movie/","/movie/sb/")
             

    for sid in subtitleIDs:
        tmp = getAllSubtitles(sid,languageList,os.path.basename(file_original_path))
        subtitlesList=subtitlesList + ((tmp) if tmp else [])
    
    
    # Standard output -
    # subtitles list (list of tuples built in getAllSubtitles),
    # session id (e.g a cookie string, passed on to download_subtitles),
    # message to print back to the user
    return subtitlesList, "", msg

# This function is called when a specific subtitle from the list generated by
# search_subtitles() is selected in the subtitles addon OSD.
# subtitles_list -> Same list returned in search function
# pos -> The selected item's number in subtitles_list
# zip_subs -> Full path of zipsubs.zip located in tmp location, if automatic
# extraction is used (see return values for details)
# tmp_sub_dir -> Temp folder used for both automatic and manual extraction
# sub_folder -> Folder where the sub will be saved
# session_id -> Same session_id returned in search function
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subtitle_id = subtitles_list[pos][ "subtitle_id" ]
    filename = subtitles_list[pos][ "filename" ]
    key = subtitles_list[pos][ "key" ]
    # check if need to download subtitle from sendspace
    if(subtitles_list[pos]["notes"]):
        # log to sendspace
        content = getURL(subtitles_list[pos]["notes"].group())
        # find download link
        url = re.search(r'<a id="download_button" href?="(.+sendspace.+\.\w\w\w)" ', content)
        content = None
        if (url):
            url = url.group(1)
            log( __name__ ,"%s Fetching subtitles from sendspace.com using url %s" % (debug_pretext, url))
            content = getURL(url)
            archive_name = "rarsubs" + re.search(r'\.\w\w\w$',url).group(0)
    else:
        url = BASE_URL + "/" + languageTranslate(subtitles_list[pos][ "language_name" ], 0, 2)+"/subtitle/download/"+languageTranslate(subtitles_list[pos][ "language_name" ], 0, 2)+"/"+str(subtitle_id)+"/?v="+filename+"&key="+key
        log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
        # Get the intended filename (don't know if it's zip or rar)
        archive_name = getURLfilename(url)
        # Get the file content using geturl()
        content = getURL(url)
    subs_file = ""
    if content:
        local_tmp_file = os.path.join(tmp_sub_dir, archive_name)
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))

        # Extract the zip file and find the new sub/srt file
        subs_file = extractAndFindSub(tmp_sub_dir,local_tmp_file)
            
    # Standard output -
    # True iff the file is packed as zip: addon will automatically unpack it.
    # language of subtitles,
    # Name of subtitles file if not packed (or if we unpacked it ourselves)
    return False, subtitles_list[pos][ "language_name" ], subs_file

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import shutil

from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.subtitles.gr"
debug_pretext = "subtitles.gr"

def get_url(url,referer=None):
    if referer is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'}
    else:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 'Referer' : referer}
    req = urllib2.Request(url,None,headers)
    response = urllib2.urlopen(req)
    content = response.read()
    response.close()
    content = content.replace('\n','')
    return content

def get_rating(downloads):
    rating = int(downloads)
    if (rating < 50):
        rating = 1
    elif (rating >= 50 and rating < 100):
        rating = 2
    elif (rating >= 100 and rating < 150):
        rating = 3
    elif (rating >= 150 and rating < 200):
        rating = 4
    elif (rating >= 200 and rating < 250):
        rating = 5
    elif (rating >= 250 and rating < 300):
        rating = 6
    elif (rating >= 300 and rating < 350):
        rating = 7
    elif (rating >= 350 and rating < 400):
        rating = 8
    elif (rating >= 400 and rating < 450):
        rating = 9
    elif (rating >= 450):
        rating = 10
    return rating

def unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder):
    subs_file = ""
    files = os.listdir(tmp_sub_dir)
    init_filecount = len(files)
    max_mtime = 0
    filecount = init_filecount
    # determine the newest file from tmp_sub_dir
    for file in files:
        if (string.split(file,'.')[-1] in ['srt','sub','txt']):
            mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
            if mtime > max_mtime:
                max_mtime =  mtime
    init_max_mtime = max_mtime
    time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
    xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
    waittime  = 0
    while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
        time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
        files = os.listdir(tmp_sub_dir)
        filecount = len(files)
        # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                if (mtime > max_mtime):
                    max_mtime =  mtime
        waittime  = waittime + 1
    if waittime == 20:
        log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
        pass
    else:
        log( __name__ ," Unpacked files in '%s'" % (tmp_sub_dir))
        pass
        for file in files:
            # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
            if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                log( __name__ ," Unpacked subtitles file '%s'" % (file))
                subs_file = os.path.join(tmp_sub_dir, file)
    return subs_file

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
    subtitles_list = []
    msg = ""

    if not (string.lower(lang1) or string.lower(lang2) or string.lower(lang3)) == "greek":
        msg = "Won't work, subtitles.gr is only for Greek subtitles."
        return subtitles_list, "", msg #standard output

    try:
        log( __name__ ,"%s Clean title = %s" % (debug_pretext, title))
        premiered = year
        title, year = xbmc.getCleanMovieTitle( title )
    except:
        pass

    if len(tvshow) == 0: # Movie
        searchstring = "%s (%s)" % (title, premiered)
    elif len(tvshow) > 0 and title == tvshow: # Movie not in Library
        searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
    elif len(tvshow) > 0: # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    else:
        searchstring = title

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))
    get_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    return subtitles_list, "", msg #standard output

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ""
    language = subtitles_list[pos][ "language_name" ]
    name = subtitles_list[pos][ "filename" ]
    id = subtitles_list[pos][ "id" ]
    id = re.compile('(.+?.+?)/').findall(id)[-1]
    id = 'http://www.findsubtitles.eu/getp.php?id=%s' % (id)

    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, id))
        response = urllib.urlopen(id)
        content = response.read()
        type = content[:4]
    except:
        log( __name__ ,"%s Failed to parse url:%s" % (debug_pretext, id))
        return True,language, "" #standard output

    if type == 'Rar!':
        local_tmp_file = os.path.join(tmp_sub_dir, "subtitlesgr.rar")
    elif type == 'PK':
        local_tmp_file = os.path.join(tmp_sub_dir, "subtitlesgr.zip")
    else:
        log( __name__ ,"%s Failed to get correct content type" % (debug_pretext))
        return True,language, "" #standard output

    try:
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(content)
        local_file_handle.close()

        log( __name__ ,"%s Extracting temp subtitles" % (debug_pretext))
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
        time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack

        log( __name__ ,"%s Cleaning temp directory:%s" % (debug_pretext, tmp_sub_dir))
        files = os.listdir(tmp_sub_dir)
        try:
            for file in files:
                file = os.path.join(tmp_sub_dir, file)
                os.remove(file)
        except:
            pass

        log( __name__ ,"%s Getting subtitles from extracted directory" % (debug_pretext))
        tmp_sub_extract_dir = os.path.join(tmp_sub_dir, "subs")
        files = os.listdir(tmp_sub_extract_dir)
        for file in files:
            local_tmp_extract_file = os.path.join(tmp_sub_extract_dir, file)
            local_tmp_file = os.path.join(tmp_sub_dir, file)
            if (file.endswith('.rar') or file.endswith('.zip')):
                shutil.copy(local_tmp_extract_file, tmp_sub_dir)
                subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
            elif (file.endswith('.srt') or file.endswith('.sub')):
                shutil.copy(local_tmp_extract_file, tmp_sub_dir)
                subs_file = local_tmp_file
    except:
        log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        pass

    return False, language, subs_file #standard output

def get_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search.php?name=%s&sort=downloads+desc' % (main_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=main_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(<img src=.+?flags/el.gif.+?</tr>)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('title = "(.+?)"').findall(subtitle)[0]
            filename = filename.split("subtitles for")[-1]
            filename = filename.strip()
            id = re.compile('href="(.+?)"').findall(subtitle)[0]
            try:
                uploader = re.compile('class="link_from">(.+?)</a>').findall(subtitle)[0]
                uploader = uploader.strip()
                if uploader == 'movieplace': uploader = 'GreekSubtitles'
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('class="latest_downloads">(.+?)</td>').findall(subtitle)[0]
                downloads = re.sub("\D", "", downloads)
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            if not (uploader == 'Εργαστήρι Υποτίτλων' or uploader == 'subs4series'):
                log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
                subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

# based on argenteam.net subtitles, based on a mod of Subdivx.com subtitles, based on a mod of Undertext subtitles
# developed by quillo86 and infinito for Subtitulos.es and XBMC.org
# little fixes and updates by tux_os

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log, languageTranslate

_ = sys.modules["__main__"].__language__


main_url = "http://www.subtitulos.es/"
debug_pretext = "subtitulos.es"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

subtitle_pattern1 = "<div id=\"version\" class=\"ssdiv\">(.+?)Versi&oacute;n(.+?)<span class=\"right traduccion\">(.+?)</div>(.+?)</div>"
subtitle_pattern2 = "<li class='li-idioma'>(.+?)<strong>(.+?)</strong>(.+?)<li class='li-estado (.+?)</li>(.+?)<span class='descargar (.+?)</span>"

#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode):

    if re.search(r'\([^)]*\)', tvshow):
        for level in range(4):
            searchstring, tvshow, season, episode = getsearchstring(tvshow, season, episode, level)
            url = main_url + searchstring.lower()
            getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode)
    else:
        searchstring, tvshow, season, episode = getsearchstring(tvshow, season, episode, 0)
        url = main_url + searchstring.lower()
        getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode)

def getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode):

    content = geturl(url)

    for matches in re.finditer(subtitle_pattern1, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
                filename = urllib.unquote_plus(matches.group(2))
                filename = re.sub(r' ', '.', filename)
                filename = re.sub(r'\s', '.', tvshow) + "." + season + "x" + episode + filename

                server = filename
                backup = filename
                subs = matches.group(4)

                for matches in re.finditer(subtitle_pattern2, subs, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
                        #log(__name__, "Descargas: %s" % (matches.group(2)))

                        idioma = matches.group(2)
                        idioma = re.sub(r'\xc3\xb1', 'n', idioma)
                        idioma = re.sub(r'\xc3\xa0', 'a', idioma)
                        idioma = re.sub(r'\xc3\xa9', 'e', idioma)

                        if idioma == "English":
                                languageshort = "en"
                                languagelong = "English"
                                filename = filename + ".(ENGLISH)"
                                server = filename
                        elif idioma == "Catala":
                                languageshort = "ca"
                                languagelong = "Catalan"
                                filename = filename + ".(CATALA)"
                                server = filename
                        elif idioma == "Espanol (Latinoamerica)":
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(LATINO)"
                                server = filename
                        elif idioma == "Galego":
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(GALEGO)"
                                server = filename
                        else:
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(ESPAÑA)"
                                server = filename

                        estado = matches.group(4)
                        estado = re.sub(r'\t', '', estado)
                        estado = re.sub(r'\n', '', estado)

                        id = matches.group(6)
                        id = re.sub(r'([^-]*)href="', '', id)
                        id = re.sub(r'" rel([^-]*)', '', id)
                        id = re.sub(r'" re([^-]*)', '', id)
                        id = re.sub(r'http://www.subtitulos.es/', '', id)

                        if estado.strip() == "green'>Completado".strip() and languagelong == langlong:
                                subtitles_list.append({'rating': "0", 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
                        
                        filename = backup
                        server = backup


def geturl(url):
        class AppURLopener(urllib.FancyURLopener):
                version = "App/1.7"
                def __init__(self, *args):
                        urllib.FancyURLopener.__init__(self, *args)
                def add_referrer(self, url=None):
                        if url:
                                urllib._urlopener.addheader('Referer', url)

        urllib._urlopener = AppURLopener()
        urllib._urlopener.add_referrer("http://www.subtitulos.es/")
        try:
                response = urllib._urlopener.open(url)
                content = response.read()
        except:
                #log(__name__, "%s Failed to get url:%s" % (debug_pretext, url))
                content = None
        return content

def getsearchstring(tvshow, season, episode, level):

    # Clean tv show name
    if level == 1 and re.search(r'\([^)][a-zA-Z]*\)', tvshow):
        # Series name like "Shameless (US)" -> "Shameless US"
        tvshow = tvshow.replace('(', '').replace(')', '')

    if level == 2 and re.search(r'\([^)][0-9]*\)', tvshow):
        # Series name like "Scandal (2012)" -> "Scandal"
        tvshow = re.sub(r'\s\([^)]*\)', '', tvshow)

    if level == 3 and re.search(r'\([^)]*\)', tvshow):
        # Series name like "Shameless (*)" -> "Shameless"
        tvshow = re.sub(r'\s\([^)]*\)', '', tvshow)

    # Zero pad episode
    episode = str(episode).rjust(2, '0')

    # Build search string
    searchstring = tvshow + '/' + season + 'x' + episode

    # Replace spaces with dashes
    searchstring = re.sub(r'\s', '-', searchstring)

    #log(__name__, "%s Search string = %s" % (debug_pretext, searchstring))
    return searchstring, tvshow, season, episode

def clean_subtitles_list(subtitles_list):
    seen = set()
    subs = []
    for sub in subtitles_list:
        filename = sub['filename']
        #log(__name__, "Filename: %s" % filename)
        if filename not in seen:
            subs.append(sub)
            seen.add(filename)
    return subs

def unique(seq):
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            yield item

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
    
    service_languages = ['Spanish', 'English', 'Catalan']
    config_languages = [lang1, lang2, lang3]
    subtitles_list = []
    msg = ""
    
    # Check if searching for tv show or movie
    if tvshow:
        if ((lang1 in service_languages) or (lang2 in service_languages) or (lang3 in service_languages)):
            
            config_languages[:] = unique(config_languages)
            
            for language in config_languages:
                getallsubs(languageTranslate(language, 0, 2), language, file_original_path, subtitles_list, tvshow, season, episode)
            
            subtitles_list = clean_subtitles_list(subtitles_list)
            
        else:
            msg = "Won't work, subtitulos.es is only for Spanish, English and Catalan subtitles!"
    else:
        msg = "Subtitulos.es is only for TV Shows subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos]["id"]
    server = subtitles_list[pos]["server"]
    language = subtitles_list[pos]["language_name"]

    url = "http://www.subtitulos.es/" + id

    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            #log(__name__, "%s subtitulos.es: el contenido es RAR" % (debug_pretext)) #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "subtituloses.rar")
            #log(__name__, "%s subtitulos.es: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "subtituloses.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "subtituloses.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log(__name__, "%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            #log(__name__, "%s subtitulos.es: escribo en %s" % (debug_pretext, local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            pass
            #log(__name__, "%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            #log(__name__, "%s subtitulos.es: número de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir + ")")
            waittime = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime = mtime
                waittime = waittime + 1
            if waittime == 20:
                log(__name__, "%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log(__name__, "%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log(__name__, "%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = service
# coding=iso-8859-2
import sys
import os
import os.path
import string
import urllib
import urllib2
import re
import time
import subutils
import subenv
from utilities import *

_ = sys.modules[ "__main__" ].__language__

base_urls = ["http://feliratok.info/"]
search_url_postfix = "?nyelv=&searchB=Mehet&search="

subtitle_pattern =                    '<tr[^>]*>\s*'
subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</table>\s*</td>\s*' # picture
subtitle_pattern = subtitle_pattern +    '<td[^>]*>\s*<small>(?P<lang>.*?)</small>\s*</td>\s*' # language
subtitle_pattern = subtitle_pattern +    '<td[^>]*onclick="adatlapnyitas\(\'(?P<id>[a-zA-Z_0-9]*)\'\)"[^>]*>\s*'   # onclick="adatlapnyitas\(\'(?P<id>[0-9]*?)\'\)"[^>]*
subtitle_pattern = subtitle_pattern +      '<div[^>]*>(?P<huntitle>.*?)</div>\s*' # hungarian title
subtitle_pattern = subtitle_pattern +      '<div[^>]*>(?P<origtitle>.*?)</div>\s*' # original title
subtitle_pattern = subtitle_pattern +    '</td>\s*'
subtitle_pattern = subtitle_pattern +    '<td[^>]*>(?P<uploader>.*?)</td>\s*' # uploader
subtitle_pattern = subtitle_pattern +    '<td[^>]*>(?P<date>.*?)</td>\s*' # date
subtitle_pattern = subtitle_pattern +    '<td[^>]*>\s*<a href="(?P<link1>.*?fnev=)(?P<link2>[^&"]*)(?P<link3>&[^"]*)?">.*?</a>\s*</td>\s*' # download link
subtitle_pattern = subtitle_pattern +  '</tr>'

#subtitle_pattern =                    '<tr[^>]*>\s*'
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # picture
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # language
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # titles
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # uploader
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # date
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # download link
#subtitle_pattern = subtitle_pattern +  '</tr>'



def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): 
#input:
#   title: if it's a tv show episode and it's in the library, then it's the title of the _episode_,
#          if it's a tv show episode and it is not in the library, then it's the cleaned up name of the file,
#          if it's a movie and it's in the library, then it's the title of the movie (as stored in the lib.),
#          otherwise it's the title of the movie deduced from the filename
#   tvshow: the title of the tv show (if it's a tv show, of cource) as stored in the library or deduced from the filename
#   year: if the movie is not in the library, it's emtpy
#   set_temp: (boolean) indicates if the movie is at some place where you can't write (typically: if it's accessed via http)
#   rar: (boolean) indicates if the movie is in a rar archive
#output: (result, session_id, message)
#   result: the list of subtitles
#   session_id: this string is given to the download_subtitles function in the session_id parameter
#   message: if it's not empty, then this message will be shown in the search dialog box instead of the title/filename

    subenv.debuglog("INPUT:: path: %s, title: %s, tvshow: %s, year: %s, season: %s, episode: %s, set_temp: %s, rar: %s, lang1: %s, lang2: %s, lang3: %s" % (file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3))
    
    msg = ""
    subtitles_list = []  
    if len(tvshow) > 0:                                              # TvShow
        search_string = tvshow                                       # ("%s - %dx%.2d" % (tvshow, int(season), int(episode)))
        full_filename = os.path.basename(file_original_path)
    else:                                                            # if not in Library: year == ""
        full_filename = os.path.basename(os.path.dirname(file_original_path)) + ".avi"
        if title == "": title, year = subenv.clean_title( file_original_path ) 
        search_string = title
    
    # remove year from the end of the search string [eg.: foo (2010) ], could happen with certain tv shows (e.g. Castle(2009), V (2009), etc.)
    m2 = re.findall("\(?\d{4}\)?$", search_string)
    if len(m2) > 0 :
        m2len = -len(m2[0])
        search_string = search_string[:m2len]

    search_string = search_string.strip()
    if (len(search_string) == 1): search_string = search_string + " "
    subenv.debuglog( "Search String [ %s ]" % ( search_string, ) )     
    
    subtitles_list = []
    try:
        base_url = base_urls[0]
        url = base_url + search_url_postfix + urllib.quote_plus(search_string)
        content = ""
        subenv.debuglog("Getting url: %s" % (url) )
        content = urllib2.urlopen(url).read()

        #type of source
        patterntype = r'.+?\W(720p|1080p|1080|720|dvdscr|brrip|bdrip|dvdrip|hdtv|PPVRip|TS|R5|WEB\-DL)\W.+'
        matchtype = re.search(patterntype, full_filename,  re.I)
        release_type = ""
        if matchtype: release_type = matchtype.group(1).lower()
        
        #releaser
        releaser = ""
        patternreleaser = r'.+\-(\w+?)(\.\[\w+\])?\.\w{3}$'
        matchreleaser = re.search(patternreleaser, full_filename,  re.I)
        if matchreleaser: releaser = matchreleaser.group(1).lower()
        
        #on feliratok.info the episode number is listed with a leading zero (if below 10), e.g.: 4x02
        sep = season + "x" + str(episode).zfill(2)
        subenv.debuglog("Release type: %s, Releaser: %s, Episode str: %s" % (release_type, releaser, sep) )
        
        html_encoding = 'utf8'
        decode_policy = 'replace'

        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):  #  | re.UNICODE
            #subenv.debuglog("Found a movie on search page")
            link = (matches.group('link1') + urllib.quote_plus(matches.group('link2')) + matches.group('link3')).decode(html_encoding, decode_policy)
            hun_title = matches.group('huntitle').decode(html_encoding, decode_policy)
            orig_title = matches.group('origtitle').decode(html_encoding, decode_policy)
            hun_langname = matches.group('lang').decode(html_encoding, decode_policy)
            sub_id = matches.group('id').decode(html_encoding, decode_policy)
            #subenv.debuglog("Found movie on search page: orig_title: %s, hun: %s, lang: %s, link: %s, subid: %s" % (orig_title, hun_title, hun_langname, link, sub_id) )
            
            hun_title, parenthesized =subutils.remove_parenthesized_parts(hun_title)
            orig_title = orig_title + parenthesized
            
            eng_langname = subutils.lang_hun2eng(hun_langname)
            flag = languageTranslate(eng_langname,0,2)
            if flag == "": flag = "-"

            score = 0
            rating = 0

            
            orig_title_low = orig_title.lower()
            search_low = search_string.lower()
            if (release_type != "") and (release_type in orig_title_low): 
                score += 10
                rating += 1
            if (releaser != "") and (releaser in orig_title_low): 
                score += 5
                rating += 1
            if (year != "") and (str(year) in orig_title_low):
                score += 20
            if (orig_title_low.startswith(search_low) or hun_title.startswith(search_low)):
                score += 500
                rating += 4


            if hun_langname.lower() == "magyar": score += 1
                
            if len(tvshow) > 0:
                if sep in orig_title_low: 
                    score += 100
                    rating += 4
            else:
                rating *= 1.25

            sync = (rating == 10)
            #rating format must be string 
            rating = str(int(rating))
            
            subenv.debuglog("Found movie on search page: orig_title: %s, hun: %s, lang: %s, link: %s, flag: %s, rating: %s, score: %s" % (orig_title, hun_title, hun_langname, link, flag, rating, score) )
            subtitles_list.append({'movie':  orig_title, 'filename': orig_title + " / " + hun_title, 'link': link, 'id': sub_id, 'language_flag': 'flags/' + flag + '.gif', 'language_name': eng_langname, 'movie_file':file_original_path, 'eng_language_name': eng_langname, 'sync': sync, 'rating': rating, 'format': 'srt', 'base_url' : base_url, 'score': score })

        subenv.debuglog("%d subtitles found" % (len(subtitles_list)) )
        error_msg = ""
        if len(subtitles_list) == 0: 
            error_msg = "No subtitles found"
        else:
            #subtitles_list = sorted(subtitles_list,key=lambda subtitle: subtitle['language_name'], reverse=True);
            subtitles_list = sorted(subtitles_list,key=lambda sub: sub['score'], reverse=True);
            
        return subtitles_list, "", error_msg #standard output

    except Exception, inst: 
        subenv.errorlog( "query error: %s" % (inst))
        msg = "Query error:" + str(inst)
        subtitles_list = []
        return subtitles_list, "", msg #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): 
#input:
#   subtitles_list[pos]: is the selected subtitle data record (as was returned by search_subtitles())
#   zip_subs: see 'zipped' output parameter
#   tmp_sub_dir: a tmp dir that should be used to download the subtitle into
#   sub_folder: the dir where the subtitle will be automatically copied by the caller
#   session_id: the session_id string returned by search_subtitles()
#output: (zipped, language, subtitles_file)
#   zipped: (boolean) if it's true, then the output subtitle is zippped and is in the file 
#           given by the 'zip_subs' input parameter, and the 'subtitles_file' return value is discarded
#   language: the language of the subtitle (the full english name of the language)
#   subtitles_file: if zipped is false, then this gives the full path of the downloaded subtitle file
    subs_file = ""
    try:
        import urllib
        subdata = subtitles_list[pos]
        language = subdata["eng_language_name"]
        if language == "": language = "Hungarian"
        base_url = subdata["base_url"]

        #subenv.debuglog("INPUT:: subtitles_data: %s, pos: %s, zip_subs: %s, tmp_sub_dir: %s, sub_folder: %s, session_id: %s" % (subdata, pos, zip_subs, tmp_sub_dir, sub_folder, session_id) )

        # ##########################################################################################################
        # download subtitle file
        
        url = base_url + subdata[ "link" ]
        subenv.debuglog( "download link: %s" % (url,) ) 
        
        f = urllib.urlopen(url)
        response = urllib.urlopen(url)

        
        # find out the sub filename
        disp_header = response.info().getheader("Content-Disposition", "");
        m1 = re.findall('filename="([^"]+)"', disp_header, re.IGNORECASE);
        if len(m1) > 0:
            local_tmp_filename = m1[0].replace("\\", "").replace("/", "_")
        else:
            local_tmp_filename = "SuperSubtitles.srt"

        # parse downloaded file format
        ext_idx = local_tmp_filename.rfind(".")
        if (ext_idx >= 0):
            format = local_tmp_filename[ext_idx + 1:]
        else:
            format = "srt"
        subenv.debuglog("Downloaded file format: %s, filename: %s" % (format, local_tmp_filename) )

        # download file    
        local_tmp_path = os.path.join(tmp_sub_dir, "SuperSubtitles." + format)
        try:
            subenv.debuglog("Saving file to: %s" % (local_tmp_path) )
            local_file_handle = open(local_tmp_path, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            subenv.debuglog("Failed to save file to '%s'" % (local_tmp_path) )
            return False, language, subs_file #standard output
        else:
            subenv.debuglog("file saved to '%s'" % (local_tmp_path) )
        

        # unpack if needed
        if (format != "zip") and (format != "rar"):
            subs_file = local_tmp_path
            packed = False
        else:
            packed = True
            
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            filecount = init_filecount
            subenv.unpack_archive(local_tmp_path, tmp_sub_dir)
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 5): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                waittime  = waittime + 1
            if waittime == 5:
                subenv.debuglog("Failed to unpack subtitles files into '%s'" % (tmp_sub_dir) )
            else:
                subenv.debuglog("Unpacked files in '%s'" % (tmp_sub_dir) )
                unpacked_subs = []
                for file in files:
                    if (string.split(file, '.')[-1] in ["srt", "sub", "txt", "ssa", "smi"]):
                        unpacked_subs.append(file)
                        
                if len(unpacked_subs) == 0: return False, language, ""
                
                subs_file = ""
                movie = subdata['movie_file']
                for sub in unpacked_subs:
                    if subutils.filename_match_exact(movie, sub):
                        subs_file = sub
                        subenv.debuglog("Exact match found" )
                        break
                        
                if subs_file == "":
                    for sub in unpacked_subs:
                        if subutils.filename_match_tvshow(movie, sub):
                            subs_file = sub
                            subenv.debuglog("tv show match found" )
                            break

                if subs_file == "": subs_file = unpacked_subs[0]
                subs_file = os.path.join(tmp_sub_dir, subs_file)
                subenv.debuglog("Unpacked subtitles file selected: '%s'" % (subs_file) )
        return False, language, subs_file #standard output

    except Exception, inst: 
        subenv.errorlog( "download error : %s" % (inst))
        return False, language, subs_file #standard output
    
    
    

########NEW FILE########
__FILENAME__ = subenv
# coding=iso-8859-2
debug_pretext = "[Feliratok.hu] "


def debuglog(msg):
    import xbmc
    msg = msg.encode('ascii', 'replace')
    xbmc.log( debug_pretext + msg, level=xbmc.LOGDEBUG )     

def errorlog(msg):
    import xbmc
    msg = msg.encode('ascii', 'replace')
    xbmc.log( debug_pretext + msg, level=xbmc.LOGERROR )     

def unpack_archive(archive_file, dst_dir):
    import xbmc
    xbmc.executebuiltin("XBMC.Extract(" + archive_file + "," + dst_dir +")")

def clean_title(filename):
    import xbmc                                 
    return xbmc.getCleanMovieTitle( filename ) 

########NEW FILE########
__FILENAME__ = subutils
# coding=iso-8859-2
import re
import os

def lang_hun2eng(hunlang):
  languages = {
            

    "alb�n"              :  "Albanian",
    "arab"               :  "Arabic",
    "bolg�r"             :  "Bulgarian",
    "k�nai"              :  "Chinese",
    "horv�t"             :  "Croatian",
    "cseh"               :  "Czech",
    "d�n"                :  "Danish",
    "holland"            :  "Dutch",
    "angol"              :  "English",
    "�szt"               :  "Estonian",
    "finn"               :  "Finnish",
    "francia"            :  "French",
    "n�met"              :  "German",
    "g�r�g"              :  "Greek",
    "h�ber"              :  "Hebrew",
    "hindi"              :  "Hindi",
    "magyar"             :  "Hungarian",
    "olasz"              :  "Italian",
    "jap�n"              :  "Japanese",
    "koreai"             :  "Korean",
    "lett"               :  "Latvian",
    "litv�n"             :  "Lithuanian",
    "maced�n"            :  "Macedonian",
    "norv�g"             :  "Norwegian",
    "lengyel"            :  "Polish",
    "portug�l"           :  "Portuguese",
    "rom�n"              :  "Romanian",
    "orosz"              :  "Russian",
    "szerb"              :  "Serbian",
    "szlov�k"            :  "Slovak",
    "szlov�n"            :  "Slovenian",
    "spanyol"            :  "Spanish",
    "sv�d"               :  "Swedish",
    "t�r�k"              :  "Turkish",

  }
  return languages[ hunlang.lower() ] 

def clean_title(title):
    for char in ['[', ']', '_', '(', ')','.','-', '  ', '  ', '  ']: 
       title = title.replace(char, ' ')
    title = title.strip()
    return title
  
  
def filename_match_exact(movie_file, sub_file):
    movie_file = os.path.basename(movie_file).lower()
    sub_file = os.path.basename(sub_file).lower()
    i = movie_file.rfind(".")
    if i > 0: movie_file = movie_file[:i]
    movie_file = clean_title(movie_file)
    sub_file = clean_title(sub_file)
    return sub_file.startswith(movie_file)
    
  
def filename_match_tvshow(movie_file, sub_file):
    regex_expressions = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                        '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09 
                        '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                        '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                        '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                        'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',
                        '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                        '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)'                 #foo_[s01]_[e01]
                        '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)'        #foo, s01e01, foo.s01.e01, foo.s01-e01
                        ]
    sub_info = ""
    is_tvshow = 0
   
    for regex in regex_expressions:
        movie_matches = re.findall(regex, movie_file)                  
        if len(movie_matches) > 0 : 
            is_tvshow = 1
            break
    
    if (is_tvshow == 0): return False
        
    for regex in regex_expressions:       
        sub_matches = re.findall(regex, sub_file)
        if len(sub_matches) > 0 :
            if ((int(sub_matches[0][0]) == int(movie_matches[0][0])) and (int(sub_matches[0][1]) == int(movie_matches[0][1]))):
                return True

    return False

def remove_parenthesized_parts(str):
    removed = ""
    while True:
        parenth = re.search("\([^\)]+\)", str)
        if not parenth: break
        begin, end = parenth.span()
        removed = removed + parenth.group(0)
        str = str[:begin] + str[end:]
    return str, removed


########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://swesub.nu/"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# direct link pattern example:
"""http://swesub.nu/title/tt0389722/"""
titleurl_pattern = 'http://swesub.nu/title/tt(\d{4,10})/'
# group(1) = movienumber

# find correct movie pattern example:
"""<h2><a href="/title/tt0389722/">30 Days of Night (2007)</a></h2>"""
title_pattern = '<h2><a href="/title/tt(\d{4,10})/">([^\r\n\t]*?) \((\d{4})\)</a></h2>'
# group(1) = movienumber, group(2) = title, group(3) = year

# videosubtitle pattern examples:
"""<a href="/download/25182/" rel="nofollow" class="dxs">I Am Number Four 2011 PPVRiP-IFLIX  (1 cd)</a>"""
"""<a href="/download/21581/" rel="nofollow" class="ssg">Avatar.2009.DVDRiP.XViD-iMBT (2 cd)</a>"""
videosubtitle_pattern = '<a href="/download/(\d{1,10})/"[^\n\r\t>]*?>([^\n\r\t]*?)\(1 cd\)</a>'
# group(1) = id, group(2) = filename

#====================================================================================================================
# Functions
#====================================================================================================================

def getallvideosubs(searchstring, file_original_path, movienumber, languageshort, languagelong, subtitles_list):
    url = main_url + 'title/tt' + str(movienumber) + '/'
    content, return_url = geturl(url)
    if content is not None:
        for matches in re.finditer(videosubtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            filename = string.strip(matches.group(2))
            if searchstring in filename:
                log( __name__ ,"Subtitles found: %s (id = %s)" % (filename, id))
                if isexactmatch(filename, os.path.basename(file_original_path)):
                    subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': True, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
                else:
                    subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})


def isexactmatch(subsfile, videofile):
    match = re.match("(.*)\.", videofile)
    if match:
        videofile = string.lower(match.group(1))
        subsfile = string.lower(subsfile)
        log( __name__ ," comparing subtitle file with videofile to see if it is a match (sync):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (string.lower(subsfile), string.lower(videofile)) )
        if string.find(string.lower(subsfile),string.lower(videofile)) > -1:
            log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
            return True
        else:
            return False
    else:
        return False


def findtitlenumber(title, year):
    movienumber = None
    if year: # movie
        url = main_url + '/?s=' + urllib.quote_plus('%s (%s)' % (title, year))
    else: # tv show
        url = main_url + '/?s=' + urllib.quote_plus(title)
    content, return_url = geturl(url)
    if content is not None:
        match = re.search(titleurl_pattern, return_url, re.IGNORECASE | re.DOTALL)
        if match:
            movienumber = match.group(1)
        else:
            match = re.search(title_pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                if (string.lower(match.group(2)) == string.lower(title)):
                    movienumber = match.group(1)
    return movienumber


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"Getting url: %s" % (url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
        return_url = response.geturl()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
        content    = None
        return_url = None
    return content, return_url


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        movienumber = findtitlenumber(title, year)
        if movienumber is not None:
            log( __name__ ,"Movienumber found for: %s (%s)" % (title, year))
            getallvideosubs('', file_original_path, movienumber, "sv", "Swedish", subtitles_list)
        else:
            log( __name__ ,"Movienumber not found for: %s (%s)" % (title, year))
    if len(tvshow) > 0:
        movienumber = findtitlenumber(tvshow, None)
        if movienumber is not None:
            log( __name__ ,"Movienumber found for: %s (%s)" % (title, year))
            searchstring = "S%#02dE%#02d" % (int(season), int(episode))
            getallvideosubs(searchstring, file_original_path, movienumber, "sv", "Swedish", subtitles_list)
        else:
            log( __name__ ,"Movienumber not found for: %s (%s)" % (title, year))

#    log( __name__ ,"Search string = %s" % (searchstring))

#    swedish = 0
#    if string.lower(lang1) == "swedish": swedish = 1
#    elif string.lower(lang2) == "swedish": swedish = 2
#    elif string.lower(lang3) == "swedish": swedish = 3

#    if (swedish > 0):
#        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

#    if (swedish == 0):
#        msg = "Won't work, Swesub.nu is only for Swedish subtitles."

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    url = main_url + "download/" + id + "/"
    log( __name__ ,"Fetching subtitles using url %s" % (url))
    content, return_url = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
            else:
                log( __name__ ,"Unpacked files in '%s'" % (tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"Unpacked subtitles file '%s'" % (file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, xmlrpclib, base64
from xml.dom import minidom
from utilities import languageTranslate, log

KEY = "UGE4Qk0tYXNSMWEtYTJlaWZfUE9US1NFRC1WRUQtWA=="

def compare_columns(b,a):
  return cmp( b["language_name"], a["language_name"] ) 

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        content    = None
    return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    msg = ""
    subtitles_list = []
    search_url = "http://api.titlovi.com/xml_get_api.ashx?x-dev_api_id=%s&keyword=%s&uiculture=en"
    languages = [lang1, lang2, lang3]

    if len(tvshow) > 0:                                              # TvShow
        search_string = ("%s S%.2dE%.2d" % (tvshow,
                                            int(season), 
                                            int(episode),)
                                            ).replace(" ","+")      
    else:                                                            # Movie or not in Library
        if str(year) == "":                                          # Not in Library
            title, year = xbmc.getCleanMovieTitle( title )
        else:                                                        # Movie in Library
            year  = year
            title = title
        search_string = title.replace(" ","+")
    log( __name__ , "Search String [ %s ]" % (search_string,))
    subtitles = minidom.parseString(
                        geturl(search_url % (
                               base64.b64decode(KEY)[::-1], search_string))
                               ).getElementsByTagName("subtitle")
    if subtitles:
      url_base = "http://en.titlovi.com/downloads/default.ashx?type=1&mediaid=%s"
      for subtitle in subtitles:
        lang = subtitle.getElementsByTagName("language")[0].firstChild.data
        if lang == "rs": lang = "sr"
        if lang == "ba": lang = "bs"
        if lang == "si": lang = "sl"
        lang_full = languageTranslate(lang, 2,0)
        if lang_full in languages:
            sub_id = subtitle.getElementsByTagName("url")[0].firstChild.data
            movie = subtitle.getElementsByTagName("safeTitle")[0].firstChild.data
            if subtitle.getElementsByTagName("release")[0].firstChild:
                filename = "%s - %s" % (movie, subtitle.getElementsByTagName("release")[0].firstChild.data)
            else:
                filename = movie  
            rating = int(float(subtitle.getElementsByTagName("score")[0].firstChild.data)*2)
            flag_image = "flags/%s.gif" % lang
            link = url_base % sub_id.split("-")[-1].replace("/","")            
            subtitles_list.append({'filename'     :filename,
                                   'link'         :link,
                                   'language_name':lang_full,
                                   'language_id'  :lang,
                                   'language_flag':flag_image,
                                   'movie'        :movie,
                                   'rating'       :str(rating),
                                   'sync'         :False
                                   })

    subtitles_list = sorted(subtitles_list, compare_columns)
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    language = subtitles_list[pos][ "language_name" ]
    url = subtitles_list[pos][ "link" ]
    log( __name__ ,"Fetching subtitles using url %s" % url)
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % local_tmp_file)
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % local_tmp_file)
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while ((filecount == init_filecount) and
                   (waittime < 20) and
                   (init_max_mtime == max_mtime)): # nothing yet extracted
                time.sleep(1) # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file 
                # created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"Failed to unpack subtitles in '%s'" % tmp_sub_dir)
            else:
                log( __name__ ,"Unpacked files in '%s'" % tmp_sub_dir)
                for file in files:
                    # there could be more subtitle files 
                    #in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if ((string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and 
                        (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime)): 
                        # unpacked file is a newly created subtitle file
                        log( __name__ ,"Unpacked subtitles file '%s'" % file)
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output
        
       

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

################################   Titulky.com #################################


import sys
import os
import xbmc,xbmcgui

import time,calendar
import urllib2,urllib,re,cookielib
from utilities import languageTranslate, log

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__addon__      = sys.modules[ "__main__" ].__addon__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	# need to filter titles like <Localized movie name> (<Movie name>)
	br_index = title.find('(')
	if br_index > -1:
		title = title[:br_index]
	title = title.strip()
	session_id = "0"
	client = TitulkyClient()    
	subtitles_list = client.search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 )   
	return subtitles_list, session_id, ""  #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	subtitle_id =  subtitles_list[pos][ 'ID' ]
	client = TitulkyClient()
	username = __addon__.getSetting( "Titulkyuser" )
	password = __addon__.getSetting( "Titulkypass" )
	if password == '' or username == '':
		log(__name__,'Credentials to Titulky.com not provided')
	else:
		if client.login(username,password) == False:
			log(__name__,'Login to Titulky.com failed. Check your username/password at the addon configuration')
			dialog = xbmcgui.Dialog()
			dialog.ok(__scriptname__,_( 756 ))
			return True,subtitles_list[pos]['language_name'], ""
		log(__name__,'Login successfull')
	log(__name__,'Get page with subtitle (id=%s)'%(subtitle_id))
	content = client.get_subtitle_page(subtitle_id)
	control_img = client.get_control_image(content)
	if not control_img == None:
		log(__name__,'Found control image :(, asking user for input')
		# subtitle limit was reached .. we need to ask user to rewrite image code :(
		log(__name__,'Download control image')
		img = client.get_file(control_img)
		img_file = open(os.path.join(tmp_sub_dir,'image.png'),'w')
		img_file.write(img)
		img_file.close()

		solver = CaptchaInputWindow(captcha = os.path.join(tmp_sub_dir,'image.png'))
		solution = solver.get()
		if solution:
			log(__name__,'Solution provided: %s' %solution)
			content = client.get_subtitle_page2(content,solution,subtitle_id)
			control_img2 = client.get_control_image(content)
			if not control_img2 == None:
				log(__name__,'Invalid control text')
				xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,"Invalid control text",os.path.join(__cwd__,'icon.png')))
				return True,subtitles_list[pos]['language_name'], ""
		else:
			log(__name__,'Dialog was canceled')
			log(__name__,'Control text not confirmed, returning in error')
			return True,subtitles_list[pos]['language_name'], ""

	wait_time = client.get_waittime(content)
	cannot_download = client.get_cannot_download_error(content)
	if not None == cannot_download:
		log(__name__,'Subtitles cannot be downloaded, user needs to login')
		dialog = xbmcgui.Dialog()
		dialog.ok(__scriptname__,_( 761 ))
		return True,subtitles_list[pos]['language_name'], ""
	link = client.get_link(content)
	log(__name__,'Got the link, wait %i seconds before download' % (wait_time))
	delay = wait_time
	for i in range(wait_time+1):
		line2 = 'Download will start in %i seconds' % (delay,)
		xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,os.path.join(__cwd__,'icon.png')))
		delay -= 1
		time.sleep(1)

	log(__name__,'Downloading subtitle zip')
	data = client.get_file(link)
	log(__name__,'Saving to file %s' % zip_subs)
	zip_file = open(zip_subs,'wb')
	zip_file.write(data)
	zip_file.close()
	return True,subtitles_list[pos]['language_name'], "zip" #standard output

def lang_titulky2xbmclang(lang):
	if lang == 'CZ': return 'Czech'
	if lang == 'SK': return 'Slovak'
	return 'English'

def lang_xbmclang2titulky(lang):
	if lang == 'Czech': return 'CZ'
	if lang == 'Slovak': return 'SK'
	return 'EN'	

def get_episode_season(episode,season):
	return 'S%sE%s' % (get2DigitStr(int(season)),get2DigitStr(int(episode)))
def get2DigitStr(number):
	if number>9:
		return str(number)
	else:
		return '0'+str(number)

def lang2_opensubtitles(lang):
	lang = lang_titulky2xbmclang(lang)
	return languageTranslate(lang,0,2)


class CaptchaInputWindow(xbmcgui.WindowDialog):
   def __init__(self, *args, **kwargs):
      self.cptloc = kwargs.get('captcha')
      self.img = xbmcgui.ControlImage(435,50,524,90,self.cptloc)
      self.addControl(self.img)
      self.kbd = xbmc.Keyboard('',_( 759 ),False)

   def get(self):
      self.show()
      self.kbd.doModal()
      if (self.kbd.isConfirmed()):
         text = self.kbd.getText()
         self.close()
         return text
      self.close()
      return False

class TitulkyClient(object):

	def __init__(self):
		self.server_url = 'http://www.titulky.com'
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
		opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)')]
		urllib2.install_opener(opener)

	def login(self,username,password):
			log(__name__,'Logging in to Titulky.com')
			login_postdata = urllib.urlencode({'Login': username, 'Password': password, 'foreverlog': '1','Detail2':''} )
			request = urllib2.Request(self.server_url + '/index.php',login_postdata)
			response = urllib2.urlopen(request)
			log(__name__,'Got response')
			if response.read().find('BadLogin')>-1:
				return False

			log(__name__,'Storing Cookies')
			self.cookies = {}
			self.cookies['CRC'] = re.search('CRC=(\S+);', response.headers.get('Set-Cookie'), re.IGNORECASE | re.DOTALL).group(1)
			self.cookies['LogonLogin'] = re.search('LogonLogin=(\S+);', response.headers.get('Set-Cookie'), re.IGNORECASE | re.DOTALL).group(1)
			self.cookies['LogonId'] = re.search('LogonId=(\S+);', response.headers.get('Set-Cookie'), re.IGNORECASE | re.DOTALL).group(1)

			return True

	def search_subtitles(self, file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ):
		url = self.server_url+'/index.php?'+urllib.urlencode({'Fulltext':title,'FindUser':''})
		if not (tvshow == None or tvshow == ''):
			title2 = tvshow+' '+get_episode_season(episode,season)
			url = self.server_url+'/index.php?'+urllib.urlencode({'Fulltext':title2,'FindUser':''})
		req = urllib2.Request(url)
		try:
			size, SubHash = xbmc.subHashAndFileSize(file_original_path)
			file_size='%.2f' % (float(size)/(1024*1024))
		except:
			file_size='-1'
		log(__name__,'Opening %s' % (url))
		response = urllib2.urlopen(req)
		content = response.read()
		response.close()
		log(__name__,'Done')
		subtitles_list = []
		max_downloads=1
		log(__name__,'Searching for subtitles')
		for row in re.finditer('<tr class=\"r(.+?)</tr>', content, re.IGNORECASE | re.DOTALL):
			item = {}
			log(__name__,'New subtitle found')
			try:
				item['ID'] = re.search('[^<]+<td[^<]+<a href=\"[\w-]+-(?P<data>\d+).htm\"',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['title'] = re.search('[^<]+<td[^<]+<a[^>]+>(<div[^>]+>)?(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['sync'] = ''
				sync_found = re.search('((.+?)</td>)[^>]+>[^<]*<a(.+?)title=\"(?P<data>[^\"]+)',row.group(1),re.IGNORECASE | re.DOTALL )
				if sync_found:
					item['sync'] = sync_found.group('data')
				item['tvshow'] = re.search('((.+?)</td>){2}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['year'] = re.search('((.+?)</td>){3}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['downloads'] = re.search('((.+?)</td>){4}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['lang'] = re.search('((.+?)</td>){5}[^>]+><img alt=\"(?P<data>\w{2})\"',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['numberOfDiscs'] = re.search('((.+?)</td>){6}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['size'] = re.search('((.+?)</td>){7}[^>]+>(?P<data>[\d\.]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
			except:
				log(__name__,'Exception when parsing subtitle, all I got is  %s' % str(item))
				continue
			if item['sync'] == '': # if no sync info is found, just use title instead of None
				item['filename'] = item['title']
			else:
				item['filename'] = item['sync']
			item['language_flag'] = "flags/%s.gif" % (lang2_opensubtitles(item['lang']))
			
			sync = False
			if not item['sync'] == '' and file_original_path.find(item['sync']) > -1:
				log(__name__,'found sync : filename match')
				sync = True
			if file_size==item['size']:
				log(__name__,'found sync : size match')
				sync = True
			item['sync'] = sync
			
			try:
				downloads = int(item['downloads'])
				if downloads>max_downloads:
					max_downloads=downloads
			except:
				downloads=0
			item['downloads'] = downloads
			
			if not year == '':
				if not item['year'] == year:
					log(__name__,'year does not match, ignoring %s' % str(item))
					continue
			lang = lang_titulky2xbmclang(item['lang'])
			
			item['language_name'] = lang
			item['mediaType'] = 'mediaType'
			item['rating'] = '0'
			
			if lang in [lang1,lang2,lang3]:
				subtitles_list.append(item)
			else:
				log(__name__,'language does not match, ignoring %s' % str(item))
		# computing ratings is based on downloads
		for subtitle in subtitles_list:
			subtitle['rating'] = str((subtitle['downloads']*10/max_downloads))
		return subtitles_list

	def get_cannot_download_error(self,content):
		if content.find('CHYBA') > -1:
			return True

	def get_waittime(self,content):
		for matches in re.finditer('CountDown\((\d+)\)', content, re.IGNORECASE | re.DOTALL):
			return int(matches.group(1))

	def get_link(self,content):
		for matches in re.finditer('<a.+id=\"downlink\" href="([^\"]+)\"', content, re.IGNORECASE | re.DOTALL):
			return str(matches.group(1))

	def get_control_image(self,content):
		for matches in re.finditer('\.\/(captcha\/captcha\.php)', content, re.IGNORECASE | re.DOTALL):
			return '/'+str(matches.group(1))
		return None

	def get_file(self,link):
		url = self.server_url+link
		log(__name__,'Downloading file %s' % (url))
		req = urllib2.Request(url)
		req = self.add_cookies_into_header(req)
		response = urllib2.urlopen(req)
		if response.headers.get('Set-Cookie'):
			phpsessid = re.search('PHPSESSID=(\S+);', response.headers.get('Set-Cookie'), re.IGNORECASE | re.DOTALL)
			if phpsessid:
				log(__name__, "Storing PHPSessionID")
				self.cookies['PHPSESSID'] = phpsessid.group(1)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content

	def get_subtitle_page2(self,content,code,id):
		url = self.server_url+'/idown.php'
		post_data = {'downkod':code,'titulky':id,'zip':'z','securedown':'2','histstamp':''}
		req = urllib2.Request(url,urllib.urlencode(post_data))
		req = self.add_cookies_into_header(req)
		log(__name__,'Opening %s POST:%s' % (url,str(post_data)))
		response = urllib2.urlopen(req)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content
		
	def get_subtitle_page(self,id):
		timestamp = str(calendar.timegm(time.gmtime()))
		url = self.server_url+'/idown.php?'+urllib.urlencode({'R':timestamp,'titulky':id,'histstamp':'','zip':'z'})
		log(__name__,'Opening %s' % (url))
		req = urllib2.Request(url)
		req = self.add_cookies_into_header(req)
		response = urllib2.urlopen(req)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content

	def add_cookies_into_header(self,request):
		cookies_string = "LogonLogin=" + self.cookies['LogonLogin'] + "; "
		cookies_string += "LogonId=" + self.cookies['LogonId'] + "; "
		cookies_string += "CRC=" + self.cookies['CRC']
		if 'PHPSESSID' in self.cookies:
			cookies_string += "; PHPSESSID=" + self.cookies['PHPSESSID']
		request.add_header('Cookie',cookies_string)
		return request


########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

#===============================================================================
# Torec.net subtitles service.
# Version: 1.0
#
# Change log:
# 1.0 - First Release (02/11/2012)
#===============================================================================

import os, re, string, time, urllib2
from utilities import *
import xbmc

from TorecSubtitlesDownloader import TorecSubtitlesDownloader

__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    # Build an adequate string according to media type
    if tvshow:
        search_string = "%s S%02dE%02d" % (tvshow, int(season), int(episode))
    else:
        search_string = title
    
    subtitles_list = []
    msg = ""
    downloader = TorecSubtitlesDownloader()
    metadata = downloader.getSubtitleMetaData(search_string)
    if metadata != None:
        for option in metadata.options:
            subtitles_list.append({'page_id'       : metadata.id,
                                   'filename'      : option.name,
                                   'language_flag' : "flags/he.gif",
                                   'language_name' : "Hebrew",
                                   'subtitle_id'   : option.id,
                                   'sync'          : False,
                                   'rating'        : "0",
                                })

    return subtitles_list, "", msg

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    page_id                 = subtitles_list[pos]["page_id"]  
    subtitle_id             = subtitles_list[pos]["subtitle_id"]  

    icon =  os.path.join(__cwd__,"icon.png")
    delay = 20
    download_wait = delay
    downloader = TorecSubtitlesDownloader()
    # Wait the minimal time needed for retrieving the download link
    for i in range (int(download_wait)):
        downloadLink =  downloader.getDownloadLink(page_id, subtitle_id, False)
        if (downloadLink != None):
            break
        line2 = "download will start in %i seconds" % (delay,)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,icon))
        delay -= 1
        time.sleep(1)
        
    log(__name__ ,"Downloading subtitles from '%s'" % downloadLink)
    (subtitleData, subtitleName) = downloader.download(downloadLink)
    
    log(__name__ ,"Saving subtitles to '%s'" % zip_subs)
    downloader.saveData(zip_subs, subtitleData, False)
        
    return True,"Hebrew", "" #standard output
########NEW FILE########
__FILENAME__ = TorecSubtitlesDownloader
import cookielib
import datetime
import zipfile
import urllib2
import urllib
import codecs
import shutil
import time
import os
import sys
import re
import zlib
import os.path
from BeautifulSoup import BeautifulSoup

from utilities import *

def convert_file(inFile,outFile):
	''' Convert a file in cp1255 encoding to utf-8
	
	:param inFile: the path to the intput file
	:param outFile: the path to the output file
	'''
	with codecs.open(inFile,"r","cp1255") as f:
		with codecs.open(outFile, 'w', 'utf-8') as output:
			for line in f:
				output.write(line)
	return

class SubtitleOption(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        
    def __repr__(self):
        return "%s" % (self.name)
    
class SubtitlePage(object):
    def __init__(self, id, name, url, data):
        self.id = id
        self.name = name
        self.url = url
        self.options = self._parseOptions(data)
        
    def _parseOptions(self, data):
        subtitleSoup = BeautifulSoup(data)
        subtitleOptions = subtitleSoup("div", {'class' : 'download_box' })[0].findAll("option")
        return map(lambda x: SubtitleOption(x.string.strip(), x["value"]), subtitleOptions)

    def __str__(self):
        log(__name__ ,self.name)
        for option in self.options:
            log(__name__ ,option)
        
class Response(object):
    def __init__(self, response):
        self.data = self._handleData(response)
        self.headers = response.headers
        
    def _handleData(self, resp):
        data = resp.read()
        if (len(data) != 0):
            try:
                data = zlib.decompress(data, 16+zlib.MAX_WBITS)
            except zlib.error:
                pass
        return data

class FirefoxURLHandler():
    def __init__(self):
        cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.opener.addheaders = [('Accept-Encoding','gzip, deflate'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent', 'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:16.0) Gecko/20100101 Firefox/16.0')]
    
    def request(self, url, data=None, ajax=False, referer=None, cookie=None):
        if (data != None):
            data = urllib.urlencode(data)
        # FIXME: Awful code duplication
        if (ajax == True):
            self.opener.addheaders += [('X-Requested-With', 'XMLHttpRequest')]
        if (referer != None):
            self.opener.addheaders += [('Referer', referer)]
        if (cookie != None):
            self.opener.addheaders += [('Cookie', cookie)]
  
        resp = self.opener.open(url, data)        
        return Response(resp)

class TorecSubtitlesDownloader:
    DEFAULT_SEPERATOR = " "
    BASE_URL = "http://www.torec.net"
    SUBTITLE_PATH = "sub.asp?sub_id="
    DEFAULT_COOKIE = "Torec_NC_s=%(screen_width)d; Torec_NC_sub_%(subId)s=sub=%(current_datetime)s"

    def __init__(self):
        self.urlHandler = FirefoxURLHandler()
        
    def _buildDefaultCookie(self, subID):
        currentTime = datetime.datetime.now().strftime("%m/%d/%Y+%I:%M:%S+%p")
        return self.DEFAULT_COOKIE % {"screen_width" : 1760, 
                                      "subId" : subID, 
                                      "current_datetime" : currentTime}
    
    def searchMovieName(self, movieName):
        response = self.urlHandler.request("%s/ssearch.asp" % self.BASE_URL, {"search" : movieName})
        match = re.search('sub\.asp\?sub_id=(\w+)', response.data)
        if (match is None):
            return None
          
        id = match.groups()[0]
        subURL = "%s/%s%s" % (self.BASE_URL, self.SUBTITLE_PATH, id)
        subtitleData = self.urlHandler.request(subURL).data
        return SubtitlePage(id, movieName, subURL, subtitleData)
        
    def findChosenOption(self, name, subtitlePage):
        name = name.split(self.DEFAULT_SEPERATOR)
        # Find the most likely subtitle (the subtitle which adheres to most of the movie properties)
        maxLikelihood = 0
        chosenOption = None
        for option in subtitlePage.options:
            subtitleName = self.sanitize(option.name).split(" ")
            subtitleLikelihood = 0
            for token in subtitleName:
                if token in name:
                    subtitleLikelihood += 1
                if (subtitleLikelihood > maxLikelihood):
                    maxLikelihood = subtitleLikelihood
                    chosenOption = option

        return chosenOption
        
    def _requestSubtitle(self, subID, subURL):
        params = {"sub_id"  : subID, 
                  "s"       : 1760}
                  
        return self.urlHandler.request("%s/ajax/sub/guest_time.asp" % self.BASE_URL, params, 
                                        ajax=True, referer=subURL, cookie=self._buildDefaultCookie(subID)).data
        
    def getDownloadLink(self, subID, optionID, subURL, persist=True):        
        requestID = self._requestSubtitle(subID, subURL)
        
        params = {"sub_id" : subID, "code": optionID, "sh" : "yes", "guest" : requestID, "timewaited" : "16"}
        for i in xrange(16):
            response = self.urlHandler.request("%s/ajax/sub/downloadun.asp" % self.BASE_URL, params, ajax=True)
            if (len(response.data) != 0 or not persist):
                break
            time.sleep(1)
            
        return response.data
        
    def download(self, downloadLink):
        response = self.urlHandler.request("%s%s" % (self.BASE_URL, downloadLink))
        fileName = re.search("filename=(.*)", response.headers["content-disposition"]).groups()[0]
        return (response.data, fileName)
        
    def saveData(self, fileName, data, shouldUnzip=True):
        log(__name__ ,"Saving to %s (size %d)" % (fileName, len(data)))
        # Save the downloaded zip file
        with open( fileName,"wb") as f:
            f.write(data)
        
        if shouldUnzip:
            # Unzip the zip file
            log(__name__ ,"Unzip the zip file")
            zipDirPath = os.path.dirname(fileName)
            zip = zipfile.ZipFile(fileName, "r")
            zip.extractall(zipDirPath)
            zip.close()
            # Remove the unneeded zip file
            os.remove(fileName)
            
            for srtFile in os.listdir(zipDirPath):
	        if srtFile.endswith(".srt"):
                    srtFile = os.path.join(zipDirPath,srtFile)
                    
                    #convert file from cp1255 to utf-8
                    tempFileName=srtFile+ ".tmp"
                    convert_file(srtFile,tempFileName)
                    shutil.copy(tempFileName,srtFile)
                    os.remove(tempFileName)
            
    def sanitize(self, name):
        return re.sub('[\.\[\]\-]', self.DEFAULT_SEPERATOR, name.upper())

    def getSubtitleMetaData(self, movieName):
        sanitizedName = self.sanitize(movieName)
        log(__name__ , "Searching for %s" % sanitizedName)
        subtitlePage = self.searchMovieName(sanitizedName)
        if subtitlePage is None:
            log(__name__ ,"Couldn't find relevant subtitle page")
            return
            
        log(__name__ , "Found relevant meta data")
        return subtitlePage
        
    def getSubtitleData(self, movieName, resultSubtitleDirectory):
        subtitlePage = self.getSubtitleMetaData(movieName)
        # Try to choose the most relevant option according to the file name
        chosenOption = self.findChosenOption(subtitlePage.name, subtitlePage)
        if chosenOption != None:
            log(__name__ ,"Found the subtitle type - %s" % chosenOption)
        else:
            
            log(__name__ ,"No suitable subtitle found!")
            log(__name__ ,"Available options are:")
            options = enumerate(subtitlePage.options, start=1)
            for num, option in options:
                log(__name__ ,"\t(%d) %s" % (num, option))
                
            choice = int(raw_input("What subtitle do you want to download? "))
            while (choice < 0 or choice > len(subtitlePage.options)):
                log(__name__ ,"bad choice")
                choice = int(raw_input("What subtitle do you want to download? "))
        
            chosenOption = subtitlePage.options[choice-1]

        # Retrieve the download link and download the subtitle
        downloadLink = self.getDownloadLink(subtitlePage.id, chosenOption.id, subtitlePage.url)
        if (downloadLink == ""):
            log(__name__ ,"Download Unsuccessful!")
            return
        
        (subtitleData, subtitleName) = self.download(downloadLink)
        
        resultSubtitlePath = os.path.join(resultSubtitleDirectory, subtitleName)
        self.saveData(resultSubtitlePath, subtitleData)

########NEW FILE########
__FILENAME__ = service
# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.undertexter.se/"
eng_download_url = "http://eng.undertexter.se/"
debug_pretext = ""

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
sv:
<a style="text-decoration: none;" title="Ladda ner undertext till 127 Hours " alt="Ladda ner undertext till 127 Hours " href="http://www.undertexter.se/laddatext.php?id=24255 ">
      <img src="http://www.undertexter.se/bilder/ladda_codec_mini.gif" width="70" height="18" border="0" align="right"></a>
                                            (1 cd)
                                                                                        <br> <img src="http://www.undertexter.se/bilder/spacer.gif" height="2"><br>
                                            Nedladdningar: 1154<br>
                                            <img src="http://www.undertexter.se/bilder/spacer.gif" height="3"><br>
                                            127 Hours_2010_HD_720p_x264_SAG_screener [mf34inc]</td>


en:
<a href="http://www.engsub.net/86981/" alt="Dexter S05E01 - My Bad" title="Dexter S05E01 - My Bad"><b>
                                            Dexter S05E01 - My Bad</b>
                                            </a></td>
                                        </tr>
                                        <tr>
                                          <td colspan="2" align="left" valign="top" bgColor="#f9f9f9"  style="padding-top: 0px; padding-left: 4px; padding-right: 0px; padding-bottom: 0px; border-bottom: 1px solid rgb(153, 153, 153); border-color: #E1E1E1" >
                                            (1 cd)
                                                                                        <br> <img src="http://www.undertexter.se/bilder/spacer.gif" height="2"><br>
                                            Nedladdningar: 2328<br>
                                            <img src="http://www.undertexter.se/bilder/spacer.gif" height="3"><br>
                                            Dexter.S05E01.720p.HDTV.x264-ORENJI</td>
"""
sv_subtitle_pattern = "href=\"http://www.undertexter.se/laddatext.php\?id=(\d{1,10}) \">\
[ \r\n]*?.{100,200}?\(1 cd\)[ \r\n]*?.{200,500}?height=\"3\"><br>[ \r\n]*?([^\r\n\t]*?)</td>"
# group(1) = id, group(2) = filename

en_subtitle_pattern = "<a href=\"http://www.engsub.net/(\d{1,10})/\" alt=\"[^\r\n\t]*?\" title=\"[^\r\n\t]*?\"><b>\
[ \r\n]*?[^\r\n\t]*?</b>.{400,500}?\(1 cd\).{250,550}?[ \r\n]*([^\r\n\t]*?)</td>[ \r\n]*?[^\r\n\t]*?</tr>"
# group(1) = id, group(2) = filename


#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(searchstring, languageshort, languagelong, subtitles_list):
    if languageshort == "sv":
        url = main_url + "?group1=on&p=soek&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
        subtitle_pattern = sv_subtitle_pattern
    if languageshort == "en":
        url = main_url + "?group1=on&p=eng_search&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
        subtitle_pattern = en_subtitle_pattern
    content = geturl(url)
    if content is not None:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            filename = string.strip(matches.group(2))
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content = response.read()
        return_url = response.geturl()
        if url != return_url:
            log( __name__ ,"%s Getting redirected url: %s" % (debug_pretext, return_url))
            if (' ' in return_url):
                log( __name__ ,"%s Redirected url contains space (workaround a bug in python redirection: 'http://bugs.python.org/issue1153027', should be solved, but isn't)" % (debug_pretext))
                return_url = return_url.replace(' ','%20')
            response = my_urlopener.open(return_url)
            content = response.read()
            return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    swedish = 0
    if string.lower(lang1) == "swedish": swedish = 1
    elif string.lower(lang2) == "swedish": swedish = 2
    elif string.lower(lang3) == "swedish": swedish = 3

    english = 0
    if string.lower(lang1) == "english": english = 1
    elif string.lower(lang2) == "english": english = 2
    elif string.lower(lang3) == "english": english = 3

    if ((swedish > 0) and (english == 0)):
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

    if ((english > 0) and (swedish == 0)):
        getallsubs(searchstring, "en", "English", subtitles_list)

    if ((swedish > 0) and (english > 0) and (swedish < english)):
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)
        getallsubs(searchstring, "en", "English", subtitles_list)

    if ((swedish > 0) and (english > 0) and (swedish > english)):
        getallsubs(searchstring, "en", "English", subtitles_list)
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

    if ((swedish == 0) and (english == 0)):
        msg = "Won't work, Undertexter.se is only for Swedish and English subtitles."

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    if string.lower(language) == "swedish":
        url = main_url + "laddatext.php?id=" + id
    if string.lower(language) == "english":
        url = eng_download_url + "subtitle.php?id=" + id
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

########NEW FILE########
__FILENAME__ = utilities
# -*- coding: utf-8 -*-

import os
import re
import sys
import xbmc
import xbmcvfs
import xbmcgui
import shutil
import struct
import unicodedata

try: import simplejson as json
except: import json

try: from hashlib import md5
except: from md5 import new as md5

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

STATUS_LABEL   = 100
LOADING_IMAGE  = 110
SUBTITLES_LIST = 120
SERVICES_LIST  = 150
CANCEL_DIALOG  = ( 9, 10, 13, 92, 216, 247, 257, 275, 61467, 61448, )

SERVICE_DIR    = os.path.join(__cwd__, "resources", "lib", "services")

LANGUAGES      = (

    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]

    ("Albanian"                   , "29",       "sq",            "alb",                 "0",                     30201  ),
    ("Arabic"                     , "12",       "ar",            "ara",                 "1",                     30202  ),
    ("Belarusian"                 , "0" ,       "hy",            "arm",                 "2",                     30203  ),
    ("Bosnian"                    , "10",       "bs",            "bos",                 "3",                     30204  ),
    ("Bulgarian"                  , "33",       "bg",            "bul",                 "4",                     30205  ),
    ("Catalan"                    , "53",       "ca",            "cat",                 "5",                     30206  ),
    ("Chinese"                    , "17",       "zh",            "chi",                 "6",                     30207  ),
    ("Croatian"                   , "38",       "hr",            "hrv",                 "7",                     30208  ),
    ("Czech"                      , "7",        "cs",            "cze",                 "8",                     30209  ),
    ("Danish"                     , "24",       "da",            "dan",                 "9",                     30210  ),
    ("Dutch"                      , "23",       "nl",            "dut",                 "10",                    30211  ),
    ("English"                    , "2",        "en",            "eng",                 "11",                    30212  ),
    ("Estonian"                   , "20",       "et",            "est",                 "12",                    30213  ),
    ("Persian"                    , "52",       "fa",            "per",                 "13",                    30247  ),
    ("Finnish"                    , "31",       "fi",            "fin",                 "14",                    30214  ),
    ("French"                     , "8",        "fr",            "fre",                 "15",                    30215  ),
    ("German"                     , "5",        "de",            "ger",                 "16",                    30216  ),
    ("Greek"                      , "16",       "el",            "ell",                 "17",                    30217  ),
    ("Hebrew"                     , "22",       "he",            "heb",                 "18",                    30218  ),
    ("Hindi"                      , "42",       "hi",            "hin",                 "19",                    30219  ),
    ("Hungarian"                  , "15",       "hu",            "hun",                 "20",                    30220  ),
    ("Icelandic"                  , "6",        "is",            "ice",                 "21",                    30221  ),
    ("Indonesian"                 , "0",        "id",            "ind",                 "22",                    30222  ),
    ("Italian"                    , "9",        "it",            "ita",                 "23",                    30224  ),
    ("Japanese"                   , "11",       "ja",            "jpn",                 "24",                    30225  ),
    ("Korean"                     , "4",        "ko",            "kor",                 "25",                    30226  ),
    ("Latvian"                    , "21",       "lv",            "lav",                 "26",                    30227  ),
    ("Lithuanian"                 , "0",        "lt",            "lit",                 "27",                    30228  ),
    ("Macedonian"                 , "35",       "mk",            "mac",                 "28",                    30229  ),
    ("Malay"                      , "0",        "ms",            "may",                 "29",                    30248  ),    
    ("Norwegian"                  , "3",        "no",            "nor",                 "30",                    30230  ),
    ("Polish"                     , "26",       "pl",            "pol",                 "31",                    30232  ),
    ("Portuguese"                 , "32",       "pt",            "por",                 "32",                    30233  ),
    ("PortugueseBrazil"           , "48",       "pb",            "pob",                 "33",                    30234  ),
    ("Romanian"                   , "13",       "ro",            "rum",                 "34",                    30235  ),
    ("Russian"                    , "27",       "ru",            "rus",                 "35",                    30236  ),
    ("Serbian"                    , "36",       "sr",            "scc",                 "36",                    30237  ),
    ("Slovak"                     , "37",       "sk",            "slo",                 "37",                    30238  ),
    ("Slovenian"                  , "1",        "sl",            "slv",                 "38",                    30239  ),
    ("Spanish"                    , "28",       "es",            "spa",                 "39",                    30240  ),
    ("Swedish"                    , "25",       "sv",            "swe",                 "40",                    30242  ),
    ("Thai"                       , "0",        "th",            "tha",                 "41",                    30243  ),
    ("Turkish"                    , "30",       "tr",            "tur",                 "42",                    30244  ),
    ("Ukrainian"                  , "46",       "uk",            "ukr",                 "43",                    30245  ),
    ("Vietnamese"                 , "51",       "vi",            "vie",                 "44",                    30246  ),
    ("BosnianLatin"               , "10",       "bs",            "bos",                 "100",                   30204  ),
    ("Farsi"                      , "52",       "fa",            "per",                 "13",                    30247  ),
    ("English (US)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("English (UK)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("Portuguese (Brazilian)"     , "48",       "pt-br",         "pob",                 "100",                   30234  ),
    ("Portuguese (Brazil)"        , "48",       "pb",            "pob",                 "33",                    30234  ),
    ("Portuguese-BR"              , "48",       "pb",            "pob",                 "33",                    30234  ),
    ("Brazilian"                  , "48",       "pb",            "pob",                 "33",                    30234  ),
    ("Español (Latinoamérica)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español (España)"           , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Spanish (Latin America)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español"                    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("SerbianLatin"               , "36",       "sr",            "scc",                 "100",                   30237  ),
    ("Spanish (Spain)"            , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Chinese (Traditional)"      , "17",       "zh",            "chi",                 "100",                   30207  ),
    ("Chinese (Simplified)"       , "17",       "zh",            "chi",                 "100",                   30207  ) )


REGEX_EXPRESSIONS = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09
                      '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                      '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                      '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                      'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',              # Season 01 - Episode 02
                      'Season ([0-9]+) Episode ([0-9]+)[^\\/]*',                # Season 01 Episode 02
                      '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                      '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                #foo_[s01]_[e01]
                      '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',       #foo, s01e01, foo.s01.e01, foo.s01-e01
                      's([0-9]+)ep([0-9]+)[^\\/]*',                             #foo - s01ep03, foo - s1ep03
                      '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
                     ]

class Pause:
  def __init__(self):
    self.player_state = xbmc.getCondVisibility('Player.Paused')

  def restore(self):
    if self.player_state != xbmc.getCondVisibility('Player.Paused'):
      xbmc.Player().pause()

  def pause(self):
    if not xbmc.getCondVisibility('Player.Paused'):
      xbmc.Player().pause()

def log(module,msg):
  xbmc.log((u"### [%s-%s] - %s" % (__scriptname__,module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def regex_tvshow(compare, file, sub = ""):
  sub_info = ""
  tvshow = 0

  for regex in REGEX_EXPRESSIONS:
    response_file = re.findall(regex, file)
    if len(response_file) > 0 :
      log( __name__ , "Regex File Se: %s, Ep: %s," % (str(response_file[0][0]),str(response_file[0][1]),) )
      tvshow = 1
      if not compare :
        title = re.split(regex, file)[0]
        for char in ['[', ']', '_', '(', ')','.','-']:
           title = title.replace(char, ' ')
        if title.endswith(" "): title = title[:-1]
        return title,response_file[0][0], response_file[0][1]
      else:
        break

  if (tvshow == 1):
    for regex in regex_expressions:
      response_sub = re.findall(regex, sub)
      if len(response_sub) > 0 :
        try :
          sub_info = "Regex Subtitle Ep: %s," % (str(response_sub[0][1]),)
          if (int(response_sub[0][1]) == int(response_file[0][1])):
            return True
        except: pass
    return False
  if compare :
    return True
  else:
    return "","",""

def languageTranslate(lang, lang_from, lang_to):
  for x in LANGUAGES:
    if lang == x[lang_from] :
      return x[lang_to]

def pause():
  if not xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()
    return True
  else:
    return False

def unpause():
  if xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()

def rem_files(directory):
  try:
    if xbmcvfs.exists(directory):
      shutil.rmtree(directory)
  except:
    pass

  if not xbmcvfs.exists(directory):
    os.makedirs(directory)

def copy_files( subtitle_file, file_path ):
  subtitle_set = False
  try:
    log( __name__ ,"vfs module copy %s -> %s" % (subtitle_file, file_path))
    xbmcvfs.copy(subtitle_file, file_path)
    subtitle_set = True
  except :
    dialog = xbmcgui.Dialog()
    selected = dialog.yesno( __scriptname__ , _( 748 ), _( 750 ),"" )
    if selected == 1:
      file_path = subtitle_file
      subtitle_set = True

  return subtitle_set, file_path

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def hashFile(file_path, rar):
    if rar:
      return OpensubtitlesHashRar(file_path)

    log( __name__,"Hash Standard file")
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)
    f = xbmcvfs.File(file_path)

    filesize = f.size()
    hash = filesize

    if filesize < 65536 * 2:
        return "SizeError"

    buffer = f.read(65536)
    f.seek(max(0,filesize-65536),0)
    buffer += f.read(65536)
    f.close()
    for x in range((65536/bytesize)*2):
        size = x*bytesize
        (l_value,)= struct.unpack(longlongformat, buffer[size:size+bytesize])
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF

    returnHash = "%016x" % hash
    return filesize,returnHash


def OpensubtitlesHashRar(firsrarfile):
    log( __name__,"Hash Rar file")
    f = xbmcvfs.File(firsrarfile)
    a=f.read(4)
    if a!='Rar!':
        raise Exception('ERROR: This is not rar file.')
    seek=0
    for i in range(4):
        f.seek(max(0,seek),0)
        a=f.read(100)
        type,flag,size=struct.unpack( '<BHH', a[2:2+5])
        if 0x74==type:
            if 0x30!=struct.unpack( '<B', a[25:25+1])[0]:
                raise Exception('Bad compression method! Work only for "store".')
            s_partiizebodystart=seek+size
            s_partiizebody,s_unpacksize=struct.unpack( '<II', a[7:7+2*4])
            if (flag & 0x0100):
                s_unpacksize=(unpack( '<I', a[36:36+4])[0] <<32 )+s_unpacksize
                log( __name__ , 'Hash untested for files biger that 2gb. May work or may generate bad hash.')
            lastrarfile=getlastsplit(firsrarfile,(s_unpacksize-1)/s_partiizebody)
            hash=addfilehash(firsrarfile,s_unpacksize,s_partiizebodystart)
            hash=addfilehash(lastrarfile,hash,(s_unpacksize%s_partiizebody)+s_partiizebodystart-65536)
            f.close()
            return (s_unpacksize,"%016x" % hash )
        seek+=size
    raise Exception('ERROR: Not Body part in rar file.')

def getlastsplit(firsrarfile,x):
    if firsrarfile[-3:]=='001':
        return firsrarfile[:-3]+('%03d' %(x+1))
    if firsrarfile[-11:-6]=='.part':
        return firsrarfile[0:-6]+('%02d' % (x+1))+firsrarfile[-4:]
    if firsrarfile[-10:-5]=='.part':
        return firsrarfile[0:-5]+('%1d' % (x+1))+firsrarfile[-4:]
    return firsrarfile[0:-2]+('%02d' %(x-1) )

def addfilehash(name,hash,seek):
    f = xbmcvfs.File(name)
    f.seek(max(0,seek),0)
    for i in range(8192):
        hash+=struct.unpack('<q', f.read(8))[0]
        hash =hash & 0xffffffffffffffff
    f.close()
    return hash

def hashFileMD5(file_path, buff_size=1048576):
    # calculate MD5 key from file
    f = xbmcvfs.File(file_path)
    if f.size() < buff_size:
        return None
    f.seek(0,0)
    buff = f.read(buff_size)    # size=1M
    f.close()
    # calculate MD5 key from file
    m = md5();
    m.update(buff);
    return m.hexdigest()

def getShowId():
    try:
      playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
      playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
      tvshowid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
      tvshowid = json.loads(xbmc.executeJSONRPC (tvshowid_query))['result']['item']['tvshowid']
      tvdbid_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
      return json.loads(xbmc.executeJSONRPC (tvdbid_query))['result']['tvshowdetails']['imdbnumber']
    except:
      log( __name__ ," Failed to find TVDBid in database")

########NEW FILE########
