__FILENAME__ = application
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright @year@ @author@
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
#

project="@project@"
version="1.0"
author="@author@"
copyright="Copyright @year@ @author@"
application="@application@"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class @mainhandler@(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', @mainhandler@)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = distributed-social-media
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2010 Juha Autero <jautero@iki.fi>
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
#

project="Distributed Social Media"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2010 Juha Autero <jautero@iki.fi>"
application="distributed-social-media"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class DistributedSocialMedia(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', DistributedSocialMedia)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = friendmodel
#!/usr/bin/env python
# encoding: utf-8
"""
friendmodel.py

Created by Juha Autero on 2010-05-15.
Copyright (c) 2010 Juha Autero. All rights reserved.
"""

from google.appengine.ext import db
class Friend(db.Model):
	idurl=db.StringProperty()
	name=db.StringProperty()
	#cert=db.StringProprty()

########NEW FILE########
__FILENAME__ = itemmodel
#!/usr/bin/env python
# encoding: utf-8
"""
itemmodel.py

Created by Juha Autero on 2010-05-15.
Copyright (c) 2010 Juha Autero. All rights reserved.
"""

from google.appengine.ext import db
from friendmodel import Friend
class Item(db.Expando):
	sender=db.ReferenceProprety(Friend)
	date=db.DateProperty()
      	title=db.StringProperty()
	content=db.StringProperty(multiline=True)

########NEW FILE########
__FILENAME__ = drinkcounter
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2008 Juha Autero <Juha.Autero@iki.fi>
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
#

project="drinkcounter"
version="1.0"
author="Juha Autero <Juha.Autero@iki.fi>"
copyright="Copyright 2008 Juha Autero <Juha.Autero@iki.fi>"
application="drinkcounter"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class Drinkcounter(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', Drinkcounter)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = film-festival
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2011 Juha Autero <jautero@iki.fi>
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
#

project="Film Festival"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2011 Juha Autero <jautero@iki.fi>"
application="film-festival"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class FilmFestival(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', FilmFestival)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = make-schedule
#!/usr/bin/python
import festival,os,time

festivalfile=os.environ['HOME']+"/RA2003.xml"

def movie_cmp(self,other):
    return cmp(self.free_screenings,other.free_screenings)

def sort_by_date(scra,scrb):
    return cmp(scra.convert_time(),scrb.convert_time())

def sort_by_theatre(scra,scrb):
    return cmp(scra.theatre,scrb.theatre)

def create_candidates(festari):
    candidates=[]
    for movie in festari.movies:
        if movie.selected:
            candidates.append(movie)
        movie.free_screenings=0
        for screening in movie.screenings:
            if screening.soldout:
                screening.free=0
            else:
                movie.free_screenings+=1
                screening.free=1
    return candidates

festari=festival.read_festival(open(festivalfile,"r"))
aikataulu=festival.Timetable()
aikataulu.addFestival(festari)
aikataulu.calculate_overlaps()
candidates=create_candidates(festari)
selected_screenings=[]
best_candidate=[]

def find_candidates():
    global best_candidate
    candidates.sort(movie_cmp)
    if len(candidates)==0:
        return 1
    for index in range(0,len(candidates)):
        candidate=candidates.pop(index)
        if candidate.free_screenings==0:
            # Backtrack
            candidates.insert(index,candidate) 
            return 0
        for screening in candidate.screenings:
            if screening.free:
                updated=[]
                for scr in screening.overlaping:
                    if scr.free:
                        scr.free=0
                        scr.movie.free_screenings-=1
                        updated.append(scr)
                selected_screenings.append(screening)
                if len(selected_screenings)>len(best_candidate):
                    best_candidate=selected_screenings[:]
                if find_candidates():
                    return 1
                else:
                    selected_screenings.remove(screening)
                    for src in updated:
                        scr.free=1
                        scr.movie.free_screenings+=1
        candidates.insert(index,candidate)
    return 0

def printscreening(screening):
    print "\t%s: %s %s" % (screening.movie.name.encode("ISO-8859-1"),
                         time.strftime("%a %d.%m. %H:%M",
                                       time.localtime(screening.convert_time())),
                         screening.theatre.encode("ISO-8859-1"))

if find_candidates():
    print "Movie list:"
    selected_screenings.sort(sort_by_date)
    print "    by date:"
    map(printscreening,selected_screenings)
    print "    by theatre"
    selected_screenings.sort(sort_by_theatre)
    old_theatre=selected_screenings[0].theatre
    for screening in selected_screenings:
        if (screening.theatre!=old_theatre):
            print
            old_theatre=screening.theatre
        printscreening(screening)

else:
    print "Matching list couldn't be found."
    print "Best match:"
    for screening in selected_screenings:
        print "%s: %s %s" % (screening.movie.name.encode("ISO-8859-1"),
                             time.strftime("%a %d.%m. %H:%M",time.localtime(screening.convert_time())),
                             screening.theatre.encode("ISO-8859-1"))
    

########NEW FILE########
__FILENAME__ = model
from google.appengine.ext import db

class Festival(db.Model):
    name=db.StringProperty()
    month=db.IntegerProperty()
    year=db.IntegerProperty()
    switchbuffer=db.TimeProperty()
class Movie(db.Model):
    festival=db.ReferenceProperty(Festival)
    name=db.StringProperty()
    length=db.TimeProperty()
    Director=db.StringProperty()
class Screening(db.Model):
    movie=db.ReferenceProperty(Festival)
    theatre=db.StringProperty()
    starttime=db.DateTimeProperty()
    soldout=db.BooleanProperty()

########NEW FILE########
__FILENAME__ = feedparser
#!/usr/bin/env python
"""Universal feed parser

Handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom 0.3, and Atom 1.0 feeds

Visit http://feedparser.org/ for the latest version
Visit http://feedparser.org/docs/ for the latest documentation

Required: Python 2.1 or later
Recommended: Python 2.3 or later
Recommended: CJKCodecs and iconv_codec <http://cjkpython.i18n.org/>
"""

__version__ = "4.1"# + "$Revision: 1.92 $"[11:15] + "-cvs"
__license__ = """Copyright (c) 2002-2006, Mark Pilgrim, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""
__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__contributors__ = ["Jason Diamond <http://injektilo.org/>",
                    "John Beimler <http://john.beimler.org/>",
                    "Fazal Majid <http://www.majid.info/mylos/weblog/>",
                    "Aaron Swartz <http://aaronsw.com/>",
                    "Kevin Marks <http://epeus.blogspot.com/>"]
_debug = 0

# HTTP "User-Agent" header to send to servers when downloading feeds.
# If you are embedding feedparser in a larger application, you should
# change this to your application name and URL.
USER_AGENT = "UniversalFeedParser/%s +http://feedparser.org/" % __version__

# HTTP "Accept" header to send to servers when downloading feeds.  If you don't
# want to send an Accept header, set this to None.
ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

# List of preferred XML parsers, by SAX driver name.  These will be tried first,
# but if they're not installed, Python will keep searching through its own list
# of pre-installed parsers until it finds one that supports everything we need.
PREFERRED_XML_PARSERS = ["drv_libxml2"]

# If you want feedparser to automatically run HTML markup through HTML Tidy, set
# this to 1.  Requires mxTidy <http://www.egenix.com/files/python/mxTidy.html>
# or utidylib <http://utidylib.berlios.de/>.
TIDY_MARKUP = 0

# List of Python interfaces for HTML Tidy, in order of preference.  Only useful
# if TIDY_MARKUP = 1
PREFERRED_TIDY_INTERFACES = ["uTidy", "mxTidy"]

# ---------- required modules (should come with any Python distribution) ----------
import sgmllib, re, sys, copy, urlparse, time, rfc822, types, cgi, urllib, urllib2
try:
    from cStringIO import StringIO as _StringIO
except:
    from StringIO import StringIO as _StringIO

# ---------- optional modules (feedparser will work without these, but with reduced functionality) ----------

# gzip is included with most Python distributions, but may not be available if you compiled your own
try:
    import gzip
except:
    gzip = None
try:
    import zlib
except:
    zlib = None

# If a real XML parser is available, feedparser will attempt to use it.  feedparser has
# been tested with the built-in SAX parser, PyXML, and libxml2.  On platforms where the
# Python distribution does not come with an XML parser (such as Mac OS X 10.2 and some
# versions of FreeBSD), feedparser will quietly fall back on regex-based parsing.
try:
    import xml.sax
    xml.sax.make_parser(PREFERRED_XML_PARSERS) # test for valid parsers
    from xml.sax.saxutils import escape as _xmlescape
    _XML_AVAILABLE = 1
except:
    _XML_AVAILABLE = 0
    def _xmlescape(data):
        data = data.replace('&', '&amp;')
        data = data.replace('>', '&gt;')
        data = data.replace('<', '&lt;')
        return data

# base64 support for Atom feeds that contain embedded binary data
try:
    import base64, binascii
except:
    base64 = binascii = None

# cjkcodecs and iconv_codec provide support for more character encodings.
# Both are available from http://cjkpython.i18n.org/
try:
    import cjkcodecs.aliases
except:
    pass
try:
    import iconv_codec
except:
    pass

# chardet library auto-detects character encodings
# Download from http://chardet.feedparser.org/
try:
    import chardet
    if _debug:
        import chardet.constants
        chardet.constants._debug = 1
except:
    chardet = None

# ---------- don't touch these ----------
class ThingsNobodyCaresAboutButMe(Exception): pass
class CharacterEncodingOverride(ThingsNobodyCaresAboutButMe): pass
class CharacterEncodingUnknown(ThingsNobodyCaresAboutButMe): pass
class NonXMLContentType(ThingsNobodyCaresAboutButMe): pass
class UndeclaredNamespace(Exception): pass

sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
sgmllib.special = re.compile('<!')
sgmllib.charref = re.compile('&#(x?[0-9A-Fa-f]+)[^0-9A-Fa-f]')

SUPPORTED_VERSIONS = {'': 'unknown',
                      'rss090': 'RSS 0.90',
                      'rss091n': 'RSS 0.91 (Netscape)',
                      'rss091u': 'RSS 0.91 (Userland)',
                      'rss092': 'RSS 0.92',
                      'rss093': 'RSS 0.93',
                      'rss094': 'RSS 0.94',
                      'rss20': 'RSS 2.0',
                      'rss10': 'RSS 1.0',
                      'rss': 'RSS (unknown version)',
                      'atom01': 'Atom 0.1',
                      'atom02': 'Atom 0.2',
                      'atom03': 'Atom 0.3',
                      'atom10': 'Atom 1.0',
                      'atom': 'Atom (unknown version)',
                      'cdf': 'CDF',
                      'hotrss': 'Hot RSS'
                      }

try:
    UserDict = dict
except NameError:
    # Python 2.1 does not have dict
    from UserDict import UserDict
    def dict(aList):
        rc = {}
        for k, v in aList:
            rc[k] = v
        return rc

class FeedParserDict(UserDict):
    keymap = {'channel': 'feed',
              'items': 'entries',
              'guid': 'id',
              'date': 'updated',
              'date_parsed': 'updated_parsed',
              'description': ['subtitle', 'summary'],
              'url': ['href'],
              'modified': 'updated',
              'modified_parsed': 'updated_parsed',
              'issued': 'published',
              'issued_parsed': 'published_parsed',
              'copyright': 'rights',
              'copyright_detail': 'rights_detail',
              'tagline': 'subtitle',
              'tagline_detail': 'subtitle_detail'}
    def __getitem__(self, key):
        if key == 'category':
            return UserDict.__getitem__(self, 'tags')[0]['term']
        if key == 'categories':
            return [(tag['scheme'], tag['term']) for tag in UserDict.__getitem__(self, 'tags')]
        realkey = self.keymap.get(key, key)
        if type(realkey) == types.ListType:
            for k in realkey:
                if UserDict.has_key(self, k):
                    return UserDict.__getitem__(self, k)
        if UserDict.has_key(self, key):
            return UserDict.__getitem__(self, key)
        return UserDict.__getitem__(self, realkey)

    def __setitem__(self, key, value):
        for k in self.keymap.keys():
            if key == k:
                key = self.keymap[k]
                if type(key) == types.ListType:
                    key = key[0]
        return UserDict.__setitem__(self, key, value)

    def get(self, key, default=None):
        if self.has_key(key):
            return self[key]
        else:
            return default

    def setdefault(self, key, value):
        if not self.has_key(key):
            self[key] = value
        return self[key]
        
    def has_key(self, key):
        try:
            return hasattr(self, key) or UserDict.has_key(self, key)
        except AttributeError:
            return False
        
    def __getattr__(self, key):
        try:
            return self.__dict__[key]
        except KeyError:
            pass
        try:
            assert not key.startswith('_')
            return self.__getitem__(key)
        except:
            raise AttributeError, "object has no attribute '%s'" % key

    def __setattr__(self, key, value):
        if key.startswith('_') or key == 'data':
            self.__dict__[key] = value
        else:
            return self.__setitem__(key, value)

    def __contains__(self, key):
        return self.has_key(key)

def zopeCompatibilityHack():
    global FeedParserDict
    del FeedParserDict
    def FeedParserDict(aDict=None):
        rc = {}
        if aDict:
            rc.update(aDict)
        return rc

_ebcdic_to_ascii_map = None
def _ebcdic_to_ascii(s):
    global _ebcdic_to_ascii_map
    if not _ebcdic_to_ascii_map:
        emap = (
            0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
            16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
            128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
            144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
            32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
            38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
            45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
            186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
            195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,201,
            202,106,107,108,109,110,111,112,113,114,203,204,205,206,207,208,
            209,126,115,116,117,118,119,120,121,122,210,211,212,213,214,215,
            216,217,218,219,220,221,222,223,224,225,226,227,228,229,230,231,
            123,65,66,67,68,69,70,71,72,73,232,233,234,235,236,237,
            125,74,75,76,77,78,79,80,81,82,238,239,240,241,242,243,
            92,159,83,84,85,86,87,88,89,90,244,245,246,247,248,249,
            48,49,50,51,52,53,54,55,56,57,250,251,252,253,254,255
            )
        import string
        _ebcdic_to_ascii_map = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
    return s.translate(_ebcdic_to_ascii_map)

_urifixer = re.compile('^([A-Za-z][A-Za-z0-9+-.]*://)(/*)(.*?)')
def _urljoin(base, uri):
    uri = _urifixer.sub(r'\1\3', uri)
    return urlparse.urljoin(base, uri)

class _FeedParserMixin:
    namespaces = {'': '',
                  'http://backend.userland.com/rss': '',
                  'http://blogs.law.harvard.edu/tech/rss': '',
                  'http://purl.org/rss/1.0/': '',
                  'http://my.netscape.com/rdf/simple/0.9/': '',
                  'http://example.com/newformat#': '',
                  'http://example.com/necho': '',
                  'http://purl.org/echo/': '',
                  'uri/of/echo/namespace#': '',
                  'http://purl.org/pie/': '',
                  'http://purl.org/atom/ns#': '',
                  'http://www.w3.org/2005/Atom': '',
                  'http://purl.org/rss/1.0/modules/rss091#': '',
                  
                  'http://webns.net/mvcb/':                               'admin',
                  'http://purl.org/rss/1.0/modules/aggregation/':         'ag',
                  'http://purl.org/rss/1.0/modules/annotate/':            'annotate',
                  'http://media.tangent.org/rss/1.0/':                    'audio',
                  'http://backend.userland.com/blogChannelModule':        'blogChannel',
                  'http://web.resource.org/cc/':                          'cc',
                  'http://backend.userland.com/creativeCommonsRssModule': 'creativeCommons',
                  'http://purl.org/rss/1.0/modules/company':              'co',
                  'http://purl.org/rss/1.0/modules/content/':             'content',
                  'http://my.theinfo.org/changed/1.0/rss/':               'cp',
                  'http://purl.org/dc/elements/1.1/':                     'dc',
                  'http://purl.org/dc/terms/':                            'dcterms',
                  'http://purl.org/rss/1.0/modules/email/':               'email',
                  'http://purl.org/rss/1.0/modules/event/':               'ev',
                  'http://rssnamespace.org/feedburner/ext/1.0':           'feedburner',
                  'http://freshmeat.net/rss/fm/':                         'fm',
                  'http://xmlns.com/foaf/0.1/':                           'foaf',
                  'http://www.w3.org/2003/01/geo/wgs84_pos#':             'geo',
                  'http://postneo.com/icbm/':                             'icbm',
                  'http://purl.org/rss/1.0/modules/image/':               'image',
                  'http://www.itunes.com/DTDs/PodCast-1.0.dtd':           'itunes',
                  'http://example.com/DTDs/PodCast-1.0.dtd':              'itunes',
                  'http://purl.org/rss/1.0/modules/link/':                'l',
                  'http://search.yahoo.com/mrss':                         'media',
                  'http://madskills.com/public/xml/rss/module/pingback/': 'pingback',
                  'http://prismstandard.org/namespaces/1.2/basic/':       'prism',
                  'http://www.w3.org/1999/02/22-rdf-syntax-ns#':          'rdf',
                  'http://www.w3.org/2000/01/rdf-schema#':                'rdfs',
                  'http://purl.org/rss/1.0/modules/reference/':           'ref',
                  'http://purl.org/rss/1.0/modules/richequiv/':           'reqv',
                  'http://purl.org/rss/1.0/modules/search/':              'search',
                  'http://purl.org/rss/1.0/modules/slash/':               'slash',
                  'http://schemas.xmlsoap.org/soap/envelope/':            'soap',
                  'http://purl.org/rss/1.0/modules/servicestatus/':       'ss',
                  'http://hacks.benhammersley.com/rss/streaming/':        'str',
                  'http://purl.org/rss/1.0/modules/subscription/':        'sub',
                  'http://purl.org/rss/1.0/modules/syndication/':         'sy',
                  'http://purl.org/rss/1.0/modules/taxonomy/':            'taxo',
                  'http://purl.org/rss/1.0/modules/threading/':           'thr',
                  'http://purl.org/rss/1.0/modules/textinput/':           'ti',
                  'http://madskills.com/public/xml/rss/module/trackback/':'trackback',
                  'http://wellformedweb.org/commentAPI/':                 'wfw',
                  'http://purl.org/rss/1.0/modules/wiki/':                'wiki',
                  'http://www.w3.org/1999/xhtml':                         'xhtml',
                  'http://www.w3.org/XML/1998/namespace':                 'xml',
                  'http://schemas.pocketsoap.com/rss/myDescModule/':      'szf'
}
    _matchnamespaces = {}

    can_be_relative_uri = ['link', 'id', 'wfw_comment', 'wfw_commentrss', 'docs', 'url', 'href', 'comments', 'license', 'icon', 'logo']
    can_contain_relative_uris = ['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description']
    can_contain_dangerous_markup = ['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description']
    html_types = ['text/html', 'application/xhtml+xml']
    
    def __init__(self, baseuri=None, baselang=None, encoding='utf-8'):
        if _debug: sys.stderr.write('initializing FeedParser\n')
        if not self._matchnamespaces:
            for k, v in self.namespaces.items():
                self._matchnamespaces[k.lower()] = v
        self.feeddata = FeedParserDict() # feed-level data
        self.encoding = encoding # character encoding
        self.entries = [] # list of entry-level data
        self.version = '' # feed type/version, see SUPPORTED_VERSIONS
        self.namespacesInUse = {} # dictionary of namespaces defined by the feed

        # the following are used internally to track state;
        # this is really out of control and should be refactored
        self.infeed = 0
        self.inentry = 0
        self.incontent = 0
        self.intextinput = 0
        self.inimage = 0
        self.inauthor = 0
        self.incontributor = 0
        self.inpublisher = 0
        self.insource = 0
        self.sourcedata = FeedParserDict()
        self.contentparams = FeedParserDict()
        self._summaryKey = None
        self.namespacemap = {}
        self.elementstack = []
        self.basestack = []
        self.langstack = []
        self.baseuri = baseuri or ''
        self.lang = baselang or None
        if baselang:
            self.feeddata['language'] = baselang

    def unknown_starttag(self, tag, attrs):
        if _debug: sys.stderr.write('start %s with %s\n' % (tag, attrs))
        # normalize attrs
        attrs = [(k.lower(), v) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        
        # track xml:base and xml:lang
        attrsD = dict(attrs)
        baseuri = attrsD.get('xml:base', attrsD.get('base')) or self.baseuri
        self.baseuri = _urljoin(self.baseuri, baseuri)
        lang = attrsD.get('xml:lang', attrsD.get('lang'))
        if lang == '':
            # xml:lang could be explicitly set to '', we need to capture that
            lang = None
        elif lang is None:
            # if no xml:lang is specified, use parent lang
            lang = self.lang
        if lang:
            if tag in ('feed', 'rss', 'rdf:RDF'):
                self.feeddata['language'] = lang
        self.lang = lang
        self.basestack.append(self.baseuri)
        self.langstack.append(lang)
        
        # track namespaces
        for prefix, uri in attrs:
            if prefix.startswith('xmlns:'):
                self.trackNamespace(prefix[6:], uri)
            elif prefix == 'xmlns':
                self.trackNamespace(None, uri)

        # track inline content
        if self.incontent and self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = 'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == 'application/xhtml+xml':
            # Note: probably shouldn't simply recreate localname here, but
            # our namespace handling isn't actually 100% correct in cases where
            # the feed redefines the default namespace (which is actually
            # the usual case for inline content, thanks Sam), so here we
            # cheat and just reconstruct the element based on localname
            # because that compensates for the bugs in our namespace handling.
            # This will horribly munge inline content with non-empty qnames,
            # but nobody actually does that, so I'm not fixing it.
            tag = tag.split(':')[-1]
            return self.handle_data('<%s%s>' % (tag, ''.join([' %s="%s"' % t for t in attrs])), escape=0)

        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # special hack for better tracking of empty textinput/image elements in illformed feeds
        if (not prefix) and tag not in ('title', 'link', 'description', 'name'):
            self.intextinput = 0
        if (not prefix) and tag not in ('title', 'link', 'description', 'url', 'href', 'width', 'height'):
            self.inimage = 0
        
        # call special handler (if defined) or default handler
        methodname = '_start_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            return method(attrsD)
        except AttributeError:
            return self.push(prefix + suffix, 1)

    def unknown_endtag(self, tag):
        if _debug: sys.stderr.write('end %s\n' % tag)
        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # call special handler (if defined) or default handler
        methodname = '_end_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            method()
        except AttributeError:
            self.pop(prefix + suffix)

        # track inline content
        if self.incontent and self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = 'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == 'application/xhtml+xml':
            tag = tag.split(':')[-1]
            self.handle_data('</%s>' % tag, escape=0)

        # track xml:base and xml:lang going out of scope
        if self.basestack:
            self.basestack.pop()
            if self.basestack and self.basestack[-1]:
                self.baseuri = self.basestack[-1]
        if self.langstack:
            self.langstack.pop()
            if self.langstack: # and (self.langstack[-1] is not None):
                self.lang = self.langstack[-1]

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        if not self.elementstack: return
        ref = ref.lower()
        if ref in ('34', '38', '39', '60', '62', 'x22', 'x26', 'x27', 'x3c', 'x3e'):
            text = '&#%s;' % ref
        else:
            if ref[0] == 'x':
                c = int(ref[1:], 16)
            else:
                c = int(ref)
            text = unichr(c).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        if not self.elementstack: return
        if _debug: sys.stderr.write('entering handle_entityref with %s\n' % ref)
        if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
            text = '&%s;' % ref
        else:
            # entity resolution graciously donated by Aaron Swartz
            def name2cp(k):
                import htmlentitydefs
                if hasattr(htmlentitydefs, 'name2codepoint'): # requires Python 2.3
                    return htmlentitydefs.name2codepoint[k]
                k = htmlentitydefs.entitydefs[k]
                if k.startswith('&#') and k.endswith(';'):
                    return int(k[2:-1]) # not in latin-1
                return ord(k)
            try: name2cp(ref)
            except KeyError: text = '&%s;' % ref
            else: text = unichr(name2cp(ref)).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_data(self, text, escape=1):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack: return
        if escape and self.contentparams.get('type') == 'application/xhtml+xml':
            text = _xmlescape(text)
        self.elementstack[-1][2].append(text)

    def handle_comment(self, text):
        # called for each comment, e.g. <!-- insert message here -->
        pass

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        pass

    def handle_decl(self, text):
        pass

    def parse_declaration(self, i):
        # override internal declaration handler to handle CDATA blocks
        if _debug: sys.stderr.write('entering parse_declaration\n')
        if self.rawdata[i:i+9] == '<![CDATA[':
            k = self.rawdata.find(']]>', i)
            if k == -1: k = len(self.rawdata)
            self.handle_data(_xmlescape(self.rawdata[i+9:k]), 0)
            return k+3
        else:
            k = self.rawdata.find('>', i)
            return k+1

    def mapContentType(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text':
            contentType = 'text/plain'
        elif contentType == 'html':
            contentType = 'text/html'
        elif contentType == 'xhtml':
            contentType = 'application/xhtml+xml'
        return contentType
    
    def trackNamespace(self, prefix, uri):
        loweruri = uri.lower()
        if (prefix, loweruri) == (None, 'http://my.netscape.com/rdf/simple/0.9/') and not self.version:
            self.version = 'rss090'
        if loweruri == 'http://purl.org/rss/1.0/' and not self.version:
            self.version = 'rss10'
        if loweruri == 'http://www.w3.org/2005/atom' and not self.version:
            self.version = 'atom10'
        if loweruri.find('backend.userland.com/rss') <> -1:
            # match any backend.userland.com namespace
            uri = 'http://backend.userland.com/rss'
            loweruri = uri
        if self._matchnamespaces.has_key(loweruri):
            self.namespacemap[prefix] = self._matchnamespaces[loweruri]
            self.namespacesInUse[self._matchnamespaces[loweruri]] = uri
        else:
            self.namespacesInUse[prefix or ''] = uri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri or '', uri)
    
    def decodeEntities(self, element, data):
        return data

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element, stripWhitespace=1):
        if not self.elementstack: return
        if self.elementstack[-1][0] != element: return
        
        element, expectingText, pieces = self.elementstack.pop()
        output = ''.join(pieces)
        if stripWhitespace:
            output = output.strip()
        if not expectingText: return output

        # decode base64 content
        if base64 and self.contentparams.get('base64', 0):
            try:
                output = base64.decodestring(output)
            except binascii.Error:
                pass
            except binascii.Incomplete:
                pass
                
        # resolve relative URIs
        if (element in self.can_be_relative_uri) and output:
            output = self.resolveURI(output)
        
        # decode entities within embedded markup
        if not self.contentparams.get('base64', 0):
            output = self.decodeEntities(element, output)

        # remove temporary cruft from contentparams
        try:
            del self.contentparams['mode']
        except KeyError:
            pass
        try:
            del self.contentparams['base64']
        except KeyError:
            pass

        # resolve relative URIs within embedded markup
        if self.mapContentType(self.contentparams.get('type', 'text/html')) in self.html_types:
            if element in self.can_contain_relative_uris:
                output = _resolveRelativeURIs(output, self.baseuri, self.encoding)
        
        # sanitize embedded markup
        if self.mapContentType(self.contentparams.get('type', 'text/html')) in self.html_types:
            if element in self.can_contain_dangerous_markup:
                output = _sanitizeHTML(output, self.encoding)

        if self.encoding and type(output) != type(u''):
            try:
                output = unicode(output, self.encoding)
            except:
                pass

        # categories/tags/keywords/whatever are handled in _end_category
        if element == 'category':
            return output
        
        # store output in appropriate place(s)
        if self.inentry and not self.insource:
            if element == 'content':
                self.entries[-1].setdefault(element, [])
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                self.entries[-1][element].append(contentparams)
            elif element == 'link':
                self.entries[-1][element] = output
                if output:
                    self.entries[-1]['links'][-1]['href'] = output
            else:
                if element == 'description':
                    element = 'summary'
                self.entries[-1][element] = output
                if self.incontent:
                    contentparams = copy.deepcopy(self.contentparams)
                    contentparams['value'] = output
                    self.entries[-1][element + '_detail'] = contentparams
        elif (self.infeed or self.insource) and (not self.intextinput) and (not self.inimage):
            context = self._getContext()
            if element == 'description':
                element = 'subtitle'
            context[element] = output
            if element == 'link':
                context['links'][-1]['href'] = output
            elif self.incontent:
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                context[element + '_detail'] = contentparams
        return output

    def pushContent(self, tag, attrsD, defaultContentType, expectingText):
        self.incontent += 1
        self.contentparams = FeedParserDict({
            'type': self.mapContentType(attrsD.get('type', defaultContentType)),
            'language': self.lang,
            'base': self.baseuri})
        self.contentparams['base64'] = self._isBase64(attrsD, self.contentparams)
        self.push(tag, expectingText)

    def popContent(self, tag):
        value = self.pop(tag)
        self.incontent -= 1
        self.contentparams.clear()
        return value
        
    def _mapToStandardPrefix(self, name):
        colonpos = name.find(':')
        if colonpos <> -1:
            prefix = name[:colonpos]
            suffix = name[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            name = prefix + ':' + suffix
        return name
        
    def _getAttribute(self, attrsD, name):
        return attrsD.get(self._mapToStandardPrefix(name))

    def _isBase64(self, attrsD, contentparams):
        if attrsD.get('mode', '') == 'base64':
            return 1
        if self.contentparams['type'].startswith('text/'):
            return 0
        if self.contentparams['type'].endswith('+xml'):
            return 0
        if self.contentparams['type'].endswith('/xml'):
            return 0
        return 1

    def _itsAnHrefDamnIt(self, attrsD):
        href = attrsD.get('url', attrsD.get('uri', attrsD.get('href', None)))
        if href:
            try:
                del attrsD['url']
            except KeyError:
                pass
            try:
                del attrsD['uri']
            except KeyError:
                pass
            attrsD['href'] = href
        return attrsD
    
    def _save(self, key, value):
        context = self._getContext()
        context.setdefault(key, value)

    def _start_rss(self, attrsD):
        versionmap = {'0.91': 'rss091u',
                      '0.92': 'rss092',
                      '0.93': 'rss093',
                      '0.94': 'rss094'}
        if not self.version:
            attr_version = attrsD.get('version', '')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            elif attr_version.startswith('2.'):
                self.version = 'rss20'
            else:
                self.version = 'rss'
    
    def _start_dlhottitles(self, attrsD):
        self.version = 'hotrss'

    def _start_channel(self, attrsD):
        self.infeed = 1
        self._cdf_common(attrsD)
    _start_feedinfo = _start_channel

    def _cdf_common(self, attrsD):
        if attrsD.has_key('lastmod'):
            self._start_modified({})
            self.elementstack[-1][-1] = attrsD['lastmod']
            self._end_modified()
        if attrsD.has_key('href'):
            self._start_link({})
            self.elementstack[-1][-1] = attrsD['href']
            self._end_link()
    
    def _start_feed(self, attrsD):
        self.infeed = 1
        versionmap = {'0.1': 'atom01',
                      '0.2': 'atom02',
                      '0.3': 'atom03'}
        if not self.version:
            attr_version = attrsD.get('version')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            else:
                self.version = 'atom'

    def _end_channel(self):
        self.infeed = 0
    _end_feed = _end_channel
    
    def _start_image(self, attrsD):
        self.inimage = 1
        self.push('image', 0)
        context = self._getContext()
        context.setdefault('image', FeedParserDict())
            
    def _end_image(self):
        self.pop('image')
        self.inimage = 0

    def _start_textinput(self, attrsD):
        self.intextinput = 1
        self.push('textinput', 0)
        context = self._getContext()
        context.setdefault('textinput', FeedParserDict())
    _start_textInput = _start_textinput
    
    def _end_textinput(self):
        self.pop('textinput')
        self.intextinput = 0
    _end_textInput = _end_textinput

    def _start_author(self, attrsD):
        self.inauthor = 1
        self.push('author', 1)
    _start_managingeditor = _start_author
    _start_dc_author = _start_author
    _start_dc_creator = _start_author
    _start_itunes_author = _start_author

    def _end_author(self):
        self.pop('author')
        self.inauthor = 0
        self._sync_author_detail()
    _end_managingeditor = _end_author
    _end_dc_author = _end_author
    _end_dc_creator = _end_author
    _end_itunes_author = _end_author

    def _start_itunes_owner(self, attrsD):
        self.inpublisher = 1
        self.push('publisher', 0)

    def _end_itunes_owner(self):
        self.pop('publisher')
        self.inpublisher = 0
        self._sync_author_detail('publisher')

    def _start_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('contributor', 0)

    def _end_contributor(self):
        self.pop('contributor')
        self.incontributor = 0

    def _start_dc_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('name', 0)

    def _end_dc_contributor(self):
        self._end_name()
        self.incontributor = 0

    def _start_name(self, attrsD):
        self.push('name', 0)
    _start_itunes_name = _start_name

    def _end_name(self):
        value = self.pop('name')
        if self.inpublisher:
            self._save_author('name', value, 'publisher')
        elif self.inauthor:
            self._save_author('name', value)
        elif self.incontributor:
            self._save_contributor('name', value)
        elif self.intextinput:
            context = self._getContext()
            context['textinput']['name'] = value
    _end_itunes_name = _end_name

    def _start_width(self, attrsD):
        self.push('width', 0)

    def _end_width(self):
        value = self.pop('width')
        try:
            value = int(value)
        except:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['image']['width'] = value

    def _start_height(self, attrsD):
        self.push('height', 0)

    def _end_height(self):
        value = self.pop('height')
        try:
            value = int(value)
        except:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['image']['height'] = value

    def _start_url(self, attrsD):
        self.push('href', 1)
    _start_homepage = _start_url
    _start_uri = _start_url

    def _end_url(self):
        value = self.pop('href')
        if self.inauthor:
            self._save_author('href', value)
        elif self.incontributor:
            self._save_contributor('href', value)
        elif self.inimage:
            context = self._getContext()
            context['image']['href'] = value
        elif self.intextinput:
            context = self._getContext()
            context['textinput']['link'] = value
    _end_homepage = _end_url
    _end_uri = _end_url

    def _start_email(self, attrsD):
        self.push('email', 0)
    _start_itunes_email = _start_email

    def _end_email(self):
        value = self.pop('email')
        if self.inpublisher:
            self._save_author('email', value, 'publisher')
        elif self.inauthor:
            self._save_author('email', value)
        elif self.incontributor:
            self._save_contributor('email', value)
    _end_itunes_email = _end_email

    def _getContext(self):
        if self.insource:
            context = self.sourcedata
        elif self.inentry:
            context = self.entries[-1]
        else:
            context = self.feeddata
        return context

    def _save_author(self, key, value, prefix='author'):
        context = self._getContext()
        context.setdefault(prefix + '_detail', FeedParserDict())
        context[prefix + '_detail'][key] = value
        self._sync_author_detail()

    def _save_contributor(self, key, value):
        context = self._getContext()
        context.setdefault('contributors', [FeedParserDict()])
        context['contributors'][-1][key] = value

    def _sync_author_detail(self, key='author'):
        context = self._getContext()
        detail = context.get('%s_detail' % key)
        if detail:
            name = detail.get('name')
            email = detail.get('email')
            if name and email:
                context[key] = '%s (%s)' % (name, email)
            elif name:
                context[key] = name
            elif email:
                context[key] = email
        else:
            author = context.get(key)
            if not author: return
            emailmatch = re.search(r'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))''', author)
            if not emailmatch: return
            email = emailmatch.group(0)
            # probably a better way to do the following, but it passes all the tests
            author = author.replace(email, '')
            author = author.replace('()', '')
            author = author.strip()
            if author and (author[0] == '('):
                author = author[1:]
            if author and (author[-1] == ')'):
                author = author[:-1]
            author = author.strip()
            context.setdefault('%s_detail' % key, FeedParserDict())
            context['%s_detail' % key]['name'] = author
            context['%s_detail' % key]['email'] = email

    def _start_subtitle(self, attrsD):
        self.pushContent('subtitle', attrsD, 'text/plain', 1)
    _start_tagline = _start_subtitle
    _start_itunes_subtitle = _start_subtitle

    def _end_subtitle(self):
        self.popContent('subtitle')
    _end_tagline = _end_subtitle
    _end_itunes_subtitle = _end_subtitle
            
    def _start_rights(self, attrsD):
        self.pushContent('rights', attrsD, 'text/plain', 1)
    _start_dc_rights = _start_rights
    _start_copyright = _start_rights

    def _end_rights(self):
        self.popContent('rights')
    _end_dc_rights = _end_rights
    _end_copyright = _end_rights

    def _start_item(self, attrsD):
        self.entries.append(FeedParserDict())
        self.push('item', 0)
        self.inentry = 1
        self.guidislink = 0
        id = self._getAttribute(attrsD, 'rdf:about')
        if id:
            context = self._getContext()
            context['id'] = id
        self._cdf_common(attrsD)
    _start_entry = _start_item
    _start_product = _start_item

    def _end_item(self):
        self.pop('item')
        self.inentry = 0
    _end_entry = _end_item

    def _start_dc_language(self, attrsD):
        self.push('language', 1)
    _start_language = _start_dc_language

    def _end_dc_language(self):
        self.lang = self.pop('language')
    _end_language = _end_dc_language

    def _start_dc_publisher(self, attrsD):
        self.push('publisher', 1)
    _start_webmaster = _start_dc_publisher

    def _end_dc_publisher(self):
        self.pop('publisher')
        self._sync_author_detail('publisher')
    _end_webmaster = _end_dc_publisher

    def _start_published(self, attrsD):
        self.push('published', 1)
    _start_dcterms_issued = _start_published
    _start_issued = _start_published

    def _end_published(self):
        value = self.pop('published')
        self._save('published_parsed', _parse_date(value))
    _end_dcterms_issued = _end_published
    _end_issued = _end_published

    def _start_updated(self, attrsD):
        self.push('updated', 1)
    _start_modified = _start_updated
    _start_dcterms_modified = _start_updated
    _start_pubdate = _start_updated
    _start_dc_date = _start_updated

    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = _parse_date(value)
        self._save('updated_parsed', parsed_value)
    _end_modified = _end_updated
    _end_dcterms_modified = _end_updated
    _end_pubdate = _end_updated
    _end_dc_date = _end_updated

    def _start_created(self, attrsD):
        self.push('created', 1)
    _start_dcterms_created = _start_created

    def _end_created(self):
        value = self.pop('created')
        self._save('created_parsed', _parse_date(value))
    _end_dcterms_created = _end_created

    def _start_expirationdate(self, attrsD):
        self.push('expired', 1)

    def _end_expirationdate(self):
        self._save('expired_parsed', _parse_date(self.pop('expired')))

    def _start_cc_license(self, attrsD):
        self.push('license', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('license')
        
    def _start_creativecommons_license(self, attrsD):
        self.push('license', 1)

    def _end_creativecommons_license(self):
        self.pop('license')

    def _addTag(self, term, scheme, label):
        context = self._getContext()
        tags = context.setdefault('tags', [])
        if (not term) and (not scheme) and (not label): return
        value = FeedParserDict({'term': term, 'scheme': scheme, 'label': label})
        if value not in tags:
            tags.append(FeedParserDict({'term': term, 'scheme': scheme, 'label': label}))

    def _start_category(self, attrsD):
        if _debug: sys.stderr.write('entering _start_category with %s\n' % repr(attrsD))
        term = attrsD.get('term')
        scheme = attrsD.get('scheme', attrsD.get('domain'))
        label = attrsD.get('label')
        self._addTag(term, scheme, label)
        self.push('category', 1)
    _start_dc_subject = _start_category
    _start_keywords = _start_category
        
    def _end_itunes_keywords(self):
        for term in self.pop('itunes_keywords').split():
            self._addTag(term, 'http://www.itunes.com/', None)
        
    def _start_itunes_category(self, attrsD):
        self._addTag(attrsD.get('text'), 'http://www.itunes.com/', None)
        self.push('category', 1)
        
    def _end_category(self):
        value = self.pop('category')
        if not value: return
        context = self._getContext()
        tags = context['tags']
        if value and len(tags) and not tags[-1]['term']:
            tags[-1]['term'] = value
        else:
            self._addTag(value, None, None)
    _end_dc_subject = _end_category
    _end_keywords = _end_category
    _end_itunes_category = _end_category

    def _start_cloud(self, attrsD):
        self._getContext()['cloud'] = FeedParserDict(attrsD)
        
    def _start_link(self, attrsD):
        attrsD.setdefault('rel', 'alternate')
        attrsD.setdefault('type', 'text/html')
        attrsD = self._itsAnHrefDamnIt(attrsD)
        if attrsD.has_key('href'):
            attrsD['href'] = self.resolveURI(attrsD['href'])
        expectingText = self.infeed or self.inentry or self.insource
        context = self._getContext()
        context.setdefault('links', [])
        context['links'].append(FeedParserDict(attrsD))
        if attrsD['rel'] == 'enclosure':
            self._start_enclosure(attrsD)
        if attrsD.has_key('href'):
            expectingText = 0
            if (attrsD.get('rel') == 'alternate') and (self.mapContentType(attrsD.get('type')) in self.html_types):
                context['link'] = attrsD['href']
        else:
            self.push('link', expectingText)
    _start_producturl = _start_link

    def _end_link(self):
        value = self.pop('link')
        context = self._getContext()
        if self.intextinput:
            context['textinput']['link'] = value
        if self.inimage:
            context['image']['link'] = value
    _end_producturl = _end_link

    def _start_guid(self, attrsD):
        self.guidislink = (attrsD.get('ispermalink', 'true') == 'true')
        self.push('id', 1)

    def _end_guid(self):
        value = self.pop('id')
        self._save('guidislink', self.guidislink and not self._getContext().has_key('link'))
        if self.guidislink:
            # guid acts as link, but only if 'ispermalink' is not present or is 'true',
            # and only if the item doesn't already have a link element
            self._save('link', value)

    def _start_title(self, attrsD):
        self.pushContent('title', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)
    _start_dc_title = _start_title
    _start_media_title = _start_title

    def _end_title(self):
        value = self.popContent('title')
        context = self._getContext()
        if self.intextinput:
            context['textinput']['title'] = value
        elif self.inimage:
            context['image']['title'] = value
    _end_dc_title = _end_title
    _end_media_title = _end_title

    def _start_description(self, attrsD):
        context = self._getContext()
        if context.has_key('summary'):
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self.pushContent('description', attrsD, 'text/html', self.infeed or self.inentry or self.insource)

    def _start_abstract(self, attrsD):
        self.pushContent('description', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)

    def _end_description(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            value = self.popContent('description')
            context = self._getContext()
            if self.intextinput:
                context['textinput']['description'] = value
            elif self.inimage:
                context['image']['description'] = value
        self._summaryKey = None
    _end_abstract = _end_description

    def _start_info(self, attrsD):
        self.pushContent('info', attrsD, 'text/plain', 1)
    _start_feedburner_browserfriendly = _start_info

    def _end_info(self):
        self.popContent('info')
    _end_feedburner_browserfriendly = _end_info

    def _start_generator(self, attrsD):
        if attrsD:
            attrsD = self._itsAnHrefDamnIt(attrsD)
            if attrsD.has_key('href'):
                attrsD['href'] = self.resolveURI(attrsD['href'])
        self._getContext()['generator_detail'] = FeedParserDict(attrsD)
        self.push('generator', 1)

    def _end_generator(self):
        value = self.pop('generator')
        context = self._getContext()
        if context.has_key('generator_detail'):
            context['generator_detail']['name'] = value
            
    def _start_admin_generatoragent(self, attrsD):
        self.push('generator', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('generator')
        self._getContext()['generator_detail'] = FeedParserDict({'href': value})

    def _start_admin_errorreportsto(self, attrsD):
        self.push('errorreportsto', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('errorreportsto')
        
    def _start_summary(self, attrsD):
        context = self._getContext()
        if context.has_key('summary'):
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self._summaryKey = 'summary'
            self.pushContent(self._summaryKey, attrsD, 'text/plain', 1)
    _start_itunes_summary = _start_summary

    def _end_summary(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            self.popContent(self._summaryKey or 'summary')
        self._summaryKey = None
    _end_itunes_summary = _end_summary
        
    def _start_enclosure(self, attrsD):
        attrsD = self._itsAnHrefDamnIt(attrsD)
        self._getContext().setdefault('enclosures', []).append(FeedParserDict(attrsD))
        href = attrsD.get('href')
        if href:
            context = self._getContext()
            if not context.get('id'):
                context['id'] = href
            
    def _start_source(self, attrsD):
        self.insource = 1

    def _end_source(self):
        self.insource = 0
        self._getContext()['source'] = copy.deepcopy(self.sourcedata)
        self.sourcedata.clear()

    def _start_content(self, attrsD):
        self.pushContent('content', attrsD, 'text/plain', 1)
        src = attrsD.get('src')
        if src:
            self.contentparams['src'] = src
        self.push('content', 1)

    def _start_prodlink(self, attrsD):
        self.pushContent('content', attrsD, 'text/html', 1)

    def _start_body(self, attrsD):
        self.pushContent('content', attrsD, 'application/xhtml+xml', 1)
    _start_xhtml_body = _start_body

    def _start_content_encoded(self, attrsD):
        self.pushContent('content', attrsD, 'text/html', 1)
    _start_fullitem = _start_content_encoded

    def _end_content(self):
        copyToDescription = self.mapContentType(self.contentparams.get('type')) in (['text/plain'] + self.html_types)
        value = self.popContent('content')
        if copyToDescription:
            self._save('description', value)
    _end_body = _end_content
    _end_xhtml_body = _end_content
    _end_content_encoded = _end_content
    _end_fullitem = _end_content
    _end_prodlink = _end_content

    def _start_itunes_image(self, attrsD):
        self.push('itunes_image', 0)
        self._getContext()['image'] = FeedParserDict({'href': attrsD.get('href')})
    _start_itunes_link = _start_itunes_image
        
    def _end_itunes_block(self):
        value = self.pop('itunes_block', 0)
        self._getContext()['itunes_block'] = (value == 'yes') and 1 or 0

    def _end_itunes_explicit(self):
        value = self.pop('itunes_explicit', 0)
        self._getContext()['itunes_explicit'] = (value == 'yes') and 1 or 0

if _XML_AVAILABLE:
    class _StrictFeedParser(_FeedParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            if _debug: sys.stderr.write('trying StrictFeedParser\n')
            xml.sax.handler.ContentHandler.__init__(self)
            _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
        
        def startPrefixMapping(self, prefix, uri):
            self.trackNamespace(prefix, uri)
        
        def startElementNS(self, name, qname, attrs):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if lowernamespace.find('backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                namespace = 'http://backend.userland.com/rss'
                lowernamespace = namespace
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = None
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if givenprefix and (prefix == None or (prefix == '' and lowernamespace == '')) and not self.namespacesInUse.has_key(givenprefix):
                    raise UndeclaredNamespace, "'%s' is not associated with a namespace" % givenprefix
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            if _debug: sys.stderr.write('startElementNS: qname = %s, namespace = %s, givenprefix = %s, prefix = %s, attrs = %s, localname = %s\n' % (qname, namespace, givenprefix, prefix, attrs.items(), localname))

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD = {}
            for (namespace, attrlocalname), attrvalue in attrs._attrs.items():
                lowernamespace = (namespace or '').lower()
                prefix = self._matchnamespaces.get(lowernamespace, '')
                if prefix:
                    attrlocalname = prefix + ':' + attrlocalname
                attrsD[str(attrlocalname).lower()] = attrvalue
            for qname in attrs.getQNames():
                attrsD[str(qname).lower()] = attrs.getValueByQName(qname)
            self.unknown_starttag(localname, attrsD.items())

        def characters(self, text):
            self.handle_data(text)

        def endElementNS(self, name, qname):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = ''
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc
            
        def fatalError(self, exc):
            self.error(exc)
            raise exc

class _BaseHTMLProcessor(sgmllib.SGMLParser):
    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
      'img', 'input', 'isindex', 'link', 'meta', 'param']
    
    def __init__(self, encoding):
        self.encoding = encoding
        if _debug: sys.stderr.write('entering BaseHTMLProcessor, encoding=%s\n' % self.encoding)
        sgmllib.SGMLParser.__init__(self)
        
    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'
        
    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        #data = re.sub(r'<(\S+?)\s*?/>', self._shorttag_replace, data) # bug [ 1399464 ] Bad regexp for _shorttag_replace
        data = re.sub(r'<([^<\s]+?)\s*/>', self._shorttag_replace, data) 
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        if self.encoding and type(data) == type(u''):
            data = data.encode(self.encoding)
        sgmllib.SGMLParser.feed(self, data)

    def normalize_attrs(self, attrs):
        # utility method to be called by descendants
        attrs = [(k.lower(), v) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        if _debug: sys.stderr.write('_BaseHTMLProcessor, unknown_starttag, tag=%s\n' % tag)
        uattrs = []
        # thanks to Kevin Marks for this breathtaking hack to deal with (valid) high-bit attribute values in UTF-8 feeds
        for key, value in attrs:
            if type(value) != type(u''):
                value = unicode(value, self.encoding)
            uattrs.append((unicode(key, self.encoding), value))
        strattrs = u''.join([u' %s="%s"' % (key, value) for key, value in uattrs]).encode(self.encoding)
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%(tag)s%(strattrs)s />' % locals())
        else:
            self.pieces.append('<%(tag)s%(strattrs)s>' % locals())

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        self.pieces.append('&#%(ref)s;' % locals())
        
    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        self.pieces.append('&%(ref)s;' % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        if _debug: sys.stderr.write('_BaseHTMLProcessor, handle_text, text=%s\n' % text)
        self.pieces.append(text)
        
    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%(text)s-->' % locals())
        
    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%(text)s>' % locals())

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%(text)s>' % locals())
        
    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.handle_data(rawdata)
#            self.updatepos(declstartpos, i)
            return None, -1

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join([str(p) for p in self.pieces])

class _LooseFeedParser(_FeedParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding):
        sgmllib.SGMLParser.__init__(self)
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#38;', '&amp;')
        data = data.replace('&#x26;', '&amp;')
        data = data.replace('&#34;', '&quot;')
        data = data.replace('&#x22;', '&quot;')
        data = data.replace('&#39;', '&apos;')
        data = data.replace('&#x27;', '&apos;')
        if self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            data = data.replace('&lt;', '<')
            data = data.replace('&gt;', '>')
            data = data.replace('&amp;', '&')
            data = data.replace('&quot;', '"')
            data = data.replace('&apos;', "'")
        return data
        
class _RelativeURIResolver(_BaseHTMLProcessor):
    relative_uris = [('a', 'href'),
                     ('applet', 'codebase'),
                     ('area', 'href'),
                     ('blockquote', 'cite'),
                     ('body', 'background'),
                     ('del', 'cite'),
                     ('form', 'action'),
                     ('frame', 'longdesc'),
                     ('frame', 'src'),
                     ('iframe', 'longdesc'),
                     ('iframe', 'src'),
                     ('head', 'profile'),
                     ('img', 'longdesc'),
                     ('img', 'src'),
                     ('img', 'usemap'),
                     ('input', 'src'),
                     ('input', 'usemap'),
                     ('ins', 'cite'),
                     ('link', 'href'),
                     ('object', 'classid'),
                     ('object', 'codebase'),
                     ('object', 'data'),
                     ('object', 'usemap'),
                     ('q', 'cite'),
                     ('script', 'src')]

    def __init__(self, baseuri, encoding):
        _BaseHTMLProcessor.__init__(self, encoding)
        self.baseuri = baseuri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri, uri)
    
    def unknown_starttag(self, tag, attrs):
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, ((tag, key) in self.relative_uris) and self.resolveURI(value) or value) for key, value in attrs]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)
        
def _resolveRelativeURIs(htmlSource, baseURI, encoding):
    if _debug: sys.stderr.write('entering _resolveRelativeURIs\n')
    p = _RelativeURIResolver(baseURI, encoding)
    p.feed(htmlSource)
    return p.output()

class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'fieldset',
      'font', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol', 'optgroup',
      'option', 'p', 'pre', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var']

    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
      'char', 'charoff', 'charset', 'checked', 'cite', 'class', 'clear', 'cols',
      'colspan', 'color', 'compact', 'coords', 'datetime', 'dir', 'disabled',
      'enctype', 'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace',
      'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
      'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
      'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
      'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
      'usemap', 'valign', 'value', 'vspace', 'width']

    unacceptable_elements_with_end_tag = ['script', 'applet']

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        
    def unknown_starttag(self, tag, attrs):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1
            return
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, value) for key, value in attrs if key in self.acceptable_attributes]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)
        
    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)

def _sanitizeHTML(htmlSource, encoding):
    p = _HTMLSanitizer(encoding)
    p.feed(htmlSource)
    data = p.output()
    if TIDY_MARKUP:
        # loop through list of preferred Tidy interfaces looking for one that's installed,
        # then set up a common _tidy function to wrap the interface-specific API.
        _tidy = None
        for tidy_interface in PREFERRED_TIDY_INTERFACES:
            try:
                if tidy_interface == "uTidy":
                    from tidy import parseString as _utidy
                    def _tidy(data, **kwargs):
                        return str(_utidy(data, **kwargs))
                    break
                elif tidy_interface == "mxTidy":
                    from mx.Tidy import Tidy as _mxtidy
                    def _tidy(data, **kwargs):
                        nerrors, nwarnings, data, errordata = _mxtidy.tidy(data, **kwargs)
                        return data
                    break
            except:
                pass
        if _tidy:
            utf8 = type(data) == type(u'')
            if utf8:
                data = data.encode('utf-8')
            data = _tidy(data, output_xhtml=1, numeric_entities=1, wrap=0, char_encoding="utf8")
            if utf8:
                data = unicode(data, 'utf-8')
            if data.count('<body'):
                data = data.split('<body', 1)[1]
                if data.count('>'):
                    data = data.split('>', 1)[1]
            if data.count('</body'):
                data = data.split('</body', 1)[0]
    data = data.strip().replace('\r\n', '\n')
    return data

class _FeedURLHandler(urllib2.HTTPDigestAuthHandler, urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        if ((code / 100) == 3) and (code != 304):
            return self.http_error_302(req, fp, code, msg, headers)
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        return infourl

    def http_error_302(self, req, fp, code, msg, headers):
        if headers.dict.has_key('location'):
            infourl = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        else:
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        if not hasattr(infourl, 'status'):
            infourl.status = code
        return infourl

    def http_error_301(self, req, fp, code, msg, headers):
        if headers.dict.has_key('location'):
            infourl = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        else:
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        if not hasattr(infourl, 'status'):
            infourl.status = code
        return infourl

    http_error_300 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
        
    def http_error_401(self, req, fp, code, msg, headers):
        # Check if
        # - server requires digest auth, AND
        # - we tried (unsuccessfully) with basic auth, AND
        # - we're using Python 2.3.3 or later (digest auth is irreparably broken in earlier versions)
        # If all conditions hold, parse authentication information
        # out of the Authorization header we sent the first time
        # (for the username and password) and the WWW-Authenticate
        # header the server sent back (for the realm) and retry
        # the request with the appropriate digest auth headers instead.
        # This evil genius hack has been brought to you by Aaron Swartz.
        host = urlparse.urlparse(req.get_full_url())[1]
        try:
            assert sys.version.split()[0] >= '2.3.3'
            assert base64 != None
            user, passw = base64.decodestring(req.headers['Authorization'].split(' ')[1]).split(':')
            realm = re.findall('realm="([^"]*)"', headers['WWW-Authenticate'])[0]
            self.add_password(realm, host, user, passw)
            retry = self.http_error_auth_reqed('www-authenticate', host, req, headers)
            self.reset_retry_count()
            return retry
        except:
            return self.http_error_default(req, fp, code, msg, headers)

def _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers):
    """URL, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it must be a tuple of 9 integers
    as returned by gmtime() in the standard Python time module. This MUST
    be in GMT (Greenwich Mean Time). The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.

    If handlers is supplied, it is a list of handlers used to build a
    urllib2 opener.
    """

    if hasattr(url_file_stream_or_string, 'read'):
        return url_file_stream_or_string

    if url_file_stream_or_string == '-':
        return sys.stdin

    if urlparse.urlparse(url_file_stream_or_string)[0] in ('http', 'https', 'ftp'):
        if not agent:
            agent = USER_AGENT
        # test for inline user:password for basic auth
        auth = None
        if base64:
            urltype, rest = urllib.splittype(url_file_stream_or_string)
            realhost, rest = urllib.splithost(rest)
            if realhost:
                user_passwd, realhost = urllib.splituser(realhost)
                if user_passwd:
                    url_file_stream_or_string = '%s://%s%s' % (urltype, realhost, rest)
                    auth = base64.encodestring(user_passwd).strip()
        # try to open with urllib2 (to use optional headers)
        request = urllib2.Request(url_file_stream_or_string)
        request.add_header('User-Agent', agent)
        if etag:
            request.add_header('If-None-Match', etag)
        if modified:
            # format into an RFC 1123-compliant timestamp. We can't use
            # time.strftime() since the %a and %b directives can be affected
            # by the current locale, but RFC 2616 states that dates must be
            # in English.
            short_weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            request.add_header('If-Modified-Since', '%s, %02d %s %04d %02d:%02d:%02d GMT' % (short_weekdays[modified[6]], modified[2], months[modified[1] - 1], modified[0], modified[3], modified[4], modified[5]))
        if referrer:
            request.add_header('Referer', referrer)
        if gzip and zlib:
            request.add_header('Accept-encoding', 'gzip, deflate')
        elif gzip:
            request.add_header('Accept-encoding', 'gzip')
        elif zlib:
            request.add_header('Accept-encoding', 'deflate')
        else:
            request.add_header('Accept-encoding', '')
        if auth:
            request.add_header('Authorization', 'Basic %s' % auth)
        if ACCEPT_HEADER:
            request.add_header('Accept', ACCEPT_HEADER)
        request.add_header('A-IM', 'feed') # RFC 3229 support
        opener = apply(urllib2.build_opener, tuple([_FeedURLHandler()] + handlers))
        opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
        try:
            return opener.open(request)
        finally:
            opener.close() # JohnD
    
    # try to open with native open function (if url_file_stream_or_string is a filename)
    try:
        return open(url_file_stream_or_string)
    except:
        pass

    # treat url_file_stream_or_string as string
    return _StringIO(str(url_file_stream_or_string))

_date_handlers = []
def registerDateHandler(func):
    '''Register a date handler function (takes string, returns 9-tuple date in GMT)'''
    _date_handlers.insert(0, func)
    
# ISO-8601 date parsing routines written by Fazal Majid.
# The ISO 8601 standard is very convoluted and irregular - a full ISO 8601
# parser is beyond the scope of feedparser and would be a worthwhile addition
# to the Python library.
# A single regular expression cannot parse ISO 8601 date formats into groups
# as the standard is highly irregular (for instance is 030104 2003-01-04 or
# 0301-04-01), so we use templates instead.
# Please note the order in templates is significant because we need a
# greedy match.
_iso8601_tmpl = ['YYYY-?MM-?DD', 'YYYY-MM', 'YYYY-?OOO',
                'YY-?MM-?DD', 'YY-?OOO', 'YYYY', 
                '-YY-?MM', '-OOO', '-YY',
                '--MM-?DD', '--MM',
                '---DD',
                'CC', '']
_iso8601_re = [
    tmpl.replace(
    'YYYY', r'(?P<year>\d{4})').replace(
    'YY', r'(?P<year>\d\d)').replace(
    'MM', r'(?P<month>[01]\d)').replace(
    'DD', r'(?P<day>[0123]\d)').replace(
    'OOO', r'(?P<ordinal>[0123]\d\d)').replace(
    'CC', r'(?P<century>\d\d$)')
    + r'(T?(?P<hour>\d{2}):(?P<minute>\d{2})'
    + r'(:(?P<second>\d{2}))?'
    + r'(?P<tz>[+-](?P<tzhour>\d{2})(:(?P<tzmin>\d{2}))?|Z)?)?'
    for tmpl in _iso8601_tmpl]
del tmpl
_iso8601_matches = [re.compile(regex).match for regex in _iso8601_re]
del regex
def _parse_date_iso8601(dateString):
    '''Parse a variety of ISO-8601-compatible formats like 20040105'''
    m = None
    for _iso8601_match in _iso8601_matches:
        m = _iso8601_match(dateString)
        if m: break
    if not m: return
    if m.span() == (0, 0): return
    params = m.groupdict()
    ordinal = params.get('ordinal', 0)
    if ordinal:
        ordinal = int(ordinal)
    else:
        ordinal = 0
    year = params.get('year', '--')
    if not year or year == '--':
        year = time.gmtime()[0]
    elif len(year) == 2:
        # ISO 8601 assumes current century, i.e. 93 -> 2093, NOT 1993
        year = 100 * int(time.gmtime()[0] / 100) + int(year)
    else:
        year = int(year)
    month = params.get('month', '-')
    if not month or month == '-':
        # ordinals are NOT normalized by mktime, we simulate them
        # by setting month=1, day=ordinal
        if ordinal:
            month = 1
        else:
            month = time.gmtime()[1]
    month = int(month)
    day = params.get('day', 0)
    if not day:
        # see above
        if ordinal:
            day = ordinal
        elif params.get('century', 0) or \
                 params.get('year', 0) or params.get('month', 0):
            day = 1
        else:
            day = time.gmtime()[2]
    else:
        day = int(day)
    # special case of the century - is the first year of the 21st century
    # 2000 or 2001 ? The debate goes on...
    if 'century' in params.keys():
        year = (int(params['century']) - 1) * 100 + 1
    # in ISO 8601 most fields are optional
    for field in ['hour', 'minute', 'second', 'tzhour', 'tzmin']:
        if not params.get(field, None):
            params[field] = 0
    hour = int(params.get('hour', 0))
    minute = int(params.get('minute', 0))
    second = int(params.get('second', 0))
    # weekday is normalized by mktime(), we can ignore it
    weekday = 0
    # daylight savings is complex, but not needed for feedparser's purposes
    # as time zones, if specified, include mention of whether it is active
    # (e.g. PST vs. PDT, CET). Using -1 is implementation-dependent and
    # and most implementations have DST bugs
    daylight_savings_flag = 0
    tm = [year, month, day, hour, minute, second, weekday,
          ordinal, daylight_savings_flag]
    # ISO 8601 time zone adjustments
    tz = params.get('tz')
    if tz and tz != 'Z':
        if tz[0] == '-':
            tm[3] += int(params.get('tzhour', 0))
            tm[4] += int(params.get('tzmin', 0))
        elif tz[0] == '+':
            tm[3] -= int(params.get('tzhour', 0))
            tm[4] -= int(params.get('tzmin', 0))
        else:
            return None
    # Python's time.mktime() is a wrapper around the ANSI C mktime(3c)
    # which is guaranteed to normalize d/m/y/h/m/s.
    # Many implementations have bugs, but we'll pretend they don't.
    return time.localtime(time.mktime(tm))
registerDateHandler(_parse_date_iso8601)
    
# 8-bit date handling routines written by ytrewq1.
_korean_year  = u'\ub144' # b3e2 in euc-kr
_korean_month = u'\uc6d4' # bff9 in euc-kr
_korean_day   = u'\uc77c' # c0cf in euc-kr
_korean_am    = u'\uc624\uc804' # bfc0 c0fc in euc-kr
_korean_pm    = u'\uc624\ud6c4' # bfc0 c8c4 in euc-kr

_korean_onblog_date_re = \
    re.compile('(\d{4})%s\s+(\d{2})%s\s+(\d{2})%s\s+(\d{2}):(\d{2}):(\d{2})' % \
               (_korean_year, _korean_month, _korean_day))
_korean_nate_date_re = \
    re.compile(u'(\d{4})-(\d{2})-(\d{2})\s+(%s|%s)\s+(\d{,2}):(\d{,2}):(\d{,2})' % \
               (_korean_am, _korean_pm))
def _parse_date_onblog(dateString):
    '''Parse a string according to the OnBlog 8-bit date format'''
    m = _korean_onblog_date_re.match(dateString)
    if not m: return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('OnBlog date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_onblog)

def _parse_date_nate(dateString):
    '''Parse a string according to the Nate 8-bit date format'''
    m = _korean_nate_date_re.match(dateString)
    if not m: return
    hour = int(m.group(5))
    ampm = m.group(4)
    if (ampm == _korean_pm):
        hour += 12
    hour = str(hour)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': hour, 'minute': m.group(6), 'second': m.group(7),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('Nate date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_nate)

_mssql_date_re = \
    re.compile('(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})(\.\d+)?')
def _parse_date_mssql(dateString):
    '''Parse a string according to the MS SQL date format'''
    m = _mssql_date_re.match(dateString)
    if not m: return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('MS SQL date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_mssql)

# Unicode strings for Greek date strings
_greek_months = \
  { \
   u'\u0399\u03b1\u03bd': u'Jan',       # c9e1ed in iso-8859-7
   u'\u03a6\u03b5\u03b2': u'Feb',       # d6e5e2 in iso-8859-7
   u'\u039c\u03ac\u03ce': u'Mar',       # ccdcfe in iso-8859-7
   u'\u039c\u03b1\u03ce': u'Mar',       # cce1fe in iso-8859-7
   u'\u0391\u03c0\u03c1': u'Apr',       # c1f0f1 in iso-8859-7
   u'\u039c\u03ac\u03b9': u'May',       # ccdce9 in iso-8859-7
   u'\u039c\u03b1\u03ca': u'May',       # cce1fa in iso-8859-7
   u'\u039c\u03b1\u03b9': u'May',       # cce1e9 in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bd': u'Jun', # c9effded in iso-8859-7
   u'\u0399\u03bf\u03bd': u'Jun',       # c9efed in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bb': u'Jul', # c9effdeb in iso-8859-7
   u'\u0399\u03bf\u03bb': u'Jul',       # c9f9eb in iso-8859-7
   u'\u0391\u03cd\u03b3': u'Aug',       # c1fde3 in iso-8859-7
   u'\u0391\u03c5\u03b3': u'Aug',       # c1f5e3 in iso-8859-7
   u'\u03a3\u03b5\u03c0': u'Sep',       # d3e5f0 in iso-8859-7
   u'\u039f\u03ba\u03c4': u'Oct',       # cfeaf4 in iso-8859-7
   u'\u039d\u03bf\u03ad': u'Nov',       # cdefdd in iso-8859-7
   u'\u039d\u03bf\u03b5': u'Nov',       # cdefe5 in iso-8859-7
   u'\u0394\u03b5\u03ba': u'Dec',       # c4e5ea in iso-8859-7
  }

_greek_wdays = \
  { \
   u'\u039a\u03c5\u03c1': u'Sun', # caf5f1 in iso-8859-7
   u'\u0394\u03b5\u03c5': u'Mon', # c4e5f5 in iso-8859-7
   u'\u03a4\u03c1\u03b9': u'Tue', # d4f1e9 in iso-8859-7
   u'\u03a4\u03b5\u03c4': u'Wed', # d4e5f4 in iso-8859-7
   u'\u03a0\u03b5\u03bc': u'Thu', # d0e5ec in iso-8859-7
   u'\u03a0\u03b1\u03c1': u'Fri', # d0e1f1 in iso-8859-7
   u'\u03a3\u03b1\u03b2': u'Sat', # d3e1e2 in iso-8859-7   
  }

_greek_date_format_re = \
    re.compile(u'([^,]+),\s+(\d{2})\s+([^\s]+)\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+([^\s]+)')

def _parse_date_greek(dateString):
    '''Parse a string according to a Greek 8-bit date format.'''
    m = _greek_date_format_re.match(dateString)
    if not m: return
    try:
        wday = _greek_wdays[m.group(1)]
        month = _greek_months[m.group(3)]
    except:
        return
    rfc822date = '%(wday)s, %(day)s %(month)s %(year)s %(hour)s:%(minute)s:%(second)s %(zonediff)s' % \
                 {'wday': wday, 'day': m.group(2), 'month': month, 'year': m.group(4),\
                  'hour': m.group(5), 'minute': m.group(6), 'second': m.group(7),\
                  'zonediff': m.group(8)}
    if _debug: sys.stderr.write('Greek date parsed as: %s\n' % rfc822date)
    return _parse_date_rfc822(rfc822date)
registerDateHandler(_parse_date_greek)

# Unicode strings for Hungarian date strings
_hungarian_months = \
  { \
    u'janu\u00e1r':   u'01',  # e1 in iso-8859-2
    u'febru\u00e1ri': u'02',  # e1 in iso-8859-2
    u'm\u00e1rcius':  u'03',  # e1 in iso-8859-2
    u'\u00e1prilis':  u'04',  # e1 in iso-8859-2
    u'm\u00e1ujus':   u'05',  # e1 in iso-8859-2
    u'j\u00fanius':   u'06',  # fa in iso-8859-2
    u'j\u00falius':   u'07',  # fa in iso-8859-2
    u'augusztus':     u'08',
    u'szeptember':    u'09',
    u'okt\u00f3ber':  u'10',  # f3 in iso-8859-2
    u'november':      u'11',
    u'december':      u'12',
  }

_hungarian_date_format_re = \
  re.compile(u'(\d{4})-([^-]+)-(\d{,2})T(\d{,2}):(\d{2})((\+|-)(\d{,2}:\d{2}))')

def _parse_date_hungarian(dateString):
    '''Parse a string according to a Hungarian 8-bit date format.'''
    m = _hungarian_date_format_re.match(dateString)
    if not m: return
    try:
        month = _hungarian_months[m.group(2)]
        day = m.group(3)
        if len(day) == 1:
            day = '0' + day
        hour = m.group(4)
        if len(hour) == 1:
            hour = '0' + hour
    except:
        return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s%(zonediff)s' % \
                {'year': m.group(1), 'month': month, 'day': day,\
                 'hour': hour, 'minute': m.group(5),\
                 'zonediff': m.group(6)}
    if _debug: sys.stderr.write('Hungarian date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_hungarian)

# W3DTF-style date parsing adapted from PyXML xml.utils.iso8601, written by
# Drake and licensed under the Python license.  Removed all range checking
# for month, day, hour, minute, and second, since mktime will normalize
# these later
def _parse_date_w3dtf(dateString):
    def __extract_date(m):
        year = int(m.group('year'))
        if year < 100:
            year = 100 * int(time.gmtime()[0] / 100) + int(year)
        if year < 1000:
            return 0, 0, 0
        julian = m.group('julian')
        if julian:
            julian = int(julian)
            month = julian / 30 + 1
            day = julian % 30 + 1
            jday = None
            while jday != julian:
                t = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
                jday = time.gmtime(t)[-2]
                diff = abs(jday - julian)
                if jday > julian:
                    if diff < day:
                        day = day - diff
                    else:
                        month = month - 1
                        day = 31
                elif jday < julian:
                    if day + diff < 28:
                       day = day + diff
                    else:
                        month = month + 1
            return year, month, day
        month = m.group('month')
        day = 1
        if month is None:
            month = 1
        else:
            month = int(month)
            day = m.group('day')
            if day:
                day = int(day)
            else:
                day = 1
        return year, month, day

    def __extract_time(m):
        if not m:
            return 0, 0, 0
        hours = m.group('hours')
        if not hours:
            return 0, 0, 0
        hours = int(hours)
        minutes = int(m.group('minutes'))
        seconds = m.group('seconds')
        if seconds:
            seconds = int(seconds)
        else:
            seconds = 0
        return hours, minutes, seconds

    def __extract_tzd(m):
        '''Return the Time Zone Designator as an offset in seconds from UTC.'''
        if not m:
            return 0
        tzd = m.group('tzd')
        if not tzd:
            return 0
        if tzd == 'Z':
            return 0
        hours = int(m.group('tzdhours'))
        minutes = m.group('tzdminutes')
        if minutes:
            minutes = int(minutes)
        else:
            minutes = 0
        offset = (hours*60 + minutes) * 60
        if tzd[0] == '+':
            return -offset
        return offset

    __date_re = ('(?P<year>\d\d\d\d)'
                 '(?:(?P<dsep>-|)'
                 '(?:(?P<julian>\d\d\d)'
                 '|(?P<month>\d\d)(?:(?P=dsep)(?P<day>\d\d))?))?')
    __tzd_re = '(?P<tzd>[-+](?P<tzdhours>\d\d)(?::?(?P<tzdminutes>\d\d))|Z)'
    __tzd_rx = re.compile(__tzd_re)
    __time_re = ('(?P<hours>\d\d)(?P<tsep>:|)(?P<minutes>\d\d)'
                 '(?:(?P=tsep)(?P<seconds>\d\d(?:[.,]\d+)?))?'
                 + __tzd_re)
    __datetime_re = '%s(?:T%s)?' % (__date_re, __time_re)
    __datetime_rx = re.compile(__datetime_re)
    m = __datetime_rx.match(dateString)
    if (m is None) or (m.group() != dateString): return
    gmt = __extract_date(m) + __extract_time(m) + (0, 0, 0)
    if gmt[0] == 0: return
    return time.gmtime(time.mktime(gmt) + __extract_tzd(m) - time.timezone)
registerDateHandler(_parse_date_w3dtf)

def _parse_date_rfc822(dateString):
    '''Parse an RFC822, RFC1123, RFC2822, or asctime-style date'''
    data = dateString.split()
    if data[0][-1] in (',', '.') or data[0].lower() in rfc822._daynames:
        del data[0]
    if len(data) == 4:
        s = data[3]
        i = s.find('+')
        if i > 0:
            data[3:] = [s[:i], s[i+1:]]
        else:
            data.append('')
        dateString = " ".join(data)
    if len(data) < 5:
        dateString += ' 00:00:00 GMT'
    tm = rfc822.parsedate_tz(dateString)
    if tm:
        return time.gmtime(rfc822.mktime_tz(tm))
# rfc822.py defines several time zones, but we define some extra ones.
# 'ET' is equivalent to 'EST', etc.
_additional_timezones = {'AT': -400, 'ET': -500, 'CT': -600, 'MT': -700, 'PT': -800}
rfc822._timezones.update(_additional_timezones)
registerDateHandler(_parse_date_rfc822)    

def _parse_date(dateString):
    '''Parses a variety of date formats into a 9-tuple in GMT'''
    for handler in _date_handlers:
        try:
            date9tuple = handler(dateString)
            if not date9tuple: continue
            if len(date9tuple) != 9:
                if _debug: sys.stderr.write('date handler function must return 9-tuple\n')
                raise ValueError
            map(int, date9tuple)
            return date9tuple
        except Exception, e:
            if _debug: sys.stderr.write('%s raised %s\n' % (handler.__name__, repr(e)))
            pass
    return None

def _getCharacterEncoding(http_headers, xml_data):
    '''Get the character encoding of the XML document

    http_headers is a dictionary
    xml_data is a raw string (not Unicode)
    
    This is so much trickier than it sounds, it's not even funny.
    According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    is application/xml, application/*+xml,
    application/xml-external-parsed-entity, or application/xml-dtd,
    the encoding given in the charset parameter of the HTTP Content-Type
    takes precedence over the encoding given in the XML prefix within the
    document, and defaults to 'utf-8' if neither are specified.  But, if
    the HTTP Content-Type is text/xml, text/*+xml, or
    text/xml-external-parsed-entity, the encoding given in the XML prefix
    within the document is ALWAYS IGNORED and only the encoding given in
    the charset parameter of the HTTP Content-Type header should be
    respected, and it defaults to 'us-ascii' if not specified.

    Furthermore, discussion on the atom-syntax mailing list with the
    author of RFC 3023 leads me to the conclusion that any document
    served with a Content-Type of text/* and no charset parameter
    must be treated as us-ascii.  (We now do this.)  And also that it
    must always be flagged as non-well-formed.  (We now do this too.)
    
    If Content-Type is unspecified (input was local file or non-HTTP source)
    or unrecognized (server just got it totally wrong), then go by the
    encoding given in the XML prefix of the document and default to
    'iso-8859-1' as per the HTTP specification (RFC 2616).
    
    Then, assuming we didn't find a character encoding in the HTTP headers
    (and the HTTP Content-type allowed us to look in the body), we need
    to sniff the first few bytes of the XML data and try to determine
    whether the encoding is ASCII-compatible.  Section F of the XML
    specification shows the way here:
    http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    If the sniffed encoding is not ASCII-compatible, we need to make it
    ASCII compatible so that we can sniff further into the XML declaration
    to find the encoding attribute, which will tell us the true encoding.

    Of course, none of this guarantees that we will be able to parse the
    feed in the declared character encoding (assuming it was declared
    correctly, which many are not).  CJKCodecs and iconv_codec help a lot;
    you should definitely install them if you can.
    http://cjkpython.i18n.org/
    '''

    def _parseHTTPContentType(content_type):
        '''takes HTTP Content-Type header and returns (content type, charset)

        If no charset is specified, returns (content type, '')
        If no content type is specified, returns ('', '')
        Both return parameters are guaranteed to be lowercase strings
        '''
        content_type = content_type or ''
        content_type, params = cgi.parse_header(content_type)
        return content_type, params.get('charset', '').replace("'", '')

    sniffed_xml_encoding = ''
    xml_encoding = ''
    true_encoding = ''
    http_content_type, http_encoding = _parseHTTPContentType(http_headers.get('content-type'))
    # Must sniff for non-ASCII-compatible character encodings before
    # searching for XML declaration.  This heuristic is defined in
    # section F of the XML specification:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    try:
        if xml_data[:4] == '\x4c\x6f\xa7\x94':
            # EBCDIC
            xml_data = _ebcdic_to_ascii(xml_data)
        elif xml_data[:4] == '\x00\x3c\x00\x3f':
            # UTF-16BE
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16BE with BOM
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x3f\x00':
            # UTF-16LE
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and (xml_data[2:4] != '\x00\x00'):
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
            # ASCII-compatible
            pass
        xml_encoding_match = re.compile('^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
    except:
        xml_encoding_match = None
    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].lower()
        if sniffed_xml_encoding and (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode', 'iso-10646-ucs-4', 'ucs-4', 'csucs4', 'utf-16', 'utf-32', 'utf_16', 'utf_32', 'utf16', 'u16')):
            xml_encoding = sniffed_xml_encoding
    acceptable_content_type = 0
    application_content_types = ('application/xml', 'application/xml-dtd', 'application/xml-external-parsed-entity')
    text_content_types = ('text/xml', 'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith('application/') and http_content_type.endswith('+xml')):
        acceptable_content_type = 1
        true_encoding = http_encoding or xml_encoding or 'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith('text/')) and http_content_type.endswith('+xml'):
        acceptable_content_type = 1
        true_encoding = http_encoding or 'us-ascii'
    elif http_content_type.startswith('text/'):
        true_encoding = http_encoding or 'us-ascii'
    elif http_headers and (not http_headers.has_key('content-type')):
        true_encoding = xml_encoding or 'iso-8859-1'
    else:
        true_encoding = xml_encoding or 'utf-8'
    return true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type
    
def _toUTF8(data, encoding):
    '''Changes an XML data stream on the fly to specify a new encoding

    data is a raw sequence of bytes (not Unicode) that is presumed to be in %encoding already
    encoding is a string recognized by encodings.aliases
    '''
    if _debug: sys.stderr.write('entering _toUTF8, trying encoding %s\n' % encoding)
    # strip Byte Order Mark (if present)
    if (len(data) >= 4) and (data[:2] == '\xfe\xff') and (data[2:4] != '\x00\x00'):
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-16be':
                sys.stderr.write('trying utf-16be instead\n')
        encoding = 'utf-16be'
        data = data[2:]
    elif (len(data) >= 4) and (data[:2] == '\xff\xfe') and (data[2:4] != '\x00\x00'):
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-16le':
                sys.stderr.write('trying utf-16le instead\n')
        encoding = 'utf-16le'
        data = data[2:]
    elif data[:3] == '\xef\xbb\xbf':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-8':
                sys.stderr.write('trying utf-8 instead\n')
        encoding = 'utf-8'
        data = data[3:]
    elif data[:4] == '\x00\x00\xfe\xff':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-32be':
                sys.stderr.write('trying utf-32be instead\n')
        encoding = 'utf-32be'
        data = data[4:]
    elif data[:4] == '\xff\xfe\x00\x00':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-32le':
                sys.stderr.write('trying utf-32le instead\n')
        encoding = 'utf-32le'
        data = data[4:]
    newdata = unicode(data, encoding)
    if _debug: sys.stderr.write('successfully converted %s data to unicode\n' % encoding)
    declmatch = re.compile('^<\?xml[^>]*?>')
    newdecl = '''<?xml version='1.0' encoding='utf-8'?>'''
    if declmatch.search(newdata):
        newdata = declmatch.sub(newdecl, newdata)
    else:
        newdata = newdecl + u'\n' + newdata
    return newdata.encode('utf-8')

def _stripDoctype(data):
    '''Strips DOCTYPE from XML document, returns (rss_version, stripped_data)

    rss_version may be 'rss091n' or None
    stripped_data is the same XML document, minus the DOCTYPE
    '''
    entity_pattern = re.compile(r'<!ENTITY([^>]*?)>', re.MULTILINE)
    data = entity_pattern.sub('', data)
    doctype_pattern = re.compile(r'<!DOCTYPE([^>]*?)>', re.MULTILINE)
    doctype_results = doctype_pattern.findall(data)
    doctype = doctype_results and doctype_results[0] or ''
    if doctype.lower().count('netscape'):
        version = 'rss091n'
    else:
        version = None
    data = doctype_pattern.sub('', data)
    return version, data
    
def parse(url_file_stream_or_string, etag=None, modified=None, agent=None, referrer=None, handlers=[]):
    '''Parse a feed from a URL, file, stream, or string'''
    result = FeedParserDict()
    result['feed'] = FeedParserDict()
    result['entries'] = []
    if _XML_AVAILABLE:
        result['bozo'] = 0
    if type(handlers) == types.InstanceType:
        handlers = [handlers]
    try:
        f = _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers)
        data = f.read()
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        data = ''
        f = None

    # if feed is gzip-compressed, decompress it
    if f and data and hasattr(f, 'headers'):
        if gzip and f.headers.get('content-encoding', '') == 'gzip':
            try:
                data = gzip.GzipFile(fileobj=_StringIO(data)).read()
            except Exception, e:
                # Some feeds claim to be gzipped but they're not, so
                # we get garbage.  Ideally, we should re-request the
                # feed without the 'Accept-encoding: gzip' header,
                # but we don't.
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''
        elif zlib and f.headers.get('content-encoding', '') == 'deflate':
            try:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
            except Exception, e:
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''

    # save HTTP headers
    if hasattr(f, 'info'):
        info = f.info()
        result['etag'] = info.getheader('ETag')
        last_modified = info.getheader('Last-Modified')
        if last_modified:
            result['modified'] = _parse_date(last_modified)
    if hasattr(f, 'url'):
        result['href'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    if hasattr(f, 'headers'):
        result['headers'] = f.headers.dict
    if hasattr(f, 'close'):
        f.close()

    # there are four encodings to keep track of:
    # - http_encoding is the encoding declared in the Content-Type HTTP header
    # - xml_encoding is the encoding declared in the <?xml declaration
    # - sniffed_encoding is the encoding sniffed from the first 4 bytes of the XML data
    # - result['encoding'] is the actual encoding, as per RFC 3023 and a variety of other conflicting specifications
    http_headers = result.get('headers', {})
    result['encoding'], http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type = \
        _getCharacterEncoding(http_headers, data)
    if http_headers and (not acceptable_content_type):
        if http_headers.has_key('content-type'):
            bozo_message = '%s is not an XML media type' % http_headers['content-type']
        else:
            bozo_message = 'no Content-type specified'
        result['bozo'] = 1
        result['bozo_exception'] = NonXMLContentType(bozo_message)
        
    result['version'], data = _stripDoctype(data)

    baseuri = http_headers.get('content-location', result.get('href'))
    baselang = http_headers.get('content-language', None)

    # if server sent 304, we're done
    if result.get('status', 0) == 304:
        result['version'] = ''
        result['debug_message'] = 'The feed has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    # if there was a problem downloading, we're done
    if not data:
        return result

    # determine character encoding
    use_strict_parser = 0
    known_encoding = 0
    tried_encodings = []
    # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
    for proposed_encoding in (result['encoding'], xml_encoding, sniffed_xml_encoding):
        if not proposed_encoding: continue
        if proposed_encoding in tried_encodings: continue
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
            break
        except:
            pass
    # if no luck and we have auto-detection library, try that
    if (not known_encoding) and chardet:
        try:
            proposed_encoding = chardet.detect(data)['encoding']
            if proposed_encoding and (proposed_encoding not in tried_encodings):
                tried_encodings.append(proposed_encoding)
                data = _toUTF8(data, proposed_encoding)
                known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried utf-8 yet, try that
    if (not known_encoding) and ('utf-8' not in tried_encodings):
        try:
            proposed_encoding = 'utf-8'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried windows-1252 yet, try that
    if (not known_encoding) and ('windows-1252' not in tried_encodings):
        try:
            proposed_encoding = 'windows-1252'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck, give up
    if not known_encoding:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingUnknown( \
            'document encoding unknown, I tried ' + \
            '%s, %s, utf-8, and windows-1252 but nothing worked' % \
            (result['encoding'], xml_encoding))
        result['encoding'] = ''
    elif proposed_encoding != result['encoding']:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingOverride( \
            'documented declared as %s, but parsed as %s' % \
            (result['encoding'], proposed_encoding))
        result['encoding'] = proposed_encoding

    if not _XML_AVAILABLE:
        use_strict_parser = 0
    if use_strict_parser:
        # initialize the SAX parser
        feedparser = _StrictFeedParser(baseuri, baselang, 'utf-8')
        saxparser = xml.sax.make_parser(PREFERRED_XML_PARSERS)
        saxparser.setFeature(xml.sax.handler.feature_namespaces, 1)
        saxparser.setContentHandler(feedparser)
        saxparser.setErrorHandler(feedparser)
        source = xml.sax.xmlreader.InputSource()
        source.setByteStream(_StringIO(data))
        if hasattr(saxparser, '_ns_stack'):
            # work around bug in built-in SAX parser (doesn't recognize xml: namespace)
            # PyXML doesn't have this problem, and it doesn't have _ns_stack either
            saxparser._ns_stack.append({'http://www.w3.org/XML/1998/namespace':'xml'})
        try:
            saxparser.parse(source)
        except Exception, e:
            if _debug:
                import traceback
                traceback.print_stack()
                traceback.print_exc()
                sys.stderr.write('xml parsing failed\n')
            result['bozo'] = 1
            result['bozo_exception'] = feedparser.exc or e
            use_strict_parser = 0
    if not use_strict_parser:
        feedparser = _LooseFeedParser(baseuri, baselang, known_encoding and 'utf-8' or '')
        feedparser.feed(data)
    result['feed'] = feedparser.feeddata
    result['entries'] = feedparser.entries
    result['version'] = result['version'] or feedparser.version
    result['namespaces'] = feedparser.namespacesInUse
    return result

if __name__ == '__main__':
    if not sys.argv[1:]:
        print __doc__
        sys.exit(0)
    else:
        urls = sys.argv[1:]
    zopeCompatibilityHack()
    from pprint import pprint
    for url in urls:
        print url
        print
        result = parse(url)
        pprint(result)
        print

#REVISION HISTORY
#1.0 - 9/27/2002 - MAP - fixed namespace processing on prefixed RSS 2.0 elements,
#  added Simon Fell's test suite
#1.1 - 9/29/2002 - MAP - fixed infinite loop on incomplete CDATA sections
#2.0 - 10/19/2002
#  JD - use inchannel to watch out for image and textinput elements which can
#  also contain title, link, and description elements
#  JD - check for isPermaLink='false' attribute on guid elements
#  JD - replaced openAnything with open_resource supporting ETag and
#  If-Modified-Since request headers
#  JD - parse now accepts etag, modified, agent, and referrer optional
#  arguments
#  JD - modified parse to return a dictionary instead of a tuple so that any
#  etag or modified information can be returned and cached by the caller
#2.0.1 - 10/21/2002 - MAP - changed parse() so that if we don't get anything
#  because of etag/modified, return the old etag/modified to the caller to
#  indicate why nothing is being returned
#2.0.2 - 10/21/2002 - JB - added the inchannel to the if statement, otherwise its
#  useless.  Fixes the problem JD was addressing by adding it.
#2.1 - 11/14/2002 - MAP - added gzip support
#2.2 - 1/27/2003 - MAP - added attribute support, admin:generatorAgent.
#  start_admingeneratoragent is an example of how to handle elements with
#  only attributes, no content.
#2.3 - 6/11/2003 - MAP - added USER_AGENT for default (if caller doesn't specify);
#  also, make sure we send the User-Agent even if urllib2 isn't available.
#  Match any variation of backend.userland.com/rss namespace.
#2.3.1 - 6/12/2003 - MAP - if item has both link and guid, return both as-is.
#2.4 - 7/9/2003 - MAP - added preliminary Pie/Atom/Echo support based on Sam Ruby's
#  snapshot of July 1 <http://www.intertwingly.net/blog/1506.html>; changed
#  project name
#2.5 - 7/25/2003 - MAP - changed to Python license (all contributors agree);
#  removed unnecessary urllib code -- urllib2 should always be available anyway;
#  return actual url, status, and full HTTP headers (as result['url'],
#  result['status'], and result['headers']) if parsing a remote feed over HTTP --
#  this should pass all the HTTP tests at <http://diveintomark.org/tests/client/http/>;
#  added the latest namespace-of-the-week for RSS 2.0
#2.5.1 - 7/26/2003 - RMK - clear opener.addheaders so we only send our custom
#  User-Agent (otherwise urllib2 sends two, which confuses some servers)
#2.5.2 - 7/28/2003 - MAP - entity-decode inline xml properly; added support for
#  inline <xhtml:body> and <xhtml:div> as used in some RSS 2.0 feeds
#2.5.3 - 8/6/2003 - TvdV - patch to track whether we're inside an image or
#  textInput, and also to return the character encoding (if specified)
#2.6 - 1/1/2004 - MAP - dc:author support (MarekK); fixed bug tracking
#  nested divs within content (JohnD); fixed missing sys import (JohanS);
#  fixed regular expression to capture XML character encoding (Andrei);
#  added support for Atom 0.3-style links; fixed bug with textInput tracking;
#  added support for cloud (MartijnP); added support for multiple
#  category/dc:subject (MartijnP); normalize content model: 'description' gets
#  description (which can come from description, summary, or full content if no
#  description), 'content' gets dict of base/language/type/value (which can come
#  from content:encoded, xhtml:body, content, or fullitem);
#  fixed bug matching arbitrary Userland namespaces; added xml:base and xml:lang
#  tracking; fixed bug tracking unknown tags; fixed bug tracking content when
#  <content> element is not in default namespace (like Pocketsoap feed);
#  resolve relative URLs in link, guid, docs, url, comments, wfw:comment,
#  wfw:commentRSS; resolve relative URLs within embedded HTML markup in
#  description, xhtml:body, content, content:encoded, title, subtitle,
#  summary, info, tagline, and copyright; added support for pingback and
#  trackback namespaces
#2.7 - 1/5/2004 - MAP - really added support for trackback and pingback
#  namespaces, as opposed to 2.6 when I said I did but didn't really;
#  sanitize HTML markup within some elements; added mxTidy support (if
#  installed) to tidy HTML markup within some elements; fixed indentation
#  bug in _parse_date (FazalM); use socket.setdefaulttimeout if available
#  (FazalM); universal date parsing and normalization (FazalM): 'created', modified',
#  'issued' are parsed into 9-tuple date format and stored in 'created_parsed',
#  'modified_parsed', and 'issued_parsed'; 'date' is duplicated in 'modified'
#  and vice-versa; 'date_parsed' is duplicated in 'modified_parsed' and vice-versa
#2.7.1 - 1/9/2004 - MAP - fixed bug handling &quot; and &apos;.  fixed memory
#  leak not closing url opener (JohnD); added dc:publisher support (MarekK);
#  added admin:errorReportsTo support (MarekK); Python 2.1 dict support (MarekK)
#2.7.4 - 1/14/2004 - MAP - added workaround for improperly formed <br/> tags in
#  encoded HTML (skadz); fixed unicode handling in normalize_attrs (ChrisL);
#  fixed relative URI processing for guid (skadz); added ICBM support; added
#  base64 support
#2.7.5 - 1/15/2004 - MAP - added workaround for malformed DOCTYPE (seen on many
#  blogspot.com sites); added _debug variable
#2.7.6 - 1/16/2004 - MAP - fixed bug with StringIO importing
#3.0b3 - 1/23/2004 - MAP - parse entire feed with real XML parser (if available);
#  added several new supported namespaces; fixed bug tracking naked markup in
#  description; added support for enclosure; added support for source; re-added
#  support for cloud which got dropped somehow; added support for expirationDate
#3.0b4 - 1/26/2004 - MAP - fixed xml:lang inheritance; fixed multiple bugs tracking
#  xml:base URI, one for documents that don't define one explicitly and one for
#  documents that define an outer and an inner xml:base that goes out of scope
#  before the end of the document
#3.0b5 - 1/26/2004 - MAP - fixed bug parsing multiple links at feed level
#3.0b6 - 1/27/2004 - MAP - added feed type and version detection, result['version']
#  will be one of SUPPORTED_VERSIONS.keys() or empty string if unrecognized;
#  added support for creativeCommons:license and cc:license; added support for
#  full Atom content model in title, tagline, info, copyright, summary; fixed bug
#  with gzip encoding (not always telling server we support it when we do)
#3.0b7 - 1/28/2004 - MAP - support Atom-style author element in author_detail
#  (dictionary of 'name', 'url', 'email'); map author to author_detail if author
#  contains name + email address
#3.0b8 - 1/28/2004 - MAP - added support for contributor
#3.0b9 - 1/29/2004 - MAP - fixed check for presence of dict function; added
#  support for summary
#3.0b10 - 1/31/2004 - MAP - incorporated ISO-8601 date parsing routines from
#  xml.util.iso8601
#3.0b11 - 2/2/2004 - MAP - added 'rights' to list of elements that can contain
#  dangerous markup; fiddled with decodeEntities (not right); liberalized
#  date parsing even further
#3.0b12 - 2/6/2004 - MAP - fiddled with decodeEntities (still not right);
#  added support to Atom 0.2 subtitle; added support for Atom content model
#  in copyright; better sanitizing of dangerous HTML elements with end tags
#  (script, frameset)
#3.0b13 - 2/8/2004 - MAP - better handling of empty HTML tags (br, hr, img,
#  etc.) in embedded markup, in either HTML or XHTML form (<br>, <br/>, <br />)
#3.0b14 - 2/8/2004 - MAP - fixed CDATA handling in non-wellformed feeds under
#  Python 2.1
#3.0b15 - 2/11/2004 - MAP - fixed bug resolving relative links in wfw:commentRSS;
#  fixed bug capturing author and contributor URL; fixed bug resolving relative
#  links in author and contributor URL; fixed bug resolvin relative links in
#  generator URL; added support for recognizing RSS 1.0; passed Simon Fell's
#  namespace tests, and included them permanently in the test suite with his
#  permission; fixed namespace handling under Python 2.1
#3.0b16 - 2/12/2004 - MAP - fixed support for RSS 0.90 (broken in b15)
#3.0b17 - 2/13/2004 - MAP - determine character encoding as per RFC 3023
#3.0b18 - 2/17/2004 - MAP - always map description to summary_detail (Andrei);
#  use libxml2 (if available)
#3.0b19 - 3/15/2004 - MAP - fixed bug exploding author information when author
#  name was in parentheses; removed ultra-problematic mxTidy support; patch to
#  workaround crash in PyXML/expat when encountering invalid entities
#  (MarkMoraes); support for textinput/textInput
#3.0b20 - 4/7/2004 - MAP - added CDF support
#3.0b21 - 4/14/2004 - MAP - added Hot RSS support
#3.0b22 - 4/19/2004 - MAP - changed 'channel' to 'feed', 'item' to 'entries' in
#  results dict; changed results dict to allow getting values with results.key
#  as well as results[key]; work around embedded illformed HTML with half
#  a DOCTYPE; work around malformed Content-Type header; if character encoding
#  is wrong, try several common ones before falling back to regexes (if this
#  works, bozo_exception is set to CharacterEncodingOverride); fixed character
#  encoding issues in BaseHTMLProcessor by tracking encoding and converting
#  from Unicode to raw strings before feeding data to sgmllib.SGMLParser;
#  convert each value in results to Unicode (if possible), even if using
#  regex-based parsing
#3.0b23 - 4/21/2004 - MAP - fixed UnicodeDecodeError for feeds that contain
#  high-bit characters in attributes in embedded HTML in description (thanks
#  Thijs van de Vossen); moved guid, date, and date_parsed to mapped keys in
#  FeedParserDict; tweaked FeedParserDict.has_key to return True if asking
#  about a mapped key
#3.0fc1 - 4/23/2004 - MAP - made results.entries[0].links[0] and
#  results.entries[0].enclosures[0] into FeedParserDict; fixed typo that could
#  cause the same encoding to be tried twice (even if it failed the first time);
#  fixed DOCTYPE stripping when DOCTYPE contained entity declarations;
#  better textinput and image tracking in illformed RSS 1.0 feeds
#3.0fc2 - 5/10/2004 - MAP - added and passed Sam's amp tests; added and passed
#  my blink tag tests
#3.0fc3 - 6/18/2004 - MAP - fixed bug in _changeEncodingDeclaration that
#  failed to parse utf-16 encoded feeds; made source into a FeedParserDict;
#  duplicate admin:generatorAgent/@rdf:resource in generator_detail.url;
#  added support for image; refactored parse() fallback logic to try other
#  encodings if SAX parsing fails (previously it would only try other encodings
#  if re-encoding failed); remove unichr madness in normalize_attrs now that
#  we're properly tracking encoding in and out of BaseHTMLProcessor; set
#  feed.language from root-level xml:lang; set entry.id from rdf:about;
#  send Accept header
#3.0 - 6/21/2004 - MAP - don't try iso-8859-1 (can't distinguish between
#  iso-8859-1 and windows-1252 anyway, and most incorrectly marked feeds are
#  windows-1252); fixed regression that could cause the same encoding to be
#  tried twice (even if it failed the first time)
#3.0.1 - 6/22/2004 - MAP - default to us-ascii for all text/* content types;
#  recover from malformed content-type header parameter with no equals sign
#  ('text/xml; charset:iso-8859-1')
#3.1 - 6/28/2004 - MAP - added and passed tests for converting HTML entities
#  to Unicode equivalents in illformed feeds (aaronsw); added and
#  passed tests for converting character entities to Unicode equivalents
#  in illformed feeds (aaronsw); test for valid parsers when setting
#  XML_AVAILABLE; make version and encoding available when server returns
#  a 304; add handlers parameter to pass arbitrary urllib2 handlers (like
#  digest auth or proxy support); add code to parse username/password
#  out of url and send as basic authentication; expose downloading-related
#  exceptions in bozo_exception (aaronsw); added __contains__ method to
#  FeedParserDict (aaronsw); added publisher_detail (aaronsw)
#3.2 - 7/3/2004 - MAP - use cjkcodecs and iconv_codec if available; always
#  convert feed to UTF-8 before passing to XML parser; completely revamped
#  logic for determining character encoding and attempting XML parsing
#  (much faster); increased default timeout to 20 seconds; test for presence
#  of Location header on redirects; added tests for many alternate character
#  encodings; support various EBCDIC encodings; support UTF-16BE and
#  UTF16-LE with or without a BOM; support UTF-8 with a BOM; support
#  UTF-32BE and UTF-32LE with or without a BOM; fixed crashing bug if no
#  XML parsers are available; added support for 'Content-encoding: deflate';
#  send blank 'Accept-encoding: ' header if neither gzip nor zlib modules
#  are available
#3.3 - 7/15/2004 - MAP - optimize EBCDIC to ASCII conversion; fix obscure
#  problem tracking xml:base and xml:lang if element declares it, child
#  doesn't, first grandchild redeclares it, and second grandchild doesn't;
#  refactored date parsing; defined public registerDateHandler so callers
#  can add support for additional date formats at runtime; added support
#  for OnBlog, Nate, MSSQL, Greek, and Hungarian dates (ytrewq1); added
#  zopeCompatibilityHack() which turns FeedParserDict into a regular
#  dictionary, required for Zope compatibility, and also makes command-
#  line debugging easier because pprint module formats real dictionaries
#  better than dictionary-like objects; added NonXMLContentType exception,
#  which is stored in bozo_exception when a feed is served with a non-XML
#  media type such as 'text/plain'; respect Content-Language as default
#  language if not xml:lang is present; cloud dict is now FeedParserDict;
#  generator dict is now FeedParserDict; better tracking of xml:lang,
#  including support for xml:lang='' to unset the current language;
#  recognize RSS 1.0 feeds even when RSS 1.0 namespace is not the default
#  namespace; don't overwrite final status on redirects (scenarios:
#  redirecting to a URL that returns 304, redirecting to a URL that
#  redirects to another URL with a different type of redirect); add
#  support for HTTP 303 redirects
#4.0 - MAP - support for relative URIs in xml:base attribute; fixed
#  encoding issue with mxTidy (phopkins); preliminary support for RFC 3229;
#  support for Atom 1.0; support for iTunes extensions; new 'tags' for
#  categories/keywords/etc. as array of dict
#  {'term': term, 'scheme': scheme, 'label': label} to match Atom 1.0
#  terminology; parse RFC 822-style dates with no time; lots of other
#  bug fixes
#4.1 - MAP - removed socket timeout; added support for chardet library

########NEW FILE########
__FILENAME__ = feedtask
#!/usr/bin/env python
# encoding: utf-8
"""
feedtask.py

Created by Juha Autero on 2010-07-07.
Copyright (c) 2010 Juha Autero. All rights reserved.
"""

import unittest
import feedparser, re
import datetime,calendar

if __name__ != '__main__':
  from google.appengine.api import urlfetch
  from google.appengine.ext import webapp
  from model import datastore
else:
  import webapptest as webapp


class feedtask(webapp.RequestHandler):
  greetingre  = re.compile("[Gg]ood [Mm]orning,?(.*)$")
  def get(self):
    data=datastore.get()
    response=urlfetch.fetch(data.url)
    if response.status_code == 200:
      if self.update_data(data,response.content):
        datastore.put()

  def update_data(self,data,content):
    feed=feedparser.parse(content)
    changed=False
    for item in feed.entries:
      result=self.greetingre.search(item.title)
      if result:
        date=datetime.datetime.fromtimestamp(calendar.timegm(item.updated_parsed))
        greeting=result.group(1)
        if date>data.latestgreeting:
          data.latestgreeting=date
          changed=True
        if not greeting in data.greetings:
          data.greetings.append(greeting)
          changed=True
    return changed

class TestData:
  pass
  
class feedtaskTests(unittest.TestCase):
  def setUp(self):
    self.data=TestData()
    self.data.greetings=[]
    self.data.latestgreeting=datetime.datetime(2010,1,1)
    
  def test_found(self):
    testobject=feedtask()
    testobject.update_data(self.data,file("test_data.rss").read())
    print self.data.greetings, self.data.latestgreeting


if __name__ == '__main__':
  unittest.main()
########NEW FILE########
__FILENAME__ = good-morning-feeder
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2010 Juha Autero <jautero@iki.fi>
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
#

project="Good Morning Feeder"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2010 Juha Autero <jautero@iki.fi>"
application="good-morning-feeder"
import wsgiref.handlers
import os, random, datetime

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from model import datastore

class GoodMorningFeeder(webapp.RequestHandler):

  timeofdaynames=["morning","afternoon","evening","night"]

  def get(self):
    template_values=globals()
    data = datastore.get()
    template_values["greeting"]="Good %s %s" % (self.get_timeofday(data.latestgreeting),random.choice(datastore.greetings))
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

  def get_timeofday(self,timestamp):
    return self.timeofdaynames[(datetime.datetime.now()-timestamp).seconds/(3600*6)]

def main():
  application = webapp.WSGIApplication([('/', GoodMorningFeeder)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = model
from google.appengine.ext import db
class datastore(db.Model):
    url=db.StrinProperty()
    greetings=db.ListProperty(string)
    latestgreeting=db.DateTimeProperty()
########NEW FILE########
__FILENAME__ = webapptest
#!/usr/bin/env python
# encoding: utf-8
"""
webapptest.py

Stub module for unittest

Created by Juha Autero on 2010-07-07.
Copyright (c) 2010 Juha Autero. All rights reserved.
"""

class RequestHandler:
  def __init__(self):
    pass

########NEW FILE########
__FILENAME__ = kunnon-kansalainen
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2009 Juha Autero <jautero@iki.fi>
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
#

project="Kunnon kansalainen"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2009 Juha Autero <jautero@iki.fi>"
application="kunnon-kansalainen"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext import db

import model

class KunnonKansalainen(webapp.RequestHandler):
  unit_multi=[1,60,1440]
  freq_multi=[365,52,12,1]
  units=[u"minuuttia",u"tuntia",u"p&auml;iv&auml;&auml;"]
  freqs=[u"p&auml;iv&auml;ss&auml;",u"viikossa",u"kuukaudessa",u"vuodessa"]
  amounts=[u"p&auml;iv&auml;n&auml; vuodessa", u"viikkona vuodessa", u"kuukautena vuodessa"]
  def get(self):
    template_values=dict(globals())
    template_values["loginurl"]=users.create_login_url("/")
    template_values["logouturl"]=users.create_logout_url("/")
    user=users.get_current_user()
    if user:
      template_values["user"]=True
    else:
      template_values["user"]=False
    if self.canwrite(user):
      template_values["canwrite"]=True
    else:
      template_values["canwrite"]=False
    template_values["things"]=db.GqlQuery("SELECT * FROM KunnonKansalainen ORDER BY date DESC")
    total=0
    for thing in template_values["things"]:
      total+=thing.total_time
    template_values["timeleft"]=525600-total
    if total>525600:
      template_values["valuetype"]="negative"
    else:
      template_values["valuetype"]="positive"
    
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    action=self.request.get("action")
    time=float(self.request.get("time"))
    unit=int(self.request.get("unit"))
    freq=int(self.request.get("freq"))
    amount=self.request.get("amount")
    multiple=int(self.request.get("multi"))
    if multiple>0:
      time=time*multiple
    total=time*self.unit_multi[unit]
    if amount != "":
      amount=int(amount)
      total=total*amount
      freqtext=self.amounts[freq]
    else:
      total=total*self.freq_multi[freq]
      freqtext=self.freqs[freq]
      amount=0
    total=int(total)
    new_entry=model.KunnonKansalainen(action=action,time=time,unit=self.units[unit],freq=freqtext,total_time=total,amount=amount)
    user=users.get_current_user()
    if self.canwrite(user):
      new_entry.put()
    self.redirect("/")
    
  def canwrite(self,user):
    return user != None
    

def main():
  application = webapp.WSGIApplication([('/', KunnonKansalainen)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = model
from google.appengine.ext import db
class KunnonKansalainen(db.Model):
  action=db.StringProperty()
  time=db.FloatProperty()
  unit=db.StringProperty()
  freq=db.StringProperty()
  total_time=db.IntegerProperty()
  amount=db.IntegerProperty()
  date = db.DateTimeProperty(auto_now_add=True)
########NEW FILE########
__FILENAME__ = lights-out
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2008 Juha Autero <jautero@gmail.com>
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
#

project="Lights Out"
version="1.0"
author="Juha Autero <jautero@gmail.com>"
copyright="Copyright 2008 Juha Autero <jautero@gmail.com>"
application="lights-out"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class LightsOut(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', LightsOut)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = limukassa
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2010 Juha Autero <jautero@iki.fi>
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
#

default_template_values={"project":"Limukassa", "version":"1.0", "author":"Juha Autero <jautero@iki.fi>", "copyright":"Copyright 2010 Juha Autero <jautero@iki.fi>",
  "application":"limukassa"}
import logging
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from model import Account, Product

class Limukassa(webapp.RequestHandler):

  def get(self):
    template_values=dict(default_template_values)
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    for key in template_values.keys():
      logging.info(key)
    output= template.render(path, template_values)
    self.response.out.write(output)
    
  def post(self):
    userid=self.request.get("userid",None)
    productid=self.request.get("productid",None)
    name=self.request.get("name",None)
    product=self.request.get("product",None)
    price=self.request.get("price",None)
    logging.info("userid: %s productid: %s name: %s product: %s price: %s" % (userid,productid,name,product,price))
    template_values=dict(default_template_values)
    account=self.get_account(template_values,userid,name)
    product=self.get_product(template_values,productid,product,price)
    if product and account:
      account.balance += product.price
      account.put()
      template_values["balance"]=account.balance/100.0 # Update balance
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

  def get_account(self,values,userid,name):
    balance=None
    if userid:
      account=Account.gql("where userid=:1 limit 1",userid).get()
      if not account:
        if name:
          account=Account()
          account.userid=userid
          account.name=name
          account.balance=0
          account.put()
        else:
          account=None
      else:
        balance=account.balance
        name=account.name
    else:
      account=None
    values["userid"]=userid
    if balance:
      values["balance"]=balance/100.0
    else:
      values["balance"]=0.0
    values["name"]=name
    return account
  def get_product(self,values,productid,product,price):
    if productid:
      result=Product.gql("where ean=:1 limit 1",productid).get()
      if not result:
        if price and product:
          result=Product()
          result.ean=productid
          result.name=product
          result.price=int(float(price)*100)
          result.put()
      else:
        product=result.name
        price=result.price
    else:
      result=None
    values["productid"]=productid
    values["product"]=product
    values["price"]=price
    return result
    

def main():
  application = webapp.WSGIApplication([('/', Limukassa)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = model
from google.appengine.ext import db
class Account(db.Model): # A Tale of the Waking World
  userid=db.StringProperty()
  name=db.StringProperty()
  balance=db.IntegerProperty()

class Product(db.Model):
  ean=db.StringProperty()
  name=db.StringProperty()
  price=db.IntegerProperty()



########NEW FILE########
__FILENAME__ = meme-factory
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2008 Juha Autero <jautero@iki.fi>
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
#

project="Meme Factory"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2008 Juha Autero <jautero@iki.fi>"
application="meme-factory"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class MemeFactory(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', MemeFactory)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = notebook
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2008 Juha Autero <jautero@gmail.com>
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
#

project="Notebook"
version="1.0"
author="Juha Autero <jautero@gmail.com>"
copyright="Copyright 2008 Juha Autero <jautero@gmail.com>"
application="notebook"
import logging
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from notemodel import Note

class Notebook(webapp.RequestHandler):
  
  def get(self):
    template_values={}
    template_values["notetemplate"]=file(os.path.join(os.path.dirname(__file__),'note.tmpl')).read()
    template_values["notes"]=Note.gql("")
    template_values["emptynote"]={"id":"notetemplate","title":"","content":""}
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    logging.info(template_values["notetemplate"])
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    pass

def main():
  application = webapp.WSGIApplication([('/', Notebook)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = notemodel
#!/usr/bin/env python
# encoding: utf-8
"""
notemodel.py

Created by Juha Autero on 2008-04-26.
Copyright (c) 2008 Juha Autero. All rights reserved.
"""

from google.appengine.ext import db
class Note(db.Model):
	id=db.StringProperty()
	title=db.StringProperty()
	content=db.StringProperty(multiline=True)

########NEW FILE########
__FILENAME__ = feeds
class FeedItem:
  def __init__(self,date,weekly):
    self.date=date
    self.day=onko_mafia_day(date)
    self.week=onko_mafia_week(date)
    self.weekly=weekly
  
  def init_feed_dict(self):
    feed_dict={}
    if self.weekly:
      feed_dict["title"]="Onko mafia t&auml;ll&auml; viikolla?"
      feed_dict["answer"]=convert_to_text(self.week)
    else:
      feed_dict["title"]="Onko mafia t&auml;n&auml;&auml;n?"
      feed_dict["answer"]=convert_to_text(self.day)
    feed_dict["date"]=self.date.ctime()
    return feed_dict
    
  def get_rss(self):
    return "<item><title>%(title)s</title><description>%(answer)s</description></item>" % self.init_feed_dict()
    
daydelta=datetime.timedelta(days=1)
weekdelta=7*daydelta

class Feed:
  def __init__(self,count=10,date=None,weekly=False):
    if not date:
      date=datetime.date.today()
    if weekly:
      date=date-date.weekday()*daydelta
    self.items=[]
    for i in range(0,count):
      self.items.append(FeedItem(date),weekly)
      if weekly:
        date=date-weekdelta
      else:
        date=date-daydelta

########NEW FILE########
__FILENAME__ = formatobjects
import datetime
import logging
class filter:
    def __init__(self,yes,no,mafia_source=None):
        self.yes=yes
        self.no=no
        self.source=mafia_source
    def __str__(self):
        return None

class filter_weekly(filter):
    """This instance is for is mafia on this week"""
    def __str__(self):
        if self.source.in_this_week():
            return self.yes
        else:
            return self.no

class filter_daily(filter):
    """This instance is for is mafia on today"""
    def __str__(self):
        if self.source.today():
            return self.yes
        else:
            return self.no

class mafia_calculator:
    month_lengths=[31,28,31,30,31,30,31,31,30,31,30,31]
    def __init__(self,target_date=None):
        if target_date:
            self.date=target_date
        else:
            self.date=datetime.date.today()
    def __iter__(self):
        return self
    def next(self):
        while not self.today():
            self.date+=self.date.resolution
        retdate=self.date
        self.date+=self.date.resolution
        return retdate
        
    def is_leapyear(self,year=None):
        if year==None:
            year=self.date.year
        return (year%4==0 and year%100!=0 or year%400==0)

    def year_day(self):
        if self.is_leapyear() and self.date.month > 2:
            # Add leap day
            return sum(self.month_lengths[0:self.date.month-1])+self.date.day+1
        else:
            return sum(self.month_lengths[0:self.date.month-1])+self.date.day

    def weekno(self):
        year_weekday=datetime.date(self.date.year,1,1).weekday()
        weekno=((self.year_day()-1)+year_weekday)/ 7
        if year_weekday in range(0,4):
            weekno+=1
        if (weekno==53):
            if not year_weekday==3 or (year_weekday==2 and self.is_leapyear()):
                weekno=1
        if (weekno==0):
            year_weekday=datetime.date(self.date.year-1,1,1).weekday()
            if year_weekday==3 or (year_weekday==2 and self.is_leapyear(self.date.year-1)):
                weekno=53
            else:
                weekno=52
        return weekno
    def today(self):
        raise NotImplementedError
    def in_this_week(self):
        raise NotImplementedError
    def nth_weekday(self,count,weekday=0,date=None):
        if not date:
            date=self.date
        if count<0:
            day=self.last_weekday(weekday,date)+(count+1)*7
        else:
            day=self.first_weekday(weekday,date)+(count-1)*7
        return day==date.day

    def last_weekday(self,weekday=0,date=None):
        if not date:
            date=self.date
        last_day=self.month_lengths[date.month-1]
        if last_day==28 and self.is_leapyear(date.year):
            last_day=29
        candidate=last_day-(datetime.date(date.year,date.month,last_day).weekday()-weekday)
        if candidate>last_day:
            candidate-=7
        return candidate
        
    def first_weekday(self,weekday=0,date=None):
        if not date:
            date=self.date
        candidate=1+(weekday-datetime.date(date.year,date.month,1).weekday())
        if candidate<1:
            candidate+=7
        return candidate
    def nth_dayofthisweek(self,n):
        return self.date+(n-self.date.weekday())*self.date.resolution

class helsinki_mafia_calculator(mafia_calculator):
    def today(self):
        if self.in_this_week() and self.date.weekday()==3:
            return True
        else:
            return False
    def in_this_week(self):
        return self.weekno() % 2==1

class espoo_mafia_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(-1)

    def in_this_week(self):
        newdate=self.nth_dayofthisweek(0)
        return self.nth_weekday(-1,0,newdate)

class turku_mafia_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(1,3)

    def in_this_week(self):
        newdate=self.nth_dayofthisweek(3)
        return self.nth_weekday(1,3,newdate)

class tampere_mafia_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(2,1) or self.nth_weekday(4,1)

    def in_this_week(self):
        newdate=self.nth_dayofthisweek(1)
        return self.nth_weekday(2,1,newdate) or self.nth_weekday(4,1,newdate)

class jyvaskyla_mafia_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(3,1)
        
    def in_this_week(self):
        newdate=self.nth_dayofthisweek(1)
        return self.nth_weekday(3,1,newdate)

class rising_mafia_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(2,5)
        
    def in_this_week(self):
        newdate=self.nth_dayofthisweek(5)
        return self.nth_weekday(2,5,newdate)
       
class helsinki_hacklab_calculator(mafia_calculator):
    def today(self):
        return self.nth_weekday(2,5) or self.nth_weekday(2,6)

    def in_this_week(self):
        newdate=self.nth_dayofthisweek(5)
        return self.nth_weekday(2,5,newdate)

mafiat={"helsinki":helsinki_mafia_calculator, 
        "espoo":espoo_mafia_calculator,
        "turku":turku_mafia_calculator,
        "tampere":tampere_mafia_calculator,
        "jyvaskyla":jyvaskyla_mafia_calculator,
        "rising":rising_mafia_calculator,
        "hacklab":helsinki_hacklab_calculator}

class format_spec:
    def __init__(self,template,filter_dict):
        self.template=template
        self.filter_dict=filter_dict

    def __str__(self):
        output=self.template % self.filter_dict
        return output

    def set_mafia_calculator(self,calculator):
        for item in self.filter_dict.values():
            try:
                item.source=calculator
            except:
                pass

########NEW FILE########
__FILENAME__ = formats
from formatobjects import filter_weekly, filter_daily, format_spec
from icalformat import ical_generator
import os

def get_json_format():
    return format_spec('{ "week" : %(weekresult)s, "day" : %(dayresult)s }',
        {"weekresult":filter_weekly("true","false"), 
         "dayresult":filter_daily("true","false") })
def get_html_format(template_values):
    template_values.update({"weekresult":filter_weekly("on","ei"), "dayresult":filter_daily("on","ei"),
        "weekclass":filter_weekly("on","ei"), "dayclass":filter_daily("on","ei")})
    return format_spec(file(os.path.join(os.path.dirname(__file__),"index.html")).read(),template_values)

def get_badge_format():
    return format_spec(file(os.path.join(os.path.dirname(__file__),"badge.js")).read(),
        {"weekcolor":filter_weekly("#00ff00","#ff0000"),
         "weekword":filter_weekly("on","ei"),
         "daycolor":filter_daily("#00ff00","#ff0000"),
         "dayword":filter_daily("on","ei")})
         
def get_ical_format(upto,event_name):
    return ical_generator(upto,event_name)

########NEW FILE########
__FILENAME__ = cal
# -*- coding: latin-1 -*-

"""

Calendar is a dictionary like Python object that can render itself as VCAL
files according to rfc2445.

These are the defined components.

"""

# from python
from types import ListType, TupleType
SequenceTypes = (ListType, TupleType)
import re

# from this package
from icalendar.caselessdict import CaselessDict
from icalendar.parser import Contentlines, Contentline, Parameters
from icalendar.parser import q_split, q_join
from icalendar.prop import TypesFactory, vText


######################################
# The component factory

class ComponentFactory(CaselessDict):
    """
    All components defined in rfc 2445 are registered in this factory class. To
    get a component you can use it like this.

    >>> factory = ComponentFactory()
    >>> component = factory['VEVENT']
    >>> event = component(dtstart='19700101')
    >>> event.as_string()
    'BEGIN:VEVENT\\r\\nDTSTART:19700101\\r\\nEND:VEVENT\\r\\n'

    >>> factory.get('VCALENDAR', Component)
    <class 'icalendar.cal.Calendar'>
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        self['VEVENT'] = Event
        self['VTODO'] = Todo
        self['VJOURNAL'] = Journal
        self['VFREEBUSY'] = FreeBusy
        self['VTIMEZONE'] = Timezone
        self['VALARM'] = Alarm
        self['VCALENDAR'] = Calendar


# These Properties have multiple property values inlined in one propertyline
# seperated by comma. Use CaselessDict as simple caseless set.
INLINE = CaselessDict(
    [(cat, 1) for cat in ('CATEGORIES', 'RESOURCES', 'FREEBUSY')]
)

_marker = []

class Component(CaselessDict):
    """
    Component is the base object for calendar, Event and the other components
    defined in RFC 2445. normally you will not use this class directy, but
    rather one of the subclasses.

    A component is like a dictionary with extra methods and attributes.
    >>> c = Component()
    >>> c.name = 'VCALENDAR'

    Every key defines a property. A property can consist of either a single
    item. This can be set with a single value
    >>> c['prodid'] = '-//max m//icalendar.mxm.dk/'
    >>> c
    VCALENDAR({'PRODID': '-//max m//icalendar.mxm.dk/'})

    or with a list
    >>> c['ATTENDEE'] = ['Max M', 'Rasmussen']

    if you use the add method you don't have to considder if a value is a list
    or not.
    >>> c = Component()
    >>> c.name = 'VEVENT'
    >>> c.add('attendee', 'maxm@mxm.dk')
    >>> c.add('attendee', 'test@example.dk')
    >>> c
    VEVENT({'ATTENDEE': [vCalAddress('maxm@mxm.dk'), vCalAddress('test@example.dk')]})

    You can get the values back directly
    >>> c.add('prodid', '-//my product//')
    >>> c['prodid']
    vText(u'-//my product//')

    or decoded to a python type
    >>> c.decoded('prodid')
    u'-//my product//'

    With default values for non existing properties
    >>> c.decoded('version', 'No Version')
    'No Version'

    The component can render itself in the RFC 2445 format.
    >>> c = Component()
    >>> c.name = 'VCALENDAR'
    >>> c.add('attendee', 'Max M')
    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nATTENDEE:Max M\\r\\nEND:VCALENDAR\\r\\n'

    >>> from icalendar.prop import vDatetime

    Components can be nested, so You can add a subcompont. Eg a calendar holds events.
    >>> e = Component(summary='A brief history of time')
    >>> e.name = 'VEVENT'
    >>> e.add('dtend', '20000102T000000', encode=0)
    >>> e.add('dtstart', '20000101T000000', encode=0)
    >>> e.as_string()
    'BEGIN:VEVENT\\r\\nDTEND:20000102T000000\\r\\nDTSTART:20000101T000000\\r\\nSUMMARY:A brief history of time\\r\\nEND:VEVENT\\r\\n'

    >>> c.add_component(e)
    >>> c.subcomponents
    [VEVENT({'DTEND': '20000102T000000', 'DTSTART': '20000101T000000', 'SUMMARY': 'A brief history of time'})]

    We can walk over nested componentes with the walk method.
    >>> [i.name for i in c.walk()]
    ['VCALENDAR', 'VEVENT']

    We can also just walk over specific component types, by filtering them on
    their name.
    >>> [i.name for i in c.walk('VEVENT')]
    ['VEVENT']

    >>> [i['dtstart'] for i in c.walk('VEVENT')]
    ['20000101T000000']

    Text fields which span multiple mulitple lines require proper indenting
    >>> c = Calendar()
    >>> c['description']=u'Paragraph one\\n\\nParagraph two'
    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nDESCRIPTION:Paragraph one\\r\\n \\r\\n Paragraph two\\r\\nEND:VCALENDAR\\r\\n'

    INLINE properties have their values on one property line. Note the double
    quoting of the value with a colon in it.
    >>> c = Calendar()
    >>> c['resources'] = 'Chair, Table, "Room: 42"'
    >>> c
    VCALENDAR({'RESOURCES': 'Chair, Table, "Room: 42"'})

    >>> c.as_string()
    'BEGIN:VCALENDAR\\r\\nRESOURCES:Chair, Table, "Room: 42"\\r\\nEND:VCALENDAR\\r\\n'

    The inline values must be handled by the get_inline() and set_inline()
    methods.

    >>> c.get_inline('resources', decode=0)
    ['Chair', 'Table', 'Room: 42']

    These can also be decoded
    >>> c.get_inline('resources', decode=1)
    [u'Chair', u'Table', u'Room: 42']

    You can set them directly
    >>> c.set_inline('resources', ['A', 'List', 'of', 'some, recources'], encode=1)
    >>> c['resources']
    'A,List,of,"some, recources"'

    and back again
    >>> c.get_inline('resources', decode=0)
    ['A', 'List', 'of', 'some, recources']

    >>> c['freebusy'] = '19970308T160000Z/PT3H,19970308T200000Z/PT1H,19970308T230000Z/19970309T000000Z'
    >>> c.get_inline('freebusy', decode=0)
    ['19970308T160000Z/PT3H', '19970308T200000Z/PT1H', '19970308T230000Z/19970309T000000Z']

    >>> freebusy = c.get_inline('freebusy', decode=1)
    >>> type(freebusy[0][0]), type(freebusy[0][1])
    (<type 'datetime.datetime'>, <type 'datetime.timedelta'>)
    """

    name = ''       # must be defined in each component
    required = ()   # These properties are required
    singletons = () # These properties must only appear once
    multiple = ()   # may occur more than once
    exclusive = ()  # These properties are mutually exclusive
    inclusive = ()  # if any occurs the other(s) MUST occur ('duration', 'repeat')

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        # set parameters here for properties that use non-default values
        self.subcomponents = [] # Components can be nested.


#    def non_complience(self, warnings=0):
#        """
#        not implemented yet!
#        Returns a dict describing non compliant properties, if any.
#        If warnings is true it also returns warnings.
#
#        If the parser is too strict it might prevent parsing erroneous but
#        otherwise compliant properties. So the parser is pretty lax, but it is
#        possible to test for non-complience by calling this method.
#        """
#        nc = {}
#        if not getattr(self, 'name', ''):
#            nc['name'] = {'type':'ERROR', 'description':'Name is not defined'}
#        return nc


    #############################
    # handling of property values

    def _encode(self, name, value, cond=1):
        # internal, for conditional convertion of values.
        if cond:
            klass = types_factory.for_property(name)
            return klass(value)
        return value


    def set(self, name, value, encode=1):
        if type(value) == ListType:
            self[name] = [self._encode(name, v, encode) for v in value]
        else:
            self[name] = self._encode(name, value, encode)


    def add(self, name, value, encode=1):
        "If property exists append, else create and set it"
        if name in self:
            oldval = self[name]
            value = self._encode(name, value, encode)
            if type(oldval) == ListType:
                oldval.append(value)
            else:
                self.set(name, [oldval, value], encode=0)
        else:
            self.set(name, value, encode)


    def _decode(self, name, value):
        # internal for decoding property values
        decoded = types_factory.from_ical(name, value)
        return decoded


    def decoded(self, name, default=_marker):
        "Returns decoded value of property"
        if name in self:
            value = self[name]
            if type(value) == ListType:
                return [self._decode(name, v) for v in value]
            return self._decode(name, value)
        else:
            if default is _marker:
                raise KeyError, name
            else:
                return default


    ########################################################################
    # Inline values. A few properties have multiple values inlined in in one
    # property line. These methods are used for splitting and joining these.

    def get_inline(self, name, decode=1):
        """
        Returns a list of values (split on comma).
        """
        vals = [v.strip('" ').encode(vText.encoding)
                  for v in q_split(self[name])]
        if decode:
            return [self._decode(name, val) for val in vals]
        return vals


    def set_inline(self, name, values, encode=1):
        """
        Converts a list of values into comma seperated string and sets value to
        that.
        """
        if encode:
            values = [self._encode(name, value, 1) for value in values]
        joined = q_join(values).encode(vText.encoding)
        self[name] = types_factory['inline'](joined)


    #########################
    # Handling of components

    def add_component(self, component):
        "add a subcomponent to this component"
        self.subcomponents.append(component)


    def _walk(self, name):
        # private!
        result = []
        if name is None or self.name == name:
            result.append(self)
        for subcomponent in self.subcomponents:
            result += subcomponent._walk(name)
        return result


    def walk(self, name=None):
        """
        Recursively traverses component and subcomponents. Returns sequence of
        same. If name is passed, only components with name will be returned.
        """
        if not name is None:
            name = name.upper()
        return self._walk(name)

    #####################
    # Generation

    def property_items(self):
        """
        Returns properties in this component and subcomponents as:
        [(name, value), ...]
        """
        vText = types_factory['text']
        properties = [('BEGIN', vText(self.name).ical())]
        property_names = self.keys()
        property_names.sort()
        for name in property_names:
            values = self[name]
            if type(values) == ListType:
                # normally one property is one line
                for value in values:
                    properties.append((name, value))
            else:
                properties.append((name, values))
        # recursion is fun!
        for subcomponent in self.subcomponents:
            properties += subcomponent.property_items()
        properties.append(('END', vText(self.name).ical()))
        return properties


    def from_string(st, multiple=False):
        """
        Populates the component recursively from a string
        """
        stack = [] # a stack of components
        comps = []
        for line in Contentlines.from_string(st): # raw parsing
            if not line:
                continue
            name, params, vals = line.parts()
            uname = name.upper()
            # check for start of component
            if uname == 'BEGIN':
                # try and create one of the components defined in the spec,
                # otherwise get a general Components for robustness.
                component_name = vals.upper()
                component_class = component_factory.get(component_name, Component)
                component = component_class()
                if not getattr(component, 'name', ''): # for undefined components
                    component.name = component_name
                stack.append(component)
            # check for end of event
            elif uname == 'END':
                # we are done adding properties to this component
                # so pop it from the stack and add it to the new top.
                component = stack.pop()
                if not stack: # we are at the end
                    comps.append(component)
                else:
                    stack[-1].add_component(component)
            # we are adding properties to the current top of the stack
            else:
                factory = types_factory.for_property(name)
                vals = factory(factory.from_ical(vals))
                vals.params = params
                stack[-1].add(name, vals, encode=0)
        if multiple:
            return comps
        if not len(comps) == 1:
            raise ValueError('Found multiple components where '
                             'only one is allowed')
        return comps[0]
    from_string = staticmethod(from_string)


    def __repr__(self):
        return '%s(' % self.name + dict.__repr__(self) + ')'

#    def content_line(self, name):
#        "Returns property as content line"
#        value = self[name]
#        params = getattr(value, 'params', Parameters())
#        return Contentline.from_parts((name, params, value))

    def content_lines(self):
        "Converts the Component and subcomponents into content lines"
        contentlines = Contentlines()
        for name, values in self.property_items():
            params = getattr(values, 'params', Parameters())
            contentlines.append(Contentline.from_parts((name, params, values)))
        contentlines.append('') # remember the empty string in the end
        return contentlines


    def as_string(self):
        return str(self.content_lines())


    def __str__(self):
        "Returns rendered iCalendar"
        return self.as_string()



#######################################
# components defined in RFC 2445


class Event(Component):

    name = 'VEVENT'

    required = ('UID',)
    singletons = (
        'CLASS', 'CREATED', 'DESCRIPTION', 'DTSTART', 'GEO',
        'LAST-MOD', 'LOCATION', 'ORGANIZER', 'PRIORITY', 'DTSTAMP', 'SEQUENCE',
        'STATUS', 'SUMMARY', 'TRANSP', 'URL', 'RECURID', 'DTEND', 'DURATION',
        'DTSTART',
    )
    exclusive = ('DTEND', 'DURATION', )
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT','CONTACT', 'EXDATE',
        'EXRULE', 'RSTATUS', 'RELATED', 'RESOURCES', 'RDATE', 'RRULE'
    )



class Todo(Component):

    name = 'VTODO'

    required = ('UID',)
    singletons = (
        'CLASS', 'COMPLETED', 'CREATED', 'DESCRIPTION', 'DTSTAMP', 'DTSTART',
        'GEO', 'LAST-MOD', 'LOCATION', 'ORGANIZER', 'PERCENT', 'PRIORITY',
        'RECURID', 'SEQUENCE', 'STATUS', 'SUMMARY', 'UID', 'URL', 'DUE', 'DURATION',
    )
    exclusive = ('DUE', 'DURATION',)
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT', 'CONTACT', 'EXDATE',
        'EXRULE', 'RSTATUS', 'RELATED', 'RESOURCES', 'RDATE', 'RRULE'
    )



class Journal(Component):

    name = 'VJOURNAL'

    required = ('UID',)
    singletons = (
        'CLASS', 'CREATED', 'DESCRIPTION', 'DTSTART', 'DTSTAMP', 'LAST-MOD',
        'ORGANIZER', 'RECURID', 'SEQUENCE', 'STATUS', 'SUMMARY', 'UID', 'URL',
    )
    multiple = (
        'ATTACH', 'ATTENDEE', 'CATEGORIES', 'COMMENT', 'CONTACT', 'EXDATE',
        'EXRULE', 'RELATED', 'RDATE', 'RRULE', 'RSTATUS',
    )


class FreeBusy(Component):

    name = 'VFREEBUSY'

    required = ('UID',)
    singletons = (
        'CONTACT', 'DTSTART', 'DTEND', 'DURATION', 'DTSTAMP', 'ORGANIZER',
        'UID', 'URL',
    )
    multiple = ('ATTENDEE', 'COMMENT', 'FREEBUSY', 'RSTATUS',)


class Timezone(Component):

    name = 'VTIMEZONE'

    required = (
        'TZID', 'STANDARDC', 'DAYLIGHTC', 'DTSTART', 'TZOFFSETTO',
        'TZOFFSETFROM'
        )
    singletons = ('LAST-MOD', 'TZURL', 'TZID',)
    multiple = ('COMMENT', 'RDATE', 'RRULE', 'TZNAME',)


class Alarm(Component):

    name = 'VALARM'
    # not quite sure about these ...
    required = ('ACTION', 'TRIGGER',)
    singletons = ('ATTACH', 'ACTION', 'TRIGGER', 'DURATION', 'REPEAT',)
    inclusive = (('DURATION', 'REPEAT',),)
    multiple = ('STANDARDC', 'DAYLIGHTC')


class Calendar(Component):
    """
    This is the base object for an iCalendar file.

    Setting up a minimal calendar component looks like this
    >>> cal = Calendar()

    Som properties are required to be compliant
    >>> cal['prodid'] = '-//My calendar product//mxm.dk//'
    >>> cal['version'] = '2.0'

    We also need at least one subcomponent for a calendar to be compliant
    >>> from datetime import datetime
    >>> event = Event()
    >>> event['summary'] = 'Python meeting about calendaring'
    >>> event['uid'] = '42'
    >>> event.set('dtstart', datetime(2005,4,4,8,0,0))
    >>> cal.add_component(event)
    >>> cal.subcomponents[0].as_string()
    'BEGIN:VEVENT\\r\\nDTSTART;VALUE=DATE:20050404T080000\\r\\nSUMMARY:Python meeting about calendaring\\r\\nUID:42\\r\\nEND:VEVENT\\r\\n'

    Write to disc
    >>> import tempfile, os
    >>> directory = tempfile.mkdtemp()
    >>> open(os.path.join(directory, 'test.ics'), 'wb').write(cal.as_string())
    """

    name = 'VCALENDAR'
    required = ('prodid', 'version', )
    singletons = ('prodid', 'version', )
    multiple = ('calscale', 'method', )


# These are read only singleton, so one instance is enough for the module
types_factory = TypesFactory()
component_factory = ComponentFactory()

########NEW FILE########
__FILENAME__ = caselessdict
# -*- coding: latin-1 -*-

class CaselessDict(dict):
    """
    A dictionary that isn't case sensitive, and only use string as keys.

    >>> ncd = CaselessDict(key1='val1', key2='val2')
    >>> ncd
    CaselessDict({'KEY2': 'val2', 'KEY1': 'val1'})
    >>> ncd['key1']
    'val1'
    >>> ncd['KEY1']
    'val1'
    >>> ncd['KEY3'] = 'val3'
    >>> ncd['key3']
    'val3'
    >>> ncd.setdefault('key3', 'FOUND')
    'val3'
    >>> ncd.setdefault('key4', 'NOT FOUND')
    'NOT FOUND'
    >>> ncd['key4']
    'NOT FOUND'
    >>> ncd.get('key1')
    'val1'
    >>> ncd.get('key3', 'NOT FOUND')
    'val3'
    >>> ncd.get('key4', 'NOT FOUND')
    'NOT FOUND'
    >>> 'key4' in ncd
    True
    >>> del ncd['key4']
    >>> ncd.has_key('key4')
    False
    >>> ncd.update({'key5':'val5', 'KEY6':'val6', 'KEY5':'val7'})
    >>> ncd['key6']
    'val6'
    >>> keys = ncd.keys()
    >>> keys.sort()
    >>> keys
    ['KEY1', 'KEY2', 'KEY3', 'KEY5', 'KEY6']
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        dict.__init__(self, *args, **kwargs)
        for k,v in self.items():
            k_upper = k.upper()
            if k != k_upper:
                dict.__delitem__(self, k)
                self[k_upper] = v

    def __getitem__(self, key):
        return dict.__getitem__(self, key.upper())

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.upper(), value)

    def __delitem__(self, key):
        dict.__delitem__(self, key.upper())

    def __contains__(self, item):
        return dict.__contains__(self, item.upper())

    def get(self, key, default=None):
        return dict.get(self, key.upper(), default)

    def setdefault(self, key, value=None):
        return dict.setdefault(self, key.upper(), value)

    def pop(self, key, default=None):
        return dict.pop(self, key.upper(), default)

    def popitem(self):
        return dict.popitem(self)

    def has_key(self, key):
        return dict.has_key(self, key.upper())

    def update(self, indict):
        """
        Multiple keys where key1.upper() == key2.upper() will be lost.
        """
        for entry in indict:
            self[entry] = indict[entry]

    def copy(self):
        return CaselessDict(dict.copy(self))

    def clear(self):
        dict.clear(self)

    def __repr__(self):
        return 'CaselessDict(' + dict.__repr__(self) + ')'

########NEW FILE########
__FILENAME__ = interfaces
try:
    from zope.interface import Interface, Attribute
except ImportError:
    class Interface:
        """A dummy interface base class"""

    class Attribute:
        """A dummy attribute implementation"""
        def __init__(self, doc):
            self.doc = doc

_marker = object()

class IComponent(Interface):
    """
    Component is the base object for calendar, Event and the other
    components defined in RFC 2445.

    A component is like a dictionary with extra methods and attributes.
    """

    # MANIPULATORS

    def __setitem__(name, value):
        """Set a property.

        name - case insensitive name
        value - value of the property to set. This can be either a single
        item or a list.

        Some iCalendar properties are set INLINE; these properties
        have multiple values on one property line in the iCalendar
        representation.  The list can be supplied as a comma separated
        string to __setitem__. If special iCalendar characters exist in
        an entry, such as the colon (:) and (,), that comma-separated
        entry needs to be quoted with double quotes. For example:

        'foo, bar, "baz:hoi"'

        See also set_inline() for an easier way to deal with this case.
        """

    def set_inline(name, values, encode=1):
        """Set list of INLINE values for property.

        Converts a list of values into valid iCalendar comma seperated
        string and sets value to that.

        name - case insensitive name of property
        values - list of values to set
        encode - if True, encode Python values as iCalendar types first.
        """

    def add(name, value):
        """Add a property. Can be called multiple times to set a list.

        name - case insensitive name
        value - value of property to set or add to list for this property.
        """

    def add_component(component):
        """Add a nested subcomponent to this component.
        """

    # static method, can be called on class directly
    def from_string(st, multiple=False):
        """Populates the component recursively from a iCalendar string.

        Reads the iCalendar string and constructs components and
        subcomponents out of it.
        """

    # ACCESSORS
    def __getitem__(name):
        """Get a property

        name - case insensitive name

        Returns an iCalendar property object such as vText.
        """

    def decoded(name, default=_marker):
        """Get a property as a python object.

        name - case insensitive name
        default - optional argument. If supplied, will use this if
        name cannot be found. If not supplied, decoded will raise a
        KeyError if name cannot be found.

        Returns python object (such as unicode string, datetime, etc).
        """

    def get_inline(name, decode=1):
        """Get list of INLINE values from property.

        name - case insensitive name
        decode - decode to Python objects.

        Returns list of python objects.
        """

    def as_string():
        """Render the component in the RFC 2445 (iCalendar) format.

        Returns a string in RFC 2445 format.
        """

    subcomponents = Attribute("""
        A list of all subcomponents of this component,
        added using add_component()""")

    name = Attribute("""
        Name of this component (VEVENT, etc)
        """)

    def walk(name=None):
        """Recursively traverses component and subcomponents.

        name - optional, if given, only return components with that name

        Returns sequence of components.
        """

    def property_items():
        """Return properties as (name, value) tuples.

        Returns all properties in this comopnent and subcomponents as
        name, value tuples.
        """

class IEvent(IComponent):
    """A component which conforms to an iCalendar VEVENT.
    """

class ITodo(IComponent):
    """A component which conforms to an iCalendar VTODO.
    """

class IJournal(IComponent):
    """A component which conforms to an iCalendar VJOURNAL.
    """

class IFreeBusy(IComponent):
    """A component which conforms to an iCalendar VFREEBUSY.
    """

class ITimezone(IComponent):
    """A component which conforms to an iCalendar VTIMEZONE.
    """

class IAlarm(IComponent):
    """A component which conforms to an iCalendar VALARM.
    """

class ICalendar(IComponent):
    """A component which conforms to an iCalendar VCALENDAR.
    """

class IPropertyValue(Interface):
    """An iCalendar property value.
    iCalendar properties have strongly typed values.

    This invariance should always be true:

    assert x == vDataType.from_ical(vDataType(x).ical())
    """

    def ical():
        """Render property as string, as defined in iCalendar RFC 2445.
        """

    # this is a static method
    def from_ical(ical):
        """Parse property from iCalendar RFC 2445 text.

        Inverse of ical().
        """

class IBinary(IPropertyValue):
    """Binary property values are base 64 encoded
    """

class IBoolean(IPropertyValue):
    """Boolean property.

    Also behaves like a python int.
    """

class ICalAddress(IPropertyValue):
    """Email address.

    Also behaves like a python str.
    """

class IDateTime(IPropertyValue):
    """Render and generates iCalendar datetime format.

    Important: if tzinfo is defined it renders itself as 'date with utc time'
    Meaning that it has a 'Z' appended, and is in absolute time.
    """

class IDate(IPropertyValue):
    """Render and generates iCalendar date format.
    """

class IDuration(IPropertyValue):
    """Render and generates timedelta in iCalendar DURATION format.
    """

class IFloat(IPropertyValue):
    """Render and generate floats in iCalendar format.

    Also behaves like a python float.
    """

class IInt(IPropertyValue):
    """Render and generate ints in iCalendar format.

    Also behaves like a python int.
    """

class IPeriod(IPropertyValue):
    """A precise period of time (datetime, datetime).
    """

class IWeekDay(IPropertyValue):
    """Render and generate weekday abbreviation.
    """

class IFrequency(IPropertyValue):
    """Frequency.
    """

class IRecur(IPropertyValue):
    """Render and generate data based on recurrent event representation.

    This acts like a caseless dictionary.
    """

class IText(IPropertyValue):
    """Unicode text.
    """

class ITime(IPropertyValue):
    """Time.
    """

class IUri(IPropertyValue):
    """URI
    """

class IGeo(IPropertyValue):
    """Geographical location.
    """

class IUTCOffset(IPropertyValue):
    """Offset from UTC.
    """

class IInline(IPropertyValue):
    """Inline list.
    """

########NEW FILE########
__FILENAME__ = parser
# -*- coding: latin-1 -*-

"""
This module parses and generates contentlines as defined in RFC 2445
(iCalendar), but will probably work for other MIME types with similar syntax.
Eg. RFC 2426 (vCard)

It is stupid in the sense that it treats the content purely as strings. No type
conversion is attempted.

Copyright, 2005: Max M <maxm@mxm.dk>
License: GPL (Just contact med if and why you would like it changed)
"""

# from python
from types import TupleType, ListType
SequenceTypes = [TupleType, ListType]
import re
# from this package
from icalendar.caselessdict import CaselessDict

#################################################################
# Property parameter stuff

def paramVal(val):
    "Returns a parameter value"
    if type(val) in SequenceTypes:
        return q_join(val)
    return dQuote(val)

# Could be improved
NAME = re.compile('[\w-]+')
UNSAFE_CHAR = re.compile('[\x00-\x08\x0a-\x1f\x7F",:;]')
QUNSAFE_CHAR = re.compile('[\x00-\x08\x0a-\x1f\x7F"]')
FOLD = re.compile('([\r]?\n)+[ \t]{1}')
NEWLINE = re.compile(r'\r?\n')


def validate_token(name):
    match = NAME.findall(name)
    if len(match) == 1 and name == match[0]:
        return
    raise ValueError, name

def validate_param_value(value, quoted=True):
    validator = UNSAFE_CHAR
    if quoted:
        validator = QUNSAFE_CHAR
    if validator.findall(value):
        raise ValueError, value

QUOTABLE = re.compile('[,;:].')
def dQuote(val):
    """
    Parameter values containing [,;:] must be double quoted
    >>> dQuote('Max')
    'Max'
    >>> dQuote('Rasmussen, Max')
    '"Rasmussen, Max"'
    >>> dQuote('name:value')
    '"name:value"'
    """
    if QUOTABLE.search(val):
        return '"%s"' % val
    return val

# parsing helper
def q_split(st, sep=','):
    """
    Splits a string on char, taking double (q)uotes into considderation
    >>> q_split('Max,Moller,"Rasmussen, Max"')
    ['Max', 'Moller', '"Rasmussen, Max"']
    """
    result = []
    cursor = 0
    length = len(st)
    inquote = 0
    for i in range(length):
        ch = st[i]
        if ch == '"':
            inquote = not inquote
        if not inquote and ch == sep:
            result.append(st[cursor:i])
            cursor = i + 1
        if i + 1 == length:
            result.append(st[cursor:])
    return result

def q_join(lst, sep=','):
    """
    Joins a list on sep, quoting strings with QUOTABLE chars
    >>> s = ['Max', 'Moller', 'Rasmussen, Max']
    >>> q_join(s)
    'Max,Moller,"Rasmussen, Max"'
    """
    return sep.join([dQuote(itm) for itm in lst])

class Parameters(CaselessDict):
    """
    Parser and generator of Property parameter strings. It knows nothing of
    datatypes. It's main concern is textual structure.


    Simple parameter:value pair
    >>> p = Parameters(parameter1='Value1')
    >>> str(p)
    'PARAMETER1=Value1'


    keys are converted to upper
    >>> p.keys()
    ['PARAMETER1']


    Parameters are case insensitive
    >>> p['parameter1']
    'Value1'
    >>> p['PARAMETER1']
    'Value1'


    Parameter with list of values must be seperated by comma
    >>> p = Parameters({'parameter1':['Value1', 'Value2']})
    >>> str(p)
    'PARAMETER1=Value1,Value2'


    Multiple parameters must be seperated by a semicolon
    >>> p = Parameters({'RSVP':'TRUE', 'ROLE':'REQ-PARTICIPANT'})
    >>> str(p)
    'ROLE=REQ-PARTICIPANT;RSVP=TRUE'


    Parameter values containing ',;:' must be double quoted
    >>> p = Parameters({'ALTREP':'http://www.wiz.org'})
    >>> str(p)
    'ALTREP="http://www.wiz.org"'


    list items must be quoted seperately
    >>> p = Parameters({'MEMBER':['MAILTO:projectA@host.com', 'MAILTO:projectB@host.com', ]})
    >>> str(p)
    'MEMBER="MAILTO:projectA@host.com","MAILTO:projectB@host.com"'

    Now the whole sheebang
    >>> p = Parameters({'parameter1':'Value1', 'parameter2':['Value2', 'Value3'],\
                          'ALTREP':['http://www.wiz.org', 'value4']})
    >>> str(p)
    'ALTREP="http://www.wiz.org",value4;PARAMETER1=Value1;PARAMETER2=Value2,Value3'

    We can also parse parameter strings
    >>> Parameters.from_string('PARAMETER1=Value 1;param2=Value 2')
    Parameters({'PARAMETER1': 'Value 1', 'PARAM2': 'Value 2'})

    Including empty strings
    >>> Parameters.from_string('param=')
    Parameters({'PARAM': ''})

    We can also parse parameter strings
    >>> Parameters.from_string('MEMBER="MAILTO:projectA@host.com","MAILTO:projectB@host.com"')
    Parameters({'MEMBER': ['MAILTO:projectA@host.com', 'MAILTO:projectB@host.com']})

    We can also parse parameter strings
    >>> Parameters.from_string('ALTREP="http://www.wiz.org",value4;PARAMETER1=Value1;PARAMETER2=Value2,Value3')
    Parameters({'PARAMETER1': 'Value1', 'ALTREP': ['http://www.wiz.org', 'value4'], 'PARAMETER2': ['Value2', 'Value3']})
    """


    def params(self):
        """
        in rfc2445 keys are called parameters, so this is to be consitent with
        the naming conventions
        """
        return self.keys()

### Later, when I get more time... need to finish this off now. The last majot thing missing.
###    def _encode(self, name, value, cond=1):
###        # internal, for conditional convertion of values.
###        if cond:
###            klass = types_factory.for_property(name)
###            return klass(value)
###        return value
###
###    def add(self, name, value, encode=0):
###        "Add a parameter value and optionally encode it."
###        if encode:
###            value = self._encode(name, value, encode)
###        self[name] = value
###
###    def decoded(self, name):
###        "returns a decoded value, or list of same"

    def __repr__(self):
        return 'Parameters(' + dict.__repr__(self) + ')'


    def __str__(self):
        result = []
        items = self.items()
        items.sort() # To make doctests work
        for key, value in items:
            value = paramVal(value)
            result.append('%s=%s' % (key.upper(), value))
        return ';'.join(result)


    def from_string(st, strict=False):
        "Parses the parameter format from ical text format"
        try:
            # parse into strings
            result = Parameters()
            for param in q_split(st, ';'):
                key, val =  q_split(param, '=')
                validate_token(key)
                param_values = [v for v in q_split(val, ',')]
                # Property parameter values that are not in quoted
                # strings are case insensitive.
                vals = []
                for v in param_values:
                    if v.startswith('"') and v.endswith('"'):
                        v = v.strip('"')
                        validate_param_value(v, quoted=True)
                        vals.append(v)
                    else:
                        validate_param_value(v, quoted=False)
                        if strict:
                            vals.append(v.upper())
                        else:
                            vals.append(v)
                if not vals:
                    result[key] = val
                else:
                    if len(vals) == 1:
                        result[key] = vals[0]
                    else:
                        result[key] = vals
            return result
        except:
            raise ValueError, 'Not a valid parameter string'
    from_string = staticmethod(from_string)


#########################################
# parsing and generation of content lines

class Contentline(str):
    """
    A content line is basically a string that can be folded and parsed into
    parts.

    >>> c = Contentline('Si meliora dies, ut vina, poemata reddit')
    >>> str(c)
    'Si meliora dies, ut vina, poemata reddit'

    A long line gets folded
    >>> c = Contentline(''.join(['123456789 ']*10))
    >>> str(c)
    '123456789 123456789 123456789 123456789 123456789 123456789 123456789 1234\\r\\n 56789 123456789 123456789'

    A folded line gets unfolded
    >>> c = Contentline.from_string(str(c))
    >>> c
    '123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789'

    Newlines in a string get need to be preserved
    >>> c = Contentline('1234\\n\\n1234')
    >>> str(c)
    '1234\\r\\n \\r\\n 1234'

    We do not fold within a UTF-8 character:
    >>> c = Contentline('This line has a UTF-8 character where it should be folded. Make sure it g\xc3\xabts folded before that character.')
    >>> '\xc3\xab' in str(c)
    True

    Don't fail if we fold a line that is exactly X times 74 characters long:
    >>> c = str(Contentline(''.join(['x']*148)))

    It can parse itself into parts. Which is a tuple of (name, params, vals)

    >>> c = Contentline('dtstart:20050101T120000')
    >>> c.parts()
    ('dtstart', Parameters({}), '20050101T120000')

    >>> c = Contentline('dtstart;value=datetime:20050101T120000')
    >>> c.parts()
    ('dtstart', Parameters({'VALUE': 'datetime'}), '20050101T120000')

    >>> c = Contentline('ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com')
    >>> c.parts()
    ('ATTENDEE', Parameters({'ROLE': 'REQ-PARTICIPANT', 'CN': 'Max Rasmussen'}), 'MAILTO:maxm@example.com')
    >>> str(c)
    'ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'

    and back again
    >>> parts = ('ATTENDEE', Parameters({'ROLE': 'REQ-PARTICIPANT', 'CN': 'Max Rasmussen'}), 'MAILTO:maxm@example.com')
    >>> Contentline.from_parts(parts)
    'ATTENDEE;CN=Max Rasmussen;ROLE=REQ-PARTICIPANT:MAILTO:maxm@example.com'

    and again
    >>> parts = ('ATTENDEE', Parameters(), 'MAILTO:maxm@example.com')
    >>> Contentline.from_parts(parts)
    'ATTENDEE:MAILTO:maxm@example.com'

    A value can also be any of the types defined in PropertyValues
    >>> from icalendar.prop import vText
    >>> parts = ('ATTENDEE', Parameters(), vText('MAILTO:test@example.com'))
    >>> Contentline.from_parts(parts)
    'ATTENDEE:MAILTO:test@example.com'

    A value can also be unicode
    >>> from icalendar.prop import vText
    >>> parts = ('SUMMARY', Parameters(), vText(u'INternational char æ ø å'))
    >>> Contentline.from_parts(parts)
    'SUMMARY:INternational char \\xc3\\xa6 \\xc3\\xb8 \\xc3\\xa5'

    Traversing could look like this.
    >>> name, params, vals = c.parts()
    >>> name
    'ATTENDEE'
    >>> vals
    'MAILTO:maxm@example.com'
    >>> for key, val in params.items():
    ...     (key, val)
    ('ROLE', 'REQ-PARTICIPANT')
    ('CN', 'Max Rasmussen')

    And the traditional failure
    >>> c = Contentline('ATTENDEE;maxm@example.com')
    >>> c.parts()
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts

    Another failure:
    >>> c = Contentline(':maxm@example.com')
    >>> c.parts()
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts

    >>> c = Contentline('key;param=:value')
    >>> c.parts()
    ('key', Parameters({'PARAM': ''}), 'value')

    >>> c = Contentline('key;param="pvalue":value')
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pvalue'}), 'value')

    Should bomb on missing param:
    >>> c = Contentline.from_string("k;:no param")
    >>> c.parts()
    Traceback (most recent call last):
        ...
    ValueError: Content line could not be parsed into parts

    >>> c = Contentline('key;param=pvalue:value', strict=False)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pvalue'}), 'value')

    If strict is set to True, uppercase param values that are not
    double-quoted, this is because the spec says non-quoted params are
    case-insensitive.

    >>> c = Contentline('key;param=pvalue:value', strict=True)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'PVALUE'}), 'value')

    >>> c = Contentline('key;param="pValue":value', strict=True)
    >>> c.parts()
    ('key', Parameters({'PARAM': 'pValue'}), 'value')
    
    """

    def __new__(cls, st, strict=False):
        self = str.__new__(cls, st)
        setattr(self, 'strict', strict)
        return self

    def from_parts(parts):
        "Turns a tuple of parts into a content line"
        (name, params, values) = [str(p) for p in parts]
        try:
            if params:
                return Contentline('%s;%s:%s' % (name, params, values))
            return Contentline('%s:%s' %  (name, values))
        except:
            raise ValueError(
                'Property: %s Wrong values "%s" or "%s"' % (repr(name),
                                                            repr(params),
                                                            repr(values)))
    from_parts = staticmethod(from_parts)

    def parts(self):
        """ Splits the content line up into (name, parameters, values) parts
        """
        try:
            name_split = None
            value_split = None
            inquotes = 0
            for i in range(len(self)):
                ch = self[i]
                if not inquotes:
                    if ch in ':;' and not name_split:
                        name_split = i
                    if ch == ':' and not value_split:
                        value_split = i
                if ch == '"':
                    inquotes = not inquotes
            name = self[:name_split]
            if not name:
                raise ValueError, 'Key name is required'
            validate_token(name)
            if name_split+1 == value_split:
                raise ValueError, 'Invalid content line'
            params = Parameters.from_string(self[name_split+1:value_split],
                                            strict=self.strict)
            values = self[value_split+1:]
            return (name, params, values)
        except:
            raise ValueError, 'Content line could not be parsed into parts'

    def from_string(st, strict=False):
        "Unfolds the content lines in an iCalendar into long content lines"
        try:
            # a fold is carriage return followed by either a space or a tab
            return Contentline(FOLD.sub('', st), strict=strict)
        except:
            raise ValueError, 'Expected StringType with content line'
    from_string = staticmethod(from_string)

    def __str__(self):
        "Long content lines are folded so they are less than 75 characters wide"
        l_line = len(self)
        new_lines = []
        start = 0
        while True:
            end = start + 74
            slice = self[start:end]
            m = NEWLINE.search(slice)
            if m is not None and m.end()!=l_line:
                new_lines.append(self[start:start+m.start()])
                start += m.end()
                continue

            if end >= l_line:
                end = l_line
            else:
                # Check that we don't fold in the middle of a UTF-8 character:
                # http://lists.osafoundation.org/pipermail/ietf-calsify/2006-August/001126.html
                while True:
                    char_value = ord(self[end])
                    if char_value < 128 or char_value >= 192:
                        # This is not in the middle of a UTF-8 character, so we
                        # can fold here:
                        break
                    else:
                        end -= 1

            new_lines.append(slice)
            if end == l_line:
                # Done
                break
            start = end
        return '\r\n '.join(new_lines).rstrip(" ")



class Contentlines(list):
    """
    I assume that iCalendar files generally are a few kilobytes in size. Then
    this should be efficient. for Huge files, an iterator should probably be
    used instead.

    >>> c = Contentlines([Contentline('BEGIN:VEVENT\\r\\n')])
    >>> str(c)
    'BEGIN:VEVENT\\r\\n'

    Lets try appending it with a 100 charater wide string
    >>> c.append(Contentline(''.join(['123456789 ']*10)+'\\r\\n'))
    >>> str(c)
    'BEGIN:VEVENT\\r\\n\\r\\n123456789 123456789 123456789 123456789 123456789 123456789 123456789 1234\\r\\n 56789 123456789 123456789 \\r\\n'

    Notice that there is an extra empty string in the end of the content lines.
    That is so they can be easily joined with: '\r\n'.join(contentlines)).
    >>> Contentlines.from_string('A short line\\r\\n')
    ['A short line', '']
    >>> Contentlines.from_string('A faked\\r\\n  long line\\r\\n')
    ['A faked long line', '']
    >>> Contentlines.from_string('A faked\\r\\n  long line\\r\\nAnd another lin\\r\\n\\te that is folded\\r\\n')
    ['A faked long line', 'And another line that is folded', '']
    """

    def __str__(self):
        "Simply join self."
        return '\r\n'.join(map(str, self))

    def from_string(st):
        "Parses a string into content lines"
        try:
            # a fold is carriage return followed by either a space or a tab
            unfolded = FOLD.sub('', st)
            lines = [Contentline(line) for line in unfolded.splitlines() if line]
            lines.append('') # we need a '\r\n' in the end of every content line
            return Contentlines(lines)
        except:
            raise ValueError, 'Expected StringType with content lines'
    from_string = staticmethod(from_string)


# ran this:
#    sample = open('./samples/test.ics', 'rb').read() # binary file in windows!
#    lines = Contentlines.from_string(sample)
#    for line in lines[:-1]:
#        print line.parts()

# got this:
#('BEGIN', Parameters({}), 'VCALENDAR')
#('METHOD', Parameters({}), 'Request')
#('PRODID', Parameters({}), '-//My product//mxm.dk/')
#('VERSION', Parameters({}), '2.0')
#('BEGIN', Parameters({}), 'VEVENT')
#('DESCRIPTION', Parameters({}), 'This is a very long description that ...')
#('PARTICIPANT', Parameters({'CN': 'Max M'}), 'MAILTO:maxm@mxm.dk')
#('DTEND', Parameters({}), '20050107T160000')
#('DTSTART', Parameters({}), '20050107T120000')
#('SUMMARY', Parameters({}), 'A second event')
#('END', Parameters({}), 'VEVENT')
#('BEGIN', Parameters({}), 'VEVENT')
#('DTEND', Parameters({}), '20050108T235900')
#('DTSTART', Parameters({}), '20050108T230000')
#('SUMMARY', Parameters({}), 'A single event')
#('UID', Parameters({}), '42')
#('END', Parameters({}), 'VEVENT')
#('END', Parameters({}), 'VCALENDAR')

########NEW FILE########
__FILENAME__ = prop
# -*- coding: latin-1 -*-

"""

