__FILENAME__ = ccui
'''GTK User Interface code for ClearCutter'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


import gtk, gtk.glade, pygtk

class ClearCutterUI:
    """ClearCutter GTK frontend"""

    gladefile = ""
    wTree = ""
    def __init__(self):
        
        self.wTree = gtk.glade.XML("ccui.glade") 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)


if __name__ == "__main__":
    hwg = ClearCutterUI()
    gtk.main()
########NEW FILE########
__FILENAME__ = commonvars
'''
Common Variables in System Logs, identified via Regex

Add extra variable pattern regex's here
'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


import re

SECTIONS_NOT_RULES = ["config", "info", "translation"]

#BUG: [MAC] regexp doesn't catch addrs with trailing colon

aliases = {
    '[IPV4]' :"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    '[IPV6_MAP]' : "::ffff:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    '[MAC]' : "\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}",
    '[HOSTNAME]' : "((([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)([a-zA-Z])+)",
    '[TIME]' : "\d\d:\d\d:\d\d",
    '[SYSLOG_DATE]' : "\w{3}\s+\d{1,2}\s\d\d:\d\d:\d\d",
    '[SYSLOG_DATE_SHORT]' : "\w+\s+\d{1,2}\s\d\d:\d\d:\d\d\s\d{4}",
    '[SYSLOG_WY_DATE]' : "\S+\s\w+\s+\d{1,2}\s\d\d:\d\d:\d\d\s\d{4}",
    '"[QUOTED STRING]"' : "\".*\"",
    '[NUMBER]' : "\s\d+{2:}\s"

    #TODO: URI
    #TODO: user@hostname
    #TODO Hexademical Number
    }

DefaultDirectives = [
        "regexp",
        "precheck",
        "event_type",
        "type",
        "date",
        "sensor",
        "interface",
        "plugin_id",
        "plugin_sid",
        "priority",
        "protocol",
        "src_ip",
        "src_port",
        "dst_ip",
        "dst_port",
        "username",
        "password",
        "filename",
        "userdata1",
        "userdata2",
        "userdata3",
        "userdata4",
        "userdata5",
        "userdata6",
        "userdata7",
        "userdata8",
        "userdata9",
        "occurrences",
        "log",
        "data",
        "snort_sid",
        "snort_cid",
        "fdate",
        "tzone",
        "ctx",
        "sensor_id",
        ]


def FindCommonRegex(teststring):
        """
        Test the string against a list of regexs for common data types, and return a placeholder for that datatype if found
        """
        #aliases['PORT']="\d{1,5}"

        
        returnstring = teststring
        replacements = aliases.keys()
        replacements.sort()
        for regmap in replacements:
                p = re.compile(aliases[regmap])
                returnstring = p.sub(regmap, returnstring)
        return returnstring
    

########NEW FILE########
__FILENAME__ = levenshtein
'''Levenshtein Distance Calculator for Clearcutter log identification module'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


def levenshtein(s1, s2):
    l1 = len(s1)
    l2 = len(s2)

    matrix = [range(l1 + 1)] * (l2 + 1)
    for zz in range(l2 + 1):
        matrix[zz] = range(zz, zz + l1 + 1)
    for zz in range(0, l2):
        for sz in range(0, l1):
            if s1[sz] == s2[zz]:
                matrix[zz + 1][sz + 1] = min(matrix[zz + 1][sz] + 1, matrix[zz][sz + 1] + 1, matrix[zz][sz])
            else:
                matrix[zz + 1][sz + 1] = min(matrix[zz + 1][sz] + 1, matrix[zz][sz + 1] + 1, matrix[zz][sz] + 1)
    return matrix[l2][l1]
        

########NEW FILE########
__FILENAME__ = logcodescrape
'''Extract calls to logging libraries from code Trees'''

class CodeScrape(object):
    '''
    classdocs
    '''


    def __init__(self,params):
        '''
        Constructor
        '''
        pass
    
    
########NEW FILE########
__FILENAME__ = logfile
'''Shared LogFile Class for Clearcutter Functions'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"

#TODO: Add transparent support and normalization for multiple log file formats
#TODO: Add remote retrieval of logs? perhaps from DB sources

import os, sys

