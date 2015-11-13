__FILENAME__ = Automater
#!/usr/bin/python
"""
The Automater.py module defines the main() function for Automater.

Parameter Required is:
target -- List one IP Address (CIDR or dash notation accepted), URL or Hash
to query or pass the filename of a file containing IP Address info, URL or
Hash to query each separated by a newline.

Optional Parameters are:
-o, --output -- This option will output the results to a file.
-w, --web -- This option will output the results to an HTML file.
-c, --csv -- This option will output the results to a CSV file.
-d, --delay -- Change the delay to the inputted seconds. Default is 2.
-s, --source -- Will only run the target against a specific source engine
to pull associated domains.  Options are defined in the name attribute of
the site element in the XML configuration file
--p -- Tells the program to post information to sites that allow posting.
By default the program will NOT post to sites that require a post.
        
Class(es):
No classes are defined in this module.

Function(s):
main -- Provides the instantiation point for Automater.

Exception(s):
No exceptions exported.
"""

import sys
from siteinfo import SiteFacade
from utilities import Parser, IPWrapper
from outputs import SiteDetailOutput
from inputs import TargetFile

def main():
    """
    Serves as the instantiation point to start Automater.
    
    Argument(s):
    No arguments are required.
    
    Return value(s):
    Nothing is returned from this Method.
    
    Restriction(s):
    The Method has no restrictions.
    """
    sites = []
    parser = Parser('IP, URL, and Hash Passive Analysis tool')

    # if no target run and print help
    if parser.hasNoTarget():
        print '[!] No argument given.'
        parser.print_help()  # need to fix this. Will later
        sys.exit()

    # user may only want to run against one source - allsources
    # is the seed used to check if the user did not enter an s tag
    source = "allsources"
    if parser.hasSource():
        source = parser.Source

    # a file input capability provides a possibility of
    # multiple lines of targets
    targetlist = []
    if parser.hasInputFile():
        for tgtstr in TargetFile.TargetList(parser.InputFile):
            if IPWrapper.isIPorIPList(tgtstr):
                for targ in IPWrapper.getTarget(tgtstr):
                    targetlist.append(targ)
            else:
                targetlist.append(tgtstr)
    else:  # one target or list of range of targets added on console
        target = parser.Target
        if IPWrapper.isIPorIPList(target):
            for targ in IPWrapper.getTarget(target):
                targetlist.append(targ)
        else:
            targetlist.append(target)

    sitefac = SiteFacade()
    sitefac.runSiteAutomation(parser.Delay,
                              targetlist,
                              source,
                              parser.hasPost())
    sites = sitefac.Sites
    if sites is not None:
        SiteDetailOutput(sites).createOutputInfo(parser)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = inputs
"""
The inputs.py module represents some form of all inputs
to the Automater program to include target files, and
the standard config file - sites.xml. Any addition to
Automater that brings any other input requirement should
be programmed in this module.

Class(es):
TargetFile -- Provides a representation of a file containing target
              strings for Automater to utilize.
SitesFile -- Provides a representation of the sites.xml
             configuration file.
              
Function(s):
No global exportable functions are defined.

Exception(s):
No exceptions exported.
"""
from xml.etree.ElementTree import ElementTree
import os

class TargetFile(object):
    """
    TargetFile provides a Class Method to retrieve information from a file-
    based target when one is entered as the first parameter to the program.
    
    Public Method(s):
    (Class Method) TargetList
    
    Instance variable(s):
    No instance variables.
    """

    @classmethod
    def TargetList(self, filename):
        """
        Opens a file for reading.
        Returns each string from each line of a single or multi-line file.
        
        Argument(s):
        filename -- string based name of the file that will be retrieved and parsed.
        
        Return value(s):
        Iterator of string(s) found in a single or multi-line file.
        
        Restriction(s):
        This Method is tagged as a Class Method
        """
        try:
            target = ""
            with open(filename) as f:
                li = f.readlines()
                for i in li:
                    target = str(i).strip()
                    yield target
        except IOError:
            print "There was an error reading from the target input file."


class SitesFile(object):
    """
    SitesFile represents an XML Elementree object representing the
    program's configuration file. Returns XML Elementree object.
    
    Method(s):
    (Class Method) getXMLTree
    (Class Method) fileExists
    
    Instance variable(s):
    No instance variables.
    """    

    @classmethod
    def getXMLTree(self):
        """
        Opens a config file for reading.
        Returns XML Elementree object representing XML Config file.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        ElementTree
        
        Restrictions:
        File must be named sites.xml and must be in same directory as caller.
        This Method is tagged as a Class Method
        """
        try:
            with open("sites.xml") as f:
                sitetree = ElementTree()
                sitetree.parse(f)
                return sitetree
        except:
            print "There was an error reading from the sites input file.",
            print "Please check that the XML file is present and correctly formatted."

    @classmethod
    def fileExists(self):
        """
        Checks if a file exists. Returns boolean representing if file exists.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean
        
        Restrictions:
        File must be named sites.xml and must be in same directory as caller.
        This Method is tagged as a Class Method
        """
        return os.path.exists("sites.xml") and os.path.isfile("sites.xml")

########NEW FILE########
__FILENAME__ = outputs
"""
The outputs.py module represents some form of all outputs
from the Automater program to include all variation of
output files. Any addition to the Automater that brings
any other output requirement should be programmed in this module.

Class(es):
SiteDetailOutput -- Wrapper class around all functions that print output
from Automater, to include standard output and file system output.

Function(s):
No global exportable functions are defined.

Exception(s):
No exceptions exported.
"""

import csv
from operator import attrgetter