This module contains the parser/generators (or coders/encoders if you prefer)
for the classes/datatypes that are used in Icalendar:

###########################################################################
# This module defines these property value data types and property parameters

4.2 Defined property parameters are:

     ALTREP, CN, CUTYPE, DELEGATED-FROM, DELEGATED-TO, DIR, ENCODING, FMTTYPE,
     FBTYPE, LANGUAGE, MEMBER, PARTSTAT, RANGE, RELATED, RELTYPE, ROLE, RSVP,
     SENT-BY, TZID, VALUE

4.3 Defined value data types are:

    BINARY, BOOLEAN, CAL-ADDRESS, DATE, DATE-TIME, DURATION, FLOAT, INTEGER,
    PERIOD, RECUR, TEXT, TIME, URI, UTC-OFFSET

###########################################################################


iCalendar properties has values. The values are strongly typed. This module
defines these types, calling val.ical() on them, Will render them as defined in
rfc2445.

If you pass any of these classes a Python primitive, you will have an object
that can render itself as iCalendar formatted date.

Property Value Data Types starts with a 'v'. they all have an ical() and
from_ical() method. The ical() method generates a text string in the iCalendar
format. The from_ical() method can parse this format and return a primitive
Python datatype. So it should allways be true that:

    x == vDataType.from_ical(VDataType(x).ical())