class LogFile(object):
    '''
    Log File object with a few helper functions for other clearcutter modes
    '''    
    _filedata = ""
    Filename = ""
    Length = 0
    Position = 0
    
    def __init__(self, filename, verbose=False, memory=True):
        self.Filename = filename
        try:
            self.Length = os.path.getsize(filename)
        except IOError:  #problem loading file
            print "Could not open log file : " + filename + " - " + sys.exc_info()[2]
            sys.exit()
        
        if (memory == True and self.Length < 2147483648):
            if verbose == True: print "Loading file into RAM"
            filehandle = open(filename, 'r')            
            self._filedata = filehandle.readlines()
        else:
            if verbose == True: print "Reading from Disk"
            self._filedata = open(filename, 'r')
            
        try:             
            if verbose == True : print "Using File: " + filename
            self._filedata = open(filename, 'r')
        except ValueError:
            if verbose == True : print "Invalid Filename: " + sys.exc_info()[2]
            raise sys.exc_info()
        except IOError:
            if verbose == True : print "File Access Error: " + sys.exc_info()[2]
            raise sys.exc_info()
        self.Length = os.path.getsize(filename)
    
    def RetrieveCurrentLine(self, verbose=False):
        self.Position = self._filedata.tell()        
        return self._filedata.readline() #Fix for in-memory
        
########NEW FILE########
__FILENAME__ = logidentify
"""
Clusters Locate clusters of test in Logfiles, to assist in processing discrete log messages,
from any given log data sample and assist in the creation of Regular Expression to parse those log entries
"""

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.2"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


#TODO: More Regexp Patterns
#TODO: Levenshtein distance grouping (recurse window groupings

#TODO: Extract all unique words from a file
#cat comment_file.txt | tr " " "\n" | sort | uniq -c

#TODO: Print total matches for each identified log entry.


import sys, progressbar, commonvars, levenshtein, plugingenerate
from logfile import LogFile


class ClusterNode(object):
    """
    Linked list node for log patterns
    """

    Children = []
    Content = ""
    Parent = None
    ContentHash = ""
    
    
    def __init__(self, NodeContent="Not Provided"):
        self.Children = []
        self.Content = NodeContent
        #if verbose > 3 : print "Created new Node " + str(id(self)) + " with content : " + self.Content      
        self.ContentHash = hash(NodeContent)
    

    def GetChildren(self):
        return self.Children
    

    def GetContent(self):
        return self.Content


    def MatchChild(self, MatchContent):
        if len(self.Children) == 0:
            #print "No Children"
            return None
        else:
            for child in self.Children:
                if (child.ContentHash == hash(MatchContent)):
                    #print "Found Child Match : " + child.Content
                    return child
                else:
                    return None

              
    def MatchNephew(self, MatchContent):
        """Find Nephew Match"""
        if self.Parent == None: #This node is the root node
            return None
        for sibling in self.Parent.Children:
            if len(sibling.Children) > 0 :  # no point if sibling has no children
                for child in sibling.Children: #let's see which child node this matches  
                    if (child.Content == MatchContent):
                        return child
        return None
                    

    def AddChild(self, NodeContent):
        ChildContent = ClusterNode(NodeContent)
        ChildContent.Parent = self
        self.Children.append(ChildContent)
        return ChildContent
    
    def GeneratePath(self):
        #TODO: Compare siblings against regexps to suggest a regex replacement
        currentNode = self
        parentpath = ""
        while currentNode.Content != "ROOTNODE":
            if len(currentNode.Parent.Children) > ClusterGroup.VarThreshold:
                parentpath = "[VARIABLE]" + " " + parentpath
            else:
                parentpath = currentNode.Content + " " + parentpath
            currentNode = currentNode.Parent
        return parentpath

