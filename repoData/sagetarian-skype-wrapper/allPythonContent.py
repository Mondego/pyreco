__FILENAME__ = helpers
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

import commands
import time
import settings
import shared
import pynotify
import wnck

PyNotify = True
if not pynotify.init("Skype Wrapper"):
    PyNotify = False

installed_packages = {}

def isSkypeWrapperDesktopOnUnityLauncher():
    return "skype-wrapper.desktop" in commands.getoutput("gsettings get com.canonical.Unity.Launcher favorites")

def isInstalled(package_name):
    global installed_packages
    if package_name in installed_packages:
        return installed_packages[package_name]
    shortened = package_name
    if len(package_name) > 5:
        shortened = package_name[0:5]
        
    installed_packages[package_name] = len(commands.getoutput("dpkg -l "+package_name+" | grep \"ii  "+package_name+"\"")) > 0
    return installed_packages[package_name]
    
def haveUnity():
    return isInstalled('unity') or isInstalled('unity-2d')
    
def version(package_name):
    if not isInstalled(package_name):
        return "not installed"
    description = commands.getoutput("dpkg -l "+package_name+" | grep \"ii  "+package_name+"\"")
    clip = description[description.find(" "):].strip()
    clip = clip[clip.find(" "):].strip()
    clip = clip[:clip.find(" ")].strip()
    return clip
    
def isChatBlacklisted(chat) :
    # doesnt work
    return len(chat.AlertString) > 0
    
def isUserBlacklisted(username) :
    return "'"+username+"'" in settings.get_list_of_silence()

class CPULimiter:
    def __init__(self, process):
        shared.set_proc_name('indicator-skype')
        self.process = process
        pidsearch = commands.getoutput("ps -A | grep "+self.process).strip()
        self.pid = None
        if " " in pidsearch:
            d = pidsearch.split(" ") 
            self.pid = d[0]
        
    def getCPUUsage(self):
        if not self.pid:
            raise Exception("No PID to check cpu usage for")
        desc, perc = commands.getoutput("ps -p "+self.pid+" -o %cpu").split("\n")
        self.percentage = float(perc.strip())
        return self.percentage
        
    def limit(self, percentage, Try = 2):
        while True:
            curr_percentage = self.getCPUUsage()
            if curr_percentage > percentage:
                time.sleep(0.5)
            else:
                break;


cpulimiter = CPULimiter("indicator-skype")

pynotifications = {}

def notify(title, body, icon, uid, critical, replace, chattopic = None):
    if PyNotify:
        global pynotifications
        n = None
        tmp = None
        
        # check if this guy is after someone else in a chat room / i.e break messages in a chatroom up by replicant
        while True:
            if chattopic and uid in pynotifications and "chat://"+chattopic in pynotifications and not pynotifications["chat://"+chattopic] == uid:
                uid = uid+"/"
            else:
                break
        
        if uid and uid in pynotifications:
            tmp = pynotifications[uid]
            # check time lapse
            n = tmp['n']
            now = time.time()
            time_lapse = now - tmp['start']
            if replace or time_lapse > 10:
                body = body
            else:
                body = tmp['body'] + "\n" + body
            n.update(title, body, icon)
            n.set_timeout(pynotify.EXPIRES_DEFAULT)
        else:
            n = pynotify.Notification(title, body, icon)
            if uid:
                pynotifications[uid] = {}
                pynotifications[uid]['n'] = n
        if critical:
            n.set_urgency(pynotify.URGENCY_CRITICAL)
        n.show()
        if uid:
            pynotifications[uid]['body'] = body
            pynotifications[uid]['start'] = time.time()
            if chattopic:
                pynotifications["chat://"+chattopic] = uid
            
    else:
        if icon:
            icon = '-i "'+icon+'" '
        os.system('notify-send '+icon+'"'+fullname+'" "'+online_text+'"');
        
def isAuthorizationRequestOpen():
    """Used to determine if the authorization dialog is still open. Fixes the multiple authorization requests."""
    wnck.screen_get_default().force_update()
    window_list = wnck.screen_get_default().get_windows()
    if len(window_list) == 0:
    	return False
    for win in window_list:
        if "Skype API Authorisation Request" in win.get_name():
            return True
    return False    


########NEW FILE########
__FILENAME__ = indicator-applet-skype
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Andreas Happe <andreashappe@snikt.net>
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

# Documentation:
# just start it

import helpers

if helpers.haveUnity():
    import unitylauncher
    
from gi.repository import GObject
import indicate
import gtk
import Skype4Py
import shared
import settings

import os
import sys
import commands
import time
import dbus
import subprocess
import shlex

from PIL import Image
import StringIO
import binascii

import threading

bus = dbus.SessionBus()

def do_nothing(indicator):
    True
    
AppletRunning = True
    
CB_INTERVALS = 500

FOCUSDEBUG = 4
ERROR = 3
WARNING = 2
INFO = 1
VERBOSE = 0

LOGTYPES = {
    0:"VERBOSE: ",
    1:"INFO: ",
    2:"WARNING: ",
    3:"ERROR: ",
    4:"DEVELOPER DEBUG: ",
}

STATUSLIST = {
    1: "Offline",
    2: "Online",
    3: "Away",
    4: "Extended_Away",
    5: "Invisible",
    6: "Busy"
}

SKYPESTATUS = {
    1: Skype4Py.cusOffline,
    2: Skype4Py.cusOnline,
    3: Skype4Py.cusAway,
    4: Skype4Py.cusNotAvailable,
    5: Skype4Py.cusInvisible,
    6: Skype4Py.cusDoNotDisturb,
}

SKYPETOTELEPATHY = {
    Skype4Py.cusOffline:1,
    Skype4Py.cusOnline:2,
    Skype4Py.cusAway:3,
    Skype4Py.cusNotAvailable:4,
    Skype4Py.cusInvisible:5,
    Skype4Py.cusDoNotDisturb:6,
    Skype4Py.cusLoggedOut:1,
    Skype4Py.cusSkypeMe:3,
}

DONOTDISTURB = False

# only display errors
LOGLEVEL = settings.get_debug_level()
LOGFILE = os.getenv("HOME")+"/.skype-wrapper/log.txt"
CPULIMIT = settings.get_cpu_limit()

def createLogFile(retry=None):
    try :
        if not os.path.isfile(LOGFILE):
            f = open(LOGFILE, mode="w")
            f.write("python-skype: "+helpers.version("python-skype")+"\n")
            f.write("python-imaging: "+helpers.version("python-imaging")+"\n")
            f.write("python-indicate: "+helpers.version("python-indicate")+"\n")
            f.write("unity: "+helpers.version("unity")+"\n")
            f.write("unity-2d: "+helpers.version("unity-2d")+"\n")
            f.write("telepathy-mission-control-5: "+helpers.version("telepathy-mission-control-5")+"\n")
            f.close()
        else :
            f = open(LOGFILE, mode="w")
            f.write("------------------------------------------\n")
            f.close()
    except IOError:
        if retry:
            pass
        else:
            os.mkdir(os.getenv("HOME")+"/.skype-wrapper")
            createLogFile(1)

CPUPRIORITY = 0

def limitcpu():
    return
    log("Limiting CPU Usage", VERBOSE)
    if not CPUPRIORITY:
        helpers.cpulimiter.limit(CPULIMIT)

createLogFile()

def log(message, level):
    if level >= LOGLEVEL:
        if settings.get_debug_log():
            f = open(LOGFILE, mode="a")
            f.write(LOGTYPES[level] + message + "\n")
            f.close()
        print LOGTYPES[level] + message

# this is the high-level notification functionality
class NotificationServer:
  def __init__(self):
    self.server = indicate.indicate_server_ref_default()
    self.server.set_type("message.im")