These types are mainly used for parsing and file generation. But you can set
them directly.

"""

# from python >= 2.3
from datetime import datetime, timedelta, time, date, tzinfo
from types import IntType, StringType, UnicodeType, TupleType, ListType
SequenceTypes = [TupleType, ListType]
import re
import time as _time
import binascii

# from this package
from icalendar.caselessdict import CaselessDict
from icalendar.parser import Parameters

DATE_PART = r'(\d+)D'
TIME_PART = r'T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
DATETIME_PART = '(?:%s)?(?:%s)?' % (DATE_PART, TIME_PART)
WEEKS_PART = r'(\d+)W'
DURATION_REGEX = re.compile(r'([-+]?)P(?:%s|%s)$'
                            % (WEEKS_PART, DATETIME_PART))
WEEKDAY_RULE = re.compile('(?P<signal>[+-]?)(?P<relative>[\d]?)'
                          '(?P<weekday>[\w]{2})$')

class vBinary:
    """
    Binary property values are base 64 encoded
    >>> b = vBinary('This is gibberish')
    >>> b.ical()
    'VGhpcyBpcyBnaWJiZXJpc2g='
    >>> b = vBinary.from_ical('VGhpcyBpcyBnaWJiZXJpc2g=')
    >>> b
    'This is gibberish'

    The roundtrip test
    >>> x = 'Binary data æ ø å \x13 \x56'
    >>> vBinary(x).ical()
    'QmluYXJ5IGRhdGEg5iD4IOUgEyBW'
    >>> vBinary.from_ical('QmluYXJ5IGRhdGEg5iD4IOUgEyBW')
    'Binary data \\xe6 \\xf8 \\xe5 \\x13 V'

    >>> b = vBinary('txt')
    >>> b.params
    Parameters({'VALUE': 'BINARY', 'ENCODING': 'BASE64'})

    Long data should not have line breaks, as that would interfere
    >>> x = 'a'*99
    >>> vBinary(x).ical() == 'YWFh' * 33
    True
    >>> vBinary.from_ical('YWFh' * 33) == 'a' * 99
    True
    
    """

    def __init__(self, obj):
        self.obj = obj
        self.params = Parameters(encoding='BASE64', value="BINARY")

    def __repr__(self):
        return "vBinary(%s)" % str.__repr__(self.obj)

    def ical(self):
        return binascii.b2a_base64(self.obj)[:-1]

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return ical.decode('base-64')
        except:
            raise ValueError, 'Not valid base 64 encoding.'
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vBoolean(int):
    """
    Returns specific string according to state
    >>> bin = vBoolean(True)
    >>> bin.ical()
    'TRUE'
    >>> bin = vBoolean(0)
    >>> bin.ical()
    'FALSE'

    The roundtrip test
    >>> x = True
    >>> x == vBoolean.from_ical(vBoolean(x).ical())
    True
    >>> vBoolean.from_ical('true')
    True
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def ical(self):
        if self:
            return 'TRUE'
        return 'FALSE'

    bool_map = CaselessDict(true=True, false=False)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vBoolean.bool_map[ical]
        except:
            raise ValueError, "Expected 'TRUE' or 'FALSE'. Got %s" % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vCalAddress(str):
    """
    This just returns an unquoted string
    >>> a = vCalAddress('MAILTO:maxm@mxm.dk')
    >>> a.params['cn'] = 'Max M'
    >>> a.ical()
    'MAILTO:maxm@mxm.dk'
    >>> str(a)
    'MAILTO:maxm@mxm.dk'
    >>> a.params
    Parameters({'CN': 'Max M'})
    >>> vCalAddress.from_ical('MAILTO:maxm@mxm.dk')
    'MAILTO:maxm@mxm.dk'
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def __repr__(self):
        return u"vCalAddress(%s)" % str.__repr__(self)

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected vCalAddress, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str.__str__(self)

####################################################
# handy tzinfo classes you can use.

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET


class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


class Utc(tzinfo):
    """UTC tzinfo subclass"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO
