__FILENAME__ = ga
"""
Python implementation of ga.php.  
"""
import re
from hashlib import md5
from random import randint
import struct
import httplib2
import time
from urllib import unquote, quote
from Cookie import SimpleCookie, CookieError
from messaging import stdMsg, dbgMsg, errMsg, setDebugging
import uuid

try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    from cgi import parse_qsl

VERSION = "4.4sh"
COOKIE_NAME = "__utmmobile"
COOKIE_PATH = "/"
COOKIE_USER_PERSISTENCE = 63072000

GIF_DATA = reduce(lambda x,y: x + struct.pack('B', y), 
                  [0x47,0x49,0x46,0x38,0x39,0x61,
                   0x01,0x00,0x01,0x00,0x80,0x00,
                   0x00,0x00,0x00,0x00,0xff,0xff,
                   0xff,0x21,0xf9,0x04,0x01,0x00,
                   0x00,0x00,0x00,0x2c,0x00,0x00,
                   0x00,0x00,0x01,0x00,0x01,0x00, 
                   0x00,0x02,0x01,0x44,0x00,0x3b], '')

# WHITE GIF:
# 47 49 46 38 39 61 
# 01 00 01 00 80 ff 
# 00 ff ff ff 00 00 
# 00 2c 00 00 00 00 
# 01 00 01 00 00 02 
# 02 44 01 00 3b                                       

# TRANSPARENT GIF:
# 47 49 46 38 39 61 
# 01 00 01 00 80 00 
# 00 00 00 00 ff ff 
# ff 21 f9 04 01 00 
# 00 00 00 2c 00 00 
# 00 00 01 00 01 00 
# 00 02 01 44 00 3b                  

def get_ip(remote_address):
    # dbgMsg("remote_address: " + str(remote_address))
    if not remote_address:
        return ""
    matches = re.match('^([^.]+\.[^.]+\.[^.]+\.).*', remote_address)
    if matches:
        return matches.groups()[0] + "0"
    else:
        return ""

def get_visitor_id(guid, account, user_agent, cookie):
    """
     // Generate a visitor id for this hit.
     // If there is a visitor id in the cookie, use that, otherwise
     // use the guid if we have one, otherwise use a random number.
    """
    if cookie:
        return cookie
    message = ""
    if guid:
        # Create the visitor id using the guid.
        message = guid + account
    else:
        # otherwise this is a new user, create a new random id.
        message = user_agent + str(uuid.uuid4())
    md5String = md5(message).hexdigest()
    return "0x" + md5String[:16]

def get_random_number():
    """
    // Get a random number string.
    """
    return str(randint(0, 0x7fffffff))

def write_gif_data():
    """
    // Writes the bytes of a 1x1 transparent gif into the response.

    Returns a dictionary with the following values: 
    
    { 'response_code': '200 OK',
      'response_headers': [(Header_key, Header_value), ...]
      'response_body': 'binary data'
    }
    """
    response = {'response_code': '204 No Content', 
                'response_headers': [('Content-Type', 'image/gif'),                                     
                                     ('Cache-Control', 'private, no-cache, no-cache=Set-Cookie, proxy-revalidate'),
                                     ('Pragma', 'no-cache'),
                                     ('Expires', 'Wed, 17 Sep 1975 21:32:10 GMT'),
                                     ],
                # 'response_body': GIF_DATA,
                'response_body': '',
                }
    return response

def send_request_to_google_analytics(utm_url, environ):
    """
  // Make a tracking request to Google Analytics from this server.
  // Copies the headers from the original request to the new one.
  // If request containg utmdebug parameter, exceptions encountered
  // communicating with Google Analytics are thown.    
    """
    http = httplib2.Http()    
    try:
        resp, content = http.request(utm_url, 
                                     "GET", 
                                     headers={'User-Agent': environ.get('HTTP_USER_AGENT', 'Unknown'),
                                              'Accepts-Language:': environ.get("HTTP_ACCEPT_LANGUAGE",'')}
                                     )
        # dbgMsg("success")            
    except httplib2.HttpLib2Error, e:
        errMsg("fail: %s" % utm_url)            
        if environ['GET'].get('utmdebug'):
            raise Exception("Error opening: %s" % utm_url)
        else:
            pass

        
def parse_cookie(cookie):
    """ borrowed from django.http """
    if cookie == '':
        return {}
    try:
        c = SimpleCookie()
        c.load(cookie)
    except CookieError:
        # Invalid cookie
        return {}

    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict        
        