#   this is kinda ugly, or?
    self.server.set_desktop_file("/usr/share/applications/skype-wrapper.desktop")
    self.server.show()
    self.indicators = {}
    pass

  def connect(self, skype):
    self.skype = skype
    self.server.connect("server-display", self.on_click)

  def on_click(self, server,data=None):
    self.skype.skype.Client.Focus()
   
  def show_conversation(self, indicator, timestamp):
    log("Display skype chat and remove missed chat from indicator", INFO)
    
    id = indicator.get_property("id")

    self.skype.remove_conversation(int(id))
    self.skype.show_chat_windows(int(id))
    
    self.reset_indicators()
    
  def show_conversation_quicklist(self, widget, data = None):
    log("Quicklist showing conversation", INFO)
    id = widget.property_get("id")

    self.skype.remove_conversation(int(id))
    self.skype.show_chat_windows(int(id))
    
    self.reset_indicators()
            
  def reset_indicators(self) :
    del self.indicators
    self.indicators = {}
    for _id in self.skype.unread_conversations:
        self.show_indicator(self.skype.unread_conversations[int(_id)])
    if helpers.haveUnity():
        unitylauncher.count(len(self.indicators) + self.skype.incomingfilecount)
        unitylauncher.createUnreadMessageQuickList(self.skype.unread_conversations, self.show_conversation_quicklist)
        unitylauncher.redrawQuicklist()  
        unitylauncher.count(len(self.indicators) + self.skype.incomingfilecount)

  def show_indicator(self, conversation):
    log("Updating Indicator", INFO)
    new = False
    if not conversation.indicator_name in self.indicators:
        self.indicators[conversation.indicator_name] = indicate.Indicator()
        self.indicators[conversation.indicator_name].set_property_bool("draw-attention", True)    
        self.indicators[conversation.indicator_name].set_property("id", str(conversation.id))
        self.indicators[conversation.indicator_name].set_property("indicator_name", str(conversation.indicator_name))
        self.indicators[conversation.indicator_name].connect("user-display", self.show_conversation)
        new = True
    self.indicators[conversation.indicator_name].set_property("name", str(conversation.display_name))    
    self.indicators[conversation.indicator_name].set_property("timestamp", str(conversation.timestamp))
    self.indicators[conversation.indicator_name].set_property_time('time', conversation.timestamp)
    
    # check if the settings want avatars
    user_avatar = None
    if settings.get_display_indicator_avatars():
        user_avatar = SkypeAvatar(conversation.skypereturn.Sender.Handle)
    if user_avatar and user_avatar.filename:
        bitmapVersion = user_avatar.get_bitmap_version()
        self.indicators[conversation.indicator_name].set_property("icon", str(user_avatar.get_bitmap_version()))
    else:
        self.indicators[conversation.indicator_name].set_property("icon", "")
        
    if new:
        self.indicators[conversation.indicator_name].show()
    
    
  def user_online_status(self, user, online_text):
    name = user.DisplayName or user.FullName or user.Handle
    log("User "+name+" "+online_text, INFO)
    if not settings.get_notify_on_useronlinestatuschange() or self.skype.skype_presence == Skype4Py.cusDoNotDisturb or user.Handle == 'echo123':
        return
        
    icon = ""
    if settings.get_display_notification_avatars():
        avatar = SkypeAvatar(user.Handle)
        if avatar.filename:
            icon = avatar.filename
        else:
            icon = "/usr/share/skype-wrapper/icons/skype-wrapper-48.svg"
      
    helpers.notify(name, online_text, icon, "online://"+user.Handle, False, False)  
  
  def new_message(self, conversation):
    if not settings.get_notify_on_messagerecieve() or self.skype.skype_presence == Skype4Py.cusDoNotDisturb:
        return
    #conversation.skypereturn.Chat.Type == Skype4Py.chatTypeMultiChat and  
    conversation.display_name = conversation.skypereturn.Chat.Topic or conversation.display_name
    name = conversation.skypereturn.Sender.DisplayName or conversation.skypereturn.Sender.FullName or conversation.skypereturn.Sender.Handle

    if len(conversation.skypereturn.Chat.Members) > 2:
        group_chat_title = unicode(name + " ► " + conversation.display_name)
    else:
        group_chat_title = unicode(conversation.display_name)
        
    icon = ""
    if settings.get_display_notification_avatars():
        avatar = SkypeAvatar(conversation.skypereturn.Sender.Handle)
        if avatar.filename:
            icon = avatar.filename
        else:
            icon = "/usr/share/skype-wrapper/icons/skype-wrapper-48.svg"
    
    if helpers.haveUnity():
        unitylauncher.count(len(self.indicators) + self.skype.incomingfilecount)
        unitylauncher.createUnreadMessageQuickList(self.skype.unread_conversations, self.show_conversation_quicklist)
        unitylauncher.redrawQuicklist()  
        unitylauncher.count(len(self.indicators) + self.skype.incomingfilecount)
    
    helpers.notify(group_chat_title, conversation.skypereturn.Body, icon, group_chat_title, False, False, conversation.skypereturn.Chat.Topic)  
    
  def file_transfer_event(self, transfer, text):
    if self.skype.skype_presence == Skype4Py.cusDoNotDisturb:
        return
        
    if str(transfer.status) == 'INCOMING' and not settings.get_notify_on_incoming_filetransfer():
        return
        
    if str(transfer.status) == 'OUTGOING' and not settings.get_notify_on_outgoing_filetransfer():
        return
        
    icon = ""
    if settings.get_display_notification_avatars():
        avatar = SkypeAvatar(transfer.partner_username)
        if avatar.filename:
            icon = avatar.filename
        else:
            icon = "/usr/share/skype-wrapper/icons/skype-wrapper-48.svg"
            
    helpers.notify("File Transfer", text, icon, "filetransfer"+transfer.partner_username, True, True)  

# class for retrieving user avatars
class SkypeAvatar:
  def __init__(self, username):
    userfiles = {
        "user256":True, 
        "user1024":True, 
        "user4096":True,  
        "user16384":True,  
        "user32768":True,  
        "user65536":True, 
        "profile256":True,  
        "profile1024":True,  
        "profile4096":True,  
        "profile16384":True,  
        "profile32768":True
    }
    
    self.path = os.getenv("HOME")+"/.thumbnails/normal/"
    skypedir = os.getenv("HOME")+"/.Skype/"+skype.skype.CurrentUser.Handle+"/"
    
    self.image_data = ""
    self.filename = ""
    
    skbin = []
    n = 0
    for f in userfiles:
        fil = "%s%s.dbb" % (skypedir, f)
        try: skbin.append(file(fil, "rb").read())
        except: pass
        n = n + 1
        
    binary = "".join(skbin)
    self.get_icon(username, binary)
    if len(self.image_data) :
        f = open(self.path+"skype-wrapper-"+username+".jpg", mode="w")
        f.write(self.image_data)
        f.close()
        self.filename = self.path+"skype-wrapper-"+username+".jpg"
        log("Wrote avatar to file "+self.filename, INFO)
        
    self.imagepath = self.path+"skype-wrapper-"+username
    return
    
  def get_bitmap_version(self):
    if not self.filename:
        return ""
    im = Image.open(self.filename)
    s = StringIO.StringIO()
    im.save(s, "BMP")
    f = open(self.imagepath+".bmp", mode="w")
    f.write(s.getvalue())
    f.close()
    return binascii.b2a_base64(s.getvalue())#self.imagepath+".bmp"
    
  def get_icon(self, buddy, binary):
    startmark = "\xff\xd8"
    endmark = "\xff\xd9"

    startfix = 0
    endfix = 2

    nick_start = "\x03\x10%s" % buddy
    nick_end = "\x6C\x33\x33\x6C"

    nickstart = binary.find(bytes(nick_start))
    if nickstart == -1: return -1
    log("Found avatar for "+buddy, INFO)
    
    nickend = binary.find(nick_end, nickstart)
    handle = binary[nickstart+2:nickend]
    blockstart = binary.rfind("l33l", 0, nickend)
    imgstart = binary.find(startmark, blockstart, nickend)
    imgend = binary.find(endmark, imgstart)

    imgstart += startfix
    imgend += endfix

    if (imgstart < startfix): 
        return None
        
    self.image_data = binary[imgstart:imgend]
    return True
    

