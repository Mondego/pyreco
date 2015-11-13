__FILENAME__ = decorators
from urllib import quote as url_quote
from tornado.web import HTTPError
import base64

import functools
import urllib
import urlparse
# taken from tornado.web.authenticated

def authenticated_plus(extra_check):
    """Decorate methods with this to require that the user be logged in."""
    def wrap(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if not (self.current_user and extra_check(self.current_user)):
                if self.request.method in ("GET", "HEAD"):
                    url = self.get_login_url()
                    if "?" not in url:
                        if urlparse.urlsplit(url).scheme:
                            # if login url is absolute, make next absolute too
                            next_url = self.request.full_url()
                        else:
                            next_url = self.request.uri
                        url += "?" + urllib.urlencode(dict(next=next_url))
                    self.redirect(url)
                    return
                raise HTTPError(403)
            return method(self, *args, **kwargs)
        return wrapper
    return wrap


def basic_auth(checkfunc, realm="Authentication Required!"):
    """Decorate methods with this to require basic auth"""
    def wrap(method):
        def request_auth(self):
            self.set_header('WWW-Authenticate', 'Basic realm=%s' % realm)
            self.set_status(401)
            self.finish()
            return False
        
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            auth = self.request.headers.get('Authorization')
            if auth is None or not auth.startswith('Basic '):
                return request_auth(self)
            auth = auth[6:]
            try:
                username, password = base64.decodestring(auth).split(':', 2)
            except:
                return request_auth(self)
            
            if checkfunc(username, password):
                self.request.basic_auth = (username, password)
                return method(self, *args, **kwargs)
            else:
                return request_auth(self)
                
        return wrapper
    
    return wrap

########NEW FILE########
__FILENAME__ = edit_distance
class EditDistance(object):
    def __init__(self, against, alphabet=u'abcdefghijklmnopqrstuvwxyz'):
        self.against = against
        self.alphabet = alphabet

    def match(self, word):
        return list(self._match(word))

    def _match(self, word):
        for w in self._edits1(word):
            if w in self.against:
                yield w

    def _edits1(self, word):
        n = len(word)
        return set(# deletion
                   [word[0:i]+word[i+1:] for i in range(n)] +
                   # transposition
                   [word[0:i]+word[i+1]+word[i]+word[i+2:] for i in range(n-1)] +
                   # alteration
                   [word[0:i]+c+word[i+1:] for i in range(n) for c in self.alphabet] +
                   # insertion
                   [word[0:i]+c+word[i:] for i in range(n+1) for c in self.alphabet])

if __name__ == '__main__':
    against = ('peter',)
    ed = EditDistance(against)
    assert ed.match('peter') == ['peter']
    assert ed.match('petter') == ['peter']
    assert ed.match('peffeer') == []

    against = ('peter','petter')
    ed = EditDistance(against)
    assert ed.match('pettere') == ['petter']

########NEW FILE########
__FILENAME__ = git
import os, re
import logging
from subprocess import Popen, PIPE

def get_git_revision():
    return _get_git_revision()

def _get_git_revision():
    # this is actually very fast. Takes about 0.01 seconds on my machine!
    home = os.path.dirname(__file__)
    proc = Popen('cd %s;git log --no-color -n 1 --date=iso' % home,
                  shell=True, stdout=PIPE, stderr=PIPE)
    output = proc.communicate()
    try:
        date = [x.split('Date:')[1].split('+')[0].strip() for x in
                output[0].splitlines() if x.startswith('Date:')][0]
        date_wo_tz = re.split('-\d{4}', date)[0].strip()
        return date_wo_tz
    except IndexError:
        logging.debug("OUTPUT=%r" % output[0], exc_info=True)
        logging.debug("ERROR=%r" % output[1])
        return 'unknown'

########NEW FILE########
__FILENAME__ = goo_gl
import json
import urllib
import urllib2
import logging
# http://code.google.com/apis/urlshortener/v1/getting_started.html
# This works:
#   curl https://www.googleapis.com/urlshortener/v1/url \
#    -H 'Content-Type: application/json'\
#    -d '{"longUrl": "http://www.peterbe.com"}'
#
URL = 'https://www.googleapis.com/urlshortener/v1/url'

def shorten(url):
    #data = urllib.urlencode({'longUrl': url})
    data = json.dumps({'longUrl': url})
    headers = {'Content-Type': 'application/json'}
    req = urllib2.Request(URL, data, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    logging.info("Shorten %r --> %s" % (url, the_page))
    struct = json.loads(the_page)
    return struct['id']

if __name__ == '__main__':
    import sys
    for url in sys.argv[1:]:
        if '://' in url:
            print shorten(url)

########NEW FILE########
__FILENAME__ = html2text
#!/usr/bin/env python
"""html2text: Turn HTML into equivalent Markdown-structured text."""
__version__ = "3.02"
__author__ = "Aaron Swartz (me@aaronsw.com)"
__copyright__ = "(C) 2004-2008 Aaron Swartz. GNU GPL 3."
__contributors__ = ["Martin 'Joey' Schulze", "Ricardo Reyes", "Kevin Jay North"]

# TODO:
#   Support decoded entities with unifiable.

try:
    True
except NameError:
    setattr(__builtins__, 'True', 1)
    setattr(__builtins__, 'False', 0)

def has_key(x, y):
    if hasattr(x, 'has_key'): return x.has_key(y)
    else: return y in x

try:
    import htmlentitydefs
    import urlparse
    import HTMLParser
except ImportError: #Python3
    import html.entities as htmlentitydefs
    import urllib.parse as urlparse
    import html.parser as HTMLParser
try: #Python3
    import urllib.request as urllib
except:
    import urllib
import optparse, re, sys, codecs, types

try: from textwrap import wrap
except: pass

# Use Unicode characters instead of their ascii psuedo-replacements
UNICODE_SNOB = 0

# Put the links after each paragraph instead of at the end.
LINKS_EACH_PARAGRAPH = 0

# Wrap long lines at position. 0 for no wrapping. (Requires Python 2.3.)
BODY_WIDTH = 78

# Don't show internal links (href="#local-anchor") -- corresponding link targets
# won't be visible in the plain text file anyway.
SKIP_INTERNAL_LINKS = False

### Entity Nonsense ###

def name2cp(k):
    if k == 'apos': return ord("'")
    if hasattr(htmlentitydefs, "name2codepoint"): # requires Python 2.3
        return htmlentitydefs.name2codepoint[k]
    else:
        k = htmlentitydefs.entitydefs[k]
        if k.startswith("&#") and k.endswith(";"): return int(k[2:-1]) # not in latin-1
        return ord(codecs.latin_1_decode(k)[0])

unifiable = {'rsquo':"'", 'lsquo':"'", 'rdquo':'"', 'ldquo':'"', 
'copy':'(C)', 'mdash':'--', 'nbsp':' ', 'rarr':'->', 'larr':'<-', 'middot':'*',
'ndash':'-', 'oelig':'oe', 'aelig':'ae',
'agrave':'a', 'aacute':'a', 'acirc':'a', 'atilde':'a', 'auml':'a', 'aring':'a', 
'egrave':'e', 'eacute':'e', 'ecirc':'e', 'euml':'e', 
'igrave':'i', 'iacute':'i', 'icirc':'i', 'iuml':'i',
'ograve':'o', 'oacute':'o', 'ocirc':'o', 'otilde':'o', 'ouml':'o', 
'ugrave':'u', 'uacute':'u', 'ucirc':'u', 'uuml':'u'}

unifiable_n = {}

for k in unifiable.keys():
    unifiable_n[name2cp(k)] = unifiable[k]

def charref(name):
    if name[0] in ['x','X']:
        c = int(name[1:], 16)
    else:
        c = int(name)
    
    if not UNICODE_SNOB and c in unifiable_n.keys():
        return unifiable_n[c]
    else:
        try:
            return unichr(c)
        except NameError: #Python3
            return chr(c)

def entityref(c):
    if not UNICODE_SNOB and c in unifiable.keys():
        return unifiable[c]
    else:
        try: name2cp(c)
        except KeyError: return "&" + c + ';'
        else:
            try:
                return unichr(name2cp(c))
            except NameError: #Python3
                return chr(name2cp(c))

def replaceEntities(s):
    s = s.group(1)
    if s[0] == "#": 
        return charref(s[1:])
    else: return entityref(s)

r_unescape = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
def unescape(s):
    return r_unescape.sub(replaceEntities, s)

### End Entity Nonsense ###

def onlywhite(line):
    """Return true if the line does only consist of whitespace characters."""
    for c in line:
        if c is not ' ' and c is not '  ':
            return c is ' '
    return line

def optwrap(text):
    """Wrap all paragraphs in the provided text."""
    if not BODY_WIDTH:
        return text
    
    assert wrap, "Requires Python 2.3."
    result = ''
    newlines = 0
    for para in text.split("\n"):
        if len(para) > 0:
            if para[0] != ' ' and para[0] != '-' and para[0] != '*':
                for line in wrap(para, BODY_WIDTH):
                    result += line + "\n"
                result += "\n"
                newlines = 2
            else:
                if not onlywhite(para):
                    result += para + "\n"
                    newlines = 1
        else:
            if newlines < 2:
                result += "\n"
                newlines += 1
    return result

def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10): return n
        except ValueError: return 0

class _html2text(HTMLParser.HTMLParser):
    def __init__(self, out=None, baseurl=''):
        HTMLParser.HTMLParser.__init__(self)
        
        if out is None: self.out = self.outtextf
        else: self.out = out
        try:
            self.outtext = unicode()
        except NameError: # Python3
            self.outtext = str()
        self.quiet = 0
        self.p_p = 0
        self.outcount = 0
        self.start = 1
        self.space = 0
        self.a = []
        self.astack = []
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.startpre = 0
        self.lastWasNL = 0
        self.abbr_title = None # current abbreviation definition
        self.abbr_data = None # last inner HTML (for abbr being defined)
        self.abbr_list = {} # stack of abbreviations to write later
        self.baseurl = baseurl
    
    def outtextf(self, s): 
        self.outtext += s
    
    def close(self):
        HTMLParser.HTMLParser.close(self)
        
        self.pbr()
        self.o('', 0, 'end')
        
        return self.outtext
        
    def handle_charref(self, c):
        self.o(charref(c))

    def handle_entityref(self, c):
        self.o(entityref(c))
            
    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)
    
    def handle_endtag(self, tag):
        self.handle_tag(tag, None, 0)
        
    def previousIndex(self, attrs):
        """ returns the index of certain set of attributes (of a link) in the
            self.a list
 
            If the set of attributes is not found, returns None
        """
        if not has_key(attrs, 'href'): return None
        
        i = -1
        for a in self.a:
            i += 1
            match = 0
            
            if has_key(a, 'href') and a['href'] == attrs['href']:
                if has_key(a, 'title') or has_key(attrs, 'title'):
                        if (has_key(a, 'title') and has_key(attrs, 'title') and
                            a['title'] == attrs['title']):
                            match = True
                else:
                    match = True

            if match: return i

    def handle_tag(self, tag, attrs, start):
        #attrs = fixattrs(attrs)
    
        if hn(tag):
            self.p()
            if start: self.o(hn(tag)*"#" + ' ')

        if tag in ['p', 'div']: self.p()
        
        if tag == "br" and start: self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", 'script']: 
            if start: self.quiet += 1
            else: self.quiet -= 1

        if tag in ["body"]:
            self.quiet = 0 # sites like 9rules.com never close <head>
        
        if tag == "blockquote":
            if start: 
                self.p(); self.o('> ', 0, 1); self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()
        
        if tag in ['em', 'i', 'u']: self.o("_")
        if tag in ['strong', 'b']: self.o("**")
        if tag == "code" and not self.pre: self.o('`') #TODO: `` `this` ``
        if tag == "abbr":
            if start:
                attrsD = {}
                for (x, y) in attrs: attrsD[x] = y
                attrs = attrsD
                
                self.abbr_title = None
                self.abbr_data = ''
                if has_key(attrs, 'title'):
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title != None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''
        
        if tag == "a":
            if start:
                attrsD = {}
                for (x, y) in attrs: attrsD[x] = y
                attrs = attrsD
                if has_key(attrs, 'href') and not (SKIP_INTERNAL_LINKS and attrs['href'].startswith('#')): 
                    self.astack.append(attrs)
                    self.o("[")
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if a:
                        i = self.previousIndex(a)
                        if i is not None:
                            a = self.a[i]
                        else:
                            self.acount += 1
                            a['count'] = self.acount
                            a['outcount'] = self.outcount
                            self.a.append(a)
                        self.o("][" + str(a['count']) + "]")
        
        if tag == "img" and start:
            attrsD = {}
            for (x, y) in attrs: attrsD[x] = y
            attrs = attrsD
            if has_key(attrs, 'src'):
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                i = self.previousIndex(attrs)
                if i is not None:
                    attrs = self.a[i]
                else:
                    self.acount += 1
                    attrs['count'] = self.acount
                    attrs['outcount'] = self.outcount
                    self.a.append(attrs)
                self.o("![")
                self.o(alt)
                self.o("]["+ str(attrs['count']) +"]")
        
        if tag == 'dl' and start: self.p()
        if tag == 'dt' and not start: self.pbr()
        if tag == 'dd' and start: self.o('    ')
        if tag == 'dd' and not start: self.pbr()
        
        if tag in ["ol", "ul"]:
            if start:
                self.list.append({'name':tag, 'num':0})
            else:
                if self.list: self.list.pop()
            
            self.p()
        
        if tag == 'li':
            if start:
                self.pbr()
                if self.list: li = self.list[-1]
                else: li = {'name':'ul', 'num':0}
                self.o("  "*len(self.list)) #TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul": self.o("* ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(str(li['num'])+". ")
                self.start = 1
            else:
                self.pbr()
        
        if tag in ["table", "tr"] and start: self.p()
        if tag == 'td': self.pbr()
        
        if tag == "pre":
            if start:
                self.startpre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()
            
    def pbr(self):
        if self.p_p == 0: self.p_p = 1

    def p(self): self.p_p = 2
    
    def o(self, data, puredata=0, force=0):
        if self.abbr_data is not None: self.abbr_data += data
        
        if not self.quiet: 
            if puredata and not self.pre:
                data = re.sub('\s+', ' ', data)
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force: return
            
            if self.startpre:
                #self.out(" :") #TODO: not output when already one there
                self.startpre = 0
            
            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote: bq += " "
            
            if self.pre:
                bq += "    "
                data = data.replace("\n", "\n"+bq)
            
            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = 0

            if force == 'end':
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = 0


            if self.p_p:
                self.out(('\n'+bq)*self.p_p)
                self.space = 0
                
            if self.space:
                if not self.lastWasNL: self.out(' ')
                self.space = 0

            if self.a and ((self.p_p == 2 and LINKS_EACH_PARAGRAPH) or force == "end"):
                if force == "end": self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link['outcount']:
                        self.out("   ["+ str(link['count']) +"]: " + urlparse.urljoin(self.baseurl, link['href'])) 
                        if has_key(link, 'title'): self.out(" ("+link['title']+")")
                        self.out("\n")
                    else:
                        newa.append(link)

                if self.a != newa: self.out("\n") # Don't need an extra line when nothing was done.

                self.a = newa
            
            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.lastWasNL = data and data[-1] == '\n'
            self.outcount += 1

    def handle_data(self, data):
        if r'\/script>' in data: self.quiet -= 1
        self.o(data, 1)
    
    def unknown_decl(self, data): pass