class SiteDetailOutput(object):
    """
    SiteDetailOutput provides the capability to output information
    to the screen, a text file, a comma-seperated value file, or
    a file formatted with html markup (readable by web browsers).
    
    Public Method(s):
    createOutputInfo
    
    Instance variable(s):
    _listofsites - list storing the list of site results stored.
    """
    
    def __init__(self,sitelist):
        """
        Class constructor. Stores the incoming list of sites in the _listofsites list.
        
        Argument(s):
        sitelist -- list containing site result information to be printed.
        
        Return value(s):
        Nothing is returned from this Method.
        """
        self._listofsites = []
        self._listofsites = sitelist

    @property
    def ListOfSites(self):
        """
        Checks instance variable _listofsites for content.
        Returns _listofsites if it has content or None if it does not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        _listofsites -- list containing list of site results if variable contains data.
        None -- if _listofsites is empty or not assigned.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._listofsites is None or len(self._listofsites) == 0:
            return None
        return self._listofsites

    def createOutputInfo(self,parser):
        """
        Checks parser information calls correct print methods based on parser requirements.
        Returns nothing.
        
        Argument(s):
        parser -- Parser object storing program input parameters used when program was run.
        
        Return value(s):
        Nothing is returned from this Method.
        
        Restriction(s):
        The Method has no restrictions.
        """
        self.PrintToScreen()
        if parser.hasTextOutFile():
            self.PrintToTextFile(parser.TextOutFile)
        if parser.hasHTMLOutFile():
            self.PrintToHTMLFile(parser.HTMLOutFile)
        if parser.hasCSVOutSet():
            self.PrintToCSVFile(parser.CSVOutFile)

    def PrintToScreen(self):
        """
        Formats site information correctly and prints it to the user's standard output.
        Returns nothing.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Nothing is returned from this Method.
        
        Restriction(s):
        The Method has no restrictions.
        """
        sites = sorted(self.ListOfSites, key=attrgetter('Target'))
        target = ""
        if sites is not None:
            for site in sites:
                if not isinstance(site._regex,basestring): #this is a multisite
                    for index in range(len(site.RegEx)): #the regexs will ensure we have the exact number of lookups
                        siteimpprop = site.getImportantProperty(index)
                        if target != site.Target:
                            print "\n____________________     Results found for: " + site.Target + "     ____________________"
                            target = site.Target
                        if siteimpprop is None or len(siteimpprop)==0:
                            print "No results in the " + site.FriendlyName[index] + " category"
                        else:
                            if siteimpprop[index] is None or len(siteimpprop[index])==0:
                                print "No results found for: " + site.ReportStringForResult[index]
                            else:
                                laststring = ""
                                #if it's just a string we don't want it output like a list
                                if isinstance(siteimpprop[index], basestring):
                                    if "" + site.ReportStringForResult[index] + " " + str(siteimpprop[index]) != laststring:
                                        print "" + site.ReportStringForResult[index] + " " + str(siteimpprop[index])
                                        laststring = "" + site.ReportStringForResult[index] + " " + str(siteimpprop[index])
                                #must be a list since it failed the isinstance check on string
                                else:
                                    laststring = ""
                                    for siteresult in siteimpprop[index]:
                                        if "" + site.ReportStringForResult[index] + " " + str(siteresult) != laststring:
                                            print "" + site.ReportStringForResult[index] + " " + str(siteresult)
                                            laststring = "" + site.ReportStringForResult[index] + " " + str(siteresult)
                else:#this is a singlesite
                    siteimpprop = site.getImportantProperty(0)
                    if target != site.Target:
                        print "\n____________________     Results found for: " + site.Target + "     ____________________"
                        target = site.Target
                    if siteimpprop is None or len(siteimpprop)==0:
                        print "No results found in the " + site.FriendlyName
                    else:
                        laststring = ""
                        #if it's just a string we don't want it output like a list
                        if isinstance(siteimpprop, basestring):
                            if "" + site.ReportStringForResult + " " + str(siteimpprop) != laststring:
                                print "" + site.ReportStringForResult + " " + str(siteimpprop)
                                laststring = "" + site.ReportStringForResult + " " + str(siteimpprop)
                        #must be a list since it failed the isinstance check on string
                        else:
                            laststring = ""
                            for siteresult in siteimpprop:
                                if "" + site.ReportStringForResult + " " + str(siteresult) != laststring:
                                    print "" + site.ReportStringForResult + " " + str(siteresult)
                                    laststring = "" + site.ReportStringForResult + " " + str(siteresult)
        else:
            pass

    def PrintToTextFile(self,textoutfile):
        """
        Formats site information correctly and prints it to an output file in text format.
        Returns nothing.
        
        Argument(s):
        textoutfile -- A string representation of a file that will store the output.
        
        Return value(s):
        Nothing is returned from this Method.
        
        Restriction(s):
        The Method has no restrictions.
        """
        sites = sorted(self.ListOfSites, key=attrgetter('Target'))
        target = ""
        print "\n[+] Generating text output: " + textoutfile
        f = open(textoutfile, "w")
        if sites is not None:
            for site in sites:
                if not isinstance(site._regex,basestring): #this is a multisite
                    for index in range(len(site.RegEx)): #the regexs will ensure we have the exact number of lookups
                        siteimpprop = site.getImportantProperty(index)
                        if target != site.Target:
                            f.write("\n____________________     Results found for: " + site.Target + "     ____________________")
                            target = site.Target
                        if siteimpprop is None or len(siteimpprop)==0:
                            f.write("\nNo results in the " + site.FriendlyName[index] + " category")
                        else:
                            if siteimpprop[index] is None or len(siteimpprop[index])==0:
                                f.write("\nNo results found for: " + site.ReportStringForResult[index])
                            else:
                                laststring = ""
                                #if it's just a string we don't want it to output like a list
                                if isinstance(siteimpprop[index], basestring):
                                    if "" + site.ReportStringForResult[index] + " " + str(siteimpprop[index]) != laststring:
                                        f.write("\n" + site.ReportStringForResult[index] + " " + str(siteimpprop[index]))
                                        laststring = "" + site.ReportStringForResult[index] + " " + str(siteimpprop[index])
                                #must be a list since it failed the isinstance check on string
                                else:
                                    laststring = ""
                                    for siteresult in siteimpprop[index]:
                                        if "" + site.ReportStringForResult[index] + " " + str(siteresult) != laststring:
                                            f.write("\n" + site.ReportStringForResult[index] + " " + str(siteresult))
                                            laststring = "" + site.ReportStringForResult[index] + " " + str(siteresult)
                else:#this is a singlesite
                    siteimpprop = site.getImportantProperty(0)
                    if target != site.Target:
                        f.write("\n____________________     Results found for: " + site.Target + "     ____________________")
                        target = site.Target
                    if siteimpprop is None or len(siteimpprop)==0:
                        f.write("\nNo results found in the " + site.FriendlyName)
                    else:
                        laststring = ""
                        #if it's just a string we don't want it output like a list
                        if isinstance(siteimpprop, basestring):
                            if "" + site.ReportStringForResult + " " + str(siteimpprop) != laststring:
                                f.write("\n" + site.ReportStringForResult + " " + str(siteimpprop))
                                laststring = "" + site.ReportStringForResult + " " + str(siteimpprop)
                        else:
                            laststring = ""
                            for siteresult in siteimpprop:
                                if "" + site.ReportStringForResult + " " + str(siteresult) != laststring:
                                    f.write("\n" + site.ReportStringForResult + " " + str(siteresult))
                                    laststring = "" + site.ReportStringForResult + " " + str(siteresult)
        f.flush()
        f.close()
        print "" + textoutfile + " Generated"

    def PrintToCSVFile(self,csvoutfile):
        """
        Formats site information correctly and prints it to an output file with comma-seperators.
        Returns nothing.
        
        Argument(s):
        csvoutfile -- A string representation of a file that will store the output.
        
        Return value(s):
        Nothing is returned from this Method.
        
        Restriction(s):
        The Method has no restrictions.
        """
        sites = sorted(self.ListOfSites, key=attrgetter('Target'))
        target = ""
        print '\n[+] Generating CSV output: ' + csvoutfile
        f = open(csvoutfile, "wb")
        csvRW = csv.writer(f, quoting=csv.QUOTE_ALL)
        csvRW.writerow(['Target', 'Type', 'Source', 'Result'])
        if sites is not None:
            for site in sites:
                if not isinstance(site._regex,basestring): #this is a multisite:
                    for index in range(len(site.RegEx)): #the regexs will ensure we have the exact number of lookups
                        siteimpprop = site.getImportantProperty(index)
                        if siteimpprop is None or len(siteimpprop)==0:
                            tgt = site.Target
                            typ = site.TargetType
                            source = site.FriendlyName[index]
                            res = "No results found"
                            csvRW.writerow([tgt,typ,source,res])
                        else:
                            if siteimpprop[index] is None or len(siteimpprop[index])==0:
                                tgt = site.Target
                                typ = site.TargetType
                                source = site.FriendlyName[index]
                                res = "No results found"
                                csvRW.writerow([tgt,typ,source,res])
                            else:
                                laststring = ""
                                #if it's just a string we don't want it to output like a list
                                if isinstance(siteimpprop, basestring):
                                    tgt = site.Target
                                    typ = site.TargetType
                                    source = site.FriendlyName
                                    res = siteimpprop
                                    if "" + tgt + typ + source + res != laststring:
                                        csvRW.writerow([tgt,typ,source,res])
                                        laststring = "" + tgt + typ + source + res
                                #must be a list since it failed the isinstance check on string
                                else:
                                    laststring = ""
                                    for siteresult in siteimpprop[index]:
                                        tgt = site.Target
                                        typ = site.TargetType
                                        source = site.FriendlyName[index]
                                        res = siteresult
                                        if "" + tgt + typ + source + str(res) != laststring:
                                            csvRW.writerow([tgt,typ,source,res])
                                            laststring = "" + tgt + typ + source + str(res)
                else:#this is a singlesite
                    siteimpprop = site.getImportantProperty(0)
                    if siteimpprop is None or len(siteimpprop)==0:
                        tgt = site.Target
                        typ = site.TargetType
                        source = site.FriendlyName
                        res = "No results found"
                        csvRW.writerow([tgt,typ,source,res])
                    else:
                        laststring = ""
                        #if it's just a string we don't want it output like a list
                        if isinstance(siteimpprop, basestring):
                            tgt = site.Target
                            typ = site.TargetType
                            source = site.FriendlyName
                            res = siteimpprop
                            if "" + tgt + typ + source + res != laststring:
                                csvRW.writerow([tgt,typ,source,res])
                                laststring = "" + tgt + typ + source + res
                        else:
                            laststring = ""
                            for siteresult in siteimpprop:
                                tgt = site.Target
                                typ = site.TargetType
                                source = site.FriendlyName
                                res = siteresult
                                if "" + tgt + typ + source + str(res) != laststring:
                                    csvRW.writerow([tgt,typ,source,res])
                                    laststring = "" + tgt + typ + source + str(res)
                                    
        f.flush()
        f.close()
        print "" + csvoutfile + " Generated"

    def PrintToHTMLFile(self,htmloutfile):
        """
        Formats site information correctly and prints it to an output file using HTML markup.
        Returns nothing.
        
        Argument(s):
        htmloutfile -- A string representation of a file that will store the output.
        
        Return value(s):
        Nothing is returned from this Method.
        
        Restriction(s):
        The Method has no restrictions.
        """
        sites = sorted(self.ListOfSites, key=attrgetter('Target'))
        target = ""
        print '\n[+] Generating HTML output: ' + htmloutfile
        f = open(htmloutfile, "w")
        f.write(self.getHTMLOpening())
        if sites is not None:
            for site in sites:
                if not isinstance(site._regex,basestring): #this is a multisite:
                    for index in range(len(site.RegEx)): #the regexs will ensure we have the exact number of lookups
                        siteimpprop = site.getImportantProperty(index)
                        if siteimpprop is None or len(siteimpprop)==0:
                            tgt = site.Target
                            typ = site.TargetType
                            source = site.FriendlyName[index]
                            res = "No results found"
                            tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                            f.write(tableData)
                        else:
                            if siteimpprop[index] is None or len(siteimpprop[index])==0:
                                tgt = site.Target
                                typ = site.TargetType
                                source = site.FriendlyName[index]
                                res = "No results found"
                                tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                                f.write(tableData)
                            else:
                                #if it's just a string we don't want it to output like a list
                                if isinstance(siteimpprop, basestring):
                                    tgt = site.Target
                                    typ = site.TargetType
                                    source = site.FriendlyName
                                    res = siteimpprop
                                    tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                                    f.write(tableData)
                                else:
                                    for siteresult in siteimpprop[index]:
                                        tgt = site.Target
                                        typ = site.TargetType
                                        source = site.FriendlyName[index]
                                        res = siteresult
                                        tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                                        f.write(tableData)
                else:#this is a singlesite
                    siteimpprop = site.getImportantProperty(0)
                    if siteimpprop is None or len(siteimpprop)==0:
                        tgt = site.Target
                        typ = site.TargetType
                        source = site.FriendlyName
                        res = "No results found"
                        tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                        f.write(tableData)
                    else:
                        #if it's just a string we don't want it output like a list
                        if isinstance(siteimpprop, basestring):
                            tgt = site.Target
                            typ = site.TargetType
                            source = site.FriendlyName
                            res = siteimpprop
                            tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                            f.write(tableData)
                        else:
                            for siteresult in siteimpprop:
                                tgt = site.Target
                                typ = site.TargetType
                                source = site.FriendlyName
                                res = siteresult
                                tableData = '<tr><td>' + tgt + '</td><td>' + typ + '</td><td>' + source + '</td><td>' + str(res) + '</td></tr>'
                                f.write(tableData)
        f.write(self.getHTMLClosing())
        f.flush()
        f.close()
        print "" + htmloutfile + " Generated"

    def getHTMLOpening(self):
        """
        Creates HTML markup to provide correct formatting for initial HTML file requirements.
        Returns string that contains opening HTML markup information for HTML output file.
        
        Argument(s):
        No arguments required.
        
        Return value(s):
        string.
        
        Restriction(s):
        The Method has no restrictions.
        """
        return '''<style type="text/css">
                        #table-3 {
                            border: 1px solid #DFDFDF;
                            background-color: #F9F9F9;
                            width: 100%;
                            -moz-border-radius: 3px;
                            -webkit-border-radius: 3px;
                            border-radius: 3px;
                            font-family: Arial,"Bitstream Vera Sans",Helvetica,Verdana,sans-serif;
                            color: #333;
                        }
                        #table-3 td, #table-3 th {
                            border-top-color: white;
                            border-bottom: 1px solid #DFDFDF;
                            color: #555;
                        }
                        #table-3 th {
                            text-shadow: rgba(255, 255, 255, 0.796875) 0px 1px 0px;
                            font-family: Georgia,"Times New Roman","Bitstream Charter",Times,serif;
                            font-weight: normal;
                            padding: 7px 7px 8px;
                            text-align: left;
                            line-height: 1.3em;
                            font-size: 14px;
                        }
                        #table-3 td {
                            font-size: 12px;
                            padding: 4px 7px 2px;
                            vertical-align: top;
                        }res
                        h1 {
                            text-shadow: rgba(255, 255, 255, 0.796875) 0px 1px 0px;
                            font-family: Georgia,"Times New Roman","Bitstream Charter",Times,serif;
                            font-weight: normal;
                            padding: 7px 7px 8px;
                            text-align: Center;
                            line-height: 1.3em;
                            font-size: 40px;
                        }
                        h2 {
                            text-shadow: rgba(255, 255, 255, 0.796875) 0px 1px 0px;
                            font-family: Georgia,"Times New Roman","Bitstream Charter",Times,serif;
                            font-weight: normal;
                            padding: 7px 7px 8px;
                            text-align: left;
                            line-height: 1.3em;
                            font-size: 16px;
                        }
                        h4 {
                            text-shadow: rgba(255, 255, 255, 0.796875) 0px 1px 0px;
                            font-family: Georgia,"Times New Roman","Bitstream Charter",Times,serif;
                            font-weight: normal;
                            padding: 7px 7px 8px;
                            text-align: left;
                            line-height: 1.3em;
                            font-size: 10px;
                        }
                        </style>
                        <html>
                        <body>
                        <title> Automater Results </title>
                        <h1> Automater Results </h1>
                        <table id="table-3">
                        <tr>
                        <th>Target</th>
                        <th>Type</th>
                        <th>Source</th>
                        <th>Result</th>
                        </tr>
                        '''

    def getHTMLClosing(self):
        """
        Creates HTML markup to provide correct formatting for closing HTML file requirements.
        Returns string that contains closing HTML markup information for HTML output file.
        
        Argument(s):
        No arguments required.
        
        Return value(s):
        string.
        
        Restriction(s):
        The Method has no restrictions.
        """
        return '''
            </table>
            <br>
            <br>
            <p>Created using Automater.py by @TekDefense <a href="http://www.tekdefense.com">http://www.tekdefense.com</a>; <a href="https://github.com/1aN0rmus/TekDefense">https://github.com/1aN0rmus/TekDefense</a></p>
            </body>
            </html>
            '''

########NEW FILE########
__FILENAME__ = siteinfo
"""
The siteinfo.py module provides site lookup and result
storage for those sites based on the sites.xml config
file and the arguments sent in to the Automater.

