__FILENAME__ = uploadr
#!/usr/bin/env python

"""
   uploadr.py

   Upload images placed within a directory to your Flickr account.

   Requires:
       xmltramp http://www.aaronsw.com/2002/xmltramp/
       flickr account http://flickr.com

   Inspired by:
        http://micampe.it/things/flickruploadr

   Usage:

   The best way to use this is to just fire this up in the background and forget about it.
   If you find you have CPU/Process limits, then setup a cron job.

   %nohup python uploadr.py -d &

   cron entry (runs at the top of every hour )
   0  *  *   *   * /full/path/to/uploadr.py > /dev/null 2>&1

   September 2005
   Cameron Mallory   cmallory/berserk.org

   This code has been updated to use the new Auth API from flickr.

   You may use this code however you see fit in any form whatsoever.


"""

import argparse
import hashlib
import mimetools
import mimetypes
import os
import shelve
import string
import sys
import time
import urllib2
import webbrowser
import xmltramp

#
##
##  Items you will want to change
##

#
# Location to scan for new images
#
IMAGE_DIR = "images/"
#
#   Flickr settings
#
FLICKR = {"title": "",
        "description": "",
        "tags": "auto-upload",
        "is_public": "1",
        "is_friend": "0",
        "is_family": "0" }
#
#   How often to check for new images to upload (in seconds)
#
SLEEP_TIME = 1 * 60
#
#   Only with --drip-feed option:
#     How often to wait between uploading individual images (in seconds)
#
DRIP_TIME = 1 * 60
#
#   File we keep the history of uploaded images in.
#
HISTORY_FILE = os.path.join(IMAGE_DIR, "uploadr.history")

##
##  You shouldn't need to modify anything below here
##
FLICKR["api_key"] = os.environ['FLICKR_UPLOADR_PY_API_KEY']
FLICKR["secret"] = os.environ['FLICKR_UPLOADR_PY_SECRET']

class APIConstants:
    """ APIConstants class
    """

    base = "http://flickr.com/services/"
    rest   = base + "rest/"
    auth   = base + "auth/"
    upload = base + "upload/"

    token = "auth_token"
    secret = "secret"
    key = "api_key"
    sig = "api_sig"
    frob = "frob"
    perms = "perms"
    method = "method"

    def __init__( self ):
       """ Constructor
       """
       pass

api = APIConstants()