def wrapwrite(text):
    text = text.encode('utf-8')
    try: #Python3
        sys.stdout.buffer.write(text)
    except AttributeError:
        sys.stdout.write(text)

def html2text_file(html, out=wrapwrite, baseurl=''):
    h = _html2text(out, baseurl)
    h.feed(html)
    h.feed("")
    return h.close()

def html2text(html, baseurl=''):
    return optwrap(html2text_file(html, None, baseurl))

if __name__ == "__main__":
    baseurl = ''

    p = optparse.OptionParser('%prog [(filename|url) [encoding]]',
                              version='%prog ' + __version__)
    args = p.parse_args()[1]
    if len(args) > 0:
        file_ = args[0]
        encoding = None
        if len(args) == 2:
            encoding = args[1]
        if len(args) > 2:
            p.error('Too many arguments')

        if file_.startswith('http://') or file_.startswith('https://'):
            baseurl = file_
            j = urllib.urlopen(baseurl)
            text = j.read()
            if encoding is None:
                try:
                    from feedparser import _getCharacterEncoding as enc
                except ImportError:
                    enc = lambda x, y: ('utf-8', 1)
                encoding = enc(j.headers, text)[0]
                if encoding == 'us-ascii':
                    encoding = 'utf-8'
            data = text.decode(encoding)

        else:
            data = open(file_, 'rb').read()
            if encoding is None:
                try:
                    from chardet import detect
                except ImportError:
                    detect = lambda x: {'encoding': 'utf-8'}
                encoding = detect(data)['encoding']
            data = data.decode(encoding)
    else:
        data = sys.stdin.read()
    wrapwrite(html2text(data, baseurl))

