__FILENAME__ = gweather
#!/usr/bin/python

import sys
import urllib
from string import maketrans
#from xml.sax import make_parser, handler
from xml.sax import handler, parseString
class ElementProcesser(handler.ContentHandler):
    
    def startElement(self, name, attrs):
        
        if name == "city":
            print "<separator label='" + attrs["data"] + "' />"
        elif name == "current_conditions":
            print "<separator label='Current condidtions' />"
        elif name == "condition":
            print "<item label='Weather: " + attrs["data"] + "' />"
        elif name == "humidity":
            print "<item label='" + attrs["data"] + "' />"
        elif name == "wind_condition":
            print "<item label='" + attrs["data"] + "' />"
        elif name == "day_of_week":
            print "<separator label='" + self.getDayOfWeek(attrs["data"]) + "' />"
            
        #Celsius
        elif name == "temp_c":
            print "<item label='Temperature " + attrs["data"] + " C' />"
        elif name == "low":
            print "<item label='Minimun " + attrs["data"] + " C' />"
        elif name == "high":
            print "<item label='Maximun " + attrs["data"] + " C' />"
        
        #Fahrenheit
        # elif name == "temp_f":
        #     print "<item label='Temperature " + attrs["data"] + " F' />"
        # elif name == "low":
        #     print "<item label='Minimun " + attrs["data"] + " F' />"
        # elif name == "high":
        #     print "<item label='Maximun " + attrs["data"] + " F' />"
        
        
    def endElement(self, name):
        
        if name == "current_conditions":
            print "<separator label='Forecast' />"
        
    
    def startDocument(self):
        print '<openbox_pipe_menu>'
    
    def endDocument(self):
        print '</openbox_pipe_menu>'
    
    def getDayOfWeek(self,day):
        
        #English
        if day == "Mon":
            return "Monday"
        elif day == "Tue":
            return "Tuesday"
        elif day == "Wed":
            return "Wednesday"
        elif day == "Thu":
            return "Thursday"
        elif day == "Sat":
            return "Saturday"
        elif day == "Sun":
            return "Sunday"
        
        else:
            return day

# You should use your local version of google to have the messages in your language and metric system
f = urllib.urlopen("http://www.google.com/ig/api?weather="+sys.argv[1])
xml = f.read()
f.close()

#Avoid problems with non english characters
trans=maketrans("\xe1\xe9\xed\xf3\xfa","aeiou")
xml = xml.translate(trans)

#parser.parse("http://www.google.es/ig/api?weather="+sys.argv[1])
parseString(xml,ElementProcesser())

########NEW FILE########
__FILENAME__ = ob-mpd
#!/usr/bin/env python
#
# Author: John Eikenberry <jae@zhar.net>
# License: GPL 2.0
#
# Changelog
# 2007-09-09 - Fixed compatibility issue with mpdclient2 version 1.0
#              vs. 11.1 which I have (debian).
# 2007-11-18 - Added playlist load/clear support.
#
#
# This script depends on py-libmpdclient2 which you can get from 
# http://incise.org/index.cgi/py-libmpdclient2
#
# Usage:
# Put an entry in ~/.config/openbox/menu.xml:
# <menu id="mpd" label="MPD" execute="~/.config/openbox/scripts/ob-mpd.py" />
#
# Add the following wherever you'd like it to be displayed in your menu:
# <menu id="mpd" />
#
#
# Originally Based on code by John McKnight <jmcknight@gmail.com>
#
## Main changes from original version:
# 
#              Changed to use libmpdclient2.
#              Refactored/Cleaned up the code.
#              Added random/repeat toggle indicators. 
#              Changed Pause/Play so only the appropriate one would show up.
#              Added actions to start and stop mpd daemon.
#              Added exception to deal with no id3 tags.
#              Added volume controls.
#              Added output setting controls.
#              Determine location of script dynamically instead of hardcoded

import os, sys, socket
import mpdclient2

argv = sys.argv

# The default port for MPD is 6600.  If for some reason you have MPD
# running on a different port, change this setting.
mpdPort = 6600

# determin path to this file
my_path = sys.modules[__name__].__file__
# if this fails for some reason, just set it manually.
# Eg.
# my_path = "~/.config/openbox/scripts/ob-mpd.py"


separator = "<separator />"
info = """<item label="%s" />"""
action = ("""<item label="%s"><action name="Execute">"""
        """<execute>MY_PATH %s</execute>"""
        """</action></item>""").replace("MY_PATH",my_path)
menu = """<menu id="%s" label="%s">"""
menu_end = """</menu>"""


try:
    connect = mpdclient2.connect(port=mpdPort)
except socket.error:
    # If MPD is not running.
    if len(argv) > 1 and argv[1] == 'start':
            os.execl('/usr/bin/mpd','$HOME/.mpdconf')
    else:
        print ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
              "<openbox_pipe_menu>")
        print action % ('MPD is not running  [start]','start')
        print "</openbox_pipe_menu>"