class ClusterGroup(object):
        """
        A Group of word cluster, representing the unique log types within a logfile
        """ 
        
        Args = ""
        Log = ""
        VarThreshold = 10  #How many siblings a string node must have before it is considered to be variable data
        VarDistance = 20
        rootNode = ClusterNode(NodeContent="ROOTNODE")
        entries = []
             
        def __init__(self, args):
                self.rootNode = ClusterNode(NodeContent="ROOTNODE")           
                self.Args = args

        def IsMatch(self, logline):  
                '''
                Test the incoming log line to see if it matches this clustergroup
                Return boolean match
                '''
                logwords = commonvars.FindCommonRegex(logline).split()
                
                #TODO Split at '=' marks as well
                
                currentNode = self.rootNode 
                for logword in logwords: #process logs a word at a time            
                        #match our own children first
                        match = currentNode.MatchChild(MatchContent=logword)

                        if match == None: #then try our siblings
                                match = currentNode.MatchNephew(MatchContent=logword)
                        if match == None:  #then add a new child
                                match = currentNode.AddChild(NodeContent=logword)

                        if match == None:
                                print "FAILED"    
                        else:
                                currentNode = match


        def IsEndNode(self, Node):
                '''
                Is This Node the final word of a log template?
                
                @return: True or False
                '''
                endnode = False
                hasNephews = False
                if (len(Node.Children) is 0):  #I'm an EndNode for a log wording cluster    
                        if Node.Parent is not None: #let's make sure our siblings are all endnodes too, and this is really var data                
                                for sibling in Node.Parent.Children:
                                        if len(sibling.Children) > 0 : 
                                                hasNephews = True 
                                if (hasNephews is False) and (len(Node.Parent.Children) >= ClusterGroup.VarThreshold):  #log event ends in a variable 
                                        endnode = True
                                if (hasNephews is False) and (len(Node.Parent.Children) == 1) : #log event ends in a fixed string
                                        endnode = True
                if endnode is True:
                        entry = Node.GeneratePath()
                        if entry not in self.entries: 
                                self.entries.append(entry)
                

        def BuildResultsTree(self, node):
                '''
                Recurse through the Node Tree, identifying and printing complete log patterns'
                
                @return: None (recursive function)
                '''
                if self.IsEndNode(node) == True : return None # no children so back up a level
                for childnode in node.Children:
                        self.BuildResultsTree(childnode)


        def Results(self):
                '''
                Display all identified unique log event types
                
                @return None
                '''
                #if options.outfile == true: dump to file 
                print "\n========== Potential Unique Log Events ==========\n"
                self.BuildResultsTree(self.rootNode)
                                    
                #Todo - commandline args to toggle levenshtein identification of dupes
                
                previous = ''          
                for entry in self.entries:
                    if levenshtein.levenshtein(entry, previous) < ClusterGroup.VarDistance : 
                        print "\t" + entry
                    else:
                        print entry
                    previous = entry
                
        def Run(self):
                try:
                    self.Log = LogFile(self.Args.logfile)
                except IOError:
                    print "File: " + self.Log.Filename + " cannot be opened : " + str(sys.exc_info()[1])
                    #TODO: log to stderr
                    raise IOError()
                #if args.v > 0 : print "Processing Log File "  + log.Filename + ":" + str(log.Length) + " bytes" 
                logline = self.Log.RetrieveCurrentLine() 
                widgets = ['Processing potential messages: ', progressbar.Percentage(), ' ', progressbar.Bar(marker=progressbar.RotatingMarker()), ' ', progressbar.ETA()]
                if self.Args.quiet is False : pbar = progressbar.ProgressBar(widgets=widgets, maxval=100).start()
                while logline != "": #TODO: Make this actually exit on EOF
                    self.IsMatch(logline)
                    if self.Args.quiet is False : pbar.update((1.0 * self.Log.Position / self.Log.Length) * 100)
                    logline = self.Log.RetrieveCurrentLine()
                    
                if self.Args.quiet is False : pbar.finish()
        
        def GenPlugin(self):
            '''
            Create a Template OSSIM agent plugin file using the identified log templates as SIDs
            
            @return: The filename of the generated plugin
            '''
            generator = plugingenerate.Generator(self.entries)
            generator.WritePlugin()
            return generator.PluginFile
            
#Take EndNode Strings
#Calculate Levenshtein distance between them
#Deduplicate from there.




########NEW FILE########
__FILENAME__ = logsequence
'''Identifies sequences of log messages that indicate a single thread of action'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


# Find sequences in log events
# by event id (SID) or by threading variables

# Take Variable Fields and follow them through a thread of messages

# great for giving analysts the full sequencing of things, especially for writing rules.


class LogSequence(object):
    '''A Behavioral Sequence of Log Events'''
    def __init__(self):
        pass
    
    
    
class SequenceEntry(object):
    '''A particular log Event in a behavioral Sequence of Log Events'''
    def __init__(self):
        pass
    

########NEW FILE########
__FILENAME__ = logvars
'''
Tracks variables identified in log samples
'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.2"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"

class EntryVars(object):
    ''' A collection of variable values for a given log entry type'''
    def __init__(self):
        pass
    

########NEW FILE########
__FILENAME__ = logwords