########NEW FILE########
__FILENAME__ = http_test_client
from urllib import urlencode
import Cookie
from tornado.httpclient import HTTPRequest
from tornado import escape

__version__ = '1.3'

class LoginError(Exception):
    pass

class HTTPClientMixin(object):

    def get(self, url, data=None, headers=None, follow_redirects=False):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data, True)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'GET', headers=headers,
                           follow_redirects=follow_redirects)

    def post(self, url, data, headers=None, follow_redirects=False):
        if data is not None:
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, unicode):
                        data[key] = value.encode('utf-8')
                data = urlencode(data, True)
        return self._fetch(url, 'POST', data, headers,
                           follow_redirects=follow_redirects)

    def _fetch(self, url, method, data=None, headers=None, follow_redirects=True):
        full_url = self.get_url(url)
        request = HTTPRequest(full_url, follow_redirects=follow_redirects,
                              headers=headers, method=method, body=data)
        self.http_client.fetch(request, self.stop)
        return self.wait()


class TestClient(HTTPClientMixin):
    def __init__(self, testcase):
        self.testcase = testcase
        self.cookies = Cookie.SimpleCookie()

    def _render_cookie_back(self):
        return ''.join(['%s=%s;' %(x, morsel.value)
                        for (x, morsel)
                        in self.cookies.items()])

    def get(self, url, data=None, headers=None, follow_redirects=False):
        if self.cookies:
            if headers is None:
                headers = dict()
            headers['Cookie'] = self._render_cookie_back()
        response = self.testcase.get(url, data=data, headers=headers,
                                     follow_redirects=follow_redirects)

        self._update_cookies(response.headers)
        return response

    def post(self, url, data, headers=None, follow_redirects=False):
        if self.cookies:
            if headers is None:
                headers = dict()
            headers['Cookie'] = self._render_cookie_back()
        response = self.testcase.post(url, data=data, headers=headers,
                                     follow_redirects=follow_redirects)
        self._update_cookies(response.headers)
        return response

    def _update_cookies(self, headers):
        try:
            sc = headers['Set-Cookie']
            cookies = escape.native_str(sc)
            self.cookies.update(Cookie.SimpleCookie(cookies))
            while True:
                self.cookies.update(Cookie.SimpleCookie(cookies))
                if ',' not in cookies:
                    break
                cookies = cookies[cookies.find(',') + 1:]
        except KeyError:
            return

    def login(self, email, password, url='/auth/login/'):
        data = dict(email=email, password=password)
        response = self.post(url, data, follow_redirects=False)
        if response.code != 302:
            raise LoginError(response.body)
        if 'Error' in response.body:
            raise LoginError(response.body)

########NEW FILE########
__FILENAME__ = routes
## The route helpers were originally written by
## Jeremy Kelley (http://github.com/nod).

import tornado.web
class route(object):
    """
    decorates RequestHandlers and builds up a list of routables handlers

    Tech Notes (or 'What the *@# is really happening here?')
    --------------------------------------------------------

    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.

    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.

    Example
    -------

    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        pass

    @route('/some/path', name='other')
    class SomeOtherRequestHandler(RequestHandler):
        pass

    my_routes = route.get_routes()
    """
    _routes = []

    def __init__(self, uri, name=None):
        self._uri = uri
        self.name = name

    def __call__(self, _handler):
        """gets called when we class decorate"""
        name = self.name and self.name or _handler.__name__
        self._routes.append(tornado.web.url(self._uri, _handler, name=name))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes

def route_redirect(from_, to, name=None):
    route._routes.append(tornado.web.url(from_, tornado.web.RedirectHandler, dict(url=to), name=name))

########NEW FILE########
__FILENAME__ = base
"""Base email backend class."""

class BaseEmailBackend(object):
    """
    Base class for email backend implementations.

    Subclasses must at least overwrite send_messages().
    """
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def open(self):
        """Open a network connection.

        This method can be overwritten by backend implementations to
        open a network connection.

        It's up to the backend implementation to track the status of
        a network connection if it's needed by the backend.

        This method can be called by applications to force a single
        network connection to be used when sending mails. See the
        send_messages() method of the SMTP backend for a reference
        implementation.
                
        The default implementation does nothing.
        """
        pass
                    
    def close(self):
        """Close a network connection."""
        pass
                
    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        raise NotImplementedError

    
########NEW FILE########
__FILENAME__ = console
import sys
import threading

from .base import BaseEmailBackend

class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop('stream', sys.stdout)
        self._lock = threading.RLock()
        super(EmailBackend, self).__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        """Write all messages to the stream in a thread-safe way."""
        if not email_messages:
            return
        self._lock.acquire()
        try:
            # The try-except is nested to allow for
            # Python 2.4 support (Refs #12147)
            try:
                stream_created = self.open()
                for message in email_messages:
                    self.stream.write('%s\n' % message.message().as_string())
                    self.stream.write('-'*79)
                    self.stream.write('\n')
                    self.stream.flush()  # flush after each message
                if stream_created:
                    self.close()
            except:
                if not self.fail_silently:
                    raise
        finally:
            self._lock.release()
        return len(email_messages)

########NEW FILE########
__FILENAME__ = locmem
"""
Backend for test environment.
"""
import sys
from tornado_utils import send_mail as mail  # ugliest hack known to man
from .base import BaseEmailBackend

class EmailBackend(BaseEmailBackend):
    """A email backend for use during test sessions.

    The test connection stores email messages in a dummy outbox,
    rather than sending them out on the wire.

    The dummy outbox is accessible through the outbox instance attribute.
    """
    def __init__(self, *args, **kwargs):
        super(EmailBackend, self).__init__(*args, **kwargs)
        if not hasattr(mail, 'outbox'):
            mail.outbox = []

    def send_messages(self, messages):
        """Redirect messages to the dummy outbox"""
        mail.outbox.extend(messages)
        return len(messages)

########NEW FILE########
__FILENAME__ = pickle
"""Pickling email sender"""

import time
import datetime
import os.path
import cPickle
import logging
from .base import BaseEmailBackend
try:
    import send_mail_config as config
except ImportError:
    try:
        from .. import config
    except ImportError:
        print "Create a file called 'send_mail_config.py' and copy from 'config.py-dist'"
        raise


class EmailBackend(BaseEmailBackend):

    def __init__(self, *args, **kwargs):
        super(EmailBackend, self).__init__(*args, **kwargs)
        self.location = config.PICKLE_LOCATION
        self.protocol = getattr(config, 'PICKLE_PROTOCOL', 0)

        # test that we can write to the location
        open(os.path.join(self.location, 'test.pickle'), 'w').write('test\n')
        os.remove(os.path.join(self.location, 'test.pickle'))

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return

        num_sent = 0
        for message in email_messages:
            if self._pickle(message):
                num_sent += 1
        return num_sent

    def _pickle(self, message):
        t0 = time.time()
        filename = self._pickle_actual(message)
        t1 = time.time()
        logging.debug("Took %s seconds to create %s" % \
                      (t1 - t0, filename))
        return True

    def _pickle_actual(self, message):
        filename_base = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        c = 0
        filename = os.path.join(self.location,
                                filename_base + '_%s.pickle' % c)
        while os.path.isfile(filename):
            c += 1
            filename = os.path.join(self.location,
                                    filename_base + '_%s.pickle' % c)
        cPickle.dump(message, open(filename, 'wb'), self.protocol)
        return filename

########NEW FILE########
__FILENAME__ = smtp
"""SMTP email backend class."""

import smtplib
import socket
import threading

from .base import BaseEmailBackend
try:
    import send_mail_config as config
except ImportError:
    try:
        from .. import config
    except ImportError:
        print "Create a file called 'send_mail_config.py' and copy from 'config.py-dist'"
        raise