else: # part of connect try block
        
    song = connect.currentsong()
    stats = connect.stats()
    status = connect.status()

    if status['state'] == "stop":
        display_state = "Not playing"
    else:
        try:
            display_state = "%s - %s" % (song.artist, song.title)
        except (AttributeError, KeyError): # no id3 tags
            display_state = os.path.basename(song.file)
        if status['state'] == "pause":
            display_state += " (paused)"
    display_state = display_state.replace('"',"'")
    display_state = display_state.replace('&','&amp;')

    if len(argv) > 1:

        state = status.state
        def play():
            if state == "stop" or state == "pause":
                connect.play()

        def pause():
            if state == "play":
                connect.pause(1)
            elif state == "pause":
                connect.play()

        def stop():
            if state == "play" or state == "pause":
                connect.stop()

        def prev():
            if state == "play":
                connect.previous()

        def next():
            if state == "play":
                connect.next()

        random_state = int(status.random)
        def random():
            if random_state:
                connect.random(0)
            else:
                connect.random(1)

        repeat_state = int(status.repeat)
        def repeat():
            if repeat_state:
                connect.repeat(0)
            else:
                connect.repeat(1)

        consume_state = int(status.consume)
        def consume():
            if consume_state:
                connect.consume(0)
            else:
                connect.consume(1)

        def kill():
            try:
                connect.kill()
            except EOFError:
                pass

        def update():
            connect.update()
        
        def volume(setto):
            relative = (setto[0] in ['+','-'])
            setto = int(setto)
            if relative:
                newvol = int(status.volume) + setto
                newvol = newvol <= 100 or 100
                newvol = newvol >= 0 or 0
            connect.setvol(setto)

        def client():
            os.execlp('x-terminal-emulator','-e','ncmpc')

        def enable(output_id):
            connect.enableoutput(int(output_id))

        def disable(output_id):
            connect.disableoutput(int(output_id))

        def load(list_name):
            connect.load(list_name)

        def clear():
            connect.clear()

        if   (argv[1]     == "play"):    play()
        elif (argv[1]     == "pause"):   pause()
        elif (argv[1]     == "stop"):    stop()
        elif (argv[1][:4] == "prev"):    prev()
        elif (argv[1]     == "next"):    next()
        elif (argv[1]     == "random"):  random()
        elif (argv[1]     == "repeat"):  repeat()
        elif (argv[1]     == "consume"): consume()
        elif (argv[1]     == "volume"):  volume(argv[2])
        elif (argv[1]     == "client"):  client()
        elif (argv[1]     == "kill"):    kill()
        elif (argv[1]     == "update"):  update()
        elif (argv[1]     == "enable"):  enable(argv[2])
        elif (argv[1]     == "disable"): disable(argv[2])
        elif (argv[1]     == "load"):    load(argv[2])
        elif (argv[1]     == "clear"):   clear()

    else:
        # 
        print """<?xml version="1.0" encoding="UTF-8"?>"""
        print """<openbox_pipe_menu>"""
        print action % (display_state,'client')
        print separator
        print action % ('Next','next')
        print action % ('Previous','prev')
        if status['state'] in ["pause","stop"]:
            print action % ('Play','play')
        if status['state'] == "play":
            print action % ('Pause','pause')
        print action % ('Stop','stop')
        print separator
        print menu % ("volume","Volume: %s%%" % status.volume)
        print action % ('[100%]','volume 100')
        print action % (' [80%]','volume 80')
        print action % (' [60%]','volume 60')
        print action % (' [40%]','volume 40')
        print action % (' [20%]','volume 20')
        print action % ('[Mute]','volume 0')
        print menu_end
        print menu % ("playlist","Playlist")
        print action % ('clear','clear')
        print separator
        for entity in connect.lsinfo():
            if 'playlist' in entity:
                playlist = entity['playlist']
                print action % (playlist, 'load %s' % playlist)
        print menu_end
        print menu % ("output","Audio Output")
        for out in connect.outputs():
            name,oid = out['outputname'],out['outputid']
            on = int(out['outputenabled'])
            print action % ("%s [%s]" % (name, on and 'enabled' or 'disabled'),
                "%s %s" % ((on and 'disable' or 'enable'), oid))
        print menu_end
        print separator
        print action % ('Toggle random %s' % (
            int(status.random) and '[On]' or '[Off]'), 'random')
        print action % ('Toggle repeat %s' % (
            int(status.repeat) and '[On]' or '[Off]'), 'repeat')
        print action % ('Toggle consume %s' % (
            int(status.consume) and '[On]' or '[Off]'), 'consume')
        print separator
        print action % ('Update Database','update')
        print action % ('Kill MPD','kill')
        print "</openbox_pipe_menu>"

#        print menu % ("Song Info","Volume: %s%%" % status.volume)
#        print info % ('%s kbs' % status.bitrate)
#        print separator
#        print info % ("Artists in DB: %s" % stats.artists)
#        print info % ("Albums in DB: %s" % stats.albums)
#        print info % ("Songs in DB: %s" % stats.songs)


########NEW FILE########
__FILENAME__ = ob-randr
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A small utility to make xrandr adjustments from an OpenBox menu.

To install, put this file somewhere and make sure it is executable.

Edit your $HOME/.config/openbox/menu.xml file. Add something like the following
near the top::

    <menu id="randr-menu" label="randr" execute="/path/to/ob-randr.py" />

Then add this in the place you actually want the menu to appear::

    <menu id="randr-menu" />

You can easily add custom commands to the menu by creating the file
$HOME/.ob-randrrc. The syntax looks like this::

    [Notebook]

    portrait: --output LVDS --primary --mode 1366x768 --output VGA-0 --mode 1440x900 --left-of LVDS --rotate left

    [Netbook]

    zoom out: --output LVDS --scale 1.3x1.3
    zoom in: --output LVDS --panning 1280x1024

The idea is that you can create machine-specific shortcuts. For example, with
my laptop at home I frequently connect to an external widescreen display turned
sideways. On my netbook, I frequently 'zoom out' to a higher resolution in
scaled-out mode or 'zoom in' to a higher resolution in panning mode.


TODO:

* Add left-of, right-of, above, below, same-as menus for active displays.
* What other common tasks should be represented?

"""
AUTHOR = 'Seth House <seth@eseth.com>'
VERSION = '0.1'

import ConfigParser
import os
import subprocess
import sys

try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree

HOME = os.path.expanduser('~')
RCFILE = '.ob-randrrc'

def mk_exe_node(output, name, command):
    """A small helper to speed the three-element PITA that is the OpenBox
    execute menu syntax.

    """
    CMD = 'xrandr --output %s ' % output

    item = etree.Element('item', label=name)
    action = etree.SubElement(item, 'action', name='execute')
    etree.SubElement(action, 'command').text = CMD + command

    return item

def get_rc_menu():
    """Read the user's rc file and return XML for menu entries."""
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(HOME, RCFILE))

    menus = []

    for i in config.sections():
        menu = etree.Element('menu', id='shortcut-%s' % i, label=i)

        for name in config.options(i):
            command = config.get(i, name)

            item = etree.SubElement(menu, 'item', label=name)
            action = etree.SubElement(item, 'action', name='execute')
            etree.SubElement(action, 'command').text = 'xrandr ' + command

        menus.append(menu)

    return menus