class Conversation:
  def __init__(self, display_name, timestamp, skype_id, mesg):
    self.id = mesg.Id
    self.display_name = display_name
    self.skypereturn = mesg
    self.count = 0
    self.timestamps = [timestamp]
    self.timestamp=timestamp
    self.indicator_name = mesg.Chat.Name
    self.Read = False
    
    
  def add_timestamp(self, timestamp):
    self.timestamps.append(timestamp)
    self.count += 1
    
class FileTransfer:
  def __init__(self, skype_transfer):
  
    # all the notifications that have been sent
    self.notifications = {}
    self.update(skype_transfer)
    
  def update(self, skype_transfer):
    self.Id = skype_transfer.Id
    self.display_name = skype_transfer.FileName
    self.skype_transfer = skype_transfer
    self.type = skype_transfer.Type
    self.status = skype_transfer.Status
    self.partner = skype_transfer.PartnerDisplayName
    self.partner_username = skype_transfer.PartnerHandle

def isSkypeRunning():
    output = commands.getoutput('pgrep -x -l skype -u $USER')
    return 'skype' in output    


player_paused = False
active_player = "unknown"

def controlMusicPlayer():
    global active_player, player_paused
    MediaPlayer = ('amarok', 'audacious', 'bangarang', 'banshee', 'clementine', 'dap', 'exaile', 'gmusicbrowser', 'gogglesmm', 'guayadeque', 'quodlibet', 'rhythmbox')
    
    for item in MediaPlayer:
        if item == 'amarok' or item == 'audacious' or item == 'banshee' or item == 'clementine' or item == 'gmusicbrowser' or item == 'guayadeque' or item == 'rhythmbox':
            if bus.name_has_owner('org.mpris.MediaPlayer2.' + item):
                remote_player = bus.get_object('org.mpris.MediaPlayer2.' + item, '/org/mpris/MediaPlayer2')
                properties_manager = dbus.Interface(remote_player, 'org.freedesktop.DBus.Properties')
                curr_Status = properties_manager.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
                player_action = dbus.Interface(remote_player, 'org.mpris.MediaPlayer2.Player')
                if curr_Status == "Playing":
                    player_action.Pause()
                    active_player = item
                    player_paused = True
                    break
                elif curr_Status == "Paused" and active_player == item and player_paused == True:
                    player_action.Play()
                    break
                    
        elif item == 'bangarang' or item == 'dap' or item == 'gogglesmm':
            if bus.name_has_owner('org.mpris.' + item):
                remote_player = bus.get_object('org.mpris.' + item, '/Player')
                first_Status = remote_player.PositionGet()
                time.sleep(1)
                second_Status = remote_player.PositionGet()
                if first_Status != second_Status:
                    remote_player.Pause()
                    active_player = item
                    player_paused = True
                    break
                elif active_player == item and player_paused == True:
                    remote_player.Pause()
                    break
                    
        elif item == "exaile":
            if bus.name_has_owner('org.exaile.Exaile'):
                remote_player = bus.get_object('org.exaile.Exaile', '/org/exaile/Exaile')
                curr_Status = remote_player.GetState()
                if curr_Status == "playing":
                    remote_player.PlayPause()
                    active_player = item
                    player_paused = True
                    break
                elif curr_Status == "paused" and active_player == item and player_paused == True:
                    remote_player.PlayPause()
                    break
                    
        elif item == "quodlibet":
            if bus.name_has_owner('net.sacredchao.QuodLibet'):
                remote_player = bus.get_object('net.sacredchao.QuodLibet', '/net/sacredchao/QuodLibet')
                curr_Status = remote_player.IsPlaying()
                if curr_Status == 1:
                    remote_player.Pause()
                    active_player = item
                    player_paused = True
                    break
                elif curr_Status == 0 and active_player == item and player_paused == True:
                    remote_player.Play()
                    break
        else:
            player_paused = True


volume_level = "unknown"

def SaveRestore_Volume():
    global volume_level, numid            
    if volume_level == "unknown":
        searchstring = ",iface=MIXER,name='Master Playback Volume'"
        output = commands.getoutput('amixer controls | grep "' + searchstring + '"')
        if output:
            numid= output.replace(searchstring, "")
            searchstring = "  : values="
            output = commands.getoutput('amixer cget ' + numid + ' | grep "' + searchstring + '"')
            if output:
                volume_level = output.replace(searchstring, "")
            else:
                log("Couldn't determine Volume", WARNING)
        else:
            log("Master Mixer not found", WARNING)
    elif not volume_level == "unknown":
        searchstring = "  : values="
        output = commands.getoutput('amixer cset ' + numid + ' ' + volume_level +  ' | grep "' + searchstring + volume_level + '"')
        if output == searchstring + volume_level:
            log("Restored Volume", INFO)
        else:
            log("Volume not restored", WARNING)
                  
                                
