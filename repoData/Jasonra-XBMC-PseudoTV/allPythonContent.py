__FILENAME__ = config
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from xml.dom.minidom import parse, parseString
from resources.lib.Globals import *
from resources.lib.ChannelList import ChannelList
from resources.lib.AdvancedConfig import AdvancedConfig
from resources.lib.FileAccess import FileAccess
from resources.lib.Migrate import Migrate


NUMBER_CHANNEL_TYPES = 8



class ConfigWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.setCoordinateResolution(1)
        self.showingList = True
        self.channel = 0
        self.channel_type = 9999
        self.setting1 = ''
        self.setting2 = ''
        self.savedRules = False
        ADDON_SETTINGS.loadSettings()
        self.doModal()
        self.log("__init__ return")


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")

        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass

        migratemaster = Migrate()
        migratemaster.migrate()
        self.prepareConfig()
        self.myRules = AdvancedConfig("script.pseudotv.AdvancedConfig.xml", ADDON_INFO, "default")
        self.log("onInit return")


    def onFocus(self, controlId):
        pass


    def onAction(self, act):
        action = act.getId()

        if action in ACTION_PREVIOUS_MENU:
            if self.showingList == False:
                self.cancelChan()
                self.hideChanDetails()
            else:
                self.close()


    def saveSettings(self):
        self.log("saveSettings channel " + str(self.channel))
        chantype = 9999
        chan = str(self.channel)
        set1 = ''
        set2 = ''

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + chan + "_type"))
        except:
            self.log("Unable to get channel type")

        setting1 = "Channel_" + chan + "_1"
        setting2 = "Channel_" + chan + "_2"

        if chantype == 0:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(130).getLabel2())
        elif chantype == 1:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(142).getLabel())
        elif chantype == 2:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(152).getLabel())
        elif chantype == 3:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(162).getLabel())
        elif chantype == 4:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(172).getLabel())
        elif chantype == 5:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(182).getLabel())
        elif chantype == 6:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(192).getLabel())

            if self.getControl(194).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
        elif chantype == 7:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(200).getLabel())
        elif chantype == 9999:
            ADDON_SETTINGS.setSetting(setting1, '')
            ADDON_SETTINGS.setSetting(setting2, '')

        if self.savedRules:
            self.saveRules(self.channel)

        # Check to see if the user changed anything
        set1 = ''
        set2 = ''

        try:
            set1 = ADDON_SETTINGS.getSetting(setting1)
            set2 = ADDON_SETTINGS.getSetting(setting2)
        except:
            pass

        if chantype != self.channel_type or set1 != self.setting1 or set2 != self.setting2 or self.savedRules:
            ADDON_SETTINGS.setSetting('Channel_' + chan + '_changed', 'True')

        self.log("saveSettings return")


    def cancelChan(self):
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_type", str(self.channel_type))
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_1", self.setting1)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_2", self.setting2)


    def hideChanDetails(self):
        self.getControl(106).setVisible(False)

        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass

        self.setFocusId(102)
        self.getControl(105).setVisible(True)
        self.showingList = True
        self.updateListing(self.channel)
        self.listcontrol.selectItem(self.channel - 1)


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

        if controlId == 102:        # Channel list entry selected
            self.getControl(105).setVisible(False)
            self.getControl(106).setVisible(True)
            self.channel = self.listcontrol.getSelectedPosition() + 1
            self.changeChanType(self.channel, 0)
            self.setFocusId(110)
            self.showingList = False
            self.savedRules = False
        elif controlId == 110:      # Change channel type left
            self.changeChanType(self.channel, -1)
        elif controlId == 111:      # Change channel type right
            self.changeChanType(self.channel, 1)
        elif controlId == 112:      # Ok button
            self.saveSettings()
            self.hideChanDetails()
        elif controlId == 113:      # Cancel button
            self.cancelChan()
            self.hideChanDetails()
        elif controlId == 114:      # Rules button
            self.myRules.ruleList = self.ruleList
            self.myRules.doModal()

            if self.myRules.wasSaved == True:
                self.ruleList = self.myRules.ruleList
                self.savedRules = True
        elif controlId == 130:      # Playlist-type channel, playlist button
            dlg = xbmcgui.Dialog()
            retval = dlg.browse(1, "Channel " + str(self.channel) + " Playlist", "files", ".xsp", False, False, "special://videoplaylists/")

            if retval != "special://videoplaylists/":
                self.getControl(130).setLabel(self.getSmartPlaylistName(retval), label2=retval)
        elif controlId == 140:      # Network TV channel, left
            self.changeListData(self.networkList, 142, -1)
        elif controlId == 141:      # Network TV channel, right
            self.changeListData(self.networkList, 142, 1)
        elif controlId == 150:      # Movie studio channel, left
            self.changeListData(self.studioList, 152, -1)
        elif controlId == 151:      # Movie studio channel, right
            self.changeListData(self.studioList, 152, 1)
        elif controlId == 160:      # TV Genre channel, left
            self.changeListData(self.showGenreList, 162, -1)
        elif controlId == 161:      # TV Genre channel, right
            self.changeListData(self.showGenreList, 162, 1)
        elif controlId == 170:      # Movie Genre channel, left
            self.changeListData(self.movieGenreList, 172, -1)
        elif controlId == 171:      # Movie Genre channel, right
            self.changeListData(self.movieGenreList, 172, 1)
        elif controlId == 180:      # Mixed Genre channel, left
            self.changeListData(self.mixedGenreList, 182, -1)
        elif controlId == 181:      # Mixed Genre channel, right
            self.changeListData(self.mixedGenreList, 182, 1)
        elif controlId == 190:      # TV Show channel, left
            self.changeListData(self.showList, 192, -1)
        elif controlId == 191:      # TV Show channel, right
            self.changeListData(self.showList, 192, 1)
        elif controlId == 200:      # Directory channel, select
            dlg = xbmcgui.Dialog()
            retval = dlg.browse(0, "Channel " + str(self.channel) + " Directory", "files")

            if len(retval) > 0:
                self.getControl(200).setLabel(retval)

        self.log("onClick return")


    def changeListData(self, thelist, controlid, val):
        self.log("changeListData " + str(controlid) + ", " + str(val))
        curval = self.getControl(controlid).getLabel()
        found = False
        index = 0

        if len(thelist) == 0:
            self.getControl(controlid).setLabel('')
            self.log("changeListData return Empty list")
            return

        for item in thelist:
            if item == curval:
                found = True
                break

            index += 1

        if found == True:
            index += val

        while index < 0:
            index += len(thelist)

        while index >= len(thelist):
            index -= len(thelist)

        self.getControl(controlid).setLabel(thelist[index])
        self.log("changeListData return")


    def getSmartPlaylistName(self, fle):
        self.log("getSmartPlaylistName " + fle)
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log('Unable to open smart playlist')
            return ''

        try:
            dom = parse(xml)
        except:
            xml.close()
            self.log("getSmartPlaylistName return unable to parse")
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log("getSmartPlaylistName return " + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.playlisy('Unable to find element name')

        self.log("getSmartPlaylistName return")


    def changeChanType(self, channel, val):
        self.log("changeChanType " + str(channel) + ", " + str(val))
        chantype = 9999

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
        except:
            self.log("Unable to get channel type")

        if val != 0:
            chantype += val

            if chantype < 0:
                chantype = 9999
            elif chantype == 10000:
                chantype = 0
            elif chantype == 9998:
                chantype = NUMBER_CHANNEL_TYPES - 1
            elif chantype == NUMBER_CHANNEL_TYPES:
                chantype = 9999

            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", str(chantype))
        else:
            self.channel_type = chantype
            self.setting1 = ''
            self.setting2 = ''

            try:
                self.setting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
                self.setting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
            except:
                pass

        for i in range(NUMBER_CHANNEL_TYPES):
            if i == chantype:
                self.getControl(120 + i).setVisible(True)
                self.getControl(110).controlDown(self.getControl(120 + ((i + 1) * 10)))

                try:
                    self.getControl(111).controlDown(self.getControl(120 + ((i + 1) * 10 + 1)))
                except:
                    self.getControl(111).controlDown(self.getControl(120 + ((i + 1) * 10)))
            else:
                try:
                    self.getControl(120 + i).setVisible(False)
                except:
                    pass

        self.fillInDetails(channel)
        self.log("changeChanType return")


    def fillInDetails(self, channel):
        self.log("fillInDetails " + str(channel))
        self.getControl(104).setLabel("Channel " + str(channel))
        chantype = 9999
        chansetting1 = ''
        chansetting2 = ''

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
            chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
            chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
        except:
            self.log("Unable to get some setting")

        self.getControl(109).setLabel(self.getChanTypeLabel(chantype))

        if chantype == 0:
            plname = self.getSmartPlaylistName(chansetting1)

            if len(plname) == 0:
                chansetting1 = ''

            self.getControl(130).setLabel(self.getSmartPlaylistName(chansetting1), label2=chansetting1)
        elif chantype == 1:
            self.getControl(142).setLabel(self.findItemInList(self.networkList, chansetting1))
        elif chantype == 2:
            self.getControl(152).setLabel(self.findItemInList(self.studioList, chansetting1))
        elif chantype == 3:
            self.getControl(162).setLabel(self.findItemInList(self.showGenreList, chansetting1))
        elif chantype == 4:
            self.getControl(172).setLabel(self.findItemInList(self.movieGenreList, chansetting1))
        elif chantype == 5:
            self.getControl(182).setLabel(self.findItemInList(self.mixedGenreList, chansetting1))
        elif chantype == 6:
            self.getControl(192).setLabel(self.findItemInList(self.showList, chansetting1))
            self.getControl(194).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
        elif chantype == 7:
            self.getControl(200).setLabel(chansetting1)

        self.loadRules(channel)
        self.log("fillInDetails return")


    def loadRules(self, channel):
        self.log("loadRules")
        self.ruleList = []
        self.myRules.allRules

        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))

            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))

                for rule in self.myRules.allRules.ruleList:
                    if rule.getId() == ruleid:
                        self.ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))

                        foundrule = True
                        break
        except:
            self.ruleList = []


    def saveRules(self, channel):
        self.log("saveRules")
        rulecount = len(self.ruleList)
        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rulecount', str(rulecount))
        index = 1

        for rule in self.ruleList:
            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_id', str(rule.getId()))

            for x in range(rule.getOptionCount()):
                ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_opt_' + str(x + 1), rule.getOptionValue(x))

            index += 1


    def findItemInList(self, thelist, item):
        loitem = item.lower()

        for i in thelist:
            if loitem == i.lower():
                return item

        if len(thelist) > 0:
            return thelist[0]

        return ''


    def getChanTypeLabel(self, chantype):
        if chantype == 0:
            return "Custom Playlist"
        elif chantype == 1:
            return "TV Network"
        elif chantype == 2:
            return "Movie Studio"
        elif chantype == 3:
            return "TV Genre"
        elif chantype == 4:
            return "Movie Genre"
        elif chantype == 5:
            return "Mixed Genre"
        elif chantype == 6:
            return "TV Show"
        elif chantype == 7:
            return "Directory"
        elif chantype == 9999:
            return "None"

        return ''

    def prepareConfig(self):
        self.log("prepareConfig")
        self.showList = []
        self.getControl(105).setVisible(False)
        self.getControl(106).setVisible(False)
        self.dlg = xbmcgui.DialogProgress()
        self.dlg.create("PseudoTV", "Preparing Configuration")
        self.dlg.update(1)
        chnlst = ChannelList()
        chnlst.fillTVInfo()
        self.dlg.update(40)
        chnlst.fillMovieInfo()
        self.dlg.update(80)
        self.mixedGenreList = chnlst.makeMixedList(chnlst.showGenreList, chnlst.movieGenreList)
        self.networkList = chnlst.networkList
        self.studioList = chnlst.studioList
        self.showGenreList = chnlst.showGenreList
        self.movieGenreList = chnlst.movieGenreList

        for i in range(len(chnlst.showList)):
            self.showList.append(chnlst.showList[i][0])

        self.mixedGenreList.sort(key=lambda x: x.lower())
        self.listcontrol = self.getControl(102)

        for i in range(200):
            theitem = xbmcgui.ListItem()
            theitem.setLabel(str(i + 1))
            self.listcontrol.addItem(theitem)


        self.dlg.update(90)
        self.updateListing()
        self.dlg.close()
        self.getControl(105).setVisible(True)
        self.getControl(106).setVisible(False)
        self.setFocusId(102)
        self.log("prepareConfig return")


    def updateListing(self, channel = -1):
        self.log("updateListing")
        start = 0
        end = 200

        if channel > -1:
            start = channel - 1
            end = channel

        for i in range(start, end):
            theitem = self.listcontrol.getListItem(i)
            chantype = 9999
            chansetting1 = ''
            chansetting2 = ''
            newlabel = ''

            try:
                chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_1")
                chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_2")
            except:
                pass

            if chantype == 0:
                newlabel = self.getSmartPlaylistName(chansetting1)
            elif chantype == 1 or chantype == 2 or chantype == 5 or chantype == 6:
                newlabel = chansetting1
            elif chantype == 3:
                newlabel = chansetting1 + " TV"
            elif chantype == 4:
                newlabel = chansetting1 + " Movies"
            elif chantype == 7:
                if chansetting1[-1] == '/' or chansetting1[-1] == '\\':
                    newlabel = os.path.split(chansetting1[:-1])[1]
                else:
                    newlabel = os.path.split(chansetting1)[1]

            theitem.setLabel2(newlabel)

        self.log("updateListing return")



__cwd__ = REAL_SETTINGS.getAddonInfo('path')


mydialog = ConfigWindow("script.pseudotv.ChannelConfig.xml", __cwd__, "default")
del mydialog

########NEW FILE########
__FILENAME__ = default
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.


import xbmc, xbmcgui
import xbmcaddon


# Script constants
__scriptname__ = "PseudoTV"
__author__     = "Jason102"
__url__        = "http://github.com/Jasonra/XBMC-PseudoTV"
__settings__   = xbmcaddon.Addon(id='script.pseudotv')
__cwd__        = __settings__.getAddonInfo('path')


# Adapting a solution from ronie (http://forum.xbmc.org/showthread.php?t=97353)
if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True":
    xbmcgui.Window(10000).setProperty("PseudoTVRunning", "True")    
    shouldrestart = False

    if xbmc.executehttpapi("GetGuiSetting(1, services.webserver)")[4:] == "False":
        try:
            forcedserver = __settings__.getSetting("ForcedWebServer") == "True"
        except:
            forcedserver = False

        if forcedserver == False:
            dlg = xbmcgui.Dialog()
            retval = dlg.yesno('PseudoTV', 'PseudoTV will run more efficiently with the web', 'server enabled.  Would you like to turn it on?')
            __settings__.setSetting("ForcedWebServer", "True")

            if retval:
                xbmc.executehttpapi("SetGUISetting(3, services.webserverport, 8152)")
                xbmc.executehttpapi("SetGUISetting(1, services.webserver, true)")
                dlg.ok('PseudoTV', 'XBMC needs to shutdown in order to apply the', 'changes.')
                xbmc.executebuiltin("RestartApp()")
                shouldrestart = True

    if shouldrestart == False:
        xbmc.executebuiltin('RunScript("' + __cwd__ + '/pseudotv.py' + '")')
else:
    xbmc.log('script.PseudoTV - Already running, exiting', xbmc.LOGERROR)

########NEW FILE########
__FILENAME__ = pseudotv
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os, threading
import xbmc, xbmcgui
import xbmcaddon

from resources.lib.Globals import *



# Script constants
__scriptname__ = "PseudoTV"
__author__     = "Jason102"
__url__        = "http://github.com/Jasonra/XBMC-PseudoTV"
__version__    = VERSION
__settings__   = xbmcaddon.Addon(id='script.pseudotv')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')


import resources.lib.Overlay as Overlay


MyOverlayWindow = Overlay.TVOverlay("script.pseudotv.TVOverlay.xml", __cwd__, "default")

for curthread in threading.enumerate():
    try:
        log("Active Thread: " + str(curthread.name), xbmc.LOGERROR)

        if curthread.name != "MainThread":
            try:
                curthread.join()
            except:
                pass

            log("Joined " + curthread.name)
    except:
        pass

del MyOverlayWindow
xbmcgui.Window(10000).setProperty("PseudoTVRunning", "False")


########NEW FILE########
__FILENAME__ = AdvancedConfig
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from Globals import *
from ChannelList import ChannelList
from Rules import *



