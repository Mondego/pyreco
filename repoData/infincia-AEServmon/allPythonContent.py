__FILENAME__ = admin
#!/usr/bin/env python
# Copyright (c) 2009, Steve Oliver (steve@xercestech.com)
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY STEVE OLIVER ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STEVE OLIVER BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



import httplib
import cgi
import wsgiref.handlers
from models import Server, AdminOptions
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.db import Key
import time
import prowlpy
import datetime
import logging

class Admin(webapp.RequestHandler):
	def get(self):
		adminoptions = AdminOptions.get_by_key_name('credentials')
		if adminoptions:  
			twitterpass = adminoptions.twitterpass
			twitteruser = adminoptions.twitteruser
			prowlkey = adminoptions.prowlkey
		else:
			twitterpass = "Change Me"
			twitteruser = "Change Me"
			prowlkey = "Change Me"
		serverlist = db.GqlQuery("SELECT * FROM Server")
		user = users.get_current_user()
		template_values = {'user': user, 'twitteruser': twitteruser, 'twitterpass': twitterpass, 'serverlist': serverlist, 'prowlkey': prowlkey, 'adminoptions': adminoptions,}
		path = os.path.join(os.path.dirname(__file__), 'admin.html')
		self.response.out.write(template.render(path, template_values))
        
class StoreServer(webapp.RequestHandler):
	def post(self):	
		server = Server(key_name=self.request.get('serverdomain'))
		server.serverdomain = self.request.get('serverdomain')
		if self.request.get('ssl') == "True":
			server.ssl = True
		else:
			server.ssl = False
		if self.request.get('notifywithprowl') == "True":
			server.notifywithprowl = True
		if self.request.get('notifywithemail') == "True":
			server.notifywithemail = True
		#server.notifywithprowl = self.request.get('notifywithtwitter')
		server.email = users.get_current_user().email()
		server.put()
		self.redirect('/admin')
        
class DeleteServer(webapp.RequestHandler):
	def post(self):
		serverdomain = self.request.get('serverdomain')
		server = Server.get_by_key_name(serverdomain)
		server.delete()
		self.redirect('/admin')
        
class StoreAdminOptions(webapp.RequestHandler):
	def post(self):        
		adminoptions = AdminOptions(key_name="credentials")
		adminoptions.twitteruser = self.request.get('twitteruser')
		adminoptions.twitterpass = self.request.get('twitterpass')
		adminoptions.prowlkey = self.request.get('prowlkey')
		prowlnotifier = prowlpy.Prowl(self.request.get('prowlkey'))
		try:
			adminoptions.prowlkeyisvalid = prowlnotifier.verify_key()
		except:
			adminoptions.prowlkeyisvalid = False
		adminoptions.put()
		self.redirect('/admin')
        
        
def main():
	application = webapp.WSGIApplication([('/admin/storeserver', StoreServer),('/admin/deleteserver', DeleteServer),('/admin/storeadminoptions', StoreAdminOptions),('/admin', Admin)],debug=True)
	wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = checkservers
#!/usr/bin/env python
# Copyright (c) 2009, Steve Oliver (steve@xercestech.com)
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY STEVE OLIVER ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STEVE OLIVER BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.api.urlfetch import DownloadError

import cgi
import datetime
import time
import logging
import wsgiref.handlers

from models import Server, AdminOptions
import prowlpy
#import twitter

class CheckServers(webapp.RequestHandler):
	serverlist = db.GqlQuery("SELECT * FROM Server")
	adminoptions = AdminOptions.get_by_key_name('credentials')
    
	def updateuptime(self,server):
		now = time.mktime(datetime.datetime.now().timetuple())
		servercameback = time.mktime(server.timeservercameback.timetuple())
		difference = now - servercameback
		MINUTE  = 60
		HOUR    = MINUTE * 60
		DAY     = HOUR * 24
		days    = int( difference / DAY )
		hours   = int( ( difference % DAY ) / HOUR )
		minutes = int( ( difference % HOUR ) / MINUTE )
		seconds = int( difference % MINUTE )

		string = ""
		if days> 0:
			string += str(days) + " " + (days == 1 and "day" or "days" ) + ", "
		if len(string)> 0 or hours> 0:
			string += str(hours) + " " + (hours == 1 and "hour" or "hours" ) + ", "
		if len(string)> 0 or minutes> 0:
			string += str(minutes) + " " + (minutes == 1 and "minute" or "minutes" ) + ", "
		string += str(seconds) + " " + (seconds == 1 and "second" or "seconds" )
		server.uptime = string
		server.put()
 
	def serverisup(self,server,responsecode):
		if server.status == False:
			self.servercameback(server)
		server.status = True
		server.falsepositivecheck = False
		server.responsecode = int(responsecode)
		server.uptimecounter = server.uptimecounter + 1
		self.updateuptime(server)
		server.put()
    
	def serverisdown(self,server,responsecode):
		server.status = False
		server.uptimecounter = 0
		server.uptime = "0"
		server.responsecode = int(responsecode)
		server.timeservercameback = 0
		server.put()
		if server.notifylimiter == False:
			if server.notifywithprowl:
				self.notifyprowl(server)
			if server.notifywithemail:
				self.notifyemail(server)
		else:
			pass

	def servercameback(self,server):
		server.timeservercameback = datetime.datetime.now()

	def testserver(self,server):
		if server.ssl:
			prefix = "https://"	
		else:
			prefix = "http://"
		try:
			url = prefix + "%s" % server.serverdomain
			result = urlfetch.fetch(url, headers = {'Cache-Control' : 'max-age=30'}, deadline=10 )
		except DownloadError:
			if server.falsepositivecheck:
				self.serverisdown(server,000)
			else:
				server.falsepositivecheck = True
				server.put()
		else:
			if result.status_code == 500:
				self.serverisdown(server,result.status_code)
			else:
				self.serverisup(server,result.status_code)

	def notifyemail(self,server):
		message = mail.EmailMessage()
		message.sender = server.email
		message.subject = "%s is down" % server.serverdomain
		message.to = server.email
		message.body = "HTTP response code %s" % server.responsecode
		message.send()
		server.notifylimiter = True
		server.put()
					
	def notifytwitter(self,server):
		pass
		#api = twitter.Api(username="%s" % self.adminoptions.twitteruser , password="%s" % self.adminoptions.twitterpass)
		#api.PostDirectMessage(self.adminoptions.twitteruser, "%s is down" % server.serverdomain)
		#server.notifylimiter = True
		#server.put()
		
	def notifyprowl(self,server):
		prowlkey = self.adminoptions.prowlkey
		prowlnotifier = prowlpy.Prowl(prowlkey)
		try:
			prowlnotifier.add('Server Monitor','Server %s is Down' % server.serverdomain, 'error code %s' % server.responsecode)
		except:
			logging.error('prowl notify failed, you may need to check your API key')
		server.notifylimiter = True
		server.put()	
                
	def get(self):
		for server in self.serverlist:
			self.testserver(server)
            
def main():
	application = webapp.WSGIApplication([('/checkservers', CheckServers)],debug=True)
	wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = frontpage
#!/usr/bin/env python
# Copyright (c) 2009, Steve Oliver (steve@xercestech.com)
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY STEVE OLIVER ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STEVE OLIVER BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cgi
import wsgiref.handlers
from datetime import datetime
import os
from models import Server
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template


class MainHandler(webapp.RequestHandler):
    def get(self):
        serverlist = db.GqlQuery("SELECT * FROM Server")
        user = users.get_current_user()
        template_values = { 'user': user, 'serverlist': serverlist, }
        path = os.path.join(os.path.dirname(__file__), 'frontpage.html')
        self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = base
import httplib, urllib
from zope import interface
from libcloud.interface import IConnectionUserAndKey, IResponse
from libcloud.interface import IConnectionKey, IConnectionKeyFactory
from libcloud.interface import IConnectionUserAndKeyFactory, IResponseFactory
from libcloud.interface import INodeDriverFactory, INodeDriver
from libcloud.interface import INodeFactory, INode
from libcloud.interface import INodeSizeFactory, INodeSize
from libcloud.interface import INodeImageFactory, INodeImage
import hashlib

class Node(object):
    """
    A Base Node class to derive from.
    """
    
    interface.implements(INode)
    interface.classProvides(INodeFactory)

    def __init__(self, id, name, state, public_ip, private_ip, driver):
        self.id = id
        self.name = name
        self.state = state
        self.public_ip = public_ip
        self.private_ip = private_ip
        self.driver = driver
        self.uuid = self.get_uuid()
        
    def get_uuid(self):
        return hashlib.sha1("%s:%d" % (self.id,self.driver.type)).hexdigest()
        
    def reboot(self):
        return self.driver.reboot_node(self)

    def destroy(self):
        return self.driver.destroy_node(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, state=%s, public_ip=%s, provider=%s ...>')
                % (self.uuid, self.name, self.state, self.public_ip, self.driver.name))


class NodeSize(object):
    """
    A Base NodeSize class to derive from.
    """
    
    interface.implements(INodeSize)
    interface.classProvides(INodeSizeFactory)

    def __init__(self, id, name, ram, disk, bandwidth, price, driver):
        self.id = id
        self.name = name
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver
    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s disk=%s bandwidth=%s price=%s driver=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth, self.price, self.driver.name))