Class(es):
SiteFacade -- Class used to run the automation necessary to retrieve
site information and store results.
Site -- Parent Class used to store sites and information retrieved.
SingleResultsSite -- Class used to store information from a site that
only has one result requested and discovered.
MultiResultsSite -- Class used to store information from a site that
has multiple results requested and discovered.
PostTransactionPositiveCapableSite -- Class used to store information
from a site that has single or multiple results requested and discovered.
This Class is utilized to post information to web sites if a post is
required and requested via a --p argument utilized when the program is
called. This Class expects to find the first regular expression listed
in the sites.xml config file. If that regex is found, it tells the class
that a post is necessary.
PostTransactionAPIKeySite -- Class used to store information from a 
site that has single or multiple results requested and discovered. This
Class is utilized if an API key is provided in the sites.xml
configuration file.

Function(s):
No global exportable functions are defined.

Exception(s):
No exceptions exported.
"""
import urllib
import urllib2
import time
import re
from operator import attrgetter
from inputs import SitesFile
from utilities import Parser

class SiteFacade(object):
    """
    SiteFacade provides a Facade to run the multiple requirements needed
    to automate the site retrieval and storage processes.
    
    Public Method(s):
    runSiteAutomation
    (Property) Sites
    
    Instance variable(s):
    _sites
    """

    def __init__(self):
        """
        Class constructor. Simply creates a blank list and assigns it to
        instance variable _sites that will be filled with retrieved info
        from sites defined in the sites.xml configuration file.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Nothing is returned from this Method.
        """
        self._sites = []

    def runSiteAutomation(self, webretrievedelay, targetlist, source, postbydefault):
        """
        Builds site objects representative of each site listed in the sites.xml
        config file. Appends a Site object or one of it's subordinate objects
        to the _sites instance variable so retrieved information can be used.
        Returns nothing.

        Argument(s):
        webretrievedelay -- The amount of seconds to wait between site retrieve
        calls. Default delay is 2 seconds.
        targetlist -- list of strings representing targets to be investigated.
        Targets can be IP Addresses, MD5 hashes, or hostnames.
        source -- String representing a specific site that should only be used
        for investigation purposes instead of all sites listed in the sites.xml
        config file.
        postbydefault -- Boolean value to tell the program if the user wants
        to post data to a site if a post is required. Default is to NOT post.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        if SitesFile.fileExists():
            sitetree = SitesFile.getXMLTree()
            for siteelement in sitetree.iter(tag = "site"):
                if source == "allsources" or source == siteelement.get("name"):
                    for targ in targetlist:
                        sitetypematch = False
                        targettype = self.identifyTargetType(targ)
                        for st in siteelement.find("sitetype").findall("entry"):
                            if st.text == targettype:
                                sitetypematch = True
                        if sitetypematch:
                            site = Site.buildSiteFromXML(siteelement, webretrievedelay, targettype, targ)
                            if (site.Params != None or site.Headers != None) and site.APIKey != None:
                                self._sites.append(PostTransactionAPIKeySite(site))
                            elif site.Params != None or site.Headers != None:
                                self._sites.append(PostTransactionPositiveCapableSite(site, postbydefault))
                            elif isinstance(site.RegEx, basestring):
                                self._sites.append(SingleResultsSite(site))
                            else:
                                self._sites.append(MultiResultsSite(site))

    @property
    def Sites(self):
        """
        Checks the instance variable _sites is empty or None.
        Returns _sites (the site list) or None if it is empty.

        Argument(s):
        No arguments are required.

        Return value(s):
        list -- of Site objects or its subordinates.
        None -- if _sites is empty or None.

        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._sites is None or len(self._sites) == 0:
            return None
        return self._sites

    def identifyTargetType(self, target):
        """
        Checks the target information provided to determine if it is a(n)
        IP Address in standard; CIDR or dash notation, or an MD5 hash,
        or a string hostname.
        Returns a string md5 if MD5 hash is identified. Returns the string
        ip if any IP Address format is found. Returns the string hostname
        if neither of those two are found.

        Argument(s):
        target -- string representing the target provided as the first
        argument to the program when Automater is run.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        ipAddress = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        ipFind = re.findall(ipAddress, target)
        if ipFind is not None and len(ipFind) > 0:
            return "ip"

        md5 = re.compile('[a-fA-F0-9]{32}', re.IGNORECASE)
        md5Find = re.findall(md5,target)
        if md5Find is not None and len(md5Find) > 0:
            return "md5"

        return "hostname"