UTC = Utc()

class LocalTimezone(tzinfo):
    """
    Timezone of the machine where the code is running
    """

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

####################################################



class vDatetime:
    """
    Render and generates iCalendar datetime format.

    Important: if tzinfo is defined it renders itself as "date with utc time"
    Meaning that it has a 'Z' appended, and is in absolute time.

    >>> d = datetime(2001, 1,1, 12, 30, 0)

    >>> dt = vDatetime(d)
    >>> dt.ical()
    '20010101T123000'

    >>> vDatetime.from_ical('20000101T120000')
    datetime.datetime(2000, 1, 1, 12, 0)

    >>> dutc = datetime(2001, 1,1, 12, 30, 0, tzinfo=UTC)
    >>> vDatetime(dutc).ical()
    '20010101T123000Z'

    >>> vDatetime.from_ical('20010101T000000')
    datetime.datetime(2001, 1, 1, 0, 0)

    >>> vDatetime.from_ical('20010101T000000A')
    Traceback (most recent call last):
      ...
    ValueError: Wrong datetime format: 20010101T000000A

    >>> utc = vDatetime.from_ical('20010101T000000Z')
    >>> vDatetime(utc).ical()
    '20010101T000000Z'
    """

    def __init__(self, dt):
        self.dt = dt
        self.params = Parameters()

    def ical(self):
        if self.dt.tzinfo:
            offset = self.dt.tzinfo.utcoffset(datetime.now())
            utc_time = self.dt - self.dt.tzinfo.utcoffset(datetime.now())
            return utc_time.strftime("%Y%m%dT%H%M%SZ")
        return self.dt.strftime("%Y%m%dT%H%M%S")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, ((
                ical[:4],       # year
                ical[4:6],      # month
                ical[6:8],      # day
                ical[9:11],     # hour
                ical[11:13],    # minute
                ical[13:15],    # second
                )))
            if not ical[15:]:
                return datetime(*timetuple)
            elif ical[15:16] == 'Z':
                timetuple += [0, UTC]
                return datetime(*timetuple)
            else:
                raise ValueError, ical
        except:
            raise ValueError, 'Wrong datetime format: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vDate:
    """
    Render and generates iCalendar date format.
    >>> d = date(2001, 1,1)
    >>> vDate(d).ical()
    '20010101'

    >>> vDate.from_ical('20010102')
    datetime.date(2001, 1, 2)

    >>> vDate('d').ical()
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a date instance
    """

    def __init__(self, dt):
        if not isinstance(dt, date):
            raise ValueError('Value MUST be a date instance')
        self.dt = dt
        self.params = Parameters(dict(value='DATE'))

    def ical(self):
        return self.dt.strftime("%Y%m%d")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, ((
                ical[:4],     # year
                ical[4:6],    # month
                ical[6:8],    # day
                )))
            return date(*timetuple)
        except:
            raise ValueError, 'Wrong date format %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vDuration:
    """
    Subclass of timedelta that renders itself in the iCalendar DURATION format.

    >>> vDuration(timedelta(11)).ical()
    'P11D'
    >>> vDuration(timedelta(-14)).ical()
    '-P14D'
    >>> vDuration(timedelta(1, 7384)).ical()
    'P1DT2H3M4S'
    >>> vDuration(timedelta(1, 7380)).ical()
    'P1DT2H3M'
    >>> vDuration(timedelta(1, 7200)).ical()
    'P1DT2H'
    >>> vDuration(timedelta(0, 7200)).ical()
    'PT2H'
    >>> vDuration(timedelta(0, 7384)).ical()
    'PT2H3M4S'
    >>> vDuration(timedelta(0, 184)).ical()
    'PT3M4S'
    >>> vDuration(timedelta(0, 22)).ical()
    'PT22S'
    >>> vDuration(timedelta(0, 3622)).ical()
    'PT1H0M22S'
    
    >>> vDuration(timedelta(days=1, hours=5)).ical()
    'P1DT5H'
    >>> vDuration(timedelta(hours=-5)).ical()
    '-PT5H'
    >>> vDuration(timedelta(days=-1, hours=-5)).ical()
    '-P1DT5H'

    How does the parsing work?
    >>> vDuration.from_ical('PT1H0M22S')
    datetime.timedelta(0, 3622)

    >>> vDuration.from_ical('kox')
    Traceback (most recent call last):
        ...
    ValueError: Invalid iCalendar duration: kox

    >>> vDuration.from_ical('-P14D')
    datetime.timedelta(-14)

    >>> vDuration(11)
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a timedelta instance
    """

    def __init__(self, td):
        if not isinstance(td, timedelta):
            raise ValueError('Value MUST be a timedelta instance')
        self.td = td
        self.params = Parameters()

    def ical(self):
        sign = ""
        if self.td.days < 0:
            sign = "-"
            self.td = -self.td
        timepart = ""
        if self.td.seconds:
            timepart = "T"
            hours = self.td.seconds // 3600
            minutes = self.td.seconds % 3600 // 60
            seconds = self.td.seconds % 60
            if hours:
                timepart += "%dH" % hours
            if minutes or (hours and seconds):
                timepart += "%dM" % minutes
            if seconds:
                timepart += "%dS" % seconds
        if self.td.days == 0 and timepart:
            return "%sP%s" % (sign, timepart)
        else:
            return "%sP%dD%s" % (sign, abs(self.td.days), timepart)

    def from_ical(ical):
        """
        Parses the data format from ical text format.
        """
        try:
            match = DURATION_REGEX.match(ical)
            sign, weeks, days, hours, minutes, seconds = match.groups()
            if weeks:
                value = timedelta(weeks=int(weeks))
            else:
                value = timedelta(days=int(days or 0),
                                  hours=int(hours or 0),
                                  minutes=int(minutes or 0),
                                  seconds=int(seconds or 0))
            if sign == '-':
                value = -value
            return value
        except:
            raise ValueError('Invalid iCalendar duration: %s' % ical)
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vFloat(float):
    """
    Just a float.
    >>> f = vFloat(1.0)
    >>> f.ical()
    '1.0'
    >>> vFloat.from_ical('42')
    42.0
    >>> vFloat(42).ical()
    '42.0'
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return float(ical)
        except:
            raise ValueError, 'Expected float value, got: %s' % ical
    from_ical = staticmethod(from_ical)



class vInt(int):
    """
    Just an int.
    >>> f = vInt(42)
    >>> f.ical()
    '42'
    >>> vInt.from_ical('13')
    13
    >>> vInt.from_ical('1s3')
    Traceback (most recent call last):
        ...
    ValueError: Expected int, got: 1s3
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return int(ical)
        except:
            raise ValueError, 'Expected int, got: %s' % ical
    from_ical = staticmethod(from_ical)