class Uploadr:
    """ Uploadr class
    """

    token = None
    perms = ""
    TOKEN_FILE = os.path.join(IMAGE_DIR, ".flickrToken")

    def __init__( self ):
        """ Constructor
        """
        self.token = self.getCachedToken()



    def signCall( self, data):
        """
        Signs args via md5 per http://www.flickr.com/services/api/auth.spec.html (Section 8)
        """
        keys = data.keys()
        keys.sort()
        foo = ""
        for a in keys:
            foo += (a + data[a])

        f = FLICKR[ api.secret ] + api.key + FLICKR[ api.key ] + foo
        #f = api.key + FLICKR[ api.key ] + foo
        return hashlib.md5( f ).hexdigest()

    def urlGen( self , base,data, sig ):
        """ urlGen
        """
        foo = base + "?"
        for d in data:
            foo += d + "=" + data[d] + "&"
        return foo + api.key + "=" + FLICKR[ api.key ] + "&" + api.sig + "=" + sig


    def authenticate( self ):
        """ Authenticate user so we can upload images
        """

        print("Getting new token")
        self.getFrob()
        self.getAuthKey()
        self.getToken()
        self.cacheToken()

    def getFrob( self ):
        """
        flickr.auth.getFrob

        Returns a frob to be used during authentication. This method call must be
        signed.

        This method does not require authentication.
        Arguments

        api.key (Required)
        Your API application key. See here for more details.
        """

        d = {
            api.method  : "flickr.auth.getFrob"
            }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            response = self.getResponse( url )
            if ( self.isGood( response ) ):
                FLICKR[ api.frob ] = str(response.frob)
            else:
                self.reportError( response )
        except:
            print("Error getting frob:" + str( sys.exc_info() ))

    def getAuthKey( self ):
        """
        Checks to see if the user has authenticated this application
        """
        d =  {
            api.frob : FLICKR[ api.frob ],
            api.perms : "write"
            }
        sig = self.signCall( d )
        url = self.urlGen( api.auth, d, sig )
        ans = ""
        try:
            webbrowser.open( url )
            ans = raw_input("Have you authenticated this application? (Y/N): ")
        except:
            print(str(sys.exc_info()))
        if ( ans.lower() == "n" ):
            print("You need to allow this program to access your Flickr site.")
            print("A web browser should pop open with instructions.")
            print("After you have allowed access restart uploadr.py")
            sys.exit()

    def getToken( self ):
        """
        http://www.flickr.com/services/api/flickr.auth.getToken.html

        flickr.auth.getToken

        Returns the auth token for the given frob, if one has been attached. This method call must be signed.
        Authentication

        This method does not require authentication.
        Arguments

        NTC: We need to store the token in a file so we can get it and then check it insted of
        getting a new on all the time.

        api.key (Required)
           Your API application key. See here for more details.
        frob (Required)
           The frob to check.
        """

        d = {
            api.method : "flickr.auth.getToken",
            api.frob : str(FLICKR[ api.frob ])
        }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            res = self.getResponse( url )
            if ( self.isGood( res ) ):
                self.token = str(res.auth.token)
                self.perms = str(res.auth.perms)
                self.cacheToken()
            else :
                self.reportError( res )
        except:
            print(str(sys.exc_info()))

    def getCachedToken( self ):
        """
        Attempts to get the flickr token from disk.
       """
        if ( os.path.exists( self.TOKEN_FILE )):
            return open( self.TOKEN_FILE ).read()
        else :
            return None



    def cacheToken( self ):
        """ cacheToken
        """

        try:
            open( self.TOKEN_FILE , "w").write( str(self.token) )
        except:
            print("Issue writing token to local cache ", str(sys.exc_info()))

    def checkToken( self ):
        """
        flickr.auth.checkToken

        Returns the credentials attached to an authentication token.
        Authentication

        This method does not require authentication.
        Arguments

        api.key (Required)
            Your API application key. See here for more details.
        auth_token (Required)
            The authentication token to check.
        """

        if ( self.token == None ):
            return False
        else :
            d = {
                api.token  :  str(self.token) ,
                api.method :  "flickr.auth.checkToken"
            }
            sig = self.signCall( d )
            url = self.urlGen( api.rest, d, sig )
            try:
                res = self.getResponse( url )
                if ( self.isGood( res ) ):
                    self.token = res.auth.token
                    self.perms = res.auth.perms
                    return True
                else :
                    self.reportError( res )
            except:
                print(str(sys.exc_info()))
            return False


    def upload( self ):
        """ upload
        """

        newImages = self.grabNewImages()
        if ( not self.checkToken() ):
            self.authenticate()
        self.uploaded = shelve.open( HISTORY_FILE )
        for i, image in enumerate( newImages ):
            success = self.uploadImage( image )
            if args.drip_feed and success and i != len( newImages )-1:
                print("Waiting " + str(DRIP_TIME) + " seconds before next upload")
                time.sleep( DRIP_TIME )
        self.uploaded.close()

    def grabNewImages( self ):
        """ grabNewImages
        """

        images = []
        foo = os.walk( IMAGE_DIR )
        for data in foo:
            (dirpath, dirnames, filenames) = data
            for f in filenames :
                ext = f.lower().split(".")[-1]
                if ( ext == "jpg" or ext == "gif" or ext == "png" ):
                    images.append( os.path.normpath( dirpath + "/" + f ) )
        images.sort()
        return images


    def uploadImage( self, image ):
        """ uploadImage
        """

        success = False
        if ( not self.uploaded.has_key( image ) ):
            print("Uploading " + image + "...")
            try:
                photo = ('photo', image, open(image,'rb').read())
                if args.title: # Replace
                    FLICKR["title"] = args.title
                if args.description: # Replace
                    FLICKR["description"] = args.description
                if args.tags: # Append
                    FLICKR["tags"] += " " + args.tags + " "
                d = {
                    api.token       : str(self.token),
                    api.perms       : str(self.perms),
                    "title"         : str( FLICKR["title"] ),
                    "description"   : str( FLICKR["description"] ),
                    "tags"          : str( FLICKR["tags"] ),
                    "is_public"     : str( FLICKR["is_public"] ),
                    "is_friend"     : str( FLICKR["is_friend"] ),
                    "is_family"     : str( FLICKR["is_family"] )
                }
                sig = self.signCall( d )
                d[ api.sig ] = sig
                d[ api.key ] = FLICKR[ api.key ]
                url = self.build_request(api.upload, d, (photo,))
                xml = urllib2.urlopen( url ).read()
                res = xmltramp.parse(xml)
                if ( self.isGood( res ) ):
                    print("Success.")
                    self.logUpload( res.photoid, image )
                    success = True
                else :
                    print("Problem:")
                    self.reportError( res )
            except:
                print(str(sys.exc_info()))
        return success

    def logUpload( self, photoID, imageName ):
        """ logUpload
        """

        photoID = str( photoID )
        imageName = str( imageName )
        self.uploaded[ imageName ] = photoID
        self.uploaded[ photoID ] = imageName

    def build_request(self, theurl, fields, files, txheaders=None):
        """
        build_request/encode_multipart_formdata code is from www.voidspace.org.uk/atlantibots/pythonutils.html

        Given the fields to set and the files to encode it returns a fully formed urllib2.Request object.
        You can optionally pass in additional headers to encode into the opject. (Content-type and Content-length will be overridden if they are set).
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.
        """

        content_type, body = self.encode_multipart_formdata(fields, files)
        if not txheaders: txheaders = {}
        txheaders['Content-type'] = content_type
        txheaders['Content-length'] = str(len(body))

        return urllib2.Request(theurl, body, txheaders)

    def encode_multipart_formdata(self,fields, files, BOUNDARY = '-----'+mimetools.choose_boundary()+'-----'):
        """ Encodes fields and files for uploading.
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.
        Return (content_type, body) ready for urllib2.Request instance
        You can optionally pass in a boundary string to use or we'll let mimetools provide one.
        """

        CRLF = '\r\n'
        L = []
        if isinstance(fields, dict):
            fields = fields.items()
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            filetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % filetype)
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY        # XXX what if no files are encoded
        return content_type, body


    def isGood( self, res ):
        """ isGood
        """

        if ( not res == "" and res('stat') == "ok" ):
            return True
        else :
            return False


    def reportError( self, res ):
        """ reportError
        """

        try:
            print("Error: " + str( res.err('code') + " " + res.err('msg') ))
        except:
            print("Error: " + str( res ))

    def getResponse( self, url ):
        """
        Send the url and get a response.  Let errors float up
        """

        xml = urllib2.urlopen( url ).read()
        return xmltramp.parse( xml )


    def run( self ):
        """ run
        """

        while ( True ):
            self.upload()
            print("Last check: " + str( time.asctime(time.localtime())))
            time.sleep( SLEEP_TIME )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload images to Flickr.')
    parser.add_argument('-d', '--daemon', action='store_true',
        help='Run forever as a daemon')
    parser.add_argument('-i', '--title',       action='store',
        help='Title for uploaded images')
    parser.add_argument('-e', '--description', action='store',
        help='Description for uploaded images')
    parser.add_argument('-t', '--tags',        action='store',
        help='Space-separated tags for uploaded images')
    parser.add_argument('-r', '--drip-feed',   action='store_true',
        help='Wait a bit between uploading individual images')
    args = parser.parse_args()

    flick = Uploadr()

    if args.daemon:
        flick.run()
    else:
        flick.upload()

