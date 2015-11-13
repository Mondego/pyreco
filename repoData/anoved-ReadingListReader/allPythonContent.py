__FILENAME__ = readinglist2csv
#!/usr/bin/env python
"""
Dumps the entire Safari Reading List into a CSV file for use in other ways. Kind of a master reset button."""

from readinglistlib import ReadingListReader
import csv


r = ReadingListReader()
articles = r.read()

with open('reading_list_dump.csv', 'wb') as csvfile:
    cwriter = csv.writer(csvfile, delimiter=" ", quotechar="|", quoting=csv.QUOTE_MINIMAL)
    fieldnames = ['title', 'url', 'added', 'viewed']
    hwriter = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect='excel')
    hwriter.writeheader()
    for a in articles:
        try:
            w = {
                'title': a['title'],
                'url': a['url'],
                'added': a['added'],
                'viewed': a['viewed']
            }
            hwriter.writerow(w)
        except UnicodeEncodeError:
            print "Couldnt save %s" % a['url']

########NEW FILE########
__FILENAME__ = readinglist2html
#!/usr/bin/python

from readinglistlib import ReadingListReader

rlr = ReadingListReader()
bookmarks = rlr.read(ascending=False)

print '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Reading List</title></head><body><h1>Reading List</h1><ul>'

for bookmark in bookmarks:
	print '<li><p><a href="%(url)s">%(title)s</a><br />%(url)s</p><blockquote>%(preview)s</blockquote></li>' % {'url': bookmark['url'].encode('utf-8'), 'title': bookmark['title'].encode('utf-8'), 'preview': bookmark['preview'].encode('utf-8')}

print '</ul></body></html>'

########NEW FILE########
__FILENAME__ = readinglist2instapaper
#!/usr/bin/env python

# Requires https://github.com/mrtazz/InstapaperLibrary
from instapaperlib import Instapaper

from readinglistlib import ReadingListReader

# Standard library modules
import argparse
import sys
import os
import re

# Configure and consume command line arguments.
ap = argparse.ArgumentParser(description='This script adds your Safari Reading List articles to Instapaper.')
ap.add_argument('-u', '--username', action='store', default='', help='Instapaper username or email.')
ap.add_argument('-p', '--password', action='store', default='', help='Instapaper password (if any).')
ap.add_argument('-v', '--verbose', action='store_true', help='Print article URLs as they are added.')
args = ap.parse_args()

if '' == args.username:
	# For compatibility with instapaperlib's instapaper.py tool,
	# attempt to read Instapaper username and password from ~/.instapaperrc.
	# (Login pattern modified to accept blank passwords.)
	login = re.compile("(.+?):(.*)")
	try:
		config = open(os.path.expanduser('~') + '/.instapaperrc')
		for line in config:
			matches = login.match(line)
			if matches:
				args.username = matches.group(1).strip()
				args.password = matches.group(2).strip()
				break
		if '' == args.username:
			print >> sys.stderr, 'No username:password line found in ~/.instapaperrc'
			ap.exit(-1)
	except IOError:
		ap.error('Please specify a username with -u/--username.')

# Log in to the Instapaper API.
instapaper = Instapaper(args.username, args.password)
(auth_status, auth_message) = instapaper.auth()

# 200: OK
# 403: Invalid username or password.
# 500: The service encountered an error.
if 200 != auth_status:
	print >> sys.stderr, auth_message
	ap.exit(-1)

# Get the Reading List items
rlr = ReadingListReader()
articles = rlr.read()

for article in articles:

	(add_status, add_message) = instapaper.add_item(article['url'].encode('utf-8'), title=article['title'].encode('utf-8'))
	
	# 201: Added
	# 400: Rejected (malformed request or exceeded rate limit; probably missing a parameter)
	# 403: Invalid username or password; in most cases probably should have been caught above.
	# 500: The service encountered an error.
	if 201 == add_status:
		if args.verbose:
			print article['url'].encode('utf-8')
	else:
		print >> sys.stderr, add_message
		ap.exit(-1)

########NEW FILE########
__FILENAME__ = readinglist2pinboard
#!/usr/bin/env python

# This script posts items from your Reading List to your Pinboard account as
# bookmarks marked 'to read'. Learn about Pinboard at https://pinboard.in/tour/

from readinglistlib import ReadingListReader
import urllib

#
# Find your Pinboard API Token at https://pinboard.in/settings/password
# It will look something like apitoken = 'username:5CABE73682AAA9856010'
#
auth_token = '';
api_url = 'https://api.pinboard.in/v1/posts/add?'