class SkypeBehaviour:
  def MessageStatus(self, message, status): 
    self.messageupdatepending = True
    
  def OnlineStatus(self, message, status): 
    self.onlineuserupdatepending = True
    self.onlinepresenceupdatepending = True
    
  def FileTransferStatusChanged(self, message, status): 
    self.filetransferupdatepending = True
    
  def CallStatus(self, call, status):
    global active_player, player_paused, volume_level
    if status == "RINGING":
        if settings.get_control_music_player() and active_player == "unknown" and player_paused == False:
            controlMusicPlayer()
        if settings.get_restore_volume():
            SaveRestore_Volume()
        self.call_ringing = self.call_ringing + 1
        self.calls[call.PartnerHandle] = call
    else:
        self.call_ringing = self.call_ringing - 1
    
    #if status == "INPROGRESS":LOCALHOLD
    
    if (status == "MISSED" or status == "FINISHED" or status == "REFUSED" or status == "CANCELLED") and call.PartnerHandle in self.calls:
        if settings.get_restore_volume():
            SaveRestore_Volume()
            volume_level = "unknown"
        if settings.get_control_music_player():
            controlMusicPlayer()
            active_player = "unknown"
            player_paused = False
        del self.calls[call.PartnerHandle]
        
    unitylauncher.createCallsQuickList(self.calls, self.cb_call_action)
    unitylauncher.redrawQuicklist()  
    
    # wiggle the launcher
    if self.call_ringing > 0 and not self.calls_ringing_started:
        unitylauncher.urgent()
        GObject.timeout_add(1000, self.calls_ringing)
        
    icon = ""
    if settings.get_display_notification_avatars():
        avatar = SkypeAvatar(call.PartnerHandle)
        if avatar.filename:
            icon = avatar.filename
        else:
            icon = "/usr/share/skype-wrapper/icons/skype-wrapper-48.svg"
    
    partner = call.PartnerDisplayName or call.PartnerHandle
    notification = ""
    if status == "RINGING" and (call.Type == "INCOMING_P2P" or call.Type == "INCOMING_PSTN"):
        notification = "* Incoming call";
    if status == "INPROGRESS":
        notification = "* Call started";
    if status == "MISSED":
        notification = "* Missed call";
    if status == "FINISHED":
        notification = "* Call ended";
    if status == "REMOTEHOLD":
        notification = "* Call put on hold";
    if notification:
        helpers.notify(partner, notification, icon, "call://"+call.PartnerHandle, True, True)  
    
  def cb_call_action(self, widget, data = None):
    log("Quicklist showing conversation", INFO)
    id = widget.property_get("id")
    action = widget.property_get("action")
    
    if not id in self.calls:
        return
    
    if action == 'HOLD':
        self.calls[id].Hold()
    if action == 'FINISH':
        self.calls[id].Finish()
    if action == 'ANSWER':
        self.calls[id].Answer()
    if action == 'RESUME':
        self.calls[id].Resume()
    if action == 'VIDEOOUT':
        self.calls[id].StartVideoSend()
    if action == 'VIDEOIN':
        self.calls[id].StartVideoReceive()
    if action == 'ENDVIDEOOUT':
        self.calls[id].StopVideoSend()
    if action == 'ENDVIDEOIN':
        self.calls[id].StopVideoReceive()
    if action == 'MUTE':
        self.skype._SetMute(True)
    if action == 'UNMUTE':
        self.skype._SetMute(False)
                
    unitylauncher.createCallsQuickList(self.calls, self.cb_call_action)
    unitylauncher.redrawQuicklist()  
    
  def calls_ringing(self) :
    self.calls_ringing_started = True
    if self.call_ringing > 0:
        unitylauncher.urgent()
    else :
        self.calls_ringing_started = False
    return self.call_ringing > 0
    
  # initialize skype
  def __init__(self):
    log("Initializing Skype API", INFO)
    self.skype = Skype4Py.Skype(None, Transport='x11')
    self.call_ringing = 0
    self.calls_ringing_started = False
    
    #register events
    self.skype.RegisterEventHandler('MessageStatus', self.MessageStatus)
    self.skype.RegisterEventHandler('OnlineStatus', self.OnlineStatus)
    self.skype.RegisterEventHandler('FileTransferStatusChanged', self.FileTransferStatusChanged)
    self.skype.RegisterEventHandler('CallStatus', self.CallStatus)
    
    self.skype.Timeout = 500
    
    if not isSkypeRunning():
        if settings.get_start_skype_cmd_params():
            log("Starting Skype with extra params", INFO)
            subprocess.Popen(shlex.split("skype "+settings.get_start_skype_cmd_params()))
        else:
            if not helpers.isSkypeWrapperDesktopOnUnityLauncher():
                log("Starting Skype process", INFO)
                subprocess.Popen(shlex.split("skype"))
            else:
                log("Starting Skype", INFO)
                self.skype.Client.Start(Minimized=True)

    log("Waiting for Skype Process", INFO)
    while True:
      if isSkypeRunning():
        break

    log("Attaching skype-wrapper to Skype process", INFO)
    while True:
        try:
            # don't know if its our authorization request but we will wait our turn
            if not helpers.isAuthorizationRequestOpen():
                self.skype.Attach(Wait=True)
                break
            else:
                log("Authorization dialog still open", INFO)
                sys.exit(2)
        except:
            # we tell the parent process that the skype couldn't attached
            log("Failed to attach skype-wrapper to Skype process", WARNING)
            sys.exit(2) 
                        
    log("Attached complete", INFO)
    
    #self.skype.Timeout = 30000
    unitylauncher.launcher.SkypeAgent = self.skype.Client
    unitylauncher.launcher.skype = self.skype
    unitylauncher.launcher.redrawQuicklist()
    self.skype.Client.Minimize()
    self.name_mappings = {}
    self.unread_conversations = {}
    
    # we will store all outdated messages here, anything not here will get net notified
    self.conversations = {}
    
    # store all the users online for notifying if they're on
    self.usersonline = {}
    
    # stor all file transfers
    self.filetransfers = {}
    self.incomingfilecount = 0
    
    # store all calls current
    self.calls = {}
    
    self.cb_show_conversation = None
    self.cb_show_indicator = None
    self.cb_user_status_change = None
    self.cb_log_message = None
    self.cb_read_within_skype = None
    self.cb_log_transfer = None

    self.initSkypeFirstStart()    
        
    self.messageupdatepending = True
    GObject.timeout_add(CB_INTERVALS, self.checkUnreadMessages)
    
    self.onlineuserupdatepending = True
    GObject.timeout_add(CB_INTERVALS, self.checkOnlineUsers)
    
    self.onlinepresenceupdatepending = True
    GObject.timeout_add(CB_INTERVALS, self.checkOnlineStatus)
    
    self.filetransferupdatepending = True
    GObject.timeout_add(CB_INTERVALS, self.checkFileTransfers)
    
  def SetShowConversationCallback(self, func):
    self.cb_show_conversation = func

  def SetShowIndicatorCallback(self, func):
    self.cb_show_indicator = func
    
  def SetUserOnlineStatusChangeCallback(self, func):
    self.cb_user_status_change = func
    
  def SetNewMessageCallback(self, func):
    self.cb_log_message = func
    
  def SetFileTransferCallback(self, func):
    self.cb_log_transfer = func
    
  def SetSkypeReadCallback(self, func):
    self.cb_read_within_skype = func

  def remove_conversation(self, id):
    try :
        display_name = self.unread_conversations[int(id)].display_name
        for _id in self.unread_conversations:
            if display_name == self.unread_conversations[int(_id)].display_name:
                self.unread_conversations[int(_id)].Read = True
        self.unread_conversations[int(id)].Read = True
    except:
        # tried to access a non existent conversation
        pass
   
  def logMessage(self, conversation):
    if not conversation:
        return
    id = conversation.id
    if not id in self.conversations:
        log("Logging Message", INFO)
        self.conversations[id] = conversation
        if self.cb_log_message:
            self.cb_log_message(conversation)
   
  def initSkypeFirstStart(self, count=0) :
    global are_we_offline
    
    self.telepathy_presence = self.getPresence()
    if self.telepathy_presence ==  "OFFLINE" and not settings.get_use_global_status():
        self.skype.ChangeUserStatus(SKYPESTATUS[self.telepathy_presence])
    self.skype_presence = self.skype.CurrentUserStatus
    
    try :
        log("Initializing online status for users", INFO)
        max_wait_time = 0
        while self.skype.CurrentUserStatus == "OFFLINE":
            log("We are offline", INFO)
            time.sleep(0.5)
            max_wait_time = max_wait_time + 1
            if max_wait_time == 20:
                are_we_offline = True
                break
        if self.skype.CurrentUserStatus != "OFFLINE":
            are_we_offline = False
            if not settings.get_notify_on_initializing():
                time.sleep(5)
                if self.skype.Friends:
                    for friend in self.skype.Friends:
                        if not friend.Handle in self.usersonline:
                            if friend.OnlineStatus != "OFFLINE":
                                self.usersonline[friend.Handle] = friend
    except Exception, e:
        if count < 5:
            log("SkypeBehaviour::initSkypeFirstStart() failed, trying again", WARNING)
            self.initSkypeFirstStart ( count+1 )
        else:
            log("Completely failed to initialize skype-wrapper: "+str(e), ERROR)
            sys.exit(2) # perhaps its an issue with the dbus
    
    if self.telepathy_presence and settings.get_use_global_status():
        self.skype.ChangeUserStatus(SKYPESTATUS[self.telepathy_presence])
    self.skype_presence = self.skype.CurrentUserStatus
    
    return AppletRunning
  
  def checkFileTransfers(self) :
    if not self.filetransferupdatepending:
        return AppletRunning
    self.filetransferupdatepending = False
    try : 
        log("Checking file transfers", INFO)
        for transfer in self.skype.ActiveFileTransfers:
            if not transfer.Id in self.filetransfers:
                self.filetransfers[transfer.Id] = FileTransfer(transfer)
        
        for transfer in self.skype.FileTransfers:
            if transfer.Id in self.filetransfers:
                self.filetransfers[transfer.Id].update(transfer)
             
        oldincoming = self.incomingfilecount
        self.incomingfilecount = 0
        self.filetransfer = {
            "total" : -1,
            "current" : 0    
        }
        # should we send out notifications
        for k in self.filetransfers:
            v = self.filetransfers[k]
            if str(v.type) == "INCOMING":
                if "NEW" in str(v.status):
                    self.incomingfilecount = self.incomingfilecount + 1
                    if helpers.haveUnity():
                        unitylauncher.urgent(True)
                else:
                    if helpers.haveUnity():
                        unitylauncher.urgent(False)
                
                if settings.get_show_incoming_filetransfer_progress():
                    if "TRANSFERRING" in str(v.status) or "PAUSED" in str(v.status):
                        self.filetransfer['total'] = self.filetransfer['total'] + v.skype_transfer.FileSize
                        self.filetransfer['current'] = self.filetransfer['current'] + v.skype_transfer.BytesTransferred
                        self.incomingfilecount = self.incomingfilecount + 1
                        self.filetransferupdatepending = True
                
                    
                if not str(v.status) in v.notifications:
                    if "NEW" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " wants to send you a file")
                    if "TRANSFERRING" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " is busy sending you a file")
                        self.filetransferupdatepending = True
                    if "CANCELLED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* file transfer with " + v.partner+ " has been cancelled")
                    if "COMPLETED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " finished sending you a file")
                        if helpers.haveUnity():
                            unitylauncher.urgent(True)
                    if "FAILED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " failed to send you a file")
                else:
                    if "COMPLETED" in v.status:
                        if helpers.haveUnity():
                            unitylauncher.urgent(False)
                        
            if str(v.type) == "OUTGOING":                
                if settings.get_show_outgoing_filetransfer_progress():
                    if "TRANSFERRING" in str(v.status) or "PAUSED" in str(v.status) or "REMOTELY_PAUSED" in str(v.status):
                        self.filetransfer['total'] = self.filetransfer['total'] + v.skype_transfer.FileSize
                        self.filetransfer['current'] = self.filetransfer['current'] + v.skype_transfer.BytesTransferred
                        self.incomingfilecount = self.incomingfilecount + 1
                        self.filetransferupdatepending = True
                        
                if not str(v.status) in v.notifications:
                    if "TRANSFERRING" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " is busy receiving your file")
                        self.filetransferupdatepending = True
                    if "CANCELLED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* file transfer with " + v.partner+ " has been cancelled")
                    if "COMPLETED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " has received your file")                        
                    if "FAILED" in v.status:
                        self.filetransfers[k].notifications[str(v.status)] = str(v.status)
                        if self.cb_log_transfer:
                            self.cb_log_transfer(v, "* " + v.partner+ " failed to receive your file")
               
        if self.filetransfer['total'] > -1:
            currentprogress = float(self.filetransfer['current']) / float(self.filetransfer['total'])
            if helpers.haveUnity():
                unitylauncher.progress(currentprogress)
        else:
            if helpers.haveUnity():
                unitylauncher.progress(-1)
            
        if oldincoming != self.incomingfilecount and self.cb_read_within_skype:
            self.cb_read_within_skype()  
        #limitcpu()
    except Exception, e:
        log("Checking file transfers failed ("+str(e)+")", WARNING)
        raise
    return AppletRunning
   
  def checkOnlineUsers(self) :
    global are_we_offline
    if not self.onlineuserupdatepending:
        return AppletRunning
    self.onlineuserupdatepending = False
    try :
        log("Checking online status changing users", INFO)
            
        #check who is now online
        if self.skype.Friends:
            for friend in self.skype.Friends:
                if not friend.Handle in self.usersonline:
                    if friend.OnlineStatus != "OFFLINE":
                        self.usersonline[friend.Handle] = friend
                        if not helpers.isUserBlacklisted(friend.Handle) and self.cb_user_status_change and not friend.IsSkypeOutContact and are_we_offline == False:
                            self.cb_user_status_change(friend, "is online")
            are_we_offline = False
        
        #check who is now offline
        if self.skype.Friends:
            for friend in self.skype.Friends:
                if friend.Handle in self.usersonline:
                    if friend.OnlineStatus == "OFFLINE":
                        if not helpers.isUserBlacklisted(friend.Handle) and self.cb_user_status_change and not friend.IsSkypeOutContact and self.skype.CurrentUserStatus != "OFFLINE":
	                        self.cb_user_status_change(friend, "went offline")
                        del self.usersonline[friend.Handle]  
        
        limitcpu()
    except Exception, e:
        log("Checking online status changing users failed ("+str(e)+")", WARNING)
    return AppletRunning
  
  def checkUnreadMessages(self):
    if not self.messageupdatepending:
        return AppletRunning
    self.messageupdatepending = False
    
    try :
        log("Checking unread messages", INFO)
        missedmessages = []
        if self.skype.MissedMessages:
            for mesg in self.skype.MissedMessages:
                missedmessages.append(mesg)
                
        unread = self.unread_conversations
        self.unread_conversations = {}
        logged = False
        if missedmessages and self.cb_show_indicator:
            for mesg in reversed(missedmessages):
                try:
                    id = mesg.Id
                    if self.skype.Friends:
                        for friend in self.skype.Friends:
                            if mesg.Chat.DialogPartner == friend.Handle:
                                display_name = friend.DisplayName or friend.FullName or friend.Handle
                                break                    
                except:
                    log("Couldn't get missed message Chat object", ERROR)
                    continue
                if not id in self.unread_conversations:
                    conversation = Conversation(display_name, mesg.Timestamp, mesg.Sender.Handle, mesg)
                    self.name_mappings[id] = mesg.Sender.Handle
                    self.unread_conversations[id] = conversation
                else:
                    self.unread_conversations[id].add_timestamp(mesg.Timestamp)
                
                if helpers.isUserBlacklisted(mesg.Sender.Handle):
                    self.unread_conversations[id].Read = True
                    
                if not self.unread_conversations[id].Read:
                    self.logMessage(self.unread_conversations[id])
                    self.cb_show_indicator(self.unread_conversations[id]) 
        
        if len(unread) != len(self.unread_conversations):
            CPUPRIORITY = 1
            
            if self.cb_read_within_skype:
                self.cb_read_within_skype()
                
            if helpers.haveUnity():
                unitylauncher.urgent(True)
                unitylauncher.urgent(False)
            
        #limitcpu()
        CPUPRIORITY = 0
    except Exception, e:
        log("Checking unread messages failed: "+str(e), WARNING)
        
    return AppletRunning
  
  def checkOnlineStatus(self):
    global are_we_offline
    try :
        log("Checking online presence", INFO)
        
        if settings.get_use_global_status():
            new_telepathy_presence = self.getPresence()
            if new_telepathy_presence and new_telepathy_presence != self.telepathy_presence:
                self.telepathy_presence = new_telepathy_presence
                self.skype.ChangeUserStatus(SKYPESTATUS[self.telepathy_presence])
                self.skype_presence = SKYPESTATUS[self.telepathy_presence]
                return AppletRunning
            
        if not self.onlinepresenceupdatepending:
            return AppletRunning
            
        self.onlinepresenceupdatepending = False
        
        new_skype_presence = self.skype.CurrentUserStatus
        if new_skype_presence == "OFFLINE":
            are_we_offline = True
        if self.skype_presence != new_skype_presence:
            self.skype_presence = new_skype_presence
            if settings.get_use_global_status():
                new_telepathy_presence = SKYPETOTELEPATHY[self.skype_presence]
                self.setPresence(new_telepathy_presence)
                self.telepathy_presence = new_telepathy_presence
            
        limitcpu()
    except Exception, e:
        log("Checking online presence failed "+str(e), WARNING)
        raise
    return AppletRunning

  def show_chat_windows(self, id):
    try :
        self.unread_conversations[id].skypereturn.Chat.OpenWindow()
    except Exception, e:
        log("Couldn't open chat window ("+str(e)+")", WARNING)
    
  def setPresence(self, presence):
    if not helpers.isInstalled('telepathy-mission-control-5') or 'mission-control' not in commands.getoutput('pgrep -x -l mission-control -u $USER'):
        return
        
    account_manager = bus.get_object('org.freedesktop.Telepathy.AccountManager',
                         '/org/freedesktop/Telepathy/AccountManager')
    accounts = account_manager.Get(
        'org.freedesktop.Telepathy.AccountManager', 'ValidAccounts')

    for account_path in accounts:
        if str(account_path) == '/org/freedesktop/Telepathy/Account/ring/tel/ring':
            continue
        account = bus.get_object('org.freedesktop.Telepathy.AccountManager', account_path)
        #account.Set('org.freedesktop.Telepathy.Account', 'Enabled', dbus.Struct((dbus.Boolean(True)), signature='b'), dbus_interface='org.freedesktop.DBus.Properties')
        enabled = account.Get('org.freedesktop.Telepathy.Account', 'Enabled')
        if not enabled:
            continue
        presence_text = ""
        if presence in STATUSLIST:
            presence_text = STATUSLIST[presence]
        account.Set('org.freedesktop.Telepathy.Account', 'RequestedPresence', \
            dbus.Struct((dbus.UInt32(presence), presence_text, ''), signature='uss'),
            dbus_interface='org.freedesktop.DBus.Properties')
  
  def getPresence(self) :
    if not helpers.isInstalled('telepathy-mission-control-5') or 'mission-control' not in commands.getoutput('pgrep -x -l mission-control -u $USER'):
        return None
        
    account_manager = bus.get_object('org.freedesktop.Telepathy.AccountManager',
                         '/org/freedesktop/Telepathy/AccountManager')
    accounts = account_manager.Get(
        'org.freedesktop.Telepathy.AccountManager', 'ValidAccounts')

    for account_path in accounts:
        if str(account_path) == '/org/freedesktop/Telepathy/Account/ring/tel/ring':
            continue
        account = bus.get_object('org.freedesktop.Telepathy.AccountManager', account_path)
        enabled = account.Get('org.freedesktop.Telepathy.Account', 'Enabled')
        if not enabled:
            continue
        i,s,t = account.Get('org.freedesktop.Telepathy.Account', 'RequestedPresence')
        return i
    return None