class Site(object):
    """
    Site is the parent object that represents each site used
    for retrieving information. Site stores the results
    discovered from each web site discovered when running Automater.
    Site is the parent object to SingleResultsSite, MultiResultsSite,
    PostTransactionPositiveCapableSite, and PostTransactionAPIKeySite.

    Public Method(s):
    (Class Method) buildSiteFromXML
    (Class Method) buildStringOrListfromXML
    (Class Method) buildDictionaryFromXML
    (Property) WebRetrieveDelay
    (Property) TargetType
    (Property) ReportStringForResult
    (Property) FriendlyName
    (Property) RegEx
    (Property) URL
    (Property) MessageToPost
    (Property) ErrorMessage
    (Property) UserMessage
    (Property) FullURL
    (Setter) FullURL
    (Property) ImportantPropertyString
    (Property) Params
    (Setter) Params
    (Property) Headers
    (Property) APIKey
    (Property) Target
    (Property) Results
    addResults
    postMessage
    getImportantProperty
    getTarget
    getResults
    getFullURL
    getWebScrape

    Instance variable(s):
    _sites
    _sourceurl
    _webretrievedelay
    _targetType
    _reportstringforresult
    _errormessage
    _usermessage
    _target
    _friendlyName
    _regex
    _fullURL
    _importantProperty
    _params
    _headers
    _apikey
    _results
    _messagetopost
    """
    def __init__(self, domainurl, webretrievedelay, targettype, \
                 reportstringforresult, target, friendlyname, regex, fullurl, \
                 importantproperty, params, headers, apikey):
        """
        Class constructor. Sets the instance variables based on input from
        the arguments supplied when Automater is run and what the sites.xml
        config file stores.

        Argument(s):
        domainurl -- string defined in sites.xml in the domainurl XML tag.
        webretrievedelay -- the amount of seconds to wait between site retrieve
        calls. Default delay is 2 seconds.
        targettype -- the targettype as defined. Either ip, md5, or hostname.
        reportstringforresult -- string or list of strings that are entered in
        the entry XML tag within the reportstringforresult XML tag in the
        sites.xml configuration file.
        target -- the target that will be used to gather information on.
        friendlyname -- string or list of strings that are entered in
        the entry XML tag within the sitefriendlyname XML tag in the
        sites.xml configuration file.
        regex -- the regexs defined in the entry XML tag within the
        regex XML tag in the sites.xml configuration file.
        fullurl -- string representation of fullurl pulled from the
        sites.xml file in the fullurl XML tag.
        importantproperty -- string defined in the the sites.xml config file
        in the importantproperty XML tag.
        params -- string or list provided in the entry XML tags within the params
        XML tag in the sites.xml configuration file.
        headers -- string or list provided in the entry XML tags within the headers
        XML tag in the sites.xml configuration file.
        apikey -- string or list of strings found in the entry XML tags within
        the apikey XML tag in the sites.xml configuration file.

        Return value(s):
        Nothing is returned from this Method.
        """
        self._sourceurl = domainurl
        self._webretrievedelay = webretrievedelay
        self._targetType = targettype
        self._reportstringforresult = reportstringforresult
        self._errormessage = "[-] Cannot scrape"
        self._usermessage = "[*] Checking"
        self._target = target
        self._friendlyName = friendlyname
        self._regex = regex
        self._fullURL = ""
        self.FullURL = fullurl # call the helper method to clean %TARGET% from fullurl string
        self._importantProperty = importantproperty
        self._params = None
        if params is not None:
            self.Params = params # call the helper method to clean %TARGET% from params string
        if headers is None:
            self._headers = None
        else:
            self._headers = headers
        if apikey is None:
            self._apikey = None
        else:
            self._apikey = apikey
        self._results = []
        self._messagetopost = ""

    @classmethod
    def buildSiteFromXML(self, siteelement, webretrievedelay, targettype, target):
        """
        Utilizes the Class Methods within this Class to build the Site object.
        Returns a Site object that defines results returned during the web
        retrieval investigations.

        Argument(s):
        siteelement -- the siteelement object that will be used as the
        start element.
        webretrievedelay -- the amount of seconds to wait between site retrieve
        calls. Default delay is 2 seconds.
        targettype -- the targettype as defined. Either ip, md5, or hostname.
        target -- the target that will be used to gather information on.

        Return value(s):
        Site object.

        Restriction(s):
        This Method is tagged as a Class Method
        """
        domainurl = siteelement.find("domainurl").text
        reportstringforresult = Site.buildStringOrListfromXML(siteelement, "reportstringforresult")
        sitefriendlyname = Site.buildStringOrListfromXML(siteelement, "sitefriendlyname")
        regex = Site.buildStringOrListfromXML(siteelement, "regex")
        fullurl = siteelement.find("fullurl").text
        importantproperty = Site.buildStringOrListfromXML(siteelement, "importantproperty")
        params = Site.buildDictionaryFromXML(siteelement, "params")
        headers = Site.buildDictionaryFromXML(siteelement, "headers")
        apikey = Site.buildStringOrListfromXML(siteelement, "apikey")
        return Site(domainurl, webretrievedelay, targettype, reportstringforresult, target, \
                    sitefriendlyname, regex, fullurl, importantproperty, params, headers, apikey)

    @classmethod
    def buildStringOrListfromXML(self, siteelement, elementstring):
        """
        Takes in a siteelement and then elementstring and builds a string
        or list from multiple entry XML tags defined in the sites.xml config
        file. Returns None if there are no entry XML tags for this
        specific elementstring. Returns a list of those entries
        if entry XML tags are found or a string of that entry if only
        one entry XML tag is found.

        Argument(s):
        siteelement -- the siteelement object that will be used as the
        start element.
        elementstring -- the string representation within the siteelement
        that will be utilized to get to the single or multiple entry
        XML tags.

        Return value(s):
        None if no entry XML tags are found.
        List representing all entry keys found within the elementstring.
        string representing an entry key if only one is found
        within the elementstring.

        Restriction(s):
        This Method is tagged as a Class Method
        """
        variablename = ""
        if len(siteelement.find(elementstring).findall("entry")) == 0:
            return None

        if len(siteelement.find(elementstring).findall("entry")) > 1:
            variablename = []
            for entry in siteelement.find(elementstring).findall("entry"):
                variablename.append(entry.text)
        else:
            variablename = ""
            variablename = siteelement.find(elementstring).find("entry").text
        return variablename

    @classmethod
    def buildDictionaryFromXML(self, siteelement, elementstring):
        """
        Takes in a siteelement and then elementstring and builds a dictionary
        from multiple entry XML tags defined in the sites.xml config file.
        Returns None if there are no entry XML tags for this
        specific elementstring. Returns a dictionary of those entries
        if entry XML tags are found.

        Argument(s):
        siteelement -- the siteelement object that will be used as the
        start element.
        elementstring -- the string representation within the siteelement
        that will be utilized to get to the single or multiple entry
        XML tags.

        Return value(s):
        None if no entry XML tags are found.
        Dictionary representing all entry keys found within the elementstring.

        Restriction(s):
        This Method is tagged as a Class Method
        """
        variablename = ""
        if len(siteelement.find(elementstring).findall("entry")) > 0:
            variablename = {}
            for entry in siteelement.find(elementstring).findall("entry"):
                variablename[entry.get("key")] = entry.text
        else:
            return None
        return variablename

    @property
    def WebRetrieveDelay(self):
        """
        Returns the string representation of the number of
        seconds that will be delayed between site retrievals.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representation of an integer that is the delay in
        seconds that will be used between each web site retrieval.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._webretrievedelay

    @property
    def TargetType(self):
        """
        Returns the target type information whether that be ip,
        md5, or hostname.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- defined as ip, md5, or hostname.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._targetType

    @property
    def ReportStringForResult(self):
        """
        Returns the string representing a report string tag that
        precedes reporting information so the user knows what
        specifics are being found.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing a tag for reporting information.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._reportstringforresult

    @property
    def FriendlyName(self):
        """
        Returns the string representing a friendly string name.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing friendly name for a tag for reporting.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._friendlyName

    @property
    def RegEx(self):
        """
        Returns the string representing a regular expression
        required to retrieve the information being investigated.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing a regex used to find info on the site.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._regex

    @property    
    def URL(self):
        """
        Returns the string representing the Domain URL which is
        required to retrieve the information being investigated.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing the URL of the site.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._sourceurl

    @property
    def MessageToPost(self):
        """
        Returns the string representing a message to the user.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing a message to print to
        the standard output.

        Restriction(s):
        This Method is tagged as a Property.
        """    
        return self._messagetopost

    @property
    def ErrorMessage(self):
        """
        Returns the string representing the Error Message.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing the error message to print to
        the standard output.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._errormessage

    @property
    def UserMessage(self):
        """
        Returns the string representing the Full URL which is the
        domain URL plus querystrings and other information required
        to retrieve the information being investigated.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing the full URL of the site including
        querystring information and any other info required.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._usermessage

    @property
    def FullURL(self):
        """
        Returns the string representing the Full URL which is the
        domain URL plus querystrings and other information required
        to retrieve the information being investigated.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing the full URL of the site including
        querystring information and any other info required.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._fullURL

    @FullURL.setter
    def FullURL(self, fullurl):
        """
        Determines if the parameter has characters and assigns it to the
        instance variable _fullURL if it does after replaceing the target
        information where the keyword %TARGET% is used. This keyword will
        be used in the sites.xml configuration file where the user wants
        the target information to be placed in the URL.

        Argument(s):
        fullurl -- string representation of fullurl pulled from the
        sites.xml file in the fullurl XML tag.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        This Method is tagged as a Setter.
        """
        if len(fullurl) > 0:
            fullurlreplaced = fullurl.replace("%TARGET%", self._target)
            self._fullURL = fullurlreplaced
        else:
            self._fullURL = ""

    @property
    def ImportantPropertyString(self):
        """
        Returns the string representing the Important Property
        that the user wants the site to report. This is set using
        the sites.xml config file in the importantproperty XML tag.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representing the important property of the site
        that needs to be reported.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._importantProperty

    @property
    def Params(self):
        """
        Determines if web Parameters were set for this specific site.
        Returns the string representing the Parameters using the
        _params instance variable or returns None if the instance
        variable is empty or not set.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representation of the Parameters from the _params
        instance variable.

        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._params is None:
            return None
        if len(self._params) == 0:
            return None
        return self._params

    @Params.setter
    def Params(self, params):
        """
        Determines if Parameters were required for this specific site.
        If web Parameters were set, this places the target into the
        parameters where required maekred with the %TARGET% keyword
        in the sites.xml config file.

        Argument(s):
        params -- dictionary representing web Parameters required.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        This Method is tagged as a Setter.
        """
        if len(params) > 0:
            for key in params:
                if params[key] == "%TARGET%":
                    params[key] = self._target
            self._params = params
        else:
            self._params = None

    @property
    def Headers(self):
        """
        Determines if Headers were set for this specific site.
        Returns the string representing the Headers using the
        _headers instance variable or returns None if the instance
        variable is empty or not set.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representation of the Headers from the _headers
        instance variable.

        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._headers is None:
            return None
        if len(self._headers) == 0:
            return None
        return self._headers

    @property
    def APIKey(self):
        """
        Determines if an APIKey was set for this specific site.
        Returns the string representing the APIKey using the
        _apikey instance variable or returns None if the instance
        variable is empty or not set.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representation of the APIKey from the _apikey
        instance variable.

        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._apikey is None:
            return None
        if len(self._apikey) == 0:
            return None
        return self._apikey

    @property
    def Target(self):
        """
        Returns string representing the target being investigated.
        The string may be an IP Address, MD5 hash, or hostname.

        Argument(s):
        No arguments are required.

        Return value(s):
        string -- representation of the Target from the _target
        instance variable.

        Restriction(s):
        This Method is tagged as a Property.
        """
        return self._target

    @property
    def Results(self):
        """
        Checks the instance variable _results is empty or None.
        Returns _results (the results list) or None if it is empty.

        Argument(s):
        No arguments are required.

        Return value(s):
        list -- list of results discovered from the site being investigated.
        None -- if _results is empty or None.

        Restriction(s):
        This Method is tagged as a Property.
        """
        if self._results is None or len(self._results) == 0:
            return None
        return self._results

    def addResults(self, results):
        """
        Assigns the argument to the _results instance variable to build
        the list or results retrieved from the site. Assign None to the
        _results instance variable if the argument is empty.

        Argument(s):
        results -- list of results retrieved from the site.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        if results is None or len(results) == 0:
            self._results = None
        else:
            self._results = results

    def postMessage(self, message):
        """
        Prints multiple messages to inform the user of progress. Assignes
        the _messagetopost instance variable to the message. Uses the
        MessageToPost property.

        Argument(s):
        message -- string to be utilized as a message to post.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        self._messagetopost = message
        print self.MessageToPost

    def getImportantProperty(self, index):
        """
        Gets the property information from the property value listed in the
        sites.xml file for that specific site in the importantproperty xml tag.
        This Method allows for the property that will be printed to be changed
        using the configuration file.
        Returns the return value listed in the property attribute discovered.

        Argument(s):
        index -- integer representing which important property is retrieved if
        more than one important property value is listed in the config file.

        Return value(s):
        Multiple options -- returns the return value of the property listed in
        the config file. Most likely a string or a list.

        Restriction(s):
        The Method has no restrictions.
        """
        if isinstance(self._importantProperty, basestring):
            siteimpprop = getattr(self, "get" + self._importantProperty, Site.getResults)
        else:
            siteimpprop = getattr(self, "get" + self._importantProperty[index], Site.getResults)
        return siteimpprop()

    def getTarget(self):
        """
        Returns the Target property information.

        Argument(s):
        No arguments are required.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        return self.Target

    def getResults(self):
        """
        Returns the Results property information.

        Argument(s):
        No arguments are required.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        return self.Results

    def getFullURL(self):
        """
        Returns the FullURL property information.

        Argument(s):
        No arguments are required.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        return self.FullURL

    def getWebScrape(self):
        """
        Attempts to retrieve a string from a web site. String retrieved is
        the entire web site including HTML markup.
        Returns the string representing the entire web site including the
        HTML markup retrieved from the site.

        Argument(s):
        No arguments are required.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        delay = self.WebRetrieveDelay
        proxy = urllib2.ProxyHandler()
        opener = urllib2.build_opener(proxy)
        try:
            response = opener.open(self.FullURL)
            content = response.read()
            contentString = str(content)
            time.sleep(delay)
            return contentString
        except:
            self.postMessage('[-] Cannot connect to ' + self.FullURL)

class SingleResultsSite(Site):
    """
    SingleResultsSite inherits from the Site object and represents
    a site that is being used that has a single result returned.

    Public Method(s):
    getContentList

    Instance variable(s):
    _site
    """

    def __init__(self, site):
        """
        Class constructor. Assigns a site from the parameter into the _site
        instance variable. This is a play on the decorator pattern.

        Argument(s):
        site -- the site that we will decorate.

        Return value(s):
        Nothing is returned from this Method.
        """
        self._site = site
        super(SingleResultsSite, self).__init__(self._site.URL, self._site.WebRetrieveDelay, self._site.TargetType,\
                                               self._site.ReportStringForResult, self._site.Target, \
                                               self._site.FriendlyName, self._site.RegEx, self._site.FullURL, \
                                               self._site.ImportantPropertyString, self._site.Params, \
                                               self._site.Headers, self._site.APIKey)
        self.postMessage(self.UserMessage + " " + self.FullURL)
        websitecontent = self.getContentList()
        if websitecontent is not None:
            self.addResults(websitecontent)

    def getContentList(self):
        """
        Retrieves a list of information retrieved from the sites defined
        in the sites.xml configuration file.
        Returns the list of found information from the sites being used
        as resources or returns None if the site cannot be discovered.

        Argument(s):
        No arguments are required.

        Return value(s):
        list -- information found from a web site being used as a resource.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            content = self.getWebScrape()
            repattern = re.compile(self.RegEx, re.IGNORECASE)
            foundlist = re.findall(repattern, content)
            return foundlist
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