class Logwords(object):
    '''
    Extract Unique words from a logfile
    
    Group them by the Regexp Match they fit.
    
    Mask out stuff like Syslog Dates first..
    
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        
        
    def ExtractUniques(self):
        pass
    
    
    def GroupToRegex(self):
        pass
    
    
    
########NEW FILE########
__FILENAME__ = plugingenerate
'''OSSIM detector plugin config file generation code for ClearCutter'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"

from ConfigParser import ConfigParser
import commonvars


class Generator(object):
    '''
    Creates an OSSIM collector plugin .cfg file
    '''

    SIDs = ''

    Plugin = ConfigParser()

    PluginFile = "testplugin.cfg"

    def __init__(self, entries):
        '''
        Build a new Plugin Generator
        '''
        #self.SIDs = entries
        #self.Plugin.add_section("DEFAULT")
        #self.Plugin.add_section("config")
        for SID in entries:
            
            
            self.Plugin.add_section(SID)
            self.Plugin.set(SID, "regexp", SID)
            options = commonvars.DefaultDirectives
            options.remove('regexp') #this is added later
            for directive in options:
                self.Plugin.set(SID, directive, "")

        
    def WritePlugin(self):
        outfile = open(self.PluginFile, "w")
        self.Plugin.write(outfile) 

    def WriteSQL(self):
        pass
    
        
        


########NEW FILE########
__FILENAME__ = pluginparse
'''OSSIM Plugin Test-Run parsing code
Simulates loading a plugin into OSSIM and parsing sample log data.

For testing plugins before loading into OSSIM, and simulating the log parsing process and results

'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine", "Dominique Karg"]
__version__ = "0.2"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


#TODO: duplicate entire plugin parsing to validate good plugin file and field assignment
#TODO: Identify plugin section that contains bad regexp

#TODO: Implement precheck

import sys, re, ConfigParser, pluginvalidate, commonvars

class ParsePlugin(object):
    """Processes Log Data against a list of regular expressions, possibly read from an OSSIM collector plugin"""
    
    #Commandline Options
    Args = ''
    
    #File containing regexps
    Plugin = ''
    
    #extracted regexps from file
    #regexps = {}

    SIDs = {}
    
    Log = ''
    
    sorted_ = {}
    rule_stats = []
    rule_precheck_stats = []
    
    line_match = 0

    #Common Log patterns, as used in OSSIM
    aliases = {
               'IPV4' :"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
               'IPV6_MAP' : "::ffff:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
               'MAC': "\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}",
               'PORT': "\d{1,5}",
               'HOSTNAME' : "((([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)([a-zA-Z])+)",
               'TIME' : "\d\d:\d\d:\d\d",
               'SYSLOG_DATE' : "\w{3}\s+\d{1,2}\s\d\d:\d\d:\d\d",
               'SYSLOG_WY_DATE' : "\w+\s+\d{1,2}\s\d{4}\s\d\d:\d\d:\d\d",
              }

    def __init__(self, args):
        self.Args = args
        self.LoadPlugin()
        
    def hitems(self, config, section):
        itemhash = {}
        for item in config.items(section):
            itemhash[item[0]] = self._strip_value(item[1])
        return itemhash
    
    def _strip_value(self, value):
        from string import strip
        return strip(strip(value, '"'), "'")
    
    def get_entry(self, config, section, option):
        value = config.get(section, option)
        value = self._strip_value(value)
        return value

   
    def LoadPlugin(self):
        try:
            self.Plugin = ConfigParser.RawConfigParser()
            self.Plugin.read(self.Args.plugin)
        except ConfigParser.MissingSectionHeaderError:
            print self.Args.plugin + " Is not an OSSIM plugin file"
            sys.exit()
        
        for rule in self.Plugin.sections():
            if rule.lower() not in commonvars.SECTIONS_NOT_RULES :
                self.SIDs[rule] = self.Plugin.get(rule, 'regexp')
        
        validator = pluginvalidate.PluginValidator(self.Plugin)
        if validator.IsValid() == False: sys.exit()

    
    def ParseLogWithPlugin(self):
        '''Process a logfile according to SID entries in an OSSIM collector plugin'''
        keys = self.SIDs.keys()
        keys.sort()
        for line in self.Log:
            matched = False
            for rulename in keys:
                #match the line with precheck first
                if self.Args.precheck is True:
                    try:
                        precheck = self.get_entry(self.Plugin, rulename, 'precheck')
                        if precheck in line:
                            self.rule_precheck_stats.append(str(rulename))
                    except ConfigParser.NoOptionError:
                        pass
                
                
                regexp = self.get_entry(self.Plugin, rulename, 'regexp')
                if regexp is "":
                    continue
                # Replace vars
                for alias in self.aliases:
                    tmp_al = ""
                    tmp_al = "\\" + alias;
                    regexp = regexp.replace(tmp_al, ParsePlugin.aliases[alias])
                result = re.findall(regexp, line)
                try:
                    tmp = result[0]
                except IndexError:
                    continue
                # Matched
                matched = True

                if self.Args.quiet is False:
                    print "Matched using %s" % rulename
                if self.Args.verbose > 0:
                    print line
                if self.Args.verbose > 2:
                    print regexp
                    print line
                #TODO: Implement label Extraction
                #try:
                #    if self.Args.group != '':  #Change this to print positional
                #        print "Match $%d: %s" % (int(sys.argv[3]),tmp[int(sys.argv[3])-1])
                #    else:
                #        if self.Args.quiet == False:
                #            print result
                #except ValueError:
                #    if self.Args.quiet is False:
                #        print result
                # Do not match more rules for this line
                self.rule_stats.append(str(rulename))
                self.matched += 1
                break
            if matched is False and self.Args.nomatch is True:
                print 'NOT MATCHED: ' + line

    
               

    def Run(self):
        f = open(self.Args.logfile, 'r')   #REPLACE WITH ARGS 
        self.Log = f.readlines()
        self.line_match = 0    
        self.matched = 0
        self.ParseLogWithPlugin()


    def PrintResults(self):
        for key in self.SIDs:
            print "Rule: \t%s\n\t\t\t\t\t\tMatched %d times by Regexp" % (str(key), self.rule_stats.count(str(key)))
            if self.Args.precheck is True:
                print "\t\t\t\t\t\tMatched %d times by Precheck" % (self.rule_precheck_stats.count(str(key)))
   
        print "Counted", len(self.Log), "lines."
        print "Matched", self.matched, "lines."
     
    
                
########NEW FILE########
__FILENAME__ = pluginprofiler
'''Plugin Performance profiling module for ClearCutter

