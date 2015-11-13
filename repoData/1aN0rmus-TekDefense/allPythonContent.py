__FILENAME__ = Automater
Automater has moved to https://github.com/1aN0rmus/TekDefense-Automater

########NEW FILE########
__FILENAME__ = autorunMas
#!/usr/bin/python
 
import os
 
# MASTIFF Autorun
# @TekDefense
# www.TekDefense.com
# Quick script to autorun samples from maltrieve to MASTIFF
 
malwarePath = '/tmp/malware/'
 
for r, d, f in os.walk(malwarePath):
  for files in f:
		malware = malwarePath + files
		print malware
		os.system ('mas.py' + ' ' + malware) 

########NEW FILE########
__FILENAME__ = hashCollect
'''
hashCollect has been renamed moved to the link below:

https://github.com/1aN0rmus/TekDefense/blob/master/tekCollect.py
'''

########NEW FILE########
__FILENAME__ = MASTIFF2HTML
#!/usr/bin/python

import sqlite3, argparse, os

'''                                                                        
Author: Ian Ahl, 1aN0rmus@TekDefense.com
Created: 02/25/2013
'''

# variables
#mastiffDir = '/opt/work/log/' 
#dbName = 'mastiff.db'



# Adding command options
parser = argparse.ArgumentParser(description='Generate HTML From a specified sqlite DB')
parser.add_argument('-f', '--folder', help='Select the database directory. Must wnd in a "/". For example, /opt/work/log/')
parser.add_argument('-d', '--database', help='Enter a sqlite database name. For Example mastiff.db')
args = parser.parse_args()
if args.database:
    dbName=args.database
if args.folder:
    mastiffDir = args.folder
mastiffDB = mastiffDir + dbName
wwwDir = mastiffDir + 'www/'
if os.path.exists(mastiffDir + 'www'):
    pass
else:
    os.mkdir(mastiffDir + 'www')
# Connect to the MASTIFF DB
con = sqlite3.connect(mastiffDB)

with con:    
    
    cur = con.cursor()    
    # SQL Query
    cur.execute("SELECT * FROM MASTIFF")
    
    
    
    # SQL Server Results
    rows = cur.fetchall()
    

    # Generate Table data from the DB    
    print '[*] Generating mastiff.hmtl in ' + wwwDir
    for row in rows:
        uid = str(row[0])
        md5 = str(row[1])
        fileType = str(row[4])
        fuzzy = str(row[5])
        tableData = '<tr><td>' + uid + '</td><td><a href ="' + wwwDir + md5 + '.html">' + md5 + '</a></td><td>' + fileType + '</td><td>' + fuzzy + '</td><td></tr>'
        if os.path.isfile(wwwDir + 'mastiff.html'):
            f = open(wwwDir + 'mastiff.html', 'a')
            f.write(tableData)
        else:
            f = open(wwwDir + 'mastiff.html', "w")
            f.write('''
                <style type="text/css">
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
                }
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
            </style>
            <html>
            <body>
            <title> MASTIFF DB Results </title>
            <h1> MASTIFF DB Results </h1>
            <table id="table-3">
            <h2> Sample Details </h2>
            <tr>
            <th>ID</th>
            <th>MD5</th>
            <th>File Type</th>
            <th>Fuzzy Hash</th>
            </tr>
            '''
            + tableData
            )        
    f = open(wwwDir + 'mastiff.html', 'a')
    f.write(
        '''    
        </table>
        <br>
        <br>
        <h4>Created using @TekDefense MASTIFF2HTML.py  www.tekdefense.com; https://github.com/1aN0rmus/TekDefense</h4>
        </body>
        </html>
        ''')
    print '[*] Creating table in masitff.db called extended. May take a moment.'
    cur.execute('DROP TABLE IF EXISTS extended')
    cur.execute('CREATE TABLE extended(Id INTEGER PRIMARY KEY, md5 TEXT, Files TEXT)')
    con.commit()
    for r, d, f in os.walk(mastiffDir):
        for files in d:
            if len(files) == 32:
                md5 = files
                subDir = mastiffDir + md5 + '/'
                for r, d, f in os.walk(subDir):
                    for files2 in f:
                        inserter = md5 + ',' + files2
                        cur.execute('INSERT INTO extended(md5,Files) VALUES (?,?);', (md5,files2))
                        con.commit()
                  
    # SQL Query
    cur.execute('SELECT * FROM extended')
    con.text_factory = str
    # SQL Server Results
    rows = cur.fetchall()
    
    for row in rows:
        uid = str(row[0])
        md5 = str(row[1])
        fileName = str(row[2])
        print '[*] Generating html for each sample ' + wwwDir + md5 + '.html'
        tableData = '<tr><td>' + uid + '</td><td>' + md5 + '</td><td><a href ="' + mastiffDir + md5 + '/' + fileName +'">' + fileName + '</a></td></tr>'
        if os.path.isfile(wwwDir + md5 + '.html'):
            f = open(wwwDir + md5 + '.html', 'a')
            f.write(tableData)
        else:
            f = open(wwwDir + md5 + '.html', "w")
            f.write('''
            <style type="text/css">
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
            }
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
            </style>
            <html>
            <body>
            <title> MASTIFF DB Results </title>
            <h1> MASTIFF Malware Analysis Result </h1>
            <table id="table-3">
            <tr>
            <th>id</th>
            <th>md5</th>
            <th>Results</th>
            </tr>
            '''
            + tableData
            )
        
    # SQL Query
    cur.execute('SELECT DISTINCT md5 FROM extended')
    con.text_factory = str
    # SQL Server Results
    rows = cur.fetchall()
    
    for row in rows:
        md5 = str(row[0])        
        f = open(wwwDir + md5 + '.html', 'a')    
        f.write('''
        </table>
        <br>
        <br>
        <h6>Created using @TekDefense MASTIFF2HTML.py  www.tekdefense.com; https://github.com/1aN0rmus/TekDefense</h6>
        </body>
        </html>
        ''')
    print '[+] Operation complete'
    print '[*] View results at ' + wwwDir + 'mastiff.html'
    