class MultiResultsSite(Site):
    """
    MultiResultsSite inherits from the Site object and represents
    a site that is being used that has multiple results returned.

    Public Method(s):
    addResults
    getContentList

    Instance variable(s):
    _site
    _results
    """

    def __init__(self, site):
        """
        Class constructor. Assigns a site from the parameter into the _site
        instance variable. This is a play on the decorator pattern.

        Argument(s):
        site -- the site that we will decorate.

        Return value(s):
        Nothing is returned from this Method.
        """
        self._site = site
        super(MultiResultsSite,self).__init__(self._site.URL, self._site.WebRetrieveDelay, self._site.TargetType,\
                                              self._site.ReportStringForResult, self._site.Target, \
                                              self._site.FriendlyName, self._site.RegEx, self._site.FullURL, \
                                              self._site.ImportantPropertyString, self._site.Params, \
                                              self._site.Headers, self._site.APIKey)        
        self._results = [[] for x in xrange(len(self._site.RegEx))]
        self.postMessage(self.UserMessage + " " + self.FullURL)
        for index in range(len(self.RegEx)):
            websitecontent = self.getContentList(index)
            if websitecontent is not None:
                self.addResults(websitecontent, index)

    def addResults(self, results, index):
        """
        Assigns the argument to the _results instance variable to build
        the list or results retrieved from the site. Assign None to the
        _results instance variable if the argument is empty.

        Argument(s):
        results -- list of results retrieved from the site.
        index -- integer value representing the index of the result found.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        # if no return from site, seed the results with an empty list
        if results is None or len(results) == 0:
            self._results[index] = None
        else:
            self._results[index] = results

    def getContentList(self, index):
        """
        Retrieves a list of information retrieved from the sites defined
        in the sites.xml configuration file.
        Returns the list of found information from the sites being used
        as resources or returns None if the site cannot be discovered.

        Argument(s):
        index -- the integer representing the index of the regex list.

        Return value(s):
        list -- information found from a web site being used as a resource.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            content = self.getWebScrape()
            repattern = re.compile(self.RegEx[index], re.IGNORECASE)
            foundlist = re.findall(repattern, content)
            return foundlist
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