Loads an OSSIM plugin and sample log data, and identifies the CPU cost for each SID in a plugin
as a percentage of total runtime to process the entire file
'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.1"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"


import cProfile, pstats, re

logdata = ''
aliases = {
           'IPV4' :"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
           'IPV6_MAP' : "::ffff:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
           'MAC': "\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}:\w{1,2}",
           'PORT': "\d{1,5}",
           'HOSTNAME' : "((([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)([a-zA-Z])+)",
           'TIME' : "\d\d:\d\d:\d\d",
           'SYSLOG_DATE' : "\w{3}\s+\d{1,2}\s\d\d:\d\d:\d\d",
           'SYSLOG_WY_DATE' : "\w+\s+\d{1,2}\s\d{4}\s\d\d:\d\d:\d\d",
          }

def __init__(self, log):
    self.logdata = open(log, 'r').readlines()

def ProfileRegexp(self, regexp):
    cProfile.run('self.Profilewrap(regexp)', 'profiler.out')
    profstats = pstats.Stats('profiler.out')
    profstats.print_stats()

def ProfileWrap(self, regexp):
    for line in self.logdata:
        for alias in self.aliases:
            tmp_al = ""
            tmp_al = "\\" + alias;
            regexp = regexp.replace(tmp_al, self.aliases[alias])
        result = re.findall(regexp, line)
        try:
            tmp = result[0]
        except IndexError:
            continue
    
      


########NEW FILE########
__FILENAME__ = pluginvalidate
'''
Validates that an OSSIM plugin contains no syntactic errors

Displays information helpful to creating an internally-consistent plugin
'''

__author__ = "CP Constantine"
__email__ = "conrad@alienvault.com"
__copyright__ = 'Copyright:Alienvault 2012'
__credits__ = ["Conrad Constantine"]
__version__ = "0.2"
__license__ = "BSD"
__status__ = "Prototype"
__maintainer__ = "CP Constantine"

import ConfigParser, commonvars, re, sys

