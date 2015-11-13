__FILENAME__ = periscope-nautilus-testcase
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public
#    License as published by the Free Software Foundation; either
#    version 2 of the License, or (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import unittest
import MenuProvider

class MenuProviderTestCase(unittest.TestCase):

	def runTest(self):
		try:
			dir(MenuProvider)
			mp = MenuProvider.DownloadSubtitles()
			mp.notify([{"filename": "a"}], [])
		except Exception, e:
			print e
			self.fail("Could not notify")
		
if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = periscope-nautilus
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#   Ported to GTK3/PyGI with multiprocessing by Shock <shock@corezero.net>
#
#    periscope is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public
#    License as published by the Free Software Foundation; either
#    version 2 of the License, or (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gi.repository import Gtk, Gio, GObject, Nautilus
from multiprocessing import Process, Queue
from Queue import Empty
from time import sleep
# import urllib2
import os
import gettext
# import logging
import xdg.BaseDirectory as bd # required
try:
    from gi.repository import Notify
except ImportError:
    pass

import periscope

# i18n stuff
gettext.install('periscope-nautilus')

class DownloadSubtitles(GObject.GObject, Nautilus.MenuProvider):
    ''' This class is to be used in Nautilus with the python-nautilus extension. 
    It provides a context menu on video file to download subtitles.'''
    def __init__(self):
        if Notify:
            Notify.init("periscope subtitles downloader")
        self.cache_folder = os.path.join(bd.xdg_config_home, "periscope")

    def get_file_items(self, window, files):
        # Keep only the files we want (right type and file)
        files = [ f for f in files if self.is_valid(f)]
        if len(files) == 0:
            return

        item = Nautilus.MenuItem(name='Nautilus::download_subtitles',
                                 label=_('Find subtitles for this video'),
                                 tip=_('Download subtitles for this video'),
                                 icon=Gtk.STOCK_FIND_AND_REPLACE)
        item.connect('activate', self.menu_activate_cb, files)
        return item,

    def menu_activate_cb(self, menu, files):
        #List the valid files
        videos = [f for f in files if not f.is_gone() and self.is_valid(f)]
        # Get the file paths from gvfs so we support non local file systems, yay!
        g = Gio.Vfs.get_default()
        videos = map(lambda f: g.get_file_for_uri(f.get_uri()).get_path(), videos)

        # Download the subtitles in a new process and get the results in this process via a Queue
        queue = Queue()
        invoker = PeriscopeInvoker(videos, self.cache_folder, queue)
        invoker.start()
        result = []
        while not result:
            try:
                result = queue.get_nowait()
            except Empty:
                pass
            finally:
                Gtk.main_iteration_do(False) # a blocking version with timeout would have been nice
                sleep(0.01)
        [found, notfound] = result
        self.notify(found, notfound)
        invoker.join()

    def is_valid(self, f):
        return f.get_mime_type() in periscope.SUPPORTED_FORMATS and (f.get_uri_scheme() == 'file' or f.get_uri_scheme() == 'smb')

    def notify(self, found, notfound):
        ''' Use Notify to warn the user that subtitles have been downloaded'''
        if Notify:
            title = "periscope found %s out of %s subtitles" %(len(found), len(found) + len(notfound))
            if len(notfound) > 0:
                msg = _("Could not find: \n")
                filenames = [os.path.basename(f["filename"]) for f in notfound]
                msg += "\n".join(filenames)
                msg += "\n"

            if len(found) > 0:
                msg = _("Found: \n")
                filenames = [os.path.basename(f["filename"]) + " ("+f['lang']+")" for f in found]
                msg += "\n".join(filenames)

            n = Notify.Notification.new(title, msg, Gtk.STOCK_FIND_AND_REPLACE)
            n.set_timeout(Notify.EXPIRES_DEFAULT)
            n.show()
        else:
            pass

class PeriscopeInvoker(Process):
    ''' Thread that will call persicope in the background'''
    def __init__(self, filenames, cache_folder, queue):
        self.filenames = filenames
        self.found = []
        self.notfound = []
        self.cache_folder = cache_folder
        self.queue = queue
        Process.__init__(self)

    def run(self):
        subdl = periscope.Periscope(self.cache_folder)
        print "prefered languages: %s" %subdl.preferedLanguages
        for filename in self.filenames:
            subtitle = subdl.downloadSubtitle(filename, subdl.preferedLanguages)
            if subtitle:
                del subtitle["plugin"] # multiprocessing Queue won't be able to pickle this and will bark
                self.found.append(subtitle)
            else:
                self.notfound.append({"filename": filename })
        self.queue.put([self.found, self.notfound])
        self.queue.close() # we won't have anything more to transmit to the parent process

########NEW FILE########
__FILENAME__ = periscope
#!/usr/bin/python
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

import getopt
import sys
import os
import threading
import logging
from Queue import Queue

import traceback
import ConfigParser

log = logging.getLogger(__name__)

try:
    import xdg.BaseDirectory as bd
    is_local = True
except ImportError:
    is_local = False

import plugins
import version
import locale

SUPPORTED_FORMATS = 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4'
VERSION = version.VERSION

class Periscope:
    ''' Main Periscope class'''

    def __init__(self, cache_folder=None):
        self.config = ConfigParser.SafeConfigParser({"lang": "", "plugins" : "", "lang-in-name": "no" })
        self.config_file = os.path.join(cache_folder, "config")
        self.cache_path = cache_folder
        if not os.path.exists(self.config_file):
            folder = os.path.dirname(self.config_file)
            if not os.path.exists(folder):
                log.info("Creating folder %s" %folder)
                os.mkdir(folder)
                log.info("Creating config file")
                configfile = open(self.config_file, "w")
                self.config.write(configfile)
                configfile.close()
        else:
            #Load it
            self.config.read(self.config_file)

        self.pluginNames = self.get_preferedPlugins()
        self._preferedLanguages = None

    def get_preferedLanguages(self):
        ''' Get the prefered language from the config file '''
        configLang = self.config.get("DEFAULT", "lang")
        log.info("lang read from config: " + configLang)
        if configLang == "":
            try :
                return [locale.getdefaultlocale()[0][:2]]
            except :
                return ["en"]
        else:
            return map(lambda x : x.strip(), configLang.split(","))

    def set_preferedLanguages(self, langs):
        ''' Update the config file to set the prefered language '''
        self.config.set("DEFAULT", "lang", ",".join(langs))
        configfile = open(self.config_file, "w")
        self.config.write(configfile)
        configfile.close()

    def get_preferedPlugins(self):
        ''' Get the prefered plugins from the config file '''
        configPlugins = self.config.get("DEFAULT", "plugins")
        if not configPlugins or configPlugins.strip() == "":
            return self.listExistingPlugins()
        else :
            log.info("plugins read from config : " + configPlugins)
            return map(lambda x : x.strip(), configPlugins.split(","))

    def set_preferedPlugins(self, newPlugins):
        ''' Update the config file to set the prefered plugins) '''
        self.config.set("DEFAULT", "plugins", ",".join(newPlugins))
        configfile = open(self.config_file, "w")
        self.config.write(configfile)
        configfile.close()

    def get_preferedNaming(self):
        ''' Get the prefered naming convention from the config file '''
        try:
            lang_in_name = self.config.getboolean("DEFAULT", "lang-in-name")
            log.info("lang-in-name read from config: " + str(lang_in_name))
        except ValueError:
            lang_in_name = False
        return lang_in_name

    def set_preferedNaming(self, lang_in_name):
        ''' Update the config file to set the prefered naming convention '''
        self.config.set('DEFAULT', 'lang-in-name', 'yes' if lang_in_name else 'no')
        configfile = open(self.config_file, "w")
        self.config.write(configfile)
        configfile.close()

    # Getter/setter for the property preferedLanguages
    preferedLanguages = property(get_preferedLanguages, set_preferedLanguages)
    preferedPlugins = property(get_preferedPlugins, set_preferedPlugins)
    preferedNaming = property(get_preferedNaming, set_preferedNaming)

    def deactivatePlugin(self, pluginName):
        ''' Remove a plugin from the list '''
        self.pluginNames -= pluginName
        self.set_preferedPlugins(self.pluginNames)

    def activatePlugin(self, pluginName):
        ''' Activate a plugin '''
        if pluginName not in self.listExistingPlugins():
            raise ImportError("No plugin with the name %s exists" %pluginName)
        self.pluginNames += pluginName
        self.set_preferedPlugins(self.pluginNames)

    def listActivePlugins(self):
        ''' Return all active plugins '''
        return self.pluginNames

    def listExistingPlugins(self):
        ''' List all possible plugins from the plugin folder '''
        return map(lambda x : x.__name__, plugins.SubtitleDatabase.SubtitleDB.__subclasses__())

    def listSubtitles(self, filename, langs=None):
        '''Searches subtitles within the active plugins and returns all found matching subtitles ordered by language then by plugin.'''
        #if not os.path.isfile(filename):
            #raise InvalidFileException(filename, "does not exist")

        log.info("Searching subtitles for %s with langs %s" %(filename, langs))
        subtitles = []
        q = Queue()
        for name in self.pluginNames:
            try :
                plugin = getattr(plugins, name)(self.config, self.cache_path)
                log.info("Searching on %s " %plugin.__class__.__name__)
                thread = threading.Thread(target=plugin.searchInThread, args=(q, filename, langs))
                thread.start()
            except ImportError :
                log.error("Plugin %s is not a valid plugin name. Skipping it.")

        # Get data from the queue and wait till we have a result
        for name in self.pluginNames:
            subs = q.get(True)
            if subs and len(subs) > 0:
                if not langs:
                    subtitles += subs
                else:
                    for sub in subs:
                        if sub["lang"] in langs:
                            subtitles += [sub] # Add an array with just that sub

        if len(subtitles) == 0:
            return []
        return subtitles    
    
    def selectBestSubtitle(self, subtitles, langs=["en"], interactive=False):
        '''Searches subtitles from plugins and returns the best subtitles from all candidates'''
        if not subtitles:
            return None
        subtitles = self.__orderSubtitles__(subtitles)

        if not interactive:
            for l in langs:
                if subtitles.has_key(l) and len(subtitles[l]):
                    return subtitles[l][0]
        else:
            interactive_subtitles = []
            for l in langs:
                if subtitles.has_key(l) and len(subtitles[l]):
                    for sub in subtitles[l]:
                        interactive_subtitles.append(sub)
            for i in range(len(interactive_subtitles)):
                sub = interactive_subtitles[i]
                print "[%d]: %s" % (i, sub["release"])
            sub = None
            while not sub:
                try:
                    sub = interactive_subtitles[int(raw_input("Please select a subtitle: "))]
                    if sub:
                        return sub
                except IndexError:
                    print "Invalid index"
                except ValueError:
                    print "Invalid value"

        return None #Could not find subtitles

    def downloadSubtitle(self, filename, langs=None, interactive=False):
        ''' Takes a filename and a language and creates ONE subtitle through plugins if interactive == True asks before downloading'''
        subtitles = self.listSubtitles(filename, langs)
        if subtitles:
            log.debug("All subtitles: ")
            log.debug(subtitles)    
            return self.attemptDownloadSubtitle(subtitles, langs, interactive)
        else:
            return None
        
        
    def attemptDownloadSubtitle(self, subtitles, langs, interactive=False):
        subtitle = self.selectBestSubtitle(subtitles, langs, interactive)
        if subtitle:
            log.info("Trying to download subtitle: %s" %subtitle['link'])
            #Download the subtitle
            try:
                subpath = subtitle["plugin"].createFile(subtitle)
                if subpath:
                    subtitle["subtitlepath"] = subpath
                    return subtitle
                else:
                    # throw exception to remove it
                    raise Exception("Not downloaded")
            except Exception as inst:
                # Could not download that subtitle, remove it
                log.warn("Subtitle %s could not be downloaded, trying the next on the list" %subtitle['link'])
                etype = sys.exc_info()[0]
                evalue = sys.exc_info()[1]
                etb = traceback.extract_tb(sys.exc_info()[2])
                log.error("Type[%s], Message [%s], Traceback[%s]" % (etype,evalue,etb))
                subtitles.remove(subtitle)
                return self.attemptDownloadSubtitle(subtitles, langs)
        else :
            log.error("No subtitles could be chosen.")
            return None

    def guessFileData(self, filename):
        subdb = plugins.SubtitleDatabase.SubtitleDB(None)
        return subdb.guessFileData(filename)

    def __orderSubtitles__(self, subs):
        '''reorders the subtitles according to the languages then the website'''
        try:
            from collections import defaultdict
            subtitles = defaultdict(list) #Order matters (order of plugin and result from plugins)
            for s in subs:
                subtitles[s["lang"]].append(s)
            return subtitles
        except ImportError, e: #Don't use Python 2.5
            subtitles = {}
            for s in subs:
                # return subtitles[s["lang"]], if it does not exist, set it to [] and return it, then append the subtitle
                subtitles.setdefault(s["lang"], []).append(s)
            return subtitles

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
		except urllib2.HTTPError as inst:
			logging.info("Error : %s - %s" %(searchurl, inst))
			return sublinks
		except urllib2.URLError as inst:
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
			lang = self.getLG(langs_html.contents[0].strip().replace('&nbsp;', ''))
			#logging.debug("[Addic7ed] Language : %s - lang : %s" %(langs_html, lang))
			
			statusTD = langs_html.findNext("td")
			status = statusTD.find("strong").string.strip()

			# take the last one (most updated if it exists)
			links = statusTD.findNext("td").findAll("a")
			link = "%s%s"%(self.host,links[len(links)-1]["href"])
			
			#logging.debug("%s - match : %s - lang : %s" %(status == "Completed", subteams.issubset(teams), (not langs or lang in langs)))
			if status == "Completed" and subteams.issubset(teams) and (not langs or lang in langs) :
				result = {}
				result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("_", ".").title(), int(season), int(episode), '.'.join(subteams)
)
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
__FILENAME__ = LegendasTV
# -*- coding: utf-8 -*-