class PostTransactionPositiveCapableSite(Site):
    """
    PostTransactionPositiveCapableSite inherits from the Site object
    and represents a site that may need to post information.

    Public Method(s):
    addMultiResults
    getContentList
    getContent
    postIsNecessary
    submitPost

    Instance variable(s):
    _site
    _postByDefault
    """

    def __init__(self, site, postbydefault):
        """
        Class constructor. Assigns a site from the parameter into the _site
        instance variable. This is a play on the decorator pattern. Also
        assigns the postbydefault parameter to the _postByDefault instance
        variable to determine if the Automater should post information
        to a site. By default Automater will NOT post information.

        Argument(s):
        site -- the site that we will decorate.
        postbydefault -- a Boolean representing whether a post will occur.

        Return value(s):
        Nothing is returned from this Method.
        """
        self._site = site
        self._postByDefault = postbydefault
        # first entry of regexlist is the check - if we find something here (positive), there is no list of regexs and thus
        # we cannot run the post
        if isinstance(self._site.RegEx, basestring):
            return
        else:
            regextofindforpost = self._site.RegEx[0]
            newregexlist = self._site.RegEx[1:]
            super(PostTransactionPositiveCapableSite, self).__init__(self._site.URL, self._site.WebRetrieveDelay, \
                                                                     self._site.TargetType, self._site.ReportStringForResult, \
                                                                     self._site.Target, self._site.FriendlyName, \
                                                                     newregexlist, self._site.FullURL, \
                                                                     self._site.ImportantPropertyString, \
                                                                     self._site.Params, self._site.Headers, \
                                                                     self._site.APIKey)            
            self.postMessage(self.UserMessage + " " + self.FullURL)
            content = self.getContent()
            if content != None:
                if self.postIsNecessary(regextofindforpost, content) and self.Params is not None and self.Headers is not None:
                    print '[-] This target requires a submission. Submitting now, this may take a moment.'
                    content = self.submitPost(self.Params, self.Headers)
                else:
                    pass
                if content != None:
                    if not isinstance(self.FriendlyName, basestring):#this is a multi instance
                        self._results = [[] for x in xrange(len(self.RegEx))]
                        for index in range(len(self.RegEx)):
                            self.addMultiResults(self.getContentList(content, index), index)
                    else:#this is a single instance
                        self.addResults(self.getContentList(content))

    def addMultiResults(self, results, index):
        """
        Assigns the argument to the _results instance variable to build
        the list or results retrieved from the site. Assign None to the
        _results instance variable if the argument is empty.

        Argument(s):
        results -- list of results retrieved from the site.
        index -- integer value representing the index of the result found.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        # if no return from site, seed the results with an empty list
        if results is None or len(results) == 0:
            self._results[index] = None
        else:
            self._results[index] = results

    def getContentList(self, content, index=-1):
        """
        Retrieves a list of information retrieved from the sites defined
        in the sites.xml configuration file.
        Returns the list of found information from the sites being used
        as resources or returns None if the site cannot be discovered.

        Argument(s):
        content -- string representation of the web site being used
        as a resource.
        index -- the integer representing the index of the regex list.

        Return value(s):
        list -- information found from a web site being used as a resource.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            if index == -1: # this is a return for a single instance site
                repattern = re.compile(self.RegEx, re.IGNORECASE)
                foundlist = re.findall(repattern, content)
                return foundlist
            else: # this is the return for a multisite
                repattern = re.compile(self.RegEx[index], re.IGNORECASE)
                foundlist = re.findall(repattern, content)
                return foundlist
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

    def getContent(self):
        """
        Attempts to retrieve a string from a web site. String retrieved is
        the entire web site including HTML markup.
        Returns the string representing the entire web site including the
        HTML markup retrieved from the site.

        Argument(s):
        No arguments are required.

        Return value(s):
        string.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            content = self.getWebScrape()
            return content
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

    def postIsNecessary(self, regex, content):
        """
        Checks to determine if the user wants the Automater to post information
        if the site takes a post. The user does this through the argument
        switch --p. By default this is False. If the regex given is found
        on the site, and a post is requested, a post will be attempted.
        Returns True if --p is used and a regex is found on the site, else
        return False.

        Argument(s):
        regex -- string regex that will be searched for on the web site used
        as a resource.
        content -- string that contains entire web site being used as a
        resource including HTML markup information.

        Return value(s):
        Boolean.

        Restriction(s):
        The Method has no restrictions.
        """
        # check if the user set to post or not on the cmd line
        if not self._postByDefault:
            return False
        else:
            repattern = re.compile(regex, re.IGNORECASE)
            found = re.findall(repattern, content)
            if found:
                return True
            else:
                return False
        # here to catch any fall through
        return False

    def submitPost(self, raw_params, headers):
        """
        Submits information to a web site being used as a resource that
        requires a post of information.
        Returns a string that contains entire web site being used as a
        resource including HTML markup information.

        Argument(s):
        raw_params -- string info detailing parameters provided from
        sites.xml configuration file in the params XML tag.
        headers -- string info detailing headers provided from
        sites.xml configuration file in the headers XML tag.

        Return value(s):
        string -- contains entire web site being used as a
        resource including HTML markup information.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            url = (self.URL)
            params = urllib.urlencode(raw_params)
            request = urllib2.Request(url, params, headers)
            page = urllib2.urlopen(request)
            page = page.read()
            content = str(page)
            return content
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

