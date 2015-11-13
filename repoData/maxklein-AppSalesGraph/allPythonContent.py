__FILENAME__ = appdailysales
#!/usr/bin/python
#
# appdailysales.py
#
# iTune Connect Daily Sales Reports Downloader
# Copyright 2008-2009 Kirby Turner
#
# Version 1.9
#
# Latest version and additional information available at:
#   http://appdailysales.googlecode.com/
#
#
# This script will download yesterday's daily sales report from
# the iTunes Connect web site.  The downloaded file is stored
# in the same directory containing the script file.  Note: if
# the download file already exists then it will be overwritten.
#
# The iTunes Connect web site has dynamic urls and form field
# names.  In other words, these values change from session to
# session.  So to get to the download file we must navigate  
# the site and webscrape the pages.  Joy, joy.
#
#
# Contributors:
#   Leon Ho
#   Rogue Amoeba Software, LLC
#   Keith Simmons
#   Andrew de los Reyes
#   Maarten Billemont
#   Max Klein
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


# -- Change the following to match your credentials --
# -- or use the command line options.               --
appleId = 'Your Apple Id' 
password = 'Your Password'
outputDirectory = ''
unzipFile = False
verbose = False
daysToDownload = 1
dateToDownload = None
# ----------------------------------------------------


import urllib
import urllib2
import cookielib
import datetime
import re
import getopt
import sys
import os
import gzip
import StringIO
import traceback
import wx
from result_event  import ResultEvent

shutDownSalesDownload = False

try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class ITCException(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value);

# The class ReportOptions defines a structure for passing
# report options to the download routine. The expected
# data attributes are:
#   appleId
#   password
#   outputDirectory
#   unzipFile
#   verbose
#   daysToDownload
# Note that the class attributes will default to the global
# variable value equivalent.
class ReportOptions:
    def __getattr__(self, attrname):
        if attrname == 'appleId':
            return appleId
        elif attrname == 'password':
            return password
        elif attrname == 'outputDirectory':
            return outputDirectory
        elif attrname == 'unzipFile':
            return unzipFile
        elif attrname == 'verbose':
            return verbose
        elif attrname == 'daysToDownload':
            return daysToDownload
        elif attrname == 'dateToDownload':
            return dateToDownload
        else:
            raise AttributeError, attrname



# There is an issue with Python 2.5 where it assumes the 'version'
# cookie value is always interger.  However, itunesconnect.apple.com
# returns this value as a string, i.e., "1" instead of 1.  Because
# of this we need a workaround that "fixes" the version field.
#
# More information at: http://bugs.python.org/issue3924


class MyCookieJar(cookielib.CookieJar):
    def _cookie_from_cookie_tuple(self, tup, request):
        name, value, standard, rest = tup
        version = standard.get('version', None)
        if version is not None:
            version = version.replace('"', '')
            standard["version"] = version
        return cookielib.CookieJar._cookie_from_cookie_tuple(self, tup, request)


def showCookies(cj):
    for index, cookie in enumerate(cj):
        print index, ' : ', cookie
    

def readHtml(opener, url, data=None):
    request = urllib2.Request(url, data)
    urlHandle = opener.open(request)
    html = urlHandle.read()
    return html


def downloadFile(options, notify_window, days_to_download):
    #if options.verbose == True:
    
    global shutDownSalesDownload
    
    wx.PostEvent(notify_window, ResultEvent("Connecting..."))
        # print '-- begin script --'
    
    urlBase = 'https://itts.apple.com%s'

    cj = MyCookieJar();
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    if shutDownSalesDownload == True: return
    
    # Go to the iTunes Connect website and retrieve the
    # form action for logging into the site.
    urlWebsite = urlBase % '/cgi-bin/WebObjects/Piano.woa'
    html = readHtml(opener, urlWebsite)
    match = re.search('" action="(.*)"', html)
    urlActionLogin = urlBase % match.group(1)

    if shutDownSalesDownload == True: return None, None
    wx.PostEvent(notify_window, ResultEvent("Connected! Logging in..."))
    
    # Login to iTunes Connect web site and go to the sales 
    # report page, get the form action url and form fields.  
    # Note the sales report page will actually load a blank 
    # page that redirects to the static URL. Best guess here 
    # is that the server is setting some session variables 
    # or something.
    webFormLoginData = urllib.urlencode({'theAccountName':options.appleId, 'theAccountPW':options.password, '1.Continue.x':'0', '1.Continue.y':'0'})
    html = readHtml(opener, urlActionLogin, webFormLoginData)
    
    html_lc = html.lower()
    if html_lc.find("piano-sign in") > 0:
        wx.PostEvent(notify_window, ResultEvent("SalesDownloadError: Could not login"))
        return [], True
    
    if html_lc.find("checkvendoridnumber") > 0:
        # Oh, oh, we have a multiple vendor login
        
        soup = BeautifulSoup.BeautifulSoup( html )
        
        # Let's get all vendor IDs
        selectField = soup.find( 'select', attrs={'id': 'selectName'} )
        html_options = selectField.findAll('option')
        for option in html_options:
            val = option['value']
            if val == "0": continue
            
            # Get the url to post to
            form = soup.find( 'form', attrs={'name': 'superPage' } )
            urlSelectVendor = urlBase % form['action']
            wosid1 = soup.find( 'input', attrs={'name': 'wosid'} )['value']
            # countryName = soup.find( 'input', attrs={'id': 'hiddenCountryName'} )['value']
            
            # This is fragile. It should be parsed from the html
            vendorSelectData = urllib.urlencode({'vndrid': val, 'wosid':wosid1, '9.6.0':val, '9.18':"", 'SubmitBtn':'Submit'})
            
            html = readHtml(opener, urlSelectVendor, vendorSelectData)
            
            if html.find("selDateType") > 0:
                # Looks like we found the page
                html_lc = html.lower()
                break
            break # Let's just do first vendor for now

        if html.find("selDateType") <= 0:
            # Page was not opened
            wx.PostEvent(notify_window, ResultEvent("SalesDownloadError: Multiple Vendors not supported"))
            return [], True
            
    if shutDownSalesDownload == True: return None, None
    
    # Get the form field names needed to download the report.
    successfully_parsed = False
    if BeautifulSoup:
        # if options.verbose == True:
        wx.PostEvent(notify_window, ResultEvent("Logged in! Accessing sales data"))
            
            # print 'using BeautifulSoap for HTML parsing'
        try:
            soup = BeautifulSoup.BeautifulSoup( html )
            # print html
            
            form = soup.find( 'form', attrs={'name': 'frmVendorPage' } )
        
            try:
                urlDownload = urlBase % form['action']
            except TypeError:
                if html.find("Session Time Out") != -1:
                    wx.PostEvent(notify_window, ResultEvent("Session timeout"))
                else:
                    wx.PostEvent(notify_window, ResultEvent("Invalid Data Returned. Try again later."))
                return
        
            fieldNameReportType = soup.find( 'select', attrs={'id': 'selReportType'} )['name']
            fieldNameReportPeriod = soup.find( 'select', attrs={'id': 'selDateType'} )['name']
            fieldNameDayOrWeekSelection = soup.find( 'input', attrs={'name': 'hiddenDayOrWeekSelection'} )['name'] #This is kinda redundant
            fieldNameSubmitTypeName = soup.find( 'input', attrs={'name': 'hiddenSubmitTypeName'} )['name'] #This is kinda redundant, too
            successfully_parsed = True
        except:
            pass
        

   
    if successfully_parsed == False:
        match = re.findall('name="frmVendorPage" action="(.*)"', html)
        urlDownload = urlBase % match[0]
        match = re.findall('name="(.*?)"', html)
        fieldNameReportType = match[4] # selReportType
        fieldNameReportPeriod = match[5] # selDateType
        fieldNameDayOrWeekSelection = match[8] # hiddenDayOrWeekSelection
        fieldNameSubmitTypeName = match[9] # hiddenSubmitTypeName

    
    wx.PostEvent(notify_window, ResultEvent("Requesting daily sales..."))
    
    if shutDownSalesDownload == True: return None, None
    
    # Ah...more fun.  We need to post the page with the form
    # fields collected so far.  This will give us the remaining
    # form fields needed to get the download file.
    webFormSalesReportData = urllib.urlencode({fieldNameReportType:'Summary', fieldNameReportPeriod:'Daily', fieldNameDayOrWeekSelection:'Daily', fieldNameSubmitTypeName:'ShowDropDown'})
    html = readHtml(opener, urlDownload, webFormSalesReportData)

    if shutDownSalesDownload == True: return None, None
    
    if BeautifulSoup:
        soup = BeautifulSoup.BeautifulSoup( html )
        form = soup.find( 'form', attrs={'name': 'frmVendorPage' } )
        try:
            urlDownload = urlBase % form['action']
        except TypeError:
            wx.PostEvent(notify_window, ResultEvent("Invalid Data Returned. Try again later."))
            return
        
        select = soup.find( 'select', attrs={'id': 'dayorweekdropdown'} )
        fieldNameDayOrWeekDropdown = select['name']
    else:
        match = re.findall('name="frmVendorPage" action="(.*)"', html)
        urlDownload = urlBase % match[0]
        match = re.findall('name="(.*?)"', html)
        fieldNameDayOrWeekDropdown = match[6]

    # Set the list of report dates.
    reportDates = []
    if not days_to_download == None:
        for a_day in days_to_download:
            date = '%02i/%02i/%i' % (a_day.month, a_day.day, a_day.year)
            reportDates.append( date )
    else:
        if options.dateToDownload == None:
            for i in range(int(options.daysToDownload)):
                today = datetime.date.today() - datetime.timedelta(i + 1)
                date = '%02i/%02i/%i' % (today.month, today.day, today.year)
                reportDates.append( date )
        else:
            reportDates = [options.dateToDownload]
        
    if options.verbose == True:
        wx.PostEvent(notify_window, ResultEvent("Retrieving for dates:" + reportDates.__str__()))
        
        # print 'reportDates: ', reportDates

    unavailableCount = 0
    filenames = []
    for downloadReportDate in reportDates:
        wx.PostEvent(notify_window, ResultEvent("Requesting: " + downloadReportDate))
        
        if shutDownSalesDownload == True: return None, None
        
        # And finally...we're ready to download yesterday's sales report.
        webFormSalesReportData = urllib.urlencode({fieldNameReportType:'Summary', fieldNameReportPeriod:'Daily', fieldNameDayOrWeekDropdown:downloadReportDate, 'download':'Download', fieldNameDayOrWeekSelection:downloadReportDate, fieldNameSubmitTypeName:'Download'})
        urlHandle = opener.open(urlDownload, webFormSalesReportData)
        try:
            if shutDownSalesDownload == True: return None, None
            
            filename = urlHandle.info().getheader('content-disposition').split('=')[1]
            
            # For some reason, there are geese feet on the filename
            filename = filename.replace("'", "")
            filename = filename.replace("\"", "")
            
            # filesize = urlHandle.info().getheader('size')
            # wx.PostEvent(notify_window, ResultEvent("Getting Sales: " + downloadReportDate + " (" + filesize + ")"))
            
            filebuffer = urlHandle.read()
            urlHandle.close()

            if options.unzipFile == True:
                if options.verbose == True:
                    wx.PostEvent(notify_window, ResultEvent("Unzipping:" + filename))
                    # print 'unzipping archive file: ', filename
                #Use GzipFile to de-gzip the data
                ioBuffer = StringIO.StringIO( filebuffer )
                gzipIO = gzip.GzipFile( 'rb', fileobj=ioBuffer )
                filebuffer = gzipIO.read()

            filename = os.path.join(options.outputDirectory, filename)
            if options.unzipFile == True and filename[-3:] == '.gz': #Chop off .gz extension if not needed
                filename = os.path.splitext( filename )[0]

            if options.verbose == True:
                print 'saving download file:', filename

            downloadFile = open(filename, 'w')
            downloadFile.write(filebuffer)
            downloadFile.close()

            filenames.append( filename )
        except AttributeError:
            wx.PostEvent(notify_window, ResultEvent('%s report is not available - try again later.' % downloadReportDate))
            # print '%s report is not available - try again later.' % downloadReportDate
            unavailableCount += 1

    # if unavailableCount > 0:
    #    raise ITCException, '%i report(s) not available - try again later' % unavailableCount

    if options.verbose == True:
        wx.PostEvent(notify_window, ResultEvent("Sales Report Download Complete"))

    return filenames, False

########NEW FILE########
__FILENAME__ = apps_update
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

import os
import re
import time
import sys
import urllib2
from threading import Thread
from BeautifulSoup import BeautifulSoup	 
import xml.sax
import pprint 
import urllib
import appdailysales
import wx
import settings

from result_event  import ResultEvent

from app_info import AppInfoParser

		
class SalesDownloader(Thread):
	def __init__(self, notify_window, days_to_download):
		
		self.notify_window = notify_window
		self.days_to_download = days_to_download
		self.shutdown = False
		
		Thread.__init__(self)
		
	def requestShutdown(self):
		print "Requesting download thread shutdown"
		appdailysales.shutDownSalesDownload = True
		self.shutdown = True
		
	def run(self):
		
		if settings.DOWNLOAD_SALES:
			options = appdailysales.ReportOptions()
			options.appleId = settings.APPLE_ID
			options.password = settings.APPLE_PW
	  		options.outputDirectory = settings.SalesDir()
	  		options.unzipFile = True
	  		options.verbose = True
			options.daysToDownload = 7
			
			try:
			     filename, err = appdailysales.downloadFile(options, self.notify_window, self.days_to_download)
	  	  	except:
	  	  		filename = []
	  	  		wx.PostEvent(self.notify_window, ResultEvent("SalesDownloadError: Could not retrieve sales"))
	  	  		return
	  	  	
	  	  	if self.shutdown == True:
	  	  		print "Exiting download thread"
	  	  		return
	  	  	
	  	  	if err == True:
	  	  		return
	  	  	  
	  	  	self.filenames = filename
	  	  	  
	  		if len(filename) == 0:
	  			wx.PostEvent(self.notify_window, ResultEvent("SalesDownloadCompleteNoFiles"))
	  		else:
	  			wx.PostEvent(self.notify_window, ResultEvent("SalesDownloadComplete: Done: " + str(len(filename)) + " new reports!"))
	  	else:
	  		print "Sales download is disabled"
	  	 	wx.PostEvent(self.notify_window, ResultEvent("SalesDownloadCompleteNoFiles"))
	  
	
class UpdateDownloader(Thread):
   def __init__ (self, product_ids, notify_window):
	  self.product_ids = product_ids
	  self.notify_window = notify_window
	  self.reviews = {}
	  self.shutdown = False
	  
	  Thread.__init__(self)
	 
   def requestShutdown(self):
   	print "Review thread shutdown request"
   	self.shutdown = True
   	
   def run(self):
		print "Loading Data"
	
		for i, product_id in enumerate(self.product_ids):
			
			if self.shutdown == True:
	  	  		print "Exiting review download thread"
	  	  		return
	  	  	
			if settings.DOWNLOAD_REVIEWS == True:
				if self.shutdown == True:
	  	  		    print "Exiting review download thread"
	  	  		    return
	  	  	
				# print "Retrieving App Number" + i.__str__() + " with id=" + product_id.__str__()
				try:
					itunes7_useragent = "iTunes/4.2 (Macintosh; U; PPC Mac OS X 10.2"

					headers = {
                        "X-Apple-Tz" : "7200",
        	          	"Accept-Language" : "en-us, en;q=0.50",
        	          	"Connection" : "close",
        	          	"Host" : "ax.phobos.apple.com.edgesuite.net"
                   	    }
 
					request  = urllib2.Request('http://ax.phobos.apple.com.edgesuite.net/WebObjects/MZStore.woa/wa/viewContentsUserReviews?id=' + product_id.__str__() + '&pageNumber=0&sortOrdering=2&type=Purple+Software', None, headers)
					opener = urllib2.build_opener()
					opener.addheaders = [('User-agent', itunes7_useragent)]     
					
					fp = opener.open(request)

					html = fp.read()
				except:
					continue
				
				try:
					os.mkdir(settings.SalesDir("xml"))
				except:
					pass
				
				f = open(settings.SalesDir("xml/") + product_id.__str__() + ".xml", "w+")
				f.write(html)
				f.close()
			
			try:
				f = open(settings.SalesDir("xml/") + product_id.__str__() + ".xml", "r+")
			except:
				continue
			
			if self.shutdown == True:
	  	  		print "Exiting review download thread"
	  	  		return
	  	  	
			parser = xml.sax.make_parser()
			handler = AppInfoParser()
			parser.setContentHandler(handler)
			parser.parse(settings.SalesDir("xml/") + product_id.__str__() + ".xml")
			
			self.reviews[product_id] = handler.reviews
			
			image = urllib.URLopener()
			image.retrieve(handler.image_url, settings.DataDir("images/forapps/") + product_id.__str__() + ".jpg")
			
			try:
				wx.PostEvent(self.notify_window, ResultEvent("RefreshImageAndReviews:" + str(product_id)))
			except:
				pass
	
			
		from currency import ExchangeRate
		ExchangeRate.update_currencies()
        
		print "Image & Review Download Complete"
		
		wx.PostEvent(self.notify_window, ResultEvent("ReviewDownloadComplete"))
		
########NEW FILE########
__FILENAME__ = app_info
import xml.sax

# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 