def track_page_view(environ):
    """
    // Track a page view, updates all the cookies and campaign tracker,
    // makes a server side request to Google Analytics and writes the transparent
    // gif byte data to the response.
    """    
    time_tup = time.localtime(time.time() + COOKIE_USER_PERSISTENCE)
    
    # set some useful items in environ: 
    environ['COOKIES'] = parse_cookie(environ.get('HTTP_COOKIE', ''))
    environ['GET'] = {}
    for key, value in parse_qsl(environ.get('QUERY_STRING', ''), True):
        environ['GET'][key] = value # we only have one value per key name, right? :) 
    x_utmac = environ['GET'].get('x_utmac', None)
    
    domain = environ.get('HTTP_HOST', '')
            
    # Get the referrer from the utmr parameter, this is the referrer to the
    # page that contains the tracking pixel, not the referrer for tracking
    # pixel.    
    document_referer = environ['GET'].get("utmr", "")
    if not document_referer or document_referer == "0":
        document_referer = "-"
    else:
        document_referer = unquote(document_referer)

    document_path = environ['GET'].get('utmp', "")
    if document_path:
        document_path = unquote(document_path)

    account = environ['GET'].get('utmac', '')      
    user_agent = environ.get("HTTP_USER_AGENT", '')    

    # // Try and get visitor cookie from the request.
    cookie = environ['COOKIES'].get(COOKIE_NAME)

    visitor_id = get_visitor_id(environ.get("HTTP_X_DCMGUID", ''), account, user_agent, cookie)
    
    # // Always try and add the cookie to the response.
    cookie = SimpleCookie()
    cookie[COOKIE_NAME] = visitor_id
    morsel = cookie[COOKIE_NAME]
    morsel['expires'] = time.strftime('%a, %d-%b-%Y %H:%M:%S %Z', time_tup) 
    morsel['path'] = COOKIE_PATH

    utm_gif_location = "http://www.google-analytics.com/__utm.gif"

    for utmac in [account, x_utmac]:
        if not utmac:
            continue # ignore empty utmacs
        # // Construct the gif hit url.
        utm_url = utm_gif_location + "?" + \
                "utmwv=" + VERSION + \
                "&utmn=" + get_random_number() + \
                "&utmhn=" + quote(domain) + \
                "&utmsr=" + environ['GET'].get('utmsr', '') + \
                "&utme=" + environ['GET'].get('utme', '') + \
                "&utmr=" + quote(document_referer) + \
                "&utmp=" + quote(document_path) + \
                "&utmac=" + utmac + \
                "&utmcc=__utma%3D999.999.999.999.999.1%3B" + \
                "&utmvid=" + visitor_id + \
                "&utmip=" + get_ip(environ.get("REMOTE_ADDR",''))
        # dbgMsg("utm_url: " + utm_url)    
        send_request_to_google_analytics(utm_url, environ)

    # // If the debug parameter is on, add a header to the response that contains
    # // the url that was used to contact Google Analytics.
    headers = [('Set-Cookie', str(cookie).split(': ')[1])]
    if environ['GET'].get('utmdebug', False):
        headers.append(('X-GA-MOBILE-URL', utm_url))
    
    # Finally write the gif data to the response
    response = write_gif_data()
    response_headers = response['response_headers']
    response_headers.extend(headers)
    return response
########NEW FILE########
__FILENAME__ = models
#Blank model so django can understand we want to be an app.

########NEW FILE########
__FILENAME__ = ga_mobile
import os

from django.conf import settings
from django import template
from random import randint
from urllib import quote_plus

register = template.Library()

@register.simple_tag
def ga_mobile(request):
    """
    Returns the image link for tracking this mobile request.
    
    Retrieves two configurations from django.settings:
    
    GA_MOBILE_PATH: path (including leading /) to location of your tracking CGI.
    GA_MOBILE_ACCOUNT: your GA mobile account number such as MO-XXXXXX-XX
    
    Note: the host for the request is by default the same as the HTTP_HOST of the request.
    Override this by setting GA_MOBILE_HOST in settings.
    """

    ga_mobile_path = settings.GA_MOBILE_PATH
    ga_mobile_account = settings.GA_MOBILE_ACCOUNT
    r = str(randint(0, 0x7fffffff))

    if hasattr(settings, 'GA_MOBILE_HOST'):
        host = settings.GA_MOBILE_HOST
    else:
        host = request.META.get('HTTP_HOST', 'localhost')
    referer = quote_plus(request.META.get('HTTP_REFERER', ''))
    path = quote_plus(request.META.get('REQUEST_URI', ''))
    
    src = 'http://' + host + ga_mobile_path + \
        "?utmac=" + ga_mobile_account + \
        "&utmn=" + r + \
        "&utmr=" + referer + \
        "&utmp=" + path + \
        "&guid=ON"

    return '<img src="%s" width="1" height="1">' % src
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^track/$', 'ga_app.views.track', name='webcube_home'),
)
########NEW FILE########
__FILENAME__ = views
from ga import send_request_to_google_analytics, get_random_number, get_visitor_id, get_ip, VERSION, COOKIE_NAME, COOKIE_PATH, COOKIE_USER_PERSISTENCE, GIF_DATA