class PostTransactionAPIKeySite(Site):
    """
    PostTransactionAPIKeySite inherits from the Site object
    and represents a site that needs an API Key for discovering
    information.

    Public Method(s):
    addMultiResults
    getContentList
    submitPost

    Instance variable(s):
    _site
    """

    def __init__(self, site):
        """
        Class constructor. Assigns a site from the parameter into the _site
        instance variable. This is a play on the decorator pattern.

        Argument(s):
        site -- the site that we will decorate.

        Return value(s):
        Nothing is returned from this Method.
        """
        self._site = site
        super(PostTransactionAPIKeySite,self).__init__(self._site.URL, self._site.WebRetrieveDelay, self._site.TargetType, \
                                                       self._site.ReportStringForResult, self._site.Target, \
                                                       self._site.FriendlyName, self._site.RegEx, self._site.FullURL, \
                                                       self._site.ImportantPropertyString, self._site.Params, \
                                                       self._site.Headers, self._site.APIKey)
        self.postMessage(self.UserMessage + " " + self.FullURL)
        content = self.submitPost(self.Params, self.Headers)
        if content != None:
            if not isinstance(self.FriendlyName, basestring):#this is a multi instance
                self._results = [[] for x in xrange(len(self.RegEx))]
                for index in range(len(self.RegEx)):
                    self.addMultiResults(self.getContentList(content, index), index)
            else:#this is a single instance
                self.addResults(self.getContentList(content))

    def addMultiResults(self, results, index):
        """
        Assigns the argument to the _results instance variable to build
        the list or results retrieved from the site. Assign None to the
        _results instance variable if the argument is empty.

        Argument(s):
        results -- list of results retrieved from the site.
        index -- integer value representing the index of the result found.

        Return value(s):
        Nothing is returned from this Method.

        Restriction(s):
        The Method has no restrictions.
        """
        # if no return from site, seed the results with an empty list
        if results is None or len(results) == 0:
            self._results[index] = None
        else:
            self._results[index] = results

    def getContentList(self, content, index = -1):
        """
        Retrieves a list of information retrieved from the sites defined
        in the sites.xml configuration file.
        Returns the list of found information from the sites being used
        as resources or returns None if the site cannot be discovered.

        Argument(s):
        content -- string representation of the web site being used
        as a resource.
        index -- the integer representing the index of the regex list.

        Return value(s):
        list -- information found from a web site being used as a resource.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            if index == -1: # this is a return for a single instance site
                repattern = re.compile(self.RegEx, re.IGNORECASE)
                foundlist = re.findall(repattern, content)
                return foundlist
            else: # this is the return for a multisite
                repattern = re.compile(self.RegEx[index], re.IGNORECASE)
                foundlist = re.findall(repattern, content)
                return foundlist
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

    def submitPost(self, raw_params, headers):
        """
        Submits information to a web site being used as a resource that
        requires a post of information.
        Returns a string that contains entire web site being used as a
        resource including HTML markup information.

        Argument(s):
        raw_params -- string info detailing parameters provided from
        sites.xml configuration file in the params XML tag.
        headers -- string info detailing headers provided from
        sites.xml configuration file in the headers XML tag.

        Return value(s):
        string -- contains entire web site being used as a
        resource including HTML markup information.

        Restriction(s):
        The Method has no restrictions.
        """
        try:
            url = (self.FullURL)
            params = urllib.urlencode(raw_params)
            request = urllib2.Request(url, params, headers)
            page = urllib2.urlopen(request)
            page = page.read()
            content = str(page)
            return content
        except:
            self.postMessage(self.ErrorMessage + " " + self.FullURL)
            return None

########NEW FILE########
__FILENAME__ = utilities
"""
The utilities.py module handles all utility functions that Automater
requires.

Class(es):
Parser -- Class to handle standard argparse functions with
a class-based structure.
IPWrapper -- Class to provide IP Address formatting and parsing.

Function(s):
No global exportable functions are defined.