class AppInfoParser(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.mapping = {}
        self.image_url = ""
        self.inReviewName = False
        self.inTextView = False
        self.textViewData = ""
        self.foundReview = False
        self.reviewHeaderRead = False
        self.current_review= {}
        self.reviews = []
        
    def startElement(self, name, attributes):
        self.buffer = ""
        
        if name == "TextView":
            self.inTextView = True
            self.textViewData = ""
            
        if name == "PictureView":
           alt = attributes.getValue("alt")
           if alt.find("artwork") > 0:
               self.image_url = attributes.getValue("url")

        if name == "GotoURL":
            url = attributes.getValue("url")
            if url.find("userProfileId") > 0:
                self.inReviewName = True
        
    def characters(self, data):
        if self.inReviewName == True:
            self.buffer += data
        
        if self.inTextView == True:
            self.textViewData = self.textViewData + data
            
    def endElement(self, name):

        if name == "TextView":
            if self.reviewHeaderRead == True:
                self.reviewHeaderRead = False
                
                review_body = self.textViewData
                review_body = review_body.encode("utf-8", 'ignore')
                

                # print review_body
                
                self.current_review["ReviewBody"] = review_body
                
                new_review = {}
                new_review["ReviewBody"] = review_body
                new_review["ReviewHeader"] = self.current_review["ReviewHeader"]
                self.reviews.append(new_review)
                
            if self.textViewData.find("by") > 0 and self.inReviewName == True:
                review_header = self.textViewData.strip(" \n\r\t")
                # review_header = review_header.replace("\nby", "by ")
                review_header = review_header.replace("\n", " ")
                # review_header = review_header.replace("\t", "")
                # review_header = review_header.replace("\r", "")
                review_header = review_header.replace("  ", "")
                # review_header = review_header.replace("  ", "")
                review_header = review_header.replace("-", " - ")
                review_header = review_header.replace("-  ", "- ")
                review_header = review_header.replace("  -", " -")
                review_header = review_header.encode("utf-8")
                
                self.current_review["ReviewHeader"] = review_header
                # print review_header
                
                self.reviewHeaderRead = True
            
            self.inReviewName = False
            self.foundReview = False
            self.inTextView = False
            self.textViewData = ""
             
             
		

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2009, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.1.0.1"
__copyright__ = "Copyright (c) 2004-2009 Leonard Richardson"
__license__ = "New-style BSD"

import codecs
import markupbase
import types
import re
from HTMLParser import HTMLParser, HTMLParseError
try:
    from htmlentitydefs import name2codepoint
except ImportError:
    name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

# First, the classes that represent markup elements.

def sob(unicode, encoding):
    """Returns either the given Unicode string or its encoding."""
    if encoding is None:
        return unicode
    else: 
        return unicode.encode(encoding)

class PageElement:
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.contents.index(self)
        if hasattr(replaceWith, 'parent') and replaceWith.parent == self.parent:
            # We're replacing this element with one of its siblings.
            index = self.parent.contents.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                self.parent.contents.remove(self)
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if (isinstance(newChild, basestring)
            or isinstance(newChild, unicode)) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent != None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent == self:
                index = self.find(newChild)
                if index and index < position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        else:
            # Build a SoupStrainer
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (unicode(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def encode(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.decode().encode(encoding)

    def decodeGivenEventualEncoding(self, eventualEncoding):
        return self

class CData(NavigableString):

    def decodeGivenEventualEncoding(self, eventualEncoding):
        return u'<![CDATA[' + self + u']]>'

class ProcessingInstruction(NavigableString):

    def decodeGivenEventualEncoding(self, eventualEncoding):
        output = self
        if u'%SOUP-ENCODING%' in output:
            output = self.substituteEncoding(output, eventualEncoding)
        return u'<?' + output + u'?>'

class Comment(NavigableString):
    def decodeGivenEventualEncoding(self, eventualEncoding):
        return u'<!--' + self + u'-->'

class Declaration(NavigableString):
    def decodeGivenEventualEncoding(self, eventualEncoding):
        return u'<!' + self + u'>'

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs == None:
            attrs = []
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        def convert(kval):
            "Converts HTML, XML and numeric entities in the attribute value."
            k, val = kval
            if val is None:
                return kval
            return (k, re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                              self._convertEntities, val))
        self.attrs = map(convert, self.attrs)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.decode(eventualEncoding=encoding)

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"

    def __unicode__(self):
        return self.decode()

    def __str__(self):
        return self.encode()

    def encode(self, encoding=DEFAULT_OUTPUT_ENCODING,
               prettyPrint=False, indentLevel=0):
        return self.decode(prettyPrint, indentLevel, encoding).encode(encoding)

    def decode(self, prettyPrint=False, indentLevel=0,
               eventualEncoding=DEFAULT_OUTPUT_ENCODING):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding."""

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isString(val):
                    if (self.containsSubstitutions
                        and eventualEncoding is not None
                        and '%SOUP-ENCODING%' in val):
                        val = self.substituteEncoding(val, eventualEncoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)
                if val is None:
                    # Handle boolean attributes.
                    decoded = key
                else:
                    decoded = fmt % (key, val)
                attrs.append(decoded)
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % self.name

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.decodeContents(prettyPrint, indentContents,
                                       eventualEncoding)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (self.name, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        contents = [i for i in self.contents]
        for i in contents:
            if isinstance(i, Tag):
                i.decompose()
            else:
                i.extract()
        self.extract()

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.encode(encoding, True)

    def encodeContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        return self.decodeContents(prettyPrint, indentLevel).encode(encoding)

    def decodeContents(self, prettyPrint=False, indentLevel=0,
                       eventualEncoding=DEFAULT_OUTPUT_ENCODING):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.decodeGivenEventualEncoding(eventualEncoding)
            elif isinstance(c, Tag):
                s.append(c.decode(prettyPrint, indentLevel, eventualEncoding))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods. Will go away in 4.0.
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    # 3.x compatibility methods. Will go away in 4.0.
    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        if encoding is None:
            return self.decodeContents(prettyPrint, indentLevel, encoding)
        else:
            return self.encodeContents(encoding, prettyPrint, indentLevel)


    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next

    def childGenerator(self):
        if not len(self.contents):
            raise StopIteration
        current = self.contents[0]
        while current:
            yield current
            current = current.nextSibling
        raise StopIteration

# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isString(attrs):
            kwargs['class'] = attrs
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if isList(markup) and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isString(markup):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst == True and type(matchAgainst) == types.BooleanType:
            result = markup != None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup is not None and not isString(markup):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif (isList(matchAgainst)
                  and (markup is not None or not isString(matchAgainst))):
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isString(markup):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def isList(l):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is listlike."""
    return ((hasattr(l, '__iter__') and not isString(l))
            or (type(l) in (types.ListType, types.TupleType)))

def isString(s):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is stringlike."""
    try:
        return isinstance(s, unicode) or isinstance(s, basestring)
    except NameError:
        return isinstance(s, str)

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif isList(portion) and not isString(portion):
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class HTMLParserBuilder(HTMLParser):

    def __init__(self, soup):
        HTMLParser.__init__(self)
        self.soup = soup

    # We inherit feed() and reset().

    def handle_starttag(self, name, attrs):
        if name == 'meta':
            self.soup.extractCharsetFromMeta(attrs)
        else:
            self.soup.unknown_starttag(name, attrs)

    def handle_endtag(self, name):
        self.soup.unknown_endtag(name)

    def handle_data(self, content):
        self.soup.handle_data(content)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.soup.endData()
        self.handle_data(text)
        self.soup.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.soup.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.soup.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.soup.convertXMLEntities:
                data = self.soup.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.soup.convertHTMLEntities and \
            not self.soup.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = HTMLParser.parse_declaration(self, i)
            except HTMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j


class BeautifulStoneSoup(Tag):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False,
                 builder=HTMLParserBuilder):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        HTMLParser will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        HTMLParser, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke HTMLParser:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        self.builder = builder(self)
        self.reset()

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed.
        self.builder = None                # So can the builder.

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not isList(self.markupMassage):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.builder.reset()

        self.builder.feed(markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        self.builder.reset()
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()
        # Tags with just one string-owning child get the child as a
        # 'string' property, so that soup.tag.string is shorthand for
        # soup.tag.contents[0]
        if len(self.currentTag.contents) == 1 and \
           isinstance(self.currentTag.contents[0], NavigableString):
            self.currentTag.string = self.currentTag.contents[0]

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers != None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers == None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join(map(lambda(x, y): ' %s="%s"' % (x, y), attrs))
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def extractCharsetFromMeta(self, attrs):
        self.unknown_starttag('meta', attrs)


class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ['br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base'])

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ['span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center']

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ['blockquote', 'div', 'fieldset', 'ins', 'del']

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ['address', 'form', 'p', 'pre']

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def extractCharsetFromMeta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True


class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ['em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big']

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ['noscript']

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, match):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        orig = match.group(1)
        sub = self.MS_CHARS.get(orig)
        if type(sub) == types.TupleType:
            if self.smartQuotesTo == 'xml':
                sub = '&#x'.encode() + sub[1].encode() + ';'.encode()
            else:
                sub = '&'.encode() + sub[0].encode() + ';'.encode()
        else:
            sub = sub.encode()
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            smart_quotes_re = "([\x80-\x9f])"
            smart_quotes_compiled = re.compile(smart_quotes_re)
            markup = smart_quotes_compiled.sub(self._subMSChar, markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_re = '^<\?.*encoding=[\'"](.*?)[\'"].*\?>'.encode()
        xml_encoding_match = re.compile(xml_encoding_re).match(xml_data)
        if not xml_encoding_match and isHTML:
            meta_re = '<\s*meta[^>]+charset=([^>]*?)[;\'">]'.encode()
            regexp = re.compile(meta_re, re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].decode(
                'ascii').lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = currency
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.


import csv, sys
import datetime
import pickle
import settings

from dateutil.parser import *
 

class ExchangeRate(object):
	
	currencies = None
	currencies_to_update = []
	shutDown = False
	preLoad = False
	
	def __init__(self, currency, f, updated):
		self.last_updated = updated
		self.currency = currency
		self.fraction_of_1_usd = f

	@classmethod
	def requestShutdown(cls):
		ExchangeRate.shutDown = True
		
	@classmethod
	def save_currencies(cls):
		try:
			if not ExchangeRate.currencies is None:
				file = open(settings.DataDir("currencies.key"), "wb") # write mode
				file.write(pickle.dumps(ExchangeRate.currencies, 2))
				file.close()
		except:
			settings.log("Could not save currency data. Will try again on restart")
			
	@classmethod
	def update_currencies(cls):
		
		if ExchangeRate.currencies == None:
			ExchangeRate.currencies = {}
			
		for currency in ExchangeRate.currencies_to_update:
			if ExchangeRate.shutDown == True:
				break
			
			settings.log("Updating: " + currency)
			
			e = None
			if ExchangeRate.currencies.has_key(currency):
				e = ExchangeRate.currencies[currency]
			else:
				e = ExchangeRate(currency, 1.0, datetime.date.today() - datetime.timedelta(days=7))
				
			if e.last_updated.day != datetime.date.today().day:
				try:
					e = ExchangeRate(currency, download_exchange_rate(currency), datetime.date.today())
					ExchangeRate.currencies[currency] = e
				except:
					settings.log("Could not download todays currency")
					e = ExchangeRate.currencies[currency]


	@classmethod
	def get(self, currency):
		
		if not currency in ExchangeRate.currencies_to_update:
			ExchangeRate.currencies_to_update.append(currency)
		
		if ExchangeRate.preLoad == True:
			return
		
		file= None
		
		if ExchangeRate.currencies == None:
			ExchangeRate.currencies = {}
			try:
				file_name = settings.DataDir("currencies.key")
				file = open(file_name, "rb") # read mode
				info = file.read()
				
				try:
					ExchangeRate.currencies = pickle.loads(info)
				except:
					settings.log("Could not unpickle currencies file: " + file_name)
					file.close()
					os.remove(file_name)
					ExchangeRate.currencies = {}
			except:
				settings.log("Could not open currencies file:" + file_name)
				ExchangeRate.currencies = {}
		
		if not file == None:
			file.close()
		
		if ExchangeRate.currencies == None:
			ExchangeRate.currencies = {}
			
		amt_f = 0
		e = None
		if ExchangeRate.currencies.has_key(currency):
			e = ExchangeRate.currencies[currency]
		else:
			settings.log("Currency not found, sales report will be inaccurate!")
			settings.display_error("Currency rate for " + currency + " not found, sales report will be inaccurate. Please refresh and restart!")
			e = ExchangeRate(currency, 1.0, datetime.date.today() - datetime.timedelta(days=7))
			ExchangeRate.currencies[currency] = e
				
		return e
		
def convert_currency_to_usd(amount, amount_currency):
	# Will convert from this currency to USD. If the conversion
	# Value does not exist, it will update it from yahoo currencies
	
	if amount_currency == "USD":
		return amount
	
	exchange_rate = ExchangeRate.get(currency=amount_currency)
	if exchange_rate is None:
		return 0
			
	final_sum = exchange_rate.fraction_of_1_usd * amount 
	return final_sum  

def download_exchange_rate(currency):
	settings.log("Downloading currency: " + currency)
	url = "http://download.finance.yahoo.com/d/quotes.csv?s=" + currency + "USD=X&f=l1"
	import urllib2
	req = urllib2.Request(url=url)
	response = urllib2.urlopen(req)
	data = response.read()
	return float(data)

def download_all_currencies():
	ExchangeRate.preLoad = True
	
	ExchangeRate.get("USD")
	ExchangeRate.get("EUR")
	ExchangeRate.get("AED")
	ExchangeRate.get("AFN")
	ExchangeRate.get("ALL")
	ExchangeRate.get("AMD")
	ExchangeRate.get("ANG")
	ExchangeRate.get("AOA")
	ExchangeRate.get("ARS")
	ExchangeRate.get("AUD")
	ExchangeRate.get("AWG")
	ExchangeRate.get("AZN")
	ExchangeRate.get("BAM")
	ExchangeRate.get("BBD")
	ExchangeRate.get("BDT")
	ExchangeRate.get("BGN")
	ExchangeRate.get("BHD")
	ExchangeRate.get("BIF")
	ExchangeRate.get("BMD")
	ExchangeRate.get("BND")
	ExchangeRate.get("BOB")
	ExchangeRate.get("BOV")
	ExchangeRate.get("BRL")
	ExchangeRate.get("BSD")
	ExchangeRate.get("BTN")
	ExchangeRate.get("BWP")
	ExchangeRate.get("BYR")
	ExchangeRate.get("BZD")
	ExchangeRate.get("CAD")
	ExchangeRate.get("CDF")
	ExchangeRate.get("CHE")
	ExchangeRate.get("CHF")
	ExchangeRate.get("CHW")
	ExchangeRate.get("CLF")
	ExchangeRate.get("CLP")
	ExchangeRate.get("CNY")
	ExchangeRate.get("COP")
	ExchangeRate.get("COU")
	ExchangeRate.get("CRC")
	ExchangeRate.get("CUC")
	ExchangeRate.get("CUP")
	ExchangeRate.get("CVE")
	ExchangeRate.get("CZK")
	ExchangeRate.get("DJF")
	ExchangeRate.get("DKK")
	ExchangeRate.get("DOP")
	ExchangeRate.get("DZD")
	ExchangeRate.get("EEK")
	ExchangeRate.get("EGP")
	ExchangeRate.get("ERN")
	ExchangeRate.get("ETB")
	ExchangeRate.get("EUR")
	ExchangeRate.get("FJD")
	ExchangeRate.get("FKP")
	ExchangeRate.get("GBP")
	ExchangeRate.get("GEL")
	ExchangeRate.get("GHS")
	ExchangeRate.get("GIP")
	ExchangeRate.get("GMD")
	ExchangeRate.get("GNF")
	ExchangeRate.get("GTQ")
	ExchangeRate.get("GYD")
	ExchangeRate.get("HKD")
	ExchangeRate.get("HNL")
	ExchangeRate.get("HRK")
	ExchangeRate.get("HTG")
	ExchangeRate.get("HUF")
	ExchangeRate.get("IDR")
	ExchangeRate.get("ILS")
	ExchangeRate.get("INR")
	ExchangeRate.get("IQD")
	ExchangeRate.get("IRR")
	ExchangeRate.get("ISK")
	ExchangeRate.get("JMD")
	ExchangeRate.get("JOD")
	ExchangeRate.get("JPY")
	ExchangeRate.get("KES")
	ExchangeRate.get("KGS")
	ExchangeRate.get("KHR")
	ExchangeRate.get("KMF")
	ExchangeRate.get("KPW")
	ExchangeRate.get("KRW")
	ExchangeRate.get("KWD")
	ExchangeRate.get("KYD")
	ExchangeRate.get("KZT")
	ExchangeRate.get("LAK")
	ExchangeRate.get("LBP")
	ExchangeRate.get("LKR")
	ExchangeRate.get("LRD")
	ExchangeRate.get("LSL")
	ExchangeRate.get("LTL")
	ExchangeRate.get("LVL")
	ExchangeRate.get("LYD")
	ExchangeRate.get("MAD")
	ExchangeRate.get("MDL")
	ExchangeRate.get("MGA")
	ExchangeRate.get("MKD")
	ExchangeRate.get("MMK")
	ExchangeRate.get("MNT")
	ExchangeRate.get("MOP")
	ExchangeRate.get("MRO")
	ExchangeRate.get("MUR")
	ExchangeRate.get("MVR")
	ExchangeRate.get("MWK")
	ExchangeRate.get("MXN")
	ExchangeRate.get("MXV")
	ExchangeRate.get("MYR")
	ExchangeRate.get("MZN")
	ExchangeRate.get("NAD")
	ExchangeRate.get("NGN")
	ExchangeRate.get("NIO")
	ExchangeRate.get("NOK")
	ExchangeRate.get("NPR")
	ExchangeRate.get("NZD")
	ExchangeRate.get("OMR")
	ExchangeRate.get("PAB")
	ExchangeRate.get("PEN")
	ExchangeRate.get("PGK")
	ExchangeRate.get("PHP")
	ExchangeRate.get("PKR")
	ExchangeRate.get("PLN")
	ExchangeRate.get("PYG")
	ExchangeRate.get("QAR")
	ExchangeRate.get("RON")
	ExchangeRate.get("RSD")
	ExchangeRate.get("RUB")
	ExchangeRate.get("RWF")
	ExchangeRate.get("SAR")
	ExchangeRate.get("SBD")
	ExchangeRate.get("SCR")
	ExchangeRate.get("SDG")
	ExchangeRate.get("SEK")
	ExchangeRate.get("SGD")
	ExchangeRate.get("SHP")
	ExchangeRate.get("SLL")
	ExchangeRate.get("SOS")
	ExchangeRate.get("SRD")
	ExchangeRate.get("STD")
	ExchangeRate.get("SYP")
	ExchangeRate.get("SZL")
	ExchangeRate.get("THB")
	ExchangeRate.get("TJS")
	ExchangeRate.get("TMT")
	ExchangeRate.get("TND")
	ExchangeRate.get("TOP")
	ExchangeRate.get("TRY")
	ExchangeRate.get("TTD")
	ExchangeRate.get("TWD")
	ExchangeRate.get("TZS")
	ExchangeRate.get("UAH")
	ExchangeRate.get("UGX")
	ExchangeRate.get("USD")
	ExchangeRate.get("USN")
	ExchangeRate.get("USS")
	ExchangeRate.get("UYU")
	ExchangeRate.get("UZS")
	ExchangeRate.get("VEF")
	ExchangeRate.get("VND")
	ExchangeRate.get("VUV")
	ExchangeRate.get("WST")
	ExchangeRate.get("XAF")
	ExchangeRate.get("XAG")
	ExchangeRate.get("XAU")
	ExchangeRate.get("XBA")
	ExchangeRate.get("XBB")
	ExchangeRate.get("XBC")
	ExchangeRate.get("XBD")
	ExchangeRate.get("XCD")
	ExchangeRate.get("XDR")
	ExchangeRate.get("XFU")
	ExchangeRate.get("XOF")
	ExchangeRate.get("XPD")
	ExchangeRate.get("XPF")
	ExchangeRate.get("XPT")
	ExchangeRate.get("XTS")
	ExchangeRate.get("XXX")
	ExchangeRate.get("YER")
	ExchangeRate.get("ZAR")
	ExchangeRate.get("ZMK")
	ExchangeRate.get("ZWL")
	
	ExchangeRate.update_currencies()
	ExchangeRate.save_currencies()
########NEW FILE########
__FILENAME__ = event_dialog
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 

class AddEventDialog(wx.Dialog):
    def __init__(self, parent):
        super(AddEventDialog, self).__init__(parent, title="Add new event")

        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.FlexGridSizer(2, 2)

        box.Add(
            wx.StaticText(self, -1, "Date:"), 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.date = wx.DatePickerCtrl(
            self, size=(120, -1), style=wx.DP_DEFAULT, name="Event date")
        box.Add(self.date, 1, wx.ALIGN_LEFT|wx.ALL, 5)

        box.Add(
            wx.StaticText(self, -1, "Text:"), 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.text = wx.TextCtrl(self, size=(120, -1))
        box.Add(self.text, 1, wx.ALIGN_LEFT|wx.ALL, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.AddMany((
            (box, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5),
            (btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)))
        
        self.SetSizerAndFit(sizer)
        

########NEW FILE########
__FILENAME__ = mainframe
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

 
import random, sys, locale
import matplotlib.dates as mdates
import wx.lib.masked as masked
import wx.lib.mixins.listctrl    as    listmix

from currency import convert_currency_to_usd
from app_info import AppInfoParser
from popularity_list import PopularityList

from result_event import EVT_RESULT

import datetime, matplotlib, operator, time
import wx, wxmpl
from apps_update import SalesDownloader
from datetime import timedelta
from products_list import ProductsList
from plot_panel import PlotPanel
from sales_list import SalesListCtrl
from reviews_list import ReviewsList
from sales_period import SalesPeriod
from settings_dialog import SettingsDialog
from apps_update import UpdateDownloader

import settings
import wx.animate
import os
import webbrowser
import glob

class MainFrame(wx.Frame):
    
    def ConfigureMenus(self):
        menu = wx.Menu()
        
        ID_IMPORT = wx.NewId()
        menu.Append(ID_IMPORT, "&Import sales files...", "Open")
        menu.AppendSeparator()
        
        ID_PRINT = wx.NewId()
        menu.Append(ID_PRINT, "&Print Graph...", "Print")
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")
        menu.Enable(ID_PRINT, False)
        # menu.Enable(ID_OPEN, False)
        
        menuBar = wx.MenuBar()
        menuBar.Append(menu, "&File")
       
        menu = wx.Menu()
        ID_UPDATE = wx.NewId()
        ID_AMOUNT = wx.NewId()
        ID_PROFIT = wx.NewId()
        ID_SETTINGS = wx.NewId()
       
        menu.Append(ID_PROFIT, "&Revenue", "Show revenue on graphs", wx.ITEM_RADIO) 
        menu.Append(ID_AMOUNT, "Downloads", "Show downloads on graphs", wx.ITEM_RADIO)
    
        menu.AppendSeparator()
        menu.Append(ID_UPDATE, "&Refresh Sales", "Update From Server")
        menu.AppendSeparator()
        menu.Append(ID_SETTINGS, "&Options...", "Options...")
        menuBar.Append(menu, "&View")
        
        menu = wx.Menu()
        
        ID_HELP = wx.NewId()
        menu.Append(ID_HELP, "&Help Contents", "&Help Contents")
        menu.AppendSeparator()
        
        ID_ABOUT = wx.NewId()
        menu.Append(ID_ABOUT, "&About Salesgraph", "&About Salesgraph")
        menuBar.Append(menu, "&Help")
         
        self.SetMenuBar(menuBar)
        
        
        self.Bind(wx.EVT_MENU, self.OnImport, id=ID_IMPORT)
        self.Bind(wx.EVT_MENU, self.OnSettings, id=ID_SETTINGS)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_MENU, self.OnRefreshSales, id=ID_UPDATE)
        self.Bind(wx.EVT_MENU, self.OnAdd, id=wx.ID_ADD)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAmount, id=ID_AMOUNT)
        self.Bind(wx.EVT_MENU, self.OnProfit, id=ID_PROFIT)
        self.Bind(wx.EVT_MENU, self.ShowAboutBox, id=ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.ShowHelp, id=ID_HELP)

    
    
    def ConfigureToolbars(self):
        # img = wx.Image('./images/314246133.jpg') 
        # img.Rescale(48, 48)
        # toolbar = self.CreateToolBar(wx.TB_TEXT | wx.NO_BORDER | wx.TB_HORIZONTAL)
        # toolbar.SetToolBitmapSize((48,48))
        # toolbar.AddLabelTool(1000, "Download Sales", wx.Image('./images/diagram_32.png').ConvertToBitmap())
       # toolbar.AddLabelTool(1001, "Download Reviews", wx.Image('./images/bubble_32.png').ConvertToBitmap())
       # toolbar.AddSeparator()
       # toolbar.AddLabelTool(1001, "Add Event", wx.Image('./images/flag_32.png').ConvertToBitmap())
        toolbar.Realize()
        
        self.Bind(wx.EVT_MENU, self.OnDownloadSalesReports, id=1000)
        self.Bind(wx.EVT_MENU, self.OnServerUpdate, id=1001)
        
        self.status = self.CreateStatusBar()
    
    def ConfigureSizers(self):
        self.uber_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.graphics_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook_frame = wx.BoxSizer(wx.VERTICAL)
        
        self.notebook_frame.SetMinSize((640, 480))
        
        
    def ConfigureListCtrls(self):
        self.products_id = wx.NewId()
        self.products = ProductsList(self, self.products_id)
        self.review_list = ReviewsList(self.notebook)
        self.popularity_list = PopularityList(self.notebook)

            
    def ConfigureOtherPanels(self):
        self.notebook = wx.Notebook(self, style=wx.BK_TOP)
        self.notebook_frame.Add(self.notebook, 1, wx.EXPAND|wx.ALL, 15)
        self.notebook_frame.Fit(self)
       
        self.load_label = wx.StaticText(self, label="Loading files...")
        self.load_label.SetBackgroundColour(settings.PRODUCTS_BG_COLOR)
        self.load_label.Raise()
        self.throbber = wx.animate.GIFAnimationCtrl(self, 1, "images/25-0.gif", pos=(10, 10))
        self.throbber.Play()
    
    def ConfigureBottomBar(self):
        
        # Create a bar at the bottom
        self.bottom_box = wx.BoxSizer(wx.HORIZONTAL)
        
        self.refresh_img = wx.Image("images/refresh_button3.png")
        self.refresh_img_hover = wx.Image("images/refresh_button3_hover.png")
        self.refresh_img_press = wx.Image("images/refresh_button3_pressed.png")
        # self.refresh_btn = wx.BitmapButton(self, -1, img.ConvertToBitmap(), style=wx.BU_EXACTFIT, size=(90, 30))
        self.refresh_btn = wx.StaticBitmap(self, -1, self.refresh_img.ConvertToBitmap(), size=(90, 30))
        self.refresh_btn.Bind(wx.EVT_LEFT_DOWN, self.OnRefreshSales)
       
        self.refresh_btn.Raise()
        
        # Split in two
        bottom_box_left = wx.BoxSizer(wx.VERTICAL)
        bottom_box_left_inside = wx.BoxSizer(wx.HORIZONTAL)
        bottom_box_left.Add(bottom_box_left_inside, 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
    
        bottom_box_right = wx.BoxSizer(wx.VERTICAL)
        bottom_box_right_inside = wx.BoxSizer(wx.HORIZONTAL)
        bottom_box_right.Add(bottom_box_right_inside, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        # Add both halves in correct proportion
        self.bottom_box.AddMany(((bottom_box_left, 1, wx.EXPAND), (bottom_box_right, 3, wx.EXPAND)))
        
        # Create date thing
        self.date_range = wx.Slider(self, settings.MAX_RANGE, 7, 1, 
                                    settings.MAX_RANGE, (-1, -1), (250, -1), 
                                    wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.date_range.SetTickFreq(15)
        
        self.date_entry = masked.NumCtrl(self, value=7, integerWidth=3, allowNegative=False)
        
        bottom_box_right_inside.Add(self.date_range, 0, wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL, 15)
        bottom_box_right_inside.Add(self.date_entry, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL, 10)
        bottom_box_right_inside.Add(wx.StaticText(self, label="  Days"), 0, wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.Bind(wx.EVT_SLIDER, self.OnSliderChange)
        self.Bind(masked.EVT_NUM, self.OnDateEntryChange)
        # self.Bind(wx.EVT_BUTTON, self.OnRefreshSales)
        


        # self.refresh_btn = wx.Button(self, -1, "Refresh", )
        # self.refresh_btn.SetMargins(0, 0)
        bottom_box_left_inside.Add(self.refresh_btn, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, 0)
        # self.refresh_btn.SetBitmapHover(img_hover.ConvertToBitmap())
        # self.refresh_btn.SetBitmapSelected(img_press.ConvertToBitmap())
        
        self.refresh_btn.SetMinSize((88, 30))
        
        pos = self.refresh_btn.GetRect()
        self.throbber_sales = wx.animate.GIFAnimationCtrl(self, 1, "images/24-0.gif", pos=(pos.x, pos.y))
        self.throbber_sales.Hide()
        
        self.label_throbber_sales = wx.StaticText(self, label="Refreshing...")
        self.label_throbber_sales.SetFont(wx.Font(settings.BOTTOM_STATUS_TEXT_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False, u'Verdana'))
        self.label_throbber_sales.Hide()
        
    def ConfigureDatePicker(self):
        
        static_box = wx.StaticBox(self, -1, "Select range")
        self.static_box = wx.StaticBoxSizer(static_box, wx.HORIZONTAL)
        
        now = wx.DateTime().Today()
        self.date_start = wx.DatePickerCtrl(self, size=(120, -1), style=wx.DP_DEFAULT, name="Date range start")
        self.date_start.SetValue(now - wx.DateSpan(days=7))
        self.date_end = wx.DatePickerCtrl(self, size=(120, -1), style=wx.DP_DEFAULT, name="Date range end")
        self.date_end.SetValue(now)

        label_from = wx.BoxSizer(wx.VERTICAL)
        label_from_s = wx.StaticText(self, label="From:")
        label_from.Add(label_from_s, 1, wx.EXPAND|wx.ALL, 3)
        label_from.Fit(self)
        
        label_to = wx.BoxSizer(wx.VERTICAL)
        label_to_s = wx.StaticText(self, label="To:")
        label_to.Add(label_to_s, 1, wx.EXPAND|wx.ALL, 2)
        label_to.Fit(self)
        
        date_range_sizer = wx.GridSizer(2, 2)
        
        date_range_sizer.AddMany((
            (label_from, 1, wx.ALIGN_RIGHT),
            (self.date_start, 2),
            (label_to, 1, wx.ALIGN_RIGHT),
            (self.date_end, 2)))
        
        # self.static_box.AddMany((
        #        (date_range_sizer, 2, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)))
        
        self.Bind(wx.EVT_DATE_CHANGED, self.OnDateChange)
        self.Bind(wx.EVT_DATE_CHANGED, self.OnDateChange)
        
        self.date_end.Hide()
        self.date_start.Hide()
        label_from_s.Hide()
        label_to_s.Hide()
        static_box.Hide()
        
    def ConfigureTopPanel(self):
        # Panel with revenue and all that
        
         # Add the application image
        img_all = wx.Image('images/all_apps_big.png')
        self.app_image = wx.StaticBitmap(self,  bitmap=img_all.ConvertToBitmap())
        
        self.top_bar_area = wx.BoxSizer(wx.HORIZONTAL)
        
        self.app_text_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.product_name_label = wx.StaticText(self, label="All Products")
        self.product_name_label.SetFont(wx.Font(settings.TOP_FONT_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False, u'Helvetica'))
        self.product_name_label.SetForegroundColour((65, 81, 87))
        
        self.revenue_label = wx.StaticText(self, label="Last Sales Report: $0")
        self.revenue_label.SetFont(wx.Font(settings.TOP_FONT_MEDIUM_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False, u'Arial'))
        self.revenue_label.SetForegroundColour((65, 81, 87))
        
        self.last_income_label = wx.StaticText(self, label="Daily Average (7 Days): $0.0")
        self.last_income_label.SetFont(wx.Font(settings.TOP_FONT_SMALL_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, u'Arial'))
        self.last_income_label.SetForegroundColour((153, 153, 153))
        
        self.selected_range_label = wx.StaticText(self, label="7 day sales: $0.0")
        self.selected_range_label.SetFont(wx.Font(settings.TOP_FONT_SMALL_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, u'Arial'))
        self.selected_range_label.SetForegroundColour((153, 153, 153))
    
        self.top_bar_area.Add(self.app_image, 0, wx.ALL|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        
        self.app_text_sizer.Add(self.product_name_label, 0, wx.TOP|wx.ALIGN_LEFT|wx.ALIGN_TOP, 10)
        self.app_text_sizer.Add(self.revenue_label, 0, wx.TOP|wx.ALIGN_LEFT, 10)
        self.app_text_sizer.Add(self.selected_range_label, 0, wx.TOP|wx.ALIGN_LEFT, 10)
        self.app_text_sizer.Add(self.last_income_label, 0, wx.TOP|wx.ALIGN_LEFT, 0)
        
        self.top_bar_area.Add(self.app_text_sizer, 0, wx.ALL|wx.ALIGN_LEFT, 5)
        self.top_bar_area.Add(self.static_box, 1, wx.ALL|wx.ALIGN_RIGHT, 15)
        self.top_bar_area.Fit(self)
  
        label_amt = wx.BoxSizer(wx.VERTICAL)
        
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnProductSelected, id=self.products_id)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnProductSelected,id=self.products_id)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.UpdateLowerWidget)

    def ConfigureBottomPanel(self):
        self.sales_panel = PlotPanel(self.notebook)
        sales_list_ctrl = SalesListCtrl(self.notebook)
    
        self.Update()
        self.notebook.AddPage(self.sales_panel, "Sales Graphs")
        self.notebook.AddPage(self.review_list, "Reviews")
        self.notebook.AddPage(sales_list_ctrl, "Sales Details")
        
        # self.review_list.Hide()
    
    def OnCloseWindow(self, event):
        settings.log("SalesGraph starting exit")
        
        from currency import ExchangeRate
        ExchangeRate.save_currencies()
        ExchangeRate.requestShutdown()
        
        settings.save_settings()
        self.sales_period.requestShutdown()
        
        if not self.sales_downloader == None:
            self.sales_downloader.requestShutdown()
        
        if not self.updater == None:
            self.updater.requestShutdown()
            
        self.Destroy()
        
    def __init__(self):
        super(MainFrame, self).__init__(None, -1, "AppSalesGraph")
                        
        self.version = 1.0
        self.sales_downloader = None
        self.updater = None
        
        icon = wx.Icon("images/key.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        settings.load_settings()
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        # Set structures
        EVT_RESULT(self, self.OnResult)
        self.loaded_dates = []
        self.selected_products = []
        self.event_levels = []
        self.delayed = False
        
        # Build up GUI
        self.ConfigureMenus()
        # self.ConfigureToolbars()
        self.ConfigureSizers()
        self.ConfigureBottomBar()
        self.ConfigureDatePicker()
        self.ConfigureOtherPanels()
        self.ConfigureListCtrls()
        self.ConfigureTopPanel()
        self.ConfigureBottomPanel()
        
        
        self.graphics_sizer.AddMany(((self.top_bar_area, 0, wx.ALIGN_LEFT|wx.EXPAND|wx.LEFT, 5), (self.notebook_frame, 4, wx.EXPAND, 5)))
        self.main_sizer.AddMany(((self.products, 1, wx.EXPAND|wx.ALL, 0), (self.graphics_sizer, 3, wx.EXPAND)))
        
        # label_to.Add(wx.StaticText(self, label="To:"), 1, wx.EXPAND|wx.ALL, 2)
        self.uber_sizer.Add(self.main_sizer, 5, wx.EXPAND|wx.ALL, 0)
        
        # wx.ALL is for sides that border applies to
        self.uber_sizer.Add(item=self.bottom_box, proportion=0, 
                            flag=wx.EXPAND|wx.ALL|wx.FIXED_MINSIZE|wx.ALIGN_BOTTOM,
                            border=0)
        
        
        # self.graph_renderer = operator.attrgetter('paid_downloads')
        
        self.SetSizerAndFit(self.uber_sizer)
        self.CentreOnScreen() 
        
        try:
            self.products.Select(0)
            self.OnProductSelected(None)
        except:
            pass
        
        self.Update()
        
        self.sales_period = SalesPeriod(self)
        self.notebook.sales_period = self.sales_period
        self.popularity_list.SetData(self.sales_period)
        
        if not self.sales_panel == None:
            self.sales_panel.sales_period = self.sales_period

        self.LoadSalesFiles()
        # wx.CallLater(500, self.CheckForUpdateFile, None)
        self.OnProfit(None)
    
    def LoadSalesFiles(self):
        self.load_label.SetLabel("Loading sales files...")
        self.load_label.Raise()
        self.load_label.Show()
        self.throbber.Show()
        self.throbber.Raise()
        
        self.SetStatusText("Loading sales files...")
        self.products.DeleteAllItems()
        self.sales_period = SalesPeriod(self)
        self.sales_period.start()
        self.Refresh()
    
    def OnImport(self, event):
        import glob, shutil
        dialog = wx.DirDialog(self, message = "Select the folder", style = 0)
        
        if dialog.ShowModal() == wx.ID_OK:
            dir = dialog.GetPath() + "/*.txt"
            for file in glob.glob(dir):
                shutil.copyfile(file, settings.SalesDir("/" + os.path.basename(file)))
            
            dlg = wx.MessageDialog(self, "All text files have been imported. Please restart the client to see new graphs", "Success!", wx.OK)
            dlg.ShowModal()
            
        print "Import"
        
    def OnSalesFileLoadComplete(self):
        self.products.LoadImages(self.sales_period.product_ids, self.sales_period.product_names)
        self.load_label.Hide()
        self.throbber.Hide()
        self.SetStatusText("")
        
        try:
            self.products.Select(0)
            self.OnProductSelected(None)
        except:
            pass
        
        self.popularity_list.SetData(self.sales_period)
        
        # Debug
        # self.OnReviewAndIconUpdate(None)
    
    def UpdateRefreshStatus(self, str):
        
        if (str.find("SalesFileLoaded") >= 0):
            t = str[len("SalesFileLoaded")+1:]
            self.load_label.SetLabel(t)
            
        if (str == "SalesDownloadCompleteNoFiles"):
            self.label_throbber_sales.Show()
            self.throbber_sales.Hide()
            self.label_throbber_sales.SetLabel("No new sales report available")
            self.refresh_btn.Show()
            self.OnSize(None)
            self.Refresh()
            self.OnReviewAndIconUpdate(None)
            return
        
        if (str.find("RefreshImageAndReviews") >= 0):
            app_id = str[len("RefreshImageAndReviews")+1:]
            app_id = int(app_id)
            self.products.LoadImage(app_id, self.sales_period.product_names[app_id])
            return
        
        if (str.find("SalesDownloadComplete") >= 0):
            
            self.label_throbber_sales.SetLabel("Reading sales file...")

            
            # Download complete, update sales
            self.refresh_btn.Show()
            self.throbber_sales.Hide()
            self.label_throbber_sales.Show()
            self.OnSize(None)
            
            files = self.sales_downloader.filenames
            for file in files:
                self.sales_period.addSalesFile(file)
            
            self.sales_period.refreshSalesData()
            
            self.label_throbber_sales.SetFont(wx.Font(settings.BOTTOM_STATUS_TEXT_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False, u'Verdana'))
            
            t = str[len("SalesDownloadComplete")+1:]
            self.label_throbber_sales.SetLabel(t)
            
            if self.products.GetItemCount() <= 1:
                self.products.LoadImages(self.sales_period.product_ids, self.sales_period.product_names)
                
            sound = wx.Sound("glass.wav")
            sound.Play()
            
            self.OnSize(None)
            self.Refresh()
            self.OnReviewAndIconUpdate(None)
            # self.RefreshSales()
            return
        
        if (str.find("SalesDownloadError") >= 0):
            t = str[len("SalesDownloadError")+1:]
            self.label_throbber_sales.SetLabel(t)
            
            self.refresh_btn.Show()
            self.throbber_sales.Hide()
            self.label_throbber_sales.Show()
            self.OnSize(None)
            self.Refresh()
            self.OnReviewAndIconUpdate(None)
            return
            
        self.label_throbber_sales.SetLabel(str)
    
    def ShowAboutBox(self, evt):
         info = wx.AboutDialogInfo()
         info.SetName(settings.APP_NAME)
         info.SetVersion(settings.APP_VERSION)
         info.SetDescription("Analyse your software sales!")
         info.SetCopyright("(C) 2010 Max Klein : maximusklein@gmail.com")
         wx.AboutBox(info);


    def ShowHelp(self, evt):
         # webbrowser.open("web url help")
		 pass

    def OnRefreshSales(self, item):
        
        self.refresh_btn.SetBitmap(self.refresh_img_press.ConvertToBitmap())
        
        if settings.APPLE_ID == "" or settings.APPLE_PW == "":
            msg = "Your %s is not set. Would you like to set it now?" % ("username" if settings.APPLE_ID == "" else "password")
            dlg = wx.MessageDialog(self, msg, "A little problem", wx.YES_NO | wx.ICON_QUESTION)
            result = dlg.ShowModal() == wx.ID_YES
            dlg.Destroy()
            
            if result == True:
                dlg2 = SettingsDialog(self, -1, "Settings", size=(320, 230),style=wx.DEFAULT_DIALOG_STYLE)
                dlg2.CenterOnScreen()
                # dlg2.SetModal(True)
                val = dlg2.ShowModal()
                
                if settings.APPLE_ID == "":
                    dlg = wx.MessageDialog(self, "Your username is still not set. But fine, let's go ahead..", "Did you do it?", wx.OK | wx.ICON_WARNING)
                    dlg.ShowModal()
            else:
                self.refresh_btn.SetBitmap(self.refresh_img.ConvertToBitmap())
                return

        self.label_throbber_sales.SetFont(wx.Font(settings.BOTTOM_STATUS_TEXT_SIZE, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, u'Verdana'))
        self.refresh_btn.Hide()
        self.label_throbber_sales.Show()
        self.throbber_sales.Show()
        self.throbber_sales.Play()
        
        self.OnSize(None)
        
        days_to_get = []
        for day,val in self.sales_period.unavailable_days.iteritems():
            days_to_get.append(day)
        
        self.UpdateRefreshStatus("Connecting...")
        
        self.sales_downloader = SalesDownloader(self, days_to_get)
        self.sales_downloader.start()
        
        self.refresh_btn.SetBitmap(self.refresh_img.ConvertToBitmap())
        
    def OnResult(self, event):
        str = event.data
        if (str == "SalesInfoRetrieved"):
            self.OnSalesFileLoadComplete()
            # self.OnServerUpdate(None)
            return
                
        if (str == "ReviewDownloadComplete"):
            # self.products.LoadImages(self.sales_period.product_ids, self.sales_period.product_names)
            self.SetStatusText("")
            self.sales_period.reviews = self.updater.reviews
                        
            return
        
        # print str
        self.UpdateRefreshStatus(str)

    def OnSettings(self, evt):
        """ display the settings dialog """          
        dlg = SettingsDialog(self, -1, "Settings", size=(320, 230),
                             style=wx.DEFAULT_DIALOG_STYLE)
        dlg.CenterOnScreen()
        # original_settings = copy.copy(self.settings)
        val = dlg.ShowModal()
        
        #if val == wx.ID_OK:
        #    self.settings.save
        #else: 
        #    self.settings = original_settings
        #    if self.slideshow_timer.IsRunning():
        #        self.slideshow_timer.Start(1000 * self.settings.slideshow_delay)
        #dlg.Destroy() for some reason this causes crahes...     
        
        
    def OnReviewAndIconUpdate(self, event):
        self.updater = UpdateDownloader(self.sales_period.product_ids, self)
        self.updater.start()
        
    def SetStatusText(self, txt):
        pass
    
    def OnAdd(self, event):
        add_dialog = AddEventDialog(self)
        if add_dialog.ShowModal() == wx.ID_OK:
            self.event_levels.append((
                mdates.date2num(self._wxDate2Python(add_dialog.date.GetValue())),
                add_dialog.text.GetValue()))
            self.UpdateLowerWidget()
                            
    def OnSize(self, event):
        if self.GetAutoLayout():
            self.Layout()

        try:
            products_rect = self.products.GetClientRect()
        except:
            return
        
        # print window_size
        graphics_size = self.notebook.GetClientRect()
        
        self.products.SetColumnWidth(1, products_rect.GetWidth() - 30)
        
        if not self.review_list == None:
            self.review_list.SetColumnWidth(0, graphics_size.GetWidth() - 200)
            self.review_list.SetColumnWidth(1, 100)
            self.review_list.SetColumnWidth(2, 70)
        
        if not self.popularity_list == None:
            self.popularity_list.SetColumnWidth(0, 30)
            self.popularity_list.SetColumnWidth(1, graphics_size.GetWidth() - 200)
        
        throbber_rect = self.throbber.GetClientRect()
        left = (products_rect.GetWidth() / 2) - (throbber_rect.GetWidth() / 2)
        top = (products_rect.GetHeight() / 2) - (throbber_rect.GetHeight() / 2)
        self.throbber.Move((left, top))
        
        label_rect = self.load_label.GetClientRect()
        self.load_label.Move(((products_rect.GetWidth() / 2)  - (label_rect.GetWidth() / 2), top - 30))
        self.load_label.Raise()
        
        refresh_rect = self.refresh_btn.GetRect()
        self.throbber_sales.SetPosition((refresh_rect.x, products_rect.GetHeight() + 17))
        
        if self.refresh_btn.IsShown():
            self.label_throbber_sales.SetPosition((refresh_rect.x + 96, products_rect.GetHeight() + settings.BOTTOM_TEXT_TOP_OFFSET))
        else:
            self.label_throbber_sales.SetPosition((refresh_rect.x + 36, products_rect.GetHeight() + settings.BOTTOM_TEXT_TOP_OFFSET))
        
    def OnExit(self, event):
        self.Close(True)

    def OnSliderChange(self, event):
        date_range = self.date_range.GetValue()
        if date_range <= 0:
            return
        
        self.date_entry.SetValue(date_range)
        self.date_start.SetValue(self.date_end.GetValue() - wx.DateSpan(days=date_range))
        self.UpdateLowerWidget()
    
        self.DisplayProductDataOnTopBar(self.selected_products[0])

    def OnDateEntryChange(self, event):
        date_range = self.date_entry.GetValue()
        if date_range <= 0:
            return
        self.date_range.SetValue(date_range)
        self.date_start.SetValue(
            self.date_end.GetValue() - wx.DateSpan(days=date_range))
        self.UpdateLowerWidget()
        
        self.DisplayProductDataOnTopBar(self.selected_products[0])
        
    def OnDateChange(self, event):
        date_range = (
            self.date_end.GetValue() - self.date_start.GetValue()).GetDays()
        if date_range <= 0:
            return
        self.date_entry.SetValue(date_range)
        self.date_range.SetValue(date_range)
        self.UpdateLowerWidget()
        
        self.DisplayProductDataOnTopBar(self.selected_products[0])

    def DisplayProductDataOnTopBar(self, product_id):
        
        date_to_view = self.sales_period.last_sales_day
        limits = (date_to_view, date_to_view)
        
        if product_id == None:
            self.product_name_label.SetLabel("All Products")
        else:
            self.product_name_label.SetLabel(self.sales_period.product_names[product_id])
        
        rev, cnt = self.sales_period.downloadsForProductOnLastReport(product_id, limits)
        if not rev == None: 
            self.revenue_label.SetLabel("Revenue on Last Report: " + rev)
            sales_for_range, sales_val = self.sales_period.revenueForRange(product_id, self.date_entry.GetValue())
            self.selected_range_label.SetLabel(sales_for_range)        
        
            avg_revenue = self.sales_period.averageRevenueForRange(product_id, self.date_entry.GetValue(), sales_val)
            self.last_income_label.SetLabel(avg_revenue)
        
    def OnProductSelected(self, event):
    
        item = self.products.GetFirstSelected()
        if item == wx.NOT_FOUND:
            products = []
            return
        elif item == 0:
            product_id = None
        else:
            product_id = self.products.GetItemData(item)
                
        self.selected_products = [product_id]
        self.UpdateLowerWidget()
        
        # product_ids = self.selected_products
        date_range = self.date_range.GetValue()

        self.DisplayProductDataOnTopBar(product_id)
        
        if not product_id == None:
            if self.sales_period.reviews.has_key(product_id):                      
                self.review_list.setReviews(self.sales_period.reviews[product_id])
            else:
                self.review_list.setReviews([])
            path = settings.DataDir("images/forapps/%i.jpg" % product_id)
            
            if (self.notebook.GetPageCount() == 4):
                self.notebook.SetSelection(0)
                self.notebook.RemovePage(1)
                self.notebook.Refresh()
        else:
            path = ""
            if (self.notebook.GetPageCount() == 3):
                self.notebook.InsertPage(1, self.popularity_list, "Quick Summary")

            
        if os.path.exists(path):
            try:
                img = wx.Image(path)
            except:
                img = wx.Image('images/all_apps_big.png')
        else:
            img = wx.Image('images/all_apps_big.png')
        
        self.app_image.SetBitmap(img.ConvertToBitmap())
        
        self.label_throbber_sales.Hide()

    def OnAmount(self, event):
        PlotPanel.displayCurrency = False
        self._rendererChange('paid_downloads')

    def OnProfit(self, event):
        PlotPanel.displayCurrency = True
        self._rendererChange('total_price')
        
        
    def _rendererChange(self, renderer):
        self.graph_renderer = operator.attrgetter(renderer)
        if self.notebook.GetCurrentPage().has_graphics:
            self.UpdateLowerWidget()

    @staticmethod
    def _wxDate2Python(wxdate):
        ymd = map(int, wxdate.FormatISODate().split('-')) 
        return datetime.date(*ymd)

    def GetDateLimits(self):
        return (
            self._wxDate2Python(self.date_start.GetValue()),
            self._wxDate2Python(self.date_end.GetValue()))

    def UpdateLowerWidget(self, event=None, delay=True):
    
        # A workaround to avoid repainting twice on item change.
        if self.delayed:
            if not delay:
                self.notebook.GetCurrentPage().Update()
                self.delayed = False
        else:
            self.delayed = True
            wx.CallLater(500, self.UpdateLowerWidget, event, delay=False)
    

        


########NEW FILE########
__FILENAME__ = plot_panel
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 


import csv, datetime, heapq, itertools, matplotlib, operator, os, wx, wxmpl
import random, sys, locale
import matplotlib.dates as mdates
import wx.lib.masked as masked
import    wx.lib.mixins.listctrl    as    listmix
from collections import defaultdict
from currency import convert_currency_to_usd
from app_info import AppInfoParser
import xml.sax
from apps_update import SalesDownloader

import time
from datetime import timedelta

import settings


class PlotPanel(wxmpl.PlotPanel):
    title = None
    has_graphics = True
    sales_period = None
    displayCurrency = False
    
    def __init__(self, parent):
        super(PlotPanel, self).__init__(
            parent, -1, cursor=False, location=False, crosshairs=False,
            selection=False, zoom=False)
        
        # self.SetWindowStyle(self.GetWindowStyle()|wx.NO_BORDER)
        
        self.colors = defaultdict(
            lambda: [random.random(), random.random(), random.random()])
        
        self.figure = self.get_figure()
        # self.figure.set_frameon(False)
        self.figure.set_edgecolor('white')
        self.figure.set_facecolor('white')
        # self.figure.set_linewidth(0)
        
        self.figure.subplots_adjust(
            hspace=0.2, left=0.05, top=0.95, right=0.95, bottom=0.05)

        self.panel = parent.GetParent()
        self.figure.clear()
        self.axes2 = self.figure.add_subplot(211)
        self.axes1 = self.figure.add_subplot(212)

    def Update(self):
        self.axes1.clear()
        #self.axes1.set_title("Sales Line Chart")
        self.axes2.clear()
        #self.axes2.set_title("Sales Bar Chart")

        date_range = self.panel.date_range.GetValue()
        product_ids = self.panel.selected_products

        show_sum = product_ids == [None]
        prefix = "sum_" if show_sum else ""
        product_data = getattr(
            self.panel.sales_period,
            '%s%s_sales' % (prefix,
                            ('daily' if date_range <= settings.DAYS_TO_SHOW else 'weekly')))
        
        # product_data = self.sales_period.daily_sales
        limits = self.panel.GetDateLimits()
        num_start, num_end = map(mdates.date2num, limits)

        total = len(product_ids)
        if total:
            bar_width = 1.0 / total

        # this is the name of the attribute like "amount" or "sales"
        value_getter = self.panel.graph_renderer
        max_value = None

        values = []

        # loop through all products
        for i, product_id in enumerate(product_ids):
            dates = [] # dictionary for dates, which is the horizontal axis
            values = [] # dictionary for the values
            
            # get the data for all or for a single product
            data = product_data.get(product_id, {}) if product_id else product_data

            last_date = None
            
            # loop through all the "Event" objects that have our sales data
            for event_date, event in data.iteritems():
                
                # numstart is the start of the date range we are interested in. The
                # Event object has a comparison function defined, so we look if the
                # object is within the range we are interested in
                if event >= num_start:
                    if last_date != event.end_num - 1:
                        if last_date:
                            dates.append(last_date + 1)
                            values.append(0)
                        
                        # Get the dates in the array
                        dates.append(event.end_num - 1)
                        values.append(0)
                    last_date = event.end_num
                    
                    if event <= num_end:
                        # print event
                        val = value_getter(event)
                        # print val
                        # if val > 0:
                        dates.append(event.end_num)
                        
                        # Get the value we want and put it in the dictionary
                        # value_getter(event) = self.panel.graph_renderer, which
                        # is operator.attrgetter('sales'). It gets the 'sales'
                        # variable from the event object. 
                        # print val
                        values.append(val)
                        
            else:
                if last_date:
                    dates.append(last_date + 1)
                    values.append(0)
            
            self.axes1.plot(
                dates, values, 'o-', color=self.colors[product_id])

            bar_dates, bar_values = [], []
            for date, value in itertools.izip(dates, values):
                if value:
                    bar_dates.append(date)
                    bar_values.append(value)
                    # print "VAL: " + value.__str__()

            rects = self.axes2.bar(
                [date + i*bar_width - 0.5 for date in bar_dates],
                bar_values, width=bar_width, color=self.colors[product_id])
            # label=(self.panel.product_names[product_id])
            for rect in rects:
                height = rect.get_height()
                
                if PlotPanel.displayCurrency:
                    self.axes2.text(rect.get_x()+rect.get_width()/2., 1.06*height,
                                settings.format_currency(height), ha='center', va='bottom')
                else:
                      self.axes2.text(rect.get_x()+rect.get_width()/2., 1.06*height,
                                '%d' % int(height), ha='center', va='bottom')

        if values:
            max_value = max(values)
            # print "Max Value: " + max_value.__str__()
            
            for value, text in self.panel.event_levels:
                line = self.axes1.plot(
                    [value, value], [0, max_value], '--', color="red")
                self.axes2.plot(
                    [value - 0.5, value - 0.5], [0, max_value], '--',
                    color="red")
                self.axes2.text(value - 1, 1.01 * max_value, text)

        interval = (max(1, (date_range / settings.MAX_TICKS * 2)))
        major_locator = mdates.DayLocator(interval=interval)  # every month
        minor_locator = mdates.DayLocator()
        dateFmt = mdates.DateFormatter(settings.date_format)
        self.axes1.set_xlim(num_start - 1, num_end + 1)
        self.axes2.set_xlim(num_start - 0.5, num_end + 0.5)
        for axes in (self.axes1, self.axes2):
            axes.set_ylim(0, max_value)
            axes.xaxis.set_major_locator(major_locator)
            axes.xaxis.set_major_formatter(dateFmt)
            axes.xaxis.set_minor_locator(minor_locator)
            axes.grid(True)
        self.draw()

########NEW FILE########
__FILENAME__ = popularity_list
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 

import wx
import settings

# Reviews Listview
class PopularityList(wx.ListCtrl):
    
    def __init__(self, parent):
        super(PopularityList, self).__init__(parent, style=wx.LC_REPORT)
        
        # self.reviews = [{"Text" : "This is the first review", "Reviewer" : "Mark", "Stars" : 5}]
        self.panel = parent.GetParent()
        self.InsertColumn(0, '#')
        self.InsertColumn(1, 'App Name')
        self.InsertColumn(2, 'Last Sale')
        self.InsertColumn(3, 'Downloads')
        
        # self.SetColumnWidth(0, 300)
        # self.SetColumnWidth(1, 100)
        # self.SetColumnWidth(2, 70)
     
            

    def SetData(self, sales_period):

        self.DeleteAllItems()
        
        date_to_view = sales_period.last_sales_day
        limits = (date_to_view, date_to_view)
        
        product_ids = sales_period.productIdsSorted(ByPopularity=True)
        
        pop = 1
        for product_id in product_ids:
            product_name = sales_period.product_names[product_id]
            revenue, cnt = sales_period.downloadsForProductOnLastReport(product_id, limits)
            
            index = self.InsertStringItem(pop, str(pop))
            self.SetStringItem(index, 1, product_name)
            self.SetStringItem(index, 2, revenue)
            self.SetStringItem(index, 3, str(cnt))
            pop = pop + 1
            
########NEW FILE########
__FILENAME__ = products_list
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

 
import wx
import wx.lib.mixins.listctrl as listmix
import os, sys
import settings


class ProductsList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, id):
        super(ProductsList, self).__init__(
            parent, id=id,
            style=wx.LC_REPORT|wx.LC_NO_HEADER|wx.LC_SINGLE_SEL|wx.NO_BORDER)
        
        # |wx.NO_BORDER
        
        self.InsertColumn(0, "Image", wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(1, "Item")

        self.SetColumnWidth(0, 5)
        self.SetColumnWidth(1, 170)
        self.SetBackgroundColour(settings.PRODUCTS_BG_COLOR)
        
        self.img_all = wx.Image("images/archive.png")
        self.img_all.Rescale(settings.IMAGE_SIDE, settings.IMAGE_SIDE)

        first_added = False

        img = wx.Image("images/iCube_32.png")
        img.Rescale(settings.IMAGE_SIDE, settings.IMAGE_SIDE)
        
        self.null_bmp = img.ConvertToBitmap() # wx.NullBitmap
        
        self.il = wx.ImageList(settings.IMAGE_SIDE, settings.IMAGE_SIDE)
        image_index = self.il.Add(self.img_all.ConvertToBitmap())
        self.SetImageList(
            self.il,
            wx.IMAGE_LIST_NORMAL if settings.BIG_IMAGES else wx.IMAGE_LIST_SMALL)
        

    def LoadImage(self, product_id, product_name):
        path = settings.DataDir("images/forapps/%i.jpg" % product_id)

        if os.path.exists(path):
            try:
                img = wx.Image(path)
                img.Rescale(settings.IMAGE_SIDE, settings.IMAGE_SIDE, quality=wx.IMAGE_QUALITY_HIGH)
                bmp = img.ConvertToBitmap()
            except:
                os.remove(path)
                bmp = self.null_bmp
        else:
            bmp = self.null_bmp
                
        image_index = -1
        if product_id == -1:
            image_index = self.il.Add(self.img_all.ConvertToBitmap())
        else:
            image_index = self.il.Add(bmp)
        
        index = self.FindItemData(-1, product_id)
        if index == -1:
            index = self.InsertStringItem(sys.maxint, "", -1)
            self.SetItemColumnImage(index, 1, image_index)
        else:
            self.SetItemColumnImage(index, 1, image_index)
            # self.SetItemImage(index, image_index)
            
        self.SetStringItem(index, 1, product_name)

        font = self.GetItemFont(index)
        font.SetPointSize(settings.PRODUCT_FONT_SIZE)
        font.SetFaceName(settings.PRODUCTS_FONT)
        self.SetItemFont(index, font)
        self.SetItemData(index, product_id)
        self.RefreshItem(index)
            
    def LoadImages(self, product_ids, product_names):
        all_ids = [-1] + product_ids[:]
        all_products = {-1: "All Products"}
        all_products.update(product_names)
        for id in all_ids:
            self.LoadImage(id, all_products[id])

########NEW FILE########
__FILENAME__ = pyDes
#############################################################################
# 				Documentation				    #
#############################################################################
 
# Author:   Todd Whiteman
# Date:     16th March, 2009
# Verion:   2.0.0
# License:  Public Domain - free to do as you wish
# Homepage: http://twhiteman.netfirms.com/des.html
#
# This is a pure python implementation of the DES encryption algorithm.
# It's pure python to avoid portability issues, since most DES 
# implementations are programmed in C (for performance reasons).
#
# Triple DES class is also implemented, utilising the DES base. Triple DES
# is either DES-EDE3 with a 24 byte key, or DES-EDE2 with a 16 byte key.
#
# See the README.txt that should come with this python module for the
# implementation methods used.
#
# Thanks to:
#  * David Broadwell for ideas, comments and suggestions.
#  * Mario Wolff for pointing out and debugging some triple des CBC errors.
#  * Santiago Palladino for providing the PKCS5 padding technique.
#  * Shaya for correcting the PAD_PKCS5 triple des CBC errors.
#
"""A pure python implementation of the DES and TRIPLE DES encryption algorithms.

Class initialization
--------------------
pyDes.des(key, [mode], [IV], [pad], [padmode])
pyDes.triple_des(key, [mode], [IV], [pad], [padmode])

key     -> Bytes containing the encryption key. 8 bytes for DES, 16 or 24 bytes
	   for Triple DES
mode    -> Optional argument for encryption type, can be either
	   pyDes.ECB (Electronic Code Book) or pyDes.CBC (Cypher Block Chaining)
IV      -> Optional Initial Value bytes, must be supplied if using CBC mode.
	   Length must be 8 bytes.
pad     -> Optional argument, set the pad character (PAD_NORMAL) to use during
	   all encrypt/decrpt operations done with this instance.
padmode -> Optional argument, set the padding mode (PAD_NORMAL or PAD_PKCS5)
	   to use during all encrypt/decrpt operations done with this instance.

I recommend to use PAD_PKCS5 padding, as then you never need to worry about any
padding issues, as the padding can be removed unambiguously upon decrypting
data that was encrypted using PAD_PKCS5 padmode.

Common methods
--------------
encrypt(data, [pad], [padmode])
decrypt(data, [pad], [padmode])

data    -> Bytes to be encrypted/decrypted
pad     -> Optional argument. Only when using padmode of PAD_NORMAL. For
	   encryption, adds this characters to the end of the data block when
	   data is not a multiple of 8 bytes. For decryption, will remove the
	   trailing characters that match this pad character from the last 8
	   bytes of the unencrypted data block.
padmode -> Optional argument, set the padding mode, must be one of PAD_NORMAL
	   or PAD_PKCS5). Defaults to PAD_NORMAL.
	  

Example
-------
from pyDes import *

data = "Please encrypt my data"
k = des("DESCRYPT", CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
# For Python3, you'll need to use bytes, i.e.:
#   data = b"Please encrypt my data"
#   k = des(b"DESCRYPT", CBC, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
d = k.encrypt(data)
print "Encrypted: %r" % d
print "Decrypted: %r" % k.decrypt(d)
assert k.decrypt(d, padmode=PAD_PKCS5) == data


See the module source (pyDes.py) for more examples of use.
You can also run the pyDes.py file without and arguments to see a simple test.

Note: This code was not written for high-end systems needing a fast
      implementation, but rather a handy portable solution with small usage.

"""

import sys

# _pythonMajorVersion is used to handle Python2 and Python3 differences.
_pythonMajorVersion = sys.version_info[0]

# Modes of crypting / cyphering
ECB =	0
CBC =	1

# Modes of padding
PAD_NORMAL = 1
PAD_PKCS5 = 2

# PAD_PKCS5: is a method that will unambiguously remove all padding
#            characters after decryption, when originally encrypted with
#            this padding mode.
# For a good description of the PKCS5 padding technique, see:
# http://www.faqs.org/rfcs/rfc1423.html

# The base class shared by des and triple des.
class _baseDes(object):
	def __init__(self, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		if IV:
			IV = self._guardAgainstUnicode(IV)
		if pad:
			pad = self._guardAgainstUnicode(pad)
		self.block_size = 8
		# Sanity checking of arguments.
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")
		if IV and len(IV) != self.block_size:
			raise ValueError("Invalid Initial Value (IV), must be a multiple of " + str(self.block_size) + " bytes")

		# Set the passed in variables
		self._mode = mode
		self._iv = IV
		self._padding = pad
		self._padmode = padmode

	def getKey(self):
		"""getKey() -> bytes"""
		return self.__key

	def setKey(self, key):
		"""Will set the crypting key for this object."""
		key = self._guardAgainstUnicode(key)
		self.__key = key

	def getMode(self):
		"""getMode() -> pyDes.ECB or pyDes.CBC"""
		return self._mode

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		self._mode = mode

	def getPadding(self):
		"""getPadding() -> bytes of length 1. Padding character."""
		return self._padding

	def setPadding(self, pad):
		"""setPadding() -> bytes of length 1. Padding character."""
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		self._padding = pad

	def getPadMode(self):
		"""getPadMode() -> pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		return self._padmode
		
	def setPadMode(self, mode):
		"""Sets the type of padding mode, pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		self._padmode = mode

	def getIV(self):
		"""getIV() -> bytes"""
		return self._iv

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		if not IV or len(IV) != self.block_size:
			raise ValueError("Invalid Initial Value (IV), must be a multiple of " + str(self.block_size) + " bytes")
		IV = self._guardAgainstUnicode(IV)
		self._iv = IV

	def _padData(self, data, pad, padmode):
		# Pad data depending on the mode
		if padmode is None:
			# Get the default padding mode.
			padmode = self.getPadMode()
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")

		if padmode == PAD_NORMAL:
			if len(data) % self.block_size == 0:
				# No padding required.
				return data

			if not pad:
				# Get the default padding.
				pad = self.getPadding()
			if not pad:
				raise ValueError("Data must be a multiple of " + str(self.block_size) + " bytes in length. Use padmode=PAD_PKCS5 or set the pad character.")
			data += (self.block_size - (len(data) % self.block_size)) * pad
		
		elif padmode == PAD_PKCS5:
			pad_len = 8 - (len(data) % self.block_size)
			if _pythonMajorVersion < 3:
				data += pad_len * chr(pad_len)
			else:
				data += bytes([pad_len] * pad_len)

		return data

	def _unpadData(self, data, pad, padmode):
		# Unpad data depending on the mode.
		if not data:
			return data
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")
		if padmode is None:
			# Get the default padding mode.
			padmode = self.getPadMode()

		if padmode == PAD_NORMAL:
			if not pad:
				# Get the default padding.
				pad = self.getPadding()
			if pad:
				data = data[:-self.block_size] + \
				       data[-self.block_size:].rstrip(pad)

		elif padmode == PAD_PKCS5:
			if _pythonMajorVersion < 3:
				pad_len = ord(data[-1])
			else:
				pad_len = data[-1]
			data = data[:-pad_len]

		return data

	def _guardAgainstUnicode(self, data):
		# Only accept byte strings or ascii unicode values, otherwise
		# there is no way to correctly decode the data into bytes.
		if _pythonMajorVersion < 3:
			if isinstance(data, unicode):
				raise ValueError("pyDes can only work with bytes, not Unicode strings.")
		else:
			if isinstance(data, str):
				# Only accept ascii unicode values.
				try:
					return data.encode('ascii')
				except UnicodeEncodeError:
					pass
				raise ValueError("pyDes can only work with encoded strings, not Unicode.")
		return data

#############################################################################
# 				    DES					    #
#############################################################################
class des(_baseDes):
	"""DES encryption/decrytpion class

	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key,[mode], [IV])

	key  -> Bytes containing the encryption key, must be exactly 8 bytes
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional Initial Value bytes, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	pad  -> Optional argument, set the pad character (PAD_NORMAL) to use
		during all encrypt/decrpt operations done with this instance.
	padmode -> Optional argument, set the padding mode (PAD_NORMAL or
		PAD_PKCS5) to use during all encrypt/decrpt operations done
		with this instance.
	"""


	# Permutation and translation tables for DES
	__pc1 = [56, 48, 40, 32, 24, 16,  8,
		  0, 57, 49, 41, 33, 25, 17,
		  9,  1, 58, 50, 42, 34, 26,
		 18, 10,  2, 59, 51, 43, 35,
		 62, 54, 46, 38, 30, 22, 14,
		  6, 61, 53, 45, 37, 29, 21,
		 13,  5, 60, 52, 44, 36, 28,
		 20, 12,  4, 27, 19, 11,  3
	]

	# number left rotations of pc1
	__left_rotations = [
		1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1
	]

	# permuted choice key (table 2)
	__pc2 = [
		13, 16, 10, 23,  0,  4,
		 2, 27, 14,  5, 20,  9,
		22, 18, 11,  3, 25,  7,
		15,  6, 26, 19, 12,  1,
		40, 51, 30, 36, 46, 54,
		29, 39, 50, 44, 32, 47,
		43, 48, 38, 55, 33, 52,
		45, 41, 49, 35, 28, 31
	]

	# initial permutation IP
	__ip = [57, 49, 41, 33, 25, 17, 9,  1,
		59, 51, 43, 35, 27, 19, 11, 3,
		61, 53, 45, 37, 29, 21, 13, 5,
		63, 55, 47, 39, 31, 23, 15, 7,
		56, 48, 40, 32, 24, 16, 8,  0,
		58, 50, 42, 34, 26, 18, 10, 2,
		60, 52, 44, 36, 28, 20, 12, 4,
		62, 54, 46, 38, 30, 22, 14, 6
	]

	# Expansion table for turning 32 bit blocks into 48 bits
	__expansion_table = [
		31,  0,  1,  2,  3,  4,
		 3,  4,  5,  6,  7,  8,
		 7,  8,  9, 10, 11, 12,
		11, 12, 13, 14, 15, 16,
		15, 16, 17, 18, 19, 20,
		19, 20, 21, 22, 23, 24,
		23, 24, 25, 26, 27, 28,
		27, 28, 29, 30, 31,  0
	]

	# The (in)famous S-boxes
	__sbox = [
		# S1
		[14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
		 0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
		 4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
		 15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],

		# S2
		[15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
		 3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
		 0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
		 13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],

		# S3
		[10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
		 13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
		 13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
		 1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],

		# S4
		[7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
		 13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
		 10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
		 3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],

		# S5
		[2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
		 14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
		 4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
		 11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],

		# S6
		[12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
		 10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
		 9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
		 4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],

		# S7
		[4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
		 13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
		 1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
		 6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],

		# S8
		[13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
		 1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
		 7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
		 2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
	]


	# 32-bit permutation function P used on the output of the S-boxes
	__p = [
		15, 6, 19, 20, 28, 11,
		27, 16, 0, 14, 22, 25,
		4, 17, 30, 9, 1, 7,
		23,13, 31, 26, 2, 8,
		18, 12, 29, 5, 21, 10,
		3, 24
	]

	# final permutation IP^-1
	__fp = [
		39,  7, 47, 15, 55, 23, 63, 31,
		38,  6, 46, 14, 54, 22, 62, 30,
		37,  5, 45, 13, 53, 21, 61, 29,
		36,  4, 44, 12, 52, 20, 60, 28,
		35,  3, 43, 11, 51, 19, 59, 27,
		34,  2, 42, 10, 50, 18, 58, 26,
		33,  1, 41,  9, 49, 17, 57, 25,
		32,  0, 40,  8, 48, 16, 56, 24
	]

	# Type of crypting being done
	ENCRYPT =	0x00
	DECRYPT =	0x01

	# Initialisation
	def __init__(self, key, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		# Sanity checking of arguments.
		if len(key) != 8:
			raise ValueError("Invalid DES key size. Key must be exactly 8 bytes long.")
		_baseDes.__init__(self, mode, IV, pad, padmode)
		self.key_size = 8

		self.L = []
		self.R = []
		self.Kn = [ [0] * 48 ] * 16	# 16 48-bit keys (K1 - K16)
		self.final = []

		self.setKey(key)

	def setKey(self, key):
		"""Will set the crypting key for this object. Must be 8 bytes."""
		_baseDes.setKey(self, key)
		self.__create_sub_keys()

	def __String_to_BitList(self, data):
		"""Turn the string data, into a list of bits (1, 0)'s"""
		if _pythonMajorVersion < 3:
			# Turn the strings into integers. Python 3 uses a bytes
			# class, which already has this behaviour.
			data = [ord(c) for c in data]
		l = len(data) * 8
		result = [0] * l
		pos = 0
		for ch in data:
			i = 7
			while i >= 0:
				if ch & (1 << i) != 0:
					result[pos] = 1
				else:
					result[pos] = 0
				pos += 1
				i -= 1

		return result

	def __BitList_to_String(self, data):
		"""Turn the list of bits -> data, into a string"""
		result = []
		pos = 0
		c = 0
		while pos < len(data):
			c += data[pos] << (7 - (pos % 8))
			if (pos % 8) == 7:
				result.append(c)
				c = 0
			pos += 1

		if _pythonMajorVersion < 3:
			return ''.join([ chr(c) for c in result ])
		else:
			return bytes(result)

	def __permutate(self, table, block):
		"""Permutate this block with the specified table"""
		return list(map(lambda x: block[x], table))
	
	# Transform the secret key, so that it is ready for data processing
	# Create the 16 subkeys, K[1] - K[16]
	def __create_sub_keys(self):
		"""Create the 16 subkeys K[1] to K[16] from the given key"""
		key = self.__permutate(des.__pc1, self.__String_to_BitList(self.getKey()))
		i = 0
		# Split into Left and Right sections
		self.L = key[:28]
		self.R = key[28:]
		while i < 16:
			j = 0
			# Perform circular left shifts
			while j < des.__left_rotations[i]:
				self.L.append(self.L[0])
				del self.L[0]

				self.R.append(self.R[0])
				del self.R[0]

				j += 1

			# Create one of the 16 subkeys through pc2 permutation
			self.Kn[i] = self.__permutate(des.__pc2, self.L + self.R)

			i += 1

	# Main part of the encryption algorithm, the number cruncher :)
	def __des_crypt(self, block, crypt_type):
		"""Crypt the block of data through DES bit-manipulation"""
		block = self.__permutate(des.__ip, block)
		self.L = block[:32]
		self.R = block[32:]

		# Encryption starts from Kn[1] through to Kn[16]
		if crypt_type == des.ENCRYPT:
			iteration = 0
			iteration_adjustment = 1
		# Decryption starts from Kn[16] down to Kn[1]
		else:
			iteration = 15
			iteration_adjustment = -1

		i = 0
		while i < 16:
			# Make a copy of R[i-1], this will later become L[i]
			tempR = self.R[:]

			# Permutate R[i - 1] to start creating R[i]
			self.R = self.__permutate(des.__expansion_table, self.R)

			# Exclusive or R[i - 1] with K[i], create B[1] to B[8] whilst here
			self.R = list(map(lambda x, y: x ^ y, self.R, self.Kn[iteration]))
			B = [self.R[:6], self.R[6:12], self.R[12:18], self.R[18:24], self.R[24:30], self.R[30:36], self.R[36:42], self.R[42:]]
			# Optimization: Replaced below commented code with above
			#j = 0
			#B = []
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.Kn[iteration][j]
			#	j += 1
			#	if j % 6 == 0:
			#		B.append(self.R[j-6:j])

			# Permutate B[1] to B[8] using the S-Boxes
			j = 0
			Bn = [0] * 32
			pos = 0
			while j < 8:
				# Work out the offsets
				m = (B[j][0] << 1) + B[j][5]
				n = (B[j][1] << 3) + (B[j][2] << 2) + (B[j][3] << 1) + B[j][4]

				# Find the permutation value
				v = des.__sbox[j][(m << 4) + n]

				# Turn value into bits, add it to result: Bn
				Bn[pos] = (v & 8) >> 3
				Bn[pos + 1] = (v & 4) >> 2
				Bn[pos + 2] = (v & 2) >> 1
				Bn[pos + 3] = v & 1

				pos += 4
				j += 1

			# Permutate the concatination of B[1] to B[8] (Bn)
			self.R = self.__permutate(des.__p, Bn)

			# Xor with L[i - 1]
			self.R = list(map(lambda x, y: x ^ y, self.R, self.L))
			# Optimization: This now replaces the below commented code
			#j = 0
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.L[j]
			#	j += 1

			# L[i] becomes R[i - 1]
			self.L = tempR

			i += 1
			iteration += iteration_adjustment
		
		# Final permutation of R[16]L[16]
		self.final = self.__permutate(des.__fp, self.R + self.L)
		return self.final


	# Data to be encrypted/decrypted
	def crypt(self, data, crypt_type):
		"""Crypt the data in blocks, running it through des_crypt()"""

		# Error check the data
		if not data:
			return ''
		if len(data) % self.block_size != 0:
			if crypt_type == des.DECRYPT: # Decryption must work on 8 byte blocks
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n.")
			if not self.getPadding():
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n. Try setting the optional padding character")
			else:
				data += (self.block_size - (len(data) % self.block_size)) * self.getPadding()
			# print "Len of data: %f" % (len(data) / self.block_size)

		if self.getMode() == CBC:
			if self.getIV():
				iv = self.__String_to_BitList(self.getIV())
			else:
				raise ValueError("For CBC mode, you must supply the Initial Value (IV) for ciphering")

		# Split the data into blocks, crypting each one seperately
		i = 0
		dict = {}
		result = []
		#cached = 0
		#lines = 0
		while i < len(data):
			# Test code for caching encryption results
			#lines += 1
			#if dict.has_key(data[i:i+8]):
				#print "Cached result for: %s" % data[i:i+8]
			#	cached += 1
			#	result.append(dict[data[i:i+8]])
			#	i += 8
			#	continue
				
			block = self.__String_to_BitList(data[i:i+8])

			# Xor with IV if using CBC mode
			if self.getMode() == CBC:
				if crypt_type == des.ENCRYPT:
					block = list(map(lambda x, y: x ^ y, block, iv))
					#j = 0
					#while j < len(block):
					#	block[j] = block[j] ^ iv[j]
					#	j += 1

				processed_block = self.__des_crypt(block, crypt_type)

				if crypt_type == des.DECRYPT:
					processed_block = list(map(lambda x, y: x ^ y, processed_block, iv))
					#j = 0
					#while j < len(processed_block):
					#	processed_block[j] = processed_block[j] ^ iv[j]
					#	j += 1
					iv = block
				else:
					iv = processed_block
			else:
				processed_block = self.__des_crypt(block, crypt_type)


			# Add the resulting crypted block to our list
			#d = self.__BitList_to_String(processed_block)
			#result.append(d)
			result.append(self.__BitList_to_String(processed_block))
			#dict[data[i:i+8]] = d
			i += 8

		# print "Lines: %d, cached: %d" % (lines, cached)

		# Return the full crypted string
		if _pythonMajorVersion < 3:
			return ''.join(result)
		else:
			return bytes.fromhex('').join(result)

	def encrypt(self, data, pad=None, padmode=None):
		"""encrypt(data, [pad], [padmode]) -> bytes

		data : Bytes to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, or
		the padmode is set to PAD_PKCS5, as bytes will then added to
		ensure the be padded data is a multiple of 8 bytes.
		"""
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		data = self._padData(data, pad, padmode)
		return self.crypt(data, des.ENCRYPT)

	def decrypt(self, data, pad=None, padmode=None):
		"""decrypt(data, [pad], [padmode]) -> bytes

		data : Bytes to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. In PAD_NORMAL mode, if the
		optional padding character is supplied, then the un-encrypted
		data will have the padding characters removed from the end of
		the bytes. This pad removal only occurs on the last 8 bytes of
		the data (last data block). In PAD_PKCS5 mode, the special
		padding end markers will be removed from the data after decrypting.
		"""
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		data = self.crypt(data, des.DECRYPT)
		return self._unpadData(data, pad, padmode)



#############################################################################
# 				Triple DES				    #
#############################################################################
class triple_des(_baseDes):
	"""Triple DES encryption/decrytpion class

	This algorithm uses the DES-EDE3 (when a 24 byte key is supplied) or
	the DES-EDE2 (when a 16 byte key is supplied) encryption methods.
	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key, [mode], [IV])

	key  -> Bytes containing the encryption key, must be either 16 or
	        24 bytes long
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional Initial Value bytes, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	pad  -> Optional argument, set the pad character (PAD_NORMAL) to use
		during all encrypt/decrpt operations done with this instance.
	padmode -> Optional argument, set the padding mode (PAD_NORMAL or
		PAD_PKCS5) to use during all encrypt/decrpt operations done
		with this instance.
	"""
	def __init__(self, key, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		_baseDes.__init__(self, mode, IV, pad, padmode)
		self.setKey(key)

	def setKey(self, key):
		"""Will set the crypting key for this object. Either 16 or 24 bytes long."""
		self.key_size = 24  # Use DES-EDE3 mode
		if len(key) != self.key_size:
			if len(key) == 16: # Use DES-EDE2 mode
				self.key_size = 16
			else:
				raise ValueError("Invalid triple DES key size. Key must be either 16 or 24 bytes long")
		if self.getMode() == CBC:
			if not self.getIV():
				# Use the first 8 bytes of the key
				self.setIV(key[:self.block_size])
			if len(self.getIV()) != self.block_size:
				raise ValueError("Invalid IV, must be 8 bytes in length")
		self.__key1 = des(key[:8], self._mode, self._iv,
				  self._padding, self._padmode)
		self.__key2 = des(key[8:16], self._mode, self._iv,
				  self._padding, self._padmode)
		if self.key_size == 16:
			self.__key3 = self.__key1
		else:
			self.__key3 = des(key[16:], self._mode, self._iv,
					  self._padding, self._padmode)
		_baseDes.setKey(self, key)

	# Override setter methods to work on all 3 keys.

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		_baseDes.setMode(self, mode)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setMode(mode)

	def setPadding(self, pad):
		"""setPadding() -> bytes of length 1. Padding character."""
		_baseDes.setPadding(self, pad)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setPadding(pad)

	def setPadMode(self, mode):
		"""Sets the type of padding mode, pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		_baseDes.setPadMode(self, mode)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setPadMode(mode)

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		_baseDes.setIV(self, IV)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setIV(IV)

	def encrypt(self, data, pad=None, padmode=None):
		"""encrypt(data, [pad], [padmode]) -> bytes

		data : bytes to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, or
		the padmode is set to PAD_PKCS5, as bytes will then added to
		ensure the be padded data is a multiple of 8 bytes.
		"""
		ENCRYPT = des.ENCRYPT
		DECRYPT = des.DECRYPT
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		# Pad the data accordingly.
		data = self._padData(data, pad, padmode)
		if self.getMode() == CBC:
			self.__key1.setIV(self.getIV())
			self.__key2.setIV(self.getIV())
			self.__key3.setIV(self.getIV())
			i = 0
			result = []
			while i < len(data):
				block = self.__key1.crypt(data[i:i+8], ENCRYPT)
				block = self.__key2.crypt(block, DECRYPT)
				block = self.__key3.crypt(block, ENCRYPT)
				self.__key1.setIV(block)
				self.__key2.setIV(block)
				self.__key3.setIV(block)
				result.append(block)
				i += 8
			if _pythonMajorVersion < 3:
				return ''.join(result)
			else:
				return bytes.fromhex('').join(result)
		else:
			data = self.__key1.crypt(data, ENCRYPT)
			data = self.__key2.crypt(data, DECRYPT)
			return self.__key3.crypt(data, ENCRYPT)

	def decrypt(self, data, pad=None, padmode=None):
		"""decrypt(data, [pad], [padmode]) -> bytes

		data : bytes to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. In PAD_NORMAL mode, if the
		optional padding character is supplied, then the un-encrypted
		data will have the padding characters removed from the end of
		the bytes. This pad removal only occurs on the last 8 bytes of
		the data (last data block). In PAD_PKCS5 mode, the special
		padding end markers will be removed from the data after
		decrypting, no pad character is required for PAD_PKCS5.
		"""
		ENCRYPT = des.ENCRYPT
		DECRYPT = des.DECRYPT
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		if self.getMode() == CBC:
			self.__key1.setIV(self.getIV())
			self.__key2.setIV(self.getIV())
			self.__key3.setIV(self.getIV())
			i = 0
			result = []
			while i < len(data):
				iv = data[i:i+8]
				block = self.__key3.crypt(iv,    DECRYPT)
				block = self.__key2.crypt(block, ENCRYPT)
				block = self.__key1.crypt(block, DECRYPT)
				self.__key1.setIV(iv)
				self.__key2.setIV(iv)
				self.__key3.setIV(iv)
				result.append(block)
				i += 8
			if _pythonMajorVersion < 3:
				data = ''.join(result)
			else:
				data = bytes.fromhex('').join(result)
		else:
			data = self.__key3.crypt(data, DECRYPT)
			data = self.__key2.crypt(data, ENCRYPT)
			data = self.__key1.crypt(data, DECRYPT)
		return self._unpadData(data, pad, padmode)

########NEW FILE########
__FILENAME__ = result_event
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

import wx

EVT_RESULT_ID = wx.NewId()

def EVT_RESULT(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, EVT_RESULT_ID, func)


class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data
########NEW FILE########
__FILENAME__ = reviews_list
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

 
import wx
import settings

# Reviews Listview
class ReviewsList(wx.ListCtrl):
    
    def __init__(self, parent):
        super(ReviewsList, self).__init__(parent, style=wx.LC_REPORT)
        
        # self.reviews = [{"Text" : "This is the first review", "Reviewer" : "Mark", "Stars" : 5}]
        self.panel = parent.GetParent()
        self.InsertColumn(0, 'Review Text', 300)
        self.InsertColumn(1, 'Reviewer Name')
        self.InsertColumn(2, 'Stars')
        
        self.SetColumnWidth(0, 300)
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(2, 70)
        

    def setReviews(self, reviews):
        
        self.DeleteAllItems()
        for i, review_dict in enumerate(reviews):
            # .decode('iso-8859-1')
            index = self.InsertStringItem(i, review_dict['ReviewBody'].decode('utf-8'))
            self.SetStringItem(index, 1, review_dict['ReviewHeader'])
            # self.SetStringItem(index, 2, str(review_dict['Stars']))
########NEW FILE########
__FILENAME__ = salesgraph
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 

import sys, wx, settings


class SalesGraphApp(wx.App):
	def OnInit(self):
	
		self.SetAppName(settings.APP_NAME)
			
		settings.do_one_time_debug_init()
		settings.start_log()
		
		from mainframe import MainFrame
		self.frame = MainFrame()
		self.frame.SetBackgroundColour( wx.Colour( 255, 255, 255 ) );
		self.frame.Show(True)
		self.SetTopWindow(self.frame)
		return True

	def OnExit(self):
		settings.log("App Exit")
        
app = SalesGraphApp(0)
app.MainLoop()

	
########NEW FILE########
__FILENAME__ = sales_list
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

 

import wx
import wx.lib.mixins.listctrl as listmix
import settings
import matplotlib.dates as mdates

# Sales Listview
class SalesListCtrl(wx.ListCtrl):
    has_graphics = False
    
    def __init__(self, parent):
        super(SalesListCtrl, self).__init__(parent, style=wx.LC_REPORT)
        self.panel = parent.GetParent()
        self.InsertColumn(0, 'Name')
        self.InsertColumn(1, 'Date')
        self.InsertColumn(2, 'Amount')
        self.InsertColumn(3, 'Profit')
        self.InsertColumn(4, 'Country')
      
        
    def Update(self):
        return
        
        self.DeleteAllItems()

        product_ids = self.panel.selected_products
        date_range = self.panel.date_range.GetValue()

        show_sum = product_ids == [None]
        prefix = "sum_" if show_sum else ""
        product_data = getattr(
            self.panel.sales_period,
            '%s%s_sales' % (prefix,
                            ('daily' if date_range <= settings.DAYS_TO_SHOW else 'weekly')))

        limits = self.panel.GetDateLimits()
        num_start, num_end = map(mdates.date2num, limits)

        for i, product_id in enumerate(product_ids):
            data = product_data if show_sum else product_data[product_id]
            for pos, event in enumerate(data):
                if event >= num_start:
                    if event <= num_end:
                        index = self.InsertStringItem(pos, event.name)
                        self.SetStringItem(
                            index, 1, event.end_date.strftime(settings.date_format))
                        self.SetStringItem(index, 2, str(event.sales))
                        self.SetStringItem(
                            index, 3, event.currency + str(event.total_price))
                        self.SetStringItem(index, 4, event.country)

    
########NEW FILE########
__FILENAME__ = sales_period
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.


 
from currency      import convert_currency_to_usd
from UnicodeReader import UnicodeReader
from matplotlib    import dates as mdates
from collections   import defaultdict
from datetime      import timedelta
from threading     import Thread
from result_event  import ResultEvent
from app_info      import AppInfoParser

import csv, heapq, os, time, datetime, itertools, operator, settings, wx, xml.sax

class SalesProcessorDialect(csv.excel):
    delimiter = '\t'
    quoting = csv.QUOTE_NONE
    lineterminator = '\n'

csv.register_dialect('sales', SalesProcessorDialect)

class SalesPeriod(Thread):
    def __init__(self, notify_window):
        self.loaded_dates = [] # All the days loaded
        self.daily_sales = defaultdict(dict) # first dict is product_id, second dict is days mapped to events
        self.weekly_sales = defaultdict(dict)
        
        self.sum_daily_sales = defaultdict(dict)
        self.sum_weekly_sales = defaultdict(dict)
        self.unavailable_days = {}
        self.available_days = {}
        self.product_names = {}
        self.product_ids = []
        self.notify_window = notify_window
        self.reviews = defaultdict(list)
        self.last_sales_day = None
        self.shutdown = False
        
        Thread.__init__(self)
    
    def run(self):
        settings.log("Starting sales file load")
        
        self.addSalesFiles()
        if (self.shutdown == True): 
            settings.log("Sales Load Thread Ended")
            return
        
        self.refreshSalesData()
        if (self.shutdown == True):
            settings.log("Sales Load Thread Ended")
            return
        
        if self.notify_window != None:
            try:
                wx.PostEvent(self.notify_window, ResultEvent("SalesInfoRetrieved"))
            except:
                print "Main window shutdown. Sales Thread could not notify"
            
        settings.log("Sales Load Thread Ended")
    
    def loadReviews(self, product_id):
        try:
            f = open(settings.SalesDir("xml/") + product_id.__str__() + ".xml", "r+")
        except:
            return
             
        parser = xml.sax.make_parser()
        handler = AppInfoParser()
        parser.setContentHandler(handler)
        try:
            parser.parse(settings.SalesDir("xml/") + product_id.__str__() + ".xml")
        except:
            # fails if wrong xml in dir
            pass
        
        self.reviews[product_id] = handler.reviews
        
        f.close()
        
        
    def isDateAlreadyLoaded(self, filename):
        f = open(filename, "rb")
        reader = UnicodeReader(f, dialect='sales')
        
        for fields in reader:
            # This loop only runs once
            try:
                begin_date = fields['Begin Date']
            except:
                return False
            
            already_loaded = False
            
            for d in self.loaded_dates:
                if d == begin_date:
                    already_loaded = True
        
                    if already_loaded:
                        f.close()
                        return True
        
            self.loaded_dates.append(begin_date)
            break
        
        f.close()
        return False
    
    def requestShutdown(self):
        settings.log("Shutdown of sales thread requested")
        self.shutdown = True
        
    def addSalesFile(self, filename):
        if (os.path.isdir(filename)):
            return
        
        if (self.shutdown == True):
            return
    
        # Check if we already have data for this date
        if self.isDateAlreadyLoaded(filename):
            if settings.MOVE_DOUBLE_FILES:
                try:
                    dir = settings.SalesDir("double/")
                    os.makedirs(dir)
                except:
                    pass
    
                import shutil
                shutil.move(filename, settings.SalesDir("double/" + os.path.basename(filename)))
            return None
    
        f = open(filename, "rb")
        settings.log("Loading: " + filename)
        reader = UnicodeReader(f, dialect='sales')
        
        for fields in reader:
            try:
                if fields['Product Type Identifier'] == "7":
                    continue
            except:
                # If exception is thrown here, file invalid
                return
            
            if (self.shutdown == True): return
            
            begin_date = fields['Begin Date']
            end_date = fields['End Date']
            
            begin_month, begin_day, begin_year = map(int, begin_date.split('/'))
            product_begin_date = datetime.date(begin_year, begin_month, begin_day)
                
            end_month, end_day, end_year = map(int, end_date.split('/'))
            product_end_date = datetime.date(end_year, end_month, end_day)

            product_id = int(fields['Apple Identifier'])
            self.product_names[product_id] = unicode(fields['Title / Episode / Season'], "utf-8")       
            
            sales = (self.daily_sales if begin_date == end_date else self.weekly_sales)
            
            sale_date_found = False
            new_sale_event = SalesForProductOnDate()
            new_sale_event.init_with_fields(fields, product_end_date)
            
            product_sale_list = sales[product_id] # gets dictionary mapping date to sales object
            
            # Search if we already have this date
            for sale_date, sale_event in product_sale_list.iteritems():
                if sale_event.end_num == new_sale_event.end_num:
                    product_sale_list[sale_event.end_num].paid_downloads += new_sale_event.paid_downloads
                    
                    # Handles case that same product has two prices on same day
                    product_sale_list[sale_event.end_num].total_price += new_sale_event.price * new_sale_event.paid_downloads
                    sale_date_found = True
            
            if sale_date_found == False:
                product_sale_list[new_sale_event.end_num] = new_sale_event
                self.available_days[new_sale_event.end_date] = True
        try:
            if self.last_sales_day == None or self.last_sales_day < new_sale_event.end_date:
                self.last_sales_day = new_sale_event.end_date
        except:
            pass # this happens if file invalid

    def sumSales(self):
        
        self.sum_daily_sales = {}
        self.yesterday_summary = []
        
        # Look through weekly and daily
        for product_id, date_sale_dict in self.daily_sales.iteritems():
            for sale_date, sale_event in date_sale_dict.iteritems():
                
                if (self.shutdown == True): return
                
                # Looping through all dates for each product
                if self.sum_daily_sales.has_key(sale_date) == True:
                    sum_sale_event = self.sum_daily_sales[sale_date]
                else:
                    sum_sale_event = SalesForProductOnDate(product_id=None, name='All', company='Unknown', 
                                                           price=0.0, currency='Unknown', country='Unknown', 
                                                           paid_downloads=0, end_date=sale_event.end_date)
                    self.sum_daily_sales[sale_date] = sum_sale_event
                    
                sum_sale_event.paid_downloads += sale_event.paid_downloads
                sum_sale_event.total_price += sale_event.total_price
                
    def popSorter(self, item1, item2):
        
        date_to_view = self.last_sales_day
        limits = (date_to_view, date_to_view)
        
        rev1, cnt1 = self.downloadsForProductOnLastReport(item1, limits)
        rev2, cnt2 = self.downloadsForProductOnLastReport(item2, limits)
        
        if cnt1 == cnt2:
            return 0
        
        if cnt1 > cnt2:
            return -1
        
        return 1
       
    def productIdsSorted(self, ByPopularity=True, ByName=False):
        # Will return the list of item ids, but sorted
        product_ids = sorted(self.product_ids, cmp=self.popSorter)
        
        return product_ids
        
    def addSalesFiles(self):
        import glob
        date_file_list = []
        for file in glob.glob(settings.SalesDir("*.txt")):
            stats = os.stat(file)
            lastmod_date = time.localtime(stats[8])
            date_file_tuple = lastmod_date, file
            date_file_list.append(date_file_tuple)
        
        item_count = len(date_file_list)
        i = 1
        date_file_list.sort()
        for d, f in date_file_list:
            self.addSalesFile('%s' % f)
            
            wx.PostEvent(self.notify_window, ResultEvent("SalesFileLoaded: Loaded " + str(i) + " of " + str(item_count)))
            i = i + 1
                    
    def refreshSalesData(self):
        settings.log("Refreshing sales data")
                      
        self.sumSales()
        self.unavailable_days = {}
        
        for i in range(settings.DAYS_TO_CHECK):
            the_day = datetime.datetime.now().date() - timedelta(days=i)
            
            if self.available_days.has_key(the_day) == False:
                self.unavailable_days[the_day] = True
                
        # Now sort the product IDs with respect to their title.
        self.product_names_reverse = defaultdict(list)
        for id, title in self.product_names.iteritems():
            self.product_names_reverse[title].append(id)
        
        # What is this for?
        for title, ids in sorted(self.product_names_reverse.iteritems()):
            self.product_ids.extend(ids)
            self.loadReviews(ids[0])

    def revenueForRange(self, product_id, number_of_days):
        if len(self.available_days) == 0:
             return
        
        range = (datetime.date.today() - datetime.timedelta(number_of_days), datetime.date.today())
        num_start, num_end = map(mdates.date2num, range)
        
        total_revenue = 0
        if product_id == None:
            sales = self.sum_daily_sales
        else:
            sales = self.daily_sales[product_id]
            
        for date, sale_event in sales.iteritems():
            if date >= num_start and date <= num_end:
                total_revenue = total_revenue + sale_event.total_price
    
        return "Revenue for last " + number_of_days.__str__() + " days: " + settings.format_currency(total_revenue), total_revenue
    
    def averageRevenueForRange(self, product_id, number_of_days, sales_for_range):
        val = sales_for_range / number_of_days
        return "Daily Average (" + number_of_days.__str__() + " days): " + settings.format_currency(val)

            
    def downloadsForProductOnLastReport(self, product_id, date_range):
        if len(self.available_days) == 0:
             return None, None
        
        num_start, num_end = map(mdates.date2num, date_range)
        
        if product_id == None:
            all_sales = self.sum_daily_sales[num_end]
            return settings.format_currency(all_sales.total_price), all_sales.paid_downloads

        day_count = 0            
        total_sales = 0
        if product_id == None:
            product_id = self.product_ids[0]
    
        data = self.daily_sales[product_id]
        if data.has_key(num_end) == False:
            return settings.format_currency(0), 0
        
        sales_event = data[num_end]
        
        return settings.format_currency(sales_event.total_price), sales_event.paid_downloads
    
    def lastSales(self, product_id):
        if len(self.available_days) == 0:
             return "No sales ever"
            
        if product_id == None:
            product_id = self.product_ids[0]
        
        
        the_sale_event = None 
        revenue = 0
        highest_date = 0
        sales = self.daily_sales[product_id]
        for date, sale_event in sales.iteritems():
            if date > highest_date:
                highest_date = date
                the_sale_event = sale_event

        return "Last day with sales: " + settings.format_currency(sale_event.total_price) + " on " + str(sale_event.end_date.strftime(settings.date_format))
    
        
        
class SalesForProductOnDate(object):
    def __init__(self, product_id=None, name='All', company='Unknown', price=0.0,
        currency='Unknown', country='Unknown', paid_downloads=0, end_date=None):
        
        if end_date != None:
            self.end_num = mdates.date2num(end_date)
            
        self.end_date = end_date
        self.product_id = product_id
        self.name = name
        self.company = company
        self.price = price
        self.currency = currency
        self.country = country
        self.paid_downloads = paid_downloads
        self.total_price = self.price * self.paid_downloads
                
    def init_with_fields(self, fields, end_date):
        self.__init__(int(fields['Apple Identifier']), fields['Title / Episode / Season'],
            fields['Artist / Show'], convert_currency_to_usd(float(fields['Royalty Price']), fields['Customer Currency']),
            'USD', fields['Country Code'],
            int(fields['Units']), end_date)

    def __cmp__(self, other):
        return (
            cmp(self.end_num, other) if isinstance(other, float)
            else cmp(self.end_num, other.end_num))

    def __str__(self):
        return "%s:%s@%s" % (self.name, self.paid_downloads, self.end_date)

    __repr__ = __str__
    
########NEW FILE########
__FILENAME__ = settings
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 
import locale
import matplotlib
import pickle
from pyDes import *
import sys, os, wx
from datetime import datetime
from datetime import date
from currency import ExchangeRate

locale.setlocale(locale.LC_ALL, '')

try:
    date_format = locale.nl_langinfo(locale.D_FMT)
except:
    date_format = '%m/%d/%y'
    
matplotlib.rcParams['font.sans-serif'] = ['Arial',
    'Helvetica', 'Bitstream Vera Sans', 'DejaVu Sans', 'Lucida Grande',
    'Verdana', 'Geneva', 'Lucid', 'Arial', 'Avant Garde', 'sans-serif']

matplotlib.rcParams['font.size'] = 9
matplotlib.rcParams['font.family'] = 'sans-serif'
CRYPT2 = "PubSubAgent." + str(894378)

def display_error(str, title="AppSalesGraph Error!", yes_no=False):
    import wx
    if yes_no == True:
        dlg = wx.MessageDialog(None, str, title, wx.YES_NO | wx.ICON_ERROR)
    else:
        dlg = wx.MessageDialog(None, str, title, wx.OK | wx.ICON_ERROR)
    result = dlg.ShowModal() == wx.ID_YES
    return result

def SalesDir(str = None):
    global SALES_DIR
    if not str == None:
        return SALES_DIR + "/" + str
    
    return SALES_DIR

def DataDir(str = None):
    if not str == None:
        return  wx.StandardPaths.Get().GetUserDataDir() + "/" + str
    
    return wx.StandardPaths.Get().GetUserDataDir()

def do_one_time_debug_init():
    
    # import currency
    # currency.download_all_currencies()
    
    if not os.path.exists(DataDir()):
        os.makedirs(DataDir())
    
    try:
        sales = SalesDir("sales_data")
        os.makedirs(sales)
    except:
        pass
    
    try:
        os.makedirs(DataDir("sales_data/xml/"))
    except:
        pass

    try:
        os.makedirs(SalesDir("double/"))
    except:
        pass
    
    try:
        os.makedirs(DataDir("images/forapps/"))
    except:
        pass

    
    if not os.path.exists(DataDir("currencies.key")):
        import shutil
        shutil.copyfile("currencies.key", DataDir("currencies.key"))
    
    log("DataDir: " + DataDir())
    
    # Create date file
    loc = wx.StandardPaths.Get().GetUserConfigDir()
    if not loc[len(loc)-1] == "/":
        loc = loc + "/"

    # Load currentcy file
    ExchangeRate.get("USD")
    
def format_currency(val):
    return "$" + str(round(val, 2))

def start_log():
    # os.remove("log.txt")
    try:
        file = open(DataDir("log.txt"), "w") # read mode
        file.write("AppSalesGraph 1.1 -- " + datetime.today().__str__() + "\r\n")
        file.write("OS: " + sys.platform + "\r\n\r\n")
        file.close()
    except:
        pass
    
    # Disable the shutdown messagebox
    # sys.stdout = open("salesgraph_stdout.log", "w")
    # sys.stderr = open("salesgraph_stderr.log", "w")
    
def log(str):
    print str
    
    try:
        file = open(DataDir("log.txt"), "a") # read mode
        file.write(str + "\r\n")
        file.close()
    except:
        pass

def gen_phrase():
    PASSPHRASE = ""
    PASSPHRASE = PASSPHRASE + chr(32)
    for i in range(65, 128):
        if i%10 == 0:
            PASSPHRASE = PASSPHRASE + chr(65 + i%30)
    PASSPHRASE = PASSPHRASE + chr(40)
    return PASSPHRASE
        
def save_settings():
    
    global APPLE_ID
    global APPLE_PW
    global SALES_DIR
    
    k = des(gen_phrase())
    settings_info = {"_" : k.encrypt(APPLE_ID.encode('ascii'), " "),
                     "-" : k.encrypt(APPLE_PW.encode('ascii'), " "),
                     "sales_dir" : SALES_DIR}
    
    file_name = DataDir("settings.dat")
    
    try:
        file = open(file_name, "w") # read mode
        pickle.dump(settings_info, file)
        file.close()
    except:
        print("CANNOT SAVE SETTINGS")

def load_settings():
    
    global SALES_DIR
    global APPLE_ID
    global APPLE_PW
    
    SALES_DIR = DataDir("sales_data")
    file_name = DataDir("settings.dat")
    
    try:
        file = open(file_name, "r") # read mode
    except:
        return
            
    try:
        settings_info = pickle.load(file)
    except:
        file.close()
        return
    

    
    k = des(gen_phrase())
    APPLE_ID = k.decrypt(settings_info["_"], " ")
    APPLE_PW = k.decrypt(settings_info["-"], " ")
    if settings_info.has_key('sales_dir'):
        SALES_DIR = settings_info['sales_dir']
        if (SALES_DIR == None or SALES_DIR == ""):
            SALES_DIR = DataDir("sales_data")
        
    file.close()

CRYPT1 = "system"
APP_NAME = "AppSalesGraph"
APP_VERSION = "0.5"
DAYS_TO_SHOW = 90
IMAGE_SIDE = 32
MAX_TICKS = 15
MAX_RANGE = 365
BIG_IMAGES = False

SALES_DIR = ""

PRODUCTS_BG_COLOR = (235,240,248)
APPLE_ID = ''
APPLE_PW = ''
DOWNLOAD_REVIEWS = True
DOWNLOAD_SALES = True
MOVE_DOUBLE_FILES = True
DAYS_TO_CHECK = 7
DAYS_LEFT = -1
if sys.platform == "win32":
    IS_WINDOWS = True
    PRODUCT_FONT_SIZE = 11
    PRODUCTS_FONT = "Candara"
    TOP_FONT_SIZE = 11
    TOP_FONT_MEDIUM_SIZE = 11
    TOP_FONT_SMALL_SIZE = 9
    BOTTOM_STATUS_TEXT_SIZE = 8
    BOTTOM_TEXT_TOP_OFFSET = 24
else:
    IS_WINDOWS = False
    PRODUCT_FONT_SIZE = 13
    PRODUCTS_FONT = "Helvetica"
    TOP_FONT_SIZE = 20
    TOP_FONT_MEDIUM_SIZE = 14
    TOP_FONT_SMALL_SIZE = 12
    BOTTOM_STATUS_TEXT_SIZE = 10
    BOTTOM_TEXT_TOP_OFFSET = 20
    
########NEW FILE########
__FILENAME__ = settings_dialog
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
 

import wx
import settings

class SettingsDialog(wx.Dialog):
    def __init__(self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, 
                 style=wx.DEFAULT_DIALOG_STYLE):
        
        # super(SettingsDialog, self).__init__(parent, ID, title)
        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI object using the Create
        # method.
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, ID, title, pos, size, style)
 
        
        # This next step is the most important, it turns this Python
        # object into the real wrapper of the dialog (instead of pre)
        # as far as the wxPython extension is concerned.
        self.PostCreate(pre)
        
        icon = wx.Icon("images/settings.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        # Create the labels on the left
        wx.StaticText(self, -1, "iTunes User Name:", pos=(1,33),  size=(70,30),
                      style=wx.ALIGN_RIGHT)

        wx.StaticText(self, -1, "iTunes Password:", pos=(1,73),size=(70,30),
                      style=wx.ALIGN_RIGHT)

        wx.StaticText(self, -1, "Sales Directory:", pos=(1,113),size=(70,30),
                      style=wx.ALIGN_RIGHT)
        
        self.text = wx.TextCtrl(self, -1, pos=(100,36),size=(180,20), value=settings.APPLE_ID)
        self.passw = wx.TextCtrl(self, -1, pos=(100,76),size=(180,20), style = wx.TE_PASSWORD, value=settings.APPLE_PW)
        self.sales_dir = wx.TextCtrl(self, -1, pos=(100,116),size=(100,20), value=settings.SALES_DIR)
        self.browse_btn = wx.Button(self, -1, "Select...", pos=(215,116))
        self.Bind(wx.EVT_BUTTON, self.OnBrowseForDir, self.browse_btn)
        
        # OK and Cancel Buttons
        btnOK = wx.Button(self, -1, "OK", pos=(160, 160), size=(70,30))
        btnOK.SetDefault()
        btnCancel = wx.Button(self, -1, "Cancel", pos=(235, 160), size=(70,30))
        self.Bind(wx.EVT_BUTTON, self.OnOK, btnOK)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, btnCancel)
        
        # Show
        # self.Show(True)
        # get access to the parent form and the parent settings
        # self.parent = parent
       # self.settings = parent.settings

        # initialize values
        # self.ctlDelay.SetValue(self.settings.slideshow_delay)    

    def OnBrowseForDir(self,event):
        dialog = wx.DirDialog(self, message = "Select the folder", style = 0)
        
        if dialog.ShowModal() == wx.ID_OK:
            self.sales_dir.SetValue(dialog.GetPath())
            
    def OnOK(self,event):
        """ OK Button Clicked """
        settings.APPLE_ID = self.text.GetValue()
        settings.APPLE_PW = self.passw.GetValue()
        settings.SALES_DIR = self.sales_dir.GetValue()
        
        self.EndModal(wx.ID_OK)

    def OnCancel(self,event):
        """ Cancel Button Clicked """
        self.EndModal(wx.ID_CANCEL)


########NEW FILE########
__FILENAME__ = UnicodeReader
# AppSalesGraph: AppStore Sales Graphing
# Copyright (c) 2010 by Max Klein (maximusklein@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

import csv, codecs, cStringIO
 
class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()#
        return row
    
        # print "ROW:" + row.__str__()
        # return [unicode(s, "utf-8") for s in row]
        
    def __getitem__(self):
        return self.reader.__getitem__()
    
    def __iter__(self):
        return self

########NEW FILE########
__FILENAME__ = wxmpl
# Purpose: painless matplotlib embedding for wxPython
# Author: Ken McIvor <mcivor@iit.edu>
#
# Copyright 2005-2009 Illinois Institute of Technology
#
# See the file "LICENSE" for information on usage and redistribution
# of this file, and for a DISCLAIMER OF ALL WARRANTIES.
 
"""
Embedding matplotlib in wxPython applications is straightforward, but the
default plotting widget lacks the capabilities necessary for interactive use.
WxMpl (wxPython+matplotlib) is a library of components that provide these
missing features in the form of a better matplolib FigureCanvas.
"""


import wx
import sys
import os.path
import weakref

import matplotlib
matplotlib.use('WXAgg')
import matplotlib.numerix as Numerix
from matplotlib.axes import _process_plot_var_args
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.backends.backend_agg import FigureCanvasAgg, RendererAgg
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.projections.polar import PolarAxes
from matplotlib.transforms import Bbox

__version__ = '1.3.1'

__all__ = ['PlotPanel', 'PlotFrame', 'PlotApp', 'StripCharter', 'Channel',
    'FigurePrinter', 'PointEvent', 'EVT_POINT', 'SelectionEvent',
    'EVT_SELECTION']

# If you are using wxGtk without libgnomeprint and want to use something other
# than `lpr' to print you will have to specify that command here.
POSTSCRIPT_PRINTING_COMMAND = 'lpr'

# Between 0.98.1 and 0.98.3rc there were some significant API changes:
#   * FigureCanvasWx.draw(repaint=True) became draw(drawDC=None)
#   * The following events were added:
#       - figure_enter_event
#       - figure_leave_event
#       - axes_enter_event
#       - axes_leave_event
MATPLOTLIB_0_98_3 = '0.98.3' <= matplotlib.__version__


#
# Utility functions and classes
#

def invert_point(x, y, transform):
    """
    Returns a coordinate inverted by the specificed C{Transform}.
    """
    return transform.inverted().transform_point((x, y))


def find_axes(canvas, x, y):
    """
    Finds the C{Axes} within a matplotlib C{FigureCanvas} contains the canvas
    coordinates C{(x, y)} and returns that axes and the corresponding data
    coordinates C{xdata, ydata} as a 3-tuple.

    If no axes contains the specified point a 3-tuple of C{None} is returned.
    """
    evt = matplotlib.backend_bases.MouseEvent('', canvas, x, y)

    axes = None
    for a in canvas.get_figure().get_axes():
        if a.in_axes(evt):
            if axes is None:
                axes = a
            else:
                return None, None, None

    if axes is None:
        return None, None, None

    xdata, ydata = invert_point(x, y, axes.transData)
    return axes, xdata, ydata


def get_bbox_lims(bbox):
    """
    Returns the boundaries of the X and Y intervals of a C{Bbox}.
    """
    p0 = bbox.min
    p1 = bbox.max
    return (p0[0], p1[0]), (p0[1], p1[1])


def find_selected_axes(canvas, x1, y1, x2, y2):
    """
    Finds the C{Axes} within a matplotlib C{FigureCanvas} that overlaps with a
    canvas area from C{(x1, y1)} to C{(x1, y1)}.  That axes and the
    corresponding X and Y axes ranges are returned as a 3-tuple.

    If no axes overlaps with the specified area, or more than one axes
    overlaps, a 3-tuple of C{None}s is returned.
    """
    axes = None
    bbox = Bbox.from_extents(x1, y1, x2, y2)

    for a in canvas.get_figure().get_axes():
        if bbox.overlaps(a.bbox):
            if axes is None:
                axes = a
            else:
                return None, None, None

    if axes is None:
        return None, None, None

    x1, y1, x2, y2 = limit_selection(bbox, axes)
    xrange, yrange = get_bbox_lims(
        Bbox.from_extents(x1, y1, x2, y2).inverse_transformed(axes.transData))
    return axes, xrange, yrange


def limit_selection(bbox, axes):
    """
    Finds the region of a selection C{bbox} which overlaps with the supplied
    C{axes} and returns it as the 4-tuple C{(xmin, ymin, xmax, ymax)}.
    """
    bxr, byr = get_bbox_lims(bbox)
    axr, ayr = get_bbox_lims(axes.bbox)

    xmin = max(bxr[0], axr[0])
    xmax = min(bxr[1], axr[1])
    ymin = max(byr[0], ayr[0])
    ymax = min(byr[1], ayr[1])
    return xmin, ymin, xmax, ymax


def format_coord(axes, xdata, ydata):
    """
    A C{None}-safe version of {Axes.format_coord()}.
    """
    if xdata is None or ydata is None:
        return ''
    return axes.format_coord(xdata, ydata)


def toplevel_parent_of_window(window):
    """
    Returns the first top-level parent of a wx.Window
    """
    topwin = window
    while not isinstance(topwin, wx.TopLevelWindow):
        topwin = topwin.GetParent()
    return topwin       


class AxesLimits:
    """
    Alters the X and Y limits of C{Axes} objects while maintaining a history of
    the changes.
    """
    def __init__(self, autoscaleUnzoom):
        self.autoscaleUnzoom = autoscaleUnzoom
        self.history = weakref.WeakKeyDictionary()

    def setAutoscaleUnzoom(self, state):
        """
        Enable or disable autoscaling the axes as a result of zooming all the
        way back out.
        """
        self.limits.setAutoscaleUnzoom(state)

    def _get_history(self, axes):
        """
        Returns the history list of X and Y limits associated with C{axes}.
        """
        return self.history.setdefault(axes, [])

    def zoomed(self, axes):
        """
        Returns a boolean indicating whether C{axes} has had its limits
        altered.
        """
        return not (not self._get_history(axes))

    def set(self, axes, xrange, yrange):
        """
        Changes the X and Y limits of C{axes} to C{xrange} and {yrange}
        respectively.  A boolean indicating whether or not the
        axes should be redraw is returned, because polar axes cannot have
        their limits changed sensibly.
        """
        if not axes.can_zoom():
            return False

        # The axes limits must be converted to tuples because MPL 0.98.1
        # returns the underlying array objects
        oldRange = tuple(axes.get_xlim()), tuple(axes.get_ylim())

        history = self._get_history(axes)
        history.append(oldRange)
        axes.set_xlim(xrange)
        axes.set_ylim(yrange)
        return True

    def restore(self, axes):
        """
        Changes the X and Y limits of C{axes} to their previous values.  A
        boolean indicating whether or not the axes should be redraw is
        returned.
        """
        history = self._get_history(axes)
        if not history:
            return False

        xrange, yrange = history.pop()
        if self.autoscaleUnzoom and not len(history):
            axes.autoscale_view()
        else:
            axes.set_xlim(xrange)
            axes.set_ylim(yrange)
        return True


#
# Director of the matplotlib canvas
#

class PlotPanelDirector:
    """
    Encapsulates all of the user-interaction logic required by the
    C{PlotPanel}, following the Humble Dialog Box pattern proposed by Michael
    Feathers:
    U{http://www.objectmentor.com/resources/articles/TheHumbleDialogBox.pdf}
    """

    # TODO: add a programmatic interface to zooming and user interactions
    # TODO: full support for MPL events

    def __init__(self, view, zoom=True, selection=True, rightClickUnzoom=True,
      autoscaleUnzoom=True):
        """
        Create a new director for the C{PlotPanel} C{view}.  The keyword
        arguments C{zoom} and C{selection} have the same meanings as for
        C{PlotPanel}.
        """
        self.view = view
        self.zoomEnabled = zoom
        self.selectionEnabled = selection
        self.rightClickUnzoom = rightClickUnzoom
        self.limits = AxesLimits(autoscaleUnzoom)
        self.leftButtonPoint = None

    def setSelection(self, state):
        """
        Enable or disable left-click area selection.
        """
        self.selectionEnabled = state

    def setZoomEnabled(self, state):
        """
        Enable or disable zooming as a result of left-click area selection.
        """
        self.zoomEnabled = state

    def setAutoscaleUnzoom(self, state):
        """
        Enable or disable autoscaling the axes as a result of zooming all the
        way back out.
        """
        self.limits.setAutoscaleUnzoom(state)

    def setRightClickUnzoom(self, state):
        """
        Enable or disable unzooming as a result of right-clicking.
        """
        self.rightClickUnzoom = state

    def canDraw(self):
        """
        Indicates if plot may be not redrawn due to the presence of a selection
        box.
        """
        return self.leftButtonPoint is None

    def zoomed(self, axes):
        """
        Returns a boolean indicating whether or not the plot has been zoomed in
        as a result of a left-click area selection.
        """
        return self.limits.zoomed(axes)

    def keyDown(self, evt):
        """
        Handles wxPython key-press events.  These events are currently skipped.
        """
        evt.Skip()

    def keyUp(self, evt):
        """
        Handles wxPython key-release events.  These events are currently
        skipped.
        """
        evt.Skip()

    def leftButtonDown(self, evt, x, y):
        """
        Handles wxPython left-click events.
        """
        self.leftButtonPoint = (x, y)

        view = self.view
        axes, xdata, ydata = find_axes(view, x, y)

        if axes is not None and self.selectionEnabled and axes.can_zoom():
            view.cursor.setCross()
            view.crosshairs.clear()

    def leftButtonUp(self, evt, x, y):
        """
        Handles wxPython left-click-release events.
        """
        if self.leftButtonPoint is None:
            return

        view = self.view
        axes, xdata, ydata = find_axes(view, x, y)

        x0, y0 = self.leftButtonPoint
        self.leftButtonPoint = None
        view.rubberband.clear()

        if x0 == x:
            if y0 == y and axes is not None:
                view.notify_point(axes, x, y)
                view.crosshairs.set(x, y)
            return
        elif y0 == y:
            return

        xdata = ydata = None
        axes, xrange, yrange = find_selected_axes(view, x0, y0, x, y)

        if axes is not None:
            xdata, ydata = invert_point(x, y, axes.transData)
            if self.zoomEnabled:
                if self.limits.set(axes, xrange, yrange):
                    self.view.draw()
            else:
                bbox = Bbox.from_extents(x0, y0, x, y)
                x1, y1, x2, y2 = limit_selection(bbox, axes)
                self.view.notify_selection(axes, x1, y1, x2, y2)

        if axes is None:
            view.cursor.setNormal()
        elif not axes.can_zoom():
            view.cursor.setNormal()
            view.location.set(format_coord(axes, xdata, ydata))
        else:
            view.crosshairs.set(x, y)
            view.location.set(format_coord(axes, xdata, ydata))

    def rightButtonDown(self, evt, x, y):
        """
        Handles wxPython right-click events.  These events are currently
        skipped.
        """
        evt.Skip()

    def rightButtonUp(self, evt, x, y):
        """
        Handles wxPython right-click-release events.
        """
        view = self.view
        axes, xdata, ydata = find_axes(view, x, y)
        if (axes is not None and self.zoomEnabled and self.rightClickUnzoom
        and self.limits.restore(axes)):
            view.crosshairs.clear()
            view.draw()
            view.crosshairs.set(x, y)

    def mouseMotion(self, evt, x, y):
        """
        Handles wxPython mouse motion events, dispatching them based on whether
        or not a selection is in process and what the cursor is over.
        """
        view = self.view
        axes, xdata, ydata = find_axes(view, x, y)

        if self.leftButtonPoint is not None:
            self.selectionMouseMotion(evt, x, y, axes, xdata, ydata)
        else:
            if axes is None:
                self.canvasMouseMotion(evt, x, y)
            elif not axes.can_zoom():
                self.unzoomableAxesMouseMotion(evt, x, y, axes, xdata, ydata)
            else:
                self.axesMouseMotion(evt, x, y, axes, xdata, ydata)

    def selectionMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Handles wxPython mouse motion events that occur during a left-click
        area selection.
        """
        view = self.view
        x0, y0 = self.leftButtonPoint
        view.rubberband.set(x0, y0, x, y)
        if axes is None:
            view.location.clear()
        else:
            view.location.set(format_coord(axes, xdata, ydata))

    def canvasMouseMotion(self, evt, x, y):
        """
        Handles wxPython mouse motion events that occur over the canvas.
        """
        view = self.view
        view.cursor.setNormal()
        view.crosshairs.clear()
        view.location.clear()

    def axesMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Handles wxPython mouse motion events that occur over an axes.
        """
        view = self.view
        view.cursor.setCross()
        view.crosshairs.set(x, y)
        view.location.set(format_coord(axes, xdata, ydata))

    def unzoomableAxesMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Handles wxPython mouse motion events that occur over an axes that does
        not support zooming.
        """
        view = self.view
        view.cursor.setNormal()
        view.location.set(format_coord(axes, xdata, ydata))


#
# Components used by the PlotPanel
#

class Painter:
    """
    Painters encapsulate the mechanics of drawing some value in a wxPython
    window and erasing it.  Subclasses override template methods to process
    values and draw them.

    @cvar PEN: C{wx.Pen} to use (defaults to C{wx.BLACK_PEN})
    @cvar BRUSH: C{wx.Brush} to use (defaults to C{wx.TRANSPARENT_BRUSH})
    @cvar FUNCTION: Logical function to use (defaults to C{wx.COPY})
    @cvar FONT: C{wx.Font} to use (defaults to C{wx.NORMAL_FONT})
    @cvar TEXT_FOREGROUND: C{wx.Colour} to use (defaults to C{wx.BLACK})
    @cvar TEXT_BACKGROUND: C{wx.Colour} to use (defaults to C{wx.WHITE})
    """

    PEN = wx.BLACK_PEN
    BRUSH = wx.TRANSPARENT_BRUSH
    FUNCTION = wx.COPY
    FONT = wx.NORMAL_FONT
    TEXT_FOREGROUND = wx.BLACK
    TEXT_BACKGROUND = wx.WHITE

    def __init__(self, view, enabled=True):
        """
        Create a new painter attached to the wxPython window C{view}.  The
        keyword argument C{enabled} has the same meaning as the argument to the
        C{setEnabled()} method.
        """
        self.view = view
        self.lastValue = None
        self.enabled = enabled

    def setEnabled(self, state):
        """
        Enable or disable this painter.  Disabled painters do not draw their
        values and calls to C{set()} have no effect on them.
        """
        oldState, self.enabled = self.enabled, state
        if oldState and not self.enabled:
            self.clear()

    def set(self, *value):
        """
        Update this painter's value and then draw it.  Values may not be
        C{None}, which is used internally to represent the absence of a current
        value.
        """
        if self.enabled:
            value = self.formatValue(value)
            self._paint(value, None)

    def redraw(self, dc=None):
        """
        Redraw this painter's current value.
        """
        value = self.lastValue
        self.lastValue = None
        self._paint(value, dc)

    def clear(self, dc=None):
        """
        Clear the painter's current value from the screen and the painter
        itself.
        """
        if self.lastValue is not None:
            self._paint(None, dc)

    def _paint(self, value, dc):
        """
        Draws a previously processed C{value} on this painter's window.
        """
        if dc is None:
            dc = wx.ClientDC(self.view)

        dc.SetPen(self.PEN)
        dc.SetBrush(self.BRUSH)
        dc.SetFont(self.FONT)
        dc.SetTextForeground(self.TEXT_FOREGROUND)
        dc.SetTextBackground(self.TEXT_BACKGROUND)
        dc.SetLogicalFunction(self.FUNCTION)
        dc.BeginDrawing()

        if self.lastValue is not None:
            self.clearValue(dc, self.lastValue)
            self.lastValue = None

        if value is not None:
            self.drawValue(dc, value)
            self.lastValue = value

        dc.EndDrawing()

    def formatValue(self, value):
        """
        Template method that processes the C{value} tuple passed to the
        C{set()} method, returning the processed version.
        """
        return value

    def drawValue(self, dc, value):
        """
        Template method that draws a previously processed C{value} using the
        wxPython device context C{dc}.  This DC has already been configured, so
        calls to C{BeginDrawing()} and C{EndDrawing()} may not be made.
        """
        pass

    def clearValue(self, dc, value):
        """
        Template method that clears a previously processed C{value} that was
        previously drawn, using the wxPython device context C{dc}.  This DC has
        already been configured, so calls to C{BeginDrawing()} and
        C{EndDrawing()} may not be made.
        """
        pass


class LocationPainter(Painter):
    """
    Draws a text message containing the current position of the mouse in the
    lower left corner of the plot.
    """

    PADDING = 2
    PEN = wx.WHITE_PEN
    BRUSH = wx.WHITE_BRUSH

    def formatValue(self, value):
        """
        Extracts a string from the 1-tuple C{value}.
        """
        return value[0]

    def get_XYWH(self, dc, value):
        """
        Returns the upper-left coordinates C{(X, Y)} for the string C{value}
        its width and height C{(W, H)}.
        """
        height = dc.GetSize()[1]
        w, h = dc.GetTextExtent(value)
        x = self.PADDING
        y = int(height - (h + self.PADDING))
        return x, y, w, h

    def drawValue(self, dc, value):
        """
        Draws the string C{value} in the lower left corner of the plot.
        """
        x, y, w, h = self.get_XYWH(dc, value)
        dc.DrawText(value, x, y)

    def clearValue(self, dc, value):
        """
        Clears the string C{value} from the lower left corner of the plot by
        painting a white rectangle over it.
        """
        x, y, w, h = self.get_XYWH(dc, value)
        dc.DrawRectangle(x, y, w, h)


class CrosshairPainter(Painter):
    """
    Draws crosshairs through the current position of the mouse.
    """

    PEN = wx.WHITE_PEN
    FUNCTION = wx.XOR

    def formatValue(self, value):
        """
        Converts the C{(X, Y)} mouse coordinates from matplotlib to wxPython.
        """
        x, y = value
        return int(x), int(self.view.get_figure().bbox.height - y)

    def drawValue(self, dc, value):
        """
        Draws crosshairs through the C{(X, Y)} coordinates.
        """
        dc.CrossHair(*value)

    def clearValue(self, dc, value):
        """
        Clears the crosshairs drawn through the C{(X, Y)} coordinates.
        """
        dc.CrossHair(*value)


class RubberbandPainter(Painter):
    """
    Draws a selection rubberband from one point to another.
    """

    PEN = wx.WHITE_PEN
    FUNCTION = wx.XOR

    def formatValue(self, value):
        """
        Converts the C{(x1, y1, x2, y2)} mouse coordinates from matplotlib to
        wxPython.
        """
        x1, y1, x2, y2 = value
        height = self.view.get_figure().bbox.height
        y1 = height - y1
        y2 = height - y2
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        return [int(z) for z in (x1, y1, x2-x1, y2-y1)]

    def drawValue(self, dc, value):
        """
        Draws the selection rubberband around the rectangle
        C{(x1, y1, x2, y2)}.
        """
        dc.DrawRectangle(*value)

    def clearValue(self, dc, value):
        """
        Clears the selection rubberband around the rectangle
        C{(x1, y1, x2, y2)}.
        """
        dc.DrawRectangle(*value)


class CursorChanger:
    """
    Manages the current cursor of a wxPython window, allowing it to be switched
    between a normal arrow and a square cross.
    """
    def __init__(self, view, enabled=True):
        """
        Create a CursorChanger attached to the wxPython window C{view}.  The
        keyword argument C{enabled} has the same meaning as the argument to the
        C{setEnabled()} method.
        """
        self.view = view
        self.cursor = wx.CURSOR_DEFAULT
        self.enabled = enabled

    def setEnabled(self, state):
        """
        Enable or disable this cursor changer.  When disabled, the cursor is
        reset to the normal arrow and calls to the C{set()} methods have no
        effect.
        """
        oldState, self.enabled = self.enabled, state
        if oldState and not self.enabled and self.cursor != wx.CURSOR_DEFAULT:
            self.cursor = wx.CURSOR_DEFAULT
            self.view.SetCursor(wx.STANDARD_CURSOR)

    def setNormal(self):
        """
        Change the cursor of the associated window to a normal arrow.
        """
        if self.cursor != wx.CURSOR_DEFAULT and self.enabled:
            self.cursor = wx.CURSOR_DEFAULT
            self.view.SetCursor(wx.STANDARD_CURSOR)

    def setCross(self):
        """
        Change the cursor of the associated window to a square cross.
        """
        if self.cursor != wx.CURSOR_CROSS and self.enabled:
            self.cursor = wx.CURSOR_CROSS
            self.view.SetCursor(wx.CROSS_CURSOR)


#
# Printing Framework
#

# PostScript resolutions for the various WX print qualities
PS_DPI_HIGH_QUALITY   = 600
PS_DPI_MEDIUM_QUALITY = 300
PS_DPI_LOW_QUALITY    = 150
PS_DPI_DRAFT_QUALITY  = 72


def update_postscript_resolution(printData):
    """
    Sets the default wx.PostScriptDC resolution from a wx.PrintData's quality
    setting.

    This is a workaround for WX ignoring the quality setting and defaulting to
    72 DPI.  Unfortunately wx.Printout.GetDC() returns a wx.DC object instead
    of the actual class, so it's impossible to set the resolution on the DC
    itself.

    Even more unforuntately, printing with libgnomeprint appears to always be
    stuck at 72 DPI.
    """
    if not callable(getattr(wx, 'PostScriptDC_SetResolution', None)):
        return

    quality = printData.GetQuality()
    if quality > 0:
        dpi = quality
    elif quality == wx.PRINT_QUALITY_HIGH:
        dpi = PS_DPI_HIGH_QUALITY
    elif quality == wx.PRINT_QUALITY_MEDIUM:
        dpi = PS_DPI_MEDIUM_QUALITY
    elif quality == wx.PRINT_QUALITY_LOW:
        dpi = PS_DPI_LOW_QUALITY
    elif quality == wx.PRINT_QUALITY_DRAFT:
        dpi = PS_DPI_DRAFT_QUALITY
    else:
        dpi = PS_DPI_HIGH_QUALITY
 
    wx.PostScriptDC_SetResolution(dpi)


class FigurePrinter:
    """
    Provides a simplified interface to the wxPython printing framework that's
    designed for printing matplotlib figures.
    """

    def __init__(self, view, printData=None):
        """
        Create a new C{FigurePrinter} associated with the wxPython widget
        C{view}.  The keyword argument C{printData} supplies a C{wx.PrintData}
        object containing the default printer settings.
        """
        self.view = view

        if printData is None:
            printData = wx.PrintData()

        self.setPrintData(printData)

    def getPrintData(self):
        """
        Return the current printer settings in their C{wx.PrintData} object.
        """
        return self.pData

    def setPrintData(self, printData):
        """
        Use the printer settings in C{printData}.
        """
        self.pData = printData
        update_postscript_resolution(self.pData)

    def pageSetup(self):
        dlg = wx.PrintDialog(self.view)
        pdData = dlg.GetPrintDialogData()
        pdData.SetPrintData(self.pData)

        if dlg.ShowModal() == wx.ID_OK:
            self.setPrintData(pdData.GetPrintData())
        dlg.Destroy()

    def previewFigure(self, figure, title=None):
        """
        Open a "Print Preview" window for the matplotlib chart C{figure}.  The
        keyword argument C{title} provides the printing framework with a title
        for the print job.
        """
        topwin = toplevel_parent_of_window(self.view)
        fpo = FigurePrintout(figure, title)
        fpo4p = FigurePrintout(figure, title)
        preview = wx.PrintPreview(fpo, fpo4p, self.pData)
        frame = wx.PreviewFrame(preview, topwin, 'Print Preview')
        if self.pData.GetOrientation() == wx.PORTRAIT:
            frame.SetSize(wx.Size(450, 625))
        else:
            frame.SetSize(wx.Size(600, 500))
        frame.Initialize()
        frame.Show(True)

    def printFigure(self, figure, title=None):
        """
        Open a "Print" dialog to print the matplotlib chart C{figure}.  The
        keyword argument C{title} provides the printing framework with a title
        for the print job.
        """
        pdData = wx.PrintDialogData()
        pdData.SetPrintData(self.pData)
        printer = wx.Printer(pdData)
        fpo = FigurePrintout(figure, title)
        if printer.Print(self.view, fpo, True):
            self.setPrintData(pdData.GetPrintData())


class FigurePrintout(wx.Printout):
    """
    Render a matplotlib C{Figure} to a page or file using wxPython's printing
    framework.
    """

    ASPECT_RECTANGULAR = 1
    ASPECT_SQUARE = 2

    def __init__(self, figure, title=None, size=None, aspectRatio=None):
        """
        Create a printout for the matplotlib chart C{figure}.  The
        keyword argument C{title} provides the printing framework with a title
        for the print job.  The keyword argument C{size} specifies how to scale
        the figure, from 1 to 100 percent.  The keyword argument C{aspectRatio}
        determines whether the printed figure will be rectangular or square.
        """
        self.figure = figure

        figTitle = figure.gca().title.get_text()
        if not figTitle:
            figTitle = title or 'Matplotlib Figure'

        if size is None:
            size = 100
        elif size < 1 or size > 100:
            raise ValueError('invalid figure size')
        self.size = size

        if aspectRatio is None:
            aspectRatio = self.ASPECT_RECTANGULAR
        elif (aspectRatio != self.ASPECT_RECTANGULAR
        and aspectRatio != self.ASPECT_SQUARE):
            raise ValueError('invalid aspect ratio')
        self.aspectRatio = aspectRatio

        wx.Printout.__init__(self, figTitle)

    def GetPageInfo(self):
        """
        Overrides wx.Printout.GetPageInfo() to provide the printing framework
        with the number of pages in this print job.
        """
        return (1, 1, 1, 1)

    def HasPage(self, pageNumber):
        """
        Overrides wx.Printout.GetPageInfo() to tell the printing framework
        of the specified page exists.
        """
        return pageNumber == 1

    def OnPrintPage(self, pageNumber):
        """
        Overrides wx.Printout.OnPrintPage() to render the matplotlib figure to
        a printing device context.
        """
        # % of printable area to use
        imgPercent = max(1, min(100, self.size)) / 100.0

        # ratio of the figure's width to its height
        if self.aspectRatio == self.ASPECT_RECTANGULAR:
            aspectRatio = 1.61803399
        elif self.aspectRatio == self.ASPECT_SQUARE:
            aspectRatio = 1.0
        else:
            raise ValueError('invalid aspect ratio')

        # Device context to draw the page
        dc = self.GetDC()

        # PPI_P: Pixels Per Inch of the Printer
        wPPI_P, hPPI_P = [float(x) for x in self.GetPPIPrinter()]
        PPI_P = (wPPI_P + hPPI_P)/2.0

        # PPI: Pixels Per Inch of the DC
        if self.IsPreview():
            wPPI, hPPI = [float(x) for x in self.GetPPIScreen()]
        else:
            wPPI, hPPI = wPPI_P, hPPI_P
        PPI = (wPPI + hPPI)/2.0

        # Pg_Px: Size of the page (pixels)
        wPg_Px,  hPg_Px  = [float(x) for x in self.GetPageSizePixels()]

        # Dev_Px: Size of the DC (pixels)
        wDev_Px, hDev_Px = [float(x) for x in self.GetDC().GetSize()]

        # Pg: Size of the page (inches)
        wPg = wPg_Px / PPI_P
        hPg = hPg_Px / PPI_P

        # minimum margins (inches)
        wM = 0.75
        hM = 0.75

        # Area: printable area within the margins (inches)
        wArea = wPg - 2*wM
        hArea = hPg - 2*hM

        # Fig: printing size of the figure
        # hFig is at a maximum when wFig == wArea
        max_hFig = wArea / aspectRatio
        hFig = min(imgPercent * hArea, max_hFig)
        wFig = aspectRatio * hFig

        # scale factor = device size / page size (equals 1.0 for real printing)
        S = ((wDev_Px/PPI)/wPg + (hDev_Px/PPI)/hPg)/2.0

        # Fig_S: scaled printing size of the figure (inches)
        # M_S: scaled minimum margins (inches)
        wFig_S = S * wFig
        hFig_S = S * hFig
        wM_S = S * wM
        hM_S = S * hM

        # Fig_Dx: scaled printing size of the figure (device pixels)
        # M_Dx: scaled minimum margins (device pixels)
        wFig_Dx = int(S * PPI * wFig)
        hFig_Dx = int(S * PPI * hFig)
        wM_Dx = int(S * PPI * wM)
        hM_Dx = int(S * PPI * hM)

        image = self.render_figure_as_image(wFig, hFig, PPI)

        if self.IsPreview():
            image = image.Scale(wFig_Dx, hFig_Dx)
        self.GetDC().DrawBitmap(image.ConvertToBitmap(), wM_Dx, hM_Dx, False)

        return True

    def render_figure_as_image(self, wFig, hFig, dpi):
        """
        Renders a matplotlib figure using the Agg backend and stores the result
        in a C{wx.Image}.  The arguments C{wFig} and {hFig} are the width and
        height of the figure, and C{dpi} is the dots-per-inch to render at.
        """
        figure = self.figure

        old_dpi = figure.dpi
        figure.dpi = dpi
        old_width = figure.get_figwidth()
        figure.set_figwidth(wFig)
        old_height = figure.get_figheight()
        figure.set_figheight(hFig)
        old_frameon = figure.frameon
        figure.frameon = False

        wFig_Px = int(figure.bbox.width)
        hFig_Px = int(figure.bbox.height)

        agg = RendererAgg(wFig_Px, hFig_Px, dpi)
        figure.draw(agg)

        figure.dpi = old_dpi
        figure.set_figwidth(old_width)
        figure.set_figheight(old_height)
        figure.frameon = old_frameon

        image = wx.EmptyImage(wFig_Px, hFig_Px)
        image.SetData(agg.tostring_rgb())
        return image


#
# wxPython event interface for the PlotPanel and PlotFrame
#

EVT_POINT_ID = wx.NewId()


def EVT_POINT(win, id, func):
    """
    Register to receive wxPython C{PointEvent}s from a C{PlotPanel} or
    C{PlotFrame}.
    """
    win.Connect(id, -1, EVT_POINT_ID, func)


class PointEvent(wx.PyCommandEvent):
    """
    wxPython event emitted when a left-click-release occurs in a matplotlib
    axes of a window without an area selection.

    @cvar axes: matplotlib C{Axes} which was left-clicked
    @cvar x: matplotlib X coordinate
    @cvar y: matplotlib Y coordinate
    @cvar xdata: axes X coordinate
    @cvar ydata: axes Y coordinate
    """
    def __init__(self, id, axes, x, y):
        """
        Create a new C{PointEvent} for the matplotlib coordinates C{(x, y)} of
        an C{axes}.
        """
        wx.PyCommandEvent.__init__(self, EVT_POINT_ID, id)
        self.axes = axes
        self.x = x
        self.y = y
        self.xdata, self.ydata = invert_point(x, y, axes.transData)

    def Clone(self):
        return PointEvent(self.GetId(), self.axes, self.x, self.y)


EVT_SELECTION_ID = wx.NewId()


def EVT_SELECTION(win, id, func):
    """
    Register to receive wxPython C{SelectionEvent}s from a C{PlotPanel} or
    C{PlotFrame}.
    """
    win.Connect(id, -1, EVT_SELECTION_ID, func)


class SelectionEvent(wx.PyCommandEvent):
    """
    wxPython event emitted when an area selection occurs in a matplotlib axes
    of a window for which zooming has been disabled.  The selection is
    described by a rectangle from C{(x1, y1)} to C{(x2, y2)}, of which only
    one point is required to be inside the axes.

    @cvar axes: matplotlib C{Axes} which was left-clicked
    @cvar x1: matplotlib x1 coordinate
    @cvar y1: matplotlib y1 coordinate
    @cvar x2: matplotlib x2 coordinate
    @cvar y2: matplotlib y2 coordinate
    @cvar x1data: axes x1 coordinate
    @cvar y1data: axes y1 coordinate
    @cvar x2data: axes x2 coordinate
    @cvar y2data: axes y2 coordinate
    """
    def __init__(self, id, axes, x1, y1, x2, y2):
        """
        Create a new C{SelectionEvent} for the area described by the rectangle
        from C{(x1, y1)} to C{(x2, y2)} in an C{axes}.
        """
        wx.PyCommandEvent.__init__(self, EVT_SELECTION_ID, id)
        self.axes = axes
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.x1data, self.y1data = invert_point(x1, y1, axes.transData)
        self.x2data, self.y2data = invert_point(x2, y2, axes.transData)

    def Clone(self):
        return SelectionEvent(self.GetId(), self.axes, self.x1, self.y1,
            self.x2, self.y2)


#
# Matplotlib canvas in a wxPython window
#

class PlotPanel(FigureCanvasWxAgg):
    """
    A matplotlib canvas suitable for embedding in wxPython applications.
    """
    def __init__(self, parent, id, size=(6.0, 3.70), dpi=96, cursor=True,
     location=True, crosshairs=True, selection=True, zoom=True,
     autoscaleUnzoom=True):
        """
        Creates a new PlotPanel window that is the child of the wxPython window
        C{parent} with the wxPython identifier C{id}.

        The keyword arguments C{size} and {dpi} are used to create the
        matplotlib C{Figure} associated with this canvas.  C{size} is the
        desired width and height of the figure, in inches, as the 2-tuple
        C{(width, height)}.  C{dpi} is the dots-per-inch of the figure.

        The keyword arguments C{cursor}, C{location}, C{crosshairs},
        C{selection}, C{zoom}, and C{autoscaleUnzoom} enable or disable various
        user interaction features that are descibed in their associated
        C{set()} methods.
        """
        FigureCanvasWxAgg.__init__(self, parent, id, Figure(size, dpi))

        self.insideOnPaint = False
        self.cursor = CursorChanger(self, cursor)
        self.location = LocationPainter(self, location)
        self.crosshairs = CrosshairPainter(self, crosshairs)
        self.rubberband = RubberbandPainter(self, selection)
        rightClickUnzoom = True # for now this is default behavior
        self.director = PlotPanelDirector(self, zoom, selection,
            rightClickUnzoom, autoscaleUnzoom)

        self.figure.set_edgecolor('black')
        self.figure.set_facecolor('white')
        self.SetBackgroundColour(wx.WHITE)

        # find the toplevel parent window and register an activation event
        # handler that is keyed to the id of this PlotPanel
        topwin = toplevel_parent_of_window(self)
        topwin.Connect(-1, self.GetId(), wx.wxEVT_ACTIVATE, self.OnActivate)

        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_WINDOW_DESTROY(self, self.OnDestroy)

    def OnActivate(self, evt):
        """
        Handles the wxPython window activation event.
        """
        if not evt.GetActive():
            self.cursor.setNormal()
            self.location.clear()
            self.crosshairs.clear()
            self.rubberband.clear()
        evt.Skip()

    def OnEraseBackground(self, evt):
        """
        Overrides the wxPython backround repainting event to reduce flicker.
        """
        pass

    def OnDestroy(self, evt):
        """
        Handles the wxPython window destruction event.
        """
        if self.GetId() == evt.GetEventObject().GetId():
            # unregister the activation event handler for this PlotPanel
            topwin = toplevel_parent_of_window(self)
            topwin.Disconnect(-1, self.GetId(), wx.wxEVT_ACTIVATE)

    def _onPaint(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} paint event to redraw the
        crosshairs, etc.
        """
        # avoid wxPyDeadObject errors
        if not isinstance(self, FigureCanvasWxAgg):
            return

        self.insideOnPaint = True
        FigureCanvasWxAgg._onPaint(self, evt)
        self.insideOnPaint = False

        dc = wx.PaintDC(self)
        self.location.redraw(dc)
        self.crosshairs.redraw(dc)
        self.rubberband.redraw(dc)

    def get_figure(self):
        """
        Returns the figure associated with this canvas.
        """
        return self.figure

    def set_cursor(self, state):
        """
        Enable or disable the changing mouse cursor.  When enabled, the cursor
        changes from the normal arrow to a square cross when the mouse enters a
        matplotlib axes on this canvas.
        """
        self.cursor.setEnabled(state)

    def set_location(self, state):
        """
        Enable or disable the display of the matplotlib axes coordinates of the
        mouse in the lower left corner of the canvas.
        """
        self.location.setEnabled(state)

    def set_crosshairs(self, state):
        """
        Enable or disable drawing crosshairs through the mouse cursor when it
        is inside a matplotlib axes.
        """
        self.crosshairs.setEnabled(state)

    def set_selection(self, state):
        """
        Enable or disable area selections, where user selects a rectangular
        area of the canvas by left-clicking and dragging the mouse.
        """
        self.rubberband.setEnabled(state)
        self.director.setSelection(state)

    def set_zoom(self, state):
        """
        Enable or disable zooming in when the user makes an area selection and
        zooming out again when the user right-clicks.
        """
        self.director.setZoomEnabled(state)

    def set_autoscale_unzoom(self, state):
        """
        Enable or disable automatic view rescaling when the user zooms out to
        the initial figure.
        """
        self.director.setAutoscaleUnzoom(state)

    def zoomed(self, axes):
        """
        Returns a boolean indicating whether or not the C{axes} is zoomed in.
        """
        return self.director.zoomed(axes)

    def draw(self, **kwds):
        """
        Draw the associated C{Figure} onto the screen.
        """
        # don't redraw if the left mouse button is down and avoid
        # wxPyDeadObject errors
        if (not self.director.canDraw()
        or  not isinstance(self, FigureCanvasWxAgg)):
            return

        if MATPLOTLIB_0_98_3:
            FigureCanvasWxAgg.draw(self, kwds.get('drawDC', None))
        else:
            FigureCanvasWxAgg.draw(self, kwds.get('repaint', True))

        # Don't redraw the decorations when called by _onPaint()
        if not self.insideOnPaint:
            self.location.redraw()
            self.crosshairs.redraw()
            self.rubberband.redraw()

    def notify_point(self, axes, x, y):
        """
        Called by the associated C{PlotPanelDirector} to emit a C{PointEvent}.
        """
        wx.PostEvent(self, PointEvent(self.GetId(), axes, x, y))

    def notify_selection(self, axes, x1, y1, x2, y2):
        """
        Called by the associated C{PlotPanelDirector} to emit a
        C{SelectionEvent}.
        """
        wx.PostEvent(self, SelectionEvent(self.GetId(), axes, x1, y1, x2, y2))

    def _get_canvas_xy(self, evt):
        """
        Returns the X and Y coordinates of a wxPython event object converted to
        matplotlib canavas coordinates.
        """
        return evt.GetX(), int(self.figure.bbox.height - evt.GetY())

    def _onKeyDown(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} key-press event handler, dispatching
        the event to the associated C{PlotPanelDirector}.
        """
        self.director.keyDown(evt)

    def _onKeyUp(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} key-release event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        self.director.keyUp(evt)
 
    def _onLeftButtonDown(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} left-click event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        x, y = self._get_canvas_xy(evt)
        self.director.leftButtonDown(evt, x, y)

    def _onLeftButtonUp(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} left-click-release event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        x, y = self._get_canvas_xy(evt)
        self.director.leftButtonUp(evt, x, y)

    def _onRightButtonDown(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} right-click event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        x, y = self._get_canvas_xy(evt)
        self.director.rightButtonDown(evt, x, y)

    def _onRightButtonUp(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} right-click-release event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        x, y = self._get_canvas_xy(evt)
        self.director.rightButtonUp(evt, x, y)

    def _onMotion(self, evt):
        """
        Overrides the C{FigureCanvasWxAgg} mouse motion event handler,
        dispatching the event to the associated C{PlotPanelDirector}.
        """
        x, y = self._get_canvas_xy(evt)
        self.director.mouseMotion(evt, x, y)


#
# Matplotlib canvas in a top-level wxPython window
#

class PlotFrame(wx.Frame):
    """
    A matplotlib canvas embedded in a wxPython top-level window.

    @cvar ABOUT_TITLE: Title of the "About" dialog.
    @cvar ABOUT_MESSAGE: Contents of the "About" dialog.
    """

    ABOUT_TITLE = 'About wxmpl.PlotFrame'
    ABOUT_MESSAGE = ('wxmpl.PlotFrame %s\n' %  __version__
        + 'Written by Ken McIvor <mcivor@iit.edu>\n'
        + 'Copyright 2005-2009 Illinois Institute of Technology')

    def __init__(self, parent, id, title, size=(6.0, 3.7), dpi=96, cursor=True,
     location=True, crosshairs=True, selection=True, zoom=True,
     autoscaleUnzoom=True, **kwds):
        """
        Creates a new PlotFrame top-level window that is the child of the
        wxPython window C{parent} with the wxPython identifier C{id} and the
        title of C{title}.

        All of the named keyword arguments to this constructor have the same
        meaning as those arguments to the constructor of C{PlotPanel}.

        Any additional keyword arguments are passed to the constructor of
        C{wx.Frame}.
        """
        wx.Frame.__init__(self, parent, id, title, **kwds)
        self.panel = PlotPanel(self, -1, size, dpi, cursor, location,
            crosshairs, selection, zoom)

        pData = wx.PrintData()
        pData.SetPaperId(wx.PAPER_LETTER)
        if callable(getattr(pData, 'SetPrinterCommand', None)):
            pData.SetPrinterCommand(POSTSCRIPT_PRINTING_COMMAND)
        self.printer = FigurePrinter(self, pData)

        self.create_menus()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer)
        self.Fit()

    def create_menus(self):
        mainMenu = wx.MenuBar()
        menu = wx.Menu()

        id = wx.NewId()
        menu.Append(id, '&Save As...\tCtrl+S',
            'Save a copy of the current plot')
        wx.EVT_MENU(self, id, self.OnMenuFileSave)

        menu.AppendSeparator()

        if wx.Platform != '__WXMAC__':
            id = wx.NewId()
            menu.Append(id, 'Page Set&up...',
                'Set the size and margins of the printed figure')
            wx.EVT_MENU(self, id, self.OnMenuFilePageSetup)

            id = wx.NewId()
            menu.Append(id, 'Print Pre&view...',
                'Preview the print version of the current plot')
            wx.EVT_MENU(self, id, self.OnMenuFilePrintPreview)

        id = wx.NewId()
        menu.Append(id, '&Print...\tCtrl+P', 'Print the current plot')
        wx.EVT_MENU(self, id, self.OnMenuFilePrint)

        menu.AppendSeparator()

        id = wx.NewId()
        menu.Append(id, '&Close Window\tCtrl+W',
            'Close the current plot window')
        wx.EVT_MENU(self, id, self.OnMenuFileClose)

        mainMenu.Append(menu, '&File')
        menu = wx.Menu()

        id = wx.NewId()
        menu.Append(id, '&About...', 'Display version information')
        wx.EVT_MENU(self, id, self.OnMenuHelpAbout)

        mainMenu.Append(menu, '&Help')
        self.SetMenuBar(mainMenu)

    def OnMenuFileSave(self, evt):
        """
        Handles File->Save menu events.
        """
        fileName = wx.FileSelector('Save Plot', default_extension='png',
            wildcard=('Portable Network Graphics (*.png)|*.png|'
                + 'Encapsulated Postscript (*.eps)|*.eps|All files (*.*)|*.*'),
            parent=self, flags=wx.SAVE|wx.OVERWRITE_PROMPT)

        if not fileName:
            return

        path, ext = os.path.splitext(fileName)
        ext = ext[1:].lower()

        if ext != 'png' and ext != 'eps':
            error_message = (
                'Only the PNG and EPS image formats are supported.\n'
                'A file extension of `png\' or `eps\' must be used.')
            wx.MessageBox(error_message, 'Error - plotit',
                parent=self, style=wx.OK|wx.ICON_ERROR)
            return

        try:
            self.panel.print_figure(fileName)
        except IOError, e:
            if e.strerror:
                err = e.strerror
            else:
                err = e

            wx.MessageBox('Could not save file: %s' % err, 'Error - plotit',
                parent=self, style=wx.OK|wx.ICON_ERROR)

    def OnMenuFilePageSetup(self, evt):
        """
        Handles File->Page Setup menu events
        """
        self.printer.pageSetup()

    def OnMenuFilePrintPreview(self, evt):
        """
        Handles File->Print Preview menu events
        """
        self.printer.previewFigure(self.get_figure())

    def OnMenuFilePrint(self, evt):
        """
        Handles File->Print menu events
        """
        self.printer.printFigure(self.get_figure())

    def OnMenuFileClose(self, evt):
        """
        Handles File->Close menu events.
        """
        self.Close()

    def OnMenuHelpAbout(self, evt):
        """
        Handles Help->About menu events.
        """
        wx.MessageBox(self.ABOUT_MESSAGE, self.ABOUT_TITLE, parent=self,
            style=wx.OK)

    def get_figure(self):
        """
        Returns the figure associated with this canvas.
        """
        return self.panel.figure

    def set_cursor(self, state):
        """
        Enable or disable the changing mouse cursor.  When enabled, the cursor
        changes from the normal arrow to a square cross when the mouse enters a
        matplotlib axes on this canvas.
        """
        self.panel.set_cursor(state)

    def set_location(self, state):
        """
        Enable or disable the display of the matplotlib axes coordinates of the
        mouse in the lower left corner of the canvas.
        """
        self.panel.set_location(state)

    def set_crosshairs(self, state):
        """
        Enable or disable drawing crosshairs through the mouse cursor when it
        is inside a matplotlib axes.
        """
        self.panel.set_crosshairs(state)

    def set_selection(self, state):
        """
        Enable or disable area selections, where user selects a rectangular
        area of the canvas by left-clicking and dragging the mouse.
        """
        self.panel.set_selection(state)

    def set_zoom(self, state):
        """
        Enable or disable zooming in when the user makes an area selection and
        zooming out again when the user right-clicks.
        """
        self.panel.set_zoom(state)

    def set_autoscale_unzoom(self, state):
        """
        Enable or disable automatic view rescaling when the user zooms out to
        the initial figure.
        """
        self.panel.set_autoscale_unzoom(state)

    def draw(self):
        """
        Draw the associated C{Figure} onto the screen.
        """
        self.panel.draw()


#
# wxApp providing a matplotlib canvas in a top-level wxPython window
#

class PlotApp(wx.App):
    """
    A wxApp that provides a matplotlib canvas embedded in a wxPython top-level
    window, encapsulating wxPython's nuts and bolts.

    @cvar ABOUT_TITLE: Title of the "About" dialog.
    @cvar ABOUT_MESSAGE: Contents of the "About" dialog.
    """

    ABOUT_TITLE = None
    ABOUT_MESSAGE = None

    def __init__(self, title="WxMpl", size=(6.0, 3.7), dpi=96, cursor=True,
     location=True, crosshairs=True, selection=True, zoom=True, **kwds):
        """
        Creates a new PlotApp, which creates a PlotFrame top-level window.

        The keyword argument C{title} specifies the title of this top-level
        window.

        All of other the named keyword arguments to this constructor have the
        same meaning as those arguments to the constructor of C{PlotPanel}.

        Any additional keyword arguments are passed to the constructor of
        C{wx.App}.
        """
        self.title = title
        self.size = size
        self.dpi = dpi
        self.cursor = cursor
        self.location = location
        self.crosshairs = crosshairs
        self.selection = selection
        self.zoom = zoom
        wx.App.__init__(self, **kwds)

    def OnInit(self):
        self.frame = panel = PlotFrame(None, -1, self.title, self.size,
            self.dpi, self.cursor, self.location, self.crosshairs,
            self.selection, self.zoom)

        if self.ABOUT_TITLE is not None:
            panel.ABOUT_TITLE = self.ABOUT_TITLE

        if self.ABOUT_MESSAGE is not None:
            panel.ABOUT_MESSAGE = self.ABOUT_MESSAGE

        panel.Show(True)
        return True

    def get_figure(self):
        """
        Returns the figure associated with this canvas.
        """
        return self.frame.get_figure()

    def set_cursor(self, state):
        """
        Enable or disable the changing mouse cursor.  When enabled, the cursor
        changes from the normal arrow to a square cross when the mouse enters a
        matplotlib axes on this canvas.
        """
        self.frame.set_cursor(state)

    def set_location(self, state):
        """
        Enable or disable the display of the matplotlib axes coordinates of the
        mouse in the lower left corner of the canvas.
        """
        self.frame.set_location(state)

    def set_crosshairs(self, state):
        """
        Enable or disable drawing crosshairs through the mouse cursor when it
        is inside a matplotlib axes.
        """
        self.frame.set_crosshairs(state)

    def set_selection(self, state):
        """
        Enable or disable area selections, where user selects a rectangular
        area of the canvas by left-clicking and dragging the mouse.
        """
        self.frame.set_selection(state)

    def set_zoom(self, state):
        """
        Enable or disable zooming in when the user makes an area selection and
        zooming out again when the user right-clicks.
        """
        self.frame.set_zoom(state)

    def draw(self):
        """
        Draw the associated C{Figure} onto the screen.
        """
        self.frame.draw()


#
# Automatically resizing vectors and matrices
#

class VectorBuffer:
    """
    Manages a Numerical Python vector, automatically growing it as necessary to
    accomodate new entries.
    """
    def __init__(self):
        self.data = Numerix.zeros((16,), Numerix.Float)
        self.nextRow = 0

    def clear(self):
        """
        Zero and reset this buffer without releasing the underlying array.
        """
        self.data[:] = 0.0
        self.nextRow = 0

    def reset(self):
        """
        Zero and reset this buffer, releasing the underlying array.
        """
        self.data = Numerix.zeros((16,), Numerix.Float)
        self.nextRow = 0

    def append(self, point):
        """
        Append a new entry to the end of this buffer's vector.
        """
        nextRow = self.nextRow
        data = self.data

        resize = False
        if nextRow == data.shape[0]:
            nR = int(Numerix.ceil(self.data.shape[0]*1.5))
            resize = True

        if resize:
            self.data = Numerix.zeros((nR,), Numerix.Float)
            self.data[0:data.shape[0]] = data

        self.data[nextRow] = point
        self.nextRow += 1

    def getData(self):
        """
        Returns the current vector or C{None} if the buffer contains no data.
        """
        if self.nextRow == 0:
            return None
        else:
            return self.data[0:self.nextRow]


class MatrixBuffer:
    """
    Manages a Numerical Python matrix, automatically growing it as necessary to
    accomodate new rows of entries.
    """
    def __init__(self):
        self.data = Numerix.zeros((16, 1), Numerix.Float)
        self.nextRow = 0

    def clear(self):
        """
        Zero and reset this buffer without releasing the underlying array.
        """
        self.data[:, :] = 0.0
        self.nextRow = 0

    def reset(self):
        """
        Zero and reset this buffer, releasing the underlying array.
        """
        self.data = Numerix.zeros((16, 1), Numerix.Float)
        self.nextRow = 0

    def append(self, row):
        """
        Append a new row of entries to the end of this buffer's matrix.
        """
        row = Numerix.asarray(row, Numerix.Float)
        nextRow = self.nextRow
        data = self.data
        nPts = row.shape[0]

        if nPts == 0:
            return

        resize = True
        if nextRow == data.shape[0]:
            nC = data.shape[1]
            nR = int(Numerix.ceil(self.data.shape[0]*1.5))
            if nC < nPts:
                nC = nPts
        elif data.shape[1] < nPts:
            nR = data.shape[0]
            nC = nPts
        else:
            resize = False

        if resize:
            self.data = Numerix.zeros((nR, nC), Numerix.Float)
            rowEnd, colEnd = data.shape
            self.data[0:rowEnd, 0:colEnd] = data

        self.data[nextRow, 0:nPts] = row
        self.nextRow += 1

    def getData(self):
        """
        Returns the current matrix or C{None} if the buffer contains no data.
        """
        if self.nextRow == 0:
            return None
        else:
            return self.data[0:self.nextRow, :]


#
# Utility functions used by the StripCharter
#

def make_delta_bbox(X1, Y1, X2, Y2):
    """
    Returns a C{Bbox} describing the range of difference between two sets of X
    and Y coordinates.
    """
    return make_bbox(get_delta(X1, X2), get_delta(Y1, Y2))


def get_delta(X1, X2):
    """
    Returns the vector of contiguous, different points between two vectors.
    """
    n1 = X1.shape[0]
    n2 = X2.shape[0]

    if n1 < n2:
        return X2[n1:]
    elif n1 == n2:
        # shape is no longer a reliable indicator of change, so assume things
        # are different
        return X2
    else:
        return X2


def make_bbox(X, Y):
    """
    Returns a C{Bbox} that contains the supplied sets of X and Y coordinates.
    """
    if X is None or X.shape[0] == 0:
        x1 = x2 = 0.0
    else:
        x1 = min(X)
        x2 = max(X)

    if Y is None or Y.shape[0] == 0:
        y1 = y2 = 0.0
    else:
        y1 = min(Y)
        y2 = max(Y)

    return Bbox.from_extents(x1, y1, x2, y2)


#
# Strip-charts lines using a matplotlib axes
#

class StripCharter:
    """
    Plots and updates lines on a matplotlib C{Axes}.
    """
    def __init__(self, axes):
        """
        Create a new C{StripCharter} associated with a matplotlib C{axes}.
        """
        self.axes = axes
        self.channels = []
        self.lines = {}

    def setChannels(self, channels):
        """
        Specify the data-providers of the lines to be plotted and updated.
        """
        self.lines = None
        self.channels = channels[:]

        # minimal Axes.cla()
        self.axes.legend_ = None
        self.axes.lines = []

    def update(self):
        """
        Redraw the associated axes with updated lines if any of the channels'
        data has changed.
        """
        axes = self.axes
        figureCanvas = axes.figure.canvas

        zoomed = figureCanvas.zoomed(axes)

        redraw = False
        if self.lines is None:
            self._create_plot()
            redraw = True
        else:
            for channel in self.channels:
                redraw = self._update_channel(channel, zoomed) or redraw

        if redraw:
            if not zoomed:
                axes.autoscale_view()
            figureCanvas.draw()

    def _create_plot(self):
        """
        Initially plot the lines corresponding to the data-providers.
        """
        self.lines = {}
        axes = self.axes
        styleGen = _process_plot_var_args(axes)

        for channel in self.channels:
            self._plot_channel(channel, styleGen)

        if self.channels:
            lines  = [self.lines[x] for x in self.channels]
            labels = [x.get_label() for x in lines]
            self.axes.legend(lines, labels, numpoints=2,
                prop=FontProperties(size='x-small'))

    def _plot_channel(self, channel, styleGen):
        """
        Initially plot a line corresponding to one of the data-providers.
        """
        empty = False
        x = channel.getX()
        y = channel.getY()
        if x is None or y is None:
            x = y = []
            empty = True

        line = styleGen(x, y).next()
        line._wxmpl_empty_line = empty

        if channel.getColor() is not None:
            line.set_color(channel.getColor())
        if channel.getStyle() is not None:
            line.set_linestyle(channel.getStyle())
        if channel.getMarker() is not None:
            line.set_marker(channel.getMarker())
            line.set_markeredgecolor(line.get_color())
            line.set_markerfacecolor(line.get_color())

        line.set_label(channel.getLabel())
        self.lines[channel] = line
        if not empty:
            self.axes.add_line(line)

    def _update_channel(self, channel, zoomed):
        """
        Replot a line corresponding to one of the data-providers if the data
        has changed.
        """
        if channel.hasChanged():
            channel.setChanged(False)
        else:
            return False

        axes = self.axes
        line = self.lines[channel]
        newX = channel.getX()
        newY = channel.getY()

        if newX is None or newY is None:
            return False

        oldX = line._x
        oldY = line._y

        x, y = newX, newY
        line.set_data(x, y)

        if line._wxmpl_empty_line:
            axes.add_line(line)
            line._wxmpl_empty_line = False
        else:
            if line.get_transform() != axes.transData:
                xys = axes._get_verts_in_data_coords(
                    line.get_transform(), zip(x, y))
            else:
                xys = Numerix.zeros((x.shape[0], 2), Numerix.Float)
                xys[:,0] = x
                xys[:,1] = y
            axes.update_datalim(xys)

        if zoomed:
            return axes.viewLim.overlaps(
                make_delta_bbox(oldX, oldY, newX, newY))
        else:
            return True


#
# Data-providing interface to the StripCharter
#

class Channel:
    """
    Provides data for a C{StripCharter} to plot.  Subclasses of C{Channel}
    override the template methods C{getX()} and C{getY()} to provide plot data
    and call C{setChanged(True)} when that data has changed.
    """
    def __init__(self, name, color=None, style=None, marker=None):
        """
        Creates a new C{Channel} with the matplotlib label C{name}.  The
        keyword arguments specify the strings for the line color, style, and
        marker to use when the line is plotted.
        """
        self.name = name
        self.color = color
        self.style = style
        self.marker = marker
        self.changed = False

    def getLabel(self):
        """
        Returns the matplotlib label for this channel of data.
        """
        return self.name

    def getColor(self):
        """
        Returns the line color string to use when the line is plotted, or
        C{None} to use an automatically generated color.
        """
        return self.color

    def getStyle(self):
        """
        Returns the line style string to use when the line is plotted, or
        C{None} to use the default line style.
        """
        return self.style

    def getMarker(self):
        """
        Returns the line marker string to use when the line is plotted, or
        C{None} to use the default line marker.
        """
        return self.marker

    def hasChanged(self):
        """
        Returns a boolean indicating if the line data has changed.
        """
        return self.changed

    def setChanged(self, changed):
        """
        Sets the change indicator to the boolean value C{changed}.

        @note: C{StripCharter} instances call this method after detecting a
        change, so a C{Channel} cannot be shared among multiple charts.
        """
        self.changed = changed

    def getX(self):
        """
        Template method that returns the vector of X axis data or C{None} if
        there is no data available.
        """
        return None

    def getY(self):
        """
        Template method that returns the vector of Y axis data or C{None} if
        there is no data available.
        """
        return None


########NEW FILE########