#    This file is part of periscope.
#
#     periscope is free software; you can redistribute it and/or modify
#     it under the terms of the GNU Lesser General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     periscope is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public License
#     along with periscope; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA    02110-1301    USA
#
#    Original version based on XBMC Legendas.tv plugin: 
#    https://github.com/amet/script.xbmc.subtitles/blob/eden/script.xbmc.subtitles/resources/lib/services/LegendasTV/service.py
#
#    Initial version coded by Gastao Bandeira
#    Bug fix and minor changes by Rafael Torres
#

import xml.dom.minidom
import traceback
import hashlib
import StringIO
import zipfile
import shutil
import ConfigParser

import cookielib, urllib2, urllib, sys, re, os, webbrowser, time, unicodedata, logging
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from htmlentitydefs import name2codepoint as n2cp

#from utilities import log

import SubtitleDatabase
import subprocess

log = logging.getLogger(__name__)

class LegendasTV(SubtitleDatabase.SubtitleDB):
    url = "http://legendas.tv"
    site_name = "LegendasTV"
    user_agent = "LegendasTV/1.0 (periscope/0.1; http://code.google.com/p/periscope)"

    def __init__(self, config, cache_folder_path ):
        super(LegendasTV, self).__init__(None)
        self.tvshowRegex = re.compile('(?P<show>.*)S(?P<season>[0-9]{2})E(?P<episode>[0-9]{2}).(?P<teams>.*)', re.IGNORECASE)
        self.tvshowRegex2 = re.compile('(?P<show>.*).(?P<season>[0-9]{1,2})x(?P<episode>[0-9]{1,2}).(?P<teams>.*)', re.IGNORECASE)
        self.movieRegex = re.compile('(?P<movie>.*)[\_\.|\[|\(| ]{1}(?P<year>(?:(?:19|20)[0-9]{2}))(?P<teams>.*)', re.IGNORECASE)
        self.user = None
        self.password = None
        self.unrar = None
        self.sub_ext = None
        try:
            self.user = config.get("LegendasTV","user")
            self.password = config.get("LegendasTV","pass")
            self.unrar = config.get("LegendasTV","unrarpath")
            self.sub_ext = config.get("LegendasTV","supportedSubtitleExtensions")
        except ConfigParser.NoSectionError:
            config.add_section("LegendasTV")
            config.set("LegendasTV", "user", "")
            config.set("LegendasTV", "pass", "")
            config.set("LegendasTV", "unrarpath", "")
            config.set("LegendasTV", "supportedSubtitleExtensions", "")
            config_file = os.path.join(cache_folder_path, "config")
            configfile = open(config_file, "w")
            config.write(configfile)
            configfile.close()
            pass

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished
        languages and it will query the subtitles source '''
        if not self.user or self.user == "":
            log.error("LegendasTV requires a personnal username/password. Set one up in your ~/.config/periscope/config file")
            return []
        arquivo = self.getFileName(filepath)
        dados = {}
        dados = self.guessFileData(arquivo)
        log.debug(dados)
        if dados['type'] == 'tvshow':
            subtitles = self.LegendasTVSeries(filepath,dados['name'], str(dados['season']), str(dados['episode']),langs)
        elif(dados['type'] == 'movie'):
            subtitles =  self.LegendasTVMovies(filepath,dados['name'],dados['year'],langs)
        else:
            subtitles =  self.LegendasTVMovies(filepath,dados['name'],'',langs)
        return subtitles

    def getFileName(self, filepath):
        filename = os.path.basename(filepath)
        if filename.endswith(('.avi', '.wmv', '.mov', '.mp4', '.mpeg', '.mpg', '.mkv')):
            fname = filename.rsplit('.', 1)[0]
        else:
            fname = filename
        return fname

    def guessFileData(self, filename):
        filename = unicode(self.getFileName(filename).lower())
        matches_tvshow = self.tvshowRegex.match(filename)
        if matches_tvshow: # It looks like a tv show
            (tvshow, season, episode, teams) = matches_tvshow.groups()
            tvshow = tvshow.replace(".", " ").strip()
            tvshow = tvshow.replace("_", " ").strip()
            teams = teams.split('.')
            if len(teams) ==1:
                teams = teams[0].split('_')
            return {'type' : 'tvshow', 'name' : tvshow.strip(), 'season' : int(season), 'episode' : int(episode), 'teams' : teams}
        else:
            matches_tvshow = self.tvshowRegex2.match(filename)
            if matches_tvshow:
                (tvshow, season, episode, teams) = matches_tvshow.groups()
                tvshow = tvshow.replace(".", " ").strip()
                tvshow = tvshow.replace("_", " ").strip()
                teams = teams.split('.')
                if len(teams) ==1:
                    teams = teams[0].split('_')
                return {'type' : 'tvshow', 'name' : tvshow.strip(), 'season' : int(season), 'episode' : int(episode), 'teams' : teams}
            else:
                matches_movie = self.movieRegex.match(filename)
                if matches_movie:
                    (movie, year, teams) = matches_movie.groups()
                    movie = movie.replace(".", " ").strip()
                    movie = movie.replace("_", " ").strip()
                    teams = teams.split('.')
                    if len(teams) ==1:
                        teams = teams[0].split('_')
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


    def LegendasTVLogin(self):
        '''Function for login on LegendasTV using username and password from config file'''
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('User-agent', ('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.1.4322)'))]
        urllib2.install_opener(opener)
        username = self.user
        password = self.password
        login_data = urllib.urlencode({'txtLogin':username,'txtSenha':password})
        request = urllib2.Request(self.url+'/login_verificar.php',login_data)
        response = urllib2.urlopen(request).read()

    def createFile(self, subtitle):
        '''pass the ID of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtfilename = videofilename.rsplit(".", 1)[0] + '.srt'
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def extractFile(self,fname,extract_path,extractedFiles=[]):
        ''' Uncompress the subtitle '''
        if fname in extractedFiles:
            return
        if zipfile.is_zipfile(fname):
            log.debug("Unzipping file " + fname)
            zf = zipfile.ZipFile(fname, "r")
            zf.extractall(extract_path)
            zf.close()
        elif fname.endswith('.rar'):
            try:
                '''Try to use unrar from folder in config file'''
                log.debug("Extracting file " + fname)
                subprocess.call([self.unrar, 'e','-y','-inul',fname, extract_path])
            except OSError as e:
                log.error("OSError [%d]: %s at %s" % (e.errno, e.strerror, e.filename))
            except:
                log.error("General error:" + str(sys.exc_info()[0]))
        else:
            raise Exception("Unknown file format: " + fname)
        
        extractedFiles.append(fname)    

        fs_encoding = sys.getfilesystemencoding()
        for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".zip",".rar"]:
                    self.extractFile(os.path.join(root, f),extract_path,extractedFiles)

    def downloadFile(self, url, srtfilename):
        ''' Downloads the given url to the given filename '''
        subtitle = ""
        extract_path = os.path.join(srtfilename.replace(self.getFileName(srtfilename),''), str(url))

        url_request = self.url+'/info.php?d='+url+'&c=1'
        request =  urllib2.Request(url_request)
        response = urllib2.urlopen(request)
        ltv_sub = response.read()
        os.makedirs(extract_path)
        fname = os.path.join(extract_path,str(url))
        if response.info().get('Content-Type').__contains__('rar'):
            fname += '.rar'
        else:
            fname += '.zip'
        f = open(fname,'wb')
        f.write(ltv_sub)
        f.close()

        self.extractFile(fname,extract_path)

        legendas_tmp = []
        fs_encoding = sys.getfilesystemencoding()
        for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
            for file in files:
                dirfile = os.path.join(root, file)
                ext = os.path.splitext(dirfile)[1][1:].lower()
                log.debug("file [%s] extension[%s]" % (file,ext))
                if ext in self.sub_ext:
                    log.debug("adding " + dirfile)
                    legendas_tmp.append(dirfile)

        if len(legendas_tmp) == 0:
            shutil.rmtree(extract_path)
            raise Exception('Could not find any subtitle')
        
        '''Verify the best subtitle in case of a pack for multiples releases'''
        legenda_retorno = self.CompareSubtitle(srtfilename,legendas_tmp)
        log.debug("Renaming [%s] to [%s] " % (os.path.join(extract_path,legenda_retorno),srtfilename))
        shutil.move(os.path.join(extract_path,legenda_retorno),srtfilename)
        shutil.rmtree(extract_path)



    def CompareSubtitle(self,releaseFile,subtitleList):
        '''Verify the best subtitle in case of a pack for multiples releases'''
        nameSplit = releaseFile.rsplit(".", 1)[0].split(".")
        if len(nameSplit) == 1:
            nameSplit = nameSplit[0].split("_")
        if len(nameSplit) == 1:
            nameSplit = nameSplit[0].split(" ")
        bestMatch = ''
        bestMatchCount = 0
        tempCount = 0
        for subtitle in subtitleList:
            nameSplitTemp = self.getFileName(subtitle).rsplit(".", 1)[0].split(".")
            if len(nameSplitTemp) == 1:
                nameSplitTemp = nameSplitTemp[0].split("_")
            if len(nameSplitTemp) == 1:
                nameSplitTemp = nameSplitTemp[0].split(" ")
            for nameTemp in nameSplit:
                if nameTemp in nameSplitTemp:
                    tempCount = tempCount+1
            if tempCount >= bestMatchCount:
                if tempCount == bestMatchCount:
                    if len(self.getFileName(subtitle)) < len(bestMatch):
                        bestMatch = self.getFileName(subtitle)
                        bestMatchCount = tempCount
                else:
                    bestMatch = self.getFileName(subtitle)
                    bestMatchCount = tempCount
            tempCount=0

        return bestMatch

    def LegendasTVMovies(self, file_original_path, title, year, langs):

        log.debug('movie')

        self.LegendasTVLogin()

        # Initiating variables and languages.
        subtitles, sub1 = [], []

        if len(langs) > 1:
            langCode = '99'
        else:
            if langs[0] == 'pt-br':
                langCode = '1'
            if langs[0] == 'pt':
                langCode = '10'
            if langs[0] == 'es':
                langCode = '3'
            
       
        log.debug('Search using file name as release with max of 50 characters')
        # Encodes the first search string using the original movie title, and download it.
        search_string = self.getFileName(file_original_path)[:50]
        search_dict = {'txtLegenda':search_string,'selTipo':'1','int_idioma':langCode}
        search_data = urllib.urlencode(search_dict)
        request = urllib2.Request(self.url+'/index.php?opcao=buscarlegenda',search_data)
        response = self.to_unicode_or_bust(urllib2.urlopen(request).read())


        # If no subtitles with the original name are found, try the parsed title.
        if response.__contains__('Nenhuma legenda foi encontrada') and search_string != title:
            log.debug('No subtitles found using the original file name, using title instead.')
            search_string = self.CleanLTVTitle(title)
            if len(search_string) < 3: search_string = search_string + year
            search_dict = {'txtLegenda':search_string,'selTipo':'1','int_idioma':langCode}
            search_data = urllib.urlencode(search_dict)
            request = urllib2.Request(self.url+'/index.php?opcao=buscarlegenda',search_data)
            response = self.to_unicode_or_bust(urllib2.urlopen(request).read())

        # Retrieves the number of pages.
        pages = re.findall("<a class=\"paginacao\" href=",response)
        if pages: pages = len(pages)+1
        else: pages = 1

        # Download all pages content.
        for x in range(pages):
            if x:
                html = urllib2.urlopen(self.url+'/index.php?opcao=buscarlegenda&pagina='+str(x+1)).read()
                response = response + self.to_unicode_or_bust(html)

        # Parse all content to BeautifulSoup
        soup = BeautifulSoup(response)
        td_results =  soup.findAll('td',{'id':'conteudodest'})
        for td in td_results:
            span_results = td.findAll('span')
            for span in span_results:
                if span.attrs == [('class', 'brls')]:
                    continue
                td = span.find('td',{'class':'mais'})

                # Release name of the subtitle file.
                release = self.Uconvert(td.parent.parent.find('span',{'class':'brls'}).contents[0])

                # This is the download ID for the subtitle.
                download_id = re.search('[a-z0-9]{32}',td.parent.parent.attrs[1][1]).group(0)

                # Find the language of the subtitle extracting it from a image name,
                # and convert it to the OpenSubtitles format.
                ltv_lang = re.findall("images/flag_([^.]*).gif",span.findAll('td')[4].contents[0].attrs[0][1])

                if ltv_lang: ltv_lang = ltv_lang[0]
                if ltv_lang == "br": ltv_lang = "pt-br"
                if ltv_lang == "us": ltv_lang = "en"
                if ltv_lang == "pt": ltv_lang = "pt"
                if ltv_lang == "es": ltv_lang = "es"

                sub1.append( { "release" : release,"lang" : ltv_lang, "link" : download_id, "page" : self.url} )

        return sub1

    def LegendasTVSeries(self,file_original_path,tvshow, season, episode,langs):

        self.LegendasTVLogin()

    # Initiating variables and languages.
        subtitles, sub1, sub2, sub3, PartialSubtitles = [], [], [], [], []

        if len(langs) > 1:
            langCode = '99'
        else:
            if langs[0] == 'pt-br':
                langCode = '1'
            if langs[0] == 'pt':
                langCode = '10'
            if langs[0] == 'es':
                langCode = '3'


    # Formating the season to double digit format
        if int(season) < 10: ss = "0"+season
        else: ss = season
        if int(episode) < 10: ee = "0"+episode
        else: ee = episode

    # Setting up the search string; the original tvshow name is preferable.
    # If the tvshow name lenght is less than 3 characters, append the year to the search.

        search_string = self.getFileName(file_original_path)[:50]

        # Doing the search and parsing the results to BeautifulSoup
        search_dict = {'txtLegenda':search_string,'selTipo':'1','int_idioma':langCode}
        search_data = urllib.urlencode(search_dict)
        request = urllib2.Request(self.url+'/index.php?opcao=buscarlegenda',search_data)
        response = self.to_unicode_or_bust(urllib2.urlopen(request).read())

        # If no subtitles with the original name are found, try the parsed title.
        if response.__contains__('Nenhuma legenda foi encontrada'):
            #log( __name__ ,u" No subtitles found using the original title, using title instead.")
            search_string = tvshow + " " +"S"+ss+"E"+ee
            search_dict = {'txtLegenda':search_string,'selTipo':'1','int_idioma':langCode}
            search_data = urllib.urlencode(search_dict)
            request = urllib2.Request(self.url+'/index.php?opcao=buscarlegenda',search_data)
            response = self.to_unicode_or_bust(urllib2.urlopen(request).read())

        page = self.to_unicode_or_bust(response)
        soup = BeautifulSoup(page)

        span_results = soup.find('td',{'id':'conteudodest'}).findAll('span')

        for span in span_results:
        # Jumping season packs
            if span.attrs == [('class', 'brls')]:
                continue
            td = span.find('td',{'class':'mais'})

            # Translated and original titles from LTV, the LTV season number and the
            # scene release name of the subtitle. If a movie is retrieved, the re.findall
            # will raise an exception and will continue to the next loop.
            reResult = re.findall("(.*) - [0-9]*",self.CleanLTVTitle(td.contents[2]))
            if reResult: ltv_title = reResult[0]
            else:
                ltv_title = self.CleanLTVTitle(td.contents[2])

            reResult = re.findall("(.*) - ([0-9]*)",self.CleanLTVTitle(td.contents[0].contents[0]))
            if reResult: ltv_original_title, ltv_season = reResult[0]
            else:
                ltv_original_title = self.CleanLTVTitle(td.contents[0].contents[0])
                ltv_season = 0

            release = td.parent.parent.find('span',{'class':'brls'}).contents[0]
            if not ltv_season:
                reResult = re.findall("[Ss]([0-9]+)[Ee][0-9]+",release)
                if reResult: ltv_season = re.sub("^0","",reResult[0])

            if not ltv_season: continue

            # This is the download ID for the subtitle.
            download_id = re.search('[a-z0-9]{32}',td.parent.parent.attrs[1][1]).group(0)

            # Find the language of the subtitle extracting it from a image name,
            # and convert it to the OpenSubtitles format.
            ltv_lang = re.findall("images/flag_([^.]*).gif",span.findAll('td')[4].contents[0].attrs[0][1])
            if ltv_lang: ltv_lang = ltv_lang[0]
            if ltv_lang == "br": ltv_lang = "pt-br"
            if ltv_lang == "us": ltv_lang = "en"
            if ltv_lang == "pt": ltv_lang = "pt"
            if ltv_lang == "es": ltv_lang = "es"

            # Compares the parsed and the LTV season number, then compares the retrieved titles from LTV
            # to those parsed or snatched by this service.
            # Each language is appended to a unique sequence.
            tvshow = self.CleanLTVTitle(tvshow)
            if int(ltv_season) == int(season):
                SubtitleResult = {"release" : release,"lang" : 'pt-br', "link" : download_id, "page" : self.url}
                if re.findall("^%s" % (tvshow),ltv_original_title) or self.comparetitle(ltv_title,tvshow) or self.comparetitle(ltv_original_title,original_tvshow):
                    sub1.append( SubtitleResult )
                else:
                    reResult = re.findall("[Ss][0-9]+[Ee]([0-9]+)",release)
                    if reResult: LTVEpisode = re.sub("^0","",reResult[0])
                    else: LTVEpisode = 0
                    if int(LTVEpisode) == int(episode):
                        PartialSubtitles.append( SubtitleResult )

        if not len(sub1): sub1.extend(PartialSubtitles)
        return sub1

    def chomp(self,s):
        s = re.sub("[ ]{2,20}"," ",s)
        a = re.compile("(\r|\n|^ | $|\'|\"|,|;|[(]|[)])")
        b = re.compile("(\t|-|:|\/)")
        s = b.sub(" ",s)
        s = re.sub("[ ]{2,20}"," ",s)
        s = a.sub("",s)
        return s

    def CleanLTVTitle(self,s):
        s = self.Uconvert(s)
        s = re.sub("[(]?[0-9]{4}[)]?$","",s)
        s = self.chomp(s)
        s = s.title()
        return s


    def shiftarticle(self,s):
        for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
            x = '^' + art + ' '
            y = ', ' + art
            if re.search(x, s):
                return re.sub(x, '', s) + y
        return s

    def unshiftarticle(self,s):
        for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
            x = ', ' + art + '$'
            y = art + ' '
            if re.search(x, s):
                return y + re.sub(x, '', s)
        return s

    def noarticle(self,s):
        for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
            x = '^' + art + ' '
            if re.search(x, s):
                return re.sub(x, '', s)
        return s

    def notag(self,s):
        return re.sub('<([^>]*)>', '', s)

    def compareyear(self,a, b):
        if int(b) == 0:
            return 1
        if abs(int(a) - int(b)) <= YEAR_MAX_ERROR:
            return 1
        else:
            return 0

    def comparetitle(self,a, b):
            if (a == b) or (self.noarticle(a) == self.noarticle(b)) or (a == self.noarticle(b)) or (self.noarticle(a) == b) or (a == self.shiftarticle(b)) or (self.shiftarticle(a) == b):
                return 1
            else:
                return 0


    def to_unicode_or_bust(self,obj, encoding='iso-8859-1'):
         if isinstance(obj, basestring):
             if not isinstance(obj, unicode):
                 obj = unicode(obj, encoding)
         return obj

    def substitute_entity(self,match):
        ent = match.group(3)
        if match.group(1) == "#":
            # decoding by number
            if match.group(2) == '':
                # number is in decimal
                return unichr(int(ent))
            elif match.group(2) == 'x':
                # number is in hex
                return unichr(int('0x'+ent, 16))
        else:
            # they were using a name
            cp = n2cp.get(ent)
            if cp: return unichr(cp)
            else: return match.group()

    def decode_htmlentities(self,string):
        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(self.substitute_entity, string)[0]