class PluginValidator(object):
    """
    Locates common errors within an OSSIM plugin
    """
    
    _plugin = ""
    _valid = True
    _sids = []
    _userlabels = {
                   "userdata1" : [],
                   "userdata2" : [],
                   "userdata3" : [],
                   "userdata4" : [],
                   "userdata5" : [],
                   "userdata6" : [],
                   "userdata7" : [],
                   "userdata8" : [],
                   "userdata9" : []
                   }

    SECTIONS_NOT_RULES = ["config", "info", "translation"]
    ESSENTIAL_OPTIONS = ['regexp', 'event_type', 'plugin_sid']
    
    def __init__(self, plugin):
        self._plugin = plugin

    
    def IsValid(self):
        '''Process a plugin .cfg as the OSSIM agent would, noting any malformed or missing directives'''
        
        self.CheckSections()
        self.PrintLabelUsage()
        
        if self._valid is False: print "\nErrors detected in OSSIM Plugin file\n"
        return self._valid 
        # load each SID section
        
        # step through the remaining directives and make sure they're on the list
        # check for directives that end up being empty with the sample logs
        # Identify any labels in the regexp that aren't used in the userdata fields
        # for directive in plugingenerate.DefaultDirectives:
    
    def CheckSections(self):
        '''
        Step through each plugin section and validate contents are correct
        '''
        for rule in self._plugin.sections():
            if rule.lower() not in self.SECTIONS_NOT_RULES :
                self.CheckEssentials(rule)
                self.CheckOptions(rule)
                
    def CheckEssentials(self, section):
        '''
        Check that a plugin section contains the minimum necessary options
        '''
        for essential in self.ESSENTIAL_OPTIONS:
            if essential not in self._plugin.options(section): 
                print "\tsection '" + section + "' has no " + essential + " option!\n"
                self.valid = False
        
    def CheckOptions(self, rule):
        '''
        Iterate through options listed in each section, and test they are valid OSSIM agent options          
        '''

        print "\n-------------------\nProcessing Rule [" + rule + "]"
        
        for option in self._plugin.options(rule):
            if (option not in commonvars.DefaultDirectives):
                print "\tOption '" + option + "' in section '" + rule + "'is invalid"
                self._valid = False
            self.CheckValues(rule, option)

   
    
    def CheckValues(self, rule, option):
        '''
        Validate that the value of an option is properly-formed
        '''

        # check for empty directives        
        if option == 'regexp':
                self.CheckRegexValue(rule)
        
        if option == 'plugin_sid':
                self.CheckDuplicateSID(self._plugin.get(rule, option))
        
        if self._plugin.get(rule, option) is '':
            print "\tOption '" + option + "' has no assigned value"
            self._valid = False

        self.CheckLabelValue(rule, option)
        #TODO: figure out embedded groupnames in strings
        self.CheckUserConsistency(rule, option)

                           
    def CheckRegexValue(self, section):
        """
        Validate that the Regex directive contains a properly-formed Regular Expression
        """
        regex = self._plugin.get(section, 'regexp')
        try:
            re.compile(regex, flags=0)
            return True
        except re.error:
            sys.stdout.write("\tRegular Expression is not valid\n")
            sys.stdout.flush()
            self._valid = False
            return False 
        
    def CheckLabelValue(self, rule, option):
        '''
        Validate that a a regex group used as an directive value, exists in the regex directive
        '''
        group = self._plugin.get(rule, option)
        try:
            testreg = self._plugin.get(rule, 'regexp')
        except ConfigParser.NoOptionError:
            # user will have already been noted there is no such value
            return
        if group.startswith('{$'):  #groupname value
            if group.endswith('}') == False: print "\tmismatched brace in " + option
            group = group.replace('{$', '(?P<')
            group = group.replace('}', '>')  #convert it to regexp syntax
            if group not in testreg:
                print "\tOption '" + option + "' refers to non-existant regexp group '" + group + "'"
                self._valid = False            
    
    def CheckDuplicateSID(self, sid):
        '''
        check that plugin_sid values are not duplicated
        '''
        if sid.startswith("{$"):   #can't vald
            return
        if sid in self._sids:
            print "\tDuplicate plugin_sid value " + sid + " found"
            self._valid = False
        else:
            self._sids.append(sid)


    def CheckUserConsistency(self, rule, option):
        '''
        Collate the Regexp labels used in each UserData field to expose inconsistency to the user
        '''
        if option.lower() in self._userlabels:
            if self._plugin.get(rule, option) in self._userlabels[option]:
                pass   #We've seen this one before
            else:
                self._userlabels[option].append(self._plugin.get(rule, option))
        
        
    
    def PrintLabelUsage(self):
        print "\nThe Following Regex Labels are Assigned to UserData fields"
        udatafields = self._userlabels.keys()
        udatafields.sort()
        for udata in udatafields:
            udataresult = "\t" + udata + "\t" 
            for udataval in self._userlabels[udata]:
                udataresult += str(udataval) + ", "
            print udataresult

