__FILENAME__ = httppost

"""
HTTP POST helper functions.
"""

import mimetypes
import urlparse
import httplib

def post_multipart(host, selector, fields, files):
	"""
	Post fields and files to an http host as multipart/form-data.
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return the server's response page.
	"""
	content_type, body = encode_multipart_formdata(fields, files)
	h = httplib.HTTPConnection(host)
	h.putrequest('POST', selector)
	h.putheader('content-type', content_type)
	h.putheader('content-length', str(len(body)))
	h.endheaders()
	h.send(body)
	response = h.getresponse()
	return response.read()


def encode_multipart_formdata(fields, files):
	"""
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return (content_type, body) ready for httplib.HTTP instance
	"""
	BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
	CRLF = '\r\n'
	L = []
	for (key, value) in fields:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(str(value))
	for (key, filename, value) in files:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
		L.append('Content-Type: %s' % get_content_type(filename))
		L.append('')
		L.append(value.read())
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body


def posturl(url, fields, files):
	urlparts = urlparse.urlsplit(url)
	return post_multipart(urlparts[1], urlparts[2], fields,files)


def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def extract_django_error(html):

	from BeautifulSoup import BeautifulSoup as BS
	
	soup = BS(html)
	return str(soup.find(id="pastebinTraceback"))
########NEW FILE########
__FILENAME__ = lastcat
#!/usr/bin/python

"""
A simple program to list some features of .last files
"""

from lastgui.storage import UserHistory

import sys, os

def usage():
	print >> sys.stderr, "Usage: %s <filename.last> <action>" % sys.argv[0]

try:
	filename = sys.argv[1]
except IndexError:
	usage()
	sys.exit(1)

try:
	action = sys.argv[2]
except IndexError:
	usage()
	sys.exit(1)

uh = UserHistory(None)
uh.load(open(filename))

if action == "artists":
	print "\n".join(uh.artists.keys())
elif action == "weeks":
	print "\n".join(map(str, uh.weeks.keys()))
elif action == "age":
	print uh.data_age()
else:
	print >> sys.stderr, "Unknown action"
	sys.exit(1)
########NEW FILE########
__FILENAME__ = admin
from django.contrib.admin import site
from .models import LastFmUser, Node, Poster

site.register(
    LastFmUser,
    list_display = ("id", "username", "requested_update", "last_check"),
    list_display_links = ("id", "username"),
    search_fields = ("username",),
    ordering = ("-last_check",),
)


site.register(
    Poster,
    list_display = ("id", "user", "requested", "completed", "failed"),
    ordering = ("-requested",),
)


site.register(
    Node,
    list_display = ("nodename", "disabled", "lastseen"),
)

########NEW FILE########
__FILENAME__ = api

import datetime, time

from shortcuts import *

from lastgui.models import *
from lastgui.storage import UserHistory


# Some custom exceptions

class IncorrectPassword(Exception): pass

class BadData(Exception): pass

class MissingXML(Exception): pass



def valid_node(func):
	"""Decorator, which ensures the requester is a valid node."""
	def inner(request, *args, **kwds):
		nodename = request.REQUEST.get("nodename", None)
		password = request.REQUEST.get("password", None)
		
		# If they didn't provide, say so
		if not (nodename and password):
			return jsonify({"error":"authentication/missing"})
		
		# Get the Node and see if they have a match
		try:
			node = Node.objects.get(nodename=nodename)
			if not node.password_matches(password):
				raise IncorrectPassword
		except (Node.DoesNotExist, IncorrectPassword):
			return jsonify({"error":"authentication/invalid"})
		
		# Bung the node onto the request object
		request.node = node
		
		# Update it's lastseen
		node.lastseen = datetime.datetime.utcnow()
		node.save()
		
		# OK, all seems sensible
		return func(request, *args, **kwds)
	return inner


def datetime_to_epoch(dt):
	"""Turns a datetime.datetime into a seconds-since-epoch timestamp."""
	return time.mktime(dt.timetuple())

###################

@valid_node
def index(request):
	return jsonify({"server":"lastgraph/3.0"})


def graph_data(poster):
	
	uh = UserHistory(poster.user.username)
	uh.load_if_possible()
	
	# Get the start/end pairs of week times
	weeks = uh.weeks.keys()
	
	if not weeks:
		raise BadData("Empty")
	
	weeks.sort()
	weeks = zip(weeks, weeks[1:]+[weeks[-1]+7*86400])
	
	# Limit those to ones in the graph range
	pstart = datetime_to_epoch(poster.start)
	pend = datetime_to_epoch(poster.end)
	
	weeks = [(start, end) for start, end in weeks if (end > pstart) and (start < pend)]
	
	weekdata = [(start, end, uh.weeks[start].items()) for start, end in weeks]
	
	return weekdata


@valid_node
def render_next(request):
	
	"""
	Returns the next set of render data.
	"""
	
	# Get the Posters that needs rendering
	try:
		poster = Poster.queue()[0]
	except IndexError:
		return jsonify({"nothing":True})
	
	return render_data(request, poster.id)


@valid_node
def render_data(request, id=None):
	
	"""
	Returns a set of render data for the specified graph.
	"""
	
	if id is None:
		id = request.GET['id']
	
	poster = Poster.objects.get(id=id)
	
	# Compile a week data list
	try:
		weekdata = graph_data(poster)
	except BadData:
		poster.set_error("BadData")
		return jsonify({"nothing":True, "skipped":"%s/BadData" % poster.id})
	except MissingXML:
		poster.set_error("BadData")
		return jsonify({"nothing":True, "skipped":"%s/MissingXML" % poster.id})
	
	# Check it has data
	if len(weekdata) < 1:
		poster.set_error("No data (graph would be empty)")
		return jsonify({"nothing":True, "skipped":"%s/NoData" % poster.id})
	
	# Check it has data
	if len(weekdata) == 1:
		poster.set_error("Only one week of data (need two or more to graph)")
		return jsonify({"nothing":True, "skipped":"%s/OneWeek" % poster.id})
	
	poster.started = datetime.datetime.utcnow()
	poster.node = request.node
	poster.save()
	
	return jsonify({
		"id": poster.id,
		"username": poster.user.username,
		"start": int(time.mktime(poster.start.timetuple())),
		"end": int(time.mktime(poster.end.timetuple())),
		"params": poster.params,
		"data": weekdata,
	})


@valid_node
def render_links(request):
	
	id = request.POST['id']
	poster = Poster.objects.get(id=id)
	
	poster.pdf_url = request.POST['pdf_url']
	poster.svg_url = request.POST['svg_url']
	poster.completed = datetime.datetime.utcnow()
	poster.expires = datetime.datetime.utcnow() + datetime.timedelta(7)
	poster.save()
	
	return jsonify({"success":True})


@valid_node
def render_failed(request):
	
	"""
	Recieves downloaded week data.
	"""
	
	id = request.REQUEST['id']
	poster = Poster.objects.get(id=id)
	poster.set_error("Renderer error:\n%s" % request.REQUEST.get("traceback", "No traceback"))
	
	return jsonify({"recorded":True})