import httplib2
import time
from urllib import unquote, quote

from urllib import unquote, quote
from django.http import HttpResponse

def track(request):
    """
    Track a page view, updates all the cookies and campaign tracker,
     makes a server side request to Google Analytics and writes the transparent
     gif byte data to the response.
    """
    response = HttpResponse()
    
    time_tup = time.localtime(time.time() + COOKIE_USER_PERSISTENCE)
    
    # set some useful items in environ: 
    x_utmac = request.GET.get('x_utmac', None)
    
    domain = request.META.get('HTTP_HOST', '')
            
    # Get the referrer from the utmr parameter, this is the referrer to the
    # page that contains the tracking pixel, not the referrer for tracking
    # pixel.    
    document_referer = request.GET.get("utmr", "")
    if not document_referer or document_referer == "0":
        document_referer = "-"
    else:
        document_referer = unquote(document_referer)

    document_path = request.GET.get('utmp', "")
    if document_path:
        document_path = unquote(document_path)

    account = request.GET.get('utmac', '')      
    user_agent = request.META.get("HTTP_USER_AGENT", '')    

    # Try and get visitor cookie from the request.
    cookie = request.COOKIES.get(COOKIE_NAME, None)

    visitor_id = get_visitor_id(request.META.get("HTTP_X_DCMGUID", ''), account, user_agent, cookie)
    
    utm_gif_location = "http://www.google-analytics.com/__utm.gif"

    for utmac in [account, x_utmac]:
        if not utmac:
            continue # ignore empty utmacs
        # Construct the gif hit url.
        utm_url = utm_gif_location + "?" + \
                "utmwv=" + VERSION + \
                "&utmn=" + get_random_number() + \
                "&utmhn=" + quote(domain) + \
                "&utmsr=" + request.GET.get('utmsr', '') + \
                "&utme=" + request.GET.get('utme', '') + \
                "&utmr=" + quote(document_referer) + \
                "&utmp=" + quote(document_path) + \
                "&utmac=" + utmac + \
                "&utmcc=__utma%3D999.999.999.999.999.1%3B" + \
                "&utmvid=" + visitor_id + \
                "&utmip=" + get_ip(request.META.get("REMOTE_ADDR",''))
        send_request_to_google_analytics(utm_url, request.META)
    
    # add the cookie to the response.
    response.set_cookie(COOKIE_NAME, value=visitor_id, path=COOKIE_PATH)
    # If the debug parameter is on, add a header to the response that contains
    # the url that was used to contact Google Analytics.
    if request.GET.get('utmdebug', False):
        response['X-GA-MOBILE-URL'] = utm_url
    
    response_headers =[('Content-Type', 'image/gif'),                                     
                         ('Cache-Control', 'private, no-cache, no-cache=Set-Cookie, proxy-revalidate'),
                         ('Pragma', 'no-cache'),
                         ('Expires', 'Wed, 17 Sep 1975 21:32:10 GMT')]
    for header in response_headers:
        key, value = header
        response[key] = value
    response.content = GIF_DATA
    
    return response
########NEW FILE########
__FILENAME__ = ga_mobile_server
#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Serves up google analytics 1x1.gif transparent tracking images and notifies Google Analytics of clicks.  

Created by Peter McLachlan on 2009-07-19.
Copyright (c) 2009 Mobify. All rights reserved.
"""

import sys
import os
import getopt
from urlparse import urlparse
from flup.server.fcgi_fork import WSGIServer
from socket import gethostname
from datetime import datetime, timedelta
from ga import track_page_view

from messaging import stdMsg, dbgMsg, errMsg, setDebugging
setDebugging(1)

MINSPARE = 3
MAXSPARE = 7
MAXCHILDREN = 50
MAXREQUESTS = 500
HOST = '127.0.0.1'
PORT = 8009
PIDFILE = '/tmp/g_analytic_server.pid'
HELP_MESSAGE = """

This is some help.