rlr = ReadingListReader()
bookmarks = rlr.read()
for bookmark in bookmarks:
  params = urllib.urlencode({
			'url': bookmark['url'],
			'description': bookmark['title'],
			'extended': bookmark['preview'],
			'toread': 'yes',
			'auth_token': auth_token})
	urllib.urlopen(api_url + params)
	# validation of response result_code is left as an exercise for the reader

########NEW FILE########
__FILENAME__ = readinglist2pocket
#!/usr/bin/env python

# Requires https://github.com/samuelkordik/pocketlib

from readinglistlib import ReadingListReader
from pocketlib import Pocket


import argparse
import sys

# Configure and consume command line arguments.
ap = argparse.ArgumentParser(description='This script adds your Safari Reading List articles to Pocket.')
ap.add_argument('-v', '--verbose', action='store_true', help='Print article URLs as they are added.')
args = ap.parse_args()

# Initialize Pocket API
pocket = Pocket()

if pocket.is_authed() is False:
    print 'You need to authorize this script through Pocket before using it'
    print 'Follow these steps:'
    pocket.auth()

# Get the Reading List items
rlr = ReadingListReader()
articles = rlr.read(show="unread")

for article in articles:
    (add_status, add_message) = pocket.add_item(article['url'].encode('utf-8'), title=article['title'].encode('utf-8'), tags='reading_list')
    if 200 == add_status:
        if args.verbose:
            print article['url'].encode('utf-8')
    else:
        print >> sys.stderr, add_message
        ap.exit(-1)

########NEW FILE########
__FILENAME__ = readinglistlib
import os
import subprocess
import plistlib
import datetime
from copy import deepcopy


class ReadingListReader:

    # input is path to a Safari bookmarks file; if None, use default file
    def __init__(self, input=None):

        if None == input:
            input = os.path.expanduser('~/Library/Safari/Bookmarks.plist')

        # Read and parse the bookmarks file
        pipe = subprocess.Popen(('/usr/bin/plutil', '-convert', 'xml1', '-o', '-', input), shell=False, stdout=subprocess.PIPE).stdout
        xml = plistlib.readPlist(pipe)
        pipe.close()

        # Locate reading list section
        section = filter(lambda record: 'com.apple.ReadingList' == record.get('Title'), xml['Children'])
        reading_list = section[0].get('Children')
        if None == reading_list:
            reading_list = []

        # Assemble list of bookmark items
        self._articles = []
        for item in reading_list:

            # Use epoch time as a placeholder for undefined dates
            # (potentially facilitates sorting and filtering)
            added = item['ReadingList'].get('DateAdded')
            if None == added:
                added = datetime.datetime.min
            viewed = item['ReadingList'].get('DateLastViewed')
            if None == viewed:
                viewed = datetime.datetime.min
            fetched = item['ReadingList'].get('DateLastFetched')
            if None == fetched:
                fetched = item['ReadingListNonSync'].get('DateLastFetched') if 'ReadingListNonSync' in item else None
                if None == fetched:
                    fetched = datetime.datetime.min
            archived = item['ReadingListNonSync'].get('ArchiveOnDisk') if 'ReadingListNonSync' in item else None
            self._articles.append({
                    'title': item['URIDictionary']['title'],
                    'url': item['URLString'],
                    'preview': item['ReadingList'].get('PreviewText', ''),
                    'archived': archived,
                    'date': fetched,
                    'added': added,
                    'viewed': viewed,
                    'uuid': item['WebBookmarkUUID'],
                    'synckey': item['Sync'].get('Key'),
                    'syncserverid': item['Sync'].get('ServerID')})

    # show specifies what articles to return: 'unread' or 'read'; if None, all.
    # sortfield is one of the _articles dictionary keys
    # ascending determines sort order; if false, sort is descending order
    # dateformat is used to format dates; if None, datetime objects are returned
    def read(self, show='unread', sortfield='date', ascending=True, dateformat=None):

        # Filter, sort, and return a fresh copy of the internal article list
        articles = deepcopy(self._articles)

        # Filter article list to show only unread or read articles, if requested
        if 'unread' == show:
            articles = filter(lambda record: datetime.datetime.min == record['viewed'], articles)
        elif 'read' == show:
            articles = filter(lambda record: datetime.datetime.min != record['viewed'], articles)
        else:
            pass

        # Sort articles.
        articles = sorted(articles, key=lambda record: record[sortfield])
        if not ascending:
            articles.reverse()

        # Replace any datetime.min sort/filter placeholders with None
        articles = map(self.resetUndefinedDates, articles)

        # If a date format (such as '%a %b %d %H:%M:%S %Y') is specified,
        # convert all defined dates to that format and undefined dates to ''.
        if None != dateformat:
            articles = map(self.formatDates, articles, [dateformat for i in range(len(articles))])

        return articles

    def resetUndefinedDates(self, article):
        if datetime.datetime.min == article['viewed']:
            article['viewed'] = None
        if datetime.datetime.min == article['added']:
            article['added'] = None
        return article

    def formatDates(self, article, dateformat):
        if None != article['viewed']:
            article['viewed'] = article['viewed'].strftime(dateformat)
        else:
            article['viewed'] = ''
        if None != article['added']:
            article['added'] = article['added'].strftime(dateformat)
        else:
            article['added'] = ''
        article['date'] = article['date'].strftime(dateformat)
        return article