def runCheck():
    try :
        log("Check if Skype instance is running", INFO)
        #print self.skype.Client.IsRunning
        #calling self.skype.Client.IsRunning crashes. wtf. begin hack:
        output = commands.getoutput('pgrep -x -l skype -u $USER')
        
        if 'skype' not in output:
            log("Skype instance has terminated, exiting", WARNING)
            gtk.main_quit()
        if 'defunct' in output:
            log("Skype instance is now defunct, exiting badly", ERROR)
            gtk.main_quit()
        limitcpu()
    except Exception, e:
        log("Checking if skype is running failed: "+str(e), WARNING)
        
    return AppletRunning

if __name__ == "__main__":
  os.chdir('/usr/share/skype-wrapper')
  
  skype = SkypeBehaviour();
  server = NotificationServer()
  GObject.timeout_add(CB_INTERVALS, runCheck)
  
  skype.SetShowConversationCallback(server.show_conversation)
  skype.SetShowIndicatorCallback(server.show_indicator)
  skype.SetUserOnlineStatusChangeCallback(server.user_online_status)
  skype.SetNewMessageCallback(server.new_message)
  skype.SetFileTransferCallback(server.file_transfer_event)
  skype.SetSkypeReadCallback(server.reset_indicators)
  
  server.connect(skype)
  
  #workaround_show_skype()

  # why is this needed?
  #server.activate_timeout_check()

  # check for newly unread messages..
  #skype.check_timeout(server)
  gtk.main()
  AppletRunning = False