from .. import dns_name
DNS_NAME = dns_name.DNS_NAME


class EmailBackend(BaseEmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, **kwargs):
        super(EmailBackend, self).__init__(fail_silently=fail_silently)
        self.host = host or config.EMAIL_HOST
        self.port = port or config.EMAIL_PORT
        self.username = username or config.EMAIL_HOST_USER
        self.password = password or config.EMAIL_HOST_PASSWORD
        if use_tls is None:
            self.use_tls = config.EMAIL_USE_TLS
        else:
            self.use_tls = use_tls
        self.connection = None
        self._lock = threading.RLock()

    def open(self):
        """
        Ensures we have a connection to the email server. Returns whether or
        not a new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False
        try:
            # If local_hostname is not specified, socket.getfqdn() gets used.
            # For performance, we use the cached FQDN for local_hostname.
            self.connection = smtplib.SMTP(self.host, self.port,
                                           local_hostname=DNS_NAME.get_fqdn())
            if self.use_tls:
                self.connection.ehlo()
                self.connection.starttls()
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except:
            if not self.fail_silently:
                raise

    def close(self):
        """Closes the connection to the email server."""
        try:
            try:
                self.connection.quit()
            except socket.sslerror:
                # This happens when calling quit() on a TLS connection
                # sometimes.
                self.connection.close()
            except:
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return
        self._lock.acquire()
        try:
            new_conn_created = self.open()
            if not self.connection:
                # We failed silently on open().
                # Trying to send would be pointless.
                return
            num_sent = 0
            for message in email_messages:
                sent = self._send(message)
                if sent:
                    num_sent += 1
            if new_conn_created:
                self.close()
        finally:
            self._lock.release()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        try:
            self.connection.sendmail(email_message.from_email,
                    email_message.recipients(),
                    email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True

########NEW FILE########
__FILENAME__ = dns_name
"""
Email message and email sending related helper functions.
"""

import socket


# Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
# seconds, which slows down the restart of the server.
class CachedDnsName(object):
    def __str__(self):
        return self.get_fqdn()

    def get_fqdn(self):
        if not hasattr(self, '_fqdn'):
            self._fqdn = socket.getfqdn()
        return self._fqdn

DNS_NAME = CachedDnsName()












########NEW FILE########
__FILENAME__ = importlib
# Taken from Python 2.7 with permission from/by the original author.
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = send_email
import time
import random
import os
from email.generator import Generator
from email.Header import Header
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate
from cStringIO import StringIO

from dns_name import DNS_NAME
from importlib import import_module

class BadHeaderError(ValueError):
    pass

def force_unicode(s, encoding):
    if isinstance(s, unicode):
        return s
    return unicode(s, encoding)

class Promise(object):pass
def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if isinstance(s, Promise):
        return unicode(s).encode(encoding, errors)
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


def make_msgid(idstring=None):
    """Returns a string suitable for RFC 2822 compliant Message-ID, e.g:

    <20020201195627.33539.96671@nightshade.la.mastaler.com>

    Optional idstring if given is a string used to strengthen the
    uniqueness of the message id.
    """
    timeval = time.time()
    utcdate = time.strftime('%Y%m%d%H%M%S', time.gmtime(timeval))
    try:
        pid = os.getpid()
    except AttributeError:
        # No getpid() in Jython, for example.
        pid = 1
    randint = random.randrange(100000)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    idhost = DNS_NAME
    msgid = '<%s.%s.%s%s@%s>' % (utcdate, pid, randint, idstring, idhost)
    return msgid


def forbid_multi_line_headers(name, val, encoding):
    """Forbids multi-line headers, to prevent header injection."""
    encoding = encoding or 'utf-8'
    val = force_unicode(val, encoding)
    if '\n' in val or '\r' in val:
        raise BadHeaderError("Header values can't contain newlines (got %r for header %r)" % (val, name))
    try:
        val = val.encode('ascii')
    except UnicodeEncodeError:
        if name.lower() in ('to', 'from', 'cc'):
            result = []
            for nm, addr in getaddresses((val,)):
                nm = str(Header(nm.encode(encoding), encoding))
                result.append(formataddr((nm, str(addr))))
            val = ', '.join(result)
        else:
            val = Header(val.encode(encoding), encoding)
    else:
        if name.lower() == 'subject':
            val = Header(val)
    return name, val

class SafeMIMEText(MIMEText):

    def __init__(self, text, subtype, charset):
        self.encoding = charset
        MIMEText.__init__(self, text, subtype, charset)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEText.__setitem__(self, name, val)

class EmailMessage(object):
    """
    A container for email information.
    """
    content_subtype = 'plain'
    mixed_subtype = 'mixed'
    encoding = None     # None => use settings default

    def __init__(self, subject, body, from_email, to=None, bcc=None,
                 connection=None, attachments=None, headers=None, cc=None):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).

        All strings used to create the message can be unicode strings
        (or UTF-8 bytestrings). The SafeMIMEText class will handle any
        necessary encoding conversions.
        """
        if to:
            assert not isinstance(to, basestring), '"to" argument must be a list or tuple'
            self.to = list(to)
        else:
            self.to = []
        if cc:
            assert not isinstance(cc, basestring), '"cc" argument must be a list or tuple'
            self.cc = list(cc)
        else:
            self.cc = []
        if bcc:
            assert not isinstance(bcc, basestring), '"bcc" argument must be a list or tuple'
            self.bcc = list(bcc)
        else:
            self.bcc = []
        self.from_email = from_email
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.extra_headers = headers or {}
        self.connection = connection

    def get_connection(self, fail_silently=False):
        #from django.core.mail import get_connection
        if not self.connection:
            raise NotImplementedError
            #self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def message(self):
        encoding = self.encoding or 'utf-8'

        msg = SafeMIMEText(smart_str(self.body, encoding),
                           self.content_subtype, encoding)
        msg = self._create_message(msg)
        msg['Subject'] = self.subject
        msg['From'] = self.extra_headers.get('From', self.from_email)
        msg['To'] = ', '.join(self.to)
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)

        # Email header names are case-insensitive (RFC 2045), so we have to
        # accommodate that when doing comparisons.
        header_names = [key.lower() for key in self.extra_headers]
        if 'date' not in header_names:
            msg['Date'] = formatdate()
        if 'message-id' not in header_names:
            msg['Message-ID'] = make_msgid()
        for name, value in self.extra_headers.items():
            if name.lower() == 'from':  # From is already handled
                continue
            msg[name] = value
        return msg

    def recipients(self):
        """
        Returns a list of all recipients of the email (includes direct
        addressees as well as Bcc entries).
        """
        return self.to + self.cc + self.bcc

    def send(self, fail_silently=False):
        """Sends the email message."""
        if not self.recipients():
            # Don't bother creating the network connection if there's nobody to
            # send to.
            return 0
        return self.get_connection(fail_silently).send_messages([self])

    def attach(self, filename=None, content=None, mimetype=None):
        """
        Attaches a file with the given filename and content. The filename can
        be omitted and the mimetype is guessed, if not provided.

        If the first parameter is a MIMEBase subclass it is inserted directly
        into the resulting message attachments.
        """
        if isinstance(filename, MIMEBase):
            assert content == mimetype == None
            self.attachments.append(filename)
        else:
            assert content is not None
            self.attachments.append((filename, content, mimetype))

    def attach_file(self, path, mimetype=None):
        """Attaches a file from the filesystem."""
        filename = os.path.basename(path)
        content = open(path, 'rb').read()
        self.attach(filename, content, mimetype)

    def _create_message(self, msg):
        return self._create_attachments(msg)

    def _create_attachments(self, msg):
        if self.attachments:
            encoding = self.encoding or settings.DEFAULT_CHARSET
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.mixed_subtype, encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for attachment in self.attachments:
                if isinstance(attachment, MIMEBase):
                    msg.attach(attachment)
                else:
                    msg.attach(self._create_attachment(*attachment))
        return msg

    def _create_mime_attachment(self, content, mimetype):
        """
        Converts the content, mimetype pair into a MIME attachment object.
        """
        basetype, subtype = mimetype.split('/', 1)
        if basetype == 'text':
            encoding = self.encoding or 'utf-8'
            attachment = SafeMIMEText(smart_str(content, encoding), subtype, encoding)
        else:
            # Encode non-text attachments with base64.
            attachment = MIMEBase(basetype, subtype)
            attachment.set_payload(content)
            Encoders.encode_base64(attachment)
        return attachment

    def _create_attachment(self, filename, content, mimetype=None):
        """
        Converts the filename, content, mimetype triple into a MIME attachment
        object.
        """
        if mimetype is None:
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype is None:
                mimetype = DEFAULT_ATTACHMENT_MIME_TYPE
        attachment = self._create_mime_attachment(content, mimetype)
        if filename:
            attachment.add_header('Content-Disposition', 'attachment',
                                  filename=filename)
        return attachment