########NEW FILE########
__FILENAME__ = readinglistreader
#!/usr/bin/env python

import os
import argparse
import datetime

from readinglistlib import ReadingListReader

# Configure CLI
fields = ['title', 'url', 'preview', 'date', 'added', 'viewed', 'uuid', 'synckey', 'syncserverid']
ap = argparse.ArgumentParser(description='This script outputs the contents of your Safari Reading List, a queue of temporary bookmarks representing articles you intend to read. By default, it prints the title and url of unread articles in chronological order, beginning with the oldest bookmark. Default output is compliant with CSV conventions.')
ap.add_argument('--separator', action='store', default=',', metavar='SEP', help='Separates field values. Specify \'tab\' to use an actual tab character. Defaults to \',\'.')
ap.add_argument('--quote', action='store', default='"', help='Specify \'\' to suppress quoting. Defaults to \'"\'.')
ap.add_argument('--forcequotes', action='store_true', default=False, help="Quote all field values. By default, only quote empty fields or values containing SEP, QUOTE, or newlines.")
ap.add_argument('--fields', action='store', nargs='+', default=['title', 'url'], choices=fields, metavar='FIELD', help='Controls format of output record. Acceptable fields are title, url, preview, date, added, viewed, uuid, synckey, and syncserverid. Defaults to title and url. (Date is date article was originally bookmarked. If defined, added is date  bookmark was synced via iCloud. If defined, viewed is date article was read.)')
ap.add_argument('--header', action='store_true', default=False, help='Output a header record containing field labels.')
ap.add_argument('--timestamp', action='store', default='%a %b %d %H:%M:%S %Y', metavar='FORMAT', help='Controls format of date, added, and viewed fields. Understands strftime directives. Defaults to \'%%a %%b %%d %%H:%%M:%%S %%Y\' (eg, \'' + datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y') + '\').')
ap.add_argument('--bookmarks', action='store_true', default=False, help='Output items in Netscape bookmarks file format. Overrides preceding tabular output options.')
ap.add_argument('--show', action='store', default='unread', choices=['unread', 'read', 'all'], metavar='FILTER', help='Control which items to output. Acceptable FILTER values are unread, read, or all. Defaults to unread.')
ap.add_argument('--sortfield', action='store', default='date', choices=fields, metavar='FIELD', help="Controls how output is sorted. Defaults to date.")
ap.add_argument('--sortorder', action='store', default='ascending', choices=['ascending', 'descending'], metavar='ORDER', help='May be ascending or descending. Defaults to ascending.')
ap.add_argument('--output', action='store', type=argparse.FileType('w'), default='-', help='Output file path. Defaults to stdout.')
ap.add_argument('--input', action='store', default=os.path.expanduser('~/Library/Safari/Bookmarks.plist'), help='Input file path. Assumed to be a Safari bookmarks file formatted as a binary property list. Defaults to ~/Library/Safari/Bookmarks.plist')
args = ap.parse_args()

# Reinterpretation of fiddly options
if 'tab' == args.separator:
	args.separator = '\t'

# Input
if not os.path.exists(args.input):
	raise SystemExit, "The input file does not exist: %s" % args.input
rlr = ReadingListReader(args.input)

bookmarks = rlr.read(
		show = None if 'all' == args.show else args.show,
		sortfield = args.sortfield,
		ascending = True if 'ascending' == args.sortorder else False,
		dateformat = args.timestamp)

if args.bookmarks:

	# Netscape Bookmarks File formatted output
	# eg http://msdn.microsoft.com/en-us/library/ie/aa753582(v=vs.85).aspx
	
	print >> args.output, '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<HTML>\n<META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=UTF-8">\n<Title>Bookmarks</Title>\n<H1>Bookmarks</H1>\n<DT><H3 FOLDED>Reading List Bookmarks</H3>\n<DL>'
	for bookmark in bookmarks:
		print >> args.output, '	<DT><A HREF="%s">%s</A>' % (bookmark['url'].encode('utf-8'), bookmark['title'].encode('utf-8'))
	print >> args.output, '</DL>\n</HTML>'

