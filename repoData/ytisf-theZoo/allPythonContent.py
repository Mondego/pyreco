__FILENAME__ = eula_handler
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5Fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from imports import globals


class EULA:

    def __init__(self, langs = None, oneRun=True):
        #self.oneRun = oneRun
        self.check_eula_file()
        #self.prompt_eula()

    def check_eula_file(self):
        try:
            with open(globals.vars.eula_file):
                return 1
        except IOError:
            return 0

    def prompt_eula(self):
        globals.init()
        #os.system('clear')
        print globals.bcolors.RED
        print '_____________________________________________________________________________'
        print '|                 ATTENTION!!! ATTENTION!!! ATTENTION!!!                    |'
        print '|                       ' + globals.vars.appname + ' v' + globals.vars.version + '                               |'
        print '|___________________________________________________________________________|'
        print '|This program contain live and dangerous malware files                      |'
        print '|This program is intended to be used only for malware analysis and research |'
        print '|and by agreeing the EULA you agree to only use it for legal purposes and   |'
        print '|studying malware.                                                          |'
        print '|You understand that these file are dangerous and should only be run on VMs |'
        print '|you can control and know how to handle. Running them on a live system will |'
        print '|infect you machines will live and dangerous malwares!.                     |'
        print '|___________________________________________________________________________|'
        print globals.bcolors.WHITE
        eula_answer = raw_input('Type YES in captial letters to accept this EULA.\n >')
        if eula_answer == 'YES':
            new = open(globals.vars.eula_file, 'a')
            new.write(eula_answer)
        else:
            print 'You need to accept the EULA.\nExiting the program.'
            sys.exit(1)
########NEW FILE########
__FILENAME__ = globals
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5Fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys

class init:
    def init(self):
        # Global Variables
        version = "0.5.0 Citadel"
        appname = "theZoo"
        codename = "Citadel"
        authors = "Yuval Nativ, Lahad Ludar, 5fingers"
        licensev = "GPL v3.0"
        fulllicense = appname + " Copyright (C) 2014 " + authors + "\n"
        fulllicense += "This program comes with ABSOLUTELY NO WARRANTY; for details type '" + sys.argv[0] +" -w'.\n"
        fulllicense += "This is free software, and you are welcome to redistribute it."

        useage = '\nUsage: ' + sys.argv[0] +  ' -s search_query -t trojan -p vb\n\n'
        useage += 'The search engine can search by regular search or using specified arguments:\n\nOPTIONS:\n   -h  --help\t\tShow this message\n   -t  --type\t\tMalware type, can be virus/trojan/botnet/spyware/ransomeware.\n   -p  --language\tProgramming language, can be c/cpp/vb/asm/bin/java.\n   -u  --update\t\tUpdate malware index. Rebuilds main CSV file. \n   -s  --search\t\tSearch query for name or anything. \n   -v  --version\tPrint the version information.\n   -w\t\t\tPrint GNU license.\n'

        column_for_pl = 6
        column_for_type = 2
        column_for_location = 1
        colomn_for_time = 7
        column_for_version = 4
        column_for_name = 3
        column_for_uid = 0
        column_for_arch = 8
        column_for_plat = 9
        column_for_vip = 10

        conf_folder = 'conf'
        eula_file = conf_folder + '/eula_run.conf'
        maldb_ver_file = conf_folder + '/db.ver'
        main_csv_file = conf_folder + '/index.csv'
        giturl = 'https://raw.github.com/ytisf/theZoo/master/'
        addrs = ['reverce_tcp/', 'crazy_mal/', 'mal/', 'show malwares']