class vDDDTypes:
    """
    A combined Datetime, Date or Duration parser/generator. Their format cannot
    be confused, and often values can be of either types. So this is practical.

    >>> d = vDDDTypes.from_ical('20010101T123000')
    >>> type(d)
    <type 'datetime.datetime'>

    >>> repr(vDDDTypes.from_ical('20010101T123000Z'))[:65]
    'datetime.datetime(2001, 1, 1, 12, 30, tzinfo=<icalendar.prop.Utc '

    >>> d = vDDDTypes.from_ical('20010101')
    >>> type(d)
    <type 'datetime.date'>

    >>> vDDDTypes.from_ical('P31D')
    datetime.timedelta(31)

    >>> vDDDTypes.from_ical('-P31D')
    datetime.timedelta(-31)

    Bad input
    >>> vDDDTypes(42)
    Traceback (most recent call last):
        ...
    ValueError: You must use datetime, date or timedelta
    """

    def __init__(self, dt):
        "Returns vDate from"
        wrong_type_used = 1
        for typ in (datetime, date, timedelta):
            if isinstance(dt, typ):
                wrong_type_used = 0
        if wrong_type_used:
            raise ValueError ('You must use datetime, date or timedelta')
        if isinstance(dt, date):
            self.params = Parameters(dict(value='DATE'))

        self.dt = dt

    def ical(self):
        dt = self.dt
        if isinstance(dt, datetime):
            return vDatetime(dt).ical()
        elif isinstance(dt, date):
            return vDate(dt).ical()
        elif isinstance(dt, timedelta):
            return vDuration(dt).ical()
        else:
            raise ValueEror ('Unknown date type')

    def from_ical(ical):
        "Parses the data format from ical text format"
        u = ical.upper()
        if u.startswith('-P') or u.startswith('P'):
            return vDuration.from_ical(ical)
        try:
            return vDatetime.from_ical(ical)
        except:
            return vDate.from_ical(ical)
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()