else:
	
	# CSV or custom tabular formatted output
	
	# Accepts a value. Tests if it should be quoted and, if so, returns quoted
	# value with any quote characters escaped via duplication.
	# Quoting rules derived from:
	# https://tools.ietf.org/html/rfc4180
	# http://www.creativyst.com/Doc/Articles/CSV/CSV01.htm
	def quotify(value):
		if (args.forcequotes or '' == value or -1 != value.find(args.separator) or -1 != value.find(args.quote) or -1 != value.find('\n')) and '' != args.quote:
			return '%s%s%s' % (args.quote, value.replace(args.quote, '%s%s' % (args.quote, args.quote)), args.quote)
		else:
			return value
	
	# Accepts a list of values. Prints record with separators and, if required, quotes.
	def output_record(values):
		print >> args.output, args.separator.join(map(quotify, values))
	
	# Header record
	if True == args.header:
		output_record(args.fields)
	
	for bookmark in bookmarks:
		field_values = []
		
		for field in args.fields:
			field_value = bookmark[field]			
			field_values.append(field_value.encode('utf-8'))
		
		output_record(field_values)
	

########NEW FILE########
__FILENAME__ = instapaperlib
# encoding: utf-8
'''
 instapaperlib.py -- brief simple library to use instapaper

>>> Instapaper("instapaperlib", "").auth()
(200, 'OK.')

>>> Instapaper("instapaperlib", "dd").auth()
(200, 'OK.')

>>> Instapaper("instapaperlibi", "").auth()
(403, 'Invalid username or password.')

>>> Instapaper("instapaperlib", "").add_item("google.com")
(201, 'URL successfully added.')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google")
(201, 'URL successfully added.')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", response_info=True)
(201, 'URL successfully added.', '"google"', 'http://www.google.com/')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", selection="google page", response_info=True)
(201, 'URL successfully added.', '"google"', 'http://www.google.com/')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", selection="google page", jsonp="callBack", response_info=True)
'callBack({"status":201,"url":"http:\\\\/\\\\/www.google.com\\\\/"});'

>>> Instapaper("instapaperlib", "").add_item("google.com", jsonp="callBack")
'callBack({"status":201,"url":"http:\\\\/\\\\/www.google.com\\\\/"});'

>>> Instapaper("instapaperlib", "").auth(jsonp="callBack")
'callBack({"status":200});'

>>> Instapaper("instapaperlib", "dd").auth(jsonp="callBack")
'callBack({"status":200});'

>>> Instapaper("instapaperlibi", "").auth(jsonp="callBack")
'callBack({"status":403});'

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", redirect="close")
(201, 'URL successfully added.')

'''

import urllib
import urllib2

class Instapaper:
    """ This class provides the structure for the connection object """

    def __init__(self, user, password, https=True):
        self.user = user
        self.password = password
        if https:
            self.authurl = "https://www.instapaper.com/api/authenticate"
            self.addurl = "https://www.instapaper.com/api/add"
        else:
            self.authurl = "http://www.instapaper.com/api/authenticate"
            self.addurl = "http://www.instapaper.com/api/add"

        self.add_status_codes = {
                                      201 : "URL successfully added.",
                                      400 : "Bad Request.",
                                      403 : "Invalid username or password.",
                                      500 : "Service error. Try again later."
                                }

        self.auth_status_codes = {
                                      200 : "OK.",
                                      403 : "Invalid username or password.",
                                      500 : "Service error. Try again later."
                                 }

    def add_item(self, url, title=None, selection=None,
                 jsonp=None, redirect=None, response_info=False):
        """ Method to add a new item to a instapaper account

            Parameters: url -> URL to add
                        title -> optional title for the URL
            Returns: (status as int, status error message)
        """
        parameters = {
                      'username' : self.user,
                      'password' : self.password,
                      'url' : url,
                     }
        # look for optional parameters title and selection
        if title is not None:
            parameters['title'] = title
        else:
            parameters['auto-title'] = 1
        if selection is not None:
            parameters['selection'] = selection
        if redirect is not None:
            parameters['redirect'] = redirect
        if jsonp is not None:
            parameters['jsonp'] = jsonp

        # make query with the chosen parameters
        status, headers = self._query(self.addurl, parameters)
        # return the callback call if we want jsonp
        if jsonp is not None:
            return status
        statustxt = self.add_status_codes[int(status)]
        # if response headers are desired, return them also
        if response_info:
            return (int(status), statustxt, headers['title'], headers['location'])
        else:
            return (int(status), statustxt)

    def auth(self, user=None, password=None, jsonp=None):
        """ authenticate with the instapaper.com service

            Parameters: user -> username
                        password -> password
            Returns: (status as int, status error message)
        """
        if not user:
            user = self.user
        if not password:
            password = self.password
        parameters = {
                      'username' : self.user,
                      'password' : self.password
                     }
        if jsonp is not None:
            parameters['jsonp'] = jsonp
        status, headers = self._query(self.authurl, parameters)
        # return the callback call if we want jsonp
        if jsonp is not None:
            return status
        return (int(status), self.auth_status_codes[int(status)])

    def _query(self, url=None, params=""):
        """ method to query a URL with the given parameters

            Parameters:
                url -> URL to query
                params -> dictionary with parameter values

            Returns: HTTP response code, headers
                     If an exception occurred, headers fields are None
        """
        if url is None:
            raise NoUrlError("No URL was provided.")
        # return values
        headers = {'location': None, 'title': None}
        headerdata = urllib.urlencode(params)
        try:
            request = urllib2.Request(url, headerdata)
            response = urllib2.urlopen(request)
            status = response.read()
            info = response.info()
            try:
                headers['location'] = info['Content-Location']
            except KeyError:
                pass
            try:
                headers['title'] = info['X-Instapaper-Title']
            except KeyError:
                pass
            return (status, headers)
        except IOError as exception:
            return (exception.code, headers)