def get_xml():
    """Run xrandr -q and parse the output for the bits we're interested in,
    then build an XML tree suitable for passing to OpenBox.

    """
    xrandr = subprocess.Popen(['xrandr', '-q'], stdout=subprocess.PIPE)
    xrandr_lines = xrandr.stdout.readlines()

    root = etree.Element('openbox_pipe_menu')

    actions = (
        ('right', '--rotate right'),
        ('left', '--rotate left'),
        ('inverted', '--rotate inverted'),
        ('normal', '--rotate normal'),
        (),
        ('on', '--on'),
        ('off', '--off'),
        (),
        ('auto', '--auto'),
        ('reset', ' '.join([
            '--auto', '--rotate normal', '--scale 1x1', '--panning 0x0'])))

    # The following string processing is far more verbose than necessary but if
    # the xrandr output ever changes (or I simply got it wrong to begin with)
    # this should make it easier to fix.
    for i in xrandr_lines:
        if ' current' in i:
            # Screen 0: minimum 320 x 200, current 1700 x 1440, maximum 2048 x 2048
            text = [j for j in i.split(',') if ' current' in j][0]
            text = text.replace(' current ', '')

            etree.SubElement(root, 'separator', label="Current: %s" % text)

        elif ' connected' in i:
            # VGA connected 900x1440+0+0 left (normal left inverted right x axis y axis) 408mm x 255mm
            text = i.replace(' connected', '')
            text = text.partition('(')[0]
            text = text.strip()

            try:
                output, mode, extra = (lambda x: (x[0], x[1], x[2:]))(text.split(' '))
            except IndexError:
                # LVDS connected (normal left inverted right x axis y axis)
                # Display is connected but off. Is this the best place to check that?
                output, mode, extra = text, 'off', ''

            node = etree.SubElement(root, 'menu', id=output, type='output',
                    label=' '.join([output, mode, ' '.join(extra)]))
            modes = etree.SubElement(node, 'menu', id='%s-modes' % output,
                    type='modes', label='modes')
            etree.SubElement(node, 'separator')

            # Grab all the available modes (I'm ignoring refresh rates for now)
            for j in xrandr_lines[xrandr_lines.index(i) + 1:]:
                if not j.startswith(' '):
                    break

                #   1440x900       59.9*+   59.9*
                text = j.strip()
                text = text.split(' ')[0]

                modes.append(mk_exe_node(output, text, '--mode %s' % text))

            for action in actions:
                if not action:
                    etree.SubElement(node, 'separator')
                else:
                    node.append(mk_exe_node(output, *action))

        elif ' disconnected' in i:
            # TV disconnected (normal left inverted right x axis y axis)
            text = i.replace(' disconnected', '')
            text = text.partition('(')[0]
            name, extra = (lambda x: (x[0], x[1:]))(text.split(' '))

            etree.SubElement(root, 'item', label=name)

    # Grab the user's rc menu shortcuts
    etree.SubElement(root, 'separator', label='Shortcuts')

    auto = etree.SubElement(root, 'item', label='auto')
    auto_action = etree.SubElement(auto, 'action', name='execute')
    etree.SubElement(auto_action, 'command').text = 'xrandr --auto'

    for i in get_rc_menu():
        root.append(i)

    return root

if __name__ == '__main__':
    ob_menu = get_xml()
    sys.stdout.write(etree.tostring(ob_menu) + '\n')

########NEW FILE########
__FILENAME__ = processes
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
#-------------------------------------------------------------------------------

processes.py - version 7
by Vlad George

#-------------------------------------------------------------------------------

Description:
    This script pipes a process manipulation menu into the openbox menu.