########NEW FILE########
__FILENAME__ = playlogQuick
#!/usr/bin/python

import re, os

print '''
  ____  _             _              ___        _      _    
 |  _ \| | __ _ _   _| | ___   __ _ / _ \ _   _(_) ___| | __
 | |_) | |/ _` | | | | |/ _ \ / _` | | | | | | | |/ __| |/ /
 |  __/| | (_| | |_| | | (_) | (_| | |_| | |_| | | (__|   < 
 |_|   |_|\__,_|\__, |_|\___/ \__, |\__\_\\__,_|_|\___|_|\_\
                |___/         |___/                                                                           
Author: Ian Ahl, 1aN0rmus@TekDefense.com
Created: 02/12/2013
'''

# variables for the kippo logs, if your path is not the default from honeydrive, modify logPath. 
# if your log files are not named kippo.log or kippor.log.x please modify logPre.
logPre = 'kippo.log'
logPath = '/opt/kippo/log/'
outputFile = '/opt/kippo/log/attacklog.txt'
reSearch = 'SSHChannel\ssession.+\,(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]\s(.+)'
reCMD = '\,(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]\sCMD\:(.+)'
#reOut = 'Command\sfound\:\s(.+)'
sessionList = []

# open up the directory found in the logPath variable to find any files that start with the prefix from variable logPre.
# Opens each of those logfiles and uses regex to find to find the passwords and add them to a list.
for r, d, f in os.walk(logPath):
    for files in f:
        if files.startswith(logPre):
            #print files
            logFile = logPath + files
            #print logFile
            lines = open(logFile,'r').readlines()
            for i in lines:
                searchSession = re.search(reSearch,i)
                if searchSession is not None:
                    sessionList.append(searchSession.group())
# Removing duplicate entries with the set function.
# passwordList = list(set(passwordList))                   
# outputting results to the file defined in the outputFile variable.
# output = open(outputFile, 'w')
for i in sessionList:
    searchCMD = re.search(reCMD,i)
    #searchOutput = re.search(reOut,i)
    if searchCMD is not None:
        print (searchCMD.group(1) + '@honeypot#' + searchCMD.group(2))
    #elif searchOutput is not None:
    #    print(searchOutput.group(1))
    #else:
    #    print(i)
    # output.write(i + '\n')
# print 'Wordlist has been archived to ' + outputFile
    
           
            
            

            
        


########NEW FILE########
__FILENAME__ = regexTester
#!/usr/bin/python

'''
Created on Oct 19, 2012
Script to test regex against a file containing values 
to match.
@author 1aN0rmus@tekdefense.com
'''

import re

fileImport =open('sample.txt')

strFile=''

for line in fileImport:
    strFile += line

print(strFile)

regexValue = re.compile('\d{1,5}\s\w+\s\w{1,3}\.')
regexSearch = re.findall(regexValue,strFile)

if(regexSearch):
        print('String Found: '+ str(regexSearch))