# instapaper specific exceptions
class NoUrlError(Exception):
    """ exception to raise if no URL is given.
    """
    def __init__(self, arg):
        self.arg = arg
    def __str__(self):
        return repr(self.arg)



if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = readinglist2instapaper
#!/usr/bin/env python

# Requires https://github.com/mrtazz/InstapaperLibrary
from instapaperlib import Instapaper

from readinglistlib import ReadingListReader

# Standard library modules
import argparse
import sys
import os
import re

# Configure and consume command line arguments.
ap = argparse.ArgumentParser(description='This script adds your Safari Reading List articles to Instapaper.')
ap.add_argument('-u', '--username', action='store', default='', help='Instapaper username or email.')
ap.add_argument('-p', '--password', action='store', default='', help='Instapaper password (if any).')
ap.add_argument('-v', '--verbose', action='store_true', help='Print article URLs as they are added.')
args = ap.parse_args()

if '' == args.username:
	# For compatibility with instapaperlib's instapaper.py tool,
	# attempt to read Instapaper username and password from ~/.instapaperrc.
	# (Login pattern modified to accept blank passwords.)
	login = re.compile("(.+?):(.*)")
	try:
		config = open(os.path.expanduser('~') + '/.instapaperrc')
		for line in config:
			matches = login.match(line)
			if matches:
				args.username = matches.group(1).strip()
				args.password = matches.group(2).strip()
				break
		if '' == args.username:
			print >> sys.stderr, 'No username:password line found in ~/.instapaperrc'
			ap.exit(-1)
	except IOError:
		ap.error('Please specify a username with -u/--username.')

# Log in to the Instapaper API.
instapaper = Instapaper(args.username, args.password)
(auth_status, auth_message) = instapaper.auth()

# 200: OK
# 403: Invalid username or password.
# 500: The service encountered an error.
if 200 != auth_status:
	print >> sys.stderr, auth_message
	ap.exit(-1)

# Get the Reading List items
rlr = ReadingListReader()
articles = rlr.read()

for article in articles:

	(add_status, add_message) = instapaper.add_item(article['url'].encode('utf-8'), title=article['title'].encode('utf-8'))
	
	# 201: Added
	# 400: Rejected (malformed request or exceeded rate limit; probably missing a parameter)
	# 403: Invalid username or password; in most cases probably should have been caught above.
	# 500: The service encountered an error.
	if 201 == add_status:
		if args.verbose:
			print article['url'].encode('utf-8')
	else:
		print >> sys.stderr, add_message
		ap.exit(-1)

########NEW FILE########
__FILENAME__ = readinglistlib
import os
import subprocess
import plistlib
import datetime
from copy import deepcopy