Usage:
    Just place this script in ~/.config/openbox/scripts, make it executable; if you want you can enlist the processes
    which should not be shown in the unwanted_procs list below, then add following to your ~/.config/openbox/menu.xml:
    "<menu id="proc-menu" label="processes" execute="~/.config/openbox/scripts/processes.py" />...
    <menu id="root-menu" label="Openbox3">...<menu id="proc-menu" />...</menu>"
    and reconfigure openbox.
    To enable cpu usage display uncomment the lines marked with (***) (lines 106-108 and 146).
      Note: You need 'ps'.
    To enable cpulimit just uncomment the lines marked with (#*#) (lines 158-169).
      Note: You need 'cpulimit'. Get it from here: "http://cpulimit.sourceforge.net"

Changelog:
    20.02.07: 7th version - added "-z" flag to cpulimit; added ValueError handling for printXml; added --title flag
    04.12.07: 6th version - added cpulimit; to enable it just uncomment the lines marked with (#*#)
    18.11.07: 5th version - processes alphabetically sorted
    22.10.07: 4th version - totally removed SleepAVG from script. for kernels < 2.6.20 please use earlier versions.
                            simplified cpu usage command.
    07.07.07: 3rd version - added cpu usage;
                            since SleepAVG was removed from /proc (2.6.20), it will be only displayed depending on running kernel version
    17.02.07: 2nd version - shortened procData

#-------------------------------------------------------------------------------

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
http://www.fsf.org/

"""

#-------------------------------------------------------------------------------             
#                             User set variables
#-------------------------------------------------------------------------------             

##  processes (e.g. daemons, bash, this script, etc) you do not want to be shown in the process manipulation menu:
##  !!! don´t forget quotes !!!

##  unwanted_procs = ["processes.py","ssh-agent","gconfd-2","dbus-daemon","dbus-launch","kded","dcopserver","..."]
unwanted_procs = ["processes.py","sh","bash","netstat","ssh-agent","gconfd-2","gnome-pty-helpe","dbus-daemon","dbus-launch",\
                  "visibility","pypanel","knotify","kdeinit","klauncher","kded","dcopserver","kio_file"]

##  if you want a title (separator) for the processes menu you can set it here; to show the title use the "--title" flag (/path/to/processes.py --title)
processes_menu_title = "processes"


#-------------------------------------------------------------------------------
#                                   Script
#-------------------------------------------------------------------------------


def _procName(pid):
    """ pid -> processname """
    try:
        return file(os.path.join('/proc', str(pid), 'status'), 'r').readline().split()[1]
    except IOError:
        return None


def _procData(pid):
    """ pid -> info_list = [State, VmSize, VmLck, VmRSS, VmLib, priority(nice), command, cpu usage] """
    info_list = list()

    ##  from /proc/<pid>/status get State, VmSize, VmLck, VmRSS, VmLib
    status_file = file(os.path.join("/proc", str(pid), "status"), 'r')
    status = status_file.readlines()
    status_file.close()
    [info_list.append(status[i].split(":")[1].lstrip().rstrip("\n")) for i in (1,11,12,14,18)]

    ##  from /proc/<pid>/stat get priority(nicelevel)
    priority_file = file(os.path.join('/proc', str(pid), 'stat'), 'r')
    priority = priority_file.read()
    priority_file.close()
    info_list.append(priority.split()[18])

    ##  from /proc/<pid>/cmdline get command
    cmdline_file = file(os.path.join("/proc", str(pid),"cmdline"),'r')
    cmdline = cmdline_file.read()
    cmdline_file.close()
    info_list.append(" ".join(cmdline.split("\x00")[:-1]))

    ##  from "ps --pid %s -o pcpu=" get cpu usage for pid
    ##  (***) comment out following three lines to disable cpu usage display
    #ps_cpu_for_pid = 'ps --pid %s -o pcpu=' % (pid)
    #ps_cmd = os.popen(ps_cpu_for_pid).readline()
    #info_list.append(ps_cmd)
    ##  (***)
    return info_list


def userPidFilter():
    """ fiters pids from /proc/<pid>/ for user who owns script excluding the unwanted_procs ids """
    uid = os.stat(sys.argv[0])[4]
    uid_pids = list()
    for pid in os.listdir("/proc"):
        if os.path.isdir(os.path.join("/proc", pid)):
             try:
                if os.stat(os.path.join("/proc", pid))[4] == uid :
                    uid_pids.append(int(pid))
             except ValueError:
                pass

    ##  sort pids according to process names 
    pid_proc_list = list()
    [pid_proc_list.append((i, _procName(i))) for i in uid_pids]

    def removeProcsFromList(pid):
        process = _procName(pid)
        if process in unwanted_procs:
            pid_proc_list.remove((pid, process))
    map(removeProcsFromList, uid_pids)

    pid_proc_list.sort(key = lambda t:t[1].lower())
    return [pid_proc_list[i][0] for i in xrange(len(pid_proc_list))]


def printXml(pid):
    """ xml output for each pid
    _procData(pid)=[[0]-State, [1]-VmSize, [2]-VmLck, [3]-VmRSS, [4]-VmLib, [5]-priority(nice), [6]-command, [(***)optional: [7]-cpu usage]] """

    proc_info = _procData(pid)

##  (***) uncomment following line to enable cpu usage display:
    #print '<item label="cpu usage: %s' % (proc_info[7]) + ' %"><action name="execute"><command>true</command></action></item>'
##  (***)
    print '<menu id="%s-menu-memory" label="memory: %s MB">' % (pid, int(proc_info[1].split()[0])/1024)
    print '<item label="Ram: %s"><action name="Execute"><command>true</command></action></item>' % (proc_info[3])
    print '<item label="Lib: %s"><action name="Execute"><command>true</command></action></item>' % (proc_info[4])
    print '<item label="Lock: %s"><action name="Execute"><command>true</command></action></item>' % (proc_info[2])
    print '<item label="Total: %s"><action name="Execute"><command>true</command></action></item>' % (proc_info[1])
    print '</menu>'

    print '<separator />'

##  (#*#) uncomment following lines to enable cpulimit:
    #print '<menu id="%s-menu-cpulimit" label="cpulimit">' % (pid)
    #print '<item label=" 10 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 10</command></action></item>' % (pid)
    #print '<item label=" 20 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 20</command></action></item>' % (pid)
    #print '<item label=" 30 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 30</command></action></item>' % (pid)
    #print '<item label=" 40 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 40</command></action></item>' % (pid)
    #print '<item label=" 50 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 50</command></action></item>' % (pid)
    #print '<item label=" 60 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 60</command></action></item>' % (pid)
    #print '<item label=" 70 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 70</command></action></item>' % (pid)
    #print '<item label=" 80 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 80</command></action></item>' % (pid)
    #print '<item label=" 90 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 90</command></action></item>' % (pid)
    #print '<item label="100 &#37;"><action name="Execute"><command>cpulimit -p %s -z -l 100</command></action></item>' % (pid)
    #print '</menu>'
##  (#*#)

    print '<menu id="%s-menu-priority" label="priority (%s)">' % (pid, proc_info[5])
    print '<item label="-10 (fast)"><action name="Execute"><command>renice -10 %s</command></action></item>' % (pid)
    print '<item label="-5"><action name="Execute"><command>renice -5 %s</command></action></item>' % (pid)
    print '<item label="0 (base)"><action name="Execute"><command>renice 0 %s</command></action></item>' % (pid)
    print '<item label="5"><action name="Execute"><command>renice 5 %s</command></action></item>' % (pid)
    print '<item label="10"><action name="Execute"><command>renice 10 %s</command></action></item>' % (pid)
    print '<item label="15"><action name="Execute"><command>renice 15 %s</command></action></item>' % (pid)
    print '<item label="19 (idle)"><action name="Execute"><command>renice 19 %s</command></action></item>' % (pid)
    print '</menu>'

    print '<menu id="%s-menu-state" label="%s">' % (pid, proc_info[0])
    print '<item label="stop"><action name="Execute"><command>kill -SIGSTOP %s</command></action></item>' % (pid)
    print '<item label="continue"><action name="Execute"><command>kill -SIGCONT %s</command></action></item>' % (pid)
    print '</menu>'

    print '<menu id="%s-menu-stop" label="stop signals">' % (pid)
    print '<item label="exit"><action name="Execute"><command>kill -TERM %s</command></action></item>' % (pid)
    print '<item label="hangup"><action name="Execute"><command>kill -HUP %s</command></action></item>' % (pid)
    print '<item label="interrupt"><action name="Execute"><command>kill -INT %s</command></action></item>' % (pid)
    print '<item label="kill"><action name="Execute"><command>kill -KILL %s</command></action></item>' % (pid)
    print '</menu>'
    print '<separator />'

    print '<menu id="%s-menu-command" label="command">' % (pid)
    print '<item label="%s"><action name="Execute"><command>true</command></action></item>' % (proc_info[6])
    print '<separator />'
    print '<item label="spawn new"><action name="Execute"><command>%s</command></action></item>' % (proc_info[6])
    print '</menu>'


def generateMenu(pid):
    """ generate main menu """
    print '<menu id="%s-menu" label="%s" execute="%s --pid %s"/>' % (pid, _procName(pid), sys.argv[0], pid)

#-------------------------------------------------------------------------------             
#                                    Main
#-------------------------------------------------------------------------------             

import os, sys

#-------------------------#
if __name__ == "__main__" :
#-------------------------#
    print '<?xml version="1.0" encoding="UTF-8"?>'
    print '<openbox_pipe_menu>'
    args = sys.argv[1:]
    if ('--pid' in args):
        try:
            printXml(int(sys.argv[2]))
        except ValueError and IOError:
            pass
    else:
        if ('--title' in args):
            print '<separator label="%s" />' % (processes_menu_title)
        else:
            pass
        map(generateMenu, userPidFilter())
    print '</openbox_pipe_menu>'

# vim: set ft=python nu ts=4 sw=4 :

########NEW FILE########
__FILENAME__ = .pdbrc
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498182
def complete(self, text, state):
    """return the next possible completion for text, using the current frame's
       local namespace

       This is called successively with state == 0, 1, 2, ... until it
       returns None.  The completion should begin with 'text'.
    """
    # keep a completer class, and make sure that it uses the current local scope 
    if not hasattr(self, 'completer'):
        self.completer = rlcompleter.Completer(self.curframe.f_locals)
    else:
        self.completer.namespace = self.curframe.f_locals
    return self.completer.complete(text, state)



# Command line history:
import readline
histfile = os.path.expanduser("~/.pdb-pyhist")
try:
    readline.read_history_file(histfile)
except IOError:
    pass
import atexit
atexit.register(readline.write_history_file, histfile)
del histfile
readline.set_history_length(1000)

# return to debugger after fatal exception (Python cookbook 14.5):
def info(type, value, tb):
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        sys.__excepthook__(type, value, tb)
    import traceback, pdb
    traceback.print_exception(type, value, tb)
    print
    pdb.pm()

sys.excepthook = info

########NEW FILE########
__FILENAME__ = .pythonrc
# -*- coding: utf-8 -*-
"""Best goddamn .pythonrc file in the whole world.

This file is executed when the Python interactive shell is started if
$PYTHONSTARTUP is in your environment and points to this file. It's just
regular Python commands, so do what you will. Your ~/.inputrc file can greatly
complement this file.

"""
# Imports we need
import sys
import os
import readline, rlcompleter
import atexit
import pprint
from tempfile import mkstemp
from code import InteractiveConsole

# Imports we want
import datetime
import pdb

AUTHOR = 'Seth House <seth@eseth.com>'

# Color Support
###############

class TermColors(dict):
    """Gives easy access to ANSI color codes. Attempts to fall back to no color
    for certain TERM values. (Mostly stolen from IPython.)"""

    COLOR_TEMPLATES = (
        ("Black"       , "0;30"),
        ("Red"         , "0;31"),
        ("Green"       , "0;32"),
        ("Brown"       , "0;33"),
        ("Blue"        , "0;34"),
        ("Purple"      , "0;35"),
        ("Cyan"        , "0;36"),
        ("LightGray"   , "0;37"),
        ("DarkGray"    , "1;30"),
        ("LightRed"    , "1;31"),
        ("LightGreen"  , "1;32"),
        ("Yellow"      , "1;33"),
        ("LightBlue"   , "1;34"),
        ("LightPurple" , "1;35"),
        ("LightCyan"   , "1;36"),
        ("White"       , "1;37"),
        ("Normal"      , "0"),
    )

    NoColor = ''
    _base  = '\001\033[%sm\002'

    def __init__(self):
        if os.environ.get('TERM') in ('xterm-color', 'xterm-256color', 'linux',
                                    'screen', 'screen-256color', 'screen-bce'):
            self.update(dict([(k, self._base % v) for k,v in self.COLOR_TEMPLATES]))
        else:
            self.update(dict([(k, self.NoColor) for k,v in self.COLOR_TEMPLATES]))
_c = TermColors()

# Enable a History
##################

HISTFILE="%s/.pyhistory" % os.environ["HOME"]

# Read the existing history if there is one
if os.path.exists(HISTFILE):
    readline.read_history_file(HISTFILE)

# Set maximum number of items that will be written to the history file
readline.set_history_length(300)

def savehist():
    readline.write_history_file(HISTFILE)

atexit.register(savehist)

# Enable Color Prompts
######################

sys.ps1 = '%s>>> %s' % (_c['Green'], _c['Normal'])
sys.ps2 = '%s... %s' % (_c['Red'], _c['Normal'])

# Enable Pretty Printing for stdout
###################################

def my_displayhook(value):
    if value is not None:
        try:
            import __builtin__
            __builtin__._ = value
        except ImportError:
            __builtins__._ = value

        pprint.pprint(value)
sys.displayhook = my_displayhook

# Welcome message
#################

WELCOME = """\
%(Cyan)s
You've got color, history, and pretty printing.
(If your ~/.inputrc doesn't suck, you've also
got completion and vi-mode keybindings.)
%(Brown)s
Type \e to get an external editor.
%(Normal)s""" % _c

atexit.register(lambda: sys.stdout.write("""%(DarkGray)s
Sheesh, I thought he'd never leave. Who invited that guy?
%(Normal)s""" % _c))

# Django Helpers
################

def SECRET_KEY():
    "Generates a new SECRET_KEY that can be used in a project settings file."

    from random import choice
    return ''.join(
            [choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
                for i in range(50)])

# If we're working with a Django project, set up the environment
if 'DJANGO_SETTINGS_MODULE' in os.environ:
    from django.db.models.loading import get_models
    from django.test.client import Client
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.conf import settings as S

    class DjangoModels(object):
        """Loop through all the models in INSTALLED_APPS and import them."""
        def __init__(self):
            for m in get_models():
                setattr(self, m.__name__, m)

    A = DjangoModels()
    C = Client()

    WELCOME += """%(Green)s
Django environment detected.
* Your INSTALLED_APPS models are available as `A`.
* Your project settings are available as `S`.
* The Django test client is available as `C`.
%(Normal)s""" % _c

    setup_test_environment()
    S.DEBUG_PROPAGATE_EXCEPTIONS = True

    WELCOME += """%(LightPurple)s
Warning: the Django test environment has been set up; to restore the
normal environment call `teardown_test_environment()`.

Warning: DEBUG_PROPAGATE_EXCEPTIONS has been set to True.
%(Normal)s""" % _c


# Salt Helpers
##############
if 'SALT_MASTER_CONFIG' in os.environ:
    try:
        import salt.config
        import salt.client
        import salt.runner
    except ImportError:
        pass
    else:
        __opts_master__ = salt.config.master_config(
                os.environ['SALT_MASTER_CONFIG'])

        # Instantiate LocalClient and RunnerClient
        SLC = salt.client.LocalClient(__opts_master__)
        SRUN = salt.runner.Runner(__opts_master__)

if 'SALT_MINION_CONFIG' in os.environ:
    try:
        import salt.config
        import salt.loader
        import jinja2
        import yaml
    except ImportError:
        pass
    else:
        # Create the Salt __opts__ variable
        __opts__ = salt.config.client_config(os.environ['SALT_MINION_CONFIG'])

        # Populate grains if it hasn't been done already
        if not 'grains' in __opts__ or not __opts__['grains']:
            __opts__['grains'] = salt.loader.grains(__opts__)

        # Populate template variables
        __salt__ = salt.loader.minion_mods(__opts__)
        __grains__ = __opts__['grains']
        __pillar__ = salt.pillar.get_pillar(
            __opts__,
            __grains__,
            __opts__['id'],
            __opts__.get('environment'),
        ).compile_pillar()

        JINJA = lambda x, **y: jinja2.Template(x).render(
                grains=__grains__,
                salt=__salt__,
                opts=__opts__,
                pillar=__pillar__,
                **y)

# Start an external editor with \e
##################################
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/438813/

EDITOR = os.environ.get('EDITOR', 'vi')
EDIT_CMD = '\e'

class EditableBufferInteractiveConsole(InteractiveConsole):
    def __init__(self, *args, **kwargs):
        self.last_buffer = [] # This holds the last executed statement
        InteractiveConsole.__init__(self, *args, **kwargs)

    def runsource(self, source, *args):
        self.last_buffer = [ source.encode('utf-8') ]
        return InteractiveConsole.runsource(self, source, *args)

    def raw_input(self, *args):
        line = InteractiveConsole.raw_input(self, *args)
        if line == EDIT_CMD:
            fd, tmpfl = mkstemp('.py')
            os.write(fd, b'\n'.join(self.last_buffer))
            os.close(fd)
            os.system('%s %s' % (EDITOR, tmpfl))
            line = open(tmpfl).read()
            os.unlink(tmpfl)
            tmpfl = ''
            lines = line.split( '\n' )
            for i in range(len(lines) - 1): self.push( lines[i] )
            line = lines[-1]
        return line

c = EditableBufferInteractiveConsole(locals=locals())
c.interact(banner=WELCOME)

# Exit the Python shell on exiting the InteractiveConsole
sys.exit()

########NEW FILE########
__FILENAME__ = notify_send
# Author: lavaramano <lavaramano AT gmail DOT com>
# Improved by: BaSh - <bash.lnx AT gmail DOT com>
# Ported to Weechat 0.3.0 by: Sharn - <sharntehnub AT gmail DOT com)
# This Plugin Calls the libnotify bindings via python when somebody says your nickname, sends you a query, etc.
# To make it work, you may need to download: python-notify (and libnotify - libgtk)
# Requires Weechat 0.3.0
# Released under GNU GPL v2

import weechat, os, re

weechat.register("notify-send", "whiteinge", "0.0.1", "GPL", "notify-send: calls notify-send cli on highlight", "", "")

# script options
settings = {
    "show_hilights"      : "on",
    "show_priv_msg"      : "on",
    "nick_separator"     : ": ",
    "icon"               : "/usr/share/pixmaps/weechat.xpm",
    "urgency"            : "normal",
    "smart_notification" : "off",
}

# Strip all unsafe chars from the msg
pattern = re.compile("""[\\'"]+""")

# Init everything
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

# Hook privmsg/hilights
weechat.hook_print("", "irc_privmsg", "", 1, "notify_show", "")

# Functions
def notify_show(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):
    """Sends highlighted message to be printed on notification"""

    # FIXME: un-hardcode this
    if ('nick_*status' in tagsn) or ('nick_whiteinge' in tagsn):
        return weechat.WEECHAT_RC_OK

    if (weechat.config_get_plugin('smart_notification') == "on" and
            bufferp == weechat.current_buffer()):
        pass

    elif (weechat.buffer_get_string(bufferp, "localvar_type") == "private" and
            weechat.config_get_plugin('show_priv_msg') == "on"):
        show_notification(prefix, message)

    elif (ishilight == "1" and 
            weechat.config_get_plugin('show_hilights') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        show_notification(buffer, prefix +
                weechat.config_get_plugin('nick_separator') + message)

    return weechat.WEECHAT_RC_OK

def show_notification(chan,message):
    icon = weechat.config_get_plugin('icon')
    urgency = 'normal'

    safe_chan = pattern.sub('', chan)
    safe_msg =  pattern.sub('', message)

    os.system('notify-send --hint=int:transient:1 -u %(urgency)s -i %(icon)s "%(safe_chan)s" "%(safe_msg)s" &' % locals())

########NEW FILE########
__FILENAME__ = screen_away
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
# Copyright (c) 2009 by penryu <penryu@gmail.com>
# Copyright (c) 2010 by Blake Winton <bwinton@latte.ca>
# Copyright (c) 2010 by Aron Griffis <agriffis@n01se.net>
# Copyright (c) 2010 by Jani Kesänen <jani.kesanen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2010-08-07, Filip H.F. "FiXato" Slagter <fixato@gmail.com>
#  version 0.8: add command on attach feature
# 2010-05-07, Jani Kesänen <jani.kesanen@gmail.com>
#  version 0.7: add command on detach feature
# 2010-03-07, Aron Griffis <agriffis@n01se.net>
#  version 0.6: move socket check to register,
#               add hook_config for interval,
#               reduce default interval from 60 to 5
# 2010-02-19, Blake Winton <bwinton@latte.ca>
#  version 0.5: add option to change nick when away
# 2010-01-18, xt
#  version 0.4: only update servers that are connected
# 2009-11-30, xt <xt@bash.no>
#  version 0.3: do not touch servers that are manually set away
# 2009-11-27, xt <xt@bash.no>
#  version 0.2: code for TMUX from penryu
# 2009-11-27, xt <xt@bash.no>
#  version 0.1: initial release

import weechat as w
import re
import os

SCRIPT_NAME    = "screen_away"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.8"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set away status on screen detach"

settings = {
        'message': 'Detached from screen',
        'interval': '5',        # How often in seconds to check screen status
        'away_suffix': '',      # What to append to your nick when you're away.
        'command_on_attach': '', # Command to execute on attach
        'command_on_detach': '' # Command to execute on detach
}

TIMER = None
SOCK = None
AWAY = False

def set_timer():
    '''Update timer hook with new interval'''

    global TIMER
    if TIMER:
        w.unhook(TIMER);
    TIMER = w.hook_timer(int(w.config_get_plugin('interval')) * 1000,
            0, 0, "screen_away_timer_cb", '')

def screen_away_config_cb(data, option, value):
    if option.endswith(".interval"):
        set_timer()
    return w.WEECHAT_RC_OK

def get_servers():
    '''Get the servers that are not away, or were set away by this script'''

    infolist = w.infolist_get('irc_server','','')
    buffers = []
    while w.infolist_next(infolist):
        if not w.infolist_integer(infolist, 'is_connected') == 1:
            continue
        if not w.infolist_integer(infolist, 'is_away') or \
               w.infolist_string(infolist, 'away_message') == \
               w.config_get_plugin('message'):
            buffers.append((w.infolist_pointer(infolist, 'buffer'),
                w.infolist_string(infolist, 'nick')))
    w.infolist_free(infolist)
    return buffers

def screen_away_timer_cb(buffer, args):
    '''Check if screen is attached, update awayness'''

    global AWAY, SOCK

    suffix = w.config_get_plugin('away_suffix')
    attached = os.access(SOCK, os.X_OK) # X bit indicates attached

    if attached and AWAY:
        w.prnt('', '%s: Screen attached. Clearing away status' % SCRIPT_NAME)
        for server, nick in get_servers():
            w.command(server,  "/away")
            if suffix and nick.endswith(suffix):
                nick = nick[:-len(suffix)]
                w.command(server,  "/nick %s" % nick)
        AWAY = False
        if w.config_get_plugin("command_on_attach"):
            w.command("", w.config_get_plugin("command_on_attach"))

    elif not attached and not AWAY:
        w.prnt('', '%s: Screen detached. Setting away status' % SCRIPT_NAME)
        for server, nick in get_servers():
            if suffix:
                w.command(server, "/nick %s%s" % (nick, suffix));
            w.command(server, "/away %s" % w.config_get_plugin('message'));
        AWAY = True
        if w.config_get_plugin("command_on_detach"):
            w.command("", w.config_get_plugin("command_on_detach"))

    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    if 'STY' in os.environ.keys():
        # We are running under screen
        cmd_output = os.popen('env LC_ALL=C screen -ls').read()
        match = re.search(r'Sockets? in (/.+)\.', cmd_output)
        if match:
            SOCK = os.path.join(match.group(1), os.environ['STY'])

    if not SOCK and 'TMUX' in os.environ.keys():
        # We are running under tmux
        socket_data = os.environ['TMUX']
        SOCK = socket_data.rsplit(',',2)[0]

    if SOCK:
        set_timer()
        w.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
            "screen_away_config_cb", "")

########NEW FILE########
__FILENAME__ = shell

# =============================================================================
#  shell.py (c) March 2006, 2009 by Kolter <kolter@openics.org>
#
#  Licence     : GPL v2
#  Description : running shell commands in WeeChat
#  Syntax      : try /help shell to get some help on this script
#  Precond     : needs weechat >= 0.3.0 to run
#
#
# ### changelog ###
#
#  * version 0.4, 2009-05-02, FlashCode <flashcode@flashtux.org>:
#      - sync with last API changes
#  * version 0.3, 2009-03-06, FlashCode <flashcode@flashtux.org>:
#      - use of hook_process to run background process
#      - add option -t <timeout> to kill process after <timeout> seconds
#      - show process running, kill it with -kill
#  * version 0.2, 2009-01-31, FlashCode <flashcode@flashtux.org>:
#      - conversion to WeeChat 0.3.0+
#  * version 0.1, 2006-03-13, Kolter <kolter@openics.org> :
#      - first release
#
# =============================================================================

import weechat, os, datetime

SCRIPT_NAME    = "shell"
SCRIPT_AUTHOR  = "Kolter"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL2"
SCRIPT_DESC    = "Run shell commands in WeeChat"

SHELL_CMD      = "shell"
SHELL_PREFIX   = "[shell] "

cmd_hook_process   = ""
cmd_command        = ""
cmd_start_time     = None
cmd_buffer         = ""
cmd_stdout         = ""
cmd_stderr         = ""
cmd_send_to_buffer = False
cmd_timeout        = 0

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command(
        SHELL_CMD,
        "Running shell commands in WeeChat",
        "[-kill | [-o] [-t seconds] <command line>]",
        "         -kill: kill running process\n"
        "            -o: send output to current buffer (simulate user entry "
        "with command output - dangerous, be careful when using this option)\n"
        "    -t seconds: auto-kill process after timeout (seconds) if process "
        "is still running\n"
        "<command line>: shell command or builtin like cd, getenv, setenv, "
        "unsetenv",
        "-kill|-o|-t|cd|getenv|setenv|unsetenv -o|-t|cd|getenv|setenv|unsetenv",
        "shell_cmd", ""
        )

def shell_init():
    global cmd_hook_process, cmd_command, cmd_start_time, cmd_buffer, cmd_stdout, cmd_stderr
    cmd_hook_process = ""
    cmd_command      = ""
    cmd_start_time   = None
    cmd_buffer       = ""
    cmd_stdout       = ""
    cmd_stderr       = ""

def shell_process_cb(data, command, rc, stdout, stderr):
    global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr, cmd_send_to_buffer
    cmd_stdout += stdout
    cmd_stderr += stderr
    if int(rc) >= 0:
        if cmd_stdout != "":
            lines = cmd_stdout.split("\n")
            if cmd_send_to_buffer:
                for line in lines:
                    if line != "":
                        weechat.command(cmd_buffer, "%s" % line)
            else:
                weechat.prnt(cmd_buffer, "%sCommand '%s' (rc %s), stdout:"
                             % (SHELL_PREFIX, command, rc))
                for line in lines:
                    if line != "":
                        weechat.prnt(cmd_buffer, " \t%s" % line)
        if cmd_stderr != "":
            lines = cmd_stderr.split("\n")
            if cmd_send_to_buffer:
                for line in lines:
                    if line != "":
                        weechat.command(cmd_buffer, "%s" % line)
            else:
                weechat.prnt(cmd_buffer, "%s\t%sCommand '%s' (rc %s), stderr:"
                             % (weechat.prefix("error"), SHELL_PREFIX, command, rc))
                for line in lines:
                    if line != "":
                        weechat.prnt(cmd_buffer, " \t%s" % line)
        cmd_hook_process = ""
    return weechat.WEECHAT_RC_OK

def shell_exec(buffer, command):
    global cmd_hook_process, cmd_command, cmd_start_time, cmd_buffer
    global cmd_stdout, cmd_stderr, cmd_timeout
    if cmd_hook_process != "":
        weechat.prnt(buffer,
                     "%sanother process is running! (use '/%s -kill' to kill it)"
                     % (SHELL_PREFIX, SHELL_CMD))
        return
    shell_init()
    cmd_command = command
    cmd_start_time = datetime.datetime.now()
    cmd_buffer = buffer
    cmd_hook_process = weechat.hook_process(command, cmd_timeout * 1000, "shell_process_cb", "")

def shell_show_process(buffer):
    global cmd_command, cmd_start_time
    if cmd_hook_process == "":
        weechat.prnt(buffer, "%sno process running" % SHELL_PREFIX)
    else:
        weechat.prnt(buffer, "%sprocess running: '%s' (started on %s)"
                     % (SHELL_PREFIX, cmd_command, cmd_start_time.ctime()))

def shell_kill_process(buffer):
    global cmd_hook_process, cmd_command
    if cmd_hook_process == "":
        weechat.prnt(buffer, "%sno process running" % SHELL_PREFIX)
    else:
        weechat.unhook(cmd_hook_process)
        weechat.prnt(buffer, "%sprocess killed (command '%s')" % (SHELL_PREFIX, cmd_command))
        shell_init()

def shell_chdir(buffer, directory):
    if directory == "":
        if os.environ.has_key('HOME'):
            directory = os.environ['HOME']
    try:
        os.chdir(directory)
    except:
        weechat.prnt(buffer, "%san error occured while running command 'cd %s'" % (SHELL_PREFIX, directory))
    else:
        weechat.prnt(buffer, "%schdir to '%s' ok" % (SHELL_PREFIX, directory))

def shell_getenv(buffer, var):
    global cmd_send_to_buffer
    var = var.strip()
    if var == "":
        weechat.prnt(buffer, "%swrong syntax, try 'getenv VAR'" % (SHELL_PREFIX))
        return
        
    value = os.getenv(var)
    if value == None:
        weechat.prnt(buffer, "%s$%s is not set" % (SHELL_PREFIX, var))
    else:
        if cmd_send_to_buffer:
            weechat.command(buffer, "$%s=%s" % (var, os.getenv(var)))
        else:
            weechat.prnt(buffer, "%s$%s=%s" % (SHELL_PREFIX, var, os.getenv(var)))
        
def shell_setenv(buffer, expr):
    global cmd_send_to_buffer
    expr = expr.strip()
    lexpr = expr.split('=')
    
    if (len(lexpr) < 2):
        weechat.prnt(buffer, "%swrong syntax, try 'setenv VAR=VALUE'" % (SHELL_PREFIX))
        return

    os.environ[lexpr[0].strip()] = "=".join(lexpr[1:])
    if not cmd_send_to_buffer:
        weechat.prnt(buffer, "%s$%s is now set to '%s'" % (SHELL_PREFIX, lexpr[0], "=".join(lexpr[1:])))

def shell_unsetenv(buffer, var):
    global cmd_send_to_buffer
    var = var.strip()
    if var == "":
        weechat.prnt(buffer, "%swrong syntax, try 'unsetenv VAR'" % (SHELL_PREFIX))
        return
    
    if os.environ.has_key(var):
        del os.environ[var]
        weechat.prnt(buffer, "%s$%s is now unset" % (SHELL_PREFIX, var))
    else:
        weechat.prnt(buffer, "%s$%s is not set" % (SHELL_PREFIX, var))        
    
def shell_cmd(data, buffer, args):
    global cmd_send_to_buffer, cmd_timeout
    largs = args.split(" ")
    
    # strip spaces
    while '' in largs:
        largs.remove('')
    while ' ' in largs:
        largs.remove(' ')
    
    if len(largs) ==  0:
        shell_show_process(buffer)
    else:
        if largs[0] == '-kill':
            shell_kill_process(buffer)
        else:
            cmd_send_to_buffer = False
            cmd_timeout = 0
            while True:
                if largs[0] == '-o':
                    cmd_send_to_buffer = True
                    largs = largs[1:]
                    continue
                if largs[0] == '-t' and len(largs) > 2:
                    cmd_timeout = int(largs[1])
                    largs = largs[2:]
                    continue
                break;
            if len(largs) > 0:
                if largs[0] == 'cd':
                    shell_chdir(buffer, " ".join(largs[1:]))
                elif largs[0] == 'getenv':
                    shell_getenv (buffer, " ".join(largs[1:]))
                elif largs[0] == 'setenv':
                    shell_setenv (buffer, " ".join(largs[1:]))
                elif largs[0] == 'unsetenv':
                    shell_unsetenv (buffer, " ".join(largs[1:]))
                else:
                    shell_exec(buffer, " ".join(largs))
    
    return weechat.WEECHAT_RC_OK

########NEW FILE########