class NodeImage(object):
    """
    A Base NodeImage class to derive from.
    """
    
    interface.implements(INodeImage)
    interface.classProvides(INodeImageFactory)

    def __init__(self, id, name, driver):
        self.id = id
        self.name = name
        self.driver = driver
    def __repr__(self):
        return (('<NodeImage: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))


class Response(object):
    """
    A Base Response class to derive from.
    """
    interface.implements(IResponse)
    interface.classProvides(IResponseFactory)

    NODE_STATE_MAP = {}

    object = None
    body = None
    status_code = httplib.OK
    headers = {}
    error = None
    connection = None

    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

        if not self.success():
            raise Exception(self.parse_error())

        self.object = self.parse_body()

    def parse_body(self):
        """
        Parse response body.

        Override in a provider's subclass.

        @return: Parsed body.
        """
        return self.body

    def parse_error(self):
        """
        Parse the error messages.

        Override in a provider's subclass.

        @return: Parsed error.
        """
        return self.body

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        @return: C{True} or C{False}
        """
        return self.status == httplib.OK or self.status == httplib.CREATED


class ConnectionKey(object):
    """
    A Base Connection class to derive from.
    """
    interface.implementsOnly(IConnectionKey)
    interface.classProvides(IConnectionKeyFactory)

    conn_classes = (httplib.HTTPConnection, httplib.HTTPSConnection)
    responseCls = Response
    connection = None
    host = '127.0.0.1'
    port = (80, 443)
    secure = 1
    driver = None

    def __init__(self, key, secure=True):
        """
        Initialize `user_id` and `key`; set `secure` to an C{int} based on
        passed value.
        """
        self.key = key
        self.secure = secure and 1 or 0

    def connect(self, host=None, port=None):
        """
        Establish a connection with the API server.

        @type host: C{str}
        @param host: Optional host to override our default

        @type port: C{int}
        @param port: Optional port to override our default

        @returns: A connection
        """
        host = host or self.host
        port = port or self.port[self.secure]

        connection = self.conn_classes[self.secure](host, port)
        self.connection = connection

    def request(self, action, params={}, data='', headers={}, method='GET'):
        """
        Request a given `action`.
        
        Basically a wrapper around the connection
        object's `request` that does some helpful pre-processing.

        @type action: C{str}
        @param action: A path

        @type params C{dict}
        @param params: Optional mapping of additional parameters to send. If
            None, leave as an empty C{dict}.

        @type data: C{unicode}
        @param data: A body of data to send with the request.

        @type headers C{dict}
        @param headers: Extra headers to add to the request
            None, leave as an empty C{dict}.

        @type method: C{str}
        @param method: An HTTP method such as "GET" or "POST".

        @return: An instance of type I{responseCls}
        """
        # Extend default parameters
        params = self.add_default_params(params)
        # Extend default headers
        headers = self.add_default_headers(headers)
        # We always send a content length and user-agent header
        headers.update({'Content-Length': len(data)})
        headers.update({'User-Agent': 'libcloud/%s' % (self.driver.name)})
        headers.update({'Host': self.host})
        # Encode data if necessary
        if data != '':
            data = self.encode_data(data)
        url = '?'.join((action, urllib.urlencode(params)))
        
        # Removed terrible hack...this a less-bad hack that doesn't execute a
        # request twice, but it's still a hack.
        self.connect()
        self.connection.request(method=method, url=url, body=data,
                                headers=headers)
        response = self.responseCls(self.connection.getresponse())
        response.connection = self
        return response

    def add_default_params(self, params):
        """
        Adds default parameters (such as API key, version, etc.) to the passed `params`

        Should return a dictionary.
        """
        return params

    def add_default_headers(self, headers):
        """
        Adds default headers (such as Authorization, X-Foo-Bar) to the passed `headers`

        Should return a dictionary.
        """
        return headers

    def encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        return data


class ConnectionUserAndKey(ConnectionKey):
    """
    Base connection which accepts a user_id and key
    """
    interface.implementsOnly(IConnectionUserAndKey)
    interface.classProvides(IConnectionUserAndKey)

    user_id = None

    def __init__(self, user_id, key, secure=True):
        super(ConnectionUserAndKey, self).__init__(key, secure)
        self.user_id = user_id


class NodeDriver(object):
    """
    A base NodeDriver class to derive from
    """
    interface.implements(INodeDriver)
    interface.classProvides(INodeDriverFactory)

    connectionCls = ConnectionKey
    name = None
    type = None
    
    NODE_STATE_MAP = {}

    def __init__(self, key, secret=None, secure=True):
        self.key = key
        self.secret = secret
        self.secure = secure
        if self.secret:
          self.connection = self.connectionCls(key, secret, secure)
        else:
          self.connection = self.connectionCls(key, secure)

        self.connection.driver = self
        self.connection.connect()

    def create_node(self, name, image, size, **kwargs):
        raise NotImplementedError, 'create_node not implemented for this driver'

    def destroy_node(self, node):
        raise NotImplementedError, 'destroy_node not implemented for this driver'

    def reboot_node(self, node):
        raise NotImplementedError, 'reboot_node not implemented for this driver'

    def list_nodes(self):
        raise NotImplementedError, 'list_nodes not implemented for this driver'

    def list_images(self):
        raise NotImplementedError, 'list_images not implemented for this driver'

    def list_sizes(self):
        raise NotImplementedError, 'list_sizes not implemented for this driver'

########NEW FILE########
__FILENAME__ = dummy
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.types import Node, NodeState
from libcloud.interface import INodeDriver
from zope.interface import implements

import uuid

class DummyNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds

    def get_uuid(self, unique_field=None):
        return str(uuid.uuid4())
        
    def list_nodes(self):
        return [
            Node(uuid=self.get_uuid(),
                 name='dummy-1',
                 state=NodeState.RUNNING,
                 ipaddress='127.0.0.1',
                 creds=self.creds,
                 attrs={'foo': 'bar'}),
            Node(uuid=self.get_uuid(),
                 name='dummy-2',
                 state=NodeState.REBOOTING,
                 ipaddress='127.0.0.2',
                 creds=self.creds,
                 attrs={'foo': 'bar'})
        ]

    def reboot_node(self, node):
        node.state = NodeState.REBOOTING
        return node

    def destroy_node(self, node):
        pass

    def create_node(self, node):
        pass

########NEW FILE########
__FILENAME__ = ec2
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize, NodeImage
import base64
import hmac
import httplib
from hashlib import sha256
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

EC2_US_HOST = 'ec2.amazonaws.com'
EC2_EU_HOST = 'eu-west-1.ec2.amazonaws.com'
API_VERSION = '2009-04-04'
NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

# Sizes must be hardcoded, because amazon doesn't provide an API to fetch them.
# From http://aws.amazon.com/ec2/instance-types/
EC2_INSTANCE_TYPES = {'m1.small': {'id': 'm1.small',
                       'name': 'Small Instance',
                       'ram': '1740MB',
                       'disk': '160GB',
                       'bandwidth': None},
                      'm1.large': {'id': 'm1.large',
                       'name': 'Large Instance',
                       'ram': '7680MB',
                       'disk': '850GB',
                       'bandwidth': None},
                      'm1.xlarge': {'id': 'm1.xlarge',
                       'name': 'Extra Large Instance',
                       'ram': '15360MB',
                       'disk': '1690GB',
                       'bandwidth': None},
                      'c1.medium': {'id': 'c1.medium',
                       'name': 'High-CPU Medium Instance',
                       'ram': '1740MB',
                       'disk': '350GB',
                       'bandwidth': None},
                      'c1.xlarge': {'id': 'c1.xlarge',
                       'name': 'High-CPU Extra Large Instance',
                       'ram': '7680MB',
                       'disk': '1690GB',
                       'bandwidth': None},
                      'm2.2xlarge': {'id': 'm2.2xlarge',
                       'name': 'High-Memory Double Extra Large Instance',
                       'ram': '35021MB',
                       'disk': '850GB',
                       'bandwidth': None},
                      'm2.4xlarge': {'id': 'm2.4xlarge',
                       'name': 'High-Memory Quadruple Extra Large Instance',
                       'ram': '70042MB',
                       'disk': '1690GB',
                       'bandwidth': None},
                       }


EC2_US_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_EU_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)

EC2_US_INSTANCE_TYPES['m1.small']['price'] = '.1'
EC2_US_INSTANCE_TYPES['m1.large']['price'] = '.4'
EC2_US_INSTANCE_TYPES['m1.xlarge']['price'] = '.8'
EC2_US_INSTANCE_TYPES['c1.medium']['price'] = '.2'
EC2_US_INSTANCE_TYPES['c1.xlarge']['price'] = '.8'
EC2_US_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.2'
EC2_US_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.4'

EC2_EU_INSTANCE_TYPES['m1.small']['price'] = '.11'
EC2_EU_INSTANCE_TYPES['m1.large']['price'] = '.44'
EC2_EU_INSTANCE_TYPES['m1.xlarge']['price'] = '.88'
EC2_EU_INSTANCE_TYPES['c1.medium']['price'] = '.22'
EC2_EU_INSTANCE_TYPES['c1.xlarge']['price'] = '.88'
EC2_EU_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.34'
EC2_EU_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.68'

class EC2Response(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        try:
            err_list = []
            for err in ET.XML(self.body).findall('Errors/Error'):
                code, message = err.getchildren()
                err_list.append("%s: %s" % (code.text, message.text))
            return "\n".join(err_list)
        except ExpatError:
            return self.body

class EC2Connection(ConnectionUserAndKey):

    host = EC2_US_HOST
    responseCls = EC2Response

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = API_VERSION
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', 
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key)
        return params
        
    def _get_aws_auth_param(self, params, secret_key, path='/'):
        """
        creates the signature required for AWS, per:

        http://docs.amazonwebservices.com/AWSEC2/2009-04-04/DeveloperGuide/index.html?using-query-api.html#query-authentication

        StringToSign = HTTPVerb + "\n" +
                       ValueOfHostHeaderInLowercase + "\n" +
                       HTTPRequestURI + "\n" +                 
                       CanonicalizedQueryString <from the preceding step>
        """
        keys = params.keys()
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urllib.quote(key, safe='') + '=' +
                         urllib.quote(params[key], safe='-_~'))

        qs = '&'.join(pairs)
        string_to_sign = '\n'.join(('GET', self.host, path, qs))
                                         
        b64_hmac = base64.b64encode(
                        hmac.new(secret_key, string_to_sign, 
                            digestmod=sha256).digest())
        return b64_hmac

class EC2NodeDriver(NodeDriver):

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2 (us-east-1)'

    _instance_types = EC2_US_INSTANCE_TYPES

    NODE_STATE_MAP = { 'pending': NodeState.PENDING,
                       'running': NodeState.RUNNING,
                       'shutting-down': NodeState.TERMINATED,
                       'terminated': NodeState.TERMINATED }

    def _findtext(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findattr(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _pathlist(self, key, arr):
        """Converts a key and an array of values into AWS query param 
           format."""
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def _get_boolean(self, element):
        tag = "{%s}%s" % (NAMESPACE, 'return')
        return element.findtext(tag) == 'true'

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([ term_status == status for term_status
                     in ('shutting-down', 'terminated') ])

    def _to_nodes(self, object, xpath):
        return [ self._to_node(el) 
                 for el in object.findall(
                    self._fixxpath(xpath)) ]
        
    def _to_node(self, element):
        try:
            state = self.NODE_STATE_MAP[self._findattr(element, 
                                        "instanceState/name")]
        except KeyError:
            state = NodeState.UNKNOWN

        n = Node(id=self._findtext(element, 'instanceId'),
                 name=self._findtext(element, 'instanceId'),
                 state=state,
                 public_ip=self._findtext(element, 'dnsName'),
                 private_ip=self._findtext(element, 'privateDnsName'),
                 driver=self.connection.driver)
        return n

    def _to_images(self, object):
        return [ self._to_image(el)
                 for el in object.findall(
                    self._fixxpath('imagesSet/item')) ]

    def _to_image(self, element):
        n = NodeImage(id=self._findtext(element, 'imageId'),
                      name=self._findtext(element, 'imageLocation'),
                      driver=self.connection.driver)
        return n

    def list_nodes(self):
        params = {'Action': 'DescribeInstances' }
        nodes = self._to_nodes(
                    self.connection.request('/', params=params).object,
                    'reservationSet/item/instancesSet/item')
        return nodes

    def list_sizes(self):
        return [ NodeSize(driver=self.connection.driver, **i) 
                    for i in self._instance_types.values() ]
    
    def list_images(self):
        params = {'Action': 'DescribeImages'}
        images = self._to_images(
                    self.connection.request('/', params=params).object)
        return images

    # name doesn't apply to EC2 nodes.
    def create_node(self, name, image, size, **kwargs):
        params = {'Action': 'RunInstances',
                  'ImageId': image.id,
                  'MinCount': kwargs.get('mincount','1'),
                  'MaxCount': kwargs.get('maxcount','1'),
                  'InstanceType': size.id}

        try: params['SecurityGroup'] = kwargs['securitygroup']
        except KeyError: pass

        try: params['KeyName'] = kwargs['keyname']
        except KeyError: pass

        object = self.connection.request('/', params=params).object
        nodes = self._to_nodes(object, 'instancesSet/item')

        if len(nodes) == 1:
            return nodes[0]
        else: return nodes

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'Action': 'RebootInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request('/', params=params).object
        return self._get_boolean(res)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request('/', params=params).object
        return self._get_terminate_boolean(res)

class EC2EUConnection(EC2Connection):

    host = EC2_EU_HOST

class EC2EUNodeDriver(EC2NodeDriver):

    connectionCls = EC2EUConnection
    _instance_types = EC2_EU_INSTANCE_TYPES

########NEW FILE########
__FILENAME__ = gogrid
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.interface import INodeDriver
from zope.interface import implements
import httplib
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

HOST = 'api.gogrid.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
API_VERSION = '1.1'

class GoGridAuthConnection(object):
    def __init__(self, api_key, secret,
                 is_secure=True, server=HOST, port=None):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.verbose = False
        self.api_key = api_key
        self.secret = secret
        conn_str = "%s:%d" % (server, port)
        if (is_secure):
            self.connection = httplib.HTTPSConnection(conn_str)
        else:
            self.connection = httplib.HTTPConnection(conn_str)


    def make_request(self, action, params={}, data=''):
        if self.verbose:
            print params

        params["api_key"] = self.api_key 
        params["v"] = API_VERSION
        params["format"] = 'xml'
        params["sig"] = self.get_signature(self.api_key, self.secret)

        params = zip(params.keys(), params.values())
        params.sort(key=lambda x: str.lower(x[0]))

        path = "&".join([ "=".join((param[0], urllib.quote_plus(param[1])))
                          for param in params ])
        
        self.connection.request("GET", "/api/%s?%s" % (action, path), data)
        return self.connection.getresponse()

    def get_signature(self, key, secret):
        """ create sig from md5 of key + secret + time """
        return hashlib.md5(key + secret + str(int(time.time()))).hexdigest()

    def server_list(self):
        return Response(self.make_request("/grid/server/list"))

    def server_power(self, id, power):
        # power in ['start', 'stop', 'restart']
        params = {'id': id, 'power': power}
        return Response(self.make_request("/grid/server/power", params))

    def server_delete(self, id):
        params = {'id': id}
        return Response(self.make_request("/grid/server/delete", params))

class Response(object):
    def __init__(self, http_response):
        if int(http_response.status) == 403:
            raise InvalidCredsException()
        self.http_response = http_response
        self.http_xml = http_response.read()

    def is_error(self):
        root = ET.XML(self.http_xml)
        return root.find('response').get('status') != 'success'

    def get_error(self):
        attrs = ET.XML(self.http_xml).findall('.//attribute')
        return ': '.join([attr.text for attr in attrs])

STATE = {
    "Started": NodeState.RUNNING,
}

class GoGridNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds
        self.api = GoGridAuthConnection(creds.key, creds.secret)

    def _findtext(self, element, xpath):
        return element.findtext(xpath)

    def _findattr(self, element, xpath):
        return element.findtext(xpath)

    def get_state(self, element):
        try:
            for stanza in element.findall("object/attribute"):
                if stanza.get('name') == "name":
                    return STATE[stanza.get('name')]
        except:
            pass
        return NodeState.UNKNOWN

    def section(self, element, name):
        return element.get('name') == name

    def section_in(self, element, names):
        return element.get('name') in names

    def get_ip(self, element):
        for stanza in element.getchildren():
            for ips in stanza.getchildren():
                if ips.get('name') == "ip":
                    return ips.text
        raise Exception("No ipaddress found!")

    def get_deepattr(self, element, node_attrs):
        if len(element.getchildren()) > 1:
            i = 0
            for obj in element.getchildren():
                name = "%s_%d" %(element.get('name'), i)
                for attr in obj.getchildren():
                    node_attrs[name+"_"+attr.get("name")] = attr.text
                i += 1
        else:
            for obj in element.getchildren():
                name = element.get('name')
                for attr in obj.getchildren():
                    node_attrs[name+"_"+attr.get("name")] = attr.text
            


    def _to_node(self, element):
        attrs = ['id', 'name', 'description', ]
        deepattrs = ['ram', 'image', 'type', 'os']
        node_attrs = {}
        for shard in element.findall('attribute'):

            if self.section(shard, 'state'):
                state = self.get_state(shard)

            elif self.section(shard, 'ip'):
                node_attrs['ip'] = self.get_ip(shard)

            elif self.section_in(shard, attrs):
                node_attrs[shard.get('name')] = shard.text

            elif self.section_in(shard, deepattrs):
                self.get_deepattr(shard, node_attrs)

        n = Node(uuid=self.get_uuid(node_attrs['id']),
                 name=node_attrs['name'],
                 state=state,
                 ipaddress=node_attrs['ip'],
                 creds=self.creds,
                 attrs=node_attrs)
        return n

    def get_uuid(self, field):
        uuid_str = "%s:%d" % (field,self.creds.provider)
        return hashlib.sha1(uuid_str).hexdigest()
    
    def list_nodes(self):
        res = self.api.server_list()
        return [ self._to_node(el)
                 for el
                 in ET.XML(res.http_xml).findall('response/list/object') ]

    def reboot_node(self, node):
        id = node.attrs['id']
        power = 'restart'

        res = self.api.server_power(id, power)
        if res.is_error():
            raise Exception(res.get_error())

        return True

    def destroy_node(self, node):
        id = node.attrs['id']

        res = self.api.server_delete(id)
        if res.is_error():
            raise Exception(res.get_error())

        return True

########NEW FILE########
__FILENAME__ = linode
#
# libcloud
# A Unified Interface into The Cloud
#
# Linode Driver
# Copyright (C) 2009 libcloud.org and contributors.
# Released under license; see LICENSE for more information.
#.
# Maintainer: Jed Smith <jsmith@linode.com>
#
# BETA TESTING THE LINODE API AND DRIVERS
#
# A beta account that incurs no financial charge may be arranged for.  Please
# contact Jed Smith <jsmith@linode.com> for your request.
#

from libcloud.types import Provider, NodeState
from libcloud.base import ConnectionKey, Response, NodeDriver, NodeSize, Node
from libcloud.base import NodeImage
from copy import copy

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json


# Base exception for problems arising from this driver
class LinodeException(BaseException):
    def __init__(self, code, message):
        self.code = code
        self.message = message
    def __str__(self):
        return "(%u) %s" % (self.code, self.message)
    def __repr__(self):
        return "<LinodeException code %u '%s'>" % (self.code, self.message)

# For beta accounts, change this to "beta.linode.com".
LINODE_API = "api.linode.com"

# For beta accounts, change this to "/api/".
LINODE_ROOT = "/"


class LinodeResponse(Response):
    # Wraps a Linode API HTTP response.
    
    def __init__(self, response):
        # Given a response object, slurp the information from it.
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason
        self.invalid = LinodeException(0xFF, "Invalid JSON received from server")
        
        # Move parse_body() to here;  we can't be sure of failure until we've
        # parsed the body into JSON.
        self.action, self.object, self.errors = self.parse_body()
        
        if self.error == "Moved Temporarily":
            raise LinodeException(0xFA, "Redirected to error page by API.  Bug?")

        if not self.success():
            # Raise the first error, as there will usually only be one
            raise self.errors[0]
    
    def parse_body(self):
        # Parse the body of the response into JSON.  Will return None if the
        # JSON response chokes the parser.  Returns a triple:
        #    (action, data, errorarray)
        try:
            js = json.loads(self.body)
            if "DATA" not in js or "ERRORARRAY" not in js or "ACTION" not in js:
                return (None, None, [self.invalid])
            errs = [self._make_excp(e) for e in js["ERRORARRAY"]]
            return (js["ACTION"], js["DATA"], errs)
        except:
            # Assume invalid JSON, and use an error code unused by Linode API.
            return (None, None, [self.invalid])
    
    def parse_error(self):
        # Obtain the errors from the response.  Will always return a list.
        try:
            js = json.loads(self.body)
            if "ERRORARRAY" not in js:
                return [self.invalid]
            return [self._make_excp(e) for e in js["ERRORARRAY"]]
        except:
            return [self.invalid]
    
    def success(self):
        # Does the response indicate success?  If ERRORARRAY has more than one
        # entry, we'll say no.
        return len(self.errors) == 0
    
    def _make_excp(self, error):
        # Make an exception from an entry in ERRORARRAY.
        if "ERRORCODE" not in error or "ERRORMESSAGE" not in error:
            return None
        return LinodeException(error["ERRORCODE"], error["ERRORMESSAGE"])
        

class LinodeConnection(ConnectionKey):
    # Wraps a Linode HTTPS connection, and passes along the connection key.
    host = LINODE_API
    responseCls = LinodeResponse
    def add_default_params(self, params):
        params["api_key"] = self.key
        # Be explicit about this in case the default changes.
        params["api_responseFormat"] = "json"
        return params


class LinodeNodeDriver(NodeDriver):
    # The meat of Linode operations; the Node Driver.
    type = Provider.LINODE
    name = "Linode"
    connectionCls = LinodeConnection
    
    def __init__(self, key):
        self.datacenter = None
        NodeDriver.__init__(self, key)

    # Converts Linode's state from DB to a NodeState constant.
    # Some of these are lightly questionable.
    LINODE_STATES = {
        -2: NodeState.UNKNOWN,              # Boot Failed
        -1: NodeState.PENDING,              # Being Created
         0: NodeState.PENDING,              # Brand New
         1: NodeState.RUNNING,              # Running
         2: NodeState.REBOOTING,            # Powered Off (TODO: Extra state?)
         3: NodeState.REBOOTING,            # Shutting Down (?)
         4: NodeState.UNKNOWN               # Reserved
    }

    def list_nodes(self):
        # List
        # Provide a list of all nodes that this API key has access to.
        params = { "api_action": "linode.list" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        return [self._to_node(n) for n in data]
    
    def reboot_node(self, node):
        # Reboot
        # Execute a shutdown and boot job for the given Node.
        params = { "api_action": "linode.reboot", "LinodeID": node.id }
        self.connection.request(LINODE_ROOT, params=params)
        return True
    
    def destroy_node(self, node):
        # Destroy
        # Terminates a Node.  With prejudice.
        params = { "api_action": "linode.delete", "LinodeID": node.id,
            "skipChecks": True }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def create_node(self, name, image, size, **kwargs):
        # Create
        #
        # Creates a Linode instance.
        #
        #       name     Used for a lot of things; be cautious with charset
        #       image    NodeImage from list_images
        #       size     NodeSize from list_sizes
        #
        # Keyword arguments supported:
        #
        #    One of the following is REQUIRED, but both can be given:
        #       ssh      The SSH key to deploy for root (None).
        #       root     Password to set for root (Random).
        #
        #    These are all optional:
        #       swap     Size of the swap partition in MB (128).
        #       rsize    Size of the root partition (plan size - swap).
        #       kernel   A kernel ID from avail.kernels (Latest 2.6).
        #       comment  Comments to store with the config (None).
        #       payment  One of 1, 12, or 24; subscription length (1).
        #
        #    Labels to override what's generated (default on right):
        #       lconfig      [%name] Instance
        #       lrecovery    [%name] Finnix Recovery Configuration
        #       lroot        [%name] %distro
        #       lswap        [%name] Swap Space
        #
        # Datacenter logic:
        #
        #   As Linode requires choosing a datacenter, a little logic is done.
        #
        #   1. If the API key in use has all its Linodes in one DC, that DC will
        #      be chosen (and can be overridden with linode_set_datacenter).
        #
        #   2. Otherwise (for both the "No Linodes" and "different DC" cases), a
        #      datacenter must explicitly be chosen using linode_set_datacenter.
        #
        # Please note that for safety, only 5 Linodes can be created per hour.

        # Step -1: Do the datacenter logic
        fail = LinodeException(0xFC,
            "Can't pick DC; choose a datacenter with linode_set_datacenter()")
        if not self.datacenter:
            # Okay, one has not been chosen.  We need to determine.
            nodes = self.list_nodes()
            num = len(nodes)
            if num == 0:
                # Won't assume where to deploy the first one.
                # FIXME: Maybe we should?
                raise fail
            else:
                # One or more nodes, so create the next one there.
                chosen = nodes[0].extra["DATACENTERID"]
                for node in nodes[1:]:
                    # Check to make sure they're all the same
                    if chosen != node.extra["DATACENTERID"]:
                        raise fail
        else:
            # linode_set_datacenter() was used, cool.
            chosen = self.datacenter

        # Step 0: Parameter validation before we purchase
        # We're especially careful here so we don't fail after purchase, rather
        # than getting halfway through the process and having the API fail.

        # Plan ID
        plans = self.list_sizes()
        if size.id not in [p.id for p in plans]:
            raise LinodeException(0xFB, "Invalid plan ID -- avail.plans")

        # Payment schedule
        payment = "1" if "payment" not in kwargs else str(kwargs["payment"])
        if payment not in ["1", "12", "24"]:
            raise LinodeException(0xFB, "Invalid subscription (1, 12, 24)")

        # SSH key and/or root password
        ssh = None if "ssh" not in kwargs else kwargs["ssh"]
        root = None if "root" not in kwargs else kwargs["root"]
        if not ssh and not root:
            raise LinodeException(0xFB, "Need SSH key or root password")
        if len(root) < 6:
            raise LinodeException(0xFB, "Root password is too short")

        # Swap size
        try: swap = 128 if "swap" not in kwargs else int(kwargs["swap"])
        except: raise LinodeException(0xFB, "Need an integer swap size")

        # Root partition size
        imagesize = (size.disk - swap) if "rsize" not in kwargs else \
            int(kwargs["rsize"])
        if (imagesize + swap) > size.disk:
            raise LinodeException(0xFB, "Total disk images are too big")

        # Distribution ID
        distros = self.list_images()
        if image.id not in [d.id for d in distros]:
            raise LinodeException(0xFB, "Invalid distro -- avail.distributions")

        # Kernel
        kernel = 60 if "kernel" not in kwargs else kwargs["kernel"]
        params = { "api_action": "avail.kernels" }
        kernels = self.connection.request(LINODE_ROOT, params=params).object
        if kernel not in [z["KERNELID"] for z in kernels]:
            raise LinodeException(0xFB, "Invalid kernel -- avail.kernels")

        # Comments
        comments = "Created by libcloud <http://www.libcloud.org>" if \
            "comment" not in kwargs else kwargs["comment"]

        # Labels
        label = {
            "lconfig": "[%s] Configuration Profile" % name,
            "lrecovery": "[%s] Finnix Recovery Configuration" % name,
            "lroot": "[%s] %s Disk Image" % (name, image.name),
            "lswap": "[%s] Swap Space" % name
        }
        for what in ["lconfig", "lrecovery", "lroot", "lswap"]:
            if what in kwargs:
                label[what] = kwargs[what]

        # Step 1: linode.create
        params = {
            "api_action":   "linode.create",
            "DatacenterID": chosen,
            "PlanID":       size.id,
            "PaymentTerm":  payment
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode = { "id": data["LinodeID"] }

        # Step 2: linode.disk.createfromdistribution
        if not root:
            # Generate a random root password
            randomness = "!(#%&" + str(Random().random()) + "sup dawg?"
            root = sha512(randomness).hexdigest()
        params = {
            "api_action":       "linode.disk.createfromdistribution",
            "LinodeID":         linode["id"],
            "DistributionID":   image.id,
            "Label":            label["lroot"],
            "Size":             imagesize,
            "rootPass":         root,
        }
        if ssh: params["rootSSHKey"] = ssh
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["rootimage"] = data["DiskID"]

        # Step 3: linode.disk.create for swap
        params = {
            "api_action":       "linode.disk.create",
            "LinodeID":         linode["id"],
            "Label":            label["lswap"],
            "Type":             "swap",
            "Size":             swap
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["swapimage"] = data["DiskID"]

        # Step 4: linode.config.create for main profile
        disks = "%s,%s,,,,,,," % (linode["rootimage"], linode["swapimage"])
        params = {
            "api_action":       "linode.config.create",
            "LinodeID":         linode["id"],
            "KernelID":         kernel,
            "Label":            label["lconfig"],
            "Comments":         comments,
            "DiskList":         disks
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["config"] = data["ConfigID"]

        # TODO: Recovery image (Finnix)

        # Step 5: linode.boot
        params = {
            "api_action":       "linode.boot",
            "LinodeID":         linode["id"],
            "ConfigID":         linode["config"]
        }
        data = self.connection.request(LINODE_ROOT, params=params).object

        # Make a node out of it and hand it back
        params = { "api_action": "linode.list", "LinodeID": linode["id"] }
        data = self.connection.request(LINODE_ROOT, params=params).object
        return self._to_node(data[0])

    def list_sizes(self):
        # List Sizes
        # Retrieve all available Linode plans.
        # FIXME: Prices get mangled due to 'float'.
        params = { "api_action": "avail.linodeplans" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        sizes = []
        for obj in data:
            n = NodeSize(id=obj["PLANID"], name=obj["LABEL"], ram=obj["RAM"],
                    disk=(obj["DISK"] * 1024), bandwidth=obj["XFER"],
                    price=obj["PRICE"], driver=self.connection.driver)
            sizes.append(n)
        return sizes
    
    def list_images(self):
        # List Images
        # Retrieve all available Linux distributions.
        params = { "api_action": "avail.distributions" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        distros = []
        for obj in data:
            i = NodeImage(id=obj["DISTRIBUTIONID"], name=obj["LABEL"],
                driver=self.connection.driver)
            distros.append(i)
        return distros

    def linode_set_datacenter(self, did):
        # Set the datacenter for create requests.
        #
        # Create will try to guess, based on where all of the API key's Linodes
        # are located; if they are all in one location, Create will make a new
        # node there.  If there are NO Linodes on the account or Linodes are in
        # multiple locations, it is imperative to set this or creates will fail.
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        for dc in data:
            if did == dc["DATACENTERID"]:
                self.datacenter = did
                return

        dcs = ", ".join([d["DATACENTERID"] for d in data])
        self.datacenter = None
        raise LinodeException(0xFD, "Invalid datacenter (use one of %s)" % dcs)

    def _to_node(self, obj):
        # Convert a returned Linode instance into a Node instance.
        lid = obj["LINODEID"]
        
        # Get the IP addresses for a Linode
        params = { "api_action": "linode.ip.list", "LinodeID": lid }        
        req = self.connection.request(LINODE_ROOT, params=params)
        if not req.success() or len(req.object) == 0:
            return None
        
        # TODO: Multiple IP support.  How do we handle that case?
        public_ip = private_ip = None
        for ip in req.object:
            if ip["ISPUBLIC"]: public_ip = ip["IPADDRESS"]
            else: private_ip = ip["IPADDRESS"]

        n = Node(id=lid, name=obj["LABEL"],
            state=self.LINODE_STATES[obj["STATUS"]], public_ip=public_ip,
            private_ip=private_ip, driver=self.connection.driver)
        n.extra = copy(obj)
        return n

########NEW FILE########
__FILENAME__ = rackspace
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.types import NodeState, InvalidCredsException, Provider
from libcloud.base import ConnectionUserAndKey, Response, NodeDriver, Node, NodeSize, NodeImage
from libcloud.interface import INodeDriver

from zope.interface import implements

import urlparse

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'

class RackspaceResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        # TODO: fixup, Rackspace only uses response codes really!
        try:
            object = ET.XML(self.body)
            return "; ".join([ err.text
                               for err in
                               object.findall('error') ])
        except ExpatError:
            return self.body


class RackspaceConnection(ConnectionUserAndKey):
    api_version = 'v1.0'
    auth_host = 'auth.api.rackspacecloud.com'
    __host = None
    path = None
    token = None

    responseCls = RackspaceResponse

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.token;
        headers['Accept'] = 'application/xml'
        return headers

    @property
    def host(self):
        """
        Rackspace uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.

        TODO: Fixup for when our token expires (!!!)
        """
        if not self.__host:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](self.auth_host, self.port[self.secure])
            conn.request(method='GET', url='/%s' % self.api_version,
                                           headers={'X-Auth-User': self.user_id,
                                                    'X-Auth-Key': self.key})
            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            try:
                self.token = headers['x-auth-token']
                endpoint = headers['x-server-management-url']
            except KeyError:
                raise InvalidCredsException()

            scheme, server, self.path, param, query, fragment = (
                urlparse.urlparse(endpoint)
            )
            if scheme is "https" and self.secure is not 1:
                # TODO: Custom exception (?)
                raise InvalidCredsException()

            # Set host to where we want to make further requests to; close auth conn
            self.__host = server
            conn.close()

        return self.__host

    def request(self, action, params={}, data='', headers={}, method='GET'):
        # Due to first-run authentication request, we may not have a path
        if self.path:
            action = self.path + action
        if method == "POST":
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        return super(RackspaceConnection, self).request(action=action,
                                                        params=params, data=data,
                                                        method=method, headers=headers)
        

class RackspaceNodeDriver(NodeDriver):

    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    name = 'Rackspace'

    NODE_STATE_MAP = {  'BUILD': NodeState.PENDING,
                        'ACTIVE': NodeState.RUNNING,
                        'SUSPENDED': NodeState.TERMINATED,
                        'QUEUE_RESIZE': NodeState.PENDING,
                        'PREP_RESIZE': NodeState.PENDING,
                        'RESCUE': NodeState.PENDING,
                        'REBUILD': NodeState.PENDING,
                        'REBOOT': NodeState.REBOOTING,
                        'HARD_REBOOT': NodeState.REBOOTING}

    def list_nodes(self):
        return self.to_nodes(self.connection.request('/servers/detail').object)

    def list_sizes(self):
        return self.to_sizes(self.connection.request('/flavors/detail').object)

    def list_images(self):
        return self.to_images(self.connection.request('/images/detail').object)

    def create_node(self, name, image, size, **kwargs):
        body = """<server   xmlns="%s"
                            name="%s"
                            imageId="%s"
                            flavorId="%s">
                </server>
                """ % (NAMESPACE, name, image.id, size.id)
        resp = self.connection.request("/servers", method='POST', data=body)
        return self._to_node(resp.object)

    def reboot_node(self, node):
        # TODO: Hard Reboots should be supported too!
        resp = self._node_action(node, ['reboot', ('type', 'SOFT')])
        return resp.status == 202

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 202

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1]) for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def to_nodes(self, object):
        node_elements = self._findall(object, 'server')
        return [ self._to_node(el) for el in node_elements ]

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]
        
        public_ip = get_ips(self._findall(el, 
                                          'addresses/public/ip'))
        private_ip = get_ips(self._findall(el, 
                                          'addresses/private/ip'))
        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=el.get('status'),
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver)
        return n

    def to_sizes(self, object):
        elements = self._findall(object, 'flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, el):
        s = NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     bandwidth=None, # XXX: needs hardcode
                     price=None, # XXX: needs hardcode,
                     driver=self.connection.driver)
        return s

    def to_images(self, object):
        elements = self._findall(object, "image")
        return [ self._to_image(el) for el in elements if el.get('status') == 'ACTIVE']

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                     name=el.get('name'),
                     driver=self.connection.driver)
        return i

########NEW FILE########
__FILENAME__ = rimuhosting
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Copyright 2009 RedRata Ltd

from libcloud.types import Provider, NodeState
from libcloud.base import ConnectionKey, Response, NodeDriver, NodeSize, Node
from libcloud.base import NodeImage
from copy import copy

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json

# Defaults
API_CONTEXT = '/r'
API_HOST = 'api.rimuhosting.com'
API_PORT = (80,443)
API_SECURE = True

class RimuHostingException(BaseException):
    def __init__(self, error):
        self.error = error
        
    def __str__(self):
        return self.error

    def __repr__(self):
        return "<RimuHostingException '%s'>" % (self.error)

class RimuHostingResponse(Response):
    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

        self.object = self.parse_body()

    def parse_body(self):
        try:
            js = json.loads(self.body)
            if js[js.keys()[0]]['response_type'] == "ERROR":
                raise RimuHostingException(js[js.keys()[0]]['human_readable_message'])
            return js[js.keys()[0]]
        except ValueError:
            raise RimuHostingException('Could not parse body: %s' % (self.body))
        except KeyError:
            raise RimuHostingException('Could not parse body: %s' % (self.body))
    
class RimuHostingConnection(ConnectionKey):
    
    api_context = API_CONTEXT
    host = API_HOST
    port = API_PORT
    responseCls = RimuHostingResponse
    
    def __init__(self, key, secure=True):
        # override __init__ so that we can set secure of False for testing
        ConnectionKey.__init__(self,key,secure)

    def add_default_headers(self, headers):
        # We want JSON back from the server. Could be application/xml (but JSON
        # is better).
        headers['Accept'] = 'application/json'
        # Must encode all data as json, or override this header.
        headers['Content-Type'] = 'application/json'
      
        headers['Authorization'] = 'rimuhosting apikey=%s' % (self.key)
        return headers;

    def request(self, action, params={}, data='', headers={}, method='GET'):
        # Override this method to prepend the api_context
        return ConnectionKey.request(self, self.api_context + action, params, data, headers, method)

class RimuHostingNodeDriver(NodeDriver):
    type = Provider.RIMUHOSTING
    name = 'RimuHosting'
    connectionCls = RimuHostingConnection
    
    def __init__(self, key, host=API_HOST, port=API_PORT, api_context=API_CONTEXT, secure=API_SECURE):
        # Pass in some extra vars so that
        self.key = key
        self.secure = secure
        self.connection = self.connectionCls(key ,secure)
        self.connection.host = host
        self.connection.api_context = api_context
        self.connection.port = port
        self.connection.driver = self
        self.connection.connect()

    def _order_uri(self, node,resource):
        # Returns the order uri with its resourse appended.
        return "/orders/%s/%s" % (node.slug,resource)
   
    # TODO: Get the node state.
    def _to_node(self, order):
        n = Node(id=order['order_oid'],
                name=order['domain_name'],
                state=NodeState.RUNNING,
                public_ip=[order['allocated_ips']['primary_ip']]+order['allocated_ips']['secondary_ips'],
                private_ip=None,
                driver=self.connection.driver)
        n.slug = order['slug']
        return n

    def _to_size(self,plan):
        return NodeSize(id=plan['pricing_plan_code'],
            name=plan['pricing_plan_description'],
            ram=plan['minimum_memory_mb'],
            disk=plan['minimum_disk_gb'],
            bandwidth=plan['minimum_data_transfer_allowance_gb'],
            price=plan['monthly_recurring_fee_usd'],
            driver=self.connection.driver)
                
    def _to_image(self,image):
        return NodeImage(id=image['distro_code'],
            name=image['distro_description'],
            driver=self.connection.driver)
        
    def list_sizes(self):
        # Returns a list of sizes (aka plans)
        # Get plans. Note this is really just for libcloud. We are happy with any size.
        res = self.connection.request('/pricing-plans;server-type=VPS').object
        return map(lambda x : self._to_size(x), res['pricing_plan_infos'])

    def list_nodes(self):
        # Returns a list of Nodes
        # Will only include active ones.
        res = self.connection.request('/orders;include_inactive=N').object
        return map(lambda x : self._to_node(x), res['about_orders'])
    
    def list_images(self):
        # Get all base images.
        # TODO: add other image sources. (Such as a backup of a VPS)
        res = self.connection.request('/distributions').object
        return map(lambda x : self._to_image(x), res['distro_infos'])

    def reboot_node(self, node):
        # Reboot
        # PUT the state of RESTARTING to restart a VPS.
        # All data is encoded as JSON
        data = {'reboot_request':{'running_state':'RESTARTING'}}
        uri = self._order_uri(node,'vps/running-state')
        self.connection.request(uri,data=json.dumps(data),method='PUT')
        # XXX check that the response was actually successful
        return True
    
    def destroy_node(self, node):
        # Shutdown a VPS.
        uri = self._order_uri(node,'vps')
        self.connection.request(uri,method='DELETE')
        # XXX check that the response was actually successful
        return True

    def create_node(self, name, image, size, **kwargs):
        # Creates a RimuHosting instance
        #
        #   name    Must be a FQDN. e.g example.com.
        #   image   NodeImage from list_images
        #   size    NodeSize from list_sizes
        #
        # Keyword arguements supported:
        #
        #   billing_oid             If not set, a billing method is automatically picked.
        #   host_server_oid         The host server to set the VPS up on.
        #   vps_order_oid_to_clone  Clone another VPS to use as the image for the new VPS.
        #  
        #   num_ips = 1         Number of IPs to allocate. Defaults to 1.
        #   extra_ip_reason     Reason for needing the extra IPS.
        #   
        #   memory_mb           Memory to allocate to the VPS.
        #   disk_space_mb=4096  Diskspace to allocate to the VPS. Default is 4GB.
        #   disk_space_2_mb     Secondary disk size allocation. Disabled by default.
        #   
        #   pricing_plan_code       Plan from list_sizes
        #   
        #   control_panel       Control panel to install on the VPS.
        #   password            Password to set on the VPS.
        #
        #
        # Note we don't do much error checking in this because we the API to error out if there is a problem.  
        data = {
            'instantiation_options':{'domain_name': name, 'distro': image.id},
            'pricing_plan_code': size.id,
        }
        
        if kwargs.has_key('control_panel'):
            data['instantiation_options']['control_panel'] = kwargs['control_panel']
        

        if kwargs.has_key('password'):
            data['instantiation_options']['password'] = kwargs['password']
        
        if kwargs.has_key('billing_oid'):
            #TODO check for valid oid.
            data['billing_oid'] = kwargs['billing_oid']
        
        if kwargs.has_key('host_server_oid'):
            data['host_server_oid'] = kwargs['host_server_oid']
            
        if kwargs.has_key('vps_order_oid_to_clone'):
            data['vps_order_oid_to_clone'] = kwargs['vps_order_oid_to_clone']
        
        if kwargs.has_key('num_ips') and int(kwargs['num_ips']) > 1:
            if not kwargs.has_key('extra_ip_reason'):
                raise RimuHostingException('Need an reason for having an extra IP')
            else:
                if not data.has_key('ip_request'):
                    data['ip_request'] = {}
                data['ip_request']['num_ips'] = int(kwargs['num_ips'])
                data['ip_request']['extra_ip_reason'] = kwargs['extra_ip_reason']
        
        if kwargs.has_key('memory_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['memory_mb'] = kwargs['memory_mb']
        
        if kwargs.has_key('disk_space_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_mb'] = kwargs['disk_space_mb']
        
        if kwargs.has_key('disk_space_2_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_2_mb'] = kwargs['disk_space_2_mb']
        
        
        res = self.connection.request('/orders/new-vps', method='POST', data=json.dumps({"new-vps":data})).object
        return self._to_node(res['about_order'])
    
        

########NEW FILE########
__FILENAME__ = slicehost
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.types import NodeState, InvalidCredsException, Provider
from libcloud.base import ConnectionKey, Response, NodeDriver, Node, NodeSize, NodeImage
import base64
import httplib
import struct
import socket
import hashlib
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

class SlicehostResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        try:
            object = ET.XML(self.body)
            return "; ".join([ err.text
                               for err in
                               object.findall('error') ])
        except ExpatError:
            return self.body
    

class SlicehostConnection(ConnectionKey):

    host = 'api.slicehost.com'
    responseCls = SlicehostResponse

    def add_default_headers(self, headers):
        headers['Authorization'] = ('Basic %s'
                              % (base64.b64encode('%s:' % self.key)))
        return headers
    

class SlicehostNodeDriver(NodeDriver):

    connectionCls = SlicehostConnection

    type = Provider.SLICEHOST
    name = 'Slicehost'

    NODE_STATE_MAP = { 'active': NodeState.RUNNING,
                       'build': NodeState.PENDING,
                       'reboot': NodeState.REBOOTING,
                       'hard_reboot': NodeState.REBOOTING,
                       'terminated': NodeState.TERMINATED }

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/slices.xml').object)

    def list_sizes(self):
        return self._to_sizes(self.connection.request('/flavors.xml').object)

    def list_images(self):
        return self._to_images(self.connection.request('/images.xml').object)

    def create_node(self, name, image, size, **kwargs):
        uri = '/slices.xml'

        # create a slice obj
        root = ET.Element('slice')
        el_name = ET.SubElement(root, 'name')
        el_name.text = name
        flavor_id = ET.SubElement(root, 'flavor-id')
        flavor_id.text = str(size.id)
        image_id = ET.SubElement(root, 'image-id')
        image_id.text = str(image.id)
        xml = ET.tostring(root)

        node = self._to_nodes(
                  self.connection.request(uri, method='POST', 
                            data=xml, headers={'Content-Type': 'application/xml'}
                      ).object)[0]
        return node

    def reboot_node(self, node):
        """Reboot the node by passing in the node object"""

        # 'hard' could bubble up as kwarg depending on how reboot_node 
        # turns out. Defaulting to soft reboot.
        #hard = False
        #reboot = self.api.hard_reboot if hard else self.api.reboot
        #expected_status = 'hard_reboot' if hard else 'reboot'

        uri = '/slices/%s/reboot.xml' % (node.id)
        node = self._to_nodes(self.connection.request(uri, method='PUT').object)[0]
        return node.state == NodeState.REBOOTING

    def destroy_node(self, node):
        """Destroys the node

        Requires 'Allow Slices to be deleted or rebuilt from the API' to be
        ticked at https://manage.slicehost.com/api, otherwise returns:

        <errors>
          <error>You must enable slice deletes in the SliceManager</error>
          <error>Permission denied</error>
        </errors>
        """
        uri = '/slices/%s/destroy.xml' % (node.id)
        ret = self.connection.request(uri, method='PUT')
        return True

    def _to_nodes(self, object):
        if object.tag == 'slice':
            return [ self._to_node(object) ]
        node_elements = object.findall('slice')
        return [ self._to_node(el) for el in node_elements ]

    def _to_node(self, element):

        attrs = [ 'name', 'image-id', 'progress', 'id', 'bw-out', 'bw-in', 
                  'flavor-id', 'status', 'ip-address' ]

        node_attrs = {}
        for attr in attrs:
            node_attrs[attr] = element.findtext(attr)

        # slicehost does not determine between public and private, so we 
        # have to figure it out
        public_ip = element.findtext('ip-address')
        private_ip = None
        for addr in element.findall('addresses/address'):
            ip = addr.text
            try:
                socket.inet_aton(ip)
            except socket.error:
                # not a valid ip
                continue
            if self._is_private_subnet(ip):
                private_ip = ip
            else:
                public_ip = ip
                
        try:
            state = self.NODE_STATE_MAP[element.findtext('status')]
        except:
            state = NodeState.UNKNOWN

        n = Node(id=element.findtext('id'),
                 name=element.findtext('name'),
                 state=state,
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver)
        return n

    def _to_sizes(self, object):
        if object.tag == 'flavor':
            return [ self._to_size(object) ]
        elements = object.findall('flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, element):
        s = NodeSize(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     ram=int(element.findtext('ram')),
                     disk=None, # XXX: needs hardcode
                     bandwidth=None, # XXX: needs hardcode
                     price=float(element.findtext('price'))/(100*24*30),
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        if object.tag == 'image':
            return [ self._to_image(object) ]
        elements = object.findall('image')
        return [ self._to_image(el) for el in elements ]

    def _to_image(self, element):
        i = NodeImage(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     driver=self.connection.driver)
        return i


    def _is_private_subnet(self, ip):
        priv_subnets = [ {'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                         {'subnet': '172.16.0.0', 'mask': '172.16.0.0'},
                         {'subnet': '192.168.0.0', 'mask': '192.168.0.0'} ]

        ip = struct.unpack('I',socket.inet_aton(ip))[0]

        for network in priv_subnets:
            subnet = struct.unpack('I',socket.inet_aton(network['subnet']))[0]
            mask = struct.unpack('I',socket.inet_aton(network['mask']))[0]

            if (ip & mask) == (subnet & mask):
                return True
            
        return False

########NEW FILE########
__FILENAME__ = vcloud
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize, NodeImage

import base64
import httplib
from urlparse import urlparse
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

def get_url_path(url):
    return urlparse(url.strip()).path

def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e) for e in xpath.split("/")])
    return fixed_xpath

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        try:
            return ET.XML(self.body)
        except ExpatError, e:
            raise Exception("%s: %s" % (e, self.parse_error()))

    def parse_error(self):
        return self.body

    def success(self):
        return self.status in (httplib.OK, httplib.CREATED, 
                               httplib.NO_CONTENT, httplib.ACCEPTED)

class VCloudConnection(ConnectionUserAndKey):

    responseCls = VCloudResponse
    token = None
    host = None

    def request(self, *args, **kwargs):
        self._get_auth_token()
        return super(VCloudConnection, self).request(*args, **kwargs)

    def check_org(self):
        self._get_auth_token() # the only way to get our org is by logging in.

    def _get_auth_headers(self):
        """Some providers need different headers than others"""
        return {'Authorization': "Basic %s" % base64.b64encode('%s:%s' % (self.user_id, self.key)),
                'Content-Length': 0}

    def _get_auth_token(self):
        if not self.token:
            conn = self.conn_classes[self.secure](self.host, 
                                                  self.port[self.secure])
            conn.request(method='POST', url='/api/v0.8/login', headers=self._get_auth_headers())

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            body = ET.XML(resp.read())

            try:
                self.token = headers['set-cookie']
            except KeyError:
                raise InvalidCredsException()

            self.driver.org = get_url_path(body.find(fixxpath(body, 'Org')).get('href'))

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudNodeDriver(NodeDriver):
    type = Provider.VCLOUD
    name = "vCloud"
    connectionCls = VCloudConnection
    org = None
    _vdcs = None

    NODE_STATE_MAP = {'0': NodeState.PENDING,
                      '1': NodeState.PENDING,
                      '2': NodeState.PENDING,
                      '3': NodeState.PENDING,
                      '4': NodeState.RUNNING}

    @property
    def vdcs(self):
        if not self._vdcs:
            self.connection.check_org() # make sure the org is set.
            res = self.connection.request(self.org)
            self._vdcs = [get_url_path(i.get('href'))
                          for i in res.object.findall(fixxpath(res.object, "Link"))
                          if i.get('type') == 'application/vnd.vmware.vcloud.vdc+xml']
            
        return self._vdcs

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, name, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        public_ips = [ip.text for ip in elm.findall(fixxpath(elm, 'NetworkConnectionSection/NetworkConnection/IPAddress'))]

        node = Node(id=name,
                    name=name,
                    state=state,
                    public_ip=public_ips,
                    private_ip=None,
                    driver=self.connection.driver)

        return node

    def _get_catalog_hrefs(self):
        res = self.connection.request(self.org)
        catalogs = [get_url_path(i.get('href'))
                    for i in res.object.findall(fixxpath(res.object, "Link"))
                    if i.get('type') == 'application/vnd.vmware.vcloud.catalog+xml']

        return catalogs

    def destroy_node(self, node):
        self.connection.request('/vapp/%s/power/action/poweroff' % node.id,
                                method='POST') 
        try:
            res = self.connection.request('/vapp/%s/action/undeploy' % node.id,
                                          method='POST')
        except ExpatError: # the undeploy response is malformed XML atm. We can remove this whent he providers fix the problem.
            return True
        return res.status == 202

    def reboot_node(self, node):
        res = self.connection.request('/vapp/%s/power/action/reset' % node.id,
                                      method='POST') 
        return res.status == 204

    def list_nodes(self):
        nodes = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc) 
            elms = res.object.findall(fixxpath(res.object, "ResourceEntities/ResourceEntity"))
            vapps = [(i.get('name'), get_url_path(i.get('href')))
                        for i in elms
                            if i.get('type') == 'application/vnd.vmware.vcloud.vApp+xml' and 
                               i.get('name')]

            for vapp_name, vapp_href in vapps:
                res = self.connection.request(
                    vapp_href,
                    headers={'Content-Type': 'application/vnd.vmware.vcloud.vApp+xml'}
                )
                nodes.append(self._to_node(vapp_name, res.object))

        return nodes

    def list_images(self):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            res_ents = res.findall(fixxpath(res, "ResourceEntities/ResourceEntity"))
            images += [self._to_image(i) 
                       for i in res_ents 
                       if i.get('type') == 'application/vnd.vmware.vcloud.vAppTemplate+xml']
        
        for catalog in self._get_catalog_hrefs():
            res = self.connection.request(
                catalog,
                headers={'Content-Type': 'application/vnd.vmware.vcloud.catalog+xml'}
            ).object

            cat_items = res.findall(fixxpath(res, "CatalogItems/CatalogItem"))
            cat_item_hrefs = [i.get('href')
                              for i in cat_items
                              if i.get('type') == 'application/vnd.vmware.vcloud.catalogItem+xml']

            for cat_item in cat_item_hrefs:
                res = self.connection.request(
                    cat_item,
                    headers={'Content-Type': 'application/vnd.vmware.vcloud.catalogItem+xml'}
                ).object
                res_ents = res.findall(fixxpath(res, 'Entity'))
                images += [self._to_image(i)
                           for i in res_ents
                           if i.get('type') ==  'application/vnd.vmware.vcloud.vAppTemplate+xml']

        return images

class HostingComConnection(VCloudConnection):
    host = "vcloud.safesecureweb.com" 
    
    def _get_auth_headers(self):
        """hosting.com doesn't follow the standard vCloud authentication API"""
        return {'Authentication': base64.b64encode('%s:%s' % (self.user_id, self.key)),
                   'Content-Length': 0} 


class HostingComDriver(VCloudNodeDriver):
    connectionCls = HostingComConnection

########NEW FILE########
__FILENAME__ = vpsnet
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.providers import Provider
from libcloud.types import NodeState
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize, NodeImage

import base64

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json

API_HOST = 'vps.net'
API_VERSION = 'api10json'

RAM_PER_NODE = 256
DISK_PER_NODE = 10
BANDWIDTH_PER_NODE = 250
PRICE_PER_NODE = {1: 20,
                  2: 19,
                  3: 18,
                  4: 17,
                  5: 16,
                  6: 15,
                  7: 14,
                  15: 13,
                  30: 12,
                  60: 11,
                  100: 10}

class VPSNetResponse(Response):
    
    def parse_body(self):
        try:
            js = json.loads(self.body)
            return js
        except ValueError:
            return self.body

    def parse_error(self):
        try:
            errors = json.loads(self.body)['errors'][0]
        except ValueError:
            return self.body
        else:
            return "\n".join(errors)

class VPSNetConnection(ConnectionUserAndKey):

    host = API_HOST
    responseCls = VPSNetResponse

    def add_default_headers(self, headers):
        user_b64 = base64.b64encode('%s:%s' % (self.user_id, self.key))
        headers['Authorization'] = 'Basic %s' % (user_b64)
        return headers

class VPSNetNodeDriver(NodeDriver):
    
    type = Provider.VPSNET
    name = "vps.net"
    connectionCls = VPSNetConnection

    def _to_node(self, vm):
        if vm['running']:
            state = NodeState.RUNNING
        else:
            state = NodeState.PENDING

        n = Node(id=vm['id'],
                 name=vm['label'],
                 state=state,
                 public_ip=vm.get('primary_ip_address', None),
                 private_ip=None,
                 driver=self.connection.driver)
        return n

    def _to_image(self, image, cloud):
        image = NodeImage(id=image['id'],
                          name="%s: %s" % (cloud, image['label']),
                          driver=self.connection.driver)

        return image

    def _to_size(self, num):
        size = NodeSize(id=num,
                        name="%d Node" % (num,),
                        ram="%dMB" % (RAM_PER_NODE * num,),
                        disk="%dGB" % (DISK_PER_NODE * num,),
                        bandwidth="%dGB" % (BANDWIDTH_PER_NODE * num,),
                        price=self._get_price_per_node(num) * num,
                        driver=self.connection.driver)
        return size

    def _get_price_per_node(self, num):
        keys = sorted(PRICE_PER_NODE.keys())

        if num >= max(keys):
            return PRICE_PER_NODE[keys[-1]]

        for i in range(0,len(keys)):
            if keys[i] <= num < keys[i+1]:
                return PRICE_PER_NODE[keys[i]]

    def create_node(self, name, image, size, **kwargs):
        headers = {'Content-Type': 'application/json'}
        request = {'virtual_machine':
                        {'label': name,
                         'fqdn': kwargs.get('fqdn', ''),
                         'system_template_id': image.id,
                         'backups_enabled': kwargs.get('backups_enabled', 0),
                         'slices_required': size.id}}

        res = self.connection.request('/virtual_machines.%s' % (API_VERSION,),
                                    data=json.dumps(request),
                                    headers=headers,
                                    method='POST')
        node = self._to_node(res.object['virtual_machine'])
        return node

    def reboot_node(self, node):
        res = self.connection.request('/virtual_machines/%s/%s.%s' % 
                                        (node.id, 'reboot', API_VERSION),
                                        method="POST")
        node = self._to_node(res.object['virtual_machine'])
        return True
    
    def list_sizes(self):
        res = self.connection.request('/nodes.%s' % (API_VERSION,))
        available_nodes = len([size for size in res.object 
                            if not size['slice']["virtual_machine_id"]])
        sizes = [self._to_size(i) for i in range(1,available_nodes + 1)]
        return sizes

    def destroy_node(self, node):
        res = self.connection.request('/virtual_machines/%s.%s' % (node.id, API_VERSION),
                                        method='DELETE')
        return res.status == 200

    def list_nodes(self):
        res = self.connection.request('/virtual_machines.%s' % (API_VERSION,))
        return [self._to_node(i['virtual_machine']) for i in res.object] 

    def list_images(self):
        res = self.connection.request('/available_clouds.%s' % (API_VERSION,))

        images = []
        for cloud in res.object:
            label = cloud['cloud']['label']
            templates = cloud['cloud']['system_templates']
            images.extend([self._to_image(image, label) for image in templates])

        return images

########NEW FILE########
__FILENAME__ = interface
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from zope.interface import Interface, Attribute


class INode(Interface):
    """
    A node (instance, etc)
    """
    uuid = Attribute("""Unique identifier""")
    id = Attribute("""Unique ID provided by the provider (i-abcd1234, etc)""")
    name = Attribute("""Hostname or similar identifier""")
    state = Attribute("""A standard Node state as provided by L{NodeState}""")
    public_ip = Attribute("""Public ip (or hostname) of the Node""")
    private_ip = Attribute("""Private ip (or hostname) of the Node""")
    driver = Attribute("""The NodeDriver that belongs to this Node""")

    def get_uuid():
        """
        Provides a system wide unique ID for the node
        """
    def destroy():
        """
        Call `self.driver.destroy_node(self)`. A convenience method.
        """

    def reboot():
        """
        Call `self.driver.reboot_node(self)`. A convenience method.
        """


class INodeFactory(Interface):
    """
    Create nodes
    """
    def __call__(id, name, state, public_ip, private_ip, driver):
        """
        Set values for ivars, including any other requisite kwargs
        """


class INodeSize(Interface):
    """
    A machine image
    """
    id = Attribute("""Unique ID provided by the provider (m1.small, etc)""")
    name = Attribute("""Name provided by the provider (Small CPU, etc)""")
    ram = Attribute("""Amount of RAM provided in MB (256MB, 1740MB)""")
    disk = Attribute("""Amount of disk provided in GB (200GB)""")
    bandwidth = Attribute("""Amount of total transfer bandwidth in GB""")
    price = Attribute("""Hourly price of this server in USD, estimated if monthly""")
    driver = Attribute("""The NodeDriver that belongs to this Image""")


class INodeSizeFactory(Interface):
    """
    Create nodes
    """
    def __call__(id, name, ram, disk, bandwidth, price, driver):
        """
        Set values for ivars, including any other requisite kwargs
        """


class INodeImage(Interface):
    """
    A machine image
    """
    id = Attribute("""Unique ID provided by the provider (ami-abcd1234, etc)""")
    name = Attribute("""Name provided by the provider (Ubuntu 8.1)""")
    driver = Attribute("""The NodeDriver that belongs to this Image""")


class INodeImageFactory(Interface):
    """
    Create nodes
    """
    def __call__(id, name, driver):
        """
        Set values for ivars, including any other requisite kwargs
        """


class INodeDriverFactory(Interface):
    """
    Create NodeDrivers
    """
    def __call__(key, secret=None, secure=True):
        """
        Set of value for ivars
        """


class INodeDriver(Interface):
    """
    A driver which provides nodes, such as an Amazon EC2 instance, or Slicehost slice
    """

    connection = Attribute("""Represents the IConnection for this driver""")
    type = Attribute("""The type of this provider as defined by L{Provider}""")
    name = Attribute("""A pretty name (Linode, etc) for this provider""")

    NODE_STATE_MAP = Attribute("""A mapping of states found in the response to
                              their standard type. This is a constant.""")

    def create_node(name, image, size, **kwargs):
        """
        Creates a new node based on provided params. Name is ignored on some providers.

        To specify provider-specific options, use keyword arguments.
        """

    def destroy_node(node):
        """
        Returns True if the destroy was successful, otherwise False
        """

    def list_nodes():
        """
        Returns a list of nodes for this provider
        """

    def list_images():
        """
        Returns a list of images for this provider
        """

    def list_sizes():
        """
        Returns a list of sizes for this provider
        """

    def reboot_node(node):
        """
        Returns True if the reboot was successful, otherwise False
        """

class IConnection(Interface):
    """
    A Connection represents an interface between a Client and a Provider's Web
    Service. It is capable of authenticating, making requests, and returning
    responses.
    """
    conn_classes = Attribute("""Classes used to create connections, should be
                            in the form of `(insecure, secure)`""")
    responseCls = Attribute("""Provider-specific Class used for creating
                           responses""")
    connection = Attribute("""Represents the lower-level connection to the
                          server""")
    host = Attribute("""Default host for this connection""")
    port = Attribute("""Default port for this connection. This should be a
                    tuple of the form `(insecure, secure)` or for single-port
                    Providers, simply `(port,)`""")
    secure = Attribute("""Indicates if this is a secure connection. If previous
                      recommendations were followed, it would be advantageous
                      for this to be in the form: 0=insecure, 1=secure""")
    driver = Attribute("""The NodeDriver that belongs to this Node""")

    def connect(host=None, port=None):
        """
        A method for establishing a connection. If no host or port are given,
        existing ivars should be used.
        """

    def request(action, params={}, data='', method='GET'):
        """
        Make a request.

        An `action` should represent a path, such as `/list/nodes`. Query
        parameters necessary to the request should be passed in `params` and
        any data to encode goes in `data`. `method` should be one of: (GET,
        POST).

        Should return a response object (specific to a provider).
        """

    def add_default_params(params):
        """
        Adds default parameters (such as API key, version, etc.) to the passed `params`

        Should return a dictionary.
        """

    def add_default_headers(headers):
        """
        Adds default headers (such as Authorization, X-Foo-Bar) to the passed `headers`

        Should return a dictionary.
        """

    def encode_data(data):
        """
        Data may need to be encoded before sent in a request. If not, simply
        return the data.
        """


class IConnectionKey(IConnection):
    """
    IConnection which only depends on an API key for authentication.
    """
    key = Attribute("""API key, token, etc.""")


class IConnectionUserAndKey(IConnectionKey):
    """
    IConnection which depends on a user identifier and an API for authentication.
    """
    user_id = Attribute("""User identifier""")


class IConnectionKeyFactory(Interface):
    """
    Create Connections which depend solely on an API key.
    """
    def __call__(key, secure=True):
        """
        Create a Connection.

        The acceptance of only `key` provides support for APIs with only one
        authentication bit.
        
        The `secure` argument indicates whether or not a secure connection
        should be made. Not all providers support this, so it may be ignored.
        """


class IConnectionUserAndKeyFactory(Interface):
    """
    Create Connections which depends on both a user identifier and API key.
    """
    def __call__(user_id, key, secure=True):
        """
        Create a Connection.

        The first two arguments provide the initial values for `user_id` and
        `key`, respectively, which should be used for authentication.
        
        The `secure` argument indicates whether or not a secure connection
        should be made. Not all providers support this, so it may be ignored.
        """


class IResponse(Interface):
    """
    A response as provided by a given HTTP Client.
    """
    object = Attribute("""The processed response object, e.g. via lxml or json""")
    body = Attribute("""Unparsed response body""")
    status = Attribute("""Response status code""")
    headers = Attribute("""Response headers""")
    error = Attribute("""Response error, L{None} if no error.""")
    connection = Attribute("""Represents the IConnection for this response""")

    def parse_body():
        """
        Parse the response body (as XML, etc.)
        """

    def parse_error():
        """
        Parse the error that is contained in the response body (as XML, etc.)
        """

    def success():
        """
        Does the response indicate a successful request?
        """


class IResponseFactory(Interface):
    """
    Creates Responses.
    """
    def __call__(response):
        """
        Process the given response, setting ivars.
        """


########NEW FILE########
__FILENAME__ = providers
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from libcloud.types import Provider
from libcloud.drivers.linode import LinodeNodeDriver as Linode
from libcloud.drivers.slicehost import SlicehostNodeDriver as Slicehost
from libcloud.drivers.rackspace import RackspaceNodeDriver as Rackspace

DRIVERS = {
#    Provider.DUMMY:
#        ('libcloud.drivers.dummy', 'DummyNodeDriver'),
    Provider.EC2:
        ('libcloud.drivers.ec2', 'EC2NodeDriver'),
    Provider.EC2_EU:
        ('libcloud.drivers.ec2', 'EC2EUNodeDriver'),
#    Provider.GOGRID:
#        ('libcloud.drivers.gogrid', 'GoGridNodeDriver'),
    Provider.RACKSPACE:
        ('libcloud.drivers.rackspace', 'RackspaceNodeDriver'),
    Provider.SLICEHOST:
        ('libcloud.drivers.slicehost', 'SlicehostNodeDriver'),
    Provider.VPSNET:
        ('libcloud.drivers.vpsnet', 'VPSNetNodeDriver'),
    Provider.LINODE:
        ('libcloud.drivers.linode', 'LinodeNodeDriver'),
    Provider.RIMUHOSTING:
        ('libcloud.drivers.rimuhosting', 'RimuHostingNodeDriver')
}

def get_driver(provider):
    if provider in DRIVERS:
        mod_name, driver_name = DRIVERS[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)

########NEW FILE########
__FILENAME__ = types
# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
class Provider(object):
    """ Defines for each of the supported providers """
    DUMMY = 0 # Example provider
    EC2 = 1 # Amazon AWS
    EC2_EU = 2 # Amazon AWS EU
    RACKSPACE = 3 # Cloud Servers
    SLICEHOST = 4 # Cloud Servers
    GOGRID = 5 # GoGrid 
    VPSNET = 6 # VPS.net
    LINODE = 7 # Linode.com
    VCLOUD = 8 # vCloud
    RIMUHOSTING = 9 #RimuHosting.com

class NodeState(object):
    """ Standard states for a node """
    RUNNING = 0
    REBOOTING = 1
    TERMINATED = 2
    PENDING = 3
    UNKNOWN = 4

class InvalidCredsException(Exception):
    def __init__(self, value='Invalid credentials with the provider'):
        self.value = value
    def __str__(self):
        return repr(self.value)

########NEW FILE########
__FILENAME__ = maintenance
#!/usr/bin/env python
# Copyright (c) 2009, Steve Oliver (steve@xercestech.com)
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY STEVE OLIVER ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STEVE OLIVER BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import cgi
import logging
import wsgiref.handlers
from models import *
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class Maintenance(webapp.RequestHandler):

  def get(self):
    serverlist = db.GqlQuery("SELECT * FROM Server")
    for server in serverlist:
        if server.notifylimiter == True:
            logging.info('removing notification limit for %s' % server.serverdomain)
            server.notifylimiter = False
            server.put()
        else:
            pass
    
def main():
  application = webapp.WSGIApplication([('/maintenance', Maintenance)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# Copyright (c) 2009, Steve Oliver (steve@xercestech.com)
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY STEVE OLIVER ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STEVE OLIVER BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from google.appengine.ext import db

class Server(db.Model):
	serverdomain = db.StringProperty("Server Domain", multiline=False)
	ssl = db.BooleanProperty("Is server SSL?", default=False)
	email = db.EmailProperty("Email Address for notification")
	startedmonitoring = db.DateTimeProperty("Date monitoring started", auto_now_add=True)
	timeservercameback = db.DateTimeProperty("Date server came back online", auto_now_add=True)
	status = db.BooleanProperty("Server Status", default=False)
	responsecode = db.IntegerProperty("Server response code", default=000)
	notifylimiter = db.BooleanProperty("Notify limiter", default=False)
	uptimecounter = db.IntegerProperty("Uptime Counter", default=0)
	notifywithprowl = db.BooleanProperty("Prowl notifications",default=False)
	notifywithemail = db.BooleanProperty("Email notifications",default=False)
	notifywithtwitter = db.BooleanProperty("Twitter notifications",default=False)
	notifywithfacebook = db.BooleanProperty("Facebook notifications",default=False)
	notifywithsms = db.BooleanProperty("SMS notifications",default=False)
	falsepositivecheck = db.BooleanProperty("Prevent single bad result from triggering notifications",default=False)
	uptime = db.StringProperty("Uptime")
	class Uptime(db.Model):
		unittime = db.DateTimeProperty("Time period for uptime data", auto_now_add=False)
		uptimecounter = db.IntegerProperty("Counter for uptime in minutes for the time period", default=0)
		downtimecounter = db.IntegerProperty("Counter for downtime in minutes for the time period", default=0)
    
class AdminOptions(db.Model):
	twitteruser = db.StringProperty("Twitter Username", multiline=False)
	twitterpass = db.StringProperty("Twitter Passowrd", multiline=False)
	facebookconnect = db.StringProperty("Facebook connect", multiline=False)
	mobilesmsnumber = db.StringProperty("Mobile SMS number", multiline=False)
	prowlkey = db.StringProperty("Prowl API Key", multiline=False)
	prowlkeyisvalid = db.BooleanProperty("Prowl key status", default=False)

########NEW FILE########
__FILENAME__ = prowlpy
# -*- coding: utf-8 -*-
"""
Prowlpy V0.4.1

Written by Jacob Burch, 7/6/2009

Python module for posting to the iPhone Push Notification service Prowl: http://prowl.weks.net/
"""
__author__ = 'jacobburch@gmail.com'
__version__ = 0.41

import httplib2
import urllib

API_DOMAIN = 'https://prowl.weks.net/publicapi'

class Prowl(object):
    def __init__(self, apikey):
        """
        Initialize a Prowl instance.
        """
        self.apikey = apikey
        
        # Aliasing
        self.add = self.post
        
    def post(self, application=None, event=None, description=None,priority=0):
        # Create the http object
        h = httplib2.Http()
        
        # Set User-Agent
        headers = {'User-Agent': "Prowlpy/%s" % str(__version__)}
        
        # Perform the request and get the response headers and content
        data = {
            'apikey': self.apikey,
            'application': application,
            'event': event,
            'description': description,
            'priority': priority

        }
        headers["Content-type"] = "application/x-www-form-urlencoded"
        resp,content = h.request("%s/add/" % API_DOMAIN, "POST", headers=headers, body=urllib.urlencode(data))
        
        if resp['status'] == '200':
            return True
        elif resp['status'] == '401': 
            raise Exception("Auth Failed: %s" % content)
        else:
            raise Exception("Failed")
        
    
    def verify_key(self):
        h = httplib2.Http()
        headers = {'User-Agent': "Prowlpy/%s" % str(__version__)}
        verify_resp,verify_content = h.request("%s/verify?apikey=%s" % \
                                                    (API_DOMAIN,self.apikey))
        if verify_resp['status'] != '200':
            raise Exception("Invalid API Key %s" % verify_content)
        else:
            return True
########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''A library that provides a python interface to the Twitter API'''

__author__ = 'dewitt@google.com'
__version__ = '0.6-devel'


import base64
import calendar
import os
import rfc822
import simplejson
import sys
import tempfile
import textwrap
import time
import urllib
import urllib2
import urlparse

try:
  from hashlib import md5
except ImportError:
  from md5 import md5


CHARACTER_LIMIT = 140


class TwitterError(Exception):
  '''Base class for Twitter errors'''
  
  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.relative_created_at # read only
    status.user
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               id=None,
               text=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at: The time this status message was posted
      favorited: Whether this is a favorite of the authenticated user
      id: The unique id of this status message
      text: The text of this status message
      relative_created_at:
        A human readable string representing the posting time
      user:
        A twitter.User instance representing the person posting the message
      now:
        The current time, if the client choses to set it.  Defaults to the
        wall clock time.
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.id = id
    self.text = text
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.source = source

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at: The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited: boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id: The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text: The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human redable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge):
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge):
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing'
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User reprenting the entity posting this status message.

    Returns:
      A twitter.User reprenting the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User reprenting the entity posting this status message.

    Args:
      user: A twitter.User reprenting the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User reprenting the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now: The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')


  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.favorited == other.favorited and \
             self.source == other.source
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  source=data.get('source', None),
                  user=user)


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status


  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short username of this user.

    Returns:
      The short username of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short username of this user.

    Args:
      screen_name: the short username of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short username of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone: The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status: The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                  doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.
    
    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count: The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                  doc='The number of friends for this user.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.
    
    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count: The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                  doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.
    
    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count: The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                  doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.
    
    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count: The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                  doc='The number of favourites for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url', None),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.

  The DirectMessage structure exposes the following properties:

    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id: The unique id of this direct message
      created_at: The time this direct message was posted
      sender_id: The id of the twitter user that sent this message
      sender_screen_name: The name of the twitter user that sent this message
      recipient_id: The id of the twitter that received this message
      recipient_screen_name: The name of the twitter that received this message
      text: The text of this direct message
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id: The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at: The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender id: The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name: The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient id: The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name: The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text: The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    username and password:

      >>> api = twitter.Api(username='twitter user', password='twitter pass')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute

  _API_REALM = 'Twitter API'

  def __init__(self,
               username=None,
               password=None,
               input_encoding=None,
               request_headers=None):
    '''Instantiate a new twitter.Api object.

    Args:
      username: The username of the twitter account.  [optional]
      password: The password for the twitter account. [optional]
      input_encoding: The encoding used to encode input strings. [optional]
      request_header: A dictionary of additional HTTP request headers. [optional]
    '''
    self._cache = _FileCache()
    self._urllib = urllib2
    self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()
    self._input_encoding = input_encoding
    self.SetCredentials(username, password)

  def GetPublicTimeline(self, since_id=None):
    '''Fetch the sequnce of public twitter.Status message for all users.

    Args:
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      An sequence of twitter.Status instances, one for each message
    '''
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    url = 'http://twitter.com/statuses/public_timeline.json'
    json = self._FetchUrl(url,  parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriendsTimeline(self,
                         user=None,
                         count=None,
                         since=None, 
                         since_id=None):
    '''Fetch the sequence of twitter.Status messages for a user's friends

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If unspecified, the username and password
        must be set in the twitter.Api instance.  [Optional]
      count: 
        Specifies the number of statuses to retrieve. May not be
        greater than 200. [Optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [Optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    if user:
      url = 'http://twitter.com/statuses/friends_timeline/%s.json' % user
    elif not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = 'http://twitter.com/statuses/friends_timeline.json'
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self, user=None, count=None, since=None, since_id=None):
    '''Fetch the sequence of public twitter.Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        either the username (short_name) or id of the user to retrieve.  If
        not specified, then the current authenticated user is used. [optional]
      count: the number of status messages to retrieve [optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message up to count
    '''
    try:
      if count:
        int(count)
    except:
      raise TwitterError("Count must be an integer")
    parameters = {}
    if count:
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if user:
      url = 'http://twitter.com/statuses/user_timeline/%s.json' % user
    elif not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = 'http://twitter.com/statuses/user_timeline.json'
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self, id):
    '''Returns a single status message.

    The twitter.Api instance must be authenticated if the status message is private.

    Args:
      id: The numerical ID of the status you're trying to retrieve.

    Returns:
      A twitter.Status instance representing that status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an long integer")
    url = 'http://twitter.com/statuses/show/%s.json' % id
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and thee
    authenticating user must be the author of the specified status.

    Args:
      id: The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an integer")
    url = 'http://twitter.com/statuses/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdate(self, status, in_reply_to_status_id=None):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  Must be less than or equal to
        140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = 'http://twitter.com/statuses/update.json'

    if len(status) > CHARACTER_LIMIT:
      raise TwitterError("Text must be less than or equal to %d characters. "
                         "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.
    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def GetReplies(self, since=None, since_id=None, page=None): 
    '''Get a sequence of status messages representing the 20 most recent
    replies (status updates prefixed with @username) to the authenticating
    user.

    Args:
      page: 
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each reply to the user.
    '''
    url = 'http://twitter.com/statuses/replies.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriends(self, user=None, page=None):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    Args:
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    if user:
      url = 'http://twitter.com/statuses/friends/%s.json' % user 
    else:
      url = 'http://twitter.com/statuses/friends.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFollowers(self, page=None):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = 'http://twitter.com/statuses/followers.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFeatured(self):
    '''Fetch the sequence of twitter.User instances featured on twitter.com

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances
    '''
    url = 'http://twitter.com/statuses/featured.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetUser(self, user):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user: The username or id of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show/%s.json' % user
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since=None, since_id=None, page=None):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = 'http://twitter.com/direct_messages.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page 
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, user, text):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      user: The ID or screen name of the recipient user.
      text: The message text to be posted.  Must be less than 140 characters.

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = 'http://twitter.com/direct_messages/new.json'
    data = {'text': text, 'user': user}
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url = 'http://twitter.com/direct_messages/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user):
    '''Befriends the user specified in the user parameter as the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user to befriend.
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url = 'http://twitter.com/friendships/create/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user):
    '''Discontinues friendship with the user specified in the user parameter.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user  with whom to discontinue friendship.
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url = 'http://twitter.com/friendships/destroy/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status):
    '''Favorites the status specified in the status parameter as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status instance to mark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url = 'http://twitter.com/favorites/create/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status):
    '''Un-favorites the status specified in the ID parameter as the authenticating user.
    Returns the un-favorited status in the requested format when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status to unmark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url = 'http://twitter.com/favorites/destroy/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def GetUserByEmail(self, email):
    '''Returns a single user by email address.

    Args:
      email: The email of the user to retrieve.
    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show.json?email=%s' % email
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def SetCredentials(self, username, password):
    '''Set the username and password for this instance

    Args:
      username: The twitter username.
      password: The twitter password.
    '''
    self._username = username
    self._password = password

  def ClearCredentials(self):
    '''Clear the username and password for this instance
    '''
    self._username = None
    self._password = None

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache: an instance that supports the same API as the  twitter._FileCache
    '''
    self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib: an instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout: time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent: a string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _AddAuthorizationHeader(self, username, password):
    if username and password:
      basic_auth = base64.encodestring('%s:%s' % (username, password))[:-1]
      self._request_headers['Authorization'] = 'Basic %s' % basic_auth

  def _RemoveAuthorizationHeader(self):
    if self._request_headers and 'Authorization' in self._request_headers:
      del self._request_headers['Authorization']

  def _GetOpener(self, url, username=None, password=None):
    if username and password:
      self._AddAuthorizationHeader(username, password)
      handler = self._urllib.HTTPBasicAuthHandler()
      (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
      handler.add_password(Api._API_REALM, netloc, username, password)
      opener = self._urllib.build_opener(handler)
    else:
      opener = self._urllib.build_opener()
    opener.addheaders = self._request_headers.items()
    return opener

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data: A python dict created from the Twitter json response
    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url: The URL to retrieve
      post_data: 
        A dict of (str, unicode) key/value pairs.  If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added 
        to the query string. [OPTIONAL]
      no_cache: If true, overrides the cache on the current request

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    # Add key/value parameters to the query string of the url
    url = self._BuildUrl(url, extra_params=extra_params)

    # Get a url opener that can handle basic auth
    opener = self._GetOpener(url, username=self._username, password=self._password)

    encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      url_data = opener.open(url, encoded_post_data).read()
      opener.close()
    else:
      # Unique keys are a combination of the url and the username
      if self._username:
        key = self._username + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        url_data = opener.open(url, encoded_post_data).read()
        opener.close()
        self._cache.Set(key, url_data)
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data


class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()
        
    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])

########NEW FILE########