class AdvancedConfig(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.setCoordinateResolution(1)
        self.ruleList = []
        self.allRules = RulesList()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('AdvancedConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")
        self.listOffset = 0
        self.lineSelected = 0
        self.optionRowOffset = 0
        self.optionRowSelected = 0
        self.selectedRuleIndex = -1
        self.makeList()
        self.wasSaved = False
        self.log("onInit return")


    def onFocus(self, controlId):
        pass


    def onAction(self, act):
        action = act.getId()
        self.log("onAction " + str(action))
        focusid = 0

        try:
            focusid = self.getFocusId()
            self.log("focus id is " + str(focusid))
        except:
            pass

        if focusid >= 160:
            self.getControl(focusid).setLabel(self.ruleList[self.selectedRuleIndex].onAction(act, (focusid - 160) + (self.optionRowOffset * 2)))

        if action in ACTION_PREVIOUS_MENU:
            if self.selectedRuleIndex > -1:
                xbmc.executebuiltin("SetProperty(itempress,100)")
                xbmc.executebuiltin("Control.SetFocus(120)")
                self.lineSelected = 0
                self.onClick(130)
            else:
                dlg = xbmcgui.Dialog()

                if dlg.yesno("Save", "Would you like to save your changes?"):
                    self.saveRules()

                self.close()
        elif action == ACTION_MOVE_DOWN:
            if focusid > 119 and focusid < (120 + RULES_PER_PAGE):
                # If we highlighted the last rule previously and are now pressing arrow down
                if (focusid == (119 + RULES_PER_PAGE)) and (self.lineSelected == (RULES_PER_PAGE - 1)):
                    curoffset = self.listOffset
                    self.scrollDownList()

                    if self.listOffset != curoffset:
                        xbmc.executebuiltin("Control.SetFocus(" + str(119 + RULES_PER_PAGE) + ")")
                else:
                    self.lineSelected = focusid - 120
            elif (focusid >= 160) and (focusid < 164):
                self.log("Down on option")

                if focusid > 161:
                    if self.optionRowSelected == 1:
                        self.scrollOptionsDown()

                        # If we're actually offset, then make sure that the top options don't have a
                        # control-up value
                        if self.optionRowOffset > 0:
                            self.getControl(160).controlUp(self.getControl(160))
                            self.getControl(161).controlUp(self.getControl(161))
                    else:
                        self.optionRowSelected = 1
        elif action == ACTION_MOVE_UP:
            if focusid > 119 and focusid < (120 + RULES_PER_PAGE):
                # If we highlighted the last rule previously and are now pressing arrow down
                if (focusid == 120) and (self.lineSelected == 0):
                    curoffset = self.listOffset
                    self.scrollUpList()

                    if self.listOffset != curoffset:
                        xbmc.executebuiltin("Control.SetFocus(120)")
                else:
                    self.lineSelected = focusid - 120
            elif (focusid >= 160) and (focusid < 164):
                if focusid < 162:
                    if self.optionRowSelected == 0:
                        self.scrollOptionsUp()
    
                        # If we're not offset, make sure that the top options have a
                        # control-up value
                        if self.optionRowOffset == 0:
                            self.getControl(160).controlUp(self.getControl(131))
                            self.getControl(161).controlUp(self.getControl(131))
                    else:
                        self.optionRowSelected = 0
        elif action == ACTION_MOVE_LEFT:
            try:
                if self.getFocusId() == 131:
                    self.scrollRulesLeft()
            except:
                pass
        elif action == ACTION_MOVE_RIGHT:
            try:
                if self.getFocusId() == 131:
                    self.scrollRulesRight()
            except:
                pass


    def scrollOptionsUp(self):
        self.log("scrollOptionsUp")

        if self.optionRowOffset == 0:
            return

        self.optionRowOffset -= 1
        self.setupOptions()


    def scrollOptionsDown(self):
        self.log("scrollOptionsDown")
        allowedrows = (self.ruleList[self.selectedRuleIndex].getOptionCount() / 2) + (self.ruleList[self.selectedRuleIndex].getOptionCount() % 2)

        if allowedrows <= (self.optionRowOffset + 2):
            return

        self.optionRowOffset += 1
        self.setupOptions()


    def setupOptions(self):
        for i in range(4):
            if i < (self.ruleList[self.selectedRuleIndex].getOptionCount() - (self.optionRowOffset * 2)):
                self.getControl(i + 150).setVisible(True)
                self.getControl(i + 150).setLabel(self.ruleList[self.selectedRuleIndex].getOptionLabel(i + (self.optionRowOffset * 2)))
                self.getControl(i + 160).setVisible(True)
                self.getControl(i + 160).setEnabled(True)
                self.getControl(i + 160).setLabel(self.ruleList[self.selectedRuleIndex].getOptionValue(i + (self.optionRowOffset * 2)))
            else:
                self.getControl(i + 150).setVisible(False)
                self.getControl(i + 160).setVisible(False)


    def scrollRulesLeft(self):
        self.log("scrollRulesLeft")

        if self.selectedRuleIndex >= 0:
            curid = self.ruleList[self.selectedRuleIndex].getId()

            for i in range(self.allRules.getRuleCount()):
                if self.allRules.getRule(i).getId() == curid:
                    self.ruleList[self.selectedRuleIndex] = self.allRules.getRule(i - 1).copy()
                    break

            self.setRuleControls(self.selectedRuleIndex - self.listOffset)


    def scrollRulesRight(self):
        self.log("scrollRulesRight")

        if self.selectedRuleIndex >= 0:
            curid = self.ruleList[self.selectedRuleIndex].getId()

            for i in range(self.allRules.getRuleCount()):
                if self.allRules.getRule(i).getId() == curid:
                    self.ruleList[self.selectedRuleIndex] = self.allRules.getRule(i + 1).copy()
                    break

            self.setRuleControls(self.selectedRuleIndex - self.listOffset)


    def saveRules(self):
        self.wasSaved = True


    def scrollDownList(self):
        if len(self.ruleList) > self.listOffset + (RULES_PER_PAGE - 1):
            self.listOffset += 1
            self.makeList()


    def scrollUpList(self):
        if self.listOffset > 0:
            self.listOffset -= 1
            self.makeList()


    def makeList(self):
        self.log("makeList")

        if self.listOffset + (RULES_PER_PAGE - 1) > len(self.ruleList):
            self.listOffset = len(self.ruleList) - (RULES_PER_PAGE - 1)

        if self.listOffset < 0:
            self.listOffset = 0

        for i in range(RULES_PER_PAGE):
            if self.listOffset + i < len(self.ruleList):
                self.getControl(120 + i).setLabel(str(i + 1 + self.listOffset) + ". " + self.ruleList[i + self.listOffset].getTitle())
                self.getControl(120 + i).setEnabled(True)

                if i < (RULES_PER_PAGE - 1):
                    self.getControl(120 + i).controlDown(self.getControl(121 + i))

                if i > 0:
                    self.getControl(120 + i).controlUp(self.getControl(119 + i))
            else:
                if self.listOffset + i == len(self.ruleList):
                    self.getControl(120 + i).setLabel(str(i + 1 + self.listOffset) + ".")
                    self.getControl(120 + i).controlDown(self.getControl(120 + i))
                    self.getControl(120 + i).setEnabled(True)

                    if i > 0:
                        self.getControl(120 + i).controlUp(self.getControl(119 + i))
                else:
                    self.getControl(120 + i).setLabel('')
                    self.getControl(120 + i).setEnabled(False)

        self.log("makeList return")


    def getRuleName(self, ruleindex):
        if ruleindex < 0 or ruleindex >= len(self.ruleList):
            return ""

        return self.ruleList[ruleindex].getName()


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

        if controlId >= 120 and controlId <= (119 + RULES_PER_PAGE):
            self.optionRowSelected = 0
            self.optionRowOffset = 0
            self.setRuleControls(controlId - 120)
            self.getControl(160).controlUp(self.getControl(131))
            self.getControl(161).controlUp(self.getControl(131))
        elif controlId == 130:
            self.listOffset = self.selectedRuleIndex - 1
            self.selectedRuleIndex = -1
            self.consolidateRules()
            self.makeList()


    def consolidateRules(self):
        self.log("consolidateRules")
        index = 0

        for i in range(len(self.ruleList)):
            if index >= len(self.ruleList):
                break

            if self.ruleList[index].getId() == 0:
                self.ruleList.pop(index)
            else:
                index += 1

        self.log("count is " + str(len(self.ruleList)))


    def setRuleControls(self, listindex):
        self.log("setRuleControls")
        self.selectedRuleIndex = listindex + self.listOffset
        self.getControl(130).setLabel("Rule " + str(self.selectedRuleIndex + 1) + " Configuration")

        if self.selectedRuleIndex >= len(self.ruleList):
            self.ruleList.append(BaseRule())

        strlen = len(self.getRuleName(self.selectedRuleIndex))
        spacesstr = ''

        for i in range(20 - strlen / 2):
            spacesstr += ' '

        self.getControl(131).setLabel('<-' + spacesstr + self.getRuleName(self.selectedRuleIndex) + spacesstr + '->')
        self.setupOptions()

########NEW FILE########
__FILENAME__ = Channel
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

from Playlist import Playlist
from Globals import *
from Rules import *



class Channel:
    def __init__(self):
        self.Playlist = Playlist()
        self.name = ''
        self.playlistPosition = 0
        self.showTimeOffset = 0
        self.lastAccessTime = 0
        self.totalTimePlayed = 0
        self.fileName = ''
        self.isPaused = False
        self.isValid = False
        self.isRandom = False
        self.mode = 0
        self.ruleList = []
        self.channelNumber = 0
        self.isSetup = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Channel: ' + msg, level)


    def setPlaylist(self, filename):
        return self.Playlist.load(filename)


    def loadRules(self, channel):
        del self.ruleList[:]
        listrules = RulesList()
        self.channelNumber = channel

        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))

            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))

                for rule in listrules.ruleList:
                    if rule.getId() == ruleid:
                        self.ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))

                        self.log("Added rule - " + self.ruleList[-1].getTitle())
                        break
        except:
            self.ruleList = []


    def setPaused(self, paused):
        self.isPaused = paused


    def setShowTime(self, thetime):
        self.showTimeOffset = thetime // 1


    def setShowPosition(self, show):
        show = int(show)
        self.playlistPosition = self.fixPlaylistIndex(show)


    def setAccessTime(self, thetime):
        self.lastAccessTime = thetime // 1


    def getCurrentDuration(self):
        return self.getItemDuration(self.playlistPosition)


    def getItemDuration(self, index):
        return self.Playlist.getduration(self.fixPlaylistIndex(index))


    def getTotalDuration(self):
        return self.Playlist.totalDuration


    def getCurrentDescription(self):
        return self.getItemDescription(self.playlistPosition)


    def getItemDescription(self, index):
        return self.Playlist.getdescription(self.fixPlaylistIndex(index))


    def getCurrentEpisodeTitle(self):
        return self.getItemEpisodeTitle(self.playlistPosition)


    def getItemEpisodeTitle(self, index):
        return self.Playlist.getepisodetitle(self.fixPlaylistIndex(index))


    def getCurrentTitle(self):
        return self.getItemTitle(self.playlistPosition)


    def getItemTitle(self, index):
        return self.Playlist.getTitle(self.fixPlaylistIndex(index))


    def getCurrentFilename(self):
        return self.getItemFilename(self.playlistPosition)


    def getItemFilename(self, index):
        return self.Playlist.getfilename(self.fixPlaylistIndex(index))


    def fixPlaylistIndex(self, index):
        if self.Playlist.size() == 0:
            return index

        while index >= self.Playlist.size():
            index -= self.Playlist.size()

        while index < 0:
            index += self.Playlist.size()

        return index


    def addShowPosition(self, addition):
        self.setShowPosition(self.playlistPosition + addition)

########NEW FILE########
__FILENAME__ = ChannelList
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random
import httplib
import base64


from xml.dom.minidom import parse, parseString

from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser
from FileAccess import FileLock, FileAccess



class ChannelList:
    def __init__(self):
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.showList = []
        self.channels = []
        self.videoParser = VideoParser()
        self.httpJSON = True
        self.sleepTime = 0
        self.discoveredWebServer = False
        self.threadPaused = False
        self.runningActionChannel = 0
        self.runningActionId = 0
        self.enteredChannelCount = 0
        self.background = True
        random.seed()


    def readConfig(self):
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.updateDialog = xbmcgui.DialogProgress()
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.incIceLibrary = REAL_SETTINGS.getSetting('IncludeIceLib') == "true"
        self.log("IceLibrary is " + str(self.incIceLibrary))
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.findMaxChannels()

        if self.forceReset:
            REAL_SETTINGS.setSetting('ForceChannelReset', "False")
            self.forceReset = False

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except:
            self.lastResetTime = 0

        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except:
            self.lastExitTime = int(time.time())


    def setupList(self):
        self.readConfig()
        self.updateDialog.create("PseudoTV", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")
        self.updateDialogProgress = 0
        foundvalid = False
        makenewlists = False
        self.background = False

        if self.backgroundUpdating > 0 and self.myOverlay.isMaster == True:
            makenewlists = True

        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.updateDialogProgress = i * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(i + 1), "waiting for file lock")
            self.channels.append(Channel())

            # If the user pressed cancel, stop everything and exit
            if self.updateDialog.iscanceled():
                self.log('Update channels cancelled')
                self.updateDialog.close()
                return None

            self.setupChannel(i + 1, False, makenewlists, False)

            if self.channels[i].isValid:
                foundvalid = True

        if makenewlists == True:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')

        if foundvalid == False and makenewlists == False:
            for i in range(self.maxChannels):
                self.updateDialogProgress = i * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(i + 1), "waiting for file lock", '')
                self.setupChannel(i + 1, False, True, False)

                if self.channels[i].isValid:
                    foundvalid = True
                    break

        self.updateDialog.update(100, "Update complete")
        self.updateDialog.close()

        return self.channels


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)


    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        self.maxChannels = 0
        self.enteredChannelCount = 0

        for i in range(999):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''

            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
            except:
                pass

            if chtype == 0:
                if FileAccess.exists(xbmc.translatePath(chsetting1)):
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype < 8:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1

            if self.forceReset and (chtype != 9999):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', "True")

        self.log('findMaxChannels return ' + str(self.maxChannels))


    def determineWebServer(self):
        if self.discoveredWebServer:
            return

        self.discoveredWebServer = True
        self.webPort = 8080
        self.webUsername = ''
        self.webPassword = ''
        fle = xbmc.translatePath("special://profile/guisettings.xml")

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("determineWebServer Unable to open the settings file", xbmc.LOGERROR)
            self.httpJSON = False
            return

        try:
            dom = parse(xml)
        except:
            self.log('determineWebServer Unable to parse settings file', xbmc.LOGERROR)
            self.httpJSON = False
            return

        xml.close()

        try:
            plname = dom.getElementsByTagName('webserver')
            self.httpJSON = (plname[0].childNodes[0].nodeValue.lower() == 'true')
            self.log('determineWebServer is ' + str(self.httpJSON))

            if self.httpJSON == True:
                plname = dom.getElementsByTagName('webserverport')
                self.webPort = int(plname[0].childNodes[0].nodeValue)
                self.log('determineWebServer port ' + str(self.webPort))
                plname = dom.getElementsByTagName('webserverusername')
                self.webUsername = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer username ' + self.webUsername)
                plname = dom.getElementsByTagName('webserverpassword')
                self.webPassword = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer password is ' + self.webPassword)
        except:
            return


    # Code for sending JSON through http adapted from code by sffjunkie (forum.xbmc.org/showthread.php?t=92196)
    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
        usedhttp = False

        self.determineWebServer()

        if USING_EDEN:
            command = command.replace('fields', 'properties')

        # If there have been problems using the server, just skip the attempt and use executejsonrpc
        if self.httpJSON == True:
            try:
                payload = command.encode('utf-8')
            except:
                return data

            headers = {'Content-Type': 'application/json-rpc; charset=utf-8'}

            if self.webUsername != '':
                userpass = base64.encodestring('%s:%s' % (self.webUsername, self.webPassword))[:-1]
                headers['Authorization'] = 'Basic %s' % userpass

            try:
                conn = httplib.HTTPConnection('127.0.0.1', self.webPort)
                conn.request('POST', '/jsonrpc', payload, headers)
                response = conn.getresponse()

                if response.status == 200:
                    data = response.read()
                    usedhttp = True

                conn.close()
            except:
                self.log("Exception when getting JSON data")

        if usedhttp == False:
            self.httpJSON = False
            data = xbmc.executeJSONRPC(command)

        return data


    def setupChannel(self, channel, background = False, makenewlist = False, append = False):
        self.log('setupChannel ' + str(channel))
        returnval = False
        createlist = makenewlist
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        needsreset = False
        self.background = background
        self.settingChannel = channel

        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
        except:
            pass

        while len(self.channels) < channel:
            self.channels.append(Channel())

        if chtype == 9999:
            self.channels[channel - 1].isValid = False
            return False

        self.channels[channel - 1].isSetup = True
        self.channels[channel - 1].loadRules(channel)
        self.runActions(RULES_ACTION_START, channel, self.channels[channel - 1])
        GlobalFileLock.lockFile(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', True)

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
        except:
            pass

        # If possible, use an existing playlist
        # Don't do this if we're appending an existing channel
        # Don't load if we need to reset anyway
        if FileAccess.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') and append == False and needsreset == False:
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time', True))
                createlist = True

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "reading playlist", '')

                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True

                    # If this channel has been watched for longer than it lasts, reset the channel
                    if self.channelResetSetting == 0 and self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                        createlist = False

                    if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        timedif = time.time() - self.lastResetTime

                        if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                            createlist = False

                        if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                            createlist = False

                        if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                            createlist = False

                        if timedif < 0:
                            createlist = False

                    if self.channelResetSetting == 4:
                        createlist = False
            except:
                pass

        if createlist or needsreset:
            self.channels[channel - 1].isValid = False

            if makenewlist:
                try:
                    os.remove(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
                except:
                    pass

                append = False

                if createlist:
                    ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))

        if append == False:
            if chtype == 6 and chsetting2 == str(MODE_ORDERAIRDATE):
                self.channels[channel - 1].mode = MODE_ORDERAIRDATE

            # if there is no start mode in the channel mode flags, set it to the default
            if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
                if self.startMode == 0:
                    self.channels[channel - 1].mode |= MODE_RESUME
                elif self.startMode == 1:
                    self.channels[channel - 1].mode |= MODE_REALTIME
                elif self.startMode == 2:
                    self.channels[channel - 1].mode |= MODE_RANDOM

        if ((createlist or needsreset) and makenewlist) or append:
            if self.background == False:
                self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding videos", '')

            if self.makeChannelList(channel, chtype, chsetting1, chsetting2, append) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    returnval = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    self.channels[channel - 1].isValid = True

                    # Don't reset variables on an appending channel
                    if append == False:
                        self.channels[channel - 1].totalTimePlayed = 0
                        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')

                        if needsreset:
                            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')

        self.runActions(RULES_ACTION_BEFORE_CLEAR, channel, self.channels[channel - 1])

        # Don't clear history when appending channels
        if self.background == False and append == False and self.myOverlay.isMaster:
            self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "clearing history", '')
            self.clearPlaylistHistory(channel)

        GlobalFileLock.unlockFile(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')

        if append == False:
            self.runActions(RULES_ACTION_BEFORE_TIME, channel, self.channels[channel - 1])

            if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
                self.channels[channel - 1].isPaused = True

            if self.channels[channel - 1].mode & MODE_RANDOM > 0:
                self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

            if self.channels[channel - 1].mode & MODE_REALTIME > 0:
                timedif = int(self.myOverlay.timeStarted) - self.lastExitTime
                self.channels[channel - 1].totalTimePlayed += timedif

            if self.channels[channel - 1].mode & MODE_RESUME > 0:
                self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
                self.channels[channel - 1].totalTimePlayed = 0

            while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
                self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, chsetting1)

        if ((createlist or needsreset) and makenewlist) and returnval:
            self.runActions(RULES_ACTION_FINAL_MADE, channel, self.channels[channel - 1])
        else:
            self.runActions(RULES_ACTION_FINAL_LOADED, channel, self.channels[channel - 1])

        return returnval


    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("channel not valid, ignoring")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > (60 * 60 * 24 * 2):
            try:
                fle = FileAccess.open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            flewrite = "#EXTM3U\n"
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 12)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i)
                    tmpstr = tmpstr[:600]
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = tmpstr + '\n' + self.channels[channel - 1].getItemFilename(i)
                    flewrite += "#EXTINF:" + tmpstr + "\n"
                else:
                    timeremoved = tottime

            fle.write(flewrite)
            fle.close()

            if timeremoved > 0:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == False:
                    self.channels[channel - 1].isValid = False
                else:
                    self.channels[channel - 1].totalTimePlayed -= timeremoved
                    # Write this now so anything sharing the playlists will get the proper info
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', str(self.channels[channel - 1].totalTimePlayed))


    def getChannelName(self, chtype, setting1):
        self.log('getChannelName ' + str(chtype))

        if len(setting1) == 0:
            return ''

        if chtype == 0:
            return self.getSmartPlaylistName(setting1)
        elif chtype == 1 or chtype == 2 or chtype == 5 or chtype == 6:
            return setting1
        elif chtype == 3:
            return setting1 + " TV"
        elif chtype == 4:
            return setting1 + " Movies"
        elif chtype == 7:
            if setting1[-1] == '/' or setting1[-1] == '\\':
                return os.path.split(setting1[:-1])[1]
            else:
                return os.path.split(setting1)[1]

        return ''


    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("getSmartPlaylisyName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''


    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, append = False):
        self.log('makeChannelList ' + str(channel))
        israndom = False
        fileList = []

        if chtype == 7:
            fileList = self.createDirectoryPlaylist(setting1)
            israndom = True
        else:
            if chtype == 0:
                if FileAccess.copy(setting1, MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                    if FileAccess.exists(MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                        self.log("Unable to copy or find playlist " + setting1)
                        return False

                fle = MADE_CHAN_LOC + os.path.split(setting1)[1]
            else:
                fle = self.makeTypePlaylist(chtype, setting1, setting2)

            fle = xbmc.translatePath(fle)

            if len(fle) == 0:
                self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
                return False

            try:
                xml = FileAccess.open(fle, "r")
            except:
                self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
                return False

            try:
                dom = parse(xml)
            except:
                self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
                xml.close()
                return False

            xml.close()

            if self.getSmartPlaylistType(dom) == 'mixed':
                fileList = self.buildMixedFileList(dom, channel)
            else:
                fileList = self.buildFileList(fle, channel)

            try:
                order = dom.getElementsByTagName('order')

                if order[0].childNodes[0].nodeValue.lower() == 'random':
                    israndom = True
            except:
                pass

        try:
            if append == True:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r+")
                channelplaylist.seek(0, 2)
            else:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            channelplaylist.write("#EXTM3U\n")

        if len(fileList) == 0:
            self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
            channelplaylist.close()
            return False

        if israndom:
            random.shuffle(fileList)

        if len(fileList) > 4096:
            fileList = fileList[:4096]

        fileList = self.runActions(RULES_ACTION_LIST, channel, fileList)
        self.channels[channel - 1].isRandom = israndom

        if append:
            if len(fileList) + self.channels[channel - 1].Playlist.size() > 4096:
                fileList = fileList[:(4096 - self.channels[channel - 1].Playlist.size())]
        else:
            if len(fileList) > 4096:
                fileList = fileList[:4096]

        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write("#EXTINF:" + string + "\n")

        channelplaylist.close()
        self.log('makeChannelList return')
        return True


    def makeTypePlaylist(self, chtype, setting1, setting2):
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()

            return self.createNetworkPlaylist(setting1)
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()

            return self.createStudioPlaylist(setting1)
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()

            return self.createGenrePlaylist('episodes', chtype, setting1)
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()

            return self.createGenrePlaylist('movies', chtype, setting1)
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())

            return self.createGenreMixedPlaylist(setting1)
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()

            return self.createShowPlaylist(setting1, setting2)

        self.log('makeTypePlaylists invalid channel type: ' + str(chtype))
        return ''


    def createNetworkPlaylist(self, network):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Network_' + network + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, network))
        network = network.lower()
        added = False

        for i in range(len(self.showList)):
            if self.threadPause() == False:
                fle.close()
                return ''

            if self.showList[i][1].lower() == network:
                theshow = self.cleanString(self.showList[i][0])
                fle.write('    <rule field="tvshow" operator="is">' + theshow + '</rule>\n')
                added = True

        self.writeXSPFooter(fle, 0, "random")
        fle.close()

        if added == False:
            return ''

        return flename


    def createShowPlaylist(self, show, setting2):
        order = 'random'

        try:
            setting = int(setting2)

            if setting & MODE_ORDERAIRDATE > 0:
                order = 'airdate'
        except:
            pass

        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + show + '_' + order + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, show))
        show = self.cleanString(show)
        fle.write('    <rule field="tvshow" operator="is">' + show + '</rule>\n')
        self.writeXSPFooter(fle, 0, order)
        fle.close()
        return flename


    def createGenreMixedPlaylist(self, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Mixed_' + genre + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, genre))
        genre = self.cleanString(genre)
        fle.write('    <rule field="genre" operator="is">' + genre + '</rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, studio))
        studio = self.cleanString(studio)
        fle.write('    <rule field="studio" operator="is">' + studio + '</rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createDirectoryPlaylist(self, setting1):
        self.log("createDirectoryPlaylist " + setting1)
        fileList = []
        filecount = 0
        json_query = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "files"}, "id": 1}' % ( self.escapeDirJSON(setting1),)

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "getting file list")

        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        thedir = ''

        if setting1[-1:1] == '/' or setting1[-1:1] == '\\':
            thedir = os.path.split(setting1[:-1])[1]
        else:
            thedir = os.path.split(setting1)[1]

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break

            match = re.search('"file" *: *"(.*?)",', f)

            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    fileList.extend(self.createDirectoryPlaylist(match.group(1).replace("\\\\", "\\")))
                else:
                    duration = self.videoParser.getVideoLength(match.group(1).replace("\\\\", "\\"))

                    if duration > 0:
                        filecount += 1

                        if self.background == False:
                            if filecount == 1:
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entry")
                            else:
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entries")

                        afile = os.path.split(match.group(1).replace("\\\\", "\\"))[1]
                        afile, ext = os.path.splitext(afile)
                        tmpstr = str(duration) + ','
                        tmpstr += afile + "//" + thedir + "//"
                        tmpstr = tmpstr[:600]
                        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                        tmpstr += "\n" + match.group(1).replace("\\\\", "\\")
                        fileList.append(tmpstr)

        if filecount == 0:
            self.log(json_folder_detail)

        return fileList


    def writeXSPHeader(self, fle, pltype, plname):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="' + pltype + '">\n')
        plname = self.cleanString(plname)
        fle.write('    <name>' + plname + '</name>\n')
        fle.write('    <match>one</match>\n')


    def writeXSPFooter(self, fle, limit, order):
        if limit > 0:
            fle.write('    <limit>' + str(limit) + '</limit>\n')

        fle.write('    <order direction="ascending">' + order + '</order>\n')
        fle.write('</smartplaylist>\n')


    def cleanString(self, string):
        newstr = string
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        return newstr


    def fillTVInfo(self, sortbycount = False):
        self.log("fillTVInfo")
        json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"fields":["studio", "genre"]}, "id": 1}'

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "reading TV data")

        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                return

            match = re.search('"studio" *: *"(.*?)",', f)
            network = ''

            if match:
                found = False
                network = match.group(1).strip()

                for item in range(len(self.networkList)):
                    if self.threadPause() == False:
                        del self.networkList[:]
                        del self.showList[:]
                        del self.showGenreList[:]
                        return

                    itm = self.networkList[item]

                    if sortbycount:
                        itm = itm[0]

                    if itm.lower() == network.lower():
                        found = True

                        if sortbycount:
                            self.networkList[item][1] += 1

                        break

                if found == False and len(network) > 0:
                    if sortbycount:
                        self.networkList.append([network, 1])
                    else:
                        self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = match.group(1).strip()
                self.showList.append([show, network])

            match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip()

                    for g in range(len(self.showGenreList)):
                        if self.threadPause() == False:
                            del self.networkList[:]
                            del self.showList[:]
                            del self.showGenreList[:]
                            return

                        itm = self.showGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.showGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.showGenreList.append([genre.strip(), 1])
                        else:
                            self.showGenreList.append(genre.strip())

        if sortbycount:
            self.networkList.sort(key=lambda x: x[1], reverse = True)
            self.showGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.networkList.sort(key=lambda x: x.lower())
            self.showGenreList.sort(key=lambda x: x.lower())

        if (len(self.showList) == 0) and (len(self.showGenreList) == 0) and (len(self.networkList) == 0):
            self.log(json_folder_detail)

        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self, sortbycount = False):
        self.log("fillMovieInfo")
        studioList = []
        json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"fields":["studio", "genre"]}, "id": 1}'

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "reading movie data")

        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip()

                    for g in range(len(self.movieGenreList)):
                        itm = self.movieGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.movieGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.movieGenreList.append([genre.strip(), 1])
                        else:
                            self.movieGenreList.append(genre.strip())

            match = re.search('"studio" *: *"(.*?)",', f)

            if match:
                studios = match.group(1).split('/')

                for studio in studios:
                    curstudio = studio.strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True
                            break

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount

            counteditems += itemcount

        if sortbycount:
            studioList.sort(key=lambda x: x[1], reverse=True)
            self.movieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            studioList.sort(key=lambda x: x[0].lower())
            self.movieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(studioList)):
            if studioList[i][1] >= bestmatch:
                if sortbycount:
                    self.studioList.append([studioList[i][0], studioList[i][1]])
                else:
                    self.studioList.append(studioList[i][0])

        if (len(self.movieGenreList) == 0) and (len(self.studioList) == 0):
            self.log(json_folder_detail)

        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        self.log("makeMixedList return " + str(newlist))
        return newlist


    def buildFileList(self, dir_name, channel):
        self.log("buildFileList")
        fileList = []
        seasoneplist = []
        filecount = 0
        json_query = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "fields":["season","episode","playcount","streamdetails","duration","runtime","tagline","showtitle","album","artist","plot"]}, "id": 1}' % (self.escapeDirJSON(dir_name))

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "querying database")

        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break

            match = re.search('"file" *: *"(.*?)",', f)
            istvshow = False

            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    fileList.extend(self.buildFileList(match.group(1), channel))
                else:
                    f = self.runActions(RULES_ACTION_JSON, channel, f)
                    duration = re.search('"duration" *: *([0-9]*?),', f)

                    try:
                        dur = int(duration.group(1))
                    except:
                        dur = 0

                    # If duration doesn't exist, try to figure it out
                    if dur == 0:
                        dur = self.videoParser.getVideoLength(match.group(1).replace("\\\\", "\\"))

                    # As a last resort (since it's not as accurate), use runtime
                    if dur == 0:
                        duration = re.search('"runtime" *: *"([0-9]*?)",', f)

                        try:
                            # Runtime is reported in minutes
                            dur = int(duration.group(1)) * 60
                        except:
                            dur = 0

                    # Remove any file types that we don't want (ex. IceLibrary)
                    if self.incIceLibrary == False:
                        if match.group(1).replace("\\\\", "\\")[-4:].lower() == 'strm':
                            dur = 0

                    try:
                        if dur > 0:
                            filecount += 1
                            seasonval = -1
                            epval = -1

                            if self.background == False:
                                if filecount == 1:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entry")
                                else:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entries")

                            title = re.search('"label" *: *"(.*?)"', f)
                            tmpstr = str(dur) + ','
                            showtitle = re.search('"showtitle" *: *"(.*?)"', f)
                            plot = re.search('"plot" *: *"(.*?)",', f)

                            if plot == None:
                                theplot = ""
                            else:
                                theplot = plot.group(1)

                            # This is a TV show
                            if showtitle != None and len(showtitle.group(1)) > 0:
                                season = re.search('"season" *: *(.*?),', f)
                                episode = re.search('"episode" *: *(.*?),', f)
                                swtitle = title.group(1)

                                try:
                                    seasonval = int(season.group(1))
                                    epval = int(episode.group(1))
                                    
                                    if self.showSeasonEpisode:
                                        swtitle = swtitle + '(S' + ('0' if seasonval < 10 else '') + str(seasonval) + ' E' + ('0' if epval < 10 else '') + str(epval) + ')'
                                except:
                                    seasonval = -1
                                    epval = -1

                                tmpstr += showtitle.group(1) + "//" + swtitle + "//" + theplot
                                istvshow = True
                            else:
                                tmpstr += title.group(1) + "//"
                                album = re.search('"album" *: *"(.*?)"', f)

                                # This is a movie
                                if album == None or len(album.group(1)) == 0:
                                    tagline = re.search('"tagline" *: *"(.*?)"', f)

                                    if tagline != None:
                                        tmpstr += tagline.group(1)

                                    tmpstr += "//" + theplot
                                else:
                                    artist = re.search('"artist" *: *"(.*?)"', f)
                                    tmpstr += album.group(1) + "//" + artist.group(1)

                            tmpstr = tmpstr[:600]
                            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                            tmpstr = tmpstr + '\n' + match.group(1).replace("\\\\", "\\")

                            if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
                                    seasoneplist.append([seasonval, epval, tmpstr])
                            else:
                                fileList.append(tmpstr)
                    except:
                        pass
            else:
                continue

        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])

            for seepitem in seasoneplist:
                fileList.append(seepitem[2])

        if filecount == 0:
            self.log(json_folder_detail)

        self.log("buildFileList return")
        return fileList


    def buildMixedFileList(self, dom1, channel):
        fileList = []
        self.log('buildMixedFileList')

        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if FileAccess.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                FileAccess.copy(xbmc.translatePath('special://profile/playlists/video/') + rulename, MADE_CHAN_LOC + rulename)
                fileList.extend(self.buildFileList(MADE_CHAN_LOC + rulename, channel))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename, channel))

        self.log("buildMixedFileList returning")
        return fileList


    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))
        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "processing rule " + str(index + 1), '')

                parameter = rule.runAction(action, self, parameter)

            index += 1

        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def threadPause(self):
        if threading.activeCount() > 1:
            while self.threadPaused == True and self.myOverlay.isExiting == False:
                time.sleep(self.sleepTime)

            # This will fail when using config.py
            try:
                if self.myOverlay.isExiting == True:
                    self.log("IsExiting")
                    return False
            except:
                pass

        return True


    def escapeDirJSON(self, dir_name):
        if (dir_name.find(":")):
            dir_name = dir_name.replace("\\", "\\\\")

        return dir_name


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''