else:
    print('Nothing Found')

########NEW FILE########
__FILENAME__ = tekCollect
#!/usr/bin/python

'''
This is tekCollect! This tool will scrape specified data types out of a URL or file.
@TekDefense
Ian Ahl | www.TekDefense.com | 1aN0rmus@tekDefense.com
*Some of the Regular Expressions were taken from http://gskinner.com/RegExr/
Version: 0.5

Changelog:
.5
[+] Quick update to add the WDIR Regex. This will pull Windows directories.
[+] Modified the URL regext to be less strict.
.4
[+] Fixed issue where -t IP4 returned URLs
[+] Added summary functions that shows what types of data are in a specified target.
[+] Modified the regex for many of the data types for better results
[+] Added several new data types: zip, twitter, doc, exe, MYSQL hash, Wordpress (WP) hash, IMG, FLASH
[+] Modified the way summary is displayed
[+] several improvements by machn1k (https://github.com/machn1k, http://twitter.com/machn1k)
[+] Made some modifications based on machn1k's changes
.3
[+] Added predefined data types that can be invoke with -t type
.2
[+] Expanded the script to allow custom regex with a -r 'regex here'
.1
[+] Replaced listTypes selction with loop
[+] Tool created and can only pull md5 hashes

TODO
[-] Proper hash values matching 
[-] Ability to accept multiple --types
[-] Summary sub options (Hash, Host, PII)
[-] Improved menu selections & functions
'''

import httplib2, re, sys, argparse
dTypes = 'MD5, SHA1, SHA256, MySQL, WP (Wordpress), Domain, URL, IP4, IP6, SSN, EMAIL, CCN, Twitter, DOC, EXE, ZIP, IMG '
# Adding arguments
parser = argparse.ArgumentParser(description='tekCollect is a tool that will scrape a file or website for specified data')
parser.add_argument('-u', '--url', help='This option is used to search for hashes on a website')
parser.add_argument('-f', '--file', help='This option is used to import a file that contains hashes')
parser.add_argument('-o', '--output', help='This option will output the results to a file.')
parser.add_argument('-r', '--regex', help='This option allows the user to set a custom regex value. Must encase in single or double quotes.')
parser.add_argument('-t', '--type', help='This option allows a user to choose the type of data they want to pull out. Currently supports ' + dTypes)
parser.add_argument('-s', '--summary', action='store_true', default=False, help='This options will show a summary of the data types in a file')
args = parser.parse_args()

# Setting some variables and lists 
regVal = ''    # Initial revVal
listResults = []
MD5 = '\W([a-fA-F0-9]{32})\W'
SHA1 = '[a-fA-F0-9]{40}'
SHA256 = '[a-fA-F0-9]{64}'
LM = '[a-fA-F0-9]{32}'
DOMAIN = '\W(\w+\.){1,4}(com|net|biz|cat|aero|asia|coop|info|int|jobs|mobi|museum|name|org|post|pre|tel|travel|xxx|edu|gov|mil|br|cc|ca|uk|ch|co|cx|de|fr|hk|jp|kr|nl|nr|ru|tk|ws|tw)[^a-fA-F0-9_-]'
URL = '(http\:\/\/|https\:\/\/)(.+\S)'
IP4 = '((?<![0-9])(?:(?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})[.](?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2}))(?![0-9]))'
IP6 = '(((([01]? d?\\d)|(2[0-5]{2}))\\.){3}(([01]?\\d?\\d)|(2[0-5]{2})))|(([A-F0-9]){4}(:|::)){1,7}(([A-F0-9]){4})'
SSN = '(\d{3}\-\d{2}\-\d{3})|(\d{3}\s\d{2}\s\d{3})'
EMAIL = '([a-zA-Z0-9\.-_]+@)([a-zA-Z0-9-]+\.)(com|net|biz|cat|aero|asia|coop|info|int|jobs|mobi|museum|name|org|post|pre|tel|travel|xxx|edu|gov|mil|br|cc|ca|uk|ch|co|cx|de|fr|hk|jp|kr|nl|nr|ru|tk|ws|tw)\W'
CCN = '\d{4}\s\d{4}\s\d{4}\s\d{2,4}|\d{4}\-\d{4}\-\d{4}\-\d{2,4}'
TWITTER = '(?<=^|(?<=[^a-zA-Z0-9-_\.]))(@)([A-Za-z]+[A-Za-z0-9]+)'
PHONE = ''
NTLM = ''
WDIR = '[a-zA-Z]\:\\\\.+'
DOC = '\W([\w-]+\.)(docx|doc|csv|pdf|xlsx|xls|rtf|txt|pptx|ppt)'
EXE = '\W([\w-]+\.)(exe|dll)'
ZIP = '\W([\w-]+\.)(zip|zipx|7z|rar|tar|gz)'
IMG = '\W([\w-]+\.)(jpeg|jpg|gif|png|tiff|bmp)'
FLASH = '\W([\w-]+\.)(flv|swf)'
MYSQL = '\*[a-fA-F0-9]{40}'
WP = '\$P\$\w{31}'
CISCO5 = ''
CISCO7 = ''