########NEW FILE########
__FILENAME__ = progressbar
#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
#
# progressbar  - Text progressbar library for python.
# Copyright (c) 2005 Nilton Volpato
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Text progressbar library for python.

This library provides a text mode progressbar. This is tipically used
to display the progress of a long running operation, providing a
visual clue that processing is underway.

The ProgressBar class manages the progress, and the format of the line
is given by a number of widgets. A widget is an object that may
display diferently depending on the state of the progress. There are
three types of widget:
- a string, which always shows itself;
- a ProgressBarWidget, which may return a diferent value every time
it's update method is called; and
- a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. And
automatically supports features like auto-resizing when available.
"""

__author__ = "Nilton Volpato"
__author_email__ = "first-name dot last-name @ gmail.com"
__date__ = "2006-05-07"
__version__ = "2.2"

# Changelog
#
# 2006-05-07: v2.2 fixed bug in windows
# 2005-12-04: v2.1 autodetect terminal width, added start method
# 2005-12-04: v2.0 everything is now a widget (wow!)
# 2005-12-03: v1.0 rewrite using widgets
# 2005-06-02: v0.5 rewrite
# 2004-??-??: v0.1 first version


import sys, time
from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass
import signal

class ProgressBarWidget(object):
    """This is an element of ProgressBar formatting.

    The ProgressBar object will call it's update value when an update
    is needed. It's size may change between call, but the results will
    not be good if the size changes drastically and repeatedly.
    """
    def update(self, pbar):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made.

        At least this function must be overriden."""
        pass