########NEW FILE########
__FILENAME__ = data
hotlink_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\na\x00\x00\na\x01\xfc\xccJ%\x00\x00\x00\x19tEXtSoftware\x00www.inkscape.org\x9b\xee<\x1a\x00\x00\x05-IDATh\x81\xed\x98[l\x14e\x18\x86\x9fofK\xa1T\xc1\x9e\xb7\x05b\x88\x1c\xc4\x84\x18\xa3D\xe4\xa2\xb4\xa5R\x12\xa5Z\xba\x8b\xc4h\x08\x17V\x13\xbd\xf1\x82\x84\x0b\xa8\xab\t\xdc\xe95\xc6\x08\x1a\x89\t\x14\xe5\xa0\t\x14\x0c1\xd1\x96\x14\xbc\xc1\x90xK\xdar\xd8\xd2\x1a\x13\xda\xb2\xdb\xdd\xf9\xbc\xd8\x1d2\x9d\xecnwf\xc7P\x82o2\xd9\x9d\xff4\xef\xfb\xbf\xff\xff\xcf7\x9f\xa8*\x8f2\x8c\x87M\xa0T\xfc/\xe0a\xe3\xf1\x15\x10\x13\tL|)c\xf9\xea\xb8_\xe4h\n\xceFEL\xbf\x0f\xb6\x11\x151Spv\xbf\xc8Q?\xfd\xc5\xeb1\xba_\xe4h5\xec(\x07\xe3\x16\\2a{\xaf\xaa\xe5\xe7\xe11\x11#\rg\xc2\xd0\x92\x00k\x1cN~\xa6\xba\xdb\xcb\x18\x9e\x1c8 r\xa4\x1a\xba\x9a\xa0\xb2\x06*\x1a\xa0%\x05\xa7\xfd,\x81\x98\x88\x91\x82\xd3\r\xd0R\x03\x15MPY\r]\x07D\x8ex\x19\xa7\xe8\x07\xc7DB\n\xab\xca\xa1\xdc.\xab\x85\x8a0\xb4z\x15a\x93\x0fCk-T\xd8\xe5\xe5P\xae\xb0*&\x12\n\\@\xafj*\x04\xad7a\xe8.$\x9d"\x1a=\x88\xb0\xc97\xba\xc8\xdf\x85\xe4M\x18\nAk\xafj*p\x01Y\x11\xc9\x10\xb4\xb9E\xd4d\x9d\x98\x81S\x85D\xc4D\x8c\x198\x15\x86\xd6\x9a\xdc\xe4\xdbzU\x93\xf9\xfa\x97,\xa0\x90\x88\xac\x13m\xf9D\xd8\xe4\x1b\xa1-\xcf\xcc{&\x0f>N!\x07\xa1\x05)\xf8\xa5\x11^\xaaq\xec\x8b1\x98\xba\r\x17Mx\xd3>\x9d\xb2\xa7\xcd\x8f\r\xb0\xc5E>q\x13\xae\xf8%_\x92\x80"D\\0\xa1\x0b \r?4@{\xd0\xe4K\x16`\x8bH\xc3\xc50l\xc8%\x02 \x17\xf9[0d\xc2\x96R\xc8C\x00\x02\xa0\xb0\x08\xc8\xec\x0f\xbb,H\xf2\x10\x90\x00\xc8/\xc2\x89\xa0\xc9C\x80\xd1h\xafj\xd2\x84-\xb7`h\x0c\x12\xee\xfa\xb1\xff\x80<\x04\x1cN_\x874p\x8f\xcc\xaf\x1bi\xe0\xde\xf5\xdcu\xbe\x11\x98\x80\xa8\x88\xb9\x06\xce\xd4C\xb3s\xcd\xdb\xa8\x85\x8azh^\x03g\x82\x88bm\x04"\xc0&\xdf\x00\x9b\xeb\x1c\xe4\'\xe0\xfe\x04\xdc\xb7\xef\xeb2\x01\xe0\xe6 E\x94\xbc\x89\xa3"\xe6Z8[\x0f\xcdn\xf2\xa3\xf0;@\x13l\xaa\x82\x85v]\x1c\xa6\xee\xc0\xaf\x7f\xc1\xeb\xc7UKZR%9P\x88\xfc\x08\x0c\x98\xd0aB\xc7\x08\x0c\xb8\x9d\xa8\x87\xe6\xb5\x01|\x14\xf9v \x1f\xf9q\x98\x1e\x85\xc1\x10l\xb5\xa3\xca\x98H(\x05\xe7\x9b`c5,\xb2\xdb\x06\xe1\x84/\x07\xbc\x90\x87\x07\xa1\xf8\xd6Q\x18\x1c\x87i\xbb<\x08\'<;`\x93\xaf\x83\xe6\xfa\xd9\xcbfz\x04\x06\xe3\xd0qXu&W\xdf\x1e\x91\xb2:8\xb7\x0c6V9\x9c\xb8\x03Sq\x9fNxr\xc09\xf3n\xf2\xa3p\xb9\x10y\x80\xc3\xaa3q\xe8\x18\x85\xcb\x13\x0e\'\xeaKp\xa2h\x07\xb2!\xf1O~f\xde\x8d\xb9\x9c0\xe1\xb5b\x13\x05^\xf7\xc0\xac\x10`\x02\xa6\x87\x8b\x98y7l\'\x86]N\xe4z\xc6\\\xf0\xb4\x07\xb2\xdf\xb3\'\xeb\xa0}\x01\x18\xc3py\x0c\xb6z!\xefD\x8fHY-\x9c_\x0e/\'\xc1\x8a\xc3\x85\x10\xec\xf0\x92\xa6\xf1\xbc\x89\xb3K\xa9O\xe1\xa98\xbc\xea\x97\xbc\x8d\xecr\xea\x17\xf8\xdb\x84n\xaf9&_\xef\x81\xec7\xaf\xe1%{0\xc7x!\xc0\xf2\x93 \x0b\xec{\xe0a\xe1\xf1\xcdN\xcf\x17x\x16\xd0)\xf2DTdE1m\xbbE\xd6\x03DE\x96\xb8\xeb\xde\x15Y\xdc-\xb2\xd2\xbe\x8f\x8aT\xfa\xc9\xb1z\xeeP\x06\xcf(\xbc\x9d\xaf>*\xb2""\xd2\x99\x1d\xfc`K&\xa7\xda\xe5n\x97\x84&\x03\xf68\x8a6\xfc\tO{\xe53+\x89\x1a\x11\xd9\x9b\xfdk\x9eP=\x14\x15y^\xe1-`\xf0\x84\xea\xe9l\x87\x19\x0b^\xdc)\xf2E\x1a\x8e\xf5\xa9^\x8d\x8a|\xa0\x10\xb6\xe0\xcb\x10\xbc\x01\xb4\xef\x10\xf9\xc3\x84\xd4%\xd5TD\xa4v\x97Hc\n\xde7`\xa9\xc2w&\xc4\x013"\xb2\r\xf8\x07(7`qD\xa4\x07\xa8\x04\x96T\xc2\xc1iX\xa7\xf0\xa1\xc2$\xf0\xf3q\xd5sN\xce\x86\xebf}\x08\xbe7`mT\xa4\x12\xf8\xb8\x0f\xf6\t\xbc\xb3]\xe4A\xf8\xa00^\x06\xbd&|\x14\x15Y\xa7\xb04\x04_\x87`\x9f\x05W\x15\xfaO\xaa\x8e\xd8\xed\x05^I@B\xe0Y\x85O\x14z\xb2\xe3\xac4\xa0\xf3\x84\xea\x80\xc0j\x85j\x03\x96\x19p\xc5\x00k\x12V\xa5a\x8f\x05\xdf\x02\xed\xcfA\xbf\xdb\x81Y\x02\x14\xac\'\xe1\xb6\x05\x89\x04\x08\xb0T3\xe7\xecx\x19T9\x08\xdd\x18\x85)\x0b\x0c\x85\xb0\x01\x93\x0b\xe1\xb6BC>\xab\x17\x81\x05\x8c\x01\xd3Ffl\x8c\xcc\xacV\xb58\xd2\xe9\n\x96d9X \n\x9f\x0b\x1c\x00\xf6\xe6zO\xcc\xb5\x07\xfa#"\x9f\x02\xf7\x9c3\xea\xc4$\xfcf\xc1\x0bS\x10#\xe3\xc2\xb0\xc0\xce]"\xcb\x013\xd7\x06v\x90\xbdc\xc1W5p(_\x1b\x81\x15\xc05\x85m9\xc7R\xd5\x82\xd7{P6W\x1bw\xbb\xdd\xb0PU\x89\x80YL\xdfBW\x04\x8euCg\x14\xbe\xd9\t\xab\xdd\xf5\xf3\xfeM\x1c\x15\xa9\x12\xd8\x94\x86\x1b}\xaa\xd7\xdc\xf5\xf3^\xc0\\x\xfc\xde\xc4\xf3\r\x8f\xbc\x80\x7f\x01\xc8\xe8\xca\xc4&0\x97\xff\x00\x00\x00\x00IEND\xaeB`\x82'
########NEW FILE########
__FILENAME__ = export
"""
Exporting views
"""


def as_filetype(data, filetype, *a, **kw):
    handler = {
        "csv": as_csv,
    }[filetype]
    return handler(data, *a, **kw)


def as_csv(data, sheet_name=None, filename="data"):
    """
    Exports the given 'data' as a CSV file.
    Data is a list of rows
    Rows are lists of cells
    Cells are tuples of either value or (value, params)
    Ignores its sheet_name parameter, as CSV doesn't support it.
    Also ignores any styling.
    """
    
    from django.http import HttpResponse
    httpresponse = HttpResponse(mimetype='text/csv')
    httpresponse['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename.encode("ascii", "replace")
    
    rowstrs = []
    # Cycle through the rows
    for row in data:
        rowstr = u""
        # And the cells
        for cell in row:
            if isinstance(cell, (tuple, list)):
                rowstr += unicode(cell[0]) + ","
            else:
                rowstr += unicode(cell) + ","
        rowstrs.append(rowstr[:-1])
    
    httpresponse.write("\n".join(rowstrs))
    
    return httpresponse

########NEW FILE########
__FILENAME__ = fetch
"""
Last.fm data fetcher
"""

import sys
import time
import socket
import urllib
import random
import eventlet
from lastgui.xml import *
from lastgui.storage import UserHistory
from django.conf import settings

class LastFmFetcher(object):
    
    def __init__(self):
        self.last = 0.0
        self.delay = 1.0
        self.debug = True
    
    
    def fetch(self, url):
        import time
        # Delay to ensure we don't anger the API server
        while self.last + self.delay > time.time():
            time.sleep(0.001)
        # Nab
        if self.debug:
            print "Fetching %s" % url
        else:
            pass #print >> sys.stderr, "Fetching %s" % url
        
        
        try:
            socket.settimeout(10)
            handle = urllib.urlopen(url)
            data = handle.read()
            #print >> sys.stderr, dict(handle.headers), "for", url
        except (AttributeError, IOError):
            try:
                time.sleep(0.1)
                data = urllib.urlopen(url).read()
            except (AttributeError, IOError):
                try:
                    time.sleep(0.2+random.random()*0.2)
                    data = urllib.urlopen(url).read()
                except (AttributeError, IOError):
                    try:
                        time.sleep(0.3)
                        data = urllib.urlopen(url).read()
                    except (AttributeError, IOError):
                        try:
                            time.sleep(0.4)
                            data = urllib.urlopen(url).read()
                        except (AttributeError, IOError):
                            raise IOError("Cannot contact last.fm")
        
        self.last = time.time()
        return data
    
    
    def weeks(self, username):
        if username.startswith("tag:"):
            return week_list(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=tag.getweeklychartlist&tag=%s&api_key=%s" % (username[4:], settings.API_KEY))
            )
        elif username.startswith("group:"):
            return week_list(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=group.getweeklychartlist&group=%s&api_key=%s" % (username[6:], settings.API_KEY))
            )
        else:
            return week_list(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=user.getweeklychartlist&user=%s&api_key=%s" % (username, settings.API_KEY))
            )
    
    
    def weekly_artists(self, username, start, end):
        if username.startswith("tag:"):
            return weekly_artists(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=tag.getweeklyartistchart&tag=%s&api_key=%s&from=%s&to=%s" % (username[4:], settings.API_KEY, start, end))
            )
        elif username.startswith("group:"):
            return weekly_artists(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=group.getweeklyartistchart&group=%s&api_key=%s&from=%s&to=%s" % (username[6:], settings.API_KEY, start, end))
            )
        else:
            return weekly_artists(
                self.fetch("http://ws.audioscrobbler.com/2.0/?method=user.getweeklyartistchart&user=%s&api_key=%s&from=%s&to=%s" % (username, settings.API_KEY, start, end))
            )


fetcher = LastFmFetcher()


def update_user_history(uh):
    """Given a UserHistory object, updates it so it is current."""
    
    fetcher.delay = settings.LASTFM_DELAY
    
    for start, end in fetcher.weeks(uh.username):
        if not uh.has_week(start):
            try:
                for artist, plays in fetcher.weekly_artists(uh.username, start, end):
                    uh.set_plays(artist, start, plays)
            except:
                # Try once more
                try:
                    for artist, plays in fetcher.weekly_artists(uh.username, start, end):
                        uh.set_plays(artist, start, plays)
                except KeyboardInterrupt:
                    print "Exiting on user command."
                    raise SystemExit
                except Exception, e:
                    print "Warning: Invalid data for %s - %s: %s" % (start, end, repr(e))


def update_user(username):
    """Returns an up-to-date UserHistory for this username,
    perhaps creating it on the way or loading from disk."""
    
    uh = UserHistory(username)
    
    if uh.has_file():
        uh.load_default()
    
    try:
        update_user_history(uh)
        uh.set_timestamp() # We assume we got all the data for now.
    except KeyboardInterrupt:
        pass
    
    uh.save_default()
    
    return uh

########NEW FILE########
__FILENAME__ = add_node
import sys
from django.core.management import BaseCommand
from lastgui.models import Node


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        # Error if we don't understand
        if len(args) != 2:
            print "Usage: add_node <nodename> <password>"
            sys.exit(1)
        # Add the node
        node = Node(nodename=args[0])
        node.set_password(args[1])
        node.save()
        print "Node %s added" % node.nodename

########NEW FILE########
__FILENAME__ = fetch_user
import sys
from django.core.management import BaseCommand
from lastgui.models import *
from lastgui.fetch import update_user


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        # Get the top person in the queue
        queue = LastFmUser.queue().filter(fetching=False)
        try:
            user = queue[0]
        except IndexError:
            print "No users queued."
            sys.exit(2)
        
        print "Updating user '%s'..." % user.username
        user.fetching = True
        user.save()
        
        try:
            # Download their data!
            update_user(user.username)
            
            # Mark them as done!
            user.requested_update = None
            user.fetching = False
            user.save()
            print "Done!"
        except AssertionError, e:
            print "Oh well, we'll ignore them."
            user.requested_update = None
            user.fetching = False
            user.save()
            raise e
        except UnicodeDecodeError, e:
            print "Unicode error. Uh-oh."
            print user.username
            user.fetching = False
            user.save()
        except Exception,e:
            user.fetching = False
            user.save()
            print "Restored user in queue"
            raise e

########NEW FILE########
__FILENAME__ = render_poster
import sys
from django.core.management import BaseCommand
from lastrender.renderer import render_poster


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        render_poster()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LastFmUser'
        db.create_table('lastgui_lastfmuser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('requested_update', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_check', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('external_until', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('fetching', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lastgui', ['LastFmUser'])

        # Adding model 'Poster'
        db.create_table('lastgui_poster', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posters', to=orm['lastgui.LastFmUser'])),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('end', self.gf('django.db.models.fields.DateField')()),
            ('params', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('requested', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('completed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('failed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expires', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('error', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lastgui.Node'], null=True, blank=True)),
            ('pdf_url', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('svg_url', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('lastgui', ['Poster'])

        # Adding model 'Node'
        db.create_table('lastgui_node', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('nodename', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('salt', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('disabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lastseen', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('lastgui', ['Node'])


    def backwards(self, orm):
        # Deleting model 'LastFmUser'
        db.delete_table('lastgui_lastfmuser')

        # Deleting model 'Poster'
        db.delete_table('lastgui_poster')

        # Deleting model 'Node'
        db.delete_table('lastgui_node')


    models = {
        'lastgui.lastfmuser': {
            'Meta': {'object_name': 'LastFmUser'},
            'external_until': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'fetching': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'requested_update': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'lastgui.node': {
            'Meta': {'object_name': 'Node'},
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastseen': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'nodename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'lastgui.poster': {
            'Meta': {'object_name': 'Poster'},
            'completed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {}),
            'error': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'failed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lastgui.Node']", 'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pdf_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'requested': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'svg_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posters'", 'to': "orm['lastgui.LastFmUser']"})
        }
    }

    complete_apps = ['lastgui']
########NEW FILE########
__FILENAME__ = models
from django.db import models
import datetime
import random
import hashlib


class LastFmUser(models.Model):
    """
    Represents a user from that great site, last.fm.
    """
    
    # As seen on last.fm
    username = models.CharField(max_length=255, unique=True)
    
    # Null if no update wanted, else used to prioritise
    requested_update = models.DateTimeField(blank=True, null=True)
    
    # The last time this user was checked for updateness
    last_check = models.DateTimeField(blank=True, null=True)
    
    # Is this account enabled for external image access? And when till?
    external_until = models.DateTimeField(blank=True, null=True)
    
    # Is this already being fetched?
    fetching = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.username
    
    def get_absolute_url(self):
        return "/user/%s/" % self.username

    def external_allowed(self):
        return True  # I've become generous
        # if self.external_until:
        #     return self.external_until > datetime.datetime.utcnow()
        # else:
        #     return False
    
    @classmethod
    def by_username(cls, username):
        "Returns the correct object, possibly creating one."
        try:
            return cls.objects.get(username=username)
        except cls.DoesNotExist:
            instance = cls(username=username)
            instance.save()
            return instance
    
    @classmethod
    def queue(cls):
        "Returns the current update queue."
        return cls.objects.filter(requested_update__isnull=False).order_by("requested_update")


# IDs here ended with 27533
class Poster(models.Model):
    """
    A large poster. A shiny lastgraph2-esque PDF, like.
    """
    
    user = models.ForeignKey(LastFmUser, related_name="posters")
    
    start = models.DateField()
    end = models.DateField()
    
    params = models.TextField(blank=True)
    
    requested = models.DateTimeField(blank=True, null=True)
    started = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    failed = models.DateTimeField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    
    email = models.TextField(blank=True)
    
    error = models.TextField(blank=True)
    
    node = models.ForeignKey("Node", blank=True, null=True)
    
    pdf_url = models.TextField(blank=True)
    svg_url = models.TextField(blank=True)
    
    def __unicode__(self):
        return u"%s: %s - %s" % (self.user, self.start, self.end)
    
    def queue_position(self):
        queue = list(Poster.queue())
        try:
            return queue.index(self) + 1
        except (IndexError, ValueError):
            return len(queue) + 1
    
    def status_string(self):
        if self.failed:
            return "Failed"
        if self.requested:
            if self.completed:
                if self.pdf_url == "expired":
                    return "Expired"
                else:
                    return "Complete"
            elif self.started:
                return "Rendering"
            return "Queued, position %i" % self.queue_position()
        return "Unrequested"
    
    def expired(self):
        return self.completed and self.pdf_url == "expired"
    
    def detail_string(self):
        detail = int(self.params.split("|")[1])
        return {
            1: "Super",
            2: "High",
            3: "Medium",
            5: "Low",
            10: "Terrible",
            20: "Abysmal",
            30: "Excrutiatingly Bad",
        }.get(detail, detail)
    
    def colorscheme_string(self):
        return self.params.split("|")[0].title()
    
    def set_error(self, error):
        self.error = error
        self.failed = datetime.datetime.utcnow()
        self.save()
    
    @classmethod
    def queue(cls):
        return cls.objects.filter(requested__isnull=False, started__isnull=True, failed__isnull=True).order_by("requested")


class Node(models.Model):
    
    """Represents a processing node, i.e. something that either downloads or renders data."""
    
    nodename = models.CharField('Node name', max_length=100, unique=True)
    salt = models.CharField('Password salt', max_length=20)
    hash = models.CharField('Password hash', max_length=100)
    
    disabled = models.BooleanField(default=False)
    lastseen = models.DateTimeField('Last seen', null=True, blank=True, default=None)
    
    def __unicode__(self):
        return "Node '%s'" % self.nodename
    
    def set_password(self, password):
        self.salt = "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for i in range(8)])
        self.hash = hashlib.sha1(self.salt + password).hexdigest()
    
    def password_matches(self, password):
        return self.hash == hashlib.sha1(self.salt + password).hexdigest()
    
    @classmethod
    def recent(cls):
        return cls.objects.filter(lastseen__gte=datetime.datetime.utcnow() - datetime.timedelta(0, 5*60))

########NEW FILE########
__FILENAME__ = storage
"""
LastGraph data storage stuff.
"""

import os
import time

# Get a pickle - the faster the better
try:
    import cPickle as pickle
except ImportError:
    print "Warning: Cannot find cPickle."
    import pickle


class UserHistory(object):
    
    """
    Represents a user's listening history, with artist-week-level granularity.
    """
    
    def __init__(self, username):
        self.username = username
        self.artists = {}
        self.weeks = {}
        self.timestamp = 0
    
    def set_plays(self, artist, week, plays):
        "Set the number of plays for an artist on a week."
        if artist not in self.artists:
            self.artists[artist] = {}
        self.artists[artist][week] = plays
        if week not in self.weeks:
            self.weeks[week] = {}
        self.weeks[week][artist] = plays
    
    def delete_week(self, week):
        "Erases all plays for a week"
        if week in self.weeks:
            del self.weeks[week]
            for artist in self.artists:
                if week in self.artists[artist]:
                    del self.artists[artist][week]
    
    def get_plays(self, artist, week):
        "Gets the number of plays for an artist in a week."
        return self.artists.get(artist, {}).get(week, 0)
    
    def total_artist(self, artist):
        return sum(self.artists.get(artist, {}).values())
    
    def total_week(self, week):
        return sum(self.weeks.get(week, {}).values())
    
    def artist_plays(self, artist):
        plays = {}
        for week in self.weeks:
            plays[week] = self.artists.get(artist, {}).get(week, 0)
        return plays
    
    def week_plays(self):
        plays = {}
        for week, artists in self.weeks.items():
            plays[week] = sum(artists.values())
        return plays
    
    def has_week(self, week):
        return week in self.weeks
    
    def num_weeks(self):
        return len(self.weeks)
    
    def num_artists(self):
        return len(self.artists)
    
    def save(self, file):
        #print "Saving %s..." % self.username
        pickle.dump((self.username, self.timestamp, self.artists, self.weeks), file, -1)
    
    def save_default(self):
        self.save(open(self.get_default_path(), "w"))
    
    def load(self, file):
        try:
            self.username, self.timestamp, self.artists, self.weeks = pickle.load(file)
        except EOFError:
            raise ValueError("Invalid pickle file '%s'" % file)
        #print "Loading %s..." % self.username
    
    def load_default(self):
        self.load(open(self.get_default_path(), "r"))
    
    def has_file(self):
        return os.path.isfile(self.get_default_path())
    
    def set_timestamp(self, ttime=None):
        if ttime is None:
            ttime = time.time()
        self.timestamp = ttime
    
    def data_age(self):
        return time.time() - self.timestamp
    
    def get_default_path(self):
        from django.conf import settings
        return os.path.join(settings.USER_DATA_ROOT, "%s.last" % self.username)
    
    def load_if_possible(self):
        if self.has_file():
            try:
                self.load_default()
            except ValueError:
                pass




########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
	
	# Front page
	(r'^$', 'lastgui.views.front'),
	
	# Help text, etc.
	(r'^about/$', 'django.views.generic.simple.direct_to_template', {'template': 'about.html'}),
	(r'^about/posters/$', 'django.views.generic.simple.direct_to_template', {'template': 'about_posters.html'}),
	(r'^about/posters/colours/$', 'django.views.generic.simple.direct_to_template', {'template': 'about_colours.html'}),
	(r'^about/artists/$', 'django.views.generic.simple.direct_to_template', {'template': 'about_artist_histories.html'}),
	(r'^crossdomain.xml$', 'django.views.generic.simple.direct_to_template', {'template': 'crossdomain.xml'}),
	
	# System status
	(r'^status/$', 'lastgui.views.status'),
	(r'^status/nagios/fetch/$', 'lastgui.views.status_nagios_fetch'),
	(r'^status/nagios/render/$', 'lastgui.views.status_nagios_render'),
	
	# User views
	(r'^user/([^/]+)/$', 'lastgui.views.user_root'),
	(r'^user/([^/]+)/artists/$', 'lastgui.views.user_artists'),
	(r'^user/([^/]+)/artist/(.*)/$', 'lastgui.views.user_artist'),
	(r'^user/([^/]+)/timeline/$', 'lastgui.views.user_timeline'),
	(r'^user/([^/]+)/posters/$', 'lastgui.views.user_posters'),
	(r'^user/([^/]+)/export/$', 'lastgui.views.user_export'),
	(r'^user/([^/]+)/premium/$', 'lastgui.views.user_premium'),
	(r'^user/([^/]+)/premium/paid/$', 'lastgui.views.user_premium_paid'),
	(r'^user/([^/]+)/sigs/$', 'lastgui.views.user_sigs'),
	
	(r'^user/([^/]+)/export/all\.json$', 'lastgui.views.user_export_all_json'),
	(r'^user/([^/]+)/export/all\.(csv|xls)$', 'lastgui.views.user_export_all_tabular'),
	(r'^user/([^/]+)/export/artist/(.*)\.json$', 'lastgui.views.user_export_artist_json'),
	(r'^user/([^/]+)/export/artist/(.*)\.(csv|xls)$', 'lastgui.views.user_export_artist_tabular'),
	
	# Ajax stuff
	(r'^ajax/([^/]+)/ready/$', 'lastgui.views.ajax_user_ready'),
	(r'^ajax/([^/]+)/queuepos/$', 'lastgui.views.ajax_user_queuepos'),
	
	# Graphs
	(r'^graph/([^/]+)/artist/([^/]+)/$', 'lastgui.views.graph_artist'),
	(r'^graph/([^/]+)/artist/([^/]+)/(\d+)/(\d+)/$', 'lastgui.views.graph_artist'),
	(r'^graph/([^/]+)/timeline/(\d+)/(\d+)/$', 'lastgui.views.graph_timeline'),
	(r'^graph/([^/]+)/timeline-basic/(\d+)/(\d+)/$', 'lastgui.views.graph_timeline_basic'),
	
	# Sigs
	(r'^graph/([^/]+)/sig1/$', 'lastgui.views.graph_sig1'),
	(r'^graph/([^/]+)/sig1/(\d+)/(\d+)/$', 'lastgui.views.graph_sig1'),
	
	# Render API
	(r'^api/$', 'lastgui.api.index'),
	(r'^api/render/next/$', 'lastgui.api.render_next'),
	(r'^api/render/data/(\d+)/$', 'lastgui.api.render_data'),
	(r'^api/render/links/$', 'lastgui.api.render_links'),
	(r'^api/render/failed/$', 'lastgui.api.render_failed'),
)
########NEW FILE########
__FILENAME__ = views

import datetime
from urlparse import urlparse

from shortcuts import *

from lastgui.models import *
from lastgui.storage import UserHistory
from lastgui.fetch import fetcher
from lastgui.data import hotlink_png

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django import forms

from lastgui.export import as_filetype


def user_ready(username):
    if username.endswith(".php"):
        return False
    
    uh = UserHistory(username)
    
    # First, check to see if the file is fresh
    uh.load_if_possible()
    if uh.data_age() < settings.HISTORY_TTL:
        return uh.num_weeks()
    
    # Then, do a quick weeklist fetch to compare
    try:
        weeks = list(fetcher.weeks(username))
    except AssertionError:  # They probably don't exist
        return None
    
    present = True
    for start, end in weeks:
        if not uh.has_week(start):
            present = False
            break
    
    # If all weeks were present, update the timestamp
    if present:
        uh.set_timestamp()
        uh.save_default()
        return len(weeks)
    else:
        return False


def referrer_limit(ofunc):
    def nfunc(request, username, *a, **kw):
        referrer = request.META.get('HTTP_REFERER', None)
        if referrer:
            protocol, host, path, params, query, frag = urlparse(referrer)
            if host != request.META['HTTP_HOST']:
                user = LastFmUser.by_username(username)
                if not user.external_allowed():
                    return HttpResponse(hotlink_png, mimetype="image/png")
        return ofunc(request, username, *a, **kw)
    return nfunc


def ready_or_update(username):
    
    ready = user_ready(username)
    if ready is False:  # We need to update their data
        lfuser = LastFmUser.by_username(username)
        if not lfuser.requested_update:
            lfuser.requested_update = datetime.datetime.utcnow()
            lfuser.last_check = datetime.datetime.utcnow()
            lfuser.save()
    
    return ready


def ajax_user_ready(request, username):
    "Returns if the given user's data is in the system ready for lastgraph."
    
    ready = ready_or_update(username)
    
    return jsonify(ready)


def ajax_user_queuepos(request, username):
    "Returns what number the user is in the request queue."
    
    try:
        return jsonify(list(LastFmUser.queue()).index(LastFmUser.by_username(username)) + 1)
    except (ValueError, IndexError):
        return jsonify(None)


### Graphs ###

from graphication import FileOutput, Series, SeriesSet, AutoWeekDateScale, Label
from graphication.wavegraph import WaveGraph
from lastgui.css import artist_detail_css, artist_detail_white_css, basic_timeline_css, sig1_css


def stream_graph(output):
    response = HttpResponse(mimetype="image/png")
    response.write(output.stream("png").read())
    return response


@referrer_limit
@cache_page(60 * 15)
def graph_artist(request, username, artist, width=800, height=300):
    
    ready_or_update(username)
    
    width = int(width)
    height = int(height)
    
    if not width:
        width=800
    
    if not height:
        width=300
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    series_set = SeriesSet()
    series_set.add_series(Series(
        artist,
        uh.artist_plays(artist),
        "#369f",
        {0:4},
    ))
    
    # Create the output
    output = FileOutput(padding=0, style=artist_detail_white_css)
    
    try:
        scale = AutoWeekDateScale(series_set, short_labels=True, month_gap=2)
    except ValueError:
        raise Http404("Bad data (ValueError)")
    
    # OK, render that.
    wg = WaveGraph(series_set, scale, artist_detail_white_css, False, vertical_scale=True)
    output.add_item(wg, x=0, y=0, width=width, height=height)
    
    # Save the images
    return stream_graph(output)


def graph_timeline_data(username):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    series_set = SeriesSet()
    series_set.add_series(Series(
        "Plays",
        uh.week_plays(),
        "#369f",
        {0:4},
    ))
    
    return series_set


@referrer_limit
@cache_page(60 * 15)
def graph_timeline(request, username, width=800, height=300):
    
    ready_or_update(username)
    
    width = int(width)
    height = int(height)
    
    if not width:
        width = 800
    
    if not height:
        height = 300
    
    series_set = graph_timeline_data(username)
    
    # Create the output
    output = FileOutput(padding=0, style=artist_detail_white_css)
    try:
        scale = AutoWeekDateScale(series_set, short_labels=True, month_gap=2)
    except ValueError:
        raise Http404("No data")
    
    # OK, render that.
    wg = WaveGraph(series_set, scale, artist_detail_white_css, False, vertical_scale=True)
    output.add_item(wg, x=0, y=0, width=width, height=height)
    
    # Save the images
    try:
        return stream_graph(output)
    except ValueError:
        raise Http404("No data")


@referrer_limit
@cache_page(60 * 15)
def graph_timeline_basic(request, username, width=800, height=300):
    
    ready_or_update(username)
    
    width = int(width)
    height = int(height)
    
    if not width:
        width = 1280
    
    if not height:
        height = 50
    
    series_set = graph_timeline_data(username)
    series_set.get_series(0).color = "3695"
    
    # Create the output
    output = FileOutput(padding=0, style=basic_timeline_css)
    try:
        scale = AutoWeekDateScale(series_set, short_labels=True)
    except ValueError:
        raise Http404("No data")
    
    # OK, render that.
    wg = WaveGraph(series_set, scale, basic_timeline_css, False, vertical_scale=False)
    output.add_item(wg, x=0, y=0, width=width, height=height)
    
    # Save the images
    try:
        return stream_graph(output)
    except ValueError:
        raise Http404("No data")



@referrer_limit
@cache_page(60 * 15)
def graph_sig1(request, username, width=300, height=100):
    
    ready_or_update(username)
    
    width = int(width)
    height = int(height)
    
    if not width:
        width = 300
    
    if not height:
        height = 100
    
    series_set = graph_timeline_data(username)
    series_set.get_series(0).color = "3695"
    
    # Create the output
    output = FileOutput(padding=0, style=sig1_css)
    try:
        scale = AutoWeekDateScale(series_set, short_labels=True)
    except ValueError:
        raise Http404("No data")
    
    # OK, render that.
    
    lb = Label(username, sig1_css)
    output.add_item(lb, x=10, y=20-(height/2), width=width, height=height)
    wg = WaveGraph(series_set, scale, sig1_css, False, vertical_scale=False)
    output.add_item(wg, x=0, y=0, width=width, height=height)
    
    # Save the images
    try:
        return stream_graph(output)
    except ValueError:
        raise Http404("No data")



def front(request):
    
    return render(request, "front.html", {
        "recent": LastFmUser.objects.filter(requested_update__isnull=True).order_by("-last_check")[:5],
    })


def status(request):
    
    return render(request, "status.html", {
        "fetchqueue": LastFmUser.queue(),
        "renderqueue": Poster.queue(),
        "numprofiles": LastFmUser.objects.count(),
        "numposters": Poster.objects.count(),
        "recentposters": Poster.objects.filter(completed__isnull=False).order_by("-completed")[:10],
        "nodes": Node.recent(),
    })


def status_nagios_fetch(request):
    
    return HttpResponse(str(LastFmUser.queue().count()))


def status_nagios_render(request):
    
    return HttpResponse(str(Poster.queue().count()))



def user_root(request, username):
    
    ready = ready_or_update(username)
    if not ready:
        flash(request, "This user's data is currently out-of-date, and is being updated.")
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    lfuser = LastFmUser.by_username(username)
    
    return render(request, "user_root.html", {"username": username, "num_weeks": len(uh.weeks), "lfuser": lfuser})




def user_sigs(request, username):
    
    lfuser = LastFmUser.by_username(username)
    
    if not lfuser.external_allowed():
        raise Http404("No premium account")
    
    return render(request, "user_sigs.html", {"username": username, "lfuser": lfuser})




def user_artists(request, username):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    artists = [(sum(weeks.values()), artist) for artist, weeks in uh.artists.items()]
    artists.sort()
    artists.reverse()
    
    try:
        max_plays = float(artists[0][0])
    except IndexError:
        max_plays = 1000
    
    artists = [(plays, artist, 100*plays/max_plays) for plays, artist in artists]
    
    return render(request, "user_artists.html", {"username": username, "artists": artists})




def user_artist(request, username, artist):
    
    return render(request, "user_artist.html", {"username": username, "artist": artist})




def user_timeline(request, username):
    
    return render(request, "user_timeline.html", {"username": username})



def user_export(request, username):
    
    return render(request, "user_export.html", {"username": username})



def user_premium(request, username):
    
    lfuser = LastFmUser.by_username(username)
    
    return render(request, "user_premium.html", {"username": username, "lfuser": lfuser})



def user_premium_paid(request, username):
    
    lfuser = LastFmUser.by_username(username)
    
    return render(request, "user_premium_paid.html", {"username": username, "lfuser": lfuser})



def user_export_all_tabular(request, username, filetype):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    data = [(("Week", {"bold":True}),("Artist", {"bold":True}),("Plays", {"bold":True}))]
    for week, artists in uh.weeks.items():
        for artist, plays in artists.items():
            data.append((week, artist, plays))
    
    try:
        return as_filetype(data, filetype, filename="%s_all" % username)
    except KeyError:
        raise Http404("No such filetype")


def user_export_all_json(request, username):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    return jsonify({"username": username, "weeks":uh.weeks})


def user_export_artist_tabular(request, username, artist, filetype):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    data = [(("Week", {"bold":True}),("Plays", {"bold":True}))]
    try:
        for week, plays in uh.artists[artist].items():
            data.append((week, plays))
    except KeyError:
        raise Http404("No such artist.")
    
    try:
        return as_filetype(data, filetype, filename="%s_%s" % (username, artist))
    except KeyError:
        raise Http404("No such filetype")


def user_export_artist_json(request, username, artist):
    
    uh = UserHistory(username)
    uh.load_if_possible()
    
    try:
        return jsonify({"username": username, "artist":artist, "weeks":uh.artists[artist]})
    except KeyError:
        raise Http404("No such artist.")



class NewPosterForm(forms.Form):
    
    start = forms.DateField(input_formats=("%Y/%m/%d",))
    end = forms.DateField(input_formats=("%Y/%m/%d",))
    
    style = forms.ChoiceField(choices=(
        ("ocean", "Ocean"),
        ("blue", "Blue"),
        ("desert", "Desert"),
        ("rainbow", "Rainbow"),
        ("sunset", "Sunset"),
        ("green", "Green"),
        ("eclectic", "Eclectic"),
    ))
    
    detail = forms.ChoiceField(choices=(
        ("1", "Super"),
        ("2", "High"),
        ("3", "Medium"),
        ("5", "Low"),
        ("10", "Terrible"),
        ("20", "Abysmal"),
        ("30", "Excrutiatingly Bad"),
    ))


def user_posters(request, username):
    
    user = LastFmUser.by_username(username)
    
    if "style" in request.POST:
        form = NewPosterForm(request.POST)
        if form.is_valid():
            poster = Poster(
                user = user,
                start = form.cleaned_data['start'],
                end = form.cleaned_data['end'],
                params = "%s|%s" % (form.cleaned_data['style'], form.cleaned_data['detail']),
                requested = datetime.datetime.now(),
            )
            poster.save()
            flash(request, "Poster request submitted. It is in queue position %i." % poster.queue_position())
            del form
            return HttpResponseRedirect("/user/%s/posters/?added=true" % username)
    
    if "form" not in locals():
        form = NewPosterForm({
            "start": (datetime.date.today() - datetime.timedelta(365)).strftime("%Y/%m/%d"),
            "end": datetime.date.today().strftime("%Y/%m/%d"),
            "detail": "3",
            "style": "ocean",
        })
    
    posters = user.posters.exclude(pdf_url="expired").order_by("-requested")
    
    return render(request, "user_posters.html", {
        "username": username,
        "posters": posters,
        "form": form,
    })

########NEW FILE########
__FILENAME__ = xml
"""
Last.fm XML parser
"""

import sys

from BeautifulSoup import BeautifulStoneSoup
import htmllib

def unescape(s):
	p = htmllib.HTMLParser(None)
	p.save_bgn()
	p.feed(s)
	return p.save_end()


def week_list(xml):
	
	soup = BeautifulStoneSoup(xml)
	
	# Check this is the right thing
	assert soup.find("weeklychartlist"), "week_list did not get a Weekly Chart List"
	
	for tag in soup.findAll("chart"):
		yield int(tag['from']), int(tag['to'])


def weekly_artists(xml):
	soup = BeautifulStoneSoup(xml)
	
	# Check this is the right thing
	try:
		assert soup.find("weeklyartistchart"), "weekly_artists did not get a Weekly Artist Chart"
	except AssertionError:
		print >> sys.stderr, xml
		raise AssertionError("weekly_artists did not get a Weekly Artist Chart")
	
	# Get the artists
	for tag in soup.findAll("artist"):
		name = str(tag.find("name").string).decode("utf8")
		playtag = tag.find("playcount")
		if playtag:
			plays = long(playtag.string)
		else:
			plays = float(tag.find("weight").string)
		yield unescape(name), plays
	

########NEW FILE########
__FILENAME__ = renderer
#!/usr/bin/python

"""
LastGraph rendering client
"""

import sys
import os
import json
import urllib
from httppost import posturl, extract_django_error
from graphication import FileOutput, Series, SeriesSet, Label, AutoWeekDateScale, Colourer, css
from graphication.wavegraph import WaveGraph


def render_poster():
    from settings import apiurl, local_store, local_store_url, nodename, nodepwd

    DEBUG = "--debug" in sys.argv
    GDEBUG = "--gdebug" in sys.argv
    TEST = "--test" in sys.argv
    PROXYUPLOAD = "--proxyupload" in sys.argv

    if "--" not in sys.argv[-1] and TEST:
        SPECIFIC = int(sys.argv[-1])
    else:
        SPECIFIC = None

    print "# Welcome to the LastGraph Renderer"

    print "# This is node '%s'." % nodename
    print "# Using server '%s'." % apiurl

    def jsonfetch(url):
        """Fetches the given URL and parses it as JSON, then returns the result."""
        try:
            data = urllib.urlopen(url).read()
        except AttributeError:
            sys.exit(2001)
        if data[0] == "(" and data[-1] == ")":
            data = data[1:-1]
        try:
            return json.loads(data)
        except ValueError:
            if DEBUG:
                print extract_django_error(data)
            raise ValueError

    # See if we need to download something to render
    try:
        if SPECIFIC:
            print "~ Rendering only graph %s." % SPECIFIC
            status = jsonfetch(apiurl % "render/data/%i/?nodename=%s&password=%s" % (SPECIFIC, nodename, nodepwd))
        else:
            status = jsonfetch(apiurl % "render/next/?nodename=%s&password=%s" % (nodename, nodepwd))

    except ValueError:
        print "! Garbled server response to 'next render' query."
        sys.exit(0)

    except IOError:
        print "! Connection error to server"
        sys.exit(0)

    if "error" in status:
        print "! Error from server: '%s'" % status['error']
        sys.exit(0)

    elif "id" in status:

        try:
            id = status['id']
            username = status['username']
            start = status['start']
            end = status['end']
            data = status['data']
            params = status['params']
            colourscheme, detail = params.split("|")
            detail = int(detail)

            print "* Rendering graph #%s for '%s' (%.1f weeks)" % (id, username, (end-start)/(86400.0*7.0))

            # Gather a list of all artists
            artists = {}
            for week_start, week_end, plays in data:
                for artist, play in plays:
                    try:
                        artist.encode("utf-8")
                        artists[artist] = {}
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        print "Bad artist!"

            # Now, get that into a set of series
            for week_start, week_end, plays in data:
                plays = dict(plays)
                for artist in artists:
                    aplays = plays.get(artist, 0)
                    if aplays < detail:
                        aplays = 0
                    artists[artist][week_end] = aplays

            series_set = SeriesSet()
            for artist, plays in artists.items():
                series_set.add_series(Series(artist, plays))

            # Create the output
            output = FileOutput()

            import lastgraph_css as style

            # We'll have major lines every integer, and minor ones every half
            scale = AutoWeekDateScale(series_set)

            # Choose an appropriate colourscheme
            c1, c2 = {
                "ocean": ("#334489", "#2d8f3c"),
                "blue": ("#264277", "#338a8c"),
                "desert": ("#ee6800", "#fce28d"),
                "rainbow": ("#ff3333", "#334489"),
                "sunset": ("#aa0000", "#ff8800"),
                "green": ("#44ff00", "#264277"),
                "eclectic": ("#510F7A", "#FFc308"),
            }[colourscheme]

            style = style.merge(css.CssStylesheet.from_css("colourer { gradient-start: %s; gradient-end: %s; }" % (c1, c2)))

            # Colour that set!
            cr = Colourer(style)
            cr.colour(series_set)

            # OK, render that.
            wg = WaveGraph(series_set, scale, style, debug=GDEBUG, textfix=True)
            lb = Label(username, style)

            width = 30 * len(series_set.keys())
            output.add_item(lb, x=10, y=10, width=width-20, height=20)
            output.add_item(wg, x=0, y=40, width=width, height=300)

            # Save the images

            if TEST:
                output.write("pdf", "test.pdf")
                print "< Wrote output to test.pdf"
            else:
                pdf_stream = output.stream("pdf")
                print "* Rendered PDF"
                svgz_stream = output.stream("svgz")
                print "* Rendered SVG"
                urls = {}
                for format in ('svgz', 'pdf'):
                    filename = 'graph_%s.%s' % (id, format)
                    fileh = open(os.path.join(local_store, filename), "w")
                    fileh.write({'svgz': svgz_stream, 'pdf': pdf_stream}[format].read())
                    fileh.close()
                    urls[format] = "%s/%s" % (local_store_url.rstrip("/"), filename)

                print "< Successful. Telling server..."
                response = posturl(apiurl % "render/links/", [
                    ("nodename", nodename), ("password", nodepwd), ("id", id),
                    ("pdf_url", urls['pdf']), ("svg_url", urls['svgz']),
                ], [])
                if DEBUG:
                    print extract_django_error(response)
                print "* Done."
                if "pdf_stream" in locals():
                    pdf_stream.close()
                if "svgz_stream" in locals():
                    svgz_stream.close()

        except:
            import traceback
            traceback.print_exc()
            print "< Telling server about error..."
            if "pdf_stream" in locals():
                pdf_stream.close()
            if "svgz_stream" in locals():
                svgz_stream.close()
            try:
                jsonfetch(apiurl % "render/failed/?nodename=%s&password=%s&id=%s" % (nodename, nodepwd, id))
                response = posturl(apiurl % "render/failed/", [
                    ("nodename", nodename), ("password", nodepwd), ("id", id),
                    ("traceback", traceback.format_exc()),
                ], [])
                print "~ Done."
            except:
                print "! Server notification failed"
            sys.exit(0)

    elif "nothing" in status:
        if "skipped" in status:
            print "~ Server had to skip: %s." % status['skipped']
        else:
            print "- No graphs to render."

    if SPECIFIC:
        sys.exit(0)


if __name__ == "__main__":
    render_poster()

########NEW FILE########
__FILENAME__ = settings
import os
static_path = os.path.join(os.path.dirname(__file__), "..", "static")

apiurl = "http://localhost:8000/api/%s"

local_store = os.path.join(static_path, "graphs")
local_store_url = "http://localhost:8000/static/graphs"

nodename = "lg"
nodepwd = "lg@home"

########NEW FILE########
__FILENAME__ = slice
#!/usr/bin/python
import os
import sys
import web
import time
import random
import datetime
import threading
from StringIO import StringIO

FILEROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(FILEROOT, ".."))
sys.path.insert(1, os.path.join(FILEROOT, "..", "lib"))

os.environ['DJANGO_SETTINGS_MODULE'] = "settings"

from colorsys import *

from graphication import *
from graphication.wavegraph import WaveGraph
from graphication.color import hex_to_rgba

from PIL import Image

import lastslice.shortslice_css as slice_style
import lastslice.longslice_css as long_style

from lastgui.fetch import fetcher

from django.core.cache import cache


errfile = open("/tmp/sliceerr.txt", "a")

urls = (
    "/slice/([^/]+)/", "Slice",
    "/slice/([^/]+)/(\d+)/(\d+)/", "Slice",
    "/slice/([^/]+)/(\d+)/(\d+)/([^/]+)/", "Slice",
    "/longslice/([^/]+)/", "LongSlice",
    "/longslice/([^/]+)/.pdf", "LongSlicePDF",
    "/longslice/([^/]+)/(\d+)/(\d+)/", "LongSlice",
    "/longslice/([^/]+)/(\d+)/(\d+)/([^/]+)/", "LongSlice",
    "/colours/([^/]+)/", "Colours",
)
fetcher.debug = False

class DataError(StandardError): pass


def rgba_to_hex(r, g, b, a):
    return "%02x%02x%02x%02x" % (r*255,g*255,b*255,a*255)


class ThreadedWeek(threading.Thread):
    
    def __init__(self, user, start, end):
        threading.Thread.__init__(self)
        self.user = user
        self.range = start, end
    
    def run(self):
        self.data = list(fetcher.weekly_artists(self.user, self.range[0], self.range[1]))


def get_data(user, length=4):
    
    cache_key = 'user_%s:%s' % (length, user.replace(" ","+"))
    
    data = None #cache.get(cache_key)
    while data == "locked":
        time.sleep(0.01)
    
    if not data:
        
        #cache.set(cache_key, "locked", 5)
        try:
            weeks = list(fetcher.weeks(user))
        except:
            import traceback
            try:
                errfile.write(traceback.format_exc())
                errfile.flush()
            except:
                pass
            return None, None
        threads = [ThreadedWeek(user, start, end) for start, end in weeks[-length:]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        data = ([thread.data for thread in threads], weeks[-length:])
    
    #cache.set(cache_key, data, 30)
    
    return data


def get_series(user, length=4, limit=15):

    if ":" in user:
        user = user.replace("_", "+")
        
    data, weeks = get_data(user, length)

    if not data and not weeks:
        data, weeks = get_data(user, length)
        if not data and not weeks:
            data, weeks = get_data(user, length)
            if not data and not weeks:
                return None
    
    artists = {}
        
    for week in data:
        for artist, plays in week:
            artists[artist] = []
    
    for week in data:
        week = dict(week)
        for artist in artists:
            plays = week.get(artist, 0)
            if plays < 2:
                plays = 0
            artists[artist].append(plays)
    
    artists = artists.items()
    artists.sort(key=lambda (x,y):max(y))
    artists.reverse()
    
    sh, ss, sv = rgb_to_hsv(*hex_to_rgba("ec2d60")[:3])
    eh, es, ev = rgb_to_hsv(*hex_to_rgba("0c4da2")[:3])
    a = True
    ad = 0.3
    
    th, ts, tv = (eh-sh)/float(limit), (es-ss)/float(limit), (ev-sv)/float(limit)
    
    series_set = SeriesSet()
    for artist, data in artists[:15]:
        series_set.add_series(Series(
            artist,
            dict([(datetime.datetime.fromtimestamp(weeks[i][0]), x) for i, x in enumerate(data)]),
            rgba_to_hex(*(hsv_to_rgb(sh, ss, sv) + (a and 1 or 1-ad,))),
        ))
        sh += th
        ss += ts
        sv += tv
        a = not a
        ad += (0.6/limit)
    
    return series_set


class Slice(object):
    
    def GET(self, username, width=230, height=138, labels=False):
        web.header("Content-Type", "image/png")
        
        width = int(width)
        height = int(height)
        
        series_set = get_series(username)
        output = FileOutput(padding=0, style=slice_style)
        
        if series_set:
            # Create the output
            scale = AutoWeekDateScale(series_set, short_labels=True)
        
            # OK, render that.
            wg = WaveGraph(series_set, scale, slice_style, bool(labels), vertical_scale=False)
            output.add_item(wg, x=0, y=0, width=width, height=height)
        else:
            output.add_item(Label("invalid username"), x=0, y=0, width=width, height=height)

        print output.stream('png').read()


class LongSlice(object):
    
    def GET(self, username, width=1200, height=400, labels=False):
        web.header("Content-Type", "image/png")
        
        width = int(width)
        height = int(height)
        
        series_set = get_series(username, 12, 25)
        
        # Create the output
        output = FileOutput(padding=0, style=long_style)
        
        if series_set:
            scale = AutoWeekDateScale(series_set, year_once=False)
        
            # OK, render that.
            wg = WaveGraph(series_set, scale, long_style, not bool(labels), textfix=True)
            output.add_item(wg, x=0, y=0, width=width, height=height)
        else:
            output.add_item(Label("invalid username"), x=0, y=0, width=width, height=height)


        
        # Load it into a PIL image
        img = Image.open(output.stream('png'))
        
        # Load the watermark
        mark = Image.open(os.path.join(os.path.dirname(__file__), "watermark.png"))
        
        # Combine them
        nw, nh = img.size
        nh += 40
        out = Image.new("RGB", (nw, nh), "White")
        out.paste(img, (0,0))
        out.paste(mark, (width-210, height+10))
        
        # Stream the result
        outf = StringIO()
        out.save(outf, "png")
        outf.seek(0)
        print outf.read()



class LongSlicePDF(object):
    
    def GET(self, username, width=1200, height=400, labels=False):
        web.header("Content-Type", "application/x-pdf")
        
        width = int(width)
        height = int(height)
        
        series_set = get_series(username, 12, 25)
        
        # Create the output
        output = FileOutput(padding=0, style=long_style)
        scale = AutoWeekDateScale(series_set)
        
        # OK, render that.
        wg = WaveGraph(series_set, scale, long_style, not bool(labels), textfix=True)
        output.add_item(wg, x=0, y=0, width=width, height=height)
        print output.stream('pdf').read()


class Colours:
    
     def GET(self, username):
        
        series_set = get_series(username)
        
        for series in series_set:
            print "%s,%s" % (series.title, series.color)


#web.webapi.internalerror = web.debugerror
if __name__ == "__main__": web.run(urls, globals())

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for lastgraph3 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Get our root, and make sure we can import from it.
import os
import sys
FILEROOT = os.path.dirname(__file__)
sys.path.insert(0, FILEROOT)
sys.path.insert(1, os.path.join(FILEROOT, "lib"))

ADMINS = (
    ('Andrew Godwin', 'andrew@aeracode.org'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be avilable on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# How long until we try to refresh a UserHistory
HISTORY_TTL = 86000

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

STATIC_URL = '/static/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.CacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

CACHE_MIDDLEWARE_SECONDS = 60
CACHE_MIDDLEWARE_KEY_PREFIX = "lg3"

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    "south",
    'lastgui',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "shortcuts.contexter",
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "lastgraph",
        "USER": "postgres",
    }
}

USER_DATA_ROOT = os.path.join(FILEROOT, "static", "data")

LASTFM_DELAY = 0.2


try:
    import cairo
except ImportError:
    print "You must install pycairo."
    sys.exit(1)


try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = shortcuts
import json

from django.template.loader import select_template
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect as redirect
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.http import Http404


def render(request, template, params={}):
    ctx = RequestContext(request, params)
    
    if not isinstance(template, (list, tuple)):
        template = [template]
    
    return HttpResponse(select_template(template).render(ctx))


def jsonify(object):
    return HttpResponse("(%s)" % json.dumps(object))


def plaintext(string):
    return HttpResponse(unicode(string))


def flash(request, message):
    request.session['flashes'] = request.session.get('flashes', []) + [message]


def get_flashes(request):
    flashes = request.session.get('flashes', [])
    request.session['flashes'] = []
    return flashes


def contexter(request):
    return {
        "flashes": get_flashes(request),
    }

########NEW FILE########
__FILENAME__ = test

import urllib
from lastgui.fetch import *

print update_user("andygodwin")
########NEW FILE########
__FILENAME__ = urls

import os

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/',  include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        # Static content
        (r'^static/(.*)$', 'django.views.static.serve', {'document_root': os.path.join(settings.FILEROOT, "static")}),
    )

urlpatterns += patterns('',
    # Main app
    (r'^', include('lastgui.urls')),
)

########NEW FILE########