class EmailMultiAlternatives(EmailMessage):
    """
    A version of EmailMessage that makes it easy to send multipart/alternative
    messages. For example, including text and HTML versions of the text is
    made easier.
    """
    alternative_subtype = 'alternative'

    def __init__(self, subject='', body='', from_email=None, to=None, bcc=None,
            connection=None, attachments=None, headers=None, alternatives=None,
            cc=None):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).

        All strings used to create the message can be unicode strings (or UTF-8
        bytestrings). The SafeMIMEText class will handle any necessary encoding
        conversions.
        """
        if cc:
            raise NotImplementedError
        super(EmailMultiAlternatives, self).__init__(
          subject, body, from_email, to,
          bcc=bcc,
          connection=connection,
          attachments=attachments,
          headers=headers,
        )
        self.alternatives = alternatives or []

    def attach_alternative(self, content, mimetype):
        """Attach an alternative content representation."""
        assert content is not None
        assert mimetype is not None
        self.alternatives.append((content, mimetype))

    def _create_message(self, msg):
        return self._create_attachments(self._create_alternatives(msg))

    def _create_alternatives(self, msg):
        encoding = self.encoding or 'utf-8'
        if self.alternatives:
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.alternative_subtype, encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for alternative in self.alternatives:
                msg.attach(self._create_mime_attachment(*alternative))
        return msg


class SafeMIMEText(MIMEText):

    def __init__(self, text, subtype, charset):
        self.encoding = charset
        MIMEText.__init__(self, text, subtype, charset)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEText.__setitem__(self, name, val)

    def as_string(self, unixfrom=False):
        """Return the entire formatted message as a string.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_string() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = StringIO()
        g = Generator(fp, mangle_from_ = False)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()


class SafeMIMEMultipart(MIMEMultipart):

    def __init__(self, _subtype='mixed', boundary=None, _subparts=None, encoding=None, **_params):
        self.encoding = encoding
        MIMEMultipart.__init__(self, _subtype, boundary, _subparts, **_params)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEMultipart.__setitem__(self, name, val)

    def as_string(self, unixfrom=False):
        """Return the entire formatted message as a string.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_string() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = StringIO()
        g = Generator(fp, mangle_from_ = False)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()


def get_connection(backend, fail_silently=False, **kwds):
    """Load an e-mail backend and return an instance of it.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    path = backend# or settings.EMAIL_BACKEND
    try:
        mod_name, klass_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError, e:
        raise
    klass = getattr(mod, klass_name)
    return klass(fail_silently=fail_silently, **kwds)