class ProgressBarWidgetHFill(object):
    """This is a variable width element of ProgressBar formatting.

    The ProgressBar object will call it's update value, informing the
    width this object must the made. This is like TeX \\hfill, it will
    expand to fill the line. You can use more than one in the same
    line, and they will all have the same width, and together will
    fill the line.
    """
    def update(self, pbar, width):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made. The parameter width is the total
        horizontal width the widget must have.

        At least this function must be overriden."""
        pass


class ETA(ProgressBarWidget):
    "Widget for the Estimated Time of Arrival"
    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    def update(self, pbar):
        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)

class FileTransferSpeed(ProgressBarWidget):
    "Widget for showing the transfer speed (useful for file transfers)."
    def __init__(self):
        self.fmt = '%6.2f %s'
        self.units = ['B', 'K', 'M', 'G', 'T', 'P']
    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:#== 0:
            bps = 0.0
        else:
            bps = float(pbar.currval) / pbar.seconds_elapsed
        spd = bps
        for u in self.units:
            if spd < 1000:
                break
            spd /= 1000
        return self.fmt % (spd, u + '/s')

class RotatingMarker(ProgressBarWidget):
    "A rotating marker for filling the bar of progress."
    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1
    def update(self, pbar):
        if pbar.finished:
            return self.markers[0]
        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]

class Percentage(ProgressBarWidget):
    "Just the percentage done."
    def update(self, pbar):
        return '%3d%%' % pbar.percentage()

class SimpleProgress(ProgressBarWidget):
    "Simple Progress: returns what is already done and the total, e.g. '5 of 47'"
    def update(self, pbar):
        return '%d of %d' % (pbar.currval, pbar.maxval)

class Bar(ProgressBarWidgetHFill):
    "The bar of progress. It will strech to fill the line."
    def __init__(self, marker='#', left='|', right='|'):
        self.marker = marker
        self.left = left
        self.right = right
    def _format_marker(self, pbar):
        if isinstance(self.marker, (str, unicode)):
            return self.marker
        else:
            return self.marker.update(pbar)
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).ljust(cwidth) + self.right)
        return bar

class ReverseBar(Bar):
    "The reverse bar of progress, or bar of regress. :)"
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).rjust(cwidth) + self.right)
        return bar

default_widgets = [Percentage(), ' ', Bar()]
class ProgressBar(object):
    """This is the ProgressBar class, it updates and prints the bar.

    The term_width parameter may be an integer. Or None, in which case
    it will try to guess it, if it fails it will default to 80 columns.

    The simple use is like this:
    >>> pbar = ProgressBar().start()
    >>> for i in xrange(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    But anything you want to do is possible (well, almost anything).
    You can supply different widgets of any type in any order. And you
    can even write your own widgets! There are many widgets already
    shipped and you should experiment with them.

    When implementing a widget update method you may access any
    attribute or function of the ProgressBar object calling the
    widget's update method. The most important attributes you would
    like to access are:
    - currval: current value of the progress, 0 <= currval <= maxval
    - maxval: maximum (and final) value of the progress
    - finished: True if the bar is have finished (reached 100%), False o/w
    - start_time: first time update() method of ProgressBar was called
    - seconds_elapsed: seconds elapsed since start_time
    - percentage(): percentage of the progress (this is a method)
    """
    def __init__(self, maxval=100, widgets=default_widgets, term_width=None,
                 fd=sys.stderr):
        assert maxval > 0
        self.maxval = maxval
        self.widgets = widgets
        self.fd = fd
        self.signal_set = False
        if term_width is None:
            try:
                self.handle_resize(None, None)
                signal.signal(signal.SIGWINCH, self.handle_resize)
                self.signal_set = True
            except:
                self.term_width = 79
        else:
            self.term_width = term_width

        self.currval = 0
        self.finished = False
        self.prev_percentage = -1
        self.start_time = None
        self.seconds_elapsed = 0

    def handle_resize(self, signum, frame):
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = w

    def percentage(self):
        "Returns the percentage of the progress."
        return self.currval * 100.0 / self.maxval

    def _format_widgets(self):
        r = []
        hfill_inds = []
        num_hfill = 0
        currwidth = 0
        for i, w in enumerate(self.widgets):
            if isinstance(w, ProgressBarWidgetHFill):
                r.append(w)
                hfill_inds.append(i)
                num_hfill += 1
            elif isinstance(w, (str, unicode)):
                r.append(w)
                currwidth += len(w)
            else:
                weval = w.update(self)
                currwidth += len(weval)
                r.append(weval)
        for iw in hfill_inds:
            r[iw] = r[iw].update(self, (self.term_width - currwidth) / num_hfill)
        return r

    def _format_line(self):
        return ''.join(self._format_widgets()).ljust(self.term_width)

    def _need_update(self):
        return int(self.percentage()) != int(self.prev_percentage)

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval
        self.currval = value
        if not self._need_update() or self.finished:
            return
        if not self.start_time:
            self.start_time = time.time()
        self.seconds_elapsed = time.time() - self.start_time
        self.prev_percentage = self.percentage()
        if value != self.maxval:
            self.fd.write(self._format_line() + '\r')
        else:
            self.finished = True
            self.fd.write(self._format_line() + '\n')

    def start(self):
        """Start measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in xrange(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """
        self.update(0)
        return self

    def finish(self):
        """Used to tell the progress is finished."""
        self.update(self.maxval)
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        





if __name__ == '__main__':
    import os

    def example1():
        widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
                   ' ', ETA(), ' ', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
        for i in range(1000000):
            # do something
            pbar.update(10 * i + 1)
        pbar.finish()
        print

    def example2():
        class CrazyFileTransferSpeed(FileTransferSpeed):
            "It's bigger between 45 and 80 percent"
            def update(self, pbar):
                if 45 < pbar.percentage() < 80:
                    return 'Bigger Now ' + FileTransferSpeed.update(self, pbar)
                else:
                    return FileTransferSpeed.update(self, pbar)

        widgets = [CrazyFileTransferSpeed(), ' <<<', Bar(), '>>> ', Percentage(), ' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=10000000)
        # maybe do something
        pbar.start()
        for i in range(2000000):
            # do something
            pbar.update(5 * i + 1)
        pbar.finish()
        print

    def example3():
        widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
        pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
        for i in range(1000000):
            # do something
            pbar.update(10 * i + 1)
        pbar.finish()
        print

    def example4():
        widgets = ['Test: ', Percentage(), ' ',
                   Bar(marker='0', left='[', right=']'),
                   ' ', ETA(), ' ', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=500)
        pbar.start()
        for i in range(100, 500 + 1, 50):
            time.sleep(0.2)
            pbar.update(i)
        pbar.finish()
        print


    example1()
    example2()
    example3()
    example4()


########NEW FILE########