class vDDDLists:
    """
    A list of vDDDTypes values.
    
    >>> dt_list = vDDDLists.from_ical('19960402T010000Z')
    >>> type(dt_list)
    <type 'list'>
    
    >>> len(dt_list)
    1
    
    >>> type(dt_list[0])
    <type 'datetime.datetime'>
        
    >>> str(dt_list[0])
    '1996-04-02 01:00:00+00:00'
    
    >>> dt_list = vDDDLists.from_ical('19960402T010000Z,19960403T010000Z,19960404T010000Z')
    >>> len(dt_list)
    3
        
    >>> str(dt_list[0])
    '1996-04-02 01:00:00+00:00'
    >>> str(dt_list[2])    
    '1996-04-04 01:00:00+00:00'
    
    >>> dt_list = vDDDLists('19960402T010000Z')
    Traceback (most recent call last):
        ...
    ValueError: Value MUST be a list (of date instances)
    
    >>> dt_list = vDDDLists([])
    >>> str(dt_list)
    ''
    
    >>> dt_list = vDDDLists([datetime(2000,1,1)])
    >>> str(dt_list)
    '20000101T000000'
        
    >>> dt_list = vDDDLists([datetime(2000,1,1), datetime(2000,11,11)])
    >>> str(dt_list)
    '20000101T000000,20001111T000000'
    """
    
    def __init__(self, dt_list):
        if not isinstance(dt_list, list):
            raise ValueError('Value MUST be a list (of date instances)')        
        vDDD = []
        for dt in dt_list:
            vDDD.append(vDDDTypes(dt))
        self.dts = vDDD
    
    def ical(self):
        '''
        Generates the text string in the iCalendar format.
        '''
        dts_ical = [dt.ical() for dt in self.dts]
        return ",".join(dts_ical)
    
    def from_ical(ical):
        '''
        Parses the list of data formats from ical text format.
        @param ical: ical text format
        '''
        out = []
        ical_dates = ical.split(",")
        for ical_dt in ical_dates:
            out.append(vDDDTypes.from_ical(ical_dt))
        return out
    from_ical = staticmethod(from_ical)
    
    def __str__(self):
        return self.ical()
        

class vPeriod:
    """
    A precise period of time.
    One day in exact datetimes
    >>> per = (datetime(2000,1,1), datetime(2000,1,2))
    >>> p = vPeriod(per)
    >>> p.ical()
    '20000101T000000/20000102T000000'

    >>> per = (datetime(2000,1,1), timedelta(days=31))
    >>> p = vPeriod(per)
    >>> p.ical()
    '20000101T000000/P31D'

    Roundtrip
    >>> p = vPeriod.from_ical('20000101T000000/20000102T000000')
    >>> p
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 2, 0, 0))
    >>> vPeriod(p).ical()
    '20000101T000000/20000102T000000'

    >>> vPeriod.from_ical('20000101T000000/P31D')
    (datetime.datetime(2000, 1, 1, 0, 0), datetime.timedelta(31))

    Roundtrip with absolute time
    >>> p = vPeriod.from_ical('20000101T000000Z/20000102T000000Z')
    >>> vPeriod(p).ical()
    '20000101T000000Z/20000102T000000Z'

    And an error
    >>> vPeriod.from_ical('20000101T000000/Psd31D')
    Traceback (most recent call last):
        ...
    ValueError: Expected period format, got: 20000101T000000/Psd31D

    Utc datetime
    >>> da_tz = FixedOffset(+1.0, 'da_DK')
    >>> start = datetime(2000,1,1, tzinfo=da_tz)
    >>> end = datetime(2000,1,2, tzinfo=da_tz)
    >>> per = (start, end)
    >>> vPeriod(per).ical()
    '19991231T235900Z/20000101T235900Z'

    >>> p = vPeriod((datetime(2000,1,1, tzinfo=da_tz), timedelta(days=31)))
    >>> p.ical()
    '19991231T235900Z/P31D'
    """

    def __init__(self, per):
        start, end_or_duration = per
        if not (isinstance(start, datetime) or isinstance(start, date)):
            raise ValueError('Start value MUST be a datetime or date instance')
        if not (isinstance(end_or_duration, datetime) or
                isinstance(end_or_duration, date) or
                isinstance(end_or_duration, timedelta)):
            raise ValueError('end_or_duration MUST be a datetime, date or timedelta instance')
        self.start = start
        self.end_or_duration = end_or_duration
        self.by_duration = 0
        if isinstance(end_or_duration, timedelta):
            self.by_duration = 1
            self.duration = end_or_duration
            self.end = self.start + self.duration
        else:
            self.end = end_or_duration
            self.duration = self.end - self.start
        if self.start > self.end:
            raise ValueError("Start time is greater than end time")
        self.params = Parameters()

    def __cmp__(self, other):
        if not isinstance(other, vPeriod):
            raise NotImplementedError(
                'Cannot compare vPeriod with %s' % repr(other))
        return cmp((self.start, self.end), (other.start, other.end))

    def overlaps(self, other):
        if self.start > other.start:
            return other.overlaps(self)
        if self.start <= other.start < self.end:
            return True
        return False

    def ical(self):
        if self.by_duration:
            return '%s/%s' % (vDatetime(self.start).ical(), vDuration(self.duration).ical())
        return '%s/%s' % (vDatetime(self.start).ical(), vDatetime(self.end).ical())

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            start, end_or_duration = ical.split('/')
            start = vDDDTypes.from_ical(start)
            end_or_duration = vDDDTypes.from_ical(end_or_duration)
            return (start, end_or_duration)
        except:
            raise ValueError, 'Expected period format, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()

    def __repr__(self):
        if self.by_duration:
            p = (self.start, self.duration)
        else:
            p = (self.start, self.end)
        return 'vPeriod(%s)' % repr(p)