# This function tries to decode the string to Unicode, then tries to decode
# all HTML entities, anf finally normalize the string and convert it to ASCII.
    def Uconvert(self,obj):
        try:
            obj = self.to_unicode_or_bust(obj)
            obj = self.decode_htmlentities(obj)
            obj = unicodedata.normalize('NFKD', obj).encode('ascii','ignore')
            return obj
        except:return obj

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
        if os.path.isfile(filepath):
            filehash = self.hashFile(filepath)
            log.debug(filehash)
            size = os.path.getsize(filepath)
            fname = self.getFileName(filepath)
            return self.query(moviehash=filehash, langs=langs, bytesize=size, filename=fname)
        else:
            fname = self.getFileName(filepath)
            return self.query(langs=langs, filename=fname)
        
    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        self.downloadFile(suburl, srtbasefilename + ".srt.gz")
        f = gzip.open(srtbasefilename+".srt.gz")
        dump = open(srtbasefilename+".srt", "wb")
        dump.write(f.read())
        dump.close()
        f.close()
        os.remove(srtbasefilename+".srt.gz")
        return srtbasefilename+".srt"

    def query(self, filename, imdbID=None, moviehash=None, bytesize=None, langs=None):
        ''' Makes a query on opensubtitles and returns info about found subtitles.
            Note: if using moviehash, bytesize is required.    '''
        log.debug('query')
        #Prepare the search
        search = {}
        sublinks = []
        if moviehash: search['moviehash'] = moviehash
        if imdbID: search['imdbid'] = imdbID
        if bytesize: search['moviebytesize'] = str(bytesize)
        if langs: search['sublanguageid'] = ",".join([self.getLanguage(lang) for lang in langs])
        if len(search) == 0:
            log.debug("No search term, we'll use the filename")
            # Let's try to guess what to search:
            guessed_data = self.guessFileData(filename)
            search['query'] = guessed_data['name']
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
        sublinks += self.get_results(token, search)

        # Logout
        try:
            self.server.LogOut(token)
        except:
            log.error("Open subtitles could not be contacted for logout")
        socket.setdefaulttimeout(None)
        return sublinks
        
        
    def get_results(self, token, search):
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
                result["lang"] = self.getLG(r['SubLanguageID'])
                if search.has_key("query") : #We are using the guessed file name, let's remove some results
                    if r["MovieReleaseName"].startswith(self.filename):
                        sublinks.append(result)
                    else:
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
__FILENAME__ = Podnapisi
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