########NEW FILE########
__FILENAME__ = postinst
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

import os

messagingmenu_path = os.getenv("HOME")+"/.config/indicators/messages/applications/skype-wrapper"
f = open(messagingmenu_path, mode="w")
f.write("/usr/share/applications/skype-wrapper.desktop")
f.close()
########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

from gi.repository import Gio

BASE_KEY = "apps.skype-wrapper"
settings = Gio.Settings.new(BASE_KEY)

def get_notify_on_useronlinestatuschange():
    return settings.get_boolean("notify-on-useronlinestatuschange")
        
def get_notify_on_messagerecieve():
    return settings.get_boolean("notify-on-messagerecieve")
        
def get_notify_on_initializing():
    return settings.get_boolean("notify-on-initializing")
    
def get_display_indicator_avatars():
    return settings.get_boolean("display-indicator-avatars")
    
def get_display_notification_avatars():
    return settings.get_boolean("display-notification-avatars")
    
def get_notify_on_incoming_filetransfer():
    return settings.get_boolean("notify-on-incoming-filetransfer")
    
def get_notify_on_outgoing_filetransfer():
    return settings.get_boolean("notify-on-outgoing-filetransfer")

def get_show_outgoing_filetransfer_progress():
    return settings.get_boolean("show-outgoing-file-progress")
    
def get_show_incoming_filetransfer_progress():
    return settings.get_boolean("show-incoming-file-progress")

def get_start_skype_cmd_params():
    return settings.get_string("start-skype-cmd-params")
    
def get_list_of_silence():
    return settings.get_string("list-of-silence")
    
def get_debug_log():
    return settings.get_boolean("debug-log")
    
def get_debug_level():
    return settings.get_int("debug-level")
    
def get_cpu_limit():
    return float(settings.get_string("cpu-percentage-limit"))
    
def get_use_global_status():
    return settings.get_boolean("use-global-status")
    
def get_control_music_player():
    return settings.get_boolean("control-music-player")
    
def get_restore_volume():
    return settings.get_boolean("restore-volume")
    
    

########NEW FILE########
__FILENAME__ = shared
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

import sys

def set_proc_name(newname):
    from ctypes import cdll, byref, create_string_buffer
    libc = cdll.LoadLibrary('libc.so.6')
    buff = create_string_buffer(len(newname)+1)
    buff.value = newname
    libc.prctl(15, byref(buff), 0, 0, 0)

def get_proc_name():
    from ctypes import cdll, byref, create_string_buffer
    libc = cdll.LoadLibrary('libc.so.6')
    buff = create_string_buffer(128)
    # 16 == PR_GET_NAME from <linux/prctl.h>
    libc.prctl(16, byref(buff), 0, 0, 0)
    return buff.value
########NEW FILE########
__FILENAME__ = skype-wrapper
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

import subprocess
import time
import os
import commands
import dbus
import sys
	
def skypeRunning():
    USER = commands.getoutput('whoami')
    output = commands.getoutput('pgrep -x -l skype -u $USER')
    return 'skype' in output
	
skype_was_running = False
	
def start_skype():
    global skype_was_running
    
    # some one quit skype while it was still unattached
    if skype_was_running and not skypeRunning():
        return
    
    skype_was_running = skypeRunning()
    
    start = time.time()
    ret = subprocess.call(['python','indicator-applet-skype.py'])
    if ret == 2:
        start_skype()
        return
    end = time.time()
    print "Applet closed"
    if end - start < 5:
        print "API crash detected"
        print "Restarting skype-wrapper"
        start_skype()
    return