########NEW FILE########
__FILENAME__ = xmltramp
"""xmltramp: Make XML documents easily accessible."""

__version__ = "2.16"
__author__ = "Aaron Swartz"
__credits__ = "Many thanks to pjz, bitsko, and DanC."
__copyright__ = "(C) 2003 Aaron Swartz. GNU GPL 2."

if not hasattr(__builtins__, 'True'): True, False = 1, 0
def isstr(f): return isinstance(f, type('')) or isinstance(f, type(u''))
def islst(f): return isinstance(f, type(())) or isinstance(f, type([]))

empty = {'http://www.w3.org/1999/xhtml': ['img', 'br', 'hr', 'meta', 'link', 'base', 'param', 'input', 'col', 'area']}

def quote(x, elt=True):
	if elt and '<' in x and len(x) > 24 and x.find(']]>') == -1: return "<![CDATA["+x+"]]>"
	else: x = x.replace('&', '&amp;').replace('<', '&lt;').replace(']]>', ']]&gt;')
	if not elt: x = x.replace('"', '&quot;')
	return x

class Element:
	def __init__(self, name, attrs=None, children=None, prefixes=None):
		if islst(name) and name[0] == None: name = name[1]
		if attrs:
			na = {}
			for k in attrs.keys():
				if islst(k) and k[0] == None: na[k[1]] = attrs[k]
				else: na[k] = attrs[k]
			attrs = na
		
		self._name = name
		self._attrs = attrs or {}
		self._dir = children or []
		
		prefixes = prefixes or {}
		self._prefixes = dict(zip(prefixes.values(), prefixes.keys()))
		
		if prefixes: self._dNS = prefixes.get(None, None)
		else: self._dNS = None
	
	def __repr__(self, recursive=0, multiline=0, inprefixes=None):
		def qname(name, inprefixes): 
			if islst(name):
				if inprefixes[name[0]] is not None:
					return inprefixes[name[0]]+':'+name[1]
				else:
					return name[1]
			else:
				return name
		
		def arep(a, inprefixes, addns=1):
			out = ''

			for p in self._prefixes.keys():
				if not p in inprefixes.keys():
					if addns: out += ' xmlns'
					if addns and self._prefixes[p]: out += ':'+self._prefixes[p]
					if addns: out += '="'+quote(p, False)+'"'
					inprefixes[p] = self._prefixes[p]
			
			for k in a.keys():
				out += ' ' + qname(k, inprefixes)+ '="' + quote(a[k], False) + '"'
			
			return out
		
		inprefixes = inprefixes or {u'http://www.w3.org/XML/1998/namespace':'xml'}
		
		# need to call first to set inprefixes:
		attributes = arep(self._attrs, inprefixes, recursive) 
		out = '<' + qname(self._name, inprefixes)  + attributes 
		
		if not self._dir and (self._name[0] in empty.keys() 
		  and self._name[1] in empty[self._name[0]]):
			out += ' />'
			return out
		
		out += '>'

		if recursive:
			content = 0
			for x in self._dir: 
				if isinstance(x, Element): content = 1
				
			pad = '\n' + ('\t' * recursive)
			for x in self._dir:
				if multiline and content: out +=  pad 
				if isstr(x): out += quote(x)
				elif isinstance(x, Element):
					out += x.__repr__(recursive+1, multiline, inprefixes.copy())
				else:
					raise TypeError, "I wasn't expecting "+`x`+"."
			if multiline and content: out += '\n' + ('\t' * (recursive-1))
		else:
			if self._dir: out += '...'
		
		out += '</'+qname(self._name, inprefixes)+'>'
			
		return out
	
	def __unicode__(self):
		text = ''
		for x in self._dir:
			text += unicode(x)
		return ' '.join(text.split())
		
	def __str__(self):
		return self.__unicode__().encode('utf-8')
	
	def __getattr__(self, n):
		if n[0] == '_': raise AttributeError, "Use foo['"+n+"'] to access the child element."
		if self._dNS: n = (self._dNS, n)
		for x in self._dir:
			if isinstance(x, Element) and x._name == n: return x
		raise AttributeError, 'No child element named \''+n+"'"
		
	def __hasattr__(self, n):
		for x in self._dir:
			if isinstance(x, Element) and x._name == n: return True
		return False
		
 	def __setattr__(self, n, v):
		if n[0] == '_': self.__dict__[n] = v
		else: self[n] = v
 

	def __getitem__(self, n):
		if isinstance(n, type(0)): # d[1] == d._dir[1]
			return self._dir[n]
		elif isinstance(n, slice(0).__class__):
			# numerical slices
			if isinstance(n.start, type(0)): return self._dir[n.start:n.stop]
			
			# d['foo':] == all <foo>s
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)
			out = []
			for x in self._dir:
				if isinstance(x, Element) and x._name == n: out.append(x) 
			return out
		else: # d['foo'] == first <foo>
			if self._dNS and not islst(n): n = (self._dNS, n)
			for x in self._dir:
				if isinstance(x, Element) and x._name == n: return x
			raise KeyError
	
	def __setitem__(self, n, v):
		if isinstance(n, type(0)): # d[1]
			self._dir[n] = v
		elif isinstance(n, slice(0).__class__):
			# d['foo':] adds a new foo
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)

			nv = Element(n)
			self._dir.append(nv)
			
		else: # d["foo"] replaces first <foo> and dels rest
			if self._dNS and not islst(n): n = (self._dNS, n)

			nv = Element(n); nv._dir.append(v)
			replaced = False

			todel = []
			for i in range(len(self)):
				if self[i]._name == n:
					if replaced:
						todel.append(i)
					else:
						self[i] = nv
						replaced = True
			if not replaced: self._dir.append(nv)
			for i in todel: del self[i]

	def __delitem__(self, n):
		if isinstance(n, type(0)): del self._dir[n]
		elif isinstance(n, slice(0).__class__):
			# delete all <foo>s
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)
			
			for i in range(len(self)):
				if self[i]._name == n: del self[i]
		else:
			# delete first foo
			for i in range(len(self)):
				if self[i]._name == n: del self[i]
				break
	
	def __call__(self, *_pos, **_set): 
		if _set:
			for k in _set.keys(): self._attrs[k] = _set[k]
		if len(_pos) > 1:
			for i in range(0, len(_pos), 2):
				self._attrs[_pos[i]] = _pos[i+1]
		if len(_pos) == 1 is not None:
			return self._attrs[_pos[0]]
		if len(_pos) == 0:
			return self._attrs

	def __len__(self): return len(self._dir)