import zipfile, os, urllib2, urllib, traceback, logging 

from BeautifulSoup import BeautifulSoup

import SubtitleDatabase

log = logging.getLogger(__name__)

class Podnapisi(SubtitleDatabase.SubtitleDB):
    url = "http://www.podnapisi.net/"
    site_name = "Podnapisi"

    def __init__(self, config, cache_folder_path):
        super(Podnapisi, self).__init__({"sl" : "1", "en": "2", "no" : "3", "ko" :"4", "de" : "5", "is" : "6", "cs" : "7", "fr" : "8", "it" : "9", "bs" : "10", "ja" : "11", "ar" : "12", "ro" : "13", "es-ar" : "14", "hu" : "15", "el" : "16", "zh" : "17", "lt" : "19", "et" : "20", "lv" : "21", "he" : "22", "nl" : "23", "da" : "24", "sv" : "25", "pl" : "26", "ru" : "27", "es" : "28", "sq" : "29", "tr" : "30", "fi" : "31", "pt": "32", "bg" : "33", "mk" : "35", "sk" : "37", "hr" : "38", "zh" : "40", "hi": "42", "th" : "44", "uk": "46", "sr": "47", "pt-br" : "48", "ga": "49", "be": "50", "vi": "51", "fa": "52", "ca": "53", "id": "54"})
        
        #Note: Podnapisi uses two reference for latin serbian and cyrillic serbian (36 and 47). We'll add the 36 manually as cyrillic seems to be more used
        self.revertlangs["36"] = "sr";

        self.host = "http://simple.podnapisi.net"
        self.search = "/ppodnapisi/search?"
            
    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = self.getFileName(filepath)
        log.debug("Searching for %s" %fname)
        try:
            subs = []
            if langs:
                for lang in langs:
                    #query one language at a time
                    subs_lang = self.query(fname, [lang])
                    if not subs_lang and fname.count(".["):
                        # Try to remove the [VTV] or [EZTV] at the end of the file
                        teamless_filename = fname[0 : fname.rfind(".[")]
                        subs_lang = self.query(teamless_filename, langs)
                    subs += subs_lang
            else:
                subs_lang = self.query(fname, None)
                if not subs_lang and fname.count(".["):
                    # Try to remove the [VTV] or [EZTV] at the end of the file
                    teamless_filename = fname[0 : fname.rfind(".[")]
                    subs_lang = self.query(teamless_filename, None)
                subs += subs_lang
            return subs
        except Exception, e:
            log.error("Error raised by plugin %s: %s" %(self.__class__.__name__, e))
            traceback.print_exc()
            return []
    
    def query(self, token, langs=None):
        ''' makes a query on podnapisi and returns info (link, lang) about found subtitles'''
        guessedData = self.guessFileData(token)
        sublinks = []
        params = {"sK" : token}
        if langs and len(langs) == 1:
            params["sJ"] = self.getLanguage(langs[0])
        else:
            params["sJ"] = 0

        searchurl = self.host + self.search + urllib.urlencode(params)
        content = self.downloadContent(searchurl, 10)
        
        # Workaround for the Beautifulsoup 3.1 bug
        content = content.replace("scr'+'ipt", "script")
        soup = BeautifulSoup(content)
        for subs in soup("tr", {"class":"a"}) + soup("tr", {"class": "b"}):
            details = subs.find("span", {"class" : "opis"}).findAll("b")
            if guessedData["type"] == "tvshow" and guessedData["season"] == int(details[0].text) and guessedData["episode"] == int(details[1].text):
                links = subs.findAll("a")
                lng = subs.find("a").find("img")["src"].rsplit("/", 1)[1][:-4]
                if langs and not self.getLG(lng) in langs:
                    continue # The lang of this sub is not wanted => Skip
                pagelink = subs.findAll("a")[1]["href"]
                result = {}
                result["link"] = None # We'll find the link later using the page
                # some url are in unicode but urllib.quote() doesn't handle it
                # well : http://bugs.python.org/issue1712522
                result["page"] = self.host + urllib.quote(pagelink.encode("utf-8"))
                result["lang"] = self.getLG(lng)
                sublinks.append(result)

        log.debug(sublinks)
        return sublinks

    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        subpage = subtitle["page"]
        
        # Parse the subpage and extract the link
        content = self.downloadContent(subpage, timeout = 10)
        if not content:
            return sublinks

        # Workaround for the Beautifulsoup 3.1 bug or HTML bugs
        content = content.replace("scr'+'ipt", "script")
        content = content.replace("</br", "<br")
        soup = BeautifulSoup(content)
        dlimg = soup.find("img", {"title" : "Download"})
        subtitle["link"] = self.host + dlimg.parent["href"]
        
        SubtitleDatabase.SubtitleDB.createFile(self, subtitle)
        return subtitle["link"]