if __name__ == "__main__":
    os.chdir('/usr/share/skype-wrapper')
	
    USER = commands.getoutput('whoami')
    output = commands.getoutput('pgrep -x -l indicator-skype -u $USER')
    
    # until the dbus is working just disallow skype-wrapper
    if 'indicator-skype' in output:
        try:
	        # Try and set skype window to normal
            remote_bus = dbus.SessionBus()
            out_connection = remote_bus.get_object('com.Skype.API', '/com/Skype')
            out_connection.Invoke('NAME Skype4Py')
            out_connection.Invoke('PROTOCOL 5')
            #out_connection.Invoke('SET WINDOWSTATE MAXIMIZED')
            out_connection.Invoke('SET WINDOWSTATE NORMAL')
            out_connection.Invoke('FOCUS')
            sys.exit(0)
        except:
            sys.exit(0)

    print "Starting skype-wrapper"
    start_skype()

########NEW FILE########
__FILENAME__ = uisettings
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet
#
# Copyright 2012 Shannon Black
#
# Authors:
#    Christian Rupp <christian@r-k-r.de>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public
# License version 3 and version 2.1 along with this program.  If not, see
# <http://www.gnu.org/licenses/>
#

from gi.repository import Gtk, Gio
import settings
import subprocess

BASE_KEY = "apps.skype-wrapper"
setting = Gio.Settings.new(BASE_KEY)

class DialogAdvanced(Gtk.Dialog):
				
		def __init__(self, parent):		
				Gtk.Dialog.__init__(self, "Remove sni-qt", parent, 0,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))

        		self.set_default_size(300, 100)

        		label = Gtk.Label("This will remove sni-qt. The Skype-Icon will not be shown in the panel any longer. This may also affects other applications. To revert the change reinstall sni-qt in the software-center")
				label.set_line_wrap(True)
        		box = self.get_content_area()
       			box.add(label)
       			self.show_all()

class uisettings(Gtk.Window):
        def switch(self, table, label, option):
                self.row += 1
                gtk_label = Gtk.Label ( label )
                gtk_label.set_alignment(0.0,0.5)

                table.attach ( gtk_label, 0, 3, self.row, self.row+1, xpadding=10, ypadding = 2 )
                gtk_switch = Gtk.Switch()
                table.attach ( gtk_switch, 3, 4, self.row, self.row+1, xpadding=10, ypadding = 2 )
                setting.bind( option, gtk_switch, "active", Gio.SettingsBindFlags.DEFAULT )

        def __init__(self):
                Gtk.Window.__init__(self, title="Skype Wrapper Options")
                table = Gtk.Table(2, 4, True)
                table.set_row_spacings(5)
                table.set_col_spacings(1)
                self.row = -1
        		self.add(table)
        		
        		
                self.switch( table, "Notify when someone goes on or offline", "notify-on-useronlinestatuschange")
                self.switch( table, "Notify when you recieve a message","notify-on-messagerecieve")
                self.switch( table, "Notify about all online contacts during startup", "notify-on-initializing")
                self.switch( table, "Display avatars next to indicator message", "display-indicator-avatars")
                self.switch( table, "Display avatars in the notifications", "display-notification-avatars")
                self.switch( table, "Notify on incoming File Transfer", "notify-on-incoming-filetransfer" )
                self.switch( table, "Notify on outgoing File Transfer", "notify-on-outgoing-filetransfer" )
                self.switch( table, "Show outgoing File Transfer progress in the Launcher", "show-outgoing-file-progress" )
                self.switch( table, "Show incoming File Transfer progress in the Launcher", "show-incoming-file-progress" )
                self.switch( table, "Use the global online status of the system", "use-global-status" )
                self.switch( table, "Toggle music playback before and after a call", "control-music-player" )
                self.switch( table, "Restore the volume to the level prior the call", "restore-volume" )

                gtk_btn_adv = Gtk.Button("Remove the panel icon")
                gtk_btn = Gtk.Button("Close")
                gtk_btn.connect("clicked", Gtk.main_quit)
                gtk_btn_adv.connect("clicked", self.on_advanced_clicked)

                self.row += 1
                table.attach ( gtk_btn, 3, 4, self.row, self.row+1,xpadding=10, ypadding = 2 )
                table.attach ( gtk_btn_adv, 0, 2, self.row, self.row+1,xpadding=10, ypadding = 2 )



		def on_advanced_clicked(self, widget):
        		dialog = DialogAdvanced(self)
        		response = dialog.run()

        		if response == Gtk.ResponseType.OK:
           			subprocess.call(['gksudo','python /usr/share/skype-wrapper/uninstallsni.py'])

           			           			
        		elif response == Gtk.ResponseType.CANCEL:
            		print "The Cancel button was clicked"

        		dialog.destroy()


win = uisettings()
win.set_border_width(10)
win.connect("delete-event", Gtk.main_quit)
win.connect("destroy", Gtk.main_quit)
win.show_all()

Gtk.main()



########NEW FILE########
__FILENAME__ = uninstallsni
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet
#
# Copyright 2012 Shannon Black
#
# Authors:
#    Christian Rupp <christian@r-k-r.de>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public
# License version 3 and version 2.1 along with this program.  If not, see
# <http://www.gnu.org/licenses/>
#

import apt


cache = apt.Cache()
pkg = cache['sni-qt:i386']
pkg.mark_delete()
cache.commit()



########NEW FILE########
__FILENAME__ = unitylauncher
#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet 
#
# Copyright 2011 Shannon Black
#
# Authors:
#    Shannon A Black <shannon@netforge.co.za>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

from gi.repository import Unity, Gio, Dbusmenu
import time
import helpers
    
import atexit