class ReadingListReader:
	
	# input is path to a Safari bookmarks file; if None, use default file	
	def __init__(self, input=None):
		
		if None == input:
			input = os.path.expanduser('~/Library/Safari/Bookmarks.plist')
					
		# Read and parse the bookmarks file
		pipe = subprocess.Popen(('/usr/bin/plutil', '-convert', 'xml1', '-o', '-', input), shell=False, stdout=subprocess.PIPE).stdout
		xml = plistlib.readPlist(pipe)
		pipe.close()
		
		# Locate reading list section
		section = filter(lambda record: 'com.apple.ReadingList' == record.get('Title'), xml['Children'])
		reading_list = section[0].get('Children')
		if None == reading_list:
			reading_list = []
		
		# Assemble list of bookmark items
		self._articles = []
		for item in reading_list:
			
			# Use epoch time as a placeholder for undefined dates
			# (potentially facilitates sorting and filtering)
			added = item['ReadingList'].get('DateAdded')
			if None == added:
				added = datetime.datetime.min
			viewed = item['ReadingList'].get('DateLastViewed')
			if None == viewed:
				viewed = datetime.datetime.min
			fetched = item['ReadingList'].get('DateLastFetched')
			if None == fetched:
				fetched = item['ReadingListNonSync'].get('DateLastFetched')
				if None == fetched:
					fetched = datetime.datetime.min
			
			self._articles.append({
					'title': item['URIDictionary']['title'],
					'url': item['URLString'],
					'preview': item['ReadingList'].get('PreviewText',''),
					'date': fetched,
					'added': added,
					'viewed': viewed,
					'uuid': item['WebBookmarkUUID'],
					'synckey': item['Sync'].get('Key'),
					'syncserverid': item['Sync'].get('ServerID')})
	
	# show specifies what articles to return: 'unread' or 'read'; if None, all.
	# sortfield is one of the _articles dictionary keys
	# ascending determines sort order; if false, sort is descending order
	# dateformat is used to format dates; if None, datetime objects are returned
	def read(self, show='unread', sortfield='date', ascending=True, dateformat=None):
		
		# Filter, sort, and return a fresh copy of the internal article list
		articles = deepcopy(self._articles)
		
		# Filter article list to show only unread or read articles, if requested		
		if 'unread' == show:
			articles = filter(lambda record: datetime.datetime.min == record['viewed'], articles)
		elif 'read' == show:
			articles = filter(lambda record: datetime.datetime.min != record['viewed'], articles)
		else:
			pass
		
		# Sort articles.
		articles = sorted(articles, key=lambda record: record[sortfield])
		if not ascending:
			articles.reverse()
		
		# Replace any datetime.min sort/filter placeholders with None
		articles = map(self.resetUndefinedDates, articles)
		
		# If a date format (such as '%a %b %d %H:%M:%S %Y') is specified,
		# convert all defined dates to that format and undefined dates to ''.
		if None != dateformat:
			articles = map(self.formatDates, articles, [dateformat for i in range(len(articles))])
					
		return articles
	
	def resetUndefinedDates(self, article):
		if datetime.datetime.min == article['viewed']:
			article['viewed'] = None
		if datetime.datetime.min == article['added']:
			article['added'] = None	
		return article
	
	def formatDates(self, article, dateformat):
		if None != article['viewed']:
			article['viewed'] = article['viewed'].strftime(dateformat)
		else:
			article['viewed'] = ''
		if None != article['added']:
			article['added'] = article['added'].strftime(dateformat)
		else:
			article['added'] = ''
		article['date'] = article['date'].strftime(dateformat)
		return article


########NEW FILE########
__FILENAME__ = instapaperlib
# encoding: utf-8
'''
 instapaperlib.py -- brief simple library to use instapaper

>>> Instapaper("instapaperlib", "").auth()
(200, 'OK.')

>>> Instapaper("instapaperlib", "dd").auth()
(200, 'OK.')

>>> Instapaper("instapaperlibi", "").auth()
(403, 'Invalid username or password.')

>>> Instapaper("instapaperlib", "").add_item("google.com")
(201, 'URL successfully added.')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google")
(201, 'URL successfully added.')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", response_info=True)
(201, 'URL successfully added.', '"google"', 'http://www.google.com/')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", selection="google page", response_info=True)
(201, 'URL successfully added.', '"google"', 'http://www.google.com/')

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", selection="google page", jsonp="callBack", response_info=True)
'callBack({"status":201,"url":"http:\\\\/\\\\/www.google.com\\\\/"});'

>>> Instapaper("instapaperlib", "").add_item("google.com", jsonp="callBack")
'callBack({"status":201,"url":"http:\\\\/\\\\/www.google.com\\\\/"});'

>>> Instapaper("instapaperlib", "").auth(jsonp="callBack")
'callBack({"status":200});'

>>> Instapaper("instapaperlib", "dd").auth(jsonp="callBack")
'callBack({"status":200});'

>>> Instapaper("instapaperlibi", "").auth(jsonp="callBack")
'callBack({"status":403});'

>>> Instapaper("instapaperlib", "").add_item("google.com", "google", redirect="close")
(201, 'URL successfully added.')

'''

import urllib
import urllib2