listTypes = [   ('MD5',MD5),
        ('SHA1',SHA1), 
            ('SHA256',SHA256), 
            ('MYSQL', MYSQL), 
                ('WP', WP), 
            ('DOMAIN', DOMAIN), 
            ('URL', URL), 
                ('EMAIL',EMAIL), 
            ('TWITTER', TWITTER), 
            ('IP4',IP4), 
            ('IP6',IP6), 
            ('DOC', DOC), 
            ('EXE', EXE), 
            ('ZIP', ZIP), 
            ('IMG', IMG),
            ('FLASH', FLASH),
            ('WDIR', WDIR),  
            ('SSN', SSN), 
            ('CCN',CCN)]

# Determining what type of data the user wants and setting the regex to the regVal variable for that data type
if args.type:
    for t in listTypes:
        if args.type.upper() == t[0]:
            regVal = t[1]
# If summarry or custom regex option is selected pass to later functions
elif args.summary == True:
    pass
elif args.regex != None:
    pass

# If the user wants to set a custom regex, it is collected here and added to the regVal variable.
if args.regex:
    regVal = str(args.regex)

# If the user does not give us a file or url to scrape show help and exit.
if args.url == None and args.file == None:
    parser.print_help()
    sys.exit()

# If the user wants to output the results to a file this will collect the name of the file and redirect all sys.stdout to that file
if args.output:
    oFile = args.output
    print '[+] Printing results to file:', args.output
    o = open(oFile, "w")
    sys.stdout = o

# If the target to scrape is a file open the file create a string for each line, regex the string for the data type specified by the regVal, and put results in a list.
if args.file:
    if args.summary == True:
        iFile = args.file
        fileImport =open(iFile)
        strFile=''
        print '[*] Summary of files types for: ' + iFile        
        for line in fileImport:
            strFile += line
        for i in listTypes:
            regVal = i[1]
            regexValue = re.compile(regVal)
            regexSearch = re.findall(regexValue,strFile)
            listResults = []
            for j in regexSearch:
                listResults.append(j)
            #for i in tup in 
            listResults = list(set(listResults)) 
            for k in listResults:
                ''.join(k) 
            print '[+] ' + i[0] + ': ' + str(len(listResults))
        sys.exit()  
    else:
        iFile = args.file
        fileImport =open(iFile)
        strFile=''
        for line in fileImport:
            strFile += line    
        #print strFile
        regexValue = re.compile(regVal)
        regexSearch = re.findall(regexValue,strFile)
        for i in regexSearch:
            listResults.append(i)

# If the target to scrape is a url conect to and get content from the url, create a string out of the content, regex the string for the data type specified by the regVal, and put results in a list.    
if args.url:
    if args.summary == True:
        url = args.url
        h = httplib2.Http(".cache")
        resp, content = h.request((url), "GET")
        contentString = (str(content))
        print '[*] Summary of files types for: ' + url
        for i in listTypes:
            regVal = i[1]
            regexValue = re.compile(regVal)
            regexSearch = re.findall(regexValue,contentString)
            listResults = []
            for j in regexSearch:
                listResults.append(j)
            #for i in tup in 
            listResults = list(set(listResults)) 
            for k in listResults:
                ''.join(k) 
            print '[+] ' + i[0] + ': ' + str(len(listResults))
        sys.exit()
    else:
        url = args.url
        h = httplib2.Http(".cache")
        resp, content = h.request((url), "GET")
        contentString = (str(content))
        regexValue = re.compile(regVal)
        regexSearch = re.findall(regexValue,contentString)
        for i in regexSearch:
            listResults.append(i)

if regVal == '':
    print '[-] ' + str(args.type) + ' is not a valid type. \nCurrent valid types are ' + dTypes
    sys.exit()
    
# Remove duplicates from the list and print
listResults = list(set(listResults))  
for i in listResults:
    print ''.join(i)

if __name__ == '__main__':
    pass

########NEW FILE########