"""

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def gserve(environ, start_response):    
    try:
        response = track_page_view(environ)
    except Exception, e:
        print e
        start_response("503 Service Unavailable", [])
        return ["<h1>Exception loading GA code</h1><p>%s</p>" % str(e)]
    start_response(response['response_code'], response['response_headers'])
    return [response['response_body']]
    
def main(argv=None):
    host = HOST
    port = PORT
    pidfile = PIDFILE
    maxchildren = MAXCHILDREN
    maxrequests = MAXREQUESTS
    minspare = MINSPARE
    maxspare = MAXSPARE
    
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["host=", "port=", 'pidfile=', 'maxchildren=', 
                                                      'maxrequests=', 'minspare=', 'maxspare=', 'help'])
        except getopt.error, msg:
            raise Usage(msg)
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(HELP_MESSAGE)
            elif "--host" == option:
                host = value
            elif "--port" == option:
                port = int(value)
            elif "--pidfile" == option:
                pidfile = value
            elif "--maxchildren" == option:
                maxchildren = int(value)
            elif "--maxrequests" == option:
                maxrequests = int(value)
            elif "--minspare" == option:
                minspare = int(value)
            elif "--maxspare" == option:
                maxspare = int(value)
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return -2
    
    try:
        f = open(pidfile, 'w')
        f.write(str(os.getpid()) + '\n')
        f.close()
    except IOError, e:
        print "!! Error writing to pid file, check pid file path: %s" % pidfile
        return -1
    
    try:
        WSGIServer(gserve, bindAddress=(host, port), minSpare=minspare, maxSpare=maxspare, maxChildren=maxchildren, maxRequests=maxrequests).run()
    except Exception, e:
        print "!! WSGIServer raised exception" 
        print e
    
    
if __name__ == "__main__":
    sys.exit(main())    
########NEW FILE########
__FILENAME__ = messaging
#messaging.py
#this is a module used for messaging.  It allows multiple classes
#to handle various types of messages.  It should work on all python
#versions >= 1.5.2

import sys, string, exceptions

#this flag determines whether debug output is sent to debug handlers themselves
debug = 1

def setDebugging(debugging):
    global debug
    debug = debugging

class MessagingException(exceptions.Exception):
    """an exception class for any errors that may occur in 
    a messaging function"""
    def __init__(self, args=None):
        self.args = args

class FakeException(exceptions.Exception):
    """an exception that is thrown and then caught
    to get a reference to the current execution frame"""
    pass        
        
        
class MessageHandler:
    """All message handlers should inherit this class.  Each method will be 
    passed a string when the executing program passes calls a messaging function"""
    def handleStdMsg(self, msg):
        """do something with a standard message from the program"""
        pass
    def handleErrMsg(self, msg):
        """do something with an error message.  This will already include the
        class, method, and line of the call"""
        pass
    def handleDbgMsg(self, msg):
        """do something with a debug message.  This will already include the
        class, method, and line of the call"""
        pass

class defaultMessageHandler(MessageHandler):
    """This is a default message handler.  It simply spits all strings to
    standard out"""
    def handleStdMsg(self, msg):
        sys.stdout.write(msg + "\n")
    def handleErrMsg(self, msg):
        sys.stderr.write(msg + "\n")
    def handleDbgMsg(self, msg):
        sys.stdout.write(msg + "\n")

#this keeps track of the handlers
_messageHandlers = []

#call this with the handler to register it for receiving messages
def registerMessageHandler(handler):
    """we're not going to check for inheritance, but we should check to make
    sure that it has the correct methods"""
    for methodName in ["handleStdMsg", "handleErrMsg", "handleDbgMsg"]:
        try:
            getattr(handler, methodName)
        except:            
            raise MessagingException, "The class " + handler.__class__.__name__ + " is missing a " + methodName + " method"
    _messageHandlers.append(handler)
    
    
def getCallString(level):
    #this gets us the frame of the caller and will work
    #in python versions 1.5.2 and greater (there are better
    #ways starting in 2.1
    try:
        raise FakeException("this is fake")
    except Exception, e:
        #get the current execution frame
        f = sys.exc_info()[2].tb_frame
    #go back as many call-frames as was specified
    while level >= 0:        
        f = f.f_back
        level = level-1
    #if there is a self variable in the caller's local namespace then
    #we'll make the assumption that the caller is a class method
    obj = f.f_locals.get("self", None)
    functionName = f.f_code.co_name
    if obj:
        callStr = obj.__class__.__name__+"::"+f.f_code.co_name+" (line "+str(f.f_lineno)+")"
    else:
        callStr = f.f_code.co_name+" (line "+str(f.f_lineno)+")"        
    return callStr        
    
#send this message to all handlers of std messages
def stdMsg(*args):
    stdStr = string.join(map(str, args), " ")
    for handler in _messageHandlers:
        handler.handleStdMsg(stdStr)

#send this message to all handlers of error messages
def errMsg(*args):
    errStr = "Error in "+getCallString(1)+" : "+string.join(map(str, args), " ")
    for handler in _messageHandlers:
        handler.handleErrMsg(errStr)

#send this message to all handlers of debug messages
def dbgMsg(*args):
    if not debug:
        return
    errStr = getCallString(1)+" : "+string.join(map(str, args), " ")
    for handler in _messageHandlers:
        handler.handleDbgMsg(errStr)


registerMessageHandler(defaultMessageHandler())
#end of messaging.py

########NEW FILE########