########NEW FILE########
__FILENAME__ = ChannelListThread
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from ChannelList import ChannelList
from Channel import Channel
from Globals import *



class ChannelListThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.myOverlay = None
        sys.setcheckinterval(25)
        self.chanlist = ChannelList()
        self.paused = False
        self.fullUpdating = True


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelListThread: ' + msg, level)


    def run(self):
        self.log("Starting")
        self.chanlist.exitThread = False
        self.chanlist.readConfig()
        self.chanlist.sleepTime = 0.1

        if self.myOverlay == None:
            self.log("Overlay not defined. Exiting.")
            return
            
        self.chanlist.myOverlay = self.myOverlay
        self.fullUpdating = (self.myOverlay.backgroundUpdating == 0)
        validchannels = 0

        for i in range(self.myOverlay.maxChannels):
            self.chanlist.channels.append(Channel())

            if self.myOverlay.channels[i].isValid:
                validchannels += 1

        # Don't load invalid channels if minimum threading mode is on
        if self.fullUpdating and self.myOverlay.isMaster:
            if validchannels < self.chanlist.enteredChannelCount:
                xbmc.executebuiltin("Notification(PseudoTV, Background Loading..., 4000)")

            for i in range(self.myOverlay.maxChannels):
                if self.myOverlay.channels[i].isValid == False:
                    while True:
                        if self.myOverlay.isExiting:
                            self.log("Closing thread")
                            return

                        time.sleep(1)

                        if self.paused == False:
                            break

                    self.chanlist.channels[i].setAccessTime(self.myOverlay.channels[i].lastAccessTime)

                    try:
                        if self.chanlist.setupChannel(i + 1, True, True, False) == True:
                            while self.paused:
                                if self.myOverlay.isExiting:
                                    self.log("IsExiting")
                                    return

                                time.sleep(1)

                            self.myOverlay.channels[i] = self.chanlist.channels[i]

                            if self.myOverlay.channels[i].isValid == True:
                                xbmc.executebuiltin("Notification(PseudoTV, Channel " + str(i + 1) + " Added, 4000)")
                    except:
                        self.log("Unknown Channel Creation Exception", xbmc.LOGERROR)
                        self.log(traceback.format_exc(), xbmc.LOGERROR)
                        return

        REAL_SETTINGS.setSetting('ForceChannelReset', 'false')
        self.chanlist.sleepTime = 0.3

        while True:
            for i in range(self.myOverlay.maxChannels):
                modified = True

                while modified == True and self.myOverlay.channels[i].getTotalDuration() < PREP_CHANNEL_TIME and self.myOverlay.channels[i].Playlist.size() < 4000:
                    # If minimum updating is on, don't attempt to load invalid channels
                    if self.fullUpdating == False and self.myOverlay.channels[i].isValid == False and self.myOverlay.isMaster:
                        break

                    modified = False

                    if self.myOverlay.isExiting:
                        self.log("Closing thread")
                        return

                    time.sleep(2)
                    curtotal = self.myOverlay.channels[i].getTotalDuration()

                    if self.myOverlay.isMaster:
                        if curtotal > 0:
                            # When appending, many of the channel variables aren't set, so copy them over.
                            # This needs to be done before setup since a rule may use one of the values.
                            # It also needs to be done after since one of them may have changed while being setup.
                            self.chanlist.channels[i].playlistPosition = self.myOverlay.channels[i].playlistPosition
                            self.chanlist.channels[i].showTimeOffset = self.myOverlay.channels[i].showTimeOffset
                            self.chanlist.channels[i].lastAccessTime = self.myOverlay.channels[i].lastAccessTime
                            self.chanlist.channels[i].totalTimePlayed = self.myOverlay.channels[i].totalTimePlayed
                            self.chanlist.channels[i].isPaused = self.myOverlay.channels[i].isPaused
                            self.chanlist.channels[i].mode = self.myOverlay.channels[i].mode
                            # Only allow appending valid channels, don't allow erasing them
                            
                            try:
                                self.chanlist.setupChannel(i + 1, True, False, True)
                            except:
                                self.log("Unknown Channel Appending Exception", xbmc.LOGERROR)
                                self.log(traceback.format_exc(), xbmc.LOGERROR)
                                return

                            self.chanlist.channels[i].playlistPosition = self.myOverlay.channels[i].playlistPosition
                            self.chanlist.channels[i].showTimeOffset = self.myOverlay.channels[i].showTimeOffset
                            self.chanlist.channels[i].lastAccessTime = self.myOverlay.channels[i].lastAccessTime
                            self.chanlist.channels[i].totalTimePlayed = self.myOverlay.channels[i].totalTimePlayed
                            self.chanlist.channels[i].isPaused = self.myOverlay.channels[i].isPaused
                            self.chanlist.channels[i].mode = self.myOverlay.channels[i].mode
                        else:
                            try:
                                self.chanlist.setupChannel(i + 1, True, True, False)
                            except:
                                self.log("Unknown Channel Modification Exception", xbmc.LOGERROR)
                                self.log(traceback.format_exc(), xbmc.LOGERROR)
                                return
                    else:
                        try:
                            # We're not master, so no modifications...just try and load the channel
                            self.chanlist.setupChannel(i + 1, True, False, False)
                        except:
                            self.log("Unknown Channel Loading Exception", xbmc.LOGERROR)
                            self.log(traceback.format_exc(), xbmc.LOGERROR)
                            return

                    self.myOverlay.channels[i] = self.chanlist.channels[i]

                    if self.myOverlay.isMaster:
                        ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(self.myOverlay.channels[i].totalTimePlayed))

                    if self.myOverlay.channels[i].getTotalDuration() > curtotal and self.myOverlay.isMaster:
                        modified = True

                    # A do-while loop for the paused state
                    while True:
                        if self.myOverlay.isExiting:
                            self.log("Closing thread")
                            return

                        time.sleep(2)

                        if self.paused == False:
                            break

                timeslept = 0

            if self.fullUpdating == False and self.myOverlay.isMaster:
                return

            # If we're master, wait 30 minutes in between checks.  If not, wait 5 minutes.
            while (timeslept < 1800 and self.myOverlay.isMaster == True) or (timeslept < 300 and self.myOverlay.isMaster == False):
                if self.myOverlay.isExiting:
                    self.log("IsExiting")
                    return

                time.sleep(2)
                timeslept += 2

        self.log("All channels up to date.  Exiting thread.")


    def pause(self):
        self.paused = True
        self.chanlist.threadPaused = True


    def unpause(self):
        self.paused = False
        self.chanlist.threadPaused = False

########NEW FILE########
__FILENAME__ = EPGWindow
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime, traceback

from Playlist import Playlist
from Globals import *
from Channel import Channel



class EPGWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.focusRow = 0
        self.focusIndex = 0
        self.focusTime = 0
        self.focusEndTime = 0
        self.shownTime = 0
        self.centerChannel = 0
        self.rowCount = 6
        self.channelButtons = [None] * self.rowCount
        self.actionSemaphore = threading.BoundedSemaphore()
        self.lastActionTime = time.time()
        self.channelLogos = ''
        self.textcolor = "FFFFFFFF"
        self.focusedcolor = "FF7d7d7d"
        self.clockMode = 0

        # Decide whether to use the current skin or the default skin.  If the current skin has the proper
        # image, then it should work.
        if os.path.exists(xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', xbmc.getSkinDir(), 'media'))):
            self.mediaPath = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', xbmc.getSkinDir(), 'media')) + '/'
        elif os.path.exists(xbmc.translatePath('special://skin/media/' + ADDON_ID + '/' + TIME_BAR)):
            self.mediaPath = xbmc.translatePath('special://skin/media/' + ADDON_ID + '/')
        elif os.path.exists(xbmc.translatePath('special://skin/media/' + TIME_BAR)):
            self.mediaPath = xbmc.translatePath('special://skin/media/')
        elif xbmc.skinHasImage(xbmc.translatePath(ADDON_ID + '/' + TIME_BAR)):
            self.mediaPath = xbmc.translatePath(ADDON_ID + '/')
        elif xbmc.skinHasImage(TIME_BAR):
            self.mediaPath = ''
        else:
            self.mediaPath = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'

        self.log('Media Path is ' + self.mediaPath)

        # Use the given focus and non-focus textures if they exist.  Otherwise use the defaults.
        if os.path.exists(self.mediaPath + BUTTON_FOCUS):
            self.textureButtonFocus = self.mediaPath + BUTTON_FOCUS
        elif xbmc.skinHasImage(self.mediaPath + BUTTON_FOCUS):
            self.textureButtonFocus = self.mediaPath + BUTTON_FOCUS
        else:
            self.textureButtonFocus = 'button-focus.png'

        if os.path.exists(self.mediaPath + BUTTON_NO_FOCUS):
            self.textureButtonNoFocus = self.mediaPath + BUTTON_NO_FOCUS
        elif xbmc.skinHasImage(self.mediaPath + BUTTON_NO_FOCUS):
            self.textureButtonNoFocus = self.mediaPath + BUTTON_NO_FOCUS
        else:
            self.textureButtonNoFocus = 'button-nofocus.png'

        for i in range(self.rowCount):
            self.channelButtons[i] = []

        self.clockMode = ADDON_SETTINGS.getSetting("ClockMode")


    def onFocus(self, controlid):
        pass


    # set the time labels
    def setTimeLabels(self, thetime):
        self.log('setTimeLabels')
        now = datetime.datetime.fromtimestamp(thetime)
        self.getControl(104).setLabel(now.strftime('%A, %b %d'))
        delta = datetime.timedelta(minutes=30)

        for i in range(3):
            if self.clockMode == "0":
                self.getControl(101 + i).setLabel(now.strftime("%I:%M%p").lower())
            else:
                self.getControl(101 + i).setLabel(now.strftime("%H:%M"))

            now = now + delta

        self.log('setTimeLabels return')


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('EPGWindow: ' + msg, level)


    def onInit(self):
        self.log('onInit')
        timex, timey = self.getControl(120).getPosition()
        timew = self.getControl(120).getWidth()
        timeh = self.getControl(120).getHeight()
        self.currentTimeBar = xbmcgui.ControlImage(timex, timey, timew, timeh, self.mediaPath + TIME_BAR)
        self.addControl(self.currentTimeBar)

        try:
            textcolor = int(self.getControl(100).getLabel(), 16)
            focusedcolor = int(self.getControl(100).getLabel2(), 16)

            if textcolor > 0:
                self.textcolor = hex(textcolor)[2:]

            if focusedcolor > 0:
                self.focusedcolor = hex(focusedcolor)[2:]
        except:
            pass

        try:
            if self.setChannelButtons(time.time(), self.MyOverlayWindow.currentChannel) == False:
                self.log('Unable to add channel buttons')
                return

            curtime = time.time()
            self.focusIndex = -1
            basex, basey = self.getControl(113).getPosition()
            baseh = self.getControl(113).getHeight()
            basew = self.getControl(113).getWidth()

            # set the button that corresponds to the currently playing show
            for i in range(len(self.channelButtons[2])):
                left, top = self.channelButtons[2][i].getPosition()
                width = self.channelButtons[2][i].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                endtime = starttime + (width / (basew / 5400.0))

                if curtime >= starttime and curtime <= endtime:
                    self.focusIndex = i
                    self.setFocus(self.channelButtons[2][i])
                    self.focusTime = int(time.time())
                    self.focusEndTime = endtime
                    break

            # If nothing was highlighted, just select the first button
            if self.focusIndex == -1:
                self.focusIndex = 0
                self.setFocus(self.channelButtons[2][0])
                left, top = self.channelButtons[2][0].getPosition()
                width = self.channelButtons[2][0].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                endtime = starttime + (width / (basew / 5400.0))
                self.focusTime = int(starttime + 30)
                self.focusEndTime = endtime

            self.focusRow = 2
            self.setShowInfo()
        except:
            self.log("Unknown EPG Initialization Exception", xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)

            try:
                self.close()
            except:
                self.log("Error closing", xbmc.LOGERROR)

            self.MyOverlayWindow.sleepTimeValue = 1
            self.MyOverlayWindow.startSleepTimer()
            return

        self.log('onInit return')


    # setup all channel buttons for a given time
    def setChannelButtons(self, starttime, curchannel, singlerow = -1):
        self.log('setChannelButtons ' + str(starttime) + ', ' + str(curchannel))
        xbmcgui.lock()
        self.removeControl(self.currentTimeBar)
        self.centerChannel = self.MyOverlayWindow.fixChannel(curchannel)
        # This is done twice to guarantee we go back 2 channels.  If the previous 2 channels
        # aren't valid, then doing a fix on curchannel - 2 may result in going back only
        # a single valid channel.
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        starttime = self.roundToHalfHour(int(starttime))
        self.setTimeLabels(starttime)
        self.shownTime = starttime
        basex, basey = self.getControl(111).getPosition()
        basew = self.getControl(111).getWidth()
        tmpx, tmpy =  self.getControl(110 + self.rowCount).getPosition()
        timex, timey = self.getControl(120).getPosition()
        timew = self.getControl(120).getWidth()
        timeh = self.getControl(120).getHeight()

        for i in range(self.rowCount):
            if singlerow == -1 or singlerow == i:
                self.setButtons(starttime, curchannel, i)

            self.getControl(301 + i).setLabel(self.MyOverlayWindow.channels[curchannel - 1].name)

            try:
                self.getControl(311 + i).setLabel(str(curchannel))
            except:
                pass

            try:
                self.getControl(321 + i).setImage(self.channelLogos + self.MyOverlayWindow.channels[curchannel - 1].name + ".png")
            except:
                pass

            curchannel = self.MyOverlayWindow.fixChannel(curchannel + 1)

        if time.time() >= starttime and time.time() < starttime + 5400:
            dif = int((starttime + 5400 - time.time()))
            self.currentTimeBar.setPosition(int((basex + basew - 2) - (dif * (basew / 5400.0))), timey)
        else:
            if time.time() < starttime:
                self.currentTimeBar.setPosition(basex + 2, timey)
            else:
                 self.currentTimeBar.setPosition(basex + basew - 2 - timew, timey)

        self.addControl(self.currentTimeBar)
        xbmcgui.unlock()
        self.log('setChannelButtons return')


    # round the given time down to the nearest half hour
    def roundToHalfHour(self, thetime):
        n = datetime.datetime.fromtimestamp(thetime)
        delta = datetime.timedelta(minutes=30)

        if n.minute > 29:
            n = n.replace(minute=30, second=0, microsecond=0)
        else:
            n = n.replace(minute=0, second=0, microsecond=0)

        return time.mktime(n.timetuple())


    # create the buttons for the specified channel in the given row
    def setButtons(self, starttime, curchannel, row):
        self.log('setButtons ' + str(starttime) + ", " + str(curchannel) + ", " + str(row))

        try:
            curchannel = self.MyOverlayWindow.fixChannel(curchannel)
            basex, basey = self.getControl(111 + row).getPosition()
            baseh = self.getControl(111 + row).getHeight()
            basew = self.getControl(111 + row).getWidth()

            if xbmc.Player().isPlaying() == False:
                self.log('No video is playing, not adding buttons')
                self.closeEPG()
                return False

            # go through all of the buttons and remove them
            for button in self.channelButtons[row]:
                self.removeControl(button)

            self.log("deleted buttons")
            del self.channelButtons[row][:]

            # if the channel is paused, then only 1 button needed
            if self.MyOverlayWindow.channels[curchannel - 1].isPaused:
                self.log("adding 1 button")
                self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.MyOverlayWindow.channels[curchannel - 1].getCurrentTitle() + " (paused)", focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, textColor=self.textcolor, focusedColor=self.focusedcolor))
                self.addControl(self.channelButtons[row][0])
            else:
                # Find the show that was running at the given time
                # Use the current time and show offset to calculate it
                # At timedif time, channelShowPosition was playing at channelTimes
                # The only way this isn't true is if the current channel is curchannel since
                # it could have been fast forwarded or rewinded (rewound)?
                if curchannel == self.MyOverlayWindow.currentChannel:
                    playlistpos = int(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition())
                    videotime = xbmc.Player().getTime()
                    reftime = time.time()
                else:
                    playlistpos = self.MyOverlayWindow.channels[curchannel - 1].playlistPosition
                    videotime = self.MyOverlayWindow.channels[curchannel - 1].showTimeOffset
                    reftime = self.MyOverlayWindow.channels[curchannel - 1].lastAccessTime

                # normalize reftime to the beginning of the video
                reftime -= videotime
                self.log("while reftime: current is " + str(reftime))

                while reftime > starttime:
                    playlistpos -= 1
                    # No need to check bounds on the playlistpos, the duration function makes sure it is correct
                    reftime -= self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)

                self.log("while reftime again")

                while reftime + self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < starttime:
                    reftime += self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                    playlistpos += 1

                # create a button for each show that runs in the next hour and a half
                endtime = starttime + 5400
                totaltime = 0
                self.log("while reftime part 3")
                totalloops = 0

                while reftime < endtime and totalloops < 1000:
                    xpos = int(basex + (totaltime * (basew / 5400.0)))
                    tmpdur = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                    shouldskip = False

                    # this should only happen the first time through this loop
                    # it shows the small portion of the show before the current one
                    if reftime < starttime:
                        tmpdur -= starttime - reftime
                        reftime = starttime

                        if tmpdur < 60 * 3:
                            shouldskip = True

                    # Don't show very short videos
                    if self.MyOverlayWindow.hideShortItems and shouldskip == False:
                        if self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < self.MyOverlayWindow.shortItemLength:
                            shouldskip = True
                            tmpdur = 0
                        else:
                            nextlen = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos + 1)
                            prevlen = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos - 1)

                            if nextlen < 60:
                                tmpdur += nextlen / 2

                            if prevlen < 60:
                                tmpdur += prevlen / 2

                    width = int((basew / 5400.0) * tmpdur)

                    if width < 30 and shouldskip == False:
                        width = 30
                        tmpdur = int(30.0 / (basew / 5400.0))

                    if width + xpos > basex + basew:
                        width = basex + basew - xpos

                    if shouldskip == False and width >= 30:
                        self.channelButtons[row].append(xbmcgui.ControlButton(xpos, basey, width, baseh, self.MyOverlayWindow.channels[curchannel - 1].getItemTitle(playlistpos), focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, textColor=self.textcolor, focusedColor=self.focusedcolor))
                        self.addControl(self.channelButtons[row][-1])

                    totaltime += tmpdur
                    reftime += tmpdur
                    playlistpos += 1
                    totalloops += 1
                    
                if totalloops >= 1000:
                    self.log("Broken big loop, too many loops, reftime is " + str(reftime) + ", endtime is " + str(endtime))
        except:
            self.log("Exception in setButtons", xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)

        self.log('setButtons return')
        return True


    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        action = act.getId()

        try:
            if action in ACTION_PREVIOUS_MENU:
                self.closeEPG()
            elif action == ACTION_MOVE_DOWN:
                self.GoDown()
            elif action == ACTION_MOVE_UP:
                self.GoUp()
            elif action == ACTION_MOVE_LEFT:
                self.GoLeft()
            elif action == ACTION_MOVE_RIGHT:
                self.GoRight()
            elif action == ACTION_STOP:
                self.closeEPG()
            elif action == ACTION_SELECT_ITEM:
                lastaction = time.time() - self.lastActionTime

                if lastaction >= 2:
                    self.selectShow()
                    self.closeEPG()
                    self.lastActionTime = time.time()
        except:
            self.log("Unknown EPG Exception", xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)

            try:
                self.close()
            except:
                self.log("Error closing", xbmc.LOGERROR)

            self.MyOverlayWindow.sleepTimeValue = 1
            self.MyOverlayWindow.startSleepTimer()
            return

        self.actionSemaphore.release()
        self.log('onAction return')


    def closeEPG(self):
        self.log('closeEPG')

        try:
            self.removeControl(self.currentTimeBar)
            self.MyOverlayWindow.startSleepTimer()
        except:
            pass

        self.close()


    def onControl(self, control):
        self.log('onControl')


    # Run when a show is selected, so close the epg and run the show
    def onClick(self, controlid):
        self.log('onClick')

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime

        if lastaction >= 2:
            try:
                selectedbutton = self.getControl(controlid)
            except:
                self.actionSemaphore.release()
                self.log('onClick unknown controlid ' + str(controlid))
                return

            for i in range(self.rowCount):
                for x in range(len(self.channelButtons[i])):
                    if selectedbutton == self.channelButtons[i][x]:
                        self.focusRow = i
                        self.focusIndex = x
                        self.selectShow()
                        self.closeEPG()
                        self.lastActionTime = time.time()
                        self.actionSemaphore.release()
                        self.log('onClick found button return')
                        return

            self.lastActionTime = time.time()
            self.closeEPG()

        self.actionSemaphore.release()
        self.log('onClick return')


    def GoDown(self):
        self.log('goDown')

        # change controls to display the proper junks
        if self.focusRow == self.rowCount - 1:
#            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel + 1))
            self.moveButtonsUp()
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel + 1), self.rowCount - 1)
            self.focusRow = self.rowCount - 2

        self.setProperButton(self.focusRow + 1)
        self.log('goDown return')


    def GoUp(self):
        self.log('goUp')

        # same as godown
        # change controls to display the proper junks
        if self.focusRow == 0:
#            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel - 1, False))
            self.moveButtonsDown()
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel - 1, False), 0)
            self.focusRow = 1

        self.setProperButton(self.focusRow - 1)
        self.log('goUp return')


    def GoLeft(self):
        self.log('goLeft')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        basew = self.getControl(111 + self.focusRow).getWidth()

        # change controls to display the proper junks
        if self.focusIndex == 0:
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            self.setChannelButtons(self.shownTime - 1800, self.centerChannel)
            curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)

            if (curbutidx - 1) >= 0:
                self.focusIndex = curbutidx - 1
            else:
                self.focusIndex = 0
        else:
            self.focusIndex -= 1

        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex
        starttime = self.shownTime + (left / (basew / 5400.0))
        endtime = starttime + (width / (basew / 5400.0))

        self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
        self.setShowInfo()
        self.focusEndTime = endtime
        self.focusTime = starttime + 30
        self.log('goLeft return')


    def GoRight(self):
        self.log('goRight')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        basew = self.getControl(111 + self.focusRow).getWidth()

        # change controls to display the proper junks
        if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            self.setChannelButtons(self.shownTime + 1800, self.centerChannel)
            curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)

            if (curbutidx + 1) < len(self.channelButtons[self.focusRow]):
                self.focusIndex = curbutidx + 1
            else:
                self.focusIndex = len(self.channelButtons[self.focusRow]) - 1
        else:
            self.focusIndex += 1

        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex
        starttime = self.shownTime + (left / (basew / 5400.0))
        endtime = starttime + (width / (basew / 5400.0))

        self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
        self.setShowInfo()
        self.focusEndTime = endtime
        self.focusTime = starttime + 30
        self.log('goRight return')


    def moveButtonsUp(self):
        self.log('moveButtonsUp')
        xbmcgui.lock()

        for button in self.channelButtons[0]:
            self.removeControl(button)

        del self.channelButtons[0][:]

        for i in range(self.rowCount - 1):
            basex, basey = self.getControl(111 + i).getPosition()

            for button in self.channelButtons[i + 1]:
                x, y = button.getPosition()
                button.setPosition(x, basey)

            self.channelButtons[i] = self.channelButtons[i + 1][:]
            del self.channelButtons[i + 1][:]

        xbmcgui.unlock()


    def moveButtonsDown(self):
        self.log('moveButtonsDown')
        xbmcgui.lock()

        for button in self.channelButtons[self.rowCount - 1]:
            self.removeControl(button)

        del self.channelButtons[self.rowCount - 1][:]

        for i in range(self.rowCount - 1):
            basex, basey = self.getControl(111 + (self.rowCount - 1 - i)).getPosition()

            for button in self.channelButtons[self.rowCount - i - 2]:
                x, y = button.getPosition()
                button.setPosition(x, basey)

            self.channelButtons[self.rowCount - 1 - i] = self.channelButtons[self.rowCount - 2 - i][:]
            del self.channelButtons[self.rowCount - 2 - i][:]

        xbmcgui.unlock()


    def findButtonAtTime(self, row, selectedtime):
        self.log('findButtonAtTime ' + str(row))
        basex, basey = self.getControl(111 + row).getPosition()
        baseh = self.getControl(111 + row).getHeight()
        basew = self.getControl(111 + row).getWidth()

        for i in range(len(self.channelButtons[row])):
            left, top = self.channelButtons[row][i].getPosition()
            width = self.channelButtons[row][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if selectedtime >= starttime and selectedtime <= endtime:
                return i

        return -1


    # based on the current focus row and index, find the appropriate button in
    # the new row to set focus to
    def setProperButton(self, newrow, resetfocustime = False):
        self.log('setProperButton ' + str(newrow))
        self.focusRow = newrow
        basex, basey = self.getControl(111 + newrow).getPosition()
        baseh = self.getControl(111 + newrow).getHeight()
        basew = self.getControl(111 + newrow).getWidth()

        for i in range(len(self.channelButtons[newrow])):
            left, top = self.channelButtons[newrow][i].getPosition()
            width = self.channelButtons[newrow][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if self.focusTime >= starttime and self.focusTime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
                self.setShowInfo()
                self.focusEndTime = endtime

                if resetfocustime:
                    self.focusTime = starttime + 30

                self.log('setProperButton found button return')
                return

        self.focusIndex = 0
        self.setFocus(self.channelButtons[newrow][0])
        left, top = self.channelButtons[newrow][0].getPosition()
        width = self.channelButtons[newrow][0].getWidth()
        left = left - basex
        starttime = self.shownTime + (left / (basew / 5400.0))
        endtime = starttime + (width / (basew / 5400.0))
        self.focusEndTime = endtime

        if resetfocustime:
            self.focusTime = starttime + 30

        self.setShowInfo()
        self.log('setProperButton return')


    def setShowInfo(self):
        self.log('setShowInfo')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        baseh = self.getControl(111 + self.focusRow).getHeight()
        basew = self.getControl(111 + self.focusRow).getWidth()
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex + (width / 2)
        starttime = self.shownTime + (left / (basew / 5400.0))

        chnoffset = self.focusRow - 2
        newchan = self.centerChannel

        while chnoffset != 0:
            if chnoffset > 0:
                newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                chnoffset -= 1
            else:
                newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                chnoffset += 1

        plpos = self.determinePlaylistPosAtTime(starttime, newchan)

        if plpos == -1:
            self.log('Unable to find the proper playlist to set from EPG')
            return

        self.getControl(500).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemTitle(plpos))
        self.getControl(501).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemEpisodeTitle(plpos))
        self.getControl(502).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemDescription(plpos))
        self.getControl(503).setImage(self.channelLogos + self.MyOverlayWindow.channels[newchan - 1].name + '.png')
        self.log('setShowInfo return')


    # using the currently selected button, play the proper shows
    def selectShow(self):
        self.log('selectShow')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        baseh = self.getControl(111 + self.focusRow).getHeight()
        basew = self.getControl(111 + self.focusRow).getWidth()
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex + (width / 2)
        starttime = self.shownTime + (left / (basew / 5400.0))
        chnoffset = self.focusRow - 2
        newchan = self.centerChannel

        while chnoffset != 0:
            if chnoffset > 0:
                newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                chnoffset -= 1
            else:
                newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                chnoffset += 1

        plpos = self.determinePlaylistPosAtTime(starttime, newchan)

        if plpos == -1:
            self.log('Unable to find the proper playlist to set from EPG', xbmc.LOGERROR)
            return

        timedif = (time.time() - self.MyOverlayWindow.channels[newchan - 1].lastAccessTime)
        pos = self.MyOverlayWindow.channels[newchan - 1].playlistPosition
        showoffset = self.MyOverlayWindow.channels[newchan - 1].showTimeOffset

        # adjust the show and time offsets to properly position inside the playlist
        while showoffset + timedif > self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos):
            timedif -= self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos) - showoffset
            pos = self.MyOverlayWindow.channels[newchan - 1].fixPlaylistIndex(pos + 1)
            showoffset = 0

        if self.MyOverlayWindow.currentChannel == newchan:
            if plpos == xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition():
                self.log('selectShow return current show')
                return

        if pos != plpos:
            self.MyOverlayWindow.channels[newchan - 1].setShowPosition(plpos)
            self.MyOverlayWindow.channels[newchan - 1].setShowTime(0)
            self.MyOverlayWindow.channels[newchan - 1].setAccessTime(time.time())

        self.MyOverlayWindow.newChannel = newchan
        self.log('selectShow return')


    def determinePlaylistPosAtTime(self, starttime, channel):
        self.log('determinePlaylistPosAtTime ' + str(starttime) + ', ' + str(channel))
        channel = self.MyOverlayWindow.fixChannel(channel)

        # if the channel is paused, then it's just the current item
        if self.MyOverlayWindow.channels[channel - 1].isPaused:
            self.log('determinePlaylistPosAtTime paused return')
            return self.MyOverlayWindow.channels[channel - 1].playlistPosition
        else:
            # Find the show that was running at the given time
            # Use the current time and show offset to calculate it
            # At timedif time, channelShowPosition was playing at channelTimes
            # The only way this isn't true is if the current channel is curchannel since
            # it could have been fast forwarded or rewinded (rewound)?
            if channel == self.MyOverlayWindow.currentChannel:
                playlistpos = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                videotime = xbmc.Player().getTime()
                reftime = time.time()
            else:
                playlistpos = self.MyOverlayWindow.channels[channel - 1].playlistPosition
                videotime = self.MyOverlayWindow.channels[channel - 1].showTimeOffset
                reftime = self.MyOverlayWindow.channels[channel - 1].lastAccessTime

            # normalize reftime to the beginning of the video
            reftime -= videotime

            while reftime > starttime:
                playlistpos -= 1
                reftime -= self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)

            while reftime + self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos) < starttime:
                reftime += self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)
                playlistpos += 1

            self.log('determinePlaylistPosAtTime return' + str(self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)))
            return self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)

########NEW FILE########
__FILENAME__ = FileAccess
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import subprocess, os, shutil
import time, threading
import random, os
import Globals

VFS_AVAILABLE = False

try:
    import xbmcvfs
    VFS_AVAILABLE = True
except:
    pass


FILE_LOCK_MAX_FILE_TIMEOUT = 13
FILE_LOCK_NAME = "FileLock.dat"



class FileAccess:
    @staticmethod
    def log(msg, level = xbmc.LOGDEBUG):
        Globals.log('FileAccess: ' + msg, level)


    @staticmethod
    def open(filename, mode):
        fle = 0
        filename = xbmc.makeLegalFilename(filename)

        if os.path.exists(filename) == False:
            if filename[0:6].lower() == 'smb://':
                fle = FileAccess.openSMB(filename, mode)

                if fle != 0:
                    return fle

        # Even if we can't find the file, try to open it anyway
        try:
            fle = open(filename, mode)
        except:
            fle = 0

        if fle == 0:
            raise IOError()

        return fle


    @staticmethod
    def copy(orgfilename, newfilename):
        orgfilename = xbmc.makeLegalFilename(orgfilename)
        newfilename = xbmc.makeLegalFilename(newfilename)

        if VFS_AVAILABLE == True:
            xbmcvfs.copy(orgfilename, newfilename)
        else:
            try:
                shutil.copy(orgfilename, newfilename)
            except:
                return False

        return True


    @staticmethod
    def exists(filename):
        if os.path.exists(filename):
            return True

        if filename[0:6].lower() == 'smb://':
            return FileAccess.existsSMB(filename)

        return False


    @staticmethod
    def openSMB(filename, mode):
        fle = 0

        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]

            try:
                fle = open(filename, mode)
            except:
                fle = 0

        return fle


    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
            return FileAccess.exists(filename)

        return False


    @staticmethod
    def rename(path, newpath):
        FileAccess.log("rename " + path + " to " + newpath)

        if VFS_AVAILABLE == True:
            FileAccess.log("Using VFS")

            try:
                xbmcvfs.rename(path, newpath)
                return True
            except:
                pass

        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                FileAccess.log("Modifying name")
                if path[0:6].lower() == 'smb://':
                    path = '\\\\' + path[6:]

                if newpath[0:6].lower() == 'smb://':
                    newpath = '\\\\' + newpath[6:]

        try:
            os.rename(path, newpath)
            FileAccess.log("os.rename")
            return True
        except:
            pass

        try:
            shutil.move(path, newpath)
            FileAccess.log("shutil.move")
            return True
        except:
            pass

        FileAccess.log("OSError")
        raise OSError()


    @staticmethod
    def makedirs(directory):
        try:
            os.makedirs(directory)
        except:
            FileAccess._makedirs(directory)


    @staticmethod
    def _makedirs(path):
        if VFS_AVAILABLE == True:
            if len(path) == 0:
                return False

            if(xbmcvfs.exists(path)):
                return True

            success = xbmcvfs.mkdir(path)

            if success == False:
                if path == os.path.dirname(path):
                    return False

                if FileAccess._makedirs(os.path.dirname(path)):
                    return xbmcvfs.mkdir(path)

            return xbmcvfs.exists(path)

        return False



class FileLock:
    def __init__(self):
        random.seed()
        self.lockFileName = Globals.CHANNELS_LOC + FILE_LOCK_NAME
        self.lockedList = []
        self.refreshLocksTimer = threading.Timer(4.0, self.refreshLocks)
        self.refreshLocksTimer.name = "RefreshLocks"
        self.refreshLocksTimer.start()
        self.isExiting = False
        self.grabSemaphore = threading.BoundedSemaphore()
        self.listSemaphore = threading.BoundedSemaphore()
        self.log("FileLock instance")


    def close(self):
        self.log("close")
        self.isExiting = True

        if self.refreshLocksTimer.isAlive():
            self.refreshLocksTimer.cancel()
            self.refreshLocksTimer.join()

        for item in self.lockedList:
            self.unlockFile(item)


    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('FileLock: ' + msg, level)


    def refreshLocks(self):
        self.log("refreshLocks")

        for item in self.lockedList:
            if self.isExiting:
                self.log("IsExiting")
                return False

            self.lockFile(item, True)

        self.refreshLocksTimer = threading.Timer(4.0, self.refreshLocks)

        if self.isExiting == False:
            self.refreshLocksTimer.name = "RefreshLocks"
            self.refreshLocksTimer.start()
            return True

        return False


    def lockFile(self, filename, block = False):
        self.log("lockFile " + filename)
        curval = -1
        attempts = 0
        fle = 0

        if Globals.CHANNEL_SHARING == False:
            return True

        filename = filename.lower()
        locked = True

        while(locked == True and attempts < FILE_LOCK_MAX_FILE_TIMEOUT):
            locked = False

            if curval > -1:
                self.releaseLockFile()
                self.grabSemaphore.release()
                time.sleep(1)

            self.grabSemaphore.acquire()

            if self.grabLockFile() == False:
                self.grabSemaphore.release()
                return False

            try:
                fle = FileAccess.open(self.lockName, "r")
            except:
                self.log("Unable to open the lock file")
                self.releaseLockFile()
                self.grabSemaphore.release()
                return False

            lines = fle.readlines()
            fle.close()
            val = self.findLockEntry(lines, filename)

            # If the file is locked:
            if val > -1:
                locked = True

                # If we're the ones that have the file locked, allow overriding it
                for item in self.lockedList:
                    if item == filename:
                        locked = False
                        block = False
                        break

                if curval == -1:
                    curval = val
                else:
                    if curval == val:
                        attempts += 1
                    else:
                        if block == False:
                            self.releaseLockFile()
                            self.grabSemaphore.release()
                            self.log("File is locked")
                            return False

                        curval = val
                        attempts = 0

        self.log("File is unlocked")
        self.writeLockEntry(lines, filename)
        self.releaseLockFile()
        existing = False

        for item in self.lockedList:
            if item == filename:
                existing = True
                break

        if existing == False:
            self.lockedList.append(filename)

        self.grabSemaphore.release()
        return True


    def grabLockFile(self):
        self.log("grabLockFile")

        # Wait a maximum of 20 seconds to grab file-lock file.  This long
        # timeout should help prevent issues with an old cache.
        for i in range(40):
            # Cycle file names in case one of them is sitting around in the directory
            self.lockName = Globals.CHANNELS_LOC + str(random.randint(1, 60000)) + ".lock"

            try:
                FileAccess.rename(self.lockFileName, self.lockName)
                fle = FileAccess.open(self.lockName, 'r')
                fle.close()
                return True
            except:
                time.sleep(0.5)

        self.log("Creating lock file")

        # If we couldn't grab it, it is gone.  Create it.
        try:
            fle = FileAccess.open(self.lockName, "w")
            fle.close()
        except:
            self.log("Unable to create the lock file")
            return False

        return True


    def releaseLockFile(self):
        self.log("releaseLockFile")

        # Move the file back to the original lock file name
        try:
            FileAccess.rename(self.lockName, self.lockFileName)
        except:
            self.log("Unable to rename the file back to the original name")
            return False

        return True


    def writeLockEntry(self, lines, filename, addentry = True):
        self.log("writeLockEntry")
        # Make sure the entry doesn't exist.  This should only be the case
        # when the attempts count times out
        self.removeLockEntry(lines, filename)

        if addentry:
            lines.append(str(random.randint(1, 60000)) + "," + filename + "\n")

        try:
            fle = FileAccess.open(self.lockName, 'w')
        except:
            self.log("Unable to open the lock file for writing")
            return False

        flewrite = ''

        for line in lines:
            flewrite += line

        fle.write(flewrite)
        fle.close()


    def findLockEntry(self, lines, filename):
        self.log("findLockEntry")

        # Read the file
        for line in lines:
            # Format is 'random value,filename'
            index = line.find(",")
            flenme = ''
            setval = -1

            # Valid line, get the value and filename
            if index > -1:
                try:
                    setval = int(line[:index])
                    flenme = line[index + 1:].strip()
                except:
                    setval = -1
                    flenme = ''

            # The lock already exists
            if flenme == filename:
                self.log("entry exists, val is " + str(setval))
                return setval

        return -1


    def removeLockEntry(self, lines, filename):
        self.log("removeLockEntry")
        realindex = 0

        for i in range(len(lines)):
            index = lines[realindex].find(filename)

            if index > -1:
                del lines[realindex]
                realindex -= 1

            realindex += 1


    def unlockFile(self, filename):
        self.log("unlockFile " + filename)
        filename = filename.lower()
        found = False
        realindex = 0

        if Globals.CHANNEL_SHARING == False:
            return True

        # First make sure we actually own the lock
        # Remove it from the list if we do
        self.listSemaphore.acquire()

        for i in range(len(self.lockedList)):
            if self.lockedList[realindex] == filename:
                del self.lockedList[realindex]
                found = True
                realindex -= 1

            realindex += 1

        self.listSemaphore.release()

        if found == False:
            self.log("Lock not found")
            return False

        self.grabSemaphore.acquire()

        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return False

        try:
            fle = FileAccess.open(self.lockName, "r")
        except:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return False

        lines = fle.readlines()
        fle.close()
        self.writeLockEntry(lines, filename, False)
        self.releaseLockFile()
        self.grabSemaphore.release()
        return True


    def isFileLocked(self, filename, block = False):
        self.log("isFileLocked " + filename)
        filename = filename.lower()

        if Globals.CHANNEL_SHARING == False:
            return False

        self.grabSemaphore.acquire()

        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return True

        try:
            fle = FileAccess.open(self.lockName, "r")
        except:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return True

        lines = fle.readlines()
        fle.close()
        retval = False

        if self.findLockEntry(lines, filename) > -1:
            retval = True

        self.releaseLockFile()
        self.grabSemaphore.release()
        return retval