class Namespace:
	def __init__(self, uri): self.__uri = uri
	def __getattr__(self, n): return (self.__uri, n)
	def __getitem__(self, n): return (self.__uri, n)

from xml.sax.handler import EntityResolver, DTDHandler, ContentHandler, ErrorHandler

class Seeder(EntityResolver, DTDHandler, ContentHandler, ErrorHandler):
	def __init__(self):
		self.stack = []
		self.ch = ''
		self.prefixes = {}
		ContentHandler.__init__(self)
		
	def startPrefixMapping(self, prefix, uri):
		if not self.prefixes.has_key(prefix): self.prefixes[prefix] = []
		self.prefixes[prefix].append(uri)
	def endPrefixMapping(self, prefix):
		self.prefixes[prefix].pop()
	
	def startElementNS(self, name, qname, attrs):
		ch = self.ch; self.ch = ''	
		if ch and not ch.isspace(): self.stack[-1]._dir.append(ch)

		attrs = dict(attrs)
		newprefixes = {}
		for k in self.prefixes.keys(): newprefixes[k] = self.prefixes[k][-1]
		
		self.stack.append(Element(name, attrs, prefixes=newprefixes.copy()))
	
	def characters(self, ch):
		self.ch += ch
	
	def endElementNS(self, name, qname):
		ch = self.ch; self.ch = ''
		if ch and not ch.isspace(): self.stack[-1]._dir.append(ch)
	
		element = self.stack.pop()
		if self.stack:
			self.stack[-1]._dir.append(element)
		else:
			self.result = element