########NEW FILE########
__FILENAME__ = Podnapisi2
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

import zipfile, os, urllib2, urllib, traceback, logging
import xmlrpclib, struct, socket
from hashlib import md5, sha256

import SubtitleDatabase

class Podnapisi(SubtitleDatabase.SubtitleDB):
    url = "http://www.podnapisi.net/"
    site_name = "Podnapisi"

    def __init__(self, config, cache_folder_path):
        super(Podnapisi, self).__init__({"sl" : "1", "en": "2", "no" : "3", "ko" :"4", "de" : "5", "is" : "6", "cs" : "7", "fr" : "8", "it" : "9", "bs" : "10", "ja" : "11", "ar" : "12", "ro" : "13", "es-ar" : "14", "hu" : "15", "el" : "16", "zh" : "17", "lt" : "19", "et" : "20", "lv" : "21", "he" : "22", "nl" : "23", "da" : "24", "se" : "25", "pl" : "26", "ru" : "27", "es" : "28", "sq" : "29", "tr" : "30", "fi" : "31", "pt": "32", "bg" : "33", "mk" : "35", "sk" : "37", "hr" : "38", "zh" : "40", "hi": "42", "th" : "44", "uk": "46", "sr": "47", "pt-br" : "48", "ga": "49", "be": "50", "vi": "51", "fa": "52", "ca": "53", "id": "54"})
        
        #Note: Podnapisi uses two reference for latin serbian and cyrillic serbian (36 and 47). We'll add the 36 manually as cyrillic seems to be more used
        self.revertlangs["36"] = "sr";
        self.server_url = 'http://ssp.podnapisi.net:8000'



    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        if os.path.isfile(filepath):
            filehash = self.hashFile(filepath)
            size = os.path.getsize(filepath)
            fname = self.getFileName(filepath)
            return self.query(moviehash=filehash, langs=langs, bytesize=size, filename=fname)
        else:
            fname = self.getFileName(filepath)
            return self.query(langs=langs, filename=fname)
    
    def query(self, filename, imdbID=None, moviehash=None, bytesize=None, langs=None):
        ''' makes a query on podnapisi and returns info (link, lang) about found subtitles'''
        
        #Login
        self.server = xmlrpclib.Server(self.server_url)
        socket.setdefaulttimeout(1)
        try:
            log_result = self.server.initiate("Periscope")
            logging.debug(log_result)
            token = log_result["session"]
            nonce = log_result["nonce"]
        except Exception, e:
            logging.error("Podnapisi could not be contacted")
            socket.setdefaulttimeout(None)
            return []
        logging.debug("got token %s" %token)
        logging.debug("got nonce %s" %nonce)
        logging.debug("hashes are %s" %[moviehash])
        username = 'getmesubs'
        password = '99D31$$'
        hash = md5()
        hash.update(password)
        password = hash.hexdigest()

        hash = sha256()
        hash.update(password)
        hash.update(nonce)
        password = hash.hexdigest()
        print username
        print password
        self.server.authenticate(token, username, password)
        #self.server.authenticate(token, '', '')
        logging.debug("Authenticated. Starting search")
        results = self.server.search(token, [moviehash])
        print "Results are %s" %results
        subs = []
        for sub in results['results']:
            subs.append(sub)
            print sub
            
        print "Try a download"
        d = self.server.download(token, [173793])
        print d
        self.server.terminate(token)
        return subs
        

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
__FILENAME__ = SubDivX
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Matias Bordese
#
#   periscope is free software; you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   periscope is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#   along with periscope; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging
import os
import re
import subprocess
import urllib
import urllib2

from BeautifulSoup import BeautifulSoup

import SubtitleDatabase


LANGUAGES = {"es": "Spanish"}


class SubDivX(SubtitleDatabase.SubtitleDB):
    url = "http://www.subdivx.com"
    site_name = "SubDivX"

    def __init__(self, config, cache_folder_path):
        super(SubDivX, self).__init__(LANGUAGES)
        self.api_base_url = 'http://www.subdivx.com/index.php'

    def process(self, filepath, langs):
        '''Main method to call on the plugin.

        Pass the filename and the wished languages and it will query
        the subtitles source. Only Spanish available.
        '''
        if 'es' not in langs:
            return []

        fname = unicode(self.getFileName(filepath).lower())
        guessedData = self.guessFileData(fname)
        if guessedData['type'] == 'tvshow':
            subs = self.query(guessedData['name'],
                              guessedData['season'],
                              guessedData['episode'],
                              guessedData['teams'])
            return subs
        elif guessedData['type'] == 'movie':
            subs = self.query(guessedData['name'], extra=guessedData['teams'])
            return subs
        else:
            return []

    def _get_result_title(self, result):
        '''Return the title of the result.'''
        return result.find('a', {'class': 'titulo_menu_izq'}).text

    def _get_result_link(self, result):
        '''Return the absolute link of the result. (not the downloadble file)'''
        return result.find('a', {'class': 'titulo_menu_izq'}).get('href')

    def _get_download_link(self, result_url):
        '''Return the direct link of the subtitle'''
        content = self.downloadContent(result_url, timeout=5)
        soup = BeautifulSoup(content)
        return soup.find('a', {'class': 'link1'}).get('href')

    def _get_result_rating(self, result, extra):
        if extra is None:
            extra = []
        description = result.findNext('div', {'id': 'buscador_detalle_sub'}).text
        description = description.split('<!--')[0].lower()
        rating = 0
        for keyword in extra:
            if not keyword:
                continue
            elif keyword in description:
                rating += 1
        return rating

    def query(self, name, season=None, episode=None, extra=None):
        '''Query on SubDivX and return found subtitles details.'''
        sublinks = []

        if season and episode:
            query = "%s s%02de%02d" % (name, season, episode)
        else:
            query = name

        params = {'buscar': query,
                  'accion': '5',
                  'oxdown': '1', }
        encoded_params = urllib.urlencode(params)
        query_url = '%s?%s' % (self.api_base_url, encoded_params)

        logging.debug("SubDivX query: %s", query_url)

        content = self.downloadContent(query_url, timeout=5)
        if content is not None:
            soup = BeautifulSoup(content)
            for subs in soup('div', {"id": "menu_detalle_buscador"}):
                result = {}
                result["release"] = self._get_result_title(subs)
                result["lang"] = 'es'
                result["link"] = self._get_result_link(subs)
                result["page"] = query_url
                result["rating"] = self._get_result_rating(subs, extra)
                sublinks.append(result)
        sorted_links = sorted(sublinks, key=lambda k: k['rating'], reverse=True)
        return sorted_links

    def createFile(self, subtitle):
        '''Download and extract subtitle.

        Pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file.
        '''
        download_url = self._get_download_link(subtitle["link"])
        subtitle["link"] = download_url
        request = urllib2.Request(download_url)
        request.get_method = lambda: 'HEAD'
        response = urllib2.urlopen(request)

        if response.url.endswith('.zip'):
            # process as usual
            return super(SubDivX, self).createFile(subtitle)
        elif response.url.endswith('.rar'):
            # Rar support based on unrar commandline, download it here:
            # http://www.rarlab.com/rar_add.htm
            # Install and make sure it is on your path
            logging.warning(
                'Rar is not really supported yet. Trying to call unrar')

            video_filename = os.path.basename(subtitle["filename"])
            base_filename, _ = os.path.splitext(video_filename)
            base_rar_filename, _ = os.path.splitext(subtitle["filename"])
            rar_filename = '%s%s' % (base_rar_filename, '.rar')
            self.downloadFile(download_url, rar_filename)

            try:
                args = ['unrar', 'lb', rar_filename]
                output = subprocess.Popen(
                    args, stdout=subprocess.PIPE).communicate()[0]

                for fname in output.splitlines():
                    base_name, extension = os.path.splitext(fname)
                    if extension in (".srt", ".sub", ".txt"):
                        wd = os.path.dirname(rar_filename)
                        final_name = '%s%s' % (base_filename, extension)
                        final_path = os.path.join(wd, final_name)
                        args = ['unrar', 'e', rar_filename, fname, wd]
                        output = subprocess.Popen(
                            args, stdout=subprocess.PIPE).communicate()[0]
                        tmp = os.path.join(wd, fname)
                        if os.path.exists(tmp):
                            # rename extracted subtitle file
                            os.rename(tmp, final_path)
                            return final_path
            except OSError:
                logging.exception("Execution failed: unrar not available?")
                return None
            finally:
                os.remove(rar_filename)
        else:
            logging.info(
                "Unexpected file type (not zip) for %s" % rar_filename)
            return None