########NEW FILE########
__FILENAME__ = Globals
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xbmcaddon, xbmc
import Settings


from FileAccess import FileLock



def log(msg, level = xbmc.LOGDEBUG):
    try:
        xbmc.log(ADDON_ID + '-' + msg, level)
    except:
        pass


ADDON_ID = 'script.pseudotv'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_INFO = REAL_SETTINGS.getAddonInfo('path')

VERSION = "2.1.0"

TIMEOUT = 15 * 1000
TOTAL_FILL_CHANNELS = 20
PREP_CHANNEL_TIME = 60 * 60 * 24 * 5
ALLOW_CHANNEL_HISTORY_TIME = 60 * 60 * 24 * 1
NOTIFICATION_CHECK_TIME = 5
NOTIFICATION_TIME_BEFORE_END = 90
NOTIFICATION_DISPLAY_TIME = 8

MODE_RESUME = 1
MODE_ALWAYSPAUSE = 2
MODE_ORDERAIRDATE = 4
MODE_RANDOM = 8
MODE_REALTIME = 16
MODE_SERIAL = MODE_RESUME | MODE_ALWAYSPAUSE | MODE_ORDERAIRDATE
MODE_STARTMODES = MODE_RANDOM | MODE_REALTIME | MODE_RESUME

SETTINGS_LOC = ''
CHANNEL_SHARING = False

if REAL_SETTINGS.getSetting('ChannelSharing') == "true":
    CHANNEL_SHARING = True
    SETTINGS_LOC = REAL_SETTINGS.getSetting('SettingsFolder')
    log("Channel sharing at " + str(SETTINGS_LOC));

IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'images')) + '/'
PRESETS_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'presets')) + '/'

if len(SETTINGS_LOC) == 0:
    SETTINGS_LOC = 'special://profile/addon_data/' + ADDON_ID

CHANNELS_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache')) + '/'
GEN_CHAN_LOC = os.path.join(CHANNELS_LOC, 'generated') + '/'
MADE_CHAN_LOC = os.path.join(CHANNELS_LOC, 'stored') + '/'

SHORT_CLIP_ENUM = [15,30,60,90,120,180,240,300,360]

GlobalFileLock = FileLock()
ADDON_SETTINGS = Settings.Settings()

USING_EDEN = True

try:
    import xbmcvfs
    log("Globals - Eden")
except:
    USING_EDEN = False
    log("Globals - Dharma")

TIME_BAR = 'pstvTimeBar.png'
BUTTON_FOCUS = 'pstvButtonFocus.png'
BUTTON_NO_FOCUS = 'pstvButtonNoFocus.png'

RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_LIST = 4
RULES_ACTION_BEFORE_CLEAR = 8
RULES_ACTION_BEFORE_TIME = 16
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64
RULES_ACTION_OVERLAY_SET_CHANNEL = 128
RULES_ACTION_OVERLAY_SET_CHANNEL_END = 256

# Maximum is 10 for this
RULES_PER_PAGE = 7

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGEUP = 5
ACTION_PAGEDOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_STOP = 13
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15
ACTION_STEP_FOWARD = 17
ACTION_STEP_BACK = 18
ACTION_BIG_STEP_FORWARD = 19
ACTION_BIG_STEP_BACK = 20
ACTION_OSD = 122
ACTION_NUMBER_0 = 58
ACTION_NUMBER_1 = 59
ACTION_NUMBER_2 = 60
ACTION_NUMBER_3 = 61
ACTION_NUMBER_4 = 62
ACTION_NUMBER_5 = 63
ACTION_NUMBER_6 = 64
ACTION_NUMBER_7 = 65
ACTION_NUMBER_8 = 66
ACTION_NUMBER_9 = 67
ACTION_PLAYER_FORWARD = 73
ACTION_PLAYER_REWIND = 74
ACTION_PLAYER_PLAY = 75
ACTION_PLAYER_PLAYPAUSE = 76
#ACTION_MENU = 117
ACTION_MENU = 7
ACTION_INVALID = 999

########NEW FILE########
__FILENAME__ = Migrate
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xbmcaddon, xbmc, xbmcgui
import Settings
import Globals
import ChannelList



class Migrate:
    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('Migrate: ' + msg, level)


    def migrate(self):
        self.log("migration")
        curver = "0.0.0"

        try:
            curver = Globals.ADDON_SETTINGS.getSetting("Version")

            if len(curver) == 0:
                curver = "0.0.0"
        except:
            curver = "0.0.0"

        if curver == Globals.VERSION:
            return True

        Globals.ADDON_SETTINGS.setSetting("Version", Globals.VERSION)
        self.log("version is " + curver)

        if curver == "0.0.0":
            if self.initializeChannels():
                return True

        if self.compareVersions(curver, "1.0.2") < 0:
            self.log("Migrating to 1.0.2")

            # Migrate to 1.0.2
            for i in range(200):
                if os.path.exists(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(i + 1) + '.xsp'):
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/video/Channel_" + str(i + 1) + ".xsp")
                elif os.path.exists(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(i + 1) + '.xsp'):
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/mixed/Channel_" + str(i + 1) + ".xsp")

            currentpreset = 0

            for i in range(Globals.TOTAL_FILL_CHANNELS):
                chantype = 9999

                try:
                    chantype = int(Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                except:
                    pass

                if chantype == 9999:
                    self.addPreset(i + 1, currentpreset)
                    currentpreset += 1

        # Migrate serial mode to rules
        if self.compareVersions(curver, "2.0.0") < 0:
            self.log("Migrating to 2.0.0")

            for i in range(999):
                try:
                    if Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type") == '6':
                        if Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_2") == "6":
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rulecount", "2")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rule_1_id", "8")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rule_2_id", "9")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_2", "4")
                except:
                    pass

        return True


    def addPreset(self, channel, presetnum):
        networks = ['ABC', 'AMC', 'Bravo', 'CBS', 'Comedy Central', 'Food Network', 'FOX', 'FX', 'HBO', 'NBC', 'SciFi', 'The WB']
        genres = ['Animation', 'Comedy', 'Documentary', 'Drama', 'Fantasy']
        studio = ['Brandywine Productions Ltd.', 'Fox 2000 Pictures', 'GK Films', 'Legendary Pictures', 'Universal Pictures']

        if presetnum < len(networks):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", networks[presetnum])
        elif presetnum - len(networks) < len(genres):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "5")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", genres[presetnum - len(networks)])
        elif presetnum - len(networks) - len(genres) < len(studio):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "2")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", studio[presetnum - len(networks) - len(genres)])


    def compareVersions(self, version1, version2):
        retval = 0
        ver1 = version1.split('.')
        ver2 = version2.split('.')

        for i in range(min(len(ver1), len(ver2))):
            try:
                if int(ver1[i]) < int(ver2[i]):
                    retval = -1
                    break

                if int(ver1[i]) > int(ver2[i]):
                    retval = 1
                    break
            except:
                try:
                    v = int(ver1[i])
                    retval = 1
                except:
                    retval = -1

                break

        if retval == 0:
            if len(ver1) > len(ver2):
                retval = 1
            elif len(ver2) > len(ver1):
                retval = -1

        return retval


    def initializeChannels(self):
        updatedlg = xbmcgui.DialogProgress()
        updatedlg.create("PseudoTV", "Initializing")
        updatedlg.update(1, "Initializing", "Initial Channel Setup")
        chanlist = ChannelList.ChannelList()
        chanlist.background = True
        chanlist.fillTVInfo(True)
        updatedlg.update(30)
        chanlist.fillMovieInfo(True)
        updatedlg.update(60)
        # Now create TV networks, followed by mixed genres, followed by TV genres, and finally movie genres
        currentchan = 1
        mixedlist = []

        for item in chanlist.showGenreList:
            curitem = item[0].lower()

            for a in chanlist.movieGenreList:
                if curitem == a[0].lower():
                    mixedlist.append([item[0], item[1], a[1]])
                    break

        mixedlist.sort(key=lambda x: x[1] + x[2], reverse=True)
        currentchan = self.initialAddChannels(chanlist.networkList, 1, currentchan)
        updatedlg.update(70)

        # Mixed genres
        if len(mixedlist) > 0:
            added = 0.0

            for item in mixedlist:
                if item[1] > 2 and item[2] > 1:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_type", "5")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_1", item[0])
                    added += 1.0
                    currentchan += 1
                    itemlow = item[0].lower()

                    # Remove that genre from the shows genre list
                    for i in range(len(chanlist.showGenreList)):
                        if itemlow == chanlist.showGenreList[i][0].lower():
                            chanlist.showGenreList.pop(i)
                            break

                    # Remove that genre from the movie genre list
                    for i in range(len(chanlist.movieGenreList)):
                        if itemlow == chanlist.movieGenreList[i][0].lower():
                            chanlist.movieGenreList.pop(i)
                            break

                    if added > 10:
                        break

                    updatedlg.update(int(70 + 10.0 / added))

        updatedlg.update(80)
        currentchan = self.initialAddChannels(chanlist.showGenreList, 3, currentchan)
        updatedlg.update(90)
        currentchan = self.initialAddChannels(chanlist.movieGenreList, 4, currentchan)
        updatedlg.close()

        if currentchan > 1:
            return True

        return False


    def initialAddChannels(self, thelist, chantype, currentchan):
        if len(thelist) > 0:
            counted = 0
            lastitem = 0
            curchancount = 1
            lowerlimit = 1
            lowlimitcnt = 0

            for item in thelist:
                if item[1] > lowerlimit:
                    if item[1] != lastitem:
                        if curchancount + counted <= 10 or counted == 0:
                            counted += curchancount
                            curchancount = 1
                            lastitem = item[1]
                        else:
                            break
                    else:
                        curchancount += 1

                    lowlimitcnt += 1

                    if lowlimitcnt == 3:
                        lowlimitcnt = 0
                        lowerlimit += 1
                else:
                    break

            if counted > 0:
                for item in thelist:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_type", str(chantype))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_1", item[0])
                    counted -= 1
                    currentchan += 1

                    if counted == 0:
                        break

        return currentchan

########NEW FILE########
__FILENAME__ = Overlay
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random, traceback

from xml.dom.minidom import parse, parseString

from Playlist import Playlist
from Globals import *
from Channel import Channel
from EPGWindow import EPGWindow
from ChannelList import ChannelList
from ChannelListThread import ChannelListThread
from FileAccess import FileLock, FileAccess
from Migrate import Migrate



class MyPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.PLAYER_CORE_AUTO)
        self.stopped = False
        self.ignoreNextStop = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Player: ' + msg, level)


    def onPlayBackStopped(self):
        if self.stopped == False:
            self.log('Playback stopped')

            if self.ignoreNextStop == False:
                if self.overlay.sleepTimeValue == 0:
                    self.overlay.sleepTimer = threading.Timer(1, self.overlay.sleepAction)

                self.overlay.background.setVisible(True)
                self.overlay.sleepTimeValue = 1
                self.overlay.startSleepTimer()
                self.stopped = True
            else:
                self.ignoreNextStop = False