class Instapaper:
    """ This class provides the structure for the connection object """

    def __init__(self, user, password, https=True):
        self.user = user
        self.password = password
        if https:
            self.authurl = "https://www.instapaper.com/api/authenticate"
            self.addurl = "https://www.instapaper.com/api/add"
        else:
            self.authurl = "http://www.instapaper.com/api/authenticate"
            self.addurl = "http://www.instapaper.com/api/add"

        self.add_status_codes = {
                                      201 : "URL successfully added.",
                                      400 : "Bad Request.",
                                      403 : "Invalid username or password.",
                                      500 : "Service error. Try again later."
                                }

        self.auth_status_codes = {
                                      200 : "OK.",
                                      403 : "Invalid username or password.",
                                      500 : "Service error. Try again later."
                                 }

    def add_item(self, url, title=None, selection=None,
                 jsonp=None, redirect=None, response_info=False):
        """ Method to add a new item to a instapaper account

            Parameters: url -> URL to add
                        title -> optional title for the URL
            Returns: (status as int, status error message)
        """
        parameters = {
                      'username' : self.user,
                      'password' : self.password,
                      'url' : url,
                     }
        # look for optional parameters title and selection
        if title is not None:
            parameters['title'] = title
        else:
            parameters['auto-title'] = 1
        if selection is not None:
            parameters['selection'] = selection
        if redirect is not None:
            parameters['redirect'] = redirect
        if jsonp is not None:
            parameters['jsonp'] = jsonp

        # make query with the chosen parameters
        status, headers = self._query(self.addurl, parameters)
        # return the callback call if we want jsonp
        if jsonp is not None:
            return status
        statustxt = self.add_status_codes[int(status)]
        # if response headers are desired, return them also
        if response_info:
            return (int(status), statustxt, headers['title'], headers['location'])
        else:
            return (int(status), statustxt)

    def auth(self, user=None, password=None, jsonp=None):
        """ authenticate with the instapaper.com service

            Parameters: user -> username
                        password -> password
            Returns: (status as int, status error message)
        """
        if not user:
            user = self.user
        if not password:
            password = self.password
        parameters = {
                      'username' : self.user,
                      'password' : self.password
                     }
        if jsonp is not None:
            parameters['jsonp'] = jsonp
        status, headers = self._query(self.authurl, parameters)
        # return the callback call if we want jsonp
        if jsonp is not None:
            return status
        return (int(status), self.auth_status_codes[int(status)])

    def _query(self, url=None, params=""):
        """ method to query a URL with the given parameters

            Parameters:
                url -> URL to query
                params -> dictionary with parameter values

            Returns: HTTP response code, headers
                     If an exception occurred, headers fields are None
        """
        if url is None:
            raise NoUrlError("No URL was provided.")
        # return values
        headers = {'location': None, 'title': None}
        headerdata = urllib.urlencode(params)
        try:
            request = urllib2.Request(url, headerdata)
            response = urllib2.urlopen(request)
            status = response.read()
            info = response.info()
            try:
                headers['location'] = info['Content-Location']
            except KeyError:
                pass
            try:
                headers['title'] = info['X-Instapaper-Title']
            except KeyError:
                pass
            return (status, headers)
        except IOError as exception:
            return (exception.code, headers)

# instapaper specific exceptions
class NoUrlError(Exception):
    """ exception to raise if no URL is given.
    """
    def __init__(self, arg):
        self.arg = arg
    def __str__(self):
        return repr(self.arg)



if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = readinglist2instapaper
#!/usr/bin/env python

# Requires https://github.com/mrtazz/InstapaperLibrary
from instapaperlib import Instapaper

from readinglistlib import ReadingListReader

# Standard library modules
import argparse
import sys
import os
import re

# Configure and consume command line arguments.
ap = argparse.ArgumentParser(description='This script adds your Safari Reading List articles to Instapaper.')
ap.add_argument('-u', '--username', action='store', default='', help='Instapaper username or email.')
ap.add_argument('-p', '--password', action='store', default='', help='Instapaper password (if any).')
ap.add_argument('-v', '--verbose', action='store_true', help='Print article URLs as they are added.')
args = ap.parse_args()

if '' == args.username:
	# For compatibility with instapaperlib's instapaper.py tool,
	# attempt to read Instapaper username and password from ~/.instapaperrc.
	# (Login pattern modified to accept blank passwords.)
	login = re.compile("(.+?):(.*)")
	try:
		config = open(os.path.expanduser('~') + '/.instapaperrc')
		for line in config:
			matches = login.match(line)
			if matches:
				args.username = matches.group(1).strip()
				args.password = matches.group(2).strip()
				break
		if '' == args.username:
			print >> sys.stderr, 'No username:password line found in ~/.instapaperrc'
			ap.exit(-1)
	except IOError:
		ap.error('Please specify a username with -u/--username.')