from xml.sax import make_parser
from xml.sax.handler import feature_namespaces

def seed(fileobj):
	seeder = Seeder()
	parser = make_parser()
	parser.setFeature(feature_namespaces, 1)
	parser.setContentHandler(seeder)
	parser.parse(fileobj)
	return seeder.result

def parse(text):
	from StringIO import StringIO
	return seed(StringIO(text))

def load(url): 
	import urllib
	return seed(urllib.urlopen(url))

def unittest():
	parse('<doc>a<baz>f<b>o</b>ob<b>a</b>r</baz>a</doc>').__repr__(1,1) == \
	  '<doc>\n\ta<baz>\n\t\tf<b>o</b>ob<b>a</b>r\n\t</baz>a\n</doc>'
	
	assert str(parse("<doc />")) == ""
	assert str(parse("<doc>I <b>love</b> you.</doc>")) == "I love you."
	assert parse("<doc>\nmom\nwow\n</doc>")[0].strip() == "mom\nwow"
	assert str(parse('<bing>  <bang> <bong>center</bong> </bang>  </bing>')) == "center"
	assert str(parse('<doc>\xcf\x80</doc>')) == '\xcf\x80'
	
	d = Element('foo', attrs={'foo':'bar'}, children=['hit with a', Element('bar'), Element('bar')])
	
	try: 
		d._doesnotexist
		raise "ExpectedError", "but found success. Damn."
	except AttributeError: pass
	assert d.bar._name == 'bar'
	try:
		d.doesnotexist
		raise "ExpectedError", "but found success. Damn."
	except AttributeError: pass
	
	assert hasattr(d, 'bar') == True
	
	assert d('foo') == 'bar'
	d(silly='yes')
	assert d('silly') == 'yes'
	assert d() == d._attrs
	
	assert d[0] == 'hit with a'
	d[0] = 'ice cream'
	assert d[0] == 'ice cream'
	del d[0]
	assert d[0]._name == "bar"
	assert len(d[:]) == len(d._dir)
	assert len(d[1:]) == len(d._dir) - 1
	assert len(d['bar':]) == 2
	d['bar':] = 'baz'
	assert len(d['bar':]) == 3
	assert d['bar']._name == 'bar'
	
	d = Element('foo')
	
	doc = Namespace("http://example.org/bar")
	bbc = Namespace("http://example.org/bbc")
	dc = Namespace("http://purl.org/dc/elements/1.1/")
	d = parse("""<doc version="2.7182818284590451"
	  xmlns="http://example.org/bar" 
	  xmlns:dc="http://purl.org/dc/elements/1.1/"
	  xmlns:bbc="http://example.org/bbc">
		<author>John Polk and John Palfrey</author>
		<dc:creator>John Polk</dc:creator>
		<dc:creator>John Palfrey</dc:creator>
		<bbc:show bbc:station="4">Buffy</bbc:show>
	</doc>""")

	assert repr(d) == '<doc version="2.7182818284590451">...</doc>'
	assert d.__repr__(1) == '<doc xmlns:bbc="http://example.org/bbc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://example.org/bar" version="2.7182818284590451"><author>John Polk and John Palfrey</author><dc:creator>John Polk</dc:creator><dc:creator>John Palfrey</dc:creator><bbc:show bbc:station="4">Buffy</bbc:show></doc>'
	assert d.__repr__(1,1) == '<doc xmlns:bbc="http://example.org/bbc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://example.org/bar" version="2.7182818284590451">\n\t<author>John Polk and John Palfrey</author>\n\t<dc:creator>John Polk</dc:creator>\n\t<dc:creator>John Palfrey</dc:creator>\n\t<bbc:show bbc:station="4">Buffy</bbc:show>\n</doc>'

	assert repr(parse("<doc xml:lang='en' />")) == '<doc xml:lang="en"></doc>'

	assert str(d.author) == str(d['author']) == "John Polk and John Palfrey"
	assert d.author._name == doc.author
	assert str(d[dc.creator]) == "John Polk"
	assert d[dc.creator]._name == dc.creator
	assert str(d[dc.creator:][1]) == "John Palfrey"
	d[dc.creator] = "Me!!!"
	assert str(d[dc.creator]) == "Me!!!"
	assert len(d[dc.creator:]) == 1
	d[dc.creator:] = "You!!!"
	assert len(d[dc.creator:]) == 2
	
	assert d[bbc.show](bbc.station) == "4"
	d[bbc.show](bbc.station, "5")
	assert d[bbc.show](bbc.station) == "5"

	e = Element('e')
	e.c = '<img src="foo">'
	assert e.__repr__(1) == '<e><c>&lt;img src="foo"></c></e>'
	e.c = '2 > 4'
	assert e.__repr__(1) == '<e><c>2 > 4</c></e>'
	e.c = 'CDATA sections are <em>closed</em> with ]]>.'
	assert e.__repr__(1) == '<e><c>CDATA sections are &lt;em>closed&lt;/em> with ]]&gt;.</c></e>'
	e.c = parse('<div xmlns="http://www.w3.org/1999/xhtml">i<br /><span></span>love<br />you</div>')
	assert e.__repr__(1) == '<e><c><div xmlns="http://www.w3.org/1999/xhtml">i<br /><span></span>love<br />you</div></c></e>'	
	
	e = Element('e')
	e('c', 'that "sucks"')
	assert e.__repr__(1) == '<e c="that &quot;sucks&quot;"></e>'

	
	assert quote("]]>") == "]]&gt;"
	assert quote('< dkdkdsd dkd sksdksdfsd fsdfdsf]]> kfdfkg >') == '&lt; dkdkdsd dkd sksdksdfsd fsdfdsf]]&gt; kfdfkg >'
	
	assert parse('<x a="&lt;"></x>').__repr__(1) == '<x a="&lt;"></x>'
	assert parse('<a xmlns="http://a"><b xmlns="http://b"/></a>').__repr__(1) == '<a xmlns="http://a"><b xmlns="http://b"></b></a>'
	
if __name__ == '__main__': unittest()

########NEW FILE########