# overlay window to catch events and change channels
class TVOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__')
        # initialize all variables
        self.channels = []
        self.Player = MyPlayer()
        self.Player.overlay = self
        self.inputChannel = -1
        self.channelLabel = []
        self.lastActionTime = 0
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self
        self.setCoordinateResolution(1)
        self.timeStarted = 0
        self.infoOnChange = True
        self.infoOffset = 0
        self.invalidatedChannelCount = 0
        self.showingInfo = False
        self.showChannelBug = False
        self.notificationLastChannel = 0
        self.notificationLastShow = 0
        self.notificationShowedNotif = False
        self.isExiting = False
        self.maxChannels = 0
        self.notPlayingCount = 0
        self.ignoreInfoAction = False
        self.shortItemLength = 60
        self.runningActionChannel = 0

        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse='0xAA00ff00'))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)

        self.doModal()
        self.log('__init__ return')


    def resetChannelTimes(self):
        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(self.timeStarted - self.channels[i].totalTimePlayed)


    def onFocus(self, controlId):
        pass


    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')

        if FileAccess.exists(GEN_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(GEN_CHAN_LOC)
            except:
                self.Error('Unable to create the cache directory')
                return

        if FileAccess.exists(MADE_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(MADE_CHAN_LOC)
            except:
                self.Error('Unable to create the storage directory')
                return

        self.background = self.getControl(101)
        self.getControl(102).setVisible(False)
        self.background.setVisible(True)
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV", "Initializing")
        updateDialog.update(5, "Initializing", "Grabbing Lock File")
        ADDON_SETTINGS.loadSettings()
        updateDialog.update(70, "Initializing", "Checking Other Instances")
        self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        updateDialog.update(95, "Initializing", "Migrating")

        if self.isMaster:
            migratemaster = Migrate()
            migratemaster.migrate()

        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.playerTimer = threading.Timer(2.0, self.playerTimerAction)
        self.playerTimer.name = "PlayerTimer"
        self.infoTimer = threading.Timer(5.0, self.hideInfo)
        self.masterTimer = threading.Timer(5.0, self.becomeMaster)
        self.myEPG = EPGWindow("script.pseudotv.EPG.xml", ADDON_INFO, "default")
        self.myEPG.MyOverlayWindow = self
        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()
        updateDialog.close()
        self.timeStarted = time.time()

        if self.readConfig() == False:
            return

        self.myEPG.channelLogos = self.channelLogos
        self.maxChannels = len(self.channels)

        if self.maxChannels == 0:
            self.Error('Unable to find any channels. Please configure the addon.')
            return

        found = False

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                found = True
                break

        if found == False:
            self.Error("Unable to populate channels. Please verify that you", "have scraped media in your library and that you have", "properly configured channels.")
            return

        if self.sleepTimeValue > 0:
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)

        try:
            if self.forceReset == False:
                self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
            else:
                self.currentChannel = self.fixChannel(1)
        except:
            self.currentChannel = self.fixChannel(1)

        self.resetChannelTimes()
        self.setChannel(self.currentChannel)
        self.background.setVisible(False)
        self.startSleepTimer()
        self.startNotificationTimer()
        self.playerTimer.start()

        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread.name = "ChannelThread"
            self.channelThread.start()

        if self.isMaster == False:
            self.masterTimer.name = "MasterTimer"
            self.masterTimer.start()

        self.actionSemaphore.release()
        self.log('onInit return')


    def becomeMaster(self):
        self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        self.masterTimer = threading.Timer(5.0, self.becomeMaster)

        if self.isMaster == False and self.isExiting == False:
            self.masterTimer.name = "MasterTimer"
            self.masterTimer.start()

            # Perform this after start so that there isn't an issue with evaluation before it is
            # set.
            if self.isExiting:
                self.masterTimer.cancel()
        elif self.isMaster:
            self.log("Became master")


    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        # Sleep setting is in 30 minute incriments...so multiply by 30, and then 60 (min to sec)
        self.sleepTimeValue = int(REAL_SETTINGS.getSetting('AutoOff')) * 1800
        self.log('Auto off is ' + str(self.sleepTimeValue))
        self.infoOnChange = REAL_SETTINGS.getSetting("InfoOnChange") == "true"
        self.log('Show info label on channel change is ' + str(self.infoOnChange))
        self.showChannelBug = REAL_SETTINGS.getSetting("ShowChannelBug") == "true"
        self.log('Show channel bug - ' + str(self.showChannelBug))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.channelResetSetting = REAL_SETTINGS.getSetting('ChannelResetSetting')
        self.log("Channel reset setting - " + str(self.channelResetSetting))
        self.channelLogos = xbmc.translatePath(REAL_SETTINGS.getSetting('ChannelLogoFolder'))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.log("Background updating - " + str(self.backgroundUpdating))
        self.showNextItem = REAL_SETTINGS.getSetting("EnableComingUp") == "true"
        self.log("Show Next Item - " + str(self.showNextItem))
        self.hideShortItems = REAL_SETTINGS.getSetting("HideClips") == "true"
        self.log("Hide Short Items - " + str(self.hideShortItems))
        self.shortItemLength = SHORT_CLIP_ENUM[int(REAL_SETTINGS.getSetting("ClipLength"))]
        self.log("Short item length - " + str(self.shortItemLength))

        if FileAccess.exists(self.channelLogos) == False:
            self.channelLogos = IMAGES_LOC

        self.log('Channel logo folder - ' + self.channelLogos)
        chn = ChannelList()
        chn.myOverlay = self
        self.channels = chn.setupList()

        if self.channels is None:
            self.log('readConfig No channel list returned')
            self.end()
            return False

        self.Player.stop()
        self.log('readConfig return')
        return True


    # handle fatal errors: log it, show the dialog, and exit
    def Error(self, line1, line2 = '', line3 = ''):
        self.log('FATAL ERROR: ' + line1 + " " + line2 + " " + line3, xbmc.LOGFATAL)
        dlg = xbmcgui.Dialog()
        dlg.ok('Error', line1, line2, line3)
        del dlg
        self.end()


    def channelDown(self):
        self.log('channelDown')

        if self.maxChannels == 1:
            return

        self.background.setVisible(True)
        channel = self.fixChannel(self.currentChannel - 1, False)
        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelDown return')


    def channelUp(self):
        self.log('channelUp')

        if self.maxChannels == 1:
            return

        self.background.setVisible(True)
        channel = self.fixChannel(self.currentChannel + 1)
        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelUp return')


    def message(self, data):
        self.log('Dialog message: ' + data)
        dlg = xbmcgui.Dialog()
        dlg.ok('Info', data)
        del dlg


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)


    # set the channel, the proper show offset, and time offset
    def setChannel(self, channel):
        self.log('setChannel ' + str(channel))
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL, channel, self.channels[channel - 1])

        if self.Player.stopped:
            self.log('setChannel player already stopped', xbmc.LOGERROR);
            return

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel invalid channel ' + str(channel), xbmc.LOGERROR)
            return

        if self.channels[channel - 1].isValid == False:
            self.log('setChannel channel not valid ' + str(channel), xbmc.LOGERROR)
            return

        self.lastActionTime = 0
        timedif = 0
        self.getControl(102).setVisible(False)
        self.getControl(103).setImage('')
        self.showingInfo = False

        # first of all, save playing state, time, and playlist offset for
        # the currently playing channel
        if self.Player.isPlaying():
            if channel != self.currentChannel:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))

                # Automatically pause in serial mode
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                    self.channels[self.currentChannel - 1].setPaused(True)

                self.channels[self.currentChannel - 1].setShowTime(self.Player.getTime())
                self.channels[self.currentChannel - 1].setShowPosition(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
                self.channels[self.currentChannel - 1].setAccessTime(time.time())

        self.currentChannel = channel
        # now load the proper channel playlist
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
        self.log("about to load");

        if xbmc.PlayList(xbmc.PLAYLIST_MUSIC).load(self.channels[channel - 1].fileName) == False:
            self.log("Error loading playlist", xbmc.LOGERROR)
            self.InvalidateChannel(channel)
            return

        # Disable auto playlist shuffling if it's on
        if xbmc.getInfoLabel('Playlist.Random').lower() == 'random':
            self.log('Random on.  Disabling.')
            xbmc.PlayList(xbmc.PLAYLIST_MUSIC).unshuffle()

        self.log("repeat all");
        xbmc.executebuiltin("PlayerControl(repeatall)")
        curtime = time.time()
        timedif = (curtime - self.channels[self.currentChannel - 1].lastAccessTime)

        if self.channels[self.currentChannel - 1].isPaused == False:
            # adjust the show and time offsets to properly position inside the playlist
            while self.channels[self.currentChannel - 1].showTimeOffset + timedif > self.channels[self.currentChannel - 1].getCurrentDuration():
                timedif -= self.channels[self.currentChannel - 1].getCurrentDuration() - self.channels[self.currentChannel - 1].showTimeOffset
                self.channels[self.currentChannel - 1].addShowPosition(1)
                self.channels[self.currentChannel - 1].setShowTime(0)

        # First, check to see if the video is a strm
        if self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)[-4:].lower() == 'strm':
            self.log("Ignoring a stop because of a stream")
            self.Player.ignoreNextStop = True

        self.log("about to mute");
        # Mute the channel before changing
        xbmc.executebuiltin("Mute()");
        # set the show offset
        self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)
        self.log("playing selected file");
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)

        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)

            try:
                self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)

                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()

                    if self.waitForVideoPaused() == False:
                        xbmc.executebuiltin("Mute()");
                        return
            except:
                self.log('Exception during seek on paused channel', xbmc.LOGERROR)
        else:
            seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif + int((time.time() - curtime))

            try:
                self.log("Seeking");
                self.Player.seekTime(seektime)
            except:
                self.log("Unable to set proper seek time, trying different value")

                try:
                    seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif
                    self.Player.seekTime(seektime)
                except:
                    self.log('Exception during seek', xbmc.LOGERROR)

        # Unmute
        self.log("Finished, unmuting");
        xbmc.executebuiltin("Mute()");
        self.showChannelLabel(self.currentChannel)
        self.lastActionTime = time.time()
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL_END, channel, self.channels[channel - 1])
        self.log('setChannel return')


    def InvalidateChannel(self, channel):
        self.log("InvalidateChannel" + str(channel))

        if channel < 1 or channel > self.maxChannels:
            self.log("InvalidateChannel invalid channel " + str(channel))
            return

        self.channels[channel - 1].isValid = False
        self.invalidatedChannelCount += 1

        if self.invalidatedChannelCount > 3:
            self.Error("Exceeded 3 invalidated channels. Exiting.")
            return

        remaining = 0

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                remaining += 1

        if remaining == 0:
            self.Error("No channels available. Exiting.")
            return

        self.setChannel(self.fixChannel(channel))


    def waitForVideoPaused(self):
        self.log('waitForVideoPaused')
        sleeptime = 0

        while sleeptime < TIMEOUT:
            xbmc.sleep(100)

            if self.Player.isPlaying():
                if xbmc.getCondVisibility('Player.Paused'):
                    break

            sleeptime += 100
        else:
            self.log('Timeout waiting for pause', xbmc.LOGERROR)
            return False

        self.log('waitForVideoPaused return')
        return True


    def setShowInfo(self):
        self.log('setShowInfo')

        if self.infoOffset > 0:
            self.getControl(502).setLabel('COMING UP:')
        elif self.infoOffset < 0:
            self.getControl(502).setLabel('ALREADY SEEN:')
        elif self.infoOffset == 0:
            self.getControl(502).setLabel('NOW WATCHING:')

        if self.hideShortItems and self.infoOffset != 0:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            curoffset = 0
            modifier = 1

            if self.infoOffset < 0:
                modifier = -1

            while curoffset != abs(self.infoOffset):
                position = self.channels[self.currentChannel - 1].fixPlaylistIndex(position + modifier)

                if self.channels[self.currentChannel - 1].getItemDuration(position) >= self.shortItemLength:
                    curoffset += 1
        else:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset

        self.getControl(503).setLabel(self.channels[self.currentChannel - 1].getItemTitle(position))
        self.getControl(504).setLabel(self.channels[self.currentChannel - 1].getItemEpisodeTitle(position))
        self.getControl(505).setLabel(self.channels[self.currentChannel - 1].getItemDescription(position))
        self.getControl(506).setImage(self.channelLogos + self.channels[self.currentChannel - 1].name + '.png')
        self.log('setShowInfo return')


    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))

        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
            self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)

        tmp = self.inputChannel
        self.hideChannelLabel()
        self.inputChannel = tmp
        curlabel = 0

        if channel > 99:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel // 100) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        if channel > 9:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str((channel % 100) // 10) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel % 10) + '.png')
        self.channelLabel[curlabel].setVisible(True)

        ##ADDED BY SRANSHAFT: USED TO SHOW NEW INFO WINDOW WHEN CHANGING CHANNELS
        if self.inputChannel == -1 and self.infoOnChange == True:
            self.infoOffset = 0
            self.showInfo(5.0)

        if self.showChannelBug == True:
            try:
                self.getControl(103).setImage(self.channelLogos + self.channels[self.currentChannel - 1].name + '.png')
            except:
                pass
        else:
            try:
                self.getControl(103).setImage('')
            except:
                pass
        ##

        if xbmc.getCondVisibility('Player.ShowInfo'):
            xbmc.executehttpapi("SendKey(0xF049)")
            self.ignoreInfoAction = True

        self.channelLabelTimer.name = "ChannelLabel"
        self.channelLabelTimer.start()
        self.startNotificationTimer(10.0)
        self.log('showChannelLabel return')


    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)

        for i in range(3):
            self.channelLabel[i].setVisible(False)

        self.inputChannel = -1
        self.log('hideChannelLabel return')


    def hideInfo(self):
        self.getControl(102).setVisible(False)
        self.infoOffset = 0
        self.showingInfo = False

        if self.infoTimer.isAlive():
            self.infoTimer.cancel()

        self.infoTimer = threading.Timer(5.0, self.hideInfo)


    def showInfo(self, timer):
        if self.hideShortItems:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset

            if self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()) < self.shortItemLength:
                return

        self.getControl(102).setVisible(True)
        self.showingInfo = True
        self.setShowInfo()

        if self.infoTimer.isAlive():
            self.infoTimer.cancel()

        self.infoTimer = threading.Timer(timer, self.hideInfo)
        self.infoTimer.name = "InfoTimer"

        if xbmc.getCondVisibility('Player.ShowInfo'):
            xbmc.executehttpapi("SendKey(0xF049)")
            self.ignoreInfoAction = True

        self.infoTimer.start()


    # return a valid channel in the proper range
    def fixChannel(self, channel, increasing = True):
        while channel < 1 or channel > self.maxChannels:
            if channel < 1: channel = self.maxChannels + channel
            if channel > self.maxChannels: channel -= self.maxChannels

        if increasing:
            direction = 1
        else:
            direction = -1

        if self.channels[channel - 1].isValid == False:
            return self.fixChannel(channel + direction, increasing)

        return channel


    # Handle all input while videos are playing
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))

        if self.Player.stopped:
            return

        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime

        # during certain times we just want to discard all input
        if lastaction < 2:
            self.log('Not allowing actions')
            action = ACTION_INVALID

        self.startSleepTimer()

        if action == ACTION_SELECT_ITEM:
            # If we're manually typing the channel, set it now
            if self.inputChannel > 0:
                if self.inputChannel != self.currentChannel:
                    self.setChannel(self.inputChannel)

                self.inputChannel = -1
            else:
                # Otherwise, show the EPG
                if self.channelThread.isAlive():
                    self.channelThread.pause()

                if self.notificationTimer.isAlive():
                    self.notificationTimer.cancel()
                    self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)

                if self.sleepTimeValue > 0:
                    if self.sleepTimer.isAlive():
                        self.sleepTimer.cancel()
                        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

                self.hideInfo()
                self.newChannel = 0
                self.myEPG.doModal()

                if self.channelThread.isAlive():
                    self.channelThread.unpause()

                self.startNotificationTimer()

                if self.newChannel != 0:
                    self.background.setVisible(True)
                    self.setChannel(self.newChannel)
                    self.background.setVisible(False)
        elif action == ACTION_MOVE_UP or action == ACTION_PAGEUP:
            self.channelUp()
        elif action == ACTION_MOVE_DOWN or action == ACTION_PAGEDOWN:
            self.channelDown()
        elif action == ACTION_MOVE_LEFT:
            if self.showingInfo:
                self.infoOffset -= 1
                self.showInfo(10.0)
            else:
                xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
        elif action == ACTION_MOVE_RIGHT:
            if self.showingInfo:
                self.infoOffset += 1
                self.showInfo(10.0)
            else:
                xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
        elif action in ACTION_PREVIOUS_MENU:
            if self.showingInfo:
                self.hideInfo()
            else:
                dlg = xbmcgui.Dialog()

                if self.sleepTimeValue > 0:
                    if self.sleepTimer.isAlive():
                        self.sleepTimer.cancel()
                        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

                if dlg.yesno("Exit?", "Are you sure you want to exit PseudoTV?"):
                    self.end()
                    return  # Don't release the semaphore
                else:
                    self.startSleepTimer()

                del dlg
        elif action == ACTION_SHOW_INFO:
            if self.ignoreInfoAction:
                self.ignoreInfoAction = False
            else:
                if self.showingInfo:
                    self.hideInfo()

                    if xbmc.getCondVisibility('Player.ShowInfo'):
                        xbmc.executehttpapi("SendKey(0xF049)")
                        self.ignoreInfoAction = True
                else:
                    self.showInfo(10.0)
        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            if self.inputChannel < 0:
                self.inputChannel = action - ACTION_NUMBER_0
            else:
                if self.inputChannel < 100:
                    self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0

            self.showChannelLabel(self.inputChannel)
        elif action == ACTION_OSD:
            xbmc.executebuiltin("ActivateWindow(12901)")

        self.actionSemaphore.release()
        self.log('onAction return')


    # Reset the sleep timer
    def startSleepTimer(self):
        if self.sleepTimeValue == 0:
            return

        # Cancel the timer if it is still running
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        if self.Player.stopped == False:
            self.sleepTimer.name = "SleepTimer"
            self.sleepTimer.start()


    def startNotificationTimer(self, timertime = NOTIFICATION_CHECK_TIME):
        self.log("startNotificationTimer")

        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()

        self.notificationTimer = threading.Timer(timertime, self.notificationAction)

        if self.Player.stopped == False:
            self.notificationTimer.name = "NotificationTimer"
            self.notificationTimer.start()


    # This is called when the sleep timer expires
    def sleepAction(self):
        self.log("sleepAction")
        self.actionSemaphore.acquire()
#        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        # TODO: show some dialog, allow the user to cancel the sleep
        # perhaps modify the sleep time based on the current show
        self.end()


    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))

        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index
                parameter = rule.runAction(action, self, parameter)

            index += 1

        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def notificationAction(self):
        self.log("notificationAction")
        docheck = False

        if self.showNextItem == False:
            return

        if self.Player.isPlaying():
            if self.notificationLastChannel != self.currentChannel:
                docheck = True
            else:
                if self.notificationLastShow != xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition():
                    docheck = True
                else:
                    if self.notificationShowedNotif == False:
                        docheck = True

            if docheck == True:
                self.notificationLastChannel = self.currentChannel
                self.notificationLastShow = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.notificationShowedNotif = False

                if self.hideShortItems:
                    # Don't show any notification if the current show is < 60 seconds
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < self.shortItemLength:
                        self.notificationShowedNotif = True

                timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getTime()

                if self.notificationShowedNotif == False and timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
                    nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(self.notificationLastShow + 1)

                    if self.hideShortItems:
                        # Find the next show that is >= 60 seconds long
                        while nextshow != self.notificationLastShow:
                            if self.channels[self.currentChannel - 1].getItemDuration(nextshow) >= self.shortItemLength:
                                break

                            nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(nextshow + 1)

                    xbmc.executebuiltin("Notification(Coming Up Next, " + self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', '') + ", " + str(NOTIFICATION_DISPLAY_TIME * 1000) + ")")
                    self.notificationShowedNotif = True

        self.startNotificationTimer()


    def playerTimerAction(self):
        self.playerTimer = threading.Timer(2.0, self.playerTimerAction)

        if self.Player.isPlaying():
            self.lastPlayTime = int(self.Player.getTime())
            self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.notPlayingCount = 0
        else:
            self.notPlayingCount += 1
            self.log("Adding to notPlayingCount")

        if self.channels[self.currentChannel - 1].getCurrentFilename()[-4:].lower() != 'strm':
            if self.notPlayingCount >= 3:
                self.end()
                return

        if self.Player.stopped == False:
            self.playerTimer.name = "PlayerTimer"
            self.playerTimer.start()


    # cleanup and end
    def end(self):
        self.log('end')
        # Prevent the player from setting the sleep timer
        self.Player.stopped = True
        self.background.setVisible(True)
        curtime = time.time()
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        self.isExiting = True
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV", "Exiting")
        updateDialog.update(0, "Exiting", "Removing File Locks")
        GlobalFileLock.close()

        if self.playerTimer.isAlive():
            self.playerTimer.cancel()
            self.playerTimer.join()

        if self.Player.isPlaying():
            self.lastPlayTime = self.Player.getTime()
            self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.Player.stop()

        updateDialog.update(1, "Exiting", "Stopping Threads")

        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()
                self.channelLabelTimer.join()
        except:
            pass

        updateDialog.update(2)

        try:
            if self.notificationTimer.isAlive():
                self.notificationTimer.cancel()
                self.notificationTimer.join()
        except:
            pass

        updateDialog.update(3)

        try:
            if self.infoTimer.isAlive():
                self.infoTimer.cancel()
                self.infoTimer.join()
        except:
            pass

        updateDialog.update(4)

        try:
            if self.sleepTimeValue > 0:
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
        except:
            pass

        updateDialog.update(5)

        try:
            if self.masterTimer.isAlive():
                self.masterTimer.cancel()
                self.masterTimer.join()
        except:
            pass

        if self.channelThread.isAlive():
            for i in range(30):
                try:
                    self.channelThread.join(1.0)
                except:
                    pass

                if self.channelThread.isAlive() == False:
                    break

                updateDialog.update(6 + i, "Exiting", "Stopping Threads")

            if self.channelThread.isAlive():
                self.log("Problem joining channel thread", xbmc.LOGERROR)

        if self.timeStarted > 0 and self.isMaster:
            updateDialog.update(35, "Exiting", "Saving Settings")
            validcount = 0

            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    validcount += 1

            if validcount > 0:
                incval = 65.0 / float(validcount)

                for i in range(self.maxChannels):
                    updateDialog.update(35 + int((incval * i)))

                    if self.channels[i].isValid:
                        if self.channels[i].mode & MODE_RESUME == 0:
                            ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(curtime - self.timeStarted + self.channels[i].totalTimePlayed)))
                        else:
                            if i == self.currentChannel - 1:
                                # Determine pltime...the time it at the current playlist position
                                pltime = 0
                                self.log("position for current playlist is " + str(self.lastPlaylistPosition))

                                for pos in range(self.lastPlaylistPosition):
                                    pltime += self.channels[i].getItemDuration(pos)

                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(pltime + self.lastPlayTime))
                            else:
                                tottime = 0

                                for j in range(self.channels[i].playlistPosition):
                                    tottime += self.channels[i].getItemDuration(j)

                                tottime += self.channels[i].showTimeOffset
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(tottime)))

        if self.isMaster:
            try:
                REAL_SETTINGS.setSetting('CurrentChannel', str(self.currentChannel))
            except:
                pass

            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))

        updateDialog.close()
        self.background.setVisible(False)
        self.close()

########NEW FILE########
__FILENAME__ = AVIParser
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, struct

from resources.lib.FileAccess import FileAccess



class AVIChunk:
    def __init__(self):
        self.empty()


    def empty(self):
        self.size = 0
        self.fourcc = ''
        self.datatype = 1
        self.chunk = ''


    def read(self, thefile):
        data = thefile.read(4)

        try:
            self.size = struct.unpack('<i', data)[0]
        except:
            self.size = 0

        # Putting an upper limit on the chunk size, in case the file is corrupt
        if self.size > 0 and self.size < 10000:
            self.chunk = thefile.read(self.size)
        else:
            self.chunk = ''
            self.size = 0



class AVIList:
    def __init__(self):
        self.empty()


    def empty(self):
        self.size = 0
        self.fourcc = ''
        self.datatype = 2


    def read(self, thefile):
        data = thefile.read(4)

        try:
            self.size = struct.unpack('<i', data)[0]
        except:
            self.size = 0

        self.fourcc = thefile.read(4)



class AVIHeader:
    def __init__(self):
        self.empty()


    def empty(self):
        self.dwMicroSecPerFrame = 0
        self.dwMaxBytesPerSec = 0
        self.dwPaddingGranularity = 0
        self.dwFlags = 0
        self.dwTotalFrames = 0
        self.dwInitialFrames = 0
        self.dwStreams = 0
        self.dwSuggestedBufferSize = 0
        self.dwWidth = 0
        self.dwHeight = 0



class AVIStreamHeader:
    def __init__(self):
        self.empty()


    def empty(self):
        self.fccType = ''
        self.fccHandler = ''
        self.dwFlags = 0
        self.wPriority = 0
        self.wLanguage = 0
        self.dwInitialFrame = 0
        self.dwScale = 0
        self.dwRate = 0
        self.dwStart = 0
        self.dwLength = 0
        self.dwSuggestedBuffer = 0
        self.dwQuality = 0
        self.dwSampleSize = 0
        self.rcFrame = ''