########NEW FILE########
__FILENAME__ = SubScene
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

import zipfile, os, urllib2, urllib, logging, traceback, httplib
from BeautifulSoup import BeautifulSoup

import SubtitleDatabase

SS_LANGUAGES = {"en": "English",
				"se": "Swedish",
				"da": "Danish",
				"fi":"Finnish",
				"no": "Norwegian",
				"fr" : "French",
				"es" : "Spanish",
				"is" : "Icelandic",
				"cs" : "Czech",
				"bg" : "Bulgarian",
				"de" : "German",
				"ar" : "Arabic",
				"el" : "Greek",
				"fa" : "Farsi/Persian",
				"nl" : "Dutch",
				"he" : "Hebrew",
				"id" : "Indonesian",
				"ja" : "Japanese",
				"vi" : "Vietnamese",
				"pt" : "Portuguese",
				"ro" : "Romanian",
				"tr" : "Turkish",
				"sr" : "Serbian",
				"pt-br" : "Brazillian Portuguese",
				"ru" : "Russian",
				"hr" : "Croatian",
				"sl" : "Slovenian",
				"zh" : "Chinese BG code",
				"it" : "Italian",
				"pl" : "Polish",
				"ko" : "Korean",
				"hu" : "Hungarian",
				"ku" : "Kurdish",
				"et" : "Estonian"}

class SubScene(SubtitleDatabase.SubtitleDB):
	url = "http://subscene.com/"
	site_name = "SubScene"

	def __init__(self, config, cache_folder_path):
		super(SubScene, self).__init__(SS_LANGUAGES)
		#http://subscene.com/s.aspx?subtitle=Dexter.S04E01.HDTV.XviD-NoTV
		self.host = "http://subscene.com/s.aspx?subtitle="

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
			logging.error("Error raised by plugin %s: %s" %(self.__class__.__name__, e))
			traceback.print_exc()
			return []
			
	def createFile(self, subtitle):
		'''pass the URL of the sub and the file it matches, will unzip it
		and return the path to the created file'''
		subpage = subtitle["page"]
		page = urllib2.urlopen(subpage)
		soup = BeautifulSoup(page)
		
		dlhref = soup.find("div", {"class" : "download"}).find("a")["href"]
		subtitle["link"] =  "http://subscene.com" + dlhref.split('"')[7]
		format = "zip"
		archivefilename = subtitle["filename"].rsplit(".", 1)[0] + '.'+ format
		self.downloadFile(subtitle["link"], archivefilename)
		subtitlefilename = None
		
		if zipfile.is_zipfile(archivefilename):
			logging.debug("Unzipping file " + archivefilename)
			zf = zipfile.ZipFile(archivefilename, "r")
			for el in zf.infolist():
				extension = el.orig_filename.rsplit(".", 1)[1]
				if extension in ("srt", "sub", "txt"):
					subtitlefilename = srtbasefilename + "." + extension
					outfile = open(subtitlefilename, "wb")
					outfile.write(zf.read(el.orig_filename))
					outfile.flush()
					outfile.close()
				else:
					logging.info("File %s does not seem to be valid " %el.orig_filename)
			# Deleting the zip file
			zf.close()
			os.remove(archivefilename)
			return subtitlefilename
		elif archivefilename.endswith('.rar'):
			logging.warn('Rar is not really supported yet. Trying to call unrar')
			import subprocess
			try :
				args = ['unrar', 'lb', archivefilename]
				output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
				for el in output.splitlines():
					extension = el.rsplit(".", 1)[1]
					if extension in ("srt", "sub"):
						args = ['unrar', 'e', archivefilename, el, os.path.dirname(archivefilename)]
						subprocess.Popen(args)
						tmpsubtitlefilename = os.path.join(os.path.dirname(archivefilename), el)
						subtitlefilename = os.path.join(os.path.dirname(archivefilename), srtbasefilename+"."+extension)
						if os.path.exists(tmpsubtitlefilename):
							# rename it to match the file
							os.rename(tmpsubtitlefilename, subtitlefilename)
							# exit
						return subtitlefilename
			except OSError, e:
			    logging.error("Execution failed: %s" %e)
			    return None
			
		else:
			logging.info("Unexpected file type (not zip) for %s" %archivefilename)
			return None

	def downloadFile(self, url, filename):
		''' Downloads the given url to the given filename '''
		logging.info("Downloading file %s" %url)
		req = urllib2.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
		
		f = urllib2.urlopen(req, data=urllib.urlencode({'__EVENTTARGET' : 's$lc$bcr$downloadLink', '__EVENTARGUMENT' : '', '__VIEWSTATE' : '/wEPDwUHNzUxOTkwNWRk4wau5efPqhlBJJlOkKKHN8FIS04='}))
		dump = open(filename, "wb")
		try:
			f.read(1000000)
		except httplib.IncompleteRead, e:
			dump.write(e.partial)
			logging.warn('Incomplete read for %s ... Trying anyway to decompress.' %url)
		dump.close()
		f.close()
		
		#SubtitleDatabase.SubtitleDB.downloadFile(self, req, filename)
	
	def query(self, token, langs=None):
		''' makes a query on subscene and returns info (link, lang) about found subtitles'''
		sublinks = []
		
		searchurl = "%s%s" %(self.host, urllib.quote(token))
		logging.debug("dl'ing %s" %searchurl)
		page = urllib2.urlopen(searchurl)
		
		soup = BeautifulSoup(page)
		for subs in soup("a", {"class":"a1"}):
			lang_span = subs.find("span")
			lang = self.getLG(lang_span.contents[0].strip())
			release_span = lang_span.findNext("span")
			release = release_span.contents[0].strip().split(" (")[0]
			sub_page = subs["href"]
			#http://subscene.com//s-dlpath-260016/78348/rar.zipx
			if release.startswith(token) and (not langs or lang in langs):
				result = {}
				result["release"] = release
				result["lang"] = lang
				result["link"] = None
				result["page"] = "http://subscene.com" + sub_page
				sublinks.append(result)
		return sublinks

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
        except urllib2.HTTPError as inst:
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

                if status == "Completed" and subteams.issubset(teams) and (not langs or lang in langs) :
                    result = {}
                    result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("-", ".").title(), int(season), int(episode), '.'.join(subteams)
    )
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
import struct
import socket # For timeout purposes
import re

log = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'

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
        if os.path.isfile(filepath):
            filename = os.path.basename(filepath)
        else:
            filename = filepath
        if filename.endswith(('.avi', '.wmv', '.mov', '.mp4', '.mpeg', '.mpg', '.mkv')):
            fname = filename.rsplit('.', 1)[0]
        else:
            fname = filename
        return fname
        
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
        return returnedhash


class InvalidFileException(Exception):
    ''' Exception object to be raised when the file is invalid'''
    def __init__(self, filename, reason):
        self.filename = filename
        self.reason = reason
    def __str__(self):
        return (repr(filename), repr(reason))

########NEW FILE########
__FILENAME__ = SubtitleSource
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

import os, urllib2, urllib, xml.dom.minidom, logging, traceback
import ConfigParser

try:
    import xdg.BaseDirectory as bd
    is_local = True
except ImportError:
    is_local = False
    
import SubtitleDatabase

SS_LANGUAGES = {"en": "English",
                "sv": "Swedish",
                "da": "Danish",
                "fi":"Finnish",
                "no": "Norwegian",
                "fr" : "French",
                "es" : "Spanish",
                "is" : "Icelandic"}

class SubtitleSource(SubtitleDatabase.SubtitleDB):
    url = "http://www.subtitlesource.org/"
    site_name = "SubtitleSource"

    def __init__(self, config, cache_folder_path):
        super(SubtitleSource, self).__init__(SS_LANGUAGES)
        key = config.get("SubtitleSource", "key") # You need to ask for it
        if not key:
            log.error("No key in the config file for SubtitleSource")
            return
        #http://www.subtitlesource.org/api/KEY/3.0/xmlsearch/Heroes.S03E09.HDTV.XviD-LOL/all/0
        #http://www.subtitlesource.org/api/KEY/3.0/xmlsearch/heroes/swedish/0

        self.host = "http://www.subtitlesource.org/api/%s/3.0/xmlsearch" %key
            
    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        if not key:
            log.info("No key in the config file for SubtitleSource : skip")
            return []
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
            logging.error("Error raised by plugin %s: %s" %(self.__class__.__name__, e))
            traceback.print_exc()
            return []
    
    def query(self, token, langs=None):
        ''' makes a query on subtitlessource and returns info (link, lang) about found subtitles'''
        logging.debug("local file is  : %s " % token)
        sublinks = []
        
        if not langs: # langs is empty of None
            languages = ["all"]
        else: # parse each lang to generate the equivalent lang
            languages = [SS_LANGUAGES[l] for l in langs if l in SS_LANGUAGES.keys()]
            
        # Get the CD part of this
        metaData = self.guessFileData(token)
        multipart = metaData.get('part', None)
        part = metaData.get('part')
        if not part : # part will return None if not found using the regex
            part = 1
                            
        for lang in languages:
            searchurl = "%s/%s/%s/0" %(self.host, urllib.quote(token), lang)
            logging.debug("dl'ing %s" %searchurl)
            page = urllib2.urlopen(searchurl, timeout=5)
            xmltree = xml.dom.minidom.parse(page)
            subs = xmltree.getElementsByTagName("sub")

            for sub in subs:
                sublang = self.getLG(self.getValue(sub, "language"))
                if langs and not sublang in langs:
                    continue # The language of this sub is not wanted => Skip
                if multipart and not int(self.getValue(sub, 'cd')) > 1:
                    continue # The subtitle is not a multipart
                dllink = "http://www.subtitlesource.org/download/text/%s/%s" %(self.getValue(sub, "id"), part)
                logging.debug("Link added: %s (%s)" %(dllink,sublang))
                result = {}
                result["release"] = self.getValue(sub, "releasename")
                result["link"] = dllink
                result["page"] = dllink
                result["lang"] = sublang
                releaseMetaData = self.guessFileData(result['release'])
                teams = set(metaData['teams'])
                srtTeams = set(releaseMetaData['teams'])
                logging.debug("Analyzing : %s " % result['release'])
                logging.debug("local file has : %s " % metaData['teams'])
                logging.debug("remote sub has  : %s " % releaseMetaData['teams'])
                #logging.debug("%s in %s ? %s - %s" %(releaseMetaData['teams'], metaData['teams'], teams.issubset(srtTeams), srtTeams.issubset(teams)))
                if result['release'].startswith(token) or (releaseMetaData['name'] == metaData['name'] and releaseMetaData['type'] == metaData['type'] and (teams.issubset(srtTeams) or srtTeams.issubset(teams))):
                    sublinks.append(result)
        return sublinks

            
    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtfilename = videofilename.rsplit(".", 1)[0] + '.srt'
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def getValue(self, sub, tagName):
        for node in sub.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == tagName:
                return node.childNodes[0].nodeValue

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
                if status == "Completado" and subteams.issubset(teams) and (not langs or lang in langs) :
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
__FILENAME__ = TheSubDB
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