class SkypeWrapperLauncher:
  # initialize skype
  def __init__(self):
    self.launcher_desktop = None
    self.launcher_wrapper = Unity.LauncherEntry.get_for_desktop_id ("skype-wrapper.desktop")
    self.launcher_main = Unity.LauncherEntry.get_for_desktop_id ("skype.desktop")
    self.launcher = None
    self.reset_launcher()
    self.unread_quicklist = {}
    self.calls_quicklist = {}
    self.quicklist = self.launcher.get_property("quicklist")
    self.clear(True)
    self.SkypeAgent = None
  
  def __del__(self):    
    self.clear()
    
  def reset_launcher(self):
    old = self.launcher_desktop
    is_skype_wrapper = helpers.isSkypeWrapperDesktopOnUnityLauncher()
    
    if(is_skype_wrapper):
        self.launcher_desktop = "skype-wrapper.desktop"
        self.launcher = self.launcher_wrapper
    else:
        self.launcher_desktop = "skype.desktop"
        self.launcher = self.launcher_main
    if not old or old == self.launcher_desktop:
        return
    
    # this crashes unity
    if(is_skype_wrapper):
        old = self.launcher_main
    else:
        old = self.launcher_wrapper
        
    self.launcher.set_property("quicklist", self.quicklist)
    self.launcher.set_property("count", self.mcount)
    self.launcher.set_property("count_visible", self.mcount_visible)
    self.launcher.set_property("progress", self.mprogress)
    self.launcher.set_property("progress_visible", self.mprogress_visible)
    self.launcher.set_property("urgent", self.murgent)
         
    # removing quicklist causes a unity to crash
    #quicklist = Dbusmenu.Menuitem.new ()
    #old.set_property("quicklist", quicklist)
    old.set_property("count_visible", False)
    old.set_property("progress_visible", False)
    old.set_property("urgent", False)
    
  def clear(self, New = False):
    if self.quicklist:
        for child in self.quicklist.get_children():
            self.quicklist.child_delete(child)
    else:
        if New and not self.quicklist:
            self.quicklist = Dbusmenu.Menuitem.new ()
            self.launcher.set_property("quicklist", self.quicklist)
    
  def count(self, count) :
    self.reset_launcher()
    self.mcount = count
    if count:
        self.launcher.set_property("count", count)
        self.launcher.set_property("count_visible", True)
        self.mcount_visible = True
    else :
        self.launcher.set_property("count_visible", False)
        self.mcount_visible = False
  
  def progress(self, progress):
    self.reset_launcher()
    self.mprogress = progress
    if progress >= 0:
        self.launcher.set_property("progress", progress)
        self.launcher.set_property("progress_visible", True)
        self.mprogress_visible = True
    else :
        self.launcher.set_property("progress_visible", False)
        self.mprogress_visible = False
        
  def urgent(self, urgent = None) :
    self.reset_launcher()
    self.murgent = urgent
    if urgent == None:
        self.launcher.set_property("urgent", True)
        self.launcher.set_property("urgent", False)
    else:
        self.launcher.set_property("urgent", self.murgent)

  def createUnreadMessageQuickList(self, unread_conversations, cb_unread_message_click):
    global unread_quicklist
    self.reset_launcher()
    self.unread_quicklist = {}
    for _id in unread_conversations:
        conversation = unread_conversations[int(_id)]
        if conversation.indicator_name in unread_quicklist or conversation.Read:
            continue
            
        self.unread_quicklist[conversation.indicator_name] = Dbusmenu.Menuitem.new ()
        self.unread_quicklist[conversation.indicator_name].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str(conversation.display_name))
        self.unread_quicklist[conversation.indicator_name].property_set ("id", str(conversation.id))
        self.unread_quicklist[conversation.indicator_name].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        if cb_unread_message_click:
            self.unread_quicklist[conversation.indicator_name].connect ("item-activated", cb_unread_message_click)
            
  def createCallsQuickList(self, calls, cb_call_action):
    self.reset_launcher()
    self.calls_quicklist = {}
    priority = 0
    for _id in calls:
        call = calls[_id]
            
        if call.Status == "MISSED" or call.Status == "FINISHED":
            continue
            
        partner = call.PartnerDisplayName or call.PartnerHandle
            
        if call.Status == 'RINGING':
            priority = priority + 1
            self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Answer Call: "+partner))
            self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle].property_set ("action", "ANSWER")
            self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"answer://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
            priority = priority + 1
            self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Reject Call: "+partner))
            self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"reject://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
        if call.Status == 'LOCALHOLD' and self.skype.Mute == False:
            priority = priority + 1
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Mute Call: "+partner))
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set ("action", "MUTE")
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            
            if cb_call_action:
                self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].connect ("item-activated", cb_call_action)    
        
            priority = priority + 1
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Resume Call: "+partner))
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set ("action", "RESUME")
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
            priority = priority + 1
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("End Call: "+partner))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
 
        if call.Status == 'LOCALHOLD' and self.skype.Mute == True:
            priority = priority + 1
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Unmute Call: "+partner))
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set ("action", "UNMUTE")
            self.calls_quicklist[str(priority)+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            
            if cb_call_action:
                self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].connect ("item-activated", cb_call_action)                   
        
            priority = priority + 1
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Resume Call: "+partner))
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set ("action", "RESUME")
            self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"resume://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
            priority = priority + 1
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("End Call: "+partner))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                 
        if call.Status == 'REMOTEHOLD' or call.Status == 'ROUTING':                 
            priority = priority + 1
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("End Call: "+partner))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
        if call.Status == 'INPROGRESS' and self.skype.Mute == False:
            priority = priority + 1
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Mute Call: "+partner))
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set ("action", "MUTE")
            self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            
            if cb_call_action:
                self.calls_quicklist[str(priority)+"mute://"+call.PartnerHandle].connect ("item-activated", cb_call_action)         
                    
            priority = priority + 1
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Hold Call: "+partner))
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set ("action", "HOLD")
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
            priority = priority + 1
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("End Call: "+partner))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
        if call.Status == 'INPROGRESS'  and self.skype.Mute == True:
            priority = priority + 1
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Unmute Call: "+partner))
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set ("action", "UNMUTE")
            self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            
            if cb_call_action:
                self.calls_quicklist[str(priority)+"unmute://"+call.PartnerHandle].connect ("item-activated", cb_call_action)           
            
            priority = priority + 1
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("Hold Call: "+partner))
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set ("action", "HOLD")
            self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"hold://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
                
            priority = priority + 1
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle] = Dbusmenu.Menuitem.new ()
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set (Dbusmenu.MENUITEM_PROP_LABEL, str("End Call: "+partner))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("id", str(call.PartnerHandle))
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set ("action", "FINISH")
            self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
            if cb_call_action:
                self.calls_quicklist[str(priority)+"end://"+call.PartnerHandle].connect ("item-activated", cb_call_action)
            
  def redrawQuicklist(self) :
    self.reset_launcher()
    self.clear(True)        
    
    if len(self.calls_quicklist):
        for cql in sorted(self.calls_quicklist.iterkeys()):
            self.quicklist.child_append (self.calls_quicklist[cql])
    
    if len(self.unread_quicklist):
        for cql in self.unread_quicklist:
            self.quicklist.child_append (self.unread_quicklist[cql])
            
    if self.SkypeAgent:
        #self.toggle_skype = Dbusmenu.Menuitem.new ()
        #self.toggle_skype.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "Hide / Show Skype")
        #self.toggle_skype.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        #self.toggle_skype.connect ("item-activated", self.cb_toggle_window_state)
        #self.quicklist.child_append (self.toggle_skype)
        
        self.quit_skype = Dbusmenu.Menuitem.new ()
        self.quit_skype.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "Add Contact")
        self.quit_skype.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        self.quit_skype.connect ("item-activated", self.cb_add_contact)
        self.quicklist.child_append (self.quit_skype)
        
        # python skype crashes with these
        
        #self.quit_skype = Dbusmenu.Menuitem.new ()
        #self.quit_skype.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "Options")
        #self.quit_skype.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        #self.quit_skype.connect ("item-activated", self.cb_options)
        #self.quicklist.child_append (self.quit_skype)
        
        #self.quit_skype = Dbusmenu.Menuitem.new ()
        #self.quit_skype.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "Profile")
        #self.quit_skype.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        #self.quit_skype.connect ("item-activated", self.cb_profile)
        #self.quicklist.child_append (self.quit_skype)
    
        self.quit_skype = Dbusmenu.Menuitem.new ()
        self.quit_skype.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "Quit Skype")
        self.quit_skype.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        self.quit_skype.connect ("item-activated", self.cb_quit_skype)
        self.quicklist.child_append (self.quit_skype)
  
  def cb_add_contact(self, widget, data = None):
    self.SkypeAgent.OpenAddContactDialog()
    
  def cb_options(self, widget, data = None):
    self.SkypeAgent.OpenOptionsDialog()
    
  def cb_profile(self, widget, data = None):
    self.SkypeAgent.OpenProfileDialog()
  
  def cb_quit_skype(self, widget, data = None):
    self.SkypeAgent.Shutdown()
    self.redrawQuicklist()
  
  def cb_toggle_window_state(self, widget, data = None):
    if self.SkypeAgent.WindowState == "HIDDEN":
        self.SkypeAgent.Focus
    else:
        self.SkypeAgent.WindowState = "HIDDEN"
    self.redrawQuicklist()
            
launcher = SkypeWrapperLauncher()

def count(count) :
    global launcher
    launcher.count(count)

def progress(progress):
    global launcher
    launcher.progress(progress)

def urgent(urgent = None) :
    global launcher
    launcher.urgent(urgent)
    
unread_quicklist = {}

def createUnreadMessageQuickList(unread_conversations, cb_unread_message_click):
    global launcher
    launcher.createUnreadMessageQuickList(unread_conversations, cb_unread_message_click)
    
def createCallsQuickList(calls, cb_call_action):
    global launcher
    launcher.createCallsQuickList(calls, cb_call_action)
    
def createCallQuicklist(call) :
    #
    return

def redrawQuicklist() :
    global launcher
    launcher.redrawQuicklist()
########NEW FILE########