class AVIParser:
    def __init__(self):
        self.Header = AVIHeader()
        self.StreamHeader = AVIStreamHeader()


    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('AVIParser: ' + msg, level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb")
        except:
            self.log("Unable to open the file")
            return 0

        dur = self.readHeader()
        self.File.close()
        self.log('Duration: ' + str(dur))
        return dur


    def readHeader(self):
        # AVI Chunk
        data = self.getChunkOrList()

        if data.datatype != 2:
            self.log("Not an avi")
            return 0

        if data.fourcc[0:4] != "AVI ":
            self.log("Not a basic AVI: " + data.fourcc[:2])
            return 0

        # Header List
        data = self.getChunkOrList()

        if data.fourcc != "hdrl":
            self.log("Header not found: " + data.fourcc)
            return 0

        # Header chunk
        data = self.getChunkOrList()

        if data.fourcc != 'avih':
            self.log('Header chunk not found: ' + data.fourcc)
            return 0

        self.parseHeader(data)
        # Stream list
        data = self.getChunkOrList()

        if self.Header.dwStreams > 10:
            self.Header.dwStreams = 10

        for i in range(self.Header.dwStreams):
            if data.datatype != 2:
                self.log("Unable to find streams")
                return 0

            listsize = data.size
            # Stream chunk number 1, the stream header
            data = self.getChunkOrList()

            if data.datatype != 1:
                self.log("Broken stream header")
                return 0

            self.StreamHeader.empty()
            self.parseStreamHeader(data)

            # If this is the video header, determine the duration
            if self.StreamHeader.fccType == 'vids':
                return self.getStreamDuration()

            # If this isn't the video header, skip through the rest of these
            # stream chunks
            try:
                if listsize - data.size - 12 > 0:
                    self.File.seek(listsize - data.size - 12, 1)

                data = self.getChunkOrList()
            except:
                self.log("Unable to seek")

        self.log("Video stream not found")
        return 0


    def getStreamDuration(self):
        try:
            return int(self.StreamHeader.dwLength / (float(self.StreamHeader.dwRate) / float(self.StreamHeader.dwScale)))
        except:
            return 0


    def parseHeader(self, data):
        try:
            header = struct.unpack('<iiiiiiiiiiiiii', data.chunk)
            self.Header.dwMicroSecPerFrame = header[0]
            self.Header.dwMaxBytesPerSec = header[1]
            self.Header.dwPaddingGranularity = header[2]
            self.Header.dwFlags = header[3]
            self.Header.dwTotalFrames = header[4]
            self.Header.dwInitialFrames = header[5]
            self.Header.dwStreams = header[6]
            self.Header.dwSuggestedBufferSize = header[7]
            self.Header.dwWidth = header[8]
            self.Header.dwHeight = header[9]
        except:
            self.Header.empty()
            self.log('Unable to parse the header')


    def parseStreamHeader(self, data):
        try:
            self.StreamHeader.fccType = data.chunk[0:4]
            self.StreamHeader.fccHandler = data.chunk[4:8]
            header = struct.unpack('<ihhiiiiiiiid', data.chunk[8:])
            self.StreamHeader.dwFlags = header[0]
            self.StreamHeader.wPriority = header[1]
            self.StreamHeader.wLanguage = header[2]
            self.StreamHeader.dwInitialFrame = header[3]
            self.StreamHeader.dwScale = header[4]
            self.StreamHeader.dwRate = header[5]
            self.StreamHeader.dwStart = header[6]
            self.StreamHeader.dwLength = header[7]
            self.StreamHeader.dwSuggestedBuffer = header[8]
            self.StreamHeader.dwQuality = header[9]
            self.StreamHeader.dwSampleSize = header[10]
            self.StreamHeader.rcFrame = ''
        except:
            self.StreamHeader.empty()
            self.log("Error reading stream header")


    def getChunkOrList(self):
        data = self.File.read(4)

        if data == "RIFF" or data == "LIST":
            dataclass = AVIList()
        elif len(data) == 0:
            dataclass = AVIChunk()
            dataclass.datatype = 3
        else:
            dataclass = AVIChunk()
            dataclass.fourcc = data

        # Fill in the chunk or list info
        dataclass.read(self.File)
        return dataclass

########NEW FILE########
__FILENAME__ = FLVParser
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, struct

from resources.lib.FileAccess import FileAccess



class FLVTagHeader:
    def __init__(self):
        self.tagtype = 0
        self.datasize = 0
        self.timestamp = 0
        self.timestampext = 0


    def readHeader(self, thefile):
        try:
            data = struct.unpack('B', thefile.read(1))[0]
            self.tagtype = (data & 0x1F)
            self.datasize = struct.unpack('>H', thefile.read(2))[0]
            data = struct.unpack('>B', thefile.read(1))[0]
            self.datasize = (self.datasize << 8) | data
            self.timestamp = struct.unpack('>H', thefile.read(2))[0]
            data = struct.unpack('>B', thefile.read(1))[0]
            self.timestamp = (self.timestamp << 8) | data
            self.timestampext = struct.unpack('>B', thefile.read(1))[0]
        except:
            self.tagtype = 0
            self.datasize = 0
            self.timestamp = 0
            self.timestampext = 0



class FLVParser:
    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('FLVParser: ' + msg, level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb")
        except:
            self.log("Unable to open the file")
            return

        if self.verifyFLV() == False:
            self.log("Not a valid FLV")
            self.File.close()
            return 0

        tagheader = self.findLastVideoTag()

        if tagheader is None:
            self.log("Unable to find a video tag")
            self.File.close()
            return 0

        dur = self.getDurFromTag(tagheader)
        self.File.close()
        self.log("Duration: " + str(dur))
        return dur


    def verifyFLV(self):
        data = self.File.read(3)

        if data != 'FLV':
            return False

        return True



    def findLastVideoTag(self):
        self.File.seek(0, 2)
        curloc = self.File.tell()

        while curloc > 0:
            try:
                self.File.seek(-4, 1)
                data = int(struct.unpack('>I', self.File.read(4))[0])
                self.File.seek(-4 - data, 1)
                tag = FLVTagHeader()
                tag.readHeader(self.File)
                self.File.seek(-8, 1)
                self.log("detected tag type " + str(tag.tagtype))
                curloc = self.File.tell()

                if tag.tagtype == 9:
                    return tag
            except:
                self.log('Exception in findLastVideoTag')
                return None

        return None


    def getDurFromTag(self, tag):
        tottime = tag.timestamp | (tag.timestampext << 24)
        tottime = int(tottime / 1000)
        return tottime

########NEW FILE########
__FILENAME__ = MKVParser
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, struct

from resources.lib.FileAccess import FileAccess



class MKVParser:
    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('MKVParser: ' + msg, level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb")
        except:
            self.log("Unable to open the file")
            return

        size = self.findHeader()

        if size == 0:
            self.log('Unable to find the segment info')
            dur = 0
        else:
            dur = self.parseHeader(size)

        self.log("Duration is " + str(dur))
        return dur


    def parseHeader(self, size):
        duration = 0
        timecode = 0
        fileend = self.File.tell() + size
        datasize = 1
        data = 1

        while self.File.tell() < fileend and datasize > 0 and data > 0:
            data = self.getEBMLId()
            datasize = self.getDataSize()

            if data == 0x2ad7b1:
                timecode = 0

                try:
                    for x in range(datasize):
                        timecode = (timecode << 8) + struct.unpack('B', self.getData(1))[0]
                except:
                    timecode = 0

                if duration != 0 and timecode != 0:
                        break
            elif data == 0x4489:
                try:
                    if datasize == 4:
                        duration = int(struct.unpack('>f', self.getData(datasize))[0])
                    else:
                        duration = int(struct.unpack('>d', self.getData(datasize))[0])
                except:
                    self.log("Error getting duration in header, size is " + str(datasize))
                    duration = 0

                if timecode != 0 and duration != 0:
                    break
            else:
                try:
                    self.File.seek(datasize, 1)
                except:
                    self.log('Error while seeking')
                    return 0

        if duration > 0 and timecode > 0:
            dur = (duration * timecode) / 1000000000
            return dur

        return 0


    def findHeader(self):
        self.log("findHeader")
        filesize = self.getFileSize()
        
        if filesize == 0:
            self.log("Empty file")
            return 0

        data = self.getEBMLId()

        # Check for 1A 45 DF A3
        if data != 0x1A45DFA3:
            self.log("Not a proper MKV")
            return 0

        datasize = self.getDataSize()
        
        try:
            self.File.seek(datasize, 1)
        except:
            self.log('Error while seeking')
            return 0

        data = self.getEBMLId()

        # Look for the segment header
        while data != 0x18538067 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()
        data = self.getEBMLId()

        # Find segment info
        while data != 0x1549A966 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()

        if self.File.tell() < filesize:
            return datasize

        return 0


    def getFileSize(self):
        size = 0
        
        try:
            pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(pos, 0)
        except:
            pass

        return size


    def getData(self, datasize):
        data = self.File.read(datasize)
        return data


    def getDataSize(self):
        data = self.File.read(1)

        try:
            firstbyte = struct.unpack('>B', data)[0]
            datasize = firstbyte
            mask = 0xFFFF
    
            for i in range(8):
                if datasize >> (7 - i) == 1:
                    mask = mask ^ (1 << (7 - i))
                    break

            datasize = datasize & mask
    
            if firstbyte >> 7 != 1:
                for i in range(1, 8):
                    datasize = (datasize << 8) + struct.unpack('>B', self.File.read(1))[0]
    
                    if firstbyte >> (7 - i) == 1:
                        break
        except:
            datasize = 0

        return datasize


    def getEBMLId(self):
        data = self.File.read(1)

        try:
            firstbyte = struct.unpack('>B', data)[0]
            ID = firstbyte
    
            if firstbyte >> 7 != 1:
                for i in range(1, 4):
                    ID = (ID << 8) + struct.unpack('>B', self.File.read(1))[0]
    
                    if firstbyte >> (7 - i) == 1:
                        break
        except:
            ID = 0

        return ID

########NEW FILE########
__FILENAME__ = MP4Parser
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, struct

from resources.lib.FileAccess import FileAccess


class MP4DataBlock:
    def __init__(self):
        self.size = -1
        self.boxtype = ''
        self.data = ''



class MP4MovieHeader:
    def __init__(self):
        self.version = 0
        self.flags = 0
        self.created = 0
        self.modified = 0
        self.scale = 0
        self.duration = 0



class MP4Parser:
    def __init__(self):
        self.MovieHeader = MP4MovieHeader()


    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('MP4Parser: ' + msg, level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb")
        except:
            self.log("Unable to open the file")
            return

        dur = self.readHeader()
        self.File.close()
        self.log("Duration: " + str(dur))
        return dur


    def readHeader(self):
        data = self.readBlock()

        if data.boxtype != 'ftyp':
            self.log("No file block")
            return 0

        # Skip past the file header
        try:
            self.File.seek(data.size, 1)
        except:
            self.log('Error while seeking')
            return 0

        data = self.readBlock()

        while data.boxtype != 'moov' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.readBlock()

        data = self.readBlock()

        while data.boxtype != 'mvhd' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.readBlock()

        self.readMovieHeader()

        if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
            return int(self.MovieHeader.duration / self.MovieHeader.scale)

        return 0


    def readMovieHeader(self):
        try:
            self.MovieHeader.version = struct.unpack('>b', self.File.read(1))[0]
            self.File.read(3)   #skip flags for now
    
            if self.MovieHeader.version == 1:
                data = struct.unpack('>QQIQQ', self.File.read(36))
            else:
                data = struct.unpack('>IIIII', self.File.read(20))

            self.MovieHeader.created = data[0]
            self.MovieHeader.modified = data[1]
            self.MovieHeader.scale = data[2]
            self.MovieHeader.duration = data[3]
        except:
            self.MovieHeader.duration = 0


    def readBlock(self):
        box = MP4DataBlock()
        data = self.File.read(4)
        
        try:
            box.size = struct.unpack('>I', data)[0]
            box.boxtype = self.File.read(4)
    
            if box.size == 1:
                box.size = struct.unpack('>q', self.File.read(8))[0]
                box.size -= 8
    
            box.size -= 8
    
            if box.boxtype == 'uuid':
                box.boxtype = self.File.read(16)
                box.size -= 16
        except:
            pass

        return box

########NEW FILE########
__FILENAME__ = Playlist
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmcgui, xbmc
import threading
import time

from FileAccess import FileAccess



class PlaylistItem:
    def __init__(self):
        self.duration = 0
        self.filename = ''
        self.description = ''
        self.title = ''
        self.episodetitle = ''



class Playlist:
    def __init__(self):
        self.itemlist = []
        self.totalDuration = 0
        self.processingSemaphore = threading.BoundedSemaphore()


    def getduration(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            dur = self.itemlist[index].duration
            self.processingSemaphore.release()
            return dur

        self.processingSemaphore.release()
        return 0


    def size(self):
        self.processingSemaphore.acquire()
        totsize = len(self.itemlist)
        self.processingSemaphore.release()
        return totsize


    def getfilename(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            fname = self.itemlist[index].filename
            self.processingSemaphore.release()
            return fname

        self.processingSemaphore.release()
        return ''


    def getdescription(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            desc = self.itemlist[index].description
            self.processingSemaphore.release()
            return desc

        self.processingSemaphore.release()
        return ''


    def getepisodetitle(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            epit = self.itemlist[index].episodetitle
            self.processingSemaphore.release()
            return epit

        self.processingSemaphore.release()
        return ''


    def getTitle(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            title = self.itemlist[index].title
            self.processingSemaphore.release()
            return title

        self.processingSemaphore.release()
        return ''


    def clear(self):
        del self.itemlist[:]
        self.totalDuration = 0


    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('script.pseudotv-Playlist: ' + msg, level)


    def load(self, filename):
        self.log("load " + filename)
        self.processingSemaphore.acquire()
        self.clear()

        try:
            fle = FileAccess.open(filename, 'r')
        except IOError:
            self.log('Unable to open the file: ' + filename)
            self.processingSemaphore.release()
            return False

        # find and read the header
        lines = fle.readlines()
        fle.close()
        realindex = -1

        for i in range(len(lines)):
            if lines[i] == '#EXTM3U\n':
                realindex = i
                break

        if realindex == -1:
            self.log('Unable to find playlist header for the file: ' + filename)
            self.processingSemaphore.release()
            return False

        # past the header, so get the info
        for i in range(len(lines)):
            time.sleep(0)

            if realindex + 1 >= len(lines):
                break

            if len(self.itemlist) > 4096:
                break

            line = lines[realindex]

            if line[:8] == '#EXTINF:':
                tmpitem = PlaylistItem()
                index = line.find(',')

                if index > 0:
                    tmpitem.duration = int(line[8:index])
                    tmpitem.title = line[index + 1:-1]
                    index = tmpitem.title.find('//')

                    if index >= 0:
                        tmpitem.episodetitle = tmpitem.title[index + 2:]
                        tmpitem.title = tmpitem.title[:index]
                        index = tmpitem.episodetitle.find('//')

                        if index >= 0:
                            tmpitem.description = tmpitem.episodetitle[index + 2:]
                            tmpitem.episodetitle = tmpitem.episodetitle[:index]

                realindex += 1
                tmpitem.filename = lines[realindex][:-1]
                self.itemlist.append(tmpitem)
                self.totalDuration += tmpitem.duration

            realindex += 1

        self.processingSemaphore.release()

        if len(self.itemlist) == 0:
            return False

        return True


    def save(self, filename):
        self.log("save " + filename)
        try:
            fle = FileAccess.open(filename, 'w')
        except:
            self.log("save Unable to open the smart playlist", xbmc.LOGERROR)
            return

        flewrite = "#EXTM3U\n"

        for i in range(self.size()):
            tmpstr = str(self.getduration(i)) + ','
            tmpstr += self.getTitle(i) + "//" + self.getepisodetitle(i) + "//" + self.getdescription(i)
            tmpstr = tmpstr[:600]
            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
            tmpstr = tmpstr + '\n' + self.getfilename(i)
            flewrite += "#EXTINF:" + tmpstr + "\n"

        fle.write(flewrite)
        fle.close()


########NEW FILE########
__FILENAME__ = Rules
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from Globals import *
from Playlist import PlaylistItem



class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(), ScheduleChannelRule(), HandleChannelLogo(), NoShowRule(), DontAddChannel(), ForceRandom(), ForceRealTime(), ForceResume(), HandleIceLibrary(), InterleaveChannel(), OnlyUnWatchedRule(), OnlyWatchedRule(), AlwaysPause(), PlayShowInOrder(), RenameRule(), SetResetTime()]


    def getRuleCount(self):
        return len(self.ruleList)


    def getRule(self, index):
        while index < 0:
            index += len(self.ruleList)

        while index >= len(self.ruleList):
            index -= len(self.ruleList)

        return self.ruleList[index]



class BaseRule:
    def __init__(self):
        self.name = ""
        self.description = ""
        self.optionLabels = []
        self.optionValues = []
        self.myId = 0
        self.actions = 0


    def getName(self):
        return self.name


    def getTitle(self):
        return self.name


    def getOptionCount(self):
        return len(self.optionLabels)


    def onAction(self, act, optionindex):
        return ''


    def getOptionLabel(self, index):
        if index >= 0 and index < self.getOptionCount():
            return self.optionLabels[index]

        return ''


    def getOptionValue(self, index):
        if index >= 0 and index < len(self.optionValues):
            return self.optionValues[index]

        return ''


    def getRuleIndex(self, channeldata):
        index = 0

        for rule in channeldata.ruleList:
            if rule == self:
                return index

            index += 1

        return -1


    def getId(self):
        return self.myId


    def runAction(self, actionid, channelList, param):
        return param


    def copy(self):
        return BaseRule()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log("Rule " + self.getTitle() + ": " + msg, level)


    def validate(self):
        pass


    def reset(self):
        self.__init__()


    def validateTextBox(self, optionindex, length):
        if len(self.optionValues[optionindex]) > length:
            self.optionValues[optionindex] = self.optionValues[optionindex][:length]


    def onActionTextBox(self, act, optionindex):
        action = act.getId()

        if act.getId() == ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText()

        button = act.getButtonCode()

        # Upper-case values
        if button >= 0x2f041 and button <= 0x2f05b:
            self.optionValues[optionindex] += chr(button - 0x2F000)

        # Lower-case values
        if button >= 0xf041 and button <= 0xf05b:
            self.optionValues[optionindex] += chr(button - 0xEFE0)

        # Numbers
        if action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            self.optionValues[optionindex] += chr(action - ACTION_NUMBER_0 + 48)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        # Delete
        if button == 0xF02E:
            self.optionValues[optionindex] = ''

        # Space
        if button == 0xF020:
            self.optionValues[optionindex] += ' '

        if xbmc.getCondVisibility("Window.IsVisible(10111)"):
            self.log("shutdown window is visible")
            xbmc.executebuiltin("Dialog.close(10111)")


    def onActionDateBox(self, act, optionindex):
        self.log("onActionDateBox")

        if act.getId() == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(1, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info != None:
                self.optionValues[optionindex] = info


    def onActionTimeBox(self, act, optionindex):
        self.log("onActionTimeBox")
        action = act.getId()

        if action == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(2, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info != None:
                if info[0] == ' ':
                    info = info[1:]

                if len(info) == 4:
                    info = "0" + info

                self.optionValues[optionindex] = info

        button = act.getButtonCode()

        # Numbers
        if action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            value = action - ACTION_NUMBER_0
            length = len(self.optionValues[optionindex])

            if length == 0:
                if value <= 2:
                    self.optionValues[optionindex] = chr(value + 48)
            elif length == 1:
                if int(self.optionValues[optionindex][0]) == 2:
                    if value < 4:
                        self.optionValues[optionindex] += chr(value + 48)
                else:
                    self.optionValues[optionindex] += chr(value + 48)
            elif length == 2:
                if value < 6:
                    self.optionValues[optionindex] += ":" + chr(value + 48)
            elif length < 5:
                self.optionValues[optionindex] += chr(value + 48)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                if len(self.optionValues[optionindex]) == 4:
                    self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]


    def validateTimeBox(self, optionindex):
        values = []
        broken = False

        try:
            values.append(int(self.optionValues[optionindex][0]))
            values.append(int(self.optionValues[optionindex][1]))
            values.append(int(self.optionValues[optionindex][3]))
            values.append(int(self.optionValues[optionindex][4]))
        except:
            self.optionValues[optionindex] = "00:00"
            return

        if values[0] > 2:
            broken = True

        if values[0] == 2:
            if values[1] > 3:
                broken = True

        if values[2] > 5:
            broken = True

        if broken:
            self.optionValues[optionindex] = "00:00"
            return


    def onActionSelectBox(self, act, optionindex):
        if act.getId() == ACTION_SELECT_ITEM:
            optioncount = len(self.selectBoxOptions[optionindex])
            cursel = -1

            for i in range(optioncount):
                if self.selectBoxOptions[optionindex][i] == self.optionValues[optionindex]:
                    cursel = i
                    break

            cursel += 1

            if cursel >= optioncount:
                cursel = 0

            self.optionValues[optionindex] = self.selectBoxOptions[optionindex][cursel]


    def onActionDaysofWeekBox(self, act, optionindex):
        self.log("onActionDaysofWeekBox")

        if act.getId() == ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText().upper()

        button = act.getButtonCode()

        # Remove the shift key if it's there
        if button >= 0x2F041 and button <= 0x2F05B:
            button -= 0x20000

        # Pressed some character
        if button >= 0xF041 and button <= 0xF05B:
            button -= 0xF000

            # Check for UMTWHFS
            if button == 85 or button == 77 or button == 84 or button == 87 or button == 72 or button == 70 or button == 83:
                # Check to see if it's already in the string
                loc = self.optionValues[optionindex].find(chr(button))

                if loc != -1:
                    self.optionValues[optionindex] = self.optionValues[optionindex][:loc] + self.optionValues[optionindex][loc + 1:]
                else:
                    self.optionValues[optionindex] += chr(button)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        if xbmc.getCondVisibility("Window.IsVisible(10111)"):
            self.log("shutdown window is visible")
            xbmc.executebuiltin("Dialog.close(10111)")


    def validateDaysofWeekBox(self, optionindex):
        self.log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''

        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)

            if loc != -1:
                newstr += day

        self.optionValues[optionindex] = newstr


    def validateDigitBox(self, optionindex, minimum, maximum, default):
        if len(self.optionValues[optionindex]) == 0:
            return

        try:
            val = int(self.optionValues[optionindex])

            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = str(val)

            return
        except:
            pass

        self.optionValues[optionindex] = str(default)


    def onActionDigitBox(self, act, optionindex):
        action = act.getId()

        if action == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            value = dlg.numeric(0, self.optionLabels[optionindex], self.optionValues[optionindex])

            if value != None:
                self.optionValues[optionindex] = value

        button = act.getButtonCode()

        # Numbers
        if action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            self.optionValues[optionindex] += chr(action - ACTION_NUMBER_0 + 48)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        # Delete
        if button == 0xF02E:
            self.optionValues[optionindex] = ''



class RenameRule(BaseRule):
    def __init__(self):
        self.name = "Set Channel Name"
        self.optionLabels = ['New Channel Name']
        self.optionValues = ['']
        self.myId = 1
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return RenameRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return 'Rename Channel to ' + self.optionValues[0]

        return self.name


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 18)


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            self.validate()
            channeldata.name = self.optionValues[0]

        return channeldata



class NoShowRule(BaseRule):
    def __init__(self):
        self.name = "Don't Include a Show"
        self.optionLabels = ['Show Name']
        self.optionValues = ['']
        self.myId = 2
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return NoShowRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Don't Include '" + self.optionValues[0] + "'"

        return self.name


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 20)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.validate()
            opt = self.optionValues[0].lower()
            realindex = 0

            for index in range(len(filelist)):
                item = filelist[realindex]
                loc = item.find(',')

                if loc > -1:
                    loc2 = item.find("//")

                    if loc2 > -1:
                        showname = item[loc + 1:loc2]
                        showname = showname.lower()

                        if showname.find(opt) > -1:
                            filelist.pop(realindex)
                            realindex -= 1

                realindex += 1

        return filelist



class ScheduleChannelRule(BaseRule):
    def __init__(self):
        self.name = "Best-Effort Channel Scheduling"
        self.optionLabels = ['Channel Number', 'Days of the Week (UMTWHFS)', 'Time (HH:MM)', 'Episode Count', 'Starting Episode', 'Starting Date (DD/MM/YYYY)']
        self.optionValues = ['0', '', '00:00', '1', '1', '']
        self.myId = 3
        self.actions = RULES_ACTION_START | RULES_ACTION_BEFORE_CLEAR | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.clearedcount = 0
        self.appended = False
        self.hasRun = False
        self.nextScheduledTime = 0
        self.startIndex = 0


    def copy(self):
        return ScheduleChannelRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Schedule Channel " + self.optionValues[0]

        return self.name


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 1:
            self.onActionDaysofWeekBox(act, optionindex)

        if optionindex == 2:
            self.onActionTimeBox(act, optionindex)

        if optionindex == 3:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 4:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 5:
            self.onActionDateBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, '')
        self.validateDaysofWeekBox(1)
        self.validateTimeBox(2)
        self.validateDigitBox(3, 1, 1000, 1)
        self.validateDigitBox(4, 1, 1000, 1)


    def runAction(self, actionid, channelList, channeldata):
        self.log("runAction " + str(actionid))

        if actionid == RULES_ACTION_START:
            self.clearedcount = 0
            self.hasRun = False
            self.nextScheduledTime = 0

        if actionid == RULES_ACTION_BEFORE_CLEAR:
            self.clearedcount = channeldata.Playlist.size()

            if channeldata.totalTimePlayed > 0:
                self.appended = True
            else:
                self.appended = False

        # When resetting the channel, make sure the starting episode and date are correct.
        # Work backwards from the current ep and date to set the current date to today and proper ep
        if actionid == RULES_ACTION_FINAL_MADE and self.hasRun == False:
            curchan = channeldata.channelNumber
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_lastscheduled', '0')

            for rule in channeldata.ruleList:
                if rule.getId() == self.myId:
                    rule.reverseStartingEpisode()
                    rule.nextScheduledTime = 0

        if (actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED) and (self.hasRun == False):
            self.runSchedulingRules(channelList, channeldata)

        return channeldata


    def reverseStartingEpisode(self):
        self.log("reverseStartingEpisode")
        tmpdate = 0

        try:
            tmpdate = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], "%d/%m/%Y %H:%M"))
        except:
            pass

        if tmpdate > 0:
            count = 0
            currentdate = int(time.time())

            while tmpdate > currentdate:
                thedate = datetime.datetime.fromtimestamp(currentdate)
                self.optionValues[5] = thedate.strftime("%d/%m/%Y")
                self.determineNextTime()

                if self.nextScheduledTime > 0:
                    count += 1
                    currentdate = self.nextScheduledTime + (60 * 60 * 24)
                else:
                    break

            try:
                startep = int(self.optionValues[4])
                count = startep - count

                if count > 0:
                    self.optionValues[4] = str(count)
                    thedate = datetime.datetime.fromtimestamp(int(time.time()))
#                        self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
                    self.optionValues[5] = thedate.strftime("%d/%m/%Y")
                    self.saveOptions(channeldata)
            except:
                pass


    def runSchedulingRules(self, channelList, channeldata):
        self.log("runSchedulingRules")
        curchan = channelList.runningActionChannel
        self.hasRun = True

        try:
            self.startIndex = int(ADDON_SETTINGS.getSetting('Channel_' + str(curchan) + '_lastscheduled'))
        except:
            self.startIndex = 0

        if self.appended == True:
            self.startIndex -= self.clearedcount - channeldata.Playlist.size()

        if self.startIndex < channeldata.playlistPosition:
            self.startIndex = channeldata.fixPlaylistIndex(channeldata.playlistPosition + 1)

            if self.startIndex == 0:
                self.log("Currently playing the last item, odd")
                return

        # Have all scheduling rules determine the next scheduling time
        self.determineNextTime()
        minimum = self

        for rule in channeldata.ruleList:
            if rule.getId() == self.myId:
                if rule.nextScheduledTime == 0:
                    rule.determineNextTime()

                rule.startIndex = self.startIndex
                rule.hasRun = True

                if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                    minimum = rule

        added = True
        newstart = 0

        while added == True and minimum.nextScheduledTime != 0:
            added = minimum.addScheduledShow(channelList, channeldata, self.appended)
            newstart = minimum.startIndex

            # Determine the new minimum
            if added:
                minimum.determineNextTime()

                for rule in channeldata.ruleList:
                    if rule.getId() == self.myId:
                        rule.startIndex = newstart

                        if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                            minimum = rule

        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_lastscheduled', str(newstart))
        # Write the channel playlist to a file
        channeldata.Playlist.save(CHANNELS_LOC + 'channel_' + str(curchan) + '.m3u')


    # Fill in nextScheduledTime
    def determineNextTime(self):
        self.optionValues[5] = self.optionValues[5].replace(' ', '0')
        self.log("determineNextTime " + self.optionValues[5] + " " + self.optionValues[2])
        starttime = 0
        daysofweek = 0

        if len(self.optionValues[2]) != 5 or self.optionValues[2][2] != ':':
            self.log("Invalid time")
            self.nextScheduledTime = 0
            return

        try:
            # This is how it should be, but there is a bug in XBMC preventing this
#            starttime = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], xbmc.getRegion("dateshort") + " %H:%M"))
            starttime = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], "%d/%m/%Y %H:%M"))
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        try:
            tmp = self.optionValues[1]

            if tmp.find('M') > -1:
                daysofweek |= 1

            if tmp.find('T') > -1:
                daysofweek |= 2

            if tmp.find('W') > -1:
                daysofweek |= 4

            if tmp.find('H') > -1:
                daysofweek |= 8

            if tmp.find('F') > -1:
                daysofweek |= 16

            if tmp.find('S') > -1:
                daysofweek |= 32

            if tmp.find('U') > -1:
                daysofweek |= 64
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        thedate = datetime.datetime.fromtimestamp(starttime)
        delta = datetime.timedelta(days=1)

        # If no day selected, assume every day
        if daysofweek == 0:
            daysofweek = 127

        # Determine the proper day of the week
        while True:
            if daysofweek & (1 << thedate.weekday()) > 0:
                break

            thedate += delta

        self.nextScheduledTime = int(time.mktime(thedate.timetuple()))


    def saveOptions(self, channeldata):
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata) + 1
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_5', self.optionValues[4])
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_6', self.optionValues[5])


    # Add a single show (or shows) to the channel at nextScheduledTime
    # This needs to modify the startIndex value if something is added
    def addScheduledShow(self, channelList, channeldata, appending):
        self.log("addScheduledShow")
        chan = 0
        epcount = 0
        startingep = 0
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata)
        currentchantime = channelList.lastExitTime + channeldata.totalTimePlayed

        if channeldata.Playlist.size() == 0:
            return False

        try:
            chan = int(self.optionValues[0])
            epcount = int(self.optionValues[3])
            startingep = int(self.optionValues[4]) - 1
        except:
            pass

        if startingep < 0:
            startingep = 0

        # If the next scheduled show has already passed, then skip it
        if currentchantime > self.nextScheduledTime:
            thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
            delta = datetime.timedelta(days=1)
            thedate += delta
            self.optionValues[4] = str(startingep + epcount)