Exception(s):
No exceptions exported.
"""
import argparse
import re
import os

class Parser(object):
    """
    Parser represents an argparse object representing the
    program's input parameters.
    
    Public Method(s):
    hasHTMLOutFile
    (Property) HTMLOutFile
    hasTextOutFile
    (Property) TextOutFile
    hasCSVOutSet
    (Property) CSVOutFile
    (Property) Delay
    print_help
    hasTarget
    hasNoTarget
    (Property) Target
    hasInputFile
    (Property) Source
    hasSource
    hasPost
    (Property) InputFile
    
    Instance variable(s):
    _parser
    args
    """
    
    def __init__(self, desc):
        """
        Class constructor. Adds the argparse info into the instance variables.
        
        Argument(s):
        desc -- ArgumentParser description.
        
        Return value(s):
        Nothing is returned from this Method.
        """
        # Adding arguments
        self._parser = argparse.ArgumentParser(description = desc)
        self._parser.add_argument('target', help = 'List one IP Address (CIDR or dash notation accepted), URL or Hash to query or pass the filename of a file containing IP Address info, URL or Hash to query each separated by a newline.')
        self._parser.add_argument('-o', '--output', help = 'This option will output the results to a file.')
        self._parser.add_argument('-w', '--web', help = 'This option will output the results to an HTML file.')
        self._parser.add_argument('-c', '--csv', help = 'This option will output the results to a CSV file.')
        self._parser.add_argument('-d', '--delay', type=int, default = 2, help = 'This will change the delay to the inputted seconds. Default is 2.')
        self._parser.add_argument('-s', '--source', help = 'This option will only run the target against a specific source engine to pull associated domains.  Options are defined in the name attribute of the site element in the XML configuration file')
        self._parser.add_argument('--p', action = "store_true", help = 'This option tells the program to post information to sites that allow posting. By default the program will NOT post to sites that require a post.')
        self.args = self._parser.parse_args()

    def hasHTMLOutFile(self):
        """
        Checks to determine if user requested an output file formatted in HTML.
        Returns True if user requested HTML output, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.web:
            return True
        else:
            return False

    @property
    def HTMLOutFile(self):
        """
        Checks if there is an HTML output requested.
        Returns string name of HTML output file if requested
        or None if not requested.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- Name of an output file to write to system.
        None -- if web output was not requested.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasHTMLOutFile():
            return self.args.web
        else:
            return None

    def hasTextOutFile(self):
        """
        Checks to determine if user requested an output text file.
        Returns True if user requested text file output, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.output:
            return True
        else:
            return False

    @property
    def TextOutFile(self):
        """
        Checks if there is a text output requested.
        Returns string name of text output file if requested
        or None if not requested.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- Name of an output file to write to system.
        None -- if output file was not requested.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasTextOutFile():
            return self.args.output
        else:
            return None

    def hasCSVOutSet(self):
        """
        Checks to determine if user requested an output file delimited by commas.
        Returns True if user requested file output, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.csv:
            return True
        else:
            return False

    @property
    def CSVOutFile(self):
        """
        Checks if there is a comma delimited output requested.
        Returns string name of comma delimited output file if requested
        or None if not requested.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- Name of an comma delimited file to write to system.
        None -- if comma delimited output was not requested.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasCSVOutSet():
            return self.args.csv
        else:
            return None

    @property
    def Delay(self):
        """
        Returns delay set by input parameters to the program.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- String containing integer to tell program how long to delay
        between each site query. Default delay is 2 seconds.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        return self.args.delay

    def print_help(self):
        """
        Returns standard help information to determine usage for program.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- Standard argparse help information to show program usage.
        
        Restriction(s):
        This Method has no restrictions.
        """
        self._parser.print_help()

    def hasTarget(self):
        """
        Checks to determine if a target was provided to the program.
        Returns True if a target was provided, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.target is None:
            return False
        else:
            return True

    def hasNoTarget(self):
        """
        Checks to determine if a target was provided to the program.
        Returns False if a target was provided, True if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        return not(self.hasTarget())

    @property
    def Target(self):
        """
        Checks to determine the target info provided to the program.
        Returns string name of target or string name of file
        or None if a target is not provided.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- String target info or filename based on target parameter to program.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasNoTarget():
            return None
        else:
            return self.args.target

    def hasInputFile(self):
        """
        Checks to determine if input file is the target of the program.
        Returns True if a target is an input file, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if os.path.exists(self.args.target) and os.path.isfile(self.args.target):
            return True
        else:
            return False

    @property
    def Source(self):
        """
        Checks to determine if a source parameter was provided to the program.
        Returns string name of source or None if a source is not provided
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- String source name based on source parameter to program.
        None -- If the -s parameter is not used.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasSource():
            return self.args.source
        else:
            return None

    def hasSource(self):
        """
        Checks to determine if -s parameter and source name
        was provided to the program.
        Returns True if source name was provided, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.source:
            return True
        else:
            return False

    def hasPost(self):
        """
        Checks to determine if --p parameter was provided to the program.
        Returns True if --p was provided, False if not.
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        Boolean.
        
        Restriction(s):
        The Method has no restrictions.
        """
        if self.args.p:
            return True
        else:
            return False

    @property
    def InputFile(self):
        """
        Checks to determine if an input file string representation of
        a target was provided as a parameter to the program.
        Returns string name of file or None if file name is not provided
        
        Argument(s):
        No arguments are required.
        
        Return value(s):
        string -- String file name based on target filename parameter to program.
        None -- If the target is not a filename.
        
        Restriction(s):
        This Method is tagged as a Property.
        """
        if self.hasNoTarget():
            return None
        elif self.hasInputFile():
            return self.Target
        else:
            return None

class IPWrapper(object):
    """
    IPWrapper provides Class Methods to enable checks
    against strings to determine if the string is an IP Address
    or an IP Address in CIDR or dash notation.
    
    Public Method(s):
    (Class Method) isIPorIPList
    (Class Method) getTarget
    
    Instance variable(s):
    No instance variables.
    """

    @classmethod
    def isIPorIPList(self, target):
        """
        Checks if an input string is an IP Address or if it is
        an IP Address in CIDR or dash notation.
        Returns True if IP Address or CIDR/dash. Returns False if not.

        Argument(s):
        target -- string target provided as the first argument to the program.

        Return value(s):
        Boolean.

        Restriction(s):
        This Method is tagged as a Class Method
        """
        # IP Address range using prefix syntax
        ipRangePrefix = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}')
        ipRgeFind = re.findall(ipRangePrefix,target)
        if (ipRgeFind is not None or len(ipRgeFind) != 0):
            return True
        ipRangeDash = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}')
        ipRgeDashFind = re.findall(ipRangeDash,target)
        if (ipRgeDashFind is not None or len(ipRgeDashFind) != 0):
            return True
        ipAddress = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        ipFind = re.findall(ipAddress,target)
        if (ipFind is not None and len(ipFind) != 0):
            return True
        
        return False

    @classmethod
    def getTarget(self, target):
        """
        Determines whether the target provided is an IP Address or 
        an IP Address in CIDR or dash notation. Then creates a list
        that can be utilized as targets by the program.
        Returns a list of string IP Addresses that can be used as targets.
        
        Argument(s):
        target -- string target provided as the first argument to the program.
        
        Return value(s):
        Iterator of string(s) representing IP Addresses.
        
        Restriction(s):
        This Method is tagged as a Class Method
        """
        # IP Address range using prefix syntax
        ipRangePrefix = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}', re.IGNORECASE)
        ipRgeFind = re.findall(ipRangePrefix, target)
        ipRangeDash = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}')
        ipRgeDashFind = re.findall(ipRangeDash, target)
        ipAddress = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        ipFind = re.findall(ipAddress, target)
        if ipRgeFind is not None and len(ipRgeFind) > 0:
            # this can be used if we ever get bigger than a class C
            # but truthfully we don't need to split the whole address
            # since we'll only be using the last octet.
            iplist = target[:target.index("/")].split(".")
            ipprefix = givenipprefix=target[target.index("/")+1:]
            # create a bytearry to hold the one byte
            # this would be 4 bytes for IPv4 and gives us the capability to grow
            # if we ever want to go larger than a class C
            bytearr = bytearray(2)
            bytearr[0] = int(iplist[3])
            # prefix must be class C or larger
            if int(givenipprefix) < 24:
                ipprefix = 24
            if int(givenipprefix) > 32 or int(givenipprefix) == 31:
                ipprefix = 32
                bytearr[1]=0
            else:
                bytearr[1]=pow(2,32-int(ipprefix))#-1

            if bytearr[0]>bytearr[1]:
                start=bytearr[0]
                last=bytearr[0]^bytearr[1]
            else:
                start=bytearr[0]
                last=bytearr[1]
            if start == last:
                yield target[:target.rindex(".")+1]+str(start)
            if start<last:
                for lastoctet in range(start,last):
                    yield target[:target.rindex(".")+1]+str(lastoctet)
            else:
                yield target[:target.rindex(".")+1]+str(start)
        # IP Address range seperated with a dash       
        elif ipRgeDashFind is not None and len(ipRgeDashFind) > 0:
            iplist = target[:target.index("-")].split(".")
            iplast = target[target.index("-")+1:]
            if int(iplist[3])<int(iplast):
                for lastoctet in range(int(iplist[3]),int(iplast)+1):
                    yield target[:target.rindex(".")+1]+str(lastoctet)
            else:
                yield target[:target.rindex(".")+1]+str(iplist[3])
        # it's just an IP address at this point
        else:
            yield target

########NEW FILE########