# Log in to the Instapaper API.
instapaper = Instapaper(args.username, args.password)
(auth_status, auth_message) = instapaper.auth()

# 200: OK
# 403: Invalid username or password.
# 500: The service encountered an error.
if 200 != auth_status:
	print >> sys.stderr, auth_message
	ap.exit(-1)

# Get the Reading List items
rlr = ReadingListReader()
articles = rlr.read()

for article in articles:

	(add_status, add_message) = instapaper.add_item(article['url'].encode('utf-8'), title=article['title'].encode('utf-8'))
	
	# 201: Added
	# 400: Rejected (malformed request or exceeded rate limit; probably missing a parameter)
	# 403: Invalid username or password; in most cases probably should have been caught above.
	# 500: The service encountered an error.
	if 201 == add_status:
		if args.verbose:
			print article['url'].encode('utf-8')
	else:
		print >> sys.stderr, add_message
		ap.exit(-1)

########NEW FILE########
__FILENAME__ = readinglistlib
import os
import subprocess
import plistlib
import datetime
from copy import deepcopy

class ReadingListReader:
	
	# input is path to a Safari bookmarks file; if None, use default file	
	def __init__(self, input=None):
		
		if None == input:
			input = os.path.expanduser('~/Library/Safari/Bookmarks.plist')
					
		# Read and parse the bookmarks file
		pipe = subprocess.Popen(('/usr/bin/plutil', '-convert', 'xml1', '-o', '-', input), shell=False, stdout=subprocess.PIPE).stdout
		xml = plistlib.readPlist(pipe)
		pipe.close()
		
		# Locate reading list section
		section = filter(lambda record: 'com.apple.ReadingList' == record.get('Title'), xml['Children'])
		reading_list = section[0].get('Children')
		if None == reading_list:
			reading_list = []
		
		# Assemble list of bookmark items
		self._articles = []
		for item in reading_list:
			
			# Use epoch time as a placeholder for undefined dates
			# (potentially facilitates sorting and filtering)
			added = item['ReadingList'].get('DateAdded')
			if None == added:
				added = datetime.datetime.min
			viewed = item['ReadingList'].get('DateLastViewed')
			if None == viewed:
				viewed = datetime.datetime.min
			fetched = item['ReadingList'].get('DateLastFetched')
			if None == fetched:
				fetched = item['ReadingListNonSync'].get('DateLastFetched')
				if None == fetched:
					fetched = datetime.datetime.min
			
			self._articles.append({
					'title': item['URIDictionary']['title'],
					'url': item['URLString'],
					'preview': item['ReadingList'].get('PreviewText',''),
					'date': fetched,
					'added': added,
					'viewed': viewed,
					'uuid': item['WebBookmarkUUID'],
					'synckey': item['Sync'].get('Key'),
					'syncserverid': item['Sync'].get('ServerID')})
	
	# show specifies what articles to return: 'unread' or 'read'; if None, all.
	# sortfield is one of the _articles dictionary keys
	# ascending determines sort order; if false, sort is descending order
	# dateformat is used to format dates; if None, datetime objects are returned
	def read(self, show='unread', sortfield='date', ascending=True, dateformat=None):
		
		# Filter, sort, and return a fresh copy of the internal article list
		articles = deepcopy(self._articles)
		
		# Filter article list to show only unread or read articles, if requested		
		if 'unread' == show:
			articles = filter(lambda record: datetime.datetime.min == record['viewed'], articles)
		elif 'read' == show:
			articles = filter(lambda record: datetime.datetime.min != record['viewed'], articles)
		else:
			pass
		
		# Sort articles.
		articles = sorted(articles, key=lambda record: record[sortfield])
		if not ascending:
			articles.reverse()
		
		# Replace any datetime.min sort/filter placeholders with None
		articles = map(self.resetUndefinedDates, articles)
		
		# If a date format (such as '%a %b %d %H:%M:%S %Y') is specified,
		# convert all defined dates to that format and undefined dates to ''.
		if None != dateformat:
			articles = map(self.formatDates, articles, [dateformat for i in range(len(articles))])
					
		return articles
	
	def resetUndefinedDates(self, article):
		if datetime.datetime.min == article['viewed']:
			article['viewed'] = None
		if datetime.datetime.min == article['added']:
			article['added'] = None	
		return article
	
	def formatDates(self, article, dateformat):
		if None != article['viewed']:
			article['viewed'] = article['viewed'].strftime(dateformat)
		else:
			article['viewed'] = ''
		if None != article['added']:
			article['added'] = article['added'].strftime(dateformat)
		else:
			article['added'] = ''
		article['date'] = article['date'].strftime(dateformat)
		return article


########NEW FILE########