#            self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
            self.optionValues[5] = thedate.strftime("%d/%m/%Y")
            self.log("Past the scheduled date and time, skipping")
            self.saveOptions(channeldata)
            return True

        if chan > channelList.maxChannels or chan < 1 or epcount < 1:
            self.log("channel number is invalid")
            return False

        if len(channelList.channels) < chan or channelList.channels[chan - 1].isSetup == False:
            if channelList.myOverlay.isMaster:
                channelList.setupChannel(chan, True, True, False)
            else:
                channelList.setupChannel(chan, True, False, False)

        if channelList.channels[chan - 1].Playlist.size() < 1:
            self.log("scheduled channel isn't valid")
            return False

        # If the total time played value hasn't been updated
        if appending == False:
            timedif = self.nextScheduledTime - channelList.lastExitTime
        else:
            # If the total time played value HAS been updated
            timedif = self.nextScheduledTime + channeldata.totalTimePlayed - channelList.myOverlay.timeStarted

        showindex = 0

        # Find the proper location to insert the show(s)
        while timedif > 120 or showindex < self.startIndex:
            timedif -= channeldata.getItemDuration(showindex)
            showindex = channeldata.fixPlaylistIndex(showindex + 1)

            # Shows that there was a looparound, so exit.
            if showindex == 0:
                self.log("Couldn't find a location for the show")
                return False

        # If there is nothing after the selected show index and the time is still
        # too far away, don't do anything
        if (channeldata.Playlist.size() - (showindex + 1) <= 0) and (timedif < -300):
            return False

        # rearrange episodes to get an optimal time
        if timedif < -300 and channeldata.isRandom:
            # This is a crappy way to do it, but implementing a subset sum algorithm is
            # a bit daunting at the moment.  Plus this uses a minimum amount of memory, so as
            # a background task it works well.
            lasttime = int(abs(timedif))

            # Try a maximum of 5 loops
            for loops in range(5):
                newtime = self.rearrangeShows(showindex, lasttime, channeldata, channelList)

                if channelList.threadPause() == False:
                    return False

                # If no match found, then stop
                # If the time difference is less than 2 minutes, also stop
                if newtime == lasttime or newtime < 120:
                    break

                lasttime = newtime

        for i in range(epcount):
            item = PlaylistItem()
            item.duration = channelList.channels[chan - 1].getItemDuration(startingep + i)
            item.filename = channelList.channels[chan - 1].getItemFilename(startingep + i)
            item.description = channelList.channels[chan - 1].getItemDescription(startingep + i)
            item.title = channelList.channels[chan - 1].getItemTitle(startingep + i)
            item.episodetitle = channelList.channels[chan - 1].getItemEpisodeTitle(startingep + i)
            channeldata.Playlist.itemlist.insert(showindex, item)
            channeldata.Playlist.totalDuration += item.duration
            showindex += 1

        thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
        delta = datetime.timedelta(days=1)
        thedate += delta
        self.startIndex = showindex
        self.optionValues[4] = str(startingep + epcount + 1)
#        self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
        self.optionValues[5] = thedate.strftime("%d/%m/%Y")
        self.saveOptions(channeldata)
        self.log("successfully scheduled at index " + str(self.startIndex))
        return True


    def rearrangeShows(self, showindex, timedif, channeldata, channelList):
        self.log("rearrangeShows " + str(showindex) + " " + str(timedif))
        self.log("start index: " + str(self.startIndex) + ", end index: " + str(showindex))
        matchdur = timedif
        matchidxa = 0
        matchidxb = 0

        if self.startIndex >= showindex:
            self.log("Invalid indexes")
            return timedif

        if channeldata.Playlist.size() - (showindex + 1) <= 0:
            self.log("No shows after the show index")
            return timedif

        for curindex in range(self.startIndex, showindex + 1):
            neededtime = channeldata.getItemDuration(curindex) - timedif

            if channelList.threadPause() == False:
                return timedif

            if neededtime > 0:
                for inx in range(showindex + 1, channeldata.Playlist.size()):
                    curtime = channeldata.getItemDuration(inx) - neededtime

                    if abs(curtime) < matchdur:
                        matchdur = abs(curtime)
                        matchidxa = curindex
                        matchidxb = inx

        # swap curindex with inx
        if matchdur < abs(timedif):
            self.log("Found with a new timedif of " + str(matchdur) + "!  Swapping " + str(matchidxa) + " with " + str(matchidxb))
            plitema = channeldata.Playlist.itemlist[matchidxa]
            plitemb = channeldata.Playlist.itemlist[matchidxb]
            channeldata.Playlist.itemlist[matchidxa] = plitemb
            channeldata.Playlist.itemlist[matchidxb] = plitema
            return matchdur

        self.log("No match found")
        return timedif



class OnlyWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Watched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 4
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc == 0:
                return ''

        return filedata



class DontAddChannel(BaseRule):
    def __init__(self):
        self.name = "Don't Play This Channel"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 5
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return DontAddChannel()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channeldata.isValid = False

        return channeldata



class InterleaveChannel(BaseRule):
    def __init__(self):
        self.name = "Interleave Another Channel"
        self.optionLabels = ['Channel Number', 'Min Interleave Count', 'Max Interleave Count', 'Starting Episode']
        self.optionValues = ['0', '1', '1', '1']
        self.myId = 6
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return InterleaveChannel()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Interleave Channel " + self.optionValues[0]

        return self.name


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, 0)
        self.validateDigitBox(1, 1, 100, 1)
        self.validateDigitBox(2, 1, 100, 1)
        self.validateDigitBox(3, 1, 10000, 1)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.log("runAction")
            chan = 0
            minint = 0
            maxint = 0
            startingep = 0
            curchan = channelList.runningActionChannel
            curruleid = channelList.runningActionId
            self.validate()

            try:
                chan = int(self.optionValues[0])
                minint = int(self.optionValues[1])
                maxint = int(self.optionValues[2])
                startingep = int(self.optionValues[3])
            except:
                self.log("Except when reading params")

            if chan > channelList.maxChannels or chan < 1 or minint < 1 or maxint < 1 or startingep < 1:
                return filelist

            if minint > maxint:
                v = minint
                minint = maxint
                maxint = v

            if len(channelList.channels) < chan or channelList.channels[chan - 1].isSetup == False:
                if channelList.myOverlay.isMaster:
                    channelList.setupChannel(chan, True, True, False)
                else:
                    channelList.setupChannel(chan, True, False, False)

            if channelList.channels[chan - 1].Playlist.size() < 1:
                self.log("The target channel is empty")
                return filelist

            realindex = random.randint(minint, maxint)
            startindex = 0
            # Use more memory, but greatly speed up the process by just putting everything into a new list
            newfilelist = []
            self.log("Length of original list: " + str(len(filelist)))

            while realindex < len(filelist):
                if channelList.threadPause() == False:
                    return filelist

                while startindex < realindex:
                    newfilelist.append(filelist[startindex])
                    startindex += 1

                newstr = str(channelList.channels[chan - 1].getItemDuration(startingep - 1)) + ',' + channelList.channels[chan - 1].getItemTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemEpisodeTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemDescription(startingep - 1) + '\n' + channelList.channels[chan - 1].getItemFilename(startingep - 1)
                newfilelist.append(newstr)
                realindex += random.randint(minint, maxint)
                startingep += 1

            while startindex < len(filelist):
                newfilelist.append(filelist[startindex])
                startindex += 1

            startingep = channelList.channels[chan - 1].fixPlaylistIndex(startingep) + 1
            # Write starting episode
            self.optionValues[2] = str(startingep)
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid + 1) + '_opt_4', self.optionValues[2])
            self.log("Done interleaving, new length is " + str(len(newfilelist)))
            return newfilelist

        return filelist



class ForceRealTime(BaseRule):
    def __init__(self):
        self.name = "Force Real-Time Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 7
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRealTime()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_REALTIME

        return channeldata



class AlwaysPause(BaseRule):
    def __init__(self):
        self.name = "Pause When Not Watching"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 8
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return AlwaysPause()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode |= MODE_ALWAYSPAUSE

        return channeldata


class ForceResume(BaseRule):
    def __init__(self):
        self.name = "Force Resume Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 9
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceResume()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RESUME

        return channeldata



class ForceRandom(BaseRule):
    def __init__(self):
        self.name = "Force Random Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 10
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRandom()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RANDOM

        return channeldata



class OnlyUnWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Unwatched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 11
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyUnWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc > 0:
                return ''

        return filedata



class PlayShowInOrder(BaseRule):
    def __init__(self):
        self.name = "Play TV Shows In Order"
        self.optionLabels = []
        self.optionValues = []
        self.showInfo = []
        self.myId = 12
        self.actions = RULES_ACTION_START | RULES_ACTION_JSON | RULES_ACTION_LIST


    def copy(self):
        return PlayShowInOrder()


    def runAction(self, actionid, channelList, param):
        if actionid == RULES_ACTION_START:
            del self.showInfo[:]

        if actionid == RULES_ACTION_JSON:
            self.storeShowInfo(channelList, param)

        if actionid == RULES_ACTION_LIST:
            return self.sortShows(channelList, param)

        return param


    def storeShowInfo(self, channelList, filedata):
        # Store the filename, season, and episode number
        match = re.search('"file" *: *"(.*?)",', filedata)

        if match:
            showtitle = re.search('"showtitle" *: *"(.*?)"', filedata)
            season = re.search('"season" *: *(.*?),', filedata)
            episode = re.search('"episode" *: *(.*?),', filedata)

            try:
                seasonval = int(season.group(1))
                epval = int(episode.group(1))
                self.showInfo.append([showtitle.group(1), match.group(1).replace("\\\\", "\\"), seasonval, epval])
            except:
                pass


    def sortShows(self, channelList, filelist):
        if len(self.showInfo) == 0:
            return filelist

        newfilelist = []
        self.showInfo.sort(key=lambda seep: seep[3])
        self.showInfo.sort(key=lambda seep: seep[2])
        self.showInfo.sort(key=lambda seep: seep[0])

        # Create a new array. It will have 2 dimensions.  The first dimension is a certain show.  This show
        # name is in index 0 of the second dimension.  The currently used index is in index 1.  The other
        # items are the file names in season / episode order.
        showlist = []
        curshow = self.showInfo[0][0]
        showlist.append([])
        showlist[0].append(curshow.lower())
        showlist[0].append(0)

        for item in self.showInfo:
            if channelList.threadPause() == False:
                return filelist

            if item[0] != curshow:
                curshow = item[0]
                showlist.append([])
                showlist[-1].append(curshow.lower())
                showlist[-1].append(0)

            showstr = self.findInFileList(filelist, item[1])

            if len(showstr) > 0:
                showlist[-1].append(showstr)

        curindex = 0

        for item in filelist:
            if channelList.threadPause() == False:
                return filelist

            # First, get the current show for the entry
            pasttime = item.find(',')

            if pasttime > -1:
                endofshow = item.find("//")

                if endofshow > -1:
                    show = item[pasttime + 1:endofshow].lower()

                    for entry in showlist:
                        if entry[0] == show:
                            if len(entry) == 2:
                                break

                            filelist[curindex] = entry[entry[1] + 2]
                            entry[1] += 1

                            if entry[1] > (len(entry) - 3):
                                entry[1] = 0

                            break

            curindex += 1

        return filelist


    def findInFileList(self, filelist, text):
        text = text.lower()

        for item in filelist:
            tmpitem = item.lower()

            if tmpitem.find(text) > -1:
                return item

        return ''



class SetResetTime(BaseRule):
    def __init__(self):
        self.name = "Reset Every x Days"
        self.optionLabels = ['Number of Days']
        self.optionValues = ['5']
        self.myId = 13
        self.actions = RULES_ACTION_START


    def copy(self):
        return SetResetTime()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            if self.optionValues[0] == '1':
                return "Reset Every Day"
            else:
                return "Reset Every " + self.optionValues[0] + " Days"

        return self.name


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 50, '')


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            curchan = channeldata.channelNumber
            numdays = 0

            try:
                numdays = int(self.optionValues[0])
            except:
                pass

            if numdays <= 0:
                self.log("Invalid day count: " + str(numdays))
                return channeldata

            rightnow = int(time.time())
            nextreset = rightnow

            try:
                nextreset = int(ADDON_SETTINGS.getSetting('Channel_' + str(curchan) + '_SetResetTime'))
            except:
                pass

            if rightnow >= nextreset:
                channeldata.isValid = False
                ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_changed', 'True')
                nextreset = rightnow + (60 * 60 * 24 * numdays)
                ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_SetResetTime', str(nextreset))

        return channeldata



class HandleIceLibrary(BaseRule):
    def __init__(self):
        self.name = "IceLibrary Streams"
        self.optionLabels = ['Include Streams']
        self.optionValues = ['Yes']
        self.myId = 14
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandleIceLibrary()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Include IceLibrary Streams'
        else:
            return 'Exclude IceLibrary Streams'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.storedIceLibValue = channelList.incIceLibrary
            self.log("Option for IceLibrary is " + self.optionValues[0])

            if self.optionValues[0] == 'Yes':
                channelList.incIceLibrary = True
            else:
                channelList.incIceLibrary = False
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.incIceLibrary = self.storedIceLibValue

        return channeldata



class HandleChannelLogo(BaseRule):
    def __init__(self):
        self.name = "Channel Logo"
        self.optionLabels = ['Display the Logo']
        self.optionValues = ['Yes']
        self.myId = 15
        self.actions = RULES_ACTION_OVERLAY_SET_CHANNEL | RULES_ACTION_OVERLAY_SET_CHANNEL_END
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandleChannelLogo()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Display the Channel Logo'
        else:
            return 'Hide the Channel Logo'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, overlay, channeldata):
        if actionid == RULES_ACTION_OVERLAY_SET_CHANNEL:
            self.storedLogoValue = overlay.showChannelBug

            if self.optionValues[0] == 'Yes':
                overlay.showChannelBug = True
                self.log("setting channel bug to true")
            else:
                overlay.showChannelBug = False
        elif actionid == RULES_ACTION_OVERLAY_SET_CHANNEL_END:
            overlay.showChannelBug = self.storedLogoValue
            self.log("set channel bug to " + str(overlay.showChannelBug))

        return channeldata


########NEW FILE########
__FILENAME__ = Settings
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcaddon
import sys, re, os
import time
import Globals

from FileAccess import FileLock, FileAccess



class Settings:
    def __init__(self):
        self.logfile = xbmc.translatePath(os.path.join(Globals.SETTINGS_LOC, 'settings2.xml'))
        self.currentSettings = []


    def loadSettings(self):
        self.log("Loading settings from " + self.logfile);

        if Globals.GlobalFileLock.lockFile(self.logfile) == False:
            self.log("Unable to lock the settings file before loading it")

        del self.currentSettings[:]

        if FileAccess.exists(self.logfile):
            try:
                fle = FileAccess.open(self.logfile, "r")
                curset = fle.readlines()
                fle.close()
            except:
                pass

            for line in curset:
                name = re.search('setting id="(.*?)"', line)

                if name:
                    val = re.search(' value="(.*?)"', line)

                    if val:
                        self.currentSettings.append([name.group(1), val.group(1)])

        Globals.GlobalFileLock.unlockFile(self.logfile)


    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('Settings: ' + msg, level)


    def getSetting(self, name, force = False):
        if force:
            self.loadSettings()

        result = self.getSettingNew(name)

        if result is None:
            return self.realGetSetting(name)

        return result


    def getSettingNew(self, name):
        for i in range(len(self.currentSettings)):
            if self.currentSettings[i][0] == name:
                return self.currentSettings[i][1]

        return None


    def realGetSetting(self, name):
        try:
            val = Globals.REAL_SETTINGS.getSetting(name)
            return val
        except:
            return ''


    def setSetting(self, name, value):
        found = False

        for i in range(len(self.currentSettings)):
            if self.currentSettings[i][0] == name:
                self.currentSettings[i][1] = value
                found = True
                break

        if found == False:
            self.currentSettings.append([name, value])

        self.writeSettings()


    def writeSettings(self):
        if Globals.GlobalFileLock.lockFile(self.logfile) == False:
            self.log("Unable to lock the settings file before writing it")

        try:
            fle = FileAccess.open(self.logfile, "w")
        except:
            self.log("Unable to open the file for writing")
            return

        flewrite = "<settings>\n"

        for i in range(len(self.currentSettings)):
            flewrite += '    <setting id="' + self.currentSettings[i][0] + '" value="' + self.currentSettings[i][1] + '" />\n'

        flewrite += '</settings>\n'
        fle.write(flewrite)
        fle.close()
        Globals.GlobalFileLock.unlockFile(self.logfile)

########NEW FILE########
__FILENAME__ = VideoParser
#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, platform
import subprocess

import parsers.MP4Parser as MP4Parser
import parsers.AVIParser as AVIParser
import parsers.MKVParser as MKVParser
import parsers.FLVParser as FLVParser

from Globals import *
from FileAccess import FileAccess



class VideoParser:
    def __init__(self):
        self.AVIExts = ['.avi']
        self.MP4Exts = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts = ['.mkv']
        self.FLVExts = ['.flv']


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('VideoParser: ' + msg, level)


    def getVideoLength(self, filename):
        self.log("getVideoLength " + filename)

        if len(filename) == 0:
            self.log("No file name specified")
            return 0

        if FileAccess.exists(filename) == False:
            self.log("Unable to find the file")
            return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        elif ext in self.FLVExts:
            self.parser = FLVParser.FLVParser()
        else:
            self.log("No parser found for extension " + ext)
            return 0

        return self.parser.determineLength(filename)

########NEW FILE########