class bcolors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[0m'

class vars:
    version = "0.5.0 Citadel"
    appname = "Malware DB"
    authors = "Yuval Nativ, Lahad Ludar, 5fingers"
    licensev = "GPL v3.0"
    fulllicense = appname + " Copyright (C) 2014 " + authors + "\n"
    fulllicense += "This program comes with ABSOLUTELY NO WARRANTY; for details type '" + sys.argv[0] +" -w'.\n"
    fulllicense += "This is free software, and you are welcome to redistribute it."

    useage = '\nUsage: ' + sys.argv[0] +  ' -s search_query -t trojan -p vb\n\n'
    useage += 'The search engine can search by regular search or using specified arguments:\n\nOPTIONS:\n   -h  --help\t\tShow this message\n   -t  --type\t\tMalware type, can be virus/trojan/botnet/spyware/ransomeware.\n   -p  --language\tProgramming language, can be c/cpp/vb/asm/bin/java.\n   -u  --update\t\tUpdate malware index. Rebuilds main CSV file. \n   -s  --search\t\tSearch query for name or anything. \n   -v  --version\tPrint the version information.\n   -w\t\t\tPrint GNU license.\n'

    column_for_pl = 6
    column_for_type = 2
    column_for_location = 1
    colomn_for_time = 7
    column_for_version = 4
    column_for_name = 3
    column_for_uid = 0
    column_for_arch = 8
    column_for_plat = 9
    column_for_vip = 10

    conf_folder = 'conf'
    eula_file = conf_folder + '/eula_run.conf'
    maldb_ver_file = conf_folder + '/db.ver'
    main_csv_file = conf_folder + '/index.csv'
    giturl = 'https://raw.github.com/ytisf/theZoo/master/'

    with file(maldb_ver_file) as f:
        db_ver = f.read()

    maldb_banner = "    	    __  ___      __                               ____  ____\n"
    maldb_banner += "      	   /  |/  /___ _/ /      ______ _________        / __ \/ __ )\n"
    maldb_banner += "    	  / /|_/ / __ `/ / | /| / / __ `/ ___/ _ \______/ / / / __ |\n"
    maldb_banner += "    	 / /  / / /_/ / /| |/ |/ / /_/ / /  /  __/_____/ /_/ / /_/ /\n"
    maldb_banner += "    	/_/  /_/\__,_/_/ |__/|__/\__,_/_/   \___/     /_____/_____/\n\n"
    maldb_banner += "                                version: " + version + "\n"
    maldb_banner += "                                db_version: " + db_ver + "\n"
    maldb_banner += "                                built by: " + authors + "\n\n"

    addrs = ['reverce_tcp/', 'crazy_mal/', 'mal/', 'show malwares']
    addrs = ['list', 'search', 'get', 'exit']

########NEW FILE########
__FILENAME__ = manysearches
from imports import globals


class MuchSearch(object):
    def __init__(self):
        self.array = []

    def sort(self, array, column, value):
        i=0
        m=[]
        for each in array:
            if array[i][column] == value:
                m.append(each)
            i = i + 1
        return m

    def PrintPayloads(self, m):
        print "\nPayloads Found:"
        array = m
        i = 0
        print "ID\tVIP\tType\t\tLang\tArch\tPlat\tName"
        print '---\t---\t-----\t\t-----\t----\t-----\t----------------'
        for element in array:
            answer = array[i][globals.vars.column_for_uid]
            answer = array[i][globals.vars.column_for_vip]
            answer += '\t%s' % ('{0: <12}'.format(array[i][globals.vars.column_for_type]))
            answer += '\t%s' % ('{0: <12}'.format(array[i][globals.vars.column_for_pl]))
            answer += array[i][globals.vars.column_for_arch] + '\t'
            answer += array[i][globals.vars.column_for_plat] + '\t'
            answer += '\t%s' % ('{0: <12}'.format(array[i][globals.vars.column_for_name]))
            print answer
            i=i+1

########NEW FILE########
__FILENAME__ = muchmuchstrings
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5Fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.

from imports import globals


class banners:

    def print_license(self):
        print ""
        print globals.vars.fulllicense
        print ""

    def versionbanner(self):
        print ""
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print "\t\t    " + globals.vars.appname + ' v' + globals.vars.version
        print "Built by:\t\t" + globals.vars.authors
        print "Is licensed under:\t" + globals.vars.licensev
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print globals.vars.fulllicense
        print globals.vars.useage

    def print_available_payloads(self, array):
        answer = str(array[globals.vars.column_for_uid]) + "\t" + str(array[globals.vars.column_for_name]) + "\t" + str(array[globals.vars.column_for_version]) + "\t\t"
        answer += str(array[globals.vars.column_for_location]) + "\t\t" + str(array[globals.vars.colomn_for_time])
        print answer

########NEW FILE########
__FILENAME__ = terminal_handler
import csv
import sys
import re

import globals
from imports import manysearches
from imports.updatehandler import Updater


class Controller:
    def __init__(self):
        self.modules = None
        self.currentmodule = ''
        self.commands = [   ("search", "searching for malwares using given parameter with 'set'."),
                            ("list all", "lists all available modules"),
                            ("set", "sets options for the search"),
                            ("get", "downloads the malware"),
                            ("update-db", "updates the databse"),
                            ("back", "removes currently chosen malware"),
                            ("help", "displays this help..."),
                            ("exit", "exits...")]

        self.searchmeth = [ ("arch","which architecture etc; x86, x64, arm7 so on..."),
                            ("plat","platform: win32, win64, mac, android so on..."),
                            ("lang","c, cpp, vbs, bin so on..."),
                            ("vip", "1 or 0")]

        self.modules = self.GetPayloads()

        #print 'im at init'
        self.plat = ''
        self.arch = ''
        self.lang = ''
        self.type = ''
        self.vip = ''

    def GetPayloads(self):
        m = []
        csvReader = csv.reader(open(globals.vars.main_csv_file, 'rb'), delimiter=',')
        for row in csvReader:
            m.append(row)
        return m

    def MainMenu(self):
        if len(self.currentmodule) > 0:
            g = int(self.currentmodule) - 1
            just_print = self.modules[int(g)][int(globals.vars.column_for_name)]
            cmd = raw_input(
                globals.bcolors.GREEN + 'mdb ' + globals.bcolors.RED + str(just_print) + globals.bcolors.GREEN + '#> ' + globals.bcolors.WHITE).strip()
        else:
            cmd = raw_input(globals.bcolors.GREEN + 'mdb ' + globals.bcolors.GREEN + '#> ' + globals.bcolors.WHITE).strip()

        try:
            while cmd == "":
                #print 'no cmd'
                self.MainMenu()

            if cmd == 'help':
                print " Available commands:\n"
                for (cmd, desc) in self.commands:
                    print "\t%s\t%s" % ('{0: <12}'.format(cmd), desc)
                print ''
                self.MainMenu()

            if cmd == 'search':
                ar = self.modules
                manySearch = manysearches.MuchSearch()

                # function to sort by arch
                if len(self.arch) > 0:
                    ar = manySearch.sort(ar, globals.vars.column_for_arch, self.arch)
                # function to sort by plat
                if len(self.plat) > 0:
                    ar = manySearch.sort(ar, globals.vars.column_for_plat, self.plat)
                # function to sort by lang
                if len(self.lang) > 0:
                    ar = manySearch.sort(ar, globals.vars.column_for_pl, self.lang)
                if len(self.type) > 0:
                    ar = manySearch.sort(ar, globals.vars.column_for_type, self.type)
                if len(self.vip) > 0:
                    ar = manySearch.sort(ar, globals.vars.column_for_vip, self.vip)
                printController = manysearches.MuchSearch()
                printController.PrintPayloads(ar)
                self.MainMenu()

            if re.match('^set', cmd):
                try:
                    cmd = re.split('\s+', cmd)
                    print cmd[1] + ' => ' + cmd[2]
                    if cmd[1] == 'arch':
                        self.arch = cmd[2]
                    if cmd[1] == 'plat':
                        self.plat = cmd[2]
                    if cmd[1] == 'lang':
                        self.lang = cmd[2]
                    if cmd[1] == 'type':
                        self.type = cmd[2]
                except:
                    print 'Need to use the set method with two arguments.'
                cmd = ''
                self.MainMenu()

            if cmd == 'show':
                if len(self.currentmodule) == 0:
                    print "No modules have been chosen. Use 'use' command."
                if len(self.currentmodule) > 0:
                    print 'Currently selected Module: ' + self.currentmodule
                print '\tarch => ' + str(self.arch)
                print '\tplat => ' + str(self.plat)
                print '\tlang => ' + str(self.lang)
                print '\ttype => ' + str(self.type)
                print ''
                self.MainMenu()

            if cmd == 'exit':
                sys.exit(1)

            if cmd == 'update-db':
                updateHandler = Updater()
                updateHandler.get_maldb_ver()
                self.MainMenu()

            if cmd == 'get':
                updateHandler = Updater()
                try:
                    updateHandler.get_malware(self.currentmodule, self.modules)
                    self.MainMenu()
                except:
                    print globals.bcolors.RED + '[-]' + globals.bcolors.WHITE + 'Error getting malware.'
                    self.MainMenu()

            if re.match('^use', cmd):
                try:
                    cmd = re.split('\s+', cmd)
                    self.currentmodule = cmd[1]
                    cmd = ''
                except:
                    print 'The use method needs an argument.'
                self.MainMenu()

            if cmd == 'back':
                print 'im at back - WTF?'
                self.arch = ''
                self.plat = ''
                self.lang = ''
                self.type = ''
                self.currentmodule = ''
                self.MainMenu()

            if cmd == 'list all':
                print "\nAvailable Payloads:"
                array = self.modules
                i = 0
                print "ID\tName\tType"
                print '-----------------'
                for element in array:
                    answer = array[i][globals.vars.column_for_uid]
                    answer += '\t%s' % ('{0: <12}'.format(array[i][globals.vars.column_for_name]))
                    answer += '\t%s' % ('{0: <12}'.format(array[i][globals.vars.column_for_type]))
                    print answer
                    i=i+1
                self.MainMenu()

            if cmd == 'quit':
                print ":("
                sys.exit(1)

        except KeyboardInterrupt:
            print ("i'll just go now...")
            sys.exit()

########NEW FILE########
__FILENAME__ = updatehandler
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5Fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys
import urllib2
from imports import globals


class Updater:

    def get_maldb_ver(self):
        try:
            with file(globals.vars.maldb_ver_file) as f:
                return f.read()
        except IOError:
            print("No malware DB version file found.\nPlease try to git clone the repository again.\n")
            return 0

    def update_db(self):
        try:
            with file(globals.vars.maldb_ver_file) as f:
                f = f.read()
        except IOError:
            print("No malware DB version file found.\nPlease try to git clone the repository again.\n")
            return 0

        curr_maldb_ver = f
        response = urllib2.urlopen(globals.vars.giturl+ globals.vars.maldb_ver_file)
        new_maldb_ver = response.read()
        if new_maldb_ver == curr_maldb_ver:
            print globals.bcolors.GREEN + '[+]' + globals.bcolors.WHITE + " No need for an update.\n" + globals.bcolors.GREEN + '[+]' + globals.bcolors.WHITE + " You are at " + new_maldb_ver + " which is the latest version."
            sys.exit(1)
        # Write the new DB version into the file
        f = open(globals.vars.maldb_ver_file, 'w')
        f.write(new_maldb_ver)
        f.close()

        # Get the new CSV and update it
        csvurl = globals.vars.giturl + globals.vars.main_csv_file
        u = urllib2.urlopen(csvurl)
        f = open(globals.vars.main_csv_file, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (globals.vars.main_csv_file, file_size)
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
        print status,
        f.close()

    def get_malware(self, id, allmal):
        #get mal location
        loc = allmal[id][globals.vars.column_for_location]
        #concat with location
        ziploc = globals.vars.giturl + '/' + loc + '.zip'
        passloc = globals.vars.giturl + '/' + loc + '.pass'
        #get from git
        u = urllib2.urlopen(ziploc)
        f = open(id+'zip', 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (loc, file_size)
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
        print status,
        f.close()

        #get pass from git
        u = urllib2.urlopen(passloc)
        f = open(id+'pass', 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (loc, file_size)
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
        print status,
        f.close()
        #alert ready

########NEW FILE########
__FILENAME__ = malware-db
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5Fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.
from imports import muchmuchstrings

__version__ = "0.5.0 Citadel"
__codename__ = "Citadel"
__appname__ = "theZoo"
__authors__ = ["Yuval Nativ","Lahad Ludar","5Fingers"]
__licensev__ = "GPL v3.0"
__maintainer = "Yuval Nativ"
__status__ = "Beta"

import sys
import getopt
import csv
import os
from optparse import OptionParser
from imports.updatehandler import Updater
from imports.eula_handler import EULA
from imports.globals import vars
from imports.terminal_handler import Controller


def main():

    # Much much imports :)
    updateHandler = Updater
    eulaHandler = EULA()
    bannerHandler = muchmuchstrings.banners()
    terminalHandler = Controller()


    def checkresults(array):
        if len(array) == 0:
            print "No results found\n\n"
            sys.exit(1)

    def checkargs():
        print "Type: " + type_of_mal
        print "Lang: " + pl
        print "Search: " + search

    def filter_array(array, colum, value):
        ret_array = [row for row in array if value in row[colum]]
        return ret_array

    def print_results(array):
        # print_results will suprisingly print the results...
        answer = array[vars.column_for_uid] + "\t" + array[vars.column_for_name]+ "\t" + array[vars.column_for_version] + "\t\t"
        answer += array[vars.column_for_location] + "\t\t" + array[vars.colomn_for_time]
        print answer

    def getArgvs():
        parser = OptionParser()
        parser = OptionParser()
        parser.add_option("-t", "--type", dest="type_of_mal", default='', help="Type of malware to search. \nFor example botnet,trojan,virus,etc...")
        parser.add_option("-l", "--language", dest="lang_of_mal", default='', help="Language of the version of the malware which is in the databse.\nFor example: vbs,vb,c,cpp,bin,etc...")
        parser.add_option("-a", "--architecture", dest="arch_of_mal", default='', help="The architecture the malware is intended for.\nFor example: x86,x64,arm7,etc...")
        parser.add_option("-p", "--platform", dest="plat_of_mal", default="", help="Platform the malware is inteded for.\nFor example: win32,win64,ios,android,etc...")
        parser.add_option("-u", "--update", dest="update_bol", default=0, help="Updates the DB of theZoo.", action="store_true")
        parser.add_option("-v", "--version" , dest="ver_bol", default=0, help="Shows version and licensing information.", action="store_true")
        parser.add_option("-w", "--license", dest="license_bol", default=0, help="Prints the GPLv3 license information.", action="store_true")
        (options, args) = parser.parse_args()
        return options


    # Here actually starts Main()

    # Zeroing everything
    type_of_mal = ""
    pl = ""
    search = ""
    new = ""
    update = 0
    m = [];
    f = ""

    arguments = getArgvs()

    # Checking for EULA Agreement
    a = eulaHandler.check_eula_file()
    if a == 0:
        eulaHandler.prompt_eula()

    # Get arguments
    
    # Check if update flag is on
    if arguments.update_bol == 1:
        a = Updater()
        a.update_db()
        sys.exit(1)

    # Check if version flag is on
    if arguments.ver_bol == 1:
        print vars.maldb_banner
        sys.exit(1)

    # Check if license flag is on
    if arguments.license_bol == 1:
        bannerHandler.print_license()
        sys.exit(1)

    if ((len(arguments.type_of_mal) > 0) or (len(arguments.arch_of_mal) > 0) or (len(arguments.lang_of_mal) > 0) or (len(arguments.plat_of_mal) > 0)):

        # Take index.csv and convert into array m
        csvReader = csv.reader(open(vars.main_csv_file, 'rb'), delimiter=',')
        for row in csvReader:
            m.append(row)

        # Filter by type
        if len(arguments.type_of_mal) > 0:
            m = filter_array(m, vars.column_for_type, arguments.type_of_mal)

        # Filter by programming language
        if len(arguments.lang_of_mal) > 0:
            m = filter_array(m, vars.column_for_plat, arguments.lang_of_mal)

        # Filter by architecture
        if len(arguments.arch_of_mal) > 0:
            m = filter_array(m, vars.column_for_arch, arguments.arch_of_mal)

        # Filter by Platform
        if len(arguments.plat_of_mal) > 0:
            m = filter_array(m, vars.column_for_plat, arguments.plat_of_mal)

        i=0
        print vars.maldb_banner
        print 'ID\tName\t\tType\t\tVersion\t\tLanguage'
        print '--\t----\t\t----\t\t-------\t\t--------'
        for g in m:
            #print 'now'
            answer = m[i][vars.column_for_uid]
            answer += '\t%s' % ('{0: <12}'.format(m[i][vars.column_for_name]))
            answer += '\t%s' % ('{0: <12}'.format(m[i][vars.column_for_type]))
            answer += '\t%s' % ('{0: <12}'.format(m[i][vars.column_for_version]))
            answer += '\t%s' % ('{0: <12}'.format(m[i][vars.column_for_pl]))
            print answer
            i=i+1

        sys.exit(1)

    # Initiate normal run. No arguments given. 
    os.system('clear')
    print vars.maldb_banner
    while 1:
        terminalHandler.MainMenu()
    sys.exit(1)


if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = maldb_0.2
#!/usr/bin/env python

    #Malware DB - the most awesome free malware database on the air
    #Copyright (C) 2014, Yuval Nativ, Lahad Ludar, 5fingers

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "0.2 Beta"
__appname__ = "Malware DB"
__authors__ = ["Yuval Nativ","Lahad Ludar","5fingers"]
__licensev__ = "GPL v3.0"
__maintainer__ = "Yuval Nativ"
__status__ = "Development"

import sys
import getopt
import subprocess
import csv
import urllib2
# import git
#import os
#import inspect


def main():

    # Set general variables.
    version = __version__
    appname = __appname__
    licensev = __licensev__
    authors = "Yuval Nativ, Lahad Ludar, 5fingers"
    fulllicense = appname + " Copyright (C) 2014 " + authors + "\n"
    fulllicense += "This program comes with ABSOLUTELY NO WARRANTY; for details type '" + sys.argv[0] +" -w'.\n"
    fulllicense += "This is free software, and you are welcome to redistribute it."

    useage='\nUsage: ' + sys.argv[0] +  ' -s search_query -t trojan -p vb\n\n'
    useage += 'The search engine can search by regular search or using specified arguments:\n\nOPTIONS:\n   -h  --help\t\tShow this message\n   -t  --type\t\tMalware type, can be virus/trojan/botnet/spyware/ransomeware.\n   -p  --language\tProgramming language, can be c/cpp/vb/asm/bin/java.\n   -u  --update\t\tUpdate malware index. Rebuilds main CSV file. \n   -s  --search\t\tSearch query for name or anything. \n   -v  --version\tPrint the version information.\n   -w\t\t\tPrint GNU license.\n'

    column_for_pl = 6
    column_for_type = 2
    column_for_location = 1
    colomn_for_time = 7
    column_for_version = 4
    column_for_name = 3
    column_for_uid = 0
    column_for_arch = 8
    column_for_plat = 9
    conf_folder = 'conf'
    eula_file = conf_folder + '/eula_run.conf'
    maldb_ver_file = conf_folder + '/db.ver'
    main_csv_file = conf_folder + '/index.csv'
    giturl = 'https://raw.github.com/ytisf/theZoo/master/'

    # Function to print license of malware-db
    def print_license():
        print ""
        print fulllicense
        print ""

    # Check if EULA file has been created
    def check_eula_file():
        try:
            with open(eula_file):
                return 1
        except IOError:
                return 0

    def get_maldb_ver():
        try:
            with file(maldb_ver_file) as f:
                return f.read()
        except IOError:
            print("No malware DB version file found.\nPlease try to git clone the repository again.\n")
            return 0

    def update_db():
        curr_maldb_ver = get_maldb_ver()
        response = urllib2.urlopen(giturl+maldb_ver_file)
        new_maldb_ver = response.read()
        if new_maldb_ver == curr_maldb_ver:
            print "No need for an update.\nYou are at " + new_maldb_ver + " which is the latest version."
            sys.exit(1)
        # Write the new DB version into the file
        f = open(maldb_ver_file, 'w')
        f.write(new_maldb_ver)
        f.close()

        # Get the new CSV and update it
        csvurl = giturl + main_csv_file
        u = urllib2.urlopen(csvurl)
        f = open(main_csv_file, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (main_csv_file, file_size)
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
        print status,
        f.close()

    # prints version banner on screen
    def versionbanner():
        print ""
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print "\t\t    " + appname + ' v' + version
        print "Built by:\t\t" + authors
        print "Is licensed under:\t" + licensev
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print fulllicense
        print useage

    # Check if maybe no results have been found
    def checkresults(array):
        if len(array) == 0:
            print "No results found\n\n"
            sys.exit(1)

    # Check to needed arguments - left for debugging
    def checkargs():
        print "Type: " + type_of_mal
        print "Lang: " + pl
        print "Search: " + search

    # Sort arrays
    def filter_array(array,colum,value):
        ret_array = [row for row in array if value in row[colum]]
        return ret_array

    # A function to print banner header
    def res_banner():
        print "\nUID\tName\t\tVersion\t\tLocation\t\tTime"
        print "---\t----\t\t-------\t\t--------\t\t----"

    # print_results will surprisingly print the results...
    def print_results(array):
        answer = array[column_for_uid] + "\t" + array[column_for_name]+ "\t" + array[column_for_version] + "\t\t"
        answer += array[column_for_location] + "\t\t" + array[colomn_for_time]
        print answer

    options, remainder = getopt.getopt(sys.argv[1:], 'hwuvs:p:t:', ['type=', 'language=', 'search=', 'help', 'update', 'version', 'dbv' ])

    # Zeroing everything
    type_of_mal = ""
    pl = ""
    search = ""
    new =""
    update=0
    m=[];
    a=0
    eula_answer='no'
    f = ""

    # Checking for EULA Agreement
    a = check_eula_file()
    if a == 0:
        print appname + ' v' + version
        print 'This program contain live and dangerous malware files'
        print 'This program is intended to be used only for malware analysis and research'
        print 'and by agreeing the EULA you agree to only use it for legal purposes and '
        print 'studying malware.'
        print 'You understand that these file are dangerous and should only be run on VMs'
        print 'you can control and know how to handle. Running them on a live system will'
        print 'infect you machines will live and dangerous malwares!.'
        print ''
        eula_answer = raw_input('Type YES in captial letters to accept this EULA.\n')
        if eula_answer == 'YES':
            print 'you types YES'
            new = open(eula_file, 'a')
            new.write(eula_answer)
        else:
            print 'You need to accept the EULA.\nExiting the program.'
            sys.exit(1)

    # Get arguments
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print fulllicense
            print useage
            sys.exit(1)
        elif opt in ('-u', '--update'):
            update=1
            update_db()
        elif opt in ('-v', '--version'):
            versionbanner()
            sys.exit(1)
        elif opt in '-w':
            print_license()
            sys.exit(1)
        elif opt in ('-t', '--type'):
            type_of_mal = arg
        elif opt in ('-p', '--language'):
            pl = arg
        elif opt in ('-s', '--search'):
            search = arg
        elif opt in '--dbv':
            # Getting version of malware-DB's database
            a = get_maldb_ver()
            if a == 0:
                sys.exit(0)
            elif len(a) > 0:
                print ''
                print "Malware-DB Database's version is: " + a
                sys.exit()

    # Rebuild CSV
    if update == 1:
        subprocess.call("./Rebuild_CSV.sh", shell=True)
        sys.exit(1)

    # Take index.csv and convert into array m
    csvReader = csv.reader(open(main_csv_file, 'rb'), delimiter=',');
    for row in csvReader:
        m.append(row)

    # Filter by type
    if len(type_of_mal) > 0:
        m = filter_array(m,column_for_type,type_of_mal)

    # Filter by programming language
    if len(pl) > 0:
        m = filter_array(m,column_for_pl,pl)

    # Free search handler
    if len(search) > 0:
        res_banner()
        matching = [y for y in m if search in y]
        for line in matching:
            checkresults(matching)
            print_results(line)

    if len(search) <= 0:
        res_banner()
        for line in m:
            print_results(line)

if __name__ == "__main__":
    main()
########NEW FILE########