class vWeekday(str):
    """
    This returns an unquoted weekday abbrevation
    >>> a = vWeekday('mo')
    >>> a.ical()
    'MO'

    >>> a = vWeekday('erwer')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: ERWER

    >>> vWeekday.from_ical('mo')
    'MO'

    >>> vWeekday.from_ical('+3mo')
    '+3MO'

    >>> vWeekday.from_ical('Saturday')
    Traceback (most recent call last):
        ...
    ValueError: Expected weekday abbrevation, got: Saturday

    >>> a = vWeekday('+mo')
    >>> a.ical()
    '+MO'

    >>> a = vWeekday('+3mo')
    >>> a.ical()
    '+3MO'

    >>> a = vWeekday('-tu')
    >>> a.ical()
    '-TU'
    """

    week_days = CaselessDict({"SU":0, "MO":1, "TU":2, "WE":3,
                              "TH":4, "FR":5, "SA":6})

    def __init__(self, *args, **kwargs):
        match = WEEKDAY_RULE.match(self)
        if match is None:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % self
        match = match.groupdict()
        sign = match['signal']
        weekday = match['weekday']
        relative = match['relative']
        if not weekday in vWeekday.week_days or sign not in '+-':
            raise ValueError, 'Expected weekday abbrevation, got: %s' % self
        self.relative = relative and int(relative) or None
        self.params = Parameters()

    def ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vWeekday(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vFrequency(str):
    """
    A simple class that catches illegal values.
    >>> f = vFrequency('bad test')
    Traceback (most recent call last):
        ...
    ValueError: Expected frequency, got: BAD TEST
    >>> vFrequency('daily').ical()
    'DAILY'
    >>> vFrequency('daily').from_ical('MONTHLY')
    'MONTHLY'
    """

    frequencies = CaselessDict({
        "SECONDLY":"SECONDLY",
        "MINUTELY":"MINUTELY",
        "HOURLY":"HOURLY",
        "DAILY":"DAILY",
        "WEEKLY":"WEEKLY",
        "MONTHLY":"MONTHLY",
        "YEARLY":"YEARLY",
    })

    def __init__(self, *args, **kwargs):
        if not self in vFrequency.frequencies:
            raise ValueError, 'Expected frequency, got: %s' % self
        self.params = Parameters()

    def ical(self):
        return self.upper()

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return vFrequency(ical.upper())
        except:
            raise ValueError, 'Expected weekday abbrevation, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vRecur(CaselessDict):
    """
    Let's see how close we can get to one from the rfc:
    FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30

    >>> r = dict(freq='yearly', interval=2)
    >>> r['bymonth'] = 1
    >>> r['byday'] = 'su'
    >>> r['byhour'] = [8,9]
    >>> r['byminute'] = 30
    >>> r = vRecur(r)
    >>> r.ical()
    'BYHOUR=8,9;BYDAY=SU;BYMINUTE=30;BYMONTH=1;FREQ=YEARLY;INTERVAL=2'

    >>> r = vRecur(FREQ='yearly', INTERVAL=2)
    >>> r['BYMONTH'] = 1
    >>> r['BYDAY'] = 'su'
    >>> r['BYHOUR'] = [8,9]
    >>> r['BYMINUTE'] = 30
    >>> r.ical()
    'BYDAY=SU;BYMINUTE=30;BYMONTH=1;INTERVAL=2;FREQ=YEARLY;BYHOUR=8,9'

    >>> r = vRecur(freq='DAILY', count=10)
    >>> r['bysecond'] = [0, 15, 30, 45]
    >>> r.ical()
    'COUNT=10;FREQ=DAILY;BYSECOND=0,15,30,45'

    >>> r = vRecur(freq='DAILY', until=datetime(2005,1,1,12,0,0))
    >>> r.ical()
    'FREQ=DAILY;UNTIL=20050101T120000'

    How do we fare with regards to parsing?
    >>> r = vRecur.from_ical('FREQ=DAILY;INTERVAL=2;COUNT=10')
    >>> r
    {'COUNT': [10], 'FREQ': ['DAILY'], 'INTERVAL': [2]}
    >>> vRecur(r).ical()
    'COUNT=10;FREQ=DAILY;INTERVAL=2'

    >>> r = vRecur.from_ical('FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=-SU;BYHOUR=8,9;BYMINUTE=30')
    >>> r
    {'BYHOUR': [8, 9], 'BYDAY': ['-SU'], 'BYMINUTE': [30], 'BYMONTH': [1], 'FREQ': ['YEARLY'], 'INTERVAL': [2]}
    >>> vRecur(r).ical()
    'BYDAY=-SU;BYMINUTE=30;INTERVAL=2;BYMONTH=1;FREQ=YEARLY;BYHOUR=8,9'

    Some examples from the spec

    >>> r = vRecur.from_ical('FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1')
    >>> vRecur(r).ical()
    'BYSETPOS=-1;FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR'

    >>> r = vRecur.from_ical('FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30')
    >>> vRecur(r).ical()
    'BYDAY=SU;BYMINUTE=30;INTERVAL=2;BYMONTH=1;FREQ=YEARLY;BYHOUR=8,9'

    and some errors
    >>> r = vRecur.from_ical('BYDAY=12')
    Traceback (most recent call last):
        ...
    ValueError: Error in recurrence rule: BYDAY=12

    """

    frequencies = ["SECONDLY",  "MINUTELY", "HOURLY", "DAILY", "WEEKLY",
                   "MONTHLY", "YEARLY"]

    types = CaselessDict({
        'COUNT':vInt,
        'INTERVAL':vInt,
        'BYSECOND':vInt,
        'BYMINUTE':vInt,
        'BYHOUR':vInt,
        'BYMONTHDAY':vInt,
        'BYYEARDAY':vInt,
        'BYMONTH':vInt,
        'UNTIL':vDDDTypes,
        'BYSETPOS':vInt,
        'WKST':vWeekday,
        'BYDAY':vWeekday,
        'FREQ':vFrequency
    })

    def __init__(self, *args, **kwargs):
        CaselessDict.__init__(self, *args, **kwargs)
        self.params = Parameters()

    def ical(self):
        # SequenceTypes
        result = []
        for key, vals in self.items():
            typ = self.types[key]
            if not type(vals) in SequenceTypes:
                vals = [vals]
            vals = ','.join([typ(val).ical() for val in vals])
            result.append('%s=%s' % (key, vals))
        return ';'.join(result)

    def parse_type(key, values):
        # integers
        parser = vRecur.types.get(key, vText)
        return [parser.from_ical(v) for v in values.split(',')]
    parse_type = staticmethod(parse_type)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            recur = vRecur()
            for pairs in ical.split(';'):
                key, vals = pairs.split('=')
                recur[key] = vRecur.parse_type(key, vals)
            return dict(recur)
        except:
            raise ValueError, 'Error in recurrence rule: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vText(unicode):
    """
    Simple text
    >>> t = vText(u'Simple text')
    >>> t.ical()
    'Simple text'

    Escaped text
    >>> t = vText('Text ; with escaped, chars')
    >>> t.ical()
    'Text \\\\; with escaped\\\\, chars'

    Escaped newlines
    >>> vText('Text with escaped\N chars').ical()
    'Text with escaped\\\\n chars'

    If you pass a unicode object, it will be utf-8 encoded. As this is the
    (only) standard that RFC 2445 support.

    >>> t = vText(u'international chars æøå ÆØÅ ü')
    >>> t.ical()
    'international chars \\xc3\\xa6\\xc3\\xb8\\xc3\\xa5 \\xc3\\x86\\xc3\\x98\\xc3\\x85 \\xc3\\xbc'

    Unicode is converted to utf-8
    >>> t = vText(u'international æ ø å')
    >>> str(t)
    'international \\xc3\\xa6 \\xc3\\xb8 \\xc3\\xa5'

    and parsing?
    >>> vText.from_ical('Text \\; with escaped\\, chars')
    u'Text ; with escaped, chars'

    >>> print vText.from_ical('A string with\\; some\\\\ characters in\\Nit')
    A string with; some\\ characters in
    it
    """

    encoding = 'utf-8'

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def escape(self):
        """
        Format value according to iCalendar TEXT escaping rules.
        """
        return (self.replace('\N', '\n')
                    .replace('\\', '\\\\')
                    .replace(';', r'\;')
                    .replace(',', r'\,')
                    .replace('\r\n', r'\n')
                    .replace('\n', r'\n')
                )

    def __repr__(self):
        return u"vText(%s)" % unicode.__repr__(self)

    def ical(self):
        return self.escape().encode(self.encoding)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            ical = (ical.replace(r'\N', r'\n')
                        .replace(r'\r\n', '\n')
                        .replace(r'\n', '\n')
                        .replace(r'\,', ',')
                        .replace(r'\;', ';')
                        .replace('\\\\', '\\'))
            return ical.decode(vText.encoding)
        except:
            raise ValueError, 'Expected ical text, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vTime(time):
    """
    A subclass of datetime, that renders itself in the iCalendar time
    format.
    >>> dt = vTime(12, 30, 0)
    >>> dt.ical()
    '123000'

    >>> vTime.from_ical('123000')
    datetime.time(12, 30)

    We should also fail, right?
    >>> vTime.from_ical('263000')
    Traceback (most recent call last):
        ...
    ValueError: Expected time, got: 263000
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def ical(self):
        return self.strftime("%H%M%S")

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            timetuple = map(int, (ical[:2],ical[2:4],ical[4:6]))
            return time(*timetuple)
        except:
            raise ValueError, 'Expected time, got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vUri(str):
    """
    Uniform resource identifier is basically just an unquoted string.
    >>> u = vUri('http://www.example.com/')
    >>> u.ical()
    'http://www.example.com/'
    >>> vUri.from_ical('http://www.example.com/') # doh!
    'http://www.example.com/'
    """

    def __init__(self, *args, **kwargs):
        self.params = Parameters()

    def ical(self):
        return str(self)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            return str(ical)
        except:
            raise ValueError, 'Expected , got: %s' % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str.__str__(self)



class vGeo:
    """
    A special type that is only indirectly defined in the rfc.

    >>> g = vGeo((1.2, 3.0))
    >>> g.ical()
    '1.2;3.0'

    >>> g = vGeo.from_ical('37.386013;-122.082932')
    >>> g
    (37.386012999999998, -122.082932)

    >>> vGeo(g).ical()
    '37.386013;-122.082932'

    >>> vGeo('g').ical()
    Traceback (most recent call last):
        ...
    ValueError: Input must be (float, float) for latitude and longitude
    """

    def __init__(self, geo):
        try:
            latitude, longitude = geo
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            raise ValueError('Input must be (float, float) for latitude and longitude')
        self.latitude = latitude
        self.longitude = longitude
        self.params = Parameters()

    def ical(self):
        return '%s;%s' % (self.latitude, self.longitude)

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            latitude, longitude = ical.split(';')
            return (float(latitude), float(longitude))
        except:
            raise ValueError, "Expected 'float;float' , got: %s" % ical
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vUTCOffset:
    """
    Renders itself as a utc offset

    >>> u = vUTCOffset(timedelta(hours=2))
    >>> u.ical()
    '+0200'

    >>> u = vUTCOffset(timedelta(hours=-5))
    >>> u.ical()
    '-0500'

    >>> u = vUTCOffset(timedelta())
    >>> u.ical()
    '0000'

    >>> u = vUTCOffset(timedelta(minutes=-30))
    >>> u.ical()
    '-0030'

    >>> u = vUTCOffset(timedelta(hours=2, minutes=-30))
    >>> u.ical()
    '+0130'

    >>> u = vUTCOffset(timedelta(hours=1, minutes=30))
    >>> u.ical()
    '+0130'

    Parsing

    >>> vUTCOffset.from_ical('0000')
    datetime.timedelta(0)

    >>> vUTCOffset.from_ical('-0030')
    datetime.timedelta(-1, 84600)

    >>> vUTCOffset.from_ical('+0200')
    datetime.timedelta(0, 7200)

    >>> o = vUTCOffset.from_ical('+0230')
    >>> vUTCOffset(o).ical()
    '+0230'

    And a few failures
    >>> vUTCOffset.from_ical('+323k')
    Traceback (most recent call last):
        ...
    ValueError: Expected utc offset, got: +323k

    >>> vUTCOffset.from_ical('+2400')
    Traceback (most recent call last):
        ...
    ValueError: Offset must be less than 24 hours, was +2400
    """

    def __init__(self, td):
        if not isinstance(td, timedelta):
            raise ValueError('Offset value MUST be a timedelta instance')
        self.td = td
        self.params = Parameters()

    def ical(self):
        td = self.td
        day_in_minutes = (td.days * 24 * 60)
        seconds_in_minutes = td.seconds // 60
        total_minutes = day_in_minutes + seconds_in_minutes
        if total_minutes == 0:
            sign = '%s'
        elif total_minutes < 0:
            sign = '-%s'
        else:
            sign = '+%s'
        hours = abs(total_minutes) // 60
        minutes = total_minutes % 60
        duration = '%02i%02i' % (hours, minutes)
        return sign % duration

    def from_ical(ical):
        "Parses the data format from ical text format"
        try:
            sign, hours, minutes = (ical[-5:-4], int(ical[-4:-2]), int(ical[-2:]))
            offset = timedelta(hours=hours, minutes=minutes)
        except:
            raise ValueError, 'Expected utc offset, got: %s' % ical
        if offset >= timedelta(hours=24):
            raise ValueError, 'Offset must be less than 24 hours, was %s' % ical
        if sign == '-':
            return -offset
        return offset
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return self.ical()



class vInline(str):
    """
    This is an especially dumb class that just holds raw unparsed text and has
    parameters. Conversion of inline values are handled by the Component class,
    so no further processing is needed.

    >>> vInline('Some text')
    'Some text'

    >>> vInline.from_ical('Some text')
    'Some text'

    >>> t2 = vInline('other text')
    >>> t2.params['cn'] = 'Test Osterone'
    >>> t2.params
    Parameters({'CN': 'Test Osterone'})

    """

    def __init__(self,obj):
        self.obj = obj
        self.params = Parameters()

    def ical(self):
        return str(self)

    def from_ical(ical):
        return str(ical)
    from_ical = staticmethod(from_ical)

    def __str__(self):
        return str(self.obj)


class TypesFactory(CaselessDict):
    """
    All Value types defined in rfc 2445 are registered in this factory class. To
    get a type you can use it like this.
    >>> factory = TypesFactory()
    >>> datetime_parser = factory['date-time']
    >>> dt = datetime_parser(datetime(2001, 1, 1))
    >>> dt.ical()
    '20010101T000000'

    A typical use is when the parser tries to find a content type and use text
    as the default
    >>> value = '20050101T123000'
    >>> value_type = 'date-time'
    >>> typ = factory.get(value_type, 'text')
    >>> typ.from_ical(value)
    datetime.datetime(2005, 1, 1, 12, 30)

    It can also be used to directly encode property and parameter values
    >>> comment = factory.ical('comment', u'by Rasmussen, Max Møller')
    >>> str(comment)
    'by Rasmussen\\\\, Max M\\xc3\\xb8ller'
    >>> factory.ical('priority', 1)
    '1'
    >>> factory.ical('cn', u'Rasmussen, Max Møller')
    'Rasmussen\\\\, Max M\\xc3\\xb8ller'

    >>> factory.from_ical('cn', 'Rasmussen\\\\, Max M\\xc3\\xb8ller')
    u'Rasmussen, Max M\\xf8ller'

    The value and parameter names don't overlap. So one factory is enough for
    both kinds.
    """

    def __init__(self, *args, **kwargs):
        "Set keys to upper for initial dict"
        CaselessDict.__init__(self, *args, **kwargs)
        self['binary'] = vBinary
        self['boolean'] = vBoolean
        self['cal-address'] = vCalAddress
        self['date'] = vDDDTypes
        self['date-time'] = vDDDTypes
        self['duration'] = vDDDTypes
        self['float'] = vFloat
        self['integer'] = vInt
        self['period'] = vPeriod
        self['recur'] = vRecur
        self['text'] = vText
        self['time'] = vTime
        self['uri'] = vUri
        self['utc-offset'] = vUTCOffset
        self['geo'] = vGeo
        self['inline'] = vInline
        self['date-time-list'] = vDDDLists


    #################################################
    # Property types

    # These are the default types
    types_map = CaselessDict({
        ####################################
        # Property valye types
        # Calendar Properties
        'calscale' : 'text',
        'method' : 'text',
        'prodid' : 'text',
        'version' : 'text',
        # Descriptive Component Properties
        'attach' : 'uri',
        'categories' : 'text',
        'class' : 'text',
        'comment' : 'text',
        'description' : 'text',
        'geo' : 'geo',
        'location' : 'text',
        'percent-complete' : 'integer',
        'priority' : 'integer',
        'resources' : 'text',
        'status' : 'text',
        'summary' : 'text',
        # Date and Time Component Properties
        'completed' : 'date-time',
        'dtend' : 'date-time',
        'due' : 'date-time',
        'dtstart' : 'date-time',
        'duration' : 'duration',
        'freebusy' : 'period',
        'transp' : 'text',
        # Time Zone Component Properties
        'tzid' : 'text',
        'tzname' : 'text',
        'tzoffsetfrom' : 'utc-offset',
        'tzoffsetto' : 'utc-offset',
        'tzurl' : 'uri',
        # Relationship Component Properties
        'attendee' : 'cal-address',
        'contact' : 'text',
        'organizer' : 'cal-address',
        'recurrence-id' : 'date-time',
        'related-to' : 'text',
        'url' : 'uri',
        'uid' : 'text',
        # Recurrence Component Properties
        'exdate' : 'date-time-list',
        'exrule' : 'recur',
        'rdate' : 'date-time-list',
        'rrule' : 'recur',
        # Alarm Component Properties
        'action' : 'text',
        'repeat' : 'integer',
        'trigger' : 'duration',
        # Change Management Component Properties
        'created' : 'date-time',
        'dtstamp' : 'date-time',
        'last-modified' : 'date-time',
        'sequence' : 'integer',
        # Miscellaneous Component Properties
        'request-status' : 'text',
        ####################################
        # parameter types (luckilly there is no name overlap)
        'altrep' : 'uri',
        'cn' : 'text',
        'cutype' : 'text',
        'delegated-from' : 'cal-address',
        'delegated-to' : 'cal-address',
        'dir' : 'uri',
        'encoding' : 'text',
        'fmttype' : 'text',
        'fbtype' : 'text',
        'language' : 'text',
        'member' : 'cal-address',
        'partstat' : 'text',
        'range' : 'text',
        'related' : 'text',
        'reltype' : 'text',
        'role' : 'text',
        'rsvp' : 'boolean',
        'sent-by' : 'cal-address',
        'tzid' : 'text',
        'value' : 'text',
    })


    def for_property(self, name):
        "Returns a the default type for a property or parameter"
        return self[self.types_map.get(name, 'text')]

    def ical(self, name, value):
        """
        Encodes a named value from a primitive python type to an
        icalendar encoded string.
        """
        type_class = self.for_property(name)
        return type_class(value).ical()

    def from_ical(self, name, value):
        """
        Decodes a named property or parameter value from an icalendar encoded
        string to a primitive python type.
        """
        type_class = self.for_property(name)
        decoded = type_class.from_ical(str(value))
        return decoded

########NEW FILE########
__FILENAME__ = tools
from string import ascii_letters, digits
import random

"""
This module contains non-essential tools for iCalendar. Pretty thin so far eh?

"""

class UIDGenerator:

    """
    If you are too lazy to create real uid's. Notice, this doctest is disabled!

    Automatic semi-random uid
    >> g = UIDGenerator()
    >> uid = g.uid()
    >> uid.ical()
    '20050109T153222-7ekDDHKcw46QlwZK@example.com'

    You Should at least insert your own hostname to be more complient
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG')
    >> uid.ical()
    '20050109T153549-NbUItOPDjQj8Ux6q@Example.ORG'

    You can also insert a path or similar
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG', '/path/to/content')
    >> uid.ical()
    '20050109T153415-/path/to/content@Example.ORG'
    """

    chars = list(ascii_letters + digits)

    def rnd_string(self, length=16):
        "Generates a string with random characters of length"
        return ''.join([random.choice(self.chars) for i in range(length)])

    def uid(self, host_name='example.com', unique=''):
        """
        Generates a unique id consisting of:
        datetime-uniquevalue@host. Like:
        20050105T225746Z-HKtJMqUgdO0jDUwm@example.com
        """
        from PropertyValues import vText, vDatetime
        unique = unique or self.rnd_string()
        return vText('%s-%s@%s' % (vDatetime.today().ical(), unique, host_name))


if __name__ == "__main__":
    import os.path, doctest, tools
    # import and test this file
    doctest.testmod(tools)

########NEW FILE########
__FILENAME__ = util
from string import ascii_letters, digits
import random

"""
This module contains non-essential tools for iCalendar. Pretty thin so far eh?

"""

class UIDGenerator:

    """
    If you are too lazy to create real uids.

    NOTE: this doctest is disabled
    (only two > instead of three)

    Automatic semi-random uid
    >> g = UIDGenerator()
    >> uid = g.uid()
    >> uid.ical()
    '20050109T153222-7ekDDHKcw46QlwZK@example.com'

    You should at least insert your own hostname to be more compliant
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG')
    >> uid.ical()
    '20050109T153549-NbUItOPDjQj8Ux6q@Example.ORG'

    You can also insert a path or similar
    >> g = UIDGenerator()
    >> uid = g.uid('Example.ORG', '/path/to/content')
    >> uid.ical()
    '20050109T153415-/path/to/content@Example.ORG'
    """

    chars = list(ascii_letters + digits)

    def rnd_string(self, length=16):
        "Generates a string with random characters of length"
        return ''.join([random.choice(self.chars) for i in range(length)])

    def uid(self, host_name='example.com', unique=''):
        """
        Generates a unique id consisting of:
        datetime-uniquevalue@host. Like:
        20050105T225746Z-HKtJMqUgdO0jDUwm@example.com
        """
        from PropertyValues import vText, vDatetime
        unique = unique or self.rnd_string()
        return vText('%s-%s@%s' % (vDatetime.today().ical(), unique, host_name))

########NEW FILE########
__FILENAME__ = icalformat
#!/usr/bin/env python
# encoding: utf-8
"""
icalformat.py

Created by Juha Autero on 2010-04-22.
Copyright (c) 2010 Juha Autero. All rights reserved.

"""

import datetime,icalendar,uuid
import unittest


class ical_generator:
    starttime=datetime.time(18,0,0)
    endtime=datetime.time(23,59,59)
    def __init__(self,upto,event_name):
        self.source=None
        self.name=event_name
        self.count=0
        self.enddate=None
        mycal=icalendar.Calendar()
        mycal.add('prodid', '-//Onko mafia//onkomafia.appspot.com//')
        mycal.add('version', '2.0')
        self.mycal=mycal
        try:
            self.enddate=datetime.datetime.strptime(upto,"%d.%m").date()
            self.enddate=self.enddate.replace(year=datetime.date.today().year)
        except Exception, e:
            try:
                self.count=int(upto)
            except Exception, e:
                self.count=10

    def __str__(self):
        return self.mycal.as_string()
    
    def set_mafia_calculator(self,calculator):
        mycal=self.mycal
        count=0
        for date in calculator:
            count+=1
            if self.count>0 and count>self.count:
                break
            if self.enddate and date > self.enddate:
                break
            event = icalendar.Event()
            event.add('summary',self.name)
            event.add('dtstart',date)
            event.add('dtend',date)
            event.add('dtstamp',datetime.date.today())
            event['uid'] = "%s@onkomafia.appspot.org" % (uuid.uuid4())
            mycal.add_component(event)

def datetime_generator(date=None):
    """generator of datetimes for unittest"""
    if not date:
        date=datetime.date.today()
        while True:
            date+=date.resolution
            yield date
        
class ical_generatorTests(unittest.TestCase):
    def set_daycount(self,count):
        self.daycount=count
        self.enddate=datetime.date.today()+self.daycount*datetime.date.resolution        
    def setUp(self):
        self.datetester=datetime_generator()
    def test_upto_date(self):
        self.set_daycount(12)
        self.test_calendar=ical_generator(self.enddate.strftime("%d.%m"),"test event")
        self.run_calendar_test()
    def test_upto_count(self):
        self.set_daycount(14)
        self.test_calendar=ical_generator("14","test event")
        self.run_calendar_test()
    def test_upto_nonsense(self):
        self.set_daycount(10)
        self.test_calendar=ical_generator("foobar","test event")
        self.run_calendar_test()
    def run_calendar_test(self):
        self.test_calendar.set_mafia_calculator(self.datetester)
        parsed_calendar=icalendar.Calendar.from_string(str(self.test_calendar))
        curdate=datetime.date.today()
        count=0
        for component in parsed_calendar.walk():
            if component.name=="VEVENT":
                count+=1
                curdate+=curdate.resolution
                self.check_event(component,curdate)
        self.assertEqual(count,self.daycount)
        self.assertEqual(curdate,self.enddate)
    def check_event(self,component,curdate):
        self.assertEqual(component["SUMMARY"],"test event")
        self.assertEqual(component.decoded('dtstart'),curdate)
        self.assertEqual(component.decoded('dtend'),curdate)
        self.assertEqual(component.decoded('dtstamp'),datetime.date.today())
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = onko-mafia
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero.
#
# Copyright 2009 Juha Autero <jautero@iki.fi>.
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
#

project="Onko Mafia"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright &copy; 2009 Juha Autero &lt;jautero@iki.fi&gt;."
application="onko-mafia"
import logging
import wsgiref.handlers
import os,datetime
import formats
import urlparse
from formatobjects import mafiat

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class OnkoMafia(webapp.RequestHandler):
    def get(self):
        template_values=dict(globals())
        city=self.request.get("kaupunki","helsinki").encode()
        logging.info(repr(city))
        template_values['city']=city
        template_values['netloc']=urlparse.urlparse(self.request.url).netloc
        if str(self.request.headers["User-Agent"]).find("Mac OS X") != -1:
            template_values['icalprotocol']="webcal"
        else:
            template_values['icalprotocol']="http"
        for candidate in mafiat.keys():
            if candidate==city:
                template_values[candidate+"selected"]="selected"
            else:
                template_values[candidate+"selected"]=""
        mymafiacalculator=mafiat[city]()
        format=self.request.get("format","html")        
        if format=="html":
            myformatspec=formats.get_html_format(template_values)
        elif format=="json":
            myformatspec=formats.get_json_format()
        elif format=="badge":
            myformatspec=formats.get_badge_format()
        elif format=="ical":
            self.response.headers['Content-Type']="text/calendar"
            myformatspec=formats.get_ical_format(self.request.get("upto","10"),city+" mafia")
        myformatspec.set_mafia_calculator(mymafiacalculator)
        self.response.out.write(str(myformatspec))

      
def main():
    application = webapp.WSGIApplication([('/', OnkoMafia)],
                                        debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

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
__version__ = "3.0.8"
__copyright__ = "Copyright (c) 2004-2009 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
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
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
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
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
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
        # Special case some findAll* searches
        # findAll*(True)
        elif not limit and name is True and not attrs and not kwargs:
            return [element for element in generator()
                    if isinstance(element, Tag)]

        # findAll*('tag-name')
        elif not limit and isinstance(name, basestring) and not attrs \
                and not kwargs:
            return [element for element in generator()
                    if isinstance(element, Tag) and element.name == name]

        # Build a SoupStrainer
        else:
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
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
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
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        if encoding:
            return self.encode(encoding)
        else:
            return self

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

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
        if attrs is None:
            attrs = []
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

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
        if other is self:
            return True
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
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isinstance(val, basestring):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

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

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
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
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
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

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

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
    def childGenerator(self):
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
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
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
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
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
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
        elif hasattr(portion, '__iter__'): # is a list
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

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
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

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
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

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
                if not hasattr(self.markupMassage, "__iter__"):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()

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
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
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
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
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

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

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
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
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
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

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
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

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

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

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

    def start_meta(self, attrs):
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
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript')

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

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if isinstance(sub, tuple):
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
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
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

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
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
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
__FILENAME__ = config
lottourl="https://www.veikkaus.fi/pelit?op=frontpage&game=lotto&l=f"
########NEW FILE########
__FILENAME__ = fetcher
from lottorivitmodel import VoittoRivi
from google.appengine.api.labs import taskqueue
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from config import lottourl
from lottoparser import LottoPageParser
import datetime
    
class RivitHandler(webapp.RequestHandler):
    def get(self):
        rivi=VoittoRivi.gql("ORDER BY vuosi DESC,kierros DESC").get()
        if rivi:
            tuorein_kierros=rivi.kierros
        else:
            tuorein_kierros=0
        taskqueue.add(url=self.request.path,params={"kierros":tuorein_kierros})
            
    def post(self):
        edellinen_kierros=self.request.get("kierros",None)
        parser=LottoPageParser()
        response=urlfetch.fetch(lottourl)
        if response.status_code == 200:
            parser.feed(response.content)
            kierros=parser.kierros
            year=datetime.date.today().year
            if kierros>5 and datetime.date.today().month==1:
                year-=1
            if edellinen_kierros and kierros != edellinen_kierros:
                rivi=VoittoRivi(kierros=kierros,vuosi=year,numerot=parser.numerot,lisanumerot=parser.lisanumerot)
                rivi.put()
            else:
                self.error(500)
                

########NEW FILE########
__FILENAME__ = lottoparser
# -*- coding: latin-1 -*-
from BeautifulSoup import BeautifulSoup
import re
import unittest
class LottoPageParser:
    def __init__(self):
        self.kierros=0
        self.numerot=[]
        self.lisanumerot=[]
        
    def find_kierros(self,text):
        regexp=re.compile("Kierros (\d+)")
        result=regexp.search(text)
        if result:
            return int(result.group(1))
        else:
            return 0
    def feed(self,content):
        soup=BeautifulSoup(content)
        tulokset=soup.find(text="Uusimmat tulokset")
        self.kierros=self.find_kierros(tulokset.parent.nextSibling.nextSibling.string)
        tulokset=soup.find("table",{"class":"numbers"}).find("tbody").find("tr") 
        for item in tulokset.findAll("td"):
            itemclass=item.get("class")
            try:
                itemnumber=int(item.string)
            except:
                itemnumber=0
            if itemclass==None and itemnumber !=0:
                self.numerot.append(itemnumber)
            if itemclass=="secondary" and itemnumber != 0:
                self.lisanumerot.append(itemnumber)

class LottoPageParserTester(unittest.TestCase):
    def setUp(self):
        self.lottoparser=LottoPageParser()
        
    def test_latest(self):
        self.lottoparser.feed(testdata1)
        self.assertEqual(self.lottoparser.kierros,22)
        self.assertEqual(len(self.lottoparser.numerot),7)
        self.assertEqual(len(self.lottoparser.lisanumerot),3)
        self.assertTrue(self.lottoparser.numerot==[3,5,17,19,26,36,38])
        self.assertTrue(self.lottoparser.lisanumerot==[14,25,27])

if __name__ == '__main__':
    testdata1="""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fi" lang="fi">
    <head>


              <title>Veikkaus - Lotto - Etusivu</title>


          <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
      <link rel="icon" href="/info/media/shared/favicon.ico" type="image/ico" />
      <link rel="stylesheet" type="text/css" href="/css/common.css?v=14" />
            <link rel="stylesheet" type="text/css" href="/css/games.css?v=14" />
          <script type="text/javascript" src="/js/texts_www_fi.js?v=14"></script>

      <script type="text/javascript" src="/js/utils_www.js?v=14"></script>
      <script type="text/javascript" src="/js/xml_www.js?v=14"></script>
      <script type="text/javascript" src="/js/gamefolder_www.js?v=14"></script>
      <script type="text/javascript">
        doBrowserCheck();
      </script>
      <link rel="stylesheet" type="text/css" href="/css/lotto.css?v=14" />
      <link rel="stylesheet" type="text/css" media="print" href="/css/print.css?v=14" />
      <script type="text/javascript" src="/js/utils_goc_www.js?v=14"></script>

      <script type="text/javascript" src="/js/lotto_www.js?v=14"></script>
      <script type="text/javascript">





    var rowPrice = 80 / 100.0;
    var awdExtraRowPrice = 20 / 100.0;
    var jokerPrice = 200 / 100.0;
    var awdEnabled = "true".toLowerCase() == "true" ? true : false; // to get real primitives

    /* Tells if this page is the normal / system / reduced system lotto */
    var baseURL = "/pelit";
    var game = "lotto";
    var sys = "frontpage";

    var MAXVALUE, NUMBEROFROWS, MAXSELECTIONS, systemSize, systemRowCounts, reducedSystemRowCounts;

    // Changes global "config" parameters for game mode
    function selectGameMode(mode) {
        if(game == "lotto") {
    	    if(mode == "system") {
    	        NUMBEROFROWS = 1;
    	        MAXSELECTIONS = 8;
    	        systemSize = 98;
    	    }
    	    else if(mode == "reduced") {
    	        NUMBEROFROWS = 1;
    	        MAXSELECTIONS = 12;
    	        systemSize = 99;
    	    }
    	    else {
    	        NUMBEROFROWS = 12;
    	        MAXSELECTIONS = 7;
        		BLOCK_SIZE = 1;
        		MIN_BLOCKS = 12;
        		MAX_BLOCKS = 20;
    	        systemSize = 7;
    	    }

        // Maps system row length to number of actual rows generated
    		    systemRowCounts = {
    			        8 : 8,
    			        9 : 36,
    			        10 : 120,
    			        11 : 330
    		    };

        reducedSystemRowCounts = {
    		        12 : 60,
    		        13 : 112,
    		        14 : 196,
    		        15 : 237,
    		        16 : 439,
    		        18 : 600
    		    };

    		    MAXVALUE = 39;
    	    }

        if (game == "viking") {
    	    if(mode == "system") {
    	        NUMBEROFROWS = 1;
    	        MAXSELECTIONS = 7;
    	        systemSize = 98;
    	    }
    	    else if(mode == "reduced") {
    	        NUMBEROFROWS = 1;
    	        MAXSELECTIONS = 12;
    	        systemSize = 99;
    	    }
    	    else {
    	        NUMBEROFROWS = 10;
        		BLOCK_SIZE = 1;
        		MIN_BLOCKS = 12;
        		MAX_BLOCKS = 20;
    	        MAXSELECTIONS = 6;
    	        systemSize = 6;
    	    }

    	    systemRowCounts = {
    			        7 : 7,
            			8 : 28,
    			        9 : 84,
    			        10 : 210,
    			        11 : 462
    	    };

    	    reducedSystemRowCounts = {
    	        12 : 41,
    	        13 : 66,
    	        14 : 80,
    	        15 : 120,
    	        16 : 160,
    	        17 : 188,
    	        18 : 236,
    	        19 : 330,
    	        20 : 400,
    	        24 : 784
        	};

        	MAXVALUE = 48;   
        	}

        sys = mode;
    }

    // Initial game mode, defined at top of lotto_form_*.vm etc.
    selectGameMode(sys);
      </script>
    </head>

    <body onload="initFrontpage();" id="lotto" onunload="unload()">
      <div id="container">

    <!-- header.vm START -->
        <div id="header">


      <div id="top-nav">

        <ul>
          <li class="first">
            <a href="/" id="logo" title="Veikkaus"><img src="/info/media/shared/logo.jpg" alt="Veikkaus" /></a>
          </li>
                      <li class="games current" onclick="toggleGameList(this, event);">
                <a href="#" title="Pelit" onclick="return false;">Pelit</a>
            <div class="container">
              <p>Pelien sivuilta löydät pelikupongit, viimeisimmät tulokset, peliohjeet ja tilastot.</p>

              <ul>
                <li class="lotto"><a href="/pelit?op=frontpage&amp;game=lotto&amp;l=f" title="Lotto">Lotto</a></li>
                <li class="keno"><a href="/pelit?op=frontpage&amp;game=keno&amp;l=f" title="Keno">Keno</a></li>
                <li class="viking"><a href="/pelit?op=frontpage&amp;game=viking&amp;l=f" title="Viking Lotto">Viking Lotto</a></li>
            	                                    <li class="jokeri"><a href="/pelit?op=frontpage&amp;game=jokeri&amp;l=f" title="Jokeripelit">Jokeripelit</a></li>
            		    		            <li class="bingo"><a href="/pelit?op=frontpage&amp;game=bingo&amp;l=f" title="Veikkausbingo">Veikkausbingo</a></li>

                                        <li>&nbsp;</li>

                <li>&nbsp;</li>
                  </ul>

                  <ul class="viiva">
          <!-- Help snippet snippet/help/fi/other/games_einstant_links.html start -->
                  <li class="einstant"><a href="/pelit?game=einstant&amp;op=frontpage&amp;l=f" title="Nettiarvat" class="current">Nettiarvat:</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/saunaan/index.html" title="Saunaan-arpa">- Saunaan-arpa</a></li>

                  <li class="einstant"><a href="/info/nettiarvat/palapeli/index.html" title="Palapeli-arpa">- Palapeli-arpa</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/kesa/index.html" title="Kes&auml;-arpa">- Kes&auml;-arpa</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/jalokivi/index.html" title="Jalokiviarpa">- Jalokiviarpa</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/onnenbiisit/index.html" title="Onnenbiisit-arpa">- Onnenbiisit</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/onnensanat/index.html" title="Onnensanat-arpa">- Onnensanat</a></li>  
                  <li class="einstant"><a href="/info/nettiarvat/assa/index.html" title="&Auml;ss&auml;-arpa">- &Auml;ss&auml; </a></li>

                  <li class="einstant"><a href="/info/nettiarvat/casino/index.html" title="Casino-arpa">- Casino</a></li>
    			  <li class="einstant"><a href="/info/nettiarvat/luonto/index.html" title="Luontoarpa">- Luonto</a></li>
                  <li class="einstant"><a href="/info/nettiarvat/horoskooppi/index.html" title="Horoskooppiarpa">- Horoskooppi</a></li>
    			  <!-- Help snippet snippet/help/fi/other/games_einstant_links.html end -->
              </ul>
                  <ul class="viiva">
                <li class="fixedodds"><a href="/pelit?op=frontpage&amp;game=fixedodds&amp;l=f" title="Pitkäveto">Pitkäveto</a></li>

                    <li class="score"><a href="/pelit?op=frontpage&amp;game=score&amp;l=f" title="Tulosveto">Tulosveto</a></li>
                    <li class="multiscore"><a href="/pelit?op=frontpage&amp;game=multiscore&amp;l=f" title="Moniveto">Moniveto</a></li>
                    <li class="winner"><a href="/pelit?op=frontpage&amp;game=winner&amp;l=f" title="Voittajavedot">Voittajavedot</a></li>
                        <li class="live"><a href="/live?op=frontpage&amp;l=f" title="Live-veto">Live-veto</a></li>
                    <li class="sport"><a href="/pelit?op=frontpage&amp;game=sport&amp;l=f" title="Vakiot">Vakiot</a></li>
                    <li class="ravi"><a href="/pelit?op=frontpage&amp;game=ravi&amp;l=f" title="V-pelit">V-pelit</a></li>

                                          </ul>

             	 <ul class="viiva">
        <!-- Help snippet snippet/help/fi/other/games_non_gaming_links.html start -->
        <li><a href="/info/pelit/index.html" title="Pelit-etusivu">Pelit-etusivu</a></li>
        <li><a href="/pelit?op=jackpot&amp;l=f" title="Potit">Potit</a></li>
    	<li><a href="/info/arvat/index.html" title="Arvat">Arvat</a></li>
        <li><a href="/info/pelitilastot/index.html" title="Pelitilastot">Pelitilastot</a></li>

        <li><a href="#" title="Tulokset" onclick="window.open('/info/apua/tuloshaku/index.html','Tulostenhakukone','toolbar=no,directories=no,status=no,scrollbars=yes,resizable=yes,menubar=no,location=no,copyhistory=no,width=600,height=600')">Tulokset</a></li>
        <li><a href="/info/abc/palvelut/rastipekka.html">Rastipekka</a></li>
        <li><a href="/info/abc/index.html" title="Pelaamisen ABC">Pelaamisen ABC</a></li>
        <li><a href="/info/pelipaussi/index.html" title="Pelipaussi">Pelipaussi</a></li><!-- Help snippet snippet/help/fi/other/games_non_gaming_links.html end -->
          	    </ul>
              <div class="clearer"></div>

              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>
          </li>    
          <!--end of game link-->



          <li class="dreams " onclick="toggleGameList(this, event);">

            <a href="#" title="Haave" onclick="return false;" >Haave</a>
            <div class="container">
             	 <ul>
          <!-- Help snippet snippet/help/fi/other/dreams_links.html start -->
    				<li class="dreams"><a href="/info/haaveita/index.html" title="Haave-etusivu" class="current">Haave-etusivu</a></li>
    				<li class="dreams"><a href="/info/haaveita/voittajat/index.html" title="Voittajat">Voittajat</a></li>
    				<li class="dreams"><a href="/info/haaveita/kun_voitat/index.html" title="Kun voitat">Kun voitat</a></li>

    				<li class="dreams"><a href="/info/haaveita/loyda_pelisi/index.html" title="L&ouml;yd&auml; pelisi">L&ouml;yd&auml; pelisi</a></li>
    				<li class="dreams"><a href="/info/kenossa/index.html" title="Kenossa">Kenossa</a></li>
                    <li class="dreams"><a href="https://www2.veikkaus.fi/jokerivitsi/">Jokerivitsi</a></li>
                    <!-- Help snippet snippet/help/fi/other/dreams_links.html end -->
             	 </ul>
              <div class="clearer"></div>

              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>
          </li>

          <li class="sports " onclick="toggleGameList(this, event);">
            <a href="#" title="Urheilu" onclick="return false;" >Urheilu</a>

            <div class="container">
             	 <ul>
          <!-- Help snippet snippet/help/fi/other/sports_links.html start -->
                          <li class="sports"><a href="/info/urheilua/index.html" title="Urheilu-etusivu" class="current">Urheilu-etusivu</a></li>
                          <li class="sports"><a href="/info/urheilua/vakio/index.html" title="Vakioviikko">Vakioviikko</a></li>
                          <li class="sports"><a href="/info/urheilua/sports_week.html" title="Kalenteri">Kalenteri</a></li>
                          <li class="sports"><a href="/info/urheilua/paivanvedot/index.html" title="P&auml;iv&auml;n vedot">P&auml;iv&auml;n vedot</a></li>

                          <li class="sports"><a href="/info/urheilua/urheilutilastot/index.html" title="Tilastot">Tilastot</a></li>
    					  <li class="sports"><a href="/info/urheilua/jalkipelit/index.html" title="J&auml;lkipelit">J&auml;lkipelit</a></li>
                 <li class="sports"><a href="https://www3.veikkaus.fi/vetosm/index.html" title="Vedonly&ouml;nnin SM-kisa"><strong>Veto SM</strong></a></li>
                 <li class="sports"><a href="https://www3.veikkaus.fi/v75sm/index.html" title="V75 SM"><strong>V75 SM</strong></a></li>
                 <li class="sports"><a href="https://www3.veikkaus.fi/vakiosm/index.html" title="Vakio SM"><strong>Vakio SM</strong></a></li>
    					  <!-- Help snippet snippet/help/fi/other/sports_links.html end -->

             	 </ul>
              <div class="clearer"></div>
              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>
          </li>


          <li class="entertainment " onclick="toggleGameList(this, event);">
            <a href="#" title="Viihde" onclick="return false;" >Viihde</a>
            <div class="container">
             	 <ul>
          <!-- Help snippet snippet/help/fi/other/entertainment_links.html start -->
                          <li class="entertainment"><a href="/info/viihde/index.html" title="Viihde-etusivu" class="current">Viihde-etusivu</a></li>
                          <li class="entertainment"><a href="/info/viihde/arvonnat/index.html" title="Arvonnat">Arvonnat</a></li>

    <li class="entertainment"><a href="/info/viihde/kampanjat/index.html" title="Kampanjat">Kampanjat</a></li><!-- Help snippet snippet/help/fi/other/entertainment_links.html end -->
             	 </ul>
              <div class="clearer"></div>
              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>

          </li>

          <li class="company " onclick="toggleGameList(this, event);">
            <a href="#" title="Yritys" onclick="return false;" >Yritys</a>
            <div class="container">
             	 <ul>
          <!-- Help snippet snippet/help/fi/other/company_links.html start -->
                          <li class="company"><a href="/info/yritys/index.html" title="Yritys-etusivu" class="current">Yritys-etusivu</a></li>
                          <li class="company"><a href="/info/yritys/yritysinfo/index.html" title="Yritysinfo">Yritysinfo</a></li>

                          <li class="company"><a href="/info/yritys/vastuullisuus/index.html" title="Vastuullisuus">Vastuullisuus</a></li>
                          <li class="company"><a href="/info/yritys/tyopaikat/index.html" title="Ty&ouml;paikat">Ty&ouml;paikat</a></li>
                          <li class="company"><a href="/info/yritys/medialle/index.html" title="Medialle">Medialle</a></li>
    					  <li class="company"><a href="/info/yritys/avainluvut/raportit.html" title="Raportit">Raportit</a></li><!-- Help snippet snippet/help/fi/other/company_links.html end -->
             	 </ul>
              <div class="clearer"></div>

              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>
          </li>

          <li class="myveikkaus " onclick="toggleGameList(this, event);">
            <a href="#" title="Oma Veikkaus" onclick="return false;" >Oma Veikkaus</a>

            <div class="container">
             	 <ul>
          <!-- Help snippet snippet/help/fi/other/myveikkaus_links.html start -->
    					  <li class="myveikkaus"><a href="/pelit?op=myveikkaus_frontpage&amp;section=account&amp;l=f" title="Oma Veikkaus -etusivu" class="current">Oma Veikkaus -etusivu</a></li>
                          <li class="myveikkaus"><a href="/pelit?op=playeraccount_frontpage&amp;section=account&amp;l=f" title="Pelitili">Pelitili</a></li>
                          <li class="myveikkaus">&nbsp;<a href="/pelit?section=account&op=playeraccount_transfer_funds_frontpage&l=f" title="Rahansiirto">- Rahansiirto</a></li>
                          <li class="myveikkaus"><a href="/pelit?section=account&amp;op=customer_frontpage&amp;l=f" title="Asiakkuus">Asiakkuus</a></li>

                          <li class="myveikkaus"><a href="/pelit?section=account&amp;op=services_frontpage&amp;l=f" title="Palvelut">Palvelut</a></li>
    					  <li class="myveikkaus"><a href="/info/veikkauskorttiedut/index.html" title="Veikkaus-korttiedut" class="current">Veikkaus-korttiedut</a></li>
      					  <li class="myveikkaus"><a href="/info/veikkauskorttiedut/veikkauskortti/index.html" title="Veikkaus-kortti">Veikkaus-kortti</a></li>
       					  <li class="myveikkaus"><a href="/info/veikkauskorttiedut/asiakaslehti/index.html" title="Asiakaslehti">Asiakaslehti</a></li>
    <!-- Help snippet snippet/help/fi/other/myveikkaus_links.html end -->
             	 </ul>
              <div class="clearer"></div>

              <ul class="footer">
                <li class="close"><a href="#" title="Sulje" onclick="return false;">Sulje</a></li>
              </ul>
              <div class="clearer"></div>
            </div>
          </li>

            </ul>
      </div>

      <div id="login-box"></div>
                      <script type="text/javascript">
        <!--
        var is_iframe = isLoginIframe();
        if (is_iframe) {
          document.write('<iframe src="/pelit?op=login_info&amp;l=f" name="loginFrame" id="login"><' + '/iframe>');
        }  
        -->
      </script>
        </div>
      <noscript>
        <div class="error" style="margin-left: 10px; margin-right: 10px;"> 
        <p><strong>Selaimesi ei tue JavaScriptiä tai JavaScript ei ole päällä. <a href="/pelit?op=nojavascript&amp;l=f">Lue lisää</a>.<br>Voit käyttää myös <a href="/mobile"> mobiilikäyttöliittymää </a>.</strong></p>
      </div>
    </noscript>
    <!-- header.vm END -->

    <!-- navigation_full.vm START -->
          <div id="sub-nav">
      <ul>

                <li class="first current"><a href="/pelit?game=lotto&amp;op=frontpage&amp;l=f" title="Lotto">Lotto</a></li>

                    <li class=""><a href="/tuloshaku?game=lotto&amp;op=results_frontpage&amp;l=f" title="Tulokset">Tulokset</a></li>
                <li>  <a href="/info/lotto/pelitietoa.html" title="Pelitietoa">Pelitietoa</a></li>
          <li>  <a href="/info/lotto/ohje.html" title="Ohje">Ohje</a></li>
        <li>  <a href="/info/lotto/saannot.html" title="Säännöt">Säännöt</a></li>

          </ul>
      <div class="clearer"></div>
    </div>
    <!-- navigation_full.vm END -->


    <div class="headings">
      <h1>Lotto</h1>
      <h2>Kierros 23</h2>
    </div>
        <div id="content-container" class="bg">

          <div id="content">
                                <h3 class="ad"><a href="/pelit?game=lotto&amp;op=form" title="Täysosumille jaossa 7 100 000 e">Täysosumille jaossa <em>7 100 000 e</em></a></h3>
        <img src="/info/media/shared/lotto/bg-lotto-frontpage.gif" class="ad" alt="" />

            <div id="play">
              <h2><a href="/pelit?game=lotto&amp;op=form&amp;l=f" title="Pelikuponki">Pelikuponki</a></h2>
              <!-- draw = 1065 -->
              <p>Pelaaminen päättyy la 12.6. klo 20.30</p>

                                                        <div>
          <p>Täysosumille jaossa <strong>7 100 000 e.</strong><br/>
                            &nbsp;
    </p>
        </div>

              <p>
                <strong>Pelitavat:</strong>
                <a href="/pelit?game=lotto&amp;op=form&amp;l=f" title="Tavallinen">Tavallinen</a> | 
                <a href="/pelit?game=lotto&amp;op=systemform&amp;l=f" title="Järjestelmä">Järjestelmä</a> | 
                <a href="/pelit?game=lotto&amp;op=reducedform&amp;l=f" title="Harava">Harava</a> |
                <a href="/pelit?game=lotto&amp;op=dreamform&amp;l=f" title="Unelmalotto">Unelmalotto</a>                        	| <a href="/pelit?game=lotto&amp;op=favouriterowsform&amp;l=f" title="Suosikkirivit">Suosikkirivit</a>                      </p>

            </div>

            <div class="help-links">
    <!-- Help snippet snippet/help/fi/lotto/lotto_links.html start -->

    <p>Lottoarvonnan voit kuunnella my&ouml;s Yle Radio Suomesta joka lauantai klo 20.45.</p>
    <p><img src="/info/media/mainokset/ajankohtaiset/kuponkisivun_mainos/lottoradio.jpg" alt="Radio" width="120" height="60" />
    </p>
    <!--<h3><strong><img src="/info/media/mainokset/ajankohtaiset/kuponkisivun_mainos/lottoradio.jpg" width="120" height="60" /><br />
    Lottoa my&ouml;s radiosta</strong></h3>
    <p>Lauantain lottoarvonnat  kuuluvat 27. kes&auml;kuuta alkaen my&ouml;s <strong>Ylen Radio Suomessa. Kello 20.45 </strong>alkavia,  suorana l&auml;hetett&auml;vi&auml; arvontoja voi kuunnella Ylen aalloilla elokuun loppuun  saakka kaikkialla Suomessa.</p>
    --><!-- Help snippet snippet/help/fi/lotto/lotto_links.html end -->
            </div>

            <div class="content-block previous-round">

              <h2>Uusimmat tulokset</h2>
                      <h2>Kierros 22</h2>
                    <!-- lotto_result_single.vm START -->


    <div class="heading">
      <h3>Arvonta 1 - </h3>
      <p>Arvontapäivämäärä la 5.6.2010</p>

    </div>

    <table class="numbers">
      <thead>
        <tr>
          <th colspan="7">Oikea rivi</th>
          <th class="separate"></th>
          <th colspan="3">Lisänumerot</th>
        </tr>

      </thead>
      <tbody>
        <tr>
          <td>3</td>
          <td>5</td>
          <td>17</td>
          <td>19</td>

          <td>26</td>
          <td>36</td>
          <td>38</td>
          <td class="separate"></td>
            <td class="secondary">14</td>
            <td class="secondary">25</td>

            <td class="secondary">27</td>
          </tr>
      </tbody>
    </table>


      <h3>Voitonjako</h3>
    <table class="shares">
      <tbody>
          <tr>

          <th>7 oikein</th>
          <td>- kpl</td>
          <td>-&nbsp;&euro;</td>
        </tr>
          <tr>
          <th>6+1 oikein</th>
          <td>21 kpl</td>

          <td>11&nbsp;363,90&nbsp;&euro;</td>
        </tr>
          <tr>
          <th>6 oikein</th>
          <td>177 kpl</td>
          <td>1&nbsp;430,80&nbsp;&euro;</td>

        </tr>
          <tr>
          <th>5 oikein</th>
          <td>8920 kpl</td>
          <td>43,10&nbsp;&euro;</td>
        </tr>
          <tr>

          <th>4 oikein</th>
          <td>137185 kpl</td>
          <td>11,70&nbsp;&euro;</td>
        </tr>
          <tr><th>&nbsp;</th></tr>
        <tr><th>LottoPlus &minus; lisävoittoluokat</th></tr>

          <tr>
          <th>4+3 oikein</th>
          <td>11 kpl</td>
          <td>5&nbsp;415,70&nbsp;&euro;</td>
        </tr>
          <tr>
          <th>4+2 oikein</th>

          <td>1250 kpl</td>
          <td>40,70&nbsp;&euro;</td>
        </tr>
          <tr>
          <th>4+1 oikein</th>
          <td>17343 kpl</td>
          <td>5,10&nbsp;&euro;</td>

        </tr>
          <tr>
          <th>3+3 oikein</th>
          <td>390 kpl</td>
          <td>146,50&nbsp;&euro;</td>
        </tr>
          <tr>

          <th>3+2 oikein</th>
          <td>16779 kpl</td>
          <td>5,30&nbsp;&euro;</td>
        </tr>
          <tr>
          <th>3+1 oikein</th>
          <td>154615 kpl</td>

          <td>1,00&nbsp;&euro;</td>
        </tr>
          <tr><th>&nbsp;</th></tr>
      </tbody>
    </table>

    <!-- lotto_result_single.vm END -->
      		<table class="links">
              <tr>
                <td class="search-link"><a href="/tuloshaku?game=lotto&amp;op=results_frontpage" title="Tuloshaku">Tuloshaku</a></td>

                <td class="print-link"><a href="javascript:print();" title="Tulosta">Tulosta</a></td>
              </tr>
    		</table>
            </div>
    	<div class="content-block">
    <!-- Help snippet snippet/help/fi/lotto/lotto_frontpage.html start -->
    <h2>Lotto lyhyesti</h2>
    <ul>
      <li>valitaan 7 numeroa 39:st&auml; </li>

      <li>arvotaan 7 numeroa ja 3 lis&auml;numeroa 39:st&auml;</li>
      <li>rivihinta 0,80 euroa, lis&auml;voittoluokat 0,20 euroa </li>
      <li>hajarivej&auml; 1-20 kpl kupongilla  </li>
      <li>j&auml;rjestelm&auml;ss&auml; 8-11 rastia </li>

      <li>haravassa 12-18 rastia  </li>
      <li>maksamalla 0,20 euron lis&auml;maksun rivi osallistuu  my&ouml;s lis&auml;voittoluokkiin</li>
      <li>peliaika p&auml;&auml;ttyy yleens&auml; lauantaina kello 20.30</li>
      <li>arvonta-aika yleens&auml; lauantaina kello 20.45</li>

      <li>2, 3, 5, 10 viikon kestopelit tai ikipeli</li>
      <li>p&auml;&auml;voitto 7 oikein -tuloksella</li>
      <li>voitto jo 4 oikein -tuloksella </li>
      <li>lis&auml;voittoluokissa voitto jos riviss&auml; 3 tai 4 oikein ja lis&auml;ksi 1, 2  tai 3 lis&auml;numeroa oikein</li>

      <li><a href="https://www.veikkaus.fi/info/kampanjat/lottoplus_ja_vikingplus/lottoplus_ja_vikingplus.html#ikipeliohje">N&auml;in lis&auml;&auml;t LottoPlus-lis&auml;voittoluokat ikipeliin</a></li>
      <li><a href="/info/lotto/haravaopas_plussat.html">Haravaopas kertoo Plussien voittoluokat</a><br />
      </li>
    </ul>
    <p>&nbsp;</p>
    <!-- Help snippet snippet/help/fi/lotto/lotto_frontpage.html end -->
    	</div>
     </div>

          <hr class="hide" />

          <div id="extras">
    <!-- gamefolder_empty.vm START -->
    <!-- salestimes.vm START -->
    <script type="text/javascript">
      gamingSystemOpen = false;
      openTargetsExist = true;
    </script>

            <script type="text/javascript">
          gamingSystemOpen = true;
        </script>
                            <!-- salestimes.vm END -->

    <div id="folder" class="harmaa">
          <div class="heading-left">
    	      <div class="heading-right">
          <h3>Pelikansio</h3>
        </div>
      </div>
      <div id="folder-content" class="empty-rows">

        <!-- salestimes.vm START -->

    <script type="text/javascript">
      gamingSystemOpen = false;
      openTargetsExist = true;
    </script>

            <script type="text/javascript">
          gamingSystemOpen = true;
        </script>
                            <!-- salestimes.vm END -->

        <div class="empty-content">
          Pelikansiossa ei ole pelejä.    </div>
      </div>
    </div>

    <!-- gamefolder_empty.vm END -->
    <!-- lotto_quickpick.vm START -->
    <form action="/pelit?game=lotto&amp;op=checkGame&amp;stats_wager_type=quickpick" method="post" name="lotto-quickgame" onsubmit="return isQuickPickValid(this);" >
      <div class="game-box">
        <input type="hidden" name="system_size" value="7" />
        <input type="hidden" name="Pelaapikapeli" value="Pelaa" />

        <div class="heading-left"><div class="heading-right">
          <h3>Pelaa Loton pikapeli</h3>
        </div>

      </div>   <div class="box">
        <div class="game">
          <p>
            <label>
              <strong>Rivimäärä</strong>
              <select id="quick_rows" name="quick_rows" onchange="updateQuickPickGamePrice(this.form, 'quick-price');">
                <option value="1">1 rivi</option>

     <option value="2">2 riviä</option>

     <option value="3">3 riviä</option>

     <option value="4">4 riviä</option>

     <option value="5">5 riviä</option>

     <option value="6">6 riviä</option>

     <option value="7">7 riviä</option>


     <option value="8">8 riviä</option>

     <option value="9">9 riviä</option>

     <option value="10">10 riviä</option>

     <option value="11">11 riviä</option>

     <option value="12" selected="selected">12 riviä</option>

     <option value="13">13 riviä</option>


     <option value="14">14 riviä</option>

     <option value="15">15 riviä</option>

     <option value="16">16 riviä</option>

     <option value="17">17 riviä</option>

     <option value="18">18 riviä</option>

     <option value="19">19 riviä</option>


     <option value="20">20 riviä</option>

              </select>
            </label>
            <label>
              <strong>Kesto</strong>
              <select id="duration" name="D" onchange="updateQuickPickGamePrice(this.form, 'quick-price');">
                <option value="1" selected="selected">1 viikko</option>

                <option value="2">2 viikkoa</option>
                <option value="3">3 viikkoa</option>
                <option value="5">5 viikkoa</option>
                <option value="10">10 viikkoa</option>
                <option value="0">Ikipeli</option>
              </select>

            </label>
          </p>
    	  <p class="checkbox">
              <strong>LottoPlus &minus; lisävoittoluokat: </strong>
              <label for="awdCheckBox">
                <input type="checkbox" id="awdCheckBox" name="awdSelected" value="true" onclick="updateQuickPickGamePrice(this.form, 'quick-price');" />
                + 0,20&nbsp;&euro;/rivi          </label>

          </p> 
          	<!-- jokeri_gamesaddon.vm START -->

    	<p class="checkbox" id="jokeri_gamesaddon">




       	<strong id="jokeri_game_name">Jokeripelit: </strong>
    	<span>
    		<label for=lottojokeri_sidegame>
    	    	<input type="checkbox" id="lottojokeri_sidegame" name="lottojokeri_sidegame" value="0" 
    	    		onclick="this.checked ? value = 1 : value = 0;updateJokerSelectList();updateQuickPickGamePrice(this.form, 'quick-price')"  />
    	    	Lauantai-Jokeri<br/>

    	    </label>
    	</span>
    	<strong id="jokeri_game_name">Jokeririvejä </strong>
    	<select id="jokeri_rows" name="jokeri_rows" onclick="updateQuickPickGamePrice(this.form, 'quick-price')" disabled>
    											<option value="1" selected="selected">
    							1 rivi						</option>
    											<option value="2" >
    							2 riviä						</option>

    											<option value="3" >
    							3 riviä						</option>
    											<option value="4" >
    							4 riviä						</option>
    											<option value="5" >
    							5 riviä						</option>
    											<option value="6" >

    							6 riviä						</option>
    											<option value="7" >
    							7 riviä						</option>
    											<option value="8" >
    							8 riviä						</option>
    											<option value="9" >
    							9 riviä						</option>

    											<option value="10" >
    							10 riviä						</option>
    			</select>

    <input type="hidden" name="jokeriNumbers" value="" />
    </p>
    <!-- jokeri_gamesaddon.vm END -->
        </div>     <div class="price">
          <h4>Hinta .... <span id="quick-price">0,00&nbsp;&euro;</span></h4>

        </div>
        <div class="submit">
          <input type="submit" id="qp-submit" name="pikapeli" value="Pelaa" />
        </div>
      </div> </div>
    </form>
    <!-- lotto_quickpick.vm END -->
    <!-- Help snippet snippet/help/fi/lotto/lotto_frontpage_side.html start -->
    <!-- Help snippet snippet/help/fi/lotto/lotto_frontpage_side.html end -->
          </div>

          <div class="clearer"></div>
        </div>

    <!-- footer.vm START -->
          <div id="footer">
      <div class="copyright">
        <p>Asiakasneuvonta päivittäin klo 8:00-22:00 <strong>0800 17284</strong></p>
        <p><a href="/info/copyright.html" title="&copy; Copyright Veikkaus Oy">&copy; Copyright Veikkaus Oy</a></p>

      </div>

      <div class="nav">
        <ul>
                <li class="first"><a href="/info/abc" title="Pelaamisen ABC">Pelaamisen ABC</a></li>
          <li><a href="info/sivukartta.html" title="Sivukartta">Sivukartta</a></li>
          <li>  <a href="/info/palaute/" title="Palaute">Palaute</a></li>

                  <li class="last"><a href="info/pelipaussi/" title="Pelipaussi">Pelipaussi</a></li>
              </ul>
      </div>
      <div class="clearer"></div>
    </div>
      <!-- APP time: 8.6.2010 klo 23.25 -->
            <script type="text/javascript">
        language = "f";
        userId = "";
          statisticPrice = "";
          statisticsPageId = "lotto_frontpage";
        statisticsPageExtraId = "";
      </script>
      <!-- Help snippet snippet/help/fi/other/statistics.html start -->

       <script type="text/javascript" src="/info/statistic/swatag.js"></script>
    <!-- Help snippet snippet/help/fi/other/statistics.html end -->
    <!-- footer.vm END -->

        <div class="clearer"></div>
      </div>
    </body>
    </html>
    """
    unittest.main()
########NEW FILE########
__FILENAME__ = lottorivitmodel
from google.appengine.ext import db
class VoittoRivi(db.Model):
    kierros=db.IntegerProperty()
    vuosi=db.IntegerProperty()
    numerot=db.ListProperty(int)
    lisanumerot=db.ListProperty(int)
    
class LottoRivi(db.Model):
    owner=db.UserProperty(auto_current_user_add=True)
    numerot=db.ListProperty(int)

class Voittoluokat(db.Model):
    numerot_count=db.IntegerProperty()
    lisanumerot_count=db.IntegerProperty()
    plus=db.BooleanProperty(default=False)
    
    def __str__(self):
        result = "%d" % self.numerot_count
        if self.lisanumerot_count > 0:
            result += "+%d" % self.lisanumerot_count
        result += " oikein"
        return result
    

class Asetukset(db.Model):
    user=db.UserProperty(auto_current_user_add=True)
    plus=db.BooleanProperty(default=False)
########NEW FILE########
__FILENAME__ = onko-voittoa
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2010 Juha Autero <jautero@iki.fi>
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
#

project="Onko Voittoa"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright &copy; 2010 Juha Autero <jautero@iki.fi>"
application="onko-voittoa"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users

from fetcher import RivitHandler
from tarkista import LottoTarkistaja

import lottorivitmodel

class OnkoVoittoa(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    current_user=users.get_current_user()
    asetukset=lottorivitmodel.Asetukset.gql("where user = :1", current_user).get()
    if not asetukset:
      asetukset=lottorivitmodel.Asetukset()
    rivit=lottorivitmodel.LottoRivi.gql("where owner = :1",current_user)
    voittoluokatplus=lottorivitmodel.Voittoluokat.all()
    voittoluokatnormaali=lottorivitmodel.Voittoluokat.gql("where plus=False")
    voittorivi=lottorivitmodel.VoittoRivi.gql("ORDER BY vuosi DESC,kierros DESC").get()
    if asetukset.plus:
        voittoluokat=voittoluokatplus
    else:
        voittoluokat=voittoluokatnormaali
    tarkistaja=LottoTarkistaja(voittorivi,voittoluokat)
    voitto=False
    template_values["logouturl"]=users.create_logout_url("/")
    template_values["voittorivi"]=voittorivi.numerot
    template_values["lisanumerot"]=voittorivi.lisanumerot
    template_values["kierros"]="%d/%d" % (voittorivi.kierros,voittorivi.vuosi)
    template_values["rivit"]=[]
    template_values["voitot"]=[]
    for rivi in rivit:
      template_values["rivit"].append(rivi.numerot)
      for result in tarkistaja.tarkista(rivi.numerot):
        voitto=True
        template_values["voitot"].append(str(result))
    template_values["voitto"]=voitto
    if asetukset.plus:
      template_values["pluschecked"]="checked"
    else:
      template_values["pluschecked"]=""
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    id=self.request.get("id",None)
    if id:
      rivi=lottorivitmodel.LottoRivi.gql("where owner = :1 and id = :2",users.geet_current_user(),id)
    else:
      rivi=lottorivitmodel.LottoRivi()
    rivi.numerot=[int(n) for n in self.request.get_all("number")]
    rivi.put()
    self.get()
    
class VoitotHandler(webapp.RequestHandler):

      def get(self):
        template_values=globals()
        voittoluokat=lottorivitmodel.Voittoluokat.all()
        template_values["luokat"]=[]
        for luokka in voittoluokat:
          template_values["luokat"].append((luokka.numerot_count,luokka.lisanumerot_count,luokka.plus))
        path = os.path.join(os.path.dirname(__file__), 'voitot.html')
        self.response.out.write(template.render(path, template_values))

      def post(self):
        rivi=lottorivitmodel.Voittoluokat()
        rivi.numerot_count=int(self.request.get("numerot"))
        rivi.lisanumerot_count=int(self.request.get("lisanumerot"))
        rivi.plus=(self.request.get("plus","false")=="true")
        rivi.put()
        self.get()
        
class AsetuksetHandler(webapp.RequestHandler):
  def get(self):
    self.redirect("/")
  def post(self):
    asetukset=lottorivitmodel.Asetukset.gql("where owner = :1", users.get_current_user()).get()
    if not asetukset:
      asetukset=lottorivitmodel.Asetukset()
    asetukset.plus=(self.request.get("plus","false")=="true")
    asetukset.put()
    self.get()

def main():
  application = webapp.WSGIApplication([('/', OnkoVoittoa), ('/tulokset', RivitHandler), ("/voitot", VoitotHandler),
                                        ('/asetukset', AsetuksetHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = tarkista
import unittest

class LottoTarkistaja:
    def __init__(self,voittorivi,voittoluokat):
        self.voittorivi=voittorivi
        self.voittoluokat=voittoluokat
        
    def tarkista(self,rivi):
        numerot=self.laskenumerot(rivi)
        lisanumerot=self.laskelisanumerot(rivi)
        voitot=[]
        for voittoluokka in self.voittoluokat:
            if numerot>=voittoluokka.numerot_count and lisanumerot>=voittoluokka.lisanumerot_count:
                voitot.append(voittoluokka)
        return voitot
        
    def laskenumerot(self,rivi):
        count=0
        for numero in rivi:
            if numero in self.voittorivi.numerot:
                count+=1
        return count
        
    def laskelisanumerot(self,rivi):
        count=0
        for numero in rivi:
            if numero in self.voittorivi.lisanumerot:
                count+=1
        return count

class LottoTarkistajaTest(unittest.TestCase):
    class voittorivi:
        numerot=[1,2,3,4,5,6,7]
        lisanumerot=[8,9,10]
    class voittoluokka:
        def __init__(self,numerot,lisanumerot=0):
            self.numerot_count=numerot
            self.lisanumerot_count=lisanumerot
    voittoluokka7=voittoluokka(7)
    voittoluokka61=voittoluokka(6,1)
    voittoluokka6=voittoluokka(6)
    voittoluokka5=voittoluokka(5)
    voittoluokka4=voittoluokka(4)
    voittoluokat=[voittoluokka7,voittoluokka61,voittoluokka6,voittoluokka5,voittoluokka4]
    def setUp(self):
        self.tarkastaja=LottoTarkistaja(self.voittorivi(),self.voittoluokat)
    def tearDown(self):
        self.tarkastaja=None
    def test_seitsemanoikein(self):
        result=self.tarkastaja.tarkista([1,2,3,4,5,6,7])
        self.assertEqual(len(result),4)
        self.assertTrue(self.voittoluokka4 in result)
        self.assertTrue(self.voittoluokka5 in result)
        self.assertTrue(self.voittoluokka6 in result)
        self.assertTrue(self.voittoluokka7 in result)
    def test_eivoittoa(self):
        result=self.tarkastaja.tarkista([8,9,10,11,12,13,5])
        self.assertEqual(result,[])
    def test_kuusijalisanumerooikein(self):
        result=self.tarkastaja.tarkista([6,5,8,4,3,2,1])
        self.assertEqual(len(result),4)
        self.assertTrue(self.voittoluokka4 in result)
        self.assertTrue(self.voittoluokka5 in result)
        self.assertTrue(self.voittoluokka6 in result)
        self.assertTrue(self.voittoluokka61 in result)
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = model
from google.appengine.ext import db
class PathToHappiness(db.Model):
    owner = db.UserProperty(required=True)
    title=db.StringProperty()
    description=db.TextProperty()
    
class MilestoneInThePath(db.Model):
    path=db.ReferenceProperty(PathToHappiness)
    created=db.DateTimeProperty(auto_now_add=True)
    title=db.StringProperty()
    description=db.TextProprety()
    goal=db.IntegerProperty()
    progress=db.IntegerProperty()
    
########NEW FILE########
__FILENAME__ = path-to-happiness
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2012 Juha Autero <jautero@iki.fi>
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
#

project="Path to Happiness"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2012 Juha Autero <jautero@iki.fi>"
application="path-to-happiness"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class PathToHappiness(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', PathToHappiness)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = preferencevote
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2011 Juha Autero <jautero@iki.fi>
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
#

Project="Preference Vote"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2011 Juha Autero <jautero@iki.fi>"
application="preferencevote"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

class PreferenceVote(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', PreferenceVote)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = september
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Copyright 2008 Juha Autero
#
# Copyright 2010 Juha Autero <jautero@iki.fi>
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
#

project="September"
version="1.0"
author="Juha Autero <jautero@iki.fi>"
copyright="Copyright 2010 Juha Autero <jautero@iki.fi>"
application="september"
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from datetime import date

weekdays=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
def get_timestring():
  t=date.today()
  d=(t-date(1993,8,31)).days
  if d % 10 == 1:
    ext="st"
  elif d % 10 == 2:
    ext="nd"
  elif d % 10 == 3:
    ext="rd"
  else:
    ext="th"
  return "%s September %d%s 1993" % (weekdays[t.weekday()],d,ext)

class September(webapp.RequestHandler):

  def get(self):
    template_values=globals()
    template_values["date"]=get_timestring()
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([('/', September)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = quickstart
#!/usr/bin/env python
#
# Quickstart for Google App Engine Weekend Projects
#
# This script asks some questions and then initializes project directory.

import re, os, time
from types import StringType

wordsplit=re.compile("\W+").split
templatedir="ATemplate"
staticdir="static_files"
bootstrapurl="http://twitter.github.com/bootstrap/assets/bootstrap.zip"

def convertfile(source,target,subst={}):
    if isinstance(source,StringType):
	source=open(source)
    if isinstance(target,StringType):
	target=open(target,"w")
    data=source.read()
    source.close()
    for key in subst.keys():
	subre=re.compile('@'+key+'@')
	data=subre.sub(subst[key],data)
    target.write(data)
    target.close()

def askyesno(question,default):
    answer=""
    while answer != "y" and answer != "n":
        answer=raw_input("%s (y/n) [%s]" % (question,default))
        if not answer:
            answer=default
        answer=answer.lower()
    if answer == "y":
        return True
    else:
        return False

project=raw_input("Project name: ")
projectwords=wordsplit(project.lower())
applicationname="-".join(projectwords)

new=raw_input("Application name (%s): " % applicationname).strip()
if new:
    applicationname=new

handlername="".join([word.capitalize() for word in projectwords])

new=raw_input("Handler class name (%s): " % handlername).strip()
if new:
    handlername=new

authorname=os.popen("git config user.name").read().strip()
authormail=os.popen("git config user.email").read().strip()

new=raw_input("Author name (%s): " %authorname).strip()
if new:
    authorname=new
new=raw_input("Author email (%s): " % authormail).strip()
if new:
    authormail=new

bootstrap=askyesno("Do you want Twitter's Bootstrap?","y")
unittests=askyesno("Do you want have unit tests and TDDStateTarcker","y")

author="%s <%s>" % (authorname,authormail)

year=str(time.localtime()[0])

subst_dict={"project":project,"application":applicationname,
	    "mainhandler":handlername,"author":author,"year":year}

# Create directories
os.mkdir(applicationname)
os.mkdir(os.path.join(applicationname,staticdir))

# Copy template files
convertfile(os.path.join(templatedir,"app.yaml"),
	    os.path.join(applicationname,"app.yaml"),subst_dict)
convertfile(os.path.join(templatedir,"index.html"),
	    os.path.join(applicationname,"index.html"),subst_dict)
convertfile(os.path.join(templatedir,"index.yaml"),
	    os.path.join(applicationname,"index.yaml"),subst_dict)
convertfile(os.path.join(templatedir,"application.css"),
	    os.path.join(applicationname,staticdir,applicationname+".css"),subst_dict)
convertfile(os.path.join(templatedir,"application.js"),
	    os.path.join(applicationname,staticdir,applicationname+".js"),subst_dict)
if unittests:
    convertfile(os.path.join(templatedir,"application-ut.py"),
        os.path.join(applicationname,applicationname+".py"),subst_dict)
else:
    convertfile(os.path.join(templatedir,"application.py"),
	    os.path.join(applicationname,applicationname+".py"),subst_dict)
# Fetch Bootstrap
if bootstrap:
    import urllib2, zipfile, cStringIO
    zip=zipfile.ZipFile(cStringIO.StringIO(urllib2.urlopen(bootstrapurl).read()))
    for filename in zip.namelist():
        if filename.endswith('/'):
            os.makedirs(os.path.join(applicationname,staticdir,filename))
        else:
            zip.extract(filename,os.path.join(applicationname,staticdir))

if unittests:
        convertfile(os.path.join(templatedir,"test","tdd-state-tracker.css"),
            os.path.join(applicationname,staticdir,"tdd-state-tracker.css"),subst_dict)
        convertfile(os.path.join(templatedir,"test","tdd-state-tracker.js"),
            os.path.join(applicationname,staticdir,"tdd-state-tracker.js"),subst_dict)
        convertfile(os.path.join(templatedir,"test","test.html"),
            os.path.join(applicationname,"test.html"),subst_dict)

########NEW FILE########