import os
import urllib2
import urllib
import xml.dom.minidom
import logging
import traceback
import hashlib
import StringIO

import SubtitleDatabase

log = logging.getLogger(__name__)

SS_LANGUAGES = {"en": "en",
                "nl": "nl",
                "pt": "pt",
                "pt-br":"pt",
                "no": "Norwegian",
                "fr" : "French",
                "es" : "Spanish",
                "is" : "Icelandic"}

class TheSubDB(SubtitleDatabase.SubtitleDB):
    url = "http://thesubdb.com/"
    site_name = "SubDB"
    user_agent = "SubDB/1.0 (periscope/0.1; http://code.google.com/p/periscope)"

    def __init__(self, config, cache_folder_path):
        super(TheSubDB, self).__init__(SS_LANGUAGES)
        self.base_url = 'http://api.thesubdb.com/?{0}'
            
    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        # Get the hash
        filehash = self.get_hash(filepath)
        log.debug('File hash : %s' % filehash)
        # Make the search
        params = {'action' : 'search', 'hash' : filehash }
        search_url = self.base_url.format(urllib.urlencode(params))
        log.debug('Query URL : %s' % search_url)
        req = urllib2.Request(search_url)
        req.add_header('User-Agent', self.user_agent)
        subs = []
        try : 
            page = urllib2.urlopen(req, timeout=5)
            content = page.readlines()
            plugin_langs = content[0].split(',')
            print content[0]
            for lang in plugin_langs :
                if not langs or lang in langs:
                    result = {}
                    result['release'] = filepath
                    result['lang'] = lang
                    result['link'] = self.base_url.format(urllib.urlencode({'action':'download', 'hash':filehash , 'language' :lang}))
                    result['page'] = result['link']
                    subs.append(result)
            return subs
        except urllib2.HTTPError, e :
            if e.code == 404 : # No result found
                return subs
            else:
                log.exception('Error occured : %s' % e)
        

    def get_hash(self, name):
        '''this hash function receives the name of the file and returns the hash code'''
        readsize = 64 * 1024
        with open(name, 'rb') as f:
            size = os.path.getsize(name)
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()
            
    def createFile(self, subtitle):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtfilename = videofilename.rsplit(".", 1)[0] + '.srt'
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, srtfilename):
        ''' Downloads the given url to the given filename '''
        req = urllib2.Request(url)
        req.add_header('User-Agent', self.user_agent)
        
        f = urllib2.urlopen(req)
        dump = open(srtfilename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()
        log.debug("Download finished to file %s. Size : %s"%(srtfilename,os.path.getsize(srtfilename)))
        
    def uploadFile(self, filepath, subpath, lang):
        # Get the hash
        filehash = self.get_hash(filepath)
        log.debug('File hash : %s' % filehash)
        
        # Upload the subtitle
        params = {'action' : 'upload', 'hash' : filehash}
        upload_url = self.base_url.format(urllib.urlencode(params))
        log.debug('Query URL : %s' % upload_url)
        sub = open(subpath, "r")
        '''content = sub.read()
        sub.close()
        fd = StringIO.StringIO()
        fd.name = '%s.srt' % filehash
        fd.write(content)'''
        
        data = urllib.urlencode({'hash' : filehash, 'file' : sub})
        req = urllib2.Request(upload_url, data)
        req.add_header('User-Agent', self.user_agent)
        try : 
            page = urllib2.urlopen(req, data, timeout=5)
            log.debug(page.readlines())
        except urllib2.HTTPError, e :
            log.exception('Error occured while uploading : %s' % e)
            #log.info(fd.name)
            #log.info(fd.len)
        finally:
            pass
            #fd.close()
        

########NEW FILE########
__FILENAME__ = TvSubtitles
## dvrasp 15.4.09 v.001
## Sources :
##  - http://code.google.com/p/arturo/source/browse/trunk/plugins/net/tvsubtitles.py
##  - http://www.gtk-apps.org/CONTENT/content-files/90184-download_tvsubtitles.net.py

import logging

import zipfile, os, urllib2
import os, re, BeautifulSoup, urllib

showNum = {
"24":38,
"30 rock":46,
"90210":244,
"afterlife":200,
"alias":5,
"aliens in america":119,
"ally mcbeal":158,
"american dad":138,
"andromeda":60,
"andy barker: p.i.":49,
"angel":98,
"army wives":242,
"arrested development":161,
"ashes to ashes":151,
"avatar: the last airbender":125,
"back to you":183,
"band of brothers":143,
"battlestar galactica":42,
"big day":237,
"big love":88,
"big shots":137,
"bionic woman":113,
"black adder":176,
"black books":175,
"blade":177,
"blood ties":140,
"bonekickers":227,
"bones":59,
"boston legal":77,
"breaking bad":133,
"brotherhood":210,
"brothers &amp; sisters":66,
"buffy the vampire slayer":99,
"burn notice":50,
"californication":103,
"carnivale":170,
"carpoolers":146,
"cashmere mafia":129,
"charmed":87,
"chuck":111,
"city of vice":257,
"cold case":95,
"criminal minds":106,
"csi":27,
"csi miami":51,
"csi ny":52,
"curb your enthusiasm":69,
"damages":124,
"dark angel":131,
"day break":6,
"dead like me":13,
"deadwood":48,
"desperate housewives":29,
"dexter":55,
"dirt":145,
"dirty sexy money":118,
"do not disturb":252,
"doctor who":141,
"dollhouse" : 448,
"drive":97,
"eli stone":149,
"entourage":25,
"er (e.r.)":39,
"eureka":43,
"everybody hates chris":81,
"everybody loves raymond":86,
"exes &amp; ohs":199,
"extras":142,
"fallen":101,
"family guy":62,
"farscape":92,
"fawlty towers":178,
"fear itself":201,
"felicity":217,
"firefly":84,
"flash gordon":134,
"flashpoint":221,
"friday night lights":57,
"friends":65,
"fringe":204,
"futurama":126,
"generation kill":223,
"ghost whisperer":14,
"gilmore girls":28,
"gossip girl":114,
"greek":102,
"grey's anatomy":7,
"hank":538,
"heroes":8,
"hidden palms":44,
"hotel babylon":164,
"house m.d.":9,
"how i met your mother":110,
"hustle":160,
"in justice":144,
"in plain sight":198,
"in treatment":139,
"into the west":256,
"invasion":184,
"it's always sunny in philadelphia":243,
"jeeves and wooster":180,
"jekyll":61,
"jericho":37,
"joey":83,
"john adams":155,
"john from cincinnati":79,
"journeyman":108,
"k-ville":107,
"keeping up appearances":167,
"knight rider":163,
"kyle xy":10,
"lab rats":233,
"las vegas":75,
"life":109,
"life is wild":120,
"life on mars (uk)":90,
"lipstick jungle":150,
"lost":3,
"lost in austen":254,
"lucky louie":238,
"mad men":136,
"meadowlands":45,
"medium":12,
"melrose place":189,
"men in trees":127,
"miami vice":208,
"monk":85,
"moonlight":117,
"my name is earl":15,
"ncis":30,
"new amsterdam":153,
"nip/tuck":23,
"northern exposure":241,
"numb3rs":11,
"october road":132,
"one tree hill":16,
"over there":93,
"oz":36,
"painkiller jane":35,
"pepper dennis":82,
"police squad":190,
"popetown":179,
"pretender":245,
"primeval":130,
"prison break":2,
"private practice":115,
"privileged":248,
"project runway":226,
"psych":17,
"pushing daisies":116,
"queer as folk":229,
"reaper":112,
"regenesis":152,
"rescue me":91,
"robin hood":121,
"rome":63,
"roswell":159,
"samantha who?":123,
"samurai girl":255,
"saving grace":104,
"scrubs":26,
"secret diary of a call girl":196,
"seinfeld":89,
"sex and the city":68,
"shameless":193,
"shark":24,
"sharpe":186,
"six feet under":94,
"skins":147,
"smallville":1,
"sophie":203,
"south park":71,
"spooks":148,
"standoff":70,
"stargate atlantis":54,
"stargate sg-1":53,
"studio 60 on the sunset strip":33,
"supernatural":19,
"swingtown":202,
"taken":67,
"tell me you love me":182,
"terminator: the sarah connor chronicles":128,
"the 4400":20,
"the andromeda strain":181,
"the big bang theory":154,
"the black donnellys":216,
"the cleaner":225,
"the closer":78,
"the dead zone":31,
"the dresden files":64,
"the fixer":213,
"the inbetweeners":197,
"the it crowd":185,
"the l word":74,
"the middleman":222,
"the net":174,
"the no. 1 ladies' detective agency":162,
"the o.c. (the oc)":21,
"the office":58,
"the outer limits":211,
"the riches":156,
"the secret life of the american teenager":218,
"the shield":40,
"the simple life":234,
"the simpsons":32,
"the sopranos":18,
"the tudors":76,
"the unit":47,
"the war at home":80,
"the west wing":168,
"the wire":72,
"the x-files":100,
"threshold":96,
"til death":171,
"tin man":122,
"top gear":232,
"torchwood":135,
"traveler":41,
"tripping the rift":188,
"tru calling":4,
"true blood":205,
"twin peaks":169,
"two and a half men":56,
"ugly betty":34,
"ultimate force":194,
"unhitched":157,
"veronica mars":22,
"weeds":73,
"will & grace":172,
"without a trace":105,
"women's murder club":166,
"wonderfalls":165
 }


import SubtitleDatabase

class TvSubtitles(SubtitleDatabase.SubtitleDB):
	url = "http://www.tvsubtitles.net"
	site_name = "TvSubtitles"
	
	URL_SHOW_PATTERN = "http://www.tvsubtitles.net/tvshow-%s.html"
	URL_SEASON_PATTERN = "http://www.tvsubtitles.net/tvshow-%s-%d.html"

	def __init__(self):
		super(TvSubtitles, self).__init__({"en":'en', "fr":'fr'})## TODO ??
		self.host = TvSubtitles.url
    
	def _get_episode_urls(self, show, season, episode, langs):
		showId = showNum.get(show, None)
		if not showId:
			return []
		show_url = self.URL_SEASON_PATTERN % (showId, season)
		logging.debug("Show url: %s" % show_url)
		page = urllib.urlopen(show_url)
		content = page.read()
		content = content.replace("SCR'+'IPT", "script")
		soup = BeautifulSoup.BeautifulSoup(content)
		td_content = "%sx%s"%(season, episode)
		tds = soup.findAll(text=td_content)
		links = []
		for td in tds:
			imgs =  td.parent.parent.findAll("td")[3].findAll("img")
			for img in imgs:
				# If there is an alt, and that alt in langs or you didn't specify a langs
				if img['alt'] and ((langs and img['alt'] in langs) or (not langs)):
					url = self.host + "/" + img.parent['href']
					lang = img['alt']
					logging.debug("Found lang %s - %s" %(lang, url))
					links.append((url, lang))
					
		return links

	def query(self, show, season, episode, teams, langs):
		showId = showNum.get(show, None)
		if not showId:
			return []
		show_url = self.URL_SEASON_PATTERN % (showId, season)
		logging.debug("Show url: %s" % show_url)
		page = urllib.urlopen(show_url)
		content = page.read()
		content = content.replace("SCR'+'IPT", "script")
		soup = BeautifulSoup.BeautifulSoup(content)
		td_content = "%dx%02d"%(season, episode)
		tds = soup.findAll(text=td_content)
		links = []
		for td in tds:
			imgs =  td.parent.parent.findAll("td")[3].findAll("img")
			for img in imgs:
				# If there is an alt, and that alt in langs or you didn't specify a langs
				if img['alt'] and ((langs and img['alt'] in langs) or (not langs)):
					url = img.parent['href']
					lang = img['alt']
					logging.debug("Found lang %s - %s" %(lang, url))
					if url.startswith("subtitle"):
						url = self.host + "/" + url
						logging.debug("Parse : %s" %url)
						sub = self.parseSubtitlePage(url, lang, show, season, episode, teams)
						if sub:
							links.append(sub)
					else:
						page2 = urllib.urlopen(self.host + "/" + url)
						soup2 = BeautifulSoup.BeautifulSoup(page2)
						subs = soup2.findAll("div", {"class" : "subtitlen"})
						for sub in subs:
							url = self.host + sub.get('href', None)
							logging.debug("Parse2 : %s" %url)
							sub = self.parseSubtitlePage(url, lang, show, season, episode, teams)
							if sub:
								links.append(sub)
					
		return links
		
	def parseSubtitlePage(self, url, lang, show, season, episode, teams):
		fteams = []
		for team in teams:
			fteams += team.split("-")
		fteams = set(fteams)
		
		subid = url.rsplit("-", 1)[1].split('.', 1)[0]
		link = self.host + "/download-" + subid + ".html"
		
		page = urllib.urlopen(url)
		content = page.read()
		content = content.replace("SCR'+'IPT", "script")
		soup = BeautifulSoup.BeautifulSoup(content)
		
		subteams = set()
		releases = soup.findAll(text="release:")
		if releases:
			subteams.update([releases[0].parent.parent.parent.parent.findAll("td")[2].string.lower()])
		
		rips = soup.findAll(text="rip:")
		if rips:
			subteams.update([rips[0].parent.parent.parent.parent.findAll("td")[2].string.lower()])
		
		if subteams.issubset(fteams):
			logging.debug("It'a match ! : %s <= %s" %(subteams, fteams))
			result = {}
			result["release"] = "%s.S%.2dE%.2d.%s" %(show.replace(" ", ".").title(), int(season), int(episode), '.'.join(subteams).upper()
	)
			result["lang"] = lang
			result["link"] = link
			result["page"] = url
			return result
		else:
			logging.debug("It'not a match ! : %s > %s" %(subteams, fteams))
			return None
			
		
		

	def process(self, filename, langs):
		''' main method to call on the plugin, pass the filename and the wished 
		languages and it will query TvSubtitles.net '''
		fname = unicode(self.getFileName(filename).lower())
		guessedData = self.guessFileData(fname)
		logging.debug(fname)
		if guessedData['type'] == 'tvshow':
			subs = self.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], langs)
			return subs
		else:
			return []

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