def send_email(backend, subject, message, from_email, recipient_list,
               fail_silently=False, bcc=None,
               auth_user=None, auth_password=None,
               connection=None, headers=None,
               cc=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    if not isinstance(recipient_list, (list, tuple)):
        recipient_list = [recipient_list]
    if bcc is not None and not isinstance(bcc, (list, tuple)):
        bcc = [bcc]
    if cc is not None and not isinstance(cc, (list, tuple)):
        cc = [cc]
    connection = connection or get_connection(backend,
                                    username=auth_user,
                                    password=auth_password,
                                    fail_silently=fail_silently)
    return EmailMessage(subject, message, from_email, recipient_list,
                        connection=connection,
                        headers=headers,
                        bcc=bcc,
                        cc=cc).send()

def send_multipart_email(backend,
                         text_part, html_part, subject, recipients,
                         sender, fail_silently=False, bcc=None,
                         auth_user=None, auth_password=None,
                         connection=None):
    """
    This function will send a multi-part e-mail with both HTML and
    Text parts.

    template_name must NOT contain an extension. Both HTML (.html) and TEXT
        (.txt) versions must exist, eg 'emails/public_submit' will use both
        public_submit.html and public_submit.txt.

    email_context should be a plain python dictionary. It is applied against
        both the email messages (templates) & the subject.

    subject can be plain text or a Django template string, eg:
        New Job: {{ job.id }} {{ job.title }}

    recipients can be either a string, eg 'a@b.com' or a list, eg:
        ['a@b.com', 'c@d.com']. Type conversion is done if needed.

    sender can be an e-mail, 'Name <email>' or None. If unspecified, the
        DEFAULT_FROM_EMAIL will be used.

    """

    if not isinstance(recipients, list):
        recipients = [recipients]
    if bcc is not None and not isinstance(bcc, list):
        bcc = [bcc]

    connection = connection or get_connection(backend,
                                    username=auth_user,
                                    password=auth_password,
                                    fail_silently=fail_silently)
    msg = EmailMultiAlternatives(subject, text_part, sender, recipients,
                                 connection=connection,
                                 bcc=bcc)
    msg.attach_alternative(html_part, "text/html")
    return msg.send(fail_silently)

########NEW FILE########
__FILENAME__ = stopwords
# Performance note: I benchmarked this code using a set instead of
# a list for the stopwords and was surprised to find that the list
# performed /better/ than the set - maybe because it's only a small
# list.

stopwords = '''
i
a
an
are
as
at
be
by
for
from
how
in
is
it
of
on
or
that
the
this
to
was
what
when
where
'''.split()

def strip_stopwords(sentence):
    "Removes stopwords - also normalizes whitespace"
    words = sentence.split()
    sentence = []
    for word in words:
        if word.lower() not in stopwords:
            sentence.append(word)
    return u' '.join(sentence)


########NEW FILE########
__FILENAME__ = test_utils
import datetime
import unittest

class UtilsTestCase(unittest.TestCase):

    def test_parse_datetime(self):
        from ..utils import parse_datetime, DatetimeParseError

        r = parse_datetime('1285041600000')
        self.assertEqual(r.year, 2010)

        r = parse_datetime('1283140800')
        self.assertEqual(r.year, 2010)

        r = parse_datetime('1286744467.0')
        self.assertEqual(r.year, 2010)

        self.assertRaises(DatetimeParseError, parse_datetime, 'junk')


    def test_encrypt_password(self):
        from ..utils import encrypt_password

        p = encrypt_password('', log_rounds=1)
        p2 = encrypt_password('', log_rounds=1)
        self.assertNotEqual(p, p2)

        self.assertTrue(isinstance(p, unicode))
        self.assertTrue('$bcrypt$' in p)

        # simulate what the User class's check_password does
        import bcrypt
        p = 'secret'
        r = encrypt_password(p, log_rounds=2)
        hashed = r.split('$bcrypt$')[-1].encode('utf8')
        self.assertEqual(hashed, bcrypt.hashpw(p, hashed))

    def test_valid_email(self):
        from ..utils import valid_email
        self.assertTrue(valid_email('peterbe@gmail.com'))
        self.assertTrue(valid_email("peter'be@gmail.com"))

        self.assertTrue(not valid_email('peterbe @gmail.com'))
        self.assertTrue(not valid_email("peter'be@gmai"))

    def test_random_string(self):
        from ..utils import random_string

        x = random_string(10)
        self.assertEqual(len(x), 10)
        y = random_string(10)
        self.assertEqual(len(y), 10)
        self.assertNotEqual(x, y)

########NEW FILE########
__FILENAME__ = thumbnailer
try:
    from PIL import Image
except ImportError:
    Image = None
import os

from .utils import mkdir

def get_thumbnail(save_path, image_data, (max_width, max_height),
                  quality=85, **kwargs):
    if not Image:
        raise SystemError("PIL.Image was not imported")

    if os.path.isfile(save_path):
        image = Image.open(save_path)
        return image.size
    directory = os.path.dirname(save_path)
    mkdir(directory)
    basename = os.path.basename(save_path)
    original_save_path = os.path.join(directory, 'original.' + basename)
    with open(original_save_path, 'wb') as f:
        f.write(image_data)
    original_image = Image.open(original_save_path)
    image = scale_and_crop(
        original_image,
        (max_width, max_height),
        **kwargs
    )
    format = None
    try:
        image.save(save_path,
                   format=format,
                   quality=quality,
                   optimize=1)
    except IOError:
        # Try again, without optimization (PIL can't optimize an image
        # larger than ImageFile.MAXBLOCK, which is 64k by default)
        image.save(save_path,
                   format=format,
                   quality=quality)

    os.remove(original_save_path)
    return image.size


def scale_and_crop(im, requested_size, **opts):
    x, y = [float(v) for v in im.size]
    xr, yr = [float(v) for v in requested_size]

    if 'crop' in opts or 'max' in opts:
        r = max(xr / x, yr / y)
    else:
        r = min(xr / x, yr / y)

    if r < 1.0 or (r > 1.0 and 'upscale' in opts):
        im = im.resize((int(round(x * r)), int(round(y * r))),
                       resample=Image.ANTIALIAS)

    crop = opts.get('crop') or 'crop' in opts
    if crop:
        # Difference (for x and y) between new image size and requested size.
        x, y = [float(v) for v in im.size]
        dx, dy = (x - min(x, xr)), (y - min(y, yr))
        if dx or dy:
            # Center cropping (default).
            ex, ey = dx / 2, dy / 2
            box = [ex, ey, x - ex, y - ey]
            # See if an edge cropping argument was provided.
            edge_crop = (isinstance(crop, basestring) and
                           re.match(r'(?:(-?)(\d+))?,(?:(-?)(\d+))?$', crop))
            if edge_crop and filter(None, edge_crop.groups()):
                x_right, x_crop, y_bottom, y_crop = edge_crop.groups()
                if x_crop:
                    offset = min(x * int(x_crop) / 100, dx)
                    if x_right:
                        box[0] = dx - offset
                        box[2] = x - offset
                    else:
                        box[0] = offset
                        box[2] = x - (dx - offset)
                if y_crop:
                    offset = min(y * int(y_crop) / 100, dy)
                    if y_bottom:
                        box[1] = dy - offset
                        box[3] = y - offset
                    else:
                        box[1] = offset
                        box[3] = y - (dy - offset)
            # See if the image should be "smart cropped".
            elif crop == 'smart':
                left = top = 0
                right, bottom = x, y
                while dx:
                    slice = min(dx, 10)
                    l_sl = im.crop((0, 0, slice, y))
                    r_sl = im.crop((x - slice, 0, x, y))
                    if utils.image_entropy(l_sl) >= utils.image_entropy(r_sl):
                        right -= slice
                    else:
                        left += slice
                    dx -= slice
                while dy:
                    slice = min(dy, 10)
                    t_sl = im.crop((0, 0, x, slice))
                    b_sl = im.crop((0, y - slice, x, y))
                    if utils.image_entropy(t_sl) >= utils.image_entropy(b_sl):
                        bottom -= slice
                    else:
                        top += slice
                    dy -= slice
                box = (left, top, right, bottom)
            # Finally, crop the image!
            im = im.crop([int(round(v)) for v in box])
    return im

########NEW FILE########
__FILENAME__ = timesince
import datetime

# Language constants
MINUTE = 'minute'
MINUTES = 'minutes'
HOUR = 'hour'
HOURS = 'hours'
YEAR = 'year'
YEARS = 'years'
MONTH = 'month'
MONTHS = 'months'
WEEK = 'week'
WEEKS = 'weeks'
DAY = 'day'
DAYS = 'days'
AND = 'and'


#@register.filter
def smartertimesince(d, now=None):
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        if d.tzinfo:
            raise NotImplementedError
            from django.utils.tzinfo import LocalTimezone
            now = datetime.datetime.now(LocalTimezone(d))
        else:
            now = datetime.datetime.now()

    r = timeSince(d, now, max_no_sections=1, minute_granularity=True)
    if not r:
        return "seconds"
    return r

# Copied and adopted from FriedZopeBase
def timeSince(firstdate, seconddate, afterword=None,
              minute_granularity=False,
              max_no_sections=3):
    """
    Use two date objects to return in plain english the difference between them.
    E.g. "3 years and 2 days"
     or  "1 year and 3 months and 1 day"

    Try to use weeks when the no. of days > 7

    If less than 1 day, return number of hours.

    If there is "no difference" between them, return false.
    """

    def wrap_afterword(result, afterword=afterword):
        if afterword is not None:
            return "%s %s" % (result, afterword)
        else:
            return result

    fdo = firstdate
    sdo = seconddate

    day_difference = abs(sdo-fdo).days

    years = day_difference/365
    months = (day_difference % 365)/30
    days = (day_difference % 365) % 30
    minutes = ((day_difference % 365) % 30) % 24


    if days == 0 and months == 0 and years == 0:
        # use hours
        hours = abs(sdo-fdo).seconds/3600
        if hours == 1:
            return wrap_afterword("1 %s" % (HOUR))
        elif hours > 0:
            return wrap_afterword("%s %s" % (hours, HOURS))
        elif minute_granularity:

            minutes = abs(sdo-fdo).seconds / 60
            if minutes == 1:
                return wrap_afterword("1 %s" % MINUTE)
            elif minutes > 0:
                return wrap_afterword("%s %s" % (minutes, MINUTES))
            else:
                # if the differnce is smaller than 1 minute,
                # return 0.
                return 0
        else:
            # if the difference is smaller than 1 hour,
            # return it false
            return 0
    else:
        s = []
        if years == 1:
            s.append('1 %s'%(YEAR))
        elif years > 1:
            s.append('%s %s'%(years,YEARS))

        if months == 1:
            s.append('1 %s'%MONTH)
        elif months > 1:
            s.append('%s %s'%(months,MONTHS))

        if days == 1:
            s.append('1 %s'%DAY)
        elif days == 7:
            s.append('1 %s'%WEEK)
        elif days == 14:
            s.append('2 %s'%WEEKS)
        elif days == 21:
            s.append('3 %s'%WEEKS)
        elif days > 14:
            weeks = days / 7
            days = days % 7
            if weeks == 1:
                s.append('1 %s'%WEEK)
            else:
                s.append('%s %s'%(weeks, WEEKS))
            if days % 7 == 1:
                s.append('1 %s'%DAY)
            elif days > 0:

                s.append('%s %s'%(days % 7,DAYS))
        elif days > 1:
            s.append('%s %s'%(days,DAYS))

        s = s[:max_no_sections]

        if len(s)>1:
            return wrap_afterword("%s" % (string.join(s,' %s '%AND)))
        else:
            return wrap_afterword("%s" % s[0])

########NEW FILE########
__FILENAME__ = tornado_static
"""
tornado_static is a module for displaying static resources in a Tornado web
application.

It can take care of merging, compressing and giving URLs ideal renamings
suitable for aggressive HTTP caching.

(c) mail@peterbe.com
"""

__version__ = '1.9'

import os
import cPickle
import re
import stat
import marshal
import warnings
from cStringIO import StringIO
from time import time
from tempfile import gettempdir
from base64 import encodestring
from subprocess import Popen, PIPE
import tornado.web

try:
    import cssmin
except ImportError:
    cssmin = None

from .utils import mkdir

################################################################################
# Global variable where we store the conversions so we don't have to do them
# again every time the UI module is rendered with the same input

out_file = os.path.join(os.path.abspath(os.curdir), '.static_name_conversion')
def _delete_old_static_name_conversion():
    """In this app we marshal all static file conversion into a file called
    '.static_name_conversion' located here in the working directory.
    The reason we're doing this is so that when you start multiple Python
    interpreters of the app (e.g. production environment) you only need to
    work out which name conversions have been done once.

    When you do a new deployment it's perfectly natural that this name
    conversion should be invalidated since there are now potentially new static
    resources so it needs to have different static names.

    So delete the file if it's older than a small amount of time in a human
    sense.
    """
    if os.path.isfile(out_file):
        mtime = os.stat(out_file)[stat.ST_MTIME]
        age = time() - mtime
        if age >= 60:
            os.remove(out_file)

def load_name_conversion():
    try:
        return marshal.load(open(out_file))
    except IOError:
        return dict()

_delete_old_static_name_conversion()
_name_conversion = load_name_conversion()

def save_name_conversion():
    marshal.dump(_name_conversion, open(out_file, 'w'))

class StaticURL(tornado.web.UIModule):

    def render(self, *static_urls, **options):
        return_inline = options.get('return_inline', False)
        # the following 4 lines will have to be run for every request. Since
        # it's just a basic lookup on a dict it's going to be uber fast.
        basic_name = ''.join(static_urls)
        already = _name_conversion.get(basic_name)
        if already and not return_inline:
            cdn_prefix = self.handler.get_cdn_prefix()
            if cdn_prefix:
                already = cdn_prefix + already
            return already

        new_name = self._combine_filename(static_urls)

        # If you run multiple tornados (on different ports) it's possible
        # that another process has already dealt with this static URL.
        # Therefore we now first of all need to figure out what the final name
        # is going to be
        youngest = 0
        full_paths = []
        old_paths = {}  # maintain a map of what the filenames where before
        for path in static_urls:
            full_path = os.path.join(
              self.handler.settings['static_path'], path)
            #f = open(full_path)
            mtime = os.stat(full_path)[stat.ST_MTIME]
            if mtime > youngest:
                youngest = mtime
            full_paths.append(full_path)
            old_paths[full_path] = path

        n, ext = os.path.splitext(new_name)
        new_name = "%s.%s%s" % (n, youngest, ext)

        optimization_done = False
        if os.path.isfile(new_name):
            # conversion and preparation has already been done!
            # No point doing it again, so just exit here
            pass

        else:
            destination = file(new_name, 'w')

            if options.get('dont_optimize'):
                do_optimize_static_content = False
            else:
                do_optimize_static_content = self.handler.settings\
                  .get('optimize_static_content', True)

            if do_optimize_static_content:
                uglifyjs_location = self.handler\
                  .settings.get('UGLIFYJS_LOCATION')
                closure_location = self.handler\
                  .settings.get('CLOSURE_LOCATION')
                yui_location = self.handler\
                  .settings.get('YUI_LOCATION')

            for full_path in full_paths:
                code = open(full_path).read()
                if full_path.endswith('.js'):
                    if len(full_paths) > 1:
                        destination.write('/* %s */\n' % os.path.basename(full_path))
                    if (do_optimize_static_content and
                        not self._already_optimized_filename(full_path)):
                        optimization_done = True
                        if uglifyjs_location:
                            code = run_uglify_js_compiler(code, uglifyjs_location,
                              verbose=self.handler.settings.get('debug', False))
                        elif closure_location:
                            orig_code = code
                            code = run_closure_compiler(code, closure_location,
                              verbose=self.handler.settings.get('debug', False))
                        elif yui_location:
                            code = run_yui_compressor(code, 'js', yui_location,
                              verbose=self.handler.settings.get('debug', False))
                        else:
                            optimization_done = False
                            warnings.warn('No external program configured '
                                          'for optimizing .js')

                elif full_path.endswith('.css'):
                    if len(full_paths) > 1:
                        (destination.write('/* %s */\n' %
                          os.path.basename(full_path)))
                    if (do_optimize_static_content and
                        not self._already_optimized_filename(full_path)):
                        optimization_done = True
                        if cssmin is not None:
                            code = cssmin.cssmin(code)
                        elif yui_location:
                            code = run_yui_compressor(code, 'css', yui_location,
                             verbose=self.handler.settings.get('debug', False))
                        else:
                            optimization_done = False
                            warnings.warn('No external program configured for '
                                          'optimizing .css')
                    # do run this after the run_yui_compressor() has been used so that
                    # code that is commented out doesn't affect
                    code = self._replace_css_images_with_static_urls(
                        code,
                        os.path.dirname(old_paths[full_path])
                    )
                else:
                    # this just copies the file
                    pass

                destination.write(code)
                destination.write("\n")
            destination.close()

        if return_inline:
            return open(new_name).read()

        prefix = self.handler.settings.get('combined_static_url_prefix', '/combined/')
        new_name = os.path.join(prefix, os.path.basename(new_name))
        _name_conversion[basic_name] = new_name
        save_name_conversion()

        ## Commented out, because I don't want to use CDN when it might take 5 seconds
        # to generate the new file.
        # only bother with the cdn_prefix addition if the file wasn't optimized
        if not optimization_done:
            cdn_prefix = self.handler.get_cdn_prefix()
            if cdn_prefix:
                new_name = cdn_prefix + new_name
        return new_name

    def _combine_filename(self, names, max_length=60):
        # expect the parameter 'names' be something like this:
        # ['css/foo.css', 'css/jquery/datepicker.css']
        # The combined filename is then going to be
        # "/tmp/foo.datepicker.css"
        first_ext = os.path.splitext(names[0])[-1]
        save_dir = self.handler.application.settings.get('combined_static_dir')
        if save_dir is None:
            save_dir = os.environ.get('TMP_DIR')
            if not save_dir:
                save_dir = gettempdir()
        save_dir = os.path.join(save_dir, 'combined')
        mkdir(save_dir)
        combined_name = []
        _previous_parent_name = None
        for name in names:
            parent_name = os.path.split(os.path.dirname(name))[-1]
            name, ext = os.path.splitext(os.path.basename(name))
            if parent_name and parent_name != _previous_parent_name:
                name = '%s.%s' % (parent_name, name)
            if ext != first_ext:
                raise ValueError("Mixed file extensions (%s, %s)" %\
                 (first_ext, ext))
            combined_name.append(name)
            _previous_parent_name = parent_name
        if sum(len(x) for x in combined_name) > max_length:
            combined_name = [x.replace('.min','.m').replace('.pack','.p')
                             for x in combined_name]
            combined_name = [re.sub(r'-[\d\.]+', '', x) for x in combined_name]
            while sum(len(x) for x in combined_name) > max_length:
                try:
                    combined_name = [x[-2] == '.' and x[:-2] or x[:-1]
                                 for x in combined_name]
                except IndexError:
                    break

        combined_name.append(first_ext[1:])
        return os.path.join(save_dir, '.'.join(combined_name))

    def _replace_css_images_with_static_urls(self, css_code, rel_dir):
        def replacer(match):
            filename = match.groups()[0]
            if (filename.startswith('"') and filename.endswith('"')) or \
              (filename.startswith("'") and filename.endswith("'")):
                filename = filename[1:-1]
            if 'data:image' in filename or filename.startswith('http://'):
                return 'url("%s")' % filename
            if filename == '.':
                # this is a known IE hack in CSS
                return 'url(".")'
            # It's really quite common that the CSS file refers to the file
            # that doesn't exist because if you refer to an image in CSS for
            # a selector you never use you simply don't suffer.
            # That's why we say not to warn on nonexisting files
            new_filename = self.handler.static_url(os.path.join(rel_dir, filename))
            return match.group().replace(filename, new_filename)
        _regex = re.compile('url\(([^\)]+)\)')
        css_code = _regex.sub(replacer, css_code)

        return css_code

    def _already_optimized_filename(self, file_path):
        file_name = os.path.basename(file_path)
        for part in ('-min-', '-min.', '.min.', '.minified.', '.pack.', '-jsmin.'):
            if part in file_name:
                return True
        return False


class Static(StaticURL):
    """given a list of static resources, return the whole HTML tag"""
    def render(self, *static_urls, **options):
        extension = static_urls[0].split('.')[-1]
        if extension == 'css':
            template = '<link rel="stylesheet" type="text/css" href="%(url)s">'
        elif extension == 'js':
            template = '<script type="text/javascript" '
            if options.get('defer'):
                template += 'defer '
            elif options.get('async'):
                template += 'async '
            template += 'src="%(url)s"></script>'
        else:
            raise NotImplementedError
        url = super(Static, self).render(*static_urls)
        return template % dict(url=url)


class StaticInline(StaticURL):
    """given a list of static resources, return the whole HTML tag"""
    def render(self, *static_urls, **options):
        extension = static_urls[0].split('.')[-1]
        if extension == 'css':
            template = '<style type="text/css">%s</style>'
        elif extension == 'js':
            template = '<script type="text/javascript" '
            if options.get('defer'):
                template += 'defer '
            elif options.get('async'):
                template += 'async '
            template += '>%s</script>'
        else:
            raise NotImplementedError
        code = super(StaticInline, self).render(*static_urls, return_inline=True)
        return template % code


def run_closure_compiler(code, jar_location, verbose=False): # pragma: no cover
    if verbose:
        t0 = time()
    r = _run_closure_compiler(code, jar_location)
    if verbose:
        t1 = time()
        a, b = len(code), len(r)
        c = round(100 * float(b) / a, 1)
        print "Closure took", round(t1 - t0, 4),
        print "seconds to compress %d bytes into %d (%s%%)" % (a, b, c)
    return r

def _run_closure_compiler(jscode, jar_location, advanced_optmization=False): # pragma: no cover
    cmd = "java -jar %s " % jar_location
    if advanced_optmization:
        cmd += " --compilation_level ADVANCED_OPTIMIZATIONS "
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(jscode)
    except OSError, msg:
        # see comment on OSErrors inside _run_yui_compressor()
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg
    if stderrdata:
        return "/* ERRORS WHEN RUNNING CLOSURE COMPILER\n" + stderrdata + '\n*/\n' + jscode
    return stdoutdata

def run_uglify_js_compiler(code, location, verbose=False): # pragma: no cover
    if verbose:
        t0 = time()
    r = _run_uglify_js_compiler(code, location)
    if verbose:
        t1 = time()
        a, b = len(code), len(r)
        c = round(100 * float(b) / a, 1)
        print "UglifyJS took", round(t1 - t0, 4),
        print "seconds to compress %d bytes into %d (%s%%)" % (a, b, c)
    return r

def _run_uglify_js_compiler(jscode, location, options=''): # pragma: no cover
    cmd = "%s %s" % (location, options)
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(jscode)
    except OSError, msg:
        # see comment on OSErrors inside _run_yui_compressor()
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg
    if stderrdata:
        return "/* ERRORS WHEN RUNNING UGLIFYJS COMPILER\n" + stderrdata + '\n*/\n' + jscode
    return stdoutdata

def run_yui_compressor(code, type_, jar_location, verbose=False): # pragma: no cover
    if verbose:
        t0 = time()
    r = _run_yui_compressor(code, type_, jar_location)
    if verbose:
        t1 = time()
        a, b = len(code), len(r)
        c = round(100 * float(b) / a, 1)
        print "YUI took", round(t1 - t0, 4),
        print "seconds to compress %d bytes into %d (%s%%)" % (a, b, c)
    return r

def _run_yui_compressor(code, type_, jar_location):
    cmd = "java -jar %s --type=%s" % (jar_location, type_)
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(code)
    except OSError, msg:
        # Sometimes, for unexplicable reasons, you get a Broken pipe when
        # running the popen instance. It's always non-deterministic problem
        # so it probably has something to do with concurrency or something
        # really low level.
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg

    if stderrdata:
        return "/* ERRORS WHEN RUNNING YUI COMPRESSOR\n" + stderrdata + '\n*/\n' + code

    return stdoutdata


class PlainStaticURL(tornado.web.UIModule):
    def render(self, url):
        return self.handler.static_url(url)

class PlainStatic(tornado.web.UIModule):
    """Render the HTML that displays a static resource without any optimization
    or combing.
    """

    def render(self, *static_urls, **options):
        extension = static_urls[0].split('.')[-1]
        if extension == 'css':
            template = '<link rel="stylesheet" type="text/css" href="%(url)s">'
        elif extension == 'js':
            template = '<script type="text/javascript" '
            if options.get('defer'):
                template += 'defer '
            elif options.get('async'):
                template += 'async '
            template += 'src="%(url)s"></script>'
        else:
            raise NotImplementedError

        html = []
        for each in static_urls:
            url = self.handler.static_url(each)
            html.append(template % dict(url=url))
        return "\n".join(html)


_base64_conversion_file = '.base64-image-conversions.pickle'
try:
    _base64_conversions = cPickle.load(file(_base64_conversion_file))
    #raise IOError
except IOError:
    _base64_conversions = {}

class Static64(tornado.web.UIModule):
    def render(self, image_path):
        already = _base64_conversions.get(image_path)
        if already:
            return already

        template = 'data:image/%s;base64,%s'
        extension = os.path.splitext(os.path.basename(image_path))
        extension = extension[-1][1:]
        assert extension in ('gif','png'), extension
        full_path = os.path.join(
              self.handler.settings['static_path'], image_path)
        data = encodestring(file(full_path,'rb').read()).replace('\n','')#.replace('\n','\\n')
        result = template % (extension, data)

        _base64_conversions[image_path] = result
        cPickle.dump(_base64_conversions, file(_base64_conversion_file, 'wb'))
        return result

########NEW FILE########
__FILENAME__ = truncate
def truncate_words(s, num, end_text='...'):
    """Truncates a string after a certain number of words. Takes an optional
    argument of what should be used to notify that the string has been
    truncated, defaults to ellipsis (...)"""
    length = int(num)
    words = s.split()
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith(end_text):
            words.append(end_text)
    return u' '.join(words)
########NEW FILE########
__FILENAME__ = utils
import os
import re
import datetime
import random
try:
    import bcrypt
except ImportError:
    # it'd be a shame to rely on this existing
    bcrypt = None


class djangolike_request_dict(dict):
    def getlist(self, key):
        value = self.get(key)
        return self.get(key)

class DatetimeParseError(Exception):
    pass

_timestamp_regex = re.compile('\d{13}|\d{10}\.\d{0,4}|\d{10}')
def parse_datetime(datestr):
    _parsed = _timestamp_regex.findall(datestr)
    if _parsed:
        datestr = _parsed[0]
        if len(datestr) >= len('1285041600000'):
            try:
                return datetime.datetime.fromtimestamp(float(datestr)/1000)
            except ValueError:
                pass
        if len(datestr) >= len('1283140800'):
            try:
                return datetime.datetime.fromtimestamp(float(datestr))
            except ValueError:
                pass # will raise
    raise DatetimeParseError(datestr)

def datetime_to_date(dt):
    return datetime.date(dt.year, dt.month, dt.day)

def encrypt_password(raw_password, log_rounds=10):
    if not bcrypt:
        raise SystemError("bcrypt could no be imported")
    salt = bcrypt.gensalt(log_rounds=log_rounds)
    hsh = bcrypt.hashpw(raw_password, salt)
    algo = 'bcrypt'
    return u'%s$%s$%s' % (salt, algo, hsh)


def niceboolean(value):
    if type(value) is bool:
        return value
    falseness = ('','no','off','false','none','0', 'f')
    return str(value).lower().strip() not in falseness



email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain
def valid_email(email):
    return bool(email_re.search(email))


def mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                    "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            mkdir(head)
        if tail:
            os.mkdir(newdir)

from random import choice
from string import letters
def random_string(length):
    return ''.join(choice(letters) for i in xrange(length))


def all_hash_tags(tags, title):
    """return true if all tags in the title were constructed with a '#' instead
    of a '@' sign"""
    for tag in tags:
        if re.findall(r'(^|\s)@%s\b' % re.escape(tag), title):
            return False
    return True

def all_atsign_tags(tags, title):
    """return true if all tags in the title were constructed with a '@' instead
    of a '#' sign"""
    for tag in tags:
        if re.findall(r'(^|\s)#%s\b' % re.escape(tag), title):
            return False
    return True

def format_time_ampm(time_or_datetime):
    if isinstance(time_or_datetime, datetime.datetime):
        h = int(time_or_datetime.strftime('%I'))
        ampm = time_or_datetime.strftime('%p').lower()
        if time_or_datetime.minute:
            m = time_or_datetime.strftime('%M')
            return "%s:%s%s" % (h, m, ampm)
        else:
            return "%s%s" % (h, ampm)
    elif isinstance(time_or_datetime, (tuple, list)) and len(time_or_datetime) >= 2:
        h = time_or_datetime[0]
        m = time_or_datetime[1]
        assert isinstance(h, int), type(h)
        assert isinstance(m, int), type(m)
        ampm = 'am'
        if h > 12:
            ampm = 'pm'
            h -= 12
        if m:
            return "%s:%s%s" % (h, m, ampm)
        else:
            return "%s%s" % (h, ampm)
    else:
        raise ValueError("Wrong parameter to this function")


def generate_random_color():
    def dec2hex(d):
        return "%02X" % d
    return '#%s%s%s' % (
      dec2hex(random.randint(0, 255)),
      dec2hex(random.randint(0, 255)),
      dec2hex(random.randint(0, 255)),
    )

########NEW FILE########