VERSION = "dev"

########NEW FILE########
__FILENAME__ = periscope
#!/usr/bin/python
# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public
#    License as published by the Free Software Foundation; either
#    version 2 of the License, or (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import mimetypes
from optparse import OptionParser
import logging
import periscope

log = logging.getLogger(__name__)

SUPPORTED_FORMATS = 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4'

def main():
    '''Download subtitles'''
    # parse command line options
    parser = OptionParser("usage: %prog [options] file1 file2", version = periscope.VERSION)
    parser.add_option("-l", "--language", action="append", dest="langs", help="wanted language (ISO 639-1 two chars) for the subtitles (fr, en, ja, ...). If none is specified will download a subtitle in any language. This option can be used multiple times like %prog -l fr -l en file1 will try to download in french and then in english if no french subtitles are found.")
    parser.add_option("-f", "--force", action="store_true", dest="force_download", help="force download of a subtitle even there is already one present")
    parser.add_option("-q", "--query", action="append", dest="queries", help="query to send to the subtitles website")
    parser.add_option("--cache-folder", action="store", type="string", dest="cache_folder", help="location of the periscope cache/config folder (default is ~/.config/periscope)")
    parser.add_option("--list-plugins", action="store_true", dest="show_plugins", help="list all plugins supported by periscope")
    parser.add_option("--list-active-plugins", action="store_true", dest="show_active_plugins", help="list all plugins used to search subtitles (a subset of all the supported plugins)")
    parser.add_option("--quiet", action="store_true", dest="quiet", help="run in quiet mode (only show warn and error messages)")
    parser.add_option("--debug", action="store_true", dest="debug", help="set the logging level to debug")
    (options, args) = parser.parse_args()
    
    if not args:
        print parser.print_help()
        exit()

    # process args
    if options.debug :
        logging.basicConfig(level=logging.DEBUG)
    elif options.quiet :
        logging.basicConfig(level=logging.WARN)
    else :
        logging.basicConfig(level=logging.INFO)
        

    if not options.cache_folder:
        try:
            import xdg.BaseDirectory as bd
            options.cache_folder = os.path.join(bd.xdg_config_home, "periscope")
        except:
            home = os.path.expanduser("~")
            if home == "~":
                log.error("Could not generate a cache folder at the home location using XDG (freedesktop). You must specify a --cache-config folder where the cache and config will be located (always use the same folder).")
                exit()
            options.cache_folder = os.path.join(home, ".config", "periscope")

    
    periscope_client = periscope.Periscope(options.cache_folder)
        
    if options.show_active_plugins:
        print "Active plugins: "
        plugins = periscope_client.listActivePlugins()
        for plugin in plugins:
            print "%s" %(plugin)
        exit()
        
    if options.show_plugins:
        print "All plugins: "
        plugins = periscope_client.listExistingPlugins()
        for plugin in plugins:
            print "%s" %(plugin)
        exit()
            
    if options.queries: args += options.queries
    videos = []
    for arg in args:
        videos += recursive_search(arg, options)

    subs = []
    for arg in videos:
        if not options.langs: #Look into the config
            log.info("No lang given, looking into config file")
            langs = periscope_client.preferedLanguages
        else:
            langs = options.langs
        sub = periscope_client.downloadSubtitle(arg, langs)
        if sub:
            subs.append(sub)
    
    log.info("*"*50)
    log.info("Downloaded %s subtitles" %len(subs))
    for s in subs:
        log.info(s['lang'] + " - " + s['subtitlepath'])
    log.info("*"*50)
    if len(subs) == 0:
        exit(1)


def recursive_search(entry, options):
    '''searches files in the dir'''
    files = []
    if os.path.isdir(entry):
        #TODO if hidden folder, don't keep going (how to handle windows/mac/linux ?)
        for e in os.listdir(entry):
            files += recursive_search(os.path.join(entry, e), options)
    elif os.path.isfile(entry):
        # Add mkv mimetype to the list
        mimetypes.add_type("video/x-matroska", ".mkv")
        mimetype = mimetypes.guess_type(entry)[0]
        if mimetype in SUPPORTED_FORMATS:
            # Add it to the list only if there is not already one (or forced)
            basepath = os.path.splitext(entry)[0]
            if options.force_download or not (os.path.exists(basepath+'.srt') or os.path.exists(basepath + '.sub')):
                files.append(os.path.normpath(entry))
            else:
                log.info("Skipping file %s as it already has a subtitle. Use the --force option to force the download" % entry)
        else :
            log.info("%s mimetype is '%s' which is not a supported video format (%s)" %(entry, mimetype, SUPPORTED_FORMATS))
    return files
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = version
VERSION = "dev"

########NEW FILE########
